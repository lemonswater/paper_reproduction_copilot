# 40. Phase 29：受控资源获取、不可变输入清单与供应链安全

Phase 28 让异步运行链可观察、可诊断。本阶段解决另一个关键缺口：论文 PDF、代码仓库、模型
checkpoint 等输入不应依赖“用户已经手工放到某个本地路径”，也不能让论文执行代码在运行时
自由联网下载。

目标链路：

```text
用户或受信任配置提出 ResourceRequest
    -> 确定性 URL / source policy
    -> request hash + 人工批准
    -> 独立 Acquisition Worker 获取
    -> streaming size/time/content validation
    -> SHA-256 / Git commit / type validation
    -> immutable Blob publication
    -> ResourceManifest
    -> Job submission 引用 resource_id
    -> Workspace 物化为只读输入
    -> OCI execution 继续 --network=none
```

> **本教程中的源码均为待实现代码。**
>
> 本阶段暂不考虑多用户，所以 schema 中没有 `owner_id`、tenant、RBAC 或用户级配额。但仍然
> 保留 request hash、审批、lease、审计 event 和资源预算，因为单用户 Agent 也会面对错误 URL、
> SSRF、超大文件、mutable repository 和断点恢复问题。

---

## 一、为什么资源获取必须与论文执行分离

> **本节类型：原理说明，不修改项目代码。**

如果直接允许训练脚本执行：

```text
requests.get(llm_generated_url)
git clone arbitrary_url
torch.hub.load(...)
pip install ...
```

系统就无法可靠回答：

```text
访问了哪个地址，是否发生重定向？
有没有访问 127.0.0.1、云 metadata 或内网服务？
实际下载内容是否和审批时一致？
下载是否超过磁盘/时间预算？
Git 仓库最终是哪一个 commit？
checkpoint 是否被替换？
失败重试会不会重复下载或产生半文件？
结果能否追溯到同一份输入？
```

因此网络权限只属于独立 Acquisition Worker；Graph/LLM 可以提出候选资源，最终执行容器仍然
保持 `network=none`。

---

## 二、本阶段完成定义

> **本节类型：目标说明，不修改项目代码。**

第一版支持三类资源：

```text
paper_pdf       HTTPS PDF
git_repository HTTPS Git repository + exact commit SHA
checkpoint      HTTPS opaque file + required expected SHA-256
```

完成后必须满足：

1. LLM 不能直接触发下载，只能生成待确认 proposal；
2. 所有远程获取先形成规范化 `ResourceRequest` 和 request hash；
3. 第一版所有联网请求都要明确批准，批准绑定 request hash；
4. URL 只允许 HTTPS、显式 host allowlist、无 userinfo、无 fragment；
5. 禁止 localhost、private、loopback、link-local、multicast、reserved 和 unspecified IP；
6. HTTP redirect 每一跳都重新校验，默认最多 5 跳；
7. 下载使用 streaming、连接/读取/总时长和字节上限；
8. `.part` 文件只写入项目配置的 staging root，验证成功后才原子发布；
9. checkpoint 必须在下载前提供 expected SHA-256，获取阶段绝不 `torch.load`；
10. Git 必须锁定 exact commit，禁止 submodule、Git LFS、file/ext/ssh protocol；
11. Artifact/Object Storage 使用内容地址，`sha256` 是最终身份，ETag 不能替代 hash；
12. Resource 状态机有 lease、heartbeat、retry、cancel 和 crash recovery；
13. Job 只能引用 `verified/published` Resource；
14. Workspace 将 Resource 作为只读输入物化；
15. 执行容器保持断网，不能因“缺资源”临时开放网络；
16. tests 不访问真实互联网，使用 Fake Transport/Fake Git；
17. telemetry 不记录 URL query、Authorization、凭据或原始下载内容。

---

## 三、安全边界与诚实限制

> **本节类型：安全说明，不修改项目代码。**

应用层 DNS/IP 检查很重要，但**不能单独彻底解决 DNS rebinding/TOCTOU**：代码检查域名解析结果
后，HTTP/Git 客户端可能再次解析。如果 DNS 在两次解析之间改变，连接目标可能不同。

因此生产级边界应是两层：

```text
应用层：scheme/host/port/DNS/redirect/size/hash/type policy
网络层：专用 Acquisition Worker + egress proxy/firewall，阻断内网和 metadata ranges
```

OWASP 同样建议限制重定向，并对域名的全部 A/AAAA 地址做校验，同时警惕 DNS pinning：
[SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)。

本地学习环境可以先完成应用层和独立 Worker；如果没有 egress proxy/firewall，文档和 readiness
必须把状态报告为 `degraded_application_guard_only`，不能声称“完全防 SSRF”。

---

## 四、本阶段明确不做

> **本节类型：范围说明，不修改项目代码。**

```text
不做通用浏览器、网页抓取器或搜索引擎
不让 LLM 自行批准资源
不支持 ftp/file/ssh/git/ext 等协议
不下载需要登录、Cookie、Authorization 或任何 URL query 参数的资源
不自动接受许可证或绕过数据集访问条款
不自动下载大型训练数据集
不在获取阶段 import/execute 下载到的 Python 代码
不在获取阶段 torch.load/pickle.load checkpoint
不自动安装 requirements.txt、wheel、conda 包或系统包
不启用 Git submodule、Git LFS 或 repository hooks
不信任 Content-Type、Content-Length、ETag 或文件名作为内容身份
不把获取失败自动交给 LLM 改 URL 后重试
不做多用户资源所有权与配额
```

大型数据集第一版继续使用 Phase 26 的 `ExternalDataReference + required_worker_label`，由维护者
按许可证准备，不纳入自动下载。

---

## 五、状态机

> **本节类型：设计说明，不修改项目代码。**

```text
ResourceRequest（尚未持久化）
    -> awaiting_approval
    -- approve + matching request hash --> queued
    -> fetching
    -> validating
    -> published

任意未终态
    -> cancelled
    -> rejected
    -> failed_retryable -> queued
    -> failed_terminal
    -> reconciliation_required
```

关键规则：

```text
批准 hash 与当前 request hash 不一致 -> stale_approval
fetching lease 过期且没有可证明终止的下载进程 -> reconciliation_required
part 文件存在但没有 verified record -> 不发布，先清理或重新校验
同一 expected hash 已存在 -> 校验 metadata 后复用，不重复下载
下载成功但 DB 未提交 -> 根据 part/blob hash 恢复 publication，不重新请求网络
```

---

## 六、文件清单

> **本节类型：实施清单。**

需要新增：

```text
app/resources/__init__.py
app/resources/schemas.py
app/resources/errors.py
app/resources/policy.py
app/resources/ports.py
app/resources/request_hash.py
app/resources/http_downloader.py
app/resources/validators.py
app/resources/git_fetcher.py
app/resources/publisher.py
app/resources/repository.py
app/resources/postgres_repository.py
app/resources/service.py
app/resources/worker.py
app/resources/reconcile.py
app/resources/materializer.py
app/api/resource_routes.py
migrations/versions/<revision>_add_resources.py
tests/fakes/fake_resource_transport.py
tests/fakes/fake_resource_repository.py
tests/test_resource_schemas.py
tests/test_resource_policy.py
tests/test_resource_request_hash.py
tests/test_http_resource_downloader.py
tests/test_resource_validators.py
tests/test_git_resource_fetcher.py
tests/test_resource_worker.py
tests/test_resource_reconcile.py
tests/test_resource_job_submission.py
tests/test_resource_api.py
```

需要修改：

```text
pyproject.toml
app/config.py
app/api/app.py
app/interaction/schemas.py
app/interaction/service.py
app/job_runtime/schemas.py
app/job_runtime/service.py
app/workspace/snapshot.py
app/workspace/materializer.py
app/main.py
```

---

## 七、依赖与配置

> **本节类型：需要修改项目代码。**
>
> 修改：`pyproject.toml`、`app/config.py`、`.env.example`。

增加可选依赖：

```toml
[project.optional-dependencies]
# 保留其他已有分组。
resources = [
    "httpx>=0.27,<1",
]
```

配置全部显式：

```python
@dataclass
class Settings:
    # ...保留已有字段...

    resource_staging_root: Path = Path(
        os.getenv("RESOURCE_STAGING_ROOT", "resources/.staging")
    )
    resource_materialized_root: Path = Path(
        os.getenv("RESOURCE_MATERIALIZED_ROOT", "resources/materialized")
    )
    resource_allowed_hosts: tuple[str, ...] = tuple(
        item.strip().lower()
        for item in os.getenv(
            "RESOURCE_ALLOWED_HOSTS",
            "arxiv.org,export.arxiv.org,github.com,codeload.github.com",
        ).split(",")
        if item.strip()
    )
    resource_max_redirects: int = int(
        os.getenv("RESOURCE_MAX_REDIRECTS", "5")
    )
    resource_connect_timeout_seconds: float = float(
        os.getenv("RESOURCE_CONNECT_TIMEOUT_SECONDS", "10")
    )
    resource_read_timeout_seconds: float = float(
        os.getenv("RESOURCE_READ_TIMEOUT_SECONDS", "30")
    )
    resource_total_timeout_seconds: float = float(
        os.getenv("RESOURCE_TOTAL_TIMEOUT_SECONDS", "300")
    )
    resource_pdf_max_bytes: int = int(
        os.getenv("RESOURCE_PDF_MAX_BYTES", str(100 * 1024 * 1024))
    )
    resource_checkpoint_max_bytes: int = int(
        os.getenv("RESOURCE_CHECKPOINT_MAX_BYTES", str(20 * 1024 * 1024 * 1024))
    )
    resource_git_timeout_seconds: float = float(
        os.getenv("RESOURCE_GIT_TIMEOUT_SECONDS", "600")
    )
    resource_lease_seconds: float = float(
        os.getenv("RESOURCE_LEASE_SECONDS", "120")
    )
    resource_heartbeat_seconds: float = float(
        os.getenv("RESOURCE_HEARTBEAT_SECONDS", "30")
    )
    resource_require_network_guard: bool = _env_bool(
        "RESOURCE_REQUIRE_NETWORK_GUARD", False
    )
    resource_network_guard_configured: bool = _env_bool(
        "RESOURCE_NETWORK_GUARD_CONFIGURED", False
    )
```

`.env.example`：

```dotenv
RESOURCE_STAGING_ROOT=resources/.staging
RESOURCE_MATERIALIZED_ROOT=resources/materialized
RESOURCE_ALLOWED_HOSTS=arxiv.org,export.arxiv.org,github.com,codeload.github.com
RESOURCE_MAX_REDIRECTS=5
RESOURCE_CONNECT_TIMEOUT_SECONDS=10
RESOURCE_READ_TIMEOUT_SECONDS=30
RESOURCE_TOTAL_TIMEOUT_SECONDS=300
RESOURCE_PDF_MAX_BYTES=104857600
RESOURCE_CHECKPOINT_MAX_BYTES=21474836480
RESOURCE_GIT_TIMEOUT_SECONDS=600
RESOURCE_LEASE_SECONDS=120
RESOURCE_HEARTBEAT_SECONDS=30
RESOURCE_REQUIRE_NETWORK_GUARD=false
RESOURCE_NETWORK_GUARD_CONFIGURED=false
```

所有 root 在应用启动时 `resolve()` 后必须位于 `settings.allowed_root`。按当前项目约束，实际路径
都应位于 `/data/tianshaoqi24/` 下，不使用系统 `/tmp`。

---

## 八、定义 Resource schemas

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/schemas.py`。

```python
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")

ResourceKind = Literal["paper_pdf", "git_repository", "checkpoint"]
ResourceStatus = Literal[
    "awaiting_approval",
    "queued",
    "fetching",
    "validating",
    "published",
    "rejected",
    "cancelled",
    "failed_retryable",
    "failed_terminal",
    "reconciliation_required",
]


class ResourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceRequest(ResourceModel):
    kind: ResourceKind
    source_url: str = Field(min_length=1, max_length=2048)
    expected_sha256: str | None = None
    expected_git_commit: str | None = None
    purpose: str = Field(min_length=1, max_length=500)

    @field_validator("expected_sha256")
    @classmethod
    def validate_sha(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if not SHA256_RE.fullmatch(lowered):
            raise ValueError("expected_sha256 必须是 64 位小写十六进制")
        return lowered

    @field_validator("expected_git_commit")
    @classmethod
    def validate_commit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if not COMMIT_RE.fullmatch(lowered):
            raise ValueError("expected_git_commit 必须是完整 commit SHA")
        return lowered

    @model_validator(mode="after")
    def validate_identity_requirement(self) -> "ResourceRequest":
        if self.kind == "git_repository":
            if self.expected_git_commit is None:
                raise ValueError("Git resource 必须指定 exact commit")
            if self.expected_sha256 is not None:
                raise ValueError("Git request 不使用下载文件 expected_sha256")
        elif self.kind == "checkpoint":
            if self.expected_sha256 is None:
                raise ValueError("Checkpoint 必须在下载前指定 expected_sha256")
            if self.expected_git_commit is not None:
                raise ValueError("非 Git resource 不能指定 expected_git_commit")
        else:
            if self.expected_git_commit is not None:
                raise ValueError("PDF 不能指定 expected_git_commit")
        return self


class ResourceApproval(ResourceModel):
    decision: Literal["approved", "rejected"]
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decided_by: str = Field(min_length=1, max_length=200)
    decided_at: str
    reason: str | None = Field(default=None, max_length=500)


class ResourceManifest(ResourceModel):
    manifest_version: Literal["phase29-v1"] = "phase29-v1"
    # 计算时排除本字段自身；Job 用它冻结完整 Resource metadata snapshot。
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    resource_id: str
    kind: ResourceKind
    source_url_sanitized: str
    redirect_chain_sanitized: list[str] = Field(default_factory=list)
    object_key: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: str
    git_commit: str | None = None
    acquired_at: str


class ResourceRecord(ResourceModel):
    resource_id: str
    idempotency_key: str
    request: ResourceRequest
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval: ResourceApproval | None = None
    status: ResourceStatus
    version: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    worker_id: str | None = None
    claim_token: str | None = None
    heartbeat_at: str | None = None
    lease_expires_at: str | None = None
    manifest: ResourceManifest | None = None
    error: dict | None = None
    created_at: str
    updated_at: str
```

PDF 的 expected hash 可以为空，因为用户可能只知道论文 URL；下载成功后仍以实际 SHA-256 发布。
Checkpoint 执行时可能触发不安全反序列化，因此必须预先给出 trusted expected hash。

---

## 九、规范化 URL 与 request hash

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/request_hash.py`。

```python
from __future__ import annotations

import hashlib
import json
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from app.resources.schemas import ResourceRequest


def canonicalize_url(raw: str) -> str:
    parsed = urlsplit(raw.strip())
    if parsed.scheme.lower() != "https":
        raise ValueError("Resource URL 第一版只允许 HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Resource URL 禁止 userinfo")
    if parsed.fragment:
        raise ValueError("Resource URL 禁止 fragment")
    if parsed.query:
        # 第一版不接受 query，避免误把 presigned token/凭据持久化或写入日志。
        raise ValueError("Resource URL 第一版禁止 query 参数")
    if not parsed.hostname:
        raise ValueError("Resource URL 缺少 host")

    host = parsed.hostname.encode("idna").decode("ascii").lower()
    port = parsed.port
    if port not in {None, 443}:
        raise ValueError("Resource URL 只允许 HTTPS 默认端口 443")
    netloc = host

    # 第一版 query 已被拒绝，只需稳定编码 path。
    path = quote(unquote(parsed.path or "/"), safe="/%:@")
    return urlunsplit(("https", netloc, path, "", ""))


def resource_request_sha256(request: ResourceRequest) -> str:
    payload = request.model_copy(
        update={"source_url": canonicalize_url(request.source_url)}
    ).model_dump(mode="json")
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

审批必须绑定此 hash。审批后如果用户把 URL、commit、expected hash 或 purpose 中任何一个字段改了，
旧审批自动失效。

---

## 十、确定性 URL/DNS policy

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/policy.py`。

```python
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.resources.errors import ResourcePolicyViolation
from app.resources.request_hash import canonicalize_url


@dataclass(frozen=True)
class ValidatedDestination:
    canonical_url: str
    host: str
    resolved_ips: tuple[str, ...]


def host_allowed(host: str, allowed_hosts: tuple[str, ...]) -> bool:
    # 精确 host 或明确子域；endswith("github.com") 会错误接受 evilgithub.com。
    return any(host == item or host.endswith(f".{item}") for item in allowed_hosts)


def resolve_public_ips(host: str) -> tuple[str, ...]:
    addresses = {
        row[4][0]
        for row in socket.getaddrinfo(
            host,
            443,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    }
    if not addresses:
        raise ResourcePolicyViolation("host 没有可用 A/AAAA address")
    for raw in addresses:
        address = ipaddress.ip_address(raw)
        # is_global=false 会覆盖 private/loopback/link-local/multicast/reserved/unspecified。
        if not address.is_global:
            raise ResourcePolicyViolation(f"Resource host 解析到非公网地址：{address}")
    return tuple(sorted(addresses))


def validate_destination(
    raw_url: str,
    *,
    allowed_hosts: tuple[str, ...],
    resolver=resolve_public_ips,
) -> ValidatedDestination:
    canonical = canonicalize_url(raw_url)
    host = (urlsplit(canonical).hostname or "").lower()
    if not host_allowed(host, allowed_hosts):
        raise ResourcePolicyViolation(f"Resource host 不在 allowlist：{host}")
    return ValidatedDestination(
        canonical_url=canonical,
        host=host,
        resolved_ips=resolver(host),
    )
```

不要加入“测试方便”的 localhost 例外。单元测试注入 fake resolver/transport；真实 integration 若
需要本地 HTTP server，应启动专用测试配置和隔离网络，而不是放宽生产函数。

---

## 十一、错误类型

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/errors.py`。

```python
class ResourceError(RuntimeError):
    pass


class ResourcePolicyViolation(ResourceError):
    """URL、DNS、redirect、协议或审批违反确定性策略；terminal。"""


class ResourceIntegrityError(ResourceError):
    """hash、commit、magic bytes 或内容结构不匹配；terminal。"""


class ResourceLimitExceeded(ResourceError):
    """字节数、文件数、时间或 redirect 超限；terminal。"""


class ResourceTransportUnavailable(ResourceError):
    """DNS、连接、服务端 5xx 等瞬时失败；可按策略 retry。"""


class ResourceLeaseLost(ResourceError):
    """旧 Worker 失去 ownership，必须停止写入和发布。"""


class ResourceStateAmbiguous(ResourceError):
    """不能证明旧获取进程已停止；必须 reconcile，不能直接重试。"""
```

错误分类应复用 Phase 15 的统一错误模型，Resource 只是增加 stage/category，不要建立互不相容
的第二套错误报告。

---

## 十二、ResourceRepository 端口

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/ports.py`。

```python
from __future__ import annotations

from typing import Protocol

from app.resources.schemas import (
    ResourceApproval,
    ResourceManifest,
    ResourceRecord,
    ResourceRequest,
)


class ResourceRepository(Protocol):
    def initialize(self) -> None:
        ...

    def ping(self) -> None:
        ...

    def submit(
        self,
        *,
        resource_id: str,
        idempotency_key: str,
        request: ResourceRequest,
        request_sha256: str,
    ) -> tuple[ResourceRecord, bool]:
        ...

    def get(self, resource_id: str) -> ResourceRecord:
        ...

    def approve(
        self,
        *,
        resource_id: str,
        approval: ResourceApproval,
        expected_version: int | None,
    ) -> ResourceRecord:
        ...

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: float,
    ) -> ResourceRecord | None:
        ...

    def heartbeat(
        self,
        *,
        resource_id: str,
        claim_token: str,
        lease_seconds: float,
    ) -> ResourceRecord:
        ...

    def mark_validating(self, *, resource_id: str, claim_token: str) -> ResourceRecord:
        ...

    def mark_published(
        self,
        *,
        resource_id: str,
        claim_token: str,
        manifest: ResourceManifest,
    ) -> ResourceRecord:
        ...

    def mark_failed(
        self,
        *,
        resource_id: str,
        claim_token: str,
        error: dict,
        retryable: bool,
    ) -> ResourceRecord:
        ...

    def request_cancel(
        self,
        *,
        resource_id: str,
        reason: str,
        actor: str,
        expected_version: int | None,
    ) -> ResourceRecord:
        ...

    def list_expired_fetching(self, *, limit: int = 100) -> list[ResourceRecord]:
        ...

    def requeue_expired(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        ...

    def require_reconciliation(
        self,
        *,
        resource_id: str,
        expired_claim_token: str,
        detail: str,
    ) -> ResourceRecord:
        ...
```

所有状态更新都必须使用 `WHERE resource_id=? AND claim_token=? AND status IN (...)` 的 fencing
条件。旧 Worker 即使稍后完成下载，也不能发布新 claim 的资源。

---

## 十三、数据库表与 migration

> **本节类型：需要新增项目代码。**
>
> 新增：migration、`app/resources/postgres_repository.py`。

建议表字段：

```text
resources
  resource_id              text primary key
  idempotency_key          text unique not null
  request_sha256           char(64) not null
  request_json             jsonb not null
  approval_json            jsonb null
  status                   text not null
  version                  integer not null
  attempt_count            integer not null
  worker_id                text null
  claim_token              text null
  heartbeat_at             timestamptz null
  lease_expires_at         timestamptz null
  manifest_json            jsonb null
  error_json               jsonb null
  available_at             timestamptz not null
  created_at               timestamptz not null
  updated_at               timestamptz not null

resource_events
  event_id                 bigserial primary key
  resource_id              text not null references resources(resource_id)
  event_type               text not null
  actor                    text not null
  payload_json             jsonb not null
  created_at               timestamptz not null
```

索引：

```sql
CREATE INDEX ix_resources_claim
ON resources (status, available_at, created_at);

CREATE INDEX ix_resources_lease
ON resources (status, lease_expires_at);
```

不要在 event payload 里保存原始 URL query、claim token 或 HTTP headers。

SQLite adapter 可以用于单元测试和单进程开发，但若 Job control plane 已经选择 PostgreSQL，正式
Resource Worker 也应使用 PostgreSQL，避免两个不一致的 lease 时钟和持久化边界。

---

## 十四、HTTP transport 与手工 redirect

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/http_downloader.py`。

第一版使用 `httpx.Client(follow_redirects=False, trust_env=False)`：

```python
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx

from app.resources.errors import (
    ResourceIntegrityError,
    ResourceLimitExceeded,
    ResourceTransportUnavailable,
)
from app.resources.policy import validate_destination


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    sha256: str
    size_bytes: int
    media_type: str
    redirect_chain: tuple[str, ...]


class HttpResourceDownloader:
    def __init__(
        self,
        *,
        allowed_hosts: tuple[str, ...],
        max_redirects: int,
        connect_timeout: float,
        read_timeout: float,
        total_timeout: float,
        resolver=None,
        client: httpx.Client | None = None,
    ):
        self.allowed_hosts = allowed_hosts
        self.max_redirects = max_redirects
        self.total_timeout = total_timeout
        self.resolver = resolver
        self.client = client or httpx.Client(
            follow_redirects=False,
            trust_env=False,
            timeout=httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=read_timeout,
                pool=connect_timeout,
            ),
            headers={"User-Agent": "paper-reproduction-copilot-resource/1"},
        )

    def _validate(self, url: str):
        kwargs = {"allowed_hosts": self.allowed_hosts}
        if self.resolver is not None:
            kwargs["resolver"] = self.resolver
        return validate_destination(url, **kwargs)

    def download(
        self,
        *,
        url: str,
        destination: Path,
        max_bytes: int,
        expected_sha256: str | None,
        ensure_active=lambda: None,
    ) -> DownloadResult:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            raise ResourceIntegrityError("staging destination 已存在")

        current = url
        redirects: list[str] = []
        started = time.monotonic()
        digest = hashlib.sha256()
        size = 0

        try:
            for redirect_index in range(self.max_redirects + 1):
                ensure_active()
                target = self._validate(current)
                redirects.append(target.canonical_url)

                with self.client.stream("GET", target.canonical_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise ResourceTransportUnavailable("redirect 缺少 Location")
                        if redirect_index >= self.max_redirects:
                            raise ResourceLimitExceeded("redirect 次数超限")
                        # 下一轮会对新 URL 的 scheme/host/DNS 重新验证。
                        current = urljoin(target.canonical_url, location)
                        continue

                    if response.status_code >= 500:
                        raise ResourceTransportUnavailable(
                            f"resource server returned {response.status_code}"
                        )
                    if response.status_code != 200:
                        raise ResourceIntegrityError(
                            f"resource server returned {response.status_code}"
                        )

                    declared = response.headers.get("content-length")
                    if declared is not None and int(declared) > max_bytes:
                        raise ResourceLimitExceeded("Content-Length 超过预算")

                    # exclusive create，避免跟随既有 symlink 或覆盖旧 part。
                    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "wb") as handle:
                        for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                            ensure_active()
                            if time.monotonic() - started > self.total_timeout:
                                raise ResourceLimitExceeded("resource total timeout")
                            size += len(chunk)
                            if size > max_bytes:
                                raise ResourceLimitExceeded("resource bytes 超过预算")
                            digest.update(chunk)
                            handle.write(chunk)
                        handle.flush()
                        os.fsync(handle.fileno())

                    actual_sha = digest.hexdigest()
                    if expected_sha256 is not None and actual_sha != expected_sha256:
                        raise ResourceIntegrityError("resource SHA-256 与 expected 不一致")
                    media_type = response.headers.get(
                        "content-type", "application/octet-stream"
                    ).split(";", 1)[0].strip().lower()
                    return DownloadResult(
                        path=destination,
                        sha256=actual_sha,
                        size_bytes=size,
                        media_type=media_type,
                        redirect_chain=tuple(redirects),
                    )
            raise ResourceLimitExceeded("redirect loop")
        except Exception:
            destination.unlink(missing_ok=True)
            raise
```

重要限制：上面的 resolver 检查和 httpx 连接仍可能发生两次 DNS 解析。正式部署必须配合 egress
proxy/firewall；若未配置，readiness 返回 degraded，而不是假装强网络隔离。

---

## 十五、PDF 和 checkpoint 验证器

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/validators.py`。

```python
from __future__ import annotations

from pathlib import Path

import fitz

from app.resources.errors import ResourceIntegrityError


def validate_pdf(path: Path) -> str:
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise ResourceIntegrityError("paper_pdf magic bytes 不是 PDF")

    try:
        document = fitz.open(path)
        page_count = document.page_count
        document.close()
    except Exception as exc:  # noqa: BLE001
        raise ResourceIntegrityError("PDF parser 无法打开文件") from exc

    if page_count < 1:
        raise ResourceIntegrityError("PDF 没有页面")
    return "application/pdf"


def validate_checkpoint_opaque(path: Path) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        raise ResourceIntegrityError("checkpoint 为空或不存在")

    # 获取阶段绝不 torch.load/pickle.load。只做 opaque blob + hash 身份验证。
    return "application/octet-stream"
```

以后真正加载 checkpoint 时，应在 OCI 边界内、使用可信代码，并在 PyTorch 版本支持时优先
`weights_only=True`；这不属于获取阶段。

---

## 十六、受控 Git fetch

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/git_fetcher.py`。

Git 不能直接使用 HTTP downloader，因为它需要协议交互。但仍要使用同一 URL/DNS policy、专用
Acquisition Worker 和网络层 egress guard。

```python
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.resources.errors import ResourceIntegrityError, ResourceTransportUnavailable
from app.resources.policy import validate_destination
from app.workspace.repo_capsule import create_repository_capsule


@dataclass(frozen=True)
class GitFetchResult:
    repository_path: Path
    bundle_path: Path
    commit_sha: str
    bundle_sha256: str
    bundle_size_bytes: int


class GitResourceFetcher:
    def __init__(self, *, allowed_hosts: tuple[str, ...], timeout_seconds: float):
        self.allowed_hosts = allowed_hosts
        self.timeout_seconds = timeout_seconds

    def _env(self, isolated_home: Path) -> dict[str, str]:
        isolated_home.mkdir(parents=True, exist_ok=True)
        return {
            "PATH": os.environ.get("PATH", ""),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "HOME": str(isolated_home),
            "XDG_CONFIG_HOME": str(isolated_home / ".config"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "GIT_PROTOCOL_FROM_USER": "0",
        }

    def _run(self, cwd: Path, env: dict[str, str], *args: str) -> str:
        completed = subprocess.run(
            [
                "git",
                "-c", "protocol.file.allow=never",
                "-c", "protocol.ext.allow=never",
                "-c", "submodule.recurse=false",
                *args,
            ],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            shell=False,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:1000]
            raise ResourceTransportUnavailable(f"controlled git failed: {detail}")
        return completed.stdout.strip()

    def fetch(
        self,
        *,
        source_url: str,
        expected_commit: str,
        staging_dir: Path,
    ) -> GitFetchResult:
        validated = validate_destination(
            source_url,
            allowed_hosts=self.allowed_hosts,
        )
        repo = staging_dir / "repo"
        home = staging_dir / "home"
        bundle = staging_dir / "repository.bundle"
        repo.mkdir(parents=True, exist_ok=False)
        env = self._env(home)

        self._run(repo, env, "init", "--initial-branch", "acquired")
        self._run(repo, env, "remote", "add", "origin", validated.canonical_url)
        self._run(
            repo,
            env,
            "fetch",
            "--depth=1",
            "--no-tags",
            "--no-recurse-submodules",
            "origin",
            expected_commit,
        )
        self._run(repo, env, "checkout", "--detach", "FETCH_HEAD")
        actual_commit = self._run(repo, env, "rev-parse", "HEAD").lower()
        if actual_commit != expected_commit:
            raise ResourceIntegrityError("Git fetch 得到的 commit 与 expected 不一致")
        if (repo / ".gitmodules").exists():
            raise ResourceIntegrityError("第一版拒绝 Git submodule")
        attributes = repo / ".gitattributes"
        if attributes.is_file() and "filter=lfs" in attributes.read_text(
            encoding="utf-8", errors="replace"
        ):
            raise ResourceIntegrityError("第一版拒绝 Git LFS")

        # 现有 create_repository_capsule 要求命名 branch，创建本地确定性 branch。
        self._run(repo, env, "switch", "-c", f"acquired-{actual_commit[:12]}")
        capsule = create_repository_capsule(repo_path=repo, destination=bundle)
        return GitFetchResult(
            repository_path=repo,
            bundle_path=capsule.bundle_path,
            commit_sha=actual_commit,
            bundle_sha256=capsule.sha256,
            bundle_size_bytes=capsule.size_bytes,
        )
```

上面代码仍需根据当前 `create_repository_capsule()` 的 staging root 限制调整：`staging_dir` 必须
位于 `settings.workspace_staging_root` 或扩展该函数接受受控的 resource staging root。不要为了
通过校验删除路径边界。

Git 官方提供 `GIT_CONFIG_NOSYSTEM` 和禁止终端提示的配置，可用于隔离宿主机配置与交互凭据：
[Git documentation](https://git-scm.com/docs/git)。

---

## 十七、为什么第一版不自动解压任意 archive

> **本节类型：知识说明，不修改项目代码。**

压缩包不仅有 `../` 路径穿越，还可能包含：

```text
绝对路径
symlink / hardlink
device / FIFO
重复文件覆盖
超多小文件
超高压缩比
解压后总大小远大于下载大小
```

Python 官方也明确警告不能在未检查时解压不可信 archive，并建议限制成员数量、总大小和链接：
[tarfile extraction filters](https://docs.python.org/3/library/tarfile.html#extraction-filters)。

因此 Phase 29 第一版只把 checkpoint 当 opaque file，Git 使用 Git 自身协议并生成 bundle，PDF 用
PDF parser 验证。若以后增加 archive，必须单独实现 safe extractor，不能直接 `extractall()`。

---

## 十八、发布不可变 ResourceManifest

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/publisher.py`。

```python
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app.resources.request_hash import canonicalize_url
from app.resources.schemas import ResourceManifest
from app.storage.ports import BlobStore


def resource_object_key(sha256: str) -> str:
    return f"resources/sha256/{sha256[:2]}/{sha256}"


def resource_manifest_sha256(payload: dict) -> str:
    """payload 不包含 manifest_sha256，避免自引用 hash。"""
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ResourcePublisher:
    def __init__(self, blob_store: BlobStore):
        self.blob_store = blob_store

    def publish_file(
        self,
        *,
        resource_id: str,
        kind: str,
        source_url: str,
        redirect_chain: list[str],
        source: Path,
        sha256: str,
        size_bytes: int,
        media_type: str,
        git_commit: str | None = None,
    ) -> ResourceManifest:
        key = resource_object_key(sha256)
        stat = self.blob_store.put_file(
            object_key=key,
            source_path=source,
            expected_sha256=sha256,
            expected_size=size_bytes,
            media_type=media_type,
        )
        if stat.sha256 != sha256 or stat.size_bytes != size_bytes:
            raise ValueError("BlobStore publication identity mismatch")

        # canonicalize_url 会再次拒绝 credentials/query/fragment，publisher 不盲信调用者。
        payload = {
            "manifest_version": "phase29-v1",
            "resource_id": resource_id,
            "kind": kind,
            "source_url_sanitized": canonicalize_url(source_url),
            "redirect_chain_sanitized": [
                canonicalize_url(item) for item in redirect_chain
            ],
            "object_key": stat.object_key,
            "sha256": stat.sha256,
            "size_bytes": stat.size_bytes,
            "media_type": media_type,
            "git_commit": git_commit,
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }
        return ResourceManifest(
            **payload,
            manifest_sha256=resource_manifest_sha256(payload),
        )
```

Publisher 会再次 canonicalize source/redirect URL。第一版直接拒绝 userinfo/query/fragment，因此
ResourceManifest 和普通 logs/events 都不会携带 URL 凭据。

---

## 十九、Resource Worker

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/worker.py`。

主流程：

```python
class ResourceWorker:
    def run_once(self) -> bool:
        record = self.repository.claim_next(
            worker_id=self.worker_id,
            lease_seconds=self.lease_seconds,
        )
        if record is None:
            return False

        # claim_next 返回本次不可变 claim token；后续每次写入都带 fencing。
        claim_token = record.claim_token
        if claim_token is None:
            raise RuntimeError("claimed resource 缺少 claim token")

        try:
            self._assert_current_approval(record)
            with self.heartbeat(record.resource_id, claim_token) as heartbeat:
                staged = self.fetcher.fetch(
                    record,
                    ensure_active=heartbeat.raise_if_unhealthy,
                )
                self.repository.mark_validating(
                    resource_id=record.resource_id,
                    claim_token=claim_token,
                )
                manifest = self.publisher.publish(staged)
                heartbeat.raise_if_unhealthy()
                self.repository.mark_published(
                    resource_id=record.resource_id,
                    claim_token=claim_token,
                    manifest=manifest,
                )
        except ResourceLeaseLost:
            # 旧 Worker 不写终态；reconciler 根据 staging/blob 事实处理。
            pass
        except ResourceTransportUnavailable as exc:
            self.repository.mark_failed(
                resource_id=record.resource_id,
                claim_token=claim_token,
                error=self.error_payload(exc),
                retryable=True,
            )
        except Exception as exc:  # policy/integrity/limit 默认 terminal
            self.repository.mark_failed(
                resource_id=record.resource_id,
                claim_token=claim_token,
                error=self.error_payload(exc),
                retryable=False,
            )
        finally:
            self.cleanup_safe_staging(record)
        return True
```

`_assert_current_approval()`：

```python
def _assert_current_approval(self, record: ResourceRecord) -> None:
    approval = record.approval
    if approval is None or approval.decision != "approved":
        raise ResourcePolicyViolation("resource 没有 approved decision")
    current_hash = resource_request_sha256(record.request)
    if current_hash != record.request_sha256:
        raise ResourceIntegrityError("persisted request hash mismatch")
    if approval.request_sha256 != current_hash:
        raise ResourcePolicyViolation("stale resource approval")
```

Phase 28 telemetry 接入点：`resource.claim`、`resource.fetch`、`resource.validate`、`resource.publish`
spans；metrics labels 只放 kind/outcome/error_category，不放 resource_id 或 URL。

---

## 二十、崩溃恢复

> **本节类型：需要新增项目代码。**
>
> 新增：`app/resources/reconcile.py`。

恢复规则：

| 持久状态 | staging/blob 事实 | 处理 |
|---|---|---|
| fetching | 无 part，无活动进程 | 可安全 requeue |
| fetching | part 存在，下载进程不明确 | reconciliation_required |
| validating | part hash 正确 | 从验证继续，不重新联网 |
| validating | part hash 错误 | 删除 part，terminal integrity failure |
| published 前崩溃 | blob 已存在且 hash/size 匹配 | 恢复 manifest/DB commit |
| published | manifest/blob 匹配 | 正常终态 |
| 任意 | claim ownership 不匹配 | 旧 Worker 不得写入/清理 |

不要使用进程名或 URL 查找旧下载。为每个 attempt 持久化：

```text
resource_id
claim_token_hash
attempt
part path
expected/actual bytes
actual sha（完成后）
process ID（Git 子进程存在时）
started_at / heartbeat_at
```

清理前先确认路径位于 `RESOURCE_STAGING_ROOT/<resource_id>/<claim_hash>/`，不能 glob 删除整个
`resources/`。

---

## 二十一、API 与 CLI

> **本节类型：需要新增和修改项目代码。**
>
> 新增：`app/api/resource_routes.py`。
>
> 修改：`app/api/app.py`、`app/main.py`。

API：

```text
POST /v1/resources
GET  /v1/resources/{resource_id}
GET  /v1/resources/{resource_id}/events
POST /v1/resources/{resource_id}/decision
POST /v1/resources/{resource_id}/cancel
```

第一版所有 submit 结果都是 `awaiting_approval`。Decision body 必须包含：

```json
{
  "decision": "approved",
  "request_sha256": "<resource request hash>",
  "expected_version": 1,
  "reason": "论文官网 PDF，允许获取"
}
```

CLI：

```bash
python -m app.main request-resource \
  --kind paper_pdf \
  --url 'https://arxiv.org/pdf/xxxx.xxxxx' \
  --purpose 'PSTNet paper input' \
  --idempotency-key 'pstnet-paper-v1'

python -m app.main show-resource <resource-id>

python -m app.main approve-resource <resource-id> \
  --request-sha256 <hash>

python -m app.main run-resource-worker --once
```

终端展示 URL 时用 sanitized URL；批准前可以另设 `show-resource --reveal-source`，但仍不能显示
凭据，因为第一版根本不接受 credentials。

---

## 二十二、把 Resource 接入 Job submission

> **本节类型：需要修改项目代码。**
>
> 修改：`app/interaction/schemas.py`、`app/job_runtime/schemas.py`、
> `app/job_runtime/service.py`、`app/workspace/snapshot.py`。

为了兼容当前本地路径用法，先允许两种输入，但必须二选一：

```python
class JobCreateRequest(BaseModel):
    paper_path: str | None = None
    repo_path: str | None = None
    paper_resource_id: str | None = None
    repo_resource_id: str | None = None
    # ...保留 experiment_goal/execution_profile_id/dataset_refs...

    @model_validator(mode="after")
    def validate_input_sources(self) -> "JobCreateRequest":
        if (self.paper_path is None) == (self.paper_resource_id is None):
            raise ValueError("paper_path 与 paper_resource_id 必须且只能提供一个")
        if (self.repo_path is None) == (self.repo_resource_id is None):
            raise ValueError("repo_path 与 repo_resource_id 必须且只能提供一个")
        return self
```

`JobRequest` 中持久化解析后的不可变引用：

```python
class ResolvedResourceInput(JobModel):
    resource_id: str
    manifest_sha256: str
    object_key: str
    content_sha256: str
    size_bytes: int
    kind: str
    git_commit: str | None = None


class JobRequest(JobModel):
    # 本地兼容字段逐步改为 optional。
    paper_path: str | None = None
    repo_path: str | None = None
    paper_resource: ResolvedResourceInput | None = None
    repo_resource: ResolvedResourceInput | None = None
    # ...保留其他字段...
```

JobService 提交时：

```text
1. get ResourceRecord
2. require status=published
3. 重新校验 manifest schema/hash
4. 将 ResourceManifest snapshot 复制进 JobRequest
5. 用 resource content identity 参与 Job request_hash
6. 创建 WorkspaceManifest 时直接引用同一 Blob，避免再次上传
```

不要只在 Job 中保存 `resource_id` 后每次动态读取最新 Resource；Job 必须冻结 manifest snapshot，
否则资源 metadata 被修正后旧 Job 的输入身份会漂移。

---

## 二十三、Workspace 物化

> **本节类型：需要修改项目代码。**
>
> 修改：`app/workspace/snapshot.py`、`app/workspace/materializer.py`。

推荐直接增加 Resource -> Workspace entry adapter：

```python
def resource_workspace_entry(
    *,
    resource: ResolvedResourceInput,
    logical_path: str,
    role: str,
) -> WorkspaceBlobEntry:
    return WorkspaceBlobEntry(
        logical_path=logical_path,
        role=role,
        object_key=resource.object_key,
        sha256=resource.content_sha256,
        size_bytes=resource.size_bytes,
        media_type=(
            "application/pdf" if resource.kind == "paper_pdf"
            else "application/octet-stream"
        ),
        executable=False,
    )
```

对应逻辑路径：

```text
paper_pdf       -> source/paper.pdf
git_repository  -> capsule/repository.bundle
checkpoint      -> inputs/checkpoints/<resource_id>.bin
```

Materializer 继续使用 Phase 26 的：

```text
object stat
stream/copy
expected size
SHA-256
atomic rename
workspace path containment
```

OCI mount：repo 只读、run 可写、checkpoint 单独只读。论文程序如果需要 checkpoint 路径，应由
Action/Profile 注入确定性容器路径，不能让 LLM 指定任意 host source。

---

## 二十四、Resource readiness

> **本节类型：需要修改 Phase 28 代码。**

API readiness 增加：

```text
critical: ResourceRepository.ping
critical: BlobStore.ensure_ready
```

Acquisition Worker readiness：

```text
critical: ResourceRepository.ping
critical: staging root containment/write/fsync
critical: BlobStore.ensure_ready
critical or degraded: egress network guard configured
critical: git executable（启用 Git resource 时）
non-critical: allowed host DNS probe（带超时和缓存，不在每次 readyz 实时解析全部 host）
```

如果 `RESOURCE_REQUIRE_NETWORK_GUARD=true` 且没有配置 egress guard，Worker 必须 `not_ready`；开发
环境若设置 false，则明确 `degraded_application_guard_only`。

---

## 二十五、测试 Fake Transport

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/fakes/fake_resource_transport.py`。

单元测试不能访问公网或 localhost。Fake transport 按 URL 返回预设 response/chunks/redirect：

```python
class FakeResourceTransport:
    def __init__(self, responses: dict[str, object]):
        self.responses = responses
        self.requests: list[str] = []

    def stream(self, method: str, url: str):
        assert method == "GET"
        self.requests.append(url)
        return self.responses[url]
```

更推荐让 `HttpResourceDownloader` 依赖一个小的 `HttpTransportPort`，再写 `HttpxTransport` adapter，
这样测试不需要模拟 httpx 内部对象。

---

## 二十六、安全测试矩阵

> **本节类型：需要新增测试代码。**

### URL/DNS

```text
拒绝 http/ftp/file/ssh/git/ext
拒绝 userinfo、query、fragment、非 443 port
拒绝 host 不在 allowlist
拒绝 evilgithub.com 冒充 github.com
拒绝 127.0.0.1、::1、10/8、172.16/12、192.168/16、169.254/16
拒绝 IPv4-mapped IPv6 private address
任一 A/AAAA 非公网就拒绝
每次 redirect 重新检查 host 与 IP
```

### HTTP

```text
Content-Length 超限时不读 body
实际 streaming bytes 超限时删除 part
总 timeout 删除 part
expected SHA mismatch 删除 part
5xx 分类 retryable，4xx 默认 terminal
redirect 超限/循环 terminal
cancel/lease loss 停止写入并不 publish
```

### PDF/checkpoint

```text
伪造 Content-Type 但 magic 非 PDF 被拒绝
PDF 无页面/损坏被拒绝
checkpoint 无 expected hash 在 schema 阶段拒绝
checkpoint 获取阶段从不调用 torch.load/pickle
```

### Git

```text
必须 exact full commit
actual commit mismatch 被拒绝
命令 shell=False、token 化
环境禁用 prompt/system/global config
file/ext/ssh protocol 不可用
submodule/LFS 被拒绝
fetch 失败不留下 published manifest
bundle identity 与 commit 一致
```

### Approval/fencing

```text
修改 URL/commit/hash 后旧 approval 失效
旧 claim 完成后不能 mark_published
同 idempotency key + 同 request 返回同 Resource
同 idempotency key + 不同 request 冲突
published blob 已存在时验证后复用
```

---

## 二十七、测试命令

> **本节类型：验证步骤，不修改项目代码。**

Phase 29 离线测试：

```bash
mkdir -p .pytest-tmp
python -m pytest -q \
  --basetemp=.pytest-tmp/phase29 \
  tests/test_resource_schemas.py \
  tests/test_resource_policy.py \
  tests/test_resource_request_hash.py \
  tests/test_http_resource_downloader.py \
  tests/test_resource_validators.py \
  tests/test_git_resource_fetcher.py \
  tests/test_resource_worker.py \
  tests/test_resource_reconcile.py \
  tests/test_resource_job_submission.py \
  tests/test_resource_api.py
```

Workspace/Artifact/Job 回归：

```bash
python -m pytest -q \
  --basetemp=.pytest-tmp/phase29-regression \
  tests/test_workspace_snapshot.py \
  tests/test_workspace_materializer.py \
  tests/test_workspace_rebind.py \
  tests/test_artifact_publication.py \
  tests/test_job_worker.py \
  tests/test_job_api.py
```

PostgreSQL contract：

```bash
export TEST_DATABASE_URL="${DATABASE_URL}"
python -m pytest -q -m postgres \
  --basetemp=.pytest-tmp/phase29-postgres \
  tests/test_postgres_resource_repository.py \
  tests/test_postgres_resource_claim.py
```

全量离线：

```bash
python -m pytest -q \
  -m 'not provider and not postgres and not container_runtime and not network' \
  --basetemp=.pytest-tmp/phase29-all
```

静态检查：

```bash
python -m compileall -q app tests
ruff check app tests
```

---

## 二十八、显式网络 integration test

> **本节类型：可选手工测试，不进入普通回归。**

真实网络测试必须：

```text
显式设置 ENABLE_RESOURCE_NETWORK_TESTS=true
只使用 allowlist 中的公开测试资源
提供 expected hash/commit
不使用凭据
有严格 byte/time budget
标记 pytest.mark.network
```

运行：

```bash
ENABLE_RESOURCE_NETWORK_TESTS=true \
python -m pytest -q -m network \
  --basetemp=.pytest-tmp/phase29-network \
  tests/test_resource_network_integration.py
```

CI 默认排除该 marker。网络波动不能让普通单元测试变红。

---

## 二十九、手工验收

> **本节类型：手工操作，不修改项目代码。**

### 29.1 PDF

1. 提交 allowlist 内的论文 PDF URL；
2. `show-resource` 检查 canonical URL、request hash、预算；
3. 使用精确 hash 批准；
4. 运行 Resource Worker；
5. 确认状态依次经过 fetching/validating/published；
6. 检查 manifest 包含 content SHA、size、object key、sanitized redirect chain；
7. 用 resource ID 提交 Job；
8. 确认 Workspace 中 `source/paper.pdf` hash 一致。

### 29.2 Git repository

1. 从受信任页面获得完整 commit SHA，不使用 branch/tag 作为最终身份；
2. 提交 HTTPS repository URL + exact commit；
3. 批准并运行 Acquisition Worker；
4. 检查 fetch 使用 detached exact commit；
5. 确认 submodule/LFS 仓库被明确拒绝；
6. 检查 bundle 的 repository identity；
7. Job submission 固化 resource manifest snapshot；
8. OCI 中 repo 只读且 execution network 仍为 none。

### 29.3 失败与恢复

1. 用错误 expected SHA 获取 checkpoint，确认 terminal integrity failure；
2. 模拟 redirect 到 private IP，确认请求在连接前被拒绝；
3. 模拟下载中 lease loss，确认旧 Worker 不 publish；
4. 模拟 blob 已写但 DB 未提交，确认 reconcile 不重新联网；
5. 修改 approved request，确认 stale approval；
6. 搜索 Phase 28 日志，确认没有 URL query、token、Prompt 和下载正文。

---

## 三十、常见错误

> **本节类型：问题排查，不修改项目代码。**

### 30.1 “已经检查 DNS，所以完全没有 SSRF”

不准确。客户端可能再次解析，仍有 DNS rebinding 窗口。需要 egress proxy/firewall 才能建立强
网络边界；未配置时 readiness 应 degraded。

### 30.2 允许自动 redirect

`follow_redirects=True` 会绕过逐跳 policy。必须关闭自动 redirect，每一跳重新 canonicalize、
allowlist 和 DNS 检查。

### 30.3 把 Content-Length 当真实大小

服务端可以缺失或伪造。必须同时限制声明大小和实际 streaming bytes。

### 30.4 Git 使用 branch 名

branch/tag 可移动，不是不可变身份。ResourceRequest 必须包含完整 commit SHA，fetch 后再次比较。

### 30.5 下载完立即 torch.load

这会把获取阶段变成代码执行阶段。checkpoint 只作为 opaque blob 校验 hash；加载发生在受控 OCI
运行中。

### 30.6 Resource published 后 Job 只保存 resource_id

Resource metadata 将来可能迁移或修正。Job 必须复制 manifest snapshot/content identity，确保旧 Job
仍能证明输入。

---

## 三十一、本阶段 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 31.1 Tool capability 应最小化

“会下载”不是一个单一工具权限。必须拆成 URL policy、审批、transport、validator、publisher 和
materializer，LLM 只能控制其中最低风险的 proposal 层。

### 31.2 内容身份应晚于获取、早于执行

URL 只是来源声明，最终身份是实际 bytes 的 SHA-256 或 Git exact commit + bundle hash。执行前
必须冻结这些身份。

### 31.3 网络与执行是不同副作用域

Acquisition Worker 可以受控联网，论文执行容器默认断网。这样失败定位、凭据范围、审计和安全
策略都更清晰。

### 31.4 Approval 绑定不可变意图

批准“下载 A”不能沿用到后来被修改的 B。request hash 与此前 Action approval hash 是同一类
Agent 安全模式。

### 31.5 Cache 不能替代验证

命中同 URL、ETag 或文件名都不表示内容相同。Cache 复用必须以 content digest 和 manifest 为准。

### 31.6 Crash recovery 要理解外部事实

数据库说 fetching 不代表下载仍在运行；blob 已存在也不代表已发布。恢复必须联合 record、part、
进程 ownership、blob stat 和 hash，而不是仅修改状态字段。

---

## 三十二、完成标准

> **本节类型：最终验收，不修改项目代码。**

- paper PDF、Git exact commit、checkpoint 三类 schema 完成；
- request hash + 人工 approval hash 防止审批漂移；
- HTTPS/host/DNS/redirect/size/time policy 有负向测试；
- 独立 Acquisition Worker 有 lease/heartbeat/fencing/reconcile；
- HTTP streaming 使用项目内 `.part`、fsync、hash 和失败清理；
- Git 禁止交互凭据、危险协议、submodule 和 LFS；
- PDF 验证 magic/parser，checkpoint 不反序列化；
- content-addressed Blob + ResourceManifest 发布完成；
- Job 冻结 Resource manifest snapshot；
- Workspace 物化同一 hash 的只读输入；
- OCI execution 仍为 `network=none`；
- Phase 28 telemetry 不泄露 URL query 或 secret；
- 普通测试完全离线；
- 未配置网络层 egress guard 时系统明确报告 degraded；
- 没有引入多用户/RBAC/tenant 复杂度。

---

## 三十三、后续路线

Phase 29 完成后，基础设施链已经形成：

```text
受控不可变输入
-> Workspace manifest
-> durable Job/checkpoint
-> human decision/fencing
-> OCI 安全执行
-> Artifact/Object Storage
-> telemetry/readiness/reconcile
```

下一步应重新回到论文复现产品价值，优先做：

```text
Experiment Run Matrix
Metric Extraction
Result Lineage
论文目标值与复现值的 evidence-backed comparison
```

Redis、消息队列、Kubernetes 和多用户系统继续延后，除非 PostgreSQL polling、单 Worker 吞吐或
真实协作需求已经有可观测数据证明它们成为瓶颈。
