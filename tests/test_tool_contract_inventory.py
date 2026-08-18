from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from app.main import app
from app.tool_contracts import (
    build_tool_registry,
    validate_tool_contract_system,
)
from app.tool_contracts.inventory import (
    TOOL_MODULE_POLICIES,
    validate_tool_inventory,
)


def test_real_tool_inventory_is_complete() -> None:
    report = validate_tool_contract_system()

    assert report.ok is True
    assert report.contracts_checked == 12
    assert report.modules_checked == len(TOOL_MODULE_POLICIES)
    assert report.issues == []


def test_inventory_detects_unreviewed_module(tmp_path: Path) -> None:
    # 为所有已声明模块创建占位文件，再额外增加 forgotten_tools.py。
    # 此测试只关心模块级遗漏，因此不要求占位模块具备真实公开函数。
    for module_name in TOOL_MODULE_POLICIES:
        (tmp_path / f"{module_name}.py").write_text("", encoding="utf-8")
    (tmp_path / "forgotten_tools.py").write_text(
        "def unsafe_tool():\n"
        "    return 'unexpected'\n",
        encoding="utf-8",
    )

    issues, _ = validate_tool_inventory(
        build_tool_registry(),
        tools_dir=tmp_path,
    )

    assert any(
        item.code == "TOOL_MODULE_NOT_IN_INVENTORY"
        and item.target == "forgotten_tools"
        for item in issues
    )


def test_inventory_detects_unreviewed_public_function(
    tmp_path: Path,
) -> None:
    for module_name in TOOL_MODULE_POLICIES:
        content = ""
        policy = TOOL_MODULE_POLICIES[module_name]
        for function_name in policy.exported_functions:
            content += f"def {function_name}():\n    pass\n\n"
        if module_name == "code_tools":
            content += "def forgotten_reader():\n    pass\n"
        (tmp_path / f"{module_name}.py").write_text(
            content,
            encoding="utf-8",
        )

    issues, _ = validate_tool_inventory(
        build_tool_registry(),
        tools_dir=tmp_path,
    )

    assert any(
        item.code == "PUBLIC_TOOL_FUNCTION_NOT_REVIEWED"
        and item.target == "code_tools.forgotten_reader"
        for item in issues
    )


def test_validate_tool_contracts_cli() -> None:
    result = CliRunner().invoke(
        app,
        ["validate-tool-contracts"],
    )

    assert result.exit_code == 0
    assert "contracts_checked" in result.stdout
    assert "phase40-v1" in result.stdout
    assert "TOOL_MODULE_NOT_IN_INVENTORY" not in result.stdout
