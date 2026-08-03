# src/workflow_engine/models.py

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceType(StrEnum):
    LOCAL = "local"
    GIT = "git"


class AdapterType(StrEnum):
    COMMAND = "command"
    DBT = "dbt"


class WorkflowSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: SourceType
    location: str = Field(min_length=1)
    branch: str | None = None

    @model_validator(mode="after")
    def validate_branch(self) -> "WorkflowSource":
        if self.type == SourceType.LOCAL and self.branch is not None:
            raise ValueError("A local workflow source cannot define a Git branch.")

        return self


class WorkflowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    command: str = Field(min_length=1)


class ExecutionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    continue_on_failure: bool = True
    retries: int = Field(default=0, ge=0, le=10)
    timeout_seconds: int = Field(default=900, gt=0)


class WorkflowConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    source: WorkflowSource
    adapter: AdapterType
    steps: list[WorkflowStep] = Field(min_length=1)
    execution: ExecutionPolicy = Field(default_factory=ExecutionPolicy)

    @model_validator(mode="after")
    def validate_unique_step_names(self) -> "WorkflowConfig":
        step_names = [step.name for step in self.steps]

        if len(step_names) != len(set(step_names)):
            raise ValueError(
                f"Workflow '{self.name}' contains duplicate step names."
            )

        return self


class WorkflowManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflows: list[WorkflowConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_workflow_names(self) -> "WorkflowManifest":
        workflow_names = [workflow.name for workflow in self.workflows]

        if len(workflow_names) != len(set(workflow_names)):
            raise ValueError("Workflow names must be unique.")

        return self