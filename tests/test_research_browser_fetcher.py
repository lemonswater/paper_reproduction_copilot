import pytest

from app.research_browser.errors import (
    ResearchContentRejected,
    ResearchLimitExceeded,
    ResearchRobotsDenied,
    ResearchTransportUnavailable,
    ResearchUrlRejected,
)
from app.research_browser.fetcher import (
    BoundedResearchFetcher,
    HttpxResearchTransport,
    validate_research_target,
)

from tests.research_browser_helpers import (
    AllowRobots,
    DenyRobots,
    FakeResponse,
    FakeTransport,
    research_policy,
)


PUBLIC_RESOLVER = lambda host: ("93.184.216.34",)
PRIVATE_RESOLVER = lambda host: ("127.0.0.1",)


def build_fetcher(transport: FakeTransport, **policy_updates):
    policy = research_policy(**policy_updates)
    fetcher = BoundedResearchFetcher(
        policy=policy,
        allowed_hosts=("example.org",),
        transport=transport,
        robots=AllowRobots(),
        resolver=PUBLIC_RESOLVER,
    )
    fetcher.rate_limiter.minimum_interval_seconds = 0
    return fetcher


def test_target_rejects_private_dns_result() -> None:
    with pytest.raises(ResearchUrlRejected):
        validate_research_target(
            "https://example.org/paper",
            allowed_hosts=("example.org",),
            resolver=PRIVATE_RESOLVER,
        )


def test_target_rejects_host_outside_allowlist() -> None:
    with pytest.raises(ResearchUrlRejected):
        validate_research_target(
            "https://evil.com/paper",
            allowed_hosts=("example.org",),
            resolver=PUBLIC_RESOLVER,
        )


def test_target_rejects_ip_literal() -> None:
    with pytest.raises(ResearchUrlRejected):
        validate_research_target(
            "https://93.184.216.34/paper",
            allowed_hosts=("93.184.216.34",),
            resolver=PUBLIC_RESOLVER,
        )


def test_fetch_revalidates_redirect_destination() -> None:
    transport = FakeTransport(
        {
            "https://example.org/start": [
                FakeResponse(302, {"location": "https://127.0.0.1/admin"}, [])
            ]
        }
    )
    with pytest.raises(ResearchUrlRejected):
        build_fetcher(transport).fetch("https://example.org/start")


def test_fetch_rejects_redirect_without_location() -> None:
    transport = FakeTransport(
        {
            "https://example.org/redirect": [
                FakeResponse(302, {}, [])
            ]
        }
    )
    with pytest.raises(ResearchTransportUnavailable):
        build_fetcher(transport).fetch("https://example.org/redirect")


def test_fetch_rejects_too_many_redirects() -> None:
    transport = FakeTransport(
        {
            "https://example.org/r1": [
                FakeResponse(302, {"location": "https://example.org/r2"}, [])
            ],
            "https://example.org/r2": [
                FakeResponse(302, {"location": "https://example.org/r3"}, [])
            ],
            "https://example.org/r3": [
                FakeResponse(302, {"location": "https://example.org/r4"}, [])
            ],
        }
    )
    with pytest.raises(ResearchLimitExceeded):
        build_fetcher(transport, max_redirects=2).fetch("https://example.org/r1")


def test_fetch_enforces_streamed_byte_limit() -> None:
    transport = FakeTransport(
        {
            "https://example.org/large": [
                FakeResponse(
                    200,
                    {"content-type": "text/plain"},
                    [b"a" * 6000, b"b" * 6000],
                )
            ]
        }
    )
    with pytest.raises(ResearchLimitExceeded):
        build_fetcher(transport, max_response_bytes=10000).fetch("https://example.org/large")


def test_fetch_rejects_declared_content_length() -> None:
    transport = FakeTransport(
        {
            "https://example.org/declared": [
                FakeResponse(
                    200,
                    {"content-type": "text/plain", "content-length": "99999"},
                    [b"small"],
                )
            ]
        }
    )
    with pytest.raises(ResearchLimitExceeded):
        build_fetcher(transport, max_response_bytes=10000).fetch("https://example.org/declared")


def test_fetch_rejects_unknown_media_type() -> None:
    transport = FakeTransport(
        {
            "https://example.org/video": [
                FakeResponse(
                    200,
                    {"content-type": "video/mp4"},
                    [b"video data"],
                )
            ]
        }
    )
    with pytest.raises(ResearchContentRejected):
        build_fetcher(transport).fetch("https://example.org/video")


def test_fetch_rejects_fake_pdf() -> None:
    transport = FakeTransport(
        {
            "https://example.org/paper.pdf": [
                FakeResponse(
                    200,
                    {"content-type": "application/pdf"},
                    [b"not a pdf"],
                )
            ]
        }
    )
    with pytest.raises(ResearchContentRejected):
        build_fetcher(transport).fetch("https://example.org/paper.pdf")


def test_fetch_maps_429_to_retryable_transport_error() -> None:
    transport = FakeTransport(
        {
            "https://example.org/rate": [
                FakeResponse(429, {}, [])
            ]
        }
    )
    with pytest.raises(ResearchTransportUnavailable):
        build_fetcher(transport).fetch("https://example.org/rate")


def test_robots_denial_prevents_document_request() -> None:
    transport = FakeTransport(
        {
            "https://example.org/denied": [
                FakeResponse(
                    200,
                    {"content-type": "text/plain"},
                    [b"content"],
                )
            ]
        }
    )
    policy = research_policy()
    fetcher = BoundedResearchFetcher(
        policy=policy,
        allowed_hosts=("example.org",),
        transport=transport,
        robots=DenyRobots(),
        resolver=PUBLIC_RESOLVER,
    )
    fetcher.rate_limiter.minimum_interval_seconds = 0
    with pytest.raises(ResearchRobotsDenied):
        fetcher.fetch("https://example.org/denied")


def test_fetch_returns_valid_document() -> None:
    body = b"<html><body><p>Hello</p></body></html>"
    transport = FakeTransport(
        {
            "https://example.org/page": [
                FakeResponse(
                    200,
                    {"content-type": "text/html"},
                    [body],
                )
            ]
        }
    )
    doc = build_fetcher(transport).fetch("https://example.org/page")
    assert doc.media_type == "text/html"
    assert doc.body == body
    assert doc.canonical_url == "https://example.org/page"
    assert doc.redirect_chain == ("https://example.org/page",)
    assert doc.robots_status == "allowed"


def test_fetch_follows_redirect() -> None:
    body = b"<html><body><p>Final</p></body></html>"
    transport = FakeTransport(
        {
            "https://example.org/short": [
                FakeResponse(301, {"location": "https://example.org/full"}, [])
            ],
            "https://example.org/full": [
                FakeResponse(200, {"content-type": "text/html"}, [body])
            ],
        }
    )
    doc = build_fetcher(transport).fetch("https://example.org/short")
    assert doc.canonical_url == "https://example.org/full"
    assert len(doc.redirect_chain) == 2
