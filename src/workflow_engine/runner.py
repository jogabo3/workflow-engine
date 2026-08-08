from __future__ import annotations

from workflow_engine.executor import CommandExecutor
from workflow_engine.models import (
    ExecutionStatus,
    RunExecutionResult,
    WorkflowConfig,
    WorkflowExecutionResult,
    WorkflowExecutionStatus,
    WorkflowManifest,
)
from workflow_engine.workspace import WorkspaceManager


class WorkflowRunner:
    """Coordinates workspace preparation and workflow execution."""

    def __init__(
        self,
        *,
        workspace_manager: WorkspaceManager | None = None,
        executor: CommandExecutor | None = None,
    ) -> None:
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.executor = executor or CommandExecutor()

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