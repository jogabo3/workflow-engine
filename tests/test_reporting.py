import json
from datetime import UTC, datetime
from pathlib import Path

from workflow_engine.models import (
    ExecutionStatus,
    RunExecutionResult,
    StepExecutionResult,
    WorkflowExecutionResult,
    WorkflowExecutionStatus,
)
from workflow_engine.reporting import JsonRunReporter


def test_writes_json_run_report(tmp_path: Path) -> None:
    now = datetime.now(UTC)

    step = StepExecutionResult(
        workflow_name="alpha",
        step_name="transform",
        command="python transform.py",
        status=ExecutionStatus.SUCCEEDED,
        exit_code=0,
        stdout="complete",
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

    reporter = JsonRunReporter(tmp_path / "reports")

    report_path = reporter.write(result)

    assert report_path.exists()

    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    assert report["run_id"] == "run-123"
    assert report["status"] == "succeeded"
    assert report["workflow_counts"]["total"] == 1
    assert report["workflow_counts"]["succeeded"] == 1

    assert (
        report["workflows"][0]["steps"][0]["name"]
        == "transform"
    )