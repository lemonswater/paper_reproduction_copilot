from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel

from app.mcp_export.errors import McpExportInputInvalid
from app.mcp_export.schemas import JOB_ID_PATTERN


def canonical_json_bytes(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        material = value.model_dump(mode="json")
    else:
        material = value
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


def validate_job_id(job_id: str) -> str:
    """只接受 JobService 当前生成的 job_<32 hex> 身份。"""

    normalized = job_id.strip()
    if re.fullmatch(JOB_ID_PATTERN, normalized) is None:
        raise McpExportInputInvalid("invalid job_id")
    return normalized


def normalize_query(query: str) -> str:
    normalized = " ".join(query.strip().split())
    if not normalized or len(normalized) > 500:
        raise McpExportInputInvalid("invalid query length")
    if any(
        ord(character) < 32 or ord(character) == 127
        for character in normalized
    ):
        raise McpExportInputInvalid("query contains control characters")
    return normalized


def bounded_limit(limit: int, *, maximum: int) -> int:
    if not 1 <= limit <= maximum:
        raise McpExportInputInvalid("limit is outside allowed range")
    return limit
