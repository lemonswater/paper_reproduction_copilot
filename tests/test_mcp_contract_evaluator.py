from __future__ import annotations

import pytest

from app.mcp_contracts.evaluator import (
    compare_observation,
    evaluate_profiles,
)
from tests.mcp_contract_helpers import (
    LEGACY,
    MODERN,
    baseline_from_observations,
    observe_test_surfaces,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_offline_profiles_pass_reviewed_baseline(tmp_path) -> None:
    observations = await observe_test_surfaces(tmp_path)
    baseline = baseline_from_observations(
        tmp_path=tmp_path,
        observations=observations,
    )

    report = await evaluate_profiles(
        profiles=[MODERN, LEGACY],
        baseline=baseline,
        mode="offline",
        timeout_seconds=5,
        token_resolver=lambda _profile: pytest.fail(
            "offline eval must not resolve a token"
        ),
    )

    assert report.passed is True
    assert {item.status for item in report.profile_results} == {"passed"}


async def test_surface_hash_drift_is_release_blocking(tmp_path) -> None:
    observations = await observe_test_surfaces(tmp_path)
    baseline = baseline_from_observations(
        tmp_path=tmp_path,
        observations=observations,
    ).model_copy(
        update={"accepted_surface_sha256": "f" * 64}
    )

    findings = compare_observation(observations[0], baseline)

    assert "surface_hash_drift" in {item.code for item in findings}


async def test_sdk_patch_version_is_not_part_of_surface_hash(tmp_path) -> None:
    modern, legacy = await observe_test_surfaces(tmp_path)

    assert modern.surface.surface_sha256 == legacy.surface.surface_sha256
    assert "mcp_sdk_version" not in modern.surface.model_dump(mode="json")
