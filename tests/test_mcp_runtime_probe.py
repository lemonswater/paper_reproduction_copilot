from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.config import settings
from app.mcp_contracts.baseline import load_baseline
from app.mcp_contracts.schemas import (
    McpClientProfile,
    McpRuntimeFingerprint,
)
from app.mcp_operations.identity import runtime_report_hash
from app.mcp_operations.policy import load_runtime_policy
from app.mcp_operations.probe import (
    McpProbeTarget,
    run_runtime_probe,
)


JOB_ID = "job_" + "a" * 32


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeToolResult:
    is_error = False
    structured_content = {"status": "ok"}


class FakeResourceResult:
    contents = [SimpleNamespace(text='{"status":"ok"}')]

    def model_dump(self, *, mode: str):
        assert mode == "json"
        return {"contents": [{"text": '{"status":"ok"}'}]}


class FakeClient:
    def __init__(self, *, timeout_status: bool = False) -> None:
        self.timeout_status = timeout_status

    async def call_tool(
        self,
        name,
        arguments,
        read_timeout_seconds=None,
    ):
        if self.timeout_status and name == "get_reproduction_status":
            # 模拟真实 MCP Client 的 read_timeout 行为：
            # 超时时间到了之后 Client 自己会抛 TimeoutError。
            await asyncio.sleep(read_timeout_seconds or 0.2)
            raise asyncio.TimeoutError("simulated read timeout")
        return FakeToolResult()

    async def read_resource(self, uri):
        return FakeResourceResult()


def _target(client: FakeClient) -> McpProbeTarget:
    profile = McpClientProfile(
        profile_id="in-memory-modern",
        transport="in_memory",
        mode="auto",
    )

    @asynccontextmanager
    async def connect():
        yield client

    return McpProbeTarget(profile=profile, connect=connect)


def _policy(*, timeout_seconds: float = 1.0):
    committed = load_runtime_policy(
        settings.mcp_runtime_policy_path,
        allowed_root=settings.allowed_root,
    )
    # 单元测试只运行一个 Profile、每个 Operation 一个样本。
    return committed.model_copy(
        update={
            "offline_profile_ids": ["in-memory-modern"],
            "samples_per_operation": 1,
            "request_timeout_seconds": timeout_seconds,
        }
    )


@pytest.mark.anyio
async def test_probe_hashes_outputs_and_covers_six_operations(
    monkeypatch,
) -> None:
    baseline = load_baseline(settings.mcp_contract_baseline_path)

    async def observe(_client, *, profile):
        return SimpleNamespace(
            runtime=McpRuntimeFingerprint(
                profile_id=profile.profile_id,
                transport=profile.transport,
                connect_mode=profile.mode,
                python_version="3.10.20",
                mcp_sdk_version="2.0.0",
                mcp_sdk_major=2,
                pydantic_version="2.13.4",
                protocol_version="2026-07-28",
            ),
            surface=SimpleNamespace(
                surface_sha256=baseline.accepted_surface_sha256
            ),
        )

    monkeypatch.setattr(
        "app.mcp_operations.probe.observe_connected_client",
        observe,
    )
    report = await run_runtime_probe(
        mode="offline",
        policy=_policy(),
        baseline=baseline,
        targets=[_target(FakeClient())],
        job_id=JOB_ID,
    )

    assert report.passed is True
    assert len(report.samples) == 6
    assert all(item.output_sha256 for item in report.samples)
    assert runtime_report_hash(report) == report.report_sha256
    serialized = json.dumps(report.model_dump(mode="json"))
    assert JOB_ID not in serialized
    assert "reproduction status and final result" not in serialized


@pytest.mark.anyio
async def test_probe_turns_hang_into_timeout_finding(monkeypatch) -> None:
    baseline = load_baseline(settings.mcp_contract_baseline_path)

    async def observe(_client, *, profile):
        return SimpleNamespace(
            runtime=McpRuntimeFingerprint(
                profile_id=profile.profile_id,
                transport=profile.transport,
                connect_mode=profile.mode,
                python_version="3.10.20",
                mcp_sdk_version="2.0.0",
                mcp_sdk_major=2,
                pydantic_version="2.13.4",
                protocol_version="2026-07-28",
            ),
            surface=SimpleNamespace(
                surface_sha256=baseline.accepted_surface_sha256
            ),
        )

    monkeypatch.setattr(
        "app.mcp_operations.probe.observe_connected_client",
        observe,
    )
    report = await run_runtime_probe(
        mode="offline",
        policy=_policy(timeout_seconds=0.01),
        baseline=baseline,
        targets=[_target(FakeClient(timeout_status=True))],
        job_id=JOB_ID,
    )

    assert report.passed is False
    status_samples = [
        item
        for item in report.samples
        if item.operation == "get_reproduction_status"
    ]
    assert status_samples[0].status == "timeout"
    assert status_samples[0].error_code == "MCP_RUNTIME_TIMEOUT"
