from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import ValidationError

from app.mcp_gateway.errors import (
    McpEndpointRejected,
    McpPolicyError,
)
from app.mcp_gateway.identity import sha256_value
from app.mcp_gateway.schemas import (
    McpGatewayPolicy,
    McpServerProfile,
)


MAX_POLICY_BYTES = 256 * 1024


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def validate_loopback_endpoint(endpoint: str) -> None:
    """第一版只接受不经过 DNS 的本机 Streamable HTTP endpoint。"""

    raw = endpoint.strip()
    if raw != endpoint or any(
        ord(character) < 32 or ord(character) == 127
        for character in raw
    ):
        raise McpEndpointRejected("MCP endpoint shape invalid")

    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise McpEndpointRejected("MCP endpoint parse failed") from exc

    if parsed.scheme != "http":
        raise McpEndpointRejected("MCP endpoint scheme denied")
    if parsed.username is not None or parsed.password is not None:
        raise McpEndpointRejected("MCP endpoint userinfo denied")
    if parsed.query or parsed.fragment:
        raise McpEndpointRejected("MCP endpoint query/fragment denied")
    if parsed.path != "/mcp":
        raise McpEndpointRejected("MCP endpoint path must be /mcp")
    if port is None or not 1024 <= port <= 65535:
        raise McpEndpointRejected("MCP endpoint requires an explicit user port")
    if parsed.hostname is None:
        raise McpEndpointRejected("MCP endpoint host required")

    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise McpEndpointRejected(
            "MCP endpoint host must be a literal loopback IP"
        ) from exc
    if not address.is_loopback:
        raise McpEndpointRejected("MCP endpoint must be loopback")


def validate_server_profile(profile: McpServerProfile) -> None:
    validate_loopback_endpoint(profile.endpoint)

    if profile.enabled:
        for binding in profile.bindings:
            if binding.expected_input_schema_sha256 == "0" * 64:
                raise McpPolicyError("enabled MCP binding has placeholder input hash")
            if binding.expected_output_schema_sha256 == "0" * 64:
                raise McpPolicyError("enabled MCP binding has placeholder output hash")


def load_mcp_gateway_policy(
    path: Path,
    *,
    allowed_root: Path,
) -> McpGatewayPolicy:
    root = allowed_root.expanduser().resolve()
    candidate = path.expanduser().resolve()
    if not _is_within(candidate, root):
        raise McpPolicyError("MCP Policy path escapes ALLOWED_ROOT")
    if not candidate.exists():
        raise McpPolicyError("MCP Policy file not found")
    if candidate.is_symlink() or not candidate.is_file():
        raise McpPolicyError("MCP Policy must be a regular non-symlink file")
    if candidate.stat().st_size > MAX_POLICY_BYTES:
        raise McpPolicyError("MCP Policy exceeds size limit")

    try:
        raw = json.loads(candidate.read_text(encoding="utf-8"))
        policy = McpGatewayPolicy.model_validate(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
        raise McpPolicyError("MCP Policy cannot be validated") from exc

    for profile in policy.servers:
        validate_server_profile(profile)
    return policy


def policy_sha256(policy: McpGatewayPolicy) -> str:
    return sha256_value(policy.model_dump(mode="json"))
