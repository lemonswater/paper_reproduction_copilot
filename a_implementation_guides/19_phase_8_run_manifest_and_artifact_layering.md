# 19. 闭环后第四阶段：Run Manifest 与 Artifact 分层

## 这一阶段的目标

到上一阶段为止，你已经补上了：

```text
Durable Checkpoint
Structured Action
Approval Hash
Command Selection
Editable Run Commands
```

这说明你的系统现在已经可以走完一条比较完整的执行链：

```text
experiment_plan
  -> command_selection
  -> action_builder
  -> risk_check
  -> human_review
  -> executor
  -> final_report
```

但是当前工程形态还有一个很明显的问题：

## 现在的痛点

### 问题 1：产物全都堆在 `outputs/`

你当前项目里已经会生成很多文件，比如：

- `paper_summary.json`
- `repo_map.json`
- `paper_code_mapping.json`
- `experiment_plan.json`
- `command_selection_record.json`
- `effective_run_commands.json`
- `execution.log`
- `debug_report.json`
- `final_report.md`

这些文件目前都平铺在：

```text
outputs/
```

这样在早期开发时没有问题，但只要你连续跑几次任务，很快就会遇到：

- 新一次运行覆盖上一次运行的同名文件
- 很难回答“这个 `final_report.md` 属于哪一次运行”
- 很难知道“这次审批通过的是哪一个 action hash”
- 很难把一次完整运行的分析、规划、执行、调试产物放在一起复盘

### 问题 2：Checkpoint 和 Artifact 还没有真正分层

你在前面已经把 checkpoint 放进了：

```text
checkpoints/langgraph.sqlite
```

这很好，但一个可持续扩展的 agent 工程，通常要明确区分三层：

```text
Checkpoint：
    保存 graph 的可恢复状态与中断点

Artifact：
    保存实际生成的文件产物

Manifest：
    保存“一次运行”的血缘信息、输入、选择、审批、执行结果
```

如果这三层没有拆开，后面你继续做：

- preflight
- verification
- repair loop
- evaluation
- 多次运行对比

都会越来越难管理。

---

## 这一阶段到底要做什么

这一阶段的目标非常明确：

1. 给每次 graph 运行分配一个唯一的 `run_id`
2. 为每次运行创建独立目录：`runs/<run_id>/`
3. 在 graph 结束时，把本次 `output_files` 对应的产物归档进去
4. 生成两个索引文件：
   - `artifact_index.json`
   - `run_manifest.json`
5. 让你后面能够回答：
   - 这次运行输入了什么
   - 选了哪条命令
   - 有没有修改命令
   - 审批通过的是哪个动作
   - 最终执行结果是什么
   - 本次运行一共产生了哪些文件

这一阶段做完之后，系统会从：

```text
能跑出很多文件
```

升级成：

```text
每次运行都有独立目录、独立清单、独立可追溯记录
```

---

## 先说明白：这一阶段不建议你立刻重写所有节点的落盘逻辑

如果追求“最理想结构”，你当然可以直接把所有节点都改成写到：

```text
runs/<run_id>/analysis/
runs/<run_id>/planning/
runs/<run_id>/execution/
runs/<run_id>/debug/
runs/<run_id>/reports/
```

但我不建议你现在就这么做。

### 原因

因为你当前仓库里已经有很多节点默认写到：

```text
settings.output_dir
```

例如：

- `paper_reader_node`
- `method_extractor_node`
- `repo_scan_node`
- `mapping_node`
- `experiment_plan_node`
- `command_selection_node`
- `executor_node`
- `log_debug_node`
- `final_report_node`

如果你这一阶段一次性把所有节点都改成 run-aware，工作量会突然变大，而且排错范围也会扩大。

### 这一阶段更稳的做法

本阶段建议采用一个“低侵入版本”：

```text
第一步：
    继续允许前面所有节点先把文件写到 outputs/

第二步：
    在 graph 开头创建 run context

第三步：
    在 graph 结尾增加 run_manifest_node
    把本次 output_files 对应的文件复制/归档到 runs/<run_id>/
    再生成 manifest 与 artifact index
```

这样做的好处是：

- 不需要重写前面所有节点
- 能快速建立 per-run artifact 目录
- 已经足够支撑后面的 verification 和 eval
- 后续你还可以再做“原生写入 run_dir”的升级版

一句话概括：

```text
Phase 19 先做“归档层”
而不是立刻做“所有节点原生写入 run_dir”
```

---

## 本阶段建议修改 / 新增的文件

```text
app/config.py
app/state.py
app/tools/artifact_tools.py
app/nodes/run_context_node.py
app/nodes/run_manifest_node.py
app/graph.py
app/main.py
tests/test_run_manifest_node.py
```

可选补充：

```text
.gitignore
```

如果你把 `runs/` 视为运行时产物目录，而不是准备提交的样例数据，建议忽略它。

---

## 开始前的两个前置检查

### 前置检查 1：先修正 Phase 18 残留字段名

根据你当前仓库状态，[app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1) 里现在还是：

```python
edited_run_command: list[dict[str, Any]]
selected_run_commnd_index: Optional[int]
```

这两个名字都不太对：

- `edited_run_command`
  - 应该是复数：`edited_run_commands`
- `selected_run_commnd_index`
  - `command` 少了一个 `a`

如果这一步不先统一，后面生成 manifest 时就会出现：

```text
state 里明明有值
但是 manifest 读不到
```

所以这一章后面的代码都统一假设你已经改成：

```python
edited_run_commands
selected_run_command_index
```

### 前置检查 2：确认 `risk_check -> executor` 的低风险分支是通的

你当前 [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1) 里还有一个值得顺手检查的点：

```python
def route_after_risk_check(state: ReproductionState) -> str:
    if state.get("requires_approval"):
        return "human_review"
    return "final_report"
```

如果这里保持 `no approval -> final_report`，那低风险动作就根本不会执行。

对一个闭环 agent 来说，更合理的是：

```python
def route_after_risk_check(state: ReproductionState) -> str:
    if state.get("requires_approval"):
        return "human_review"
    return "executor"
```

这不是 Phase 19 的核心内容，但建议你在进入本阶段前先确认这条链是正确的，否则你得到的 manifest 也只会记录“分析结束”，而不是“动作执行闭环”。

### 这一步为什么要先做

因为 Phase 19 要记录的是：

- 这次运行最后选了什么命令
- 命令有没有执行
- 执行结果是什么
- 执行日志在哪

如果你的 graph 还停留在：

```text
risk_check
  -> human_review
  -> executor
```

而不存在：

```text
risk_check
  -> executor
```

这条“无需审批直达执行”的分支，那么后面生成的 manifest 就会天然丢掉一类非常重要的运行场景：

```text
低风险动作本来应该自动执行
但实际上被 graph 提前结束了
```

所以这一步虽然不是 run manifest 本身的代码，但它直接决定了：

```text
你记录到的闭环，是真闭环，还是半闭环
```

### 先看清楚：你当前代码里为什么这条分支不通

按你当前仓库的实现，这个问题其实不是单点 bug，而是 4 个位置一起造成的。

#### 问题 1：风险评估层几乎不给 `low`

你当前 [app/tools/safe_shell_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/safe_shell_tools.py:1) 的 `assess_action_risk()` 逻辑基本是：

- `blocked`
- `high`
- `medium`

几乎没有真正的：

```text
low risk
```

这意味着“低风险无需审批”这条分支连入口都没有。

#### 问题 2：`risk_check_node` 把“未阻止”全都当成“要审批”

你当前 [app/nodes/risk_check_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/risk_check_node.py:1) 里核心逻辑是：

```python
"requires_approval": not risk.blocked
```

这会把两类本来应该分开的情况混在一起：

- `low risk`
  - 应该自动执行
- `medium/high risk`
  - 应该人工审批

现在它们都会变成：

```text
requires_approval = True
```

#### 问题 3：graph 路由没有第三条分支

你当前 [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1) 里的 `route_after_risk_check()` 只有两条路：

- `requires_approval=True -> human_review`
- `requires_approval=False -> final_report`

也就是说，即使未来你让某些动作成为“无需审批”，它现在也不会进入 `executor`，而是直接结束。

#### 问题 4：executor 虽然支持 `not_required`，但前面没人把这个状态送进来

你当前 [app/nodes/executor_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/executor_node.py:1) 其实已经接受：

```python
decision in {"approved", "not_required"}
```

这说明 executor 这一层已经基本准备好了。

真正缺的是前面的 `risk_check_node` 还没有在“低风险无需审批”时把：

```python
"user_approval": "not_required"
```

写进 state。

---

### 推荐的最小实现思路

这一步最稳妥的方式，不是一下子重构整条执行链，而是先把状态分成 3 类：

```text
blocked
  -> 不执行，直接结束

low risk
  -> 不审批，直接执行

medium/high risk
  -> 先审批，再执行
```

也就是让 `risk_check` 之后真正出现三条语义上不同的路：

```text
blocked
  -> final_report

requires approval
  -> human_review

not_required
  -> executor
```

下面按文件给你写最小改法。

---

### 修改 1：让 `safe_shell_tools.py` 真的能返回 `low`

当前的风险评估基本没有“低风险白名单”。建议你先加一组非常保守的只读命令，例如：

- `echo`
- `pwd`
- `ls`
- `which`
- `python --version`

注意，不要把下面这些放进 `low`：

- `python train.py`
- `python -m ...`
- `pip install ...`
- `conda install ...`
- `bash script.sh`

因为它们仍然可能改环境、写文件或者启动长时间任务。

#### 建议代码

下面这段代码是基于你当前 [app/tools/safe_shell_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/safe_shell_tools.py:1) 的“最小升级版”。

```python
import shlex
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

# 只放非常保守的“只读命令”。
LOW_RISK_PROGRAMS = {
    "echo",
    "pwd",
    "ls",
    "which",
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
    评估结构化动作的执行风险。

    当前项目里 action 已经不是字符串命令了，
    而是 ExecutableAction model_dump() 之后的 dict，
    所以这里要从 program / args 读信息。
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

    # 先处理一个很常见的安全查询命令：
    # python --version / python -V
    if program == "python" and args in (["--version"], ["-V"]):
        return ActionRisk(
            program=program,
            args=args,
            risk_level="low",
            reason="version check is read-only and safe to run automatically",
            blocked=False,
        )

    if program in LOW_RISK_PROGRAMS:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="low",
            reason="read-only utility command can run without manual approval",
            blocked=False,
        )

    if program in {"pip", "conda"} and "install" in args:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="high",
            reason="environment-changing command requires approval",
            blocked=False,
        )

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

#### 这一改之后你应该得到什么

改完后，至少下面这些动作应该能产生：

```text
echo hello -> low
pwd -> low
ls -> low
python --version -> low
python train.py -> medium
pip install torch -> high
rm -rf outputs -> blocked
```

---

### 修改 2：让 `risk_check_node` 明确区分 blocked / low / review-needed

当前 [app/nodes/risk_check_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/risk_check_node.py:1) 的问题在于：

```python
requires_approval = not risk.blocked
```

这会把：

- `low`
- `medium`
- `high`

都压成同一类。

更合理的做法是：

#### 目标状态

```text
blocked
  -> requires_approval=False
  -> final_status="blocked"

low
  -> requires_approval=False
  -> user_approval="not_required"

medium/high
  -> requires_approval=True
```

#### 建议代码

```python
from app.tools.safe_shell_tools import assess_action_risk


def risk_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {
            "requires_approval": False,
            "pending_action": None,
        }

    action_type = pending_action.get("action_type")

    if action_type == "run_command":
        risk = assess_action_risk(pending_action)
        pending_action["risk"] = {
            "level": risk.risk_level,
            "reason": risk.reason,
            "blocked": risk.blocked,
        }

        # 1. 明确阻止执行。
        if risk.blocked:
            return {
                "pending_action": pending_action,
                "pending_action_hash": state.get("pending_action_hash"),
                "requires_approval": False,
                "final_status": "blocked",
                "error": risk.reason,
            }

        # 2. 低风险动作直接放行，不进入 human review。
        if risk.risk_level == "low":
            return {
                "pending_action": pending_action,
                "pending_action_hash": state.get("pending_action_hash"),
                "requires_approval": False,
                "user_approval": "not_required",
                "error": None,
            }

        # 3. 其余 medium / high 仍然走审批。
        return {
            "pending_action": pending_action,
            "pending_action_hash": state.get("pending_action_hash"),
            "requires_approval": True,
            "error": None,
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

#### 这一步最关键的点

最关键的不是 `requires_approval=False` 本身，而是你要让 graph 能区分：

- `blocked`
- `not_required`

否则这两种情况都会被当成同一类“无需审批”，路由时还是会混掉。

这里我给你的最小做法是：

```python
"final_status": "blocked"
```

把“被阻止”单独标出来。

---

### 修改 3：让 `graph.py` 真正出现第三条路由

当前 [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1) 只有两条路：

```text
需要审批 -> human_review
不需要审批 -> final_report
```

你要把它改成三条：

```text
blocked -> final_report
需要审批 -> human_review
无需审批 -> executor
```

#### 建议代码

```python
def route_after_risk_check(state: ReproductionState) -> str:
    # 如果已经被风险层明确阻止，就不要继续走 executor。
    if state.get("final_status") == "blocked":
        return "final_report"

    # 需要审批的动作进入 human review。
    if state.get("requires_approval"):
        return "human_review"

    # 否则就是低风险自动放行，直接去 executor。
    return "executor"
```

#### 为什么不能只判断 `requires_approval`

因为改完 `risk_check_node` 之后，这两类状态都会是：

```python
requires_approval = False
```

第一类：

```text
blocked
```

第二类：

```text
not_required
```

如果 graph 不额外判断 `final_status == "blocked"`，就会把“明明被禁止执行”的动作也错误送进 `executor`。

---

### 修改 4：确认 `executor_node` 能接住 `not_required`

这一步你当前代码其实已经差不多具备了。

因为 [app/nodes/executor_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/executor_node.py:1) 里已经写了：

```python
if decision not in {"approved", "not_required"}:
    ...
```

所以这里通常不需要大改。

你只需要确认：

- `risk_check_node` 在低风险情况下真的会写入：
  - `"user_approval": "not_required"`
- graph 真的会把这类状态送进 `executor`

就够了。

如果你想再做一层防御式兼容，也可以把 executor 写得更稳一点，例如：

```python
if not decision and state.get("requires_approval") is False:
    decision = "not_required"
```

不过这属于“兜底增强”，不是最小改法必须做的部分。

---

### 建议补哪些测试

这里我建议你不要只做手工测试，最好把这一块补成单测，因为这条逻辑以后很容易回归。

另外要特别注意一件事：

你当前有些旧测试可能还是基于早期字符串命令接口，比如：

```python
{"type": "run_command", "command": "python train.py"}
```

但你现在项目里 `pending_action` 已经是结构化动作，更接近：

```python
{
    "action_type": "run_command",
    "program": "python",
    "args": ["train.py"],
    "cwd": ".",
}
```

所以这一步建议你直接新写一组面向“结构化动作”的测试，不要完全依赖旧版测试。

#### 测试 1：风险评估能产出 `low`

可以新建到 `tests/test_low_risk_route.py`，也可以并入已有测试文件。

```python
from app.tools.safe_shell_tools import assess_action_risk


def test_assess_action_risk_returns_low_for_echo() -> None:
    action = {
        "action_type": "run_command",
        "program": "echo",
        "args": ["hello"],
        "cwd": ".",
    }

    risk = assess_action_risk(action)

    assert risk.risk_level == "low"
    assert risk.blocked is False


def test_assess_action_risk_returns_medium_for_python_script() -> None:
    action = {
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": ".",
    }

    risk = assess_action_risk(action)

    assert risk.risk_level == "medium"
    assert risk.blocked is False


def test_assess_action_risk_returns_blocked_for_rm() -> None:
    action = {
        "action_type": "run_command",
        "program": "rm",
        "args": ["-rf", "outputs"],
        "cwd": ".",
    }

    risk = assess_action_risk(action)

    assert risk.risk_level == "blocked"
    assert risk.blocked is True
```

#### 测试 2：`risk_check_node` 对低风险动作直接放行

```python
from app.nodes.risk_check_node import risk_check_node


def test_risk_check_node_skips_review_for_low_risk_action() -> None:
    state = {
        "pending_action": {
            "action_type": "run_command",
            "program": "echo",
            "args": ["hello"],
            "cwd": ".",
        },
        "pending_action_hash": "demo-hash",
    }

    result = risk_check_node(state)

    assert result["requires_approval"] is False
    assert result["user_approval"] == "not_required"
    assert result["pending_action"]["risk"]["level"] == "low"
    assert result.get("final_status") is None
```

#### 测试 3：`risk_check_node` 对 blocked 动作直接阻止

```python
from app.nodes.risk_check_node import risk_check_node


def test_risk_check_node_marks_blocked_action() -> None:
    state = {
        "pending_action": {
            "action_type": "run_command",
            "program": "rm",
            "args": ["-rf", "outputs"],
            "cwd": ".",
        },
        "pending_action_hash": "demo-hash",
    }

    result = risk_check_node(state)

    assert result["requires_approval"] is False
    assert result["final_status"] == "blocked"
    assert result["error"]
    assert result["pending_action"]["risk"]["level"] == "blocked"
```

#### 测试 4：graph 路由在低风险时走 `executor`

```python
from app.graph import route_after_risk_check


def test_route_after_risk_check_goes_to_executor_when_not_required() -> None:
    state = {
        "requires_approval": False,
        "user_approval": "not_required",
    }

    assert route_after_risk_check(state) == "executor"


def test_route_after_risk_check_goes_to_final_report_when_blocked() -> None:
    state = {
        "requires_approval": False,
        "final_status": "blocked",
    }

    assert route_after_risk_check(state) == "final_report"
```

#### 测试 5：executor 在 `not_required` 时真的会执行

这里最好 mock 掉真实执行，避免测试过程中真的去跑命令。

```python
from unittest.mock import patch

from app.config import settings
from app.nodes.executor_node import executor_node


def test_executor_runs_when_user_approval_is_not_required(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

    state = {
        "pending_action": {
            "action_type": "run_command",
            "program": "echo",
            "args": ["hello"],
            "cwd": ".",
        },
        "user_approval": "not_required",
        "output_files": [],
    }

    fake_result = {
        "ok": True,
        "returncode": 0,
        "stdout": "hello\n",
        "stderr": "",
        "combined_output": "hello\n",
    }

    with patch("app.nodes.executor_node.run_action_safe", return_value=fake_result):
        result = executor_node(state)

    assert result["final_status"] == "succeeded"
    assert result["execution_result"]["ok"] is True
    assert result["execution_log_path"]
```

---

### 推荐的测试顺序

为了减少排错范围，建议你按下面顺序测。

#### 第 1 步：先测纯函数风险评估

先确认 `assess_action_risk()` 本身已经能区分：

- `low`
- `medium`
- `high`
- `blocked`

运行命令：

```bash
python -m pytest tests/test_low_risk_route.py -q
```

如果你把这些测试并到了已有文件里，就按实际文件名跑。

#### 第 2 步：再测 `risk_check_node`

确认它能产出：

- `user_approval="not_required"`
- `final_status="blocked"`

这一步测的是“risk 结果有没有被正确翻译成 graph state”。

#### 第 3 步：再测 `route_after_risk_check`

这一步非常关键，因为很多时候函数本身都对，但 graph 路由还是写错。

你要确认：

```text
blocked -> final_report
not_required -> executor
requires_approval -> human_review
```

#### 第 4 步：最后测 `executor_node`

确认它在：

```python
user_approval == "not_required"
```

时不会误判成：

```text
not_executed
```

---

### 一套最小的手工验证方式

如果你在单测通过后，还想做一次最小手工验证，可以直接在终端临时跑这段代码：

```bash
python - <<'PY'
from app.nodes.risk_check_node import risk_check_node
from app.graph import route_after_risk_check

state = {
    "pending_action": {
        "action_type": "run_command",
        "program": "echo",
        "args": ["hello"],
        "cwd": ".",
    }
}

state.update(risk_check_node(state))
print("after risk_check:", state)
print("next node:", route_after_risk_check(state))
PY
```

理想情况下你应该看到类似：

```text
after risk_check: {
  ...,
  'requires_approval': False,
  'user_approval': 'not_required',
  'pending_action': {
    ...,
    'risk': {
      'level': 'low',
      ...
    }
  }
}
next node: executor
```

如果你看到的是：

```text
requires_approval: True
```

说明问题还停留在风险评估层或 `risk_check_node`。

如果你看到的是：

```text
next node: final_report
```

说明问题还停留在 `route_after_risk_check()`。

---

### 这一块做完后的目标状态

你可以把最终理想链路记成下面这张小图：

```text
low risk
  -> risk_check
  -> executor

medium/high risk
  -> risk_check
  -> human_review
  -> executor

blocked
  -> risk_check
  -> final_report
```

只要这条链真的成立，后面你做 Phase 19 的 run manifest 时，记录到的“执行路径”才是完整可信的。

---

## 一、先补配置：增加 `runs_dir`

当前 [app/config.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/config.py:1) 已经有：

- `output_dir`
- `checkpoint_db_path`

现在还缺：

- `runs_dir`

### 为什么需要单独的 `runs_dir`

因为这两层职责不同：

- `outputs/`
  - 更像“当前调试产物”
- `runs/`
  - 更像“按运行实例归档的长期产物”

### 建议修改后的代码

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

    # 继续保留 outputs/，让已有节点不用立刻全部重写。
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))

    # 新增 runs/，作为“每次运行的独立归档目录”。
    runs_dir: Path = Path(os.getenv("RUNS_DIR", "runs"))

    # Durable checkpoint 继续走 sqlite。
    checkpoint_db_path: Path = Path(
        os.getenv("CHECKPOINT_DB_PATH", "checkpoints/langgraph.sqlite")
    )

    max_steps: int = int(os.getenv("MAX_STEPS", "20"))


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.runs_dir.mkdir(parents=True, exist_ok=True)
settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
```

### 这一改的作用

改完后，你的工程目录就明确多出一层：

```text
outputs/   -> 当前通用输出
runs/      -> 每次运行归档
```

---

## 二、扩展 State：把 run 级元数据纳入状态

这一阶段的核心不是“再加一个输出文件”，而是引入“运行实例”这个概念。

所以你需要让 state 里能携带：

- `run_id`
- `run_dir`
- `run_started_at`
- `artifact_records`
- `artifact_index_path`
- `run_manifest_path`

### 建议修改后的代码

下面给出一个可直接参考的 [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1) 版本：

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

    # Phase 18：命令选择与修改后的结果。
    edited_run_commands: list[dict[str, Any]]
    selected_run_command_index: Optional[int]
    command_selection_record: Optional[dict[str, Any]]

    # Phase 17：结构化动作与审批链。
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

    # 通用输出文件列表。前面所有节点仍然往这里追加。
    output_files: list[str]
    final_report: Optional[str]
    messages: list[dict[str, Any]]
    step_count: int
    max_steps: int
    error: Optional[str]
    code_search_results: dict[str, Any]

    # Phase 19：运行级上下文。
    run_id: Optional[str]
    run_dir: Optional[str]
    run_started_at: Optional[str]

    # Phase 19：最终归档与索引信息。
    artifact_records: list[dict[str, Any]]
    artifact_index_path: Optional[str]
    run_manifest_path: Optional[str]
```

### 为什么这些字段放在 state 里

因为 checkpoint 恢复时，最重要的是“恢复同一条运行上下文”，而不是重新生成一个新 run。

如果这些字段不放进 state，而只是临时局部变量，就会出现：

```text
第一次 run_graph 创建的是 run_A
中断后 resume 时又创建了 run_B
```

这就违背了“同一条任务恢复时，应该继续写回同一条运行记录”的目标。

---

## 三、新增工具层：`artifact_tools.py`

这一层的作用是把“run 目录创建、artifact 分类、文件归档、manifest 组装”从节点逻辑里拆出来。

建议新增文件：

```text
app/tools/artifact_tools.py
```

### 建议代码

```python
import hashlib
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from app.config import settings


def _slugify(value: str) -> str:
    """
    把 task_id 这类字符串转成适合作为目录名的安全前缀。
    例如：
        "paper-001" -> "paper-001"
        "My Task / Demo" -> "my-task-demo"
    """
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "run"


def build_run_id(task_id: str | None) -> str:
    """
    生成 run_id。

    这里不直接只用 task_id，原因是：
    - 同一个 thread_id 未来可能会多次重新发起 run
    - 只用 task_id 会碰撞

    所以这里采用：
        {task_id前缀}-{UTC时间戳}-{短uuid}
    """
    prefix = _slugify(task_id or "run")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}-{timestamp}-{suffix}"


def create_run_layout(run_id: str) -> dict[str, str]:
    """
    创建一次运行对应的目录结构。

    这里采用一个比较轻量但足够实用的分层：
        analysis/
        planning/
        execution/
        debug/
        reports/
    """
    run_root = settings.runs_dir / run_id
    layout = {
        "run_root": str(run_root),
        "analysis_dir": str(run_root / "analysis"),
        "planning_dir": str(run_root / "planning"),
        "execution_dir": str(run_root / "execution"),
        "debug_dir": str(run_root / "debug"),
        "reports_dir": str(run_root / "reports"),
    }

    for path in layout.values():
        Path(path).mkdir(parents=True, exist_ok=True)

    return layout


def sha256_file(path: Path) -> str | None:
    """
    为归档后的文件计算 sha256。
    这样后续你做“产物是否变化”的对比会方便很多。
    """
    if not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def try_get_git_commit(repo_path: str | None) -> str | None:
    """
    尝试记录仓库当前 commit。

    这里不强依赖 repo_path 一定是 git 仓库。
    如果拿不到 commit，就返回 None，不要让整个流程失败。
    """
    if not repo_path:
        return None

    repo_dir = Path(repo_path)
    if not repo_dir.exists():
        return None

    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    commit = result.stdout.strip()
    return commit or None


def classify_output_file(path: str) -> str:
    """
    根据输出文件名，把 artifact 归到一个大类里。

    这是“约定优于配置”的第一版实现。
    当前项目里文件命名已经比较固定，所以这样足够用了。
    """
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
    }:
        return "planning"

    if name in {"execution.log"}:
        return "execution"

    if name in {"debug_report.json", "debug_report.md"}:
        return "debug"

    if name in {"final_report.md", "eval_report.json", "eval_report.md"}:
        return "reports"

    # 未识别文件先保守地归到 reports，
    # 这样至少不会丢。
    return "reports"


def snapshot_output_files(output_files: list[str], run_root: str) -> list[dict[str, Any]]:
    """
    把本次 state.output_files 中记录到的文件复制到 runs/<run_id>/ 下。

    设计原则：
    1. 只复制当前 output_files 里出现的文件
    2. 文件不存在时不要抛异常中断整个 graph，而是记录 status=missing
    3. 去重，避免重复写入相同路径
    4. 不去复制 run_dir 内部文件，避免自我递归归档
    """
    run_root_path = Path(run_root).resolve()
    seen: set[str] = set()
    records: list[dict[str, Any]] = []

    for index, raw_path in enumerate(output_files):
        if raw_path in seen:
            continue
        seen.add(raw_path)

        artifact_type = classify_output_file(raw_path)
        source_path = Path(raw_path)

        if source_path.exists():
            resolved_source = source_path.resolve()
            if resolved_source == run_root_path or run_root_path in resolved_source.parents:
                records.append(
                    {
                        "source_path": str(source_path),
                        "artifact_type": artifact_type,
                        "status": "skipped_internal",
                        "dest_path": None,
                        "sha256": None,
                    }
                )
                continue

        if not source_path.exists():
            records.append(
                {
                    "source_path": str(source_path),
                    "artifact_type": artifact_type,
                    "status": "missing",
                    "dest_path": None,
                    "sha256": None,
                }
            )
            continue

        target_dir = run_root_path / artifact_type
        target_dir.mkdir(parents=True, exist_ok=True)

        dest_path = target_dir / source_path.name
        if dest_path.exists():
            # 如果未来出现同名文件，简单加前缀避免覆盖。
            dest_path = target_dir / f"{index:02d}_{source_path.name}"

        shutil.copy2(source_path, dest_path)

        records.append(
            {
                "source_path": str(source_path),
                "artifact_type": artifact_type,
                "status": "copied",
                "dest_path": str(dest_path),
                "sha256": sha256_file(dest_path),
            }
        )

    return records


def build_run_manifest(state: dict[str, Any], artifact_records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    组装一份“这次运行到底发生了什么”的总清单。

    这个 manifest 未来会非常重要：
    - 做审计
    - 做复盘
    - 做对比
    - 做 evaluation 汇总
    """
    selected_index = state.get("selected_run_command_index")
    effective_commands = state.get("edited_run_commands") or state.get("run_commands") or []

    selected_command = None
    if isinstance(selected_index, int) and 0 <= selected_index < len(effective_commands):
        selected_command = effective_commands[selected_index]

    copied_count = sum(1 for item in artifact_records if item.get("status") == "copied")
    missing_count = sum(1 for item in artifact_records if item.get("status") == "missing")

    return {
        "run_id": state.get("run_id"),
        "task_id": state.get("task_id"),
        "run_dir": state.get("run_dir"),
        "run_started_at": state.get("run_started_at"),
        "manifest_generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_path": state.get("paper_path"),
        "repo_path": state.get("repo_path"),
        "repo_git_commit": try_get_git_commit(state.get("repo_path")),
        "experiment_goal": state.get("experiment_goal"),
        "final_status": state.get("final_status"),
        "selected_run_command_index": selected_index,
        "selected_run_command": selected_command,
        "command_selection_record": state.get("command_selection_record"),
        "pending_action_hash": state.get("pending_action_hash"),
        "approval": {
            "decision": state.get("user_approval"),
            "feedback": state.get("human_feedback"),
            "record": state.get("approval_record"),
        },
        "execution": {
            "log_path": state.get("execution_log_path") or state.get("log_path"),
            "result": state.get("execution_result"),
        },
        "artifacts": {
            "count": len(artifact_records),
            "copied_count": copied_count,
            "missing_count": missing_count,
            "items": artifact_records,
        },
        "output_files": state.get("output_files", []),
    }
```

### 这层工具的核心思路

这层工具本质上做了 4 件事：

1. 生成 run id
2. 创建 per-run 目录结构
3. 把 `outputs/` 中的文件复制到 `runs/<run_id>/`
4. 组装一份结构化 `run_manifest.json`

这样节点层就不需要关心太多文件系统细节。

---

## 四、graph 开头加一个 `run_context_node`

这一节点只做一件事：

```text
如果这次运行还没有 run_id，就创建 run_id 和 run_dir
如果是中断恢复，就复用原来的 run_id
```

建议新增：

```text
app/nodes/run_context_node.py
```

### 建议代码

```python
from datetime import datetime, timezone

from app.tools.artifact_tools import build_run_id, create_run_layout


def run_context_node(state: dict) -> dict:
    """
    为一次 graph 运行补齐 run 级上下文。

    这个节点必须放在 graph 很靠前的位置，
    这样后面所有节点都能共享同一个 run_id。
    """
    existing_run_id = state.get("run_id")
    existing_run_dir = state.get("run_dir")
    existing_started_at = state.get("run_started_at")

    # 如果是从 checkpoint 恢复回来的，尽量复用原 run。
    if existing_run_id:
        layout = create_run_layout(existing_run_id)
        return {
            "run_id": existing_run_id,
            "run_dir": existing_run_dir or layout["run_root"],
            "run_started_at": existing_started_at
            or datetime.now(timezone.utc).isoformat(),
        }

    run_id = build_run_id(state.get("task_id"))
    layout = create_run_layout(run_id)

    return {
        "run_id": run_id,
        "run_dir": layout["run_root"],
        "run_started_at": datetime.now(timezone.utc).isoformat(),
    }
```

### 为什么这个节点要放在 graph 开头

因为你要保证：

```text
同一次 graph run 的所有后续节点
共享同一个 run_id
```

如果你把它放到很后面，就会出现：

- 前面已经产生了很多文件
- 但这些文件并不知道属于哪个 run

---

## 五、graph 结尾加一个 `run_manifest_node`

这一节点负责把“本次运行已经生成好的产物”正式归档，并写出 manifest。

建议新增：

```text
app/nodes/run_manifest_node.py
```

### 建议代码

```python
import json
from pathlib import Path

from app.tools.artifact_tools import (
    build_run_id,
    build_run_manifest,
    create_run_layout,
    snapshot_output_files,
)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    """
    output_files 是一个不断 append 的列表。
    这里做一个保序去重，避免 manifest 自己重复追加多次。
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def run_manifest_node(state: dict) -> dict:
    """
    把本次运行的 output_files 归档到 runs/<run_id>/，
    然后生成 artifact_index.json 和 run_manifest.json。
    """
    run_id = state.get("run_id") or build_run_id(state.get("task_id"))
    layout = create_run_layout(run_id)
    run_dir = Path(state.get("run_dir") or layout["run_root"])
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    original_output_files = state.get("output_files", [])
    artifact_records = snapshot_output_files(original_output_files, str(run_dir))

    artifact_index_path = reports_dir / "artifact_index.json"
    artifact_index_path.write_text(
        json.dumps(artifact_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = build_run_manifest(
        {
            **state,
            "run_id": run_id,
            "run_dir": str(run_dir),
        },
        artifact_records,
    )
    run_manifest_path = reports_dir / "run_manifest.json"
    run_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    updated_output_files = _dedupe_preserve_order(
        [
            *original_output_files,
            str(artifact_index_path),
            str(run_manifest_path),
        ]
    )

    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "artifact_records": artifact_records,
        "artifact_index_path": str(artifact_index_path),
        "run_manifest_path": str(run_manifest_path),
        "output_files": updated_output_files,
    }
```

### 为什么是“复制归档”而不是“移动文件”

因为当前阶段你仍然保留：

```text
outputs/ 作为开发调试目录
```

如果你直接移动文件，会影响你前面很多命令和调试习惯。

所以这一阶段更稳的策略是：

```text
原文件继续留在 outputs/
run_manifest_node 在结束时复制一份到 runs/<run_id>/
```

这就是“归档层”的含义。

---

## 六、把两个新节点接进 graph

现在要把：

- `run_context_node`
- `run_manifest_node`

接进 [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1)。

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
    if state.get("requires_approval"):
        return "human_review"
    return "executor"


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
    builder.add_edge("human_review", "executor")
    builder.add_conditional_edges("executor", route_after_executor)
    builder.add_edge("log_debug", "final_report")

    # 原来 final_report 直接结束。
    # 现在让它先进入归档节点，再统一结束。
    builder.add_edge("final_report", "run_manifest")
    builder.add_edge("run_manifest", END)

    return builder.compile(checkpointer=build_checkpointer())
```

### 这一改之后，graph 的关键变化

运行路径会从：

```text
START -> paper_reader -> ... -> final_report -> END
```

变成：

```text
START -> run_context -> paper_reader -> ... -> final_report -> run_manifest -> END
```

这很关键，因为它意味着：

```text
最终归档不再依赖 CLI 手工做
而是成为 graph 自身流程的一部分
```

---

## 七、更新 CLI：把 `task_id` 传进 graph，并补一个 `show_run`

这一阶段对 [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:1) 的改动主要有两个：

1. `run_graph()` 里把 `task_id=thread_id` 传入初始 state
2. 增加一个 `show_run()` 命令，方便你查看 manifest

顺手一提，你当前 `resume_command_selection()` 已经用了 `json.loads(...)`，但文件顶部还缺 `import json`，这一步也一起补掉。

### 建议代码

下面给出的是“这一阶段需要重点改的部分”，不是要求你和当前文件一字不差完全一致。

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
from app.nodes.repo_scan_node import repo_scan_node

app = typer.Typer(help="Paper Reproduction Copilot")


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
            # 这里很关键：
            # task_id 不一定非要和 thread_id 完全相同，
            # 但在当前项目里直接复用 thread_id 最简单也最稳定。
            "task_id": thread_id,
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
def show_state(
    thread_id: str = typer.Option("demo_thread", "--thread-id"),
):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    print(state)


@app.command()
def show_run(run_id: str):
    """
    直接查看某次运行的 run_manifest.json。
    """
    manifest_path = settings.runs_dir / run_id / "reports" / "run_manifest.json"
    if not manifest_path.exists():
        raise typer.BadParameter(f"run manifest not found: {manifest_path}")

    print(manifest_path.read_text(encoding="utf-8"))


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


@app.command()
def resume_command_selection(
    thread_id: str,
    selected_index: int | None = typer.Option(None, "--selected-index"),
    input: str | None = typer.Option(None, "--input"),
):
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
def reset_thread(thread_id: str):
    checkpointer = build_checkpointer()
    checkpointer.delete_thread(thread_id)
    print(f"[yellow]deleted checkpoints for thread_id={thread_id}[/yellow]")
```

### 为什么 `task_id` 这里直接用 `thread_id`

因为你当前项目已经把 checkpoint 的恢复主键建立在：

```text
thread_id
```

所以最简单、最稳妥的做法就是：

```text
同一条任务的 task_id 先直接复用 thread_id
```

后面如果你要支持：

- 一个 thread 下多次独立 run
- 或者一个 case_id 下多次实验

再把 `task_id` 拆得更细也不迟。

---

## 八、补测试：至少测 run context 和 manifest 归档

建议新增：

```text
tests/test_run_manifest_node.py
```

### 建议代码

```python
import json
from pathlib import Path

from app.config import settings
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node


def test_run_context_node_creates_run_id_and_run_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")

    result = run_context_node({"task_id": "paper-001"})

    assert result["run_id"].startswith("paper-001-")
    assert Path(result["run_dir"]).exists()
    assert (Path(result["run_dir"]) / "analysis").exists()
    assert (Path(result["run_dir"]) / "planning").exists()
    assert (Path(result["run_dir"]) / "execution").exists()
    assert (Path(result["run_dir"]) / "debug").exists()
    assert (Path(result["run_dir"]) / "reports").exists()
    assert result["run_started_at"]


def test_run_context_node_reuses_existing_run_on_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")

    existing_run_dir = tmp_path / "runs" / "demo-run"
    state = {
        "run_id": "demo-run",
        "run_dir": str(existing_run_dir),
        "run_started_at": "2026-07-16T00:00:00+00:00",
    }

    result = run_context_node(state)

    assert result["run_id"] == "demo-run"
    assert result["run_dir"] == str(existing_run_dir)
    assert result["run_started_at"] == "2026-07-16T00:00:00+00:00"
    assert existing_run_dir.exists()


def test_run_manifest_node_snapshots_outputs_and_writes_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")

    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    paper_summary_path = outputs_dir / "paper_summary.json"
    final_report_path = outputs_dir / "final_report.md"

    paper_summary_path.write_text('{"title": "demo"}', encoding="utf-8")
    final_report_path.write_text("# Final Report\n", encoding="utf-8")

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    state = {
        "task_id": "paper-001",
        "run_id": "paper-001-demo",
        "run_dir": str(tmp_path / "runs" / "paper-001-demo"),
        "run_started_at": "2026-07-16T00:00:00+00:00",
        "paper_path": "pdf/demo.pdf",
        "repo_path": str(repo_dir),
        "experiment_goal": "复现论文 main result",
        "final_status": "succeeded",
        "output_files": [
            str(paper_summary_path),
            str(final_report_path),
        ],
        "run_commands": [
            {
                "command": "python train.py --dataset_path /data/demo",
                "cwd": str(repo_dir),
                "source": "readme",
                "risk_level": "high",
                "reason": "demo command",
            }
        ],
        "selected_run_command_index": 0,
        "command_selection_record": {
            "selected_index": 0,
            "edits": [],
            "original_count": 1,
            "reviewed_at": "2026-07-16T00:00:00+00:00",
        },
        "pending_action_hash": "hash-demo",
        "user_approval": "approved",
        "human_feedback": "looks good",
        "approval_record": {
            "decision": "approved",
            "action_hash": "hash-demo",
        },
        "execution_result": {
            "ok": True,
            "returncode": 0,
        },
        "execution_log_path": str(outputs_dir / "execution.log"),
    }

    result = run_manifest_node(state)

    artifact_index_path = Path(result["artifact_index_path"])
    run_manifest_path = Path(result["run_manifest_path"])

    assert artifact_index_path.exists()
    assert run_manifest_path.exists()

    artifact_index = json.loads(artifact_index_path.read_text(encoding="utf-8"))
    manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))

    assert any(item["artifact_type"] == "analysis" for item in artifact_index)
    assert any(item["artifact_type"] == "reports" for item in artifact_index)

    assert manifest["run_id"] == "paper-001-demo"
    assert manifest["final_status"] == "succeeded"
    assert manifest["selected_run_command"]["command"] == "python train.py --dataset_path /data/demo"
    assert manifest["pending_action_hash"] == "hash-demo"

    analysis_copy = Path(state["run_dir"]) / "analysis" / "paper_summary.json"
    report_copy = Path(state["run_dir"]) / "reports" / "final_report.md"

    assert analysis_copy.exists()
    assert report_copy.exists()
```

### 这些测试分别在测什么

第 1 个测试：

- `run_context_node` 能创建 run id
- run 目录结构真的被创建出来了

第 2 个测试：

- 中断恢复时不会重新生成新的 run id

第 3 个测试：

- `run_manifest_node` 能把现有输出文件复制到 `runs/<run_id>/`
- 能生成 `artifact_index.json`
- 能生成 `run_manifest.json`
- manifest 里能正确记录选中的命令和 action hash

---

## 九、建议的手工验证顺序

### 1. 先跑单测

```bash
python -m pytest tests/test_run_manifest_node.py
```

如果你想顺手确保前面闭环没有被影响，也可以一起跑：

```bash
python -m pytest \
  tests/test_action_builder_node.py \
  tests/test_review_flow.py \
  tests/test_executor_node.py \
  tests/test_fail_to_debug_flow.py \
  tests/test_final_report_node.py \
  tests/test_run_manifest_node.py
```

### 2. 跑一次真实 graph

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer/ \
  --thread-id manifest-001
```

如果中间停在：

- `command_selection_node`
- `human_review_node`

就继续按你现在已有的方式 resume。

### 3. 查看 checkpoint state

注意：你当前 `show_state()` 最好按 option 形式调用：

```bash
python -m app.main show-state --thread-id manifest-001
```

重点看 state 里有没有：

- `run_id`
- `run_dir`
- `run_started_at`
- `run_manifest_path`

### 4. 直接查看某次运行的 manifest

先从 `show-state` 里拿到 `run_id`，然后执行：

```bash
python -m app.main show-run <run_id>
```

或者你也可以直接打开：

```text
runs/<run_id>/reports/run_manifest.json
```

### 5. 检查目录结构

理想情况下，你应该能看到类似结构：

```text
runs/
  manifest-001-20260716-xxxxxx-abcdef12/
    analysis/
      paper_summary.json
      method_modules.json
      repo_map.json
      repo_summary.md
      paper_code_mapping.json
      paper_code_mapping.md
    planning/
      experiment_plan.json
      experiment_plan.md
      command_selection_record.json
      effective_run_commands.json
    execution/
      execution.log
    debug/
      debug_report.json
      debug_report.md
    reports/
      final_report.md
      artifact_index.json
      run_manifest.json
```

---

## 十、这一阶段完成后的验收标准

你可以按下面这份清单验收。

### 功能验收

- 每次 `run_graph` 都会生成一个新的 `run_id`
- graph 如果发生 interrupt/resume，会继续复用同一个 `run_id`
- graph 结束后，`runs/<run_id>/` 会被创建出来
- `output_files` 中已有的文件会被归档到 `runs/<run_id>/` 下
- 会生成：
  - `runs/<run_id>/reports/artifact_index.json`
  - `runs/<run_id>/reports/run_manifest.json`

### 信息完整性验收

- `run_manifest.json` 能记录：
  - `paper_path`
  - `repo_path`
  - `experiment_goal`
  - `final_status`
  - `selected_run_command_index`
  - `selected_run_command`
  - `pending_action_hash`
  - `approval_record`
  - `execution_result`

### 工程结构验收

- `outputs/` 仍然可以继续作为开发调试目录使用
- `runs/` 成为真正的 per-run 归档目录
- checkpoint 和 artifact 不再混在一起

---

## 十一、这一阶段的价值到底是什么

这一阶段看起来不像前面“命令选择”“审批哈希”那样显眼，但实际上工程价值非常高。

它解决的是 agent 系统里一个很常见的问题：

```text
系统能跑
但每次跑完之后很难复盘
```

做完这一步之后，你的项目就开始具备“可审计、可复盘、可比较”的基础设施了。

这会直接帮助你继续做下面这些能力：

- 多次运行效果对比
- 自动评测按 run 归档
- 失败样本回放
- reproduction verification
- repair loop 迭代历史追踪

---

## 十二、下一步最值得做什么

在这个阶段之后，我最推荐你继续做的是：

```text
Phase 20：Preflight Check 与 Environment Readiness
```

也就是在真正执行命令之前，先自动检查：

- Python 版本是否匹配
- 依赖是否安装
- CUDA / torch / gcc 是否兼容
- 数据路径是否存在
- shell 命令是否可执行

为什么下一步推荐做这个？

因为你现在已经有：

- action builder
- command selection
- approval hash
- executor
- run manifest

这意味着你已经具备“执行前最后一道检查层”所需要的上下文了。

很多真实复现失败，其实不是算法问题，而是：

- 环境没准备好
- 命令参数缺失
- 数据路径不存在
- 扩展编译前置条件不满足

所以在真正执行前补一层 preflight，会非常值得。

---

## 最后一句话总结这一阶段

这一阶段的本质不是“再生成两个 JSON 文件”，而是：

```text
把 agent 从“会跑的一次性流程”
升级成“每次运行都有独立身份、独立产物、独立清单的可追溯系统”
```

这一步做完后，你后面不管做验证、调试、评测还是 resume，都会顺手很多。
