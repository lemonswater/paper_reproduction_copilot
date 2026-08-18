import pytest

from app.research_browser.errors import ResearchUrlRejected
from app.research_browser.identity import (
    canonicalize_research_url,
    host_matches,
    safe_search_text,
    sha256_text,
    sha256_value,
    stable_id,
)


def test_url_canonicalization_removes_fragment_and_tracking() -> None:
    assert canonicalize_research_url(
        "https://Example.org:443/paper?utm_source=x&id=42#method"
    ) == "https://example.org/paper?id=42"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/paper",
        "https://user:pass@example.org/paper",
        "https://example.org:8443/paper",
        "https://example.org/paper?token=secret",
        "file:///etc/passwd",
    ],
)
def test_url_canonicalization_rejects_unsafe_shapes(url: str) -> None:
    with pytest.raises(ResearchUrlRejected):
        canonicalize_research_url(url)


def test_host_matches_exact_and_subdomain() -> None:
    assert host_matches("example.org", ("example.org",))
    assert host_matches("sub.example.org", ("example.org",))
    assert not host_matches("evilexample.org", ("example.org",))
    assert not host_matches("example.com", ("example.org",))


def test_safe_search_text_normalizes_whitespace() -> None:
    assert safe_search_text("  hello   world  ", max_chars=100) == "hello world"


def test_safe_search_text_rejects_empty() -> None:
    with pytest.raises(ValueError):
        safe_search_text("   ", max_chars=100)


def test_safe_search_text_rejects_control_chars() -> None:
    with pytest.raises(ValueError):
        safe_search_text("hello\x00world", max_chars=100)


def test_stable_id_is_deterministic() -> None:
    assert stable_id("rblk", {"a": 1}) == stable_id("rblk", {"a": 1})


def test_stable_id_changes_with_input() -> None:
    assert stable_id("rblk", {"a": 1}) != stable_id("rblk", {"a": 2})


def test_sha256_text_is_hex_64() -> None:
    result = sha256_text("test")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_sha256_value_sorts_keys() -> None:
    assert sha256_value({"a": 1, "b": 2}) == sha256_value({"b": 2, "a": 1})
