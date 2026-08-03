
# tests/test_workspace.py

from pathlib import Path

import pytest

from workflow_engine.models import (
    AdapterType,
    SourceType,
    WorkflowConfig,
    WorkflowSource,
    WorkflowStep,
)
from workflow_engine.workspace import WorkspaceError, WorkspaceManager


def build_workflow(
    name: str,
    source_path: Path,
) -> WorkflowConfig:
    return WorkflowConfig(
        name=name,
        source=WorkflowSource(
            type=SourceType.LOCAL,
            location=str(source_path),
        ),
        adapter=AdapterType.COMMAND,
        steps=[
            WorkflowStep(
                name="run",
                command="python run.py",
            )
        ],
    )


def create_project(
    root: Path,
    project_name: str,
    file_contents: str,
) -> Path:
    project_dir = root / project_name
    project_dir.mkdir()

    project_file = project_dir / "project.yml"
    project_file.write_text(file_contents, encoding="utf-8")

    return project_dir


def test_prepares_isolated_workspace(tmp_path: Path) -> None:
    source_dir = create_project(
        tmp_path,
        "source_project",
        "name: alpha",
    )

    manager = WorkspaceManager(tmp_path / "runs")
    workflow = build_workflow("project_alpha", source_dir)

    prepared = manager.prepare(workflow, run_id="test-run")

    assert prepared.workflow_name == "project_alpha"
    assert prepared.run_id == "test-run"
    assert prepared.project_dir.exists()
    assert (
        prepared.project_dir / "project.yml"
    ).read_text(encoding="utf-8") == "name: alpha"


def test_workflows_with_same_filenames_do_not_overwrite(
    tmp_path: Path,
) -> None:
    source_alpha = create_project(
        tmp_path,
        "source_alpha",
        "name: alpha",
    )
    source_beta = create_project(
        tmp_path,
        "source_beta",
        "name: beta",
    )

    manager = WorkspaceManager(tmp_path / "runs")

    alpha = manager.prepare(
        build_workflow("project_alpha", source_alpha),
        run_id="shared-run",
    )
    beta = manager.prepare(
        build_workflow("project_beta", source_beta),
        run_id="shared-run",
    )

    alpha_contents = (
        alpha.project_dir / "project.yml"
    ).read_text(encoding="utf-8")

    beta_contents = (
        beta.project_dir / "project.yml"
    ).read_text(encoding="utf-8")

    assert alpha.project_dir != beta.project_dir
    assert alpha_contents == "name: alpha"
    assert beta_contents == "name: beta"


def test_rejects_duplicate_workspace_for_same_workflow(
    tmp_path: Path,
) -> None:
    source_dir = create_project(
        tmp_path,
        "source_project",
        "name: alpha",
    )

    manager = WorkspaceManager(tmp_path / "runs")
    workflow = build_workflow("project_alpha", source_dir)

    manager.prepare(workflow, run_id="test-run")

    with pytest.raises(
        WorkspaceError,
        match="Workspace already exists",
    ):
        manager.prepare(workflow, run_id="test-run")


def test_rejects_missing_source_directory(tmp_path: Path) -> None:
    missing_source = tmp_path / "does-not-exist"

    manager = WorkspaceManager(tmp_path / "runs")
    workflow = build_workflow(
        "project_alpha",
        missing_source,
    )

    with pytest.raises(
        WorkspaceError,
        match="does not exist",
    ):
        manager.prepare(workflow, run_id="test-run")


def test_cleanup_removes_entire_run(tmp_path: Path) -> None:
    source_dir = create_project(
        tmp_path,
        "source_project",
        "name: alpha",
    )

    manager = WorkspaceManager(tmp_path / "runs")
    workflow = build_workflow("project_alpha", source_dir)

    prepared = manager.prepare(
        workflow,
        run_id="test-run",
    )

    assert prepared.run_root.exists()

    manager.cleanup_run("test-run")

    assert not prepared.run_root.exists()
