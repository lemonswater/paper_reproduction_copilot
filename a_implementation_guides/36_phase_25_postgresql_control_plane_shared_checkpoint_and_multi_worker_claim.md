# 36. Phase 25：PostgreSQL Control Plane、Shared Checkpoint 与 Multi-Worker Claim

Phase 24 已经把可变工作区与持久 Artifact 分开，并建立了 `JobStore`、
`ArtifactRepository` 和 `BlobStore` 端口。但是控制面仍然分散在三个本地 SQLite
文件中：

```text
jobs/runtime.sqlite
    Job、Resume、Event、Lease

checkpoints/langgraph.sqlite
    LangGraph state、pending writes、interrupt

storage/artifacts.sqlite
    Artifact version 与 head
```

这意味着 API 和 Worker 只能在能访问同一组本地文件的进程中协作。本阶段将小型、
事务型元数据迁到 PostgreSQL，并把 LangGraph checkpoint 切换为 `PostgresSaver`：

```text
API process ───────────────┐
Worker A ──────────────────┼── PostgreSQL control plane
Worker B ──────────────────┘      ├── Job / Resume / Event
                                 ├── Artifact metadata
                                 └── LangGraph checkpoint

Worker local workspace ───────── runs/<run_id>/
Published immutable blob ─────── Local Blob 或 S3/MinIO
```

> **本教程中的源码均为待实现代码。**
>
> 除了明确标记为“知识说明”的小节，其余小节都会指出需要新增或修改的文件。
> 你仍然自己修改项目源码；本教程不会直接修改 `app/` 和 `tests/`。

---

## 一、本阶段为什么只选 PostgreSQL

> **本节类型：架构决策说明，不修改项目代码。**

本阶段不同时实现 MySQL。原因不是 MySQL 不能完成任务，而是队列 claim、JSON 类型、
时间函数、冲突插入和迁移 DDL 都存在方言差异：

```text
PostgreSQL：
    SELECT ... FOR UPDATE SKIP LOCKED
    JSONB
    INSERT ... ON CONFLICT
    clock_timestamp()

MySQL：
    对应能力存在，但语法、锁行为和版本要求不同
```

同时支持两种生产数据库会使本阶段真正需要验证的语义被方言兼容代码淹没。

最终选择：

```text
sqlite       -> 离线测试、单进程开发、已有任务兼容
postgresql   -> 多进程控制面、共享 checkpoint、生产目标
```

PostgreSQL 的 `SKIP LOCKED` 明确适用于多个消费者访问 queue-like table；它提供的是
队列消费视图，不应拿来实现普通业务查询。

参考：

- [PostgreSQL SELECT locking clause](https://www.postgresql.org/docs/18/sql-select.html)
- [SQLAlchemy PostgreSQL dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)

---

## 二、Phase 25 能做到什么，不能做到什么

> **本节类型：能力边界说明，不修改项目代码。**

完成后可以做到：

1. API、Worker A、Worker B 使用同一个 Job/Event 数据源；
2. 多个 Worker 并发 claim 时，每个 Job 最多被一个 claim token 获得；
3. Worker A 在 interrupt 后退出，Worker B 能读取同一 PostgreSQL checkpoint 恢复；
4. API 在另一个进程读取 Artifact Catalog；
5. 数据库时间统一决定 `available_at`、heartbeat 和 lease expiry；
6. PostgreSQL 重启后的 stale pooled connection 能被检测；
7. Schema 变化通过 Alembic revision 审计，而不是在启动时偷偷 `CREATE TABLE`；
8. SQLite 与 PostgreSQL 运行相同的 JobStore contract tests。

本阶段仍然不能宣称任意多主机接管：

```text
Job metadata              已共享
LangGraph checkpoint      已共享
Artifact blob             可共享（使用 S3/MinIO 时）
run workspace             仍是本地 runs/<run_id>/
target repository         仍是本地路径
active subprocess         仍属于原主机
```

所以本阶段的正式验收是：

```text
同一台机器上的多个独立进程共享控制面并恢复
```

真正跨主机必须再增加以下任一方案：

```text
共享 POSIX workspace（NFS/PVC）
workspace snapshot + rehydration
按 host/capability 做 Worker affinity
```

不要在本阶段通过“所有机器恰好挂载相同路径”来假装问题已经解决。

---

## 三、四类持久化事实的所有权

> **本节类型：知识说明，不修改项目代码。**

| 数据 | 所有者 | Schema 管理者 | 是否迁 PostgreSQL |
|---|---|---|---|
| Job/Resume/Event/Command | 应用 | Alembic | 是 |
| Artifact version/head | 应用 | Alembic | 是 |
| LangGraph checkpoint/writes | LangGraph | `PostgresSaver.setup()` | 是 |
| Artifact Blob | BlobStore | S3/MinIO 或 Local | 否 |
| run workspace | Execution runtime | 文件系统 | 否 |

最重要的边界是：

```text
Alembic 不管理 LangGraph 内部表
PostgresSaver.setup() 不管理应用业务表
```

`langgraph-checkpoint-postgres` 升级时可能调整它自己的迁移表。复制这些表到应用
Alembic revision 会形成两个 schema owner，后续升级无法判断谁负责。

---

## 四、不要在本阶段做双写

> **本节类型：迁移原则说明，不修改项目代码。**

错误方案：

```text
每次 submit/heartbeat/mark_* 同时写 SQLite 和 PostgreSQL
```

只要第二次写失败，就会出现：

```text
SQLite = running
PostgreSQL = queued
```

之后没有可靠办法知道哪一个才是事实源。

本阶段使用停写切换：

```text
1. 停 API submit/resume
2. 停 Worker
3. 备份 SQLite
4. 迁移 terminal metadata（可选）
5. 初始化 PostgreSQL schema/checkpoint
6. 切换所有进程环境变量
7. 启动 API/Worker
8. 新 Job 只写 PostgreSQL
```

处于 `queued/running/waiting_for_input/cancelling/reconciliation_required` 的旧任务不要
自动搬运。先在 SQLite 后端完成或人工取消，再切换。原因见第三十三节。

---

## 五、本阶段目标

> **本节类型：实现目标，不修改项目代码。**

1. 增加 SQLAlchemy 2.x 同步 Engine；
2. 增加 PostgreSQL runtime table metadata；
3. 使用 Alembic 管理应用表；
4. 实现完整 `PostgresJobStore`；
5. 使用 `FOR UPDATE SKIP LOCKED` 原子 claim；
6. 使用 `clock_timestamp()` 作为 lease 时间源；
7. 实现 `PostgresArtifactRepository`；
8. 让 Job 与 Artifact factory 选择 backend；
9. 让 checkpoint factory 支持 SQLite/PostgreSQL；
10. 提供显式 database/checkpoint setup CLI；
11. 提供 SQLite terminal metadata 迁移 CLI；
12. 增加双后端 contract tests；
13. 增加并发 claim、lease fencing 和跨进程 resume 测试；
14. 完成 PSTNet Worker A interrupt、Worker B resume 手工验收。

---

## 六、本阶段明确不做什么

> **本节类型：范围说明，不修改项目代码。**

- 不支持 MySQL；
- 不引入 Redis；
- 不引入 Kafka、RabbitMQ 或 Celery；
- 不异步化 FastAPI/SQLAlchemy；
- 不迁移 Artifact Blob；
- 不自动删除 SQLite 文件；
- 不双写 SQLite/PostgreSQL；
- 不直接复制 LangGraph 内部数据库表；
- 不自动迁移 active/waiting checkpoint；
- 不实现跨主机 workspace rehydration；
- 不让数据库连接跨 `fork()` 继承；
- 不在每次进程启动时自动执行 Alembic；
- 不把数据库密码打印到日志、Event 或 API。

---

## 七、需要新增和修改的文件

> **本节类型：文件清单，不修改项目代码。**

新增：

```text
app/persistence/__init__.py
app/persistence/database.py
app/persistence/tables.py

app/job_runtime/errors.py
app/job_runtime/postgres_store.py
app/storage/postgres_artifact_repository.py

alembic.ini
alembic/env.py
alembic/script.py.mako
alembic/versions/20260731_0001_runtime_and_artifact_tables.py

tests/job_store_contract.py
tests/test_postgres_job_store.py
tests/test_postgres_distributed_claim.py
tests/test_postgres_artifact_repository.py
tests/test_postgres_checkpoint.py
tests/test_postgres_cutover.py
```

修改：

```text
pyproject.toml
app/config.py
app/job_runtime/ports.py
app/job_runtime/store.py
app/job_runtime/factory.py
app/job_runtime/service.py
app/job_runtime/worker.py
app/job_runtime/heartbeat.py
app/job_runtime/process_reconcile.py
app/interaction/policy.py
app/interaction/artifacts.py
app/api/errors.py
app/storage/factory.py
app/memory/checkpoint.py
app/main.py
.env.example
.gitignore
tests/conftest.py
a_implementation_guides/README.md
```

---

## 八、增加 PostgreSQL 可选依赖

> **本节类型：需要修改依赖。**
>
> 修改：`pyproject.toml`

在 `[project.optional-dependencies]` 中增加：

```toml
postgres = [
    "SQLAlchemy>=2.0.51,<2.1",
    "alembic>=1.18,<2",
    "psycopg[binary,pool]>=3.2,<4",
    "langgraph-checkpoint-postgres>=3.1,<4",
]
```

安装：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent
python -m pip install -e ".[api,storage-s3,postgres,dev]"
```

为什么同时出现 SQLAlchemy pool 和 Psycopg pool：

```text
SQLAlchemy Engine pool：
    Job 与 Artifact repository 使用

Psycopg ConnectionPool：
    LangGraph PostgresSaver 使用
```

不要尝试让两个框架共用一个底层 connection 对象。分别设置小 pool，并计算总连接
预算。SQLAlchemy 官方建议每个数据库在单个进程中复用一个 Engine，并可使用
`pool_pre_ping` 处理失效连接。

参考：

- [SQLAlchemy Engine 与连接池](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [Psycopg pool](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)

---

## 九、增加 PostgreSQL 配置

> **本节类型：需要修改代码。**
>
> 修改：`app/config.py`

在 Phase 24 storage 配置之后增加：

```python
    # 只在 backend=postgresql 时读取；不要提供带密码的默认值。
    database_url: str | None = os.getenv(
        "DATABASE_URL"
    )

    database_pool_size: int = int(
        os.getenv("DATABASE_POOL_SIZE", "5")
    )
    database_max_overflow: int = int(
        os.getenv("DATABASE_MAX_OVERFLOW", "5")
    )
    database_pool_timeout_seconds: float = float(
        os.getenv(
            "DATABASE_POOL_TIMEOUT_SECONDS",
            "10",
        )
    )
    database_statement_timeout_ms: int = int(
        os.getenv(
            "DATABASE_STATEMENT_TIMEOUT_MS",
            "30000",
        )
    )
    database_lock_timeout_ms: int = int(
        os.getenv(
            "DATABASE_LOCK_TIMEOUT_MS",
            "5000",
        )
    )

    checkpoint_backend: str = os.getenv(
        "CHECKPOINT_BACKEND",
        "sqlite",
    )
    checkpoint_postgres_pool_min_size: int = int(
        os.getenv(
            "CHECKPOINT_POSTGRES_POOL_MIN_SIZE",
            "1",
        )
    )
    checkpoint_postgres_pool_max_size: int = int(
        os.getenv(
            "CHECKPOINT_POSTGRES_POOL_MAX_SIZE",
            "5",
        )
    )
```

把原来的 backend 校验扩展为：

```python
if settings.job_store_backend not in {
    "sqlite",
    "postgresql",
}:
    raise ValueError(
        "JOB_STORE_BACKEND 必须是 sqlite 或 postgresql"
    )

if settings.checkpoint_backend not in {
    "sqlite",
    "postgresql",
}:
    raise ValueError(
        "CHECKPOINT_BACKEND 必须是 sqlite 或 postgresql"
    )

uses_postgres = (
    settings.job_store_backend == "postgresql"
    or settings.checkpoint_backend == "postgresql"
)
if uses_postgres and not settings.database_url:
    raise ValueError(
        "PostgreSQL backend 需要 DATABASE_URL"
    )

if settings.database_pool_size < 1:
    raise ValueError(
        "DATABASE_POOL_SIZE 必须至少为 1"
    )

if (
    settings.checkpoint_postgres_pool_min_size < 1
    or settings.checkpoint_postgres_pool_max_size
    < settings.checkpoint_postgres_pool_min_size
):
    raise ValueError(
        "Checkpoint pool min/max 配置无效"
    )
```

Artifact metadata backend 与 Job backend 本阶段保持一致，不再增加第三个容易配错的
环境变量：

```text
JOB_STORE_BACKEND=sqlite
    -> SqliteJobStore + SqliteArtifactRepository

JOB_STORE_BACKEND=postgresql
    -> PostgresJobStore + PostgresArtifactRepository
```

---

## 十、抽离共享 JobStore 错误

> **本节类型：需要新增并修改代码。**
>
> 新增：`app/job_runtime/errors.py`

完整代码：

```python
class JobStoreError(RuntimeError):
    """Job control plane 错误基类。"""


class JobNotFoundError(JobStoreError):
    """目标 Job 不存在。"""


class JobConflictError(JobStoreError):
    """幂等身份、版本或当前状态冲突。"""


class LeaseLostError(JobStoreError):
    """claim token 已失效，旧 owner 不得继续写状态。"""


class JobBackendUnavailable(JobStoreError):
    """数据库连接或后端暂时不可用。"""
```

> 修改：`app/job_runtime/store.py`

删除文件内四个旧错误类，改为：

```python
from app.job_runtime.errors import (
    JobConflictError,
    JobNotFoundError,
    JobStoreError,
    LeaseLostError,
)
```

然后把以下文件中从 `app.job_runtime.store` 导入错误的代码统一改为从
`app.job_runtime.errors` 导入：

```text
app/job_runtime/service.py
app/job_runtime/worker.py
app/job_runtime/process_reconcile.py
app/interaction/policy.py
app/interaction/artifacts.py
app/api/errors.py
app/main.py
tests/ 中对应文件
```

不要让 `PostgresJobStore` 为了复用异常而反向 import `SqliteJobStore` 模块。

---

## 十一、给持久化端口增加生命周期与健康检查

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/ports.py`

在 `JobStore` Protocol 中增加：

```python
    def ping(self) -> None:
        """连接后端并执行最小只读检查。"""
        ...

    def close(self) -> None:
        """释放当前进程拥有的连接池资源。"""
        ...
```

> 修改：`app/job_runtime/store.py`

在 `SqliteJobStore` 增加兼容实现：

```python
    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    def close(self) -> None:
        # SQLite 实现每次方法调用创建 connection，没有常驻 pool。
        return None
```

这样 service/CLI 可以统一检查和关闭后端，不需要 `isinstance`。

---

## 十二、创建 Persistence 包

> **本节类型：需要新增代码。**
>
> 新增：`app/persistence/__init__.py`

```python
"""PostgreSQL application schema、Engine 与迁移支持。"""
```

---

## 十三、定义 PostgreSQL 应用表

> **本节类型：需要新增代码。**
>
> 新增：`app/persistence/tables.py`

完整代码：

```python
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": (
        "fk_%(table_name)s_%(column_0_name)s_"
        "%(referred_table_name)s"
    ),
    "pk": "pk_%(table_name)s",
}

metadata = sa.MetaData(
    naming_convention=NAMING_CONVENTION
)


jobs = sa.Table(
    "jobs",
    metadata,
    sa.Column("job_id", sa.Text, primary_key=True),
    sa.Column(
        "idempotency_key",
        sa.Text,
        nullable=False,
        unique=True,
    ),
    sa.Column("request_hash", sa.Text, nullable=False),
    sa.Column("thread_id", sa.Text, nullable=False, unique=True),
    sa.Column("run_id", sa.Text, nullable=False, unique=True),
    sa.Column("run_dir", sa.Text, nullable=False, unique=True),
    sa.Column("request_json", JSONB, nullable=False),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("version", sa.Integer, nullable=False, server_default="0"),
    sa.Column(
        "attempt_count",
        sa.Integer,
        nullable=False,
        server_default="0",
    ),
    sa.Column("max_attempts", sa.Integer, nullable=False),
    sa.Column(
        "wait_generation",
        sa.Integer,
        nullable=False,
        server_default="0",
    ),
    sa.Column("worker_id", sa.Text),
    sa.Column("claim_token", sa.Text),
    sa.Column("claimed_at", sa.DateTime(timezone=True)),
    sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column(
        "interrupt_nodes_json",
        JSONB,
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    ),
    sa.Column(
        "interrupts_json",
        JSONB,
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    ),
    sa.Column("pending_resume_id", sa.Text),
    sa.Column(
        "cancel_requested",
        sa.Boolean,
        nullable=False,
        server_default=sa.false(),
    ),
    sa.Column("cancellation_reason", sa.Text),
    sa.Column("result_json", JSONB),
    sa.Column("error_json", JSONB),
    sa.Column("reconciliation_json", JSONB),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "status IN ('queued','running','waiting_for_input',"
        "'cancelling','succeeded','failed','cancelled',"
        "'reconciliation_required')",
        name="valid_status",
    ),
)

sa.Index(
    "ix_jobs_claim",
    jobs.c.status,
    jobs.c.cancel_requested,
    jobs.c.available_at,
    jobs.c.created_at,
)
sa.Index(
    "ix_jobs_lease",
    jobs.c.status,
    jobs.c.lease_expires_at,
)


job_resumes = sa.Table(
    "job_resumes",
    metadata,
    sa.Column("resume_id", sa.Text, primary_key=True),
    sa.Column(
        "job_id",
        sa.Text,
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("wait_generation", sa.Integer, nullable=False),
    sa.Column("idempotency_key", sa.Text, nullable=False, unique=True),
    sa.Column("expected_node", sa.Text, nullable=False),
    sa.Column("value_json", JSONB, nullable=False),
    sa.Column("value_hash", sa.Text, nullable=False),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("consumed_at", sa.DateTime(timezone=True)),
    sa.UniqueConstraint(
        "job_id",
        "wait_generation",
        name="uq_job_resumes_job_generation",
    ),
    sa.CheckConstraint(
        "status IN ('pending','consumed')",
        name="valid_status",
    ),
)


job_events = sa.Table(
    "job_events",
    metadata,
    sa.Column(
        "event_id",
        sa.BigInteger,
        sa.Identity(),
        primary_key=True,
    ),
    sa.Column(
        "job_id",
        sa.Text,
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("event_type", sa.Text, nullable=False),
    sa.Column("actor", sa.Text, nullable=False),
    sa.Column("payload_json", JSONB, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)
sa.Index(
    "ix_job_events_job_event",
    job_events.c.job_id,
    job_events.c.event_id,
)


job_commands = sa.Table(
    "job_commands",
    metadata,
    sa.Column("command_id", sa.Text, primary_key=True),
    sa.Column(
        "job_id",
        sa.Text,
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("command_type", sa.Text, nullable=False),
    sa.Column("idempotency_key", sa.Text, nullable=False, unique=True),
    sa.Column("request_hash", sa.Text, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "command_type IN ('cancel')",
        name="valid_type",
    ),
)
sa.Index(
    "ix_job_commands_job_command",
    job_commands.c.job_id,
    job_commands.c.command_id,
)


artifact_versions = sa.Table(
    "artifact_versions",
    metadata,
    sa.Column("artifact_id", sa.Text, primary_key=True),
    sa.Column("sha256", sa.Text, primary_key=True),
    sa.Column("backend", sa.Text, primary_key=True),
    sa.Column("job_id", sa.Text, nullable=False),
    sa.Column("run_id", sa.Text, nullable=False),
    sa.Column("layer", sa.Text, nullable=False),
    sa.Column("relative_path", sa.Text, nullable=False),
    sa.Column("media_type", sa.Text, nullable=False),
    sa.Column("size_bytes", sa.BigInteger, nullable=False),
    sa.Column("producer_node", sa.Text, nullable=False),
    sa.Column("artifact_created_at", sa.Text, nullable=False),
    sa.Column("object_key", sa.Text, nullable=False),
    sa.Column("etag", sa.Text),
    sa.Column("object_version_id", sa.Text),
    sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "size_bytes >= 0",
        name="non_negative_size",
    ),
)


artifact_heads = sa.Table(
    "artifact_heads",
    metadata,
    sa.Column("artifact_id", sa.Text, primary_key=True),
    sa.Column("job_id", sa.Text, nullable=False),
    sa.Column("run_id", sa.Text, nullable=False),
    sa.Column("relative_path", sa.Text, nullable=False),
    sa.Column("current_sha256", sa.Text, nullable=False),
    sa.Column("current_backend", sa.Text, nullable=False),
    sa.Column("revision", sa.Integer, nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(
        [
            "artifact_id",
            "current_sha256",
            "current_backend",
        ],
        [
            "artifact_versions.artifact_id",
            "artifact_versions.sha256",
            "artifact_versions.backend",
        ],
        name="fk_artifact_heads_current_version",
    ),
    sa.UniqueConstraint(
        "job_id",
        "relative_path",
        name="uq_artifact_heads_job_path",
    ),
    sa.CheckConstraint(
        "revision >= 1",
        name="positive_revision",
    ),
)
sa.Index(
    "ix_artifact_heads_job_artifact",
    artifact_heads.c.job_id,
    artifact_heads.c.artifact_id,
)
```

Artifact 表没有到 `jobs` 的外键。这是刻意的：Blob-first 发布可能在 Job metadata
迁移或灾难恢复期间单独重建 Catalog。应用层仍会校验 `job_id/run_id` 身份。

---

## 十四、实现 SQLAlchemy Engine 生命周期

> **本节类型：需要新增代码。**
>
> 新增：`app/persistence/database.py`

完整代码：

```python
from __future__ import annotations

import atexit
import os
import threading
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url

from app.config import settings


_lock = threading.Lock()
_engine: Engine | None = None
_engine_pid: int | None = None


def require_database_url() -> str:
    value = settings.database_url
    if not value:
        raise RuntimeError(
            "DATABASE_URL 未配置"
        )
    parsed = make_url(value)
    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError(
            "Phase 25 DATABASE_URL 必须指向 PostgreSQL"
        )
    return value


def build_engine() -> Engine:
    """返回当前进程唯一 Engine；fork 后重新创建 pool。"""

    global _engine, _engine_pid
    pid = os.getpid()
    with _lock:
        if _engine is not None and _engine_pid == pid:
            return _engine

        if _engine is not None:
            # 子进程不能继承父进程已经建立的 socket。
            _engine.dispose(close=False)

        options = (
            "-c statement_timeout="
            f"{settings.database_statement_timeout_ms} "
            "-c lock_timeout="
            f"{settings.database_lock_timeout_ms}"
        )
        _engine = sa.create_engine(
            require_database_url(),
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=(
                settings.database_max_overflow
            ),
            pool_timeout=(
                settings.database_pool_timeout_seconds
            ),
            connect_args={
                "options": options,
                "application_name": (
                    "paper-reproduction-copilot"
                ),
            },
        )
        _engine_pid = pid
        return _engine


def database_clock(
    connection: sa.Connection,
) -> datetime:
    """
    使用真实推进的数据库时钟。

    PostgreSQL now()/CURRENT_TIMESTAMP 在一个事务中固定；lease 语义使用
    clock_timestamp() 更明确。
    """

    return connection.execute(
        sa.select(sa.func.clock_timestamp())
    ).scalar_one()


def psycopg_conninfo() -> str:
    """把 SQLAlchemy URL 转为 Psycopg 可接受的 URL。"""

    parsed = make_url(require_database_url())
    return parsed.set(
        drivername="postgresql"
    ).render_as_string(hide_password=False)


def ping_database() -> None:
    with build_engine().connect() as connection:
        connection.execute(sa.text("SELECT 1"))


def close_engine() -> None:
    global _engine, _engine_pid
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _engine_pid = None


atexit.register(close_engine)
```

不要打印 `require_database_url()` 或 `psycopg_conninfo()` 的返回值。

---

## 十五、Alembic 初始化与 ownership

> **本节类型：需要新增配置和迁移代码。**

在项目根目录执行一次：

```bash
alembic init alembic
```

> 新增：`alembic.ini`

保留生成文件的大部分默认值，但把 URL 留空：

```ini
[alembic]
script_location = %(here)s/alembic
prepend_sys_path = .
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

> 修改：`alembic/env.py`

完整代码：

```python
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.persistence.database import (
    require_database_url,
)
from app.persistence.tables import metadata


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option(
    "sqlalchemy.url",
    require_database_url().replace("%", "%%"),
)
target_metadata = metadata
application_tables = set(metadata.tables)


def include_name(
    name: str | None,
    type_: str,
    parent_names: dict,
) -> bool:
    """Alembic 只反射应用表，不接管 LangGraph Saver 表。"""

    del parent_names
    if type_ == "table":
        return name in application_tables
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

生成初始 revision：

```bash
alembic revision \
  --autogenerate \
  -m "runtime and artifact tables"
```

把文件重命名为容易识别的：

```text
alembic/versions/20260731_0001_runtime_and_artifact_tables.py
```

必须人工检查生成 revision：

- 只包含第十三节定义的 6 张应用表；
- 不包含 `checkpoints`、`checkpoint_writes` 等 LangGraph 表；
- JSON 字段是 PostgreSQL `JSONB`；
- 所有 timestamp 都是 `timezone=True`；
- `job_events.event_id` 是 identity/bigint；
- claim 和 lease 索引存在；
- Artifact composite foreign key 存在；
- downgrade 按外键反序删除表。

Alembic 官方明确说明 autogenerate 生成的是 candidate migration，必须人工审查；CI
再使用 `alembic check` 防止 model 与 revision 漂移。

参考：[Alembic autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)

---

## 十六、PostgresJobStore 的实现策略

> **本节类型：核心实现说明，不修改项目代码。**

`PostgresJobStore` 必须完整实现 Phase 24 的 `JobStore` Protocol，不能只实现
`submit/claim_next` 后让其余路径回退 SQLite。

每个方法遵守相同模板：

```text
engine.begin()
    -> database_clock(connection)
    -> 锁定/读取当前行
    -> 校验 version/status/claim token
    -> 更新 Job
    -> 同事务写 Event/Resume/Command
    -> 返回更新后的 JobRecord
commit
```

事务中不能包含：

```text
LLM 调用
Graph stream
S3 上传
subprocess
文件 hash
sleep/retry backoff
```

否则一个 Job row lock 会被持有数分钟。

---

## 十七、实现 PostgresJobStore 公共骨架

> **本节类型：需要新增代码。**
>
> 新增：`app/job_runtime/postgres_store.py`

先写文件头、转换函数和公共 helper：

```python
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.job_runtime.errors import (
    JobBackendUnavailable,
    JobConflictError,
    JobNotFoundError,
    LeaseLostError,
)
from app.job_runtime.schemas import (
    HeartbeatResult,
    JobClaim,
    JobEvent,
    JobInterrupt,
    JobRecord,
    JobRequest,
    JobResumeRequest,
)
from app.persistence.database import (
    build_engine,
    database_clock,
)
from app.persistence.tables import (
    job_commands,
    job_events,
    job_resumes,
    jobs,
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _json_hash(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class PostgresJobStore:
    """PostgreSQL JobStore；schema 只能由 Alembic 创建。"""

    def __init__(self, engine: Engine | None = None):
        self.engine = engine or build_engine()

    def initialize(self) -> None:
        # 不在应用启动时 create_all 或执行 Alembic。
        self.ping()

    def ping(self) -> None:
        try:
            with self.engine.connect() as connection:
                connection.execute(sa.text("SELECT 1"))
        except DBAPIError as exc:
            raise JobBackendUnavailable(
                "PostgreSQL JobStore 不可用"
            ) from exc

    def close(self) -> None:
        # 全局 Engine 由 app.persistence.database 统一释放。
        return None

    def _append_event(
        self,
        connection: sa.Connection,
        *,
        job_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        connection.execute(
            job_events.insert().values(
                job_id=job_id,
                event_type=event_type,
                actor=actor[:100],
                payload_json=payload,
                created_at=now,
            )
        )

    def _row_to_record(
        self,
        row: RowMapping,
    ) -> JobRecord:
        return JobRecord(
            job_id=row["job_id"],
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            thread_id=row["thread_id"],
            run_id=row["run_id"],
            run_dir=row["run_dir"],
            request=JobRequest.model_validate(
                row["request_json"]
            ),
            status=row["status"],
            version=row["version"],
            attempt_count=row["attempt_count"],
            max_attempts=row["max_attempts"],
            wait_generation=row["wait_generation"],
            worker_id=row["worker_id"],
            claim_token=row["claim_token"],
            claimed_at=_iso(row["claimed_at"]),
            heartbeat_at=_iso(row["heartbeat_at"]),
            lease_expires_at=_iso(
                row["lease_expires_at"]
            ),
            available_at=_iso(row["available_at"]),
            interrupt_nodes=list(
                row["interrupt_nodes_json"] or []
            ),
            interrupts=[
                JobInterrupt.model_validate(item)
                for item in (
                    row["interrupts_json"] or []
                )
            ],
            pending_resume_id=row[
                "pending_resume_id"
            ],
            cancel_requested=bool(
                row["cancel_requested"]
            ),
            cancellation_reason=row[
                "cancellation_reason"
            ],
            result=row["result_json"],
            error=row["error_json"],
            reconciliation=row[
                "reconciliation_json"
            ],
            created_at=_iso(row["created_at"]),
            updated_at=_iso(row["updated_at"]),
        )

    def _row_to_resume(
        self,
        row: RowMapping,
    ) -> JobResumeRequest:
        return JobResumeRequest(
            resume_id=row["resume_id"],
            job_id=row["job_id"],
            wait_generation=row["wait_generation"],
            idempotency_key=row["idempotency_key"],
            expected_node=row["expected_node"],
            value=row["value_json"],
            value_hash=row["value_hash"],
            status=row["status"],
            created_at=_iso(row["created_at"]),
            consumed_at=_iso(row["consumed_at"]),
        )

    def _get_row(
        self,
        connection: sa.Connection,
        job_id: str,
        *,
        for_update: bool = False,
    ) -> RowMapping:
        statement = sa.select(jobs).where(
            jobs.c.job_id == job_id
        )
        if for_update:
            statement = statement.with_for_update()
        row = connection.execute(
            statement
        ).mappings().one_or_none()
        if row is None:
            raise JobNotFoundError(
                f"未找到 job_id={job_id}"
            )
        return row

    def _owned_row(
        self,
        connection: sa.Connection,
        *,
        job_id: str,
        claim_token: str,
    ) -> RowMapping:
        row = self._get_row(
            connection,
            job_id,
            for_update=True,
        )
        if (
            row["status"]
            not in {"running", "cancelling"}
            or row["claim_token"] != claim_token
        ):
            raise LeaseLostError(
                "Job claim 已失效"
            )
        return row

    def get(self, job_id: str) -> JobRecord:
        with self.engine.connect() as connection:
            return self._row_to_record(
                self._get_row(connection, job_id)
            )
```

后续各节的方法都追加到同一个 `PostgresJobStore` 类中，不要创建多个同名类。

---

## 十八、实现 submit、list 与 Event 查询

> **本节类型：需要继续修改代码。**
>
> 继续修改：`app/job_runtime/postgres_store.py`

在类中追加：

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
        max_attempts: int,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
        # PostgreSQL backend 忽略调用方 wall clock，统一使用 DB clock。
        del now
        request_payload = request.model_dump()
        request_hash = _json_hash(
            {
                "thread_id": thread_id,
                "request": request_payload,
            }
        )

        try:
            with self.engine.begin() as connection:
                current = database_clock(connection)
                statement = (
                    insert(jobs)
                    .values(
                        job_id=job_id,
                        idempotency_key=idempotency_key,
                        request_hash=request_hash,
                        thread_id=thread_id,
                        run_id=run_id,
                        run_dir=run_dir,
                        request_json=request_payload,
                        status="queued",
                        version=0,
                        attempt_count=0,
                        max_attempts=max_attempts,
                        wait_generation=0,
                        available_at=current,
                        created_at=current,
                        updated_at=current,
                    )
                    .on_conflict_do_nothing()
                    .returning(jobs.c.job_id)
                )
                inserted = connection.execute(
                    statement
                ).scalar_one_or_none()

                if inserted is None:
                    existing = connection.execute(
                        sa.select(jobs).where(
                            jobs.c.idempotency_key
                            == idempotency_key
                        )
                    ).mappings().one_or_none()
                    if existing is None:
                        raise JobConflictError(
                            "thread_id、run_id 或 run_dir 已存在"
                        )
                    if existing["request_hash"] != request_hash:
                        raise JobConflictError(
                            "相同 idempotency_key 对应不同请求"
                        )
                    return self._row_to_record(existing), False

                self._append_event(
                    connection,
                    job_id=job_id,
                    event_type="job_submitted",
                    actor="client",
                    payload={
                        "thread_id": thread_id,
                        "run_id": run_id,
                    },
                    now=current,
                )
                row = self._get_row(connection, job_id)
                return self._row_to_record(row), True
        except IntegrityError as exc:
            raise JobConflictError(
                "Job 唯一身份冲突"
            ) from exc
        except DBAPIError as exc:
            raise JobBackendUnavailable(
                "PostgreSQL submit 失败"
            ) from exc

    def list_jobs(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[JobRecord]:
        statement = sa.select(jobs)
        if status is not None:
            statement = statement.where(
                jobs.c.status == status
            )
        statement = statement.order_by(
            jobs.c.created_at.desc()
        ).limit(max(1, min(limit, 500)))
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement
            ).mappings().all()
        return [self._row_to_record(row) for row in rows]

    def _event_from_row(
        self,
        row: RowMapping,
    ) -> JobEvent:
        return JobEvent(
            event_id=row["event_id"],
            job_id=row["job_id"],
            event_type=row["event_type"],
            actor=row["actor"],
            payload=row["payload_json"],
            created_at=_iso(row["created_at"]),
        )

    def list_events(
        self,
        job_id: str,
        *,
        limit: int = 200,
    ) -> list[JobEvent]:
        statement = (
            sa.select(job_events)
            .where(job_events.c.job_id == job_id)
            .order_by(job_events.c.event_id.desc())
            .limit(max(1, min(limit, 1000)))
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement
            ).mappings().all()
        rows.reverse()
        return [self._event_from_row(row) for row in rows]

    def list_events_after(
        self,
        job_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        statement = (
            sa.select(job_events)
            .where(
                job_events.c.job_id == job_id,
                job_events.c.event_id > after_event_id,
            )
            .order_by(job_events.c.event_id.asc())
            .limit(max(1, min(limit, 1000)))
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement
            ).mappings().all()
        return [self._event_from_row(row) for row in rows]
```

`ON CONFLICT DO NOTHING` 后必须再次按 idempotency key 读取并比对 hash。不能把所有
unique conflict 都当成一次幂等重放。

---

## 十九、实现原子 Multi-Worker Claim

> **本节类型：需要继续修改代码。**
>
> 继续修改：`app/job_runtime/postgres_store.py`

在类中追加：

```python
    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: float,
        now: float | None = None,
    ) -> JobClaim | None:
        del now
        claim_token = f"claim_{uuid4().hex}"

        with self.engine.begin() as connection:
            current = database_clock(connection)
            candidate = connection.execute(
                sa.select(jobs.c.job_id)
                .where(
                    jobs.c.status == "queued",
                    jobs.c.cancel_requested.is_(False),
                    jobs.c.available_at <= current,
                )
                .order_by(
                    jobs.c.available_at.asc(),
                    jobs.c.created_at.asc(),
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            ).scalar_one_or_none()
            if candidate is None:
                return None

            lease_expires = current + timedelta(
                seconds=lease_seconds
            )
            connection.execute(
                jobs.update()
                .where(jobs.c.job_id == candidate)
                .values(
                    status="running",
                    version=jobs.c.version + 1,
                    attempt_count=(
                        jobs.c.attempt_count + 1
                    ),
                    worker_id=worker_id,
                    claim_token=claim_token,
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
                actor=worker_id,
                payload={
                    "attempt_count": row["attempt_count"],
                },
                now=current,
            )
            return JobClaim(
                job=self._row_to_record(row),
                claim_token=claim_token,
                resume_request=resume,
            )
```

关键点：

```text
SELECT row lock
UPDATE ownership
读取 pending resume
写 job_claimed event
```

全部发生在同一个短事务中。不要先 `SELECT`、commit，再单独 `UPDATE`。

---

## 二十、实现 heartbeat 与 fencing

> **本节类型：需要继续修改代码。**
>
> 继续修改：`app/job_runtime/postgres_store.py`

```python
    def heartbeat(
        self,
        *,
        job_id: str,
        claim_token: str,
        lease_seconds: float,
        now: float | None = None,
    ) -> HeartbeatResult:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            lease_expires = current + timedelta(
                seconds=lease_seconds
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    heartbeat_at=current,
                    lease_expires_at=lease_expires,
                    updated_at=current,
                )
            )
            return HeartbeatResult(
                lease_renewed=True,
                cancel_requested=bool(
                    row["cancel_requested"]
                ),
                cancellation_reason=row[
                    "cancellation_reason"
                ],
                lease_expires_at=lease_expires.isoformat(),
            )
```

所有 `mark_*` 方法也必须调用 `_owned_row()`。数据库 row lock 不能替代 claim token：
旧 Worker 可能在 lease 过期后才恢复运行，此时必须被新的 token 拒绝。

---

## 二十一、完整移植剩余状态转换方法

> **本节类型：需要继续修改代码。**
>
> 继续修改：`app/job_runtime/postgres_store.py`

以下方法不能遗漏：

```text
mark_waiting
mark_succeeded
mark_cancelled
mark_failed
queue_resume
request_cancel
list_expired_running
requeue_expired
require_reconciliation
resolve_reconciliation
```

这里不建议重新设计业务语义。逐个对照 `SqliteJobStore`，只替换事务和 SQL 表达：

| SQLite 语义 | PostgreSQL 写法 |
|---|---|
| `BEGIN IMMEDIATE` | `engine.begin()` + 必要行 `FOR UPDATE` |
| `?` 参数 | SQLAlchemy expression/bind parameter |
| JSON string | JSONB Python dict/list |
| epoch float | timezone-aware `datetime` |
| `time.time()` | `database_clock(connection)` |
| `AUTOINCREMENT` | identity bigint |
| `INSERT OR IGNORE` | `ON CONFLICT DO NOTHING` |

为了防止“看起来实现了但语义遗漏”，每个方法必须满足下面的实现清单：

### 21.1 `mark_waiting`

```text
锁定 owned row
consume pending resume
status = waiting_for_input
version += 1
wait_generation += 1
清空 ownership
保存 bounded interrupts/result
写 job_waiting_for_input event
```

### 21.2 `mark_succeeded`

```text
锁定 owned row
consume pending resume
status = succeeded
version += 1
清空 ownership/pending_resume_id
保存 result，清空 error
写 job_succeeded event
```

### 21.3 `mark_cancelled`

```text
锁定 owned row
consume pending resume
status = cancelled
cancel_requested = true
清空 ownership
写 job_cancelled event
```

### 21.4 `mark_failed`

```text
锁定 owned row
can_retry = retryable and not cancel_requested and attempt_count < max_attempts
retry 时 status=queued、DB current + bounded backoff、保留 pending resume
不 retry 时 failed/cancelled、consume pending resume
清空 ownership
保存 error
同事务写 retry_scheduled/failed/cancelled event
```

### 21.5 `queue_resume`

```text
FOR UPDATE 锁 Job
校验 waiting_for_input/version/wait_generation/node
按 idempotency_key 查旧 resume 并比较 value hash
按 (job_id, wait_generation) 拒绝第二个不同 resume
插入 pending resume
Job status=queued、version+=1、pending_resume_id=新值
写 job_resume_queued event
```

### 21.6 `request_cancel`

```text
FOR UPDATE 锁 Job
幂等 command key + request hash
校验 expected version
terminal Job 不反向变更
queued/waiting -> cancelled
running -> cancelling
写 command 与 Job event 同一事务
```

### 21.7 Lease reconciliation

```text
list_expired_running 使用 DB clock
requeue/require_reconciliation 再次锁行并核对 expired claim token
resolve_reconciliation 只允许 reconciliation_required
```

### 21.8 剩余方法完整参考实现

把下面代码继续追加到同一个 `PostgresJobStore` 类中：

```python
    def _consume_pending_resume(
        self,
        connection: sa.Connection,
        *,
        pending_resume_id: str | None,
        now: datetime,
    ) -> None:
        if pending_resume_id is None:
            return
        connection.execute(
            job_resumes.update()
            .where(
                job_resumes.c.resume_id
                == pending_resume_id,
                job_resumes.c.status == "pending",
            )
            .values(
                status="consumed",
                consumed_at=now,
            )
        )

    def mark_waiting(
        self,
        *,
        job_id: str,
        claim_token: str,
        interrupts: list[JobInterrupt],
        result: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            self._consume_pending_resume(
                connection,
                pending_resume_id=row[
                    "pending_resume_id"
                ],
                now=current,
            )
            nodes = sorted(
                {item.node for item in interrupts}
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    status="waiting_for_input",
                    version=jobs.c.version + 1,
                    wait_generation=(
                        jobs.c.wait_generation + 1
                    ),
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    pending_resume_id=None,
                    interrupt_nodes_json=nodes,
                    interrupts_json=[
                        item.model_dump()
                        for item in interrupts
                    ],
                    result_json=result,
                    error_json=None,
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_waiting_for_input",
                actor=actor,
                payload={"interrupt_nodes": nodes},
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def mark_succeeded(
        self,
        *,
        job_id: str,
        claim_token: str,
        result: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            self._consume_pending_resume(
                connection,
                pending_resume_id=row[
                    "pending_resume_id"
                ],
                now=current,
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    status="succeeded",
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    pending_resume_id=None,
                    interrupt_nodes_json=[],
                    interrupts_json=[],
                    result_json=result,
                    error_json=None,
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_succeeded",
                actor=actor,
                payload={},
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def mark_cancelled(
        self,
        *,
        job_id: str,
        claim_token: str,
        reason: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            self._consume_pending_resume(
                connection,
                pending_resume_id=row[
                    "pending_resume_id"
                ],
                now=current,
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    status="cancelled",
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    pending_resume_id=None,
                    cancel_requested=True,
                    cancellation_reason=reason[:500],
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_cancelled",
                actor=actor,
                payload={"reason": reason[:500]},
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def mark_failed(
        self,
        *,
        job_id: str,
        claim_token: str,
        error: dict[str, Any],
        actor: str,
        retryable: bool = False,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            can_retry = (
                retryable
                and not row["cancel_requested"]
                and row["attempt_count"]
                < row["max_attempts"]
            )
            if can_retry:
                delay = min(
                    60.0,
                    2.0
                    ** max(
                        row["attempt_count"] - 1,
                        0,
                    ),
                )
                target = "queued"
                available_at = current + timedelta(
                    seconds=delay
                )
                event_type = "job_retry_scheduled"
                pending_resume_id = row[
                    "pending_resume_id"
                ]
            else:
                target = (
                    "cancelled"
                    if row["cancel_requested"]
                    else "failed"
                )
                available_at = current
                event_type = f"job_{target}"
                pending_resume_id = None
                self._consume_pending_resume(
                    connection,
                    pending_resume_id=row[
                        "pending_resume_id"
                    ],
                    now=current,
                )

            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    status=target,
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    pending_resume_id=pending_resume_id,
                    available_at=available_at,
                    error_json=error,
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=event_type,
                actor=actor,
                payload={
                    "retryable": retryable,
                    "error_type": error.get("type"),
                    "available_at": (
                        available_at.isoformat()
                    ),
                },
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

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
        del now
        value_hash = _json_hash(value)
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._get_row(
                connection,
                job_id,
                for_update=True,
            )
            replay = connection.execute(
                sa.select(job_resumes).where(
                    job_resumes.c.idempotency_key
                    == idempotency_key
                )
            ).mappings().one_or_none()
            if replay is not None:
                if (
                    replay["job_id"] != job_id
                    or replay["expected_node"]
                    != expected_node
                    or replay["value_hash"] != value_hash
                ):
                    raise JobConflictError(
                        "resume idempotency key 冲突"
                    )
                return self._row_to_record(row), False

            if row["status"] != "waiting_for_input":
                raise JobConflictError(
                    "Job 当前不在 waiting_for_input"
                )
            if (
                expected_job_version is not None
                and row["version"]
                != expected_job_version
            ):
                raise JobConflictError("Job version 已变化")
            if (
                expected_wait_generation is not None
                and row["wait_generation"]
                != expected_wait_generation
            ):
                raise JobConflictError(
                    "wait_generation 已变化"
                )
            nodes = sorted(
                set(row["interrupt_nodes_json"] or [])
            )
            if nodes != [expected_node]:
                raise JobConflictError(
                    "resume node 与当前 interrupt 不匹配"
                )
            same_generation = connection.execute(
                sa.select(job_resumes.c.resume_id).where(
                    job_resumes.c.job_id == job_id,
                    job_resumes.c.wait_generation
                    == row["wait_generation"],
                )
            ).scalar_one_or_none()
            if same_generation is not None:
                raise JobConflictError(
                    "当前 generation 已存在 resume"
                )

            resume_id = f"resume_{uuid4().hex}"
            connection.execute(
                job_resumes.insert().values(
                    resume_id=resume_id,
                    job_id=job_id,
                    wait_generation=row[
                        "wait_generation"
                    ],
                    idempotency_key=idempotency_key,
                    expected_node=expected_node,
                    value_json=value,
                    value_hash=value_hash,
                    status="pending",
                    created_at=current,
                )
            )
            connection.execute(
                jobs.update()
                .where(jobs.c.job_id == job_id)
                .values(
                    status="queued",
                    version=jobs.c.version + 1,
                    pending_resume_id=resume_id,
                    interrupt_nodes_json=[],
                    interrupts_json=[],
                    available_at=current,
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_resume_queued",
                actor=actor,
                payload={
                    "expected_node": expected_node,
                    "wait_generation": row[
                        "wait_generation"
                    ],
                },
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            ), True

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
        del now
        command_key = idempotency_key or (
            f"cancel:{job_id}:{uuid4().hex}"
        )
        request_hash = _json_hash(
            {"job_id": job_id, "reason": reason}
        )
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._get_row(
                connection,
                job_id,
                for_update=True,
            )
            existing = connection.execute(
                sa.select(job_commands).where(
                    job_commands.c.idempotency_key
                    == command_key
                )
            ).mappings().one_or_none()
            if existing is not None:
                if (
                    existing["job_id"] != job_id
                    or existing["request_hash"]
                    != request_hash
                ):
                    raise JobConflictError(
                        "cancel idempotency key 冲突"
                    )
                return self._row_to_record(row)

            if (
                expected_job_version is not None
                and row["version"]
                != expected_job_version
            ):
                raise JobConflictError("Job version 已变化")
            connection.execute(
                job_commands.insert().values(
                    command_id=f"command_{uuid4().hex}",
                    job_id=job_id,
                    command_type="cancel",
                    idempotency_key=command_key,
                    request_hash=request_hash,
                    created_at=current,
                )
            )
            if row["status"] in {
                "succeeded",
                "failed",
                "cancelled",
            }:
                return self._row_to_record(row)

            if row["status"] in {
                "queued",
                "waiting_for_input",
                "reconciliation_required",
            }:
                target = "cancelled"
                owner_values = {
                    "worker_id": None,
                    "claim_token": None,
                    "claimed_at": None,
                    "heartbeat_at": None,
                    "lease_expires_at": None,
                    "pending_resume_id": None,
                }
                self._consume_pending_resume(
                    connection,
                    pending_resume_id=row[
                        "pending_resume_id"
                    ],
                    now=current,
                )
            else:
                target = "cancelling"
                owner_values = {}

            connection.execute(
                jobs.update()
                .where(jobs.c.job_id == job_id)
                .values(
                    status=target,
                    version=jobs.c.version + 1,
                    cancel_requested=True,
                    cancellation_reason=reason[:500],
                    updated_at=current,
                    **owner_values,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_cancelled"
                    if target == "cancelled"
                    else "job_cancellation_requested"
                ),
                actor=actor,
                payload={"reason": reason[:500]},
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def list_expired_running(
        self,
        *,
        now: float | None = None,
        limit: int = 100,
    ) -> list[JobRecord]:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            rows = connection.execute(
                sa.select(jobs)
                .where(
                    jobs.c.status.in_(
                        ["running", "cancelling"]
                    ),
                    jobs.c.lease_expires_at <= current,
                )
                .order_by(jobs.c.lease_expires_at)
                .limit(max(1, min(limit, 500)))
            ).mappings().all()
        return [self._row_to_record(row) for row in rows]

    def _lock_expired(
        self,
        connection: sa.Connection,
        *,
        job_id: str,
        expired_claim_token: str,
        current: datetime,
    ) -> RowMapping:
        row = self._get_row(
            connection,
            job_id,
            for_update=True,
        )
        if (
            row["status"]
            not in {"running", "cancelling"}
            or row["claim_token"]
            != expired_claim_token
            or row["lease_expires_at"] > current
        ):
            raise LeaseLostError(
                "stale Job 已被其他 Worker 处理"
            )
        return row

    def requeue_expired(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._lock_expired(
                connection,
                job_id=job_id,
                expired_claim_token=expired_claim_token,
                current=current,
            )
            if row["cancel_requested"]:
                target = "cancelled"
            elif row["attempt_count"] >= row["max_attempts"]:
                target = "failed"
            else:
                target = "queued"
            error = (
                {
                    "type": "LeaseAttemptsExhausted",
                    "message": detail[:1000],
                }
                if target == "failed"
                else None
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token
                    == expired_claim_token,
                )
                .values(
                    status=target,
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    available_at=current,
                    error_json=error,
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_lease_requeued"
                    if target == "queued"
                    else f"job_{target}"
                ),
                actor=actor,
                payload={"detail": detail[:1000]},
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def require_reconciliation(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        reconciliation: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            self._lock_expired(
                connection,
                job_id=job_id,
                expired_claim_token=expired_claim_token,
                current=current,
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token
                    == expired_claim_token,
                )
                .values(
                    status="reconciliation_required",
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    reconciliation_json=reconciliation,
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_reconciliation_required"
                ),
                actor=actor,
                payload=reconciliation,
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def resolve_reconciliation(
        self,
        *,
        job_id: str,
        decision: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        if decision not in {
            "requeue",
            "failed",
            "cancelled",
        }:
            raise ValueError(
                "无效 reconciliation decision"
            )
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._get_row(
                connection,
                job_id,
                for_update=True,
            )
            if row["status"] != "reconciliation_required":
                raise JobConflictError(
                    "Job 当前不需要 reconciliation"
                )
            target = (
                "queued"
                if decision == "requeue"
                else decision
            )
            error = (
                {
                    "type": "ManualReconciliation",
                    "message": detail[:1000],
                }
                if target == "failed"
                else row["error_json"]
            )
            connection.execute(
                jobs.update()
                .where(jobs.c.job_id == job_id)
                .values(
                    status=target,
                    version=jobs.c.version + 1,
                    available_at=current,
                    reconciliation_json=None,
                    error_json=error,
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_reconciliation_resolved"
                ),
                actor=actor,
                payload={
                    "decision": decision,
                    "detail": detail[:1000],
                },
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )
```

这段参考实现必须继续通过原 SQLite 语义测试。若当前 `SqliteJobStore` 在某个边界上
已有更严格行为，以现有测试为准同步修正 PostgreSQL 实现，而不是放宽 contract。

> **暂停点：不要在 contract tests 全绿前进入 checkpoint 改造。**
>
> 这部分代码行数较多，最可靠的方法是保留 `SqliteJobStore` 每个方法旁的语义注释，
> 一次移植一个方法并立即运行同一 contract。不要一次性凭记忆重写十个状态转换。

---

## 二十二、更新 JobStore Factory

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/factory.py`

完整代码：

```python
from app.config import settings
from app.job_runtime.ports import JobStore


def build_job_store() -> JobStore:
    """唯一 JobStore composition root。"""

    if settings.job_store_backend == "sqlite":
        from app.job_runtime.store import (
            SqliteJobStore,
        )

        store: JobStore = SqliteJobStore(
            settings.job_db_path
        )
    elif settings.job_store_backend == "postgresql":
        from app.job_runtime.postgres_store import (
            PostgresJobStore,
        )

        store = PostgresJobStore()
    else:
        raise ValueError(
            "不支持的 JOB_STORE_BACKEND："
            f"{settings.job_store_backend}"
        )

    store.initialize()
    return store
```

动态 import 保证只安装基础依赖时，SQLite 测试不会因为缺少 SQLAlchemy/Psycopg 而
无法收集。

### 22.1 映射 Control Plane 暂时不可用

> 修改：`app/api/errors.py`

增加 import：

```python
from app.job_runtime.errors import (
    JobBackendUnavailable,
)
```

在 `install_error_handlers()` 中增加：

```python
    @app.exception_handler(
        JobBackendUnavailable
    )
    async def handle_job_backend_unavailable(
        request: Request,
        exc: JobBackendUnavailable,
    ) -> JSONResponse:
        del exc
        return _response(
            request,
            status_code=503,
            code="JOB_BACKEND_UNAVAILABLE",
            message="任务控制面暂时不可用",
        )
```

不要把 Psycopg exception、host、database name 或 DSN 返回给客户端。

---

## 二十三、实现 PostgreSQL Artifact Repository

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/postgres_artifact_repository.py`

完整代码：

```python
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine, RowMapping

from app.persistence.database import (
    build_engine,
    database_clock,
)
from app.persistence.tables import (
    artifact_heads,
    artifact_versions,
)
from app.storage.errors import (
    ArtifactIntegrityError,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)


class PostgresArtifactRepository:
    def __init__(self, engine: Engine | None = None):
        self.engine = engine or build_engine()

    def initialize(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(sa.text("SELECT 1"))

    def _joined(self) -> sa.Select:
        return sa.select(
            artifact_versions,
            artifact_heads.c.revision,
        ).join(
            artifact_heads,
            sa.and_(
                artifact_heads.c.artifact_id
                == artifact_versions.c.artifact_id,
                artifact_heads.c.current_sha256
                == artifact_versions.c.sha256,
                artifact_heads.c.current_backend
                == artifact_versions.c.backend,
            ),
        )

    def _to_published(
        self,
        row: RowMapping,
    ) -> PublishedArtifact:
        return PublishedArtifact(
            job_id=row["job_id"],
            descriptor=ArtifactDescriptor(
                artifact_id=row["artifact_id"],
                run_id=row["run_id"],
                layer=row["layer"],
                relative_path=row["relative_path"],
                media_type=row["media_type"],
                sha256=row["sha256"],
                size_bytes=row["size_bytes"],
                producer_node=row["producer_node"],
                created_at=row["artifact_created_at"],
            ),
            backend=row["backend"],
            object_key=row["object_key"],
            etag=row["etag"],
            object_version_id=row[
                "object_version_id"
            ],
            revision=row["revision"],
            published_at=row[
                "published_at"
            ].isoformat(),
        )

    def publish(
        self,
        *,
        job_id: str,
        descriptor: ArtifactDescriptor,
        blob: BlobStat,
    ) -> PublishedArtifact:
        if (
            descriptor.sha256 != blob.sha256
            or descriptor.size_bytes != blob.size_bytes
        ):
            raise ArtifactIntegrityError(
                "Blob 与 ArtifactDescriptor 不一致"
            )

        with self.engine.begin() as connection:
            current = database_clock(connection)
            # 相同 artifact_id 串行；不同 Artifact 不互相阻塞。
            connection.execute(
                sa.select(
                    sa.func.pg_advisory_xact_lock(
                        sa.func.hashtextextended(
                            descriptor.artifact_id,
                            0,
                        )
                    )
                )
            )
            head = connection.execute(
                sa.select(artifact_heads)
                .where(
                    artifact_heads.c.artifact_id
                    == descriptor.artifact_id
                )
                .with_for_update()
            ).mappings().one_or_none()

            if head is not None and (
                head["job_id"] != job_id
                or head["run_id"] != descriptor.run_id
                or head["relative_path"]
                != descriptor.relative_path
            ):
                raise ArtifactIntegrityError(
                    "artifact_id 身份发生冲突"
                )

            version_values = {
                "artifact_id": descriptor.artifact_id,
                "sha256": descriptor.sha256,
                "backend": blob.backend,
                "job_id": job_id,
                "run_id": descriptor.run_id,
                "layer": descriptor.layer,
                "relative_path": descriptor.relative_path,
                "media_type": descriptor.media_type,
                "size_bytes": descriptor.size_bytes,
                "producer_node": descriptor.producer_node,
                "artifact_created_at": descriptor.created_at,
                "object_key": blob.object_key,
                "etag": blob.etag,
                "object_version_id": blob.version_id,
                "published_at": current,
            }
            connection.execute(
                insert(artifact_versions)
                .values(**version_values)
                .on_conflict_do_nothing(
                    index_elements=[
                        artifact_versions.c.artifact_id,
                        artifact_versions.c.sha256,
                        artifact_versions.c.backend,
                    ]
                )
            )

            existing_version = connection.execute(
                sa.select(artifact_versions).where(
                    artifact_versions.c.artifact_id
                    == descriptor.artifact_id,
                    artifact_versions.c.sha256
                    == descriptor.sha256,
                    artifact_versions.c.backend
                    == blob.backend,
                )
            ).mappings().one()
            if existing_version["object_key"] != blob.object_key:
                raise ArtifactIntegrityError(
                    "相同 Artifact version 对应不同 object_key"
                )

            same_head = (
                head is not None
                and head["current_sha256"]
                == descriptor.sha256
                and head["current_backend"] == blob.backend
            )
            if head is None:
                connection.execute(
                    artifact_heads.insert().values(
                        artifact_id=descriptor.artifact_id,
                        job_id=job_id,
                        run_id=descriptor.run_id,
                        relative_path=descriptor.relative_path,
                        current_sha256=descriptor.sha256,
                        current_backend=blob.backend,
                        revision=1,
                        updated_at=current,
                    )
                )
            elif not same_head:
                connection.execute(
                    artifact_heads.update()
                    .where(
                        artifact_heads.c.artifact_id
                        == descriptor.artifact_id
                    )
                    .values(
                        current_sha256=descriptor.sha256,
                        current_backend=blob.backend,
                        revision=(
                            artifact_heads.c.revision + 1
                        ),
                        updated_at=current,
                    )
                )

            row = connection.execute(
                self._joined().where(
                    artifact_heads.c.artifact_id
                    == descriptor.artifact_id
                )
            ).mappings().one()
            return self._to_published(row)

    def find(
        self,
        *,
        job_id: str,
        artifact_id: str,
    ) -> PublishedArtifact | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                self._joined().where(
                    artifact_heads.c.job_id == job_id,
                    artifact_heads.c.artifact_id
                    == artifact_id,
                )
            ).mappings().one_or_none()
        return (
            None
            if row is None
            else self._to_published(row)
        )

    def list_for_job(
        self,
        job_id: str,
    ) -> list[PublishedArtifact]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                self._joined()
                .where(artifact_heads.c.job_id == job_id)
                .order_by(
                    artifact_versions.c.layer,
                    artifact_versions.c.relative_path,
                )
            ).mappings().all()
        return [self._to_published(row) for row in rows]
```

正式实现已经在事务开头使用 transaction-level advisory lock。这样相同
`artifact_id` 的首次发布串行，不同 Artifact 仍可并行；锁在事务结束时自动释放。

---

## 二十四、更新 Artifact Factory

> **本节类型：需要修改代码。**
>
> 修改：`app/storage/factory.py`

把 repository 构造改为：

```python
    if settings.job_store_backend == "sqlite":
        repository: ArtifactRepository = (
            SqliteArtifactRepository(
                settings.artifact_catalog_db_path
            )
        )
    elif settings.job_store_backend == "postgresql":
        from app.storage.postgres_artifact_repository import (
            PostgresArtifactRepository,
        )

        repository = PostgresArtifactRepository()
    else:
        raise ValueError(
            "不支持的 metadata backend"
        )

    repository.initialize()
```

其余 Local/S3 BlobStore、Publisher、Registry 和 Catalog 组合保持 Phase 24 不变。

---

## 二十五、实现共享 PostgreSQL Checkpointer

> **本节类型：需要修改代码。**
>
> 修改：`app/memory/checkpoint.py`

用下面完整代码替换当前文件：

```python
from __future__ import annotations

import atexit
import sqlite3
import threading
from typing import Any

from app.config import settings


_lock = threading.Lock()
_checkpointer: Any | None = None
_sqlite_connection: sqlite3.Connection | None = None
_postgres_pool: Any | None = None


def _build_sqlite_checkpointer():
    from langgraph.checkpoint.sqlite import (
        SqliteSaver,
    )

    global _sqlite_connection
    settings.checkpoint_db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    _sqlite_connection = sqlite3.connect(
        settings.checkpoint_db_path,
        check_same_thread=False,
        timeout=30,
    )
    _sqlite_connection.execute(
        "PRAGMA journal_mode=WAL"
    )
    _sqlite_connection.execute(
        "PRAGMA synchronous=NORMAL"
    )
    _sqlite_connection.execute(
        "PRAGMA busy_timeout=30000"
    )
    return SqliteSaver(_sqlite_connection)


def _build_postgres_checkpointer():
    from langgraph.checkpoint.postgres import (
        PostgresSaver,
    )
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    from app.persistence.database import (
        psycopg_conninfo,
    )

    global _postgres_pool
    _postgres_pool = ConnectionPool(
        conninfo=psycopg_conninfo(),
        min_size=(
            settings
            .checkpoint_postgres_pool_min_size
        ),
        max_size=(
            settings
            .checkpoint_postgres_pool_max_size
        ),
        timeout=(
            settings.database_pool_timeout_seconds
        ),
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=True,
        name="langgraph-checkpoint",
    )
    _postgres_pool.wait()
    return PostgresSaver(_postgres_pool)


def build_checkpointer():
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    with _lock:
        if _checkpointer is not None:
            return _checkpointer
        if settings.checkpoint_backend == "sqlite":
            _checkpointer = (
                _build_sqlite_checkpointer()
            )
        elif settings.checkpoint_backend == "postgresql":
            _checkpointer = (
                _build_postgres_checkpointer()
            )
        else:
            raise ValueError(
                "不支持的 CHECKPOINT_BACKEND"
            )
        return _checkpointer


def setup_checkpointer() -> None:
    """显式创建/升级 Saver 自有表；只由迁移 CLI 调用。"""

    saver = build_checkpointer()
    saver.setup()


def close_checkpointer() -> None:
    global _checkpointer
    global _sqlite_connection
    global _postgres_pool

    with _lock:
        _checkpointer = None
        if _sqlite_connection is not None:
            _sqlite_connection.close()
            _sqlite_connection = None
        if _postgres_pool is not None:
            _postgres_pool.close()
            _postgres_pool = None


atexit.register(close_checkpointer)
```

正式进程启动只调用 `build_checkpointer()`，不调用 `setup()`。DDL 必须由显式部署步骤
执行。LangGraph 官方要求首次使用 PostgreSQL checkpointer 时调用 `setup()`。

---

## 二十六、Graph Factory 不需要知道数据库类型

> **本节类型：代码检查说明，通常不修改代码。**

检查 `app/graph.py` 仍保持：

```python
selected_checkpointer = (
    checkpointer
    if checkpointer is not None
    else build_checkpointer()
)
return builder.compile(
    checkpointer=selected_checkpointer
)
```

如果已经是这个结构，不修改。Graph 只依赖 Saver interface，不应 import
`PostgresSaver`。

---

## 二十七、增加显式数据库管理 CLI

> **本节类型：需要修改代码。**
>
> 修改：`app/main.py`

增加 import：

```python
import subprocess

from app.memory.checkpoint import (
    setup_checkpointer,
)
from app.persistence.database import (
    ping_database,
)
```

增加命令：

```python
@app.command("migrate-database")
def migrate_database_command():
    """升级应用表，再升级 LangGraph Saver 自有表。"""

    if settings.job_store_backend != "postgresql":
        raise typer.BadParameter(
            "migrate-database 只用于 PostgreSQL backend"
        )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    if settings.checkpoint_backend == "postgresql":
        setup_checkpointer()
    print(
        {
            "status": "migrated",
            "job_backend": settings.job_store_backend,
            "checkpoint_backend": (
                settings.checkpoint_backend
            ),
        }
    )


@app.command("check-database")
def check_database_command():
    """检查连接和当前 Alembic revision，不输出 DSN。"""

    ping_database()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "current",
            "--check-heads",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise typer.BadParameter(
            "数据库 revision 未到 head"
        )
    print(
        {
            "status": "ready",
            "job_backend": settings.job_store_backend,
            "checkpoint_backend": (
                settings.checkpoint_backend
            ),
        }
    )
```

不要使用 `shell=True`，也不要把 `DATABASE_URL` 拼进命令行参数。

---

## 二十八、SQLite metadata 迁移边界

> **本节类型：需要新增迁移功能与安全约束。**

本阶段只允许迁移 terminal Job：

```text
succeeded
failed
cancelled
```

禁止自动迁移：

```text
queued
running
waiting_for_input
cancelling
reconciliation_required
```

原因：active Job 的正确恢复不仅需要 Job row，还需要 checkpoint history、pending
writes、interrupt identity、本地 workspace 和可能存活的 subprocess。公共 Saver API
返回的 `pending_writes` 不保留所有内部存储细节，直接复制内部表又会绑定具体包版本。

推荐增加 CLI：

```text
python -m app.main migrate-sqlite-terminal-metadata \
  --job-db jobs/runtime.sqlite \
  --artifact-db storage/artifacts.sqlite \
  --dry-run
```

实现规则：

1. 默认 `--dry-run`；
2. 发现一个非 terminal Job 就退出并列出 job_id/status；
3. 按原 `job_id/idempotency_key/thread_id/run_id` 插入；
4. 保留 Event `event_id` 时同步 PostgreSQL identity sequence；
5. Artifact metadata 迁移不复制 Blob；
6. 每张表迁移前后记录 count 和稳定 hash；
7. 再次执行必须幂等；
8. 不删除 SQLite 文件；
9. 不迁移 LangGraph checkpoint；
10. 迁移报告写入项目内 `manual_acceptance/phase25/`。

如果项目当前没有必须保留的历史 terminal Job，最安全的第一轮验收是空 PostgreSQL
数据库 + 新 thread_id，不要为了演示迁移而增加不必要风险。

---

## 二十九、建立双后端 JobStore Contract

> **本节类型：需要新增并重构测试。**
>
> 新增：`tests/job_store_contract.py`

不要从一个 `test_*.py` import 私有 helper。把后端无关场景写成普通函数：

```python
from app.job_runtime.schemas import JobRequest


def submit_fixture(store, *, suffix: str = "1"):
    return store.submit(
        job_id=f"job-{suffix}",
        idempotency_key=f"submit-{suffix}",
        thread_id=f"thread-{suffix}",
        run_id=f"run-{suffix}",
        run_dir=f"/data/tianshaoqi24/runs/run-{suffix}",
        request=JobRequest(
            paper_path="/data/tianshaoqi24/paper.pdf",
            repo_path="/data/tianshaoqi24/repo",
            execution_profile_id="local",
        ),
        max_attempts=3,
    )


def contract_submit_is_idempotent(store) -> None:
    first, created = submit_fixture(store)
    second, replay_created = submit_fixture(store)
    assert created is True
    assert replay_created is False
    assert first.job_id == second.job_id


def contract_claim_is_exclusive(store) -> None:
    submit_fixture(store)
    first = store.claim_next(
        worker_id="worker-a",
        lease_seconds=30,
    )
    second = store.claim_next(
        worker_id="worker-b",
        lease_seconds=30,
    )
    assert first is not None
    assert second is None


def contract_wait_resume_succeed(store) -> None:
    submit_fixture(store)
    claim = store.claim_next(
        worker_id="worker-a",
        lease_seconds=30,
    )
    assert claim is not None
    waiting = store.mark_waiting(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        interrupts=[],
        result={"run_id": claim.job.run_id},
        actor="worker-a",
    )
    assert waiting.status == "waiting_for_input"

    # 实际 contract 继续覆盖 queue_resume -> claim -> mark_succeeded。
```

Contract 最终必须覆盖 Phase 22/23 已经验证的全部语义：

```text
submit idempotency/conflict
claim exclusivity
heartbeat/cancel observation
waiting generation
resume idempotency/stale generation
cancel command idempotency
mark terminal fencing
retry backoff/max attempts
expired lease reconciliation
event ordering/events_after
```

原 SQLite tests 可以继续保留；新增 contract 是为了防止 PostgreSQL 实现只通过几个
happy path。

---

## 三十、PostgreSQL 测试数据库 Fixture

> **本节类型：需要修改测试配置。**
>
> 修改：`tests/conftest.py`

增加 marker 和 fixture：

```python
import os

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "postgres: 需要 TEST_DATABASE_URL 的 PostgreSQL integration test",
    )


@pytest.fixture
def postgres_engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("未设置 TEST_DATABASE_URL")

    import sqlalchemy as sa

    from app.persistence.tables import metadata

    engine = sa.create_engine(
        url,
        pool_pre_ping=True,
    )
    metadata.drop_all(engine)
    metadata.create_all(engine)
    try:
        yield engine
    finally:
        metadata.drop_all(engine)
        engine.dispose()
```

普通业务进程禁止 `create_all()`；这里只允许隔离 integration test fixture 使用。

---

## 三十一、增加 PostgreSQL JobStore 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_postgres_job_store.py`

```python
import pytest

from app.job_runtime.postgres_store import (
    PostgresJobStore,
)
from tests.job_store_contract import (
    contract_claim_is_exclusive,
    contract_submit_is_idempotent,
)


pytestmark = pytest.mark.postgres


def test_postgres_submit_contract(
    postgres_engine,
) -> None:
    contract_submit_is_idempotent(
        PostgresJobStore(postgres_engine)
    )


def test_postgres_claim_contract(
    postgres_engine,
) -> None:
    contract_claim_is_exclusive(
        PostgresJobStore(postgres_engine)
    )
```

把其余 contract 逐个加入本文件。只有 SQLite 与 PostgreSQL 都通过同一组 contract，
factory 切换才可信。

---

## 三十二、增加并发 Claim 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_postgres_distributed_claim.py`

完整核心测试：

```python
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.job_runtime.postgres_store import (
    PostgresJobStore,
)
from tests.job_store_contract import submit_fixture


pytestmark = pytest.mark.postgres


def test_workers_never_claim_same_job(
    postgres_engine,
) -> None:
    store = PostgresJobStore(postgres_engine)
    total = 40
    for index in range(total):
        submit_fixture(
            store,
            suffix=str(index),
        )

    def claim(worker_index: int):
        local_store = PostgresJobStore(
            postgres_engine
        )
        return local_store.claim_next(
            worker_id=f"worker-{worker_index}",
            lease_seconds=30,
        )

    with ThreadPoolExecutor(
        max_workers=12
    ) as executor:
        claims = list(
            executor.map(claim, range(total))
        )

    claimed = [
        item.job.job_id
        for item in claims
        if item is not None
    ]
    assert len(claimed) == total
    assert len(set(claimed)) == total
```

再增加以下测试：

- 80 次 claim 只有 40 个非空结果；
- 旧 token 在 lease requeue 后无法 heartbeat/mark；
- 一个 Worker 持有 row lock 时其他 Worker skip 而不是等待到 timeout；
- DB clock 与本机 monkeypatch 时间无关；
- 连接被 PostgreSQL 主动关闭后 `pool_pre_ping` 能恢复下一次 checkout。

---

## 三十三、增加 Shared Checkpoint 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_postgres_checkpoint.py`

这个测试不能只检查 `PostgresSaver` 可 import。必须创建两个独立 Saver/Graph 实例：

```python
import os
from typing import TypedDict
from uuid import uuid4

import pytest
from langgraph.checkpoint.postgres import (
    PostgresSaver,
)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


pytestmark = pytest.mark.postgres


class HandoffState(TypedDict, total=False):
    prepared: int
    decision: str
    finished: bool


def _build_handoff_graph(
    *,
    checkpointer,
    prepare_calls: list[str],
):
    def prepare(state: HandoffState) -> dict:
        prepare_calls.append("prepare")
        return {
            "prepared": state.get("prepared", 0) + 1
        }

    def review(state: HandoffState) -> dict:
        del state
        value = interrupt(
            {"kind": "test_review"}
        )
        return {"decision": str(value)}

    def finish(state: HandoffState) -> dict:
        assert state["decision"] == "approved"
        return {"finished": True}

    builder = StateGraph(HandoffState)
    builder.add_node("prepare", prepare)
    builder.add_node("review", review)
    builder.add_node("finish", finish)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "review")
    builder.add_edge("review", "finish")
    builder.add_edge("finish", END)
    return builder.compile(
        checkpointer=checkpointer
    )


def test_second_graph_reads_first_graph_checkpoint():
    url = os.environ["TEST_DATABASE_URL"].replace(
        "postgresql+psycopg://",
        "postgresql://",
    )
    thread_id = f"handoff-{uuid4().hex}"
    config = {
        "configurable": {"thread_id": thread_id}
    }
    prepare_calls: list[str] = []

    with PostgresSaver.from_conn_string(url) as saver_a:
        saver_a.setup()
        graph_a = _build_handoff_graph(
            checkpointer=saver_a,
            prepare_calls=prepare_calls,
        )
        first = graph_a.invoke({}, config)
        assert "__interrupt__" in first

    with PostgresSaver.from_conn_string(url) as saver_b:
        graph_b = _build_handoff_graph(
            checkpointer=saver_b,
            prepare_calls=prepare_calls,
        )
        final = graph_b.invoke(
            Command(resume="approved"),
            config,
        )

    assert final["finished"] is True
    assert final["prepared"] == 1
    assert prepare_calls == ["prepare"]
```

Saver A 运行到 review 后关闭；Saver B 用同一 `thread_id` 恢复，并断言 prepare 只执行
一次。这个测试不连接 Provider、不执行真实训练。

---

## 三十四、测试 Artifact Repository 双后端语义

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_postgres_artifact_repository.py`

把 Phase 24 的 repository 测试抽成 backend-neutral contract，并让 PostgreSQL 覆盖：

```text
首次 publish revision=1
同 sha/backend 重放 revision 不变
新 sha revision+1
backend 迁移 revision+1
同 artifact_id 不同 run/path 冲突
并发首次 publish 只产生一个 head
list_for_job 隔离
Catalog 不包含 absolute_path
```

并发测试必须使用多个 connection，而不是同一 transaction 中连续调用。

---

## 三十五、配置文件与 Secret 边界

> **本节类型：需要修改配置文件。**
>
> 修改：`.env.example`

增加：

```dotenv
# Phase 25 production control plane
JOB_STORE_BACKEND=sqlite
CHECKPOINT_BACKEND=sqlite

# 只在两个 backend 都切为 postgresql 后启用。
# DATABASE_URL=postgresql+psycopg://agent_app:REPLACE_ME@127.0.0.1:55432/paper_agent
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5
DATABASE_POOL_TIMEOUT_SECONDS=10
DATABASE_STATEMENT_TIMEOUT_MS=30000
DATABASE_LOCK_TIMEOUT_MS=5000

CHECKPOINT_POSTGRES_POOL_MIN_SIZE=1
CHECKPOINT_POSTGRES_POOL_MAX_SIZE=5
```

真实密码不能提交。生产中由 Secret Manager、systemd credential、Kubernetes Secret
或受控环境变量注入。

> 修改：`.gitignore`

确认包含：

```gitignore
.env
manual_acceptance/
postgres-phase25/
postgres-socket/
```

---

## 三十六、完整测试命令

> **本节类型：运行验证，不修改项目代码。**

先运行不需要 PostgreSQL 的回归：

```bash
python -m pytest \
  tests/test_job_store.py \
  tests/test_job_store_interaction_semantics.py \
  tests/test_job_heartbeat.py \
  tests/test_job_process_reconcile.py \
  tests/test_job_worker.py \
  tests/test_artifact_repository.py \
  tests/test_artifact_publisher.py \
  tests/test_artifact_storage_api.py \
  -q
```

启动测试 PostgreSQL 并设置 `TEST_DATABASE_URL` 后：

```bash
python -m pytest \
  tests/test_postgres_job_store.py \
  tests/test_postgres_distributed_claim.py \
  tests/test_postgres_artifact_repository.py \
  tests/test_postgres_checkpoint.py \
  tests/test_postgres_cutover.py \
  -m postgres \
  -q
```

检查 migration 漂移：

```bash
python -m alembic upgrade head
python -m alembic check
python -m alembic current --check-heads
```

静态检查：

```bash
python -m compileall \
  app/persistence \
  app/job_runtime \
  app/storage \
  app/memory

python -m ruff check \
  --select E4,E7,E9,F \
  app/persistence \
  app/job_runtime \
  app/storage \
  app/memory \
  tests/test_postgres_job_store.py \
  tests/test_postgres_distributed_claim.py \
  tests/test_postgres_artifact_repository.py \
  tests/test_postgres_checkpoint.py
```

最后运行全量离线回归：

```bash
python -m pytest -m "not provider and not postgres" -q
```

---

## 三十七、在 `/data/tianshaoqi24/` 启动本地 PostgreSQL

> **本节类型：手工验收，不修改项目代码。**

本教程不自动下载安装系统软件。先确认：

```bash
command -v initdb
command -v pg_ctl
command -v psql
```

所有项目验收数据放在 `/data/tianshaoqi24/`：

```bash
export PHASE25_PGDATA=/data/tianshaoqi24/postgres-phase25/data
export PHASE25_PGSOCKET=/data/tianshaoqi24/postgres-phase25/socket
export PHASE25_PGPORT=55432

mkdir -p \
  /data/tianshaoqi24/postgres-phase25/data \
  /data/tianshaoqi24/postgres-phase25/socket
```

首次初始化：

```bash
initdb \
  --pgdata "$PHASE25_PGDATA" \
  --auth-local=scram-sha-256 \
  --auth-host=scram-sha-256 \
  --username=postgres \
  --pwprompt
```

启动时只监听本机：

```bash
pg_ctl \
  --pgdata "$PHASE25_PGDATA" \
  --log /data/tianshaoqi24/postgres-phase25/postgresql.log \
  --options "-h 127.0.0.1 -p $PHASE25_PGPORT -k $PHASE25_PGSOCKET" \
  start
```

创建应用角色与数据库时使用你自己生成的高熵密码：

```bash
psql \
  --host 127.0.0.1 \
  --port "$PHASE25_PGPORT" \
  --username postgres \
  --dbname postgres
```

在 psql 中执行：

```sql
CREATE ROLE agent_app
LOGIN
PASSWORD '替换为高熵随机密码'
NOSUPERUSER
NOCREATEDB
NOCREATEROLE;

CREATE DATABASE paper_agent
OWNER agent_app;
```

不要把密码写入教程、Git、shell history 或验收报告。

---

## 三十八、初始化 Schema 与 Checkpoint

> **本节类型：手工验收，不修改项目代码。**

在项目终端设置：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent

export DATABASE_URL='postgresql+psycopg://agent_app:URL编码后的密码@127.0.0.1:55432/paper_agent'
export JOB_STORE_BACKEND=postgresql
export CHECKPOINT_BACKEND=postgresql
```

执行：

```bash
python -m app.main migrate-database
python -m app.main check-database
python -m alembic current --check-heads
```

检查表：

```bash
export PG_DSN='postgresql://agent_app:URL编码后的密码@127.0.0.1:55432/paper_agent'
psql "$PG_DSN" -c '\dt'
```

应同时看到应用表和 LangGraph 自有表，但 `alembic_version` 只管理应用 migration。

---

## 三十九、双 Worker Claim 手工验收

> **本节类型：手工验收，不修改项目代码。**

终端 A、B 使用完全相同的 `DATABASE_URL`、backend、Artifact backend 和执行 profile。

终端 A：

```bash
python -m app.main run-worker \
  --worker-id phase25-worker-a
```

终端 B：

```bash
python -m app.main run-worker \
  --worker-id phase25-worker-b
```

通过 integration fixture 一次插入 20 个无 Provider 的测试 Job，或运行：

```bash
python -m pytest \
  tests/test_postgres_distributed_claim.py \
  -m postgres \
  -q
```

查询：

```sql
SELECT
    job_id,
    status,
    worker_id,
    claim_token,
    attempt_count
FROM jobs
ORDER BY created_at;
```

验收条件：

- 同一 `job_id` 没有两个同时有效的 claim；
- Worker 不因另一行被锁而全局阻塞；
- `job_claimed` Event 与 ownership 同事务出现；
- 旧 token 无法写终态；
- Event ID 全局单调，SSE cursor 仍可继续。

---

## 四十、PSTNet 跨进程 Checkpoint Handoff

> **本节类型：手工验收，不修改项目代码。**

继续使用：

```text
论文：
/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/
PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf

仓库：
/data/tianshaoqi24/PST-Convolution-main/

Profile：
pstnet-local-supervised
```

验收步骤：

1. 只启动 Worker A；
2. 通过 Phase 23 API 提交 `thread_id=phase25-pstnet-handoff-001`；
3. 等待 Job 到 `command_selection` interrupt；
4. 确认 PostgreSQL Job 为 `waiting_for_input`；
5. 正常停止 Worker A；
6. 通过 API 提交 Command Selection decision；
7. 只启动 Worker B；
8. Worker B 必须从 PostgreSQL checkpoint 恢复；
9. 论文解析和 repo scan 不应再次执行；
10. Worker B 到达下一 interrupt 或受控终态。

检查 Job/Event：

```bash
python -m app.main show-job "$JOB_ID"
python -m app.main show-job-events "$JOB_ID" --limit 100
```

检查 checkpoint：

```bash
python -m app.main show-state \
  --thread-id phase25-pstnet-handoff-001
```

验收证据至少保留：

```text
Worker A 的 job_claimed + waiting event
Worker B 的新 job_claimed event
相同 thread_id/run_id
checkpoint 恢复后的 next node
Artifact Catalog 中前后两批 Artifact
没有重复执行已完成节点的 trace
```

这证明跨进程 handoff。由于两个 Worker 使用同一台机器上的 `runs/` 和仓库，它还不
证明跨主机 workspace handoff。

---

## 四十一、数据库重启与 Lease 恢复测试

> **本节类型：手工验收，不修改项目代码。**

使用无真实训练副作用的测试 Job：

1. Worker claim Job；
2. 停止 PostgreSQL；
3. heartbeat 应记录后端故障，Worker 不得继续写终态；
4. 停 Worker；
5. 重启 PostgreSQL；
6. `check-database` 必须恢复；
7. 等 lease 到期；
8. Reconciler 按现有 process journal 判断 safe/ambiguous；
9. 只有 safe Job 才 requeue；
10. 新 Worker 使用新 claim token 接管。

停止与启动：

```bash
pg_ctl --pgdata "$PHASE25_PGDATA" stop --mode fast
pg_ctl \
  --pgdata "$PHASE25_PGDATA" \
  --log /data/tianshaoqi24/postgres-phase25/postgresql.log \
  --options "-h 127.0.0.1 -p $PHASE25_PGPORT -k $PHASE25_PGSOCKET" \
  start
```

不能把数据库断开统一包装成“Graph 失败”。它是 control-plane backend failure，
应保留原 checkpoint 和外部副作用证据。

---

## 四十二、常见问题排查

> **本节类型：故障排查，不修改项目代码。**

### 42.1 `ModuleNotFoundError: sqlalchemy/psycopg`

```bash
python -m pip install -e ".[postgres]"
```

### 42.2 `relation jobs does not exist`

只连接数据库不等于迁移完成：

```bash
python -m app.main migrate-database
python -m alembic current --check-heads
```

### 42.3 `relation checkpoints does not exist`

Alembic 不管理 Saver 表。确认：

```text
CHECKPOINT_BACKEND=postgresql
python -m app.main migrate-database
```

命令必须调用 `setup_checkpointer()`。

### 42.4 Worker 全部卡在 claim

检查是否：

```text
FOR UPDATE 后在事务里运行了 Graph/网络/文件操作
遗漏 skip_locked=True
lock_timeout 设置过大
连接池小于 Worker 并发需求
```

### 42.5 Job 很快 lease expired

检查数据库服务器时间和 heartbeat：

```sql
SELECT clock_timestamp(), now();
```

不要混用本机 `time.time()` 和数据库时间计算同一个 lease。

### 42.6 API 能看到 Job，但 Worker 看不到 checkpoint

通常是：

```text
API 与 Worker DATABASE_URL 不同
CHECKPOINT_BACKEND 一边是 sqlite、一边是 postgresql
thread_id 不一致
某个终端仍读取旧 .env
```

### 42.7 PostgreSQL 连接数过多

每个进程的最大连接近似：

```text
SQLAlchemy pool_size + max_overflow
+ Checkpoint pool max_size
```

再乘 API/Worker 进程数。先降低每进程 pool，不要立即引入 PgBouncer。

### 42.8 Alembic 想删除 LangGraph 表

说明 `target_metadata` 或 schema include 配置错误。应用 metadata 本来不包含 LangGraph
表；autogenerate 可能把数据库中的外部表识别为待删除。为 `env.py` 增加
`include_name/include_object`，只管理本教程的应用表，绝不能接受 DROP candidate。

### 42.9 第二个 Worker 恢复后找不到本地文件

这不是 PostgreSQL 问题，而是 workspace 边界。当前只支持同机共享路径；跨主机需要
下一阶段的 workspace materialization/affinity。

---

## 四十三、安全与可靠性复核

> **本节类型：安全清单，不修改项目代码。**

- PostgreSQL 只监听受控网络；
- 应用角色不是 superuser；
- 密码不进 Git、Event、Artifact 或日志；
- API 不返回 DATABASE_URL；
- Alembic 与 Saver 表 ownership 分离；
- 启动路径不自动执行 DDL；
- claim 使用短事务和 `SKIP LOCKED`；
- lease 使用数据库时钟；
- 所有终态写入校验 claim token；
- stale Worker 不能覆盖新 owner；
- `pool_pre_ping` 只解决 checkout 前失效，不伪装事务中断自动成功；
- 数据库异常不进行无界重试；
- active SQLite Job 不自动迁移；
- migration 默认 dry-run；
- SQLite 备份不自动删除；
- Artifact Blob 与 metadata 仍执行 Blob-first；
- PostgreSQL 不保存 AWS secret；
- checkpoint 可选启用 LangGraph serializer encryption；
- integration test 使用独立数据库；
- test fixture 的 `drop_all` 绝不能指向生产 URL；
- 多进程验收不冒充多主机验收；
- 本阶段不引入消息队列掩盖数据库语义问题。

---

## 四十四、本阶段 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 44.1 Control Plane 与 Data Plane

```text
Control plane：
    Job、lease、decision、event、checkpoint metadata

Data plane：
    论文、代码仓库、训练数据、日志、模型权重
```

PostgreSQL 适合前者，不应把所有大文件塞进 JSONB。

### 44.2 Competing Consumers

多个 Worker 竞争队列表中的 Job。`SKIP LOCKED` 提供高并发 claim，但最终安全仍来自：

```text
row lock + claim token + lease + fencing
```

### 44.3 Database Time

分布式 lease 不能依赖每台 Worker 的 wall clock。数据库时钟成为统一裁判。

### 44.4 Schema Ownership

Agent 系统通常同时使用应用表和框架表。明确 migration owner 能避免框架升级与应用
Alembic 互相破坏。

### 44.5 Checkpoint 与 Queue 一致性

Job queue 表示“谁应该运行”；checkpoint 表示“从哪里继续”。只共享其中一个，恢复
都不完整。

### 44.6 Exactly-once 是错觉

数据库可以保证单次 claim 转移，但外部训练、Git、文件和 S3 不能和 Job row 形成一个
普通 ACID 事务。仍需要 idempotency、journal、fencing 和人工 reconciliation。

### 44.7 Backpressure 与连接预算

连接池不是越大越好。每个 API/Worker 都有两个 pool，数据库连接预算本身就是运行时
资源约束。

---

## 四十五、完成标准

> **本节类型：最终验收清单，不修改项目代码。**

只有以下全部满足，才算 Phase 25 完成：

- PostgreSQL 是唯一生产数据库目标；
- SQLite 后端仍通过原回归；
- JobStore errors 不再属于 SQLite 模块；
- JobStore Protocol 包含 ping/close；
- 应用表由 Alembic 管理；
- LangGraph 表只由 `PostgresSaver.setup()` 管理；
- `alembic check` 无漂移；
- PostgresJobStore 实现全部 Protocol 方法；
- 双后端 contract 全绿；
- claim 使用 `FOR UPDATE SKIP LOCKED`；
- claim transaction 不包含 Graph/网络/文件操作；
- lease 使用 `clock_timestamp()`；
- heartbeat 与所有 mark 校验 claim token；
- 并发 claim 不重复 Job；
- stale token fencing 测试通过；
- Event 与状态转换同事务；
- PostgresArtifactRepository revision contract 通过；
- 并发 Artifact publish 不产生双 head；
- API/Worker 共用 PostgreSQL Artifact Catalog；
- 两个独立 Saver 能读取同一 thread；
- Saver A interrupt、Saver B resume 不重跑前置节点；
- active SQLite Job 不被自动迁移；
- migration dry-run 和 count/hash 报告存在；
- 数据库密码不出现在输出；
- PostgreSQL 重启恢复测试通过；
- Phase 22/23/24 回归通过；
- PSTNet Worker A -> Worker B handoff 成功；
- 文档明确只验收同机多进程；
- 本地 PostgreSQL 数据全部位于 `/data/tianshaoqi24/`。

---

## 四十六、下一阶段建议

> **本节类型：路线说明，不修改项目代码。**

Phase 25 完成后，下一阶段最值得做的是：

```text
Phase 26：
Workspace Materialization、Worker Capability/Affinity 与真正跨主机接管
```

建议内容：

```text
Worker registration 与 heartbeat
CPU/GPU/CUDA/磁盘 capability
Job execution requirements
host affinity 与 repository ownership
workspace manifest/snapshot
从 ArtifactStore rehydrate 新 Worker workspace
代码仓库 commit/dirty-state 身份
数据集只保存引用，不复制巨量数据
跨主机 resume 前 preflight
原主机活跃 subprocess fencing
workspace garbage collection
两主机故障注入验收
```

Redis/MQ 仍不是默认下一步。只有 PostgreSQL claim 的轮询延迟或路由吞吐成为实测瓶颈，
再增加通知层；数据库仍应保留 Job 状态事实源。

---

## 四十七、阶段结论

> **本节类型：总结，不修改项目代码。**

Phase 25 建立的是 Agent 的共享控制面：

```text
Job queue + Decision + Event
          │
          ├── PostgreSQL transaction / lease / fencing
          │
          └── LangGraph shared checkpoint
```

它让多个独立进程能够竞争任务，并由另一个进程从同一 checkpoint 继续；但可靠 Agent
不能把“共享数据库”误写成“整个执行环境已经可迁移”。本地 workspace 和外部副作用
仍然决定真正跨主机接管是否安全，这正是下一阶段要解决的边界。
