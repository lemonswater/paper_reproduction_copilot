from types import SimpleNamespace

import pytest

from app.research_browser.errors import (
    ResearchConflict,
    ResearchResourceCandidateRejected,
)
from app.research_browser.identity import sha256_value, without_hash
from app.research_browser.schemas import (
    ResearchEvidencePack,
    ResearchReport,
    ResearchResourceCandidate,
    ResearchResourceSelection,
)
from app.research_browser.service import ResearchBrowserService
from app.research_browser.catalog import LoadedResearchPolicy
from app.research_browser.identity import request_sha256

from tests.research_browser_helpers import (
    evidence_draft,
    evidence_pack,
    research_policy,
    research_request,
)


class FakeRepository:
    def __init__(self) -> None:
        self.packs: dict[str, ResearchEvidencePack] = {}
        self.resource_links: dict[str, str] = {}

    def initialize(self) -> None:
        pass

    def ping(self) -> None:
        pass

    def get_pack(self, session_id: str) -> ResearchEvidencePack:
        return self.packs[session_id]

    def record_resource_link(
        self,
        *,
        session_id: str,
        candidate_id: str,
        candidate_sha256: str,
        pack_sha256: str,
        idempotency_key: str,
        resource_id: str,
    ) -> str:
        if idempotency_key in self.resource_links:
            return self.resource_links[idempotency_key]
        self.resource_links[idempotency_key] = resource_id
        return resource_id


class FakeResourceService:
    def __init__(self) -> None:
        self.submit_calls = []
        self.approve_calls = []

    def submit(self, *, request, idempotency_key):
        self.submit_calls.append({
            "request": request,
            "idempotency_key": idempotency_key,
        })
        record = SimpleNamespace(
            resource_id="res_" + "a" * 24,
            request_sha256="3" * 64,
            status="awaiting_approval",
            version=0,
        )
        return record, True


class PassThroughRedactor:
    def redact_text(self, value: str, *, max_chars: int) -> str:
        return value[:max_chars]


def _build_service_with_pack(pack: ResearchEvidencePack):
    repo = FakeRepository()
    repo.packs["research_" + "z" * 24] = pack
    policy = research_policy()
    loaded = LoadedResearchPolicy(
        document=policy,
        policy_sha256="1" * 64,
        path=None,
    )
    resource_svc = FakeResourceService()
    svc = ResearchBrowserService(
        enabled=True,
        repository=repo,
        policy=loaded,
        skills=None,
        synthesizer=None,
        redactor=PassThroughRedactor(),
        resource_service=resource_svc,
        workspace_root="/tmp",
        run_root="/tmp/runs",
    )
    return svc, resource_svc


def test_resource_candidate_submit_creates_resource() -> None:
    evidence = evidence_draft()
    # Build a candidate
    from app.research_browser.identity import sha256_value, without_hash

    candidate = evidence.resource_candidates or []
    # Manually create a PDF candidate from the snapshot
    snapshot = evidence.snapshots[0]
    draft = ResearchResourceCandidate(
        candidate_id="rcand_" + "a" * 24,
        kind="paper_pdf",
        source_url_sanitized=snapshot.canonical_url,
        expected_sha256=snapshot.body_sha256,
        citation_ids=[evidence.citations[0].citation_id],
        reason="test candidate",
        candidate_sha256="0" * 64,
    )
    candidate_hash = sha256_value(without_hash(draft, "candidate_sha256"))
    candidate = draft.model_copy(update={"candidate_sha256": candidate_hash})

    report = ResearchReport(
        synthesis_status="succeeded",
        answer="test",
        citations=evidence.citations,
        resource_candidates=[candidate],
    )
    pack = evidence_pack()
    pack = pack.model_copy(update={
        "resource_candidates": [candidate],
        "report": report,
    })

    svc, resource_svc = _build_service_with_pack(pack)
    selection = ResearchResourceSelection(
        candidate_id=candidate.candidate_id,
        candidate_sha256=candidate.candidate_sha256,
        expected_pack_sha256=pack.pack_sha256,
        purpose="download verified paper",
    )
    resource = svc.submit_resource_candidate(
        session_id="research_" + "z" * 24,
        selection=selection,
        actor="test",
    )
    assert resource.status == "awaiting_approval"
    assert resource_svc.approve_calls == []
    assert resource_svc.submit_calls[0]["idempotency_key"] == (
        f"research-resource:research_{'z' * 24}:{candidate.candidate_id}"
    )


def test_pack_hash_mismatch_raises_conflict() -> None:
    evidence = evidence_draft()
    snapshot = evidence.snapshots[0]
    draft = ResearchResourceCandidate(
        candidate_id="rcand_" + "b" * 24,
        kind="paper_pdf",
        source_url_sanitized=snapshot.canonical_url,
        expected_sha256=snapshot.body_sha256,
        citation_ids=[evidence.citations[0].citation_id],
        reason="test",
        candidate_sha256="0" * 64,
    )
    candidate_hash = sha256_value(without_hash(draft, "candidate_sha256"))
    candidate = draft.model_copy(update={"candidate_sha256": candidate_hash})

    pack = evidence_pack()
    pack = pack.model_copy(update={"resource_candidates": [candidate]})

    svc, _ = _build_service_with_pack(pack)
    selection = ResearchResourceSelection(
        candidate_id=candidate.candidate_id,
        candidate_sha256=candidate.candidate_sha256,
        expected_pack_sha256="0" * 64,
        purpose="test",
    )
    with pytest.raises(ResearchConflict):
        svc.submit_resource_candidate(
            session_id="research_" + "z" * 24,
            selection=selection,
            actor="test",
        )


def test_candidate_not_found_raises_rejection() -> None:
    pack = evidence_pack()
    svc, _ = _build_service_with_pack(pack)
    selection = ResearchResourceSelection(
        candidate_id="rcand_" + "e" * 24,
        candidate_sha256="1" * 64,
        expected_pack_sha256=pack.pack_sha256,
        purpose="test",
    )
    with pytest.raises(ResearchResourceCandidateRejected):
        svc.submit_resource_candidate(
            session_id="research_" + "z" * 24,
            selection=selection,
            actor="test",
        )


def test_candidate_hash_mismatch_raises_conflict() -> None:
    evidence = evidence_draft()
    snapshot = evidence.snapshots[0]
    draft = ResearchResourceCandidate(
        candidate_id="rcand_" + "c" * 24,
        kind="paper_pdf",
        source_url_sanitized=snapshot.canonical_url,
        expected_sha256=snapshot.body_sha256,
        citation_ids=[evidence.citations[0].citation_id],
        reason="test",
        candidate_sha256="0" * 64,
    )
    candidate_hash = sha256_value(without_hash(draft, "candidate_sha256"))
    candidate = draft.model_copy(update={"candidate_sha256": candidate_hash})

    pack = evidence_pack()
    pack = pack.model_copy(update={"resource_candidates": [candidate]})

    svc, _ = _build_service_with_pack(pack)
    selection = ResearchResourceSelection(
        candidate_id=candidate.candidate_id,
        candidate_sha256="0" * 64,
        expected_pack_sha256=pack.pack_sha256,
        purpose="test",
    )
    with pytest.raises(ResearchConflict):
        svc.submit_resource_candidate(
            session_id="research_" + "z" * 24,
            selection=selection,
            actor="test",
        )
