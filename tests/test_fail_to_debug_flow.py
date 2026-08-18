from __future__ import annotations

from app.graph import (
    route_after_execution_verifier,
    route_after_executor,
)


def test_route_after_new_executor_requires_verifier() -> None:
    state = {
        "execution_evidence": {
            "evidence_id": "exec-evidence"
        }
    }
    assert route_after_executor(state) == "execution_verifier"


def test_route_after_verifier_debugs_verified_failure() -> None:
    state = {
        "final_status": "failed",
        "log_path": "runs/run-1/execution/combined.log",
        "execution_verification": {"verdict": "failed"},
    }
    assert route_after_execution_verifier(state) == "log_debug"


def test_route_after_verifier_finishes_verified_success() -> None:
    state = {
        "final_status": "succeeded",
        "execution_verification": {"verdict": "verified"},
    }
    assert route_after_execution_verifier(state) == "final_report"


def test_legacy_checkpoint_failed_with_log_goes_to_debug() -> None:
    state = {
        "final_status": "failed",
        "log_path": "outputs/execution.log",
    }

    result = route_after_executor(state)

    assert result == "log_debug"


def test_legacy_checkpoint_succeeded_goes_to_final_report() -> None:
    state = {
        "final_status": "succeeded",
        "execution_log_path": "outputs/execution.log",
    }

    result = route_after_executor(state)

    assert result == "final_report"


def test_legacy_checkpoint_failed_no_log_goes_to_final_report() -> None:
    state = {
        "final_status": "failed",
    }

    result = route_after_executor(state)

    assert result == "final_report"
