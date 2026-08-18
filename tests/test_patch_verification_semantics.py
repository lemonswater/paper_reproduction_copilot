from __future__ import annotations

from app.schemas import PatchVerificationCheck
from app.tools.patch_tools import summarize_patch_verification


def _passed(name: str) -> PatchVerificationCheck:
    return PatchVerificationCheck(name=name, status="passed")


def _structural_checks() -> list[PatchVerificationCheck]:
    return [
        _passed("git_apply_check"),
        _passed("git_apply"),
        _passed("after_sha256"),
        _passed("worktree_diff_scope"),
        PatchVerificationCheck(name="python_syntax", status="skipped"),
    ]


def test_no_behavior_test_is_only_structurally_valid():
    checks = [
        *_structural_checks(),
        PatchVerificationCheck(name="targeted_tests", status="skipped"),
    ]
    status, allowed, structural, run_count, passed = (
        summarize_patch_verification(checks)
    )
    assert status == "structurally_valid"
    assert allowed is False
    assert structural is True
    assert run_count == 0
    assert passed == 0


def test_passed_behavior_test_allows_promotion():
    checks = [*_structural_checks(), _passed("targeted_tests")]
    status, allowed, _, run_count, passed = (
        summarize_patch_verification(checks)
    )
    assert status == "behaviorally_verified"
    assert allowed is True
    assert run_count == 1
    assert passed == 1


def test_failed_behavior_test_fails_verification():
    checks = [
        *_structural_checks(),
        PatchVerificationCheck(name="targeted_tests", status="failed"),
    ]
    status, allowed, *_ = summarize_patch_verification(checks)
    assert status == "failed"
    assert allowed is False