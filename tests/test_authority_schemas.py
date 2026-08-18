from __future__ import annotations

import pytest

from app.authority.evidence import (
    build_execution_evidence,
    build_execution_verification,
    validate_execution_evidence_hash,
)
from app.schemas import ExecutableAction, ExecutionResult


def _action() -> ExecutableAction:
    return ExecutableAction(
        action_id="action-phase43",
        program="python",
        args=["train.py"],
        cwd="/workspace/repo",
        source="script",
        reason="run bounded training command",
        execution_profile_id="local-test",
        execution_profile_fingerprint="profile-sha",
    )


def _result(*, ok: bool = True) -> ExecutionResult:
    return ExecutionResult(
        ok=ok,
        returncode=0 if ok else 1,
        end_reason="exited",
        execution_id="exec-phase43",
        execution_profile_id="local-test",
        execution_backend="local",
        process_record_path=(
            "/workspace/run/process_record.json"
        ),
        combined_log_path="/workspace/run/combined.log",
    )


def test_execution_evidence_hash_round_trip() -> None:
    evidence = build_execution_evidence(
        action=_action(),
        result=_result(),
        artifact_records=[
            {"artifact_id": "artifact-process-record"},
            {"artifact_id": "artifact-combined-log"},
        ],
    )

    validate_execution_evidence_hash(evidence)
    assert len(evidence.evidence_sha256) == 64
    assert evidence.artifact_ids == [
        "artifact-combined-log",
        "artifact-process-record",
    ]


def test_execution_evidence_detects_tampering() -> None:
    evidence = build_execution_evidence(
        action=_action(),
        result=_result(),
        artifact_records=[],
    )
    tampered = evidence.model_copy(update={"returncode": 9})

    with pytest.raises(ValueError, match="hash mismatch"):
        validate_execution_evidence_hash(tampered)


def test_verified_scope_does_not_claim_scientific_success() -> None:
    action = _action()
    result = _result()
    evidence = build_execution_evidence(
        action=action,
        result=result,
        artifact_records=[],
    )

    verification = build_execution_verification(
        action=action,
        result=result,
        evidence=evidence,
        decision="not_required",
        approval=None,
    )

    assert verification.verdict == "verified"
    assert verification.claim_scope == "execution_protocol"
    assert verification.projected_final_status == "succeeded"
    assert "科学指标" in verification.summary
