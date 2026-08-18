from __future__ import annotations

import ast
from pathlib import Path

from app.tool_calling.catalog import STATIC_BINDINGS


ROOT = Path(__file__).resolve().parents[1]

MUTATION_MARKERS = {
    "submit_decision",
    "cancel_job",
    "create_job",
    "create_proposal",
    "approve_resource",
    "apply_patch",
    "run_command",
}


def test_chat_tool_catalog_contains_no_mutation_names() -> None:
    material = " ".join(
        list(STATIC_BINDINGS)
        + list(STATIC_BINDINGS.values())
    )
    assert all(marker not in material for marker in MUTATION_MARKERS)


def test_tool_calling_package_has_no_shell_or_process_imports() -> None:
    forbidden_modules = {
        "subprocess",
        "pty",
        "pexpect",
    }
    for path in (ROOT / "app" / "tool_calling").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(item.name.split(".")[0] for item in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert imported.isdisjoint(forbidden_modules), path


def test_tool_calling_does_not_import_execution_or_approval_modules() -> None:
    forbidden = {
        "app.nodes.executor_node",
        "app.nodes.human_review_node",
        "app.execution",
        "app.patch",
        "app.resource_acquisition.worker",
    }
    for path in (ROOT / "app" / "tool_calling").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert all(item not in source for item in forbidden), path


def test_live_research_tool_is_not_in_chat_catalog() -> None:
    assert "browser.collect_research_evidence" not in (
        STATIC_BINDINGS.values()
    )
