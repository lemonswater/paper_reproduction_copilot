from __future__ import annotations

import asyncio
import socket
import threading
from contextlib import closing

import httpx2
import mcp
import pytest
import uvicorn
from mcp.client.streamable_http import streamable_http_client

from app.mcp_export.asgi import build_mcp_export_asgi_bundle
from app.mcp_export.factory import McpExportRuntime
from app.observability.in_memory import InMemoryTelemetry
from tests.mcp_export_helpers import JOB_ID, build_test_service


TOKEN = "phase56-loopback-token-" + "x" * 32


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _unused_loopback_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _wait_until_started(server: uvicorn.Server) -> None:
    for _ in range(100):
        if server.started:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Uvicorn did not start within 2 seconds")


@pytest.mark.anyio
async def test_real_http_invokes_four_tools_and_two_resources(
    tmp_path,
) -> None:
    service, audit, _delivery, _registry = build_test_service(tmp_path)
    runtime = McpExportRuntime(
        service=service,
        audit_repository=audit,
        telemetry=InMemoryTelemetry(validate_attributes=True),
    )
    bundle = build_mcp_export_asgi_bundle(
        runtime=runtime,
        token=TOKEN,
    )
    port = _unused_loopback_port()
    server = uvicorn.Server(
        uvicorn.Config(
            bundle.app,
            host="127.0.0.1",
            port=port,
            log_level="error",
            access_log=False,
            lifespan="on",
        )
    )
    thread = threading.Thread(
        target=server.run,
        name="phase56-test-mcp-http",
        daemon=True,
    )
    thread.start()

    try:
        await _wait_until_started(server)
        async with httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=httpx2.Timeout(3),
            follow_redirects=False,
            trust_env=False,
        ) as http_client:
            transport = streamable_http_client(
                f"http://127.0.0.1:{port}/mcp",
                http_client=http_client,
            )
            async with mcp.Client(
                transport,
                mode="auto",
                raise_exceptions=True,
                read_timeout_seconds=3,
            ) as client:
                listed = await client.list_tools()
                assert len(listed.tools) == 4

                tool_calls = [
                    (
                        "get_reproduction_status",
                        {"job_id": JOB_ID},
                    ),
                    (
                        "list_reproduction_artifacts",
                        {"job_id": JOB_ID, "limit": 5},
                    ),
                    (
                        "read_reproduction_final_report",
                        {"job_id": JOB_ID},
                    ),
                    (
                        "search_reproduction_evidence",
                        {
                            "job_id": JOB_ID,
                            "query": "final result",
                            "limit": 3,
                        },
                    ),
                ]
                for name, arguments in tool_calls:
                    result = await client.call_tool(
                        name,
                        arguments,
                        read_timeout_seconds=3,
                    )
                    assert result.is_error is not True
                    assert result.structured_content is not None

                status_resource = await asyncio.wait_for(
                    client.read_resource(
                        f"repro://jobs/{JOB_ID}/status"
                    ),
                    timeout=3,
                )
                report_resource = await asyncio.wait_for(
                    client.read_resource(
                        f"repro://jobs/{JOB_ID}/final-report"
                    ),
                    timeout=3,
                )
                assert status_resource.contents
                assert report_resource.contents
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive()
