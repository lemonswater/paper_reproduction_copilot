from __future__ import annotations

import json

import pytest

from app.config import settings
from app.mcp_operations.errors import McpRuntimePolicyInvalid
from app.mcp_operations.identity import policy_hash
from app.mcp_operations.policy import load_runtime_policy
from app.mcp_operations.schemas import McpRuntimePolicy


def test_committed_runtime_policy_is_valid() -> None:
    policy = load_runtime_policy(
        settings.mcp_runtime_policy_path,
        allowed_root=settings.allowed_root,
    )
    assert policy.policy_sha256 == policy_hash(policy)
    assert policy.offline_profile_ids == [
        "in-memory-legacy",
        "in-memory-modern",
    ]
    assert "loopback-http" in policy.release_profile_ids


def test_policy_rejects_hash_mismatch(tmp_path) -> None:
    payload = json.loads(
        settings.mcp_runtime_policy_path.read_text(encoding="utf-8")
    )
    payload["maximum_p95_ms"] = 1234.0
    path = tmp_path / "config" / "policy.json"
    path.parent.mkdir()
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(McpRuntimePolicyInvalid):
        load_runtime_policy(path, allowed_root=tmp_path)


def test_policy_rejects_new_operation_even_with_valid_hash(tmp_path) -> None:
    payload = json.loads(
        settings.mcp_runtime_policy_path.read_text(encoding="utf-8")
    )
    payload["required_operation_names"].append("execute_command")
    payload["required_operation_names"] = sorted(
        payload["required_operation_names"]
    )
    candidate = McpRuntimePolicy.model_validate(payload)
    payload["policy_sha256"] = policy_hash(candidate)

    path = tmp_path / "config" / "policy.json"
    path.parent.mkdir()
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(McpRuntimePolicyInvalid):
        load_runtime_policy(path, allowed_root=tmp_path)
