from __future__ import annotations

import time
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Protocol
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from app.research_browser.errors import (
    ResearchContentRejected,
    ResearchLimitExceeded,
    ResearchRobotsDenied,
    ResearchTransportUnavailable,
    ResearchUrlRejected,
)
from app.research_browser.identity import (
    canonicalize_research_url,
    host_matches,
    sha256_bytes,
)
from app.research_browser.schemas import ResearchPolicyDocument
from app.resources.policy import resolve_public_ips, validate_public_ips


@dataclass(frozen=True)
class ValidatedResearchTarget:
    canonical_url: str
    host: str
    resolved_ips: tuple[str, ...]


@dataclass(frozen=True)
class FetchedDocument:
    canonical_url: str
    redirect_chain: tuple[str, ...]
    body: bytes
    body_sha256: str
    media_type: str
    fetched_at_epoch: float
    robots_status: str


class ResearchHttpResponse(Protocol):
    status_code: int
    headers: Any

    def iter_bytes(self, *, chunk_size: int) -> Iterator[bytes]:
        ...


class ResearchHttpTransport(Protocol):
    def stream(
        self,
        method: str,
        url: str,
    ) -> AbstractContextManager[ResearchHttpResponse]:
        ...


class HttpxResearchTransport:
    def __init__(self, *, policy: ResearchPolicyDocument, client: Any | None = None):
        self._owns_client = client is None
        if client is not None:
            self._client = client
            return
        import httpx

        self._client = httpx.Client(
            follow_redirects=False,
            trust_env=False,
            timeout=httpx.Timeout(
                connect=policy.connect_timeout_seconds,
                read=policy.read_timeout_seconds,
                write=policy.read_timeout_seconds,
                pool=policy.connect_timeout_seconds,
            ),
            headers={
                "User-Agent": policy.user_agent,
                "Accept": "text/html,text/plain,application/pdf",
                "Accept-Encoding": "identity",
            },
        )

    @contextmanager
    def stream(self, method: str, url: str) -> Iterator[ResearchHttpResponse]:
        # httpx Client 会维护 Cookie Jar；每次请求前后清空，避免跨站传播状态。
        self._client.cookies.clear()
        try:
            with self._client.stream(method, url, headers={"Cookie": ""}) as response:
                yield response
        finally:
            self._client.cookies.clear()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def validate_research_target(
    raw_url: str,
    *,
    allowed_hosts: tuple[str, ...],
    resolver=resolve_public_ips,
) -> ValidatedResearchTarget:
    canonical = canonicalize_research_url(raw_url)
    host = (urlsplit(canonical).hostname or "").lower()
    if not host_matches(host, allowed_hosts):
        raise ResearchUrlRejected("RESEARCH_HOST_NOT_ALLOWED")
    # IP literal 不是第一版研究来源，即使它恰好是公网地址也拒绝。
    if host.replace(".", "").isdigit() or ":" in host:
        raise ResearchUrlRejected("RESEARCH_IP_LITERAL_DENIED")
    try:
        ips = resolver(host)
        validated = validate_public_ips(tuple(ips))
    except Exception as exc:
        raise ResearchUrlRejected("RESEARCH_DNS_DESTINATION_DENIED") from exc
    return ValidatedResearchTarget(canonical, host, validated)


class RobotsPolicy:
    """robots 检查也走固定 HTTPS、无 redirect、无 Cookie、有大小限制的请求。"""

    def __init__(
        self,
        *,
        policy: ResearchPolicyDocument,
        transport: ResearchHttpTransport,
        resolver=resolve_public_ips,
    ) -> None:
        self.policy = policy
        self.transport = transport
        self.resolver = resolver
        self._cache: dict[str, tuple[float, RobotFileParser | None]] = {}

    def check(self, target: ValidatedResearchTarget) -> str:
        cached = self._cache.get(target.host)
        if cached is not None and time.monotonic() - cached[0] < 3600:
            parser = cached[1]
        else:
            robots_url = urlunsplit(("https", target.host, "/robots.txt", "", ""))
            # 再做一次目的地校验，不能把 robots 当特殊绕过路径。
            validate_research_target(
                robots_url,
                allowed_hosts=(target.host,),
                resolver=self.resolver,
            )
            with self.transport.stream("GET", robots_url) as response:
                if response.status_code == 404:
                    parser = None
                elif response.status_code != 200:
                    raise ResearchTransportUnavailable("RESEARCH_ROBOTS_UNAVAILABLE")
                else:
                    raw = bytearray()
                    for chunk in response.iter_bytes(chunk_size=16384):
                        raw.extend(chunk)
                        if len(raw) > 256 * 1024:
                            raise ResearchLimitExceeded("RESEARCH_ROBOTS_TOO_LARGE")
                    parser = RobotFileParser()
                    parser.set_url(robots_url)
                    parser.parse(bytes(raw).decode("utf-8", errors="replace").splitlines())
            self._cache[target.host] = (time.monotonic(), parser)
        if parser is None:
            return "not_present"
        if not parser.can_fetch(self.policy.user_agent, target.canonical_url):
            raise ResearchRobotsDenied("RESEARCH_ROBOTS_DENIED")
        return "allowed"


class HostRateLimiter:
    def __init__(self, minimum_interval_seconds: float) -> None:
        self.minimum_interval_seconds = minimum_interval_seconds
        self._last_request: dict[str, float] = {}

    def wait(self, host: str) -> None:
        previous = self._last_request.get(host)
        if previous is not None:
            remaining = self.minimum_interval_seconds - (time.monotonic() - previous)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request[host] = time.monotonic()


class BoundedResearchFetcher:
    def __init__(
        self,
        *,
        policy: ResearchPolicyDocument,
        allowed_hosts: tuple[str, ...],
        transport: ResearchHttpTransport,
        robots: RobotsPolicy,
        resolver=resolve_public_ips,
    ) -> None:
        self.policy = policy
        self.allowed_hosts = allowed_hosts
        self.transport = transport
        self.robots = robots
        self.resolver = resolver
        self.rate_limiter = HostRateLimiter(policy.min_host_interval_seconds)

    def fetch(self, url: str) -> FetchedDocument:
        started = time.monotonic()
        current = url
        chain: list[str] = []
        for redirect_index in range(self.policy.max_redirects + 1):
            if time.monotonic() - started > self.policy.total_timeout_seconds:
                raise ResearchLimitExceeded("RESEARCH_TOTAL_TIMEOUT")
            target = validate_research_target(
                current,
                allowed_hosts=self.allowed_hosts,
                resolver=self.resolver,
            )
            chain.append(target.canonical_url)
            robots_status = self.robots.check(target)
            self.rate_limiter.wait(target.host)
            try:
                context = self.transport.stream("GET", target.canonical_url)
                with context as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise ResearchTransportUnavailable("RESEARCH_REDIRECT_LOCATION_MISSING")
                        if redirect_index >= self.policy.max_redirects:
                            raise ResearchLimitExceeded("RESEARCH_REDIRECT_LIMIT")
                        current = urljoin(target.canonical_url, location)
                        continue
                    if response.status_code in {429, 500, 502, 503, 504}:
                        raise ResearchTransportUnavailable("RESEARCH_TARGET_RETRYABLE")
                    if response.status_code != 200:
                        raise ResearchContentRejected("RESEARCH_TARGET_STATUS_REJECTED")

                    declared = response.headers.get("content-length")
                    if declared is not None:
                        try:
                            declared_size = int(declared)
                        except ValueError as exc:
                            raise ResearchContentRejected("RESEARCH_CONTENT_LENGTH_INVALID") from exc
                        if declared_size > self.policy.max_response_bytes:
                            raise ResearchLimitExceeded("RESEARCH_DECLARED_BYTES_EXCEEDED")

                    media_type = str(response.headers.get("content-type") or "")
                    media_type = media_type.split(";", 1)[0].strip().lower()
                    if media_type not in self.policy.allowed_media_types:
                        raise ResearchContentRejected("RESEARCH_MEDIA_TYPE_DENIED")

                    body = bytearray()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        if time.monotonic() - started > self.policy.total_timeout_seconds:
                            raise ResearchLimitExceeded("RESEARCH_TOTAL_TIMEOUT")
                        body.extend(chunk)
                        if len(body) > self.policy.max_response_bytes:
                            raise ResearchLimitExceeded("RESEARCH_ACTUAL_BYTES_EXCEEDED")
                    payload = bytes(body)
                    if media_type == "application/pdf" and not payload.startswith(b"%PDF-"):
                        raise ResearchContentRejected("RESEARCH_PDF_MAGIC_MISMATCH")
                    if media_type.startswith("text/") and b"\x00" in payload[:4096]:
                        raise ResearchContentRejected("RESEARCH_TEXT_BINARY_MISMATCH")
                    return FetchedDocument(
                        canonical_url=target.canonical_url,
                        redirect_chain=tuple(chain),
                        body=payload,
                        body_sha256=sha256_bytes(payload),
                        media_type=media_type,
                        fetched_at_epoch=time.time(),
                        robots_status=robots_status,
                    )
            except (ResearchLimitExceeded, ResearchContentRejected, ResearchTransportUnavailable):
                raise
            except Exception as exc:
                raise ResearchTransportUnavailable("RESEARCH_TARGET_UNAVAILABLE") from exc
        raise ResearchLimitExceeded("RESEARCH_REDIRECT_LIMIT")
