# Phase 35：单机数据保留、容量配额与可审计垃圾回收

> 本章是在 Phase 34 已完成之后的下一阶段实现教程。
>
> 本章会给出需要新增或修改的文件、带上下文的核心代码、测试代码、测试命令和手工验收步骤；本教程本身不会直接修改 `app/`、`tests/` 或 `web/`。
>
> 本阶段优先保证单机单用户的数据生命周期闭环，不引入 Redis、消息队列、定时任务框架或多租户配额。

---

## 一、为什么现在优先做数据保留与 GC

> **本节类型：设计说明，不修改项目代码。**

目前系统已经能够持续产生并保存多类数据：

```text
Job Runtime SQLite
LangGraph Checkpoint SQLite
Chat SQLite
Resource SQLite
Artifact Catalog SQLite
Artifact / Resource / Workspace Blob
runs/<run_id>/ 运行目录
worker_workspaces/<host>/jobs/<job>/epochs/<epoch>/ 物化目录
workspace_staging/ 与 exports/.staging/ 临时文件
日志、trace、评测报告与修复记录
```

如果继续增加功能却没有生命周期管理，单机长期运行后会出现：

1. 磁盘逐渐耗尽，但用户不知道哪些数据可以安全删除；
2. 删除一个 Job 目录后，Checkpoint、Chat 和 Catalog 中仍保留悬空记录；
3. 直接删除 Blob 可能破坏另一个 Job、Workspace 或 Resource；
4. SQLite 删除行后文件不立即缩小，用户误以为 GC 没有生效；
5. 清理中途进程崩溃后，无法判断哪些步骤已经执行；
6. 磁盘已经接近满载时仍可提交新任务，最终在运行中不可预测地失败。

因此本阶段不是实现一个简单的 `rm -rf old-runs`，而是建立完整协议：

```text
Inventory
    -> Policy + Hold
    -> Immutable Cleanup Plan
    -> Human Confirm(plan_hash)
    -> Idempotent Sweep Journal
    -> Recount Shared References
    -> Cleanup Audit
```

这使 Agent 从“会产生数据”升级为“知道数据属于谁、何时可删、为什么删除、删除到哪一步以及释放了多少空间”。

---

## 二、本阶段完成后的能力

> **本节类型：目标说明，不修改项目代码。**

完成后应满足：

1. 系统可以统计所有受管目录、SQLite 文件和 staging 的占用；
2. 统计同时区分逻辑大小和磁盘分配大小；
3. 容量盘点不跟随符号链接，也不遍历配置根目录之外的路径；
4. 只把超过保留期的终态 Job 列为候选；
5. `queued/running/waiting_for_input/cancelling/reconciliation_required` 永不自动清理；
6. 用户可以为重要 Job 设置 retention hold；
7. 清理必须先创建不可变 Plan，再提交完全相同的 `plan_hash` 确认；
8. Plan 过期、Job version 变化、状态变化或路径身份变化时 fail closed；
9. 清理步骤写入独立审计账本，进程崩溃后可从同一 Plan 重试；
10. Job、Chat、Checkpoint、Artifact metadata、Workspace 和运行目录有明确删除顺序；
11. Blob 只有在 Artifact、Workspace Manifest 和 Resource Manifest 引用数都为零时才能删除；
12. Resource 默认不随 Job 删除；Resource 是可复用输入，拥有独立生命周期；
13. 本地 Blob 删除前重新核对 `object_key + size + SHA-256`；
14. 第一版只允许 `SQLite + LocalBlobStore` 执行破坏性 Sweep；
15. PostgreSQL 或 S3 配置下仍可查看容量摘要，但 Sweep 明确拒绝；
16. 配额不足时拒绝新 Job，不中止正在运行的 Job；
17. API、CLI 和 Web 都可以查看 Plan 与清理结果；
18. GC 审计记录不会因为 Job 本身被删除而一起消失；
19. 默认操作是 preview/dry-run，不会因打开页面或查看摘要而删除数据；
20. 所有测试临时数据都位于项目内 `.pytest-tmp/`，不使用系统 `/tmp`。

---

## 三、本阶段明确不做

> **本节类型：范围说明，不修改项目代码。**

```text
不实现多用户、按租户配额或 RBAC
不实现自动定时 Sweep
不在磁盘达到阈值时自动删除最旧 Job
不终止运行中的任务来回收空间
不删除非终态 Job
不把 Resource 生命周期隐式绑定到某个 Job
不自动删除 published Resource metadata 或 Resource Blob
不扫描并自动删除从未出现在当前 Plan 中的历史孤儿文件
不删除配置允许根目录之外的任何文件
不跟随符号链接统计或删除内容
不相信前端提交的本地路径、object_key、size 或 hash
不允许只凭 job_id 直接执行删除
不把 cleanup report 发布成待删除 Job 的 Artifact
不把 SQLite VACUUM 算作普通在线 Sweep 的一部分
不在 S3 上执行 DeleteObject
不在 PostgreSQL 控制面执行破坏性 GC
不实现 systemd timer、Celery Beat、Redis scheduler 或 Kubernetes CronJob
不承诺精确预测压缩文件、稀疏文件和写时复制文件系统的实际回收字节
```

第一版刻意保守。先把本地数据引用和删除协议做正确，再考虑远端对象存储版本、分布式锁、对象保留策略和后台调度。

---

## 四、先理解当前数据所有权

> **本节类型：架构说明，不修改项目代码。**

### 4.1 Job 私有数据

以下数据可以随一个满足策略的终态 Job 一起删除：

```text
jobs/runtime.sqlite
  |- jobs 中该 Job
  |- job_resumes
  |- job_events
  `- job_commands

chat/chat.sqlite
  `- chat_messages WHERE job_id = ?

LangGraph checkpoint
  `- thread_id 对应的 checkpoint/write/blob 记录

storage/artifacts.sqlite
  |- artifact_heads WHERE job_id = ?
  `- artifact_versions WHERE job_id = ?

runs/<run_id>/
worker_workspaces/<host>/jobs/<job_id>/epochs/<epoch>/
```

### 4.2 共享或可能共享的数据

以下内容不能仅因删除一个 Job 就直接删除：

```text
BlobStore/<object_key>
ResourceRecord / ResourceManifest
worker session
其他 Job 的 Workspace Manifest
```

ArtifactPublisher 使用内容寻址 key，同一个内容可以被多个 Artifact 或 Workspace 复用；WorkspaceManifest 也会记录 Blob 引用；Job 还可以引用 published Resource。因此 Blob 的可删除条件不是“当前 Job 已删除”，而是：

```text
artifact_reference_count(object_key) == 0
AND workspace_reference_count(object_key) == 0
AND resource_reference_count(object_key) == 0
```

### 4.3 为什么 Resource 不跟 Job 删除

一个论文 PDF Resource 可能被十个复现 Job 复用。删除其中一个 Job 时若顺带删除 Resource，剩余九个 Job 的输入 provenance 会失效。

本阶段只做：

```text
保护 Resource 引用的 Blob
统计 Resource 占用
报告可能长期未使用的 Resource
```

真正的 Resource 删除应在后续阶段使用独立的 Resource retention policy、独立 hold 和独立确认哈希。

### 4.4 SQLite 行删除与磁盘空间

SQLite 执行 `DELETE` 后，数据库页通常进入 freelist，数据库文件大小不会立即减小。这些页可以被后续写入复用，因此逻辑清理已经生效。

```text
Sweep reclaimed_logical_bytes
    != 操作系统立即增加的 free bytes
```

`VACUUM` 会重写整个数据库，需要额外临时空间并可能长时间持有锁。本阶段只在运维说明中提供离线手工命令，不把它放入在线 GC。

---

## 五、核心状态机与安全协议

> **本节类型：协议说明，不修改项目代码。**

### 5.1 Cleanup Plan 状态

```text
planned
   |
   | confirm(exact plan_hash)
   v
confirmed
   |
   | sweep CAS claim
   v
sweeping ---- process crash ----> sweeping
   |                                  |
   | retry same plan_hash             |
   +----------------------------------+
   |
   +----> completed
   `----> failed（可在未过期且身份仍一致时重试）
```

### 5.2 三步 API

```text
POST /v1/retention/plans
    生成候选快照；永不删除。

POST /v1/retention/plans/{plan_id}/confirm
    用户提交 exact plan_hash；只改变 Plan 状态。

POST /v1/retention/plans/{plan_id}/sweep
    再次提交 exact plan_hash；执行幂等清理。
```

查看容量和 hold：

```text
GET    /v1/storage/summary
GET    /v1/retention/holds
PUT    /v1/retention/holds/{job_id}
DELETE /v1/retention/holds/{job_id}
GET    /v1/retention/plans/{plan_id}
```

### 5.3 Plan Hash 绑定什么

Plan 的 canonical payload 至少包含：

```text
policy snapshot
created_at / expires_at
每个 job_id
thread_id / run_id / run_dir
job version / status / updated_at
workspace manifest id / generation
Artifact version 与 object reference 快照
Workspace root 与 binding marker 身份
候选 Blob 的 object_key / sha256 / size
```

确认只接受服务端计算的 exact hash。前端不能修改候选列表后继续使用旧确认。

### 5.4 为什么要“全部预检后再第一次删除”

如果先删 Chat，再发现 Workspace marker 不匹配，系统会留下一个只删了一半的 Job。正确流程是：

```text
读取 Plan
  -> 检查 Plan 未过期
  -> 检查所有 Job 仍为同一终态和 version
  -> 检查所有路径仍在 allowlist
  -> 检查所有 workspace marker
  -> 检查 backend 支持破坏性清理
  -> 全部通过后才开始第一个 delete step
```

预检通过后仍可能出现磁盘错误或进程崩溃，所以每个删除步骤还必须幂等并写 journal。

### 5.5 推荐删除顺序

```text
1. delete_chat(job_id)
2. delete_checkpoint(thread_id)
3. delete_artifact_metadata(job_id)
4. delete_workspace_roots(job_id)
5. delete_legacy_run_root(run_id)
6. delete_job_metadata(job_id)  # 最后删除 Job 控制面
7. recount every candidate blob
8. delete unreferenced local blobs
9. mark plan completed + write audit summary
```

Job metadata 最后删除，是因为前面步骤失败时仍可通过 Job 查到身份并重试。Blob 最后删除，是因为必须先移除所有待清理 metadata 引用，再对剩余全局引用重新计数。

---

## 六、涉及文件总览

> **本节类型：实施清单。以下文件需要修改或新增。**

### 6.1 新增文件

```text
app/retention/__init__.py
app/retention/errors.py
app/retention/schemas.py
app/retention/ports.py
app/retention/repository.py
app/retention/lock.py
app/retention/inventory.py
app/retention/paths.py
app/retention/checkpoint_adapter.py
app/retention/service.py
app/retention/factory.py
app/api/retention_routes.py
web/src/components/StoragePanel.tsx
tests/test_retention_inventory.py
tests/test_retention_service.py
tests/test_retention_api.py
web/tests/storage-panel.test.tsx
```

### 6.2 修改文件

```text
.gitignore
.env.example
app/config.py
app/job_runtime/service.py
app/job_runtime/store.py
app/storage/artifact_repository.py
app/storage/local_blob_store.py
app/chat/store.py
app/resources/repository.py
app/api/errors.py
app/api/app.py
app/main.py
web/src/api/types.ts
web/src/api/client.ts
web/src/App.tsx
web/src/styles/app.css
a_implementation_guides/README.md
```

### 6.3 为什么不直接扩大现有通用 Protocol

本项目同时有 SQLite/PostgreSQL 和 Local/S3 实现。若直接给现有 `JobStore`、`ArtifactRepository`、`BlobStore` Protocol 增加删除方法，所有远端实现会立刻被迫声明支持破坏性删除。

本阶段应新增窄端口：

```text
JobRetentionPort
ArtifactRetentionPort
ChatRetentionPort
ResourceReferencePort
CheckpointRetentionPort
DeletableBlobStore
```

SQLite/Local 具体类通过新增方法结构化满足这些端口；PostgreSQL/S3 不实现，所以 factory 可以 fail closed。

---

## 七、增加配置

> **本节类型：需要修改配置文件。**

### 7.1 修改 `.gitignore`

确认已有下面内容；缺少时追加：

```gitignore
# Pytest 临时文件固定在项目目录内。
.pytest-tmp/

# Phase 35 retention 审计数据库是运行数据，不提交 Git。
retention/
```

不要忽略整个 `storage/` 或 `runs/` 的新规则覆盖已有项目约定；只按当前仓库的实际 `.gitignore` 补缺失项。

### 7.2 修改 `.env.example`

在 Artifact/Chat 配置附近增加：

```dotenv
# Phase 35：第一版只允许 SQLite + LocalBlobStore 执行 destructive sweep。
RETENTION_ENABLED=true

# 独立审计账本。不能放进待删除 Job 的 Artifact 或 Job DB。
RETENTION_DB_PATH=retention/retention.sqlite

# 终态 Job 至少保留 14 天；0 只用于自动化测试，生产配置拒绝小于 1 天。
RETENTION_JOB_DAYS=14

# 一次 Plan 最多包含 20 个 Job，避免一次删除范围过大。
RETENTION_PLAN_MAX_JOBS=20

# Plan 在 30 分钟后过期，过期后必须重新生成和确认。
RETENTION_PLAN_TTL_SECONDS=1800

# 默认仍需要显式 confirm + sweep；该值不是自动清理开关。
RETENTION_LOCAL_BLOB_DELETE_ENABLED=true

# managed storage 的软/硬阈值。0 表示不按总字节阈值限制。
STORAGE_SOFT_LIMIT_BYTES=0
STORAGE_HARD_LIMIT_BYTES=0

# 即使未达到 hard limit，文件系统剩余空间低于 5 GiB 也拒绝新 Job。
STORAGE_MIN_FREE_BYTES=5368709120

# inventory 单次最多记录的错误和符号链接数量，避免响应失控。
STORAGE_INVENTORY_MAX_WARNINGS=100
```

### 7.3 修改 `app/config.py`

在 `chat_*` 配置之后、`settings = Settings()` 之前增加字段：

```python
    # Phase 35：单机 retention 与容量保护。
    retention_enabled: bool = _env_bool(
        "RETENTION_ENABLED", True
    )
    retention_db_path: Path = Path(
        os.getenv(
            "RETENTION_DB_PATH",
            "retention/retention.sqlite",
        )
    )
    retention_job_days: int = int(
        os.getenv("RETENTION_JOB_DAYS", "14")
    )
    retention_plan_max_jobs: int = int(
        os.getenv("RETENTION_PLAN_MAX_JOBS", "20")
    )
    retention_plan_ttl_seconds: int = int(
        os.getenv(
            "RETENTION_PLAN_TTL_SECONDS",
            "1800",
        )
    )
    retention_local_blob_delete_enabled: bool = _env_bool(
        "RETENTION_LOCAL_BLOB_DELETE_ENABLED",
        True,
    )
    storage_soft_limit_bytes: int = int(
        os.getenv("STORAGE_SOFT_LIMIT_BYTES", "0")
    )
    storage_hard_limit_bytes: int = int(
        os.getenv("STORAGE_HARD_LIMIT_BYTES", "0")
    )
    storage_min_free_bytes: int = int(
        os.getenv(
            "STORAGE_MIN_FREE_BYTES",
            str(5 * 1024 * 1024 * 1024),
        )
    )
    storage_inventory_max_warnings: int = int(
        os.getenv(
            "STORAGE_INVENTORY_MAX_WARNINGS",
            "100",
        )
    )
```

在路径初始化区域增加：

```python
settings.retention_db_path = (
    settings.retention_db_path.expanduser().resolve()
)
retention_allowed_root = settings.job_export_allowed_root.expanduser().resolve()
if (
    settings.retention_db_path == retention_allowed_root
    or retention_allowed_root not in settings.retention_db_path.parents
):
    raise ValueError(
        "RETENTION_DB_PATH 必须位于项目允许根目录内"
    )
settings.retention_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
```

在配置校验区域增加：

```python
if settings.retention_job_days < 1:
    raise ValueError(
        "RETENTION_JOB_DAYS 必须 >= 1；"
        "测试请直接注入 RetentionPolicy"
    )
if not 1 <= settings.retention_plan_max_jobs <= 100:
    raise ValueError(
        "RETENTION_PLAN_MAX_JOBS 必须为 1..100"
    )
if settings.retention_plan_ttl_seconds < 60:
    raise ValueError(
        "RETENTION_PLAN_TTL_SECONDS 必须 >= 60"
    )
if min(
    settings.storage_soft_limit_bytes,
    settings.storage_hard_limit_bytes,
    settings.storage_min_free_bytes,
) < 0:
    raise ValueError("storage limit 不能为负数")
if (
    settings.storage_soft_limit_bytes
    and settings.storage_hard_limit_bytes
    and settings.storage_soft_limit_bytes
    > settings.storage_hard_limit_bytes
):
    raise ValueError(
        "STORAGE_SOFT_LIMIT_BYTES 不能大于 HARD limit"
    )
```

这里不允许环境变量把保留期设置为 0。测试需要立即过期候选时，应直接构造 `RetentionPolicy(job_retention_seconds=0, ...)`，避免测试配置误用于真实服务。

---

## 八、定义错误、Schema 与窄端口

> **本节类型：需要新增后端代码。**

### 8.1 新建 `app/retention/__init__.py`

```python
"""Phase 35：单机数据保留、容量统计与可审计 GC。"""
```

### 8.2 新建 `app/retention/errors.py`

```python
class RetentionError(RuntimeError):
    """Retention 领域错误基类。"""


class RetentionNotFound(RetentionError):
    """Plan 或 Hold 不存在。"""


class RetentionConflict(RetentionError):
    """状态、版本、确认哈希或身份已经变化。"""


class RetentionBackendUnsupported(RetentionError):
    """当前 backend 只允许盘点，不允许 destructive sweep。"""


class StorageCapacityExceeded(RetentionError):
    """新任务会突破硬配额或最小剩余空间。"""


class RetentionPathUnsafe(RetentionError):
    """候选路径不满足 allowlist、identity 或 symlink 约束。"""
```

### 8.3 新建 `app/retention/schemas.py`

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RetentionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetentionPolicy(RetentionModel):
    job_retention_seconds: int = Field(ge=0)
    max_jobs_per_plan: int = Field(ge=1, le=100)
    plan_ttl_seconds: int = Field(ge=60)
    delete_local_blobs: bool = True


class ManagedRootUsage(RetentionModel):
    name: str
    path: str
    exists: bool
    logical_bytes: int = Field(ge=0)
    allocated_bytes: int = Field(ge=0)
    file_count: int = Field(ge=0)
    directory_count: int = Field(ge=0)
    skipped_symlink_count: int = Field(ge=0)
    error_count: int = Field(ge=0)


class StorageSummary(RetentionModel):
    generated_at: str
    managed_logical_bytes: int = Field(ge=0)
    managed_allocated_bytes: int = Field(ge=0)
    filesystem_total_bytes: int = Field(ge=0)
    filesystem_free_bytes: int = Field(ge=0)
    soft_limit_bytes: int = Field(ge=0)
    hard_limit_bytes: int = Field(ge=0)
    min_free_bytes: int = Field(ge=0)
    pressure: Literal["normal", "soft", "hard"]
    destructive_gc_supported: bool
    roots: list[ManagedRootUsage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ManagedRootUsageView(RetentionModel):
    name: str
    exists: bool
    logical_bytes: int = Field(ge=0)
    allocated_bytes: int = Field(ge=0)
    file_count: int = Field(ge=0)
    directory_count: int = Field(ge=0)
    skipped_symlink_count: int = Field(ge=0)
    error_count: int = Field(ge=0)


class StorageSummaryView(RetentionModel):
    """Web/API 不公开宿主机绝对路径。"""

    generated_at: str
    managed_logical_bytes: int
    managed_allocated_bytes: int
    filesystem_total_bytes: int
    filesystem_free_bytes: int
    soft_limit_bytes: int
    hard_limit_bytes: int
    min_free_bytes: int
    pressure: Literal["normal", "soft", "hard"]
    destructive_gc_supported: bool
    roots: list[ManagedRootUsageView]
    warnings: list[str]

    @classmethod
    def from_summary(cls, summary: StorageSummary) -> "StorageSummaryView":
        payload = summary.model_dump(exclude={"roots", "warnings"})
        return cls(
            **payload,
            roots=[
                ManagedRootUsageView(
                    **item.model_dump(exclude={"path"})
                )
                for item in summary.roots
            ],
            warnings=(
                [f"{len(summary.warnings)} inventory warnings; inspect CLI"]
                if summary.warnings
                else []
            ),
        )


class BlobReference(RetentionModel):
    backend: str
    object_key: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class WorkspaceDeleteTarget(RetentionModel):
    path: str
    assignment_epoch: int = Field(ge=0)
    # API/审计中只保存 token hash，不泄露 fencing token 原文。
    assignment_token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class JobCleanupTarget(RetentionModel):
    job_id: str
    thread_id: str
    run_id: str
    run_dir: str
    job_version: int = Field(ge=0)
    job_status: Literal["succeeded", "failed", "cancelled"]
    job_updated_at: str
    workspace_manifest_id: str
    workspace_manifest_generation: int = Field(ge=0)
    workspace_targets: list[WorkspaceDeleteTarget] = Field(
        default_factory=list
    )
    artifact_blobs: list[BlobReference] = Field(default_factory=list)
    workspace_blobs: list[BlobReference] = Field(default_factory=list)
    estimated_logical_bytes: int = Field(ge=0)


class CleanupPlan(RetentionModel):
    plan_id: str
    status: Literal[
        "planned",
        "confirmed",
        "sweeping",
        "completed",
        "failed",
    ]
    plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: RetentionPolicy
    targets: list[JobCleanupTarget]
    created_at: str
    expires_at: str
    confirmed_at: str | None = None
    completed_at: str | None = None
    failure_code: str | None = None


class CleanupStep(RetentionModel):
    plan_id: str
    job_id: str
    step_name: str
    status: Literal["pending", "completed", "failed"]
    detail: str | None = None
    updated_at: str


class CleanupResult(RetentionModel):
    plan: CleanupPlan
    deleted_jobs: int = Field(ge=0)
    deleted_blob_count: int = Field(ge=0)
    retained_shared_blob_count: int = Field(ge=0)
    reclaimed_logical_bytes: int = Field(ge=0)
    steps: list[CleanupStep] = Field(default_factory=list)


class CleanupTargetView(RetentionModel):
    """API 公开视图不暴露本地路径、Blob key 或 token hash。"""

    job_id: str
    run_id: str
    job_status: Literal["succeeded", "failed", "cancelled"]
    job_updated_at: str
    estimated_logical_bytes: int = Field(ge=0)


class CleanupPlanView(RetentionModel):
    plan_id: str
    status: str
    plan_hash: str
    targets: list[CleanupTargetView]
    created_at: str
    expires_at: str
    failure_code: str | None = None

    @classmethod
    def from_plan(cls, plan: CleanupPlan) -> "CleanupPlanView":
        return cls(
            plan_id=plan.plan_id,
            status=plan.status,
            plan_hash=plan.plan_hash,
            targets=[
                CleanupTargetView(
                    job_id=item.job_id,
                    run_id=item.run_id,
                    job_status=item.job_status,
                    job_updated_at=item.job_updated_at,
                    estimated_logical_bytes=item.estimated_logical_bytes,
                )
                for item in plan.targets
            ],
            created_at=plan.created_at,
            expires_at=plan.expires_at,
            failure_code=plan.failure_code,
        )


class CleanupResultView(RetentionModel):
    plan: CleanupPlanView
    deleted_jobs: int = Field(ge=0)
    deleted_blob_count: int = Field(ge=0)
    retained_shared_blob_count: int = Field(ge=0)
    reclaimed_logical_bytes: int = Field(ge=0)

    @classmethod
    def from_result(cls, result: CleanupResult) -> "CleanupResultView":
        return cls(
            plan=CleanupPlanView.from_plan(result.plan),
            deleted_jobs=result.deleted_jobs,
            deleted_blob_count=result.deleted_blob_count,
            retained_shared_blob_count=result.retained_shared_blob_count,
            reclaimed_logical_bytes=result.reclaimed_logical_bytes,
        )


class RetentionHold(RetentionModel):
    job_id: str
    reason: str = Field(min_length=1, max_length=500)
    actor: str = Field(min_length=1, max_length=200)
    created_at: str


class PlanConfirmRequest(RetentionModel):
    plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class HoldRequest(RetentionModel):
    reason: str = Field(min_length=1, max_length=500)
```

`estimated_logical_bytes` 只是计划时估算，不能承诺等于最终文件系统 free space 增量。最终报告同时记录实际成功删除的文件/Blob 大小。

### 8.4 新建 `app/retention/ports.py`

```python
from __future__ import annotations

from pathlib import Path
from contextlib import AbstractContextManager
from typing import Protocol

from app.job_runtime.schemas import JobRecord
from app.retention.schemas import BlobReference
from app.workspace.schemas import WorkspaceBinding, WorkspaceManifest


class JobRetentionPort(Protocol):
    def list_retention_candidates(
        self,
        *,
        updated_before: float,
        limit: int,
    ) -> list[JobRecord]: ...

    def get(self, job_id: str) -> JobRecord: ...

    def list_workspace_bindings_for_retention(
        self,
        job_id: str,
    ) -> list[WorkspaceBinding]: ...

    def list_workspace_manifests_for_retention(
        self,
        job_id: str,
    ) -> list[WorkspaceManifest]: ...

    def count_workspace_blob_references(
        self,
        *,
        object_key: str,
    ) -> int: ...

    def delete_job_for_retention(
        self,
        *,
        job_id: str,
        expected_version: int,
        expected_status: str,
    ) -> bool: ...


class ArtifactRetentionPort(Protocol):
    def list_blob_references_for_job(
        self,
        job_id: str,
    ) -> list[BlobReference]: ...

    def delete_job_artifacts(self, job_id: str) -> int: ...

    def count_blob_references(
        self,
        *,
        backend: str,
        object_key: str,
    ) -> int: ...


class ChatRetentionPort(Protocol):
    def delete_job_messages(self, job_id: str) -> int: ...


class ResourceReferencePort(Protocol):
    def count_blob_references(
        self,
        *,
        backend: str,
        object_key: str,
    ) -> int: ...


class CheckpointRetentionPort(Protocol):
    def delete_thread(self, thread_id: str) -> None: ...


class DeletableBlobStore(Protocol):
    backend_name: str

    def delete_if_matches(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_size: int,
    ) -> bool: ...


class PathRemover(Protocol):
    def validate_job_paths(
        self,
        *,
        job: JobRecord,
        bindings: list[WorkspaceBinding],
    ) -> list[Path]: ...

    def remove_tree(self, path: Path) -> int: ...


class SweepLock(Protocol):
    def acquire(self) -> AbstractContextManager[None]: ...
```

注意：`ResourceReferencePort` 第一版只有引用计数，没有 `delete_resource()`。这是有意限制，不是遗漏。

---

## 九、实现独立 Retention 审计账本

> **本节类型：需要新增后端代码。**

新建 `app/retention/repository.py`。这个数据库不能复用 Job DB，因为完成清理后审计记录仍需存在。

```python
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from app.retention.errors import RetentionConflict, RetentionNotFound
from app.retention.schemas import (
    CleanupPlan,
    CleanupStep,
    RetentionHold,
)


def _iso(value: float | None = None) -> str:
    return datetime.fromtimestamp(
        time.time() if value is None else value,
        tz=timezone.utc,
    ).isoformat()


class SqliteRetentionRepository:
    """保存 Plan、确认、逐步 journal 和 hold。"""

    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS retention_plans (
                    plan_id TEXT PRIMARY KEY,
                    plan_hash TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    confirmed_at REAL,
                    completed_at REAL,
                    failure_code TEXT
                );

                CREATE TABLE IF NOT EXISTS retention_steps (
                    plan_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detail TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (plan_id, job_id, step_name),
                    FOREIGN KEY (plan_id)
                        REFERENCES retention_plans(plan_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS retention_holds (
                    job_id TEXT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _plan(row: sqlite3.Row) -> CleanupPlan:
        payload = json.loads(row["payload_json"])
        payload.update(
            {
                "status": row["status"],
                "confirmed_at": (
                    _iso(row["confirmed_at"])
                    if row["confirmed_at"] is not None
                    else None
                ),
                "completed_at": (
                    _iso(row["completed_at"])
                    if row["completed_at"] is not None
                    else None
                ),
                "failure_code": row["failure_code"],
            }
        )
        return CleanupPlan.model_validate(payload)

    def create_plan(self, plan: CleanupPlan) -> CleanupPlan:
        # status/确认时间属于 mutable envelope，不参与 payload hash。
        payload = plan.model_dump(
            mode="json",
            exclude={
                "status",
                "confirmed_at",
                "completed_at",
                "failure_code",
            },
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO retention_plans (
                    plan_id, plan_hash, status, payload_json,
                    created_at, expires_at
                ) VALUES (?, ?, 'planned', ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    plan.plan_hash,
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    datetime.fromisoformat(plan.created_at).timestamp(),
                    datetime.fromisoformat(plan.expires_at).timestamp(),
                ),
            )
        return self.get_plan(plan.plan_id)

    def get_plan(self, plan_id: str) -> CleanupPlan:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM retention_plans WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
        if row is None:
            raise RetentionNotFound(f"cleanup plan 不存在：{plan_id}")
        return self._plan(row)

    def confirm_plan(self, *, plan_id: str, plan_hash: str) -> CleanupPlan:
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """
                UPDATE retention_plans
                SET status = 'confirmed', confirmed_at = ?
                WHERE plan_id = ?
                  AND plan_hash = ?
                  AND status = 'planned'
                  AND expires_at > ?
                """,
                (now, plan_id, plan_hash, now),
            ).rowcount
            if changed != 1:
                raise RetentionConflict(
                    "Plan 不存在、已过期、状态已变化或 hash 不匹配"
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self.get_plan(plan_id)

    def claim_sweep(self, *, plan_id: str, plan_hash: str) -> CleanupPlan:
        """confirmed/failed 可进入 sweeping；sweeping 重试保持幂等。"""

        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM retention_plans WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
            if (
                row is None
                or row["plan_hash"] != plan_hash
                or row["expires_at"] <= now
                or row["status"] not in {"confirmed", "failed", "sweeping"}
            ):
                raise RetentionConflict(
                    "Plan 不能执行：状态、过期时间或 hash 不匹配"
                )
            connection.execute(
                """
                UPDATE retention_plans
                SET status = 'sweeping', failure_code = NULL
                WHERE plan_id = ?
                """,
                (plan_id,),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self.get_plan(plan_id)

    def step_completed(
        self,
        *,
        plan_id: str,
        job_id: str,
        step_name: str,
    ) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT status FROM retention_steps
                WHERE plan_id = ? AND job_id = ? AND step_name = ?
                """,
                (plan_id, job_id, step_name),
            ).fetchone()
        return row is not None and row["status"] == "completed"

    def record_step(
        self,
        *,
        plan_id: str,
        job_id: str,
        step_name: str,
        status: str,
        detail: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO retention_steps (
                    plan_id, job_id, step_name, status, detail, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(plan_id, job_id, step_name) DO UPDATE SET
                    status = excluded.status,
                    detail = excluded.detail,
                    updated_at = excluded.updated_at
                """,
                (plan_id, job_id, step_name, status, detail, time.time()),
            )

    def list_steps(self, plan_id: str) -> list[CleanupStep]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM retention_steps
                WHERE plan_id = ?
                ORDER BY updated_at, job_id, step_name
                """,
                (plan_id,),
            ).fetchall()
        return [
            CleanupStep(
                plan_id=row["plan_id"],
                job_id=row["job_id"],
                step_name=row["step_name"],
                status=row["status"],
                detail=row["detail"],
                updated_at=_iso(row["updated_at"]),
            )
            for row in rows
        ]

    def finish_plan(self, *, plan_id: str) -> CleanupPlan:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE retention_plans
                SET status = 'completed', completed_at = ?, failure_code = NULL
                WHERE plan_id = ? AND status = 'sweeping'
                """,
                (time.time(), plan_id),
            )
        return self.get_plan(plan_id)

    def fail_plan(self, *, plan_id: str, code: str) -> CleanupPlan:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE retention_plans
                SET status = 'failed', failure_code = ?
                WHERE plan_id = ? AND status = 'sweeping'
                """,
                (code[:200], plan_id),
            )
        return self.get_plan(plan_id)

    def put_hold(self, *, job_id: str, reason: str, actor: str) -> RetentionHold:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO retention_holds (job_id, reason, actor, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    reason = excluded.reason,
                    actor = excluded.actor,
                    created_at = excluded.created_at
                """,
                (job_id, reason, actor, now),
            )
        return RetentionHold(
            job_id=job_id,
            reason=reason,
            actor=actor,
            created_at=_iso(now),
        )

    def delete_hold(self, job_id: str) -> bool:
        with self._connect() as connection:
            return (
                connection.execute(
                    "DELETE FROM retention_holds WHERE job_id = ?",
                    (job_id,),
                ).rowcount
                == 1
            )

    def held_job_ids(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT job_id FROM retention_holds"
            ).fetchall()
        return {str(row["job_id"]) for row in rows}

    def list_holds(self) -> list[RetentionHold]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM retention_holds
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            RetentionHold(
                job_id=row["job_id"],
                reason=row["reason"],
                actor=row["actor"],
                created_at=_iso(row["created_at"]),
            )
            for row in rows
        ]
```

实现后检查两点：

1. `payload_json` 中保存的是 Plan 的不可变部分；状态和时间戳单独存列；
2. `retention_steps` 通过 `(plan_id, job_id, step_name)` 唯一键支持重复执行。

### 9.1 增加单主机 Sweep 互斥锁

`claim_sweep()` 允许 `sweeping` 状态在进程崩溃后重试，但不能让两个进程同时重试。单主机第一版使用 OS 文件锁最简单：进程崩溃时内核自动释放，不需要 Redis lease。

新建 `app/retention/lock.py`：

```python
from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.retention.errors import RetentionConflict


class SingleHostSweepLock:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def acquire(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            except BlockingIOError:
                raise RetentionConflict(
                    "另一个 GC sweep 正在本机执行"
                ) from None
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
```

锁文件建议使用：

```python
settings.retention_db_path.with_suffix(".gc.lock")
```

不要先执行 `claim_sweep()` 再获取文件锁；必须先拿锁，避免第二个进程把 Plan 状态改写后才发现不能执行。

---

## 十、实现不跟随符号链接的容量盘点

> **本节类型：需要新增后端代码。**

新建 `app/retention/inventory.py`：

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.retention.schemas import ManagedRootUsage, StorageSummary


@dataclass(frozen=True)
class InventoryConfig:
    roots: tuple[tuple[str, Path], ...]
    filesystem_anchor: Path
    soft_limit_bytes: int
    hard_limit_bytes: int
    min_free_bytes: int
    max_warnings: int
    destructive_gc_supported: bool


def _allocated_bytes(stat_result: os.stat_result) -> int:
    # POSIX st_blocks 以 512-byte block 表示；没有该字段时退回逻辑大小。
    blocks = getattr(stat_result, "st_blocks", None)
    return stat_result.st_size if blocks is None else int(blocks) * 512


def _scan_root(
    *,
    name: str,
    root: Path,
    warnings: list[str],
    max_warnings: int,
) -> ManagedRootUsage:
    """使用 scandir + follow_symlinks=False，绝不穿过 symlink。"""

    logical = 0
    allocated = 0
    files = 0
    directories = 0
    skipped_symlinks = 0
    errors = 0

    if not root.exists() and not root.is_symlink():
        return ManagedRootUsage(
            name=name,
            path=str(root),
            exists=False,
            logical_bytes=0,
            allocated_bytes=0,
            file_count=0,
            directory_count=0,
            skipped_symlink_count=0,
            error_count=0,
        )

    # 根本身是 symlink 时也不能进入。
    if root.is_symlink():
        return ManagedRootUsage(
            name=name,
            path=str(root),
            exists=True,
            logical_bytes=0,
            allocated_bytes=0,
            file_count=0,
            directory_count=0,
            skipped_symlink_count=1,
            error_count=0,
        )

    pending = [root]
    while pending:
        current = pending.pop()
        try:
            current_stat = current.stat(follow_symlinks=False)
            logical += current_stat.st_size
            allocated += _allocated_bytes(current_stat)
            if current.is_file():
                files += 1
                continue
            directories += 1

            with os.scandir(current) as iterator:
                for entry in iterator:
                    try:
                        if entry.is_symlink():
                            skipped_symlinks += 1
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(Path(entry.path))
                            continue
                        stat_result = entry.stat(follow_symlinks=False)
                        logical += stat_result.st_size
                        allocated += _allocated_bytes(stat_result)
                        files += 1
                    except OSError as exc:
                        errors += 1
                        if len(warnings) < max_warnings:
                            warnings.append(f"inventory entry skipped: {exc}")
        except OSError as exc:
            errors += 1
            if len(warnings) < max_warnings:
                warnings.append(f"inventory root skipped: {current}: {exc}")

    return ManagedRootUsage(
        name=name,
        path=str(root),
        exists=True,
        logical_bytes=logical,
        allocated_bytes=allocated,
        file_count=files,
        directory_count=directories,
        skipped_symlink_count=skipped_symlinks,
        error_count=errors,
    )


class StorageInventoryService:
    def __init__(self, config: InventoryConfig):
        self.config = config

    def summarize(self) -> StorageSummary:
        warnings: list[str] = []
        usages = [
            _scan_root(
                name=name,
                root=path,
                warnings=warnings,
                max_warnings=self.config.max_warnings,
            )
            for name, path in self.config.roots
        ]
        statvfs = os.statvfs(self.config.filesystem_anchor)
        total = statvfs.f_blocks * statvfs.f_frsize
        free = statvfs.f_bavail * statvfs.f_frsize
        managed_allocated = sum(item.allocated_bytes for item in usages)

        hard = (
            (
                self.config.hard_limit_bytes > 0
                and managed_allocated >= self.config.hard_limit_bytes
            )
            or free < self.config.min_free_bytes
        )
        soft = (
            self.config.soft_limit_bytes > 0
            and managed_allocated >= self.config.soft_limit_bytes
        )
        pressure = "hard" if hard else "soft" if soft else "normal"

        return StorageSummary(
            generated_at=datetime.now(timezone.utc).isoformat(),
            managed_logical_bytes=sum(item.logical_bytes for item in usages),
            managed_allocated_bytes=managed_allocated,
            filesystem_total_bytes=total,
            filesystem_free_bytes=free,
            soft_limit_bytes=self.config.soft_limit_bytes,
            hard_limit_bytes=self.config.hard_limit_bytes,
            min_free_bytes=self.config.min_free_bytes,
            pressure=pressure,
            destructive_gc_supported=self.config.destructive_gc_supported,
            roots=usages,
            warnings=warnings,
        )
```

构建 `roots` 时必须避免父子目录重复统计。例如 `storage/` 和 `storage/artifacts/` 不能同时加入。建议只列具体根和具体 DB 文件：

```python
roots = (
    ("runs", settings.runs_dir.resolve()),
    ("worker_workspaces", settings.worker_workspace_root.resolve()),
    ("workspace_staging", settings.workspace_staging_root.resolve()),
    ("export_staging", settings.job_export_staging_root.resolve()),
    ("artifact_blobs", settings.artifact_local_store_dir.resolve()),
    ("job_db", settings.job_db_path.resolve()),
    ("checkpoint_db", settings.checkpoint_db_path.resolve()),
    ("artifact_db", settings.artifact_catalog_db_path.resolve()),
    ("resource_db", settings.resource_db_path.resolve()),
    ("chat_db", settings.chat_db_path.resolve()),
    ("retention_db", settings.retention_db_path.resolve()),
)
```

如果 SQLite 使用 WAL，`database.sqlite-wal` 和 `database.sqlite-shm` 是同级文件，不会被“单文件 root”自动统计。推荐在 factory 中为每个 DB 额外加入存在的 sidecar：

```python
def sqlite_files(name: str, path: Path) -> list[tuple[str, Path]]:
    return [
        (name, path),
        (f"{name}_wal", Path(f"{path}-wal")),
        (f"{name}_shm", Path(f"{path}-shm")),
    ]
```

容量盘点不要计算每个文件的 SHA-256。Inventory 是频繁读操作，哈希全部大模型权重或数据集会造成不必要 I/O；hash 只在具体 Blob 删除前验证。

---

## 十一、实现安全路径验证与删除

> **本节类型：需要新增后端代码。**

新建 `app/retention/paths.py`：

```python
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

from app.job_runtime.schemas import JobRecord
from app.retention.errors import RetentionPathUnsafe
from app.workspace.schemas import WorkspaceBinding


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _component(value: str, field: str) -> str:
    if value in {".", ".."} or not _SAFE_COMPONENT.fullmatch(value):
        raise RetentionPathUnsafe(f"{field} 不能用作受管目录名")
    return value


def _reject_symlink_chain(path: Path, root: Path) -> None:
    current = path
    while current != root:
        if current.is_symlink():
            raise RetentionPathUnsafe(f"路径链包含 symlink：{current}")
        if root not in current.parents:
            raise RetentionPathUnsafe(f"路径逃逸受管 root：{path}")
        current = current.parent


def _tree_logical_bytes(root: Path) -> int:
    """删除前估算；不跟随 symlink，symlink 本身也不允许存在。"""

    total = 0
    pending = [root]
    while pending:
        current = pending.pop()
        if current.is_symlink():
            raise RetentionPathUnsafe(f"待删除树包含 symlink：{current}")
        with os.scandir(current) as iterator:
            for entry in iterator:
                if entry.is_symlink():
                    raise RetentionPathUnsafe(
                        f"待删除树包含 symlink：{entry.path}"
                    )
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                else:
                    total += entry.stat(follow_symlinks=False).st_size
    return total


class SafePathRemover:
    def __init__(self, *, runs_root: Path, worker_root: Path):
        self.runs_root = runs_root.resolve()
        self.worker_root = worker_root.resolve()

    def _workspace_epoch_root(self, binding: WorkspaceBinding) -> Path:
        expected = (
            self.worker_root
            / "jobs"
            / _component(binding.job_id, "job_id")
            / "epochs"
            / f"{binding.assignment_epoch:08d}"
        )
        if Path(binding.workspace_root) != expected:
            raise RetentionPathUnsafe("workspace_root 与受管派生路径不一致")
        _reject_symlink_chain(expected, self.worker_root)

        if expected.exists():
            marker = expected / ".workspace-binding.json"
            if not marker.is_file() or marker.is_symlink():
                raise RetentionPathUnsafe("workspace binding marker 缺失")
            local = WorkspaceBinding.model_validate_json(
                marker.read_text(encoding="utf-8")
            )
            identity = (
                local.assignment_id,
                local.assignment_token,
                local.manifest_hash,
                local.job_id,
                local.run_id,
            )
            expected_identity = (
                binding.assignment_id,
                binding.assignment_token,
                binding.manifest_hash,
                binding.job_id,
                binding.run_id,
            )
            if identity != expected_identity:
                raise RetentionPathUnsafe("workspace binding marker 身份不一致")
        return expected

    def validate_job_paths(
        self,
        *,
        job: JobRecord,
        bindings: list[WorkspaceBinding],
    ) -> list[Path]:
        workspace_roots = [self._workspace_epoch_root(item) for item in bindings]

        # 旧单机模式 run_dir 的唯一合法位置是 runs/<run_id>。
        legacy = self.runs_root / _component(job.run_id, "run_id")
        declared_run = Path(job.run_dir)
        binding_run_dirs = {Path(item.run_dir) for item in bindings}
        if declared_run == legacy:
            _reject_symlink_chain(legacy, self.runs_root)
            candidates = [*workspace_roots, legacy]
        elif declared_run in binding_run_dirs:
            # Phase 26 workspace 内的 run 已被 epoch root 覆盖，不重复删除。
            candidates = workspace_roots
        else:
            raise RetentionPathUnsafe("Job run_dir 不是合法 legacy/workspace 路径")

        # 去重并去掉已经被父目录覆盖的子目录。
        ordered = sorted(set(candidates), key=lambda item: len(item.parts))
        result: list[Path] = []
        for candidate in ordered:
            if any(parent == candidate or parent in candidate.parents for parent in result):
                continue
            result.append(candidate)
        return result

    def remove_tree(self, path: Path) -> int:
        """不存在视为已删除；存在时先完整安全扫描，再 rmtree。"""

        if not path.exists() and not path.is_symlink():
            return 0
        if path.is_symlink() or not path.is_dir():
            raise RetentionPathUnsafe(f"GC target 不是普通目录：{path}")
        size = _tree_logical_bytes(path)
        shutil.rmtree(path)
        return size
```

不要把 Plan 中保存的 `run_dir` 直接传给 `shutil.rmtree()`。Plan 路径只用于身份对比和审计；真正删除前必须从当前可信配置、Job record 和 WorkspaceBinding 重新派生合法路径。

如果业务确实允许 Workspace 内有 symlink，第一版 GC 仍应拒绝整个目标，而不是尝试“只删除链接不跟随”。这是保守但容易证明的安全边界。

---

## 十二、为 SQLite Store 增加 Retention 方法

> **本节类型：需要修改现有后端代码。**

### 12.1 修改 `app/job_runtime/store.py`

在 `SqliteJobStore` 类末尾、不要放进另一个方法内部，增加：

```python
    def list_retention_candidates(
        self,
        *,
        updated_before: float,
        limit: int,
    ) -> list[JobRecord]:
        bounded = max(1, min(limit, 100))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM jobs
                WHERE status IN ('succeeded', 'failed', 'cancelled')
                  AND updated_at <= ?
                ORDER BY updated_at ASC, job_id ASC
                LIMIT ?
                """,
                (updated_before, bounded),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_workspace_bindings_for_retention(
        self,
        job_id: str,
    ) -> list[WorkspaceBinding]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE job_id = ?
                ORDER BY assignment_epoch ASC
                """,
                (job_id,),
            ).fetchall()
        return [self._binding_from_row(row) for row in rows]

    def list_workspace_manifests_for_retention(
        self,
        job_id: str,
    ) -> list[WorkspaceManifest]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM workspace_manifests
                WHERE job_id = ?
                ORDER BY generation ASC
                """,
                (job_id,),
            ).fetchall()
        return [self._manifest_from_row(row) for row in rows]

    def count_workspace_blob_references(
        self,
        *,
        object_key: str,
    ) -> int:
        # SQLite JSON 查询扩展不应成为部署前提；逐行解析 manifest。
        count = 0
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT manifest_json FROM workspace_manifests"
            ).fetchall()
        for row in rows:
            manifest = WorkspaceManifest.model_validate_json(
                row["manifest_json"]
            )
            count += sum(
                1 for entry in manifest.entries if entry.object_key == object_key
            )
        return count

    def delete_job_for_retention(
        self,
        *,
        job_id: str,
        expected_version: int,
        expected_status: str,
    ) -> bool:
        if expected_status not in {"succeeded", "failed", "cancelled"}:
            raise JobConflictError("Retention 只能删除终态 Job")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status, version FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                # 幂等重试：Job 已在此前尝试中删除。
                connection.commit()
                return False
            if row["status"] != expected_status or row["version"] != expected_version:
                raise JobConflictError("Job 状态或 version 已变化，拒绝 GC")

            # SQLite 这两张表当前没有 Job 外键，必须显式删除。
            connection.execute(
                "DELETE FROM workspace_assignments WHERE job_id = ?",
                (job_id,),
            )
            connection.execute(
                "DELETE FROM workspace_manifests WHERE job_id = ?",
                (job_id,),
            )
            changed = connection.execute(
                """
                DELETE FROM jobs
                WHERE job_id = ? AND version = ? AND status = ?
                """,
                (job_id, expected_version, expected_status),
            ).rowcount
            if changed != 1:
                raise JobConflictError("Job retention fencing 失败")
            # resumes/events/commands 通过 ON DELETE CASCADE 清理。
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
```

这里必须先删除 `workspace_assignments` 和 `workspace_manifests`。当前 SQLite schema 没有把它们通过外键绑定到 `jobs`；只执行 `DELETE FROM jobs` 会留下悬空行和永久 Blob 引用。

### 12.2 修改 `app/storage/artifact_repository.py`

文件顶部增加：

```python
from app.retention.schemas import BlobReference
```

在 `SqliteArtifactRepository` 类末尾增加：

```python
    def list_blob_references_for_job(
        self,
        job_id: str,
    ) -> list[BlobReference]:
        # 必须取 versions，而不是只取 heads；历史 revision 也持有 Blob 引用。
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT backend, object_key, sha256, size_bytes
                FROM artifact_versions
                WHERE job_id = ?
                ORDER BY backend, object_key
                """,
                (job_id,),
            ).fetchall()
        return [
            BlobReference(
                backend=row["backend"],
                object_key=row["object_key"],
                sha256=row["sha256"],
                size_bytes=row["size_bytes"],
            )
            for row in rows
        ]

    def delete_job_artifacts(self, job_id: str) -> int:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            # heads 通过 FK 指向 versions，所以先删 heads。
            connection.execute(
                "DELETE FROM artifact_heads WHERE job_id = ?",
                (job_id,),
            )
            deleted = connection.execute(
                "DELETE FROM artifact_versions WHERE job_id = ?",
                (job_id,),
            ).rowcount
            connection.commit()
            return int(deleted)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def count_blob_references(
        self,
        *,
        backend: str,
        object_key: str,
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM artifact_versions
                WHERE backend = ? AND object_key = ?
                """,
                (backend, object_key),
            ).fetchone()
        return int(row["count"])
```

Artifact 删除返回的是 metadata version 数量，不是 Blob 数量；一个 Blob 可能对应多个 version。

### 12.3 修改 `app/chat/store.py`

在 `SqliteChatRepository` 类末尾增加：

```python
    def delete_job_messages(self, job_id: str) -> int:
        with self._connect() as connection:
            deleted = connection.execute(
                "DELETE FROM chat_messages WHERE job_id = ?",
                (job_id,),
            ).rowcount
        return int(deleted)
```

`CHAT_ENABLED=false` 时 factory 应注入一个 No-op 实现，而不是为了 GC 自动创建 Chat 数据库：

```python
class NoOpChatRetentionPort:
    def delete_job_messages(self, job_id: str) -> int:
        del job_id
        return 0
```

### 12.4 修改 `app/resources/repository.py`

在 `SqliteResourceRepository` 类末尾增加：

```python
    def count_blob_references(
        self,
        *,
        backend: str,
        object_key: str,
    ) -> int:
        # ResourceManifest 目前不保存 backend；当前 selected backend 必须匹配。
        if backend not in {"local", "s3"}:
            return 0
        count = 0
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT manifest_json
                FROM resources
                WHERE manifest_json IS NOT NULL
                """
            ).fetchall()
        for row in rows:
            manifest = ResourceManifest.model_validate_json(row["manifest_json"])
            if manifest.object_key == object_key:
                count += 1
        return count
```

这里仍然不增加 Resource 删除。第一版只让 Resource 参与 Blob 可达性判断。

### 12.5 Workspace Blob 转换规则

`WorkspaceManifest.entries` 没有 `backend` 字段，因为当前 WorkspaceSnapshotter 使用系统 selected BlobStore。创建 Plan 时按当前 selected backend 转换：

```python
def workspace_blob_references(
    manifests: list[WorkspaceManifest],
    *,
    selected_backend: str,
) -> list[BlobReference]:
    unique: dict[tuple[str, str], BlobReference] = {}
    for manifest in manifests:
        for entry in manifest.entries:
            key = (selected_backend, entry.object_key)
            current = BlobReference(
                backend=selected_backend,
                object_key=entry.object_key,
                sha256=entry.sha256,
                size_bytes=entry.size_bytes,
            )
            previous = unique.get(key)
            if previous is not None and previous != current:
                raise RetentionConflict(
                    "同一 Workspace object_key 出现不一致身份"
                )
            unique[key] = current
    return sorted(
        unique.values(),
        key=lambda item: (item.backend, item.object_key),
    )
```

如果未来允许一个 Manifest 混用多个 Blob backend，必须先给 `WorkspaceBlobEntry` 增加 backend/version identity，再开放 GC；不要根据 object key 格式猜测 backend。

---

## 十三、实现本地 Blob 的 compare-and-delete

> **本节类型：需要修改现有后端代码。**

修改 `app/storage/local_blob_store.py`，在 `LocalBlobStore.open()` 后增加：

```python
    def delete_if_matches(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_size: int,
    ) -> bool:
        """只有磁盘上的对象仍与 Plan 身份一致时才删除。"""

        path = self._path(object_key)
        if not path.exists() and not path.is_symlink():
            # 幂等重试：此前尝试已经删除。
            return False
        if path.is_symlink() or not path.is_file():
            raise ArtifactIntegrityError("待删除 Blob 不是普通文件")

        stat_result = path.stat(follow_symlinks=False)
        if stat_result.st_size != expected_size:
            raise ArtifactIntegrityError("待删除 Blob size 已变化")
        if sha256_file(path) != expected_sha256:
            raise ArtifactIntegrityError("待删除 Blob SHA-256 已变化")

        path.unlink()

        # 只清理空父目录，最多到 Blob root，不触碰其它对象。
        parent = path.parent
        while parent != self.root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
        return True
```

不能写成：

```python
(self.root / object_key).unlink(missing_ok=True)
```

因为这样缺少 object key 规范化、root containment、symlink、size 和 hash 检查。GC 是延迟执行，Plan 生成后对象可能被替换，必须 validate at use。

S3BlobStore 本阶段不要增加同名删除方法。即使 S3 支持 `DeleteObject`，版本化 bucket 还需要处理 version id、delete marker、Object Lock 和 retention policy；当前 Workspace/Resource manifest 也没有完整保存 object version id。

---

## 十四、封装 Checkpoint 删除

> **本节类型：需要新增后端代码。**

新建 `app/retention/checkpoint_adapter.py`：

```python
from __future__ import annotations

from typing import Any


class LangGraphCheckpointRetentionAdapter:
    def __init__(self, checkpointer: Any):
        self.checkpointer = checkpointer

    def delete_thread(self, thread_id: str) -> None:
        # SqliteSaver/PostgresSaver 已提供 delete_thread；不存在也应幂等。
        self.checkpointer.delete_thread(thread_id)
```

不要直接删除 `checkpoints.sqlite` 中猜测出来的表。LangGraph Saver 的内部 schema 由依赖版本维护，应该调用公开的 `delete_thread(thread_id)`。

第一版 destructive Sweep 已限定 SQLite，但仍使用 adapter 是为了隔离依赖；后续支持 PostgreSQL 时可以在这里增加事务和超时处理。

---

## 十五、实现 Plan、确认、预检与幂等 Sweep

> **本节类型：需要新增后端代码。**

新建 `app/retention/service.py`。下面代码给出完整主干；异常指标可在主流程通过后再接入现有 TelemetryPort。

```python
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.job_runtime.errors import JobNotFoundError
from app.job_runtime.schemas import TERMINAL_JOB_STATUSES, JobRecord
from app.retention.errors import (
    RetentionBackendUnsupported,
    RetentionConflict,
    StorageCapacityExceeded,
)
from app.retention.inventory import StorageInventoryService
from app.retention.ports import (
    ArtifactRetentionPort,
    ChatRetentionPort,
    CheckpointRetentionPort,
    DeletableBlobStore,
    JobRetentionPort,
    PathRemover,
    ResourceReferencePort,
    SweepLock,
)
from app.retention.repository import SqliteRetentionRepository
from app.retention.schemas import (
    BlobReference,
    CleanupPlan,
    CleanupResult,
    JobCleanupTarget,
    RetentionHold,
    RetentionPolicy,
    StorageSummaryView,
    WorkspaceDeleteTarget,
)
from app.workspace.schemas import WorkspaceManifest


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _workspace_blob_references(
    manifests: list[WorkspaceManifest],
    *,
    backend: str,
) -> list[BlobReference]:
    unique: dict[tuple[str, str], BlobReference] = {}
    for manifest in manifests:
        for entry in manifest.entries:
            candidate = BlobReference(
                backend=backend,
                object_key=entry.object_key,
                sha256=entry.sha256,
                size_bytes=entry.size_bytes,
            )
            key = (candidate.backend, candidate.object_key)
            previous = unique.get(key)
            if previous is not None and previous != candidate:
                raise RetentionConflict(
                    "同一 Workspace Blob key 对应不同内容身份"
                )
            unique[key] = candidate
    return sorted(
        unique.values(),
        key=lambda item: (item.backend, item.object_key),
    )


def _blob_map(
    references: list[BlobReference],
) -> dict[tuple[str, str], BlobReference]:
    result: dict[tuple[str, str], BlobReference] = {}
    for item in references:
        key = (item.backend, item.object_key)
        existing = result.get(key)
        if existing is not None and existing != item:
            raise RetentionConflict("同一 Blob key 的 size/hash 身份不一致")
        result[key] = item
    return result


class StorageQuotaGuard:
    """提交前容量保护；只拒绝新任务，不影响已有 Job。"""

    def __init__(self, inventory: StorageInventoryService):
        self.inventory = inventory

    def assert_can_submit(self) -> None:
        summary = self.inventory.summarize()
        if summary.pressure == "hard":
            raise StorageCapacityExceeded(
                "受管存储达到硬阈值或文件系统剩余空间不足；"
                "请先查看 /v1/storage/summary 并执行确认后的 GC"
            )


class RetentionService:
    def __init__(
        self,
        *,
        policy: RetentionPolicy,
        repository: SqliteRetentionRepository,
        jobs: JobRetentionPort,
        artifacts: ArtifactRetentionPort,
        chats: ChatRetentionPort,
        resources: ResourceReferencePort,
        checkpoints: CheckpointRetentionPort,
        blob_store: DeletableBlobStore | None,
        path_remover: PathRemover,
        inventory: StorageInventoryService,
        selected_blob_backend: str,
        destructive_supported: bool,
        sweep_lock: SweepLock,
    ):
        self.policy = policy
        self.repository = repository
        self.jobs = jobs
        self.artifacts = artifacts
        self.chats = chats
        self.resources = resources
        self.checkpoints = checkpoints
        self.blob_store = blob_store
        self.path_remover = path_remover
        self.inventory = inventory
        self.selected_blob_backend = selected_blob_backend
        self.destructive_supported = destructive_supported
        self.sweep_lock = sweep_lock
        self.repository.initialize()

    def storage_summary(self) -> StorageSummary:
        return self.inventory.summarize()

    def create_hold(self, *, job_id: str, reason: str, actor: str) -> RetentionHold:
        # Hold 只能绑定真实 Job，避免拼写错误制造虚假安全感。
        self.jobs.get(job_id)
        return self.repository.put_hold(
            job_id=job_id,
            reason=reason,
            actor=actor,
        )

    def delete_hold(self, job_id: str) -> bool:
        return self.repository.delete_hold(job_id)

    def list_holds(self) -> list[RetentionHold]:
        return self.repository.list_holds()

    def _target(self, job: JobRecord) -> JobCleanupTarget:
        bindings = self.jobs.list_workspace_bindings_for_retention(job.job_id)
        manifests = self.jobs.list_workspace_manifests_for_retention(job.job_id)
        paths = self.path_remover.validate_job_paths(job=job, bindings=bindings)

        workspace_targets = [
            WorkspaceDeleteTarget(
                path=str(Path(binding.workspace_root)),
                assignment_epoch=binding.assignment_epoch,
                assignment_token_sha256=_token_hash(binding.assignment_token),
                manifest_hash=binding.manifest_hash,
            )
            for binding in bindings
        ]
        artifact_blobs = self.artifacts.list_blob_references_for_job(job.job_id)
        workspace_blobs = _workspace_blob_references(
            manifests,
            backend=self.selected_blob_backend,
        )

        # 估算不对共享 key 重复求和；路径字节在 Sweep 前安全扫描时计算。
        estimated = sum(
            item.size_bytes
            for item in _blob_map([*artifact_blobs, *workspace_blobs]).values()
        )
        return JobCleanupTarget(
            job_id=job.job_id,
            thread_id=job.thread_id,
            run_id=job.run_id,
            run_dir=job.run_dir,
            job_version=job.version,
            job_status=job.status,
            job_updated_at=job.updated_at,
            workspace_manifest_id=job.workspace_manifest_id,
            workspace_manifest_generation=job.workspace_manifest_generation,
            workspace_targets=workspace_targets,
            artifact_blobs=artifact_blobs,
            workspace_blobs=workspace_blobs,
            estimated_logical_bytes=estimated,
        )

    def create_plan(self) -> CleanupPlan:
        cutoff = time.time() - self.policy.job_retention_seconds
        held = self.repository.held_job_ids()
        # 多取一些，避免前几项都被 hold 后返回空计划。
        candidates = self.jobs.list_retention_candidates(
            updated_before=cutoff,
            limit=min(100, self.policy.max_jobs_per_plan * 4),
        )
        selected = [job for job in candidates if job.job_id not in held][
            : self.policy.max_jobs_per_plan
        ]

        created = datetime.now(timezone.utc)
        expires = created + timedelta(seconds=self.policy.plan_ttl_seconds)
        plan_id = f"gc_{uuid4().hex}"
        hash_payload = {
            "plan_id": plan_id,
            "policy": self.policy.model_dump(mode="json"),
            "targets": [self._target(job).model_dump(mode="json") for job in selected],
            "created_at": created.isoformat(),
            "expires_at": expires.isoformat(),
        }
        plan = CleanupPlan(
            **hash_payload,
            status="planned",
            plan_hash=_sha256(hash_payload),
        )
        return self.repository.create_plan(plan)

    def get_plan(self, plan_id: str) -> CleanupPlan:
        return self.repository.get_plan(plan_id)

    def confirm_plan(self, *, plan_id: str, plan_hash: str) -> CleanupPlan:
        return self.repository.confirm_plan(
            plan_id=plan_id,
            plan_hash=plan_hash,
        )

    def _assert_plan_hash(self, plan: CleanupPlan) -> None:
        payload = {
            "plan_id": plan.plan_id,
            "policy": plan.policy.model_dump(mode="json"),
            "targets": [item.model_dump(mode="json") for item in plan.targets],
            "created_at": plan.created_at,
            "expires_at": plan.expires_at,
        }
        if _sha256(payload) != plan.plan_hash:
            raise RetentionConflict("持久化 Plan payload 与 hash 不一致")

    def _assert_target_current(self, target: JobCleanupTarget) -> None:
        current = self.jobs.get(target.job_id)
        identity = (
            current.thread_id,
            current.run_id,
            current.run_dir,
            current.version,
            current.status,
            current.updated_at,
            current.workspace_manifest_id,
            current.workspace_manifest_generation,
        )
        expected = (
            target.thread_id,
            target.run_id,
            target.run_dir,
            target.job_version,
            target.job_status,
            target.job_updated_at,
            target.workspace_manifest_id,
            target.workspace_manifest_generation,
        )
        if identity != expected or current.status not in TERMINAL_JOB_STATUSES:
            raise RetentionConflict(f"Job 身份已变化：{target.job_id}")

        bindings = self.jobs.list_workspace_bindings_for_retention(target.job_id)
        paths = self.path_remover.validate_job_paths(job=current, bindings=bindings)
        planned_paths = {item.path for item in target.workspace_targets}
        current_workspace_paths = {item.workspace_root for item in bindings}
        if planned_paths != current_workspace_paths:
            raise RetentionConflict("Workspace target 集合已变化")

        current_tokens = {
            (item.assignment_epoch, _token_hash(item.assignment_token), item.manifest_hash)
            for item in bindings
        }
        planned_tokens = {
            (
                item.assignment_epoch,
                item.assignment_token_sha256,
                item.manifest_hash,
            )
            for item in target.workspace_targets
        }
        if current_tokens != planned_tokens:
            raise RetentionConflict("Workspace binding 身份已变化")

        # validate_job_paths 已重新派生 legacy/workspace run roots。
        del paths

        current_artifacts = self.artifacts.list_blob_references_for_job(target.job_id)
        current_manifests = self.jobs.list_workspace_manifests_for_retention(
            target.job_id
        )
        current_workspace_blobs = _workspace_blob_references(
            current_manifests,
            backend=self.selected_blob_backend,
        )
        if _blob_map(current_artifacts) != _blob_map(target.artifact_blobs):
            raise RetentionConflict("Artifact 引用快照已变化")
        if _blob_map(current_workspace_blobs) != _blob_map(target.workspace_blobs):
            raise RetentionConflict("Workspace Blob 引用快照已变化")

    def _preflight(self, plan: CleanupPlan) -> None:
        if not self.destructive_supported:
            raise RetentionBackendUnsupported(
                "第一版 Sweep 只支持 SQLite control plane + LocalBlobStore"
            )
        if self.policy.delete_local_blobs and self.blob_store is None:
            raise RetentionBackendUnsupported("当前 BlobStore 不支持安全删除")
        self._assert_plan_hash(plan)

        held = self.repository.held_job_ids()
        for target in plan.targets:
            if any(
                blob.backend != self.selected_blob_backend
                for blob in [*target.artifact_blobs, *target.workspace_blobs]
            ):
                raise RetentionBackendUnsupported(
                    "Plan 含有非当前 LocalBlobStore 的历史 Blob；拒绝部分清理"
                )
            if target.job_id in held:
                raise RetentionConflict(f"Job 已被 retention hold：{target.job_id}")

            # 重试时 job_metadata 已完成，Job 不存在是预期状态。
            if self.repository.step_completed(
                plan_id=plan.plan_id,
                job_id=target.job_id,
                step_name="job_metadata",
            ):
                continue
            try:
                self._assert_target_current(target)
            except JobNotFoundError:
                # 处理“DELETE 已提交但 journal 还没写入”这一窄窗口。
                prerequisites = (
                    "chat",
                    "checkpoint",
                    "artifact_metadata",
                    "filesystem",
                )
                if not all(
                    self.repository.step_completed(
                        plan_id=plan.plan_id,
                        job_id=target.job_id,
                        step_name=name,
                    )
                    for name in prerequisites
                ):
                    raise RetentionConflict(
                        "Job 缺失但前置清理 journal 不完整，拒绝推断"
                    ) from None
                self.repository.record_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="job_metadata",
                    status="completed",
                    detail='{"inferred_after_crash":true}',
                )

    def _run_step(
        self,
        *,
        plan_id: str,
        job_id: str,
        step_name: str,
        operation,
    ) -> object | None:
        if self.repository.step_completed(
            plan_id=plan_id,
            job_id=job_id,
            step_name=step_name,
        ):
            return None
        try:
            value = operation()
            self.repository.record_step(
                plan_id=plan_id,
                job_id=job_id,
                step_name=step_name,
                status="completed",
                detail=_canonical({"result": value}),
            )
            return value
        except Exception as exc:
            self.repository.record_step(
                plan_id=plan_id,
                job_id=job_id,
                step_name=step_name,
                status="failed",
                detail=_canonical({"error_type": type(exc).__name__}),
            )
            raise

    def _remove_paths(self, target: JobCleanupTarget) -> int:
        # 此处重新读当前身份，不使用 API 提交的路径。
        job = self.jobs.get(target.job_id)
        bindings = self.jobs.list_workspace_bindings_for_retention(target.job_id)
        roots = self.path_remover.validate_job_paths(job=job, bindings=bindings)
        return sum(self.path_remover.remove_tree(path) for path in roots)

    def _live_blob_references(self, blob: BlobReference) -> int:
        return (
            self.artifacts.count_blob_references(
                backend=blob.backend,
                object_key=blob.object_key,
            )
            + self.jobs.count_workspace_blob_references(
                object_key=blob.object_key
            )
            + self.resources.count_blob_references(
                backend=blob.backend,
                object_key=blob.object_key,
            )
        )

    def _result_from_journal(self, plan: CleanupPlan) -> CleanupResult:
        steps = self.repository.list_steps(plan.plan_id)
        reclaimed = 0
        deleted_blobs = 0
        retained_shared = 0
        completed_jobs: set[str] = set()
        for step in steps:
            if step.status != "completed":
                continue
            detail = json.loads(step.detail or "{}")
            if step.step_name == "filesystem":
                value = detail.get("result")
                reclaimed += value if isinstance(value, int) else 0
            elif step.step_name == "job_metadata":
                completed_jobs.add(step.job_id)
            elif step.step_name.startswith("blob:"):
                if detail.get("deleted") is True:
                    deleted_blobs += 1
                    reclaimed += int(detail.get("size_bytes", 0))
                elif int(detail.get("live_references", 0)) > 0:
                    retained_shared += 1
        return CleanupResult(
            plan=plan,
            deleted_jobs=len(completed_jobs),
            deleted_blob_count=deleted_blobs,
            retained_shared_blob_count=retained_shared,
            reclaimed_logical_bytes=reclaimed,
            steps=steps,
        )

    def sweep(self, *, plan_id: str, plan_hash: str) -> CleanupResult:
        # 文件锁覆盖读取、claim、preflight 和全部 delete。
        with self.sweep_lock.acquire():
            existing = self.repository.get_plan(plan_id)
            if existing.plan_hash != plan_hash:
                raise RetentionConflict("Plan hash 不匹配")
            if existing.status == "completed":
                return self._result_from_journal(existing)
            return self._sweep_locked(plan_id=plan_id, plan_hash=plan_hash)

    def _sweep_locked(
        self,
        *,
        plan_id: str,
        plan_hash: str,
    ) -> CleanupResult:
        plan = self.repository.claim_sweep(
            plan_id=plan_id,
            plan_hash=plan_hash,
        )
        try:
            # 在第一次删除之前校验所有尚未完成的 target。
            self._preflight(plan)

            all_blobs = _blob_map(
                [
                    blob
                    for target in plan.targets
                    for blob in [*target.artifact_blobs, *target.workspace_blobs]
                ]
            )

            for target in plan.targets:
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="chat",
                    operation=lambda target=target: self.chats.delete_job_messages(
                        target.job_id
                    ),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="checkpoint",
                    operation=lambda target=target: self.checkpoints.delete_thread(
                        target.thread_id
                    ),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="artifact_metadata",
                    operation=lambda target=target: self.artifacts.delete_job_artifacts(
                        target.job_id
                    ),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="filesystem",
                    operation=lambda target=target: self._remove_paths(target),
                )
                self._run_step(
                    plan_id=plan.plan_id,
                    job_id=target.job_id,
                    step_name="job_metadata",
                    operation=lambda target=target: self.jobs.delete_job_for_retention(
                        job_id=target.job_id,
                        expected_version=target.job_version,
                        expected_status=target.job_status,
                    ),
                )
            # 所有 Job metadata 引用移除后，才能做全局 recount。
            for blob in all_blobs.values():
                step_name = "blob:" + _sha256(
                    {"backend": blob.backend, "object_key": blob.object_key}
                )[:24]
                if self.repository.step_completed(
                    plan_id=plan.plan_id,
                    job_id="__global__",
                    step_name=step_name,
                ):
                    continue
                references = self._live_blob_references(blob)
                if references > 0 or not self.policy.delete_local_blobs:
                    self.repository.record_step(
                        plan_id=plan.plan_id,
                        job_id="__global__",
                        step_name=step_name,
                        status="completed",
                        detail=_canonical(
                            {
                                "deleted": False,
                                "live_references": references,
                                "size_bytes": blob.size_bytes,
                            }
                        ),
                    )
                    continue

                assert self.blob_store is not None
                removed = self.blob_store.delete_if_matches(
                    object_key=blob.object_key,
                    expected_sha256=blob.sha256,
                    expected_size=blob.size_bytes,
                )
                self.repository.record_step(
                    plan_id=plan.plan_id,
                    job_id="__global__",
                    step_name=step_name,
                    status="completed",
                    detail=_canonical(
                        {
                            "deleted": removed,
                            "live_references": 0,
                            "size_bytes": blob.size_bytes,
                        }
                    ),
                )

            completed = self.repository.finish_plan(plan_id=plan.plan_id)
            # 从 durable journal 重建最终结果，重启和 replay 语义一致。
            return self._result_from_journal(completed)
        except Exception as exc:
            self.repository.fail_plan(
                plan_id=plan.plan_id,
                code=type(exc).__name__,
            )
            raise
```

### 15.1 关于重试结果计数

`_result_from_journal()` 从 durable step detail 重建整个 Plan 的累计结果，不依赖本次进程内计数。因此进程重启、失败重试和 completed replay 返回一致的统计。若以后新增步骤指标，先把有界 JSON 写入 step detail，再扩展这个 reducer。

### 15.2 空 Plan 的行为

没有候选时仍可创建 targets 为空的 Plan，用于明确记录“当前没有满足策略的 Job”。确认后 Sweep 会直接完成且不删除任何内容。这比返回 `404` 更容易测试，也方便 Web 展示。

### 15.3 Hold 与已确认 Plan

用户在 Plan 确认后、Sweep 前新增 Hold，`_preflight()` 会重新检查并拒绝执行。Hold 的优先级高于旧确认；用户必须移除 Hold 并重新生成 Plan，不能继续使用旧 Plan。

---

## 十六、实现 Factory 与 Backend Fail-Closed

> **本节类型：需要新增后端代码。**

新建 `app/retention/factory.py`：

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.chat.store import SqliteChatRepository
from app.config import settings
from app.memory.checkpoint import build_checkpointer
from app.resources.repository import SqliteResourceRepository
from app.retention.checkpoint_adapter import (
    LangGraphCheckpointRetentionAdapter,
)
from app.retention.inventory import InventoryConfig, StorageInventoryService
from app.retention.lock import SingleHostSweepLock
from app.retention.paths import SafePathRemover
from app.retention.repository import SqliteRetentionRepository
from app.retention.schemas import RetentionPolicy
from app.retention.service import (
    RetentionService,
    StorageQuotaGuard,
)
from app.storage.factory import ArtifactStorageBundle
from app.storage.local_blob_store import LocalBlobStore


class NoOpChatRetentionPort:
    def delete_job_messages(self, job_id: str) -> int:
        del job_id
        return 0


def _sqlite_roots(name: str, path: Path) -> list[tuple[str, Path]]:
    return [
        (name, path),
        (f"{name}_wal", Path(f"{path}-wal")),
        (f"{name}_shm", Path(f"{path}-shm")),
    ]


def build_inventory(*, destructive_supported: bool) -> StorageInventoryService:
    roots: list[tuple[str, Path]] = [
        ("runs", settings.runs_dir.resolve()),
        ("worker_workspaces", settings.worker_workspace_root.resolve()),
        ("workspace_staging", settings.workspace_staging_root.resolve()),
        ("export_staging", settings.job_export_staging_root.resolve()),
        ("artifact_blobs", settings.artifact_local_store_dir.resolve()),
    ]
    for name, path in (
        ("job_db", settings.job_db_path.resolve()),
        ("checkpoint_db", settings.checkpoint_db_path.resolve()),
        ("artifact_db", settings.artifact_catalog_db_path.resolve()),
        ("resource_db", settings.resource_db_path.resolve()),
        ("chat_db", settings.chat_db_path.resolve()),
        ("retention_db", settings.retention_db_path.resolve()),
    ):
        roots.extend(_sqlite_roots(name, path))

    return StorageInventoryService(
        InventoryConfig(
            roots=tuple(roots),
            filesystem_anchor=settings.runs_dir.resolve(),
            soft_limit_bytes=settings.storage_soft_limit_bytes,
            hard_limit_bytes=settings.storage_hard_limit_bytes,
            min_free_bytes=settings.storage_min_free_bytes,
            max_warnings=settings.storage_inventory_max_warnings,
            destructive_gc_supported=destructive_supported,
        )
    )


@dataclass(frozen=True)
class RetentionBundle:
    inventory: StorageInventoryService
    quota_guard: StorageQuotaGuard
    service: RetentionService | None


def build_retention(
    *,
    job_store,
    artifact_storage: ArtifactStorageBundle,
) -> RetentionBundle:
    destructive_supported = (
        settings.retention_enabled
        and settings.job_store_backend == "sqlite"
        and settings.checkpoint_backend == "sqlite"
        and settings.artifact_blob_backend == "local"
    )
    inventory = build_inventory(destructive_supported=destructive_supported)

    quota_guard = StorageQuotaGuard(inventory)
    if not destructive_supported:
        # PostgreSQL/S3 仍可查看 summary 和受 quota guard 保护，
        # 但不会构造一个伪装可删除的 service。
        return RetentionBundle(
            inventory=inventory,
            quota_guard=quota_guard,
            service=None,
        )

    # 只有 LocalBlobStore 才能进入这里。
    if not isinstance(artifact_storage.selected_store, LocalBlobStore):
        raise RuntimeError("Local backend 与 concrete BlobStore 不一致")
    deletable = artifact_storage.selected_store
    chat = (
        SqliteChatRepository(settings.chat_db_path)
        if settings.chat_enabled or settings.chat_db_path.exists()
        else NoOpChatRetentionPort()
    )
    if isinstance(chat, SqliteChatRepository):
        chat.initialize()

    resource_repository = SqliteResourceRepository(settings.resource_db_path)
    resource_repository.initialize()
    repository = SqliteRetentionRepository(settings.retention_db_path)
    service = RetentionService(
        policy=RetentionPolicy(
            job_retention_seconds=settings.retention_job_days * 86400,
            max_jobs_per_plan=settings.retention_plan_max_jobs,
            plan_ttl_seconds=settings.retention_plan_ttl_seconds,
            delete_local_blobs=settings.retention_local_blob_delete_enabled,
        ),
        repository=repository,
        jobs=job_store,
        artifacts=artifact_storage.repository,
        chats=chat,
        resources=resource_repository,
        checkpoints=LangGraphCheckpointRetentionAdapter(build_checkpointer()),
        blob_store=deletable,
        path_remover=SafePathRemover(
            runs_root=settings.runs_dir,
            worker_root=settings.worker_workspace_root,
        ),
        inventory=inventory,
        selected_blob_backend=artifact_storage.selected_store.backend_name,
        destructive_supported=destructive_supported,
        sweep_lock=SingleHostSweepLock(
            settings.retention_db_path.with_suffix(".gc.lock")
        ),
    )
    return RetentionBundle(
        inventory=inventory,
        quota_guard=quota_guard,
        service=service,
    )
```

这个 factory 刻意拆开“盘点能力”和“破坏性清理能力”：

```python
bundle.inventory       # 所有 backend 都可用
bundle.quota_guard     # 所有 backend 都可用
bundle.service         # 只有 SQLite + Local 非 None
```

API 的 `/v1/storage/summary` 总是挂载；若 destructive service 为 `None`，Plan/confirm/sweep 返回 `501 RETENTION_BACKEND_UNSUPPORTED`。不要为了让类型检查通过，把 PostgreSQL/S3 强制 cast 成删除端口。

---

## 十七、把配额保护接到统一 Job 提交入口

> **本节类型：需要修改现有后端代码。**

只在 FastAPI `POST /jobs` 中检查配额是不完整的，因为 `python -m app.main submit-job` 会绕过路由。正确位置是 `JobService.submit()`。

### 17.1 修改 `app/job_runtime/service.py`

在 import 区域增加：

```python
from typing import Protocol


class CapacityGuard(Protocol):
    def assert_can_submit(self) -> None: ...
```

修改构造函数，保留上下文：

```python
class JobService:
    def __init__(
        self,
        store: JobStore,
        *,
        workspace_snapshotter: WorkspaceSnapshotter,
        telemetry: TelemetryPort | None = None,
        capacity_guard: CapacityGuard | None = None,
    ):
        self.store = store
        self.workspace_snapshotter = workspace_snapshotter
        self.capacity_guard = capacity_guard
        self.telemetry = (
            telemetry
            if telemetry is not None
            else build_telemetry_runtime().telemetry
        )
        self.store.initialize()
```

在 `submit()` 最开头、生成 Job/Workspace snapshot 之前增加：

```python
    def submit(
        self,
        *,
        request: JobRequest,
        thread_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[JobRecord, bool]:
        if self.capacity_guard is not None:
            self.capacity_guard.assert_can_submit()

        job_id = f"job_{uuid4().hex}"
        # 保留后续原有代码……
```

一定要在 `_build_initial_manifest()` 前检查。Workspace snapshot 可能复制仓库/PDF 并写入 BlobStore；若先 snapshot 再检查容量，拒绝提交本身还会继续消耗空间。

需要知道这个第一版取舍：磁盘处于 hard pressure 时，相同 `Idempotency-Key` 的提交重试也会被 507 拒绝。已有 Job 不会丢失，客户端仍可用 `GET /jobs/{job_id}` 查询。后续若要严格保持 mutation replay，应在 JobStore 增加 `find_by_idempotency_key + request identity`，先返回已接受请求，再只对全新请求执行 capacity guard。

### 17.2 修改 `build_job_service()`

原函数已经创建 storage 和 JobStore。调整为复用同一份对象：

```python
def build_job_service() -> JobService:
    """CLI、API 和 Worker 共用 Store/Blob/Quota 配置。"""

    from app.retention.factory import build_inventory
    from app.retention.service import StorageQuotaGuard
    from app.storage.factory import build_artifact_storage

    storage = build_artifact_storage()
    store = build_job_store()
    inventory = build_inventory(
        destructive_supported=(
            settings.retention_enabled
            and settings.job_store_backend == "sqlite"
            and settings.checkpoint_backend == "sqlite"
            and settings.artifact_blob_backend == "local"
        )
    )
    return JobService(
        store,
        workspace_snapshotter=WorkspaceSnapshotter(
            blob_store=storage.selected_store
        ),
        capacity_guard=(
            StorageQuotaGuard(inventory)
            if settings.retention_enabled
            else None
        ),
    )
```

独立 CLI/Worker 构造路径只需要 Inventory + QuotaGuard，不应为了提交检查额外打开 Checkpointer 和 Retention Repository。API 还要提供 Plan/Sweep，因此下一节会在 app composition root 中创建一次完整 bundle，并把其中同一个 QuotaGuard 注入 JobService。

---

## 十八、增加 Retention API 与稳定错误语义

> **本节类型：需要新增和修改 API 代码。**

### 18.1 新建 `app/api/retention_routes.py`

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.auth import require_api_auth
from app.retention.errors import RetentionBackendUnsupported
from app.retention.schemas import (
    CleanupPlanView,
    CleanupResultView,
    HoldRequest,
    PlanConfirmRequest,
    RetentionHold,
    StorageSummary,
)


router = APIRouter(prefix="/v1")
Actor = Annotated[str, Depends(require_api_auth)]


def _bundle(request: Request):
    return request.app.state.retention_bundle


def _service(request: Request):
    service = _bundle(request).service
    if service is None:
        raise RetentionBackendUnsupported(
            "当前 backend 只支持容量盘点，不支持 destructive GC"
        )
    return service


@router.get("/storage/summary", response_model=StorageSummaryView)
def storage_summary(request: Request, _actor: Actor) -> StorageSummaryView:
    return StorageSummaryView.from_summary(
        _bundle(request).inventory.summarize()
    )


@router.post("/retention/plans", response_model=CleanupPlanView, status_code=201)
def create_plan(request: Request, _actor: Actor) -> CleanupPlanView:
    # body 不接受 job_id/path/object_key；候选完全由服务端 policy 计算。
    return CleanupPlanView.from_plan(_service(request).create_plan())


@router.get("/retention/plans/{plan_id}", response_model=CleanupPlanView)
def get_plan(plan_id: str, request: Request, _actor: Actor) -> CleanupPlanView:
    return CleanupPlanView.from_plan(_service(request).get_plan(plan_id))


@router.post(
    "/retention/plans/{plan_id}/confirm",
    response_model=CleanupPlanView,
)
def confirm_plan(
    plan_id: str,
    body: PlanConfirmRequest,
    request: Request,
    _actor: Actor,
) -> CleanupPlanView:
    return CleanupPlanView.from_plan(
        _service(request).confirm_plan(
            plan_id=plan_id,
            plan_hash=body.plan_hash,
        )
    )


@router.post(
    "/retention/plans/{plan_id}/sweep",
    response_model=CleanupResultView,
)
def sweep_plan(
    plan_id: str,
    body: PlanConfirmRequest,
    request: Request,
    _actor: Actor,
) -> CleanupResultView:
    return CleanupResultView.from_result(
        _service(request).sweep(
            plan_id=plan_id,
            plan_hash=body.plan_hash,
        )
    )


@router.get("/retention/holds", response_model=list[RetentionHold])
def list_holds(request: Request, _actor: Actor) -> list[RetentionHold]:
    return _service(request).list_holds()


@router.put("/retention/holds/{job_id}", response_model=RetentionHold)
def put_hold(
    job_id: str,
    body: HoldRequest,
    request: Request,
    actor: Actor,
) -> RetentionHold:
    return _service(request).create_hold(
        job_id=job_id,
        reason=body.reason,
        actor=actor,
    )


@router.delete("/retention/holds/{job_id}", status_code=204)
def delete_hold(job_id: str, request: Request, _actor: Actor) -> None:
    _service(request).delete_hold(job_id)
```

Plan 创建接口故意没有请求体，避免用户提交路径或“指定一个当前正在运行的 Job 强制删除”。若后续需要用户选择候选，应采用：服务端先返回 eligible candidate IDs，客户端只能提交子集，服务端再对每个 ID 重做 eligibility 校验并绑定 hash。

### 18.2 修改 `app/api/errors.py`

增加 import：

```python
from app.retention.errors import (
    RetentionBackendUnsupported,
    RetentionConflict,
    RetentionNotFound,
    RetentionPathUnsafe,
    StorageCapacityExceeded,
)
```

在 `install_error_handlers()` 内增加：

```python
    @app.exception_handler(RetentionNotFound)
    async def handle_retention_not_found(
        request: Request,
        exc: RetentionNotFound,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="RETENTION_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(RetentionConflict)
    async def handle_retention_conflict(
        request: Request,
        exc: RetentionConflict,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="RETENTION_CONFLICT",
            message=str(exc),
        )

    @app.exception_handler(RetentionPathUnsafe)
    async def handle_retention_path_unsafe(
        request: Request,
        exc: RetentionPathUnsafe,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="RETENTION_PATH_UNSAFE",
            message=str(exc),
        )

    @app.exception_handler(RetentionBackendUnsupported)
    async def handle_retention_backend_unsupported(
        request: Request,
        exc: RetentionBackendUnsupported,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=501,
            code="RETENTION_BACKEND_UNSUPPORTED",
            message=str(exc),
        )

    @app.exception_handler(StorageCapacityExceeded)
    async def handle_storage_capacity(
        request: Request,
        exc: StorageCapacityExceeded,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=507,
            code="STORAGE_CAPACITY_EXCEEDED",
            message=str(exc),
        )
```

`507 Insufficient Storage` 比 422 或 500 更准确：请求本身可能完全合法，只是当前服务没有足够受管容量接收新任务。

### 18.3 修改 `app/api/app.py`

文件顶部增加：

```python
from app.api.retention_routes import router as retention_router
from app.retention.factory import RetentionBundle, build_retention
```

给 factory 增加可测试注入参数：

```python
def create_api_app(
    *,
    job_service: JobService | None = None,
    artifact_catalog: ArtifactCatalog | None = None,
    artifact_delivery_service: ArtifactDeliveryService | None = None,
    api_token: str | None = None,
    service_host: Any | None = None,
    chat_service: ChatService | None = None,
    retention_bundle: RetentionBundle | None = None,
) -> FastAPI:
```

调整 storage/job service 构建片段。关键是只构造一次 storage、store 和 retention：

```python
    storage = None
    if job_service is None or artifact_catalog is None or retention_bundle is None:
        storage = build_artifact_storage()

    if job_service is None:
        from app.job_runtime.factory import build_job_store
        from app.workspace.snapshot import WorkspaceSnapshotter

        assert storage is not None
        job_store = build_job_store()
        if retention_bundle is None:
            retention_bundle = build_retention(
                job_store=job_store,
                artifact_storage=storage,
            )
        job_service = JobService(
            job_store,
            workspace_snapshotter=WorkspaceSnapshotter(
                blob_store=storage.selected_store
            ),
            telemetry=telemetry,
            capacity_guard=(
                retention_bundle.quota_guard
                if settings.retention_enabled
                else None
            ),
        )

    selected_job_service = job_service

    if retention_bundle is None:
        # 现有 API 测试若注入 fake JobService，也应显式注入 fake bundle。
        # 不要让测试悄悄访问开发机真实 retention DB。
        raise RuntimeError(
            "注入 job_service 时必须同时注入 retention_bundle"
        )
```

如果一次修改所有旧 API 测试成本过高，可以为测试提供 `build_disabled_retention_bundle(tmp_path)` fixture，并统一传入；不要在 app factory 中默认连接真实 `retention/retention.sqlite`。

在 app state 区域增加：

```python
    app.state.retention_bundle = retention_bundle
```

在 router 挂载区域增加，且仍在 SPA mount 之前：

```python
    app.include_router(router)
    app.include_router(resource_router)
    app.include_router(ui_router)
    app.include_router(chat_router)
    app.include_router(retention_router)
    install_error_handlers(app)
```

在 readiness probes 中加入 retention ledger。只有 destructive service 存在时才检查：

```python
    if retention_bundle.service is not None:
        probes.append(
            ReadinessProbe(
                name="retention_db_readiness",
                is_critical=False,
                check=lambda: (
                    retention_bundle.service.repository.initialize()
                    or "ready"
                ),
                timeout_seconds=settings.readiness_timeout_seconds,
            )
        )
```

更干净的实现是给 `SqliteRetentionRepository` 增加 `ping()`，readiness 调用 `ping()`，不要长期用 `initialize()` 代替健康检查：

```python
def ping(self) -> None:
    with self._connect() as connection:
        connection.execute("SELECT 1").fetchone()
```

---

## 十九、增加 CLI 运维入口

> **本节类型：需要修改现有 CLI 代码。**

修改 `app/main.py`，增加 import：

```python
from app.job_runtime.factory import build_job_store
from app.retention.errors import RetentionError
from app.retention.factory import build_retention
```

增加统一 builder，确保 CLI 使用和 API 一样的配置：

```python
def _build_retention_bundle():
    storage = build_artifact_storage()
    store = build_job_store()
    return build_retention(
        job_store=store,
        artifact_storage=storage,
    )
```

增加以下命令：

```python
@app.command("storage-summary")
def storage_summary_command():
    """只盘点，不删除任何数据。"""

    bundle = _build_retention_bundle()
    print(bundle.inventory.summarize().model_dump(mode="json"))


@app.command("gc-plan")
def gc_plan_command():
    """创建不可变 cleanup plan；该命令永不删除。"""

    bundle = _build_retention_bundle()
    if bundle.service is None:
        raise typer.BadParameter("当前 backend 不支持 destructive GC")
    plan = bundle.service.create_plan()
    print(plan.model_dump(mode="json"))


@app.command("gc-confirm")
def gc_confirm_command(
    plan_id: str,
    plan_hash: str = typer.Option(..., "--plan-hash"),
):
    """确认完全相同的 Plan；仍不执行删除。"""

    bundle = _build_retention_bundle()
    if bundle.service is None:
        raise typer.BadParameter("当前 backend 不支持 destructive GC")
    try:
        plan = bundle.service.confirm_plan(
            plan_id=plan_id,
            plan_hash=plan_hash,
        )
    except RetentionError as exc:
        raise typer.BadParameter(str(exc)) from None
    print(plan.model_dump(mode="json"))


@app.command("gc-sweep")
def gc_sweep_command(
    plan_id: str,
    plan_hash: str = typer.Option(..., "--plan-hash"),
):
    """执行已确认 Plan；失败后使用同一 hash 重试。"""

    bundle = _build_retention_bundle()
    if bundle.service is None:
        raise typer.BadParameter("当前 backend 不支持 destructive GC")
    try:
        result = bundle.service.sweep(
            plan_id=plan_id,
            plan_hash=plan_hash,
        )
    except RetentionError as exc:
        raise typer.BadParameter(str(exc)) from None
    print(result.model_dump(mode="json"))


@app.command("retention-hold")
def retention_hold_command(
    job_id: str,
    reason: str = typer.Option(..., "--reason"),
):
    bundle = _build_retention_bundle()
    if bundle.service is None:
        raise typer.BadParameter("当前 backend 不支持 retention hold")
    hold = bundle.service.create_hold(
        job_id=job_id,
        reason=reason,
        actor="cli",
    )
    print(hold.model_dump(mode="json"))


@app.command("retention-release")
def retention_release_command(job_id: str):
    bundle = _build_retention_bundle()
    if bundle.service is None:
        raise typer.BadParameter("当前 backend 不支持 retention hold")
    print({"removed": bundle.service.delete_hold(job_id)})
```

CLI 不提供 `--path`、`--object-key`、`--force-running` 或跳过 hash 的选项。运维便利性不能突破领域安全协议。

---

## 二十、增加最小 Web Storage 面板

> **本节类型：需要修改前端代码。前端保持简单，后端协议是重点。**

### 20.1 修改 `web/src/api/types.ts`

增加：

```typescript
export type ManagedRootUsage = {
  name: string;
  exists: boolean;
  logical_bytes: number;
  allocated_bytes: number;
  file_count: number;
  directory_count: number;
  skipped_symlink_count: number;
  error_count: number;
};

export type StorageSummary = {
  generated_at: string;
  managed_logical_bytes: number;
  managed_allocated_bytes: number;
  filesystem_total_bytes: number;
  filesystem_free_bytes: number;
  soft_limit_bytes: number;
  hard_limit_bytes: number;
  min_free_bytes: number;
  pressure: "normal" | "soft" | "hard";
  destructive_gc_supported: boolean;
  roots: ManagedRootUsage[];
  warnings: string[];
};

export type CleanupTarget = {
  job_id: string;
  run_id: string;
  job_status: "succeeded" | "failed" | "cancelled";
  job_updated_at: string;
  estimated_logical_bytes: number;
};

export type CleanupPlan = {
  plan_id: string;
  status: "planned" | "confirmed" | "sweeping" | "completed" | "failed";
  plan_hash: string;
  targets: CleanupTarget[];
  created_at: string;
  expires_at: string;
  failure_code: string | null;
};

export type CleanupResult = {
  plan: CleanupPlan;
  deleted_jobs: number;
  deleted_blob_count: number;
  retained_shared_blob_count: number;
  reclaimed_logical_bytes: number;
};
```

前端不需要声明或展示 Workspace token hash、Blob object key 和宿主机绝对路径。后端 response model 最好进一步拆成 `CleanupPlanView`，只公开 Job ID、状态、时间和估算大小；上面的最小类型只消费需要字段，TypeScript 会忽略额外 JSON 字段。

### 20.2 修改 `web/src/api/client.ts`

增加 type import，并在 `api` 中增加：

```typescript
  storageSummary() {
    return request<StorageSummary>("/v1/storage/summary");
  },

  createCleanupPlan() {
    return request<CleanupPlan>("/v1/retention/plans", {
      method: "POST",
    });
  },

  confirmCleanupPlan(plan: CleanupPlan) {
    return request<CleanupPlan>(
      `/v1/retention/plans/${encodeURIComponent(plan.plan_id)}/confirm`,
      {
        method: "POST",
        body: JSON.stringify({ plan_hash: plan.plan_hash }),
      },
    );
  },

  sweepCleanupPlan(plan: CleanupPlan) {
    return request<CleanupResult>(
      `/v1/retention/plans/${encodeURIComponent(plan.plan_id)}/sweep`,
      {
        method: "POST",
        body: JSON.stringify({ plan_hash: plan.plan_hash }),
      },
    );
  },
```

GC mutation 不使用普通随机 `Idempotency-Key`；它的幂等身份就是持久化的 `plan_id + plan_hash`。

### 20.3 新建 `web/src/components/StoragePanel.tsx`

```tsx
import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { CleanupPlan, CleanupResult, StorageSummary } from "../api/types";


function bytes(value: number): string {
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let amount = value;
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) {
    amount /= 1024;
    unit += 1;
  }
  return `${amount.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}


type Props = { onClose: () => void };


export function StoragePanel({ onClose }: Props) {
  const [summary, setSummary] = useState<StorageSummary | null>(null);
  const [plan, setPlan] = useState<CleanupPlan | null>(null);
  const [result, setResult] = useState<CleanupResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run<T>(operation: () => Promise<T>, apply: (value: T) => void) {
    setBusy(true);
    setError(null);
    try {
      apply(await operation());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void run(api.storageSummary, setSummary);
  }, []);

  return (
    <div className="storage-backdrop" role="presentation">
      <section className="storage-panel" role="dialog" aria-label="Storage management">
        <header>
          <div>
            <p className="eyebrow">LOCAL DATA LIFECYCLE</p>
            <h2>Storage & retention</h2>
          </div>
          <button type="button" onClick={onClose}>Close</button>
        </header>

        {error && <p className="error-banner">{error}</p>}
        {summary && (
          <div className={`storage-pressure storage-pressure--${summary.pressure}`}>
            <strong>{summary.pressure.toUpperCase()}</strong>
            <span>Managed {bytes(summary.managed_allocated_bytes)}</span>
            <span>Free {bytes(summary.filesystem_free_bytes)}</span>
          </div>
        )}

        <div className="storage-roots">
          {summary?.roots.map((root) => (
            <div key={root.name} className="storage-root-row">
              <span>{root.name}</span>
              <strong>{bytes(root.allocated_bytes)}</strong>
            </div>
          ))}
        </div>

        {!plan && (
          <button
            type="button"
            disabled={busy || !summary?.destructive_gc_supported}
            onClick={() => void run(api.createCleanupPlan, setPlan)}
          >
            Preview cleanup plan
          </button>
        )}

        {plan && (
          <div className="cleanup-plan">
            <p>{plan.targets.length} eligible terminal jobs</p>
            <code>{plan.plan_hash}</code>
            {plan.targets.map((target) => (
              <div key={target.job_id} className="cleanup-target">
                <span>{target.job_id}</span>
                <span>{target.job_status}</span>
                <span>{bytes(target.estimated_logical_bytes)}</span>
              </div>
            ))}

            {plan.status === "planned" && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void run(
                  () => api.confirmCleanupPlan(plan),
                  setPlan,
                )}
              >
                Confirm exact plan
              </button>
            )}
            {plan.status === "confirmed" && (
              <button
                className="danger-button"
                type="button"
                disabled={busy}
                onClick={() => void run(
                  () => api.sweepCleanupPlan(plan),
                  (value) => {
                    setResult(value);
                    setPlan(value.plan);
                    void run(api.storageSummary, setSummary);
                  },
                )}
              >
                Sweep confirmed plan
              </button>
            )}
          </div>
        )}

        {result && (
          <p>
            Deleted {result.deleted_jobs} jobs and {result.deleted_blob_count} blobs;
            retained {result.retained_shared_blob_count} shared blobs.
          </p>
        )}
      </section>
    </div>
  );
}
```

“Preview cleanup plan”和“Sweep confirmed plan”必须是两个不同按钮，中间展示完整 hash、候选数量和过期时间。不要用一次点击的浏览器 `confirm()` 代替持久化确认状态。

### 20.4 修改 `web/src/App.tsx`

增加 import 和 state：

```tsx
import { StoragePanel } from "./components/StoragePanel";

const [storageOpen, setStorageOpen] = useState(false);
```

在 `<main>` 内增加一个简单入口和面板：

```tsx
<button
  type="button"
  className="storage-launcher"
  onClick={() => setStorageOpen(true)}
>
  Storage
</button>

{storageOpen && <StoragePanel onClose={() => setStorageOpen(false)} />}
```

### 20.5 修改 `web/src/styles/app.css`

沿用现有 token，增加最小样式：

```css
.storage-launcher {
  position: fixed;
  right: 1.25rem;
  bottom: 1.25rem;
  z-index: 20;
}

.storage-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgb(14 18 17 / 58%);
}

.storage-panel {
  width: min(720px, 100%);
  max-height: min(820px, 92vh);
  overflow: auto;
  padding: 1.25rem;
  border: 1px solid var(--line);
  border-radius: 1rem;
  background: var(--surface);
  box-shadow: 0 24px 80px rgb(0 0 0 / 28%);
}

.storage-panel header,
.storage-pressure,
.storage-root-row,
.cleanup-target {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.storage-roots,
.cleanup-plan {
  display: grid;
  gap: 0.6rem;
  margin-block: 1rem;
}

.storage-pressure--soft { color: #8a5b00; }
.storage-pressure--hard { color: #a52b1f; }

.cleanup-plan code {
  display: block;
  overflow-wrap: anywhere;
  padding: 0.75rem;
  background: var(--surface-muted);
}

.danger-button {
  background: #a52b1f;
  color: #fff;
}
```

如果现有 CSS 变量名不同，替换为项目已有 token，不要为了这个面板重写整个视觉系统。

---

## 二十一、增加容量盘点测试

> **本节类型：需要新增测试代码。**

新建 `tests/test_retention_inventory.py`：

```python
from pathlib import Path

from app.retention.inventory import (
    InventoryConfig,
    StorageInventoryService,
)


def test_inventory_does_not_follow_symlink(tmp_path: Path) -> None:
    managed = tmp_path / "managed"
    outside = tmp_path / "outside"
    managed.mkdir()
    outside.mkdir()
    (managed / "inside.bin").write_bytes(b"a" * 10)
    (outside / "large.bin").write_bytes(b"b" * 10_000)
    (managed / "escape").symlink_to(outside, target_is_directory=True)

    service = StorageInventoryService(
        InventoryConfig(
            roots=(("managed", managed),),
            filesystem_anchor=tmp_path,
            soft_limit_bytes=0,
            hard_limit_bytes=0,
            min_free_bytes=0,
            max_warnings=10,
            destructive_gc_supported=True,
        )
    )
    summary = service.summarize()

    assert summary.roots[0].skipped_symlink_count == 1
    # outside/large.bin 不能计入 managed root。
    assert summary.roots[0].logical_bytes < 10_000


def test_inventory_reports_hard_pressure_from_min_free_bytes(
    tmp_path: Path,
) -> None:
    service = StorageInventoryService(
        InventoryConfig(
            roots=(("managed", tmp_path),),
            filesystem_anchor=tmp_path,
            soft_limit_bytes=0,
            hard_limit_bytes=0,
            # 明确设置为大于当前文件系统总空间。
            min_free_bytes=10**30,
            max_warnings=10,
            destructive_gc_supported=False,
        )
    )

    summary = service.summarize()
    assert summary.pressure == "hard"
    assert summary.destructive_gc_supported is False


def test_inventory_reports_missing_root_without_creating_it(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "does-not-exist"
    service = StorageInventoryService(
        InventoryConfig(
            roots=(("missing", missing),),
            filesystem_anchor=tmp_path,
            soft_limit_bytes=0,
            hard_limit_bytes=0,
            min_free_bytes=0,
            max_warnings=10,
            destructive_gc_supported=True,
        )
    )

    summary = service.summarize()
    assert summary.roots[0].exists is False
    assert not missing.exists()
```

运行：

```bash
python -m pytest tests/test_retention_inventory.py \
  --basetemp=.pytest-tmp/phase35-inventory -q
```

---

## 二十二、增加 Retention Service 测试

> **本节类型：需要新增测试代码。**

新建 `tests/test_retention_service.py`。本文件使用小型 fake 隔离 Plan/Sweep 协议，不依赖真实论文或 LLM。

```python
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.job_runtime.errors import JobNotFoundError
from app.retention.errors import RetentionConflict
from app.retention.repository import SqliteRetentionRepository
from app.retention.schemas import BlobReference, RetentionPolicy
from app.retention.service import RetentionService


SHA = "a" * 64


class FakeJobs:
    def __init__(self, run_dir: Path, *, crash_after_delete: bool = False):
        self.job = SimpleNamespace(
            job_id="job-old",
            thread_id="thread-old",
            run_id="run-old",
            run_dir=str(run_dir),
            version=7,
            status="succeeded",
            updated_at="2025-01-01T00:00:00+00:00",
            workspace_manifest_id="manifest-old",
            workspace_manifest_generation=1,
        )
        self.crash_after_delete = crash_after_delete
        self.delete_calls = 0

    def list_retention_candidates(self, *, updated_before: float, limit: int):
        del updated_before, limit
        return [] if self.job is None else [self.job]

    def get(self, job_id: str):
        if self.job is None or self.job.job_id != job_id:
            raise JobNotFoundError(job_id)
        return self.job

    def list_workspace_bindings_for_retention(self, job_id: str):
        del job_id
        return []

    def list_workspace_manifests_for_retention(self, job_id: str):
        del job_id
        return []

    def count_workspace_blob_references(self, *, object_key: str) -> int:
        del object_key
        return 0

    def delete_job_for_retention(
        self,
        *,
        job_id: str,
        expected_version: int,
        expected_status: str,
    ) -> bool:
        current = self.get(job_id)
        assert current.version == expected_version
        assert current.status == expected_status
        self.delete_calls += 1
        self.job = None
        if self.crash_after_delete and self.delete_calls == 1:
            # 模拟 Job DELETE 已提交，但 journal 尚未写成功。
            raise RuntimeError("injected crash after delete")
        return True


class FakeArtifacts:
    def __init__(self):
        self.refs = {
            "job-old": [
                BlobReference(
                    backend="local",
                    object_key="sha256/aa/blob",
                    sha256=SHA,
                    size_bytes=7,
                )
            ]
        }

    def list_blob_references_for_job(self, job_id: str):
        return list(self.refs.get(job_id, []))

    def delete_job_artifacts(self, job_id: str) -> int:
        return len(self.refs.pop(job_id, []))

    def count_blob_references(self, *, backend: str, object_key: str) -> int:
        return sum(
            1
            for values in self.refs.values()
            for item in values
            if item.backend == backend and item.object_key == object_key
        )


class FakeChats:
    def __init__(self):
        self.deleted: list[str] = []

    def delete_job_messages(self, job_id: str) -> int:
        self.deleted.append(job_id)
        return 2


class FakeResources:
    def __init__(self, references: int):
        self.references = references

    def count_blob_references(self, *, backend: str, object_key: str) -> int:
        del backend, object_key
        return self.references


class FakeCheckpoints:
    def __init__(self):
        self.deleted: list[str] = []

    def delete_thread(self, thread_id: str) -> None:
        self.deleted.append(thread_id)


class FakeBlobStore:
    backend_name = "local"

    def __init__(self):
        self.deleted: list[str] = []

    def delete_if_matches(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_size: int,
    ) -> bool:
        assert expected_sha256 == SHA
        assert expected_size == 7
        self.deleted.append(object_key)
        return True


class FakePaths:
    def validate_job_paths(self, *, job, bindings):
        del bindings
        return [Path(job.run_dir)]

    def remove_tree(self, path: Path) -> int:
        del path
        return 11


class UnusedInventory:
    pass


class FakeSweepLock:
    @contextmanager
    def acquire(self):
        yield


def build_service(
    tmp_path: Path,
    *,
    resource_references: int = 0,
    crash_after_delete: bool = False,
):
    jobs = FakeJobs(
        tmp_path / "runs" / "run-old",
        crash_after_delete=crash_after_delete,
    )
    artifacts = FakeArtifacts()
    chats = FakeChats()
    checkpoints = FakeCheckpoints()
    blobs = FakeBlobStore()
    repository = SqliteRetentionRepository(tmp_path / "retention.sqlite")
    service = RetentionService(
        policy=RetentionPolicy(
            job_retention_seconds=0,
            max_jobs_per_plan=10,
            plan_ttl_seconds=300,
            delete_local_blobs=True,
        ),
        repository=repository,
        jobs=jobs,
        artifacts=artifacts,
        chats=chats,
        resources=FakeResources(resource_references),
        checkpoints=checkpoints,
        blob_store=blobs,
        path_remover=FakePaths(),
        inventory=UnusedInventory(),  # type: ignore[arg-type]
        selected_blob_backend="local",
        destructive_supported=True,
        sweep_lock=FakeSweepLock(),
    )
    return service, jobs, artifacts, chats, checkpoints, blobs


def test_plan_requires_exact_hash(tmp_path: Path) -> None:
    service, *_ = build_service(tmp_path)
    plan = service.create_plan()

    with pytest.raises(RetentionConflict):
        service.confirm_plan(plan_id=plan.plan_id, plan_hash="0" * 64)

    confirmed = service.confirm_plan(
        plan_id=plan.plan_id,
        plan_hash=plan.plan_hash,
    )
    assert confirmed.status == "confirmed"


def test_hold_excludes_terminal_job(tmp_path: Path) -> None:
    service, *_ = build_service(tmp_path)
    service.create_hold(job_id="job-old", reason="keep for paper", actor="test")

    plan = service.create_plan()
    assert plan.targets == []


def test_stale_job_fails_before_first_delete(tmp_path: Path) -> None:
    service, jobs, _, chats, checkpoints, blobs = build_service(tmp_path)
    plan = service.create_plan()
    service.confirm_plan(plan_id=plan.plan_id, plan_hash=plan.plan_hash)
    jobs.job.version += 1

    with pytest.raises(RetentionConflict):
        service.sweep(plan_id=plan.plan_id, plan_hash=plan.plan_hash)

    assert chats.deleted == []
    assert checkpoints.deleted == []
    assert blobs.deleted == []


def test_resource_reference_protects_shared_blob(tmp_path: Path) -> None:
    service, jobs, _, _, _, blobs = build_service(
        tmp_path,
        resource_references=1,
    )
    plan = service.create_plan()
    service.confirm_plan(plan_id=plan.plan_id, plan_hash=plan.plan_hash)
    result = service.sweep(plan_id=plan.plan_id, plan_hash=plan.plan_hash)

    assert result.plan.status == "completed"
    assert jobs.job is None
    assert blobs.deleted == []
    assert result.retained_shared_blob_count == 1


def test_unreferenced_blob_is_deleted(tmp_path: Path) -> None:
    service, jobs, _, _, _, blobs = build_service(tmp_path)
    plan = service.create_plan()
    service.confirm_plan(plan_id=plan.plan_id, plan_hash=plan.plan_hash)
    result = service.sweep(plan_id=plan.plan_id, plan_hash=plan.plan_hash)

    assert result.plan.status == "completed"
    assert jobs.job is None
    assert blobs.deleted == ["sha256/aa/blob"]

    replay = service.sweep(plan_id=plan.plan_id, plan_hash=plan.plan_hash)
    assert replay.model_dump() == result.model_dump()
    assert blobs.deleted == ["sha256/aa/blob"]


def test_retry_recovers_when_job_delete_committed_before_journal(
    tmp_path: Path,
) -> None:
    service, jobs, _, _, _, blobs = build_service(
        tmp_path,
        crash_after_delete=True,
    )
    plan = service.create_plan()
    service.confirm_plan(plan_id=plan.plan_id, plan_hash=plan.plan_hash)

    with pytest.raises(RuntimeError, match="injected crash"):
        service.sweep(plan_id=plan.plan_id, plan_hash=plan.plan_hash)

    assert jobs.job is None
    failed = service.get_plan(plan.plan_id)
    assert failed.status == "failed"

    retried = service.sweep(plan_id=plan.plan_id, plan_hash=plan.plan_hash)
    assert retried.plan.status == "completed"
    assert blobs.deleted == ["sha256/aa/blob"]
    assert any(
        item.step_name == "job_metadata" and item.status == "completed"
        for item in retried.steps
    )
```

运行：

```bash
python -m pytest tests/test_retention_service.py \
  --basetemp=.pytest-tmp/phase35-service -q
```

这个测试使用 fake 验证协议，不替代 SQLite repository 集成测试。还应在现有 `tests/test_job_store.py`、Artifact/Chat repository 测试中分别验证新增 SQL 方法。

---

## 二十三、增加具体 Repository 与 Local Blob 测试

> **本节类型：需要修改或新增测试代码。**

至少补齐以下测试。可以放入现有对应测试文件，也可以新建 `tests/test_retention_repositories.py`：

```python
def test_delete_if_matches_rejects_changed_blob(tmp_path: Path) -> None:
    import hashlib

    from app.storage.errors import ArtifactIntegrityError
    from app.storage.local_blob_store import LocalBlobStore

    source = tmp_path / "source.bin"
    source.write_bytes(b"original")
    digest = hashlib.sha256(b"original").hexdigest()
    store = LocalBlobStore(tmp_path / "blobs")
    store.put_file(
        object_key=f"sha256/{digest[:2]}/{digest}",
        source_path=source,
        expected_sha256=digest,
        expected_size=len(b"original"),
        media_type="application/octet-stream",
    )

    # 模拟 Plan 创建后对象被替换；compare-and-delete 必须拒绝。
    target = store._path(f"sha256/{digest[:2]}/{digest}")
    target.write_bytes(b"changed!")
    with pytest.raises(ArtifactIntegrityError):
        store.delete_if_matches(
            object_key=f"sha256/{digest[:2]}/{digest}",
            expected_sha256=digest,
            expected_size=len(b"original"),
        )
    assert target.exists()


def test_delete_if_matches_is_idempotent(tmp_path: Path) -> None:
    import hashlib

    from app.storage.local_blob_store import LocalBlobStore

    payload = b"content"
    source = tmp_path / "source.bin"
    source.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    key = f"sha256/{digest[:2]}/{digest}"
    store = LocalBlobStore(tmp_path / "blobs")
    store.put_file(
        object_key=key,
        source_path=source,
        expected_sha256=digest,
        expected_size=len(payload),
        media_type="application/octet-stream",
    )

    assert store.delete_if_matches(
        object_key=key,
        expected_sha256=digest,
        expected_size=len(payload),
    ) is True
    assert store.delete_if_matches(
        object_key=key,
        expected_sha256=digest,
        expected_size=len(payload),
    ) is False
```

Repository 测试必须覆盖：

```text
Job candidate 只包含三个终态且满足 updated_before
delete_job_for_retention 的 version/status fencing
Job 删除后 resumes/events/commands 被级联删除
Job 删除后 workspace_manifests/assignments 被显式删除
Artifact 删除 heads 后再删除全部历史 versions
Artifact 引用计数按 backend + object_key
Chat 只删除目标 job_id 的消息
Resource manifest 仍保留且可保护 object_key
```

运行：

```bash
python -m pytest \
  tests/test_retention_repositories.py \
  tests/test_job_store.py \
  tests/test_artifact_storage.py \
  --basetemp=.pytest-tmp/phase35-repositories -q
```

如果当前 Artifact 测试文件名不是 `tests/test_artifact_storage.py`，先运行 `rg --files tests | rg 'artifact|storage'` 找到真实文件，不要机械复制不存在的路径。

---

## 二十四、增加 API 测试

> **本节类型：需要新增测试代码。**

新建 `tests/test_retention_api.py`。复用上一节的 service fixture；下面给出路由边界测试核心：

```python
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import install_error_handlers
from app.api.retention_routes import router
from app.retention.schemas import (
    ManagedRootUsage,
    StorageSummary,
)


class FakeInventory:
    def summarize(self) -> StorageSummary:
        return StorageSummary(
            generated_at="2026-08-07T00:00:00+00:00",
            managed_logical_bytes=10,
            managed_allocated_bytes=4096,
            filesystem_total_bytes=100_000,
            filesystem_free_bytes=90_000,
            soft_limit_bytes=0,
            hard_limit_bytes=0,
            min_free_bytes=0,
            pressure="normal",
            destructive_gc_supported=False,
            roots=[
                ManagedRootUsage(
                    name="runs",
                    path="/redacted/in-view",
                    exists=True,
                    logical_bytes=10,
                    allocated_bytes=4096,
                    file_count=1,
                    directory_count=1,
                    skipped_symlink_count=0,
                    error_count=0,
                )
            ],
        )


def make_app(bundle) -> FastAPI:
    app = FastAPI()
    app.state.api_token = None
    app.state.retention_bundle = bundle
    app.include_router(router)
    install_error_handlers(app)
    return app


def test_summary_remains_available_when_sweep_backend_is_unsupported() -> None:
    bundle = SimpleNamespace(inventory=FakeInventory(), service=None)
    client = TestClient(make_app(bundle))

    summary = client.get("/v1/storage/summary")
    assert summary.status_code == 200
    assert summary.json()["destructive_gc_supported"] is False
    assert "path" not in summary.json()["roots"][0]

    plan = client.post("/v1/retention/plans")
    assert plan.status_code == 501
    assert plan.json()["code"] == "RETENTION_BACKEND_UNSUPPORTED"
```

在使用真实 RetentionService 的 API fixture 中继续验证：

```python
def test_api_never_exposes_cleanup_internal_paths(client) -> None:
    response = client.post("/v1/retention/plans")
    assert response.status_code == 201
    payload = response.json()
    serialized = str(payload)
    assert "run_dir" not in serialized
    assert "object_key" not in serialized
    assert "assignment_token" not in serialized


def test_api_requires_confirm_before_sweep(client) -> None:
    plan = client.post("/v1/retention/plans").json()
    response = client.post(
        f"/v1/retention/plans/{plan['plan_id']}/sweep",
        json={"plan_hash": plan["plan_hash"]},
    )
    assert response.status_code == 409


def test_api_rejects_wrong_hash(client) -> None:
    plan = client.post("/v1/retention/plans").json()
    response = client.post(
        f"/v1/retention/plans/{plan['plan_id']}/confirm",
        json={"plan_hash": "0" * 64},
    )
    assert response.status_code == 409
```

还要在现有 Job API 集成测试增加 `507 STORAGE_CAPACITY_EXCEEDED`：注入一个 `capacity_guard.assert_can_submit()` 总是抛异常，并断言 WorkspaceSnapshotter 从未被调用。

运行：

```bash
python -m pytest tests/test_retention_api.py \
  --basetemp=.pytest-tmp/phase35-api -q
```

---

## 二十五、增加前端测试

> **本节类型：需要新增前端测试代码。**

新建 `web/tests/storage-panel.test.tsx`：

```tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "../src/api/client";
import { StoragePanel } from "../src/components/StoragePanel";
import type { CleanupPlan, StorageSummary } from "../src/api/types";


const summary: StorageSummary = {
  generated_at: "2026-08-07T00:00:00Z",
  managed_logical_bytes: 1024,
  managed_allocated_bytes: 4096,
  filesystem_total_bytes: 100_000,
  filesystem_free_bytes: 90_000,
  soft_limit_bytes: 0,
  hard_limit_bytes: 0,
  min_free_bytes: 0,
  pressure: "normal",
  destructive_gc_supported: true,
  roots: [
    {
      name: "runs",
      exists: true,
      logical_bytes: 1024,
      allocated_bytes: 4096,
      file_count: 1,
      directory_count: 1,
      skipped_symlink_count: 0,
      error_count: 0,
    },
  ],
  warnings: [],
};

const planned: CleanupPlan = {
  plan_id: "gc-1",
  status: "planned",
  plan_hash: "a".repeat(64),
  targets: [
    {
      job_id: "job-old",
      run_id: "run-old",
      job_status: "succeeded",
      job_updated_at: "2026-01-01T00:00:00Z",
      estimated_logical_bytes: 1024,
    },
  ],
  created_at: "2026-08-07T00:00:00Z",
  expires_at: "2026-08-07T00:30:00Z",
  failure_code: null,
};


afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});


it("requires separate preview, confirm and sweep actions", async () => {
  vi.spyOn(api, "storageSummary").mockResolvedValue(summary);
  vi.spyOn(api, "createCleanupPlan").mockResolvedValue(planned);
  vi.spyOn(api, "confirmCleanupPlan").mockResolvedValue({
    ...planned,
    status: "confirmed",
  });
  vi.spyOn(api, "sweepCleanupPlan").mockResolvedValue({
    plan: { ...planned, status: "completed" },
    deleted_jobs: 1,
    deleted_blob_count: 1,
    retained_shared_blob_count: 0,
    reclaimed_logical_bytes: 1024,
  });

  render(<StoragePanel onClose={() => undefined} />);
  fireEvent.click(await screen.findByRole("button", {
    name: "Preview cleanup plan",
  }));
  expect(await screen.findByText("job-old")).toBeTruthy();
  expect(api.confirmCleanupPlan).not.toHaveBeenCalled();
  expect(api.sweepCleanupPlan).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Confirm exact plan" }));
  expect(await screen.findByRole("button", {
    name: "Sweep confirmed plan",
  })).toBeTruthy();
  expect(api.sweepCleanupPlan).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Sweep confirmed plan" }));
  expect(await screen.findByText(/Deleted 1 jobs/)).toBeTruthy();
});
```

运行：

```bash
cd web
npm test -- storage-panel.test.tsx
npm run typecheck
npm run build
cd ..
```

---

## 二十六、建议的测试顺序

> **本节类型：测试说明，不修改项目代码。**

### 26.1 先跑 Phase 35 小集合

```bash
python -m pytest \
  tests/test_retention_inventory.py \
  tests/test_retention_service.py \
  tests/test_retention_repositories.py \
  tests/test_retention_api.py \
  --basetemp=.pytest-tmp/phase35-focused -q
```

### 26.2 再跑受影响的旧功能

```bash
python -m pytest \
  tests/test_job_store.py \
  tests/test_job_api.py \
  tests/test_chat_api.py \
  tests/test_workspace_gc.py \
  --basetemp=.pytest-tmp/phase35-related -q
```

文件名以当前仓库真实测试为准；不存在时使用：

```bash
rg --files tests | rg 'job|api|chat|workspace|artifact'
```

### 26.3 代码质量与全量回归

```bash
python -m ruff check app tests
python -m pytest --basetemp=.pytest-tmp/phase35-all -q

cd web
npm test
npm run build
cd ..
```

不要在测试命令中省略 `--basetemp=.pytest-tmp/...`。这样本阶段所有临时测试文件都留在项目目录内，结束后可统一清理。

---

## 二十七、手工验收前的安全准备

> **本节类型：手工验收说明，不修改项目代码。**

### 27.1 先确认当前 backend

```bash
python - <<'PY'
from app.config import settings

print({
    "job_store_backend": settings.job_store_backend,
    "checkpoint_backend": settings.checkpoint_backend,
    "artifact_blob_backend": settings.artifact_blob_backend,
    "retention_db_path": str(settings.retention_db_path),
})
PY
```

只有下面组合允许真正 Sweep：

```text
JOB_STORE_BACKEND=sqlite
CHECKPOINT_BACKEND=sqlite
ARTIFACT_BLOB_BACKEND=local
```

其它组合只能验收 summary 和 `501 RETENTION_BACKEND_UNSUPPORTED`。

### 27.2 查看候选 Job，不要先改数据库时间

```bash
python -m app.main list-jobs --limit 100
```

寻找：

```text
status 是 succeeded / failed / cancelled
updated_at 早于当前时间 14 天（或你的 RETENTION_JOB_DAYS）
不再需要继续调试或对话
重要结果已经通过 Phase 34 Export 保存
```

不要为了手工验收直接把真实 Job 的 `updated_at` 改成旧时间。立即过期行为已经由注入 `job_retention_seconds=0` 的自动化测试覆盖；真实 Sweep 应使用自然满足策略的旧 Job。

### 27.3 给重要 Job 加 Hold

对仍要保留的旧 Job：

```bash
python -m app.main retention-hold \
  job_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --reason "保留用于论文结果对比"
```

再次创建 Plan 时，该 Job 不应出现在 targets 中。

### 27.4 可选备份

Phase 34 已提供单 Job 导出，先在 Web 点击 `Export job (.zip)` 保存用户可见结果。数据库级备份应在服务停止后进行，并放在项目允许目录内，例如：

```bash
mkdir -p backups/phase35-before-gc
cp jobs/runtime.sqlite backups/phase35-before-gc/
cp storage/artifacts.sqlite backups/phase35-before-gc/
cp chat/chat.sqlite backups/phase35-before-gc/
cp retention/retention.sqlite backups/phase35-before-gc/ 2>/dev/null || true
```

如果 SQLite 正在 WAL 模式运行，不要把上面的普通 `cp` 当作一致性在线备份。正式备份应先停止 `serve-stack`，或使用 SQLite backup API。单 Job ZIP 是结果交付包，不等于完整数据库灾备。

---

## 二十八、手工验收容量摘要与配额保护

> **本节类型：手工验收说明。**

### 28.1 CLI 查看容量

```bash
python -m app.main storage-summary
```

重点检查：

```text
pressure 是 normal / soft / hard
managed_allocated_bytes 大于等于各 root 合计
filesystem_free_bytes 合理
roots 只包含项目配置的受管路径
warnings 没有无限增长
destructive_gc_supported 与 backend 组合一致
```

### 28.2 启动单机服务

```bash
python -m app.main serve-stack --host 127.0.0.1 --port 8000
```

另开一个终端：

```bash
curl -s http://127.0.0.1:8000/v1/storage/summary | python -m json.tool
```

浏览器进入 Web Console，点击右下角 `Storage`，应看到和 API 一致的 pressure、managed bytes、free bytes 和 root 列表。

### 28.3 验收 hard quota

这一步会暂时拒绝新任务，但不会中止已有任务。先停止服务，在当前终端临时设置一个极小 hard limit：

```bash
export STORAGE_HARD_LIMIT_BYTES=1
python -m app.main serve-stack --host 127.0.0.1 --port 8000
```

尝试从 Web 创建新任务，或调用现有 Job 提交 API，应得到：

```json
{
  "code": "STORAGE_CAPACITY_EXCEEDED",
  "message": "...",
  "request_id": "..."
}
```

HTTP 状态应为 `507`。同时检查已有 Worker/Job 没有被取消。验收后退出服务并恢复：

```bash
unset STORAGE_HARD_LIMIT_BYTES
```

不要在共享 shell 配置文件中永久保留测试阈值。

---

## 二十九、手工验收 Plan、Confirm 与 Sweep

> **本节类型：手工验收说明。以下命令可能删除满足条件的数据，必须逐步核对。**

### 29.1 创建 Plan

```bash
python -m app.main gc-plan
```

输出中记录：

```text
plan_id
plan_hash
status=planned
expires_at
targets 中每个 job_id/run_id/status/updated_at
```

此时逐项检查：

1. 没有运行中、等待输入或 reconciliation Job；
2. Hold Job 不在列表；
3. 每个 Job 都超过保留期；
4. 候选数量不超过 `RETENTION_PLAN_MAX_JOBS`；
5. 重要 Job 已完成导出；
6. `runs/`、Artifact、Chat 和 Job DB 此时均未删除。

### 29.2 用错误 Hash 验证拒绝路径

```bash
python -m app.main gc-confirm \
  gc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --plan-hash 0000000000000000000000000000000000000000000000000000000000000000
```

预期失败，错误说明 hash 不匹配。Plan 仍应为 `planned`。

### 29.3 确认正确 Plan

```bash
python -m app.main gc-confirm \
  gc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --plan-hash <gc-plan输出的64位plan_hash>
```

预期 `status=confirmed`。此时仍没有文件被删除。

### 29.4 验收 Stale Plan

如果当前有专门用于验收的候选 Job，可以在 confirm 后给它增加 Hold：

```bash
python -m app.main retention-hold \
  job_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --reason "验证 confirmed plan 会被新 hold 阻止"
```

再运行 sweep：

```bash
python -m app.main gc-sweep \
  gc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --plan-hash <plan_hash>
```

预期返回 conflict，不删除 Plan 中任何尚未清理的数据。移除 Hold：

```bash
python -m app.main retention-release job_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

旧 Plan 已进入 `failed` 或已经与当前 hold 历史不一致时，最安全做法是重新 `gc-plan -> gc-confirm`，而不是强制沿用旧确认。

### 29.5 执行真正 Sweep

重新生成并确认 Plan 后：

```bash
python -m app.main gc-sweep \
  gc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --plan-hash <完全相同的plan_hash>
```

预期：

```text
plan.status=completed
每个 Job 的 chat/checkpoint/artifact/filesystem/job_metadata step 为 completed
shared Blob 显示 retained，不会删除
unreferenced local Blob 才显示 deleted
retention/retention.sqlite 中 Plan 与 step 仍存在
```

### 29.6 验收幂等重试

使用完全相同命令再次执行：

```bash
python -m app.main gc-sweep \
  gc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --plan-hash <完全相同的plan_hash>
```

预期直接从 durable journal 返回已完成结果，不重复删除。教程中的 `RetentionService.sweep()` 已在获取文件锁后处理 completed replay；为该路径增加断言，确保第二次调用的统计与第一次一致。

### 29.7 验收审计不会随 Job 消失

```bash
python -m app.main list-jobs --limit 100
python -m app.main storage-summary
```

被清理 Job 应不再出现在 Job 列表，但：

```bash
python - <<'PY'
import sqlite3
from app.config import settings

with sqlite3.connect(settings.retention_db_path) as connection:
    print(connection.execute(
        "SELECT plan_id, status, completed_at FROM retention_plans "
        "ORDER BY created_at DESC LIMIT 5"
    ).fetchall())
    print(connection.execute(
        "SELECT job_id, step_name, status FROM retention_steps "
        "ORDER BY updated_at DESC LIMIT 30"
    ).fetchall())
PY
```

仍应能看到 Plan 和步骤记录。

---

## 三十、验证共享 Blob 不会误删

> **本节类型：测试与验收说明。**

自动化测试已经用 `FakeResources(references=1)` 覆盖。若要在真实数据中验证：

1. 找到两个 Artifact/Workspace/Resource 引用同一内容寻址 key 的测试数据；
2. 只让其中一个 Job 满足 retention policy；
3. 创建并确认 Plan；
4. Sweep 后检查另一个引用仍可通过 Catalog/Workspace 打开；
5. 检查 audit 中该 Blob 的 `live_references > 0` 且 `deleted=false`。

不要通过手工复制同名文件模拟共享引用。GC 判断的是 Catalog/Manifest 中受信任的 metadata 引用，不是文件名相同。

如果同一 Blob 同时被 Artifact 和 Workspace 引用，Artifact metadata 删除后仍必须由 Workspace reference count 保护；如果它来自 published Resource，ResourceManifest 还会继续保护。

---

## 三十一、Workspace GC 与 Retention GC 如何共存

> **本节类型：设计说明，不修改项目代码。**

现有 `WorkspaceGarbageCollector` 负责：

```text
只清理 released 且超过 workspace_gc_min_age 的旧 assignment epoch
清理后把 assignment 标记 garbage_collected
不删除 Job、Checkpoint、Chat 或 Artifact metadata
```

本阶段 Retention GC 负责：

```text
清理满足 retention policy 的整个终态 Job 生命周期
包含 current/released/failed workspace assignment 的受管目录
最终删除该 Job 的 workspace assignment/manifest metadata
```

两者可以保留，但不要让它们并发删除同一路径。最简单做法是让旧 Workspace GC 也复用 `SingleHostSweepLock`，或在运行 Retention Sweep 时暂停独立 Workspace GC 命令。

如果旧 GC 已经删除某个 released epoch，Retention PathRemover 看到目标不存在应视为幂等成功，但 marker/path 身份仍来自当前 assignment metadata，不能改为扫描 `worker_workspaces/` 猜测孤儿目录。

---

## 三十二、SQLite VACUUM 的正确位置

> **本节类型：运维说明，不属于普通 Sweep。**

先查看 freelist：

```bash
python - <<'PY'
import sqlite3
from app.config import settings

for path in (
    settings.job_db_path,
    settings.checkpoint_db_path,
    settings.artifact_catalog_db_path,
    settings.chat_db_path,
    settings.retention_db_path,
):
    if not path.exists():
        continue
    with sqlite3.connect(path) as connection:
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        free_pages = connection.execute("PRAGMA freelist_count").fetchone()[0]
    print(path, {"reusable_bytes": page_size * free_pages})
PY
```

只有在以下条件都满足时才考虑离线 VACUUM：

```text
serve-stack、worker 和 API 已停止
数据库已有一致性备份
文件系统有足够空间容纳重写过程
确实需要把 freelist 归还给操作系统，而不是继续复用
```

对单个数据库执行：

```bash
python - <<'PY'
import sqlite3
from app.config import settings

with sqlite3.connect(settings.job_db_path) as connection:
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.execute("VACUUM")
PY
```

不要在服务运行时循环 VACUUM 所有数据库，也不要把 VACUUM 失败解释为 GC metadata 删除失败。

---

## 三十三、常见问题与排查

> **本节类型：故障排查，不修改项目代码。**

### 33.1 Plan 没有候选

依次检查：

```text
Job 是否为 succeeded/failed/cancelled
updated_at 是否早于 retention cutoff
Job 是否有 Hold
RETENTION_PLAN_MAX_JOBS 是否有效
CLI 和 API 是否读取同一份 .env/工作目录
```

不要把 `RETENTION_JOB_DAYS` 改为负数或用 `--force` 绕过；测试立即过期使用注入 policy。

### 33.2 Confirm 返回 hash mismatch

必须使用同一次 `gc-plan` 返回的完整 64 位 hash。重新创建 Plan 会产生新的 `plan_id/created_at/hash`，旧 hash 不能确认新 Plan。

### 33.3 Sweep 返回 Job identity changed

Plan 之后 Job 的 version、status、Workspace generation、Artifact revision 或路径身份发生变化。重新查看 Job，确认没有 Worker/人工操作仍在写，然后重新生成 Plan。

### 33.4 Workspace marker missing/mismatch

不要直接创建一个假 marker 或跳过检查。先检查：

```text
workspace_root 是否由 worker root + job + epoch 派生
assignment token/hash 是否与 DB 一致
目录是否被人工移动
旧 Workspace GC 是否已经处理该 assignment
```

目标不存在可以幂等跳过；目标存在但 marker 缺失必须人工调查。

### 33.5 GC 显示 completed，但 `df` 空间变化很小

可能原因：

```text
删除的大部分是 SQLite 行，页进入 freelist
Blob 被其它 Artifact/Workspace/Resource 引用而保留
文件系统使用压缩、稀疏文件或 copy-on-write
目录文件很小，logical bytes 与 allocated bytes 不同
进程仍持有已 unlink 文件的打开句柄
```

先查看 audit 的 deleted/retained 和 SQLite freelist，不要立即重复删除。

### 33.6 S3/PostgreSQL 模式返回 501

这是预期的 fail-closed 行为，不是 factory 故障。Summary 应仍可用。后续支持远端 GC 前必须补齐：

```text
PostgreSQL advisory lock / transaction fencing
S3 version ID 与 delete marker
Object Lock / retention policy
Workspace/Resource backend + version identity
远端对象 listing 的一致性与成本预算
```

### 33.7 第二个 Sweep 提示另一个 GC 正在运行

单机文件锁正在生效。等待第一个请求完成。若进程已经崩溃，OS 会自动释放锁；不要手工删除 `.gc.lock` 来“解锁”，文件是否存在不等于锁是否被持有。

### 33.8 Chat 数据没有删除

检查 factory 是否保留了教程中的条件：

```python
chat = (
    SqliteChatRepository(settings.chat_db_path)
    if settings.chat_enabled or settings.chat_db_path.exists()
    else NoOpChatRetentionPort()
)
```

`CHAT_ENABLED` 只控制新 Chat 能力，不控制历史数据生命周期。只要旧 `chat_db_path` 存在，Retention 仍应打开它并删除目标 Job 的历史消息。

### 33.9 Retention audit 自己会不会无限增长

会缓慢增长，但远小于 Artifact/Workspace。第一版保留全部 GC audit。后续可以给 completed Plan 设置更长的独立保留期，例如 365 天，并导出聚合报告后清理旧 step detail；不能让某个 Job 的 retention policy 删除自己的审计证据。

---

## 三十四、本阶段涉及的 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 34.1 Agent 数据生命周期

Agent 系统不只有 prompt 和 model。State、Checkpoint、Tool output、Artifact、Workspace、Chat 和 Resource 都有生命周期。生命周期不清晰会让“记忆”变成不可控存储。

### 34.2 Reachability-Based GC

Blob 是否可删由可达性决定，而不是年龄或目录名决定：

```text
Artifact metadata ─┐
Workspace manifest ├─> Blob
Resource manifest ─┘
```

只有所有可信引用都消失后，Blob 才是 orphan。这与编程语言垃圾回收器从 root set 判断对象可达性是同一核心思想。

### 34.3 Human-in-the-Loop for Destructive Action

GC 也是高风险 Agent action。`Preview -> exact hash confirm -> execute` 与此前 command approval hash、patch approval hash 使用相同原则：审批必须绑定将要执行的精确对象，不能只绑定自然语言意图。

### 34.4 Optimistic Concurrency Control

Plan 绑定 `Job.version/status/updated_at`。执行前比较当前身份，发现变化就拒绝。这避免用户审批动作 A 后，系统实际删除已经变化的动作 B。

### 34.5 Idempotency 与 Durable Journal

跨多个 SQLite/文件系统的清理无法形成一个全局 ACID transaction。解决方式不是假装原子，而是：

```text
小步骤幂等
每步持久 journal
失败可重试
已完成步骤不重复执行
窄崩溃窗口有明确恢复规则
```

这是一种轻量 Saga。

### 34.6 Fail Closed

未知 backend、过期 Plan、身份漂移、marker 缺失、symlink、hash 变化和共享引用都默认阻止删除。清理得少是容量问题，误删是完整性事故。

### 34.7 Admission Control

配额保护属于 admission control：在新任务进入系统、写入大量 Workspace/Blob 之前拒绝，而不是任务运行到一半磁盘耗尽后补救。它与 Worker capability/preflight 一样，是执行前约束。

### 34.8 Control Plane 与 Data Plane

Job/Artifact/Retention SQLite 是控制面 metadata；Blob、Workspace 和 run directory 是数据面。删除顺序必须先理解二者引用，不可只操作其中一侧。

### 34.9 Internal Model 与 Public View

内部 CleanupPlan 需要路径、Blob key 和 token hash 做审计与校验；前端只需要 Job、状态、大小、过期时间和 plan hash。独立 `CleanupPlanView` 防止内部能力信息越过 API 边界。

### 34.10 Single-Host Coordination

单机不代表没有并发：浏览器双击、CLI 与 API 同时调用、多个线程都可能并发 Sweep。OS file lock 是符合当前规模的协调工具；未来跨主机才升级为数据库 advisory lock 或 durable lease。

---

## 三十五、完成标准

> **本节类型：最终验收，不修改项目代码。**

- 配置中有 retention DB、保留期、Plan TTL、批量上限和容量阈值；
- retention audit 位于独立 SQLite，不属于待删除 Job；
- Inventory 只扫描显式 managed roots；
- Inventory 不跟随 root 或子目录 symlink；
- Inventory 统计 logical/allocated bytes、free space 和 warnings；
- Job submit 在 Workspace snapshot 前执行 quota guard；
- hard pressure 返回 507，且不取消已有任务；
- 只有 succeeded/failed/cancelled 且超过保留期的 Job 可进入 Plan；
- Hold Job 不进入 Plan；
- Plan payload canonical hash 可重算；
- API 公开 View 不含本地路径、object key 或 token；
- Confirm 只接受 exact hash；
- Hold 在 confirm 后新增仍能阻止 Sweep；
- Sweep 前对所有未完成 target 做完整预检；
- 路径由配置、Job 和 WorkspaceBinding 重新派生；
- Workspace marker identity 不一致时零删除；
- 文件树存在 symlink 时拒绝删除；
- Chat、Checkpoint、Artifact、Filesystem、Job metadata 有明确顺序；
- Workspace assignments/manifests 不留下悬空记录；
- Artifact 删除包括历史 versions；
- Blob recount 同时包含 Artifact、Workspace 和 Resource；
- Resource metadata 不随 Job 删除；
- Local Blob 删除前核对 key、size 和 SHA-256；
- PostgreSQL/S3 模式的 destructive Sweep 返回 501；
- 同一主机同一时刻最多一个 Sweep；
- 进程崩溃后可用相同 Plan/hash 幂等重试；
- completed replay 不会重复删除；
- Retention audit 在 Job 删除后仍可查询；
- Web 明确分离 Preview、Confirm 和 Sweep；
- 所有测试临时目录位于项目 `.pytest-tmp/`；
- Phase 35 focused tests、相关回归、全量 pytest、前端 test/build 全部通过。

---

## 三十六、Phase 35 之后优先做什么

> **本节类型：后续路线，不修改项目代码。**

完成本阶段后，单机产品闭环已经包括：

```text
输入导入
-> Agent Job 执行
-> Human Review / 可编辑命令
-> Artifact / Chat 交互
-> 安全预览、下载、导出
-> 容量保护、数据保留与可审计 GC
```

下一阶段优先建议：

```text
Phase 36：Chat 上下文压缩、会话摘要与引用保真
```

原因是当前 Chat Agent 已适合做上下文管理，但不能简单删除旧消息。应把历史拆成：

```text
最近原始对话窗口
长期会话摘要
不可压缩的用户约束/决定
Artifact citation anchors
当前 Job state snapshot
```

下一阶段重点不是“存更多记忆”，而是：

```text
超过 token budget 时增量压缩
摘要绑定 covered_sequence 范围与 hash
保留未解决问题、用户决定和审批结果
引用仍指向真实 Artifact，不把摘要当证据
摘要生成失败时回退到有界原始窗口
评测压缩前后答案与 citation 是否漂移
```

再后续可按实际痛点选择：

```text
P2 Chat Citation Golden Eval
P2 Run-to-Run Manifest/Artifact Diff
P2 Resource 独立 retention 与显式删除协议
P3 PostgreSQL/S3 分布式 GC
P3 多用户配额、RBAC 与 legal hold
```

此时仍不建议优先引入复杂多 Agent 编排。单机单用户阶段最有价值的是让 Chat 在长会话中稳定记住约束、可追溯引用，同时不无限增长上下文和本地数据库。
