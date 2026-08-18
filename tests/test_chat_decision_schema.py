from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.chat.schemas import ChatDraft


def test_read_only_draft_cannot_carry_operation() -> None:
    with pytest.raises(ValidationError):
        ChatDraft(
            answer="只读回答",
            citation_ids=["job:current"],
            intent="read_only",
            requested_operation={"kind": "cancel"},
        )


def test_operation_request_requires_operation() -> None:
    with pytest.raises(ValidationError):
        ChatDraft(
            answer="请使用审批卡片",
            citation_ids=["job:current"],
            intent="operation_request",
        )


def test_submit_decision_requires_decision_kind() -> None:
    with pytest.raises(ValidationError):
        ChatDraft(
            answer="请使用审批卡片",
            citation_ids=["job:current"],
            intent="operation_request",
            requested_operation={"kind": "submit_decision"},
        )


def test_cancel_cannot_carry_decision_kind() -> None:
    with pytest.raises(ValidationError):
        ChatDraft(
            answer="请使用取消入口",
            citation_ids=["job:current"],
            intent="operation_request",
            requested_operation={
                "kind": "cancel",
                "decision_kind": "action_approval",
            },
        )


def test_operation_request_never_contains_execution_identity() -> None:
    schema = ChatDraft.model_json_schema()
    serialized = str(schema)
    for forbidden in (
        "operation_id",
        "expected_job_version",
        "expected_wait_generation",
        "action_hash",
    ):
        assert forbidden not in serialized
