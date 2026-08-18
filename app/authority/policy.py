from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.authority.schemas import (
    AuthorityAuditRecord,
    AuthorityRole,
    NodeAuthorityContract,
)

NodeCallable = Callable[[dict[str, Any]], dict[str, Any]]


class AuthorityViolation(RuntimeError):
    """节点尝试写入当前角色不拥有的 authority 字段。"""


DECISION_FIELDS = {
    "user_approval",
    "approval_record",
    "patch_approval",
    "patch_approval_record",
    "patch_promotion_decision",
    "patch_promotion_record",
}

PROPOSAL_FIELDS = {
    "experiment_plan",
    "run_commands",
    "pending_action",
    "pending_action_hash",
    "repair_proposal",
    "file_repair_proposal",
    "pending_patch",
    "pending_patch_hash",
}

EXECUTION_FIELDS = {
    "execution_result",
    "execution_evidence",
    "active_execution_id",
    "active_process_record_path",
    "execution_end_reason",
    "execution_resource_usage",
    "patch_verification_evidence",
    "patch_application_record",
    "applied_patch_hash",
}

VERIFICATION_FIELDS = {
    "execution_verification",
    "execution_verification_hash",
    "patch_verification_report",
    "patch_verification_passed",
    "patch_verification_hash",
}


ROLE_CONTRACTS: dict[AuthorityRole, NodeAuthorityContract] = {
    "planner": NodeAuthorityContract(
        role="planner",
        capabilities={"read_evidence", "create_proposal"},
        forbidden_output_fields=(
            DECISION_FIELDS
            | EXECUTION_FIELDS
            | VERIFICATION_FIELDS
        ),
    ),
    "executor": NodeAuthorityContract(
        role="executor",
        capabilities={
            "read_evidence",
            "execute_action",
            "apply_repository_change",
        },
        forbidden_output_fields=(
            DECISION_FIELDS
            | PROPOSAL_FIELDS
            | VERIFICATION_FIELDS
        ),
    ),
    "verifier": NodeAuthorityContract(
        role="verifier",
        capabilities={
            "read_evidence",
            "verify_evidence",
            "project_terminal_status",
        },
        forbidden_output_fields=(
            DECISION_FIELDS
            | PROPOSAL_FIELDS
            | EXECUTION_FIELDS
        ),
    ),
}


def _hash_update(update: dict[str, Any]) -> str:
    """只把 Hash 持久化；序列化字符串不会进入 Audit Record。"""

    payload = json.dumps(
        update,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_role_update(
    *,
    role: AuthorityRole,
    update: dict[str, Any],
) -> None:
    contract = ROLE_CONTRACTS[role]
    forbidden = sorted(
        set(update).intersection(
            contract.forbidden_output_fields
        )
    )
    if forbidden:
        raise AuthorityViolation(
            f"{role} attempted forbidden state writes: "
            + ", ".join(forbidden)
        )

    # Planner 可以报告"没有 Action"或输入/规划失败，但不能把建议直接
    # 投影为执行成功。终态 succeeded 只能来自 Verifier。
    if role == "planner" and update.get("final_status") == "succeeded":
        raise AuthorityViolation(
            "planner cannot project succeeded final_status"
        )

    # Executor 可以在"执行准入失败"时返回 terminal StageError；但一旦已经
    # 产出正常执行 Evidence，就不能同时自证 final_status。
    if role == "executor" and "final_status" in update:
        if update.get("final_status") == "succeeded":
            raise AuthorityViolation(
                "executor cannot project succeeded final_status"
            )
        produced_evidence = bool(
            {
                "execution_evidence",
                "patch_verification_evidence",
            }.intersection(update)
        )
        if produced_evidence:
            raise AuthorityViolation(
                "executor cannot write final_status with evidence"
            )


def build_authority_audit_record(
    *,
    node_name: str,
    role: AuthorityRole,
    update: dict[str, Any],
) -> AuthorityAuditRecord:
    contract = ROLE_CONTRACTS[role]
    return AuthorityAuditRecord(
        node_name=node_name,
        role=role,
        capabilities=sorted(contract.capabilities),
        output_fields=sorted(update),
        output_sha256=_hash_update(update),
        recorded_at=datetime.now(timezone.utc).isoformat(),
    )


def role_guarded_node(
    *,
    node_name: str,
    role: AuthorityRole,
    node: NodeCallable,
) -> NodeCallable:
    """包装 LangGraph Node，在 update 进入 State 前执行 authority 校验。"""

    def invoke(state: dict[str, Any]) -> dict[str, Any]:
        update = node(state)
        if not isinstance(update, dict):
            raise AuthorityViolation(
                f"{node_name} must return a dict update"
            )

        validate_role_update(role=role, update=update)
        record = build_authority_audit_record(
            node_name=node_name,
            role=role,
            update=update,
        )

        # 当前 Graph 是线性的，第一版直接保留完整审计列表。后续如果数量增长，
        # 应改为 Run-native Artifact，而不是无限扩大 Checkpoint。
        history = list(
            state.get("authority_audit_records", [])
        )
        return {
            **update,
            "authority_audit_records": [
                *history,
                record.model_dump(),
            ],
        }

    return invoke
