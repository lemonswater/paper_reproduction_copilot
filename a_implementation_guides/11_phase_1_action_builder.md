# 11. 端到端闭环第一阶段：打通 `experiment_plan -> pending_action -> risk_check`

## 这一阶段的目标

这一阶段不做真正的命令执行，只解决当前闭环里的第一个关键断点：

```text
experiment_plan 已经能生成 run_commands
但 graph 里没有节点把 run_commands 转成 pending_action
导致 risk_check / human_review 分支虽然存在，却很难真正触发
```

所以这一阶段的目标很明确：

1. 补 state 字段  
2. 调整 CLI 入口  
3. 新增 `action_builder_node`  
4. 修改 graph，让 `experiment_plan` 后面先进入 `action_builder`  
5. 加一份针对 `action_builder_node` 的测试

这一步做完后，你的项目会从：

```text
分析 -> 计划 -> 结束
```

升级成：

```text
分析 -> 计划 -> 待执行动作 -> 风险判断 -> 人工审批
```

虽然还没有真正执行命令，但审批链就已经真正接上了。

---

## 本阶段要修改 / 新增的文件

```text
app/state.py
app/main.py
app/nodes/action_builder_node.py
app/graph.py
tests/test_action_builder_node.py
```

---

## 1. 修改 `app/state.py`

### 作用

当前 `state.py` 里还缺少闭环第一阶段会用到的一些关键字段，尤其是：

- `run_commands`
- `human_feedback`
- `execution_result`
- `execution_log_path`
- `last_action_result`
- `final_status`

另外，当前 `experiment_plan` 的类型也更适合写成 `dict[str, Any]`，因为 `experiment_plan_node()` 实际返回的是一个对象，而不是列表。

### 建议修改后的完整代码

```python
from typing import Any, Optional, TypedDict


# 这个 TypedDict 定义了整条 Agent 图工作流共享的状态结构。
# total=False 表示这些字段不是每个阶段都必须一次性提供，
# 而是允许节点逐步往 state 里补充信息。
class ReproductionState(TypedDict, total=False):
    # 任务身份与用户输入
    task_id: str
    user_query: str
    paper_path: Optional[str]
    repo_path: Optional[str]
    log_path: Optional[str]
    experiment_goal: Optional[str]

    # 论文与仓库分析阶段产出的中间结果
    paper_text_chunks: list[dict[str, Any]]
    paper_summary: dict[str, Any]
    method_modules: list[dict[str, Any]]
    repo_map: dict[str, Any]
    paper_code_mapping: list[dict[str, Any]]

    # experiment_plan_node 实际返回的是一个对象，
    # 所以这里用 dict[str, Any] 比 list[...] 更合适。
    experiment_plan: dict[str, Any]

    # 从 ExperimentPlan 中单独抽出来的命令建议列表。
    # 这是 action_builder_node 的直接输入。
    run_commands: list[dict[str, Any]]

    # 日志调试阶段产出的结构化报告。
    debug_report: dict[str, Any]

    # 待执行动作与审批相关字段。
    pending_action: Optional[dict[str, Any]]
    requires_approval: bool
    user_approval: Optional[str]
    human_feedback: Optional[str]

    # 执行阶段相关字段。
    # 当前第一阶段还不会真正执行命令，但先把字段预留好，
    # 后面接 executor_node 时会顺很多。
    execution_result: dict[str, Any]
    execution_log_path: Optional[str]
    last_action_result: dict[str, Any]
    final_status: Optional[str]

    # 通用输出与流程控制字段
    output_files: list[str]
    final_report: Optional[str]
    messages: list[dict[str, Any]]
    step_count: int
    max_steps: int
    error: Optional[str]

    # 代码搜索阶段产出的中间结果
    code_search_results: dict[str, Any]
```

---

## 2. 修改 `app/main.py`

### 作用

这一阶段建议先做两件事：

1. 让 `run_graph()` 里的 `log_path` 变成可选参数  
   这样正常主链运行时不需要强行传日志。

2. 给 `resume_review()` 补上 `Command` 导入  
   否则后面你在审批链里做恢复时，CLI 会直接报错。

### 建议修改后的完整代码

```python
from pathlib import Path

import typer
from langgraph.types import Command
from rich import print

from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.code_search_node import code_search_node
from app.nodes.mapping_node import mapping_node
from app.graph import build_graph


app = typer.Typer(help="Paper Reproduction Copilot")


@app.command()
def version():
    # 最小健康检查命令。
    # 用来确认 CLI 是否能正常启动。
    print("[green]paper-reproduction-copilot 0.1.0[/green]")


@app.command()
def init_outputs():
    # 统一创建 outputs 目录，避免后续节点落盘时目录不存在。
    Path("outputs").mkdir(exist_ok=True)
    print("[green]outputs/ is ready[/green]")


@app.command()
def read_paper(paper_path: str):
    # 只跑 V0 论文阅读链路。
    state = {"paper_path": paper_path, "output_files": []}
    state.update(paper_reader_node(state))
    state.update(method_extractor_node(state))
    print("[green]paper reading finished[/green]")
    print(state["output_files"])


@app.command()
def scan_repo(repo_path: str):
    # 只跑 V1 仓库扫描链路。
    state = {"repo_path": repo_path, "output_files": []}
    state.update(repo_scan_node(state))
    print("[green]repo scan finished[/green]")
    print(state["output_files"])


@app.command()
def map_code(paper_path: str, repo_path: str):
    # 串联论文阅读、仓库扫描和映射链路。
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
    # 串联到实验计划阶段。
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
    # 把 log_path 改成可选参数，而不是强制必填。
    # 这样正常主链运行时，可以不传日志；
    # 如果想让图直接走 debug 分支，再显式传入日志即可。
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
def show_state(thread_id: str = "demo-thread"):
    # 查看某个 thread_id 对应的 graph state 快照。
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
    # 用同一个 thread_id 恢复此前被 interrupt 暂停的图。
    # 这里的 Command(resume=...) 是 LangGraph 恢复机制的关键。
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        Command(resume={"decision": decision, "feedback": feedback}),
        config=config,
    )
    print(result)


if __name__ == "__main__":
    app()
```

---

## 3. 新增 `app/nodes/action_builder_node.py`

### 作用

这是这一阶段最重要的新节点。

它做的事情其实很简单：

- 从 `state["run_commands"]` 中挑出第一条建议命令
- 把它包装成统一的 `pending_action`
- 交给后面的 `risk_check_node`

### 为什么只取第一条命令

因为当前目标是先打通“最小闭环”，不是一次性实现：

- 多动作队列
- 批量审批
- 自动循环执行多个命令

先只执行第一条建议，能让 graph、审批和后续 executor 更容易对齐。

### 新文件完整代码

```python
def action_builder_node(state: dict) -> dict:
    """
    根据 experiment_plan_node 产出的 run_commands，
    构造后续风险判断与人工审批所需要的 pending_action。

    这一阶段先只挑第一条命令，原因是：
    1. 先打通“计划 -> 审批”这条最小闭环；
    2. 降低 graph 路由复杂度；
    3. 让后面新增 executor_node 时更容易调试。
    """

    # 如果上游已经显式写好了 pending_action，
    # 这里优先保留，不覆盖。
    #
    # 这样做的好处是：
    # 1. 便于后续其他节点直接产出动作；
    # 2. 便于手工测试 graph 审批分支；
    # 3. action_builder 既能做“默认桥接”，也不会妨碍“人工注入动作”。
    existing_action = state.get("pending_action")
    if existing_action:
        return {"pending_action": existing_action}

    run_commands = state.get("run_commands", [])

    # 如果 experiment plan 没有给出任何建议命令，
    # 说明当前阶段没有可执行动作。
    # 这里明确返回 pending_action=None，
    # 同时记录 final_status，方便后续 graph 或报告判断。
    if not run_commands:
        return {
            "pending_action": None,
            "final_status": "no_action",
        }

    # 当前只取第一条命令作为待审批动作。
    first_command = run_commands[0]

    # 如果计划里没有给 cwd，就退回到 repo_path。
    # 再退一步，就用当前目录 "."。
    cwd = first_command.get("cwd") or state.get("repo_path") or "."

    # pending_action 是 V6 审批链真正依赖的统一动作格式。
    pending_action = {
        "type": "run_command",
        "command": first_command["command"],
        "cwd": cwd,
        "reason": first_command.get("reason", "from experiment plan"),
        "source": "experiment_plan",
    }

    return {"pending_action": pending_action}
```

---

## 4. 修改 `app/graph.py`

### 作用

当前 graph 的问题是：

- `experiment_plan` 后面直接路由
- 但 `pending_action` 还没被构造出来

所以需要把图改成：

```text
mapping
  -> experiment_plan
  -> action_builder
  -> risk_check / log_debug / END
```

### 建议修改后的完整代码

```python
from langgraph.graph import END, START, StateGraph

from app.state import ReproductionState
from app.memory.checkpoint import build_checkpointer
from app.nodes.action_builder_node import action_builder_node
from app.nodes.code_search_node import code_search_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.log_debug_node import log_debug_node
from app.nodes.human_review_node import human_review_node
from app.nodes.risk_check_node import risk_check_node


def route_after_action_builder(state: ReproductionState) -> str:
    """
    action_builder 执行完成后，决定图接下来往哪里走。

    优先级设计如下：
    1. 如果已经成功构造出 pending_action，说明应该进入审批链；
    2. 如果没有 pending_action，但有 log_path，说明用户想直接走 debug；
    3. 否则说明当前没有待执行动作，也没有显式日志输入，流程结束。
    """
    if state.get("pending_action"):
        return "risk_check"
    if state.get("log_path"):
        return "log_debug"
    return END


def route_after_risk_check(state: ReproductionState) -> str:
    """
    根据风险判断结果，决定是否进入 human_review。

    当前这一阶段仍然是 proposal-only：
    - 需要审批 -> 进入 human_review
    - 不需要审批 / 被阻断 -> 先结束
    """
    if state.get("requires_approval"):
        return "human_review"
    return END


def build_graph():
    builder = StateGraph(ReproductionState)

    # 主链节点：从论文阅读一路到实验计划
    builder.add_node("paper_reader", paper_reader_node)
    builder.add_node("method_extractor", method_extractor_node)
    builder.add_node("repo_scan", repo_scan_node)
    builder.add_node("code_search", code_search_node)
    builder.add_node("mapping", mapping_node)
    builder.add_node("experiment_plan", experiment_plan_node)

    # 新增的桥接节点：把 run_commands 转成 pending_action
    builder.add_node("action_builder", action_builder_node)

    # 失败分析与审批相关节点
    builder.add_node("log_debug", log_debug_node)
    builder.add_node("risk_check", risk_check_node)
    builder.add_node("human_review", human_review_node)

    # 主链顺序
    builder.add_edge(START, "paper_reader")
    builder.add_edge("paper_reader", "method_extractor")
    builder.add_edge("method_extractor", "repo_scan")
    builder.add_edge("repo_scan", "code_search")
    builder.add_edge("code_search", "mapping")
    builder.add_edge("mapping", "experiment_plan")

    # 关键改动：
    # experiment_plan 后面不再直接路由，
    # 而是先进入 action_builder，把动作桥接出来。
    builder.add_edge("experiment_plan", "action_builder")

    # action_builder 后再根据 state 决定往审批链、debug 分支还是结束。
    builder.add_conditional_edges("action_builder", route_after_action_builder)

    # 风险判断后决定是否进入人工审批。
    builder.add_conditional_edges("risk_check", route_after_risk_check)

    builder.add_edge("log_debug", END)
    builder.add_edge("human_review", END)

    return builder.compile(checkpointer=build_checkpointer())
```

---

## 5. 新增 `tests/test_action_builder_node.py`

### 作用

这一阶段建议先给桥接节点单独补一个测试文件，避免你把 graph 和审批逻辑都接上之后，问题反而不好定位。

### 推荐测试点

建议先覆盖这三类情况：

1. 正常从 `run_commands` 构造 `pending_action`
2. 没有命令时返回 `no_action`
3. 上游已经提供 `pending_action` 时不覆盖

### 新文件完整代码

```python
from app.nodes.action_builder_node import action_builder_node


def test_action_builder_builds_pending_action_from_first_run_command() -> None:
    # 构造一个最小状态，模拟 experiment_plan_node 已经给出了两条命令。
    state = {
        "repo_path": "/tmp/demo-repo",
        "run_commands": [
            {
                "command": "python train.py --config configs/base.yaml",
                "cwd": "/tmp/demo-repo",
                "reason": "run baseline training",
            },
            {
                "command": "python eval.py --ckpt outputs/best.pt",
                "cwd": "/tmp/demo-repo",
                "reason": "run evaluation",
            },
        ],
    }

    result = action_builder_node(state)

    # 当前阶段只取第一条命令。
    assert result["pending_action"]["type"] == "run_command"
    assert result["pending_action"]["command"] == "python train.py --config configs/base.yaml"
    assert result["pending_action"]["cwd"] == "/tmp/demo-repo"
    assert result["pending_action"]["reason"] == "run baseline training"
    assert result["pending_action"]["source"] == "experiment_plan"


def test_action_builder_returns_no_action_when_run_commands_is_empty() -> None:
    # 如果没有任何建议命令，就不应该凭空构造动作。
    state = {"run_commands": []}

    result = action_builder_node(state)

    assert result["pending_action"] is None
    assert result["final_status"] == "no_action"


def test_action_builder_keeps_existing_pending_action() -> None:
    # 如果上游已经显式构造了 pending_action，
    # action_builder 应该保持它，而不是覆盖它。
    existing_action = {
        "type": "run_command",
        "command": "python custom.py",
        "cwd": "/tmp/custom",
        "reason": "manual injected action",
        "source": "manual",
    }
    state = {
        "pending_action": existing_action,
        "run_commands": [
            {
                "command": "python train.py",
                "cwd": "/tmp/demo-repo",
                "reason": "from plan",
            }
        ],
    }

    result = action_builder_node(state)

    assert result["pending_action"] == existing_action
```

---

## 6. 这一阶段的手动运行方式

### 先跑节点级测试

```bash
python -m pytest tests/test_action_builder_node.py
```

如果你还想把审批链一起确认一下，也可以再跑：

```bash
python -m pytest tests/test_review_flow.py
```

### 再跑 graph 主链

先不传日志，验证 `run_graph` 现在能走正常主链：

```bash
python -m app.main run-graph "pdf/Point Spatio-Temporal Transformer Networks.pdf" /data/tianshaoqi24/P4Transformer/ --thread-id action-001
```

### 观察结果

你可以重点检查：

- `experiment_plan.json` 是否正常生成
- `action_builder` 是否把第一条 `run_commands` 转成了 `pending_action`
- graph 是否真正进入了 `risk_check` / `human_review` 分支

如果你想进一步看 state：

```bash
python -m app.main show-state --thread-id action-001
```

不过要注意：

- 你当前如果还是 `InMemorySaver`
- 并且 `run-graph` 和 `show-state` 是两条独立命令

那跨进程时很可能看不到之前那次运行的 state，这是 `InMemorySaver` 的天然限制，不一定是代码坏了。

---

## 7. 本阶段完成后的预期效果

这一阶段做完后，你的 graph 会从原来的：

```text
experiment_plan -> END / log_debug
```

变成：

```text
experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
```

这代表：

- 实验计划不再只是“生成一份报告”
- 它开始真正推动后续动作流转
- 审批链从“理论上存在”变成“实际上会被触发”

这是补齐端到端闭环的第一块关键桥。

---

## 8. 下一阶段该做什么

等你把这一阶段手改完并测通后，下一步就该进入：

```text
executor_node
```

也就是：

- 审批通过后，不再直接 `END`
- 而是真正执行一条命令
- 把 stdout / stderr / returncode 和日志路径写回 state
- 为失败后自动接入 `log_debug` 做准备

如果你愿意，等你把这一阶段改完，我下一步可以继续按同样风格给你写：

```text
12_phase_2_executor.md
```

把第二阶段要改的代码也完整写进 md 文件里。
