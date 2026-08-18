from __future__ import annotations

from app.tools.action_tools import compute_action_hash
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
    write_text_artifact,
)
from app.tools.error_tools import (
    persist_stage_errors,
    stage_error_result,
)
from app.tools.exec_tools import (
    build_execution_stage_error,
    register_execution_artifacts,
    run_action_safe,
)
from app.tools.smoke_test_tools import (
    build_smoke_test_report,
    derive_smoke_test_action,
    render_smoke_test_report_md,
)


def smoke_test_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return stage_error_result(
            state=state,
            stage="smoke_test",
            code="PENDING_ACTION_REQUIRED",
            category="agent",
            message="冒烟测试前缺少 pending_action",
            extra_update={
                "smoke_test_report": None,
                "smoke_test_status": "blocked",
                "smoke_test_passed": False,
                "final_status": "blocked",
            },
        )

    smoke_action, overrides, summary = derive_smoke_test_action(
        pending_action
    )

    if smoke_action is None:
        # 当前命令不适合被安全缩减，这不算失败，只是跳过。
        report = build_smoke_test_report(
            action=pending_action,
            action_hash=state.get("pending_action_hash"),
            status="skipped",
            summary=summary,
            applied_overrides=[],
            result={},
            log_path=None,
        )

        _, json_record = write_json_artifact(
            state=state,
            relative_path="execution/smoke_test_report.json",
            payload=report.model_dump(),
            producer_node="smoke_test",
        )
        _, md_record = write_text_artifact(
            state=state,
            relative_path="execution/smoke_test_report.md",
            text=render_smoke_test_report_md(report),
            producer_node="smoke_test",
            media_type="text/markdown",
        )

        return {
            "smoke_test_report": report.model_dump(),
            "smoke_test_status": "skipped",
            # 无法安全缩减时允许继续 full executor。
            "smoke_test_passed": True,
            **artifact_state_update(
                state,
                [json_record, md_record],
            ),
        }

    smoke_action_hash = compute_action_hash(smoke_action)
    result = run_action_safe(
        smoke_action,
        state=state,
        stage="smoke_test",
    )
    records = register_execution_artifacts(
        state=state,
        result=result,
        producer_node="smoke_test",
    )
    smoke_log_path = result.get("combined_log_path")

    status = "passed" if result["ok"] else "failed"
    report = build_smoke_test_report(
        action=smoke_action,
        action_hash=smoke_action_hash,
        status=status,
        summary=summary,
        applied_overrides=overrides,
        result=result,
        log_path=smoke_log_path,
    )

    _, json_record = write_json_artifact(
        state=state,
        relative_path="execution/smoke_test_report.json",
        payload=report.model_dump(),
        producer_node="smoke_test",
    )
    _, md_record = write_text_artifact(
        state=state,
        relative_path="execution/smoke_test_report.md",
        text=render_smoke_test_report_md(report),
        producer_node="smoke_test",
        media_type="text/markdown",
    )

    all_records = [
        *records,
        json_record,
        md_record,
    ]
    payload = {
        "active_execution_mode": "smoke",
        "active_execution_id": result.get("execution_id"),
        "active_process_record_path": result.get(
            "process_record_path"
        ),
        "execution_end_reason": result.get("end_reason"),
        "execution_resource_usage": result.get(
            "resource_usage",
            {},
        ),
        "cancellation_requested": result.get("cancelled", False),
        "cancellation_reason": result.get("cancellation_reason"),
        "smoke_test_report": report.model_dump(),
        "smoke_test_status": status,
        "smoke_test_passed": status == "passed",
        "smoke_test_log_path": smoke_log_path,
        **artifact_state_update(state, all_records),
    }

    if status == "passed":
        return payload

    error, final_status = build_execution_stage_error(
        stage="smoke_test",
        result=result,
        log_path=smoke_log_path,
    )
    payload.update(
        {
            "final_status": final_status,
            "last_action_result": {
                "status": final_status,
                "pending_action": smoke_action,
                "returncode": result.get("returncode"),
                "end_reason": result.get("end_reason"),
                "execution_id": result.get("execution_id"),
            },
        }
    )
    if smoke_log_path:
        payload["log_path"] = smoke_log_path

    return {
        **payload,
        **persist_stage_errors(
            state={**state, **payload},
            new_errors=[error],
        ),
        "final_status": final_status,
    }
