# 39. Phase 28：分布式可观测性、运行就绪与故障诊断

Phase 27 让论文代码在单主机 OCI 边界内可控执行。本阶段不增加第二台主机，也不先部署一套
庞大的监控平台，而是让当前已经存在的异步组件真正“可解释”：

```text
FastAPI
PostgreSQL Job Store
Worker heartbeat / claim
LangGraph checkpoint
LLM / Embedding Provider
Workspace / Artifact Store
OCI Runtime
```

即使这些组件都跑在同一台机器，它们也跨越了 HTTP、数据库、线程、后台轮询、checkpoint 和
外部进程边界。这里的“分布式可观测性”指的是：一次任务可以跨这些边界被关联和诊断，不等于
本阶段要做多主机部署。

> **本教程中的源码均为待实现代码。**
>
> 本阶段不做多用户、RBAC、tenant 标签或用户级配额。需要修改和新增的文件会逐节注明。

---

## 一、先区分四类运行事实

> **本节类型：知识说明，不修改项目代码。**

### 1.1 Log：某个时刻发生了什么

适合保存：

```text
job_id / run_id / worker_id
stage / node
错误类别与有界错误摘要
container_id
artifact publication 结果
```

### 1.2 Metric：系统整体是否健康

适合聚合：

```text
HTTP 请求数和延迟
Job queue depth / queue wait
claim、heartbeat、reconcile 次数
Graph node / Provider / container 执行耗时
Artifact 发布失败数
readiness 失败数
```

Metric 不适合放 `job_id`、`run_id`、路径、URL、错误消息等无限增长的 label。Prometheus 明确
提醒每组 labels 都会创建新 time series，高基数 label 会显著增加成本：
[Metric and label naming](https://prometheus.io/docs/practices/naming/)。

### 1.3 Trace：一次操作跨组件走了哪条路径

适合回答：

```text
POST /jobs 花了多久？
Job 排队多久后被哪个 Worker claim？
Workspace materialization、Graph、Provider、OCI 哪一步最慢？
一次重试是原 span 的 child 还是新的 attempt？
```

### 1.4 Event / Artifact：可恢复和可审计业务事实

现有 `JobEvent`、checkpoint、run manifest、StageError 和 Artifact 仍是业务事实源。Observability
不能替代它们：日志丢失不能改变 Job 状态，trace backend 不可用也不能阻止业务执行。

---

## 二、本阶段完成定义

> **本节类型：目标说明，不修改项目代码。**

完成后必须满足：

1. API、Worker、Graph、Provider、Workspace、Artifact 和 OCI 使用统一 telemetry context；
2. request/job/run/thread/worker/container 可以在 log 和 trace 中关联；
3. 原始 claim token、API key、Authorization、Prompt、论文正文和签名 URL 不进入 telemetry；
4. Job submit 时持久化 W3C trace carrier，Worker claim 后以 **span link** 关联；
5. 所有日志为结构化 JSON，异常摘要有长度上限和脱敏；
6. metrics 使用固定名称和低基数 labels；
7. `/livez` 只检查进程活性，`/readyz` 检查关键依赖并返回明确降级原因；
8. API 和 Worker 分别有 readiness，不把 Provider 实时调用放进每次健康检查；
9. telemetry exporter 故障时业务继续运行，并记录 bounded internal error；
10. 有 InMemory/NoOp adapter，普通测试不依赖真实 Collector、Prometheus 或 Grafana；
11. 建立最小 SLI/SLO、告警条件和故障排查 runbook；
12. 所有新增测试默认离线，临时文件位于项目 `.pytest-tmp/`。

---

## 三、本阶段明确不做

> **本节类型：范围说明，不修改项目代码。**

```text
不做多用户、tenant_id、RBAC 或用户级 dashboard
不要求部署 Grafana、Jaeger、Tempo、Loki 或 ELK
不把 Job/Run ID 放进 metrics labels
不采集完整 Prompt、模型 raw response 或论文/源码正文
不把健康检查变成昂贵的真实 LLM 调用
不让 exporter 故障阻断 Job
不把 log/trace 当作 checkpoint 或审计状态机
不先做自适应自动扩缩容
```

第一版输出可以是 JSON log + InMemory telemetry；OpenTelemetry/OTLP exporter 是可插拔 adapter。
OpenTelemetry Python 官方文档支持手工创建 spans、attributes、events、links 和 metrics：
[Python manual instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)。

---

## 四、Telemetry 身份模型

> **本节类型：设计说明，不修改项目代码。**

### 4.1 可出现在 log/trace 的关联字段

```text
request_id
trace_id / span_id
job_id
run_id
thread_id
worker_id / worker_session_id / worker_host_id
claim_token_hash（只允许短 hash，不允许原 token）
workspace_manifest_id / assignment_epoch
graph_node / stage / attempt
execution_backend / container_id
```

### 4.2 只能作为 metric 的低基数 labels

```text
component=api|worker|graph|provider|workspace|artifact|oci
operation=submit|claim|heartbeat|invoke|publish|execute|reconcile
outcome=success|failure|cancelled|waiting|degraded
stage=<固定枚举>
backend=local|conda|oci
error_category=<统一错误枚举>
```

### 4.3 永远不采集

```text
Authorization / API token / Provider key
claim token / assignment token / presigned URL query
完整 Prompt、模型 raw output、论文正文和源码内容
任意环境变量全集
用户主目录和无界绝对路径
完整 traceback 作为 metric label
```

---

## 五、异步 Job 为什么要用 span link

> **本节类型：核心知识说明，不修改项目代码。**

API 请求一般几十毫秒到几秒，而 Job 可能排队数分钟、等待人工审批数小时。不能让
`POST /jobs` 的 server span 一直保持打开。

正确关系：

```text
HTTP submit span（结束）
    -> 将 traceparent/tracestate 持久化进 JobRecord

若干分钟后：
Worker claim span（新 trace 或新 root span）
    -- Link --> submit span context
    -> workspace span
    -> graph execute span
    -> node/provider/container child spans
```

Link 表达“由先前异步操作触发”，不会伪装成持续数小时的同步 parent-child 调用。W3C
`traceparent` / `tracestate` 是跨边界传播格式：
[W3C Trace Context](https://www.w3.org/TR/trace-context/)。

---

## 六、文件清单

> **本节类型：实施清单。**

需要新增：

```text
app/observability/__init__.py
app/observability/schemas.py
app/observability/context.py
app/observability/redaction.py
app/observability/ports.py
app/observability/noop.py
app/observability/in_memory.py
app/observability/json_logging.py
app/observability/otel_adapter.py
app/observability/runtime.py
app/observability/readiness.py
app/observability/instrumentation.py
tests/test_telemetry_context.py
tests/test_telemetry_redaction.py
tests/test_json_logging.py
tests/test_metrics_cardinality.py
tests/test_trace_link_propagation.py
tests/test_api_readiness.py
tests/test_worker_readiness.py
tests/test_job_observability.py
```

需要修改：

```text
pyproject.toml
app/config.py
app/job_runtime/schemas.py
app/job_runtime/ports.py
app/job_runtime/service.py
app/job_runtime/worker.py
app/job_runtime/graph_runner.py
app/api/app.py
app/api/routes.py
app/model.py
app/storage/publisher.py
app/execution/container_supervisor.py（Phase 27 已实现时）
app/main.py
```

如果某个 Phase 27 文件尚未实现，先保留 instrumentation helper，不要为通过 import 创建空的
容器模块。

---

## 七、增加可选依赖与配置

> **本节类型：需要修改项目代码。**
>
> 修改：`pyproject.toml`、`app/config.py`、`.env.example`。

`pyproject.toml` 增加可选组：

```toml
[project.optional-dependencies]
# 保留现有 api/storage/dev/postgres 等分组。
observability = [
    "opentelemetry-api>=1,<2",
    "opentelemetry-sdk>=1,<2",
    "opentelemetry-exporter-otlp-proto-http>=1,<2",
]
```

不把 OTel SDK 放入核心依赖：NoOp/InMemory adapter 只使用标准库，普通开发和测试仍能运行。

在 `Settings` 中增加：

```python
@dataclass
class Settings:
    # ...保留已有字段...

    observability_backend: str = os.getenv(
        "OBSERVABILITY_BACKEND", "in_memory"
    ).strip().lower()
    observability_service_name: str = os.getenv(
        "OBSERVABILITY_SERVICE_NAME", "paper-reproduction-copilot"
    )
    otlp_http_endpoint: str | None = (
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip() or None
    )
    telemetry_environment: str = os.getenv(
        "TELEMETRY_ENVIRONMENT", "development"
    )
    telemetry_log_level: str = os.getenv("TELEMETRY_LOG_LEVEL", "INFO")
    telemetry_error_max_chars: int = int(
        os.getenv("TELEMETRY_ERROR_MAX_CHARS", "2000")
    )
    readiness_timeout_seconds: float = float(
        os.getenv("READINESS_TIMEOUT_SECONDS", "2")
    )
```

`.env.example`：

```dotenv
OBSERVABILITY_BACKEND=in_memory
OBSERVABILITY_SERVICE_NAME=paper-reproduction-copilot
OTEL_EXPORTER_OTLP_ENDPOINT=
TELEMETRY_ENVIRONMENT=development
TELEMETRY_LOG_LEVEL=INFO
TELEMETRY_ERROR_MAX_CHARS=2000
READINESS_TIMEOUT_SECONDS=2
```

---

## 八、定义 telemetry schema

> **本节类型：需要新增项目代码。**
>
> 新增：`app/observability/schemas.py`。

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TraceCarrier(TelemetryModel):
    """允许跨数据库边界持久化的最小 W3C carrier。"""

    traceparent: str = Field(min_length=55, max_length=512)
    tracestate: str | None = Field(default=None, max_length=512)

    @field_validator("traceparent")
    @classmethod
    def validate_traceparent(cls, value: str) -> str:
        # 详细语义仍由 OTel propagator 解析，这里先拒绝换行和明显注入。
        if "\n" in value or "\r" in value:
            raise ValueError("traceparent 不能包含换行")
        return value.strip()


class TelemetryContext(TelemetryModel):
    request_id: str | None = None
    job_id: str | None = None
    run_id: str | None = None
    thread_id: str | None = None
    worker_id: str | None = None
    worker_session_id: str | None = None
    worker_host_id: str | None = None
    claim_token_hash: str | None = None
    graph_node: str | None = None
    stage: str | None = None
    execution_backend: str | None = None
    container_id: str | None = None


class MetricPoint(TelemetryModel):
    kind: Literal["counter", "histogram", "gauge"]
    name: str
    value: float
    attributes: dict[str, str] = Field(default_factory=dict)


class SpanLink(TelemetryModel):
    carrier: TraceCarrier
    attributes: dict[str, str] = Field(default_factory=dict)


class ReadinessCheck(TelemetryModel):
    name: str
    status: Literal["ready", "degraded", "not_ready"]
    latency_seconds: float = Field(ge=0)
    detail: str | None = None


class ReadinessReport(TelemetryModel):
    status: Literal["ready", "degraded", "not_ready"]
    component: Literal["api", "worker"]
    checks: list[ReadinessCheck]
    generated_at: str
```

---

## 九、用 contextvars 绑定执行上下文

> **本节类型：需要新增项目代码。**
>
> 新增：`app/observability/context.py`。

```python
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from app.observability.schemas import TelemetryContext


_current_context: ContextVar[TelemetryContext] = ContextVar(
    "paper_copilot_telemetry_context",
    default=TelemetryContext(),
)


def short_secret_hash(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def current_telemetry_context() -> TelemetryContext:
    # 返回不可与 ContextVar 内对象共享可变状态的新模型。
    return _current_context.get().model_copy(deep=True)


@contextmanager
def bind_telemetry_context(**updates: str | None) -> Iterator[TelemetryContext]:
    previous = _current_context.get()
    merged = previous.model_copy(
        update={key: value for key, value in updates.items() if value is not None}
    )
    token = _current_context.set(merged)
    try:
        yield merged
    finally:
        _current_context.reset(token)
```

`contextvars` 能跨 async task 正常传播，但新线程通常需要显式复制/重新 bind。Worker heartbeat
线程只绑定 worker/session，不应误继承某个 Job 的上下文。

---

## 十、统一脱敏

> **本节类型：需要新增项目代码。**
>
> 新增：`app/observability/redaction.py`。

```python
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "token",
    "claim_token",
    "assignment_token",
    "password",
    "secret",
    "cookie",
}


def sanitize_url(value: str) -> str:
    """保留 scheme/host/path，丢弃 userinfo、query 和 fragment。"""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<invalid-url>"
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def redact(value: Any, *, max_chars: int = 2000) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if any(secret in normalized for secret in SENSITIVE_KEYS):
                cleaned[str(key)] = "<redacted>"
            else:
                cleaned[str(key)] = redact(item, max_chars=max_chars)
        return cleaned
    if isinstance(value, list):
        return [redact(item, max_chars=max_chars) for item in value[:100]]
    if isinstance(value, str):
        if value.startswith(("http://", "https://")):
            value = sanitize_url(value)
        return value[:max_chars]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:max_chars]
```

不要只依赖 key 名。现有 `sanitize_error_message()` 仍应在异常入口先做路径/凭据清理，telemetry
redaction 是最后一层防线。

---

## 十一、定义可测试的 TelemetryPort

> **本节类型：需要新增项目代码。**
>
> 新增：`app/observability/ports.py`。

```python
from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol

from app.observability.schemas import SpanLink, TraceCarrier


class SpanPort(Protocol):
    def set_attribute(self, key: str, value: str | int | float | bool) -> None:
        ...

    def add_event(self, name: str, attributes: dict[str, str] | None = None) -> None:
        ...

    def record_exception(self, exc: BaseException) -> None:
        ...

    def carrier(self) -> TraceCarrier | None:
        ...


class TelemetryPort(Protocol):
    def span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        links: list[SpanLink] | None = None,
    ) -> AbstractContextManager[SpanPort]:
        ...

    def counter(self, name: str, value: int, attributes: dict[str, str]) -> None:
        ...

    def histogram(self, name: str, value: float, attributes: dict[str, str]) -> None:
        ...

    def gauge(self, name: str, value: float, attributes: dict[str, str]) -> None:
        ...
```

在 `app/observability/noop.py` 实现所有方法为空操作。业务模块必须依赖这个端口，不要直接在
每个 node 中初始化 OTel SDK。

---

## 十二、InMemory adapter 与 metric cardinality guard

> **本节类型：需要新增项目代码。**
>
> 新增：`app/observability/in_memory.py`、`app/observability/instrumentation.py`。

先建立 metric allowlist：

```python
ALLOWED_METRIC_ATTRIBUTES: dict[str, frozenset[str]] = {
    "paper_copilot_http_requests_total": frozenset({"method", "route", "status_class"}),
    "paper_copilot_http_request_duration_seconds": frozenset({"method", "route"}),
    "paper_copilot_jobs_submitted_total": frozenset({"outcome"}),
    "paper_copilot_jobs_claimed_total": frozenset({"outcome"}),
    "paper_copilot_job_queue_wait_seconds": frozenset({"execution_backend"}),
    "paper_copilot_job_runs_total": frozenset({"outcome", "execution_backend"}),
    "paper_copilot_job_run_duration_seconds": frozenset({"outcome", "execution_backend"}),
    "paper_copilot_graph_node_duration_seconds": frozenset({"node", "outcome"}),
    "paper_copilot_provider_calls_total": frozenset({"operation", "outcome", "provider"}),
    "paper_copilot_provider_duration_seconds": frozenset({"operation", "provider"}),
    "paper_copilot_artifact_publications_total": frozenset({"outcome", "backend"}),
    "paper_copilot_container_runs_total": frozenset({"outcome"}),
    "paper_copilot_reconcile_total": frozenset({"disposition"}),
    "paper_copilot_readiness_checks_total": frozenset({"component", "check", "outcome"}),
}

FORBIDDEN_METRIC_KEYS = {
    "request_id",
    "job_id",
    "run_id",
    "thread_id",
    "worker_id",
    "container_id",
    "path",
    "url",
    "error_message",
}


def validate_metric_attributes(name: str, attributes: dict[str, str]) -> None:
    allowed = ALLOWED_METRIC_ATTRIBUTES.get(name)
    if allowed is None:
        raise ValueError(f"metric 未登记：{name}")
    keys = set(attributes)
    if keys & FORBIDDEN_METRIC_KEYS:
        raise ValueError("metric attributes 含高基数或敏感身份")
    if not keys <= allowed:
        raise ValueError(f"metric attributes 超出 allowlist：{keys - allowed}")
```

InMemory adapter 保存 `MetricPoint` 和 span snapshots，供测试断言。生产 adapter 在 debug 模式也
应调用同一 guard，防止一次代码修改制造 cardinality explosion。

---

## 十三、结构化 JSON 日志

> **本节类型：需要新增项目代码。**
>
> 新增：`app/observability/json_logging.py`。

```python
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.observability.context import current_telemetry_context
from app.observability.redaction import redact


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        context = current_telemetry_context().model_dump(exclude_none=True)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **context,
        }
        extra = getattr(record, "event_fields", None)
        if isinstance(extra, dict):
            payload["fields"] = redact(extra)
        if record.exc_info:
            # 不直接输出无限 traceback；正式实现可写受限 traceback Artifact。
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(redact(payload), ensure_ascii=False, sort_keys=True)


def configure_json_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
```

调用示例：

```python
logger.info(
    "job claimed",
    extra={
        "event_fields": {
            "attempt_count": claim.job.attempt_count,
            "execution_backend": claim.job.requirements.execution_backend,
        }
    },
)
```

不要把动态值拼进 message，例如 `f"job {job_id} failed"`。message 保持稳定，动态信息放入
fields 和 context，便于搜索和聚合。

---

## 十四、OpenTelemetry adapter

> **本节类型：需要新增项目代码。**
>
> 新增：`app/observability/otel_adapter.py`、`app/observability/runtime.py`。

初始化原则：

```text
入口进程初始化一次 SDK
业务模块只拿 TelemetryPort
没有 optional dependency 时回退 NoOp/InMemory
exporter 异常不抛进业务路径
shutdown 时 flush 有时间上限
```

最小初始化骨架：

```python
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def build_otel_provider(*, service_name: str, environment: str, endpoint: str):
    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment.name": environment,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
        )
    )
    trace.set_tracer_provider(provider)
    return provider
```

正式 adapter 还需：

```text
使用 W3C propagator inject/extract TraceCarrier
把 SpanLink 转换为 opentelemetry.trace.Link
统一 attribute 类型与长度
调用 validate_metric_attributes
异常时 record_exception + ERROR status
shutdown 时 provider.force_flush()/shutdown()
```

第一轮不要启用 OTel experimental log signal。结构化日志用标准库，trace/metrics 用 OTel，避免
日志 API 版本变化阻塞项目。

---

## 十五、持久化 submit trace carrier

> **本节类型：需要修改项目代码和数据库 migration。**
>
> 修改：`app/job_runtime/schemas.py`、`app/job_runtime/ports.py`、JobStore 实现、
> `app/job_runtime/service.py`、`app/api/routes.py`。

在 `JobRecord` 增加：

```python
from app.observability.schemas import TraceCarrier


class JobRecord(JobModel):
    # ...保留已有字段...
    submit_trace: TraceCarrier | None = None
```

`JobStore.submit()` 增加：

```python
def submit(
    self,
    *,
    # ...保留已有参数...
    submit_trace: TraceCarrier | None,
    now: float | None = None,
) -> tuple[JobRecord, bool]:
    ...
```

PostgreSQL migration 增加 nullable JSONB 或两个 nullable text 字段。Trace carrier 不应参与业务
`request_hash` 和 idempotency 判断，因为采样决策变化不能让同一 Job 变成不同业务请求。

API submit 路由：

```python
with telemetry.span(
    "job.submit",
    attributes={"app.operation": "submit"},
) as span:
    carrier = span.carrier()
    job, created = service.submit(
        request=job_request,
        idempotency_key=idempotency_key,
        submit_trace=carrier,
    )
```

如果重复 idempotency key 返回旧 Job，不覆盖旧 `submit_trace`，只在当前 span 上记录
`job.idempotent_replay=true`。

---

## 十六、API request instrumentation

> **本节类型：需要修改项目代码。**
>
> 修改：`app/api/app.py`。

保留现有 request ID middleware，并绑定 context：

```python
import time

from app.observability.context import bind_telemetry_context


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = (
        request.headers.get("X-Request-ID") or f"request_{uuid4().hex}"
    )[:200]
    request.state.request_id = request_id
    started = time.monotonic()
    response = None

    with bind_telemetry_context(request_id=request_id):
        with telemetry.span(
            "http.request",
            attributes={
                "http.request.method": request.method,
            },
        ) as span:
            try:
                response = await call_next(request)
                outcome = "success"
            except Exception:
                outcome = "failure"
                raise
            finally:
                # Starlette 完成路由匹配后，scope 中才有 route template。
                # 不能退回 request.url.path，否则 job_id 会制造高基数 label。
                route_template = getattr(
                    request.scope.get("route"), "path", "unmatched"
                )
                span.set_attribute("http.route", route_template)
                duration = time.monotonic() - started
                telemetry.histogram(
                    "paper_copilot_http_request_duration_seconds",
                    duration,
                    {"method": request.method, "route": route_template},
                )

    # 正常路径一定有 response；异常会在上面重新抛给统一 error handler。
    assert response is not None
    response.headers["X-Request-ID"] = request_id
    return response
```

注意使用 route template `/v1/jobs/{job_id}`，不能把实际 `/v1/jobs/job_abcd...` 作为 label。
统一 exception handler 负责补充 5xx counter；middleware 的 `finally` 只负责不会遗漏的耗时指标。

---

## 十七、Worker claim 与 Job span

> **本节类型：需要修改项目代码。**
>
> 修改：`app/job_runtime/worker.py`。

在 `claim_next()` 成功后绑定上下文并创建带 link 的 span：

```python
from app.observability.context import bind_telemetry_context, short_secret_hash
from app.observability.schemas import SpanLink


links = (
    [SpanLink(carrier=claim.job.submit_trace, attributes={"link.kind": "job_submit"})]
    if claim.job.submit_trace is not None
    else []
)

with bind_telemetry_context(
    job_id=claim.job.job_id,
    run_id=claim.job.run_id,
    thread_id=claim.job.thread_id,
    worker_id=self.worker_id,
    worker_session_id=claim.worker.worker_session_id,
    worker_host_id=claim.worker.host_id,
    claim_token_hash=short_secret_hash(claim.claim_token),
):
    with self.telemetry.span(
        "job.execute",
        attributes={
            "job.attempt": claim.job.attempt_count,
            "execution.backend": claim.job.requirements.execution_backend,
        },
        links=links,
    ) as span:
        # 原有 heartbeat/workspace/runner/publication/mark_* 流程放在这里。
        ...
```

不要在 telemetry 中记录 `claim.claim_token`。Job 进入 terminal 后，span outcome 和
`paper_copilot_job_runs_total` 必须在同一个 finally/结果分类函数中生成，避免日志说 success、
metric 却记 failure。

---

## 十八、Graph node instrumentation

> **本节类型：需要新增和修改项目代码。**
>
> 新增：`app/observability/instrumentation.py`。
>
> 修改：`app/graph.py` 或节点注册位置。

不要逐个复制 try/except。使用包装器：

```python
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.observability.context import bind_telemetry_context


def instrument_node(name: str, node: Callable, telemetry):
    def wrapped(state: dict[str, Any], *args: Any, **kwargs: Any):
        started = time.monotonic()
        outcome = "success"
        with bind_telemetry_context(graph_node=name, stage=name):
            with telemetry.span(
                "graph.node",
                attributes={"graph.node.name": name},
            ) as span:
                try:
                    return node(state, *args, **kwargs)
                except Exception as exc:
                    outcome = "failure"
                    span.record_exception(exc)
                    raise
                finally:
                    telemetry.histogram(
                        "paper_copilot_graph_node_duration_seconds",
                        time.monotonic() - started,
                        {"node": name, "outcome": outcome},
                    )
    return wrapped
```

`name` 必须来自 Graph 注册时的固定节点集合，不能使用 LLM 返回文本。

---

## 十九、Provider instrumentation

> **本节类型：需要修改项目代码。**
>
> 修改：`app/model.py` 和结构化输出统一调用层。

Provider span 只记录：

```text
provider/model 的配置名
operation=paper_summary|mapping|plan|section_extract|embedding
attempt
structured output method
latency
token usage（Provider 返回时）
outcome/error_category
```

不能记录：

```text
Prompt 正文
paper_text/source code
raw response
API key/base URL query
```

示意：

```python
with telemetry.span(
    "provider.invoke",
    attributes={
        "gen_ai.provider.name": provider_name,
        "gen_ai.request.model": model_name,
        "app.operation": operation,
        "app.attempt": attempt,
    },
) as span:
    try:
        result = structured_llm.invoke(prompt)
    except Exception as exc:
        span.record_exception(exc)
        telemetry.counter(
            "paper_copilot_provider_calls_total",
            1,
            {"operation": operation, "outcome": "failure", "provider": provider_name},
        )
        raise
```

如果已有 Phase 17 structured trace Artifact，不要重复写 raw/parsed 内容到 OTel；只在 span 中写
该 Artifact 的 ID 或相对路径摘要。

---

## 二十、Workspace、Artifact 和 OCI instrumentation

> **本节类型：需要修改项目代码。**
>
> 修改：`app/workspace/manager.py`、`app/storage/publisher.py`、
> `app/execution/container_supervisor.py`（已实现时）。

建议 spans：

```text
workspace.prepare
workspace.materialize
workspace.verify
workspace.seal
artifact.publish
artifact.put_blob
container.create
container.start_attach
container.inspect
container.stop
container.reconcile
```

Artifact span 记录 `media_type`、backend、size bucket 和 outcome，不记录 object key 中可能出现的
敏感路径。Container span 可以记录 container ID，因为它是 trace/log 查询身份，但不能作为 metric
label。

---

## 二十一、实现 readiness probes

> **本节类型：需要新增项目代码。**
>
> 新增：`app/observability/readiness.py`。

```python
from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timezone
from typing import Literal

from app.observability.redaction import redact
from app.observability.schemas import ReadinessCheck, ReadinessReport


class ReadinessProbe:
    def __init__(
        self,
        *,
        name: str,
        check: Callable[[], None],
        critical: bool,
    ):
        self.name = name
        self.check = check
        self.critical = critical


class ReadinessService:
    def __init__(
        self,
        *,
        component: Literal["api", "worker"],
        probes: list[ReadinessProbe],
        timeout_seconds: float,
    ):
        names = [probe.name for probe in probes]
        if len(names) != len(set(names)):
            raise ValueError("readiness probe name 重复")
        self.component = component
        self.probes = probes
        self.timeout_seconds = timeout_seconds
        # 持久 executor 限制并发数，避免每次请求创建无限线程。
        self.executor = ThreadPoolExecutor(
            max_workers=max(1, len(probes)),
            thread_name_prefix=f"{component}-readiness",
        )

    def check(self) -> ReadinessReport:
        results: list[ReadinessCheck] = []
        critical_failed = False
        degraded = False

        for probe in self.probes:
            started = time.monotonic()
            future = self.executor.submit(probe.check)
            try:
                future.result(timeout=self.timeout_seconds)
                status = "ready"
                detail = None
            except FutureTimeout:
                future.cancel()
                status = "not_ready" if probe.critical else "degraded"
                detail = "readiness check timeout"
                critical_failed = critical_failed or probe.critical
                degraded = degraded or not probe.critical
            except Exception as exc:  # noqa: BLE001
                status = "not_ready" if probe.critical else "degraded"
                detail = str(redact(str(exc), max_chars=300))
                critical_failed = critical_failed or probe.critical
                degraded = degraded or not probe.critical

            results.append(
                ReadinessCheck(
                    name=probe.name,
                    status=status,
                    latency_seconds=time.monotonic() - started,
                    detail=detail,
                )
            )

        overall = (
            "not_ready" if critical_failed else "degraded" if degraded else "ready"
        )
        return ReadinessReport(
            status=overall,
            component=self.component,
            checks=results,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
```

`future.cancel()` 不能中断已经进入阻塞系统调用的线程，所以每个数据库、对象存储和 runtime
adapter 本身仍必须设置连接/读取 timeout。Executor 只是 endpoint 的第二层总预算。

### API probes

```text
critical: JobStore.ping()
critical: BlobStore.ensure_ready() / Artifact repository lightweight check
critical: checkpoint backend lightweight connection check
non-critical: 至少一个 Worker session 新鲜且满足默认 profile
non-critical: telemetry exporter 最近是否成功
```

### Worker probes

```text
critical: JobStore.ping()
critical: workspace root 可创建、写入、fsync、删除项目内 probe 文件
critical: 当前 execution profile probe
critical: Artifact backend ensure_ready
non-critical: telemetry exporter
```

不要在 readiness 中调用真实 LLM。Provider 暂时不可用应由最近调用指标和告警反映，而不是让
每次 `/readyz` 都花钱、触发限流或泄露 Prompt。

---

## 二十二、增加 livez、readyz 和 metrics endpoint

> **本节类型：需要修改项目代码。**
>
> 修改：`app/api/app.py`。

```python
from fastapi import Response, status


@app.get("/livez")
def livez() -> dict[str, str]:
    # 只证明事件循环/进程能响应，不访问任何外部依赖。
    return {"status": "alive"}


@app.get("/readyz")
def readyz(response: Response) -> dict:
    report = app.state.api_readiness.check()
    if report.status == "not_ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report.model_dump(mode="json")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    # 兼容旧调用；语义等同 livez，并在文档中标记 deprecated。
    return {"status": "ok"}
```

`/metrics` 只在 Prometheus adapter 启用时注册。虽然本阶段不做多用户，仍不要把 metrics endpoint
暴露到公网；最简单做法是仅监听管理网卡或由反向代理限制来源。

---

## 二十三、运行就绪不是只有 HTTP endpoint

> **本节类型：需要修改项目代码。**
>
> 修改：`app/main.py`。

增加 CLI：

```bash
python -m app.main readiness --component api
python -m app.main readiness --component worker
python -m app.main observability-doctor
```

`observability-doctor` 建议检查：

```text
JSON logger 能否输出
Telemetry backend 是否构造成功
OTLP endpoint 是否配置（不发送测试 Prompt）
InMemory counter/span 是否可写
metric allowlist 是否完整
readiness probes 名称是否唯一
当前日志是否意外包含环境变量 secret key 名
```

返回码：ready=0，degraded=0，not_ready=1。这样本地脚本和 systemd 都能使用同一语义。

---

## 二十四、建议的 SLI、SLO 与告警

> **本节类型：运维设计，不修改项目代码。**

第一版先写目标，不需要立即部署告警平台。

### 24.1 API

```text
SLI: 非 5xx 请求比例
SLI: POST /jobs p95 latency
SLO: 7 天窗口 API 非 5xx >= 99.5%
```

### 24.2 Job Runtime

```text
SLI: queue wait p95
SLI: claim 后 heartbeat freshness
SLI: 非业务错误导致的 retry/reconcile 比例
SLO: 有兼容 Worker 时 95% Job 在 60 秒内被 claim
```

### 24.3 Artifact / Workspace

```text
SLI: publication success rate
SLI: materialization verify failure rate
SLO: Artifact publish 非输入错误成功率 >= 99%
```

### 24.4 OCI

```text
SLI: create-before-start record 成功率
SLI: active managed container cleanup lag
SLI: ambiguous reconcile 数
```

本阶段不把“论文复现成功率”作为基础设施 SLO。论文结果失败可能是数据、代码、环境或研究方法
本身问题，不等同于系统不可用。

建议告警：

```text
API readyz 连续 3 次 not_ready
running Job heartbeat lag > lease/2
queued Job 有兼容 Worker但等待超过阈值
reconciliation_required 持续增加
Artifact publish failure rate 突升
managed container 在 terminal Job 后仍 active
Provider failure rate 或 latency 突升
```

---

## 二十五、故障诊断 runbook

> **本节类型：运维文档，不修改项目代码。**

### 25.1 Job 一直 queued

1. 查看 worker session freshness；
2. 比较 JobRequirements 与 Worker capability；
3. 查看 `jobs_claimed_total{outcome="no_compatible_worker"}`；
4. 检查 JobStore readiness；
5. 不要直接改数据库状态。

### 25.2 Job running 但无进展

1. 用 job_id 查 log/trace；
2. 检查 heartbeat_at 和 lease_expires_at；
3. 查看当前 graph node/span；
4. 查看 active process/container record；
5. 如果 container 状态不明确，进入 reconciliation，不盲目 requeue。

### 25.3 Provider 慢

1. 看 provider duration histogram；
2. 按固定 operation/provider 维度比较；
3. 检查 structured retry attempt；
4. 从 run Artifact 查看有界 structured trace；
5. 不在日志中打印完整 Prompt 或 raw response。

### 25.4 Artifact publish 失败

1. 查看 BlobStore 与 repository readiness；
2. 区分 put blob 与 metadata publish；
3. 检查 expected sha/size；
4. 保留 run-native Artifact，不删除 workspace；
5. 由原 claim fencing 下重试 publication。

---

## 二十六、测试教程

> **本节类型：需要新增测试代码。**

### 26.1 Context 隔离

`tests/test_telemetry_context.py`：

```text
嵌套 bind 后正确恢复上层 context
两个 async task 的 job_id 不串线
新线程未显式 bind 时不继承 Job context
claim_token 只产生 hash
```

### 26.2 脱敏

`tests/test_telemetry_redaction.py`：

```text
Authorization/api_key/token/password 被替换
URL query/userinfo/fragment 被移除
长错误被截断
嵌套 dict/list 也脱敏
```

### 26.3 Metric 基数

`tests/test_metrics_cardinality.py`：

```python
import pytest

from app.observability.instrumentation import validate_metric_attributes


def test_metric_rejects_job_id_label():
    with pytest.raises(ValueError, match="高基数"):
        validate_metric_attributes(
            "paper_copilot_jobs_submitted_total",
            {"outcome": "success", "job_id": "job_123"},
        )


def test_metric_accepts_fixed_outcome_label():
    validate_metric_attributes(
        "paper_copilot_jobs_submitted_total",
        {"outcome": "success"},
    )
```

### 26.4 Trace link

`tests/test_trace_link_propagation.py`：

```text
submit carrier 被写入 JobRecord
idempotency replay 不覆盖旧 carrier
claim span 创建一个 job_submit link
缺少 carrier 时仍可执行
非法 traceparent 被 schema 拒绝
raw claim token 不出现在 span snapshot
```

### 26.5 Readiness

`tests/test_api_readiness.py`、`tests/test_worker_readiness.py`：

```text
livez 不调用任何依赖
critical probe 失败 -> 503/not_ready
non-critical probe 失败 -> 200/degraded
所有 probe 成功 -> 200/ready
错误 detail 有界且脱敏
readiness 不调用 Provider
```

### 26.6 Worker 故障路径

`tests/test_job_observability.py`：

```text
success/failure/cancel/waiting 各产生一次终态 metric
LeaseLost 不被错误记录为普通 Job failure
ArtifactBackendUnavailable 保留 retryable 分类
telemetry adapter 抛错不会覆盖原业务异常
job context 在 run_once 结束后被清理
```

---

## 二十七、完整测试命令

> **本节类型：验证步骤，不修改项目代码。**

```bash
mkdir -p .pytest-tmp
python -m pytest -q \
  --basetemp=.pytest-tmp/phase28 \
  tests/test_telemetry_context.py \
  tests/test_telemetry_redaction.py \
  tests/test_json_logging.py \
  tests/test_metrics_cardinality.py \
  tests/test_trace_link_propagation.py \
  tests/test_api_readiness.py \
  tests/test_worker_readiness.py \
  tests/test_job_observability.py
```

API/Job 回归：

```bash
python -m pytest -q \
  --basetemp=.pytest-tmp/phase28-regression \
  tests/test_job_api.py \
  tests/test_job_worker.py \
  tests/test_postgres_job_store.py \
  tests/test_artifact_api.py \
  tests/test_job_process_reconcile.py
```

全量离线：

```bash
python -m pytest -q \
  -m 'not provider and not postgres and not container_runtime' \
  --basetemp=.pytest-tmp/phase28-all
```

静态检查：

```bash
python -m compileall -q app tests
ruff check app tests
```

---

## 二十八、手工验收

> **本节类型：手工操作，不修改项目代码。**

1. 以 `OBSERVABILITY_BACKEND=in_memory` 启动 API 和 Worker；
2. 调用 `/livez`，确认它不访问 PostgreSQL、Artifact 或 Provider；
3. 调用 `/readyz`，确认各依赖有独立 check；
4. 提交一个 Job，记录响应中的 `X-Request-ID`；
5. 用 job_id 搜索 JSON log，确认可串起 submit、claim、workspace、graph、artifact；
6. 检查 submit span 和 worker Job span 通过 link 关联，而非长时间 parent span；
7. 让 Job 进入 human interrupt，确认 waiting 时 span 正常结束；
8. resume 后确认新 attempt span 仍关联同一 Job，但 attempt 值变化；
9. 临时停止 Artifact backend，确认 `/readyz` 变为 not_ready，`/livez` 仍 alive；
10. 恢复依赖，确认 readiness 自动恢复；
11. 搜索日志，确认没有 API key、Authorization、claim token、Prompt 或 URL query；
12. 检查 metric snapshots，确认 labels 中没有任何 ID 或路径。

---

## 二十九、常见错误

> **本节类型：问题排查，不修改项目代码。**

### 29.1 每个 Job 都产生一组 metric label

原因：把 job_id/run_id 当 labels。解决：ID 只进 log/span，metric 只保留固定 outcome/stage/backend。

### 29.2 Worker trace 和 API trace 完全断开

原因：submit carrier 没有持久化，或 Worker 把它当普通字符串而没有 extract/link。解决：使用
`TraceCarrier` schema，并在 claim span 创建 `Link`。

### 29.3 readiness 经常超时

原因：probe 做了真实 Provider 调用、大文件读写或完整 bucket listing。解决：只做最小、只读、
有界检查；昂贵诊断放 doctor 命令。

### 29.4 exporter 挂了导致 Job 失败

原因：telemetry adapter 异常穿透业务代码。解决：adapter 内 fail-open，记录有界 internal error，
业务状态只由原逻辑决定。

### 29.5 日志有关联字段但无法检索

原因：每条 message 都是动态字符串。解决：稳定 message + structured fields + context。

---

## 三十、本阶段 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 30.1 Observability 是 Agent 的外部记忆索引

Checkpoint 保存“下一步怎么继续”；telemetry 保存“为什么走到这里、哪个边界慢或失败”。两者
结合，才能诊断长运行 Agent。

### 30.2 异步因果不等于同步调用栈

队列/数据库 claim 后的工作不是 HTTP span 的长子调用。持久 carrier + span link 更准确地表达
异步因果。

### 30.3 Metric 必须先控制基数

Agent 天然产生大量动态 ID、节点、模型文本和路径。如果不先建立 allowlist，监控系统会被
自身 telemetry 拖垮。

### 30.4 Readiness 是调度契约

Liveness 只回答进程是否活着；readiness 回答当前是否应该接收/claim 工作。错误地把二者混合，
会造成服务重启风暴或 Job 被不可用 Worker 领取。

### 30.5 可观测性不能改变业务真相

Exporter、Collector 或 dashboard 都不是 Job Store。任何 telemetry 故障都不能伪造成功、覆盖
StageError 或破坏 lease fencing。

---

## 三十一、完成标准

> **本节类型：最终验收，不修改项目代码。**

- request/job/run/worker/node/provider/container 能通过 log/trace 关联；
- submit trace carrier 持久化，Worker 使用 span link；
- JSON log 统一、脱敏、有界；
- metrics 有 allowlist，测试拒绝高基数 labels；
- `/livez`、`/readyz` 和 Worker readiness 语义分离；
- Provider 不参与频繁健康检查；
- telemetry adapter 故障不影响业务；
- success/failure/cancel/waiting/reconcile 均有一致信号；
- runbook 能定位 queued、stuck、Provider 慢和 Artifact 失败；
- 普通测试不依赖外部 observability backend；
- 项目没有引入多用户/RBAC/tenant 复杂度。

---

## 三十二、下一阶段

下一阶段实现：

```text
Phase 29：受控资源获取、不可变输入清单与供应链安全
```

Phase 28 先让我们能观察下载请求、字节数、耗时、拒绝原因和失败位置；Phase 29 再把论文 PDF、
Git 仓库和 checkpoint 从“任意本地路径/执行时联网”升级为“策略校验 -> 受控下载 -> hash/type
验证 -> Object Storage 发布 -> Workspace 只读物化”的输入闭环。
