from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "app" / "mcp_contracts"

FORBIDDEN_IMPORT_PREFIXES = {
    "app.execution",
    "app.nodes.executor_node",
    "app.nodes.human_review_node",
    "app.repair",
    "app.resources.worker",
    "app.research_browser",
    "app.model_routing",
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_contract_package_does_not_import_mutation_runtime() -> None:
    violations = []
    for path in PACKAGE.glob("*.py"):
        for module in imported_modules(path):
            if any(
                module == prefix or module.startswith(prefix + ".")
                for prefix in FORBIDDEN_IMPORT_PREFIXES
            ):
                violations.append(f"{path.name}:{module}")
    assert violations == []


def test_contract_package_has_no_business_tool_invocation() -> None:
    forbidden_calls = {
        "run_command",
        "apply_patch",
        "submit_decision",
        "approve_action",
        "cancel_job",
    }
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in PACKAGE.glob("*.py")
    )
    for name in forbidden_calls:
        assert f"{name}(" not in source
