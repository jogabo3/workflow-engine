from __future__ import annotations

import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from workflow_engine.models import (
    ExecutionStatus,
    StepExecutionResult,
    WorkflowConfig,
    WorkflowStep,
)


class CommandExecutor:
    """Executes configured workflow steps inside isolated project directories."""

    def run_step(
        self,
        workflow: WorkflowConfig,
        step: WorkflowStep,
        *,
        working_directory: str | Path,
    ) -> StepExecutionResult:
        cwd = Path(working_directory).resolve()

        if not cwd.exists():
            raise ValueError(f"Working directory does not exist: {cwd}")

        if not cwd.is_dir():
            raise ValueError(f"Working directory is not a directory: {cwd}")

        maximum_attempts = workflow.execution.retries + 1

        last_stdout = ""
        last_stderr = ""
        last_exit_code: int | None = None
        last_status = ExecutionStatus.FAILED

        started_at = datetime.now(UTC)
        timer_start = time.perf_counter()

        for attempt in range(1, maximum_attempts + 1):
            try:
                completed = subprocess.run(
                    step.command,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=workflow.execution.timeout_seconds,
                    shell=True,
                    check=False,
                )

                last_stdout = completed.stdout
                last_stderr = completed.stderr
                last_exit_code = completed.returncode

                if completed.returncode == 0:
                    last_status = ExecutionStatus.SUCCEEDED
                    break

                last_status = ExecutionStatus.FAILED

            except subprocess.TimeoutExpired as exc:
                last_status = ExecutionStatus.TIMED_OUT
                last_exit_code = None
                last_stdout = self._decode_output(exc.stdout)
                last_stderr = self._decode_output(exc.stderr)

            if attempt < maximum_attempts:
                continue

        finished_at = datetime.now(UTC)
        duration_seconds = time.perf_counter() - timer_start

        return StepExecutionResult(
            workflow_name=workflow.name,
            step_name=step.name,
            command=step.command,
            status=last_status,
            exit_code=last_exit_code,
            stdout=last_stdout,
            stderr=last_stderr,
            attempts=attempt,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
        )

    @staticmethod
    def _decode_output(output: str | bytes | None) -> str:
        if output is None:
            return ""

        if isinstance(output, bytes):
            return output.decode("utf-8", errors="replace")

        return output