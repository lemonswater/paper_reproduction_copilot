from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from langgraph.types import interrupt
from pydantic import ValidationError

from app.schemas import (
    PatchBundle,
    PatchPromotionRecord,
    PatchVerificationReport,
)
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import stage_error_result
from app.tools.patch_tools import validate_patch_promotion_authorization


def _promotion_blocked(
    state: dict,
    *,
    final_status: str,
    error: str,
) -> dict:
    return stage_error_result(
        state=state,
        stage="patch_promotion_review",
        code="PATCH_PROMOTION_BLOCKED",
        category="agent",
        message=error,
        extra_update={
            "patch_promotion_decision": "blocked",
            "patch_promotion_feedback": None,
            "patch_promotion_record": None,
            "final_status": final_status,
        },
    )


def patch_promotion_review_node(state: dict) -> dict:
    try:
        bundle = PatchBundle.model_validate(state.get("pending_patch"))
        report = PatchVerificationReport.model_validate(
            state.get("patch_verification_report")
        )
        computed_hash = validate_patch_promotion_authorization(
            bundle=bundle,
            report=report,
            promotion=None,
            state=state,
            require_promotion=False,
        )
    except (KeyError, ValidationError, ValueError) as exc:
        return _promotion_blocked(
            state,
            final_status="patch_not_authorized_for_promotion",
            error=str(exc),
        )

    response = interrupt(
        {
            "review_type": "patch_promotion_review",
            "patch_id": bundle.patch_id,
            "patch_sha256": bundle.patch_sha256,
            "verification_sha256": computed_hash,
            "verification_status": report.status,
            "worktree_diff_sha256": report.worktree_diff_sha256,
            "checks": [item.model_dump() for item in report.checks],
            "allowed_decisions": ["approved", "rejected"],
        }
    )

    # interrupt 恢复后再次从当前 state 校验，防止暂停期间发生变化。
    try:
        bundle = PatchBundle.model_validate(state.get("pending_patch"))
        report = PatchVerificationReport.model_validate(
            state.get("patch_verification_report")
        )
        computed_hash = validate_patch_promotion_authorization(
            bundle=bundle,
            report=report,
            promotion=None,
            state=state,
            require_promotion=False,
        )
    except (KeyError, ValidationError, ValueError) as exc:
        return _promotion_blocked(
            state,
            final_status="stale_patch_verification",
            error=str(exc),
        )

    if isinstance(response, dict):
        raw_decision = response.get("decision", "rejected")
        feedback = response.get("feedback")
    else:
        raw_decision = response
        feedback = None

    decision = str(raw_decision)
    if decision not in {"approved", "rejected"}:
        decision = "rejected"
        feedback = f"invalid promotion decision: {raw_decision}"

    record = PatchPromotionRecord(
        promotion_id=f"patch_promotion_{uuid4().hex[:12]}",
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        verification_sha256=computed_hash,
        decision=decision,
        reviewer="human",
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        comment=feedback,
    )

    _, record_artifact = write_json_artifact(
        state=state,
        relative_path="planning/patch_promotion_record.json",
        payload=record.model_dump(),
        producer_node="patch_promotion_review",
    )

    return {
        "patch_promotion_decision": decision,
        "patch_promotion_feedback": feedback,
        "patch_promotion_record": record.model_dump(),
        "final_status": (
            "patch_promotion_approved"
            if decision == "approved"
            else "patch_promotion_rejected"
        ),
        "error": None,
        **artifact_state_update(state, [record_artifact]),
    }
