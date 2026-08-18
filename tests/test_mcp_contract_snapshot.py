from __future__ import annotations

import mcp  # noqa: F401  # 缺失 SDK 时必须在收集阶段失败。
import pytest

from tests.mcp_contract_helpers import observe_test_surfaces

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_modern_and_legacy_observe_same_public_surface(tmp_path) -> None:
    modern, legacy = await observe_test_surfaces(tmp_path)

    assert modern.surface.surface_sha256 == legacy.surface.surface_sha256
    assert modern.runtime.protocol_version
    assert legacy.runtime.protocol_version
    assert modern.runtime.mcp_sdk_major == 2
    assert legacy.runtime.mcp_sdk_major == 2


async def test_snapshot_contains_exact_read_only_catalog(tmp_path) -> None:
    modern, _legacy = await observe_test_surfaces(tmp_path)
    surface = modern.surface

    assert [item.name for item in surface.tools] == [
        "get_reproduction_status",
        "list_reproduction_artifacts",
        "read_reproduction_final_report",
        "search_reproduction_evidence",
    ]
    assert [item.uri_template for item in surface.resource_templates] == [
        "repro://jobs/{job_id}/final-report",
        "repro://jobs/{job_id}/status",
    ]
    assert surface.static_resource_uris == []
    assert surface.prompt_names == []
    assert all(item.output_schema is not None for item in surface.tools)


async def test_snapshot_contains_no_authority_parameter(tmp_path) -> None:
    modern, _legacy = await observe_test_surfaces(tmp_path)
    serialized = modern.surface.model_dump_json().lower()

    for forbidden in [
        '"token"',
        '"authorization"',
        '"actor"',
        '"capability"',
        '"endpoint"',
        '"path"',
    ]:
        assert forbidden not in serialized
