from pathlib import Path

from workflow_engine.models import (
    AdapterType,
    ExecutionPolicy,
    RunExecutionResult,
    SourceType,
    WorkflowConfig,
    WorkflowExecutionStatus,
    WorkflowManifest,
    WorkflowSource,
    WorkflowStep,
)
from workflow_engine.runner import WorkflowRunner
from workflow_engine.workspace import WorkspaceManager


def create_project(
    root: Path,
    name: str,
    script_contents: str,
) -> Path:
    project_dir = root / name
    project_dir.mkdir()

    (project_dir / "run.py").write_text(
        script_contents,
        encoding="utf-8",
    )

    return project_dir


def build_workflow(
    *,
    name: str,
    source: Path,
    continue_on_failure: bool = True,
    steps: list[WorkflowStep] | None = None,
) -> WorkflowConfig:
    return WorkflowConfig(
        name=name,
        source=WorkflowSource(
            type=SourceType.LOCAL,
            location=str(source),
        ),
        adapter=AdapterType.COMMAND,
        steps=steps
        or [
            WorkflowStep(
                name="run",
                command="python run.py",
            )
        ],
        execution=ExecutionPolicy(
            continue_on_failure=continue_on_failure,
            retries=0,
            timeout_seconds=10,
        ),
    )


def test_runs_multiple_workflows(tmp_path: Path) -> None:
    alpha_source = create_project(
        tmp_path,
        "alpha_source",
        'print("alpha complete")',
    )

    beta_source = create_project(
        tmp_path,
        "beta_source",
        'print("beta complete")',
    )

    manifest = WorkflowManifest(
        workflows=[
            build_workflow(
                name="alpha",
                source=alpha_source,
            ),
            build_workflow(
                name="beta",
                source=beta_source,
            ),
        ]
    )

    runner = WorkflowRunner(
        workspace_manager=WorkspaceManager(tmp_path / "runs")
    )

    result = runner.run(
        manifest,
        run_id="test-run",
    )

    assert isinstance(result, RunExecutionResult)
    assert len(result.workflows) == 2
    assert result.succeeded is True

    assert result.workflows[0].status == (
        WorkflowExecutionStatus.SUCCEEDED
    )
    assert result.workflows[1].status == (
        WorkflowExecutionStatus.SUCCEEDED
    )


def test_failed_workflow_does_not_block_next_workflow(
    tmp_path: Path,
) -> None:
    failing_source = create_project(
        tmp_path,
        "failing_source",
        """
raise SystemExit(1)
""".strip(),
    )

    successful_source = create_project(
        tmp_path,
        "successful_source",
        """
from pathlib import Path

Path("completed.txt").write_text(
    "success",
    encoding="utf-8",
)
""".strip(),
    )

    manifest = WorkflowManifest(
        workflows=[
            build_workflow(
                name="failing_project",
                source=failing_source,
            ),
            build_workflow(
                name="successful_project",
                source=successful_source,
            ),
        ]
    )

    workspace_manager = WorkspaceManager(tmp_path / "runs")

    runner = WorkflowRunner(
        workspace_manager=workspace_manager
    )

    result = runner.run(
        manifest,
        run_id="failure-isolation-test",
    )

    assert result.workflows[0].status == (
        WorkflowExecutionStatus.FAILED
    )

    assert result.workflows[1].status == (
        WorkflowExecutionStatus.SUCCEEDED
    )

    successful_output = (
        tmp_path
        / "runs"
        / "failure-isolation-test"
        / "successful_project"
        / "completed.txt"
    )

    assert successful_output.exists()


def test_stops_remaining_steps_when_continue_on_failure_false(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "fail.py").write_text(
        "raise SystemExit(1)",
        encoding="utf-8",
    )

    (source / "should_not_run.py").write_text(
        """
from pathlib import Path

Path("unexpected.txt").write_text(
    "this should not exist",
    encoding="utf-8",
)
""".strip(),
        encoding="utf-8",
    )

    workflow = build_workflow(
        name="stop_on_failure",
        source=source,
        continue_on_failure=False,
        steps=[
            WorkflowStep(
                name="fail",
                command="python fail.py",
            ),
            WorkflowStep(
                name="next",
                command="python should_not_run.py",
            ),
        ],
    )

    runner = WorkflowRunner(
        workspace_manager=WorkspaceManager(tmp_path / "runs")
    )

    result = runner.run(
        WorkflowManifest(workflows=[workflow]),
        run_id="stop-test",
    )

    workflow_result = result.workflows[0]

    assert workflow_result.status == WorkflowExecutionStatus.FAILED
    assert len(workflow_result.steps) == 1

    unexpected_file = (
        tmp_path
        / "runs"
        / "stop-test"
        / "stop_on_failure"
        / "unexpected.txt"
    )

    assert not unexpected_file.exists()


def test_continue_on_failure_runs_remaining_steps(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "fail.py").write_text(
        "raise SystemExit(1)",
        encoding="utf-8",
    )

    (source / "success.py").write_text(
        """
from pathlib import Path

Path("continued.txt").write_text(
    "continued",
    encoding="utf-8",
)
""".strip(),
        encoding="utf-8",
    )

    workflow = build_workflow(
        name="continue_on_failure",
        source=source,
        continue_on_failure=True,
        steps=[
            WorkflowStep(
                name="fail",
                command="python fail.py",
            ),
            WorkflowStep(
                name="continue",
                command="python success.py",
            ),
        ],
    )

    runner = WorkflowRunner(
        workspace_manager=WorkspaceManager(tmp_path / "runs")
    )

    result = runner.run(
        WorkflowManifest(workflows=[workflow]),
        run_id="continue-test",
    )

    workflow_result = result.workflows[0]

    assert workflow_result.status == (
        WorkflowExecutionStatus.PARTIALLY_SUCCEEDED
    )

    assert len(workflow_result.steps) == 2

    continued_file = (
        tmp_path
        / "runs"
        / "continue-test"
        / "continue_on_failure"
        / "continued.txt"
    )

    assert continued_file.exists()

def test_middle_workflow_failure_does_not_block_following_workflow(
    tmp_path: Path,
) -> None:
    alpha_source = create_project(
        tmp_path,
        "alpha_source",
        'print("alpha complete")',
    )

    beta_source = create_project(
        tmp_path,
        "beta_source",
        "raise SystemExit(1)",
    )

    gamma_source = create_project(
        tmp_path,
        "gamma_source",
        """
from pathlib import Path

Path("gamma_completed.txt").write_text(
    "success",
    encoding="utf-8",
)
""".strip(),
    )

    manifest = WorkflowManifest(
        workflows=[
            build_workflow(
                name="alpha",
                source=alpha_source,
            ),
            build_workflow(
                name="beta",
                source=beta_source,
            ),
            build_workflow(
                name="gamma",
                source=gamma_source,
            ),
        ]
    )

    runner = WorkflowRunner(
        workspace_manager=WorkspaceManager(tmp_path / "runs")
    )

    result = runner.run(
        manifest,
        run_id="three-project-test",
    )

    assert result.workflows[0].status == WorkflowExecutionStatus.SUCCEEDED
    assert result.workflows[1].status == WorkflowExecutionStatus.FAILED
    assert result.workflows[2].status == WorkflowExecutionStatus.SUCCEEDED

    gamma_output = (
        tmp_path
        / "runs"
        / "three-project-test"
        / "gamma"
        / "gamma_completed.txt"
    )

    assert gamma_output.exists()

from workflow_engine.state import JsonStateStore


def test_successful_workflow_persists_state(
    tmp_path: Path,
) -> None:
    source = create_project(
        tmp_path,
        "source",
        'print("complete")',
    )

    workflow = build_workflow(
        name="alpha",
        source=source,
    )

    state_store = JsonStateStore(tmp_path / "state")

    runner = WorkflowRunner(
        workspace_manager=WorkspaceManager(tmp_path / "runs"),
        state_store=state_store,
    )

    runner.run(
        WorkflowManifest(workflows=[workflow]),
        run_id="state-test",
    )

    state = state_store.get("alpha")

    assert state.last_run_id == "state-test"
    assert state.last_status == WorkflowExecutionStatus.SUCCEEDED
    assert state.last_successful_step == "run"
    assert state.last_error is None

def test_resume_starts_after_last_successful_step(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    (source / "step_one.py").write_text(
        """
from pathlib import Path

counter = Path("step_one_count.txt")
count = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(count))
""".strip(),
        encoding="utf-8",
    )

    (source / "step_two.py").write_text(
        """
from pathlib import Path

marker = Path("allow_success.txt")

if not marker.exists():
    raise SystemExit(1)

Path("step_two_complete.txt").write_text(
    "done",
    encoding="utf-8",
)
""".strip(),
        encoding="utf-8",
    )

    workflow = WorkflowConfig(
        name="resume_test",
        source=WorkflowSource(
            type=SourceType.LOCAL,
            location=str(source),
        ),
        adapter=AdapterType.COMMAND,
        steps=[
            WorkflowStep(
                name="step_one",
                command="python step_one.py",
            ),
            WorkflowStep(
                name="step_two",
                command="python step_two.py",
            ),
        ],
        execution=ExecutionPolicy(
            continue_on_failure=False,
            retries=0,
            timeout_seconds=10,
            resume_from_checkpoint=True,
        ),
    )

    state_store = JsonStateStore(tmp_path / "state")
    workspace_manager = WorkspaceManager(tmp_path / "runs")

    runner = WorkflowRunner(
        workspace_manager=workspace_manager,
        state_store=state_store,
    )

    first_result = runner.run(
        WorkflowManifest(workflows=[workflow]),
        run_id="first-run",
    )

    assert first_result.workflows[0].status == WorkflowExecutionStatus.FAILED

    state = state_store.get("resume_test")
    assert state.last_successful_step == "step_one"

    (source / "allow_success.txt").write_text(
        "yes",
        encoding="utf-8",
    )

    second_result = runner.run(
        WorkflowManifest(workflows=[workflow]),
        run_id="second-run",
    )

    assert second_result.workflows[0].status == WorkflowExecutionStatus.SUCCEEDED

from workflow_engine.reporting import JsonRunReporter


def test_runner_writes_run_report(tmp_path: Path) -> None:
    source = create_project(
        tmp_path,
        "source",
        'print("complete")',
    )

    workflow = build_workflow(
        name="alpha",
        source=source,
    )

    reporter = JsonRunReporter(tmp_path / "reports")

    runner = WorkflowRunner(
        workspace_manager=WorkspaceManager(tmp_path / "runs"),
        state_store=JsonStateStore(tmp_path / "state"),
        reporter=reporter,
    )

    runner.run(
        WorkflowManifest(workflows=[workflow]),
        run_id="report-test",
    )

    report_path = (
        tmp_path
        / "reports"
        / "report-test"
        / "summary.json"
    )

    assert report_path.exists()

def test_runner_reports_failed_workflow(tmp_path: Path) -> None:
    source = create_project(
        tmp_path,
        "source",
        "raise SystemExit(1)",
    )

    workflow = build_workflow(
        name="alpha",
        source=source,
    )

    reporter = JsonRunReporter(tmp_path / "reports")

    runner = WorkflowRunner(
        workspace_manager=WorkspaceManager(tmp_path / "runs"),
        state_store=JsonStateStore(tmp_path / "state"),
        reporter=reporter,
    )

    result = runner.run(
        WorkflowManifest(workflows=[workflow]),
        run_id="failed-report-test",
    )

    report_path = (
        tmp_path
        / "reports"
        / "failed-report-test"
        / "summary.json"
    )

    assert report_path.exists()
    assert result.succeeded is False    


