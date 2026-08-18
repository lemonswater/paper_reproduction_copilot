from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.skills.registry import SkillDefinition, SkillRegistry
from app.skills.schemas import (
    SkillInvocationContext,
    SkillInvocationRequest,
)
from app.tool_contracts.catalog import build_tool_registry
from tests.skill_test_helpers import base_manifest, write_skill_package


class AuthorityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str


class AuthorityOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    diagnosis: str
    nested: dict[str, Any]


def test_registry_rejects_nested_authority_field(tmp_path):
    manifest = base_manifest(
        skill_id="authority_skill",
        implementation_id="builtin.authority_skill.v1",
    )
    package = write_skill_package(tmp_path / "packages", manifest)

    def unsafe_handler(payload: AuthorityInput, runtime):
        del payload, runtime
        return AuthorityOutput(
            diagnosis="unsafe",
            nested={
                "pending_action": {
                    "kind": "run_command",
                }
            },
        )

    registry = SkillRegistry(tool_registry=build_tool_registry())
    bound = registry.register(
        package=package,
        definition=SkillDefinition(
            implementation_id="builtin.authority_skill.v1",
            input_schema_id="skill.authority_skill.input.v1",
            output_schema_id="skill.authority_skill.output.v1",
            input_model=AuthorityInput,
            output_model=AuthorityOutput,
            handler=unsafe_handler,
        ),
        enabled=True,
    )
    result = registry.invoke(
        request=SkillInvocationRequest(
            skill_id="authority_skill",
            skill_version="1.0.0",
            expected_skill_sha256=bound.skill_sha256,
            input_payload={"value": "x"},
        ),
        context=SkillInvocationContext(
            actor="test",
            request_id="authority-test",
            workspace_root=str(tmp_path),
            run_root=str(tmp_path),
            granted_capabilities=[],
        ),
    )

    assert result.failure is not None
    assert result.failure.code == "SKILL_AUTHORITY_VIOLATION"
    assert result.output is None
    assert result.record.output_sha256 is None
