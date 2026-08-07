
# src/workflow_engine/workspace.py

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from workflow_engine.models import SourceType, WorkflowConfig


class WorkspaceError(RuntimeError):
    """Raised when an isolated workflow workspace cannot be prepared."""


@dataclass(frozen=True)
class PreparedWorkspace:
    """Represents the isolated directory prepared for one workflow."""

    workflow_name: str
    run_id: str
    run_root: Path
    project_dir: Path


class WorkspaceManager:
    """Creates isolated execution directories for configured workflows."""

    def __init__(self, base_dir: str | Path = ".workflow-runs") -> None:
        self.base_dir = Path(base_dir).resolve()

    def create_run_id(self) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        unique_suffix = uuid4().hex[:8]
        return f"{timestamp}-{unique_suffix}"

    def prepare(
        self,
        workflow: WorkflowConfig,
        *,
        run_id: str | None = None,
    ) -> PreparedWorkspace:
        effective_run_id = run_id or self.create_run_id()

        run_root = self.base_dir / effective_run_id
        project_dir = run_root / workflow.name

        self._assert_within_base(run_root)
        self._assert_within_base(project_dir)

        if project_dir.exists():
            raise WorkspaceError(
                f"Workspace already exists for workflow "
                f"'{workflow.name}': {project_dir}"
            )

        project_dir.parent.mkdir(parents=True, exist_ok=True)

        if workflow.source.type == SourceType.LOCAL:
            self._copy_local_source(
                source=Path(workflow.source.location),
                destination=project_dir,
            )
        elif workflow.source.type == SourceType.GIT:
            raise WorkspaceError(
                "Git sources are not supported yet. "
                "Git cloning will be added in a later step."
            )
        else:
            raise WorkspaceError(
                f"Unsupported source type: {workflow.source.type}"
            )

        return PreparedWorkspace(
            workflow_name=workflow.name,
            run_id=effective_run_id,
            run_root=run_root,
            project_dir=project_dir,
        )

    def cleanup_run(self, run_id: str) -> None:
        run_root = self.base_dir / run_id
        self._assert_within_base(run_root)

        if run_root.exists():
            shutil.rmtree(run_root)

    def _copy_local_source(
        self,
        *,
        source: Path,
        destination: Path,
    ) -> None:
        resolved_source = source.resolve()

        if not resolved_source.exists():
            raise WorkspaceError(
                f"Local workflow source does not exist: {resolved_source}"
            )

        if not resolved_source.is_dir():
            raise WorkspaceError(
                f"Local workflow source is not a directory: {resolved_source}"
            )

        try:
            shutil.copytree(resolved_source, destination)
        except OSError as exc:
            raise WorkspaceError(
                f"Unable to copy workflow source from "
                f"{resolved_source} to {destination}: {exc}"
            ) from exc

    def _assert_within_base(self, path: Path) -> None:
        resolved_path = path.resolve()

        try:
            resolved_path.relative_to(self.base_dir)
        except ValueError as exc:
            raise WorkspaceError(
                f"Workspace path escapes configured base directory: "
                f"{resolved_path}"
            ) from exc

