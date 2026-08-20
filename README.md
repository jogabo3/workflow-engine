# Workflow Engine

A lightweight Python workflow orchestration engine designed around isolation,
failure recovery, reproducibility, and operational visibility.

## Why This Project Exists

Running one project is straightforward. Running several independent projects in a
reliable and recoverable way is a different problem entirely.

This project addresses a common operational pattern in automation and data work:

- one failed project should not block unrelated work
- project files and configuration must remain isolated
- transient failures should be retryable
- long-running commands need timeouts
- failed workflows should be restartable
- operators need to understand what happened after a run
- workflows may originate from local directories or Git repositories

Workflow Engine explores these concerns through a small, production-minded
orchestration system rather than depending on a large workflow framework.

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

### Current Scope

Workflow state and run reports are currently persisted to the local filesystem.
The architecture keeps these responsibilities separate so alternative backends can
be introduced later without affecting the orchestration model.

The engine is intentionally designed for single-host execution rather than
large-scale distributed scheduling. It prioritizes isolation, reproducibility,
checkpoint recovery, and operational visibility over cluster coordination and
high-throughput scheduling.

## Current CLI and Runtime Behavior

The project currently exposes a minimal command-line interface through the
`workflow-engine` entry point:

```bash
workflow-engine run path/to/workflows.yml
workflow-engine run path/to/workflows.yml --run-id example-run
```

The `run` command loads a manifest, executes each workflow in isolation, writes
state, and prints a structured summary to stdout. The interface is intentionally
small: it supports the execution path directly, but it does not yet provide
commands for listing historical runs, resuming paused work, or managing worker
pools.

## File Layout and Persistence

By default, execution metadata and workflow state are stored on the local
filesystem:

- `.workflow-runs/<run-id>/summary.json` stores the final structured run report
- `.workflow-state/<workflow-name>.json` stores the latest workflow checkpoint state

The reporting layer generates JSON summaries from the run result model, while
the state layer records the most recent workflow status and the last successful
step so that checkpoint recovery can safely resume after a failure.

## Current Implementation Limits

The project models a broader architecture than the runtime currently enforces.
In practice, the implementation is narrower than the schema suggests:

- source types supported by the workspace manager: `local` and `git`
- execution adapter implemented in the runtime: `command`
- the project is designed for local or single-host orchestration rather than
  distributed scheduling
- dependency graphs, concurrency, richer adapters, and pluggable state backends
  remain future work rather than shipped features

The models describe a general design direction, while the current code focuses on
core orchestration fundamentals rather than a full enterprise workflow platform.

## Operational Semantics and Failure Model

The current engine behavior is intentionally simple, but it is important to
understand the exact semantics it enforces:

- a workflow is considered failed when its executed steps do not reach a
  successful terminal state for the configured workflow
- a workflow may be marked `failed` or `partially_succeeded` depending on
  whether execution stopped early, continued past a failure, or completed some
  successful work before encountering an error
- timeouts are surfaced as `timed_out` for the affected step
- retries are attempted up to `retries + 1` total runs for a step, with no
  backoff between attempts yet
- checkpoint resumption is only applied when the previous state indicates a
  failure and a last successful step is known

This design provides a solid foundation for reliable automation, but it remains a
small, single-host orchestration engine rather than a fully featured workflow
platform.

## Engineering Motivation

This project grew from a production orchestration problem involving multiple
independent data projects.

An early implementation allowed project configuration files to share execution
space. Because projects used identically named configuration files, processing
one project could overwrite configuration belonging to another. A failure in
one project could also prevent unrelated downstream projects from executing.

Rather than patching those behaviors individually, this project explores the
underlying platform requirements:

- isolate execution environments
- contain failures
- make retry behavior explicit
- persist execution state
- support safe recovery
- expose enough operational information to diagnose failures

The result is a general workflow engine rather than a solution tied to one
specific data tool.

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
```

## Quick Start

### Requirements

- Python 3.11+
- Git

### Installation

Clone the repository and create a virtual environment:

```bash
python -m venv .venv
```

Activate it and install the project in editable mode:

```bash
python -m pip install -e .
```

### Run the Example

```bash
workflow-engine run configs/workflows.example.yml
```

Or provide your own run identifier:

```bash
workflow-engine run configs/workflows.example.yml --run-id example-run
```

The command executes the configured workflows and prints a structured run
summary. A persisted report is also written to:

```text
.workflow-runs/<run-id>/summary.json
```

## Example Manifest

```yaml
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
```

## Failure Isolation

Workflows execute independently.

A failure in one workflow does not prevent unrelated workflows from running:

```text
project_alpha  SUCCEEDED
project_beta   FAILED
project_gamma  SUCCEEDED
```

This prevents one project failure from unnecessarily increasing the blast radius
of a run.

## Checkpoint Recovery

Workflow state is persisted after execution.

If checkpoint recovery is enabled and a workflow fails after completing earlier
steps, a subsequent run can continue after the last successful step instead of
replaying the entire workflow.

```text
Run 1

extract       SUCCEEDED
transform     SUCCEEDED
publish       FAILED

Run 2

extract       CHECKPOINTED
transform     CHECKPOINTED
publish       SUCCEEDED
```

## Observability

Each run records:

- run identifier
- start and finish timestamps
- total duration
- workflow status
- individual step status
- execution attempts
- exit codes
- step duration

Structured summaries can be consumed by the CLI, CI/CD systems, or external
monitoring tooling.

## Design Principles

### Isolation over shared mutable state

Each workflow receives an isolated workspace. Files from one project cannot
silently overwrite another project's configuration.

### Failure containment

A failed workflow should affect that workflow, not every independent workload in
the run.

### Explicit state

Recovery behavior is based on persisted execution state rather than assumptions
about what previously completed.

### Operability

Execution is only part of the problem. The engine also records what happened,
where execution stopped, and what can safely happen next.

### Small composable components

Configuration loading, workspace management, command execution, state,
summarization, reporting, and orchestration remain separate concerns.

## Development

Run the test suite:

```bash
python -m pytest -v
```

Run linting:

```bash
ruff check src tests
```

Run static type checking:

```bash
mypy src
```

## Project Status

This project is intentionally focused on orchestration fundamentals rather than
competing with mature platforms such as Airflow, Prefect, or Dagster.

## Future Areas of Exploration

- dependency graphs between workflows
- concurrency
- pluggable state backends
- richer execution adapters
- secrets and environment management
- metrics integration


Future areas of exploration may include:

dependency graphs between workflows
concurrency
pluggable state backends
richer execution adapters
secrets and environment management
metrics integration