from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "app" / "mcp_export"

FORBIDDEN_IMPORT_PREFIXES = {
    "app.execution",
    "app.nodes.executor_node",
    "app.nodes.human_review_node",
    "app.repair",
    "app.resources.worker",
    "app.research_browser",
    "app.mcp_gateway",
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


def test_mcp_export_does_not_import_mutation_or_network_runtime() -> None:
    violations = []
    for path in PACKAGE.glob("*.py"):
        for module in imported_modules(path):
            if any(
                module == prefix or module.startswith(prefix + ".")
                for prefix in FORBIDDEN_IMPORT_PREFIXES
            ):
                violations.append((path.name, module))
    assert violations == []


def test_service_does_not_use_direct_filesystem_or_process_apis() -> None:
    source = (PACKAGE / "service.py").read_text(encoding="utf-8")
    for forbidden in [
        "subprocess.",
        "os.system",
        "shell=True",
        "requests.",
        "httpx.",
        ".read_text(",
        ".read_bytes(",
        ".open(",
    ]:
        assert forbidden not in source


def test_server_exports_no_mutation_names() -> None:
    source = (PACKAGE / "server.py").read_text(encoding="utf-8")
    for forbidden in [
        "submit_decision",
        "approve_action",
        "run_command",
        "apply_patch",
        "cancel_job",
        "request_resource",
    ]:
        assert f"def {forbidden}" not in source
