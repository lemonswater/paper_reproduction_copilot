import json
from pathlib import Path

from app.research_browser.tooling import ResearchToolBindings
from app.skills.catalog import build_skill_registry
from app.skills.schemas import SkillInvocationContext, SkillInvocationRequest
from app.tool_contracts.catalog import build_tool_registry

from tests.research_browser_helpers import evidence_draft


ROOT = Path(__file__).resolve().parents[1]
SUITE = (
    ROOT
    / "app"
    / "evaluation"
    / "skill_cases"
    / "restricted_web_research_offline_v1.json"
)


class FixtureCollector:
    def collect(self, request):
        del request
        return evidence_draft()


def test_restricted_research_skill_matches_offline_suite() -> None:
    suite = json.loads(SUITE.read_text(encoding="utf-8"))
    case = suite["cases"][0]
    tools = build_tool_registry(
        research_bindings=ResearchToolBindings(
            collector=FixtureCollector()
        )
    )
    registry = build_skill_registry(
        package_root=ROOT / "agent_skills",
        globally_enabled=True,
        enabled_skill_ids={"restricted_web_research"},
        tool_registry=tools,
    )
    bound = registry.get(suite["skill_id"])
    result = registry.invoke(
        request=SkillInvocationRequest(
            skill_id=suite["skill_id"],
            skill_version=suite["skill_version"],
            expected_skill_sha256=bound.skill_sha256,
            input_payload=case["input"],
        ),
        context=SkillInvocationContext(
            actor="eval:phase51",
            request_id=case["case_id"],
            job_id="job-research-golden",
            workspace_root=str(ROOT),
            run_root=str(ROOT / "runs"),
            granted_capabilities=["network.read.research"],
        ),
    )
    assert result.failure is None
    assert result.output is not None
    assert len(result.output["evidence"]["citations"]) >= 1
    assert result.output["requires_main_agent_synthesis"] is True
    assert result.output["requires_explicit_resource_review"] is True
    assert len(result.record.tool_calls) == 1
    assert result.record.tool_calls[0].tool_name == (
        "browser.collect_research_evidence"
    )


def test_skill_manifest_matches_suite() -> None:
    suite = json.loads(SUITE.read_text(encoding="utf-8"))
    manifest_path = ROOT / "agent_skills" / "restricted_web_research" / "skill.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["skill_id"] == suite["skill_id"]
    assert manifest["skill_version"] == suite["skill_version"]
    assert manifest["eval_suite"] == "restricted_web_research_offline_v1"
