"""Phase 30 对话式 Timeline 投影。

把 Job/Event/Interrupt/AllowedOperation 确定性投影成前端可渲染的对话项，
不调用 LLM 生成文案，也不引入第二套状态机。
"""

from __future__ import annotations

from app.interaction.schemas import (
    EventView,
    JobView,
    TimelineItem,
    TimelineResponse,
)

EVENT_COPY: dict[str, tuple[str, str]] = {
    "job_submitted": (
        "任务已进入队列",
        "输入身份与执行配置已经固定。",
    ),
    "job_claimed": (
        "Worker 已接管任务",
        "正在准备独立 Workspace。",
    ),
    "workspace_materializing": (
        "正在准备 Workspace",
        "正在校验并物化论文、仓库和运行材料。",
    ),
    "workspace_ready": (
        "Workspace 已就绪",
        "Agent 开始执行论文理解与代码分析流程。",
    ),
    "job_waiting_for_input": (
        "需要你的确认",
        "请检查下方操作卡片后再继续。",
    ),
    "job_resume_queued": (
        "已收到你的决定",
        "任务已重新进入执行队列。",
    ),
    "job_succeeded": (
        "任务已完成",
        "可以在右侧查看报告和其他 Artifact。",
    ),
    "job_failed": (
        "任务执行失败",
        "请查看错误摘要、日志和可用 Artifact。",
    ),
    "job_cancelled": (
        "任务已取消",
        "系统已停止继续推进本次任务。",
    ),
    "job_reconciliation_required": (
        "需要运维核对",
        "外部副作用状态不明确，系统不会自动重跑。",
    ),
    "workspace_materialization_failed": (
        "Workspace 准备失败",
        "输入材料无法安全物化，请查看错误摘要。",
    ),
}

_TERMINAL_RESULT_EVENTS = {
    "job_succeeded",
    "job_cancelled",
}

_ERROR_MARKERS = (
    "failed",
    "reconciliation",
)


def _event_item(event: EventView) -> TimelineItem:
    title, content = EVENT_COPY.get(
        event.event_type,
        (
            "运行状态已更新",
            f"事件：{event.event_type}",
        ),
    )
    lowered = event.event_type
    if any(marker in lowered for marker in _ERROR_MARKERS):
        kind = "error"
    elif event.event_type in _TERMINAL_RESULT_EVENTS:
        kind = "result"
    else:
        kind = "progress"
    return TimelineItem(
        item_id=f"event:{event.event_id}",
        role="assistant",
        kind=kind,  # type: ignore[arg-type]
        title=title,
        content=content,
        created_at=event.created_at,
        event_id=event.event_id,
    )


def build_timeline(
    *,
    job: JobView,
    events: list[EventView],
) -> TimelineResponse:
    items = [
        TimelineItem(
            item_id="request",
            role="user",
            kind="request",
            title=job.input.experiment_goal,
            content=(
                f"论文：{job.input.paper_name}\n"
                f"仓库：{job.input.repo_name}\n"
                f"执行配置：{job.input.execution_profile_id}"
            ),
            created_at=job.created_at,
        ),
        *[_event_item(event) for event in events],
    ]

    # Decision 卡片完全来自服务端 AllowedOperation，
    # 前端不根据 node 自行猜测。
    decision_operation = next(
        (
            item
            for item in job.allowed_operations
            if item.kind == "submit_decision"
        ),
        None,
    )
    if decision_operation is not None:
        interrupt = (
            job.interrupts[0]
            if len(job.interrupts) == 1
            else None
        )
        items.append(
            TimelineItem(
                item_id=(
                    f"decision:{decision_operation.operation_id}"
                ),
                role="assistant",
                kind="decision",
                title="等待你的决定",
                content=(
                    decision_operation.detail
                    or "请检查操作详情。"
                ),
                created_at=job.updated_at,
                operation=decision_operation,
                interrupt=interrupt,
            )
        )

    if job.error is not None:
        items.append(
            TimelineItem(
                item_id=f"error:{job.version}",
                role="assistant",
                kind="error",
                title="当前错误摘要",
                content=str(job.error)[:2000],
                created_at=job.updated_at,
            )
        )

    return TimelineResponse(
        job=job,
        items=items,
        last_event_id=(
            events[-1].event_id if events else 0
        ),
    )
