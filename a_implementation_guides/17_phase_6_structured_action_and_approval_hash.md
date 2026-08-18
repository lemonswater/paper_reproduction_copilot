# 17. 闭环后第二阶段：Structured Action 与 Approval Hash

## 这一阶段的目标

上一阶段你已经补上了：

```text
Durable Checkpoint
跨进程 Resume
```

这说明你的 Agent 已经开始具备：

```text
有状态
可中断
可恢复
```

但当前执行链里还有两个非常关键的安全与一致性问题：

### 问题 1：`pending_action` 还是“自由文本命令”

你当前的 [app/nodes/action_builder_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/action_builder_node.py:1) 还是这样构造动作：

```python
pending_action = {
    "type": "run_command",
    "command": first_command["command"],
    "cwd": cwd,
    "reason": first_command.get("reason", "from experiment plan"),
    "source": "experiment_plan"
}
```

这里的问题是：

- `command` 是一个完整字符串
- 可能包含：
  - `cd ... && python ...`
  - `;`
  - `|`
  - 重定向
  - 子 Shell
- 风险判断只能做很粗的字符串启发式
- executor 也只能再把字符串拿去 `shlex.split()`

这会导致一个很现实的问题：

```text
“能审批”和“能安全执行”不是一回事
```

比如你现在 `experiment_plan.json` 里就出现过这种命令：

```bash
cd /data/tianshaoqi24/P4Transformer/modules && python setup.py install
```

这类命令：

- 从审批链角度，能进入 `human_review`
- 但从 executor 角度，当前 `shell=False` 风格并不适合直接执行这种复合 shell 命令

### 问题 2：审批没有绑定到“那个具体动作”

你当前的 [app/nodes/human_review_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/human_review_node.py:1) 只返回：

```python
{
    "user_approval": decision,
    "human_feedback": feedback
}
```

这意味着审批通过的只是一个抽象结论：

```text
approved
```

而不是：

```text
approved for action_hash=abc123...
```

这样会有一个很严重但很隐蔽的问题：

```text
人工审批的是动作 A
后来 pending_action 被修改成动作 B
但系统仍然可能沿用旧的 approved 结果执行 B
```

所以这一阶段的目标非常明确：

1. 把 `pending_action` 从自由文本命令升级为结构化动作  
2. 给动作计算稳定的 `action_hash`  
3. 让审批记录绑定 `action_hash`  
4. executor 真正执行前校验“当前动作”和“已审批动作”是否一致  

这一阶段做完后，你的执行链会从：

```text
run_commands -> pending_action(command string) -> approval -> executor
```

升级成：

```text
run_commands -> structured_action -> action_hash -> approval_record -> executor(hash verify)
```

这一步是从“能跑”走向“更可信、更安全”的重要升级。

---

## 先说清楚：这一阶段不需要重写 ExperimentPlan

当前 [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1) 里的 `RunCommand` 还是：

```python
class RunCommand(BaseModel):
    command: str
    cwd: str
    source: Literal["readme", "script", "config", "inferred", "need_confirm"]
    risk_level: Literal["low", "medium", "high"]
    reason: str
```

这一阶段**不建议直接改实验计划生成 prompt**，让 LLM 立刻改成直接输出结构化动作。

原因是：

- 改 planner 输出格式会牵动 prompt、schema、调试方式
- 你现在已经有稳定的 `run_commands` 产物
- 更合适的做法是：

```text
让 ExperimentPlan 继续输出 string command
然后在 action_builder 阶段，把它“转译”为 Structured Action
```

也就是说：

```text
V17 的重点不是重写 planner
而是增加“动作规范化层”
```

---

## 本阶段建议修改 / 新增的文件

```text
app/schemas.py
app/state.py
app/tools/action_tools.py
app/tools/safe_shell_tools.py
app/tools/exec_tools.py
app/nodes/action_builder_node.py
app/nodes/risk_check_node.py
app/nodes/human_review_node.py
app/nodes/executor_node.py
tests/test_structured_action_and_approval_hash.py
```

本阶段通常不需要修改：

```text
app/graph.py
```

因为主链路还是：

```text
action_builder
  -> risk_check
  -> human_review
  -> executor
```

只是节点之间传递的数据结构变得更严格了。

---

## 一、先补 Schema：定义 Structured Action 和 Approval Record

### 为什么要先定义 schema

如果没有明确的数据结构，后面很容易退回到：

```text
dict 里随便塞几个字段
```

短期能跑，长期会非常难维护。

所以这一阶段建议你先在 [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1) 里补两类结构：

1. `ExecutableAction`
2. `ApprovalRecord`

### 建议修改后的代码片段

下面这份代码是“在你现有 schemas 基础上新增”的版本，不是要你重写整个文件结构。

```python
from typing import Literal, Optional

from pydantic import BaseModel, Field

Confidence = Literal["low", "medium", "high"]


class Evidence(BaseModel):
    source_type: Literal["paper", "code", "readme", "config", "log"]
    source_path: str
    location: Optional[str] = None
    quote_or_summary: str
    confidence: Confidence = "medium"


class MethodModule(BaseModel):
    name: str
    description: str
    possible_keywords: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)


class PaperSummary(BaseModel):
    title: Optional[str] = None
    research_problem: str
    core_idea: str
    method_modules: list[MethodModule] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    experiment_settings: dict = Field(default_factory=dict)
    reproduction_risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


class RepoMap(BaseModel):
    repo_path: str
    readme_files: list[str] = Field(default_factory=list)
    train_entries: list[str] = Field(default_factory=list)
    eval_entries: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    model_files: list[str] = Field(default_factory=list)
    dataset_files: list[str] = Field(default_factory=list)
    loss_files: list[str] = Field(default_factory=list)
    important_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CodeCandidate(BaseModel):
    file_path: str
    symbols: list[str] = Field(default_factory=list)
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence = "medium"


class ModuleMapping(BaseModel):
    module_name: str
    candidates: list[CodeCandidate] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


class ExperimentStep(BaseModel):
    order: int
    name: str
    action: str
    source: Literal["paper", "readme", "config", "script", "inferred", "need_confirm"]
    evidence: list[Evidence] = Field(default_factory=list)
    risk: str | None = None
    done: bool = False


class RunCommand(BaseModel):
    command: str
    cwd: str
    source: Literal["readme", "script", "config", "inferred", "need_confirm"]
    risk_level: Literal["low", "medium", "high"]
    reason: str


class ExperimentPlan(BaseModel):
    goal: str
    environment_steps: list[ExperimentStep] = Field(default_factory=list)
    data_steps: list[ExperimentStep] = Field(default_factory=list)
    train_steps: list[ExperimentStep] = Field(default_factory=list)
    eval_steps: list[ExperimentStep] = Field(default_factory=list)
    run_commands: list[RunCommand] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


# 新增：
# 结构化的可执行动作。注意这里不再直接保存完整 shell 字符串，
# 而是拆成 program + args + cwd，这样更适合后续审批、风控和执行。
class ExecutableAction(BaseModel):
    action_id: str
    action_type: Literal["run_command"] = "run_command"

    # 比如 "python"、"torchrun"、"pip"
    program: str

    # 比如 ["train.py", "--config", "configs/msr.yaml"]
    args: list[str] = Field(default_factory=list)

    # 真正执行时的工作目录。
    # 这一项很重要，因为它允许我们把 "cd xxx && python yyy"
    # 这种 shell 风格命令转成更安全的结构化动作。
    cwd: str

    source: Literal["readme", "script", "config", "inferred", "need_confirm"]
    reason: str

    # 先给一个保守默认值。后面如果需要，
    # 可以按动作类型动态覆盖。
    timeout_seconds: int = 300

    # 第一阶段先只做很轻量的环境白名单控制。
    env_allowlist: dict[str, str] = Field(default_factory=dict)

    # 表示这个动作允许写哪些路径。
    # 第一阶段可以先只放 cwd，后面再做更细粒度限制。
    writable_paths: list[str] = Field(default_factory=list)

    # risk 信息会在 risk_check_node 里补充，不一定在 action_builder 时就有。
    risk: dict | None = None


# 新增：
# 人工审批记录。核心不是只有 approved / rejected，
# 而是把审批绑定到 action_hash。
class ApprovalRecord(BaseModel):
    approval_id: str
    action_id: str
    action_hash: str
    decision: Literal["approved", "rejected", "revise"]
    reviewer: str = "human"
    risk_level: str
    reviewed_at: str
    comment: str | None = None


class DebugReport(BaseModel):
    error_type: str
    most_likely_causes: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    check_order: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
```

### 这一段设计的核心思路

最关键的变化是：

```text
command string
    ↓
program + args + cwd
```

这是后面做下面这些能力的基础：

- 更可靠的风控
- 更稳定的 executor
- 更清晰的审批展示
- `action_hash` 计算
- 幂等执行

---

## 二、补 State：增加 `pending_action_hash` 和 `approval_record`

这一阶段你当前的 [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1) 还缺两个很关键的字段：

- `pending_action_hash`
- `approval_record`

### 建议修改后的代码

```python
from typing import Any, Optional, TypedDict


class ReproductionState(TypedDict, total=False):
    task_id: str
    user_query: str
    paper_path: Optional[str]
    repo_path: Optional[str]
    log_path: Optional[str]
    experiment_goal: Optional[str]

    paper_text_chunks: list[dict[str, Any]]
    paper_summary: dict[str, Any]
    method_modules: list[dict[str, Any]]
    repo_map: dict[str, Any]
    paper_code_mapping: list[dict[str, Any]]
    experiment_plan: dict[str, Any]
    debug_report: dict[str, Any]
    run_commands: list[dict[str, Any]]

    pending_action: Optional[dict[str, Any]]

    # 新增：
    # 当前待执行动作的哈希，用来和审批记录绑定。
    pending_action_hash: Optional[str]

    requires_approval: bool
    user_approval: Optional[str]
    human_feedback: Optional[str]

    # 新增：
    # 保存人类审批记录，而不仅仅是 approved / rejected 这一个字符串。
    approval_record: Optional[dict[str, Any]]

    execution_result: dict[str, Any]
    execution_log_path: Optional[str]
    last_action_result: dict[str, Any]
    final_status: Optional[str]

    output_files: list[str]
    final_report: Optional[str]
    messages: list[dict[str, Any]]
    step_count: int
    max_steps: int
    error: Optional[str]
    code_search_results: dict[str, Any]
```

---

## 三、新增动作工具层：`app/tools/action_tools.py`

这是这一阶段最值得单独抽出来的一层。

### 为什么要单独建 `action_tools.py`

因为 Structured Action 不是某一个节点的私有逻辑，而是整条审批执行链都会用到：

- `action_builder_node`
- `risk_check_node`
- `human_review_node`
- `executor_node`

这里建议把三类能力都放进工具层：

1. 从 `RunCommand.command` 解析出结构化动作  
2. 计算 `action_hash`  
3. 生成 `approval_record`  

### 建议新文件完整代码

```python
import hashlib
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.schemas import ApprovalRecord, ExecutableAction


# 这些 shell 特性会让“结构化动作 -> 安全执行”的边界变得模糊。
# 第一阶段建议直接不支持。
UNSUPPORTED_SHELL_MARKERS = [
    "&&",
    "||",
    ";",
    "|",
    ">",
    "<",
    "$(",
    "`",
]


# 这类标记通常意味着命令还不完整，不能直接执行。
PLACEHOLDER_MARKERS = [
    "[需要确认参数]",
    "<需要确认>",
    "<todo>",
    "TODO",
]


def _strip_leading_cd(command: str, cwd: str) -> tuple[str, str]:
    """
    处理常见的 shell 风格命令：
        cd /repo/modules && python setup.py install

    因为 Structured Action 已经有独立的 cwd 字段，
    所以更好的做法不是保留这段 "cd ... &&"，
    而是把它吸收到 cwd 中，然后把真正命令部分留下来。

    只有在匹配到非常明确的：
        cd <path> && <command>
    时，才做这类转换；否则保持原样。
    """

    stripped = command.strip()
    if not stripped.startswith("cd "):
        return stripped, cwd

    if "&&" not in stripped:
        return stripped, cwd

    left, right = stripped.split("&&", 1)
    left = left.strip()
    right = right.strip()

    try:
        tokens = shlex.split(left)
    except ValueError:
        return stripped, cwd

    if len(tokens) == 2 and tokens[0] == "cd":
        return right, tokens[1]

    return stripped, cwd


def _contains_unsupported_shell_syntax(command: str) -> bool:
    """
    检查命令里是否还包含不支持的 shell 特性。
    """

    return any(marker in command for marker in UNSUPPORTED_SHELL_MARKERS)


def _contains_placeholder(command: str) -> bool:
    """
    检查命令中是否还保留“待确认参数”占位符。
    这类命令不应该直接进入 executor。
    """

    lowered = command.lower()
    return any(marker.lower() in lowered for marker in PLACEHOLDER_MARKERS)


def build_run_action_from_command(
    *,
    command: str,
    cwd: str,
    source: str,
    reason: str,
    timeout_seconds: int = 300,
) -> dict:
    """
    将 ExperimentPlan 中的 RunCommand 转换成结构化动作。

    当前阶段的设计目标是：
    1. 继续允许 planner 输出字符串命令；
    2. 但在 action_builder 节点，把字符串收紧成更安全的结构化动作；
    3. 一旦命令包含不支持的 shell 语法，就拒绝转成 executable action。
    """

    normalized_command, normalized_cwd = _strip_leading_cd(command, cwd)

    # 去掉前缀 cd 后，如果命令里仍然带有复杂 shell 特性，就拒绝。
    if _contains_unsupported_shell_syntax(normalized_command):
        raise ValueError(
            "unsupported shell syntax in run command; please convert it into a single executable command"
        )

    if _contains_placeholder(normalized_command):
        raise ValueError(
            "run command still contains unresolved placeholders; do not execute yet"
        )

    try:
        tokens = shlex.split(normalized_command)
    except ValueError as exc:
        raise ValueError(f"invalid shell quoting: {exc}") from exc

    if not tokens:
        raise ValueError("empty run command")

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
    )

    return action.model_dump()


def compute_action_hash(action: dict) -> str:
    """
    为动作计算稳定哈希。

    注意这里故意只使用“真正影响执行效果”的字段，
    而不把 reason、risk 这类展示/派生信息塞进去。
    否则仅仅因为风控解释文案变了，action_hash 也会变化。
    """

    material = {
        "action_type": action.get("action_type"),
        "program": action.get("program"),
        "args": action.get("args", []),
        "cwd": action.get("cwd"),
        "env_allowlist": action.get("env_allowlist", {}),
        "timeout_seconds": action.get("timeout_seconds"),
        "writable_paths": action.get("writable_paths", []),
    }

    payload = json.dumps(material, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_approval_record(
    *,
    action: dict,
    action_hash: str,
    decision: str,
    risk_level: str,
    comment: str | None,
) -> dict:
    """
    根据当前动作和审批结果，生成结构化审批记录。
    """

    record = ApprovalRecord(
        approval_id=f"approval_{uuid4().hex[:12]}",
        action_id=action["action_id"],
        action_hash=action_hash,
        decision=decision,
        reviewer="human",
        risk_level=risk_level,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        comment=comment,
    )
    return record.model_dump()
```

### 为什么这份工具层代码值得单独做

因为它解决了三个当前最实际的问题：

#### 1. 把 `cd ... && xxx` 吸收到 `cwd`

这正好对应你现在项目里真实出现过的命令形式。

#### 2. 拒绝复杂 shell 语法

这样后面的 executor 才能继续坚持：

```text
shell=False
```

#### 3. `action_hash` 成为审批和执行之间的桥

这就是本阶段标题里 `Approval Hash` 的真正落地点。

---

## 四、更新风控工具：从“检查命令字符串”切到“检查结构化动作”

你当前的 [app/tools/safe_shell_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/safe_shell_tools.py:1) 还是：

```python
assess_command_risk(command: str)
```

既然这一阶段我们已经有了结构化动作，更合理的做法是评估：

```text
program
args
cwd
```

而不是继续把所有逻辑压在原始字符串上。

### 建议修改后的完整代码

```python
from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["low", "medium", "high", "blocked"]


BLOCKED_PROGRAMS = {
    "rm",
    "sudo",
    "chmod",
    "chown",
    "mkfs",
    "dd",
    "shutdown",
    "reboot",
    "git",
}


@dataclass
class ActionRisk:
    program: str
    args: list[str]
    risk_level: RiskLevel
    reason: str
    blocked: bool


def assess_action_risk(action: dict) -> ActionRisk:
    """
    根据结构化动作进行风控。

    这比直接分析完整 shell 字符串更稳定，
    因为 action_builder 已经提前把 cwd / command 拆开了。
    """

    program = action.get("program", "")
    args = action.get("args", [])

    if not program:
        return ActionRisk(
            program="",
            args=[],
            risk_level="blocked",
            reason="missing executable program",
            blocked=True,
        )

    if program in BLOCKED_PROGRAMS:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="blocked",
            reason=f"program is blocked: {program}",
            blocked=True,
        )

    # 环境变更类命令风险更高，但不一定完全禁止。
    if program in {"pip", "conda"} and "install" in args:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="high",
            reason="environment-changing command requires approval",
            blocked=False,
        )

    # python -m xxx 也视为潜在环境/脚本变更入口，风险给高一点更稳妥。
    if program == "python" and "-m" in args:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="high",
            reason="python module execution requires explicit approval",
            blocked=False,
        )

    if program in {"python", "torchrun", "accelerate", "bash"}:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="medium",
            reason="script or training execution requires approval",
            blocked=False,
        )

    return ActionRisk(
        program=program,
        args=args,
        risk_level="medium",
        reason="unknown executable, review before execution",
        blocked=False,
    )
```

### 这里为什么把 `bash` 留在 medium

这是一个可以继续讨论的点。

你可以选择：

- `medium`
- `high`
- `blocked`

如果你当前项目里大量训练入口还是 `bash train.sh` 这类形式，直接 `blocked` 会影响推进。  
所以这一阶段更保守的做法是：

```text
先允许，但一定审批
```

等你后面把 Docker / sandbox 真补齐后，再进一步收紧。

---

## 五、改 `action_builder_node`：真正生成 Structured Action

这是本阶段非常核心的节点修改。

你当前的 [app/nodes/action_builder_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/action_builder_node.py:1) 直接把字符串命令塞进 `pending_action`。

这一阶段应该改成：

1. 从 `run_commands[0]` 读取原始命令  
2. 调用 `build_run_action_from_command(...)` 转成结构化动作  
3. 计算 `pending_action_hash`  
4. 一起写回 state  

### 建议修改后的完整代码

```python
from app.tools.action_tools import build_run_action_from_command, compute_action_hash


def action_builder_node(state: dict) -> dict:
    """
    从 ExperimentPlan 的 run_commands 中挑出一个待执行动作，
    并把原始字符串命令转换成结构化动作。
    """

    existing_action = state.get("pending_action")
    if existing_action:
        return {
            "pending_action": existing_action,
            "pending_action_hash": state.get("pending_action_hash")
            or compute_action_hash(existing_action),
        }

    run_commands = state.get("run_commands", [])
    if not run_commands:
        return {
            "pending_action": None,
            "pending_action_hash": None,
            "final_status": "no_action",
        }

    first_command = run_commands[0]
    cwd = first_command.get("cwd") or state.get("repo_path") or "."

    try:
        action = build_run_action_from_command(
            command=first_command["command"],
            cwd=cwd,
            source=first_command.get("source", "inferred"),
            reason=first_command.get("reason", "from experiment plan"),
            timeout_seconds=300,
        )
    except ValueError as exc:
        return {
            "pending_action": None,
            "pending_action_hash": None,
            "final_status": "invalid_action",
            "error": str(exc),
        }

    action_hash = compute_action_hash(action)

    return {
        "pending_action": action,
        "pending_action_hash": action_hash,
    }
```

### 这一版 action_builder 带来的实际收益

#### 1. 当前 `cd ... && python ...` 这种命令会变得可执行

因为工具层会把它转成：

```python
{
    "program": "python",
    "args": ["setup.py", "install"],
    "cwd": "/data/tianshaoqi24/P4Transformer/modules",
}
```

这比直接把复合 shell 命令扔给 executor 稳定得多。

#### 2. 不完整命令会被挡在 action_builder 阶段

例如：

```bash
python train-msr-small.py [需要确认参数]
```

这类命令现在应该在这里就被标记为：

```text
invalid_action
```

而不是走到 executor 再报一堆莫名其妙的执行错误。

---

## 六、改 `risk_check_node`：改为基于 Structured Action 风控

### 建议修改后的完整代码

```python
from app.tools.safe_shell_tools import assess_action_risk


def risk_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {
            "requires_approval": False,
            "pending_action": None,
            "pending_action_hash": None,
        }

    action_type = pending_action.get("action_type")

    if action_type == "run_command":
        risk = assess_action_risk(pending_action)
        pending_action["risk"] = {
            "level": risk.risk_level,
            "reason": risk.reason,
            "blocked": risk.blocked,
        }
        return {
            "pending_action": pending_action,
            "pending_action_hash": state.get("pending_action_hash"),
            "requires_approval": not risk.blocked,
            "error": risk.reason if risk.blocked else None,
        }

    if action_type in {"modify_config", "write_repo_file"}:
        pending_action["risk"] = {
            "level": "high",
            "reason": "action modifies user repository",
            "blocked": False,
        }
        return {
            "pending_action": pending_action,
            "pending_action_hash": state.get("pending_action_hash"),
            "requires_approval": True,
        }

    pending_action["risk"] = {
        "level": "medium",
        "reason": "unknown action type",
        "blocked": False,
    }
    return {
        "pending_action": pending_action,
        "pending_action_hash": state.get("pending_action_hash"),
        "requires_approval": True,
    }
```

### 这里有一个小细节

你原来在多个地方写的是：

```python
action_type == "run_command"
```

但当前 `action_builder_node` 里写的是：

```python
"type": "run_command"
```

这一阶段建议统一成：

```python
action_type
```

因为 `ExecutableAction` schema 里就是：

```python
action_type: Literal["run_command"]
```

统一字段名可以减少很多后面排查时的低级错误。

---

## 七、改 `human_review_node`：让审批记录绑定 `action_hash`

这一步是本阶段标题里的另一个核心。

### 建议修改后的完整代码

```python
from langgraph.types import interrupt

from app.tools.action_tools import build_approval_record, compute_action_hash


def human_review_node(state: dict) -> dict:
    """
    向人类展示当前待执行动作，并记录与 action_hash 绑定的审批结果。
    """

    if not state.get("requires_approval"):
        return {"user_approval": "not_required"}

    pending_action = state.get("pending_action")
    if not pending_action:
        return {"user_approval": "missing_action"}

    action_hash = state.get("pending_action_hash") or compute_action_hash(pending_action)

    payload = {
        "message": "请确认是否允许执行该操作",
        "action": pending_action,
        "action_hash": action_hash,
        "allowed_responses": ["approved", "rejected", "revise"],
    }

    response = interrupt(payload)

    if isinstance(response, dict):
        decision = response.get("decision", "rejected")
        feedback = response.get("feedback")
    else:
        decision = str(response)
        feedback = None

    approval_record = build_approval_record(
        action=pending_action,
        action_hash=action_hash,
        decision=decision,
        risk_level=pending_action.get("risk", {}).get("level", "unknown"),
        comment=feedback,
    )

    return {
        "user_approval": decision,
        "human_feedback": feedback,
        "approval_record": approval_record,
        "pending_action_hash": action_hash,
    }
```

### 这一版最大的变化

以前审批只保存：

```text
approved / rejected / revise
```

现在审批会保存：

```text
approval_id
action_id
action_hash
decision
risk_level
comment
reviewed_at
```

这意味着后面 executor 能真正做这一步检查：

```text
当前动作还是不是当时被审批通过的那个动作？
```

---

## 八、改执行工具：真正执行 Structured Action

你当前的 [app/tools/exec_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/exec_tools.py:1) 还是：

```python
run_command_safe(command: str, cwd: str, timeout: int = 300)
```

这一阶段更合理的做法是：

```python
run_action_safe(action: dict)
```

### 建议修改后的完整代码

```python
import subprocess


def run_action_safe(action: dict) -> dict:
    """
    执行结构化动作。

    当前阶段只支持 action_type == "run_command"，
    并坚持 shell=False，从而保持执行边界清晰。
    """

    program = action.get("program")
    args = action.get("args", [])
    cwd = action.get("cwd", ".")
    timeout = action.get("timeout_seconds", 300)

    if not program:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": "missing program",
            "combined_output": "missing program",
            "timeout": False,
        }

    tokens = [program, *args]

    try:
        completed = subprocess.run(
            tokens,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            shell=False,
        )

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        combined_output = stdout

        if stderr:
            if combined_output:
                combined_output += "\n\n[stderr]\n" + stderr
            else:
                combined_output = "[stderr]\n" + stderr

        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "combined_output": combined_output,
            "timeout": False,
        }

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        combined_output = stdout

        if stderr:
            if combined_output:
                combined_output += "\n\n[stderr]\n" + stderr
            else:
                combined_output = "[stderr]\n" + stderr

        if not combined_output:
            combined_output = f"command timed out after {timeout} seconds"

        return {
            "ok": False,
            "returncode": None,
            "stdout": stdout,
            "stderr": stderr or f"command timed out after {timeout} seconds",
            "combined_output": combined_output,
            "timeout": True,
        }

    except FileNotFoundError as exc:
        message = str(exc)
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": message,
            "combined_output": message,
            "timeout": False,
        }
```

### 为什么这一步很重要

到这一阶段为止，executor 应该彻底摆脱：

```text
再拿自由文本命令临时 shlex.split
```

而是建立这种链：

```text
LLM 产出 run_command string
  ↓
action_builder 转成 Structured Action
  ↓
executor 只消费 Structured Action
```

这样职责才是清晰的。

---

## 九、改 `executor_node`：执行前校验审批哈希

这是本阶段的收口点。

### 建议修改后的完整代码

```python
from app.config import settings
from app.tools.action_tools import compute_action_hash
from app.tools.exec_tools import run_action_safe


def executor_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {"final_status": "no_pending_action"}

    decision = state.get("user_approval")

    if decision == "rejected":
        return {
            "final_status": "rejected",
            "last_action_result": {
                "status": "rejected",
                "pending_action": pending_action,
            },
        }

    if decision == "revise":
        return {
            "final_status": "revise_requested",
            "last_action_result": {
                "status": "revise_requested",
                "pending_action": pending_action,
                "human_feedback": state.get("human_feedback"),
            },
        }

    if decision not in {"approved", "not_required"}:
        return {
            "final_status": "not_executed",
            "last_action_result": {
                "status": "not_executed",
                "pending_action": pending_action,
                "reason": f"unsupported approval status: {decision}",
            },
        }

    action_type = pending_action.get("action_type")
    if action_type != "run_command":
        return {
            "final_status": "unsupported_action",
            "last_action_result": {
                "status": "unsupported_action",
                "pending_action": pending_action,
            },
            "error": f"unsupported action type: {action_type}",
        }

    current_action_hash = compute_action_hash(pending_action)

    # 如果是审批通过的动作，必须检查审批记录绑定的 action_hash
    # 是否和当前待执行动作一致。
    if decision == "approved":
        approval_record = state.get("approval_record")
        if not approval_record:
            return {
                "final_status": "missing_approval_record",
                "last_action_result": {
                    "status": "missing_approval_record",
                    "pending_action": pending_action,
                },
            }

        approved_hash = approval_record.get("action_hash")
        if approved_hash != current_action_hash:
            return {
                "final_status": "stale_approval",
                "last_action_result": {
                    "status": "stale_approval",
                    "pending_action": pending_action,
                    "approved_hash": approved_hash,
                    "current_hash": current_action_hash,
                },
                "error": "approval record does not match current action",
            }

    result = run_action_safe(pending_action)

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = settings.output_dir / "execution.log"
    log_path.write_text(result["combined_output"], encoding="utf-8")

    final_status = "succeeded" if result["ok"] else "failed"

    payload = {
        "execution_result": result,
        "execution_log_path": str(log_path),
        "last_action_result": {
            "status": final_status,
            "pending_action": pending_action,
            "returncode": result["returncode"],
        },
        "final_status": final_status,
        "output_files": [
            *state.get("output_files", []),
            str(log_path),
        ],
    }

    if final_status == "failed":
        payload["log_path"] = str(log_path)

    return payload
```

### 这一版 executor 新增了什么保护

以前：

```text
approved -> execute current pending_action
```

现在：

```text
approved
  -> approval_record.action_hash == compute_action_hash(current pending_action)?
      yes -> execute
      no  -> stale_approval，拒绝执行
```

这就是这一阶段最重要的安全收益。

---

## 十、建议新增测试：`tests/test_structured_action_and_approval_hash.py`

这个阶段非常值得补一份单测，因为它主要是“数据结构和执行边界”的逻辑，不依赖完整大图。

### 建议新文件完整代码

```python
from unittest.mock import patch

from app.nodes.action_builder_node import action_builder_node
from app.nodes.executor_node import executor_node
from app.nodes.human_review_node import human_review_node
from app.nodes.risk_check_node import risk_check_node
from app.tools.action_tools import build_run_action_from_command, compute_action_hash


def test_build_run_action_strips_leading_cd_and_uses_cwd() -> None:
    action = build_run_action_from_command(
        command="cd /repo/modules && python setup.py install",
        cwd="/repo",
        source="inferred",
        reason="build extension",
    )

    assert action["program"] == "python"
    assert action["args"] == ["setup.py", "install"]
    assert action["cwd"] == "/repo/modules"
    assert action["action_type"] == "run_command"


def test_build_run_action_rejects_placeholder_command() -> None:
    try:
        build_run_action_from_command(
            command="python train.py [需要确认参数]",
            cwd="/repo",
            source="script",
            reason="train model",
        )
    except ValueError as exc:
        assert "unresolved placeholders" in str(exc)
    else:
        raise AssertionError("expected ValueError for unresolved placeholder")


def test_action_builder_returns_structured_action_and_hash() -> None:
    state = {
        "repo_path": "/repo",
        "run_commands": [
            {
                "command": "cd /repo/modules && python setup.py install",
                "cwd": "/repo/modules",
                "source": "inferred",
                "reason": "build extension",
            }
        ],
    }

    result = action_builder_node(state)

    assert result["pending_action"]["program"] == "python"
    assert result["pending_action"]["args"] == ["setup.py", "install"]
    assert result["pending_action_hash"]


def test_risk_check_node_uses_structured_action() -> None:
    state = {
        "pending_action": {
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py"],
            "cwd": "/repo",
            "source": "script",
            "reason": "train",
            "action_id": "action_001",
        },
        "pending_action_hash": "hash_001",
    }

    result = risk_check_node(state)

    assert result["requires_approval"] is True
    assert result["pending_action"]["risk"]["level"] == "medium"


def test_human_review_node_returns_approval_record_with_hash() -> None:
    state = {
        "requires_approval": True,
        "pending_action_hash": "hash_001",
        "pending_action": {
            "action_id": "action_001",
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py"],
            "cwd": "/repo",
            "source": "script",
            "reason": "train",
            "risk": {
                "level": "medium",
                "reason": "training execution requires approval",
                "blocked": False,
            },
        },
    }

    with patch(
        "app.nodes.human_review_node.interrupt",
        return_value={"decision": "approved", "feedback": "可以执行"},
    ):
        result = human_review_node(state)

    assert result["user_approval"] == "approved"
    assert result["approval_record"]["action_hash"] == "hash_001"
    assert result["approval_record"]["decision"] == "approved"


def test_executor_rejects_stale_approval() -> None:
    pending_action = {
        "action_id": "action_001",
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": "/repo",
        "source": "script",
        "reason": "train",
    }

    state = {
        "pending_action": pending_action,
        "user_approval": "approved",
        "approval_record": {
            "approval_id": "approval_001",
            "action_id": "action_001",
            "action_hash": "some_old_hash",
            "decision": "approved",
            "reviewer": "human",
            "risk_level": "medium",
            "reviewed_at": "2026-01-01T00:00:00+00:00",
            "comment": None,
        },
    }

    result = executor_node(state)

    assert result["final_status"] == "stale_approval"


def test_executor_runs_when_hash_matches() -> None:
    pending_action = {
        "action_id": "action_001",
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": "/repo",
        "source": "script",
        "reason": "train",
    }
    action_hash = compute_action_hash(pending_action)

    state = {
        "pending_action": pending_action,
        "user_approval": "approved",
        "approval_record": {
            "approval_id": "approval_001",
            "action_id": "action_001",
            "action_hash": action_hash,
            "decision": "approved",
            "reviewer": "human",
            "risk_level": "medium",
            "reviewed_at": "2026-01-01T00:00:00+00:00",
            "comment": None,
        },
        "output_files": [],
    }

    with patch(
        "app.nodes.executor_node.run_action_safe",
        return_value={
            "ok": True,
            "returncode": 0,
            "stdout": "done",
            "stderr": "",
            "combined_output": "done",
            "timeout": False,
        },
    ):
        result = executor_node(state)

    assert result["final_status"] == "succeeded"
```

### 这份测试在验证什么

它验证的是本阶段最重要的 4 件事：

1. `cd ... && python ...` 能被规范化  
2. 不完整命令会被拒绝  
3. 审批记录会绑定 `action_hash`  
4. executor 会拒绝使用过期审批  

---

## 十一、运行方式与验收标准

### 先跑单测

```bash
python -m pytest tests/test_structured_action_and_approval_hash.py
```

### 再跑项目主链

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer/ \
  --thread-id action-hash-001
```

### 然后查看 state

```bash
python -m app.main show-state --thread-id action-hash-001
```

你希望在 state 里能看到：

- `pending_action`
- `pending_action_hash`

如果已经做了审批恢复，再继续：

```bash
python -m app.main resume-review action-hash-001 --decision approved
```

再次查看 state，你希望能看到：

- `approval_record`
- `user_approval`
- `human_feedback`

---

## 十二、本阶段完成后的验收标准

我建议你把验收写得非常具体：

### 1. `pending_action` 不再保存自由文本 shell 命令

而是至少包含：

- `action_id`
- `action_type`
- `program`
- `args`
- `cwd`

### 2. `pending_action_hash` 能稳定生成

同一个动作的哈希应保持一致；关键执行字段变了，哈希应变化。

### 3. `human_review_node` 会生成 `approval_record`

且其中包含：

- `action_id`
- `action_hash`
- `decision`

### 4. `executor_node` 会校验审批是否过期

如果 `approval_record.action_hash != compute_action_hash(current_action)`，必须拒绝执行。

### 5. 当前项目里常见的 `cd ... && python ...` 能被规范化

这条对你当前仓库很重要，因为你已经真实遇到过这种 planner 输出。

---

## 十三、这一阶段做完后，下一步最自然接什么

这个阶段做完以后，最自然的下一步通常有两个方向：

### 方向一：Preflight

因为 Structured Action 一旦稳定，你就更容易在真正执行前插入：

- static preflight
- runtime probe
- smoke test

### 方向二：轻量 Idempotency Guard / Action Ledger

因为现在你已经有：

- `action_id`
- `action_hash`
- `approval_record`

再往前一步，就是引入：

- action lifecycle
- attempt count
- 成功动作缓存

所以 V17 其实是在给更完整的执行安全系统打地基。

---

## 十四、最后的整体理解

这一阶段最重要的不是“多写几个字段”，而是把执行系统的边界真正收紧：

```text
LLM 提建议
  ↓
action_builder 规范化动作
  ↓
risk_check 做结构化风控
  ↓
human_review 审批具体动作哈希
  ↓
executor 校验审批与当前动作是否一致
```

这会让你的系统从：

```text
能审批字符串命令
```

升级成：

```text
能审批并验证“这个具体动作”
```

这一步虽然不像 durable checkpoint 那样显眼，但从 Agent 工程深度来说，非常关键。
