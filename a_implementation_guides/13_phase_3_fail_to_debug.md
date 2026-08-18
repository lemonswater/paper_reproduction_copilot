# 13. 端到端闭环第三阶段：执行失败后自动进入 `log_debug`

## 这一阶段的目标

第二阶段你已经把链路推进到了：

```text
experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
  -> executor
  -> END
```

现在最关键的断点在于：

- 命令已经能执行
- 执行日志也已经能落盘
- 但**执行失败之后，graph 还不会自动进入 `log_debug`**

所以第三阶段的目标就是把下面这条链打通：

```text
审批通过
  -> executor 执行命令
  -> 执行失败
  -> 把执行日志路径写回 state["log_path"]
  -> graph 自动路由到 log_debug
  -> 生成 debug_report.json / debug_report.md
```

这一阶段做完后，你的 Agent 就会从：

```text
执行失败 -> 停在那儿
```

升级成：

```text
执行失败 -> 自动进入日志诊断 -> 输出结构化 debug 报告
```

这是真正的“失败路径闭环”。

这里的“执行失败”特指：

- Agent 已经成功走到了 `executor_node`
- 并且开始执行一条“复现任务命令”
- 但这条命令本身执行失败了

例如：

- `python train.py` 缺依赖
- `torchrun ...` CUDA OOM
- 数据路径错误
- 配置不匹配导致脚本退出

它**不是**指：

- 你的 Agent 项目源码自己报 `TypeError`
- graph 节点导入错误
- `executor_node.py` / `exec_tools.py` 本身写错导致程序崩掉

也就是说，Phase 3 处理的是：

```text
复现动作执行失败
```

而不是：

```text
Agent 项目实现 bug
```

---

## 先说清楚：这一阶段解决的不是“日志节点本身”，而是“失败回流的桥”

你现在的 [app/nodes/log_debug_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/log_debug_node.py:1) 已经可以：

- 读取 `log_path`
- 提取 traceback
- 调用 LLM 生成 `DebugReport`
- 输出 `debug_report.json` 和 `debug_report.md`

所以 V5 的日志分析能力本身已经存在。

当前真正缺的是：

- 谁在失败时把日志路径放回 state？
- graph 怎么知道“失败了，现在该进 debug”？

也就是说，这一阶段补的是“失败 -> debug”之间的桥，而不是重新发明一个 debug 节点。

---

## 本阶段要新增 / 修改的文件

```text
app/nodes/executor_node.py
app/graph.py
tests/test_executor_node.py
tests/test_fail_to_debug_flow.py
```

可选补充：

```text
tests/test_log_debug_node.py
```

如果你想把日志诊断节点本身也做成更稳定的 mock 测试，可以后面再加这一份。

---

## 先提醒一个前置检查：Phase 2 代码里有两个常见小问题

我根据你现在仓库里的代码状态，先提醒两处很容易影响第三阶段调试的点。

### 1. `app/nodes/executor_node.py` 里有一个字段名拼写

你现在文件里开头是：

```python
if not pending_action:
    return {"final_statue": "no_pending_action"}
```

这里应该是：

```python
return {"final_status": "no_pending_action"}
```

否则后面 graph 路由或报告判断会读不到统一的 `final_status`。

### 2. `app/tools/exec_tools.py` 里 `subprocess.run()` 参数可能写成了 `text=text`

如果你当前文件里有这种写法：

```python
text=text,
```

应该改成：

```python
text=True,
```

否则执行命令时会直接报错。

这两处不属于 phase 3 的核心逻辑，但如果不先修掉，后面做“失败回流到 debug”时会很容易被无关错误干扰。

---

## 一、Phase 3 的设计目标

这一阶段建议你坚持下面这套简单设计：

### 成功路径

```text
executor
  -> final_status == "succeeded"
  -> END
```

### 失败路径

```text
executor
  -> final_status == "failed"
  -> log_path 已写回 state
  -> route_after_executor() 返回 "log_debug"
  -> log_debug_node
  -> END
```

### 为什么不要一开始就做得太复杂

你当然可以直接设计成：

- success -> final_report
- fail -> debug -> final_report
- reject -> final_report
- revise -> 回到 action_builder

但第三阶段建议先别这么做。

原因是现在最重要的不是“漂亮的最终结构”，而是先证明：

> executor 失败以后，graph 的确会自动走到 debug 节点。

等这一跳稳定了，再做：

- `final_report_node`
- `revise` 回流
- 执行成功后的总结节点

会更稳。

---

## 二、先改 `app/nodes/executor_node.py`

### 这一步要解决什么问题

第二阶段的 executor 已经会：

- 执行命令
- 写 execution log
- 记录 `final_status`

但它现在还没有做一件对 phase 3 最重要的事：

- 在失败时把这份 execution log 写回 `state["log_path"]`

而 `log_debug_node()` 正是依赖这个字段触发的。

### 建议的改法

策略很简单：

- 执行成功时：
  - 记录 `execution_log_path`
  - 不一定非要覆盖 `log_path`

- 执行失败时：
  - 同时写：
    - `execution_log_path`
    - `log_path`

这样 graph 后面的路由就可以直接根据 `log_path` 决定是否进入 `log_debug`。

### 建议修改后的完整代码

```python
from app.config import settings
from app.tools.exec_tools import run_command_safe


def executor_node(state: dict) -> dict:
    """
    根据审批结果决定是否执行 pending_action。

    Phase 3 的关键增强点是：
    - 如果执行失败，把 execution log 的路径同步写回 state["log_path"]
    - 让 graph 可以自然地把失败执行接到 log_debug 分支
    """

    pending_action = state.get("pending_action")
    if not pending_action:
        return {"final_status": "no_pending_action"}

    decision = state.get("user_approval")

    # 审批拒绝：不执行，但保留状态，方便后续做 final_report。
    if decision == "rejected":
        return {
            "final_status": "rejected",
            "last_action_result": {
                "status": "rejected",
                "pending_action": pending_action,
            },
        }

    # 审批要求修改：不执行，等待后续更复杂的 revise 回流机制。
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

    result = run_command_safe(command=command, cwd=cwd)

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = settings.output_dir / "execution.log"

    # 无论成功还是失败，都把执行输出落盘。
    # 这样失败时可以直接作为 log_debug 的输入。
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

    # Phase 3 的关键：
    # 只有执行失败时，才额外把日志路径写回 log_path。
    # 这样 route_after_executor() 就能判断：
    # "failed + log_path" 是否应该进入 log_debug。
    if final_status == "failed":
        payload["log_path"] = str(log_path)

    return payload
```

---

## 三、修改 `app/graph.py`

### 这一步要解决什么问题

你现在的 graph 是：

```text
human_review -> executor -> END
```

这意味着：

- 即便 executor 已经失败
- 即便 executor 已经写了日志

graph 仍然会直接结束，而不会进入 `log_debug`。

所以这一阶段要加一个新的路由函数：

```python
route_after_executor()
```

### 建议的路由规则

推荐用下面这套足够简单的规则：

- `final_status == "failed"` 且 `log_path` 存在
  - 进入 `log_debug`

- 其他情况
  - 结束

这样设计的优点是：

- 简单
- 好测
- 状态语义清晰

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
    risk_check 后决定是否需要人工审批。
    当前阶段仍然保持：
    - requires_approval=True -> human_review
    - 否则结束
    """
    if state.get("requires_approval"):
        return "human_review"
    return END


def route_after_executor(state: ReproductionState) -> str:
    """
    Phase 3 新增的关键路由函数。

    当 executor 执行失败，并且已经把日志路径写回 state["log_path"] 后，
    graph 自动进入 log_debug 分支。

    其他情况直接结束：
    - 执行成功
    - 审批被拒绝
    - revise_requested
    - unsupported_action
    """
    if state.get("final_status") == "failed" and state.get("log_path"):
        return "log_debug"
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

    # action_builder 决定是否进入审批链
    builder.add_conditional_edges("action_builder", route_after_action_builder)

    # risk_check 决定是否需要人工审批
    builder.add_conditional_edges("risk_check", route_after_risk_check)

    # 审批结束后进入 executor
    builder.add_edge("human_review", "executor")

    # Phase 3 核心改动：
    # executor 执行后不再直接 END，
    # 而是根据 final_status 决定是否要自动进入 log_debug。
    builder.add_conditional_edges("executor", route_after_executor)

    builder.add_edge("log_debug", END)

    return builder.compile(checkpointer=build_checkpointer())
```

---

## 四、补测试：修改 `tests/test_executor_node.py`

### 这一步要解决什么问题

第二阶段你已经有：

- `approved` 时执行
- `rejected` / `revise` 时不执行
- 失败时 `final_status == "failed"`

第三阶段还要补一个关键断言：

- 当执行失败时，返回结果里必须带上 `log_path`

因为 graph 后续正是依赖这个字段路由到 `log_debug`。

### 建议修改后的完整测试文件

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

    with patch("app.nodes.executor_node.settings.output_dir", tmp_path):
        with patch("app.nodes.executor_node.run_command_safe", return_value=fake_result) as mocked_run:
            result = executor_node(state)

    mocked_run.assert_called_once_with(command="python train.py", cwd="/tmp/demo-repo")
    assert result["final_status"] == "succeeded"
    assert result["execution_result"]["ok"] is True
    assert result["execution_log_path"]
    assert result["output_files"]

    # 成功执行时不强制要求写回 log_path。
    assert "log_path" not in result


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


def test_executor_marks_failed_and_sets_log_path_when_command_execution_fails(tmp_path) -> None:
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

    # Phase 3 的关键断言：
    # 执行失败时，必须把日志路径同步写回 log_path，
    # 这样 graph 后面的 route_after_executor() 才能自动进入 log_debug。
    assert result["log_path"] == result["execution_log_path"]
```

---

## 五、新增测试：`tests/test_fail_to_debug_flow.py`

### 为什么还要单独加这个测试

因为第三阶段真正新增的是“graph 的失败路由逻辑”，而不仅仅是 executor 的返回值。

所以建议单独写一份小测试，验证：

- `route_after_executor()` 会不会在失败时返回 `"log_debug"`
- 在非失败状态时会不会正确返回 `END`

这比一上来就硬写完整 graph e2e 测试更稳。

### 新文件完整代码

```python
from langgraph.graph import END

from app.graph import route_after_executor


def test_route_after_executor_goes_to_log_debug_when_failed_with_log_path() -> None:
    state = {
        "final_status": "failed",
        "log_path": "outputs/execution.log",
    }

    result = route_after_executor(state)

    assert result == "log_debug"


def test_route_after_executor_ends_when_succeeded() -> None:
    state = {
        "final_status": "succeeded",
        "execution_log_path": "outputs/execution.log",
    }

    result = route_after_executor(state)

    assert result == END


def test_route_after_executor_ends_when_failed_but_no_log_path() -> None:
    # 即使 final_status 是 failed，如果没有 log_path，
    # graph 也没法进入 log_debug。
    # 这个测试可以帮助你发现 executor 是否漏写了 log_path。
    state = {
        "final_status": "failed",
    }

    result = route_after_executor(state)

    assert result == END
```

---

## 六、这一阶段怎么运行验证

### 1. 先跑节点级测试

```bash
python -m pytest tests/test_executor_node.py
python -m pytest tests/test_fail_to_debug_flow.py
```

如果你想一起回归前两阶段：

```bash
python -m pytest tests/test_action_builder_node.py tests/test_review_flow.py tests/test_executor_node.py tests/test_fail_to_debug_flow.py
```

### 2. 手动验证“失败会进入 debug”

真正要让 graph 自动进入 `log_debug`，你需要一条确定会失败的命令。

但当前主链里 `experiment_plan` 产出的命令是由 LLM 决定的，所以手工验图时会有不稳定性。

因此这一阶段更推荐两种验证方式：

#### 方式 A：节点级 + 路由级测试

这是最稳的，优先推荐。

#### 方式 B：临时手工注入失败动作

如果你以后想做手工 graph 验证，可以考虑：

- 在测试里直接构造 state
- 跳过前面的论文和仓库分析节点
- 只测：

```text
action_builder / risk_check / human_review / executor / log_debug
```

这样可以更稳定地复现失败链。

---

## 七、这一步做完后，你的闭环能力会发生什么变化

第三阶段做完后，你的系统会从：

```text
计划 -> 审批 -> 执行 -> 结束
```

升级成：

```text
计划 -> 审批 -> 执行
         -> 成功：结束
         -> 失败：自动日志诊断 -> 结束
```

这意味着：

- Agent 已经不只是“执行动作”
- 而是开始具备“失败自我诊断”的能力

这正是端到端闭环里非常关键的一环。

---

## 八、这一阶段最常见的坑

### 1. executor 写了 `execution_log_path`，但没写 `log_path`

这是 phase 3 最核心也最容易漏的一点。

后果是：

- 日志文件虽然存在
- 但 graph 路由条件读不到 `log_path`
- `log_debug` 分支永远进不去

### 2. graph 里还是 `builder.add_edge("executor", END)`

如果你忘了把 executor 改成条件路由，那么失败后也不会进入 debug。

一定要改成：

```python
builder.add_conditional_edges("executor", route_after_executor)
```

### 3. 把“审批被拒绝”也送进 log_debug

`rejected` 和 `revise_requested` 不是“执行失败”，而是“人工决策结果”。

所以不要让这些状态误进 `log_debug`，否则语义会很乱。

### 4. 在这一步就强行做跨 CLI resume 验证

如果还没把 `InMemorySaver` 换成持久化 checkpointer，两条独立命令之间通常共享不了中断状态。

这一阶段先把：

- executor
- route_after_executor
- fail -> log_debug

这些节点级和图级逻辑补稳就好。

### 5. 手动测试时过度依赖 LLM 输出的命令

因为 `experiment_plan.run_commands` 来自模型，可能每次都不一样。

所以 phase 3 最稳的验证方式仍然是：

- mock executor
- mock command output
- 单元测试路由逻辑

---

## 九、下一阶段该做什么

当你把第三阶段改完并测通后，下一步最值得做的是：

```text
phase 4: final_report + eval 升级
```

也就是把现在这些分散产物串成统一报告：

- 论文摘要
- repo map
- paper-code mapping
- experiment plan
- 审批结果
- 执行结果
- debug 报告

最后统一落成：

```text
outputs/final_report.md
```

同时升级 `run_eval.py`，让评测不只是分析链，还能覆盖：

- action builder
- executor
- fail -> debug

如果你愿意，等你把这一阶段做完，我下一步可以继续按同样风格给你写：

```text
14_phase_4_final_report_and_eval.md
```

把最后一段“收口和展示”的代码也完整写进 md 文件里。
