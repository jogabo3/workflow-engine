# tests/test_config.py

from pathlib import Path

import pytest

from workflow_engine.config import ConfigurationError, load_manifest
from workflow_engine.models import AdapterType, SourceType


def write_config(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "workflows.yml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def test_loads_valid_manifest(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
workflows:
  - name: project_alpha
    source:
      type: local
      location: examples/project_alpha
    adapter: command
    steps:
      - name: run
        command: python run.py
""",
    )

    manifest = load_manifest(config_path)
    workflow = manifest.workflows[0]

    assert workflow.name == "project_alpha"
    assert workflow.source.type == SourceType.LOCAL
    assert workflow.adapter == AdapterType.COMMAND
    assert workflow.execution.continue_on_failure is True


def test_rejects_duplicate_workflow_names(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
workflows:
  - name: duplicate
    source:
      type: local
      location: examples/one
    adapter: command
    steps:
      - name: run
        command: python run.py

  - name: duplicate
    source:
      type: local
      location: examples/two
    adapter: command
    steps:
      - name: run
        command: python run.py
""",
    )

    with pytest.raises(ConfigurationError, match="Workflow names must be unique"):
        load_manifest(config_path)


def test_rejects_unknown_fields(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
workflows:
  - name: project_alpha
    source:
      type: local
      location: examples/project_alpha
    adapter: command
    target_name: accidental_field
    steps:
      - name: run
        command: python run.py
""",
    )

    with pytest.raises(ConfigurationError, match="target_name"):
        load_manifest(config_path)


def test_rejects_duplicate_step_names(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
workflows:
  - name: project_alpha
    source:
      type: local
      location: examples/project_alpha
    adapter: command
    steps:
      - name: run
        command: python first.py
      - name: run
        command: python second.py
""",
    )

    with pytest.raises(ConfigurationError, match="duplicate step names"):
        load_manifest(config_path)