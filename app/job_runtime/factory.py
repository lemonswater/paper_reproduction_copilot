from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.config import settings
from app.job_runtime.ports import JobStore

if TYPE_CHECKING:
    from app.job_runtime.service import JobService


def build_job_store() -> JobStore:
    """唯一 JobStore composition root。"""

    if settings.job_store_backend == "sqlite":
        from app.job_runtime.store import (
            SqliteJobStore,
        )

        store: JobStore = SqliteJobStore(
            settings.job_db_path
        )
    elif settings.job_store_backend == "postgresql":
        from app.job_runtime.postgres_store import (
            PostgresJobStore,
        )

        store = PostgresJobStore()
    else:
        raise ValueError(
            "不支持的 JOB_STORE_BACKEND："
            f"{settings.job_store_backend}"
        )

    store.initialize()
    return store

class CapacityGuard(Protocol):
    def assert_can_submit(self) -> None: ...


def build_job_service() -> JobService:
    """CLI、API 和 Worker 共用 Store/Blob/Quota 配置。"""
    from app.workspace.snapshot import WorkspaceSnapshotter

    from app.retention.factory import build_inventory
    from app.retention.service import StorageQuotaGuard
    from app.storage.factory import build_artifact_storage

    storage = build_artifact_storage()
    store = build_job_store()
    inventory = build_inventory(
        destructive_supported=(
            settings.retention_enabled
            and settings.job_store_backend == "sqlite"
            and settings.checkpoint_backend == "sqlite"
            and settings.artifact_blob_backend == "local"
        )
    )
    from app.job_runtime.service import JobService

    return JobService(
        store,
        workspace_snapshotter=WorkspaceSnapshotter(
            blob_store=storage.selected_store
        ),
        capacity_guard=(
            StorageQuotaGuard(inventory)
            if settings.retention_enabled
            else None
        ),
    )
