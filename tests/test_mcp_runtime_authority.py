from __future__ import annotations

from app.mcp_operations.policy import KNOWN_OPERATIONS
from app.mcp_operations.schemas import McpInvocationSample


def test_runtime_registry_contains_only_six_read_only_operations() -> None:
    assert KNOWN_OPERATIONS == {
        "get_reproduction_status",
        "list_reproduction_artifacts",
        "read_reproduction_final_report",
        "search_reproduction_evidence",
        "resource_job_status",
        "resource_final_report",
    }
    forbidden = {
        "shell",
        "command",
        "execute",
        "patch",
        "write",
        "delete",
        "approve",
        "cancel",
        "rerun",
    }
    assert not any(
        fragment in operation
        for operation in KNOWN_OPERATIONS
        for fragment in forbidden
    )


def test_sample_schema_cannot_store_raw_request_or_response() -> None:
    fields = set(McpInvocationSample.model_fields)
    assert not fields.intersection(
        {
            "job_id",
            "request_id",
            "query",
            "arguments",
            "response",
            "content",
            "token",
            "endpoint",
        }
    )
    assert {"output_sha256", "error_code"}.issubset(fields)
