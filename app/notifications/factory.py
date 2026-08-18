from __future__ import annotations

from app.config import settings
from app.job_runtime.service import JobService
from app.notifications.projector import NotificationProjector
from app.notifications.repository import (
    SqliteNotificationRepository,
)
from app.notifications.service import NotificationService


def build_notification_service(
    *,
    jobs: JobService,
) -> NotificationService:
    """Phase 44 单机 Composition Root。"""

    repository = SqliteNotificationRepository(
        settings.notification_db_path
    )
    repository.initialize()
    projector = NotificationProjector(
        jobs=jobs,
        repository=repository,
        batch_size=(
            settings.notification_projection_batch_size
        ),
    )
    return NotificationService(
        jobs=jobs,
        repository=repository,
        projector=projector,
        max_sync_batches=(
            settings.notification_projection_max_batches
        ),
    )
