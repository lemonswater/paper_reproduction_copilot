"""Phase 29 Resource schemas 负向测试。

覆盖三类资源的身份约束：
- paper_pdf：URL HTTPS PDF，expected_sha256 可选，不能带 commit。
- git_repository：必须 exact commit，不接受下载文件 expected_sha256。
- checkpoint：必须在下载前提供 expected_sha256，不能带 commit。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.resources.schemas import (
    ResourceApproval,
    ResourceManifest,
    ResourceRequest,
    TERMINAL_RESOURCE_STATUSES,
)


class TestPaperPdfSchema:
    def test_paper_pdf_minimal_valid(self) -> None:
        request = ResourceRequest(
            kind="paper_pdf",
            source_url="https://arxiv.org/pdf/1234.5678",
            purpose="PSTNet paper input",
        )
        assert request.expected_sha256 is None
        assert request.expected_git_commit is None

    def test_paper_pdf_with_expected_sha256(self) -> None:
        request = ResourceRequest(
            kind="paper_pdf",
            source_url="https://arxiv.org/pdf/1234.5678",
            expected_sha256="a" * 64,
            purpose="paper",
        )
        assert request.expected_sha256 == "a" * 64

    def test_paper_pdf_rejects_git_commit(self) -> None:
        with pytest.raises(
            ValidationError
        ) as exc_info:
            ResourceRequest(
                kind="paper_pdf",
                source_url="https://arxiv.org/pdf/1234.5678",
                expected_git_commit="b" * 40,
                purpose="paper",
            )
        assert "expected_git_commit" in str(
            exc_info.value
        )

    def test_paper_pdf_uppercase_sha_normalized(self) -> None:
        request = ResourceRequest(
            kind="paper_pdf",
            source_url="https://arxiv.org/pdf/1234.5678",
            expected_sha256="A" * 64,
            purpose="paper",
        )
        assert request.expected_sha256 == "a" * 64

    def test_paper_pdf_invalid_sha_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ResourceRequest(
                kind="paper_pdf",
                source_url="https://arxiv.org/pdf/1234.5678",
                expected_sha256="xyz",
                purpose="paper",
            )


class TestGitRepositorySchema:
    def test_git_valid_with_commit(self) -> None:
        request = ResourceRequest(
            kind="git_repository",
            source_url="https://github.com/org/repo",
            expected_git_commit="a" * 40,
            purpose="repo input",
        )
        assert request.expected_git_commit == "a" * 40

    def test_git_requires_commit(self) -> None:
        with pytest.raises(
            ValidationError
        ) as exc_info:
            ResourceRequest(
                kind="git_repository",
                source_url="https://github.com/org/repo",
                purpose="repo",
            )
        assert "exact commit" in str(exc_info.value)

    def test_git_rejects_expected_sha256(self) -> None:
        with pytest.raises(
            ValidationError
        ) as exc_info:
            ResourceRequest(
                kind="git_repository",
                source_url="https://github.com/org/repo",
                expected_git_commit="a" * 40,
                expected_sha256="b" * 64,
                purpose="repo",
            )
        assert "expected_sha256" in str(
            exc_info.value
        )

    def test_git_commit_64_chars_accepted(self) -> None:
        request = ResourceRequest(
            kind="git_repository",
            source_url="https://github.com/org/repo",
            expected_git_commit="c" * 64,
            purpose="repo",
        )
        assert len(request.expected_git_commit) == 64


class TestCheckpointSchema:
    def test_checkpoint_valid_with_sha(self) -> None:
        request = ResourceRequest(
            kind="checkpoint",
            source_url="https://example.com/model.pt",
            expected_sha256="d" * 64,
            purpose="pretrained weights",
        )
        assert request.expected_sha256 == "d" * 64

    def test_checkpoint_requires_sha(self) -> None:
        with pytest.raises(
            ValidationError
        ) as exc_info:
            ResourceRequest(
                kind="checkpoint",
                source_url="https://example.com/model.pt",
                purpose="weights",
            )
        assert "expected_sha256" in str(
            exc_info.value
        )

    def test_checkpoint_rejects_git_commit(self) -> None:
        with pytest.raises(ValidationError):
            ResourceRequest(
                kind="checkpoint",
                source_url="https://example.com/model.pt",
                expected_sha256="d" * 64,
                expected_git_commit="e" * 40,
                purpose="weights",
            )


class TestResourceApproval:
    def test_approval_valid(self) -> None:
        approval = ResourceApproval(
            decision="approved",
            request_sha256="a" * 64,
            decided_by="operator",
            decided_at="2026-01-01T00:00:00+00:00",
            reason="ok",
        )
        assert approval.decision == "approved"

    def test_approval_rejects_invalid_decision(self) -> None:
        with pytest.raises(ValidationError):
            ResourceApproval(
                decision="maybe",
                request_sha256="a" * 64,
                decided_by="operator",
                decided_at="2026-01-01T00:00:00+00:00",
            )

    def test_approval_rejects_bad_hash(self) -> None:
        with pytest.raises(ValidationError):
            ResourceApproval(
                decision="approved",
                request_sha256="short",
                decided_by="operator",
                decided_at="2026-01-01T00:00:00+00:00",
            )


class TestResourceManifest:
    def _manifest_kwargs(self) -> dict:
        return {
            "manifest_sha256": "a" * 64,
            "resource_id": "res_123",
            "kind": "paper_pdf",
            "source_url_sanitized": (
                "https://arxiv.org/pdf/1234.5678"
            ),
            "object_key": "resources/sha256/aa/" + "a" * 64,
            "sha256": "a" * 64,
            "size_bytes": 100,
            "media_type": "application/pdf",
            "acquired_at": "2026-01-01T00:00:00+00:00",
        }

    def test_manifest_valid(self) -> None:
        manifest = ResourceManifest(
            **self._manifest_kwargs()
        )
        assert manifest.manifest_version == "phase29-v1"

    def test_manifest_rejects_extra_fields(self) -> None:
        kwargs = self._manifest_kwargs()
        kwargs["extra"] = "bad"
        with pytest.raises(ValidationError):
            ResourceManifest(**kwargs)

    def test_manifest_rejects_negative_size(self) -> None:
        kwargs = self._manifest_kwargs()
        kwargs["size_bytes"] = -1
        with pytest.raises(ValidationError):
            ResourceManifest(**kwargs)


class TestTerminalStatuses:
    def test_published_is_terminal(self) -> None:
        assert "published" in TERMINAL_RESOURCE_STATUSES

    def test_failed_terminal_is_terminal(self) -> None:
        assert (
            "failed_terminal"
            in TERMINAL_RESOURCE_STATUSES
        )

    def test_queued_is_not_terminal(self) -> None:
        assert "queued" not in TERMINAL_RESOURCE_STATUSES

    def test_fetching_is_not_terminal(self) -> None:
        assert (
            "fetching" not in TERMINAL_RESOURCE_STATUSES
        )
