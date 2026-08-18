from __future__ import annotations

from pydantic import ValidationError

from app.authority.evidence import (
    build_patch_verification_evidence,
)
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


def _patch_execution_error(
    state: dict,
    *,
    final_status: str,
    message: str,
) -> dict:
    """输入或执行环境不足时不会伪造 Patch Evidence。"""

    return stage_error_result(
        state=state,
        stage="patch_verification_executor",
        code="PATCH_VERIFICATION_EXECUTION_BLOCKED",
        category="agent",
        message=message,
        extra_update={
            "patch_verification_evidence": None,
            "final_status": final_status,
        },
    )


def patch_verification_executor_node(state: dict) -> dict:
    """执行 worktree 检查，只输出 Evidence，不输出 promotion verdict。"""

    try:
        bundle = PatchBundle.model_validate(
            state.get("pending_patch")
        )
        approval = PatchApprovalRecord.model_validate(
            state.get("patch_approval_record")
        )
        proposal = FileRepairProposal.model_validate(
            state.get("file_repair_proposal")
        )
    except ValidationError as exc:
        return _patch_execution_error(
            state,
            final_status="patch_verification_blocked",
            message=f"无效的 Patch 验证执行输入：{exc}",
        )

    # Executor 在副作用发生前仍负责最后一次 approval identity 校验。
    if approval.decision != "approved":
        return _patch_execution_error(
            state,
            final_status="patch_not_approved",
            message="Patch 验证审批未获批准",
        )
    if (
        approval.patch_id != bundle.patch_id
        or approval.patch_sha256 != bundle.patch_sha256
    ):
        return _patch_execution_error(
            state,
            final_status="stale_patch_approval",
            message="审批记录与当前 Patch 不匹配",
        )

    profile_id = state.get("execution_profile_id")
    profile_fingerprint = state.get(
        "execution_profile_fingerprint"
    )
    if not profile_id or not profile_fingerprint:
        return _patch_execution_error(
            state,
            final_status="patch_verification_blocked",
            message="缺少执行环境配置绑定",
        )

    run_dir = require_run_root(state)
    worktree_path = (
        run_dir
        / "execution"
        / "patch_worktrees"
        / bundle.patch_id
    )

    try:
        # 旧工具内部仍会计算一个 Report，但本节点不会信任或持久化其中的
        # status/promotion_allowed，只提取原始 checks。
        runner_report = verify_patch_in_worktree(
            bundle=bundle,
            worktree_path=worktree_path,
            verification_targets=proposal.verification_targets,
            execution_profile_id=str(profile_id),
            execution_profile_fingerprint=str(
                profile_fingerprint
            ),
            run_dir=run_dir,
        )
    except (OSError, ValueError) as exc:
        return _patch_execution_error(
            state,
            final_status="patch_verification_blocked",
            message=str(exc),
        )

    evidence = build_patch_verification_evidence(
        runner_report
    )
    _, evidence_record = write_json_artifact(
        state=state,
        relative_path=(
            "execution/patch_verification_evidence.json"
        ),
        payload=evidence.model_dump(),
        producer_node="patch_verification_executor",
    )

    return {
        "patch_verification_evidence": evidence.model_dump(),
        **artifact_state_update(state, [evidence_record]),
    }
