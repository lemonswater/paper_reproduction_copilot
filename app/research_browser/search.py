from __future__ import annotations

import json
from typing import Any, Protocol

from app.research_browser.errors import (
    ResearchLimitExceeded,
    ResearchTransportUnavailable,
)
from app.research_browser.schemas import ProviderSearchHit
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService


BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
BRAVE_API_VERSION = "2023-01-01"
MAX_SEARCH_RESPONSE_BYTES = 2 * 1024 * 1024


class SearchProviderPort(Protocol):
    def search(self, *, query: str, count: int) -> list[ProviderSearchHit]:
        ...


class BraveSearchProvider:
    """只在一次 search 调用的局部作用域内解析 Search Secret。"""

    def __init__(
        self,
        *,
        secret_service: SecretService,
        secret_name: str,
        timeout_seconds: float,
        client: Any | None = None,
    ) -> None:
        self.secret_service = secret_service
        self.secret_name = secret_name
        self.timeout_seconds = timeout_seconds
        self._client = client

    def search(self, *, query: str, count: int) -> list[ProviderSearchHit]:
        if count < 1 or count > 20:
            raise ResearchLimitExceeded("RESEARCH_SEARCH_COUNT_EXCEEDED")
        # Brave Web Search 当前限制 q 最多 400 字符、50 个词。
        if len(query) > 400 or len(query.split()) > 50:
            raise ResearchLimitExceeded("RESEARCH_SEARCH_QUERY_EXCEEDED")
        material = self.secret_service.resolve_current(
            name=self.secret_name,
            use=SecretUse.RESEARCH_SEARCH,
            actor="research-browser:search",
        )
        client = self._client
        owns_client = client is None
        try:
            if client is None:
                import httpx

                client = httpx.Client(
                    timeout=self.timeout_seconds,
                    follow_redirects=False,
                    trust_env=False,
                )
            with client.stream(
                "GET",
                BRAVE_SEARCH_ENDPOINT,
                params={
                    "q": query,
                    "count": count,
                    "safesearch": "strict",
                    "text_decorations": False,
                    "result_filter": "web",
                },
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    "Api-Version": BRAVE_API_VERSION,
                    "X-Subscription-Token": material.reveal(),
                },
            ) as response:
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise ResearchTransportUnavailable(
                        "RESEARCH_SEARCH_RETRYABLE"
                    )
                if response.status_code != 200:
                    raise ResearchTransportUnavailable(
                        "RESEARCH_SEARCH_REJECTED"
                    )
                raw = bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    raw.extend(chunk)
                    if len(raw) > MAX_SEARCH_RESPONSE_BYTES:
                        raise ResearchLimitExceeded(
                            "RESEARCH_SEARCH_RESPONSE_TOO_LARGE"
                        )
                content = bytes(raw)
        except (ResearchLimitExceeded, ResearchTransportUnavailable):
            raise
        except Exception as exc:
            # 不把可能包含 query/header 的原始异常向上抛出。
            raise ResearchTransportUnavailable(
                "RESEARCH_SEARCH_UNAVAILABLE"
            ) from exc
        finally:
            if owns_client and client is not None:
                client.close()
            del material

        try:
            payload = json.loads(content)
            rows = payload.get("web", {}).get("results", [])
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
            raise ResearchTransportUnavailable(
                "RESEARCH_SEARCH_RESPONSE_INVALID"
            ) from exc

        hits: list[ProviderSearchHit] = []
        for index, row in enumerate(rows[:count], start=1):
            if not isinstance(row, dict) or not row.get("url") or not row.get("title"):
                continue
            hits.append(
                ProviderSearchHit(
                    title=str(row["title"])[:500],
                    url=str(row["url"])[:2048],
                    snippet=str(row.get("description") or "")[:2000],
                    rank=index,
                )
            )
        return hits


class FixtureSearchProvider:
    """普通离线测试专用；不允许 Factory 在 active 生产配置下偷偷使用。"""

    def __init__(self, hits: list[ProviderSearchHit]) -> None:
        self.hits = list(hits)
        self.calls: list[tuple[str, int]] = []

    def search(self, *, query: str, count: int) -> list[ProviderSearchHit]:
        self.calls.append((query, count))
        return self.hits[:count]
