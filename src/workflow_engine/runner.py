from __future__ import annotations

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
    ) -> None:
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.executor = executor or CommandExecutor()
        self.state_store = state_store or JsonStateStore()

    def run(
        self,
        manifest: WorkflowManifest,
        *,
        run_id: str | None = None,
    ) -> RunExecutionResult:
        effective_run_id = (
            run_id or self.workspace_manager.create_run_id()
        )

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

        return RunExecutionResult(
            run_id=effective_run_id,
            workflows=workflow_results,
        )

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

        step_results = []

        for step in workflow.steps:
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
    ) -> WorkflowExecutionStatus:
        total_steps = len(workflow.steps)

        if successful_steps == total_steps:
            return WorkflowExecutionStatus.SUCCEEDED

        if successful_steps == 0:
            return WorkflowExecutionStatus.FAILED

        if completed_steps < total_steps:
            return WorkflowExecutionStatus.FAILED

        return WorkflowExecutionStatus.PARTIALLY_SUCCEEDED