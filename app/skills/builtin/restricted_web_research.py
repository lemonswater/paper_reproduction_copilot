from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.research_browser.schemas import ResearchEvidenceDraft, ResearchRequest
from app.skills.runtime import SkillRuntime


class ResearchSkillModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RestrictedWebResearchInput(ResearchSkillModel):
    request: ResearchRequest


class RestrictedWebResearchOutput(ResearchSkillModel):
    evidence: ResearchEvidenceDraft
    requires_main_agent_synthesis: bool = True
    requires_explicit_resource_review: bool = True


def run_restricted_web_research(
    payload: RestrictedWebResearchInput,
    runtime: SkillRuntime,
) -> RestrictedWebResearchOutput:
    output = runtime.call_tool(
        "browser.collect_research_evidence",
        {"request": payload.request.model_dump(mode="json")},
    )
    return RestrictedWebResearchOutput(
        evidence=ResearchEvidenceDraft.model_validate(output["evidence"]),
    )
