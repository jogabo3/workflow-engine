# src/workflow_engine/config.py

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from workflow_engine.models import WorkflowManifest


class ConfigurationError(ValueError):
    """Raised when a workflow configuration cannot be loaded or validated."""


def load_manifest(path: str | Path) -> WorkflowManifest:
    config_path = Path(path)

    if not config_path.exists():
        raise ConfigurationError(
            f"Workflow configuration does not exist: {config_path}"
        )

    if not config_path.is_file():
        raise ConfigurationError(
            f"Workflow configuration is not a file: {config_path}"
        )

    try:
        with config_path.open("r", encoding="utf-8") as file:
            raw_config: Any = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Invalid YAML in {config_path}: {exc}"
        ) from exc
    except OSError as exc:
        raise ConfigurationError(
            f"Unable to read {config_path}: {exc}"
        ) from exc

    if raw_config is None:
        raise ConfigurationError(
            f"Workflow configuration is empty: {config_path}"
        )

    try:
        return WorkflowManifest.model_validate(raw_config)
    except ValidationError as exc:
        raise ConfigurationError(
            f"Invalid workflow configuration in {config_path}:\n{exc}"
        ) from exc