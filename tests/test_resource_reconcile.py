"""Phase 29 Resource 崩溃恢复（reconcile）测试。

恢复矩阵：
- fetching + 无 part -> 可安全 requeue
- fetching + part 存在 -> reconciliation_required
- published + manifest/blob 匹配 -> already_published
- blob 已写但 DB 未提交 -> publication_recovered
- claim ownership 不匹配 -> ownership_mismatch
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.resources.publisher import (
    ResourcePublisher,
    resource_object_key,
)
from app.resources.reconcile import (
    ResourceReconciler,
)
from app.resources.request_hash import (
    resource_request_sha256,
)
from app.resources.schemas import (
    ResourceApproval,
    ResourceManifest,
    ResourceRequest,
)
from app.storage.ports import OpenedBlob
from app.storage.schemas import BlobStat
from tests.fakes.fake_resource_repository import (
    FakeResourceRepository,
)


@dataclass
class FakeBlobStore:
    backend_name: str = "fake"
    sharing_scope: str = "host"
    _blobs: dict[str, bytes] = field(default_factory=dict)

    def ensure_ready(self) -> None:
        pass

    def stat(
        self, object_key: str
    ) -> BlobStat | None:
        data = self._blobs.get(object_key)
        if data is None:
            return None
        return BlobStat(
            backend=self.backend_name,
            object_key=object_key,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            etag=hashlib.sha256(data).hexdigest(),
        )

    def put_file(
        self,
        *,
        object_key: str,
        source_path: Path,
        expected_sha256: str,
        expected_size: int,
        media_type: str,
    ) -> BlobStat:
        del media_type
        data = source_path.read_bytes()
        self._blobs[object_key] = data
        return BlobStat(
            backend=self.backend_name,
            object_key=object_key,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            etag=hashlib.sha256(data).hexdigest(),
        )

    def open(
        self, object_key: str
    ) -> OpenedBlob:
        import io

        data = self._blobs[object_key]
        stat = self.stat(object_key)
        assert stat is not None
        return OpenedBlob(
            stat=stat,
            body=io.BytesIO(data),
        )


@pytest.fixture
def repository() -> FakeResourceRepository:
    return FakeResourceRepository()


@pytest.fixture
def blob_store() -> FakeBlobStore:
    return FakeBlobStore()


@pytest.fixture
def reconciler(
    repository: FakeResourceRepository,
    blob_store: FakeBlobStore,
) -> ResourceReconciler:
    return ResourceReconciler(
        repository=repository,
        blob_store=blob_store,
        publisher=ResourcePublisher(
            blob_store=blob_store
        ),
    )


def _make_pdf_request() -> ResourceRequest:
    return ResourceRequest(
        kind="paper_pdf",
        source_url="https://arxiv.org/pdf/1234.5678",
        purpose="paper",
    )


def _submit_and_claim_expired(
    repository: FakeResourceRepository,
    *,
    resource_id: str = "res_recon1",
    idempotency_key: str = "recon1",
) -> str:
    """提交、批准、claim，然后让 lease 过期。返回 claim_token。"""

    request = _make_pdf_request()
    sha = resource_request_sha256(request)
    record, _ = repository.submit(
        resource_id=resource_id,
        idempotency_key=idempotency_key,
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
        resource_id=resource_id,
        approval=approval,
        expected_version=None,
    )
    claimed = repository.claim_next(
        worker_id="dead_worker",
        lease_seconds=60,
    )
    assert claimed is not None
    token = repository.last_claim_token
    assert token is not None

    # 模拟 lease 过期。
    repository.advance_clock(120)
    return token


class TestRequeueExpired:
    def test_no_part_safe_requeue(
        self,
        repository: FakeResourceRepository,
        reconciler: ResourceReconciler,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "app.resources.reconcile.settings.resource_staging_root",
            tmp_path / "staging",
        )
        token = _submit_and_claim_expired(repository)

        # 使用实际 claim token 直接调用 _reconcile_one。
        # 生产 reconciler 无法获得原 token，用 placeholder；
        # 测试注入真实 token 验证 requeue 语义。
        record = repository.get("res_recon1")
        result = reconciler._reconcile_one(
            record, token
        )
        assert result.disposition == "safe_to_requeue"
        updated = repository.get("res_recon1")
        assert updated.status == "queued"

    def test_with_part_reconciliation_required(
        self,
        repository: FakeResourceRepository,
        reconciler: ResourceReconciler,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        staging = tmp_path / "staging"
        monkeypatch.setattr(
            "app.resources.reconcile.settings.resource_staging_root",
            staging,
        )
        token = _submit_and_claim_expired(repository)

        # 创建 part 文件模拟未完成的下载。
        from app.observability.context import (
            short_secret_hash,
        )

        part_dir = (
            staging
            / "res_recon1"
            / short_secret_hash(token)
        )
        part_dir.mkdir(parents=True)
        (part_dir / "download.part").write_bytes(
            b"partial"
        )

        record = repository.get("res_recon1")
        result = reconciler._reconcile_one(
            record, token
        )
        assert (
            result.disposition
            == "reconciliation_required"
        )
        updated = repository.get("res_recon1")
        assert (
            updated.status
            == "reconciliation_required"
        )

    def test_placeholder_token_ownership_mismatch(
        self,
        repository: FakeResourceRepository,
        reconciler: ResourceReconciler,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """生产 reconciler 用 placeholder token，不能匹配真实 claim。"""

        monkeypatch.setattr(
            "app.resources.reconcile.settings.resource_staging_root",
            tmp_path / "staging",
        )
        _submit_and_claim_expired(repository)

        results = reconciler.reconcile_expired()
        assert len(results) == 1
        # placeholder token 不匹配真实 claim -> ownership_mismatch。
        assert (
            results[0].disposition
            == "ownership_mismatch"
        )


class TestPublicationRecovery:
    def test_blob_exists_publication_recovered(
        self,
        repository: FakeResourceRepository,
        blob_store: FakeBlobStore,
        reconciler: ResourceReconciler,
    ) -> None:
        body = b"%PDF-1.4 recovered content"
        sha = hashlib.sha256(body).hexdigest()
        key = resource_object_key(sha)
        blob_store._blobs[key] = body

        result = reconciler.recover_publication(
            resource_id="res_recovery1",
            sha256=sha,
            size_bytes=len(body),
        )
        assert (
            result.disposition
            == "publication_recovered"
        )

    def test_blob_missing_terminal_failure(
        self,
        reconciler: ResourceReconciler,
    ) -> None:
        result = reconciler.recover_publication(
            resource_id="res_missing",
            sha256="a" * 64,
            size_bytes=100,
        )
        assert (
            result.disposition
            == "terminal_integrity_failure"
        )

    def test_blob_hash_mismatch(
        self,
        blob_store: FakeBlobStore,
        reconciler: ResourceReconciler,
    ) -> None:
        body = b"wrong content"
        wrong_sha = "a" * 64
        key = resource_object_key(wrong_sha)
        blob_store._blobs[key] = body

        result = reconciler.recover_publication(
            resource_id="res_mismatch",
            sha256=wrong_sha,
            size_bytes=999,
        )
        assert (
            result.disposition
            == "terminal_integrity_failure"
        )


class TestVerifyPublished:
    def test_published_consistent(
        self,
        repository: FakeResourceRepository,
        blob_store: FakeBlobStore,
        reconciler: ResourceReconciler,
    ) -> None:
        body = b"%PDF-1.4 published"
        sha = hashlib.sha256(body).hexdigest()
        key = resource_object_key(sha)
        blob_store._blobs[key] = body

        manifest = ResourceManifest(
            manifest_sha256="a" * 64,
            resource_id="res_pub1",
            kind="paper_pdf",
            source_url_sanitized="https://arxiv.org/pdf/1234",
            object_key=key,
            sha256=sha,
            size_bytes=len(body),
            media_type="application/pdf",
            acquired_at="2026-01-01T00:00:00+00:00",
        )
        request = _make_pdf_request()
        record, _ = repository.submit(
            resource_id="res_pub1",
            idempotency_key="pub1",
            request=request,
            request_sha256=resource_request_sha256(
                request
            ),
        )
        from app.resources.schemas import (
            ResourceRecord,
        )
        published = ResourceRecord(
            resource_id="res_pub1",
            idempotency_key="pub1",
            request=request,
            request_sha256=record.request_sha256,
            approval=None,
            status="published",
            version=1,
            attempt_count=1,
            manifest=manifest,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        result = reconciler.verify_published(
            record=published
        )
        assert (
            result.disposition == "already_published"
        )

    def test_published_blob_missing(
        self,
        repository: FakeResourceRepository,
        reconciler: ResourceReconciler,
    ) -> None:
        request = _make_pdf_request()
        record, _ = repository.submit(
            resource_id="res_pub2",
            idempotency_key="pub2",
            request=request,
            request_sha256=resource_request_sha256(
                request
            ),
        )
        manifest = ResourceManifest(
            manifest_sha256="b" * 64,
            resource_id="res_pub2",
            kind="paper_pdf",
            source_url_sanitized="https://arxiv.org/pdf/1234",
            object_key="resources/sha256/aa/" + "a" * 64,
            sha256="a" * 64,
            size_bytes=100,
            media_type="application/pdf",
            acquired_at="2026-01-01T00:00:00+00:00",
        )
        from app.resources.schemas import (
            ResourceRecord,
        )
        published = ResourceRecord(
            resource_id="res_pub2",
            idempotency_key="pub2",
            request=request,
            request_sha256=record.request_sha256,
            approval=None,
            status="published",
            version=1,
            attempt_count=1,
            manifest=manifest,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        result = reconciler.verify_published(
            record=published
        )
        assert (
            result.disposition
            == "terminal_integrity_failure"
        )
