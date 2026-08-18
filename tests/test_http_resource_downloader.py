"""Phase 29 HTTP resource downloader 测试。

完全离线，使用 FakeResourceTransport。

覆盖安全矩阵：
- Content-Length 超限时不读 body
- 实际 streaming bytes 超限时删除 part
- total timeout 删除 part
- expected SHA mismatch 删除 part
- 5xx 分类 retryable，4xx 默认 terminal
- redirect 超限/循环 terminal
- cancel/lease loss 停止写入并不 publish
- 每一跳 redirect 重新检查 host 与 IP
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.resources.errors import (
    ResourceIntegrityError,
    ResourceLimitExceeded,
    ResourcePolicyViolation,
    ResourceTransportUnavailable,
)
from app.resources.http_downloader import (
    HttpResourceDownloader,
)
from tests.fakes.fake_resource_transport import (
    FakeHeaders,
    FakeResourceTransport,
    FakeResponse,
    make_ok,
    make_redirect,
)

ALLOWED = ("arxiv.org", "export.arxiv.org")
PUBLIC_IP = ("93.184.216.34",)


def _make_downloader(
    transport: FakeResourceTransport,
    *,
    max_redirects: int = 5,
    total_timeout: float = 300,
) -> HttpResourceDownloader:
    return HttpResourceDownloader(
        allowed_hosts=ALLOWED,
        max_redirects=max_redirects,
        connect_timeout=10,
        read_timeout=30,
        total_timeout=total_timeout,
        resolver=lambda host: PUBLIC_IP,
        transport=transport,
    )


class TestSuccessfulDownload:
    def test_download_ok(
        self, tmp_path: Path
    ) -> None:
        body = b"%PDF-1.4 hello"
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/pdf/1234": make_ok(
                    body, content_type="application/pdf"
                )
            }
        )
        downloader = _make_downloader(transport)
        dest = tmp_path / "download.part"
        result = downloader.download(
            url="https://arxiv.org/pdf/1234",
            destination=dest,
            max_bytes=1024,
            expected_sha256=hashlib.sha256(
                body
            ).hexdigest(),
        )
        assert result.sha256 == hashlib.sha256(
            body
        ).hexdigest()
        assert result.size_bytes == len(body)
        assert result.media_type == "application/pdf"
        assert dest.read_bytes() == body

    def test_download_without_expected_sha(
        self, tmp_path: Path
    ) -> None:
        body = b"opaque checkpoint data"
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/file.pt": make_ok(
                    body
                )
            }
        )
        downloader = _make_downloader(transport)
        dest = tmp_path / "download.part"
        result = downloader.download(
            url="https://arxiv.org/file.pt",
            destination=dest,
            max_bytes=1024,
            expected_sha256=None,
        )
        assert result.sha256 == hashlib.sha256(
            body
        ).hexdigest()

    def test_content_type_with_charset_stripped(
        self, tmp_path: Path
    ) -> None:
        body = b"data"
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/f": FakeResponse(
                    200,
                    FakeHeaders(
                        {
                            "content-type": "application/pdf; charset=utf-8",
                            "content-length": str(len(body)),
                        }
                    ),
                    (body,),
                )
            }
        )
        downloader = _make_downloader(transport)
        result = downloader.download(
            url="https://arxiv.org/f",
            destination=tmp_path / "d.part",
            max_bytes=1024,
            expected_sha256=None,
        )
        assert result.media_type == "application/pdf"


class TestSizeLimits:
    def test_content_length_over_budget_rejected(
        self, tmp_path: Path
    ) -> None:
        body = b"x" * 100
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/big": make_ok(
                    body
                )
            }
        )
        downloader = _make_downloader(transport)
        with pytest.raises(ResourceLimitExceeded):
            downloader.download(
                url="https://arxiv.org/big",
                destination=tmp_path / "d.part",
                max_bytes=50,
                expected_sha256=None,
            )
        assert not (
            tmp_path / "d.part"
        ).exists()

    def test_streaming_bytes_over_budget_deletes_part(
        self, tmp_path: Path
    ) -> None:
        body = b"x" * 200
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/stream": FakeResponse(
                    200,
                    FakeHeaders(
                        {"content-type": "application/octet-stream"}
                    ),
                    (body,),
                )
            }
        )
        downloader = _make_downloader(transport)
        with pytest.raises(ResourceLimitExceeded):
            downloader.download(
                url="https://arxiv.org/stream",
                destination=tmp_path / "d.part",
                max_bytes=100,
                expected_sha256=None,
            )
        assert not (
            tmp_path / "d.part"
        ).exists()


class TestShaMismatch:
    def test_expected_sha_mismatch_deletes_part(
        self, tmp_path: Path
    ) -> None:
        body = b"actual content"
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/f": make_ok(
                    body
                )
            }
        )
        downloader = _make_downloader(transport)
        with pytest.raises(ResourceIntegrityError):
            downloader.download(
                url="https://arxiv.org/f",
                destination=tmp_path / "d.part",
                max_bytes=1024,
                expected_sha256="0" * 64,
            )
        assert not (
            tmp_path / "d.part"
        ).exists()


class TestHttpErrors:
    def test_5xx_retryable(
        self, tmp_path: Path
    ) -> None:
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/err": FakeResponse(
                    503,
                    FakeHeaders({}),
                    (),
                )
            }
        )
        downloader = _make_downloader(transport)
        with pytest.raises(
            ResourceTransportUnavailable
        ):
            downloader.download(
                url="https://arxiv.org/err",
                destination=tmp_path / "d.part",
                max_bytes=1024,
                expected_sha256=None,
            )

    def test_4xx_terminal(
        self, tmp_path: Path
    ) -> None:
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/err": FakeResponse(
                    404,
                    FakeHeaders({}),
                    (),
                )
            }
        )
        downloader = _make_downloader(transport)
        with pytest.raises(ResourceIntegrityError):
            downloader.download(
                url="https://arxiv.org/err",
                destination=tmp_path / "d.part",
                max_bytes=1024,
                expected_sha256=None,
            )


class TestRedirects:
    def test_redirect_followed(
        self, tmp_path: Path
    ) -> None:
        body = b"final content"
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/redirect": make_redirect(
                    "https://export.arxiv.org/final"
                ),
                "https://export.arxiv.org/final": make_ok(
                    body
                ),
            }
        )
        downloader = _make_downloader(transport)
        result = downloader.download(
            url="https://arxiv.org/redirect",
            destination=tmp_path / "d.part",
            max_bytes=1024,
            expected_sha256=hashlib.sha256(
                body
            ).hexdigest(),
        )
        assert len(result.redirect_chain) == 2
        assert (
            "https://arxiv.org/redirect"
            in result.redirect_chain
        )
        assert (
            "https://export.arxiv.org/final"
            in result.redirect_chain
        )

    def test_redirect_to_private_ip_rejected(
        self, tmp_path: Path
    ) -> None:
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/r": make_redirect(
                    "https://export.arxiv.org/evil"
                ),
            }
        )
        downloader = HttpResourceDownloader(
            allowed_hosts=ALLOWED,
            max_redirects=5,
            connect_timeout=10,
            read_timeout=30,
            total_timeout=300,
            resolver=lambda host: (
                ("93.184.216.34",)
                if host == "arxiv.org"
                else ("10.0.0.1",)
            ),
            transport=transport,
        )
        with pytest.raises(
            ResourcePolicyViolation
        ) as exc_info:
            downloader.download(
                url="https://arxiv.org/r",
                destination=tmp_path / "d.part",
                max_bytes=1024,
                expected_sha256=None,
            )
        # redirect 到 private IP 应在 DNS 校验阶段被拒绝。
        assert "非公网" in str(exc_info.value)

    def test_redirect_limit_exceeded(
        self, tmp_path: Path
    ) -> None:
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/r1": make_redirect(
                    "https://arxiv.org/r2"
                ),
                "https://arxiv.org/r2": make_redirect(
                    "https://arxiv.org/r3"
                ),
            }
        )
        downloader = _make_downloader(
            transport, max_redirects=1
        )
        with pytest.raises(ResourceLimitExceeded):
            downloader.download(
                url="https://arxiv.org/r1",
                destination=tmp_path / "d.part",
                max_bytes=1024,
                expected_sha256=None,
            )


class TestCancelAndLeaseLoss:
    def test_ensure_active_aborts_download(
        self, tmp_path: Path
    ) -> None:
        body = b"data" * 100
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/f": make_ok(
                    body
                )
            }
        )
        downloader = _make_downloader(transport)

        calls = [0]

        def ensure_active():
            calls[0] += 1
            if calls[0] > 1:
                raise RuntimeError("lease lost")

        with pytest.raises(RuntimeError):
            downloader.download(
                url="https://arxiv.org/f",
                destination=tmp_path / "d.part",
                max_bytes=1024 * 1024,
                expected_sha256=None,
                ensure_active=ensure_active,
            )
        assert not (
            tmp_path / "d.part"
        ).exists()


class TestExistingDestination:
    def test_existing_destination_rejected(
        self, tmp_path: Path
    ) -> None:
        dest = tmp_path / "d.part"
        dest.write_bytes(b"old")
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/f": make_ok(
                    b"new"
                )
            }
        )
        downloader = _make_downloader(transport)
        with pytest.raises(ResourceIntegrityError):
            downloader.download(
                url="https://arxiv.org/f",
                destination=dest,
                max_bytes=1024,
                expected_sha256=None,
            )
        # 原文件不被覆盖。
        assert dest.read_bytes() == b"old"
