# 18. 闭环后第三阶段：Command Selection 与可编辑 Run Commands

## 这一阶段的目标

到上一阶段为止，你已经补上了：

```text
Structured Action
Approval Hash
Durable Checkpoint
跨进程 Resume
```

这说明你现在已经具备一条比较完整的执行链：

```text
experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
  -> executor
```

但是当前这条链还有一个非常实际的问题：

### 问题 1：`action_builder_node` 默认只拿 `run_commands[0]`

你现在的 [app/nodes/action_builder_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/action_builder_node.py:1) 逻辑本质上还是：

```python
first_command = run_commands[0]
```

这会带来两个现实问题：

- 第一个命令可能只是“需要确认参数”的草稿命令
- 第二个、第三个命令反而更适合先执行

你之前就已经真实遇到过这种情况：

```json
"run_commands": [
  {
    "command": "python train-ntu60.py --dataset_path <path_to_ntu60> --other_args ...",
    ...
  },
  {
    "command": "python train-msr-small.py --dataset_path <path_to_msr> --other_args ...",
    ...
  },
  {
    "command": "cd modules && python setup.py install",
    ...
  }
]
```

在这个例子里：

- 第 1 条和第 2 条都还不完整
- 第 3 条反而是更适合先执行的命令

但如果系统死板地只拿第一个，就会直接进入：

```text
invalid_action
```

而不会进入更后面的审批和执行链。

### 问题 2：用户无法在执行前修正命令

即使 planner 找到了大致正确的训练脚本，现实里也经常还需要补参数，例如：

- `--dataset_path`
- `--batch_size`
- `--config`
- `--gpu`

如果系统完全不让用户介入，就会很容易出现：

```text
planner 给了“接近正确”的命令
但因为还差一两个参数，整条执行链无法推进
```

所以这一阶段的目标非常明确：

1. 在终端打印全部 `run_commands`  
2. 让用户决定“先执行哪一条”  
3. 允许用户修改一个或多个 `run_command.command`  
4. 修改后的命令仍然继续走：
   - `action_builder`
   - `Structured Action`
   - `pending_action_hash`
   - `human_review`
   - `executor`

也就是说，这一阶段不是绕过前面做好的安全链，而是在安全链**前面**插入一个“用户命令确认层”。

最终目标图会从：

```text
experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
  -> executor
```

变成：

```text
experiment_plan
  -> command_selection
      -> 终端展示全部 run_commands
      -> 用户选择 index
      -> 用户可选修改 1~N 条 command
  -> action_builder
      -> 基于选择后的命令生成 Structured Action
  -> risk_check
  -> human_review
  -> executor
```

---

## 先明确：为什么不直接在 `run_graph()` 里用 `input()`

你当然可以在 [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:1) 里直接写终端交互，例如：

```python
choice = input("select run command index: ")
```

但我不建议这么做。

### 原因

因为你现在这个项目已经不是单纯的线性脚本了，而是：

```text
LangGraph
Checkpoint
interrupt / resume
跨进程恢复
```

如果你在 CLI 入口里直接做阻塞式 `input()`，会带来几个问题：

- 无法利用 durable checkpoint
- 用户选到一半退出后，无法恢复
- 选择过程不会进入 graph state
- 后续审计时，不知道用户当时选了哪一条、改了什么

所以更合适的做法是：

```text
把“命令选择”做成 graph 节点
并使用 interrupt / resume 机制
```

这能和你已有的：

- `human_review_node`
- `resume_review`
- `show_state`
- `list_checkpoints`

形成统一的交互模型。

---

## 本阶段建议修改 / 新增的文件

```text
app/schemas.py
app/state.py
app/nodes/command_selection_node.py
app/nodes/action_builder_node.py
app/graph.py
app/main.py
tests/test_command_selection_node.py
```

这一阶段通常不需要修改：

```text
app/nodes/risk_check_node.py
app/nodes/human_review_node.py
app/nodes/executor_node.py
```

因为这些节点仍然消费“结构化动作”这一层，不需要知道用户是怎么选命令的。

---

## 一、先补 Schema：定义命令编辑与选择结果

当前 [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1) 里还没有“用户如何修改 run_commands”的结构。

这一阶段建议增加三类对象：

1. `CommandEdit`
2. `CommandSelectionResponse`
3. `CommandSelectionRecord`

### 建议修改后的代码片段

下面这份代码是在你当前 `schemas.py` 基础上新增的部分，不是要求你把整个文件重写。

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


class ApprovalRecord(BaseModel):
    approval_id: str
    action_id: str
    action_hash: str
    decision: Literal["approved", "rejected", "revise"]
    reviewer: str = "human"
    risk_level: str
    reviewed_at: str
    comment: str | None = None


# 新增：
# 用户对某一条 run_command 的编辑。
# 这里故意只允许改 command 字符串，
# 不允许用户直接改 program/args/cwd 这些结构化字段。
# 因为后面仍然要交给 action_builder 去重新规范化和校验。
class CommandEdit(BaseModel):
    index: int
    command: str


# 新增：
# 从 interrupt 恢复时，用户给 command_selection_node 的输入结构。
# selected_index 表示“本次优先执行哪一条”；
# edits 表示“可选地修改一条或多条 command”。
class CommandSelectionResponse(BaseModel):
    selected_index: int
    edits: list[CommandEdit] = Field(default_factory=list)


# 新增：
# 用于审计本次命令选择和编辑记录。
class CommandSelectionRecord(BaseModel):
    selected_index: int
    edits: list[CommandEdit] = Field(default_factory=list)
    original_count: int
    reviewed_at: str


class DebugReport(BaseModel):
    error_type: str
    most_likely_causes: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    check_order: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
```

### 这一层设计的核心思路

最关键的是：

```text
用户只改原始 command string
    ↓
系统后面仍然重新走 Structured Action 规范化
```

这样可以保证：

- 用户参与修正命令
- 但不会绕过：
  - action_builder
  - pending_action_hash
  - risk_check
  - human_review

---

## 二、补 State：增加选择结果和编辑后的命令列表

### 为什么要分开保存原始命令和编辑后命令

不建议直接覆盖：

```python
state["run_commands"]
```

更好的做法是分两层：

- `run_commands`
  - planner 原始产物
- `edited_run_commands`
  - 用户修改后的版本

这样你后面调试和审计会轻松很多。

### 建议修改 `app/state.py`

把 [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1) 改成下面这种结构：

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

    # planner 原始输出
    run_commands: list[dict[str, Any]]

    # 新增：
    # 用户修改后的 run_commands。
    # 如果用户没有修改，这个字段可以不存在或为空。
    edited_run_commands: list[dict[str, Any]]

    # 新增：
    # 用户最终选择先执行哪一条命令。
    selected_run_command_index: Optional[int]

    # 新增：
    # 这次选择/编辑过程的审计记录。
    command_selection_record: Optional[dict[str, Any]]

    pending_action: Optional[dict[str, Any]]
    pending_action_hash: Optional[str]
    requires_approval: bool
    user_approval: Optional[str]
    human_feedback: Optional[str]
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

## 三、新增节点：`app/nodes/command_selection_node.py`

这是本阶段的核心节点。

### 这个节点要完成什么

1. 从 state 里拿出全部 `run_commands`
2. 在终端打印它们，方便用户看
3. 调用 `interrupt(payload)` 暂停
4. 等待用户通过 resume 提交：
   - `selected_index`
   - 可选的多条 `edits`
5. 产出：
   - `selected_run_command_index`
   - `edited_run_commands`
   - `command_selection_record`

### 为什么这个节点可以直接打印到终端

通常我们会尽量避免节点直接负责 UI 展示，但这里是个例外。

原因是你当前项目的主要入口还是 CLI，而用户明确希望：

```text
在终端看到全部 run_commands，再决定先执行哪个
```

所以这一阶段可以接受：

```python
print(...)
```

直接发生在 `command_selection_node` 里。

### 建议新文件完整代码

```python
from copy import deepcopy
from datetime import datetime, timezone
import json

from langgraph.types import interrupt
from rich import print

from app.config import settings
from app.schemas import (
    CommandEdit,
    CommandSelectionRecord,
    CommandSelectionResponse,
)


def _render_run_commands_for_terminal(run_commands: list[dict]) -> None:
    """
    在终端输出全部 run_commands，帮助用户做选择。

    这里使用 rich.print 只是为了让 CLI 下显示更清楚，
    不影响 graph 本身的状态逻辑。
    """

    print("\n[bold cyan]Available run_commands[/bold cyan]")
    for index, item in enumerate(run_commands):
        print(f"\n[yellow][{index}][/yellow] {item.get('command', '')}")
        print(f"  cwd: {item.get('cwd', '')}")
        print(f"  source: {item.get('source', '')}")
        print(f"  risk_level: {item.get('risk_level', '')}")
        print(f"  reason: {item.get('reason', '')}")


def _normalize_interrupt_response(response: object) -> CommandSelectionResponse:
    """
    将 interrupt 的返回值规范化成 CommandSelectionResponse。

    支持几种形式：
    1. dict: {"selected_index": 2, "edits": [...]}
    2. int: 2
    3. str: "2"
    """

    if isinstance(response, dict):
        return CommandSelectionResponse.model_validate(response)

    if isinstance(response, int):
        return CommandSelectionResponse(selected_index=response, edits=[])

    if isinstance(response, str) and response.isdigit():
        return CommandSelectionResponse(selected_index=int(response), edits=[])

    raise ValueError("invalid command selection response")


def _apply_command_edits(
    run_commands: list[dict],
    edits: list[CommandEdit],
) -> list[dict]:
    """
    基于原始 run_commands 生成一份“应用编辑后的副本”。

    这里用 deepcopy，是为了确保：
    - planner 原始输出 run_commands 不被覆盖
    - 用户修改结果单独保存在 edited_run_commands
    """

    effective_commands = deepcopy(run_commands)
    for edit in edits:
        if edit.index < 0 or edit.index >= len(effective_commands):
            raise ValueError(f"edit index out of range: {edit.index}")

        new_command = edit.command.strip()
        if not new_command:
            raise ValueError(f"edited command cannot be empty: index={edit.index}")

        effective_commands[edit.index]["command"] = new_command

    return effective_commands


def command_selection_node(state: dict) -> dict:
    """
    在 action_builder 之前，允许用户：
    1. 查看全部 run_commands；
    2. 选择先执行哪一条；
    3. 可选修改一条或多条 command。

    这一步并不会绕过 Structured Action，
    修改后的命令仍然会继续交给 action_builder 去规范化。
    """

    run_commands = state.get("run_commands", [])
    if not run_commands:
        return {
            "selected_run_command_index": None,
            "edited_run_commands": [],
        }

    _render_run_commands_for_terminal(run_commands)

    payload = {
        "message": "请选择先执行哪个 run_command，并可选修改一个或多个 command",
        "run_commands": run_commands,
        "resume_example": {
            "selected_index": 0,
            "edits": [
                {"index": 0, "command": "python train.py --dataset_path /data/demo"}
            ],
        },
    }

    response = interrupt(payload)
    parsed = _normalize_interrupt_response(response)

    if parsed.selected_index < 0 or parsed.selected_index >= len(run_commands):
        raise ValueError(f"selected_index out of range: {parsed.selected_index}")

    effective_commands = _apply_command_edits(run_commands, parsed.edits)

    record = CommandSelectionRecord(
        selected_index=parsed.selected_index,
        edits=parsed.edits,
        original_count=len(run_commands),
        reviewed_at=datetime.now(timezone.utc).isoformat(),
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    record_path = settings.output_dir / "command_selection_record.json"
    effective_path = settings.output_dir / "effective_run_commands.json"

    record_path.write_text(
        record.model_dump_json(indent=2),
        encoding="utf-8",
    )
    effective_path.write_text(
        json.dumps(effective_commands, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "selected_run_command_index": parsed.selected_index,
        "edited_run_commands": effective_commands,
        "command_selection_record": record.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(record_path),
            str(effective_path),
        ],
    }
```

### 这一版节点的几个关键点

#### 1. 终端输出 run_commands

这正是你想要的用户体验：

```text
run_graph
  -> command_selection_node
  -> 终端打印所有 run_commands
  -> interrupt
```

#### 2. 支持一次修改多条 command

通过：

```json
"edits": [
  {"index": 0, "command": "..."},
  {"index": 2, "command": "..."}
]
```

就能实现批量修改。

#### 3. 修改不覆盖 planner 原始产物

这对调试特别重要。

---

## 四、改 `action_builder_node`：优先使用用户选择和编辑后的命令

这一阶段 `action_builder` 的职责会变成：

1. 读取 `edited_run_commands`，如果没有则回退到 `run_commands`
2. 读取 `selected_run_command_index`
3. 只把“用户选中的那一条”转成 Structured Action

### 建议修改后的完整代码

```python
from app.tools.action_tools import build_run_action_from_command, compute_action_hash


def action_builder_node(state: dict) -> dict:
    """
    从用户选择后的 run_commands 中挑出一条命令，
    转成 Structured Action，并生成 pending_action_hash。
    """

    existing_action = state.get("pending_action")
    if existing_action:
        return {
            "pending_action": existing_action,
            "pending_action_hash": state.get("pending_action_hash")
            or compute_action_hash(existing_action),
        }

    # 如果用户有修改后的命令列表，优先使用它；
    # 否则回退到 planner 原始输出。
    effective_run_commands = state.get("edited_run_commands") or state.get("run_commands", [])

    if not effective_run_commands:
        return {
            "pending_action": None,
            "pending_action_hash": None,
            "final_status": "no_action",
        }

    # 如果用户没有显式选择，就默认 0。
    selected_index = state.get("selected_run_command_index", 0)
    if selected_index < 0 or selected_index >= len(effective_run_commands):
        return {
            "pending_action": None,
            "pending_action_hash": None,
            "final_status": "invalid_action",
            "error": f"selected_run_command_index out of range: {selected_index}",
        }

    selected_command = effective_run_commands[selected_index]
    cwd = selected_command.get("cwd") or state.get("repo_path") or "."

    try:
        action = build_run_action_from_command(
            command=selected_command["command"],
            cwd=cwd,
            source=selected_command.get("source", "inferred"),
            reason=selected_command.get("reason", "from experiment plan"),
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

### 为什么这一步特别关键

它保证了这条链仍然成立：

```text
用户改 command
  ↓
action_builder 重新规范化
  ↓
重新生成 pending_action_hash
  ↓
human_review 审批的是“修改后的具体动作”
```

这正是你前一章做 `Approval Hash` 的意义。

---

## 五、改 `graph.py`：在 `experiment_plan` 和 `action_builder` 之间插节点

这是图层的唯一核心修改。

### 建议修改后的完整代码

```python
from langgraph.graph import END, START, StateGraph

from app.memory.checkpoint import build_checkpointer
from app.nodes.action_builder_node import action_builder_node
from app.nodes.code_search_node import code_search_node
from app.nodes.command_selection_node import command_selection_node
from app.nodes.executor_node import executor_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.final_report_node import final_report_node
from app.nodes.human_review_node import human_review_node
from app.nodes.log_debug_node import log_debug_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.risk_check_node import risk_check_node
from app.state import ReproductionState


def route_after_action_builder(state: ReproductionState) -> str:
    if state.get("pending_action"):
        return "risk_check"
    if state.get("log_path"):
        return "log_debug"
    return "final_report"


def route_after_risk_check(state: ReproductionState) -> str:
    if state.get("requires_approval"):
        return "human_review"
    return "final_report"


def route_after_executor(state: ReproductionState) -> str:
    if state.get("final_status") == "failed" and state.get("log_path"):
        return "log_debug"
    return "final_report"


def build_graph():
    builder = StateGraph(ReproductionState)

    builder.add_node("paper_reader", paper_reader_node)
    builder.add_node("method_extractor", method_extractor_node)
    builder.add_node("repo_scan", repo_scan_node)
    builder.add_node("code_search", code_search_node)
    builder.add_node("mapping", mapping_node)
    builder.add_node("experiment_plan", experiment_plan_node)

    # 新增：
    # 在 action_builder 之前插入“用户命令确认层”。
    builder.add_node("command_selection", command_selection_node)

    builder.add_node("action_builder", action_builder_node)
    builder.add_node("final_report", final_report_node)
    builder.add_node("log_debug", log_debug_node)
    builder.add_node("risk_check", risk_check_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("executor", executor_node)

    builder.add_edge(START, "paper_reader")
    builder.add_edge("paper_reader", "method_extractor")
    builder.add_edge("method_extractor", "repo_scan")
    builder.add_edge("repo_scan", "code_search")
    builder.add_edge("code_search", "mapping")
    builder.add_edge("mapping", "experiment_plan")

    # 原来是 experiment_plan -> action_builder
    # 现在改成：
    builder.add_edge("experiment_plan", "command_selection")
    builder.add_edge("command_selection", "action_builder")

    builder.add_conditional_edges("action_builder", route_after_action_builder)
    builder.add_conditional_edges("risk_check", route_after_risk_check)
    builder.add_edge("human_review", "executor")
    builder.add_conditional_edges("executor", route_after_executor)
    builder.add_edge("log_debug", "final_report")
    builder.add_edge("final_report", END)

    return builder.compile(checkpointer=build_checkpointer())
```

---

## 六、改 `main.py`：新增 `resume-command-selection`

这一阶段最适合新增一个单独的恢复命令，而不是复用 `resume_review`。

### 为什么要单独做一个恢复入口

因为现在有两类中断：

1. `command_selection_node`
2. `human_review_node`

它们的 resume payload 完全不一样。

所以更好的做法是分开：

- `resume-command-selection`
- `resume-review`

### 我推荐的交互方式

支持两种恢复方式：

#### 方式 A：只选 index

```bash
python -m app.main resume-command-selection select-001 --selected-index 2
```

#### 方式 B：从 JSON 文件读取选择 + 批量编辑

```bash
python -m app.main resume-command-selection select-001 --input command_selection.json
```

### 为什么我更推荐 JSON 文件方式做批量编辑

因为命令字符串里经常包含：

- 空格
- 引号
- `--args`
- 路径

如果全塞到命令行参数里，bash 转义会很容易变复杂。  
JSON 文件方式更稳。

### 建议修改后的代码片段

下面这份代码只展示与本阶段新增功能相关的部分，不是要求你重写整个 `main.py`。

```python
import json
from pathlib import Path

import typer
from langgraph.types import Command
from rich import print

from app.graph import build_graph
from app.memory import checkpoint
from app.nodes.code_search_node import code_search_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.repo_scan_node import repo_scan_node

app = typer.Typer(help="Paper Reproduction Copilot")


@app.command()
def version():
    print("[green]paper-reproduction-copilot 0.1.0[/green]")


@app.command()
def init_outputs():
    Path("outputs").mkdir(exist_ok=True)
    print("[green]outputs/ is ready[/green]")


@app.command()
def read_paper(paper_path: str):
    state = {"paper_path": paper_path, "output_files": []}
    state.update(paper_reader_node(state))
    state.update(method_extractor_node(state))
    print("[green]paper reading finished[/green]")
    print(state["output_files"])


@app.command()
def scan_repo(repo_path: str):
    state = {"repo_path": repo_path, "output_files": []}
    state.update(repo_scan_node(state))
    print("[green]repo scan finished[/green]")
    print(state["output_files"])


@app.command()
def map_code(paper_path: str, repo_path: str):
    state = {
        "paper_path": paper_path,
        "repo_path": repo_path,
        "output_files": [],
    }
    state.update(paper_reader_node(state))
    state.update(method_extractor_node(state))
    state.update(repo_scan_node(state))
    state.update(code_search_node(state))
    state.update(mapping_node(state))
    print("[green]paper-code mapping finished[/green]")
    print(state["output_files"])


@app.command()
def plan_experiment(
    paper_path: str,
    repo_path: str,
    goal: str = "复现论文 main result",
):
    state = {
        "paper_path": paper_path,
        "repo_path": repo_path,
        "experiment_goal": goal,
        "output_files": [],
    }
    state.update(paper_reader_node(state))
    state.update(method_extractor_node(state))
    state.update(repo_scan_node(state))
    state.update(code_search_node(state))
    state.update(mapping_node(state))
    state.update(experiment_plan_node(state))
    print("[green]experiment plan finished[/green]")
    print(state["output_files"])


@app.command()
def run_graph(
    paper_path: str,
    repo_path: str,
    log_path: str | None = typer.Argument(None),
    thread_id: str = "demo_thread",
    goal: str = "复现论文 main result",
):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {
            "paper_path": paper_path,
            "repo_path": repo_path,
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


@app.command()
def show_state(thread_id: str = "demo_thread"):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    print(state)


@app.command()
def resume_review(
    thread_id: str,
    decision: str = "approved",
    feedback: str | None = None,
):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        Command(resume={"decision": decision, "feedback": feedback}),
        config=config,
    )
    print("[green]resume finished[/green]")
    print(result)


@app.command("resume-command-selection")
def resume_command_selection(
    thread_id: str,
    selected_index: int | None = typer.Option(None, "--selected-index"),
    input: str | None = typer.Option(None, "--input"),
):
    """
    恢复 command_selection_node 的 interrupt。

    支持两种方式：
    1. 只选一个 index：
       --selected-index 2

    2. 从 JSON 文件读取：
       --input command_selection.json
    """

    if input:
        payload = json.loads(Path(input).read_text(encoding="utf-8"))
    else:
        if selected_index is None:
            raise typer.BadParameter("either --selected-index or --input is required")
        payload = {
            "selected_index": selected_index,
            "edits": [],
        }

    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        Command(resume=payload),
        config=config,
    )
    print("[green]command selection resume finished[/green]")
    print(result)


@app.command()
def list_checkpoints(thread_id: str, limit: int = 5):
    checkpointer = checkpoint.build_checkpointer()
    config = {"configurable": {"thread_id": thread_id}}
    checkpoints = list(checkpointer.list(config, limit=limit))
    rows = []
    for item in checkpoints:
        rows.append(
            {
                "config": item.config,
                "metadata": item.metadata,
                "has_parent": item.parent_config is not None,
            }
        )
    print(rows)


@app.command()
def reset_thread(thread_id: str):
    checkpointer = checkpoint.build_checkpointer()
    checkpointer.delete_thread(thread_id)
    print(f"[yellow]deleted checkpoints for thread_id={thread_id}[/yellow]")


if __name__ == "__main__":
    app()
```

### 这里有两个重点

#### 1. `resume-command-selection` 和 `resume-review` 分离

这样职责更清晰，也更符合不同 interrupt 的恢复语义。

#### 2. 通过 JSON 文件支持“修改一个或多个 command”

这就是你问的第二个功能：

```text
用户可以指定修改一个或多个 run_command.command
```

---

## 七、建议的 JSON 输入格式

### 最小版：只选择 index

```json
{
  "selected_index": 2,
  "edits": []
}
```

### 完整版：选择 index + 修改一个或多个 command

```json
{
  "selected_index": 2,
  "edits": [
    {
      "index": 0,
      "command": "python train-ntu60.py --dataset_path /data/ntu60 --batch_size 8"
    },
    {
      "index": 1,
      "command": "python train-msr-small.py --dataset_path /data/msr --batch_size 8"
    },
    {
      "index": 2,
      "command": "python setup.py install"
    }
  ]
}
```

### 这里为什么允许修改未被选中的 command

因为你提到的需求是：

```text
用户可以指定修改一个或多个 run_command 中的 command
```

所以这个设计允许：

- 当前先执行 index 2
- 同时把 index 0 / 1 也提前修好

这样后面如果你进一步扩展到“多动作依次执行”，这个输入结构也还能继续复用。

---

## 八、建议新增测试：`tests/test_command_selection_node.py`

这一阶段非常适合做节点级单测，因为它的核心是：

- interrupt 交互
- 命令列表编辑
- 状态写回

### 建议新文件完整代码

```python
from unittest.mock import patch

from app.config import settings
from app.nodes.action_builder_node import action_builder_node
from app.nodes.command_selection_node import command_selection_node


def test_command_selection_selects_index_without_edits(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

    state = {
        "run_commands": [
            {
                "command": "python a.py",
                "cwd": "/repo",
                "source": "script",
                "risk_level": "medium",
                "reason": "run a",
            },
            {
                "command": "python b.py",
                "cwd": "/repo",
                "source": "script",
                "risk_level": "medium",
                "reason": "run b",
            },
        ],
        "output_files": [],
    }

    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value={"selected_index": 1, "edits": []},
    ), patch("app.nodes.command_selection_node.print"):
        result = command_selection_node(state)

    assert result["selected_run_command_index"] == 1
    assert result["edited_run_commands"][1]["command"] == "python b.py"
    assert result["command_selection_record"]["selected_index"] == 1


def test_command_selection_applies_multiple_command_edits(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

    state = {
        "run_commands": [
            {
                "command": "python train-ntu60.py --dataset_path <path>",
                "cwd": "/repo",
                "source": "script",
                "risk_level": "high",
                "reason": "train ntu",
            },
            {
                "command": "python setup.py install",
                "cwd": "/repo/modules",
                "source": "inferred",
                "risk_level": "medium",
                "reason": "build extension",
            },
        ],
        "output_files": [],
    }

    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value={
            "selected_index": 0,
            "edits": [
                {
                    "index": 0,
                    "command": "python train-ntu60.py --dataset_path /data/ntu60 --batch_size 8",
                },
                {
                    "index": 1,
                    "command": "python setup.py install",
                },
            ],
        },
    ), patch("app.nodes.command_selection_node.print"):
        result = command_selection_node(state)

    assert result["selected_run_command_index"] == 0
    assert (
        result["edited_run_commands"][0]["command"]
        == "python train-ntu60.py --dataset_path /data/ntu60 --batch_size 8"
    )
    assert len(result["command_selection_record"]["edits"]) == 2


def test_action_builder_uses_selected_index_from_edited_run_commands() -> None:
    state = {
        "repo_path": "/repo",
        "selected_run_command_index": 1,
        "edited_run_commands": [
            {
                "command": "python train.py --dataset_path /data/demo",
                "cwd": "/repo",
                "source": "script",
                "reason": "train model",
            },
            {
                "command": "python setup.py install",
                "cwd": "/repo/modules",
                "source": "inferred",
                "reason": "build extension",
            },
        ],
    }

    result = action_builder_node(state)

    assert result["pending_action"]["program"] == "python"
    assert result["pending_action"]["args"] == ["setup.py", "install"]
    assert result["pending_action"]["cwd"] == "/repo/modules"
    assert result["pending_action_hash"]
```

### 这份测试在验证什么

它验证的是本阶段最关键的三件事：

1. 用户可以选第几条命令先执行
2. 用户可以一次修改多条 command
3. `action_builder` 会使用“选择后的有效命令”，而不是继续死拿 `run_commands[0]`

---

## 九、如何手工测试

### 第一步：跑主图

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer/ \
  --thread-id command-select-001
```

### 预期现象

在终端里你应该看到类似：

```text
Available run_commands
[0] python train-ntu60.py --dataset_path <path_to_ntu60> --other_args ...
[1] python train-msr-small.py --dataset_path <path_to_msr> --other_args ...
[2] cd modules && python setup.py install
```

然后图会在 `command_selection_node` 的 `interrupt()` 处暂停。

注意：

```text
它不会像 input() 一样在终端等你继续输入
而是会把中断点保存到 checkpoint
```

### 第二步：只选择一个 index

比如你想先执行第 2 条：

```bash
python -m app.main resume-command-selection command-select-001 --selected-index 2
```

### 第三步：从 JSON 文件恢复，并顺便编辑命令

先准备一个文件，例如 `command_selection.json`：

```json
{
  "selected_index": 2,
  "edits": [
    {
      "index": 0,
      "command": "python train-ntu60.py --dataset_path /data/ntu60 --batch_size 8"
    },
    {
      "index": 1,
      "command": "python train-msr-small.py --dataset_path /data/msr --batch_size 8"
    },
    {
      "index": 2,
      "command": "python setup.py install"
    }
  ]
}
```

然后执行：

```bash
python -m app.main resume-command-selection command-select-001 --input command_selection.json
```

### 第四步：查看 state

```bash
python -m app.main show-state --thread-id command-select-001
```

你希望能看到：

- `selected_run_command_index`
- `edited_run_commands`
- `command_selection_record`

### 第五步：继续走审批链

如果用户选中的命令能成功被 `action_builder` 规范化，那么后面就会继续进入：

```text
risk_check
  -> human_review
  -> executor
```

这时你再用：

```bash
python -m app.main resume-review command-select-001 --decision approved
```

继续后面的链路即可。

---

## 十、这一阶段常见错误与排查方法

### 1. `selected_index out of range`

#### 原因

用户选了一个不存在的 index。

例如只有 3 条命令，却选了：

```json
"selected_index": 5
```

#### 解决

检查 `run_commands` 长度和恢复 payload。

---

### 2. 修改后的 command 仍然进 `invalid_action`

#### 原因

这通常不是 `command_selection_node` 的问题，而是后面的 `action_builder` 在重新规范化时拒绝了该命令。

比如：

- 命令里仍然有 `<path_to_xxx>`
- 命令里仍然有 `...`
- 命令里仍然带复杂 shell 语法

#### 解决

检查：

- `edited_run_commands`
- `error`
- `final_status`

这也是为什么我们要把修改后的命令再继续送回 `action_builder`，而不是直接执行。

---

### 3. 终端没有显示 run_commands

#### 原因

通常是：

- 图没有成功走到 `command_selection_node`
- 或者该节点没有真的执行

#### 排查

先看：

```bash
python -m app.main show-state --thread-id <thread_id>
```

确认图停在哪个节点。

---

## 十一、本阶段完成后的验收标准

我建议你把验收写得非常具体：

### 1. `run_graph` 时，终端能打印全部 `run_commands`

这说明 `command_selection_node` 已经接进图了。

### 2. 用户可以通过 `resume-command-selection` 选择先执行哪一条命令

至少支持：

```bash
--selected-index 2
```

### 3. 用户可以通过 JSON 文件修改一条或多条 `command`

例如同时修改第 0、1、2 条。

### 4. `action_builder` 不再默认只用 `run_commands[0]`

而是优先使用：

- `edited_run_commands`
- `selected_run_command_index`

### 5. 用户修改后的命令仍然继续走 Structured Action 与 Approval Hash

这是这阶段最重要的架构约束。

---

## 十二、这一阶段做完后，下一步最自然接什么

这个阶段做完后，最自然的下一步通常有两个方向：

### 方向一：Run Manifest 与 Artifact 分层

因为现在你已经有了：

- 用户原始命令
- 用户编辑后的命令
- 选择记录

这些都非常适合进入：

- `run_manifest.json`
- `runs/<run_id>/...`

也就是后面你要做的运行血缘和 artifact 分层。

### 方向二：Preflight

因为用户选择并修改完命令后，下一步非常适合自动插入：

- static preflight
- runtime probe
- smoke test

先做小风险检查，再进入真正执行。

---

## 十三、最后的整体理解

这一阶段的重点，不只是让用户“选一个 index”。

更重要的是把执行前链路升级成：

```text
planner 提供候选命令
  ↓
用户在 graph 内部选择和修正命令
  ↓
action_builder 重新规范化成 Structured Action
  ↓
risk_check 做风控
  ↓
human_review 审批具体动作
  ↓
executor 执行
```

这会让你的系统从：

```text
planner 给什么，就硬着头皮执行什么
```

升级成：

```text
planner 提供候选
用户可修正
系统再按安全链执行
```

这一步非常适合论文复现这种场景，因为真实复现任务里：

- 命令几乎总需要补参数
- 但补参数又不能绕过安全与审批链

而这一阶段正好解决了这个矛盾。
