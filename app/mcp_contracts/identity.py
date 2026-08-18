from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from app.mcp_contracts.schemas import (
    McpContractBaseline,
    McpContractCandidate,
    McpContractEvalReport,
    McpResourceTemplateSurface,
    McpSurfaceSnapshot,
    McpToolSurface,
)


def _normalize(value: Any) -> Any:
    """递归把嵌套的 Pydantic BaseModel 转成 JSON-safe dict/list。"""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """把 Pydantic/JSON 对象转成稳定 UTF-8 字节。"""

    material = _normalize(value)
    return json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def tool_surface(
    *,
    name: str,
    description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any] | None,
    annotations: dict[str, Any],
) -> McpToolSurface:
    payload = {
        "name": name,
        # Baseline 不需要保存完整描述，只需要发现描述是否漂移。
        "description_sha256": sha256_text(description),
        "input_schema": input_schema,
        "output_schema": output_schema,
        "annotations": annotations,
    }
    return McpToolSurface(
        **payload,
        contract_sha256=sha256_value(payload),
    )


def resource_template_surface(
    *,
    uri_template: str,
    name: str,
    mime_type: str | None,
    description: str,
) -> McpResourceTemplateSurface:
    payload = {
        "uri_template": uri_template,
        "name": name,
        "mime_type": mime_type,
        "description_sha256": sha256_text(description),
    }
    return McpResourceTemplateSurface(
        **payload,
        contract_sha256=sha256_value(payload),
    )


def surface_snapshot(**payload: Any) -> McpSurfaceSnapshot:
    return McpSurfaceSnapshot(
        **payload,
        surface_sha256=sha256_value(payload),
    )


def candidate_hash(candidate: McpContractCandidate) -> str:
    payload = candidate.model_dump(
        mode="json",
        exclude={"candidate_sha256"},
    )
    return sha256_value(payload)


def baseline_hash(baseline: McpContractBaseline) -> str:
    payload = baseline.model_dump(
        mode="json",
        exclude={"baseline_sha256"},
    )
    return sha256_value(payload)


def report_hash(report: McpContractEvalReport) -> str:
    payload = report.model_dump(
        mode="json",
        exclude={"report_sha256"},
    )
    return sha256_value(payload)
