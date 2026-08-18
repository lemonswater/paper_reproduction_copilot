from __future__ import annotations

from datetime import datetime, timezone

from pydantic import ValidationError

from app.authority.evidence import (
    validate_patch_evidence_hash,
)
from app.authority.schemas import PatchVerificationEvidence
from app.schemas import (
    PatchApprovalRecord,
    PatchBundle,
    PatchVerificationReport,
)
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import stage_error_result
from app.tools.patch_tools import (
    compute_verification_hash,
    summarize_patch_verification,
)


def _patch_verdict_error(
    state: dict,
    *,
    final_status: str,
    message: str,
) -> dict:
    return stage_error_result(
        state=state,
        stage="patch_verdict",
        code="PATCH_VERDICT_INCONCLUSIVE",
        category="agent",
        message=message,
        extra_update={
            "patch_verification_report": None,
            "patch_verification_passed": False,
            "patch_verification_hash": None,
            "final_status": final_status,
        },
    )


def patch_verdict_node(state: dict) -> dict:
    """依据 Patch Evidence 重算 verdict；绝不调用 worktree Runner。"""

    try:
        bundle = PatchBundle.model_validate(
            state.get("pending_patch")
        )
        approval = PatchApprovalRecord.model_validate(
            state.get("patch_approval_record")
        )
        evidence = PatchVerificationEvidence.model_validate(
            state.get("patch_verification_evidence")
        )
    except ValidationError as exc:
        return _patch_verdict_error(
            state,
            final_status="patch_verification_inconclusive",
            message=f"Patch verdict 输入无效：{exc}",
        )

    try:
        validate_patch_evidence_hash(evidence)
    except ValueError as exc:
        return _patch_verdict_error(
            state,
            final_status="patch_verification_inconclusive",
            message=str(exc),
        )

    identities_match = (
        evidence.patch_id == bundle.patch_id
        and evidence.patch_sha256 == bundle.patch_sha256
        and approval.decision == "approved"
        and approval.patch_id == bundle.patch_id
        and approval.patch_sha256 == bundle.patch_sha256
        and evidence.execution_profile_id
        == state.get("execution_profile_id")
        and evidence.execution_profile_fingerprint
        == state.get("execution_profile_fingerprint")
    )
    if not identities_match:
        return _patch_verdict_error(
            state,
            final_status="patch_verification_inconclusive",
            message=(
                "Patch、审批、执行环境或 Evidence identity 不一致"
            ),
        )

    (
        status,
        promotion_allowed,
        structural_checks_passed,
        behavioral_checks_run,
        behavioral_checks_passed,
    ) = summarize_patch_verification(evidence.checks)

    if status == "behaviorally_verified":
        summary = "补丁已通过结构检查和至少一项行为检查"
    elif status == "structurally_valid":
        summary = "补丁结构检查通过，但没有可信行为检查"
    elif status == "failed":
        summary = "补丁的一项或多项验证检查失败"
    else:
        summary = "补丁验证证据不足，无法形成可提升结论"

    draft = PatchVerificationReport(
        patch_id=evidence.patch_id,
        patch_sha256=evidence.patch_sha256,
        execution_profile_id=evidence.execution_profile_id,
        execution_profile_fingerprint=(
            evidence.execution_profile_fingerprint
        ),
        execution_backend=evidence.execution_backend,
        status=status,
        promotion_allowed=promotion_allowed,
        structural_checks_passed=structural_checks_passed,
        behavioral_checks_run=behavioral_checks_run,
        behavioral_checks_passed=behavioral_checks_passed,
        worktree_path=evidence.worktree_path,
        worktree_diff_sha256=evidence.worktree_diff_sha256,
        checks=evidence.checks,
        summary=summary,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    report = draft.model_copy(
        update={
            "verification_sha256": compute_verification_hash(
                draft
            )
        }
    )

    _, report_record = write_json_artifact(
        state=state,
        relative_path=(
            "execution/patch_verification_report.json"
        ),
        payload=report.model_dump(),
        producer_node="patch_verdict",
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
