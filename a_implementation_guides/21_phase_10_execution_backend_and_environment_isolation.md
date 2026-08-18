# 21. 闭环后第六阶段：Execution Backend 与环境隔离

## 这一阶段的目标

前面的阶段已经让 Agent 具备了：

```text
论文理解
  -> 仓库扫描
  -> 实验计划
  -> 命令选择
  -> 风险检查
  -> 人工审批
  -> preflight
  -> executor
  -> debug / report / manifest
```

但是当前执行链里还隐藏着一个非常现实的假设：

```text
Agent 环境 == 论文复现环境
```

实际项目中通常不是这样：

```text
Agent 项目：
  /data/.../paper_reproduction_copilot
  Python 环境：agent

论文仓库：
  /data/.../P4Transformer
  Python 环境：p4transformer
  CUDA / PyTorch / GCC：由论文代码决定
```

目录不同本身没有问题，因为 `subprocess.run(..., cwd=...)` 可以进入另一个目录。

真正的问题是：

```text
cwd 只改变工作目录
不会改变 Python、PATH、PyTorch、CUDA 和依赖环境
```

所以这一阶段要完成的核心升级是：

```text
Agent 负责规划、审批、调度和记录
Runner 负责在指定论文环境中执行和探测
```

完成后，Agent 和论文复现将形成真正的“控制面 / 执行面”分离。

---

## 为什么这一阶段必须放在 Smoke Test 前面

当前执行工具直接调用：

```python
subprocess.run(
    [program, *args],
    cwd=cwd,
    shell=False,
)
```

这意味着：

- `python` 从 Agent 的 `PATH` 中解析
- `torchrun` 从 Agent 的 `PATH` 中解析
- `import torch` 导入 Agent 环境里的 PyTorch
- CUDA 探测读取 Agent 环境里的运行时

如果现在直接实现 Smoke Test，那么 Smoke Test 也会在错误环境中执行。

可能出现这样的假失败：

```text
Agent 环境没有 torch
论文环境已经正确安装 torch

Smoke Test 结果：ModuleNotFoundError: No module named 'torch'
```

Repair Planner 随后甚至可能错误地建议安装依赖，但论文环境其实完全正常。

因此正确顺序必须是：

```text
Phase 20 Preflight
  -> Phase 21 Execution Backend
  -> Phase 22 Smoke Test
  -> Repair Proposal
  -> Bounded Repair
```

---

## 做完后的架构

```text
Agent Environment
├── LangGraph
├── LLM
├── Checkpoint
├── Approval
├── Run Manifest
└── Runner Registry
      ├── LocalRunner
      ├── CondaRunner       本阶段实现
      ├── DockerRunner      后续扩展
      └── SSHRunner         后续扩展

Paper Reproduction Environment
├── source repository
├── dataset
├── conda environment
├── CUDA / PyTorch / extensions
└── experiment artifacts
```

节点不再关心 Conda 命令应该怎么拼接：

```text
executor_node
  -> run_action_safe(action)
      -> load ExecutionProfile
      -> select Runner
      -> runner.run(action)
```

preflight 也必须使用同一个 Runner：

```text
preflight_check_node
  -> runner.which("python")
  -> runner.probe("python", ["--version"])
  -> runner.probe("python", ["-c", "import torch; ..."])
```

这样才能保证：

```text
检查的是哪个环境
最终就在哪个环境执行
```

---

## 本阶段边界

为了控制复杂度，本阶段只实现：

- 同一台机器上的不同代码目录
- 同一台机器上的不同 Conda 环境
- `LocalRunner`
- `CondaRunner`
- 目标环境 runtime probe
- 执行环境绑定动作哈希
- Agent 侧执行日志和 manifest 记录

本阶段暂时不实现：

- Docker 镜像构建
- SSH 远程执行
- Slurm / Kubernetes 调度
- 自动同步远程仓库
- 自动上传大型 checkpoint
- 自动创建或修改 Conda 环境

这里的原则是：

```text
先把执行接口抽象正确
再逐个增加执行后端
```

---

## 本阶段建议新增和修改的文件

```text
app/config.py
app/schemas.py
app/state.py
app/main.py

app/execution/__init__.py
app/execution/base.py
app/execution/local_runner.py
app/execution/conda_runner.py
app/execution/profile_store.py
app/execution/registry.py

app/tools/action_tools.py
app/tools/exec_tools.py
app/tools/preflight_tools.py
app/tools/artifact_tools.py

app/nodes/action_builder_node.py
app/nodes/executor_node.py

config/execution_profiles.example.json
config/execution_profiles.local.json

tests/test_execution_profiles.py
tests/test_execution_runners.py
tests/test_execution_profile_hash.py
```

建议把本机专用配置加入 `.gitignore`：

```gitignore
config/execution_profiles.local.json
```

因为里面包含本机绝对路径，不适合提交到公共仓库。

---

## 一、定义 ExecutionProfile

### 1. 为什么不能把环境信息直接写进 command

不要让运行命令变成：

```text
conda activate p4transformer && python train.py
```

原因包括：

- `conda activate` 依赖 shell 初始化
- 当前安全执行器使用 `shell=False`
- 命令、环境和工作目录混在一起，难以审计
- 将来切换 Docker / SSH 时需要重新解析字符串
- 环境变化无法可靠绑定审批哈希

正确做法是把动作和环境分开：

```text
ExecutableAction：执行什么
ExecutionProfile：在哪里、用什么环境执行
```

### 2. 修改 `app/schemas.py`

先修改 import：

```python
from pydantic import BaseModel, Field, model_validator
```

然后在 `ExecutableAction` 前增加：

```python
class ExecutionProfile(BaseModel):
    """
    由项目维护者配置的受信任执行环境。

    profile 不能由 LLM 临时生成，否则模型就可以绕过环境边界，
    把动作发送到任意目录或任意执行后端。
    """

    profile_id: str
    backend: Literal["local", "conda"]

    # 论文代码在执行机上的根目录。
    # 本阶段是同机执行，所以这里可以直接使用宿主机绝对路径。
    workspace_root: str

    # 论文运行产生的模型、指标和临时结果应尽量写到这里。
    artifact_root: str

    # backend=conda 时使用。这里推荐写 conda 可执行文件的绝对路径，
    # 不依赖 Agent 进程当前的 PATH。
    conda_executable: str | None = None
    conda_prefix: str | None = None

    # 只放论文执行需要的普通环境变量。
    # 不要把 API Key 等秘密写进会被保存到 manifest 的结构中。
    env: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_backend_fields(self) -> "ExecutionProfile":
        """校验不同 backend 所需的配置字段。"""

        if self.backend == "conda":
            if not self.conda_executable:
                raise ValueError("conda backend requires conda_executable")
            if not self.conda_prefix:
                raise ValueError("conda backend requires conda_prefix")

        return self
```

然后扩展 `ExecutableAction`：

```python
class ExecutableAction(BaseModel):
    action_id: str
    action_type: Literal["run_command"] = "run_command"
    program: str
    args: list[str] = Field(default_factory=list)
    cwd: str
    source: Literal["readme", "script", "config", "inferred", "need_confirm"]
    reason: str
    timeout_seconds: int = 300
    env_allowlist: dict[str, str] = Field(default_factory=dict)
    writable_paths: list[str] = Field(default_factory=list)
    risk: dict | None = None

    # 动作明确绑定到一个受信任执行环境。
    execution_profile_id: str

    # 构造动作时记录 profile 指纹。
    # 如果审批后 profile 被修改，executor 必须拒绝沿用旧审批。
    execution_profile_fingerprint: str
```

这里建议把两个字段设为必填，而不是长期保留默认值。

如果你希望平滑迁移，可以先临时写成：

```python
execution_profile_id: str = "local"
execution_profile_fingerprint: str = ""
```

等所有测试和调用点都迁移完成后，再改成必填。

---

## 二、扩展 State

在 `app/state.py` 的 `ReproductionState` 中增加：

```python
class ReproductionState(TypedDict, total=False):
    # 省略已有字段...

    # 用户为本次复现任务选择的执行环境。
    execution_profile_id: str

    # action builder 创建动作时解析出的 profile 指纹。
    execution_profile_fingerprint: str
```

为什么既要放进 state，又要放进 action？

```text
state.execution_profile_id
    表示当前任务选择了哪个环境

pending_action.execution_profile_id
    表示这个具体动作最终绑定到了哪个环境
```

动作进入审批后，应以 `pending_action` 中的值为准。

---

## 三、增加配置入口

### 1. 修改 `app/config.py`

在 `Settings` 中增加：

```python
@dataclass
class Settings:
    # 省略已有配置...

    execution_profiles_path: Path = Path(
        os.getenv(
            "EXECUTION_PROFILES_PATH",
            "config/execution_profiles.local.json",
        )
    )

    default_execution_profile: str = os.getenv(
        "DEFAULT_EXECUTION_PROFILE",
        "local",
    )
```

### 2. 新建示例配置

创建 `config/execution_profiles.example.json`：

```json
{
  "profiles": [
    {
      "profile_id": "local",
      "backend": "local",
      "workspace_root": "/absolute/path/to/repository",
      "artifact_root": "/absolute/path/to/repository/agent_outputs",
      "env": {}
    },
    {
      "profile_id": "p4transformer-conda",
      "backend": "conda",
      "workspace_root": "/data/tianshaoqi24/P4Transformer",
      "artifact_root": "/data/tianshaoqi24/P4Transformer/agent_outputs",
      "conda_executable": "/home/tianshaoqi24/miniconda3/bin/conda",
      "conda_prefix": "/home/tianshaoqi24/miniconda3/envs/p4transformer",
      "env": {
        "CUDA_VISIBLE_DEVICES": "0"
      }
    }
  ]
}
```

再根据本机情况创建：

```text
config/execution_profiles.local.json
```

注意：

```text
conda_prefix 必须是已经存在的环境目录
本阶段不会自动创建环境
```

可以先手动检查：

```bash
/home/tianshaoqi24/miniconda3/bin/conda run \
  --no-capture-output \
  -p /home/tianshaoqi24/miniconda3/envs/p4transformer \
  python -c "import sys; print(sys.executable)"
```

---

## 四、实现 Profile Store 和指纹

新建 `app/execution/profile_store.py`：

```python
import hashlib
import json
from pathlib import Path

from app.config import settings
from app.schemas import ExecutionProfile


def load_execution_profiles(path: Path | None = None) -> dict[str, ExecutionProfile]:
    """从受信任的本地配置文件加载所有执行环境。"""

    config_path = path or settings.execution_profiles_path

    if not config_path.exists():
        raise FileNotFoundError(
            f"execution profiles file not found: {config_path}"
        )

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    raw_profiles = payload.get("profiles", [])

    profiles: dict[str, ExecutionProfile] = {}
    for raw_profile in raw_profiles:
        profile = ExecutionProfile.model_validate(raw_profile)

        if profile.profile_id in profiles:
            raise ValueError(
                f"duplicate execution profile id: {profile.profile_id}"
            )

        profiles[profile.profile_id] = profile

    return profiles


def get_execution_profile(profile_id: str) -> ExecutionProfile:
    """根据稳定 ID 获取一个执行环境。"""

    profiles = load_execution_profiles()
    profile = profiles.get(profile_id)

    if profile is None:
        available = ", ".join(sorted(profiles)) or "<none>"
        raise KeyError(
            f"execution profile not found: {profile_id}; "
            f"available profiles: {available}"
        )

    return profile


def compute_execution_profile_fingerprint(profile: ExecutionProfile) -> str:
    """
    为会影响执行语义的 profile 字段生成稳定指纹。

    不能只哈希 profile_id，因为同一个 ID 对应的 conda_prefix、
    workspace_root 或环境变量以后可能被修改。
    """

    material = {
        "profile_id": profile.profile_id,
        "backend": profile.backend,
        "workspace_root": profile.workspace_root,
        "artifact_root": profile.artifact_root,
        "conda_executable": profile.conda_executable,
        "conda_prefix": profile.conda_prefix,
        "env": profile.env,
    }

    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()
```

不要让 LLM 修改这个配置文件。

`ExecutionProfile` 属于系统策略和部署配置，不属于实验计划输出。

---

## 五、定义 Runner 抽象

新建 `app/execution/base.py`：

```python
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.schemas import ExecutionProfile


def _to_text(value: str | bytes | None) -> str:
    """统一 subprocess 正常返回和超时异常中的文本类型。"""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _combine_output(stdout: str, stderr: str) -> str:
    """保持 stdout / stderr 可读，同时避免 str 与 bytes 拼接错误。"""

    if stdout and stderr:
        return stdout + "\n\n[stderr]\n" + stderr
    if stderr:
        return "[stderr]\n" + stderr
    return stdout


class ExecutionRunner(ABC):
    """所有执行后端共同遵守的最小接口。"""

    def __init__(self, profile: ExecutionProfile):
        self.profile = profile

    @abstractmethod
    def build_host_command(self, program: str, args: list[str]) -> list[str]:
        """把目标命令转换成宿主机实际启动的 token 列表。"""

    def validate_cwd(self, cwd: str) -> Path:
        """限制动作只能在 profile 声明的 workspace 中执行。"""

        workspace_root = Path(self.profile.workspace_root).resolve()
        resolved_cwd = Path(cwd).resolve()

        if (
            resolved_cwd != workspace_root
            and workspace_root not in resolved_cwd.parents
        ):
            raise ValueError(
                f"cwd is outside execution workspace: {resolved_cwd}"
            )

        return resolved_cwd

    def run_program(
        self,
        *,
        program: str,
        args: list[str],
        cwd: str,
        timeout_seconds: int,
        action_env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """在当前 Runner 对应的目标环境中执行一个程序。"""

        try:
            resolved_cwd = self.validate_cwd(cwd)
            host_command = self.build_host_command(program, args)

            # 继承宿主机最基本环境，再叠加受信任 profile 和动作允许的变量。
            env = os.environ.copy()
            env.update(self.profile.env)
            env.update(action_env or {})

            completed = subprocess.run(
                host_command,
                cwd=str(resolved_cwd),
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                shell=False,
                check=False,
            )

            stdout = completed.stdout or ""
            stderr = completed.stderr or ""

            return {
                "ok": completed.returncode == 0,
                "returncode": completed.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "combined_output": _combine_output(stdout, stderr),
                "timeout": False,
                "execution_profile_id": self.profile.profile_id,
                "execution_backend": self.profile.backend,
                "cwd": str(resolved_cwd),
            }

        except subprocess.TimeoutExpired as exc:
            stdout = _to_text(exc.stdout)
            stderr = _to_text(exc.stderr)
            combined = _combine_output(stdout, stderr)
            if not combined:
                combined = f"command timed out after {timeout_seconds} seconds"

            return {
                "ok": False,
                "returncode": None,
                "stdout": stdout,
                "stderr": stderr or combined,
                "combined_output": combined,
                "timeout": True,
                "execution_profile_id": self.profile.profile_id,
                "execution_backend": self.profile.backend,
            }

        except (FileNotFoundError, OSError, ValueError) as exc:
            message = str(exc)
            return {
                "ok": False,
                "returncode": None,
                "stdout": "",
                "stderr": message,
                "combined_output": message,
                "timeout": False,
                "execution_profile_id": self.profile.profile_id,
                "execution_backend": self.profile.backend,
            }

    def run(self, action: dict[str, Any]) -> dict[str, Any]:
        """执行经过 action builder 和审批链生成的正式动作。"""

        return self.run_program(
            program=str(action.get("program") or ""),
            args=list(action.get("args") or []),
            cwd=str(action.get("cwd") or self.profile.workspace_root),
            timeout_seconds=int(action.get("timeout_seconds", 300)),
            action_env=dict(action.get("env_allowlist") or {}),
        )

    def probe(
        self,
        *,
        program: str,
        args: list[str],
        cwd: str,
        timeout_seconds: int = 15,
    ) -> dict[str, Any]:
        """preflight 使用的短时探测，同样走目标执行环境。"""

        return self.run_program(
            program=program,
            args=args,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )

    def which(self, program: str, cwd: str) -> str | None:
        """在目标环境中解析程序，而不是读取 Agent 自己的 PATH。"""

        script = (
            "import shutil, sys; "
            "resolved = shutil.which(sys.argv[1]); "
            "print(resolved or '')"
        )
        result = self.probe(
            program="python",
            args=["-c", script, program],
            cwd=cwd,
        )

        if not result["ok"]:
            return None

        resolved = result["stdout"].strip()
        return resolved or None
```

这里继续使用：

```python
shell=False
```

Runner 只负责增加结构化前缀，不把命令重新拼成 shell 字符串。

---

## 六、实现 LocalRunner 和 CondaRunner

### 1. `app/execution/local_runner.py`

```python
from app.execution.base import ExecutionRunner


class LocalRunner(ExecutionRunner):
    """直接使用 Agent 当前宿主机环境执行，主要用于兼容和测试。"""

    def build_host_command(self, program: str, args: list[str]) -> list[str]:
        return [program, *args]
```

### 2. `app/execution/conda_runner.py`

```python
from app.execution.base import ExecutionRunner


class CondaRunner(ExecutionRunner):
    """通过 `conda run -p` 在指定 Conda prefix 中执行。"""

    def build_host_command(self, program: str, args: list[str]) -> list[str]:
        conda_executable = self.profile.conda_executable
        conda_prefix = self.profile.conda_prefix

        if not conda_executable or not conda_prefix:
            raise ValueError("incomplete conda execution profile")

        return [
            conda_executable,
            "run",
            "--no-capture-output",
            "-p",
            conda_prefix,
            program,
            *args,
        ]
```

为什么使用 `conda run` 而不是 `conda activate`？

```text
conda activate：修改当前 shell 会话
conda run：启动一个明确属于目标环境的新进程
```

Agent 每次执行都是独立子进程，所以 `conda run` 更符合执行器模型。

### 3. `app/execution/registry.py`

```python
from app.execution.base import ExecutionRunner
from app.execution.conda_runner import CondaRunner
from app.execution.local_runner import LocalRunner
from app.schemas import ExecutionProfile


def build_execution_runner(profile: ExecutionProfile) -> ExecutionRunner:
    """根据受信任 profile 选择执行后端。"""

    if profile.backend == "local":
        return LocalRunner(profile)

    if profile.backend == "conda":
        return CondaRunner(profile)

    raise ValueError(f"unsupported execution backend: {profile.backend}")
```

### 4. `app/execution/__init__.py`

```python
from app.execution.profile_store import get_execution_profile
from app.execution.registry import build_execution_runner

__all__ = ["build_execution_runner", "get_execution_profile"]
```

---

## 七、让 Action Builder 绑定执行环境

### 1. 扩展 `build_run_action_from_command`

在 `app/tools/action_tools.py` 中增加两个参数：

```python
def build_run_action_from_command(
    *,
    command: str,
    cwd: str,
    source: str,
    reason: str,
    execution_profile_id: str,
    execution_profile_fingerprint: str,
    timeout_seconds: int = 300,
) -> dict:
```

创建 `ExecutableAction` 时写入：

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
    writable_paths=[str(Path(normalized_cwd))],
    execution_profile_id=execution_profile_id,
    execution_profile_fingerprint=execution_profile_fingerprint,
)
```

`build_preflight_action_from_command()` 也要接收和写入相同字段。

### 2. 修改 `action_builder_node`

```python
from app.config import settings
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.tools.action_tools import (
    build_run_action_from_command,
    compute_action_hash,
)


def action_builder_node(state: dict) -> dict:
    # 省略已有的 existing_action、命令选择和 index 校验逻辑...

    selected_command = effective_run_commands[selected_index]

    profile_id = (
        state.get("execution_profile_id")
        or settings.default_execution_profile
    )

    try:
        profile = get_execution_profile(profile_id)
        profile_fingerprint = compute_execution_profile_fingerprint(profile)

        # selected command 中的 cwd 仍然优先；如果模型没有给出，
        # 使用 profile.workspace_root，而不是 Agent 项目目录。
        cwd = selected_command.get("cwd") or profile.workspace_root

        action = build_run_action_from_command(
            command=selected_command["command"],
            cwd=cwd,
            source=selected_command.get("source", "inferred"),
            reason=selected_command.get("reason", "from experiment plan"),
            execution_profile_id=profile.profile_id,
            execution_profile_fingerprint=profile_fingerprint,
            timeout_seconds=300,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return {
            "pending_action": None,
            "pending_action_hash": None,
            "final_status": "invalid_action",
            "error": str(exc),
        }

    action_hash = compute_action_hash(action)

    return {
        "execution_profile_id": profile.profile_id,
        "execution_profile_fingerprint": profile_fingerprint,
        "pending_action": action,
        "pending_action_hash": action_hash,
    }
```

不要让模型输出的 `run_commands[*].cwd` 任意覆盖 profile 的 workspace。

Runner 的 `validate_cwd()` 会进行最终边界校验。

---

## 八、把执行环境加入 Action Hash

修改 `compute_action_hash()`：

```python
def compute_action_hash(action: dict) -> str:
    material = {
        "action_type": action.get("action_type"),
        "program": action.get("program"),
        "args": action.get("args", []),
        "cwd": action.get("cwd"),
        "env_allowlist": action.get("env_allowlist", {}),
        "timeout_seconds": action.get("timeout_seconds"),
        "writable_paths": action.get("writable_paths", []),

        # 审批必须同时绑定执行环境。
        "execution_profile_id": action.get("execution_profile_id"),
        "execution_profile_fingerprint": action.get(
            "execution_profile_fingerprint"
        ),
    }

    payload = json.dumps(material, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

这样以下任何变化都会让旧审批失效：

- Conda 环境路径变化
- workspace 变化
- artifact root 变化
- CUDA 环境变量变化
- backend 从 local 改成 conda

---

## 九、重构 `run_action_safe`

把 `app/tools/exec_tools.py` 从“直接执行 subprocess”改成 Runner facade：

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
    profile_id: str | None = None,
) -> dict[str, Any]:
    """统一返回 executor 已经熟悉的失败结构。"""

    return {
        "ok": False,
        "returncode": None,
        "stdout": "",
        "stderr": message,
        "combined_output": message,
        "timeout": False,
        "execution_profile_id": profile_id,
    }


def run_action_safe(action: dict) -> dict[str, Any]:
    """解析动作绑定的 profile，并委托给对应 Runner。"""

    profile_id = action.get("execution_profile_id")
    if not profile_id:
        return _execution_failure(message="missing execution_profile_id")

    try:
        profile = get_execution_profile(profile_id)
        current_fingerprint = compute_execution_profile_fingerprint(profile)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return _execution_failure(
            message=str(exc),
            profile_id=profile_id,
        )

    expected_fingerprint = action.get("execution_profile_fingerprint")
    if expected_fingerprint != current_fingerprint:
        return _execution_failure(
            message=(
                "execution profile changed after action creation; "
                "rebuild and re-approve the action"
            ),
            profile_id=profile_id,
        )

    runner = build_execution_runner(profile)
    return runner.run(action)
```

`executor_node` 可以暂时保持原调用形式：

```python
result = run_action_safe(pending_action)
```

这样现有节点职责不需要大改：

```text
executor_node：审批校验、状态转换、日志落盘
run_action_safe：profile 校验和 Runner 分发
Runner：真正执行
```

---

## 十、让 Preflight 检查目标环境

这是本阶段最容易遗漏、也最重要的一步。

当前 preflight 里的下面代码检查的是 Agent 环境：

```python
shutil.which(program)
subprocess.run(["python", "--version"])
subprocess.run(["python", "-c", "import torch; ..."])
```

必须改成目标 Runner。

### 1. 增加解析 Runner 的帮助函数

在 `app/tools/preflight_tools.py` 中增加：

```python
from app.execution.base import ExecutionRunner
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.execution.registry import build_execution_runner


def _resolve_action_runner(action: dict) -> tuple[ExecutionRunner, str]:
    """解析 action 绑定的 profile，并验证 profile 没有被修改。"""

    profile_id = action.get("execution_profile_id")
    if not profile_id:
        raise ValueError("missing execution_profile_id")

    profile = get_execution_profile(profile_id)
    current_fingerprint = compute_execution_profile_fingerprint(profile)
    expected_fingerprint = action.get("execution_profile_fingerprint")

    if expected_fingerprint != current_fingerprint:
        raise ValueError("execution profile fingerprint mismatch")

    return build_execution_runner(profile), current_fingerprint
```

### 2. 修改 runtime probe

让 `_run_probe()` 接收 Runner：

```python
def _run_probe(
    runner: ExecutionRunner,
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int = 8,
) -> tuple[bool, str]:
    """通过目标 Runner 执行探测，而不是直接启动 Agent subprocess。"""

    if not command:
        return False, "empty probe command"

    result = runner.probe(
        program=command[0],
        args=command[1:],
        cwd=str(cwd),
        timeout_seconds=timeout_seconds,
    )

    return result["ok"], result["combined_output"]
```

修改函数签名：

```python
def collect_runtime_preflight_items(
    action: dict,
    runner: ExecutionRunner,
) -> list[PreflightItem]:
```

调用改为：

```python
ok, evidence = _run_probe(
    runner,
    ["python", "--version"],
    cwd=cwd,
)

ok, evidence = _run_probe(
    runner,
    [
        "python",
        "-c",
        "import sys, torch; print(sys.executable); print(torch.__version__)",
    ],
    cwd=cwd,
)

ok, evidence = _run_probe(
    runner,
    [
        "python",
        "-c",
        "import torch; print(torch.cuda.is_available())",
    ],
    cwd=cwd,
)
```

建议把 `sys.executable` 一起写入 evidence。

这是验证环境是否真正解耦最直观的证据。

### 3. 替换 `shutil.which`

将：

```python
resolved_program = shutil.which(str(program))
```

替换为：

```python
resolved_program = runner.which(str(program), str(cwd))
```

因此 `collect_static_preflight_items()` 也要接收 `runner`：

```python
def collect_static_preflight_items(
    action: dict,
    repo_path: str | None,
    runner: ExecutionRunner,
) -> list[PreflightItem]:
```

### 4. 修改 `build_preflight_report`

```python
def build_preflight_report(
    action: dict,
    *,
    repo_path: str | None = None,
    action_hash: str | None = None,
) -> PreflightReport:
    try:
        runner, _ = _resolve_action_runner(action)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        item = PreflightItem(
            name="execution_profile_ready",
            category="runtime",
            status="failed",
            evidence=str(exc),
            recommendation="检查 execution profile 配置并重新构建动作。",
        )

        return PreflightReport(
            action_id=action.get("action_id"),
            action_hash=action_hash,
            ready_to_execute=False,
            summary="preflight blocked execution: execution_profile_ready",
            items=[item],
            blocking_items=[item.name],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    static_items = collect_static_preflight_items(
        action,
        repo_path=repo_path,
        runner=runner,
    )
    runtime_items = collect_runtime_preflight_items(action, runner=runner)
    items = [*static_items, *runtime_items]

    # 后面的 blocking_items / summary / report 构造逻辑保持不变。
```

本阶段是同一台宿主机，所以以下静态检查仍然可以使用 `Path`：

- workspace 是否存在
- dataset path 是否存在
- entry script 是否存在
- 目录是否可写

等以后增加 Docker / SSH Runner 时，这些检查也要下沉为：

```text
runner.path_exists(...)
runner.path_writable(...)
```

---

## 十一、修改 CLI

### 1. `run_graph` 增加 profile 参数

修改 `app/main.py`：

```python
@app.command()
def run_graph(
    paper_path: str,
    repo_path: str,
    log_path: str | None = typer.Argument(None),
    thread_id: str = "demo_thread",
    goal: str = "复现论文 main result",
    execution_profile: str | None = typer.Option(
        None,
        "--execution-profile",
        help="受信任执行环境的 profile_id",
    ),
):
    profile_id = execution_profile or settings.default_execution_profile

    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {
            "paper_path": paper_path,
            "repo_path": repo_path,
            "execution_profile_id": profile_id,
            "log_path": log_path,
            "experiment_goal": goal,
            "output_files": [],
            "step_count": 0,
            "max_steps": 20,
        },
        config=config,
    )

    print("[green]graph finished[/green]")
    print(result.get("output_files", []))
```

注意：

```text
thread_id 用于恢复 LangGraph 状态
execution_profile_id 用于选择论文运行环境
两者不能互相替代
```

### 2. `run_preflight` 同样增加参数

```python
@app.command()
def run_preflight(
    repo_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "manual preflight check",
    execution_profile: str | None = typer.Option(
        None,
        "--execution-profile",
    ),
):
    profile_id = execution_profile or settings.default_execution_profile
    profile = get_execution_profile(profile_id)
    profile_fingerprint = compute_execution_profile_fingerprint(profile)

    action = build_preflight_action_from_command(
        command=command,
        cwd=cwd or profile.workspace_root,
        source=source,
        reason=reason,
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint=profile_fingerprint,
        timeout_seconds=300,
    )

    action_hash = compute_action_hash(action)

    state = {
        "repo_path": repo_path,
        "execution_profile_id": profile.profile_id,
        "execution_profile_fingerprint": profile_fingerprint,
        "pending_action": action,
        "pending_action_hash": action_hash,
        "requires_approval": False,
        "user_approval": "not_required",
        "output_files": [],
    }

    result = preflight_check_node(state)
    print("[green]preflight finished[/green]")
    print(result.get("preflight_report"))
```

---

## 十二、Artifact 和 Run Manifest 分层

环境隔离以后，必须明确两类产物。

### Agent 控制面产物

由 Agent 自己写入：

```text
runs/<run_id>/
├── planning/
├── execution/execution.log
├── debug/
└── reports/run_manifest.json
```

包括：

- preflight report
- stdout / stderr
- debug report
- approval record
- final report
- run manifest

### 论文执行面产物

由目标论文环境写入：

```text
<artifact_root>/<run_id>/
├── checkpoints/
├── metrics/
├── predictions/
└── tensorboard/
```

本阶段不建议让 Agent 自动扫描和复制整个论文仓库，因为：

- checkpoint 可能非常大
- dataset 不能被当成输出复制
- 仓库里可能有大量缓存文件

先在 `run_manifest.json` 中记录：

```python
"execution_environment": {
    "profile_id": state.get("execution_profile_id"),
    "profile_fingerprint": state.get("execution_profile_fingerprint"),
    "backend": (
        state.get("execution_result", {}).get("execution_backend")
    ),
},
"execution_artifact_root": state.get("execution_artifact_root"),
```

以后再增加显式 `ArtifactSpec`：

```text
只收集用户或计划声明的路径
不递归抓取整个工作区
```

---

## 十三、单元测试

### 1. 测试 Profile Store 和指纹

新建 `tests/test_execution_profiles.py`：

```python
import json

from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    load_execution_profiles,
)


def test_load_execution_profiles(tmp_path) -> None:
    config_path = tmp_path / "profiles.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "profile_id": "paper-conda",
                        "backend": "conda",
                        "workspace_root": "/tmp/paper-repo",
                        "artifact_root": "/tmp/paper-artifacts",
                        "conda_executable": "/opt/conda/bin/conda",
                        "conda_prefix": "/opt/conda/envs/paper",
                        "env": {"CUDA_VISIBLE_DEVICES": "0"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    profiles = load_execution_profiles(config_path)

    assert set(profiles) == {"paper-conda"}
    assert profiles["paper-conda"].backend == "conda"


def test_profile_fingerprint_changes_with_environment(tmp_path) -> None:
    config_path = tmp_path / "profiles.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "profile_id": "paper-conda",
                        "backend": "conda",
                        "workspace_root": "/tmp/paper-repo",
                        "artifact_root": "/tmp/paper-artifacts",
                        "conda_executable": "/opt/conda/bin/conda",
                        "conda_prefix": "/opt/conda/envs/paper",
                        "env": {"CUDA_VISIBLE_DEVICES": "0"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    profile = load_execution_profiles(config_path)["paper-conda"]
    original = compute_execution_profile_fingerprint(profile)

    changed_profile = profile.model_copy(
        update={"conda_prefix": "/opt/conda/envs/paper-v2"}
    )
    changed = compute_execution_profile_fingerprint(changed_profile)

    assert original != changed
```

这里不要求测试机真的存在 `/opt/conda`，因为这个测试只验证配置解析和指纹逻辑，不执行 Conda。

### 2. 测试 CondaRunner 只构造 token，不依赖 shell

新建 `tests/test_execution_runners.py`：

```python
from app.execution.conda_runner import CondaRunner
from app.schemas import ExecutionProfile


def test_conda_runner_builds_structured_host_command() -> None:
    profile = ExecutionProfile(
        profile_id="paper-conda",
        backend="conda",
        workspace_root="/tmp/paper-repo",
        artifact_root="/tmp/paper-artifacts",
        conda_executable="/opt/conda/bin/conda",
        conda_prefix="/opt/conda/envs/paper",
    )
    runner = CondaRunner(profile)

    tokens = runner.build_host_command(
        "python",
        ["train.py", "--epochs", "1"],
    )

    assert tokens == [
        "/opt/conda/bin/conda",
        "run",
        "--no-capture-output",
        "-p",
        "/opt/conda/envs/paper",
        "python",
        "train.py",
        "--epochs",
        "1",
    ]

    # command 始终是 token list，不需要 &&、引号拼接或 shell=True。
    assert "&&" not in tokens
```

### 3. 测试 LocalRunner 的 cwd 边界

```python
import sys

from app.execution.local_runner import LocalRunner
from app.schemas import ExecutionProfile


def test_local_runner_executes_inside_workspace(tmp_path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()

    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "artifacts"),
    )
    runner = LocalRunner(profile)

    result = runner.run_program(
        program=sys.executable,
        args=["-c", "from pathlib import Path; print(Path.cwd())"],
        cwd=str(workspace),
        timeout_seconds=10,
    )

    assert result["ok"] is True
    assert result["stdout"].strip() == str(workspace)


def test_local_runner_rejects_cwd_outside_workspace(tmp_path) -> None:
    workspace = tmp_path / "repo"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()

    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(tmp_path / "artifacts"),
    )
    runner = LocalRunner(profile)

    result = runner.run_program(
        program=sys.executable,
        args=["-c", "print('should not run')"],
        cwd=str(outside),
        timeout_seconds=10,
    )

    assert result["ok"] is False
    assert "outside execution workspace" in result["stderr"]
```

### 4. 测试 profile 变化会改变动作哈希

新建 `tests/test_execution_profile_hash.py`：

```python
from copy import deepcopy

from app.tools.action_tools import compute_action_hash


def _action() -> dict:
    return {
        "action_id": "action_001",
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": "/tmp/repo",
        "source": "script",
        "reason": "test",
        "timeout_seconds": 300,
        "env_allowlist": {},
        "writable_paths": ["/tmp/repo"],
        "execution_profile_id": "paper-conda",
        "execution_profile_fingerprint": "fingerprint-a",
    }


def test_action_hash_changes_when_profile_changes() -> None:
    original = _action()
    changed = deepcopy(original)
    changed["execution_profile_fingerprint"] = "fingerprint-b"

    assert compute_action_hash(original) != compute_action_hash(changed)
```

### 5. 现有测试需要补哪些字段

当前测试中手工构造的 `pending_action` 需要增加：

```python
"execution_profile_id": "test-local",
"execution_profile_fingerprint": "test-fingerprint",
```

以下测试最容易受影响：

```text
tests/test_action_builder_node.py
tests/test_executor_node.py
tests/test_review_flow.py
tests/test_low_risk_route.py
tests/test_structured_action_and_approval_hash.py
tests/test_preflight_check_node.py
```

对节点单元测试，仍然可以 mock `run_action_safe()`。

Runner 的真实行为放到独立 runner 测试中，不要让所有图测试都依赖本机 Conda。

---

## 十四、推荐测试顺序

### 1. 先测试纯结构逻辑

```bash
python -m pytest \
  tests/test_execution_profiles.py \
  tests/test_execution_profile_hash.py \
  tests/test_execution_runners.py
```

### 2. 再跑原有安全执行测试

```bash
python -m pytest \
  tests/test_action_builder_node.py \
  tests/test_structured_action_and_approval_hash.py \
  tests/test_review_flow.py \
  tests/test_executor_node.py \
  tests/test_low_risk_route.py
```

### 3. 单独验证目标 Conda 环境

先确认 Agent 环境：

```bash
python -c "import sys; print(sys.executable)"
```

再确认论文环境：

```bash
/home/tianshaoqi24/miniconda3/bin/conda run \
  --no-capture-output \
  -p /home/tianshaoqi24/miniconda3/envs/p4transformer \
  python -c "import sys, torch; print(sys.executable); print(torch.__version__)"
```

这两个 `sys.executable` 应该不同。

### 4. 运行目标环境 Preflight

```bash
python -m app.main run-preflight \
  /data/tianshaoqi24/P4Transformer \
  "python train-msr-small.py --help" \
  --execution-profile p4transformer-conda
```

重点检查：

- `program_in_path` 来自论文环境
- `python_version_probe` 来自论文环境
- `torch_import_probe` 使用论文环境的 PyTorch
- `cuda_available_probe` 反映论文环境状态
- evidence 中的 `sys.executable` 不是 Agent Python

### 5. 最后跑整图

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer \
  --thread-id execution-backend-001 \
  --execution-profile p4transformer-conda
```

命令选择后继续：

```bash
python -m app.main resume-command-selection \
  execution-backend-001 \
  --selected-index 0
```

需要审批时：

```bash
python -m app.main resume-review \
  execution-backend-001 \
  --decision approved
```

---

## 十五、常见问题

### 问题 1：`conda run` 提示环境不存在

可能看到：

```text
EnvironmentLocationNotFound
```

检查：

```bash
/home/tianshaoqi24/miniconda3/bin/conda env list
```

确保 profile 中的 `conda_prefix` 是真实目录。

### 问题 2：Preflight 仍然显示 Agent Python

说明某个 probe 仍然直接调用了：

```python
subprocess.run(["python", ...])
```

或者仍然使用：

```python
shutil.which("python")
```

所有 runtime probe 都必须通过 Runner。

### 问题 3：`cwd is outside execution workspace`

说明动作里的 `cwd` 与 profile 不一致。

不要简单关闭检查，应确认：

- command 中的 cwd 是否是旧路径
- profile.workspace_root 是否正确
- experiment plan 是否生成了错误 cwd

### 问题 4：审批后提示 profile fingerprint mismatch

说明动作创建后，执行 profile 被修改了。

这是预期的安全行为。应该：

```text
重新构建 action
  -> 重新 risk check
  -> 重新人工审批
```

不能继续沿用旧审批。

### 问题 5：目标环境能执行，但 Agent 找不到产物

先区分：

```text
execution.log：Agent 控制面产物
checkpoint / metrics：论文执行面产物
```

确认训练命令把输出写到了 profile 的 `artifact_root`，再由 manifest 记录或显式收集。

### 问题 6：为什么不能直接使用目标环境的 Python 绝对路径

下面的方式对简单 Python 脚本确实可用：

```bash
/path/to/env/bin/python train.py
```

但它不能统一处理：

- `torchrun`
- 环境变量
- Conda activation scripts
- 将来的 Docker / SSH 后端
- profile 审计和指纹

因此可以作为临时排错手段，不建议作为最终架构。

---

## 十六、本阶段验收标准

### 功能验收

- CLI 可以显式选择 `execution_profile_id`
- action 中记录 profile ID 和 fingerprint
- `LocalRunner` 可以用于单元测试
- `CondaRunner` 使用 `conda run -p`
- executor 在论文环境执行命令
- preflight 在同一个论文环境执行 probe

### 安全验收

- Runner 始终使用 `shell=False`
- cwd 不能逃出 profile.workspace_root
- profile 不由 LLM 生成
- profile 变化后旧 action 失效
- profile 字段进入 action hash
- 修改执行环境后必须重新审批

### 可观测性验收

- execution result 记录 `execution_profile_id`
- execution result 记录 backend
- preflight evidence 包含目标 `sys.executable`
- run manifest 记录 profile ID 和 fingerprint
- Agent 日志与论文实验产物能够区分

### 回归验收

- 现有 command selection 流程仍然正常
- low-risk 路由仍然经过 preflight
- human review 恢复后仍能执行
- stale approval 测试仍然通过
- fail -> log_debug -> final_report 流程不受影响

---

## 十七、这一阶段完成后如何继续

下一阶段再实现 Smoke Test。

此时 Smoke Test 不应该自己操作 Conda，而应该复用动作里已有的 profile：

```python
smoke_action = {
    **pending_action,
    "action_id": f"{pending_action['action_id']}_smoke",
    "args": reduced_args,
    "timeout_seconds": settings.smoke_test_timeout_seconds,
}

result = run_action_safe(smoke_action)
```

因为 `smoke_action` 保留了：

```text
execution_profile_id
execution_profile_fingerprint
cwd
```

所以 Smoke Test 和 Full Executor 自然运行在同一个论文环境中。

推荐继续按三个检查点推进：

```text
Phase 22A：只完成 Smoke Test
Phase 22B：只生成 Repair Proposal
Phase 22C：最多一次 Bounded Repair 重试
```

不要在第一次接入时直接打开自动修复循环。

---

## 最后一句话总结这一阶段

这一阶段的本质不是“学会调用 Conda”，而是：

```text
把 Agent 的决策过程
和论文代码的运行过程
通过受信任、可审计、可替换的 Runner 接口解耦
```

完成后，你的 Agent 才真正具备继续扩展 Smoke Test、Docker、远程 GPU 和任务调度的稳定基础。
