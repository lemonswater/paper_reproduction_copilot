"""Phase 29 URL 规范化与 request hash 测试。

审批必须绑定 request_sha256；审批后 URL/commit/hash/purpose 任一改变，
旧 approval 自动失效（stale approval）。
"""

from __future__ import annotations

import pytest

from app.resources.request_hash import (
    canonicalize_url,
    resource_request_sha256,
)
from app.resources.schemas import ResourceRequest


class TestCanonicalizeUrl:
    def test_basic_https(self) -> None:
        assert (
            canonicalize_url(
                "https://arxiv.org/pdf/1234.5678"
            )
            == "https://arxiv.org/pdf/1234.5678"
        )

    def test_trailing_slash_normalized(self) -> None:
        result = canonicalize_url(
            "https://github.com/org/repo/"
        )
        assert result == (
            "https://github.com/org/repo/"
        )

    def test_idna_host(self) -> None:
        result = canonicalize_url(
            "https://xn--e1afmkfd.org/path"
        )
        assert result == (
            "https://xn--e1afmkfd.org/path"
        )

    def test_uppercase_scheme_normalized(self) -> None:
        result = canonicalize_url(
            "HTTPS://arxiv.org/pdf/1234"
        )
        assert result == (
            "https://arxiv.org/pdf/1234"
        )

    def test_uppercase_host_normalized(self) -> None:
        result = canonicalize_url(
            "https://ARXIV.ORG/pdf/1234"
        )
        assert result == "https://arxiv.org/pdf/1234"

    def test_explicit_443_stripped(self) -> None:
        result = canonicalize_url(
            "https://arxiv.org:443/pdf/1234"
        )
        assert result == (
            "https://arxiv.org/pdf/1234"
        )

    @pytest.mark.parametrize(
        "url",
        [
            "http://arxiv.org/pdf",
            "ftp://arxiv.org/file",
            "https://user:pass@arxiv.org/pdf",
            "https://arxiv.org/pdf?token=x",
            "https://arxiv.org/pdf#frag",
            "https://arxiv.org:8443/pdf",
        ],
    )
    def test_invalid_urls_rejected(
        self, url: str
    ) -> None:
        with pytest.raises(ValueError):
            canonicalize_url(url)

    def test_empty_url_rejected(self) -> None:
        with pytest.raises(ValueError):
            canonicalize_url("")

    def test_path_percent_encoding_stable(
        self,
    ) -> None:
        result = canonicalize_url(
            "https://arxiv.org/pdf/abc%20def"
        )
        assert "%20" in result


class TestRequestHash:
    def _make_request(
        self, **overrides
    ) -> ResourceRequest:
        kwargs = {
            "kind": "paper_pdf",
            "source_url": "https://arxiv.org/pdf/1234.5678",
            "purpose": "paper input",
        }
        kwargs.update(overrides)
        return ResourceRequest(**kwargs)

    def test_same_request_same_hash(self) -> None:
        r1 = self._make_request()
        r2 = self._make_request()
        assert resource_request_sha256(r1) == (
            resource_request_sha256(r2)
        )

    def test_different_url_different_hash(
        self,
    ) -> None:
        r1 = self._make_request(
            source_url="https://arxiv.org/pdf/1111.1111"
        )
        r2 = self._make_request(
            source_url="https://arxiv.org/pdf/2222.2222"
        )
        assert resource_request_sha256(r1) != (
            resource_request_sha256(r2)
        )

    def test_different_purpose_different_hash(
        self,
    ) -> None:
        r1 = self._make_request(purpose="purpose A")
        r2 = self._make_request(purpose="purpose B")
        assert resource_request_sha256(r1) != (
            resource_request_sha256(r2)
        )

    def test_different_kind_different_hash(
        self,
    ) -> None:
        r1 = self._make_request(kind="paper_pdf")
        r2 = self._make_request(kind="checkpoint",
            expected_sha256="a" * 64,
        )
        assert resource_request_sha256(r1) != (
            resource_request_sha256(r2)
        )

    def test_url_normalization_stable_hash(
        self,
    ) -> None:
        """URL 大小写/端口差异规范化后 hash 一致。"""
        r1 = self._make_request(
            source_url="https://arxiv.org/pdf/1234"
        )
        r2 = self._make_request(
            source_url="https://ARXIV.ORG:443/pdf/1234"
        )
        assert resource_request_sha256(r1) == (
            resource_request_sha256(r2)
        )

    def test_different_expected_sha_different_hash(
        self,
    ) -> None:
        r1 = self._make_request(
            expected_sha256="a" * 64
        )
        r2 = self._make_request(
            expected_sha256="b" * 64
        )
        assert resource_request_sha256(r1) != (
            resource_request_sha256(r2)
        )

    def test_hash_is_64_hex(self) -> None:
        sha = resource_request_sha256(
            self._make_request()
        )
        assert len(sha) == 64
        int(sha, 16)  # 不抛异常即合法 hex

    def test_git_commit_affects_hash(self) -> None:
        r1 = ResourceRequest(
            kind="git_repository",
            source_url="https://github.com/org/repo",
            expected_git_commit="a" * 40,
            purpose="repo",
        )
        r2 = ResourceRequest(
            kind="git_repository",
            source_url="https://github.com/org/repo",
            expected_git_commit="b" * 40,
            purpose="repo",
        )
        assert resource_request_sha256(r1) != (
            resource_request_sha256(r2)
        )
