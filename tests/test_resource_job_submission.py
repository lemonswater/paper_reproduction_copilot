"""Phase 29 Resource -> Job submission 集成测试。

覆盖：
- Job 只能引用 published Resource
- Job 冻结 Resource manifest snapshot（不动态读取）
- JobCreateRequest 二选一约束（本地路径 vs resource_id）
- ResolvedResourceInput 包含完整 content identity
"""

from __future__ import annotations

import pytest

from app.interaction.schemas import (
    JobCreateRequest,
)
from app.interaction.service import (
    InteractionService,
)
from app.job_runtime.schemas import (
    JobRequest,
    ResolvedResourceInput,
)
from app.resources.request_hash import (
    resource_request_sha256,
)
from app.resources.schemas import (
    ResourceApproval,
    ResourceManifest,
    ResourceRequest,
)
from app.resources.service import ResourceService
from tests.fakes.fake_resource_repository import (
    FakeResourceRepository,
)


def _make_manifest(
    *,
    resource_id: str = "res_pub1",
    kind: str = "paper_pdf",
    sha256: str = "a" * 64,
    size_bytes: int = 100,
    git_commit: str | None = None,
) -> ResourceManifest:
    return ResourceManifest(
        manifest_sha256="b" * 64,
        resource_id=resource_id,
        kind=kind,
        source_url_sanitized="https://arxiv.org/pdf/1234",
        object_key=f"resources/sha256/{sha256[:2]}/{sha256}",
        sha256=sha256,
        size_bytes=size_bytes,
        media_type="application/pdf",
        git_commit=git_commit,
        acquired_at="2026-01-01T00:00:00+00:00",
    )


class TestJobCreateRequestValidation:
    def test_paper_resource_only_valid(self) -> None:
        req = JobCreateRequest(
            paper_resource_id="res_1",
            repo_path="/tmp/repo",
            execution_profile_id="local",
        )
        assert req.paper_resource_id == "res_1"

    def test_paper_path_only_valid(self) -> None:
        req = JobCreateRequest(
            paper_path="/tmp/paper.pdf",
            repo_path="/tmp/repo",
            execution_profile_id="local",
        )
        assert req.paper_path == "/tmp/paper.pdf"

    def test_both_paper_inputs_rejected(self) -> None:
        with pytest.raises(
            ValueError
        ) as exc_info:
            JobCreateRequest(
                paper_path="/tmp/paper.pdf",
                paper_resource_id="res_1",
                repo_path="/tmp/repo",
                execution_profile_id="local",
            )
        assert "paper_path" in str(exc_info.value)

    def test_neither_paper_input_rejected(self) -> None:
        with pytest.raises(
            ValueError
        ) as exc_info:
            JobCreateRequest(
                repo_path="/tmp/repo",
                execution_profile_id="local",
            )
        assert "paper_path" in str(exc_info.value)

    def test_both_repo_inputs_rejected(self) -> None:
        with pytest.raises(ValueError):
            JobCreateRequest(
                paper_path="/tmp/paper.pdf",
                repo_path="/tmp/repo",
                repo_resource_id="res_2",
                execution_profile_id="local",
            )


class TestResolvedResourceInput:
    def test_resolved_input_freezes_identity(self) -> None:
        resolved = ResolvedResourceInput(
            resource_id="res_1",
            manifest_sha256="a" * 64,
            object_key="resources/sha256/aa/" + "a" * 64,
            content_sha256="b" * 64,
            size_bytes=100,
            kind="paper_pdf",
        )
        assert resolved.resource_id == "res_1"
        assert resolved.content_sha256 == "b" * 64

    def test_resolved_input_rejects_bad_hash(
        self,
    ) -> None:
        with pytest.raises(Exception):
            ResolvedResourceInput(
                resource_id="res_1",
                manifest_sha256="short",
                object_key="key",
                content_sha256="b" * 64,
                size_bytes=100,
                kind="paper_pdf",
            )


class TestResourceResolution:
    def test_resolve_published_resource(
        self,
    ) -> None:
        """InteractionService._resolve_resource 解析 published Resource。"""

        repository = FakeResourceRepository()
        service = ResourceService(repository)

        request = ResourceRequest(
            kind="paper_pdf",
            source_url="https://arxiv.org/pdf/1234",
            purpose="paper",
        )
        sha = resource_request_sha256(request)
        repository.submit(
            resource_id="res_pub1",
            idempotency_key="key1",
            request=request,
            request_sha256=sha,
        )
        approval = ResourceApproval(
            decision="approved",
            request_sha256=sha,
            decided_by="operator",
            decided_at="2026-01-01T00:00:00+00:00",
            reason="ok",
        )
        repository.approve(
            resource_id="res_pub1",
            approval=approval,
            expected_version=None,
        )

        # 模拟 published 状态。
        manifest = _make_manifest()
        stored = repository._store["res_pub1"]
        stored.record = stored.record.model_copy(
            update={
                "status": "published",
                "manifest": manifest,
            }
        )

        class FakeJobService:
            def submit(self, **kwargs):  # noqa: ARG002
                return (None, True)

        interaction = InteractionService(
            FakeJobService(),  # type: ignore[arg-type]
            resource_service=service,
        )
        resolved = interaction._resolve_resource(
            "res_pub1"
        )
        assert resolved.resource_id == "res_pub1"
        assert (
            resolved.content_sha256
            == manifest.sha256
        )
        assert (
            resolved.manifest_sha256
            == manifest.manifest_sha256
        )

    def test_resolve_non_published_rejected(
        self,
    ) -> None:
        repository = FakeResourceRepository()
        service = ResourceService(repository)

        request = ResourceRequest(
            kind="paper_pdf",
            source_url="https://arxiv.org/pdf/1234",
            purpose="paper",
        )
        sha = resource_request_sha256(request)
        repository.submit(
            resource_id="res_pending",
            idempotency_key="key2",
            request=request,
            request_sha256=sha,
        )

        class FakeJobService:
            def submit(self, **kwargs):  # noqa: ARG002
                return (None, True)

        interaction = InteractionService(
            FakeJobService(),  # type: ignore[arg-type]
            resource_service=service,
        )
        with pytest.raises(
            ValueError
        ) as exc_info:
            interaction._resolve_resource(
                "res_pending"
            )
        assert "published" in str(exc_info.value)

    def test_resolve_nonexistent_rejected(
        self,
    ) -> None:
        repository = FakeResourceRepository()
        service = ResourceService(repository)

        class FakeJobService:
            def submit(self, **kwargs):  # noqa: ARG002
                return (None, True)

        interaction = InteractionService(
            FakeJobService(),  # type: ignore[arg-type]
            resource_service=service,
        )
        with pytest.raises(ValueError):
            interaction._resolve_resource(
                "res_missing"
            )


class TestJobRequestWithResource:
    def test_job_request_with_resource_only(
        self,
    ) -> None:
        resolved = ResolvedResourceInput(
            resource_id="res_1",
            manifest_sha256="a" * 64,
            object_key="key",
            content_sha256="b" * 64,
            size_bytes=100,
            kind="paper_pdf",
        )
        request = JobRequest(
            paper_resource=resolved,
            repo_path="/tmp/repo",
            execution_profile_id="local",
        )
        assert request.paper_path is None
        assert request.paper_resource is not None

    def test_job_request_with_paths_only(
        self,
    ) -> None:
        request = JobRequest(
            paper_path="/tmp/paper.pdf",
            repo_path="/tmp/repo",
            execution_profile_id="local",
        )
        assert request.paper_path is not None
        assert request.paper_resource is None
