from __future__ import annotations

"""Phase 29 HTTP transport 与手工 redirect。

第一版使用 ``httpx.Client(follow_redirects=False, trust_env=False)``：
- 自动 redirect 会绕过逐跳 policy，必须关闭，每一跳重新 canonicalize/allowlist/DNS。
- Content-Length 不可信，必须同时限制声明大小和实际 streaming bytes。
- ``.part`` 文件用 ``O_CREAT|O_EXCL`` 独占创建，避免跟随 symlink 或覆盖旧 part。
- 失败时 ``unlink(missing_ok=True)`` 清理 part。

为了离线可测试，下载器依赖一个小的 ``HttpTransportPort``；默认 ``HttpxTransport``
封装 httpx.Client，测试用 ``FakeResourceTransport`` 注入，避免模拟 httpx 内部对象。
"""

import hashlib
import os
import time
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Protocol
from urllib.parse import urljoin

from app.resources.errors import (
    ResourceIntegrityError,
    ResourceLimitExceeded,
    ResourceTransportUnavailable,
)
from app.resources.policy import (
    ValidatedDestination,
    validate_destination,
)


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    sha256: str
    size_bytes: int
    media_type: str
    redirect_chain: tuple[str, ...]


class HttpResponse(Protocol):
    """transport 返回的最小 response 视图，避免暴露 httpx 内部对象。"""

    status_code: int
    headers: Any

    def iter_bytes(
        self, *, chunk_size: int
    ) -> Iterator[bytes]:
        ...


class HttpTransportPort(Protocol):
    def stream(
        self, method: str, url: str
    ) -> AbstractContextManager[HttpResponse]:
        ...


class HttpxTransport:
    """默认 transport：封装 httpx.Client(follow_redirects=False, trust_env=False)。"""

    def __init__(
        self,
        *,
        connect_timeout: float,
        read_timeout: float,
        client: Any | None = None,
    ):
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            import httpx

            self._client = httpx.Client(
                follow_redirects=False,
                trust_env=False,
                timeout=httpx.Timeout(
                    connect=connect_timeout,
                    read=read_timeout,
                    write=read_timeout,
                    pool=connect_timeout,
                ),
                headers={
                    "User-Agent": (
                        "paper-reproduction-copilot-resource/1"
                    )
                },
            )
            self._owns_client = True

    @contextmanager
    def stream(
        self, method: str, url: str
    ) -> Iterator[HttpResponse]:
        try:
            with self._client.stream(
                method, url
            ) as response:
                yield response
        finally:
            pass

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


class HttpResourceDownloader:
    def __init__(
        self,
        *,
        allowed_hosts: tuple[str, ...],
        max_redirects: int,
        connect_timeout: float,
        read_timeout: float,
        total_timeout: float,
        resolver=None,
        transport: HttpTransportPort | None = None,
    ):
        self.allowed_hosts = allowed_hosts
        self.max_redirects = max_redirects
        self.total_timeout = total_timeout
        self.resolver = resolver
        self.transport = transport or HttpxTransport(
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )

    def _validate(
        self, url: str
    ) -> ValidatedDestination:
        kwargs: dict[str, Any] = {
            "allowed_hosts": self.allowed_hosts
        }
        if self.resolver is not None:
            kwargs["resolver"] = self.resolver
        return validate_destination(url, **kwargs)

    def download(
        self,
        *,
        url: str,
        destination: Path,
        max_bytes: int,
        expected_sha256: str | None,
        ensure_active=None,
    ) -> DownloadResult:
        if ensure_active is None:
            ensure_active = lambda: None  # noqa: E731
        destination.parent.mkdir(
            parents=True, exist_ok=True
        )
        if destination.exists() or destination.is_symlink():
            raise ResourceIntegrityError(
                "staging destination 已存在"
            )

        current = url
        redirects: list[str] = []
        started = time.monotonic()
        digest = hashlib.sha256()
        size = 0

        try:
            for redirect_index in range(
                self.max_redirects + 1
            ):
                ensure_active()
                target = self._validate(current)
                redirects.append(target.canonical_url)

                with self.transport.stream(
                    "GET", target.canonical_url
                ) as response:
                    status = response.status_code
                    if status in {
                        301,
                        302,
                        303,
                        307,
                        308,
                    }:
                        location = response.headers.get(
                            "location"
                        )
                        if not location:
                            raise ResourceTransportUnavailable(
                                "redirect 缺少 Location"
                            )
                        if (
                            redirect_index
                            >= self.max_redirects
                        ):
                            raise ResourceLimitExceeded(
                                "redirect 次数超限"
                            )
                        # 下一轮对新 URL 的 scheme/host/DNS 重新验证。
                        current = urljoin(
                            target.canonical_url, location
                        )
                        continue

                    if status >= 500:
                        raise ResourceTransportUnavailable(
                            f"resource server returned {status}"
                        )
                    if status != 200:
                        raise ResourceIntegrityError(
                            f"resource server returned {status}"
                        )

                    declared = response.headers.get(
                        "content-length"
                    )
                    if declared is not None:
                        try:
                            declared_size = int(declared)
                        except ValueError:
                            raise ResourceIntegrityError(
                                "Content-Length 非法"
                            )
                        if declared_size > max_bytes:
                            raise ResourceLimitExceeded(
                                "Content-Length 超过预算"
                            )

                    # 独占创建，避免跟随既有 symlink 或覆盖旧 part。
                    fd = os.open(
                        destination,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL,
                        0o600,
                    )
                    with os.fdopen(fd, "wb") as handle:
                        for chunk in response.iter_bytes(
                            chunk_size=1024 * 1024
                        ):
                            ensure_active()
                            if (
                                time.monotonic() - started
                                > self.total_timeout
                            ):
                                raise ResourceLimitExceeded(
                                    "resource total timeout"
                                )
                            size += len(chunk)
                            if size > max_bytes:
                                raise ResourceLimitExceeded(
                                    "resource bytes 超过预算"
                                )
                            digest.update(chunk)
                            handle.write(chunk)
                        handle.flush()
                        os.fsync(handle.fileno())

                    actual_sha = digest.hexdigest()
                    if (
                        expected_sha256 is not None
                        and actual_sha != expected_sha256
                    ):
                        raise ResourceIntegrityError(
                            "resource SHA-256 与 expected 不一致"
                        )
                    media_type = response.headers.get(
                        "content-type",
                        "application/octet-stream",
                    ).split(";", 1)[0].strip().lower()
                    return DownloadResult(
                        path=destination,
                        sha256=actual_sha,
                        size_bytes=size,
                        media_type=media_type,
                        redirect_chain=tuple(redirects),
                    )
            raise ResourceLimitExceeded("redirect loop")
        except Exception:
            destination.unlink(missing_ok=True)
            raise
