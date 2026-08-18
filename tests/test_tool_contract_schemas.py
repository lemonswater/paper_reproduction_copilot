from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.tool_contracts.schemas import (
    ToolContract,
    ToolDeterminism,
    ToolEffect,
    ToolExposure,
    ToolRisk,
)


def _contract(**updates) -> ToolContract:
    values = {
        "name": "demo.echo",
        "version": "phase40-v1",
        "summary": "test contract",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "effects": [ToolEffect.NONE],
        "required_capabilities": [],
        "exposure": ToolExposure.AGENT_READ_ONLY,
        "risk_level": ToolRisk.LOW,
        "determinism": ToolDeterminism.DETERMINISTIC,
        "idempotent": True,
        "timeout_seconds": None,
        "audit_event": "tool.demo.echo",
        "path_scopes": [],
        "declared_errors": [],
    }
    values.update(updates)
    return ToolContract.model_validate(values)


def test_pure_read_only_contract_is_valid() -> None:
    contract = _contract()

    assert contract.name == "demo.echo"
    assert contract.effects == [ToolEffect.NONE]


def test_none_cannot_be_combined_with_other_effects() -> None:
    with pytest.raises(ValidationError, match="none 不能与其他副作用"):
        _contract(
            effects=[
                ToolEffect.NONE,
                ToolEffect.FILESYSTEM_READ,
            ],
            required_capabilities=["filesystem.read.workspace"],
        )


def test_effectful_tool_requires_capability() -> None:
    with pytest.raises(ValidationError, match="required_capabilities"):
        _contract(effects=[ToolEffect.FILESYSTEM_READ])


def test_process_tool_requires_timeout() -> None:
    with pytest.raises(ValidationError, match="timeout_seconds"):
        _contract(
            effects=[ToolEffect.PROCESS_SPAWN],
            required_capabilities=["process.spawn.rg"],
        )


def test_agent_read_only_cannot_write() -> None:
    with pytest.raises(ValidationError, match="不能声明写或控制副作用"):
        _contract(
            effects=[ToolEffect.FILESYSTEM_WRITE],
            required_capabilities=["filesystem.write.workspace"],
        )


def test_high_risk_tool_cannot_be_agent_read_only() -> None:
    with pytest.raises(ValidationError, match="高风险工具"):
        _contract(risk_level=ToolRisk.HIGH)
