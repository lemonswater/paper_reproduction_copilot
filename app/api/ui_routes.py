"""Phase 30 UI API：Timeline 投影与 UI 配置。

不引入 LLM 文案，也不重新设计 Job Runtime。
Timeline endpoint 最多读取 200 个事件，避免现在引入 cursor/pagination。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.auth import require_api_auth
from app.config import settings
from app.execution.profile_store import (
    load_execution_profiles,
)
from app.interaction.schemas import (
    PublicExecutionProfile,
    TimelineResponse,
    UiConfigResponse,
)
from app.interaction.service import InteractionService
from app.interaction.timeline import build_timeline

router = APIRouter(prefix="/v1/ui")
Actor = Annotated[str, Depends(require_api_auth)]


def interaction_service(
    request: Request,
) -> InteractionService:
    """从 app.state 取用例服务。

    这里不从 app.api.routes 导入私有 helper，避免 UI router
    和主 Job router 互相耦合甚至形成循环导入。
    """

    return request.app.state.interaction_service


InteractionDependency = Annotated[
    InteractionService,
    Depends(interaction_service),
]


@router.get("/config", response_model=UiConfigResponse)
def ui_config(_actor: Actor) -> UiConfigResponse:
    profiles = load_execution_profiles()
    return UiConfigResponse(
        product_name="Paper Reproduction Copilot",
        default_execution_profile=(
            settings.default_execution_profile
        ),
        execution_profiles=[
            PublicExecutionProfile(
                profile_id=item.profile_id,
                backend=item.backend,
                enforcement_mode=item.enforcement_mode,
                network_policy=item.network_policy,
            )
            for item in sorted(
                profiles.values(),
                key=lambda value: value.profile_id,
            )
        ],
        chat_enabled=settings.chat_enabled,
    )


@router.get(
    "/jobs/{job_id}/timeline",
    response_model=TimelineResponse,
)
def job_timeline(
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
) -> TimelineResponse:
    job = service.get_job(job_id)
    events = service.events_after(
        job_id=job_id,
        after_event_id=0,
        limit=200,
    )
    return build_timeline(job=job, events=events)
