from __future__ import annotations

import time
from datetime import UTC, datetime

from workflow_engine.executor import CommandExecutor
from workflow_engine.models import (
    ExecutionStatus,
    RunExecutionResult,
    WorkflowConfig,
    WorkflowExecutionResult,
    WorkflowExecutionStatus,
    WorkflowManifest,
    WorkflowState,
)
from workflow_engine.reporting import JsonRunReporter
from workflow_engine.state import JsonStateStore
from workflow_engine.workspace import WorkspaceManager


class WorkflowRunner:
    """Coordinates workspace preparation, execution, and workflow state."""

    def __init__(
        self,
        *,
        workspace_manager: WorkspaceManager | None = None,
        executor: CommandExecutor | None = None,
        state_store: JsonStateStore | None = None,
        reporter: JsonRunReporter | None = None,
    ) -> None:
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.executor = executor or CommandExecutor()
        self.state_store = state_store or JsonStateStore()
        self.reporter = reporter or JsonRunReporter()

    def run(
        self,
        manifest: WorkflowManifest,
        *,
        run_id: str | None = None,
    ) -> RunExecutionResult:
        started_at = datetime.now(UTC)
        timer_start = time.perf_counter()

        effective_run_id = run_id or self.workspace_manager.create_run_id()

        workflow_results: list[WorkflowExecutionResult] = []

        for workflow in manifest.workflows:
            result = self._run_workflow(
                workflow,
                run_id=effective_run_id,
            )

            workflow_results.append(result)

            self._persist_workflow_state(
                workflow=workflow,
                result=result,
                run_id=effective_run_id,
            )

        finished_at = datetime.now(UTC)

        run_result = RunExecutionResult(
            run_id=effective_run_id,
            workflows=workflow_results,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=time.perf_counter() - timer_start,
        )

        self.reporter.write(run_result)

        return run_result

    def _run_workflow(
        self,
        workflow: WorkflowConfig,
        *,
        run_id: str,
    ) -> WorkflowExecutionResult:
        prepared = self.workspace_manager.prepare(
            workflow,
            run_id=run_id,
        )

        previous_state = self.state_store.get(workflow.name)

        start_index = 0

        if (
            workflow.execution.resume_from_checkpoint
            and previous_state.last_status == WorkflowExecutionStatus.FAILED
            and previous_state.last_successful_step is not None
        ):
            step_names = [step.name for step in workflow.steps]

            if previous_state.last_successful_step in step_names:
                start_index = (
                    step_names.index(previous_state.last_successful_step) + 1
                )

        step_results = []

        for step in workflow.steps[start_index:]:
            result = self.executor.run_step(
                workflow,
                step,
                working_directory=prepared.project_dir,
            )

            step_results.append(result)

            if (
                result.status != ExecutionStatus.SUCCEEDED
                and not workflow.execution.continue_on_failure
            ):
                break

        workflow_status = self._determine_workflow_status(
            workflow,
            completed_steps=len(step_results),
            successful_steps=sum(
                result.status == ExecutionStatus.SUCCEEDED
                for result in step_results
            ),
            previously_completed_steps=start_index,
        )

        workflow_status = self._determine_workflow_status(
            workflow,
            completed_steps=len(step_results),
            successful_steps=sum(
                result.status == ExecutionStatus.SUCCEEDED
                for result in step_results
            ),
            previously_completed_steps=start_index,
        )

        return WorkflowExecutionResult(
            workflow_name=workflow.name,
            status=workflow_status,
            steps=step_results,
        )

    def _persist_workflow_state(
        self,
        *,
        workflow: WorkflowConfig,
        result: WorkflowExecutionResult,
        run_id: str,
    ) -> None:
        successful_steps = [
            step
            for step in result.steps
            if step.status == ExecutionStatus.SUCCEEDED
        ]

        last_successful_step = (
            successful_steps[-1].step_name
            if successful_steps
            else None
        )

        failed_steps = [
            step
            for step in result.steps
            if step.status != ExecutionStatus.SUCCEEDED
        ]

        last_error = None

        if failed_steps:
            failed_step = failed_steps[-1]
            last_error = (
                failed_step.stderr.strip()
                or f"Step '{failed_step.step_name}' failed"
            )

        state = WorkflowState(
            workflow_name=workflow.name,
            last_run_id=run_id,
            last_status=result.status,
            last_successful_step=last_successful_step,
            last_error=last_error,
        )

        self.state_store.save(state)

    @staticmethod
    def _determine_workflow_status(
        workflow: WorkflowConfig,
            *,
            completed_steps: int,
            successful_steps: int,
            previously_completed_steps: int = 0,
        ) -> WorkflowExecutionStatus:
            total_steps = len(workflow.steps)
        
            total_successful_steps = (
                previously_completed_steps + successful_steps
            )
        
            total_completed_steps = (
                previously_completed_steps + completed_steps
            )
        
            failed_steps = completed_steps - successful_steps
        
            # Every configured step has succeeded,
            # including any previously checkpointed steps.
            if total_successful_steps == total_steps:
                return WorkflowExecutionStatus.SUCCEEDED
        
            # A failure occurred and this workflow is configured
            # to stop on failure.
            if failed_steps > 0 and not workflow.execution.continue_on_failure:
                return WorkflowExecutionStatus.FAILED
        
            # Nothing has succeeded.
            if total_successful_steps == 0:
                return WorkflowExecutionStatus.FAILED
        
            # Execution stopped before all steps were attempted.
            if total_completed_steps < total_steps:
                return WorkflowExecutionStatus.FAILED
        
            # All steps were attempted, but at least one failed
            # while continue_on_failure allowed the workflow to proceed.
            return WorkflowExecutionStatus.PARTIALLY_SUCCEEDED
