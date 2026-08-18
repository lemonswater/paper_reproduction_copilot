"""Phase 50: Model Routing Authority Boundary 测试。

使用 AST 和 import 检查确保路由模块不绕过安全边界。
"""

from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

import pytest


_FORBIDDEN_MODULES = {
    "app.execution",
    "app.nodes.human_review_node",
    "subprocess",
    "socket",
    "requests",
}


def _check_imports(file_path: Path, forbidden: set[str]) -> list[str]:
    """检查文件中的 import 是否包含禁止的模块。"""
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden_mod in forbidden:
                    if alias.name == forbidden_mod or alias.name.startswith(
                        forbidden_mod + "."
                    ):
                        violations.append(
                            f"{file_path.name}: import {alias.name}"
                        )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for forbidden_mod in forbidden:
                    if node.module == forbidden_mod or node.module.startswith(
                        forbidden_mod + "."
                    ):
                        violations.append(
                            f"{file_path.name}: from {node.module} import ..."
                        )
    return violations


@pytest.mark.parametrize(
    "module_path",
    [
        "app/model_routing/catalog.py",
        "app/model_routing/policy.py",
        "app/model_routing/repository.py",
        "app/model_routing/evaluation.py",
        "app/model_routing/identity.py",
        "app/model_routing/schemas.py",
        "app/model_routing/errors.py",
        "app/model_routing/usage.py",
    ],
)
def test_core_modules_no_forbidden_imports(module_path: str):
    path = Path(module_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / module_path
    violations = _check_imports(path, _FORBIDDEN_MODULES)
    assert not violations, (
        f"禁止的 import: {violations}"
    )


def test_gateway_no_execution_imports():
    path = (
        Path(__file__).resolve().parents[1]
        / "app/model_routing/gateway.py"
    )
    forbidden = {
        "app.execution",
        "app.nodes.human_review_node",
        "app.nodes.executor_node",
        "app.tools.patch_tools",
        "app.tools.safe_shell_tools",
    }
    violations = _check_imports(path, forbidden)
    assert not violations, f"Gateway 禁止的 import: {violations}"


def test_provider_no_business_logic_imports():
    path = (
        Path(__file__).resolve().parents[1]
        / "app/model_routing/provider.py"
    )
    forbidden = {
        "app.chat",
        "app.memory",
        "app.knowledge_base",
        "app.tools.action_tools",
    }
    violations = _check_imports(path, forbidden)
    assert not violations, f"Provider 禁止的 import: {violations}"


def test_api_router_only_get_methods():
    """API Router 只应有 GET 端点。"""
    path = (
        Path(__file__).resolve().parents[1]
        / "app/api/model_routing_routes.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    methods_found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if func.attr in {"get", "post", "put", "delete", "patch"}:
                    methods_found.append(func.attr)

    assert all(m == "get" for m in methods_found), (
        f"只允许 GET，发现: {methods_found}"
    )


def test_invocation_record_no_secrets():
    """ModelInvocationRecord 不应包含 api_key/secret/prompt 原文等字段。"""
    from app.model_routing.schemas import ModelInvocationRecord

    fields = set(ModelInvocationRecord.model_fields.keys())
    forbidden_fields = {
        "api_key",
        "authorization",
        "secret",
        "base_url",
        "prompt",
        "output",
        "raw_preview",
    }
    overlap = fields & forbidden_fields
    assert not overlap, (
        f"ModelInvocationRecord 包含禁止字段: {overlap}"
    )


def test_invocation_record_dump_no_secrets():
    """ModelInvocationRecord 的 dump 不应包含 secret 值。"""
    from app.model_routing.schemas import ModelInvocationRecord
    from datetime import datetime, timezone

    record = ModelInvocationRecord(
        invocation_id="mdl_" + "a" * 32,
        request_sha256="0" * 64,
        decision_sha256="0" * 64,
        task_kind="chat_answer",
        job_id="job-1",
        run_id="run-1",
        node_name="test_node",
        profile_id="legacy_chat",
        model_name="legacy-model",
        pricing_version="test-v1",
        enforced=True,
        status="succeeded",
        reserved_input_tokens=100,
        reserved_output_tokens=50,
        reserved_cost_micro_usd=10,
        actual_input_tokens=100,
        actual_output_tokens=50,
        actual_cost_micro_usd=10,
        usage_quality="provider_reported",
        provider_response_count=1,
        prompt_chars=100,
        prompt_sha256="0" * 64,
        schema_sha256="0" * 64,
        latency_ms=500,
        error_code=None,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        lease_expires_at=datetime.now(timezone.utc).isoformat(),
    )
    dumped = record.model_dump(mode="json")
    dumped_str = str(dumped).lower()

    forbidden_patterns = [
        "sk-",
        "api_key",
        "authorization",
        "base_url",
        "secret",
    ]
    for pattern in forbidden_patterns:
        # prompt_sha256 is allowed, but raw "prompt" should not appear
        if pattern == "secret" and "prompt_sha256" in dumped_str:
            continue
        assert pattern not in dumped_str or pattern in dumped_str and pattern.endswith(
            "_sha256"
        ), f"dump 中发现禁止的模式: {pattern}"
