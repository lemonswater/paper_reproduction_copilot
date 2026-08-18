from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from langgraph.types import interrupt

from app.schemas import PatchApprovalRecord, PatchBundle
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import stage_error_result
from app.tools.patch_tools import validate_patch_bundle


def patch_review_node(state: dict) -> dict:
    bundle = PatchBundle.model_validate(state.get("pending_patch"))

    # interrupt 前先确认磁盘上的 diff 与 state 中 hash 一致。
    try:
        validate_patch_bundle(bundle)
    except (OSError, ValueError) as exc:
        return stage_error_result(
            state=state,
            stage="patch_review",
            code="STALE_PATCH_BEFORE_REVIEW",
            category="agent",
            message=str(exc),
            extra_update={
                "patch_approval": "blocked",
                "patch_approval_record": None,
                "final_status": "stale_patch_before_review",
            },
        )

    patch_text = Path(bundle.patch_path).read_text(encoding="utf-8")
    response = interrupt(
        {
            "review_type": "patch_review",
            "message": "请在隔离验证前审核这份精确补丁。",
            "patch_id": bundle.patch_id,
            "patch_sha256": bundle.patch_sha256,
            "base_git_commit": bundle.base_git_commit,
            "files": [item.model_dump() for item in bundle.files],
            "patch_path": bundle.patch_path,
            # 终端可直接展示，但限制预览大小，完整内容仍以文件为准。
            "patch_preview": patch_text[:12000],
            "allowed_decisions": ["approved", "rejected", "revise"],
        }
    )

    raw_decision = str(response.get("decision", "rejected"))
    decision = raw_decision
    feedback = response.get("feedback")
    if decision not in {"approved", "rejected", "revise"}:
        decision = "rejected"
        feedback = f"无效的补丁审核决定：{raw_decision}"

    # 从 interrupt 恢复后再检查一次，避免暂停期间 patch 被替换。
    try:
        validate_patch_bundle(bundle)
    except (OSError, ValueError) as exc:
        return stage_error_result(
            state=state,
            stage="patch_review",
            code="STALE_PATCH_AFTER_REVIEW",
            category="agent",
            message=str(exc),
            extra_update={
                "patch_approval": "blocked",
                "patch_approval_record": None,
                "final_status": "stale_patch_after_review",
            },
        )

    record = PatchApprovalRecord(
        approval_id=f"patch_approval_{uuid4().hex[:12]}",
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        decision=decision,
        reviewer="human",
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        comment=feedback,
    )

    _, record_artifact = write_json_artifact(
        state=state,
        relative_path="planning/patch_approval_record.json",
        payload=record.model_dump(),
        producer_node="patch_review",
    )

    return {
        "patch_approval": decision,
        "patch_feedback": feedback,
        "patch_approval_record": record.model_dump(),
        **artifact_state_update(state, [record_artifact]),
    }
