from __future__ import annotations


from pydantic import ValidationError

from app.schemas import (
    FileRepairProposal,
    PatchApprovalRecord,
    PatchBundle,
)
from app.tools.artifact_tools import (
    artifact_state_update,
    require_run_root,
    write_json_artifact,
)
from app.tools.error_tools import stage_error_result
from app.tools.patch_tools import verify_patch_in_worktree


def _verification_error(
    state: dict,
    *,
    final_status: str,
    error: str,
) -> dict:
    """统一构造不会进入 promotion 的验证失败状态。"""

    return stage_error_result(
        state=state,
        stage="patch_verifier",
        code="PATCH_VERIFICATION_BLOCKED",
        category="agent",
        message=error,
        extra_update={
            "patch_verification_report": None,
            "patch_verification_passed": False,
            "patch_verification_hash": None,
            "final_status": final_status,
        },
    )


def patch_verifier_node(state: dict) -> dict:
    """校验第一次审批绑定，并在隔离 worktree 中验证 patch。"""

    try:
        bundle = PatchBundle.model_validate(state.get("pending_patch"))
        approval = PatchApprovalRecord.model_validate(
            state.get("patch_approval_record")
        )
        proposal = FileRepairProposal.model_validate(
            state.get("file_repair_proposal")
        )
    except ValidationError as exc:
        return _verification_error(
            state,
            final_status="patch_verification_blocked",
            error=f"无效的 patch 验证输入：{exc}",
        )

    # 第一次审批必须绑定当前 patch，而不是只检查 approved 字符串。
    if approval.decision != "approved":
        return _verification_error(
            state,
            final_status="patch_not_approved",
            error="patch 审核决定未获批准",
        )
    if (
        approval.patch_id != bundle.patch_id
        or approval.patch_sha256 != bundle.patch_sha256
    ):
        return _verification_error(
            state,
            final_status="stale_patch_approval",
            error="审批记录与当前 patch 不匹配",
        )

    execution_profile_id = state.get("execution_profile_id")
    execution_profile_fingerprint = state.get(
        "execution_profile_fingerprint"
    )
    if not execution_profile_id or not execution_profile_fingerprint:
        return _verification_error(
            state,
            final_status="patch_verification_blocked",
            error="缺少执行环境配置绑定",
        )

    run_dir = require_run_root(state)
    worktree_path = (
        run_dir
        / "execution"
        / "patch_worktrees"
        / bundle.patch_id
    )

    try:
        report = verify_patch_in_worktree(
            bundle=bundle,
            worktree_path=worktree_path,
            verification_targets=proposal.verification_targets,
            execution_profile_id=str(execution_profile_id),
            execution_profile_fingerprint=str(
                execution_profile_fingerprint
            ),
            run_dir=run_dir,
        )
    except (OSError, ValueError) as exc:
        return _verification_error(
            state,
            final_status="patch_verification_blocked",
            error=str(exc),
        )

    _, report_record = write_json_artifact(
        state=state,
        relative_path="execution/patch_verification_report.json",
        payload=report.model_dump(),
        producer_node="patch_verifier",
    )

    passed = (
        report.status == "behaviorally_verified"
        and report.promotion_allowed is True
    )
    return {
        "patch_verification_report": report.model_dump(),
        "patch_verification_passed": passed,
        "patch_verification_hash": report.verification_sha256,
        "final_status": report.status,
        "error": None if passed else report.summary,
        **artifact_state_update(state, [report_record]),
    }
