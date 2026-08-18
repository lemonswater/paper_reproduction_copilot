# Phase 41：本地 Secret 管理、短期注入与统一脱敏

> **阶段状态**：核心项目代码已实现；专项测试与 Container Plan 回归合计 101 passed。  
> **优先级**：P0。  
> **部署边界**：单机、单用户；不引入多租户、RBAC、Vault Server 或 KMS。  
> **前置阶段**：Phase 16 安全执行边界、Phase 28 可观测性脱敏、Phase 29 受控资源获取、
> Phase 40 Tool Contract。  
> **本阶段原则**：明文 Secret 只能短暂存在于需要它的进程内存和目标调用边界，不能进入
> Prompt、Chat Memory、Checkpoint、Event、Log、Artifact、Tool Audit 或 Support Bundle。

---

## 一、为什么下一阶段必须先做 Secret 管理

> **本节类型：解释，不修改代码。**

Phase 40 已经解决“哪些函数可以成为 Agent Tool”的问题，但当前系统仍有几类 Secret
直接保存在全局配置或进程环境中：

~~~text
OPENAI_API_KEY
EMBEDDING_API_KEY
DATABASE_URL 中的数据库密码
AGENT_API_TOKEN
未来的 Hugging Face / GitHub / 私有资源 Token
用户希望注入论文程序的敏感环境变量
~~~

现有安全措施只能覆盖一部分风险：

- `build_minimal_environment()` 不再复制整个 `os.environ`，能阻止论文程序读取 Agent API Key；
- `observability.redaction.redact()` 能按字段名隐藏 `api_key`、`token` 等值；
- ProcessRecord 会隐藏常见 `--token value` 命令行参数；
- Tool Audit 只保存输入输出 SHA-256，不保存原始 Payload；
- Resource URL 已拒绝 userinfo、query 和 fragment。

但这些措施仍有四个缺口：

1. `Settings` 仍长期保存 Provider Key、API Token 和 Database URL 明文；
2. 只按字段名脱敏，抓不住 `"connection failed: sk-..."` 这种嵌入普通字符串的 Secret；
3. 子进程如果主动打印注入的 Token，当前 stdout/stderr 会把它原样写入日志；
4. State、Chat、Event、Artifact 和 Tool Output 没有统一的“已知 Secret 值”泄漏门禁。

因此 Phase 41 不是“再加几个正则表达式”，而是建立一条完整生命周期：

~~~text
安全录入
  -> 加密存储
  -> 只保存版本化引用
  -> 按用途短期解析
  -> 注入单个调用边界
  -> 输出流脱敏
  -> 持久化前扫描
  -> 可审计轮换与撤销
~~~

---

## 二、本阶段完成后的能力

> **本节类型：目标说明，不修改代码。**

完成后系统应具备：

1. Secret 通过隐藏输入 CLI 录入，不允许通过命令行参数传明文；
2. Secret 使用 Fernet 认证加密后保存在本地 SQLite Vault；
3. Master Key 与 Vault 文件都要求普通文件、禁止符号链接、权限必须为 `0600`；
4. State、Action、Request 和 Approval 中只出现 `SecretReference`；
5. 引用绑定 `name + version + keyed fingerprint`，轮换后旧引用不能继续执行；
6. Secret 声明允许用途，例如 `provider`、`database`、`resource_http` 或 `execution_env`；
7. Provider、数据库、API Auth、资源 Worker 和论文子进程只在调用前解析明文；
8. JSON Log、错误报告、Chat、Tool 输入输出、Process Log 和 Artifact 使用同一 Redactor；
9. stdout/stderr 即使把 Secret 拆成多个 byte chunk 输出，也不能写入原始日志；
10. 提供 Secret Canary 与 Leak Scanner 测试，验证 Run、Checkpoint、Event、Chat 和 Artifact；
11. CLI 永远不提供“显示 Secret 明文”的命令；
12. 所有审计只记录引用、用途、actor、时间和结果，不记录明文或可离线猜测的普通 SHA-256。

---

## 三、本阶段明确不做

> **本节类型：范围约束，不修改代码。**

本阶段不实现：

- HashiCorp Vault、AWS KMS、云 Secret Manager；
- 多用户、租户隔离、RBAC 和 Secret Sharing；
- 浏览器登录、Cookie Jar 或 OAuth Refresh Token 自动刷新；
- 自动从网页、论文或代码中识别并导入 Secret；
- 允许 LLM 查看、创建、删除或选择 Secret；
- 把 Secret 明文写入 Docker/OCI Image、Workspace Snapshot 或 Support Bundle；
- 通过命令行 `--value secret`、URL query、Git remote URL 或 Action args 传 Secret；
- 对本机 root、同一 Unix 用户完全失陷后的强安全保证；
- 在 Python 中可靠“清零”不可变字符串内存。

本地加密主要防止误提交、普通 Artifact 导出、日志泄漏和数据库文件被单独复制后直接读取。
如果攻击者同时取得当前 Unix 用户权限、Master Key 和 Vault，仍可以解密；这是单机单用户
边界下的明确限制。

---

## 四、威胁模型与不变量

> **本节类型：架构约束，不修改代码。**

### 4.1 主要威胁

| 威胁 | 示例 | 本阶段处理 |
|---|---|---|
| 配置泄漏 | `Settings` 被打印后包含 API Key | Settings 只保存 Secret 名称 |
| 日志泄漏 | 子进程执行 `print(HF_TOKEN)` | 流式已知值脱敏 |
| Prompt 泄漏 | 用户把 Token 粘贴进 Chat | 入库和进 Prompt 前统一脱敏 |
| Artifact 泄漏 | traceback 包含 Authorization Header | Artifact 写入前脱敏或拒绝 |
| Checkpoint 泄漏 | Action 保存 `env={"TOKEN": "..."}` | Action 只保存 SecretReference |
| 旧审批复用 | Secret 轮换后旧 Action 仍执行 | version + fingerprint 进入 Action Hash |
| Tool 越权 | Tool 读取 `.env` 或返回已知 Key | 敏感路径拒绝 + Registry Leak Guard |
| 审计反推 | 保存低熵密码普通 SHA-256 | 使用 Master Key 做 HMAC fingerprint |
| 路径攻击 | Vault Path 指向 symlink | lstat、O_NOFOLLOW、权限校验 |

### 4.2 必须长期保持的不变量

~~~text
Invariant 1：Secret 明文不是 Pydantic State 字段。
Invariant 2：Secret 明文不是 Action、Approval、Event 或 Artifact Metadata。
Invariant 3：SecretReference 必须进入 Action Hash。
Invariant 4：用途不匹配时 fail closed。
Invariant 5：轮换或撤销后，旧 Reference 不可解析。
Invariant 6：日志先脱敏，再写文件和 preview。
Invariant 7：未知错误不能把 exception message 原样持久化。
Invariant 8：Secret Store 不提供 list-values 或 show-value。
Invariant 9：LLM/Tool 不能调用 Secret Resolve。
Invariant 10：测试使用 Canary 验证“值没有出现”，不能只验证字段名。
~~~

---

## 五、三个容易混淆的概念

> **本节类型：解释，不修改代码。**

### 5.1 Secret Metadata

可以持久化和展示：

~~~text
name / version / status / allowed_uses / fingerprint / created_at / updated_at
~~~

### 5.2 Secret Reference

可以进入 State、Checkpoint、Action、Request 和审批 Hash：

~~~json
{
  "name": "HF_TOKEN",
  "version": 3,
  "fingerprint": "hmac-sha256:..."
}
~~~

### 5.3 Secret Material

只存在于受信任 Python 调用栈内：

~~~text
SecretMaterial(reference, allowed_uses, private plaintext)
~~~

`SecretMaterial.__str__()` 和 `repr()` 必须只显示 `<redacted>`，并且禁止 pickle，防止被
LangGraph Checkpoint 或普通 `json.dumps(default=str)` 意外保存。

---

## 六、总体架构

> **本节类型：架构说明，不修改代码。**

~~~mermaid
flowchart TD
    CLI["Hidden-input CLI"] --> SERVICE["SecretService"]
    SERVICE --> STORE["Encrypted SQLite SecretStore"]
    STORE --> KEY["0600 Master Key"]

    SERVICE --> REF["SecretReference only"]
    REF --> STATE["State / Action / Approval / Event"]

    SERVICE --> MATERIAL["SecretMaterial in memory"]
    MATERIAL --> PROVIDER["Provider Client"]
    MATERIAL --> DB["Database Engine"]
    MATERIAL --> RESOURCE["Resource Worker"]
    MATERIAL --> EXEC["Supervised Process env"]

    MATERIAL --> REDACTOR["SecretRedactor"]
    REDACTOR --> LOG["JSON / Process Log"]
    REDACTOR --> CHAT["Chat / Prompt"]
    REDACTOR --> TOOL["Tool Boundary"]
    REDACTOR --> ARTIFACT["Artifact / Support Bundle"]

    STORE --> AUDIT["Metadata-only Audit"]
~~~

Secret 使用流程：

~~~text
SecretReference
  -> Store 查询 exact version
  -> 校验 active
  -> 校验 keyed fingerprint
  -> 校验 requested use
  -> 解密 envelope
  -> 注入目标调用
  -> 输出经过 scoped redactor
  -> 审计只记录 metadata
~~~

---

## 七、涉及文件与推荐顺序

> **本节类型：实施清单，不修改代码。**

### 7.1 需要新增

~~~text
app/secrets/__init__.py
app/secrets/errors.py
app/secrets/schemas.py
app/secrets/ports.py
app/secrets/crypto.py
app/secrets/store.py
app/secrets/redaction.py
app/secrets/service.py
app/secrets/factory.py
app/secrets/doctor.py
app/secrets/scanner.py

tests/test_secret_store.py
tests/test_secret_redaction.py
tests/test_model.py
tests/test_execution_secret_injection.py
tests/test_secret_artifact_boundary.py
tests/test_secret_canary_boundary.py
tests/test_secret_scanner.py
tests/test_database_secret.py
tests/test_api_auth.py
tests/test_secret_cli.py
~~~

### 7.2 需要修改

~~~text
pyproject.toml
.gitignore
app/config.py
app/model.py
app/persistence/database.py
alembic/env.py
app/api/app.py
app/api/auth.py
app/schemas.py
app/execution/environment.py
app/execution/base.py
app/execution/process_supervisor.py
app/execution/registry.py
app/resources/schemas.py
app/resources/http_downloader.py
app/resources/git_fetcher.py
app/resources/worker.py
app/resources/request_hash.py
app/observability/redaction.py
app/observability/json_logging.py
app/observability/instrumentation.py
app/tools/error_tools.py
app/tools/artifact_tools.py
app/tool_contracts/registry.py
app/tool_contracts/catalog.py
app/tool_contracts/inventory.py
app/chat/service.py
app/api/chat_routes.py（仅在 API 层选择“拒绝 Secret 输入”时修改）
app/artifact_delivery/service.py
app/main.py
~~~

### 7.3 本阶段不修改

~~~text
app/graph.py
app/nodes/* 的主业务路由
LangGraph Checkpoint Schema
Web 页面主体
OCI Image 构建流程
PostgreSQL 表结构
~~~

本阶段通过“只允许引用进入 State”和“统一持久化边界扫描”保护 Graph，不需要给每个 Node
增加一套 Secret 字段。

### 7.4 推荐实施顺序

~~~text
依赖与忽略规则
  -> Schema / Error / Crypto
  -> SQLite Store
  -> Redactor / Streaming Redactor
  -> SecretService / Factory
  -> Config 与 Provider
  -> Database / API Auth
  -> Action Reference 与执行注入
  -> Process Log 脱敏
  -> Resource Credential
  -> Tool / Chat / Artifact 边界
  -> CLI 与迁移
  -> Canary / Fault Injection / 全量回归
~~~

---

## 八、增加依赖与本地文件忽略规则

> **本节类型：需要修改代码。**
>
> 需要修改：`pyproject.toml`、`.gitignore`。

### 8.1 修改 `pyproject.toml`

在 `[project].dependencies` 中增加 `cryptography`：

~~~toml
[project]
requires-python = ">=3.10"
dependencies = [
    "langchain>=0.3",
    "langchain-openai>=1.3,<2",
    "langgraph>=0.2",
    "langgraph-checkpoint-sqlite>=3",
    "pydantic>=2",
    "typer>=0.12",
    "rich>=13",
    "pymupdf>=1.24",
    "python-dotenv>=1.0",
    "psutil>=5.9",
    "cryptography>=42",
]
~~~

安装：

~~~bash
python -m pip install -e .
~~~

### 8.2 修改 `.gitignore`

在末尾增加：

~~~gitignore
# Phase 41 local encrypted Secret Vault and master key.
/secrets/
config/secrets.local.json
~~~

`/secrets/` 中同时包含 Vault 和 Master Key。加密不代表可以提交 Git；密文、名称和使用时间
仍然属于敏感运维信息。

---

## 九、定义稳定错误类型

> **本节类型：需要新增代码。**
>
> 需要新增：`app/secrets/errors.py`。

完整文件：

~~~python
from __future__ import annotations


class SecretError(RuntimeError):
    """Phase 41 Secret 子系统的稳定基类。"""


class SecretConfigurationError(SecretError):
    """Vault 路径、Master Key 或权限配置不安全。"""


class SecretNotFoundError(SecretError):
    """指定名称或版本不存在。"""


class SecretInactiveError(SecretError):
    """Secret 已轮换、撤销或删除，旧引用不能继续使用。"""


class SecretUseDeniedError(SecretError):
    """Secret 没有授权给当前用途。"""


class SecretIntegrityError(SecretError):
    """密文、Envelope、Fingerprint 或 Reference 身份不一致。"""


class SecretLeakDetectedError(SecretError):
    """持久化边界检测到已知 Secret 明文。"""
~~~

错误消息只能包含 Secret 名称、版本、用途和稳定错误码，不能包含明文、密文或请求 Header。

---

## 十、定义 Secret Schema

> **本节类型：需要新增代码。**
>
> 需要新增：`app/secrets/schemas.py`。

完整文件：

~~~python
from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SECRET_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
FINGERPRINT_RE = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")


class SecretModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SecretUse(str, Enum):
    PROVIDER = "provider"
    EMBEDDING = "embedding"
    DATABASE = "database"
    API_AUTH = "api_auth"
    RESOURCE_HTTP = "resource_http"
    RESOURCE_GIT = "resource_git"
    EXECUTION_ENV = "execution_env"


class SecretStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"


class SecretReference(SecretModel):
    """可以进入 State、Action、Request 和 Approval Hash 的公开引用。"""

    name: str = Field(pattern=SECRET_NAME_RE.pattern)
    version: int = Field(ge=1)
    fingerprint: str = Field(pattern=FINGERPRINT_RE.pattern)


class SecretMetadata(SecretModel):
    reference: SecretReference
    status: SecretStatus
    allowed_uses: list[SecretUse] = Field(min_length=1)
    created_at: str
    updated_at: str
    last_used_at: str | None = None

    @field_validator("allowed_uses")
    @classmethod
    def normalize_uses(
        cls,
        value: list[SecretUse],
    ) -> list[SecretUse]:
        unique = sorted(set(value), key=lambda item: item.value)
        if not unique:
            raise ValueError("allowed_uses 不能为空")
        return unique


class SecretAuditRecord(SecretModel):
    event_id: int
    event_type: Literal[
        "secret.created",
        "secret.rotated",
        "secret.resolved",
        "secret.revoked",
        "secret.redactor_loaded",
    ]
    secret_name: str
    secret_version: int
    use: SecretUse | None = None
    actor: str
    outcome: Literal["succeeded", "denied", "failed"]
    created_at: str


class SecretHealthReport(SecretModel):
    ok: bool
    vault_initialized: bool
    key_permissions_ok: bool
    vault_permissions_ok: bool
    active_secret_count: int = Field(ge=0)
    issues: list[str] = Field(default_factory=list)
~~~

这里故意没有 `SecretCreateRequest(value=...)`。明文不进入 Pydantic 模型，避免
`model_dump()`、ValidationError、OpenAPI Schema 或日志把值保存下来。

---

## 十一、定义内存 Material 与 Store Protocol

> **本节类型：需要新增代码。**
>
> 需要新增：`app/secrets/ports.py`。

完整文件：

~~~python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.secrets.schemas import (
    SecretAuditRecord,
    SecretMetadata,
    SecretReference,
    SecretUse,
)


@dataclass(frozen=True, slots=True)
class SecretMaterial:
    """受信任调用栈内的短期明文包装。

    _value 不参与 repr；对象禁止 pickle，避免进入 Checkpoint。
    """

    reference: SecretReference
    allowed_uses: tuple[SecretUse, ...]
    _value: str = field(repr=False)

    def reveal(self) -> str:
        return self._value

    def __str__(self) -> str:
        return "<redacted>"

    def __repr__(self) -> str:
        return (
            "SecretMaterial("
            f"name={self.reference.name!r}, "
            f"version={self.reference.version}, "
            "value=<redacted>)"
        )

    def __getstate__(self):
        raise TypeError("SecretMaterial 禁止序列化或写入 Checkpoint")

    def __reduce__(self):
        raise TypeError("SecretMaterial 禁止 pickle")


class SecretStore(Protocol):
    def initialize(self) -> None:
        ...

    def put(
        self,
        *,
        name: str,
        value: str,
        allowed_uses: list[SecretUse],
        actor: str,
    ) -> SecretMetadata:
        ...

    def current_reference(self, name: str) -> SecretReference:
        ...

    def resolve(
        self,
        *,
        reference: SecretReference,
        use: SecretUse,
        actor: str,
    ) -> SecretMaterial:
        ...

    def list_metadata(self) -> list[SecretMetadata]:
        ...

    def revoke(
        self,
        *,
        reference: SecretReference,
        actor: str,
    ) -> SecretMetadata:
        ...

    def active_materials_for_redaction(
        self,
        *,
        actor: str,
    ) -> list[SecretMaterial]:
        ...

    def list_audit(
        self,
        *,
        limit: int = 200,
    ) -> list[SecretAuditRecord]:
        ...
~~~

---

## 十二、实现 Master Key 与认证加密

> **本节类型：需要新增代码。**
>
> 需要新增：`app/secrets/crypto.py`。

完整文件：

~~~python
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.secrets.errors import (
    SecretConfigurationError,
    SecretIntegrityError,
)


def require_private_regular_file(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise SecretConfigurationError(
            f"Secret 文件不存在：{path}"
        ) from exc
    if stat.S_ISLNK(info.st_mode):
        raise SecretConfigurationError("Secret 文件不能是符号链接")
    if not stat.S_ISREG(info.st_mode):
        raise SecretConfigurationError("Secret 文件必须是普通文件")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise SecretConfigurationError(
            f"Secret 文件权限过宽：{path}，要求 0600"
        )


def create_master_key_file(path: Path) -> None:
    """显式初始化 Master Key；运行时不能静默重新生成。"""

    # abspath() 规范化相对路径和 ..，但不跟随最终 symlink；
    # 若先 resolve()，后面的 is_symlink()/lstat() 将看不到链接本身。
    target = Path(os.path.abspath(path.expanduser()))
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent_info = parent.lstat()
    if stat.S_ISLNK(parent_info.st_mode):
        raise SecretConfigurationError(
            "Master Key 目录不能是符号链接"
        )
    if not stat.S_ISDIR(parent_info.st_mode):
        raise SecretConfigurationError(
            "Master Key 父路径必须是目录"
        )
    # init 命令可以把新建/专用目录收紧；运行时 doctor 仍需 fail closed。
    os.chmod(parent, 0o700)
    if target.exists() or target.is_symlink():
        raise SecretConfigurationError("Master Key 已存在")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(Fernet.generate_key() + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    os.chmod(target, 0o600)


class FernetSecretCipher:
    def __init__(self, key_path: Path):
        self.key_path = Path(
            os.path.abspath(key_path.expanduser())
        )
        require_private_regular_file(self.key_path)
        key = self.key_path.read_bytes().strip()
        try:
            raw_key = base64.urlsafe_b64decode(key)
            if len(raw_key) != 32:
                raise ValueError("invalid key length")
            self._fernet = Fernet(key)
        except (ValueError, TypeError) as exc:
            raise SecretConfigurationError(
                "Master Key 不是合法 Fernet Key"
            ) from exc
        self._fingerprint_key = hmac.new(
            raw_key,
            b"paper-copilot-phase41-fingerprint-v1",
            hashlib.sha256,
        ).digest()

    def fingerprint(self, value: str) -> str:
        digest = hmac.new(
            self._fingerprint_key,
            value.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"hmac-sha256:{digest}"

    def encrypt(
        self,
        *,
        name: str,
        version: int,
        value: str,
    ) -> bytes:
        envelope = json.dumps(
            {
                "format": "phase41-v1",
                "name": name,
                "version": version,
                "value": value,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return self._fernet.encrypt(envelope)

    def decrypt(
        self,
        *,
        name: str,
        version: int,
        ciphertext: bytes,
    ) -> str:
        try:
            envelope = json.loads(
                self._fernet.decrypt(ciphertext).decode("utf-8")
            )
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SecretIntegrityError(
                f"Secret 密文无法通过认证：{name} v{version}"
            ) from exc

        if (
            envelope.get("format") != "phase41-v1"
            or envelope.get("name") != name
            or envelope.get("version") != version
            or not isinstance(envelope.get("value"), str)
        ):
            raise SecretIntegrityError(
                f"Secret Envelope 身份不匹配：{name} v{version}"
            )
        return str(envelope["value"])
~~~

为什么 Fingerprint 使用 HMAC，而不是普通 SHA-256：

~~~text
普通 SHA-256(password)
  -> 攻击者拿到数据库后可以离线猜常见密码

HMAC(master-derived-key, password)
  -> 没有 Master Key 时不能验证猜测
~~~

Fingerprint 不是认证凭据，只用于把 Action 审批绑定到某个 Secret 内容版本。

---

## 十三、实现加密 SQLite Secret Store

> **本节类型：需要新增代码。**
>
> 需要新增：`app/secrets/store.py`。

完整文件：

~~~python
from __future__ import annotations

import json
import os
import sqlite3
import stat
from datetime import datetime, timezone
from pathlib import Path

from app.secrets.crypto import FernetSecretCipher
from app.secrets.errors import (
    SecretConfigurationError,
    SecretInactiveError,
    SecretIntegrityError,
    SecretNotFoundError,
    SecretUseDeniedError,
)
from app.secrets.ports import SecretMaterial
from app.secrets.schemas import (
    SECRET_NAME_RE,
    SecretAuditRecord,
    SecretMetadata,
    SecretReference,
    SecretStatus,
    SecretUse,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(value: str) -> str:
    name = value.strip().upper()
    if not SECRET_NAME_RE.fullmatch(name):
        raise ValueError(
            "Secret name 必须是 3..128 位大写字母、数字或下划线"
        )
    return name


def _validate_plaintext(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Secret value 必须是字符串")
    if not 8 <= len(value) <= 16384:
        raise ValueError("Secret value 长度必须位于 8..16384")
    if "\x00" in value:
        raise ValueError("Secret value 不能包含 NUL")
    return value


class SqliteSecretStore:
    def __init__(
        self,
        *,
        path: Path,
        cipher: FernetSecretCipher,
    ):
        # 不用 resolve()，否则最终路径是 symlink 时检查会失效。
        self.path = Path(os.path.abspath(path.expanduser()))
        self.cipher = cipher

    def _prepare_private_database_file(self) -> None:
        """在 SQLite 打开前固定路径类型和权限，避免首次创建窗口。"""

        parent = self.path.parent
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent_info = parent.lstat()
        if stat.S_ISLNK(parent_info.st_mode):
            raise SecretConfigurationError(
                "Secret Vault 目录不能是符号链接"
            )
        if not stat.S_ISDIR(parent_info.st_mode):
            raise SecretConfigurationError(
                "Secret Vault 父路径必须是目录"
            )
        if stat.S_IMODE(parent_info.st_mode) & 0o077:
            raise SecretConfigurationError(
                "Secret Vault 目录权限必须为 0700"
            )

        if self.path.is_symlink():
            raise SecretConfigurationError(
                "Secret Vault 不能是符号链接"
            )
        if self.path.exists():
            info = self.path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise SecretConfigurationError(
                    "Secret Vault 必须是普通文件"
                )
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise SecretConfigurationError(
                    "Secret Vault 文件权限必须为 0600"
                )
            return

        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.path, flags, 0o600)
        os.close(descriptor)

    def _connect(self) -> sqlite3.Connection:
        self._prepare_private_database_file()
        connection = sqlite3.connect(
            self.path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS secret_versions (
                    name TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    ciphertext BLOB NOT NULL,
                    value_fingerprint TEXT NOT NULL,
                    allowed_uses_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_used_at TEXT,
                    PRIMARY KEY (name, version),
                    CHECK (version >= 1),
                    CHECK (
                        status IN ('active', 'superseded', 'revoked')
                    )
                );

                CREATE UNIQUE INDEX IF NOT EXISTS
                    uq_secret_one_active_version
                ON secret_versions(name)
                WHERE status = 'active';

                CREATE TABLE IF NOT EXISTS secret_audit (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    secret_name TEXT NOT NULL,
                    secret_version INTEGER NOT NULL,
                    use_name TEXT,
                    actor TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
        self._chmod_sqlite_files()

    def _chmod_sqlite_files(self) -> None:
        for candidate in (
            self.path,
            self.path.with_name(self.path.name + "-wal"),
            self.path.with_name(self.path.name + "-shm"),
        ):
            if candidate.exists():
                if candidate.is_symlink():
                    raise SecretConfigurationError(
                        "Secret SQLite 文件不能是符号链接"
                    )
                os.chmod(candidate, 0o600)

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        *,
        event_type: str,
        name: str,
        version: int,
        use: SecretUse | None,
        actor: str,
        outcome: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO secret_audit (
                event_type, secret_name, secret_version,
                use_name, actor, outcome, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                name,
                version,
                use.value if use is not None else None,
                actor[:200],
                outcome,
                _utc_now(),
            ),
        )

    @staticmethod
    def _metadata(row: sqlite3.Row) -> SecretMetadata:
        uses = [
            SecretUse(item)
            for item in json.loads(row["allowed_uses_json"])
        ]
        return SecretMetadata(
            reference=SecretReference(
                name=row["name"],
                version=row["version"],
                fingerprint=row["value_fingerprint"],
            ),
            status=SecretStatus(row["status"]),
            allowed_uses=uses,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_used_at=row["last_used_at"],
        )

    def put(
        self,
        *,
        name: str,
        value: str,
        allowed_uses: list[SecretUse],
        actor: str,
    ) -> SecretMetadata:
        normalized_name = _normalize_name(name)
        plaintext = _validate_plaintext(value)
        normalized_uses = sorted(
            set(allowed_uses),
            key=lambda item: item.value,
        )
        if not normalized_uses:
            raise ValueError("allowed_uses 不能为空")

        now = _utc_now()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT COALESCE(MAX(version), 0) AS latest
                FROM secret_versions
                WHERE name = ?
                """,
                (normalized_name,),
            ).fetchone()
            version = int(row["latest"]) + 1
            fingerprint = self.cipher.fingerprint(plaintext)
            ciphertext = self.cipher.encrypt(
                name=normalized_name,
                version=version,
                value=plaintext,
            )

            changed = connection.execute(
                """
                UPDATE secret_versions
                SET status = 'superseded', updated_at = ?
                WHERE name = ? AND status = 'active'
                """,
                (now, normalized_name),
            ).rowcount
            event_type = "secret.rotated" if changed else "secret.created"
            connection.execute(
                """
                INSERT INTO secret_versions (
                    name, version, ciphertext, value_fingerprint,
                    allowed_uses_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    normalized_name,
                    version,
                    ciphertext,
                    fingerprint,
                    json.dumps(
                        [item.value for item in normalized_uses],
                        separators=(",", ":"),
                    ),
                    now,
                    now,
                ),
            )
            self._audit(
                connection,
                event_type=event_type,
                name=normalized_name,
                version=version,
                use=None,
                actor=actor,
                outcome="succeeded",
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        self._chmod_sqlite_files()
        return self._get_metadata(normalized_name, version)

    def _get_row(
        self,
        *,
        name: str,
        version: int,
    ) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM secret_versions
                WHERE name = ? AND version = ?
                """,
                (name, version),
            ).fetchone()
        if row is None:
            raise SecretNotFoundError(
                f"Secret 不存在：{name} v{version}"
            )
        return row

    def _get_metadata(
        self,
        name: str,
        version: int,
    ) -> SecretMetadata:
        return self._metadata(
            self._get_row(name=name, version=version)
        )

    def current_reference(self, name: str) -> SecretReference:
        normalized_name = _normalize_name(name)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM secret_versions
                WHERE name = ? AND status = 'active'
                """,
                (normalized_name,),
            ).fetchone()
        if row is None:
            raise SecretNotFoundError(
                f"没有 active Secret：{normalized_name}"
            )
        return self._metadata(row).reference

    def resolve(
        self,
        *,
        reference: SecretReference,
        use: SecretUse,
        actor: str,
    ) -> SecretMaterial:
        row = self._get_row(
            name=reference.name,
            version=reference.version,
        )
        metadata = self._metadata(row)
        if metadata.status != SecretStatus.ACTIVE:
            raise SecretInactiveError(
                f"Secret 已失效：{reference.name} v{reference.version}"
            )
        if metadata.reference.fingerprint != reference.fingerprint:
            raise SecretIntegrityError(
                "Secret Reference fingerprint 不匹配："
                f"{reference.name} v{reference.version}"
            )
        if use not in metadata.allowed_uses:
            with self._connect() as connection:
                self._audit(
                    connection,
                    event_type="secret.resolved",
                    name=reference.name,
                    version=reference.version,
                    use=use,
                    actor=actor,
                    outcome="denied",
                )
            raise SecretUseDeniedError(
                f"Secret 未授权用途：{reference.name} -> {use.value}"
            )

        value = self.cipher.decrypt(
            name=reference.name,
            version=reference.version,
            ciphertext=bytes(row["ciphertext"]),
        )
        if self.cipher.fingerprint(value) != reference.fingerprint:
            raise SecretIntegrityError(
                "Secret 明文 fingerprint 不匹配："
                f"{reference.name} v{reference.version}"
            )

        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE secret_versions
                SET last_used_at = ?, updated_at = ?
                WHERE name = ? AND version = ? AND status = 'active'
                """,
                (
                    now,
                    now,
                    reference.name,
                    reference.version,
                ),
            )
            self._audit(
                connection,
                event_type="secret.resolved",
                name=reference.name,
                version=reference.version,
                use=use,
                actor=actor,
                outcome="succeeded",
            )
        return SecretMaterial(
            reference=reference,
            allowed_uses=tuple(metadata.allowed_uses),
            _value=value,
        )

    def list_metadata(self) -> list[SecretMetadata]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM secret_versions
                ORDER BY name, version DESC
                """
            ).fetchall()
        return [self._metadata(row) for row in rows]

    def revoke(
        self,
        *,
        reference: SecretReference,
        actor: str,
    ) -> SecretMetadata:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """
                UPDATE secret_versions
                SET status = 'revoked', updated_at = ?
                WHERE name = ?
                  AND version = ?
                  AND value_fingerprint = ?
                  AND status = 'active'
                """,
                (
                    _utc_now(),
                    reference.name,
                    reference.version,
                    reference.fingerprint,
                ),
            ).rowcount
            if changed != 1:
                raise SecretInactiveError(
                    "Secret 已失效或 Reference 不匹配"
                )
            self._audit(
                connection,
                event_type="secret.revoked",
                name=reference.name,
                version=reference.version,
                use=None,
                actor=actor,
                outcome="succeeded",
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self._get_metadata(
            reference.name,
            reference.version,
        )

    def active_materials_for_redaction(
        self,
        *,
        actor: str,
    ) -> list[SecretMaterial]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM secret_versions
                WHERE status = 'active'
                ORDER BY name
                """
            ).fetchall()
            materials: list[SecretMaterial] = []
            for row in rows:
                metadata = self._metadata(row)
                value = self.cipher.decrypt(
                    name=metadata.reference.name,
                    version=metadata.reference.version,
                    ciphertext=bytes(row["ciphertext"]),
                )
                if (
                    self.cipher.fingerprint(value)
                    != metadata.reference.fingerprint
                ):
                    raise SecretIntegrityError(
                        "Redactor 加载时 Secret fingerprint 不匹配"
                    )
                materials.append(
                    SecretMaterial(
                        reference=metadata.reference,
                        allowed_uses=tuple(metadata.allowed_uses),
                        _value=value,
                    )
                )
                self._audit(
                    connection,
                    event_type="secret.redactor_loaded",
                    name=metadata.reference.name,
                    version=metadata.reference.version,
                    use=None,
                    actor=actor,
                    outcome="succeeded",
                )
        return materials

    def list_audit(
        self,
        *,
        limit: int = 200,
    ) -> list[SecretAuditRecord]:
        bounded = min(max(limit, 1), 1000)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM secret_audit
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (bounded,),
            ).fetchall()
        return [
            SecretAuditRecord(
                event_id=row["event_id"],
                event_type=row["event_type"],
                secret_name=row["secret_name"],
                secret_version=row["secret_version"],
                use=(
                    SecretUse(row["use_name"])
                    if row["use_name"]
                    else None
                ),
                actor=row["actor"],
                outcome=row["outcome"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
~~~

### 13.1 为什么轮换后旧版本直接失效

假设动作 A 获得审批时绑定：

~~~text
HF_TOKEN version=2 fingerprint=hmac-sha256:<64-hex>
~~~

之后用户轮换为 version 3。旧 Action 不能自动改用 version 3，因为这会改变被批准的内容身份。
正确流程是：

~~~text
old action resolve v2
  -> SECRET_INACTIVE
  -> rebuild action with v3 reference
  -> recompute action hash
  -> user approves again
~~~

### 13.2 关于 SQLite sidecar

WAL 模式可能生成 `vault.sqlite-wal` 和 `vault.sqlite-shm`。它们同样属于 Vault，必须：

- 位于 `secrets/`；
- 权限收紧为 `0600`；
- 不进入 Artifact、Support Bundle 或 Git；
- 备份时与主数据库一致处理。

---

## 十四、实现统一 Redactor 与流式 byte 脱敏

> **本节类型：需要新增代码。**
>
> 需要新增：`app/secrets/redaction.py`。

完整文件：

~~~python
from __future__ import annotations

import base64
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from pydantic import BaseModel

from app.secrets.errors import SecretLeakDetectedError
from app.secrets.ports import SecretMaterial


REDACTED = "<redacted>"
REDACTED_BYTES = REDACTED.encode("utf-8")

SENSITIVE_KEY_PARTS = {
    "authorization",
    "api_key",
    "apikey",
    "token",
    "password",
    "passwd",
    "secret",
    "credential",
    "cookie",
}

_ASSIGNMENT_RE = re.compile(
    r"(?i)"
    r"([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)"
    r"[A-Z0-9_]*)"
    r"\s*=\s*([^\s,;]+)"
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
_URL_USERINFO_RE = re.compile(
    r"(?i)\b(https?://)[^/\s:@]+:[^/\s@]+@"
)


def _sanitize_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<invalid-url>"
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


class SecretRedactor:
    """同时使用已知值匹配和通用 secret-like 规则。"""

    def __init__(
        self,
        materials: Sequence[SecretMaterial] = (),
        *,
        known_values: Mapping[str, str] | None = None,
    ):
        patterns: dict[str, str] = {}
        byte_patterns: dict[bytes, str] = {}

        values = [
            (material.reference.name, material.reveal())
            for material in materials
        ]
        values.extend((known_values or {}).items())

        for name, value in values:
            variants = {value, quote(value, safe="")}
            if len(value) >= 12:
                encoded = base64.urlsafe_b64encode(
                    value.encode("utf-8")
                ).decode("ascii")
                variants.add(encoded)
                variants.add(encoded.rstrip("="))
            for variant in variants:
                if len(variant) < 8:
                    continue
                patterns[variant] = name
                byte_patterns[variant.encode("utf-8")] = name
        self._patterns = tuple(
            sorted(patterns, key=len, reverse=True)
        )
        self._pattern_names = patterns
        self._byte_patterns = tuple(
            sorted(byte_patterns, key=len, reverse=True)
        )
        self._byte_pattern_names = byte_patterns

    @classmethod
    def empty(cls) -> "SecretRedactor":
        return cls()

    @classmethod
    def from_values(
        cls,
        values: Sequence[str],
    ) -> "SecretRedactor":
        """只供测试或受信任的短生命周期边界使用。"""

        return cls(
            known_values={
                f"INLINE_SECRET_{index}": value
                for index, value in enumerate(values)
            }
        )

    @property
    def byte_patterns(self) -> tuple[bytes, ...]:
        return self._byte_patterns

    def redact_text(
        self,
        value: object,
        *,
        max_chars: int | None = None,
    ) -> str:
        text = str(value)
        for pattern in self._patterns:
            text = text.replace(pattern, REDACTED)
        text = _ASSIGNMENT_RE.sub(r"\1=<redacted>", text)
        text = _BEARER_RE.sub("Bearer <redacted>", text)
        text = _URL_USERINFO_RE.sub(r"\1<redacted>@", text)
        if text.startswith(("http://", "https://")):
            text = _sanitize_url(text)
        if max_chars is not None:
            text = text[:max_chars]
        return text

    def redact_object(
        self,
        value: Any,
        *,
        max_chars: int = 2000,
    ) -> Any:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        if isinstance(value, Mapping):
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                name = str(key)
                normalized = name.lower()
                if any(
                    part in normalized
                    for part in SENSITIVE_KEY_PARTS
                ):
                    cleaned[name] = REDACTED
                else:
                    cleaned[name] = self.redact_object(
                        item,
                        max_chars=max_chars,
                    )
            return cleaned
        if isinstance(value, (list, tuple)):
            return [
                self.redact_object(item, max_chars=max_chars)
                for item in value[:100]
            ]
        if isinstance(value, str):
            return self.redact_text(
                value,
                max_chars=max_chars,
            )
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return self.redact_text(value, max_chars=max_chars)

    def find_known_in_text(self, value: str) -> list[str]:
        return sorted(
            {
                self._pattern_names[pattern]
                for pattern in self._patterns
                if pattern in value
            }
        )

    def find_known_in_bytes(self, value: bytes) -> list[str]:
        return sorted(
            {
                self._byte_pattern_names[pattern]
                for pattern in self._byte_patterns
                if pattern in value
            }
        )

    def contains_secret(self, value: str) -> bool:
        return bool(self.find_known_in_text(value))

    def contains_secret_bytes(self, value: bytes) -> bool:
        return bool(self.find_known_in_bytes(value))

    def assert_no_known_secret(
        self,
        value: bytes,
        *,
        boundary: str,
    ) -> None:
        names = self.find_known_in_bytes(value)
        if names:
            raise SecretLeakDetectedError(
                f"{boundary} 检测到 Secret：{', '.join(names)}"
            )

    def stream(self) -> "StreamingSecretRedactor":
        return StreamingSecretRedactor(self._byte_patterns)


class StreamingSecretRedactor:
    """跨 chunk 精确匹配已知 Secret byte pattern。"""

    def __init__(self, patterns: Sequence[bytes]):
        self._patterns = tuple(
            sorted(set(patterns), key=len, reverse=True)
        )
        self._buffer = bytearray()
        self._closed = False

    def _drain(self, *, final: bool) -> bytes:
        output = bytearray()
        while self._buffer:
            current = bytes(self._buffer)
            matched = next(
                (
                    pattern
                    for pattern in self._patterns
                    if current.startswith(pattern)
                ),
                None,
            )
            if matched is not None:
                output.extend(REDACTED_BYTES)
                del self._buffer[: len(matched)]
                continue

            could_be_prefix = any(
                pattern.startswith(current)
                for pattern in self._patterns
            )
            if could_be_prefix and not final:
                break

            output.append(self._buffer[0])
            del self._buffer[0]
        return bytes(output)

    def feed(self, data: bytes) -> bytes:
        if self._closed:
            raise RuntimeError("StreamingSecretRedactor 已关闭")
        self._buffer.extend(data)
        return self._drain(final=False)

    def flush(self) -> bytes:
        if self._closed:
            return b""
        self._closed = True
        return self._drain(final=True)
~~~

### 14.1 为什么不能对每个 chunk 单独 `replace()`

错误实现：

~~~python
safe = chunk.replace(secret_bytes, b"<redacted>")
~~~

如果程序分两次输出：

~~~text
chunk 1: "hf_abcd"
chunk 2: "efgh1234"
~~~

两个 chunk 都不包含完整 Secret，原值会被写入。`StreamingSecretRedactor` 会暂存仍可能是
Secret 前缀的 byte，直到可以确认安全或完成替换。

### 14.2 已知值与启发式规则的边界

已从 Vault 注入的 Secret 必须做到确定性拦截。仓库里原本就存在、但没有登记到 Vault 的未知
凭据只能依赖文件名、`KEY=value`、Bearer 和 URL userinfo 等启发式规则。因此本阶段还要：

- 默认拒绝 Tool 读取 `.env`、`*.pem`、`*.key`、`credentials`、`secrets.json`；
- 禁止把敏感参数放入 Action args；
- 在最终验收中扫描常见 secret-like 文本；
- 发现未知凭据时要求用户手工迁入 Vault，而不是让模型自动导入。

---

## 十五、实现 SecretService 与 Factory

> **本节类型：需要新增代码。**
>
> 需要新增：`app/secrets/service.py`、`app/secrets/factory.py`。

### 15.1 `app/secrets/service.py`

完整文件：

~~~python
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.secrets.ports import SecretMaterial, SecretStore
from app.secrets.redaction import SecretRedactor
from app.secrets.schemas import (
    SecretMetadata,
    SecretReference,
    SecretUse,
)


class SecretService:
    def __init__(self, store: SecretStore):
        self.store = store
        self.store.initialize()

    def put(
        self,
        *,
        name: str,
        value: str,
        allowed_uses: list[SecretUse] | set[SecretUse],
        actor: str = "local:operator",
    ) -> SecretMetadata:
        return self.store.put(
            name=name,
            value=value,
            allowed_uses=list(allowed_uses),
            actor=actor,
        )

    def reference(self, name: str) -> SecretReference:
        return self.store.current_reference(name)

    def list_metadata(self) -> list[SecretMetadata]:
        return self.store.list_metadata()

    def revoke(
        self,
        *,
        reference: SecretReference,
        actor: str = "local:operator",
    ) -> SecretMetadata:
        return self.store.revoke(
            reference=reference,
            actor=actor,
        )

    def resolve(
        self,
        *,
        reference: SecretReference,
        use: SecretUse,
        actor: str,
    ) -> SecretMaterial:
        return self.store.resolve(
            reference=reference,
            use=use,
            actor=actor,
        )

    def resolve_current(
        self,
        *,
        name: str,
        use: SecretUse,
        actor: str,
    ) -> SecretMaterial:
        return self.resolve(
            reference=self.reference(name),
            use=use,
            actor=actor,
        )

    def build_redactor(
        self,
        *,
        actor: str,
    ) -> SecretRedactor:
        materials = self.store.active_materials_for_redaction(
            actor=actor
        )
        return SecretRedactor(materials)

    @contextmanager
    def material(
        self,
        reference: SecretReference,
        *,
        required_use: SecretUse,
        actor: str = "runtime:scoped",
    ) -> Iterator[SecretMaterial]:
        """给调用方一个结构化短生命周期边界。

        Python str 无法可靠清零；context manager 的价值是限制变量作用域，
        不是声称能从内存中物理擦除 material。
        """

        material = self.resolve(
            reference=reference,
            use=required_use,
            actor=actor,
        )
        try:
            yield material
        finally:
            del material
~~~

### 15.2 `app/secrets/factory.py`

完整文件：

~~~python
from __future__ import annotations

import threading

from app.config import settings
from app.secrets.crypto import FernetSecretCipher
from app.secrets.service import SecretService
from app.secrets.store import SqliteSecretStore


_lock = threading.Lock()
_service: SecretService | None = None


def build_secret_service() -> SecretService:
    global _service
    with _lock:
        if _service is None:
            cipher = FernetSecretCipher(
                settings.secret_master_key_path
            )
            _service = SecretService(
                SqliteSecretStore(
                    path=settings.secret_vault_db_path,
                    cipher=cipher,
                )
            )
        return _service


def reset_secret_service_for_tests() -> None:
    global _service
    with _lock:
        _service = None
~~~

Factory 不应在 Master Key 缺失时自动生成新 Key。否则 Vault 已存在但 Key 丢失时，系统会悄悄
创建一个无法解密旧数据的新 Key，把配置事故伪装成“Secret 不存在”。

---

## 十六、公开 Package API

> **本节类型：需要新增代码。**
>
> 需要新增：`app/secrets/__init__.py`。

完整文件：

~~~python
from app.secrets.errors import (
    SecretConfigurationError,
    SecretError,
    SecretInactiveError,
    SecretIntegrityError,
    SecretLeakDetectedError,
    SecretNotFoundError,
    SecretUseDeniedError,
)
from app.secrets.factory import build_secret_service
from app.secrets.ports import SecretMaterial, SecretStore
from app.secrets.redaction import (
    REDACTED,
    SecretRedactor,
    StreamingSecretRedactor,
)
from app.secrets.schemas import (
    SecretMetadata,
    SecretReference,
    SecretStatus,
    SecretUse,
)
from app.secrets.service import SecretService

__all__ = [
    "REDACTED",
    "SecretConfigurationError",
    "SecretError",
    "SecretInactiveError",
    "SecretIntegrityError",
    "SecretLeakDetectedError",
    "SecretMaterial",
    "SecretMetadata",
    "SecretNotFoundError",
    "SecretRedactor",
    "SecretReference",
    "SecretService",
    "SecretStatus",
    "SecretStore",
    "SecretUse",
    "SecretUseDeniedError",
    "StreamingSecretRedactor",
    "build_secret_service",
]
~~~

---

## 十七、修改 Settings：只保存 Secret 名称

> **本节类型：需要修改代码。**
>
> 需要修改：`app/config.py`。
>
> **迁移顺序要求**：先完成第二十九节的 Vault 初始化和旧环境变量导入，再删除下面的明文字段。

### 17.1 保留路径和名称，删除明文值

在 `Settings` 开头，把当前：

~~~python
openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
embedding_api_key: str | None = os.getenv("EMBEDDING_API_KEY")
~~~

替换为：

~~~python
@dataclass
class Settings:
    # Phase 41：Settings 只保存 Vault 路径和 Secret 名称。
    # 不读取 OPENAI_API_KEY、EMBEDDING_API_KEY 等明文环境变量。
    secret_master_key_path: Path = Path(
        os.getenv(
            "SECRET_MASTER_KEY_PATH",
            "secrets/master.key",
        )
    )
    secret_vault_db_path: Path = Path(
        os.getenv(
            "SECRET_VAULT_DB_PATH",
            "secrets/vault.sqlite",
        )
    )

    openai_api_key_secret_name: str = os.getenv(
        "OPENAI_API_KEY_SECRET_NAME",
        "OPENAI_API_KEY",
    )
    embedding_api_key_secret_name: str = os.getenv(
        "EMBEDDING_API_KEY_SECRET_NAME",
        "EMBEDDING_API_KEY",
    )
    database_url_secret_name: str = os.getenv(
        "DATABASE_URL_SECRET_NAME",
        "DATABASE_URL",
    )
    api_token_secret_name: str = os.getenv(
        "AGENT_API_TOKEN_SECRET_NAME",
        "AGENT_API_TOKEN",
    )

    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    openai_model: str = os.getenv(
        "OPENAI_MODEL",
        "mimo-v2.5-pro",
    )
~~~

保留 `load_dotenv()` 只用于非敏感配置，例如模型名、端口和目录。Phase 41 完成后，`.env`
只能包含 Secret 名称，不能再包含 Secret 明文。

### 17.2 删除其他明文字段

删除：

~~~python
api_token: str | None = os.getenv("AGENT_API_TOKEN")
database_url: str | None = os.getenv("DATABASE_URL")
~~~

原位置改成注释，提醒后续维护者：

~~~python
# Phase 41：API Token 和 DATABASE_URL 由 SecretService 按名称解析。
# 这里不能重新读取 AGENT_API_TOKEN 或 DATABASE_URL 明文。
~~~

### 17.3 修改 PostgreSQL 启动校验

把：

~~~python
if uses_postgres and not settings.database_url:
    raise ValueError("PostgreSQL backend 需要 DATABASE_URL")
~~~

替换为：

~~~python
if uses_postgres and not settings.database_url_secret_name.strip():
    raise ValueError(
        "PostgreSQL backend 需要 DATABASE_URL_SECRET_NAME"
    )
~~~

这里仅校验引用名称。Vault 是否初始化、Secret 是否存在、用途是否正确，应由
`runtime-doctor`、`readiness-check` 和真正的数据库 Composition Root 验证，不能在 import
`app.config` 时解密 Secret。

### 17.4 增加路径校验

在 Settings 实例创建后的校验区增加：

~~~python
settings.secret_master_key_path = (
    Path(
        os.path.abspath(
            settings.secret_master_key_path.expanduser()
        )
    )
)
settings.secret_vault_db_path = (
    Path(
        os.path.abspath(
            settings.secret_vault_db_path.expanduser()
        )
    )
)

if (
    settings.secret_master_key_path.parent
    != settings.secret_vault_db_path.parent
):
    raise ValueError(
        "第一版要求 Master Key 与 Vault 位于同一受控 secrets 目录"
    )

secret_root = settings.secret_master_key_path.parent
allowed_root = Path(
    os.path.abspath(settings.allowed_root.expanduser())
)
if not secret_root.is_relative_to(allowed_root):
    raise ValueError(
        "Secret 路径必须位于 ALLOWED_ROOT 内"
    )

for secret_name in (
    settings.openai_api_key_secret_name,
    settings.embedding_api_key_secret_name,
    settings.database_url_secret_name,
    settings.api_token_secret_name,
):
    if not secret_name.strip():
        raise ValueError("Secret name 配置不能为空")
~~~

同目录不是强安全要求，而是单机第一版的生命周期约束，便于统一权限、备份排除和 GC 排除。

---

## 十八、Provider 只在创建 Client 时解析 Secret

> **本节类型：需要修改代码。**
>
> 需要修改：`app/model.py`、`tests/test_model.py`。

### 18.1 替换 `app/model.py`

文件较短，可以完整替换为：

~~~python
from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr

from app.config import settings
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService


def _service(
    injected: SecretService | None,
) -> SecretService:
    if injected is not None:
        return injected
    from app.secrets.factory import build_secret_service

    return build_secret_service()


def get_chat_model(
    temperature: float = 0,
    *,
    secret_service: SecretService | None = None,
):
    material = _service(secret_service).resolve_current(
        name=settings.openai_api_key_secret_name,
        use=SecretUse.PROVIDER,
        actor="provider:chat",
    )
    model_options: dict[str, Any] = {
        "model": settings.openai_model,
        # SecretStr 防止 Provider Client repr 意外显示明文。
        "api_key": SecretStr(material.reveal()),
        "base_url": settings.openai_base_url,
        "temperature": temperature,
        "max_completion_tokens": settings.openai_max_output_tokens,
    }
    if settings.openai_thinking_mode is not None:
        model_options["extra_body"] = {
            "thinking": {
                "type": settings.openai_thinking_mode,
            }
        }
    return ChatOpenAI(**model_options)


def get_embedding_model(
    *,
    secret_service: SecretService | None = None,
):
    material = _service(secret_service).resolve_current(
        name=settings.embedding_api_key_secret_name,
        use=SecretUse.EMBEDDING,
        actor="provider:embedding",
    )
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=SecretStr(material.reveal()),
        base_url=settings.embedding_base_url,
    )
~~~

这里的“短期”表示：

- 不再保存在全局 `Settings`；
- 不进入 Prompt、State 或 Artifact；
- 只传给 Provider Client；
- Client 生命周期结束后不再由项目持有额外明文副本。

Python 字符串无法保证立刻清零，因此不能把它宣传为硬件级内存隔离。

### 18.2 修改模型测试

在 `tests/test_model.py` 中增加 Fake Service，并保留原有 output budget 测试：

~~~python
from __future__ import annotations

from app.secrets.ports import SecretMaterial
from app.secrets.schemas import SecretReference, SecretUse


CANARY = "phase41-provider-canary-value"


class FakeSecretService:
    def resolve_current(self, *, name, use, actor):
        assert name == "OPENAI_API_KEY"
        assert use == SecretUse.PROVIDER
        assert actor == "provider:chat"
        return SecretMaterial(
            reference=SecretReference(
                name=name,
                version=1,
                fingerprint="hmac-sha256:" + "a" * 64,
            ),
            allowed_uses=(SecretUse.PROVIDER,),
            _value=CANARY,
        )


def test_chat_model_resolves_provider_secret(monkeypatch):
    import app.model as model_module
    from app.config import settings

    captured: dict = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(model_module, "ChatOpenAI", fake_chat_openai)
    monkeypatch.setattr(
        settings,
        "openai_api_key_secret_name",
        "OPENAI_API_KEY",
    )

    model_module.get_chat_model(
        temperature=0,
        secret_service=FakeSecretService(),
    )

    assert captured["api_key"].get_secret_value() == CANARY
    assert CANARY not in repr(captured["api_key"])
~~~

测试允许在内存中的 Fake Client 捕获 Canary，但不得把 `captured` 打印或写入 pytest snapshot。

---

## 十九、PostgreSQL DSN 按用途解析

> **本节类型：需要修改代码。**
>
> 需要修改：`app/persistence/database.py`、`alembic/env.py`。

### 19.1 修改 `require_database_url()`

保留现有 Engine、PID 和 Lock 逻辑，只替换 URL 解析函数：

~~~python
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService


def require_database_url(
    *,
    secret_service: SecretService | None = None,
) -> str:
    if secret_service is None:
        from app.secrets.factory import build_secret_service

        secret_service = build_secret_service()

    material = secret_service.resolve_current(
        name=settings.database_url_secret_name,
        use=SecretUse.DATABASE,
        actor="database:engine",
    )
    value = material.reveal()
    parsed = make_url(value)
    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError(
            "Phase 41 DATABASE_URL Secret 必须指向 PostgreSQL"
        )
    return value
~~~

在 `build_engine()` 的 `sa.create_engine()` 参数中增加：

~~~python
_engine = sa.create_engine(
    require_database_url(),
    pool_pre_ping=True,
    hide_parameters=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout_seconds,
    connect_args={
        "options": options,
        "application_name": "paper-reproduction-copilot",
    },
)
~~~

`hide_parameters=True` 不能隐藏连接 URL 本身，所以异常消息仍必须经过统一 Redactor。

### 19.2 `alembic/env.py`

原代码仍可调用 `require_database_url()`：

~~~python
config.set_main_option(
    "sqlalchemy.url",
    require_database_url().replace("%", "%%"),
)
~~~

但不要打印 `config.get_main_option("sqlalchemy.url")`。手工排查时只能输出：

~~~python
from sqlalchemy.engine.url import make_url

safe_url = make_url(require_database_url()).render_as_string(
    hide_password=True
)
~~~

---

## 二十、API Bearer Token 不再保存在 `app.state` 明文

> **本节类型：需要修改代码。**
>
> 需要修改：`app/api/app.py`、`app/api/auth.py` 及对应 API 测试。

### 20.1 修改 App Factory

`create_api_app()` 的参数增加 `secret_service`；`api_token` 仅保留为测试兼容入口，并使用
`SecretStr` 包装：

~~~python
from pydantic import SecretStr

from app.secrets.service import SecretService


def create_api_app(
    *,
    job_service: JobService | None = None,
    artifact_catalog: ArtifactCatalog | None = None,
    artifact_delivery_service: ArtifactDeliveryService | None = None,
    api_token: str | None = None,
    secret_service: SecretService | None = None,
    service_host: Any | None = None,
    chat_service: ChatService | None = None,
    comparison_service: ComparisonService | None = None,
    rerun_service: RerunService | None = None,
) -> FastAPI:
    # 保留函数后续现有装配代码。
    if secret_service is None:
        from app.secrets.factory import build_secret_service

        secret_service = build_secret_service()

    app = FastAPI(
        title="Paper Reproduction Copilot API",
        version="1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # 只保存 Service、名称和测试 SecretStr，不保存生产明文字符串。
    app.state.secret_service = secret_service
    app.state.api_token_secret_name = (
        settings.api_token_secret_name
    )
    app.state.api_token_override = (
        SecretStr(api_token)
        if api_token is not None
        else None
    )

    # 下面继续保留原有 Job/Artifact/Chat/Resource 装配。
~~~

删除原来的：

~~~python
app.state.api_token = settings.api_token if api_token is None else api_token
~~~

### 20.2 完整替换 `app/api/auth.py`

~~~python
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, Request

from app.secrets.errors import SecretNotFoundError
from app.secrets.schemas import SecretUse


def require_api_auth(
    request: Request,
    authorization: str | None = Header(
        default=None,
        alias="Authorization",
    ),
) -> str:
    override = request.app.state.api_token_override
    if override is not None:
        expected = override.get_secret_value()
    else:
        try:
            material = (
                request.app.state.secret_service.resolve_current(
                    name=request.app.state.api_token_secret_name,
                    use=SecretUse.API_AUTH,
                    actor="api:auth",
                )
            )
            expected = material.reveal()
        except SecretNotFoundError:
            # 未配置 Token 只允许 serve 命令绑定 loopback；
            # 非 loopback 的检查仍由 serve-api 启动边界执行。
            return "api:local"

    scheme, separator, credentials = (
        authorization or ""
    ).partition(" ")
    valid = (
        separator == " "
        and scheme.lower() == "bearer"
        and secrets.compare_digest(credentials, expected)
    )
    if not valid:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "缺少或无效的 Bearer Token",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "api:token"
~~~

`serve-api` 和 `serve-stack` 的非 loopback 校验也要从“`settings.api_token` 是否有值”改成：

~~~python
from app.secrets.errors import SecretNotFoundError
from app.secrets.factory import build_secret_service


def _api_token_available() -> bool:
    try:
        build_secret_service().reference(
            settings.api_token_secret_name
        )
        return True
    except SecretNotFoundError:
        return False
~~~

非 loopback 且返回 False 时，启动必须失败。

---

## 二十一、让 Action 只保存版本化 Secret Binding

> **本节类型：需要修改代码。**
>
> 需要修改：`app/schemas.py`、`config/execution_profiles.local.json`。

### 21.1 在 `ExecutableAction` 前增加 `SecretBinding`

在 `app/schemas.py` 的 import 区增加：

~~~python
import re

from app.secrets.schemas import SecretReference
~~~

在 `ExecutableAction` 前增加：

~~~python
SECRET_ENV_NAME_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)


class SecretBinding(BaseModel):
    """Action 中只保存引用，绝不保存明文。"""

    env_name: str = Field(
        min_length=1,
        max_length=128,
        pattern=SECRET_ENV_NAME_RE.pattern,
    )
    reference: SecretReference
~~~

修改 `ExecutionProfile`，在 `allowed_action_env_keys` 后增加：

~~~python
class ExecutionProfile(BaseModel):
    # 保留前面的现有字段。

    # 普通非敏感变量仍走 env / env_overrides。
    allowed_action_env_keys: list[str] = Field(default_factory=list)

    # Phase 41：只有这里列出的 key 能由 Secret Binding 注入。
    # 该列表属于受信任 Profile，并进入 Profile Fingerprint。
    allowed_secret_env_keys: list[str] = Field(default_factory=list)
~~~

在 `validate_backend_fields()` 末尾增加：

~~~python
self.allowed_secret_env_keys = sorted(
    set(self.allowed_secret_env_keys)
)
if any(
    not SECRET_ENV_NAME_RE.fullmatch(item)
    for item in self.allowed_secret_env_keys
):
    raise ValueError("allowed_secret_env_keys 包含无效变量名")
if set(self.allowed_secret_env_keys).intersection(
    self.allowed_action_env_keys
):
    raise ValueError(
        "同一变量不能同时作为普通 env 和 Secret env"
    )
if self.backend == "oci" and self.allowed_secret_env_keys:
    raise ValueError(
        "Phase 41 第一版 OCI 不支持 Secret env；"
        "必须使用安全的容器 Secret Driver 后再开放"
    )
~~~

修改 `ExecutableAction`：

~~~python
class ExecutableAction(BaseModel):
    action_id: str
    action_type: Literal["run_command"] = "run_command"
    program: str
    args: list[str] = Field(default_factory=list)
    cwd: str
    source: Literal[
        "readme",
        "script",
        "config",
        "inferred",
        "need_confirm",
    ]
    reason: str
    timeout_seconds: int = Field(default=300, gt=0)

    # 普通非敏感值；敏感变量名仍会被 environment.py 拒绝。
    env_overrides: dict[str, str] = Field(
        default_factory=dict,
        validation_alias=AliasChoices(
            "env_overrides",
            "env_allowlist",
        ),
    )

    # Phase 41：name/version/fingerprint 会自然进入 model_dump 和 Action Hash。
    secret_bindings: list[SecretBinding] = Field(
        default_factory=list
    )

    writable_paths: list[str] = Field(default_factory=list)
    network_access: Literal["none", "outbound"] = "none"
    resource_budget: ResourceBudgetOverride | None = None
    risk: dict[str, Any] | None = None
    execution_profile_id: str
    execution_profile_fingerprint: str
    repo_patch_hash: str | None = None

    @model_validator(mode="after")
    def validate_secret_bindings(self) -> "ExecutableAction":
        env_names = [item.env_name for item in self.secret_bindings]
        if len(env_names) != len(set(env_names)):
            raise ValueError("secret_bindings env_name 不能重复")
        if set(env_names).intersection(self.env_overrides):
            raise ValueError(
                "同一 env_name 不能同时出现在普通值和 Secret Binding"
            )
        return self
~~~

修改 `ProcessRecord`，只增加键名：

~~~python
class ProcessRecord(BaseModel):
    # 保留所有现有字段。
    inherited_env_keys: list[str] = Field(default_factory=list)
    profile_env_keys: list[str] = Field(default_factory=list)
    action_env_keys: list[str] = Field(default_factory=list)
    secret_env_keys: list[str] = Field(default_factory=list)
~~~

### 21.2 Profile 示例

`config/execution_profiles.local.json` 可以增加：

~~~json
{
  "profiles": [
    {
      "profile_id": "local",
      "backend": "local",
      "workspace_root": "/data/tianshaoqi24",
      "artifact_root": "/data/tianshaoqi24/agent/paper_reproduction_copilot/runs",
      "inherited_env_keys": ["PATH", "LANG"],
      "env": {},
      "allowed_action_env_keys": [
        "CUDA_VISIBLE_DEVICES",
        "OMP_NUM_THREADS"
      ],
      "allowed_secret_env_keys": [
        "HF_TOKEN"
      ],
      "allowed_programs": [
        "python",
        "python3",
        "torchrun",
        "pytest"
      ],
      "writable_roots": ["/data/tianshaoqi24"],
      "network_policy": "deny",
      "enforcement_mode": "best_effort"
    }
  ]
}
~~~

LLM 不能修改 Profile，也不能凭空创建 SecretReference。Reference 必须来自用户或受信任
Composition Root。

### 21.3 Hash 测试

在 `tests/test_structured_action_and_approval_hash.py` 增加：

~~~python
def test_action_hash_changes_when_secret_reference_changes():
    first = _action().model_copy(
        update={
            "secret_bindings": [
                {
                    "env_name": "HF_TOKEN",
                    "reference": {
                        "name": "HF_TOKEN",
                        "version": 1,
                        "fingerprint": (
                            "hmac-sha256:" + "a" * 64
                        ),
                    },
                }
            ]
        }
    )
    second = first.model_copy(
        update={
            "secret_bindings": [
                {
                    "env_name": "HF_TOKEN",
                    "reference": {
                        "name": "HF_TOKEN",
                        "version": 2,
                        "fingerprint": (
                            "hmac-sha256:" + "b" * 64
                        ),
                    },
                }
            ]
        }
    )

    assert compute_action_hash(first.model_dump()) != (
        compute_action_hash(second.model_dump())
    )
~~~

---

## 二十二、在最小执行环境中按引用注入

> **本节类型：需要修改代码。**
>
> 需要修改：`app/execution/environment.py`。

### 22.1 扩展返回值

在 import 区增加：

~~~python
from app.secrets.redaction import SecretRedactor
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService
~~~

替换 `EnvironmentBuildResult`：

~~~python
@dataclass(frozen=True)
class EnvironmentBuildResult:
    # env 只传给 Popen，不允许 model_dump 或写入 Artifact。
    env: dict[str, str]
    runtime_dir: Path
    inherited_keys: list[str]
    profile_keys: list[str]
    action_keys: list[str]
    secret_keys: list[str]
    redactor: SecretRedactor
~~~

### 22.2 修改函数签名

下面给出完整的函数级上下文。`...` 对应当前函数里已经存在的 inherited/profile/action 普通
环境构建逻辑，不要删除；新增逻辑放在 Supervisor Owned 变量写入之后、返回值之前：

~~~python
def build_minimal_environment(
    *,
    profile: ExecutionProfile,
    action: ExecutableAction,
    run_dir: str | Path,
    execution_id: str,
    secret_service: SecretService,
) -> EnvironmentBuildResult:
    # 这五个值由当前函数已有逻辑产生。实现时保留原代码，不要真的替换为 Ellipsis。
    env: dict[str, str] = ...
    runtime_dir: Path = ...
    inherited_keys: list[str] = ...
    profile_keys: list[str] = ...
    action_keys: list[str] = ...

    secret_keys: list[str] = []
    materials = []

    if profile.backend == "oci" and action.secret_bindings:
        raise ValueError(
            "Phase 41 第一版禁止 OCI Secret Binding"
        )

    for binding in action.secret_bindings:
        key = binding.env_name
        if key not in profile.allowed_secret_env_keys:
            raise ValueError(
                f"Secret env 未被 profile 允许：{key}"
            )
        if key in SUPERVISOR_OWNED_ENV_KEYS:
            raise ValueError(
                f"Secret 不能覆盖 Supervisor 变量：{key}"
            )
        if key in env:
            raise ValueError(
                f"Secret env 与普通 env 冲突：{key}"
            )
        if not VALID_ENV_NAME.fullmatch(key):
            raise ValueError("Secret env name 无效")

        material = secret_service.resolve(
            reference=binding.reference,
            use=SecretUse.EXECUTION_ENV,
            actor=f"execution:{execution_id}",
        )
        value = material.reveal()
        if "\x00" in value:
            raise ValueError(
                f"Secret env 包含 NUL：{key}"
            )
        env[key] = value
        secret_keys.append(key)
        materials.append(material)

    return EnvironmentBuildResult(
        env=env,
        runtime_dir=runtime_dir,
        inherited_keys=sorted(inherited_keys),
        profile_keys=sorted(profile_keys),
        action_keys=sorted(action_keys),
        secret_keys=sorted(secret_keys),
        redactor=SecretRedactor(materials),
    )
~~~

为什么不把 `material` 或 `redactor` 写入 State：

- `material` 禁止 pickle；
- `redactor` 内部持有匹配模式；
- 它们都只属于当前 `ExecutionRunner.run()` 调用栈；
- 持久化层只记录 `secret_env_keys` 和 Action 中的 Reference。

---

## 二十三、让 Runner 注入 SecretService

> **本节类型：需要修改代码。**
>
> 需要修改：`app/execution/base.py`、`app/execution/registry.py`。

### 23.1 修改 `ExecutionRunner.__init__()`

~~~python
from app.secrets.service import SecretService


class ExecutionRunner(ABC):
    def __init__(
        self,
        profile: ExecutionProfile,
        *,
        secret_service: SecretService | None = None,
    ):
        self.profile = profile
        if secret_service is None:
            from app.secrets.factory import build_secret_service

            secret_service = build_secret_service()
        self.secret_service = secret_service
        self.supervisor = ProcessSupervisor()
~~~

修改 `run()` 中环境构建和 Supervisor 调用：

~~~python
env_result = build_minimal_environment(
    profile=self.profile,
    action=parsed,
    run_dir=run_dir,
    execution_id=execution_id,
    secret_service=self.secret_service,
)

result = self.supervisor.execute(
    SupervisedExecutionRequest(
        host_command=host_command,
        cwd=resolved_cwd,
        env=env_result.env,
        run_dir=Path(run_dir).resolve(),
        action_id=parsed.action_id,
        stage=stage,
        profile_id=self.profile.profile_id,
        backend=self.profile.backend,
        budget=decision.effective_budget,
        execution_id=execution_id,
    ),
    inherited_env_keys=env_result.inherited_keys,
    profile_env_keys=env_result.profile_keys,
    action_env_keys=env_result.action_keys,
    secret_env_keys=env_result.secret_keys,
    redactor=env_result.redactor,
)
~~~

`probe()` 不接受 Secret Binding，继续使用空绑定的内部 Action。Preflight 不应该为了探测环境而
提前解析训练 Token。

### 23.2 修改 `build_execution_runner()`

给 `app/execution/registry.py` 的函数增加可注入参数：

~~~python
from app.secrets.service import SecretService


def build_execution_runner(
    profile: ExecutionProfile,
    *,
    secret_service: SecretService | None = None,
) -> ExecutionRunner:
    common = {"secret_service": secret_service}
    if profile.backend == "local":
        return LocalRunner(profile, **common)
    if profile.backend == "conda":
        return CondaRunner(profile, **common)
    if profile.backend == "oci":
        return OciRunner(profile, **common)
    raise ValueError(f"未知 execution backend：{profile.backend}")
~~~

如果现有 `OciRunner.__init__()` 有额外参数，保留原参数并把 `secret_service` 传给
`super().__init__()`。

---

## 二十四、Process Log 必须先流式脱敏再落盘

> **本节类型：需要修改代码。**
>
> 需要修改：`app/execution/process_supervisor.py`。

### 24.1 修改 import

~~~python
from app.secrets.redaction import (
    SecretRedactor,
    StreamingSecretRedactor,
)
~~~

### 24.2 完整替换 `BoundedLogSink`

~~~python
class BoundedLogSink:
    """统计原始字节，但只持久化脱敏后的有界内容。"""

    def __init__(
        self,
        *,
        path: Path,
        max_file_bytes: int,
        max_preview_bytes: int,
        stream_redactor: StreamingSecretRedactor | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.max_file_bytes = max_file_bytes
        self.max_preview_bytes = max_preview_bytes
        self.bytes_seen = 0
        self.bytes_written = 0
        self.preview = bytearray()
        self.truncated = False
        self._redactor = stream_redactor
        self._file = path.open("wb")

    def _write_safe(self, data: bytes) -> None:
        if not data:
            return
        preview_remaining = (
            self.max_preview_bytes - len(self.preview)
        )
        if preview_remaining > 0:
            self.preview.extend(data[:preview_remaining])

        file_remaining = self.max_file_bytes - self.bytes_written
        if file_remaining > 0:
            chunk = data[:file_remaining]
            self._file.write(chunk)
            self.bytes_written += len(chunk)

    def consume(self, data: bytes) -> None:
        if not data:
            return
        self.bytes_seen += len(data)
        safe = (
            self._redactor.feed(data)
            if self._redactor is not None
            else data
        )
        self._write_safe(safe)
        if self.bytes_seen > self.max_file_bytes:
            self.truncated = True

    def close(self) -> None:
        if self._file.closed:
            return
        if self._redactor is not None:
            self._write_safe(self._redactor.flush())
        self._file.flush()
        os.fsync(self._file.fileno())
        self._file.close()

    def preview_text(self) -> str:
        return bytes(self.preview).decode(
            "utf-8",
            errors="replace",
        )
~~~

### 24.3 修改 `ProcessSupervisor.execute()`

函数签名增加：

~~~python
def execute(
    self,
    request: SupervisedExecutionRequest,
    *,
    inherited_env_keys: list[str] | None = None,
    profile_env_keys: list[str] | None = None,
    action_env_keys: list[str] | None = None,
    secret_env_keys: list[str] | None = None,
    redactor: SecretRedactor | None = None,
) -> ExecutionResult:
    # 下方 24.3 代码放入当前 execute()，其余监管逻辑保持不变。
    ...
~~~

创建三个 Sink 时，每个 Sink 必须得到独立 Stream：

~~~python
stdout_sink = BoundedLogSink(
    path=stdout_path,
    max_file_bytes=request.budget.max_log_bytes_per_stream,
    max_preview_bytes=request.budget.max_preview_bytes,
    stream_redactor=(redactor.stream() if redactor else None),
)
stderr_sink = BoundedLogSink(
    path=stderr_path,
    max_file_bytes=request.budget.max_log_bytes_per_stream,
    max_preview_bytes=request.budget.max_preview_bytes,
    stream_redactor=(redactor.stream() if redactor else None),
)
combined_sink = BoundedLogSink(
    path=combined_path,
    max_file_bytes=(
        request.budget.max_log_bytes_per_stream * 2
    ),
    max_preview_bytes=request.budget.max_preview_bytes * 2,
    stream_redactor=(redactor.stream() if redactor else None),
)
~~~

ProcessRecord 增加：

~~~python
record = ProcessRecord(
    # 保留现有字段。
    inherited_env_keys=sorted(inherited_env_keys or []),
    profile_env_keys=sorted(profile_env_keys or []),
    action_env_keys=sorted(action_env_keys or []),
    secret_env_keys=sorted(secret_env_keys or []),
)
~~~

三个重要结果：

1. `bytes_seen` 统计论文程序真实输出量；
2. `bytes_written` 统计脱敏后的落盘量；
3. preview 从脱敏后的 byte 构建，因此不会再通过 `ExecutionResult.stdout` 进入 State。

不要在 ProcessRecord 中记录 Secret 版本列表以外的 material，也不要记录 `request.env`。

### 24.4 OCI 第一版为什么拒绝

下面做法都不安全：

~~~text
podman run --env HF_TOKEN=secret ...
podman run --env-file /path/that/is-later-published ...
把 secret 写入 ContainerPlan JSON
~~~

命令行可能被 `ps` 读取，普通容器环境可能被 `inspect` 持久显示。因此 Phase 41 第一版明确
拒绝 OCI Secret Binding。后续若要支持，应单独实现并验证 Podman Secret Driver，而且
Secret ID、创建、挂载、撤销和崩溃清理都要纳入监管。

## 二十五、给 Resource Acquisition 增加受控凭据

> 本节类型：需要修改源代码和测试。

需要修改：

- `app/resources/schemas.py`
- `app/resources/http_downloader.py`
- `app/resources/git_fetcher.py`
- `app/resources/worker.py`
- `app/resources/request_hash.py`（通常无需改算法，但必须补回归测试）
- `tests/test_resource_schemas.py`
- `tests/test_http_resource_downloader.py`
- `tests/test_git_resource_fetcher.py`
- `tests/test_resource_request_hash.py`

### 25.1 请求只携带凭据引用

在 `app/resources/schemas.py` 的 `ResourceRequest` 前增加：

~~~python
from app.secrets.schemas import SecretReference


class ResourceCredential(ResourceModel):
    """Resource 获取时使用的凭据引用，不包含明文。

    mode 决定受控 Transport 如何使用该值。第一版只支持两个明确模式，
    不允许用户自由拼接 Header 或 Git 参数。
    """

    reference: SecretReference
    mode: Literal["bearer", "git_https_token"]
~~~

给 `ResourceRequest` 增加字段，并在已有 `model_validator` 中补交叉校验：

~~~python
class ResourceRequest(ResourceModel):
    # 保留已有字段。
    kind: ResourceKind
    source_url: str = Field(min_length=1, max_length=2048)
    expected_sha256: str | None = None
    expected_git_commit: str | None = None
    purpose: str = Field(min_length=1, max_length=500)

    # 这里只保存 name/version/fingerprint。
    credential: ResourceCredential | None = None

    @model_validator(mode="after")
    def validate_identity_requirement(self) -> "ResourceRequest":
        # 先保留当前 kind、sha256、commit 的全部校验。
        # ... existing validation ...

        if self.credential is not None:
            if (
                self.kind == "git_repository"
                and self.credential.mode != "git_https_token"
            ):
                raise ValueError(
                    "Git resource 只能使用 git_https_token credential"
                )
            if (
                self.kind != "git_repository"
                and self.credential.mode != "bearer"
            ):
                raise ValueError(
                    "HTTP resource 只能使用 bearer credential"
                )
        return self
~~~

因为 `resource_request_sha256()` 已对整个 Pydantic Model 做规范序列化，`credential`
会自然进入请求 Hash。这样用户批准“使用 Token v3 下载 checkpoint”后，即使请求被改成
Token v4，也会触发 stale approval，而不是沿用旧批准。

补测试：

~~~python
def test_resource_hash_binds_secret_reference():
    first = ResourceRequest(
        kind="checkpoint",
        source_url="https://models.example.org/model.pt",
        expected_sha256="a" * 64,
        purpose="download exact checkpoint",
        credential=ResourceCredential(
            mode="bearer",
            reference=SecretReference(
                name="MODEL_REGISTRY_TOKEN",
                version=1,
                    fingerprint="hmac-sha256:" + "b" * 64,
            ),
        ),
    )
    second = first.model_copy(
        update={
            "credential": ResourceCredential(
                mode="bearer",
                reference=SecretReference(
                    name="MODEL_REGISTRY_TOKEN",
                    version=2,
                    fingerprint="hmac-sha256:" + "c" * 64,
                ),
            )
        }
    )

    assert resource_request_sha256(first) != resource_request_sha256(second)
~~~

### 25.2 HTTP Header 由 Transport 内部构造

修改 `HttpTransportPort.stream()` 和 `HttpxTransport.stream()`，只允许 Worker 传入固定
Header 字典：

~~~python
class HttpTransportPort(Protocol):
    def stream(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> AbstractContextManager[HttpResponse]:
        ...


@contextmanager
def stream(
    self,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
) -> Iterator[HttpResponse]:
    with self._client.stream(
        method,
        url,
        headers=headers,
    ) as response:
        yield response
~~~

`download()` 增加 `authorization_bearer`，但绝不能把它放入 URL、异常或结果对象：

~~~python
def download(
    self,
    *,
    url: str,
    destination: Path,
    max_bytes: int,
    expected_sha256: str | None,
    ensure_active=None,
    authorization_bearer: str | None = None,
) -> DownloadResult:
    headers = None
    if authorization_bearer is not None:
        if "\r" in authorization_bearer or "\n" in authorization_bearer:
            raise ResourceIntegrityError("credential 含非法换行")
        headers = {
            "Authorization": f"Bearer {authorization_bearer}"
        }

    # redirect 后仍只向 allowlist + DNS policy 验证通过的目标发送 Header。
    # 若未来允许跨 host redirect，默认必须丢弃 Authorization。
    with self.transport.stream(
        "GET",
        target.canonical_url,
        headers=headers,
    ) as response:
        # 保留已有 streaming、大小和 hash 校验。
        ...
~~~

第一版建议进一步规定：携带凭据时，redirect 的 hostname 必须和初始 hostname 完全相同。
这能防止可信站点把 `Authorization` 重定向给另一个 allowlist host。

### 25.3 Git Token 使用 `GIT_ASKPASS`，不能进入 argv

不要这样做：

~~~text
git fetch https://user:token@example.org/repo.git
git -c http.extraHeader="Authorization: Bearer token" fetch ...
~~~

URL 和 argv 都可能进入进程列表、错误消息或 Git 配置。修改 `GitResourceFetcher`：

~~~python
def _env(
    self,
    isolated_home: Path,
    *,
    askpass_path: Path | None = None,
    git_token: str | None = None,
) -> dict[str, str]:
    env = {
        # 保留当前最小 Git 环境。
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
    if git_token is not None:
        if askpass_path is None:
            raise ValueError("git token 缺少 askpass helper")
        env.update(
            {
                "GIT_ASKPASS": str(askpass_path),
                "PAPER_COPILOT_GIT_USERNAME": "oauth2",
                "PAPER_COPILOT_GIT_TOKEN": git_token,
            }
        )
    return env
~~~

在 `staging_dir` 内原子写入 mode `0o700` 的固定 helper，脚本只能读取环境变量：

~~~sh
#!/bin/sh
case "$1" in
  *Username*) printf '%s\n' "$PAPER_COPILOT_GIT_USERNAME" ;;
  *Password*) printf '%s\n' "$PAPER_COPILOT_GIT_TOKEN" ;;
  *) exit 1 ;;
esac
~~~

`fetch()` 用 `try/finally` 删除 helper；`_run()` 抛错前必须通过本次 material 创建的
`SecretRedactor` 清理 `stdout/stderr`。测试替身应检查 Token 位于子进程 `env`，且不位于
argv、异常和 staging 产物。

### 25.4 Worker 是唯一解析者

修改 `ResourceWorker.__init__()`：

~~~python
from app.secrets import SecretService, SecretUse


class ResourceWorker:
    def __init__(
        self,
        *,
        # 保留已有参数。
        repository: ResourceRepository,
        blob_store: BlobStore,
        worker_id: str,
        secret_service: SecretService,
        **existing_dependencies,
    ):
        self.secret_service = secret_service
        # 保留已有初始化。
~~~

在 `_fetch()` 内用短生命周期 context 解析：

~~~python
credential = record.request.credential
if credential is None:
    return self._fetch_without_credential(record, ensure_active)

use = (
    SecretUse.RESOURCE_GIT
    if record.request.kind == "git_repository"
    else SecretUse.RESOURCE_HTTP
)
with self.secret_service.material(
    credential.reference,
    required_use=use,
) as material:
    redactor = SecretRedactor([material])
    try:
        if record.request.kind == "git_repository":
            return self.git_fetcher.fetch(
                source_url=record.request.source_url,
                expected_commit=record.request.expected_git_commit,
                staging_dir=staging,
                git_token=material.reveal(),
                redactor=redactor,
            )
        return self.downloader.download(
            url=record.request.source_url,
            destination=destination,
            max_bytes=max_bytes,
            expected_sha256=record.request.expected_sha256,
            ensure_active=ensure_active,
            authorization_bearer=material.reveal(),
        )
    except Exception as exc:
        # 不能把 transport 返回的原始异常直接写入 ResourceRecord.error。
        raise ResourceTransportUnavailable(
            redactor.redact_text(str(exc))
        ) from exc
~~~

不要让 API 路由、ResourceService、Repository 或审批逻辑解析 material。它们只处理
`ResourceCredential`，这样网络执行职责和控制面职责仍然分离。

## 二十六、把 Observability 统一到同一个 Redactor

> 本节类型：需要修改源代码和测试。

需要修改：`app/observability/redaction.py`、`app/tools/error_tools.py`、
`app/observability/json_logging.py`、`app/observability/instrumentation.py`。

现有 `app.observability.redaction` 仍保留 Key-name、URL 和长度规则；Phase 41 在其上增加
“当前进程已知 Secret 值”规则。不要在两个模块各维护一套正则。

~~~python
# app/observability/redaction.py
from __future__ import annotations

import threading
from typing import Any

from app.secrets.redaction import SecretRedactor

_LOCK = threading.RLock()
_VALUE_REDACTOR = SecretRedactor.empty()


def configure_secret_redactor(redactor: SecretRedactor) -> None:
    """替换进程级已知值集合；仅由 composition root 调用。"""

    global _VALUE_REDACTOR
    with _LOCK:
        _VALUE_REDACTOR = redactor


def _redact_known_values(text: str) -> str:
    with _LOCK:
        selected = _VALUE_REDACTOR
    return selected.redact_text(text)


def sanitize_error_message(
    value: object,
    max_chars: int = 4000,
) -> str:
    text = _redact_known_values(str(value))
    text = _SENSITIVE_ASSIGNMENT_RE.sub(
        r"\1=<redacted>", text
    )
    return text[:max_chars]


def redact(value: Any, *, max_chars: int = 2000) -> Any:
    # dict/list 的现有递归逻辑保持不变。
    if isinstance(value, str):
        safe = _redact_known_values(value)
        if safe.startswith(("http://", "https://")):
            safe = sanitize_url(safe)
        return safe[:max_chars]
    # ... existing recursive branches ...
~~~

`app/tools/error_tools.py` 删除重复的 `_SENSITIVE_ASSIGNMENT_RE` 和实现，改为：

~~~python
from app.observability.redaction import sanitize_error_message
~~~

注意：进程级 Redactor 适合 Provider、数据库和 API 等长生命周期 Secret；每次 Action 或
Resource 的临时 Secret 仍应使用调用级 Redactor。不要把已经撤销的全部历史 Secret 永久保留
在全局内存中。

结构化日志 Formatter、span event、metric attribute 和 error payload 在序列化前都调用
`redact()`。Metric label 继续只允许低基数枚举，不允许 Secret name、fingerprint 或版本。

## 二十七、给 Tool Registry 增加 Secret Canary Guard

> 本节类型：需要修改源代码和测试。

需要修改：`app/tool_contracts/registry.py`、`app/tool_contracts/inventory.py`、
`app/tool_contracts/errors.py`、`tests/test_tool_contract_registry.py`、
`tests/test_tool_contract_inventory.py`。

Phase 40 的 Tool Contract 已经限制输入、输出、副作用和调用者，但它还不知道某段普通字符串
是不是 Secret。Phase 41 在模型验证前后各增加一道**已知值检测**：

~~~python
class ToolRegistry:
    def __init__(
        self,
        *,
        secret_redactor: SecretRedactor | None = None,
    ) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._secret_redactor = (
            secret_redactor or SecretRedactor.empty()
        )

    def _contains_secret(self, value: Any) -> bool:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        return self._secret_redactor.contains_secret(encoded)
~~~

在 `invoke()` 一开始、计算输入 Hash 之前检查：

~~~python
if self._contains_secret(raw_input):
    return self._failed_result(
        definition=definition,
        context=context,
        sink=sink,
        started=started,
        started_at=started_at,
        # 不允许对含 Secret 的原始输入计算并留存普通审计 Hash。
        input_sha256=hashlib.sha256(
            b"blocked-secret-input"
        ).hexdigest(),
        failure=ToolFailure(
            code="TOOL_SECRET_INPUT_BLOCKED",
            category="policy",
            retryable=False,
            message="工具输入包含受保护凭据",
        ),
    )
~~~

Handler 返回并通过 `output_model` 校验后、生成结果和 Audit 前检查：

~~~python
safe_output = output.model_dump(mode="json")
if self._contains_secret(safe_output):
    return self._failed_result(
        # 其余公共参数沿用当前函数。
        definition=definition,
        context=context,
        sink=sink,
        started=started,
        started_at=started_at,
        input_sha256=input_sha256,
        failure=ToolFailure(
            code="TOOL_SECRET_OUTPUT_BLOCKED",
            category="policy",
            retryable=False,
            message="工具输出包含受保护凭据",
        ),
    )
~~~

Inventory 还应加入两条确定性规则：

1. `app.secrets` 下的函数永远不能自动登记为 Agent Tool；
2. 读取 `.env`、`secrets/`、Master Key 或 Secret DB 的文件工具不能暴露为
   `AGENT_READ_ONLY`。

Tool 不能调用 `SecretService.resolve()`。真正需要凭据的 Provider、Runner 和 Resource
Worker 是可信 Adapter，不是让 LLM 任意调用的 Tool。

## 二十八、保护 Chat、Prompt、Checkpoint 和 Event

> 本节类型：需要修改源代码和测试。

需要修改：`app/chat/service.py`、Chat factory、事件写入入口和对应测试。LangGraph State
Schema 通常只需确认没有 material 字段，不需要新增明文 Secret 字段。

### 28.1 用户把 Token 粘贴到 Chat 时

`ChatService` 注入 Redactor，并且必须在 request hash、Prompt 和 Repository 之前处理：

~~~python
class ChatService:
    def __init__(
        self,
        *,
        # 保留已有依赖。
        secret_redactor: SecretRedactor,
        **existing_dependencies,
    ):
        self.secret_redactor = secret_redactor
        # 保留已有初始化。

    def ask(
        self,
        *,
        job_id: str,
        question: str,
        idempotency_key: str,
    ) -> ChatAskResponse:
        normalized_question = question.strip()
        if not normalized_question:
            raise ChatConflictError("question 不能为空")

        # 此后 hash、Prompt、历史和持久化都只接触 safe_question。
        safe_question = self.secret_redactor.redact_text(
            normalized_question
        )
        request_hash = _request_sha256(job_id, safe_question)

        # context builder 和 prompt builder 改用 safe_question。
        bundle = self.context_builder.build(
            job_id=job_id,
            question=safe_question,
        )
        prompt_build = build_budgeted_chat_prompt(
            question=safe_question,
            history=history,
            memory=memory,
            bundle=bundle,
            prompt_max_chars=self.prompt_max_chars,
            history_max_chars=self.history_max_chars,
            memory_max_chars=self.memory_max_chars,
        )
        draft = self.draft_invoker(prompt_build.prompt)
        answer = self.secret_redactor.redact_text(draft.answer)

        self.repository.append_exchange(
            job_id=job_id,
            idempotency_key=key,
            request_sha256=request_hash,
            question=safe_question,
            answer=answer,
            citations=citations,
        )
~~~

这意味着用户以后看到的是：

~~~text
用户原始输入：请用 sk-live-canary-123 调 API
持久化消息：请用 <redacted> 调 API
模型 Prompt：请用 <redacted> 调 API
~~~

如果产品要求“拒绝而不是替换”，可以在 API 层返回 422；本项目第一版采用替换，避免用户
必须重新输入整条长消息。

### 28.2 Checkpoint 和 State

在写 checkpoint 前加入测试断言，而不是把 Redactor 当作允许 State 保存明文的理由：

~~~python
serialized = json.dumps(state, ensure_ascii=False, default=str)
assert not redactor.contains_secret(serialized)
~~~

正确 State 示例：

~~~json
{
  "pending_action": {
    "secret_bindings": [
      {
        "env_name": "HF_TOKEN",
        "reference": {
          "name": "huggingface-token",
          "version": 3,
          "fingerprint": "..."
        }
      }
    ]
  }
}
~~~

错误 State 示例：

~~~json
{
  "pending_action": {
    "env": {"HF_TOKEN": "hf_actual_value"}
  }
}
~~~

### 28.3 Event 和错误载荷

所有 `append_event()`、SSE payload 和 `StageError.message/details` 在写 Repository 前调用统一
`redact()`。事件里允许记录：

- `secret_name`
- `secret_version`
- `secret_fingerprint`
- `purpose`
- `outcome`

事件里禁止记录：

- Secret material
- `Authorization` Header
- 完整执行环境
- 含 userinfo/query 的 URL
- 子进程原始 stdout/stderr

## 二十九、Artifact 写入与登记前做最终泄漏检查

> 本节类型：需要修改源代码和测试。

需要修改：`app/tools/artifact_tools.py`、Artifact 发布/导出入口、
`tests/test_run_native_artifacts.py`，并新增 `tests/test_secret_artifact_boundary.py`。

### 29.1 文本 Artifact 先脱敏

给 `write_text_artifact()` 和 `write_json_artifact()` 增加可注入 Redactor：

~~~python
def write_text_artifact(
    *,
    state: dict[str, Any],
    relative_path: str,
    text: str,
    producer_node: str,
    media_type: str = "text/plain",
    redactor: SecretRedactor | None = None,
) -> tuple[Path, ArtifactRecord]:
    safe_text = (
        redactor.redact_text(text)
        if redactor is not None
        else redact(text, max_chars=max(len(text), 1))
    )
    return write_bytes_artifact(
        state=state,
        relative_path=relative_path,
        data=safe_text.encode("utf-8"),
        producer_node=producer_node,
        media_type=media_type,
        redactor=redactor,
    )
~~~

`write_json_artifact()` 先对结构调用 `observability.redact()`，再 `json.dumps()`。不要先写磁盘
再尝试覆盖，因为文件监听器、备份程序或 Blob Publisher 可能已经读到未脱敏版本。

### 29.2 二进制 Artifact 默认 fail closed

二进制不能安全地做任意字符串替换，否则会破坏 checkpoint、PDF 或压缩包。修改
`write_bytes_artifact()`：

~~~python
def write_bytes_artifact(
    *,
    # 保留已有参数。
    data: bytes,
    redactor: SecretRedactor | None = None,
    **existing_arguments,
) -> tuple[Path, ArtifactRecord]:
    if redactor is not None and redactor.contains_secret_bytes(data):
        raise ValueError(
            "Artifact payload contains protected secret material"
        )
    # 只有检查通过才执行 _atomic_write_bytes()。
    ...
~~~

### 29.3 登记已有文件前扫描

`register_existing_artifact()` 是最容易漏掉的边界，因为文件可能由旧工具直接生成。规则如下：

1. 文本类型：读取、脱敏、原子替换、再算 SHA-256；
2. 二进制类型：只检测已知 Secret bytes，命中则拒绝登记和发布；
3. 文件过大：按流扫描，不能一次读入内存；
4. 文件位于论文仓库源码目录时：**不允许原地改写**，只拒绝登记并报告路径；
5. Support bundle、ZIP 导出和 Blob publish 必须复用同一检查函数。

建议新增统一入口：

~~~python
@dataclass(frozen=True)
class SecretScanResult:
    safe: bool
    textual: bool
    replacements: int


def enforce_artifact_secret_boundary(
    path: Path,
    *,
    media_type: str,
    redactor: SecretRedactor,
    allow_text_rewrite: bool,
) -> SecretScanResult:
    """发布前最后一道边界；不返回匹配到的 Secret 内容。"""
    ...
~~~

### 29.4 实现通用流式 Leak Scanner

新增 `app/secrets/scanner.py`。Scanner 只返回命中的文件和 Secret name，不返回明文或匹配
片段；Vault 目录必须整体排除。

~~~python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.secrets.redaction import SecretRedactor


@dataclass(frozen=True, slots=True)
class SecretLeakFinding:
    path: str
    secret_names: tuple[str, ...]


class SecretLeakScanner:
    """按 chunk 扫描已知 Secret bytes，同时处理跨 chunk 匹配。"""

    def __init__(
        self,
        *,
        redactor: SecretRedactor,
        excluded_roots: tuple[Path, ...] = (),
        chunk_bytes: int = 1024 * 1024,
    ):
        if chunk_bytes < 4096:
            raise ValueError("chunk_bytes 不能小于 4096")
        self.redactor = redactor
        self.chunk_bytes = chunk_bytes
        self.excluded_roots = tuple(
            Path(os.path.abspath(item.expanduser()))
            for item in excluded_roots
        )
        self._overlap = max(
            (
                len(pattern) - 1
                for pattern in redactor.byte_patterns
            ),
            default=0,
        )

    def _is_excluded(self, path: Path) -> bool:
        absolute = Path(os.path.abspath(path))
        return any(
            absolute == root or absolute.is_relative_to(root)
            for root in self.excluded_roots
        )

    def scan_file(
        self,
        path: Path,
    ) -> SecretLeakFinding | None:
        absolute = Path(os.path.abspath(path.expanduser()))
        if self._is_excluded(absolute) or absolute.is_symlink():
            return None
        if not absolute.is_file():
            return None

        names: set[str] = set()
        carry = b""
        with absolute.open("rb") as handle:
            while True:
                chunk = handle.read(self.chunk_bytes)
                if not chunk:
                    break
                window = carry + chunk
                names.update(
                    self.redactor.find_known_in_bytes(window)
                )
                carry = (
                    window[-self._overlap :]
                    if self._overlap
                    else b""
                )

        if not names:
            return None
        return SecretLeakFinding(
            path=str(absolute),
            secret_names=tuple(sorted(names)),
        )

    def scan_roots(
        self,
        roots: list[Path],
    ) -> list[SecretLeakFinding]:
        findings: list[SecretLeakFinding] = []
        seen: set[Path] = set()
        for raw_root in roots:
            root = Path(
                os.path.abspath(raw_root.expanduser())
            )
            if self._is_excluded(root) or not root.exists():
                continue
            candidates = [root] if root.is_file() else root.rglob("*")
            for path in candidates:
                absolute = Path(os.path.abspath(path))
                if absolute in seen:
                    continue
                seen.add(absolute)
                finding = self.scan_file(absolute)
                if finding is not None:
                    findings.append(finding)
        return sorted(findings, key=lambda item: item.path)
~~~

这里故意不自动改写命中文件。Leak Scanner 的职责是发现和阻断；文本 Artifact 的原子脱敏由
Artifact Boundary 完成，源码、数据库和未知二进制必须由用户判断后处理。

## 三十、增加安全 CLI 和旧配置迁移

> 本节类型：需要修改源代码和测试。

需要修改：`app/main.py`、`.env.example`、`README.md`；新增
`tests/test_secret_cli.py`。

推荐命令：

~~~text
python -m app.main init-secret-store
python -m app.main set-secret OPENAI_API_KEY --use provider
python -m app.main list-secrets
python -m app.main revoke-secret OPENAI_API_KEY --version 1
python -m app.main secret-doctor
python -m app.main scan-secret-leaks
~~~

### 30.1 `set-secret` 必须隐藏输入

~~~python
@app.command("set-secret")
def set_secret(
    name: str = typer.Argument(...),
    use: SecretUse = typer.Option(..., "--use"),
) -> None:
    """从隐藏终端输入写入新版本；不接受 --value。"""

    value = typer.prompt(
        "Secret value",
        hide_input=True,
        confirmation_prompt=True,
    )
    service = build_secret_service()
    metadata = service.put(
        name=name,
        value=value,
        allowed_uses={use},
    )
    # 只输出非敏感 metadata。
    typer.echo(
        f"stored {metadata.reference.name} "
        f"version={metadata.reference.version} "
        f"fingerprint={metadata.reference.fingerprint[:24]}..."
    )
~~~

不要提供下面这些接口：

~~~text
set-secret --value actual-secret
show-secret --raw
export-all-secrets
GET /api/secrets/{name}/value
~~~

因为它们会让 Secret 进入 shell history、进程列表、Web 响应或录屏。

### 30.2 `secret-doctor`

Doctor 只检查：

- Master Key 和 DB 是否存在；
- 路径是否位于配置允许的 `secret_root`；
- 目录是否 `0700`、文件是否 `0600`；
- 是否存在 symlink；
- DB schema/version 是否兼容；
- Settings 引用的 Secret name/use 是否存在；
- 是否发现仍启用的旧明文环境字段。

Doctor 不解密并输出 Secret，也不把所有 material 一次加载进内存。

新增 `app/secrets/doctor.py`：

~~~python
from __future__ import annotations

import os
import stat
from pathlib import Path

from app.secrets.crypto import FernetSecretCipher
from app.secrets.schemas import SecretHealthReport, SecretStatus
from app.secrets.store import SqliteSecretStore


LEGACY_PLAINTEXT_ENV_NAMES = (
    "OPENAI_API_KEY",
    "EMBEDDING_API_KEY",
    "AGENT_API_TOKEN",
    "DATABASE_URL",
)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _private_regular_file(path: Path) -> bool:
    if not path.exists() or path.is_symlink():
        return False
    info = path.lstat()
    return stat.S_ISREG(info.st_mode) and not (
        stat.S_IMODE(info.st_mode) & 0o077
    )


def inspect_secret_health(
    *,
    key_path: Path,
    vault_path: Path,
    allowed_root: Path,
) -> SecretHealthReport:
    """只读取安全状态和 Metadata；绝不返回 material。"""

    key = _absolute(key_path)
    vault = _absolute(vault_path)
    root = _absolute(allowed_root)
    secret_root = key.parent
    issues: list[str] = []

    if secret_root != vault.parent:
        issues.append("key 和 vault 不在同一目录")
    if not secret_root.is_relative_to(root):
        issues.append("secret root 位于 ALLOWED_ROOT 外")

    directory_ok = False
    if secret_root.exists() and not secret_root.is_symlink():
        info = secret_root.lstat()
        directory_ok = stat.S_ISDIR(info.st_mode) and not (
            stat.S_IMODE(info.st_mode) & 0o077
        )
    if not directory_ok:
        issues.append("secret root 必须是权限 0700 的普通目录")

    key_ok = _private_regular_file(key)
    vault_ok = _private_regular_file(vault)
    if not key_ok:
        issues.append("master key 缺失、类型错误或权限不是 0600")
    if not vault.exists():
        issues.append("vault 尚未初始化")
    elif not vault_ok:
        issues.append("vault 类型错误或权限不是 0600")

    active_count = 0
    vault_initialized = key_ok and vault_ok and directory_ok
    if vault_initialized:
        try:
            # list_metadata() 不解密 value，只读取版本、用途和状态。
            store = SqliteSecretStore(
                path=vault,
                cipher=FernetSecretCipher(key),
            )
            store.initialize()
            active_count = sum(
                item.status == SecretStatus.ACTIVE
                for item in store.list_metadata()
            )
        except Exception as exc:
            # 只记录异常类型，避免第三方异常夹带 DSN/路径内容。
            issues.append(
                f"vault schema/integrity check failed: "
                f"{type(exc).__name__}"
            )
            vault_initialized = False

    legacy_names = [
        name
        for name in LEGACY_PLAINTEXT_ENV_NAMES
        if os.getenv(name)
    ]
    if legacy_names:
        issues.append(
            "仍存在旧明文环境变量："
            + ",".join(sorted(legacy_names))
        )

    return SecretHealthReport(
        ok=not issues,
        vault_initialized=vault_initialized,
        key_permissions_ok=key_ok and directory_ok,
        vault_permissions_ok=vault_ok and directory_ok,
        active_secret_count=active_count,
        issues=issues,
    )
~~~

注意：这里允许输出旧环境变量的**名称**，但绝不能读取并拼接它们的值。Settings 中引用的
Secret name/use 是否齐全，可以在 readiness 中逐个调用 `service.reference(name)` 并只记录
缺失名称。

### 30.3 迁移旧 `.env`

安全迁移顺序：

1. 先 `init-secret-store`；
2. 用隐藏输入分别写入 `OPENAI_API_KEY`、`EMBEDDING_API_KEY`、`AGENT_API_TOKEN` 和
   `DATABASE_URL`；
3. 修改 `.env`，只保留 `*_SECRET_NAME`；
4. 重启 API、Worker 和 CLI 进程；
5. 从当前 shell 执行 `unset OPENAI_API_KEY API_TOKEN DATABASE_URL`；
6. 运行 `secret-doctor` 和泄漏扫描；
7. 确认无依赖后轮换旧 Provider/API Token。

`.env.example` 示例：

~~~dotenv
SECRET_MASTER_KEY_PATH=secrets/master.key
SECRET_VAULT_DB_PATH=secrets/vault.sqlite

OPENAI_API_KEY_SECRET_NAME=OPENAI_API_KEY
EMBEDDING_API_KEY_SECRET_NAME=EMBEDDING_API_KEY
AGENT_API_TOKEN_SECRET_NAME=AGENT_API_TOKEN
DATABASE_URL_SECRET_NAME=DATABASE_URL
~~~

### 30.4 接入其余 CLI 命令

在 `app/main.py` import 区增加：

~~~python
from pathlib import Path

import typer

from app.secrets.crypto import create_master_key_file
from app.secrets.doctor import inspect_secret_health
from app.secrets.factory import build_secret_service
from app.secrets.scanner import SecretLeakScanner
~~~

然后在现有 Typer `app` 上增加：

~~~python
@app.command("init-secret-store")
def init_secret_store() -> None:
    key_path = settings.secret_master_key_path
    vault_path = settings.secret_vault_db_path

    # Vault 已存在而 Key 丢失时绝不能创建新 Key，否则旧密文永久不可解。
    if vault_path.exists() and not key_path.exists():
        raise typer.BadParameter(
            "Vault 已存在但 Master Key 缺失；请从安全备份恢复 Key"
        )
    if not key_path.exists():
        create_master_key_file(key_path)

    # Service 构造会初始化空 Vault，并执行路径、权限和 Schema 校验。
    build_secret_service()
    typer.echo("secret store initialized")


@app.command("list-secrets")
def list_secrets() -> None:
    for metadata in build_secret_service().list_metadata():
        reference = metadata.reference
        uses = ",".join(
            item.value for item in metadata.allowed_uses
        )
        typer.echo(
            f"{reference.name} v{reference.version} "
            f"status={metadata.status.value} "
            f"uses={uses} "
            f"fingerprint={reference.fingerprint[:24]}..."
        )


@app.command("revoke-secret")
def revoke_secret(
    name: str,
    version: int = typer.Option(..., "--version", min=1),
) -> None:
    service = build_secret_service()
    current = service.reference(name)
    if current.version != version:
        # 第一版只允许撤销当前 active version；历史版本已经 superseded。
        raise typer.BadParameter(
            "指定版本不是当前 active version"
        )
    metadata = service.revoke(reference=current)
    typer.echo(
        f"revoked {metadata.reference.name} "
        f"v{metadata.reference.version}"
    )


@app.command("secret-doctor")
def secret_doctor() -> None:
    report = inspect_secret_health(
        key_path=settings.secret_master_key_path,
        vault_path=settings.secret_vault_db_path,
        allowed_root=settings.allowed_root,
    )
    typer.echo(
        f"secret health: {'ready' if report.ok else 'not-ready'}"
    )
    typer.echo(
        f"active_secret_count={report.active_secret_count}"
    )
    for issue in report.issues:
        typer.echo(f"- {issue}")
    if not report.ok:
        raise typer.Exit(code=1)


def _default_secret_scan_roots() -> list[Path]:
    """只扫描项目已知持久化面，不扫描 Vault 本身。"""

    return [
        settings.runs_dir,
        settings.output_dir,
        settings.checkpoint_db_path,
        settings.embedding_cache_db_path,
        settings.job_db_path,
        settings.artifact_catalog_db_path,
        settings.artifact_local_store_dir,
        settings.resource_db_path,
        settings.chat_db_path,
        settings.rerun_db_path,
        settings.retention_db_path,
    ]


@app.command("scan-secret-leaks")
def scan_secret_leaks(
    roots: list[Path] | None = typer.Option(
        None,
        "--root",
        help="可重复指定；省略时扫描项目已知持久化面",
    ),
) -> None:
    service = build_secret_service()
    # 只在本命令生命周期内解密 active Secret，命令结束即释放引用。
    redactor = service.build_redactor(actor="cli:leak-scan")
    scanner = SecretLeakScanner(
        redactor=redactor,
        excluded_roots=(
            settings.secret_master_key_path.parent,
        ),
    )
    findings = scanner.scan_roots(
        roots or _default_secret_scan_roots()
    )
    if not findings:
        typer.echo("no known secret material found")
        return

    for finding in findings:
        # 只打印路径和 Secret name，不打印内容片段。
        typer.echo(
            f"{finding.path}: "
            f"{','.join(finding.secret_names)}"
        )
    raise typer.Exit(code=2)
~~~

教程代码中禁止用 `metadata.model_dump_json()` 整体打印，避免未来 Schema 误加入敏感字段后
自动暴露。

## 三十一、Composition Root：只创建一次 Service，按职责注入

> 本节类型：需要修改源代码和测试。

不要在每个函数里临时 `build_secret_service()`。在 CLI/API/Worker 的 Composition Root 创建
一次 Store 和 Service，再注入具体 Adapter：

~~~python
def build_runtime_dependencies() -> RuntimeDependencies:
    secret_service = build_secret_service()

    # 长生命周期值只注册到进程级 Redactor，不把 material 放入容器对象。
    process_redactor = build_process_secret_redactor(
        secret_service=secret_service,
        configured_names={
            settings.openai_api_key_secret_name,
            settings.embedding_api_key_secret_name,
            settings.api_token_secret_name,
            settings.database_url_secret_name,
        },
    )
    configure_secret_redactor(process_redactor)

    return RuntimeDependencies(
        secret_service=secret_service,
        process_redactor=process_redactor,
        execution_runner=build_execution_runner(
            secret_service=secret_service,
        ),
        resource_worker=build_resource_worker(
            secret_service=secret_service,
        ),
        chat_service=build_chat_service(
            secret_redactor=process_redactor,
        ),
    )
~~~

这里需要把**生命周期**分清：

- `SecretStore`：进程级，持有 DB 连接配置，不持有所有明文；
- `SecretService`：进程级，执行用途和版本校验；
- Provider/API/DB material：只在创建对应 Client 或验证请求时短暂解析；
- Action/Resource material：只在一次执行或下载期间存在；
- State、Repository、Artifact、Event：永远只接触 Reference 或脱敏值。

## 三十二、增加 Store、加密和权限测试

> 本节类型：需要新增测试代码。

新增 `tests/test_secret_store.py`。下面是一组可直接落地的核心测试；函数名应和第九至十三节
最终实现保持一致：

~~~python
from __future__ import annotations

import os
import sqlite3

import pytest

from app.secrets.crypto import (
    FernetSecretCipher,
    create_master_key_file,
)
from app.secrets.errors import (
    SecretConfigurationError,
    SecretInactiveError,
    SecretIntegrityError,
)
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService
from app.secrets.store import SqliteSecretStore


@pytest.fixture
def secret_service(tmp_path):
    root = tmp_path / "secrets"
    key_path = root / "master.key"
    create_master_key_file(key_path)
    cipher = FernetSecretCipher(key_path)
    store = SqliteSecretStore(
        path=root / "vault.sqlite",
        cipher=cipher,
    )
    return SecretService(store)


def test_store_round_trip_does_not_persist_plaintext(
    secret_service,
):
    canary = "phase41-store-canary-7Qw9"
    metadata = secret_service.put(
        name="PROVIDER_KEY",
        value=canary,
        allowed_uses={SecretUse.PROVIDER},
    )

    with secret_service.material(
        metadata.reference,
        required_use=SecretUse.PROVIDER,
    ) as material:
        assert material.reveal() == canary
        assert canary not in repr(material)
        assert str(material) == "<redacted>"

    database_bytes = secret_service.store.path.read_bytes()
    assert canary.encode() not in database_bytes


def test_master_key_and_database_permissions(tmp_path):
    root = tmp_path / "secrets"
    key_path = root / "master.key"
    create_master_key_file(key_path)

    assert os.stat(root).st_mode & 0o777 == 0o700
    assert os.stat(key_path).st_mode & 0o777 == 0o600


def test_master_key_rejects_symlink(tmp_path):
    target = tmp_path / "real-key"
    target.write_bytes(b"not-a-valid-fernet-key")
    link = tmp_path / "master.key"
    link.symlink_to(target)

    with pytest.raises(SecretConfigurationError):
        FernetSecretCipher(link)


def test_rotation_invalidates_old_reference(secret_service):
    first = secret_service.put(
        name="PROVIDER_KEY",
        value="old-value-7Qw9",
        allowed_uses={SecretUse.PROVIDER},
    )
    second = secret_service.put(
        name="PROVIDER_KEY",
        value="new-value-8Rx0",
        allowed_uses={SecretUse.PROVIDER},
    )

    assert second.reference.version == first.reference.version + 1
    with pytest.raises(SecretInactiveError):
        with secret_service.material(
            first.reference,
            required_use=SecretUse.PROVIDER,
        ):
            pass


def test_ciphertext_tampering_fails_closed(
    secret_service,
):
    metadata = secret_service.put(
        name="PROVIDER_KEY",
        value="tamper-canary-7Qw9",
        allowed_uses={SecretUse.PROVIDER},
    )
    with sqlite3.connect(
        secret_service.store.path
    ) as connection:
        row = connection.execute(
            "SELECT ciphertext FROM secret_versions "
            "WHERE name = ? AND version = ?",
            (
                metadata.reference.name,
                metadata.reference.version,
            ),
        ).fetchone()
        damaged = bytearray(row[0])
        damaged[-1] ^= 1
        connection.execute(
            "UPDATE secret_versions SET ciphertext = ? "
            "WHERE name = ? AND version = ?",
            (
                bytes(damaged),
                metadata.reference.name,
                metadata.reference.version,
            ),
        )

    with pytest.raises(SecretIntegrityError):
        with secret_service.material(
            metadata.reference,
            required_use=SecretUse.PROVIDER,
        ):
            pass
~~~

还要补以下边界：

- 非法 Secret name 被拒绝；
- 空值和过大值被拒绝；
- `allowed_uses` 不匹配被拒绝；
- revoked version 不能解析；
- fingerprint 被篡改时 fail closed；
- 并发轮换不会产生重复 version；
- Store 不允许复制、pickle 或在异常中打印 material。

## 三十三、增加普通与流式 Redaction 测试

> 本节类型：需要新增测试代码。

新增 `tests/test_secret_redaction.py`：

~~~python
from app.secrets.redaction import SecretRedactor


def test_redactor_replaces_known_value_anywhere():
    secret = "phase41-redaction-canary-7Qw9"
    redactor = SecretRedactor.from_values([secret])

    value = f"prefix={secret}; url=/callback/{secret}/done"
    safe = redactor.redact_text(value)

    assert secret not in safe
    assert safe.count("<redacted>") == 2


def test_stream_redactor_handles_secret_split_across_chunks():
    secret = "phase41-stream-canary-7Qw9"
    redactor = SecretRedactor.from_values([secret])
    stream = redactor.stream()

    chunks = [
        b"before phase41-stream-",
        b"canary-",
        b"7Qw9 after",
    ]
    output = b"".join(stream.feed(chunk) for chunk in chunks)
    output += stream.flush()

    assert secret.encode() not in output
    assert b"before " in output
    assert b" after" in output


def test_two_log_streams_must_not_share_stream_state():
    secret = "phase41-independent-stream-7Qw9"
    redactor = SecretRedactor.from_values([secret])
    stdout = redactor.stream()
    stderr = redactor.stream()

    stdout_value = stdout.feed(secret[:10].encode())
    stderr_value = stderr.feed(b"ordinary stderr")
    stdout_value += stdout.feed(secret[10:].encode())
    stdout_value += stdout.flush()
    stderr_value += stderr.flush()

    assert secret.encode() not in stdout_value
    assert b"ordinary stderr" in stderr_value


def test_redactor_does_not_over_redact_short_common_values():
    # SecretRedactor.from_values() 应拒绝过短 material，避免把普通文本全部替换。
    redactor = SecretRedactor.from_values(["abc"])
    assert redactor.redact_text("abc is a common token") == (
        "abc is a common token"
    )
~~~

最后一个测试对应一个重要实现规则：低于最小长度的 Secret 不能可靠做 value-aware Redaction。
推荐在 `put()` 时直接拒绝少于 8 个字符的值，而不是静默不保护。

新增 `tests/test_secret_scanner.py`，验证文件扫描同样处理跨 chunk 边界，并排除 Vault：

~~~python
from app.secrets.redaction import SecretRedactor
from app.secrets.scanner import SecretLeakScanner


def test_scanner_detects_split_secret_and_excludes_vault(
    tmp_path,
):
    secret = "phase41-scanner-canary-7Qw9"
    redactor = SecretRedactor.from_values([secret])
    vault_root = tmp_path / "secrets"
    vault_root.mkdir()
    (vault_root / "vault.sqlite").write_text(secret)

    public_root = tmp_path / "runs"
    public_root.mkdir()
    # 让 Secret 从第 4090 byte 开始，跨越 Scanner 的 4096-byte chunk。
    leaked = public_root / "execution.log"
    leaked.write_bytes(b"x" * 4090 + secret.encode())

    scanner = SecretLeakScanner(
        redactor=redactor,
        excluded_roots=(vault_root,),
        chunk_bytes=4096,
    )
    findings = scanner.scan_roots(
        [public_root, vault_root]
    )

    assert [item.path for item in findings] == [str(leaked)]
    assert findings[0].secret_names == ("INLINE_SECRET_0",)
~~~

## 三十四、增加 Provider、API、数据库和执行注入测试

> 本节类型：需要新增/修改测试代码。

新增或修改：

- `tests/test_model.py`
- `tests/test_api_auth.py`
- `tests/test_database_secret.py`
- `tests/test_execution_secret_injection.py`

### 34.1 Provider 测试

不发真实网络请求，只注入 Fake Store 和 Fake Client Factory：

~~~python
def test_chat_model_resolves_provider_secret_only_at_factory(
    fake_secret_service,
    monkeypatch,
):
    metadata = fake_secret_service.put(
        name="OPENAI_API_KEY",
        value="provider-canary-7Qw9",
        allowed_uses={SecretUse.PROVIDER},
    )
    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("app.model.ChatOpenAI", FakeChatOpenAI)
    get_chat_model(
        temperature=0,
        secret_service=fake_secret_service,
    )

    assert (
        captured["api_key"].get_secret_value()
        == "provider-canary-7Qw9"
    )
    assert "provider-canary-7Qw9" not in repr(
        metadata.reference
    )
~~~

### 34.2 API Auth 测试

验证请求 Header 可以参与恒定时间比较，但不会进入 `app.state`、错误响应或日志：

~~~python
def test_auth_failure_does_not_echo_token(
    client,
    caplog,
):
    token = "api-canary-invalid-7Qw9"
    response = client.get(
        "/api/jobs",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert token not in response.text
    assert token not in caplog.text
~~~

### 34.3 子进程能使用 Secret，但所有记录都看不到

测试程序只打印环境变量；Supervisor 必须让进程读到值，同时把输出脱敏：

~~~python
def test_execution_injects_secret_but_redacts_all_logs(
    tmp_path,
    fake_secret_service,
):
    canary = "execution-canary-7Qw9"
    reference = fake_secret_service.put(
        name="TRAINING_TOKEN",
        value=canary,
        allowed_uses={SecretUse.EXECUTION_ENV},
    ).reference
    action = ExecutableAction(
        action_id="action-secret-test",
        program=sys.executable,
        args=[
            "-c",
            (
                "import os; "
                "print(os.environ['TRAINING_TOKEN']); "
                "raise SystemExit(3)"
            ),
        ],
        cwd=str(tmp_path),
        source="script",
        reason="Phase 41 execution injection test",
        secret_bindings=[
            SecretBinding(
                env_name="TRAINING_TOKEN",
                reference=reference,
            )
        ],
        execution_profile_id=runner.profile.profile_id,
        execution_profile_fingerprint=(
            compute_execution_profile_fingerprint(
                runner.profile
            )
        ),
    )

    result = runner.run(
        action.model_dump(),
        run_dir=str(tmp_path / "run"),
        stage="phase41-test",
    )
    record = ProcessRecord.model_validate_json(
        Path(result["process_record_path"]).read_text(
            encoding="utf-8"
        )
    )

    assert result["returncode"] == 3
    assert canary not in result["stdout"]
    assert canary not in result["stderr"]
    assert canary.encode() not in Path(record.stdout_path).read_bytes()
    assert canary.encode() not in Path(
        record.combined_log_path
    ).read_bytes()
    serialized = record.model_dump_json()
    assert canary not in serialized
    assert record.secret_env_keys == ["TRAINING_TOKEN"]
~~~

还要测试：

- 未在 Profile allowlist 的 env name 被拒绝；
- ordinary env 和 secret binding 同名时被拒绝；
- Secret 轮换后旧 Action 得到 `stale_secret_reference`，不能执行；
- 用新引用重建 Action 后 action hash 改变，必须重新审批；
- 进程启动失败时 material 也不会进入 ProcessRecord；
- stdout 和 stderr 在任意 chunk 边界下都脱敏；
- OCI Action 携带 Secret Binding 时返回明确 policy error。

## 三十五、增加跨边界 Canary 扫描测试

> 本节类型：需要新增测试代码。这是 Phase 41 最重要的回归测试。

新增 `tests/test_secret_canary_boundary.py`。测试不只检查函数返回值，还要在一次最小任务后扫描
所有持久化边界：

~~~python
from __future__ import annotations

import sqlite3
from pathlib import Path


TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".log",
    ".yaml",
    ".yml",
    ".toml",
}


def assert_canary_absent_from_tree(
    root: Path,
    canary: bytes,
) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        # Vault ciphertext 和 Master Key 不属于公开持久化面；它们有独立加密测试。
        if "secrets" in path.parts:
            continue
        if path.suffix in TEXT_SUFFIXES or path.stat().st_size < 2_000_000:
            assert canary not in path.read_bytes(), str(path)


def assert_canary_absent_from_sqlite(
    database: Path,
    canary: bytes,
) -> None:
    # 直接扫描 DB/WAL/SHM bytes，能覆盖 ORM 未枚举字段。
    for path in [
        database,
        database.with_name(database.name + "-wal"),
        database.with_name(database.name + "-shm"),
    ]:
        if path.exists():
            assert canary not in path.read_bytes(), str(path)


def test_secret_canary_never_crosses_persistence_boundary(
    phase41_runtime,
):
    canary = b"phase41-global-canary-7Qw9"
    phase41_runtime.store_secret(canary.decode())

    # 依次触发 Chat、Tool、Action、日志、StageError、Event、Artifact、Checkpoint。
    phase41_runtime.exercise_all_boundaries()

    assert_canary_absent_from_tree(
        phase41_runtime.runs_dir,
        canary,
    )
    assert_canary_absent_from_tree(
        phase41_runtime.artifact_cache_dir,
        canary,
    )
    for database in phase41_runtime.persistence_databases:
        assert_canary_absent_from_sqlite(database, canary)
~~~

测试注意事项：

1. Canary 必须是专用随机字符串，不能使用真实 API Key；
2. 不扫描加密 Vault 和 Master Key，是因为密文测试已单独确认明文不存在；
3. 必须关闭数据库连接或执行 checkpoint，确保 WAL 内容已经可读；
4. PostgreSQL 模式用查询各文本/JSON 列的测试替代本地文件扫描；
5. 失败信息只输出命中的文件路径，不能输出 Secret material；
6. CI 日志中也不能打印 Canary。

Phase 17 已有 `secret_canary_not_leaked` Eval Case，可以把本测试的结果转换为 Observation，继续
复用现有安全评分，而不是另建一套评测报告。

## 三十六、CLI 单元测试

> 本节类型：需要新增测试代码。

新增 `tests/test_secret_cli.py`：

~~~python
from typer.testing import CliRunner

from app.config import settings
from app.main import app
from app.secrets.crypto import create_master_key_file
from app.secrets.factory import (
    build_secret_service,
    reset_secret_service_for_tests,
)
from app.secrets.schemas import SecretUse

runner = CliRunner()


def configure_test_secret_paths(
    monkeypatch,
    tmp_path,
) -> None:
    root = tmp_path / "secrets"
    monkeypatch.setattr(
        settings,
        "secret_master_key_path",
        root / "master.key",
    )
    monkeypatch.setattr(
        settings,
        "secret_vault_db_path",
        root / "vault.sqlite",
    )
    reset_secret_service_for_tests()


def build_test_secret_service(tmp_path):
    key_path = tmp_path / "secrets" / "master.key"
    if not key_path.exists():
        create_master_key_file(key_path)
    return build_secret_service()


def test_set_secret_uses_hidden_prompt(monkeypatch, tmp_path):
    configure_test_secret_paths(monkeypatch, tmp_path)
    runner.invoke(app, ["init-secret-store"])

    result = runner.invoke(
        app,
        ["set-secret", "PROVIDER_KEY", "--use", "provider"],
        input="phase41-cli-canary-7Qw9\nphase41-cli-canary-7Qw9\n",
    )

    assert result.exit_code == 0
    assert "phase41-cli-canary-7Qw9" not in result.stdout
    assert "PROVIDER_KEY" in result.stdout


def test_list_secrets_only_returns_metadata(monkeypatch, tmp_path):
    configure_test_secret_paths(monkeypatch, tmp_path)
    # 通过 Service 写入 fixture，避免在测试输出中展示输入过程。
    service = build_test_secret_service(tmp_path)
    service.put(
        name="PROVIDER_KEY",
        value="phase41-list-canary-7Qw9",
        allowed_uses={SecretUse.PROVIDER},
    )

    result = runner.invoke(app, ["list-secrets"])

    assert result.exit_code == 0
    assert "PROVIDER_KEY" in result.stdout
    assert "phase41-list-canary-7Qw9" not in result.stdout


def test_cli_has_no_raw_secret_export_command():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "show-secret" not in result.stdout
    assert "export-all-secrets" not in result.stdout
~~~

## 三十七、推荐测试命令

先运行 Phase 41 小范围测试：

~~~bash
python -m pytest \
  tests/test_secret_store.py \
  tests/test_secret_redaction.py \
  tests/test_secret_scanner.py \
  tests/test_secret_cli.py \
  tests/test_model.py \
  tests/test_api_auth.py \
  tests/test_database_secret.py \
  tests/test_execution_secret_injection.py \
  tests/test_secret_artifact_boundary.py \
  tests/test_secret_canary_boundary.py -q
~~~

再运行被改动边界的回归测试：

~~~bash
python -m pytest \
  tests/test_process_supervisor.py \
  tests/test_execution_runners.py \
  tests/test_resource_schemas.py \
  tests/test_resource_request_hash.py \
  tests/test_http_resource_downloader.py \
  tests/test_git_resource_fetcher.py \
  tests/test_resource_worker.py \
  tests/test_tool_contract_registry.py \
  tests/test_tool_contract_inventory.py \
  tests/observability \
  tests/test_chat_service.py \
  tests/test_chat_memory.py \
  tests/test_run_native_artifacts.py -q
~~~

最后运行全量回归：

~~~bash
python -m pytest
~~~

静态检查：

~~~bash
python -m ruff check app tests
python -m compileall -q app tests
~~~

如果项目 Python 环境中缺少 `cryptography`，先重新安装当前项目依赖；不要在系统 Python 和
项目虚拟环境之间混装。

## 三十八、手工验收：从初始化到轮换

> 本节类型：操作验证，不新增代码。以下命令都在项目根目录
> `/data/tianshaoqi24/agent/paper_reproduction_copilot` 执行。

### 38.1 初始化本地 Vault

~~~bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m app.main init-secret-store
python -m app.main secret-doctor
~~~

预期：

- `secrets/` 权限为 `0700`；
- `secrets/master.key` 和 `secrets/secrets.db` 权限为 `0600`；
- Doctor 输出 `ready`；
- 输出中没有 Master Key 和任何 Secret material。

检查权限：

~~~bash
stat -c '%a %n' secrets secrets/master.key secrets/secrets.db
~~~

### 38.2 写入项目需要的 Secret

~~~bash
python -m app.main set-secret OPENAI_API_KEY --use provider
python -m app.main set-secret EMBEDDING_API_KEY --use embedding
python -m app.main set-secret AGENT_API_TOKEN --use api_auth
~~~

终端会出现隐藏输入提示。不要把值直接写进命令。然后查看 Metadata：

~~~bash
python -m app.main list-secrets
~~~

预期只看到 name、version、fingerprint、allowed uses、状态和时间。

### 38.3 修改 `.env` 引用

只写 Secret name：

~~~dotenv
OPENAI_API_KEY_SECRET_NAME=OPENAI_API_KEY
EMBEDDING_API_KEY_SECRET_NAME=EMBEDDING_API_KEY
AGENT_API_TOKEN_SECRET_NAME=AGENT_API_TOKEN
~~~

删除旧的 `OPENAI_API_KEY=...`、`API_TOKEN=...` 等明文字段。重启服务，确认 readiness
成功；Provider 可以正常调用，API Bearer Auth 可以正常验证。

### 38.4 验证执行环境与日志脱敏

创建一个仅用于验收的 `execution_env` Secret：

~~~bash
python -m app.main set-secret PHASE41_TRAINING_TOKEN --use execution_env
~~~

在测试 Action 中绑定：

~~~json
{
  "env_name": "PHASE41_TRAINING_TOKEN",
  "reference": {
    "name": "PHASE41_TRAINING_TOKEN",
    "version": 1,
    "fingerprint": "以 list-secrets 输出为准"
  }
}
~~~

Action 命令可以故意打印该环境变量。审批并执行后检查：

~~~bash
rg -n --hidden --glob '!secrets/**' '你刚才输入的验收值' .
~~~

预期 `rg` 没有结果。Execution log 中对应位置显示 `<redacted>`，ProcessRecord 只出现
`PHASE41_TRAINING_TOKEN` 这个 Key 名。

注意：上面的搜索命令会把测试值写入 shell history。实际验收更推荐使用项目提供的
`scan-secret-leaks`，它从 Vault 内存中构建检测器，不把明文放进 argv：

~~~bash
python -m app.main scan-secret-leaks
~~~

### 38.5 验证 Chat 泄漏边界

在 Web Chat 中输入包含验收 Secret 的一句话，例如“请检查这个凭据是否可用”。不要使用真实
生产 Token。刷新页面并查询历史，预期用户消息和回答都只显示 `<redacted>`。随后执行：

~~~bash
python -m app.main scan-secret-leaks
~~~

预期 Chat DB、Memory、Prompt Trace、Event 和 Artifact 均无命中。

### 38.6 验证轮换导致旧批准失效

1. 创建引用 `PHASE41_TRAINING_TOKEN v1` 的 Action；
2. 让流程停在 `human_review_node -> interrupt()`；
3. 执行 `set-secret PHASE41_TRAINING_TOKEN --use execution_env` 写入 v2；
4. 恢复旧审批；
5. 预期 Executor 返回 `stale_secret_reference`，不启动进程；
6. 重新 Build Action，让它引用 v2；
7. 预期 Action Hash 改变，系统要求重新审批；
8. 新审批完成后才允许执行。

这一步验证了“审批的是具体动作加具体 Secret 版本”，不是永久批准某个 Secret name。

### 38.7 验证撤销

~~~bash
python -m app.main revoke-secret PHASE41_TRAINING_TOKEN --version 2
python -m app.main secret-doctor
~~~

任何仍引用 v2 的 Action 和 Resource Request 都应 fail closed。历史 State 可以保留 v2 的
Reference 用于审计，但不能再解析出 material。

## 三十九、故障注入清单

> 本节类型：操作验证，不新增功能代码。

逐项注入以下故障，确认错误稳定、可理解且不泄漏：

| 故障 | 预期结果 |
|---|---|
| 删除 `master.key` | readiness 失败，已有 Vault 不可自动生成新 Key 覆盖 |
| 修改 Master Key 一个字节 | 所有解密 fail closed，错误中无 ciphertext/material |
| 把 `master.key` 改成 `0644` | `secret-doctor` 失败，不继续启动生产服务 |
| 将 `master.key` 换成 symlink | 路径安全检查拒绝 |
| 篡改 ciphertext | `SecretIntegrityError`，不返回部分明文 |
| 使用错误 `allowed_use` | `SecretUseDenied` |
| 引用旧版本 | `SecretInactiveError` |
| 引用 revoked 版本 | `SecretRevoked` |
| Action 普通 env 覆盖 secret env | Schema/Policy 拒绝 |
| 子进程分三段打印 Token | stdout/stderr/combined 全部脱敏 |
| Tool 输出 Token | `TOOL_SECRET_OUTPUT_BLOCKED` |
| Chat 输入 Token | 持久化与 Prompt 中为 `<redacted>` |
| Artifact 二进制含 Token bytes | 拒绝登记和发布 |
| HTTP 认证跨 host redirect | 丢弃凭据或拒绝 redirect |
| Git 命令失败并回显环境 | 错误先脱敏再持久化 |
| OCI Action 带 Secret | 明确拒绝，不降级到不安全 argv/env |

不要只验证“程序报错了”，还要验证：

1. 没有启动副作用；
2. 错误码稳定；
3. retryable/terminal 分类正确；
4. Event、Log、State、Artifact 和 Audit 都没有 Canary；
5. 修复条件清楚，例如“重新初始化权限”或“重建 Action 并重新审批”。

## 四十、常见实现错误与修复方式

### 40.1 只在日志 Formatter 脱敏

问题：原始值可能已经进入 Checkpoint、DB、Artifact 或 Tool Result。

修复：在数据进入每个持久化边界**之前**处理；Formatter 只是最后一道防线。

### 40.2 用普通 SHA-256 作为短 Secret fingerprint

问题：攻击者可以离线枚举常见 Token/密码并比对 Hash。

修复：用 Master Key 派生的 HMAC Key 计算 fingerprint，并保持固定长度。

### 40.3 轮换后仍允许解析旧版本

问题：旧 Action 和旧 Approval 可以继续使用已替换凭据。

修复：第一版采用单活跃版本；轮换后旧引用稳定返回 `SecretInactiveError`。

### 40.4 把 Token 放进命令行

问题：`ps`、shell history、ProcessRecord 和错误栈都可能看到。

修复：本地/Conda 用受控子进程 env；Git 用 `GIT_ASKPASS`；OCI 暂不支持，不能偷偷降级。

### 40.5 把完整环境写入 ProcessRecord

问题：即使 Artifact 层脱敏，Record 已经泄漏。

修复：只记录 inherited/profile/action/secret **key names**，不记录 value。

### 40.6 Stream 每个 chunk 独立替换

问题：Secret 跨 chunk 时不会命中。

修复：保留 `max_secret_length - 1` 的尾部窗口，并为每条输出流创建独立状态。

### 40.7 为测试提供 `show-secret`

问题：测试辅助接口最终很容易被误带进生产 CLI/API。

修复：测试直接注入内存 Store；生产命令永远只显示 Metadata。

### 40.8 把 Vault 当成操作系统隔离

问题：同一 Unix 用户、root 或已被接管的 Python 进程仍可能读取 Master Key 和内存。

修复：明确威胁模型。Phase 41 解决静态存储、误日志、误持久化和普通工具越权，不声称抵御
主机完全失陷。后续可迁移到 OS Keyring、TPM、Vault/KMS 或独立凭据代理。

## 四十一、本阶段完成标准

只有同时满足以下条件，Phase 41 才算完成：

- [ ] 本地 Vault 使用认证加密，Master Key 与 DB 权限正确且拒绝 symlink；
- [ ] Settings、State、Action、Approval、Resource、Event 和 Artifact 不保存明文 Secret；
- [ ] Secret Reference 包含 name、version 和 HMAC fingerprint；
- [ ] Action/Resource Hash 绑定完整 Reference，轮换后旧批准失效；
- [ ] Provider、DB、API Auth、Runner 和 Resource Worker 按用途短暂解析 material；
- [ ] 本地/Conda Runner 只通过最小环境注入，ProcessRecord 只保存 env key；
- [ ] stdout、stderr 和 combined log 能处理跨 chunk Secret；
- [ ] Tool Registry 能阻断含已知 Secret 的输入和输出；
- [ ] Chat、Prompt、Memory、Checkpoint、StageError、Event 和 Telemetry 统一脱敏；
- [ ] Artifact 在写入、登记、发布和导出前执行 Secret Boundary；
- [ ] CLI 只接受隐藏输入，不提供 raw show/export；
- [ ] Canary 测试覆盖本地文件、SQLite/WAL、日志、Artifact 和 State；
- [ ] 小范围测试、受影响回归、全量 pytest 和 Ruff 全部通过；
- [ ] `secret-doctor`、轮换、撤销和 stale approval 手工验收通过；
- [ ] 项目概览和 Python 源码参考同步更新到 Phase 41 实际实现。

## 四十二、本阶段涉及的 Agent 知识点

### 42.1 Capability Security

Agent 不直接持有“万能 Token”，而是得到一个受用途、版本和执行边界限制的 Reference。真正
解析 material 的是可信 Adapter。

### 42.2 Taint Tracking 的工程化近似

Python 没有自动的信息流类型系统，因此本阶段用以下组合近似追踪敏感数据：

- 专用 `SecretMaterial` 类型；
- 明确的解析入口；
- 依赖注入；
- value-aware Redactor；
- 持久化边界 Guard；
- Canary 回归测试。

### 42.3 Approval Binding

审批对象不只绑定命令，还绑定 Secret 的具体版本和 fingerprint。任何 credential 轮换都会改变
动作身份，必须重建并重新批准。

### 42.4 Fail Closed

无法确定是否安全时不执行、不发布、不降级。例如 OCI Secret 暂未安全实现，就明确拒绝，而
不是把值塞进 argv 继续运行。

### 42.5 Defense in Depth

单一 Redactor 不足以保证安全。Schema 不存值、Store 加密、用途限制、最短生命周期、边界扫描
和最终日志脱敏共同组成纵深防御。

## 四十三、下一阶段建议

Phase 41 实现并验证后，优先进入路线图中的 **Phase 42：对话决策评测**，再进入
**Phase 43：Planner / Executor / Verifier 职责分离**。

先做 Phase 42 的原因是：Secret 和 Tool Contract 已经建立了明确安全不变量，下一步应把这些
不变量固化成可重复的对话决策 Golden Case。例如：

1. 用户说“直接运行”时，Chat 不能绕过 Proposal、Risk Check 和人工审批；
2. Artifact 中的 Prompt Injection 不能扩大工具权限；
3. 用户在对话中粘贴 Secret 时，Prompt、Memory、Event 和回答均不得泄漏；
4. stale Action、stale Secret Reference 和重复 Decision 必须返回稳定结果；
5. 切换模型或 Provider 后，越权率和证据引用门禁仍需达到同一阈值。

有了这条评测基线，Phase 43 才能安全地拆分角色权限：Reader/Planner 只读，Executor 只执行
已审批 Action，Verifier 独立验证，Chat Agent 不持有 Vault、Shell 和写文件能力。

三个阶段最终组成的安全链为：

~~~text
Tool Contract
  -> Secret Reference + Purpose
  -> Conversation Decision Golden Eval
  -> Role Capability Policy
  -> Hash-bound Human Approval
  -> Supervised Side Effect
  -> Redacted Audit + Artifact
~~~

在 Phase 42/43 之前不建议急着做 Plugin 或通用浏览器 Agent，因为它们会显著扩大工具和外部凭据
边界；先把最小权限打牢，后续扩展的回归风险会小很多。
