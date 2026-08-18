from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from app.mcp_gateway.errors import McpEvidenceIntegrityError
from app.mcp_gateway.schemas import (
    McpEvidenceItem,
    McpEvidencePack,
    McpServerProfile,
    McpToolBinding,
)


def canonical_json_bytes(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{sha256_value(value)[:24]}"


def schema_sha256(schema: dict[str, Any]) -> str:
    """对远端原始 JSON Schema 做确定性 Hash，不做宽松语义折叠。"""
    return sha256_value(schema)


def profile_sha256(
    *,
    profile: McpServerProfile,
    binding: McpToolBinding,
) -> str:
    """只绑定一个可调用能力，而不是给整个远端目录授权。"""
    return sha256_value(
        {
            "schema_version": "phase53-v1",
            "server_id": profile.server_id,
            "transport": profile.transport,
            "endpoint": profile.endpoint,
            "allowed_protocol_versions": sorted(
                profile.allowed_protocol_versions
            ),
            "binding": binding.model_dump(mode="json"),
        }
    )


def build_evidence_item(
    *,
    server_id: str,
    binding_id: str,
    title: str,
    source_uri: str,
    excerpt: str,
    locator: str,
) -> McpEvidenceItem:
    payload = {
        "server_id": server_id,
        "binding_id": binding_id,
        "title": title,
        "source_uri": source_uri,
        "excerpt": excerpt,
        "locator": locator,
    }
    return McpEvidenceItem(
        item_id=stable_id("mcpitem", payload),
        title=title,
        source_uri=source_uri,
        excerpt=excerpt,
        locator=locator,
        item_sha256=sha256_value(payload),
    )


def pack_payload(pack: McpEvidencePack) -> dict[str, Any]:
    payload = pack.model_dump(mode="json")
    payload.pop("pack_sha256", None)
    return payload


def compute_pack_hash(pack: McpEvidencePack) -> str:
    return sha256_value(pack_payload(pack))


def validate_pack_hash(pack: McpEvidencePack) -> None:
    if compute_pack_hash(pack) != pack.pack_sha256:
        raise McpEvidenceIntegrityError("MCP Evidence Pack hash mismatch")

    for item in pack.items:
        expected = sha256_value(
            {
                "server_id": pack.server_id,
                "binding_id": pack.binding_id,
                "title": item.title,
                "source_uri": item.source_uri,
                "excerpt": item.excerpt,
                "locator": item.locator,
            }
        )
        if expected != item.item_sha256:
            raise McpEvidenceIntegrityError("MCP Evidence item hash mismatch")
