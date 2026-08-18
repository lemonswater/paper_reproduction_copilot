from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.mcp_contracts.errors import McpClientProfileInvalid
from app.mcp_contracts.schemas import McpClientProfile
from app.mcp_gateway.policy import validate_loopback_endpoint

MAX_PROFILE_BYTES = 64 * 1024
FORBIDDEN_RAW_KEYS = {
    "token",
    "access_token",
    "authorization",
    "headers",
    "password",
    "secret_value",
}


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            keys.append(str(key).lower())
            keys.extend(_walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_walk_keys(item))
    return keys


def load_client_profiles(
    path: Path,
    *,
    allowed_root: Path,
) -> list[McpClientProfile]:
    """读取无凭证 Profile；拒绝越界、symlink、超大和重复身份。"""

    candidate = path.expanduser()
    if candidate.is_symlink():
        raise McpClientProfileInvalid("profile path cannot be a symlink")

    resolved = candidate.resolve()
    root = allowed_root.expanduser().resolve()
    if resolved == root or root not in resolved.parents:
        raise McpClientProfileInvalid("profile path is outside allowed root")
    if not resolved.is_file():
        raise McpClientProfileInvalid("profile file does not exist")
    if resolved.stat().st_size > MAX_PROFILE_BYTES:
        raise McpClientProfileInvalid("profile file is too large")

    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise McpClientProfileInvalid("profile JSON is invalid") from exc

    if raw.get("schema_version") != "phase55-v1":
        raise McpClientProfileInvalid("profile schema_version is invalid")
    forbidden = FORBIDDEN_RAW_KEYS.intersection(_walk_keys(raw))
    if forbidden:
        raise McpClientProfileInvalid(
            "profile contains raw credential fields"
        )

    try:
        profiles = TypeAdapter(list[McpClientProfile]).validate_python(
            raw.get("profiles")
        )
    except Exception as exc:
        raise McpClientProfileInvalid("profile schema is invalid") from exc

    ids = [item.profile_id for item in profiles]
    if len(ids) != len(set(ids)):
        raise McpClientProfileInvalid("profile_id must be unique")

    enabled = [item for item in profiles if item.enabled]
    if not enabled:
        raise McpClientProfileInvalid("at least one profile must be enabled")

    for profile in enabled:
        if profile.transport == "streamable_http":
            # 复用 Phase 53 的字面量 loopback、显式端口和 /mcp Policy。
            validate_loopback_endpoint(profile.endpoint or "")
    return enabled
