from datetime import UTC, datetime

from workflow_engine.models import (
    ExecutionStatus,
    RunExecutionResult,
    StepExecutionResult,
    WorkflowExecutionResult,
    WorkflowExecutionStatus,
)
from workflow_engine.summary import build_run_summary


def test_build_run_summary() -> None:
    now = datetime.now(UTC)

    step = StepExecutionResult(
        workflow_name="alpha",
        step_name="run",
        command="python run.py",
        status=ExecutionStatus.SUCCEEDED,
        exit_code=0,
        stdout="done",
        stderr="",
        attempts=1,
        started_at=now,
        finished_at=now,
        duration_seconds=0.25,
    )

    workflow = WorkflowExecutionResult(
        workflow_name="alpha",
        status=WorkflowExecutionStatus.SUCCEEDED,
        steps=[step],
    )

    result = RunExecutionResult(
        run_id="run-123",
        workflows=[workflow],
        started_at=now,
        finished_at=now,
        duration_seconds=0.25,
    )

    summary = build_run_summary(result)

    assert summary["run_id"] == "run-123"
    assert summary["status"] == "succeeded"

    counts = summary["workflow_counts"]
    assert isinstance(counts, dict)
    assert counts["total"] == 1
    assert counts["succeeded"] == 1
    assert counts["failed"] == 0