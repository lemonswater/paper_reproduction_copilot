from __future__ import annotations

import pytest

from app.authority.policy import (
    AuthorityViolation,
    role_guarded_node,
    validate_role_update,
)


def test_planner_cannot_write_execution_result() -> None:
    with pytest.raises(
        AuthorityViolation,
        match="execution_result",
    ):
        validate_role_update(
            role="planner",
            update={"execution_result": {"ok": True}},
        )


def test_executor_cannot_write_verification() -> None:
    with pytest.raises(
        AuthorityViolation,
        match="execution_verification",
    ):
        validate_role_update(
            role="executor",
            update={
                "execution_verification": {
                    "verdict": "verified"
                }
            },
        )


def test_executor_cannot_self_certify_with_evidence() -> None:
    with pytest.raises(
        AuthorityViolation,
        match="final_status",
    ):
        validate_role_update(
            role="executor",
            update={
                "execution_evidence": {"evidence_id": "x"},
                "final_status": "succeeded",
            },
        )


def test_planner_and_executor_cannot_claim_success() -> None:
    with pytest.raises(AuthorityViolation, match="planner"):
        validate_role_update(
            role="planner",
            update={"final_status": "succeeded"},
        )

    with pytest.raises(AuthorityViolation, match="executor"):
        validate_role_update(
            role="executor",
            update={"final_status": "succeeded"},
        )


def test_verifier_cannot_replace_action() -> None:
    with pytest.raises(
        AuthorityViolation,
        match="pending_action",
    ):
        validate_role_update(
            role="verifier",
            update={
                "pending_action": {
                    "program": "python",
                    "args": ["different.py"],
                }
            },
        )


def test_valid_planner_update_writes_hash_only_audit() -> None:
    wrapped = role_guarded_node(
        node_name="planner-fixture",
        role="planner",
        node=lambda _state: {
            "pending_action": {
                "action_id": "proposal-only"
            }
        },
    )

    update = wrapped({"authority_audit_records": []})

    assert update["pending_action"]["action_id"] == (
        "proposal-only"
    )
    record = update["authority_audit_records"][0]
    assert record["role"] == "planner"
    assert record["output_fields"] == ["pending_action"]
    assert len(record["output_sha256"]) == 64
    # Audit 不复制完整 Proposal。
    assert "proposal-only" not in str(record)
