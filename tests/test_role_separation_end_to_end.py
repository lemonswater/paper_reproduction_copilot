from __future__ import annotations

from pathlib import Path

from app.authority.policy import role_guarded_node
from app.nodes.execution_verifier_node import (
    execution_verifier_node,
)
from app.nodes.executor_node import executor_node
from app.schemas import ExecutableAction
from app.tools.action_tools import compute_action_hash


def _runner_result(run_state: dict) -> dict:
    attempt = (
        Path(run_state["run_dir"])
        / "execution"
        / "attempts"
        / "phase43-e2e"
    )
    attempt.mkdir(parents=True)
    stdout = attempt / "stdout.log"
    stderr = attempt / "stderr.log"
    combined = attempt / "combined.log"
    process = attempt / "process_record.json"
    stdout.write_text("phase43 ok\n", encoding="utf-8")
    stderr.write_text("", encoding="utf-8")
    combined.write_text("phase43 ok\n", encoding="utf-8")
    process.write_text("{}\n", encoding="utf-8")

    return {
        "ok": True,
        "returncode": 0,
        "end_reason": "exited",
        "stdout": "phase43 ok",
        "stderr": "",
        "combined_output": "phase43 ok",
        "timeout": False,
        "cancelled": False,
        "log_truncated": False,
        "execution_id": "phase43-e2e",
        "execution_profile_id": "local-test",
        "execution_backend": "local",
        "resource_usage": {},
        "stdout_path": str(stdout),
        "stderr_path": str(stderr),
        "combined_log_path": str(combined),
        "process_record_path": str(process),
    }


def test_executor_to_verifier_authority_handoff(
    run_state,
    monkeypatch,
) -> None:
    action = ExecutableAction(
        action_id="phase43-e2e-action",
        program="python",
        args=["-c", "print('phase43 ok')"],
        cwd="/workspace/repo",
        source="inferred",
        reason="authority integration fixture",
        execution_profile_id="local-test",
        execution_profile_fingerprint="profile-test",
    )
    action_hash = compute_action_hash(action.model_dump())
    state = {
        **run_state,
        "pending_action": action.model_dump(),
        "pending_action_hash": action_hash,
        "user_approval": "approved",
        "approval_record": {
            "approval_id": "phase43-e2e-approval",
            "action_id": action.action_id,
            "action_hash": action_hash,
            "decision": "approved",
            "reviewer": "human",
            "risk_level": "medium",
            "reviewed_at": "2026-08-10T00:00:00+00:00",
        },
        "authority_audit_records": [],
    }
    monkeypatch.setattr(
        "app.nodes.executor_node.run_action_safe",
        lambda *_args, **_kwargs: _runner_result(run_state),
    )

    guarded_executor = role_guarded_node(
        node_name="executor",
        role="executor",
        node=executor_node,
    )
    guarded_verifier = role_guarded_node(
        node_name="execution_verifier",
        role="verifier",
        node=execution_verifier_node,
    )

    execution_update = guarded_executor(state)
    assert "execution_evidence" in execution_update
    assert "final_status" not in execution_update

    after_execution = {**state, **execution_update}
    verification_update = guarded_verifier(after_execution)

    assert verification_update["final_status"] == "succeeded"
    assert verification_update["execution_verification"][
        "verdict"
    ] == "verified"
    roles = [
        item["role"]
        for item in verification_update[
            "authority_audit_records"
        ]
    ]
    assert roles == ["executor", "verifier"]
