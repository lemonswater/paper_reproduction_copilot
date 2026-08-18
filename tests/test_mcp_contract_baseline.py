from __future__ import annotations

import json

import pytest

from app.mcp_contracts.baseline import (
    build_candidate,
    load_baseline,
    load_candidate,
    promote_candidate,
    write_candidate,
)
from app.mcp_contracts.errors import (
    McpContractBaselineInvalid,
    McpContractPromotionRejected,
)
from tests.mcp_contract_helpers import observe_test_surfaces

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_candidate_round_trip_is_hash_bound(tmp_path) -> None:
    observations = await observe_test_surfaces(tmp_path)
    candidate = build_candidate(observations)
    path = tmp_path / "candidate.json"

    write_candidate(path, candidate)
    loaded = load_candidate(path)

    assert loaded.candidate_sha256 == candidate.candidate_sha256
    assert loaded.consistent_surface is True


async def test_tampered_candidate_is_rejected(tmp_path) -> None:
    candidate = build_candidate(await observe_test_surfaces(tmp_path))
    path = tmp_path / "candidate.json"
    write_candidate(path, candidate)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["surface_sha256"] = "f" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(McpContractBaselineInvalid, match="hash"):
        load_candidate(path)


async def test_symlinked_candidate_is_rejected(tmp_path) -> None:
    candidate = build_candidate(await observe_test_surfaces(tmp_path))
    target = tmp_path / "candidate-target.json"
    link = tmp_path / "candidate-link.json"
    write_candidate(target, candidate)
    link.symlink_to(target)

    with pytest.raises(McpContractBaselineInvalid, match="symlink"):
        load_candidate(link)


async def test_promotion_requires_expected_surface_hash(tmp_path) -> None:
    candidate = build_candidate(await observe_test_surfaces(tmp_path))

    with pytest.raises(
        McpContractPromotionRejected,
        match="stale",
    ):
        promote_candidate(
            candidate=candidate,
            baseline_path=tmp_path / "baseline.json",
            expected_surface_sha256="0" * 64,
            reviewed_by="tester",
            reason="reviewed schema diff",
            replace=False,
            expected_current_baseline_sha256=None,
        )


async def test_replacement_requires_current_baseline_hash(tmp_path) -> None:
    candidate = build_candidate(await observe_test_surfaces(tmp_path))
    path = tmp_path / "baseline.json"
    first = promote_candidate(
        candidate=candidate,
        baseline_path=path,
        expected_surface_sha256=candidate.surface_sha256,
        reviewed_by="tester",
        reason="initial reviewed baseline",
        replace=False,
        expected_current_baseline_sha256=None,
    )
    assert load_baseline(path).baseline_sha256 == first.baseline_sha256

    with pytest.raises(McpContractPromotionRejected, match="stale"):
        promote_candidate(
            candidate=candidate,
            baseline_path=path,
            expected_surface_sha256=candidate.surface_sha256,
            reviewed_by="tester",
            reason="replace reviewed baseline",
            replace=True,
            expected_current_baseline_sha256="0" * 64,
        )
