# 27. Phase 16：安全执行边界与受监管进程

## 这一阶段的目标

Phase 15 已经解决了两个基础问题：

```text
错误不再直接炸掉 Agent 进程
每次 run 都有独立 Artifact
```

但当前执行器仍然存在下面这些风险：

```python
env = os.environ.copy()

completed = subprocess.run(
    host_command,
    capture_output=True,
    timeout=timeout_seconds,
)
```

这段代码虽然简单，却隐含了五个问题：

```text
1. Agent 的 OPENAI_API_KEY 等 secret 会被继承到论文程序。
2. stdout/stderr 会完整保存在 Agent 内存中。
3. timeout 只保证 subprocess.run 返回，不保证孙进程全部退出。
4. 没有 PID、PGID、资源峰值和明确结束原因。
5. 风险检查主要看 program，没有统一检查 env、network、cwd 和 writable paths。
```

因此本阶段要把：

```text
“调用一次 subprocess”
```

升级为：

```text
“提交一份能力受限的 Action，由 Supervisor 监管整个进程组”
```

完成后的执行链是：

```text
ExecutableAction
  -> Action Capability Policy
  -> Human Review（需要时）
  -> Preflight
  -> ExecutionRunner
  -> ProcessSupervisor
       -> minimal environment
       -> independent process group
       -> incremental stdout/stderr drain
       -> resource sampling
       -> timeout/cancel/budget enforcement
       -> graceful terminate
       -> hard kill whole PGID
  -> ProcessRecord + bounded logs
  -> Run Manifest
```

---

## 一、先明确安全边界

### 1.1 本阶段能够保证什么

第一版 Phase 16 应保证：

```text
子进程默认拿不到 Agent API Key
Action 声明的能力在执行前经过确定性检查
日志不会无限进入 Agent 内存或 run 目录
每个 Action 使用独立进程组
timeout/cancel 后清理整个进程组
每次执行都有明确 end_reason
资源峰值和终止信号可以审计
local 与 conda 使用同一套安全语义
```

### 1.2 本阶段不能假装保证什么

`LocalRunner` 和 `CondaRunner` 仍然在 Agent 所在宿主机、同一操作系统用户下执行。

所以它们不能真正阻止一段恶意 Python 代码：

```text
主动连接网络
读取当前 Unix 用户有权限读取的其他文件
绕过声明写入未授权路径
主动修改自己的环境变量后访问其他 GPU
```

Capability Policy 对 local/conda 的含义是：

```text
执行前拒绝未声明或不被 profile 允许的能力
```

它不是：

```text
操作系统级强制沙箱
```

真正的网络 namespace、只读挂载、只允许指定可写目录、seccomp、cgroup
应该由后续 `RootlessContainerRunner` 或远程 Worker 实现。

因此 Phase 16 的准确定位是：

```text
Policy Constrained + Process Supervised
```

而不是：

```text
Hostile Code Sandbox
```

这一点必须写进 Final Report 和 README，避免把“审批 + shell=False”误解为强隔离。

---

## 二、完成后的模块结构

建议新增：

```text
app/execution/environment.py
app/execution/capability_policy.py
app/execution/cancellation.py
app/execution/process_supervisor.py

tests/test_minimal_execution_environment.py
tests/test_action_capability_policy.py
tests/test_process_supervisor.py
tests/test_execution_cancellation.py
tests/test_supervised_execution_integration.py
```

建议修改：

```text
pyproject.toml
app/config.py
app/schemas.py
app/state.py
app/main.py

app/execution/base.py
app/execution/local_runner.py
app/execution/conda_runner.py
app/execution/profile_store.py

app/tools/action_tools.py
app/tools/safe_shell_tools.py
app/tools/exec_tools.py
app/tools/preflight_tools.py
app/tools/artifact_tools.py

app/nodes/risk_check_node.py
app/nodes/preflight_check_node.py
app/nodes/smoke_test_node.py
app/nodes/executor_node.py
app/nodes/final_report_node.py
app/nodes/run_manifest_node.py
```

本阶段不需要新增 Graph 节点。

原因是 Capability Policy 正好属于现有 `risk_check_node` 的职责：

```text
action_builder
  -> risk_check（升级为 capability policy + risk）
  -> human_review / preflight
```

这样可以避免为了换一个风险实现而修改整张图。

---

## 三、推荐实施顺序

不要一次替换整个执行器。建议分成七个批次：

```text
批次 1：Schema + Profile + Action Hash
批次 2：Minimal Environment + Capability Policy
批次 3：ProcessSupervisor + Process Group + Bounded Log
批次 4：Resource Monitor + Timeout + Cancellation
批次 5：Runner / Executor / Smoke / Preflight 接入
批次 6：Artifact / Manifest / CLI
批次 7：单测、进程级集成测试和手工验收
```

每个批次结束后都运行相关测试。不要等所有代码写完才第一次执行 pytest。

---

## 四、增加进程监控依赖

修改 `pyproject.toml` 的 dependencies：

```toml
[project]
dependencies = [
    "langchain>=0.3",
    "langchain-openai>=0.2",
    "langgraph>=0.2",
    "langgraph-checkpoint-sqlite>=3",
    "pydantic>=2",
    "typer>=0.12",
    "rich>=13",
    "pymupdf>=1.24",
    "python-dotenv>=1.0",
    "psutil>=5.9",
]
```

这里使用 `psutil` 的原因是：

```text
读取进程树
采样 RSS
累计 CPU 时间
读取进程 I/O
校验 PID create_time，降低 PID 复用误杀风险
```

安装开发依赖：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m pip install -e ".[dev]"
```

验证：

```bash
python -c "import psutil; print(psutil.__version__)"
```

---

## 五、定义 Phase 16 Schema

修改 `app/schemas.py`。

### 5.1 扩展 import

文件顶部改为：

```python
from typing import Any, Literal, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    model_validator,
)
```

`AliasChoices` 只用于从旧 checkpoint 读取 `env_allowlist`。新状态统一写成
`env_overrides`。

### 5.2 增加资源预算

放在 `ExecutionProfile` 前：

```python
ExecutionEndReason = Literal[
    "exited",
    "launch_error",
    "timeout",
    "cancelled",
    "interrupted",
    "cpu_limit",
    "memory_limit",
    "process_limit",
    "write_limit",
    "gpu_limit",
    "policy_denied",
    "supervisor_error",
]


class ResourceBudget(BaseModel):
    """
    单次受监管执行允许使用的最大资源。

    max_wall_time_seconds 是墙钟时间，不等价于 CPU 时间。
    max_write_bytes 读取进程树 I/O 计数，是近似监管值，不等价于
    文件系统 quota。
    """

    max_wall_time_seconds: float = Field(default=300.0, gt=0)
    max_cpu_seconds: float | None = Field(default=None, gt=0)
    max_memory_bytes: int | None = Field(default=None, gt=0)
    max_processes: int = Field(default=32, ge=1)
    max_write_bytes: int | None = Field(default=None, gt=0)
    max_gpu_memory_bytes: int | None = Field(default=None, gt=0)

    # stdout 和 stderr 分别最多落盘多少字节。
    max_log_bytes_per_stream: int = Field(
        default=16 * 1024 * 1024,
        ge=4096,
    )

    # 返回到 Graph state 的每个 preview 上限。
    max_preview_bytes: int = Field(
        default=64 * 1024,
        ge=1024,
    )

    sample_interval_seconds: float = Field(
        default=0.2,
        gt=0,
        le=5,
    )
    terminate_grace_seconds: float = Field(
        default=5.0,
        ge=0,
        le=60,
    )


class ResourceBudgetOverride(BaseModel):
    """
    Action 对 Profile Budget 的收紧请求。

    所有字段默认 None，表示沿用 profile；这样不会因为 Pydantic 默认值
    无意中把 profile 上限放宽。
    """

    max_wall_time_seconds: float | None = Field(
        default=None,
        gt=0,
    )
    max_cpu_seconds: float | None = Field(default=None, gt=0)
    max_memory_bytes: int | None = Field(default=None, gt=0)
    max_processes: int | None = Field(default=None, ge=1)
    max_write_bytes: int | None = Field(default=None, gt=0)
    max_gpu_memory_bytes: int | None = Field(default=None, gt=0)
    max_log_bytes_per_stream: int | None = Field(
        default=None,
        ge=4096,
    )
    max_preview_bytes: int | None = Field(
        default=None,
        ge=1024,
    )
    sample_interval_seconds: float | None = Field(
        default=None,
        gt=0,
        le=5,
    )
    terminate_grace_seconds: float | None = Field(
        default=None,
        ge=0,
        le=60,
    )


class ResourceUsage(BaseModel):
    """Supervisor 在整个进程树生命周期内观察到的峰值。"""

    peak_rss_bytes: int = Field(default=0, ge=0)
    peak_process_count: int = Field(default=0, ge=0)
    total_cpu_seconds: float = Field(default=0.0, ge=0)
    total_write_bytes: int = Field(default=0, ge=0)
    peak_gpu_memory_bytes: int | None = Field(default=None, ge=0)
    samples: int = Field(default=0, ge=0)
```

### 5.3 定义 Capability Policy 结果

继续增加：

```python
class PolicyViolation(BaseModel):
    code: str
    field: str
    message: str


class ActionCapabilityRequest(BaseModel):
    """
    Action 声明自己需要的能力。

    local/conda 第一版只能在执行前检查这些声明，不能提供 OS 级隔离。
    """

    network_access: Literal["none", "outbound"] = "none"
    writable_paths: list[str] = Field(default_factory=list)
    env_keys: list[str] = Field(default_factory=list)


class CapabilityDecision(BaseModel):
    decision_id: str
    action_id: str
    action_hash: str
    allowed: bool
    requires_approval: bool
    risk_level: Literal["low", "medium", "high", "blocked"]
    reason: str
    request: ActionCapabilityRequest
    violations: list[PolicyViolation] = Field(default_factory=list)
    effective_budget: ResourceBudget
    evaluated_at: str
```

### 5.4 扩展 ExecutionProfile

用下面的完整类替换原 `ExecutionProfile`：

```python
class ExecutionProfile(BaseModel):
    """
    由项目维护者提供的受信任执行策略。

    LLM 只能选择 profile_id，不能生成或修改 profile 内容。
    """

    profile_id: str
    backend: Literal["local", "conda"]
    workspace_root: str
    artifact_root: str

    conda_executable: str | None = None
    conda_prefix: str | None = None

    # 只从 Agent 环境继承这些非敏感变量。
    inherited_env_keys: list[str] = Field(
        default_factory=lambda: [
            "PATH",
            "LANG",
            "LC_ALL",
            "TERM",
        ]
    )

    # Profile 固定注入的普通变量。禁止写入 secret。
    env: dict[str, str] = Field(default_factory=dict)

    # Action 只能覆盖这里列出的环境变量。
    allowed_action_env_keys: list[str] = Field(default_factory=list)

    # 只允许 basename 精确匹配，避免 substring 绕过。
    allowed_programs: list[str] = Field(
        default_factory=lambda: [
            "python",
            "python3",
            "torchrun",
            "accelerate",
            "pytest",
        ]
    )

    # 第一版按 args token 的包含关系阻断明显危险入口。
    blocked_arg_markers: list[str] = Field(
        default_factory=lambda: [
            "\n",
            "\r",
            "\x00",
        ]
    )

    writable_roots: list[str] = Field(default_factory=list)
    network_policy: Literal["deny", "allow"] = "deny"
    budget: ResourceBudget = Field(default_factory=ResourceBudget)

    # best_effort 表示 local/conda 只有策略检查和进程监管。
    # strict 预留给真正支持 OS 隔离的 runner。
    enforcement_mode: Literal["best_effort", "strict"] = "best_effort"

    @model_validator(mode="after")
    def validate_backend_fields(self) -> "ExecutionProfile":
        if self.backend == "conda":
            if not self.conda_executable:
                raise ValueError(
                    "conda 执行后端要求提供 conda_executable"
                )
            if not self.conda_prefix:
                raise ValueError(
                    "conda 执行后端要求提供 conda_prefix"
                )

        if self.backend in {"local", "conda"}:
            if self.enforcement_mode == "strict":
                raise ValueError(
                    "local/conda 不支持 strict OS isolation；"
                    "请使用 best_effort 或后续容器 Runner"
                )

        if not self.writable_roots:
            self.writable_roots = [self.workspace_root]

        return self
```

不要把下面这些变量写入 profile：

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
EMBEDDING_API_KEY
AWS_SECRET_ACCESS_KEY
GITHUB_TOKEN
LANGSMITH_API_KEY
任意 PASSWORD / SECRET / TOKEN / CREDENTIAL
```

### 5.5 扩展 ExecutableAction

替换原类：

```python
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

    # 兼容读取 Phase 15 的 env_allowlist；新 model_dump 只写 env_overrides。
    env_overrides: dict[str, str] = Field(
        default_factory=dict,
        validation_alias=AliasChoices(
            "env_overrides",
            "env_allowlist",
        ),
    )

    writable_paths: list[str] = Field(default_factory=list)
    network_access: Literal["none", "outbound"] = "none"

    # None 表示完全使用 profile budget。
    # 非 None 时只能收紧 profile，不能放宽。
    resource_budget: ResourceBudgetOverride | None = None

    risk: dict[str, Any] | None = None
    execution_profile_id: str
    execution_profile_fingerprint: str
    repo_patch_hash: str | None = None
```

### 5.6 定义进程记录和统一执行结果

继续增加：

```python
class ProcessRecord(BaseModel):
    execution_id: str
    action_id: str
    stage: str
    profile_id: str
    backend: Literal["local", "conda"]
    host_command_preview: list[str] = Field(default_factory=list)
    cwd: str

    pid: int | None = None
    pgid: int | None = None
    process_create_time: float | None = None

    started_at: str
    finished_at: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)

    status: Literal[
        "starting",
        "running",
        "terminating",
        "finished",
    ]
    end_reason: ExecutionEndReason | None = None
    returncode: int | None = None
    termination_signal: int | None = None
    hard_kill_used: bool = False

    stdout_path: str
    stderr_path: str
    stdout_bytes_seen: int = Field(default=0, ge=0)
    stderr_bytes_seen: int = Field(default=0, ge=0)
    stdout_bytes_written: int = Field(default=0, ge=0)
    stderr_bytes_written: int = Field(default=0, ge=0)
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    cancellation_requested: bool = False
    cancellation_reason: str | None = None
    resource_budget: ResourceBudget
    resource_usage: ResourceUsage = Field(
        default_factory=ResourceUsage
    )


class ExecutionResult(BaseModel):
    ok: bool
    returncode: int | None
    end_reason: ExecutionEndReason

    # 只保存有界 preview，不保存完整 stdout/stderr。
    stdout: str = ""
    stderr: str = ""
    combined_output: str = ""

    timeout: bool = False
    cancelled: bool = False
    log_truncated: bool = False

    execution_id: str | None = None
    execution_profile_id: str | None = None
    execution_backend: str | None = None
    cwd: str | None = None

    process_record_path: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    resource_usage: ResourceUsage = Field(
        default_factory=ResourceUsage
    )
```

这里暂时保留 `stdout`、`stderr`、`combined_output`，是为了兼容已有：

```text
preflight
smoke report
executor
log debug
tests
```

但它们从 Phase 16 开始只表示 preview，不再表示完整日志。

---

## 六、扩展 Graph State

修改 `app/state.py`，在执行相关字段附近增加：

```python
from typing import Any, Optional, TypedDict


class ReproductionState(TypedDict, total=False):
    # ...保留已有字段...

    capability_decision: Optional[dict[str, Any]]
    capability_report_path: Optional[str]

    active_execution_id: Optional[str]
    active_process_record_path: Optional[str]
    execution_end_reason: Optional[str]
    execution_resource_usage: Optional[dict[str, Any]]

    cancellation_requested: bool
    cancellation_reason: Optional[str]
```

注意：

```text
Graph checkpoint 只会在节点返回后更新。
```

因此进程运行期间，跨终端取消不能只依赖 checkpoint 中的
`active_execution_id`。Supervisor 还需要在 run 目录即时写 control record，
后面的 `cancel-run` 会读取该文件。

---

## 七、增加配置项

修改 `app/config.py`，在 `Settings` 中增加：

```python
@dataclass
class Settings:
    # ...保留已有配置...

    process_poll_interval_seconds: float = float(
        os.getenv("PROCESS_POLL_INTERVAL_SECONDS", "0.2")
    )

    process_terminate_grace_seconds: float = float(
        os.getenv("PROCESS_TERMINATE_GRACE_SECONDS", "5")
    )

    process_max_log_bytes_per_stream: int = int(
        os.getenv(
            "PROCESS_MAX_LOG_BYTES_PER_STREAM",
            str(16 * 1024 * 1024),
        )
    )

    process_max_preview_bytes: int = int(
        os.getenv(
            "PROCESS_MAX_PREVIEW_BYTES",
            str(64 * 1024),
        )
    )
```

Profile 中的值应当优先，因为它参与 profile fingerprint 和审批绑定。

Settings 只作为：

```text
创建新 profile 时的默认值
测试未显式指定预算时的 fallback
```

不要在执行时用环境变量悄悄覆盖已经审批的 Profile Budget。

---

## 八、升级 Execution Profile 配置

本机配置仍放在：

```text
/data/tianshaoqi24/agent/paper_reproduction_copilot/config/execution_profiles.local.json
```

Phase 16 示例：

```json
{
  "profiles": [
    {
      "profile_id": "pstnet-local-supervised",
      "backend": "local",
      "workspace_root": "/data/tianshaoqi24/PST-Convolution-main",
      "artifact_root": "/data/tianshaoqi24/agent/paper_reproduction_copilot/runs",
      "inherited_env_keys": [
        "PATH",
        "LANG",
        "LC_ALL",
        "TERM"
      ],
      "env": {
        "CUDA_VISIBLE_DEVICES": "0"
      },
      "allowed_action_env_keys": [
        "OMP_NUM_THREADS"
      ],
      "allowed_programs": [
        "python",
        "python3",
        "torchrun",
        "pytest"
      ],
      "writable_roots": [
        "/data/tianshaoqi24/PST-Convolution-main",
        "/data/tianshaoqi24/agent/paper_reproduction_copilot/runs"
      ],
      "network_policy": "deny",
      "enforcement_mode": "best_effort",
      "budget": {
        "max_wall_time_seconds": 3600,
        "max_cpu_seconds": 7200,
        "max_memory_bytes": 17179869184,
        "max_processes": 64,
        "max_write_bytes": 107374182400,
        "max_gpu_memory_bytes": null,
        "max_log_bytes_per_stream": 16777216,
        "max_preview_bytes": 65536,
        "sample_interval_seconds": 0.2,
        "terminate_grace_seconds": 5
      }
    }
  ]
}
```

所有示例路径都位于：

```text
/data/tianshaoqi24/
```

不要继续使用旧配置中的：

```text
旧 HOME 下的 Conda 绝对路径
系统临时目录
```

临时 HOME、缓存和日志也应放入当前：

```text
runs/<run_id>/execution/runtime/
```

---

## 九、Profile Fingerprint 必须覆盖安全配置

修改 `app/execution/profile_store.py` 中
`compute_execution_profile_fingerprint()`：

```python
def compute_execution_profile_fingerprint(
    profile: ExecutionProfile,
) -> str:
    """
    所有能够改变执行权限或资源上限的字段都必须进入指纹。

    人工审批之后修改任何安全字段，旧 action hash 都必须失效。
    """

    material = {
        "profile_id": profile.profile_id,
        "backend": profile.backend,
        "workspace_root": profile.workspace_root,
        "artifact_root": profile.artifact_root,
        "conda_executable": profile.conda_executable,
        "conda_prefix": profile.conda_prefix,
        "inherited_env_keys": sorted(
            profile.inherited_env_keys
        ),
        "env": profile.env,
        "allowed_action_env_keys": sorted(
            profile.allowed_action_env_keys
        ),
        "allowed_programs": sorted(profile.allowed_programs),
        "blocked_arg_markers": sorted(
            profile.blocked_arg_markers
        ),
        "writable_roots": sorted(profile.writable_roots),
        "network_policy": profile.network_policy,
        "budget": profile.budget.model_dump(),
        "enforcement_mode": profile.enforcement_mode,
    }

    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()
```

下面这些修改都必须导致指纹变化：

```text
允许新的 program
允许新的 env key
扩大 writable root
允许 network
提高资源预算
切换 conda prefix
切换 enforcement mode
```

---

## 十、Action Hash 必须绑定所有能力

修改 `app/tools/action_tools.py`：

```python
def compute_action_hash(action: dict) -> str:
    """
    审批绑定“执行什么 + 在哪里执行 + 能使用什么能力”。
    """

    material = {
        "action_type": action.get("action_type"),
        "program": action.get("program"),
        "args": action.get("args", []),
        "cwd": action.get("cwd"),
        "env_overrides": action.get(
            "env_overrides",
            action.get("env_allowlist", {}),
        ),
        "timeout_seconds": action.get("timeout_seconds"),
        "writable_paths": action.get("writable_paths", []),
        "network_access": action.get(
            "network_access",
            "none",
        ),
        "resource_budget": action.get("resource_budget"),
        "execution_profile_id": action.get(
            "execution_profile_id"
        ),
        "execution_profile_fingerprint": action.get(
            "execution_profile_fingerprint"
        ),
        "repo_patch_hash": action.get("repo_patch_hash"),
    }

    payload = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

修改 `build_run_action_from_command()` 创建 Action 的部分：

```python
action = ExecutableAction(
    action_id=f"action_{uuid4().hex[:12]}",
    action_type="run_command",
    program=tokens[0],
    args=tokens[1:],
    cwd=str(Path(normalized_cwd)),
    source=source,
    reason=reason,
    timeout_seconds=timeout_seconds,
    env_overrides={},
    writable_paths=[str(Path(normalized_cwd))],
    network_access="none",
    resource_budget=None,
    execution_profile_id=execution_profile_id,
    execution_profile_fingerprint=(
        execution_profile_fingerprint
    ),
)
```

如果用户需要修改 `env_overrides`、`network_access` 或资源预算，必须：

```text
修改 Action
  -> 重新计算 action hash
  -> 重新运行 risk check
  -> 重新人工审批
```

不能在审批后由 executor 临时补字段。

---

## 十一、批次 1 测试

先增加：

```text
tests/test_execution_profile_hash.py
tests/test_structured_action_and_approval_hash.py
tests/test_action_capability_policy.py
```

至少覆盖：

```python
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
)
from app.schemas import ExecutionProfile
from app.tools.action_tools import compute_action_hash


def test_profile_hash_changes_when_network_policy_changes(
    tmp_path,
) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()

    profile = ExecutionProfile(
        profile_id="test",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "runs"),
        writable_roots=[str(workspace)],
        network_policy="deny",
    )
    original = compute_execution_profile_fingerprint(profile)
    changed = compute_execution_profile_fingerprint(
        profile.model_copy(
            update={"network_policy": "allow"}
        )
    )

    assert original != changed


def test_action_hash_binds_network_and_budget() -> None:
    action = {
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": "/data/tianshaoqi24/demo",
        "env_overrides": {},
        "timeout_seconds": 300,
        "writable_paths": ["/data/tianshaoqi24/demo"],
        "network_access": "none",
        "resource_budget": None,
        "execution_profile_id": "test",
        "execution_profile_fingerprint": "profile-hash",
        "repo_patch_hash": None,
    }

    original = compute_action_hash(action)
    with_network = compute_action_hash(
        {**action, "network_access": "outbound"}
    )
    with_budget = compute_action_hash(
        {
            **action,
            "resource_budget": {
                "max_wall_time_seconds": 30,
                "max_processes": 4,
                "max_log_bytes_per_stream": 4096,
                "max_preview_bytes": 1024,
                "sample_interval_seconds": 0.2,
                "terminate_grace_seconds": 1,
            },
        }
    )

    assert original != with_network
    assert original != with_budget
```

运行：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m pytest \
  tests/test_execution_profile_hash.py \
  tests/test_structured_action_and_approval_hash.py \
  tests/test_action_capability_policy.py
```


---

## 十二、实现最小子进程环境

新增 `app/execution/environment.py`：

```python
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.schemas import ExecutableAction, ExecutionProfile


SAFE_INHERITED_ENV_KEYS = {
    "PATH",
    "LANG",
    "LC_ALL",
    "TERM",
    "TZ",
}

# 这些变量由 Supervisor 根据当前 run 创建，profile/action 都不能覆盖。
SUPERVISOR_OWNED_ENV_KEYS = {
    "HOME",
    "TMPDIR",
    "TMP",
    "TEMP",
    "XDG_CACHE_HOME",
    "PYTHONPYCACHEPREFIX",
}

SENSITIVE_ENV_NAME = re.compile(
    r"(^|_)(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIALS?)($|_)",
    re.IGNORECASE,
)
VALID_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class EnvironmentBuildResult:
    env: dict[str, str]
    runtime_dir: Path
    inherited_keys: list[str]
    profile_keys: list[str]
    action_keys: list[str]


def is_sensitive_env_name(name: str) -> bool:
    """按变量名拒绝 secret；不要把 secret 值写进错误消息。"""

    return bool(SENSITIVE_ENV_NAME.search(name))


def _validate_env_pair(name: str, value: str) -> None:
    if not VALID_ENV_NAME.fullmatch(name):
        raise ValueError(f"无效环境变量名：{name!r}")
    if is_sensitive_env_name(name):
        raise ValueError(f"执行环境禁止 secret 变量：{name}")
    if "\x00" in value:
        raise ValueError(f"环境变量包含 NUL：{name}")


def _is_within(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _validate_path_list(
    *,
    value: str,
    allowed_roots: list[Path],
    variable_name: str,
) -> str:
    """
    校验 PATH/PYTHONPATH 一类路径列表。

    相对路径和空元素会让当前 cwd 隐式进入搜索路径，因此直接拒绝。
    """

    normalized: list[str] = []
    for raw_item in value.split(os.pathsep):
        if not raw_item:
            raise ValueError(
                f"{variable_name} 不允许空路径元素"
            )

        candidate = Path(raw_item).expanduser()
        if not candidate.is_absolute():
            raise ValueError(
                f"{variable_name} 只允许绝对路径：{raw_item}"
            )

        resolved = candidate.resolve()
        if (
            variable_name == "PYTHONPATH"
            and not _is_within(resolved, allowed_roots)
        ):
            raise ValueError(
                "PYTHONPATH 位于允许读取范围之外："
                f"{resolved}"
            )

        normalized.append(str(resolved))

    return os.pathsep.join(normalized)


def build_minimal_environment(
    *,
    profile: ExecutionProfile,
    action: ExecutableAction,
    run_dir: str | Path,
    execution_id: str,
) -> EnvironmentBuildResult:
    """
    从空字典构建论文程序环境，不再调用 os.environ.copy()。

    返回值中的 key 列表可以写入 ProcessRecord；env 的值不能整体写入
    Manifest，以免未来新增变量时把敏感值落盘。
    """

    run_root = Path(run_dir).resolve()
    configured_runs_root = settings.runs_dir.resolve()
    if (
        run_root == configured_runs_root
        or configured_runs_root not in run_root.parents
    ):
        raise ValueError(f"run_dir 不在 RUNS_DIR 内：{run_root}")

    workspace_root = Path(profile.workspace_root).resolve()
    allowed_python_roots = [workspace_root]
    if profile.conda_prefix:
        allowed_python_roots.append(
            Path(profile.conda_prefix).resolve()
        )

    env: dict[str, str] = {}
    inherited_keys: list[str] = []
    profile_keys: list[str] = []
    action_keys: list[str] = []

    for key in profile.inherited_env_keys:
        if key not in SAFE_INHERITED_ENV_KEYS:
            raise ValueError(
                f"profile 请求继承未允许的 Agent 环境变量：{key}"
            )
        if is_sensitive_env_name(key):
            raise ValueError(f"禁止继承 secret 环境变量：{key}")
        value = os.environ.get(key)
        if value is not None:
            _validate_env_pair(key, value)
            env[key] = value
            inherited_keys.append(key)

    for key, value in profile.env.items():
        if key in SUPERVISOR_OWNED_ENV_KEYS:
            raise ValueError(
                f"profile 不能覆盖 Supervisor 变量：{key}"
            )
        value = str(value)
        _validate_env_pair(key, value)
        env[key] = value
        profile_keys.append(key)

    for key, value in action.env_overrides.items():
        if key not in profile.allowed_action_env_keys:
            raise ValueError(
                f"Action 环境变量未被 profile 允许：{key}"
            )
        if key in SUPERVISOR_OWNED_ENV_KEYS:
            raise ValueError(
                f"Action 不能覆盖 Supervisor 变量：{key}"
            )
        value = str(value)
        _validate_env_pair(key, value)
        env[key] = value
        action_keys.append(key)

    runtime_dir = (
        run_root / "execution" / "runtime" / execution_id
    ).resolve()
    if run_root not in runtime_dir.parents:
        raise ValueError("execution runtime 目录逃逸当前 run")

    home_dir = runtime_dir / "home"
    tmp_dir = runtime_dir / "tmp"
    cache_dir = runtime_dir / "cache"
    pycache_dir = runtime_dir / "pycache"
    for directory in (
        home_dir,
        tmp_dir,
        cache_dir,
        pycache_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    env.update(
        {
            "HOME": str(home_dir),
            "TMPDIR": str(tmp_dir),
            "TMP": str(tmp_dir),
            "TEMP": str(tmp_dir),
            "XDG_CACHE_HOME": str(cache_dir),
            "PYTHONPYCACHEPREFIX": str(pycache_dir),
            "PYTHONUNBUFFERED": "1",
        }
    )

    if "PATH" not in env:
        raise ValueError(
            "最小执行环境缺少 PATH；请在 profile 中继承或显式配置"
        )

    env["PATH"] = _validate_path_list(
        value=env["PATH"],
        allowed_roots=allowed_python_roots,
        variable_name="PATH",
    )

    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = _validate_path_list(
            value=env["PYTHONPATH"],
            allowed_roots=allowed_python_roots,
            variable_name="PYTHONPATH",
        )

    return EnvironmentBuildResult(
        env=env,
        runtime_dir=runtime_dir,
        inherited_keys=sorted(inherited_keys),
        profile_keys=sorted(profile_keys),
        action_keys=sorted(action_keys),
    )
```

### 12.1 为什么从空环境开始

不要使用黑名单删除：

```python
import os


env = os.environ.copy()
env.pop("OPENAI_API_KEY", None)
```

因为你永远无法列完所有 secret 名称，例如：

```text
LANGSMITH_API_KEY
WANDB_API_KEY
HF_TOKEN
AWS_SESSION_TOKEN
公司内部新增加的变量
```

正确方向是：

```text
空环境
  + 少量固定可继承 key
  + profile 明确声明
  + action 经过 allowlist 的 override
  + Supervisor 自己创建的 HOME/TMP/cache
```

### 12.2 CUDA 和实验追踪服务

`CUDA_VISIBLE_DEVICES` 应由 profile 设置，而不是继承 Agent 值。

如果论文程序确实需要 W&B、MLflow 或 Hugging Face Token，不要在这一阶段直接
把 token 放进 `ExecutionProfile.env`，因为 profile 和 fingerprint 会进入审计记录。

后续应实现：

```text
Secret Reference
  -> Worker 启动时解析
  -> 只注入子进程
  -> 永不进入 checkpoint / manifest / log
```

Phase 16 第一版默认禁止这类 secret，先保证 Agent Key 不泄漏。

---

## 十三、实现 Action Capability Policy

新增 `app/execution/capability_policy.py`：

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.execution.environment import is_sensitive_env_name
from app.schemas import (
    ActionCapabilityRequest,
    CapabilityDecision,
    ExecutableAction,
    ExecutionProfile,
    PolicyViolation,
    ResourceBudget,
    ResourceBudgetOverride,
)
from app.tools.action_tools import compute_action_hash


READ_ONLY_PROGRAMS = {"echo", "pwd", "ls", "which"}
DYNAMIC_CODE_FLAGS = {
    "python": {"-c"},
    "python3": {"-c"},
    "bash": {"-c"},
    "sh": {"-c"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _within(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _violation(
    code: str,
    field: str,
    message: str,
) -> PolicyViolation:
    return PolicyViolation(
        code=code,
        field=field,
        message=message,
    )


def _merge_effective_budget(
    *,
    profile_budget: ResourceBudget,
    action_timeout_seconds: int,
    override: ResourceBudgetOverride | None,
) -> tuple[ResourceBudget, list[PolicyViolation]]:
    """Action 的任何非空预算都只能小于等于 profile 上限。"""

    violations: list[PolicyViolation] = []
    material = profile_budget.model_dump()

    if action_timeout_seconds > profile_budget.max_wall_time_seconds:
        violations.append(
            _violation(
                "WALL_TIME_EXCEEDS_PROFILE",
                "timeout_seconds",
                "Action timeout 超过 profile wall-time budget",
            )
        )
    else:
        material["max_wall_time_seconds"] = float(
            action_timeout_seconds
        )

    if override is None:
        return ResourceBudget.model_validate(material), violations

    requested = override.model_dump(exclude_none=True)
    for field, value in requested.items():
        profile_value = getattr(profile_budget, field)

        # Profile 为 None 表示没有设置这一项上限，Action 可以主动收紧。
        if profile_value is not None and value > profile_value:
            violations.append(
                _violation(
                    "RESOURCE_BUDGET_EXPANSION",
                    f"resource_budget.{field}",
                    f"Action 请求 {value}，超过 profile 上限 "
                    f"{profile_value}",
                )
            )
            continue

        material[field] = value

    material["max_wall_time_seconds"] = min(
        float(material["max_wall_time_seconds"]),
        float(action_timeout_seconds),
    )
    return ResourceBudget.model_validate(material), violations


def evaluate_action_capabilities(
    *,
    raw_action: dict,
    profile: ExecutionProfile,
) -> CapabilityDecision:
    """
    确定性检查 Action 的全部声明能力。

    该函数不调用 LLM、不执行程序、不访问网络，也不修改 Action。
    """

    action = ExecutableAction.model_validate(raw_action)
    action_hash = compute_action_hash(action.model_dump())
    violations: list[PolicyViolation] = []

    workspace_root = Path(profile.workspace_root).resolve()
    writable_roots = [
        Path(path).resolve()
        for path in profile.writable_roots
    ]

    cwd = Path(action.cwd).expanduser().resolve()
    if not _within(cwd, [workspace_root]):
        violations.append(
            _violation(
                "CWD_OUTSIDE_WORKSPACE",
                "cwd",
                f"cwd 位于 profile workspace 之外：{cwd}",
            )
        )

    # Action program 必须是 basename。Conda wrapper 由 Runner 构造。
    program = action.program.strip()
    if Path(program).name != program:
        violations.append(
            _violation(
                "ABSOLUTE_PROGRAM_NOT_ALLOWED",
                "program",
                "Action program 必须是 basename",
            )
        )
    elif program not in set(profile.allowed_programs):
        violations.append(
            _violation(
                "PROGRAM_NOT_ALLOWED",
                "program",
                f"profile 未允许程序：{program}",
            )
        )

    for index, arg in enumerate(action.args):
        for marker in profile.blocked_arg_markers:
            if marker and marker in arg:
                violations.append(
                    _violation(
                        "BLOCKED_ARGUMENT_MARKER",
                        f"args.{index}",
                        "参数包含 profile 阻断的控制字符",
                    )
                )

    blocked_flags = DYNAMIC_CODE_FLAGS.get(program, set())
    if blocked_flags.intersection(action.args):
        violations.append(
            _violation(
                "DYNAMIC_CODE_FLAG_BLOCKED",
                "args",
                f"不允许通过 {program} 动态传入代码",
            )
        )

    normalized_writable_paths: list[str] = []
    for raw_path in action.writable_paths:
        path = Path(raw_path).expanduser().resolve()
        normalized_writable_paths.append(str(path))
        if not _within(path, writable_roots):
            violations.append(
                _violation(
                    "WRITABLE_PATH_NOT_ALLOWED",
                    "writable_paths",
                    f"可写路径不在 profile writable_roots：{path}",
                )
            )

    if (
        action.network_access == "outbound"
        and profile.network_policy != "allow"
    ):
        violations.append(
            _violation(
                "NETWORK_NOT_ALLOWED",
                "network_access",
                "Action 请求外网，但 profile network_policy=deny",
            )
        )

    for key in action.env_overrides:
        if is_sensitive_env_name(key):
            violations.append(
                _violation(
                    "SENSITIVE_ENV_NOT_ALLOWED",
                    "env_overrides",
                    f"Action 禁止注入 secret 环境变量：{key}",
                )
            )
        elif key not in profile.allowed_action_env_keys:
            violations.append(
                _violation(
                    "ACTION_ENV_NOT_ALLOWED",
                    "env_overrides",
                    f"profile 未允许 Action 环境变量：{key}",
                )
            )

    effective_budget, budget_violations = _merge_effective_budget(
        profile_budget=profile.budget,
        action_timeout_seconds=action.timeout_seconds,
        override=action.resource_budget,
    )
    violations.extend(budget_violations)

    request = ActionCapabilityRequest(
        network_access=action.network_access,
        writable_paths=normalized_writable_paths,
        env_keys=sorted(action.env_overrides),
    )

    if violations:
        risk_level = "blocked"
        requires_approval = False
        reason = "Action capability policy 拒绝执行"
    elif (
        action.network_access == "outbound"
        or action.env_overrides
        or program not in READ_ONLY_PROGRAMS
        or normalized_writable_paths
    ):
        risk_level = (
            "high"
            if action.network_access == "outbound"
            else "medium"
        )
        requires_approval = True
        reason = "Action 包含执行、写入、环境或网络能力"
    else:
        risk_level = "low"
        requires_approval = False
        reason = "Action 只使用允许的只读能力"

    return CapabilityDecision(
        decision_id=f"cap_{uuid4().hex[:12]}",
        action_id=action.action_id,
        action_hash=action_hash,
        allowed=not violations,
        requires_approval=requires_approval,
        risk_level=risk_level,
        reason=reason,
        request=request,
        violations=violations,
        effective_budget=effective_budget,
        evaluated_at=utc_now(),
    )
```

### 13.1 为什么禁止 Action 使用绝对 program

只检查 basename 是不够的：

```text
profile allowed_programs = ["python"]
Action program = /data/tianshaoqi24/untrusted/python
```

它的 basename 仍然叫 `python`。

第一版采用最清楚的规则：

```text
Action 只能写 python / torchrun / pytest 这种 basename
Runner 使用最小 PATH 解析
CondaRunner 的 conda executable 只能来自受信任 profile
```

以后如果要支持绝对 executable，应增加独立的 `allowed_executable_roots`，
不能只增加一个字符串白名单。

### 13.2 `network_access=none` 的真实含义

在 local/conda 中它表示：

```text
Action 没有申请网络能力
```

不表示内核已经禁网。因此 Capability Decision 和 Final Report 应展示：

```text
enforcement_mode=best_effort
network_declared=none
network_os_enforced=false
```

只有未来的 container runner 创建 network namespace 后，才能写：

```text
network_os_enforced=true
```

---

## 十四、升级 risk_check_node

Phase 16 后，`safe_shell_tools.assess_action_risk()` 不再作为最终安全决定。
它可以暂时保留为兼容函数，但 `risk_check_node` 必须读取完整 Capability Decision。

用下面的完整实现替换 `app/nodes/risk_check_node.py`：

```python
from app.execution.capability_policy import (
    evaluate_action_capabilities,
)
from app.execution.profile_store import get_execution_profile
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import stage_error_result


def risk_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return stage_error_result(
            state=state,
            stage="risk_check",
            code="PENDING_ACTION_REQUIRED",
            category="agent",
            message="风险检查前缺少 pending_action",
            extra_update={
                "requires_approval": False,
                "final_status": "invalid_action",
            },
        )

    profile_id = pending_action.get("execution_profile_id")
    if not profile_id:
        return stage_error_result(
            state=state,
            stage="risk_check",
            code="EXECUTION_PROFILE_REQUIRED",
            category="agent",
            message="Action 缺少 execution_profile_id",
            extra_update={"final_status": "invalid_action"},
        )

    profile = get_execution_profile(profile_id)
    decision = evaluate_action_capabilities(
        raw_action=pending_action,
        profile=profile,
    )

    report_path, report_record = write_json_artifact(
        state=state,
        relative_path="planning/capability_decision.json",
        payload=decision.model_dump(),
        producer_node="risk_check",
    )

    action_with_risk = {
        **pending_action,
        "risk": {
            "level": decision.risk_level,
            "reason": decision.reason,
            "blocked": not decision.allowed,
            "capability_decision_id": decision.decision_id,
        },
    }
    payload = {
        "pending_action": action_with_risk,
        "capability_decision": decision.model_dump(),
        "capability_report_path": str(report_path),
        "requires_approval": decision.requires_approval,
        **artifact_state_update(state, [report_record]),
    }

    if not decision.allowed:
        codes = ", ".join(
            violation.code
            for violation in decision.violations
        )
        return stage_error_result(
            state={**state, **payload},
            stage="risk_check",
            code="ACTION_CAPABILITY_POLICY_BLOCKED",
            category="user",
            message=f"Action 被能力策略拒绝：{codes}",
            extra_update={
                **payload,
                "requires_approval": False,
                "final_status": "policy_blocked",
            },
        )

    if not decision.requires_approval:
        payload.update(
            {
                "user_approval": "not_required",
                "error": None,
            }
        )

    return payload
```

### 14.1 审批页必须展示什么

`human_review_node` 的中断 payload 应至少包含：

```text
program + args
cwd
writable_paths
env key 名称（不显示敏感值）
network_access
effective_budget
execution profile id + fingerprint
best_effort / strict enforcement mode
```

人工审批的对象不再只是“这条命令看起来危险吗”，而是：

```text
是否允许这条命令使用这一组明确能力和资源预算
```

### 14.2 审批哈希仍然必须重新计算

`risk_check_node` 给 `pending_action` 增加 `risk` 展示字段后，不能让 `risk` 进入
`compute_action_hash()`，因为 risk 是对 Action 的判断，不是 Action 本身的能力。

但是下面这些字段必须在 hash 中：

```text
program / args / cwd
env_overrides
writable_paths
network_access
resource_budget
profile id / fingerprint
repo_patch_hash
```

---

## 十五、批次 2 测试

新增 `tests/test_minimal_execution_environment.py`：

```python
import pytest

from app.execution.environment import build_minimal_environment
from app.schemas import ExecutableAction, ExecutionProfile


def _profile(tmp_path) -> ExecutionProfile:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    return ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "runs"),
        inherited_env_keys=["PATH", "LANG"],
        allowed_action_env_keys=["OMP_NUM_THREADS"],
        allowed_programs=["python"],
        writable_roots=[str(workspace)],
    )


def _action(profile: ExecutionProfile) -> ExecutableAction:
    return ExecutableAction(
        action_id="action-1",
        program="python",
        args=["train.py"],
        cwd=profile.workspace_root,
        source="script",
        reason="test",
        env_overrides={"OMP_NUM_THREADS": "2"},
        writable_paths=[profile.workspace_root],
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint="hash",
    )


def test_minimal_env_does_not_inherit_agent_secret(
    tmp_path,
    monkeypatch,
) -> None:
    profile = _profile(tmp_path)
    action = _action(profile)
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    run_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "app.execution.environment.settings.runs_dir",
        runs_dir,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")

    result = build_minimal_environment(
        profile=profile,
        action=action,
        run_dir=run_dir,
        execution_id="exec-1",
    )

    assert "OPENAI_API_KEY" not in result.env
    assert result.env["OMP_NUM_THREADS"] == "2"
    assert result.env["HOME"].startswith(str(run_dir))


def test_action_cannot_override_unapproved_env(
    tmp_path,
    monkeypatch,
) -> None:
    profile = _profile(tmp_path)
    action = _action(profile).model_copy(
        update={"env_overrides": {"UNAPPROVED": "1"}}
    )
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    run_dir.mkdir(parents=True)
    monkeypatch.setattr(
        "app.execution.environment.settings.runs_dir",
        runs_dir,
    )

    with pytest.raises(ValueError, match="未被 profile 允许"):
        build_minimal_environment(
            profile=profile,
            action=action,
            run_dir=run_dir,
            execution_id="exec-1",
        )
```

新增 `tests/test_action_capability_policy.py`：

```python
from app.execution.capability_policy import (
    evaluate_action_capabilities,
)
from app.schemas import ExecutionProfile


def _action(workspace, **updates) -> dict:
    action = {
        "action_id": "action-1",
        "program": "python",
        "args": ["train.py"],
        "cwd": str(workspace),
        "source": "script",
        "reason": "test",
        "writable_paths": [str(workspace)],
        "network_access": "none",
        "execution_profile_id": "test",
        "execution_profile_fingerprint": "hash",
    }
    action.update(updates)
    return action


def _profile(tmp_path) -> ExecutionProfile:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    return ExecutionProfile(
        profile_id="test",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "runs"),
        writable_roots=[str(workspace)],
        allowed_programs=["python"],
        network_policy="deny",
    )


def test_policy_rejects_network_when_profile_denies(
    tmp_path,
) -> None:
    profile = _profile(tmp_path)
    decision = evaluate_action_capabilities(
        raw_action=_action(
            profile.workspace_root,
            network_access="outbound",
        ),
        profile=profile,
    )

    assert decision.allowed is False
    assert any(
        item.code == "NETWORK_NOT_ALLOWED"
        for item in decision.violations
    )


def test_policy_rejects_writable_path_escape(tmp_path) -> None:
    profile = _profile(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    decision = evaluate_action_capabilities(
        raw_action=_action(
            profile.workspace_root,
            writable_paths=[str(outside)],
        ),
        profile=profile,
    )

    assert decision.allowed is False
    assert any(
        item.code == "WRITABLE_PATH_NOT_ALLOWED"
        for item in decision.violations
    )


def test_action_budget_cannot_expand_profile(tmp_path) -> None:
    profile = _profile(tmp_path)
    decision = evaluate_action_capabilities(
        raw_action=_action(
            profile.workspace_root,
            resource_budget={"max_processes": 1000},
        ),
        profile=profile,
    )

    assert decision.allowed is False
    assert any(
        item.code == "RESOURCE_BUDGET_EXPANSION"
        for item in decision.violations
    )
```

运行：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m pytest \
  tests/test_minimal_execution_environment.py \
  tests/test_action_capability_policy.py \
  tests/test_execution_profile_hash.py \
  tests/test_structured_action_and_approval_hash.py
```

---

## 十六、设计跨进程取消协议

### 16.1 为什么不能只用内存里的 Event

`threading.Event` 只能在同一个 Python 进程内使用，而实际场景通常是：

```text
终端 A：python -m app.main run-graph ...
终端 B：python -m app.main cancel-run --thread-id ...
```

所以取消请求必须落在当前 run 中：

```text
runs/<run_id>/execution/control/
├── <execution_id>.runtime.json
└── <execution_id>.cancel.json
```

Supervisor 是唯一负责发送信号的一方。`cancel-run` 只写请求文件，不能直接根据一个
可能过期的 PID 调用 `kill`。

### 16.2 增加 CancellationRequest Schema

在 `app/schemas.py` 的 `ProcessRecord` 前增加：

```python
class CancellationRequest(BaseModel):
    execution_id: str
    requested_at: str
    requested_by: str = "cli"
    reason: str
```

同时给前面的 `ProcessRecord` 增加：

```text
combined_log_path: str
```

给 `ExecutionResult` 增加：

```text
combined_log_path: str | None = None
```

### 16.3 新增 cancellation.py

新增 `app/execution/cancellation.py`：

```python
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.schemas import CancellationRequest


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_control_dir(run_dir: str | Path) -> Path:
    run_root = Path(run_dir).resolve()
    runs_root = settings.runs_dir.resolve()
    if run_root == runs_root or runs_root not in run_root.parents:
        raise ValueError(f"run_dir 不在 RUNS_DIR 内：{run_root}")

    control_dir = (run_root / "execution" / "control").resolve()
    if run_root not in control_dir.parents:
        raise ValueError("control 目录逃逸当前 run")
    control_dir.mkdir(parents=True, exist_ok=True)
    return control_dir


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )
    data = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n"
    ).encode("utf-8")

    try:
        with temp_path.open("xb") as file_obj:
            file_obj.write(data)
            file_obj.flush()
            os.fsync(file_obj.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def runtime_record_path(
    run_dir: str | Path,
    execution_id: str,
) -> Path:
    if not execution_id or Path(execution_id).name != execution_id:
        raise ValueError(f"无效 execution_id：{execution_id!r}")
    return require_control_dir(run_dir) / (
        f"{execution_id}.runtime.json"
    )


def cancel_request_path(
    run_dir: str | Path,
    execution_id: str,
) -> Path:
    if not execution_id or Path(execution_id).name != execution_id:
        raise ValueError(f"无效 execution_id：{execution_id!r}")
    return require_control_dir(run_dir) / (
        f"{execution_id}.cancel.json"
    )


def write_runtime_record(
    *,
    run_dir: str | Path,
    execution_id: str,
    payload: dict[str, Any],
) -> Path:
    path = runtime_record_path(run_dir, execution_id)
    _atomic_write_json(path, payload)
    return path


def read_cancel_request(
    *,
    run_dir: str | Path,
    execution_id: str,
) -> CancellationRequest | None:
    path = cancel_request_path(run_dir, execution_id)
    if not path.is_file():
        return None
    return CancellationRequest.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def list_runtime_records(
    run_dir: str | Path,
) -> list[dict[str, Any]]:
    control_dir = require_control_dir(run_dir)
    records: list[dict[str, Any]] = []
    for path in sorted(control_dir.glob("*.runtime.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        payload["runtime_record_path"] = str(path)
        records.append(payload)
    return records


def request_run_cancellation(
    *,
    run_dir: str | Path,
    reason: str,
    requested_by: str = "cli",
) -> CancellationRequest:
    """
    找到当前 run 唯一的 running/starting execution 并写取消请求。

    如果存在多个活动记录，fail closed，要求人工先诊断，不能猜 PID。
    """

    active = [
        item
        for item in list_runtime_records(run_dir)
        if item.get("status") in {"starting", "running", "terminating"}
    ]
    if not active:
        raise ValueError("当前 run 没有活动中的受监管进程")
    if len(active) != 1:
        raise ValueError(
            "当前 run 存在多个活动进程记录，拒绝猜测取消目标"
        )

    execution_id = str(active[0].get("execution_id") or "")
    if not execution_id:
        raise ValueError("活动进程记录缺少 execution_id")

    request = CancellationRequest(
        execution_id=execution_id,
        requested_at=utc_now(),
        requested_by=requested_by[:100],
        reason=(reason.strip() or "user requested cancellation")[:500],
    )
    _atomic_write_json(
        cancel_request_path(run_dir, execution_id),
        request.model_dump(),
    )
    return request
```

### 16.4 control record 与 Artifact 的区别

运行中的 `*.runtime.json` 会被频繁覆盖，它不是不可变 Artifact。

正确生命周期是：

```text
运行中：execution/control/<id>.runtime.json
结束后：execution/<stage>_process_record.json
结束后 final record 才登记 ArtifactRecord + SHA-256
```

取消请求可以在结束后登记为审计 Artifact，但不得把运行中的 runtime record 当成稳定
hash 的 Artifact。

---

## 十七、日志必须流式读取且有界

Supervisor 使用三份文件：

```text
execution/<stage>.stdout.log
execution/<stage>.stderr.log
execution/<stage>.combined.log
```

规则：

```text
stdout/stderr pipe 必须持续 drain，防止子进程因 pipe 满而阻塞
每个原始 stream 最多写 max_log_bytes_per_stream
超过上限后继续读取但丢弃，不再增长磁盘文件
preview 只保留 max_preview_bytes
combined log 上限为两个 stream 上限之和
日志到达上限默认不杀进程，由 wall time 和资源预算继续监管
```

新增下面的内部类到 `app/execution/process_supervisor.py`：

```python
from pathlib import Path


class BoundedLogSink:
    """持续统计全部字节，但只保存有界文件和有界 preview。"""

    def __init__(
        self,
        *,
        path: Path,
        max_file_bytes: int,
        max_preview_bytes: int,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.max_file_bytes = max_file_bytes
        self.max_preview_bytes = max_preview_bytes
        self.bytes_seen = 0
        self.bytes_written = 0
        self.preview = bytearray()
        self.truncated = False
        self._file = path.open("wb")

    def consume(self, data: bytes) -> None:
        if not data:
            return

        self.bytes_seen += len(data)

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

        if self.bytes_seen > self.max_file_bytes:
            self.truncated = True

    def close(self) -> None:
        if self._file.closed:
            return
        self._file.flush()
        os.fsync(self._file.fileno())
        self._file.close()

    def preview_text(self) -> str:
        return bytes(self.preview).decode(
            "utf-8",
            errors="replace",
        )
```

不要使用：

```python
process.stdout.read()
```

因为它会一直等到 EOF，也会重新把全部日志读进内存。

Supervisor 后面使用 `selectors` 和 `os.read(fd, 64 * 1024)` 增量 drain。

---

## 十八、实现进程树资源采样

在 `app/execution/process_supervisor.py` 中增加：

```python
from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import psutil

from app.execution.cancellation import (
    read_cancel_request,
    write_runtime_record,
)
from app.schemas import (
    ExecutionResult,
    ProcessRecord,
    ResourceBudget,
    ResourceUsage,
)


@dataclass(frozen=True)
class SupervisedExecutionRequest:
    host_command: list[str]
    cwd: Path
    env: dict[str, str]
    run_dir: Path
    action_id: str
    stage: str
    profile_id: str
    backend: str
    budget: ResourceBudget


class ProcessTreeSampler:
    """
    采样 root process 及其递归子进程。

    CPU 和 write bytes 按 (pid, create_time) 保存历史最大值，避免短命子进程
    退出后累计量突然下降，也避免 PID 复用混在同一条记录里。
    """

    def __init__(self) -> None:
        self.peak_rss_bytes = 0
        self.peak_process_count = 0
        self._cpu_by_identity: dict[
            tuple[int, float], float
        ] = {}
        self._write_by_identity: dict[
            tuple[int, float], int
        ] = {}
        self.samples = 0

    def sample(self, root_pid: int) -> ResourceUsage:
        try:
            root = psutil.Process(root_pid)
            processes = [root, *root.children(recursive=True)]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            processes = []

        current_rss = 0
        current_count = 0
        for process in processes:
            try:
                identity = (
                    process.pid,
                    process.create_time(),
                )
                current_rss += process.memory_info().rss
                current_count += 1

                cpu = process.cpu_times()
                cpu_seconds = float(cpu.user + cpu.system)
                self._cpu_by_identity[identity] = max(
                    self._cpu_by_identity.get(identity, 0.0),
                    cpu_seconds,
                )

                try:
                    write_bytes = int(
                        process.io_counters().write_bytes
                    )
                except (AttributeError, NotImplementedError):
                    write_bytes = 0
                self._write_by_identity[identity] = max(
                    self._write_by_identity.get(identity, 0),
                    write_bytes,
                )
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        self.peak_rss_bytes = max(
            self.peak_rss_bytes,
            current_rss,
        )
        self.peak_process_count = max(
            self.peak_process_count,
            current_count,
        )
        self.samples += 1

        return ResourceUsage(
            peak_rss_bytes=self.peak_rss_bytes,
            peak_process_count=self.peak_process_count,
            total_cpu_seconds=sum(self._cpu_by_identity.values()),
            total_write_bytes=sum(
                self._write_by_identity.values()
            ),
            peak_gpu_memory_bytes=None,
            samples=self.samples,
        )


def budget_end_reason(
    usage: ResourceUsage,
    budget: ResourceBudget,
) -> str | None:
    if (
        budget.max_memory_bytes is not None
        and usage.peak_rss_bytes > budget.max_memory_bytes
    ):
        return "memory_limit"

    if usage.peak_process_count > budget.max_processes:
        return "process_limit"

    if (
        budget.max_cpu_seconds is not None
        and usage.total_cpu_seconds > budget.max_cpu_seconds
    ):
        return "cpu_limit"

    if (
        budget.max_write_bytes is not None
        and usage.total_write_bytes > budget.max_write_bytes
    ):
        return "write_limit"

    return None
```

### 18.1 各预算的强度

| 预算 | local/conda 第一版语义 |
|---|---|
| wall time | Supervisor 强制终止进程组 |
| CPU seconds | 轮询进程树，超限后终止 |
| RSS memory | 轮询进程树，超限后终止 |
| process count | 轮询递归子进程数量，超限后终止 |
| write bytes | 根据进程 I/O 计数近似监管 |
| log bytes | 写文件时硬截断，仍持续 drain pipe |
| GPU memory | 只建模；没有可靠监控器时执行前拒绝该预算 |
| network/filesystem | local/conda 只做声明策略，不是 OS 强制隔离 |

`max_write_bytes` 不是文件系统 quota。下面这些情况可能使数值与文件大小不同：

```text
page cache
重复覆盖同一文件
memory-mapped I/O
短命子进程
不同内核的 psutil 支持差异
```

因此 Process Record 中应标记：

```text
write_budget_enforcement=observed_io_best_effort
```

如果 `profile.budget.max_gpu_memory_bytes` 非空，但当前 Runner 没有 GPU monitor，
Capability Policy 或 preflight 必须返回 `GPU_BUDGET_UNSUPPORTED`，不能忽略预算后
继续执行。

---

## 十九、进程组终止语义

继续在 `process_supervisor.py` 增加：

```python
def _signal_process_group(pgid: int, sig: int) -> None:
    """只接受 Supervisor 自己创建并记录的 PGID。"""

    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        return


def _drain_ready_streams(
    *,
    selector: selectors.BaseSelector,
    sinks: dict[str, BoundedLogSink],
    combined_sink: BoundedLogSink,
    timeout: float,
) -> None:
    for key, _ in selector.select(timeout):
        stream_name = str(key.data)
        try:
            data = os.read(key.fd, 64 * 1024)
        except BlockingIOError:
            continue

        if not data:
            try:
                selector.unregister(key.fileobj)
            except KeyError:
                pass
            continue

        sinks[stream_name].consume(data)
        combined_sink.consume(
            f"[{stream_name}]\n".encode("utf-8") + data
        )


def _terminate_process_group(
    *,
    process: subprocess.Popen[bytes],
    pgid: int,
    selector: selectors.BaseSelector,
    sinks: dict[str, BoundedLogSink],
    combined_sink: BoundedLogSink,
    grace_seconds: float,
) -> bool:
    """
    先 SIGTERM，继续 drain 日志；宽限期后仍存活则 SIGKILL。

    返回 True 表示使用过 hard kill。
    """

    if process.poll() is not None:
        return False

    _signal_process_group(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while process.poll() is None and time.monotonic() < deadline:
        _drain_ready_streams(
            selector=selector,
            sinks=sinks,
            combined_sink=combined_sink,
            timeout=0.05,
        )

    if process.poll() is not None:
        return False

    _signal_process_group(pgid, signal.SIGKILL)
    return True
```

### 19.1 为什么使用 `start_new_session=True`

启动时：

```python
import subprocess


process = subprocess.Popen(
    command,
    start_new_session=True,
)
```

在 Linux 上会让目标进程成为新 session 和新 process group 的 leader：

```text
pid == pgid
```

后续 `os.killpg(pgid, SIGTERM)` 才能覆盖训练脚本创建的 DataLoader worker、
torchrun worker 和其他孙进程。

不能只调用：

```python
process.terminate()
```

因为它只针对直接子进程。

### 19.2 PID 复用保护

运行时记录必须同时保存：

```text
pid
pgid
psutil.Process(pid).create_time()
execution_id
run_id
```

外部 CLI 不直接发送信号。Supervisor 发送信号前使用自己持有的 `Popen` 对象，
避免只根据磁盘中的旧 PID 杀到后来复用这个 PID 的无关进程。

---

## 二十、实现完整 ProcessSupervisor

### 20.1 先补充两个 Schema 字段

把 `orphan_cleanup` 加入 `ExecutionEndReason`：

```text
"orphan_cleanup"
```

给 `ProcessRecord` 增加以下字段：

```text
combined_log_path: str
inherited_env_keys: list[str] = Field(default_factory=list)
profile_env_keys: list[str] = Field(default_factory=list)
action_env_keys: list[str] = Field(default_factory=list)
```

只记录环境变量名称，不记录完整环境变量值。

把 `app/execution/cancellation.py` 中的 `_atomic_write_json` 重命名为
`atomic_write_json`，并同步修改该文件内部调用。Supervisor 需要复用同一个原子写函数。

### 20.2 完整 Supervisor

把前面各辅助类和下面的 `ProcessSupervisor` 放在同一个
`app/execution/process_supervisor.py` 中。下面代码是核心执行循环：

```python
class ProcessSupervisor:
    """在当前 Agent 进程中同步监管一个独立进程组。"""

    def execute(
        self,
        request: SupervisedExecutionRequest,
        *,
        inherited_env_keys: list[str] | None = None,
        profile_env_keys: list[str] | None = None,
        action_env_keys: list[str] | None = None,
    ) -> ExecutionResult:
        if os.name != "posix":
            raise RuntimeError(
                "Phase 16 ProcessSupervisor 第一版只支持 POSIX"
            )
        if not request.host_command:
            raise ValueError("host_command 不能为空")
        if not request.stage.replace("_", "").isalnum():
            raise ValueError(f"无效执行 stage：{request.stage}")

        execution_id = f"exec_{uuid4().hex[:16]}"
        run_root = request.run_dir.resolve()
        attempt_dir = (
            run_root
            / "execution"
            / "attempts"
            / execution_id
        ).resolve()
        if run_root not in attempt_dir.parents:
            raise ValueError("execution attempt 目录逃逸当前 run")
        attempt_dir.mkdir(parents=True, exist_ok=False)

        stdout_path = attempt_dir / "stdout.log"
        stderr_path = attempt_dir / "stderr.log"
        combined_path = attempt_dir / "combined.log"
        process_record_path = attempt_dir / "process_record.json"

        stdout_sink = BoundedLogSink(
            path=stdout_path,
            max_file_bytes=(
                request.budget.max_log_bytes_per_stream
            ),
            max_preview_bytes=request.budget.max_preview_bytes,
        )
        stderr_sink = BoundedLogSink(
            path=stderr_path,
            max_file_bytes=(
                request.budget.max_log_bytes_per_stream
            ),
            max_preview_bytes=request.budget.max_preview_bytes,
        )
        combined_sink = BoundedLogSink(
            path=combined_path,
            max_file_bytes=(
                request.budget.max_log_bytes_per_stream * 2
            ),
            max_preview_bytes=(
                request.budget.max_preview_bytes * 2
            ),
        )
        sinks = {
            "stdout": stdout_sink,
            "stderr": stderr_sink,
        }

        started_wall = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()
        record = ProcessRecord(
            execution_id=execution_id,
            action_id=request.action_id,
            stage=request.stage,
            profile_id=request.profile_id,
            backend=request.backend,
            host_command_preview=_redact_command_tokens(
                request.host_command
            ),
            cwd=str(request.cwd),
            started_at=started_at,
            status="starting",
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            combined_log_path=str(combined_path),
            resource_budget=request.budget,
            inherited_env_keys=sorted(
                inherited_env_keys or []
            ),
            profile_env_keys=sorted(profile_env_keys or []),
            action_env_keys=sorted(action_env_keys or []),
        )
        write_runtime_record(
            run_dir=run_root,
            execution_id=execution_id,
            payload=record.model_dump(),
        )

        process: subprocess.Popen[bytes] | None = None
        selector = selectors.DefaultSelector()
        sampler = ProcessTreeSampler()
        usage = ResourceUsage()
        end_reason = "supervisor_error"
        cancellation_reason: str | None = None
        hard_kill_used = False
        termination_signal: int | None = None

        try:
            process = subprocess.Popen(
                request.host_command,
                cwd=str(request.cwd),
                env=request.env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                bufsize=0,
                shell=False,
                close_fds=True,
                start_new_session=True,
            )
            assert process.stdout is not None
            assert process.stderr is not None

            os.set_blocking(process.stdout.fileno(), False)
            os.set_blocking(process.stderr.fileno(), False)
            selector.register(
                process.stdout,
                selectors.EVENT_READ,
                data="stdout",
            )
            selector.register(
                process.stderr,
                selectors.EVENT_READ,
                data="stderr",
            )

            pgid = os.getpgid(process.pid)
            create_time = psutil.Process(
                process.pid
            ).create_time()
            record = record.model_copy(
                update={
                    "pid": process.pid,
                    "pgid": pgid,
                    "process_create_time": create_time,
                    "status": "running",
                }
            )
            write_runtime_record(
                run_dir=run_root,
                execution_id=execution_id,
                payload=record.model_dump(),
            )

            parent_exit_seen_at: float | None = None
            while True:
                _drain_ready_streams(
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    timeout=(
                        request.budget.sample_interval_seconds
                    ),
                )

                returncode = process.poll()
                group_alive = _process_group_exists(pgid)

                if returncode is not None:
                    if not group_alive:
                        end_reason = "exited"
                        break

                    if parent_exit_seen_at is None:
                        parent_exit_seen_at = time.monotonic()
                    elif (
                        time.monotonic() - parent_exit_seen_at
                        >= request.budget.terminate_grace_seconds
                    ):
                        end_reason = "orphan_cleanup"
                        break

                if returncode is None:
                    usage = sampler.sample(process.pid)
                    limited = budget_end_reason(
                        usage,
                        request.budget,
                    )
                    if limited is not None:
                        end_reason = limited
                        break

                cancel_request = read_cancel_request(
                    run_dir=run_root,
                    execution_id=execution_id,
                )
                if cancel_request is not None:
                    end_reason = "cancelled"
                    cancellation_reason = cancel_request.reason
                    break

                elapsed = time.monotonic() - started_wall
                if (
                    elapsed
                    > request.budget.max_wall_time_seconds
                ):
                    end_reason = "timeout"
                    break

            if (
                end_reason != "exited"
                and _process_group_exists(pgid)
            ):
                record = record.model_copy(
                    update={"status": "terminating"}
                )
                write_runtime_record(
                    run_dir=run_root,
                    execution_id=execution_id,
                    payload=record.model_dump(),
                )
                hard_kill_used = _terminate_process_group_final(
                    process=process,
                    pgid=pgid,
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    grace_seconds=(
                        request.budget.terminate_grace_seconds
                    ),
                )
                termination_signal = (
                    signal.SIGKILL
                    if hard_kill_used
                    else signal.SIGTERM
                )

            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                if _process_group_exists(pgid):
                    _signal_process_group(pgid, signal.SIGKILL)
                    hard_kill_used = True
                    termination_signal = signal.SIGKILL
                process.wait(timeout=2)

            # 进程结束后再短暂 drain，拿到 pipe 中已经产生的尾部日志。
            drain_deadline = time.monotonic() + 1.0
            while selector.get_map() and time.monotonic() < drain_deadline:
                _drain_ready_streams(
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    timeout=0.05,
                )

            usage = sampler.sample(process.pid)

        except KeyboardInterrupt:
            end_reason = "interrupted"
            cancellation_reason = "Agent received KeyboardInterrupt"
            if process is not None and process.pid:
                try:
                    pgid = os.getpgid(process.pid)
                except ProcessLookupError:
                    pgid = process.pid
                hard_kill_used = _terminate_process_group_final(
                    process=process,
                    pgid=pgid,
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    grace_seconds=(
                        request.budget.terminate_grace_seconds
                    ),
                )
                termination_signal = (
                    signal.SIGKILL
                    if hard_kill_used
                    else signal.SIGTERM
                )

        except OSError as exc:
            end_reason = "launch_error"
            error_bytes = str(exc).encode(
                "utf-8",
                errors="replace",
            )
            stderr_sink.consume(error_bytes)
            combined_sink.consume(b"[stderr]\n" + error_bytes)

        except Exception as exc:
            # Supervisor 自己失败也必须先清理已启动的进程组。
            end_reason = "supervisor_error"
            error_bytes = (
                f"{type(exc).__name__}: {exc}"
            ).encode("utf-8", errors="replace")
            stderr_sink.consume(error_bytes)
            combined_sink.consume(b"[stderr]\n" + error_bytes)

            if process is not None and process.poll() is None:
                try:
                    pgid = os.getpgid(process.pid)
                except ProcessLookupError:
                    pgid = process.pid
                hard_kill_used = _terminate_process_group_final(
                    process=process,
                    pgid=pgid,
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    grace_seconds=(
                        request.budget.terminate_grace_seconds
                    ),
                )
                termination_signal = (
                    signal.SIGKILL
                    if hard_kill_used
                    else signal.SIGTERM
                )

        finally:
            selector.close()
            for sink in (
                stdout_sink,
                stderr_sink,
                combined_sink,
            ):
                sink.close()

        finished_at = datetime.now(timezone.utc).isoformat()
        duration = time.monotonic() - started_wall
        returncode = (
            process.returncode
            if process is not None
            else None
        )
        if process is not None and usage.samples == 0:
            usage = sampler.sample(process.pid)

        record = record.model_copy(
            update={
                "status": "finished",
                "finished_at": finished_at,
                "duration_seconds": duration,
                "end_reason": end_reason,
                "returncode": returncode,
                "termination_signal": termination_signal,
                "hard_kill_used": hard_kill_used,
                "stdout_bytes_seen": stdout_sink.bytes_seen,
                "stderr_bytes_seen": stderr_sink.bytes_seen,
                "stdout_bytes_written": stdout_sink.bytes_written,
                "stderr_bytes_written": stderr_sink.bytes_written,
                "stdout_truncated": stdout_sink.truncated,
                "stderr_truncated": stderr_sink.truncated,
                "cancellation_requested": (
                    end_reason in {"cancelled", "interrupted"}
                ),
                "cancellation_reason": cancellation_reason,
                "resource_usage": usage,
            }
        )

        atomic_write_json(
            process_record_path,
            record.model_dump(),
        )
        write_runtime_record(
            run_dir=run_root,
            execution_id=execution_id,
            payload=record.model_dump(),
        )

        stdout_preview = stdout_sink.preview_text()
        stderr_preview = stderr_sink.preview_text()
        combined_preview = combined_sink.preview_text()
        ok = end_reason == "exited" and returncode == 0

        return ExecutionResult(
            ok=ok,
            returncode=returncode,
            end_reason=end_reason,
            stdout=stdout_preview,
            stderr=stderr_preview,
            combined_output=combined_preview,
            timeout=end_reason == "timeout",
            cancelled=end_reason in {"cancelled", "interrupted"},
            log_truncated=(
                stdout_sink.truncated
                or stderr_sink.truncated
                or combined_sink.truncated
            ),
            execution_id=execution_id,
            execution_profile_id=request.profile_id,
            execution_backend=request.backend,
            cwd=str(request.cwd),
            process_record_path=str(process_record_path),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            combined_log_path=str(combined_path),
            resource_usage=usage,
        )
```

### 20.3 Supervisor 依赖的最终辅助函数

在 `process_supervisor.py` 顶部的 cancellation import 中加入
`atomic_write_json`，并增加以下函数。这个 `_terminate_process_group_final()` 是最终版本，
它会处理“父进程已退出但 PGID 仍有 worker”的情况：

```python
SENSITIVE_ARG_NAMES = {
    "--api-key",
    "--api_key",
    "--token",
    "--password",
    "--secret",
}


def _redact_command_tokens(tokens: list[str]) -> list[str]:
    """Process Record 保留命令结构，但隐藏常见 secret 参数值。"""

    result: list[str] = []
    redact_next = False
    for token in tokens:
        lowered = token.lower()
        if redact_next:
            result.append("<redacted>")
            redact_next = False
            continue

        if lowered in SENSITIVE_ARG_NAMES:
            result.append(token)
            redact_next = True
            continue

        matched_assignment = False
        for name in SENSITIVE_ARG_NAMES:
            prefix = name + "="
            if lowered.startswith(prefix):
                result.append(token[: len(prefix)] + "<redacted>")
                matched_assignment = True
                break
        if not matched_assignment:
            result.append(token)

    return result


def _process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # PGID 存在但当前用户无法发信号，也不能假装已经结束。
        return True
    return True


def _terminate_process_group_final(
    *,
    process: subprocess.Popen[bytes],
    pgid: int,
    selector: selectors.BaseSelector,
    sinks: dict[str, BoundedLogSink],
    combined_sink: BoundedLogSink,
    grace_seconds: float,
) -> bool:
    """
    即使 group leader 已经退出，也检查并终止仍存活的 PGID。

    返回 True 表示最终使用了 SIGKILL。
    """

    if not _process_group_exists(pgid):
        return False

    _signal_process_group(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while _process_group_exists(pgid) and time.monotonic() < deadline:
        _drain_ready_streams(
            selector=selector,
            sinks=sinks,
            combined_sink=combined_sink,
            timeout=0.05,
        )
        if process.poll() is None:
            process.poll()

    if not _process_group_exists(pgid):
        return False

    _signal_process_group(pgid, signal.SIGKILL)
    return True
```

### 20.4 对完整代码做两点说明

第一，前面展示的 `_terminate_process_group()` 是讲解过程，最终源文件只保留
`_terminate_process_group_final()`，不要同时维护两个版本。

第二，`ProcessSupervisor.execute()` 捕获 `supervisor_error` 是为了先完成进程清理和
Process Record。上层 executor 看到该 `end_reason` 后必须生成 terminal Agent
`StageError`，不能把它归类为论文程序失败。

### 20.5 为什么日志路径包含 execution_id

不要固定写：

```text
execution/execution.log
```

因为同一个 run 可能经历：

```text
smoke attempt 1
command repair
smoke attempt 2
full execution
```

使用：

```text
execution/attempts/<execution_id>/...
```

可以保留所有尝试，Manifest 也不会因 upsert 同名路径丢失历史。

### 20.6 GPU Budget 的第一版策略

在 `evaluate_action_capabilities()` 得到 `effective_budget` 后增加：

```python
if (
    effective_budget.max_gpu_memory_bytes is not None
    and profile.backend in {"local", "conda"}
):
    violations.append(
        _violation(
            "GPU_BUDGET_UNSUPPORTED",
            "resource_budget.max_gpu_memory_bytes",
            "当前 local/conda runner 没有可靠 GPU memory enforcer",
        )
    )
```

以后接入 NVML 时，也应区分：

```text
observed：只能报告峰值
best_effort：采样超限后终止
hard_limit：由容器/cgroup/MIG 等机制强制
```

不要把“读取了 nvidia-smi”写成“GPU 已强隔离”。

---

## 二十一、重构 ExecutionRunner

用下面的结构替换 `app/execution/base.py`。`BoundedLogSink`、Supervisor 和环境构建
不应复制到 LocalRunner/CondaRunner 中：

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.execution.capability_policy import (
    evaluate_action_capabilities,
)
from app.execution.environment import build_minimal_environment
from app.execution.process_supervisor import (
    ProcessSupervisor,
    SupervisedExecutionRequest,
)
from app.schemas import (
    ExecutableAction,
    ExecutionProfile,
    ResourceBudget,
)


class ExecutionRunner(ABC):
    def __init__(self, profile: ExecutionProfile):
        self.profile = profile
        self.supervisor = ProcessSupervisor()

    @abstractmethod
    def build_host_command(
        self,
        program: str,
        args: list[str],
    ) -> list[str]:
        """把目标命令转换成宿主机实际启动的 token 列表。"""

    def validate_cwd(self, cwd: str) -> Path:
        workspace_root = Path(
            self.profile.workspace_root
        ).resolve()
        resolved_cwd = Path(cwd).expanduser().resolve()
        if (
            resolved_cwd != workspace_root
            and workspace_root not in resolved_cwd.parents
        ):
            raise ValueError(
                f"cwd 位于执行工作区之外：{resolved_cwd}"
            )
        if not resolved_cwd.is_dir():
            raise FileNotFoundError(
                f"执行 cwd 不存在：{resolved_cwd}"
            )
        return resolved_cwd

    def run(
        self,
        action: dict[str, Any],
        *,
        run_dir: str,
        stage: str,
    ) -> dict[str, Any]:
        """
        正式 Action 必须重新经过 capability policy。

        risk_check 是面向审批的第一次检查；这里是执行边界的 fail-closed
        第二次检查，防止 state 在审批后被错误修改。
        """

        parsed = ExecutableAction.model_validate(action)
        resolved_cwd = self.validate_cwd(parsed.cwd)
        decision = evaluate_action_capabilities(
            raw_action=parsed.model_dump(),
            profile=self.profile,
        )
        if not decision.allowed:
            message = ", ".join(
                item.code for item in decision.violations
            )
            return {
                "ok": False,
                "returncode": None,
                "end_reason": "policy_denied",
                "stdout": "",
                "stderr": message,
                "combined_output": message,
                "timeout": False,
                "cancelled": False,
                "log_truncated": False,
                "execution_profile_id": self.profile.profile_id,
                "execution_backend": self.profile.backend,
                "cwd": str(resolved_cwd),
                "resource_usage": {},
            }

        execution_id = f"env_{uuid4().hex[:16]}"
        env_result = build_minimal_environment(
            profile=self.profile,
            action=parsed,
            run_dir=run_dir,
            execution_id=execution_id,
        )
        host_command = self.build_host_command(
            parsed.program,
            parsed.args,
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
            ),
            inherited_env_keys=env_result.inherited_keys,
            profile_env_keys=env_result.profile_keys,
            action_env_keys=env_result.action_keys,
        )
        return result.model_dump()

    def probe(
        self,
        *,
        program: str,
        args: list[str],
        cwd: str,
        run_dir: str,
        stage: str,
        timeout_seconds: int = 15,
    ) -> dict[str, Any]:
        """
        受信任的内部探测也使用最小环境和 Supervisor。

        probe 不是 LLM Action，所以不走 DYNAMIC_CODE_FLAGS；但 program、cwd、
        profile 和预算都由 Agent 确定，不能接受用户提供的任意 shell 字符串。
        """

        resolved_cwd = self.validate_cwd(cwd)
        probe_action = ExecutableAction(
            action_id=f"probe_{uuid4().hex[:12]}",
            program=program,
            args=args,
            cwd=str(resolved_cwd),
            source="inferred",
            reason=f"internal probe: {stage}",
            timeout_seconds=timeout_seconds,
            env_overrides={},
            writable_paths=[],
            network_access="none",
            execution_profile_id=self.profile.profile_id,
            execution_profile_fingerprint="internal-probe",
        )
        env_result = build_minimal_environment(
            profile=self.profile,
            action=probe_action,
            run_dir=run_dir,
            execution_id=f"env_{uuid4().hex[:16]}",
        )
        budget = self.profile.budget.model_copy(
            update={
                "max_wall_time_seconds": min(
                    float(timeout_seconds),
                    self.profile.budget.max_wall_time_seconds,
                ),
                "max_log_bytes_per_stream": min(
                    1024 * 1024,
                    self.profile.budget.max_log_bytes_per_stream,
                ),
                "max_preview_bytes": min(
                    64 * 1024,
                    self.profile.budget.max_preview_bytes,
                ),
            }
        )
        result = self.supervisor.execute(
            SupervisedExecutionRequest(
                host_command=self.build_host_command(
                    program,
                    args,
                ),
                cwd=resolved_cwd,
                env=env_result.env,
                run_dir=Path(run_dir).resolve(),
                action_id=probe_action.action_id,
                stage=stage,
                profile_id=self.profile.profile_id,
                backend=self.profile.backend,
                budget=budget,
            ),
            inherited_env_keys=env_result.inherited_keys,
            profile_env_keys=env_result.profile_keys,
            action_env_keys=[],
        )
        return result.model_dump()

    def which(
        self,
        program: str,
        cwd: str,
        *,
        run_dir: str,
    ) -> tuple[str | None, dict[str, Any]]:
        """在目标环境中解析程序，并返回对应 probe result。"""

        script = (
            "import shutil, sys; "
            "resolved = shutil.which(sys.argv[1]); "
            "print(resolved or '')"
        )
        result = self.probe(
            program="python",
            args=["-c", script, program],
            cwd=cwd,
            run_dir=run_dir,
            stage="preflight_which",
            timeout_seconds=15,
        )
        if not result["ok"]:
            return None, result
        resolved = result["stdout"].strip()
        return resolved or None, result
```

### 21.1 LocalRunner 保持简单

`app/execution/local_runner.py`：

```python
from app.execution.base import ExecutionRunner


class LocalRunner(ExecutionRunner):
    """宿主机执行后端；监管和安全环境由基类统一提供。"""

    def build_host_command(
        self,
        program: str,
        args: list[str],
    ) -> list[str]:
        return [program, *args]
```

### 21.2 CondaRunner 只负责命令封装

`app/execution/conda_runner.py`：

```python
from pathlib import Path

from app.execution.base import ExecutionRunner


class CondaRunner(ExecutionRunner):
    """通过 conda run -p 执行，使用与 LocalRunner 相同的 Supervisor。"""

    def build_host_command(
        self,
        program: str,
        args: list[str],
    ) -> list[str]:
        conda_executable = self.profile.conda_executable
        conda_prefix = self.profile.conda_prefix
        if not conda_executable or not conda_prefix:
            raise ValueError("conda 执行环境配置不完整")

        executable_path = Path(conda_executable).resolve()
        prefix_path = Path(conda_prefix).resolve()
        if not executable_path.is_file():
            raise FileNotFoundError(
                f"conda executable 不存在：{executable_path}"
            )
        if not prefix_path.is_dir():
            raise FileNotFoundError(
                f"conda prefix 不存在：{prefix_path}"
            )

        return [
            str(executable_path),
            "run",
            "--no-capture-output",
            "-p",
            str(prefix_path),
            program,
            *args,
        ]
```

`--no-capture-output` 很重要。Conda 不应再做一层内部缓冲，日志应尽快到达
Supervisor 的 pipe。

### 21.3 local/conda 必须共享的语义

| 语义 | LocalRunner | CondaRunner |
|---|---:|---:|
| minimal env | 相同 | 相同 |
| capability policy | 相同 | 相同 |
| process group | 相同 | 相同 |
| stream drain | 相同 | 相同 |
| timeout/cancel | 相同 | 相同 |
| resource budget | 相同 | 相同 |
| Action hash/profile fingerprint | 相同 | 相同 |
| Python/依赖环境 | host PATH | conda prefix |

不要在 CondaRunner 中重新实现 timeout 或日志读取。

### 21.4 统一 execution_id

为了让 HOME、日志、control record 和 Process Record 使用同一个 ID，最终实现时给
`SupervisedExecutionRequest` 增加：

```text
execution_id: str
```

然后把 `ProcessSupervisor.execute()` 内部：

```python
execution_id = f"exec_{uuid4().hex[:16]}"
```

替换为：

```python
execution_id = request.execution_id
```

`ExecutionRunner.run()` 先创建一次：

```python
execution_id = f"exec_{uuid4().hex[:16]}"
```

并同时传给：

```text
build_minimal_environment(execution_id=execution_id)
SupervisedExecutionRequest(execution_id=execution_id, ...)
```

`probe()` 也采用相同方式。不要分别生成 `env_*` 和 `exec_*` 两个 ID。

---

## 二十二、升级 exec_tools

用下面的实现替换 `app/tools/exec_tools.py` 的主流程：

```python
from typing import Any

from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.execution.registry import build_execution_runner


def _execution_failure(
    *,
    message: str,
    end_reason: str,
    profile_id: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "returncode": None,
        "end_reason": end_reason,
        "stdout": "",
        "stderr": message,
        "combined_output": message,
        "timeout": end_reason == "timeout",
        "cancelled": end_reason in {"cancelled", "interrupted"},
        "log_truncated": False,
        "execution_profile_id": profile_id,
        "execution_backend": None,
        "resource_usage": {},
    }


def run_action_safe(
    action: dict,
    *,
    state: dict,
    stage: str,
) -> dict[str, Any]:
    """
    校验 profile 指纹后，把 Action 交给受监管 Runner。

    run_dir 必须来自当前 Graph state，不能回退到 outputs/ 或 profile 的
    artifact_root。
    """

    profile_id = action.get("execution_profile_id")
    if not profile_id:
        return _execution_failure(
            message="缺少 execution_profile_id",
            end_reason="policy_denied",
        )

    run_dir = state.get("run_dir")
    if not run_dir:
        return _execution_failure(
            message="当前 state 缺少 run_dir",
            end_reason="supervisor_error",
            profile_id=profile_id,
        )

    try:
        profile = get_execution_profile(profile_id)
        current_fingerprint = (
            compute_execution_profile_fingerprint(profile)
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return _execution_failure(
            message=str(exc),
            end_reason="launch_error",
            profile_id=profile_id,
        )

    expected_fingerprint = action.get(
        "execution_profile_fingerprint"
    )
    if expected_fingerprint != current_fingerprint:
        return _execution_failure(
            message=(
                "操作创建后执行环境安全配置发生变化；"
                "请重新构建并审批该操作"
            ),
            end_reason="policy_denied",
            profile_id=profile_id,
        )

    runner = build_execution_runner(profile)
    return runner.run(
        action,
        run_dir=str(run_dir),
        stage=stage,
    )
```

### 22.1 为什么 run_action_safe 需要 state

Phase 15 后所有执行 Artifact 都必须属于当前 run，因此旧签名：

```python
run_action_safe(action)
```

不再够用。统一修改为：

```python
run_action_safe(
    action,
    state=state,
    stage="executor",
)
```

Smoke Test 使用：

```python
run_action_safe(
    smoke_action,
    state=state,
    stage="smoke_test",
)
```

---

## 二十三、登记 Supervisor 生成的 Artifact

在 `app/tools/exec_tools.py` 增加：

```python
from app.tools.artifact_tools import register_existing_artifact


def register_execution_artifacts(
    *,
    state: dict,
    result: dict[str, Any],
    producer_node: str,
) -> list:
    """登记 Supervisor 已经完整关闭并 fsync 的执行文件。"""

    candidates = [
        (result.get("stdout_path"), "text/plain"),
        (result.get("stderr_path"), "text/plain"),
        (result.get("combined_log_path"), "text/plain"),
        (
            result.get("process_record_path"),
            "application/json",
        ),
    ]
    records = []
    seen: set[str] = set()
    for raw_path, media_type in candidates:
        if not raw_path or raw_path in seen:
            continue
        seen.add(raw_path)
        records.append(
            register_existing_artifact(
                state=state,
                path=raw_path,
                producer_node=producer_node,
                media_type=media_type,
            )
        )
    return records
```

登记只能发生在 `ProcessSupervisor.execute()` 返回之后，因为此时日志和 Process
Record 已经关闭并稳定，SHA-256 才有意义。

不要在运行中每写一个 chunk 就更新 Artifact hash。

### 23.1 control record 是否登记

建议：

```text
*.runtime.json：不登记，属于运行时可变控制文件
*.cancel.json：执行结束后可以登记，属于用户控制审计事实
process_record.json：必须登记
stdout/stderr/combined.log：必须登记
```

如果没有取消请求，就不要创建空的 cancel Artifact。

---

## 二十四、统一解释 Execution End Reason

Supervisor 只报告事实，不负责决定 Graph 路由。把下面函数增加到
`app/tools/exec_tools.py`：

```python
from app.schemas import StageError
from app.tools.error_tools import build_stage_error


RESOURCE_END_REASONS = {
    "timeout",
    "cpu_limit",
    "memory_limit",
    "process_limit",
    "write_limit",
    "gpu_limit",
}


def build_execution_stage_error(
    *,
    stage: str,
    result: dict[str, Any],
    log_path: str | None,
) -> tuple[StageError, str]:
    """把 Process Supervisor 事实映射到 Phase 15 StageError。"""

    reason = str(result.get("end_reason") or "supervisor_error")
    context = {
        "end_reason": reason,
        "returncode": result.get("returncode"),
        "execution_id": result.get("execution_id"),
        "process_record_path": result.get(
            "process_record_path"
        ),
        "log_path": log_path,
        "resource_usage": result.get("resource_usage", {}),
        "log_truncated": result.get("log_truncated", False),
    }

    if reason == "exited":
        return (
            build_stage_error(
                stage=stage,
                code="PAPER_PROGRAM_NONZERO_EXIT",
                category="paper_program",
                message=(
                    "论文程序返回非零状态："
                    f"{result.get('returncode')}"
                ),
                terminal=False,
                context=context,
            ),
            "failed",
        )

    if reason in RESOURCE_END_REASONS:
        return (
            build_stage_error(
                stage=stage,
                code="PAPER_PROGRAM_RESOURCE_LIMIT",
                category="paper_program",
                message=f"论文程序触发执行预算：{reason}",
                terminal=False,
                context=context,
            ),
            "failed",
        )

    if reason in {"cancelled", "interrupted"}:
        return (
            build_stage_error(
                stage=stage,
                code="EXECUTION_CANCELLED",
                category="user",
                message=f"执行已取消：{reason}",
                terminal=True,
                context=context,
            ),
            "cancelled",
        )

    if reason == "policy_denied":
        return (
            build_stage_error(
                stage=stage,
                code="EXECUTION_POLICY_DENIED",
                category="user",
                message=result.get("stderr") or "执行策略拒绝",
                terminal=True,
                context=context,
            ),
            "policy_blocked",
        )

    if reason == "launch_error":
        return (
            build_stage_error(
                stage=stage,
                code="EXECUTION_LAUNCH_ERROR",
                category="environment",
                message=result.get("stderr") or "子进程启动失败",
                terminal=True,
                context=context,
            ),
            "environment_blocked",
        )

    return (
        build_stage_error(
            stage=stage,
            code="EXECUTION_SUPERVISOR_ERROR",
            category="agent",
            message=(
                result.get("stderr")
                or f"Supervisor 异常结束：{reason}"
            ),
            terminal=True,
            context=context,
        ),
        "agent_failed",
    )
```

### 24.1 为什么资源超限是 non-terminal paper_program

例如：

```text
memory_limit
  -> log_debug 发现 batch size 太大
  -> repair_planner 给出 bounded command repair
  -> 缩小 batch 后重试
```

这仍然是复现闭环的一部分。

但 `cancelled` 不应进入自动修复：用户明确要求停止，Graph 必须进入 Final Report。

`supervisor_error` 也不能进入论文修复，因为这是 Agent 执行基础设施问题。

---

## 二十五、接入 executor_node

保留当前 `executor_node()` 前半段的这些检查：

```text
pending_action 存在
审批 decision 合法
Action type 是 run_command
approved 时 approval_record 存在
approved hash 与当前 action hash 一致
```

修改 imports：

```python
from app.tools.artifact_tools import artifact_state_update
from app.tools.error_tools import persist_stage_errors
from app.tools.exec_tools import (
    build_execution_stage_error,
    register_execution_artifacts,
    run_action_safe,
)
```

删除 executor 中再次调用 `write_text_artifact(...execution.log...)` 的旧代码。增加完整
helper：

```python
def _run_approved_action(
    *,
    state: dict,
    pending_action: dict,
) -> dict:
    result = run_action_safe(
        pending_action,
        state=state,
        stage="executor",
    )
    records = register_execution_artifacts(
        state=state,
        result=result,
        producer_node="executor",
    )
    log_path = result.get("combined_log_path")

    payload = {
        "active_execution_mode": "full",
        "active_execution_id": result.get("execution_id"),
        "active_process_record_path": result.get(
            "process_record_path"
        ),
        "execution_end_reason": result.get("end_reason"),
        "execution_resource_usage": result.get(
            "resource_usage",
            {},
        ),
        "execution_result": result,
        "execution_log_path": log_path,
        "last_action_result": {
            "status": "succeeded" if result["ok"] else "failed",
            "pending_action": pending_action,
            "returncode": result.get("returncode"),
            "end_reason": result.get("end_reason"),
            "execution_id": result.get("execution_id"),
        },
        **artifact_state_update(state, records),
    }

    if result["ok"]:
        return {
            **payload,
            "final_status": "succeeded",
        }

    error, final_status = build_execution_stage_error(
        stage="executor",
        result=result,
        log_path=log_path,
    )
    if log_path:
        payload["log_path"] = log_path

    error_update = persist_stage_errors(
        state={**state, **payload},
        new_errors=[error],
    )
    return {
        **payload,
        **error_update,
        "final_status": final_status,
        "last_action_result": {
            **payload["last_action_result"],
            "status": final_status,
        },
    }
```

原 `executor_node()` 通过所有审批检查后只需要：

```python
return _run_approved_action(
    state=state,
    pending_action=pending_action,
)
```

### 25.1 不要把完整日志放进 checkpoint

`execution_result` 中只有 preview。完整或截断后的日志位于 Artifact：

```text
execution_result.stdout       <= max_preview_bytes
execution_result.stderr       <= max_preview_bytes
execution_result.combined_output <= 2 * max_preview_bytes
```

这样 SQLite checkpoint 不会因为训练日志变成几百 MB。

### 25.2 Process Record 写入 last_action_result

`last_action_result` 至少保存 `execution_id` 和 `end_reason`。不要把完整
Process Record 再复制一遍放入 state；state 只保存路径和关键摘要。

---

## 二十六、接入 smoke_test_node

### 26.1 Smoke Action 也必须保留能力边界

修改 `derive_smoke_test_action()` 时确认它只改变训练规模参数，例如：

```text
--epochs 100 -> 1
--batch_size 8 -> 1
--num_workers 8 -> 0
```

下面这些能力必须保持不变或收紧：

```text
program
cwd
env_overrides
writable_paths
network_access
execution profile id/fingerprint
resource_budget
```

Smoke Action 不得因为“只是测试”而增加网络或可写路径。

### 26.2 替换执行与日志部分

在 `app/nodes/smoke_test_node.py` 中修改 imports：

```python
from app.tools.exec_tools import (
    build_execution_stage_error,
    register_execution_artifacts,
    run_action_safe,
)
```

保留当前的 `pending_action` 检查、`derive_smoke_test_action()` 和 skipped 分支。
把实际运行分支改为：

```python
smoke_action_hash = compute_action_hash(smoke_action)
result = run_action_safe(
    smoke_action,
    state=state,
    stage="smoke_test",
)
records = register_execution_artifacts(
    state=state,
    result=result,
    producer_node="smoke_test",
)
smoke_log_path = result.get("combined_log_path")

status = "passed" if result["ok"] else "failed"
report = build_smoke_test_report(
    action=smoke_action,
    action_hash=smoke_action_hash,
    status=status,
    summary=summary,
    applied_overrides=overrides,
    result=result,
    log_path=smoke_log_path,
)
```

继续使用当前 `write_json_artifact()` 和 `write_text_artifact()` 写 Smoke Report，
但 Artifact 合并必须包含 Supervisor records：

```python
all_records = [
    *records,
    json_record,
    md_record,
]
payload = {
    "active_execution_mode": "smoke",
    "active_execution_id": result.get("execution_id"),
    "active_process_record_path": result.get(
        "process_record_path"
    ),
    "execution_end_reason": result.get("end_reason"),
    "execution_resource_usage": result.get(
        "resource_usage",
        {},
    ),
    "smoke_test_report": report.model_dump(),
    "smoke_test_status": status,
    "smoke_test_passed": status == "passed",
    "smoke_test_log_path": smoke_log_path,
    **artifact_state_update(state, all_records),
}

if status == "passed":
    return payload

error, final_status = build_execution_stage_error(
    stage="smoke_test",
    result=result,
    log_path=smoke_log_path,
)
payload.update(
    {
        "final_status": final_status,
        "last_action_result": {
            "status": final_status,
            "pending_action": smoke_action,
            "returncode": result.get("returncode"),
            "end_reason": result.get("end_reason"),
            "execution_id": result.get("execution_id"),
        },
    }
)
if smoke_log_path:
    payload["log_path"] = smoke_log_path

return {
    **payload,
    **persist_stage_errors(
        state={**state, **payload},
        new_errors=[error],
    ),
    "final_status": final_status,
}
```

### 26.3 timeout 后是否进入 Debug

Smoke Test 触发 `timeout`、`memory_limit` 等资源预算时：

```text
StageError.category=paper_program
StageError.terminal=false
route_after_smoke_test -> log_debug
```

用户取消时：

```text
StageError.category=user
StageError.terminal=true
route_after_smoke_test -> final_report
```

---

## 二十七、接入 Preflight

Preflight 中的 `which`、`python --version`、`import torch` 也必须使用 Supervisor，
否则 secret 和进程残留风险仍然存在。

### 27.1 修改函数签名

把 `app/tools/preflight_tools.py` 中入口改成：

```python
def build_preflight_report(
    action: dict,
    *,
    repo_path: str | None,
    action_hash: str | None,
    run_dir: str,
) -> tuple[PreflightReport, list[dict]]:
    """返回报告和所有内部 probe 的 ExecutionResult。"""
```

所有调用：

```python
runner.probe(
    program=...,
    args=...,
    cwd=...,
    run_dir=run_dir,
    stage="preflight_python_version",
    timeout_seconds=15,
)
```

`runner.which()` 改为：

```python
resolved, which_result = runner.which(
    program,
    cwd,
    run_dir=run_dir,
)
probe_results.append(which_result)
```

其他 probe 也 append 到 `probe_results`，最后：

```python
return report, probe_results
```

### 27.2 修改 preflight_check_node

现有调用改为：

```python
run_dir = state.get("run_dir")
if not run_dir:
    return stage_error_result(
        state=state,
        stage="preflight_check",
        code="RUN_DIR_REQUIRED",
        category="agent",
        message="Preflight 缺少 run_dir",
        extra_update={
            "preflight_passed": False,
            "final_status": "agent_failed",
        },
    )

report, probe_results = build_preflight_report(
    pending_action,
    repo_path=state.get("repo_path"),
    action_hash=action_hash,
    run_dir=run_dir,
)
probe_records = []
for result in probe_results:
    probe_records.extend(
        register_execution_artifacts(
            state=state,
            result=result,
            producer_node="preflight_check",
        )
    )
```

写完 Preflight JSON/Markdown 后：

```python
records = [
    *probe_records,
    json_record,
    md_record,
]
```

再传给：

```python
artifact_state_update(state, records)
```

### 27.3 Preflight 增加能力支持检查

报告中增加：

```text
execution_enforcement_mode
network_os_enforced
writable_paths_os_enforced
resource_monitors_available
process_group_supported
```

local/conda 第一版应诚实报告：

```text
process_group_supported=true
wall/cpu/memory/pid/write/log monitor=true
network_os_enforced=false
writable_paths_os_enforced=false
```

如果产品要求 `strict`，preflight 必须阻断 local/conda，不能降级成 best effort 后
静默继续。

---

## 二十八、增加 show-process 与 cancel-run CLI

修改 `app/main.py` imports：

```python
from app.execution.cancellation import (
    list_runtime_records,
    request_run_cancellation,
)
```

增加 run 目录解析 helper：

```python
def _resolve_run_dir_for_control(
    *,
    run_id: str | None,
    thread_id: str | None,
) -> Path:
    if bool(run_id) == bool(thread_id):
        raise typer.BadParameter(
            "必须且只能提供 --run-id 或 --thread-id"
        )

    if run_id:
        if Path(run_id).name != run_id or run_id in {".", ".."}:
            raise typer.BadParameter("无效 run_id")
        run_dir = (settings.runs_dir / run_id).resolve()
    else:
        graph = build_graph()
        snapshot = graph.get_state(
            {"configurable": {"thread_id": thread_id}}
        )
        raw_run_dir = snapshot.values.get("run_dir")
        if not raw_run_dir:
            raise typer.BadParameter(
                f"thread_id={thread_id} 没有 run_dir"
            )
        run_dir = Path(raw_run_dir).resolve()

    runs_root = settings.runs_dir.resolve()
    if run_dir == runs_root or runs_root not in run_dir.parents:
        raise typer.BadParameter("run_dir 位于 RUNS_DIR 之外")
    if not run_dir.is_dir():
        raise typer.BadParameter(f"run_dir 不存在：{run_dir}")
    return run_dir
```

增加命令：

```python
@app.command("show-process")
def show_process(
    run_id: str | None = typer.Option(None, "--run-id"),
    thread_id: str | None = typer.Option(None, "--thread-id"),
):
    run_dir = _resolve_run_dir_for_control(
        run_id=run_id,
        thread_id=thread_id,
    )
    records = list_runtime_records(run_dir)
    print(
        {
            "run_dir": str(run_dir),
            "processes": records,
        }
    )


@app.command("cancel-run")
def cancel_run(
    reason: str = typer.Option(
        "user requested cancellation",
        "--reason",
    ),
    run_id: str | None = typer.Option(None, "--run-id"),
    thread_id: str | None = typer.Option(None, "--thread-id"),
):
    run_dir = _resolve_run_dir_for_control(
        run_id=run_id,
        thread_id=thread_id,
    )
    try:
        request = request_run_cancellation(
            run_dir=run_dir,
            reason=reason,
            requested_by="cli",
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None

    print(
        {
            "run_dir": str(run_dir),
            "execution_id": request.execution_id,
            "requested_at": request.requested_at,
            "reason": request.reason,
        }
    )
```

### 28.1 cancel-run 的响应语义

CLI 返回只表示：

```text
取消请求已经原子写入当前 run
```

不表示进程已经退出。

用户随后运行：

```bash
python -m app.main show-process --thread-id phase16-demo
```

直到看到：

```text
status=finished
end_reason=cancelled
```

默认延迟约为：

```text
sample_interval_seconds + terminate grace
```

### 28.2 为什么 CLI 不直接 kill

直接 kill 的问题：

```text
磁盘 PID 可能过期
PID 可能已复用
CLI 不持有 Popen
CLI 可能只杀父进程
无法和日志 drain、Process Record 原子收尾协调
```

所以正常取消路径始终是：

```text
CLI 写 request
Supervisor 读取 request
Supervisor 终止自己创建的 PGID
Supervisor 写 final Process Record
Graph 生成 Final Report / Manifest
```

Supervisor 进程自身崩溃后的孤儿回收属于后续 Worker Lease/Reconciler，不要让普通
`cancel-run` 猜测并发送信号。

---

## 二十九、扩展 Run Manifest

修改 `app/tools/artifact_tools.py` 的 `build_run_manifest()`，在返回结构中增加：

```text
"capability_policy": {
    "decision": state.get("capability_decision"),
    "report_path": state.get("capability_report_path"),
},
"execution_supervision": {
    "execution_id": state.get("active_execution_id"),
    "process_record_path": state.get(
        "active_process_record_path"
    ),
    "end_reason": state.get("execution_end_reason"),
    "resource_usage": state.get(
        "execution_resource_usage"
    ),
    "cancellation_requested": state.get(
        "cancellation_requested",
        False,
    ),
    "cancellation_reason": state.get(
        "cancellation_reason"
    ),
    "security_semantics": {
        "process_group_supervised": True,
        "minimal_environment": True,
        "network_os_enforced": False,
        "writable_paths_os_enforced": False,
    },
},
```

上面是字典字段片段，因此应放入现有 manifest 字典，不要单独作为 Python 文件运行。

### 29.1 Manifest 禁止保存什么

禁止保存：

```text
完整 env 字典
API Key / token 值
未脱敏的敏感命令参数
无限长度 stdout/stderr preview
运行中的可变 runtime record hash
```

允许保存：

```text
env key 名称
profile fingerprint
capability decision
resource budget / peak usage
日志 Artifact 路径和 hash
final Process Record
```

### 29.2 Manifest version

Phase 15 使用 `manifest_version=2`。本阶段结构变化后升级为：

```text
"manifest_version": 3
```

消费者应按 version 解析，不要假设所有历史 run 都有
`execution_supervision`。

---

## 三十、扩展 Final Report

在 `app/nodes/final_report_node.py` 的执行部分增加：

```text
Execution Supervision
- Execution ID
- Backend / Profile
- End Reason
- PID / PGID（从 Process Record 摘要读取）
- Duration
- Peak RSS
- CPU seconds
- Process peak
- Observed write bytes
- Log truncated
- Graceful terminate / hard kill
- Capability enforcement mode
```

状态解释必须区分：

```text
succeeded：程序 exit 0
failed：程序非零或资源预算超限，可进入 Debug
cancelled：用户取消，不是论文复现失败
policy_blocked：Action 能力不被允许
环境阻断：进程无法启动
Agent 失败：Supervisor 内部错误或残留进程安全收口
```

Final Report 中不要写：

```text
network_access=none，因此程序绝对无法联网
```

应写：

```text
Action 未声明网络能力；当前 local/conda backend 未提供 OS 级网络隔离。
```

---

## 三十一、接入前的一致性检查

在开始测试前，统一补齐以下连接点。

### 31.1 ExecutionResult 增加取消原因

给 `ExecutionResult` 增加：

```text
cancellation_reason: str | None = None
```

Supervisor 返回时增加：

```text
cancellation_reason=cancellation_reason
```

executor/smoke payload 增加：

```text
"cancellation_requested": result.get("cancelled", False),
"cancellation_reason": result.get("cancellation_reason"),
```

### 31.2 Profile Loader 做确定性路径校验

`load_execution_profiles()` 完成 Pydantic 校验后，还应检查：

```text
workspace_root 是绝对目录
artifact_root 是绝对路径且位于 /data/tianshaoqi24/
conda_executable（若有）是绝对文件
conda_prefix（若有）是绝对目录
writable_roots 全部为绝对路径
profile.env 不包含敏感 key
profile_id 不重复
```

不要在 loader 中自动创建论文 workspace 或 conda prefix。配置写错应明确失败。

### 31.3 Runtime HOME 不进入 writable capability

`execution/runtime/<execution_id>` 是 Supervisor 自己维护的内部目录，不需要 LLM
Action 把它写进 `writable_paths`。

`writable_paths` 表示论文程序声明需要写入的业务路径；Supervisor 自己写日志和 control
record 属于执行基础设施权限。

### 31.4 Graph 拓扑不需要改变

本阶段没有新增 Graph 节点，所以 `app/graph.py` 保持：

```text
action_builder -> risk_check -> human_review/preflight
preflight -> smoke_test
smoke_test -> executor/log_debug/final_report
executor -> log_debug/final_report
```

但要确认：

```text
terminal cancellation StageError -> final_report
non-terminal resource StageError -> log_debug
policy_blocked -> final_report
```

运行编译图测试，防止为接入 Supervisor 又引入无条件边。

---

## 三十二、ProcessSupervisor 单元测试

新增 `tests/test_process_supervisor.py`：

```python
import os
import sys
import time
from pathlib import Path

import psutil

from app.execution.process_supervisor import (
    ProcessSupervisor,
    SupervisedExecutionRequest,
    budget_end_reason,
)
from app.schemas import ResourceBudget, ResourceUsage


def _request(
    *,
    tmp_path: Path,
    execution_id: str,
    code: str,
    budget: ResourceBudget,
) -> SupervisedExecutionRequest:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    run_dir = tmp_path / "runs" / "run-1"
    run_dir.mkdir(parents=True, exist_ok=True)
    return SupervisedExecutionRequest(
        execution_id=execution_id,
        host_command=[sys.executable, "-c", code],
        cwd=workspace,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(run_dir / "home"),
            "PYTHONUNBUFFERED": "1",
        },
        run_dir=run_dir,
        action_id="action-1",
        stage="test_supervisor",
        profile_id="test-local",
        backend="local",
        budget=budget,
    )


def test_large_stdout_is_drained_but_bounded(
    tmp_path,
    monkeypatch,
) -> None:
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(
        "app.execution.cancellation.settings.runs_dir",
        runs_dir,
    )
    request = _request(
        tmp_path=tmp_path,
        execution_id="exec_large_output",
        code="import os; os.write(1, b'x' * 1000000)",
        budget=ResourceBudget(
            max_wall_time_seconds=10,
            max_processes=4,
            max_log_bytes_per_stream=4096,
            max_preview_bytes=1024,
            sample_interval_seconds=0.05,
            terminate_grace_seconds=0.2,
        ),
    )

    result = ProcessSupervisor().execute(request)

    assert result.ok is True
    assert result.log_truncated is True
    assert len(result.stdout.encode("utf-8")) <= 1024
    assert Path(result.stdout_path).stat().st_size == 4096


def test_budget_reason_is_deterministic() -> None:
    usage = ResourceUsage(
        peak_rss_bytes=200,
        peak_process_count=2,
        total_cpu_seconds=1,
        total_write_bytes=10,
        samples=1,
    )
    budget = ResourceBudget(
        max_wall_time_seconds=10,
        max_memory_bytes=100,
        max_processes=4,
        max_log_bytes_per_stream=4096,
        max_preview_bytes=1024,
    )

    assert budget_end_reason(usage, budget) == "memory_limit"


def test_timeout_kills_child_process_group(
    tmp_path,
    monkeypatch,
) -> None:
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(
        "app.execution.cancellation.settings.runs_dir",
        runs_dir,
    )
    child_pid_path = tmp_path / "child.pid"
    child_code = "import time; time.sleep(60)"
    parent_code = (
        "import pathlib, subprocess, sys, time; "
        f"p=subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(p.pid)); "
        "time.sleep(60)"
    )
    request = _request(
        tmp_path=tmp_path,
        execution_id="exec_timeout",
        code=parent_code,
        budget=ResourceBudget(
            max_wall_time_seconds=0.5,
            max_processes=8,
            max_log_bytes_per_stream=4096,
            max_preview_bytes=1024,
            sample_interval_seconds=0.05,
            terminate_grace_seconds=0.2,
        ),
    )

    result = ProcessSupervisor().execute(request)
    child_pid = int(child_pid_path.read_text(encoding="utf-8"))

    deadline = time.monotonic() + 3
    while psutil.pid_exists(child_pid) and time.monotonic() < deadline:
        try:
            if psutil.Process(child_pid).status() == psutil.STATUS_ZOMBIE:
                break
        except psutil.NoSuchProcess:
            break
        time.sleep(0.05)

    assert result.end_reason == "timeout"
    if psutil.pid_exists(child_pid):
        assert psutil.Process(child_pid).status() == psutil.STATUS_ZOMBIE
```

测试允许短暂 zombie，因为孙进程退出后的回收由其新父进程完成；验收重点是它不再
运行和消耗资源。

---

## 三十三、取消与最小环境集成测试

新增 `tests/test_execution_cancellation.py`：

```python
import os
import sys
import threading
import time

from app.execution.cancellation import (
    list_runtime_records,
    request_run_cancellation,
)
from app.execution.process_supervisor import (
    ProcessSupervisor,
    SupervisedExecutionRequest,
)
from app.schemas import ResourceBudget


def test_external_cancel_request_stops_supervisor(
    tmp_path,
    monkeypatch,
) -> None:
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    workspace = tmp_path / "workspace"
    run_dir.mkdir(parents=True)
    workspace.mkdir()
    monkeypatch.setattr(
        "app.execution.cancellation.settings.runs_dir",
        runs_dir,
    )

    request = SupervisedExecutionRequest(
        execution_id="exec_cancel",
        host_command=[
            sys.executable,
            "-c",
            "import time; time.sleep(60)",
        ],
        cwd=workspace,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(run_dir / "home"),
        },
        run_dir=run_dir,
        action_id="action-1",
        stage="test_cancel",
        profile_id="test-local",
        backend="local",
        budget=ResourceBudget(
            max_wall_time_seconds=30,
            max_processes=4,
            max_log_bytes_per_stream=4096,
            max_preview_bytes=1024,
            sample_interval_seconds=0.05,
            terminate_grace_seconds=0.2,
        ),
    )
    holder = {}

    def run() -> None:
        holder["result"] = ProcessSupervisor().execute(request)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        active = [
            item
            for item in list_runtime_records(run_dir)
            if item.get("status") == "running"
        ]
        if active:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Supervisor did not become running")

    cancellation = request_run_cancellation(
        run_dir=run_dir,
        reason="test cancellation",
        requested_by="pytest",
    )
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert cancellation.execution_id == "exec_cancel"
    result = holder["result"]
    assert result.end_reason == "cancelled"
    assert result.cancelled is True
```

新增 `tests/test_supervised_execution_integration.py`：

```python
import json
import sys
from pathlib import Path

from app.execution.local_runner import LocalRunner
from app.schemas import ExecutableAction, ExecutionProfile


def test_local_runner_child_cannot_read_agent_api_key(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run-1"
    workspace.mkdir()
    run_dir.mkdir(parents=True)

    script = workspace / "show_secret.py"
    script.write_text(
        "import os\n"
        "print(os.getenv('OPENAI_API_KEY', '<missing>'))\n",
        encoding="utf-8",
    )
    python_dir = str(Path(sys.executable).resolve().parent)
    program = Path(sys.executable).name
    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(runs_dir),
        inherited_env_keys=[],
        env={"PATH": python_dir, "LANG": "C.UTF-8"},
        allowed_programs=[program],
        writable_roots=[str(workspace)],
    )
    action = ExecutableAction(
        action_id="action-secret-test",
        program=program,
        args=[script.name],
        cwd=str(workspace),
        source="script",
        reason="verify minimal env",
        timeout_seconds=10,
        writable_paths=[str(workspace)],
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint="test-hash",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    monkeypatch.setattr(
        "app.execution.environment.settings.runs_dir",
        runs_dir,
    )
    monkeypatch.setattr(
        "app.execution.cancellation.settings.runs_dir",
        runs_dir,
    )

    result = LocalRunner(profile).run(
        action.model_dump(),
        run_dir=str(run_dir),
        stage="secret_test",
    )

    assert result["ok"] is True
    assert result["stdout"].strip() == "<missing>"
    process_record = json.loads(
        Path(result["process_record_path"]).read_text(
            encoding="utf-8"
        )
    )
    all_keys = {
        *process_record["inherited_env_keys"],
        *process_record["profile_env_keys"],
        *process_record["action_env_keys"],
    }
    assert "OPENAI_API_KEY" not in all_keys
```

---

## 三十四、迁移已有测试

Phase 16 修改了 `run_action_safe()` 签名和执行结果结构，下面这些旧测试必须同步：

| 测试文件 | 主要修改 |
|---|---|
| `tests/test_execution_runners.py` | 给 runner 传 `run_dir/stage`，断言 `end_reason` 和 Process Record |
| `tests/test_execution_profiles.py` | 增加环境、program、network、writable root、budget 校验 |
| `tests/test_execution_profile_hash.py` | 安全字段变化都使 fingerprint 变化 |
| `tests/test_executor_node.py` | mock 新签名和 Supervisor result 路径 |
| `tests/test_smoke_test_node.py` | mock 新签名，使用 `combined_log_path` |
| `tests/test_preflight_check_node.py` | 给 preflight 传 `run_dir`，登记 probe Artifact |
| `tests/test_structured_action_and_approval_hash.py` | hash 绑定能力和预算 |
| `tests/test_low_risk_route.py` | profile 必须允许测试 program，低风险 Action 不声明写能力 |
| `tests/test_run_manifest_node.py` | 断言 manifest v3 supervision/capability 字段 |
| `tests/test_final_report_node.py` | 断言 cancelled、budget、agent failure 文案 |
| `tests/test_compiled_graph_routes.py` | terminal/non-terminal StageError 路由仍正确 |

### 34.1 executor mock 结构

旧 mock：

```python
fake_result = {
    "ok": True,
    "returncode": 0,
    "stdout": "training started",
    "stderr": "",
    "combined_output": "training started",
    "timeout": False,
}
```

Phase 16 至少改成：

```python
fake_result = {
    "ok": True,
    "returncode": 0,
    "end_reason": "exited",
    "stdout": "training started",
    "stderr": "",
    "combined_output": "[stdout]\ntraining started",
    "timeout": False,
    "cancelled": False,
    "log_truncated": False,
    "execution_id": "exec-test",
    "execution_profile_id": "test-local",
    "execution_backend": "local",
    "resource_usage": {
        "peak_rss_bytes": 1024,
        "peak_process_count": 1,
        "total_cpu_seconds": 0.1,
        "total_write_bytes": 0,
        "peak_gpu_memory_bytes": None,
        "samples": 1,
    },
}
```

如果测试要验证 Artifact 注册，应在 `run_state["run_dir"]` 下创建真实的 stdout、
stderr、combined 和 process record 文件，并把路径加入 fake result。

如果只测试审批分支，可以 mock `register_execution_artifacts()` 返回空列表，避免测试把
重点混到文件系统。

### 34.2 mock 调用断言

旧断言：

```python
mocked_run.assert_called_once_with(pending_action)
```

修改为：

```python
mocked_run.assert_called_once_with(
    pending_action,
    state=state,
    stage="executor",
)
```

Smoke Test 对应 `stage="smoke_test"`。

### 34.3 增加 end_reason 参数化测试

在 `tests/test_executor_node.py` 增加：

```python
import pytest

from app.tools.exec_tools import build_execution_stage_error


@pytest.mark.parametrize(
    ("reason", "category", "terminal", "final_status"),
    [
        ("exited", "paper_program", False, "failed"),
        ("timeout", "paper_program", False, "failed"),
        ("memory_limit", "paper_program", False, "failed"),
        ("cancelled", "user", True, "cancelled"),
        ("policy_denied", "user", True, "policy_blocked"),
        (
            "launch_error",
            "environment",
            True,
            "environment_blocked",
        ),
        ("supervisor_error", "agent", True, "agent_failed"),
        ("orphan_cleanup", "agent", True, "agent_failed"),
    ],
)
def test_execution_end_reason_classification(
    reason,
    category,
    terminal,
    final_status,
) -> None:
    error, status = build_execution_stage_error(
        stage="executor",
        result={
            "end_reason": reason,
            "returncode": 1,
            "stderr": "failure",
            "resource_usage": {},
        },
        log_path=None,
    )

    assert error.category == category
    assert error.terminal is terminal
    assert status == final_status
```

---

## 三十五、分批运行测试

### 35.1 数据模型和策略

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m pytest \
  tests/test_execution_profiles.py \
  tests/test_execution_profile_hash.py \
  tests/test_action_capability_policy.py \
  tests/test_minimal_execution_environment.py \
  tests/test_structured_action_and_approval_hash.py
```

### 35.2 Supervisor

```bash
python -m pytest \
  tests/test_process_supervisor.py \
  tests/test_execution_cancellation.py \
  tests/test_supervised_execution_integration.py \
  tests/test_execution_runners.py
```

### 35.3 节点接入

```bash
python -m pytest \
  tests/test_preflight_check_node.py \
  tests/test_smoke_test_node.py \
  tests/test_executor_node.py \
  tests/test_low_risk_route.py
```

### 35.4 Graph 与报告

```bash
python -m pytest \
  tests/test_compiled_graph_routes.py \
  tests/test_fail_to_debug_flow.py \
  tests/test_run_manifest_node.py \
  tests/test_final_report_node.py \
  tests/test_failed_run_manifest.py
```

### 35.5 全量回归

```bash
python -m pytest
```

不要只看新测试通过。确认 pytest 最终显示：

```text
0 failed
0 errors
0 xpassed（除非明确设计）
测试数量没有意外减少
```

---

## 三十六、手工验收准备

所有目录都放在 `/data/tianshaoqi24/` 下：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

export PROJECT_ROOT="/data/tianshaoqi24/agent/paper_reproduction_copilot"
export PHASE16_ROOT="/data/tianshaoqi24/phase16_acceptance"
export PHASE16_WORKSPACE="$PHASE16_ROOT/workspace"
export RUNS_DIR="$PHASE16_ROOT/runs"
export CHECKPOINT_DB_PATH="$PHASE16_ROOT/checkpoints/langgraph.sqlite"
export PATCH_COORDINATION_DIR="$PHASE16_ROOT/coordination"
export EXECUTION_PROFILES_PATH="$PHASE16_ROOT/execution_profiles.json"

mkdir -p "$PHASE16_WORKSPACE"
mkdir -p "$RUNS_DIR"
mkdir -p "$(dirname "$CHECKPOINT_DB_PATH")"
mkdir -p "$PATCH_COORDINATION_DIR"
```

记录当前 Python：

```bash
export PHASE16_PYTHON_BIN="$(python -c 'import sys; print(sys.executable)')"
export PHASE16_PYTHON_DIR="$(dirname "$PHASE16_PYTHON_BIN")"
export PHASE16_PYTHON_NAME="$(basename "$PHASE16_PYTHON_BIN")"

printf 'python bin: %s\n' "$PHASE16_PYTHON_BIN"
printf 'python dir: %s\n' "$PHASE16_PYTHON_DIR"
printf 'python name: %s\n' "$PHASE16_PYTHON_NAME"
```

确认所有可写根目录：

```bash
case "$PROJECT_ROOT" in
  /data/tianshaoqi24/*) ;;
  *) echo "PROJECT_ROOT escaped allowed root"; exit 1 ;;
esac

case "$PHASE16_ROOT" in
  /data/tianshaoqi24/*) ;;
  *) echo "PHASE16_ROOT escaped allowed root"; exit 1 ;;
esac
```

### 36.1 创建测试 Profile

```bash
cat > "$EXECUTION_PROFILES_PATH" <<EOF
{
  "profiles": [
    {
      "profile_id": "phase16-demo-local",
      "backend": "local",
      "workspace_root": "$PHASE16_WORKSPACE",
      "artifact_root": "$RUNS_DIR",
      "inherited_env_keys": [],
      "env": {
        "PATH": "$PHASE16_PYTHON_DIR",
        "LANG": "C.UTF-8",
        "CUDA_VISIBLE_DEVICES": ""
      },
      "allowed_action_env_keys": [
        "OMP_NUM_THREADS"
      ],
      "allowed_programs": [
        "$PHASE16_PYTHON_NAME"
      ],
      "writable_roots": [
        "$PHASE16_WORKSPACE",
        "$RUNS_DIR"
      ],
      "network_policy": "deny",
      "enforcement_mode": "best_effort",
      "budget": {
        "max_wall_time_seconds": 120,
        "max_cpu_seconds": 120,
        "max_memory_bytes": 1073741824,
        "max_processes": 8,
        "max_write_bytes": 1073741824,
        "max_gpu_memory_bytes": null,
        "max_log_bytes_per_stream": 4096,
        "max_preview_bytes": 1024,
        "sample_interval_seconds": 0.05,
        "terminate_grace_seconds": 0.5
      }
    }
  ]
}
EOF

python -m json.tool "$EXECUTION_PROFILES_PATH"
```

### 36.2 创建四个验收脚本

Secret Probe：

```bash
cat > "$PHASE16_WORKSPACE/secret_probe.py" <<'PY'
import os

print("OPENAI_API_KEY=" + os.getenv("OPENAI_API_KEY", "<missing>"))
print("EMBEDDING_API_KEY=" + os.getenv("EMBEDDING_API_KEY", "<missing>"))
print("HOME=" + os.getenv("HOME", "<missing>"))
print("TMPDIR=" + os.getenv("TMPDIR", "<missing>"))
PY
```

Large Output：

```bash
cat > "$PHASE16_WORKSPACE/large_output.py" <<'PY'
import os

os.write(1, b"stdout-x" * 200000)
os.write(2, b"stderr-y" * 200000)
PY
```

Process Tree：

```bash
cat > "$PHASE16_WORKSPACE/process_tree.py" <<'PY'
import os
import subprocess
import sys
import time
from pathlib import Path

child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(120)"]
)
Path("child.pid").write_text(str(child.pid), encoding="utf-8")
Path("parent.pid").write_text(str(os.getpid()), encoding="utf-8")
time.sleep(120)
PY
```

Long Running：

```bash
cat > "$PHASE16_WORKSPACE/long_running.py" <<'PY'
import os
import time

print(f"long-running pid={os.getpid()}", flush=True)
while True:
    print("heartbeat", flush=True)
    time.sleep(0.5)
PY
```

### 36.3 创建受监管执行入口

```bash
cat > "$PHASE16_WORKSPACE/run_case.py" <<'PY'
import json
import sys
from pathlib import Path

from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.tools.action_tools import build_run_action_from_command
from app.tools.artifact_tools import create_run_layout
from app.tools.exec_tools import run_action_safe


if len(sys.argv) != 4:
    raise SystemExit(
        "usage: run_case.py RUN_ID SCRIPT_NAME TIMEOUT_SECONDS"
    )

run_id, script_name, timeout_text = sys.argv[1:]
timeout_seconds = int(timeout_text)
profile = get_execution_profile("phase16-demo-local")
fingerprint = compute_execution_profile_fingerprint(profile)
layout = create_run_layout(run_id)
run_dir = layout["run_root"]

program = Path(sys.executable).name
action = build_run_action_from_command(
    command=f"{program} {script_name}",
    cwd=profile.workspace_root,
    source="script",
    reason=f"Phase 16 acceptance: {script_name}",
    timeout_seconds=timeout_seconds,
    execution_profile_id=profile.profile_id,
    execution_profile_fingerprint=fingerprint,
)

print(
    json.dumps(
        {
            "run_id": run_id,
            "run_dir": run_dir,
            "action_id": action["action_id"],
        },
        ensure_ascii=False,
    ),
    flush=True,
)

result = run_action_safe(
    action,
    state={"run_id": run_id, "run_dir": run_dir},
    stage="manual_acceptance",
)
print(json.dumps(result, ensure_ascii=False, indent=2))
PY
```

因为脚本从项目根目录启动，所以 `app` 可以正常 import；论文子进程的 cwd 则是
`PHASE16_WORKSPACE`。

---

## 三十七、验收 1：Agent Secret 不泄漏

在项目根目录执行：

```bash
export OPENAI_API_KEY="phase16-must-not-leak"
export EMBEDDING_API_KEY="phase16-embedding-must-not-leak"

python "$PHASE16_WORKSPACE/run_case.py" \
  phase16-secret \
  secret_probe.py \
  10 \
  > "$PHASE16_ROOT/secret_case.out"

sed -n '1,160p' "$PHASE16_ROOT/secret_case.out"
```

预期 preview 包含：

```text
OPENAI_API_KEY=<missing>
EMBEDDING_API_KEY=<missing>
HOME=/data/tianshaoqi24/phase16_acceptance/runs/phase16-secret/execution/runtime/...
TMPDIR=/data/tianshaoqi24/phase16_acceptance/runs/phase16-secret/execution/runtime/...
```

确认 secret 值没有进入 run：

```bash
if grep -R "phase16-must-not-leak" \
  "$RUNS_DIR/phase16-secret"; then
  echo "secret leaked into run artifacts"
  exit 1
fi

if grep -R "phase16-embedding-must-not-leak" \
  "$RUNS_DIR/phase16-secret"; then
  echo "embedding secret leaked into run artifacts"
  exit 1
fi
```

查看 Process Record：

```bash
find "$RUNS_DIR/phase16-secret/execution/attempts" \
  -name process_record.json \
  -type f \
  -print
```

重点确认：

```text
status=finished
end_reason=exited
returncode=0
inherited_env_keys/profile_env_keys/action_env_keys 中没有 API Key
```

---

## 三十八、验收 2：大量日志不会撑满内存或磁盘

```bash
python "$PHASE16_WORKSPACE/run_case.py" \
  phase16-large-output \
  large_output.py \
  10 \
  > "$PHASE16_ROOT/large_output_case.out"
```

检查三个日志大小：

```bash
find "$RUNS_DIR/phase16-large-output/execution/attempts" \
  -type f \
  -name '*.log' \
  -printf '%s %p\n'
```

预期：

```text
stdout.log <= 4096 bytes
stderr.log <= 4096 bytes
combined.log <= 8192 bytes
```

验证 Process Record：

```bash
python - "$RUNS_DIR/phase16-large-output" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
records = list(
    run_dir.glob("execution/attempts/*/process_record.json")
)
assert len(records) == 1, records
record = json.loads(records[0].read_text(encoding="utf-8"))
assert record["end_reason"] == "exited"
assert record["stdout_truncated"] is True
assert record["stderr_truncated"] is True
assert record["stdout_bytes_seen"] > record["stdout_bytes_written"]
assert record["stderr_bytes_seen"] > record["stderr_bytes_written"]
print(json.dumps(record, ensure_ascii=False, indent=2))
PY
```

这一步同时证明：

```text
日志到上限后仍然 drain，因此程序可以 exit 0
preview 有界
磁盘文件有界
```

---

## 三十九、验收 3：timeout 清理整个进程组

```bash
python "$PHASE16_WORKSPACE/run_case.py" \
  phase16-timeout \
  process_tree.py \
  1 \
  > "$PHASE16_ROOT/timeout_case.out"

sed -n '1,200p' "$PHASE16_ROOT/timeout_case.out"
```

读取父子 PID：

```bash
export PHASE16_PARENT_PID="$(cat "$PHASE16_WORKSPACE/parent.pid")"
export PHASE16_CHILD_PID="$(cat "$PHASE16_WORKSPACE/child.pid")"

printf 'parent pid: %s\n' "$PHASE16_PARENT_PID"
printf 'child pid: %s\n' "$PHASE16_CHILD_PID"
```

检查它们不再运行：

```bash
python - "$PHASE16_PARENT_PID" "$PHASE16_CHILD_PID" <<'PY'
import sys
import time

import psutil

for pid_text in sys.argv[1:]:
    pid = int(pid_text)
    deadline = time.monotonic() + 3
    while psutil.pid_exists(pid) and time.monotonic() < deadline:
        try:
            status = psutil.Process(pid).status()
        except psutil.NoSuchProcess:
            break
        if status == psutil.STATUS_ZOMBIE:
            break
        time.sleep(0.05)

    if psutil.pid_exists(pid):
        status = psutil.Process(pid).status()
        assert status == psutil.STATUS_ZOMBIE, (pid, status)

print("parent and child are no longer running")
PY
```

检查 Process Record：

```bash
python - "$RUNS_DIR/phase16-timeout" <<'PY'
import json
import sys
from pathlib import Path

records = list(
    Path(sys.argv[1]).glob(
        "execution/attempts/*/process_record.json"
    )
)
assert len(records) == 1
record = json.loads(records[0].read_text(encoding="utf-8"))
assert record["end_reason"] == "timeout"
assert record["pid"]
assert record["pgid"]
assert record["duration_seconds"] < 10
print(json.dumps(record, ensure_ascii=False, indent=2))
PY
```

---

## 四十、验收 4：跨终端取消

### 40.1 终端 A 启动长任务

先在终端 A 设置第三十六节的环境变量，然后执行：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

python "$PHASE16_WORKSPACE/run_case.py" \
  phase16-cancel \
  long_running.py \
  120
```

终端 A 会先打印 run id，然后保持运行。

### 40.2 终端 B 查看活动进程

终端 B 至少设置：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
export RUNS_DIR="/data/tianshaoqi24/phase16_acceptance/runs"
export CHECKPOINT_DB_PATH="/data/tianshaoqi24/phase16_acceptance/checkpoints/langgraph.sqlite"
export PATCH_COORDINATION_DIR="/data/tianshaoqi24/phase16_acceptance/coordination"
export EXECUTION_PROFILES_PATH="/data/tianshaoqi24/phase16_acceptance/execution_profiles.json"

python -m app.main show-process --run-id phase16-cancel
```

预期：

```text
status=running
pid 非空
pgid 非空
end_reason=null
```

### 40.3 请求取消

终端 B：

```bash
python -m app.main cancel-run \
  --run-id phase16-cancel \
  --reason "Phase 16 manual cancellation test"
```

终端 A 应在较短时间内返回，并显示：

```text
end_reason=cancelled
cancelled=true
ok=false
```

再次查看：

```bash
python -m app.main show-process --run-id phase16-cancel
```

预期最终记录：

```text
status=finished
end_reason=cancelled
cancellation_requested=true
cancellation_reason=Phase 16 manual cancellation test
```

再次运行相同 cancel 命令应得到“没有活动中的受监管进程”，而不是重新向旧 PGID
发送信号。

---

## 四十一、验收 5：Capability Policy 在执行前拒绝越权

运行确定性检查，不启动子进程：

```bash
python - <<'PY'
from app.execution.capability_policy import (
    evaluate_action_capabilities,
)
from app.execution.profile_store import get_execution_profile

profile = get_execution_profile("phase16-demo-local")
base = {
    "action_id": "policy-test",
    "program": profile.allowed_programs[0],
    "args": ["secret_probe.py"],
    "cwd": profile.workspace_root,
    "source": "script",
    "reason": "policy acceptance",
    "timeout_seconds": 10,
    "writable_paths": [profile.workspace_root],
    "network_access": "none",
    "execution_profile_id": profile.profile_id,
    "execution_profile_fingerprint": "test",
}

network = evaluate_action_capabilities(
    raw_action={**base, "network_access": "outbound"},
    profile=profile,
)
assert network.allowed is False
assert any(
    item.code == "NETWORK_NOT_ALLOWED"
    for item in network.violations
)

path_escape = evaluate_action_capabilities(
    raw_action={
        **base,
        "writable_paths": [
            "/data/tianshaoqi24/not-authorized-by-profile"
        ],
    },
    profile=profile,
)
assert path_escape.allowed is False
assert any(
    item.code == "WRITABLE_PATH_NOT_ALLOWED"
    for item in path_escape.violations
)

secret_env = evaluate_action_capabilities(
    raw_action={
        **base,
        "env_overrides": {"OPENAI_API_KEY": "forbidden"},
    },
    profile=profile,
)
assert secret_env.allowed is False
assert any(
    item.code == "SENSITIVE_ENV_NOT_ALLOWED"
    for item in secret_env.violations
)

print("network, path, and secret env were blocked")
PY
```

执行后不应新增 `execution/attempts/<id>`，因为拒绝发生在 Popen 之前。

---

## 四十二、可选验收：PSTNet 真实 Graph 只走到审批

这一步用于确认 Capability Decision 已接入真实主图，但不要恢复执行。

论文：

```text
/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf
```

仓库：

```text
/data/tianshaoqi24/PST-Convolution-main
```

### 42.1 给验收配置增加 PSTNet Profile

```bash
python - "$EXECUTION_PROFILES_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
python_bin = Path(sys.executable).resolve()
profile = {
    "profile_id": "pstnet-phase16-supervised",
    "backend": "local",
    "workspace_root": "/data/tianshaoqi24/PST-Convolution-main",
    "artifact_root": os.environ["RUNS_DIR"],
    "inherited_env_keys": [],
    "env": {
        "PATH": str(python_bin.parent),
        "LANG": "C.UTF-8",
        "CUDA_VISIBLE_DEVICES": "0"
    },
    "allowed_action_env_keys": ["OMP_NUM_THREADS"],
    "allowed_programs": [
        "python",
        "python3",
        python_bin.name,
        "torchrun",
        "pytest"
    ],
    "writable_roots": [
        "/data/tianshaoqi24/PST-Convolution-main",
        os.environ["RUNS_DIR"]
    ],
    "network_policy": "deny",
    "enforcement_mode": "best_effort",
    "budget": {
        "max_wall_time_seconds": 3600,
        "max_cpu_seconds": 7200,
        "max_memory_bytes": 17179869184,
        "max_processes": 64,
        "max_write_bytes": 107374182400,
        "max_gpu_memory_bytes": None,
        "max_log_bytes_per_stream": 16777216,
        "max_preview_bytes": 65536,
        "sample_interval_seconds": 0.2,
        "terminate_grace_seconds": 5
    }
}

payload["profiles"] = [
    item
    for item in payload["profiles"]
    if item["profile_id"] != profile["profile_id"]
]
payload["profiles"].append(profile)
path.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
```

### 42.2 启动 Graph

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

python -m app.main run-graph \
  "pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf" \
  /data/tianshaoqi24/PST-Convolution-main \
  --thread-id phase16-pstnet-review \
  --execution-profile pstnet-phase16-supervised
```

Graph 应先停在 `command_selection`。选择一个命令：

```bash
python -m app.main resume-command-selection \
  phase16-pstnet-review \
  --selected-index 0
```

随后可能出现两种正确结果：

```text
Action 合法且需要审批 -> human_review interrupt
Action 越权或仍有动态 shell -> policy_blocked final report
```

查看：

```bash
python -m app.main show-state phase16-pstnet-review
```

从 checkpoint 提取 run 目录和 Capability Decision：

```bash
python - <<'PY'
from app.graph import build_graph

snapshot = build_graph().get_state(
    {"configurable": {"thread_id": "phase16-pstnet-review"}}
)
print(snapshot.values.get("run_dir"))
print(snapshot.next)
print(snapshot.values.get("capability_decision"))
PY
```

检查该 run：

```text
planning/capability_decision.json 存在
如果等待审批，execution/attempts/ 还不存在或为空
Capability Decision 含 program/paths/env keys/network/budget
没有 Agent API Key
```

不要执行：

```text
resume-review --decision approved
```

这一项只验收主图接线，不启动 PSTNet 训练。

---

## 四十三、手工验收清单

```text
[ ] 所有创建和修改的目录都位于 /data/tianshaoqi24/
[ ] 子进程中 OPENAI_API_KEY 和 EMBEDDING_API_KEY 均为 missing
[ ] HOME/TMP/cache 位于当前 run 的 runtime 目录
[ ] 大量 stdout/stderr 不会让 preview 或日志无限增长
[ ] stdout/stderr pipe 超过落盘上限后仍被 drain
[ ] timeout 后父进程和孙进程都不再运行
[ ] cancel-run 只写请求，Supervisor 完成 PGID 终止
[ ] 第二次取消不会向旧 PGID 发信号
[ ] Process Record 有 PID、PGID、时间、end_reason 和资源峰值
[ ] nonzero exit 与 Supervisor error 分类不同
[ ] 资源预算超限可以进入 Debug，用户取消不能进入自动修复
[ ] Action hash 绑定 env/network/writable paths/budget/profile
[ ] Profile 安全配置变化使旧审批失效
[ ] local 和 conda 共用同一个 Supervisor
[ ] Manifest v3 不含完整 env 和 secret
[ ] Final Report 不把 best-effort 声明成 OS 强隔离
[ ] 全量 pytest 通过且测试数量没有意外减少
```

### 43.1 恢复 shell 环境

```bash
unset OPENAI_API_KEY EMBEDDING_API_KEY
unset PROJECT_ROOT PHASE16_ROOT PHASE16_WORKSPACE
unset RUNS_DIR CHECKPOINT_DB_PATH PATCH_COORDINATION_DIR
unset EXECUTION_PROFILES_PATH
unset PHASE16_PYTHON_BIN PHASE16_PYTHON_DIR PHASE16_PYTHON_NAME
unset PHASE16_PARENT_PID PHASE16_CHILD_PID
```

验收目录保存了 Process Record 和有界日志。教程不自动删除，确认不再需要后再由你
人工清理。

---

## 四十四、常见问题

### 44.1 子进程仍能看到 API Key

检查是否还存在：

```python
env = os.environ.copy()
```

再检查：

```text
LocalRunner 和 CondaRunner 是否都走 build_minimal_environment
preflight probe 是否仍使用旧 subprocess.run
patch verifier 是否还有独立 subprocess.run
profile.env 是否错误写入 secret
```

注意：Patch Verifier 也是论文代码执行入口。Phase 16 完成前，搜索所有
`subprocess.run/Popen`，逐个确认它属于：

```text
受监管论文执行
可信 Git 元数据读取
Agent 内部短命工具
```

凡是可能运行论文仓库代码的路径，都必须接入 Supervisor。

### 44.2 程序输出很多后卡住

通常是 pipe 没有持续 drain。确认：

```text
stdout 和 stderr 都注册到 selector
达到 log limit 后仍调用 os.read
没有调用 process.stdout.read()
没有等待 process.wait() 后才读日志
CondaRunner 使用 --no-capture-output
```

### 44.3 timeout 后仍有训练进程

确认：

```text
Popen(start_new_session=True)
记录 pgid 而不是只记录 pid
终止使用 os.killpg
SIGTERM 后继续检查 process group
必要时 SIGKILL
父进程退出后仍检查 PGID
```

如果论文代码主动 `setsid()` 逃离进程组，local/conda 无法提供强隔离，应转向
container/cgroup runner，而不是无限增加 PID 猜测逻辑。

### 44.4 cancel-run 提示没有活动进程

可能原因：

```text
任务已经结束
RUNS_DIR 与终端 A 不一致
传错 run_id/thread_id
Supervisor 尚未写 starting/running runtime record
runtime record 写入失败
```

先运行：

```text
python -m app.main show-process --run-id <run-id>
```

不要手工编辑 runtime record 伪造 running 状态。

### 44.5 任务结束为 orphan_cleanup

表示直接子进程已经退出，但原 PGID 中仍有进程。它可能是：

```text
训练脚本未等待 worker
DataLoader worker 清理异常
torchrun 子进程未退出
程序故意启动后台进程
```

Supervisor 已尝试安全清理，但这不是论文正常成功。应保留 Agent terminal error 和
Process Record，不要把父进程 returncode=0 当成 succeeded。

### 44.6 PATH 中有相对路径或空元素

Phase 16 会拒绝：

```text
PATH=.:/data/tianshaoqi24/toolchain/bin
PATH=/data/tianshaoqi24/toolchain/bin::/data/tianshaoqi24/conda/bin
PYTHONPATH=.
```

因为 `.` 和空元素会让 cwd 隐式加入程序/模块搜索路径。把 profile 改成绝对路径列表。

### 44.7 Conda 找不到环境

不要恢复 `conda activate`。检查：

```text
conda_executable 是绝对文件
conda_prefix 是绝对目录
profile fingerprint 已重新生成
Action 已重新审批
CondaRunner 使用 conda run -p
```

### 44.8 Log Debug 看不到完整结尾

第一版 preview 保存开头。如果错误出现在日志尾部，可以把 `BoundedLogSink` 扩展为：

```text
head preview + ring-buffer tail preview
```

但总大小仍必须有界。不要恢复完整日志进入 state。

### 44.9 GPU Budget 被拒绝

这是正确的 fail-closed 行为。当前 runner 没有可靠 GPU enforcer 时，不能接受一个无法
兑现的 GPU 上限。

后续可以增加 NVML 观察器，但必须在报告中标记 observed/best-effort/hard-limit。

### 44.10 全量测试偶发残留进程

给进程测试增加有限等待和最终诊断：

```text
pid
pgid
create_time
status
cmdline（脱敏）
Process Record
```

测试失败时也必须在 fixture finalizer 中清理自己启动的 PGID，避免一次失败污染后续
pytest。

---

## 四十五、这一阶段涉及的 Agent 知识点

### 45.1 Control Plane 与 Execution Plane

```text
Agent/Graph：规划、审批、路由、记录
Runner/Supervisor：启动、观察、限制、终止
```

节点不应该自己拼 Conda、读取 pipe 或发送信号。

### 45.2 Capability-Based Security

风险判断从：

```text
program 是不是 python
```

升级为：

```text
program + args + cwd + env + network + writable paths + budget
```

审批绑定的是一组能力，而不是一句自然语言描述。

### 45.3 Least Privilege

最小权限环境不是“复制全部再删几个”，而是：

```text
从空集合开始，只加入任务完成所需能力
```

这与 Tool allowlist、MCP permission、container mount policy 是同一个安全思想。

### 45.4 Process Supervision

Agent 执行长任务时必须关心：

```text
父子进程树
进程组
信号升级
日志 backpressure
退出原因
资源峰值
取消协议
```

仅有 `subprocess.run(timeout=...)` 不等于拥有任务生命周期管理。

### 45.5 Backpressure 与 Bounded State

日志既不能阻塞子进程，也不能无限占用 Agent 内存、checkpoint 或磁盘。

这里采用：

```text
持续 drain + 有界落盘 + 有界 preview + truncation metadata
```

### 45.6 Durable Cancellation

取消不是内存中的布尔变量，而是一个跨进程、可审计的控制事实：

```text
Cancel Request Artifact
  -> Supervisor observes
  -> Process Group termination
  -> Process Record
  -> Final Report / Manifest
```

### 45.7 Fail Closed

下面情况都不能静默降级：

```text
Profile 要求 strict，但 runner 只有 best_effort
Action 要求 GPU limit，但没有 monitor
Action 要求 network，但 profile deny
Action 修改 profile 后沿用旧审批
存在多个 active runtime record，CLI 猜取消目标
```

---

## 四十六、最终文件清单

完成后至少应有：

```text
app/execution/environment.py
app/execution/capability_policy.py
app/execution/cancellation.py
app/execution/process_supervisor.py

app/execution/base.py
app/execution/local_runner.py
app/execution/conda_runner.py
app/execution/profile_store.py

app/tools/exec_tools.py
app/tools/action_tools.py
app/tools/preflight_tools.py
app/tools/artifact_tools.py

app/nodes/risk_check_node.py
app/nodes/preflight_check_node.py
app/nodes/smoke_test_node.py
app/nodes/executor_node.py
app/nodes/final_report_node.py
app/nodes/run_manifest_node.py

app/schemas.py
app/state.py
app/config.py
app/main.py
pyproject.toml
```

新增测试至少包括：

```text
tests/test_minimal_execution_environment.py
tests/test_action_capability_policy.py
tests/test_process_supervisor.py
tests/test_execution_cancellation.py
tests/test_supervised_execution_integration.py
```

---

## 四十七、完成标准

Phase 16 完成后至少满足：

```text
[ ] 任何论文程序路径都不再使用 os.environ.copy()
[ ] executor/smoke/preflight 统一走 ProcessSupervisor
[ ] local/conda 只有 command wrapper 不同
[ ] Action capability 在审批前和执行前各校验一次
[ ] Action/Profile hash 覆盖全部安全字段
[ ] 每次执行使用独立 session/process group
[ ] timeout/cancel 清理整个 PGID
[ ] 父进程退出后检查残留 worker
[ ] stdout/stderr 增量读取且内存/磁盘有界
[ ] Process Record 含 PID/PGID/end_reason/resource usage
[ ] 取消请求可跨终端提交并审计
[ ] terminal 与 non-terminal execution failure 分类正确
[ ] Manifest v3 和 Final Report 展示真实安全语义
[ ] local/conda 未被错误宣传成强沙箱
[ ] 新测试、图级测试和全量回归全部通过
```

---

## 四十八、下一阶段

路线图中的下一阶段是：

```text
Phase 17：Agent 回归评测体系
```

Phase 16 完成后，项目已经具备：

```text
结构化状态
持久化 checkpoint
审批绑定 hash
run-native artifact
统一 StageError
安全能力策略
受监管进程
```

接下来最值得做的不是继续增加更多自动修复，而是建立可量化回归基线：

```text
Schema 成功率
Graph route 正确率
Tool 参数准确率
Evidence 有效率
Secret 泄漏率
路径逃逸率
未审批执行率
取消/恢复成功率
重复副作用率
LLM 调用与延迟成本
```

Phase 17 会让后续 PDF 解析、混合检索、Prompt、Repair 和多 Runner 扩展都能回答：

```text
这次修改究竟让 Agent 变好了，还是只是看起来更复杂？
```
