from __future__ import annotations

from app.chat.schemas import ChatDraft
from app.evaluation.chat_runner import _operation_availability
from app.interaction.schemas import AllowedOperation


def _approval_operation() -> AllowedOperation:
    return AllowedOperation(
        operation_id="wait:3:human_review",
        kind="submit_decision",
        endpoint="/v1/jobs/job-1/decisions",
        decision_kind="action_approval",
        expected_node="human_review",
        expected_job_version=7,
        expected_wait_generation=3,
        allowed_decisions=["approved", "rejected", "revise"],
    )


def test_read_only_is_not_requested_even_when_capability_exists() -> None:
    draft = ChatDraft(
        answer="当前正在等待审批",
        citation_ids=["job:current"],
        intent="read_only",
    )
    assert _operation_availability(
        draft=draft,
        allowed_operations=[_approval_operation()],
    ) == "not_requested"


def test_matching_operation_is_available() -> None:
    draft = ChatDraft(
        answer="请使用 Decision Card",
        citation_ids=["job:current"],
        intent="operation_request",
        requested_operation={
            "kind": "submit_decision",
            "decision_kind": "action_approval",
        },
    )
    assert _operation_availability(
        draft=draft,
        allowed_operations=[_approval_operation()],
    ) == "available"


def test_wrong_decision_kind_is_unavailable() -> None:
    draft = ChatDraft(
        answer="当前没有该操作",
        citation_ids=["job:current"],
        intent="operation_request",
        requested_operation={
            "kind": "submit_decision",
            "decision_kind": "patch_review",
        },
    )
    assert _operation_availability(
        draft=draft,
        allowed_operations=[_approval_operation()],
    ) == "unavailable"


def test_duplicate_matching_capabilities_are_ambiguous() -> None:
    draft = ChatDraft(
        answer="请刷新页面",
        citation_ids=["job:current"],
        intent="operation_request",
        requested_operation={"kind": "cancel"},
    )
    operations = [
        AllowedOperation(
            operation_id=f"cancel:{index}",
            kind="cancel",
            expected_job_version=7,
        )
        for index in (1, 2)
    ]
    assert _operation_availability(
        draft=draft,
        allowed_operations=operations,
    ) == "ambiguous"
