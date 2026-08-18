from __future__ import annotations

from pathlib import Path

from app.tool_contracts.catalog import build_tool_registry
from app.tool_contracts.inventory import validate_tool_inventory
from app.tool_contracts.schemas import ContractValidationReport


def validate_tool_contract_system(
    *,
    tools_dir: Path | None = None,
) -> ContractValidationReport:
    registry = build_tool_registry()
    definition_issues = registry.validate_definitions()
    inventory_issues, modules_checked = validate_tool_inventory(
        registry,
        tools_dir=tools_dir,
    )
    issues = [*definition_issues, *inventory_issues]
    return ContractValidationReport(
        ok=not issues,
        contracts_checked=len(registry.names()),
        modules_checked=modules_checked,
        issues=issues,
    )
