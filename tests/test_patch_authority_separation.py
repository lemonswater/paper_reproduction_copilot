from __future__ import annotations

from app.nodes.patch_verdict_node import patch_verdict_node
from app.nodes.patch_verification_executor_node import (
    patch_verification_executor_node,
)
from app.schemas import PatchVerificationReport


PATCH_SHA = "a" * 64
PROFILE_SHA = "profile-phase43"


def _state(run_state: dict) -> dict:
    return {
        **run_state,
        "repo_path": "/workspace/repo",
        "execution_profile_id": "local-test",
        "execution_profile_fingerprint": PROFILE_SHA,
        "pending_patch": {
            "patch_id": "patch-phase43",
            "proposal_id": "proposal-phase43",
            "repo_path": "/workspace/repo",
            "base_git_commit": "deadbeef",
            "patch_path": "/workspace/patch.diff",
            "patch_sha256": PATCH_SHA,
            "files": [],
            "summary": "bounded patch",
            "generated_at": "2026-08-10T00:00:00+00:00",
        },
        "patch_approval_record": {
            "approval_id": "approval-phase43",
            "patch_id": "patch-phase43",
            "patch_sha256": PATCH_SHA,
            "decision": "approved",
            "reviewed_at": "2026-08-10T00:01:00+00:00",
        },
        "file_repair_proposal": {
            "proposal_id": "proposal-phase43",
            "kind": "patch",
            "summary": "replace unsafe view",
            "root_cause": "non-contiguous input",
            "edits": [
                {
                    "relative_path": "model.py",
                    "reason": "use reshape",
                    "replacements": [
                        {
                            "old_text": "x.view(-1)",
                            "new_text": "x.reshape(-1)",
                            "reason": "support non-contiguous input",
                        }
                    ],
                }
            ],
            "verification_targets": ["tests/test_model.py"],
            "risks": [],
            "bounded": True,
        },
    }


def _runner_report() -> PatchVerificationReport:
    checks = [
        {
            "name": "git_apply_check",
            "status": "passed",
        },
        {"name": "git_apply", "status": "passed"},
        {"name": "after_sha256", "status": "passed"},
        {
            "name": "worktree_diff_scope",
            "status": "passed",
        },
        {
            "name": "targeted_tests",
            "status": "passed",
            "command": [
                "python",
                "-m",
                "pytest",
                "-q",
                "tests/test_model.py",
            ],
            "returncode": 0,
        },
    ]
    return PatchVerificationReport(
        patch_id="patch-phase43",
        patch_sha256=PATCH_SHA,
        execution_profile_id="local-test",
        execution_profile_fingerprint=PROFILE_SHA,
        execution_backend="local",
        status="behaviorally_verified",
        promotion_allowed=True,
        structural_checks_passed=True,
        behavioral_checks_run=1,
        behavioral_checks_passed=1,
        worktree_path="/workspace/worktree",
        worktree_diff_sha256="b" * 64,
        checks=checks,
        summary="legacy runner report",
        generated_at="2026-08-10T00:02:00+00:00",
    )


def test_patch_executor_outputs_evidence_not_verdict(
    run_state,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.nodes.patch_verification_executor_node."
        "verify_patch_in_worktree",
        lambda **_kwargs: _runner_report(),
    )

    result = patch_verification_executor_node(
        _state(run_state)
    )

    assert result["patch_verification_evidence"]
    assert "patch_verification_report" not in result
    assert "patch_verification_passed" not in result
    assert "final_status" not in result


def test_patch_verdict_recomputes_promotion_result(
    run_state,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.nodes.patch_verification_executor_node."
        "verify_patch_in_worktree",
        lambda **_kwargs: _runner_report(),
    )
    state = _state(run_state)
    execution_update = patch_verification_executor_node(state)

    verdict = patch_verdict_node(
        {**state, **execution_update}
    )

    assert verdict["patch_verification_passed"] is True
    assert verdict["patch_verification_report"]["status"] == (
        "behaviorally_verified"
    )
    assert verdict["patch_verification_report"][
        "promotion_allowed"
    ] is True


def test_patch_verdict_rejects_tampered_evidence(
    run_state,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.nodes.patch_verification_executor_node."
        "verify_patch_in_worktree",
        lambda **_kwargs: _runner_report(),
    )
    state = _state(run_state)
    execution_update = patch_verification_executor_node(state)
    evidence = execution_update["patch_verification_evidence"]
    evidence["checks"][0]["status"] = "failed"

    verdict = patch_verdict_node(
        {**state, **execution_update}
    )

    assert verdict["patch_verification_passed"] is False
    assert verdict["final_status"] == (
        "patch_verification_inconclusive"
    )
