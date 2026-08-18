from __future__ import annotations

from app.graph import (
    route_after_patch_promotion_review,
    route_after_patch_review,
    route_after_patch_verifier,
)


def test_approved_patch_routes_to_verifier():
    assert route_after_patch_review({"patch_approval": "approved"}) == (
        "patch_verifier"
    )


def test_rejected_patch_routes_to_final_report():
    assert route_after_patch_review({"patch_approval": "rejected"}) == (
        "final_report"
    )


def test_only_passed_verification_routes_to_promotion_review():
    assert route_after_patch_verifier(
        {
            "patch_verification_passed": True,
            "patch_verification_report": {
                "status": "behaviorally_verified",
                "promotion_allowed": True,
            },
        }
    ) == "patch_promotion_review"
    assert route_after_patch_verifier(
        {"patch_verification_passed": False}
    ) == "final_report"


def test_structural_verification_cannot_route_to_promotion_review():
    assert route_after_patch_verifier(
        {
            "patch_verification_passed": True,
            "patch_verification_report": {
                "status": "structurally_valid",
                "promotion_allowed": False,
            },
        }
    ) == "final_report"


def test_only_approved_promotion_routes_to_apply():
    assert route_after_patch_promotion_review(
        {"patch_promotion_decision": "approved"}
    ) == "patch_apply"
    assert route_after_patch_promotion_review(
        {"patch_promotion_decision": "rejected"}
    ) == "final_report"
