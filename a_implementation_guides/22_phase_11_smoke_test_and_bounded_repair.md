# 22. 闭环后第七阶段：Smoke Test 与 Bounded Repair

> 实施建议：这一章内容较多，请先只完成 Smoke Test，再完成 Repair Proposal，最后才开启一次 Bounded Repair 重试。不要一次性把三个能力全部接入主图。

> 前置条件：请先完成 Phase 21 的 Execution Profile 与 Runner。本文中的 `run_action_safe(smoke_action)` 应通过动作里的 `execution_profile_id` 分发到目标 Runner，不能退回 Agent 环境直接执行。

## 这一阶段的目标

到上一阶段为止，你已经补上了：

```text
Durable Checkpoint
Structured Action
Approval Hash
Command Selection
Editable Run Commands
Run Manifest
Artifact Layering
Preflight Check
Execution Profile
CondaRunner / LocalRunner
```

这说明你的系统现在已经具备了一条相当完整的“执行前闭环”：

```text
experiment_plan
  -> command_selection
  -> action_builder
  -> risk_check
  -> human_review
  -> preflight_check
  -> executor
  -> log_debug
  -> final_report
  -> run_manifest
```

但是到了这里，还会有一个很现实的问题：

```text
preflight 只能告诉你“现在有没有资格执行”
不能告诉你“这条命令跑起来会不会立刻炸”
```

举几个很常见的例子：

- `--batch_size 64` 在你的 GPU 上一跑就 OOM
- `--num_workers 16` 在当前机器上会卡死或报资源错误
- `--epochs 300` 虽然合法，但根本不适合第一次尝试
- 命令本身没问题，但真正训练时会遇到 shape mismatch / CUDA OOM / runtime error

所以在 `preflight` 之后、`full executor` 之前，最值得补的一层就是：

```text
先跑一个低成本 smoke test
```

而当 smoke test 或 full run 失败后，下一步最有 Agent 味道的事情，就是不要只停在 debug report，而是进一步给出：

```text
一个“有界”的 repair 方案
```

注意这个“有界”非常关键。

这一阶段我们不直接做：

- 自动改源码
- 自动改 config 文件
- 自动安装依赖
- 自动下载数据

而是只做：

```text
命令级 repair
```

也就是：

- 改参数
- 改路径
- 降低 batch size
- 降低 num_workers
- 缩短 epochs / steps
- 再走一轮 risk_check / human_review / preflight / smoke / executor

---

## 这一阶段做完后，链路会升级成什么

当前你大概是：

```text
preflight_check
  -> executor
  -> log_debug
  -> final_report
```

这一阶段做完后，建议升级成：

```text
preflight_check
  -> smoke_test
      -> passed / skipped -> executor
      -> failed -> log_debug

executor
  -> failed -> log_debug
  -> succeeded -> final_report

log_debug
  -> repair_planner
      -> bounded command repair -> repair_action_builder
      -> risk_check
      -> human_review
      -> preflight_check
      -> smoke_test
      -> executor
```

更完整地写出来是：

```text
action_builder
  -> risk_check
  -> human_review（如需）
  -> preflight_check
  -> smoke_test
      -> 通过 / 跳过 -> full executor
      -> 失败 -> log_debug
  -> repair_planner
      -> 生成 bounded repair proposal
  -> repair_action_builder
      -> 只允许 command-level repair
  -> risk_check
  -> human_review
  -> preflight_check
  -> smoke_test
  -> executor
```

这一步的意义非常大，因为从这里开始，你的项目就不再只是：

```text
会执行，会报错，会分析
```

而是开始变成：

```text
会先低成本试跑，失败后还能在边界内自我修正
```

---

## 先说清楚：这一阶段只做“有界修复”，不做“自动改代码”

这里一定要克制。

### 为什么不能一上来就自动改仓库源码

因为一旦系统可以直接：

- 改 `.py`
- 改 `.yaml`
- 改训练配置
- 改数据处理逻辑

那风险会陡然上升：

- 很难审计
- 很容易引入新的 bug
- 很容易把“复现任务失败”变成“你的 agent 把 repo 改坏了”

### 这一章的边界

所以这一章严格限定 repair 范围：

```text
只允许 command-level bounded repair
```

也就是：

- 修改运行命令里的参数
- 修改运行命令里的路径
- 缩小运行规模

不允许：

- `pip install`
- `conda install`
- `git` 操作
- 自动写 repo 文件
- 自动 patch 源码

如果 debug 结论指向“需要改源码 / config / 环境”，这一阶段只生成：

```text
manual_only proposal
```

而不是自动执行。

---

## 本阶段建议修改 / 新增的文件

```text
app/config.py
app/schemas.py
app/state.py
app/tools/smoke_test_tools.py
app/tools/repair_tools.py
app/prompts/repair_prompt.py
app/nodes/smoke_test_node.py
app/nodes/repair_planner_node.py
app/nodes/repair_action_builder_node.py
app/nodes/final_report_node.py
app/tools/artifact_tools.py
app/graph.py
app/main.py
tests/test_smoke_test_node.py
tests/test_repair_action_builder_node.py
tests/test_smoke_repair_flow.py
```

如果你想把这一步调试得更轻松，也很推荐：

- `app/main.py`
  - 增加 `run_smoke`
  - 增加 `plan_repair`

这样你不用每次都完整跑整条 graph。

---

## 这一阶段的核心设计

### 设计 1：Smoke Test 先于 Full Executor

smoke test 的目标不是“得到最终实验结果”，而是：

```text
用更低成本确认：
这条命令是不是至少能正常跑起来
```

所以它应该尽量做到：

- `batch_size -> 1`
- `epochs -> 1`
- `num_workers -> 0`
- `max_steps -> 1`

但要注意：

```text
只改“已存在”的常见参数
不要盲目给所有命令追加陌生 flag
```

否则 smoke test 本身就会引入新的参数错误。

### 设计 2：Repair 先做 Proposal，再做有界重试

repair loop 也不要一上来就做“自动 patch 文件”。

这一阶段建议分两层：

1. `repair_planner_node`
   - 先输出结构化 repair proposal
2. `repair_action_builder_node`
   - 只消费 `kind=edit_command` 的 bounded proposal
   - 重新生成 `pending_action`
   - 再走既有的安全链

这样整个系统会非常清晰：

- LLM 负责提建议
- 工具负责校验边界
- graph 负责控制是否允许 rerun

---

## 一、先补配置：增加 smoke / repair 的全局控制项

当前 [app/config.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/config.py:1) 已经有：

- `output_dir`
- `runs_dir`
- `checkpoint_db_path`
- `max_steps`

这一阶段推荐再加两个配置：

- `smoke_test_timeout_seconds`
- `max_repair_attempts`

### 为什么要有这两个配置

因为 smoke 和 repair 都属于“有边界的尝试”。

如果没有边界，就很容易出现：

- smoke test 反而跑很久
- repair loop 反复重试停不下来

### 建议代码

```python
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL")
    openai_model: str = os.getenv("OPENAI_MODEL", "mimo-v2.5-pro")

    embedding_api_key: Optional[str] = os.getenv("EMBEDDING_API_KEY")
    embedding_base_url: Optional[str] = os.getenv("EMBEDDING_BASE_URL")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "qwen-text-embedding-v4")

    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
    runs_dir: Path = Path(os.getenv("RUNS_DIR", "runs"))
    checkpoint_db_path: Path = Path(
        os.getenv("CHECKPOINT_DB_PATH", "checkpoints/langgraph.sqlite")
    )

    max_steps: int = int(os.getenv("MAX_STEPS", "20"))

    # Smoke test 要明显比 full executor 更保守。
    smoke_test_timeout_seconds: int = int(
        os.getenv("SMOKE_TEST_TIMEOUT_SECONDS", "60")
    )

    # Bounded repair 必须有重试上限。
    max_repair_attempts: int = int(
        os.getenv("MAX_REPAIR_ATTEMPTS", "1")
    )


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.runs_dir.mkdir(parents=True, exist_ok=True)
settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
```

### 推荐默认值

这一步我建议默认先保守一点：

- `SMOKE_TEST_TIMEOUT_SECONDS=60`
- `MAX_REPAIR_ATTEMPTS=1`

先把单轮 bounded repair 打通，再考虑多轮。

---

## 二、扩展 Schema：定义 Smoke Test 和 Repair Proposal

当前 [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1) 里已经有：

- `ExecutableAction`
- `ApprovalRecord`
- `DebugReport`
- `PreflightReport`

现在要补上：

- `SmokeTestReport`
- `RepairStep`
- `RepairProposal`

### 建议代码

下面给出建议加入到 [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1) 的新增部分：

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


class CommandEdit(BaseModel):
    index: int
    command: str


class CommandSelectionResponse(BaseModel):
    selected_index: int
    edits: list[CommandEdit] = Field(default_factory=list)


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


class PreflightItem(BaseModel):
    name: str
    category: Literal["static", "runtime", "smoke"] = "static"
    status: Literal["passed", "warning", "failed", "unknown"]
    evidence: str
    recommendation: str | None = None


class PreflightReport(BaseModel):
    action_id: str | None = None
    action_hash: str | None = None
    ready_to_execute: bool = False
    summary: str
    items: list[PreflightItem] = Field(default_factory=list)
    blocking_items: list[str] = Field(default_factory=list)
    generated_at: str


class SmokeTestReport(BaseModel):
    action_id: str | None = None
    action_hash: str | None = None

    # smoke test 最终状态：
    # - passed: 低成本试跑成功
    # - failed: 低成本试跑失败
    # - skipped: 当前动作不适合安全缩减，直接跳过 smoke
    # - blocked: 连 smoke 都没法构造
    status: Literal["passed", "failed", "skipped", "blocked"]

    summary: str
    applied_overrides: list[str] = Field(default_factory=list)
    command_preview: str | None = None
    log_path: str | None = None
    result: dict = Field(default_factory=dict)
    generated_at: str


class RepairStep(BaseModel):
    step_type: Literal[
        "edit_command",
        "manual_check",
        "rerun_smoke",
        "rerun_full",
    ]
    target: str
    change: str
    reason: str
    risk: Literal["low", "medium", "high"] = "low"


class RepairProposal(BaseModel):
    proposal_id: str | None = None
    source_error_type: str

    # edit_command: 当前阶段允许自动进入 bounded rerun
    # manual_only: 只给建议，不自动继续
    # no_repair: 暂无可靠修复路径
    kind: Literal["edit_command", "manual_only", "no_repair"] = "no_repair"

    summary: str
    root_cause: str

    # 只有 kind=edit_command 时才应提供。
    repaired_command: str | None = None
    changed_arguments: list[str] = Field(default_factory=list)

    steps: list[RepairStep] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    # 这一阶段所有 repair proposal 都应该保持 bounded=True。
    bounded: bool = True
```

### 为什么这里把 `RepairProposal.kind` 限定成 3 种

因为这能逼着 repair planner 明确表达：

- `edit_command`
  - 这轮可以在“命令层”自动重试
- `manual_only`
  - 有建议，但不能自动执行
- `no_repair`
  - 当前证据不足，别乱试

这是“有界自治”里非常关键的一步。

---

## 三、扩展 State：加入 smoke / repair 的运行状态

当前 [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1) 已经有：

- `preflight_report`
- `execution_result`
- `debug_report`
- `run_manifest_path`

现在要把 smoke 和 repair 也纳入状态。

### 推荐新增字段

- `active_execution_mode`
- `smoke_test_report`
- `smoke_test_status`
- `smoke_test_passed`
- `smoke_test_log_path`
- `repair_proposal`
- `repair_attempt_count`
- `repair_history`

### 建议代码

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

    edited_run_commands: list[dict[str, Any]]
    selected_run_command_index: Optional[int]
    command_selection_record: Optional[dict[str, Any]]

    pending_action: Optional[dict[str, Any]]
    pending_action_hash: Optional[str]
    requires_approval: bool
    user_approval: Optional[str]
    human_feedback: Optional[str]
    approval_record: Optional[dict[str, Any]]

    preflight_report: Optional[dict[str, Any]]
    preflight_passed: bool
    preflight_report_path: Optional[str]

    # Phase 22：记录当前是在 smoke 还是 full executor 失败。
    active_execution_mode: Optional[str]

    # Phase 22：smoke test 状态。
    smoke_test_report: Optional[dict[str, Any]]
    smoke_test_status: Optional[str]
    smoke_test_passed: bool
    smoke_test_log_path: Optional[str]

    # Phase 22：bounded repair 状态。
    repair_proposal: Optional[dict[str, Any]]
    repair_attempt_count: int
    repair_history: list[dict[str, Any]]

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

    run_id: Optional[str]
    run_dir: Optional[str]
    run_started_at: Optional[str]

    artifact_records: list[dict[str, Any]]
    artifact_index_path: Optional[str]
    run_manifest_path: Optional[str]
```

### 为什么要有 `active_execution_mode`

因为后面 `log_debug -> repair_planner` 时，repair planner 最好知道：

```text
这次失败发生在 smoke test
还是发生在 full executor
```

这两者语义不同：

- smoke 失败
  - 更像“最小规模都跑不起来”
- full run 失败
  - 更像“基础能跑，但规模或资源不行”

---

## 四、工具层一：新增 `smoke_test_tools.py`

这一层负责把 full action 收缩成一个“尽量低成本的 smoke action”。

建议新增：

```text
app/tools/smoke_test_tools.py
```

### 这一层的设计原则

最关键的原则有两个：

1. 尽量只改“已存在”的参数
2. 不要盲目发明新的 flag

举例：

如果原命令里有：

```text
--batch_size 16 --epochs 200 --num_workers 8
```

那你可以安全地把它改成：

```text
--batch_size 1 --epochs 1 --num_workers 0
```

但如果原命令里根本没有 `--batch_size`，你就不要自己擅自追加一个不一定被脚本支持的 `--batch_size 1`。

### 建议代码

```python
from datetime import datetime, timezone
import shlex
from typing import Any

from app.config import settings
from app.schemas import SmokeTestReport


# 这些是“常见而相对安全”的收缩参数。
# 原则：
# - 只覆盖命令里已存在的 flag
# - 不主动给命令加未知 flag
SMOKE_OVERRIDE_VALUES = {
    "--batch_size": "1",
    "--batch-size": "1",
    "--epochs": "1",
    "--epoch": "1",
    "--max_epochs": "1",
    "--max-epochs": "1",
    "--num_workers": "0",
    "--num-workers": "0",
    "--workers": "0",
    "--max_steps": "1",
    "--max-steps": "1",
    "--train_steps": "1",
    "--train-steps": "1",
    "--limit_train_batches": "1",
    "--limit-val-batches": "1",
    "--limit_val_batches": "1",
}


SUPPORTED_SMOKE_PROGRAMS = {
    "python",
    "torchrun",
    "accelerate",
    "bash",
}


def _set_flag_value(args: list[str], flag: str, new_value: str) -> tuple[list[str], bool]:
    """
    支持两类常见 flag 形式：
    1. --batch_size 16
    2. --batch_size=16
    """
    updated = list(args)
    changed = False

    index = 0
    while index < len(updated):
        token = updated[index]

        if token == flag and index + 1 < len(updated):
            if updated[index + 1] != new_value:
                updated[index + 1] = new_value
                changed = True
            index += 2
            continue

        prefix = f"{flag}="
        if token.startswith(prefix):
            if token != f"{flag}={new_value}":
                updated[index] = f"{flag}={new_value}"
                changed = True

        index += 1

    return updated, changed


def _render_action_preview(action: dict[str, Any]) -> str:
    program = action.get("program", "")
    args = action.get("args", [])
    return " ".join([shlex.quote(program), *[shlex.quote(arg) for arg in args]]).strip()


def derive_smoke_test_action(action: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str]:
    """
    从 full action 派生 smoke action。

    返回：
    - smoke_action：派生出的结构化动作；如果无法安全派生则返回 None
    - overrides：本次实际做了哪些缩减
    - summary：给 node / report 用的人类可读摘要
    """
    program = action.get("program", "")
    args = list(action.get("args", []))

    if program not in SUPPORTED_SMOKE_PROGRAMS:
        return None, [], f"program not supported for smoke reduction: {program}"

    updated_args = list(args)
    overrides: list[str] = []

    for flag, value in SMOKE_OVERRIDE_VALUES.items():
        updated_args, changed = _set_flag_value(updated_args, flag, value)
        if changed:
            overrides.append(f"{flag} -> {value}")

    if not overrides:
        return None, [], "no known safe reductions found in command arguments"

    smoke_action = {
        **action,
        # 给 smoke action 一个新的 action_id，避免和 full action 混淆。
        "action_id": f"{action.get('action_id', 'action')}_smoke",
        "args": updated_args,
        "reason": f"smoke test derived from: {action.get('reason', 'unknown reason')}",
        # smoke timeout 必须明显更短。
        "timeout_seconds": min(
            int(action.get("timeout_seconds", 300)),
            settings.smoke_test_timeout_seconds,
        ),
    }

    return smoke_action, overrides, "derived smoke action with bounded argument reductions"


def build_smoke_test_report(
    *,
    action: dict[str, Any],
    action_hash: str | None,
    status: str,
    summary: str,
    applied_overrides: list[str],
    result: dict[str, Any] | None = None,
    log_path: str | None = None,
) -> SmokeTestReport:
    return SmokeTestReport(
        action_id=action.get("action_id"),
        action_hash=action_hash,
        status=status,  # type: ignore[arg-type]
        summary=summary,
        applied_overrides=applied_overrides,
        command_preview=_render_action_preview(action),
        log_path=log_path,
        result=result or {},
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def render_smoke_test_report_md(report: SmokeTestReport) -> str:
    lines = ["# Smoke Test Report", ""]

    lines += [
        "## Summary",
        "",
        f"- Action ID: `{report.action_id or 'N/A'}`",
        f"- Action Hash: `{report.action_hash or 'N/A'}`",
        f"- Status: `{report.status}`",
        f"- Summary: {report.summary}",
        f"- Command Preview: `{report.command_preview or 'N/A'}`",
        f"- Log Path: `{report.log_path or 'N/A'}`",
        "",
    ]

    lines += ["## Applied Overrides", ""]
    if not report.applied_overrides:
        lines.append("- None")
    else:
        for item in report.applied_overrides:
            lines.append(f"- {item}")
    lines.append("")

    if report.result:
        lines += [
            "## Result",
            "",
            f"- OK: `{report.result.get('ok')}`",
            f"- Return Code: `{report.result.get('returncode')}`",
            "",
        ]

    return "\n".join(lines)
```

### 这层工具的关键点

这层的本质不是“构造一个一定能通过的命令”，而是：

```text
在不发明新参数的前提下
尽量把一次 full run 收缩成一次低成本尝试
```

如果收缩不了，就宁可：

```text
skip smoke
```

也不要为了“非要跑一次 smoke”而把命令改坏。

---

## 五、工具层二：新增 `repair_tools.py`

repair 这里也建议单独封一层工具。

建议新增：

```text
app/tools/repair_tools.py
```

### 为什么要单独有 repair 工具层

因为 repair planner 给出的 proposal 不能直接信任。

你必须先有一层 deterministic 校验，确认它是否真的：

- 在边界内
- 还是 command-level
- 没有偷偷升级成 install / rm / git / 多段 shell

### 建议代码

```python
from copy import deepcopy
import shlex
from typing import Any

from app.tools.action_tools import build_run_action_from_command, compute_action_hash


UNSUPPORTED_REPAIR_SHELL_MARKERS = [
    "&&",
    "||",
    ";",
    "|",
    ">",
    "<",
    "$(",
    "`",
]


BLOCKED_REPAIR_PROGRAMS = {
    "pip",
    "conda",
    "sudo",
    "rm",
    "git",
    "apt",
    "apt-get",
}


def validate_bounded_repair_command(command: str) -> tuple[bool, str]:
    """
    校验 repair proposal 给出的新命令是否仍然在本阶段允许的边界内。
    """
    stripped = command.strip()
    if not stripped:
        return False, "empty repaired_command"

    if any(marker in stripped for marker in UNSUPPORTED_REPAIR_SHELL_MARKERS):
        return False, "repaired_command contains unsupported shell syntax"

    try:
        tokens = shlex.split(stripped)
    except ValueError as exc:
        return False, f"invalid repaired_command quoting: {exc}"

    if not tokens:
        return False, "empty repaired_command after shlex parsing"

    if tokens[0] in BLOCKED_REPAIR_PROGRAMS:
        return False, f"repaired_command uses blocked program: {tokens[0]}"

    return True, "ok"


def render_repair_proposal_md(proposal: dict[str, Any]) -> str:
    lines = ["# Repair Proposal", ""]

    lines += [
        "## Summary",
        "",
        f"- Proposal ID: `{proposal.get('proposal_id', 'N/A')}`",
        f"- Error Type: `{proposal.get('source_error_type', 'unknown')}`",
        f"- Kind: `{proposal.get('kind', 'unknown')}`",
        f"- Bounded: `{proposal.get('bounded', False)}`",
        f"- Summary: {proposal.get('summary', 'N/A')}",
        f"- Root Cause: {proposal.get('root_cause', 'N/A')}",
        "",
    ]

    repaired_command = proposal.get("repaired_command")
    lines += ["## Repaired Command", ""]
    if repaired_command:
        lines.append(f"- `{repaired_command}`")
    else:
        lines.append("- None")
    lines.append("")

    sections = [
        ("Changed Arguments", proposal.get("changed_arguments", [])),
        ("Verification Steps", proposal.get("verification_steps", [])),
        ("Rollback Steps", proposal.get("rollback_steps", [])),
        ("Risks", proposal.get("risks", [])),
    ]
    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("- None")
        else:
            for item in items:
                lines.append(f"- {item}")
        lines.append("")

    steps = proposal.get("steps", [])
    lines += ["## Steps", ""]
    if not steps:
        lines.append("- None")
        lines.append("")
    else:
        for step in steps:
            lines.append(
                f"- `{step.get('step_type', 'unknown')}` on `{step.get('target', '')}`: {step.get('change', '')}"
            )
            lines.append(f"  reason: {step.get('reason', '')}")
            lines.append(f"  risk: `{step.get('risk', 'unknown')}`")
        lines.append("")

    return "\n".join(lines)


def apply_command_repair_to_state(state: dict[str, Any], repaired_command: str) -> dict[str, Any]:
    """
    把 bounded repair 作用到当前“被选中的命令”上，并重新生成 pending_action。
    """
    effective_commands = deepcopy(
        state.get("edited_run_commands") or state.get("run_commands") or []
    )
    selected_index = state.get("selected_run_command_index", 0)

    if not effective_commands:
        raise ValueError("cannot apply repair: no effective run commands found")

    if selected_index is None or selected_index < 0 or selected_index >= len(effective_commands):
        raise ValueError(f"selected_run_command_index out of range: {selected_index}")

    target_command = effective_commands[selected_index]
    target_command["command"] = repaired_command

    cwd = target_command.get("cwd") or state.get("repo_path") or "."
    source = target_command.get("source", "inferred")
    reason = target_command.get("reason", "repair proposal generated command")

    new_action = build_run_action_from_command(
        command=repaired_command,
        cwd=cwd,
        source=source,
        reason=reason,
        timeout_seconds=300,
    )

    return {
        "edited_run_commands": effective_commands,
        "pending_action": new_action,
        "pending_action_hash": compute_action_hash(new_action),
    }
```

### 为什么 repair 这里仍然要二次校验

因为 LLM 生成 proposal 时，哪怕 prompt 写得再严，也不代表它永远不会输出：

- `pip install ...`
- `conda install ...`
- `git pull`
- `cd ... && ...`

所以这一层 deterministic check 非常必要。

---

## 六、Prompt 层：新增 `repair_prompt.py`

repair planner 的质量很大程度上取决于 prompt 边界是否清晰。

建议新增：

```text
app/prompts/repair_prompt.py
```

### 这一层最关键的约束

repair prompt 一定要明确告诉模型：

```text
你不是在写“最理想的修复建议”
而是在写“当前阶段允许执行的 bounded proposal”
```

### 建议代码

```python
REPAIR_PROMPT = """
你是一个深度学习实验 repair planner。

请根据当前执行动作、preflight 报告、smoke test 报告和 debug 报告，
输出一个“有界修复方案（bounded repair proposal）”。

严格要求：
1. 只允许三种 `kind`：
   - `edit_command`
   - `manual_only`
   - `no_repair`
2. `edit_command` 只允许修改运行命令本身，不允许修改仓库源码、配置文件、依赖环境。
3. 不要建议：
   - `pip install`
   - `conda install`
   - `sudo`
   - `git`
   - 删除文件
   - 自动 patch 仓库代码
4. 如果修复需要改源码、改配置或改环境，`kind` 必须是 `manual_only`。
5. 如果给出 `edit_command`，必须提供完整的 `repaired_command`，且尽量只做最小修改。
6. `verification_steps` 必须包含：
   - 先 rerun smoke test
   - smoke 通过后再 rerun full executor
7. 如果证据不足，返回 `no_repair`，不要编造命令。

当前执行模式：
{execution_mode}

当前动作：
{pending_action}

Preflight Report：
{preflight_report}

Smoke Test Report：
{smoke_test_report}

Debug Report：
{debug_report}
"""
```

### 为什么 `manual_only` 很重要

因为很多真实问题的正确修法其实是：

- 改 config
- 改源码
- 安装依赖
- 换环境

但这些都已经超出了这一阶段的边界。

所以这时最好的做法不是“硬编一个命令修复”，而是明确告诉系统：

```text
这轮只能给人工建议，不能自动继续
```

---

## 七、节点层一：新增 `smoke_test_node.py`

这个节点负责：

1. 从 `pending_action` 派生 `smoke_action`
2. 运行低成本 smoke test
3. 写出 `smoke_test_report.json / .md`
4. 如果失败，把日志交给后面的 `log_debug`

建议新增：

```text
app/nodes/smoke_test_node.py
```

### 建议代码

```python
from app.config import settings
from app.tools.action_tools import compute_action_hash
from app.tools.exec_tools import run_action_safe
from app.tools.smoke_test_tools import (
    build_smoke_test_report,
    derive_smoke_test_action,
    render_smoke_test_report_md,
)


def smoke_test_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {
            "smoke_test_report": None,
            "smoke_test_status": "blocked",
            "smoke_test_passed": False,
            "final_status": "blocked",
            "error": "missing pending_action before smoke_test",
        }

    smoke_action, overrides, summary = derive_smoke_test_action(pending_action)

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = settings.output_dir / "smoke_test_report.json"
    report_md_path = settings.output_dir / "smoke_test_report.md"

    if smoke_action is None:
        # 当前命令不适合被安全缩减，这不算失败，只是跳过。
        report = build_smoke_test_report(
            action=pending_action,
            action_hash=state.get("pending_action_hash"),
            status="skipped",
            summary=summary,
            applied_overrides=[],
            result={},
            log_path=None,
        )

        report_json_path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        report_md_path.write_text(
            render_smoke_test_report_md(report),
            encoding="utf-8",
        )

        return {
            "smoke_test_report": report.model_dump(),
            "smoke_test_status": "skipped",
            # skipped 在图路由上等价于“允许继续 full executor”
            "smoke_test_passed": True,
            "output_files": [
                *state.get("output_files", []),
                str(report_json_path),
                str(report_md_path),
            ],
        }

    smoke_action_hash = compute_action_hash(smoke_action)
    result = run_action_safe(smoke_action)

    smoke_log_path = settings.output_dir / "smoke_test.log"
    smoke_log_path.write_text(result["combined_output"], encoding="utf-8")

    status = "passed" if result["ok"] else "failed"
    report = build_smoke_test_report(
        action=smoke_action,
        action_hash=smoke_action_hash,
        status=status,
        summary=summary,
        applied_overrides=overrides,
        result=result,
        log_path=str(smoke_log_path),
    )

    report_json_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_md_path.write_text(
        render_smoke_test_report_md(report),
        encoding="utf-8",
    )

    payload = {
        "active_execution_mode": "smoke",
        "smoke_test_report": report.model_dump(),
        "smoke_test_status": status,
        "smoke_test_passed": status == "passed",
        "smoke_test_log_path": str(smoke_log_path),
        "output_files": [
            *state.get("output_files", []),
            str(smoke_log_path),
            str(report_json_path),
            str(report_md_path),
        ],
    }

    if status == "failed":
        payload["log_path"] = str(smoke_log_path)
        payload["final_status"] = "failed"
        payload["last_action_result"] = {
            "status": "smoke_failed",
            "pending_action": smoke_action,
            "returncode": result["returncode"],
        }

    return payload
```

### 这里为什么 `skipped` 不算失败

因为有些命令确实不适合安全缩减。

例如：

- 参数里根本没有你能安全降低的规模项
- 命令本身更像一个脚本包装器

这时更好的语义是：

```text
smoke 不适用
但 full executor 仍然可以继续
```

而不是强行把它判成失败。

---

## 八、节点层二：新增 `repair_planner_node.py`

这个节点负责在：

```text
smoke / full executor 失败
-> log_debug 已经生成 debug_report
```

之后，进一步输出一个结构化 repair proposal。

建议新增：

```text
app/nodes/repair_planner_node.py
```

### 建议代码

```python
import json
from uuid import uuid4

from app.config import settings
from app.model import get_chat_model
from app.prompts.repair_prompt import REPAIR_PROMPT
from app.schemas import RepairProposal
from app.tools.repair_tools import render_repair_proposal_md


def repair_planner_node(state: dict) -> dict:
    debug_report = state.get("debug_report")
    if not debug_report:
        return {
            "repair_proposal": {
                "proposal_id": None,
                "source_error_type": "unknown",
                "kind": "no_repair",
                "summary": "missing debug_report, cannot plan repair",
                "root_cause": "debug_report not available",
                "repaired_command": None,
                "changed_arguments": [],
                "steps": [],
                "verification_steps": [],
                "rollback_steps": [],
                "risks": [],
                "bounded": True,
            }
        }

    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(RepairProposal)

    proposal: RepairProposal = structured_llm.invoke(
        REPAIR_PROMPT.format(
            execution_mode=state.get("active_execution_mode", "unknown"),
            pending_action=json.dumps(
                state.get("pending_action", {}),
                ensure_ascii=False,
                indent=2,
            ),
            preflight_report=json.dumps(
                state.get("preflight_report", {}),
                ensure_ascii=False,
                indent=2,
            ),
            smoke_test_report=json.dumps(
                state.get("smoke_test_report", {}),
                ensure_ascii=False,
                indent=2,
            ),
            debug_report=json.dumps(
                debug_report,
                ensure_ascii=False,
                indent=2,
            ),
        )
    )

    if not proposal.proposal_id:
        proposal = proposal.model_copy(
            update={"proposal_id": f"repair_{uuid4().hex[:12]}"}
        )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "repair_proposal.json"
    md_path = settings.output_dir / "repair_proposal.md"

    json_path.write_text(
        proposal.model_dump_json(indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        render_repair_proposal_md(proposal.model_dump()),
        encoding="utf-8",
    )

    return {
        "repair_proposal": proposal.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(json_path),
            str(md_path),
        ],
    }
```

### 为什么 repair planner 要读 `preflight_report` 和 `smoke_test_report`

因为 repair proposal 不能只看 traceback。

它最好能综合判断：

- preflight 有没有暴露路径 / 环境问题
- smoke 是不是已经把 batch size 降过一次
- 失败发生在 smoke 还是 full run

这样 proposal 才更像“系统性修复建议”，而不是只看一段报错瞎猜。

---

## 九、节点层三：新增 `repair_action_builder_node.py`

这个节点是 bounded repair 的真正执行边界。

它只负责一件事：

```text
把 repair proposal 中允许自动继续的 command-level repair
变成新的 pending_action
```

也就是说：

- `kind=edit_command`
  - 可以继续
- `kind=manual_only`
  - 不继续
- `kind=no_repair`
  - 不继续

建议新增：

```text
app/nodes/repair_action_builder_node.py
```

### 建议代码

```python
from app.config import settings
from app.tools.repair_tools import (
    apply_command_repair_to_state,
    validate_bounded_repair_command,
)


def repair_action_builder_node(state: dict) -> dict:
    proposal = state.get("repair_proposal")
    if not proposal:
        return {
            "final_status": "no_repair_proposal",
            "error": "repair_proposal is missing",
        }

    attempts = int(state.get("repair_attempt_count", 0))
    if attempts >= settings.max_repair_attempts:
        return {
            "final_status": "repair_limit_reached",
            "error": f"max repair attempts reached: {settings.max_repair_attempts}",
        }

    kind = proposal.get("kind")
    repaired_command = (proposal.get("repaired_command") or "").strip()

    if kind != "edit_command":
        return {
            "final_status": "repair_proposal_only",
            "last_action_result": {
                "status": "repair_proposal_only",
                "proposal_kind": kind,
            },
        }

    ok, reason = validate_bounded_repair_command(repaired_command)
    if not ok:
        return {
            "final_status": "repair_out_of_bounds",
            "error": reason,
            "last_action_result": {
                "status": "repair_out_of_bounds",
                "proposal_kind": kind,
                "repaired_command": repaired_command,
            },
        }

    updated_action = apply_command_repair_to_state(state, repaired_command)

    history_entry = {
        "attempt": attempts + 1,
        "proposal_id": proposal.get("proposal_id"),
        "kind": kind,
        "repaired_command": repaired_command,
        "summary": proposal.get("summary"),
    }

    return {
        **updated_action,
        "repair_attempt_count": attempts + 1,
        "repair_history": [
            *state.get("repair_history", []),
            history_entry,
        ],

        # 新动作要重新走完整安全链。
        "user_approval": None,
        "human_feedback": None,
        "approval_record": None,

        # 旧 preflight / smoke / debug 结果已经过期，必须清空。
        "preflight_report": None,
        "preflight_passed": False,
        "preflight_report_path": None,
        "smoke_test_report": None,
        "smoke_test_status": None,
        "smoke_test_passed": False,
        "smoke_test_log_path": None,
        "debug_report": None,
        "log_path": None,
        "execution_result": {},
        "execution_log_path": None,
        "active_execution_mode": None,
        "final_status": None,
        "error": None,
    }
```

### 为什么 repair 后要把旧状态清空

因为 repair 之后你面对的已经不是同一个动作了。

如果不清空：

- 旧的 `approval_record`
- 旧的 `preflight_report`
- 旧的 `smoke_test_report`
- 旧的 `debug_report`

就会污染新一轮动作。

这一步和你前面做 `approval_hash` 的逻辑是一脉相承的：

```text
动作变了
旧结论不能直接复用
```

---

## 十、Graph 接入：把 smoke / repair 正式编进闭环

现在要把：

- `smoke_test_node`
- `repair_planner_node`
- `repair_action_builder_node`

接进 [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1)。

### 推荐的核心流程

图结构建议变成：

```text
preflight_check
  -> smoke_test
      -> passed / skipped -> executor
      -> failed -> log_debug

log_debug
  -> repair_planner
      -> edit_command -> repair_action_builder
      -> otherwise -> final_report

repair_action_builder
  -> risk_check
```

### 建议代码

```python
from langgraph.graph import END, START, StateGraph

from app.config import settings
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
from app.nodes.preflight_check_node import preflight_check_node
from app.nodes.repair_action_builder_node import repair_action_builder_node
from app.nodes.repair_planner_node import repair_planner_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.risk_check_node import risk_check_node
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node
from app.nodes.smoke_test_node import smoke_test_node
from app.state import ReproductionState


def route_after_action_builder(state: ReproductionState) -> str:
    if state.get("pending_action"):
        return "risk_check"
    if state.get("log_path"):
        return "log_debug"
    return "final_report"


def route_after_risk_check(state: ReproductionState) -> str:
    if state.get("final_status") == "blocked":
        return "final_report"
    if state.get("requires_approval"):
        return "human_review"
    return "preflight_check"


def route_after_human_review(state: ReproductionState) -> str:
    decision = state.get("user_approval")
    if decision == "approved":
        return "preflight_check"
    return "final_report"


def route_after_preflight(state: ReproductionState) -> str:
    if state.get("preflight_passed"):
        return "smoke_test"
    return "final_report"


def route_after_smoke_test(state: ReproductionState) -> str:
    status = state.get("smoke_test_status")
    if status in {"passed", "skipped"}:
        return "executor"
    if status == "failed" and state.get("log_path"):
        return "log_debug"
    return "final_report"


def route_after_executor(state: ReproductionState) -> str:
    if state.get("final_status") == "failed" and state.get("log_path"):
        return "log_debug"
    return "final_report"


def route_after_log_debug(state: ReproductionState) -> str:
    attempts = int(state.get("repair_attempt_count", 0))
    if attempts >= settings.max_repair_attempts:
        return "final_report"
    return "repair_planner"


def route_after_repair_planner(state: ReproductionState) -> str:
    proposal = state.get("repair_proposal", {})
    if proposal.get("kind") == "edit_command" and proposal.get("repaired_command"):
        return "repair_action_builder"
    return "final_report"


def route_after_repair_action_builder(state: ReproductionState) -> str:
    if state.get("pending_action"):
        return "risk_check"
    return "final_report"


def build_graph():
    builder = StateGraph(ReproductionState)

    builder.add_node("run_context", run_context_node)
    builder.add_node("paper_reader", paper_reader_node)
    builder.add_node("method_extractor", method_extractor_node)
    builder.add_node("repo_scan", repo_scan_node)
    builder.add_node("code_search", code_search_node)
    builder.add_node("mapping", mapping_node)
    builder.add_node("experiment_plan", experiment_plan_node)
    builder.add_node("command_selection", command_selection_node)
    builder.add_node("action_builder", action_builder_node)
    builder.add_node("risk_check", risk_check_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("preflight_check", preflight_check_node)
    builder.add_node("smoke_test", smoke_test_node)
    builder.add_node("executor", executor_node)
    builder.add_node("log_debug", log_debug_node)
    builder.add_node("repair_planner", repair_planner_node)
    builder.add_node("repair_action_builder", repair_action_builder_node)
    builder.add_node("final_report", final_report_node)
    builder.add_node("run_manifest", run_manifest_node)

    builder.add_edge(START, "run_context")
    builder.add_edge("run_context", "paper_reader")
    builder.add_edge("paper_reader", "method_extractor")
    builder.add_edge("method_extractor", "repo_scan")
    builder.add_edge("repo_scan", "code_search")
    builder.add_edge("code_search", "mapping")
    builder.add_edge("mapping", "experiment_plan")
    builder.add_edge("experiment_plan", "command_selection")
    builder.add_edge("command_selection", "action_builder")

    builder.add_conditional_edges("action_builder", route_after_action_builder)
    builder.add_conditional_edges("risk_check", route_after_risk_check)
    builder.add_conditional_edges("human_review", route_after_human_review)
    builder.add_conditional_edges("preflight_check", route_after_preflight)
    builder.add_conditional_edges("smoke_test", route_after_smoke_test)
    builder.add_conditional_edges("executor", route_after_executor)
    builder.add_conditional_edges("log_debug", route_after_log_debug)
    builder.add_conditional_edges("repair_planner", route_after_repair_planner)
    builder.add_conditional_edges(
        "repair_action_builder",
        route_after_repair_action_builder,
    )

    builder.add_edge("final_report", "run_manifest")
    builder.add_edge("run_manifest", END)

    return builder.compile(checkpointer=build_checkpointer())
```

### 为什么 `repair_action_builder` 要回到 `risk_check`

因为 repair 之后其实已经是一个新动作了。

它应该重新经过：

- `risk_check`
- `human_review`
- `preflight_check`
- `smoke_test`

而不是跳过这些保护层。

---

## 十一、更新 Executor 与 Final Report：补足上下文

这一阶段建议顺手改两个小地方。

### 1. `executor_node.py` 补上 `active_execution_mode="full"`

否则后面的 debug / repair planner 很难区分：

- 是 smoke 失败
- 还是 full run 失败

建议在 [app/nodes/executor_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/executor_node.py:1) 的返回 payload 里加上：

```python
    payload = {
        "active_execution_mode": "full",
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
```

### 2. `final_report_node.py` 增加 Smoke / Repair 摘要

建议在 [app/nodes/final_report_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/final_report_node.py:1) 里补两个 section：

```python
    smoke_report = state.get("smoke_test_report", {})
    smoke_items: list[str] = []
    if smoke_report:
        smoke_items.append(f"Smoke Status: `{smoke_report.get('status', 'unknown')}`")
        smoke_items.append(
            f"Smoke Overrides: {len(smoke_report.get('applied_overrides', []))}"
        )
        for item in smoke_report.get("applied_overrides", [])[:5]:
            smoke_items.append(f"Override: {item}")
    lines += _render_section("Smoke Test Summary", smoke_items)

    repair_proposal = state.get("repair_proposal", {})
    repair_items: list[str] = []
    if repair_proposal:
        repair_items.append(f"Repair Kind: `{repair_proposal.get('kind', 'unknown')}`")
        repair_items.append(f"Repair Summary: {repair_proposal.get('summary', 'N/A')}")
    repair_attempt_count = state.get("repair_attempt_count")
    if repair_attempt_count is not None:
        repair_items.append(f"Repair Attempt Count: `{repair_attempt_count}`")
    lines += _render_section("Repair Summary", repair_items)
```

### 一个顺手提醒

你当前 `final_report_node.py` 里如果还在按旧结构读：

- `pending_action["type"]`
- `pending_action["command"]`

那这一阶段建议一起改成兼容结构化动作的写法，比如：

- `pending_action["action_type"]`
- `pending_action["program"]`
- `pending_action["args"]`

否则最终报告里的动作摘要会一直是旧格式残影。

---

## 十二、更新 Artifact 与 Run Manifest：把 smoke / repair 纳入可追溯记录

你在 Phase 19 已经有了：

- [app/tools/artifact_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/artifact_tools.py:1)
- `run_manifest.json`

这一阶段非常推荐把新的 smoke / repair 产物也纳入归档。

### 1. 更新 `classify_output_file(...)`

建议在 [app/tools/artifact_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/artifact_tools.py:1) 里补上：

```python
def classify_output_file(path: str) -> str:
    name = Path(path).name

    if name in {
        "paper_summary.json",
        "method_modules.json",
        "repo_map.json",
        "repo_summary.md",
        "paper_code_mapping.json",
        "paper_code_mapping.md",
    }:
        return "analysis"

    if name in {
        "experiment_plan.json",
        "experiment_plan.md",
        "command_selection_record.json",
        "effective_run_commands.json",
        "preflight_report.json",
        "preflight_report.md",
    }:
        return "planning"

    if name in {
        "execution.log",
        "smoke_test.log",
        "smoke_test_report.json",
        "smoke_test_report.md",
    }:
        return "execution"

    if name in {
        "debug_report.json",
        "debug_report.md",
        "repair_proposal.json",
        "repair_proposal.md",
    }:
        return "debug"

    if name in {"final_report.md", "eval_report.json", "eval_report.md"}:
        return "reports"

    return "reports"
```

### 2. 推荐扩展 `build_run_manifest(...)`

建议把 `smoke` 和 `repair` 摘要也放进 manifest：

```python
        "smoke_test": {
            "status": state.get("smoke_test_status"),
            "passed": state.get("smoke_test_passed"),
            "log_path": state.get("smoke_test_log_path"),
            "report": state.get("smoke_test_report"),
        },
        "repair": {
            "attempt_count": state.get("repair_attempt_count", 0),
            "history": state.get("repair_history", []),
            "proposal": state.get("repair_proposal"),
        },
```

### 为什么这里很值得做

因为一旦你后面开始研究：

- 为什么这次 full run 没继续
- 为什么这次走了 repair
- repair 改过几次命令

这些信息都很适合直接从 run manifest 回溯。

---

## 十三、CLI 层：强烈建议增加 `run_smoke` 和 `plan_repair`

这一章我非常推荐你加两个独立命令。

否则你每次想测：

- smoke 派生得对不对
- repair planner 提得好不好

都得跑完整 graph，效率太低。

### 1. `run_smoke`

建议在 [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:1) 里新增：

```python
@app.command()
def run_smoke(
    repo_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "manual smoke test",
    execution_profile: str | None = typer.Option(
        None,
        "--execution-profile",
    ),
):
    profile_id = execution_profile or settings.default_execution_profile
    profile = get_execution_profile(profile_id)
    profile_fingerprint = compute_execution_profile_fingerprint(profile)

    action = build_run_action_from_command(
        command=command,
        cwd=cwd or repo_path,
        source=source,
        reason=reason,
        timeout_seconds=300,
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint=profile_fingerprint,
    )
    action_hash = compute_action_hash(action)

    state = {
        "repo_path": repo_path,
        "execution_profile_id": profile.profile_id,
        "execution_profile_fingerprint": profile_fingerprint,
        "pending_action": action,
        "pending_action_hash": action_hash,
        "output_files": [],
    }

    result = smoke_test_node(state)
    print("[green]smoke test finished[/green]")
    print(result.get("smoke_test_report"))
    print(result.get("output_files", []))
```

### 2. `plan_repair`

建议再新增一个只跑：

```text
log_debug -> repair_planner
```

的命令：

```python
@app.command()
def plan_repair(
    repo_path: str,
    log_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "manual repair planning",
    execution_profile: str | None = typer.Option(
        None,
        "--execution-profile",
    ),
):
    profile_id = execution_profile or settings.default_execution_profile
    profile = get_execution_profile(profile_id)
    profile_fingerprint = compute_execution_profile_fingerprint(profile)

    action = build_run_action_from_command(
        command=command,
        cwd=cwd or repo_path,
        source=source,
        reason=reason,
        timeout_seconds=300,
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint=profile_fingerprint,
    )
    action_hash = compute_action_hash(action)

    state = {
        "repo_path": repo_path,
        "execution_profile_id": profile.profile_id,
        "execution_profile_fingerprint": profile_fingerprint,
        "pending_action": action,
        "pending_action_hash": action_hash,
        "log_path": log_path,
        "repo_map": {},
        "experiment_plan": {},
        "preflight_report": {},
        "smoke_test_report": {},
        "output_files": [],
    }

    state.update(log_debug_node(state))
    state.update(repair_planner_node(state))

    print("[green]repair planning finished[/green]")
    print(state.get("repair_proposal"))
    print(state.get("output_files", []))
```

### 为什么这两个 CLI 很值

因为它们分别回答两个非常常见的问题：

1. `run_smoke`
   - 这条命令会被怎么缩减？
   - smoke 会不会通过？
2. `plan_repair`
   - 当前报错会得到什么 bounded proposal？

这会让你开发这两个节点时轻松很多。

---

## 十四、补测试：建议至少覆盖这 4 类场景

建议新增：

```text
tests/test_smoke_test_node.py
tests/test_repair_action_builder_node.py
tests/test_smoke_repair_flow.py
```

### 最值得测的 4 类场景

1. smoke 能正确降低已存在参数
2. smoke 失败时能把日志交给后续 debug
3. repair action builder 只能接受 bounded command repair
4. repair 后会重新进入风险 / 审批 / preflight / smoke 链

---

## 十五、测试一：`test_smoke_test_node.py`

### 建议代码

```python
from pathlib import Path
from unittest.mock import patch

from app.config import settings
from app.nodes.smoke_test_node import smoke_test_node


def test_smoke_test_node_runs_reduced_action_and_writes_report(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    state = {
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": [
                "train.py",
                "--batch_size", "8",
                "--epochs", "100",
                "--num_workers", "8",
            ],
            "cwd": str(repo_dir),
            "source": "manual",
            "reason": "test",
            "timeout_seconds": 300,
            "env_allowlist": {},
            "writable_paths": [str(repo_dir)],
        },
        "pending_action_hash": "hash_demo",
        "output_files": [],
    }

    fake_result = {
        "ok": True,
        "returncode": 0,
        "stdout": "smoke ok\n",
        "stderr": "",
        "combined_output": "smoke ok\n",
    }

    with patch("app.nodes.smoke_test_node.run_action_safe", return_value=fake_result):
        result = smoke_test_node(state)

    assert result["smoke_test_status"] == "passed"
    assert result["smoke_test_passed"] is True
    assert Path(result["smoke_test_log_path"]).exists()

    report = result["smoke_test_report"]
    assert "--batch_size -> 1" in report["applied_overrides"]
    assert "--epochs -> 1" in report["applied_overrides"]
    assert "--num_workers -> 0" in report["applied_overrides"]


def test_smoke_test_node_skips_when_no_safe_reduction_found(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    state = {
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": ["eval.py", "--config", "configs/eval.yaml"],
            "cwd": str(repo_dir),
            "source": "manual",
            "reason": "test",
            "timeout_seconds": 300,
            "env_allowlist": {},
            "writable_paths": [str(repo_dir)],
        },
        "pending_action_hash": "hash_demo",
        "output_files": [],
    }

    result = smoke_test_node(state)

    assert result["smoke_test_status"] == "skipped"
    assert result["smoke_test_passed"] is True
    assert any(path.endswith("smoke_test_report.json") for path in result["output_files"])


def test_smoke_test_node_sets_log_path_when_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    state = {
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py", "--batch_size", "8"],
            "cwd": str(repo_dir),
            "source": "manual",
            "reason": "test",
            "timeout_seconds": 300,
            "env_allowlist": {},
            "writable_paths": [str(repo_dir)],
        },
        "pending_action_hash": "hash_demo",
        "output_files": [],
    }

    fake_result = {
        "ok": False,
        "returncode": 1,
        "stdout": "",
        "stderr": "RuntimeError: CUDA out of memory",
        "combined_output": "RuntimeError: CUDA out of memory",
    }

    with patch("app.nodes.smoke_test_node.run_action_safe", return_value=fake_result):
        result = smoke_test_node(state)

    assert result["smoke_test_status"] == "failed"
    assert result["log_path"].endswith("smoke_test.log")
    assert result["final_status"] == "failed"
```

---

## 十六、测试二：`test_repair_action_builder_node.py`

### 建议代码

```python
from app.nodes.repair_action_builder_node import repair_action_builder_node


def test_repair_action_builder_rebuilds_pending_action_and_increments_attempts():
    state = {
        "repo_path": "/tmp/repo",
        "selected_run_command_index": 0,
        "edited_run_commands": [
            {
                "command": "python train.py --dataset_path /data/demo --batch_size 8 --epochs 100",
                "cwd": "/tmp/repo",
                "source": "script",
                "risk_level": "high",
                "reason": "demo command",
            }
        ],
        "repair_proposal": {
            "proposal_id": "repair_001",
            "source_error_type": "cuda_oom",
            "kind": "edit_command",
            "summary": "reduce batch size for smoke and rerun",
            "root_cause": "batch size too large",
            "repaired_command": "python train.py --dataset_path /data/demo --batch_size 1 --epochs 1",
            "changed_arguments": ["--batch_size 8 -> 1", "--epochs 100 -> 1"],
            "steps": [],
            "verification_steps": ["rerun smoke test", "rerun full executor"],
            "rollback_steps": [],
            "risks": [],
            "bounded": True,
        },
        "repair_attempt_count": 0,
        "repair_history": [],
        "user_approval": "approved",
        "approval_record": {"action_hash": "old_hash"},
        "preflight_report": {"ready_to_execute": True},
        "smoke_test_report": {"status": "failed"},
        "debug_report": {"error_type": "cuda_oom"},
        "execution_result": {"ok": False},
        "final_status": "failed",
    }

    result = repair_action_builder_node(state)

    assert result["repair_attempt_count"] == 1
    assert result["pending_action"]["program"] == "python"
    assert "--batch_size" in result["pending_action"]["args"]
    assert result["user_approval"] is None
    assert result["approval_record"] is None
    assert result["preflight_report"] is None
    assert result["smoke_test_report"] is None
    assert result["debug_report"] is None


def test_repair_action_builder_rejects_out_of_bounds_command():
    state = {
        "repair_proposal": {
            "proposal_id": "repair_001",
            "source_error_type": "dependency_missing",
            "kind": "edit_command",
            "summary": "install missing package",
            "root_cause": "package missing",
            "repaired_command": "pip install torch",
            "changed_arguments": [],
            "steps": [],
            "verification_steps": [],
            "rollback_steps": [],
            "risks": ["environment mutation"],
            "bounded": True,
        },
        "repair_attempt_count": 0,
    }

    result = repair_action_builder_node(state)

    assert result["final_status"] == "repair_out_of_bounds"
```

---

## 十七、测试三：`test_smoke_repair_flow.py`

### 建议代码

```python
from app.graph import (
    route_after_log_debug,
    route_after_preflight,
    route_after_repair_action_builder,
    route_after_repair_planner,
    route_after_smoke_test,
)


def test_route_after_preflight_goes_to_smoke_when_passed():
    assert route_after_preflight({"preflight_passed": True}) == "smoke_test"


def test_route_after_smoke_test_goes_to_executor_when_passed():
    assert route_after_smoke_test({"smoke_test_status": "passed"}) == "executor"


def test_route_after_smoke_test_goes_to_executor_when_skipped():
    assert route_after_smoke_test({"smoke_test_status": "skipped"}) == "executor"


def test_route_after_smoke_test_goes_to_log_debug_when_failed():
    state = {
        "smoke_test_status": "failed",
        "log_path": "outputs/smoke_test.log",
    }
    assert route_after_smoke_test(state) == "log_debug"


def test_route_after_log_debug_goes_to_repair_planner_before_limit():
    assert route_after_log_debug({"repair_attempt_count": 0}) == "repair_planner"


def test_route_after_repair_planner_goes_to_repair_action_builder_for_edit_command():
    state = {
        "repair_proposal": {
            "kind": "edit_command",
            "repaired_command": "python train.py --batch_size 1",
        }
    }
    assert route_after_repair_planner(state) == "repair_action_builder"


def test_route_after_repair_action_builder_returns_to_risk_check():
    assert route_after_repair_action_builder({"pending_action": {"action_type": "run_command"}}) == "risk_check"
```

### 这些测试分别在证明什么

第一组 smoke tests 证明：

- smoke 缩减逻辑正常
- smoke 失败会把日志交给 debug

第二组 repair tests 证明：

- repair 只能消费 bounded command proposal
- repair 后会强制重新走安全链

第三组 flow tests 证明：

- graph 的关键路由没有走偏

---

## 十八、建议的手工验证顺序

这一章非常推荐你按“先局部、再闭环”的方式验证。

### 1. 先跑单测

```bash
python -m pytest \
  tests/test_smoke_test_node.py \
  tests/test_repair_action_builder_node.py \
  tests/test_smoke_repair_flow.py
```

### 2. 先单独跑 `run_smoke`

例如：

```bash
python -m app.main run-smoke \
  /data/tianshaoqi24/P4Transformer/ \
  "python train-ntu60.py --data-path /data/ntu60 --batch-size 8 --epochs 100 --workers 8" \
  --execution-profile p4transformer-conda
```

理想结果：

- 生成：
  - `outputs/smoke_test.log`
  - `outputs/smoke_test_report.json`
  - `outputs/smoke_test_report.md`
- 报告里能看到：
  - `--batch_size -> 1`
  - `--epochs -> 1`
  - `--num_workers -> 0`

### 3. 再测 repair planner

如果你手头已经有一个失败日志：

```bash
python -m app.main plan-repair \
  /data/tianshaoqi24/P4Transformer/ \
  outputs/smoke_test.log \
  "python train-ntu60.py --data-path /data/ntu60 --batch-size 8 --epochs 100 --workers 8" \
  --execution-profile p4transformer-conda
```

理想结果：

- 生成：
  - `outputs/repair_proposal.json`
  - `outputs/repair_proposal.md`
- proposal 的 `kind` 应该明确是：
  - `edit_command`
  - `manual_only`
  - 或 `no_repair`

### 4. 再跑完整 graph

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer/ \
  --thread-id smoke-repair-001
```

如果中间进入：

- `command_selection_node`
- `human_review_node`

就按你前面已经做好的方式继续 resume。

### 5. 检查最终状态

执行：

```bash
python -m app.main show-state --thread-id smoke-repair-001
```

重点看这些字段：

- `smoke_test_report`
- `smoke_test_status`
- `repair_proposal`
- `repair_attempt_count`
- `repair_history`
- `final_status`

### 6. 检查运行归档

如果你已经接好了 Phase 19 的 run manifest，那还要确认：

- `smoke_test.log`
- `smoke_test_report.json`
- `repair_proposal.json`

都进入了：

```text
runs/<run_id>/
```

---

## 十九、一个非常推荐的本地可控演示场景

如果你想做一个稳定、可重复的 smoke + repair demo，可以自己准备一个极小 fake repo。

### 例子思路

准备一个最小脚本：

```python
# train.py
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--batch_size", type=int, default=8)
parser.add_argument("--epochs", type=int, default=100)
args = parser.parse_args()

if args.batch_size > 1:
    raise RuntimeError("CUDA out of memory")

print("train ok")
```

然后原命令设成：

```text
python train.py --batch_size 8 --epochs 100
```

你就能很稳定地看到：

1. smoke test 自动收缩成：
   - `--batch_size 1`
   - `--epochs 1`
2. smoke test 通过
3. full executor 仍然用原命令，失败
4. debug -> repair planner 生成：
   - `repaired_command = python train.py --batch_size 1 --epochs 1`
5. bounded rerun 后成功

这个场景特别适合做你自己的阶段验收和演示。

---

## 二十、这一阶段的验收标准

你可以按下面这份清单验收。

### 功能验收

- `preflight_check` 通过后会先进入 `smoke_test`
- smoke 能在“已存在参数”的基础上降低常见训练规模
- smoke 失败时会进入 `log_debug`
- debug 之后会生成结构化 `repair_proposal`
- 只有 `kind=edit_command` 的 proposal 才能进入 bounded rerun

### 安全验收

- repair proposal 不允许直接变成：
  - `pip install`
  - `conda install`
  - `git`
  - `rm`
  - 多段 shell
- repair 后必须重新走：
  - `risk_check`
  - `human_review`
  - `preflight_check`
  - `smoke_test`

### 产物验收

- 能生成：
  - `outputs/smoke_test.log`
  - `outputs/smoke_test_report.json`
  - `outputs/smoke_test_report.md`
  - `outputs/repair_proposal.json`
  - `outputs/repair_proposal.md`
- `run_manifest.json` 能追踪：
  - smoke 状态
  - repair 尝试次数
  - repair proposal

---

## 二十一、这一阶段的价值到底是什么

这一阶段是你整个项目从“执行器”向“代理体”升级的一大步。

它的价值不在于：

```text
又多了几个 JSON 文件
```

而在于系统行为的变化：

### 变化 1：从 full run 直冲，变成先低成本试跑

这能显著减少：

- 一上来就 OOM
- 一上来就长时间挂住
- 一上来就高成本失败

### 变化 2：从“只会报错和分析”，变成“能在边界内继续推进”

注意这里不是无限自治，而是：

```text
bounded repair
```

这恰恰是更像真实工程系统的地方。

### 变化 3：debug 不再是终点，而是 repair proposal 的输入

这一步会让你整个项目更像一个真正的：

```text
paper reproduction copilot
```

而不只是“论文分析 + 命令执行 + 日志总结”的流水线。

---

## 二十二、下一步最值得做什么

这一步做完后，不建议马上开放文件修改。更稳妥的下一阶段是：

```text
Phase 12：Structured Output Reliability
```

先把当前结构化调用补成可靠控制面：

- 显式使用 JSON Schema strict
- Pydantic 结构及语义校验
- 携带 validation error 有限重试
- 保存每次 structured output attempt
- 连续失败后确定性规则或 no_repair 降级

注意：

```text
模型输出稳定性是 Patch Proposal 的前置基础
不能把格式不可靠的输出直接升级成文件修改动作
```

完整教程见：

```text
a_implementation_guides/23_phase_12_structured_output_reliability.md
```

完成后再进入：

```text
Phase 13：Manual File Repair Review 与 Patch-Level Verification
```

---

## 最后一句话总结这一阶段

这一阶段的本质不是“多跑一次小实验”，也不是“自动改个参数”，而是：

```text
把系统从“执行前做检查”
升级成“先低成本试跑，失败后还能在边界内提出修复并重新进入安全执行链”
```

这是你这个项目真正开始具备“闭环自治能力”的地方。
