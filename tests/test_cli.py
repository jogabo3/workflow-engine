from pathlib import Path

from workflow_engine.cli import build_parser
from workflow_engine.cli import main



def test_run_command_parses_manifest() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "run",
            "configs/workflows.yml",
            "--run-id",
            "test-run",
        ]
    )

    assert args.command == "run"
    assert args.manifest == Path("configs/workflows.yml")
    assert args.run_id == "test-run"

def test_invalid_manifest_returns_configuration_exit_code(
    tmp_path: Path,
) -> None:
    missing_manifest = tmp_path / "missing.yml"

    exit_code = main(
        [
            "run",
            str(missing_manifest),
        ]
    )

    assert exit_code == 2