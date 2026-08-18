from __future__ import annotations

import hashlib
from typing import Any

from app.job_runtime.schemas import JobEvent
from app.job_runtime.service import JobService
from app.notifications.ports import NotificationRepository
from app.notifications.schemas import (
    NotificationDraft,
    NotificationProjection,
)


APPROVAL_NODES = {
    "human_review",
    "patch_review",
    "patch_promotion_review",
}

INPUT_NODES = {
    "command_selection",
}

INVALIDATES_OPERATION = {
    "job_resume_queued",
    "job_claimed",
    "job_succeeded",
    "job_failed",
    "job_cancelled",
    "job_lease_requeued",
    "job_reconciliation_required",
}


def _optional_int(
    payload: dict[str, Any],
    key: str,
    *,
    minimum: int,
) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= minimum else None


def _notification_id(event: JobEvent, kind: str) -> str:
    material = (
        f"phase44-v1:{event.event_id}:{event.job_id}:{kind}"
    ).encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()[:32]
    return f"notice_{digest}"


def _draft(
    event: JobEvent,
    *,
    kind: str,
    severity: str,
    title: str,
    message: str,
    operation_kind: str | None = None,
    expected_node: str | None = None,
) -> NotificationDraft:
    payload = event.payload
    return NotificationDraft(
        notification_id=_notification_id(event, kind),
        source_event_id=event.event_id,
        job_id=event.job_id,
        kind=kind,
        severity=severity,
        title=title,
        message=message,
        job_version=_optional_int(
            payload,
            "job_version",
            minimum=0,
        ),
        wait_generation=_optional_int(
            payload,
            "wait_generation",
            minimum=1,
        ),
        expected_node=expected_node,
        operation_kind=operation_kind,
        created_at=event.created_at,
    )


def build_notification_projection(
    event: JobEvent,
    *,
    worker_lost_active: bool,
) -> NotificationProjection:
    """纯确定性映射；不读取 LLM、日志、Artifact 或当前 Job。"""

    notification = None
    supersede_operation = (
        event.event_type in INVALIDATES_OPERATION
    )
    supersede_worker_lost = event.event_type in {
        "job_succeeded",
        "job_failed",
        "job_cancelled",
    }

    if event.event_type == "job_waiting_for_input":
        # 新 generation 先关闭旧等待通知，再插入当前通知。
        supersede_operation = True
        nodes = event.payload.get("interrupt_nodes")
        unique_nodes = (
            sorted(set(nodes))
            if isinstance(nodes, list)
            and all(isinstance(item, str) for item in nodes)
            else []
        )
        node = unique_nodes[0] if len(unique_nodes) == 1 else None

        if node in APPROVAL_NODES:
            notification = _draft(
                event,
                kind="approval_required",
                severity="warning",
                title="任务正在等待人工审批",
                message="请打开任务并核对当前提案、风险和内容身份。",
                operation_kind="submit_decision",
                expected_node=node,
            )
        elif node in INPUT_NODES:
            notification = _draft(
                event,
                kind="input_required",
                severity="warning",
                title="任务正在等待输入",
                message="请打开任务并完成当前命令选择。",
                operation_kind="submit_decision",
                expected_node=node,
            )
        else:
            # 未知或多 interrupt 不猜测 Decision 类型。
            notification = _draft(
                event,
                kind="input_required",
                severity="warning",
                title="任务需要人工检查",
                message="当前等待节点无法安全映射，请刷新任务详情。",
            )

    elif event.event_type == "job_succeeded":
        final_status = event.payload.get("final_status")
        suffix = (
            f"业务终态为 {final_status}。"
            if isinstance(final_status, str)
            and 0 < len(final_status) <= 100
            else "请打开最终报告查看业务终态。"
        )
        notification = _draft(
            event,
            kind="job_succeeded",
            severity="success",
            title="后台任务已经结束",
            message=(
                "Job Runtime 已安全推进到终点；"
                f"{suffix}"
            ),
        )

    elif event.event_type == "job_failed":
        notification = _draft(
            event,
            kind="job_failed",
            severity="error",
            title="后台任务执行失败",
            message="请打开任务查看结构化错误和已发布日志 Artifact。",
        )

    elif event.event_type == "job_lease_requeued":
        # 如果上一次 worker_lost 尚未关闭，先 supersede 后再写当前一次。
        supersede_worker_lost = True
        notification = _draft(
            event,
            kind="worker_lost",
            severity="warning",
            title="Worker 失联，任务等待恢复",
            message="Lease 已过期，系统确认可安全重新排队。",
        )

    elif event.event_type == "job_reconciliation_required":
        supersede_worker_lost = True
        notification = _draft(
            event,
            kind="worker_lost",
            severity="error",
            title="Worker 失联，需要人工核对",
            message=(
                "检测到可能存在外部副作用，系统不会自动重跑。"
            ),
            operation_kind=(
                "operator_reconciliation_required"
            ),
        )

    elif (
        event.event_type == "job_claimed"
        and worker_lost_active
    ):
        supersede_worker_lost = True
        notification = _draft(
            event,
            kind="job_recovered",
            severity="info",
            title="任务已由 Worker 恢复",
            message="新的 fenced claim 已接管任务并继续推进。",
        )

    return NotificationProjection(
        source_event_id=event.event_id,
        job_id=event.job_id,
        event_type=event.event_type,
        event_created_at=event.created_at,
        notification=notification,
        supersede_operation_notifications=(
            supersede_operation
        ),
        supersede_worker_lost=supersede_worker_lost,
    )


class NotificationProjector:
    """从全局 Job Event cursor 推进通知 Materialized View。"""

    def __init__(
        self,
        *,
        jobs: JobService,
        repository: NotificationRepository,
        batch_size: int = 200,
    ):
        self.jobs = jobs
        self.repository = repository
        self.batch_size = max(1, min(batch_size, 1000))

    def project_once(self) -> int:
        cursor = self.repository.projection_cursor()
        events = self.jobs.events_global_after(
            after_event_id=cursor,
            limit=self.batch_size,
        )
        for event in events:
            worker_lost_active = (
                self.repository.has_active_kind(
                    job_id=event.job_id,
                    kind="worker_lost",
                )
            )
            projection = build_notification_projection(
                event,
                worker_lost_active=worker_lost_active,
            )
            self.repository.apply_projection(projection)
        return len(events)

    def catch_up(
        self,
        *,
        max_batches: int = 50,
    ) -> int:
        """有界 catch-up；避免一次 HTTP 请求无限占用线程。"""

        processed = 0
        for _ in range(max(1, max_batches)):
            count = self.project_once()
            processed += count
            if count < self.batch_size:
                break
        return processed
