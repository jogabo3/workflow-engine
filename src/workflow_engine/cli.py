from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from workflow_engine.config import ConfigurationError, load_manifest
from workflow_engine.runner import WorkflowRunner
from workflow_engine.summary import build_run_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workflow-engine",
        description="Execute configured workflows reliably.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Execute workflows from a manifest.",
    )

    run_parser.add_argument(
        "manifest",
        type=Path,
        help="Path to the workflow manifest.",
    )

    run_parser.add_argument(
        "--run-id",
        help="Optional run identifier.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return _run_command(
            manifest_path=args.manifest,
            run_id=args.run_id,
        )

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_command(
    *,
    manifest_path: Path,
    run_id: str | None,
) -> int:
    try:
        manifest = load_manifest(manifest_path)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}")
        return 2

    runner = WorkflowRunner()
    result = runner.run(
        manifest,
        run_id=run_id,
    )

    print(
        json.dumps(
            build_run_summary(result),
            indent=2,
        )
    )

    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())