from __future__ import annotations

import ast
from pathlib import Path


VERIFIER_FILES = [
    Path("app/nodes/execution_verifier_node.py"),
    Path("app/nodes/patch_verdict_node.py"),
]

FORBIDDEN_IMPORTED_NAMES = {
    "subprocess",
    "run_action_safe",
    "build_execution_runner",
    "verify_patch_in_worktree",
    "apply_verified_patch_to_source",
}


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
    return names


def test_verifiers_do_not_import_execution_capabilities() -> None:
    for path in VERIFIER_FILES:
        imported = _imported_names(path)
        forbidden = sorted(
            imported.intersection(FORBIDDEN_IMPORTED_NAMES)
        )
        assert forbidden == [], (
            f"{path} imported execution authority: {forbidden}"
        )
