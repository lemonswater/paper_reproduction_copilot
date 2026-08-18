from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.skills.registry import (
    SkillDefinition,
    SkillRegistry,
)
from app.skills.schemas import (
    SkillInvocationContext,
    SkillInvocationRequest,
)
from app.tool_contracts.catalog import build_tool_registry
from tests.skill_test_helpers import write_skill_package


class EchoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str


class EchoOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    diagnosis: str


def _context(tmp_path) -> SkillInvocationContext:
    return SkillInvocationContext(
        actor="test",
        request_id="registry-test",
        workspace_root=str(tmp_path),
        run_root=str(tmp_path),
        granted_capabilities=[],
    )


def _bound_registry(tmp_path, *, enabled: bool, calls: list[str]):
    package = write_skill_package(tmp_path / "packages")

    def handler(payload: EchoInput, runtime) -> EchoOutput:
        del runtime
        calls.append(payload.value)
        return EchoOutput(diagnosis=payload.value)

    registry = SkillRegistry(tool_registry=build_tool_registry())
    bound = registry.register(
        package=package,
        definition=SkillDefinition(
            implementation_id="builtin.example_skill.v1",
            input_schema_id="skill.example_skill.input.v1",
            output_schema_id="skill.example_skill.output.v1",
            input_model=EchoInput,
            output_model=EchoOutput,
            handler=handler,
        ),
        enabled=enabled,
    )
    return registry, bound


def test_disabled_skill_does_not_call_handler(tmp_path):
    calls: list[str] = []
    registry, bound = _bound_registry(
        tmp_path,
        enabled=False,
        calls=calls,
    )

    result = registry.invoke(
        request=SkillInvocationRequest(
            skill_id="example_skill",
            skill_version="1.0.0",
            expected_skill_sha256=bound.skill_sha256,
            input_payload={"value": "must-not-run"},
        ),
        context=_context(tmp_path),
    )

    assert result.failure is not None
    assert result.failure.code == "SKILL_DISABLED"
    assert result.record.tool_calls == []
    assert calls == []


def test_stale_skill_hash_does_not_call_handler(tmp_path):
    calls: list[str] = []
    registry, _ = _bound_registry(
        tmp_path,
        enabled=True,
        calls=calls,
    )

    result = registry.invoke(
        request=SkillInvocationRequest(
            skill_id="example_skill",
            skill_version="1.0.0",
            expected_skill_sha256="0" * 64,
            input_payload={"value": "must-not-run"},
        ),
        context=_context(tmp_path),
    )

    assert result.failure is not None
    assert result.failure.code == "SKILL_STALE_IDENTITY"
    assert result.record.tool_calls == []
    assert calls == []


def test_matching_hash_returns_typed_output(tmp_path):
    calls: list[str] = []
    registry, bound = _bound_registry(
        tmp_path,
        enabled=True,
        calls=calls,
    )

    result = registry.invoke(
        request=SkillInvocationRequest(
            skill_id="example_skill",
            skill_version="1.0.0",
            expected_skill_sha256=bound.skill_sha256,
            input_payload={"value": "diagnosed"},
        ),
        context=_context(tmp_path),
    )

    assert result.failure is None
    assert result.output == {"diagnosis": "diagnosed"}
    assert result.record.output_sha256 is not None
    assert calls == ["diagnosed"]
