"""Phase 29 崩溃恢复（reconcile）。

恢复规则联合 record、staging、blob 事实，而不是仅修改状态字段：

| 持久状态 | staging/blob 事实 | 处理 |
|---|---|---|
| fetching | 无 part，无活动进程 | 可安全 requeue |
| fetching | part 存在，下载进程不明确 | reconciliation_required |
| validating | part hash 正确 | 从验证继续，不重新联网 |
| validating | part hash 错误 | 删除 part，terminal integrity failure |
| published 前崩溃 | blob 已存在且 hash/size 匹配 | 恢复 manifest/DB commit |
| published | manifest/blob 匹配 | 正常终态 |
| 任意 | claim ownership 不匹配 | 旧 Worker 不得写入/清理 |

不要使用进程名或 URL 查找旧下载；为每个 attempt 持久化 staging 路径。
清理前先确认路径位于 ``RESOURCE_STAGING_ROOT/<resource_id>/<claim_hash>``。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.config import settings
from app.resources.errors import ResourceStateAmbiguous
from app.resources.ports import ResourceRepository
from app.resources.publisher import (
    ResourcePublisher,
    resource_object_key,
)
from app.resources.schemas import ResourceRecord
from app.storage.ports import BlobStore


ReconcileDisposition = Literal[
    "safe_to_requeue",
    "reconciliation_required",
    "terminal_integrity_failure",
    "publication_recovered",
    "already_published",
    "ownership_mismatch",
]


@dataclass
class ReconcileResult:
    disposition: ReconcileDisposition
    resource_id: str
    detail: str
    record: ResourceRecord | None = None


class ResourceReconciler:
    """扫描 expired fetching resource 并按事实恢复。"""

    def __init__(
        self,
        *,
        repository: ResourceRepository,
        blob_store: BlobStore,
        publisher: ResourcePublisher | None = None,
    ):
        self.repository = repository
        self.blob_store = blob_store
        self.publisher = publisher or ResourcePublisher(
            blob_store=blob_store
        )

    def reconcile_expired(self, *, limit: int = 100) -> list[ReconcileResult]:
        expired = self.repository.list_expired_fetching(
            limit=limit
        )
        results: list[ReconcileResult] = []
        for record in expired:
            # 旧 claim_token 未持久化明文；requeue/require_reconciliation
            # 需要一个与原 claim 匹配的 token。第一版使用 record 的
            # worker_id + resource_id 派生确定性 placeholder，仅用于
            # fencing 比对——由于 DB 存的是 hash，不匹配会抛 ambiguous。
            # 实际生产应持久化 claim_token_hash 并由 reconciler 持有。
            placeholder_token = (
                f"expired:{record.resource_id}:{record.worker_id or 'unknown'}"
            )
            results.append(
                self._reconcile_one(record, placeholder_token)
            )
        return results

    def _reconcile_one(
        self,
        record: ResourceRecord,
        expired_claim_token: str,
    ) -> ReconcileResult:
        staging_root = settings.resource_staging_root.resolve()
        # 扫描该 resource 的所有 attempt staging 目录。
        resource_staging = (
            staging_root / Path(record.resource_id).name
        )
        has_part = False
        if resource_staging.is_dir():
            for attempt_dir in resource_staging.iterdir():
                if attempt_dir.is_dir() and any(
                    attempt_dir.iterdir()
                ):
                    has_part = True
                    break

        if not has_part:
            # 无 part 文件，可安全 requeue。
            try:
                updated = self.repository.requeue_expired(
                    resource_id=record.resource_id,
                    expired_claim_token=expired_claim_token,
                    detail="lease expired, no staging part",
                )
                return ReconcileResult(
                    disposition="safe_to_requeue",
                    resource_id=record.resource_id,
                    detail="lease expired, no staging part",
                    record=updated,
                )
            except ResourceStateAmbiguous:
                return ReconcileResult(
                    disposition="ownership_mismatch",
                    resource_id=record.resource_id,
                    detail="requeue fencing 失败",
                )

        # part 存在但下载进程不明确 -> reconciliation_required。
        try:
            updated = self.repository.require_reconciliation(
                resource_id=record.resource_id,
                expired_claim_token=expired_claim_token,
                detail=(
                    "staging part exists, download process ambiguous"
                ),
            )
            return ReconcileResult(
                disposition="reconciliation_required",
                resource_id=record.resource_id,
                detail=(
                    "staging part exists, download process ambiguous"
                ),
                record=updated,
            )
        except ResourceStateAmbiguous:
            return ReconcileResult(
                disposition="ownership_mismatch",
                resource_id=record.resource_id,
                detail="require_reconciliation fencing 失败",
            )

    def recover_publication(
        self,
        *,
        resource_id: str,
        sha256: str,
        size_bytes: int,
    ) -> ReconcileResult:
        """blob 已写但 DB 未提交时，根据 blob 事实恢复 publication。

        不重新联网；只校验 blob stat 与 expected hash/size。
        """

        key = resource_object_key(sha256)
        stat = self.blob_store.stat(key)
        if stat is None:
            return ReconcileResult(
                disposition="terminal_integrity_failure",
                resource_id=resource_id,
                detail="blob 不存在，无法恢复 publication",
            )
        if stat.sha256 != sha256 or stat.size_bytes != size_bytes:
            return ReconcileResult(
                disposition="terminal_integrity_failure",
                resource_id=resource_id,
                detail="blob hash/size 与 expected 不一致",
            )
        # blob 已存在且匹配；caller（Worker/手动）应据此重建 manifest。
        return ReconcileResult(
            disposition="publication_recovered",
            resource_id=resource_id,
            detail="blob 存在且 hash/size 匹配，可恢复 manifest",
        )

    def verify_published(
        self,
        *,
        record: ResourceRecord,
    ) -> ReconcileResult:
        """published 状态：校验 manifest 与 blob 一致。"""

        if record.status != "published" or record.manifest is None:
            return ReconcileResult(
                disposition="ownership_mismatch",
                resource_id=record.resource_id,
                detail="resource 非 published 或无 manifest",
            )
        manifest = record.manifest
        stat = self.blob_store.stat(manifest.object_key)
        if stat is None:
            return ReconcileResult(
                disposition="terminal_integrity_failure",
                resource_id=record.resource_id,
                detail="published resource 的 blob 不存在",
            )
        if (
            stat.sha256 != manifest.sha256
            or stat.size_bytes != manifest.size_bytes
        ):
            return ReconcileResult(
                disposition="terminal_integrity_failure",
                resource_id=record.resource_id,
                detail="published blob hash/size 与 manifest 不一致",
            )
        return ReconcileResult(
            disposition="already_published",
            resource_id=record.resource_id,
            detail="manifest 与 blob 一致",
            record=record,
        )
