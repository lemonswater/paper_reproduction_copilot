from __future__ import annotations

import json

from app.model_routing.errors import ModelBudgetExceeded
from app.model_routing.gateway import ModelGateway
from app.prompts.research_browser_prompt import RESEARCH_SYNTHESIS_PROMPT
from app.research_browser.errors import ResearchSynthesisRejected
from app.research_browser.schemas import (
    ResearchEvidenceDraft,
    ResearchReport,
    ResearchRequest,
    ResearchSynthesisDraft,
)
from app.secrets.redaction import SecretRedactor


class ResearchSynthesizer:
    def __init__(self, *, gateway: ModelGateway, redactor: SecretRedactor) -> None:
        self.gateway = gateway
        self.redactor = redactor

    def synthesize(
        self,
        *,
        request: ResearchRequest,
        evidence: ResearchEvidenceDraft,
    ) -> ResearchReport:
        if not evidence.citations:
            return ResearchReport(
                synthesis_status="insufficient_evidence",
                answer="没有取得可验证的外部正文证据。",
                citations=[],
                resource_candidates=[],
            )

        citation_by_id = {item.citation_id: item for item in evidence.citations}
        candidate_by_id = {
            item.candidate_id: item for item in evidence.resource_candidates
        }
        # Prompt 只包含有界 excerpt；不包含原始 HTML/PDF、Header 或 Search 响应。
        external = [
            {
                "citation_id": item.citation_id,
                "label": item.label,
                "locator": item.locator,
                "excerpt": item.excerpt,
                "content_trust": "untrusted_external_data",
            }
            for item in evidence.citations
        ]
        prompt = RESEARCH_SYNTHESIS_PROMPT.format(
            allowed_citation_ids=json.dumps(sorted(citation_by_id)),
            allowed_resource_candidate_ids=json.dumps(sorted(candidate_by_id)),
            user_query=self.redactor.redact_text(request.query, max_chars=400),
            external_evidence_json=json.dumps(
                external,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        try:
            invocation = self.gateway.invoke_structured(
                task_kind="web_research_synthesis",
                schema=ResearchSynthesisDraft,
                prompt=prompt,
                node_name="research_browser_synthesis",
                job_id=request.job_id,
                quality_tier="balanced",
                requested_max_output_tokens=1200,
            )
        except ModelBudgetExceeded:
            return ResearchReport(
                synthesis_status="budget_denied",
                answer="已取得外部证据，但模型预算不足，暂未生成综合结论。",
                citations=evidence.citations[:8],
                resource_candidates=[],
            )

        draft = invocation.value
        if draft is None:
            return ResearchReport(
                synthesis_status="evidence_only",
                answer="已取得外部证据，但结构化综合失败。",
                citations=evidence.citations[:8],
                resource_candidates=[],
                model_invocation_id=invocation.invocation_id,
                model_decision_sha256=invocation.decision.decision_sha256,
            )
        unknown_citations = set(draft.citation_ids) - set(citation_by_id)
        unknown_candidates = set(draft.resource_candidate_ids) - set(candidate_by_id)
        if unknown_citations or unknown_candidates:
            raise ResearchSynthesisRejected("RESEARCH_SYNTHESIS_UNKNOWN_REFERENCE")

        answer = self.redactor.redact_text(draft.answer, max_chars=6000)
        return ResearchReport(
            synthesis_status=(
                "insufficient_evidence"
                if draft.insufficient_evidence
                else "succeeded"
            ),
            answer=answer,
            citations=[citation_by_id[item] for item in draft.citation_ids],
            resource_candidates=[
                candidate_by_id[item] for item in draft.resource_candidate_ids
            ],
            model_invocation_id=invocation.invocation_id,
            model_decision_sha256=invocation.decision.decision_sha256,
        )
