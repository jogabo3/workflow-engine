from pathlib import Path

from workflow_engine.models import (
    WorkflowExecutionStatus,
    WorkflowState,
)
from workflow_engine.state import JsonStateStore


def test_returns_empty_state_when_missing(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path / "state")

    state = store.get("alpha")

    assert state.workflow_name == "alpha"
    assert state.last_run_id is None
    assert state.last_status is None


def test_saves_and_loads_state(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path / "state")

    original = WorkflowState(
        workflow_name="alpha",
        last_run_id="run-123",
        last_status=WorkflowExecutionStatus.SUCCEEDED,
        last_successful_step="transform",
    )

    store.save(original)

    loaded = store.get("alpha")

    assert loaded.workflow_name == "alpha"
    assert loaded.last_run_id == "run-123"
    assert loaded.last_status == WorkflowExecutionStatus.SUCCEEDED
    assert loaded.last_successful_step == "transform"
    assert loaded.updated_at is not None


def test_overwrites_existing_state(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path / "state")

    store.save(
        WorkflowState(
            workflow_name="alpha",
            last_run_id="run-1",
            last_status=WorkflowExecutionStatus.FAILED,
        )
    )

    store.save(
        WorkflowState(
            workflow_name="alpha",
            last_run_id="run-2",
            last_status=WorkflowExecutionStatus.SUCCEEDED,
        )
    )

    loaded = store.get("alpha")

    assert loaded.last_run_id == "run-2"
    assert loaded.last_status == WorkflowExecutionStatus.SUCCEEDED