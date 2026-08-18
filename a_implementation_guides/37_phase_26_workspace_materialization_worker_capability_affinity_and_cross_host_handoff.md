# 37. Phase 26：Workspace Materialization、Worker Capability/Affinity 与跨主机接管

Phase 25 已经建立了共享控制面：

```text
PostgreSQL
    Job / Resume / Event / Lease
    Artifact metadata
    LangGraph checkpoint

S3 / MinIO
    immutable Artifact Blob
```

这使 Worker A 和 Worker B 可以竞争同一个 Job，也可以读取同一个 checkpoint。但是
checkpoint 里保存的仍然只是路径字符串：

```text
/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/<run_id>
/data/tianshaoqi24/PST-Convolution-main
/data/tianshaoqi24/.../paper.pdf
```

如果 Worker B 位于另一台主机，这些路径可能不存在；即使恰好存在，也不能证明内容与
Worker A 完全一致。因此：

```text
共享 Job + 共享 checkpoint != 可迁移执行环境
```

本阶段增加三层能力：

```text
调度层：Worker registration + capability matching + host affinity
数据层：immutable workspace manifest + content-addressed blob
恢复层：materialize + integrity verification + checkpoint path rebind
```

最终闭环是：

```text
Worker A 到达安全 interrupt
    -> 发布当前 workspace manifest
    -> PostgreSQL 原子保存 manifest pointer
    -> Job waiting_for_input
    -> Worker A 停止
    -> 用户提交 decision
    -> 兼容的 Worker B claim
    -> 从 S3/MinIO 物化 paper、repo 和 run files
    -> 校验 hash、Git commit、symlink 与外部数据引用
    -> 重绑定 checkpoint 中的本地路径
    -> 从原 interrupt 继续，不重跑前置节点
```

> **本教程中的源码均为待实现代码。**
>
> 除了明确标记为“知识说明”的小节，其余小节都会指出需要新增或修改的文件。
> 你仍然自己修改 `app/` 与 `tests/`；本教程本身只提供完整实现步骤和带注释代码。

---

## 一、先确认 Phase 25 的真实边界

> **本节类型：现状说明，不修改项目代码。**

当前 `GraphJobRunner._initial_state()` 直接把 Job 中的本地路径写进 state：

```python
return {
    "run_dir": claim.job.run_dir,
    "paper_path": request.paper_path,
    "repo_path": request.repo_path,
}
```

`run_context_node()`、`artifact_tools.require_run_root()`、
`ExecutionRunner.validate_cwd()` 又会校验这些路径必须位于当前进程配置的 root 内。

所以 Phase 25 的恢复实际是：

```text
同机 Worker A -> 同机 Worker B：可以
主机 A Worker  -> 主机 B Worker：路径和内容均未建立
```

Phase 25 的 PostgreSQL 测试还依赖 `TEST_DATABASE_URL`。如果直接运行相关测试但没有先
导出该变量，`tests/test_postgres_checkpoint.py` 会因读取
`os.environ["TEST_DATABASE_URL"]` 报 `KeyError`，这不等于 checkpoint 代码本身失败。

正确方式是：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent
set -a
source .env
set +a
export TEST_DATABASE_URL="${DATABASE_URL}"
python -m pytest -q \
  tests/test_postgres_job_store.py \
  tests/test_postgres_distributed_claim.py \
  tests/test_postgres_artifact_repository.py \
  tests/test_postgres_checkpoint.py \
  tests/test_postgres_cutover.py
```

不要把带密码的 URL 写进测试输出或提交到 Git。

---

## 二、本阶段的完成定义

> **本节类型：目标说明，不修改项目代码。**

完成后必须做到：

1. Worker 启动时注册独立 `worker_session_id`，并持续 heartbeat；
2. Worker 上报可执行 profile、backend、GPU/CUDA、可用磁盘和数据集标签；
3. Job 从受信任 Execution Profile 派生 `JobRequirements`；
4. PostgreSQL claim 只选择当前 Worker 能执行的 Job；
5. 不可迁移的 Job 绑定 `affinity_host_id`，其他主机不能 claim；
6. 初始 paper 和 clean Git repository 被封装为不可变 Workspace Manifest；
7. interrupt 时只发布恢复必需的 run files，不打包 cache、secret 或任意目录；
8. S3/MinIO 是跨主机 Blob 源；LocalBlobStore 只能产生 host-local manifest；
9. 新 Worker 在 claim 后、Graph 恢复前完成 materialization；
10. 每个文件都校验 `size + SHA-256`，Git 仓库校验 commit 与 clean state；
11. checkpoint 中的 `run_dir/repo_path/paper_path` 显式重绑定；
12. 旧 Worker 的 claim token 失效后不能发布新 manifest 或提交 binding；
13. 活跃或身份不明的 subprocess 禁止跨主机接管；
14. Worker A 与 Worker B 使用不同本地 workspace root，仍能从同一 interrupt 继续；
15. SQLite/单机旧路径保持兼容。

---

## 三、本阶段明确不做什么

> **本节类型：范围说明，不修改项目代码。**

- 不把整个 `/data/tianshaoqi24/` 打成 tar；
- 不自动上传训练数据集；
- 不复制 Conda environment；
- 不保存 API key、数据库密码、AWS secret 或完整进程环境；
- 不自动打包 Git ignored/untracked 文件；
- 不迁移有未提交修改的仓库；
- 第一版不支持 Git submodule 与 Git LFS workspace capsule；
- 不在旧主机仍有活跃 subprocess 时 requeue 到新主机；
- 不因为路径字符串相同就假设两台主机共享文件；
- 不让 LLM 决定可访问文件范围、Worker capability 或 affinity；
- 不让 `update_state()` 跳过审批节点；
- 不删除共享 Blob；本阶段 GC 只处理安全的本地 workspace epoch；
- 不引入 Redis、Kafka、RabbitMQ 或 Celery；
- 不宣称 exactly-once 外部执行。

---

## 四、为什么不用 tar 整体搬目录

> **本节类型：安全知识说明，不修改项目代码。**

直接执行下面这种方案很危险：

```text
tar -czf workspace.tar.gz repo/ runs/<run_id>/
```

风险包括：

```text
路径穿越          ../outside
绝对路径          /etc/...
symlink 逃逸       repo/link -> /data/secret
secret 泄漏        .env、credential、SSH key
无界体积           dataset、checkpoint、cache
竞态               打包过程中源文件继续变化
不可审计           不知道恢复真正依赖了哪些文件
```

本阶段采用逐文件 manifest：

```text
WorkspaceManifest
    entries[]
        logical_path
        role
        object_key
        sha256
        size_bytes
        media_type
        executable
```

Blob 使用内容地址：

```text
workspace/sha256/<sha-prefix>/<sha256>
```

Materializer 不解压用户控制的 archive。唯一特殊对象是由受信任 Git 命令创建、并经过
`git bundle verify` 的 repository bundle。

Git 官方文档说明 bundle 用于离线传输 Git objects 与 refs，也明确指出 bundle 不包含
working tree、index、stash、hooks 和 repository config：

- [Git bundle documentation](https://git-scm.com/docs/git-bundle)

这正好符合本阶段“只搬可验证 Git 身份，不搬本地主机状态”的边界。

---

## 五、为什么第一版只迁移 clean Git repository

> **本节类型：安全知识说明，不修改项目代码。**

假设仓库当前状态为：

```text
HEAD commit = abc123
tracked file model.py 有未提交修改
untracked file local_config.py 存在
```

只保存 `abc123` 会丢修改；自动保存 diff 又会遇到：

```text
diff 是否已人工审批？
untracked 文件是否包含 secret？
binary 文件如何处理？
patch 应用时 base 是否仍相同？
```

所以本阶段定义：

```text
clean repository
    -> 可创建 Git bundle，可跨 host

dirty repository
    -> manifest.portable = false
    -> affinity_host_id = 当前 host
    -> 不自动 stash/reset/commit
```

Phase 14 的文件修复如果已经把 patch promotion 到原仓库但没有提交，后续 Job 会保留
host affinity。这是有意的 fail-closed 行为，不是功能缺失。未来可以增加“reviewed dirty
patch capsule”，但必须把 base commit、patch hash、untracked allowlist 和审批记录一起
绑定。

---

## 六、三种 ID 不要混用

> **本节类型：模型说明，不修改项目代码。**

```text
worker_id
    运维可读逻辑名称，例如 pstnet-gpu-worker

worker_session_id
    每次进程启动生成的新 UUID；同名 worker 重启后必须变化

host_id
    主机稳定身份，由受信任配置显式提供，例如 gpu-host-a
```

还要区分：

```text
manifest_generation
    Workspace 内容快照版本；每次安全 seal 后递增

assignment_epoch
    Job 每次成功 claim 后递增；用于隔离旧 Worker 的本地写入

claim_token
    Phase 25 的数据库 fencing token；所有 manifest/binding 写入都必须校验
```

不能用 PID 当 `worker_session_id`，也不能用 hostname 自动替代 `host_id`。容器重建、主机
别名和 PID 复用都会破坏身份语义。

---

## 七、整体架构

> **本节类型：架构说明，不修改项目代码。**

```text
                         PostgreSQL
                ┌──────────────────────────┐
                │ jobs + requirements      │
                │ worker_sessions          │
                │ workspace_manifests      │
                │ workspace_assignments    │
                │ LangGraph checkpoint     │
                └─────────────┬────────────┘
                              │ metadata / fencing
                 ┌────────────┴────────────┐
                 │                         │
        Worker A / host-a          Worker B / host-b
        local epoch 1              local epoch 2
                 │                         │
                 └────────────┬────────────┘
                              │ immutable blobs
                       S3 / MinIO bucket
```

一个 portable manifest 只描述内容，不描述“所有主机都必须使用同一个绝对路径”。每个
Worker 都在自己的受控 root 下物化：

```text
<WORKER_WORKSPACE_ROOT>/jobs/<job_id>/epochs/<assignment_epoch>/
    source/
        paper.pdf
        external.log
    capsule/
        repository.bundle
    repo/
    run/
        inputs/
        analysis/
        planning/
        execution/
        debug/
        patches/
        reports/
        traces/
    .workspace-binding.json
```

不同 claim 使用不同 epoch 目录。即使旧 Worker 在租约失效后仍错误地写本地文件，也不
会污染新 claim 的工作区；它仍然无法通过 claim token 更新 PostgreSQL 指针。

---

## 八、安全接管状态机

> **本节类型：状态机说明，不修改项目代码。**

```text
queued
  -> claim + assignment_epoch++
  -> materializing
  -> workspace_ready
  -> Graph running
  -> Graph interrupt
  -> publish Artifact blobs
  -> seal workspace manifest
  -> waiting_for_input
  -> queue resume
  -> queued
  -> another compatible Worker claim
```

失败分支：

```text
capability 不匹配
    -> 保持 queued，不 claim

manifest hash/blob 校验失败
    -> reconciliation_required，不执行 Graph

dirty repo / unsafe interrupt / external ref 仅当前 host 可见
    -> affinity_host_id=current host

发现 active/ambiguous subprocess
    -> reconciliation_required，禁止跨 host

S3/MinIO 暂时不可用
    -> retryable failure，保持 checkpoint 与旧 manifest
```

---

## 九、需要新增和修改的文件

> **本节类型：文件清单，不修改项目代码。**

新增：

```text
app/workspace/__init__.py
app/workspace/errors.py
app/workspace/schemas.py
app/workspace/paths.py
app/workspace/capabilities.py
app/workspace/repository.py
app/workspace/repo_capsule.py
app/workspace/snapshot.py
app/workspace/materializer.py
app/workspace/rebind.py
app/workspace/manager.py
app/workspace/gc.py

alembic/versions/20260731_0002_worker_workspace_control.py

config/worker_capabilities.host-a.example.json
config/worker_capabilities.host-b.example.json

tests/test_worker_capabilities.py
tests/test_workspace_manifest.py
tests/test_repo_capsule.py
tests/test_workspace_materializer.py
tests/test_workspace_rebind.py
tests/test_workspace_scheduling.py
tests/test_workspace_fencing.py
tests/test_cross_host_workspace_handoff.py
tests/test_workspace_gc.py
```

修改：

```text
app/config.py
app/schemas.py
app/state.py
app/persistence/tables.py
app/job_runtime/schemas.py
app/job_runtime/ports.py
app/job_runtime/store.py
app/job_runtime/postgres_store.py
app/job_runtime/service.py
app/job_runtime/graph_runner.py
app/job_runtime/worker.py
app/job_runtime/process_reconcile.py
app/storage/ports.py
app/storage/local_blob_store.py
app/storage/s3_blob_store.py
app/storage/publisher.py
app/storage/factory.py
app/tools/artifact_tools.py
app/execution/cancellation.py
app/execution/environment.py
app/execution/profile_store.py
app/nodes/run_context_node.py
app/nodes/input_validation_node.py
app/nodes/action_builder_node.py
app/nodes/risk_check_node.py
app/tools/preflight_tools.py
app/tools/exec_tools.py
app/tools/repair_tools.py
app/tools/patch_tools.py
app/interaction/schemas.py
app/interaction/service.py
app/interaction/artifacts.py
app/api/routes.py
app/main.py
.env.example
.gitignore
config/execution_profiles.local.json
tests/conftest.py
a_implementation_guides/README.md
```

文件较多的原因不是要再造一套 Agent，而是这次变化同时跨越：

```text
Job scheduling
filesystem trust boundary
Artifact data plane
Graph checkpoint state
execution profile security boundary
API/CLI observability
```

不要把所有逻辑塞进 `JobWorker.run_once()`。

---

## 十、增加配置

> **本节类型：需要修改代码。**
>
> 修改：`app/config.py`、`.env.example`、`.gitignore`

### 10.1 修改 `app/config.py`

在 `Settings` 的 Job Runtime 配置附近增加：

```python
    # host_id 是运维配置的稳定主机身份，不能由 LLM 或 Job request 指定。
    worker_host_id: str = os.getenv(
        "WORKER_HOST_ID",
        "local-host",
    ).strip()

    worker_pool: str = os.getenv(
        "WORKER_POOL",
        "default",
    ).strip()

    # 每个 Worker 只允许在自己的 root 下创建 job/epoch workspace。
    worker_workspace_root: Path = Path(
        os.getenv(
            "WORKER_WORKSPACE_ROOT",
            "worker_workspaces/local-host",
        )
    )

    worker_capabilities_path: Path = Path(
        os.getenv(
            "WORKER_CAPABILITIES_PATH",
            "config/worker_capabilities.local.json",
        )
    )

    worker_session_lease_seconds: float = float(
        os.getenv("WORKER_SESSION_LEASE_SECONDS", "30")
    )

    worker_session_heartbeat_seconds: float = float(
        os.getenv("WORKER_SESSION_HEARTBEAT_SECONDS", "5")
    )

    # Repo bundle 和临时下载必须放在项目受控目录，不使用 /tmp。
    workspace_staging_root: Path = Path(
        os.getenv(
            "WORKSPACE_STAGING_ROOT",
            "workspace_staging",
        )
    )

    workspace_max_file_bytes: int = int(
        os.getenv(
            "WORKSPACE_MAX_FILE_BYTES",
            str(2 * 1024 * 1024 * 1024),
        )
    )

    workspace_max_manifest_bytes: int = int(
        os.getenv(
            "WORKSPACE_MAX_MANIFEST_BYTES",
            str(4 * 1024 * 1024),
        )
    )

    workspace_max_total_bytes: int = int(
        os.getenv(
            "WORKSPACE_MAX_TOTAL_BYTES",
            str(8 * 1024 * 1024 * 1024),
        )
    )

    workspace_git_timeout_seconds: float = float(
        os.getenv("WORKSPACE_GIT_TIMEOUT_SECONDS", "120")
    )

    workspace_gc_min_age_seconds: float = float(
        os.getenv("WORKSPACE_GC_MIN_AGE_SECONDS", "86400")
    )
```

在配置目录创建和校验区域增加：

```python
settings.worker_workspace_root.mkdir(
    parents=True,
    exist_ok=True,
)
settings.workspace_staging_root.mkdir(
    parents=True,
    exist_ok=True,
)

if not settings.worker_host_id:
    raise ValueError("WORKER_HOST_ID 不能为空")
if not settings.worker_pool:
    raise ValueError("WORKER_POOL 不能为空")
if (
    settings.worker_session_lease_seconds
    <= settings.worker_session_heartbeat_seconds * 2
):
    raise ValueError(
        "WORKER_SESSION_LEASE_SECONDS 必须大于 heartbeat 的 2 倍"
    )
if settings.workspace_max_file_bytes <= 0:
    raise ValueError("WORKSPACE_MAX_FILE_BYTES 必须大于 0")
if (
    settings.worker_workspace_root.expanduser().resolve()
    == settings.allowed_root.expanduser().resolve()
):
    raise ValueError(
        "WORKER_WORKSPACE_ROOT 不能直接等于 ALLOWED_ROOT"
    )
```

### 10.2 修改 `.env.example`

```dotenv
# Phase 26 Worker identity / workspace
WORKER_HOST_ID=gpu-host-a
WORKER_POOL=gpu
WORKER_WORKSPACE_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-a
WORKER_CAPABILITIES_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/config/worker_capabilities.host-a.json
WORKER_SESSION_LEASE_SECONDS=30
WORKER_SESSION_HEARTBEAT_SECONDS=5

WORKSPACE_STAGING_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/workspace_staging
WORKSPACE_MAX_FILE_BYTES=2147483648
WORKSPACE_MAX_MANIFEST_BYTES=4194304
WORKSPACE_MAX_TOTAL_BYTES=8589934592
WORKSPACE_GIT_TIMEOUT_SECONDS=120
WORKSPACE_GC_MIN_AGE_SECONDS=86400
```

### 10.3 修改 `.gitignore`

```gitignore
worker_workspaces/
workspace_staging/
config/worker_capabilities.local.json
config/worker_capabilities.host-a.json
config/worker_capabilities.host-b.json
```

示例文件使用 `.example.json` 后缀，可以提交；真实主机 capability 文件不提交。

---

## 十一、定义 Workspace 与 Worker schema

> **本节类型：需要新增代码。**
>
> 新增：`app/workspace/__init__.py`、`app/workspace/errors.py`、
> `app/workspace/schemas.py`

### 11.1 新增 `app/workspace/__init__.py`

```python
"""Phase 26 workspace scheduling、snapshot 与 materialization。"""
```

### 11.2 新增 `app/workspace/errors.py`

```python
class WorkspaceError(RuntimeError):
    """Workspace 子系统错误基类。"""


class WorkspaceIntegrityError(WorkspaceError):
    """Manifest、Blob、路径或 Git identity 校验失败。"""


class WorkspaceNotPortableError(WorkspaceError):
    """当前 workspace 只能由 affinity host 继续。"""


class WorkerCapabilityError(WorkspaceError):
    """Worker capability 配置不合法或不满足 Job。"""


class WorkspaceFencedError(WorkspaceError):
    """旧 claim/session 尝试更新当前 workspace pointer。"""
```

### 11.3 新增 `app/workspace/schemas.py`

```python
from __future__ import annotations

import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class WorkspaceModel(BaseModel):
    """共享控制面对象拒绝未知字段，防止版本漂移被静默吞掉。"""

    model_config = ConfigDict(extra="forbid")


class WorkerCapabilities(WorkspaceModel):
    """Worker 启动时从受信任配置加载的可调度能力。"""

    execution_profile_ids: list[str] = Field(min_length=1)
    execution_backends: list[Literal["local", "conda"]] = Field(
        min_length=1
    )
    # 代码根据本机 profile 计算并覆盖，不能盲信 JSON 文件。
    execution_policy_hashes: dict[str, str] = Field(default_factory=dict)
    cpu_count: int = Field(ge=1)
    memory_bytes: int = Field(ge=1)
    workspace_free_bytes: int = Field(ge=0)
    gpu_count: int = Field(default=0, ge=0)
    cuda_major: int | None = Field(default=None, ge=1)
    labels: list[str] = Field(default_factory=list)
    # key 是受信任 dataset label；API 公开视图不能返回 host-local path。
    dataset_mounts: dict[str, str] = Field(default_factory=dict)
    capability_version: str = "phase26-v1"

    @field_validator(
        "execution_profile_ids",
        "execution_backends",
        "labels",
    )
    @classmethod
    def unique_non_empty(cls, values: list[str]) -> list[str]:
        normalized = sorted({str(item).strip() for item in values})
        if any(not item for item in normalized):
            raise ValueError("capability 列表不能包含空字符串")
        return normalized

    @model_validator(mode="after")
    def validate_cuda(self) -> "WorkerCapabilities":
        if self.gpu_count == 0 and self.cuda_major is not None:
            raise ValueError("没有 GPU 时不能声明 cuda_major")
        return self


class WorkerIdentity(WorkspaceModel):
    worker_id: str = Field(min_length=1, max_length=200)
    worker_session_id: str = Field(min_length=1, max_length=200)
    host_id: str = Field(min_length=1, max_length=200)
    pool: str = Field(min_length=1, max_length=100)
    workspace_root: str = Field(min_length=1)
    capabilities: WorkerCapabilities


class WorkerSession(WorkerIdentity):
    status: Literal["active", "draining", "offline"]
    registered_at: str
    heartbeat_at: str
    lease_expires_at: str


class JobRequirements(WorkspaceModel):
    """由受信任 Execution Profile 派生，不能接受 LLM 自由生成。"""

    worker_pool: str = "default"
    execution_profile_id: str = Field(min_length=1)
    execution_policy_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_backend: Literal["local", "conda"]
    min_workspace_free_bytes: int = Field(default=0, ge=0)
    min_gpu_count: int = Field(default=0, ge=0)
    cuda_major: int | None = Field(default=None, ge=1)
    required_labels: list[str] = Field(default_factory=list)

    @field_validator("required_labels")
    @classmethod
    def normalize_labels(cls, values: list[str]) -> list[str]:
        labels = sorted({item.strip() for item in values})
        if any(not item for item in labels):
            raise ValueError("required_labels 不能包含空字符串")
        return labels


class RepositoryIdentity(WorkspaceModel):
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    branch: str = Field(min_length=1)
    clean: bool
    # dirty/host-affine fallback 没有可迁移 bundle。
    bundle_logical_path: str | None = None
    has_submodules: bool = False
    has_lfs: bool = False


WorkspaceEntryRole = Literal[
    "paper",
    "input_log",
    "repository_bundle",
    "run_artifact",
    "process_record",
    "process_log",
]


class WorkspaceBlobEntry(WorkspaceModel):
    logical_path: str
    role: WorkspaceEntryRole
    object_key: str
    sha256: str
    size_bytes: int = Field(ge=0)
    media_type: str = "application/octet-stream"
    executable: bool = False

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        lowered = value.lower()
        if not SHA256_PATTERN.fullmatch(lowered):
            raise ValueError("sha256 必须是 64 位小写十六进制")
        return lowered


class ExternalDataReference(WorkspaceModel):
    """数据集只保存引用和可达性要求，不自动上传内容。"""

    name: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    fingerprint: str | None = None
    required_worker_label: str = Field(min_length=1)


class WorkspaceSourcePaths(WorkspaceModel):
    """仅供同一 affinity host 复用；不能把这些路径当跨主机地址。"""

    run_dir: str | None = None
    repo_path: str
    paper_path: str
    log_path: str | None = None


class WorkspaceManifest(WorkspaceModel):
    manifest_version: Literal["phase26-v1"] = "phase26-v1"
    manifest_id: str
    manifest_hash: str
    job_id: str
    run_id: str
    generation: int = Field(ge=0)
    parent_manifest_id: str | None = None
    source_host_id: str
    source_worker_session_id: str | None = None
    entries: list[WorkspaceBlobEntry]
    repository: RepositoryIdentity
    external_data: list[ExternalDataReference] = Field(
        default_factory=list
    )
    portable: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    source_paths: WorkspaceSourcePaths | None = None
    created_at: str

    @model_validator(mode="after")
    def validate_portability(self) -> "WorkspaceManifest":
        logical_paths = [item.logical_path for item in self.entries]
        if len(logical_paths) != len(set(logical_paths)):
            raise ValueError("manifest logical_path 重复")
        if self.portable and self.blocked_reasons:
            raise ValueError("portable manifest 不能包含 blocked_reasons")
        if not self.portable and not self.blocked_reasons:
            raise ValueError("non-portable manifest 必须说明原因")
        if not self.portable and self.source_paths is None:
            raise ValueError(
                "non-portable manifest 必须保存 affinity host 的 source_paths"
            )
        return self


class WorkspaceBinding(WorkspaceModel):
    assignment_id: str
    assignment_epoch: int = Field(ge=1)
    assignment_token: str
    job_id: str
    run_id: str
    manifest_id: str
    manifest_hash: str
    manifest_generation: int = Field(ge=0)
    worker_session_id: str
    host_id: str
    workspace_root: str
    run_dir: str
    repo_path: str
    paper_path: str
    log_path: str | None = None
    status: Literal[
        "materializing",
        "ready",
        "released",
        "failed",
        "garbage_collected",
    ]
    created_at: str
    updated_at: str


class SchedulingExplanation(WorkspaceModel):
    compatible: bool
    reasons: list[str] = Field(default_factory=list)
```

这里刻意不把 `WorkspaceManifest` 塞进 LangGraph state。state 只保存当前 binding 和
manifest hash；完整 manifest 属于 PostgreSQL control plane。

---

## 十二、给 Execution Profile 增加调度要求

> **本节类型：需要修改代码与配置。**
>
> 修改：`app/schemas.py`、`app/execution/profile_store.py`、
> `config/execution_profiles.local.json`

### 12.1 修改 `ExecutionProfile`

在现有 `ExecutionProfile` 的 `enforcement_mode` 后增加默认字段，保持旧配置兼容：

```python
class ExecutionProfile(BaseModel):
    # 前面的 Phase 16 字段保持不变。

    enforcement_mode: Literal["best_effort", "strict"] = "best_effort"

    # Phase 26：这些字段由项目维护者配置，不允许 Job/LLM 降低要求。
    worker_pool: str = "default"
    min_workspace_free_bytes: int = Field(default=0, ge=0)
    min_gpu_count: int = Field(default=0, ge=0)
    cuda_major: int | None = Field(default=None, ge=1)
    required_worker_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_backend_fields(self) -> "ExecutionProfile":
        # 保留原有 conda 与 strict 检查。
        if self.backend == "conda":
            if not self.conda_executable:
                raise ValueError(
                    "conda 执行后端要求提供 conda_executable"
                )
            if not self.conda_prefix:
                raise ValueError(
                    "conda 执行后端要求提供 conda_prefix"
                )

        if (
            self.backend in {"local", "conda"}
            and self.enforcement_mode == "strict"
        ):
            raise ValueError(
                "local/conda 不支持 strict OS isolation"
            )

        if not self.writable_roots:
            self.writable_roots = [self.workspace_root]

        if self.min_gpu_count == 0 and self.cuda_major is not None:
            raise ValueError("cuda_major 要求至少一个 GPU")
        if not self.worker_pool.strip():
            raise ValueError("worker_pool 不能为空")
        self.required_worker_labels = sorted(
            {item.strip() for item in self.required_worker_labels}
        )
        if any(not item for item in self.required_worker_labels):
            raise ValueError("required_worker_labels 不能包含空值")
        return self
```

### 12.2 修改 profile fingerprint

在 `compute_execution_profile_fingerprint()` 的 `material` 中增加：

```python
material.update(
    {
        "worker_pool": profile.worker_pool,
        "min_workspace_free_bytes": profile.min_workspace_free_bytes,
        "min_gpu_count": profile.min_gpu_count,
        "cuda_major": profile.cuda_major,
        "required_worker_labels": sorted(
            profile.required_worker_labels
        ),
    }
)
```

调度能力改变会改变 profile fingerprint，旧审批不能继续沿用。

另外新增一个**只用于跨主机调度等价性**的 hash。它不包含 host-local path，但包含所有
安全策略：

```python
def compute_execution_policy_hash(
    profile: ExecutionProfile,
) -> str:
    material = {
        "profile_id": profile.profile_id,
        "backend": profile.backend,
        "inherited_env_keys": sorted(profile.inherited_env_keys),
        "env_keys": sorted(profile.env),
        "allowed_action_env_keys": sorted(
            profile.allowed_action_env_keys
        ),
        "allowed_programs": sorted(profile.allowed_programs),
        "blocked_arg_markers": sorted(profile.blocked_arg_markers),
        "network_policy": profile.network_policy,
        "budget": profile.budget.model_dump(),
        "enforcement_mode": profile.enforcement_mode,
        "worker_pool": profile.worker_pool,
        "min_workspace_free_bytes": profile.min_workspace_free_bytes,
        "min_gpu_count": profile.min_gpu_count,
        "cuda_major": profile.cuda_major,
        "required_worker_labels": sorted(
            profile.required_worker_labels
        ),
    }
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

`compute_execution_profile_fingerprint()` 继续用于 action approval，包含当前有效路径；
`compute_execution_policy_hash()` 用于 scheduler，忽略不同主机的 workspace/Conda 绝对
路径。Conda 环境内容身份第一版用受信任 label，例如 `env:pstnet-cu118-v1` 约束。

### 12.3 修改 PSTNet profile

在 profile JSON 中增加：

```json
{
  "worker_pool": "gpu",
  "min_workspace_free_bytes": 10737418240,
  "min_gpu_count": 1,
  "cuda_major": 11,
  "required_worker_labels": [
    "dataset:pstnet-ready"
  ]
}
```

`cuda_major` 要填实际运行环境要求，不要照抄示例。可以先执行：

```bash
nvidia-smi
python -c "import torch; print(torch.version.cuda); print(torch.cuda.device_count())"
```

如果本阶段只验收 CPU 分析节点，把 `min_gpu_count` 设为 `0`、删除 `cuda_major`，但不要
因此宣称训练环境已满足。

---

## 十三、Worker capability 配置与确定性匹配

> **本节类型：需要新增代码和配置。**
>
> 新增：`app/workspace/capabilities.py`、
> `config/worker_capabilities.host-a.example.json`、
> `config/worker_capabilities.host-b.example.json`

### 13.1 新增 capability 示例

`config/worker_capabilities.host-a.example.json`：

```json
{
  "execution_profile_ids": [
    "pstnet-local-supervised"
  ],
  "execution_backends": [
    "local"
  ],
  "cpu_count": 32,
  "memory_bytes": 68719476736,
  "workspace_free_bytes": 0,
  "gpu_count": 1,
  "cuda_major": 11,
  "labels": [
    "dataset:pstnet-ready",
    "arch:x86_64"
  ],
  "dataset_mounts": {
    "dataset:pstnet-ready": "/data/tianshaoqi24/datasets/pstnet"
  },
  "capability_version": "phase26-v1"
}
```

host-b 的格式相同，只填写真实能力。`workspace_free_bytes` 会在启动和 heartbeat 时由
代码根据 `WORKER_WORKSPACE_ROOT` 动态覆盖，配置文件里的值只是 schema 占位。

### 13.2 新增 `app/workspace/capabilities.py`

```python
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

import psutil

from app.config import settings
from app.execution.profile_store import (
    compute_execution_policy_hash,
    load_execution_profiles,
)
from app.schemas import ExecutionProfile
from app.workspace.errors import WorkerCapabilityError
from app.workspace.schemas import (
    JobRequirements,
    SchedulingExplanation,
    WorkerCapabilities,
    WorkerIdentity,
)


def requirements_from_profile(
    profile: ExecutionProfile,
) -> JobRequirements:
    """只从受信任 profile 派生，绝不接受模型自行降低要求。"""

    return JobRequirements(
        worker_pool=profile.worker_pool,
        execution_profile_id=profile.profile_id,
        execution_policy_hash=compute_execution_policy_hash(profile),
        execution_backend=profile.backend,
        min_workspace_free_bytes=profile.min_workspace_free_bytes,
        min_gpu_count=profile.min_gpu_count,
        cuda_major=profile.cuda_major,
        required_labels=profile.required_worker_labels,
    )


def load_worker_capabilities(
    path: Path | None = None,
) -> WorkerCapabilities:
    config_path = (path or settings.worker_capabilities_path).resolve()
    if not config_path.is_file():
        raise WorkerCapabilityError(
            f"Worker capability 文件不存在：{config_path}"
        )

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    declared = WorkerCapabilities.model_validate(payload)

    profiles = load_execution_profiles()
    missing = sorted(
        set(declared.execution_profile_ids) - set(profiles)
    )
    if missing:
        raise WorkerCapabilityError(
            "Worker 声明了本机不存在的 profile：" + ", ".join(missing)
        )

    actual_backends = {
        profiles[profile_id].backend
        for profile_id in declared.execution_profile_ids
    }
    if not actual_backends.issubset(
        set(declared.execution_backends)
    ):
        raise WorkerCapabilityError(
            "execution_backends 未覆盖已声明 profile"
        )

    workspace_root = settings.worker_workspace_root.resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(workspace_root).free

    normalized_mounts: dict[str, str] = {}
    allowed_root = settings.allowed_root.resolve()
    for label, raw_path in declared.dataset_mounts.items():
        if label not in declared.labels:
            raise WorkerCapabilityError(
                f"dataset_mount label 未出现在 labels：{label}"
            )
        mount = Path(raw_path).expanduser()
        if not mount.is_absolute():
            raise WorkerCapabilityError(
                f"dataset mount 必须是绝对路径：{label}"
            )
        resolved = mount.resolve()
        if resolved != allowed_root and allowed_root not in resolved.parents:
            raise WorkerCapabilityError(
                f"dataset mount 位于 ALLOWED_ROOT 外：{label}"
            )
        normalized_mounts[label] = str(resolved)

    return declared.model_copy(
        update={
            "cpu_count": os.cpu_count() or declared.cpu_count,
            "memory_bytes": int(psutil.virtual_memory().total),
            "workspace_free_bytes": int(free_bytes),
            "execution_policy_hashes": {
                profile_id: compute_execution_policy_hash(
                    profiles[profile_id]
                )
                for profile_id in declared.execution_profile_ids
            },
            "dataset_mounts": normalized_mounts,
        }
    )


def build_worker_identity(
    *,
    worker_id: str,
    worker_session_id: str | None = None,
) -> WorkerIdentity:
    return WorkerIdentity(
        worker_id=worker_id,
        worker_session_id=(
            worker_session_id or f"ws_{uuid4().hex}"
        ),
        host_id=settings.worker_host_id,
        pool=settings.worker_pool,
        workspace_root=str(
            settings.worker_workspace_root.resolve()
        ),
        capabilities=load_worker_capabilities(),
    )


def explain_compatibility(
    *,
    requirements: JobRequirements,
    worker: WorkerIdentity,
    affinity_host_id: str | None,
) -> SchedulingExplanation:
    """供单元测试、CLI explain 和 SQL 语义对照使用。"""

    caps = worker.capabilities
    reasons: list[str] = []

    if worker.pool != requirements.worker_pool:
        reasons.append("worker_pool_mismatch")
    if (
        requirements.execution_profile_id
        not in caps.execution_profile_ids
    ):
        reasons.append("execution_profile_missing")
    elif (
        caps.execution_policy_hashes.get(
            requirements.execution_profile_id
        )
        != requirements.execution_policy_hash
    ):
        reasons.append("execution_policy_hash_mismatch")
    if requirements.execution_backend not in caps.execution_backends:
        reasons.append("execution_backend_missing")
    if caps.workspace_free_bytes < requirements.min_workspace_free_bytes:
        reasons.append("workspace_disk_insufficient")
    if caps.gpu_count < requirements.min_gpu_count:
        reasons.append("gpu_count_insufficient")
    if (
        requirements.cuda_major is not None
        and caps.cuda_major != requirements.cuda_major
    ):
        reasons.append("cuda_major_mismatch")
    if not set(requirements.required_labels).issubset(set(caps.labels)):
        reasons.append("required_worker_label_missing")
    if affinity_host_id is not None and worker.host_id != affinity_host_id:
        reasons.append("host_affinity_mismatch")

    return SchedulingExplanation(
        compatible=not reasons,
        reasons=reasons,
    )
```

GPU 数量和 CUDA 版本第一版使用受信任运维配置，而不是让 Worker 任意调用并解析
`nvidia-smi`。后续可以增加受监管 probe，但“探测失败”必须降级为能力未知，不能猜测
可用。

---

## 十四、统一 managed run path 校验

> **本节类型：需要新增和修改代码。**
>
> 新增：`app/workspace/paths.py`
>
> 修改：`app/tools/artifact_tools.py`、`app/execution/cancellation.py`、
> `app/execution/environment.py`、`app/nodes/run_context_node.py`、
> `app/interaction/artifacts.py`、`app/job_runtime/service.py`

Phase 15 的 `RUNS_DIR` 校验不能直接删除；Phase 26 应把“唯一 root”扩展成“受信任 root
集合”。

### 14.1 新增 `app/workspace/paths.py`

```python
from __future__ import annotations

from pathlib import Path, PurePosixPath

from app.config import settings
from app.workspace.errors import WorkspaceIntegrityError


RUN_LAYERS = {
    "inputs",
    "analysis",
    "planning",
    "execution",
    "debug",
    "patches",
    "reports",
    "traces",
}


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def managed_run_roots() -> tuple[Path, ...]:
    return (
        settings.runs_dir.expanduser().resolve(),
        settings.worker_workspace_root.expanduser().resolve(),
    )


def require_managed_run_root(raw_path: str | Path) -> Path:
    candidate = Path(raw_path).expanduser().resolve()
    roots = managed_run_roots()
    if not any(
        candidate != root and root in candidate.parents
        for root in roots
    ):
        raise WorkspaceIntegrityError(
            f"run_dir 不在受信任 run root 内：{candidate}"
        )
    return candidate


def require_workspace_relative_path(value: str) -> PurePosixPath:
    logical = PurePosixPath(value)
    if (
        logical.is_absolute()
        or not logical.parts
        or any(part in {"", ".", ".."} for part in logical.parts)
    ):
        raise WorkspaceIntegrityError(
            f"无效 workspace logical_path：{value!r}"
        )
    return logical


def resolve_inside(root: Path, logical_path: str) -> Path:
    logical = require_workspace_relative_path(logical_path)
    target = root.joinpath(*logical.parts).resolve()
    if target == root or root not in target.parents:
        raise WorkspaceIntegrityError("workspace path 逃逸 root")
    return target


def create_run_layout_at(run_root: Path) -> dict[str, str]:
    checked = require_managed_run_root(run_root)
    layout = {"run_root": str(checked)}
    for layer in sorted(RUN_LAYERS):
        directory = checked / layer
        directory.mkdir(parents=True, exist_ok=True)
        layout[f"{layer}_dir"] = str(directory)
    return layout
```

### 14.2 修改 `artifact_tools.py`

导入：

```python
from app.workspace.paths import (
    create_run_layout_at,
    require_managed_run_root,
)
```

把 `create_run_layout` 改成兼容可选 root：

```python
def create_run_layout(
    run_id: str,
    *,
    run_root_override: str | Path | None = None,
) -> dict[str, str]:
    if not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError(f"无效的 run_id：{run_id!r}")

    if run_root_override is None:
        run_root = (settings.runs_dir / run_id).resolve()
    else:
        run_root = Path(run_root_override).expanduser().resolve()

    return create_run_layout_at(run_root)


def require_run_root(state: dict[str, Any]) -> Path:
    raw_run_dir = state.get("run_dir")
    if not raw_run_dir:
        raise ValueError("当前 state 缺少 run_dir")

    run_root = require_managed_run_root(str(raw_run_dir))
    run_root.mkdir(parents=True, exist_ok=True)
    return run_root
```

### 14.3 修改 `run_context_node.py`

替换原先固定从 `RUNS_DIR` 推导的部分：

```python
    run_id = existing_run_id or build_run_id(state.get("task_id"))
    layout = create_run_layout(
        run_id,
        run_root_override=(
            existing_run_dir if existing_run_dir else None
        ),
    )
    expected_run_dir = Path(layout["run_root"]).resolve()
    run_dir = str(expected_run_dir)
```

不要再把 managed workspace 的 `run_dir` 强制等同于
`settings.runs_dir / run_id`。

### 14.4 修改其他边界函数

下列函数都应调用 `require_managed_run_root()`，不要各自复制 root 判断：

```text
app/execution/cancellation.py
    require_control_dir()

app/execution/environment.py
    build_minimal_environment()

app/interaction/artifacts.py
    LocalArtifactCatalog._run_root()

app/job_runtime/service.py
    tail_log()
```

`LocalArtifactCatalog` 与 `tail_log()` 仍只能读取当前主机存在的文件。生产跨主机模式必须
使用 Published Artifact Catalog；API 不应假装能打开另一个 host 的本地 epoch。

---

## 十五、扩展 Job schema 与持久化端口

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/schemas.py`、`app/job_runtime/ports.py`

### 15.1 修改 `JobRecord` 与 `JobClaim`

先导入：

```python
from app.workspace.schemas import (
    JobRequirements,
    WorkerIdentity,
    WorkspaceBinding,
)
```

在 `JobRecord` 的 `run_dir/request` 后增加：

```python
class JobRecord(JobModel):
    # 原有 identity/request 字段保持不变。
    job_id: str
    idempotency_key: str
    request_hash: str
    thread_id: str
    run_id: str
    run_dir: str
    request: JobRequest

    # Phase 26 调度与 workspace pointer。
    requirements: JobRequirements
    affinity_host_id: str | None = None
    workspace_manifest_id: str
    workspace_manifest_generation: int = Field(ge=0)
    workspace_assignment_epoch: int = Field(ge=0)

    # 原有 status/version/attempt 字段保持不变。
```

在 ownership 字段旁增加：

```python
    worker_session_id: str | None = None
    worker_host_id: str | None = None
    workspace_assignment_token: str | None = None
```

更新 ownership validator：

```python
    @model_validator(mode="after")
    def validate_ownership(self) -> "JobRecord":
        owned = self.status in {"running", "cancelling"}
        ownership = (
            self.worker_id,
            self.worker_session_id,
            self.worker_host_id,
            self.claim_token,
            self.workspace_assignment_token,
            self.claimed_at,
            self.heartbeat_at,
            self.lease_expires_at,
        )
        if owned and any(value is None for value in ownership):
            raise ValueError(
                "running/cancelling Job 必须有完整 ownership"
            )
        return self
```

扩展 `JobClaim`：

```python
class JobClaim(JobModel):
    job: JobRecord
    claim_token: str
    worker: WorkerIdentity
    resume_request: JobResumeRequest | None = None
    workspace_binding: WorkspaceBinding | None = None
```

`workspace_binding` 在 claim 刚完成时仍为 `None`；Worker 完成 materialization 并把 binding
写回数据库后，使用 `model_copy()` 生成包含 binding 的内存 claim，再交给 Graph。

### 15.2 修改 `JobStore.submit()`

先导入：

```python
from app.workspace.schemas import (
    JobRequirements,
    WorkerIdentity,
    WorkerSession,
    WorkspaceBinding,
    WorkspaceManifest,
)
```

修改签名：

```python
    def submit(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        thread_id: str,
        run_id: str,
        run_dir: str,
        request: JobRequest,
        requirements: JobRequirements,
        initial_manifest: WorkspaceManifest,
        max_attempts: int,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
        ...
```

修改 claim：

```python
    def claim_next(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
        now: float | None = None,
    ) -> JobClaim | None:
        ...
```

新增 Worker session 方法：

```python
    def register_worker(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
    ) -> WorkerSession:
        ...

    def heartbeat_worker(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
    ) -> WorkerSession:
        ...

    def drain_worker(
        self,
        *,
        worker_session_id: str,
    ) -> WorkerSession:
        ...

    def list_workers(
        self,
        *,
        include_expired: bool = False,
        limit: int = 100,
    ) -> list[WorkerSession]:
        ...
```

新增 Workspace 方法：

```python
    def get_workspace_manifest(
        self,
        manifest_id: str,
    ) -> WorkspaceManifest:
        ...

    def begin_workspace_assignment(
        self,
        *,
        job_id: str,
        claim_token: str,
        worker: WorkerIdentity,
        manifest: WorkspaceManifest,
        assignment_token: str,
        workspace_root: str,
        run_dir: str,
        repo_path: str,
        paper_path: str,
        log_path: str | None,
    ) -> WorkspaceBinding:
        ...

    def mark_workspace_ready(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
    ) -> WorkspaceBinding:
        ...

    def fail_workspace_assignment(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
        reason: str,
    ) -> WorkspaceBinding:
        ...

    def current_workspace_binding(
        self,
        job_id: str,
    ) -> WorkspaceBinding | None:
        ...

    def seal_workspace_manifest(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
        manifest: WorkspaceManifest,
        affinity_host_id: str | None,
        actor: str,
    ) -> JobRecord:
        ...

    def list_workspace_gc_candidates(
        self,
        *,
        host_id: str,
        older_than: str,
        limit: int = 100,
    ) -> list[WorkspaceBinding]:
        ...

    def mark_workspace_garbage_collected(
        self,
        *,
        assignment_id: str,
        assignment_token: str,
        host_id: str,
    ) -> WorkspaceBinding:
        ...
```

所有改变 current manifest/binding 的方法都同时接收 `claim_token` 和
`assignment_token`。只校验 `worker_id` 不够，因为同名 Worker 重启后会复用逻辑名称。

### 15.3 SQLite 兼容策略

`SqliteJobStore` 也要满足新 Protocol，但不宣称跨主机：

```text
register_worker             保存本地 session row
claim_next                  运行相同 Python compatibility 判断
initial manifest            保存 JSON
workspace binding           使用本地路径
portable                    强制 false，affinity=local host
```

不要在 SQLite 实现里静默忽略 requirements；否则 contract tests 无法发现 Postgres 与
SQLite 语义漂移。

---

## 十六、增加 PostgreSQL 表

> **本节类型：需要修改数据库 metadata。**
>
> 修改：`app/persistence/tables.py`

在 `jobs` 增加列：

```python
    sa.Column(
        "requirements_json",
        JSONB,
        nullable=False,
    ),
    # 高频 claim 字段同时规范化，避免每次都做复杂 JSON cast。
    sa.Column("required_worker_pool", sa.Text, nullable=False),
    sa.Column("required_profile_id", sa.Text, nullable=False),
    sa.Column("required_policy_hash", sa.Text, nullable=False),
    sa.Column("required_backend", sa.Text, nullable=False),
    sa.Column(
        "min_workspace_free_bytes",
        sa.BigInteger,
        nullable=False,
        server_default="0",
    ),
    sa.Column(
        "min_gpu_count",
        sa.Integer,
        nullable=False,
        server_default="0",
    ),
    sa.Column("required_cuda_major", sa.Integer),
    sa.Column(
        "required_labels_json",
        JSONB,
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    ),
    sa.Column("affinity_host_id", sa.Text),
    sa.Column("workspace_manifest_id", sa.Text, nullable=False),
    sa.Column(
        "workspace_manifest_generation",
        sa.Integer,
        nullable=False,
        server_default="0",
    ),
    sa.Column(
        "workspace_assignment_epoch",
        sa.Integer,
        nullable=False,
        server_default="0",
    ),
    sa.Column("worker_session_id", sa.Text),
    sa.Column("worker_host_id", sa.Text),
    sa.Column("workspace_assignment_token", sa.Text),
```

`workspace_manifest_id` 的 foreign key 在定义顺序上可能需要通过
`sa.ForeignKeyConstraint` 后置添加；Alembic migration 中必须实际建立 FK。

新增表：

```python
worker_sessions = sa.Table(
    "worker_sessions",
    metadata,
    sa.Column("worker_session_id", sa.Text, primary_key=True),
    sa.Column("worker_id", sa.Text, nullable=False),
    sa.Column("host_id", sa.Text, nullable=False),
    sa.Column("worker_pool", sa.Text, nullable=False),
    sa.Column("workspace_root", sa.Text, nullable=False),
    sa.Column("capabilities_json", JSONB, nullable=False),
    sa.Column("profile_ids_json", JSONB, nullable=False),
    sa.Column("profile_hashes_json", JSONB, nullable=False),
    sa.Column("backends_json", JSONB, nullable=False),
    sa.Column("labels_json", JSONB, nullable=False),
    sa.Column("workspace_free_bytes", sa.BigInteger, nullable=False),
    sa.Column("gpu_count", sa.Integer, nullable=False),
    sa.Column("cuda_major", sa.Integer),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "status IN ('active','draining','offline')",
        name="valid_status",
    ),
)

sa.Index(
    "ix_worker_sessions_schedulable",
    worker_sessions.c.status,
    worker_sessions.c.worker_pool,
    worker_sessions.c.lease_expires_at,
)


workspace_manifests = sa.Table(
    "workspace_manifests",
    metadata,
    sa.Column("manifest_id", sa.Text, primary_key=True),
    sa.Column("manifest_hash", sa.Text, nullable=False, unique=True),
    sa.Column("job_id", sa.Text, nullable=False),
    sa.Column("run_id", sa.Text, nullable=False),
    sa.Column("generation", sa.Integer, nullable=False),
    sa.Column("parent_manifest_id", sa.Text),
    sa.Column("portable", sa.Boolean, nullable=False),
    sa.Column("source_host_id", sa.Text, nullable=False),
    sa.Column("source_worker_session_id", sa.Text),
    sa.Column("manifest_json", JSONB, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint(
        "job_id",
        "generation",
        name="uq_workspace_manifest_job_generation",
    ),
    sa.CheckConstraint(
        "generation >= 0",
        name="non_negative_generation",
    ),
)

sa.Index(
    "ix_workspace_manifests_job_generation",
    workspace_manifests.c.job_id,
    workspace_manifests.c.generation,
)


workspace_assignments = sa.Table(
    "workspace_assignments",
    metadata,
    sa.Column("assignment_id", sa.Text, primary_key=True),
    sa.Column(
        "job_id",
        sa.Text,
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    ),
    # run_id 是稳定的业务运行标识；job_id 是队列调度标识，二者不能混用。
    sa.Column("run_id", sa.Text, nullable=False),
    sa.Column("assignment_epoch", sa.Integer, nullable=False),
    sa.Column("assignment_token", sa.Text, nullable=False, unique=True),
    sa.Column("manifest_id", sa.Text, nullable=False),
    sa.Column("manifest_hash", sa.Text, nullable=False),
    sa.Column("manifest_generation", sa.Integer, nullable=False),
    sa.Column("worker_session_id", sa.Text, nullable=False),
    sa.Column("host_id", sa.Text, nullable=False),
    sa.Column("workspace_root", sa.Text, nullable=False),
    sa.Column("run_dir", sa.Text, nullable=False),
    sa.Column("repo_path", sa.Text, nullable=False),
    sa.Column("paper_path", sa.Text, nullable=False),
    sa.Column("log_path", sa.Text),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("error_code", sa.Text),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint(
        "job_id",
        "assignment_epoch",
        name="uq_workspace_assignment_job_epoch",
    ),
    sa.CheckConstraint(
        "status IN ('materializing','ready','released','failed',"
        "'garbage_collected')",
        name="valid_status",
    ),
)

sa.Index(
    "ix_workspace_assignments_job_epoch",
    workspace_assignments.c.job_id,
    workspace_assignments.c.assignment_epoch,
)
```

不要把每个 manifest entry 拆成数千条 SQL row。第一版 manifest 有严格字节上限，整体
JSONB 更容易做 hash、一致性校验和版本迁移；大文件内容仍只进 BlobStore。

---

## 十七、编写 Alembic migration

> **本节类型：需要新增数据库迁移。**
>
> 新增：`alembic/versions/20260731_0002_worker_workspace_control.py`

迁移必须显式写出列和表，不要只依赖 autogenerate。文件骨架：

```python
"""worker capability and workspace control plane

Revision ID: 20260731_0002
Revises: 20260731_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260731_0002"
down_revision: str | None = "20260731_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # 先建 manifest 表，因为 jobs.workspace_manifest_id 最终引用它。
    op.create_table(
        "workspace_manifests",
        sa.Column("manifest_id", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("parent_manifest_id", sa.Text(), nullable=True),
        sa.Column("portable", sa.Boolean(), nullable=False),
        sa.Column("source_host_id", sa.Text(), nullable=False),
        sa.Column("source_worker_session_id", sa.Text(), nullable=True),
        sa.Column(
            "manifest_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "generation >= 0",
            name="ck_workspace_manifests_non_negative_generation",
        ),
        sa.PrimaryKeyConstraint(
            "manifest_id",
            name="pk_workspace_manifests",
        ),
        sa.UniqueConstraint(
            "manifest_hash",
            name="uq_workspace_manifests_manifest_hash",
        ),
        sa.UniqueConstraint(
            "job_id",
            "generation",
            name="uq_workspace_manifest_job_generation",
        ),
    )

    op.create_table(
        "worker_sessions",
        sa.Column("worker_session_id", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("host_id", sa.Text(), nullable=False),
        sa.Column("worker_pool", sa.Text(), nullable=False),
        sa.Column("workspace_root", sa.Text(), nullable=False),
        sa.Column("capabilities_json", postgresql.JSONB(), nullable=False),
        sa.Column("profile_ids_json", postgresql.JSONB(), nullable=False),
        sa.Column("profile_hashes_json", postgresql.JSONB(), nullable=False),
        sa.Column("backends_json", postgresql.JSONB(), nullable=False),
        sa.Column("labels_json", postgresql.JSONB(), nullable=False),
        sa.Column("workspace_free_bytes", sa.BigInteger(), nullable=False),
        sa.Column("gpu_count", sa.Integer(), nullable=False),
        sa.Column("cuda_major", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active','draining','offline')",
            name="ck_worker_sessions_valid_status",
        ),
        sa.PrimaryKeyConstraint(
            "worker_session_id",
            name="pk_worker_sessions",
        ),
    )

    # 先用 nullable 列回填已有 Job，再收紧 NOT NULL。
    op.add_column(
        "jobs",
        sa.Column("requirements_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("required_worker_pool", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("required_profile_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("required_policy_hash", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("required_backend", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "min_workspace_free_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "min_gpu_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("required_cuda_major", sa.Integer(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "required_labels_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("affinity_host_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("workspace_manifest_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "workspace_manifest_generation",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "workspace_assignment_epoch",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("jobs", sa.Column("worker_session_id", sa.Text()))
    op.add_column("jobs", sa.Column("worker_host_id", sa.Text()))
    op.add_column(
        "jobs",
        sa.Column("workspace_assignment_token", sa.Text()),
    )

    # 已有 Job 没有可验证 workspace manifest，绝不能伪造成 portable。
    # 生产 cutover 前应先完成旧 active Job；这里只给 terminal 历史行回填 legacy 标记。
    op.execute(
        """
        UPDATE jobs
        SET requirements_json = jsonb_build_object(
                'worker_pool', 'legacy',
                'execution_profile_id', request_json->>'execution_profile_id',
                'execution_backend', 'local',
                'min_workspace_free_bytes', 0,
                'min_gpu_count', 0,
                'cuda_major', NULL,
                'required_labels', jsonb_build_array('legacy-host-only')
            ),
            required_worker_pool = 'legacy',
            required_profile_id = request_json->>'execution_profile_id',
            required_policy_hash = repeat('0', 64),
            required_backend = 'local'
        """
    )

    # workspace_manifest_id 无法安全伪造；存在旧行时先阻断 migration。
    connection = op.get_bind()
    legacy_count = connection.execute(
        sa.text("SELECT count(*) FROM jobs")
    ).scalar_one()
    if legacy_count:
        raise RuntimeError(
            "Phase 26 migration 检测到旧 Job；请先执行显式 legacy backfill 工具"
        )

    op.alter_column("jobs", "requirements_json", nullable=False)
    op.alter_column("jobs", "required_worker_pool", nullable=False)
    op.alter_column("jobs", "required_profile_id", nullable=False)
    op.alter_column("jobs", "required_policy_hash", nullable=False)
    op.alter_column("jobs", "required_backend", nullable=False)
    op.alter_column("jobs", "workspace_manifest_id", nullable=False)

    op.create_foreign_key(
        "fk_jobs_workspace_manifest_id_workspace_manifests",
        "jobs",
        "workspace_manifests",
        ["workspace_manifest_id"],
        ["manifest_id"],
    )

    op.create_table(
        "workspace_assignments",
        sa.Column("assignment_id", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("assignment_epoch", sa.Integer(), nullable=False),
        sa.Column("assignment_token", sa.Text(), nullable=False),
        sa.Column("manifest_id", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.Text(), nullable=False),
        sa.Column("manifest_generation", sa.Integer(), nullable=False),
        sa.Column("worker_session_id", sa.Text(), nullable=False),
        sa.Column("host_id", sa.Text(), nullable=False),
        sa.Column("workspace_root", sa.Text(), nullable=False),
        sa.Column("run_dir", sa.Text(), nullable=False),
        sa.Column("repo_path", sa.Text(), nullable=False),
        sa.Column("paper_path", sa.Text(), nullable=False),
        sa.Column("log_path", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('materializing','ready','released','failed',"
            "'garbage_collected')",
            name="ck_workspace_assignments_valid_status",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.job_id"],
            ondelete="CASCADE",
            name="fk_workspace_assignments_job_id_jobs",
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["workspace_manifests.manifest_id"],
            name="fk_workspace_assignments_manifest_id_workspace_manifests",
        ),
        sa.PrimaryKeyConstraint(
            "assignment_id",
            name="pk_workspace_assignments",
        ),
        sa.UniqueConstraint(
            "assignment_token",
            name="uq_workspace_assignments_assignment_token",
        ),
        sa.UniqueConstraint(
            "job_id",
            "assignment_epoch",
            name="uq_workspace_assignment_job_epoch",
        ),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Phase 26 downgrade 可能丢失 workspace fencing 历史；"
        "请从数据库备份恢复，不提供自动 downgrade"
    )
```

上面故意在检测到旧 Job 时停止，而不是生成假的 manifest。正式项目可以再写
`backfill-phase26-workspaces`：逐个 terminal Job 读取 published Artifact，生成
`portable=false` 的 legacy manifest；active/waiting Job 仍必须先处理完或人工取消。

迁移前后检查：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent
set -a
source .env
set +a

python -m alembic current
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

---

## 十八、注册 Worker session

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/postgres_store.py`、`app/job_runtime/store.py`

`PostgresJobStore` 增加 Worker row 转换：

```python
def _row_to_worker_session(row: Any) -> WorkerSession:
    return WorkerSession(
        worker_id=str(row["worker_id"]),
        worker_session_id=str(row["worker_session_id"]),
        host_id=str(row["host_id"]),
        pool=str(row["worker_pool"]),
        workspace_root=str(row["workspace_root"]),
        capabilities=WorkerCapabilities.model_validate(
            row["capabilities_json"]
        ),
        status=str(row["status"]),
        registered_at=row["registered_at"].isoformat(),
        heartbeat_at=row["heartbeat_at"].isoformat(),
        lease_expires_at=row["lease_expires_at"].isoformat(),
    )
```

实现注册与 heartbeat：

```python
def register_worker(
    self,
    *,
    worker: WorkerIdentity,
    lease_seconds: float,
) -> WorkerSession:
    with self.engine.begin() as connection:
        current = database_clock(connection)
        lease_expires = current + timedelta(seconds=lease_seconds)
        caps = worker.capabilities

        # session_id 每次进程启动唯一；重复注册同一 session 必须内容一致。
        existing = connection.execute(
            sa.select(worker_sessions).where(
                worker_sessions.c.worker_session_id
                == worker.worker_session_id
            )
        ).mappings().one_or_none()

        values = {
            "worker_session_id": worker.worker_session_id,
            "worker_id": worker.worker_id,
            "host_id": worker.host_id,
            "worker_pool": worker.pool,
            "workspace_root": worker.workspace_root,
            "capabilities_json": caps.model_dump(),
            "profile_ids_json": caps.execution_profile_ids,
            "profile_hashes_json": caps.execution_policy_hashes,
            "backends_json": caps.execution_backends,
            "labels_json": caps.labels,
            "workspace_free_bytes": caps.workspace_free_bytes,
            "gpu_count": caps.gpu_count,
            "cuda_major": caps.cuda_major,
            "status": "active",
            "heartbeat_at": current,
            "lease_expires_at": lease_expires,
        }

        if existing is None:
            connection.execute(
                worker_sessions.insert().values(
                    **values,
                    registered_at=current,
                )
            )
        else:
            immutable_identity = (
                existing["worker_id"],
                existing["host_id"],
                existing["workspace_root"],
            )
            expected_identity = (
                worker.worker_id,
                worker.host_id,
                worker.workspace_root,
            )
            if immutable_identity != expected_identity:
                raise JobConflictError(
                    "worker_session_id 被不同身份复用"
                )
            connection.execute(
                worker_sessions.update()
                .where(
                    worker_sessions.c.worker_session_id
                    == worker.worker_session_id
                )
                .values(**values)
            )

        row = connection.execute(
            sa.select(worker_sessions).where(
                worker_sessions.c.worker_session_id
                == worker.worker_session_id
            )
        ).mappings().one()
        return _row_to_worker_session(row)


def heartbeat_worker(
    self,
    *,
    worker: WorkerIdentity,
    lease_seconds: float,
) -> WorkerSession:
    # 重新加载 capability 可以更新磁盘余量；session 身份不能改变。
    return self.register_worker(
        worker=worker,
        lease_seconds=lease_seconds,
    )


def drain_worker(
    self,
    *,
    worker_session_id: str,
) -> WorkerSession:
    with self.engine.begin() as connection:
        current = database_clock(connection)
        row = connection.execute(
            worker_sessions.update()
            .where(
                worker_sessions.c.worker_session_id
                == worker_session_id
            )
            .values(status="draining", heartbeat_at=current)
            .returning(worker_sessions)
        ).mappings().one_or_none()
        if row is None:
            raise JobNotFoundError("Worker session 不存在")
        return _row_to_worker_session(row)
```

`draining` Worker 可以续租已经 claim 的 Job，但不能 claim 新 Job。不要把 shutdown 直接
写成 `offline`；进程可能仍在完成当前 Graph chunk。

---

## 十九、让 capability matching 进入 claim 事务

> **本节类型：需要修改核心 claim 代码。**
>
> 修改：`app/job_runtime/postgres_store.py`

错误做法：

```text
claim 任意 queued Job
    -> Python 检查 capability
    -> 不匹配再 requeue
```

这会增加 attempt_count、产生事件噪声，并可能让多个不兼容 Worker 无限争抢同一个 Job。

正确做法是在 `SELECT ... FOR UPDATE SKIP LOCKED` 中过滤。替换
`PostgresJobStore.claim_next()`：

```python
def claim_next(
    self,
    *,
    worker: WorkerIdentity,
    lease_seconds: float,
    now: float | None = None,
) -> JobClaim | None:
    del now
    claim_token = f"claim_{uuid4().hex}"
    assignment_token = f"wa_{uuid4().hex}"

    with self.engine.begin() as connection:
        current = database_clock(connection)

        session = connection.execute(
            sa.select(worker_sessions).where(
                worker_sessions.c.worker_session_id
                == worker.worker_session_id
            )
        ).mappings().one_or_none()
        if session is None:
            raise JobConflictError("Worker 尚未注册")
        if session["status"] != "active":
            return None
        if session["lease_expires_at"] <= current:
            raise JobConflictError("Worker session lease 已过期")

        caps = WorkerCapabilities.model_validate(
            session["capabilities_json"]
        )

        profile_pairs = [
            sa.and_(
                jobs.c.required_profile_id == profile_id,
                jobs.c.required_policy_hash == policy_hash,
            )
            for profile_id, policy_hash
            in caps.execution_policy_hashes.items()
        ]
        if not profile_pairs:
            return None

        # required_labels_json <@ worker labels。
        # 绑定参数显式 cast JSONB，避免驱动把 list 当普通 SQL array。
        labels_cover = jobs.c.required_labels_json.op("<@")(
            sa.cast(
                sa.bindparam(
                    "worker_labels",
                    value=caps.labels,
                ),
                JSONB,
            )
        )

        filters = [
            jobs.c.status == "queued",
            jobs.c.cancel_requested.is_(False),
            jobs.c.available_at <= current,
            jobs.c.required_worker_pool == worker.pool,
            jobs.c.required_profile_id.in_(
                caps.execution_profile_ids
            ),
            sa.or_(*profile_pairs),
            jobs.c.required_backend.in_(
                caps.execution_backends
            ),
            jobs.c.min_workspace_free_bytes
            <= caps.workspace_free_bytes,
            jobs.c.min_gpu_count <= caps.gpu_count,
            sa.or_(
                jobs.c.required_cuda_major.is_(None),
                jobs.c.required_cuda_major == caps.cuda_major,
            ),
            labels_cover,
            sa.or_(
                jobs.c.affinity_host_id.is_(None),
                jobs.c.affinity_host_id == worker.host_id,
            ),
        ]

        candidate = connection.execute(
            sa.select(jobs.c.job_id)
            .where(*filters)
            .order_by(
                jobs.c.available_at.asc(),
                jobs.c.created_at.asc(),
            )
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        if candidate is None:
            return None

        lease_expires = current + timedelta(seconds=lease_seconds)
        connection.execute(
            jobs.update()
            .where(jobs.c.job_id == candidate)
            .values(
                status="running",
                version=jobs.c.version + 1,
                attempt_count=jobs.c.attempt_count + 1,
                worker_id=worker.worker_id,
                worker_session_id=worker.worker_session_id,
                worker_host_id=worker.host_id,
                claim_token=claim_token,
                workspace_assignment_token=assignment_token,
                workspace_assignment_epoch=(
                    jobs.c.workspace_assignment_epoch + 1
                ),
                claimed_at=current,
                heartbeat_at=current,
                lease_expires_at=lease_expires,
                updated_at=current,
            )
        )
        row = self._get_row(connection, candidate)

        resume = None
        if row["pending_resume_id"] is not None:
            resume_row = connection.execute(
                sa.select(job_resumes).where(
                    job_resumes.c.resume_id
                    == row["pending_resume_id"]
                )
            ).mappings().one_or_none()
            if resume_row is None or resume_row["status"] != "pending":
                raise JobConflictError(
                    "pending_resume_id 无有效 resume"
                )
            resume = self._row_to_resume(resume_row)

        self._append_event(
            connection,
            job_id=candidate,
            event_type="job_claimed",
            actor=worker.worker_id,
            payload={
                "attempt_count": row["attempt_count"],
                "worker_session_id": worker.worker_session_id,
                "host_id": worker.host_id,
                "workspace_assignment_epoch": row[
                    "workspace_assignment_epoch"
                ],
            },
            now=current,
        )
        return JobClaim(
            job=self._row_to_record(row),
            claim_token=claim_token,
            worker=worker,
            resume_request=resume,
        )
```

PostgreSQL JSONB `<@` 表示左侧 JSON 被右侧包含，可用于
`required_labels <@ worker_labels`。参考：

- [PostgreSQL JSON functions and operators](https://www.postgresql.org/docs/18/functions-json.html)

必须增加集成测试，对照 Python `explain_compatibility()` 与 SQL claim 的结果，避免两套
规则长期漂移。

---

## 二十、Job row 转换与 ownership 清理

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/postgres_store.py`、`app/job_runtime/store.py`

`_row_to_record()` 要解析：

```python
requirements=JobRequirements.model_validate(
    row["requirements_json"]
),
affinity_host_id=row["affinity_host_id"],
workspace_manifest_id=str(row["workspace_manifest_id"]),
workspace_manifest_generation=int(
    row["workspace_manifest_generation"]
),
workspace_assignment_epoch=int(
    row["workspace_assignment_epoch"]
),
worker_session_id=row["worker_session_id"],
worker_host_id=row["worker_host_id"],
workspace_assignment_token=row[
    "workspace_assignment_token"
],
```

所有释放 Job ownership 的状态转换都要一起清空：

```python
worker_id=None,
worker_session_id=None,
worker_host_id=None,
claim_token=None,
workspace_assignment_token=None,
claimed_at=None,
heartbeat_at=None,
lease_expires_at=None,
```

包括：

```text
mark_waiting
mark_succeeded
mark_cancelled
mark_failed terminal
requeue_expired
resolve_reconciliation
```

但 `workspace_assignments` 的历史 row 不删除；它记录某个 epoch 曾经由谁物化，便于审计
和 GC。

---

## 二十一、增加 BlobStore 的共享范围

> **本节类型：需要修改代码。**
>
> 修改：`app/storage/ports.py`、`app/storage/local_blob_store.py`、
> `app/storage/s3_blob_store.py`

跨主机是否可恢复不能通过 `backend_name` 猜。给 `BlobStore` Protocol 增加显式属性：

```python
from typing import Literal


class BlobStore(Protocol):
    backend_name: str
    sharing_scope: Literal["host", "shared"]

    # 原有 ensure_ready/stat/put_file/open 保持不变。
```

两个实现分别声明：

```python
class LocalBlobStore:
    backend_name = "local"
    sharing_scope = "host"
```

```python
class S3BlobStore:
    backend_name = "s3"
    sharing_scope = "shared"
```

MinIO 通过 S3 adapter 使用时也属于 `shared`，前提是两个 Worker 访问的是同一 endpoint、
bucket 与 prefix。仅仅都设置 `ARTIFACT_BLOB_BACKEND=s3` 还不够，手工验收必须比较实际
配置。

Amazon S3 对成功 PUT 后的 GET/HEAD 提供 strong read-after-write consistency，但这不
替代应用自己的 manifest pointer 与 hash 校验：

- [Amazon S3 consistency model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)

---

## 二十二、Canonical manifest hash

> **本节类型：需要新增代码。**
>
> 新增：`app/workspace/repository.py`

该模块同时放 canonical hash 和 control-plane repository。先写纯函数部分：

```python
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.schemas import WorkspaceManifest


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def workspace_manifest_hash(
    manifest: WorkspaceManifest | dict[str, Any],
) -> str:
    if isinstance(manifest, WorkspaceManifest):
        payload = manifest.model_dump()
    else:
        payload = dict(manifest)

    # identity/观测时间不能改变内容身份，否则 commit response 丢失后无法幂等重放。
    payload.pop("manifest_hash", None)
    payload.pop("manifest_id", None)
    payload.pop("created_at", None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def validate_manifest_hash(manifest: WorkspaceManifest) -> None:
    actual = workspace_manifest_hash(manifest)
    if actual != manifest.manifest_hash:
        raise WorkspaceIntegrityError(
            "Workspace manifest hash 校验失败"
        )
```

生成 manifest 时先创建占位 identity，计算语义 hash，再使用
`manifest_id=f"wm_{digest[:32]}"`。`manifest_id`、`manifest_hash` 和 `created_at` 不参与
内容 hash；Job/run/generation/parent、entries、repo identity、external refs 和 portability
全部参与。不要对 pretty-printed JSON 文件内容直接 hash，否则缩进和换行会改变身份。

---

## 二十三、创建 clean Git repository capsule

> **本节类型：需要新增代码。**
>
> 新增：`app/workspace/repo_capsule.py`

完整实现：

```python
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.tools.artifact_tools import sha256_file
from app.workspace.errors import (
    WorkspaceIntegrityError,
    WorkspaceNotPortableError,
)
from app.workspace.schemas import RepositoryIdentity


@dataclass(frozen=True)
class RepositoryCapsule:
    identity: RepositoryIdentity
    bundle_path: Path
    sha256: str
    size_bytes: int


def _run_git(
    repo: Path,
    args: list[str],
    *,
    timeout: float | None = None,
) -> str:
    """只执行代码中固定构造的 token，不接受 shell command 字符串。"""

    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=(timeout or settings.workspace_git_timeout_seconds),
        shell=False,
        env={
            "PATH": os.environ.get("PATH", ""),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1",
            # 禁止 Git 调用交互式 credential helper。
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise WorkspaceIntegrityError(
            f"Git command failed：git {' '.join(args[:2])}；"
            f"{message[:500]}"
        )
    return completed.stdout.strip()


def _require_clean_repository(repo: Path) -> tuple[str, str]:
    if not repo.is_dir():
        raise WorkspaceIntegrityError(f"repo 不存在：{repo}")

    top = Path(
        _run_git(repo, ["rev-parse", "--show-toplevel"])
    ).resolve()
    if top != repo:
        raise WorkspaceIntegrityError(
            "repo_path 必须是 Git top-level，不能是任意子目录"
        )

    status = _run_git(
        repo,
        ["status", "--porcelain=v1", "--untracked-files=all"],
    )
    if status:
        raise WorkspaceNotPortableError(
            "repository_dirty：不会自动 stash/reset/commit"
        )

    try:
        branch = _run_git(
            repo,
            ["symbolic-ref", "--quiet", "--short", "HEAD"],
        )
    except WorkspaceIntegrityError as exc:
        # symbolic-ref 在 detached HEAD 下返回非 0。这里应转成“不可迁移”，
        # 而不是误报为 bundle 内容损坏。
        raise WorkspaceNotPortableError(
            "detached_head：第一版要求有命名 branch"
        ) from exc

    commit = _run_git(repo, ["rev-parse", "HEAD"])
    return branch, commit


def _reject_unsupported_repository_features(repo: Path) -> None:
    gitmodules = repo / ".gitmodules"
    if gitmodules.exists():
        raise WorkspaceNotPortableError(
            "git_submodule_unsupported"
        )

    # 没安装 git-lfs 时命令可能失败；再检查 attributes 中的常见标记。
    attributes = repo / ".gitattributes"
    if attributes.is_file():
        text = attributes.read_text(
            encoding="utf-8",
            errors="replace",
        )
        if "filter=lfs" in text:
            raise WorkspaceNotPortableError("git_lfs_unsupported")


def inspect_repository_identity(
    repo_path: str | Path,
) -> RepositoryIdentity:
    """即使 dirty，也记录当前可验证的 commit/branch 与 feature 状态。"""

    repo = Path(repo_path).expanduser().resolve()
    top = Path(
        _run_git(repo, ["rev-parse", "--show-toplevel"])
    ).resolve()
    if top != repo:
        raise WorkspaceIntegrityError("repo_path 不是 Git top-level")

    commit = _run_git(repo, ["rev-parse", "HEAD"])
    branch_result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "symbolic-ref",
            "--quiet",
            "--short",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=settings.workspace_git_timeout_seconds,
        shell=False,
    )
    branch = branch_result.stdout.strip() or "<detached>"
    status = _run_git(
        repo,
        ["status", "--porcelain=v1", "--untracked-files=all"],
    )
    attributes = repo / ".gitattributes"
    has_lfs = (
        attributes.is_file()
        and "filter=lfs"
        in attributes.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )
    return RepositoryIdentity(
        commit_sha=commit,
        branch=branch,
        clean=not bool(status),
        bundle_logical_path=None,
        has_submodules=(repo / ".gitmodules").exists(),
        has_lfs=has_lfs,
    )


def create_repository_capsule(
    *,
    repo_path: str | Path,
    destination: Path,
) -> RepositoryCapsule:
    repo = Path(repo_path).expanduser().resolve()
    branch, commit = _require_clean_repository(repo)
    _reject_unsupported_repository_features(repo)

    destination = destination.resolve()
    staging_root = settings.workspace_staging_root.resolve()
    if staging_root not in destination.parents:
        raise WorkspaceIntegrityError(
            "repository bundle 必须写入 WORKSPACE_STAGING_ROOT"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise WorkspaceIntegrityError("bundle destination 已存在")

    # 必须传命名 ref。Git 官方文档指出仅传不可解析为 ref 的 commit
    # 可能得到 empty bundle。
    _run_git(
        repo,
        ["bundle", "create", str(destination), branch],
    )
    _run_git(repo, ["bundle", "verify", str(destination)])

    size = destination.stat().st_size
    if size > settings.workspace_max_file_bytes:
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

注意：`git bundle verify` 的 stdout 可能包含 ref/commit，但不应包含 secret。错误消息仍然
只保留 500 字符；不要把完整 Git config 或 remote URL 写进 Event。

---

## 二十四、Workspace snapshotter

> **本节类型：需要新增代码。**
>
> 新增：`app/workspace/snapshot.py`

该模块负责：

```text
初始 snapshot：paper + optional log + clean repo bundle
interrupt seal：前述内容 + 当前 ArtifactRecord + allowlisted process journal
```

完整主体代码：

```python
from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable
from uuid import uuid4

from app.config import settings
from app.schemas import ArtifactRecord
from app.storage.ports import BlobStore
from app.tools.artifact_tools import sha256_file
from app.workspace.errors import (
    WorkspaceIntegrityError,
    WorkspaceNotPortableError,
)
from app.workspace.paths import (
    require_managed_run_root,
    require_workspace_relative_path,
)
from app.workspace.repo_capsule import (
    create_repository_capsule,
    inspect_repository_identity,
)
from app.workspace.repository import workspace_manifest_hash
from app.workspace.schemas import (
    ExternalDataReference,
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
    WorkspaceSourcePaths,
)


PROCESS_FILE_PATTERNS = (
    "execution/attempts/*/process_record.json",
    "execution/attempts/*/stdout.log",
    "execution/attempts/*/stderr.log",
    "execution/attempts/*/combined.log",
    "execution/control/*.runtime.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_object_key(sha256: str) -> str:
    return f"workspace/sha256/{sha256[:2]}/{sha256}"


def _media_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


class WorkspaceSnapshotter:
    def __init__(self, *, blob_store: BlobStore):
        self.blob_store = blob_store
        self.blob_store.ensure_ready()

    def _publish_entry(
        self,
        *,
        source: Path,
        logical_path: str,
        role: str,
        executable: bool = False,
    ) -> WorkspaceBlobEntry:
        require_workspace_relative_path(logical_path)
        resolved = source.resolve()
        if not resolved.is_file():
            raise WorkspaceIntegrityError(
                f"workspace source 不存在：{resolved}"
            )
        size = resolved.stat().st_size
        if size > settings.workspace_max_file_bytes:
            raise WorkspaceNotPortableError(
                f"workspace_file_too_large:{logical_path}"
            )

        digest = sha256_file(resolved)
        stat = self.blob_store.put_file(
            object_key=workspace_object_key(digest),
            source_path=resolved,
            expected_sha256=digest,
            expected_size=size,
            media_type=_media_type(resolved),
        )
        if stat.sha256 != digest or stat.size_bytes != size:
            raise WorkspaceIntegrityError(
                "BlobStore 返回的 workspace stat 不匹配"
            )
        return WorkspaceBlobEntry(
            logical_path=logical_path,
            role=role,
            object_key=stat.object_key,
            sha256=digest,
            size_bytes=size,
            media_type=_media_type(resolved),
            executable=executable,
        )

    def _build_manifest(
        self,
        *,
        job_id: str,
        run_id: str,
        generation: int,
        parent_manifest_id: str | None,
        source_host_id: str,
        source_worker_session_id: str | None,
        entries: list[WorkspaceBlobEntry],
        repository: RepositoryIdentity,
        external_data: list[ExternalDataReference],
        blocked_reasons: list[str],
        source_paths: WorkspaceSourcePaths | None,
    ) -> WorkspaceManifest:
        total = sum(item.size_bytes for item in entries)
        if total > settings.workspace_max_total_bytes:
            blocked_reasons.append("workspace_total_size_exceeded")

        # 只有共享 Blob、clean repo 和全部外部引用可调度时才 portable。
        if self.blob_store.sharing_scope != "shared":
            blocked_reasons.append("blob_store_is_host_local")

        reasons = sorted(set(blocked_reasons))
        draft = WorkspaceManifest(
            manifest_id="wm_pending",
            manifest_hash="",
            job_id=job_id,
            run_id=run_id,
            generation=generation,
            parent_manifest_id=parent_manifest_id,
            source_host_id=source_host_id,
            source_worker_session_id=source_worker_session_id,
            entries=sorted(entries, key=lambda item: item.logical_path),
            repository=repository,
            external_data=external_data,
            portable=not reasons,
            blocked_reasons=reasons,
            source_paths=source_paths,
            created_at=utc_now(),
        )
        digest = workspace_manifest_hash(draft)
        return draft.model_copy(
            update={
                "manifest_id": f"wm_{digest[:32]}",
                "manifest_hash": digest,
            }
        )

    def snapshot_initial(
        self,
        *,
        job_id: str,
        run_id: str,
        paper_path: str,
        repo_path: str,
        log_path: str | None,
        source_host_id: str,
        external_data: list[ExternalDataReference],
    ) -> WorkspaceManifest:
        paper = Path(paper_path).expanduser().resolve()
        entries = [
            self._publish_entry(
                source=paper,
                logical_path="source/paper.pdf",
                role="paper",
            )
        ]

        if log_path:
            entries.append(
                self._publish_entry(
                    source=Path(log_path).expanduser().resolve(),
                    logical_path="source/external.log",
                    role="input_log",
                )
            )

        blocked_reasons: list[str] = []
        repository = inspect_repository_identity(repo_path)
        try:
            with TemporaryDirectory(
                prefix="repo-capsule-",
                dir=settings.workspace_staging_root,
            ) as raw_dir:
                capsule = create_repository_capsule(
                    repo_path=repo_path,
                    destination=Path(raw_dir) / "repository.bundle",
                )
                repository = capsule.identity
                entries.append(
                    self._publish_entry(
                        source=capsule.bundle_path,
                        logical_path="capsule/repository.bundle",
                        role="repository_bundle",
                    )
                )
        except WorkspaceNotPortableError as exc:
            blocked_reasons.append(str(exc))

        # required_worker_label 已经进入 Job requirements；manifest 只保存引用。
        return self._build_manifest(
            job_id=job_id,
            run_id=run_id,
            generation=0,
            parent_manifest_id=None,
            source_host_id=source_host_id,
            source_worker_session_id=None,
            entries=entries,
            repository=repository,
            external_data=external_data,
            blocked_reasons=blocked_reasons,
            source_paths=WorkspaceSourcePaths(
                run_dir=None,
                repo_path=str(Path(repo_path).expanduser().resolve()),
                paper_path=str(paper),
                log_path=(
                    str(Path(log_path).expanduser().resolve())
                    if log_path
                    else None
                ),
            ),
        )

    def _artifact_entries(
        self,
        *,
        run_root: Path,
        records: Iterable[ArtifactRecord | dict],
    ) -> list[WorkspaceBlobEntry]:
        latest: dict[str, ArtifactRecord] = {}
        for raw in records:
            record = (
                raw
                if isinstance(raw, ArtifactRecord)
                else ArtifactRecord.model_validate(raw)
            )
            latest[record.artifact_id] = record

        entries: list[WorkspaceBlobEntry] = []
        for record in latest.values():
            require_workspace_relative_path(record.relative_path)
            source = (run_root / record.relative_path).resolve()
            if run_root not in source.parents:
                raise WorkspaceIntegrityError(
                    "Artifact relative_path 逃逸 run root"
                )
            if (
                not source.is_file()
                or source.stat().st_size != record.size_bytes
                or sha256_file(source) != record.sha256
            ):
                raise WorkspaceIntegrityError(
                    f"Artifact 在 snapshot 前发生变化：{record.artifact_id}"
                )
            entries.append(
                self._publish_entry(
                    source=source,
                    logical_path=f"run/{record.relative_path}",
                    role="run_artifact",
                    executable=False,
                )
            )
        return entries

    def _process_entries(self, run_root: Path) -> list[WorkspaceBlobEntry]:
        entries: dict[str, WorkspaceBlobEntry] = {}
        for pattern in PROCESS_FILE_PATTERNS:
            for source in run_root.glob(pattern):
                if not source.is_file() or source.is_symlink():
                    continue
                relative = source.resolve().relative_to(run_root).as_posix()
                role = (
                    "process_record"
                    if source.name.endswith(".json")
                    else "process_log"
                )
                entry = self._publish_entry(
                    source=source,
                    logical_path=f"run/{relative}",
                    role=role,
                )
                entries[entry.logical_path] = entry
        return list(entries.values())

    def seal(
        self,
        *,
        job_id: str,
        run_id: str,
        run_dir: str,
        repo_path: str,
        paper_path: str,
        log_path: str | None,
        parent: WorkspaceManifest,
        source_host_id: str,
        source_worker_session_id: str,
        artifact_records: Iterable[ArtifactRecord | dict],
        external_data: list[ExternalDataReference],
        blocked_reasons: list[str],
    ) -> WorkspaceManifest:
        run_root = require_managed_run_root(run_dir)
        entries = [
            item
            for item in parent.entries
            if item.role in {
                "paper",
                "input_log",
                "repository_bundle",
            }
        ]
        entries.extend(
            self._artifact_entries(
                run_root=run_root,
                records=artifact_records,
            )
        )
        entries.extend(self._process_entries(run_root))

        repository = parent.repository
        try:
            with TemporaryDirectory(
                prefix="repo-seal-",
                dir=settings.workspace_staging_root,
            ) as raw_dir:
                capsule = create_repository_capsule(
                    repo_path=repo_path,
                    destination=Path(raw_dir) / "repository.bundle",
                )
                repository = capsule.identity
                entries = [
                    item
                    for item in entries
                    if item.role != "repository_bundle"
                ]
                entries.append(
                    self._publish_entry(
                        source=capsule.bundle_path,
                        logical_path="capsule/repository.bundle",
                        role="repository_bundle",
                    )
                )
        except WorkspaceNotPortableError as exc:
            blocked_reasons.append(str(exc))
            repository = inspect_repository_identity(repo_path)

        # 同一路径只保留最后一个内容版本。
        unique = {item.logical_path: item for item in entries}
        return self._build_manifest(
            job_id=job_id,
            run_id=run_id,
            generation=parent.generation + 1,
            parent_manifest_id=parent.manifest_id,
            source_host_id=source_host_id,
            source_worker_session_id=source_worker_session_id,
            entries=list(unique.values()),
            repository=repository,
            external_data=external_data,
            blocked_reasons=blocked_reasons,
            source_paths=WorkspaceSourcePaths(
                run_dir=str(run_root),
                repo_path=str(Path(repo_path).expanduser().resolve()),
                paper_path=str(Path(paper_path).expanduser().resolve()),
                log_path=(
                    str(Path(log_path).expanduser().resolve())
                    if log_path
                    else None
                ),
            ),
        )
```

### 24.1 修正一个容易忽略的 Python 生命周期问题

上面 `snapshot_initial()` 在 `with TemporaryDirectory(...)` 之外读取
`capsule.identity` 是安全的，因为 `RepositoryCapsule` 中的 identity 已经是内存中的
Pydantic 对象；但 `capsule.bundle_path` 在退出 `with` 后已经不存在，所以必须在 `with`
内部调用 `_publish_entry()`。教程代码正是这样安排的。

### 24.2 不收录哪些目录

明确排除：

```text
execution/runtime/**
**/__pycache__/**
.git/**（由 Git bundle 取代）
embedding cache 数据库
dataset
Conda env
cancel request
任意未登记文件
```

cancel request 属于旧 execution epoch 的瞬时控制消息，不能带到新 Worker，否则新进程
可能刚启动就读取到过期取消请求。

---

## 二十五、检测安全 seal 边界

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/process_reconcile.py`

增加“是否允许跨 host seal”的纯函数：

```python
PATH_BOUND_INTERRUPT_NODES = {
    "human_review",
    "patch_review",
    "patch_promotion_review",
}


def workspace_portability_blockers(
    *,
    run_dir: str,
    interrupt_nodes: list[str],
    state: dict[str, Any],
) -> list[str]:
    """只返回原因，不执行 requeue、kill 或文件修改。"""

    blockers: list[str] = []

    if set(interrupt_nodes).intersection(PATH_BOUND_INTERRUPT_NODES):
        blockers.append("path_bound_approval_interrupt")

    # 已构造的 action/patch 通常包含绝对 cwd、repo path 和审批 hash。
    if state.get("pending_action") is not None:
        blockers.append("pending_action_contains_local_paths")
    if state.get("pending_patch") is not None:
        blockers.append("pending_patch_contains_local_paths")
    if state.get("patch_approval_record") is not None:
        blockers.append("patch_approval_is_path_bound")

    run_root = require_managed_run_root(run_dir)
    records = list_runtime_records(run_root)
    active = [
        item
        for item in records
        if item.get("status")
        in {"starting", "running", "terminating"}
    ]
    if active:
        blockers.append("active_or_ambiguous_subprocess")

    return sorted(set(blockers))
```

为什么路径型审批第一版不迁移：

```text
用户审批的是：
    cwd=/host-a/.../epochs/1/repo
    action_hash=hash-A

新 Worker 实际执行：
    cwd=/host-b/.../epochs/2/repo
```

如果静默改 cwd，hash 已经变了；如果不改，路径不存在。正确选择是保留 host affinity，
而不是绕过 Phase 17 的 stale approval 防线。

第一版建议用于跨 host 验收的 interrupt 是：

```text
command_selection
```

但仍要在下一节重绑定 `run_commands[].cwd`，并确认 command 字符串本身不硬编码旧绝对
路径。

---

## 二十六、Workspace materializer

> **本节类型：需要新增代码。**
>
> 新增：`app/workspace/materializer.py`

Materializer 的顺序必须是：

```text
validate manifest hash
    -> validate Worker labels/affinity
    -> create private staging directory
    -> stream every Blob and verify size/hash
    -> git bundle verify
    -> git clone named branch
    -> verify commit/clean/symlink
    -> write binding marker
    -> atomic rename staging -> final epoch
```

完整实现：

```python
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.storage.ports import BlobStore
from app.workspace.capabilities import explain_compatibility
from app.workspace.errors import (
    WorkerCapabilityError,
    WorkspaceIntegrityError,
    WorkspaceNotPortableError,
)
from app.workspace.paths import (
    create_run_layout_at,
    require_workspace_relative_path,
    resolve_inside,
)
from app.workspace.repository import validate_manifest_hash
from app.workspace.schemas import (
    JobRequirements,
    WorkerIdentity,
    WorkspaceBinding,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_component(value: str, *, field: str) -> str:
    if not value or Path(value).name != value or value in {".", ".."}:
        raise WorkspaceIntegrityError(f"无效 {field}：{value!r}")
    return value


def _entry_target(
    *,
    staging_root: Path,
    entry: WorkspaceBlobEntry,
) -> Path:
    logical = require_workspace_relative_path(entry.logical_path)
    first = logical.parts[0]
    if first not in {"source", "capsule", "run"}:
        raise WorkspaceIntegrityError(
            f"未知 workspace entry scope：{first}"
        )

    expected_scope = {
        "paper": "source",
        "input_log": "source",
        "repository_bundle": "capsule",
        "run_artifact": "run",
        "process_record": "run",
        "process_log": "run",
    }[entry.role]
    if first != expected_scope:
        raise WorkspaceIntegrityError(
            f"entry role 与 logical_path 不匹配：{entry.role}"
        )
    return resolve_inside(staging_root, entry.logical_path)


def _copy_verified_blob(
    *,
    blob_store: BlobStore,
    entry: WorkspaceBlobEntry,
    target: Path,
) -> None:
    opened = blob_store.open(entry.object_key)
    if (
        opened.stat.sha256 != entry.sha256
        or opened.stat.size_bytes != entry.size_bytes
    ):
        opened.body.close()
        raise WorkspaceIntegrityError(
            "Blob metadata 与 Workspace Manifest 不一致"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    copied = 0
    try:
        with target.open("xb") as output:
            while True:
                chunk = opened.body.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                copied += len(chunk)
                if copied > entry.size_bytes:
                    raise WorkspaceIntegrityError(
                        "Blob stream 超过 manifest size"
                    )
            output.flush()
            os.fsync(output.fileno())
    finally:
        opened.body.close()

    if copied != entry.size_bytes or digest.hexdigest() != entry.sha256:
        raise WorkspaceIntegrityError(
            f"Blob 内容完整性失败：{entry.logical_path}"
        )

    # 只恢复普通可读文件和可执行位，不恢复 suid/sgid/sticky bits。
    target.chmod(0o755 if entry.executable else 0o644)


def _run_git(args: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=(str(cwd) if cwd is not None else None),
        capture_output=True,
        text=True,
        check=False,
        shell=False,
        timeout=settings.workspace_git_timeout_seconds,
        env={
            "PATH": os.environ.get("PATH", ""),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise WorkspaceIntegrityError(
            f"Git materialization failed：{message[:500]}"
        )
    return completed.stdout.strip()


def _validate_repository_symlinks(repo: Path) -> None:
    for path in repo.rglob("*"):
        if ".git" in path.relative_to(repo).parts:
            continue
        if not path.is_symlink():
            continue
        raw_target = os.readlink(path)
        if Path(raw_target).is_absolute():
            raise WorkspaceIntegrityError(
                f"仓库包含绝对 symlink：{path.relative_to(repo)}"
            )
        resolved = (path.parent / raw_target).resolve()
        if resolved != repo and repo not in resolved.parents:
            raise WorkspaceIntegrityError(
                f"仓库 symlink 逃逸 workspace：{path.relative_to(repo)}"
            )


def _clone_repository(
    *,
    staging_root: Path,
    manifest: WorkspaceManifest,
) -> Path:
    bundle = staging_root / "capsule" / "repository.bundle"
    if not bundle.is_file():
        raise WorkspaceIntegrityError("portable manifest 缺少 Git bundle")

    # list-heads 不依赖当前 Git repository，可在 clone 前拒绝损坏的 bundle。
    _run_git(["bundle", "list-heads", str(bundle)])
    repo = staging_root / "repo"
    _run_git(
        [
            "clone",
            "--branch",
            manifest.repository.branch,
            "--single-branch",
            str(bundle),
            str(repo),
        ]
    )

    # clone 后再在目标 repository 上执行完整 prerequisite 校验。
    _run_git(["bundle", "verify", str(bundle)], cwd=repo)

    commit = _run_git(["rev-parse", "HEAD"], cwd=repo)
    if commit != manifest.repository.commit_sha:
        raise WorkspaceIntegrityError(
            "materialized repository commit 不匹配"
        )
    status = _run_git(
        ["status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo,
    )
    if status:
        raise WorkspaceIntegrityError(
            "materialized repository 不是 clean state"
        )
    _validate_repository_symlinks(repo)
    return repo


class WorkspaceMaterializer:
    def __init__(self, *, blob_store: BlobStore):
        self.blob_store = blob_store

    def _epoch_root(
        self,
        *,
        worker: WorkerIdentity,
        job_id: str,
        assignment_epoch: int,
    ) -> Path:
        _safe_component(job_id, field="job_id")
        configured = settings.worker_workspace_root.resolve()
        declared = Path(worker.workspace_root).resolve()
        if declared != configured:
            raise WorkspaceIntegrityError(
                "Worker identity workspace_root 与本进程配置不一致"
            )
        return (
            configured
            / "jobs"
            / job_id
            / "epochs"
            / f"{assignment_epoch:08d}"
        ).resolve()

    def planned_binding(
        self,
        *,
        worker: WorkerIdentity,
        manifest: WorkspaceManifest,
        requirements: JobRequirements,
        assignment_epoch: int,
        assignment_token: str,
    ) -> WorkspaceBinding:
        explanation = explain_compatibility(
            requirements=requirements,
            worker=worker,
            affinity_host_id=(
                None if manifest.portable else manifest.source_host_id
            ),
        )
        if not explanation.compatible:
            raise WorkerCapabilityError(
                "Worker 不满足 workspace requirement："
                + ",".join(explanation.reasons)
            )

        now = utc_now()
        if not manifest.portable:
            if manifest.source_paths is None:
                raise WorkspaceNotPortableError(
                    "host-affine manifest 缺少 source_paths"
                )
            source = manifest.source_paths
            if source.run_dir is None:
                # 初始 host-affine Job 仍使用原始 RUNS_DIR；run_context 会创建它。
                run_dir = str(
                    (
                        settings.runs_dir.resolve()
                        / _safe_component(manifest.run_id, field="run_id")
                    ).resolve()
                )
            else:
                run_dir = str(Path(source.run_dir).resolve())
            return WorkspaceBinding(
                assignment_id=f"was_{uuid4().hex}",
                assignment_epoch=assignment_epoch,
                assignment_token=assignment_token,
                job_id=manifest.job_id,
                run_id=manifest.run_id,
                manifest_id=manifest.manifest_id,
                manifest_hash=manifest.manifest_hash,
                manifest_generation=manifest.generation,
                worker_session_id=worker.worker_session_id,
                host_id=worker.host_id,
                workspace_root=str(Path(run_dir).parent),
                run_dir=run_dir,
                repo_path=source.repo_path,
                paper_path=source.paper_path,
                log_path=source.log_path,
                status="materializing",
                created_at=now,
                updated_at=now,
            )

        epoch_root = self._epoch_root(
            worker=worker,
            job_id=manifest.job_id,
            assignment_epoch=assignment_epoch,
        )
        return WorkspaceBinding(
            assignment_id=f"was_{uuid4().hex}",
            assignment_epoch=assignment_epoch,
            assignment_token=assignment_token,
            job_id=manifest.job_id,
            run_id=manifest.run_id,
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            manifest_generation=manifest.generation,
            worker_session_id=worker.worker_session_id,
            host_id=worker.host_id,
            workspace_root=str(epoch_root),
            run_dir=str(epoch_root / "run"),
            repo_path=str(epoch_root / "repo"),
            paper_path=str(epoch_root / "source" / "paper.pdf"),
            log_path=(
                str(epoch_root / "source" / "external.log")
                if any(item.role == "input_log" for item in manifest.entries)
                else None
            ),
            status="materializing",
            created_at=now,
            updated_at=now,
        )

    def materialize(
        self,
        *,
        manifest: WorkspaceManifest,
        binding: WorkspaceBinding,
    ) -> WorkspaceBinding:
        validate_manifest_hash(manifest)

        # Host-affine fallback 复用当前主机已有路径，但仍逐项检查存在性。
        if not manifest.portable:
            if binding.host_id != manifest.source_host_id:
                raise WorkspaceNotPortableError("host affinity 不匹配")
            for path in (
                Path(binding.repo_path),
                Path(binding.paper_path),
            ):
                if not path.exists():
                    raise WorkspaceNotPortableError(
                        f"affinity host source 不存在：{path}"
                    )
            create_run_layout_at(Path(binding.run_dir))
            now = utc_now()
            return binding.model_copy(
                update={"status": "ready", "updated_at": now}
            )

        final_root = Path(binding.workspace_root).resolve()
        parent = final_root.parent
        parent.mkdir(parents=True, exist_ok=True)
        staging = parent / f".{final_root.name}.{uuid4().hex}.staging"

        if final_root.exists():
            marker = final_root / ".workspace-binding.json"
            if not marker.is_file():
                raise WorkspaceIntegrityError(
                    "epoch root 已存在但没有 binding marker"
                )
            existing = WorkspaceBinding.model_validate_json(
                marker.read_text(encoding="utf-8")
            )
            if (
                existing.assignment_token != binding.assignment_token
                or existing.manifest_hash != manifest.manifest_hash
            ):
                raise WorkspaceIntegrityError(
                    "epoch root 已被其他 assignment 使用"
                )
            return existing

        try:
            staging.mkdir(mode=0o700)
            for entry in manifest.entries:
                target = _entry_target(
                    staging_root=staging,
                    entry=entry,
                )
                _copy_verified_blob(
                    blob_store=self.blob_store,
                    entry=entry,
                    target=target,
                )

            repo = _clone_repository(
                staging_root=staging,
                manifest=manifest,
            )
            run_dir = staging / "run"
            create_run_layout_at(run_dir)

            # rename 前构造最终路径，marker 不能记录 staging path。
            now = utc_now()
            ready = binding.model_copy(
                update={
                    "repo_path": str(final_root / repo.relative_to(staging)),
                    "run_dir": str(final_root / "run"),
                    "paper_path": str(final_root / "source" / "paper.pdf"),
                    "log_path": (
                        str(final_root / "source" / "external.log")
                        if binding.log_path is not None
                        else None
                    ),
                    "status": "ready",
                    "updated_at": now,
                }
            )
            marker = staging / ".workspace-binding.json"
            marker.write_text(
                ready.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
            marker.chmod(stat.S_IRUSR | stat.S_IWUSR)
            os.replace(staging, final_root)
            return ready
        finally:
            if staging.exists():
                shutil.rmtree(staging)
```

### 26.1 Materializer 不能直接信任数据库路径

`WorkspaceBinding.workspace_root` 来自本进程根据受信任 `WORKER_WORKSPACE_ROOT` 计算的
planned binding，而不是 API/LLM 输入。即使数据库 row 被错误写入其他路径，
`_epoch_root()` 仍会阻断。

### 26.2 不要把 assignment token 发布到 Blob

`.workspace-binding.json` 只用于当前 host 幂等判断，不进入 Workspace Manifest 和
ArtifactPublisher。token 是 fencing capability，不是用户产物。

---

## 二十七、持久化 manifest 与 assignment

> **本节类型：需要新增和修改代码。**
>
> 修改：`app/workspace/repository.py`、`app/job_runtime/postgres_store.py`

`repository.py` 增加 row 解析：

```python
from app.workspace.schemas import WorkspaceBinding, WorkspaceManifest


def manifest_from_row(row: Any) -> WorkspaceManifest:
    manifest = WorkspaceManifest.model_validate(row["manifest_json"])
    validate_manifest_hash(manifest)
    if (
        manifest.manifest_id != row["manifest_id"]
        or manifest.manifest_hash != row["manifest_hash"]
    ):
        raise WorkspaceIntegrityError(
            "manifest row identity 与 JSON 不一致"
        )
    return manifest


def binding_from_row(row: Any) -> WorkspaceBinding:
    return WorkspaceBinding(
        assignment_id=str(row["assignment_id"]),
        assignment_epoch=int(row["assignment_epoch"]),
        assignment_token=str(row["assignment_token"]),
        job_id=str(row["job_id"]),
        run_id=str(row["run_id"]),
        manifest_id=str(row["manifest_id"]),
        manifest_hash=str(row["manifest_hash"]),
        manifest_generation=int(row["manifest_generation"]),
        worker_session_id=str(row["worker_session_id"]),
        host_id=str(row["host_id"]),
        workspace_root=str(row["workspace_root"]),
        run_dir=str(row["run_dir"]),
        repo_path=str(row["repo_path"]),
        paper_path=str(row["paper_path"]),
        log_path=row["log_path"],
        status=str(row["status"]),
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )
```

第十六、十七节的正式 table 与 migration 已包含 `run_id`。如果你在补全该字段之前已经执行
过 migration，不要改已应用 revision，新增 `0003` 修正 migration。

> **实现提醒：**本教程还没执行 migration 时，直接在 `0002` 中加入
> `sa.Column("run_id", sa.Text(), nullable=False)`；已经在任何环境执行过 `0002` 时，必须
> 新增 revision，不能重写历史。

`PostgresJobStore.begin_workspace_assignment()`：

```python
def begin_workspace_assignment(
    self,
    *,
    job_id: str,
    claim_token: str,
    worker: WorkerIdentity,
    manifest: WorkspaceManifest,
    assignment_token: str,
    workspace_root: str,
    run_dir: str,
    repo_path: str,
    paper_path: str,
    log_path: str | None,
) -> WorkspaceBinding:
    validate_manifest_hash(manifest)
    with self.engine.begin() as connection:
        current = database_clock(connection)
        job = self._owned_row(
            connection,
            job_id=job_id,
            claim_token=claim_token,
        )
        if job["workspace_assignment_token"] != assignment_token:
            raise LeaseLostError("workspace assignment token 已失效")
        if job["worker_session_id"] != worker.worker_session_id:
            raise LeaseLostError("worker session 已失效")
        if job["workspace_manifest_id"] != manifest.manifest_id:
            raise JobConflictError("claim 使用了过期 workspace manifest")

        epoch = int(job["workspace_assignment_epoch"])
        existing = connection.execute(
            sa.select(workspace_assignments)
            .where(
                workspace_assignments.c.job_id == job_id,
                workspace_assignments.c.assignment_epoch == epoch,
            )
            .with_for_update()
        ).mappings().one_or_none()
        if existing is not None:
            # DB commit 已成功但 Worker 没收到响应时，prepare 会重试。
            # 只有完全相同的 assignment 才能幂等返回，不能吞掉真实冲突。
            expected = {
                "assignment_token": assignment_token,
                "manifest_id": manifest.manifest_id,
                "manifest_hash": manifest.manifest_hash,
                "worker_session_id": worker.worker_session_id,
                "host_id": worker.host_id,
                "workspace_root": workspace_root,
                "run_dir": run_dir,
                "repo_path": repo_path,
                "paper_path": paper_path,
                "log_path": log_path,
            }
            mismatches = [
                key
                for key, value in expected.items()
                if existing[key] != value
            ]
            if mismatches:
                raise JobConflictError(
                    "同一 assignment epoch 已被不同内容占用："
                    + ", ".join(mismatches)
                )
            return binding_from_row(existing)

        assignment_id = f"was_{uuid4().hex}"
        connection.execute(
            workspace_assignments.insert().values(
                assignment_id=assignment_id,
                job_id=job_id,
                run_id=job["run_id"],
                assignment_epoch=epoch,
                assignment_token=assignment_token,
                manifest_id=manifest.manifest_id,
                manifest_hash=manifest.manifest_hash,
                manifest_generation=manifest.generation,
                worker_session_id=worker.worker_session_id,
                host_id=worker.host_id,
                workspace_root=workspace_root,
                run_dir=run_dir,
                repo_path=repo_path,
                paper_path=paper_path,
                log_path=log_path,
                status="materializing",
                created_at=current,
                updated_at=current,
            )
        )
        row = connection.execute(
            sa.select(workspace_assignments).where(
                workspace_assignments.c.assignment_id == assignment_id
            )
        ).mappings().one()
        self._append_event(
            connection,
            job_id=job_id,
            event_type="workspace_materializing",
            actor=worker.worker_id,
            payload={
                "assignment_id": assignment_id,
                "assignment_epoch": row["assignment_epoch"],
                "manifest_id": manifest.manifest_id,
                "host_id": worker.host_id,
            },
            now=current,
        )
        return binding_from_row(row)
```

`mark_workspace_ready()` 的完整核心如下。它先验证当前 Job claim 与 workspace token，再把
当前 assignment 变成 `ready`；只有新 epoch 已经 ready 后，才释放旧 workspace：

```python
def mark_workspace_ready(
    self,
    *,
    job_id: str,
    claim_token: str,
    assignment_token: str,
) -> WorkspaceBinding:
    with self.engine.begin() as connection:
        current = database_clock(connection)
        job = self._owned_row(
            connection,
            job_id=job_id,
            claim_token=claim_token,
        )
        if job["workspace_assignment_token"] != assignment_token:
            raise LeaseLostError("workspace assignment token 已失效")

        row = connection.execute(
            sa.select(workspace_assignments)
            .where(
                workspace_assignments.c.job_id == job_id,
                workspace_assignments.c.assignment_token
                == assignment_token,
            )
            .with_for_update()
        ).mappings().one_or_none()
        if row is None:
            raise JobConflictError("workspace assignment 不存在")
        if row["status"] == "ready":
            return binding_from_row(row)
        if row["status"] != "materializing":
            raise JobConflictError(
                f"不能从 {row['status']} 转成 ready"
            )

        result = connection.execute(
            workspace_assignments.update()
            .where(
                workspace_assignments.c.assignment_id
                == row["assignment_id"],
                workspace_assignments.c.status == "materializing",
            )
            .values(status="ready", updated_at=current)
        )
        if result.rowcount != 1:
            raise LeaseLostError("workspace ready fencing 失败")

        # 当前 epoch 已 ready 后，旧目录才允许进入 GC 候选。
        connection.execute(
            workspace_assignments.update()
            .where(
                workspace_assignments.c.job_id == job_id,
                workspace_assignments.c.assignment_epoch
                < row["assignment_epoch"],
                workspace_assignments.c.status == "ready",
            )
            .values(status="released", updated_at=current)
        )
        ready = connection.execute(
            sa.select(workspace_assignments).where(
                workspace_assignments.c.assignment_id
                == row["assignment_id"]
            )
        ).mappings().one()
        self._append_event(
            connection,
            job_id=job_id,
            event_type="workspace_ready",
            actor=str(job["claimed_by"]),
            payload={
                "assignment_id": row["assignment_id"],
                "assignment_epoch": row["assignment_epoch"],
                "manifest_id": row["manifest_id"],
            },
            now=current,
        )
        return binding_from_row(ready)
```

失败路径同样不能绕过 fencing：

```python
def fail_workspace_assignment(
    self,
    *,
    job_id: str,
    claim_token: str,
    assignment_token: str,
    reason: str,
) -> WorkspaceBinding:
    with self.engine.begin() as connection:
        current = database_clock(connection)
        job = self._owned_row(
            connection,
            job_id=job_id,
            claim_token=claim_token,
        )
        if job["workspace_assignment_token"] != assignment_token:
            raise LeaseLostError("workspace assignment token 已失效")
        row = connection.execute(
            sa.select(workspace_assignments)
            .where(
                workspace_assignments.c.job_id == job_id,
                workspace_assignments.c.assignment_token
                == assignment_token,
            )
            .with_for_update()
        ).mappings().one_or_none()
        if row is None:
            raise JobConflictError("workspace assignment 不存在")
        if row["status"] != "materializing":
            # ready 可能表示上一请求已提交、只是响应丢失；不能反向覆盖。
            return binding_from_row(row)

        connection.execute(
            workspace_assignments.update()
            .where(
                workspace_assignments.c.assignment_id
                == row["assignment_id"],
                workspace_assignments.c.status == "materializing",
            )
            .values(
                status="failed",
                error_code=reason[:120],
                updated_at=current,
            )
        )
        failed = connection.execute(
            sa.select(workspace_assignments).where(
                workspace_assignments.c.assignment_id
                == row["assignment_id"]
            )
        ).mappings().one()
        self._append_event(
            connection,
            job_id=job_id,
            event_type="workspace_materialization_failed",
            actor=str(job["claimed_by"]),
            payload={
                "assignment_id": row["assignment_id"],
                "error_code": reason[:120],
            },
            now=current,
        )
        return binding_from_row(failed)
```

`seal_workspace_manifest()` 必须在一个 transaction 内完成：

```text
lock owned Job
verify assignment status=ready and token matches
verify new generation=current generation+1
verify parent_manifest_id=current manifest
insert workspace_manifests
update jobs.workspace_manifest_id/generation/affinity
append workspace_sealed or workspace_portability_blocked event
commit
```

完整核心：

```python
from sqlalchemy.dialects import postgresql


def seal_workspace_manifest(
    self,
    *,
    job_id: str,
    claim_token: str,
    assignment_token: str,
    manifest: WorkspaceManifest,
    affinity_host_id: str | None,
    actor: str,
) -> JobRecord:
    validate_manifest_hash(manifest)
    with self.engine.begin() as connection:
        current = database_clock(connection)
        row = self._owned_row(
            connection,
            job_id=job_id,
            claim_token=claim_token,
        )
        if row["workspace_assignment_token"] != assignment_token:
            raise LeaseLostError("workspace assignment 已失效")
        if manifest.job_id != job_id or manifest.run_id != row["run_id"]:
            raise JobConflictError("manifest Job identity 不一致")
        if row["workspace_manifest_id"] == manifest.manifest_id:
            # DB commit 成功但客户端未收到响应时的同内容重放。
            existing = connection.execute(
                sa.select(workspace_manifests).where(
                    workspace_manifests.c.manifest_id
                    == manifest.manifest_id
                )
            ).mappings().one()
            if existing["manifest_hash"] != manifest.manifest_hash:
                raise JobConflictError("manifest_id 内容冲突")
            return self._row_to_record(row)
        if manifest.parent_manifest_id != row["workspace_manifest_id"]:
            raise JobConflictError("manifest parent 不是当前 head")
        if manifest.generation != row["workspace_manifest_generation"] + 1:
            raise JobConflictError("manifest generation 不连续")
        if manifest.portable and affinity_host_id is not None:
            raise JobConflictError("portable manifest 不应设置 affinity")
        if not manifest.portable and affinity_host_id != row["worker_host_id"]:
            raise JobConflictError(
                "non-portable manifest 必须绑定当前 worker host"
            )

        insert_manifest = postgresql.insert(
            workspace_manifests
        ).values(
                manifest_id=manifest.manifest_id,
                manifest_hash=manifest.manifest_hash,
                job_id=manifest.job_id,
                run_id=manifest.run_id,
                generation=manifest.generation,
                parent_manifest_id=manifest.parent_manifest_id,
                portable=manifest.portable,
                source_host_id=manifest.source_host_id,
                source_worker_session_id=(
                    manifest.source_worker_session_id
                ),
                manifest_json=manifest.model_dump(),
                created_at=datetime.fromisoformat(manifest.created_at),
            ).on_conflict_do_nothing(
                index_elements=[workspace_manifests.c.manifest_hash]
            )
        connection.execute(insert_manifest)
        stored = connection.execute(
            sa.select(workspace_manifests).where(
                workspace_manifests.c.manifest_hash
                == manifest.manifest_hash
            )
        ).mappings().one()
        if (
            stored["manifest_id"] != manifest.manifest_id
            or stored["job_id"] != job_id
            or stored["generation"] != manifest.generation
        ):
            raise JobConflictError(
                "manifest hash 命中了不同 identity"
            )
        connection.execute(
            jobs.update()
            .where(
                jobs.c.job_id == job_id,
                jobs.c.claim_token == claim_token,
                jobs.c.workspace_assignment_token == assignment_token,
            )
            .values(
                workspace_manifest_id=manifest.manifest_id,
                workspace_manifest_generation=manifest.generation,
                affinity_host_id=affinity_host_id,
                updated_at=current,
            )
        )
        event_type = (
            "workspace_sealed"
            if manifest.portable
            else "workspace_portability_blocked"
        )
        self._append_event(
            connection,
            job_id=job_id,
            event_type=event_type,
            actor=actor,
            payload={
                "manifest_id": manifest.manifest_id,
                "generation": manifest.generation,
                "portable": manifest.portable,
                "blocked_reasons": manifest.blocked_reasons,
                "affinity_host_id": affinity_host_id,
            },
            now=current,
        )
        return self._row_to_record(
            self._get_row(connection, job_id)
        )
```

Blob 上传发生在 transaction 之前；数据库只发布已存在、已校验的 immutable Blob 指针。
如果 DB commit 失败，最多产生未引用 Blob，不能产生指向缺失 Blob 的 manifest head。

---

## 二十八、初始 snapshot 与 Job submit

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/service.py`、`app/job_runtime/postgres_store.py`、
> `app/job_runtime/store.py`、`app/storage/factory.py`

### 28.1 让 Storage bundle 暴露选中的 BlobStore

修改 `ArtifactStorageBundle`：

```python
@dataclass(frozen=True)
class ArtifactStorageBundle:
    repository: ArtifactRepository
    stores: list[BlobStore]
    selected_store: BlobStore
    publisher: ArtifactPublisher
    catalog: PublishedArtifactCatalog
```

factory return 时增加：

```python
selected_store=selected,
```

### 28.2 修改 `JobService`

构造函数注入 Snapshotter：

```python
class JobService:
    def __init__(
        self,
        store: JobStore,
        *,
        workspace_snapshotter: WorkspaceSnapshotter,
    ):
        self.store = store
        self.workspace_snapshotter = workspace_snapshotter
        self.store.initialize()
```

在 `submit()` 中生成 `job_id/run_id` 后、调用 Store 前增加：

```python
        profile = get_execution_profile(
            request.execution_profile_id
        )
        requirements = requirements_from_profile(profile)

        # 第一版 external_data 可从 JobRequest.dataset_refs 传入；没有则为空。
        external_data = list(request.dataset_refs)
        required_dataset_labels = {
            item.required_worker_label for item in external_data
        }
        requirements = requirements.model_copy(
            update={
                "required_labels": sorted(
                    set(requirements.required_labels)
                    | required_dataset_labels
                )
            }
        )

        manifest = self.workspace_snapshotter.snapshot_initial(
            job_id=job_id,
            run_id=run_id,
            paper_path=request.paper_path,
            repo_path=request.repo_path,
            log_path=request.log_path,
            source_host_id=settings.worker_host_id,
            external_data=external_data,
        )

        return self.store.submit(
            job_id=job_id,
            idempotency_key=effective_idempotency_key,
            thread_id=effective_thread_id,
            run_id=run_id,
            run_dir=str(run_dir),
            request=request,
            requirements=requirements,
            initial_manifest=manifest,
            max_attempts=settings.job_max_attempts,
        )
```

`JobRequest` 增加：

```python
from app.workspace.schemas import ExternalDataReference


class JobRequest(JobModel):
    # 原字段保持不变。
    dataset_refs: list[ExternalDataReference] = Field(default_factory=list)
```

### 28.3 Store submit 的原子顺序

PostgreSQL transaction：

```text
查 idempotency_key
    existing -> 校验 request hash 并直接返回，不插入新 manifest
    new      -> insert initial workspace manifest
             -> insert Job + requirements + manifest pointer
             -> append job_submitted event
```

`request_hash` 必须同时覆盖：

```text
JobRequest
JobRequirements
initial manifest semantic identity
```

至少使用：

```python
request_material = {
    "request": request.model_dump(),
    "requirements": requirements.model_dump(),
    "workspace_manifest_hash": initial_manifest.manifest_hash,
}
```

如果 Blob 已上传但命中旧 idempotency Job，这些内容地址对象通常会被复用；没有 metadata
引用的对象留给未来离线 mark-and-sweep，不要在请求线程中猜测并删除。

对于 `portable=false` 初始 manifest：

```python
affinity_host_id = initial_manifest.source_host_id
```

portable 则为 `None`。

---

## 二十九、ArtifactPublisher 不再信任 absolute_path

> **本节类型：需要修改代码。**
>
> 修改：`app/storage/publisher.py`

Phase 24 的 `_source_path()` 同时要求：

```text
job.run_dir + relative_path == record.absolute_path
```

跨 workspace epoch 后，`absolute_path` 是旧主机提示，不应再作为 Artifact 身份。真正的
安全边界是当前 binding 的 run root、受控 relative path、size 和 hash。

修改签名：

```python
def _source_path(
    self,
    *,
    job: JobRecord,
    record: ArtifactRecord,
    workspace_binding: WorkspaceBinding | None,
) -> Path:
    if record.run_id != job.run_id:
        raise ArtifactIntegrityError("Artifact run_id 与 Job 不一致")

    run_root = require_managed_run_root(
        workspace_binding.run_dir
        if workspace_binding is not None
        else job.run_dir
    )
    logical = require_workspace_relative_path(record.relative_path)
    source = run_root.joinpath(*logical.parts).resolve()
    if source == run_root or run_root not in source.parents:
        raise ArtifactIntegrityError("Artifact source 逃逸 run_dir")
    if not source.is_file():
        raise ArtifactIntegrityError("Artifact source 不存在")
    if source.stat().st_size != record.size_bytes:
        raise ArtifactIntegrityError("Artifact source 大小变化")
    if sha256_file(source) != record.sha256:
        raise ArtifactIntegrityError("Artifact source SHA-256 变化")
    return source
```

删除原来的：

```python
if Path(record.absolute_path).resolve() != source:
    raise ArtifactIntegrityError(...)
```

`publish()` 增加参数并向下传：

```python
workspace_binding: WorkspaceBinding | None = None
```

这不是放松路径安全。恰恰相反：代码完全不再使用 checkpoint 中可移植性很差的
`absolute_path` 定位文件，只使用当前 Worker 已校验 binding 的 root。

---

## 三十、重绑定 checkpoint 中的路径字段

> **本节类型：需要新增代码。**
>
> 新增：`app/workspace/rebind.py`

只改顶层已知的 path-bearing 字段，不能递归替换论文正文、Evidence summary 或 LLM 输出
中的普通文本。完整代码：

```python
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from app.schemas import ArtifactRecord
from app.workspace.errors import WorkspaceNotPortableError
from app.workspace.schemas import WorkspaceBinding


SINGLE_PATH_KEYS = {
    "run_dir",
    "paper_path",
    "repo_path",
    "log_path",
    "repo_index_path",
    "mapping_targets_path",
    "run_manifest_path",
    "artifact_index_path",
    "execution_log_path",
    "smoke_test_log_path",
    "preflight_report_path",
    "capability_report_path",
    "active_process_record_path",
    "paper_blocks_path",
    "paper_sections_path",
    "paper_parse_report_path",
    "semantic_index_manifest_path",
    "debug_evidence_pack_path",
    "error_report_json_path",
    "error_report_md_path",
    "command_selection_input_path",
}

PATH_MAP_KEYS = {
    "code_evidence_pack_paths",
    "dense_retrieval_report_paths",
}


def _rebase_absolute_path(
    raw_value: str | None,
    *,
    old_run: Path,
    new_run: Path,
    old_repo: Path,
    new_repo: Path,
    old_paper: Path,
    new_paper: Path,
    old_log: Path | None,
    new_log: Path | None,
) -> str | None:
    if raw_value is None:
        return None
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        return raw_value
    resolved = candidate.resolve()

    if resolved == old_paper:
        return str(new_paper)
    if old_log is not None and resolved == old_log:
        if new_log is None:
            raise WorkspaceNotPortableError(
                "新 binding 缺少旧 state 使用的 log"
            )
        return str(new_log)
    if resolved == old_run or old_run in resolved.parents:
        relative = resolved.relative_to(old_run)
        return str((new_run / relative).resolve())
    if resolved == old_repo or old_repo in resolved.parents:
        relative = resolved.relative_to(old_repo)
        return str((new_repo / relative).resolve())
    return raw_value


def _rebind_commands(
    commands: list[dict[str, Any]],
    *,
    old_binding: WorkspaceBinding,
    new_binding: WorkspaceBinding,
) -> list[dict[str, Any]]:
    result = deepcopy(commands)
    old_roots = {
        old_binding.repo_path,
        old_binding.run_dir,
        old_binding.paper_path,
    }

    for command in result:
        raw_command = str(command.get("command", ""))
        # 不修改 shell-like command 文本；发现旧绝对路径就阻断迁移。
        if any(root and root in raw_command for root in old_roots):
            raise WorkspaceNotPortableError(
                "run_command_text_contains_old_absolute_path"
            )
        cwd = command.get("cwd")
        if cwd:
            command["cwd"] = _rebase_absolute_path(
                str(cwd),
                old_run=Path(old_binding.run_dir),
                new_run=Path(new_binding.run_dir),
                old_repo=Path(old_binding.repo_path),
                new_repo=Path(new_binding.repo_path),
                old_paper=Path(old_binding.paper_path),
                new_paper=Path(new_binding.paper_path),
                old_log=(
                    Path(old_binding.log_path)
                    if old_binding.log_path
                    else None
                ),
                new_log=(
                    Path(new_binding.log_path)
                    if new_binding.log_path
                    else None
                ),
            )
    return result


def build_workspace_state_update(
    *,
    state: dict[str, Any],
    new_binding: WorkspaceBinding,
) -> dict[str, Any]:
    """构造有界 update；本函数不直接写 checkpoint。"""

    raw_old = state.get("workspace_binding")
    if raw_old is None:
        # 旧 checkpoint 没有 Phase 26 binding 时，以 state 顶层路径建立旧视图。
        old_binding = new_binding.model_copy(
            update={
                "run_dir": str(state.get("run_dir") or new_binding.run_dir),
                "repo_path": str(
                    state.get("repo_path") or new_binding.repo_path
                ),
                "paper_path": str(
                    state.get("paper_path") or new_binding.paper_path
                ),
                "log_path": state.get("log_path"),
            }
        )
    else:
        old_binding = WorkspaceBinding.model_validate(raw_old)

    if old_binding.job_id != new_binding.job_id:
        raise WorkspaceNotPortableError("workspace binding job_id 改变")
    if old_binding.run_id != new_binding.run_id:
        raise WorkspaceNotPortableError("workspace binding run_id 改变")
    if old_binding.assignment_epoch > new_binding.assignment_epoch:
        raise WorkspaceNotPortableError("拒绝回退 workspace epoch")

    old_run = Path(old_binding.run_dir).resolve()
    new_run = Path(new_binding.run_dir).resolve()
    old_repo = Path(old_binding.repo_path).resolve()
    new_repo = Path(new_binding.repo_path).resolve()
    old_paper = Path(old_binding.paper_path).resolve()
    new_paper = Path(new_binding.paper_path).resolve()
    old_log = (
        Path(old_binding.log_path).resolve()
        if old_binding.log_path
        else None
    )
    new_log = (
        Path(new_binding.log_path).resolve()
        if new_binding.log_path
        else None
    )

    update: dict[str, Any] = {
        "workspace_binding": new_binding.model_dump(),
        "workspace_assignment_epoch": new_binding.assignment_epoch,
        "workspace_manifest_id": new_binding.manifest_id,
        "workspace_manifest_hash": new_binding.manifest_hash,
        "run_dir": str(new_run),
        "repo_path": str(new_repo),
        "paper_path": str(new_paper),
        "log_path": str(new_log) if new_log is not None else None,
        # 新 workspace 必须重新建立 effective profile fingerprint。
        "execution_profile_fingerprint": "",
    }

    for key in SINGLE_PATH_KEYS:
        if key not in state or key in update:
            continue
        update[key] = _rebase_absolute_path(
            state.get(key),
            old_run=old_run,
            new_run=new_run,
            old_repo=old_repo,
            new_repo=new_repo,
            old_paper=old_paper,
            new_paper=new_paper,
            old_log=old_log,
            new_log=new_log,
        )

    for key in PATH_MAP_KEYS:
        if key not in state:
            continue
        update[key] = {
            map_key: _rebase_absolute_path(
                str(value),
                old_run=old_run,
                new_run=new_run,
                old_repo=old_repo,
                new_repo=new_repo,
                old_paper=old_paper,
                new_paper=new_paper,
                old_log=old_log,
                new_log=new_log,
            )
            for map_key, value in dict(state[key]).items()
        }

    for key in ("run_commands", "edited_run_commands"):
        if key in state:
            update[key] = _rebind_commands(
                list(state[key]),
                old_binding=old_binding,
                new_binding=new_binding,
            )

    if "output_files" in state:
        update["output_files"] = [
            _rebase_absolute_path(
                str(value),
                old_run=old_run,
                new_run=new_run,
                old_repo=old_repo,
                new_repo=new_repo,
                old_paper=old_paper,
                new_paper=new_paper,
                old_log=old_log,
                new_log=new_log,
            )
            for value in state["output_files"]
        ]

    if "artifact_records" in state:
        records = [
            ArtifactRecord.model_validate(item)
            for item in state["artifact_records"]
        ]
        update["artifact_records"] = [
            record.model_copy(
                update={
                    "absolute_path": str(
                        (new_run / record.relative_path).resolve()
                    )
                }
            ).model_dump()
            for record in records
        ]

    return update
```

### 30.1 为什么不递归替换所有字符串

Evidence 中可能合法记录：

```text
README 示例路径 /old/path/to/dataset
论文中出现的绝对路径
错误日志中的 traceback path
```

全局字符串替换会篡改证据和日志。只重绑定执行语义明确的字段。

---

## 三十一、不要在 interrupt 后单独调用 update_state

> **本节类型：关键 LangGraph 语义说明，需要修改 Graph runner。**
>
> 修改：`app/job_runtime/graph_runner.py`

下面的代码看起来合理，但不能用于本阶段：

```python
graph.update_state(config, path_updates)
graph.stream(Command(resume=decision), config=config)
```

`update_state()` 会创建一个新 checkpoint；官方文档也说明它不是原地修改，并且 update
会像 node update 一样经过 reducer、影响下一节点。实测在当前 LangGraph 版本中，对
interrupt checkpoint 单独调用它会让新 checkpoint 的 task 不再保留原 interrupt resume
信息。

参考：

- [LangGraph persistence and update state](https://docs.langchain.com/oss/python/langgraph/use-time-travel)
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)

正确做法是把 state update 与 resume 放进同一个 `Command`：

```python
Command(
    resume=claim.resume_request.value,
    update=workspace_state_update,
)
```

普通 pending node（没有动态 interrupt）可以使用：

```python
Command(update=workspace_state_update)
```

这会让路径重绑定与本次恢复成为一次 Graph input。

### 31.1 修改 `_initial_state()`

```python
    def _initial_state(self, claim: JobClaim) -> dict[str, Any]:
        request = claim.job.request
        binding = claim.workspace_binding
        if binding is None or binding.status != "ready":
            raise JobGraphStateError(
                "Graph 初始执行前 workspace 尚未 ready"
            )
        return {
            "job_id": claim.job.job_id,
            "thread_id": claim.job.thread_id,
            "task_id": claim.job.thread_id,
            "run_id": claim.job.run_id,
            "run_dir": binding.run_dir,
            "paper_path": binding.paper_path,
            "repo_path": binding.repo_path,
            "log_path": binding.log_path,
            "workspace_binding": binding.model_dump(),
            "workspace_assignment_epoch": binding.assignment_epoch,
            "workspace_manifest_id": binding.manifest_id,
            "workspace_manifest_hash": binding.manifest_hash,
            "execution_profile_id": request.execution_profile_id,
            "experiment_goal": request.experiment_goal,
            "output_files": [],
            "artifact_records": [],
            "stage_errors": [],
            "inputs_validated": False,
            "step_count": 0,
            "max_steps": settings.max_steps,
        }
```

### 31.2 修改 `execute()` 的 graph input 构造

在读取 snapshot 并校验 Job identity 后：

```python
        binding = claim.workspace_binding
        if binding is None or binding.status != "ready":
            raise JobGraphStateError("workspace binding 未 ready")

        workspace_update = (
            build_workspace_state_update(
                state=values,
                new_binding=binding,
            )
            if values
            else {}
        )

        # terminal checkpoint 不再 invoke，也不需要为了展示结果重绑定。
        if values and not next_nodes:
            return JobExecutionOutcome(
                status="succeeded",
                result=_result_summary(claim=claim, state=values),
                artifact_records=_artifact_records(
                    values,
                    expected_run_id=claim.job.run_id,
                ),
            )

        if interrupts:
            if claim.resume_request is None:
                return JobExecutionOutcome(
                    status="waiting_for_input",
                    result=_result_summary(claim=claim, state=values),
                    interrupts=interrupts,
                    artifact_records=_artifact_records(
                        values,
                        expected_run_id=claim.job.run_id,
                    ),
                )

            current_nodes = {item.node for item in interrupts}
            expected_node = claim.resume_request.expected_node
            if expected_node not in current_nodes:
                return JobExecutionOutcome(
                    status="waiting_for_input",
                    result=_result_summary(claim=claim, state=values),
                    interrupts=interrupts,
                    artifact_records=_artifact_records(
                        values,
                        expected_run_id=claim.job.run_id,
                    ),
                )

            graph_input = Command(
                resume=claim.resume_request.value,
                update=workspace_update,
            )
        elif values:
            graph_input = Command(update=workspace_update)
        else:
            if claim.resume_request is not None:
                raise JobGraphStateError(
                    "没有 checkpoint 却存在 pending resume"
                )
            graph_input = self._initial_state(claim)
```

### 31.3 reducers 注意事项

如果 `artifact_records`、`output_files` 在 State schema 上配置了 append reducer，
`Command(update=...)` 会追加而不是替换，导致记录重复。当前项目 `ReproductionState` 是
普通 `TypedDict`，没有这些 reducer；如果以后增加 reducer，必须改成 keyed merge 或给
rebind 提供专用 replace channel。

---

## 三十二、让 Execution Profile 绑定当前 workspace

> **本节类型：需要修改代码。**
>
> 修改：`app/execution/profile_store.py` 及所有 stateful profile 调用方。

同一个 profile 的安全策略不变，但 `workspace_root/artifact_root/writable_roots` 必须绑定
当前 epoch。新增：

```python
from typing import Any

from app.workspace.schemas import WorkspaceBinding


def get_execution_profile_for_state(
    state: dict[str, Any],
) -> ExecutionProfile:
    profile_id = str(state.get("execution_profile_id") or "")
    if not profile_id:
        raise ValueError("state 缺少 execution_profile_id")

    base = get_execution_profile(profile_id)
    raw_binding = state.get("workspace_binding")
    if raw_binding is None:
        return base

    binding = WorkspaceBinding.model_validate(raw_binding)
    if binding.status != "ready":
        raise ValueError("workspace binding 未 ready")

    # 不保留原主机的任意 writable root。只允许本次 repo 与 run workspace。
    return base.model_copy(
        update={
            "workspace_root": str(Path(binding.repo_path).resolve()),
            "artifact_root": str(Path(binding.run_dir).resolve()),
            "writable_roots": [
                str(Path(binding.repo_path).resolve()),
                str(Path(binding.run_dir).resolve()),
            ],
        }
    )
```

把下列 stateful 调用从：

```python
get_execution_profile(profile_id)
```

改成：

```python
get_execution_profile_for_state(state)
```

涉及：

```text
app/nodes/input_validation_node.py
app/nodes/action_builder_node.py
app/nodes/risk_check_node.py
app/tools/preflight_tools.py
app/tools/exec_tools.py
app/tools/repair_tools.py
app/tools/patch_tools.py
```

`app/main.py` 中纯 profile 查询/探测命令没有 Graph state，可以继续使用
`get_execution_profile()`。

Action builder、risk check 和 executor 都必须使用同一 effective profile。计算出的
approval fingerprint 包含当前 repo/run path，所以 handoff 后旧 action approval 自然
失效；本阶段又在 seal 前阻断 pending action 的跨 host 迁移，形成双重保护。

### 32.1 修改 Input Validation

`_check_execution_profile()` 增加 `state` 参数并使用 effective profile；不要再拿 host
config 中的原始 `workspace_root` 与 materialized `repo_path` 比较。调用示例：

```python
def _check_execution_profile(
    *,
    state: dict[str, Any],
    repo_path: str | None,
) -> InputCheck:
    try:
        profile = get_execution_profile_for_state(state)
    except (FileNotFoundError, ValueError) as exc:
        return InputCheck(
            name="execution_profile",
            status="failed",
            category="environment",
            code="EXECUTION_PROFILE_INVALID",
            message=str(exc),
        )

    workspace = Path(profile.workspace_root).resolve()
    repo = Path(repo_path or "").resolve()
    if repo != workspace:
        return InputCheck(
            name="execution_profile",
            status="failed",
            category="environment",
            code="REPO_BINDING_MISMATCH",
            message="repo_path 与 effective workspace binding 不一致",
            path=str(workspace),
        )
    return InputCheck(
        name="execution_profile",
        status="passed",
        category="environment",
        code="OK",
        message=f"execution profile 可用：{profile.profile_id}",
        path=str(workspace),
    )
```

---

## 三十三、扩展 Graph state

> **本节类型：需要修改代码。**
>
> 修改：`app/state.py`

增加：

```python
    # Phase 26：完整 manifest 留在 PostgreSQL，state 只保存当前 binding identity。
    workspace_binding: dict[str, Any]
    workspace_assignment_epoch: int
    workspace_manifest_id: str
    workspace_manifest_hash: str
```

这些字段也应进入 run manifest 的运行身份区域，但不得写入
`workspace_assignment_token`。生成报告时使用删减视图：

```python
binding = dict(state.get("workspace_binding") or {})
binding.pop("assignment_token", None)
```

公开 Artifact、API 和最终报告都不能泄漏 fencing token。

---

## 三十四、WorkspaceManager 编排 prepare 与 seal

> **本节类型：需要新增代码。**
>
> 新增：`app/workspace/manager.py`

```python
from __future__ import annotations

from app.job_runtime.ports import JobStore
from app.job_runtime.schemas import JobClaim, JobExecutionOutcome
from app.job_runtime.errors import LeaseLostError
from app.workspace.materializer import WorkspaceMaterializer
from app.workspace.snapshot import WorkspaceSnapshotter
from app.workspace.schemas import WorkspaceBinding
from app.job_runtime.process_reconcile import (
    workspace_portability_blockers,
)


class WorkspaceManager:
    def __init__(
        self,
        *,
        store: JobStore,
        materializer: WorkspaceMaterializer,
        snapshotter: WorkspaceSnapshotter,
    ):
        self.store = store
        self.materializer = materializer
        self.snapshotter = snapshotter

    def prepare(self, claim: JobClaim) -> JobClaim:
        """claim 后、Graph 前执行；所有 DB 更新继续受 claim token fencing。"""

        job = claim.job
        manifest = self.store.get_workspace_manifest(
            job.workspace_manifest_id
        )
        if manifest.manifest_hash == "":
            raise ValueError("workspace manifest 缺少 hash")

        assignment_token = job.workspace_assignment_token
        if assignment_token is None:
            raise ValueError("claimed Job 缺少 workspace assignment token")

        planned = self.materializer.planned_binding(
            worker=claim.worker,
            manifest=manifest,
            requirements=job.requirements,
            assignment_epoch=job.workspace_assignment_epoch,
            assignment_token=assignment_token,
        )
        persisted = self.store.begin_workspace_assignment(
            job_id=job.job_id,
            claim_token=claim.claim_token,
            worker=claim.worker,
            manifest=manifest,
            assignment_token=assignment_token,
            workspace_root=planned.workspace_root,
            run_dir=planned.run_dir,
            repo_path=planned.repo_path,
            paper_path=planned.paper_path,
            log_path=planned.log_path,
        )

        try:
            self.materializer.materialize(
                manifest=manifest,
                binding=persisted,
            )
            ready = self.store.mark_workspace_ready(
                job_id=job.job_id,
                claim_token=claim.claim_token,
                assignment_token=assignment_token,
            )
        except Exception as exc:
            # 失败登记也受 fencing 保护；旧 Worker 丢 lease 时不能用登记失败
            # 覆盖新 Worker 的 assignment，同时不能让 LeaseLost 掩盖原始异常。
            try:
                self.store.fail_workspace_assignment(
                    job_id=job.job_id,
                    claim_token=claim.claim_token,
                    assignment_token=assignment_token,
                    reason=type(exc).__name__,
                )
            except LeaseLostError:
                pass
            raise

        return claim.model_copy(
            update={"workspace_binding": ready}
        )

    def seal_waiting(
        self,
        *,
        claim: JobClaim,
        outcome: JobExecutionOutcome,
    ) -> WorkspaceBinding:
        binding = claim.workspace_binding
        if binding is None:
            raise ValueError("seal 前缺少 workspace binding")

        state = dict(outcome.checkpoint_state)
        blockers = workspace_portability_blockers(
            run_dir=binding.run_dir,
            interrupt_nodes=[item.node for item in outcome.interrupts],
            state=state,
        )
        parent = self.store.get_workspace_manifest(
            claim.job.workspace_manifest_id
        )
        manifest = self.snapshotter.seal(
            job_id=claim.job.job_id,
            run_id=claim.job.run_id,
            run_dir=binding.run_dir,
            repo_path=binding.repo_path,
            paper_path=binding.paper_path,
            log_path=binding.log_path,
            parent=parent,
            source_host_id=claim.worker.host_id,
            source_worker_session_id=claim.worker.worker_session_id,
            artifact_records=outcome.artifact_records,
            external_data=parent.external_data,
            blocked_reasons=blockers,
        )
        affinity = (
            None if manifest.portable else claim.worker.host_id
        )
        self.store.seal_workspace_manifest(
            job_id=claim.job.job_id,
            claim_token=claim.claim_token,
            assignment_token=binding.assignment_token,
            manifest=manifest,
            affinity_host_id=affinity,
            actor=claim.worker.worker_id,
        )
        return binding
```

`seal_waiting()` 返回 binding 主要便于测试；Job 的 current manifest pointer 已经在 Store
中更新。不要在这个方法里调用 `mark_waiting()`，状态转换仍由 Worker 统一提交。

---

## 三十五、让 JobExecutionOutcome 暂存 checkpoint state

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/schemas.py`、`app/job_runtime/graph_runner.py`

增加仅进程内使用、不会进入持久 result 的字段：

```python
class JobExecutionOutcome(JobModel):
    # 原有 status/result/interrupts/artifact_records 保持不变。

    checkpoint_state: dict[str, Any] = Field(
        default_factory=dict,
        exclude=True,
    )
```

`GraphJobRunner.execute()` 的每个 outcome 都填入对应 snapshot values：

```python
checkpoint_state=final_values
```

执行前就发现 terminal checkpoint 时填 `values`；初次 interrupt 检查时也填 `values`。

该 state 只在当前 Worker 内传给 `WorkspaceManager.seal_waiting()`，不能整体写进 Job
`result_json`，否则会把大 state、Prompt、路径和 potentially sensitive context 复制进
PostgreSQL control row。

---

## 三十六、Worker session heartbeat

> **本节类型：需要新增代码。**
>
> 新增：`app/workspace/heartbeat.py`

```python
from __future__ import annotations

import threading
from collections.abc import Callable

from app.job_runtime.ports import JobStore
from app.workspace.schemas import WorkerIdentity


class WorkerSessionHeartbeat:
    """Worker 空闲或执行 Graph 时都续 session lease。"""

    def __init__(
        self,
        *,
        store: JobStore,
        identity_factory: Callable[[], WorkerIdentity],
        lease_seconds: float,
        interval_seconds: float,
    ):
        self.store = store
        self.identity_factory = identity_factory
        self.lease_seconds = lease_seconds
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._identity: WorkerIdentity | None = None
        self._error: BaseException | None = None

    @property
    def identity(self) -> WorkerIdentity:
        with self._lock:
            if self._identity is None:
                raise RuntimeError("Worker session 尚未启动")
            return self._identity

    def _refresh(self) -> None:
        identity = self.identity_factory()
        self.store.heartbeat_worker(
            worker=identity,
            lease_seconds=self.lease_seconds,
        )
        with self._lock:
            self._identity = identity

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self._refresh()
            except BaseException as exc:  # noqa: BLE001
                with self._lock:
                    self._error = exc
                return

    def start(self) -> WorkerIdentity:
        with self._lock:
            existing = self._thread
            current_identity = self._identity
        if existing is not None:
            if current_identity is None:
                raise RuntimeError("Worker heartbeat 状态不一致")
            return current_identity

        identity = self.identity_factory()
        self.store.register_worker(
            worker=identity,
            lease_seconds=self.lease_seconds,
        )
        thread = threading.Thread(
            target=self._loop,
            name=f"worker-session-{identity.worker_session_id}",
            daemon=True,
        )
        with self._lock:
            if self._thread is not None:
                raise RuntimeError("Worker heartbeat 被并发启动")
            self._identity = identity
            self._thread = thread
        thread.start()
        return identity

    def raise_if_unhealthy(self) -> None:
        with self._lock:
            error = self._error
        if error is not None:
            raise RuntimeError("Worker session heartbeat failed") from error

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=max(self.interval_seconds * 2, 1.0))
        identity = self._identity
        if identity is not None:
            try:
                self.store.drain_worker(
                    worker_session_id=identity.worker_session_id
                )
            except Exception:  # noqa: BLE001
                # 关闭路径不能覆盖当前 Job 的真实结果。
                pass
```

---

## 三十七、把 WorkspaceManager 接入 JobWorker

> **本节类型：需要修改核心 Worker。**
>
> 修改：`app/job_runtime/worker.py`

### 37.1 构造函数

增加参数和字段：

```python
class JobWorker:
    def __init__(
        self,
        *,
        worker_id: str,
        store: JobStore,
        workspace_manager: WorkspaceManager,
        runner: GraphJobRunner | None = None,
        artifact_publisher: ArtifactPublisher | None = None,
        lease_seconds: float | None = None,
        heartbeat_seconds: float | None = None,
        poll_seconds: float | None = None,
    ):
        if not worker_id.strip():
            raise ValueError("worker_id 不能为空")

        self.worker_id = worker_id
        self.store = store
        self.workspace_manager = workspace_manager
        self.runner = runner or GraphJobRunner()
        self.artifact_publisher = artifact_publisher
        self.lease_seconds = (
            lease_seconds
            if lease_seconds is not None
            else settings.job_lease_seconds
        )
        self.heartbeat_seconds = (
            heartbeat_seconds
            if heartbeat_seconds is not None
            else settings.job_heartbeat_seconds
        )
        self.poll_seconds = (
            poll_seconds
            if poll_seconds is not None
            else settings.job_poll_seconds
        )
        self._worker_session_id = f"ws_{uuid4().hex}"
        self.session_heartbeat = WorkerSessionHeartbeat(
            store=store,
            identity_factory=lambda: build_worker_identity(
                worker_id=self.worker_id,
                worker_session_id=self._worker_session_id,
            ),
            lease_seconds=settings.worker_session_lease_seconds,
            interval_seconds=(
                settings.worker_session_heartbeat_seconds
            ),
        )
        self.reconciler = JobReconciler(
            store=store,
            actor=worker_id,
            host_id=settings.worker_host_id,
        )
```

需要新增 imports：

```python
from uuid import uuid4

from app.workspace.capabilities import build_worker_identity
from app.workspace.heartbeat import WorkerSessionHeartbeat
from app.workspace.manager import WorkspaceManager
```

### 37.2 `_notify_process_cancel()` 使用 binding

```python
    def _notify_process_cancel(
        self,
        claim: JobClaim,
        reason: str,
    ) -> None:
        binding = claim.workspace_binding
        if binding is None:
            return
        try:
            request_run_cancellation(
                run_dir=binding.run_dir,
                reason=reason,
                requested_by=self.worker_id,
            )
        except (ValueError, FileNotFoundError):
            return
```

### 37.3 修改 `run_once()` 主流程

保留原错误处理结构，但把成功路径改成：

先把原有两段 `mark_failed()` 异常处理抽成以下辅助方法。这样主流程更清晰，同时继续保证
旧 Worker 在 lease/token 失效后静默退出：

```python
    def _mark_retryable_if_owned(
        self,
        claim: JobClaim,
        exc: BaseException,
    ) -> None:
        try:
            self.store.mark_failed(
                job_id=claim.job.job_id,
                claim_token=claim.claim_token,
                error=self._error_payload(exc),
                actor=self.worker_id,
                retryable=True,
            )
        except LeaseLostError:
            pass

    def _mark_terminal_if_owned(
        self,
        claim: JobClaim,
        exc: BaseException,
    ) -> None:
        try:
            self.store.mark_failed(
                job_id=claim.job.job_id,
                claim_token=claim.claim_token,
                error=self._error_payload(exc),
                actor=self.worker_id,
                # 未知异常可能已经越过副作用边界，默认不自动 retry。
                retryable=False,
            )
        except LeaseLostError:
            pass
```

然后替换 `run_once()`：

```python
    def run_once(self) -> bool:
        worker_identity = self.session_heartbeat.start()
        self.session_heartbeat.raise_if_unhealthy()

        self.reconciler.reconcile_expired()
        claim = self.store.claim_next(
            worker=worker_identity,
            lease_seconds=self.lease_seconds,
        )
        if claim is None:
            return False

        heartbeat = LeaseHeartbeat(
            store=self.store,
            job_id=claim.job.job_id,
            claim_token=claim.claim_token,
            lease_seconds=self.lease_seconds,
            interval_seconds=self.heartbeat_seconds,
            on_cancel_requested=lambda reason: (
                self._notify_process_cancel(claim, reason)
            ),
        )

        try:
            with heartbeat:
                claim = self.workspace_manager.prepare(claim)
                heartbeat.raise_if_unhealthy()
                self.session_heartbeat.raise_if_unhealthy()

                outcome = self.runner.execute(claim, heartbeat)
                heartbeat.raise_if_unhealthy()

                publication = None
                if self.artifact_publisher is not None:
                    publication = self.artifact_publisher.publish(
                        job=claim.job,
                        records=outcome.artifact_records,
                        workspace_binding=claim.workspace_binding,
                        ensure_active=heartbeat.raise_if_unhealthy,
                    )
                heartbeat.raise_if_unhealthy()

                # waiting 前必须先得到新的可恢复 manifest pointer。
                if outcome.status == "waiting_for_input":
                    self.workspace_manager.seal_waiting(
                        claim=claim,
                        outcome=outcome,
                    )
                heartbeat.raise_if_unhealthy()

            result = dict(outcome.result)
            if publication is not None:
                result["artifact_publication"] = publication.model_dump()

            if outcome.status == "waiting_for_input":
                self.store.mark_waiting(
                    job_id=claim.job.job_id,
                    claim_token=claim.claim_token,
                    interrupts=outcome.interrupts,
                    result=result,
                    actor=self.worker_id,
                )
            elif outcome.status == "cancelled":
                self.store.mark_cancelled(
                    job_id=claim.job.job_id,
                    claim_token=claim.claim_token,
                    reason=(
                        heartbeat.cancellation_reason
                        or "runner cancelled"
                    ),
                    actor=self.worker_id,
                )
            else:
                self.store.mark_succeeded(
                    job_id=claim.job.job_id,
                    claim_token=claim.claim_token,
                    result=result,
                    actor=self.worker_id,
                )
        except ArtifactBackendUnavailable as exc:
            self._mark_retryable_if_owned(claim, exc)
        except LeaseLostError:
            pass
        except Exception as exc:  # noqa: BLE001
            self._mark_terminal_if_owned(claim, exc)

        return True
```

Workspace integrity 错误不能一律当普通 provider retry：

```text
ArtifactBackendUnavailable        retryable
WorkspaceNotPortableError         通常 scheduling/affinity conflict
WorkspaceIntegrityError           reconciliation_required 或 terminal security error
WorkerCapabilityError             queued/unschedulable，不应在 claim 后出现
LeaseLostError                    旧 Worker 静默放弃终态写入
```

如果 `prepare()` 发现 manifest hash 错误，推荐新增 Store 方法
`require_workspace_reconciliation()`，以当前 claim token 原子进入
`reconciliation_required`，而不是标记普通 `failed`。

### 37.4 close 与 run_forever

```python
    def close(self) -> None:
        self.session_heartbeat.close()

    def run_forever(
        self,
        *,
        stop_event: threading.Event | None = None,
    ) -> None:
        stop = stop_event or threading.Event()
        self.session_heartbeat.start()
        try:
            while not stop.is_set():
                self.session_heartbeat.raise_if_unhealthy()
                handled = self.run_once()
                if not handled:
                    stop.wait(self.poll_seconds)
        finally:
            self.close()
```

CLI 的 `--once` 分支也必须 `try/finally: worker.close()`，否则 session 会一直显示 active
直到 lease 到期。

---

## 三十八、远端进程不能由本机自动判活

> **本节类型：需要修改 crash reconciliation。**
>
> 修改：`app/job_runtime/process_reconcile.py`

`JobReconciler` 增加 `host_id`，并读取 current binding：

```python
class JobReconciler:
    def __init__(
        self,
        *,
        store: JobStore,
        actor: str,
        host_id: str,
    ):
        self.store = store
        self.actor = actor
        self.host_id = host_id
```

在检查 expired Job 前：

```python
binding = self.store.current_workspace_binding(job.job_id)
if binding is not None and binding.host_id != self.host_id:
    decision = ReconcileDecision(
        disposition="ambiguous_process",
        detail=(
            "expired Job 属于其他 host；当前 Worker 不能用本机 PID namespace "
            "证明远端 subprocess 已结束"
        ),
        process_records=[],
    )
else:
    decision = inspect_job_processes(
        job,
        run_dir=(binding.run_dir if binding is not None else job.run_dir),
    )
```

修改 `inspect_job_processes()` 接受显式 `run_dir`，不要再固定读取 `job.run_dir`。

即使远端 Worker session lease 也过期，也不能自动认为其训练进程已结束：Worker 进程和
它启动的子进程可能有不同生命周期。人工确认主机已下线、容器已销毁或 scheduler 已
fence 后，才允许 reconciliation。

此外，running crash 时 PostgreSQL checkpoint 可能比最后一次 sealed workspace
manifest 更新。Phase 26 不自动把这种 Job 迁到新 host；本阶段自动 handoff 只接受
`waiting_for_input` 之后由 decision 重新排队的任务。

---

## 三十九、分布式取消不再由 API 写远端文件

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/service.py`

Phase 25 的 `JobService.cancel()` 会在 API 进程直接执行：

```python
request_run_cancellation(
    run_dir=record.run_dir,
    reason=reason,
    requested_by=actor,
)
```

跨主机后 API 的本地路径不是 active Worker workspace。删除这段直接文件桥接，只保留：

```text
API -> PostgreSQL cancel_requested=true
Job heartbeat -> Worker 收到 cancellation_reason
Worker -> 当前 binding.run_dir 写 cancel request
ProcessSupervisor -> 精确取消 PID/create_time/PGID
```

因此 `cancel()` 简化为：

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
        return self.store.request_cancel(
            job_id=job_id,
            reason=reason,
            actor=actor,
            idempotency_key=idempotency_key,
            expected_job_version=expected_job_version,
        )
```

这会略微增加取消延迟，最大约为 Job heartbeat interval；但不会误写 API 主机上的同名
目录。

---

## 四十、更新 composition root

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/service.py`、`app/main.py`、`app/api/app.py`

### 40.1 修改 `build_job_service()`

```python
def build_job_service() -> JobService:
    """CLI、API 和 Worker 共用 Store/Blob 配置。"""

    storage = build_artifact_storage()
    return JobService(
        build_job_store(),
        workspace_snapshotter=WorkspaceSnapshotter(
            blob_store=storage.selected_store
        ),
    )
```

需要 imports：

```python
from app.storage.factory import build_artifact_storage
from app.workspace.snapshot import WorkspaceSnapshotter
```

单元测试直接构造 `JobService` 时注入 fake/local Snapshotter，不允许为了省事在构造函数
中偷偷读取 production S3。

### 40.2 修改 `run-worker`

在创建 Worker 前：

```python
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
```

创建 Worker：

```python
    worker = JobWorker(
        worker_id=effective_worker_id,
        store=service.store,
        workspace_manager=workspace_manager,
        artifact_publisher=artifact_storage.publisher,
    )
```

启动输出增加非敏感摘要：

```python
print(
    {
        "worker_id": effective_worker_id,
        "host_id": settings.worker_host_id,
        "worker_pool": settings.worker_pool,
        "workspace_root": str(settings.worker_workspace_root.resolve()),
        "artifact_backend": settings.artifact_blob_backend,
        "artifact_sharing_scope": (
            artifact_storage.selected_store.sharing_scope
        ),
        "once": once,
    }
)
```

`--once` 必须关闭：

```python
    if once:
        try:
            handled = worker.run_once()
            print({"handled": handled})
        finally:
            worker.close()
        return
```

`run_forever()` 已经 finally close；外层 Ctrl+C 不要再次并发 close。

### 40.3 API app 避免无意创建多套 storage bundle

推荐让 app factory 一次组装：

```python
    storage = build_artifact_storage()
    selected_job_service = (
        job_service
        if job_service is not None
        else JobService(
            build_job_store(),
            workspace_snapshotter=WorkspaceSnapshotter(
                blob_store=storage.selected_store
            ),
        )
    )
    selected_catalog = artifact_catalog or storage.catalog
```

测试注入 `job_service` 与 `artifact_catalog` 时，可以不创建 production storage。可写成：

```python
    storage = None
    if job_service is None or artifact_catalog is None:
        storage = build_artifact_storage()

    if job_service is None:
        assert storage is not None
        job_service = JobService(
            build_job_store(),
            workspace_snapshotter=WorkspaceSnapshotter(
                blob_store=storage.selected_store
            ),
        )
    if artifact_catalog is None:
        assert storage is not None
        artifact_catalog = storage.catalog
```

这样 API 单元测试不会因本机没有 S3 credential 在 import/app factory 阶段失败。

---

## 四十一、增加公开调度与 Workspace 视图

> **本节类型：需要修改 API/交互层。**
>
> 修改：`app/interaction/schemas.py`、`app/interaction/service.py`、
> `app/api/routes.py`

### 41.1 Public schema

```python
class PublicScheduling(InteractionModel):
    worker_pool: str
    execution_profile_id: str
    min_gpu_count: int
    cuda_major: int | None = None
    required_labels: list[str] = Field(default_factory=list)
    affinity_host_id: str | None = None
    workspace_manifest_generation: int
    workspace_assignment_epoch: int
    active_host_id: str | None = None


class WorkerView(InteractionModel):
    worker_id: str
    worker_session_id: str
    host_id: str
    pool: str
    status: str
    execution_profile_ids: list[str]
    gpu_count: int
    cuda_major: int | None = None
    labels: list[str] = Field(default_factory=list)
    workspace_free_bytes: int
    heartbeat_at: str
    lease_expires_at: str


class WorkerListResponse(InteractionModel):
    items: list[WorkerView]
    count: int


class WorkspaceView(InteractionModel):
    job_id: str
    manifest_id: str
    manifest_hash: str
    generation: int
    portable: bool
    blocked_reasons: list[str]
    entry_count: int
    total_bytes: int
    repository_commit: str
    repository_clean: bool
    source_host_id: str
    assignment_epoch: int
    assignment_status: str | None = None
    active_host_id: str | None = None
```

给 `JobView` 增加：

```python
scheduling: PublicScheduling
```

投影时显式 allowlist，不返回：

```text
claim_token
workspace_assignment_token
workspace_root/run_dir/repo_path/paper_path
S3 object_key
source_paths
```

### 41.2 Service 方法

```python
def list_workers(self) -> list[WorkerView]:
    return [
        WorkerView(
            worker_id=item.worker_id,
            worker_session_id=item.worker_session_id,
            host_id=item.host_id,
            pool=item.pool,
            status=item.status,
            execution_profile_ids=(
                item.capabilities.execution_profile_ids
            ),
            gpu_count=item.capabilities.gpu_count,
            cuda_major=item.capabilities.cuda_major,
            labels=item.capabilities.labels,
            workspace_free_bytes=(
                item.capabilities.workspace_free_bytes
            ),
            heartbeat_at=item.heartbeat_at,
            lease_expires_at=item.lease_expires_at,
        )
        for item in self.job_service.store.list_workers()
    ]


def get_workspace(self, job_id: str) -> WorkspaceView:
    job = self.job_service.get(job_id)
    manifest = self.job_service.store.get_workspace_manifest(
        job.workspace_manifest_id
    )
    binding = self.job_service.store.current_workspace_binding(job_id)
    return WorkspaceView(
        job_id=job_id,
        manifest_id=manifest.manifest_id,
        manifest_hash=manifest.manifest_hash,
        generation=manifest.generation,
        portable=manifest.portable,
        blocked_reasons=manifest.blocked_reasons,
        entry_count=len(manifest.entries),
        total_bytes=sum(item.size_bytes for item in manifest.entries),
        repository_commit=manifest.repository.commit_sha,
        repository_clean=manifest.repository.clean,
        source_host_id=manifest.source_host_id,
        assignment_epoch=job.workspace_assignment_epoch,
        assignment_status=(binding.status if binding else None),
        active_host_id=(binding.host_id if binding else None),
    )
```

### 41.3 Routes

```python
@router.get(
    "/workers",
    response_model=WorkerListResponse,
)
def list_workers(
    _actor: Actor,
    service: InteractionDependency,
) -> WorkerListResponse:
    items = service.list_workers()
    return WorkerListResponse(items=items, count=len(items))


@router.get(
    "/jobs/{job_id}/workspace",
    response_model=WorkspaceView,
)
def get_workspace(
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
) -> WorkspaceView:
    return service.get_workspace(job_id)
```

Event payload 也要经过 `_public_value()`；把以下 key 加入 `_REDACTED_KEYS`：

```python
"assignment_token",
"workspace_assignment_token",
"workspace_root",
"source_paths",
```

---

## 四十二、增加 CLI 诊断命令

> **本节类型：需要修改 CLI。**
>
> 修改：`app/main.py`

### 42.1 `list-workers`

```python
@app.command("list-workers")
def list_workers_command(
    include_expired: bool = typer.Option(
        False,
        "--include-expired",
    ),
):
    service = build_job_service()
    workers = service.store.list_workers(
        include_expired=include_expired
    )
    print(
        [
            {
                "worker_id": item.worker_id,
                "worker_session_id": item.worker_session_id,
                "host_id": item.host_id,
                "pool": item.pool,
                "status": item.status,
                "profiles": item.capabilities.execution_profile_ids,
                "gpu_count": item.capabilities.gpu_count,
                "cuda_major": item.capabilities.cuda_major,
                "labels": item.capabilities.labels,
                "workspace_free_bytes": (
                    item.capabilities.workspace_free_bytes
                ),
                "lease_expires_at": item.lease_expires_at,
            }
            for item in workers
        ]
    )
```

### 42.2 `show-workspace`

```python
@app.command("show-workspace")
def show_workspace_command(job_id: str):
    service = build_job_service()
    job = service.get(job_id)
    manifest = service.store.get_workspace_manifest(
        job.workspace_manifest_id
    )
    binding = service.store.current_workspace_binding(job_id)
    print(
        {
            "job_id": job_id,
            "manifest_id": manifest.manifest_id,
            "manifest_hash": manifest.manifest_hash,
            "generation": manifest.generation,
            "portable": manifest.portable,
            "blocked_reasons": manifest.blocked_reasons,
            "source_host_id": manifest.source_host_id,
            "entry_count": len(manifest.entries),
            "total_bytes": sum(
                item.size_bytes for item in manifest.entries
            ),
            "repo_commit": manifest.repository.commit_sha,
            "repo_clean": manifest.repository.clean,
            "affinity_host_id": job.affinity_host_id,
            "assignment_epoch": job.workspace_assignment_epoch,
            "binding_status": binding.status if binding else None,
            "binding_host_id": binding.host_id if binding else None,
            # 不打印 assignment token 和 object keys。
        }
    )
```

### 42.3 `explain-scheduling`

```python
@app.command("explain-scheduling")
def explain_scheduling_command(job_id: str):
    service = build_job_service()
    job = service.get(job_id)
    rows = []
    for session in service.store.list_workers(
        include_expired=False
    ):
        worker = WorkerIdentity(
            worker_id=session.worker_id,
            worker_session_id=session.worker_session_id,
            host_id=session.host_id,
            pool=session.pool,
            workspace_root=session.workspace_root,
            capabilities=session.capabilities,
        )
        explanation = explain_compatibility(
            requirements=job.requirements,
            worker=worker,
            affinity_host_id=job.affinity_host_id,
        )
        rows.append(
            {
                "worker_id": worker.worker_id,
                "host_id": worker.host_id,
                "compatible": explanation.compatible,
                "reasons": explanation.reasons,
            }
        )
    print(
        {
            "job_id": job_id,
            "requirements": job.requirements.model_dump(),
            "affinity_host_id": job.affinity_host_id,
            "workers": rows,
        }
    )
```

该命令只解释当前快照；最终 claim 仍以数据库 transaction 内的 worker session lease 与
capability 为准。

---

## 四十三、日志读取的跨主机降级语义

> **本节类型：需要修改交互行为。**
>
> 修改：`app/job_runtime/service.py` 或增加 Published Log Reader。

当前 `tail_log()` 直接读取 local run path。第一版有两个可接受实现，推荐 A：

```text
A. 从 PublishedArtifactCatalog 找最新 process_log 并流式 tail（推荐）
B. binding.host_id != API_HOST_ID 时返回明确 LOG_NOT_LOCAL
```

不能做：

```text
路径不存在 -> 返回空字符串 -> 让用户误以为从未产生日志
```

如果先实现 B：

```python
binding = self.store.current_workspace_binding(job_id)
if binding is not None and binding.host_id != settings.worker_host_id:
    raise JobConflictError(
        "LOG_NOT_LOCAL：请从 published Artifact 下载 process log"
    )
```

后续实现 A 时，下载到内存前仍要执行 `max_bytes` 限制；不要为了 tail 最后 100 行无界
读取数 GB 日志。更完整的方案需要 S3 Range GET，可放在下一阶段。

---

## 四十四、先更新 JobStore contract fixture

> **本节类型：需要修改测试基础设施。**
>
> 修改：`tests/job_store_contract.py`、Phase 25 中所有直接调用
> `claim_next(worker_id=...)` 的测试。

在文件顶部增加：

```python
from datetime import datetime, timezone

from app.workspace.repository import workspace_manifest_hash
from app.workspace.schemas import (
    JobRequirements,
    RepositoryIdentity,
    WorkerCapabilities,
    WorkerIdentity,
    WorkspaceManifest,
    WorkspaceSourcePaths,
)
```

增加共享构造器：

```python
POLICY_HASH = "a" * 64


def worker_fixture(
    *,
    worker_id: str = "worker-a",
    session_id: str = "session-a",
    host_id: str = "host-a",
    pool: str = "default",
    labels: list[str] | None = None,
    gpu_count: int = 0,
    cuda_major: int | None = None,
) -> WorkerIdentity:
    return WorkerIdentity(
        worker_id=worker_id,
        worker_session_id=session_id,
        host_id=host_id,
        pool=pool,
        workspace_root=f"/data/workspaces/{host_id}",
        capabilities=WorkerCapabilities(
            execution_profile_ids=["local"],
            execution_backends=["local"],
            execution_policy_hashes={"local": POLICY_HASH},
            cpu_count=8,
            memory_bytes=16 * 1024**3,
            workspace_free_bytes=100 * 1024**3,
            gpu_count=gpu_count,
            cuda_major=cuda_major,
            labels=labels or [],
        ),
    )


def requirements_fixture() -> JobRequirements:
    return JobRequirements(
        worker_pool="default",
        execution_profile_id="local",
        execution_policy_hash=POLICY_HASH,
        execution_backend="local",
    )


def manifest_fixture(
    *,
    suffix: str,
    host_id: str = "host-a",
) -> WorkspaceManifest:
    draft = WorkspaceManifest(
        manifest_id=f"manifest-{suffix}",
        manifest_hash="",
        job_id=f"job-{suffix}",
        run_id=f"run-{suffix}",
        generation=0,
        source_host_id=host_id,
        entries=[],
        repository=RepositoryIdentity(
            commit_sha="b" * 40,
            branch="main",
            clean=False,
            bundle_logical_path=None,
        ),
        portable=False,
        blocked_reasons=["contract-host-local"],
        source_paths=WorkspaceSourcePaths(
            repo_path="/data/repo",
            paper_path="/data/paper.pdf",
        ),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return draft.model_copy(
        update={"manifest_hash": workspace_manifest_hash(draft)}
    )
```

更新 `submit_fixture()`：

```python
def submit_fixture(
    store,
    *,
    suffix: str = "1",
    max_attempts: int = 3,
):
    return store.submit(
        job_id=f"job-{suffix}",
        idempotency_key=f"submit-{suffix}",
        thread_id=f"thread-{suffix}",
        run_id=f"run-{suffix}",
        run_dir=f"/data/runs/run-{suffix}",
        request=_request(),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix=suffix),
        max_attempts=max_attempts,
    )
```

在每个 contract claim 前注册并传完整 worker：

```python
worker = worker_fixture()
store.register_worker(worker=worker, lease_seconds=30)
claim = store.claim_next(worker=worker, lease_seconds=30)
```

如果一个测试需要 Worker B claim host-affine fixture，它必须仍声明 `host_id="host-a"`；
需要验证不同 host 被阻断时再使用 `host-b`。不要为了让旧测试通过而忽略 affinity。

Phase 25 所有并发 claim helper 也要改成每个线程使用唯一 `worker_session_id`，并先注册。

---

## 四十五、Worker capability 单元测试

> **本节类型：需要新增测试。**
>
> 新增：`tests/test_worker_capabilities.py`

```python
from app.workspace.capabilities import explain_compatibility
from app.workspace.schemas import (
    JobRequirements,
    WorkerCapabilities,
    WorkerIdentity,
)


def _worker(
    *,
    host_id: str = "host-a",
    gpu_count: int = 1,
    cuda_major: int | None = 11,
    labels: list[str] | None = None,
) -> WorkerIdentity:
    return WorkerIdentity(
        worker_id="worker",
        worker_session_id=f"session-{host_id}",
        host_id=host_id,
        pool="gpu",
        workspace_root=f"/data/workspaces/{host_id}",
        capabilities=WorkerCapabilities(
            execution_profile_ids=["pstnet"],
            execution_backends=["local"],
            execution_policy_hashes={"pstnet": "a" * 64},
            cpu_count=16,
            memory_bytes=64 * 1024**3,
            workspace_free_bytes=200 * 1024**3,
            gpu_count=gpu_count,
            cuda_major=cuda_major,
            labels=labels or ["dataset:pstnet-ready"],
        ),
    )


def _requirements() -> JobRequirements:
    return JobRequirements(
        worker_pool="gpu",
        execution_profile_id="pstnet",
        execution_policy_hash="a" * 64,
        execution_backend="local",
        min_workspace_free_bytes=10 * 1024**3,
        min_gpu_count=1,
        cuda_major=11,
        required_labels=["dataset:pstnet-ready"],
    )


def test_compatible_worker_matches() -> None:
    result = explain_compatibility(
        requirements=_requirements(),
        worker=_worker(),
        affinity_host_id=None,
    )
    assert result.compatible is True
    assert result.reasons == []


def test_cuda_mismatch_is_explicit() -> None:
    result = explain_compatibility(
        requirements=_requirements(),
        worker=_worker(cuda_major=12),
        affinity_host_id=None,
    )
    assert result.compatible is False
    assert "cuda_major_mismatch" in result.reasons


def test_policy_hash_mismatch_is_rejected() -> None:
    worker = _worker()
    worker = worker.model_copy(
        update={
            "capabilities": worker.capabilities.model_copy(
                update={
                    "execution_policy_hashes": {
                        "pstnet": "b" * 64
                    }
                }
            )
        }
    )
    result = explain_compatibility(
        requirements=_requirements(),
        worker=worker,
        affinity_host_id=None,
    )
    assert "execution_policy_hash_mismatch" in result.reasons


def test_affinity_blocks_other_host() -> None:
    result = explain_compatibility(
        requirements=_requirements(),
        worker=_worker(host_id="host-b"),
        affinity_host_id="host-a",
    )
    assert result.compatible is False
    assert "host_affinity_mismatch" in result.reasons
```

运行：

```bash
python -m pytest -q tests/test_worker_capabilities.py
```

---

## 四十六、Manifest hash 测试

> **本节类型：需要新增测试。**
>
> 新增：`tests/test_workspace_manifest.py`

```python
from datetime import datetime, timezone

import pytest

from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.repository import (
    validate_manifest_hash,
    workspace_manifest_hash,
)
from app.workspace.schemas import (
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)


def _manifest() -> WorkspaceManifest:
    draft = WorkspaceManifest(
        manifest_id="wm-test",
        manifest_hash="",
        job_id="job-test",
        run_id="run-test",
        generation=0,
        source_host_id="host-a",
        entries=[
            WorkspaceBlobEntry(
                logical_path="source/paper.pdf",
                role="paper",
                object_key="workspace/sha256/aa/" + "a" * 64,
                sha256="a" * 64,
                size_bytes=10,
                media_type="application/pdf",
            ),
            WorkspaceBlobEntry(
                logical_path="capsule/repository.bundle",
                role="repository_bundle",
                object_key="workspace/sha256/bb/" + "b" * 64,
                sha256="b" * 64,
                size_bytes=20,
            ),
        ],
        repository=RepositoryIdentity(
            commit_sha="c" * 40,
            branch="main",
            clean=True,
            bundle_logical_path="capsule/repository.bundle",
        ),
        portable=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return draft.model_copy(
        update={"manifest_hash": workspace_manifest_hash(draft)}
    )


def test_manifest_hash_is_canonical() -> None:
    manifest = _manifest()
    validate_manifest_hash(manifest)
    dumped = manifest.model_dump()
    reordered = dict(reversed(list(dumped.items())))
    assert workspace_manifest_hash(reordered) == manifest.manifest_hash


def test_manifest_tampering_is_detected() -> None:
    manifest = _manifest()
    changed_entry = manifest.entries[0].model_copy(
        update={"size_bytes": 11}
    )
    tampered = manifest.model_copy(
        update={"entries": [changed_entry, manifest.entries[1]]}
    )
    with pytest.raises(WorkspaceIntegrityError):
        validate_manifest_hash(tampered)
```

运行：

```bash
python -m pytest -q tests/test_workspace_manifest.py
```

---

## 四十七、Git capsule 测试

> **本节类型：需要新增测试。**
>
> 新增：`tests/test_repo_capsule.py`

```python
import subprocess
from pathlib import Path

import pytest

from app.config import settings
from app.workspace.errors import WorkspaceNotPortableError
from app.workspace.repo_capsule import create_repository_capsule


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    return result.stdout.strip()


def _clean_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "Tests")
    (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
    (repo / "train.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "train.py")
    _git(repo, "commit", "-m", "initial")
    return repo


def test_capsule_preserves_commit_but_not_ignored_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(settings, "workspace_staging_root", staging)
    repo = _clean_repo(tmp_path)
    (repo / ".env").write_text("TOKEN=secret\n", encoding="utf-8")

    capsule = create_repository_capsule(
        repo_path=repo,
        destination=staging / "repo.bundle",
    )
    clone = tmp_path / "clone"
    subprocess.run(
        [
            "git",
            "clone",
            "--branch",
            "main",
            str(capsule.bundle_path),
            str(clone),
        ],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    assert _git(clone, "rev-parse", "HEAD") == capsule.identity.commit_sha
    assert not (clone / ".env").exists()


def test_dirty_repo_is_not_portable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(settings, "workspace_staging_root", staging)
    repo = _clean_repo(tmp_path)
    (repo / "train.py").write_text("VALUE = 2\n", encoding="utf-8")

    with pytest.raises(
        WorkspaceNotPortableError,
        match="repository_dirty",
    ):
        create_repository_capsule(
            repo_path=repo,
            destination=staging / "repo.bundle",
        )
```

运行：

```bash
python -m pytest -q tests/test_repo_capsule.py
```

---

## 四十八、Materializer 完整性测试

> **本节类型：需要新增测试。**
>
> 新增：`tests/test_workspace_materializer.py`

```python
from pathlib import Path

import pytest

from app.config import settings
from app.storage.local_blob_store import LocalBlobStore
from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.materializer import WorkspaceMaterializer
from app.workspace.repository import workspace_manifest_hash
from app.workspace.schemas import (
    JobRequirements,
    WorkerCapabilities,
    WorkerIdentity,
)
from app.workspace.snapshot import WorkspaceSnapshotter
from tests.test_repo_capsule import _clean_repo


class SharedLocalBlobStore(LocalBlobStore):
    """测试中用两个不同 workspace root 模拟共享对象存储。"""

    sharing_scope = "shared"


def _worker(root: Path) -> WorkerIdentity:
    return WorkerIdentity(
        worker_id="worker-b",
        worker_session_id="session-b",
        host_id="host-b",
        pool="default",
        workspace_root=str(root.resolve()),
        capabilities=WorkerCapabilities(
            execution_profile_ids=["local"],
            execution_backends=["local"],
            execution_policy_hashes={"local": "a" * 64},
            cpu_count=8,
            memory_bytes=16 * 1024**3,
            workspace_free_bytes=100 * 1024**3,
        ),
    )


def _requirements() -> JobRequirements:
    return JobRequirements(
        execution_profile_id="local",
        execution_policy_hash="a" * 64,
        execution_backend="local",
    )


def _portable_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(settings, "workspace_staging_root", staging)
    monkeypatch.setattr(settings, "workspace_max_file_bytes", 1024**3)
    monkeypatch.setattr(settings, "workspace_max_total_bytes", 2 * 1024**3)

    repo = _clean_repo(tmp_path)
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"%PDF-1.4\nfixture\n")
    blob = SharedLocalBlobStore(tmp_path / "blobs")
    snapshotter = WorkspaceSnapshotter(blob_store=blob)
    manifest = snapshotter.snapshot_initial(
        job_id="job-test",
        run_id="run-test",
        paper_path=str(paper),
        repo_path=str(repo),
        log_path=None,
        source_host_id="host-a",
        external_data=[],
    )
    assert manifest.portable is True
    return manifest, blob


def test_materialize_verifies_repo_and_paper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, blob = _portable_manifest(tmp_path, monkeypatch)
    worker_root = tmp_path / "host-b-workspaces"
    monkeypatch.setattr(settings, "worker_workspace_root", worker_root)

    materializer = WorkspaceMaterializer(blob_store=blob)
    binding = materializer.planned_binding(
        worker=_worker(worker_root),
        manifest=manifest,
        requirements=_requirements(),
        assignment_epoch=1,
        assignment_token="token-1",
    )
    ready = materializer.materialize(
        manifest=manifest,
        binding=binding,
    )

    assert ready.status == "ready"
    assert Path(ready.paper_path).read_bytes().startswith(b"%PDF")
    assert (Path(ready.repo_path) / "train.py").is_file()
    assert Path(ready.run_dir, "analysis").is_dir()


def test_corrupted_blob_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, blob = _portable_manifest(tmp_path, monkeypatch)
    paper_entry = next(
        item for item in manifest.entries if item.role == "paper"
    )
    blob_path = blob._path(paper_entry.object_key)  # noqa: SLF001
    blob_path.write_bytes(b"X" * paper_entry.size_bytes)

    worker_root = tmp_path / "host-b-workspaces"
    monkeypatch.setattr(settings, "worker_workspace_root", worker_root)
    materializer = WorkspaceMaterializer(blob_store=blob)
    binding = materializer.planned_binding(
        worker=_worker(worker_root),
        manifest=manifest,
        requirements=_requirements(),
        assignment_epoch=1,
        assignment_token="token-1",
    )
    with pytest.raises(WorkspaceIntegrityError):
        materializer.materialize(manifest=manifest, binding=binding)


def test_path_traversal_entry_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, blob = _portable_manifest(tmp_path, monkeypatch)
    first = manifest.entries[0].model_copy(
        update={"logical_path": "../escape"}
    )
    changed = manifest.model_copy(
        update={"entries": [first, *manifest.entries[1:]]}
    )
    changed = changed.model_copy(
        update={"manifest_hash": workspace_manifest_hash(changed)}
    )

    worker_root = tmp_path / "host-b-workspaces"
    monkeypatch.setattr(settings, "worker_workspace_root", worker_root)
    materializer = WorkspaceMaterializer(blob_store=blob)
    binding = materializer.planned_binding(
        worker=_worker(worker_root),
        manifest=changed,
        requirements=_requirements(),
        assignment_epoch=1,
        assignment_token="token-1",
    )
    with pytest.raises(WorkspaceIntegrityError):
        materializer.materialize(manifest=changed, binding=binding)
```

运行：

```bash
python -m pytest -q tests/test_workspace_materializer.py
```

---

## 四十九、Path rebind 与 atomic resume 测试

> **本节类型：需要新增测试。**
>
> 新增：`tests/test_workspace_rebind.py`

```python
from datetime import datetime, timezone

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.workspace.errors import WorkspaceNotPortableError
from app.workspace.rebind import build_workspace_state_update
from app.workspace.schemas import WorkspaceBinding


def _binding(
    *,
    host: str,
    epoch: int,
) -> WorkspaceBinding:
    root = f"/data/workspaces/{host}/job/epochs/{epoch}"
    now = datetime.now(timezone.utc).isoformat()
    return WorkspaceBinding(
        assignment_id=f"assignment-{host}-{epoch}",
        assignment_epoch=epoch,
        assignment_token=f"token-{host}-{epoch}",
        job_id="job-test",
        run_id="run-test",
        manifest_id=f"manifest-{epoch}",
        manifest_hash=("a" if epoch == 1 else "b") * 64,
        manifest_generation=epoch - 1,
        worker_session_id=f"session-{host}",
        host_id=host,
        workspace_root=root,
        run_dir=f"{root}/run",
        repo_path=f"{root}/repo",
        paper_path=f"{root}/source/paper.pdf",
        log_path=None,
        status="ready",
        created_at=now,
        updated_at=now,
    )


def test_rebind_known_paths_without_mutating_plain_text() -> None:
    old = _binding(host="host-a", epoch=1)
    new = _binding(host="host-b", epoch=2)
    state = {
        "workspace_binding": old.model_dump(),
        "run_dir": old.run_dir,
        "repo_path": old.repo_path,
        "paper_path": old.paper_path,
        "repo_index_path": f"{old.run_dir}/analysis/repo_index.json",
        "run_commands": [
            {
                "command": "python train.py",
                "cwd": old.repo_path,
            }
        ],
        "paper_summary": {
            "plain_text": f"example path: {old.repo_path}"
        },
    }

    update = build_workspace_state_update(
        state=state,
        new_binding=new,
    )

    assert update["repo_path"] == new.repo_path
    assert update["repo_index_path"].startswith(new.run_dir)
    assert update["run_commands"][0]["cwd"] == new.repo_path
    # 普通 LLM/Evidence 文本不在 update 中，不能被全局替换。
    assert "paper_summary" not in update


def test_command_text_with_old_absolute_path_blocks_handoff() -> None:
    old = _binding(host="host-a", epoch=1)
    new = _binding(host="host-b", epoch=2)
    state = {
        "workspace_binding": old.model_dump(),
        "run_commands": [
            {
                "command": f"python {old.repo_path}/train.py",
                "cwd": old.repo_path,
            }
        ],
    }
    with pytest.raises(
        WorkspaceNotPortableError,
        match="old_absolute_path",
    ):
        build_workspace_state_update(state=state, new_binding=new)


def test_command_update_and_resume_are_atomic() -> None:
    class State(dict):
        """StateGraph 运行时使用 dict schema，测试聚焦 Command 语义。"""

    prepare_calls: list[str] = []

    def prepare(state: dict) -> dict:
        prepare_calls.append(state["path"])
        return {"prepared": True}

    def review(state: dict) -> dict:
        del state
        return {"decision": interrupt({"kind": "review"})}

    def finish(state: dict) -> dict:
        return {
            "finished_path": state["path"],
            "finished": state["decision"] == "approved",
        }

    builder = StateGraph(dict)
    builder.add_node("prepare", prepare)
    builder.add_node("review", review)
    builder.add_node("finish", finish)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "review")
    builder.add_edge("review", "finish")
    builder.add_edge("finish", END)
    graph = builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "atomic-rebind"}}

    graph.invoke({"path": "/host-a/repo"}, config)
    final = graph.invoke(
        Command(
            resume="approved",
            update={"path": "/host-b/repo"},
        ),
        config,
    )

    assert final["finished"] is True
    assert final["finished_path"] == "/host-b/repo"
    assert prepare_calls == ["/host-a/repo"]
```

这里不要先写一个“错误的 `update_state()` 测试”再依赖当前内部 task 表现；只锁定项目
真正需要的 public behavior：前置节点只执行一次，resume decision 与新 path 同时生效。

运行：

```bash
python -m pytest -q tests/test_workspace_rebind.py
```

---

## 五十、PostgreSQL scheduling 测试

> **本节类型：需要新增集成测试。**
>
> 新增：`tests/test_workspace_scheduling.py`

```python
import pytest

from app.job_runtime.postgres_store import PostgresJobStore
from app.workspace.schemas import JobRequirements
from tests.job_store_contract import (
    POLICY_HASH,
    manifest_fixture,
    worker_fixture,
)
from app.job_runtime.schemas import JobRequest


pytestmark = pytest.mark.postgres


def _submit(
    store: PostgresJobStore,
    *,
    suffix: str,
    requirements: JobRequirements,
    source_host: str = "host-a",
) -> None:
    store.submit(
        job_id=f"job-{suffix}",
        idempotency_key=f"submit-{suffix}",
        thread_id=f"thread-{suffix}",
        run_id=f"run-{suffix}",
        run_dir=f"/data/runs/run-{suffix}",
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements,
        initial_manifest=manifest_fixture(
            suffix=suffix,
            host_id=source_host,
        ),
        max_attempts=3,
    )


def test_cpu_worker_skips_gpu_job_and_gpu_worker_claims(
    postgres_engine,
) -> None:
    store = PostgresJobStore(postgres_engine)
    requirements = JobRequirements(
        worker_pool="gpu",
        execution_profile_id="local",
        execution_policy_hash=POLICY_HASH,
        execution_backend="local",
        min_gpu_count=1,
        cuda_major=11,
    )
    _submit(
        store,
        suffix="gpu",
        requirements=requirements,
        source_host="host-a",
    )

    cpu = worker_fixture(
        worker_id="cpu",
        session_id="cpu-session",
        host_id="host-a",
        pool="gpu",
    )
    gpu = worker_fixture(
        worker_id="gpu",
        session_id="gpu-session",
        host_id="host-a",
        pool="gpu",
        gpu_count=1,
        cuda_major=11,
    )
    store.register_worker(worker=cpu, lease_seconds=30)
    store.register_worker(worker=gpu, lease_seconds=30)

    assert store.claim_next(worker=cpu, lease_seconds=30) is None
    claim = store.claim_next(worker=gpu, lease_seconds=30)
    assert claim is not None
    assert claim.job.job_id == "job-gpu"


def test_host_affinity_blocks_other_host(
    postgres_engine,
) -> None:
    store = PostgresJobStore(postgres_engine)
    requirements = JobRequirements(
        execution_profile_id="local",
        execution_policy_hash=POLICY_HASH,
        execution_backend="local",
    )
    _submit(
        store,
        suffix="affinity",
        requirements=requirements,
        source_host="host-a",
    )
    host_b = worker_fixture(
        worker_id="worker-b",
        session_id="session-b",
        host_id="host-b",
    )
    host_a = worker_fixture(
        worker_id="worker-a",
        session_id="session-a",
        host_id="host-a",
    )
    store.register_worker(worker=host_b, lease_seconds=30)
    store.register_worker(worker=host_a, lease_seconds=30)

    assert store.claim_next(worker=host_b, lease_seconds=30) is None
    assert store.claim_next(worker=host_a, lease_seconds=30) is not None


def test_policy_hash_mismatch_is_not_claimed(
    postgres_engine,
) -> None:
    store = PostgresJobStore(postgres_engine)
    requirements = JobRequirements(
        execution_profile_id="local",
        execution_policy_hash="f" * 64,
        execution_backend="local",
    )
    _submit(
        store,
        suffix="policy",
        requirements=requirements,
        source_host="host-a",
    )
    worker = worker_fixture(host_id="host-a")
    store.register_worker(worker=worker, lease_seconds=30)
    assert store.claim_next(worker=worker, lease_seconds=30) is None
```

注意第二个测试使用的是 `portable=false` contract manifest，所以 Store submit 必须自动把
`affinity_host_id` 设置成 `source_host_id`。

运行：

```bash
export TEST_DATABASE_URL="${DATABASE_URL}"
python -m pytest -q -m postgres tests/test_workspace_scheduling.py
```

---

## 五十一、Workspace fencing 测试

> **本节类型：需要新增集成测试。**
>
> 新增：`tests/test_workspace_fencing.py`

```python
import pytest

from app.job_runtime.errors import LeaseLostError
from app.job_runtime.postgres_store import PostgresJobStore
from app.workspace.repository import workspace_manifest_hash
from tests.job_store_contract import submit_fixture, worker_fixture


pytestmark = pytest.mark.postgres


def test_old_claim_cannot_publish_new_manifest(
    postgres_engine,
) -> None:
    store = PostgresJobStore(postgres_engine)
    submit_fixture(store)
    worker = worker_fixture()
    store.register_worker(worker=worker, lease_seconds=30)
    claim = store.claim_next(worker=worker, lease_seconds=0)
    assert claim is not None

    parent = store.get_workspace_manifest(
        claim.job.workspace_manifest_id
    )
    token = claim.job.workspace_assignment_token
    assert token is not None

    store.begin_workspace_assignment(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        worker=worker,
        manifest=parent,
        assignment_token=token,
        workspace_root="/data/workspaces/host-a/job-1",
        run_dir="/data/runs/run-1",
        repo_path="/data/repo",
        paper_path="/data/paper.pdf",
        log_path=None,
    )
    store.mark_workspace_ready(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        assignment_token=token,
    )

    store.requeue_expired(
        job_id=claim.job.job_id,
        expired_claim_token=claim.claim_token,
        detail="test lease expiry",
        actor="test",
    )

    draft = parent.model_copy(
        update={
            "manifest_id": "manifest-stale",
            "manifest_hash": "",
            "generation": parent.generation + 1,
            "parent_manifest_id": parent.manifest_id,
        }
    )
    stale_manifest = draft.model_copy(
        update={"manifest_hash": workspace_manifest_hash(draft)}
    )

    with pytest.raises(LeaseLostError):
        store.seal_workspace_manifest(
            job_id=claim.job.job_id,
            claim_token=claim.claim_token,
            assignment_token=token,
            manifest=stale_manifest,
            affinity_host_id="host-a",
            actor="old-worker",
        )
```

运行：

```bash
export TEST_DATABASE_URL="${DATABASE_URL}"
python -m pytest -q -m postgres tests/test_workspace_fencing.py
```

---

## 五十二、双 root 跨 host handoff 测试

> **本节类型：需要新增测试。**
>
> 新增：`tests/test_cross_host_workspace_handoff.py`

该测试不调用 Provider，也不需要真实 GPU。它验证：

```text
host-a workspace root != host-b workspace root
prepare 节点只执行一次
run Artifact 被带到 host-b
repo commit 相同
resume 使用 host-b path
```

完整测试：

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.config import settings
from app.schemas import ArtifactRecord
from app.storage.local_blob_store import LocalBlobStore
from app.tools.artifact_tools import sha256_file
from app.workspace.materializer import WorkspaceMaterializer
from app.workspace.rebind import build_workspace_state_update
from app.workspace.schemas import (
    JobRequirements,
    WorkerCapabilities,
    WorkerIdentity,
)
from app.workspace.snapshot import WorkspaceSnapshotter
from tests.test_repo_capsule import _clean_repo


class SharedLocalBlobStore(LocalBlobStore):
    sharing_scope = "shared"


class HandoffState(TypedDict, total=False):
    run_dir: str
    repo_path: str
    paper_path: str
    workspace_binding: dict[str, Any]
    workspace_assignment_epoch: int
    workspace_manifest_id: str
    workspace_manifest_hash: str
    artifact_records: list[dict[str, Any]]
    run_commands: list[dict[str, Any]]
    prepared: int
    decision: str
    finished: bool
    finished_repo_path: str


def _worker(host: str, root: Path) -> WorkerIdentity:
    return WorkerIdentity(
        worker_id=f"worker-{host}",
        worker_session_id=f"session-{host}",
        host_id=host,
        pool="default",
        workspace_root=str(root.resolve()),
        capabilities=WorkerCapabilities(
            execution_profile_ids=["local"],
            execution_backends=["local"],
            execution_policy_hashes={"local": "a" * 64},
            cpu_count=8,
            memory_bytes=16 * 1024**3,
            workspace_free_bytes=100 * 1024**3,
        ),
    )


def _requirements() -> JobRequirements:
    return JobRequirements(
        execution_profile_id="local",
        execution_policy_hash="a" * 64,
        execution_backend="local",
    )


def test_safe_interrupt_handoff_between_distinct_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(settings, "workspace_staging_root", staging)
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "legacy-runs")
    monkeypatch.setattr(settings, "workspace_max_file_bytes", 1024**3)
    monkeypatch.setattr(settings, "workspace_max_total_bytes", 2 * 1024**3)

    source_repo = _clean_repo(tmp_path)
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"%PDF-1.4\nphase26\n")
    blob = SharedLocalBlobStore(tmp_path / "shared-blobs")
    snapshotter = WorkspaceSnapshotter(blob_store=blob)
    initial_manifest = snapshotter.snapshot_initial(
        job_id="job-handoff",
        run_id="run-handoff",
        paper_path=str(paper),
        repo_path=str(source_repo),
        log_path=None,
        source_host_id="host-a",
        external_data=[],
    )
    assert initial_manifest.portable is True

    host_a_root = tmp_path / "host-a-workspaces"
    monkeypatch.setattr(settings, "worker_workspace_root", host_a_root)
    materializer_a = WorkspaceMaterializer(blob_store=blob)
    binding_a = materializer_a.planned_binding(
        worker=_worker("host-a", host_a_root),
        manifest=initial_manifest,
        requirements=_requirements(),
        assignment_epoch=1,
        assignment_token="token-a",
    )
    binding_a = materializer_a.materialize(
        manifest=initial_manifest,
        binding=binding_a,
    )

    prepare_calls: list[str] = []

    def prepare(state: HandoffState) -> dict[str, Any]:
        prepare_calls.append(state["repo_path"])
        output = Path(state["run_dir"]) / "analysis" / "prepared.txt"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("prepared once\n", encoding="utf-8")
        relative = output.relative_to(Path(state["run_dir"])).as_posix()
        record = ArtifactRecord(
            artifact_id="artifact-prepared",
            run_id="run-handoff",
            layer="analysis",
            relative_path=relative,
            absolute_path=str(output.resolve()),
            media_type="text/plain",
            sha256=sha256_file(output),
            size_bytes=output.stat().st_size,
            producer_node="prepare",
            created_at="2026-07-31T00:00:00+00:00",
        )
        return {
            "prepared": state.get("prepared", 0) + 1,
            "artifact_records": [record.model_dump()],
            "run_commands": [
                {
                    "command": "python train.py",
                    "cwd": state["repo_path"],
                }
            ],
        }

    def review(state: HandoffState) -> dict[str, Any]:
        del state
        return {"decision": str(interrupt({"kind": "command_selection"}))}

    def finish(state: HandoffState) -> dict[str, Any]:
        assert Path(
            state["run_dir"],
            "analysis",
            "prepared.txt",
        ).read_text(encoding="utf-8") == "prepared once\n"
        return {
            "finished": state["decision"] == "approved",
            "finished_repo_path": state["repo_path"],
        }

    builder = StateGraph(HandoffState)
    builder.add_node("prepare", prepare)
    builder.add_node("review", review)
    builder.add_node("finish", finish)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "review")
    builder.add_edge("review", "finish")
    builder.add_edge("finish", END)
    graph = builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "phase26-handoff"}}
    first = graph.invoke(
        {
            "run_dir": binding_a.run_dir,
            "repo_path": binding_a.repo_path,
            "paper_path": binding_a.paper_path,
            "workspace_binding": binding_a.model_dump(),
            "workspace_assignment_epoch": 1,
            "workspace_manifest_id": initial_manifest.manifest_id,
            "workspace_manifest_hash": initial_manifest.manifest_hash,
            "artifact_records": [],
        },
        config,
    )
    assert "__interrupt__" in first
    state_a = dict(graph.get_state(config).values)

    sealed = snapshotter.seal(
        job_id="job-handoff",
        run_id="run-handoff",
        run_dir=binding_a.run_dir,
        repo_path=binding_a.repo_path,
        paper_path=binding_a.paper_path,
        log_path=None,
        parent=initial_manifest,
        source_host_id="host-a",
        source_worker_session_id="session-host-a",
        artifact_records=state_a["artifact_records"],
        external_data=[],
        blocked_reasons=[],
    )
    assert sealed.portable is True

    host_b_root = tmp_path / "host-b-workspaces"
    assert host_b_root != host_a_root
    monkeypatch.setattr(settings, "worker_workspace_root", host_b_root)
    materializer_b = WorkspaceMaterializer(blob_store=blob)
    binding_b = materializer_b.planned_binding(
        worker=_worker("host-b", host_b_root),
        manifest=sealed,
        requirements=_requirements(),
        assignment_epoch=2,
        assignment_token="token-b",
    )
    binding_b = materializer_b.materialize(
        manifest=sealed,
        binding=binding_b,
    )
    assert binding_b.repo_path != binding_a.repo_path
    assert binding_b.run_dir != binding_a.run_dir

    update = build_workspace_state_update(
        state=state_a,
        new_binding=binding_b,
    )
    final = graph.invoke(
        Command(resume="approved", update=update),
        config,
    )

    assert final["finished"] is True
    assert final["finished_repo_path"] == binding_b.repo_path
    assert prepare_calls == [binding_a.repo_path]
    assert Path(
        binding_b.run_dir,
        "analysis",
        "prepared.txt",
    ).is_file()
```

运行：

```bash
python -m pytest -q tests/test_cross_host_workspace_handoff.py
```

这个测试仍是在一台机器上模拟两个 host，但已经故意使用不同 root；它证明代码不依赖
共享 POSIX workspace。真正两主机验收见第六十节。

---

## 五十三、本地 Workspace GC

> **本节类型：需要新增和修改代码。**
>
> 新增：`app/workspace/gc.py`
>
> 修改：`app/job_runtime/postgres_store.py`、`app/main.py`

### 53.1 何时把旧 assignment 标记 released

`mark_workspace_ready()` 成功后，在同一 transaction 中把同 Job、较小 epoch 的 `ready`
assignment 改为 `released`。此时新 epoch 已完整物化，旧 epoch 才不再是当前恢复依赖。

Job 进入 `succeeded/failed/cancelled` 终态时，也把当前 `ready` assignment 标记
`released`。`waiting_for_input` 的 current assignment 不能释放，因为 non-portable
manifest 可能必须原地复用。

### 53.2 新增 `app/workspace/gc.py`

```python
from __future__ import annotations

import shutil
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.job_runtime.ports import JobStore
from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.schemas import WorkspaceBinding


_SAFE_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _safe_component(value: str, *, field: str) -> str:
    if (
        value in {".", ".."}
        or not _SAFE_PATH_COMPONENT.fullmatch(value)
    ):
        raise WorkspaceIntegrityError(
            f"{field} 不能作为受管目录名：{value!r}"
        )
    return value


def _expected_epoch_root(binding: WorkspaceBinding) -> Path:
    root = settings.worker_workspace_root.resolve()
    job_component = _safe_component(
        binding.job_id,
        field="job_id",
    )
    epoch_component = f"{binding.assignment_epoch:08d}"
    expected = (
        root
        / "jobs"
        / job_component
        / "epochs"
        / epoch_component
    )
    resolved = expected.resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise WorkspaceIntegrityError("GC 目标逃逸 worker root")
    return expected


def _reject_symlink_chain(path: Path, root: Path) -> None:
    current = path
    while current != root:
        if current.is_symlink():
            raise WorkspaceIntegrityError(
                f"GC 路径链包含 symlink：{current}"
            )
        if root not in current.parents:
            raise WorkspaceIntegrityError("GC 路径逃逸 worker root")
        current = current.parent


class WorkspaceGarbageCollector:
    def __init__(self, *, store: JobStore, host_id: str):
        self.store = store
        self.host_id = host_id

    def collect(
        self,
        *,
        dry_run: bool,
        limit: int = 100,
    ) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.workspace_gc_min_age_seconds
        )
        candidates = self.store.list_workspace_gc_candidates(
            host_id=self.host_id,
            older_than=cutoff.isoformat(),
            limit=limit,
        )
        removed: list[str] = []
        skipped: list[dict[str, str]] = []

        for binding in candidates:
            expected = _expected_epoch_root(binding)
            declared = Path(binding.workspace_root)
            if declared != expected:
                skipped.append(
                    {
                        "assignment_id": binding.assignment_id,
                        "reason": "workspace_root_mismatch",
                    }
                )
                continue

            _reject_symlink_chain(expected, settings.worker_workspace_root.resolve())
            marker = expected / ".workspace-binding.json"
            if expected.exists():
                if not marker.is_file() or marker.is_symlink():
                    skipped.append(
                        {
                            "assignment_id": binding.assignment_id,
                            "reason": "binding_marker_missing",
                        }
                    )
                    continue
                local = WorkspaceBinding.model_validate_json(
                    marker.read_text(encoding="utf-8")
                )
                if (
                    local.assignment_id != binding.assignment_id
                    or local.assignment_token != binding.assignment_token
                    or local.manifest_hash != binding.manifest_hash
                ):
                    skipped.append(
                        {
                            "assignment_id": binding.assignment_id,
                            "reason": "binding_marker_mismatch",
                        }
                    )
                    continue

            if dry_run:
                removed.append(binding.assignment_id)
                continue

            if expected.exists():
                shutil.rmtree(expected)
            self.store.mark_workspace_garbage_collected(
                assignment_id=binding.assignment_id,
                assignment_token=binding.assignment_token,
                host_id=self.host_id,
            )
            removed.append(binding.assignment_id)

        return {
            "dry_run": dry_run,
            "candidate_count": len(candidates),
            "removed_or_planned": removed,
            "skipped": skipped,
        }
```

### 53.3 Store GC 查询

只返回：

```sql
host_id = :current_host
status IN ('released', 'failed')
updated_at < :cutoff
```

`mark_workspace_garbage_collected()` 要用：

```text
assignment_id + assignment_token + host_id + status IN (released, failed)
```

做 compare-and-set。不要根据目录 mtime 自行删除数据库仍标记 `ready` 的 workspace。

### 53.4 CLI

```python
@app.command("gc-workspaces")
def gc_workspaces_command(
    execute: bool = typer.Option(False, "--execute"),
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
):
    service = build_job_service()
    collector = WorkspaceGarbageCollector(
        store=service.store,
        host_id=settings.worker_host_id,
    )
    print(collector.collect(dry_run=not execute, limit=limit))
```

默认必须 dry-run。共享 S3/MinIO Blob 不在这个命令的删除范围内。

---

## 五十四、GC 测试

> **本节类型：需要新增测试。**
>
> 新增：`tests/test_workspace_gc.py`

```python
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.config import settings
from app.workspace.gc import WorkspaceGarbageCollector
from tests.test_workspace_rebind import _binding


class FakeGcStore:
    def __init__(self, binding):
        self.binding = binding
        self.marked: list[str] = []

    def list_workspace_gc_candidates(
        self,
        *,
        host_id: str,
        older_than: str,
        limit: int,
    ):
        del older_than, limit
        return [self.binding] if self.binding.host_id == host_id else []

    def mark_workspace_garbage_collected(
        self,
        *,
        assignment_id: str,
        assignment_token: str,
        host_id: str,
    ):
        assert assignment_token == self.binding.assignment_token
        assert host_id == self.binding.host_id
        self.marked.append(assignment_id)
        return self.binding.model_copy(
            update={
                "status": "garbage_collected",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )


def test_gc_is_dry_run_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "worker"
    monkeypatch.setattr(settings, "worker_workspace_root", root)
    monkeypatch.setattr(settings, "workspace_gc_min_age_seconds", 0)
    binding = _binding(host="host-a", epoch=1).model_copy(
        update={
            "workspace_root": str(
                root / "jobs/job-test/epochs/00000001"
            ),
            "status": "released",
        }
    )
    epoch = Path(binding.workspace_root)
    epoch.mkdir(parents=True)
    (epoch / ".workspace-binding.json").write_text(
        binding.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    store = FakeGcStore(binding)
    report = WorkspaceGarbageCollector(
        store=store,
        host_id="host-a",
    ).collect(dry_run=True)

    assert report["removed_or_planned"] == [binding.assignment_id]
    assert epoch.exists()
    assert store.marked == []


def test_gc_deletes_only_matching_released_epoch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "worker"
    monkeypatch.setattr(settings, "worker_workspace_root", root)
    monkeypatch.setattr(settings, "workspace_gc_min_age_seconds", 0)
    binding = _binding(host="host-a", epoch=1).model_copy(
        update={
            "workspace_root": str(
                root / "jobs/job-test/epochs/00000001"
            ),
            "status": "released",
        }
    )
    epoch = Path(binding.workspace_root)
    epoch.mkdir(parents=True)
    (epoch / ".workspace-binding.json").write_text(
        binding.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    store = FakeGcStore(binding)
    WorkspaceGarbageCollector(
        store=store,
        host_id="host-a",
    ).collect(dry_run=False)

    assert not epoch.exists()
    assert store.marked == [binding.assignment_id]
```

运行：

```bash
python -m pytest -q tests/test_workspace_gc.py
```

---

## 五十五、跨 host 恢复前重新检查外部数据

> **本节类型：需要修改代码和测试。**
>
> 修改：`app/workspace/capabilities.py`、`app/workspace/manager.py`、
> `app/job_runtime/graph_runner.py`、`app/state.py`、
> `tests/test_worker_capabilities.py`

数据集不能因为 label 匹配就直接假设可用。增加：

```python
from app.workspace.schemas import WorkspaceManifest


def verify_external_data_mounts(
    *,
    manifest: WorkspaceManifest,
    worker: WorkerIdentity,
) -> dict[str, str]:
    """返回 label -> host-local mount；不遍历或上传数据集。"""

    resolved: dict[str, str] = {}
    for reference in manifest.external_data:
        label = reference.required_worker_label
        raw_mount = worker.capabilities.dataset_mounts.get(label)
        if raw_mount is None:
            raise WorkerCapabilityError(
                f"dataset mount 未配置：{label}"
            )
        mount = Path(raw_mount).resolve()
        if not mount.is_dir():
            raise WorkerCapabilityError(
                f"dataset mount 不存在：{label}"
            )

        if reference.fingerprint:
            marker = mount / ".agent-dataset-fingerprint"
            if not marker.is_file():
                raise WorkerCapabilityError(
                    f"dataset fingerprint marker 缺失：{label}"
                )
            actual = marker.read_text(encoding="utf-8").strip()
            if actual != reference.fingerprint:
                raise WorkerCapabilityError(
                    f"dataset fingerprint 不匹配：{label}"
                )
        resolved[label] = str(mount)
    return resolved
```

`WorkspaceManager.prepare()` 在 `planned_binding()` 前调用：

```python
dataset_mounts = verify_external_data_mounts(
    manifest=manifest,
    worker=claim.worker,
)
```

`JobClaim` 增加仅进程内字段：

```python
dataset_mounts: dict[str, str] = Field(default_factory=dict)
```

prepare return 时写入：

```python
return claim.model_copy(
    update={
        "workspace_binding": ready,
        "dataset_mounts": dataset_mounts,
    }
)
```

Graph initial state 与 rebind update 分别增加：

```python
initial_state["dataset_mounts"] = dict(claim.dataset_mounts)
workspace_update["dataset_mounts"] = dict(claim.dataset_mounts)
```

`ReproductionState` 增加：

```python
dataset_mounts: dict[str, str]
```

这些路径只进入内部 checkpoint/run manifest 的受控运行身份，不进入 Public Worker API。
训练 command 仍需要用户在 command selection 中确认具体参数；Agent 不根据 label 自动拼接
任意命令。

测试增加：

```python
def test_dataset_label_without_real_mount_is_rejected(
    tmp_path,
) -> None:
    from datetime import datetime, timezone

    import pytest

    from app.workspace.capabilities import verify_external_data_mounts
    from app.workspace.errors import WorkerCapabilityError
    from app.workspace.repository import workspace_manifest_hash
    from app.workspace.schemas import (
        ExternalDataReference,
        RepositoryIdentity,
        WorkspaceManifest,
    )

    worker = _worker(labels=["dataset:pstnet-ready"])
    worker = worker.model_copy(
        update={
            "capabilities": worker.capabilities.model_copy(
                update={
                    "dataset_mounts": {
                        "dataset:pstnet-ready": str(
                            tmp_path / "missing"
                        )
                    }
                }
            )
        }
    )
    draft = WorkspaceManifest(
        manifest_id="wm-data",
        manifest_hash="",
        job_id="job-data",
        run_id="run-data",
        generation=0,
        source_host_id="host-a",
        entries=[],
        repository=RepositoryIdentity(
            commit_sha="a" * 40,
            branch="main",
            clean=True,
            bundle_logical_path="capsule/repository.bundle",
        ),
        external_data=[
            ExternalDataReference(
                name="pstnet",
                uri="dataset://pstnet",
                required_worker_label="dataset:pstnet-ready",
            )
        ],
        portable=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    manifest = draft.model_copy(
        update={"manifest_hash": workspace_manifest_hash(draft)}
    )

    with pytest.raises(
        WorkerCapabilityError,
        match="mount 不存在",
    ):
        verify_external_data_mounts(
            manifest=manifest,
            worker=worker,
        )
```

对于超大数据集，不要递归计算全量 SHA-256。使用数据准备流程生成的稳定 marker，例如：

```text
dataset release id + split manifest hash + preprocessing version
```

---

## 五十六、Preflight 必须在 handoff 后重新运行

> **本节类型：需要修改或确认 Graph 路由。**
>
> 修改/检查：`app/graph.py`、`app/nodes/preflight_check_node.py`

如果 handoff 发生在 `command_selection`，正常路由应为：

```text
command_selection resume
    -> action_builder
    -> risk_check / human_review
    -> preflight_check
    -> executor
```

这样 Worker B 会自然重新执行 preflight。检查编译图，不要为了“恢复更快”从 checkpoint
直接 goto executor。

Preflight 报告增加：

```text
workspace_assignment_epoch
workspace_manifest_id/hash
worker host/session（公开报告只保留 host，不保留 token）
materialized repo commit
effective execution policy hash
dataset mount labels/fingerprint status
disk free bytes
GPU/CUDA capability summary
```

如果 checkpoint 已经越过 preflight 才发生 running crash，本阶段不自动跨 host requeue，
因此不会复用旧 host 的 preflight 结果执行新 host command。

---

## 五十七、更新旧测试与 fake

> **本节类型：需要修改测试。**

接口变化会影响以下旧测试：

```text
tests/job_store_contract.py
tests/test_job_store.py
tests/test_sqlite_job_store_contract.py
tests/test_postgres_job_store.py
tests/test_postgres_distributed_claim.py
tests/test_job_worker.py
tests/test_worker_artifact_publication.py
tests/test_job_graph_runner.py
tests/test_job_process_reconcile.py
tests/test_interaction_api.py
tests/test_interaction_artifacts.py
tests/test_job_cli.py
tests/test_artifact_publisher.py
```

统一修改原则：

```text
旧 worker_id 字符串
    -> WorkerIdentity + register_worker

旧 JobService(store)
    -> JobService(store, workspace_snapshotter=fake)

旧 JobWorker(...)
    -> 注入 FakeWorkspaceManager 或真实临时 manager

旧 Graph claim
    -> workspace_binding.status=ready

旧 ArtifactPublisher.publish
    -> 可省略 binding 保持 legacy；Phase 26 测试显式传 binding
```

一个最小 Fake WorkspaceManager：

```python
class PassThroughWorkspaceManager:
    def __init__(self, binding):
        self.binding = binding
        self.seal_calls = 0

    def prepare(self, claim):
        return claim.model_copy(
            update={"workspace_binding": self.binding}
        )

    def seal_waiting(self, *, claim, outcome):
        del claim, outcome
        self.seal_calls += 1
        return self.binding
```

Fake 不应返回 `MagicMock` 作为 binding，因为 Pydantic/path 代码可能把 mock 静默转成奇怪
字符串。使用真实 `WorkspaceBinding` fixture。

### 57.1 修复无 `TEST_DATABASE_URL` 时 checkpoint 测试未 skip

当前部分 Postgres checkpoint tests 不接收 `postgres_engine` fixture，而是在测试体内直接
读取 `os.environ["TEST_DATABASE_URL"]`，所以未配置变量时会 `KeyError` 而非 skip。

在 `tests/conftest.py` 增加 autouse marker guard：

```python
@pytest.fixture(autouse=True)
def require_postgres_url_for_marked_test(
    request: pytest.FixtureRequest,
):
    if (
        request.node.get_closest_marker("postgres") is not None
        and not os.getenv("TEST_DATABASE_URL")
    ):
        pytest.skip("未设置 TEST_DATABASE_URL")
```

这不会掩盖配置了 URL 后的真实失败。

---

## 五十八、自动测试顺序

> **本节类型：测试命令，不修改项目代码。**

### 58.1 先跑纯离线 Phase 26 测试

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent

python -m pytest -q \
  tests/test_worker_capabilities.py \
  tests/test_workspace_manifest.py \
  tests/test_repo_capsule.py \
  tests/test_workspace_materializer.py \
  tests/test_workspace_rebind.py \
  tests/test_cross_host_workspace_handoff.py \
  tests/test_workspace_gc.py
```

### 58.2 跑 PostgreSQL 集成测试

```bash
set -a
source .env
set +a
export TEST_DATABASE_URL="${DATABASE_URL}"

python -m pytest -q -m postgres \
  tests/test_workspace_scheduling.py \
  tests/test_workspace_fencing.py \
  tests/test_postgres_job_store.py \
  tests/test_postgres_distributed_claim.py \
  tests/test_postgres_artifact_repository.py \
  tests/test_postgres_checkpoint.py
```

`tests/conftest.py` 当前会对 `TEST_DATABASE_URL` 执行 `metadata.drop_all()`；测试数据库必须
与开发/生产数据库隔离。建议数据库名包含 `_test`，并在 fixture 中检查数据库名后再
允许 drop。

### 58.3 跑 Phase 22-25 回归

```bash
python -m pytest -q \
  tests/test_job_store.py \
  tests/test_sqlite_job_store_contract.py \
  tests/test_job_heartbeat.py \
  tests/test_job_worker.py \
  tests/test_job_graph_runner.py \
  tests/test_job_durable_resume.py \
  tests/test_job_process_reconcile.py \
  tests/test_interaction_api.py \
  tests/test_interaction_policy.py \
  tests/test_interaction_sse.py \
  tests/test_artifact_publisher.py \
  tests/test_artifact_storage_api.py \
  tests/test_worker_artifact_publication.py
```

### 58.4 最后跑全量测试

```bash
python -m pytest -q
```

没有 `TEST_DATABASE_URL` 时 Postgres tests 应显示 `skipped`，不能显示 `KeyError`。

---

## 五十九、静态检查与 migration 检查

> **本节类型：验证命令，不修改项目代码。**

```bash
python -m compileall -q app tests
python -m ruff check app tests
python -m alembic check
```

检查 migration metadata 是否遗漏：

```bash
python -m app.main migrate-database
python -m app.main check-database
python -m app.main check-artifact-storage
```

`check-artifact-storage` 输出应增加：

```text
sharing_scope=shared
```

如果是 `host`，可以跑本地单元测试，但不能进入真正跨主机手工验收。

---

## 六十、PSTNet 手工验收：同机双 root 模拟

> **本节类型：手工验收，不修改项目代码。**

本节论文与仓库：

```text
论文：
/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf

仓库：
/data/tianshaoqi24/PST-Convolution-main/
```

所有新增目录仍位于 `/data/tianshaoqi24/` 下，不使用系统 `/tmp`。

### 60.1 检查源输入

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent

test -f "pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf"
test -d /data/tianshaoqi24/PST-Convolution-main/.git
git -C /data/tianshaoqi24/PST-Convolution-main status --porcelain=v1 --untracked-files=all
git -C /data/tianshaoqi24/PST-Convolution-main rev-parse HEAD
git -C /data/tianshaoqi24/PST-Convolution-main symbolic-ref --short HEAD
```

跨 host portable 验收要求 `status --porcelain` 没有输出。

如果有输出：

```text
不要自动 git reset --hard
不要自动 git clean
不要自动 stash
```

先确认修改是否应该保留；有意修改应由你自己审查并 commit。若保持 dirty，本阶段正确
结果是 `portable=false + affinity_host_id=submit host`，只能验收 fail-closed 分支。

### 60.2 确认 PostgreSQL 与 S3/MinIO 为共享后端

`.env` 至少包含：

```dotenv
JOB_STORE_BACKEND=postgresql
CHECKPOINT_BACKEND=postgresql
ARTIFACT_BLOB_BACKEND=s3
DATABASE_URL=postgresql+psycopg://...
ARTIFACT_S3_ENDPOINT_URL=http://127.0.0.1:9000
ARTIFACT_S3_BUCKET=paper-reproduction-artifacts
ARTIFACT_S3_PREFIX=copilot
```

执行：

```bash
set -a
source .env
set +a

python -m app.main migrate-database
python -m app.main check-database
python -m app.main check-artifact-storage
```

期望：

```text
Job backend              postgresql
Checkpoint backend       postgresql
Artifact backend         s3
Artifact sharing scope   shared
```

如果 selected backend 是 `local`，停止本节；双 root 可能在同一磁盘上“碰巧可见”，不能
证明跨主机数据平面。

### 60.3 准备 Host A/B capability 文件

创建但不要提交：

```text
/data/tianshaoqi24/agent/paper_reproduction_copilot/config/worker_capabilities.host-a.json
/data/tianshaoqi24/agent/paper_reproduction_copilot/config/worker_capabilities.host-b.json
```

两者都要声明相同 profile policy 所需能力。若暂时只测试分析到 command selection，可
使用无 GPU requirement 的测试 profile；若 profile 要求 GPU，capability 必须与真实
机器一致。

数据集 label 示例：

```json
{
  "labels": ["dataset:pstnet-ready"],
  "dataset_mounts": {
    "dataset:pstnet-ready": "/data/tianshaoqi24/datasets/pstnet"
  }
}
```

不要为不存在的目录虚构 label。若当前阶段还没有准备数据集，应从 profile 中暂时移除
该 required label，并只验收到 preflight 之前；不能把训练就绪写成通过。

### 60.4 准备两个 host-local Execution Profile 文件

建议创建：

```text
config/execution_profiles.host-a.json
config/execution_profiles.host-b.json
```

两个文件的安全策略、budget、backend、required labels 必须相同；只允许以下 host-local
路径不同：

```text
workspace_root
artifact_root
conda_executable
conda_prefix
```

Host A：

```json
{
  "profile_id": "pstnet-phase26",
  "backend": "local",
  "workspace_root": "/data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-a",
  "artifact_root": "/data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-a",
  "worker_pool": "gpu",
  "min_workspace_free_bytes": 1073741824,
  "min_gpu_count": 0,
  "required_worker_labels": [],
  "network_policy": "deny",
  "enforcement_mode": "best_effort",
  "allowed_programs": ["python", "python3", "pytest"],
  "writable_roots": [
    "/data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-a"
  ]
}
```

该片段只展示 Phase 26 相关字段，实际文件还要保留 Phase 16 的完整 budget、环境变量等
配置。Host B 把路径改为 `host-b`，其余安全字段保持一致。

先创建两个 root：

```bash
mkdir -p \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-a \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-b \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/workspace_staging \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_inputs
```

### 60.5 以 Host A 身份提交 Job

当前 source repo 位于这台机器，所以 submission host 使用 `host-a`：

```bash
export WORKER_HOST_ID=host-a
export WORKER_POOL=gpu
export WORKER_WORKSPACE_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-a
export WORKER_CAPABILITIES_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/config/worker_capabilities.host-a.json
export EXECUTION_PROFILES_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/config/execution_profiles.host-a.json
export WORKSPACE_STAGING_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/workspace_staging

python -m app.main submit-job \
  "pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf" \
  /data/tianshaoqi24/PST-Convolution-main/ \
  --thread-id phase26-pstnet-001 \
  --execution-profile pstnet-phase26 \
  --idempotency-key submit-phase26-pstnet-001
```

保存输出中的真实 `job_id`：

```bash
export JOB_ID='job_这里替换成真实值'
```

检查初始 manifest：

```bash
python -m app.main show-job "$JOB_ID"
python -m app.main show-workspace "$JOB_ID"
python -m app.main explain-scheduling "$JOB_ID"
```

clean repo + shared S3 的期望：

```text
generation=0
portable=true
blocked_reasons=[]
affinity_host_id=None
repo_clean=true
```

如果 `portable=false`，先查看 `blocked_reasons`，不要继续假装跨 host。

### 60.6 Worker A 运行到 command selection interrupt

```bash
python -m app.main run-worker \
  --worker-id phase26-worker-a \
  --once
```

检查：

```bash
python -m app.main show-job "$JOB_ID"
python -m app.main show-job-events "$JOB_ID" --limit 200
python -m app.main show-workspace "$JOB_ID"
python -m app.main list-workers --include-expired
```

期望 Job：

```text
status=waiting_for_input
interrupt_nodes 包含 command_selection
workspace manifest generation=1
portable=true
affinity_host_id=None
binding host_id=host-a
assignment_epoch=1
```

事件顺序至少包含：

```text
job_claimed
workspace_materializing
workspace_ready
workspace_sealed
job_waiting_for_input
```

检查 Host A 本地 epoch：

```bash
find \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-a/jobs \
  -maxdepth 5 -type f \
  | sort \
  | head -n 80
```

应该有 `.workspace-binding.json`、materialized repo、paper 和 run Artifact。不要输出 marker
全文，因为其中包含 assignment token。

### 60.7 准备 command selection decision

从 `show-job` 当前 interrupt preview 读取真实：

```text
run_commands
run_commands_hash
```

创建：

```text
/data/tianshaoqi24/agent/paper_reproduction_copilot/manual_inputs/phase26-command-selection.json
```

内容：

```json
{
  "run_commands_hash": "替换成当前 interrupt 的真实 hash",
  "selected_index": 0,
  "edits": []
}
```

确认索引 `0` 对应的命令是你愿意进入后续审批的命令。该 decision 只选择命令，不等于
批准训练执行。

排队恢复：

```bash
python -m app.main resume-job "$JOB_ID" \
  --expected-node command_selection \
  --input /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_inputs/phase26-command-selection.json \
  --idempotency-key resume-phase26-command-selection-001
```

期望 Job 重新变成 `queued`。

### 60.8 切换成 Host B 并恢复

同机模拟只切换受信任 host 配置和本地 root：

```bash
export WORKER_HOST_ID=host-b
export WORKER_POOL=gpu
export WORKER_WORKSPACE_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-b
export WORKER_CAPABILITIES_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/config/worker_capabilities.host-b.json
export EXECUTION_PROFILES_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/config/execution_profiles.host-b.json

python -m app.main explain-scheduling "$JOB_ID"
python -m app.main run-worker \
  --worker-id phase26-worker-b \
  --once
```

Worker B 正常情况下会继续到下一个审批 interrupt，例如 `human_review`。检查：

```bash
python -m app.main show-job "$JOB_ID"
python -m app.main show-job-events "$JOB_ID" --limit 300
python -m app.main show-workspace "$JOB_ID"
python -m app.main show-state --thread-id phase26-pstnet-001
```

关键期望：

```text
prepare/论文解析/Repo scan 等前置节点没有重新执行
assignment_epoch=2
当前 binding host_id=host-b
checkpoint repo_path/run_dir 指向 host-b root
Host B 的 run/analysis 文件已从 manifest 恢复
Job 到达 action approval 时，pending_action.cwd 指向 host-b repo
```

因为 `human_review` 包含 path-bound action，Worker B 再次 seal 时正确结果通常是：

```text
portable=false
blocked_reasons 包含 path_bound_approval_interrupt
affinity_host_id=host-b
```

这不否定前一步跨 host 成功；它表示接下来的 action approval 和执行必须留在 Host B，
避免审批 hash 与 cwd 被静默修改。

### 60.9 检查 Host B 文件不依赖 Host A root

```bash
find \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-b/jobs \
  -maxdepth 5 -type f \
  | sort \
  | head -n 80
```

比较 repo commit：

```bash
git -C /data/tianshaoqi24/PST-Convolution-main rev-parse HEAD

# 从 show-state 的 repo_path 复制 Host B 当前路径后执行：
git -C /data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-b/jobs/<job_id>/epochs/00000002/repo rev-parse HEAD
```

两个 commit 必须一致。不要硬编码 `<job_id>`；使用真实目录。

---

## 六十一、真正两台主机验收

> **本节类型：正式跨主机验收，不修改项目代码。**

同机双 root 通过后，再使用真实 Host A/Host B。要求：

```text
两台主机都能访问同一 PostgreSQL DATABASE_URL
两台主机都能访问同一 S3/MinIO endpoint/bucket/prefix
两台主机安装同一项目 commit
两台主机 execution policy hash 相同
各自主机使用不同且本地的 WORKER_WORKSPACE_ROOT
Host B 不挂载 Host A workspace
外部数据集按 label/fingerprint 各自准备
系统时间可由 NTP 管理，但 lease 仍只信数据库时间
```

### 61.1 Host A

```bash
export WORKER_HOST_ID=gpu-host-a
export WORKER_WORKSPACE_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-a
export WORKER_CAPABILITIES_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/config/worker_capabilities.host-a.json
export EXECUTION_PROFILES_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/config/execution_profiles.host-a.json

python -m app.main run-worker --worker-id pstnet-worker-a --once
```

到达 `command_selection` 后不要在 Host A resume。

### 61.2 提交 decision

从任意能连接同一 PostgreSQL 的受信任 API/CLI 主机提交 decision。decision 不需要能访问
Host A 本地 workspace，因为需要的 run commands/hash 已经在 interrupt preview 与
checkpoint 中。

### 61.3 Host B

Host B 上不要创建或挂载 Host A epoch 目录：

```bash
export WORKER_HOST_ID=gpu-host-b
export WORKER_WORKSPACE_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/worker_workspaces/host-b
export WORKER_CAPABILITIES_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/config/worker_capabilities.host-b.json
export EXECUTION_PROFILES_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/config/execution_profiles.host-b.json

python -m app.main explain-scheduling "$JOB_ID"
python -m app.main run-worker --worker-id pstnet-worker-b --once
```

正式通过条件：

```text
Host B 在执行前从共享 Blob 下载全部 manifest entries
Host B Git commit 校验通过
Host B 获得新的 assignment_epoch
旧 Host A assignment token 无法写 manifest head
Graph 从原 interrupt 恢复
前置节点调用计数/trace 没有增加
新的 Artifact 由 Host B 发布到同一 Catalog
```

只看到 `job_claimed worker-b` 不算通过；必须同时证明 workspace materialized 和 Graph
未重跑前置节点。

---

## 六十二、故障注入验收

> **本节类型：可靠性验收，不修改项目代码。**

### 62.1 不兼容 GPU/CUDA

让 Host B capability 暂时声明不匹配的 CUDA major，重新启动新 session：

```bash
python -m app.main explain-scheduling "$JOB_ID"
python -m app.main run-worker --worker-id incompatible-b --once
```

期望：

```text
explain 包含 cuda_major_mismatch
handled=false
Job attempt_count 不增加
Job 仍 queued
```

恢复真实配置后再启动兼容 Worker。

### 62.2 Dirty repository

在一个专用测试 branch 对源 repo 做未提交修改后 submit。不要改正在使用的重要工作区。

期望：

```text
initial manifest portable=false
blocked_reasons 包含 repository_dirty
affinity_host_id=submit host
其他 host 无法 claim
没有自动 stash/reset/commit
```

### 62.3 S3/MinIO 暂时不可用

在测试环境停止 MinIO 或使用错误 endpoint，再让 Worker materialize。

期望：

```text
Graph 不启动
Job 不写 succeeded
已有 checkpoint/manifest pointer 不丢失
错误分类为 ArtifactBackendUnavailable
恢复服务后可按 retry policy 继续
```

### 62.4 Manifest/Blob tamper

只在隔离 test bucket 操作。替换一个对象内容但保留 key，或构造错误 metadata。

期望：

```text
size/hash 校验失败
repo/Graph 不执行
Job reconciliation_required 或 terminal integrity error
错误消息不打印对象内容和 credential
```

### 62.5 Worker A 在运行中被 kill

让 Worker A 进入受监管 sleep/训练 probe 后 `kill` Worker 进程，但不要手动结束子进程。

期望：

```text
lease 到期
其他 host 无法用本机 PID namespace 判定远端子进程
Job reconciliation_required
不会自动在 Host B 重跑 command
```

这与 graceful interrupt handoff 是不同场景。确认原主机/容器已被外部 scheduler fence 后，
再人工 resolve reconciliation。

### 62.6 旧 Worker 恢复网络

让 Worker A 丢失数据库连接超过 lease，Job 经人工安全处理后被新 Worker claim；再恢复
Worker A 连接。

期望旧 Worker：

```text
heartbeat/mark/seal 因 claim token 失效失败
不能覆盖 current manifest
不能覆盖 Job 终态
只能在旧 epoch 目录留下隔离写入
```

### 62.7 GC dry-run

```bash
python -m app.main gc-workspaces
```

先核对 candidate，再执行：

```bash
python -m app.main gc-workspaces --execute
```

期望只删除当前 host、released/failed、超过年龄、marker identity 完全匹配的 epoch。

---

## 六十三、可观测性与事件清单

> **本节类型：观测设计，不修改项目代码。**

建议事件：

| Event | 何时产生 | 关键非敏感字段 |
|---|---|---|
| `job_submitted` | 初始 manifest pointer 与 Job 同事务创建 | manifest id、portable、requirements summary |
| `job_claimed` | capability/affinity SQL 匹配成功 | host、session、assignment epoch |
| `workspace_materializing` | assignment row 创建 | assignment id、manifest id、host |
| `workspace_ready` | 文件/Git/hash 校验全部通过 | entry count、bytes、repo commit |
| `workspace_materialization_failed` | 物化失败 | error code、stage，不含路径内容/secret |
| `workspace_sealed` | 新 portable manifest 成为 head | generation、manifest hash |
| `workspace_portability_blocked` | 只能 host-affine | bounded blocked reasons、host |
| `job_waiting_for_input` | manifest 已 seal 后进入等待 | interrupt nodes、wait generation |
| `workspace_rebound` | resume 使用新 binding | old/new epoch、old/new host |
| `workspace_released` | 新 epoch ready 或 Job terminal | assignment id、epoch |
| `workspace_garbage_collected` | 本地目录安全删除 | assignment id、epoch、host |

不要为每次 Worker session heartbeat 写 Event row，否则会形成高频日志风暴。当前状态留在
`worker_sessions` row；只记录注册、draining 和异常状态变化。

建议指标：

```text
queued_jobs_by_requirement
active_worker_sessions_by_pool
unschedulable_job_age_seconds
workspace_materialization_seconds
workspace_materialization_bytes
workspace_manifest_entry_count
workspace_integrity_failure_total
workspace_affinity_blocked_total
handoff_total{from_host,to_host,result}
workspace_gc_bytes_total
```

`unschedulable_job_age_seconds` 比“轮询次数”更有意义；任务长期 queued 时，CLI/API 应直接
显示哪个 requirement 无 Worker 满足。

---

## 六十四、安全复核清单

> **本节类型：安全检查，不修改项目代码。**

- Worker identity 来自受信任配置，不来自 Job/LLM；
- 同名 Worker 重启生成新 session ID；
- session lease 和 Job lease 都使用数据库时间；
- claim 在 SQL transaction 内同时检查 capability 与 affinity；
- policy hash 防止同 profile ID 的安全策略漂移；
- assignment epoch 隔离旧 Worker 的本地写入；
- manifest pointer 更新校验 claim token 与 assignment token；
- manifest content hash 不含随机 ID/时间，支持幂等重放；
- Blob-first，DB pointer 永不指向尚未上传的对象；
- LocalBlobStore 不冒充 shared store；
- Workspace entry 只允许相对 POSIX path；
- Materializer 不解压任意 tar/zip；
- 每个 Blob 校验 metadata、size 和 SHA-256；
- Git bundle 来自 clean named branch；
- submodule/LFS 第一版 fail closed；
- Git checkout 后复核 commit、clean state 和 symlink；
- 不恢复 suid/sgid/sticky permissions；
- ignored/untracked 文件不进入 Git bundle；
- dirty repo 不自动 stash/reset/commit；
- 数据集只保存引用，不上传；
- dataset label 还要对应真实 mount/fingerprint marker；
- active/ambiguous remote subprocess 不自动迁移；
- path-bound approval interrupt 保留 host affinity；
- `Command(resume, update)` 原子消费 decision 与路径更新；
- 不用单独 `update_state()` 破坏 interrupt task；
- ArtifactPublisher 不信任旧 absolute path；
- API cancel 只写数据库，由 owning Worker 写本地 cancel request；
- Public API 不返回 source paths、object keys 或 fencing token；
- GC 默认 dry-run，只删精确 marker 匹配的 released epoch；
- GC 不删除共享 Blob；
- migration 不伪造旧 active Job 的 portable manifest；
- 测试数据库与生产数据库隔离。

---

## 六十五、常见问题排查

> **本节类型：排障说明，不修改项目代码。**

### 65.1 Job 一直 queued

执行：

```bash
python -m app.main list-workers --include-expired
python -m app.main explain-scheduling "$JOB_ID"
```

常见原因：

```text
worker session lease expired
worker_pool_mismatch
execution_profile_missing
execution_policy_hash_mismatch
gpu_count_insufficient
cuda_major_mismatch
required_worker_label_missing
workspace_disk_insufficient
host_affinity_mismatch
```

不要通过直接改 Job row 降低 requirement；修正受信任 profile/capability 后创建新 Worker
session。

### 65.2 `repository_dirty`

说明 tracked/untracked 内容不等于 HEAD。查看：

```bash
git -C /data/tianshaoqi24/PST-Convolution-main status --short
```

确认修改后由你决定 commit 或保持 host-affine。Agent 不应替你清理。

### 65.3 `Refusing to create empty bundle`

通常是 detached HEAD 或把 commit SHA 当作唯一 rev-list arg。检查：

```bash
git -C /data/tianshaoqi24/PST-Convolution-main symbolic-ref --short HEAD
```

本教程传命名 branch，不传裸 commit。

### 65.4 `manifest hash 校验失败`

检查：

```text
是否把 manifest_id/created_at 错误纳入内容 hash
是否在计算 hash 后又修改 entries/portable/source
DB manifest_hash 与 JSON manifest_hash 是否一致
Pydantic dump 是否使用了不同 alias/exclude 规则
```

不要“重新计算后覆盖数据库”掩盖 tamper；先确认哪个写入路径破坏了不可变性。

### 65.5 Materializer 报 path escape

检查 `logical_path` 是否：

```text
以 / 开头
包含 ..
scope 与 role 不匹配
经过 symlink 指向 root 外
```

不要用 `Path.resolve()` 后再把逃逸路径硬改回 root；应拒绝该 manifest。

### 65.6 `workspace binding 未 ready`

说明 Graph 在 materialization/DB ready 提交前启动。正确顺序：

```text
begin assignment -> materialize -> mark ready -> runner.execute
```

检查 Worker 是否在 prepare 失败后仍继续调用 runner。

### 65.7 Resume 后又回到同一个 interrupt

重点检查是否写成：

```python
graph.update_state(...)
graph.invoke(Command(resume=...), ...)
```

应改成：

```python
graph.invoke(
    Command(resume=value, update=workspace_update),
    config,
)
```

并运行 `tests/test_workspace_rebind.py::test_command_update_and_resume_are_atomic`。

### 65.8 `Artifact absolute_path 与 relative_path 不一致`

说明旧 Publisher 的 absolute-path equality 还没删除，或 Worker 没有传当前 binding。检查
`ArtifactPublisher._source_path()` 是否只用：

```text
binding.run_dir + record.relative_path + size + hash
```

### 65.9 Host B 找不到 profile workspace root

`load_execution_profiles()` 仍会验证 base profile root 存在。每台 host 使用自己的 profile
配置文件，并让 base `workspace_root` 指向该 Worker 已存在的受控 root；Graph 执行时再由
`get_execution_profile_for_state()` 收紧到具体 materialized repo。

### 65.10 policy hash mismatch

比较两个 profile JSON 的：

```text
backend
allowed programs/args/env
network policy
resource budget
enforcement mode
worker requirement/labels
```

host-local path 不应进入 policy hash；环境内容差异用受信任 `env:*` label 表达。

### 65.11 dataset label 存在但 preflight 失败

label 只是调度索引，还要确认：

```text
dataset_mounts[label] 是绝对路径
路径位于 ALLOWED_ROOT 内
目录真实存在
fingerprint marker 与 manifest 一致
```

### 65.12 旧 Worker 仍能写本地文件

fencing 不能让失联进程瞬间消失。Phase 26 的保证是：

```text
旧 epoch 与新 epoch 隔离
旧 token 不能更新 DB head/终态
远端活跃进程触发 reconciliation
```

真正强制停止需要容器/集群 runtime，这也是下一阶段建议。

### 65.13 Migration 检测到 legacy Job

不要注释掉 guard。先：

```text
停止 API/Worker 写入
备份数据库
处理 active/waiting Job
对 terminal Job 执行显式 legacy backfill 或归档
再升级 schema
```

### 65.14 GC 一直跳过 marker mismatch

不要手动删除 marker。比较 DB assignment identity 与本地 marker；如果 token/hash 不一致，
说明路径可能被复用或人工移动，应进入诊断，不应让 GC 猜测。

---

## 六十六、本阶段 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 66.1 Control Plane 与 Execution Plane 不同

PostgreSQL 可以决定“谁运行”，但不能自动提供“运行所需文件”。Distributed Agent 必须
同时设计 metadata ownership 和 workspace ownership。

### 66.2 Capability-based Scheduling

Agent 任务不是普通 FIFO：不同 Job 对 profile、GPU、CUDA、磁盘、数据集和安全策略有
要求。正确 claim 是：

```text
queue ordering + compatible capabilities + affinity + row lock
```

### 66.3 Affinity 是安全约束，不只是性能优化

当审批 hash、dirty repo、外部挂载或活动进程绑定某台主机时，affinity 防止另一台主机
执行语义不同的动作。

### 66.4 Workspace as an Immutable Value

Manifest 把“目录”转成可验证值：

```text
logical file set + content hashes + repo identity + external references
```

这使恢复、审计、缓存和跨 host 传输拥有共同语言。

### 66.5 Content-addressed Storage

同内容复用同 object key，重试不会产生多个可变副本。内容地址不等于权限控制，仍要由
Artifact/Workspace catalog 做 Job ownership 与公开投影。

### 66.6 Fencing 不等于 Kill

claim token 能阻止 stale writer 更新共享事实源，但不能直接终止旧主机进程。因此仍需
epoch 隔离、process identity、reconciliation，以及未来更强的容器 scheduler fencing。

### 66.7 Safe Point / Quiescence

跨 host 接管要求系统到达可证明无活跃副作用的边界。Human interrupt 是天然 safe point
候选，但只有在路径型审批和 pending action 等额外条件也满足时才 portable。

### 66.8 Checkpoint State 也有本地性

持久化 state 并不代表 state 中的每个值都可移植。绝对路径、PID、open handle、临时目录
和环境 fingerprint 都需要显式转换或阻断。

### 66.9 Atomic Resume Update

LangGraph `Command(resume=..., update=...)` 允许在消费 interrupt input 的同一次恢复中更新
state。单独 `update_state()` 会创建新 checkpoint，不能在不了解 task/reducer 语义时拿来
做透明迁移。

### 66.10 Environment Identity

相同 profile ID 不代表相同环境。Phase 26 先用 policy hash + environment label；真正
可重复执行仍需要 immutable image digest 或 lockfile/environment attestation。

---

## 六十七、完成标准

> **本节类型：最终验收清单，不修改项目代码。**

只有以下全部满足，Phase 26 才算完成：

- Worker 每次启动生成新 session ID；
- Worker session idle/running heartbeat 都正常；
- draining Worker 不 claim 新 Job；
- Job requirements 只从受信任 profile 派生；
- execution policy hash 能发现同 ID 配置漂移；
- Python compatibility 与 PostgreSQL claim 结果一致；
- 不兼容 Worker 不增加 Job attempt_count；
- affinity host 之外的 Worker 无法 claim；
- initial snapshot 支持 paper、optional log 和 clean Git bundle；
- dirty repo 不被自动修改且变成 host-affine；
- submodule/LFS 第一版 fail closed；
- LocalBlobStore manifest 不被标为 portable；
- S3/MinIO Blob 上传后再发布 DB pointer；
- manifest hash 为稳定语义 hash；
- 相同 seal 在响应丢失后可幂等重放；
- assignment begin 可幂等重放；
- 每个 Blob materialize 后校验 size/hash；
- Git commit/clean/symlink 校验通过；
- materialization 使用 staging + atomic rename；
- 每次 claim 使用隔离 assignment epoch；
- stale claim/token 不能 seal manifest；
- checkpoint 路径只重绑定已知 path-bearing 字段；
- command 文本硬编码旧绝对路径时阻断 handoff；
- ArtifactRecord absolute path 被更新但不再作为定位依据；
- `Command(resume, update)` 测试证明前置节点不重跑；
- effective execution profile 使用当前 binding；
- dataset mount 与 optional fingerprint 在 Graph 前校验；
- waiting 前已完成 Artifact publish 和 workspace seal；
- path-bound approval interrupt 保持 host affinity；
- remote running crash 进入 reconciliation；
- API cancel 不写远端本地路径；
- Public API 不泄漏 token/object key/source path；
- GC 默认 dry-run 且只删 released/failed 精确 epoch；
- 无 TEST DB URL 时 Postgres tests 正确 skip；
- Phase 22-25 回归通过；
- 同机双 root handoff 通过；
- 两台真实主机 handoff 通过；
- PSTNet 前置节点未重复执行；
- Host B 新 Artifact 出现在共享 Catalog；
- 文档没有把 active crash 写成自动安全接管。

---

## 六十八、下一阶段建议

> **本节类型：路线说明，不修改项目代码。**

Phase 26 完成后，最值得继续的是：

```text
Phase 27：OCI Container Execution、Immutable Environment Identity
          与 Strong Runtime Isolation
```

原因：

```text
Workspace 已可迁移
PostgreSQL/S3 已共享
但 local/conda runner 仍是 best_effort
```

下一阶段建议内容：

```text
Container/Podman/Docker runner port
image digest 而不是 mutable tag
rootless execution
read-only root filesystem
repo/run/dataset 精确 mount
tmpfs HOME/TMP
CPU/memory/pids cgroup hard limit
GPU device request 与 CUDA image compatibility
default-deny egress
seccomp/capability drop/no-new-privileges
container/process identity journal
claim token -> container label fencing
crash 后由 runtime 查询并终止 orphan container
image SBOM/provenance/signature
preflight environment attestation
双 host 相同 image digest 回归
```

这会补上 Phase 16 明确留下的边界：当前 local/conda policy 能检查声明并监管进程，但不能
提供真正的 filesystem/network/kernel isolation。Redis/MQ 仍不应优先于这个执行安全
缺口，除非 PostgreSQL polling 已经有明确性能数据证明成为瓶颈。

---

## 六十九、阶段结论

> **本节类型：总结，不修改项目代码。**

Phase 25 让多个 Worker 共享“任务事实”；Phase 26 让兼容 Worker 能获得“等价且可验证的
执行材料”：

```text
Shared control plane
    + capability-aware claim
    + immutable workspace manifest
    + content-addressed shared blob
    + verified materialization
    + atomic checkpoint path rebind
    + host affinity / process fencing
```

可靠的跨主机 Agent 不是“换一个 worker_id 再 invoke”。它必须先回答：

```text
新 Worker 能不能执行？
它拿到的代码和输入是不是同一份？
旧 Worker 是否仍可能产生副作用？
checkpoint 中哪些字段绑定旧主机？
用户审批是否仍对应将要执行的动作？
```

本阶段的价值，就是把这些隐含假设变成结构化 schema、数据库条件、hash、状态机、测试
与可审计 Event。
