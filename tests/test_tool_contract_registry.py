from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import Field

from app.tool_contracts.errors import ToolRegistryError
from app.tool_contracts.registry import (
    InMemoryToolAuditSink,
    ToolRegistry,
    build_tool_definition,
)
from app.tool_contracts.schemas import (
    ContractModel,
    ToolDeterminism,
    ToolEffect,
    ToolErrorSpec,
    ToolExposure,
    ToolFailure,
    ToolInvocationContext,
    ToolRisk,
)


class EchoInput(ContractModel):
    value: str = Field(min_length=1)


class EchoOutput(ContractModel):
    echoed: str


class DemoFailure(RuntimeError):
    pass


def _context() -> ToolInvocationContext:
    return ToolInvocationContext(
        actor="test",
        request_id="request-1",
        caller_kind="agent",
    )


def _definition(handler, error_mapper=lambda exc: None):
    return build_tool_definition(
        name="demo.echo",
        version="phase40-v1",
        summary="echo fixture",
        input_model=EchoInput,
        output_model=EchoOutput,
        handler=handler,
        error_mapper=error_mapper,
        effects=[ToolEffect.NONE],
        required_capabilities=[],
        exposure=ToolExposure.AGENT_READ_ONLY,
        risk_level=ToolRisk.LOW,
        determinism=ToolDeterminism.DETERMINISTIC,
        idempotent=True,
        timeout_seconds=None,
        audit_event="tool.demo.echo",
        path_scopes=[],
        declared_errors=[
            ToolErrorSpec(
                code="DEMO_FAILED",
                category="tool",
                summary="demo failure",
            )
        ],
    )


def test_registry_success_validates_output_and_writes_hash_only_audit() -> None:
    def handler(payload, context):
        assert context.actor == "test"
        return {"echoed": payload.value}

    registry = ToolRegistry()
    registry.register(_definition(handler))
    audit = InMemoryToolAuditSink()

    result = registry.invoke(
        name="demo.echo",
        raw_input={"value": "secret-canary-value"},
        context=_context(),
        audit_sink=audit,
    )

    assert result.failure is None
    assert result.output == {"echoed": "secret-canary-value"}
    assert result.record.status == "succeeded"
    assert len(audit.records) == 1
    # Audit 只保存 hash；真实输出返回调用方，但不复制进审计记录。
    assert "secret-canary-value" not in audit.records[0].model_dump_json()


def test_registry_rejects_invalid_input_before_handler() -> None:
    called = False

    def handler(payload, context):
        nonlocal called
        called = True
        return {"echoed": payload.value}

    registry = ToolRegistry()
    registry.register(_definition(handler))

    result = registry.invoke(
        name="demo.echo",
        raw_input={},
        context=_context(),
    )

    assert called is False
    assert result.failure is not None
    assert result.failure.code == "TOOL_INPUT_INVALID"


def test_registry_detects_output_schema_drift() -> None:
    registry = ToolRegistry()
    registry.register(
        _definition(lambda payload, context: {"unexpected": payload.value})
    )

    result = registry.invoke(
        name="demo.echo",
        raw_input={"value": "hello"},
        context=_context(),
    )

    assert result.failure is not None
    assert result.failure.code == "TOOL_OUTPUT_INVALID"


def test_registry_maps_declared_error() -> None:
    def handler(payload, context):
        raise DemoFailure("do not expose this raw detail")

    def mapper(exc):
        if isinstance(exc, DemoFailure):
            return ToolFailure(
                code="DEMO_FAILED",
                category="tool",
                message="demo failed safely",
            )
        return None

    registry = ToolRegistry()
    registry.register(_definition(handler, mapper))

    result = registry.invoke(
        name="demo.echo",
        raw_input={"value": "hello"},
        context=_context(),
    )

    assert result.failure is not None
    assert result.failure.code == "DEMO_FAILED"
    assert "raw detail" not in result.failure.message


def test_registry_marks_unknown_exception_as_undeclared() -> None:
    def handler(payload, context):
        raise RuntimeError("unexpected")

    registry = ToolRegistry()
    registry.register(_definition(handler))

    result = registry.invoke(
        name="demo.echo",
        raw_input={"value": "hello"},
        context=_context(),
    )

    assert result.failure is not None
    assert result.failure.code == "TOOL_UNDECLARED_EXCEPTION"


def test_registry_contains_broken_error_mapper() -> None:
    def handler(payload, context):
        raise DemoFailure("original")

    def broken_mapper(exc):
        raise RuntimeError("mapper is broken")

    registry = ToolRegistry()
    registry.register(_definition(handler, broken_mapper))

    result = registry.invoke(
        name="demo.echo",
        raw_input={"value": "hello"},
        context=_context(),
    )

    assert result.failure is not None
    assert result.failure.code == "TOOL_ERROR_MAPPER_FAILED"


def test_registry_does_not_swallow_process_control_signal() -> None:
    def handler(payload, context):
        raise KeyboardInterrupt()

    registry = ToolRegistry()
    registry.register(_definition(handler))

    with pytest.raises(KeyboardInterrupt):
        registry.invoke(
            name="demo.echo",
            raw_input={"value": "hello"},
            context=_context(),
        )


def test_registry_rejects_duplicate_name() -> None:
    definition = _definition(
        lambda payload, context: {"echoed": payload.value}
    )
    registry = ToolRegistry()
    registry.register(definition)

    with pytest.raises(ToolRegistryError, match="重复注册"):
        registry.register(definition)


def test_definition_validation_detects_frozen_schema_drift() -> None:
    definition = _definition(
        lambda payload, context: {"echoed": payload.value}
    )
    drifted = replace(
        definition,
        contract=definition.contract.model_copy(
            update={"input_schema": {"type": "object"}}
        ),
    )
    registry = ToolRegistry()
    registry.register(drifted)

    issues = registry.validate_definitions()

    assert [item.code for item in issues] == ["INPUT_SCHEMA_DRIFT"]
