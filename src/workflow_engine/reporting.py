from __future__ import annotations

import json
from pathlib import Path

from workflow_engine.models import RunExecutionResult
from workflow_engine.summary import build_run_summary


class RunReportError(RuntimeError):
    """Raised when a run report cannot be written."""


class JsonRunReporter:
    """Writes structured workflow run summaries to disk."""

    def __init__(
        self,
        base_dir: str | Path = ".workflow-runs",
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write(self, result: RunExecutionResult) -> Path:
        run_dir = self.base_dir / result.run_id

        try:
            run_dir.mkdir(parents=True, exist_ok=True)

            report_path = run_dir / "summary.json"

            report_path.write_text(
                json.dumps(
                    build_run_summary(result),
                    indent=2,
                ),
                encoding="utf-8",
            )

            return report_path

        except OSError as exc:
            raise RunReportError(
                f"Unable to write report for run "
                f"'{result.run_id}': {exc}"
            ) from exc