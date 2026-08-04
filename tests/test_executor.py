from pathlib import Path

from workflow_engine.executor import CommandExecutor
from workflow_engine.models import (
    AdapterType,
    ExecutionPolicy,
    ExecutionStatus,
    SourceType,
    WorkflowConfig,
    WorkflowSource,
    WorkflowStep,
)


def build_workflow(
    *,
    retries: int = 0,
    timeout_seconds: int = 10,
) -> WorkflowConfig:
    return WorkflowConfig(
        name="test_workflow",
        source=WorkflowSource(
            type=SourceType.LOCAL,
            location="unused",
        ),
        adapter=AdapterType.COMMAND,
        steps=[
            WorkflowStep(
                name="run",
                command="python run.py",
            )
        ],
        execution=ExecutionPolicy(
            continue_on_failure=True,
            retries=retries,
            timeout_seconds=timeout_seconds,
        ),
    )


def test_successful_command_returns_structured_result(
    tmp_path: Path,
) -> None:
    script = tmp_path / "success.py"
    script.write_text(
        'print("workflow completed")',
        encoding="utf-8",
    )

    workflow = build_workflow()
    step = WorkflowStep(
        name="success",
        command="python success.py",
    )

    result = CommandExecutor().run_step(
        workflow,
        step,
        working_directory=tmp_path,
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.exit_code == 0
    assert result.attempts == 1
    assert "workflow completed" in result.stdout
    assert result.stderr == ""
    assert result.succeeded is True


def test_failed_command_captures_stderr(
    tmp_path: Path,
) -> None:
    script = tmp_path / "failure.py"
    script.write_text(
        """
import sys

print("workflow failed", file=sys.stderr)
raise SystemExit(7)
""".strip(),
        encoding="utf-8",
    )

    workflow = build_workflow()
    step = WorkflowStep(
        name="failure",
        command="python failure.py",
    )

    result = CommandExecutor().run_step(
        workflow,
        step,
        working_directory=tmp_path,
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.exit_code == 7
    assert result.attempts == 1
    assert "workflow failed" in result.stderr
    assert result.succeeded is False


def test_failed_command_is_retried(
    tmp_path: Path,
) -> None:
    script = tmp_path / "retry.py"
    counter = tmp_path / "counter.txt"

    script.write_text(
        f"""
from pathlib import Path

counter = Path(r"{counter}")
attempt = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(attempt))

if attempt < 3:
    raise SystemExit(1)

print("succeeded after retry")
""".strip(),
        encoding="utf-8",
    )

    workflow = build_workflow(retries=2)
    step = WorkflowStep(
        name="retry",
        command="python retry.py",
    )

    result = CommandExecutor().run_step(
        workflow,
        step,
        working_directory=tmp_path,
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.exit_code == 0
    assert result.attempts == 3
    assert "succeeded after retry" in result.stdout


def test_command_timeout_returns_timed_out_result(
    tmp_path: Path,
) -> None:
    script = tmp_path / "slow.py"
    script.write_text(
        """
import time

time.sleep(5)
""".strip(),
        encoding="utf-8",
    )

    workflow = build_workflow(timeout_seconds=1)
    step = WorkflowStep(
        name="slow",
        command="python slow.py",
    )

    result = CommandExecutor().run_step(
        workflow,
        step,
        working_directory=tmp_path,
    )

    assert result.status == ExecutionStatus.TIMED_OUT
    assert result.exit_code is None
    assert result.attempts == 1
    assert result.succeeded is False


def test_missing_working_directory_raises_clear_error(
    tmp_path: Path,
) -> None:
    workflow = build_workflow()
    step = WorkflowStep(
        name="run",
        command="python run.py",
    )

    missing_directory = tmp_path / "missing"

    try:
        CommandExecutor().run_step(
            workflow,
            step,
            working_directory=missing_directory,
        )
    except ValueError as exc:
        assert "Working directory does not exist" in str(exc)
    else:
        raise AssertionError("Expected ValueError")