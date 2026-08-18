from __future__ import annotations

import json
from pathlib import Path

from app.skills.builtin.cuda_build_diagnosis import (
    CudaBuildDiagnosisInput,
    CudaBuildDiagnosisOutput,
    diagnose_cuda_build,
)
from app.skills.builtin.restricted_web_research import (
    RestrictedWebResearchInput,
    RestrictedWebResearchOutput,
    run_restricted_web_research,
)
from app.skills.loader import discover_skill_packages
from app.skills.registry import (
    SkillDefinition,
    SkillRegistry,
    SkillRegistryError,
)
from app.skills.schemas import SkillManifest
from app.tool_contracts.catalog import build_tool_registry


BUILTIN_SKILL_DEFINITIONS = {
    "builtin.cuda_build_diagnosis.v1": SkillDefinition(
        implementation_id="builtin.cuda_build_diagnosis.v1",
        input_schema_id="skill.cuda_build_diagnosis.input.v1",
        output_schema_id="skill.cuda_build_diagnosis.output.v1",
        input_model=CudaBuildDiagnosisInput,
        output_model=CudaBuildDiagnosisOutput,
        handler=diagnose_cuda_build,
    ),
    "builtin.restricted_web_research.v1": SkillDefinition(
        implementation_id="builtin.restricted_web_research.v1",
        input_schema_id="skill.restricted_web_research.input.v1",
        output_schema_id="skill.restricted_web_research.output.v1",
        input_model=RestrictedWebResearchInput,
        output_model=RestrictedWebResearchOutput,
        handler=run_restricted_web_research,
    ),
}


def _eval_case_path(eval_suite: str) -> Path:
    project_root = Path(__file__).resolve().parents[2]
    return (
        project_root
        / "app"
        / "evaluation"
        / "skill_cases"
        / f"{eval_suite}.json"
    )


def _validate_eval_suite(manifest: SkillManifest) -> None:
    path = _eval_case_path(manifest.eval_suite)
    if path.is_symlink() or not path.is_file():
        raise SkillRegistryError(
            "Skill 缺少声明的离线 Eval Suite："
            f"{manifest.eval_suite}"
        )
    if path.stat().st_size > 1024 * 1024:
        raise SkillRegistryError("Skill Eval Suite 超过 1 MiB")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SkillRegistryError("Skill Eval Suite 不是有效 JSON") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("suite_version") not in {"phase48-v1", "phase51-v1"}
        or payload.get("skill_id") != manifest.skill_id
        or payload.get("skill_version") != manifest.skill_version
        or not isinstance(payload.get("cases"), list)
        or not payload["cases"]
    ):
        raise SkillRegistryError(
            "Skill Eval Suite 身份不匹配或没有 Golden Case"
        )


def build_skill_registry(
    *,
    package_root: Path,
    globally_enabled: bool,
    enabled_skill_ids: set[str],
    tool_registry=None,
) -> SkillRegistry:
    """从静态实现表和受控 Manifest 构建本进程 Registry。"""

    selected_tools = tool_registry or build_tool_registry()
    registry = SkillRegistry(tool_registry=selected_tools)
    for package in discover_skill_packages(package_root):
        implementation_id = package.manifest.implementation_id
        definition = BUILTIN_SKILL_DEFINITIONS.get(implementation_id)
        if definition is None:
            raise SkillRegistryError(
                "Plugin Manifest 引用了未知内置实现："
                f"{implementation_id}"
            )
        _validate_eval_suite(package.manifest)
        enabled = (
            globally_enabled
            and package.manifest.skill_id in enabled_skill_ids
        )
        required_tool_names = {
            item.name for item in package.manifest.required_tools
        }
        # Optional integrations may be absent while their Skill is disabled.
        # Enabled Skills still fail closed in registry.register below.
        if not enabled and not required_tool_names.issubset(
            set(selected_tools.names())
        ):
            continue
        registry.register(
            package=package,
            definition=definition,
            enabled=enabled,
        )
    return registry
