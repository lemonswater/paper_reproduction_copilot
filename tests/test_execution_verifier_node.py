from __future__ import annotations

from app.authority.evidence import build_execution_evidence
from app.nodes.execution_verifier_node import (
    execution_verifier_node,
)
from app.schemas import ExecutableAction, ExecutionResult


def _action() -> ExecutableAction:
    return ExecutableAction(
        action_id="action-verifier-test",
        program="python",
        args=["train.py"],
        cwd="/workspace/repo",
        source="script",
        reason="verify execution authority",
        execution_profile_id="local-test",
        execution_profile_fingerprint="profile-test",
    )


def _result(*, ok: bool) -> ExecutionResult:
    return ExecutionResult(
        ok=ok,
        returncode=0 if ok else 2,
        end_reason="exited",
        stderr="" if ok else "RuntimeError: failure",
        execution_id="exec-verifier-test",
        execution_profile_id="local-test",
        execution_backend="local",
        combined_log_path="/run/combined.log",
    )


def _state(run_state: dict, *, ok: bool) -> dict:
    action = _action()
    result = _result(ok=ok)
    evidence = build_execution_evidence(
        action=action,
        result=result,
        artifact_records=[],
    )
    return {
        **run_state,
        "pending_action": action.model_dump(),
        "user_approval": "not_required",
        "execution_result": result.model_dump(),
        "execution_evidence": evidence.model_dump(),
        "last_action_result": {
            "status": "evidence_recorded"
        },
    }


def test_execution_verifier_projects_success(run_state) -> None:
    result = execution_verifier_node(
        _state(run_state, ok=True)
    )

    assert result["final_status"] == "succeeded"
    assert result["execution_verification"]["verdict"] == (
        "verified"
    )
    assert result["execution_verification"]["claim_scope"] == (
        "execution_protocol"
    )
    assert result["last_action_result"]["status"] == (
        "succeeded"
    )


def test_execution_verifier_classifies_nonzero_exit(
    run_state,
) -> None:
    result = execution_verifier_node(
        _state(run_state, ok=False)
    )

    assert result["final_status"] == "failed"
    assert result["execution_verification"]["verdict"] == (
        "failed"
    )
    assert result["active_stage_error"]["category"] == (
        "paper_program"
    )
    assert result["active_stage_error"]["terminal"] is False


def test_execution_verifier_fails_closed_on_tampering(
    run_state,
) -> None:
    state = _state(run_state, ok=True)
    state["execution_evidence"]["returncode"] = 99

    result = execution_verifier_node(state)

    assert result["final_status"] == "agent_failed"
    assert result["execution_verification"]["verdict"] == (
        "inconclusive"
    )
    assert result["active_stage_error"]["terminal"] is True


def test_execution_verifier_rejects_stale_approval(
    run_state,
) -> None:
    state = _state(run_state, ok=True)
    state["user_approval"] = "approved"
    state["approval_record"] = {
        "approval_id": "approval-stale",
        "action_id": _action().action_id,
        "action_hash": "stale-action-hash",
        "decision": "approved",
        "reviewer": "human",
        "risk_level": "high",
        "reviewed_at": "2026-08-10T00:00:00+00:00",
    }

    result = execution_verifier_node(state)

    assert result["final_status"] == "agent_failed"
    assert result["execution_verification"]["verdict"] == (
        "inconclusive"
    )
    checks = {
        item["name"]: item["passed"]
        for item in result["execution_verification"]["checks"]
    }
    assert checks["authorization_identity"] is False
