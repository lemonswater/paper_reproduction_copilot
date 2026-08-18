from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from app.research_browser.errors import ResearchLimitExceeded
from app.research_browser.extractors import extract_document
from app.research_browser.fetcher import BoundedResearchFetcher
from app.research_browser.identity import (
    canonicalize_research_url,
    host_matches,
    safe_search_text,
    sha256_text,
    sha256_value,
    stable_id,
    without_hash,
)
from app.research_browser.schemas import (
    ResearchCitation,
    ResearchEvidenceDraft,
    ResearchPolicyDocument,
    ResearchRequest,
    ResearchResourceCandidate,
    ResearchSearchHit,
    ResearchSourceSnapshot,
)
from app.research_browser.search import SearchProviderPort


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_.-]{2,}|[\u4e00-\u9fff]{2,}")
GITHUB_COMMIT_PATTERN = re.compile(
    r"^/([^/]+)/([^/]+)/(?:commit|tree)/([0-9a-fA-F]{40,64})(?:/|$)"
)


def _keywords(query: str) -> set[str]:
    return {item.lower() for item in TOKEN_PATTERN.findall(query)}


def _score(text: str, keywords: set[str]) -> float:
    lowered = text.lower()
    if not keywords:
        return 0.0
    hits = sum(1 for keyword in keywords if keyword in lowered)
    return min(1.0, hits / max(1, min(8, len(keywords))))


def _candidate_hash(candidate: ResearchResourceCandidate) -> str:
    return sha256_value(without_hash(candidate, "candidate_sha256"))


class ResearchCollector:
    def __init__(
        self,
        *,
        search_provider: SearchProviderPort,
        fetcher: BoundedResearchFetcher,
        policy: ResearchPolicyDocument,
        policy_sha256: str,
    ) -> None:
        self.search_provider = search_provider
        self.fetcher = fetcher
        self.policy = policy
        self.policy_sha256 = policy_sha256

    def collect(self, request: ResearchRequest) -> ResearchEvidenceDraft:
        query = safe_search_text(request.query, max_chars=400)
        provider_hits = self.search_provider.search(
            query=query,
            count=request.max_results,
        )
        hits: list[ResearchSearchHit] = []
        seen_urls: set[str] = set()
        skipped: list[str] = []
        effective_hosts = tuple(request.allowed_hosts or self.policy.allowed_hosts)
        for provider_hit in provider_hits:
            try:
                url = canonicalize_research_url(provider_hit.url)
            except Exception:
                skipped.append("search_hit_url_rejected")
                continue
            host = (urlsplit(url).hostname or "").lower()
            if not host_matches(host, effective_hosts):
                skipped.append("search_hit_host_outside_request_scope")
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            identity = {
                "url": url,
                "title": provider_hit.title,
                "snippet": provider_hit.snippet,
                "rank": provider_hit.rank,
            }
            hits.append(
                ResearchSearchHit(
                    hit_id=stable_id("rhit", identity),
                    canonical_url=url,
                    title=provider_hit.title,
                    snippet=provider_hit.snippet,
                    rank=provider_hit.rank,
                    hit_sha256=sha256_value(identity),
                )
            )

        snapshots: list[ResearchSourceSnapshot] = []
        total_bytes = 0
        for hit in hits:
            if len(snapshots) >= request.max_sources:
                break
            try:
                fetched = self.fetcher.fetch(hit.canonical_url)
                if fetched.media_type == "application/pdf" and not request.allow_pdf:
                    skipped.append(f"{hit.hit_id}:pdf_disabled")
                    continue
                total_bytes += len(fetched.body)
                if total_bytes > self.policy.max_total_bytes:
                    raise ResearchLimitExceeded("RESEARCH_TOTAL_BYTES_EXCEEDED")
                extracted = extract_document(
                    media_type=fetched.media_type,
                    body=fetched.body,
                    max_pages=self.policy.max_pdf_pages,
                    max_blocks=self.policy.max_blocks_per_source,
                )
                snapshot_id = stable_id(
                    "rsnap",
                    {
                        "url": fetched.canonical_url,
                        "body_sha256": fetched.body_sha256,
                        "policy_sha256": self.policy_sha256,
                    },
                )
                snapshots.append(
                    ResearchSourceSnapshot(
                        snapshot_id=snapshot_id,
                        canonical_url=fetched.canonical_url,
                        redirect_chain=list(fetched.redirect_chain),
                        fetched_at=datetime.fromtimestamp(
                            fetched.fetched_at_epoch,
                            tz=timezone.utc,
                        ).isoformat(),
                        media_type=fetched.media_type,
                        source_kind=extracted.source_kind,
                        body_sha256=fetched.body_sha256,
                        body_size_bytes=len(fetched.body),
                        normalized_text_sha256=extracted.normalized_text_sha256,
                        title=extracted.title or hit.title,
                        blocks=extracted.blocks,
                        robots_status=fetched.robots_status,
                        fetch_policy_sha256=self.policy_sha256,
                    )
                )
            except ResearchLimitExceeded:
                raise
            except Exception:
                # 单页失败不泄漏 URL/异常正文，也不阻止其他来源继续。
                skipped.append(f"{hit.hit_id}:open_or_extract_failed")

        keywords = _keywords(query)
        citations: list[ResearchCitation] = []
        for snapshot in snapshots:
            ranked = sorted(
                snapshot.blocks,
                key=lambda block: _score(
                    " ".join([*block.heading_path, block.text]),
                    keywords,
                ),
                reverse=True,
            )[:4]
            for block in ranked:
                excerpt = block.text[:1200]
                excerpt_hash = sha256_text(excerpt)
                citation_identity = {
                    "snapshot_id": snapshot.snapshot_id,
                    "block_id": block.block_id,
                    "excerpt_sha256": excerpt_hash,
                }
                citations.append(
                    ResearchCitation(
                        citation_id=stable_id("rcit", citation_identity),
                        snapshot_id=snapshot.snapshot_id,
                        snapshot_body_sha256=snapshot.body_sha256,
                        block_id=block.block_id,
                        canonical_url=snapshot.canonical_url,
                        label=snapshot.title or snapshot.canonical_url,
                        locator=block.locator,
                        excerpt=excerpt,
                        excerpt_sha256=excerpt_hash,
                        relevance_score=_score(block.text, keywords),
                    )
                )
        citations = sorted(
            citations,
            key=lambda item: item.relevance_score,
            reverse=True,
        )[: self.policy.max_citations]

        citation_by_snapshot: dict[str, list[ResearchCitation]] = {}
        for citation in citations:
            citation_by_snapshot.setdefault(citation.snapshot_id, []).append(citation)

        candidates: list[ResearchResourceCandidate] = []
        for snapshot in snapshots:
            evidence = citation_by_snapshot.get(snapshot.snapshot_id, [])
            if not evidence:
                continue
            if snapshot.source_kind == "pdf" and not urlsplit(snapshot.canonical_url).query:
                draft = ResearchResourceCandidate(
                    candidate_id=stable_id(
                        "rcand",
                        {"kind": "paper_pdf", "snapshot": snapshot.snapshot_id},
                    ),
                    kind="paper_pdf",
                    source_url_sanitized=snapshot.canonical_url,
                    expected_sha256=snapshot.body_sha256,
                    citation_ids=[item.citation_id for item in evidence[:3]],
                    reason="已抓取 PDF 并计算完整响应 SHA-256，仍需 Phase 29 人工批准。",
                    candidate_sha256="0" * 64,
                )
                candidates.append(
                    draft.model_copy(update={"candidate_sha256": _candidate_hash(draft)})
                )

        for hit in hits:
            parsed = urlsplit(hit.canonical_url)
            if parsed.hostname != "github.com" or parsed.query:
                continue
            match = GITHUB_COMMIT_PATTERN.match(parsed.path)
            if match is None:
                continue
            owner, repository, commit = match.groups()
            repository_url = urlunsplit(
                ("https", "github.com", f"/{owner}/{repository}", "", "")
            )
            related: list[ResearchCitation] = []
            for item in citations:
                citation_url = urlsplit(item.canonical_url)
                if citation_url.hostname != "github.com":
                    continue
                citation_match = GITHUB_COMMIT_PATTERN.match(
                    citation_url.path
                )
                if citation_match is None:
                    continue
                citation_owner, citation_repository, citation_commit = (
                    citation_match.groups()
                )
                if (
                    citation_owner == owner
                    and citation_repository == repository
                    and citation_commit.lower() == commit.lower()
                ):
                    related.append(item)
                if len(related) >= 3:
                    break
            if not related:
                continue
            draft = ResearchResourceCandidate(
                candidate_id=stable_id(
                    "rcand",
                    {"kind": "git_repository", "url": repository_url, "commit": commit.lower()},
                ),
                kind="git_repository",
                source_url_sanitized=repository_url,
                expected_git_commit=commit.lower(),
                citation_ids=[item.citation_id for item in related],
                reason="搜索结果绑定了 exact commit；仍需 Phase 29 人工批准和 Git 校验。",
                candidate_sha256="0" * 64,
            )
            candidates.append(
                draft.model_copy(update={"candidate_sha256": _candidate_hash(draft)})
            )

        return ResearchEvidenceDraft(
            search_hits=hits,
            snapshots=snapshots,
            citations=citations,
            resource_candidates=candidates,
            skipped=skipped,
        )
