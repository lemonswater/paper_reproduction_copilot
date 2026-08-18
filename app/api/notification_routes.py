from __future__ import annotations

import asyncio
import json
import time
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
    Request,
)
from fastapi.responses import StreamingResponse

from app.api.auth import require_api_auth
from app.config import settings
from app.notifications.schemas import (
    MarkNotificationReadRequest,
    MarkNotificationsReadRequest,
    MarkNotificationsReadResponse,
    NotificationPage,
    NotificationUnreadCount,
    NotificationView,
)
from app.notifications.service import NotificationService


router = APIRouter(prefix="/v1/notifications")

Actor = Annotated[str, Depends(require_api_auth)]
AfterQuery = Annotated[int, Query(ge=0)]
LimitQuery = Annotated[int, Query(ge=1)]
UnreadOnlyQuery = Annotated[bool, Query()]
FollowQuery = Annotated[bool, Query()]
LastEventIdHeader = Annotated[
    Optional[int],
    Header(alias="Last-Event-ID", ge=0),
]


def notification_service(
    request: Request,
) -> NotificationService:
    return request.app.state.notification_service


NotificationDependency = Annotated[
    NotificationService,
    Depends(notification_service),
]


def _sse(notification: NotificationView) -> str:
    payload = json.dumps(
        notification.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        f"id: {notification.notification_seq}\n"
        "event: notification\n"
        f"data: {payload}\n\n"
    )


@router.get("", response_model=NotificationPage)
def list_notifications(
    _actor: Actor,
    service: NotificationDependency,
    after: AfterQuery = 0,
    unread_only: UnreadOnlyQuery = False,
    limit: LimitQuery = 100,
) -> NotificationPage:
    return service.list_notifications(
        after_sequence=after,
        unread_only=unread_only,
        limit=min(limit, settings.api_max_page_size),
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCount,
)
def unread_count(
    _actor: Actor,
    service: NotificationDependency,
) -> NotificationUnreadCount:
    return service.unread_count()


# 固定路径必须定义在 /{notification_id}/read 之前。
@router.post(
    "/read-all",
    response_model=MarkNotificationsReadResponse,
)
def mark_all_read(
    body: MarkNotificationsReadRequest,
    _actor: Actor,
    service: NotificationDependency,
) -> MarkNotificationsReadResponse:
    return service.mark_all_read(
        through_sequence=body.through_sequence
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationView,
)
def mark_read(
    notification_id: str,
    body: MarkNotificationReadRequest,
    _actor: Actor,
    service: NotificationDependency,
) -> NotificationView:
    return service.mark_read(
        notification_id=notification_id,
        expected_version=(
            body.expected_notification_version
        ),
    )


@router.get("/stream")
async def stream_notifications(
    request: Request,
    _actor: Actor,
    service: NotificationDependency,
    after: AfterQuery = 0,
    last_event_id: LastEventIdHeader = None,
    follow: FollowQuery = True,
) -> StreamingResponse:
    """SSE id 使用 notification_seq；follow=false 便于测试 backlog。"""

    # 在响应头发送前检查 Repository 和 Job Event 源。
    await asyncio.to_thread(service.sync)

    async def generate():
        cursor = max(after, last_event_id or 0)
        last_heartbeat = time.monotonic()

        while True:
            page = await asyncio.to_thread(
                service.list_notifications,
                after_sequence=cursor,
                unread_only=False,
                limit=settings.api_max_page_size,
            )
            for item in page.items:
                cursor = item.notification_seq
                yield _sse(item)

            if not follow:
                return
            if await request.is_disconnected():
                return

            now = time.monotonic()
            if (
                now - last_heartbeat
                >= settings.api_sse_heartbeat_seconds
            ):
                # 只是连接 keep-alive，不是 Job heartbeat。
                yield ": keep-alive\n\n"
                last_heartbeat = now

            await asyncio.sleep(
                settings.api_event_poll_seconds
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
