from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.skills.catalog import build_skill_registry
from app.skills.schemas import (
    SkillInvocationContext,
    SkillInvocationRequest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = (
    PROJECT_ROOT
    / "app"
    / "evaluation"
    / "skill_cases"
    / "cuda_build_diagnosis_offline_v1.json"
)
FIXTURE_ROOT = (
    PROJECT_ROOT
    / "app"
    / "evaluation"
    / "fixtures"
    / "skills"
    / "cuda_build"
)


def _contains_forbidden_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in forbidden
            or _contains_forbidden_key(child, forbidden)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(
            _contains_forbidden_key(child, forbidden)
            for child in value
        )
    return False


def test_cuda_build_skill_matches_offline_golden_case():
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    case = suite["cases"][0]
    registry = build_skill_registry(
        package_root=PROJECT_ROOT / "agent_skills",
        globally_enabled=True,
        enabled_skill_ids={"cuda_build_diagnosis"},
    )
    bound = registry.get("cuda_build_diagnosis")

    result = registry.invoke(
        request=SkillInvocationRequest(
            skill_id=suite["skill_id"],
            skill_version=suite["skill_version"],
            expected_skill_sha256=bound.skill_sha256,
            input_payload=case["input"],
        ),
        context=SkillInvocationContext(
            actor="eval:phase48",
            request_id=case["case_id"],
            workspace_root=str(FIXTURE_ROOT / "workspace"),
            run_root=str(FIXTURE_ROOT / "run"),
            granted_capabilities=[
                "filesystem.read.workspace",
                "filesystem.read.run",
                "process.spawn.rg",
            ],
        ),
    )

    assert result.failure is None
    assert result.output is not None
    expected = case["expected"]
    assert result.output["error_category"] == expected["error_category"]
    assert set(expected["required_finding_codes"]).issubset(
        result.output["finding_codes"]
    )
    assert set(expected["required_related_files"]).issubset(
        result.output["related_files"]
    )
    assert result.output["confidence"] >= expected["minimum_confidence"]
    assert len(result.record.tool_calls) <= expected["maximum_tool_calls"]
    assert all(
        item.status == "succeeded"
        for item in result.record.tool_calls
    )
    assert not _contains_forbidden_key(
        result.output,
        set(expected["forbidden_output_keys"]),
    )
