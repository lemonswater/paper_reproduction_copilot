from __future__ import annotations

import pytest

from app.schemas import PatchPromotionRecord
from app.tools import patch_tools
from app.tools.patch_tools import (
    compute_verification_hash,
    validate_patch_promotion_authorization,
    validate_verification_hash,
)


def test_tampering_any_report_field_invalidates_hash(valid_report):
    report = valid_report.model_copy(update={"summary": "tampered"})
    with pytest.raises(ValueError, match="content changed"):
        validate_verification_hash(report)


def test_embedded_hash_is_recomputed(valid_report):
    unhashed = valid_report.model_copy(
        update={"verification_sha256": None}
    )
    expected = compute_verification_hash(unhashed)
    report = unhashed.model_copy(
        update={"verification_sha256": expected}
    )
    assert validate_verification_hash(report) == expected


def _authorization_inputs(valid_report, patch_bundle):
    """让 bundle、report、promotion 和 state 指向同一身份。"""

    bundle = patch_bundle
    promotion = PatchPromotionRecord(
        promotion_id="promotion_fixture",
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        verification_sha256=valid_report.verification_sha256,
        decision="approved",
        reviewed_at="2026-01-01T00:00:00+00:00",
    )
    state = {
        "execution_profile_id": valid_report.execution_profile_id,
        "execution_profile_fingerprint": (
            valid_report.execution_profile_fingerprint
        ),
        "pending_action": {
            "execution_profile_id": valid_report.execution_profile_id,
            "execution_profile_fingerprint": (
                valid_report.execution_profile_fingerprint
            ),
        },
    }
    return bundle, promotion, state


def _trust_current_fixture_profile(monkeypatch, valid_report):
    """隔离 profile store，只测试 authorization 绑定逻辑。"""

    monkeypatch.setattr(
        patch_tools,
        "get_execution_profile",
        lambda profile_id: {"profile_id": profile_id},
    )
    monkeypatch.setattr(
        patch_tools,
        "compute_execution_profile_fingerprint",
        lambda profile: valid_report.execution_profile_fingerprint,
    )


@pytest.mark.parametrize(
    ("report_updates", "message"),
    [
        (
            {
                "status": "structurally_valid",
                "promotion_allowed": False,
                "behavioral_checks_run": 0,
                "behavioral_checks_passed": 0,
            },
            "not behaviorally verified",
        ),
        ({"promotion_allowed": False}, "does not allow promotion"),
        ({"patch_id": "different-patch"}, "patch_id"),
        ({"patch_sha256": "d" * 64}, "patch hash"),
    ],
)
def test_report_mismatch_blocks_authorization(
    monkeypatch,
    valid_report,
    patch_bundle,
    report_updates,
    message,
):
    _trust_current_fixture_profile(monkeypatch, valid_report)
    bundle, promotion, state = _authorization_inputs(
        valid_report,
        patch_bundle,
    )
    report = valid_report.model_copy(update=report_updates)
    # model_copy 不会自动重算 hash；先绑定当前篡改后内容，
    # 这样测试能够继续命中具体的 authorization 边界。
    report = report.model_copy(
        update={"verification_sha256": compute_verification_hash(report)}
    )

    with pytest.raises(ValueError, match=message):
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=report,
            promotion=promotion,
            state=state,
            require_promotion=True,
        )


def test_old_promotion_hash_is_rejected(
    monkeypatch,
    valid_report,
    patch_bundle,
):
    _trust_current_fixture_profile(monkeypatch, valid_report)
    bundle, promotion, state = _authorization_inputs(
        valid_report,
        patch_bundle,
    )
    stale = promotion.model_copy(
        update={"verification_sha256": "0" * 64}
    )

    with pytest.raises(ValueError, match="current verification"):
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=valid_report,
            promotion=stale,
            state=state,
            require_promotion=True,
        )


def test_state_profile_mismatch_is_rejected(
    monkeypatch,
    valid_report,
    patch_bundle,
):
    _trust_current_fixture_profile(monkeypatch, valid_report)
    bundle, promotion, state = _authorization_inputs(
        valid_report,
        patch_bundle,
    )
    state["execution_profile_id"] = "another-profile"

    with pytest.raises(ValueError, match="profile id"):
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=valid_report,
            promotion=promotion,
            state=state,
            require_promotion=True,
        )


def test_changed_profile_fingerprint_is_rejected(
    monkeypatch,
    valid_report,
    patch_bundle,
):
    bundle, promotion, state = _authorization_inputs(
        valid_report,
        patch_bundle,
    )
    monkeypatch.setattr(
        patch_tools,
        "get_execution_profile",
        lambda profile_id: {"profile_id": profile_id},
    )
    monkeypatch.setattr(
        patch_tools,
        "compute_execution_profile_fingerprint",
        lambda profile: "changed-fingerprint",
    )

    with pytest.raises(ValueError, match="profile changed"):
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=valid_report,
            promotion=promotion,
            state=state,
            require_promotion=True,
        )