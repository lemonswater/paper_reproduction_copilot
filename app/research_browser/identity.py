from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import (
    parse_qsl,
    quote,
    urlencode,
    urlsplit,
    urlunsplit,
)

from pydantic import BaseModel

from app.research_browser.errors import ResearchUrlRejected


SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "credential",
    "key",
    "password",
    "secret",
    "signature",
    "sig",
    "token",
    "x-amz-credential",
    "x-amz-signature",
}

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


def canonical_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_text(canonical_json(value))


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{sha256_value(value)[:24]}"


def canonicalize_research_url(raw_url: str) -> str:
    """生成可持久化 URL；任何可能携带凭据的形状都 fail closed。"""

    raw = raw_url.strip()
    if (
        len(raw) > 2048
        or "\\" in raw
        or any(
            ord(character) < 32 or ord(character) == 127
            for character in raw
        )
    ):
        raise ResearchUrlRejected("RESEARCH_URL_SHAPE_INVALID")
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise ResearchUrlRejected("RESEARCH_URL_PARSE_FAILED") from exc
    if parsed.scheme.lower() != "https":
        raise ResearchUrlRejected("RESEARCH_URL_SCHEME_DENIED")
    if parsed.username is not None or parsed.password is not None:
        raise ResearchUrlRejected("RESEARCH_URL_USERINFO_DENIED")
    if not parsed.hostname:
        raise ResearchUrlRejected("RESEARCH_URL_HOST_REQUIRED")
    if port not in {None, 443}:
        raise ResearchUrlRejected("RESEARCH_URL_PORT_DENIED")

    try:
        host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ResearchUrlRejected("RESEARCH_URL_HOST_INVALID") from exc

    pairs = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=20)
    normalized_query: list[tuple[str, str]] = []
    for key, value in pairs:
        lowered = key.strip().lower()
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in f"{key}{value}"
        ):
            raise ResearchUrlRejected("RESEARCH_URL_QUERY_CONTROL_DENIED")
        if lowered.startswith("utm_") or lowered in TRACKING_QUERY_KEYS:
            continue
        if lowered in SENSITIVE_QUERY_KEYS or any(
            marker in lowered for marker in ("token", "secret", "signature", "password")
        ):
            raise ResearchUrlRejected("RESEARCH_URL_SENSITIVE_QUERY_DENIED")
        if len(key) > 80 or len(value) > 300:
            raise ResearchUrlRejected("RESEARCH_URL_QUERY_TOO_LARGE")
        normalized_query.append((key, value))
    normalized_query.sort()

    # Fragment 只在客户端页面内定位，抓取身份不应随 fragment 漂移。
    path = quote(parsed.path or "/", safe="/%:@-._~")
    query = urlencode(normalized_query, doseq=True)
    return urlunsplit(("https", host, path, query, ""))


def host_matches(host: str, allowed_hosts: tuple[str, ...]) -> bool:
    normalized = host.rstrip(".").lower()
    return any(
        normalized == allowed or normalized.endswith(f".{allowed}")
        for allowed in allowed_hosts
    )


def safe_search_text(value: str, *, max_chars: int) -> str:
    if any(
        ord(character) < 32 or ord(character) == 127
        for character in value
    ):
        raise ValueError("Research query 包含控制字符")
    normalized = " ".join(value.strip().split())
    if not normalized or len(normalized) > max_chars:
        raise ValueError("Research query 长度无效")
    return normalized


def request_sha256(request: BaseModel) -> str:
    payload = request.model_dump(mode="json")
    payload["allowed_hosts"] = sorted(payload.get("allowed_hosts") or [])
    return sha256_value(payload)


def without_hash(value: BaseModel, field_name: str) -> dict[str, Any]:
    payload = value.model_dump(mode="json")
    payload.pop(field_name, None)
    return payload
