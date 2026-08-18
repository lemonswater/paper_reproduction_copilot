# 16. 闭环后第一阶段：Durable Checkpoint 与真正可恢复的 Resume

## 这一阶段的目标

前面你已经把端到端闭环补到了：

```text
paper -> repo -> mapping -> plan -> action -> approval -> executor -> debug -> final_report
```

但闭环跑通，不等于“真正可恢复”。

你当前项目还有一个非常关键的工程短板：

```text
checkpoint 还是内存型的
```

这会直接导致一个很典型的问题：

```text
run_graph 用一个 Python 进程执行
show_state / resume_review 又是另一个 Python 进程执行
虽然 thread_id 一样，但内存已经不是同一份了
所以状态接不住、resume 也不可靠
```

这也是你之前看到：

```text
graph finished
show_state 结果 values={}
```

这种现象背后的核心原因之一。

所以这一阶段的目标非常明确：

1. 把 `InMemorySaver` 升级成持久化的 SQLite checkpointer  
2. 让 `run_graph / show_state / resume_review` 真正共享同一份 checkpoint 数据  
3. 增加查看 checkpoint、删除 thread 历史的 CLI 能力  
4. 补一份最小但关键的“跨 graph 实例 resume”测试  

这一阶段做完后，你的项目会从：

```text
能在单进程里中断恢复
```

升级成：

```text
能跨命令、跨 graph 实例恢复
```

这一步非常关键，因为它会把你的 Agent 从“演示态工作流”推进到“更接近真实可用的工作流系统”。

---

## 先明确：这一阶段解决的到底是什么问题

你当前的 [app/memory/checkpoint.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/memory/checkpoint.py:1) 是：

```python
from langgraph.checkpoint.memory import InMemorySaver


def build_checkpointer():
    return InMemorySaver()
```

这段代码在“单进程开发调试”里是没问题的，但它有一个天然限制：

### `InMemorySaver` 的状态只活在当前 Python 进程里

也就是说：

- 你执行：

```bash
python -m app.main run-graph ...
```

这会启动一个 Python 进程。

- 然后你再执行：

```bash
python -m app.main show-state ...
```

这是第二个全新的 Python 进程。

第二个进程根本拿不到第一个进程的内存对象，所以即使：

- `thread_id` 一样
- graph 结构一样

也依然会出现：

```text
thread_id 对上了
但是 checkpoint 数据不在了
```

所以 Durable Checkpoint 的本质，不是“让 `show_state()` 好看一点”，而是：

```text
让状态落到持久化存储里
从而让不同命令、不同 graph 实例，也能接着同一个任务继续跑
```

---

## 这一阶段建议修改 / 新增的文件

```text
pyproject.toml
.gitignore
app/config.py
app/memory/checkpoint.py
app/main.py
tests/test_durable_checkpoint_resume.py
```

可选检查：

```text
app/state.py
```

因为你当前 [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1) 里还没有 `run_commands` 字段，但你的：

- `experiment_plan_node`
- `action_builder_node`
- `final_report_node`

都已经在使用 `run_commands` 了。

这不是 Durable Checkpoint 本身的核心，但如果这块状态字段没补齐，你后面测试 approval / resume 时，可能会误以为是 checkpoint 失效，实际上是 action 分支根本没触发。

---

## 一、先补依赖：安装 SQLite Checkpointer

### 为什么先做这一步

你当前 `pyproject.toml` 里只有：

- `langgraph`

但没有 SQLite checkpointer 的独立包。

根据官方包发布方式，SQLite checkpoint saver 是单独的包，而不是默认跟着 `langgraph` 一起进来。

### 建议修改 `pyproject.toml`

在 [pyproject.toml](/data/tianshaoqi24/agent/paper_reproduction_copilot/pyproject.toml:1) 的 `dependencies` 里加入：

```toml
[project]
name = "paper-reproduction-copilot"
version = "0.1.0"
description = "A LangGraph-based copilot for paper reproduction tasks."
requires-python = ">=3.10"
dependencies = [
    "langchain>=0.3",
    "langchain-openai>=0.2",
    "langgraph>=0.2",

    # 新增：
    # LangGraph 官方提供的 SQLite checkpoint saver。
    # 它会把 graph 的 checkpoint 写到 sqlite 文件中，
    # 从而让 run_graph / show_state / resume_review 可以跨进程共享状态。
    "langgraph-checkpoint-sqlite>=3",

    "pydantic>=2",
    "typer>=0.12",
    "rich>=13",
    "pymupdf>=1.24",
    "python-dotenv>=1.0",
]
```

### 安装命令

如果你是直接在当前环境里装，可以执行：

```bash
python -m pip install langgraph-checkpoint-sqlite
```

如果你使用的是项目依赖同步方式，就按你项目当前的依赖管理方式重新安装。

### 一个很重要的提醒

一定要确认你安装包时用的 `python`，和你执行：

```bash
python -m app.main ...
```

用的是同一个环境。

否则很容易出现：

```text
命令能运行
但 import langgraph.checkpoint.sqlite 时报错
```

这不是代码问题，而是环境不一致。

---

## 二、补配置：把 checkpoint 数据库路径显式写进 Settings

### 为什么建议单独给 checkpoint 建目录

不建议把 checkpoint 数据库放在 `outputs/` 里。

原因很简单：

- `outputs/` 通常是“产物目录”
- 很多人会习惯性删除 `outputs/` 重新跑
- 如果 checkpoint 也在里面，就会把恢复状态一起删掉

所以更稳的做法是单独用一个目录，比如：

```text
checkpoints/langgraph.sqlite
```

### 建议修改 `app/config.py`

把 [app/config.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/config.py:1) 改成下面这种形式：

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

    # 业务产物目录：
    # 用来存 paper_summary.json、repo_map.json、final_report.md 等结果。
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))

    # 新增：
    # checkpoint 数据库单独放在 checkpoints/ 下，
    # 避免你清理 outputs/ 时把恢复状态一起删掉。
    checkpoint_db_path: Path = Path(
        os.getenv("CHECKPOINT_DB_PATH", "checkpoints/langgraph.sqlite")
    )

    max_steps: int = int(os.getenv("MAX_STEPS", "20"))


settings = Settings()

# 确保业务产物目录存在。
settings.output_dir.mkdir(parents=True, exist_ok=True)

# 确保 checkpoint 数据库所在目录存在。
# 注意这里只创建父目录，不会提前创建空 sqlite 文件。
settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
```

### 建议在 `.env` 里补一项

```dotenv
CHECKPOINT_DB_PATH=checkpoints/langgraph.sqlite
```

### 再补一个安全提醒

LangGraph 官方对 SQLite checkpointer 还给了一个安全建议：

```dotenv
LANGGRAPH_STRICT_MSGPACK=true
```

这一项建议你也加到 `.env` 里。

它的作用不是“让 resume 更好用”，而是限制 checkpoint 反序列化时的风险，属于安全加固项。

---

## 三、补 `.gitignore`：不要把 checkpoint 数据库提交进仓库

### 为什么要做这一步

checkpoint 数据库属于运行时状态，不属于源码，也不属于最终业务产物。

如果不忽略它，很容易出现：

- sqlite 文件被误提交
- git diff 里出现一堆没意义的二进制变化
- 任务历史混进版本管理

### 建议修改 `.gitignore`

当前 [.gitignore](/data/tianshaoqi24/agent/paper_reproduction_copilot/.gitignore:1) 几乎还是空的，建议至少补成：

```gitignore
.env
checkpoints/
outputs/
a_implementation_guides/
```

### 如果你不想忽略整个 `outputs/`

也可以只忽略 checkpoint：

```gitignore
.env
checkpoints/
a_implementation_guides/
```

这个看你自己希望不希望把 `outputs/` 当演示产物保留下来。

---

## 四、核心修改：把 `InMemorySaver` 替换成 `SqliteSaver`

这是这一阶段最核心的代码变更。

### 先说一个很容易踩坑的点

官方文档里经常会写：

```python
with SqliteSaver.from_conn_string(":memory:") as checkpointer:
    ...
```

这在“局部演示代码”里很好用，但你这里不能直接机械照抄成：

```python
def build_checkpointer():
    return SqliteSaver.from_conn_string("checkpoints/langgraph.sqlite")
```

因为 `from_conn_string(...)` 返回的是**上下文管理器**风格的对象创建方式。

如果你没有正确管理它的生命周期，就很容易出现两类问题：

1. 你返回的不是实际 saver，而是 context manager  
2. 你在函数里 `with` 完就返回，连接可能立刻关闭  

所以对你当前这种项目结构，最稳的写法是：

```text
自己显式创建 sqlite3.Connection
再传给 SqliteSaver
```

### 建议修改 `app/memory/checkpoint.py`

把 [app/memory/checkpoint.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/memory/checkpoint.py:1) 改成下面这种形式：

```python
import atexit
import sqlite3
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import settings


# 这两个模块级变量的作用是：
# 1. 在同一个 Python 进程里复用同一条 sqlite 连接；
# 2. 避免每次 build_graph() 都新建连接；
# 3. 同时保证 run_graph / show_state / resume_review 这些命令
#    只要指向同一个 sqlite 文件，就能跨进程共享 checkpoint 数据。
_conn: Optional[sqlite3.Connection] = None
_checkpointer: Optional[SqliteSaver] = None


def build_checkpointer() -> SqliteSaver:
    """
    构建一个可持久化的 LangGraph checkpointer。

    为什么不用 InMemorySaver：
    - InMemorySaver 只在当前 Python 进程里有效；
    - CLI 的 run_graph / show_state / resume_review 往往是不同进程；
    - 所以需要把 checkpoint 落到 sqlite 文件里。

    为什么不用直接 return SqliteSaver.from_conn_string(...):
    - from_conn_string() 更适合 with 语句管理生命周期；
    - 当前项目更适合显式持有 sqlite3.Connection；
    - 这样更容易做模块级复用，也更容易调试。
    """

    global _conn, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    # 确保目录存在。
    settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)

    # check_same_thread=False 是官方示例中也会用到的模式。
    # SqliteSaver 内部有锁，适合这种轻量、同步、单机场景。
    _conn = sqlite3.connect(
        settings.checkpoint_db_path,
        check_same_thread=False,
    )

    _checkpointer = SqliteSaver(_conn)
    return _checkpointer


def close_checkpointer() -> None:
    """
    在进程退出前尽量关闭 sqlite 连接。
    对于当前 CLI 项目，这不是绝对必须，
    但这样做更稳，也更符合长期维护习惯。
    """

    global _conn, _checkpointer

    if _conn is not None:
        _conn.close()

    _conn = None
    _checkpointer = None


# 注册进程退出时的清理函数。
atexit.register(close_checkpointer)
```

### 这一版代码的关键点

#### 1. 用模块级单例复用连接

这样同一个进程里：

- `build_graph()`
- `show_state()`
- 其他调试逻辑

不会反复新建连接。

#### 2. 跨进程共享依赖的是“同一个 sqlite 文件”

也就是说真正让恢复成立的关键不是：

```text
同一个 Python 对象
```

而是：

```text
同一个 CHECKPOINT_DB_PATH
+ 同一个 thread_id
```

#### 3. `SqliteSaver` 更适合本地开发和轻量部署

这一步是 Durable Checkpoint 的第一版落地方案。

如果后面你想继续往生产化靠，可以再升级到：

- Postgres checkpointer

但对你现在这个项目阶段来说，SQLite 是最合适的。

---

## 五、`app/main.py`：把“恢复”真正做成可操作的 CLI

你当前 [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:1) 里其实已经有：

- `run_graph`
- `show_state`
- `resume_review`

这很好，说明接口骨架已经在了。

这一阶段建议你继续做三件事：

1. 统一默认 `thread_id` 的命名  
2. 增加 `list_checkpoints` 命令  
3. 增加 `reset_thread` 命令  

### 为什么要统一默认 `thread_id`

你当前是：

- `run_graph`: `"demo_thread"`
- `show_state`: `"demo-thread"`

一个是下划线，一个是中划线。

这虽然不是大 bug，但在调试 checkpoint 时特别容易把人绕进去。

建议统一成同一个值，例如：

```text
demo_thread
```

### 建议修改后的 `app/main.py`

下面这份代码不是要求你逐字照抄全文件，而是把 Durable Resume 相关部分整理成一版更完整的参考实现。

```python
from pathlib import Path

import typer
from langgraph.types import Command
from rich import print

from app.graph import build_graph
from app.memory.checkpoint import build_checkpointer
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
    """
    跑整条图工作流。

    Durable checkpoint 生效的关键条件：
    1. 使用同一个 CHECKPOINT_DB_PATH；
    2. 使用同一个 thread_id。
    """

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
    """
    查看某个 thread_id 当前保存的 graph 状态。

    在 Durable Checkpoint 做好后，这个命令应该能够在新的 Python 进程里
    看到之前 run_graph 保存下来的状态，而不是空壳。
    """

    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    print(snapshot)


@app.command()
def resume_review(
    thread_id: str,
    decision: str = "approved",
    feedback: str | None = None,
):
    """
    恢复一个因为 human_review_node.interrupt() 而暂停的任务。
    """

    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke(
        Command(resume={"decision": decision, "feedback": feedback}),
        config=config,
    )

    print("[green]resume finished[/green]")
    print(result)


@app.command("list-checkpoints")
def list_checkpoints(thread_id: str, limit: int = 5):
    """
    直接列出某个 thread_id 的 checkpoint 历史。

    这个命令非常适合排查：
    - 有没有真的写入 sqlite
    - thread_id 有没有写错
    - checkpoint_id 是否在递增
    """

    checkpointer = build_checkpointer()
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


@app.command("reset-thread")
def reset_thread(thread_id: str):
    """
    删除某个 thread_id 的全部 checkpoint 历史。

    适合在你想从头重新跑、又不想手动删除整个 sqlite 文件时使用。
    """

    checkpointer = build_checkpointer()
    checkpointer.delete_thread(thread_id)
    print(f"[yellow]deleted checkpoints for thread_id={thread_id}[/yellow]")


if __name__ == "__main__":
    app()
```

### 为什么 `list-checkpoints` 很有用

很多时候你以为“resume 不工作”，实际上问题根本不在 resume，而在更前面：

- checkpoint 没落盘
- thread_id 写错
- 任务根本没有 interrupt

这时如果有 `list-checkpoints`，排查会快很多。

---

## 六、关于 `app/graph.py`：这一阶段通常不需要大改

你当前 [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1) 最关键的一行是：

```python
return builder.compile(checkpointer=build_checkpointer())
```

这一行本身是对的。

Durable Checkpoint 做好的关键在于：

- `build_checkpointer()` 不再返回 `InMemorySaver`
- 而是返回绑定到 sqlite 文件的 `SqliteSaver`

也就是说，这一阶段通常不需要大改 graph 结构，重点在存储后端。

### 但这里有一个实战提醒

要想验证 resume 生效，你的 graph 必须真的走到：

```text
human_review_node -> interrupt()
```

如果图根本没中断，那你后面执行：

```bash
python -m app.main resume-review ...
```

当然也不会有可恢复的内容。

所以你在手工验证前，要先确认：

1. `experiment_plan_node` 确实把 `run_commands` 写回 state  
2. `action_builder_node` 确实构造出了 `pending_action`  
3. `risk_check_node` 返回的是 `requires_approval=True` 而不是 blocked  
4. 图真的进入 `human_review_node`  

其中第 1 点你当前仓库已经在 [app/nodes/experiment_plan_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/experiment_plan_node.py:1) 里做了：

```python
"run_commands": [cmd.model_dump() for cmd in plan.run_commands]
```

但你的 [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1) 还没把 `run_commands` 字段补进去，所以建议你顺手也补上。

### `state.py` 建议补上的字段

```python
run_commands: list[dict[str, Any]]
```

如果你想顺便给后面做更强的任务管理铺路，也可以继续加：

```python
current_stage: Optional[str]
run_id: Optional[str]
created_at: Optional[str]
updated_at: Optional[str]
```

但这些不是本阶段必须项。

---

## 七、测试怎么做：不要一上来就跑完整项目图

### 为什么不建议一开始就测完整项目图

完整项目图里会包含：

- LLM 调用
- PDF 读取
- repo 扫描
- approval 分支
- executor 分支

这会让你很难判断：

```text
到底是 Durable Checkpoint 有问题
还是别的节点先出问题了
```

所以这一阶段建议你新增一份**最小但关键**的测试：

> 用一个极小的 LangGraph，在第一次 graph 实例中触发 `interrupt()`，再在第二次 graph 实例中用同一个 sqlite 文件和同一个 `thread_id` 做 `resume`。

如果这个测试通过，说明：

- 持久化 checkpointer 本身是通的
- 跨 graph 实例恢复是成立的

这就是这一阶段最重要的技术验证。

---

## 八、建议新增测试：`tests/test_durable_checkpoint_resume.py`

下面这份测试代码非常值得你自己手打一遍，因为它会让你真正理解：

```text
LangGraph 的 durable resume 到底在恢复什么
```

### 建议新文件完整代码

```python
import sqlite3
from pathlib import Path
from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


# 如果当前测试环境里还没安装 sqlite checkpointer，
# 这里会直接把测试标记为 skip，而不是报一大串 import error。
SqliteSaver = pytest.importorskip("langgraph.checkpoint.sqlite").SqliteSaver


class ReviewState(TypedDict, total=False):
    decision: str
    result: str


def review_node(state: ReviewState) -> ReviewState:
    """
    一个最小的 interrupt 节点。
    第一次运行到这里会暂停；
    恢复时会从 interrupt 的返回值里拿到 decision。
    """

    response = interrupt({"message": "approve this action?"})

    if isinstance(response, dict):
        decision = response.get("decision", "rejected")
    else:
        decision = str(response)

    return {"decision": decision}


def finish_node(state: ReviewState) -> ReviewState:
    """
    根据 decision 产出最终结果。
    """

    if state.get("decision") == "approved":
        return {"result": "done"}
    return {"result": "blocked"}


def build_test_graph(db_path: Path):
    """
    每次都创建新的 graph 实例和新的 sqlite 连接，
    用来模拟“不同命令 / 不同进程重新打开同一个 checkpoint 文件”。
    """

    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)

    builder = StateGraph(ReviewState)
    builder.add_node("review", review_node)
    builder.add_node("finish", finish_node)
    builder.add_edge(START, "review")
    builder.add_edge("review", "finish")
    builder.add_edge("finish", END)

    graph = builder.compile(checkpointer=memory)
    return graph, conn


def test_sqlite_checkpoint_supports_resume_across_graph_instances(tmp_path: Path) -> None:
    """
    这个测试验证 Durable Checkpoint 的关键能力：
    - 第一次 graph 实例触发 interrupt
    - 第二次 graph 实例从同一个 sqlite 文件恢复
    - resume 后可以继续完成流程
    """

    db_path = tmp_path / "langgraph.sqlite"
    config = {"configurable": {"thread_id": "thread-001"}}

    # 第一次 graph：触发 interrupt，把 checkpoint 写进 sqlite。
    graph1, conn1 = build_test_graph(db_path)
    try:
        graph1.invoke({}, config=config)
    finally:
        conn1.close()

    # 第二次 graph：模拟“新的命令 / 新的进程”重新打开同一个 sqlite 文件。
    graph2, conn2 = build_test_graph(db_path)
    try:
        result = graph2.invoke(
            Command(resume={"decision": "approved"}),
            config=config,
        )
    finally:
        conn2.close()

    assert result["decision"] == "approved"
    assert result["result"] == "done"
```

### 这份测试为什么重要

它验证的不是：

- 你的论文阅读链
- 你的 repo map
- 你的 executor

而是更底层、更关键的一件事：

```text
checkpoint 的持久化和恢复机制是否成立
```

只要这份测试通过，你后面再排完整项目里的 resume 问题时，心里就会很有底。

---

## 九、手工验证怎么做

### 验证前先确认这几个前置条件

#### 1. `action_builder` 链路真的能产出 `pending_action`

否则图不会进入 approval 分支。

#### 2. 该动作不是 blocked

如果命令被风控判成 blocked，你的 [app/nodes/risk_check_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/risk_check_node.py:1) 会返回：

- `requires_approval=False`
- `error=...`

这时图也不会走到 `human_review_node` 的 `interrupt()`。

#### 3. 使用同一个 `thread_id`

这是最容易因为手滑写错导致误判的地方。

#### 4. 使用同一个 `CHECKPOINT_DB_PATH`

如果你改了 `.env`，记得确认命令运行时真的读到了新的路径。

---

## 十、建议的手工验证命令

下面是一套建议的验证方式。

### 第一步：先删干净旧 thread

如果你已经实现了 `reset-thread`：

```bash
python -m app.main reset-thread durable-001
```

### 第二步：启动图，让它停在 `human_review`

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer/ \
  --thread-id durable-001
```

如果前置链路正常，而且 `pending_action` 触发了审批，这一步应该会在 `interrupt()` 处停住。

### 第三步：查看当前 state

```bash
python -m app.main show-state durable-001
```

这时你希望看到的不是空壳，而是带有：

- `values`
- `next`
- `interrupts`

等信息的 snapshot。

### 第四步：查看 checkpoint 历史

```bash
python -m app.main list-checkpoints durable-001
```

如果这里能列出 checkpoint，说明 sqlite 落盘至少是通的。

### 第五步：恢复审批

```bash
python -m app.main resume-review durable-001 --decision approved
```

如果你还想附带说明：

```bash
python -m app.main resume-review durable-001 --decision revise --feedback "先检查 batch size"
```

### 第六步：再看一次 state

```bash
python -m app.main show-state durable-001
```

这一步的目的是确认：

- 图是否继续往后推进了
- `user_approval` / `human_feedback` 是否被写回 state
- 是否进入了 executor 或后续分支

---

## 十一、这一阶段最常见的报错与排查思路

### 1. `ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'`

#### 原因

- 依赖没装
- 或者装在了错误的 Python 环境里

#### 解决

确认执行下面两件事用的是同一个环境：

```bash
python -m pip install langgraph-checkpoint-sqlite
python -m app.main version
```

---

### 2. `show_state` 还是空的

#### 可能原因

1. 你仍然在用 `InMemorySaver`  
2. `CHECKPOINT_DB_PATH` 没生效  
3. `thread_id` 不一致  
4. 图没有真的写入 checkpoint  
5. 你看的 thread 历史被你提前删掉了  

#### 排查顺序

建议按这个顺序查：

1. 打开 [app/memory/checkpoint.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/memory/checkpoint.py:1)，确认已经不是 `InMemorySaver`
2. 执行 `list-checkpoints`
3. 检查 `run_graph` 和 `show_state` 用的是不是同一个 `thread_id`
4. 检查 sqlite 文件是否真的生成了

---

### 3. `resume-review` 没效果

#### 可能原因

1. 图根本没 interrupt  
2. 你恢复的不是那个 `thread_id`  
3. 上次运行已经走到 `END` 了  
4. 任务在 approval 之前就已经分支结束了  

#### 排查建议

先不要急着看大图，先看：

- `show_state`
- `list-checkpoints`

如果 `interrupts` 里根本没有待恢复信息，那就说明问题不在 durable checkpoint，而在图根本没停在 review。

---

### 4. sqlite 文件有了，但还是恢复失败

#### 可能原因

- graph 结构变了
- 你改了 node 名称或路由
- 同一个 `thread_id` 对应的是旧结构写下来的 checkpoint

#### 解决思路

这种情况下建议：

```bash
python -m app.main reset-thread <thread_id>
```

然后重新跑一遍。

也就是说：

```text
checkpoint 是和 graph 结构强相关的
```

在你频繁改图结构的开发阶段，适度清理旧 thread 是正常操作。

---

## 十二、这一阶段完成后的验收标准

我建议你把验收标准定得很具体，不要只写“感觉能恢复”。

至少做到下面 4 条：

### 1. `run_graph`、`show_state`、`resume_review` 使用不同命令执行时，能够共享状态

这说明你已经不再依赖内存型 saver。

### 2. `show_state` 不再只是空壳

至少在 interrupt 后能看到有效 snapshot。

### 3. `list-checkpoints` 能看到某个 `thread_id` 的历史记录

这说明 checkpoint 真的写入了 sqlite。

### 4. `tests/test_durable_checkpoint_resume.py` 能通过

这说明 durable resume 的底层机制是成立的。

---

## 十三、这一阶段做完后，下一步最自然接什么

当 Durable Checkpoint 做完后，最自然的下一步通常有两个方向：

### 方向一：更强的任务管理

例如：

- `list-runs`
- `show-run`
- `show-artifacts`
- `show-last-interrupt`

让 thread 不只是“能恢复”，还能“更好管理”。

### 方向二：把失败后的 repair loop 接上

也就是从：

```text
executor failed -> log_debug -> final_report
```

进一步升级成：

```text
executor failed
  -> log_debug
  -> repair proposal
  -> human review
  -> rerun
```

但无论后面走哪条路线，Durable Checkpoint 都会是非常重要的底座。

---

## 十四、最后的整体理解

这一阶段的重点，不只是“把 `InMemorySaver` 换成 `SqliteSaver`”。

更重要的是建立下面这个 Agent 工程思维：

```text
Agent 不是一次性函数调用
而是有状态、有中断、有恢复、有副作用边界的流程系统
```

当你把这一步做完之后，这个项目就会更明显地从：

```text
能跑通的课程式实现
```

变成：

```text
更像真实工作流系统的 Agent Prototype
```

这一步非常值得认真做扎实。
