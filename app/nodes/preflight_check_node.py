from __future__ import annotations

from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
    write_text_artifact,
)
from app.tools.error_tools import stage_error_result
from app.tools.exec_tools import register_execution_artifacts
from app.tools.preflight_tools import (
    build_preflight_report,
    render_preflight_report_md,
)


def preflight_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return stage_error_result(
            state=state,
            stage="preflight_check",
            code="PENDING_ACTION_REQUIRED",
            category="agent",
            message="预检前缺少 pending_action",
            extra_update={
                "preflight_report": None,
                "preflight_passed": False,
                "final_status": "blocked",
            },
        )

    run_dir = state.get("run_dir")
    if not run_dir:
        return stage_error_result(
            state=state,
            stage="preflight_check",
            code="RUN_DIR_REQUIRED",
            category="agent",
            message="Preflight 缺少 run_dir",
            extra_update={
                "preflight_passed": False,
                "final_status": "agent_failed",
            },
        )

    action_hash = state.get("pending_action_hash")
    report, probe_results = build_preflight_report(
        pending_action,
        repo_path=state.get("repo_path"),
        action_hash=action_hash,
        run_dir=run_dir,
    )
    probe_records = []
    for result in probe_results:
        probe_records.extend(
            register_execution_artifacts(
                state=state,
                result=result,
                producer_node="preflight_check",
            )
        )

    report_json_path, json_record = write_json_artifact(
        state=state,
        relative_path="planning/preflight_report.json",
        payload=report.model_dump(),
        producer_node="preflight_check",
    )
    _, md_record = write_text_artifact(
        state=state,
        relative_path="planning/preflight_report.md",
        text=render_preflight_report_md(report),
        producer_node="preflight_check",
        media_type="text/markdown",
    )

    payload = {
        "preflight_report": report.model_dump(),
        "preflight_passed": report.ready_to_execute,
        "preflight_report_path": str(report_json_path),
        **artifact_state_update(
            state,
            [*probe_records, json_record, md_record],
        ),
    }
    
    if not state.get("requires_approval") and not state.get("user_approval"):
        payload["user_approval"] = "not_required"

    if report.ready_to_execute:
        return payload

    return stage_error_result(
        state={**state, **payload},
        stage="preflight_check",
        code="PREFLIGHT_BLOCKED",
        category="environment",
        message=report.summary,
        extra_update={
            **payload,
            "final_status": "blocked",
            "last_action_result": {
                "status": "blocked_by_preflight",
                "pending_action": pending_action,
                "blocking_items": report.blocking_items,
            },
        },
    )
