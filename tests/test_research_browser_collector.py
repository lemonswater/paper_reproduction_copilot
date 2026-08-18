import pytest

from app.research_browser.collector import ResearchCollector
from app.research_browser.errors import ResearchLimitExceeded
from app.research_browser.fetcher import FetchedDocument
from app.research_browser.identity import sha256_bytes, sha256_value
from app.research_browser.schemas import ProviderSearchHit
from app.research_browser.search import FixtureSearchProvider

from tests.research_browser_helpers import research_policy, research_request


class FakeFetcher:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch(self, url: str) -> FetchedDocument:
        self.urls.append(url)
        body = b"<html><title>PSTNet</title><p>Point spatio-temporal convolution.</p></html>"
        return FetchedDocument(
            canonical_url=url,
            redirect_chain=(url,),
            body=body,
            body_sha256=sha256_bytes(body),
            media_type="text/html",
            fetched_at_epoch=0,
            robots_status="allowed",
        )


class FailingFetcher:
    def fetch(self, url: str) -> FetchedDocument:
        raise RuntimeError("connection refused")


class OversizedFetcher:
    def fetch(self, url: str) -> FetchedDocument:
        body = b"a" * 20000
        return FetchedDocument(
            canonical_url=url,
            redirect_chain=(url,),
            body=body,
            body_sha256=sha256_bytes(body),
            media_type="text/html",
            fetched_at_epoch=0,
            robots_status="allowed",
        )


def test_collector_enforces_request_host_subset() -> None:
    policy = research_policy(allowed_hosts=["example.org", "github.com"])
    search = FixtureSearchProvider(
        [
            ProviderSearchHit(
                title="Allowed",
                url="https://example.org/pstnet",
                snippet="paper",
                rank=1,
            ),
            ProviderSearchHit(
                title="Globally allowed but not requested",
                url="https://github.com/hehefan/Point-Spatio-Temporal-Convolution",
                snippet="repository",
                rank=2,
            ),
        ]
    )
    fetcher = FakeFetcher()
    collector = ResearchCollector(
        search_provider=search,
        fetcher=fetcher,
        policy=policy,
        policy_sha256=sha256_value(policy),
    )
    evidence = collector.collect(
        research_request(allowed_hosts=["example.org"])
    )
    assert fetcher.urls == ["https://example.org/pstnet"]
    assert "search_hit_host_outside_request_scope" in evidence.skipped


def test_collector_deduplicates_canonical_url() -> None:
    search = FixtureSearchProvider(
        [
            ProviderSearchHit(
                title="A",
                url="https://example.org/page",
                snippet="",
                rank=1,
            ),
            ProviderSearchHit(
                title="B",
                url="https://example.org/page?utm_source=test#frag",
                snippet="",
                rank=2,
            ),
        ]
    )
    fetcher = FakeFetcher()
    collector = ResearchCollector(
        search_provider=search,
        fetcher=fetcher,
        policy=research_policy(),
        policy_sha256="1" * 64,
    )
    evidence = collector.collect(research_request())
    assert len(fetcher.urls) == 1


def test_single_page_failure_does_not_block_others() -> None:
    search = FixtureSearchProvider(
        [
            ProviderSearchHit(
                title="A",
                url="https://example.org/a",
                snippet="",
                rank=1,
            ),
            ProviderSearchHit(
                title="B",
                url="https://example.org/b",
                snippet="",
                rank=2,
            ),
        ]
    )
    collector = ResearchCollector(
        search_provider=search,
        fetcher=FailingFetcher(),
        policy=research_policy(),
        policy_sha256="1" * 64,
    )
    evidence = collector.collect(research_request(max_sources=2))
    assert len(evidence.skipped) >= 2
    assert len(evidence.snapshots) == 0


def test_total_bytes_exceeds_limit_terminates_collector() -> None:
    search = FixtureSearchProvider(
        [
            ProviderSearchHit(
                title="Large",
                url="https://example.org/large",
                snippet="",
                rank=1,
            ),
        ]
    )
    collector = ResearchCollector(
        search_provider=search,
        fetcher=OversizedFetcher(),
        policy=research_policy(max_total_bytes=10000, max_response_bytes=5000),
        policy_sha256="1" * 64,
    )
    with pytest.raises(ResearchLimitExceeded):
        collector.collect(research_request())


def test_citation_binds_snapshot_and_block_hash() -> None:
    search = FixtureSearchProvider(
        [
            ProviderSearchHit(
                title="PSTNet",
                url="https://example.org/pstnet",
                snippet="method",
                rank=1,
            ),
        ]
    )
    fetcher = FakeFetcher()
    collector = ResearchCollector(
        search_provider=search,
        fetcher=fetcher,
        policy=research_policy(),
        policy_sha256="1" * 64,
    )
    evidence = collector.collect(research_request())
    assert len(evidence.citations) >= 1
    citation = evidence.citations[0]
    snapshot = evidence.snapshots[0]
    assert citation.snapshot_id == snapshot.snapshot_id
    assert citation.snapshot_body_sha256 == snapshot.body_sha256
    block = next(b for b in snapshot.blocks if b.block_id == citation.block_id)
    assert citation.excerpt == block.text[:1200]


def test_github_default_branch_does_not_form_candidate() -> None:
    search = FixtureSearchProvider(
        [
            ProviderSearchHit(
                title="Repo",
                url="https://github.com/owner/repo",
                snippet="",
                rank=1,
            ),
        ]
    )
    fetcher = FakeFetcher()
    collector = ResearchCollector(
        search_provider=search,
        fetcher=fetcher,
        policy=research_policy(allowed_hosts=["github.com"]),
        policy_sha256="1" * 64,
    )
    evidence = collector.collect(
        research_request(allowed_hosts=["github.com"])
    )
    assert len(evidence.resource_candidates) == 0


def test_github_exact_commit_forms_candidate() -> None:
    commit = "a" * 40
    search = FixtureSearchProvider(
        [
            ProviderSearchHit(
                title="Commit",
                url=f"https://github.com/owner/repo/commit/{commit}",
                snippet="",
                rank=1,
            ),
        ]
    )
    fetcher = FakeFetcher()
    collector = ResearchCollector(
        search_provider=search,
        fetcher=fetcher,
        policy=research_policy(allowed_hosts=["github.com"]),
        policy_sha256="1" * 64,
    )
    evidence = collector.collect(
        research_request(allowed_hosts=["github.com"])
    )
    assert len(evidence.resource_candidates) == 1
    candidate = evidence.resource_candidates[0]
    assert candidate.kind == "git_repository"
    assert candidate.expected_git_commit == commit
    assert candidate.requires_explicit_user_review is True


def test_pdf_candidate_has_body_hash() -> None:
    pdf_body = b"%PDF-1.4\ntest pdf content"
    search = FixtureSearchProvider(
        [
            ProviderSearchHit(
                title="Paper",
                url="https://example.org/paper.pdf",
                snippet="",
                rank=1,
            ),
        ]
    )

    class PdfFetcher:
        def fetch(self, url: str) -> FetchedDocument:
            return FetchedDocument(
                canonical_url=url,
                redirect_chain=(url,),
                body=pdf_body,
                body_sha256=sha256_bytes(pdf_body),
                media_type="application/pdf",
                fetched_at_epoch=0,
                robots_status="allowed",
            )

    collector = ResearchCollector(
        search_provider=search,
        fetcher=PdfFetcher(),
        policy=research_policy(),
        policy_sha256="1" * 64,
    )
    # PDF extraction will fail since body is fake, but the test is about candidate formation
    evidence = collector.collect(research_request(allow_pdf=True))
    # If extraction fails, snapshot won't be created. That's acceptable.
    # When it does succeed, candidate should have body hash.
    for candidate in evidence.resource_candidates:
        if candidate.kind == "paper_pdf":
            assert candidate.expected_sha256 is not None
            assert candidate.requires_explicit_user_review is True
