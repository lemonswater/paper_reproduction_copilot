from __future__ import annotations

import json

import pytest

from app.mcp_contracts.errors import McpClientProfileInvalid
from app.mcp_contracts.profiles import load_client_profiles


def _write(path, payload) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_loads_loopback_profiles_without_credentials(tmp_path) -> None:
    path = tmp_path / "profiles.json"
    _write(
        path,
        {
            "schema_version": "phase55-v1",
            "profiles": [
                {
                    "profile_id": "in-memory-modern",
                    "transport": "in_memory",
                    "mode": "auto",
                },
                {
                    "profile_id": "loopback-http",
                    "transport": "streamable_http",
                    "mode": "auto",
                    "endpoint": "http://127.0.0.1:8770/mcp",
                    "secret_name": "PAPER_COPILOT_MCP_EXPORT_TOKEN",
                },
            ],
        },
    )

    profiles = load_client_profiles(path, allowed_root=tmp_path)

    assert [item.profile_id for item in profiles] == [
        "in-memory-modern",
        "loopback-http",
    ]
    serialized = json.dumps(
        [item.model_dump(mode="json") for item in profiles]
    )
    assert "Bearer " not in serialized


@pytest.mark.parametrize(
    "raw_key",
    ["token", "access_token", "authorization", "headers", "password"],
)
def test_rejects_raw_credential_fields(tmp_path, raw_key: str) -> None:
    path = tmp_path / "profiles.json"
    _write(
        path,
        {
            "schema_version": "phase55-v1",
            "profiles": [
                {
                    "profile_id": "loopback-http",
                    "transport": "streamable_http",
                    "mode": "auto",
                    "endpoint": "http://127.0.0.1:8770/mcp",
                    "secret_name": "SAFE_REFERENCE",
                    raw_key: "must-not-be-stored",
                }
            ],
        },
    )

    with pytest.raises(
        McpClientProfileInvalid,
        match="credential",
    ):
        load_client_profiles(path, allowed_root=tmp_path)


def test_rejects_remote_or_dns_endpoint(tmp_path) -> None:
    path = tmp_path / "profiles.json"
    _write(
        path,
        {
            "schema_version": "phase55-v1",
            "profiles": [
                {
                    "profile_id": "remote-http",
                    "transport": "streamable_http",
                    "mode": "auto",
                    "endpoint": "https://example.com/mcp",
                    "secret_name": "SAFE_REFERENCE",
                }
            ],
        },
    )

    with pytest.raises(Exception):  # noqa: B017
        load_client_profiles(path, allowed_root=tmp_path)
