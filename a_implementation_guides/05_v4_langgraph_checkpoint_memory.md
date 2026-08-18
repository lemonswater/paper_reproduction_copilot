# 05. V4 LangGraph、Checkpoint 与 Memory

## 目标

把 V0-V3 的线性 CLI 流程改造成 LangGraph 状态机，并接入 checkpoint 支持中断恢复。

这是你项目里最应该讲清楚的 memory 阶段：

```text
State = 单次任务工作记忆
Checkpoint = 单个 thread 的持久化状态
Store / Long-term Memory = 跨 thread 的长期记忆，后期再做
```

## 什么时候做 memory

```text
V0-V3：
    只设计 State，并把中间结果写入 outputs。

V4：
    正式接入 LangGraph checkpoint。
    支持 thread_id、恢复任务、查看 state。

V7 之后：
    再考虑长期 memory/store。
```

## 本阶段要新增的文件

```text
app/graph.py
app/memory/checkpoint.py
```

## app/memory/checkpoint.py

开发阶段先用内存 checkpointer。注意：进程重启后会丢失；如果要跨进程恢复，再换 SQLite、Postgres 或 Redis。

```python
from langgraph.checkpoint.memory import InMemorySaver


# 创建开发阶段使用的内存型 checkpointer。
def build_checkpointer():
    return InMemorySaver()
```

## app/graph.py

```python
from langgraph.graph import END, START, StateGraph

from app.memory.checkpoint import build_checkpointer
from app.nodes.code_search_node import code_search_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.repo_scan_node import repo_scan_node
from app.state import ReproductionState


# 决定实验计划节点执行完成后图应该流向哪里。
def route_after_plan(state: ReproductionState) -> str:
    return END


# 组装并编译 V0-V3 节点构成的 LangGraph 工作流。
def build_graph():
    builder = StateGraph(ReproductionState)

    builder.add_node("paper_reader", paper_reader_node)
    builder.add_node("method_extractor", method_extractor_node)
    builder.add_node("repo_scan", repo_scan_node)
    builder.add_node("code_search", code_search_node)
    builder.add_node("mapping", mapping_node)
    builder.add_node("experiment_plan", experiment_plan_node)

    builder.add_edge(START, "paper_reader")
    builder.add_edge("paper_reader", "method_extractor")
    builder.add_edge("method_extractor", "repo_scan")
    builder.add_edge("repo_scan", "code_search")
    builder.add_edge("code_search", "mapping")
    builder.add_edge("mapping", "experiment_plan")
    builder.add_conditional_edges("experiment_plan", route_after_plan)

    return builder.compile(checkpointer=build_checkpointer())
```

## CLI 入口

```python
from app.graph import build_graph


# 运行带 checkpoint 的 LangGraph 流程，并绑定指定 thread_id。
@app.command()
def run_graph(
    paper_path: str,
    repo_path: str,
    thread_id: str = "demo-thread",
    goal: str = "复现论文 main result",
):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {
            "paper_path": paper_path,
            "repo_path": repo_path,
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

## 查看当前 State

```python
# 查看指定 thread_id 对应的持久化 state。
@app.command()
def show_state(thread_id: str = "demo-thread"):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    print(state)
```

## 恢复任务的关键点

使用同一个 `thread_id`：

```bash
python -m app.main run-graph "pdf/Point Spatio-Temporal Transformer Networks.pdf" /data/tianshaoqi24/P4Transformer/ --thread-id paper-001
python -m app.main show-state --thread-id paper-001
```

如果后续接入日志分支或 interrupt，恢复时也必须使用同一个 `thread_id`。

## 本阶段验收

你需要能讲清楚：

- 每个 node 读哪些 state 字段。
- 每个 node 写哪些 state 字段。
- `messages` 和 `state` 的区别。
- checkpoint 为什么属于短期 thread memory。
- long-term memory 为什么不在 MVP 阶段做。

## 参考官方文档

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph memory: https://docs.langchain.com/oss/python/langgraph/add-memory
