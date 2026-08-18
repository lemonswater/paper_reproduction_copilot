from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from app.research_browser.identity import (
    sha256_bytes,
    sha256_text,
    sha256_value,
    stable_id,
    without_hash,
)
from app.research_browser.schemas import (
    ExtractedBlock,
    ResearchCitation,
    ResearchEvidenceDraft,
    ResearchEvidencePack,
    ResearchPolicyDocument,
    ResearchReport,
    ResearchRequest,
    ResearchSourceSnapshot,
)


def research_policy(**updates) -> ResearchPolicyDocument:
    payload = {
        "policy_version": "test-v1",
        "search_provider_binding": "fixture_search",
        "allowed_hosts": ["example.org", "arxiv.org", "github.com"],
        "allowed_media_types": [
            "text/html",
            "text/plain",
            "application/pdf",
        ],
        "user_agent": "research-test/1.0",
        "max_redirects": 2,
        "connect_timeout_seconds": 1,
        "read_timeout_seconds": 2,
        "total_timeout_seconds": 10,
        "max_response_bytes": 10000,
        "max_total_bytes": 20000,
        "max_pdf_pages": 5,
        "max_blocks_per_source": 20,
        "max_citations": 8,
        "min_host_interval_seconds": 0.1,
        "robots_required": True,
    }
    payload.update(updates)
    return ResearchPolicyDocument.model_validate(payload)


def research_request(**updates) -> ResearchRequest:
    payload = {
        "query": "PSTNet point spatio temporal convolution",
        "purpose": "寻找论文和官方仓库证据",
        "job_id": "job-research-test",
        "allowed_hosts": ["example.org"],
        "max_results": 3,
        "max_sources": 2,
        "allow_pdf": True,
    }
    payload.update(updates)
    return ResearchRequest.model_validate(payload)


def evidence_draft() -> ResearchEvidenceDraft:
    text = "PSTNet introduces point spatio-temporal convolution."
    text_hash = sha256_text(text)
    block = ExtractedBlock(
        block_id=stable_id(
            "rblk",
            {"locator": "html:block:1", "text_sha256": text_hash},
        ),
        kind="paragraph",
        locator="html:block:1",
        heading_path=["Method"],
        text=text,
        text_sha256=text_hash,
    )
    body = b"<p>PSTNet introduces point spatio-temporal convolution.</p>"
    body_hash = sha256_bytes(body)
    snapshot = ResearchSourceSnapshot(
        snapshot_id=stable_id(
            "rsnap",
            {
                "url": "https://example.org/pstnet",
                "body_sha256": body_hash,
                "policy_sha256": "1" * 64,
            },
        ),
        canonical_url="https://example.org/pstnet",
        redirect_chain=["https://example.org/pstnet"],
        fetched_at="2026-01-01T00:00:00+00:00",
        media_type="text/html",
        source_kind="html",
        body_sha256=body_hash,
        body_size_bytes=len(body),
        normalized_text_sha256=text_hash,
        title="PSTNet",
        blocks=[block],
        robots_status="allowed",
        fetch_policy_sha256="1" * 64,
    )
    excerpt_hash = sha256_text(text)
    citation = ResearchCitation(
        citation_id=stable_id(
            "rcit",
            {
                "snapshot_id": snapshot.snapshot_id,
                "block_id": block.block_id,
                "excerpt_sha256": excerpt_hash,
            },
        ),
        snapshot_id=snapshot.snapshot_id,
        snapshot_body_sha256=snapshot.body_sha256,
        block_id=block.block_id,
        canonical_url=snapshot.canonical_url,
        label="PSTNet",
        locator=block.locator,
        excerpt=text,
        excerpt_sha256=excerpt_hash,
        relevance_score=1.0,
    )
    return ResearchEvidenceDraft(
        search_hits=[],
        snapshots=[snapshot],
        citations=[citation],
        resource_candidates=[],
        skipped=[],
    )


def evidence_pack(
    *,
    session_id: str = "research_" + "a" * 24,
    request_hash: str = "2" * 64,
    policy_hash: str = "1" * 64,
) -> ResearchEvidencePack:
    evidence = evidence_draft()
    report = ResearchReport(
        synthesis_status="succeeded",
        answer="PSTNet 的核心模块是 point spatio-temporal convolution。",
        citations=evidence.citations,
        resource_candidates=[],
    )
    pack_id = stable_id(
        "rpack",
        {
            "session_id": session_id,
            "request_sha256": request_hash,
            "snapshots": [
                item.snapshot_id for item in evidence.snapshots
            ],
        },
    )
    draft = ResearchEvidencePack(
        pack_id=pack_id,
        session_id=session_id,
        request_sha256=request_hash,
        policy_sha256=policy_hash,
        search_hits=[],
        snapshots=evidence.snapshots,
        citations=evidence.citations,
        resource_candidates=[],
        report=report,
        pack_sha256="0" * 64,
        created_at="2026-01-01T00:00:00+00:00",
    )
    return draft.model_copy(
        update={
            "pack_sha256": sha256_value(
                without_hash(draft, "pack_sha256")
            )
        }
    )


@dataclass
class FakeResponse:
    status_code: int
    headers: dict[str, str]
    chunks: list[bytes]

    def iter_bytes(self, *, chunk_size: int) -> Iterator[bytes]:
        del chunk_size
        yield from self.chunks


class FakeTransport:
    def __init__(self, responses: dict[str, list[FakeResponse]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    @contextmanager
    def stream(self, method: str, url: str):
        self.calls.append((method, url))
        candidates = self.responses.get(url)
        if not candidates:
            raise AssertionError(f"unexpected URL: {url}")
        yield candidates.pop(0)


class AllowRobots:
    def check(self, target) -> str:
        del target
        return "allowed"


class DenyRobots:
    def check(self, target) -> str:
        from app.research_browser.errors import ResearchRobotsDenied

        raise ResearchRobotsDenied("RESEARCH_ROBOTS_DENIED")
