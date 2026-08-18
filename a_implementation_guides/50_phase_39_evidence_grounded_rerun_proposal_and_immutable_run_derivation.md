# Phase 39：Evidence-Grounded Rerun Proposal 与 Immutable Run Derivation

> 本章是在 Phase 38 已完成之后的下一阶段实现教程。
>
> 本章会明确标出需要新增或修改的文件，并提供带上下文的代码、测试、API、CLI、崩溃恢复与手工验收步骤。教程本身不会直接修改 `app/`、`tests/` 或 `web/` 源代码。
>
> 本阶段继续面向单机单用户；它解决“基于可信父运行修改少量参数并创建全新 Job”，不判断论文复现结果是否成功。

---

## 一、为什么 Phase 39 优先做可信重跑

> **本节类型：优先级分析，不修改项目代码。**

Phase 38 已经可以确定性回答两个 Run 的差异，但用户看到差异后仍需要手工完成：

```text
重新找到论文和仓库路径
重新填写 execution profile 和数据集
从报告中复制旧命令
手工修改一个参数
重新提交 Job
```

例如：

```text
Run A：python train.py --batch-size 16 --epochs 50，OOM
Run B：python train.py --batch-size 8  --epochs 50，正常退出

用户：以 Run B 为模板，将 epochs 改成 100，再运行一次。
```

如果只把旧命令复制到一个新的 `submit-job` 请求，会产生三个严重问题：

```text
1. 旧命令里的 repo_path、dataset_path 可能指向已经回收的 Workspace；
2. 旧审批可能错误地覆盖修改后的新命令；
3. JobService 会重新读取本机 paper/repo 路径，输入内容可能已经漂移。
```

正确边界是：

```text
Terminal Parent Job
  -> 校验 Job / WorkspaceManifest / run_manifest / Artifact 身份
  -> 从真实 selected_run_command 构造安全参数模板
  -> 只允许结构化修改已有长选项
  -> 生成不可变、可过期、带 hash 的 Rerun Proposal
  -> 用户显式提交 Proposal
  -> 从父 Workspace Blob 派生全新的 generation-0 Manifest
  -> 创建新的 Job / run_id / thread_id / checkpoint
  -> 再次经过 Command Selection / Risk / Human Review / Preflight / Smoke Test
```

本阶段不是“自动重试失败任务”，而是“以可验证事实为来源，安全地派生一次新实验”。

---

## 二、本阶段完成后的能力

> **本节类型：目标说明，不修改项目代码。**

完成后应满足：

1. 只能从终态父 Job 创建 Rerun Proposal；
2. 必须通过 Artifact Catalog 打开并校验父 `run_manifest.json`；
3. Proposal 使用真实 `selected_run_command.command`，不使用 Comparison 中的脱敏展示命令；
4. 调用方必须提交预期的父 `run_manifest` SHA-256，防止旧页面创建提案；
5. 可选绑定 Phase 38 `comparison_id + comparison_hash`；
6. 第一版只允许修改或删除已有 `--long-option`；
7. 不允许替换 executable、位置参数或整条命令；
8. 不允许 shell pipeline、重定向、命令替换、环境变量前缀或 secret-like 参数；
9. 父仓库和父 run_dir 内绝对路径转换为 repo/run-relative 模板；
10. 已声明数据集路径转换为 dataset label 模板；
11. 无法解释的绝对路径直接拒绝；
12. Proposal 内容不可变，状态与内容分开保存；
13. Proposal 有版本号、过期时间、状态和稳定 hash；
14. 同一创建幂等键加同一请求返回同一 Proposal；
15. 同一提交操作崩溃重试不会创建两个子 Job；
16. 子 Job 的 paper、repository bundle 和 input log 直接复用父 Blob identity；
17. 子 Job 不复制父 run Artifact、process log、checkpoint、审批或执行结果；
18. 即使 BlobStore 是本机类型，也从不可变 Blob 物化新 Workspace；
19. 子 Job 继承父数据集引用，但仍由新 Worker 能力重新解析挂载；
20. 子 Job 使用当前 Execution Profile 配置重新计算 policy hash；
21. 派生命令在新 Workspace 中重新解析 cwd 和数据集路径；
22. 派生命令进入新的 command selection interrupt；
23. 新 action hash、新预检、新风险判断和新人工审批全部重新生成；
24. API 可创建、查询、取消和提交 Proposal；
25. CLI 可完成同样流程；
26. Retention Inventory 能统计 Rerun DB，但 Phase 39 不自动删除 Proposal；
27. 测试覆盖 stale、篡改、过期、并发、幂等、非法命令与审批不继承。

---

## 三、本阶段明确不做

> **本节类型：范围说明，不修改项目代码。**

```text
不让 Chat Agent 直接执行重跑
不让 LLM 自由重写整条命令
不自动选择“更好的”父 Run
不自动根据 OOM 或 traceback 修改参数
不允许新增未知命令选项
不修改 executable 或位置参数
不继承父 Job 的 human approval
不复制父 LangGraph checkpoint
不复制父 Run Artifact 和进程记录
不跨论文合并输入
不切换 paper、repository 或 dataset identity
不把 succeeded 解释为论文复现成功
不在本阶段实现多用户权限
不增加 Redis 或消息队列
不实现周期性参数搜索或超参优化
不实现 Proposal 自动 GC
```

后续若希望用户用自然语言说“把 epoch 改成 100”，可以在现有结构化接口上增加一个只生成
`RerunArgumentEdit` 草稿的 Chat Tool；但最终仍必须走本阶段的确定性校验和显式提交。

---

## 四、最重要的六个安全边界

> **本节类型：架构说明，不修改项目代码。**

### 4.1 Comparison 命令不能用于执行

Phase 38 的 `CommandSnapshot.display` 会把路径和 secret 脱敏：

```text
python train.py --data <absolute-path> --token <redacted>
```

它适合展示和对比，不是可执行事实。Phase 39 必须重新打开父 Run 的已验证
`reports/run_manifest.json`，从其中读取原始 `selected_run_command`。

### 4.2 Proposal 不是 Approval

```text
Rerun Proposal：允许创建哪个新 Job
Command Selection：新 Job 选择哪个候选命令
Action Approval：允许执行哪个 action hash
```

三者用途不同。提交 Proposal 不能设置：

```text
user_approval = approved
approval_record = parent.approval_record
pending_action_hash = parent.pending_action_hash
```

### 4.3 派生输入复用内容，不复用本机路径

错误做法：

```text
child.paper_path = parent.request.paper_path
child.repo_path = parent.request.repo_path
```

正确做法：

```text
parent WorkspaceBlobEntry
  -> 校验 manifest hash
  -> 仅复制 paper/input_log/repository_bundle entry identity
  -> child generation-0 WorkspaceManifest
  -> 新 assignment epoch 中重新 materialize
```

### 4.4 本地 Blob 与不可变物化是两个维度

当前项目把 `portable=False` 同时理解为：

```text
需要 source host affinity
必须复用 source_paths
```

但派生 Job 在本地 BlobStore 下需要的是：

```text
仍需 source host affinity
但必须从 Blob entries 物化，不能复用 source_paths
```

因此本阶段增加 `materialization_mode`，将“能否跨主机”和“从哪里物化”分开。

### 4.5 Proposal 状态与 Proposal 内容分离

不可变内容：

```text
parent identities
command template
argument edits
derived command hash
comparison binding
created_at / expires_at
proposal_hash
```

可变状态：

```text
pending -> submitting -> submitted
pending -> cancelled
pending -> expired
version
child_job_id
last_error
```

不要在状态更新时重写 Proposal 内容，否则用户确认的 hash 会失效。

### 4.6 跨数据库不强求分布式事务

Rerun Repository 使用项目内 SQLite，Job Store 可能是 SQLite 或 PostgreSQL。第一版不引入
分布式事务，而使用确定性 Job 幂等键：

```text
rerun-submit:<proposal_id>
```

如果进程在 Job 创建后、Proposal 标记 submitted 前崩溃，重试会拿到原 Job，再完成状态更新。

---

## 五、总体架构

> **本节类型：架构说明，不修改项目代码。**

```text
POST /v1/rerun-proposals
  |
  v
RerunService.create_proposal
  +--> VerifiedRunEvidenceReader.read(parent_job_id)
  +--> optional ComparisonService.get(comparison_id)
  +--> SafeCommandDeriver.build_template(raw selected command)
  +--> apply_option_edits(expected old values)
  +--> RerunRepository.create(idempotently)

POST /v1/rerun-proposals/<id>/submit
  |
  v
RerunRepository.begin_submission(expected hash/version)
  +--> 再次读取并校验父 Run Evidence
  +--> JobService.submit(
          JobRequest(derived_run=...)
          idempotency_key="rerun-submit:<proposal_id>"
       )
  +--> WorkspaceSnapshotter.derive_initial(parent manifest)
  +--> RerunRepository.complete_submission(child_job_id)

Worker claim child Job
  +--> WorkspaceMaterializer 从 Blob entries 创建新 epoch workspace
  +--> GraphJobRunner 解析 command template
  +--> experiment_plan
  +--> rerun_seed_node 覆盖 run_commands
  +--> command_selection interrupt
  +--> action_builder -> risk -> human review -> preflight -> smoke_test -> executor
```

---

## 六、文件清单与推荐实现顺序

> **本节类型：实施清单，不修改项目代码。**

### 6.1 需要新增

```text
app/run_evidence/__init__.py
app/run_evidence/errors.py
app/run_evidence/schemas.py
app/run_evidence/reader.py

app/rerun/__init__.py
app/rerun/errors.py
app/rerun/schemas.py
app/rerun/identity.py
app/rerun/command_template.py
app/rerun/repository.py
app/rerun/service.py
app/rerun/factory.py

app/nodes/rerun_seed_node.py
app/api/rerun_routes.py

tests/test_verified_run_evidence_reader.py
tests/test_rerun_command_template.py
tests/test_rerun_repository.py
tests/test_immutable_workspace_derivation.py
tests/test_rerun_seed_node.py
tests/test_rerun_service.py
tests/test_rerun_api.py
tests/test_rerun_end_to_end.py
```

### 6.2 需要修改

```text
app/comparison/service.py
app/comparison/factory.py
app/job_runtime/schemas.py
app/job_runtime/service.py
app/job_runtime/graph_runner.py
app/job_runtime/postgres_store.py
app/workspace/schemas.py
app/workspace/snapshot.py
app/workspace/materializer.py
app/state.py
app/graph.py
app/interaction/schemas.py
app/interaction/service.py
app/interaction/policy.py
app/api/app.py
app/api/errors.py
app/main.py
app/config.py
app/retention/factory.py
.env.example
README.md
```

### 6.3 推荐顺序

```text
1. 抽取 VerifiedRunEvidenceReader
2. 实现 Rerun schema / identity / command template
3. 实现 Rerun SQLite repository
4. 拆分 Workspace portable 与 materialization mode
5. 扩展 JobRequest 和 JobService derived branch
6. 接入 GraphJobRunner / rerun_seed_node / graph
7. 实现 RerunService
8. 接 API / CLI / readiness / retention
9. 跑单元、集成和手工验收
```

不要先写 API，再让 route 直接读取文件和创建 Job。安全边界必须在 Service 内复用。

---

## 七、增加配置

> **本节类型：需要修改配置代码。**
>
> 需要修改：`app/config.py`、`.env.example`。

在 `Settings` 中与 Comparison 配置相邻的位置增加：

```python
# app/config.py

rerun_db_path: Path = Path(
    os.getenv("RERUN_DB_PATH", "rerun/rerun.sqlite")
)
rerun_proposal_ttl_seconds: int = int(
    os.getenv("RERUN_PROPOSAL_TTL_SECONDS", "86400")
)
rerun_max_command_chars: int = int(
    os.getenv("RERUN_MAX_COMMAND_CHARS", "8192")
)
rerun_max_argv_items: int = int(
    os.getenv("RERUN_MAX_ARGV_ITEMS", "256")
)
rerun_max_edits: int = int(
    os.getenv("RERUN_MAX_EDITS", "16")
)
```

在配置规范化区域增加：

```python
settings.rerun_db_path = settings.rerun_db_path.expanduser().resolve()

rerun_allowed_root = settings.job_export_allowed_root.expanduser().resolve()
if (
    settings.rerun_db_path == rerun_allowed_root
    or rerun_allowed_root not in settings.rerun_db_path.parents
):
    raise ValueError("RERUN_DB_PATH 必须位于受控项目数据根目录内")

settings.rerun_db_path.parent.mkdir(parents=True, exist_ok=True)

for name, value in {
    "RERUN_PROPOSAL_TTL_SECONDS": settings.rerun_proposal_ttl_seconds,
    "RERUN_MAX_COMMAND_CHARS": settings.rerun_max_command_chars,
    "RERUN_MAX_ARGV_ITEMS": settings.rerun_max_argv_items,
    "RERUN_MAX_EDITS": settings.rerun_max_edits,
}.items():
    if value <= 0:
        raise ValueError(f"{name} 必须大于 0")
```

`.env.example` 增加：

```dotenv
# Phase 39：可信重跑提案。目录应位于项目受控数据根下。
RERUN_DB_PATH=rerun/rerun.sqlite
RERUN_PROPOSAL_TTL_SECONDS=86400
RERUN_MAX_COMMAND_CHARS=8192
RERUN_MAX_ARGV_ITEMS=256
RERUN_MAX_EDITS=16
```

不要把数据库默认放到系统 `/tmp`。Proposal 是持久控制面记录，不是临时文件。

---

## 八、定义错误类型

> **本节类型：需要新增代码。**
>
> 需要新增：`app/rerun/errors.py`。

```python
# app/rerun/errors.py

class RerunError(RuntimeError):
    """Phase 39 重跑域错误基类。"""


class RerunNotFoundError(RerunError):
    """Proposal 不存在。"""


class RerunConflictError(RerunError):
    """状态、版本、幂等键或 stale identity 冲突。"""


class RerunIntegrityError(RerunError):
    """已持久化内容、父证据或 hash 校验失败。"""


class RerunCommandRejectedError(RerunError):
    """父命令或参数编辑超出安全子集。"""


class RerunExpiredError(RerunConflictError):
    """Proposal 已经过期，必须基于当前证据重新创建。"""
```

同时新增空导出文件：

```python
# app/rerun/__init__.py
"""Evidence-grounded rerun proposal domain."""
```

---

## 九、抽取共享 Verified Run Evidence Reader

> **本节类型：需要新增并修改代码。**
>
> 需要新增：`app/run_evidence/errors.py`、`app/run_evidence/schemas.py`、
> `app/run_evidence/reader.py`、`app/run_evidence/__init__.py`。
>
> 需要修改：`app/comparison/service.py`、`app/comparison/factory.py`。

Phase 38 已在 `ComparisonService._read_verified_manifest()` 中实现可信读取。如果 Phase 39 再复制
一份，后续两个实现很容易在大小限制、SHA 校验或 identity 校验上漂移。先将它抽成公共只读边界。

### 9.1 中性 Evidence 错误

新增 `app/run_evidence/errors.py`：

```python
# app/run_evidence/errors.py
class RunEvidenceError(RuntimeError):
    """已完成 Run 的可信证据读取错误基类。"""


class RunEvidenceNotFoundError(RunEvidenceError):
    """所需运行 Artifact 不存在或数量不唯一。"""


class RunEvidenceConflictError(RunEvidenceError):
    """Job 状态或 Manifest 版本不满足读取前提。"""


class RunEvidenceIntegrityError(RunEvidenceError):
    """Job、Workspace、Catalog、Descriptor 或 Blob 身份不一致。"""


class RunEvidenceLimitExceededError(RunEvidenceError):
    """Manifest 或 Artifact 数量超过有界读取上限。"""
```

### 9.2 内部读取结果

新增 `app/run_evidence/schemas.py`：

```python
# app/run_evidence/schemas.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.workspace.schemas import WorkspaceManifest


@dataclass(frozen=True)
class VerifiedRunEvidence:
    """仅在受信任服务内部传递，不直接作为 API response。"""

    job: JobRecord
    workspace: WorkspaceManifest
    artifacts: tuple[ArtifactView, ...]
    run_manifest_artifact: ArtifactView
    run_manifest: dict[str, Any]
```

新增 `app/run_evidence/__init__.py`：

```python
# app/run_evidence/__init__.py
from app.run_evidence.reader import VerifiedRunEvidenceReader
from app.run_evidence.schemas import VerifiedRunEvidence

__all__ = ["VerifiedRunEvidence", "VerifiedRunEvidenceReader"]
```

### 9.3 完整 Reader

新增 `app/run_evidence/reader.py`：

```python
# app/run_evidence/reader.py
from __future__ import annotations

import hashlib
import json
from typing import Protocol

from app.run_evidence.errors import (
    RunEvidenceConflictError,
    RunEvidenceIntegrityError,
    RunEvidenceLimitExceededError,
    RunEvidenceNotFoundError,
)
from app.interaction.artifacts import ArtifactCatalog
from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import (
    TERMINAL_JOB_STATUSES,
    JobRecord,
)
from app.run_evidence.schemas import VerifiedRunEvidence
from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.repository import validate_manifest_hash
from app.workspace.schemas import WorkspaceManifest

RUN_MANIFEST_PATH = "reports/run_manifest.json"


class RunEvidenceJobReader(Protocol):
    def get(self, job_id: str) -> JobRecord:
        ...

    def get_workspace_manifest(
        self,
        manifest_id: str,
    ) -> WorkspaceManifest:
        ...


class VerifiedRunEvidenceReader:
    """统一校验 Job、Workspace、Catalog、Descriptor 和 Blob。"""

    def __init__(
        self,
        *,
        jobs: RunEvidenceJobReader,
        artifact_catalog: ArtifactCatalog,
        max_manifest_bytes: int,
        max_artifacts: int,
    ) -> None:
        self.jobs = jobs
        self.artifact_catalog = artifact_catalog
        self.max_manifest_bytes = max_manifest_bytes
        self.max_artifacts = max_artifacts

    @staticmethod
    def _require_terminal(job: JobRecord) -> None:
        if job.status not in TERMINAL_JOB_STATUSES:
            raise RunEvidenceConflictError(
                f"Job {job.job_id} 尚未终止，当前状态为 {job.status}"
            )

    @staticmethod
    def _validate_workspace(
        job: JobRecord,
        manifest: WorkspaceManifest,
    ) -> None:
        try:
            validate_manifest_hash(manifest)
        except WorkspaceIntegrityError as exc:
            raise RunEvidenceIntegrityError(
                "Workspace Manifest hash 校验失败"
            ) from exc
        if manifest.manifest_id != job.workspace_manifest_id:
            raise RunEvidenceIntegrityError(
                "Job 的 workspace_manifest_id 已漂移"
            )
        if manifest.job_id != job.job_id or manifest.run_id != job.run_id:
            raise RunEvidenceIntegrityError(
                "WorkspaceManifest 与 Job 身份不一致"
            )
        if manifest.generation != job.workspace_manifest_generation:
            raise RunEvidenceIntegrityError(
                "WorkspaceManifest generation 不一致"
            )

    def _list_artifacts(self, job: JobRecord) -> list[ArtifactView]:
        views = self.artifact_catalog.list_views(job)
        if len(views) > self.max_artifacts:
            raise RunEvidenceLimitExceededError(
                "Artifact 数量超过可信读取上限"
            )
        ids = [item.artifact_id for item in views]
        paths = [item.relative_path for item in views]
        if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
            raise RunEvidenceIntegrityError(
                "Artifact identity 或 relative_path 重复"
            )
        if any(item.run_id != job.run_id for item in views):
            raise RunEvidenceIntegrityError(
                "Artifact Catalog 混入其他 run_id"
            )
        return sorted(views, key=lambda item: item.relative_path)

    def _read_manifest_blob(
        self,
        *,
        job: JobRecord,
        views: list[ArtifactView],
    ) -> tuple[ArtifactView, dict]:
        matches = [
            item
            for item in views
            if item.relative_path == RUN_MANIFEST_PATH
        ]
        if len(matches) != 1:
            raise RunEvidenceNotFoundError(
                f"Job {job.job_id} 必须且只能有一个 {RUN_MANIFEST_PATH}"
            )
        view = matches[0]
        if view.size_bytes > self.max_manifest_bytes:
            raise RunEvidenceLimitExceededError(
                "run_manifest.json 超过读取上限"
            )

        opened = self.artifact_catalog.open(
            job=job,
            artifact_id=view.artifact_id,
        )
        try:
            descriptor = opened.artifact.descriptor
            stat = opened.blob.stat
            identity_matches = (
                descriptor.artifact_id == view.artifact_id
                and descriptor.relative_path == view.relative_path
                and descriptor.run_id == job.run_id
                and descriptor.sha256 == view.sha256
                and descriptor.size_bytes == view.size_bytes
                and stat.sha256 == view.sha256
                and stat.size_bytes == view.size_bytes
            )
            if not identity_matches:
                raise RunEvidenceIntegrityError(
                    "Catalog、Descriptor 与 Blob 身份不一致"
                )
            raw = opened.blob.body.read(self.max_manifest_bytes + 1)
        finally:
            opened.blob.body.close()

        if len(raw) > self.max_manifest_bytes or len(raw) != view.size_bytes:
            raise RunEvidenceIntegrityError(
                "run_manifest.json 读取大小不一致"
            )
        if hashlib.sha256(raw).hexdigest() != view.sha256:
            raise RunEvidenceIntegrityError(
                "run_manifest.json SHA-256 校验失败"
            )
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RunEvidenceIntegrityError(
                "run_manifest.json 不是有效 UTF-8 JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise RunEvidenceConflictError(
                "run_manifest.json 顶层必须是 object"
            )
        version = payload.get("manifest_version")
        if not isinstance(version, int) or version < 4:
            raise RunEvidenceConflictError(
                "可信运行读取需要 manifest_version >= 4"
            )
        if payload.get("job_id") != job.job_id:
            raise RunEvidenceIntegrityError(
                "run_manifest.json job_id 不一致"
            )
        if payload.get("run_id") != job.run_id:
            raise RunEvidenceIntegrityError(
                "run_manifest.json run_id 不一致"
            )
        return view, payload

    def read(self, job_id: str) -> VerifiedRunEvidence:
        job = self.jobs.get(job_id)
        self._require_terminal(job)
        workspace = self.jobs.get_workspace_manifest(
            job.workspace_manifest_id
        )
        self._validate_workspace(job, workspace)
        artifacts = self._list_artifacts(job)
        manifest_view, payload = self._read_manifest_blob(
            job=job,
            views=artifacts,
        )
        return VerifiedRunEvidence(
            job=job,
            workspace=workspace,
            artifacts=tuple(artifacts),
            run_manifest_artifact=manifest_view,
            run_manifest=payload,
        )
```

### 9.4 ComparisonService 改为复用 Reader

修改 `app/comparison/service.py`：

```python
# app/comparison/service.py：import 区域
from app.run_evidence.errors import (
    RunEvidenceConflictError,
    RunEvidenceIntegrityError,
    RunEvidenceLimitExceededError,
    RunEvidenceNotFoundError,
)
from app.run_evidence.reader import VerifiedRunEvidenceReader


class ComparisonService:
    def __init__(
        self,
        *,
        evidence_reader: VerifiedRunEvidenceReader,
        repository: FileComparisonRepository,
        max_changes: int,
    ):
        self.evidence_reader = evidence_reader
        self.jobs = evidence_reader.jobs
        self.repository = repository
        self.max_changes = max_changes
```

删除 `ComparisonService` 中已经迁移到 Reader 的：

```text
_require_terminal
_validate_workspace
_list_artifacts
_read_verified_manifest
```

将 `_snapshot()` 开头替换为：

```python
def _snapshot(self, job_id: str) -> RunSnapshot:
    try:
        evidence = self.evidence_reader.read(job_id)
    except RunEvidenceNotFoundError as exc:
        raise ComparisonNotFoundError(str(exc)) from exc
    except RunEvidenceConflictError as exc:
        raise ComparisonConflictError(str(exc)) from exc
    except RunEvidenceIntegrityError as exc:
        raise ComparisonIntegrityError(str(exc)) from exc
    except RunEvidenceLimitExceededError as exc:
        raise ComparisonLimitExceededError(str(exc)) from exc
    job = evidence.job
    workspace = evidence.workspace
    views = list(evidence.artifacts)
    run_manifest_view = evidence.run_manifest_artifact
    manifest = evidence.run_manifest

    # 下方 RunSnapshot 构建逻辑保持 Phase 38 原样。
```

修改 `app/comparison/factory.py`，确保 Comparison 与 Rerun 可以共享同一 reader：

```python
from app.run_evidence.reader import VerifiedRunEvidenceReader


def build_run_evidence_reader(
    *,
    jobs,
    artifact_catalog,
) -> VerifiedRunEvidenceReader:
    return VerifiedRunEvidenceReader(
        jobs=jobs,
        artifact_catalog=artifact_catalog,
        max_manifest_bytes=settings.comparison_manifest_max_bytes,
        max_artifacts=settings.comparison_max_artifacts,
    )


def build_comparison_service(
    *,
    jobs,
    artifact_catalog,
    evidence_reader: VerifiedRunEvidenceReader | None = None,
) -> ComparisonService:
    selected_reader = evidence_reader or build_run_evidence_reader(
        jobs=jobs,
        artifact_catalog=artifact_catalog,
    )
    return ComparisonService(
        evidence_reader=selected_reader,
        repository=build_comparison_repository(),
        max_changes=settings.comparison_max_changes,
    )
```

这一步完成后先运行 Phase 38 回归，确认抽取 Reader 没有改变 Comparison 语义：

```bash
python -m pytest \
  tests/test_comparison_service.py \
  tests/test_comparison_repository.py \
  tests/test_comparison_api.py
```

---

## 十、定义 Rerun Schema

> **本节类型：需要新增代码。**
>
> 需要新增：`app/rerun/schemas.py`。

以下 Schema 将命令模板、父证据、Proposal 内容和状态明确分离。新增完整文件：

```python
# app/rerun/schemas.py
from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

SHA256 = r"^[0-9a-f]{64}$"
PROPOSAL_ID = r"^rerun_[0-9a-f]{24}$"


class RerunModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RerunArgumentEdit(RerunModel):
    """第一版只编辑已经存在的 GNU-style 长选项。"""

    option: str = Field(pattern=r"^--[A-Za-z0-9][A-Za-z0-9_-]*$")
    operation: Literal["set", "remove"]
    expected_old_value: str | None = Field(default=None, max_length=2000)
    value: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_operation(self) -> "RerunArgumentEdit":
        if self.operation == "set":
            if self.expected_old_value is None:
                raise ValueError("set 必须声明 expected_old_value")
            if self.value is None:
                raise ValueError("set 必须提供 value")
        elif self.value is not None:
            raise ValueError("remove 不能提供 value")
        return self


class RerunTemplateArg(RerunModel):
    kind: Literal[
        "literal",
        "repo_path",
        "run_path",
        "dataset_path",
    ]
    value: str | None = Field(default=None, max_length=2000)
    relative_path: str | None = Field(default=None, max_length=1000)
    dataset_label: str | None = Field(default=None, max_length=200)

    @field_validator("value")
    @classmethod
    def reject_control_characters(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("template literal 不能为空")
        if value is not None and any(
            char in value for char in ("\x00", "\n", "\r")
        ):
            raise ValueError("template literal 不能包含控制字符")
        return value

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or value.startswith("/") or "\\" in value:
            raise ValueError("template path 必须是 POSIX 相对路径")
        parts = value.split("/")
        if any(part in {"", ".."} for part in parts):
            raise ValueError("template path 不能包含空段或 ..")
        return value

    @model_validator(mode="after")
    def validate_shape(self) -> "RerunTemplateArg":
        if self.kind == "literal":
            if self.value is None:
                raise ValueError("literal arg 缺少 value")
            if self.relative_path is not None or self.dataset_label is not None:
                raise ValueError("literal arg 不能包含路径模板字段")
        elif self.kind in {"repo_path", "run_path"}:
            if self.relative_path is None:
                raise ValueError("repo/run path arg 缺少 relative_path")
            if self.value is not None or self.dataset_label is not None:
                raise ValueError("repo/run path arg 字段组合非法")
        else:
            if self.relative_path is None or self.dataset_label is None:
                raise ValueError("dataset_path arg 缺少 label 或 relative_path")
            if not self.dataset_label.strip():
                raise ValueError("dataset_path label 不能为空")
            if self.value is not None:
                raise ValueError("dataset_path arg 不能包含 literal value")
        return self


class RerunCommandTemplate(RerunModel):
    argv: list[RerunTemplateArg] = Field(min_length=1, max_length=256)
    cwd_relative: str = "."
    # RunCommand 已支持 config；详细重跑 lineage 单独保存在 rerun_seed。
    source: Literal["config"] = "config"
    risk_level: Literal["low", "medium", "high"] = "high"
    reason: str = Field(min_length=1, max_length=1000)
    parent_command_sha256: str = Field(pattern=SHA256)
    template_hash: str = Field(pattern=SHA256)

    @field_validator("cwd_relative")
    @classmethod
    def validate_cwd_relative(cls, value: str) -> str:
        if not value or value.startswith("/"):
            raise ValueError("cwd_relative 必须是非空相对路径")
        parts = value.replace("\\", "/").split("/")
        if any(part in {"", ".."} for part in parts):
            raise ValueError("cwd_relative 不能包含空段或 ..")
        return value


class RerunSourceIdentity(RerunModel):
    parent_job_id: str = Field(min_length=1, max_length=200)
    parent_run_id: str = Field(min_length=1, max_length=300)
    parent_workspace_manifest_id: str = Field(min_length=1, max_length=200)
    parent_workspace_manifest_hash: str = Field(pattern=SHA256)
    parent_workspace_generation: int = Field(ge=0)
    parent_run_manifest_artifact_id: str = Field(min_length=1, max_length=300)
    parent_run_manifest_sha256: str = Field(pattern=SHA256)


class RerunProposalCreateRequest(RerunModel):
    parent_job_id: str = Field(min_length=1, max_length=200)
    expected_parent_job_version: int = Field(ge=0)
    expected_parent_run_manifest_sha256: str = Field(pattern=SHA256)
    edits: list[RerunArgumentEdit] = Field(min_length=1, max_length=16)
    experiment_goal: str | None = Field(default=None, max_length=1000)
    execution_profile_id: str | None = Field(default=None, max_length=200)
    comparison_id: str | None = Field(default=None, max_length=200)
    expected_comparison_hash: str | None = Field(default=None, pattern=SHA256)

    @model_validator(mode="after")
    def validate_comparison_binding(self) -> "RerunProposalCreateRequest":
        if (self.comparison_id is None) != (
            self.expected_comparison_hash is None
        ):
            raise ValueError(
                "comparison_id 和 expected_comparison_hash 必须同时提供"
            )
        options = [item.option for item in self.edits]
        if len(options) != len(set(options)):
            raise ValueError("同一 option 不能重复编辑")
        return self


class RerunProposal(RerunModel):
    proposal_version: Literal["phase39-v1"] = "phase39-v1"
    proposal_id: str = Field(pattern=PROPOSAL_ID)
    proposal_hash: str = Field(pattern=SHA256)
    source: RerunSourceIdentity
    comparison_id: str | None = None
    comparison_hash: str | None = Field(default=None, pattern=SHA256)
    edits: list[RerunArgumentEdit]
    command_template: RerunCommandTemplate
    experiment_goal: str
    execution_profile_id: str
    execution_policy_hash: str = Field(pattern=SHA256)
    execution_backend: Literal["local", "conda", "oci"]
    created_at: str
    expires_at: str


RerunProposalStatus = Literal[
    "pending",
    "submitting",
    "submitted",
    "cancelled",
    "expired",
]


class RerunProposalRecord(RerunModel):
    proposal: RerunProposal
    status: RerunProposalStatus
    version: int = Field(ge=0)
    child_job_id: str | None = None
    submit_idempotency_key: str | None = None
    last_error: str | None = None
    updated_at: str


class RerunProposalSubmitRequest(RerunModel):
    expected_proposal_hash: str = Field(pattern=SHA256)
    expected_version: int = Field(ge=0)


class RerunProposalCancelRequest(RerunModel):
    expected_proposal_hash: str = Field(pattern=SHA256)
    expected_version: int = Field(ge=0)
    reason: str = Field(default="user cancelled", min_length=1, max_length=500)


class DerivedRunInput(RerunModel):
    """持久化到子 JobRequest 的最小不可变派生契约。"""

    proposal_id: str = Field(pattern=PROPOSAL_ID)
    proposal_hash: str = Field(pattern=SHA256)
    source: RerunSourceIdentity
    command_template: RerunCommandTemplate
```

`DerivedRunInput` 不包含 `approved=True`、父路径、claim token 或 checkpoint ID。Schema 层根本不提供这些字段，
比在 Service 中“记得清空”更可靠。

---

## 十一、实现 Proposal 与模板 Hash

> **本节类型：需要新增代码。**
>
> 需要新增：`app/rerun/identity.py`。

新增完整文件：

```python
# app/rerun/identity.py
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from app.rerun.errors import RerunIntegrityError
from app.rerun.schemas import (
    RerunCommandTemplate,
    RerunProposal,
)


def canonical_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_value(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def command_template_hash(template: RerunCommandTemplate) -> str:
    payload = template.model_dump(mode="json")
    payload.pop("template_hash", None)
    return sha256_value(payload)


def validate_command_template_hash(
    template: RerunCommandTemplate,
) -> None:
    actual = command_template_hash(template)
    if actual != template.template_hash:
        raise RerunIntegrityError(
            "Rerun command template hash 校验失败"
        )


def proposal_hash(proposal: RerunProposal) -> str:
    payload = proposal.model_dump(mode="json")
    payload.pop("proposal_id", None)
    payload.pop("proposal_hash", None)
    return sha256_value(payload)


def proposal_id_for_hash(value: str) -> str:
    return f"rerun_{value[:24]}"


def validate_proposal_hash(proposal: RerunProposal) -> None:
    validate_command_template_hash(proposal.command_template)
    actual = proposal_hash(proposal)
    if actual != proposal.proposal_hash:
        raise RerunIntegrityError("Rerun Proposal hash 校验失败")
    if proposal.proposal_id != proposal_id_for_hash(actual):
        raise RerunIntegrityError("Rerun Proposal ID 与 hash 不一致")
```

这里将 `created_at` 和 `expires_at` 纳入 Proposal hash，因此两次独立创建即使编辑相同，也会得到两个
不同 Proposal；同一创建请求的重放由 `Idempotency-Key` 返回原 Proposal。

---

## 十二、实现安全命令模板与结构化参数编辑

> **本节类型：需要新增代码。**
>
> 需要新增：`app/rerun/command_template.py`。

这一层只接受父 `run_manifest` 中的原始 selected action。它不是通用 Shell parser，而是故意只支持
单进程命令安全子集。

新增完整文件：

```python
# app/rerun/command_template.py
from __future__ import annotations

import hashlib
import re
import shlex
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

from app.rerun.errors import (
    RerunCommandRejectedError,
    RerunConflictError,
    RerunIntegrityError,
)
from app.rerun.identity import (
    command_template_hash,
    validate_command_template_hash,
)
from app.rerun.schemas import (
    RerunArgumentEdit,
    RerunCommandTemplate,
    RerunTemplateArg,
)
from app.workspace.schemas import (
    ExternalDataReference,
    WorkspaceManifest,
)

_FORBIDDEN_SHELL = re.compile(r"[|&;<>`\n\r]|\$\(")
_OPTION = re.compile(r"^--[A-Za-z0-9][A-Za-z0-9_-]*$")
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_SECRET_PARTS = {
    "api-key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_secret_option(option: str) -> bool:
    normalized = option.lower().lstrip("-").replace("_", "-")
    return any(part in normalized for part in _SECRET_PARTS)


def _reject_shell_text(value: str, *, field: str) -> None:
    if not value or "\x00" in value or _FORBIDDEN_SHELL.search(value):
        raise RerunCommandRejectedError(
            f"{field} 包含空值、NUL 或不支持的 Shell 语法"
        )


def _pure_absolute(value: str, *, field: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts:
        raise RerunCommandRejectedError(
            f"{field} 必须是无 .. 的绝对 POSIX 路径"
        )
    return path


def _relative_under(
    value: PurePosixPath,
    root: PurePosixPath,
) -> str | None:
    try:
        relative = value.relative_to(root)
    except ValueError:
        return None
    text = relative.as_posix()
    return text if text else "."


def _dataset_root(reference: ExternalDataReference) -> PurePosixPath | None:
    parsed = urlparse(reference.uri)
    if parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"}:
            return None
        return _pure_absolute(
            unquote(parsed.path),
            field=f"dataset {reference.name} uri",
        )
    if not parsed.scheme and reference.uri.startswith("/"):
        return _pure_absolute(
            reference.uri,
            field=f"dataset {reference.name} uri",
        )
    return None


def _normalize_option_equals(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    for token in argv:
        if token.startswith("--") and "=" in token:
            option, value = token.split("=", 1)
            if not _OPTION.fullmatch(option):
                raise RerunCommandRejectedError(
                    f"非法长选项：{option!r}"
                )
            normalized.extend([option, value])
        else:
            normalized.append(token)
    return normalized


def _parse_parent_argv(
    command: str,
    *,
    max_command_chars: int,
    max_argv_items: int,
) -> list[str]:
    if len(command) > max_command_chars:
        raise RerunCommandRejectedError("父命令超过字符上限")
    _reject_shell_text(command, field="parent command")
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as exc:
        raise RerunCommandRejectedError(
            "父命令不是合法的单进程 argv"
        ) from exc
    if not argv or len(argv) > max_argv_items:
        raise RerunCommandRejectedError(
            "父命令 argv 为空或超过数量上限"
        )
    if _ENV_ASSIGNMENT.match(argv[0]):
        raise RerunCommandRejectedError(
            "第一版不继承命令前的环境变量赋值"
        )
    normalized = _normalize_option_equals(argv)
    for token in normalized:
        if _OPTION.fullmatch(token) and _is_secret_option(token):
            raise RerunCommandRejectedError(
                f"父命令包含 secret-like 参数：{token}"
            )
    return normalized


def _find_edit_span(
    argv: list[str],
    edit: RerunArgumentEdit,
) -> tuple[int, int]:
    indexes = [
        index
        for index, token in enumerate(argv)
        if token == edit.option
    ]
    if len(indexes) != 1:
        raise RerunCommandRejectedError(
            f"{edit.option} 必须在父命令中恰好出现一次"
        )
    start = indexes[0]
    next_index = start + 1

    if edit.expected_old_value is None:
        # expected_old_value=None 表示调用方确认它是无值 flag。
        if next_index < len(argv) and not argv[next_index].startswith("--"):
            raise RerunCommandRejectedError(
                f"{edit.option} 当前看起来带值；请提交 expected_old_value"
            )
        return start, start + 1

    if next_index >= len(argv) or argv[next_index] != edit.expected_old_value:
        raise RerunConflictError(
            f"{edit.option} 的旧值已变化或与 expected_old_value 不一致"
        )
    return start, start + 2


def _validate_new_value(value: str) -> None:
    _reject_shell_text(value, field="new option value")
    if value.startswith("/"):
        raise RerunCommandRejectedError(
            "参数编辑不能注入新的主机绝对路径"
        )
    if value.startswith("${"):
        raise RerunCommandRejectedError(
            "参数编辑不能伪造内部模板占位符"
        )


def apply_argument_edits(
    argv: list[str],
    edits: list[RerunArgumentEdit],
) -> list[str]:
    result = list(argv)
    seen: set[str] = set()
    for edit in edits:
        if edit.option in seen:
            raise RerunCommandRejectedError("同一 option 不能重复编辑")
        seen.add(edit.option)
        if _is_secret_option(edit.option):
            raise RerunCommandRejectedError(
                "禁止修改 secret-like option"
            )
        start, end = _find_edit_span(result, edit)
        if edit.operation == "remove":
            result[start:end] = []
        else:
            assert edit.value is not None
            _validate_new_value(edit.value)
            result[start:end] = [edit.option, edit.value]
    return result


def _template_arg(
    token: str,
    *,
    repo_root: PurePosixPath,
    run_root: PurePosixPath,
    datasets: list[ExternalDataReference],
) -> RerunTemplateArg:
    if not token.startswith("/"):
        return RerunTemplateArg(kind="literal", value=token)

    absolute = _pure_absolute(token, field="command argument")
    repo_relative = _relative_under(absolute, repo_root)
    if repo_relative is not None:
        return RerunTemplateArg(
            kind="repo_path",
            relative_path=repo_relative,
        )

    run_relative = _relative_under(absolute, run_root)
    if run_relative is not None:
        return RerunTemplateArg(
            kind="run_path",
            relative_path=run_relative,
        )

    matches: list[tuple[ExternalDataReference, str]] = []
    for reference in datasets:
        root = _dataset_root(reference)
        if root is None:
            continue
        relative = _relative_under(absolute, root)
        if relative is not None:
            matches.append((reference, relative))
    if len(matches) == 1:
        reference, relative = matches[0]
        return RerunTemplateArg(
            kind="dataset_path",
            dataset_label=reference.required_worker_label,
            relative_path=relative,
        )
    if len(matches) > 1:
        raise RerunCommandRejectedError(
            "绝对路径同时匹配多个 dataset reference"
        )
    raise RerunCommandRejectedError(
        "命令包含无法解释的主机绝对路径"
    )


def build_command_template(
    *,
    selected_action: Any,
    run_manifest: dict,
    workspace: WorkspaceManifest,
    edits: list[RerunArgumentEdit],
    max_command_chars: int,
    max_argv_items: int,
) -> RerunCommandTemplate:
    if not isinstance(selected_action, dict):
        raise RerunCommandRejectedError(
            "父 run_manifest 缺少 selected_run_command"
        )
    command = str(selected_action.get("command") or "").strip()
    cwd = str(selected_action.get("cwd") or "").strip()
    repo_path = str(run_manifest.get("repo_path") or "").strip()
    run_dir = str(run_manifest.get("run_dir") or "").strip()
    if not command or not cwd or not repo_path or not run_dir:
        raise RerunCommandRejectedError(
            "父命令缺少 command、cwd、repo_path 或 run_dir"
        )

    repo_root = _pure_absolute(repo_path, field="parent repo_path")
    run_root = _pure_absolute(run_dir, field="parent run_dir")
    cwd_path = _pure_absolute(cwd, field="parent command cwd")
    cwd_relative = _relative_under(cwd_path, repo_root)
    if cwd_relative is None:
        raise RerunCommandRejectedError(
            "父命令 cwd 不在父 repository 内"
        )

    argv = _parse_parent_argv(
        command,
        max_command_chars=max_command_chars,
        max_argv_items=max_argv_items,
    )
    edited_argv = apply_argument_edits(argv, edits)
    if not edited_argv:
        raise RerunCommandRejectedError("编辑后命令为空")

    template_args = [
        _template_arg(
            token,
            repo_root=repo_root,
            run_root=run_root,
            datasets=workspace.external_data,
        )
        for token in edited_argv
    ]
    draft = RerunCommandTemplate(
        argv=template_args,
        cwd_relative=cwd_relative,
        source="config",
        risk_level="high",
        reason="由可信父运行派生；必须重新完成预检与审批。",
        parent_command_sha256=_sha256_text(command),
        template_hash="0" * 64,
    )
    return draft.model_copy(
        update={"template_hash": command_template_hash(draft)}
    )


def _resolve_inside(root: Path, relative_path: str) -> Path:
    if relative_path == ".":
        return root.resolve()
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise RerunIntegrityError("模板相对路径非法")
    target = (root / Path(*pure.parts)).resolve()
    root = root.resolve()
    if target != root and root not in target.parents:
        raise RerunIntegrityError("模板路径逃逸运行时根目录")
    return target


def resolve_command_template(
    *,
    template: RerunCommandTemplate,
    repo_path: str,
    run_dir: str,
    dataset_mounts: dict[str, str],
) -> dict[str, str]:
    validate_command_template_hash(template)
    repo_root = Path(repo_path).resolve()
    child_run_root = Path(run_dir).resolve()
    argv: list[str] = []
    for item in template.argv:
        if item.kind == "literal":
            assert item.value is not None
            argv.append(item.value)
        elif item.kind == "repo_path":
            assert item.relative_path is not None
            argv.append(
                str(_resolve_inside(repo_root, item.relative_path))
            )
        elif item.kind == "run_path":
            assert item.relative_path is not None
            argv.append(
                str(_resolve_inside(child_run_root, item.relative_path))
            )
        else:
            assert item.dataset_label is not None
            assert item.relative_path is not None
            raw_mount = dataset_mounts.get(item.dataset_label)
            if not raw_mount:
                raise RerunIntegrityError(
                    f"Worker 缺少数据集挂载：{item.dataset_label}"
                )
            mount_root = Path(raw_mount).resolve()
            argv.append(
                str(_resolve_inside(mount_root, item.relative_path))
            )

    cwd = _resolve_inside(repo_root, template.cwd_relative)
    return {
        "command": shlex.join(argv),
        "cwd": str(cwd),
        "source": template.source,
        "risk_level": template.risk_level,
        "reason": template.reason,
    }
```

这里故意将新增值限制为非绝对路径。需要切换数据集时，不应伪装成普通参数编辑，而应创建新的
Resource/Job 输入，以便数据集 fingerprint 和 Worker label 也发生可审计变化。

---

## 十三、实现持久 Proposal Repository

> **本节类型：需要新增代码。**
>
> 需要新增：`app/rerun/repository.py`。

Proposal 使用独立 SQLite 数据库。即使 Job Store 使用 PostgreSQL，也不要让 API route 直接写两套表。
Repository 只负责状态机，跨库 exactly-once 由 RerunService 和 Job 幂等键完成。

新增完整文件：

```python
# app/rerun/repository.py
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.rerun.errors import (
    RerunConflictError,
    RerunExpiredError,
    RerunIntegrityError,
    RerunNotFoundError,
)
from app.rerun.identity import validate_proposal_hash
from app.rerun.schemas import (
    RerunProposal,
    RerunProposalRecord,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_expired(proposal: RerunProposal, now: str) -> bool:
    return proposal.expires_at <= now


class SqliteRerunRepository:
    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.path = path
        self.clock = clock

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=30.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rerun_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    proposal_hash TEXT NOT NULL UNIQUE,
                    create_idempotency_key TEXT NOT NULL UNIQUE,
                    create_request_hash TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    child_job_id TEXT,
                    submit_idempotency_key TEXT,
                    last_error TEXT,
                    cancel_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rerun_parent_job
                ON rerun_proposals(
                    json_extract(proposal_json, '$.source.parent_job_id'),
                    created_at DESC
                )
                """
            )
        finally:
            connection.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> RerunProposalRecord:
        proposal = RerunProposal.model_validate_json(row["proposal_json"])
        validate_proposal_hash(proposal)
        if proposal.proposal_id != row["proposal_id"]:
            raise RerunIntegrityError("Proposal row identity 不一致")
        if proposal.proposal_hash != row["proposal_hash"]:
            raise RerunIntegrityError("Proposal row hash 不一致")
        return RerunProposalRecord(
            proposal=proposal,
            status=row["status"],
            version=row["version"],
            child_job_id=row["child_job_id"],
            submit_idempotency_key=row["submit_idempotency_key"],
            last_error=row["last_error"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_by_id(
        connection: sqlite3.Connection,
        proposal_id: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM rerun_proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
        if row is None:
            raise RerunNotFoundError(
                f"Rerun Proposal 不存在：{proposal_id}"
            )
        return row

    def _expire_if_needed(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> sqlite3.Row:
        record = self._record(row)
        if (
            record.status == "pending"
            and _is_expired(record.proposal, self.clock())
        ):
            connection.execute(
                """
                UPDATE rerun_proposals
                SET status = 'expired', version = version + 1, updated_at = ?
                WHERE proposal_id = ? AND version = ?
                """,
                (self.clock(), record.proposal.proposal_id, record.version),
            )
            return self._row_by_id(
                connection,
                record.proposal.proposal_id,
            )
        return row

    def create(
        self,
        *,
        proposal: RerunProposal,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[RerunProposalRecord, bool]:
        validate_proposal_hash(proposal)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT * FROM rerun_proposals
                WHERE create_idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["create_request_hash"] != request_hash:
                    raise RerunConflictError(
                        "创建 Proposal 的幂等键已绑定其他请求"
                    )
                connection.execute("COMMIT")
                return self._record(existing), False

            now = self.clock()
            connection.execute(
                """
                INSERT INTO rerun_proposals (
                    proposal_id, proposal_hash,
                    create_idempotency_key, create_request_hash,
                    proposal_json, status, version,
                    child_job_id, submit_idempotency_key,
                    last_error, cancel_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', 0, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.proposal_hash,
                    idempotency_key,
                    request_hash,
                    proposal.model_dump_json(),
                    now,
                    now,
                ),
            )
            row = self._row_by_id(connection, proposal.proposal_id)
            connection.execute("COMMIT")
            return self._record(row), True
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def get(self, proposal_id: str) -> RerunProposalRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._row_by_id(connection, proposal_id)
            row = self._expire_if_needed(connection, row)
            connection.execute("COMMIT")
            return self._record(row)
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def begin_submission(
        self,
        *,
        proposal_id: str,
        expected_hash: str,
        expected_version: int,
        submit_idempotency_key: str,
    ) -> RerunProposalRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._expire_if_needed(
                connection,
                self._row_by_id(connection, proposal_id),
            )
            record = self._record(row)
            if record.proposal.proposal_hash != expected_hash:
                raise RerunConflictError("Proposal hash 已变化")
            if record.status == "expired":
                raise RerunExpiredError("Proposal 已过期")
            if record.status == "submitted":
                connection.execute("COMMIT")
                return record
            if record.status == "submitting":
                if record.submit_idempotency_key != submit_idempotency_key:
                    raise RerunConflictError("Proposal 正由其他提交操作处理")
                connection.execute("COMMIT")
                return record
            if record.status != "pending":
                raise RerunConflictError(
                    f"Proposal 当前不能提交：{record.status}"
                )
            if record.version != expected_version:
                raise RerunConflictError(
                    "Proposal version 已变化，请刷新后重试"
                )

            now = self.clock()
            connection.execute(
                """
                UPDATE rerun_proposals
                SET status = 'submitting',
                    submit_idempotency_key = ?,
                    last_error = NULL,
                    version = version + 1,
                    updated_at = ?
                WHERE proposal_id = ? AND version = ?
                """,
                (
                    submit_idempotency_key,
                    now,
                    proposal_id,
                    record.version,
                ),
            )
            updated = self._record(
                self._row_by_id(connection, proposal_id)
            )
            connection.execute("COMMIT")
            return updated
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def complete_submission(
        self,
        *,
        proposal_id: str,
        submit_idempotency_key: str,
        child_job_id: str,
    ) -> RerunProposalRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            record = self._record(
                self._row_by_id(connection, proposal_id)
            )
            if record.status == "submitted":
                if record.child_job_id != child_job_id:
                    raise RerunIntegrityError(
                        "Proposal 已绑定另一个 child Job"
                    )
                connection.execute("COMMIT")
                return record
            if (
                record.status != "submitting"
                or record.submit_idempotency_key != submit_idempotency_key
            ):
                raise RerunConflictError("Proposal submission ownership 不匹配")

            now = self.clock()
            connection.execute(
                """
                UPDATE rerun_proposals
                SET status = 'submitted',
                    child_job_id = ?,
                    version = version + 1,
                    updated_at = ?
                WHERE proposal_id = ? AND version = ?
                """,
                (child_job_id, now, proposal_id, record.version),
            )
            updated = self._record(
                self._row_by_id(connection, proposal_id)
            )
            connection.execute("COMMIT")
            return updated
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def record_submission_error(
        self,
        *,
        proposal_id: str,
        submit_idempotency_key: str,
        detail: str,
    ) -> None:
        """保持 submitting，重试仍使用同一 Job 幂等键消歧。"""

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            record = self._record(
                self._row_by_id(connection, proposal_id)
            )
            if (
                record.status == "submitting"
                and record.submit_idempotency_key == submit_idempotency_key
            ):
                connection.execute(
                    """
                    UPDATE rerun_proposals
                    SET last_error = ?, version = version + 1, updated_at = ?
                    WHERE proposal_id = ? AND version = ?
                    """,
                    (detail[:1000], self.clock(), proposal_id, record.version),
                )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def cancel(
        self,
        *,
        proposal_id: str,
        expected_hash: str,
        expected_version: int,
        reason: str,
    ) -> RerunProposalRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._expire_if_needed(
                connection,
                self._row_by_id(connection, proposal_id),
            )
            record = self._record(row)
            if record.proposal.proposal_hash != expected_hash:
                raise RerunConflictError("Proposal hash 已变化")
            if record.status == "cancelled":
                connection.execute("COMMIT")
                return record
            if record.status != "pending":
                raise RerunConflictError(
                    f"只有 pending Proposal 可以取消：{record.status}"
                )
            if record.version != expected_version:
                raise RerunConflictError("Proposal version 已变化")
            connection.execute(
                """
                UPDATE rerun_proposals
                SET status = 'cancelled', cancel_reason = ?,
                    version = version + 1, updated_at = ?
                WHERE proposal_id = ? AND version = ?
                """,
                (reason, self.clock(), proposal_id, record.version),
            )
            updated = self._record(
                self._row_by_id(connection, proposal_id)
            )
            connection.execute("COMMIT")
            return updated
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def ping(self) -> bool:
        connection = self._connect()
        try:
            return connection.execute("SELECT 1").fetchone()[0] == 1
        finally:
            connection.close()
```

注意：`record_submission_error()` 不把状态改回 `pending`。数据库连接中断时，调用方无法证明
Job 是否已经创建；保持 `submitting` 并以同一个 Job 幂等键重试，才能安全消除这种歧义。
TTL 也只把 `pending` 变成 `expired`；`submitting` 可能已经产生子 Job，必须一直保留恢复入口。

---

## 十四、为 Workspace 增加版本化物化模式

> **本节类型：需要修改代码。**
>
> 需要修改：`app/workspace/schemas.py`、`app/workspace/repository.py`。

### 14.1 为什么不能只加一个默认字段

历史 `phase26-v1` Manifest 的 hash 是按旧字段集合计算的。如果直接给 Pydantic Model 新增
`materialization_mode="auto"`，`model_dump()` 会把默认字段加入重算 payload，所有旧 Manifest 都会
报 hash 校验失败。

因此必须同时做两件事：

```text
旧 phase26-v1：重算 hash 时排除 materialization_mode
新 phase39-v2：重算 hash 时包含 materialization_mode
```

### 14.2 修改 WorkspaceManifest

在 `app/workspace/schemas.py` 中增加类型，并替换 `WorkspaceManifest` 对应部分：

```python
WorkspaceMaterializationMode = Literal[
    "auto",
    "host_paths",
    "blob_entries",
]


class WorkspaceManifest(WorkspaceModel):
    manifest_version: Literal[
        "phase26-v1",
        "phase39-v2",
    ] = "phase39-v2"
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
    external_data: list[ExternalDataReference] = Field(default_factory=list)
    portable: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    source_paths: WorkspaceSourcePaths | None = None

    # auto 保持 phase26 语义：portable 从 Blob，non-portable 从 host path。
    materialization_mode: WorkspaceMaterializationMode = "auto"
    created_at: str

    def resolved_materialization_mode(
        self,
    ) -> Literal["host_paths", "blob_entries"]:
        if self.materialization_mode != "auto":
            return self.materialization_mode
        return "blob_entries" if self.portable else "host_paths"

    @model_validator(mode="after")
    def validate_portability(self) -> "WorkspaceManifest":
        logical_paths = [item.logical_path for item in self.entries]
        if len(logical_paths) != len(set(logical_paths)):
            raise ValueError("manifest logical_path 重复")
        if self.manifest_version == "phase26-v1":
            if self.materialization_mode != "auto":
                raise ValueError("phase26-v1 只能使用 auto materialization")

        if self.portable and self.blocked_reasons:
            raise ValueError("portable manifest 不能包含 blocked_reasons")
        if not self.portable and not self.blocked_reasons:
            raise ValueError("non-portable manifest 必须说明原因")
        if self.portable and self.materialization_mode == "host_paths":
            raise ValueError("portable manifest 不能强制复用 host_paths")

        mode = self.resolved_materialization_mode()
        if mode == "host_paths" and self.source_paths is None:
            raise ValueError("host_paths materialization 缺少 source_paths")
        if mode == "blob_entries":
            paper = [item for item in self.entries if item.role == "paper"]
            bundles = [
                item
                for item in self.entries
                if item.role == "repository_bundle"
            ]
            if len(paper) != 1 or len(bundles) != 1:
                raise ValueError(
                    "blob_entries materialization 需要唯一 paper 和 repository bundle"
                )
            if not self.repository.clean:
                raise ValueError("blob_entries 不能物化 dirty repository")
        return self
```

### 14.3 修改版本化 hash

修改 `app/workspace/repository.py` 中的 `workspace_manifest_hash()`：

```python
def workspace_manifest_hash(
    manifest: WorkspaceManifest | dict[str, Any],
) -> str:
    if isinstance(manifest, WorkspaceManifest):
        payload = manifest.model_dump()
    else:
        payload = dict(manifest)

    payload.pop("manifest_hash", None)
    payload.pop("manifest_id", None)
    payload.pop("created_at", None)

    # 历史 hash 兼容：该字段在 phase26-v1 创建时不存在。
    if payload.get("manifest_version") == "phase26-v1":
        payload.pop("materialization_mode", None)

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
```

必须增加回归测试：加载一个真实格式的 `phase26-v1` payload，确认新增字段后仍能通过旧 hash；再篡改
`phase39-v2.materialization_mode`，确认新 hash 校验失败。

---

## 十五、从父 Blob 派生 generation-0 Workspace

> **本节类型：需要修改代码。**
>
> 需要修改：`app/workspace/snapshot.py`。

### 15.1 扩展 `_build_manifest()`

在参数中增加：

```python
def _build_manifest(
    self,
    *,
    # 原有参数保持不变
    materialization_mode: str = "auto",
) -> WorkspaceManifest:
    ...
```

构造 `WorkspaceManifest` 时增加：

```python
draft = WorkspaceManifest(
    manifest_version="phase39-v2",
    # 原有字段保持不变
    materialization_mode=materialization_mode,
)
```

现有 `snapshot_initial()`、`snapshot_initial_from_resources()` 和 `seal()` 不传该参数，继续使用
`auto`。只有派生分支显式使用 `blob_entries`。

### 15.2 新增 `derive_initial()`

在 `WorkspaceSnapshotter` 类中新增完整方法：

```python
def derive_initial(
    self,
    *,
    job_id: str,
    run_id: str,
    parent: WorkspaceManifest,
    source_host_id: str,
    external_data: list[ExternalDataReference],
) -> WorkspaceManifest:
    """从父终态 Manifest 的不可变输入 Blob 创建子 generation-0。"""

    from app.workspace.repository import validate_manifest_hash

    validate_manifest_hash(parent)
    if parent.repository.clean is not True:
        raise WorkspaceNotPortableError(
            "dirty repository 不能进行不可变重跑派生"
        )
    if parent.repository.bundle_logical_path is None:
        raise WorkspaceNotPortableError(
            "父 Workspace 缺少 repository bundle identity"
        )
    if external_data != parent.external_data:
        raise WorkspaceIntegrityError(
            "派生 Job 的 dataset references 与父 Workspace 不一致"
        )

    input_roles = {
        "paper",
        "input_log",
        "repository_bundle",
    }
    entries = [
        item.model_copy(deep=True)
        for item in parent.entries
        if item.role in input_roles
    ]
    paper_count = sum(item.role == "paper" for item in entries)
    bundle_count = sum(
        item.role == "repository_bundle" for item in entries
    )
    if paper_count != 1 or bundle_count != 1:
        raise WorkspaceIntegrityError(
            "父 Workspace 必须包含唯一 paper 与 repository bundle"
        )

    # 注意：不复制 run_artifact/process_record/process_log，也不保存父 source_paths。
    return self._build_manifest(
        job_id=job_id,
        run_id=run_id,
        generation=0,
        parent_manifest_id=parent.manifest_id,
        source_host_id=source_host_id,
        source_worker_session_id=None,
        entries=entries,
        repository=parent.repository.model_copy(deep=True),
        external_data=[item.model_copy(deep=True) for item in external_data],
        blocked_reasons=[],
        source_paths=None,
        materialization_mode="blob_entries",
    )
```

本地 BlobStore 会在 `_build_manifest()` 中追加 `blob_store_is_host_local`，因此子 Manifest 仍然
`portable=False`、仍绑定当前 host；但它的 `materialization_mode="blob_entries"`，不会重用父路径。

---

## 十六、让 Materializer 正确处理本机 Blob 派生

> **本节类型：需要修改代码。**
>
> 需要修改：`app/workspace/materializer.py`。

当前代码以 `manifest.portable` 决定走 host path 还是 Blob。将这个判断替换为两个独立事实：

```python
mode = manifest.resolved_materialization_mode()

# portable 只决定调度时是否需要 host affinity。
affinity_host_id = None if manifest.portable else manifest.source_host_id

# materialization mode 决定实际从哪里创建 workspace。
from_blob_entries = mode == "blob_entries"
```

### 16.1 修改 `planned_binding()`

保留 `explain_compatibility()` 的 host affinity 逻辑，然后将 non-portable 分支改成：

```python
mode = manifest.resolved_materialization_mode()
now = utc_now()

if mode == "host_paths":
    if manifest.source_paths is None:
        raise WorkspaceNotPortableError(
            "host_paths manifest 缺少 source_paths"
        )
    source = manifest.source_paths
    if source.run_dir is None:
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

# blob_entries 分支继续使用现有 epoch_root WorkspaceBinding 代码。
```

### 16.2 修改 `materialize()`

将开头的 host-affine 判断改成：

```python
validate_manifest_hash(manifest)
mode = manifest.resolved_materialization_mode()

if not manifest.portable and binding.host_id != manifest.source_host_id:
    raise WorkspaceNotPortableError("host affinity 不匹配")

if mode == "host_paths":
    for path in (Path(binding.repo_path), Path(binding.paper_path)):
        if not path.exists():
            raise WorkspaceNotPortableError(
                f"affinity host source 不存在：{path}"
            )
    create_run_layout_at(Path(binding.run_dir))
    return binding.model_copy(
        update={"status": "ready", "updated_at": utc_now()}
    )

# 下方原 portable Blob copy + git clone 分支保持不变，
# 现在也会被 non-portable/blob_entries Manifest 使用。
```

同时将 `_clone_repository()` 中错误文字：

```text
portable manifest 缺少 Git bundle
```

改为：

```text
blob-entry manifest 缺少 Git bundle
```

避免日志把“本机 Blob 派生”误写成 portable。

---

## 十七、扩展 JobRequest 与 JobService 派生分支

> **本节类型：需要修改代码。**
>
> 需要修改：`app/job_runtime/schemas.py`、`app/job_runtime/service.py`、`app/job_runtime/postgres_store.py`。

### 17.1 JobRequest 三种互斥输入模式

修改 `app/job_runtime/schemas.py`：

```python
from app.rerun.schemas import DerivedRunInput


class JobRequest(JobModel):
    paper_path: str | None = None
    repo_path: str | None = None
    paper_resource: ResolvedResourceInput | None = None
    repo_resource: ResolvedResourceInput | None = None
    derived_run: DerivedRunInput | None = None
    log_path: str | None = None
    experiment_goal: str = "复现论文 main result"
    execution_profile_id: str = Field(min_length=1)
    dataset_refs: list[ExternalDataReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_input_sources(self) -> "JobRequest":
        local_complete = (
            self.paper_path is not None
            and self.repo_path is not None
            and self.paper_resource is None
            and self.repo_resource is None
            and self.derived_run is None
        )
        resource_complete = (
            self.paper_resource is not None
            and self.repo_resource is not None
            and self.paper_path is None
            and self.repo_path is None
            and self.derived_run is None
        )
        derived_complete = (
            self.derived_run is not None
            and self.paper_path is None
            and self.repo_path is None
            and self.paper_resource is None
            and self.repo_resource is None
            and self.log_path is None
        )
        if sum((local_complete, resource_complete, derived_complete)) != 1:
            raise ValueError(
                "JobRequest 必须完整选择 local、resource 或 derived_run 一种输入模式"
            )
        return self
```

派生模式禁止 `log_path`，因为 input log 是否存在由父 Workspace Blob 决定，不再读取本机路径。

### 17.2 JobService 校验父 Manifest

在 `app/job_runtime/service.py` import 中增加：

```python
from app.job_runtime.schemas import TERMINAL_JOB_STATUSES
from app.workspace.repository import validate_manifest_hash
```

这里不需要重新构造完整 Proposal；`RerunService` 会校验 Proposal，JobService 只重新验证持久化在
`DerivedRunInput` 中的父 Workspace 身份。将 `_build_initial_manifest()` 的开头增加：

```python
if request.derived_run is not None:
    source = request.derived_run.source
    parent_job = self.store.get(source.parent_job_id)
    if parent_job.status not in TERMINAL_JOB_STATUSES:
        raise ValueError("derived parent Job 必须是终态")
    if parent_job.run_id != source.parent_run_id:
        raise ValueError("derived parent run_id 不一致")
    if parent_job.workspace_manifest_id != source.parent_workspace_manifest_id:
        raise ValueError("derived parent workspace pointer 已变化")

    parent = self.store.get_workspace_manifest(
        source.parent_workspace_manifest_id
    )
    validate_manifest_hash(parent)
    if (
        parent.manifest_hash != source.parent_workspace_manifest_hash
        or parent.generation != source.parent_workspace_generation
        or parent.job_id != source.parent_job_id
        or parent.run_id != source.parent_run_id
    ):
        raise ValueError("derived parent Workspace identity 不一致")
    if list(request.dataset_refs) != list(parent.external_data):
        raise ValueError("derived Job dataset references 已漂移")

    return self.workspace_snapshotter.derive_initial(
        job_id=job_id,
        run_id=run_id,
        parent=parent,
        source_host_id=settings.worker_host_id,
        external_data=external_data,
    )
```

该分支必须放在 resource/local 分支之前，且不能访问 `request.paper_path` 或 `request.repo_path`。

### 17.3 修复 PostgreSQL request hash 一致性

当前 SQLite Job Store 的 `request_hash` 包含 `requirements`，PostgreSQL 分支只包含 `thread_id + request`。
在依赖派生幂等前先统一，否则同一个 profile ID 的受信任配置变化可能被 PostgreSQL 错误重放。

修改 `app/job_runtime/postgres_store.py`：

```python
request_payload = request.model_dump()
requirements_payload = requirements.model_dump()
request_hash = _json_hash(
    {
        "thread_id": thread_id,
        "request": request_payload,
        "requirements": requirements_payload,
    }
)
```

测试中应对 SQLite/PostgreSQL store contract 使用同一组 case：同幂等键、同请求、不同 requirements
必须冲突。

---

## 十八、将 Rerun Seed 接回完整安全图

> **本节类型：需要新增并修改代码。**
>
> 需要新增：`app/nodes/rerun_seed_node.py`。
>
> 需要修改：`app/state.py`、`app/job_runtime/graph_runner.py`、`app/graph.py`。

### 18.1 保持 RunCommand 来源边界

不要修改 `app/schemas.py` 的 `RunCommand.source`。`RunCommand` 同时是 LLM 生成的
ExperimentPlan Schema；如果增加 `rerun_proposal`，普通规划模型也可能伪称命令来自可信 Proposal。

`RerunCommandTemplate` 使用现有、可被 `RunCommand` 接受的 `config`，详细可信来源由独立
`planning/rerun_seed.json` 绑定：

```python
source: Literal["config"] = "config"
```

### 18.2 GraphRunner 在受信任 Worker 上解析模板

在 `app/job_runtime/graph_runner.py` 增加：

```python
from app.rerun.command_template import resolve_command_template
```

在 `_initial_state()` 返回前构造：

```python
rerun_seed = None
if request.derived_run is not None:
    resolved = resolve_command_template(
        template=request.derived_run.command_template,
        repo_path=binding.repo_path,
        run_dir=binding.run_dir,
        dataset_mounts=claim.worker.capabilities.dataset_mounts,
    )
    rerun_seed = {
        "proposal_id": request.derived_run.proposal_id,
        "proposal_hash": request.derived_run.proposal_hash,
        "source": request.derived_run.source.model_dump(mode="json"),
        "template_hash": request.derived_run.command_template.template_hash,
        "run_command": resolved,
    }
```

在初始 State 中增加：

```python
initial_state = {
    # 原有字段保持不变。
    "rerun_seed": rerun_seed,
}
```

不要把完整 `dataset_mounts` 保存到 checkpoint；只保存解析后的命令。Worker 本机能力路径不应成为
新的公共控制面字段。

### 18.3 State 字段

在 `app/state.py` 增加：

```python
# Phase 39：只在 derived Job 中存在；普通 Job 为 None 或缺省。
rerun_seed: dict[str, Any] | None
rerun_seed_path: str | None
```

### 18.4 完整 rerun seed node

新增 `app/nodes/rerun_seed_node.py`：

```python
# app/nodes/rerun_seed_node.py
from __future__ import annotations

from app.schemas import RunCommand
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)


def rerun_seed_node(state: dict) -> dict:
    """普通 Job 是 no-op；派生 Job 用可信种子覆盖 LLM 候选命令。"""

    raw_seed = state.get("rerun_seed")
    if raw_seed is None:
        return {}
    if not isinstance(raw_seed, dict):
        raise ValueError("rerun_seed 必须是 object")

    command = RunCommand.model_validate(raw_seed.get("run_command"))
    payload = {
        "proposal_id": raw_seed.get("proposal_id"),
        "proposal_hash": raw_seed.get("proposal_hash"),
        "source": raw_seed.get("source"),
        "template_hash": raw_seed.get("template_hash"),
        "run_command": command.model_dump(mode="json"),
    }
    path, record = write_json_artifact(
        state=state,
        relative_path="planning/rerun_seed.json",
        payload=payload,
        producer_node="rerun_seed",
    )

    # 所有依赖旧命令或旧 action 的状态都显式清空。
    return {
        "run_commands": [command.model_dump(mode="json")],
        "edited_run_commands": [],
        "selected_run_command_index": None,
        "command_selection_record": None,
        "pending_action": None,
        "pending_action_hash": None,
        "requires_approval": False,
        "user_approval": None,
        "human_feedback": None,
        "approval_record": None,
        "preflight_report": None,
        "preflight_passed": False,
        "rerun_seed_path": str(path),
        **artifact_state_update(state, [record]),
    }
```

### 18.5 修改 Graph

在 `app/graph.py` import：

```python
from app.nodes.rerun_seed_node import rerun_seed_node
```

注册节点：

```python
add_guarded(builder, "rerun_seed", rerun_seed_node)
```

将线性边：

```python
("experiment_plan", "command_selection_prepare"),
```

替换为：

```python
("experiment_plan", "rerun_seed"),
("rerun_seed", "command_selection_prepare"),
```

普通 Job 的 `rerun_seed_node` 返回空更新，不改变 Phase 38 之前的流程。派生 Job 仍先完成论文阅读、仓库扫描、
mapping 和 experiment plan，但在用户选择命令前，用可信模板产生的唯一候选覆盖模型候选。

---

## 十九、实现 RerunService 用例层

> **本节类型：需要新增并小幅补充代码。**
>
> 需要新增：`app/rerun/service.py`。
>
> 需要补充：`app/rerun/repository.py`、`app/rerun/schemas.py`。

### 19.1 先给 Repository 增加创建重放查询

在 `SqliteRerunRepository` 中增加：

```python
def find_create_replay(
    self,
    *,
    idempotency_key: str,
    request_hash: str,
) -> RerunProposalRecord | None:
    connection = self._connect()
    try:
        row = connection.execute(
            """
            SELECT * FROM rerun_proposals
            WHERE create_idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        if row["create_request_hash"] != request_hash:
            raise RerunConflictError(
                "创建 Proposal 的幂等键已绑定其他请求"
            )
        proposal_id = str(row["proposal_id"])
    finally:
        connection.close()
    # 复用 get() 的 pending -> expired 原子投影。
    return self.get(proposal_id)
```

这样同一创建请求重放时，即使父 Run 后来已被 Retention 回收，也可以返回已创建 Proposal，而不需要
重新打开父 Artifact。

### 19.2 增加 API 响应 Schema

在 `app/rerun/schemas.py` 末尾增加：

```python
class RerunProposalMutationResponse(RerunModel):
    proposal: RerunProposalRecord
    replayed: bool


class RerunSubmissionResponse(RerunModel):
    proposal: RerunProposalRecord
    child_job_id: str
    job_created: bool
```

### 19.3 完整 RerunService

新增 `app/rerun/service.py`：

```python
# app/rerun/service.py
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from app.comparison.schemas import ComparisonReport
from app.execution.profile_store import get_execution_profile
from app.job_runtime.schemas import JobRecord, JobRequest
from app.job_runtime.service import JobService
from app.rerun.command_template import build_command_template
from app.rerun.errors import (
    RerunConflictError,
    RerunIntegrityError,
)
from app.rerun.identity import (
    proposal_hash,
    proposal_id_for_hash,
    sha256_value,
    validate_command_template_hash,
    validate_proposal_hash,
)
from app.rerun.repository import SqliteRerunRepository
from app.rerun.schemas import (
    DerivedRunInput,
    RerunProposal,
    RerunProposalCancelRequest,
    RerunProposalCreateRequest,
    RerunProposalRecord,
    RerunProposalSubmitRequest,
    RerunSourceIdentity,
)
from app.run_evidence.errors import (
    RunEvidenceConflictError,
    RunEvidenceIntegrityError,
    RunEvidenceLimitExceededError,
    RunEvidenceNotFoundError,
)
from app.run_evidence.reader import VerifiedRunEvidenceReader
from app.run_evidence.schemas import VerifiedRunEvidence
from app.workspace.capabilities import requirements_from_profile
from app.workspace.schemas import JobRequirements


class ComparisonReader(Protocol):
    def get(self, comparison_id: str) -> ComparisonReport:
        ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_key(value: str) -> str:
    key = value.strip()
    if not key or len(key) > 300:
        raise ValueError("Idempotency-Key 长度必须为 1..300")
    return key


def _expires_at(created_at: str, ttl_seconds: int) -> str:
    created = datetime.fromisoformat(created_at)
    if created.tzinfo is None:
        raise ValueError("clock 必须返回带 timezone 的 ISO 时间")
    return (created + timedelta(seconds=ttl_seconds)).isoformat()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _trusted_requirements(profile_id: str) -> JobRequirements:
    return requirements_from_profile(
        get_execution_profile(profile_id)
    )


class RerunService:
    def __init__(
        self,
        *,
        repository: SqliteRerunRepository,
        evidence_reader: VerifiedRunEvidenceReader,
        job_service: JobService,
        comparison_reader: ComparisonReader | None,
        proposal_ttl_seconds: int,
        max_command_chars: int,
        max_argv_items: int,
        max_edits: int,
        clock: Callable[[], str] = utc_now,
        requirements_resolver: Callable[
            [str], JobRequirements
        ] = _trusted_requirements,
    ) -> None:
        self.repository = repository
        self.evidence_reader = evidence_reader
        self.job_service = job_service
        self.comparison_reader = comparison_reader
        self.proposal_ttl_seconds = proposal_ttl_seconds
        self.max_command_chars = max_command_chars
        self.max_argv_items = max_argv_items
        self.max_edits = max_edits
        self.clock = clock
        self.requirements_resolver = requirements_resolver
        self.repository.initialize()

    def _read_evidence(self, job_id: str) -> VerifiedRunEvidence:
        try:
            return self.evidence_reader.read(job_id)
        except (
            RunEvidenceNotFoundError,
            RunEvidenceConflictError,
            RunEvidenceLimitExceededError,
        ) as exc:
            raise RerunConflictError(str(exc)) from exc
        except RunEvidenceIntegrityError as exc:
            raise RerunIntegrityError(
                "Parent Run evidence integrity validation failed"
            ) from exc

    def _verify_comparison(
        self,
        *,
        parent_job_id: str,
        comparison_id: str | None,
        expected_hash: str | None,
    ) -> None:
        if comparison_id is None:
            return
        if self.comparison_reader is None or expected_hash is None:
            raise RerunConflictError("Comparison reader 未配置")
        report = self.comparison_reader.get(comparison_id)
        if report.comparison_hash != expected_hash:
            raise RerunConflictError("Comparison hash 已变化")
        if parent_job_id not in {report.base.job_id, report.target.job_id}:
            raise RerunConflictError(
                "父 Job 不属于指定 Comparison"
            )

    @staticmethod
    def _source_identity(
        evidence: VerifiedRunEvidence,
    ) -> RerunSourceIdentity:
        job = evidence.job
        workspace = evidence.workspace
        artifact = evidence.run_manifest_artifact
        return RerunSourceIdentity(
            parent_job_id=job.job_id,
            parent_run_id=job.run_id,
            parent_workspace_manifest_id=workspace.manifest_id,
            parent_workspace_manifest_hash=workspace.manifest_hash,
            parent_workspace_generation=workspace.generation,
            parent_run_manifest_artifact_id=artifact.artifact_id,
            parent_run_manifest_sha256=artifact.sha256,
        )

    @staticmethod
    def _verify_source_against_proposal(
        *,
        evidence: VerifiedRunEvidence,
        proposal: RerunProposal,
    ) -> None:
        current = RerunService._source_identity(evidence)
        if current != proposal.source:
            raise RerunConflictError(
                "父 Run Evidence identity 已变化，Proposal 已 stale"
            )
        selected = evidence.run_manifest.get("selected_run_command")
        if not isinstance(selected, dict):
            raise RerunIntegrityError(
                "父 run_manifest 缺少 selected_run_command"
            )
        command = str(selected.get("command") or "")
        if _text_sha256(command) != proposal.command_template.parent_command_sha256:
            raise RerunIntegrityError(
                "父 selected command 与 Proposal identity 不一致"
            )

    def create_proposal(
        self,
        *,
        request: RerunProposalCreateRequest,
        idempotency_key: str,
    ) -> tuple[RerunProposalRecord, bool]:
        key = _required_key(idempotency_key)
        if len(request.edits) > self.max_edits:
            raise ValueError("Rerun edits 超过配置上限")
        request_hash = sha256_value(request.model_dump(mode="json"))

        replay = self.repository.find_create_replay(
            idempotency_key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay, False

        evidence = self._read_evidence(request.parent_job_id)
        if evidence.job.version != request.expected_parent_job_version:
            raise RerunConflictError(
                "父 Job version 与调用方预期不一致，请刷新页面"
            )
        if (
            evidence.run_manifest_artifact.sha256
            != request.expected_parent_run_manifest_sha256
        ):
            raise RerunConflictError(
                "父 run_manifest SHA 与调用方预期不一致，请刷新页面"
            )
        self._verify_comparison(
            parent_job_id=request.parent_job_id,
            comparison_id=request.comparison_id,
            expected_hash=request.expected_comparison_hash,
        )

        template = build_command_template(
            selected_action=evidence.run_manifest.get(
                "selected_run_command"
            ),
            run_manifest=evidence.run_manifest,
            workspace=evidence.workspace,
            edits=request.edits,
            max_command_chars=self.max_command_chars,
            max_argv_items=self.max_argv_items,
        )
        profile_id = (
            request.execution_profile_id
            or evidence.job.request.execution_profile_id
        )
        requirements = self.requirements_resolver(profile_id)
        created_at = self.clock()
        draft = RerunProposal(
            proposal_id="rerun_" + "0" * 24,
            proposal_hash="0" * 64,
            source=self._source_identity(evidence),
            comparison_id=request.comparison_id,
            comparison_hash=request.expected_comparison_hash,
            edits=request.edits,
            command_template=template,
            experiment_goal=(
                request.experiment_goal
                or evidence.job.request.experiment_goal
            ),
            execution_profile_id=profile_id,
            execution_policy_hash=requirements.execution_policy_hash,
            execution_backend=requirements.execution_backend,
            created_at=created_at,
            expires_at=_expires_at(
                created_at,
                self.proposal_ttl_seconds,
            ),
        )
        digest = proposal_hash(draft)
        proposal = draft.model_copy(
            update={
                "proposal_hash": digest,
                "proposal_id": proposal_id_for_hash(digest),
            }
        )
        return self.repository.create(
            proposal=proposal,
            idempotency_key=key,
            request_hash=request_hash,
        )

    def get_proposal(self, proposal_id: str) -> RerunProposalRecord:
        return self.repository.get(proposal_id)

    def cancel_proposal(
        self,
        *,
        proposal_id: str,
        request: RerunProposalCancelRequest,
    ) -> RerunProposalRecord:
        return self.repository.cancel(
            proposal_id=proposal_id,
            expected_hash=request.expected_proposal_hash,
            expected_version=request.expected_version,
            reason=request.reason,
        )

    def submit_proposal(
        self,
        *,
        proposal_id: str,
        request: RerunProposalSubmitRequest,
        idempotency_key: str,
    ) -> tuple[RerunProposalRecord, JobRecord, bool]:
        operation_key = _required_key(idempotency_key)
        record = self.repository.begin_submission(
            proposal_id=proposal_id,
            expected_hash=request.expected_proposal_hash,
            expected_version=request.expected_version,
            submit_idempotency_key=operation_key,
        )
        if record.status == "submitted":
            if record.child_job_id is None:
                raise RerunIntegrityError(
                    "submitted Proposal 缺少 child_job_id"
                )
            return record, self.job_service.get(record.child_job_id), False

        proposal = record.proposal
        validate_proposal_hash(proposal)
        validate_command_template_hash(proposal.command_template)

        try:
            # 提交前再次打开父证据，而不是只相信创建 Proposal 时的内存对象。
            evidence = self._read_evidence(
                proposal.source.parent_job_id
            )
            self._verify_source_against_proposal(
                evidence=evidence,
                proposal=proposal,
            )
            self._verify_comparison(
                parent_job_id=proposal.source.parent_job_id,
                comparison_id=proposal.comparison_id,
                expected_hash=proposal.comparison_hash,
            )
            current_requirements = self.requirements_resolver(
                proposal.execution_profile_id
            )
            if (
                current_requirements.execution_policy_hash
                != proposal.execution_policy_hash
                or current_requirements.execution_backend
                != proposal.execution_backend
            ):
                raise RerunConflictError(
                    "Execution Profile policy 已变化，Proposal 已 stale"
                )

            child, created = self.job_service.submit(
                request=JobRequest(
                    derived_run=DerivedRunInput(
                        proposal_id=proposal.proposal_id,
                        proposal_hash=proposal.proposal_hash,
                        source=proposal.source,
                        command_template=proposal.command_template,
                    ),
                    experiment_goal=proposal.experiment_goal,
                    execution_profile_id=proposal.execution_profile_id,
                    dataset_refs=[
                        item.model_copy(deep=True)
                        for item in evidence.workspace.external_data
                    ],
                ),
                thread_id=f"rerun-{proposal.proposal_id}",
                # 跨 Rerun DB 与 Job DB 的 exactly-once 锚点。
                idempotency_key=f"rerun-submit:{proposal.proposal_id}",
            )
        except Exception as exc:
            self.repository.record_submission_error(
                proposal_id=proposal_id,
                submit_idempotency_key=operation_key,
                detail=f"{type(exc).__name__}: {exc}",
            )
            raise

        completed = self.repository.complete_submission(
            proposal_id=proposal_id,
            submit_idempotency_key=operation_key,
            child_job_id=child.job_id,
        )
        return completed, child, created
```

`record_submission_error()` 只保存有界错误摘要，不保存 traceback、命令正文或 secret。详细内部错误继续进入
服务日志和 Trace。

### 19.4 一个已知但受控的边界

如果发生极端序列：

```text
Job Store 已提交成功
-> Rerun DB 尚未 complete
-> 进程崩溃
-> 管理员随后修改了同名 Execution Profile 的 policy
-> 再重试
```

Job Store 可能因同幂等键但 `requirements` 变化而返回 conflict。此时不能猜测，应保留 `submitting` 并由
运维查询该幂等键对应的 Job。后续可给 `JobStore` 增加只读 `find_by_idempotency_key()` 进一步自动消歧，
但第一版不要为了极低概率窗口引入跨后端大改。

---

## 二十、组装 Factory

> **本节类型：需要新增代码。**
>
> 需要新增：`app/rerun/factory.py`。

```python
# app/rerun/factory.py
from __future__ import annotations

from app.comparison.factory import (
    build_comparison_service,
    build_run_evidence_reader,
)
from app.config import settings
from app.interaction.artifacts import ArtifactCatalog
from app.job_runtime.service import JobService
from app.rerun.repository import SqliteRerunRepository
from app.rerun.service import RerunService


def build_rerun_service(
    *,
    job_service: JobService,
    artifact_catalog: ArtifactCatalog,
    comparison_service=None,
) -> RerunService:
    reader = build_run_evidence_reader(
        jobs=job_service.store,
        artifact_catalog=artifact_catalog,
    )
    selected_comparison = (
        comparison_service
        if comparison_service is not None
        else build_comparison_service(
            jobs=job_service.store,
            artifact_catalog=artifact_catalog,
            evidence_reader=reader,
        )
    )
    return RerunService(
        repository=SqliteRerunRepository(settings.rerun_db_path),
        evidence_reader=reader,
        job_service=job_service,
        comparison_reader=selected_comparison,
        proposal_ttl_seconds=settings.rerun_proposal_ttl_seconds,
        max_command_chars=settings.rerun_max_command_chars,
        max_argv_items=settings.rerun_max_argv_items,
        max_edits=settings.rerun_max_edits,
    )
```

Web App 组装时应构造一次 Reader 并同时注入 Comparison 与 Rerun，避免同一进程创建两套配置不同的
可信读取器。上面的 Factory 保留独立 CLI 使用时的便利分支。

---

## 二十一、增加 HTTP API

> **本节类型：需要新增并修改代码。**
>
> 需要新增：`app/api/rerun_routes.py`。
>
> 需要修改：`app/api/app.py`、`app/api/errors.py`。

### 21.1 完整 Route

新增 `app/api/rerun_routes.py`：

```python
# app/api/rerun_routes.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.api.auth import require_api_auth
from app.rerun.schemas import (
    RerunProposalCancelRequest,
    RerunProposalCreateRequest,
    RerunProposalMutationResponse,
    RerunProposalRecord,
    RerunProposalSubmitRequest,
    RerunSubmissionResponse,
)
from app.rerun.service import RerunService

router = APIRouter(prefix="/v1")

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=300,
    ),
]
Actor = Annotated[str, Depends(require_api_auth)]


def rerun_service(request: Request) -> RerunService:
    return request.app.state.rerun_service


RerunDependency = Annotated[
    RerunService,
    Depends(rerun_service),
]


@router.post(
    "/rerun-proposals",
    response_model=RerunProposalMutationResponse,
)
def create_rerun_proposal(
    body: RerunProposalCreateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: RerunDependency,
) -> RerunProposalMutationResponse:
    del actor
    record, created = service.create_proposal(
        request=body,
        idempotency_key=idempotency_key,
    )
    return RerunProposalMutationResponse(
        proposal=record,
        replayed=not created,
    )


@router.get(
    "/rerun-proposals/{proposal_id}",
    response_model=RerunProposalRecord,
)
def get_rerun_proposal(
    proposal_id: str,
    actor: Actor,
    service: RerunDependency,
) -> RerunProposalRecord:
    del actor
    return service.get_proposal(proposal_id)


@router.post(
    "/rerun-proposals/{proposal_id}/submit",
    response_model=RerunSubmissionResponse,
)
def submit_rerun_proposal(
    proposal_id: str,
    body: RerunProposalSubmitRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: RerunDependency,
) -> RerunSubmissionResponse:
    del actor
    record, job, created = service.submit_proposal(
        proposal_id=proposal_id,
        request=body,
        idempotency_key=idempotency_key,
    )
    return RerunSubmissionResponse(
        proposal=record,
        child_job_id=job.job_id,
        job_created=created,
    )


@router.post(
    "/rerun-proposals/{proposal_id}/cancel",
    response_model=RerunProposalRecord,
)
def cancel_rerun_proposal(
    proposal_id: str,
    body: RerunProposalCancelRequest,
    actor: Actor,
    service: RerunDependency,
) -> RerunProposalRecord:
    del actor
    return service.cancel_proposal(
        proposal_id=proposal_id,
        request=body,
    )
```

### 21.2 App 组装

在 `app/api/app.py` 增加：

```python
from app.api.rerun_routes import router as rerun_router
from app.rerun.factory import build_rerun_service
from app.rerun.service import RerunService
```

给 `create_api_app()` 增加可测试注入参数：

```python
rerun_service: RerunService | None = None,
```

在 Comparison Service 已构造后增加：

```python
selected_rerun_service = (
    rerun_service
    if rerun_service is not None
    else build_rerun_service(
        job_service=selected_job_service,
        artifact_catalog=selected_catalog,
        comparison_service=selected_comparison_service,
    )
)
app.state.rerun_service = selected_rerun_service
```

其中 `selected_job_service` 请替换为该函数中实际保存的 JobService 局部变量名，不要重复调用
`build_job_service()`。

在 readiness probe 列表增加：

```python
ReadinessProbe(
    name="rerun_repository_readiness",
    is_critical=True,
    check=lambda: (
        "ready"
        if selected_rerun_service.repository.ping()
        else "not_ready"
    ),
    timeout_seconds=settings.readiness_timeout_seconds,
),
```

最后注册：

```python
app.include_router(rerun_router)
```

### 21.3 稳定错误映射

在 `app/api/errors.py` import：

```python
from app.rerun.errors import (
    RerunCommandRejectedError,
    RerunConflictError,
    RerunExpiredError,
    RerunIntegrityError,
    RerunNotFoundError,
)
```

在 `install_error_handlers()` 内按现有 `_response()` 风格注册：

```python
@app.exception_handler(RerunNotFoundError)
async def rerun_not_found_handler(request, exc):
    return _response(
        request,
        status_code=404,
        code="RERUN_PROPOSAL_NOT_FOUND",
        message=str(exc),
    )


@app.exception_handler(RerunExpiredError)
async def rerun_expired_handler(request, exc):
    return _response(
        request,
        status_code=409,
        code="RERUN_PROPOSAL_EXPIRED",
        message=str(exc),
    )


@app.exception_handler(RerunConflictError)
async def rerun_conflict_handler(request, exc):
    return _response(
        request,
        status_code=409,
        code="RERUN_CONFLICT",
        message=str(exc),
    )


@app.exception_handler(RerunCommandRejectedError)
async def rerun_command_rejected_handler(request, exc):
    return _response(
        request,
        status_code=422,
        code="RERUN_COMMAND_REJECTED",
        message=str(exc),
    )


@app.exception_handler(RerunIntegrityError)
async def rerun_integrity_handler(request, exc):
    return _response(
        request,
        status_code=500,
        code="RERUN_INTEGRITY_ERROR",
        message="Rerun evidence integrity validation failed",
    )
```

Integrity 响应不要把内部 object key、路径或原始命令返回给客户端。

---

## 二十二、公开 Job View 与 Allowed Operation 接线

> **本节类型：需要修改代码。**
>
> 需要修改：`app/interaction/schemas.py`、`app/interaction/service.py`、`app/interaction/policy.py`。

### 22.1 增加操作类型与派生来源摘要

修改 `app/interaction/schemas.py`：

```python
OperationKind = Literal[
    "submit_decision",
    "cancel",
    "operator_reconciliation_required",
    "create_rerun_proposal",
]


class PublicJobInput(InteractionModel):
    paper_name: str
    repo_name: str
    experiment_goal: str
    execution_profile_id: str
    derived_from_job_id: str | None = None
```

### 22.2 安全投影 derived Job

在 `app/interaction/service.py` 增加：

```python
def _public_job_input(record: JobRecord) -> PublicJobInput:
    derived = record.request.derived_run
    if derived is not None:
        parent = derived.source.parent_job_id
        return PublicJobInput(
            paper_name="derived:parent-paper",
            repo_name="derived:parent-repository",
            experiment_goal=record.request.experiment_goal,
            execution_profile_id=record.request.execution_profile_id,
            derived_from_job_id=parent,
        )
    return PublicJobInput(
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
    )
```

然后在 `project_job()` 中将原内联 `PublicJobInput(...)` 替换为：

```python
input=_public_job_input(record),
```

不要公开 `proposal.command_template` 或父绝对路径。Proposal 有独立 API，Job View 只说明 lineage。

### 22.3 给终态 Job 声明可创建 Proposal

在 `allowed_operations()` 末尾增加：

```python
if record.status in {"succeeded", "failed"}:
    operations.append(
        AllowedOperation(
            operation_id=f"rerun-proposal:{record.version}",
            kind="create_rerun_proposal",
            endpoint="/v1/rerun-proposals",
            expected_job_version=record.version,
            requires_idempotency_key=True,
            detail=(
                "可基于该终态 Run 的已验证 selected command 创建重跑提案；"
                "新 Job 仍需重新审批。"
            ),
        )
    )
```

取消态 Job 不声明该能力，因为它不一定生成完整 `run_manifest.json`。即使 succeeded/failed Job 因历史原因
缺少 Manifest，RerunService 仍会 fail closed。

---

## 二十三、增加 CLI

> **本节类型：需要修改代码。**
>
> 需要修改：`app/main.py`。

CLI 使用 JSON 文件传 edits，避免复杂参数被 Shell 二次解释。先在 import 区增加：

```python
from app.comparison.service import build_command_snapshot
from app.rerun.factory import build_rerun_service
from app.rerun.schemas import (
    RerunArgumentEdit,
    RerunProposalCancelRequest,
    RerunProposalCreateRequest,
    RerunProposalSubmitRequest,
)
```

增加一个内部组装函数：

```python
def _build_cli_rerun_service():
    job_service = build_job_service()
    storage = build_artifact_storage()
    comparison = build_comparison_service(
        jobs=job_service.store,
        artifact_catalog=storage.catalog,
    )
    return build_rerun_service(
        job_service=job_service,
        artifact_catalog=storage.catalog,
        comparison_service=comparison,
    )
```

### 23.1 查看可派生来源

```python
@app.command("inspect-rerun-source")
def inspect_rerun_source_command(
    parent_job_id: str = typer.Argument(...),
) -> None:
    """显示创建 Proposal 需要的 SHA 和脱敏命令摘要。"""

    service = _build_cli_rerun_service()
    evidence = service.evidence_reader.read(parent_job_id)
    snapshot = build_command_snapshot(
        evidence.run_manifest.get("selected_run_command")
    )
    print(
        {
            "parent_job_id": evidence.job.job_id,
            "parent_run_id": evidence.job.run_id,
            "parent_job_version": evidence.job.version,
            "run_manifest_sha256": (
                evidence.run_manifest_artifact.sha256
            ),
            "workspace_manifest_hash": evidence.workspace.manifest_hash,
            "selected_command_display": snapshot.display,
            "selected_command_sha256": snapshot.command_sha256,
            "execution_profile_id": (
                evidence.job.request.execution_profile_id
            ),
            "dataset_labels": [
                item.required_worker_label
                for item in evidence.workspace.external_data
            ],
        }
    )
```

这里打印的是 Phase 38 脱敏投影，不打印 secret 或完整绝对路径。

### 23.2 创建 Proposal

```python
@app.command("create-rerun-proposal")
def create_rerun_proposal_command(
    parent_job_id: str = typer.Argument(...),
    expected_manifest_sha: str = typer.Option(
        ...,
        "--expected-manifest-sha",
    ),
    expected_job_version: int = typer.Option(
        ...,
        "--expected-job-version",
        min=0,
    ),
    edits_file: Path = typer.Option(
        ...,
        "--edits-file",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    idempotency_key: str = typer.Option(
        ...,
        "--idempotency-key",
    ),
    experiment_goal: str | None = typer.Option(
        None,
        "--experiment-goal",
    ),
    execution_profile_id: str | None = typer.Option(
        None,
        "--execution-profile-id",
    ),
    comparison_id: str | None = typer.Option(None, "--comparison-id"),
    comparison_hash: str | None = typer.Option(None, "--comparison-hash"),
) -> None:
    raw = json.loads(edits_file.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise typer.BadParameter("edits-file 顶层必须是 JSON array")
    edits = [RerunArgumentEdit.model_validate(item) for item in raw]

    service = _build_cli_rerun_service()
    record, created = service.create_proposal(
        request=RerunProposalCreateRequest(
            parent_job_id=parent_job_id,
            expected_parent_job_version=expected_job_version,
            expected_parent_run_manifest_sha256=expected_manifest_sha,
            edits=edits,
            experiment_goal=experiment_goal,
            execution_profile_id=execution_profile_id,
            comparison_id=comparison_id,
            expected_comparison_hash=comparison_hash,
        ),
        idempotency_key=idempotency_key,
    )
    print(
        {
            "proposal_id": record.proposal.proposal_id,
            "proposal_hash": record.proposal.proposal_hash,
            "status": record.status,
            "version": record.version,
            "created": created,
            "expires_at": record.proposal.expires_at,
        }
    )
```

### 23.3 查看、提交与取消

```python
@app.command("show-rerun-proposal")
def show_rerun_proposal_command(
    proposal_id: str = typer.Argument(...),
) -> None:
    service = _build_cli_rerun_service()
    record = service.get_proposal(proposal_id)
    print(record.model_dump(mode="json"))


@app.command("submit-rerun-proposal")
def submit_rerun_proposal_command(
    proposal_id: str = typer.Argument(...),
    expected_hash: str = typer.Option(..., "--expected-hash"),
    expected_version: int = typer.Option(..., "--expected-version", min=0),
    idempotency_key: str = typer.Option(..., "--idempotency-key"),
) -> None:
    service = _build_cli_rerun_service()
    record, child, created = service.submit_proposal(
        proposal_id=proposal_id,
        request=RerunProposalSubmitRequest(
            expected_proposal_hash=expected_hash,
            expected_version=expected_version,
        ),
        idempotency_key=idempotency_key,
    )
    print(
        {
            "proposal_id": record.proposal.proposal_id,
            "proposal_status": record.status,
            "proposal_version": record.version,
            "child_job_id": child.job_id,
            "child_thread_id": child.thread_id,
            "child_status": child.status,
            "job_created": created,
        }
    )


@app.command("cancel-rerun-proposal")
def cancel_rerun_proposal_command(
    proposal_id: str = typer.Argument(...),
    expected_hash: str = typer.Option(..., "--expected-hash"),
    expected_version: int = typer.Option(..., "--expected-version", min=0),
    reason: str = typer.Option("user cancelled", "--reason"),
) -> None:
    service = _build_cli_rerun_service()
    record = service.cancel_proposal(
        proposal_id=proposal_id,
        request=RerunProposalCancelRequest(
            expected_proposal_hash=expected_hash,
            expected_version=expected_version,
            reason=reason,
        ),
    )
    print(record.model_dump(mode="json"))
```

`app/main.py` 已有 `json` 和 `Path` 时不要重复 import；以当前文件为准整理。

---

## 二十四、Retention 与引用安全

> **本节类型：需要修改少量代码并验证已有能力。**
>
> 需要修改：`app/retention/factory.py`。

### 24.1 只做容量盘点

在 `build_inventory()` 的 SQLite 根列表增加：

```python
("rerun_db", settings.rerun_db_path.resolve()),
```

`_sqlite_roots()` 会同时统计：

```text
rerun.sqlite
rerun.sqlite-wal
rerun.sqlite-shm
```

Phase 39 不把 Proposal 接入删除协议。父 Job 被 GC 后，历史 Proposal 仍可作为审计记录读取，但再次提交时
会因父 Evidence 不存在而 fail closed。

### 24.2 验证共享 Blob 不会被父 Job GC 误删

当前 `RetentionService._live_blob_references()` 已同时统计：

```text
Artifact Catalog references
+ Workspace Manifest references
+ Resource references
```

子 Manifest 复用了父 paper/repository object key，因此删除父 Job 时，子 Manifest 的引用计数仍大于零，
Blob 不应被删除。必须增加回归测试：

```text
创建 parent manifest
派生 child manifest
删除 parent Job 的控制面和 Blob 候选
count_workspace_blob_references(object_key) 仍为 1
GC 结果 retained_shared_blob_count 增加
child materialize 仍成功
```

不要为了 lineage 增加“父 Job 永远不能删除”的粗粒度规则。真正需要保留的是子 Manifest 引用的内容，
不是父 Job 的全部过程数据。

---

## 二十五、命令模板单元测试

> **本节类型：需要新增测试代码。**
>
> 需要新增：`tests/test_rerun_command_template.py`。

新增完整文件：

```python
# tests/test_rerun_command_template.py
from __future__ import annotations

import shlex

import pytest

from app.rerun.command_template import (
    build_command_template,
    resolve_command_template,
)
from app.rerun.errors import (
    RerunCommandRejectedError,
    RerunConflictError,
)
from app.rerun.schemas import RerunArgumentEdit
from app.workspace.schemas import (
    ExternalDataReference,
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)


def _workspace() -> WorkspaceManifest:
    return WorkspaceManifest(
        manifest_version="phase39-v2",
        manifest_id="wm-parent",
        manifest_hash="a" * 64,
        job_id="job-parent",
        run_id="run-parent",
        generation=2,
        source_host_id="host-a",
        entries=[
            WorkspaceBlobEntry(
                logical_path="source/paper.pdf",
                role="paper",
                object_key="workspace/paper",
                sha256="b" * 64,
                size_bytes=10,
            ),
            WorkspaceBlobEntry(
                logical_path="capsule/repository.bundle",
                role="repository_bundle",
                object_key="workspace/repository",
                sha256="c" * 64,
                size_bytes=20,
            ),
        ],
        repository=RepositoryIdentity(
            commit_sha="d" * 40,
            branch="main",
            clean=True,
            bundle_logical_path="capsule/repository.bundle",
        ),
        external_data=[
            ExternalDataReference(
                name="NTU60",
                uri="file:///datasets/ntu60",
                fingerprint="ntu60-v1",
                required_worker_label="dataset:ntu60",
            )
        ],
        portable=False,
        blocked_reasons=["blob_store_is_host_local"],
        source_paths=None,
        materialization_mode="blob_entries",
        created_at="2026-08-09T00:00:00+00:00",
    )


def _build(command: str, edits: list[RerunArgumentEdit]):
    return build_command_template(
        selected_action={
            "command": command,
            "cwd": "/parent/repository/modules",
            "source": "readme",
            "risk_level": "high",
        },
        run_manifest={
            "repo_path": "/parent/repository",
            "run_dir": "/parent/run",
        },
        workspace=_workspace(),
        edits=edits,
        max_command_chars=8192,
        max_argv_items=256,
    )


def test_build_and_resolve_template_changes_only_expected_option(
    tmp_path,
) -> None:
    template = _build(
        (
            "python /parent/repository/train.py "
            "--dataset=/datasets/ntu60/train "
            "--output /parent/run/results "
            "--epochs 50 --batch-size=8"
        ),
        [
            RerunArgumentEdit(
                option="--epochs",
                operation="set",
                expected_old_value="50",
                value="100",
            )
        ],
    )
    repo = tmp_path / "child-repository"
    child_run = tmp_path / "child-run"
    dataset = tmp_path / "datasets" / "ntu60"
    repo.mkdir()
    child_run.mkdir()
    dataset.mkdir(parents=True)

    resolved = resolve_command_template(
        template=template,
        repo_path=str(repo),
        run_dir=str(child_run),
        dataset_mounts={"dataset:ntu60": str(dataset)},
    )
    argv = shlex.split(resolved["command"])
    assert argv == [
        "python",
        str(repo / "train.py"),
        "--dataset",
        str(dataset / "train"),
        "--output",
        str(child_run / "results"),
        "--epochs",
        "100",
        "--batch-size",
        "8",
    ]
    assert resolved["cwd"] == str(repo / "modules")
    assert resolved["source"] == "config"
    assert resolved["risk_level"] == "high"


def test_remove_existing_flag() -> None:
    template = _build(
        "python train.py --amp --epochs 50",
        [
            RerunArgumentEdit(
                option="--amp",
                operation="remove",
                expected_old_value=None,
            )
        ],
    )
    literal_values = [
        item.value
        for item in template.argv
        if item.kind == "literal"
    ]
    assert "--amp" not in literal_values


@pytest.mark.parametrize(
    "command",
    [
        "python train.py | tee output.log --epochs 50",
        "python train.py > output.log --epochs 50",
        "TOKEN=secret python train.py --epochs 50",
        "python train.py --token secret --epochs 50",
        "python /unrelated/train.py --epochs 50",
    ],
)
def test_rejects_unsafe_parent_command(command: str) -> None:
    with pytest.raises(RerunCommandRejectedError):
        _build(
            command,
            [
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="50",
                    value="100",
                )
            ],
        )


def test_rejects_stale_expected_old_value() -> None:
    with pytest.raises(RerunConflictError, match="expected_old_value"):
        _build(
            "python train.py --epochs 50",
            [
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="40",
                    value="100",
                )
            ],
        )


def test_rejects_new_absolute_path() -> None:
    with pytest.raises(RerunCommandRejectedError):
        _build(
            "python train.py --output old --epochs 50",
            [
                RerunArgumentEdit(
                    option="--output",
                    operation="set",
                    expected_old_value="old",
                    value="/host/private/output",
                )
            ],
        )
```

---

## 二十六、Proposal Repository 单元测试

> **本节类型：需要新增测试代码。**
>
> 需要新增：`tests/test_rerun_repository.py`。

新增完整文件：

```python
# tests/test_rerun_repository.py
from __future__ import annotations

import pytest

from app.rerun.errors import RerunConflictError
from app.rerun.identity import (
    command_template_hash,
    proposal_hash,
    proposal_id_for_hash,
)
from app.rerun.repository import SqliteRerunRepository
from app.rerun.schemas import (
    RerunArgumentEdit,
    RerunCommandTemplate,
    RerunProposal,
    RerunSourceIdentity,
    RerunTemplateArg,
)


def _proposal() -> RerunProposal:
    template_draft = RerunCommandTemplate(
        argv=[
            RerunTemplateArg(kind="literal", value="python"),
            RerunTemplateArg(kind="literal", value="train.py"),
            RerunTemplateArg(kind="literal", value="--epochs"),
            RerunTemplateArg(kind="literal", value="100"),
        ],
        cwd_relative=".",
        reason="test rerun",
        parent_command_sha256="a" * 64,
        template_hash="0" * 64,
    )
    template = template_draft.model_copy(
        update={"template_hash": command_template_hash(template_draft)}
    )
    draft = RerunProposal(
        proposal_id="rerun_" + "0" * 24,
        proposal_hash="0" * 64,
        source=RerunSourceIdentity(
            parent_job_id="job-parent",
            parent_run_id="run-parent",
            parent_workspace_manifest_id="wm-parent",
            parent_workspace_manifest_hash="b" * 64,
            parent_workspace_generation=2,
            parent_run_manifest_artifact_id="artifact-manifest",
            parent_run_manifest_sha256="c" * 64,
        ),
        edits=[
            RerunArgumentEdit(
                option="--epochs",
                operation="set",
                expected_old_value="50",
                value="100",
            )
        ],
        command_template=template,
        experiment_goal="rerun test",
        execution_profile_id="cpu-local",
        execution_policy_hash="e" * 64,
        execution_backend="local",
        created_at="2026-08-09T00:00:00+00:00",
        expires_at="2026-08-10T00:00:00+00:00",
    )
    digest = proposal_hash(draft)
    return draft.model_copy(
        update={
            "proposal_hash": digest,
            "proposal_id": proposal_id_for_hash(digest),
        }
    )


def _repository(tmp_path) -> SqliteRerunRepository:
    repository = SqliteRerunRepository(
        tmp_path / "rerun.sqlite",
        clock=lambda: "2026-08-09T01:00:00+00:00",
    )
    repository.initialize()
    return repository


def test_create_is_idempotent(tmp_path) -> None:
    repository = _repository(tmp_path)
    proposal = _proposal()
    first, first_created = repository.create(
        proposal=proposal,
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    second, second_created = repository.create(
        proposal=proposal,
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    assert first_created is True
    assert second_created is False
    assert first.proposal.proposal_id == second.proposal.proposal_id


def test_same_create_key_with_different_request_conflicts(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.create(
        proposal=_proposal(),
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    with pytest.raises(RerunConflictError):
        repository.find_create_replay(
            idempotency_key="create-1",
            request_hash="e" * 64,
        )


def test_submission_recovery_reuses_same_ownership(tmp_path) -> None:
    repository = _repository(tmp_path)
    pending, _ = repository.create(
        proposal=_proposal(),
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    submitting = repository.begin_submission(
        proposal_id=pending.proposal.proposal_id,
        expected_hash=pending.proposal.proposal_hash,
        expected_version=pending.version,
        submit_idempotency_key="submit-operation-1",
    )
    assert submitting.status == "submitting"

    # 模拟 Job 创建后、complete 前崩溃：同 operation key 可恢复。
    replay = repository.begin_submission(
        proposal_id=pending.proposal.proposal_id,
        expected_hash=pending.proposal.proposal_hash,
        expected_version=pending.version,
        submit_idempotency_key="submit-operation-1",
    )
    assert replay.status == "submitting"

    with pytest.raises(RerunConflictError):
        repository.begin_submission(
            proposal_id=pending.proposal.proposal_id,
            expected_hash=pending.proposal.proposal_hash,
            expected_version=pending.version,
            submit_idempotency_key="submit-operation-2",
        )

    completed = repository.complete_submission(
        proposal_id=pending.proposal.proposal_id,
        submit_idempotency_key="submit-operation-1",
        child_job_id="job-child",
    )
    assert completed.status == "submitted"
    assert completed.child_job_id == "job-child"


def test_only_pending_proposal_can_be_cancelled(tmp_path) -> None:
    repository = _repository(tmp_path)
    pending, _ = repository.create(
        proposal=_proposal(),
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    cancelled = repository.cancel(
        proposal_id=pending.proposal.proposal_id,
        expected_hash=pending.proposal.proposal_hash,
        expected_version=pending.version,
        reason="not needed",
    )
    assert cancelled.status == "cancelled"
```

再增加过期测试，使用一个可变 clock，让 `get()` 在 `expires_at` 之后将状态原子更新为 `expired`，并确认
`begin_submission()` 抛出 `RerunExpiredError`。

---

## 二十七、Workspace 派生与历史 Hash 测试

> **本节类型：需要新增测试代码。**
>
> 需要新增：`tests/test_immutable_workspace_derivation.py`。

核心测试代码：

```python
# tests/test_immutable_workspace_derivation.py
from __future__ import annotations

import hashlib

import pytest

from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.repository import (
    canonical_json_bytes,
    validate_manifest_hash,
    workspace_manifest_hash,
)
from app.workspace.schemas import (
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
    WorkspaceSourcePaths,
)
from app.workspace.snapshot import WorkspaceSnapshotter


class FakeLocalBlobStore:
    sharing_scope = "host-local"

    def ensure_ready(self) -> None:
        return None


def _entries() -> list[WorkspaceBlobEntry]:
    return [
        WorkspaceBlobEntry(
            logical_path="source/paper.pdf",
            role="paper",
            object_key="workspace/paper",
            sha256="a" * 64,
            size_bytes=10,
        ),
        WorkspaceBlobEntry(
            logical_path="capsule/repository.bundle",
            role="repository_bundle",
            object_key="workspace/repository",
            sha256="b" * 64,
            size_bytes=20,
        ),
        WorkspaceBlobEntry(
            logical_path="run/reports/final_report.md",
            role="run_artifact",
            object_key="workspace/report",
            sha256="c" * 64,
            size_bytes=30,
        ),
    ]


def _parent() -> WorkspaceManifest:
    draft = WorkspaceManifest(
        manifest_version="phase39-v2",
        manifest_id="wm-pending",
        manifest_hash="0" * 64,
        job_id="job-parent",
        run_id="run-parent",
        generation=2,
        source_host_id="host-a",
        entries=_entries(),
        repository=RepositoryIdentity(
            commit_sha="d" * 40,
            branch="main",
            clean=True,
            bundle_logical_path="capsule/repository.bundle",
        ),
        portable=False,
        blocked_reasons=["blob_store_is_host_local"],
        source_paths=WorkspaceSourcePaths(
            run_dir="/old/run",
            repo_path="/old/repo",
            paper_path="/old/paper.pdf",
        ),
        materialization_mode="auto",
        created_at="2026-08-09T00:00:00+00:00",
    )
    digest = workspace_manifest_hash(draft)
    return draft.model_copy(
        update={
            "manifest_id": f"wm_{digest[:32]}",
            "manifest_hash": digest,
        }
    )


def test_derive_reuses_only_immutable_input_entries() -> None:
    snapshotter = WorkspaceSnapshotter(
        blob_store=FakeLocalBlobStore()
    )
    parent = _parent()
    child = snapshotter.derive_initial(
        job_id="job-child",
        run_id="run-child",
        parent=parent,
        source_host_id="host-a",
        external_data=[],
    )
    validate_manifest_hash(child)
    assert child.generation == 0
    assert child.parent_manifest_id == parent.manifest_id
    assert child.materialization_mode == "blob_entries"
    assert child.portable is False
    assert child.source_paths is None
    assert {item.role for item in child.entries} == {
        "paper",
        "repository_bundle",
    }
    assert {item.object_key for item in child.entries} == {
        "workspace/paper",
        "workspace/repository",
    }


def test_phase26_hash_ignores_new_default_field() -> None:
    payload = {
        "manifest_version": "phase26-v1",
        "manifest_id": "wm-old",
        "manifest_hash": "",
        "job_id": "job-old",
        "run_id": "run-old",
        "generation": 0,
        "parent_manifest_id": None,
        "source_host_id": "host-a",
        "source_worker_session_id": None,
        "entries": [item.model_dump(mode="json") for item in _entries()[:2]],
        "repository": {
            "commit_sha": "d" * 40,
            "branch": "main",
            "clean": True,
            "bundle_logical_path": "capsule/repository.bundle",
            "has_submodules": False,
            "has_lfs": False,
        },
        "external_data": [],
        "portable": False,
        "blocked_reasons": ["blob_store_is_host_local"],
        "source_paths": {
            "run_dir": None,
            "repo_path": "/old/repo",
            "paper_path": "/old/paper.pdf",
            "log_path": None,
        },
        "created_at": "2026-08-01T00:00:00+00:00",
    }
    historical = dict(payload)
    historical.pop("manifest_hash")
    historical.pop("manifest_id")
    historical.pop("created_at")
    digest = hashlib.sha256(
        canonical_json_bytes(historical)
    ).hexdigest()
    payload["manifest_hash"] = digest

    loaded = WorkspaceManifest.model_validate(payload)
    assert loaded.materialization_mode == "auto"
    validate_manifest_hash(loaded)


def test_phase39_hash_binds_materialization_mode() -> None:
    parent = _parent()
    changed = parent.model_copy(
        update={"materialization_mode": "host_paths"}
    )
    with pytest.raises(WorkspaceIntegrityError, match="hash"):
        validate_manifest_hash(changed)
```

`FakeLocalBlobStore` 只覆盖本测试调用到的接口；若静态类型检查要求完整 Protocol，可以继承项目内的
测试 Fake 或补齐 `put_file/open/delete_if_matches`，但不要在测试里访问真实 Artifact Store。

---

## 二十八、Rerun Seed 与 Graph 回归测试

> **本节类型：需要新增测试代码。**
>
> 需要新增：`tests/test_rerun_seed_node.py`。

```python
# tests/test_rerun_seed_node.py
from __future__ import annotations

from app.config import settings
from app.nodes.rerun_seed_node import rerun_seed_node


def test_normal_job_is_noop() -> None:
    assert rerun_seed_node({}) == {}


def test_rerun_seed_overrides_commands_and_clears_approval(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "runs_dir", tmp_path)
    run_dir = tmp_path / "run-child"
    state = {
        "run_id": "run-child",
        "run_dir": str(run_dir),
        "artifact_records": [],
        "output_files": [],
        "run_commands": [
            {
                "command": "python wrong.py",
                "cwd": "/wrong",
                "source": "inferred",
                "risk_level": "low",
                "reason": "LLM candidate",
            }
        ],
        "pending_action": {"command": "old"},
        "pending_action_hash": "a" * 64,
        "user_approval": "approved",
        "approval_record": {"decision": "approved"},
        "rerun_seed": {
            "proposal_id": "rerun_" + "1" * 24,
            "proposal_hash": "2" * 64,
            "source": {"parent_job_id": "job-parent"},
            "template_hash": "3" * 64,
            "run_command": {
                "command": "python train.py --epochs 100",
                "cwd": str(tmp_path / "repo"),
                "source": "config",
                "risk_level": "high",
                "reason": "trusted rerun seed",
            },
        },
    }
    update = rerun_seed_node(state)
    assert update["run_commands"][0]["command"].endswith("--epochs 100")
    assert update["pending_action"] is None
    assert update["pending_action_hash"] is None
    assert update["user_approval"] is None
    assert update["approval_record"] is None
    assert update["requires_approval"] is False
    assert update["rerun_seed_path"].endswith("planning/rerun_seed.json")
    assert len(update["artifact_records"]) == 1
```

再在现有 Graph topology 测试中增加断言：

```text
experiment_plan -> rerun_seed
rerun_seed -> command_selection_prepare
不存在 rerun_seed -> executor
不存在 rerun_seed -> preflight_check
```

并保留所有普通 Job Graph 测试，确认插入 no-op 节点没有改变旧路由。

---

## 二十九、Service、Evidence Reader 与 API 测试

> **本节类型：需要新增并修改测试代码。**
>
> 需要新增：`tests/test_verified_run_evidence_reader.py`、`tests/test_rerun_service.py`、
> `tests/test_rerun_api.py`。
>
> 需要修改：`tests/test_comparison_service.py` 及其他直接构造 `ComparisonService` 的测试。

### 29.1 先修 Phase 38 Constructor

将 Phase 38 测试中：

```python
ComparisonService(
    jobs=jobs,
    artifact_catalog=catalog,
    repository=repository,
    max_manifest_bytes=1024 * 1024,
    max_artifacts=100,
    max_changes=100,
)
```

改为：

```python
reader = VerifiedRunEvidenceReader(
    jobs=jobs,
    artifact_catalog=catalog,
    max_manifest_bytes=1024 * 1024,
    max_artifacts=100,
)
service = ComparisonService(
    evidence_reader=reader,
    repository=repository,
    max_changes=100,
)
```

这不是改变测试预期，只是将可信读取边界变成可复用依赖。

此外，Phase 38 的 `_workspace()` 测试 fixture 当前只放了 paper entry。新增
`blob_entries` 校验后，请补一条 `capsule/repository.bundle` entry，并让
`RepositoryIdentity.bundle_logical_path` 与它一致；生产快照本来就应满足该约束。所有手工构造
`WorkspaceManifest` 的测试都要显式选择 `phase26-v1` 历史语义，或提供完整的 Phase 39 Blob entries。

### 29.2 Evidence Reader 必测 case

可以把 `tests/test_comparison_service.py` 已有 `FakeJobs`、`FakeCatalog`、`_workspace()` 和
`_run_manifest()` 移到 `tests/fakes/run_evidence.py`，然后 Comparison 与 Reader 测试共同使用。至少覆盖：

```python
from app.run_evidence.errors import (
    RunEvidenceConflictError,
    RunEvidenceIntegrityError,
    RunEvidenceNotFoundError,
)


def test_reader_returns_verified_terminal_evidence(fixture):
    evidence = fixture.reader.read(fixture.job.job_id)
    assert evidence.job.job_id == fixture.job.job_id
    assert evidence.workspace.manifest_id == fixture.workspace.manifest_id
    assert evidence.run_manifest["run_id"] == fixture.job.run_id


def test_reader_rejects_non_terminal_job(fixture):
    fixture.job.status = "running"
    with pytest.raises(RunEvidenceConflictError):
        fixture.reader.read(fixture.job.job_id)


def test_reader_rejects_catalog_blob_sha_mismatch(fixture):
    fixture.catalog.corrupt_blob(fixture.job.job_id)
    with pytest.raises(RunEvidenceIntegrityError):
        fixture.reader.read(fixture.job.job_id)


def test_reader_rejects_workspace_hash_mismatch(fixture):
    fixture.workspace.manifest_hash = "0" * 64
    with pytest.raises(RunEvidenceIntegrityError):
        fixture.reader.read(fixture.job.job_id)


def test_reader_rejects_duplicate_run_manifest(fixture):
    fixture.catalog.duplicate_run_manifest(fixture.job.job_id)
    with pytest.raises(RunEvidenceNotFoundError):
        fixture.reader.read(fixture.job.job_id)
```

不要用真实路径直接 `read_text()` 代替 Fake Catalog；否则测试会绕开本阶段真正要保护的 Descriptor/Blob
identity 链。

### 29.3 RerunService 主流程测试

下面给出主流程完整骨架。`_evidence()` 使用第二十五节相同 Workspace helper 即可：

```python
# tests/test_rerun_service.py
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from app.interaction.schemas import ArtifactView
from app.rerun.repository import SqliteRerunRepository
from app.rerun.schemas import (
    RerunArgumentEdit,
    RerunProposalCreateRequest,
    RerunProposalSubmitRequest,
)
from app.rerun.service import RerunService
from app.run_evidence.schemas import VerifiedRunEvidence
from app.workspace.schemas import (
    JobRequirements,
    RepositoryIdentity,
    WorkspaceBlobEntry,
    WorkspaceManifest,
)


def _evidence() -> VerifiedRunEvidence:
    workspace = WorkspaceManifest(
        manifest_version="phase39-v2",
        manifest_id="wm-parent",
        manifest_hash="a" * 64,
        job_id="job-parent",
        run_id="run-parent",
        generation=2,
        source_host_id="host-a",
        entries=[
            WorkspaceBlobEntry(
                logical_path="source/paper.pdf",
                role="paper",
                object_key="workspace/paper",
                sha256="b" * 64,
                size_bytes=10,
            ),
            WorkspaceBlobEntry(
                logical_path="capsule/repository.bundle",
                role="repository_bundle",
                object_key="workspace/repository",
                sha256="c" * 64,
                size_bytes=20,
            ),
        ],
        repository=RepositoryIdentity(
            commit_sha="d" * 40,
            branch="main",
            clean=True,
            bundle_logical_path="capsule/repository.bundle",
        ),
        portable=False,
        blocked_reasons=["blob_store_is_host_local"],
        materialization_mode="blob_entries",
        created_at="2026-08-09T00:00:00+00:00",
    )
    job = SimpleNamespace(
        job_id="job-parent",
        run_id="run-parent",
        version=4,
        request=SimpleNamespace(
            experiment_goal="复现 main result",
            execution_profile_id="cpu-local",
        ),
    )
    artifact = ArtifactView(
        artifact_id="artifact-manifest",
        run_id="run-parent",
        layer="reports",
        relative_path="reports/run_manifest.json",
        media_type="application/json",
        sha256="e" * 64,
        size_bytes=100,
        producer_node="run_manifest",
        created_at="2026-08-09T00:00:00+00:00",
    )
    return VerifiedRunEvidence(
        job=job,
        workspace=workspace,
        artifacts=(artifact,),
        run_manifest_artifact=artifact,
        run_manifest={
            "job_id": "job-parent",
            "run_id": "run-parent",
            "repo_path": "/parent/repo",
            "run_dir": "/parent/run",
            "selected_run_command": {
                "command": "python train.py --epochs 50",
                "cwd": "/parent/repo",
                "source": "readme",
                "risk_level": "high",
            },
        },
    )


def _service(tmp_path):
    evidence = _evidence()
    reader = Mock()
    reader.read.return_value = evidence
    jobs = Mock()
    jobs.submit.return_value = (
        SimpleNamespace(
            job_id="job-child",
            thread_id="rerun-thread",
            status="queued",
        ),
        True,
    )
    repository = SqliteRerunRepository(
        tmp_path / "rerun.sqlite",
        clock=lambda: "2026-08-09T01:00:00+00:00",
    )
    service = RerunService(
        repository=repository,
        evidence_reader=reader,
        job_service=jobs,
        comparison_reader=None,
        proposal_ttl_seconds=3600,
        max_command_chars=8192,
        max_argv_items=256,
        max_edits=16,
        clock=lambda: "2026-08-09T01:00:00+00:00",
        requirements_resolver=lambda profile_id: JobRequirements(
            execution_profile_id=profile_id,
            execution_policy_hash="f" * 64,
            execution_backend="local",
        ),
    )
    return service, reader, jobs, evidence


def test_create_and_submit_builds_derived_job_request(tmp_path) -> None:
    service, reader, jobs, evidence = _service(tmp_path)
    proposal, created = service.create_proposal(
        request=RerunProposalCreateRequest(
            parent_job_id="job-parent",
            expected_parent_job_version=4,
            expected_parent_run_manifest_sha256="e" * 64,
            edits=[
                RerunArgumentEdit(
                    option="--epochs",
                    operation="set",
                    expected_old_value="50",
                    value="100",
                )
            ],
        ),
        idempotency_key="create-1",
    )
    assert created is True
    assert proposal.status == "pending"

    submitted, child, child_created = service.submit_proposal(
        proposal_id=proposal.proposal.proposal_id,
        request=RerunProposalSubmitRequest(
            expected_proposal_hash=proposal.proposal.proposal_hash,
            expected_version=proposal.version,
        ),
        idempotency_key="submit-operation-1",
    )
    assert child_created is True
    assert child.job_id == "job-child"
    assert submitted.status == "submitted"
    assert reader.read.call_count == 2

    kwargs = jobs.submit.call_args.kwargs
    request = kwargs["request"]
    assert request.paper_path is None
    assert request.repo_path is None
    assert request.paper_resource is None
    assert request.repo_resource is None
    assert request.derived_run.proposal_id == proposal.proposal.proposal_id
    assert request.derived_run.command_template.argv[-1].value == "100"
    assert kwargs["idempotency_key"] == (
        f"rerun-submit:{proposal.proposal.proposal_id}"
    )
```

还必须增加：

```text
创建时 expected run_manifest SHA 错误 -> RerunConflictError
创建时 comparison hash 错误 -> RerunConflictError
父 Job 不属于 comparison -> RerunConflictError
提交前 workspace generation 改变 -> stale
提交前 run_manifest SHA 改变 -> stale
提交前 selected command 改变 -> integrity error
提交前同名 Execution Profile policy 改变 -> stale
Proposal hash 被篡改 -> integrity error
过期 Proposal -> 不调用 JobService.submit
取消 Proposal -> 不调用 JobService.submit
同 create key 同 request -> reader 只调用一次
同 create key 不同 request -> conflict
同 submit operation key 崩溃重试 -> 同 child_job_id
不同 submit operation key 并发 -> conflict
```

### 29.4 API 必测 case

`tests/test_rerun_api.py` 使用 `create_api_app(rerun_service=fake)`，至少覆盖：

```text
POST /v1/rerun-proposals 缺 Idempotency-Key -> 422
POST create 合法 -> 200 + pending + replayed=false
同 key 重放 -> replayed=true
GET proposal -> 不包含 object_key、source_paths 或原始父绝对路径
POST submit stale version -> 409 RERUN_CONFLICT
POST submit expired -> 409 RERUN_PROPOSAL_EXPIRED
POST unsafe command -> 422 RERUN_COMMAND_REJECTED
GET unknown -> 404 RERUN_PROPOSAL_NOT_FOUND
Integrity error -> 500 且响应不泄露内部 detail
认证关闭/开启行为与现有 Job API 一致
```

API Fake 应返回真实 `RerunProposalRecord`，不要用任意 dict 绕过 response model 校验。

---

## 三十、端到端集成测试

> **本节类型：需要新增测试代码。**
>
> 需要新增：`tests/test_rerun_end_to_end.py`。

这一测试不调用真实 LLM 或训练程序。使用测试 Graph/Fake Runner 验证控制面闭环：

```text
parent Job terminal + sealed manifest + verified run_manifest
-> create Proposal
-> submit Proposal
-> child Job queued
-> child initial manifest 只包含父输入 Blob
-> worker materialize 到新的 assignment epoch
-> child checkpoint 没有父 approval
-> child 在 command_selection 等待
-> command selection resume
-> child 在 human_review 再次等待
```

关键断言：

```python
assert child.job_id != parent.job_id
assert child.run_id != parent.run_id
assert child.thread_id != parent.thread_id
assert child.workspace_manifest_id != parent.workspace_manifest_id

child_manifest = store.get_workspace_manifest(
    child.workspace_manifest_id
)
assert child_manifest.parent_manifest_id == parent.workspace_manifest_id
assert child_manifest.generation == 0
assert child_manifest.materialization_mode == "blob_entries"
assert child_manifest.source_paths is None
assert {
    item.object_key for item in child_manifest.entries
} <= {
    item.object_key
    for item in parent_manifest.entries
    if item.role in {"paper", "input_log", "repository_bundle"}
}
assert all(
    item.role not in {"run_artifact", "process_record", "process_log"}
    for item in child_manifest.entries
)

snapshot = graph.get_state(
    {"configurable": {"thread_id": child.thread_id}}
)
assert snapshot.values.get("user_approval") is None
assert snapshot.values.get("approval_record") is None
assert snapshot.values["run_commands"][0]["source"] == "config"
assert snapshot.values["rerun_seed"]["proposal_id"] == proposal_id
```

为了避免单测调用 LLM，可以给测试 Graph 提供确定性前置节点，或先用 `graph.update_state()` 注入到
`experiment_plan` 后的合法状态。不要通过直接调用 Executor 来“简化”，那会跳过本阶段最重要的安全验证。

---

## 三十一、运行自动化测试

> **本节类型：验证命令，不修改代码。**

先跑 Phase 39 定向测试：

```bash
python -m pytest \
  tests/test_verified_run_evidence_reader.py \
  tests/test_rerun_command_template.py \
  tests/test_rerun_repository.py \
  tests/test_immutable_workspace_derivation.py \
  tests/test_rerun_seed_node.py \
  tests/test_rerun_service.py \
  tests/test_rerun_api.py \
  tests/test_rerun_end_to_end.py
```

再跑被修改边界的回归：

```bash
python -m pytest \
  tests/test_comparison_service.py \
  tests/test_comparison_repository.py \
  tests/test_comparison_api.py \
  tests/test_workspace_materializer.py \
  tests/test_workspace_snapshot.py \
  tests/test_job_runtime.py \
  tests/test_job_api.py \
  tests/test_command_selection_node.py \
  tests/test_review_flow.py \
  tests/test_retention_service.py
```

最后执行全量检查：

```bash
python -m pytest
python -m ruff check app tests
python -m compileall app tests
```

如果仓库里的测试文件名与上面不同，先使用：

```bash
rg --files tests | sort
```

找到对应模块后替换命令，不要因为某个历史文件名不存在就跳过整个边界测试。

---

## 三十二、手工验收前准备

> **本节类型：手工验收，不修改代码。**

下面所有临时输入都放在项目目录：

```text
/data/tianshaoqi24/agent/paper_reproduction_copilot/runtime_inputs/phase39/
```

不要使用系统 `/tmp`，也不要在 `/data/tianshaoqi24/` 之外创建文件。

进入项目和激活环境：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent
mkdir -p runtime_inputs/phase39
```

先确认配置与数据库可用：

```bash
python -m app.main runtime-doctor
python -m app.main readiness-check
```

readiness 中应出现：

```text
rerun_repository_readiness = ready
```

### 32.1 选择合适的父 Job

父 Job 应满足：

```text
status 是 succeeded 或 failed
已有 reports/run_manifest.json
selected_run_command 是单进程命令
repository 是 clean 且有 Git bundle
命令不含 pipe、重定向、secret-like option
命令 cwd 位于 repo_path 内
命令里的绝对数据路径已在 Workspace external_data 声明
```

查看 Job：

```bash
python -m app.main list-jobs --limit 20
python -m app.main show-job <PARENT_JOB_ID>
```

如果现有父 Job 命令是：

```text
conda activate p4transformer
```

不要用它测试 Phase 39。它是 shell 会话状态修改，不是可由 `shell=False` 监管的单进程实验命令。

---

## 三十三、手工创建 Rerun Proposal

> **本节类型：手工验收，不修改代码。**

### 33.1 查看可信来源摘要

```bash
python -m app.main inspect-rerun-source <PARENT_JOB_ID>
```

记录输出中的：

```text
run_manifest_sha256
parent_job_version
selected_command_display
selected_command_sha256
workspace_manifest_hash
```

假设脱敏命令摘要中有：

```text
python train.py --batch-size 8 --epochs 50
```

在项目内创建 edits 文件：

```bash
cat > runtime_inputs/phase39/edits.json <<'JSON'
[
  {
    "option": "--epochs",
    "operation": "set",
    "expected_old_value": "50",
    "value": "100"
  }
]
JSON
```

如果父命令使用 `--epochs=50` 也仍提交 `expected_old_value="50"`；服务端会先规范化为两个 argv token。

### 33.2 创建 Proposal

```bash
python -m app.main create-rerun-proposal \
  <PARENT_JOB_ID> \
  --expected-job-version <PARENT_JOB_VERSION> \
  --expected-manifest-sha <RUN_MANIFEST_SHA256> \
  --edits-file runtime_inputs/phase39/edits.json \
  --idempotency-key phase39-create-001
```

预期：

```text
status = pending
version = 0
created = true
proposal_id = rerun_<24 hex>
proposal_hash = <64 hex>
expires_at > created_at
```

使用同一条命令重放，预期：

```text
created = false
proposal_id 与第一次完全相同
```

保持同一幂等键但将 `value` 改为 `200`，预期 `RERUN_CONFLICT`，不能静默返回旧 Proposal。

### 33.3 检查 Proposal 内容

```bash
python -m app.main show-rerun-proposal <PROPOSAL_ID>
```

确认：

```text
[ ] command_template 中 epochs 为 100
[ ] parent command SHA 与 inspect 输出一致
[ ] cwd 保存为 cwd_relative，不是父绝对路径
[ ] repo 内绝对参数保存为 repo_path template
[ ] 父 run_dir 内输出参数保存为 run_path template
[ ] dataset 参数保存为 dataset_path + worker label
[ ] 没有 parent run_dir
[ ] 没有 source_paths
[ ] 没有 approval_record
[ ] 没有 user_approval
[ ] 没有 claim_token
[ ] 没有 API key 或 token value
[ ] execution_profile_id、execution_policy_hash 和 execution_backend 均已冻结
```

此时还没有创建子 Job，`list-jobs` 数量不应增加。

---

## 三十四、手工提交并验证不可变派生

> **本节类型：手工验收，不修改代码。**

### 34.1 提交 Proposal

使用 `show-rerun-proposal` 返回的当前 hash 和 version：

```bash
python -m app.main submit-rerun-proposal \
  <PROPOSAL_ID> \
  --expected-hash <PROPOSAL_HASH> \
  --expected-version 0 \
  --idempotency-key phase39-submit-001
```

预期：

```text
proposal_status = submitted
child_job_id = job_<...>
child_status = queued
job_created = true
```

再次使用相同命令，Proposal 已是 submitted；应返回同一个 `child_job_id`，不能创建第二个 Job。

### 34.2 检查父子 Job 身份

```bash
python -m app.main show-job <PARENT_JOB_ID>
python -m app.main show-job <CHILD_JOB_ID>
```

确认：

```text
parent_job_id != child_job_id
parent_run_id != child_run_id
parent_thread_id != child_thread_id
child.input.derived_from_job_id == parent_job_id
child.status == queued
```

### 34.3 检查子 Workspace Manifest

使用下面的只读脚本；它不会修改数据库：

```bash
PARENT_JOB_ID=<PARENT_JOB_ID> CHILD_JOB_ID=<CHILD_JOB_ID> \
python - <<'PY'
import os

from app.job_runtime.factory import build_job_service

service = build_job_service()
parent = service.get(os.environ["PARENT_JOB_ID"])
child = service.get(os.environ["CHILD_JOB_ID"])
parent_manifest = service.store.get_workspace_manifest(
    parent.workspace_manifest_id
)
child_manifest = service.store.get_workspace_manifest(
    child.workspace_manifest_id
)

print({
    "parent_manifest_id": parent_manifest.manifest_id,
    "child_manifest_id": child_manifest.manifest_id,
    "child_parent_manifest_id": child_manifest.parent_manifest_id,
    "child_generation": child_manifest.generation,
    "child_portable": child_manifest.portable,
    "child_materialization_mode": child_manifest.materialization_mode,
    "child_has_source_paths": child_manifest.source_paths is not None,
    "child_roles": sorted(item.role for item in child_manifest.entries),
    "shared_object_keys": sorted(
        {item.object_key for item in parent_manifest.entries}
        & {item.object_key for item in child_manifest.entries}
    ),
})
PY
```

预期：

```text
child_parent_manifest_id == parent_manifest_id
child_generation == 0
child_materialization_mode == blob_entries
child_has_source_paths == false
child_roles 只包含 paper、repository_bundle 和可选 input_log
shared_object_keys 至少包含 paper 与 repository bundle
```

如果看到 `run_artifact`、`process_record` 或 `process_log`，说明派生边界写错，先停止后续运行。

---

## 三十五、验证新 Job 必须重新中断审批

> **本节类型：手工验收，不修改代码。**

这一步不需要真的执行训练命令。我们只运行到 `human_review`，然后选择拒绝即可。

### 35.1 运行到命令选择

```bash
python -m app.main run-worker --once --worker-id phase39-worker
python -m app.main show-job <CHILD_JOB_ID>
```

预期：

```text
status = waiting_for_input
interrupt_nodes = ["command_selection"]
```

从 `show-job` 获取 child `run_dir`，检查：

```bash
cat <CHILD_RUN_DIR>/planning/rerun_seed.json
cat <CHILD_RUN_DIR>/planning/command_selection_input.json
```

确认命令已经使用 child repo path，且 `--epochs 100`。它不应仍指向父 Workspace repo path。

### 35.2 选择派生命令

```bash
python -m app.main resume-job \
  <CHILD_JOB_ID> \
  --expected-node command_selection \
  --input <CHILD_RUN_DIR>/planning/command_selection_input.json \
  --idempotency-key phase39-command-select-001
```

再次运行 Worker：

```bash
python -m app.main run-worker --once --worker-id phase39-worker
python -m app.main show-job <CHILD_JOB_ID>
```

由于 Rerun Seed 固定为 high risk，预期：

```text
status = waiting_for_input
interrupt_nodes = ["human_review"]
```

这证明提交 Proposal 没有沿用父审批，也没有跳过 Action Builder/Risk Check。

### 35.3 安全地结束手工验收

为了不实际启动论文训练，拒绝新 action：

```bash
python -m app.main resume-job \
  <CHILD_JOB_ID> \
  --expected-node human_review \
  --decision rejected \
  --feedback "Phase 39 manual acceptance; do not execute training" \
  --idempotency-key phase39-review-reject-001

python -m app.main run-worker --once --worker-id phase39-worker
python -m app.main show-job <CHILD_JOB_ID>
```

预期 Job 安全结束并生成 Final Report/Run Manifest，没有 Executor 训练进程。

只有在你确认命令、数据集、资源预算和运行成本后，才把 `rejected` 改成 `approved` 做真实实验。

---

## 三十六、HTTP 手工验收

> **本节类型：手工验收，不修改代码。**

启动 API：

```bash
python -m app.main serve-stack
```

创建请求文件：

```bash
cat > runtime_inputs/phase39/create_request.json <<'JSON'
{
  "parent_job_id": "<PARENT_JOB_ID>",
  "expected_parent_job_version": <PARENT_JOB_VERSION>,
  "expected_parent_run_manifest_sha256": "<RUN_MANIFEST_SHA256>",
  "edits": [
    {
      "option": "--epochs",
      "operation": "set",
      "expected_old_value": "50",
      "value": "100"
    }
  ]
}
JSON
```

创建 Proposal：

```bash
curl -sS \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: phase39-api-create-001' \
  -H 'Authorization: Bearer <LOCAL_API_TOKEN>' \
  --data @runtime_inputs/phase39/create_request.json \
  http://127.0.0.1:8000/v1/rerun-proposals
```

创建提交体：

```bash
cat > runtime_inputs/phase39/submit_request.json <<'JSON'
{
  "expected_proposal_hash": "<PROPOSAL_HASH>",
  "expected_version": 0
}
JSON
```

提交：

```bash
curl -sS \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: phase39-api-submit-001' \
  -H 'Authorization: Bearer <LOCAL_API_TOKEN>' \
  --data @runtime_inputs/phase39/submit_request.json \
  http://127.0.0.1:8000/v1/rerun-proposals/<PROPOSAL_ID>/submit
```

查询：

```bash
curl -sS \
  -H 'Authorization: Bearer <LOCAL_API_TOKEN>' \
  http://127.0.0.1:8000/v1/rerun-proposals/<PROPOSAL_ID>
```

如果本地 API 配置关闭认证，则去掉 `Authorization`；不要把真实 token 写进教程、Git 或请求 JSON。

---

## 三十七、故障注入验收

> **本节类型：高级手工/测试验收，不修改生产数据。**

这些 case 优先用测试数据库执行，不要直接篡改真实 Job DB。

### 37.1 stale source

用 Fake Catalog 将 run manifest SHA 改变后提交旧 Proposal：

```text
预期：409 RERUN_CONFLICT
JobService.submit 调用次数：0
Proposal 不变为 submitted
```

### 37.2 Proposal 篡改

在测试 DB 中只改 `proposal_json.command_template`，不更新 hash：

```text
预期：RERUN_INTEGRITY_ERROR
不创建 child Job
```

### 37.3 提交中崩溃

让测试替身在 `JobService.submit()` 成功后、`complete_submission()` 前抛错，再用相同
`Idempotency-Key` 重试：

```text
第一次：Proposal 保持 submitting
第二次：Job Store 返回同一个 child Job
最终：Proposal submitted
Job 总数只增加 1
```

### 37.4 旧审批注入

在父 checkpoint 中设置：

```text
user_approval = approved
approval_record = {...}
```

派生 child 后断言：

```text
child checkpoint user_approval is None
child checkpoint approval_record is None
child 仍停在 command_selection/human_review
```

---

## 三十八、常见问题与排查

> **本节类型：故障排查，不修改代码。**

### 38.1 `RERUN_COMMAND_REJECTED`

依次检查：

```text
命令是否包含 |、&&、;、>、<、反引号或 $()
是否以 ENV=value 开头
是否包含 token/password/secret/api-key 等 option
cwd 是否位于 run_manifest.repo_path 内
是否有无法映射到 repo/dataset 的绝对路径
是否试图修改不存在或重复出现的 option
expected_old_value 是否与父命令一致
新 value 是否为主机绝对路径
```

不要通过删除校验来“兼容”复杂命令。应先把复杂 shell 流程包装为仓库内受审脚本，再让命令调用该脚本。

### 38.2 `dirty repository 不能进行不可变重跑派生`

父 Workspace 没有可信 Git bundle。可以：

```text
先把需要的修改提交到 Git，再运行一个新父 Job
或使用 Phase 29 受控 Resource 获取已固定 commit 的仓库
```

不要回退到复制父工作目录，因为 dirty/untracked 文件无法证明与 Proposal 创建时一致。

### 38.3 子 Job materialize 时仍去找父路径

检查：

```text
child manifest_version 是否 phase39-v2
materialization_mode 是否 blob_entries
source_paths 是否 None
WorkspaceMaterializer 是否按 resolved_materialization_mode 分支
是否只改了 materialize()，却漏改 planned_binding()
```

### 38.4 旧 Manifest 全部 hash 失败

通常是 `workspace_manifest_hash()` 没有对 `phase26-v1` 排除新字段。不要重写数据库中的旧 hash；修复
版本化 hash 逻辑并运行历史 fixture 测试。

### 38.5 子 Job 直接结束，没有 interrupt

查看：

```bash
python -m app.main show-job <CHILD_JOB_ID>
python -m app.main show-job-events <CHILD_JOB_ID>
```

并检查 child Run：

```text
reports/error_report.json
reports/final_report.md
planning/rerun_seed.json
planning/command_selection_input.json
```

常见原因：

```text
模板解析时缺少 dataset mount
repo-relative cwd 解析失败
实验规划前置节点出现 terminal StageError
rerun_seed.run_command.source 不是 RunCommand 已支持的 config
rerun_seed 节点没有插入 experiment_plan 与 command_selection_prepare 之间
```

### 38.6 Proposal 一直是 `submitting`

先用同一个提交 `Idempotency-Key` 重试。不要手工改成 pending，也不要换 key。如果仍失败：

```text
检查 Job Store 是否已有 rerun-submit:<proposal_id> 对应 Job
检查 Execution Profile policy 是否在崩溃窗口发生变化
检查 Job Store 错误和 Trace
```

无法确定外部提交结果时保持 `submitting` 是正确的 fail-closed 行为。

### 38.7 child 缺少 dataset mount

Proposal 只继承数据集 identity，不继承父 Worker 的主机路径。检查当前 Worker capability：

```text
dataset_mounts 是否包含 required_worker_label
挂载目录是否存在
子 Job requirements.required_labels 是否包含该 label
```

这正是重新调度和重新预检的目的，不应把父绝对路径硬编码回模板。

---

## 三十九、完成标准

> **本节类型：验收标准，不修改代码。**

只有同时满足下面条件，Phase 39 才算完成：

```text
[ ] Comparison 与 Rerun 共用 VerifiedRunEvidenceReader
[ ] Reader 校验 terminal Job、Workspace hash、Catalog、Descriptor、Blob size/SHA
[ ] Rerun 不使用脱敏 CommandSnapshot 作为执行输入
[ ] 创建 Proposal 需要 expected parent run_manifest SHA
[ ] 创建 Proposal 同时校验 expected parent Job version
[ ] Comparison binding 同时校验 comparison_id/hash 和 parent membership
[ ] Proposal 冻结 Execution Profile policy hash/backend，提交时重新校验
[ ] 命令 parser 拒绝 shell operator、env prefix 和 secret option
[ ] 第一版只允许 set/remove 已有长选项
[ ] option edit 绑定 expected_old_value
[ ] repo/dataset 路径变成类型化模板
[ ] 父 run_dir 路径变成 run_path，并解析到 child run_dir
[ ] 无法解释的绝对路径被拒绝
[ ] Proposal 内容有稳定 hash，状态单独持久化
[ ] 创建幂等键同请求重放、不同请求冲突
[ ] Proposal 有 pending/submitting/submitted/cancelled/expired 状态
[ ] 提交崩溃重试使用确定性 Job 幂等键
[ ] 子 Job 使用新的 job/run/thread/checkpoint identity
[ ] 子 generation-0 Manifest 只复用输入 Blob
[ ] 子 Manifest 不包含父 run/process Artifact
[ ] 本地 Blob 派生仍从 Blob entries 新建 Workspace
[ ] phase26-v1 历史 Manifest hash 继续有效
[ ] phase39-v2 hash 绑定 materialization_mode
[ ] 子 Job 重新解析 repo/dataset 路径
[ ] rerun_seed 覆盖 LLM run_commands 并清空旧 action/approval
[ ] 派生 Job 重新进入 command_selection interrupt
[ ] 派生 Job 重新进入 human_review interrupt
[ ] 不存在 Proposal -> Executor 的直接边
[ ] Job API View 只公开 derived_from_job_id，不泄露父路径
[ ] API 有 create/get/submit/cancel 和稳定错误 code
[ ] CLI 有 inspect/create/show/submit/cancel
[ ] Readiness 检查 Rerun DB
[ ] Retention Inventory 统计 Rerun SQLite/WAL/SHM
[ ] 父 Job GC 时共享 Blob 仍受 child Manifest 引用保护
[ ] Phase 38 Comparison 回归通过
[ ] Workspace、Job、审批与 Retention 回归通过
[ ] 全量 pytest、Ruff 和 compileall 通过
```

---

## 四十、本阶段涉及的 Agent 知识点

> **本节类型：知识总结，不修改代码。**

### 40.1 Agent Action Proposal 与 Action Execution 分离

成熟 Agent 不应把“建议下一步”直接等同于“执行下一步”：

```text
Evidence -> Proposal -> User Intent -> New Action -> Policy -> Approval -> Execution
```

每个箭头都有独立身份和 stale 检查，能解释系统为什么做这次运行。

### 40.2 Immutable Derivation

派生运行不是复制目录，而是从不可变内容身份构造新运行：

```text
same paper SHA
same repository bundle SHA / commit
same dataset references
+ changed structured arguments
+ new execution policy evaluation
= new independent Run
```

这与数据工程中的 lineage、容器镜像 layer 和可复现实验追踪是同一种思想。

### 40.3 Capability 与 Authority 分离

Proposal 拥有“描述新实验”的能力，但没有“执行命令”的 authority。真正执行仍取决于：

```text
Worker capability
Execution Profile
Preflight result
Risk policy
Action hash
Human approval
```

### 40.4 Typed Template 优于字符串占位符

`${REPO_ROOT}` 这类字符串占位符容易被用户伪造，也容易在 Shell 中产生二次展开。类型化参数明确区分：

```text
literal
repo_path
run_path
dataset_path(label, relative_path)
```

解析器可以针对每种类型执行不同的边界校验。

### 40.5 Optimistic Concurrency 与 Stale Decision

本阶段同时绑定：

```text
parent run_manifest SHA
parent Workspace manifest hash/generation
comparison hash
proposal hash/version
option expected_old_value
submit idempotency key
```

这不是重复，而是不同层级的并发身份。任何一层变化都应该让旧决策失效。

### 40.6 Saga 与幂等恢复

Rerun DB 和 Job DB 之间没有原子事务，提交过程属于一个很小的 Saga：

```text
begin submission
-> idempotent child Job submit
-> complete Proposal
```

无法原子提交时，可靠系统依赖稳定幂等键、可观察中间状态和重试消歧，而不是假装跨库操作不会崩溃。

---

## 四十一、下一阶段建议

> **本节类型：路线建议，不修改代码。**

完成 Phase 39 后，单机单用户系统已经形成：

```text
运行 -> 证据 -> 对比 -> 提案 -> 新运行
```

下一阶段如果仍不评价论文复现是否科学成功，建议做一个较小的：

```text
Phase 40：Conversational Rerun Drafting
          + Explicit Tool Confirmation
```

让用户可以在 Chat 中说：

```text
“以刚才成功的 Run 为模板，把 epochs 从 50 改成 100。”
```

Chat Agent 只能生成结构化 `RerunProposalCreateRequest` 草稿并展示：

```text
父 Run identity
旧值 -> 新值
继承的输入/environment identity
风险和不能证明的结论
```

用户点击确认后，后端才调用本阶段的 `create_proposal()`；提交 Proposal 和 action approval 仍是后续两个
独立确认。这样可以提升可对话体验，而不会给 Chat Agent 直接 Shell 权限。

如果开始关心论文是否真正复现成功，则应转向：

```text
Structured Metric Extraction
-> dataset/split/protocol identity
-> paper target metric
-> tolerance policy
-> evidence-grounded scientific comparison
```

---

## 四十二、本章总结

Phase 39 将 Phase 38 的“可验证差异”推进为“可审计的新实验”，但没有扩大不受控执行权：

```text
Verified Parent Run Evidence
  -> restricted argument edit
  -> immutable hashed Proposal
  -> versioned/idempotent submission state machine
  -> child generation-0 Manifest from immutable input Blobs
  -> new workspace / job / run / checkpoint
  -> rerun seed
  -> command selection
  -> risk + new human approval + preflight + smoke test
  -> supervised execution
```

这一阶段最重要的结果不是少输入一次命令，而是建立了可靠实验迭代边界：系统知道新运行从哪里来、改了
什么、复用了哪些内容、没有继承哪些权限，并能在崩溃、重试和旧页面操作下保持 fail closed。
