from __future__ import annotations

from pydantic import ValidationError

from app.schemas import (
    PatchBundle,
    PatchPromotionRecord,
    PatchVerificationReport,
)
from app.tools.action_tools import compute_action_hash
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import stage_error_result
from app.tools.patch_tools import (
    apply_verified_patch_to_source,
    validate_patch_promotion_authorization,
)


def patch_apply_node(state: dict) -> dict:
    try:
        bundle = PatchBundle.model_validate(state.get("pending_patch"))
        report = PatchVerificationReport.model_validate(
            state.get("patch_verification_report")
        )
        promotion = PatchPromotionRecord.model_validate(
            state.get("patch_promotion_record")
        )
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=report,
            promotion=promotion,
            state=state,
            require_promotion=True,
        )
    except (KeyError, ValidationError, ValueError) as exc:
        return stage_error_result(
            state=state,
            stage="patch_apply",
            code="PATCH_APPLY_NOT_AUTHORIZED",
            category="agent",
            message=str(exc),
            extra_update={
                "patch_application_record": None,
                "final_status": "patch_apply_not_authorized",
            },
        )

    run_id = str(state.get("run_id") or state.get("task_id") or "unknown")
    application = apply_verified_patch_to_source(
        bundle,
        owner_run_id=run_id,
    )

    application_path, application_record = write_json_artifact(
        state=state,
        relative_path="execution/patch_application_record.json",
        payload=application.model_dump(),
        producer_node="patch_apply",
    )

    if application.status != "applied":
        payload = {
            "patch_application_record": application.model_dump(),
            "final_status": (
                "patch_apply_manual_intervention"
                if application.status == "manual_intervention"
                else "patch_apply_blocked"
            ),
            **artifact_state_update(state, [application_record]),
        }
        return stage_error_result(
            state={**state, **payload},
            stage="patch_apply",
            code="PATCH_APPLICATION_FAILED",
            category="agent",
            message=application.error or "patch application failed",
            extra_update=payload,
        )

    # 源码变化后，动作身份也发生变化，必须重算 action hash。
    pending_action = dict(state.get("pending_action") or {})
    pending_action["repo_patch_hash"] = bundle.patch_sha256
    new_action_hash = compute_action_hash(pending_action)

    attempts = int(state.get("file_repair_attempt_count", 0)) + 1
    history_entry = {
        "attempt": attempts,
        "patch_id": bundle.patch_id,
        "patch_sha256": bundle.patch_sha256,
        "files": [item.relative_path for item in bundle.files],
        "status": "applied",
        "recovered": application.recovered,
    }

    return {
        "patch_application_record": application.model_dump(),
        "applied_patch_hash": bundle.patch_sha256,
        "file_repair_attempt_count": attempts,
        "file_repair_history": [
            *state.get("file_repair_history", []),
            history_entry,
        ],
        "pending_action": pending_action,
        "pending_action_hash": new_action_hash,

        # 旧审批绑定的是 patch 前的 action hash，源码变化后必须清空。
        "user_approval": None,
        "human_feedback": None,
        "approval_record": None,

        # 旧的环境检查、smoke、debug 和 execution 结果全部失效。
        "preflight_report": None,
        "preflight_passed": False,
        "preflight_report_path": None,
        "smoke_test_report": None,
        "smoke_test_status": None,
        "smoke_test_passed": False,
        "smoke_test_log_path": None,
        "debug_report": None,
        "execution_result": {},
        "execution_log_path": None,
        "log_path": None,
        "final_status": "patch_applied",
        "error": None,
        **artifact_state_update(state, [application_record]),
    }
