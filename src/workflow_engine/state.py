from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from workflow_engine.models import WorkflowState


class StateStoreError(RuntimeError):
    """Raised when workflow state cannot be read or written."""


class JsonStateStore:
    """Persists workflow execution state as JSON."""

    def __init__(self, base_dir: str | Path = ".workflow-state") -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get(self, workflow_name: str) -> WorkflowState:
        state_path = self._state_path(workflow_name)

        if not state_path.exists():
            return WorkflowState(workflow_name=workflow_name)

        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            return WorkflowState.model_validate(data)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise StateStoreError(
                f"Unable to read state for '{workflow_name}': {exc}"
            ) from exc

    def save(self, state: WorkflowState) -> None:
        state_path = self._state_path(state.workflow_name)

        state.updated_at = datetime.now(UTC)

        try:
            state_path.write_text(
                state.model_dump_json(indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise StateStoreError(
                f"Unable to save state for '{state.workflow_name}': {exc}"
            ) from exc

    def _state_path(self, workflow_name: str) -> Path:
        return self.base_dir / f"{workflow_name}.json"