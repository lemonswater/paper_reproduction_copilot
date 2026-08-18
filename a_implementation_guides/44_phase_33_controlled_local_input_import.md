# Phase 33：受控本地输入导入（Controlled Local Input Import）

> 本章是在 Phase 32 已完成之后的下一阶段实现教程。
>
> 本章会给出需要修改或新增的文件、完整核心代码、测试代码、测试命令和手工验收步骤；本教程本身不会直接修改 `app/`、`tests/` 或 `web/`。

---

## 一、为什么下一阶段优先做本地输入导入

> **本节类型：设计说明，不修改项目代码。**

Phase 32 完成后，系统已经具备：

```text
论文与仓库的受控远程 Resource 获取
异步 Job、Checkpoint、恢复与人工决策
受控命令编辑、stale decision 防护
Artifact 发布、对象存储和证据化 Chat Agent
单机 Web Console 与后端部署闭环
```

但创建新复现任务时，Web Console 仍要求用户提供：

```text
Paper PDF HTTPS URL
Git repository HTTPS URL
Exact commit SHA
```

真实使用时，论文和代码往往已经位于本机，例如：

```text
/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf
/data/tianshaoqi24/PST-Convolution-main/
```

如果仍要求用户先把它们上传到 HTTPS 服务，不仅麻烦，还会让一个单机单用户系统缺少最基本的输入闭环。

但是，本地导入不能简单写成：

```python
# 错误示例：不要让 Job 或 Agent 直接持有任意宿主机路径。
state["paper_path"] = user_input
state["repo_path"] = user_input
```

这样会绕过 Phase 24～29 已经建立的边界：

- 任意绝对路径可能读取 `.env`、SSH key 或系统文件；
- 软链接可能从允许目录跳到目录外；
- 用户确认后，源文件仍可能被替换；
- Git 工作区可能有未提交修改，无法用 commit 精确表示；
- Job 记录的是可变路径，而不是不可变内容身份；
- OCI、Workspace、Artifact 和 Chat Agent 会出现第二套输入协议；
- 后续无法证明“用户批准的输入”和“Agent 实际读取的输入”一致。

因此，本阶段最值得做的不是“路径表单”，而是：

```text
受限路径
  -> 安全检查
  -> 项目内不可变暂存快照
  -> 用户确认快照 hash / commit
  -> 绑定审批的 ResourceRequest
  -> Resource Worker 再校验
  -> BlobStore 发布
  -> Job 只接收 resource_id
```

这补齐的是系统入口，不是另起一套旁路。

---

## 二、本阶段完成后的能力

> **本节类型：目标说明，不修改项目代码。**

完成后应满足：

1. Web 可以在“远程 URL”和“本机服务端路径”之间切换；
2. 本地路径必须是绝对路径，并位于显式 allowlist root 内；
3. 路径链中的软链接会被拒绝；
4. PDF 会先复制到项目内 staging，再校验 magic、可解析性、大小和 SHA-256；
5. Git 输入必须是 clean 的仓库根目录；
6. Git 仓库会被固化为 bundle，并绑定 exact commit 与 bundle SHA-256；
7. 原始本地绝对路径不会写入 Resource DB、Event、Artifact 或日志；
8. 浏览器先看到脱敏预览，再确认 `preview_sha256`；
9. 确认动作使用 `preview_sha256` 防止 stale preview；
10. Local Import 最终仍生成普通 `ResourceRecord`；
11. Resource approval 绑定完整 `request_sha256`；
12. Resource Worker 使用本地快照时不会调用网络；
13. Worker 在发布前再次验证 staged snapshot SHA-256；
14. 发布后 Job 仍只使用 `paper_resource_id` 和 `repo_resource_id`；
15. 本地快照最终进入现有 content-addressed BlobStore；
16. 发布成功后删除大 payload，仅保留小型 manifest/commit 记录用于审计和幂等重放；
17. 远程 URL Resource 的既有行为和测试保持不变。

---

## 三、本阶段明确不做

> **本节类型：范围说明，不修改项目代码。**

```text
不把浏览器上传的大文件直接塞进 API 进程内存
不实现分片上传、断点续传或上传进度条
不允许任意 file:// URL
不让 Agent 自己选择宿主机路径
不自动导入 dirty Git 工作区
不自动 commit、stash、reset 或清理用户仓库
不跟随 Git submodule
不自动获取 Git LFS 对象
不导入任意 checkpoint；本阶段只做 PDF 和 Git repository
不为本地输入建立第二套 Job schema
不绕过 Resource approval、Worker 和 BlobStore
不引入 Redis、消息队列、多用户 RBAC 或远程文件浏览器
不把绝对路径放入 telemetry label、Event 或 Artifact
```

浏览器中的“本地路径”是 **API 所在主机上的路径**，不是访问者电脑上的路径。当前项目按单机单用户部署，因此这是有意义且足够简单的第一版。

---

## 四、核心协议与安全边界

> **本节类型：架构说明，不修改项目代码。**

### 4.1 两步协议

本阶段使用两步协议，而不是“输入路径后立即运行”：

```text
POST /v1/local-imports/inspect
  输入：kind + source_path + purpose
  输出：import_id + source_label + size + content hash + commit + preview hash

POST /v1/local-imports/{import_id}/commit
  输入：expected_preview_sha256
  输出：已经 queued 或 published 的 Resource
```

第一步只创建项目内快照。第二步确认的是这个快照，而不是仍在变化的原始路径。

### 4.2 四层身份

```text
source_path
    仅用于 inspect 请求处理，不持久化。

snapshot_sha256
    暂存 payload 的字节身份。

preview_sha256
    绑定 import_id、kind、label、大小、snapshot hash、commit 和 purpose。

request_sha256
    绑定正式 ResourceRequest；ResourceApproval 继续绑定它。
```

对于 Git 还要增加：

```text
git_commit
    表示源码语义身份。

snapshot_sha256
    表示这次 bundle 文件的字节身份。
```

commit 相同不代表任意 bundle 字节一定相同，所以两者不能互相替代。

### 4.3 数据流

```text
Web local path form
       |
       v
LocalImportService.inspect
       |- allowlist containment
       |- no-symlink path walk
       |- PDF secure copy / Git clean bundle
       |- content hash + type validation
       `- local import manifest
                 |
                 v
          browser preview
                 |
        confirm preview_sha256
                 |
                 v
LocalImportService.commit
       |- reload + recompute preview hash
       |- recheck payload hash
       |- deterministic idempotency key
       |- ResourceService.submit
       |- write compact commit record
       `- ResourceService.approve(request_sha256)
                 |
                 v
ResourceWorker
       |- claim + fencing + heartbeat
       |- copy local staged payload to claim staging
       |- verify snapshot hash again
       |- validate kind
       |- publish to BlobStore
       |- mark Resource published
       `- remove large local import payload
                 |
                 v
Job create: paper_resource_id + repo_resource_id
```

### 4.4 为什么不把本地路径直接加入 `ResourceRequest`

正式 `ResourceRequest` 会进入数据库、hash、审批、Event 和公开视图。若把绝对路径直接放进去，会泄露宿主机目录结构，也会把可变路径误当成资源身份。

本教程让正式请求只保存：

```text
source_type = local_import
local_import_id = imp_<random-id>
source_label = 仅文件名或仓库目录名
local_snapshot_sha256 = 快照 hash
expected_git_commit = exact commit（Git only）
```

原始 `source_path` 在 inspect 请求结束后即退出业务对象。

---

## 五、文件清单

> **本节类型：实施清单。**

新增后端文件：

```text
app/resources/local_import_schemas.py
app/resources/local_import.py
app/api/local_import_routes.py
```

修改后端文件：

```text
.env.example
.gitignore
app/config.py
app/resources/schemas.py
app/resources/request_hash.py
app/resources/publisher.py
app/resources/service.py
app/resources/worker.py
app/workspace/repo_capsule.py
app/api/resource_routes.py
app/api/app.py
```

新增后端测试：

```text
tests/test_local_import_service.py
tests/test_local_import_api.py
tests/test_local_import_worker.py
```

修改已有后端测试：

```text
tests/test_resource_schemas.py
tests/test_resource_request_hash.py
tests/test_resource_worker.py（如构造函数使用严格 mock）
```

新增前端文件：

```text
web/src/components/LocalImportWizard.tsx
web/tests/local-import-wizard.test.tsx
```

修改前端文件：

```text
web/src/api/types.ts
web/src/api/client.ts
web/src/components/NewSessionPanel.tsx
web/src/styles/app.css
```

本阶段不修改 LangGraph 拓扑，也不增加 Agent node。它扩展的是 Agent 的可信输入面。

---

## 六、增加本地导入配置

> **本节类型：需要修改项目代码。**
>
> 需要修改：`.env.example`、`app/config.py`。

### 6.1 修改 `.env.example`

在 Phase 29 Resource 配置附近新增：

```dotenv
# Phase 33：本地输入导入。
# 多个允许根目录使用 Linux PATH 分隔符“:”。生产时尽量写窄，不要配置 /。
LOCAL_IMPORT_ALLOWED_ROOTS=/data/tianshaoqi24

# staging 必须位于 ALLOWED_ROOT 下，不使用系统 /tmp。
LOCAL_IMPORT_STAGING_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/resources/local_imports

# inspect 后未 commit 的快照最多保留 24 小时。
LOCAL_IMPORT_TTL_SECONDS=86400

# Git bundle 上限。第一版限制为 2 GiB，可按机器磁盘情况收紧。
LOCAL_IMPORT_GIT_MAX_BYTES=2147483648
```

更安全的实际配置示例：

```dotenv
LOCAL_IMPORT_ALLOWED_ROOTS=/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf:/data/tianshaoqi24/PST-Convolution-main
```

不要配置：

```dotenv
LOCAL_IMPORT_ALLOWED_ROOTS=/
```

### 6.2 修改 `app/config.py` 的路径解析 helper

在 `_env_path()` 下方新增：

```python
def _env_paths(
    name: str,
    default: str,
) -> tuple[Path, ...]:
    """解析由 os.pathsep 分隔的路径列表。

    Linux 的 os.pathsep 是 ``:``。这里不使用逗号，避免路径名中
    偶然出现逗号时产生歧义。空项会被忽略。
    """

    raw_value = os.getenv(name, default)
    values = tuple(
        Path(item.strip())
        for item in raw_value.split(os.pathsep)
        if item.strip()
    )
    if not values:
        raise ValueError(f"{name} 至少需要一个目录")
    return values
```

`app/config.py` 已经导入 `os` 和 `Path`，不需要重复 import。

### 6.3 在 `Settings` 的 Resource 配置后新增字段

把下面代码放在 `resource_poll_seconds` 附近：

```python
    # Phase 33：本地路径仅在 inspect 阶段使用。
    # 正式 ResourceRequest 不保存这些绝对路径。
    local_import_allowed_roots: tuple[Path, ...] = _env_paths(
        "LOCAL_IMPORT_ALLOWED_ROOTS",
        "/data/tianshaoqi24",
    )
    local_import_staging_root: Path = Path(
        os.getenv(
            "LOCAL_IMPORT_STAGING_ROOT",
            (
                "/data/tianshaoqi24/agent/"
                "paper_reproduction_copilot/resources/local_imports"
            ),
        )
    )
    local_import_ttl_seconds: int = int(
        os.getenv("LOCAL_IMPORT_TTL_SECONDS", "86400")
    )
    local_import_git_max_bytes: int = int(
        os.getenv(
            "LOCAL_IMPORT_GIT_MAX_BYTES",
            str(2 * 1024 * 1024 * 1024),
        )
    )
```

### 6.4 在 `app/config.py` 底部增加配置校验

放在 Phase 29 Resource 目录校验之后：

```python
# Phase 33：Local Import staging 必须位于全局 allowed_root 中。
settings.local_import_staging_root.mkdir(
    parents=True,
    exist_ok=True,
)

_allowed_root = settings.allowed_root.expanduser().resolve()
_local_staging = (
    settings.local_import_staging_root
    .expanduser()
    .resolve()
)
if (
    _local_staging == _allowed_root
    or _allowed_root not in _local_staging.parents
):
    raise ValueError(
        "LOCAL_IMPORT_STAGING_ROOT 必须严格位于 ALLOWED_ROOT 下"
    )

if settings.local_import_ttl_seconds <= 0:
    raise ValueError("LOCAL_IMPORT_TTL_SECONDS 必须大于 0")

if settings.local_import_git_max_bytes <= 0:
    raise ValueError("LOCAL_IMPORT_GIT_MAX_BYTES 必须大于 0")

for configured_root in settings.local_import_allowed_roots:
    # 不自动创建用户输入目录；拼错配置时应在启动阶段失败。
    if configured_root.is_symlink():
        raise ValueError(
            "LOCAL_IMPORT_ALLOWED_ROOTS 不能包含符号链接根目录："
            f"{configured_root}"
        )
    resolved_root = configured_root.expanduser().resolve()
    if not resolved_root.is_dir():
        raise ValueError(
            "LOCAL_IMPORT_ALLOWED_ROOTS 中的目录不存在："
            f"{configured_root}"
        )
```

这里允许 input root 本身位于 `/data/tianshaoqi24/`，但 `LocalImportStore` 仍会单独拒绝从自己的 staging 目录再次导入。

### 6.5 修改 `.gitignore`

增加：

```gitignore
# Phase 33 local input snapshots and import metadata
resources/local_imports/
```

本地快照和脱敏 metadata 都属于运行时数据，不应提交到 Git。

---

## 七、扩展 Resource 来源身份

> **本节类型：需要修改项目代码。**
>
> 需要修改：`app/resources/schemas.py`。

现有 `ResourceRequest` 假设所有输入都有 HTTPS `source_url`。本阶段需要兼容旧记录，同时增加本地快照来源。

### 7.1 增加类型与正则

在 `ResourceKind` 附近新增：

```python
ResourceSourceType = Literal[
    "remote_url",
    "local_import",
]

LOCAL_IMPORT_ID_RE = re.compile(r"^imp_[0-9a-f]{32}$")
```

### 7.2 用下面的完整版本替换 `ResourceRequest`

```python
class ResourceRequest(ResourceModel):
    """Resource 的不可变请求身份。

    旧数据库记录没有 source_type，默认值 ``remote_url`` 可以继续读取。
    本地导入绝不保存原始绝对路径，只保存 import_id、脱敏 label 和
    staged snapshot hash。
    """

    kind: ResourceKind
    source_type: ResourceSourceType = "remote_url"

    # remote_url 专用字段。
    source_url: str | None = Field(
        default=None,
        min_length=1,
        max_length=2048,
    )

    # local_import 专用字段。source_label 只能是 basename，不能是路径。
    local_import_id: str | None = Field(
        default=None,
        pattern=r"^imp_[0-9a-f]{32}$",
    )
    source_label: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    local_snapshot_sha256: str | None = None

    expected_sha256: str | None = None
    expected_git_commit: str | None = None
    purpose: str = Field(min_length=1, max_length=500)

    @field_validator(
        "expected_sha256",
        "local_snapshot_sha256",
    )
    @classmethod
    def validate_sha(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if not SHA256_RE.fullmatch(lowered):
            raise ValueError("SHA-256 必须是 64 位小写十六进制")
        return lowered

    @field_validator("expected_git_commit")
    @classmethod
    def validate_commit(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if not COMMIT_RE.fullmatch(lowered):
            raise ValueError("expected_git_commit 必须是完整 commit SHA")
        return lowered

    @field_validator("source_label")
    @classmethod
    def validate_source_label(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("source_label 不能为空")
        if "/" in normalized or "\\" in normalized:
            raise ValueError("source_label 只能是 basename，不能包含路径分隔符")
        if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
            raise ValueError("source_label 不能包含控制字符")
        return normalized

    @model_validator(mode="after")
    def validate_identity_requirement(self) -> "ResourceRequest":
        if self.source_type == "remote_url":
            if self.source_url is None:
                raise ValueError("remote_url Resource 必须提供 source_url")
            if any(
                value is not None
                for value in (
                    self.local_import_id,
                    self.source_label,
                    self.local_snapshot_sha256,
                )
            ):
                raise ValueError("remote_url Resource 不能携带 local import 字段")
        else:
            if self.kind == "checkpoint":
                raise ValueError("Phase 33 暂不支持本地 checkpoint 导入")
            if self.source_url is not None:
                raise ValueError("local_import Resource 不能保存 source_url")
            if (
                self.local_import_id is None
                or self.source_label is None
                or self.local_snapshot_sha256 is None
            ):
                raise ValueError(
                    "local_import 必须绑定 import_id、source_label 和 snapshot hash"
                )

        if self.kind == "git_repository":
            if self.expected_git_commit is None:
                raise ValueError("Git resource 必须指定 exact commit")
            if self.expected_sha256 is not None:
                # Git 的源码身份由 exact commit 表示；local bundle 的字节身份
                # 单独放在 local_snapshot_sha256，避免改变旧字段语义。
                raise ValueError("Git request 不使用 expected_sha256")
        elif self.kind == "checkpoint":
            if self.expected_sha256 is None:
                raise ValueError("Checkpoint 必须在下载前指定 expected_sha256")
            if self.expected_git_commit is not None:
                raise ValueError("非 Git resource 不能指定 expected_git_commit")
        else:
            if self.expected_git_commit is not None:
                raise ValueError("PDF 不能指定 expected_git_commit")

        if self.source_type == "local_import" and self.kind == "paper_pdf":
            if self.expected_sha256 != self.local_snapshot_sha256:
                raise ValueError(
                    "本地 PDF 的 expected_sha256 必须等于 snapshot hash"
                )
        return self
```

为什么保留 `source_url` 而不是直接改名为 `source_locator`：

- 旧 SQLite/PostgreSQL `request_json` 可以继续反序列化；
- 远程 API 和已有测试不必一次性大改；
- 本地来源通过独立字段表达，不伪造 HTTPS URL；
- 公开视图稍后使用统一的 sanitized locator。

数据库表不需要迁移，因为 Request 和 Manifest 当前都以 JSON 存储；但是必须跑旧 Resource 回归测试，确认默认值兼容历史 JSON。

---

## 八、统一请求 hash 与脱敏来源 locator

> **本节类型：需要修改项目代码。**
>
> 需要修改：`app/resources/request_hash.py`。

### 8.1 保留 `canonicalize_url()`，在它下方新增本地 locator helper

```python
def canonicalize_local_import_locator(raw: str) -> str:
    """规范化脱敏 local-import URI。

    URI 中只能出现随机 import_id 和 basename，绝不能出现原始绝对路径。
    """

    parsed = urlsplit(raw.strip())
    if parsed.scheme.lower() != "local-import":
        raise ValueError("本地来源必须使用 local-import scheme")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("local-import URI 禁止 userinfo")
    if parsed.query or parsed.fragment:
        raise ValueError("local-import URI 禁止 query 和 fragment")

    import_id = parsed.hostname or ""
    if not re.fullmatch(r"imp_[0-9a-f]{32}", import_id):
        raise ValueError("local-import URI 缺少合法 import_id")

    label = unquote(parsed.path.lstrip("/"))
    if (
        not label
        or "/" in label
        or "\\" in label
        or any(ord(char) < 32 or ord(char) == 127 for char in label)
    ):
        raise ValueError("local-import URI 包含非法 source label")

    encoded_label = quote(label, safe="")
    return f"local-import://{import_id}/{encoded_label}"


def resource_source_locator(request: ResourceRequest) -> str:
    """从 ResourceRequest 生成可公开的脱敏来源 URI。"""

    if request.source_type == "remote_url":
        if request.source_url is None:
            raise ValueError("remote_url request 缺少 source_url")
        return canonicalize_url(request.source_url)

    if request.local_import_id is None or request.source_label is None:
        raise ValueError("local_import request 身份不完整")
    raw = (
        f"local-import://{request.local_import_id}/"
        f"{quote(request.source_label, safe='')}"
    )
    return canonicalize_local_import_locator(raw)


def canonicalize_resource_locator(raw: str) -> str:
    """Publisher 对所有来源 URI 做最终防御性规范化。"""

    scheme = urlsplit(raw.strip()).scheme.lower()
    if scheme == "https":
        return canonicalize_url(raw)
    if scheme == "local-import":
        return canonicalize_local_import_locator(raw)
    raise ValueError("不支持的 Resource source locator")
```

同时在文件顶部增加：

```python
import re
```

### 8.2 替换 `resource_request_sha256()`

```python
def resource_request_sha256(
    request: ResourceRequest,
) -> str:
    """对 ResourceRequest 做确定性 hash。

    remote_url 先规范化 URL；local_import 没有原始路径，直接对结构化
    import identity 做 canonical JSON hash。
    """

    normalized = request
    if request.source_type == "remote_url":
        if request.source_url is None:
            raise ValueError("remote_url request 缺少 source_url")
        normalized = request.model_copy(
            update={
                "source_url": canonicalize_url(request.source_url),
            }
        )

    payload = normalized.model_dump(mode="json")
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

注意：不要从 hash 中排除 `source_label` 或 `purpose`。用户批准的是完整请求，而不仅是 payload 字节。

---

## 九、新增 Local Import Schema

> **本节类型：需要新增项目代码和测试。**
>
> 需要新增：`app/resources/local_import_schemas.py`。

新建完整文件：

```python
from __future__ import annotations

"""Phase 33 Local Import 的持久化与公开 Schema。

这里刻意不在 Manifest 中保存 source_path。绝对路径只存在于一次 inspect
请求的内存对象中，避免进入 DB、Event、Artifact 和日志。
"""

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

LocalImportKind = Literal["paper_pdf", "git_repository"]


class LocalImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalImportInspectRequest(LocalImportModel):
    kind: LocalImportKind
    source_path: str = Field(min_length=1, max_length=4096)
    purpose: str = Field(min_length=1, max_length=500)
    expected_git_commit: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{40,64}$",
    )

    @field_validator("expected_git_commit")
    @classmethod
    def normalize_commit(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None

    @model_validator(mode="after")
    def validate_kind_fields(self) -> LocalImportInspectRequest:
        if self.kind == "paper_pdf" and self.expected_git_commit is not None:
            raise ValueError("PDF inspect 不能提供 expected_git_commit")
        return self


class LocalImportManifest(LocalImportModel):
    manifest_version: Literal["phase33-v1"] = "phase33-v1"
    import_id: str = Field(pattern=r"^imp_[0-9a-f]{32}$")
    kind: LocalImportKind
    source_label: str = Field(min_length=1, max_length=255)

    # 只能是下面两个固定 basename 之一，不能由 API 任意指定路径。
    payload_name: Literal["paper.pdf", "repository.bundle"]
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)
    media_type: str = Field(min_length=1, max_length=200)
    git_commit: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40,64}$",
    )
    purpose: str = Field(min_length=1, max_length=500)
    created_at: datetime
    expires_at: datetime
    preview_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_kind_identity(self) -> LocalImportManifest:
        if self.kind == "paper_pdf":
            if self.payload_name != "paper.pdf" or self.git_commit is not None:
                raise ValueError("paper import manifest 身份不一致")
        else:
            if (
                self.payload_name != "repository.bundle"
                or self.git_commit is None
            ):
                raise ValueError("git import manifest 身份不一致")
        return self


class LocalImportPreview(LocalImportModel):
    """可以返回浏览器的脱敏预览。"""

    import_id: str
    kind: LocalImportKind
    source_label: str
    snapshot_sha256: str
    size_bytes: int
    media_type: str
    git_commit: str | None = None
    purpose: str
    expires_at: datetime
    preview_sha256: str


class LocalImportCommitBody(LocalImportModel):
    expected_preview_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )


class LocalImportCommitRecord(LocalImportModel):
    record_version: Literal["phase33-v1"] = "phase33-v1"
    import_id: str
    resource_id: str
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    committed_by: str = Field(min_length=1, max_length=200)
    committed_at: datetime


def compute_preview_sha256(payload: dict) -> str:
    """计算不包含 preview_sha256 自身的 canonical JSON hash。"""

    canonical = {
        key: value
        for key, value in payload.items()
        if key != "preview_sha256"
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=(
            lambda value: value.isoformat()
            if isinstance(value, datetime)
            else str(value)
        ),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def manifest_to_preview(
    manifest: LocalImportManifest,
) -> LocalImportPreview:
    return LocalImportPreview(
        import_id=manifest.import_id,
        kind=manifest.kind,
        source_label=manifest.source_label,
        snapshot_sha256=manifest.snapshot_sha256,
        size_bytes=manifest.size_bytes,
        media_type=manifest.media_type,
        git_commit=manifest.git_commit,
        purpose=manifest.purpose,
        expires_at=manifest.expires_at,
        preview_sha256=manifest.preview_sha256,
    )
```

这里的 `payload_name` 使用 Literal，是为了保证 manifest 即使被篡改，也不能让 Worker 从 import 目录读取任意相对路径。

---

## 十、让 Repository Capsule 支持受控目标根目录

> **本节类型：需要修改项目代码和测试。**
>
> 需要修改：`app/workspace/repo_capsule.py`、`tests/test_repo_capsule.py`。

不要在 Local Import 中复制一套 Git 检查逻辑。复用 Phase 26 已有的 clean repo、submodule、LFS、bundle verify 约束，只把目标根目录和大小上限参数化。

### 10.1 替换 `create_repository_capsule()` 签名和相关实现

用下面完整函数替换原函数：

```python
def create_repository_capsule(
    *,
    repo_path: str | Path,
    destination: Path,
    destination_root: Path | None = None,
    max_bytes: int | None = None,
) -> RepositoryCapsule:
    """把 clean Git repository 固化成可验证 bundle。

    Phase 26 默认写入 WORKSPACE_STAGING_ROOT；Phase 33 可以显式传入
    LOCAL_IMPORT_STAGING_ROOT。调用方只能扩大“代码允许的目标根”，不能传
    任意文件路径后绕过 containment。
    """

    repo = Path(repo_path).expanduser().resolve()
    branch, commit = _require_clean_repository(repo)
    _reject_unsupported_repository_features(repo)

    destination = destination.resolve()
    staging_root = (
        destination_root
        if destination_root is not None
        else settings.workspace_staging_root
    ).expanduser().resolve()
    if destination == staging_root or staging_root not in destination.parents:
        raise WorkspaceIntegrityError(
            "repository bundle 必须写入指定 staging root"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise WorkspaceIntegrityError("bundle destination 已存在")

    # 必须使用命名 ref；只传裸 commit 可能创建 empty bundle。
    _run_git(
        repo,
        ["bundle", "create", str(destination), branch],
    )
    _run_git(repo, ["bundle", "verify", str(destination)])

    # Bundle 期间仓库可能被另一个终端修改，因此生成后再次确认 identity。
    branch_after, commit_after = _require_clean_repository(repo)
    if branch_after != branch or commit_after != commit:
        destination.unlink(missing_ok=True)
        raise WorkspaceIntegrityError(
            "repository_changed_during_bundle"
        )

    size = destination.stat().st_size
    effective_max_bytes = (
        max_bytes
        if max_bytes is not None
        else settings.workspace_max_file_bytes
    )
    if size > effective_max_bytes:
        destination.unlink(missing_ok=True)
        raise WorkspaceNotPortableError(
            "repository_bundle_too_large"
        )

    return RepositoryCapsule(
        identity=RepositoryIdentity(
            commit_sha=commit,
            branch=branch,
            clean=True,
            bundle_logical_path="capsule/repository.bundle",
            has_submodules=False,
            has_lfs=False,
        ),
        bundle_path=destination,
        sha256=sha256_file(destination),
        size_bytes=size,
    )
```

### 10.2 增加边界测试

在 `tests/test_repo_capsule.py` 增加：

```python
def test_capsule_accepts_explicit_destination_root(
    clean_repo: Path,
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "local-imports"
    destination = local_root / "imp_1" / "repository.bundle"

    capsule = create_repository_capsule(
        repo_path=clean_repo,
        destination=destination,
        destination_root=local_root,
        max_bytes=20 * 1024 * 1024,
    )

    assert capsule.bundle_path == destination.resolve()
    assert capsule.identity.clean is True
    assert capsule.identity.commit_sha


def test_capsule_rejects_destination_outside_explicit_root(
    clean_repo: Path,
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "local-imports"

    with pytest.raises(WorkspaceIntegrityError):
        create_repository_capsule(
            repo_path=clean_repo,
            destination=tmp_path / "outside.bundle",
            destination_root=local_root,
        )
```

如果你的 fixture 名不是 `clean_repo`，复用该文件已有的 Git fixture 名称即可，不要额外复制仓库初始化代码。

---

## 十一、实现 LocalImportStore 与 LocalImportService

> **本节类型：需要新增项目代码和测试。**
>
> 需要新增：`app/resources/local_import.py`。

新建完整文件：

```python
from __future__ import annotations

"""Phase 33：受控本地 PDF / Git repository 导入。

安全原则：
- 原始绝对路径只在 inspect 调用栈中存在；
- 只接受 allowlist root 下的绝对路径；
- 拒绝路径链软链接；
- 先生成项目内不可变快照，再让用户确认 preview hash；
- commit 后仍走 ResourceService、approval、Worker 和 BlobStore；
- 不执行用户提供的 shell 字符串。
"""

import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.resources.local_import_schemas import (
    LocalImportCommitRecord,
    LocalImportInspectRequest,
    LocalImportManifest,
    LocalImportPreview,
    compute_preview_sha256,
    manifest_to_preview,
)

from app.config import settings
from app.resources.errors import (
    ResourceConflictError,
    ResourceIntegrityError,
    ResourceNotFoundError,
    ResourcePolicyViolation,
)
from app.resources.schemas import (
    ResourceApproval,
    ResourceRecord,
    ResourceRequest,
)
from app.resources.service import ResourceService
from app.resources.validators import validate_pdf
from app.workspace.errors import (
    WorkspaceIntegrityError,
    WorkspaceNotPortableError,
)
from app.workspace.repo_capsule import create_repository_capsule


class LocalImportError(ValueError):
    """可安全映射为 4xx 的 Local Import 领域错误。"""


class LocalImportNotFoundError(LocalImportError):
    pass


class LocalImportConflictError(LocalImportError):
    pass


@dataclass(frozen=True)
class LocalImportPayload:
    path: Path
    sha256: str
    size_bytes: int
    media_type: str
    git_commit: str | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _atomic_write_json(path: Path, payload: dict) -> None:
    """同目录写临时文件后原子替换，避免 Worker 读取半个 JSON。"""

    temporary = path.with_name(f".{path.name}.{uuid4().hex}.part")
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json_regular_file(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise LocalImportIntegrityError(
            f"Local Import metadata 不是普通文件：{path.name}"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalImportIntegrityError(
            f"Local Import metadata 无法读取：{path.name}"
        ) from exc
    if not isinstance(value, dict):
        raise LocalImportIntegrityError("Local Import metadata 必须是对象")
    return value


class LocalImportIntegrityError(LocalImportConflictError):
    pass


def _secure_copy_regular_file(
    *,
    source: Path,
    destination: Path,
    max_bytes: int,
    ensure_active: Callable[[], None] | None = None,
) -> tuple[str, int]:
    """通过 O_NOFOLLOW 打开并复制普通文件，同时检测复制期间替换。

    仅靠 ``Path.resolve`` 仍存在检查后替换的 TOCTOU 窗口，因此这里绑定
    打开的文件描述符，并比较复制前后的 inode/size/mtime。
    """

    no_follow = getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(source, os.O_RDONLY | no_follow)
    part = destination.with_name(f".{destination.name}.part")
    digest = hashlib.sha256()
    total = 0
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise LocalImportError("本地输入必须是普通文件")
        if before.st_size <= 0:
            raise LocalImportError("本地输入文件为空")
        if before.st_size > max_bytes:
            raise LocalImportError("本地输入超过大小上限")

        destination.parent.mkdir(parents=True, exist_ok=True)
        with part.open("xb") as target:
            while True:
                if ensure_active is not None:
                    ensure_active()
                block = os.read(descriptor, 1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > max_bytes:
                    raise LocalImportError("本地输入超过大小上限")
                digest.update(block)
                target.write(block)
            target.flush()
            os.fsync(target.fileno())

        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if identity_before != identity_after or total != before.st_size:
            raise LocalImportConflictError(
                "源文件在导入期间发生变化，请重新 inspect"
            )

        os.chmod(part, 0o400)
        os.replace(part, destination)
        return digest.hexdigest(), total
    finally:
        os.close(descriptor)
        part.unlink(missing_ok=True)


def _hash_regular_file(path: Path, *, expected_size: int) -> str:
    """对 staging payload 做使用时复核，不信任只读权限本身。"""

    no_follow = getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, os.O_RDONLY | no_follow)
    digest = hashlib.sha256()
    total = 0
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise LocalImportIntegrityError("staged payload 不是普通文件")
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            total += len(block)
            digest.update(block)
    finally:
        os.close(descriptor)
    if total != expected_size:
        raise LocalImportIntegrityError("staged payload size 已变化")
    return digest.hexdigest()


class LocalImportStore:
    """单主机 durable staging store。

    大 payload 位于 ``root/<import_id>/``。manifest/commit 均不包含原始路径。
    """

    def __init__(
        self,
        *,
        root: Path,
        allowed_roots: tuple[Path, ...],
        ttl_seconds: int,
        pdf_max_bytes: int,
        git_max_bytes: int,
    ):
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.allowed_roots = tuple(
            item.expanduser().resolve()
            for item in allowed_roots
        )
        self.ttl_seconds = ttl_seconds
        self.pdf_max_bytes = pdf_max_bytes
        self.git_max_bytes = git_max_bytes

    @classmethod
    def from_settings(cls) -> LocalImportStore:
        return cls(
            root=settings.local_import_staging_root,
            allowed_roots=settings.local_import_allowed_roots,
            ttl_seconds=settings.local_import_ttl_seconds,
            pdf_max_bytes=settings.resource_pdf_max_bytes,
            git_max_bytes=settings.local_import_git_max_bytes,
        )

    def _import_dir(self, import_id: str) -> Path:
        if re.fullmatch(r"imp_[0-9a-f]{32}", import_id) is None:
            raise LocalImportNotFoundError("非法 import_id")
        path = (self.root / import_id).resolve()
        if self.root not in path.parents:
            raise LocalImportNotFoundError("import_id 越过 staging root")
        return path

    def _resolve_source(self, raw_path: str) -> Path:
        """检查绝对路径、allowlist containment 和完整 no-symlink 链。"""

        supplied = Path(raw_path).expanduser()
        if not supplied.is_absolute():
            raise LocalImportError("source_path 必须是绝对路径")

        # abspath 只消除 . 和 ..，不会跟随软链接。
        lexical = Path(os.path.abspath(str(supplied)))
        matching_root: Path | None = None
        for root in self.allowed_roots:
            try:
                lexical.relative_to(root)
                matching_root = root
                break
            except ValueError:
                continue
        if matching_root is None:
            raise LocalImportError("source_path 不在 LOCAL_IMPORT_ALLOWED_ROOTS 内")

        relative = lexical.relative_to(matching_root)
        current = matching_root
        if current.is_symlink():
            raise LocalImportError("允许根目录不能是软链接")
        for component in relative.parts:
            current = current / component
            if current.is_symlink():
                raise LocalImportError("source_path 路径链中不允许软链接")

        try:
            resolved = lexical.resolve(strict=True)
        except FileNotFoundError as exc:
            raise LocalImportNotFoundError("source_path 不存在") from exc
        if matching_root != resolved and matching_root not in resolved.parents:
            raise LocalImportError("source_path 解析后越过允许根目录")
        if resolved == self.root or self.root in resolved.parents:
            raise LocalImportError("不能从 Local Import staging 目录再次导入")
        return resolved

    def prune_expired_uncommitted(
        self,
        *,
        now: datetime | None = None,
    ) -> int:
        """机会式清理过期且未 commit 的 snapshot。

        只遍历 staging root 的直接子目录；无法非阻塞获取 commit lock 时跳过，
        避免删除正在确认的 import。损坏且无法验证身份的目录也保留给人工排查。
        """

        current_time = now or utc_now()
        removed = 0
        for child in self.root.iterdir():
            if (
                child.is_symlink()
                or not child.is_dir()
                or re.fullmatch(r"imp_[0-9a-f]{32}", child.name) is None
            ):
                continue
            lock_path = child / ".commit.lock"
            lock_handle = lock_path.open("a+b")
            try:
                try:
                    fcntl.flock(
                        lock_handle.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB,
                    )
                except BlockingIOError:
                    continue
                manifest = self.load_manifest(child.name)
                if self.load_commit_record(child.name) is not None:
                    continue
                if manifest.expires_at > current_time:
                    continue
                # child 已通过 name、direct-child 和 no-symlink 检查。
                shutil.rmtree(child)
                removed += 1
            except LocalImportError:
                # 不自动删除无法证明身份的目录。
                continue
            finally:
                try:
                    fcntl.flock(
                        lock_handle.fileno(),
                        fcntl.LOCK_UN,
                    )
                except OSError:
                    pass
                lock_handle.close()
        return removed

    def inspect(
        self,
        request: LocalImportInspectRequest,
    ) -> LocalImportPreview:
        # 机会式清理过期且从未 commit 的快照，避免用户频繁切换输入模式
        # 后 staging 无限增长。正在 commit 的目录由文件锁保护。
        self.prune_expired_uncommitted()
        source = self._resolve_source(request.source_path)
        import_id = f"imp_{uuid4().hex}"
        import_dir = self._import_dir(import_id)
        import_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
        created_at = utc_now()

        try:
            if request.kind == "paper_pdf":
                if not source.is_file():
                    raise LocalImportError("paper_pdf source 必须是普通文件")
                destination = import_dir / "paper.pdf"
                snapshot_sha, size_bytes = _secure_copy_regular_file(
                    source=source,
                    destination=destination,
                    max_bytes=self.pdf_max_bytes,
                )
                try:
                    media_type = validate_pdf(destination)
                except ResourceIntegrityError as exc:
                    raise LocalImportError(
                        "paper_pdf 内容不是有效 PDF"
                    ) from exc
                git_commit = None
                payload_name = "paper.pdf"
            else:
                if not source.is_dir():
                    raise LocalImportError("git_repository source 必须是目录")
                destination = import_dir / "repository.bundle"
                try:
                    capsule = create_repository_capsule(
                        repo_path=source,
                        destination=destination,
                        destination_root=self.root,
                        max_bytes=self.git_max_bytes,
                    )
                except (
                    WorkspaceIntegrityError,
                    WorkspaceNotPortableError,
                ) as exc:
                    raise LocalImportError(str(exc)) from exc
                git_commit = capsule.identity.commit_sha.lower()
                if (
                    request.expected_git_commit is not None
                    and request.expected_git_commit != git_commit
                ):
                    raise LocalImportConflictError(
                        "仓库 HEAD 与 expected_git_commit 不一致"
                    )
                snapshot_sha = capsule.sha256
                size_bytes = capsule.size_bytes
                media_type = "application/octet-stream"
                payload_name = "repository.bundle"
                os.chmod(destination, 0o400)

            raw_manifest = {
                "manifest_version": "phase33-v1",
                "import_id": import_id,
                "kind": request.kind,
                "source_label": source.name,
                "payload_name": payload_name,
                "snapshot_sha256": snapshot_sha,
                "size_bytes": size_bytes,
                "media_type": media_type,
                "git_commit": git_commit,
                "purpose": request.purpose,
                "created_at": created_at,
                "expires_at": created_at + timedelta(seconds=self.ttl_seconds),
            }
            raw_manifest["preview_sha256"] = compute_preview_sha256(
                raw_manifest
            )
            manifest = LocalImportManifest.model_validate(raw_manifest)
            _atomic_write_json(
                import_dir / "manifest.json",
                manifest.model_dump(mode="json"),
            )
            return manifest_to_preview(manifest)
        except Exception:
            # 只删除刚创建且已经确认位于 staging root 的 import_dir。
            shutil.rmtree(import_dir, ignore_errors=True)
            raise

    def load_manifest(self, import_id: str) -> LocalImportManifest:
        import_dir = self._import_dir(import_id)
        manifest_path = import_dir / "manifest.json"
        if not manifest_path.exists():
            raise LocalImportNotFoundError("Local Import 不存在")
        try:
            manifest = LocalImportManifest.model_validate(
                _read_json_regular_file(manifest_path)
            )
        except Exception as exc:
            if isinstance(exc, LocalImportError):
                raise
            raise LocalImportIntegrityError(
                "Local Import manifest schema 无效"
            ) from exc
        if manifest.import_id != import_id:
            raise LocalImportIntegrityError("manifest import_id 不匹配")
        expected = compute_preview_sha256(
            manifest.model_dump(mode="json")
        )
        if expected != manifest.preview_sha256:
            raise LocalImportIntegrityError("Local Import preview hash 不自洽")
        return manifest

    def assert_payload_current(
        self,
        manifest: LocalImportManifest,
    ) -> Path:
        payload = self._import_dir(manifest.import_id) / manifest.payload_name
        if payload.is_symlink() or not payload.is_file():
            raise LocalImportIntegrityError("Local Import payload 不存在")
        actual = _hash_regular_file(
            payload,
            expected_size=manifest.size_bytes,
        )
        if actual != manifest.snapshot_sha256:
            raise LocalImportIntegrityError("Local Import payload hash 已变化")
        return payload

    def write_commit_record(
        self,
        record: LocalImportCommitRecord,
    ) -> None:
        _atomic_write_json(
            self._import_dir(record.import_id) / "commit.json",
            record.model_dump(mode="json"),
        )

    def load_commit_record(
        self,
        import_id: str,
    ) -> LocalImportCommitRecord | None:
        path = self._import_dir(import_id) / "commit.json"
        if not path.exists():
            return None
        try:
            return LocalImportCommitRecord.model_validate(
                _read_json_regular_file(path)
            )
        except Exception as exc:
            raise LocalImportIntegrityError(
                "Local Import commit record 无效"
            ) from exc

    def lock(self, import_id: str):
        """返回由调用方持有的跨线程/跨进程文件锁。"""

        import_dir = self._import_dir(import_id)
        if import_dir.is_symlink() or not import_dir.is_dir():
            raise LocalImportNotFoundError("Local Import 不存在")
        path = import_dir / ".commit.lock"
        handle = path.open("a+b")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return handle

    def copy_for_worker(
        self,
        *,
        request: ResourceRequest,
        resource_id: str,
        destination: Path,
        ensure_active: Callable[[], None],
    ) -> LocalImportPayload:
        if request.source_type != "local_import":
            raise ResourcePolicyViolation("request 不是 local_import")
        if request.local_import_id is None:
            raise ResourceIntegrityError("local_import_id 缺失")

        try:
            manifest = self.load_manifest(request.local_import_id)
            committed = self.load_commit_record(request.local_import_id)
        except LocalImportError as exc:
            raise ResourceIntegrityError(
                f"Local Import metadata invalid: {exc}"
            ) from exc
        if committed is None or committed.resource_id != resource_id:
            raise ResourcePolicyViolation("Local Import 未绑定当前 Resource")

        if (
            manifest.kind != request.kind
            or manifest.source_label != request.source_label
            or manifest.snapshot_sha256
            != request.local_snapshot_sha256
            or manifest.git_commit != request.expected_git_commit
        ):
            raise ResourceIntegrityError(
                "Local Import manifest 与 ResourceRequest 不一致"
            )

        source = self.assert_payload_current(manifest)
        copied_sha, copied_size = _secure_copy_regular_file(
            source=source,
            destination=destination,
            max_bytes=manifest.size_bytes,
            ensure_active=ensure_active,
        )
        if (
            copied_sha != manifest.snapshot_sha256
            or copied_size != manifest.size_bytes
        ):
            raise ResourceIntegrityError("Local Import worker copy identity mismatch")
        return LocalImportPayload(
            path=destination,
            sha256=copied_sha,
            size_bytes=copied_size,
            media_type=manifest.media_type,
            git_commit=manifest.git_commit,
        )

    def remove_published_payload(
        self,
        *,
        import_id: str,
        resource_id: str,
    ) -> None:
        """Resource published 后只删除大 payload，保留小型审计 metadata。"""

        committed = self.load_commit_record(import_id)
        if committed is None or committed.resource_id != resource_id:
            return
        manifest = self.load_manifest(import_id)
        payload = self._import_dir(import_id) / manifest.payload_name
        if payload.is_file() and not payload.is_symlink():
            payload.unlink(missing_ok=True)


class LocalImportService:
    def __init__(
        self,
        *,
        store: LocalImportStore,
        resource_service: ResourceService,
    ):
        self.store = store
        self.resource_service = resource_service

    def inspect(
        self,
        request: LocalImportInspectRequest,
    ) -> LocalImportPreview:
        return self.store.inspect(request)

    def commit(
        self,
        *,
        import_id: str,
        expected_preview_sha256: str,
        actor: str,
    ) -> tuple[ResourceRecord, bool]:
        """确认快照并幂等创建/批准 Resource。

        Resource idempotency key 由 import_id 确定，而不是由浏览器随机生成。
        即使 API 在 submit 后、返回前崩溃，重试也不会创建第二个 Resource。
        """

        lock_handle = self.store.lock(import_id)
        try:
            manifest = self.store.load_manifest(import_id)
            if manifest.preview_sha256 != expected_preview_sha256:
                raise LocalImportConflictError(
                    "stale Local Import preview；请重新 inspect"
                )

            committed = self.store.load_commit_record(import_id)
            if committed is None:
                if utc_now() > manifest.expires_at:
                    raise LocalImportConflictError(
                        "Local Import preview 已过期；请重新 inspect"
                    )
                # 首次 commit 必须在创建 Resource 前确认快照仍然有效。
                self.store.assert_payload_current(manifest)
            request = ResourceRequest(
                kind=manifest.kind,
                source_type="local_import",
                source_url=None,
                local_import_id=manifest.import_id,
                source_label=manifest.source_label,
                local_snapshot_sha256=manifest.snapshot_sha256,
                expected_sha256=(
                    manifest.snapshot_sha256
                    if manifest.kind == "paper_pdf"
                    else None
                ),
                expected_git_commit=manifest.git_commit,
                purpose=manifest.purpose,
            )
            try:
                resource, created = self.resource_service.submit(
                    request=request,
                    idempotency_key=f"local-import:{import_id}",
                )
            except ResourceConflictError as exc:
                raise LocalImportConflictError(str(exc)) from exc

            commit_record = LocalImportCommitRecord(
                import_id=import_id,
                resource_id=resource.resource_id,
                request_sha256=resource.request_sha256,
                committed_by=actor,
                committed_at=utc_now(),
            )
            if committed is not None:
                if (
                    committed.resource_id != resource.resource_id
                    or committed.request_sha256 != resource.request_sha256
                ):
                    raise LocalImportIntegrityError(
                        "Local Import commit record 与 Resource 不一致"
                    )
            else:
                # 必须先写 commit record，再把 Resource 变为 queued；
                # Worker claim 后会要求这条绑定记录存在。
                self.store.write_commit_record(commit_record)

            if resource.status == "awaiting_approval":
                # 覆盖 submit 后进程崩溃、随后重试 commit 的恢复场景。
                # 只要尚未 queued，payload 就必须存在且 hash 正确。
                self.store.assert_payload_current(manifest)
                resource = self.resource_service.approve(
                    resource_id=resource.resource_id,
                    approval=ResourceApproval(
                        decision="approved",
                        request_sha256=resource.request_sha256,
                        decided_by=actor,
                        decided_at=utc_now().isoformat(),
                        reason=(
                            "approved exact local import preview "
                            f"{manifest.preview_sha256}"
                        ),
                    ),
                    expected_version=resource.version,
                )
            return resource, created
        except ResourceNotFoundError as exc:
            raise LocalImportNotFoundError(str(exc)) from exc
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()


def build_local_import_service(
    resource_service: ResourceService,
) -> LocalImportService:
    return LocalImportService(
        store=LocalImportStore.from_settings(),
        resource_service=resource_service,
    )
```

### 11.1 一个需要注意的实现细节

`commit()` 中的顺序必须是：

```text
submit awaiting_approval
  -> write commit.json
  -> approve to queued
```

不能先 approve 再写 `commit.json`。否则 Resource Worker 可能在 commit record 尚未落盘时 claim 任务，并把一个合法导入误判为未绑定。

### 11.2 关于 `shutil.rmtree`

这里仅在 inspect 失败时清理 **刚创建的** `root/<random import_id>`，并且 `_import_dir()` 已验证路径严格位于 Local Import staging root 内。不要改成 glob，也不要删除整个 `resources/`。

---

## 十二、让 Resource Worker 获取本地快照

> **本节类型：需要修改项目代码和测试。**
>
> 需要修改：`app/resources/worker.py`。

本地导入提交后仍然由 Resource Worker 发布。区别只在 `_fetch()`：远程来源使用 HTTP/Git fetcher，本地来源从 Local Import staging 安全复制。

### 12.1 增加 import

在 `app/resources/worker.py` 顶部增加：

```python
from app.resources.local_import import LocalImportStore
```

### 12.2 扩展 `ResourceWorker.__init__()`

在现有参数列表末尾增加可注入参数：

```python
        local_import_store: LocalImportStore | None = None,
```

在 `self.publisher = ...` 后增加：

```python
        self.local_import_store = (
            local_import_store
            if local_import_store is not None
            else LocalImportStore.from_settings()
        )
```

测试可以注入临时目录 Store；生产默认读取 Phase 33 配置。

### 12.3 在 `_fetch()` 中最先处理 local import

用下面完整函数替换当前 `_fetch()`：

```python
    def _fetch(
        self,
        record: ResourceRecord,
        claim_token: str,
        ensure_active,
    ) -> StagedResource:
        request = record.request
        staging_dir = resource_staging_dir(
            record.resource_id,
            claim_token,
        )
        staging_dir.mkdir(parents=True, exist_ok=True)

        if request.source_type == "local_import":
            # 本地来源不会调用 downloader 或 git_fetcher。
            destination = staging_dir / (
                "repository.bundle"
                if request.kind == "git_repository"
                else "paper.pdf"
            )
            payload = self.local_import_store.copy_for_worker(
                request=request,
                resource_id=record.resource_id,
                destination=destination,
                ensure_active=ensure_active,
            )
            return StagedResource(
                source_path=payload.path,
                sha256=payload.sha256,
                size_bytes=payload.size_bytes,
                media_type=payload.media_type,
                redirect_chain=[],
                git_commit=payload.git_commit,
            )

        # 从这里开始都是 remote_url。Optional 字段在分支内收窄。
        if request.source_url is None:
            raise ResourceIntegrityError(
                "remote ResourceRequest 缺少 source_url"
            )

        if request.kind == "git_repository":
            assert request.expected_git_commit is not None
            result = self.git_fetcher.fetch(
                source_url=request.source_url,
                expected_commit=request.expected_git_commit,
                staging_dir=staging_dir,
            )
            return StagedResource(
                source_path=result.bundle_path,
                sha256=result.bundle_sha256,
                size_bytes=result.bundle_size_bytes,
                media_type="application/octet-stream",
                redirect_chain=[],
                git_commit=result.commit_sha,
            )

        max_bytes = self._max_bytes_for(request.kind)
        destination = staging_dir / "download.part"
        result = self.downloader.download(
            url=request.source_url,
            destination=destination,
            max_bytes=max_bytes,
            expected_sha256=request.expected_sha256,
            ensure_active=ensure_active,
        )
        return StagedResource(
            source_path=result.path,
            sha256=result.sha256,
            size_bytes=result.size_bytes,
            media_type=result.media_type,
            redirect_chain=list(result.redirect_chain),
            git_commit=None,
        )
```

### 12.4 发布成功后删除大 payload

在 `_process()` 中，`mark_published()` 成功之后、指标记录之前增加：

```python
            if (
                record.request.source_type == "local_import"
                and record.request.local_import_id is not None
            ):
                # 必须在 DB 已经进入 published 后清理。
                # 如果 publish 或 mark_published 失败，payload 仍保留给重试/对账。
                self.local_import_store.remove_published_payload(
                    import_id=record.request.local_import_id,
                    resource_id=record.resource_id,
                )
```

完整上下文应是：

```python
            self.repository.mark_published(
                resource_id=record.resource_id,
                claim_token=claim_token,
                manifest=manifest,
            )
            if (
                record.request.source_type == "local_import"
                and record.request.local_import_id is not None
            ):
                self.local_import_store.remove_published_payload(
                    import_id=record.request.local_import_id,
                    resource_id=record.resource_id,
                )
            increment_counter_safe(
                self.telemetry,
                "paper_copilot_resources_acquired_total",
                attributes={
                    "kind": record.request.kind,
                    "outcome": "published",
                },
            )
```

不要在 `finally` 中删除 Local Import payload。`finally` 只清理本次 claim 的临时 staging；Local Import 原始快照必须等正式 Resource 状态成为 `published` 才能清理。

---

## 十三、让 Publisher 接受统一 sanitized locator

> **本节类型：需要修改项目代码和测试。**
>
> 需要修改：`app/resources/publisher.py`、`app/resources/worker.py`。

当前 Publisher 强制对 `source_url` 调用 `canonicalize_url()`，它会拒绝 `local-import://`。不要放宽 `canonicalize_url()`，而是调用第八节新增的统一 locator 规范化函数。

### 13.1 修改 `app/resources/publisher.py` import

替换：

```python
from app.resources.request_hash import canonicalize_url
```

为：

```python
from app.resources.request_hash import canonicalize_resource_locator
```

### 13.2 修改 `ResourcePublisher.publish_file()` 参数

把参数：

```python
        source_url: str,
```

改为：

```python
        source_locator: str,
```

把 payload 中：

```python
            "source_url_sanitized": canonicalize_url(source_url),
```

改为：

```python
            # 为兼容 Phase 29 已落库 manifest，字段名暂时保留；
            # 值现在是 sanitized Resource URI，可能是 https 或 local-import。
            "source_url_sanitized": canonicalize_resource_locator(
                source_locator
            ),
```

redirect chain 仍然只来自 HTTP 下载，所以保持严格 HTTPS：

```python
            "redirect_chain_sanitized": [
                canonicalize_resource_locator(item)
                for item in redirect_chain
            ],
```

### 13.3 修改 Worker `_publish()`

先在 `app/resources/worker.py` 增加 import：

```python
from app.resources.request_hash import (
    resource_request_sha256,
    resource_source_locator,
)
```

然后完整替换 `_publish()`：

```python
    def _publish(
        self,
        record: ResourceRecord,
        staged: StagedResource,
        media_type: str,
    ) -> ResourceManifest:
        return self.publisher.publish_file(
            resource_id=record.resource_id,
            kind=record.request.kind,
            source_locator=resource_source_locator(record.request),
            redirect_chain=staged.redirect_chain,
            source=staged.source_path,
            sha256=staged.sha256,
            size_bytes=staged.size_bytes,
            media_type=media_type,
            git_commit=staged.git_commit,
        )
```

`ResourceManifest.source_url_sanitized` 暂不改数据库字段名是兼容性选择。后续如果做正式 API v2，可以统一改为 `source_locator_sanitized`，但本阶段没必要为了命名迁移全部历史 JSON 和前端。

---

## 十四、更新 Resource 公开视图

> **本节类型：需要修改项目代码和测试。**
>
> 需要修改：`app/resources/service.py`、`app/api/resource_routes.py`。

### 14.1 修改 `app/resources/service.py`

将 request hash import 扩展为：

```python
from app.resources.request_hash import resource_source_locator
```

如果原来还在本文件使用 `canonicalize_url`，删除对应 import。

在 `sanitize_resource_view()` 中，把 source URL 计算替换为：

```python
    request = record.request
    # reveal_source 不再返回本地绝对路径，因为它根本没有持久化。
    # 对 remote URL，Phase 29 已拒绝 query/userinfo/fragment。
    source_locator = resource_source_locator(request)
```

返回 dict 中替换并新增：

```python
        "source_type": request.source_type,
        "source_url_sanitized": source_locator,
```

不要在公开视图中增加：

```text
source_path
staging_path
payload_path
commit.json path
```

### 14.2 修改 `app/api/resource_routes.py`

在 schema import 中增加：

```python
    ResourceSourceType,
```

在 `ResourceResponse` 中增加：

```python
    source_type: ResourceSourceType
```

远程 Resource submit 仍然显式创建：

```python
        request = ResourceRequest(
            kind=body.kind,
            source_type="remote_url",
            source_url=body.source_url,
            expected_sha256=body.expected_sha256,
            expected_git_commit=body.expected_git_commit,
            purpose=body.purpose,
        )
```

不要让 `/v1/resources` 接受客户端传入 `source_type="local_import"`。本地导入必须经过专门 endpoint 完成路径检查和 snapshot；否则攻击者可以伪造 `local_import_id`。

---

## 十五、新增 Local Import API

> **本节类型：需要新增项目代码和测试。**
>
> 需要新增：`app/api/local_import_routes.py`。

新建完整文件：

```python
from __future__ import annotations

"""Phase 33 Local Import HTTP API。

路径只进入 inspect body，不出现在响应、Event 或 ResourceRequest 中。
"""

from typing import Annotated

from app.resources.local_import import (
    LocalImportConflictError,
    LocalImportError,
    LocalImportNotFoundError,
    LocalImportService,
)
from app.resources.local_import_schemas import (
    LocalImportCommitBody,
    LocalImportInspectRequest,
    LocalImportPreview,
)
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.api.auth import require_api_auth
from app.api.resource_routes import ResourceResponse
from app.resources.service import sanitize_resource_view

router = APIRouter(prefix="/v1/local-imports")
Actor = Annotated[str, Depends(require_api_auth)]


class LocalImportCommitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource: ResourceResponse
    replayed: bool


def local_import_service(request: Request) -> LocalImportService:
    service = getattr(
        request.app.state,
        "local_import_service",
        None,
    )
    if service is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LOCAL_IMPORT_UNAVAILABLE",
                "message": "Local Import service 未配置",
            },
        )
    return service


LocalImportServiceDependency = Annotated[
    LocalImportService,
    Depends(local_import_service),
]


@router.post(
    "/inspect",
    response_model=LocalImportPreview,
    status_code=201,
)
def inspect_local_input(
    body: LocalImportInspectRequest,
    _actor: Actor,
    service: LocalImportServiceDependency,
) -> LocalImportPreview:
    try:
        return service.inspect(body)
    except LocalImportNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "LOCAL_IMPORT_SOURCE_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc
    except LocalImportConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "LOCAL_IMPORT_CONFLICT",
                "message": str(exc),
            },
        ) from exc
    except LocalImportError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_LOCAL_IMPORT",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/{import_id}/commit",
    response_model=LocalImportCommitResponse,
)
def commit_local_input(
    import_id: str,
    body: LocalImportCommitBody,
    actor: Actor,
    service: LocalImportServiceDependency,
) -> LocalImportCommitResponse:
    try:
        record, created = service.commit(
            import_id=import_id,
            expected_preview_sha256=(
                body.expected_preview_sha256
            ),
            actor=actor,
        )
    except LocalImportNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "LOCAL_IMPORT_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc
    except LocalImportConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "STALE_LOCAL_IMPORT",
                "message": str(exc),
            },
        ) from exc
    except LocalImportError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_LOCAL_IMPORT",
                "message": str(exc),
            },
        ) from exc

    return LocalImportCommitResponse(
        resource=ResourceResponse(
            **sanitize_resource_view(record)
        ),
        replayed=not created,
    )
```

这里没有要求浏览器传 `Idempotency-Key`，因为 endpoint path 中的 `import_id` 本身就是这次 snapshot 的幂等身份，Service 内部使用 `local-import:<import_id>` 创建 Resource。以后若统一 HTTP mutation contract，也可以要求 header，但不能用随机 header 替代领域幂等键。

---

## 十六、在 FastAPI App 中接线

> **本节类型：需要修改项目代码和测试。**
>
> 需要修改：`app/api/app.py`。

### 16.1 增加 import

```python
from app.api.local_import_routes import (
    router as local_import_router,
)
from app.resources.local_import import (
    LocalImportService,
    build_local_import_service,
)
```

### 16.2 扩展 App factory 参数

在 `create_api_app()` 参数列表增加：

```python
    local_import_service: LocalImportService | None = None,
```

这样 API 集成测试可以注入 `tmp_path` Store，不会写真实 staging。

### 16.3 在 ResourceService 建立后初始化 LocalImportService

放在：

```python
    app.state.resource_service = resource_service
```

之后：

```python
    selected_local_import_service = (
        local_import_service
        if local_import_service is not None
        else build_local_import_service(resource_service)
    )
    app.state.local_import_service = selected_local_import_service
```

### 16.4 增加 readiness probe

先为 `LocalImportStore` 增加一个简单方法，放进 `app/resources/local_import.py::LocalImportStore`：

```python
    def ping(self) -> None:
        """确认 staging root 可读写，不创建系统临时文件。"""

        probe = self.root / f".ready-{uuid4().hex}"
        try:
            with probe.open("xb") as handle:
                handle.write(b"ready")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            probe.unlink(missing_ok=True)
```

在 `app/api/app.py` 增加 check：

```python
    def local_import_check() -> str:
        try:
            selected_local_import_service.store.ping()
            return "ready"
        except Exception:
            return "not_ready"
```

在 `probes` 中增加：

```python
        ReadinessProbe(
            name="local_import_staging",
            is_critical=True,
            check=local_import_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        ),
```

### 16.5 注册 router

在 SPA mount 之前、其他 `/v1` router 附近增加：

```python
    app.include_router(router)
    app.include_router(resource_router)
    app.include_router(local_import_router)
    app.include_router(ui_router)
    app.include_router(chat_router)
```

不要在 `mount_web_ui()` 之后注册，否则 SPA fallback 可能吞掉 Local Import API。

---

## 十七、修正 commit 重放与 payload 清理边界

> **本节类型：需要修改项目代码。**
>
> 需要修改：`app/resources/local_import.py`。

第十一节给出的主流程需要处理一个关键恢复场景：Resource 已经 published 后，Worker 会删除大 payload；此时浏览器因网络超时再次调用 commit，应该返回同一个 Resource，而不是因为 payload 不存在报错。

因此，在 `LocalImportService.commit()` 中，不要无条件执行：

```python
self.store.assert_payload_current(manifest)
```

把过期与 payload 校验部分改成下面的完整逻辑：

```python
            committed = self.store.load_commit_record(import_id)
            if committed is None:
                if utc_now() > manifest.expires_at:
                    raise LocalImportConflictError(
                        "Local Import preview 已过期；请重新 inspect"
                    )
                # 首次 commit 必须在创建 Resource 前确认快照仍存在且 hash 正确。
                self.store.assert_payload_current(manifest)
```

然后在 `if resource.status == "awaiting_approval":` 内，批准前再检查一次：

```python
            if resource.status == "awaiting_approval":
                # 覆盖“submit 成功、进程崩溃、commit 重试”的恢复场景。
                # 只要还未 queued，payload 就必须存在且匹配。
                self.store.assert_payload_current(manifest)
                resource = self.resource_service.approve(
                    # 其余参数保持第十一节内容不变。
                )
```

最终语义是：

```text
首次 commit                 -> 必须有正确 payload
崩溃后恢复 awaiting_approval -> 必须有正确 payload
queued/fetching/validating   -> Worker 自己做使用时校验
published commit replay      -> 不再要求已经清理的大 payload
```

这是典型的“验证时机跟状态一致”，不要为了代码短而无条件检查文件。

---

## 十八、增加后端领域测试

> **本节类型：需要新增测试代码。**
>
> 需要新增：`tests/test_local_import_service.py`。

新建完整测试文件：

```python
from __future__ import annotations

import subprocess
from datetime import timedelta
from pathlib import Path

import pytest
from app.resources.local_import import (
    LocalImportConflictError,
    LocalImportError,
    LocalImportService,
    LocalImportStore,
)
from app.resources.local_import_schemas import (
    LocalImportInspectRequest,
)

from app.resources.service import ResourceService
from tests.fakes.fake_resource_repository import (
    FakeResourceRepository,
)


def _write_pdf(path: Path) -> None:
    """创建能被 PyMuPDF 打开的真实一页 PDF。"""

    try:
        import fitz
    except ImportError:
        # validators.py 在没有 fitz 时只检查 magic。
        path.write_bytes(b"%PDF-1.4\n% test fixture\n")
        return
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Phase 33 fixture")
    document.save(path)
    document.close()


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    return completed.stdout.strip()


def _make_repo(path: Path) -> str:
    path.mkdir()
    _git(path, "init")
    _git(path, "config", "user.email", "tests@example.com")
    _git(path, "config", "user.name", "Tests")
    (path / "train.py").write_text("print('train')\n", encoding="utf-8")
    _git(path, "add", "train.py")
    _git(path, "commit", "-m", "initial")
    return _git(path, "rev-parse", "HEAD")


@pytest.fixture
def local_import_runtime(
    tmp_path: Path,
) -> tuple[LocalImportService, LocalImportStore, ResourceService, Path]:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    store = LocalImportStore(
        root=tmp_path / "project" / "local-imports",
        allowed_roots=(inputs,),
        ttl_seconds=3600,
        pdf_max_bytes=10 * 1024 * 1024,
        git_max_bytes=50 * 1024 * 1024,
    )
    resource_service = ResourceService(FakeResourceRepository())
    service = LocalImportService(
        store=store,
        resource_service=resource_service,
    )
    return service, store, resource_service, inputs


def test_pdf_inspect_does_not_persist_absolute_path(
    local_import_runtime,
) -> None:
    service, store, _, inputs = local_import_runtime
    paper = inputs / "paper.pdf"
    _write_pdf(paper)

    preview = service.inspect(
        LocalImportInspectRequest(
            kind="paper_pdf",
            source_path=str(paper),
            purpose="paper input",
        )
    )

    manifest_path = (
        store.root / preview.import_id / "manifest.json"
    )
    persisted = manifest_path.read_text(encoding="utf-8")
    assert str(paper) not in persisted
    assert preview.source_label == "paper.pdf"
    assert preview.snapshot_sha256
    assert preview.preview_sha256


def test_outside_allowlist_is_rejected(
    local_import_runtime,
    tmp_path: Path,
) -> None:
    service, _, _, _ = local_import_runtime
    outside = tmp_path / "outside.pdf"
    _write_pdf(outside)

    with pytest.raises(LocalImportError, match="不在"):
        service.inspect(
            LocalImportInspectRequest(
                kind="paper_pdf",
                source_path=str(outside),
                purpose="paper input",
            )
        )


def test_symlink_source_is_rejected(
    local_import_runtime,
) -> None:
    service, _, _, inputs = local_import_runtime
    real = inputs / "real.pdf"
    link = inputs / "linked.pdf"
    _write_pdf(real)
    link.symlink_to(real)

    with pytest.raises(LocalImportError, match="软链接"):
        service.inspect(
            LocalImportInspectRequest(
                kind="paper_pdf",
                source_path=str(link),
                purpose="paper input",
            )
        )


def test_stale_preview_hash_does_not_create_resource(
    local_import_runtime,
) -> None:
    service, _, resource_service, inputs = local_import_runtime
    paper = inputs / "paper.pdf"
    _write_pdf(paper)
    preview = service.inspect(
        LocalImportInspectRequest(
            kind="paper_pdf",
            source_path=str(paper),
            purpose="paper input",
        )
    )

    with pytest.raises(LocalImportConflictError, match="stale"):
        service.commit(
            import_id=preview.import_id,
            expected_preview_sha256="0" * 64,
            actor="test-user",
        )

    assert resource_service.repository.claim_next(
        worker_id="test-worker",
        lease_seconds=60,
    ) is None


def test_expired_uncommitted_snapshot_is_pruned(
    local_import_runtime,
) -> None:
    service, store, _, inputs = local_import_runtime
    paper = inputs / "paper.pdf"
    _write_pdf(paper)
    preview = service.inspect(
        LocalImportInspectRequest(
            kind="paper_pdf",
            source_path=str(paper),
            purpose="paper input",
        )
    )

    removed = store.prune_expired_uncommitted(
        now=preview.expires_at + timedelta(seconds=1),
    )

    assert removed == 1
    assert not (store.root / preview.import_id).exists()


def test_commit_creates_approved_local_resource_idempotently(
    local_import_runtime,
) -> None:
    service, _, _, inputs = local_import_runtime
    paper = inputs / "paper.pdf"
    _write_pdf(paper)
    preview = service.inspect(
        LocalImportInspectRequest(
            kind="paper_pdf",
            source_path=str(paper),
            purpose="paper input",
        )
    )

    first, created = service.commit(
        import_id=preview.import_id,
        expected_preview_sha256=preview.preview_sha256,
        actor="test-user",
    )
    second, replay_created = service.commit(
        import_id=preview.import_id,
        expected_preview_sha256=preview.preview_sha256,
        actor="test-user",
    )

    assert created is True
    assert replay_created is False
    assert first.resource_id == second.resource_id
    assert first.status == "queued"
    assert first.request.source_type == "local_import"
    assert first.request.source_url is None
    assert first.approval is not None
    assert first.approval.request_sha256 == first.request_sha256


def test_git_inspect_pins_clean_head(
    local_import_runtime,
) -> None:
    service, _, _, inputs = local_import_runtime
    repo = inputs / "repo"
    head = _make_repo(repo)

    preview = service.inspect(
        LocalImportInspectRequest(
            kind="git_repository",
            source_path=str(repo),
            purpose="repository input",
            expected_git_commit=head,
        )
    )

    assert preview.git_commit == head
    assert preview.source_label == "repo"
    assert preview.size_bytes > 0


def test_dirty_git_repository_is_rejected(
    local_import_runtime,
) -> None:
    service, _, _, inputs = local_import_runtime
    repo = inputs / "repo"
    _make_repo(repo)
    (repo / "untracked.txt").write_text("dirty", encoding="utf-8")

    with pytest.raises(LocalImportError, match="dirty|repository_dirty"):
        service.inspect(
            LocalImportInspectRequest(
                kind="git_repository",
                source_path=str(repo),
                purpose="repository input",
            )
        )
```

如果你的 `WorkspaceNotPortableError` 不是 `WorkspaceIntegrityError` 子类，需要在 `local_import.py` 同时捕获两者：

```python
from app.workspace.errors import (
    WorkspaceIntegrityError,
    WorkspaceNotPortableError,
)

except (WorkspaceIntegrityError, WorkspaceNotPortableError) as exc:
    raise LocalImportError(str(exc)) from exc
```

请根据当前实际继承关系选择，不要让 dirty repo 变成 HTTP 500。

---

## 十九、增加 Local Import API 测试

> **本节类型：需要新增测试代码。**
>
> 需要新增：`tests/test_local_import_api.py`。

新建完整文件：

```python
from __future__ import annotations

from pathlib import Path

from app.api.local_import_routes import router
from app.resources.local_import import (
    LocalImportService,
    LocalImportStore,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.resources.service import ResourceService
from tests.fakes.fake_resource_repository import (
    FakeResourceRepository,
)

AUTH = {"Authorization": "Bearer test-token"}


def _write_pdf(path: Path) -> None:
    try:
        import fitz
    except ImportError:
        path.write_bytes(b"%PDF-1.4\n% local import API fixture\n")
        return
    document = fitz.open()
    document.new_page().insert_text((72, 72), "API fixture")
    document.save(path)
    document.close()


def _client(
    tmp_path: Path,
) -> tuple[TestClient, LocalImportService, Path]:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    resource_service = ResourceService(FakeResourceRepository())
    local_service = LocalImportService(
        store=LocalImportStore(
            root=tmp_path / "staging" / "local-imports",
            allowed_roots=(inputs,),
            ttl_seconds=3600,
            pdf_max_bytes=10 * 1024 * 1024,
            git_max_bytes=50 * 1024 * 1024,
        ),
        resource_service=resource_service,
    )
    app = FastAPI()
    app.include_router(router)
    app.state.api_token = "test-token"
    app.state.local_import_service = local_service
    return TestClient(app), local_service, inputs


def test_inspect_and_commit_local_pdf(tmp_path: Path) -> None:
    client, _, inputs = _client(tmp_path)
    paper = inputs / "paper.pdf"
    _write_pdf(paper)

    inspected = client.post(
        "/v1/local-imports/inspect",
        headers=AUTH,
        json={
            "kind": "paper_pdf",
            "source_path": str(paper),
            "purpose": "paper input",
        },
    )
    assert inspected.status_code == 201
    preview = inspected.json()
    assert "source_path" not in preview
    assert str(inputs) not in inspected.text

    committed = client.post(
        f"/v1/local-imports/{preview['import_id']}/commit",
        headers=AUTH,
        json={
            "expected_preview_sha256": preview["preview_sha256"],
        },
    )
    assert committed.status_code == 200
    body = committed.json()
    assert body["replayed"] is False
    assert body["resource"]["status"] == "queued"
    assert body["resource"]["source_type"] == "local_import"
    assert body["resource"]["source_url_sanitized"].startswith(
        "local-import://imp_"
    )
    assert str(inputs) not in committed.text


def test_commit_is_idempotent(tmp_path: Path) -> None:
    client, _, inputs = _client(tmp_path)
    paper = inputs / "paper.pdf"
    _write_pdf(paper)
    preview = client.post(
        "/v1/local-imports/inspect",
        headers=AUTH,
        json={
            "kind": "paper_pdf",
            "source_path": str(paper),
            "purpose": "paper input",
        },
    ).json()
    path = f"/v1/local-imports/{preview['import_id']}/commit"
    payload = {
        "expected_preview_sha256": preview["preview_sha256"],
    }

    first = client.post(path, headers=AUTH, json=payload)
    second = client.post(path, headers=AUTH, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["replayed"] is True
    assert (
        first.json()["resource"]["resource_id"]
        == second.json()["resource"]["resource_id"]
    )


def test_stale_preview_returns_409(tmp_path: Path) -> None:
    client, _, inputs = _client(tmp_path)
    paper = inputs / "paper.pdf"
    _write_pdf(paper)
    preview = client.post(
        "/v1/local-imports/inspect",
        headers=AUTH,
        json={
            "kind": "paper_pdf",
            "source_path": str(paper),
            "purpose": "paper input",
        },
    ).json()

    response = client.post(
        f"/v1/local-imports/{preview['import_id']}/commit",
        headers=AUTH,
        json={"expected_preview_sha256": "0" * 64},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "STALE_LOCAL_IMPORT"


def test_inspect_requires_auth(tmp_path: Path) -> None:
    client, _, inputs = _client(tmp_path)
    paper = inputs / "paper.pdf"
    _write_pdf(paper)

    response = client.post(
        "/v1/local-imports/inspect",
        json={
            "kind": "paper_pdf",
            "source_path": str(paper),
            "purpose": "paper input",
        },
    )

    assert response.status_code in {401, 403}


def test_unknown_fields_are_rejected(tmp_path: Path) -> None:
    client, _, inputs = _client(tmp_path)
    paper = inputs / "paper.pdf"
    _write_pdf(paper)

    response = client.post(
        "/v1/local-imports/inspect",
        headers=AUTH,
        json={
            "kind": "paper_pdf",
            "source_path": str(paper),
            "purpose": "paper input",
            "follow_symlinks": True,
        },
    )

    assert response.status_code == 422
```

这个 API 测试刻意直接挂载 router，而不是启动完整 ServiceHost，因此运行快、失败定位清楚。完整 App 接线由后面的 smoke test 覆盖。

---

## 二十、增加 Worker 端到端本地发布测试

> **本节类型：需要新增测试代码。**
>
> 需要新增：`tests/test_local_import_worker.py`。

这个测试证明本地导入并不是只创建一条 DB 记录，而是真的经过 Resource Worker、validator 和 BlobStore 发布。

```python
from __future__ import annotations

from pathlib import Path

import pytest
from app.resources.local_import import (
    LocalImportService,
    LocalImportStore,
)
from app.resources.local_import_schemas import (
    LocalImportInspectRequest,
)

from app.config import settings
from app.resources.service import ResourceService
from app.resources.worker import ResourceWorker
from app.storage.local_blob_store import LocalBlobStore
from tests.fakes.fake_resource_repository import (
    FakeResourceRepository,
)


def _write_pdf(path: Path) -> None:
    try:
        import fitz
    except ImportError:
        path.write_bytes(b"%PDF-1.4\n% worker fixture\n")
        return
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Worker fixture")
    document.save(path)
    document.close()


def test_local_pdf_reaches_published_resource(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    paper = inputs / "paper.pdf"
    _write_pdf(paper)

    # Resource Worker 的 claim staging 也隔离到项目测试目录。
    monkeypatch.setattr(
        settings,
        "resource_staging_root",
        tmp_path / "resource-claims",
    )

    repository = FakeResourceRepository()
    resource_service = ResourceService(repository)
    import_store = LocalImportStore(
        root=tmp_path / "local-imports",
        allowed_roots=(inputs,),
        ttl_seconds=3600,
        pdf_max_bytes=10 * 1024 * 1024,
        git_max_bytes=50 * 1024 * 1024,
    )
    import_service = LocalImportService(
        store=import_store,
        resource_service=resource_service,
    )
    preview = import_service.inspect(
        LocalImportInspectRequest(
            kind="paper_pdf",
            source_path=str(paper),
            purpose="paper input",
        )
    )
    queued, _ = import_service.commit(
        import_id=preview.import_id,
        expected_preview_sha256=preview.preview_sha256,
        actor="test-user",
    )

    blob_store = LocalBlobStore(tmp_path / "blob-store")
    blob_store.ensure_ready()
    worker = ResourceWorker(
        repository=repository,
        blob_store=blob_store,
        worker_id="resource-worker-test",
        local_import_store=import_store,
    )

    assert worker.run_once() is True
    published = resource_service.get(queued.resource_id)
    assert published.status == "published"
    assert published.manifest is not None
    assert published.manifest.sha256 == preview.snapshot_sha256
    assert published.manifest.source_url_sanitized.startswith(
        "local-import://"
    )
    assert blob_store.stat(published.manifest.object_key) is not None

    import_dir = import_store.root / preview.import_id
    assert not (import_dir / "paper.pdf").exists()
    assert (import_dir / "manifest.json").is_file()
    assert (import_dir / "commit.json").is_file()

    # payload 删除后 commit 重放仍然返回已发布的同一个 Resource。
    replayed, created = import_service.commit(
        import_id=preview.import_id,
        expected_preview_sha256=preview.preview_sha256,
        actor="test-user",
    )
    assert created is False
    assert replayed.resource_id == published.resource_id
    assert replayed.status == "published"
```

### 20.1 错误分类补强

`copy_for_worker()` 调用 `load_manifest()`、`load_commit_record()` 时可能得到 Local Import 领域错误。Worker 应把它们归类为 Resource integrity，而不是泛化为 internal error。

在 `app/resources/local_import.py::copy_for_worker()` 中，将 metadata 读取包裹为：

```python
        try:
            manifest = self.load_manifest(request.local_import_id)
            committed = self.load_commit_record(request.local_import_id)
        except LocalImportError as exc:
            raise ResourceIntegrityError(
                f"Local Import metadata invalid: {exc}"
            ) from exc
```

其余 identity 比较保持不变。这样 `ResourceWorker._error_payload()` 会输出 `category="integrity"`，与 Phase 15/29 的统一错误模型一致。

---

## 二十一、补充 Resource Schema 与 Hash 回归测试

> **本节类型：需要修改测试代码。**
>
> 需要修改：`tests/test_resource_schemas.py`、`tests/test_resource_request_hash.py`。

### 21.1 `tests/test_resource_schemas.py`

新增：

```python
def test_local_pdf_request_requires_exact_snapshot_identity() -> None:
    request = ResourceRequest(
        kind="paper_pdf",
        source_type="local_import",
        local_import_id="imp_" + "a" * 32,
        source_label="paper.pdf",
        local_snapshot_sha256="b" * 64,
        expected_sha256="b" * 64,
        purpose="paper input",
    )

    assert request.source_url is None
    assert request.source_type == "local_import"


def test_local_request_rejects_absolute_path_as_label() -> None:
    with pytest.raises(ValidationError):
        ResourceRequest(
            kind="paper_pdf",
            source_type="local_import",
            local_import_id="imp_" + "a" * 32,
            source_label="/data/private/paper.pdf",
            local_snapshot_sha256="b" * 64,
            expected_sha256="b" * 64,
            purpose="paper input",
        )


def test_remote_request_defaults_remain_backward_compatible() -> None:
    request = ResourceRequest.model_validate(
        {
            "kind": "paper_pdf",
            "source_url": "https://arxiv.org/pdf/1234",
            "purpose": "paper input",
        }
    )

    assert request.source_type == "remote_url"
```

### 21.2 `tests/test_resource_request_hash.py`

新增：

```python
def _local_pdf_request(*, snapshot: str) -> ResourceRequest:
    return ResourceRequest(
        kind="paper_pdf",
        source_type="local_import",
        local_import_id="imp_" + "a" * 32,
        source_label="paper.pdf",
        local_snapshot_sha256=snapshot,
        expected_sha256=snapshot,
        purpose="paper input",
    )


def test_local_request_hash_is_deterministic() -> None:
    first = _local_pdf_request(snapshot="b" * 64)
    second = _local_pdf_request(snapshot="b" * 64)

    assert resource_request_sha256(first) == resource_request_sha256(second)


def test_local_snapshot_change_invalidates_request_hash() -> None:
    first = _local_pdf_request(snapshot="b" * 64)
    second = _local_pdf_request(snapshot="c" * 64)

    assert resource_request_sha256(first) != resource_request_sha256(second)


def test_local_source_locator_never_contains_host_path() -> None:
    request = _local_pdf_request(snapshot="b" * 64)
    locator = resource_source_locator(request)

    assert locator.startswith("local-import://imp_")
    assert "/data/" not in locator
```

记得在测试 import 中加入：

```python
from app.resources.request_hash import (
    resource_request_sha256,
    resource_source_locator,
)
```

旧测试构造 `ResourceRequest(source_url=...)` 不必批量添加 `source_type`，默认值正是为了兼容旧代码。

---

## 二十二、增加前端 API 类型与客户端方法

> **本节类型：需要修改前端代码。**
>
> 需要修改：`web/src/api/types.ts`、`web/src/api/client.ts`。

### 22.1 修改 `web/src/api/types.ts`

在 `ResourceView` 中增加 `source_type`：

```typescript
export type ResourceView = {
  resource_id: string;
  kind: "paper_pdf" | "git_repository" | "checkpoint";
  source_type: "remote_url" | "local_import";
  source_url_sanitized: string;
  purpose: string;
  expected_git_commit: string | null;
  request_sha256: string;
  status: string;
  version: number;
  manifest: Record<string, unknown> | null;
  error: unknown;
};
```

新增：

```typescript
export type LocalImportPreview = {
  import_id: string;
  kind: "paper_pdf" | "git_repository";
  source_label: string;
  snapshot_sha256: string;
  size_bytes: number;
  media_type: string;
  git_commit: string | null;
  purpose: string;
  expires_at: string;
  preview_sha256: string;
};
```

### 22.2 修改 `web/src/api/client.ts` import

增加：

```typescript
  LocalImportPreview,
```

### 22.3 在 `api` 对象中增加方法

放在 Resource 方法附近：

```typescript
  inspectLocalImport(input: {
    kind: "paper_pdf" | "git_repository";
    sourcePath: string;
    purpose: string;
    expectedGitCommit?: string;
  }) {
    return request<LocalImportPreview>(
      "/v1/local-imports/inspect",
      {
        method: "POST",
        body: JSON.stringify({
          kind: input.kind,
          source_path: input.sourcePath,
          purpose: input.purpose,
          expected_git_commit: input.expectedGitCommit ?? null,
        }),
      },
    );
  },

  commitLocalImport(preview: LocalImportPreview) {
    return request<{ resource: ResourceView; replayed: boolean }>(
      `/v1/local-imports/${encodeURIComponent(preview.import_id)}/commit`,
      {
        method: "POST",
        body: JSON.stringify({
          expected_preview_sha256: preview.preview_sha256,
        }),
      },
    ).then((value) => value.resource);
  },
```

这里不发送原路径到 commit endpoint。第二步只发送 `import_id + preview_sha256`。

---

## 二十三、新增最小 Local Import Wizard

> **本节类型：需要新增前端代码。**
>
> 需要新增：`web/src/components/LocalImportWizard.tsx`。

本阶段前端保持简单：输入两个服务端绝对路径、inspect、显示哈希与 commit、确认并等待 published。

新建完整文件：

```tsx
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import type {
  LocalImportPreview,
  ResourceView,
} from "../api/types";
import {
  waitUntilPublished,
  type PublishedResourcePair,
} from "./ResourceWizard";


type Props = {
  onReady: (resources: PublishedResourcePair) => void;
};


export function LocalImportWizard({ onReady }: Props) {
  const [paperPath, setPaperPath] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [paperPreview, setPaperPreview] = (
    useState<LocalImportPreview | null>(null)
  );
  const [repoPreview, setRepoPreview] = (
    useState<LocalImportPreview | null>(null)
  );
  const [paperResource, setPaperResource] = (
    useState<ResourceView | null>(null)
  );
  const [repoResource, setRepoResource] = (
    useState<ResourceView | null>(null)
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(new AbortController());

  useEffect(() => () => abortRef.current.abort(), []);

  async function inspectBoth(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      // 顺序执行能让错误明确对应某个输入，也避免一次操作同时创建
      // 两个较大的 Git/PDF 快照。第一项成功后重试会复用已有 preview。
      let paper = paperPreview;
      if (!paper) {
        paper = await api.inspectLocalImport({
          kind: "paper_pdf",
          sourcePath: paperPath.trim(),
          purpose: "paper input for Web Console reproduction session",
        });
        setPaperPreview(paper);
      }

      if (!repoPreview) {
        const repository = await api.inspectLocalImport({
          kind: "git_repository",
          sourcePath: repoPath.trim(),
          purpose: "repository input for Web Console reproduction session",
        });
        setRepoPreview(repository);
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Local input inspect failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function commitOne(
    preview: LocalImportPreview,
    setResource: (resource: ResourceView) => void,
  ) {
    setBusy(true);
    setError(null);
    try {
      const queued = await api.commitLocalImport(preview);
      setResource(queued);
      const published = queued.status === "published"
        ? queued
        : await waitUntilPublished(
            queued.resource_id,
            abortRef.current.signal,
            setResource,
          );
      setResource(published);
    } catch (caught) {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Local input publication failed",
        );
      }
    } finally {
      setBusy(false);
    }
  }

  const ready = (
    paperResource?.status === "published"
    && repoResource?.status === "published"
  );

  return (
    <section className="resource-wizard local-import-wizard">
      {!paperPreview || !repoPreview ? (
        <form onSubmit={inspectBoth}>
          <p className="operator-note">
            Paths are resolved on the API server. Only configured local
            import roots are allowed.
          </p>
          <label>
            Paper PDF absolute server path
            <input
              required
              value={paperPath}
              placeholder="/data/tianshaoqi24/.../paper.pdf"
              onChange={(event) => {
                setPaperPath(event.currentTarget.value);
                setPaperPreview(null);
                setPaperResource(null);
              }}
            />
          </label>
          <label>
            Clean Git repository absolute server path
            <input
              required
              value={repoPath}
              placeholder="/data/tianshaoqi24/.../repository"
              onChange={(event) => {
                setRepoPath(event.currentTarget.value);
                setRepoPreview(null);
                setRepoResource(null);
              }}
            />
          </label>
          <button
            className="primary-action"
            disabled={busy}
            type="submit"
          >
            Inspect and snapshot local inputs
          </button>
        </form>
      ) : null}

      {[
        [paperPreview, paperResource, setPaperResource],
        [repoPreview, repoResource, setRepoResource],
      ].map(([previewValue, resourceValue, setterValue]) => {
        const preview = previewValue as LocalImportPreview | null;
        const resource = resourceValue as ResourceView | null;
        const setResource = setterValue as (
          value: ResourceView,
        ) => void;
        if (!preview) return null;
        return (
          <article className="resource-card" key={preview.import_id}>
            <strong>{preview.kind}</strong>
            <p>{preview.source_label}</p>
            <small>Snapshot SHA-256</small>
            <code>{preview.snapshot_sha256}</code>
            {preview.git_commit ? (
              <>
                <small>Exact Git commit</small>
                <code>{preview.git_commit}</code>
              </>
            ) : null}
            <small>Size</small>
            <p>{preview.size_bytes.toLocaleString()} bytes</p>
            <small>Preview SHA-256</small>
            <code>{preview.preview_sha256}</code>
            <p>Status: {resource?.status ?? "awaiting confirmation"}</p>
            {!resource ? (
              <button
                disabled={busy}
                onClick={() => void commitOne(preview, setResource)}
              >
                Confirm this exact local snapshot
              </button>
            ) : null}
          </article>
        );
      })}

      {paperPreview && repoPreview && !paperResource && !repoResource ? (
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            // 已生成但未 commit 的 snapshots 由后端 TTL 机会式清理。
            setPaperPreview(null);
            setRepoPreview(null);
          }}
        >
          Choose different local paths
        </button>
      ) : null}

      {error ? (
        <p className="inline-error" role="alert">{error}</p>
      ) : null}

      {ready ? (
        <button
          className="primary-action"
          onClick={() => onReady({
            paper: paperResource!,
            repository: repoResource!,
          })}
        >
          Continue with published local resources
        </button>
      ) : null}
    </section>
  );
}
```

数组中混合 State setter 会让 TypeScript 推断变宽，所以示例做了显式类型收窄。若你更看重类型简洁，可以抽取单独的 `LocalImportCard` 组件，但不要为了前端美化改变后端协议。

---

## 二十四、在 New Session 中增加来源切换

> **本节类型：需要修改前端代码。**
>
> 需要修改：`web/src/components/NewSessionPanel.tsx`、`web/src/styles/app.css`。

### 24.1 修改 `NewSessionPanel.tsx` import 与 state

增加 import：

```tsx
import { LocalImportWizard } from "./LocalImportWizard";
```

在组件 state 中增加：

```tsx
  const [inputMode, setInputMode] = useState<"remote" | "local">(
    "local",
  );
```

本项目当前主要在单机上使用，所以默认 `local`。如果你仍以远程 URL 为主，可以把默认值改回 `remote`。

### 24.2 替换 `!resources` 分支

把：

```tsx
        {!resources ? (
          <ResourceWizard onReady={setResources} />
        ) : (
```

替换为：

```tsx
        {!resources ? (
          <>
            <div className="input-mode-switch" role="group" aria-label="Input source">
              <button
                className={inputMode === "local" ? "active" : ""}
                type="button"
                onClick={() => setInputMode("local")}
              >
                Local server paths
              </button>
              <button
                className={inputMode === "remote" ? "active" : ""}
                type="button"
                onClick={() => setInputMode("remote")}
              >
                Remote HTTPS URLs
              </button>
            </div>
            {inputMode === "local" ? (
              <LocalImportWizard onReady={setResources} />
            ) : (
              <ResourceWizard onReady={setResources} />
            )}
          </>
        ) : (
```

切换模式时，未 commit 的 snapshot 可能留在 staging，之后由 TTL 清理。不要把另一个模式已经 published 的 Resource 自动混入当前 pair。

### 24.3 修改样式

在 `web/src/styles/app.css` 增加：

```css
.input-mode-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.45rem;
  margin: 1rem 0;
  border-radius: 0.9rem;
  padding: 0.35rem;
  background: rgb(101 112 106 / 10%);
}

.input-mode-switch button {
  border: 0;
  border-radius: 0.65rem;
  padding: 0.65rem;
  color: var(--ink-muted);
  background: transparent;
  cursor: pointer;
}

.input-mode-switch button.active {
  color: var(--ink);
  background: var(--paper-raised);
  box-shadow: var(--shadow);
}

.local-import-wizard code {
  display: block;
  overflow-wrap: anywhere;
  margin: 0.2rem 0 0.7rem;
  font-size: 0.78rem;
}
```

这已经足够支持本阶段，不需要引入文件树组件或复杂上传 UI。

---

## 二十五、增加前端测试

> **本节类型：需要新增测试代码。**
>
> 需要新增：`web/tests/local-import-wizard.test.tsx`。

新建完整文件：

```tsx
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { api } from "../src/api/client";
import { LocalImportWizard } from "../src/components/LocalImportWizard";
import type {
  LocalImportPreview,
  ResourceView,
} from "../src/api/types";


function preview(
  kind: "paper_pdf" | "git_repository",
): LocalImportPreview {
  const suffix = (
    kind === "paper_pdf" ? "a" : "b"
  ).repeat(32);
  return {
    import_id: `imp_${suffix}`,
    kind,
    source_label: kind === "paper_pdf" ? "paper.pdf" : "repo",
    snapshot_sha256: kind === "paper_pdf" ? "c".repeat(64) : "d".repeat(64),
    size_bytes: 1024,
    media_type: kind === "paper_pdf"
      ? "application/pdf"
      : "application/octet-stream",
    git_commit: kind === "git_repository" ? "e".repeat(40) : null,
    purpose: "test input",
    expires_at: "2026-08-07T00:00:00Z",
    preview_sha256: kind === "paper_pdf" ? "f".repeat(64) : "1".repeat(64),
  };
}


function published(value: LocalImportPreview): ResourceView {
  return {
    resource_id: `res_${value.import_id}`,
    kind: value.kind,
    source_type: "local_import",
    source_url_sanitized: `local-import://${value.import_id}/${value.source_label}`,
    purpose: value.purpose,
    expected_git_commit: value.git_commit,
    request_sha256: "2".repeat(64),
    status: "published",
    version: 3,
    manifest: {},
    error: null,
  };
}


afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});


describe("LocalImportWizard", () => {
  it("inspects paths, confirms hashes, and returns resources", async () => {
    const paper = preview("paper_pdf");
    const repo = preview("git_repository");
    const inspect = vi.spyOn(api, "inspectLocalImport")
      .mockResolvedValueOnce(paper)
      .mockResolvedValueOnce(repo);
    vi.spyOn(api, "commitLocalImport")
      .mockResolvedValueOnce(published(paper))
      .mockResolvedValueOnce(published(repo));
    const onReady = vi.fn();
    render(<LocalImportWizard onReady={onReady} />);

    fireEvent.change(
      screen.getByLabelText("Paper PDF absolute server path"),
      { target: { value: "/data/inputs/paper.pdf" } },
    );
    fireEvent.change(
      screen.getByLabelText("Clean Git repository absolute server path"),
      { target: { value: "/data/repos/paper-code" } },
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Inspect and snapshot local inputs",
      }),
    );

    await screen.findByText(paper.snapshot_sha256);
    expect(inspect.mock.calls[0][0]).toMatchObject({
      kind: "paper_pdf",
      sourcePath: "/data/inputs/paper.pdf",
    });
    expect(inspect.mock.calls[1][0]).toMatchObject({
      kind: "git_repository",
      sourcePath: "/data/repos/paper-code",
    });

    const confirmButtons = screen.getAllByRole("button", {
      name: "Confirm this exact local snapshot",
    });
    fireEvent.click(confirmButtons[0]);
    await waitFor(() => {
      expect(api.commitLocalImport).toHaveBeenCalledWith(paper);
    });

    fireEvent.click(
      screen.getAllByRole("button", {
        name: "Confirm this exact local snapshot",
      })[0],
    );
    await screen.findByRole("button", {
      name: "Continue with published local resources",
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue with published local resources",
      }),
    );

    expect(onReady).toHaveBeenCalledWith({
      paper: published(paper),
      repository: published(repo),
    });
  });
});
```

`import_id` fixture 必须满足 `imp_` 加 32 位小写十六进制；这里先选择字符再统一调用 `.repeat(32)`，避免条件表达式优先级错误。

---

## 二十六、测试顺序与命令

> **本节类型：验证步骤，不修改项目代码。**

所有命令都在项目根目录执行：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
```

### 26.1 先跑最小领域测试

```bash
python -m pytest -q \
  tests/test_local_import_service.py \
  tests/test_repo_capsule.py \
  tests/test_resource_schemas.py \
  tests/test_resource_request_hash.py
```

### 26.2 再跑 API 与 Worker 闭环

```bash
python -m pytest -q \
  tests/test_local_import_api.py \
  tests/test_local_import_worker.py \
  tests/test_resource_api.py \
  tests/test_resource_worker.py \
  tests/test_resource_job_submission.py
```

### 26.3 跑 Resource 全量回归

```bash
python -m pytest -q \
  tests/test_resource_schemas.py \
  tests/test_resource_request_hash.py \
  tests/test_resource_policy.py \
  tests/test_resource_validators.py \
  tests/test_http_resource_downloader.py \
  tests/test_git_resource_fetcher.py \
  tests/test_resource_worker.py \
  tests/test_resource_reconcile.py \
  tests/test_resource_api.py \
  tests/test_resource_job_submission.py \
  tests/test_local_import_service.py \
  tests/test_local_import_api.py \
  tests/test_local_import_worker.py
```

### 26.4 前端测试与构建

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot/web
npm test -- --run \
  tests/local-import-wizard.test.tsx \
  tests/command-selection.test.tsx \
  tests/timeline.test.tsx \
  tests/chat-panel.test.tsx
npm run build
```

### 26.5 Python 质量检查

回到项目根目录：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m ruff check app tests
python -m pytest -q
```

如果全量测试包含需要 PostgreSQL、容器或外部服务的可选集成测试，按项目已有 marker/env 约定执行；不要为了让默认测试通过而删除这些测试。

---

## 二十七、后端手工验收

> **本节类型：手工验收，不修改项目代码。**

本节使用：

```text
论文：
/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf

仓库：
/data/tianshaoqi24/PST-Convolution-main/
```

### 27.1 确认仓库是 clean 状态

```bash
git -C /data/tianshaoqi24/PST-Convolution-main status --short
git -C /data/tianshaoqi24/PST-Convolution-main rev-parse HEAD
```

第一条应无输出。若有输出，本阶段应拒绝导入。请先由你自己决定如何处理这些修改，不要让 Agent 自动 stash/reset/commit。

### 27.2 配置允许目录

在项目 `.env` 中确认：

```dotenv
ALLOWED_ROOT=/data/tianshaoqi24
LOCAL_IMPORT_ALLOWED_ROOTS=/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf:/data/tianshaoqi24/PST-Convolution-main
LOCAL_IMPORT_STAGING_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/resources/local_imports
LOCAL_IMPORT_TTL_SECONDS=86400
LOCAL_IMPORT_GIT_MAX_BYTES=2147483648
```

### 27.3 启动单机服务

使用 Phase 30 已有的统一入口：

```bash
python -m app.main serve-stack
```

另开终端检查：

```bash
curl -s http://127.0.0.1:8000/livez
curl -s http://127.0.0.1:8000/readyz
```

`readyz` 中应出现：

```text
local_import_staging: ready
```

### 27.4 用 API inspect PDF

如果 API 配置了 token，先设置：

```bash
export PAPER_COPILOT_TOKEN='你的本地 API token'
```

执行：

```bash
curl -sS \
  -H "Authorization: Bearer ${PAPER_COPILOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "paper_pdf",
    "source_path": "/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf",
    "purpose": "PSTNet paper input"
  }' \
  http://127.0.0.1:8000/v1/local-imports/inspect
```

保存响应中的：

```text
import_id
snapshot_sha256
preview_sha256
```

响应中不应出现 `/data/tianshaoqi24/`。

### 27.5 commit PDF snapshot

将上一步值填入：

```bash
curl -sS \
  -H "Authorization: Bearer ${PAPER_COPILOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "expected_preview_sha256": "<PDF_PREVIEW_SHA256>"
  }' \
  "http://127.0.0.1:8000/v1/local-imports/<PDF_IMPORT_ID>/commit"
```

期望：

```text
source_type = local_import
source_url_sanitized = local-import://imp_.../PSTNet...
status = queued / fetching / validating / published
```

### 27.6 inspect 并 commit Git repository

先得到 HEAD：

```bash
git -C /data/tianshaoqi24/PST-Convolution-main rev-parse HEAD
```

inspect：

```bash
curl -sS \
  -H "Authorization: Bearer ${PAPER_COPILOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "git_repository",
    "source_path": "/data/tianshaoqi24/PST-Convolution-main",
    "purpose": "PSTNet repository input",
    "expected_git_commit": "<EXACT_HEAD_SHA>"
  }' \
  http://127.0.0.1:8000/v1/local-imports/inspect
```

确认响应 `git_commit` 与 `<EXACT_HEAD_SHA>` 一致，然后 commit：

```bash
curl -sS \
  -H "Authorization: Bearer ${PAPER_COPILOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "expected_preview_sha256": "<REPO_PREVIEW_SHA256>"
  }' \
  "http://127.0.0.1:8000/v1/local-imports/<REPO_IMPORT_ID>/commit"
```

### 27.7 轮询 Resource

```bash
curl -sS \
  -H "Authorization: Bearer ${PAPER_COPILOT_TOKEN}" \
  "http://127.0.0.1:8000/v1/resources/<RESOURCE_ID>"
```

PDF 和 repository 最终都应成为 `published`。

### 27.8 检查 staging 与 Blob

```bash
find \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/resources/local_imports \
  -maxdepth 2 \
  -type f \
  -printf '%P\n'
```

发布后对应目录应保留：

```text
manifest.json
commit.json
.commit.lock（可以为空）
```

不应再保留大文件：

```text
paper.pdf
repository.bundle
```

实际 Blob 位于现有 Artifact/Resource BlobStore 的 `resources/sha256/...` object key 中。

### 27.9 检查没有泄露原始路径

先查询 Resource Event：

```bash
curl -sS \
  -H "Authorization: Bearer ${PAPER_COPILOT_TOKEN}" \
  "http://127.0.0.1:8000/v1/resources/<RESOURCE_ID>/events"
```

再在项目可持久化数据中检查。不要扫描 `/data/tianshaoqi24/` 全目录，只检查本项目：

```bash
rg -n \
  '/data/tianshaoqi24/PST-Convolution-main|PSTNet—Point' \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/resources \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/runs \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/logs
```

`source_label` 中允许出现论文 basename 或仓库名；不应出现完整绝对路径。

---

## 二十八、Web 端到端验收

> **本节类型：手工验收，不修改项目代码。**

1. 打开 Phase 30 Web Console；
2. 点击创建新的 reproduction session；
3. 选择 `Local server paths`；
4. 输入上节 PDF 和 Git 仓库绝对路径；
5. 点击 `Inspect and snapshot local inputs`；
6. 确认页面展示 PDF basename、SHA-256 和大小；
7. 确认页面展示 repo basename、bundle SHA-256 和 exact Git commit；
8. 页面不应显示 API staging path；
9. 分别点击 `Confirm this exact local snapshot`；
10. 等待两项成为 `published`；
11. 点击 `Continue with published local resources`；
12. 输入实验目标与 execution profile；
13. 创建 Job；
14. 打开 Job timeline，确认后续论文读取、仓库扫描、命令选择都正常；
15. Job 公开输入只显示 paper/repo 名和 Resource identity，不持有原始 host path；
16. 切回 `Remote HTTPS URLs`，确认 Phase 29/30 的旧流程仍能使用。

### 28.1 stale preview 验收

1. inspect 一次 PDF；
2. 记录 `preview_sha256`；
3. 使用 API 把最后一位替换后 commit；
4. 应返回 HTTP 409；
5. 不应创建 Resource；
6. 使用原 hash commit；
7. 应正常创建并批准同一个 snapshot。

### 28.2 路径边界验收

分别尝试：

```text
相对路径：pdf/paper.pdf
允许目录外路径：/etc/passwd
指向允许目录外的 symlink
Local Import staging 内的 paper.pdf
不存在的路径
PDF kind 对应一个目录
Git kind 对应一个普通文件
dirty Git repository
Git 子目录而不是 top-level
带 submodule 的 repository
带 Git LFS 标记的 repository
```

期望全部在 inspect 阶段失败，不创建 queued Resource，也不修改用户源文件。

---

## 二十九、常见问题

> **本节类型：问题排查，不修改项目代码。**

### 29.1 `source_path 不在 LOCAL_IMPORT_ALLOWED_ROOTS 内`

检查 API 进程读取到的 `.env` 是否正确，且输入的是服务端绝对路径。修改 `.env` 后需要重启 `serve-stack`。

### 29.2 Git 仓库提示 `repository_dirty`

这是预期安全行为。执行：

```bash
git -C <repo> status --short
```

由你人工决定提交、删除或保留修改。不要在 importer 中自动 `git reset --hard`、`git clean` 或 `git stash`。

### 29.3 commit 后 Resource 一直 `queued`

检查 Resource Worker 是否随 `serve-stack` 启动，以及 readiness 的 embedded worker 状态。Local Import API 只创建并批准 Resource，不直接执行 Worker。

### 29.4 Worker 报 `Local Import 未绑定当前 Resource`

检查 `commit()` 顺序是否是“写 commit record 后 approve”，并确认 API 和 Worker 的 `LOCAL_IMPORT_STAGING_ROOT` 指向同一主机目录。

### 29.5 Worker 报 `integrity` 而不是 `transport_unavailable`

本地快照不存在、hash 变化或 metadata 损坏属于 integrity，不是网络瞬时错误，不应自动重试下载。

### 29.6 published 后再次 commit 报 payload 不存在

说明 `commit()` 仍然无条件调用 `assert_payload_current()`。按第十七节区分首次 commit、awaiting approval 恢复和 published replay。

### 29.7 原始路径出现在 Resource API 响应

这是安全回归。检查：

```text
LocalImportManifest 是否保存 source_path
ResourceRequest 是否新增了 source_path
sanitize_resource_view 是否返回 staging path
Event payload 是否复制了 inspect body
日志是否记录整个 Pydantic request
```

本阶段只允许公开 `source_label` 和 `local-import://...`。

### 29.8 旧 Resource JSON 无法读取

确认 `ResourceRequest.source_type` 默认是 `remote_url`，新增本地字段都有 `None` 默认值。不要把旧字段 `source_url` 直接改成必需的新 union 而不做数据迁移。

### 29.9 PDF fixture 在安装 PyMuPDF 后突然失败

只写 `%PDF-` magic 的伪文件无法通过真实 parser。测试 helper 应在有 `fitz` 时创建真实一页 PDF。

### 29.10 Web 第二个确认按钮找不到

第一个 Resource published 后，其确认按钮会消失，因此 DOM 中剩下的第一个确认按钮就是另一个 preview。前端测试应在每次状态变化后重新查询按钮，不要复用旧 HTMLElement 引用。

---

## 三十、本阶段涉及的 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 30.1 Agent 输入也需要供应链身份

论文、代码和 checkpoint 不只是“文件参数”，它们决定 Agent 的推理和执行。只有绑定 hash/commit，才能说明一次运行到底基于什么输入。

### 30.2 Path 不是 Identity

同一个路径的内容可以变化，同一份内容也可以出现在多个路径。可恢复 Agent 应保存 content identity，而不是把宿主机路径当作事实。

### 30.3 Snapshot before Approval

用户应批准已经冻结的快照，而不是批准一个稍后可能变化的路径。这个原则与 Phase 17 Action Hash、Phase 32 run command hash 完全一致。

### 30.4 Validate at Boundary and at Use

inspect 时检查用于快速拒绝；commit 时检查用于绑定决定；Worker 使用时再检查用于防御中间篡改。多次验证针对的是不同时间边界，不是重复代码。

### 30.5 Capability Narrowing

Web 用户只能请求 importer 检查允许目录，Job 只能引用 `resource_id`，Agent 只能读取 materialized workspace。每经过一层，能力更窄，而不是把宿主机读权限层层传递。

### 30.6 Domain Idempotency

`import_id` 唯一表示一个快照，因此 `local-import:<import_id>` 比随机 HTTP key 更适合作为 Resource 幂等键。协议幂等应来自业务身份，而不只是客户端重试技巧。

### 30.7 Durable State 与大对象分层

manifest/commit 是小型 durable metadata；PDF/bundle 是暂存大对象；正式内容进入 content-addressed BlobStore。状态、暂存和发布对象应有不同生命周期。

### 30.8 Local 不等于 Trusted

单机单用户降低了认证复杂度，但不消除路径穿越、软链接、TOCTOU、dirty repo、陈旧确认和误操作风险。安全边界仍应由确定性代码保证。

---

## 三十一、完成标准

> **本节类型：最终验收，不修改项目代码。**

- Local Import 配置有 allowlist、staging root、TTL 和大小上限；
- staging 全部位于 `/data/tianshaoqi24/` 下的项目目录，不使用系统 `/tmp`；
- `ResourceRequest` 兼容旧 remote JSON，并支持脱敏 local identity；
- 远程 `canonicalize_url()` 没有被放宽；
- 本地来源使用 `local-import://` sanitized locator；
- inspect 只接受允许根目录内的绝对路径；
- 软链接、越界路径、不存在路径和类型不匹配均被拒绝；
- PDF 先复制再校验，并绑定 snapshot SHA-256；
- Git 仓库必须 clean、top-level、无 submodule/LFS，并生成已验证 bundle；
- preview hash 自洽，stale hash 返回 409；
- commit 使用 import_id 领域幂等，崩溃重试不创建重复 Resource；
- commit record 在 Resource approve 前落盘；
- Worker 获取本地快照时不调用网络；
- Worker 在使用时再次校验 manifest、commit record、size 和 SHA-256；
- 发布仍进入现有 BlobStore 和 ResourceManifest；
- Job 仍只接收 resource_id；
- published 后删除大 payload，commit replay 仍成功；
- API、Event、Artifact、日志和 telemetry 不包含原始绝对路径；
- Web 支持 remote/local 切换、预览和确认；
- 本地领域、API、Worker、Resource 回归、前端测试和 build 全部通过。

---

## 三十二、Phase 33 之后做什么

> **本节类型：后续路线，不修改项目代码。**

在单机单用户、优先把产品闭环做完整、暂不深挖复现结果成功率的前提下，下一阶段建议做：

```text
Phase 34：Artifact Preview、Safe Download 与单 Job Export Bundle
```

原因是输入端在 Phase 33 已闭环，下一处明显产品缺口是输出端：现在 Artifact 有 catalog 和 Chat citation，但用户仍需要更方便地查看 Markdown/JSON/日志、下载单个文件，并一键导出某个 Job 的 manifest、报告、日志和关键证据。

Phase 34 建议保持轻量：

```text
后端按 media type 安全预览文本 Artifact
严格大小和编码限制
Content-Disposition / nosniff
单 Artifact 下载
单 Job ZIP/TAR 导出
导出清单与 SHA-256
Web 简单 Preview/Download 按钮
```

再后续可以按优先级考虑：

```text
P1 单机数据保留、配额与 GC
P2 Chat Citation Golden Eval
P2 Run 对比与 Artifact diff
P3 由评测证明需要后再升级 dense Chat retrieval
```

仍不建议此时优先引入多 Agent、多用户 RBAC、Redis、消息队列或复杂前端框架。
