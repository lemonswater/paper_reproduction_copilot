from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
    Request,
)
from fastapi.responses import StreamingResponse

from app.api.auth import require_api_auth
from app.artifact_delivery.schemas import (
    ArtifactPreviewResponse,
)
from app.artifact_delivery.service import (
    ArtifactDeliveryService,
)
from app.config import settings
from app.interaction.artifacts import (
    ArtifactCatalog,
)
from app.interaction.schemas import (
    ArtifactListResponse,
    CancelEnvelope,
    DecisionEnvelope,
    EventPage,
    JobCreateRequest,
    JobListResponse,
    JobMutationResponse,
    JobView,
    LogTailResponse,
)
from app.interaction.service import (
    InteractionService,
)
from app.job_runtime.schemas import (
    TERMINAL_JOB_STATUSES,
    JobStatus,
)
from app.observability.noop import NoOpTelemetry

router = APIRouter(prefix="/v1")

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=300,
    ),
]


def interaction_service(
    request: Request,
) -> InteractionService:
    return request.app.state.interaction_service


def artifact_catalog(
    request: Request,
) -> ArtifactCatalog:
    return request.app.state.artifact_catalog


def artifact_delivery_service(
    request: Request,
) -> ArtifactDeliveryService:
    return request.app.state.artifact_delivery_service


Actor = Annotated[
    str,
    Depends(require_api_auth),
]

InteractionDependency = Annotated[
    InteractionService,
    Depends(interaction_service),
]

ArtifactCatalogDependency = Annotated[
    ArtifactCatalog,
    Depends(artifact_catalog),
]

ArtifactDeliveryDependency = Annotated[
    ArtifactDeliveryService,
    Depends(artifact_delivery_service),
]

JobStatusQuery = Annotated[
    Optional[JobStatus],
    Query(),
]

PageLimitQuery = Annotated[
    int,
    Query(ge=1),
]

EventCursorQuery = Annotated[
    int,
    Query(ge=0),
]

LastEventIdHeader = Annotated[
    Optional[int],
    Header(
        alias="Last-Event-ID",
        ge=0,
    ),
]

FollowQuery = Annotated[
    bool,
    Query(),
]

LogLinesQuery = Annotated[
    int,
    Query(ge=1, le=2000),
]


def _get_telemetry(request: Request):
    try:
        telemetry = getattr(request.app.state, "telemetry", None)
        if telemetry is not None:
            return telemetry
    except Exception:
        pass
    return NoOpTelemetry()


def _sse(event: dict) -> str:
    """把单个事件编码为标准 SSE frame。"""

    payload = json.dumps(
        event,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        f"id: {event['event_id']}\n"
        f"event: {event['event_type']}\n"
        f"data: {payload}\n\n"
    )


def _iter_blob(
    body,
    *,
    chunk_bytes: int,
) -> Iterator[bytes]:
    """无论客户端正常完成还是中断，最终都关闭后端 body。"""

    try:
        while True:
            chunk = body.read(chunk_bytes)
            if not chunk:
                break
            yield chunk
    finally:
        body.close()


_UNSAFE_ATTACHMENT_CHARS = re.compile(
    r"[^A-Za-z0-9._-]+"
)


def _attachment_disposition(filename: str) -> str:
    """同时提供保守 ASCII fallback 和 RFC 5987 UTF-8 文件名。"""

    basename = Path(filename).name or "download.bin"
    fallback = _UNSAFE_ATTACHMENT_CHARS.sub(
        "_",
        basename,
    ).strip("._")[:120]
    if not fallback:
        fallback = "download.bin"

    return (
        f'attachment; filename="{fallback}"; '
        "filename*=UTF-8''"
        f"{quote(basename, safe='')}"
    )


def _iter_file_and_delete(
    path: Path,
    *,
    chunk_bytes: int,
) -> Iterator[bytes]:
    """导出响应完成或断开时都删除临时 ZIP。"""

    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(chunk_bytes)
                if not chunk:
                    break
                yield chunk
    finally:
        path.unlink(missing_ok=True)


@router.post(
    "/jobs",
    response_model=JobMutationResponse,
    status_code=201,
)
def create_job(
    request: Request,
    body: JobCreateRequest,
    idempotency_key: IdempotencyKey,
    _actor: Actor,
    service: InteractionDependency,
) -> JobMutationResponse:
    telemetry = _get_telemetry(request)
    try:
        with telemetry.span(
            "route.submit_job",
            attributes={
                "graph_node": "http_route",
                "endpoint": "/jobs",
            },
        ):
            return service.create_job(
                request=body,
                idempotency_key=idempotency_key,
            )
    except Exception:
        return service.create_job(
            request=body,
            idempotency_key=idempotency_key,
        )


@router.get(
    "/jobs",
    response_model=JobListResponse,
)
def list_jobs(
    request: Request,
    _actor: Actor,
    service: InteractionDependency,
    status: JobStatusQuery = None,
    limit: PageLimitQuery = 50,
) -> JobListResponse:
    telemetry = _get_telemetry(request)
    try:
        with telemetry.span(
            "route.list_jobs",
            attributes={
                "graph_node": "http_route",
            },
        ):
            bounded = min(
                limit,
                settings.api_max_page_size,
            )
            items = service.list_jobs(
                status=status,
                limit=bounded,
            )
            return JobListResponse(
                items=items,
                count=len(items),
            )
    except Exception:
        bounded = min(
            limit,
            settings.api_max_page_size,
        )
        items = service.list_jobs(
            status=status,
            limit=bounded,
        )
        return JobListResponse(
            items=items,
            count=len(items),
        )


@router.get(
    "/jobs/{job_id}",
    response_model=JobView,
)
def get_job(
    request: Request,
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
) -> JobView:
    telemetry = _get_telemetry(request)
    try:
        with telemetry.span(
            "route.get_job",
            attributes={
                "graph_node": "http_route",
            },
        ):
            return service.get_job(job_id)
    except Exception:
        return service.get_job(job_id)


@router.post(
    "/jobs/{job_id}/decisions",
    response_model=JobMutationResponse,
)
def submit_decision(
    job_id: str,
    body: DecisionEnvelope,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: InteractionDependency,
) -> JobMutationResponse:
    # mutation 绝不能放在"捕获任意异常后再调用一次"的 fallback 中。
    # JobConflictError/ValueError 交给 app/api/errors.py 的稳定 handler。
    return service.submit_decision(
        job_id=job_id,
        envelope=body,
        idempotency_key=idempotency_key,
        actor=actor,
    )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobMutationResponse,
)
def cancel_job(
    job_id: str,
    body: CancelEnvelope,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: InteractionDependency,
) -> JobMutationResponse:
    return service.cancel_job(
        job_id=job_id,
        envelope=body,
        idempotency_key=idempotency_key,
        actor=actor,
    )


@router.get(
    "/jobs/{job_id}/events",
    response_model=EventPage,
)
def list_events(
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
    after: EventCursorQuery = 0,
    limit: PageLimitQuery = 100,
) -> EventPage:
    events = service.events_after(
        job_id=job_id,
        after_event_id=after,
        limit=min(
            limit,
            settings.api_max_page_size,
        ),
    )
    return EventPage(
        items=events,
        next_after=(
            events[-1].event_id
            if events
            else after
        ),
    )


@router.get(
    "/jobs/{job_id}/events/stream"
)
async def stream_events(
    request: Request,
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
    after: EventCursorQuery = 0,
    last_event_id: LastEventIdHeader = None,
    follow: FollowQuery = True,
) -> StreamingResponse:
    """
    follow=false 用于读取当前 backlog 后关闭，也让离线测试不会永久阻塞。
    """

    telemetry = _get_telemetry(request)

    async def run_with_telemetry():
        # 必须在 StreamingResponse 开始发送响应头前验证 Job。
        # 否则 generator 内抛出的 404 已经无法转换成普通 JSON 错误响应。
        service.get_job(job_id)

        async def generate():
            cursor = max(
                after,
                last_event_id or 0,
            )
            last_heartbeat = time.monotonic()

            while True:
                events = await asyncio.to_thread(
                    service.events_after,
                    job_id=job_id,
                    after_event_id=cursor,
                    limit=settings.api_max_page_size,
                )

                for event in events:
                    cursor = event.event_id
                    yield _sse(
                        event.model_dump()
                    )

                if not follow:
                    return

                current = await asyncio.to_thread(
                    service.get_job,
                    job_id,
                )
                if (
                    current.status
                    in TERMINAL_JOB_STATUSES
                    and not events
                ):
                    return

                if await request.is_disconnected():
                    return

                now = time.monotonic()
                if (
                    now - last_heartbeat
                    >= settings
                    .api_sse_heartbeat_seconds
                ):
                    # SSE comment 不代表 Job heartbeat 或业务进度。
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

    try:
        with telemetry.span(
            "route.stream_events",
            attributes={
                "graph_node": "http_route",
            },
        ):
            return await run_with_telemetry()
    except Exception:
        return await run_with_telemetry()


@router.get(
    "/jobs/{job_id}/artifacts",
    response_model=ArtifactListResponse,
)
def list_artifacts(
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
    delivery: ArtifactDeliveryDependency,
) -> ArtifactListResponse:
    internal_job = (
        service.job_service.get(job_id)
    )
    items = delivery.list_views(internal_job)
    return ArtifactListResponse(
        items=items,
        count=len(items),
    )


@router.get(
    "/jobs/{job_id}/artifacts/"
    "{artifact_id}/preview",
    response_model=ArtifactPreviewResponse,
)
def preview_artifact(
    job_id: str,
    artifact_id: str,
    _actor: Actor,
    service: InteractionDependency,
    delivery: ArtifactDeliveryDependency,
) -> ArtifactPreviewResponse:
    internal_job = (
        service.job_service.get(job_id)
    )
    return delivery.preview(
        job=internal_job,
        artifact_id=artifact_id,
    )


@router.get(
    "/jobs/{job_id}/artifacts/"
    "{artifact_id}/content",
    include_in_schema=False,
)
@router.get(
    "/jobs/{job_id}/artifacts/"
    "{artifact_id}/download"
)
def download_artifact(
    job_id: str,
    artifact_id: str,
    _actor: Actor,
    service: InteractionDependency,
    catalog: ArtifactCatalogDependency,
) -> StreamingResponse:
    internal_job = (
        service.job_service.get(job_id)
    )
    opened = catalog.open(
        job=internal_job,
        artifact_id=artifact_id,
    )
    descriptor = (
        opened.artifact.descriptor
    )
    filename = Path(
        descriptor.relative_path
    ).name

    return StreamingResponse(
        _iter_blob(
            opened.blob.body,
            chunk_bytes=(
                settings
                .artifact_stream_chunk_bytes
            ),
        ),
        media_type="application/octet-stream",
        headers={
            "Content-Length": str(
                descriptor.size_bytes
            ),
            "Content-Disposition": (
                _attachment_disposition(filename)
            ),
            "ETag": (
                f'"sha256:{descriptor.sha256}"'
            ),
            "X-Artifact-SHA256": (
                descriptor.sha256
            ),
            "Cache-Control": (
                "private, no-store"
            ),
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": (
                "sandbox; default-src 'none'"
            ),
        },
    )


@router.get("/jobs/{job_id}/export")
def export_job(
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
    delivery: ArtifactDeliveryDependency,
) -> StreamingResponse:
    internal_job = (
        service.job_service.get(job_id)
    )
    public_job = service.get_job(job_id)

    prepared = delivery.build_export(
        job=internal_job,
        public_job=public_job.model_dump(mode="json"),
    )

    try:
        return StreamingResponse(
            _iter_file_and_delete(
                prepared.path,
                chunk_bytes=(
                    settings
                    .artifact_stream_chunk_bytes
                ),
            ),
            media_type="application/zip",
            headers={
                "Content-Length": str(
                    prepared.size_bytes
                ),
                "Content-Disposition": (
                    _attachment_disposition(
                        prepared.filename
                    )
                ),
                "ETag": (
                    f'"sha256:{prepared.sha256}"'
                ),
                "X-Export-SHA256": (
                    prepared.sha256
                ),
                "Cache-Control": (
                    "private, no-store"
                ),
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception:
        prepared.path.unlink(missing_ok=True)
        raise


@router.get(
    "/jobs/{job_id}/logs",
    response_model=LogTailResponse,
)
def tail_log(
    request: Request,
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
    lines: LogLinesQuery = 100,
) -> LogTailResponse:
    telemetry = _get_telemetry(request)
    try:
        with telemetry.span(
            "route.stream_logs",
            attributes={
                "graph_node": "http_route",
            },
        ):
            return service.tail_log(
                job_id=job_id,
                lines=lines,
                max_bytes=settings.api_max_log_bytes,
            )
    except Exception:
        return service.tail_log(
            job_id=job_id,
            lines=lines,
            max_bytes=settings.api_max_log_bytes,
        )
