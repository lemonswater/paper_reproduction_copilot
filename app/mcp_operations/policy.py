from __future__ import annotations

from pathlib import Path

from app.mcp_operations.errors import McpRuntimePolicyInvalid
from app.mcp_operations.identity import policy_hash
from app.mcp_operations.schemas import McpRuntimePolicy


KNOWN_OPERATIONS = {
    "get_reproduction_status",
    "list_reproduction_artifacts",
    "read_reproduction_final_report",
    "search_reproduction_evidence",
    "resource_job_status",
    "resource_final_report",
}


def _inside_allowed_root(path: Path, allowed_root: Path) -> Path:
    if path.is_symlink():
        raise McpRuntimePolicyInvalid(
            "MCP runtime policy must not be a symlink"
        )
    resolved = path.expanduser().resolve()
    root = allowed_root.expanduser().resolve()
    if resolved == root or root not in resolved.parents:
        raise McpRuntimePolicyInvalid(
            "MCP runtime policy is outside allowed root"
        )
    return resolved


def load_runtime_policy(
    path: Path,
    *,
    allowed_root: Path,
) -> McpRuntimePolicy:
    selected = _inside_allowed_root(path, allowed_root)
    if not selected.is_file():
        raise McpRuntimePolicyInvalid(
            "MCP runtime policy does not exist"
        )
    try:
        policy = McpRuntimePolicy.model_validate_json(
            selected.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise McpRuntimePolicyInvalid(
            "MCP runtime policy is invalid"
        ) from exc

    if policy_hash(policy) != policy.policy_sha256:
        raise McpRuntimePolicyInvalid(
            "MCP runtime policy hash mismatch"
        )
    if set(policy.required_operation_names) != KNOWN_OPERATIONS:
        raise McpRuntimePolicyInvalid(
            "MCP runtime policy operation set is not approved"
        )
    if not set(policy.offline_profile_ids).issubset(
        policy.release_profile_ids
    ):
        raise McpRuntimePolicyInvalid(
            "offline profiles must be a subset of release profiles"
        )
    return policy
