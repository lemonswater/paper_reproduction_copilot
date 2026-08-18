# 38. Phase 27：单主机 OCI 安全执行、不可变环境身份与运行时闭环

Phase 26 已经建立 Workspace materialization、Worker capability、lease 和恢复机制。本阶段暂时
**不继续扩展跨主机执行**，而是先把一台主机上的真实执行边界补完整：论文代码必须进入一个
身份可验证、权限可限制、生命周期可恢复的 OCI 容器中运行。

> **本教程中的源码均为待实现代码。**
>
> 需要修改的文件和需要新增的文件都会明确列出。你仍然自己修改 `app/` 和 `tests/`；本教程
> 本身不会修改项目源码，也不会安装 Podman。

---

## 一、本版教程的范围调整

> **本节类型：范围说明，不修改项目代码。**

旧版 Phase 27 同时包含了单主机 OCI、跨主机镜像一致性、GPU/CDI、Cosign、SBOM 和供应链
证明，范围过大，也会掩盖当前最重要的安全闭环。本版改成三层优先级。

### 1.1 Phase 27 必做

```text
rootless Podman
+ digest-pinned image
+ --pull=never
+ read-only root filesystem
+ exact bind mounts
+ --network=none
+ cap-drop / no-new-privileges
+ memory / CPU / PID limits
+ create-before-start identity journal
+ timeout / cancel / lease-loss stop
+ crash reconciliation
+ Fake Engine tests + CPU smoke test
```

### 1.2 本阶段只保留接口、不做完整实现

```text
GPU / NVIDIA CDI
镜像签名与 Cosign
SBOM / vulnerability scan
镜像仓库自动 pull、build、登录和凭据管理
跨主机 image/runtime fingerprint 一致性验证
Kubernetes、Slurm、containerd 或 Docker daemon adapter
```

这些能力不是无价值，而是应在单主机 CPU OCI 闭环稳定后按真实需求追加。Phase 29 会先解决
更紧迫的受控资源获取和输入供应链问题。

### 1.3 Phase 26 仍然保留什么

即使暂时只在一台主机运行，Phase 26 的 Workspace 仍然有价值：

```text
每个 Job 使用独立目录
执行不直接修改原始论文仓库
Workspace manifest 可校验
waiting interrupt 前可 seal
失败后可恢复或 GC
```

本阶段只是不用“Host A -> Host B handoff”作为验收项，并不撤销 Workspace 抽象。

---

## 二、为什么 local/conda Runner 还不够

> **本节类型：原理说明，不修改项目代码。**

当前 `ProcessSupervisor` 最终仍在宿主机执行：

```python
subprocess.Popen(
    request.host_command,
    cwd=str(request.cwd),
    env=request.env,
    shell=False,
    start_new_session=True,
)
```

这能避免 shell 拼接并监管进程组，但不能强制阻止：

```text
读取当前系统用户可读的其他文件
network_policy=deny 时访问网络
依赖宿主机未声明的 Python/CUDA/动态库
瞬间超过内存或 PID 预算
Agent 崩溃后留下继续运行的外部进程
```

因此两层都要保留：

```text
Agent policy：这个动作是否应该执行
OCI boundary：操作系统实际上允许它做什么
```

容器不是虚拟机，也不是对恶意内核逃逸代码的绝对沙箱。但相比宿主机直接运行，它能给当前
项目提供更明确的 mount、network、namespace 和 cgroup 边界。

---

## 三、完成定义与安全不变量

> **本节类型：设计约束，不修改项目代码。**

完成后必须满足：

1. `ExecutionProfile.backend` 支持 `oci`，且 OCI profile 只能使用 `strict`；
2. image 必须写成 `name@sha256:<64 hex>`，禁止 `latest` 和仅 tag 引用；
3. Job 执行路径固定使用 `--pull=never`，绝不隐式联网；
4. Worker 启动时检查 Podman、rootless、cgroup v2 和目标 image 是否已存在；
5. 容器 root filesystem 只读，只挂载明确的 repo/run/dataset 路径；
6. `network_policy=deny` 必须映射为 `--network=none`；
7. 禁止 `--privileged`、host network、host PID、host IPC 和 runtime socket mount；
8. 默认 `--cap-drop=all`，并开启 `no-new-privileges`；
9. memory、CPU 和 PID 预算由 cgroup 参数表达，wall time 由 Supervisor 监管；
10. `podman create` 后、`podman start` 前必须先持久化 container ID；
11. timeout、cancel 和 lease loss 都必须按精确 ID 停止容器；
12. attach 进程退出后仍要 `inspect`，不能把 Podman CLI PID 当作容器事实；
13. Agent 重启后可以识别 active/exited/ambiguous 容器并进入 reconcile；
14. 自动清理只操作带本项目 ownership label 的精确 container ID；
15. 所有测试默认离线，真实 Podman 测试必须显式 opt-in。

参考 Podman 官方语义：`--network=none` 创建无网络连接的 namespace，`--read-only` 将 rootfs
设为只读；rootless 场景的部分资源限制依赖 cgroup v2 和宿主机配置：
[podman-run](https://docs.podman.io/en/stable/markdown/podman-run.1.html)。

---

## 四、最终执行链

> **本节类型：架构说明，不修改项目代码。**

```text
approved ExecutableAction
    -> capability policy
    -> verified OCI ExecutionProfile
    -> current WorkspaceBinding
    -> deterministic ContainerPlan
    -> podman create
    -> persist ContainerRuntimeRecord
    -> podman start --attach
    -> timeout/cancel/lease supervisor
    -> podman inspect
    -> stop/remove or reconciliation_required
    -> execution Artifact + Job result
```

关键设计是 **create-before-start**。如果直接 `podman run`，Agent 恰好在容器启动后崩溃，就
可能没有可靠 container ID。先 create、先记录、后 start，相当于为外部副作用建立 write-ahead
identity journal。

---

## 五、文件清单

> **本节类型：实施清单。**

需要修改：

```text
pyproject.toml
app/config.py
app/schemas.py
app/execution/base.py
app/execution/registry.py
app/execution/profile_store.py
app/execution/process_supervisor.py
app/tools/exec_tools.py
app/workspace/schemas.py
app/workspace/capabilities.py
app/job_runtime/worker.py
app/main.py
```

需要新增：

```text
app/execution/container_schemas.py
app/execution/container_errors.py
app/execution/container_engine.py
app/execution/podman_engine.py
app/execution/container_plan.py
app/execution/container_records.py
app/execution/container_supervisor.py
app/execution/oci_runner.py
app/execution/container_reconcile.py
tests/test_container_schemas.py
tests/test_container_plan.py
tests/test_container_supervisor.py
tests/test_oci_runner.py
tests/test_container_reconcile.py
tests/test_podman_runtime_integration.py
tests/fakes/fake_container_engine.py
```

不要把真实 Podman 调用写进单元测试。单元测试使用 Fake Engine；只有显式 integration test
才访问本机 runtime。

---

## 六、增加 OCI 配置

> **本节类型：需要修改项目代码。**
>
> 修改：`app/config.py`、`.env.example`。

在 `Settings` 中增加：

```python
class Settings(BaseSettings):
    # ...保留已有字段...

    # Phase 27 第一版只支持 rootless Podman CLI。
    container_runtime: str = "podman"

    # 所有容器都带此前缀，reconcile/GC 仍必须同时校验 label。
    container_name_prefix: str = "prc"

    # stop 先给容器正常退出时间，超时后 runtime 才强制终止。
    container_stop_timeout_seconds: float = 10.0

    # 默认不删除失败容器，先保留 inspect 证据；由受控 GC 处理。
    container_remove_succeeded: bool = True
    container_remove_failed: bool = False

    # 真实 runtime 测试默认关闭，避免普通 pytest 操作宿主机容器。
    enable_container_integration_tests: bool = False
```

`.env.example`：

```dotenv
CONTAINER_RUNTIME=podman
CONTAINER_NAME_PREFIX=prc
CONTAINER_STOP_TIMEOUT_SECONDS=10
CONTAINER_REMOVE_SUCCEEDED=true
CONTAINER_REMOVE_FAILED=false
ENABLE_CONTAINER_INTEGRATION_TESTS=false
```

本阶段不把 registry token、Cosign key 或云凭据放进 `.env`，因为执行路径根本不负责拉取镜像。

---

## 七、扩展 ExecutionProfile

> **本节类型：需要修改项目代码。**
>
> 修改：`app/schemas.py`、`app/workspace/schemas.py`。

先把 backend 扩展为 `oci`，再增加最小 OCI 配置。下面代码放在现有 `ExecutionProfile` 附近，
不要创建第二个同名模型。

```python
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class OciExecutionConfig(BaseModel):
    """只保存确定性运行参数，不保存 registry 凭据或任意 Podman flags。"""

    image_ref: str
    runtime: Literal["podman"] = "podman"
    container_repo_root: str = "/workspace/repo"
    container_run_root: str = "/workspace/run"
    memory_bytes: int = Field(ge=256 * 1024 * 1024)
    cpus: float = Field(gt=0, le=64)
    pids_limit: int = Field(default=512, ge=32, le=32768)
    tmpfs_bytes: int = Field(default=512 * 1024 * 1024, ge=16 * 1024 * 1024)

    @model_validator(mode="after")
    def require_digest_pinned_image(self) -> "OciExecutionConfig":
        prefix, separator, digest = self.image_ref.rpartition("@sha256:")
        if not separator or not prefix:
            raise ValueError("OCI image_ref 必须包含 @sha256:<64 hex>")
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("OCI image digest 必须是 64 位小写十六进制")
        return self


class ExecutionProfile(BaseModel):
    # 保留当前模型中的其他字段。
    profile_id: str
    backend: Literal["local", "conda", "oci"]
    enforcement_mode: Literal["best_effort", "strict"] = "best_effort"
    network_policy: Literal["deny", "allow"] = "deny"
    oci: OciExecutionConfig | None = None

    @model_validator(mode="after")
    def validate_backend_contract(self) -> "ExecutionProfile":
        if self.backend == "oci":
            if self.enforcement_mode != "strict":
                raise ValueError("OCI backend 必须使用 strict enforcement")
            if self.oci is None:
                raise ValueError("OCI backend 缺少 oci 配置")
            if self.network_policy != "deny":
                raise ValueError("Phase 27 OCI 第一版只允许 network_policy=deny")
        elif self.oci is not None:
            raise ValueError("非 OCI backend 不能携带 oci 配置")
        return self
```

上面 `ExecutionProfile` 代码块只展示新增/变化字段，**不能整体覆盖当前类**。当前类已有的
`workspace_root`、`artifact_root`、conda、env、allowed programs、budget、writable roots、Worker
requirements 以及原 `validate_backend_fields()` 分支都要保留。最安全的合并方式是：

```text
1. 在现有 ExecutionProfile 前新增 OciExecutionConfig
2. 把 backend Literal 改为 local/conda/oci
3. 在现有字段区新增 oci: OciExecutionConfig | None = None
4. 将 OCI 分支合并进现有 validate_backend_fields()
5. 保留 conda、local/conda strict、writable_roots、GPU 和 labels 的原校验
6. 全类只保留一个 model_validator 和一个 return self
```

Phase 26 的调度 schema 也要扩展，否则 profile 已接受 OCI、Job requirements 却会在 Pydantic
阶段拒绝：

```python
class WorkerCapabilities(WorkspaceModel):
    # 保留其他字段，只修改这个 Literal。
    execution_backends: list[Literal["local", "conda", "oci"]] = Field(
        min_length=1
    )


class JobRequirements(WorkspaceModel):
    # 保留其他字段，只修改这个 Literal。
    execution_backend: Literal["local", "conda", "oci"]
```

`app/workspace/capabilities.py` 和 requirements 构造逻辑继续从**受信任 profile** 推导 backend，
不能接受 Job request 或 LLM 自报 `oci`。

为什么第一版只接受 `network_policy=deny`：`allow` 不是安全策略，它没有说明允许哪些域名、端口、
重定向和字节数。联网获取会在 Phase 29 由独立 Resource Acquisition 边界实现。

---

## 八、定义容器计划和运行记录

> **本节类型：需要新增项目代码。**
>
> 新增：`app/execution/container_schemas.py`。

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ContainerMount(BaseModel):
    """host_path 只能由 Workspace/Profile 构造，不能直接来自 LLM。"""

    host_path: str
    container_path: str
    mode: Literal["ro", "rw"]


class ContainerPlan(BaseModel):
    """Podman token 的结构化输入，也是审批后可哈希的安全计划。"""

    job_id: str
    run_id: str
    ownership_token_hash: str
    image_ref: str
    name: str
    workdir: str
    argv: list[str]
    env: dict[str, str] = Field(default_factory=dict)
    mounts: list[ContainerMount]
    labels: dict[str, str]
    memory_bytes: int
    cpus: float
    pids_limit: int
    tmpfs_bytes: int


class ContainerInspect(BaseModel):
    container_id: str
    name: str
    running: bool
    status: str
    exit_code: int | None = None
    oom_killed: bool = False
    image_digest: str
    labels: dict[str, str] = Field(default_factory=dict)


class ContainerRuntimeRecord(BaseModel):
    """容器副作用的持久身份，不存原始 assignment token。"""

    schema_version: Literal["phase27-v1"] = "phase27-v1"
    job_id: str
    run_id: str
    ownership_token_hash: str
    container_id: str
    container_name: str
    image_ref: str
    plan_sha256: str
    status: Literal[
        "created",
        "running",
        "exited",
        "stop_requested",
        "cleanup_pending",
        "removed",
        "reconciliation_required",
    ]
    exit_code: int | None = None
    oom_killed: bool = False
    created_at: str
    updated_at: str
```

`ownership_token_hash` 来自当前 `WorkspaceBinding.assignment_token`，只用于容器 ownership 对比。
原始 assignment token 不能写入日志、label 或 Artifact。

---

## 九、定义错误类型

> **本节类型：需要新增项目代码。**
>
> 新增：`app/execution/container_errors.py`。

```python
class ContainerRuntimeError(RuntimeError):
    """所有 OCI runtime 错误的基类。"""


class ContainerRuntimeUnavailable(ContainerRuntimeError):
    """Podman 不存在、不是 rootless 或 cgroup 条件不满足。"""


class ContainerIdentityMismatch(ContainerRuntimeError):
    """inspect 得到的 ID、image 或 ownership labels 与记录不一致。"""


class ContainerStateAmbiguous(ContainerRuntimeError):
    """不能证明容器已停止，必须进入人工/后台 reconcile。"""


class ContainerPolicyViolation(ContainerRuntimeError):
    """image、mount、network 或 security plan 违反确定性策略。"""
```

这些错误后续应映射到项目现有 `StageError`：policy violation 通常 terminal；runtime 暂时不可用
可能 retryable；ambiguous 必须 reconciliation，不允许简单重跑。

---

## 十、建立 ContainerEngine 端口

> **本节类型：需要新增项目代码。**
>
> 新增：`app/execution/container_engine.py`。

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.execution.container_schemas import ContainerInspect


@dataclass(frozen=True)
class RuntimeProbe:
    runtime: str
    version: str
    rootless: bool
    cgroup_version: str


class ContainerEngine(Protocol):
    """业务层依赖端口；单元测试使用 FakeContainerEngine。"""

    def probe(self) -> RuntimeProbe:
        ...

    def image_exists(self, image_ref: str) -> bool:
        ...

    def create(self, tokens: list[str]) -> str:
        """返回完整 container ID；此方法不能启动容器。"""
        ...

    def start_attach(self, container_id: str) -> int:
        """阻塞等待 attach client，返回 CLI exit code，不代表容器 exit code。"""
        ...

    def inspect(self, container_id: str) -> ContainerInspect:
        ...

    def stop(self, container_id: str, timeout_seconds: float) -> None:
        ...

    def remove(self, container_id: str) -> None:
        ...
```

端口刻意不提供 `run(raw_flags: str)`，否则调用者仍可绕过策略拼接 `--privileged`。

---

## 十一、实现 Podman CLI Adapter

> **本节类型：需要新增项目代码。**
>
> 新增：`app/execution/podman_engine.py`。

```python
from __future__ import annotations

import json
import subprocess

from app.execution.container_engine import ContainerEngine, RuntimeProbe
from app.execution.container_errors import ContainerRuntimeError
from app.execution.container_schemas import ContainerInspect


class PodmanEngine(ContainerEngine):
    def __init__(self, executable: str = "podman"):
        self.executable = executable

    def _run(self, *args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
        # shell=False 且参数逐 token 传入，避免 shell 展开。
        completed = subprocess.run(
            [self.executable, *args],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            # 正式代码应经过现有 sanitize_error_message 再写日志。
            detail = completed.stderr.strip()[-2000:]
            raise ContainerRuntimeError(
                f"podman {' '.join(args[:2])} failed: {detail}"
            )
        return completed

    def probe(self) -> RuntimeProbe:
        info = json.loads(self._run("info", "--format", "json").stdout)
        version = json.loads(self._run("version", "--format", "json").stdout)
        return RuntimeProbe(
            runtime="podman",
            version=str(version.get("Client", {}).get("Version", "unknown")),
            rootless=bool(info.get("host", {}).get("security", {}).get("rootless")),
            cgroup_version=str(info.get("host", {}).get("cgroupVersion", "unknown")),
        )

    def image_exists(self, image_ref: str) -> bool:
        completed = subprocess.run(
            [self.executable, "image", "exists", image_ref],
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        return completed.returncode == 0

    def create(self, tokens: list[str]) -> str:
        container_id = self._run("create", *tokens, timeout=60).stdout.strip()
        if len(container_id) < 12:
            raise ContainerRuntimeError("podman create 未返回有效 container ID")
        return container_id

    def start_attach(self, container_id: str) -> int:
        completed = subprocess.run(
            [self.executable, "start", "--attach", container_id],
            text=False,
            check=False,
        )
        return completed.returncode

    def inspect(self, container_id: str) -> ContainerInspect:
        rows = json.loads(self._run("inspect", container_id).stdout)
        if len(rows) != 1:
            raise ContainerRuntimeError("podman inspect 返回数量异常")
        row = rows[0]
        state = row.get("State", {})
        config = row.get("Config", {})
        image_digest = str(row.get("ImageDigest") or row.get("ImageName") or "")
        return ContainerInspect(
            container_id=str(row["Id"]),
            name=str(row["Name"]),
            running=bool(state.get("Running")),
            status=str(state.get("Status", "unknown")),
            exit_code=state.get("ExitCode"),
            oom_killed=bool(state.get("OOMKilled")),
            image_digest=image_digest,
            labels=dict(config.get("Labels") or {}),
        )

    def stop(self, container_id: str, timeout_seconds: float) -> None:
        self._run("stop", "--time", str(int(timeout_seconds)), container_id)

    def remove(self, container_id: str) -> None:
        # 不使用 --force；调用者必须先 inspect 证明容器已停止。
        self._run("rm", container_id)
```

`start_attach()` 的 stdout/stderr 在正式接入时应重定向到现有 bounded log sink，而不是无限保留
在内存。不要为了复用 `subprocess.run` 而丢掉日志上限和取消能力。

---

## 十二、确定性构造 ContainerPlan

> **本节类型：需要新增项目代码。**
>
> 新增：`app/execution/container_plan.py`。

```python
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from app.execution.container_errors import ContainerPolicyViolation
from app.execution.container_schemas import ContainerMount, ContainerPlan
from app.schemas import ExecutableAction, ExecutionProfile
from app.workspace.schemas import WorkspaceBinding

SAFE_ENV_KEYS = {
    "PYTHONUNBUFFERED",
    "OMP_NUM_THREADS",
    "CUDA_VISIBLE_DEVICES",
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_container_plan(
    *,
    action: ExecutableAction,
    profile: ExecutionProfile,
    binding: WorkspaceBinding,
    job_id: str,
    run_id: str,
) -> ContainerPlan:
    """把已审批 Action 映射为固定容器视图，绝不接受任意 runtime flags。"""

    if profile.backend != "oci" or profile.oci is None:
        raise ContainerPolicyViolation("profile 不是 OCI backend")

    repo_root = Path(binding.repo_path).resolve(strict=True)
    run_root = Path(binding.run_dir).resolve(strict=True)
    action_cwd = Path(action.cwd).resolve(strict=True)
    try:
        relative_cwd = action_cwd.relative_to(repo_root)
    except ValueError as exc:
        raise ContainerPolicyViolation("Action cwd 必须位于 current workspace repo") from exc

    # Action 使用结构化 program/args；如果当前模型字段名不同，请映射现有字段，禁止 shlex 字符串。
    argv = [action.program, *action.args]
    if not argv[0].strip():
        raise ContainerPolicyViolation("program 不能为空")

    ownership_hash = _sha256_text(binding.assignment_token)
    safe_job = re.sub(r"[^a-zA-Z0-9_.-]", "-", job_id)[:40]
    name = f"prc-{safe_job}-{ownership_hash[:12]}"
    labels = {
        "io.paper-copilot.managed": "true",
        "io.paper-copilot.job-id": job_id,
        "io.paper-copilot.run-id": run_id,
        "io.paper-copilot.ownership-hash": ownership_hash,
    }

    env = {
        key: value
        for key, value in action.env_overrides.items()
        if key in SAFE_ENV_KEYS
    }

    return ContainerPlan(
        job_id=job_id,
        run_id=run_id,
        ownership_token_hash=ownership_hash,
        image_ref=profile.oci.image_ref,
        name=name,
        workdir=str(Path(profile.oci.container_repo_root) / relative_cwd),
        argv=argv,
        env=env,
        mounts=[
            ContainerMount(
                host_path=str(repo_root),
                container_path=profile.oci.container_repo_root,
                mode="ro",
            ),
            ContainerMount(
                host_path=str(run_root),
                container_path=profile.oci.container_run_root,
                mode="rw",
            ),
        ],
        labels=labels,
        memory_bytes=profile.oci.memory_bytes,
        cpus=profile.oci.cpus,
        pids_limit=profile.oci.pids_limit,
        tmpfs_bytes=profile.oci.tmpfs_bytes,
    )


def plan_sha256(plan: ContainerPlan) -> str:
    payload = json.dumps(
        plan.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return _sha256_text(payload)
```

如果训练必须写 repo，不要直接把整个 repo 改成 `rw`。优先把 checkpoint、log、output 参数指向
`/workspace/run`；确实需要源码构建时，再为经过审批的 build workspace 建单独 profile。

---

## 十三、把计划编译成固定 Podman tokens

> **本节类型：需要继续修改 `app/execution/container_plan.py`。**

```python
def build_podman_create_tokens(plan: ContainerPlan) -> list[str]:
    tokens = [
        "--name", plan.name,
        "--pull=never",
        "--read-only",
        "--network=none",
        "--cap-drop=all",
        "--security-opt=no-new-privileges",
        "--pids-limit", str(plan.pids_limit),
        "--memory", str(plan.memory_bytes),
        "--cpus", str(plan.cpus),
        "--workdir", plan.workdir,
        "--tmpfs", f"/tmp:rw,nosuid,nodev,noexec,size={plan.tmpfs_bytes}",
    ]

    for key, value in sorted(plan.labels.items()):
        tokens.extend(["--label", f"{key}={value}"])

    for mount in sorted(plan.mounts, key=lambda item: item.container_path):
        # source 已在 plan 构造阶段 resolve；destination 来自 profile 常量。
        tokens.extend(
            [
                "--mount",
                (
                    "type=bind,"
                    f"src={mount.host_path},"
                    f"dst={mount.container_path},"
                    f"{mount.mode},bind-propagation=rprivate"
                ),
            ]
        )

    for key, value in sorted(plan.env.items()):
        tokens.extend(["--env", f"{key}={value}"])

    # image 后面的所有 token 都是容器内 argv，不再被 runtime 解析为 flags。
    tokens.extend([plan.image_ref, *plan.argv])
    return tokens
```

必须增加负向测试，确认 tokens 中永远没有：

```text
--privileged
--network=host
--pid=host
--ipc=host
--userns=host
/run/podman/podman.sock
/var/run/docker.sock
```

---

## 十四、原子持久化 ContainerRuntimeRecord

> **本节类型：需要新增项目代码。**
>
> 新增：`app/execution/container_records.py`。

```python
from __future__ import annotations

import json
import os
from pathlib import Path

from app.execution.container_schemas import ContainerRuntimeRecord


def record_path(run_dir: Path) -> Path:
    return run_dir / "execution" / "container_runtime.json"


def write_container_record(run_dir: Path, record: ContainerRuntimeRecord) -> Path:
    target = record_path(run_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.part")
    payload = json.dumps(
        record.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    temporary.write_text(payload + "\n", encoding="utf-8")
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(target)
    return target


def load_container_record(run_dir: Path) -> ContainerRuntimeRecord | None:
    target = record_path(run_dir)
    if not target.exists():
        return None
    return ContainerRuntimeRecord.model_validate_json(
        target.read_text(encoding="utf-8")
    )
```

这里使用 run-native Artifact，符合 Phase 26 的 Workspace 生命周期。后续如果需要中心化容器记录，
可以再增加 PostgreSQL repository，但第一版不要同时引入第二套状态机。

---

## 十五、ContainerSupervisor 的关键顺序

> **本节类型：需要新增和修改项目代码。**
>
> 新增：`app/execution/container_supervisor.py`。
>
> 修改：`app/execution/process_supervisor.py`，复用 bounded log、取消和 wall timeout 能力。

完整业务顺序如下：

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.execution.container_engine import ContainerEngine
from app.execution.container_errors import (
    ContainerIdentityMismatch,
    ContainerStateAmbiguous,
)
from app.execution.container_plan import build_podman_create_tokens, plan_sha256
from app.execution.container_records import write_container_record
from app.execution.container_schemas import ContainerPlan, ContainerRuntimeRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContainerSupervisor:
    def __init__(self, engine: ContainerEngine):
        self.engine = engine

    def _assert_owned(self, record: ContainerRuntimeRecord, labels: dict[str, str]) -> None:
        expected = {
            "io.paper-copilot.managed": "true",
            "io.paper-copilot.job-id": record.job_id,
            "io.paper-copilot.run-id": record.run_id,
            "io.paper-copilot.ownership-hash": record.ownership_token_hash,
        }
        if any(labels.get(key) != value for key, value in expected.items()):
            raise ContainerIdentityMismatch("container ownership labels 不匹配")

    def execute(self, *, plan: ContainerPlan, run_dir: Path) -> ContainerRuntimeRecord:
        tokens = build_podman_create_tokens(plan)
        container_id = self.engine.create(tokens)

        # 必须先落记录再启动，不能调换顺序。
        now = _now_iso()
        record = ContainerRuntimeRecord(
            job_id=plan.job_id,
            run_id=plan.run_id,
            ownership_token_hash=plan.ownership_token_hash,
            container_id=container_id,
            container_name=plan.name,
            image_ref=plan.image_ref,
            plan_sha256=plan_sha256(plan),
            status="created",
            created_at=now,
            updated_at=now,
        )
        write_container_record(run_dir, record)

        attach_code = self.engine.start_attach(container_id)
        inspected = self.engine.inspect(container_id)
        self._assert_owned(record, inspected.labels)
        if inspected.container_id != container_id:
            raise ContainerIdentityMismatch("inspect container ID 不匹配")
        if inspected.running:
            # attach client 结束但容器还活着，不能把 attach_code 当作业务终态。
            record.status = "reconciliation_required"
            record.updated_at = _now_iso()
            write_container_record(run_dir, record)
            raise ContainerStateAmbiguous(
                f"attach exited with {attach_code}, but container is still running"
            )

        record.status = "exited"
        record.exit_code = inspected.exit_code
        record.oom_killed = inspected.oom_killed
        record.updated_at = _now_iso()
        write_container_record(run_dir, record)
        return record
```

上面是主顺序，不要直接照搬成最终阻塞实现。正式版本要把 `start --attach` 接入当前
`ProcessSupervisor` 的：

```text
bounded stdout/stderr
wall timeout
cancel event
lease heartbeat callback
process-group termination
```

当 timeout/cancel/lease loss 发生时，顺序必须是：

```text
record stop_requested
-> engine.stop(exact container_id)
-> inspect 证明 running=false
-> 再终止或回收 attach client
-> 写 exited/cleanup_pending/reconciliation_required
```

如果 `inspect` 失败，不能假定容器已停止，应写 `reconciliation_required`。

---

## 十六、实现 OCI Runner 并注册

> **本节类型：需要新增和修改项目代码。**
>
> 新增：`app/execution/oci_runner.py`。
>
> 修改：`app/execution/registry.py`、`app/execution/base.py`、
> `app/tools/exec_tools.py`。

当前项目没有 `ExecutionRequest` 平行模型，Runner 的真实入口是：

```python
runner.run(action, run_dir=..., stage=...)
```

因此不要新造一套请求/结果协议。先在 `app/execution/base.py` 增加一个只携带本次 Workspace
身份的上下文，并给现有 `run()` 增加可选参数；local/conda 暂时忽略它：

```python
from dataclasses import dataclass

from app.workspace.schemas import WorkspaceBinding


@dataclass(frozen=True)
class ExecutionRuntimeContext:
    job_id: str
    run_id: str
    workspace_binding: WorkspaceBinding


class ExecutionRunner(ABC):
    # 保留现有 __init__、build_host_command、validate_cwd 等实现。

    def run(
        self,
        action: dict[str, Any],
        *,
        run_dir: str,
        stage: str,
        runtime_context: ExecutionRuntimeContext | None = None,
    ) -> dict[str, Any]:
        # local/conda 保留当前方法体；runtime_context 目前只供 OCI 使用。
        ...
```

在 `app/tools/exec_tools.py::run_action_safe()` 中，从已经经过 Phase 26 校验的 Graph state 构造
context：

```python
from app.execution.base import ExecutionRuntimeContext
from app.workspace.schemas import WorkspaceBinding


raw_binding = state.get("workspace_binding")
runtime_context = None
if raw_binding is not None:
    runtime_context = ExecutionRuntimeContext(
        job_id=str(state["job_id"]),
        run_id=str(state["run_id"]),
        workspace_binding=WorkspaceBinding.model_validate(raw_binding),
    )

return runner.run(
    action,
    run_dir=str(run_dir),
    stage=stage,
    runtime_context=runtime_context,
)
```

不要把原始 Job claim token 塞进 Graph checkpoint。容器 ownership 使用当前
`WorkspaceBinding.assignment_token` 的 hash；数据库终态仍由 Job Worker 的 claim token fencing
保护。

`app/execution/oci_runner.py` 使用当前项目真实的 `ExecutableAction` 和 `ExecutionResult`：

```python
from pathlib import Path

from app.execution.base import ExecutionRuntimeContext, ExecutionRunner
from app.execution.capability_policy import evaluate_action_capabilities
from app.execution.container_plan import build_container_plan
from app.execution.container_records import record_path
from app.execution.container_supervisor import ContainerSupervisor
from app.schemas import ExecutableAction, ExecutionProfile, ExecutionResult


class OciRunner(ExecutionRunner):
    backend = "oci"

    def __init__(
        self,
        profile: ExecutionProfile,
        supervisor: ContainerSupervisor,
    ):
        # 不调用 base ProcessSupervisor 执行论文命令；容器 supervisor 接管生命周期。
        self.profile = profile
        self.supervisor = supervisor

    def build_host_command(self, program: str, args: list[str]) -> list[str]:
        raise RuntimeError("OCI Runner 不通过 host command 路径执行论文程序")

    def run(
        self,
        action: dict,
        *,
        run_dir: str,
        stage: str,
        runtime_context: ExecutionRuntimeContext | None = None,
    ) -> dict:
        if runtime_context is None:
            raise ValueError("OCI execution 缺少 current WorkspaceBinding")

        parsed = ExecutableAction.model_validate(action)
        decision = evaluate_action_capabilities(
            raw_action=parsed.model_dump(),
            profile=self.profile,
        )
        if not decision.allowed:
            message = ", ".join(item.code for item in decision.violations)
            return ExecutionResult(
                ok=False,
                returncode=None,
                end_reason="policy_denied",
                stderr=message,
                combined_output=message,
                execution_profile_id=self.profile.profile_id,
                execution_backend="oci",
                cwd=parsed.cwd,
            ).model_dump()

        binding = runtime_context.workspace_binding
        if Path(run_dir).resolve() != Path(binding.run_dir).resolve():
            raise ValueError("run_dir 与 current WorkspaceBinding 不一致")

        plan = build_container_plan(
            action=parsed,
            profile=self.profile,
            binding=binding,
            job_id=runtime_context.job_id,
            run_id=runtime_context.run_id,
        )
        record = self.supervisor.execute(
            plan=plan,
            run_dir=Path(binding.run_dir),
        )
        end_reason = "memory_limit" if record.oom_killed else "exited"
        result = ExecutionResult(
            ok=record.exit_code == 0 and not record.oom_killed,
            returncode=record.exit_code,
            end_reason=end_reason,
            stdout="",
            stderr="",
            combined_output="",
            execution_id=f"container_{record.container_id[:16]}",
            execution_profile_id=self.profile.profile_id,
            execution_backend="oci",
            cwd=parsed.cwd,
            process_record_path=str(record_path(Path(binding.run_dir))),
            # ContainerSupervisor 接入 bounded log sink 后在这里返回真实路径。
            combined_log_path=None,
        )
        return result.model_dump()
```

Registry 中增加 `"oci": OciRunner(profile, supervisor)`，但只有 runtime probe 通过时才实例化
可用 runner。随后扩展 `register_execution_artifacts()`，把 `container_runtime.json` 和容器 bounded
logs 作为已有文件登记；不要把完整 `podman inspect` 原文直接塞进 Graph state。

---

## 十七、Worker 启动探测与 capability

> **本节类型：需要修改项目代码。**
>
> 修改：`app/workspace/capabilities.py`、`app/job_runtime/worker.py`。

启动探测：

```python
def probe_oci_profile(engine: ContainerEngine, profile: ExecutionProfile) -> dict[str, object]:
    if profile.backend != "oci" or profile.oci is None:
        raise ValueError("not an OCI profile")

    probe = engine.probe()
    if not probe.rootless:
        raise ContainerRuntimeUnavailable("strict OCI profile 要求 rootless Podman")
    if probe.cgroup_version not in {"v2", "2"}:
        raise ContainerRuntimeUnavailable("strict OCI profile 要求 cgroup v2")
    if not engine.image_exists(profile.oci.image_ref):
        raise ContainerRuntimeUnavailable(
            "digest-pinned image 不在本机；执行路径禁止自动 pull"
        )
    return {
        "runtime": probe.runtime,
        "runtime_version": probe.version,
        "profile_id": profile.profile_id,
        "image_ref": profile.oci.image_ref,
    }
```

Worker capability 只上报**探测成功**的 OCI profile。探测失败不应阻止 API 启动，但 Worker
必须明确标记 degraded，且不能 claim 需要 OCI 的 Job。

当前虽然只有一台主机，capability 仍然必要：它防止错误配置的 Worker 接到自己无法执行的 Job，
也为未来增加第二个 Worker 保留一致接口。

---

## 十八、崩溃恢复与精确 reconcile

> **本节类型：需要新增和修改项目代码。**
>
> 新增：`app/execution/container_reconcile.py`。
>
> 修改：`app/job_runtime/worker.py`。

Worker 每轮 claim 前先扫描当前项目管理的未终态 record，但只能处理精确 ID：

```python
class ContainerReconciler:
    def __init__(self, engine: ContainerEngine):
        self.engine = engine

    def reconcile(self, record: ContainerRuntimeRecord, run_dir: Path) -> str:
        inspected = self.engine.inspect(record.container_id)

        # 先验证 identity，再做任何 stop/remove。
        expected_ownership = record.ownership_token_hash
        labels = inspected.labels
        if (
            labels.get("io.paper-copilot.managed") != "true"
            or labels.get("io.paper-copilot.job-id") != record.job_id
            or labels.get("io.paper-copilot.ownership-hash") != expected_ownership
        ):
            raise ContainerIdentityMismatch("reconcile ownership mismatch")

        if inspected.running:
            # 是否 stop 取决于当前 Job claim 是否仍有效；不能只看 record 时间。
            return "active_requires_ownership_check"

        record.status = "exited"
        record.exit_code = inspected.exit_code
        record.oom_killed = inspected.oom_killed
        record.updated_at = _now_iso()
        write_container_record(run_dir, record)
        return "exited_requires_job_reconciliation"
```

恢复决策表：

| Container | Job/claim | 处理 |
|---|---|---|
| running | 当前 claim 仍有效 | 继续观察，不重复启动 |
| running | claim 已失效 | exact-ID stop，进入 reconciliation |
| exited | Job 仍 running | 记录 exit，恢复 Job 提交或人工判定 |
| not found | record=created/running | ambiguous，禁止自动重跑 |
| ownership mismatch | 任意 | 拒绝操作并告警 |
| removed | Job 已终态 | 正常 |

最危险的错误是“查不到就重跑”。它可能造成训练任务实际仍运行，却启动第二份副作用。

---

## 十九、镜像准备方式

> **本节类型：运维步骤，不修改项目代码。**

镜像 build/pull 不属于 Job 执行路径。先由维护者在受控终端准备：

```bash
podman pull docker.io/library/python:3.10-slim
podman image inspect docker.io/library/python:3.10-slim --format '{{.Digest}}'
```

然后把得到的 digest 写入 profile：

```json
{
  "profile_id": "pstnet-oci-cpu-smoke",
  "backend": "oci",
  "enforcement_mode": "strict",
  "network_policy": "deny",
  "oci": {
    "image_ref": "docker.io/example/pstnet@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "memory_bytes": 8589934592,
    "cpus": 4.0,
    "pids_limit": 512,
    "tmpfs_bytes": 536870912
  }
}
```

不要为了“方便”在 runner 中遇到 image missing 就 `podman pull`。这会把不受控联网、registry
凭据、mutable tag 和执行审批混成一个副作用。

---

## 二十、单元测试

> **本节类型：需要新增测试代码。**

### 20.1 Fake Engine

新增 `tests/fakes/fake_container_engine.py`：

```python
class FakeContainerEngine:
    def __init__(self):
        self.calls: list[tuple] = []
        self.inspect_result = None
        self.container_id = "a" * 64

    def create(self, tokens: list[str]) -> str:
        self.calls.append(("create", list(tokens)))
        return self.container_id

    def start_attach(self, container_id: str) -> int:
        self.calls.append(("start_attach", container_id))
        return 0

    def inspect(self, container_id: str):
        self.calls.append(("inspect", container_id))
        return self.inspect_result

    def stop(self, container_id: str, timeout_seconds: float) -> None:
        self.calls.append(("stop", container_id, timeout_seconds))

    def remove(self, container_id: str) -> None:
        self.calls.append(("remove", container_id))
```

### 20.2 必测场景

`tests/test_container_schemas.py`：

```text
接受 digest-pinned image
拒绝 latest、仅 tag、非 64 位 digest、大写 digest
OCI 拒绝 best_effort
OCI 第一版拒绝 network allow
非 OCI profile 拒绝携带 oci 字段
```

`tests/test_container_plan.py`：

```text
cwd 从 host workspace 正确映射到 /workspace/repo
repo mount=ro，run mount=rw
拒绝 workspace 外 cwd
只保留 env allowlist
tokens 固定含 pull=never/read-only/network=none/cap-drop=all
tokens 不含 privileged/host namespace/runtime socket
同一输入得到同一 plan hash
```

`tests/test_container_supervisor.py`：

```text
调用顺序必须是 create -> write record -> start -> inspect
attach=0 但 inspect.running=true 时进入 reconciliation
OOMKilled 被写入 record
ownership label 不匹配时拒绝 stop/remove
timeout/cancel/lease loss 触发 exact-ID stop
inspect 失败时不自动判定 stopped
```

`tests/test_container_reconcile.py`：

```text
running + stale claim 不自动重跑
exited + running job 返回待 reconcile
container missing 返回 ambiguous
ownership hash 不匹配时不调用 stop/remove
```

测试时把 pytest 临时目录放在项目内：

```bash
mkdir -p .pytest-tmp
python -m pytest -q \
  --basetemp=.pytest-tmp/phase27 \
  tests/test_container_schemas.py \
  tests/test_container_plan.py \
  tests/test_container_supervisor.py \
  tests/test_oci_runner.py \
  tests/test_container_reconcile.py
```

---

## 二十一、真实 CPU Podman integration test

> **本节类型：需要新增测试和手工运行。**
>
> 新增：`tests/test_podman_runtime_integration.py`。

测试文件必须默认 skip：

```python
import os

import pytest


pytestmark = pytest.mark.container_runtime


def require_container_runtime() -> None:
    if os.getenv("ENABLE_CONTAINER_INTEGRATION_TESTS") != "true":
        pytest.skip("set ENABLE_CONTAINER_INTEGRATION_TESTS=true explicitly")
```

第一轮只用 CPU 小镜像验证边界，不直接训练 PSTNet：

```text
python -c 写 /workspace/run/smoke.txt 成功
写 /workspace/repo/forbidden.txt 失败
写 /etc/forbidden 失败
/proc/net/route 没有默认外网路由
容器退出后 inspect.exit_code 正确
Job 结束后不存在 running managed container
```

运行：

```bash
export ENABLE_CONTAINER_INTEGRATION_TESTS=true
export TEST_OCI_IMAGE='docker.io/library/python@sha256:<真实 digest>'
python -m pytest -q -m container_runtime \
  --basetemp=.pytest-tmp/phase27-runtime \
  tests/test_podman_runtime_integration.py
```

不要在测试里自动 pull。测试开始前 image missing 应清楚地 skip 或 fail，并提示运维准备命令。

---

## 二十二、CLI doctor

> **本节类型：需要修改项目代码。**
>
> 修改：`app/main.py`。

增加只读命令：

```bash
python -m app.main runtime-doctor --profile-id pstnet-oci-cpu-smoke
```

建议输出：

```text
runtime: podman
version: 5.x
rootless: true
cgroup: v2
image_ref: ...@sha256:...
image_present: true
profile_valid: true
ready: true
```

doctor 不能 build、pull、remove 或修复任何东西。它只解释“为什么该 profile 当前可用/不可用”。

---

## 二十三、完整验证顺序

> **本节类型：验证步骤，不修改项目代码。**

### 23.1 静态检查

```bash
python -m compileall -q app tests
ruff check app tests
```

### 23.2 Phase 27 离线测试

```bash
python -m pytest -q \
  --basetemp=.pytest-tmp/phase27 \
  tests/test_container_schemas.py \
  tests/test_container_plan.py \
  tests/test_container_supervisor.py \
  tests/test_oci_runner.py \
  tests/test_container_reconcile.py
```

### 23.3 原有执行链回归

```bash
python -m pytest -q \
  --basetemp=.pytest-tmp/phase27-regression \
  tests/test_execution_profiles.py \
  tests/test_execution_runners.py \
  tests/test_action_capability_policy.py \
  tests/test_supervised_execution_integration.py \
  tests/test_executor_node.py \
  tests/test_job_worker.py \
  tests/test_workspace_materializer.py \
  tests/test_workspace_fencing.py
```

### 23.4 显式 runtime 测试

```bash
ENABLE_CONTAINER_INTEGRATION_TESTS=true \
python -m pytest -q -m container_runtime \
  --basetemp=.pytest-tmp/phase27-runtime
```

### 23.5 全量离线回归

```bash
python -m pytest -q \
  -m 'not provider and not postgres and not container_runtime' \
  --basetemp=.pytest-tmp/phase27-all
```

---

## 二十四、手工验收

> **本节类型：手工操作，不修改项目代码。**

1. 使用 `runtime-doctor` 确认 rootless、cgroup v2 和 image digest；
2. 提交一个只写 run 目录的 CPU smoke Action；
3. 在 interrupt 前检查 `execution/container_runtime.json` 已保存 container ID；
4. 批准后确认容器使用 `network=none`、rootfs readonly、repo=ro、run=rw；
5. 执行期间请求 cancel，确认容器停止且 record 更新；
6. 模拟 Worker 在 create 后崩溃，重启后确认进入 reconcile，而不是再创建第二个容器；
7. 修改 record 中 ownership hash，确认系统拒绝 stop/remove；
8. 成功 Job 完成后确认没有 running managed container；
9. 失败 Job 保留 inspect 证据，由项目 GC 精确处理；
10. 最后再尝试 PSTNet 的最小 import/build smoke，不直接进入完整训练。

检查命令示例：

```bash
podman ps --filter label=io.paper-copilot.managed=true
podman inspect <container-id>
python -m app.main show-state --thread-id <thread-id>
```

不要执行全局 `podman container prune`，它可能删除本项目之外的容器。

---

## 二十五、Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 25.1 Policy 与 enforcement 是两层

审批决定动作是否被允许，OCI/cgroup 决定操作系统是否真正执行边界。任意一层缺失都不是完整
的安全执行系统。

### 25.2 外部副作用需要稳定身份

Graph checkpoint 只能证明 Agent 状态；container ID 才能定位已经发生的运行时副作用。先记录
再启动，是可恢复 Agent 的关键模式。

### 25.3 Fencing 必须覆盖外部世界

Job claim token 保护数据库终态写入；Workspace assignment token 的 hash 进入 container ownership
label。两层 fencing 共同防止旧 Worker 误停新 assignment 创建的容器。

### 25.4 Immutable image 不等于供应链可信

digest 只证明按内容寻址，不证明构建者可信，也不说明镜像中有哪些漏洞。本阶段只解决不可变
身份；签名、SBOM 和漏洞扫描以后再按需求扩展。

### 25.5 Single-host 也需要恢复设计

进程崩溃、机器重启、lease 超时和 attach client 断开都可能发生。是否跨主机与是否需要幂等、
journal、inspect 和 reconcile 是两回事。

---

## 二十六、本阶段完成标准

> **本节类型：最终验收，不修改项目代码。**

### 必须完成

- `backend=oci` 与 strict profile 校验完成；
- image 必须 digest-pinned，运行固定 `--pull=never`；
- rootless/cgroup/image probe 接入 Worker readiness/capability；
- mount、env、network 和 security tokens 由确定性代码构造；
- `create -> record -> start -> inspect` 顺序有测试保护；
- timeout/cancel/lease loss 能按精确 ID 停止容器；
- crash 后不重复启动，ambiguous 状态进入 reconcile；
- CPU Fake Engine 和真实 Podman smoke 通过；
- local/conda 和 Workspace 原有测试没有回归。

### 不作为完成阻塞项

- Host A/Host B handoff；
- GPU/CDI；
- Cosign signature；
- SBOM 和漏洞扫描；
- Registry 自动拉取；
- Kubernetes/Slurm。

---

## 二十七、下一阶段

下一阶段优先做：

```text
Phase 28：分布式可观测性与运行就绪
```

这里的“分布式”不是要求多台主机，而是 API、PostgreSQL Job Store、Worker、LangGraph、LLM
Provider、OCI Runtime 和 Object Storage 已经是多个异步边界。我们需要统一 request/job/run/claim
关联、结构化日志、metrics、trace、readiness、SLO 和故障诊断，才能知道系统到底卡在哪里。

Phase 28 完成后，再做：

```text
Phase 29：受控资源获取与供应链安全
```

把论文、仓库、checkpoint 等联网输入先下载、校验、发布为不可变 Resource，再只读挂载给
`network=none` 的执行容器。
