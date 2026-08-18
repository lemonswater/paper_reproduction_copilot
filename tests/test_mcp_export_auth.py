from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.mcp_export.auth import LocalBearerAuthMiddleware


TOKEN = "phase54-test-token-" + "x" * 32


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def endpoint(_request: Request):
    return JSONResponse({"ok": True})


def build_app():
    inner = Starlette(
        routes=[
            Route("/mcp", endpoint, methods=["POST"]),
            Route("/healthz", endpoint, methods=["GET"]),
        ]
    )
    return LocalBearerAuthMiddleware(
        inner,
        expected_token=TOKEN,
        public_paths={"/healthz"},
    )


@pytest.mark.anyio
async def test_missing_token_is_rejected() -> None:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    ) as client:
        response = await client.post("/mcp")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MCP_EXPORT_UNAUTHORIZED"
    assert "Bearer" in response.headers["WWW-Authenticate"]


@pytest.mark.anyio
async def test_valid_token_reaches_inner_app() -> None:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    ) as client:
        response = await client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.anyio
async def test_duplicate_authorization_headers_are_rejected() -> None:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    ) as client:
        response = await client.post(
            "/mcp",
            headers=[
                ("Authorization", f"Bearer {TOKEN}"),
                ("Authorization", "Bearer attacker"),
            ],
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_healthz_contains_no_private_state() -> None:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    ) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
