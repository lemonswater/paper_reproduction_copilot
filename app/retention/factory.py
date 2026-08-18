"""Retention Factory 与 Backend Fail-Closed."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from app.chat.store import SqliteChatRepository
from app.config import settings
from app.failure_memory.repository import (
    SqliteFailureCaseRepository,
)
from app.memory.checkpoint import build_checkpointer
from app.notifications.repository import (
    SqliteNotificationRepository,
)
from app.resources.repository import SqliteResourceRepository
from app.retention.checkpoint_adapter import (
    LangGraphCheckpointRetentionAdapter,
)
from app.retention.inventory import InventoryConfig, StorageInventoryService
from app.retention.lock import SingleHostSweepLock
from app.retention.paths import SafePathRemover
from app.retention.repository import SqliteRetentionRepository
from app.retention.schemas import RetentionPolicy
from app.retention.service import (
    RetentionService,
    StorageQuotaGuard,
)
from app.storage.factory import ArtifactStorageBundle
from app.storage.local_blob_store import LocalBlobStore

class NoOpChatRetentionPort:
    def delete_job_messages(self, job_id: str) -> int:
        del job_id
        return 0


class NoOpFailureMemoryRetentionPort:
    def active_referenced_job_ids(self) -> set[str]:
        return set()


class NoOpProjectMemoryRetentionPort:
    def active_referenced_job_ids(self) -> set[str]:
        return set()


class NoOpKnowledgeMemoryRetentionPort:
    def active_referenced_job_ids(self) -> set[str]:
        return set()


class NoOpMcpEvidenceRetentionPort:
    def delete_for_job(self, job_id: str) -> int:
        del job_id
        return 0


class NoOpMcpExportAuditRetentionPort:
    def delete_for_job(self, job_id: str) -> int:
        del job_id
        return 0

def _sqlite_roots(name: str, path: Path) -> list[tuple[str, Path]]:
    return [
        (name, path),
        (f"{name}_wal", Path(f"{path}-wal")),
        (f"{name}_shm", Path(f"{path}-shm")),
    ]

def build_inventory(*, destructive_supported: bool) -> StorageInventoryService:
    roots: list[tuple[str, Path]] = [
        ("runs", settings.runs_dir.resolve()),
        ("worker_workspaces", settings.worker_workspace_root.resolve()),
        ("workspace_staging", settings.workspace_staging_root.resolve()),
        ("export_staging", settings.job_export_staging_root.resolve()),
        ("artifact_blobs", settings.artifact_local_store_dir.resolve()),
        # Phase 38：只做容量盘点，不加入 RetentionService 的删除端口。
        ("comparisons", settings.comparison_root.resolve()),
    ]
    for name, path in (
        ("job_db", settings.job_db_path.resolve()),
        ("checkpoint_db", settings.checkpoint_db_path.resolve()),
        ("artifact_db", settings.artifact_catalog_db_path.resolve()),
        ("resource_db", settings.resource_db_path.resolve()),
        ("chat_db", settings.chat_db_path.resolve()),
        ("retention_db", settings.retention_db_path.resolve()),
        ("rerun_db", settings.rerun_db_path.resolve()),
        ("notification_db", settings.notification_db_path.resolve()),
        ("failure_memory_db", settings.failure_memory_db_path.resolve()),
    ):
        roots.extend(_sqlite_roots(name, path))
    if settings.project_memory_enabled:
        roots.extend(
            _sqlite_roots(
                "project_memory_db",
                settings.project_memory_db_path.resolve(),
            )
        )
    roots.extend(
        _sqlite_roots(
            "knowledge_db",
            settings.knowledge_db_path.resolve(),
        )
    )
    roots.extend(
        _sqlite_roots(
            "mcp_gateway_db",
            settings.mcp_gateway_db_path.resolve(),
        )
    )
    roots.extend(
        _sqlite_roots(
            "mcp_export_audit_db",
            settings.mcp_export_audit_db_path.resolve(),
        )
    )

    return StorageInventoryService(
        InventoryConfig(
            roots=tuple(roots),
            filesystem_anchor=settings.runs_dir.resolve(),
            soft_limit_bytes=settings.storage_soft_limit_bytes,
            hard_limit_bytes=settings.storage_hard_limit_bytes,
            min_free_bytes=settings.storage_min_free_bytes,
            max_warnings=settings.storage_inventory_max_warnings,
            destructive_gc_supported=destructive_supported,
        )
    )

@dataclass(frozen=True)
class RetentionBundle:
    inventory: StorageInventoryService
    quota_guard: StorageQuotaGuard
    service: RetentionService | None

def _build_mcp_evidence_retention():
    if settings.mcp_gateway_enabled or settings.mcp_gateway_db_path.exists():
        from app.mcp_gateway.repository import SqliteMcpEvidenceRepository

        repository = SqliteMcpEvidenceRepository(
            settings.mcp_gateway_db_path
        )
        repository.initialize()
        return repository
    return NoOpMcpEvidenceRetentionPort()


def _build_mcp_export_audit_retention():
    path = settings.mcp_export_audit_db_path
    if settings.mcp_export_enabled or path.exists():
        from app.mcp_export.audit import (
            SqliteMcpExportAuditRepository,
        )

        repository = SqliteMcpExportAuditRepository(path)
        repository.initialize()
        return repository
    return NoOpMcpExportAuditRetentionPort()


def build_retention(
    *,
    job_store,
    artifact_storage: ArtifactStorageBundle,
    project_memory_repository=None,
    knowledge_repository=None,
) -> RetentionBundle:
    destructive_supported = (
        settings.retention_enabled
        and settings.job_store_backend == "sqlite"
        and settings.checkpoint_backend == "sqlite"
        and settings.artifact_blob_backend == "local"
    )
    inventory = build_inventory(destructive_supported=destructive_supported)

    quota_guard = StorageQuotaGuard(inventory)
    if not destructive_supported:
        return RetentionBundle(
            inventory=inventory,
            quota_guard=quota_guard,
            service=None,
        )

    if not isinstance(artifact_storage.selected_store, LocalBlobStore):
        raise RuntimeError("Local backend 与 concrete BlobStore 不一致")
    deletable = artifact_storage.selected_store
    chat = (
        SqliteChatRepository(settings.chat_db_path)
        if settings.chat_enabled or settings.chat_db_path.exists()
        else NoOpChatRetentionPort()
    )
    if isinstance(chat, SqliteChatRepository):
        chat.initialize()

    resource_repository = SqliteResourceRepository(settings.resource_db_path)
    resource_repository.initialize()
    notification_repository = SqliteNotificationRepository(
        settings.notification_db_path
    )
    notification_repository.initialize()
    repository = SqliteRetentionRepository(settings.retention_db_path)
    failure_memory_repository = SqliteFailureCaseRepository(
        settings.failure_memory_db_path
    )
    failure_memory_repository.initialize()
    selected_knowledge_repository = knowledge_repository
    if (
        selected_knowledge_repository is None
        and settings.knowledge_db_path.exists()
    ):
        from app.knowledge_base.repository import (
            SqliteKnowledgeRepository,
        )

        selected_knowledge_repository = SqliteKnowledgeRepository(
            settings.knowledge_db_path
        )
        selected_knowledge_repository.initialize()
    service = RetentionService(
        policy=RetentionPolicy(
            job_retention_seconds=settings.retention_job_days * 86400,
            max_jobs_per_plan=settings.retention_plan_max_jobs,
            plan_ttl_seconds=settings.retention_plan_ttl_seconds,
            delete_local_blobs=settings.retention_local_blob_delete_enabled,
        ),
        repository=repository,
        jobs=job_store,
        artifacts=artifact_storage.repository,
        chats=chat,
        notifications=notification_repository,
        resources=resource_repository,
        checkpoints=LangGraphCheckpointRetentionAdapter(build_checkpointer()),
        blob_store=deletable,
        path_remover=SafePathRemover(
            runs_root=settings.runs_dir,
            worker_root=settings.worker_workspace_root,
        ),
        inventory=inventory,
        selected_blob_backend=artifact_storage.selected_store.backend_name,
        destructive_supported=destructive_supported,
        sweep_lock=SingleHostSweepLock(
            settings.retention_db_path.with_suffix(".gc.lock")
        ),
        failure_memory=failure_memory_repository,
        project_memory=(
            project_memory_repository
            if project_memory_repository is not None
            else NoOpProjectMemoryRetentionPort()
        ),
        knowledge_memory=(
            selected_knowledge_repository
            if selected_knowledge_repository is not None
            else NoOpKnowledgeMemoryRetentionPort()
        ),
        mcp_evidence=_build_mcp_evidence_retention(),
        mcp_export_audit=_build_mcp_export_audit_retention(),
    )
    return RetentionBundle(
        inventory=inventory,
        quota_guard=quota_guard,
        service=service,
    )