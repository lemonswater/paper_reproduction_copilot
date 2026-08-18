# Phase 54：论文复现 Agent 只读 MCP Server Export、公开投影与本地访问控制

> 本阶段类型：需要新增源码、修改现有源码并补充测试。  
> 当前状态：实现教程；项目源码需要你按照本文逐步落地。  
> 推荐运行环境：项目原有 Python 3.10 虚拟环境。  
> 前置阶段：Phase 40 Tool Contract、Phase 41 Secret、Phase 52 Bounded Tool Calling、Phase 53 MCP Client Gateway。  
> 默认开关：`MCP_EXPORT_ENABLED=false`。  
> 第一版部署：单机、单用户、独立 loopback Streamable HTTP 服务。  
> 第一版协议与 SDK：MCP Specification `2026-07-28`、官方 Python SDK `mcp>=2.0,<3`。

---

## 一、为什么 Phase 54 优先做 MCP Server Export

Phase 53 让当前项目具备了 MCP Client 能力：

```text
论文复现 Agent
  -> 本地受约束 Tool Calling
  -> MCP Gateway
  -> 经过固定 Schema Pin 的外部只读 Tool
  -> 本地 Evidence Pack 和 Citation
```

但当前项目自己的复现状态、最终报告和证据仍只能通过项目 Web/API/CLI 使用。如果另一个可信 Agent、IDE
或自动化 Host 想读取复现结果，就需要重新理解本项目私有 HTTP API。

Phase 54 反转协议方向：

```text
Phase 53：本项目是 MCP Client，消费外部证据。
Phase 54：本项目是 MCP Server，导出本项目已有的只读证据。
```

一个实际场景是：

```text
用户在另一个 MCP Host 中提问：
“job_... 当前复现到哪一步，失败原因是什么？”

Host 调用：
get_reproduction_status(job_id)
search_reproduction_evidence(job_id, query="失败原因", limit=4)

本项目返回：
公开 Job 状态
+ 有界 Evidence excerpt
+ Artifact/Event 内容身份
+ Citation ID
```

外部 Host 不需要知道 LangGraph checkpoint、SQLite 表、Run 目录或 Artifact BlobStore 的实现方式，也不能
直接访问这些内部对象。

### 1.1 为什么不是直接把 FastAPI 路由改名为 MCP Tool

REST API 和 MCP Tool 的边界不同：

```text
REST API：面向前端和确定性客户端。
MCP Tool：可能由模型选择并填充参数。
```

如果直接把 `/v1/jobs/{job_id}`、Artifact 下载或 Decision API 原样导出，会产生四个问题：

1. 内部 API 字段可能包含 MCP 场景不应该暴露的路径、操作入口或错误详情；
2. REST API 的某些写操作会被错误加入 Tool Catalog；
3. 模型可以尝试构造 Artifact 路径或任意对象 ID；
4. MCP 调用缺少独立的调用预算、审计 Hash 和只读能力证明。

本阶段因此增加一个独立的 **MCP Public Projection**：只从现有可信 Service 读取，再构造更窄的 MCP 输出。

### 1.2 为什么第一版仍然使用独立进程

官方 Python SDK 2.x 的 `streamable_http_app()` 会创建带自身 lifespan/session manager 的 ASGI 应用。把它
Mount 到已有 FastAPI 时，顶层应用必须显式接管 MCP session manager 的生命周期；遗漏后服务虽然能启动，
首个 MCP 请求却会失败。

第一版使用独立命令：

```bash
python -m app.main serve-mcp-export
```

这样可以得到更清晰的边界：

```text
主 API：127.0.0.1:8000
MCP Export：127.0.0.1:8770/mcp
```

关闭 MCP Export 不影响主 API、Worker、Graph 或 Phase 53 MCP Client Gateway。

### 1.3 官方资料与版本说明

本文按 2026-08-14 的官方稳定接口编写：

- [MCP Python SDK v2](https://py.sdk.modelcontextprotocol.io/)：使用 `MCPServer` 定义 Tool 和 Resource；
- [将 MCP Server 作为 ASGI 应用运行](https://py.sdk.modelcontextprotocol.io/run/asgi/)：`streamable_http_app()`、lifespan 和 DNS rebinding 防护；
- [Structured Tool Output](https://py.sdk.modelcontextprotocol.io/server/)：Pydantic 返回类型会生成并校验 output schema；
- [MCP Authorization](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/authorization)：远程生产部署应使用标准 OAuth 2.1 资源服务器；
- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)：本机 HTTP MCP Server 仍应限制监听范围并要求访问凭证。

本阶段只做单机单用户，因此使用项目 Secret Vault 中的独立静态 Bearer Token，不实现 OAuth、动态客户端注册
或多租户 Scope。这个简化只适用于 `127.0.0.1`；未来监听非 loopback 地址前必须替换为标准 OAuth 资源服务器。

---

## 二、Phase 53 完成后的真实基线

开始前先运行：

```bash
python -m pytest -q \
  tests/test_mcp_gateway_schemas.py \
  tests/test_mcp_gateway_policy.py \
  tests/test_mcp_gateway_repository.py \
  tests/test_mcp_gateway_gateway.py \
  tests/test_mcp_gateway_authority.py \
  tests/test_tool_calling_catalog.py \
  tests/test_tool_calling_chat_integration.py \
  tests/test_tool_calling_authority.py
```

本文编写时，这组测试结果为：

```text
40 passed
```

当前关键实现包括：

- `app/mcp_gateway/`：本项目作为 MCP Client 时的只读远端证据网关；
- `app/tool_calling/evidence_tools.py`：三个本地高层 Evidence Tool；
- `app/tool_contracts/registry.py`：Tool Exposure、Capability、Schema、错误和 Audit 边界；
- `app/interaction/service.py`：把内部 `JobRecord` 投影为不含绝对路径的 `JobView`；
- `app/artifact_delivery/service.py`：Artifact 元数据、受限文本预览、完整性校验；
- `app/secrets/`：本地加密 Secret Store 和用途约束；
- `app/observability/`：request/job 关联、结构化日志和 Telemetry。

Phase 54 必须复用这些边界，而不是从 MCP handler 中执行 SQL 或拼接文件路径。

---

## 三、本阶段目标

完成后系统应具备：

1. 独立的本机 Streamable HTTP MCP Server；
2. 独立 Bearer Token，不复用 Provider Key 或主 API Token；
3. 四个静态只读 Tool；
4. 两个公开 Resource Template；
5. Pydantic structured output 和稳定 Schema；
6. Job ID、查询长度、结果数量和响应字符预算；
7. 复用现有 `ToolRegistry` 的 Evidence 检索；
8. Artifact 只返回公开 metadata，不返回绝对路径、object key 或下载 URL；
9. 只允许读取服务端识别出的 `final_report.md`，不提供任意 Artifact 内容读取；
10. Hash-only 调用审计，不保存 Token、原始 query 或完整输出；
11. 单进程速率限制和稳定公开错误；
12. Retention 删除 Job 时同步删除 MCP Export Audit；
13. In-memory MCP Client、ASGI Auth、Authority 和回归测试；
14. Feature Flag 可独立关闭。

### 3.1 第一版公开的 Tool

```text
get_reproduction_status
list_reproduction_artifacts
read_reproduction_final_report
search_reproduction_evidence
```

### 3.2 第一版公开的 Resource

```text
repro://jobs/{job_id}/status
repro://jobs/{job_id}/final-report
```

Tool 适合模型按问题调用；Resource 适合 Host 或用户显式读取。两者最终都调用同一个
`ReadOnlyMcpExportService`，不能形成两套权限逻辑。

---

## 四、本阶段明确不做什么

第一版不实现：

- 不导出 `submit_decision`；
- 不导出 `approve`、`reject` 或命令选择；
- 不导出 `run`、`rerun`、`cancel`、`patch` 或资源下载；
- 不暴露 Shell、Executor、Human Review 或 Repair Node；
- 不提供任意文件路径、Artifact path 或 URI 读取；
- 不提供 Job 列举 Tool，避免无界枚举；
- 不导出 Chat Prompt；
- 不接收 MCP Sampling、Elicitation 或 Roots；
- 不使用 MCP Tasks 执行长任务；
- 不支持 SSE 旧传输；
- 不支持 stdio 子进程分发；
- 不监听 `0.0.0.0`、主机名或非 loopback 地址；
- 不实现 OAuth、动态客户端注册或多用户 Scope；
- 不自动把所有 `ToolRegistry` 工具导出；
- 不允许 MCP Export 递归调用 Phase 53 MCP Gateway；
- 不允许 MCP Export 触发 Phase 51 Live Research Browser；
- 不把 `readOnlyHint` 当作安全授权依据。

---

## 五、长期必须保持的不变量

### 5.1 静态公开面不变量

```text
MCP tools/list 的内容
    = 本地源码中显式注册的四个 Tool
    != ToolRegistry 中所有工具
    != Plugin Registry 中所有 Skill
    != Phase 53 远端发现到的 Tool
```

### 5.2 公开投影不变量

MCP 输出只能由明确的 Pydantic Export Schema 构造，禁止：

```python
# 错误示例：内部模型新增字段后会被自动暴露。
return internal_job.model_dump(mode="json")
```

### 5.3 Job Scope 不变量

MCP Client 可以提交 `job_id`，但这个值只用于选择一个 Job。它不能影响：

```text
数据库路径
Run 根目录
Artifact object key
Tool Capability
Secret 名称
MCP Server 配置
```

### 5.4 无传递网络不变量

```text
MCP Export request
  -> 只读本地 Job/Artifact/Event/Log
  -X-> Phase 53 MCP Client Gateway
  -X-> Research Browser
  -X-> Resource Downloader
```

### 5.5 身份不变量

每个结果都绑定：

```text
job_id
+ run_id 或 artifact_id
+ source SHA-256
+ export schema version
+ output snapshot hash
```

### 5.6 Token 不变量

Bearer Token：

- 只从 `SecretService` 读取；
- 不进入 CLI 参数；
- 不写入 `.env`；
- 不写入 Tool input/output；
- 不写入 Audit、log、exception 或 Telemetry；
- 不转发给下游 API、Phase 53 Server 或 Provider。

### 5.7 MCP Annotation 不变量

可以将 Tool 标注为 read-only，但 Annotation 只用于 Host UI 和提示，不是权限证明。真正的权限来自：

```text
静态注册
+ Export Service 公开投影
+ ToolRegistry Capability
+ 只读依赖
+ Authority Negative Test
```

---

## 六、总体架构

```text
MCP Host / Client
  |
  | Authorization: Bearer <local token>
  v
127.0.0.1:8770/mcp
  |
  +-- LocalBearerAuthMiddleware
  |
  +-- MCPServer (四个 Tool、两个 Resource)
  |
  +-- ReadOnlyMcpExportService
        |
        +-- InteractionService -> public Job projection
        +-- ArtifactDeliveryService -> metadata/final report preview
        +-- ToolRegistry -> local evidence search
        +-- SqliteMcpExportAuditRepository -> hash-only audit
        +-- InMemoryRateLimiter -> bounded calls
```

### 6.1 与 Phase 53 的关系

```text
app/mcp_gateway/
    协议方向：outbound
    本项目作为 Client
    访问固定外部 MCP Server

app/mcp_export/
    协议方向：inbound
    本项目作为 Server
    对外提供固定本地只读投影
```

两者必须使用不同 Feature Flag、不同数据库和不同 Token。关闭其中一个不能影响另一个。

### 6.2 为什么不直接代理内部 REST API

如果 MCP Export 再通过 HTTP 调用主 API，会增加：

- 第二份 Token；
- Token 转发风险；
- 同机网络故障；
- REST 错误到 MCP 错误的重复映射；
- 主 API 未启动时 MCP 无法读取本地状态。

本阶段直接依赖相同的 Python Service/Port，但不依赖 HTTP Route。

---

## 七、文件变更总览

### 7.1 需要新增

```text
app/mcp_export/__init__.py
app/mcp_export/errors.py
app/mcp_export/schemas.py
app/mcp_export/identity.py
app/mcp_export/audit.py
app/mcp_export/rate_limit.py
app/mcp_export/service.py
app/mcp_export/factory.py
app/mcp_export/server.py
app/mcp_export/auth.py
app/mcp_export/asgi.py

tests/mcp_export_helpers.py
tests/test_mcp_export_schemas.py
tests/test_mcp_export_audit.py
tests/test_mcp_export_rate_limit.py
tests/test_mcp_export_service.py
tests/test_mcp_export_server.py
tests/test_mcp_export_auth.py
tests/test_mcp_export_authority.py
tests/test_mcp_export_retention.py
```

### 7.2 需要修改

```text
app/config.py
app/main.py
app/secrets/schemas.py
app/retention/ports.py
app/retention/service.py
app/retention/factory.py
.env.example
.gitignore
a_implementation_guides/README.md
a_implementation_guides/project_phase_capability_summary.md
a_implementation_guides/agent_project_analysis_and_technical_roadmap.md
```

### 7.3 不需要修改

下面这些文件只需要复用，不应为 MCP 添加后门：

```text
app/nodes/executor_node.py
app/nodes/human_review_node.py
app/execution/
app/repair/
app/resources/worker.py
app/mcp_gateway/client.py
app/research_browser/fetcher.py
```

---

## 八、依赖与运行环境

### 8.1 `pyproject.toml` 不需要再次增加 MCP 依赖

Phase 53 已经增加：

```toml
[project.optional-dependencies]
mcp = [
    "mcp>=2.0,<3",
    "jsonschema>=4.23,<5",
]
```

本阶段直接复用，不要再添加第二个 `mcp-server` 包，也不要同时安装第三方同名 FastMCP 实现。

安装命令：

```bash
python -m pip install -e '.[mcp]'
```

确认版本：

```bash
python - <<'PY'
from importlib.metadata import version

print(version("mcp"))
PY
```

如果当前解释器低于 Python 3.10，应先切回项目环境。官方 MCP Python SDK v2 要求 Python 3.10+。

---

## 九、增加配置与 Feature Flag

### 9.1 必须修改：`app/config.py`

在 Phase 53 MCP Gateway 配置后增加：

```text
    # Phase 54：本项目作为 MCP Server 时的独立开关。
    mcp_export_enabled: bool = _env_bool(
        "MCP_EXPORT_ENABLED",
        False,
    )
    # 第一版只允许字面量 IPv4 loopback，不能配置 0.0.0.0 或主机名。
    mcp_export_host: str = os.getenv(
        "MCP_EXPORT_HOST",
        "127.0.0.1",
    )
    mcp_export_port: int = int(
        os.getenv("MCP_EXPORT_PORT", "8770")
    )
    # 这里只保存 Secret 的逻辑名称，不保存 Token 明文。
    mcp_export_token_secret_name: str = os.getenv(
        "MCP_EXPORT_TOKEN_SECRET_NAME",
        "PAPER_COPILOT_MCP_EXPORT_TOKEN",
    )
    mcp_export_audit_db_path: Path = Path(
        os.getenv(
            "MCP_EXPORT_AUDIT_DB_PATH",
            "control/mcp_export_audit.sqlite",
        )
    )
    mcp_export_max_artifacts: int = int(
        os.getenv("MCP_EXPORT_MAX_ARTIFACTS", "50")
    )
    mcp_export_max_report_chars: int = int(
        os.getenv("MCP_EXPORT_MAX_REPORT_CHARS", "50000")
    )
    mcp_export_max_calls_per_minute: int = int(
        os.getenv("MCP_EXPORT_MAX_CALLS_PER_MINUTE", "60")
    )
```

在 Settings 初始化后的集中校验位置增加：

```text
        if self.mcp_export_host != "127.0.0.1":
            raise ValueError(
                "Phase 54 MCP Export 只允许监听 127.0.0.1"
            )
        if not 1024 <= self.mcp_export_port <= 65535:
            raise ValueError(
                "MCP_EXPORT_PORT 必须位于 1024..65535"
            )
        if not 1 <= self.mcp_export_max_artifacts <= 100:
            raise ValueError(
                "MCP_EXPORT_MAX_ARTIFACTS 必须位于 1..100"
            )
        if not 1000 <= self.mcp_export_max_report_chars <= 100000:
            raise ValueError(
                "MCP_EXPORT_MAX_REPORT_CHARS 必须位于 1000..100000"
            )
        if not 1 <= self.mcp_export_max_calls_per_minute <= 600:
            raise ValueError(
                "MCP_EXPORT_MAX_CALLS_PER_MINUTE 必须位于 1..600"
            )
```

如果当前 `Settings` 不是 Pydantic Model，而是在模块导入时直接创建 dataclass/普通对象，就把这些判断放进
现有 `validate_runtime_settings()` 或 CLI 启动边界，不要机械复制 `self`。

### 9.2 必须修改：`.env.example`

```dotenv

# Phase 54 MCP Server Export。只允许单机 loopback，默认关闭。
MCP_EXPORT_ENABLED=false
MCP_EXPORT_HOST=127.0.0.1
MCP_EXPORT_PORT=8770
MCP_EXPORT_TOKEN_SECRET_NAME=PAPER_COPILOT_MCP_EXPORT_TOKEN
MCP_EXPORT_AUDIT_DB_PATH=control/mcp_export_audit.sqlite
MCP_EXPORT_MAX_ARTIFACTS=50
MCP_EXPORT_MAX_REPORT_CHARS=50000
MCP_EXPORT_MAX_CALLS_PER_MINUTE=60
```

注意检查 Phase 53 配置块前是否有换行，避免出现：

```text
RESEARCH_BROWSER_NETWORK_GUARD=application_only# Phase 53 ...
```

正确格式必须是两行。

### 9.3 必须修改：`.gitignore`

```gitignore
# Phase 54：本地 MCP Export 调用审计。
control/mcp_export_audit.sqlite
control/mcp_export_audit.sqlite-wal
control/mcp_export_audit.sqlite-shm
```

Token 位于 Secret Vault，不应产生单独 Token 文件。

---

## 十、给 Secret 增加独立用途

### 10.1 必须修改：`app/secrets/schemas.py`

在 `SecretUse` 中增加：

```python
class SecretUse(str, Enum):
    PROVIDER = "provider"
    EMBEDDING = "embedding"
    DATABASE = "database"
    API_AUTH = "api_auth"
    RESOURCE_HTTP = "resource_http"
    RESOURCE_GIT = "resource_git"
    EXECUTION_ENV = "execution_env"
    RESEARCH_SEARCH = "research_search"

    # MCP Export Token 只验证入站本机 MCP 请求，不能当成 API 或 Provider Key。
    MCP_EXPORT_AUTH = "mcp_export_auth"
```

不能复用 `API_AUTH`，原因是：

```text
主 API Token 泄漏范围 != MCP Export Token 泄漏范围
撤销 MCP Export       != 关闭主 Web/API
MCP Host 配置          不应获得主 API 权限
```

创建 Token：

```bash
python -m app.main set-secret \
  PAPER_COPILOT_MCP_EXPORT_TOKEN \
  --use mcp_export_auth
```

终端会隐藏输入。不要把 Token 写在命令参数、Shell history 或 `.env`。

---

## 十一、建立模块与稳定错误

### 11.1 需要新增：`app/mcp_export/__init__.py`

```python
"""Phase 54：只读 MCP Server Export。"""
```

### 11.2 需要新增：`app/mcp_export/errors.py`

```python
from __future__ import annotations


class McpExportError(RuntimeError):
    """可以映射成稳定 MCP 公开错误的领域异常。"""

    code = "MCP_EXPORT_ERROR"
    public_message = "MCP Export request failed"


class McpExportDisabled(McpExportError):
    code = "MCP_EXPORT_DISABLED"
    public_message = "MCP Export is disabled"


class McpExportUnauthorized(McpExportError):
    code = "MCP_EXPORT_UNAUTHORIZED"
    public_message = "Authentication required"


class McpExportInputInvalid(McpExportError):
    code = "MCP_EXPORT_INPUT_INVALID"
    public_message = "Request input is invalid"


class McpExportJobNotFound(McpExportError):
    code = "MCP_EXPORT_JOB_NOT_FOUND"
    public_message = "Reproduction job was not found"


class McpExportFinalReportNotFound(McpExportError):
    code = "MCP_EXPORT_FINAL_REPORT_NOT_FOUND"
    public_message = "Final report is not available"


class McpExportEvidenceUnavailable(McpExportError):
    code = "MCP_EXPORT_EVIDENCE_UNAVAILABLE"
    public_message = "Reproduction evidence is unavailable"


class McpExportRateLimited(McpExportError):
    code = "MCP_EXPORT_RATE_LIMITED"
    public_message = "MCP Export rate limit exceeded"


class McpExportIntegrityError(McpExportError):
    code = "MCP_EXPORT_INTEGRITY_ERROR"
    public_message = "Exported evidence failed integrity validation"


class McpExportInternalError(McpExportError):
    code = "MCP_EXPORT_INTERNAL"
    public_message = "MCP Export internal error"
```

公开错误不能包含：

```text
绝对路径
SQL
原始 exception repr
Bearer Token
Secret 名称以外的 material
Artifact object key
完整 query 或 evidence 内容
```

---

## 十二、定义公开 Schema

### 12.1 需要新增：`app/mcp_export/schemas.py`

```python
from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


JOB_ID_PATTERN = r"^job_[0-9a-f]{32}$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"


class McpExportModel(BaseModel):
    """所有 MCP Export 对象都拒绝未知字段，防止协议静默漂移。"""

    model_config = ConfigDict(extra="forbid")


class McpExportJobStatus(McpExportModel):
    schema_version: Literal["phase54-v1"] = "phase54-v1"
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    run_id: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=64)
    version: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    waiting_for_user: bool
    allowed_operation_kinds: list[str] = Field(
        default_factory=list,
        max_length=8,
    )
    final_status: str | None = Field(
        default=None,
        max_length=100,
    )
    stage_error_count: int | None = Field(default=None, ge=0)
    output_file_count: int | None = Field(default=None, ge=0)
    has_error: bool
    error_code: str | None = Field(default=None, max_length=100)
    created_at: str
    updated_at: str
    snapshot_sha256: str = Field(pattern=SHA256_PATTERN)


class McpExportArtifact(McpExportModel):
    artifact_id: str = Field(min_length=1, max_length=200)
    run_id: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=255)
    layer: str = Field(min_length=1, max_length=100)
    media_type: str = Field(min_length=1, max_length=200)
    sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=0)
    producer_node: str = Field(min_length=1, max_length=200)
    created_at: str
    preview_supported: bool

    @field_validator("display_name")
    @classmethod
    def reject_path_like_name(cls, value: str) -> str:
        if value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("display_name 只能是 basename")
        return value


class McpExportArtifactPage(McpExportModel):
    schema_version: Literal["phase54-v1"] = "phase54-v1"
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    run_id: str = Field(min_length=1, max_length=200)
    items: list[McpExportArtifact] = Field(
        default_factory=list,
        max_length=100,
    )
    returned_count: int = Field(ge=0)
    truncated: bool
    snapshot_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_count(self) -> "McpExportArtifactPage":
        if self.returned_count != len(self.items):
            raise ValueError("returned_count 与 items 数量不一致")
        return self


class McpExportFinalReport(McpExportModel):
    schema_version: Literal["phase54-v1"] = "phase54-v1"
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    run_id: str = Field(min_length=1, max_length=200)
    artifact_id: str = Field(min_length=1, max_length=200)
    artifact_sha256: str = Field(pattern=SHA256_PATTERN)
    media_type: Literal["text/markdown", "text/plain"]
    total_size_bytes: int = Field(ge=0)
    returned_chars: int = Field(ge=0)
    truncated: bool
    content: str = Field(max_length=100000)
    content_sha256: str = Field(pattern=SHA256_PATTERN)
    snapshot_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_length(self) -> "McpExportFinalReport":
        if self.returned_chars != len(self.content):
            raise ValueError("returned_chars 与 content 长度不一致")
        return self


class McpExportCitation(McpExportModel):
    citation_id: str = Field(min_length=1, max_length=300)
    source_type: Literal["job", "event", "artifact", "log"]
    label: str = Field(min_length=1, max_length=300)
    artifact_id: str | None = Field(default=None, max_length=200)
    artifact_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    event_id: int | None = Field(default=None, ge=0)


class McpExportEvidenceItem(McpExportModel):
    citation: McpExportCitation
    excerpt: str = Field(min_length=1, max_length=4000)
    excerpt_sha256: str = Field(pattern=SHA256_PATTERN)


class McpExportEvidencePack(McpExportModel):
    schema_version: Literal["phase54-v1"] = "phase54-v1"
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    query_sha256: str = Field(pattern=SHA256_PATTERN)
    items: list[McpExportEvidenceItem] = Field(
        default_factory=list,
        max_length=6,
    )
    truncated: bool
    pack_sha256: str = Field(pattern=SHA256_PATTERN)


class McpExportAuditRecord(McpExportModel):
    call_id: str = Field(pattern=r"^mcpexportcall_[0-9a-f]{24}$")
    request_id: str = Field(min_length=1, max_length=200)
    actor_fingerprint: str = Field(pattern=SHA256_PATTERN)
    operation: Literal[
        "get_reproduction_status",
        "list_reproduction_artifacts",
        "read_reproduction_final_report",
        "search_reproduction_evidence",
        "resource_job_status",
        "resource_final_report",
    ]
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    status: Literal["succeeded", "failed"]
    input_sha256: str = Field(pattern=SHA256_PATTERN)
    output_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    error_code: str | None = Field(default=None, max_length=100)
    started_at: str
    finished_at: str
    duration_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_result_shape(self) -> "McpExportAuditRecord":
        if self.status == "succeeded":
            if self.output_sha256 is None or self.error_code is not None:
                raise ValueError("成功 Audit 必须只有 output_sha256")
        elif self.error_code is None or self.output_sha256 is not None:
            raise ValueError("失败 Audit 必须只有 error_code")
        return self


class McpExportDoctorReport(McpExportModel):
    enabled: bool
    ready: bool
    host: str
    port: int = Field(ge=1, le=65535)
    token_available: bool
    audit_ready: bool
    tool_names: list[str] = Field(default_factory=list)
    resource_templates: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
```

### 12.2 输入输出含义

| 字段 | 含义 | 不是 |
|---|---|---|
| `job_id` | JobStore 中由服务端生成的任务身份 | 路径、thread ID 或 run 目录 |
| `artifact_id` | Artifact Catalog 的内容对象身份 | 文件路径 |
| `artifact_sha256` | 完整 Artifact 内容 Hash | Token 或加密值 |
| `content_sha256` | 本次返回的有界文本内容 Hash | 完整 Artifact Hash |
| `snapshot_sha256` | 当前公开投影的规范化 Hash | 数据库行号 |
| `query_sha256` | 用户查询文本的 SHA-256，用于审计关联 | 可逆加密后的 query |
| `actor_fingerprint` | 固定 actor 标签的 SHA-256 | Bearer Token Hash |
| `pack_sha256` | Evidence Pack 内容身份 | 模型置信度 |

`actor_fingerprint` 必须从固定字符串（如 `mcp:local-token`）生成，不要对 Token 做普通 SHA-256 后保存。低熵或
泄漏 Token 的 Hash 仍可能被离线猜测，而且没有审计需要保存凭证指纹。

---

## 十三、实现规范化 Hash 与输入校验

### 13.1 需要新增：`app/mcp_export/identity.py`

```python
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from app.mcp_export.errors import McpExportInputInvalid
from app.mcp_export.schemas import JOB_ID_PATTERN


def canonical_json_bytes(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        material = value.model_dump(mode="json")
    else:
        material = value
    return json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_job_id(job_id: str) -> str:
    """只接受 JobService 当前生成的 job_<32 hex> 身份。"""

    import re

    normalized = job_id.strip()
    if re.fullmatch(JOB_ID_PATTERN, normalized) is None:
        raise McpExportInputInvalid("invalid job_id")
    return normalized


def normalize_query(query: str) -> str:
    normalized = " ".join(query.strip().split())
    if not normalized or len(normalized) > 500:
        raise McpExportInputInvalid("invalid query length")
    if any(
        ord(character) < 32 or ord(character) == 127
        for character in normalized
    ):
        raise McpExportInputInvalid("query contains control characters")
    return normalized


def bounded_limit(limit: int, *, maximum: int) -> int:
    if not 1 <= limit <= maximum:
        raise McpExportInputInvalid("limit is outside allowed range")
    return limit
```

伪代码：

```text
validate_job_id(job_id)
    去除首尾空白
    如果不符合 job_ + 32 位十六进制
        抛出稳定输入异常
    返回规范化 job_id

normalize_query(query)
    合并多余空白
    如果为空或超过 500 字符
        抛出稳定输入异常
    如果包含 ASCII 控制字符
        抛出稳定输入异常
    返回规范化 query
```

---

## 十四、实现 Hash-only Audit Repository

### 14.1 需要新增：`app/mcp_export/audit.py`

```python
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.mcp_export.schemas import McpExportAuditRecord


class SqliteMcpExportAuditRepository:
    """只保存调用身份和 Hash，不保存 Token、query 或 Tool 输出。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=30,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mcp_export_calls (
                    call_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    actor_fingerprint TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_sha256 TEXT NOT NULL,
                    output_sha256 TEXT,
                    error_code TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    record_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mcp_export_calls_job
                ON mcp_export_calls(job_id, started_at, call_id)
                """
            )

    def put(self, record: McpExportAuditRecord) -> None:
        payload = record.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO mcp_export_calls (
                    call_id, request_id, actor_fingerprint,
                    operation, job_id, status, input_sha256,
                    output_sha256, error_code, started_at,
                    finished_at, duration_ms, record_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.call_id,
                    record.request_id,
                    record.actor_fingerprint,
                    record.operation,
                    record.job_id,
                    record.status,
                    record.input_sha256,
                    record.output_sha256,
                    record.error_code,
                    record.started_at,
                    record.finished_at,
                    record.duration_ms,
                    payload,
                ),
            )

    def list_for_job(
        self,
        job_id: str,
        *,
        limit: int = 100,
    ) -> list[McpExportAuditRecord]:
        bounded = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT record_json
                FROM mcp_export_calls
                WHERE job_id = ?
                ORDER BY started_at DESC, call_id DESC
                LIMIT ?
                """,
                (job_id, bounded),
            ).fetchall()
        return [
            McpExportAuditRecord.model_validate_json(row["record_json"])
            for row in rows
        ]

    def delete_for_job(self, job_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM mcp_export_calls WHERE job_id = ?",
                (job_id,),
            )
        return max(cursor.rowcount, 0)

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()
```

### 14.2 Audit 中为什么连 query 都不保存

论文检索问题本身可能包含：

```text
未公开实验设想
仓库内部模块名
错误日志片段
用户环境描述
```

本阶段只需要回答“何时、由谁、对哪个 Job、调用了什么、输入输出身份是什么”，因此保存 `input_sha256` 和
`output_sha256` 已经足够。需要调试内容时应回到原始 Job Evidence，而不是把第二份内容复制进 Audit DB。

---

## 十五、实现单进程速率限制

### 15.1 需要新增：`app/mcp_export/rate_limit.py`

```python
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from app.mcp_export.errors import McpExportRateLimited


class InMemoryMcpExportRateLimiter:
    """单机单进程滑动窗口；重启后清零是第一版可接受行为。"""

    def __init__(
        self,
        *,
        max_calls_per_minute: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_calls = max_calls_per_minute
        self.clock = clock
        self._lock = threading.Lock()
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def acquire(self, actor_fingerprint: str) -> None:
        now = self.clock()
        cutoff = now - 60.0
        with self._lock:
            bucket = self._calls[actor_fingerprint]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_calls:
                raise McpExportRateLimited("rate limit exceeded")
            bucket.append(now)
```

这不是分布式 Rate Limiter，也不是安全隔离的替代品。它只用于避免一个本机 Host 因循环 Tool Calling 快速读取
大量 Artifact。Phase 54 明确不支持多 Worker MCP Server，因此不需要 Redis。

---

## 十六、实现公开投影服务

### 16.1 需要新增：`app/mcp_export/service.py`

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import PurePosixPath
from time import perf_counter
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from app.artifact_delivery.errors import ArtifactPreviewUnsupported
from app.artifact_delivery.service import ArtifactDeliveryService
from app.interaction.service import InteractionService
from app.job_runtime.errors import JobConflictError, JobNotFoundError
from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.errors import (
    McpExportError,
    McpExportEvidenceUnavailable,
    McpExportFinalReportNotFound,
    McpExportIntegrityError,
    McpExportInternalError,
    McpExportJobNotFound,
)
from app.mcp_export.identity import (
    bounded_limit,
    normalize_query,
    sha256_text,
    sha256_value,
    validate_job_id,
)
from app.mcp_export.rate_limit import InMemoryMcpExportRateLimiter
from app.mcp_export.schemas import (
    McpExportArtifact,
    McpExportArtifactPage,
    McpExportAuditRecord,
    McpExportCitation,
    McpExportEvidenceItem,
    McpExportEvidencePack,
    McpExportFinalReport,
    McpExportJobStatus,
)
from app.secrets.redaction import SecretRedactor
from app.storage.errors import ArtifactIntegrityError
from app.tool_calling.schemas import EvidenceToolOutput
from app.tool_contracts.registry import ToolRegistry
from app.tool_contracts.schemas import ToolInvocationContext


ExportResult = TypeVar("ExportResult", bound=BaseModel)

LOCAL_ACTOR = "mcp-export:local-token"
LOCAL_CAPABILITIES = {
    "job.read.current",
    "run.read.evidence",
}
LOCAL_EVIDENCE_TYPES = [
    "job",
    "event",
    "artifact",
    "log",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_code(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("code") or value.get("error_code")
    if raw is None:
        return None
    normalized = str(raw).strip()
    return normalized[:100] or None


def _map_export_error(exc: BaseException) -> McpExportError:
    if isinstance(exc, McpExportError):
        return exc
    if isinstance(exc, JobNotFoundError):
        return McpExportJobNotFound("job not found")
    if isinstance(exc, ArtifactPreviewUnsupported):
        return McpExportFinalReportNotFound("report is not previewable")
    if isinstance(exc, (JobConflictError, ArtifactIntegrityError)):
        return McpExportIntegrityError("evidence identity mismatch")
    return McpExportInternalError("unexpected export failure")


class ReadOnlyMcpExportService:
    def __init__(
        self,
        *,
        interaction: InteractionService,
        artifact_delivery: ArtifactDeliveryService,
        evidence_registry: ToolRegistry,
        audit_repository: SqliteMcpExportAuditRepository,
        rate_limiter: InMemoryMcpExportRateLimiter,
        redactor: SecretRedactor,
        max_artifacts: int,
        max_report_chars: int,
    ) -> None:
        self.interaction = interaction
        self.artifact_delivery = artifact_delivery
        self.evidence_registry = evidence_registry
        self.audit_repository = audit_repository
        self.rate_limiter = rate_limiter
        self.redactor = redactor
        self.max_artifacts = max_artifacts
        self.max_report_chars = max_report_chars
        self.actor_fingerprint = sha256_text(LOCAL_ACTOR)

    def _execute(
        self,
        *,
        operation: str,
        job_id: str,
        request_id: str,
        input_payload: dict,
        function: Callable[[], ExportResult],
    ) -> ExportResult:
        """统一处理预算、错误收敛和 Hash-only Audit。"""

        started_at = utc_now()
        started = perf_counter()
        input_sha256 = sha256_value(input_payload)

        try:
            # 限流也属于受审计的调用结果，必须放在 try 内。
            self.rate_limiter.acquire(self.actor_fingerprint)
            output = function()
        except Exception as exc:
            mapped = _map_export_error(exc)
            record = McpExportAuditRecord(
                call_id=f"mcpexportcall_{uuid4().hex[:24]}",
                request_id=request_id,
                actor_fingerprint=self.actor_fingerprint,
                operation=operation,
                job_id=job_id,
                status="failed",
                input_sha256=input_sha256,
                error_code=mapped.code,
                started_at=started_at,
                finished_at=utc_now(),
                duration_ms=(perf_counter() - started) * 1000,
            )
            self.audit_repository.put(record)
            raise mapped from None

        record = McpExportAuditRecord(
            call_id=f"mcpexportcall_{uuid4().hex[:24]}",
            request_id=request_id,
            actor_fingerprint=self.actor_fingerprint,
            operation=operation,
            job_id=job_id,
            status="succeeded",
            input_sha256=input_sha256,
            output_sha256=sha256_value(output),
            started_at=started_at,
            finished_at=utc_now(),
            duration_ms=(perf_counter() - started) * 1000,
        )
        # Audit 是安全边界；持久化失败时不向 Client 声称调用成功。
        self.audit_repository.put(record)
        return output

    def get_status(
        self,
        *,
        job_id: str,
        request_id: str,
        operation: str = "get_reproduction_status",
    ) -> McpExportJobStatus:
        selected_job_id = validate_job_id(job_id)

        def build() -> McpExportJobStatus:
            view = self.interaction.get_job(selected_job_id)
            result = view.result
            payload = {
                "schema_version": "phase54-v1",
                "job_id": view.job_id,
                "run_id": view.run_id,
                "status": view.status,
                "version": view.version,
                "attempt_count": view.attempt_count,
                "max_attempts": view.max_attempts,
                # cancel/rerun 也属于 allowed_operation，不能据此判断等待用户。
                "waiting_for_user": view.status == "waiting_for_input",
                "allowed_operation_kinds": sorted(
                    {item.kind for item in view.allowed_operations}
                ),
                "final_status": (
                    result.final_status if result is not None else None
                ),
                "stage_error_count": (
                    result.stage_error_count if result is not None else None
                ),
                "output_file_count": (
                    result.output_file_count if result is not None else None
                ),
                "has_error": view.error is not None,
                "error_code": _error_code(view.error),
                "created_at": view.created_at,
                "updated_at": view.updated_at,
            }
            return McpExportJobStatus(
                **payload,
                snapshot_sha256=sha256_value(payload),
            )

        return self._execute(
            operation=operation,
            job_id=selected_job_id,
            request_id=request_id,
            input_payload={"job_id": selected_job_id},
            function=build,
        )

    def list_artifacts(
        self,
        *,
        job_id: str,
        limit: int,
        request_id: str,
    ) -> McpExportArtifactPage:
        selected_job_id = validate_job_id(job_id)
        selected_limit = bounded_limit(
            limit,
            maximum=self.max_artifacts,
        )

        def build() -> McpExportArtifactPage:
            internal_job = self.interaction.job_service.get(selected_job_id)
            views = self.artifact_delivery.list_views(internal_job)
            selected = views[:selected_limit]
            items = [
                McpExportArtifact(
                    artifact_id=item.artifact_id,
                    run_id=item.run_id,
                    # 只返回 basename，不返回 relative_path。
                    display_name=PurePosixPath(item.relative_path).name,
                    layer=item.layer,
                    media_type=item.media_type,
                    sha256=item.sha256,
                    size_bytes=item.size_bytes,
                    producer_node=item.producer_node,
                    created_at=item.created_at,
                    preview_supported=item.preview_supported,
                )
                for item in selected
            ]
            payload = {
                "schema_version": "phase54-v1",
                "job_id": internal_job.job_id,
                "run_id": internal_job.run_id,
                "items": [
                    item.model_dump(mode="json") for item in items
                ],
                "returned_count": len(items),
                "truncated": len(views) > len(items),
            }
            return McpExportArtifactPage(
                **payload,
                snapshot_sha256=sha256_value(payload),
            )

        return self._execute(
            operation="list_reproduction_artifacts",
            job_id=selected_job_id,
            request_id=request_id,
            input_payload={
                "job_id": selected_job_id,
                "limit": selected_limit,
            },
            function=build,
        )

    @staticmethod
    def _final_report_priority(relative_path: str) -> tuple[int, str]:
        """服务端识别 final_report；Client 不能提交路径。"""

        normalized = relative_path.replace("\\", "/").lower()
        preferred = {
            "reports/final_report.md": 0,
            "outputs/final_report.md": 1,
            "final_report.md": 2,
        }
        return preferred.get(normalized, 10), normalized

    def read_final_report(
        self,
        *,
        job_id: str,
        request_id: str,
        operation: str = "read_reproduction_final_report",
    ) -> McpExportFinalReport:
        selected_job_id = validate_job_id(job_id)

        def build() -> McpExportFinalReport:
            internal_job = self.interaction.job_service.get(selected_job_id)
            views = self.artifact_delivery.list_views(internal_job)
            candidates = [
                item
                for item in views
                if PurePosixPath(item.relative_path).name.lower()
                == "final_report.md"
                and item.media_type in {"text/markdown", "text/plain"}
                and item.preview_supported
            ]
            if not candidates:
                raise McpExportFinalReportNotFound("no final report")

            selected = sorted(
                candidates,
                key=lambda item: self._final_report_priority(
                    item.relative_path
                ),
            )[0]
            preview = self.artifact_delivery.preview(
                job=internal_job,
                artifact_id=selected.artifact_id,
            )
            raw_content = preview.content[: self.max_report_chars]
            content = self.redactor.redact_text(
                raw_content,
                max_chars=self.max_report_chars,
            )
            truncated = (
                preview.truncated
                or len(preview.content) > len(raw_content)
            )
            payload = {
                "schema_version": "phase54-v1",
                "job_id": internal_job.job_id,
                "run_id": internal_job.run_id,
                "artifact_id": selected.artifact_id,
                "artifact_sha256": selected.sha256,
                "media_type": selected.media_type,
                "total_size_bytes": preview.total_size_bytes,
                "returned_chars": len(content),
                "truncated": truncated,
                "content": content,
                "content_sha256": sha256_text(content),
            }
            return McpExportFinalReport(
                **payload,
                snapshot_sha256=sha256_value(payload),
            )

        return self._execute(
            operation=operation,
            job_id=selected_job_id,
            request_id=request_id,
            input_payload={"job_id": selected_job_id},
            function=build,
        )

    @staticmethod
    def _public_citation(item) -> McpExportCitation:
        citation = item.citation
        source_type = citation.source_type
        if source_type not in LOCAL_EVIDENCE_TYPES:
            raise McpExportEvidenceUnavailable(
                "transitive evidence type is not exportable"
            )

        if source_type == "artifact":
            label = f"artifact:{citation.artifact_id or 'unknown'}"
        elif source_type == "event":
            label = f"job-event:{citation.event_id or 0}"
        elif source_type == "log":
            label = "bounded-job-log"
        else:
            label = "current-job-status"

        return McpExportCitation(
            citation_id=citation.citation_id,
            source_type=source_type,
            label=label,
            artifact_id=citation.artifact_id,
            artifact_sha256=citation.artifact_sha256,
            event_id=citation.event_id,
        )

    def search_evidence(
        self,
        *,
        job_id: str,
        query: str,
        limit: int,
        request_id: str,
    ) -> McpExportEvidencePack:
        selected_job_id = validate_job_id(job_id)
        selected_query = normalize_query(query)
        selected_limit = bounded_limit(limit, maximum=6)

        def build() -> McpExportEvidencePack:
            result = self.evidence_registry.invoke(
                name="chat.search_reproduction_evidence",
                raw_input={
                    "query": selected_query,
                    # 固定本地来源，禁止 web/mcp/knowledge 等传递能力。
                    "source_types": list(LOCAL_EVIDENCE_TYPES),
                    "limit": selected_limit,
                },
                context=ToolInvocationContext(
                    actor=LOCAL_ACTOR,
                    request_id=request_id,
                    caller_kind="agent",
                    job_id=selected_job_id,
                    granted_capabilities=set(LOCAL_CAPABILITIES),
                ),
            )
            if result.failure is not None or result.output is None:
                code = (
                    result.failure.code
                    if result.failure is not None
                    else "TOOL_EMPTY_RESULT"
                )
                raise McpExportEvidenceUnavailable(code)

            evidence = EvidenceToolOutput.model_validate(result.output)
            items = []
            for item in evidence.items[:selected_limit]:
                excerpt = self.redactor.redact_text(
                    item.content,
                    max_chars=4000,
                )
                if not excerpt.strip():
                    continue
                items.append(
                    McpExportEvidenceItem(
                        citation=self._public_citation(item),
                        excerpt=excerpt,
                        excerpt_sha256=sha256_text(excerpt),
                    )
                )

            payload = {
                "schema_version": "phase54-v1",
                "job_id": selected_job_id,
                "query_sha256": sha256_text(selected_query),
                "items": [
                    item.model_dump(mode="json") for item in items
                ],
                "truncated": evidence.truncated,
            }
            return McpExportEvidencePack(
                **payload,
                pack_sha256=sha256_value(payload),
            )

        return self._execute(
            operation="search_reproduction_evidence",
            job_id=selected_job_id,
            request_id=request_id,
            input_payload={
                "job_id": selected_job_id,
                "query_sha256": sha256_text(selected_query),
                "limit": selected_limit,
                "source_types": list(LOCAL_EVIDENCE_TYPES),
            },
            function=build,
        )
```

### 16.2 四个方法的输入输出

| 方法 | 输入 | 输出 | 关键限制 |
|---|---|---|---|
| `get_status` | Job 身份、MCP request ID | 公开状态快照 | 不返回路径、claim token、完整 error |
| `list_artifacts` | Job 身份、数量上限 | Artifact metadata 页面 | 只返回 basename，不返回下载 URL |
| `read_final_report` | Job 身份 | 最终报告有界文本 | Client 不能提交 Artifact ID 或路径 |
| `search_evidence` | Job 身份、query、limit | 带 Citation 的 Evidence Pack | 来源固定为本地四类，不传递联网能力 |

### 16.3 为什么 `read_final_report` 不接受 `artifact_id`

如果 Tool Schema 是：

```text
read_artifact(job_id, artifact_id)
```

模型就获得了枚举和读取任意文本 Artifact 的能力。即使 Catalog 会校验 Job Scope，日志、补丁草稿或内部诊断
也未必适合交给外部 Host。第一版由服务端只选择 `final_report.md`，公开面明显更窄。

### 16.4 为什么 Evidence 不能包含 `mcp` 来源

否则可能形成调用环：

```text
外部 Host
  -> 当前 MCP Export Server
  -> Phase 53 MCP Client Gateway
  -> 另一个 MCP Server
  -> 可能再次调用当前 Server
```

Phase 54 固定 `job/event/artifact/log`，因此整个 Tool Call 不产生网络副作用。

---

## 十七、建立最小只读 Composition Root

### 17.1 需要新增：`app/mcp_export/factory.py`

```python
from __future__ import annotations

from dataclasses import dataclass

from app.artifact_delivery.service import ArtifactDeliveryService
from app.chat.context import ChatContextBuilder
from app.config import settings
from app.interaction.service import InteractionService
from app.job_runtime.factory import build_job_store
from app.job_runtime.service import JobService
from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.errors import McpExportDisabled
from app.mcp_export.rate_limit import InMemoryMcpExportRateLimiter
from app.mcp_export.schemas import McpExportDoctorReport
from app.mcp_export.service import ReadOnlyMcpExportService
from app.secrets.errors import SecretNotFoundError
from app.secrets.factory import build_secret_service
from app.secrets.schemas import SecretUse
from app.storage.factory import build_artifact_storage
from app.tool_calling.evidence_tools import (
    ChatEvidenceToolBindings,
    build_chat_evidence_tool_registry,
)
from app.workspace.snapshot import WorkspaceSnapshotter


TOOL_NAMES = [
    "get_reproduction_status",
    "list_reproduction_artifacts",
    "read_reproduction_final_report",
    "search_reproduction_evidence",
]

RESOURCE_TEMPLATES = [
    "repro://jobs/{job_id}/status",
    "repro://jobs/{job_id}/final-report",
]


@dataclass(frozen=True)
class McpExportRuntime:
    service: ReadOnlyMcpExportService
    audit_repository: SqliteMcpExportAuditRepository


def _build_artifact_delivery(storage) -> ArtifactDeliveryService:
    return ArtifactDeliveryService(
        catalog=storage.catalog,
        preview_max_bytes=settings.artifact_preview_max_bytes,
        stream_chunk_bytes=settings.artifact_stream_chunk_bytes,
        export_allowed_root=settings.job_export_allowed_root,
        export_staging_root=settings.job_export_staging_root,
        export_max_artifacts=settings.job_export_max_artifacts,
        export_max_uncompressed_bytes=(
            settings.job_export_max_uncompressed_bytes
        ),
        export_max_archive_bytes=settings.job_export_max_archive_bytes,
        export_staging_ttl_seconds=(
            settings.job_export_staging_ttl_seconds
        ),
    )


def build_mcp_export_runtime() -> McpExportRuntime:
    if not settings.mcp_export_enabled:
        raise McpExportDisabled("MCP Export is disabled")

    storage = build_artifact_storage()
    job_service = JobService(
        build_job_store(),
        workspace_snapshotter=WorkspaceSnapshotter(
            blob_store=storage.selected_store
        ),
    )
    interaction = InteractionService(job_service)
    delivery = _build_artifact_delivery(storage)

    # 第一版只构造本地 Job/Artifact/Event/Log Context，不注入 Research、
    # MCP Gateway、Knowledge 或 Project Fact Retriever。
    context_builder = ChatContextBuilder(
        interaction=interaction,
        artifact_catalog=storage.catalog,
        artifacts_to_open=settings.chat_artifacts_to_open,
        source_limit=settings.chat_source_limit,
        artifact_max_bytes=settings.chat_artifact_max_bytes,
        total_context_chars=settings.chat_total_context_chars,
        log_max_bytes=settings.chat_log_max_bytes,
    )
    evidence_registry = build_chat_evidence_tool_registry(
        ChatEvidenceToolBindings(
            context_builder=context_builder,
            # 显式 None，防止 Phase 53 MCP Gateway 被递归导出。
            mcp_gateway=None,
        )
    )

    audit = SqliteMcpExportAuditRepository(
        settings.mcp_export_audit_db_path
    )
    audit.initialize()
    limiter = InMemoryMcpExportRateLimiter(
        max_calls_per_minute=(
            settings.mcp_export_max_calls_per_minute
        )
    )
    service = ReadOnlyMcpExportService(
        interaction=interaction,
        artifact_delivery=delivery,
        evidence_registry=evidence_registry,
        audit_repository=audit,
        rate_limiter=limiter,
        redactor=build_secret_service().build_redactor(
            actor="runtime:mcp-export-redactor"
        ),
        max_artifacts=settings.mcp_export_max_artifacts,
        max_report_chars=settings.mcp_export_max_report_chars,
    )
    return McpExportRuntime(
        service=service,
        audit_repository=audit,
    )


def resolve_mcp_export_token() -> str:
    """仅在启动 MCP Export 进程时解析明文 Token。"""

    material = build_secret_service().resolve_current(
        name=settings.mcp_export_token_secret_name,
        use=SecretUse.MCP_EXPORT_AUTH,
        actor="runtime:mcp-export-auth",
    )
    return material.reveal()


def inspect_mcp_export() -> McpExportDoctorReport:
    issues: list[str] = []
    token_available = False
    audit_ready = False

    if settings.mcp_export_host != "127.0.0.1":
        issues.append("mcp_export_host_not_loopback")

    try:
        # Doctor 只验证 Secret 存在、状态正常且允许用于 MCP Export，
        # 不调用 reveal()，避免把明文 Token 留在局部变量中。
        build_secret_service().resolve_current(
            name=settings.mcp_export_token_secret_name,
            use=SecretUse.MCP_EXPORT_AUTH,
            actor="doctor:mcp-export-auth",
        )
        token_available = True
    except SecretNotFoundError:
        issues.append("mcp_export_token_missing")
    except Exception as exc:
        issues.append(f"mcp_export_token_invalid:{type(exc).__name__}")

    try:
        repository = SqliteMcpExportAuditRepository(
            settings.mcp_export_audit_db_path
        )
        repository.initialize()
        repository.ping()
        audit_ready = True
    except Exception as exc:
        issues.append(f"mcp_export_audit_invalid:{type(exc).__name__}")

    return McpExportDoctorReport(
        enabled=settings.mcp_export_enabled,
        ready=(
            settings.mcp_export_enabled
            and token_available
            and audit_ready
            and not issues
        ),
        host=settings.mcp_export_host,
        port=settings.mcp_export_port,
        token_available=token_available,
        audit_ready=audit_ready,
        tool_names=list(TOOL_NAMES),
        resource_templates=list(RESOURCE_TEMPLATES),
        issues=issues,
    )
```

### 17.2 Composition Root 的核心边界

```text
允许构造：
JobStore、Artifact Catalog、Artifact Delivery、ChatContextBuilder、
本地 Evidence ToolRegistry、Audit、RateLimiter

禁止构造：
Executor、Graph Runner、Worker、Resource Worker、Research Browser、
Phase 53 MCP Client、Model Gateway、Human Review、Patch Service
```

这样即使 MCP handler 被错误调用，也没有可以执行命令或联网的依赖对象。

---

## 十八、用官方 SDK 注册四个 Tool 和两个 Resource

### 18.1 需要新增：`app/mcp_export/server.py`

```python
from __future__ import annotations

import json
from typing import Annotated, NoReturn
from uuid import uuid4

from pydantic import Field

from app.mcp_export.errors import McpExportError
from app.mcp_export.schemas import (
    McpExportArtifactPage,
    McpExportEvidencePack,
    McpExportFinalReport,
    McpExportJobStatus,
)
from app.mcp_export.service import ReadOnlyMcpExportService


def _request_id(ctx) -> str:
    raw = getattr(ctx, "request_id", None)
    normalized = str(raw).strip() if raw is not None else ""
    return normalized[:200] or f"mcp_{uuid4().hex[:24]}"


def _resource_request_id(kind: str) -> str:
    return f"mcp_resource_{kind}_{uuid4().hex[:16]}"


def _raise_public_error(exc: BaseException) -> NoReturn:
    """只把稳定 code 和公开消息交给 MCP Client。"""

    if isinstance(exc, McpExportError):
        raise RuntimeError(
            f"{exc.code}: {exc.public_message}"
        ) from None
    raise RuntimeError(
        "MCP_EXPORT_INTERNAL: MCP Export internal error"
    ) from None


def build_mcp_export_server(service: ReadOnlyMcpExportService):
    # 动态 import 保证 MCP_EXPORT_ENABLED=false 时普通 CLI/API 不依赖 SDK。
    from mcp.server import MCPServer
    from mcp.server.mcpserver import Context
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response

    mcp = MCPServer(
        "Paper Reproduction Copilot Read-only Export",
        version="phase54-v1",
    )

    @mcp.tool()
    def get_reproduction_status(
        job_id: Annotated[
            str,
            Field(
                description=(
                    "Server-generated reproduction Job ID: "
                    "job_ followed by 32 lowercase hex characters"
                ),
                pattern=r"^job_[0-9a-f]{32}$",
            ),
        ],
        ctx: Context,
    ) -> McpExportJobStatus:
        """Read a bounded public status snapshot for one known reproduction Job."""

        try:
            return service.get_status(
                job_id=job_id,
                request_id=_request_id(ctx),
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.tool()
    def list_reproduction_artifacts(
        job_id: Annotated[
            str,
            Field(pattern=r"^job_[0-9a-f]{32}$"),
        ],
        ctx: Context,
        limit: Annotated[
            int,
            Field(ge=1, le=100),
        ] = 20,
    ) -> McpExportArtifactPage:
        """List bounded public Artifact metadata without paths or download URLs."""

        try:
            return service.list_artifacts(
                job_id=job_id,
                limit=limit,
                request_id=_request_id(ctx),
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.tool()
    def read_reproduction_final_report(
        job_id: Annotated[
            str,
            Field(pattern=r"^job_[0-9a-f]{32}$"),
        ],
        ctx: Context,
    ) -> McpExportFinalReport:
        """Read the server-selected, integrity-checked final report for one Job."""

        try:
            return service.read_final_report(
                job_id=job_id,
                request_id=_request_id(ctx),
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.tool()
    def search_reproduction_evidence(
        job_id: Annotated[
            str,
            Field(pattern=r"^job_[0-9a-f]{32}$"),
        ],
        query: Annotated[
            str,
            Field(
                min_length=1,
                max_length=500,
                description=(
                    "Question used only to rank local Job, Event, "
                    "Artifact and Log evidence"
                ),
            ),
        ],
        ctx: Context,
        limit: Annotated[
            int,
            Field(ge=1, le=6),
        ] = 5,
    ) -> McpExportEvidencePack:
        """Search bounded local evidence and return citation-bound excerpts."""

        try:
            return service.search_evidence(
                job_id=job_id,
                query=query,
                limit=limit,
                request_id=_request_id(ctx),
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.resource(
        "repro://jobs/{job_id}/status",
        mime_type="application/json",
    )
    def job_status_resource(job_id: str) -> str:
        """Public status resource for a known reproduction Job."""

        try:
            result = service.get_status(
                job_id=job_id,
                request_id=_resource_request_id("status"),
                operation="resource_job_status",
            )
            return json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.resource(
        "repro://jobs/{job_id}/final-report",
        mime_type="application/json",
    )
    def final_report_resource(job_id: str) -> str:
        """Integrity-bound JSON projection of one final report."""

        try:
            result = service.read_final_report(
                job_id=job_id,
                request_id=_resource_request_id("report"),
                operation="resource_final_report",
            )
            return json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except Exception as exc:
            _raise_public_error(exc)

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(_request: Request) -> Response:
        # Custom route 不返回 Job、Token、路径或数据库信息。
        return JSONResponse(
            {
                "status": "ok",
                "service": "paper-reproduction-mcp-export",
                "version": "phase54-v1",
            }
        )

    return mcp
```

### 18.2 关于 `Context` 参数

官方 SDK 会识别 `Context` 类型并由 Host 注入，不把它加入模型可见 JSON Schema。`ctx` 放在有默认值的
`limit` 前面，是为了同时满足 Python 参数规则和 SDK 注入规则。运行 `tools/list` 时必须确认：

```text
inputSchema 中没有 ctx
required 中没有 ctx
Client 不能通过 arguments 提供 ctx
```

最终验收以真实 `tools/list` 为准，而不是只看 Python 函数签名。

### 18.3 为什么使用 Pydantic 返回类型

官方 SDK 会从返回类型生成 `outputSchema`，并在发送前验证 structured output。这样 Client 能得到：

```text
content                 兼容旧 Host 的文本表示
structuredContent       符合 Pydantic outputSchema 的对象
```

本项目只把 `structuredContent` 视为机器可验证结果。兼容文本不能用来恢复缺失字段或绕过 Hash。

### 18.4 Resource 为什么返回 JSON 而不是纯 Markdown

如果 final report Resource 只返回 Markdown，Client 无法同时获得 Artifact Hash、截断状态和内容 Hash。返回
JSON 可以保留完整身份。Host 若要展示 Markdown，应读取 `content` 字段后渲染，而不是丢弃 metadata。

---

## 十九、实现本机 Bearer Auth 中间件

### 19.1 需要新增：`app/mcp_export/auth.py`

```python
from __future__ import annotations

import secrets

from starlette.responses import JSONResponse


class LocalBearerAuthMiddleware:
    """保护本机 HTTP MCP endpoint；不实现 OAuth 或 Token 转发。"""

    def __init__(
        self,
        app,
        *,
        expected_token: str,
        public_paths: set[str] | None = None,
    ) -> None:
        token = expected_token.strip()
        if len(token) < 32:
            raise ValueError("MCP Export Token 至少需要 32 个字符")
        self.app = app
        self._expected = token.encode("utf-8")
        self.public_paths = set(public_paths or {"/healthz"})

    @staticmethod
    def _authorization_values(scope) -> list[bytes]:
        return [
            value
            for key, value in scope.get("headers", [])
            if key.lower() == b"authorization"
        ]

    async def __call__(self, scope, receive, send) -> None:
        # lifespan 和非 HTTP scope 必须原样传递给 MCP SDK。
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("path") in self.public_paths:
            await self.app(scope, receive, send)
            return

        values = self._authorization_values(scope)
        valid = False
        if len(values) == 1:
            try:
                raw = values[0].decode("utf-8")
            except UnicodeDecodeError:
                raw = ""
            scheme, separator, credential = raw.partition(" ")
            valid = (
                separator == " "
                and scheme.lower() == "bearer"
                and secrets.compare_digest(
                    credential.encode("utf-8"),
                    self._expected,
                )
            )

        if not valid:
            response = JSONResponse(
                {
                    "error": {
                        "code": "MCP_EXPORT_UNAUTHORIZED",
                        "message": "Authentication required",
                    }
                },
                status_code=401,
                headers={
                    "WWW-Authenticate": (
                        'Bearer realm="paper-reproduction-mcp"'
                    ),
                    "Cache-Control": "no-store",
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
```

### 19.2 为什么拒绝重复 Authorization Header

不同代理或框架可能选择第一个或最后一个重复 Header。如果同时存在合法 Token 和攻击者 Token，解析差异会
造成 Request Smuggling 风格的身份歧义。因此必须要求“恰好一个 Authorization Header”。

### 19.3 为什么不记录认证失败 Token Hash

认证失败只需要记录计数，不需要保存攻击者提交的 credential。对 Token 做普通 SHA-256 不会自动安全，反而
为离线猜测提供验证值。可以在 Telemetry 中记录：

```text
event=mcp_export.auth.denied
remote=loopback
reason=missing_or_invalid
```

不能记录 Header 或 credential。

---

## 二十、构造 ASGI 应用

### 20.1 需要新增：`app/mcp_export/asgi.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.mcp_export.auth import LocalBearerAuthMiddleware
from app.mcp_export.factory import (
    McpExportRuntime,
    build_mcp_export_runtime,
    resolve_mcp_export_token,
)
from app.mcp_export.server import build_mcp_export_server


@dataclass(frozen=True)
class McpExportAsgiBundle:
    mcp_server: Any
    app: Any
    runtime: McpExportRuntime


def build_mcp_export_asgi_bundle(
    *,
    runtime: McpExportRuntime | None = None,
    token: str | None = None,
) -> McpExportAsgiBundle:
    selected_runtime = runtime or build_mcp_export_runtime()
    selected_token = token or resolve_mcp_export_token()
    server = build_mcp_export_server(selected_runtime.service)

    # 不 Mount 到另一个应用，因此 SDK 自带 lifespan 可以正常启动
    # session_manager；默认 transport security 继续保护 localhost Host。
    inner = server.streamable_http_app()
    protected = LocalBearerAuthMiddleware(
        inner,
        expected_token=selected_token,
        public_paths={"/healthz"},
    )
    return McpExportAsgiBundle(
        mcp_server=server,
        app=protected,
        runtime=selected_runtime,
    )
```

不要在模块顶层写：

```python
# 错误示例：任何 import 都会解析 Secret、打开数据库并要求安装 MCP SDK。
app = build_mcp_export_asgi_bundle().app
```

CLI 在 Feature Flag 检查通过后再调用 Factory，测试则显式注入 Runtime 和 Token。

### 20.2 DNS Rebinding 防护

官方 SDK 的 `streamable_http_app()` 默认按 localhost 场景启用安全 Host allowlist。第一版不要传自定义
`TransportSecuritySettings` 放宽它，也不要因为某个客户端使用主机名失败就改成 `allowed_hosts=["*"]`。

客户端统一连接：

```text
http://127.0.0.1:8770/mcp
```

如果 SDK 默认 allowlist 不接受字面量 `127.0.0.1:8770`，应使用精确 allowlist，而不是通配：

```python
from mcp.server.transport_security import TransportSecuritySettings

security = TransportSecuritySettings(
    allowed_hosts=["127.0.0.1:8770"],
    allowed_origins=[],
)
inner = server.streamable_http_app(
    transport_security=security,
)
```

只有真实测试证明需要时才增加这段。

---

## 二十一、增加 CLI 启动与 Doctor

### 21.1 必须修改：`app/main.py`

在现有 `mcp-doctor` 命令之后增加：

```python
@app.command("mcp-export-doctor")
def mcp_export_doctor() -> None:
    """离线检查 Phase 54 配置、Token 和 Audit，不启动监听端口。"""

    from app.mcp_export.factory import inspect_mcp_export

    report = inspect_mcp_export()
    typer.echo(
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
    )
    if not report.ready:
        raise typer.Exit(code=1)


@app.command("serve-mcp-export")
def serve_mcp_export() -> None:
    """启动独立的本机只读 Streamable HTTP MCP Server。"""

    if not settings.mcp_export_enabled:
        raise typer.BadParameter(
            "MCP_EXPORT_ENABLED=false；拒绝启动 MCP Export"
        )
    if settings.mcp_export_host != "127.0.0.1":
        raise typer.BadParameter(
            "Phase 54 只允许监听 127.0.0.1"
        )

    from app.mcp_export.asgi import build_mcp_export_asgi_bundle

    try:
        import uvicorn
    except ImportError as exc:
        raise typer.BadParameter(
            "缺少 MCP/uvicorn 依赖，请安装 python -m pip install -e '.[mcp]'"
        ) from exc

    bundle = build_mcp_export_asgi_bundle()
    uvicorn.run(
        bundle.app,
        host=settings.mcp_export_host,
        port=settings.mcp_export_port,
        log_level="info",
        access_log=False,
        # 开发环境也不要自动 reload，避免重复初始化 Vault/DB。
        reload=False,
    )
```

### 21.2 CLI 行为

```text
mcp-export-doctor
    不监听端口
    不调用模型
    不读取 Job 内容
    检查 Token 用途与 Audit DB

serve-mcp-export
    检查 Feature Flag
    强制 127.0.0.1
    解析独立 Secret
    构造最小只读 Runtime
    启动 /mcp 和 /healthz
```

### 21.3 不要把 Token 变成 CLI Option

禁止：

```bash
python -m app.main serve-mcp-export --token secret-value
```

因为它可能进入：

```text
Shell history
ps / process list
IDE launch.json
日志和工单截图
```

---

## 二十二、接入 Retention 与容量盘点

### 22.1 必须修改：`app/retention/ports.py`

在 `McpEvidenceRetentionPort` 后增加：

```python
class McpExportAuditRetentionPort(Protocol):
    def delete_for_job(self, job_id: str) -> int: ...
```

### 22.2 必须修改：`app/retention/service.py`

导入新端口：

```python
from app.retention.ports import (
    # ...保留现有导入...
    McpEvidenceRetentionPort,
    McpExportAuditRetentionPort,
)
```

增加 No-op：

```python
class _NoOpMcpExportAuditRetentionPort:
    def delete_for_job(self, job_id: str) -> int:
        del job_id
        return 0
```

给 `RetentionService.__init__` 增加可选依赖：

```python
class RetentionService:
    def __init__(
        self,
        *,
        # ...保留现有参数...
        mcp_evidence: McpEvidenceRetentionPort | None = None,
        mcp_export_audit: McpExportAuditRetentionPort | None = None,
    ):
        # ...保留现有赋值...
        self.mcp_evidence = (
            mcp_evidence or _NoOpMcpEvidenceRetentionPort()
        )
        self.mcp_export_audit = (
            mcp_export_audit
            or _NoOpMcpExportAuditRetentionPort()
        )
```

在 `_sweep_locked()` 中 `mcp_evidence` 后增加独立 Journal Step：

```text
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="mcp_export_audit",
                    operation=lambda target=target: (
                        self.mcp_export_audit.delete_for_job(
                            target.job_id
                        )
                    ),
                )
```

不要把 MCP Gateway Evidence 和 MCP Export Audit 合并成一个 Step。前者是入站外部证据，后者是出站读取
审计；其中一个删除失败时，另一个仍应有独立重试和 Journal 状态。

### 22.3 必须修改：`app/retention/factory.py`

增加 No-op 和 Factory：

```python
class NoOpMcpExportAuditRetentionPort:
    def delete_for_job(self, job_id: str) -> int:
        del job_id
        return 0


def _build_mcp_export_audit_retention():
    path = settings.mcp_export_audit_db_path
    if settings.mcp_export_enabled or path.exists():
        from app.mcp_export.audit import (
            SqliteMcpExportAuditRepository,
        )

        repository = SqliteMcpExportAuditRepository(path)
        repository.initialize()
        return repository
    return NoOpMcpExportAuditRetentionPort()
```

构造 `RetentionService` 时注入：

```text
        mcp_evidence=_build_mcp_evidence_retention(),
        mcp_export_audit=_build_mcp_export_audit_retention(),
```

给 `build_inventory()` 增加 SQLite/WAL/SHM：

```text
    roots.extend(
        _sqlite_roots(
            "mcp_export_audit_db",
            settings.mcp_export_audit_db_path.resolve(),
        )
    )
```

即使 Feature Flag 已关闭，只要历史数据库还存在，Retention 仍应能清理它。

---

## 二十三、理解 `_execute` 为什么把限流放在 Audit 边界内

第 16 节给出的已经是最终实现，不需要在这里再次替换代码。它先记录开始时间和输入 Hash，再在同一个 `try`
中执行限流与业务函数，原因是限流拒绝也属于一次真实、已认证的调用结果：

```text
开始计时并计算 input_sha256

尝试获取调用额度
如果额度足够
    执行业务函数

如果限流或业务函数抛出异常
    收敛为稳定公开错误码
    写入 status=failed 的 Hash-only Audit
    向上抛出公开错误

如果业务函数成功
    计算 output_sha256
    写入 status=succeeded 的 Hash-only Audit
    返回公开 Pydantic 输出
```

不要把 `rate_limiter.acquire()` 移到 `try` 之前，否则 `MCP_EXPORT_RATE_LIMITED` 不会形成失败 Audit。也不要在
Audit 写入失败后继续返回业务结果；Audit 是这个公开面的安全边界，必须 fail closed。

如果 `job_id` 本身不符合 Schema，SDK 或 `validate_job_id()` 会在领域调用前拒绝。第一版不把非法原始 Job ID
写入 Audit，避免 Audit Schema 接收攻击字符串；认证失败和 Schema 拒绝通过 Telemetry counter 观察。

---

## 二十四、增加测试辅助对象

### 24.1 需要新增：`tests/mcp_export_helpers.py`

```python
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.chat.schemas import ChatCitation
from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.rate_limit import InMemoryMcpExportRateLimiter
from app.mcp_export.service import ReadOnlyMcpExportService
from app.secrets.redaction import SecretRedactor
from app.tool_calling.schemas import (
    EvidenceToolOutput,
    ToolEvidenceItem,
)


JOB_ID = "job_" + "a" * 32
RUN_ID = "run_phase54_test"
ARTIFACT_ID = "artifact_final_report"
ARTIFACT_SHA256 = "b" * 64
SECRET_VALUE = "phase54-sensitive-token-1234567890"


class FakeInteraction:
    def __init__(self) -> None:
        self.internal_job = SimpleNamespace(
            job_id=JOB_ID,
            run_id=RUN_ID,
        )
        self.job_service = SimpleNamespace(
            get=self._get_internal_job,
        )

    def _get_internal_job(self, job_id: str):
        if job_id != JOB_ID:
            from app.job_runtime.errors import JobNotFoundError

            raise JobNotFoundError(job_id)
        return self.internal_job

    def get_job(self, job_id: str):
        self._get_internal_job(job_id)
        return SimpleNamespace(
            job_id=JOB_ID,
            run_id=RUN_ID,
            status="waiting_for_input",
            version=7,
            attempt_count=1,
            max_attempts=3,
            allowed_operations=[
                SimpleNamespace(kind="submit_decision")
            ],
            result=SimpleNamespace(
                final_status=None,
                stage_error_count=1,
                output_file_count=8,
            ),
            error={"code": "TRAINING_FAILED", "message": "hidden"},
            created_at="2026-08-14T00:00:00+00:00",
            updated_at="2026-08-14T00:01:00+00:00",
        )


class FakeArtifactDelivery:
    def __init__(self) -> None:
        self.views = [
            SimpleNamespace(
                artifact_id=ARTIFACT_ID,
                run_id=RUN_ID,
                layer="report",
                relative_path="reports/final_report.md",
                media_type="text/markdown",
                sha256=ARTIFACT_SHA256,
                size_bytes=36,
                producer_node="final_report",
                created_at="2026-08-14T00:02:00+00:00",
                preview_supported=True,
            )
        ]

    def list_views(self, _job):
        return list(self.views)

    def preview(self, *, job, artifact_id: str):
        assert job.job_id == JOB_ID
        assert artifact_id == ARTIFACT_ID
        content = (
            "# Final report\n\nEvidence-grounded result.\n"
            f"API_TOKEN={SECRET_VALUE}"
        )
        return SimpleNamespace(
            artifact_id=ARTIFACT_ID,
            media_type="text/markdown",
            sha256=ARTIFACT_SHA256,
            total_size_bytes=len(content.encode("utf-8")),
            returned_bytes=len(content.encode("utf-8")),
            truncated=False,
            content=content,
        )


class FakeEvidenceRegistry:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def invoke(self, **kwargs):
        self.calls.append(kwargs)
        output = EvidenceToolOutput(
            summary="matching evidence",
            items=[
                ToolEvidenceItem(
                    citation=ChatCitation(
                        citation_id=(
                            f"artifact:{ARTIFACT_ID}:1"
                        ),
                        source_type="artifact",
                        label="reports/final_report.md",
                        artifact_id=ARTIFACT_ID,
                        relative_path="reports/final_report.md",
                        artifact_sha256=ARTIFACT_SHA256,
                        locator="chunk 1",
                    ),
                    content=(
                        "The run stopped before training completed. "
                        f"Bearer {SECRET_VALUE}"
                    ),
                )
            ],
            truncated=False,
        )
        return SimpleNamespace(
            output=output.model_dump(mode="json"),
            failure=None,
        )


def build_test_service(
    tmp_path: Path,
) -> tuple[
    ReadOnlyMcpExportService,
    SqliteMcpExportAuditRepository,
    FakeArtifactDelivery,
    FakeEvidenceRegistry,
]:
    audit = SqliteMcpExportAuditRepository(
        tmp_path / "mcp_export_audit.sqlite"
    )
    audit.initialize()
    delivery = FakeArtifactDelivery()
    registry = FakeEvidenceRegistry()
    service = ReadOnlyMcpExportService(
        interaction=FakeInteraction(),
        artifact_delivery=delivery,
        evidence_registry=registry,
        audit_repository=audit,
        rate_limiter=InMemoryMcpExportRateLimiter(
            max_calls_per_minute=100
        ),
        redactor=SecretRedactor.from_values([SECRET_VALUE]),
        max_artifacts=50,
        max_report_chars=50000,
    )
    return service, audit, delivery, registry
```

测试辅助对象只模拟 Port，不读取真实论文、仓库、Run 目录或 Secret Vault。

---

## 二十五、Schema 与 Identity 测试

### 25.1 需要新增：`tests/test_mcp_export_schemas.py`

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.mcp_export.identity import (
    normalize_query,
    validate_job_id,
)
from app.mcp_export.schemas import (
    McpExportArtifact,
    McpExportAuditRecord,
)


def test_validate_job_id_accepts_only_generated_identity() -> None:
    valid = "job_" + "a" * 32
    assert validate_job_id(valid) == valid

    for invalid in [
        "job_test",
        "../job_" + "a" * 32,
        "job_" + "A" * 32,
        "job_" + "a" * 31,
    ]:
        with pytest.raises(Exception):
            validate_job_id(invalid)


def test_normalize_query_rejects_control_characters() -> None:
    assert normalize_query("  failure   reason ") == "failure reason"
    with pytest.raises(Exception):
        normalize_query("failure\x00reason")


def test_artifact_projection_rejects_path_like_display_name() -> None:
    with pytest.raises(ValidationError):
        McpExportArtifact(
            artifact_id="artifact_1",
            run_id="run_1",
            display_name="reports/final_report.md",
            layer="report",
            media_type="text/markdown",
            sha256="a" * 64,
            size_bytes=10,
            producer_node="final_report",
            created_at="2026-08-14T00:00:00+00:00",
            preview_supported=True,
        )


def test_success_audit_requires_output_hash() -> None:
    with pytest.raises(ValidationError):
        McpExportAuditRecord(
            call_id="mcpexportcall_" + "a" * 24,
            request_id="request-1",
            actor_fingerprint="b" * 64,
            operation="get_reproduction_status",
            job_id="job_" + "c" * 32,
            status="succeeded",
            input_sha256="d" * 64,
            output_sha256=None,
            started_at="2026-08-14T00:00:00+00:00",
            finished_at="2026-08-14T00:00:01+00:00",
            duration_ms=1.0,
        )
```

---

## 二十六、Audit 与 Rate Limit 测试

### 26.1 需要新增：`tests/test_mcp_export_audit.py`

```python
from __future__ import annotations

from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.schemas import McpExportAuditRecord


def _record(job_id: str) -> McpExportAuditRecord:
    return McpExportAuditRecord(
        call_id="mcpexportcall_" + "a" * 24,
        request_id="request-1",
        actor_fingerprint="b" * 64,
        operation="get_reproduction_status",
        job_id=job_id,
        status="succeeded",
        input_sha256="c" * 64,
        output_sha256="d" * 64,
        started_at="2026-08-14T00:00:00+00:00",
        finished_at="2026-08-14T00:00:01+00:00",
        duration_ms=1.0,
    )


def test_audit_round_trip_and_delete(tmp_path) -> None:
    job_id = "job_" + "e" * 32
    repository = SqliteMcpExportAuditRepository(
        tmp_path / "audit.sqlite"
    )
    repository.initialize()
    repository.put(_record(job_id))

    assert repository.list_for_job(job_id) == [_record(job_id)]
    assert repository.delete_for_job(job_id) == 1
    assert repository.delete_for_job(job_id) == 0
    assert repository.list_for_job(job_id) == []


def test_audit_database_does_not_store_raw_payload(tmp_path) -> None:
    path = tmp_path / "audit.sqlite"
    repository = SqliteMcpExportAuditRepository(path)
    repository.initialize()
    repository.put(_record("job_" + "f" * 32))

    raw = path.read_bytes()
    assert b"Bearer " not in raw
    assert b"failure reason from user" not in raw
```

### 26.2 需要新增：`tests/test_mcp_export_rate_limit.py`

```python
from __future__ import annotations

import pytest

from app.mcp_export.errors import McpExportRateLimited
from app.mcp_export.rate_limit import InMemoryMcpExportRateLimiter


def test_rate_limiter_uses_sliding_window() -> None:
    now = [100.0]
    limiter = InMemoryMcpExportRateLimiter(
        max_calls_per_minute=2,
        clock=lambda: now[0],
    )

    limiter.acquire("actor-a")
    limiter.acquire("actor-a")
    with pytest.raises(McpExportRateLimited):
        limiter.acquire("actor-a")

    now[0] = 161.0
    limiter.acquire("actor-a")
```

---

## 二十七、公开投影 Service 测试

### 27.1 需要新增：`tests/test_mcp_export_service.py`

```python
from __future__ import annotations

import pytest

from app.mcp_export.errors import McpExportFinalReportNotFound
from app.mcp_export.identity import sha256_text
from tests.mcp_export_helpers import (
    ARTIFACT_ID,
    JOB_ID,
    SECRET_VALUE,
    build_test_service,
)


def test_status_is_a_narrow_public_projection(tmp_path) -> None:
    service, audit, _delivery, _registry = build_test_service(tmp_path)

    status = service.get_status(
        job_id=JOB_ID,
        request_id="request-status",
    )

    payload = status.model_dump(mode="json")
    assert status.waiting_for_user is True
    assert status.error_code == "TRAINING_FAILED"
    assert "run_dir" not in payload
    assert "thread_id" not in payload
    assert "claim_token" not in payload
    assert "message" not in payload
    assert len(audit.list_for_job(JOB_ID)) == 1


def test_artifacts_do_not_export_relative_path(tmp_path) -> None:
    service, _audit, _delivery, _registry = build_test_service(tmp_path)

    page = service.list_artifacts(
        job_id=JOB_ID,
        limit=20,
        request_id="request-artifacts",
    )

    assert page.items[0].artifact_id == ARTIFACT_ID
    assert page.items[0].display_name == "final_report.md"
    serialized = page.model_dump_json()
    assert "reports/final_report.md" not in serialized
    assert "relative_path" not in serialized
    assert "object_key" not in serialized


def test_final_report_is_server_selected_and_hash_bound(tmp_path) -> None:
    service, _audit, _delivery, _registry = build_test_service(tmp_path)

    report = service.read_final_report(
        job_id=JOB_ID,
        request_id="request-report",
    )

    assert report.artifact_id == ARTIFACT_ID
    assert report.content_sha256 == sha256_text(report.content)
    assert report.content.startswith("# Final report")
    assert SECRET_VALUE not in report.content
    assert "<redacted>" in report.content


def test_missing_final_report_is_a_stable_error(tmp_path) -> None:
    service, audit, delivery, _registry = build_test_service(tmp_path)
    delivery.views = []

    with pytest.raises(McpExportFinalReportNotFound):
        service.read_final_report(
            job_id=JOB_ID,
            request_id="request-no-report",
        )

    records = audit.list_for_job(JOB_ID)
    assert records[0].error_code == "MCP_EXPORT_FINAL_REPORT_NOT_FOUND"


def test_evidence_uses_only_local_source_types(tmp_path) -> None:
    service, _audit, _delivery, registry = build_test_service(tmp_path)

    pack = service.search_evidence(
        job_id=JOB_ID,
        query="Why did training fail?",
        limit=3,
        request_id="request-evidence",
    )

    raw_input = registry.calls[0]["raw_input"]
    assert raw_input["source_types"] == [
        "job",
        "event",
        "artifact",
        "log",
    ]
    assert "mcp" not in raw_input["source_types"]
    assert "web" not in raw_input["source_types"]
    assert pack.items[0].citation.label == f"artifact:{ARTIFACT_ID}"
    assert "reports/final_report.md" not in pack.model_dump_json()
    assert SECRET_VALUE not in pack.model_dump_json()
    assert "<redacted>" in pack.items[0].excerpt
```

---

## 二十八、官方 MCP SDK In-memory 测试

### 28.1 需要新增：`tests/test_mcp_export_server.py`

```python
from __future__ import annotations

import pytest

from tests.mcp_export_helpers import JOB_ID, build_test_service


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    # MCP Python SDK 使用 asyncio；固定 backend 也避免 pytest 尝试未安装的 Trio。
    return "asyncio"


async def test_server_lists_exactly_four_read_only_tools(tmp_path) -> None:
    mcp_module = pytest.importorskip("mcp")
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)

    async with mcp_module.Client(server) as client:
        listed = await client.list_tools()

    names = {item.name for item in listed.tools}
    assert names == {
        "get_reproduction_status",
        "list_reproduction_artifacts",
        "read_reproduction_final_report",
        "search_reproduction_evidence",
    }
    assert not names.intersection(
        {
            "run_command",
            "submit_decision",
            "approve_action",
            "apply_patch",
            "cancel_job",
        }
    )


async def test_status_tool_returns_structured_content(tmp_path) -> None:
    mcp_module = pytest.importorskip("mcp")
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)

    async with mcp_module.Client(server) as client:
        result = await client.call_tool(
            "get_reproduction_status",
            {"job_id": JOB_ID},
        )

    assert result.is_error is not True
    assert result.structured_content["job_id"] == JOB_ID
    assert "run_dir" not in result.structured_content


async def test_tool_schema_has_no_path_or_authority_fields(tmp_path) -> None:
    mcp_module = pytest.importorskip("mcp")
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)

    async with mcp_module.Client(server) as client:
        listed = await client.list_tools()

    serialized = str(
        [item.input_schema for item in listed.tools]
    ).lower()
    for forbidden in [
        "path",
        "endpoint",
        "token",
        "capability",
        "actor",
        "tool_name",
        "ctx",
    ]:
        assert forbidden not in serialized


async def test_resource_templates_are_fixed(tmp_path) -> None:
    mcp_module = pytest.importorskip("mcp")
    from app.mcp_export.server import build_mcp_export_server

    service, _audit, _delivery, _registry = build_test_service(tmp_path)
    server = build_mcp_export_server(service)

    async with mcp_module.Client(server) as client:
        listed = await client.list_resource_templates()

    uris = {str(item.uri_template) for item in listed.resource_templates}
    assert uris == {
        "repro://jobs/{job_id}/status",
        "repro://jobs/{job_id}/final-report",
    }
```

### 28.2 为什么优先使用 In-memory Client

`Client(server)` 仍然经过真实 MCP tools/list、Schema 校验、tools/call 和 structured output，只是不经过端口。
它能稳定测试协议契约，不受端口占用、网络和 Token 配置影响。HTTP/Auth 在下一组单独测试。

---

## 二十九、ASGI Bearer Auth 测试

### 29.1 需要新增：`tests/test_mcp_export_auth.py`

```python
from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.mcp_export.auth import LocalBearerAuthMiddleware


TOKEN = "phase54-test-token-" + "x" * 32


@pytest.fixture
def anyio_backend() -> str:
    # 本组 ASGI 测试不需要 Trio，固定 asyncio 让本地与 CI 行为一致。
    return "asyncio"


async def endpoint(_request: Request):
    return JSONResponse({"ok": True})


def build_app():
    inner = Starlette(
        routes=[
            Route("/mcp", endpoint, methods=["POST"]),
            Route("/healthz", endpoint, methods=["GET"]),
        ]
    )
    return LocalBearerAuthMiddleware(
        inner,
        expected_token=TOKEN,
        public_paths={"/healthz"},
    )


@pytest.mark.anyio
async def test_missing_token_is_rejected() -> None:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    ) as client:
        response = await client.post("/mcp")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MCP_EXPORT_UNAUTHORIZED"
    assert "Bearer" in response.headers["WWW-Authenticate"]


@pytest.mark.anyio
async def test_valid_token_reaches_inner_app() -> None:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    ) as client:
        response = await client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.anyio
async def test_duplicate_authorization_headers_are_rejected() -> None:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    ) as client:
        response = await client.post(
            "/mcp",
            headers=[
                ("Authorization", f"Bearer {TOKEN}"),
                ("Authorization", "Bearer attacker"),
            ],
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_healthz_contains_no_private_state() -> None:
    transport = httpx.ASGITransport(app=build_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    ) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
```

---

## 三十、Authority 与 Import Boundary 测试

### 30.1 需要新增：`tests/test_mcp_export_authority.py`

```python
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "app" / "mcp_export"

FORBIDDEN_IMPORT_PREFIXES = {
    "app.execution",
    "app.nodes.executor_node",
    "app.nodes.human_review_node",
    "app.repair",
    "app.resources.worker",
    "app.research_browser",
    "app.mcp_gateway",
    "app.model_routing",
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_mcp_export_does_not_import_mutation_or_network_runtime() -> None:
    violations = []
    for path in PACKAGE.glob("*.py"):
        for module in imported_modules(path):
            if any(
                module == prefix or module.startswith(prefix + ".")
                for prefix in FORBIDDEN_IMPORT_PREFIXES
            ):
                violations.append((path.name, module))
    assert violations == []


def test_service_does_not_use_direct_filesystem_or_process_apis() -> None:
    source = (PACKAGE / "service.py").read_text(encoding="utf-8")
    for forbidden in [
        "subprocess.",
        "os.system",
        "shell=True",
        "requests.",
        "httpx.",
        ".read_text(",
        ".read_bytes(",
        ".open(",
    ]:
        assert forbidden not in source


def test_server_exports_no_mutation_names() -> None:
    source = (PACKAGE / "server.py").read_text(encoding="utf-8")
    for forbidden in [
        "submit_decision",
        "approve_action",
        "run_command",
        "apply_patch",
        "cancel_job",
        "request_resource",
    ]:
        assert f"def {forbidden}" not in source
```

这个测试不是形式主义。未来有人为了“方便”在 `mcp_export/factory.py` import `build_graph()` 或
`build_research_browser_service()` 时，它会立刻阻止权限面扩张。

---

## 三十一、Retention 测试

### 31.1 需要新增：`tests/test_mcp_export_retention.py`

```python
from __future__ import annotations

from app.mcp_export.audit import SqliteMcpExportAuditRepository
from app.mcp_export.schemas import McpExportAuditRecord


def test_export_audit_satisfies_retention_port(tmp_path) -> None:
    job_id = "job_" + "a" * 32
    repository = SqliteMcpExportAuditRepository(
        tmp_path / "audit.sqlite"
    )
    repository.initialize()
    repository.put(
        McpExportAuditRecord(
            call_id="mcpexportcall_" + "b" * 24,
            request_id="request-1",
            actor_fingerprint="c" * 64,
            operation="resource_job_status",
            job_id=job_id,
            status="succeeded",
            input_sha256="d" * 64,
            output_sha256="e" * 64,
            started_at="2026-08-14T00:00:00+00:00",
            finished_at="2026-08-14T00:00:01+00:00",
            duration_ms=1.0,
        )
    )

    assert repository.delete_for_job(job_id) == 1
    assert repository.list_for_job(job_id) == []
```

还要在现有 Retention 集成测试的 Fake Port 中增加 `mcp_export_audit`，并断言 Sweep Journal 包含：

```text
step_name = mcp_export_audit
status = completed
```

不要只测试 Repository；必须证明 RetentionService 的实际 Sweep 顺序会调用它。

---

## 三十二、专项测试命令

### 32.1 不安装 MCP SDK 也应通过的领域测试

```bash
python -m pytest -q \
  tests/test_mcp_export_schemas.py \
  tests/test_mcp_export_audit.py \
  tests/test_mcp_export_rate_limit.py \
  tests/test_mcp_export_service.py \
  tests/test_mcp_export_auth.py \
  tests/test_mcp_export_authority.py \
  tests/test_mcp_export_retention.py
```

`test_mcp_export_server.py` 使用 `pytest.importorskip("mcp")`，未安装 extra 时会跳过，而不是让项目普通环境无法
import。

### 32.2 安装 MCP extra 后运行协议测试

```bash
python -m pip install -e '.[mcp]'

python -m pytest -q \
  tests/test_mcp_export_server.py
```

### 32.3 Phase 53 与 Phase 52 回归

```bash
python -m pytest -q \
  tests/test_mcp_gateway_schemas.py \
  tests/test_mcp_gateway_policy.py \
  tests/test_mcp_gateway_repository.py \
  tests/test_mcp_gateway_gateway.py \
  tests/test_mcp_gateway_authority.py \
  tests/test_tool_calling_schemas.py \
  tests/test_tool_calling_catalog.py \
  tests/test_tool_calling_evidence_tools.py \
  tests/test_tool_calling_loop.py \
  tests/test_tool_calling_chat_integration.py \
  tests/test_tool_calling_authority.py \
  tests/test_tool_contract_registry.py
```

### 32.4 Secret、Artifact 和 Retention 回归

```bash
python -m pytest -q \
  tests/test_secret_store.py \
  tests/test_secret_redaction.py \
  tests/test_artifact_delivery_service.py \
  tests/test_artifact_delivery_api.py \
  tests/test_notification_retention.py \
  tests/test_knowledge_retention.py \
  tests/test_failure_memory_retention.py
```

如果某些文件在当前分支不存在，先用：

```bash
rg --files tests | sort
```

确认真实测试名，不要把“找不到测试文件”误判为实现失败。

### 32.5 全量测试

```bash
python -m pytest -q --basetemp=.pytest-tmp/phase54
```

项目环境应为 Python 3.10+。如果终端显示 Python 3.9，先切换环境；不要根据 3.9 下的 SDK ImportError 修改
Phase 54 代码。

---

## 三十三、手工验收前准备

### 33.1 确认项目根目录

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
pwd
```

后续所有数据库、缓存和测试临时目录都应位于项目路径或 `.pytest-tmp/`，不要在 `/tmp` 创建本项目脚本。

### 33.2 确认 Python 和依赖

```bash
python --version
python -m pip show mcp
python -m pip show httpx2
```

预期：

```text
Python >= 3.10
mcp 2.x
httpx2 已由 MCP SDK 安装
```

### 33.3 初始化 Secret Store

如果尚未初始化：

```bash
python -m app.main init-secret-store
python -m app.main secret-doctor
```

生成随机 Token。下面的命令只把随机值显示在当前终端，不把值写入 Shell history：

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

随后运行：

```bash
python -m app.main set-secret \
  PAPER_COPILOT_MCP_EXPORT_TOKEN \
  --use mcp_export_auth
```

在隐藏提示中输入刚生成的值。完成后只能看到 metadata：

```bash
python -m app.main list-secrets
```

确认输出中：

```text
name=PAPER_COPILOT_MCP_EXPORT_TOKEN
uses=mcp_export_auth
```

不应显示明文。

### 33.4 启用本阶段

在当前验收终端设置：

```bash
export MCP_EXPORT_ENABLED=true
export MCP_EXPORT_HOST=127.0.0.1
export MCP_EXPORT_PORT=8770
```

Phase 53 是否启用与此无关：

```bash
export MCP_GATEWAY_ENABLED=false
```

关闭 Phase 53 后 Phase 54 仍应正常读取本地 Job Evidence，这也是“无传递网络”的一次验收。

---

## 三十四、准备一个可读取的真实 Job

### 34.1 优先使用现有终态 Job

```bash
python -m app.main list-jobs --limit 20
```

选择一个由 Job Runtime 生成、格式类似下面的 ID：

```text
job_0123456789abcdef0123456789abcdef
```

不要使用 `thread_id`、`run_id` 或早期 `run-graph --thread-id` 的自定义字符串替代。Phase 54 的公开 Job ID
严格是 `job_` 加 32 位小写十六进制。

### 34.2 确认 Job 状态

```bash
python -m app.main show-job \
  job_0123456789abcdef0123456789abcdef
```

记录以下公开事实用于比对：

```text
status
version
run_id
final_status
是否等待人工输入
```

### 34.3 确认最终报告是否存在

如果 Web/API 已启动，可以使用现有 Artifact API；如果未启动，可以从 `show-job` 和 Artifact Catalog 命令
确认。Phase 54 只接受 Catalog 中 basename 为 `final_report.md`、类型为 Markdown/Text 且允许预览的 Artifact。

没有 final report 的 Job 仍可测试 Status、Artifact List 和 Evidence Search；读取最终报告应返回稳定的
`MCP_EXPORT_FINAL_REPORT_NOT_FOUND`，这也是正常行为。

---

## 三十五、运行 Doctor

```bash
python -m app.main mcp-export-doctor
```

预期结构：

```json
{
  "enabled": true,
  "ready": true,
  "host": "127.0.0.1",
  "port": 8770,
  "token_available": true,
  "audit_ready": true,
  "tool_names": [
    "get_reproduction_status",
    "list_reproduction_artifacts",
    "read_reproduction_final_report",
    "search_reproduction_evidence"
  ],
  "resource_templates": [
    "repro://jobs/{job_id}/status",
    "repro://jobs/{job_id}/final-report"
  ],
  "issues": []
}
```

常见失败：

| Issue | 含义 | 处理 |
|---|---|---|
| `mcp_export_token_missing` | Vault 没有指定 Secret | 用 `set-secret --use mcp_export_auth` 写入 |
| `mcp_export_host_not_loopback` | 配置要求监听非本机地址 | 改回 `127.0.0.1` |
| `mcp_export_audit_invalid:*` | Audit 路径或 SQLite 不可用 | 检查项目内目录权限和 DB 完整性 |
| `enabled=false` | Feature Flag 未开启 | 只在验收终端设置 `MCP_EXPORT_ENABLED=true` |

Doctor 不连接端口，因此 `ready=true` 只说明本地依赖可构造，不代表 HTTP Server 已启动。

---

## 三十六、启动独立 MCP Export Server

### 36.1 终端 A：启动服务

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
export MCP_EXPORT_ENABLED=true
export MCP_EXPORT_HOST=127.0.0.1
export MCP_EXPORT_PORT=8770

python -m app.main serve-mcp-export
```

预期监听：

```text
http://127.0.0.1:8770/mcp
```

不应监听：

```text
0.0.0.0:8770
[::]:8770
局域网 IP
```

### 36.2 终端 B：检查公开 Health

```bash
curl --fail --silent \
  http://127.0.0.1:8770/healthz
```

预期只包含：

```json
{
  "status": "ok",
  "service": "paper-reproduction-mcp-export",
  "version": "phase54-v1"
}
```

不能包含数据库路径、Job 数量、Token 状态或当前 Job ID。

### 36.3 验证未授权访问

```bash
curl -i \
  -X POST \
  http://127.0.0.1:8770/mcp
```

预期：

```text
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="paper-reproduction-mcp"
Cache-Control: no-store
```

这里不要求请求体是合法 MCP 消息，因为 Auth 必须发生在 JSON-RPC 解析之前。

---

## 三十七、使用真实 MCP Client 验收

### 37.1 终端 B：运行受控 Client

下面脚本不会把 Token 写入文件或命令参数；运行时通过隐藏输入读取。把 `JOB_ID` 改为第 34 节选择的真实 Job。

```bash
python - <<'PY'
import asyncio
import getpass
import json

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


URL = "http://127.0.0.1:8770/mcp"
JOB_ID = "job_0123456789abcdef0123456789abcdef"


async def main() -> None:
    token = getpass.getpass("MCP Export token: ")
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx2.Timeout(30.0, read=60.0),
        follow_redirects=False,
        trust_env=False,
    ) as http_client:
        transport = streamable_http_client(
            URL,
            http_client=http_client,
        )
        async with Client(transport) as client:
            tools = await client.list_tools()
            print("TOOLS")
            print([item.name for item in tools.tools])

            status = await client.call_tool(
                "get_reproduction_status",
                {"job_id": JOB_ID},
            )
            print("STATUS")
            print(
                json.dumps(
                    status.structured_content,
                    ensure_ascii=False,
                    indent=2,
                )
            )

            artifacts = await client.call_tool(
                "list_reproduction_artifacts",
                {"job_id": JOB_ID, "limit": 20},
            )
            print("ARTIFACTS")
            print(
                json.dumps(
                    artifacts.structured_content,
                    ensure_ascii=False,
                    indent=2,
                )
            )

            evidence = await client.call_tool(
                "search_reproduction_evidence",
                {
                    "job_id": JOB_ID,
                    "query": "当前执行状态和失败原因",
                    "limit": 4,
                },
            )
            print("EVIDENCE")
            print(
                json.dumps(
                    evidence.structured_content,
                    ensure_ascii=False,
                    indent=2,
                )
            )

            report = await client.call_tool(
                "read_reproduction_final_report",
                {"job_id": JOB_ID},
            )
            print("FINAL REPORT")
            print(
                json.dumps(
                    report.structured_content,
                    ensure_ascii=False,
                    indent=2,
                )
            )


asyncio.run(main())
PY
```

官方 SDK 2.x 要求自定义 Header 放在 `httpx2.AsyncClient`，再通过
`streamable_http_client(url, http_client=...)` 构造 Transport。不要使用旧版的：

```text
streamable_http_client(url, headers={...})
```

否则会出现 `unexpected keyword argument 'headers'`。

### 37.2 验收 Tool Catalog

输出必须恰好是：

```text
get_reproduction_status
list_reproduction_artifacts
read_reproduction_final_report
search_reproduction_evidence
```

如果出现下面任何名称，立即停止验收并关闭 Feature Flag：

```text
run_command
apply_patch
submit_decision
approve_action
cancel_job
request_resource
search_external_paper_evidence
```

### 37.3 验收状态投影

Status 应与 `show-job` 的公开事实一致，但不应包含：

```text
run_dir
paper_path
repo_path
claim_token
workspace_assignment_token
完整 error message
内部 interrupt value
```

### 37.4 验收 Artifact 投影

Artifact 只应包含：

```text
artifact_id
run_id
display_name
layer
media_type
sha256
size_bytes
producer_node
created_at
preview_supported
```

不应出现：

```text
relative_path
absolute_path
object_key
download_url
blob backend credential
```

### 37.5 验收 Evidence

每个 Evidence Item 必须有：

```text
citation_id
source_type = job | event | artifact | log
excerpt
excerpt_sha256
```

不允许出现 `source_type=web`、`source_type=mcp` 或新的联网调用记录。

---

## 三十八、验收 Resource Template

在上一个 Client 脚本的 `async with Client(...)` 中增加：

```text
            templates = await client.list_resource_templates()
            print(
                [
                    str(item.uri_template)
                    for item in templates.resource_templates
                ]
            )

            status_resource = await client.read_resource(
                f"repro://jobs/{JOB_ID}/status"
            )
            print(status_resource.contents)

            report_resource = await client.read_resource(
                f"repro://jobs/{JOB_ID}/final-report"
            )
            print(report_resource.contents)
```

只能列出两个模板。尝试读取：

```text
file:///etc/passwd
repro://jobs/<job_id>/artifacts/<arbitrary-id>
repro://jobs/<job_id>/run
```

必须返回 Resource Not Found 或协议拒绝，不能落入通用 URI Handler。

---

## 三十九、检查 Hash-only Audit

完成四个 Tool 和两个 Resource 调用后：

```bash
sqlite3 control/mcp_export_audit.sqlite \
  "SELECT operation, status, error_code, length(input_sha256), length(output_sha256) FROM mcp_export_calls ORDER BY started_at;"
```

成功记录预期：

```text
status=succeeded
error_code=NULL
length(input_sha256)=64
length(output_sha256)=64
```

确认数据库没有 Token 或查询原文：

```bash
sqlite3 control/mcp_export_audit.sqlite \
  "SELECT record_json FROM mcp_export_calls LIMIT 1;"
```

`record_json` 只应包含 Hash 和调用 metadata。不要通过 `strings`、`grep` 或日志命令把真实 Token 放进搜索参数。

---

## 四十、必须执行的故障注入

### 40.1 缺少 Token

临时设置一个不存在的 Secret 名称：

```bash
export MCP_EXPORT_TOKEN_SECRET_NAME=NON_EXISTENT_PHASE54_TOKEN
python -m app.main mcp-export-doctor
```

预期：

```text
ready=false
mcp_export_token_missing
```

恢复环境变量后再继续。

### 40.2 错误 Token

使用第 37 节 Client，但输入错误 Token。预期 HTTP 401，服务端不能把 Token 内容写入日志。

### 40.3 非法 Job ID

```python
await client.call_tool(
    "get_reproduction_status",
    {"job_id": "../../etc/passwd"},
)
```

预期在 MCP input schema 或领域 validator 被拒绝，不进入 JobStore。

### 40.4 不存在的合法形状 Job ID

```python
await client.call_tool(
    "get_reproduction_status",
    {"job_id": "job_" + "f" * 32},
)
```

预期稳定错误：

```text
MCP_EXPORT_JOB_NOT_FOUND
```

不能返回 SQL、数据库路径或 traceback。

### 40.5 Final Report 缺失

选择一个尚未产出 `final_report.md` 的 Job 调用 `read_reproduction_final_report`。预期：

```text
MCP_EXPORT_FINAL_REPORT_NOT_FOUND
```

Status 和 Evidence Tool 仍可用。

### 40.6 Artifact 完整性漂移

不要修改真实 Artifact。使用 `tests/mcp_export_helpers.py` 的 Fake Delivery，让 preview 抛出
`ArtifactIntegrityError`，断言：

```text
公开错误 = MCP_EXPORT_INTEGRITY_ERROR
Audit status = failed
无原始路径泄漏
```

### 40.7 Rate Limit

测试配置设为每分钟 2 次，连续调用三次。第三次应返回：

```text
MCP_EXPORT_RATE_LIMITED
```

并产生失败 Audit。不要在真实长期运行环境把限制设得过低后忘记恢复。

### 40.8 Phase 53 Server Down

保持 `MCP_GATEWAY_ENABLED=false` 或停止外部 MCP Server，再调用 Phase 54 Evidence Tool。它仍应成功，因为
Phase 54 Factory 没有构造 Phase 53 Gateway。

### 40.9 Research Provider Down

关闭 Research Browser 或移除 Search Provider 凭证，再调用 Phase 54 Evidence Tool。它只能读取现有本地
Evidence，不应发起网络请求。

### 40.10 Audit DB 不可写

只在测试临时目录中将 Audit 路径指向不可写位置。预期调用失败，不能在 Audit 失败后仍返回成功结果。不要
修改项目真实 `control/` 权限做这个测试。

---

## 四十一、常见问题与排查

### 41.1 `ModuleNotFoundError: No module named 'mcp'`

原因：当前环境没有安装 Phase 53/54 optional extra。

```bash
python -m pip install -e '.[mcp]'
```

同时确认 `python --version` 为 3.10+。

### 41.2 `421 Misdirected Request`

原因通常是 SDK DNS rebinding Host allowlist 与 Client URL 不一致。

先确认 Client 使用：

```text
http://127.0.0.1:8770/mcp
```

不要先关闭安全检查。只有确认 SDK 默认规则确实不接受该 Host 后，才按第 20.2 节增加精确
`127.0.0.1:8770` allowlist。

### 41.3 `401 Unauthorized`

按顺序检查：

1. Secret 名称与 `MCP_EXPORT_TOKEN_SECRET_NAME` 是否一致；
2. Secret use 是否为 `mcp_export_auth`；
3. Client Header 是否是一个且只有一个 `Authorization: Bearer ...`；
4. 是否错误复用了 API Token 或 Phase 53 Server Token；
5. Token 输入是否带了首尾换行。

不要打印 Token 排查。使用 `list-secrets` 查看 metadata 和版本。

### 41.4 Tool Schema 中出现 `ctx`

说明 SDK 没有识别 Context 注入。确认：

```python
from mcp.server.mcpserver import Context
```

并把 `ctx: Context` 放在有默认值参数之前，不要使用 `Any` 或自定义同名 Context。

### 41.5 `streamable_http_client() got an unexpected keyword argument 'headers'`

这是 SDK 2.x Client API。Header 应放进 `httpx2.AsyncClient`，然后通过 `http_client=` 传给 Transport。

### 41.6 首次请求提示 session manager 未初始化

如果按本教程独立运行 `server.streamable_http_app()`，SDK 自带 lifespan 会初始化 manager。这个错误通常说明
你后来把 MCP app Mount 到 FastAPI，却没有在顶层 lifespan 中执行：

```python
async with mcp.session_manager.run():
    yield
```

第一版不要 Mount，恢复独立进程即可。

### 41.7 Final Report 明明存在却找不到

检查 Artifact Catalog 中：

```text
basename 是否为 final_report.md
media_type 是否为 text/markdown 或 text/plain
preview_supported 是否为 true
Artifact 是否属于当前 run_id
Hash/size 是否仍匹配
```

不要为解决这个问题增加任意 `path` 参数。

### 41.8 Evidence 结果为空

可能是 Job 尚未产生 Event/Artifact/Log，或 query 与内容没有匹配。空 `items` 可以是合法成功结果；它不应
触发联网搜索，也不应由模型编造 Evidence。

---

## 四十二、安全复核

### 42.1 公开面复核

```bash
rg -n "@mcp\.tool|@mcp\.resource" app/mcp_export
```

人工确认只有四个 Tool、两个 Resource。

### 42.2 Import Boundary 复核

```bash
rg -n "app\.(execution|repair|research_browser|mcp_gateway|resources\.worker|nodes\.executor)" \
  app/mcp_export
```

预期没有结果。

### 42.3 路径泄漏复核

```bash
rg -n "relative_path|absolute_path|object_key|run_dir|workspace_root" \
  app/mcp_export/schemas.py \
  app/mcp_export/server.py
```

公开 Schema 和 Server handler 中不应包含这些字段。`service.py` 内部可以读取 `relative_path` 来选择
final report 和生成 basename，但不能返回它。

### 42.4 Secret 复核

```bash
rg -n "Authorization|Bearer|token" \
  app/mcp_export \
  tests/test_mcp_export_*.py
```

逐项确认只存在鉴权逻辑、测试常量和 Secret 逻辑名称，没有真实 Token。

### 42.5 Tool Schema 快照

使用 In-memory Client 将 `tools/list` 的 input/output schema 规范化并保存为 Golden Fixture，例如：

```text
tests/fixtures/mcp_export_tools_phase54_v1.json
```

后续 Schema 变化必须经过显式审查，不能只因为测试更新而覆盖 Fixture。

---

## 四十三、灰度启用顺序

严格按下面顺序：

```text
1. MCP_EXPORT_ENABLED=false 下运行普通全量回归
2. 安装 [mcp] extra，运行 In-memory Client 测试
3. 创建独立 Secret，运行 mcp-export-doctor
4. 启动 loopback Server，只测试 health 和 401
5. 使用 Fake/测试 Job 调用四个 Tool
6. 使用一个真实终态 Job 调用 Status/Artifacts
7. 验证 Final Report 和 Evidence Hash
8. 检查 Audit 不含内容和 Token
9. 连接一个真实可信 MCP Host
10. 保持主 API/Worker 回归通过后再长期启用
```

不要在同一天同时：

```text
开放非 loopback 地址
增加 OAuth
增加 Mutation Tool
增加任意 Artifact Resource
增加多用户 Scope
```

每次只改变一个信任边界。

---

## 四十四、回滚

### 44.1 最小回滚

```bash
export MCP_EXPORT_ENABLED=false
```

停止 `serve-mcp-export` 进程。主 API、Graph、Worker、Phase 52 Tool Calling 和 Phase 53 MCP Gateway 不受影响。

### 44.2 撤销 Token

先查看当前版本：

```bash
python -m app.main list-secrets
```

再撤销：

```bash
python -m app.main revoke-secret \
  PAPER_COPILOT_MCP_EXPORT_TOKEN \
  --version <当前版本>
```

Token 撤销后旧 MCP Host 必须无法连接。

### 44.3 保留历史 Audit

普通回滚不要删除 `control/mcp_export_audit.sqlite`。它只含 Hash 和 metadata，可以用于确认回滚前发生过哪些
读取。只有 Job Retention 或明确的数据删除流程才能按 Job 清理。

### 44.4 完整代码回滚顺序

如果必须撤回 Phase 54 代码：

```text
1. 关闭 Feature Flag
2. 停止 MCP Export 进程
3. 从所有 MCP Host 删除连接配置
4. 撤销 MCP Export Token
5. 保留或归档 Audit
6. 移除 CLI 命令
7. 移除 Retention 接线
8. 移除 app/mcp_export 和对应测试
9. 保留 Phase 53 MCP Client Gateway
```

不要反向删除 Phase 53，因为两个方向是独立能力。

---

## 四十五、本阶段涉及的 Agent 知识点

### 45.1 Tool Calling 与 Tool Serving 是两件事

```text
Tool Calling：模型建议调用什么。
Tool Serving：应用以协议形式提供什么。
```

Phase 54 只提供工具，不赋予外部模型本项目内部 Authority。

### 45.2 协议发现不是授权

`tools/list` 只是公开协议面。一个工具能被列出，不代表它可以绕过本项目的 Job Scope、Capability 和公开投影。

### 45.3 Capability Confinement

Export Runtime 从构造时就没有 Executor、Browser 和 MCP Client 依赖。这比在 handler 中写一个
`if read_only` 更可靠，因为越权能力根本不在对象图中。

### 45.4 Public Projection

内部模型适合业务运行，公开模型适合跨边界传输。显式 allowlist projection 可以防止内部 Schema 新增字段后
自动泄漏。

### 45.5 Structured Output

Pydantic 返回类型同时定义代码对象、MCP output schema 和运行时验证。结构化并不等于可信，仍需要 Job/Artifact
Hash 和本地身份验证。

### 45.6 Evidence Grounding

外部 Agent 获得的是 Citation-bound excerpt，而不是“本项目告诉它结论”。它可以根据 Artifact/Event Hash
判断来源，并在证据不足时明确降级。

### 45.7 Stateless Protocol 与显式业务状态

MCP 2026 协议不要求把业务状态隐藏在连接 Session 中。Job ID、Artifact ID 和 Snapshot Hash 都是显式身份，
因此请求可以独立审计和重放验证。

### 45.8 Confused Deputy 防护

MCP Export Token 只授权读取本项目的固定公开面，不能被转发给主 API、Provider 或外部 MCP Server。否则当前
Server 会成为替 Client 使用更高权限凭证的代理。

### 45.9 安全降级

Audit 不可写、Artifact Hash 漂移或依赖不可用时，系统拒绝返回结果，而不是绕过校验给出“尽可能多”的数据。

---

## 四十六、完成检查清单

### 46.1 功能

- [ ] `MCP_EXPORT_ENABLED=false` 时普通 API/CLI 不导入 MCP SDK；
- [ ] 独立 Secret Use `mcp_export_auth` 可用；
- [ ] Doctor 能检查 Token 和 Audit；
- [ ] 服务只监听 `127.0.0.1`；
- [ ] `/healthz` 不包含私有状态；
- [ ] `/mcp` 未授权时返回 401；
- [ ] `tools/list` 恰好包含四个 Tool；
- [ ] `resources/templates/list` 恰好包含两个模板；
- [ ] 四个 Tool 返回 structured content；
- [ ] Status 与真实 Job 公开状态一致；
- [ ] Artifact Page 不包含路径；
- [ ] Final Report 由服务端选择并校验 Hash；
- [ ] Evidence 只有本地四类来源；
- [ ] Final Report 与 Evidence 文本在返回前经过现有 `SecretRedactor`；
- [ ] Audit 只保存 Hash 和 metadata；
- [ ] Rate Limit 生效；
- [ ] Retention 能删除指定 Job 的 Export Audit。

### 46.2 安全

- [ ] 不导出 Mutation Tool；
- [ ] 不导出任意文件读取；
- [ ] 不导出 Job 枚举；
- [ ] 不 import Executor、Repair、Resource Worker；
- [ ] 不构造 Research Browser；
- [ ] 不构造 Phase 53 MCP Client；
- [ ] 不把 Token 传进 MCP Context；
- [ ] 不向 Client 返回 Secret 原文、绝对路径或对象存储 Key；
- [ ] 不记录 Token、Header、query 或原始输出；
- [ ] 不信任 MCP Annotation 作为授权；
- [ ] 不允许 wildcard Host；
- [ ] 不允许 CORS wildcard；
- [ ] 不监听非 loopback 地址；
- [ ] 不实现自制远程 OAuth。

### 46.3 测试

- [ ] Schema/Identity 测试通过；
- [ ] Audit/Rate Limit 测试通过；
- [ ] Service 投影测试通过；
- [ ] In-memory MCP Client 测试通过；
- [ ] ASGI Auth 测试通过；
- [ ] Authority Import Boundary 通过；
- [ ] Retention 集成测试通过；
- [ ] Phase 52/53 回归通过；
- [ ] Secret/Artifact 回归通过；
- [ ] 全量测试通过；
- [ ] 真实 loopback Client 手工验收通过；
- [ ] 故障注入通过。

### 46.4 文档

- [ ] `.env.example` 已更新且配置块之间有换行；
- [ ] `.gitignore` 已登记 SQLite/WAL/SHM；
- [ ] `README.md` 已登记 Phase 54；
- [ ] `project_phase_capability_summary.md` 已更新真实实现状态；
- [ ] `agent_project_analysis_and_technical_roadmap.md` 已更新；
- [ ] 实现完成后更新 `python_source_code_reference*.md`；
- [ ] 记录真实 MCP SDK 版本和 Tool Schema Golden Hash。

---

## 四十七、阶段结论与下一步

Phase 54 完成后，项目会形成双向但仍然只读的 MCP 互操作：

```text
外部 Evidence MCP Server
  -> Phase 53 MCP Client Gateway
  -> 本地 Evidence/Citation

本地 Job/Artifact/Evidence
  -> Phase 54 MCP Server Export
  -> 其他可信 MCP Host
```

双向不代表权限对称：Phase 53 的外部 Server 不能控制本项目，Phase 54 的外部 Client 也不能控制复现流程。
Human Review、Decision、Executor、Patch 和 Resource Approval 仍只存在于现有主系统。

下一阶段不建议立刻增加 MCP Mutation。更值得优先做 **Phase 55：MCP 互操作契约评测、Client Profile 与
单机运行收口**，内容可以保持轻量：

```text
固定 Tool/Resource Schema Golden
验证至少两个 MCP Client 的兼容性
生成不含 Token 的 Client 配置模板
统一 MCP Client/Gateway/Export readiness
增加启动、停止、备份和恢复 Runbook
把 Phase 53/54 纳入一键单机验收
```

完成这个收口后，再根据真实需求决定是否需要标准 OAuth、远程部署或受审批 Mutation。没有明确使用场景时，
不要为了“协议完整”开放写能力。
