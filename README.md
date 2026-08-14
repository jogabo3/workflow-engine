# Workflow Engine

A lightweight Python workflow orchestration engine designed around isolation,
failure recovery, reproducibility, and operational visibility.

## Why This Project Exists

Running one project is easy.

Running multiple independent projects reliably introduces a different set of
problems:

- one failed project should not block unrelated work
- project files and configuration must remain isolated
- transient failures should be retryable
- long-running processes need timeouts
- failed workflows should be restartable
- operators need to understand what happened after a run
- workflows may originate from local directories or Git repositories

Workflow Engine explores those problems through a small, production-minded
orchestration system rather than relying on a large orchestration framework.

## Features

- YAML-based workflow configuration
- isolated per-run workspaces
- local and Git repository sources
- multi-workflow execution
- workflow failure isolation
- configurable retries and timeouts
- persistent workflow state
- checkpoint-based recovery
- structured run summaries
- persisted JSON run reports
- command-line interface
- typed configuration using Pydantic
- automated testing with pytest
- static analysis with Ruff and mypy

### Git Authentication

Workflow Engine does not manage Git credentials.

Authentication for private repositories should be provided through the host
environment, such as an existing Git credential helper or CI/CD identity.
Credentials should not be embedded in workflow manifests.

## Architecture

```text
                  YAML Manifest
                       │
                       ▼
                Configuration Layer
                       │
                       ▼
                 WorkflowRunner
                /      |       \
               /       |        \
              ▼        ▼         ▼
       Workspace    Executor    State Store
       Manager                    │
          │                        │
     ┌────┴────┐                   │
     ▼         ▼                   │
   Local      Git              Checkpoints
   Source    Source                 │
     │         │                    │
     └────┬────┘                    │
          ▼                         │
   Isolated Workspace              │
          │                         │
          ▼                         │
      Step Execution ───────────────┘
          │
          ▼
   RunExecutionResult
        /       \
       ▼         ▼
 Run Summary   JSON Reporter
       │            │
       ▼            ▼
 CLI Output   .workflow-runs/

 Quick Start
Requirements
Python 3.11+
Git
Installation

Clone the repository and create a virtual environment:

python -m venv .venv

Activate it and install the project in editable mode:

python -m pip install -e .
Run the Example
workflow-engine run configs/workflows.example.yml

Or provide your own run identifier:

workflow-engine run configs/workflows.example.yml \
  --run-id example-run

The command executes the configured workflows and prints a structured run
summary.

A persisted report is also written to:

.workflow-runs/<run-id>/summary.json
Example Manifest
workflows:
  - name: project_alpha
    source:
      type: local
      location: examples/project_alpha


    adapter: command


    steps:
      - name: run
        command: python run.py


    execution:
      continue_on_failure: false
      retries: 1
      timeout_seconds: 30
      resume_from_checkpoint: true
Failure Isolation

Workflows execute independently.

A failure in one workflow does not prevent unrelated workflows from running:

project_alpha  SUCCEEDED
project_beta   FAILED
project_gamma  SUCCEEDED

This prevents one project failure from unnecessarily increasing the blast
radius of a run.

Checkpoint Recovery

Workflow state is persisted after execution.

If checkpoint recovery is enabled and a workflow fails after completing
earlier steps, a subsequent run can continue after the last successful step
instead of replaying the entire workflow.

Run 1


extract       SUCCEEDED
transform     SUCCEEDED
publish       FAILED


Run 2


extract       CHECKPOINTED
transform     CHECKPOINTED
publish       SUCCEEDED
Observability

Each run records:

run identifier
start and finish timestamps
total duration
workflow status
individual step status
execution attempts
exit codes
step duration

Structured summaries can be consumed by the CLI, CI/CD systems, or external
monitoring tooling.

Design Principles
Isolation over shared mutable state

Each workflow receives an isolated workspace. Files from one project cannot
silently overwrite another project's configuration.

Failure containment

A failed workflow should affect that workflow, not every independent workload
in the run.

Explicit state

Recovery behavior is based on persisted execution state rather than assumptions
about what previously completed.

Operability

Execution is only part of the problem. The engine also records what happened,
where execution stopped, and what can safely happen next.

Small composable components

Configuration loading, workspace management, command execution, state,
summarization, reporting, and orchestration remain separate concerns.

Development

Run the test suite:

python -m pytest -v

Run linting:

ruff check src tests

Run static type checking:

mypy src
Project Status

This project is intentionally focused on orchestration fundamentals rather than
competing with mature platforms such as Airflow, Prefect, or Dagster.

Future areas of exploration may include:

dependency graphs between workflows
concurrency
pluggable state backends
richer execution adapters
secrets and environment management
metrics integration