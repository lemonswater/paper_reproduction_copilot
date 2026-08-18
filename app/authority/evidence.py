from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.authority.schemas import (
    ExecutionEvidence,
    ExecutionVerificationRecord,
    PatchVerificationEvidence,
    VerificationCheck,
)
from app.schemas import (
    ApprovalRecord,
    ExecutableAction,
    ExecutionResult,
    PatchVerificationReport,
)
from app.tools.action_tools import compute_action_hash


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_sha256(payload: dict[str, Any]) -> str:
    """对 JSON 业务字段计算稳定 Hash。

    所有传入对象必须已经通过 Pydantic 转为 JSON-compatible dict。
    不要在这里使用 repr()，因为对象地址和集合顺序不稳定。
    """

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact_ids(records: list[Any]) -> list[str]:
    """同时兼容 ArtifactRecord 对象和 checkpoint 中的 dict。"""

    result: list[str] = []
    for record in records:
        if hasattr(record, "artifact_id"):
            value = record.artifact_id
        elif isinstance(record, dict):
            value = record.get("artifact_id")
        else:
            value = None
        if value:
            result.append(str(value))
    return sorted(set(result))


def _execution_evidence_payload(
    evidence: ExecutionEvidence,
) -> dict[str, Any]:
    """时间和自身 Hash 不参与内容身份。"""

    return evidence.model_dump(
        exclude={"recorded_at", "evidence_sha256"}
    )


def compute_execution_evidence_hash(
    evidence: ExecutionEvidence,
) -> str:
    return canonical_sha256(
        _execution_evidence_payload(evidence)
    )


def build_execution_evidence(
    *,
    action: ExecutableAction,
    result: ExecutionResult,
    artifact_records: list[Any],
) -> ExecutionEvidence:
    """由 Executor 把 Process Result 投影成不可变证据摘要。"""

    execution_id = result.execution_id or "not-started"
    evidence_identity = canonical_sha256(
        {
            "action_id": action.action_id,
            "execution_id": execution_id,
        }
    )
    draft = ExecutionEvidence(
        # 使用固定长度身份，避免长 action_id 使领域对象越过长度上限。
        evidence_id=f"exec-evidence:{evidence_identity}",
        action_id=action.action_id,
        action_sha256=compute_action_hash(action.model_dump()),
        execution_id=result.execution_id,
        execution_profile_id=result.execution_profile_id,
        execution_profile_fingerprint=(
            action.execution_profile_fingerprint
        ),
        execution_backend=result.execution_backend,
        end_reason=result.end_reason,
        returncode=result.returncode,
        process_record_path=result.process_record_path,
        combined_log_path=result.combined_log_path,
        artifact_ids=_artifact_ids(artifact_records),
        resource_usage=result.resource_usage.model_dump(),
        recorded_at=utc_now(),
        # 先使用合法占位值构造严格模型，随后立刻替换为真实 Hash。
        evidence_sha256="0" * 64,
    )
    return draft.model_copy(
        update={
            "evidence_sha256": compute_execution_evidence_hash(
                draft
            )
        }
    )


def validate_execution_evidence_hash(
    evidence: ExecutionEvidence,
) -> None:
    actual = compute_execution_evidence_hash(evidence)
    if actual != evidence.evidence_sha256:
        raise ValueError("execution evidence hash mismatch")


def _project_final_status(
    result: ExecutionResult,
) -> str:
    """保持 Phase 15/16 已有终态语义，不在 Executor 内投影。"""

    reason = result.end_reason
    if reason == "exited" and result.returncode == 0:
        return "succeeded"
    if reason in {
        "exited",
        "timeout",
        "cpu_limit",
        "memory_limit",
        "process_limit",
        "write_limit",
        "gpu_limit",
    }:
        return "failed"
    if reason in {"cancelled", "interrupted"}:
        return "cancelled"
    if reason == "policy_denied":
        return "policy_blocked"
    if reason == "launch_error":
        return "environment_blocked"
    return "agent_failed"


def _verification_payload(
    record: ExecutionVerificationRecord,
) -> dict[str, Any]:
    return record.model_dump(
        exclude={"verified_at", "verification_sha256"}
    )


def compute_execution_verification_hash(
    record: ExecutionVerificationRecord,
) -> str:
    return canonical_sha256(_verification_payload(record))


def build_execution_verification(
    *,
    action: ExecutableAction,
    result: ExecutionResult,
    evidence: ExecutionEvidence,
    decision: str,
    approval: ApprovalRecord | None,
) -> ExecutionVerificationRecord:
    """Verifier 只根据输入事实构造结论，不启动任何进程。"""

    expected_action_hash = compute_action_hash(
        action.model_dump()
    )
    expected_evidence_hash = compute_execution_evidence_hash(
        evidence
    )

    observed_success = (
        result.end_reason == "exited"
        and result.returncode == 0
    )
    authorization_valid = (
        decision == "not_required"
        or (
            decision == "approved"
            and approval is not None
            and approval.decision == "approved"
            and approval.action_id == action.action_id
            and approval.action_hash == expected_action_hash
        )
    )
    checks = [
        VerificationCheck(
            name="evidence_hash",
            passed=(
                expected_evidence_hash
                == evidence.evidence_sha256
            ),
            detail="ExecutionEvidence 内容身份必须可重算",
        ),
        VerificationCheck(
            name="action_identity",
            passed=(
                evidence.action_id == action.action_id
                and evidence.action_sha256
                == expected_action_hash
            ),
            detail="Evidence 必须绑定当前 ExecutableAction",
        ),
        VerificationCheck(
            name="authorization_identity",
            passed=authorization_valid,
            detail=(
                "高风险 Action 必须绑定 approved record；"
                "低风险 Action 必须明确标记 not_required"
            ),
        ),
        VerificationCheck(
            name="process_identity",
            passed=(
                evidence.execution_id == result.execution_id
                and evidence.end_reason == result.end_reason
                and evidence.returncode == result.returncode
            ),
            detail="Evidence 与 Process Result 必须描述同一次执行",
        ),
        VerificationCheck(
            name="runtime_identity",
            passed=(
                evidence.execution_profile_id
                == action.execution_profile_id
                == result.execution_profile_id
                and evidence.execution_profile_fingerprint
                == action.execution_profile_fingerprint
                and evidence.execution_backend
                == result.execution_backend
            ),
            detail=(
                "Action、Evidence 与 Process Result 必须绑定同一运行环境"
            ),
        ),
        VerificationCheck(
            name="result_consistency",
            passed=(result.ok is observed_success),
            detail=(
                "ok 必须与 end_reason=exited 且 returncode=0 一致"
            ),
        ),
    ]

    identity_valid = all(item.passed for item in checks)
    projected_status = _project_final_status(result)

    if not identity_valid:
        verdict = "inconclusive"
        projected_status = "agent_failed"
        summary = (
            "执行证据身份或结果语义不一致，不能确认执行结论"
        )
    elif observed_success:
        verdict = "verified"
        summary = (
            "执行协议证据完整，受监管进程以 return code 0 退出；"
            "该结论不代表论文科学指标已经复现"
        )
    else:
        verdict = "failed"
        summary = (
            "执行证据完整，但进程未以成功协议状态结束"
        )

    draft = ExecutionVerificationRecord(
        verification_id=(
            f"exec-verification:{evidence.evidence_sha256}"
        ),
        action_id=action.action_id,
        action_sha256=expected_action_hash,
        evidence_id=evidence.evidence_id,
        evidence_sha256=evidence.evidence_sha256,
        verdict=verdict,
        projected_final_status=projected_status,
        checks=checks,
        summary=summary,
        verified_at=utc_now(),
        verification_sha256="0" * 64,
    )
    return draft.model_copy(
        update={
            "verification_sha256": (
                compute_execution_verification_hash(draft)
            )
        }
    )


def _patch_evidence_payload(
    evidence: PatchVerificationEvidence,
) -> dict[str, Any]:
    return evidence.model_dump(
        exclude={"collected_at", "evidence_sha256"}
    )


def compute_patch_evidence_hash(
    evidence: PatchVerificationEvidence,
) -> str:
    return canonical_sha256(_patch_evidence_payload(evidence))


def build_patch_verification_evidence(
    report: PatchVerificationReport,
) -> PatchVerificationEvidence:
    """只提取检查事实，故意丢弃 report 中原有 verdict 字段。"""

    evidence_identity = canonical_sha256(
        {
            "patch_id": report.patch_id,
            "patch_sha256": report.patch_sha256,
            "execution_profile_id": report.execution_profile_id,
            "execution_profile_fingerprint": (
                report.execution_profile_fingerprint
            ),
        }
    )
    draft = PatchVerificationEvidence(
        evidence_id=f"patch-evidence:{evidence_identity}",
        patch_id=report.patch_id,
        patch_sha256=report.patch_sha256,
        execution_profile_id=report.execution_profile_id,
        execution_profile_fingerprint=(
            report.execution_profile_fingerprint
        ),
        execution_backend=report.execution_backend,
        worktree_path=report.worktree_path,
        worktree_diff_sha256=report.worktree_diff_sha256,
        checks=report.checks,
        collected_at=utc_now(),
        evidence_sha256="0" * 64,
    )
    return draft.model_copy(
        update={
            "evidence_sha256": compute_patch_evidence_hash(
                draft
            )
        }
    )


def validate_patch_evidence_hash(
    evidence: PatchVerificationEvidence,
) -> None:
    actual = compute_patch_evidence_hash(evidence)
    if actual != evidence.evidence_sha256:
        raise ValueError("patch verification evidence hash mismatch")
