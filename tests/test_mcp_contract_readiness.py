from __future__ import annotations

import json

import pytest

from app.config import settings
from app.mcp_contracts.baseline import build_candidate, promote_candidate
from app.mcp_contracts.readiness import inspect_mcp_stack
from app.mcp_contracts.schemas import McpStackComponent
from tests.mcp_contract_helpers import observe_test_surfaces


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _prepare_contract_files(tmp_path):
    observations = await observe_test_surfaces(tmp_path)
    candidate = build_candidate(observations)
    baseline_path = tmp_path / "baseline.json"
    promote_candidate(
        candidate=candidate,
        baseline_path=baseline_path,
        expected_surface_sha256=candidate.surface_sha256,
        reviewed_by="pytest",
        reason="readiness test baseline",
        replace=False,
        expected_current_baseline_sha256=None,
    )
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": "phase55-v1",
                "profiles": [
                    {
                        "profile_id": "in-memory-modern",
                        "transport": "in_memory",
                        "mode": "auto",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return baseline_path, profile_path


async def test_stack_ready_with_valid_contracts_and_disabled_features(
    tmp_path,
    monkeypatch,
) -> None:
    baseline_path, profile_path = await _prepare_contract_files(tmp_path)
    monkeypatch.setattr(settings, "allowed_root", tmp_path)
    monkeypatch.setattr(
        settings,
        "mcp_contract_baseline_path",
        baseline_path,
    )
    monkeypatch.setattr(
        settings,
        "mcp_client_profiles_path",
        profile_path,
    )
    monkeypatch.setattr(settings, "mcp_gateway_enabled", False)
    monkeypatch.setattr(settings, "mcp_export_enabled", False)
    monkeypatch.setattr(
        "app.mcp_contracts.readiness._runtime_component",
        lambda: McpStackComponent(
            name="runtime",
            status="ready",
        ),
    )

    report = inspect_mcp_stack()

    assert report.status == "ready"
    components = {item.name: item.status for item in report.components}
    assert components["sdk"] == "ready"
    assert components["contracts"] == "ready"
    assert components["gateway"] == "disabled"
    assert components["export"] == "disabled"
    assert components["runtime"] == "ready"


async def test_missing_baseline_is_not_ready(
    tmp_path,
    monkeypatch,
) -> None:
    _baseline_path, profile_path = await _prepare_contract_files(tmp_path)
    monkeypatch.setattr(settings, "allowed_root", tmp_path)
    monkeypatch.setattr(
        settings,
        "mcp_contract_baseline_path",
        tmp_path / "missing.json",
    )
    monkeypatch.setattr(
        settings,
        "mcp_client_profiles_path",
        profile_path,
    )
    monkeypatch.setattr(settings, "mcp_gateway_enabled", False)
    monkeypatch.setattr(settings, "mcp_export_enabled", False)
    monkeypatch.setattr(
        "app.mcp_contracts.readiness._runtime_component",
        lambda: McpStackComponent(
            name="runtime",
            status="ready",
        ),
    )

    report = inspect_mcp_stack()

    assert report.status == "not_ready"


async def test_runtime_component_requires_release_report(
    tmp_path,
    monkeypatch,
) -> None:
    policy_path = tmp_path / "config" / "mcp_runtime_policy.json"
    policy_path.parent.mkdir()
    policy_path.write_text(
        settings.mcp_runtime_policy_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    report_root = tmp_path / "analysis" / "mcp_runtime"
    report_root.mkdir(parents=True)

    monkeypatch.setattr(settings, "allowed_root", tmp_path)
    monkeypatch.setattr(
        settings,
        "mcp_runtime_policy_path",
        policy_path,
    )
    monkeypatch.setattr(
        settings,
        "mcp_runtime_report_root",
        report_root,
    )
    monkeypatch.setattr(settings, "mcp_export_enabled", True)

    from app.mcp_contracts.readiness import _runtime_component

    component = _runtime_component()
    assert component.status == "not_ready"
    assert component.issues == ["runtime_release_report_missing"]
