from pathlib import Path


FORBIDDEN_IMPORTS = {
    "subprocess",
    "app.execution",
    "app.repair",
    "app.interaction.decisions",
}


def test_knowledge_modules_do_not_import_execution_authority():
    root = Path("app/knowledge_base")
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(root.glob("*.py"))
    )
    for forbidden in FORBIDDEN_IMPORTS:
        assert f"import {forbidden}" not in source
        assert f"from {forbidden}" not in source
