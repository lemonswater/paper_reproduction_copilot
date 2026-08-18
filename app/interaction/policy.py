from __future__ import annotations

from typing import Any

from app.command_selection import (
    CommandSelectionIntegrityError,
    CommandSelectionValidationError,
    StaleCommandSelectionError,
    validate_command_selection_response,
)
from app.interaction.schemas import (
    AllowedOperation,
    CommandSelectionDecision,
    Decision,
    DecisionEnvelope,
)
from app.job_runtime.errors import (
    JobConflictError,
)
from app.job_runtime.schemas import JobRecord
from app.schemas import CommandSelectionResponse

NODE_TO_DECISION_KIND = {
    "command_selection": "command_selection",
    "human_review": "action_approval",
    "patch_review": "patch_review",
    "patch_promotion_review": "patch_promotion",
}

DECISION_KIND_TO_NODE = {
    value: key
    for key, value in NODE_TO_DECISION_KIND.items()
}

ALLOWED_REVIEW_DECISIONS = {
    "command_selection": [],
    "action_approval": [
        "approved",
        "rejected",
        "revise",
    ],
    "patch_review": [
        "approved",
        "rejected",
        "revise",
    ],
    "patch_promotion": [
        "approved",
        "rejected",
    ],
}


def allowed_operations(
    record: JobRecord,
) -> list[AllowedOperation]:
    """根据服务端当前状态生成客户端可以执行的操作。"""

    operations: list[AllowedOperation] = []

    if record.status == "waiting_for_input":
        # 当前 Graph 是串行审批图。出现多个不同 interrupt 时不能猜测。
        unique_nodes = sorted(
            set(record.interrupt_nodes)
        )
        if len(unique_nodes) == 1:
            node = unique_nodes[0]
            decision_kind = NODE_TO_DECISION_KIND.get(
                node
            )
            if decision_kind is not None:
                operations.append(
                    AllowedOperation(
                        operation_id=(
                            f"wait:"
                            f"{record.wait_generation}:"
                            f"{node}"
                        ),
                        kind="submit_decision",
                        endpoint=(
                            f"/v1/jobs/{record.job_id}"
                            "/decisions"
                        ),
                        decision_kind=decision_kind,
                        expected_node=node,
                        expected_job_version=(
                            record.version
                        ),
                        expected_wait_generation=(
                            record.wait_generation
                        ),
                        allowed_decisions=(
                            ALLOWED_REVIEW_DECISIONS[
                                decision_kind
                            ]
                        ),
                    )
                )

    if record.status in {
        "queued",
        "running",
        "waiting_for_input",
        "cancelling",
    }:
        operations.append(
            AllowedOperation(
                operation_id=(
                    f"cancel:{record.version}"
                ),
                kind="cancel",
                endpoint=(
                    f"/v1/jobs/{record.job_id}"
                    "/cancel"
                ),
                expected_job_version=record.version,
            )
        )

    if record.status == "reconciliation_required":
        # 只提示，不开放危险的远程自动恢复。
        operations.append(
            AllowedOperation(
                operation_id=(
                    f"reconcile:{record.version}"
                ),
                kind=(
                    "operator_reconciliation_required"
                ),
                expected_job_version=record.version,
                requires_idempotency_key=False,
                detail=(
                    "请由受信任运维人员使用 "
                    "resolve-job 检查外部副作用"
                ),
            )
        )

    if record.status in {"succeeded", "failed"}:
        operations.append(
            AllowedOperation(
                operation_id=(
                    f"rerun-proposal:{record.version}"
                ),
                kind="create_rerun_proposal",
                endpoint="/v1/rerun-proposals",
                expected_job_version=record.version,
                requires_idempotency_key=True,
                detail=(
                    "可基于该终态 Run 的已验证 "
                    "selected command 创建重跑提案；"
                    "新 Job 仍需重新审批。"
                ),
            )
        )

    return operations


def validate_decision(
    *,
    record: JobRecord,
    envelope: DecisionEnvelope,
) -> str:
    """
    校验当前状态并返回真正的 expected_node。

    该函数只验证交互身份，不替代节点内部 action/patch/hash 校验。
    """

    if record.status != "waiting_for_input":
        raise JobConflictError(
            "Job 当前不在 waiting_for_input"
        )

    if record.version != envelope.expected_job_version:
        raise JobConflictError(
            "Job version 已变化："
            f"expected={envelope.expected_job_version}, "
            f"current={record.version}"
        )

    if (
        record.wait_generation
        != envelope.expected_wait_generation
    ):
        raise JobConflictError(
            "interrupt generation 已变化："
            f"expected={envelope.expected_wait_generation}, "
            f"current={record.wait_generation}"
        )

    unique_nodes = sorted(
        set(record.interrupt_nodes)
    )
    if len(unique_nodes) != 1:
        raise JobConflictError(
            "当前 interrupt 节点不唯一，"
            "API 不会猜测应恢复哪个节点："
            f"{unique_nodes}"
        )

    expected_node = DECISION_KIND_TO_NODE.get(
        envelope.decision.kind
    )
    if expected_node is None:
        raise JobConflictError(
            "不支持的 decision kind"
        )

    if unique_nodes[0] != expected_node:
        raise JobConflictError(
            "decision kind 与当前 interrupt 不匹配："
            f"kind={envelope.decision.kind}, "
            f"current_node={unique_nodes[0]}"
        )

    return expected_node


def normalize_decision_against_record(
    *,
    record: JobRecord,
    decision: Decision,
) -> Decision:
    """使用当前服务端 interrupt 规范化需要绑定动态状态的 decision。"""

    if not isinstance(
        decision,
        CommandSelectionDecision,
    ):
        return decision

    command_interrupts = [
        item
        for item in record.interrupts
        if item.node == "command_selection"
    ]
    if len(command_interrupts) != 1:
        raise JobConflictError(
            "当前 command_selection interrupt 不唯一，"
            "请刷新 Job 后重新确认"
        )

    preview = command_interrupts[0].value_preview
    if not isinstance(preview, dict):
        raise JobConflictError(
            "command_selection interrupt preview 缺失"
        )

    raw_commands = preview.get("run_commands")
    preview_hash = preview.get("run_commands_hash")
    if (
        not isinstance(raw_commands, list)
        or not all(
            isinstance(item, dict)
            for item in raw_commands
        )
        or not isinstance(preview_hash, str)
    ):
        raise JobConflictError(
            "command_selection interrupt preview 不完整"
        )

    response = CommandSelectionResponse(
        selected_index=decision.selected_index,
        edits=decision.edits,
        run_commands_hash=decision.run_commands_hash,
    )
    try:
        normalized = validate_command_selection_response(
            run_commands=raw_commands,
            response=response,
            expected_preview_hash=preview_hash,
        )
    except StaleCommandSelectionError as exc:
        raise JobConflictError(str(exc)) from exc
    except CommandSelectionIntegrityError as exc:
        raise JobConflictError(str(exc)) from exc
    except CommandSelectionValidationError as exc:
        raise ValueError(str(exc)) from exc

    return decision.model_copy(
        update={
            "selected_index": normalized.selected_index,
            "edits": normalized.edits,
            "run_commands_hash": normalized.run_commands_hash,
        }
    )


def decision_to_resume_value(
    decision: Decision,
) -> Any:
    """把公开 Decision schema 转成原 interrupt 节点已经接受的值。"""

    payload = decision.model_dump()
    payload.pop("kind", None)
    return payload