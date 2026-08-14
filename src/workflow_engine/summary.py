from __future__ import annotations

from workflow_engine.models import RunExecutionResult


def build_run_summary(result: RunExecutionResult) -> dict[str, object]:
    return {
        "run_id": result.run_id,
        "status": "succeeded" if result.succeeded else "failed",
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "duration_seconds": round(result.duration_seconds, 3),
        "workflow_counts": {
            "total": len(result.workflows),
            "succeeded": result.succeeded_count,
            "failed": result.failed_count,
            "partial": result.partial_count,
        },
        "workflows": [
            {
                "name": workflow.workflow_name,
                "status": workflow.status.value,
                "steps": [
                    {
                        "name": step.step_name,
                        "status": step.status.value,
                        "attempts": step.attempts,
                        "exit_code": step.exit_code,
                        "duration_seconds": round(
                            step.duration_seconds,
                            3,
                        ),
                    }
                    for step in workflow.steps
                ],
            }
            for workflow in result.workflows
        ],
    }