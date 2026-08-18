"""Phase 46: Project Memory Authority Boundary 测试。"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from app.project_memory.schemas import ProjectFactPack, ProjectFactPackItem, TextFactValue
from tests.helpers.project_memory import confirmed_fact


PROJECT_MEMORY_DIR = Path(__file__).resolve().parent.parent / "app" / "project_memory"


def _module_imports(module_path: Path) -> set[str]:
    """Parse a Python file and return top-level module names."""
    tree = ast.parse(module_path.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
    return modules


def test_project_memory_does_not_import_executor_or_shell():
    forbidden = {
        "app.nodes.executor_node",
        "app.tools.safe_shell_tools",
        "app.execution.process_supervisor",
        "app.authority.guard",
        "app.tools.exec_tools",
        "app.tools.action_tools",
    }
    for py_file in PROJECT_MEMORY_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        imports = _module_imports(py_file)
        leaking = imports & forbidden
        assert not leaking, (
            f"{py_file.name} imports forbidden modules: {leaking}"
        )


def test_fact_pack_cannot_construct_action_fields():
    fact = confirmed_fact()
    item = ProjectFactPackItem(
        fact_id=fact.fact_id,
        fact_hash=fact.record_hash,
        category=fact.content.category,
        key=fact.content.key,
        value=fact.content.value,
        source_kind="manual_user",
    )
    pack = ProjectFactPack(
        project_id=fact.project_id,
        project_hash="a" * 64,
        items=[item],
        pack_hash="b" * 64,
        generated_at="2026-08-11T10:00:00+00:00",
    )
    payload = pack.model_dump(mode="json")
    forbidden_keys = {
        "pending_action",
        "approval_record",
        "execution_result",
        "patch_plan",
        "decision_envelope",
    }
    assert forbidden_keys.isdisjoint(payload)


def test_fact_pack_only_contains_explicit_user_authority():
    fact = confirmed_fact()
    item = ProjectFactPackItem(
        fact_id=fact.fact_id,
        fact_hash=fact.record_hash,
        category=fact.content.category,
        key=fact.content.key,
        value=fact.content.value,
        source_kind="manual_user",
    )
    assert item.authority == "explicit_user"


def test_fact_pack_value_is_read_only_data():
    fact = confirmed_fact()
    item = ProjectFactPackItem(
        fact_id=fact.fact_id,
        fact_hash=fact.record_hash,
        category=fact.content.category,
        key=fact.content.key,
        value=fact.content.value,
        source_kind="manual_user",
    )
    payload = item.model_dump(mode="json")
    forbidden_action_keys = {
        "command",
        "operation_id",
        "endpoint",
        "token",
        "claim_token",
    }
    assert forbidden_action_keys.isdisjoint(payload)
