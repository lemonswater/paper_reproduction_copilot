"""Phase 29 Resource Worker（Acquisition Worker）。

网络权限只属于本 Worker；论文执行容器保持 ``network=none``。

主流程：
1. claim_next 获取一个 queued resource（带不可变 claim_token）。
2. _assert_current_approval 校验 approval 绑定当前 request hash。
3. heartbeat 周期续租；下载/验证/发布每步都带 fencing。
4. 失败分类：transport 可重试，policy/integrity/limit 默认 terminal。
5. lease loss 时旧 Worker 不写终态，由 reconciler 处理。

Phase 28 telemetry 接入点：resource.claim/fetch/validate/publish spans；
metrics labels 只放 kind/outcome/error_category，不放 resource_id 或 URL。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.observability.context import (
    bind_telemetry_context,
)
from app.observability.instrumentation import (
    increment_counter_safe,
)
from app.observability.ports import TelemetryPort
from app.observability.runtime import (
    build_telemetry_runtime,
)
from app.resources.errors import (
    ResourceError,
    ResourceIntegrityError,
    ResourceLeaseLost,
    ResourcePolicyViolation,
    ResourceStateAmbiguous,
    ResourceTransportUnavailable,
    is_retryable_resource_error,
)
from app.resources.git_fetcher import (
    GitResourceFetcher,
    resource_staging_dir,
)
from app.resources.http_downloader import (
    HttpResourceDownloader,
)
from app.resources.ports import ResourceRepository
from app.resources.publisher import ResourcePublisher
from app.resources.request_hash import (
    resource_request_sha256,
)
from app.resources.schemas import (
    ResourceManifest,
    ResourceRecord,
)
from app.resources.validators import validate_for_kind
from app.storage.ports import BlobStore


@dataclass
class StagedResource:
    """下载/获取完成后的本地 staging 产物。"""

    source_path: Path
    sha256: str
    size_bytes: int
    media_type: str
    redirect_chain: list[str]
    git_commit: str | None = None


class HeartbeatGuard:
    """周期续租 + cancel/lease-loss 检测。

    ``raise_if_unhealthy`` 在下载循环中被调用，lease 失效时抛
    ResourceLeaseLost，旧 Worker 立即停止写入并不 publish。
    """

    def __init__(
        self,
        *,
        repository: ResourceRepository,
        resource_id: str,
        claim_token: str,
        lease_seconds: float,
        heartbeat_seconds: float,
        stop_event: threading.Event,
    ):
        self.repository = repository
        self.resource_id = resource_id
        self.claim_token = claim_token
        self.lease_seconds = lease_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.stop_event = stop_event
        self._thread: threading.Thread | None = None
        self._healthy = True
        self._failure: BaseException | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._loop,
            name="resource-heartbeat",
            daemon=True,
        )
        self._thread.start()

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.repository.heartbeat(
                    resource_id=self.resource_id,
                    claim_token=self.claim_token,
                    lease_seconds=self.lease_seconds,
                )
            except ResourceStateAmbiguous as exc:
                self._failure = exc
                self._healthy = False
                self.stop_event.set()
                return
            except Exception:
                # 瞬时 DB 错误不立即放弃；下次 heartbeat 再试。
                pass
            self.stop_event.wait(self.heartbeat_seconds)

    def raise_if_unhealthy(self) -> None:
        if not self._healthy and self._failure is not None:
            raise ResourceLeaseLost(
                "resource lease 已失效"
            ) from self._failure

    def stop(self) -> None:
        self.stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)


def _error_payload(exc: BaseException) -> dict[str, Any]:
    """错误分类，复用 Phase 15 统一错误模型思路。"""

    if isinstance(exc, ResourcePolicyViolation):
        category = "policy_violation"
    elif isinstance(exc, ResourceIntegrityError):
        category = "integrity"
    elif isinstance(exc, ResourceTransportUnavailable):
        category = "transport_unavailable"
    elif isinstance(exc, ResourceLeaseLost):
        category = "lease_lost"
    else:
        category = "internal"
    return {
        "category": category,
        "message": str(exc)[:500],
        "type": type(exc).__name__,
    }


class ResourceWorker:
    """Acquisition Worker：受控联网获取，执行容器保持断网。"""

    def __init__(
        self,
        *,
        repository: ResourceRepository,
        blob_store: BlobStore,
        worker_id: str,
        lease_seconds: float | None = None,
        heartbeat_seconds: float | None = None,
        telemetry: TelemetryPort | None = None,
        downloader: HttpResourceDownloader | None = None,
        git_fetcher: GitResourceFetcher | None = None,
        publisher: ResourcePublisher | None = None,
    ):
        self.repository = repository
        self.blob_store = blob_store
        self.worker_id = worker_id
        self.lease_seconds = (
            lease_seconds
            if lease_seconds is not None
            else settings.resource_lease_seconds
        )
        self.heartbeat_seconds = (
            heartbeat_seconds
            if heartbeat_seconds is not None
            else settings.resource_heartbeat_seconds
        )
        self.telemetry = (
            telemetry
            if telemetry is not None
            else build_telemetry_runtime().telemetry
        )
        self.downloader = downloader or HttpResourceDownloader(
            allowed_hosts=settings.resource_allowed_hosts,
            max_redirects=settings.resource_max_redirects,
            connect_timeout=(
                settings.resource_connect_timeout_seconds
            ),
            read_timeout=settings.resource_read_timeout_seconds,
            total_timeout=(
                settings.resource_total_timeout_seconds
            ),
        )
        self.git_fetcher = git_fetcher or GitResourceFetcher(
            allowed_hosts=settings.resource_allowed_hosts,
            timeout_seconds=(
                settings.resource_git_timeout_seconds
            ),
        )
        self.publisher = publisher or ResourcePublisher(
            blob_store=self.blob_store
        )

    def run_once(self) -> bool:
        record = self.repository.claim_next(
            worker_id=self.worker_id,
            lease_seconds=self.lease_seconds,
        )
        if record is None:
            return False
        claim_token = record.claim_token
        if claim_token is None:
            raise RuntimeError(
                "claimed resource 缺少 claim token"
            )

        with bind_telemetry_context(
            resource_id=record.resource_id
        ):
            return self._process(record, claim_token)

    def run_forever(
        self,
        *,
        stop_event: threading.Event | None = None,
        poll_seconds: float = 1.0,
    ) -> None:
        """持续轮询 queued resource，直到 stop_event 被设置。

        ``run_once`` 自行把单个 Resource 的业务异常写回状态，
        因此这里不会因为一次下载失败退出整个 Worker。
        真正的初始化错误仍会从 factory 抛出，让 serve-stack 启动失败。
        """

        stop = stop_event or threading.Event()
        while not stop.is_set():
            handled = self.run_once()
            if not handled:
                # Event.wait 可在 shutdown 时立即醒来，
                # 比 time.sleep 更容易停止。
                stop.wait(poll_seconds)

    def _process(
        self,
        record: ResourceRecord,
        claim_token: str,
    ) -> bool:
        stop_event = threading.Event()
        guard = HeartbeatGuard(
            repository=self.repository,
            resource_id=record.resource_id,
            claim_token=claim_token,
            lease_seconds=self.lease_seconds,
            heartbeat_seconds=self.heartbeat_seconds,
            stop_event=stop_event,
        )
        try:
            self._assert_current_approval(record)
            guard.start()
            with self.telemetry.span(
                "resource.fetch",
                attributes={"kind": record.request.kind},
            ):
                staged = self._fetch(
                    record, claim_token, guard.raise_if_unhealthy
                )
            guard.raise_if_unhealthy()
            self.repository.mark_validating(
                resource_id=record.resource_id,
                claim_token=claim_token,
            )
            with self.telemetry.span(
                "resource.validate",
                attributes={"kind": record.request.kind},
            ):
                media_type = self._validate(staged, record)
            guard.raise_if_unhealthy()
            with self.telemetry.span(
                "resource.publish",
                attributes={"kind": record.request.kind},
            ):
                manifest = self._publish(
                    record, staged, media_type
                )
            guard.raise_if_unhealthy()
            self.repository.mark_published(
                resource_id=record.resource_id,
                claim_token=claim_token,
                manifest=manifest,
            )
            increment_counter_safe(
                self.telemetry,
                "paper_copilot_resources_acquired_total",
                attributes={
                    "kind": record.request.kind,
                    "outcome": "published",
                },
            )
        except ResourceLeaseLost:
            # 旧 Worker 不写终态；reconciler 根据 staging/blob 处理。
            increment_counter_safe(
                self.telemetry,
                "paper_copilot_resources_acquired_total",
                attributes={
                    "kind": record.request.kind,
                    "outcome": "lease_lost",
                },
            )
        except ResourceError as exc:
            self._mark_failed(
                record, claim_token, exc
            )
        except Exception as exc:
            # 未分类错误默认 terminal，避免无限重试。
            self._mark_failed(
                record,
                claim_token,
                exc,
            )
        finally:
            stop_event.set()
            guard.stop()
            self._cleanup_safe_staging(record, claim_token)
        return True

    def _assert_current_approval(
        self, record: ResourceRecord
    ) -> None:
        approval = record.approval
        if approval is None or approval.decision != "approved":
            raise ResourcePolicyViolation(
                "resource 没有 approved decision"
            )
        current_hash = resource_request_sha256(
            record.request
        )
        if current_hash != record.request_sha256:
            raise ResourceIntegrityError(
                "persisted request hash mismatch"
            )
        if approval.request_sha256 != current_hash:
            raise ResourcePolicyViolation(
                "stale resource approval"
            )

    def _fetch(
        self,
        record: ResourceRecord,
        claim_token: str,
        ensure_active,
    ) -> StagedResource:
        request = record.request
        staging_dir = resource_staging_dir(
            record.resource_id,
            claim_token,
        )
        staging_dir.mkdir(parents=True, exist_ok=True)

        if request.kind == "git_repository":
            assert request.expected_git_commit is not None
            result = self.git_fetcher.fetch(
                source_url=request.source_url,
                expected_commit=request.expected_git_commit,
                staging_dir=staging_dir,
            )
            return StagedResource(
                source_path=result.bundle_path,
                sha256=result.bundle_sha256,
                size_bytes=result.bundle_size_bytes,
                media_type="application/octet-stream",
                redirect_chain=[],
                git_commit=result.commit_sha,
            )

        max_bytes = self._max_bytes_for(request.kind)
        destination = staging_dir / "download.part"
        result = self.downloader.download(
            url=request.source_url,
            destination=destination,
            max_bytes=max_bytes,
            expected_sha256=request.expected_sha256,
            ensure_active=ensure_active,
        )
        return StagedResource(
            source_path=result.path,
            sha256=result.sha256,
            size_bytes=result.size_bytes,
            media_type=result.media_type,
            redirect_chain=list(result.redirect_chain),
            git_commit=None,
        )

    def _max_bytes_for(self, kind: str) -> int:
        if kind == "paper_pdf":
            return settings.resource_pdf_max_bytes
        if kind == "checkpoint":
            return settings.resource_checkpoint_max_bytes
        raise ResourcePolicyViolation(
            f"未知 resource kind：{kind}"
        )

    def _validate(
        self,
        staged: StagedResource,
        record: ResourceRecord,
    ) -> str:
        # checkpoint 在下载前已要求 expected_sha256；下载阶段已校验 hash。
        # 这里只做 type-specific 结构校验（PDF magic/parser，opaque blob）。
        media_type = validate_for_kind(
            staged.source_path, record.request.kind
        )
        if (
            record.request.expected_sha256 is not None
            and staged.sha256
            != record.request.expected_sha256
        ):
            raise ResourceIntegrityError(
                "staged SHA-256 与 expected 不一致"
            )
        return media_type

    def _publish(
        self,
        record: ResourceRecord,
        staged: StagedResource,
        media_type: str,
    ) -> ResourceManifest:
        return self.publisher.publish_file(
            resource_id=record.resource_id,
            kind=record.request.kind,
            source_url=record.request.source_url,
            redirect_chain=staged.redirect_chain,
            source=staged.source_path,
            sha256=staged.sha256,
            size_bytes=staged.size_bytes,
            media_type=media_type,
            git_commit=staged.git_commit,
        )

    def _mark_failed(
        self,
        record: ResourceRecord,
        claim_token: str,
        exc: BaseException,
    ) -> None:
        payload = _error_payload(exc)
        retryable = is_retryable_resource_error(exc)
        try:
            self.repository.mark_failed(
                resource_id=record.resource_id,
                claim_token=claim_token,
                error=payload,
                retryable=retryable,
            )
        except ResourceStateAmbiguous:
            # lease 已被回收，不能写终态；reconciler 接管。
            pass
        increment_counter_safe(
            self.telemetry,
            "paper_copilot_resources_acquired_total",
            attributes={
                "kind": record.request.kind,
                "outcome": "failed",
                "error_category": payload["category"],
            },
        )

    def _cleanup_safe_staging(
        self,
        record: ResourceRecord,
        claim_token: str,
    ) -> None:
        """清理本次 attempt 的 staging 目录。

        清理前先确认路径位于 ``RESOURCE_STAGING_ROOT/<resource_id>/<claim_hash>``，
        不能 glob 删除整个 resources/。
        """

        import shutil

        try:
            staging_dir = resource_staging_dir(
                record.resource_id,
                claim_token,
            )
        except Exception:
            return
        root = settings.resource_staging_root.resolve()
        if staging_dir != root and root in staging_dir.parents:
            shutil.rmtree(staging_dir, ignore_errors=True)


def build_resource_worker(
    *,
    worker_id: str | None = None,
    repository: ResourceRepository | None = None,
    blob_store: BlobStore | None = None,
) -> ResourceWorker:
    """CLI/Worker composition root。"""

    from app.storage.factory import (
        build_artifact_storage,
    )

    if repository is None:
        from app.resources.repository import (
            build_resource_repository,
        )

        repository = build_resource_repository()
    if blob_store is None:
        storage = build_artifact_storage()
        blob_store = storage.selected_store
    effective_worker_id = (
        worker_id
        or f"resource_worker_{settings.worker_host_id}"
    )
    return ResourceWorker(
        repository=repository,
        blob_store=blob_store,
        worker_id=effective_worker_id,
    )
