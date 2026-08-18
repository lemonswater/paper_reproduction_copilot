# 20. 闭环后第五阶段：Preflight Check 与 Environment Readiness

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
```

这说明你现在的系统已经不只是“分析论文并写报告”，而是真的具备了一条比较完整的执行链：

```text
experiment_plan
  -> command_selection
  -> action_builder
  -> risk_check
  -> human_review
  -> executor
  -> final_report
  -> run_manifest
```

但是只要你开始真的拿它去跑论文仓库，很快就会发现一个非常高频的问题：

```text
很多失败，其实不是训练逻辑失败
而是执行前的环境根本没准备好
```

最常见的情况包括：

- `python` / `torchrun` 根本不存在
- 当前 `cwd` 不存在
- 训练脚本路径不存在
- `--dataset_path` 还是占位符，或者目标路径不存在
- `--config` / `--weights` 指向的文件不存在
- PyTorch 没装，或者 `import torch` 就报错
- repo 根目录连 `requirements.txt` / `environment.yml` / `pyproject.toml` 都没找到

这些问题如果每次都等到 `executor` 真跑起来后再报错，效率会很低。

所以这一阶段要补的是：

```text
在真正执行之前
先做一次 deterministic preflight
```

也就是：

- 先检查环境条件是否满足
- 能提前发现的问题，提前阻断
- 生成结构化 preflight 报告
- 只有在“基本可执行”时，才进入 `executor`

---

## 这一阶段做完后，执行链会变成什么

当前链路大致是：

```text
risk_check
  -> human_review
  -> executor
```

这一阶段完成后，建议升级成：

```text
risk_check
  -> human_review（如果需要审批）
  -> preflight_check
  -> executor
```

更完整一点写，就是：

```text
action_builder
  -> risk_check
      -> blocked? final_report
      -> approval needed? human_review
      -> otherwise preflight_check

human_review
  -> approved? preflight_check
  -> rejected / revise? final_report

preflight_check
  -> ready_to_execute? executor
  -> otherwise final_report
```

这样系统的语义就很清楚了：

- `risk_check`
  - 判断“安不安全”
- `human_review`
  - 判断“让不让执行”
- `preflight_check`
  - 判断“现在能不能执行”
- `executor`
  - 真正执行

这是四个完全不同的职责层。

---

## 先说清楚：这一阶段先做“最小可落地版本”

Preflight 其实可以做得非常深。

如果你愿意，后面完全可以继续扩展成三层：

```text
Static Preflight
Runtime Probe
Smoke Test
```

但我不建议你一上来就做到那么重。

### 这一章建议的范围

这一章先实现：

1. `Static Check`
   - 检查 `cwd`
   - 检查程序是否在 PATH 中
   - 检查脚本文件是否存在
   - 检查 `dataset_path / config / weights / checkpoint` 是否存在
   - 检查命令参数里是否还残留占位符
   - 检查 repo 里是否有依赖声明文件

2. `Light Runtime Probe`
   - `python --version`
   - `python -c "import torch; print(torch.__version__)"`
   - `python -c "import torch; print(torch.cuda.is_available())"`

### 这一章先不做什么

先不做：

- 自动安装依赖
- 自动改环境
- 自动修 config
- 自动拉取数据集
- 自动 smoke test 一轮训练

原因很简单：

```text
Phase 20 的目标是“执行前把明显问题前置暴露”
不是“替用户自动修环境”
```

---

## 本阶段建议修改 / 新增的文件

```text
app/schemas.py
app/state.py
app/tools/preflight_tools.py
app/tools/artifact_tools.py
app/nodes/preflight_check_node.py
app/nodes/final_report_node.py
app/graph.py
app/main.py
tests/test_preflight_check_node.py
```

如果你希望这个阶段也方便单独调试，我还推荐：

```text
app/main.py
```

里增加一个独立命令：

```text
run_preflight
```

这样你不用每次都完整跑整张 graph。

---

## 开始前的两个前置认识

### 认识 1：Preflight 不是 Risk Check

很多人第一次实现时会把这两件事混在一起。

你要明确：

- `risk_check`
  - 这个命令危险不危险
- `preflight_check`
  - 这个命令现在能不能跑

举个例子：

```text
python train.py --dataset_path /missing/path
```

它可能：

- 风险不高
- 但完全不能执行

所以：

```text
risk_check 通过
不代表 preflight 通过
```

### 认识 2：Preflight 优先做“规则检查”，不要先让 LLM 猜

这一阶段一定要坚持：

```text
能用工具直接判断的，不要先交给 LLM 猜
```

比如：

- 路径存不存在
- 程序在不在 PATH
- `python --version` 能不能执行
- `import torch` 会不会失败

这些都应该优先用 deterministic 工具检查。

LLM 最适合做的是：

- 解释 preflight 结果
- 总结建议
- 生成人类可读报告

---

## 一、先补 Schema：定义 `PreflightItem` 和 `PreflightReport`

当前 [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1) 里还没有 preflight 专用结构。

这一阶段建议补两个模型：

1. `PreflightItem`
2. `PreflightReport`

### 建议代码

下面是建议加入到 [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1) 的新增部分：

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
    # 这条检查项的名字，例如：
    # - working_directory_exists
    # - program_in_path
    # - dataset_path_exists
    name: str

    # 把 preflight 明确分层，方便后续继续扩展：
    # static / runtime / smoke
    category: Literal["static", "runtime", "smoke"] = "static"

    # 当前检查结果。
    status: Literal["passed", "warning", "failed", "unknown"]

    # 给人看的证据描述。
    evidence: str

    # 建议动作。
    recommendation: str | None = None


class PreflightReport(BaseModel):
    action_id: str | None = None
    action_hash: str | None = None
    ready_to_execute: bool = False
    summary: str
    items: list[PreflightItem] = Field(default_factory=list)
    blocking_items: list[str] = Field(default_factory=list)
    generated_at: str
```

### 为什么要单独有 `PreflightReport`

因为 preflight 不是一条布尔值。

你最终肯定会需要：

- 哪些项通过了
- 哪些项只是 warning
- 哪些项是 blocking failure
- 为什么失败
- 给什么建议

所以：

```text
不要只返回一个 preflight_passed=True/False
而是先有结构化 report，再从 report 派生布尔值
```

---

## 二、扩展 State：把 preflight 结果纳入状态

当前 [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1) 还没有 preflight 字段。

建议新增：

- `preflight_report`
- `preflight_passed`
- `preflight_report_path`

### 建议代码

下面是建议修改后的 [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1)：

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

    # Phase 20：执行前预检结果。
    preflight_report: Optional[dict[str, Any]]
    preflight_passed: bool
    preflight_report_path: Optional[str]

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

### 为什么 `preflight_passed` 仍然值得保留

虽然我们前面说了不能只返回一个布尔值，但布尔值仍然有用，因为 graph 路由层最关心的是：

```text
接下来是去 executor，还是去 final_report
```

也就是说：

- `PreflightReport`
  - 给人看、给调试看、给评测看
- `preflight_passed`
  - 给路由看

---

## 三、工具层：新增 `preflight_tools.py`

这一层是本阶段的核心。

建议新增文件：

```text
app/tools/preflight_tools.py
```

### 设计原则

这个工具层要坚持三个原则：

1. 先检查静态事实
2. 再做轻量 probe
3. 不要在 preflight 里执行用户项目逻辑

也就是说，preflight 可以执行：

- `python --version`
- `python -c "import torch"`

但不要直接执行：

- `python train.py`
- `torchrun train.py ...`

### 很重要：Preflight 的命令解析不要直接复用“执行期 parser”

这是 Phase 20 非常容易踩的一个坑。

你前面已经有了一个严格的执行期解析函数：

```python
build_run_action_from_command(...)
```

它的职责是：

```text
把“准备真正执行”的命令
转成一个可执行的结构化动作
```

所以它会故意比较严格，例如：

- 不允许占位符残留
- 不允许不受支持的 shell 语法
- 不允许模糊的命令结构

这对于真正执行前的安全链是对的。

但是对 preflight 来说，这种严格会带来一个问题：

```text
preflight 本来就是要检查“为什么这条命令现在还不能执行”
如果你在进入 preflight 之前就先把命令拦死了
那 preflight 就失去意义了
```

最典型的例子就是：

```bash
python -m app.main run-preflight \
  /data/tianshaoqi24/P4Transformer/ \
  "python train-ntu60.py --dataset_path <path_to_ntu60>"
```

如果 `run_preflight()` 里直接调用：

```python
build_run_action_from_command(...)
```

那么 `<path_to_ntu60>` 里的 `<` 很可能会在 preflight 之前就被识别成“不支持的 shell 语法”，直接抛出：

```text
ValueError: unsupported shell syntax in run command; please convert it into a single executable command
```

这并不是你想要的行为。

更合理的行为应该是：

- `run_preflight` 正常执行
- 生成 `preflight_report`
- 在报告里明确告诉你：
  - `command_placeholders_resolved = failed`
  - 或 `dataset_path_resolved = failed`
- `ready_to_execute = false`

所以这里建议你**不要直接复用执行期 parser**，而是单独提供一个：

```python
build_preflight_action_from_command(...)
```

它和执行期 parser 的边界应该是：

#### 执行期 parser

- 面向“现在就要执行”的命令
- 必须拒绝占位符
- 必须拒绝模糊和危险的 shell 语法

#### Preflight parser

- 面向“先检查一下”的命令
- 可以保留占位符
- 仍然拒绝真正的多命令拼接 / 重定向 / 复杂 shell 逻辑
- 目标是把命令先结构化，交给 preflight 规则继续判断

一句话概括：

```text
执行期 parser 是“只接受可执行命令”
preflight parser 是“接受可能还不能执行、但值得被检查的命令”
```

### 建议代码

```python
import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from app.schemas import ExecutableAction, PreflightItem, PreflightReport


# 这些占位符在你前面几个阶段里已经频繁出现过。
# Preflight 的一个重要职责，就是在真正执行前把它们拦下来。
PLACEHOLDER_MARKERS = (
    "<path",
    "<todo>",
    "TODO",
    "[需要确认参数]",
    "<需要确认>",
)


# 这些 flag 的 value 高概率是路径，应该做 exists 检查。
PATH_LIKE_FLAGS = {
    "--dataset_path": "dataset path",
    "--data_root": "data root",
    "--data-dir": "data directory",
    "--config": "config file",
    "--cfg": "config file",
    "--weights": "weights file",
    "--pretrained": "pretrained weights",
    "--checkpoint": "checkpoint file",
    "--ckpt": "checkpoint file",
    "--resume": "checkpoint file",
}


# 对 preflight 来说，我们仍然不希望支持真正复杂的 shell 逻辑。
# 但注意：这里不要把 "<path_to_xxx>" 这种占位符简单粗暴地判成 shell redirection。
UNSUPPORTED_PREFLIGHT_TEXT_MARKERS = (
    "&&",
    "||",
    ";",
    "|",
    "$(",
    "`",
)

UNSUPPORTED_PREFLIGHT_TOKENS = {"<", ">", ">>", "<<"}


def _contains_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker.lower() in lowered for marker in PLACEHOLDER_MARKERS)


def _strip_leading_cd_for_preflight(command: str, cwd: str) -> tuple[str, str]:
    """
    兼容这类常见命令：
        cd modules && python setup.py install

    如果是标准的“前置 cd + 单条命令”，就把 cwd 提出来，
    剩下的部分继续按 preflight 单命令解析。
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


def _contains_unsupported_preflight_shell_syntax(command: str) -> bool:
    return any(marker in command for marker in UNSUPPORTED_PREFLIGHT_TEXT_MARKERS)


def _resolve_path(candidate: str, cwd: Path) -> Path:
    """
    把命令里出现的路径解析成绝对路径。
    相对路径默认相对当前动作的 cwd。
    """
    path = Path(candidate)
    if path.is_absolute():
        return path
    return (cwd / path).resolve()


def _add_item(
    items: list[PreflightItem],
    *,
    name: str,
    category: str,
    status: str,
    evidence: str,
    recommendation: str | None = None,
) -> None:
    items.append(
        PreflightItem(
            name=name,
            category=category,  # type: ignore[arg-type]
            status=status,      # type: ignore[arg-type]
            evidence=evidence,
            recommendation=recommendation,
        )
    )


def _extract_flag_values(args: list[str]) -> dict[str, str]:
    """
    支持两种常见参数写法：
    1. --config configs/train.yaml
    2. --config=configs/train.yaml
    """
    values: dict[str, str] = {}

    index = 0
    while index < len(args):
        token = args[index]

        if token in PATH_LIKE_FLAGS and index + 1 < len(args):
            values[token] = args[index + 1]
            index += 2
            continue

        if token.startswith("--") and "=" in token:
            key, value = token.split("=", 1)
            if key in PATH_LIKE_FLAGS:
                values[key] = value

        index += 1

    return values


def _detect_entry_script(program: str, args: list[str], cwd: Path) -> Path | None:
    """
    对 python / bash 这类命令，尽量找出它真正要执行的脚本文件。
    例如：
        python train.py
        bash scripts/train.sh

    如果是：
        python -m module_name
    那就不做脚本存在性检查。
    """
    if not args:
        return None

    if program == "python":
        first = args[0]
        if first == "-m":
            return None
        if first.startswith("-"):
            return None
        return _resolve_path(first, cwd)

    if program == "bash":
        first = args[0]
        if first.startswith("-"):
            return None
        return _resolve_path(first, cwd)

    return None


def _detect_dependency_files(repo_path: str | None) -> list[Path]:
    """
    不要求所有 repo 都有同一种依赖文件，
    但如果一个都没有，至少要给 warning。
    """
    if not repo_path:
        return []

    repo_dir = Path(repo_path)
    candidates = [
        repo_dir / "requirements.txt",
        repo_dir / "pyproject.toml",
        repo_dir / "environment.yml",
        repo_dir / "environment.yaml",
    ]
    return [path for path in candidates if path.exists()]


def _run_probe(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 8,
) -> tuple[bool, str]:
    """
    运行一个低风险 probe。

    注意：
    - shell=False
    - timeout 短
    - 只用于轻量环境探测
    """
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        return False, str(exc)

    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode == 0:
        return True, output.strip() or "probe succeeded"
    return False, output.strip() or f"probe failed with return code {result.returncode}"


def build_preflight_action_from_command(
    *,
    command: str,
    cwd: str,
    source: str,
    reason: str,
    timeout_seconds: int = 300,
) -> dict:
    """
    为 preflight 构造结构化动作。

    注意它和 build_run_action_from_command(...) 的区别：
    - 这里允许命令里保留占位符
    - 但仍然拒绝真正复杂的 shell 语法
    - 目的不是立刻执行，而是让 preflight 能继续检查
    """
    normalized_command, normalized_cwd = _strip_leading_cd_for_preflight(command, cwd)

    # 对 preflight 仍然要拒绝真正复杂的 shell 语法，
    # 否则后面的静态检查会越来越难做。
    if _contains_unsupported_preflight_shell_syntax(normalized_command):
        raise ValueError(
            "unsupported shell syntax in preflight command; please keep it to a single executable invocation"
        )

    try:
        tokens = shlex.split(normalized_command)
    except ValueError as exc:
        raise ValueError(f"invalid shell quoting: {exc}") from exc

    if not tokens:
        raise ValueError("empty preflight command")

    # 这里单独拦真正的 shell 重定向 token。
    # 这样既能拒绝：python train.py < input.txt
    # 又不会误伤：--dataset_path <path_to_ntu60>
    if any(token in UNSUPPORTED_PREFLIGHT_TOKENS for token in tokens):
        raise ValueError(
            "shell redirection is not supported in preflight command; pass concrete argument values instead"
        )

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


def collect_static_preflight_items(action: dict, repo_path: str | None = None) -> list[PreflightItem]:
    items: list[PreflightItem] = []

    program = action.get("program", "")
    args = action.get("args", [])
    cwd = Path(action.get("cwd") or ".")

    # 1. cwd 是否存在
    if cwd.exists() and cwd.is_dir():
        _add_item(
            items,
            name="working_directory_exists",
            category="static",
            status="passed",
            evidence=f"working directory exists: {cwd}",
        )
    else:
        _add_item(
            items,
            name="working_directory_exists",
            category="static",
            status="failed",
            evidence=f"working directory missing: {cwd}",
            recommendation="确认 repo_path / cwd 是否正确。",
        )

    # 2. cwd 是否可写
    if cwd.exists():
        if os.access(cwd, os.W_OK):
            _add_item(
                items,
                name="working_directory_writable",
                category="static",
                status="passed",
                evidence=f"working directory is writable: {cwd}",
            )
        else:
            _add_item(
                items,
                name="working_directory_writable",
                category="static",
                status="failed",
                evidence=f"working directory is not writable: {cwd}",
                recommendation="确认目录权限，或把动作切到可写目录。",
            )

    # 3. 程序是否在 PATH 中
    resolved_program = shutil.which(program)
    if resolved_program:
        _add_item(
            items,
            name="program_in_path",
            category="static",
            status="passed",
            evidence=f"program resolved to: {resolved_program}",
        )
    else:
        _add_item(
            items,
            name="program_in_path",
            category="static",
            status="failed",
            evidence=f"program not found in PATH: {program}",
            recommendation="确认虚拟环境是否激活，或确认命令程序是否已安装。",
        )

    # 4. 参数里是否还残留占位符
    joined = " ".join([program, *args]).strip()
    if _contains_placeholder(joined):
        _add_item(
            items,
            name="command_placeholders_resolved",
            category="static",
            status="failed",
            evidence=f"command still contains placeholders: {joined}",
            recommendation="把 <path> / TODO / [需要确认参数] 替换成真实值。",
        )
    else:
        _add_item(
            items,
            name="command_placeholders_resolved",
            category="static",
            status="passed",
            evidence="no unresolved placeholders detected in command arguments",
        )

    # 5. 如果能识别出真正的脚本文件，就检查它是否存在
    entry_script = _detect_entry_script(program, args, cwd)
    if entry_script is not None:
        if entry_script.exists():
            _add_item(
                items,
                name="entry_script_exists",
                category="static",
                status="passed",
                evidence=f"entry script exists: {entry_script}",
            )
        else:
            _add_item(
                items,
                name="entry_script_exists",
                category="static",
                status="failed",
                evidence=f"entry script missing: {entry_script}",
                recommendation="确认命令里的脚本路径是否正确。",
            )

    # 6. 检查 path-like 参数
    for flag, raw_value in _extract_flag_values(args).items():
        label = PATH_LIKE_FLAGS[flag]

        if _contains_placeholder(raw_value):
            _add_item(
                items,
                name=f"{flag}_resolved",
                category="static",
                status="failed",
                evidence=f"{label} still contains placeholder: {raw_value}",
                recommendation=f"把 {flag} 替换成真实路径。",
            )
            continue

        target_path = _resolve_path(raw_value, cwd)
        if target_path.exists():
            _add_item(
                items,
                name=f"{flag}_exists",
                category="static",
                status="passed",
                evidence=f"{label} exists: {target_path}",
            )
        else:
            _add_item(
                items,
                name=f"{flag}_exists",
                category="static",
                status="failed",
                evidence=f"{label} missing: {target_path}",
                recommendation=f"确认 {flag} 指向的路径存在。",
            )

    # 7. 依赖声明文件存在性
    dependency_files = _detect_dependency_files(repo_path)
    if dependency_files:
        _add_item(
            items,
            name="dependency_manifest_detected",
            category="static",
            status="passed",
            evidence="detected dependency files: "
            + ", ".join(str(path.name) for path in dependency_files),
        )
    else:
        _add_item(
            items,
            name="dependency_manifest_detected",
            category="static",
            status="warning",
            evidence="no requirements.txt / pyproject.toml / environment.yml detected",
            recommendation="后续可以从 README 或安装脚本中补充依赖来源。",
        )

    return items


def collect_runtime_preflight_items(action: dict) -> list[PreflightItem]:
    items: list[PreflightItem] = []

    program = action.get("program", "")
    cwd = Path(action.get("cwd") or ".")

    # 程序本身不在 PATH 里，就没必要继续 probe。
    if not shutil.which(program):
        return items

    # 对 python / torchrun 项目来说，python runtime probe 非常关键。
    # 注意：这里做的是轻量探测，不是执行训练脚本。
    if program == "python":
        ok, evidence = _run_probe(["python", "--version"], cwd=cwd)
        _add_item(
            items,
            name="python_version_probe",
            category="runtime",
            status="passed" if ok else "failed",
            evidence=evidence,
            recommendation=None if ok else "确认 python 可执行程序是否可用。",
        )

        ok, evidence = _run_probe(
            ["python", "-c", "import torch; print(torch.__version__)"],
            cwd=cwd,
        )
        _add_item(
            items,
            name="torch_import_probe",
            category="runtime",
            status="passed" if ok else "failed",
            evidence=evidence,
            recommendation=None if ok else "确认当前环境已安装可导入的 PyTorch。",
        )

        ok, evidence = _run_probe(
            ["python", "-c", "import torch; print(torch.cuda.is_available())"],
            cwd=cwd,
        )
        _add_item(
            items,
            name="cuda_available_probe",
            category="runtime",
            status="passed" if ok else "warning",
            evidence=evidence,
            recommendation=None if ok else "如果需要 GPU，请检查 CUDA / 驱动 / PyTorch 兼容性。",
        )

    elif program == "torchrun":
        ok, evidence = _run_probe(["torchrun", "--help"], cwd=cwd)
        _add_item(
            items,
            name="torchrun_help_probe",
            category="runtime",
            status="passed" if ok else "failed",
            evidence=evidence,
            recommendation=None if ok else "确认 torchrun 是否在当前环境中可用。",
        )

    else:
        ok, evidence = _run_probe([program, "--help"], cwd=cwd)
        _add_item(
            items,
            name="program_help_probe",
            category="runtime",
            status="passed" if ok else "warning",
            evidence=evidence,
            recommendation=None if ok else "确认该命令在当前环境中可执行。",
        )

    return items


def build_preflight_report(
    action: dict,
    *,
    repo_path: str | None = None,
    action_hash: str | None = None,
) -> PreflightReport:
    static_items = collect_static_preflight_items(action, repo_path=repo_path)
    runtime_items = collect_runtime_preflight_items(action)
    items = [*static_items, *runtime_items]

    blocking_items = [item.name for item in items if item.status == "failed"]
    ready_to_execute = len(blocking_items) == 0

    if ready_to_execute:
        summary = "preflight passed: no blocking issues detected"
    else:
        summary = (
            "preflight blocked execution: "
            + ", ".join(blocking_items)
        )

    return PreflightReport(
        action_id=action.get("action_id"),
        action_hash=action_hash,
        ready_to_execute=ready_to_execute,
        summary=summary,
        items=items,
        blocking_items=blocking_items,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def render_preflight_report_md(report: PreflightReport) -> str:
    lines = ["# Preflight Report", ""]

    lines += [
        "## Summary",
        "",
        f"- Action ID: `{report.action_id or 'N/A'}`",
        f"- Action Hash: `{report.action_hash or 'N/A'}`",
        f"- Ready To Execute: `{report.ready_to_execute}`",
        f"- Generated At: `{report.generated_at}`",
        f"- Summary: {report.summary}",
        "",
    ]

    if report.blocking_items:
        lines += ["## Blocking Items", ""]
        for item in report.blocking_items:
            lines.append(f"- {item}")
        lines.append("")

    lines += ["## Items", ""]
    for item in report.items:
        lines.append(f"### {item.name}")
        lines.append("")
        lines.append(f"- Category: `{item.category}`")
        lines.append(f"- Status: `{item.status}`")
        lines.append(f"- Evidence: {item.evidence}")
        if item.recommendation:
            lines.append(f"- Recommendation: {item.recommendation}")
        lines.append("")

    return "\n".join(lines)
```

### 这份工具代码的核心价值

这份工具层做了 5 件非常关键的事：

1. 检查命令中还是否残留占位符
2. 检查脚本 / 数据 / config / checkpoint 路径是否存在
3. 检查程序本身是否可执行
4. 做轻量 Python / Torch runtime probe
5. 生成结构化 `PreflightReport`

也就是说：

```text
它不是在“猜为什么会失败”
而是在“提前发现本来就不该执行的问题”
```

---

## 四、节点层：新增 `preflight_check_node.py`

有了工具层后，下一步就是把 preflight 变成一个 graph 节点。

建议新增：

```text
app/nodes/preflight_check_node.py
```

### 这个节点要负责什么

它主要负责：

1. 从 state 中拿到 `pending_action`
2. 调用 `build_preflight_report(...)`
3. 把报告写入 `outputs/preflight_report.json` 和 `outputs/preflight_report.md`
4. 把结果回写到 state
5. 如果 preflight 失败，则阻断后续执行

### 建议代码

```python
from app.config import settings
from app.tools.preflight_tools import build_preflight_report, render_preflight_report_md


def preflight_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {
            "preflight_report": None,
            "preflight_passed": False,
            "final_status": "blocked",
            "error": "missing pending_action before preflight",
        }

    action_hash = state.get("pending_action_hash")
    report = build_preflight_report(
        pending_action,
        repo_path=state.get("repo_path"),
        action_hash=action_hash,
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = settings.output_dir / "preflight_report.json"
    report_md_path = settings.output_dir / "preflight_report.md"

    report_json_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_md_path.write_text(
        render_preflight_report_md(report),
        encoding="utf-8",
    )

    payload = {
        "preflight_report": report.model_dump(),
        "preflight_passed": report.ready_to_execute,
        "preflight_report_path": str(report_json_path),
        "output_files": [
            *state.get("output_files", []),
            str(report_json_path),
            str(report_md_path),
        ],
    }

    # 当前链路里，如果 risk_check 判定不需要人工审批，
    # human_review 节点不会被经过。
    # 但 executor 现在又要求 user_approval 至少是 "not_required"。
    # 所以这里顺手把默认值补上，保证“无需审批 -> preflight -> executor”这条链是自洽的。
    if not state.get("requires_approval") and not state.get("user_approval"):
        payload["user_approval"] = "not_required"

    if report.ready_to_execute:
        return payload

    payload["final_status"] = "blocked"
    payload["error"] = report.summary
    payload["last_action_result"] = {
        "status": "blocked_by_preflight",
        "pending_action": pending_action,
        "blocking_items": report.blocking_items,
    }
    return payload
```

### 为什么这里把失败状态记成 `blocked`

因为 preflight 失败不是“执行失败”。

它的语义更准确地说是：

```text
执行还没开始
但前置条件不满足
所以先阻断
```

所以：

- `failed`
  - 更适合 executor 真跑过了但失败
- `blocked`
  - 更适合前置条件不满足

---

## 五、Graph 接入：把 preflight 插到 executor 前面

现在要把 `preflight_check_node` 接进 [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1)。

这一步是本阶段最关键的 graph 改造。

### 设计思路

你不能只是简单地：

```python
builder.add_edge("human_review", "preflight_check")
builder.add_edge("preflight_check", "executor")
```

因为 `human_review` 之后并不一定都应该继续执行。

例如：

- `approved`
  - 可以继续 preflight
- `rejected`
  - 应该直接结束
- `revise`
  - 也应该先结束，而不是继续 preflight

所以这里更合理的是增加两个路由函数：

1. `route_after_human_review`
2. `route_after_preflight`

### 建议代码

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
from app.nodes.preflight_check_node import preflight_check_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.risk_check_node import risk_check_node
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node
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
        return "executor"
    return "final_report"


def route_after_executor(state: ReproductionState) -> str:
    if state.get("final_status") == "failed" and state.get("log_path"):
        return "log_debug"
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
    builder.add_node("executor", executor_node)
    builder.add_node("log_debug", log_debug_node)
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
    builder.add_conditional_edges("executor", route_after_executor)

    builder.add_edge("log_debug", "final_report")
    builder.add_edge("final_report", "run_manifest")
    builder.add_edge("run_manifest", END)

    return builder.compile(checkpointer=build_checkpointer())
```

### 这一步的图结构变化

改完后，执行链就会从：

```text
risk_check -> human_review -> executor
```

升级成：

```text
risk_check -> human_review -> preflight_check -> executor
```

而且“无需审批”的分支也会变成：

```text
risk_check -> preflight_check -> executor
```

这就是真正完整的：

```text
安全性检查
  + 审批
  + 可执行性检查
  + 执行
```

---

## 六、更新 Artifact 分类：把 preflight 产物归档进去

你在 Phase 19 已经有了 [app/tools/artifact_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/artifact_tools.py:1)。

既然这一阶段会新生成：

- `preflight_report.json`
- `preflight_report.md`

就要记得把它们归进 `runs/<run_id>/` 的某个类别里。

### 为什么这一点容易漏掉

如果你只在 `preflight_check_node` 里把文件写到 `outputs/`，但忘了更新 `artifact_tools.py`，就会出现：

```text
preflight 明明跑过了
但 run manifest 里看不到它
```

### 建议修改

在 [app/tools/artifact_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/artifact_tools.py:1) 的 `classify_output_file(...)` 里补上：

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
        # Phase 20：preflight 报告也可以先归到 planning。
        "preflight_report.json",
        "preflight_report.md",
    }:
        return "planning"

    if name in {"execution.log"}:
        return "execution"

    if name in {"debug_report.json", "debug_report.md"}:
        return "debug"

    if name in {"final_report.md", "eval_report.json", "eval_report.md"}:
        return "reports"

    return "reports"
```

### 为什么我这里把 preflight 放到 `planning`

因为在这个项目阶段里，preflight 更接近：

```text
执行前规划与准备的最后一道检查
```

当然你也可以把它归到 `reports/`。

这不是原则性问题，关键是：

```text
要稳定、有约定、能在 run manifest 里找到
```

---

## 七、建议同步更新 Final Report：加入 Preflight 摘要

这一步不是绝对必须，但很推荐。

因为你已经有了结构化 preflight 报告，如果最终 `final_report.md` 里一点都不体现，会显得这一步“存在感很弱”。

建议在 [app/nodes/final_report_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/final_report_node.py:1) 中加一个摘要 section。

### 建议修改思路

在 `_render_final_report(...)` 里新增一段：

```python
    # 8. Preflight 摘要
    preflight_report = state.get("preflight_report", {})
    preflight_items: list[str] = []
    if preflight_report:
        preflight_items.append(
            f"Ready To Execute: `{preflight_report.get('ready_to_execute', False)}`"
        )
        preflight_items.append(
            f"Blocking Items: {len(preflight_report.get('blocking_items', []))}"
        )

        for name in preflight_report.get("blocking_items", [])[:5]:
            preflight_items.append(f"Blocking: {name}")

    lines += _render_section("Preflight Summary", preflight_items)
```

然后把原来的 Debug / Output Files 序号顺延一下即可。

### 这样做的好处

以后你看到 `final_report.md` 时，一眼就能知道：

- 是不是被 preflight 挡住了
- 被哪几项挡住了

---

## 八、CLI 层：推荐增加一个单独的 `run_preflight` 命令

这一阶段最推荐你加的调试命令就是：

```text
python -m app.main run-preflight ...
```

因为它会极大降低你的测试成本。

否则每次想测 preflight，都要：

```text
run_graph
  -> command selection
  -> human review
  -> preflight
```

这太重了。

### 建议修改

在 [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:1) 中新增：

```python
import json
from pathlib import Path

import typer
from langgraph.types import Command
from rich import print

from app.config import settings
from app.graph import build_graph
from app.memory import checkpoint
from app.memory.checkpoint import build_checkpointer
from app.nodes.code_search_node import code_search_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.preflight_check_node import preflight_check_node
from app.nodes.repo_scan_node import repo_scan_node
from app.tools.action_tools import compute_action_hash
from app.tools.preflight_tools import build_preflight_action_from_command

app = typer.Typer(help="Paper Reproduction Copilot")


@app.command()
def run_preflight(
    repo_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "manual preflight check",
):
    """
    单独跑一次 preflight，方便调试执行前检查逻辑。
    """
    # 这里不要直接复用执行期的 build_run_action_from_command(...)。
    # 原因是：
    # - 执行期 parser 会拒绝占位符
    # - 而 preflight 恰恰需要检查“命令里是否还留着占位符”
    # 所以这里应该走一个更宽松的 preflight 专用 parser。
    action = build_preflight_action_from_command(
        command=command,
        cwd=cwd or repo_path,
        source=source,
        reason=reason,
        timeout_seconds=300,
    )
    action_hash = compute_action_hash(action)

    state = {
        "repo_path": repo_path,
        "pending_action": action,
        "pending_action_hash": action_hash,
        "requires_approval": False,
        "user_approval": "not_required",
        "output_files": [],
    }

    result = preflight_check_node(state)
    print("[green]preflight finished[/green]")
    print(result.get("preflight_report"))
    print(result.get("output_files", []))
```

### 为什么这个命令很值得加

因为你后面调 preflight 时，经常只想回答一个问题：

```text
这条命令为什么被挡住了？
```

这时候单独跑 `run_preflight` 会比整图调试高效很多。

### 很重要：如果你这里还在直接调用 `build_run_action_from_command(...)`

那你后面拿这条命令去测：

```bash
python -m app.main run-preflight \
  /data/tianshaoqi24/P4Transformer/ \
  "python train-ntu60.py --dataset_path <path_to_ntu60>"
```

很可能会在进入 preflight 之前就直接报：

```text
ValueError: unsupported shell syntax in run command; please convert it into a single executable command
```

这说明：

```text
你的 preflight CLI 还在用执行期 parser
而不是 preflight 专用 parser
```

只有切换到 `build_preflight_action_from_command(...)` 之后，这条命令才会变成你真正想要的语义：

- 不报异常
- 生成 preflight 报告
- 明确指出 placeholder 未替换
- `ready_to_execute = false`

---

## 九、补测试：建议至少覆盖 4 个场景

建议新增：

```text
tests/test_preflight_check_node.py
```

### 这一阶段最值得测的 4 类场景

1. 正常命令能通过 preflight
2. 命令里有占位符时会被挡住
3. 路径不存在时会被挡住
4. 无需审批时，preflight 会自动补 `user_approval="not_required"`

### 建议代码

```python
import json
from pathlib import Path

from app.config import settings
from app.nodes.preflight_check_node import preflight_check_node


def test_preflight_blocks_when_dataset_path_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "train.py").write_text("print('demo')\n", encoding="utf-8")
    (repo_dir / "requirements.txt").write_text("torch\n", encoding="utf-8")

    state = {
        "repo_path": str(repo_dir),
        "requires_approval": False,
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py", "--dataset_path", "/path/does/not/exist"],
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

    result = preflight_check_node(state)

    assert result["preflight_passed"] is False
    assert result["final_status"] == "blocked"
    assert "preflight_report" in result
    assert "dataset_path" in json.dumps(result["preflight_report"], ensure_ascii=False)


def test_preflight_blocks_when_placeholders_remain(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "train.py").write_text("print('demo')\n", encoding="utf-8")

    state = {
        "repo_path": str(repo_dir),
        "requires_approval": False,
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py", "--dataset_path", "<path_to_dataset>"],
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

    result = preflight_check_node(state)

    assert result["preflight_passed"] is False
    assert result["final_status"] == "blocked"
    assert "placeholder" in json.dumps(result["preflight_report"], ensure_ascii=False).lower()


def test_preflight_passes_for_minimal_local_python_action(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "train.py").write_text("print('demo')\n", encoding="utf-8")
    (repo_dir / "requirements.txt").write_text("torch\n", encoding="utf-8")

    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()

    state = {
        "repo_path": str(repo_dir),
        "requires_approval": False,
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py", "--dataset_path", str(dataset_dir)],
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

    result = preflight_check_node(state)

    assert "preflight_report" in result
    assert "preflight_passed" in result
    assert result["user_approval"] == "not_required"

    # 这里不强行断言一定 passed，
    # 因为不同机器上 python / torch / cuda 环境可能不同。
    # 但至少应该产出报告文件。
    assert Path(result["preflight_report_path"]).exists()
    assert any(path.endswith("preflight_report.md") for path in result["output_files"])


def test_preflight_sets_not_required_when_approval_not_needed(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "train.py").write_text("print('demo')\n", encoding="utf-8")

    state = {
        "repo_path": str(repo_dir),
        "requires_approval": False,
        "pending_action": {
            "action_id": "action_demo",
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py"],
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

    result = preflight_check_node(state)

    assert result["user_approval"] == "not_required"
```

### 关于“环境相关测试不稳定”的提醒

你会注意到上面第 3 个测试没有强行断言：

```python
assert result["preflight_passed"] is True
```

这是故意的。

因为不同机器上：

- 有没有 `python`
- 有没有 `torch`
- CUDA 能不能用

可能不一样。

所以这里更合理的测试策略是：

- 对 deterministic 的静态项做强断言
- 对 runtime probe 只断言“能产出报告”

如果你后面想把运行时 probe 测得更稳定，推荐再把 `_run_probe(...)` monkeypatch 掉。

---

## 十、建议的手工验证顺序

这一章我非常推荐你用“先单点，再整链”的方式验证。

### 1. 先跑单测

```bash
python -m pytest tests/test_preflight_check_node.py
```

### 2. 先单独跑 `run_preflight`

这是最省心的调法。

例如故意传一个不存在的数据路径：

```bash
python -m app.main run-preflight \
  /data/tianshaoqi24/P4Transformer/ \
  "python train-ntu60.py --dataset_path /path/does/not/exist"
```

理想结果：

- 生成：
  - `outputs/preflight_report.json`
  - `outputs/preflight_report.md`
- `preflight_passed=False`
- `final_status=blocked`

### 3. 再测占位符阻断

```bash
python -m app.main run-preflight \
  /data/tianshaoqi24/P4Transformer/ \
  "python train-ntu60.py --dataset_path <path_to_ntu60>"
```

理想结果：

- 不抛 `unsupported shell syntax` 异常
- 不进入 executor
- preflight 报告中明确指出 placeholder 未替换
- `preflight_passed=False`

如果你这里仍然报：

```text
ValueError: unsupported shell syntax in run command
```

说明你还没有把 `run_preflight()` 切换到：

```python
build_preflight_action_from_command(...)
```

而是仍然在调用执行期的：

```python
build_run_action_from_command(...)
```

### 4. 再测完整 graph

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer/ \
  --thread-id preflight-001
```

如果中间停在：

- `command_selection_node`
- `human_review_node`

就按你前面已经实现好的方式继续 resume。

### 5. 看最终是不是被 preflight 挡住

执行：

```bash
python -m app.main show-state --thread-id preflight-001
```

重点看：

- `preflight_report`
- `preflight_passed`
- `final_status`
- `preflight_report_path`

如果命令里的数据路径或脚本路径有问题，理想状态应该是：

```text
preflight_passed = False
final_status = blocked
```

而不是：

```text
直接进入 executor 然后才失败
```

### 6. 看 run manifest 有没有把 preflight 产物归档进去

如果你已经接好了 Phase 19 的 run manifest，那么再看：

```bash
python -m app.main show-run <run_id>
```

或者直接打开：

```text
runs/<run_id>/planning/preflight_report.json
runs/<run_id>/planning/preflight_report.md
```

---

## 十一、这一阶段的验收标准

你可以按下面这份清单来验收。

### 功能验收

- `pending_action` 在真正执行前会先进入 `preflight_check`
- preflight 能生成：
  - `outputs/preflight_report.json`
  - `outputs/preflight_report.md`
- 明显错误会被提前发现，例如：
  - `cwd` 不存在
  - 程序不在 PATH
  - 训练脚本不存在
  - 数据路径不存在
  - 配置路径不存在
  - 命令里还留着 `<path>` 占位符

### 路由验收

- `approved -> preflight_check -> executor`
- `not_required -> preflight_check -> executor`
- `rejected / revise -> final_report`
- `preflight_passed=False -> final_report`

### 产物验收

- `final_report.md` 最好能体现 preflight 摘要
- `run_manifest.json` 能通过 `output_files` 看到 preflight 产物
- `runs/<run_id>/` 中能找到归档后的 preflight 报告

---

## 十二、这一阶段的价值到底是什么

这个阶段看起来不像“human review”或者“executor”那么显眼，但它的工程价值非常高。

它解决的是一个很现实的问题：

```text
系统会执行
不代表系统值得执行
```

有了 preflight 之后，你的 agent 就不再是“拿到命令就跑”，而是开始具备：

- 执行前环境认知
- 执行前条件校验
- 执行前阻断能力

这一步非常像真实生产系统里的：

```text
readiness check
```

做完后，系统整体会更像一个“负责任的执行代理”，而不是“盲跑脚本的自动机”。

---

## 十三、下一步最值得做什么

Preflight 做完以后，先不要立刻增加 Smoke Test。

当前 executor 和 runtime probe 仍然默认使用 Agent 自己的 Python / PATH。为了避免 Smoke Test 也运行在错误环境中，下一步应先完成：

```text
Phase 21：Execution Backend 与环境隔离
```

也就是把 Agent 控制面和论文执行面拆开：

1. 用 `ExecutionProfile` 描述论文仓库、Conda 环境和产物目录
2. 用统一 Runner 执行正式动作和 runtime probe
3. 确保 preflight 与 executor 使用同一个论文环境
4. 把执行环境指纹绑定到 action hash 和人工审批

这一层完成后，再进入：

```text
Phase 22：Smoke Test 与 Bounded Repair
```

为什么要这样调整顺序？

因为现在你已经有：

- action builder
- approval hash
- command selection
- preflight readiness
- executor
- log debug
- final report
- run manifest

但这些能力目前还缺少统一的“目标执行环境”抽象。正确顺序应该是：

```text
preflight
  -> execution profile / runner
  -> smoke test
  -> full executor
  -> bounded repair
```

这样 Smoke Test、Full Executor 和后续 Repair 才会在同一个论文环境中运行。

---

## 最后一句话总结这一阶段

这一阶段的本质不是“多写一个 `preflight_report.json`”，而是：

```text
把系统从“拿到命令就执行”
升级成“先判断是否具备基本执行条件，再决定要不要执行”
```

这一步做完后，你的闭环会更稳，调试成本会明显下降，后面继续做 smoke test 和 repair loop 也会顺很多。
