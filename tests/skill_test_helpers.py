from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.skills.loader import (
    DiscoveredSkillPackage,
    load_skill_package,
)


def base_manifest(
    *,
    skill_id: str = "example_skill",
    implementation_id: str = "builtin.example_skill.v1",
) -> dict[str, Any]:
    return {
        "manifest_version": "phase48-v1",
        "skill_id": skill_id,
        "skill_version": "1.0.0",
        "display_name": "Example Skill",
        "summary": "Fixture Skill used by unit tests.",
        "implementation_id": implementation_id,
        "input_schema_id": f"skill.{skill_id}.input.v1",
        "output_schema_id": f"skill.{skill_id}.output.v1",
        "required_tools": [
            {
                "name": "log.extract_traceback",
                "version": "phase40-v1",
            }
        ],
        "required_capabilities": [],
        "side_effect_level": "proposal_only",
        "prompt_or_policy_version": "fixture-v1",
        "eval_suite": "fixture_skill_eval_v1",
        "feature_flag": f"skill.{skill_id}",
        "max_tool_calls": 1,
        "max_duration_ms": 5000,
        "resources": [],
    }


def write_skill_package(
    root: Path,
    manifest: dict[str, Any] | None = None,
) -> DiscoveredSkillPackage:
    payload = manifest or base_manifest()
    package_dir = root / str(payload["skill_id"])
    package_dir.mkdir(parents=True)
    (package_dir / "skill.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return load_skill_package(package_dir, package_root=root)
