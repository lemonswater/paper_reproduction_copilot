from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_SOURCE_ROOT = PROJECT_ROOT / "app" / "skills"
PLUGIN_ROOT = PROJECT_ROOT / "agent_skills"

FORBIDDEN_IMPORT_PREFIXES = (
    "app.execution",
    "app.nodes.executor_node",
    "app.nodes.human_review_node",
    "app.nodes.patch_executor_node",
    "app.nodes.patch_apply_node",
    "app.secrets",
    "subprocess",
    "importlib",
)


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            values.append(node.module)
    return values


def test_skill_source_has_no_direct_privileged_imports():
    violations: list[str] = []
    for path in sorted(SKILL_SOURCE_ROOT.rglob("*.py")):
        for imported in _imports(path):
            if imported.startswith(FORBIDDEN_IMPORT_PREFIXES):
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)} -> {imported}"
                )

    assert violations == []


def test_plugin_packages_contain_no_python_or_native_code():
    forbidden_suffixes = {".py", ".pyc", ".so", ".dll", ".dylib", ".sh"}
    violations = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in PLUGIN_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in forbidden_suffixes
    ]

    assert violations == []
