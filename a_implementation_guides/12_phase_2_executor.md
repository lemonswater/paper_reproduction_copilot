# 12. 端到端闭环第二阶段：新增 `executor_node`，打通“审批后执行”

## 这一阶段的目标

第一阶段你已经把这条链打通到了：

```text
experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
```

但当前图里还有一个很明显的断点：

- 审批可以发生
- 风险可以判断
- 但审批通过后，没有任何节点真的去执行动作

所以第二阶段的目标非常明确：

1. 新增命令执行工具层 `exec_tools.py`
2. 新增 `executor_node.py`
3. 把 graph 改成 `human_review -> executor -> END`
4. 让 executor 能把执行结果、日志路径、最终状态写回 state
5. 补一份 `tests/test_executor_node.py`

这一步做完后，项目会从：

```text
分析 -> 计划 -> 审批 -> 结束
```

升级成：

```text
分析 -> 计划 -> 审批 -> 执行 -> 记录结果 -> 结束
```

虽然还没有把“执行失败自动进入 log_debug”接上，但闭环里最关键的“执行动作”这一跳就已经打通了。

---

## 先提醒一个重要现实：当前 `InMemorySaver` 的限制

你现在的 [app/memory/checkpoint.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/memory/checkpoint.py:1) 还是 `InMemorySaver`。

这意味着：

- 同一个 Python 进程里，graph 的暂停 / 恢复可以共享内存状态
- 但如果你这样测试：

```bash
python -m app.main run-graph ...
python -m app.main resume-review ...
```

这是两条独立进程命令，第二条命令通常拿不到第一条命令的内存 checkpoint。

所以在这一阶段你要分清两件事：

1. **节点逻辑是否正确**
   - 可以通过 `pytest` 测

2. **跨命令的 interrupt / resume 是否能恢复**
   - 当前默认 `InMemorySaver` 下，不一定能成立

这不是你代码写错了，而是 checkpointer 选型的天然限制。

所以第二阶段的重点，先放在：

- executor 节点本身
- graph 结构是否合理
- 执行结果是否能回写 state

而不是强求立刻用两条 CLI 命令把 resume 全部跑通。

---

## 本阶段要新增 / 修改的文件

```text
app/tools/exec_tools.py
app/nodes/executor_node.py
app/graph.py
tests/test_executor_node.py
```

可选检查：

```text
app/state.py
```

因为你在第一阶段里本来就应该已经加过：

- `run_commands`
- `human_feedback`
- `execution_result`
- `execution_log_path`
- `last_action_result`
- `final_status`

如果你发现 `state.py` 里还没有 `run_commands`，建议顺手补上。

---

## 一、先补工具层：`app/tools/exec_tools.py`

### 作用

不要把 `subprocess.run(...)` 直接写进 `executor_node.py` 里。

把真正的命令执行逻辑抽成工具层有几个好处：

1. 节点层更干净，只负责读 state / 写 state
2. 工具层可以单独测试
3. 后面如果想加 timeout、环境变量、stdout 截断、日志清洗，都有明确位置

### 设计原则

这一阶段建议先坚持一个简单边界：

- 只支持普通命令行
- 不支持 pipe、重定向、复杂 shell 语法
- 使用 `shlex.split()` + `subprocess.run(shell=False)`

这样做的好处是更可控，也更符合“审批后受限执行”的目标。

### 新文件完整代码

```python
import shlex
import subprocess


def run_command_safe(command: str, cwd: str, timeout: int = 300) -> dict:
    """
    在指定 cwd 中执行一条命令，并返回统一结构的执行结果。

    这一阶段刻意做得比较保守：
    1. 只接受一条普通命令字符串；
    2. 使用 shlex.split() 解析，而不是 shell=True；
    3. 不支持 pipe、重定向、变量展开等复杂 shell 功能；
    4. 给一个默认 timeout，避免子进程无限挂住。

    返回结果统一为 dict，方便 executor_node 直接写回 state。
    """

    # 先把命令拆成 token。
    # 例如：
    # "python train.py --config configs/base.yaml"
    # 会变成：
    # ["python", "train.py", "--config", "configs/base.yaml"]
    tokens = shlex.split(command)

    # 空命令直接返回失败结果，而不是继续调用 subprocess。
    if not tokens:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": "empty command",
            "combined_output": "empty command",
            "timeout": False,
        }

    try:
        # shell=False 更适合“受控执行”场景：
        # - 不会自动解释复杂 shell 语法
        # - 更容易控制命令边界
        # - 风险更小
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

        # 只有 stderr 非空时，才把它拼接到 combined_output 后面。
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
        # 命令超时也要返回统一结构，而不是直接让整个节点崩掉。
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
        # 比如 python / torchrun 本身不存在时会进这里。
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

---

## 二、新增节点：`app/nodes/executor_node.py`

### 作用

这个节点负责两类事情：

1. 处理审批结果
2. 如果审批通过，就真正执行 `pending_action`

这意味着它不仅是“执行器”，也是“审批结果落地器”。

### 设计思路

这里建议采用一种很稳的做法：

- graph 里统一让 `human_review -> executor`
- 不在 graph 层再细分 `approved / rejected / revise`
- 而是让 `executor_node()` 自己判断：
  - `approved`：执行
  - `rejected`：不执行，记录状态
  - `revise`：不执行，记录状态

这样 graph 会更简单，状态语义更集中。

### 日志文件怎么处理

这一阶段虽然还没把失败自动接到 `log_debug`，但建议你现在就把执行日志落盘。

原因是下一阶段接 `log_debug` 时，会非常顺。

### 新文件完整代码

```python
from app.config import settings
from app.tools.exec_tools import run_command_safe


def executor_node(state: dict) -> dict:
    """
    根据审批结果决定是否执行 pending_action，
    并把执行结果写回 state。

    当前阶段只支持：
    - pending_action["type"] == "run_command"

    如果审批未通过，executor 不会真正执行命令，
    但仍然会把最终状态写回 state，方便后续报告与调试。
    """

    pending_action = state.get("pending_action")
    if not pending_action:
        return {"final_status": "no_pending_action"}

    # human_review_node 返回的 user_approval 可能是：
    # - approved
    # - rejected
    # - revise
    #
    # 为了兼容未来“无需审批直接执行”的分支，
    # 这里也接受 not_required。
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

    # 当前阶段把 approved 和 not_required 都视为允许执行。
    if decision not in {"approved", "not_required"}:
        return {
            "final_status": "not_executed",
            "last_action_result": {
                "status": "not_executed",
                "pending_action": pending_action,
                "reason": f"unsupported approval status: {decision}",
            },
        }

    action_type = pending_action.get("type")
    if action_type != "run_command":
        return {
            "final_status": "unsupported_action",
            "last_action_result": {
                "status": "unsupported_action",
                "pending_action": pending_action,
            },
            "error": f"unsupported action type: {action_type}",
        }

    command = pending_action["command"]
    cwd = pending_action.get("cwd") or state.get("repo_path") or "."

    # 这里调用工具层真正执行命令。
    result = run_command_safe(command=command, cwd=cwd)

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = settings.output_dir / "execution.log"

    # 把执行输出统一落到日志文件里。
    # 这样下一阶段接 log_debug 时，只要把 log_path 写回 state，
    # router 就能很自然地进入 debug 分支。
    log_path.write_text(result["combined_output"], encoding="utf-8")

    final_status = "succeeded" if result["ok"] else "failed"

    return {
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

---

## 三、修改 `app/graph.py`

### 作用

现在第二阶段的核心图改动很简单：

```text
human_review -> executor -> END
```

在这个阶段里，我们还不把 executor 失败自动接到 `log_debug`，因为那会留到第三阶段单独处理。

### 图层设计建议

当前建议保留这几条原则：

- `action_builder` 后统一决定要不要进入审批链
- `risk_check` 仍然只负责“要不要审批”
- `human_review` 只负责收集人工意见
- `executor` 才真正处理“执行 / 不执行”

### 建议修改后的完整代码

```python
from langgraph.graph import END, START, StateGraph

from app.nodes.action_builder_node import action_builder_node
from app.state import ReproductionState
from app.memory.checkpoint import build_checkpointer
from app.nodes.code_search_node import code_search_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.log_debug_node import log_debug_node
from app.nodes.human_review_node import human_review_node
from app.nodes.risk_check_node import risk_check_node
from app.nodes.executor_node import executor_node


def route_after_action_builder(state: ReproductionState) -> str:
    """
    action_builder 后的路由：
    1. 有 pending_action -> 进入 risk_check
    2. 没有 pending_action 但有 log_path -> 进入 log_debug
    3. 否则结束
    """
    if state.get("pending_action"):
        return "risk_check"
    if state.get("log_path"):
        return "log_debug"
    return END


def route_after_risk_check(state: ReproductionState) -> str:
    """
    risk_check 之后：
    - 需要审批 -> 进入 human_review
    - 不需要审批 / 被阻断 -> 先结束

    注意：
    当前 safe_shell_tools 的规则下，真正的 run_command 基本都会要求审批，
    被 blocked 的命令则会直接终止，不进入 executor。
    """
    if state.get("requires_approval"):
        return "human_review"
    return END


def build_graph():
    builder = StateGraph(ReproductionState)

    # 主分析链
    builder.add_node("paper_reader", paper_reader_node)
    builder.add_node("method_extractor", method_extractor_node)
    builder.add_node("repo_scan", repo_scan_node)
    builder.add_node("code_search", code_search_node)
    builder.add_node("mapping", mapping_node)
    builder.add_node("experiment_plan", experiment_plan_node)
    builder.add_node("action_builder", action_builder_node)

    # 审批与执行相关节点
    builder.add_node("risk_check", risk_check_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("executor", executor_node)

    # 失败分析节点
    builder.add_node("log_debug", log_debug_node)

    # 主链
    builder.add_edge(START, "paper_reader")
    builder.add_edge("paper_reader", "method_extractor")
    builder.add_edge("method_extractor", "repo_scan")
    builder.add_edge("repo_scan", "code_search")
    builder.add_edge("code_search", "mapping")
    builder.add_edge("mapping", "experiment_plan")
    builder.add_edge("experiment_plan", "action_builder")

    # action_builder 决定往审批链 / debug / END
    builder.add_conditional_edges("action_builder", route_after_action_builder)

    # risk_check 决定是否需要人工审批
    builder.add_conditional_edges("risk_check", route_after_risk_check)

    # 第二阶段的关键新增：
    # human_review 后固定进入 executor。
    # executor 自己根据 user_approval 决定是否真正执行命令。
    builder.add_edge("human_review", "executor")

    # 当前阶段 executor 执行完就结束；
    # 第三阶段再把 failed -> log_debug 接起来。
    builder.add_edge("executor", END)

    builder.add_edge("log_debug", END)

    return builder.compile(checkpointer=build_checkpointer())
```

---

## 四、新增测试：`tests/test_executor_node.py`

### 作用

这一阶段最重要的测试不是 graph 级测试，而是先把 `executor_node()` 本身测稳。

因为当前跨两条 CLI 命令恢复 graph 仍然受 `InMemorySaver` 限制，所以节点级测试会更稳定。

### 测试重点

建议至少覆盖下面四种情况：

1. `approved` 时真正执行，并写出日志
2. `rejected` 时不执行
3. `revise` 时不执行
4. 命令执行失败时，`final_status == "failed"`

### 新文件完整代码

```python
from unittest.mock import patch

from app.nodes.executor_node import executor_node


def test_executor_runs_command_when_approved(tmp_path) -> None:
    state = {
        "user_approval": "approved",
        "pending_action": {
            "type": "run_command",
            "command": "python train.py",
            "cwd": "/tmp/demo-repo",
            "reason": "run baseline training",
            "source": "experiment_plan",
        },
        "output_files": [],
    }

    fake_result = {
        "ok": True,
        "returncode": 0,
        "stdout": "training started",
        "stderr": "",
        "combined_output": "training started",
        "timeout": False,
    }

    # patch settings.output_dir，让测试写到 pytest 提供的临时目录里。
    with patch("app.nodes.executor_node.settings.output_dir", tmp_path):
        with patch("app.nodes.executor_node.run_command_safe", return_value=fake_result) as mocked_run:
            result = executor_node(state)

    mocked_run.assert_called_once_with(command="python train.py", cwd="/tmp/demo-repo")
    assert result["final_status"] == "succeeded"
    assert result["execution_result"]["ok"] is True
    assert result["execution_log_path"]
    assert result["output_files"]


def test_executor_does_not_run_when_rejected() -> None:
    state = {
        "user_approval": "rejected",
        "pending_action": {
            "type": "run_command",
            "command": "python train.py",
            "cwd": "/tmp/demo-repo",
        },
    }

    with patch("app.nodes.executor_node.run_command_safe") as mocked_run:
        result = executor_node(state)

    mocked_run.assert_not_called()
    assert result["final_status"] == "rejected"
    assert result["last_action_result"]["status"] == "rejected"


def test_executor_does_not_run_when_revise_requested() -> None:
    state = {
        "user_approval": "revise",
        "human_feedback": "请先缩小 batch size",
        "pending_action": {
            "type": "run_command",
            "command": "python train.py",
            "cwd": "/tmp/demo-repo",
        },
    }

    with patch("app.nodes.executor_node.run_command_safe") as mocked_run:
        result = executor_node(state)

    mocked_run.assert_not_called()
    assert result["final_status"] == "revise_requested"
    assert result["last_action_result"]["human_feedback"] == "请先缩小 batch size"


def test_executor_marks_failed_when_command_execution_fails(tmp_path) -> None:
    state = {
        "user_approval": "approved",
        "pending_action": {
            "type": "run_command",
            "command": "python train.py",
            "cwd": "/tmp/demo-repo",
        },
        "output_files": [],
    }

    fake_result = {
        "ok": False,
        "returncode": 1,
        "stdout": "",
        "stderr": "RuntimeError: CUDA out of memory",
        "combined_output": "RuntimeError: CUDA out of memory",
        "timeout": False,
    }

    with patch("app.nodes.executor_node.settings.output_dir", tmp_path):
        with patch("app.nodes.executor_node.run_command_safe", return_value=fake_result):
            result = executor_node(state)

    assert result["final_status"] == "failed"
    assert result["execution_result"]["ok"] is False
    assert result["execution_log_path"]
```

---

## 五、推荐运行方式

### 1. 先跑 executor 节点测试

```bash
python -m pytest tests/test_executor_node.py
```

### 2. 再跑前面两阶段相关测试

```bash
python -m pytest tests/test_action_builder_node.py
python -m pytest tests/test_review_flow.py
```

如果你想一次性跑审批链相关测试：

```bash
python -m pytest tests/test_action_builder_node.py tests/test_review_flow.py tests/test_executor_node.py
```

### 3. 手工跑 graph 主链

这一阶段你可以先验证 graph 至少能走到 `human_review` / `executor` 结构上：

```bash
python -m app.main run-graph "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" /data/tianshaoqi24/P4Transformer/ --thread-id executor-001
```

不过要注意：

- 当前如果 graph 真的触发了 `interrupt()`
- 你再用第二条 CLI 命令 `resume-review`
- 在 `InMemorySaver` 下很可能接不回去

所以这一阶段真正可靠的验证方式，还是：

- 节点级测试
- 单进程里的 graph 测试

而不是跨两条独立命令硬测 resume。

---

## 六、这一阶段完成后的预期效果

这一阶段做完后，你的工作流会从：

```text
experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
  -> END
```

升级成：

```text
experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
  -> executor
  -> END
```

这代表：

- 审批不再只是“形式上的”
- graph 已经真正拥有执行动作的能力
- execution log 已经开始落盘
- 为下一阶段“失败自动接到 log_debug”做好了准备

---

## 七、这一阶段最常见的坑

### 1. 直接用 `shell=True`

这虽然看起来更省事，但会让命令边界变得更难控制，也不利于安全。

当前阶段建议优先：

- `shlex.split()`
- `subprocess.run(shell=False)`

### 2. 把执行逻辑直接写进 graph 或 review 节点

这样后面很难测试和复用。

建议坚持：

- 工具层只负责执行命令
- 节点层只负责读写 state

### 3. 审批拒绝时还继续执行

一定要在 executor 里显式区分：

- `approved`
- `rejected`
- `revise`

否则审批链就失去意义了。

### 4. 只返回 stdout/stderr，不落日志文件

这样下一阶段接 log debug 时会很别扭。

建议现在就统一写出：

```text
outputs/execution.log
```

### 5. 用两条 CLI 命令强测 `resume-review`

如果你还没换 persistent checkpointer，这通常会因为 `InMemorySaver` 限制而失败。

要区分：

- checkpoint 机制的理论设计
- 当前 checkpointer 的进程级限制

---

## 八、下一阶段该做什么

等你把这一阶段手改完并测试通过后，下一步就应该进入：

```text
phase 3: 失败自动进入 log_debug
```

也就是：

1. executor 失败时把日志路径写回 `log_path`
2. 新增 `route_after_executor()`
3. `failed + log_path -> log_debug`
4. 自动生成 `debug_report.json` 和 `debug_report.md`

如果你愿意，等你把这一阶段改完，我下一步可以继续按同样风格给你写：

```text
13_phase_3_fail_to_debug.md
```

把第三阶段的代码也完整写进 md 文件里。
