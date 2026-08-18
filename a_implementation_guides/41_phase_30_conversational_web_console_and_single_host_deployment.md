# 41. Phase 30：对话式 Web Console 与单主机完整部署

Phase 29 已经补齐受控资源获取。当前系统具备 Job、Decision、SSE Event、Artifact、日志、
readiness、Job Worker 和 Resource Worker，但主要入口仍是 CLI 与原始 JSON API。

本阶段先停止继续增加底层基础设施，把现有能力包装成一个可以真实使用的单用户产品：

```text
浏览器提交论文与仓库资源
    -> 人工确认 Resource request hash
    -> Resource Worker 获取并发布
    -> 浏览器以自然语言描述实验目标
    -> 创建 Job，也就是一次 Conversation
    -> SSE 持续更新对话时间线
    -> 在对话中完成命令选择、执行审批和 Patch 审批
    -> 查看日志、Artifact 和最终状态
    -> 刷新页面后从后端恢复
```

> **本教程中的源码均为待实现代码。**
>
> 本阶段只做单用户、单主机、local-first 部署。前端和 API 同源，API 只监听 `127.0.0.1`；
> 远程访问使用 SSH 端口转发。暂不实现多用户登录、RBAC、公网 Cookie 会话和租户隔离。

---

## 一、这里的“可对话”是什么意思

> **本节类型：产品定义，不修改项目代码。**

本阶段不把系统改成一个无边界的通用聊天机器人。一个 `job_id` 就是一段任务对话：

```text
用户消息
    论文、仓库、实验目标

Agent 消息
    资源已固定
    正在解析论文
    正在扫描仓库
    正在生成实验计划
    正在执行命令

交互卡片
    选择 run_command
    批准 / 拒绝 / 要求修改 Action
    批准 / 拒绝 / 要求修改 Patch

结果消息
    succeeded / failed / cancelled
    Artifact 列表
    有界日志
    StageError 摘要
```

核心原则：

```text
Conversation 是 Job 的呈现方式，不是第二套状态机
Message 从 Job/Event/Interrupt/Artifact 确定性投影
前端只提交 AllowedOperation，不自行猜测 Graph 状态
页面刷新后从后端恢复，不依赖浏览器内存
```

这样既有对话体验，又不破坏前面已经建立的 checkpoint、hash、审批和 fencing。

---

## 二、为什么现在适合做前端

> **本节类型：架构说明，不修改项目代码。**

当前已有接口覆盖了 Web Console 的主要用例：

| 用户动作 | 已有后端能力 |
|---|---|
| 创建任务 | `POST /v1/jobs` |
| 查看历史任务 | `GET /v1/jobs` |
| 查看当前状态 | `GET /v1/jobs/{job_id}` |
| 实时更新 | `GET /v1/jobs/{job_id}/events/stream` |
| 人工决策 | `POST /v1/jobs/{job_id}/decisions` |
| 取消任务 | `POST /v1/jobs/{job_id}/cancel` |
| 查看日志 | `GET /v1/jobs/{job_id}/logs` |
| 查看和下载产物 | Artifact API |
| 提交/批准资源 | Resource API |
| 判断服务可用性 | `/livez`、`/readyz` |

所以 Phase 30 的后端工作主要是 **presentation adapter**、静态文件托管和本机进程编排，而不是
重新设计 Job Runtime。

---

## 三、本阶段完成定义

> **本节类型：目标说明，不修改项目代码。**

完成后必须满足：

1. 使用 React + TypeScript + Vite 构建单页 Web Console；
2. `job_id` 作为 conversation identity，不增加 Conversation 数据库表；
3. 后端提供确定性的 timeline endpoint，不调用 LLM 生成聊天文案；
4. 左侧可查看任务历史，中间是对话时间线，右侧是状态/日志/Artifact；
5. 用户可以通过 Resource wizard 提交论文 PDF 和 Git exact commit；
6. Resource approval 必须展示并绑定服务端 `request_sha256`；
7. 用户可以从界面创建 Job、取消 Job 和完成全部现有 Decision；
8. SSE 到达后刷新 timeline/job，断线时有低频轮询兜底；
9. 前端只使用服务端返回的 `allowed_operations`；
10. 409 stale version 后刷新当前 Job，不自动重放旧决定；
11. 页面刷新后可以恢复历史 Job 和当前对话；
12. 生产构建由 FastAPI 同源托管，不需要 CORS；
13. 一个 `serve-stack` 命令启动 API、Job Worker 和 Resource Worker；
14. 服务只监听 loopback，远程浏览器通过 SSH tunnel 访问；
15. 普通 API/Worker/CLI 能力保持可用；
16. 有后端单元测试、前端类型检查、前端构建和手工端到端验收。

---

## 四、本阶段明确不做

> **本节类型：范围说明，不修改项目代码。**

```text
不做多用户注册、登录、RBAC 和 tenant
不暴露公网 API
不把 AGENT_API_TOKEN 打包进前端
不把 token 放在 URL 或 EventSource query
不引入 Next.js、SSR 或 React Server Components
不引入 Redux、MobX、复杂前端状态机或大型 UI 框架
不改成 WebSocket；现有 SSE 足够
不引入 Redis、消息队列、Kubernetes 或 Docker Compose
不实现任意文件上传
不实现通用聊天记忆和跨 Job 自由问答
不自动判断论文是否复现成功
不让前端直接读取 run_dir、数据库或宿主机仓库
```

Vite 官方说明 `vite preview` 只用于本地预览，不是生产服务器；本阶段生产模式使用
`vite build` 的 `dist/`，由 FastAPI 托管：
[Vite static deployment](https://vite.dev/guide/static-deploy.html)。

---

## 五、最终架构

> **本节类型：架构说明，不修改项目代码。**

```text
Browser
  React SPA
    | same-origin fetch
    | EventSource SSE
    v
FastAPI 127.0.0.1:8000
  /v1/jobs
  /v1/resources
  /v1/ui/config
  /livez /readyz
  /assets/* + SPA index.html
    |
    +-> SQLite/PostgreSQL Job Store
    +-> Artifact Store

serve-stack process
  +-> API main thread
  +-> JobWorker thread
  +-> ResourceWorker polling thread

Remote browser
  -> SSH -L 8000:127.0.0.1:8000
```

SSE 是单向 server-to-browser 推送，浏览器决策仍使用普通 POST；这正好符合当前交互模型。
`EventSource` 是浏览器原生 API：
[Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)。

---

## 六、页面结构与视觉方向

> **本节类型：产品设计，不修改项目代码。**

界面不是普通后台表格，而是一个“研究工作台”：

```text
┌────────────────┬──────────────────────────────┬──────────────────┐
│ Reproduction   │ 对话时间线                    │ Run Context      │
│ sessions       │                              │                  │
│                │ You                          │ Status           │
│ + New session  │ 复现 PSTNet main result      │ running          │
│                │                              │                  │
│ running        │ Agent                        │ Artifacts        │
│ PSTNet         │ 已完成论文结构提取             │ paper_summary    │
│                │                              │ experiment_plan  │
│ waiting        │ [Command selection card]     │                  │
│ P4Transformer  │                              │ Live log         │
└────────────────┴──────────────────────────────┴──────────────────┘
```

视觉建议：

```text
背景：暖灰纸张色 + 很淡的坐标网格
正文：深墨色
主强调：氧化橙，不使用默认紫色
成功：苔绿色
等待审批：琥珀色
失败：砖红色
标题字体：Newsreader Variable
正文字体：Manrope Variable
日志：等宽字体
```

桌面三栏，窄屏下：历史列表变顶部抽屉，右侧 Context 变底部 tab。只保留两种动画：页面首次
进入的 stagger reveal，以及新增 timeline item 的短距离淡入。

---

## 七、文件清单

> **本节类型：实施清单。**

需要新增后端文件：

```text
app/interaction/timeline.py
app/api/ui_routes.py
app/web.py
app/service_host.py
tests/test_timeline_projection.py
tests/test_ui_api.py
tests/test_web_static.py
tests/test_service_host.py
```

需要修改后端文件：

```text
app/config.py
app/interaction/schemas.py
app/interaction/service.py
app/api/routes.py
app/api/app.py
app/resources/worker.py（可选；也可只在 service_host 外层循环）
app/main.py
.env.example
.gitignore
```

需要新增前端目录：

```text
web/
  package.json
  package-lock.json
  tsconfig.json
  vite.config.ts
  index.html
  src/
    main.tsx
    App.tsx
    api/types.ts
    api/client.ts
    hooks/useJobStream.ts
    components/SessionSidebar.tsx
    components/ConversationTimeline.tsx
    components/DecisionCard.tsx
    components/NewSessionPanel.tsx
    components/ResourceWizard.tsx
    components/RunContextPanel.tsx
    components/StatusBadge.tsx
    styles/tokens.css
    styles/app.css
  tests/
    timeline.test.tsx
```

本阶段不生成临时拼接文件。所有教程代码直接写入上述正式文件；测试临时目录继续使用项目内
`.pytest-tmp/`。

---

## 八、先修复两个公开 API 接缝

> **本节类型：需要修改项目代码。**
>
> 修改：`app/interaction/service.py`、`app/api/app.py`。

### 8.1 Resource Job 的公开名称

Phase 29 Resource 分支允许 `paper_path/repo_path=None`。当前 `project_job()` 如果仍直接执行
`Path(record.request.paper_path)`，Web 查询 Resource Job 时会报错。

在 `app/interaction/service.py` 增加：

```python
def _public_input_name(
    *,
    local_path: str | None,
    resource: Any | None,
    fallback: str,
) -> str:
    if local_path:
        return Path(local_path).name
    if resource is not None:
        # 公开视图只展示稳定 Resource ID，不泄露 object key 或本机物化路径。
        return f"{resource.kind}:{resource.resource_id}"
    return fallback
```

然后替换 `PublicJobInput` 构造：

```python
input=PublicJobInput(
    paper_name=_public_input_name(
        local_path=record.request.paper_path,
        resource=record.request.paper_resource,
        fallback="paper",
    ),
    repo_name=_public_input_name(
        local_path=record.request.repo_path,
        resource=record.request.repo_resource,
        fallback="repository",
    ),
    experiment_goal=record.request.experiment_goal,
    execution_profile_id=record.request.execution_profile_id,
),
```

### 8.2 HTTP metric 必须使用 route template

当前 middleware 如果使用 `request.url.path`，`/v1/jobs/job_xxx` 会为每个 Job 创建一组 metric
series。应在 `call_next()` 后读取匹配后的 route template：

```python
response = await call_next(request)
route_template = getattr(
    request.scope.get("route"),
    "path",
    "unmatched",
)

telemetry.counter(
    "paper_copilot_http_requests_total",
    1,
    {
        "method": request.method,
        "route": route_template,
        "status_class": status_class,
    },
)
telemetry.histogram(
    "paper_copilot_http_request_duration_seconds",
    elapsed,
    {
        "method": request.method,
        "route": route_template,
        "status_class": status_class,
    },
)
```

计数器和 histogram 必须一起改，否则仍会留下一组高基数时序。不要用真实 path 作为
metric label；`job_id` 可以进入单条 log/span context，但不能进入 metric label。创建 span 时如果
还没有 route template，先只记录 `http.method`，不要把真实 path 冒充为 `http.route`。

---

## 九、增加 Timeline schema

> **本节类型：需要修改项目代码。**
>
> 修改：`app/interaction/schemas.py`。

在文件末尾增加：

```python
TimelineRole = Literal["user", "assistant", "system"]
TimelineKind = Literal[
    "request",
    "progress",
    "decision",
    "result",
    "error",
]


class TimelineItem(InteractionModel):
    """前端可以稳定渲染的对话项，不包含内部 State 或绝对路径。"""

    item_id: str
    role: TimelineRole
    kind: TimelineKind
    title: str
    content: str
    created_at: str
    event_id: int | None = None
    operation: AllowedOperation | None = None
    interrupt: PublicInterrupt | None = None


class TimelineResponse(InteractionModel):
    job: JobView
    items: list[TimelineItem]
    last_event_id: int = 0


class PublicExecutionProfile(InteractionModel):
    profile_id: str
    backend: str
    enforcement_mode: str
    network_policy: str


class UiConfigResponse(InteractionModel):
    product_name: str
    default_execution_profile: str
    execution_profiles: list[PublicExecutionProfile]
    resources_enabled: bool = True
    deployment_mode: Literal["local_single_user"] = "local_single_user"
```

Timeline 不返回 Event 的任意 payload。Decision 需要的有界 preview 已经通过 `PublicInterrupt` 投影，
其他内部 payload 默认不进入聊天界面。

---

## 十、确定性投影 Timeline

> **本节类型：需要新增项目代码。**
>
> 新增：`app/interaction/timeline.py`。

```python
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


def _event_item(event: EventView) -> TimelineItem:
    title, content = EVENT_COPY.get(
        event.event_type,
        (
            "运行状态已更新",
            f"事件：{event.event_type}",
        ),
    )
    kind = (
        "error"
        if "failed" in event.event_type
        or "reconciliation" in event.event_type
        else "result"
        if event.event_type in {
            "job_succeeded",
            "job_cancelled",
        }
        else "progress"
    )
    return TimelineItem(
        item_id=f"event:{event.event_id}",
        role="assistant",
        kind=kind,
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

    # Decision 卡片完全来自服务端 AllowedOperation，前端不根据 node 自行猜测。
    decision_operation = next(
        (
            item
            for item in job.allowed_operations
            if item.kind == "submit_decision"
        ),
        None,
    )
    if decision_operation is not None:
        interrupt = job.interrupts[0] if len(job.interrupts) == 1 else None
        items.append(
            TimelineItem(
                item_id=f"decision:{decision_operation.operation_id}",
                role="assistant",
                kind="decision",
                title="等待你的决定",
                content=decision_operation.detail or "请检查操作详情。",
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
        last_event_id=(events[-1].event_id if events else 0),
    )
```

`str(job.error)` 是已经经过 `_public_value()` 脱敏的公开对象。后续可以做更漂亮的 Error schema，
但本阶段不要让 LLM重新解释错误。

---

## 十一、增加 Timeline 与 UI Config API

> **本节类型：需要新增和修改项目代码。**
>
> 新增：`app/api/ui_routes.py`。
>
> 修改：`app/api/app.py`。

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.auth import require_api_auth
from app.config import settings
from app.execution.profile_store import load_execution_profiles
from app.interaction.schemas import (
    PublicExecutionProfile,
    TimelineResponse,
    UiConfigResponse,
)
from app.interaction.service import InteractionService
from app.interaction.timeline import build_timeline

router = APIRouter(prefix="/v1/ui")
Actor = Annotated[str, Depends(require_api_auth)]


def interaction_service(request: Request) -> InteractionService:
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
        default_execution_profile=settings.default_execution_profile,
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
```

在 `create_api_app()` 中，API routers 必须在静态 SPA 之前注册：

```python
from app.api.ui_routes import router as ui_router

app.include_router(router)
app.include_router(resource_router)
app.include_router(ui_router)
```

第一版 timeline 最多读取 200 个事件。真实任务超过后再做 cursor/pagination，不要现在引入新的
消息数据库。

---

## 十二、托管 Vite 生产构建

> **本节类型：需要新增和修改项目代码。**
>
> 新增：`app/web.py`。
>
> 修改：`app/config.py`、`app/api/app.py`、`.env.example`。

配置：

```python
class Settings:
    # ...保留已有字段...
    web_dist_dir: Path = Path(
        os.getenv("WEB_DIST_DIR", "web/dist")
    )
    web_ui_required: bool = _env_bool(
        "WEB_UI_REQUIRED", False
    )
    resource_poll_seconds: float = float(
        os.getenv("RESOURCE_POLL_SECONDS", "1")
    )
```

`.env.example`：

```dotenv
WEB_DIST_DIR=web/dist
WEB_UI_REQUIRED=false
RESOURCE_POLL_SECONDS=1
```

`app/web.py`：

```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response


class SpaStaticFiles(StaticFiles):
    """未知的无扩展名路径回退到 index.html，静态资源 404 不回退。"""

    async def get_response(self, path: str, scope) -> Response:
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            # StaticFiles 在没有自定义 404.html 时会抛异常，
            # 但 JS/CSS/image 等真实静态资源仍应保持 404。
            if exc.status_code != 404 or Path(path).suffix:
                raise
            return await super().get_response("index.html", scope)

        # 如果 dist 中存在 404.html，StaticFiles 可能返回 404 Response
        # 而不是抛异常，因此这个分支也要保留。
        if response.status_code == 404 and not Path(path).suffix:
            return await super().get_response("index.html", scope)
        return response


def mount_web_ui(
    app: FastAPI,
    *,
    dist_dir: Path,
    required: bool,
) -> None:
    resolved = dist_dir.expanduser().resolve()
    index = resolved / "index.html"
    if not index.is_file():
        if required:
            raise RuntimeError(
                f"WEB_UI_REQUIRED=true，但缺少前端构建：{index}"
            )
        return

    # 必须最后 mount，避免吞掉 /v1、/docs、/livez 和 /readyz。
    app.mount(
        "/",
        SpaStaticFiles(directory=resolved, html=True),
        name="web-ui",
    )
```

`create_api_app()` 最后：

```python
app.include_router(router)
app.include_router(resource_router)
app.include_router(ui_router)
install_error_handlers(app)

mount_web_ui(
    app,
    dist_dir=settings.web_dist_dir,
    required=settings.web_ui_required,
)
return app
```

FastAPI 官方提供 `StaticFiles` 作为静态文件托管能力：
[FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/)。

---

## 十三、增加最小安全响应头

> **本节类型：需要修改项目代码。**
>
> 修改：`app/api/app.py`。

在 observability middleware 正常得到 response 后增加：

```python
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["Referrer-Policy"] = "no-referrer"
response.headers["X-Frame-Options"] = "DENY"
if settings.web_ui_required:
    # Vite dev server 需要 HMR WebSocket；生产同源构建才使用这个严格 CSP。
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "font-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
```

因此字体必须打包进前端，不能依赖 Google Fonts CDN。开发阶段 Vite HMR 可能需要更宽松 CSP，
最简单做法是只在 `WEB_UI_REQUIRED=true` 的生产模式增加 CSP。

---

## 十四、让 Resource Worker 可以持续轮询

> **本节类型：需要修改项目代码。**
>
> 修改：`app/resources/worker.py` 或在 `app/service_host.py` 外层实现循环。

当前 `run-resource-worker` 一次只调用一轮。单命令部署需要一个可停止的循环：

```python
import threading


class ResourceWorker:
    # 保留现有 __init__ 和 run_once。

    def run_forever(
        self,
        *,
        stop_event: threading.Event | None = None,
        poll_seconds: float = 1.0,
    ) -> None:
        stop = stop_event or threading.Event()
        while not stop.is_set():
            handled = self.run_once()
            if not handled:
                # Event.wait 可在 shutdown 时立即醒来，比 time.sleep 更容易停止。
                stop.wait(poll_seconds)
```

`run_once()` 必须自行把单个 Resource 的业务异常写回状态，不能因为一次下载失败退出整个 Worker。
真正的初始化错误仍应抛出，让 `serve-stack` 启动失败而不是假装 ready。

---

## 十五、增加单进程 Stack Host

> **本节类型：需要新增和修改项目代码。**
>
> 新增：`app/service_host.py`。
>
> 修改：`app/main.py`。

先把 `app/main.py` 中构造 Worker 的长代码提取成可复用函数，例如：

```python
from app.resources.worker import ResourceWorker


def build_job_worker(worker_id: str) -> JobWorker:
    """CLI 独立 Worker 和 serve-stack 共用完全相同的构造路径。"""

    from app.workspace.manager import WorkspaceManager
    from app.workspace.materializer import WorkspaceMaterializer
    from app.workspace.snapshot import WorkspaceSnapshotter

    service = build_job_service()
    artifact_storage = build_artifact_storage()
    workspace_manager = WorkspaceManager(
        store=service.store,
        materializer=WorkspaceMaterializer(
            blob_store=artifact_storage.selected_store,
        ),
        snapshotter=WorkspaceSnapshotter(
            blob_store=artifact_storage.selected_store,
        ),
    )
    return JobWorker(
        worker_id=worker_id,
        store=service.store,
        workspace_manager=workspace_manager,
        artifact_publisher=artifact_storage.publisher,
    )


def build_resource_worker(worker_id: str) -> ResourceWorker:
    """Resource Worker 仍保留 Phase 29 的网络 guard，不因 Web 部署降级。"""

    if settings.resource_require_network_guard and (
        not settings.resource_network_guard_configured
    ):
        raise RuntimeError(
            "RESOURCE_REQUIRE_NETWORK_GUARD=true 但未配置 egress guard"
        )

    from app.resources.service import build_resource_service

    resource_service = build_resource_service()
    artifact_storage = build_artifact_storage()
    return ResourceWorker(
        repository=resource_service.repository,
        blob_store=artifact_storage.selected_store,
        worker_id=worker_id,
    )
```

然后让现有 `run-worker` 和 `run-resource-worker` 也调用这两个 builder，删除命令内的重复
构造代码。这一步不是为了“好看”，而是防止 CLI 与 Web 使用不同 Store、Blob Store 或
Workspace policy。

`run-resource-worker` 的 `--once` 语义保留，不带 `--once` 时改成真正的持续模式：

```python
worker = build_resource_worker(effective_worker_id)
if once:
    processed = worker.run_once()
    print({"processed": int(processed)})
    return

try:
    worker.run_forever(
        poll_seconds=settings.resource_poll_seconds,
    )
except KeyboardInterrupt:
    print("Resource Worker 已停止")
```

`app/service_host.py`：

```python
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)


class ServiceHost:
    """单用户本机部署的轻量编排器，不替代 systemd/Kubernetes。"""

    def __init__(
        self,
        *,
        job_worker_factory: Callable[[], object],
        resource_worker_factory: Callable[[], object],
        resource_poll_seconds: float,
    ):
        self.job_worker_factory = job_worker_factory
        self.resource_worker_factory = resource_worker_factory
        self.resource_poll_seconds = resource_poll_seconds
        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []
        self.job_worker = None
        self.resource_worker = None
        self.failure: BaseException | None = None
        self._failure_lock = threading.Lock()

    def _run_worker(self, name: str, worker, **kwargs) -> None:
        try:
            worker.run_forever(**kwargs)
        except Exception as exc:
            # 不让后台线程静默死亡；readiness 必须能观察到。
            log.exception("embedded %s stopped unexpectedly", name)
            with self._failure_lock:
                self.failure = exc
            self.stop_event.set()

    def readiness(self) -> str:
        with self._failure_lock:
            if self.failure is not None:
                return "not_ready"
        if not self.threads or any(not thread.is_alive() for thread in self.threads):
            return "not_ready"
        return "ready"

    def start(self) -> None:
        self.job_worker = self.job_worker_factory()
        self.resource_worker = self.resource_worker_factory()

        self.threads = [
            threading.Thread(
                name="job-worker",
                target=self._run_worker,
                kwargs={
                    "name": "job-worker",
                    "worker": self.job_worker,
                    "stop_event": self.stop_event,
                },
                daemon=False,
            ),
            threading.Thread(
                name="resource-worker",
                target=self._run_worker,
                kwargs={
                    "name": "resource-worker",
                    "worker": self.resource_worker,
                    "stop_event": self.stop_event,
                    "poll_seconds": self.resource_poll_seconds,
                },
                daemon=False,
            ),
        ]
        for thread in self.threads:
            thread.start()

    def stop(self, timeout_seconds: float = 15.0) -> None:
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=timeout_seconds)

        alive = [thread.name for thread in self.threads if thread.is_alive()]
        if alive:
            raise RuntimeError(
                f"workers 未在预算内退出：{alive}"
            )
```

`JobWorker.run_forever()` 已经在自己的 `finally` 中调用 `close()`，所以
`ServiceHost.stop()` 只负责发送停止信号和等待线程，不要在 Worker 仍可能运行时提前
关闭 heartbeat。`ResourceWorker` 没有长期资源，通过同一个 `stop_event` 退出即可。

在 `app/api/app.py` 的 `create_api_app()` 增加可选 `service_host` 参数，并在已有 `probes`
中加入临界检查：

```python
def create_api_app(
    *,
    job_service: JobService | None = None,
    artifact_catalog: ArtifactCatalog | None = None,
    api_token: str | None = None,
    service_host: Any | None = None,
) -> FastAPI:
    # ...保留原有构造逻辑...
    probes = [
        # ...保留 db/storage/resource_db probes...
    ]
    if service_host is not None:
        probes.append(
            ReadinessProbe(
                name="embedded_workers",
                is_critical=True,
                check=service_host.readiness,
                timeout_seconds=settings.readiness_timeout_seconds,
            )
        )
```

`Any` 已经用于这个可选端口时，记得在 `app/api/app.py` 顶部从 `typing` 导入。API 单独
启动时 `service_host=None`，不会凭空要求嵌入式 Worker。

在 `app/main.py` 增加：

```python
@app.command("serve-stack")
def serve_stack_command(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """启动 Web/API、Job Worker 和 Resource Worker。"""

    if not _is_loopback_host(host):
        raise typer.BadParameter(
            "Phase 30 serve-stack 只允许 loopback；远程访问请使用 SSH tunnel"
        )
    if settings.api_token:
        raise typer.BadParameter(
            "Phase 30 浏览器 EventSource 不携带 Bearer header；"
            "请在 loopback 部署中取消 AGENT_API_TOKEN"
        )

    from uuid import uuid4
    import socket
    import uvicorn

    from app.api.app import create_api_app
    from app.service_host import ServiceHost

    hostname = socket.gethostname()
    host_runtime = ServiceHost(
        job_worker_factory=lambda: build_job_worker(
            f"{hostname}-web-{uuid4().hex[:8]}"
        ),
        resource_worker_factory=lambda: build_resource_worker(
            f"{hostname}-resource-{uuid4().hex[:8]}"
        ),
        resource_poll_seconds=settings.resource_poll_seconds,
    )
    host_runtime.start()
    try:
        uvicorn.run(
            create_api_app(service_host=host_runtime),
            host=host,
            port=port,
            reload=False,
            proxy_headers=False,
            workers=1,
        )
    finally:
        host_runtime.stop()
```

第一版固定一个 Uvicorn Worker，因为后台 Worker thread 与进程绑定。以后改成独立服务时再允许多
API workers；本阶段不要引入重复启动后台线程的风险。

---

## 十六、后端测试

> **本节类型：需要新增测试代码。**

### 16.1 Timeline

`tests/test_timeline_projection.py`：

```python
from app.interaction.schemas import (
    AllowedOperation,
    EventView,
    JobView,
    PublicInterrupt,
    PublicJobInput,
)
from app.interaction.timeline import build_timeline


def _job(**updates) -> JobView:
    values = {
        "job_id": "job-1",
        "thread_id": "thread-1",
        "run_id": "run-1",
        "status": "running",
        "version": 2,
        "attempt_count": 1,
        "max_attempts": 3,
        "wait_generation": 0,
        "interrupt_nodes": [],
        "interrupts": [],
        "cancel_requested": False,
        "input": PublicJobInput(
            paper_name="paper:r-paper",
            repo_name="git_repository:r-repo",
            experiment_goal="reproduce main result",
            execution_profile_id="local",
        ),
        "allowed_operations": [],
        "created_at": "2026-08-01T00:00:00+00:00",
        "updated_at": "2026-08-01T00:01:00+00:00",
    }
    values.update(updates)
    return JobView(**values)


def test_timeline_is_deterministic_and_does_not_copy_payload():
    event = EventView(
        event_id=7,
        job_id="job-1",
        event_type="future_internal_event",
        actor="worker",
        payload={"claim_token": "must-not-leak"},
        created_at="2026-08-01T00:00:10+00:00",
    )

    first = build_timeline(job=_job(), events=[event])
    second = build_timeline(job=_job(), events=[event])

    assert first == second
    assert first.items[0].role == "user"
    assert first.items[1].item_id == "event:7"
    assert "must-not-leak" not in first.model_dump_json()


def test_waiting_job_uses_server_operation_for_decision_item():
    operation = AllowedOperation(
        operation_id="wait:1:human_review",
        kind="submit_decision",
        endpoint="/v1/jobs/job-1/decisions",
        decision_kind="action_approval",
        expected_node="human_review",
        expected_job_version=3,
        expected_wait_generation=1,
        allowed_decisions=["approved", "rejected", "revise"],
    )
    interrupt = PublicInterrupt(
        node="human_review",
        value_preview={"action": {"command": "python train.py"}},
    )
    timeline = build_timeline(
        job=_job(
            status="waiting_for_input",
            version=3,
            wait_generation=1,
            interrupt_nodes=["human_review"],
            interrupts=[interrupt],
            allowed_operations=[operation],
        ),
        events=[],
    )

    decision = timeline.items[-1]
    assert decision.kind == "decision"
    assert decision.operation == operation
    assert decision.interrupt == interrupt
```

### 16.2 UI API

`tests/test_ui_api.py`：

```python
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.ui_routes as ui_routes
from app.api.ui_routes import router
from app.config import settings
from app.interaction.service import _public_input_name
from tests.test_timeline_projection import _job


class FakeInteractionService:
    def get_job(self, job_id: str):
        assert job_id == "job-1"
        return _job()

    def events_after(self, **kwargs):
        assert kwargs["after_event_id"] == 0
        return []


def _client() -> TestClient:
    app = FastAPI()
    app.state.api_token = None
    app.state.interaction_service = FakeInteractionService()
    app.include_router(router)
    return TestClient(app)


def test_ui_config_only_contains_public_profile_fields(monkeypatch):
    profile = SimpleNamespace(
        profile_id="safe-local",
        backend="native",
        enforcement_mode="strict",
        network_policy="none",
        workspace_root="/must/not/leak",
        env={"SECRET": "must-not-leak"},
    )
    monkeypatch.setattr(
        ui_routes,
        "load_execution_profiles",
        lambda: {"safe-local": profile},
    )
    monkeypatch.setattr(
        settings,
        "default_execution_profile",
        "safe-local",
    )

    response = _client().get("/v1/ui/config")

    assert response.status_code == 200
    encoded = response.text
    assert "safe-local" in encoded
    assert "workspace_root" not in encoded
    assert "must-not-leak" not in encoded


def test_timeline_endpoint_returns_public_projection():
    response = _client().get("/v1/ui/jobs/job-1/timeline")

    assert response.status_code == 200
    assert response.json()["job"]["job_id"] == "job-1"
    assert response.json()["items"][0]["role"] == "user"


def test_resource_input_name_does_not_call_path_on_none():
    resource = SimpleNamespace(
        kind="paper_pdf",
        resource_id="resource-1",
    )

    assert _public_input_name(
        local_path=None,
        resource=resource,
        fallback="paper",
    ) == "paper_pdf:resource-1"
```

如果你的 `tests/` 不是 Python package，不要跨测试文件导入 `_job`；把该 fixture 移到
`tests/helpers/interaction.py` 后从两个测试共用。不要为了复用去修改产品源码。

### 16.3 Static UI

`tests/test_web_static.py`：

```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.web import mount_web_ui


def test_missing_optional_dist_does_not_break_api(tmp_path):
    app = FastAPI()
    app.get("/readyz")(lambda: {"status": "ready"})

    mount_web_ui(app, dist_dir=tmp_path / "missing", required=False)

    assert TestClient(app).get("/readyz").status_code == 200


def test_missing_required_dist_fails_fast(tmp_path):
    with pytest.raises(RuntimeError, match="index.html"):
        mount_web_ui(
            FastAPI(),
            dist_dir=tmp_path / "missing",
            required=True,
        )


def test_spa_fallback_does_not_hide_missing_assets(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<html><body>paper-copilot-ui</body></html>",
        encoding="utf-8",
    )
    app = FastAPI()
    app.get("/v1/ping")(lambda: {"ok": True})
    mount_web_ui(app, dist_dir=dist, required=True)
    client = TestClient(app)

    assert "paper-copilot-ui" in client.get("/").text
    assert "paper-copilot-ui" in client.get("/jobs/job-1").text
    assert client.get("/assets/missing.js").status_code == 404
    assert client.get("/v1/ping").json() == {"ok": True}
```

### 16.4 Service Host

`tests/test_service_host.py` 使用 Fake Worker：

```python
import threading

import pytest

from app.service_host import ServiceHost


class FakeWorker:
    def __init__(self):
        self.started = threading.Event()
        self.closed = False

    def run_forever(self, *, stop_event, **_kwargs):
        self.started.set()
        try:
            stop_event.wait(5)
        finally:
            # 模拟 JobWorker.run_forever() 自己的 finally/close 语义。
            self.closed = True


def test_host_starts_and_stops_both_workers():
    job_worker = FakeWorker()
    resource_worker = FakeWorker()
    host = ServiceHost(
        job_worker_factory=lambda: job_worker,
        resource_worker_factory=lambda: resource_worker,
        resource_poll_seconds=0.01,
    )

    host.start()
    assert job_worker.started.wait(1)
    assert resource_worker.started.wait(1)
    assert host.readiness() == "ready"

    host.stop(timeout_seconds=1)

    assert job_worker.closed
    assert resource_worker.closed
    assert all(not thread.is_alive() for thread in host.threads)


def test_factory_failure_does_not_start_half_a_stack():
    job_worker = FakeWorker()

    def fail_resource_factory():
        raise RuntimeError("resource init failed")

    host = ServiceHost(
        job_worker_factory=lambda: job_worker,
        resource_worker_factory=fail_resource_factory,
        resource_poll_seconds=0.01,
    )

    with pytest.raises(RuntimeError, match="resource init failed"):
        host.start()

    assert host.threads == []
    assert not job_worker.started.is_set()
```

---

## 十七、创建 React + TypeScript 工程

> **本节类型：需要新增前端代码。**

Vite 当前版本要求较新的 Node.js；先按官方文档检查 Node 版本。当前 Vite 文档要求 Node
`20.19+` 或 `22.12+`：
[Vite Getting Started](https://vite.dev/guide/)。

在项目根目录执行：

```bash
node --version
npm --version
npm create vite@latest web -- --template react-ts --no-interactive
cd web
npm install
npm install @fontsource-variable/newsreader @fontsource-variable/manrope
npm install --save-dev vitest jsdom @testing-library/react
```

不要删除 `package-lock.json`。生产构建使用 `npm ci`，保证依赖来自已提交 lockfile。

`web/package.json` scripts 至少包含：

```json
{
  "scripts": {
    "dev": "vite",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "build": "npm run typecheck && vite build",
    "preview": "vite preview"
  }
}
```

将脚手架默认的 `web/src/main.tsx` 改成下面这个唯一入口：

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles/tokens.css";
import "./styles/app.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Missing #root element");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

删除脚手架中不再使用的 `App.css` logo 样式和 SVG 示例，避免两套全局样式互相
覆盖。

在项目根 `.gitignore` 增加：

```gitignore
web/node_modules/
web/dist/
```

`web/package-lock.json` 不能忽略，它是单主机重复构建前端的依赖身份。

---

## 十八、配置 Vite 同源代理

> **本节类型：需要新增前端代码。**
>
> 修改：`web/vite.config.ts`。

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  base: "/",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/v1": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
      },
      "/livez": "http://127.0.0.1:8000",
      "/readyz": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
  },
});
```

浏览器始终请求相对路径 `/v1/...`。不要在源码中硬编码生产 API host，也不要开启宽泛 CORS。

---

## 十九、定义前端 API 类型

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/api/types.ts`。

第一版手工维护少量公开 schema，避免现在引入 OpenAPI code generator：

```typescript
export type JobStatus =
  | "queued"
  | "running"
  | "waiting_for_input"
  | "cancelling"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "reconciliation_required";

export type PublicInterrupt = {
  node: string;
  interrupt_id: string | null;
  value_preview: unknown;
};

export type AllowedOperation = {
  operation_id: string;
  kind: "submit_decision" | "cancel" | "operator_reconciliation_required";
  endpoint: string | null;
  decision_kind:
    | "command_selection"
    | "action_approval"
    | "patch_review"
    | "patch_promotion"
    | null;
  expected_node: string | null;
  expected_job_version: number;
  expected_wait_generation: number | null;
  allowed_decisions: string[];
  requires_idempotency_key: boolean;
  detail: string | null;
};

export type JobView = {
  job_id: string;
  thread_id: string;
  run_id: string;
  status: JobStatus;
  version: number;
  attempt_count: number;
  max_attempts: number;
  wait_generation: number;
  interrupts: PublicInterrupt[];
  cancel_requested: boolean;
  cancellation_reason: string | null;
  result: {
    final_status: string | null;
    stage_error_count: number | null;
    output_file_count: number | null;
  } | null;
  error: unknown;
  reconciliation: unknown;
  input: {
    paper_name: string;
    repo_name: string;
    experiment_goal: string;
    execution_profile_id: string;
  };
  allowed_operations: AllowedOperation[];
  created_at: string;
  updated_at: string;
};

export type TimelineItem = {
  item_id: string;
  role: "user" | "assistant" | "system";
  kind: "request" | "progress" | "decision" | "result" | "error";
  title: string;
  content: string;
  created_at: string;
  event_id: number | null;
  operation: AllowedOperation | null;
  interrupt: PublicInterrupt | null;
};

export type TimelineResponse = {
  job: JobView;
  items: TimelineItem[];
  last_event_id: number;
};

export type ArtifactView = {
  artifact_id: string;
  relative_path: string;
  media_type: string;
  sha256: string;
  size_bytes: number;
  producer_node: string;
  created_at: string;
};

export type ResourceView = {
  resource_id: string;
  kind: "paper_pdf" | "git_repository" | "checkpoint";
  source_url_sanitized: string;
  purpose: string;
  expected_git_commit: string | null;
  request_sha256: string;
  status: string;
  version: number;
  manifest: Record<string, unknown> | null;
  error: unknown;
};

export type UiConfig = {
  product_name: string;
  default_execution_profile: string;
  execution_profiles: Array<{
    profile_id: string;
    backend: string;
    enforcement_mode: string;
    network_policy: string;
  }>;
};
```

后端公开 schema 改动时，前端 `typecheck + API contract tests` 必须一起更新。

---

## 二十、实现 API Client

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/api/client.ts`。

```typescript
import type {
  AllowedOperation,
  ArtifactView,
  JobView,
  ResourceView,
  TimelineResponse,
  UiConfig,
} from "./types";

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail ?? payload;
    throw new ApiClientError(
      detail?.message ?? `Request failed: ${response.status}`,
      response.status,
      detail?.code ?? "HTTP_ERROR",
    );
  }
  return response.json() as Promise<T>;
}

function mutationHeaders(): HeadersInit {
  return { "Idempotency-Key": crypto.randomUUID() };
}

export const api = {
  async config() {
    return request<UiConfig>("/v1/ui/config");
  },

  async listJobs(): Promise<JobView[]> {
    const result = await request<{ items: JobView[] }>("/v1/jobs?limit=100");
    return result.items;
  },

  timeline(jobId: string) {
    return request<TimelineResponse>(
      `/v1/ui/jobs/${encodeURIComponent(jobId)}/timeline`,
    );
  },

  async createJob(input: {
    paperResourceId: string;
    repoResourceId: string;
    experimentGoal: string;
    executionProfileId: string;
  }): Promise<JobView> {
    const result = await request<{ job: JobView }>("/v1/jobs", {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({
        paper_resource_id: input.paperResourceId,
        repo_resource_id: input.repoResourceId,
        experiment_goal: input.experimentGoal,
        execution_profile_id: input.executionProfileId,
      }),
    });
    return result.job;
  },

  createResource(input: {
    kind: "paper_pdf" | "git_repository";
    sourceUrl: string;
    expectedGitCommit?: string;
    purpose: string;
  }) {
    return request<{ resource: ResourceView }>("/v1/resources", {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({
        kind: input.kind,
        source_url: input.sourceUrl,
        expected_git_commit: input.expectedGitCommit ?? null,
        expected_sha256: null,
        purpose: input.purpose,
      }),
    }).then((value) => value.resource);
  },

  resource(resourceId: string) {
    return request<ResourceView>(
      `/v1/resources/${encodeURIComponent(resourceId)}`,
    );
  },

  approveResource(resource: ResourceView) {
    return request<{ resource: ResourceView }>(
      `/v1/resources/${encodeURIComponent(resource.resource_id)}/decision`,
      {
        method: "POST",
        body: JSON.stringify({
          decision: "approved",
          request_sha256: resource.request_sha256,
          expected_version: resource.version,
          reason: "approved in local Web Console",
        }),
      },
    ).then((value) => value.resource);
  },

  submitDecision(
    job: JobView,
    operation: AllowedOperation,
    decision: Record<string, unknown>,
  ) {
    return request<{ job: JobView }>(operation.endpoint!, {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({
        expected_job_version: operation.expected_job_version,
        expected_wait_generation: operation.expected_wait_generation,
        decision,
      }),
    }).then((value) => value.job);
  },

  cancel(job: JobView) {
    const operation = job.allowed_operations.find((item) => item.kind === "cancel");
    if (!operation?.endpoint) {
      throw new Error("Current job cannot be cancelled");
    }
    return request<{ job: JobView }>(operation.endpoint, {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({
        expected_job_version: operation.expected_job_version,
        reason: "cancelled from Web Console",
      }),
    }).then((value) => value.job);
  },

  async artifacts(jobId: string): Promise<ArtifactView[]> {
    const result = await request<{ items: ArtifactView[] }>(
      `/v1/jobs/${encodeURIComponent(jobId)}/artifacts`,
    );
    return result.items;
  },

  log(jobId: string) {
    return request<{ content: string; relative_path: string | null }>(
      `/v1/jobs/${encodeURIComponent(jobId)}/logs?lines=200`,
    );
  },
};
```

Resource decision endpoint 当前不要求 `Idempotency-Key`，如果你的实现已经要求，给
`approveResource()` 同样增加 `mutationHeaders()`，以真实 API contract 为准。

---

## 二十一、实现 SSE Hook

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/hooks/useJobStream.ts`。

当前 SSE 使用动态 `event: <job_event_type>`，`onmessage` 不会收到自定义 event。第一版注册已知
Job event，同时每 15 秒兜底刷新；以后可以增加固定 `job_event` stream，不必现在改协议。

```typescript
import { useEffect, useEffectEvent } from "react";

const JOB_EVENT_TYPES = [
  "job_submitted",
  "job_claimed",
  "workspace_materializing",
  "workspace_ready",
  "workspace_materialization_failed",
  "job_waiting_for_input",
  "job_resume_queued",
  "job_retry_scheduled",
  "job_lease_requeued",
  "job_cancel_requested",
  "job_succeeded",
  "job_failed",
  "job_cancelled",
  "job_reconciliation_required",
  "job_reconciliation_resolved",
  "workspace_sealed",
  "workspace_portability_blocked",
] as const;

export function useJobStream(
  jobId: string | null,
  afterEventId: number,
  refresh: () => void,
) {
  const onServerUpdate = useEffectEvent(() => {
    refresh();
  });

  useEffect(() => {
    if (!jobId) return;

    const encoded = encodeURIComponent(jobId);
    const source = new EventSource(
      `/v1/jobs/${encoded}/events/stream?after=${afterEventId}`,
    );
    const handler = () => onServerUpdate();
    for (const type of JOB_EVENT_TYPES) {
      source.addEventListener(type, handler);
    }

    // 兜底处理未来新增但前端尚未登记的事件。
    const fallback = window.setInterval(() => onServerUpdate(), 15_000);
    return () => {
      window.clearInterval(fallback);
      for (const type of JOB_EVENT_TYPES) {
        source.removeEventListener(type, handler);
      }
      source.close();
    };
  }, [jobId, afterEventId]);
}
```

`useEffectEvent` 适合让 Effect 内的连接读取最新 refresh 逻辑，而不因每次 render 重连；不要用它
隐藏真正应该触发重连的 `jobId/afterEventId`：
[React useEffectEvent](https://react.dev/reference/react/useEffectEvent)。

---

## 二十二、App 状态与刷新恢复

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/App.tsx`。

第一版不引入全局状态库。后端是事实源，React 只保存当前页面状态：

```tsx
import { startTransition, useEffect, useState } from "react";

import { api, ApiClientError } from "./api/client";
import { ConversationTimeline } from "./components/ConversationTimeline";
import { NewSessionPanel } from "./components/NewSessionPanel";
import { RunContextPanel } from "./components/RunContextPanel";
import { SessionSidebar } from "./components/SessionSidebar";
import type { JobView, TimelineResponse } from "./api/types";
import { useJobStream } from "./hooks/useJobStream";

export default function App() {
  const [jobs, setJobs] = useState<JobView[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(
    window.location.hash.slice(1) || null,
  );
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newSessionOpen, setNewSessionOpen] = useState(false);

  async function refreshJobs() {
    try {
      const next = await api.listJobs();
      startTransition(() => {
        setJobs(next);
        // 函数式更新避免闭包读到旧 selectedId。
        setSelectedId((current) => current ?? next[0]?.job_id ?? null);
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "任务列表加载失败");
    }
  }

  async function refreshTimeline() {
    if (!selectedId) return;
    try {
      const next = await api.timeline(selectedId);
      startTransition(() => setTimeline(next));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载任务失败");
    }
  }

  useEffect(() => {
    void refreshJobs();

    const restoreFromHash = () => {
      setSelectedId(window.location.hash.slice(1) || null);
    };
    window.addEventListener("hashchange", restoreFromHash);
    return () => window.removeEventListener("hashchange", restoreFromHash);
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setTimeline(null);
      return;
    }
    window.history.replaceState(null, "", `#${selectedId}`);
    setTimeline(null);
    void refreshTimeline();
  }, [selectedId]);

  useJobStream(
    selectedId,
    timeline?.job.job_id === selectedId ? timeline.last_event_id : 0,
    () => {
      void Promise.all([refreshTimeline(), refreshJobs()]);
    },
  );

  async function runMutation(action: () => Promise<unknown>) {
    try {
      await action();
      await Promise.all([refreshTimeline(), refreshJobs()]);
    } catch (caught) {
      if (caught instanceof ApiClientError && caught.status === 409) {
        await refreshTimeline();
        setError("状态已经变化，页面已刷新，请重新确认当前操作。");
        return;
      }
      setError(caught instanceof Error ? caught.message : "操作失败");
    }
  }

  return (
    <main className="workspace-shell">
      <SessionSidebar
        jobs={jobs}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onNew={() => setNewSessionOpen(true)}
      />
      <ConversationTimeline
        timeline={timeline}
        error={error}
        onMutation={runMutation}
      />
      <RunContextPanel
        job={timeline?.job ?? null}
        onMutation={runMutation}
      />
      {newSessionOpen && (
        <NewSessionPanel
          onClose={() => setNewSessionOpen(false)}
          onCreated={(job) => {
            setSelectedId(job.job_id);
            setNewSessionOpen(false);
            void refreshJobs();
          }}
        />
      )}
    </main>
  );
}
```

---

## 二十三、Session Sidebar

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/components/SessionSidebar.tsx`。

```tsx
import { useDeferredValue, useState } from "react";

import type { JobView } from "../api/types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  jobs: JobView[];
  selectedId: string | null;
  onSelect: (jobId: string) => void;
  onNew: () => void;
};

export function SessionSidebar({ jobs, selectedId, onSelect, onNew }: Props) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const visible = jobs.filter((job) =>
    [job.input.experiment_goal, job.input.paper_name, job.input.repo_name]
      .join(" ")
      .toLowerCase()
      .includes(deferredQuery),
  );

  return (
    <aside className="session-sidebar">
      <header>
        <p className="eyebrow">Research workspace</p>
        <h1>Reproduction sessions</h1>
        <button className="primary-action" onClick={onNew}>
          New session
        </button>
      </header>
      <input
        aria-label="Search sessions"
        placeholder="Search paper or goal"
        value={query}
        onChange={(event) => setQuery(event.currentTarget.value)}
      />
      <nav aria-label="Reproduction sessions">
        {visible.map((job) => (
          <button
            key={job.job_id}
            className={job.job_id === selectedId ? "session active" : "session"}
            onClick={() => onSelect(job.job_id)}
          >
            <span>{job.input.paper_name}</span>
            <small>{job.input.experiment_goal}</small>
            <StatusBadge status={job.status} />
          </button>
        ))}
      </nav>
    </aside>
  );
}
```

`useDeferredValue` 只用于让历史列表过滤不阻塞输入，不要把它用于延迟服务端状态更新。

### 23.1 Status Badge

`web/src/components/StatusBadge.tsx` 不要包含状态推导逻辑，只做稳定的文案和样式映射：

```tsx
import type { JobStatus } from "../api/types";

const LABELS: Record<JobStatus, string> = {
  queued: "Queued",
  running: "Running",
  waiting_for_input: "Needs input",
  cancelling: "Cancelling",
  succeeded: "Succeeded",
  failed: "Failed",
  cancelled: "Cancelled",
  reconciliation_required: "Operator check",
};

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span className={`status-badge status-${status}`}>
      {LABELS[status]}
    </span>
  );
}
```

---

## 二十四、Conversation Timeline

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/components/ConversationTimeline.tsx`。

```tsx
import type { TimelineResponse } from "../api/types";
import { DecisionCard } from "./DecisionCard";

type Props = {
  timeline: TimelineResponse | null;
  error: string | null;
  onMutation: (action: () => Promise<unknown>) => Promise<void>;
};

export function ConversationTimeline({ timeline, error, onMutation }: Props) {
  if (!timeline) {
    return (
      <section className="conversation empty-state">
        <p className="eyebrow">No session selected</p>
        <h2>Start with a paper and its repository.</h2>
      </section>
    );
  }

  return (
    <section className="conversation" aria-live="polite">
      <header className="conversation-header">
        <p className="eyebrow">{timeline.job.input.paper_name}</p>
        <h2>{timeline.job.input.experiment_goal}</h2>
      </header>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <ol className="timeline-list">
        {timeline.items.map((item) => (
          <li
            key={item.item_id}
            className={`timeline-item ${item.role} ${item.kind}`}
          >
            <div className="message-meta">
              <span>{item.role === "user" ? "You" : "Agent"}</span>
              <time dateTime={item.created_at}>
                {new Date(item.created_at).toLocaleString()}
              </time>
            </div>
            <article>
              <h3>{item.title}</h3>
              <p>{item.content}</p>
              {item.kind === "decision" && item.operation && (
                <DecisionCard
                  job={timeline.job}
                  item={item}
                  onMutation={onMutation}
                />
              )}
            </article>
          </li>
        ))}
      </ol>
    </section>
  );
}
```

不要用 `dangerouslySetInnerHTML` 渲染 Event、Error、Prompt 或日志。第一版全部作为文本节点。

---

## 二十五、Decision Card

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/components/DecisionCard.tsx`。

```tsx
import { useState } from "react";

import { api } from "../api/client";
import type { JobView, TimelineItem } from "../api/types";

type Props = {
  job: JobView;
  item: TimelineItem;
  onMutation: (action: () => Promise<unknown>) => Promise<void>;
};

export function DecisionCard({ job, item, onMutation }: Props) {
  const operation = item.operation!;
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(decision: Record<string, unknown>) {
    setBusy(true);
    try {
      await onMutation(() => api.submitDecision(job, operation, decision));
    } finally {
      setBusy(false);
    }
  }

  if (operation.decision_kind === "command_selection") {
    const preview = item.interrupt?.value_preview as {
      run_commands?: Array<{ command: string; cwd?: string }>;
      run_commands_hash?: string;
    } | null;
    const commands = preview?.run_commands ?? [];
    const commandsHash = preview?.run_commands_hash;
    if (!commandsHash) {
      return (
        <div className="decision-card inline-error">
          Command preview is incomplete. Refresh the session before deciding.
        </div>
      );
    }
    return (
      <div className="decision-card">
        <p>Select the command to run first.</p>
        {commands.map((command, index) => (
          <button
            key={`${index}:${command.command}`}
            disabled={busy}
            onClick={() => void submit({
              kind: "command_selection",
              selected_index: index,
              edits: [],
              run_commands_hash: commandsHash,
            })}
          >
            <code>{command.command}</code>
          </button>
        ))}
      </div>
    );
  }

  const kind = operation.decision_kind;
  if (!kind) {
    return <div className="decision-card inline-error">Unsupported decision.</div>;
  }
  const canRevise = operation.allowed_decisions.includes("revise");
  const canApprove = operation.allowed_decisions.includes("approved");
  const canReject = operation.allowed_decisions.includes("rejected");
  return (
    <div className="decision-card">
      <pre>{JSON.stringify(item.interrupt?.value_preview, null, 2)}</pre>
      <label>
        Feedback
        <textarea
          value={feedback}
          onChange={(event) => setFeedback(event.currentTarget.value)}
          maxLength={4000}
        />
      </label>
      <div className="decision-actions">
        {canApprove && (
          <button disabled={busy} onClick={() => void submit({
            kind,
            decision: "approved",
            feedback: feedback || null,
          })}>
            Approve
          </button>
        )}
        {canReject && (
          <button disabled={busy} onClick={() => void submit({
            kind,
            decision: "rejected",
            feedback: feedback || null,
          })}>
            Reject
          </button>
        )}
        {canRevise && (
          <button disabled={busy} onClick={() => void submit({
            kind,
            decision: "revise",
            feedback: feedback || null,
          })}>
            Request revision
          </button>
        )}
      </div>
    </div>
  );
}
```

第一版 command selection 先支持“选择但不编辑”。第二个小迭代再为每条命令增加 textarea 并只提交
变化项 `CommandEdit`；不要因为前端尚未支持 edits 就绕过服务端 hash。

---

## 二十六、Resource Wizard 与 New Session

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/components/ResourceWizard.tsx`、
> `web/src/components/NewSessionPanel.tsx`。

向导只需要四步：

```text
1. 输入 PDF HTTPS URL、Git HTTPS URL、exact commit
2. 创建两个 Resource，展示 canonical URL 与 request SHA-256
3. 用户分别点击 Approve，轮询到 published
4. 输入实验目标和 execution profile，创建 Job
```

`web/src/components/ResourceWizard.tsx`：

```tsx
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import type { ResourceView } from "../api/types";

export type PublishedResourcePair = {
  paper: ResourceView;
  repository: ResourceView;
};

type ResourcePair = {
  paper: ResourceView | null;
  repository: ResourceView | null;
};

const TERMINAL_RESOURCE_FAILURES = new Set([
  "rejected",
  "cancelled",
  "failed_terminal",
  "reconciliation_required",
]);

// 轮询仅用于 Resource；Job 状态仍使用 SSE。导出该函数便于单测。
export async function waitUntilPublished(
  resourceId: string,
  signal: AbortSignal,
  onUpdate: (resource: ResourceView) => void,
): Promise<ResourceView> {
  while (!signal.aborted) {
    const current = await api.resource(resourceId);
    onUpdate(current);
    if (current.status === "published") return current;
    if (TERMINAL_RESOURCE_FAILURES.has(current.status)) {
      throw new Error(`Resource stopped in status: ${current.status}`);
    }
    await new Promise<void>((resolve, reject) => {
      const onAbort = () => {
        window.clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      };
      const timer = window.setTimeout(() => {
        signal.removeEventListener("abort", onAbort);
        resolve();
      }, 1000);
      signal.addEventListener("abort", onAbort, { once: true });
    });
  }
  throw new DOMException("Aborted", "AbortError");
}

type Props = {
  onReady: (resources: PublishedResourcePair) => void;
};

export function ResourceWizard({ onReady }: Props) {
  const [paperUrl, setPaperUrl] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [commitSha, setCommitSha] = useState("");
  const [resources, setResources] = useState<ResourcePair>({
    paper: null,
    repository: null,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(new AbortController());

  useEffect(() => () => abortRef.current.abort(), []);

  function updateResource(resource: ResourceView) {
    setResources((current) => ({
      ...current,
      [resource.kind === "paper_pdf" ? "paper" : "repository"]: resource,
    }));
  }

  async function createResources(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      // 先显示规范化 URL 与 request hash，创建时绝不自动批准。
      // 第二个请求失败后重试时，复用已创建的 paper resource，
      // 不因部分失败重复生成资源请求。
      if (!resources.paper) {
        const paper = await api.createResource({
          kind: "paper_pdf",
          sourceUrl: paperUrl,
          purpose: "paper input for Web Console reproduction session",
        });
        updateResource(paper);
      }

      if (!resources.repository) {
        const repository = await api.createResource({
          kind: "git_repository",
          sourceUrl: repoUrl,
          expectedGitCommit: commitSha.trim().toLowerCase(),
          purpose: "repository input for Web Console reproduction session",
        });
        updateResource(repository);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Resource 创建失败");
    } finally {
      setBusy(false);
    }
  }

  async function approveAndWait(resource: ResourceView) {
    setBusy(true);
    setError(null);
    try {
      const approved = await api.approveResource(resource);
      updateResource(approved);
      const published = await waitUntilPublished(
        approved.resource_id,
        abortRef.current.signal,
        updateResource,
      );
      updateResource(published);
    } catch (caught) {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) {
        setError(caught instanceof Error ? caught.message : "Resource 获取失败");
      }
    } finally {
      setBusy(false);
    }
  }

  const published =
    resources.paper?.status === "published" &&
    resources.repository?.status === "published";

  return (
    <section className="resource-wizard">
      {!resources.paper || !resources.repository ? (
        <form onSubmit={createResources}>
          <label>
            Paper PDF HTTPS URL
            <input
              type="url"
              required
              value={paperUrl}
              onChange={(event) => setPaperUrl(event.currentTarget.value)}
            />
          </label>
          <label>
            Git repository HTTPS URL
            <input
              type="url"
              required
              value={repoUrl}
              onChange={(event) => setRepoUrl(event.currentTarget.value)}
            />
          </label>
          <label>
            Exact commit SHA
            <input
              required
              minLength={40}
              maxLength={64}
              pattern="[0-9a-fA-F]{40,64}"
              value={commitSha}
              onChange={(event) => setCommitSha(event.currentTarget.value)}
            />
          </label>
          <button className="primary-action" disabled={busy} type="submit">
            Create acquisition requests
          </button>
        </form>
      ) : null}

      {([resources.paper, resources.repository].filter(Boolean) as ResourceView[])
        .map((resource) => (
          <article className="resource-card" key={resource.resource_id}>
            <strong>{resource.kind}</strong>
            <p>{resource.source_url_sanitized}</p>
            {resource.expected_git_commit && <code>{resource.expected_git_commit}</code>}
            <small>Request SHA-256</small>
            <code>{resource.request_sha256}</code>
            <p>Status: {resource.status}</p>
            {resource.status === "awaiting_approval" && (
              <button disabled={busy} onClick={() => void approveAndWait(resource)}>
                Approve this exact request
              </button>
            )}
          </article>
        ))}

      {error && <p className="inline-error" role="alert">{error}</p>}
      {published && (
        <button
          className="primary-action"
          onClick={() => onReady({
            paper: resources.paper!,
            repository: resources.repository!,
          })}
        >
          Continue with published resources
        </button>
      )}
    </section>
  );
}
```

`web/src/components/NewSessionPanel.tsx`：

```tsx
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import type { JobView, UiConfig } from "../api/types";
import {
  ResourceWizard,
  type PublishedResourcePair,
} from "./ResourceWizard";

type Props = {
  onClose: () => void;
  onCreated: (job: JobView) => void;
};

export function NewSessionPanel({ onClose, onCreated }: Props) {
  const [config, setConfig] = useState<UiConfig | null>(null);
  const [resources, setResources] = useState<PublishedResourcePair | null>(null);
  const [goal, setGoal] = useState("复现论文 main result");
  const [profileId, setProfileId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.config()
      .then((value) => {
        setConfig(value);
        setProfileId(value.default_execution_profile);
      })
      .catch((caught) => {
        setError(caught instanceof Error ? caught.message : "配置加载失败");
      });
  }, []);

  async function createJob(event: FormEvent) {
    event.preventDefault();
    if (!resources || !profileId) return;
    setBusy(true);
    setError(null);
    try {
      const job = await api.createJob({
        paperResourceId: resources.paper.resource_id,
        repoResourceId: resources.repository.resource_id,
        experimentGoal: goal.trim(),
        executionProfileId: profileId,
      });
      onCreated(job);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Job 创建失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section className="new-session-panel" role="dialog" aria-modal="true">
        <header>
          <div>
            <p className="eyebrow">New reproduction session</p>
            <h2>Fix inputs before the agent starts</h2>
          </div>
          <button aria-label="Close" onClick={onClose}>Close</button>
        </header>

        {!resources ? (
          <ResourceWizard onReady={setResources} />
        ) : (
          <form onSubmit={createJob}>
            <p>
              Inputs published: {resources.paper.resource_id} / {resources.repository.resource_id}
            </p>
            <label>
              Experiment goal
              <textarea
                required
                maxLength={4000}
                value={goal}
                onChange={(event) => setGoal(event.currentTarget.value)}
              />
            </label>
            <label>
              Execution profile
              <select
                required
                value={profileId}
                onChange={(event) => setProfileId(event.currentTarget.value)}
              >
                {config?.execution_profiles.map((profile) => (
                  <option key={profile.profile_id} value={profile.profile_id}>
                    {profile.profile_id} / {profile.backend} / {profile.network_policy}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary-action" disabled={busy || !config} type="submit">
              Create session
            </button>
          </form>
        )}
        {error && <p className="inline-error" role="alert">{error}</p>}
      </section>
    </div>
  );
}
```

这个 MVP 不保存尚未建立 Job 的表单 draft。如果页面在 Resource 已创建但 Job 尚未创建时
刷新，先通过 Resource CLI/API 找回 ID；真实使用证明这是高频问题后，再增加只保存公开
`resource_id` 的 localStorage draft。

---

## 二十七、Run Context Panel

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/components/RunContextPanel.tsx`。

右侧只在用户打开对应 tab 时请求数据：

```text
Overview：状态、attempt、profile、paper/repo
Artifacts：公开 Artifact 列表和下载链接
Logs：最近 200 行，每 2 秒刷新；Job terminal 后停止
```

```tsx
import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { ArtifactView, JobStatus, JobView } from "../api/types";
import { StatusBadge } from "./StatusBadge";

type Tab = "overview" | "artifacts" | "logs";

const ACTIVE_STATUSES = new Set<JobStatus>([
  "queued",
  "running",
  "waiting_for_input",
  "cancelling",
]);

type Props = {
  job: JobView | null;
  onMutation: (action: () => Promise<unknown>) => Promise<void>;
};

export function RunContextPanel({ job, onMutation }: Props) {
  const [tab, setTab] = useState<Tab>("overview");
  const [artifacts, setArtifacts] = useState<ArtifactView[]>([]);
  const [log, setLog] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job || tab !== "artifacts") return;
    let disposed = false;
    void api.artifacts(job.job_id)
      .then((items) => {
        if (!disposed) setArtifacts(items);
      })
      .catch((caught) => {
        if (!disposed) setError(caught instanceof Error ? caught.message : "Artifact 加载失败");
      });
    return () => {
      disposed = true;
    };
  }, [job?.job_id, tab]);

  useEffect(() => {
    if (!job || tab !== "logs") return;
    let disposed = false;
    async function refreshLog() {
      try {
        const result = await api.log(job.job_id);
        if (!disposed) setLog(result.content);
      } catch (caught) {
        if (!disposed) setError(caught instanceof Error ? caught.message : "日志加载失败");
      }
    }

    void refreshLog();
    const timer = ACTIVE_STATUSES.has(job.status)
      ? window.setInterval(() => void refreshLog(), 2000)
      : null;
    return () => {
      disposed = true;
      if (timer !== null) window.clearInterval(timer);
    };
  }, [job?.job_id, job?.status, tab]);

  if (!job) {
    return <aside className="run-context"><p>Select a session.</p></aside>;
  }

  const canCancel = job.allowed_operations.some((item) => item.kind === "cancel");
  const operatorOperation = job.allowed_operations.find(
    (item) => item.kind === "operator_reconciliation_required",
  );

  return (
    <aside className="run-context">
      <header>
        <p className="eyebrow">Run context</p>
        <StatusBadge status={job.status} />
      </header>
      <nav className="context-tabs" aria-label="Run context">
        {(["overview", "artifacts", "logs"] as Tab[]).map((name) => (
          <button key={name} aria-pressed={tab === name} onClick={() => setTab(name)}>
            {name}
          </button>
        ))}
      </nav>

      {error && <p className="inline-error" role="alert">{error}</p>}
      {tab === "overview" && (
        <dl>
          <dt>Paper</dt><dd>{job.input.paper_name}</dd>
          <dt>Repository</dt><dd>{job.input.repo_name}</dd>
          <dt>Profile</dt><dd>{job.input.execution_profile_id}</dd>
          <dt>Attempt</dt><dd>{job.attempt_count} / {job.max_attempts}</dd>
        </dl>
      )}
      {tab === "artifacts" && (
        <ul className="artifact-list">
          {artifacts.map((artifact) => (
            <li key={artifact.artifact_id}>
              <a
                href={`/v1/jobs/${encodeURIComponent(job.job_id)}/artifacts/${encodeURIComponent(
                  artifact.artifact_id,
                )}/content`}
              >
                {artifact.relative_path}
              </a>
              <small>{artifact.media_type} / {artifact.size_bytes} bytes</small>
            </li>
          ))}
        </ul>
      )}
      {tab === "logs" && <pre className="log-tail">{log || "No log output yet."}</pre>}

      {operatorOperation && <p className="operator-note">{operatorOperation.detail}</p>}
      {canCancel && (
        <button className="danger-action" onClick={() => void onMutation(() => api.cancel(job))}>
          Cancel session
        </button>
      )}
    </aside>
  );
}
```

日志必须使用 `<pre>` 的文本内容，不使用 HTML。Cancel 按钮同样来自
`allowed_operations`；`reconciliation_required` 只显示服务端给出的运维提示，不在浏览器
提供危险的强制 requeue。

---

## 二十八、样式与响应式布局

> **本节类型：需要新增前端代码。**
>
> 新增：`web/src/styles/tokens.css`、`web/src/styles/app.css`。

`tokens.css`：

```css
@import "@fontsource-variable/newsreader";
@import "@fontsource-variable/manrope";

:root {
  --paper: #f3efe5;
  --paper-raised: #fffdf7;
  --ink: #18221f;
  --ink-muted: #65706a;
  --line: #d7d1c2;
  --signal: #d85f35;
  --signal-dark: #9f3f22;
  --moss: #3d6f58;
  --amber: #b87a22;
  --brick: #a13e32;
  --shadow: 0 18px 50px rgb(42 34 22 / 10%);
  font-family: "Manrope Variable", sans-serif;
  color: var(--ink);
  background: var(--paper);
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  background:
    radial-gradient(circle at 82% 12%, rgb(216 95 53 / 12%), transparent 28rem),
    linear-gradient(rgb(24 34 31 / 3%) 1px, transparent 1px),
    linear-gradient(90deg, rgb(24 34 31 / 3%) 1px, transparent 1px),
    var(--paper);
  background-size: auto, 32px 32px, 32px 32px, auto;
}

h1,
h2,
h3 {
  font-family: "Newsreader Variable", serif;
  font-weight: 520;
  letter-spacing: -0.025em;
}

button,
input,
textarea,
select {
  font: inherit;
}
```

`app.css` 核心布局：

```css
.workspace-shell {
  display: grid;
  grid-template-columns: 18rem minmax(28rem, 1fr) 21rem;
  min-height: 100vh;
}

.session-sidebar,
.run-context {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
  box-sizing: border-box;
  padding: 1.4rem;
  background: rgb(255 253 247 / 78%);
  backdrop-filter: blur(18px);
}

.session-sidebar {
  border-right: 1px solid var(--line);
}

.run-context {
  border-left: 1px solid var(--line);
}

.conversation {
  width: min(52rem, calc(100% - 3rem));
  margin: 0 auto;
  padding: 3rem 0 8rem;
}

.timeline-item {
  list-style: none;
  margin: 0 0 1.25rem;
  animation: item-in 240ms ease-out both;
}

.timeline-item article {
  border: 1px solid var(--line);
  border-radius: 1.1rem;
  padding: 1rem 1.15rem;
  background: var(--paper-raised);
  box-shadow: var(--shadow);
}

.timeline-item.user article {
  margin-left: 12%;
  border-color: rgb(216 95 53 / 45%);
}

.timeline-item.decision article {
  border-left: 4px solid var(--amber);
}

.timeline-item.error article {
  border-left: 4px solid var(--brick);
}

.eyebrow {
  margin: 0 0 0.35rem;
  color: var(--signal-dark);
  font-size: 0.72rem;
  font-weight: 750;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.session,
.decision-card button,
.context-tabs button,
.primary-action,
.danger-action {
  border: 1px solid var(--line);
  border-radius: 0.75rem;
  padding: 0.65rem 0.8rem;
  color: inherit;
  background: var(--paper-raised);
  cursor: pointer;
}

.primary-action {
  color: white;
  border-color: var(--signal);
  background: var(--signal);
}

.danger-action {
  color: white;
  border-color: var(--brick);
  background: var(--brick);
}

input,
textarea,
select {
  width: 100%;
  box-sizing: border-box;
  margin: 0.3rem 0 0.9rem;
  border: 1px solid var(--line);
  border-radius: 0.7rem;
  padding: 0.7rem;
  color: var(--ink);
  background: var(--paper-raised);
}

.status-badge {
  display: inline-flex;
  width: fit-content;
  border-radius: 999px;
  padding: 0.2rem 0.5rem;
  color: var(--ink-muted);
  background: rgb(101 112 106 / 12%);
  font-size: 0.72rem;
}

.status-running,
.status-queued { color: var(--moss); }
.status-waiting_for_input { color: var(--amber); }
.status-failed,
.status-reconciliation_required { color: var(--brick); }

.dialog-backdrop {
  position: fixed;
  z-index: 10;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgb(24 34 31 / 48%);
}

.new-session-panel {
  width: min(46rem, 100%);
  max-height: calc(100vh - 2rem);
  overflow: auto;
  border-radius: 1.2rem;
  padding: 1.4rem;
  background: var(--paper-raised);
  box-shadow: var(--shadow);
}

.new-session-panel > header,
.run-context > header,
.message-meta,
.decision-actions,
.context-tabs {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}

.resource-card,
.decision-card,
.operator-note {
  margin-top: 0.8rem;
  border: 1px solid var(--line);
  border-radius: 0.85rem;
  padding: 0.8rem;
  overflow-wrap: anywhere;
}

.log-tail,
.decision-card pre {
  max-height: 28rem;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.78rem;
}

.inline-error {
  border-left: 3px solid var(--brick);
  padding: 0.6rem 0.8rem;
  color: var(--brick);
  background: rgb(161 62 50 / 8%);
}

@keyframes item-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 980px) {
  .workspace-shell {
    grid-template-columns: 15rem minmax(0, 1fr);
  }
  .run-context {
    position: fixed;
    inset: auto 0 0 0;
    width: 100%;
    height: min(55vh, 32rem);
    border: 1px solid var(--line);
  }
}

@media (max-width: 700px) {
  .workspace-shell { display: block; }
  .session-sidebar {
    position: static;
    width: 100%;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
  .conversation {
    width: min(100% - 2rem, 42rem);
    padding-top: 1.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 二十九、前端测试

> **本节类型：需要新增前端测试。**

`web/tests/timeline.test.tsx` 先覆盖纯渲染与搜索两个关键路径：

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConversationTimeline } from "../src/components/ConversationTimeline";
import { SessionSidebar } from "../src/components/SessionSidebar";
import type { JobView, TimelineResponse } from "../src/api/types";

const job: JobView = {
  job_id: "job-1",
  thread_id: "thread-1",
  run_id: "run-1",
  status: "running",
  version: 1,
  attempt_count: 1,
  max_attempts: 3,
  wait_generation: 0,
  interrupts: [],
  cancel_requested: false,
  cancellation_reason: null,
  result: null,
  error: null,
  reconciliation: null,
  input: {
    paper_name: "PSTNet.pdf",
    repo_name: "PST-Convolution",
    experiment_goal: "reproduce main result",
    execution_profile_id: "local",
  },
  allowed_operations: [],
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:01:00Z",
};

describe("conversation projection", () => {
  it("renders timeline content as text", () => {
    const timeline: TimelineResponse = {
      job,
      last_event_id: 1,
      items: [{
        item_id: "event:1",
        role: "assistant",
        kind: "progress",
        title: "Workspace ready",
        content: "Agent started analysis.",
        created_at: "2026-08-01T00:00:10Z",
        event_id: 1,
        operation: null,
        interrupt: null,
      }],
    };

    render(
      <ConversationTimeline
        timeline={timeline}
        error={null}
        onMutation={async () => undefined}
      />,
    );

    expect(screen.getByText("Workspace ready")).toBeTruthy();
    expect(screen.getByText("Agent started analysis.")).toBeTruthy();
  });

  it("filters session history without changing server state", () => {
    const second = {
      ...job,
      job_id: "job-2",
      input: {
        ...job.input,
        paper_name: "Other.pdf",
        experiment_goal: "different target",
      },
    };
    render(
      <SessionSidebar
        jobs={[job, second]}
        selectedId="job-1"
        onSelect={() => undefined}
        onNew={() => undefined}
      />,
    );

    fireEvent.change(screen.getByLabelText("Search sessions"), {
      target: { value: "PSTNet" },
    });

    expect(screen.getByText("PSTNet.pdf")).toBeTruthy();
    expect(screen.queryByText("Other.pdf")).toBeNull();
  });
});
```

在这个最小文件通过后，再依次补下列边界，不需要引入端到端浏览器框架：

```text
DecisionCard 只渲染 allowed operation
409 后触发 refresh，不重复提交旧 operation
Resource terminal failure 停止 polling
组件卸载时关闭 EventSource 和 timer
日志内容按文本渲染
```

运行：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot/web
npm run typecheck
npm test
npm run build
```

Vite 只转译 TypeScript，不代替完整类型检查，所以 `build` script 中显式执行 `tsc --noEmit`。

---

## 三十、本地开发运行

> **本节类型：运行步骤，不修改项目代码。**

终端 1：API。

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m app.main serve-api --host 127.0.0.1 --port 8000
```

终端 2：Job Worker。

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m app.main run-worker
```

终端 3：Resource Worker。在完成 `run_forever` CLI 接线前，可以重复 `--once`；完成后使用持续模式。

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m app.main run-resource-worker
```

终端 4：Vite。

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot/web
npm run dev
```

浏览器打开：

```text
http://127.0.0.1:5173
```

---

## 三十一、单命令部署

> **本节类型：部署步骤，不修改项目代码。**

### 31.1 准备生产前端

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot/web
npm ci
npm run build
```

Vite 默认生成 `web/dist/`，生产不运行 Node server。

### 31.2 生产配置

项目根目录 `.env`：

```dotenv
AGENT_API_HOST=127.0.0.1
AGENT_API_PORT=8000
AGENT_API_TOKEN=
WEB_DIST_DIR=/data/tianshaoqi24/agent/paper_reproduction_copilot/web/dist
WEB_UI_REQUIRED=true

JOB_STORE_BACKEND=sqlite
ARTIFACT_BLOB_BACKEND=local
RESOURCE_POLL_SECONDS=1

RUNS_DIR=/data/tianshaoqi24/agent/paper_reproduction_copilot/runs
WORKER_WORKSPACE_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces
WORKSPACE_STAGING_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/workspace_staging
RESOURCE_STAGING_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/resources/.staging
RESOURCE_MATERIALIZED_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/resources/materialized
```

Provider key 和其他 secret 仍由环境注入，不写入版本控制。

### 31.3 启动

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m app.main serve-stack --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

### 31.4 远程访问

在自己的电脑执行：

```bash
ssh -N -L 8000:127.0.0.1:8000 <user>@<server>
```

然后本机浏览器打开 `http://127.0.0.1:8000`。API 在服务器上仍只监听 loopback，不需要本阶段
实现公网认证。

---

## 三十二、完整验证顺序

> **本节类型：验证步骤，不修改项目代码。**

### 32.1 后端新增测试

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
mkdir -p .pytest-tmp
python -m pytest -q \
  --basetemp=.pytest-tmp/phase30 \
  tests/test_timeline_projection.py \
  tests/test_ui_api.py \
  tests/test_web_static.py \
  tests/test_service_host.py
```

### 32.2 交互与资源回归

```bash
python -m pytest -q \
  --basetemp=.pytest-tmp/phase30-regression \
  tests/test_interaction_api.py \
  tests/test_interaction_policy.py \
  tests/test_interaction_sse.py \
  tests/test_interaction_artifacts.py \
  tests/test_resource_api.py \
  tests/test_resource_job_submission.py \
  tests/test_job_worker.py
```

### 32.3 前端

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot/web
npm run typecheck
npm test
npm run build
```

### 32.4 静态与 Python 检查

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m compileall -q app tests
ruff check app tests
```

### 32.5 全量离线回归

```bash
python -m pytest -q \
  -m 'not provider and not postgres and not container_runtime and not network' \
  --basetemp=.pytest-tmp/phase30-all
```

---

## 三十三、手工端到端验收

> **本节类型：手工操作，不修改项目代码。**

### 33.1 启动与恢复

1. 构建 `web/dist`；
2. 启动 `serve-stack`；
3. 检查 `/livez` 和 `/readyz`；
4. 打开首页，确认 UI config 和 Job history 正常；
5. 刷新页面，确认选中的 `job_id` 可以从 URL hash 恢复。

### 33.2 Resource wizard

1. 输入 allowlist 内的 PDF HTTPS URL；
2. 输入 Git HTTPS URL 和完整 commit SHA；
3. 创建 Resource；
4. 检查页面展示 canonical URL 与 request hash；
5. 点击批准；
6. 确认 Resource 状态进入 queued/fetching/validating/published；
7. 确认两个 Resource 都 published 之前无法创建 Job。

### 33.3 对话任务

1. 输入自然语言实验目标；
2. 选择 execution profile；
3. 创建 Job；
4. 确认左侧出现新 session；
5. 确认中间 timeline 随 SSE 更新；
6. 在 command selection 卡片选择命令；
7. 在 action approval 卡片批准或拒绝；
8. 检查 409 stale version 会刷新而不是重复提交；
9. 查看日志和 Artifact；
10. 任务 terminal 后刷新浏览器，确认结果仍在。

### 33.4 安全边界

1. 浏览器响应中没有 run_dir、claim token、assignment token 和 object key；
2. 页面源码中没有 Provider key 或 `AGENT_API_TOKEN`；
3. Artifact 只能通过公开 content endpoint 下载；
4. `reconciliation_required` 只显示运维提示；
5. API 只监听 `127.0.0.1`；
6. SSH tunnel 关闭后远程访问立即结束；
7. EventSource 断线后能重连，组件切换 Job 后旧连接被关闭。

---

## 三十四、常见问题

> **本节类型：问题排查，不修改项目代码。**

### 34.1 首页 404 或只返回 API JSON

检查 `WEB_DIST_DIR` 是否指向真实 `web/dist`，并确认执行过 `npm run build`。生产不要使用
`vite preview`。

### 34.2 `/v1` 被前端 index.html 吞掉

Static mount 注册得太早。必须先 include API routers、error handlers，最后 mount `/`。

### 34.3 SSE 一直 401

Phase 30 只支持 loopback 无 token。如果配置了 `AGENT_API_TOKEN`，原生 EventSource 无法添加
Bearer header。不要把 token 放 query；取消 token 并保持 loopback/SSH tunnel，或以后实现 HttpOnly
session cookie。

### 34.4 SSE 已连接但页面不更新

当前服务发送自定义 event type，不能只写 `source.onmessage`。为已知类型注册
`addEventListener(type, handler)`，并保留低频刷新兜底。

### 34.5 Resource Job 查询报 `Path(None)`

说明第八节公开名称修复未完成。Resource 输入应显示公开 resource identity，不依赖本地 path。

### 34.6 每个 Job 都产生新 HTTP metric series

middleware 仍在使用 `request.url.path`。改用路由模板 `/v1/jobs/{job_id}`。

### 34.7 `serve-stack` 启动了两个相同 Job Worker

不要同时运行独立 `run-worker` 和 `serve-stack`。单用户部署只保留一个 Stack Host。

### 34.8 浏览器刷新后资源向导丢失

这是 Phase 30 MVP 的明确限制，不影响已创建 Job 的恢复。先通过 Resource CLI/API 查回
`resource_id`；只有它成为高频问题时，才按第二十六节说明增加仅保存公开 ID 的
localStorage draft，不保存 secret。

---

## 三十五、本阶段 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 35.1 Conversational UX 不要求新的 Agent 状态机

已有 Job Event、Interrupt 和 AllowedOperation 已经表达了对话事实。前端把它们投影成消息，比再建
一套 ChatHistory 更可靠。

### 35.2 UI 应消费 capability，而不是复制 policy

前端不根据 `status/node` 猜按钮，而是渲染服务端 `allowed_operations`。这样 stale version、审批
类型和危险恢复仍由后端控制。

### 35.3 流式界面不等于流式生成

SSE 推送的是持久业务事件，不是未落盘 token。页面断线后可以根据 Event ID 和 Job Store 恢复。

### 35.4 后端仍是事实源

浏览器 state 只是缓存。刷新后从 Job、Timeline、Artifact API 重建，避免“页面显示成功但数据库
仍 running”的双重真相。

### 35.5 产品闭环优先于继续堆基础设施

只有真实使用界面后，才知道最需要的是上传、搜索、结果比较还是多用户。先完成使用闭环，可以
避免凭想象引入 Redis、Kubernetes 或复杂 Agent memory。

---

## 三十六、完成标准

> **本节类型：最终验收，不修改项目代码。**

- Resource-only Job 的公开投影不再依赖本地 path；
- HTTP metrics 使用 route template；
- timeline 是 Job/Event/Operation 的确定性投影；
- Web Console 能创建资源、批准资源和创建 Job；
- 全部现有人工决策可以在对话卡片完成；
- SSE 更新、断线重连和轮询兜底正常；
- Job history、timeline、日志和 Artifact 可以在刷新后恢复；
- Vite build 由 FastAPI 同源托管；
- `serve-stack` 可以同时运行 API、Job Worker 和 Resource Worker；
- 只监听 loopback，SSH tunnel 可远程使用；
- 前后端测试、类型检查、build 和原 API 回归通过；
- 前端不包含 secret、内部路径或危险运维操作；
- 没有引入多用户、Redis、WebSocket、Kubernetes 或通用聊天复杂度。

---

## 三十七、完成 Phase 30 后先做什么

Phase 30 完成后，不建议立即写一个更大的基础设施阶段。先用 2 到 3 篇论文完整走几遍界面，
记录真实摩擦点，再从下面的小功能中选一个：

```text
P1 受控文件上传：用户只有本地 PDF/仓库压缩包时使用
P1 Post-run Q&A：只对当前 Job 的 Artifact 做有引用回答
P1 前端命令编辑：补齐 CommandEdit 可视化
P2 结果指标提取与比较：恢复论文复现产品价值主线
P2 单用户 HttpOnly session：确实需要直接暴露到局域网时再做
P3 多用户/RBAC：出现真实多人协作需求后再做
```

当前最重要的目标不是再证明系统“能扩展”，而是让它成为一个你可以每天打开、提交任务、完成
审批、观察进度并拿到产物的完整应用。
