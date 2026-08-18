"""Phase 29 Resource Worker (Acquisition Worker) 测试。

安全矩阵：
- 修改 URL/commit/hash 后旧 approval 失效（stale approval）
- 旧 claim 完成后不能 mark_published
- 同 idempotency key + 同 request 返回同 Resource
- published blob 已存在时验证后复用
- cancel/lease loss 停止写入并不 publish
- 5xx retryable, 4xx/policy/integrity terminal
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.resources.http_downloader import (
    HttpResourceDownloader,
)
from app.resources.publisher import (
    ResourcePublisher,
)
from app.resources.request_hash import (
    resource_request_sha256,
)
from app.resources.schemas import (
    ResourceApproval,
    ResourceRequest,
)
from app.resources.worker import (
    ResourceWorker,
)
from app.storage.ports import OpenedBlob
from app.storage.schemas import BlobStat
from tests.fakes.fake_resource_repository import (
    FakeResourceRepository,
)
from tests.fakes.fake_resource_transport import (
    FakeResourceTransport,
    make_ok,
)
from tests.fakes.pdf_helpers import make_valid_pdf_bytes


@dataclass
class FakeBlobStore:
    """内存 BlobStore，用于 Worker 测试。"""

    backend_name: str = "fake"
    sharing_scope: str = "host"
    _blobs: dict[str, bytes] = None

    def __post_init__(self) -> None:
        self._blobs = {}

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
        if len(data) != expected_size:
            raise ValueError("size mismatch")
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected_sha256:
            raise ValueError("sha mismatch")
        self._blobs[object_key] = data
        return BlobStat(
            backend=self.backend_name,
            object_key=object_key,
            size_bytes=len(data),
            sha256=actual,
            etag=actual,
        )

    def open(
        self, object_key: str
    ) -> OpenedBlob:
        data = self._blobs[object_key]
        import io

        stat = self.stat(object_key)
        assert stat is not None
        return OpenedBlob(
            stat=stat,
            body=io.BytesIO(data),
        )


@pytest.fixture
def fake_blob_store() -> FakeBlobStore:
    return FakeBlobStore()


@pytest.fixture
def repository() -> FakeResourceRepository:
    return FakeResourceRepository()


def _make_pdf_request(
    *, url: str = "https://arxiv.org/pdf/1234.5678",
    purpose: str = "paper",
    expected_sha256: str | None = None,
) -> ResourceRequest:
    return ResourceRequest(
        kind="paper_pdf",
        source_url=url,
        purpose=purpose,
        expected_sha256=expected_sha256,
    )


def _approve(
    repository: FakeResourceRepository,
    record,
) -> None:
    approval = ResourceApproval(
        decision="approved",
        request_sha256=record.request_sha256,
        decided_by="operator",
        decided_at="2026-01-01T00:00:00+00:00",
        reason="ok",
    )
    repository.approve(
        resource_id=record.resource_id,
        approval=approval,
        expected_version=None,
    )


def _make_worker(
    *,
    repository: FakeResourceRepository,
    blob_store: FakeBlobStore,
    transport: FakeResourceTransport | None = None,
) -> ResourceWorker:
    downloader = HttpResourceDownloader(
        allowed_hosts=("arxiv.org",),
        max_redirects=5,
        connect_timeout=10,
        read_timeout=30,
        total_timeout=300,
        resolver=lambda host: ("93.184.216.34",),
        transport=transport or FakeResourceTransport(),
    )
    return ResourceWorker(
        repository=repository,
        blob_store=blob_store,
        worker_id="test_worker",
        lease_seconds=120,
        heartbeat_seconds=30,
        downloader=downloader,
        publisher=ResourcePublisher(blob_store=blob_store),
    )


class TestWorkerHappyPath:
    def test_pdf_published(
        self,
        repository: FakeResourceRepository,
        fake_blob_store: FakeBlobStore,
    ) -> None:
        # 使用真实可解析 PDF，确保 fitz 可用时 validator 通过。
        body = make_valid_pdf_bytes()
        sha = hashlib.sha256(body).hexdigest()
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/pdf/1234.5678": make_ok(
                    body, content_type="application/pdf"
                )
            }
        )
        worker = _make_worker(
            repository=repository,
            blob_store=fake_blob_store,
            transport=transport,
        )

        record, _ = repository.submit(
            resource_id="res_test1",
            idempotency_key="key1",
            request=_make_pdf_request(),
            request_sha256=resource_request_sha256(
                _make_pdf_request()
            ),
        )
        _approve(repository, record)

        assert worker.run_once() is True
        updated = repository.get(record.resource_id)
        assert updated.status == "published"
        assert updated.manifest is not None
        assert updated.manifest.sha256 == sha
        assert (
            updated.manifest.size_bytes
            == len(body)
        )

    def test_checkpoint_published(
        self,
        repository: FakeResourceRepository,
        fake_blob_store: FakeBlobStore,
    ) -> None:
        body = b"\x00\x01checkpoint data"
        sha = hashlib.sha256(body).hexdigest()
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/model.pt": make_ok(
                    body
                )
            }
        )
        worker = _make_worker(
            repository=repository,
            blob_store=fake_blob_store,
            transport=transport,
        )

        request = ResourceRequest(
            kind="checkpoint",
            source_url="https://arxiv.org/model.pt",
            purpose="weights",
            expected_sha256=sha,
        )
        record, _ = repository.submit(
            resource_id="res_ckpt1",
            idempotency_key="ckpt1",
            request=request,
            request_sha256=resource_request_sha256(
                request
            ),
        )
        _approve(repository, record)

        assert worker.run_once() is True
        updated = repository.get(record.resource_id)
        assert updated.status == "published"
        assert updated.manifest.sha256 == sha


class TestStaleApproval:
    def test_stale_approval_rejected(
        self,
        repository: FakeResourceRepository,
        fake_blob_store: FakeBlobStore,
    ) -> None:
        """修改 URL 后旧 approval 失效。"""

        transport = FakeResourceTransport({})
        worker = _make_worker(
            repository=repository,
            blob_store=fake_blob_store,
            transport=transport,
        )

        request = _make_pdf_request()
        record, _ = repository.submit(
            resource_id="res_stale1",
            idempotency_key="stale1",
            request=request,
            request_sha256=resource_request_sha256(
                request
            ),
        )
        _approve(repository, record)

        # 模拟修改 URL：直接替换 request（保持 request_sha256 不变会失败）。
        new_request = _make_pdf_request(
            url="https://arxiv.org/pdf/9999.9999"
        )
        stored = repository._store[record.resource_id]
        stored.record = stored.record.model_copy(
            update={"request": new_request}
        )
        # request_sha256 仍是旧值，approval 绑定旧 hash -> stale。

        assert worker.run_once() is True
        updated = repository.get(record.resource_id)
        assert updated.status == "failed_terminal"
        assert updated.error is not None
        # request hash mismatch -> integrity error
        assert (
            updated.error["category"] == "integrity"
        )


class TestErrorClassification:
    def test_5xx_retryable(
        self,
        repository: FakeResourceRepository,
        fake_blob_store: FakeBlobStore,
    ) -> None:
        from tests.fakes.fake_resource_transport import (
            FakeHeaders,
            FakeResponse,
        )

        transport = FakeResourceTransport(
            {
                "https://arxiv.org/pdf/1234.5678": FakeResponse(
                    503,
                    FakeHeaders({}),
                    (),
                )
            }
        )
        worker = _make_worker(
            repository=repository,
            blob_store=fake_blob_store,
            transport=transport,
        )

        request = _make_pdf_request()
        record, _ = repository.submit(
            resource_id="res_5xx",
            idempotency_key="5xx",
            request=request,
            request_sha256=resource_request_sha256(
                request
            ),
        )
        _approve(repository, record)

        assert worker.run_once() is True
        updated = repository.get(record.resource_id)
        assert updated.status == "failed_retryable"

    def test_4xx_terminal(
        self,
        repository: FakeResourceRepository,
        fake_blob_store: FakeBlobStore,
    ) -> None:
        from tests.fakes.fake_resource_transport import (
            FakeHeaders,
            FakeResponse,
        )

        transport = FakeResourceTransport(
            {
                "https://arxiv.org/pdf/1234.5678": FakeResponse(
                    404,
                    FakeHeaders({}),
                    (),
                )
            }
        )
        worker = _make_worker(
            repository=repository,
            blob_store=fake_blob_store,
            transport=transport,
        )

        request = _make_pdf_request()
        record, _ = repository.submit(
            resource_id="res_4xx",
            idempotency_key="4xx",
            request=request,
            request_sha256=resource_request_sha256(
                request
            ),
        )
        _approve(repository, record)

        assert worker.run_once() is True
        updated = repository.get(record.resource_id)
        assert updated.status == "failed_terminal"

    def test_sha_mismatch_terminal(
        self,
        repository: FakeResourceRepository,
        fake_blob_store: FakeBlobStore,
    ) -> None:
        body = b"%PDF-1.4 content"
        transport = FakeResourceTransport(
            {
                "https://arxiv.org/pdf/1234.5678": make_ok(
                    body
                )
            }
        )
        worker = _make_worker(
            repository=repository,
            blob_store=fake_blob_store,
            transport=transport,
        )

        request = ResourceRequest(
            kind="paper_pdf",
            source_url="https://arxiv.org/pdf/1234.5678",
            purpose="paper",
            expected_sha256="0" * 64,
        )
        record, _ = repository.submit(
            resource_id="res_sha",
            idempotency_key="sha",
            request=request,
            request_sha256=resource_request_sha256(
                request
            ),
        )
        _approve(repository, record)

        assert worker.run_once() is True
        updated = repository.get(record.resource_id)
        assert updated.status == "failed_terminal"
        assert (
            updated.error["category"] == "integrity"
        )


class TestNoWork:
    def test_no_queued_returns_false(
        self,
        repository: FakeResourceRepository,
        fake_blob_store: FakeBlobStore,
    ) -> None:
        worker = _make_worker(
            repository=repository,
            blob_store=fake_blob_store,
        )
        assert worker.run_once() is False


class TestIdempotency:
    def test_same_idempotency_same_request(
        self,
        repository: FakeResourceRepository,
    ) -> None:
        request = _make_pdf_request()
        sha = resource_request_sha256(request)
        r1, created1 = repository.submit(
            resource_id="res_idem1",
            idempotency_key="same_key",
            request=request,
            request_sha256=sha,
        )
        r2, created2 = repository.submit(
            resource_id="res_idem2",
            idempotency_key="same_key",
            request=request,
            request_sha256=sha,
        )
        assert created1 is True
        assert created2 is False
        assert r1.resource_id == r2.resource_id

    def test_same_idempotency_different_request_conflict(
        self,
        repository: FakeResourceRepository,
    ) -> None:
        from app.resources.errors import (
            ResourceConflictError,
        )

        r1 = _make_pdf_request()
        r2 = _make_pdf_request(
            url="https://arxiv.org/pdf/9999.9999"
        )
        sha1 = resource_request_sha256(r1)
        sha2 = resource_request_sha256(r2)
        repository.submit(
            resource_id="res_conf1",
            idempotency_key="conf_key",
            request=r1,
            request_sha256=sha1,
        )
        with pytest.raises(ResourceConflictError):
            repository.submit(
                resource_id="res_conf2",
                idempotency_key="conf_key",
                request=r2,
                request_sha256=sha2,
            )
