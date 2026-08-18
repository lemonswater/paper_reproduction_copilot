# 34. Phase 23：统一任务交互 API、Decision Protocol 与 Event Stream

这一阶段建立在 Phase 22 已完成的异步 Job Runtime 之上。目标不是立刻把
SQLite、Checkpoint 和 Artifact 全部替换成 MySQL、Redis 或消息队列，而是先把
任务提交、查询、人工决策、取消、事件、日志和 Artifact 访问整理成稳定的服务
协议。

> **本教程中的源码均为待实现代码。**
>
> 除了明确标记为“知识说明”的小节，其余小节都会指出需要新增或修改的文件。
> 你仍然自己修改项目源码；本教程不会直接改动 `app/` 和 `tests/`。

---

## 一、先回答优先级问题

> **本节类型：架构决策说明，不修改项目代码。**

当前更应该优先完成：

```text
Phase 23：
统一任务交互 API
+ Decision Protocol
+ Event Stream
+ Artifact ID 访问
```

而不是直接引入：

```text
MySQL / PostgreSQL
Redis
RabbitMQ / Kafka / RocketMQ
```

这不是因为数据库和中间件不重要，而是因为它们分别只解决整个问题的一部分。

### 1.1 MySQL 不能代替 Artifact 存储

关系数据库适合保存：

```text
Job 元数据
状态机
版本号
幂等记录
事件索引
租约和 worker ownership
```

但它不适合直接保存大量：

```text
PDF
运行日志
模型输出
训练 checkpoint
补丁文件
实验结果
图片和压缩包
```

即使把这些内容放入 `BLOB`，通常也会增加数据库备份、复制、清理和传输成本。
Artifact 更适合放在 S3、MinIO 或其他对象存储中。

### 1.2 Redis 不应成为任务事实的唯一来源

Redis 很适合：

```text
短期缓存
分布式锁
速率限制
Pub/Sub
Streams
短生命周期队列
```

但 Job 的最终状态、审批结果、执行记录和 Artifact 元数据需要可审计、可恢复的
持久化事实。除非专门设计 Redis 持久化和恢复策略，否则不能把它当作唯一真相。

### 1.3 消息队列不负责保存业务状态

消息队列解决的是：

```text
谁来消费任务
如何削峰
如何重试投递
如何跨主机分发
```

它并不会自动解决：

```text
Job 当前状态是什么
审批是否过期
Artifact 在哪里
外部副作用是否已经发生
worker 崩溃后是否允许重放
```

“消息被消费一次”也不等于“业务副作用 exactly-once”。Phase 22 已经建立的
lease、fencing token、idempotency 和 reconciliation 仍然必须保留。

### 1.4 现在先定义协议，后面才能安全换后端

如果现在直接把源码中的 `Path`、SQLite SQL 和 Redis key 暴露给 Web/CLI，之后
每换一次存储，Graph、CLI、API 和前端都需要一起修改。

正确顺序是：

```text
Phase 22
异步 Job Runtime
    ↓
Phase 23
稳定任务 API、Decision、Event cursor、Artifact ID
    ↓
Phase 24
JobRepository / ArtifactStore / CheckpointBackend / EventBus 抽象
    ↓
Phase 25
按真实部署需求接入关系库、对象存储和可选消息中间件
```

这样调用方只认识：

```text
job_id
artifact_id
event_id
expected_job_version
expected_wait_generation
idempotency_key
```

而不认识：

```text
runs/xxx/...
jobs/runtime.sqlite
Redis key
对象存储 bucket 内部路径
worker claim_token
```

---

## 二、本地数据其实包含四类不同事实

> **本节类型：知识说明，不修改项目代码。**

不能只用一句“都存在本地文件”概括当前数据。后续迁移前应先分类：

| 数据 | 当前实现 | 后续适合的后端 | 是否由 Phase 23 替换 |
|---|---|---|---|
| Job 状态、事件、租约 | `jobs/runtime.sqlite` | MySQL/PostgreSQL | 否 |
| LangGraph checkpoint | `checkpoints/langgraph.sqlite` | 数据库型 Checkpointer | 否 |
| Artifact、日志、补丁、报告 | `runs/<run_id>/` | S3/MinIO | 否，但 API 不再暴露路径 |
| Embedding/抽取缓存 | 本地 SQLite 和文件 | DB、对象存储或专用向量后端 | 否 |

Phase 23 要完成的是“访问边界收口”：

```text
外部调用方
    ↓
Interaction API
    ↓
JobService / ArtifactCatalog
    ↓
当前 SQLite + 本地文件
```

Phase 24 再把最底层替换为接口：

```text
JobRepository
ArtifactStore
CheckpointBackend
EventBus
CacheStore
```

---

## 三、本阶段目标

> **本节类型：实现目标，不修改项目代码。**

完成后应支持：

```text
POST   /v1/jobs
GET    /v1/jobs
GET    /v1/jobs/{job_id}
GET    /v1/jobs/{job_id}/events
GET    /v1/jobs/{job_id}/events/stream
GET    /v1/jobs/{job_id}/artifacts
GET    /v1/jobs/{job_id}/artifacts/{artifact_id}/content
GET    /v1/jobs/{job_id}/logs
POST   /v1/jobs/{job_id}/decisions
POST   /v1/jobs/{job_id}/cancel
GET    /healthz
```

同时满足：

1. API 不返回 `claim_token`、`run_dir`、绝对 Artifact 路径和提交幂等 key；
2. 所有写请求都使用 `Idempotency-Key`；
3. 人工决策必须带 `expected_job_version`；
4. 人工决策必须带 `expected_wait_generation`；
5. 决策类型必须与当前 interrupt 节点匹配；
6. 过期页面不能审批新一代 interrupt；
7. Artifact 只通过 `artifact_id` 访问；
8. 下载前重新校验路径边界和 SHA-256；
9. Event Stream 使用 `event_id` 作为恢复游标；
10. API 与 CLI 共用 `JobService`，不让 API 直接写 SQL；
11. 第一版只监听 loopback；需要远程监听时必须配置 Bearer Token；
12. API 重启后 Job、事件和 Artifact 仍可查询。

---

## 四、本阶段明确不做什么

> **本节类型：范围说明，不修改项目代码。**

本阶段不做：

- 不引入 MySQL、PostgreSQL；
- 不引入 Redis；
- 不引入 RabbitMQ、Kafka、RocketMQ；
- 不把 Artifact 上传到对象存储；
- 不做多租户；
- 不做完整 RBAC；
- 不做 Web 页面；
- 不开放公网部署；
- 不提供 PDF 或代码仓库上传接口；
- 不通过 API 执行任意 shell；
- 不允许 API 传入任意日志路径或 Artifact 路径；
- 不允许远程 API 自动处理 `reconciliation_required`；
- 不把 SSE 当作可靠消息队列；
- 不承诺事件 exactly-once 到达客户端；
- 不把 `heartbeat` 冒充成业务进度百分比。

`reconciliation_required` 继续由受信任的运维 CLI 显式解决，因为它可能涉及孤儿
进程和重复外部副作用。

第一版 `POST /v1/jobs` 仍接收服务器本机可访问的 `paper_path` 和 `repo_path`，
所以它面向同机可信控制面，而不是任意互联网客户端。Phase 24 接入对象存储时，
再增加 `paper_artifact_id`、代码仓库引用或受控上传协议，并保留当前路径模式作为
本地部署兼容入口。

---

## 五、目标架构

> **本节类型：架构说明，不修改项目代码。**

```text
CLI / curl / 后续 Web
          |
          v
  FastAPI Interaction API
          |
          +--> Auth + Request ID
          |
          +--> DecisionPolicy
          |      - 当前允许什么操作
          |      - node 与 decision kind 是否匹配
          |      - version / generation 是否匹配
          |
          +--> InteractionService
                  |
                  +--> JobService
                  |      |
                  |      +--> SqliteJobStore
                  |      +--> Process cancellation bridge
                  |
                  +--> LocalArtifactCatalog
                         |
                         +--> LangGraph checkpoint
                         +--> runs/<run_id>/
```

SSE 的第一版数据流：

```text
client --Last-Event-ID--> API
API --list_events_after--> SQLite
API --id/event/data------> client
```

它使用短轮询 SQLite，而不是 Redis Pub/Sub。这样协议先稳定，Phase 24/25 只替换
`EventBus` 实现，不需要修改浏览器协议。

---

## 六、Decision Protocol 的核心语义

> **本节类型：协议说明，不修改项目代码。**

### 6.1 为什么不能只提交 `approved`

假设页面在 Job version 8 时打开：

```text
version = 8
wait_generation = 2
node = human_review
action = A
```

页面停留期间，其他客户端已经提交审批，Graph 推进后又产生新动作 B：

```text
version = 13
wait_generation = 3
node = human_review
action = B
```

旧页面如果只提交：

```json
{"decision": "approved"}
```

服务端无法判断用户批准的是 A 还是 B。

因此请求必须绑定：

```json
{
  "expected_job_version": 8,
  "expected_wait_generation": 2,
  "decision": {
    "kind": "action_approval",
    "decision": "approved",
    "feedback": null
  }
}
```

当前 Job 已经是 version 13，API 必须返回 `409 Conflict`，让客户端重新读取当前
状态。

### 6.2 两层哈希不能互相替代

本阶段的乐观并发控制：

```text
job.version
wait_generation
```

原节点已有的业务身份校验：

```text
run_commands_hash
action_hash
patch_sha256
verification_sha256
```

两者职责不同：

```text
version / generation：
    防止把旧交互提交到新的等待状态。

业务 hash：
    防止等待期间业务对象被替换。
```

两层都必须保留。

### 6.3 Decision kind 与节点映射

```text
command_selection
    -> command_selection

human_review
    -> action_approval

patch_review
    -> patch_review

patch_promotion_review
    -> patch_promotion
```

客户端不能自己指定 `expected_node`。服务端根据 `decision.kind` 和当前
`interrupt_nodes` 决定恢复哪个节点。

---

## 七、需要新增和修改的文件

> **本节类型：文件清单，不修改项目代码。**

新增：

```text
app/interaction/__init__.py
app/interaction/schemas.py
app/interaction/policy.py
app/interaction/service.py
app/interaction/artifacts.py

app/api/__init__.py
app/api/auth.py
app/api/errors.py
app/api/routes.py
app/api/app.py

tests/test_interaction_policy.py
tests/test_job_store_interaction_semantics.py
tests/test_interaction_artifacts.py
tests/test_interaction_api.py
tests/test_interaction_sse.py
```

修改：

```text
pyproject.toml
app/config.py
app/job_runtime/store.py
app/job_runtime/service.py
app/main.py
.env.example                  # 如果项目中已有
a_implementation_guides/README.md
```

不要修改：

```text
Graph 节点中的 interrupt 业务校验
Phase 16 Process Supervisor
Phase 22 Worker claim/heartbeat 主流程
现有 ArtifactRecord 的 absolute_path 字段
```

`absolute_path` 暂时仍供内部运行时使用，但 API 永远不返回它。

---

## 八、增加 API 依赖

> **本节类型：需要修改代码。**
>
> 修改：`pyproject.toml`

在 `[project.optional-dependencies]` 中增加 `api`，保留原来的 `dev`：

```toml
[project.optional-dependencies]
api = [
    "fastapi>=0.115,<1",
    "uvicorn>=0.30,<1",
    "httpx>=0.27,<1",
]

dev = [
    "pytest>=8",
    "ruff>=0.6",
]
```

这里把 API 依赖放到可选组，而不是核心依赖，原因是：

```text
只运行 worker：
    不必加载 FastAPI。

只运行旧 CLI：
    不必启动 HTTP 服务。

运行 API 测试：
    安装 api + dev。
```

安装：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent
python -m pip install -e ".[api,dev]"
```

---

## 九、增加 API 配置

> **本节类型：需要修改代码。**
>
> 修改：`app/config.py`

在 `Settings` 的 Job Runtime 配置之后增加：

```python
    # API 默认只监听本机。监听非 loopback 地址时必须配置 token。
    api_host: str = os.getenv(
        "AGENT_API_HOST",
        "127.0.0.1",
    )

    api_port: int = int(
        os.getenv(
            "AGENT_API_PORT",
            "8000",
        )
    )

    # 不设置 token 时只允许本机监听。
    # 生产环境应由 Secret Manager 或进程环境注入，不能写入仓库。
    api_token: str | None = os.getenv(
        "AGENT_API_TOKEN"
    )

    # SSE 第一版轮询 SQLite。后续可由 EventBus 替换内部实现。
    api_event_poll_seconds: float = float(
        os.getenv(
            "AGENT_API_EVENT_POLL_SECONDS",
            "0.5",
        )
    )

    # 长时间没有业务事件时发送 SSE comment，防止代理关闭空闲连接。
    api_sse_heartbeat_seconds: float = float(
        os.getenv(
            "AGENT_API_SSE_HEARTBEAT_SECONDS",
            "15",
        )
    )

    api_max_page_size: int = int(
        os.getenv(
            "AGENT_API_MAX_PAGE_SIZE",
            "100",
        )
    )

    api_max_log_bytes: int = int(
        os.getenv(
            "AGENT_API_MAX_LOG_BYTES",
            str(256 * 1024),
        )
    )
```

在文件底部已有 Job 配置校验之后增加：

```python
if not 1 <= settings.api_port <= 65535:
    raise ValueError(
        "AGENT_API_PORT 必须位于 1..65535"
    )

if settings.api_event_poll_seconds <= 0:
    raise ValueError(
        "AGENT_API_EVENT_POLL_SECONDS 必须大于 0"
    )

if settings.api_sse_heartbeat_seconds <= 0:
    raise ValueError(
        "AGENT_API_SSE_HEARTBEAT_SECONDS 必须大于 0"
    )

if settings.api_max_page_size < 1:
    raise ValueError(
        "AGENT_API_MAX_PAGE_SIZE 必须至少为 1"
    )

if settings.api_max_log_bytes < 1024:
    raise ValueError(
        "AGENT_API_MAX_LOG_BYTES 必须至少为 1024"
    )
```

如果项目存在 `.env.example`，只写变量名和安全默认值：

```dotenv
AGENT_API_HOST=127.0.0.1
AGENT_API_PORT=8000
AGENT_API_EVENT_POLL_SECONDS=0.5
AGENT_API_SSE_HEARTBEAT_SECONDS=15

# 不要提交真实 token。
# AGENT_API_TOKEN=
```

---

## 十、定义公开 API Schema

> **本节类型：需要新增代码。**
>
> 新增：`app/interaction/__init__.py`

先创建空文件：

```python
"""面向 CLI、HTTP API 和后续 Web 的统一任务交互层。"""
```

> 新增：`app/interaction/schemas.py`

完整代码：

```python
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.job_runtime.schemas import JobStatus
from app.schemas import CommandEdit


DecisionKind = Literal[
    "command_selection",
    "action_approval",
    "patch_review",
    "patch_promotion",
]

OperationKind = Literal[
    "submit_decision",
    "cancel",
    "operator_reconciliation_required",
]


class InteractionModel(BaseModel):
    """所有交互协议拒绝未知字段，避免拼错字段被静默忽略。"""

    model_config = ConfigDict(extra="forbid")


class JobCreateRequest(InteractionModel):
    """HTTP 提交体；thread_id 是运行身份，不放入 JobRequest。"""

    paper_path: str = Field(min_length=1)
    repo_path: str = Field(min_length=1)
    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    log_path: str | None = None
    experiment_goal: str = "复现论文 main result"
    execution_profile_id: str = Field(min_length=1)


class CommandSelectionDecision(InteractionModel):
    kind: Literal["command_selection"]
    selected_index: int = Field(ge=0)
    edits: list[CommandEdit] = Field(default_factory=list)
    run_commands_hash: str = Field(min_length=1)


class ActionApprovalDecision(InteractionModel):
    kind: Literal["action_approval"]
    decision: Literal["approved", "rejected", "revise"]
    feedback: str | None = Field(
        default=None,
        max_length=4000,
    )


class PatchReviewDecision(InteractionModel):
    kind: Literal["patch_review"]
    decision: Literal["approved", "rejected", "revise"]
    feedback: str | None = Field(
        default=None,
        max_length=4000,
    )


class PatchPromotionDecision(InteractionModel):
    kind: Literal["patch_promotion"]
    decision: Literal["approved", "rejected"]
    feedback: str | None = Field(
        default=None,
        max_length=4000,
    )


# discriminator 让 FastAPI/Pydantic 根据 kind 选择唯一 schema。
Decision = Annotated[
    CommandSelectionDecision
    | ActionApprovalDecision
    | PatchReviewDecision
    | PatchPromotionDecision,
    Field(discriminator="kind"),
]


class DecisionEnvelope(InteractionModel):
    """
    version 防止旧 Job 快照写入；
    wait_generation 防止旧 interrupt 输入写入新 interrupt。
    """

    expected_job_version: int = Field(ge=0)
    expected_wait_generation: int = Field(ge=1)
    decision: Decision


class CancelEnvelope(InteractionModel):
    expected_job_version: int = Field(ge=0)
    reason: str = Field(
        default="user requested cancellation",
        min_length=1,
        max_length=500,
    )


class PublicJobInput(InteractionModel):
    """
    响应只返回用户可理解的摘要。

    paper_path/repo_path/log_path 属于本机部署细节，不从 Job 查询接口返回。
    """

    paper_name: str
    repo_name: str
    experiment_goal: str
    execution_profile_id: str


class PublicInterrupt(InteractionModel):
    node: str
    interrupt_id: str | None = None
    value_preview: Any = None


class AllowedOperation(InteractionModel):
    operation_id: str
    kind: OperationKind
    endpoint: str | None = None
    decision_kind: DecisionKind | None = None
    expected_node: str | None = None
    expected_job_version: int
    expected_wait_generation: int | None = None
    allowed_decisions: list[str] = Field(
        default_factory=list
    )
    requires_idempotency_key: bool = True
    detail: str | None = None


class PublicJobResult(InteractionModel):
    final_status: str | None = None
    stage_error_count: int | None = None
    output_file_count: int | None = None


class JobView(InteractionModel):
    job_id: str
    thread_id: str
    run_id: str
    status: JobStatus
    version: int
    attempt_count: int
    max_attempts: int
    wait_generation: int
    interrupt_nodes: list[str] = Field(
        default_factory=list
    )
    interrupts: list[PublicInterrupt] = Field(
        default_factory=list
    )
    cancel_requested: bool
    cancellation_reason: str | None = None
    result: PublicJobResult | None = None
    error: Any = None
    reconciliation: Any = None
    input: PublicJobInput
    allowed_operations: list[AllowedOperation] = Field(
        default_factory=list
    )
    created_at: str
    updated_at: str


class JobMutationResponse(InteractionModel):
    job: JobView
    # submit/resume 可以精确返回是否重放；当前 cancel 兼容接口暂不返回该事实。
    replayed: bool | None = None


class JobListResponse(InteractionModel):
    items: list[JobView]
    count: int


class EventView(InteractionModel):
    event_id: int
    job_id: str
    event_type: str
    actor: str
    payload: dict[str, Any] = Field(
        default_factory=dict
    )
    created_at: str


class EventPage(InteractionModel):
    items: list[EventView]
    next_after: int


class ArtifactView(InteractionModel):
    artifact_id: str
    run_id: str
    layer: str
    relative_path: str
    media_type: str
    sha256: str
    size_bytes: int
    producer_node: str
    created_at: str
    integrity_status: Literal[
        "unchecked",
        "current",
    ] = "unchecked"


class ArtifactListResponse(InteractionModel):
    items: list[ArtifactView]
    count: int


class LogTailResponse(InteractionModel):
    relative_path: str | None = None
    content: str = ""
    lines: int
    truncated_by_bytes: bool = False


class ApiError(InteractionModel):
    code: str
    message: str
    request_id: str | None = None
```

### 10.1 为什么响应中没有 `run_dir`

`run_dir` 是 `LocalArtifactCatalog` 的内部实现。Phase 24 改成 MinIO 后，Artifact
可能根本没有本地目录。

公开协议只保留：

```text
run_id
artifact_id
relative_path
download endpoint
```

### 10.2 为什么仍然保留 `relative_path`

`relative_path` 表示 Artifact 在 run 中的逻辑位置，例如：

```text
analysis/paper_summary.json
planning/command_selection_input.json
reports/final_report.md
```

它不是服务器绝对路径，将来放入对象存储后仍可作为逻辑名称和展示名称。

---

## 十一、实现允许操作与 Decision Policy

> **本节类型：需要新增代码。**
>
> 新增：`app/interaction/policy.py`

完整代码：

```python
from __future__ import annotations

from typing import Any

from app.interaction.schemas import (
    AllowedOperation,
    Decision,
    DecisionEnvelope,
)
from app.job_runtime.schemas import JobRecord
from app.job_runtime.store import JobConflictError


NODE_TO_DECISION_KIND = {
    "command_selection": "command_selection",
    "human_review": "action_approval",
    "patch_review": "patch_review",
    "patch_promotion_review": "patch_promotion",
}

DECISION_KIND_TO_NODE = {
    value: key
    for key, value in NODE_TO_DECISION_KIND.items()
}

ALLOWED_REVIEW_DECISIONS = {
    "command_selection": [],
    "action_approval": [
        "approved",
        "rejected",
        "revise",
    ],
    "patch_review": [
        "approved",
        "rejected",
        "revise",
    ],
    "patch_promotion": [
        "approved",
        "rejected",
    ],
}


def allowed_operations(
    record: JobRecord,
) -> list[AllowedOperation]:
    """根据服务端当前状态生成客户端可以执行的操作。"""

    operations: list[AllowedOperation] = []

    if record.status == "waiting_for_input":
        # 当前 Graph 是串行审批图。出现多个不同 interrupt 时不能猜测。
        unique_nodes = sorted(
            set(record.interrupt_nodes)
        )
        if len(unique_nodes) == 1:
            node = unique_nodes[0]
            decision_kind = NODE_TO_DECISION_KIND.get(
                node
            )
            if decision_kind is not None:
                operations.append(
                    AllowedOperation(
                        operation_id=(
                            f"wait:"
                            f"{record.wait_generation}:"
                            f"{node}"
                        ),
                        kind="submit_decision",
                        endpoint=(
                            f"/v1/jobs/{record.job_id}"
                            "/decisions"
                        ),
                        decision_kind=decision_kind,
                        expected_node=node,
                        expected_job_version=(
                            record.version
                        ),
                        expected_wait_generation=(
                            record.wait_generation
                        ),
                        allowed_decisions=(
                            ALLOWED_REVIEW_DECISIONS[
                                decision_kind
                            ]
                        ),
                    )
                )

    if record.status in {
        "queued",
        "running",
        "waiting_for_input",
        "cancelling",
    }:
        operations.append(
            AllowedOperation(
                operation_id=(
                    f"cancel:{record.version}"
                ),
                kind="cancel",
                endpoint=(
                    f"/v1/jobs/{record.job_id}"
                    "/cancel"
                ),
                expected_job_version=record.version,
            )
        )

    if record.status == "reconciliation_required":
        # 只提示，不开放危险的远程自动恢复。
        operations.append(
            AllowedOperation(
                operation_id=(
                    f"reconcile:{record.version}"
                ),
                kind=(
                    "operator_reconciliation_required"
                ),
                expected_job_version=record.version,
                requires_idempotency_key=False,
                detail=(
                    "请由受信任运维人员使用 "
                    "resolve-job 检查外部副作用"
                ),
            )
        )

    return operations


def validate_decision(
    *,
    record: JobRecord,
    envelope: DecisionEnvelope,
) -> str:
    """
    校验当前状态并返回真正的 expected_node。

    该函数只验证交互身份，不替代节点内部 action/patch/hash 校验。
    """

    if record.status != "waiting_for_input":
        raise JobConflictError(
            "Job 当前不在 waiting_for_input"
        )

    if record.version != envelope.expected_job_version:
        raise JobConflictError(
            "Job version 已变化："
            f"expected={envelope.expected_job_version}, "
            f"current={record.version}"
        )

    if (
        record.wait_generation
        != envelope.expected_wait_generation
    ):
        raise JobConflictError(
            "interrupt generation 已变化："
            f"expected={envelope.expected_wait_generation}, "
            f"current={record.wait_generation}"
        )

    unique_nodes = sorted(
        set(record.interrupt_nodes)
    )
    if len(unique_nodes) != 1:
        raise JobConflictError(
            "当前 interrupt 节点不唯一，"
            "API 不会猜测应恢复哪个节点："
            f"{unique_nodes}"
        )

    expected_node = DECISION_KIND_TO_NODE.get(
        envelope.decision.kind
    )
    if expected_node is None:
        raise JobConflictError(
            "不支持的 decision kind"
        )

    if unique_nodes[0] != expected_node:
        raise JobConflictError(
            "decision kind 与当前 interrupt 不匹配："
            f"kind={envelope.decision.kind}, "
            f"current_node={unique_nodes[0]}"
        )

    return expected_node


def decision_to_resume_value(
    decision: Decision,
) -> Any:
    """把公开 Decision schema 转成原 interrupt 节点已经接受的值。"""

    payload = decision.model_dump()
    payload.pop("kind", None)
    return payload
```

这一层最重要的边界是：

```text
API：
    校验“这个用户输入属于当前哪一代、哪一个节点”。

Graph 节点：
    校验“业务对象 hash 是否仍然一致、审批是否允许执行”。
```

不要为了“统一”而删除节点原有校验。

---

## 十二、增强 Job Store 的交互并发语义

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/store.py`

### 12.1 增加写命令幂等表

在 `initialize()` 的 `executescript()` 中，放到 `job_events` 表之后：

```sql
CREATE TABLE IF NOT EXISTS job_commands (
    command_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    command_type TEXT NOT NULL CHECK (
        command_type IN ('cancel')
    ),
    idempotency_key TEXT NOT NULL UNIQUE,
    request_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(job_id)
        REFERENCES jobs(job_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_commands_job
ON job_commands(job_id, command_id);
```

`resume` 已有独立的 `job_resumes.idempotency_key`。这里先只给 `cancel` 增加命令
幂等记录。

### 12.2 增加事件游标查询

在现有 `list_events()` 后增加完整函数：

```python
    def list_events_after(
        self,
        job_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        """
        返回 event_id 严格大于游标的事件。

        event_id 是数据库内单调递增游标；客户端不得用数组下标或时间戳续读。
        """

        self.get(job_id)
        bounded_after = max(0, after_event_id)
        bounded_limit = max(
            1,
            min(limit, 1000),
        )

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM job_events
                WHERE job_id = ?
                  AND event_id > ?
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (
                    job_id,
                    bounded_after,
                    bounded_limit,
                ),
            ).fetchall()

        return [
            JobEvent(
                event_id=row["event_id"],
                job_id=row["job_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                payload=_load_json(
                    row["payload_json"],
                    {},
                ),
                created_at=_iso(
                    row["created_at"]
                ),
            )
            for row in rows
        ]
```

现有 `list_events()` 暂时保留，兼容 Phase 22 CLI。

### 12.3 给 `queue_resume()` 增加乐观并发参数

修改函数签名：

```python
    def queue_resume(
        self,
        *,
        job_id: str,
        expected_node: str,
        value: Any,
        idempotency_key: str,
        actor: str,
        expected_job_version: int | None = None,
        expected_wait_generation: int | None = None,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
```

保留原函数中的幂等 key 查询，并且必须先处理“相同 key 的重放”。在查询 Job row
之后、检查 `status` 之前加入：

```python
            if (
                expected_job_version is not None
                and row["version"]
                != expected_job_version
            ):
                raise JobConflictError(
                    "Job version 已变化："
                    f"expected={expected_job_version}, "
                    f"current={row['version']}"
                )

            if (
                expected_wait_generation
                is not None
                and row["wait_generation"]
                != expected_wait_generation
            ):
                raise JobConflictError(
                    "interrupt generation 已变化："
                    f"expected={expected_wait_generation}, "
                    f"current={row['wait_generation']}"
                )
```

顺序必须是：

```text
1. 查询已有 idempotency_key；
2. 如果相同 key + 相同 payload，返回旧结果；
3. 如果是首次请求，再检查当前 version/generation；
4. 创建 resume。
```

如果先检查 version，客户端重试一个已经成功的请求时，Job version 已递增，重试
会错误地返回 conflict。

### 12.4 完整替换 `request_cancel()`

为了让取消也支持幂等和乐观并发，用下面函数完整替换原实现：

```python
    def request_cancel(
        self,
        *,
        job_id: str,
        reason: str,
        actor: str,
        idempotency_key: str | None = None,
        expected_job_version: int | None = None,
        now: float | None = None,
    ) -> JobRecord:
        current = time.time() if now is None else now
        bounded_reason = (
            reason.strip()
            or "user requested cancellation"
        )[:500]

        # CLI 旧调用可以不传 key；HTTP 写请求必须传。
        effective_key = (
            idempotency_key.strip()
            if idempotency_key
            else None
        )
        if (
            effective_key is not None
            and (
                not effective_key
                or len(effective_key) > 300
            )
        ):
            raise ValueError(
                "idempotency_key 长度必须为 1..300"
            )
        request_hash = _json_hash(
            {
                "job_id": job_id,
                "command_type": "cancel",
                "reason": bounded_reason,
            }
        )

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")

            # 幂等重放优先于版本校验。
            if effective_key is not None:
                existing = connection.execute(
                    """
                    SELECT *
                    FROM job_commands
                    WHERE idempotency_key = ?
                    """,
                    (effective_key,),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["job_id"] != job_id
                        or existing["command_type"]
                        != "cancel"
                        or existing["request_hash"]
                        != request_hash
                    ):
                        raise JobConflictError(
                            "相同 cancel idempotency_key "
                            "对应不同请求"
                        )

                    replayed_job = connection.execute(
                        """
                        SELECT *
                        FROM jobs
                        WHERE job_id = ?
                        """,
                        (job_id,),
                    ).fetchone()
                    if replayed_job is None:
                        raise JobNotFoundError(
                            f"未找到 job_id={job_id}"
                        )
                    connection.commit()
                    return self._row_to_record(
                        replayed_job
                    )

            row = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                raise JobNotFoundError(
                    f"未找到 job_id={job_id}"
                )

            if (
                expected_job_version is not None
                and row["version"]
                != expected_job_version
            ):
                raise JobConflictError(
                    "Job version 已变化："
                    f"expected={expected_job_version}, "
                    f"current={row['version']}"
                )

            terminal = row["status"] in {
                "succeeded",
                "failed",
                "cancelled",
            }

            if not terminal:
                if row["status"] in {
                    "queued",
                    "waiting_for_input",
                }:
                    target_status = "cancelled"
                    clear_ownership = True
                elif row["status"] in {
                    "running",
                    "cancelling",
                }:
                    target_status = "cancelling"
                    clear_ownership = False
                else:
                    # reconciliation_required 不能靠 API 猜测孤儿进程状态。
                    target_status = (
                        "reconciliation_required"
                    )
                    clear_ownership = True

                if clear_ownership:
                    self._consume_pending_resume(
                        connection,
                        resume_id=row[
                            "pending_resume_id"
                        ],
                        now=current,
                    )
                    ownership_sql = """
                        worker_id = NULL,
                        claim_token = NULL,
                        claimed_at = NULL,
                        heartbeat_at = NULL,
                        lease_expires_at = NULL,
                        pending_resume_id = NULL,
                    """
                else:
                    ownership_sql = ""

                connection.execute(
                    f"""
                    UPDATE jobs
                    SET status = ?,
                        version = version + 1,
                        {ownership_sql}
                        cancel_requested = 1,
                        cancellation_reason = ?,
                        updated_at = ?
                    WHERE job_id = ?
                    """,
                    (
                        target_status,
                        bounded_reason,
                        current,
                        job_id,
                    ),
                )
                self._append_event(
                    connection,
                    job_id=job_id,
                    event_type=(
                        "job_cancelled"
                        if target_status
                        == "cancelled"
                        else "job_cancel_requested"
                    ),
                    actor=actor,
                    payload={
                        "reason": bounded_reason
                    },
                    now=current,
                )

            if effective_key is not None:
                connection.execute(
                    """
                    INSERT INTO job_commands (
                        command_id,
                        job_id,
                        command_type,
                        idempotency_key,
                        request_hash,
                        created_at
                    )
                    VALUES (?, ?, 'cancel', ?, ?, ?)
                    """,
                    (
                        f"command_{uuid4().hex}",
                        job_id,
                        effective_key,
                        request_hash,
                        current,
                    ),
                )

            updated = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._row_to_record(updated)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
```

注意：当前 `store.py` 已经从 `uuid` 导入 `uuid4`，也已经有 `_json_hash()`，不需要
新增重复实现。

---

## 十三、扩展 JobService

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/service.py`

### 13.1 增加事件游标方法

在现有 `events()` 后增加：

```python
    def events_after(
        self,
        job_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        """供分页查询和 SSE 共用，API 不直接访问 Store。"""

        return self.store.list_events_after(
            job_id,
            after_event_id=after_event_id,
            limit=limit,
        )
```

### 13.2 修改 `resume()` 签名和 Store 调用

完整函数改为：

```python
    def resume(
        self,
        *,
        job_id: str,
        expected_node: str,
        value: Any,
        idempotency_key: str | None = None,
        expected_job_version: int | None = None,
        expected_wait_generation: int | None = None,
        actor: str = "cli",
    ) -> tuple[JobRecord, bool]:
        current = self.store.get(job_id)
        key = (
            idempotency_key.strip()
            if idempotency_key
            else (
                f"resume:{job_id}:"
                f"{current.wait_generation}:"
                f"{_value_hash(value)}"
            )
        )
        if not key or len(key) > 300:
            raise ValueError(
                "idempotency_key 长度必须为 1..300"
            )
        return self.store.queue_resume(
            job_id=job_id,
            expected_node=expected_node,
            value=value,
            idempotency_key=key,
            actor=actor,
            expected_job_version=(
                expected_job_version
            ),
            expected_wait_generation=(
                expected_wait_generation
            ),
        )
```

### 13.3 修改 `cancel()` 签名和 Store 调用

完整函数改为：

```python
    def cancel(
        self,
        *,
        job_id: str,
        reason: str,
        idempotency_key: str | None = None,
        expected_job_version: int | None = None,
        actor: str = "cli",
    ) -> JobRecord:
        record = self.store.request_cancel(
            job_id=job_id,
            reason=reason,
            actor=actor,
            idempotency_key=idempotency_key,
            expected_job_version=(
                expected_job_version
            ),
        )

        # running/cancelling 时立即桥接已有 Process Supervisor。
        # 没有活动进程可能意味着当前在 LLM 节点，不算错误。
        if record.status == "cancelling":
            try:
                request_run_cancellation(
                    run_dir=record.run_dir,
                    reason=reason,
                    requested_by=actor,
                )
            except (
                ValueError,
                FileNotFoundError,
            ):
                pass
        return record
```

原 CLI 没有传新参数时仍能工作；API 会强制传入。

---

## 十四、实现公开 Job 投影与统一 InteractionService

> **本节类型：需要新增代码。**
>
> 新增：`app/interaction/service.py`

完整代码：

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.interaction.policy import (
    allowed_operations,
    decision_to_resume_value,
    validate_decision,
)
from app.interaction.schemas import (
    CancelEnvelope,
    DecisionEnvelope,
    EventView,
    JobCreateRequest,
    JobMutationResponse,
    JobView,
    LogTailResponse,
    PublicInterrupt,
    PublicJobInput,
    PublicJobResult,
)
from app.job_runtime.schemas import (
    JobRecord,
    JobRequest,
)
from app.job_runtime.service import JobService
from app.job_runtime.store import JobConflictError


_REDACTED_KEYS = {
    "absolute_path",
    "claim_token",
    "run_dir",
    "patch_path",
    "worktree_path",
    "input_path",
}

_SECRET_KEY_PARTS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
}


def _public_value(value: Any) -> Any:
    """递归移除运行时内部路径和常见 secret 字段。"""

    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if (
                lowered in _REDACTED_KEYS
                or any(
                    part in lowered
                    for part in _SECRET_KEY_PARTS
                )
            ):
                result[key] = "[redacted]"
            else:
                result[key] = _public_value(
                    raw_value
                )
        return result

    if isinstance(value, list):
        return [
            _public_value(item)
            for item in value
        ]

    return value


def _public_result(
    record: JobRecord,
) -> PublicJobResult | None:
    if record.result is None:
        return None
    return PublicJobResult(
        final_status=record.result.get(
            "final_status"
        ),
        stage_error_count=record.result.get(
            "stage_error_count"
        ),
        output_file_count=record.result.get(
            "output_file_count"
        ),
    )


def _required_idempotency_key(
    value: str,
) -> str:
    """规范化并拒绝空白或过长的写请求幂等键。"""

    key = value.strip()
    if not key or len(key) > 300:
        raise ValueError(
            "Idempotency-Key 长度必须为 1..300"
        )
    return key


def project_job(record: JobRecord) -> JobView:
    """
    JobRecord 是内部模型；JobView 是公开模型。

    禁止使用 record.model_dump() 再排除几个字段，因为以后 JobRecord 新增
    secret 字段时可能被默认暴露。这里采用显式 allowlist。
    """

    return JobView(
        job_id=record.job_id,
        thread_id=record.thread_id,
        run_id=record.run_id,
        status=record.status,
        version=record.version,
        attempt_count=record.attempt_count,
        max_attempts=record.max_attempts,
        wait_generation=record.wait_generation,
        interrupt_nodes=list(
            record.interrupt_nodes
        ),
        interrupts=[
            PublicInterrupt(
                node=item.node,
                interrupt_id=item.interrupt_id,
                value_preview=_public_value(
                    item.value_preview
                ),
            )
            for item in record.interrupts
        ],
        cancel_requested=record.cancel_requested,
        cancellation_reason=(
            record.cancellation_reason
        ),
        result=_public_result(record),
        error=_public_value(record.error),
        reconciliation=_public_value(
            record.reconciliation
        ),
        input=PublicJobInput(
            paper_name=Path(
                record.request.paper_path
            ).name,
            repo_name=Path(
                record.request.repo_path
            ).name,
            experiment_goal=(
                record.request.experiment_goal
            ),
            execution_profile_id=(
                record.request
                .execution_profile_id
            ),
        ),
        allowed_operations=(
            allowed_operations(record)
        ),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class InteractionService:
    """CLI/API 共用的交互用例层，不直接执行 SQL。"""

    def __init__(
        self,
        job_service: JobService,
    ):
        self.job_service = job_service

    def create_job(
        self,
        *,
        request: JobCreateRequest,
        idempotency_key: str,
    ) -> JobMutationResponse:
        key = _required_idempotency_key(
            idempotency_key
        )
        record, created = self.job_service.submit(
            request=JobRequest(
                paper_path=request.paper_path,
                repo_path=request.repo_path,
                log_path=request.log_path,
                experiment_goal=(
                    request.experiment_goal
                ),
                execution_profile_id=(
                    request.execution_profile_id
                ),
            ),
            thread_id=request.thread_id,
            idempotency_key=key,
        )
        return JobMutationResponse(
            job=project_job(record),
            replayed=not created,
        )

    def get_job(
        self,
        job_id: str,
    ) -> JobView:
        return project_job(
            self.job_service.get(job_id)
        )

    def list_jobs(
        self,
        *,
        status: str | None,
        limit: int,
    ) -> list[JobView]:
        return [
            project_job(item)
            for item in self.job_service.list(
                status=status,
                limit=limit,
            )
        ]

    def submit_decision(
        self,
        *,
        job_id: str,
        envelope: DecisionEnvelope,
        idempotency_key: str,
        actor: str,
    ) -> JobMutationResponse:
        key = _required_idempotency_key(
            idempotency_key
        )
        current = self.job_service.get(job_id)
        expected_node = validate_decision(
            record=current,
            envelope=envelope,
        )
        value = decision_to_resume_value(
            envelope.decision
        )
        updated, created = (
            self.job_service.resume(
                job_id=job_id,
                expected_node=expected_node,
                value=value,
                idempotency_key=key,
                expected_job_version=(
                    envelope
                    .expected_job_version
                ),
                expected_wait_generation=(
                    envelope
                    .expected_wait_generation
                ),
                actor=actor,
            )
        )
        return JobMutationResponse(
            job=project_job(updated),
            replayed=not created,
        )

    def cancel_job(
        self,
        *,
        job_id: str,
        envelope: CancelEnvelope,
        idempotency_key: str,
        actor: str,
    ) -> JobMutationResponse:
        key = _required_idempotency_key(
            idempotency_key
        )
        updated = self.job_service.cancel(
            job_id=job_id,
            reason=envelope.reason,
            idempotency_key=key,
            expected_job_version=(
                envelope.expected_job_version
            ),
            actor=actor,
        )
        return JobMutationResponse(
            job=project_job(updated),
        )

    def events_after(
        self,
        *,
        job_id: str,
        after_event_id: int,
        limit: int,
    ) -> list[EventView]:
        return [
            EventView(
                event_id=item.event_id,
                job_id=item.job_id,
                event_type=item.event_type,
                actor=item.actor,
                payload=_public_value(
                    item.payload
                ),
                created_at=item.created_at,
            )
            for item in (
                self.job_service.events_after(
                    job_id,
                    after_event_id=(
                        after_event_id
                    ),
                    limit=limit,
                )
            )
        ]

    def tail_log(
        self,
        *,
        job_id: str,
        lines: int,
        max_bytes: int,
    ) -> LogTailResponse:
        record = self.job_service.get(job_id)
        path, content = (
            self.job_service.tail_log(
                job_id=job_id,
                lines=lines,
                max_bytes=max_bytes,
            )
        )
        if path is None:
            return LogTailResponse(
                lines=lines
            )

        run_root = Path(
            record.run_dir
        ).resolve()
        resolved = Path(path).resolve()
        if run_root not in resolved.parents:
            raise JobConflictError(
                "日志路径逃逸当前 run"
            )

        return LogTailResponse(
            relative_path=(
                resolved.relative_to(
                    run_root
                ).as_posix()
            ),
            content=content,
            lines=lines,
            truncated_by_bytes=(
                resolved.stat().st_size
                > max_bytes
            ),
        )
```

注意 `_public_value()` 只是响应层的防泄漏措施，不是完整 DLP 系统。认证、最小监听
范围、日志脱敏和部署网络边界仍然必须存在。

---

## 十五、实现 Artifact Catalog

> **本节类型：需要新增代码。**
>
> 新增：`app/interaction/artifacts.py`

完整代码：

```python
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.graph import build_graph
from app.interaction.schemas import (
    ArtifactView,
)
from app.job_runtime.schemas import JobRecord
from app.job_runtime.store import (
    JobConflictError,
    JobNotFoundError,
)
from app.schemas import ArtifactRecord
from app.tools.artifact_tools import sha256_file


StateReader = Callable[
    [str],
    dict[str, Any],
]


@dataclass(frozen=True)
class ResolvedArtifact:
    """只在 API 内部短暂存在，不能直接序列化返回。"""

    record: ArtifactRecord
    path: Path


def read_graph_state(
    thread_id: str,
) -> dict[str, Any]:
    """从 LangGraph checkpoint 读取当前完整 state。"""

    snapshot = build_graph().get_state(
        {
            "configurable": {
                "thread_id": thread_id,
            }
        }
    )
    return dict(
        getattr(
            snapshot,
            "values",
            {},
        )
        or {}
    )


class LocalArtifactCatalog:
    """
    当前本地 Artifact 适配器。

    API 依赖这个 catalog，而不是直接拼接 runs 路径。Phase 24 可增加
    S3ArtifactStore，同时保持 HTTP 协议不变。
    """

    def __init__(
        self,
        *,
        state_reader: StateReader = read_graph_state,
    ):
        self.state_reader = state_reader

    def _run_root(
        self,
        job: JobRecord,
    ) -> Path:
        runs_root = settings.runs_dir.resolve()
        run_root = Path(job.run_dir).resolve()
        if (
            run_root == runs_root
            or runs_root not in run_root.parents
        ):
            raise JobConflictError(
                "Job run_dir 位于 RUNS_DIR 之外"
            )
        return run_root

    def _manifest_records(
        self,
        run_root: Path,
    ) -> list[dict[str, Any]]:
        """
        checkpoint 不可用时读取最终 Artifact index。

        这只是当前本地实现的恢复路径，不进入公开 API schema。
        """

        index_path = (
            run_root
            / "reports"
            / "artifact_index.json"
        )
        if not index_path.is_file():
            return []
        try:
            payload = json.loads(
                index_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise JobConflictError(
                f"无法读取 Artifact index：{exc}"
            ) from exc
        return list(
            payload.get("artifacts", [])
        )

    def records(
        self,
        job: JobRecord,
    ) -> list[ArtifactRecord]:
        run_root = self._run_root(job)
        state = self.state_reader(
            job.thread_id
        )

        raw_records = state.get(
            "artifact_records",
            [],
        )
        if not raw_records:
            raw_records = (
                self._manifest_records(
                    run_root
                )
            )

        records: dict[
            str,
            ArtifactRecord,
        ] = {}
        for raw in raw_records:
            record = (
                ArtifactRecord.model_validate(
                    raw
                )
            )
            if record.run_id != job.run_id:
                raise JobConflictError(
                    "Artifact run_id 与 Job 不匹配"
                )
            previous = records.get(
                record.artifact_id
            )
            if (
                previous is not None
                and previous.relative_path
                != record.relative_path
            ):
                raise JobConflictError(
                    "同一 artifact_id 对应多个路径"
                )
            records[record.artifact_id] = (
                record
            )

        return sorted(
            records.values(),
            key=lambda item: (
                item.layer,
                item.relative_path,
            ),
        )

    def list_views(
        self,
        job: JobRecord,
    ) -> list[ArtifactView]:
        # 列表查询不逐个计算大文件 hash，下载时再做强校验。
        return [
            ArtifactView(
                artifact_id=item.artifact_id,
                run_id=item.run_id,
                layer=item.layer,
                relative_path=(
                    item.relative_path
                ),
                media_type=item.media_type,
                sha256=item.sha256,
                size_bytes=item.size_bytes,
                producer_node=(
                    item.producer_node
                ),
                created_at=item.created_at,
                integrity_status="unchecked",
            )
            for item in self.records(job)
        ]

    def resolve(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> ResolvedArtifact:
        run_root = self._run_root(job)
        record = next(
            (
                item
                for item in self.records(job)
                if item.artifact_id
                == artifact_id
            ),
            None,
        )
        if record is None:
            raise JobNotFoundError(
                "当前 Job 中不存在 "
                f"artifact_id={artifact_id}"
            )

        # 只使用受校验的 run_root + relative_path。
        # 不信任 record.absolute_path。
        candidate = (
            run_root
            / record.relative_path
        ).resolve()
        if (
            candidate == run_root
            or run_root not in candidate.parents
        ):
            raise JobConflictError(
                "Artifact 路径逃逸当前 run"
            )
        if not candidate.is_file():
            raise JobNotFoundError(
                "Artifact 文件不存在"
            )
        if candidate.stat().st_size != (
            record.size_bytes
        ):
            raise JobConflictError(
                "Artifact 大小与记录不一致"
            )
        if sha256_file(candidate) != record.sha256:
            raise JobConflictError(
                "Artifact SHA-256 校验失败"
            )

        return ResolvedArtifact(
            record=record,
            path=candidate,
        )
```

### 15.1 为什么不能使用请求中的 `path`

错误接口：

```text
GET /download?path=/data/.../secret
```

正确接口：

```text
GET /v1/jobs/{job_id}/artifacts/{artifact_id}/content
```

服务端通过：

```text
job_id
  -> run_id/run_root
artifact_id
  -> ArtifactRecord.relative_path
```

定位文件，并重新执行：

```text
run 边界校验
symlink resolve 校验
size 校验
SHA-256 校验
```

Phase 24 改为对象存储后，`resolve()` 可以返回受控流或短期签名 URL。

---

## 十六、实现 API 认证

> **本节类型：需要新增代码。**
>
> 新增：`app/api/__init__.py`

```python
"""FastAPI 任务交互入口。"""
```

> 新增：`app/api/auth.py`

完整代码：

```python
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, Request


def require_api_auth(
    request: Request,
    authorization: str | None = Header(
        default=None,
        alias="Authorization",
    ),
) -> str:
    """
    返回审计 actor。

    未配置 token 时，serve-api 会强制只能监听 loopback。
    """

    expected = request.app.state.api_token
    if not expected:
        return "api:local"

    scheme, separator, credentials = (
        authorization or ""
    ).partition(" ")
    valid = (
        separator == " "
        and scheme.lower() == "bearer"
        and secrets.compare_digest(
            credentials,
            expected,
        )
    )
    if not valid:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": (
                    "缺少或无效的 Bearer Token"
                ),
            },
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # 第一版只有一个 service identity，后续再加入用户主体和 RBAC。
    return "api:token"
```

不要：

- 把 token 打印到启动日志；
- 把 token 写入 `.env.example`；
- 把 `Authorization` 写入 Job Event；
- 在 URL query 中传 token。

---

## 十七、统一 API 错误

> **本节类型：需要新增代码。**
>
> 新增：`app/api/errors.py`

完整代码：

```python
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.interaction.schemas import ApiError
from app.job_runtime.store import (
    JobConflictError,
    JobNotFoundError,
    JobStoreError,
)


def _response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    payload = ApiError(
        code=code,
        message=message,
        request_id=getattr(
            request.state,
            "request_id",
            None,
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
    )


def install_error_handlers(
    app: FastAPI,
) -> None:
    """把内部异常映射成稳定 HTTP 语义。"""

    @app.exception_handler(
        JobNotFoundError
    )
    async def handle_not_found(
        request: Request,
        exc: JobNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="JOB_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(
        JobConflictError
    )
    async def handle_conflict(
        request: Request,
        exc: JobConflictError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="JOB_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(
        request: Request,
        exc: ValueError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="INVALID_REQUEST",
            message=str(exc),
        )

    @app.exception_handler(JobStoreError)
    async def handle_store_error(
        request: Request,
        exc: JobStoreError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=500,
            code="JOB_STORE_ERROR",
            message=str(exc),
        )
```

不要把 Python traceback 返回给客户端。traceback 应进入服务端日志；响应只返回
有限、可审计的错误码和 `request_id`。

---

## 十八、实现 API Routes 与 SSE

> **本节类型：需要新增代码。**
>
> 新增：`app/api/routes.py`

完整代码：

```python
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
    Request,
)
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
)

from app.api.auth import require_api_auth
from app.config import settings
from app.interaction.artifacts import (
    LocalArtifactCatalog,
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
    JobStatus,
    TERMINAL_JOB_STATUSES,
)


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
) -> LocalArtifactCatalog:
    return request.app.state.artifact_catalog


Actor = Annotated[
    str,
    Depends(require_api_auth),
]

InteractionDependency = Annotated[
    InteractionService,
    Depends(interaction_service),
]

ArtifactCatalogDependency = Annotated[
    LocalArtifactCatalog,
    Depends(artifact_catalog),
]

JobStatusQuery = Annotated[
    JobStatus | None,
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
    int | None,
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


@router.post(
    "/jobs",
    response_model=JobMutationResponse,
    status_code=201,
)
def create_job(
    body: JobCreateRequest,
    idempotency_key: IdempotencyKey,
    _actor: Actor,
    service: InteractionDependency,
) -> JobMutationResponse:
    return service.create_job(
        request=body,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/jobs",
    response_model=JobListResponse,
)
def list_jobs(
    _actor: Actor,
    service: InteractionDependency,
    status: JobStatusQuery = None,
    limit: PageLimitQuery = 50,
) -> JobListResponse:
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
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
) -> JobView:
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


@router.get(
    "/jobs/{job_id}/artifacts",
    response_model=ArtifactListResponse,
)
def list_artifacts(
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
    catalog: ArtifactCatalogDependency,
) -> ArtifactListResponse:
    internal_job = (
        service.job_service.get(job_id)
    )
    items = catalog.list_views(internal_job)
    return ArtifactListResponse(
        items=items,
        count=len(items),
    )


@router.get(
    "/jobs/{job_id}/artifacts/"
    "{artifact_id}/content"
)
def download_artifact(
    job_id: str,
    artifact_id: str,
    _actor: Actor,
    service: InteractionDependency,
    catalog: ArtifactCatalogDependency,
) -> FileResponse:
    internal_job = (
        service.job_service.get(job_id)
    )
    resolved = catalog.resolve(
        job=internal_job,
        artifact_id=artifact_id,
    )
    return FileResponse(
        path=resolved.path,
        media_type=(
            resolved.record.media_type
        ),
        filename=Path(
            resolved.record.relative_path
        ).name,
        headers={
            "ETag": (
                f'"sha256:{resolved.record.sha256}"'
            ),
            "Cache-Control": "private, no-store",
        },
    )


@router.get(
    "/jobs/{job_id}/logs",
    response_model=LogTailResponse,
)
def tail_log(
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
    lines: LogLinesQuery = 100,
) -> LogTailResponse:
    return service.tail_log(
        job_id=job_id,
        lines=lines,
        max_bytes=settings.api_max_log_bytes,
    )
```

### 18.1 `follow=false` 是什么

它不是生产轮询模式，而是：

```text
返回 after 游标之后当前已经存在的事件
然后关闭连接
```

生产客户端默认使用 `follow=true`。测试使用 `follow=false`，避免测试永久等待。

### 18.2 SSE 是否会丢事件

网络断开时，客户端记住最后收到的 `event_id`：

```text
Last-Event-ID = 17
```

重连时可使用标准请求头：

```text
Last-Event-ID: 17
```

也可以使用便于 CLI 调试的 query：

```text
GET /events/stream?after=17
```

因为事件先持久化到 `job_events`，SSE 只负责投影，所以临时断线不会要求 Redis
保存未投递消息。

---

## 十九、实现 FastAPI App Factory

> **本节类型：需要新增代码。**
>
> 新增：`app/api/app.py`

完整代码：

```python
from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request

from app.api.errors import (
    install_error_handlers,
)
from app.api.routes import router
from app.config import settings
from app.interaction.artifacts import (
    LocalArtifactCatalog,
)
from app.interaction.service import (
    InteractionService,
)
from app.job_runtime.service import (
    JobService,
    build_job_service,
)


def create_api_app(
    *,
    job_service: JobService | None = None,
    artifact_catalog: (
        LocalArtifactCatalog | None
    ) = None,
    api_token: str | None = None,
) -> FastAPI:
    """
    App factory 允许测试注入临时 Job DB 和伪 checkpoint reader。
    """

    selected_job_service = (
        job_service
        if job_service is not None
        else build_job_service()
    )

    app = FastAPI(
        title=(
            "Paper Reproduction Copilot API"
        ),
        version="1.0",
        docs_url="/docs",
        redoc_url=None,
    )
    app.state.interaction_service = (
        InteractionService(
            selected_job_service
        )
    )
    app.state.artifact_catalog = (
        artifact_catalog
        if artifact_catalog is not None
        else LocalArtifactCatalog()
    )
    app.state.api_token = (
        settings.api_token
        if api_token is None
        else api_token
    )

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next,
    ):
        request_id = (
            request.headers.get(
                "X-Request-ID"
            )
            or f"request_{uuid4().hex}"
        )[:200]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[
            "X-Request-ID"
        ] = request_id
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        # liveness 不查询 Provider、Graph 或 worker。
        return {"status": "ok"}

    app.include_router(router)
    install_error_handlers(app)
    return app
```

不要在模块底部写：

```python
app = create_api_app()
```

否则测试执行：

```python
from app.api.app import create_api_app
```

时就会使用默认配置初始化真实 Job DB。下一节使用 Uvicorn factory，让 App 只在
真正启动服务时创建。

第一版 `/healthz` 只是 liveness。后续可以增加受认证的 `/readyz`，分别检查 Job
DB、Checkpoint 和 Artifact backend，但不要在每次 liveness 中调用模型 Provider。

---

## 二十、增加安全的 API 启动命令

> **本节类型：需要修改代码。**
>
> 修改：`app/main.py`

在文件 import 区增加：

```python
import ipaddress
```

在 Job CLI 区域增加辅助函数和命令：

```python
def _is_loopback_host(host: str) -> bool:
    """只接受明确的 loopback 名称或 IP。"""

    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(
            normalized
        ).is_loopback
    except ValueError:
        return False


@app.command("serve-api")
def serve_api_command(
    host: str = typer.Option(
        settings.api_host,
        "--host",
    ),
    port: int = typer.Option(
        settings.api_port,
        "--port",
        min=1,
        max=65535,
    ),
):
    """启动本地优先的任务交互 API。"""

    if (
        not _is_loopback_host(host)
        and not settings.api_token
    ):
        raise typer.BadParameter(
            "监听非 loopback 地址前必须设置 "
            "AGENT_API_TOKEN"
        )

    # 动态 import，避免只运行 worker 时强制依赖 uvicorn。
    import uvicorn

    print(
        {
            "host": host,
            "port": port,
            "authentication": (
                "bearer"
                if settings.api_token
                else "local-only"
            ),
        }
    )
    uvicorn.run(
        "app.api.app:create_api_app",
        host=host,
        port=port,
        reload=False,
        factory=True,
        proxy_headers=False,
    )
```

第一版必须：

```text
reload=False
proxy_headers=False
```

开发时如果需要 reload，也应单独启动，并理解它会创建重载进程。不要把开发重载
进程误认为 Job worker。

---

## 二十一、让旧 CLI 也使用乐观并发

> **本节类型：需要修改代码。**
>
> 修改：`app/main.py`

HTTP API 已经强制版本和 generation。为了让 CLI 行为不落后，在
`resume_job_command()` 中增加两个可选参数：

```python
    expected_version: int | None = typer.Option(
        None,
        "--expected-version",
        min=0,
    ),
    expected_wait_generation: (
        int | None
    ) = typer.Option(
        None,
        "--expected-wait-generation",
        min=1,
    ),
```

在 `service.resume()` 前读取当前 Job，并传入有效值：

```python
    service = build_job_service()
    try:
        current = service.get(job_id)
        record, created = service.resume(
            job_id=job_id,
            expected_node=expected_node,
            value=value,
            idempotency_key=idempotency_key,
            expected_job_version=(
                expected_version
                if expected_version is not None
                else current.version
            ),
            expected_wait_generation=(
                expected_wait_generation
                if expected_wait_generation
                is not None
                else current.wait_generation
            ),
            actor="cli",
        )
    except (ValueError, JobStoreError) as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None
```

在 `cancel_job_command()` 中增加：

```python
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
    ),
    expected_version: int | None = typer.Option(
        None,
        "--expected-version",
        min=0,
    ),
```

调用改为：

```python
    service = build_job_service()
    try:
        current = service.get(job_id)
        record = service.cancel(
            job_id=job_id,
            reason=reason,
            idempotency_key=(
                idempotency_key
            ),
            expected_job_version=(
                expected_version
                if expected_version is not None
                else current.version
            ),
            actor="cli",
        )
    except JobStoreError as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None
```

这里 CLI 和 API 共用的是：

```text
JobService
Store transaction
version/generation
idempotency
Process Supervisor cancellation bridge
```

CLI 不需要通过本机 HTTP 调用 API。否则 API 停止时，受信任的运维 CLI 也无法
处理 Job。

---

## 二十二、增加 Decision Policy 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_interaction_policy.py`

完整代码：

```python
from datetime import datetime, timezone

import pytest

from app.interaction.policy import (
    allowed_operations,
    decision_to_resume_value,
    validate_decision,
)
from app.interaction.schemas import (
    ActionApprovalDecision,
    DecisionEnvelope,
)
from app.job_runtime.schemas import (
    JobInterrupt,
    JobRecord,
    JobRequest,
)
from app.job_runtime.store import (
    JobConflictError,
)


def _waiting_job(
    *,
    version: int = 4,
    generation: int = 2,
    node: str = "human_review",
) -> JobRecord:
    now = datetime.now(
        timezone.utc
    ).isoformat()
    return JobRecord(
        job_id="job_policy",
        idempotency_key="submit-policy",
        request_hash="request-hash",
        thread_id="thread-policy",
        run_id="run-policy",
        run_dir="/data/runs/run-policy",
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        status="waiting_for_input",
        version=version,
        attempt_count=1,
        max_attempts=3,
        wait_generation=generation,
        available_at=now,
        interrupt_nodes=[node],
        interrupts=[
            JobInterrupt(
                node=node,
                value_preview={
                    "message": "review"
                },
            )
        ],
        created_at=now,
        updated_at=now,
    )


def _envelope(
    *,
    version: int = 4,
    generation: int = 2,
) -> DecisionEnvelope:
    return DecisionEnvelope(
        expected_job_version=version,
        expected_wait_generation=(
            generation
        ),
        decision=ActionApprovalDecision(
            kind="action_approval",
            decision="approved",
        ),
    )


def test_allowed_operation_contains_server_identity():
    record = _waiting_job()

    operation = allowed_operations(
        record
    )[0]

    assert operation.kind == "submit_decision"
    assert (
        operation.expected_job_version
        == record.version
    )
    assert (
        operation.expected_wait_generation
        == record.wait_generation
    )
    assert (
        operation.decision_kind
        == "action_approval"
    )


def test_stale_job_version_is_rejected():
    with pytest.raises(
        JobConflictError,
        match="version",
    ):
        validate_decision(
            record=_waiting_job(
                version=5
            ),
            envelope=_envelope(
                version=4
            ),
        )


def test_stale_wait_generation_is_rejected():
    with pytest.raises(
        JobConflictError,
        match="generation",
    ):
        validate_decision(
            record=_waiting_job(
                generation=3
            ),
            envelope=_envelope(
                generation=2
            ),
        )


def test_wrong_decision_kind_is_rejected():
    with pytest.raises(
        JobConflictError,
        match="不匹配",
    ):
        validate_decision(
            record=_waiting_job(
                node="patch_review"
            ),
            envelope=_envelope(),
        )


def test_decision_value_does_not_include_kind():
    value = decision_to_resume_value(
        _envelope().decision
    )

    assert value == {
        "decision": "approved",
        "feedback": None,
    }
```

---

## 二十三、增加 Store 交互语义测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_job_store_interaction_semantics.py`

完整代码：

```python
import pytest

from app.job_runtime.schemas import (
    JobInterrupt,
    JobRequest,
)
from app.job_runtime.store import (
    JobConflictError,
    SqliteJobStore,
)


def _store_and_job(tmp_path):
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    record, _ = store.submit(
        job_id="job_api",
        idempotency_key="submit-api",
        thread_id="thread-api",
        run_id="run-api",
        run_dir=str(
            tmp_path / "runs" / "run-api"
        ),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        max_attempts=3,
        now=100.0,
    )
    return store, record


def _mark_waiting(store):
    claim = store.claim_next(
        worker_id="worker-test",
        lease_seconds=30,
        now=101.0,
    )
    assert claim is not None
    return store.mark_waiting(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={},
            )
        ],
        result={},
        actor="worker-test",
        now=102.0,
    )


def test_resume_rejects_stale_version(
    tmp_path,
):
    store, _ = _store_and_job(
        tmp_path
    )
    waiting = _mark_waiting(store)

    with pytest.raises(
        JobConflictError,
        match="version",
    ):
        store.queue_resume(
            job_id=waiting.job_id,
            expected_node="human_review",
            value={
                "decision": "approved"
            },
            idempotency_key=(
                "resume-stale-version"
            ),
            actor="api",
            expected_job_version=(
                waiting.version - 1
            ),
            expected_wait_generation=(
                waiting.wait_generation
            ),
            now=103.0,
        )


def test_resume_idempotent_replay_wins_over_version(
    tmp_path,
):
    store, _ = _store_and_job(
        tmp_path
    )
    waiting = _mark_waiting(store)
    args = {
        "job_id": waiting.job_id,
        "expected_node": "human_review",
        "value": {
            "decision": "approved"
        },
        "idempotency_key": "resume-replay",
        "actor": "api",
        "expected_job_version": (
            waiting.version
        ),
        "expected_wait_generation": (
            waiting.wait_generation
        ),
        "now": 103.0,
    }

    first, first_created = (
        store.queue_resume(**args)
    )
    second, second_created = (
        store.queue_resume(**args)
    )

    assert first_created is True
    assert second_created is False
    assert (
        first.pending_resume_id
        == second.pending_resume_id
    )


def test_events_after_uses_strict_cursor(
    tmp_path,
):
    store, record = _store_and_job(
        tmp_path
    )
    first_page = store.list_events_after(
        record.job_id,
        after_event_id=0,
    )
    assert first_page

    cursor = first_page[-1].event_id
    assert store.list_events_after(
        record.job_id,
        after_event_id=cursor,
    ) == []


def test_cancel_is_idempotent(
    tmp_path,
):
    store, record = _store_and_job(
        tmp_path
    )

    first = store.request_cancel(
        job_id=record.job_id,
        reason="stop",
        actor="api",
        idempotency_key="cancel-1",
        expected_job_version=record.version,
        now=101.0,
    )
    second = store.request_cancel(
        job_id=record.job_id,
        reason="stop",
        actor="api",
        idempotency_key="cancel-1",
        # 重放时原 version 已经变化，但仍应返回旧命令结果。
        expected_job_version=record.version,
        now=102.0,
    )

    assert first.status == "cancelled"
    assert second.status == "cancelled"
    events = store.list_events(
        record.job_id
    )
    assert [
        item.event_type
        for item in events
    ].count("job_cancelled") == 1


def test_same_cancel_key_rejects_new_reason(
    tmp_path,
):
    store, record = _store_and_job(
        tmp_path
    )
    store.request_cancel(
        job_id=record.job_id,
        reason="first",
        actor="api",
        idempotency_key="cancel-conflict",
        expected_job_version=record.version,
        now=101.0,
    )

    with pytest.raises(
        JobConflictError,
        match="不同请求",
    ):
        store.request_cancel(
            job_id=record.job_id,
            reason="second",
            actor="api",
            idempotency_key=(
                "cancel-conflict"
            ),
            expected_job_version=(
                record.version
            ),
            now=102.0,
        )
```

---

## 二十四、增加 Artifact Catalog 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_interaction_artifacts.py`

完整代码：

```python
import pytest

from app.config import settings
from app.interaction.artifacts import (
    LocalArtifactCatalog,
)
from app.job_runtime.schemas import (
    JobRequest,
)
from app.job_runtime.store import (
    JobConflictError,
    SqliteJobStore,
)
from app.tools.artifact_tools import (
    build_artifact_record,
)


def _job_and_state(
    tmp_path,
    monkeypatch,
):
    runs_root = tmp_path / "runs"
    monkeypatch.setattr(
        settings,
        "runs_dir",
        runs_root,
    )
    run_root = runs_root / "run-artifact"
    target = (
        run_root
        / "reports"
        / "final_report.md"
    )
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    target.write_text(
        "report",
        encoding="utf-8",
    )

    state = {
        "run_id": "run-artifact",
        "run_dir": str(run_root),
    }
    record = build_artifact_record(
        state=state,
        path=target,
        producer_node="test",
    )
    state["artifact_records"] = [
        record.model_dump()
    ]

    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    job, _ = store.submit(
        job_id="job-artifact",
        idempotency_key="submit-artifact",
        thread_id="thread-artifact",
        run_id="run-artifact",
        run_dir=str(run_root),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        max_attempts=3,
    )
    return job, state, record, target


def test_catalog_does_not_expose_absolute_path(
    tmp_path,
    monkeypatch,
):
    job, state, record, _ = (
        _job_and_state(
            tmp_path,
            monkeypatch,
        )
    )
    catalog = LocalArtifactCatalog(
        state_reader=lambda _: state
    )

    dumped = (
        catalog.list_views(job)[0]
        .model_dump()
    )

    assert dumped["artifact_id"] == (
        record.artifact_id
    )
    assert "absolute_path" not in dumped


def test_download_rechecks_hash(
    tmp_path,
    monkeypatch,
):
    job, state, record, target = (
        _job_and_state(
            tmp_path,
            monkeypatch,
        )
    )
    catalog = LocalArtifactCatalog(
        state_reader=lambda _: state
    )
    target.write_text(
        "tampered",
        encoding="utf-8",
    )

    with pytest.raises(
        JobConflictError,
        match="SHA-256|大小",
    ):
        catalog.resolve(
            job=job,
            artifact_id=(
                record.artifact_id
            ),
        )


def test_symlink_escape_is_rejected(
    tmp_path,
    monkeypatch,
):
    job, state, record, target = (
        _job_and_state(
            tmp_path,
            monkeypatch,
        )
    )
    outside = tmp_path / "outside.txt"
    outside.write_text(
        "outside",
        encoding="utf-8",
    )
    target.unlink()
    target.symlink_to(outside)
    catalog = LocalArtifactCatalog(
        state_reader=lambda _: state
    )

    with pytest.raises(
        JobConflictError,
        match="逃逸",
    ):
        catalog.resolve(
            job=job,
            artifact_id=(
                record.artifact_id
            ),
        )
```

---

## 二十五、增加 API 集成测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_interaction_api.py`

完整代码：

```python
from fastapi.testclient import TestClient

from app.api.app import create_api_app
from app.config import settings
from app.interaction.artifacts import (
    LocalArtifactCatalog,
)
from app.job_runtime.schemas import (
    JobInterrupt,
)
from app.job_runtime.service import (
    JobService,
)
from app.job_runtime.store import (
    SqliteJobStore,
)


AUTH = {
    "Authorization": "Bearer test-token"
}


def _client(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    service = JobService(store)
    catalog = LocalArtifactCatalog(
        state_reader=lambda _: {}
    )
    app = create_api_app(
        job_service=service,
        artifact_catalog=catalog,
        api_token="test-token",
    )
    return TestClient(app), service


def _submit(client):
    return client.post(
        "/v1/jobs",
        headers={
            **AUTH,
            "Idempotency-Key": "submit-api-1",
        },
        json={
            "paper_path": "/data/paper.pdf",
            "repo_path": "/data/repo",
            "thread_id": "api-thread-1",
            "experiment_goal": "test",
            "execution_profile_id": "local",
        },
    )


def test_api_requires_token(
    tmp_path,
    monkeypatch,
):
    client, _ = _client(
        tmp_path,
        monkeypatch,
    )

    response = client.get("/v1/jobs")

    assert response.status_code == 401


def test_submit_is_idempotent_and_public(
    tmp_path,
    monkeypatch,
):
    client, _ = _client(
        tmp_path,
        monkeypatch,
    )

    first = _submit(client)
    second = _submit(client)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["replayed"] is True

    body = first.json()["job"]
    assert "run_dir" not in body
    assert "claim_token" not in body
    assert "idempotency_key" not in body
    assert "paper_path" not in body["input"]


def test_stale_decision_returns_409(
    tmp_path,
    monkeypatch,
):
    client, service = _client(
        tmp_path,
        monkeypatch,
    )
    submitted = _submit(client).json()
    job_id = submitted["job"]["job_id"]

    claim = service.store.claim_next(
        worker_id="test-worker",
        lease_seconds=30,
    )
    assert claim is not None
    waiting = service.store.mark_waiting(
        job_id=job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={
                    "action": {
                        "command": "python x.py"
                    }
                },
            )
        ],
        result={},
        actor="test-worker",
    )

    response = client.post(
        f"/v1/jobs/{job_id}/decisions",
        headers={
            **AUTH,
            "Idempotency-Key": (
                "decision-stale"
            ),
        },
        json={
            "expected_job_version": (
                waiting.version - 1
            ),
            "expected_wait_generation": (
                waiting.wait_generation
            ),
            "decision": {
                "kind": "action_approval",
                "decision": "approved",
            },
        },
    )

    assert response.status_code == 409
    assert (
        response.json()["code"]
        == "JOB_CONFLICT"
    )


def test_current_decision_queues_resume(
    tmp_path,
    monkeypatch,
):
    client, service = _client(
        tmp_path,
        monkeypatch,
    )
    submitted = _submit(client).json()
    job_id = submitted["job"]["job_id"]
    claim = service.store.claim_next(
        worker_id="test-worker",
        lease_seconds=30,
    )
    assert claim is not None
    waiting = service.store.mark_waiting(
        job_id=job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={},
            )
        ],
        result={},
        actor="test-worker",
    )

    response = client.post(
        f"/v1/jobs/{job_id}/decisions",
        headers={
            **AUTH,
            "Idempotency-Key": (
                "decision-current"
            ),
        },
        json={
            "expected_job_version": (
                waiting.version
            ),
            "expected_wait_generation": (
                waiting.wait_generation
            ),
            "decision": {
                "kind": "action_approval",
                "decision": "approved",
            },
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["job"]["status"]
        == "queued"
    )
```

### 25.1 为什么测试 App Factory

不要在测试中连接真实：

```text
jobs/runtime.sqlite
checkpoints/langgraph.sqlite
runs/
```

App factory 注入：

```text
tmp_path Job DB
tmp_path runs
fake state_reader
test token
```

这能保证 API 测试离线、可重复且不会污染真实任务。

---

## 二十六、增加 SSE 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_interaction_sse.py`

完整代码：

```python
from fastapi.testclient import TestClient

from app.api.app import create_api_app
from app.config import settings
from app.interaction.artifacts import (
    LocalArtifactCatalog,
)
from app.job_runtime.schemas import (
    JobRequest,
)
from app.job_runtime.service import (
    JobService,
)
from app.job_runtime.store import (
    SqliteJobStore,
)


def test_sse_returns_backlog_after_cursor(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    service = JobService(
        SqliteJobStore(
            tmp_path / "jobs.sqlite"
        )
    )
    job, _ = service.submit(
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        thread_id="sse-thread",
        idempotency_key="sse-submit",
    )
    app = create_api_app(
        job_service=service,
        artifact_catalog=(
            LocalArtifactCatalog(
                state_reader=lambda _: {}
            )
        ),
        api_token="test-token",
    )
    client = TestClient(app)

    response = client.get(
        (
            f"/v1/jobs/{job.job_id}"
            "/events/stream"
            "?after=0&follow=false"
        ),
        headers={
            "Authorization": (
                "Bearer test-token"
            )
        },
    )

    assert response.status_code == 200
    assert "event: job_submitted" in (
        response.text
    )
    assert "id: " in response.text


def test_event_page_cursor_does_not_repeat(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    service = JobService(
        SqliteJobStore(
            tmp_path / "jobs.sqlite"
        )
    )
    job, _ = service.submit(
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        thread_id="cursor-thread",
        idempotency_key="cursor-submit",
    )
    client = TestClient(
        create_api_app(
            job_service=service,
            artifact_catalog=(
                LocalArtifactCatalog(
                    state_reader=lambda _: {}
                )
            ),
            api_token="test-token",
        )
    )
    headers = {
        "Authorization": "Bearer test-token"
    }

    first = client.get(
        f"/v1/jobs/{job.job_id}/events",
        headers=headers,
    ).json()
    second = client.get(
        (
            f"/v1/jobs/{job.job_id}/events"
            f"?after={first['next_after']}"
        ),
        headers=headers,
    ).json()

    assert first["items"]
    assert second["items"] == []
```

---

## 二十七、先做静态检查

> **本节类型：运行验证，不修改项目代码。**

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent

python -m compileall \
  app/interaction \
  app/api \
  app/job_runtime

python -m ruff check \
  --select E4,E7,E9,F \
  app/interaction \
  app/api \
  app/job_runtime/store.py \
  app/job_runtime/service.py \
  app/main.py \
  tests/test_interaction_policy.py \
  tests/test_job_store_interaction_semantics.py \
  tests/test_interaction_artifacts.py \
  tests/test_interaction_api.py \
  tests/test_interaction_sse.py
```

如果 Ruff 报 routes 中 `Path` 未定义，回到第二十二节补 import。

---

## 二十八、运行本阶段测试

> **本节类型：运行验证，不修改项目代码。**

```bash
python -m pytest \
  tests/test_interaction_policy.py \
  tests/test_job_store_interaction_semantics.py \
  tests/test_interaction_artifacts.py \
  tests/test_interaction_api.py \
  tests/test_interaction_sse.py \
  -q
```

然后运行 Phase 22 回归：

```bash
python -m pytest \
  tests/test_job_store.py \
  tests/test_job_heartbeat.py \
  tests/test_job_process_reconcile.py \
  tests/test_job_graph_runner.py \
  tests/test_job_worker.py \
  tests/test_job_cli.py \
  tests/test_job_durable_resume.py \
  -q
```

再运行安全边界相关回归：

```bash
python -m pytest \
  tests/test_command_selection_node.py \
  tests/test_structured_action_and_approval_hash.py \
  tests/test_patch_review_flow.py \
  tests/test_patch_promotion_flow.py \
  tests/test_run_native_artifacts.py \
  tests/test_supervised_process.py \
  -q
```

如果某个测试文件在你的项目中名称不同，使用：

```bash
rg --files tests | rg \
  'command_selection|approval_hash|patch|artifact|supervised'
```

确认实际文件名，不要凭教程猜测。

最后运行全量离线回归：

```bash
python -m pytest -m "not provider" -q
```

---

## 二十九、手工验收准备

> **本节类型：运行验证，不修改项目代码。**

本教程继续使用：

```text
论文：
/data/tianshaoqi24/agent/paper_reproduction_copilot/
pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf

仓库：
/data/tianshaoqi24/PST-Convolution-main/
```

所有读写仍限制在：

```text
/data/tianshaoqi24/
```

进入项目：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent
```

设置本次手工验收专用路径：

```bash
export ALLOWED_ROOT=/data/tianshaoqi24
export RUNS_DIR=/data/tianshaoqi24/agent/paper_reproduction_copilot/runs
export JOB_DB_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/jobs/runtime.sqlite
export CHECKPOINT_DB_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/checkpoints/langgraph.sqlite
```

生成临时 token。它只存在于当前 shell 环境，不写入仓库：

```bash
export AGENT_API_TOKEN="$(
  python -c 'import secrets; print(secrets.token_urlsafe(32))'
)"
```

为了方便后续 curl：

```bash
export API_BASE=http://127.0.0.1:8000
```

---

## 三十、启动 API、Worker 和事件监听

> **本节类型：运行验证，不修改项目代码。**

打开终端 A：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent
python -m app.main serve-api \
  --host 127.0.0.1 \
  --port 8000
```

打开终端 B，并重新设置与终端 A 相同的运行环境变量，然后启动 worker：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent

export ALLOWED_ROOT=/data/tianshaoqi24
export RUNS_DIR=/data/tianshaoqi24/agent/paper_reproduction_copilot/runs
export JOB_DB_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/jobs/runtime.sqlite
export CHECKPOINT_DB_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/checkpoints/langgraph.sqlite

python -m app.main run-worker \
  --worker-id phase23-worker
```

终端 C 用来执行 curl。它也需要设置：

```bash
export API_BASE=http://127.0.0.1:8000
export AGENT_API_TOKEN='终端A使用的同一个token'
```

先检查 liveness：

```bash
curl --fail --silent \
  "$API_BASE/healthz"
```

应得到：

```json
{"status":"ok"}
```

再检查认证：

```bash
curl --silent \
  --output /dev/null \
  --write-out '%{http_code}\n' \
  "$API_BASE/v1/jobs"
```

应得到：

```text
401
```

---

## 三十一、通过 API 提交 PSTNet Job

> **本节类型：运行验证，不修改项目代码。**

```bash
curl --fail --silent \
  --request POST \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --header "Idempotency-Key: phase23-pstnet-submit-001" \
  --header "Content-Type: application/json" \
  --data '{
    "paper_path": "/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf",
    "repo_path": "/data/tianshaoqi24/PST-Convolution-main/",
    "thread_id": "phase23-pstnet-001",
    "experiment_goal": "复现论文 main result",
    "execution_profile_id": "local"
  }' \
  "$API_BASE/v1/jobs"
```

响应应包含：

```json
{
  "job": {
    "job_id": "job_...",
    "thread_id": "phase23-pstnet-001",
    "run_id": "...",
    "status": "queued",
    "version": 0,
    "allowed_operations": []
  },
  "replayed": false
}
```

实际 `allowed_operations` 通常会包含 cancel，以上仅展示关键字段。

必须确认响应中不包含：

```text
run_dir
claim_token
idempotency_key
request_hash
paper_path
repo_path
absolute_path
```

记录响应中的真实 Job ID：

```bash
export JOB_ID=job_实际值
```

使用完全相同的 `Idempotency-Key` 和请求体再次提交，应返回相同 `job_id`：

```json
"replayed": true
```

---

## 三十二、监听 Event Stream

> **本节类型：运行验证，不修改项目代码。**

终端 D：

```bash
export API_BASE=http://127.0.0.1:8000
export AGENT_API_TOKEN='与API一致的token'
export JOB_ID=job_实际值

curl --no-buffer \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID/events/stream?after=0"
```

应逐步看到类似：

```text
id: 1
event: job_submitted
data: {...}

id: 2
event: job_claimed
data: {...}

id: 3
event: job_waiting_for_input
data: {...}
```

记录最后一个 `id`。中断 curl：

```text
Ctrl+C
```

假设最后事件是 3，重新连接：

```bash
curl --no-buffer \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID/events/stream?after=3"
```

不得重复返回 1、2、3。

---

## 三十三、查询当前允许的操作

> **本节类型：运行验证，不修改项目代码。**

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID"
```

当 Job 到达 command selection，应看到：

```json
{
  "status": "waiting_for_input",
  "version": 3,
  "wait_generation": 1,
  "interrupt_nodes": [
    "command_selection"
  ],
  "allowed_operations": [
    {
      "kind": "submit_decision",
      "decision_kind": "command_selection",
      "expected_node": "command_selection",
      "expected_job_version": 3,
      "expected_wait_generation": 1
    }
  ]
}
```

不要照抄示例中的 3 和 1。必须使用当前响应的真实：

```text
version
wait_generation
run_commands_hash
```

---

## 三十四、通过 Artifact API 找到命令选择输入

> **本节类型：运行验证，不修改项目代码。**

列出 Artifact：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID/artifacts"
```

找到：

```text
planning/command_selection_input.json
```

记录对应 `artifact_id`：

```bash
export COMMAND_INPUT_ARTIFACT=artifact_实际值
```

下载到项目内手工验收目录：

```bash
mkdir -p \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase23

curl --fail \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --output \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase23/command_selection_input.json \
  "$API_BASE/v1/jobs/$JOB_ID/artifacts/$COMMAND_INPUT_ARTIFACT/content"
```

检查内容：

```bash
python -m json.tool \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase23/command_selection_input.json
```

这里没有向 API 提交文件路径。下载端点只使用：

```text
job_id + artifact_id
```

---

## 三十五、恢复 Command Selection

> **本节类型：运行验证，不修改项目代码。**

先再次查询 Job，读取最新：

```text
version
wait_generation
run_commands_hash
```

提交示例：

```bash
curl --fail --silent \
  --request POST \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --header "Idempotency-Key: phase23-command-selection-001" \
  --header "Content-Type: application/json" \
  --data '{
    "expected_job_version": 真实version,
    "expected_wait_generation": 真实generation,
    "decision": {
      "kind": "command_selection",
      "selected_index": 0,
      "edits": [],
      "run_commands_hash": "真实run_commands_hash"
    }
  }' \
  "$API_BASE/v1/jobs/$JOB_ID/decisions"
```

因为 JSON 中不能直接写“真实version”，实际执行前请替换为数字。例如：

```json
{
  "expected_job_version": 3,
  "expected_wait_generation": 1,
  "decision": {
    "kind": "command_selection",
    "selected_index": 0,
    "edits": [],
    "run_commands_hash": "abc..."
  }
}
```

响应应变为：

```text
status = queued
```

再次使用相同 key 和相同 body，应该：

```text
replayed = true
不会生成第二条 pending resume
```

---

## 三十六、验证旧 Decision 会被拒绝

> **本节类型：运行验证，不修改项目代码。**

Graph 到达下一个 interrupt 后，再提交上一节完全相同的业务体，但换一个新的
幂等 key：

```bash
curl --silent \
  --request POST \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --header "Idempotency-Key: phase23-stale-decision-001" \
  --header "Content-Type: application/json" \
  --data '{
    "expected_job_version": 旧version,
    "expected_wait_generation": 旧generation,
    "decision": {
      "kind": "command_selection",
      "selected_index": 0,
      "edits": [],
      "run_commands_hash": "旧hash"
    }
  }' \
  "$API_BASE/v1/jobs/$JOB_ID/decisions"
```

应返回：

```text
HTTP 409
code = JOB_CONFLICT
```

这一步证明旧页面不会审批新动作。

---

## 三十七、恢复 Action、Patch 和 Promotion Review

> **本节类型：运行验证，不修改项目代码。**

每到一个新 interrupt，都必须先：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID"
```

### 37.1 Action Review

当前 `decision_kind` 为 `action_approval` 时：

```json
{
  "expected_job_version": 真实值,
  "expected_wait_generation": 真实值,
  "decision": {
    "kind": "action_approval",
    "decision": "approved",
    "feedback": "已检查 command、cwd 和 risk"
  }
}
```

### 37.2 Patch Review

当前 `decision_kind` 为 `patch_review` 时：

```json
{
  "expected_job_version": 真实值,
  "expected_wait_generation": 真实值,
  "decision": {
    "kind": "patch_review",
    "decision": "approved",
    "feedback": "允许进入隔离 worktree 验证"
  }
}
```

### 37.3 Patch Promotion

当前 `decision_kind` 为 `patch_promotion` 时：

```json
{
  "expected_job_version": 真实值,
  "expected_wait_generation": 真实值,
  "decision": {
    "kind": "patch_promotion",
    "decision": "rejected",
    "feedback": "本次只验证，不写回原仓库"
  }
}
```

每一种请求使用新的 `Idempotency-Key`。不要把 command selection 的 key 用在
action review 上。

---

## 三十八、查询日志与最终 Artifact

> **本节类型：运行验证，不修改项目代码。**

查看最近 200 行：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID/logs?lines=200"
```

响应只能返回相对路径，例如：

```text
execution/processes/<execution_id>/combined.log
```

不得返回 `/data/.../runs/...`。

Job 结束后列出 Artifact：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID/artifacts"
```

重点确认：

```text
reports/final_report.md
reports/run_manifest.json
reports/artifact_index.json
```

通过对应 `artifact_id` 下载。不要直接从 API 响应拼本地绝对路径。

---

## 三十九、验证取消与幂等

> **本节类型：运行验证，不修改项目代码。**

新建一个 Job，先查询当前 version，然后：

```bash
curl --fail --silent \
  --request POST \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --header "Idempotency-Key: phase23-cancel-001" \
  --header "Content-Type: application/json" \
  --data '{
    "expected_job_version": 真实version,
    "reason": "Phase 23 manual cancellation test"
  }' \
  "$API_BASE/v1/jobs/$JOB_ID/cancel"
```

相同 key、相同请求再次调用：

```text
返回当前 Job
不重复写 job_cancelled/job_cancel_requested 事件
```

相同 key、不同 reason：

```text
HTTP 409
```

旧 version + 新 key：

```text
HTTP 409
```

---

## 四十、验证 API 重启后仍能续读

> **本节类型：运行验证，不修改项目代码。**

1. 记录当前 `JOB_ID` 和最后 `event_id`；
2. 只停止 API，不停止 worker；
3. 重新执行 `serve-api`；
4. 查询同一个 Job；
5. 从最后 `event_id` 继续 SSE；
6. 重新列出 Artifact。

应满足：

```text
Job 状态仍在 SQLite
事件仍在 SQLite
Graph 状态仍在 checkpoint
Artifact 仍在 run 目录
API 不保存关键会话状态
```

这说明 API 是无状态交互层。后续可以横向扩展，但在横向扩展前仍需要把 SQLite
和本地 Artifact 换成共享后端。

---

## 四十一、直接检查底层事实

> **本节类型：调试验证，不修改项目代码。**

查看 Job version：

```bash
python - <<'PY'
import sqlite3

path = (
    "/data/tianshaoqi24/agent/"
    "paper_reproduction_copilot/"
    "jobs/runtime.sqlite"
)
connection = sqlite3.connect(path)
connection.row_factory = sqlite3.Row

for row in connection.execute(
    """
    SELECT
        job_id,
        status,
        version,
        wait_generation,
        pending_resume_id
    FROM jobs
    ORDER BY created_at DESC
    LIMIT 10
    """
):
    print(dict(row))
PY
```

查看事件游标：

```bash
python - <<'PY'
import sqlite3

path = (
    "/data/tianshaoqi24/agent/"
    "paper_reproduction_copilot/"
    "jobs/runtime.sqlite"
)
connection = sqlite3.connect(path)
connection.row_factory = sqlite3.Row

for row in connection.execute(
    """
    SELECT
        event_id,
        job_id,
        event_type,
        actor
    FROM job_events
    ORDER BY event_id DESC
    LIMIT 30
    """
):
    print(dict(row))
PY
```

查看写命令幂等事实：

```bash
python - <<'PY'
import sqlite3

path = (
    "/data/tianshaoqi24/agent/"
    "paper_reproduction_copilot/"
    "jobs/runtime.sqlite"
)
connection = sqlite3.connect(path)
connection.row_factory = sqlite3.Row

for row in connection.execute(
    """
    SELECT
        command_id,
        job_id,
        command_type,
        idempotency_key,
        request_hash
    FROM job_commands
    ORDER BY created_at DESC
    LIMIT 20
    """
):
    print(dict(row))
PY
```

这些 SQL 只用于调试，不应复制到 API Route。

---

## 四十二、常见问题排查

> **本节类型：故障排查，不修改项目代码。**

### 42.1 `ModuleNotFoundError: No module named 'fastapi'`

执行：

```bash
python -m pip install -e ".[api,dev]"
```

并确认：

```bash
which python
python -m pip --version
```

两者来自同一个 `agent` 环境。

### 42.2 非本机监听被拒绝

如果使用：

```bash
python -m app.main serve-api --host 0.0.0.0
```

必须先设置：

```bash
export AGENT_API_TOKEN='高熵随机值'
```

即使设置 token，也不等于已经具备公网生产安全。还需要 TLS、反向代理、防火墙、
审计、速率限制和 secret 管理。

### 42.3 Decision 返回 409

重新查询：

```text
GET /v1/jobs/{job_id}
```

检查：

```text
status
version
wait_generation
decision_kind
interrupt_nodes
```

不要不断修改 expected 值直到请求成功。必须重新检查当前操作内容。

### 42.4 SSE 一直没有业务事件

SSE keep-alive：

```text
: keep-alive
```

只表示 HTTP 连接仍活着，不表示 worker 仍活着。另查：

```text
Job status
heartbeat_at
lease_expires_at
worker 终端
```

公开 `JobView` 当前不暴露 lease 细节；运维人员可用 Phase 22 CLI 检查内部状态。

### 42.5 SSE 经过 Nginx 后一次性返回

需要关闭代理缓冲。API 已发送：

```text
X-Accel-Buffering: no
Cache-Control: no-cache
```

但反向代理仍可能需要对应配置。本阶段本机直连验收不依赖 Nginx。

### 42.6 Artifact 列表为空

依次检查：

```text
Job thread_id 是否对应正确 checkpoint
checkpoint state 是否有 artifact_records
reports/artifact_index.json 是否存在
ArtifactRecord.run_id 是否等于 Job.run_id
```

不要退化成扫描整个 `runs/` 并把所有文件暴露为 Artifact。

### 42.7 Artifact 下载返回 409

常见原因：

```text
文件被手工修改
文件大小变化
SHA-256 变化
relative_path 指向 symlink 外部
ArtifactRecord 与 run_id 不一致
```

这是完整性保护在生效，不要直接取消 hash 校验。

### 42.8 同一个取消请求产生两条事件

检查：

```text
两次请求是否使用完全相同的 Idempotency-Key
reason 是否完全相同
job_commands 表是否创建
request_cancel 是否先查幂等记录
```

### 42.9 API 与 CLI 结果不一致

检查二者是否使用相同：

```text
JOB_DB_PATH
RUNS_DIR
CHECKPOINT_DB_PATH
conda 环境
当前工作目录
```

相同源码不代表环境变量相同。

---

## 四十三、本阶段 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 43.1 Control Plane 与 Data Plane

```text
Control Plane：
    提交、审批、取消、状态、策略。

Data Plane：
    LLM 调用、代码检索、训练命令、日志和 Artifact。
```

API 是控制面入口，不应直接成为任意 shell 数据面。

### 43.2 Optimistic Concurrency Control

`expected_job_version` 的语义类似：

```sql
UPDATE jobs
SET ...
WHERE job_id = ?
  AND version = expected_version
```

它避免 lost update，但不能替代业务 hash。

### 43.3 Typed Human-in-the-loop

人工输入不是任意字符串，而是有限 schema：

```text
command_selection
action_approval
patch_review
patch_promotion
```

这让权限、审计、重放、测试和前端渲染都有确定边界。

### 43.4 Idempotent Command

每个写操作都看作命令：

```text
Idempotency-Key + canonical request hash
```

相同 key + 相同请求返回旧事实；相同 key + 不同请求返回 conflict。

### 43.5 Event Log 与 Event Sourcing 的区别

本阶段 `job_events` 是审计和流式通知日志，不是完整 Event Sourcing：

```text
Job 当前状态：
    仍由 jobs 表提供。

event：
    用于解释变化和客户端增量通知。
```

不要宣称可以只靠当前 event payload 完整重建所有 Job。

### 43.6 SSE 与 Message Queue 的区别

SSE 是：

```text
服务端 -> 客户端
HTTP 长连接
```

消息队列是：

```text
服务 -> 服务
消费确认、重投递、分区或顺序语义
```

未来可以让 Redis Streams/Kafka 作为内部 EventBus，但浏览器仍通过 SSE。

### 43.7 Capability-oriented API

`allowed_operations` 由服务端生成，客户端不猜状态机：

```text
能否审批
审批类型
当前 version
当前 generation
允许的 decision
```

这比在前端复制一份 Graph 路由规则更可靠。

### 43.8 Public Projection

内部模型和公开模型分离：

```text
JobRecord：
    worker ownership、run_dir、request hash。

JobView：
    用户可见状态和受限操作。
```

必须显式 allowlist，不应 `model_dump()` 后临时删几个字段。

### 43.9 Artifact Addressing

公开地址：

```text
job_id + artifact_id
```

本地实现：

```text
run_root + relative_path
```

对象存储实现：

```text
bucket + object_key
```

公开协议不变，这就是存储可替换性的基础。

---

## 四十四、安全边界复核

> **本节类型：安全清单，不修改项目代码。**

本阶段必须保持：

- 默认只监听 `127.0.0.1`；
- 非 loopback 监听必须有 Bearer Token；
- token 不进入日志、Event、Job DB 和 Artifact；
- 写请求必须有 `Idempotency-Key`；
- Decision 必须校验 Job version；
- Decision 必须校验 wait generation；
- Decision kind 必须与当前 interrupt node 匹配；
- 多个未知 interrupt 时 fail closed；
- 节点原有 action/patch/hash 校验不能删除；
- API 不返回 `claim_token`；
- API 不返回 `run_dir`；
- API 不返回 Artifact `absolute_path`；
- Artifact 下载不接收任意路径；
- Artifact 下载重新校验 run 边界；
- Artifact 下载重新校验 symlink resolve；
- Artifact 下载重新校验 size 和 SHA-256；
- 日志读取只在当前 run 中；
- 错误响应不返回 traceback；
- SSE payload 经过公开投影；
- SSE keep-alive 不冒充 Job heartbeat；
- API 不直接写 SQL；
- API 不自动处理 reconciliation；
- API 不直接执行任意命令；
- API 重启不丢关键状态；
- CORS 默认不开放；
- 第一版不信任代理头；
- 测试不连接真实 Job DB 和 run 目录。

---

## 四十五、完成标准

> **本节类型：最终验收清单，不修改项目代码。**

只有以下全部满足，才算 Phase 23 完成：

- API 可通过 `serve-api` 启动；
- `/healthz` 可用；
- 未授权访问受保护端点返回 401；
- 相同提交 key + 相同 body 返回同一 Job；
- 相同提交 key + 不同 body 返回 conflict；
- JobView 不泄漏内部字段；
- `allowed_operations` 与当前状态一致；
- command selection 使用结构化 Decision；
- action review 使用结构化 Decision；
- patch review 使用结构化 Decision；
- patch promotion 使用结构化 Decision；
- stale version 返回 409；
- stale wait generation 返回 409；
- decision kind 与 node 不匹配返回 409；
- resume 重试不创建第二条 pending resume；
- cancel 重试不写第二条取消事件；
- cancel 相同 key 不同 body 返回 409；
- event page 使用严格大于游标；
- SSE 能从游标续读；
- SSE 断开不影响 Job；
- Artifact 列表不含绝对路径；
- Artifact 下载只接收 artifact_id；
- symlink 路径逃逸被拒绝；
- Artifact hash 不一致被拒绝；
- 日志只返回相对路径；
- API 与 CLI 使用同一个 Job DB 和 JobService；
- API 重启后仍能查询 Job；
- API 重启后仍能续读事件；
- API 重启后仍能列出 Artifact；
- Phase 22 的 23 项现有测试继续通过；
- 全量离线回归通过；
- PSTNet 至少完成一次 API 提交、interrupt、decision 和 artifact 下载。

---

## 四十六、数据库和中间件应该放到哪一阶段

> **本节类型：后续路线说明，不修改项目代码。**

Phase 23 完成后，下一个最值得做的是：

```text
Phase 24：
Persistence Port、Object Storage 与 Backend Migration
```

推荐先定义接口：

```python
class JobRepository:
    ...


class ArtifactStore:
    ...


class CheckpointBackend:
    ...


class EventBus:
    ...


class CacheStore:
    ...
```

并用 contract test 保证：

```text
SqliteJobRepository
    与
MySQL/PostgreSQLJobRepository

LocalArtifactStore
    与
S3/MinIOArtifactStore
```

具有相同业务语义。

推荐迁移顺序：

```text
1. ArtifactStore 抽象；
2. Local + MinIO/S3 双实现；
3. JobRepository 抽象；
4. SQLite + MySQL/PostgreSQL 双实现；
5. Checkpoint backend 迁移；
6. 多 API/worker 实例验证；
7. 出现实时广播需求后引入 Redis Streams；
8. 出现跨主机高吞吐调度需求后评估消息队列。
```

### 46.1 什么情况下才优先引入 Redis

满足至少一个真实需求：

```text
多个 API 实例需要低延迟广播 Job Event
需要跨实例速率限制
需要短期共享缓存
需要分布式协调且数据库锁不合适
```

即使引入 Redis，Job 和审批事实仍应落入持久化数据库。

### 46.2 什么情况下才优先引入消息队列

满足至少一个真实需求：

```text
SQLite 单机 claim 已成为吞吐瓶颈
worker 分布到多台机器
需要按 GPU/CPU/队列类型路由
需要优先级和配额
需要消费组和背压监控
```

消息队列只替换“待处理通知和分发”，不能删除：

```text
JobRepository
claim/fencing
idempotency
reconciliation
ArtifactStore
```

### 46.3 MySQL 还是 PostgreSQL

两者都能实现本项目的 JobRepository。选择时重点比较：

```text
团队现有运维能力
事务和锁语义
JSON 查询需求
SKIP LOCKED 支持
备份恢复
监控体系
云环境托管能力
```

不要因为教程举例就同时维护两套生产数据库。Phase 24 先写 backend contract，
再选择一个真实目标后端实现即可。

---

## 四十七、阶段结论

> **本节类型：总结，不修改项目代码。**

当前“都保存在本地”的问题不能用单一 MySQL、Redis 或 MQ 一次解决。最稳妥的
推进方式是：

```text
先让外部调用方不再依赖本地路径和 SQLite 细节
    ↓
稳定 Job / Decision / Event / Artifact API
    ↓
再把每类数据迁移到最适合的后端
```

Phase 23 的价值不是多了一个 HTTP 壳，而是建立了四个长期稳定的身份：

```text
job_id
artifact_id
event_id
decision generation
```

有了这些边界，下一阶段接入数据库、对象存储和中间件时，Graph 节点、人工审批
语义和客户端协议都不需要推倒重来。
