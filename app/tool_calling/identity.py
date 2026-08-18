from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from app.tool_calling.schemas import ToolLoopTrace


def canonical_json_bytes(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def trace_id_for(*, job_id: str, request_sha256: str) -> str:
    return "tooltrace_" + sha256_value(
        {
            "version": "phase52-v1",
            "job_id": job_id,
            "request_sha256": request_sha256,
        }
    )[:24]


def tool_call_fingerprint(*, internal_name: str, arguments: dict) -> str:
    return sha256_value(
        {
            "tool_name": internal_name,
            "arguments": arguments,
        }
    )


def trace_payload(trace: ToolLoopTrace) -> dict:
    payload = trace.model_dump(mode="json")
    payload.pop("trace_sha256", None)
    return payload


def compute_trace_hash(trace: ToolLoopTrace) -> str:
    return sha256_value(trace_payload(trace))


def validate_trace_hash(trace: ToolLoopTrace) -> None:
    if compute_trace_hash(trace) != trace.trace_sha256:
        from app.tool_calling.errors import ToolTraceIntegrityError

        raise ToolTraceIntegrityError("Tool trace hash mismatch")
