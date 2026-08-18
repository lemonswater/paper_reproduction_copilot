from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.skills.runtime import SkillRuntime, SkillRuntimeError
from app.skills.schemas import SkillInvocationContext, SkillManifest
from app.tool_contracts.catalog import build_tool_registry


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _cuda_manifest() -> SkillManifest:
    payload = json.loads(
        (
            PROJECT_ROOT
            / "agent_skills"
            / "cuda_build_diagnosis"
            / "skill.json"
        ).read_text(encoding="utf-8")
    )
    return SkillManifest.model_validate(payload)


def _context(tmp_path, *, capabilities: list[str]):
    workspace = tmp_path / "workspace"
    run = tmp_path / "run"
    workspace.mkdir(exist_ok=True)
    run.mkdir(exist_ok=True)
    return SkillInvocationContext(
        actor="test",
        request_id="runtime-test",
        workspace_root=str(workspace),
        run_root=str(run),
        granted_capabilities=capabilities,
    )


def test_runtime_rejects_undeclared_tool(tmp_path):
    runtime = SkillRuntime(
        manifest=_cuda_manifest(),
        tool_registry=build_tool_registry(),
        context=_context(
            tmp_path,
            capabilities=[
                "filesystem.read.workspace",
                "filesystem.read.run",
                "process.spawn.rg",
            ],
        ),
    )

    with pytest.raises(SkillRuntimeError) as exc_info:
        runtime.call_tool("code.read_file_slice", {"path": "x.py"})

    assert exc_info.value.code == "SKILL_TOOL_NOT_DECLARED"
    assert runtime.tool_call_refs == []


def test_runtime_rejects_missing_host_capability(tmp_path):
    runtime = SkillRuntime(
        manifest=_cuda_manifest(),
        tool_registry=build_tool_registry(),
        context=_context(
            tmp_path,
            capabilities=["filesystem.read.run"],
        ),
    )

    with pytest.raises(SkillRuntimeError) as exc_info:
        runtime.call_tool(
            "log.read_log",
            {"path": "execution.log", "max_chars": 1000},
        )

    assert exc_info.value.code == "SKILL_CAPABILITY_NOT_GRANTED"
    assert runtime.tool_call_refs == []


def test_runtime_rejects_trusted_node_tool(tmp_path):
    payload = _cuda_manifest().model_dump(mode="json")
    payload["required_tools"] = [
        {
            "name": "risk.assess_action_risk",
            "version": "phase40-v1",
        }
    ]
    payload["required_capabilities"] = []
    payload["max_tool_calls"] = 1
    runtime = SkillRuntime(
        manifest=SkillManifest.model_validate(payload),
        tool_registry=build_tool_registry(),
        context=_context(tmp_path, capabilities=[]),
    )

    with pytest.raises(SkillRuntimeError) as exc_info:
        runtime.call_tool(
            "risk.assess_action_risk",
            {"action": {"kind": "run_command"}},
        )

    assert exc_info.value.code == "SKILL_TOOL_EXPOSURE_DENIED"
    assert runtime.tool_call_refs == []


def test_runtime_enforces_tool_call_budget(tmp_path):
    payload = _cuda_manifest().model_dump(mode="json")
    payload["required_tools"] = [
        {
            "name": "log.extract_traceback",
            "version": "phase40-v1",
        }
    ]
    payload["required_capabilities"] = []
    payload["max_tool_calls"] = 1
    runtime = SkillRuntime(
        manifest=SkillManifest.model_validate(payload),
        tool_registry=build_tool_registry(),
        context=_context(tmp_path, capabilities=[]),
    )

    runtime.call_tool("log.extract_traceback", {"text": "ValueError: x"})
    with pytest.raises(SkillRuntimeError) as exc_info:
        runtime.call_tool("log.extract_traceback", {"text": "ValueError: y"})

    assert exc_info.value.code == "SKILL_TOOL_BUDGET_EXCEEDED"
    assert len(runtime.tool_call_refs) == 1
