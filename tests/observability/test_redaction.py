from __future__ import annotations

from app.observability.redaction import (
    redact,
    sanitize_url,
    SENSITIVE_KEYS,
)


def test_redact_simple_dict_ok():
    data = {"a": "b", "c": "d"}
    result = redact(data)
    assert result == {"a": "b", "c": "d"}


def test_redact_authorization_value():
    data = {"Authorization": "Bearer xxx"}
    result = redact(data)
    assert result["Authorization"] == "<redacted>"


def test_redact_case_insensitive_key():
    data = {"API_KEY": "abc"}
    result = redact(data)
    assert result["API_KEY"] == "<redacted>"


def test_redact_api_key_nested():
    data = {"headers": {"claim_token": "secret123"}}
    result = redact(data)
    assert result["headers"]["claim_token"] == "<redacted>"


def test_redact_preserves_non_strings():
    data = {"n": 1, "b": True, "f": 2.5, "o": None}
    result = redact(data)
    assert result["n"] == 1
    assert result["b"] is True
    assert result["f"] == 2.5
    assert result["o"] is None


def test_redact_list_truncation():
    data = [{"i": i} for i in range(200)]
    result = redact(data)
    assert len(result) == 100
    assert result[0] == {"i": 0}
    assert result[99] == {"i": 99}


def test_redact_string_length_trim():
    data = "a" * 5000
    result = redact(data)
    assert len(result) == 2000


def test_redact_custom_max_chars():
    data = "a" * 5000
    result = redact(data, max_chars=3)
    assert len(result) == 3


def test_sanitize_url_removes_userinfo():
    result = sanitize_url("https://user:pwd@host/path?q=1#frag")
    assert result == "https://host/path"


def test_sanitize_url_preserves_host_and_port():
    result = sanitize_url("https://h:8080/p")
    assert result == "https://h:8080/p"


def test_sanitize_url_invalid_returns_tag():
    result = sanitize_url("http://[")
    assert result == "<invalid-url>"


def test_redact_url_string():
    result = redact("https://k:s@x/p?q")
    assert "k:s@" not in result
    assert "?q" not in result
    assert result.startswith("https://")


def test_redact_dict_with_url_value():
    data = {"url": "http://u:p@host/x?a=1"}
    result = redact(data)
    assert "u:p@" not in result["url"]
    assert "?a=1" not in result["url"]
    assert result["url"].startswith("http://")
