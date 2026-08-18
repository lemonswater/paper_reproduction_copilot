"""Phase 29 Fake HTTP transport for offline tests.

单元测试不能访问公网或 localhost。Fake transport 按 URL 返回预设
response/chunks/redirect，避免模拟 httpx 内部对象。
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class FakeHeaders:
    """最小 headers 视图，支持 ``.get`` 和大小写无关查找。"""

    items: dict[str, str] = field(default_factory=dict)

    def get(self, name: str, default=None):
        lowered = name.lower()
        for key, value in self.items.items():
            if key.lower() == lowered:
                return value
        return default


@dataclass
class FakeResponse:
    status_code: int = 200
    headers: FakeHeaders = field(default_factory=FakeHeaders)
    chunks: tuple[bytes, ...] = ()

    def iter_bytes(self, *, chunk_size: int) -> Iterator[bytes]:
        for chunk in self.chunks:
            yield chunk


class FakeResourceTransport:
    """按 URL 返回预设 response；记录所有请求用于断言。"""

    def __init__(self, responses: dict[str, FakeResponse] | None = None):
        self.responses = dict(responses or {})
        self.requests: list[str] = []

    @contextmanager
    def stream(self, method: str, url: str) -> Iterator[FakeResponse]:
        assert method == "GET", f"Fake transport 只支持 GET，收到 {method}"
        self.requests.append(url)
        response = self.responses.get(url)
        if response is None:
            raise KeyError(
                f"Fake transport 未配置 URL：{url}"
            )
        yield response


def make_redirect(
    location: str, status: int = 302
) -> FakeResponse:
    return FakeResponse(
        status_code=status,
        headers=FakeHeaders({"location": location}),
        chunks=(),
    )


def make_ok(
    body: bytes,
    *,
    content_type: str = "application/octet-stream",
    content_length: bool = True,
) -> FakeResponse:
    headers = {"content-type": content_type}
    if content_length:
        headers["content-length"] = str(len(body))
    return FakeResponse(
        status_code=200,
        headers=FakeHeaders(headers),
        chunks=(body,),
    )
