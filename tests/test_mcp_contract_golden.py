from __future__ import annotations

from pathlib import Path

import pytest

from app.mcp_contracts.baseline import load_baseline
from app.mcp_contracts.evaluator import compare_observation
from tests.mcp_contract_helpers import observe_test_surfaces

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_committed_mcp_surface_matches_golden(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    baseline = load_baseline(
        root / "config" / "mcp_export_contract_baseline.json"
    )
    observations = await observe_test_surfaces(tmp_path)

    for observation in observations:
        assert compare_observation(observation, baseline) == []
