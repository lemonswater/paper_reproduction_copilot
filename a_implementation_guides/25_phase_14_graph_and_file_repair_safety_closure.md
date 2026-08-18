# 25. Phase 14：主图与文件修复安全收口

这一阶段不增加新的 Agent 业务能力，而是把 Phase 13 已实现的文件修复链从：

```text
主体流程能够运行
```

收口为：

```text
失败路由唯一
验证结论准确
审批绑定不可伪造
仓库修改互斥
崩溃后能够幂等恢复
临时 worktree 可审计、可清理
```

根据最新的 `agent_project_analysis_and_technical_roadmap.md`，这是当前优先级最高的 P0 阶段。

在本阶段全部验收通过前，继续保持：

```dotenv
ENABLE_FILE_REPAIR=false
```

---

## 一、为什么 Phase 13 之后还需要安全收口

Phase 13 已经建立了很好的安全骨架：

- LLM 只输出结构化 replacement proposal。
- 程序确定性生成 unified diff。
- patch 绑定原文件和目标文件 SHA-256。
- 第一次人工审批绑定 patch hash。
- patch 先在隔离 Git worktree 中验证。
- 第二次人工审批绑定 verification hash。
- 应用后重新计算 command action hash。

但当前仍有六类 P0 风险。

### 1. `log_debug` 有两个出口

当前主图同时存在：

```python
builder.add_conditional_edges("log_debug", route_after_log_debug)
builder.add_edge("log_debug", "final_report")
```

失败后可能同时调度 `repair_planner` 和 `final_report`，触发：

```text
INVALID_CONCURRENT_GRAPH_UPDATE
```

而且 `route_after_log_debug()` 和 `route_after_repair_planner()` 当前各定义了两次，旧定义会被 Python 静默覆盖。

### 2. `passed` 的含义过强

当前 targeted tests 可以是 `skipped`。只要 apply、hash 和语法没有失败，报告仍可能写 `passed`。

这只能证明 patch 在结构上可应用，不能证明程序行为正确。

### 3. Hash 没有在边界重新计算

如果 verification report 内容被修改，但旧 `verification_sha256` 字段没变，单纯比较两个旧字段无法发现篡改。

### 4. Patch apply 不是崩溃幂等的

```text
git apply 成功
    ↓
Python 进程突然退出
    ↓
LangGraph 尚未保存 checkpoint
```

恢复后节点会重放。系统必须识别仓库已经处于 exact-after 状态，而不是重复 apply 或把它误判为未知 dirty tree。

### 5. 两个 run 可以同时修改同一仓库

Checkpoint 隔离了 thread state，却没有隔离共享的外部 Git 仓库。两个 run 可能同时进入 `patch_apply`。

### 6. 复用 worktree 只检查目标文件

目标文件 after hash 正确，不代表 worktree 中没有其他 tracked 修改。行为测试可能运行在被污染的代码上。

---

## 二、本阶段范围

本阶段要完成：

1. 清理重复路由函数和 `log_debug` 无条件边。
2. 为条件路由增加 `Literal` 返回类型和显式 `path_map`。
3. 增加编译图拓扑测试和真实条件路由运行测试。
4. 重定义 patch verification 状态。
5. 在 promotion 和 apply 边界重新计算 verification hash。
6. apply 前独立校验 report、bundle、promotion 和 execution profile。
7. 复用 worktree 时检查完整 tracked diff。
8. 增加跨 run 的 repository lock。
9. 增加 patch application write-ahead journal。
10. 支持 apply 后、checkpoint 前崩溃的幂等恢复。
11. 增加受控 worktree 清理入口。
12. 用故障注入和并发测试验证边界。

本阶段明确不做：

```text
扩大可修改文件类型
创建、删除或重命名文件
自动批准 patch
自动提交、push 或创建 PR
自动评定论文结果指标
引入 Docker/Podman 沙箱
全面迁移所有节点的 outputs 目录
```

统一异常模型和所有 Artifact 直接写 `run_dir` 属于 Phase 15。

---

## 三、收口后的流程

```text
log_debug
    ↓ 唯一条件出口
repair_planner
    ├── command repair
    ├── file repair
    └── final report

file repair proposal
    ↓
patch bundle + patch hash
    ↓
patch review
    ↓
isolated worktree
    ├── apply/hash/syntax only -> structurally_valid -> 停止
    ├── behavioral test passed -> behaviorally_verified
    └── any check failed -> failed/blocked
                    ↓
            promotion review
                    ↓
重新计算 verification hash
重新校验 patch/profile/id
                    ↓
获取 repository lock
                    ↓
journal: prepared -> applying
                    ↓
git apply
                    ↓
exact-after-hash + exact-diff
                    ↓
journal: applied
                    ↓
LangGraph checkpoint
```

如果在 `git apply` 后崩溃，恢复时使用：

```text
journal + exact-after-hash + exact tracked diff
```

识别“已经应用”，而不是重复执行。

---

## 四、涉及文件

建议新增：

```text
app/tools/repository_lock_tools.py
app/tools/patch_journal_tools.py

tests/conftest.py
tests/test_compiled_graph_routes.py
tests/test_patch_verification_semantics.py
tests/test_patch_authorization_boundaries.py
tests/test_patch_application_recovery.py
tests/test_repository_lock.py
tests/test_patch_worktree_cleanup.py
```

建议修改：

```text
.env.example
app/config.py
app/schemas.py
app/graph.py
app/main.py
app/tools/patch_tools.py
app/nodes/patch_verifier_node.py
app/nodes/patch_promotion_review_node.py
app/nodes/patch_apply_node.py
app/tools/artifact_tools.py
app/nodes/final_report_node.py
```

只需检查、通常无需修改：

```text
app/state.py
```

Phase 13 已经加入 `patch_verification_report`、`patch_application_record`、`file_repair_attempt_count` 等顶层状态。本阶段新增的 journal、lock key 和 recovered 信息都保存在 `patch_application_record` 内，不需要再增加平行的顶层字段。

### 4.1 代码片段使用规则

为了避免把教程中的局部片段误当成完整文件，本章统一使用下面三种标记：

- **完整文件**：代码块包含该文件需要的 import、函数和返回值，可以整体对照。
- **完整函数**：只替换同名函数，文件中的其他函数保持不变。
- **插入片段**：明确写出插入位置；不要删除位置前后的原代码。

如果后文同时给出“算法片段”和“完整文件参考”，应以完整文件参考为准。修改前建议先执行：

```bash
rg -n "^(def|class) " app/graph.py app/nodes app/tools/patch_tools.py
```

这样可以确认同名函数是否已经存在，避免把新实现追加到旧实现后面形成重复定义。

`app/tools/patch_tools.py` 较长，建议按下面顺序落位：

| 位置 | 函数 |
|---|---|
| 原 `_run_git()` 后 | `_git_output()`、`get_changed_tracked_paths()`、`ensure_no_staged_changes()` |
| 原 worktree helper 区域 | `compute_worktree_diff_hash()`、`validate_worktree_matches_patch()` |
| 原 `verify_patch_in_worktree()` 前后 | 替换 `summarize_patch_verification()`，并按第 9、10 节修改验证函数尾部 |
| 原 `compute_verification_hash()` 后 | `validate_verification_hash()`、`validate_patch_promotion_authorization()` |
| 原 source apply 区域 | `inspect_source_patch_state()`、`_application_record()`、新版 `apply_verified_patch_to_source()` |
| 文件末尾或 worktree helper 后 | `validate_patch_worktree_path()`、`remove_patch_worktree()` |

其中 `apply_verified_patch_to_source()` 是**替换旧函数**，不能保留 Phase 13 的旧实现；其余函数如果已存在，则替换同名函数而不是再次追加。

---

## 五、冻结功能并记录测试基线

先确认 `.env`：

```dotenv
ENABLE_FILE_REPAIR=false
```

运行：

```bash
python -m pytest -q
```

路线图撰写时的基线是：

```text
80 passed
```

如果本地数量已经变化，以实际结果为准。这一步只用于建立回归基线，不代表整条 Graph 已经安全。

---

## 六、清理 Graph 路由

修改：

```text
app/graph.py
```

### 6.1 删除重复函数

先检查定义次数：

```bash
rg -n "^def route_after_(log_debug|repair_planner)" app/graph.py
```

每个函数最终只能出现一次。保留 6.2 给出的 command/file 独立预算版本，完整删除旧函数的函数头、docstring 和函数体。不要依赖“后定义覆盖前定义”。

### 6.2 给路由增加 Literal 返回类型

顶部增加：

```python
from typing import Literal
```

修改路由：

```python
def route_after_log_debug(
    state: ReproductionState,
) -> Literal["repair_planner", "final_report"]:
    command_attempts = int(state.get("repair_attempt_count", 0))
    file_attempts = int(state.get("file_repair_attempt_count", 0))

    command_budget_available = (
        command_attempts < settings.max_repair_attempts
    )
    file_budget_available = (
        settings.enable_file_repair
        and file_attempts < settings.max_file_repair_attempts
    )

    if command_budget_available or file_budget_available:
        return "repair_planner"
    return "final_report"


def route_after_repair_planner(
    state: ReproductionState,
) -> Literal[
    "repair_action_builder",
    "file_repair_planner",
    "final_report",
]:
    proposal = state.get("repair_proposal") or {}

    command_budget_available = (
        int(state.get("repair_attempt_count", 0))
        < settings.max_repair_attempts
    )
    if (
        command_budget_available
        and proposal.get("kind") == "edit_command"
        and proposal.get("repaired_command")
    ):
        return "repair_action_builder"

    file_budget_available = (
        settings.enable_file_repair
        and int(state.get("file_repair_attempt_count", 0))
        < settings.max_file_repair_attempts
    )
    if (
        file_budget_available
        and proposal.get("kind") == "manual_only"
        and (state.get("debug_report") or {}).get("related_files")
    ):
        return "file_repair_planner"

    return "final_report"
```

其他路由同样声明有限返回集合，例如：

```python
def route_after_patch_verifier(
    state: ReproductionState,
) -> Literal["patch_promotion_review", "final_report"]:
    report = state.get("patch_verification_report") or {}
    if (
        state.get("patch_verification_passed")
        and report.get("status") == "behaviorally_verified"
        and report.get("promotion_allowed") is True
    ):
        return "patch_promotion_review"
    return "final_report"
```

### 6.3 为条件边增加显式 path_map

把隐式注册改成：

```python
builder.add_conditional_edges(
    "log_debug",
    route_after_log_debug,
    {
        "repair_planner": "repair_planner",
        "final_report": "final_report",
    },
)

builder.add_conditional_edges(
    "repair_planner",
    route_after_repair_planner,
    {
        "repair_action_builder": "repair_action_builder",
        "file_repair_planner": "file_repair_planner",
        "final_report": "final_report",
    },
)

builder.add_conditional_edges(
    "patch_verifier",
    route_after_patch_verifier,
    {
        "patch_promotion_review": "patch_promotion_review",
        "final_report": "final_report",
    },
)
```

本文件所有条件边的完整注册见 6.6。`Literal` 帮助类型检查，`path_map` 明确运行时允许目标，不能只修改上面三个示例。

### 6.4 删除错误的无条件边

必须删除：

```python
builder.add_edge("log_debug", "final_report")
```

正确的结尾边仍是：

```python
builder.add_edge("final_report", "run_manifest")
builder.add_edge("run_manifest", END)
```

### 6.5 允许测试注入内存 Checkpointer

把 `build_graph()` 改为接收仅限关键字的 `checkpointer` 参数，并在函数结尾选择测试注入值或生产默认值。不要只替换函数尾部，完整函数见 6.6。

测试时使用：

```python
from langgraph.checkpoint.memory import MemorySaver

graph = build_graph(checkpointer=MemorySaver())
```

避免污染真实 SQLite checkpoint。

### 6.6 `build_graph()` 完整函数

下面是修改后的完整函数。它包含全部节点、固定边、条件边和 `path_map`；`app/graph.py` 顶部的 import 与 6.2 中的路由函数放在它前面。


```python
def build_graph(*, checkpointer=None):
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
    builder.add_node("file_repair_planner", file_repair_planner_node)
    builder.add_node("patch_builder", patch_builder_node)
    builder.add_node("patch_review", patch_review_node)
    builder.add_node("patch_verifier", patch_verifier_node)
    builder.add_node("patch_promotion_review", patch_promotion_review_node)
    builder.add_node("patch_apply", patch_apply_node)

    builder.add_edge(START, "run_context")
    builder.add_edge("run_context", "paper_reader")
    builder.add_edge("paper_reader", "method_extractor")
    builder.add_edge("method_extractor", "repo_scan")
    builder.add_edge("repo_scan", "code_search")
    builder.add_edge("code_search", "mapping")
    builder.add_edge("mapping", "experiment_plan")
    builder.add_edge("experiment_plan", "command_selection")
    builder.add_edge("command_selection", "action_builder")

    builder.add_conditional_edges(
        "action_builder",
        route_after_action_builder,
        {
            "risk_check": "risk_check",
            "log_debug": "log_debug",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "risk_check",
        route_after_risk_check,
        {
            "final_report": "final_report",
            "human_review": "human_review",
            "preflight_check": "preflight_check",
        },
    )
    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "preflight_check": "preflight_check",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "preflight_check",
        route_after_preflight,
        {
            "smoke_test": "smoke_test",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "smoke_test",
        route_after_smoke_test,
        {
            "executor": "executor",
            "log_debug": "log_debug",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "log_debug": "log_debug",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "log_debug",
        route_after_log_debug,
        {
            "repair_planner": "repair_planner",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "repair_planner",
        route_after_repair_planner,
        {
            "repair_action_builder": "repair_action_builder",
            "file_repair_planner": "file_repair_planner",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "repair_action_builder",
        route_after_repair_action_builder,
        {
            "risk_check": "risk_check",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "file_repair_planner",
        route_after_file_repair_planner,
        {
            "patch_builder": "patch_builder",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_builder",
        route_after_patch_builder,
        {
            "patch_review": "patch_review",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_review",
        route_after_patch_review,
        {
            "patch_verifier": "patch_verifier",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_verifier",
        route_after_patch_verifier,
        {
            "patch_promotion_review": "patch_promotion_review",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_promotion_review",
        route_after_patch_promotion_review,
        {
            "patch_apply": "patch_apply",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_apply",
        route_after_patch_apply,
        {
            "risk_check": "risk_check",
            "final_report": "final_report",
        },
    )

    builder.add_edge("final_report", "run_manifest")
    builder.add_edge("run_manifest", END)

    selected_checkpointer = (
        checkpointer
        if checkpointer is not None
        else build_checkpointer()
    )
    return builder.compile(checkpointer=selected_checkpointer)
```

修改后再检查一次：

```bash
rg -n "^def route_after_|add_conditional_edges|add_edge" app/graph.py
```


---

## 七、增加编译图级路由测试

新增：

```text
tests/test_compiled_graph_routes.py
```

### 7.1 检查生产编译图拓扑

```python
import ast
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.graph import build_graph


def test_route_functions_are_not_defined_twice():
    graph_source = Path("app/graph.py").read_text(encoding="utf-8")
    module = ast.parse(graph_source)
    function_names = [
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    assert function_names.count("route_after_log_debug") == 1
    assert function_names.count("route_after_repair_planner") == 1


def test_compiled_graph_has_no_unconditional_log_debug_edge():
    graph = build_graph(checkpointer=MemorySaver())
    drawable = graph.get_graph()
    log_debug_edges = [
        edge for edge in drawable.edges if edge.source == "log_debug"
    ]

    assert {edge.target for edge in log_debug_edges} == {
        "repair_planner",
        "final_report",
    }
    assert all(edge.conditional for edge in log_debug_edges)
```

不同 LangGraph 小版本的可视化 `Edge` 字段可能不同。如果没有 `conditional` 属性，先在 Debug Console 查看：

```python
build_graph(checkpointer=MemorySaver()).get_graph().edges
```

按真实结构调整断言，但必须保留“没有额外无条件边”的目标。

### 7.2 用真实 StateGraph 执行三条分支

```python
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from app.graph import (
    route_after_log_debug,
    route_after_repair_planner,
)


class RouteHarnessState(TypedDict, total=False):
    repair_attempt_count: int
    file_repair_attempt_count: int
    repair_proposal: dict
    debug_report: dict
    visited: Annotated[list[str], operator.add]


def _mark(name: str):
    def node(state: RouteHarnessState) -> dict:
        return {"visited": [name]}
    return node


def _build_failure_route_harness():
    builder = StateGraph(RouteHarnessState)
    builder.add_node("log_debug", _mark("log_debug"))
    builder.add_node("repair_planner", _mark("repair_planner"))
    builder.add_node("repair_action_builder", _mark("command"))
    builder.add_node("file_repair_planner", _mark("file"))
    builder.add_node("final_report", _mark("final"))

    builder.add_edge(START, "log_debug")
    builder.add_conditional_edges(
        "log_debug",
        route_after_log_debug,
        {
            "repair_planner": "repair_planner",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "repair_planner",
        route_after_repair_planner,
        {
            "repair_action_builder": "repair_action_builder",
            "file_repair_planner": "file_repair_planner",
            "final_report": "final_report",
        },
    )
    builder.add_edge("repair_action_builder", END)
    builder.add_edge("file_repair_planner", END)
    builder.add_edge("final_report", END)
    return builder.compile()
```

command repair 用例：

```python
def test_compiled_route_selects_only_command_branch():
    result = _build_failure_route_harness().invoke(
        {
            "repair_attempt_count": 0,
            "file_repair_attempt_count": 0,
            "repair_proposal": {
                "kind": "edit_command",
                "repaired_command": "python train.py --batch_size 1",
            },
            "debug_report": {},
            "visited": [],
        }
    )
    assert result["visited"] == ["log_debug", "repair_planner", "command"]
```

继续在同一个 `tests/test_compiled_graph_routes.py` 中加入另外两条完整用例：

```python
def test_compiled_route_selects_only_file_branch(monkeypatch):
    monkeypatch.setattr(settings, "enable_file_repair", True)
    result = _build_failure_route_harness().invoke(
        {
            "repair_attempt_count": settings.max_repair_attempts,
            "file_repair_attempt_count": 0,
            "repair_proposal": {
                "kind": "manual_only",
                "repaired_command": None,
            },
            "debug_report": {"related_files": ["train.py"]},
            "visited": [],
        }
    )
    assert result["visited"] == ["log_debug", "repair_planner", "file"]


def test_compiled_route_selects_only_final_branch(monkeypatch):
    monkeypatch.setattr(settings, "enable_file_repair", False)
    result = _build_failure_route_harness().invoke(
        {
            "repair_attempt_count": 0,
            "file_repair_attempt_count": 0,
            "repair_proposal": {"kind": "no_repair"},
            "debug_report": {},
            "visited": [],
        }
    )
    assert result["visited"] == ["log_debug", "repair_planner", "final"]
```

三个用例的核心断言都是每次只出现一个终点分支。注意：这些代码块属于同一个测试文件，不要把 import、harness 和测试函数拆成多个文件。

---

## 八、重定义 Patch Verification 状态

修改：

```text
app/schemas.py
```

`PatchVerificationCheck` 保留在这个类之前，并确认文件顶部已有：

```python
from typing import Literal

from pydantic import BaseModel, Field, model_validator
```

用下面的完整类替换原 `PatchVerificationReport`：

```python
class PatchVerificationReport(BaseModel):
    """隔离 worktree 中的分层验证结论。"""

    patch_id: str
    patch_sha256: str
    execution_profile_id: str
    execution_profile_fingerprint: str
    execution_backend: Literal["local", "conda"]

    status: Literal[
        "behaviorally_verified",
        "structurally_valid",
        "failed",
        "blocked",
    ]
    promotion_allowed: bool = False
    structural_checks_passed: bool = False
    behavioral_checks_run: int = 0
    behavioral_checks_passed: int = 0

    worktree_path: str | None = None
    worktree_diff_sha256: str | None = None
    checks: list[PatchVerificationCheck] = Field(default_factory=list)
    summary: str
    generated_at: str
    verification_sha256: str | None = None

    @model_validator(mode="after")
    def validate_verification_semantics(self) -> "PatchVerificationReport":
        if self.status == "behaviorally_verified":
            if not self.structural_checks_passed:
                raise ValueError(
                    "behaviorally_verified requires structural checks"
                )
            if self.behavioral_checks_run < 1:
                raise ValueError(
                    "behaviorally_verified requires a behavioral check"
                )
            if self.behavioral_checks_passed != self.behavioral_checks_run:
                raise ValueError("all behavioral checks must pass")
            if self.promotion_allowed is not True:
                raise ValueError(
                    "behaviorally_verified must allow promotion"
                )
        elif self.promotion_allowed:
            raise ValueError(
                "only behaviorally_verified may allow promotion"
            )

        return self
```

状态含义：

| 状态 | 含义 | 可 Promotion |
|---|---|---|
| `behaviorally_verified` | 结构检查和至少一个行为测试全部通过 | 是 |
| `structurally_valid` | patch/hash/语法正确，但没有行为测试 | 否 |
| `failed` | 某项检查明确失败 | 否 |
| `blocked` | profile、worktree 等前置条件不满足 | 否 |

---

## 九、精确计算验证级别

修改：

```text
app/tools/patch_tools.py
```

```python
STRUCTURAL_CHECK_NAMES = {
    "git_apply_check",
    "git_apply",
    "after_sha256",
    "worktree_diff_scope",
    "python_syntax",
}

BEHAVIORAL_CHECK_NAMES = {"targeted_tests"}


def summarize_patch_verification(
    checks: list[PatchVerificationCheck],
) -> tuple[str, bool, bool, int, int]:
    """
    返回 status、promotion_allowed、structural_passed、
    behavioral_run、behavioral_passed。
    """

    if not checks:
        return "blocked", False, False, 0, 0

    required_structural_names = {
        "git_apply_check",
        "git_apply",
        "after_sha256",
        "worktree_diff_scope",
    }
    passed_names = {
        item.name for item in checks if item.status == "passed"
    }
    structural_passed = required_structural_names.issubset(passed_names)

    structural_failed = any(
        item.name in STRUCTURAL_CHECK_NAMES and item.status == "failed"
        for item in checks
    )
    if structural_failed:
        return "failed", False, False, 0, 0
    if not structural_passed:
        return "blocked", False, False, 0, 0

    behavioral_checks = [
        item
        for item in checks
        if item.name in BEHAVIORAL_CHECK_NAMES
        and item.status != "skipped"
    ]
    run_count = len(behavioral_checks)
    passed_count = sum(
        item.status == "passed" for item in behavioral_checks
    )

    if run_count == 0:
        return "structurally_valid", False, True, 0, 0
    if passed_count == run_count:
        return "behaviorally_verified", True, True, run_count, passed_count
    return "failed", False, True, run_count, passed_count
```

在 `verify_patch_in_worktree()` 末尾使用：

```python
(
    status,
    promotion_allowed,
    structural_checks_passed,
    behavioral_checks_run,
    behavioral_checks_passed,
) = summarize_patch_verification(checks)

report = PatchVerificationReport(
    patch_id=bundle.patch_id,
    patch_sha256=bundle.patch_sha256,
    execution_profile_id=execution_profile_id,
    execution_profile_fingerprint=current_profile_fingerprint,
    execution_backend=verification_runner.profile.backend,
    status=status,
    promotion_allowed=promotion_allowed,
    structural_checks_passed=structural_checks_passed,
    behavioral_checks_run=behavioral_checks_run,
    behavioral_checks_passed=behavioral_checks_passed,
    worktree_path=str(worktree_path),
    worktree_diff_sha256=worktree_diff_sha256,
    checks=checks,
    summary=(
        "patch passed structural and behavioral verification"
        if status == "behaviorally_verified"
        else "patch has not reached behavioral verification"
    ),
    generated_at=datetime.now(timezone.utc).isoformat(),
)
verification_hash = compute_verification_hash(report)
return report.model_copy(
    update={"verification_sha256": verification_hash}
)
```

修改 `patch_verifier_node()`。下面是 `app/nodes/patch_verifier_node.py` 的完整文件参考：

```python
from pathlib import Path

from pydantic import ValidationError

from app.config import settings
from app.schemas import (
    FileRepairProposal,
    PatchApprovalRecord,
    PatchBundle,
)
from app.tools.patch_tools import verify_patch_in_worktree


def _verification_error(
    state: dict,
    *,
    final_status: str,
    error: str,
) -> dict:
    """统一构造不会进入 promotion 的验证失败状态。"""

    return {
        "patch_verification_report": None,
        "patch_verification_passed": False,
        "patch_verification_hash": None,
        "final_status": final_status,
        "error": error,
        "output_files": list(state.get("output_files", [])),
    }


def patch_verifier_node(state: dict) -> dict:
    """校验第一次审批绑定，并在隔离 worktree 中验证 patch。"""

    try:
        bundle = PatchBundle.model_validate(state.get("pending_patch"))
        approval = PatchApprovalRecord.model_validate(
            state.get("patch_approval_record")
        )
        proposal = FileRepairProposal.model_validate(
            state.get("file_repair_proposal")
        )
    except ValidationError as exc:
        return _verification_error(
            state,
            final_status="patch_verification_blocked",
            error=f"invalid patch verification input: {exc}",
        )

    # 第一次审批必须绑定当前 patch，而不是只检查 approved 字符串。
    if approval.decision != "approved":
        return _verification_error(
            state,
            final_status="patch_not_approved",
            error="patch review decision is not approved",
        )
    if (
        approval.patch_id != bundle.patch_id
        or approval.patch_sha256 != bundle.patch_sha256
    ):
        return _verification_error(
            state,
            final_status="stale_patch_approval",
            error="approval record does not match the current patch",
        )

    execution_profile_id = state.get("execution_profile_id")
    execution_profile_fingerprint = state.get(
        "execution_profile_fingerprint"
    )
    if not execution_profile_id or not execution_profile_fingerprint:
        return _verification_error(
            state,
            final_status="patch_verification_blocked",
            error="missing execution profile binding",
        )

    run_dir = Path(state.get("run_dir") or settings.output_dir)
    worktree_path = (
        run_dir
        / "execution"
        / "patch_worktrees"
        / bundle.patch_id
    )

    try:
        report = verify_patch_in_worktree(
            bundle=bundle,
            worktree_path=worktree_path,
            verification_targets=proposal.verification_targets,
            execution_profile_id=str(execution_profile_id),
            execution_profile_fingerprint=str(
                execution_profile_fingerprint
            ),
        )
    except (OSError, ValueError) as exc:
        return _verification_error(
            state,
            final_status="patch_verification_blocked",
            error=str(exc),
        )

    # 关键 artifact 写入当前 run，而不是全局 outputs 下的固定文件名。
    report_path = run_dir / "execution" / "patch_verification_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    passed = (
        report.status == "behaviorally_verified"
        and report.promotion_allowed is True
    )
    return {
        "patch_verification_report": report.model_dump(),
        "patch_verification_passed": passed,
        "patch_verification_hash": report.verification_sha256,
        "final_status": report.status,
        "error": None if passed else report.summary,
        "output_files": [
            *state.get("output_files", []),
            str(report_path),
        ],
    }
```

---

## 十、验证复用 Worktree 的完整修改范围

当前复用逻辑只看目标文件 after hash。还必须确认没有其他 tracked 文件被修改。

在 `app/tools/patch_tools.py` 增加：

```python
def _git_output(repo_path: Path, args: list[str]) -> str:
    result = _run_git(repo_path, args)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "git command failed")
    return result.stdout


def get_changed_tracked_paths(worktree_path: Path) -> set[str]:
    output = _git_output(
        worktree_path,
        ["diff", "--name-only", "HEAD"],
    )
    return {line.strip() for line in output.splitlines() if line.strip()}


def ensure_no_staged_changes(worktree_path: Path) -> None:
    staged = _git_output(
        worktree_path,
        ["diff", "--cached", "--name-only"],
    )
    if staged.strip():
        raise ValueError("patch worktree contains staged changes")


def compute_worktree_diff_hash(worktree_path: Path) -> str:
    """对完整 tracked binary diff 做哈希。"""

    diff_text = _git_output(
        worktree_path,
        ["diff", "--binary", "--full-index", "HEAD"],
    )
    return sha256_text(diff_text)


def validate_worktree_matches_patch(
    bundle: PatchBundle,
    worktree_path: Path,
) -> str:
    """
    目标文件必须全部为 after hash，且 tracked diff 只能包含 bundle 文件。

    返回完整 worktree diff SHA-256。
    """

    if get_git_commit(worktree_path) != bundle.base_git_commit:
        raise ValueError("patch worktree HEAD changed")

    ensure_no_staged_changes(worktree_path)

    expected_paths = {item.relative_path for item in bundle.files}
    changed_paths = get_changed_tracked_paths(worktree_path)
    if changed_paths != expected_paths:
        raise ValueError(
            "worktree tracked diff scope mismatch: "
            f"expected={sorted(expected_paths)}, "
            f"actual={sorted(changed_paths)}"
        )

    for file_record in bundle.files:
        target = worktree_path / file_record.relative_path
        if not target.is_file():
            raise ValueError(
                f"patched worktree file missing: {file_record.relative_path}"
            )
        if sha256_file(target) != file_record.after_sha256:
            raise ValueError(
                f"patched worktree hash mismatch: {file_record.relative_path}"
            )

    diff_check = _run_git(worktree_path, ["diff", "--check", "HEAD"])
    if diff_check.returncode != 0:
        raise ValueError(
            f"worktree diff check failed: {diff_check.stderr.strip()}"
        )

    return compute_worktree_diff_hash(worktree_path)
```

在 apply 到 worktree 后增加：

```python
try:
    worktree_diff_sha256 = validate_worktree_matches_patch(
        bundle,
        worktree_path,
    )
    checks.append(
        PatchVerificationCheck(
            name="worktree_diff_scope",
            status="passed",
            output_preview=(
                "tracked diff exactly matches patch bundle; "
                f"sha256={worktree_diff_sha256}"
            ),
        )
    )
except ValueError as exc:
    worktree_diff_sha256 = None
    checks.append(
        PatchVerificationCheck(
            name="worktree_diff_scope",
            status="failed",
            output_preview=str(exc),
        )
    )
```

复用已有 worktree 时也必须调用该函数，不能只凭 `after_matches=True` 直接成功。

---

## 十一、重新计算 Verification Hash

继续修改 `app/tools/patch_tools.py`：

```python
import hmac


def validate_verification_hash(
    report: PatchVerificationReport,
) -> str:
    """重新序列化完整报告并校验 embedded hash。"""

    embedded_hash = report.verification_sha256
    if not embedded_hash:
        raise ValueError("verification report has no embedded hash")

    computed_hash = compute_verification_hash(report)
    if not hmac.compare_digest(embedded_hash, computed_hash):
        raise ValueError(
            "verification report content changed after hash generation"
        )
    return computed_hash
```

关键不是使用哪种字符串比较，而是：

```text
必须从当前完整报告重新计算
不能只比较两个已经保存的旧 hash 字段
```

---

## 十二、统一 Patch Authorization 校验

在 `app/tools/patch_tools.py` 增加：

```python
# Path、Any、PatchBundle、PatchVerificationReport 和 sha256_file
# 在该文件原有 import 中已经存在，不要重复定义。
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.schemas import PatchPromotionRecord


def validate_patch_promotion_authorization(
    *,
    bundle: PatchBundle,
    report: PatchVerificationReport,
    promotion: PatchPromotionRecord | None,
    state: dict[str, Any],
    require_promotion: bool,
) -> str:
    """
    在 promotion review 和 apply 边界复用同一套确定性校验。

    返回重新计算的 verification hash。
    """

    # 这里只校验不可变 patch artifact，不要求源码仍是 before 状态。
    # 源码可能已经 apply 成功但 checkpoint 尚未更新，此时必须允许
    # apply 层通过 exact-after 状态完成幂等恢复。
    patch_path = Path(bundle.patch_path)
    if not patch_path.is_file():
        raise ValueError("patch artifact is missing")
    if sha256_file(patch_path) != bundle.patch_sha256:
        raise ValueError("patch artifact hash mismatch")

    computed_hash = validate_verification_hash(report)

    if report.status != "behaviorally_verified":
        raise ValueError(
            f"patch is not behaviorally verified: {report.status}"
        )
    if report.promotion_allowed is not True:
        raise ValueError("verification report does not allow promotion")

    if report.patch_id != bundle.patch_id:
        raise ValueError("report patch_id does not match bundle")
    if report.patch_sha256 != bundle.patch_sha256:
        raise ValueError("report patch hash does not match bundle")

    state_profile_id = state.get("execution_profile_id")
    state_fingerprint = state.get("execution_profile_fingerprint")
    pending_action = state.get("pending_action") or {}

    if report.execution_profile_id != state_profile_id:
        raise ValueError("verification profile id does not match state")
    if report.execution_profile_fingerprint != state_fingerprint:
        raise ValueError("verification profile fingerprint does not match state")
    if pending_action.get("execution_profile_id") != state_profile_id:
        raise ValueError("pending action profile id does not match state")
    if (
        pending_action.get("execution_profile_fingerprint")
        != state_fingerprint
    ):
        raise ValueError("pending action profile fingerprint does not match state")

    current_profile = get_execution_profile(str(state_profile_id))
    current_fingerprint = compute_execution_profile_fingerprint(
        current_profile
    )
    if current_fingerprint != state_fingerprint:
        raise ValueError(
            "execution profile changed after patch verification"
        )

    if require_promotion:
        if promotion is None or promotion.decision != "approved":
            raise ValueError("patch promotion is not approved")
        if promotion.patch_id != bundle.patch_id:
            raise ValueError("promotion patch_id does not match bundle")
        if promotion.patch_sha256 != bundle.patch_sha256:
            raise ValueError("promotion patch hash does not match bundle")
        if not hmac.compare_digest(
            promotion.verification_sha256,
            computed_hash,
        ):
            raise ValueError(
                "promotion does not match current verification report"
            )

    return computed_hash
```

这个函数不修改文件，只回答：当前 patch 是否仍然是被验证和批准的同一对象。

---

## 十三、修复 Promotion Review 边界

修改：

```text
app/nodes/patch_promotion_review_node.py
```

下面是 `app/nodes/patch_promotion_review_node.py` 的完整文件参考：

```python
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from langgraph.types import interrupt
from pydantic import ValidationError

from app.config import settings
from app.schemas import (
    PatchBundle,
    PatchPromotionRecord,
    PatchVerificationReport,
)
from app.tools.patch_tools import validate_patch_promotion_authorization


def _promotion_blocked(
    *,
    final_status: str,
    error: str,
) -> dict:
    return {
        "patch_promotion_decision": "blocked",
        "patch_promotion_feedback": None,
        "patch_promotion_record": None,
        "final_status": final_status,
        "error": error,
    }


def patch_promotion_review_node(state: dict) -> dict:
    try:
        bundle = PatchBundle.model_validate(state.get("pending_patch"))
        report = PatchVerificationReport.model_validate(
            state.get("patch_verification_report")
        )
        computed_hash = validate_patch_promotion_authorization(
            bundle=bundle,
            report=report,
            promotion=None,
            state=state,
            require_promotion=False,
        )
    except (KeyError, ValidationError, ValueError) as exc:
        return _promotion_blocked(
            final_status="patch_not_authorized_for_promotion",
            error=str(exc),
        )

    response = interrupt(
        {
            "review_type": "patch_promotion_review",
            "patch_id": bundle.patch_id,
            "patch_sha256": bundle.patch_sha256,
            "verification_sha256": computed_hash,
            "verification_status": report.status,
            "worktree_diff_sha256": report.worktree_diff_sha256,
            "checks": [item.model_dump() for item in report.checks],
            "allowed_decisions": ["approved", "rejected"],
        }
    )

    # interrupt 恢复后再次从当前 state 校验，防止暂停期间发生变化。
    try:
        bundle = PatchBundle.model_validate(state.get("pending_patch"))
        report = PatchVerificationReport.model_validate(
            state.get("patch_verification_report")
        )
        computed_hash = validate_patch_promotion_authorization(
            bundle=bundle,
            report=report,
            promotion=None,
            state=state,
            require_promotion=False,
        )
    except (KeyError, ValidationError, ValueError) as exc:
        return _promotion_blocked(
            final_status="stale_patch_verification",
            error=str(exc),
        )

    if isinstance(response, dict):
        raw_decision = response.get("decision", "rejected")
        feedback = response.get("feedback")
    else:
        raw_decision = response
        feedback = None

    decision = str(raw_decision)
    if decision not in {"approved", "rejected"}:
        decision = "rejected"
        feedback = f"invalid promotion decision: {raw_decision}"

    record = PatchPromotionRecord(
        promotion_id=f"patch_promotion_{uuid4().hex[:12]}",
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        verification_sha256=computed_hash,
        decision=decision,
        reviewer="human",
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        comment=feedback,
    )

    run_dir = Path(state.get("run_dir") or settings.output_dir)
    record_path = run_dir / "planning" / "patch_promotion_record.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        record.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return {
        "patch_promotion_decision": decision,
        "patch_promotion_feedback": feedback,
        "patch_promotion_record": record.model_dump(),
        "final_status": (
            "patch_promotion_approved"
            if decision == "approved"
            else "patch_promotion_rejected"
        ),
        "error": None,
        "output_files": [
            *state.get("output_files", []),
            str(record_path),
        ],
    }
```

报告只是 `structurally_valid` 时，该节点不会 interrupt。

---

## 十四、增加 Repository Lock

新增：

```text
app/tools/repository_lock_tools.py
```

Linux 环境可使用标准库 `fcntl.flock()`：

```python
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, TextIO

from app.config import settings


class RepositoryLockBusyError(RuntimeError):
    """同一个 repo 正在被另一个 patch apply 持有。"""


def repository_lock_key(repo_path: str | Path) -> str:
    canonical = str(Path(repo_path).resolve())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@contextmanager
def acquire_repository_lock(
    repo_path: str | Path,
    *,
    owner_run_id: str,
    timeout_seconds: float,
) -> Generator[str, None, None]:
    """获取跨进程排他锁；锁文件不写入论文仓库。"""

    lock_key = repository_lock_key(repo_path)
    lock_dir = settings.patch_coordination_dir / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{lock_key}.lock"

    lock_file: TextIO = lock_path.open("a+", encoding="utf-8")
    deadline = time.monotonic() + max(timeout_seconds, 0.0)

    try:
        while True:
            try:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RepositoryLockBusyError(
                        f"repository is busy: {Path(repo_path).resolve()}"
                    )
                time.sleep(0.05)

        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(
            json.dumps(
                {
                    "owner_run_id": owner_run_id,
                    "pid": os.getpid(),
                    "repo_path": str(Path(repo_path).resolve()),
                    "acquired_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        lock_file.flush()
        os.fsync(lock_file.fileno())
        yield lock_key
    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()
```

不要用“普通 `.lock` 文件存在”代替内核锁。进程崩溃后普通文件会残留，而 `flock` 会自动释放。

修改 `app/config.py`：

```python
@dataclass
class Settings:
    # Settings 中原有字段保持不变，在类体末尾增加下面两个字段。
    patch_coordination_dir: Path = Path(
        os.getenv("PATCH_COORDINATION_DIR", "runs/.coordination")
    )

    patch_repo_lock_timeout_seconds: float = float(
        os.getenv("PATCH_REPO_LOCK_TIMEOUT_SECONDS", "2")
    )
```

不要在文件末尾重新声明第二个 `Settings` 类。上面的类头用于展示上下文，实际操作是在现有 `Settings` 类内部追加两个缩进为四个空格的字段。

`settings = Settings()` 初始化后的完整目录创建区域应为：

```python
settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.runs_dir.mkdir(parents=True, exist_ok=True)
settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
settings.patch_coordination_dir.mkdir(parents=True, exist_ok=True)
```

修改 `.env.example`：

```dotenv
PATCH_COORDINATION_DIR=runs/.coordination
PATCH_REPO_LOCK_TIMEOUT_SECONDS=2
```

---

## 十五、增加 Patch Application Journal

修改 `app/schemas.py`：

```python
class PatchApplicationJournal(BaseModel):
    """仓库副作用的 write-ahead journal。"""

    journal_version: int = 1
    patch_id: str
    patch_sha256: str
    repo_path: str
    base_git_commit: str
    owner_run_id: str
    status: Literal[
        "prepared",
        "applying",
        "applied",
        "blocked",
        "manual_intervention",
    ]
    files: list[PatchFileRecord] = Field(default_factory=list)
    repository_state: Literal["before", "after", "conflict"]
    recovered: bool = False
    error: str | None = None
    created_at: str
    updated_at: str


class PatchApplicationRecord(BaseModel):
    """patch 应用结果；字段完整列出，不要覆盖掉 Phase 13 的字段。"""

    patch_id: str
    patch_sha256: str
    repo_path: str
    status: Literal[
        "applied",
        "failed",
        "blocked",
        "manual_intervention",
    ]
    files: list[PatchFileRecord] = Field(default_factory=list)
    applied_at: str
    recovered: bool = False
    error: str | None = None
    journal_path: str | None = None
    repository_lock_key: str | None = None
```

这里两个类应放在 `PatchFileRecord` 和 `PatchBundle` 已定义之后。`app/schemas.py` 顶部必须已经导入：

```python
from typing import Literal

from pydantic import BaseModel, Field
```

新增：

```text
app/tools/patch_journal_tools.py
```

```python
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.config import settings
from app.schemas import PatchApplicationJournal, PatchBundle
from app.tools.repository_lock_tools import repository_lock_key


def patch_journal_path(bundle: PatchBundle) -> Path:
    """同一 repo + patch 在所有 run 中共享一个 journal。"""

    repo_key = repository_lock_key(bundle.repo_path)
    journal_dir = settings.patch_coordination_dir / "journals" / repo_key
    journal_dir.mkdir(parents=True, exist_ok=True)
    return journal_dir / f"{bundle.patch_sha256}.json"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """写临时文件并 fsync，再原子替换目标 JSON。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")

    with temp_path.open("wb") as file_obj:
        file_obj.write(encoded)
        file_obj.flush()
        os.fsync(file_obj.fileno())

    os.replace(temp_path, path)
    directory_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def load_patch_journal(
    bundle: PatchBundle,
) -> PatchApplicationJournal | None:
    path = patch_journal_path(bundle)
    if not path.exists():
        return None
    return PatchApplicationJournal.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def write_patch_journal(
    *,
    bundle: PatchBundle,
    owner_run_id: str,
    status: Literal[
        "prepared",
        "applying",
        "applied",
        "blocked",
        "manual_intervention",
    ],
    repository_state: Literal["before", "after", "conflict"],
    recovered: bool = False,
    error: str | None = None,
) -> tuple[PatchApplicationJournal, Path]:
    path = patch_journal_path(bundle)
    previous = load_patch_journal(bundle)
    now = datetime.now(timezone.utc).isoformat()

    journal = PatchApplicationJournal(
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        repo_path=bundle.repo_path,
        base_git_commit=bundle.base_git_commit,
        owner_run_id=owner_run_id,
        status=status,
        files=bundle.files,
        repository_state=repository_state,
        recovered=recovered,
        error=error,
        created_at=previous.created_at if previous else now,
        updated_at=now,
    )
    atomic_write_json(path, journal.model_dump())
    return journal, path
```

Journal 与 checkpoint 记录不同事实：

```text
LangGraph checkpoint：推理流程走到哪里
application journal：仓库副作用进行到哪里
```

---

## 十六、识别仓库 Before / After / Conflict

在 `app/tools/patch_tools.py` 增加：

```python
def inspect_source_patch_state(bundle: PatchBundle) -> str:
    """
    返回 before、after 或 conflict。

    这是 apply 幂等恢复的事实来源，不修改仓库。
    """

    repo = Path(bundle.repo_path).resolve()
    if get_git_commit(repo) != bundle.base_git_commit:
        return "conflict"

    staged = _git_output(repo, ["diff", "--cached", "--name-only"])
    if staged.strip():
        return "conflict"

    changed_paths = get_changed_tracked_paths(repo)
    expected_paths = {item.relative_path for item in bundle.files}

    all_files_exist = all(
        (repo / item.relative_path).is_file() for item in bundle.files
    )
    if not all_files_exist:
        return "conflict"

    before_matches = all(
        sha256_file(repo / item.relative_path) == item.before_sha256
        for item in bundle.files
    )
    after_matches = all(
        sha256_file(repo / item.relative_path) == item.after_sha256
        for item in bundle.files
    )

    if before_matches and not changed_paths:
        return "before"

    if after_matches and changed_paths == expected_paths:
        return "after"

    return "conflict"
```

如果用户在审批期间修改了另一个 tracked 文件，状态必须是 `conflict`。Agent 不能自动 stash、reset 或回滚用户内容。

---

## 十七、实现崩溃幂等 Patch Apply

重写 `apply_verified_patch_to_source()`，同时使用 repository lock 和 journal。

```python
from collections.abc import Callable

from app.tools.patch_journal_tools import write_patch_journal
from app.tools.repository_lock_tools import (
    RepositoryLockBusyError,
    acquire_repository_lock,
)


FaultHook = Callable[[str], None]


def _application_record(
    *,
    bundle: PatchBundle,
    status: str,
    applied_at: str,
    recovered: bool = False,
    error: str | None = None,
    journal_path: Path | None = None,
    lock_key: str | None = None,
) -> PatchApplicationRecord:
    return PatchApplicationRecord(
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        repo_path=bundle.repo_path,
        status=status,
        files=bundle.files,
        applied_at=applied_at,
        recovered=recovered,
        error=error,
        journal_path=str(journal_path) if journal_path else None,
        repository_lock_key=lock_key,
    )


def apply_verified_patch_to_source(
    bundle: PatchBundle,
    *,
    owner_run_id: str,
    fault_hook: FaultHook | None = None,
) -> PatchApplicationRecord:
    """
    在仓库锁内通过 write-ahead journal 幂等应用 patch。

    fault_hook 只用于测试，生产调用不传。
    """

    repo = Path(bundle.repo_path).resolve()

    def inject(point: str) -> None:
        if fault_hook is not None:
            fault_hook(point)

    try:
        with acquire_repository_lock(
            repo,
            owner_run_id=owner_run_id,
            timeout_seconds=settings.patch_repo_lock_timeout_seconds,
        ) as lock_key:
            patch_path = Path(bundle.patch_path)
            if not patch_path.is_file():
                raise ValueError("patch artifact is missing")
            if sha256_file(patch_path) != bundle.patch_sha256:
                raise ValueError("patch artifact hash mismatch")

            repository_state = inspect_source_patch_state(bundle)

            if repository_state == "after":
                # 上次可能在 apply 成功后、checkpoint 前崩溃。
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status="applied",
                    repository_state="after",
                    recovered=True,
                )
                return _application_record(
                    bundle=bundle,
                    status="applied",
                    applied_at=journal.updated_at,
                    recovered=True,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            if repository_state == "conflict":
                message = (
                    "repository matches neither exact before nor exact after state"
                )
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status="manual_intervention",
                    repository_state="conflict",
                    error=message,
                )
                return _application_record(
                    bundle=bundle,
                    status="manual_intervention",
                    applied_at=journal.updated_at,
                    error=message,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            # 只有 exact before 才能开始新的 apply。
            journal, journal_path = write_patch_journal(
                bundle=bundle,
                owner_run_id=owner_run_id,
                status="prepared",
                repository_state="before",
            )
            inject("after_journal_prepared")

            apply_check = _run_git(
                repo,
                ["apply", "--check", bundle.patch_path],
            )
            if apply_check.returncode != 0:
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status="blocked",
                    repository_state="before",
                    error=apply_check.stderr.strip(),
                )
                return _application_record(
                    bundle=bundle,
                    status="blocked",
                    applied_at=journal.updated_at,
                    error=journal.error,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            write_patch_journal(
                bundle=bundle,
                owner_run_id=owner_run_id,
                status="applying",
                repository_state="before",
            )
            inject("before_git_apply")

            apply_result = _run_git(repo, ["apply", bundle.patch_path])
            if apply_result.returncode != 0:
                current_state = inspect_source_patch_state(bundle)
                journal_status = (
                    "blocked" if current_state == "before"
                    else "manual_intervention"
                )
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status=journal_status,
                    repository_state=current_state,
                    error=apply_result.stderr.strip(),
                )
                return _application_record(
                    bundle=bundle,
                    status=(
                        "failed"
                        if current_state == "before"
                        else "manual_intervention"
                    ),
                    applied_at=journal.updated_at,
                    error=journal.error,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            # 最重要的故障点：仓库已变化，checkpoint 尚未变化。
            inject("after_git_apply_before_journal")

            if inspect_source_patch_state(bundle) != "after":
                message = "source repository did not reach exact after state"
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status="manual_intervention",
                    repository_state="conflict",
                    error=message,
                )
                return _application_record(
                    bundle=bundle,
                    status="manual_intervention",
                    applied_at=journal.updated_at,
                    error=message,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            journal, journal_path = write_patch_journal(
                bundle=bundle,
                owner_run_id=owner_run_id,
                status="applied",
                repository_state="after",
            )
            inject("after_journal_applied")

            return _application_record(
                bundle=bundle,
                status="applied",
                applied_at=journal.updated_at,
                recovered=False,
                journal_path=journal_path,
                lock_key=lock_key,
            )

    except RepositoryLockBusyError as exc:
        return _application_record(
            bundle=bundle,
            status="blocked",
            applied_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
        )
    except (OSError, ValueError) as exc:
        # 可预期的磁盘、Git、hash 错误转成审计记录；
        # fault_hook 抛出的 BaseException 不会在这里被吞掉。
        return _application_record(
            bundle=bundle,
            status="failed",
            applied_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
        )
```

不要用“失败后无条件 `git apply -R`”代替状态判断。发生 conflict 时，自动反向 patch 也可能破坏用户后续修改。

---

## 十八、收紧 Patch Apply Node

修改：

```text
app/nodes/patch_apply_node.py
```

下面是 `app/nodes/patch_apply_node.py` 的完整文件参考。任何仓库写入前都先完成独立授权校验：

```python
from pathlib import Path

from pydantic import ValidationError

from app.config import settings
from app.schemas import (
    PatchBundle,
    PatchPromotionRecord,
    PatchVerificationReport,
)
from app.tools.action_tools import compute_action_hash
from app.tools.patch_tools import (
    apply_verified_patch_to_source,
    validate_patch_promotion_authorization,
)


def patch_apply_node(state: dict) -> dict:
    try:
        bundle = PatchBundle.model_validate(state.get("pending_patch"))
        report = PatchVerificationReport.model_validate(
            state.get("patch_verification_report")
        )
        promotion = PatchPromotionRecord.model_validate(
            state.get("patch_promotion_record")
        )
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=report,
            promotion=promotion,
            state=state,
            require_promotion=True,
        )
    except (KeyError, ValidationError, ValueError) as exc:
        return {
            "patch_application_record": None,
            "final_status": "patch_apply_not_authorized",
            "error": str(exc),
            "output_files": list(state.get("output_files", [])),
        }

    run_id = str(state.get("run_id") or state.get("task_id") or "unknown")
    application = apply_verified_patch_to_source(
        bundle,
        owner_run_id=run_id,
    )

    # Patch application artifact 直接写当前 run，避免关键记录被覆盖。
    run_dir = Path(state.get("run_dir") or settings.output_dir)
    application_path = run_dir / "execution" / "patch_application_record.json"
    application_path.parent.mkdir(parents=True, exist_ok=True)
    application_path.write_text(
        application.model_dump_json(indent=2),
        encoding="utf-8",
    )

    if application.status != "applied":
        return {
            "patch_application_record": application.model_dump(),
            "final_status": (
                "patch_apply_manual_intervention"
                if application.status == "manual_intervention"
                else "patch_apply_blocked"
            ),
            "error": application.error,
            "output_files": [
                *state.get("output_files", []),
                str(application_path),
            ],
        }

    # 源码变化后，动作身份也发生变化，必须重算 action hash。
    pending_action = dict(state.get("pending_action") or {})
    pending_action["repo_patch_hash"] = bundle.patch_sha256
    new_action_hash = compute_action_hash(pending_action)

    attempts = int(state.get("file_repair_attempt_count", 0)) + 1
    history_entry = {
        "attempt": attempts,
        "patch_id": bundle.patch_id,
        "patch_sha256": bundle.patch_sha256,
        "files": [item.relative_path for item in bundle.files],
        "status": "applied",
        "recovered": application.recovered,
    }

    return {
        "patch_application_record": application.model_dump(),
        "applied_patch_hash": bundle.patch_sha256,
        "file_repair_attempt_count": attempts,
        "file_repair_history": [
            *state.get("file_repair_history", []),
            history_entry,
        ],
        "pending_action": pending_action,
        "pending_action_hash": new_action_hash,

        # 旧审批绑定的是 patch 前的 action hash，源码变化后必须清空。
        "user_approval": None,
        "human_feedback": None,
        "approval_record": None,

        # 旧的环境检查、smoke、debug 和 execution 结果全部失效。
        "preflight_report": None,
        "preflight_passed": False,
        "preflight_report_path": None,
        "smoke_test_report": None,
        "smoke_test_status": None,
        "smoke_test_passed": False,
        "smoke_test_log_path": None,
        "debug_report": None,
        "execution_result": {},
        "execution_log_path": None,
        "log_path": None,
        "final_status": "patch_applied",
        "error": None,
        "output_files": [
            *state.get("output_files", []),
            str(application_path),
        ],
    }
```

即使 `application.recovered=True`，也按成功处理并重建 action state。它表示副作用已在上一次执行完成，本次只是恢复事实。

---

## 十九、增加 Worktree 清理入口

在 `app/tools/patch_tools.py` 增加：

```python
def validate_patch_worktree_path(
    *,
    worktree_path: Path,
    run_dir: Path,
) -> Path:
    """只允许当前 run/execution/patch_worktrees 下的精确路径。"""

    resolved_worktree = worktree_path.resolve()
    allowed_root = run_dir.resolve() / "execution" / "patch_worktrees"
    if (
        resolved_worktree != allowed_root
        and allowed_root not in resolved_worktree.parents
    ):
        raise ValueError("worktree path is outside current run")
    if not (resolved_worktree / ".git").exists():
        raise ValueError("target is not a Git worktree")
    return resolved_worktree


def remove_patch_worktree(
    *,
    repo_path: str,
    worktree_path: str,
    run_dir: str,
) -> None:
    target = validate_patch_worktree_path(
        worktree_path=Path(worktree_path),
        run_dir=Path(run_dir),
    )
    result = _run_git(
        Path(repo_path),
        ["worktree", "remove", "--force", str(target)],
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "worktree removal failed")
```

在 `app/main.py` 增加：

```python
# 与 app/main.py 顶部的其他 app.tools import 放在一起。
from app.tools.patch_tools import remove_patch_worktree


@app.command()
def cleanup_patch_worktree(
    thread_id: str,
    force: bool = typer.Option(False, "--force"),
):
    """显式清理已结束 patch 流程的隔离 worktree。"""

    graph = build_graph()
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 60,
    }
    snapshot = graph.get_state(config)

    protected_nodes = {"patch_review", "patch_promotion_review"}
    if protected_nodes.intersection(snapshot.next):
        raise typer.BadParameter(
            "cannot clean a worktree while patch review is pending"
        )

    values = snapshot.values
    report = values.get("patch_verification_report") or {}
    worktree_path = report.get("worktree_path")
    if not worktree_path:
        raise typer.BadParameter("patch worktree not found in checkpoint")

    application = values.get("patch_application_record") or {}
    if application.get("status") != "applied" and not force:
        raise typer.BadParameter(
            "patch is not applied; inspect it or pass --force"
        )

    remove_patch_worktree(
        repo_path=values["repo_path"],
        worktree_path=worktree_path,
        run_dir=values["run_dir"],
    )
    print(f"[green]removed patch worktree:[/green] {worktree_path}")
```

`--force` 只允许清理失败或拒绝后的隔离 worktree，不能绕过路径检查，也不能清理仍在审批中的 worktree。

---

## 二十、更新 Artifact 和 Final Report

在 `app/tools/artifact_tools.py` 的 `build_run_manifest()` 中，用下面的完整对象替换原 `"file_repair"` 对象：

```python
manifest_fragment = {
    "file_repair": {
        "attempt_count": state.get("file_repair_attempt_count", 0),
        "history": state.get("file_repair_history", []),
        "proposal": state.get("file_repair_proposal"),
        "pending_patch": state.get("pending_patch"),
        "patch_approval": state.get("patch_approval_record"),
        "verification": state.get("patch_verification_report"),
        "promotion": state.get("patch_promotion_record"),
        "application": state.get("patch_application_record"),
        "application_journal_path": (
            (state.get("patch_application_record") or {}).get(
                "journal_path"
            )
        ),
        "application_recovered": (
            (state.get("patch_application_record") or {}).get(
                "recovered",
                False,
            )
        ),
        "worktree_diff_sha256": (
            (state.get("patch_verification_report") or {}).get(
                "worktree_diff_sha256"
            )
        ),
    },
}
```

`manifest_fragment` 只是为了让教程片段本身保持可运行语法。实际修改时，把其中完整的 `"file_repair"` 键值项放回 `build_run_manifest()` 已有的返回字典，不要在函数中额外返回 `manifest_fragment`。

在 `app/nodes/final_report_node.py` 的 `_render_final_report()` 中，找到现有 `file_repair_items` 区域；保留 proposal 和 pending patch 的处理，并用下面代码替换原 verification/application 两段。最后的 `_render_section()` 调用仍放在这段代码之后：

```python
verification = state.get("patch_verification_report") or {}
if verification:
    file_repair_items.extend(
        [
            f"Verification Status: `{verification.get('status')}`",
            f"Promotion Allowed: `{verification.get('promotion_allowed', False)}`",
            (
                "Behavioral Checks: "
                f"`{verification.get('behavioral_checks_passed', 0)}` / "
                f"`{verification.get('behavioral_checks_run', 0)}`"
            ),
        ]
    )

application = state.get("patch_application_record") or {}
if application:
    file_repair_items.extend(
        [
            f"Application Status: `{application.get('status')}`",
            f"Recovered After Crash: `{application.get('recovered', False)}`",
            f"Journal: `{application.get('journal_path', 'N/A')}`",
        ]
    )

lines += _render_section("File Repair Summary", file_repair_items)
```

### 20.1 增加测试共享 Fixture

后续测试会使用 `valid_report`、`patch_bundle` 和 `verified_worktree`。新增 `tests/conftest.py`，下面是完整文件：

```python
from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from app.config import settings
from app.schemas import (
    PatchBundle,
    PatchFileRecord,
    PatchVerificationCheck,
    PatchVerificationReport,
)
from app.tools.patch_tools import (
    build_unified_diff,
    compute_verification_hash,
    sha256_file,
    sha256_text,
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """测试只执行固定 Git token，不经过 shell。"""

    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )


@pytest.fixture
def valid_report(
    patch_bundle: PatchBundle,
) -> PatchVerificationReport:
    """构造语义有效且 embedded hash 正确的验证报告。"""

    checks = [
        PatchVerificationCheck(
            name="git_apply_check",
            status="passed",
        ),
        PatchVerificationCheck(name="git_apply", status="passed"),
        PatchVerificationCheck(name="after_sha256", status="passed"),
        PatchVerificationCheck(
            name="worktree_diff_scope",
            status="passed",
        ),
        PatchVerificationCheck(name="python_syntax", status="passed"),
        PatchVerificationCheck(name="targeted_tests", status="passed"),
    ]
    report = PatchVerificationReport(
        patch_id=patch_bundle.patch_id,
        patch_sha256=patch_bundle.patch_sha256,
        execution_profile_id="local",
        execution_profile_fingerprint="b" * 64,
        execution_backend="local",
        status="behaviorally_verified",
        promotion_allowed=True,
        structural_checks_passed=True,
        behavioral_checks_run=1,
        behavioral_checks_passed=1,
        worktree_path="/data/tianshaoqi24/phase14-test-fixture/worktree",
        worktree_diff_sha256="c" * 64,
        checks=checks,
        summary="fixture verification passed",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return report.model_copy(
        update={"verification_sha256": compute_verification_hash(report)}
    )


@pytest.fixture
def patch_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> PatchBundle:
    """创建包含一个目标文件和一个额外 tracked 文件的真实 Git 仓库。"""

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "Tests")

    target = repo / "train.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "extra.py").write_text("EXTRA = 1\n", encoding="utf-8")
    _git(repo, "add", "train.py", "extra.py")
    _git(repo, "commit", "-m", "initial")

    before = target.read_text(encoding="utf-8")
    after = "VALUE = 2\n"
    patch_text = build_unified_diff("train.py", before, after)

    patch_dir = tmp_path / "bundle"
    patch_dir.mkdir()
    patch_path = patch_dir / "patch.diff"
    patch_path.write_text(patch_text, encoding="utf-8")

    # Lock 和 journal 都隔离到 pytest 临时目录，避免污染 runs/。
    coordination_dir = tmp_path / "coordination"
    monkeypatch.setattr(
        settings,
        "patch_coordination_dir",
        coordination_dir,
    )
    monkeypatch.setattr(
        settings,
        "patch_repo_lock_timeout_seconds",
        0.0,
    )

    return PatchBundle(
        patch_id="patch_fixture",
        proposal_id="proposal_fixture",
        repo_path=str(repo.resolve()),
        base_git_commit=_git(repo, "rev-parse", "HEAD").stdout.strip(),
        patch_path=str(patch_path.resolve()),
        patch_sha256=sha256_file(patch_path),
        files=[
            PatchFileRecord(
                relative_path="train.py",
                before_sha256=sha256_text(before),
                after_sha256=sha256_text(after),
                replacement_count=1,
                changed_line_count=1,
            )
        ],
        summary="change fixture value",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def verified_worktree(
    patch_bundle: PatchBundle,
    tmp_path: Path,
):
    """创建 HEAD 正确、且已精确应用 bundle 的 detached worktree。"""

    source_repo = Path(patch_bundle.repo_path)
    worktree = tmp_path / "verified-worktree"
    _git(
        source_repo,
        "worktree",
        "add",
        "--detach",
        str(worktree),
        patch_bundle.base_git_commit,
    )
    _git(worktree, "apply", patch_bundle.patch_path)

    try:
        yield worktree
    finally:
        subprocess.run(
            [
                "git",
                "-C",
                str(source_repo),
                "worktree",
                "remove",
                "--force",
                str(worktree),
            ],
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
```

如果项目已经有 `tests/conftest.py`，不要新建第二份同名文件；把这些 import、辅助函数和 fixture 合并到现有文件，并避免覆盖已有 fixture。

---

## 二十一、测试 Verification 语义

新增 `tests/test_patch_verification_semantics.py`：

```python
from app.schemas import PatchVerificationCheck
from app.tools.patch_tools import summarize_patch_verification


def _passed(name: str) -> PatchVerificationCheck:
    return PatchVerificationCheck(name=name, status="passed")


def _structural_checks() -> list[PatchVerificationCheck]:
    return [
        _passed("git_apply_check"),
        _passed("git_apply"),
        _passed("after_sha256"),
        _passed("worktree_diff_scope"),
        PatchVerificationCheck(name="python_syntax", status="skipped"),
    ]


def test_no_behavior_test_is_only_structurally_valid():
    checks = [
        *_structural_checks(),
        PatchVerificationCheck(name="targeted_tests", status="skipped"),
    ]
    status, allowed, structural, run_count, passed = (
        summarize_patch_verification(checks)
    )
    assert status == "structurally_valid"
    assert allowed is False
    assert structural is True
    assert run_count == 0
    assert passed == 0


def test_passed_behavior_test_allows_promotion():
    checks = [*_structural_checks(), _passed("targeted_tests")]
    status, allowed, _, run_count, passed = (
        summarize_patch_verification(checks)
    )
    assert status == "behaviorally_verified"
    assert allowed is True
    assert run_count == 1
    assert passed == 1


def test_failed_behavior_test_fails_verification():
    checks = [
        *_structural_checks(),
        PatchVerificationCheck(name="targeted_tests", status="failed"),
    ]
    status, allowed, *_ = summarize_patch_verification(checks)
    assert status == "failed"
    assert allowed is False
```

---

## 二十二、测试 Hash 和授权边界

新增 `tests/test_patch_authorization_boundaries.py`：

```python
import pytest

import app.tools.patch_tools as patch_tools
from app.schemas import PatchPromotionRecord
from app.tools.patch_tools import (
    compute_verification_hash,
    validate_patch_promotion_authorization,
    validate_verification_hash,
)


def test_tampering_any_report_field_invalidates_hash(valid_report):
    report = valid_report.model_copy(update={"summary": "tampered"})
    with pytest.raises(ValueError, match="content changed"):
        validate_verification_hash(report)


def test_embedded_hash_is_recomputed(valid_report):
    unhashed = valid_report.model_copy(
        update={"verification_sha256": None}
    )
    expected = compute_verification_hash(unhashed)
    report = unhashed.model_copy(
        update={"verification_sha256": expected}
    )
    assert validate_verification_hash(report) == expected


def _authorization_inputs(valid_report, patch_bundle):
    """让 bundle、report、promotion 和 state 指向同一身份。"""

    bundle = patch_bundle
    promotion = PatchPromotionRecord(
        promotion_id="promotion_fixture",
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        verification_sha256=valid_report.verification_sha256,
        decision="approved",
        reviewed_at="2026-01-01T00:00:00+00:00",
    )
    state = {
        "execution_profile_id": valid_report.execution_profile_id,
        "execution_profile_fingerprint": (
            valid_report.execution_profile_fingerprint
        ),
        "pending_action": {
            "execution_profile_id": valid_report.execution_profile_id,
            "execution_profile_fingerprint": (
                valid_report.execution_profile_fingerprint
            ),
        },
    }
    return bundle, promotion, state


def _trust_current_fixture_profile(monkeypatch, valid_report):
    """隔离 profile store，只测试 authorization 绑定逻辑。"""

    monkeypatch.setattr(
        patch_tools,
        "get_execution_profile",
        lambda profile_id: {"profile_id": profile_id},
    )
    monkeypatch.setattr(
        patch_tools,
        "compute_execution_profile_fingerprint",
        lambda profile: valid_report.execution_profile_fingerprint,
    )


@pytest.mark.parametrize(
    ("report_updates", "message"),
    [
        (
            {
                "status": "structurally_valid",
                "promotion_allowed": False,
                "behavioral_checks_run": 0,
                "behavioral_checks_passed": 0,
            },
            "not behaviorally verified",
        ),
        ({"promotion_allowed": False}, "does not allow promotion"),
        ({"patch_id": "different-patch"}, "patch_id"),
        ({"patch_sha256": "d" * 64}, "patch hash"),
    ],
)
def test_report_mismatch_blocks_authorization(
    monkeypatch,
    valid_report,
    patch_bundle,
    report_updates,
    message,
):
    _trust_current_fixture_profile(monkeypatch, valid_report)
    bundle, promotion, state = _authorization_inputs(
        valid_report,
        patch_bundle,
    )
    report = valid_report.model_copy(update=report_updates)
    # model_copy 不会自动重算 hash；先绑定当前篡改后内容，
    # 这样测试能够继续命中具体的 authorization 边界。
    report = report.model_copy(
        update={"verification_sha256": compute_verification_hash(report)}
    )

    with pytest.raises(ValueError, match=message):
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=report,
            promotion=promotion,
            state=state,
            require_promotion=True,
        )


def test_old_promotion_hash_is_rejected(
    monkeypatch,
    valid_report,
    patch_bundle,
):
    _trust_current_fixture_profile(monkeypatch, valid_report)
    bundle, promotion, state = _authorization_inputs(
        valid_report,
        patch_bundle,
    )
    stale = promotion.model_copy(
        update={"verification_sha256": "0" * 64}
    )

    with pytest.raises(ValueError, match="current verification"):
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=valid_report,
            promotion=stale,
            state=state,
            require_promotion=True,
        )


def test_state_profile_mismatch_is_rejected(
    monkeypatch,
    valid_report,
    patch_bundle,
):
    _trust_current_fixture_profile(monkeypatch, valid_report)
    bundle, promotion, state = _authorization_inputs(
        valid_report,
        patch_bundle,
    )
    state["execution_profile_id"] = "another-profile"

    with pytest.raises(ValueError, match="profile id"):
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=valid_report,
            promotion=promotion,
            state=state,
            require_promotion=True,
        )


def test_changed_profile_fingerprint_is_rejected(
    monkeypatch,
    valid_report,
    patch_bundle,
):
    bundle, promotion, state = _authorization_inputs(
        valid_report,
        patch_bundle,
    )
    monkeypatch.setattr(
        patch_tools,
        "get_execution_profile",
        lambda profile_id: {"profile_id": profile_id},
    )
    monkeypatch.setattr(
        patch_tools,
        "compute_execution_profile_fingerprint",
        lambda profile: "changed-fingerprint",
    )

    with pytest.raises(ValueError, match="profile changed"):
        validate_patch_promotion_authorization(
            bundle=bundle,
            report=valid_report,
            promotion=promotion,
            state=state,
            require_promotion=True,
        )
```

这些负例都在调用仓库写入函数前失败。这里使用 monkeypatch 隔离 profile store，是为了让单元测试只验证授权关系；真实 profile 文件变化仍应由集成测试覆盖。

---

## 二十三、故障注入：Apply 后崩溃再恢复

新增 `tests/test_patch_application_recovery.py`：

```python
from pathlib import Path

import pytest

from app.tools.patch_tools import (
    apply_verified_patch_to_source,
    inspect_source_patch_state,
)


class SimulatedProcessCrash(BaseException):
    """避免被普通 except Exception 当成业务失败。"""


@pytest.mark.parametrize(
    ("fault_point", "state_after_crash", "recovered"),
    [
        ("after_journal_prepared", "before", False),
        ("before_git_apply", "before", False),
        ("after_git_apply_before_journal", "after", True),
        ("after_journal_applied", "after", True),
    ],
)
def test_replay_is_idempotent_at_every_fault_point(
    patch_bundle,
    fault_point,
    state_after_crash,
    recovered,
):
    def crash(point: str) -> None:
        if point == fault_point:
            raise SimulatedProcessCrash()

    with pytest.raises(SimulatedProcessCrash):
        apply_verified_patch_to_source(
            patch_bundle,
            owner_run_id="run-crash",
            fault_hook=crash,
        )

    assert inspect_source_patch_state(patch_bundle) == state_after_crash

    replayed = apply_verified_patch_to_source(
        patch_bundle,
        owner_run_id="run-replay",
    )
    assert replayed.status == "applied"
    assert replayed.recovered is recovered
    assert inspect_source_patch_state(patch_bundle) == "after"


def test_extra_tracked_change_requires_manual_intervention(
    patch_bundle,
):
    extra_path = (
        Path(patch_bundle.repo_path)
        / "extra.py"
    )
    extra_path.write_text("USER_CHANGE = True\n", encoding="utf-8")

    result = apply_verified_patch_to_source(
        patch_bundle,
        owner_run_id="run-conflict",
    )

    assert result.status == "manual_intervention"
    assert extra_path.read_text(encoding="utf-8") == (
        "USER_CHANGE = True\n"
    )
    assert inspect_source_patch_state(patch_bundle) == "conflict"
```

---

## 二十四、测试仓库并发互斥

新增 `tests/test_repository_lock.py`：

```python
import pytest

from app.config import settings
from app.tools.repository_lock_tools import (
    RepositoryLockBusyError,
    acquire_repository_lock,
)


@pytest.fixture(autouse=True)
def _isolated_coordination_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        settings,
        "patch_coordination_dir",
        tmp_path / "coordination",
    )


def test_second_run_cannot_lock_same_repository(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    with acquire_repository_lock(
        repo,
        owner_run_id="run-a",
        timeout_seconds=0,
    ):
        with pytest.raises(RepositoryLockBusyError):
            with acquire_repository_lock(
                repo,
                owner_run_id="run-b",
                timeout_seconds=0,
            ):
                raise AssertionError("second lock must not be acquired")


def test_different_repositories_have_independent_locks(tmp_path):
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    repo_a.mkdir()
    repo_b.mkdir()

    with acquire_repository_lock(
        repo_a,
        owner_run_id="run-a",
        timeout_seconds=0,
    ):
        with acquire_repository_lock(
            repo_b,
            owner_run_id="run-b",
            timeout_seconds=0,
        ):
            pass
```

如平台内同进程 `flock` 行为不同，使用 `multiprocessing` 测试真实跨进程锁，不要退化成线程锁。

---

## 二十五、测试污染 Worktree 必须失败

在 `tests/test_patch_verifier_node.py` 增加：

```python
from pathlib import Path
import subprocess

import pytest

from app.tools.patch_tools import validate_worktree_matches_patch


def _git_for_test(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )


def test_reused_worktree_rejects_extra_tracked_change(
    patch_bundle,
    verified_worktree,
):
    # extra.py 必须存在于 fixture 初始 commit 中。
    (verified_worktree / "extra.py").write_text(
        "changed outside patch\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="diff scope mismatch"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )


def test_reused_worktree_rejects_staged_change(
    patch_bundle,
    verified_worktree,
):
    extra = verified_worktree / "extra.py"
    extra.write_text("STAGED = True\n", encoding="utf-8")
    _git_for_test(verified_worktree, "add", "extra.py")

    with pytest.raises(ValueError, match="staged changes"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )


def test_reused_worktree_rejects_missing_target(
    patch_bundle,
    verified_worktree,
):
    (verified_worktree / "train.py").unlink()

    with pytest.raises(ValueError, match="file missing"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )


def test_reused_worktree_rejects_wrong_after_hash(
    patch_bundle,
    verified_worktree,
):
    (verified_worktree / "train.py").write_text(
        "VALUE = 999\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hash mismatch"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )


def test_reused_worktree_rejects_changed_head(
    patch_bundle,
    verified_worktree,
):
    _git_for_test(verified_worktree, "add", "train.py")
    _git_for_test(verified_worktree, "commit", "-m", "changed head")

    with pytest.raises(ValueError, match="HEAD changed"):
        validate_worktree_matches_patch(
            patch_bundle,
            verified_worktree,
        )
```

如果该测试文件已经有 `pytest`、`subprocess` 或同类 Git helper，只保留一份 import/helper，追加测试函数即可。

### 25.1 测试 Worktree 清理边界

新增 `tests/test_patch_worktree_cleanup.py`，下面是完整文件：

```python
from pathlib import Path
import subprocess

import pytest

from app.tools.patch_tools import (
    remove_patch_worktree,
    validate_patch_worktree_path,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )


def test_cleanup_rejects_path_outside_current_run(tmp_path):
    run_dir = tmp_path / "run"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / ".git").write_text("gitdir: fixture\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside current run"):
        validate_patch_worktree_path(
            worktree_path=outside,
            run_dir=run_dir,
        )


def test_cleanup_removes_only_valid_run_worktree(
    patch_bundle,
    tmp_path,
):
    repo = Path(patch_bundle.repo_path)
    run_dir = tmp_path / "run"
    worktree = (
        run_dir
        / "execution"
        / "patch_worktrees"
        / patch_bundle.patch_id
    )
    worktree.parent.mkdir(parents=True)
    _git(
        repo,
        "worktree",
        "add",
        "--detach",
        str(worktree),
        patch_bundle.base_git_commit,
    )

    remove_patch_worktree(
        repo_path=str(repo),
        worktree_path=str(worktree),
        run_dir=str(run_dir),
    )

    assert not worktree.exists()
```

---

## 二十六、测试命令

本章所有测试都把 pytest 临时目录、Python 字节码和通用缓存放到
`/data/tianshaoqi24/` 下。先在当前 shell 执行：

```bash
export PHASE14_TEST_ROOT="$(
  mktemp -d \
    -p /data/tianshaoqi24 \
    paper-reproduction-copilot-phase14-tests.XXXXXX
)"
export PHASE14_TEST_ORIGINAL_HOME="$HOME"
export HOME="$PHASE14_TEST_ROOT/home"
export TMPDIR="$PHASE14_TEST_ROOT/tmp"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export PYTHONPYCACHEPREFIX="$PHASE14_TEST_ROOT/pycache"
export XDG_CACHE_HOME="$PHASE14_TEST_ROOT/cache"
export XDG_CONFIG_HOME="$PHASE14_TEST_ROOT/config"
export XDG_DATA_HOME="$PHASE14_TEST_ROOT/data"
export PYTEST_ADDOPTS="--basetemp=$PHASE14_TEST_ROOT/pytest-tmp"

mkdir -p \
  "$HOME" \
  "$TMPDIR" \
  "$PYTHONPYCACHEPREFIX" \
  "$XDG_CACHE_HOME" \
  "$XDG_CONFIG_HOME" \
  "$XDG_DATA_HOME" \
  "$PHASE14_TEST_ROOT/pytest-tmp"
```

这里的 `PYTEST_ADDOPTS` 会让测试中的 `tmp_path` fixture 实际落在
`/data/tianshaoqi24/paper-reproduction-copilot-phase14-tests.*/pytest-tmp/`
中，而不是系统默认的 `/tmp`。`mktemp -p` 每次创建一个新的根目录内测试目录，
避免 pytest 清理 `--basetemp` 时碰到上一轮或其他人的文件。

先运行新增快速测试：

```bash
python -m pytest \
  tests/test_compiled_graph_routes.py \
  tests/test_patch_verification_semantics.py \
  tests/test_patch_authorization_boundaries.py \
  tests/test_repository_lock.py \
  -q
```

再运行 Git/worktree/journal 集成测试：

```bash
python -m pytest \
  tests/test_patch_tools.py \
  tests/test_patch_verifier_node.py \
  tests/test_patch_application_recovery.py \
  tests/test_patch_worktree_cleanup.py \
  -q
```

运行 Phase 13 与闭环回归：

```bash
python -m pytest \
  tests/test_patch_review_nodes.py \
  tests/test_smoke_repair_flow.py \
  tests/test_repair_action_builder_node.py \
  tests/test_review_flow.py \
  tests/test_durable_checkpoint_resume.py \
  -q
```

最后运行：

```bash
python -m pytest -q
```

测试结束后恢复当前 shell。测试产物仍保留在打印出的
`$PHASE14_TEST_ROOT` 中，确认不再需要后再人工处理：

```bash
if [ -n "${PHASE14_TEST_ORIGINAL_HOME:-}" ]; then
  export HOME="$PHASE14_TEST_ORIGINAL_HOME"
fi

unset PHASE14_TEST_ORIGINAL_HOME PHASE14_TEST_ROOT
unset TMPDIR TMP TEMP
unset PYTHONPYCACHEPREFIX PYTEST_ADDOPTS
unset XDG_CACHE_HOME XDG_CONFIG_HOME XDG_DATA_HOME
```

---

## 二十七、手工验收

本节使用：

```text
论文：
/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf

操作仓库：
/data/tianshaoqi24/PST-Convolution-main/
```

验收分成两部分：

1. 直接在 PSTNet 原始仓库上完成一次真实端到端闭环。
2. 用专项测试验证篡改、崩溃恢复和并发锁等分支。

本流程会直接改变 `/data/tianshaoqi24/PST-Convolution-main/`。首次验收且仓库没有
Git `HEAD` 时，需要把现有 PSTNet 文件和验收文件提交为第一个 baseline commit；
重测时可以复用已经提交且 tracked tree 干净的 Phase 14 baseline。Promotion
批准后，`phase14_demo.py` 会在该仓库中留下未提交修改。执行前应确认这里没有
需要保留但不应提交的文件。

### 27.1 固定验收路径和隔离运行目录

本机使用两个彼此解耦的 Python 环境：

- Agent CLI 使用已经安装好项目依赖的 `agent` 环境。该环境可以位于
  `/home/...` 或其真实映射路径 `/data2t/...`，但本次验收只把它当作受信任的
  只读运行时，不向其中安装依赖。
- PSTNet 的 preflight、smoke test、executor 和 patch verifier 统一使用
  `3d` Conda 环境。该环境的真实 prefix 位于 `/data/tianshaoqi24/` 下。

所有新增写入、临时文件、缓存和运行产物都必须位于
`/data/tianshaoqi24/` 下。受信任的 Agent 解释器和 Conda 可执行文件可以从
根目录之外读取，但不能把 `ALLOWED_ROOT` 放宽到 `/home`、`/data2t` 或 `/`。
所有命令都从 Agent 项目根目录执行：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

export ALLOWED_ROOT="/data/tianshaoqi24"
export PROJECT_ROOT="/data/tianshaoqi24/agent/paper_reproduction_copilot"
export PAPER="$PROJECT_ROOT/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf"
export REPO="/data/tianshaoqi24/PST-Convolution-main"

export TRUSTED_AGENT_PREFIX="$(
  readlink -f /home/tianshaoqi24/miniconda3/envs/agent
)"
export CONDA_EXECUTABLE="/home/tianshaoqi24/miniconda3/bin/conda"
export REPRO_CONDA_PREFIX="$(
  readlink -f /home/tianshaoqi24/miniconda3/envs/3d
)"

# 每次正式重测都更换编号，不复用旧 checkpoint 和 run artifacts。
export ACCEPTANCE_ID="004"
export SESSION_ROOT="/data/tianshaoqi24/pstnet-phase14-direct-$ACCEPTANCE_ID"
export THREAD_ID="pstnet-phase14-e2e-$ACCEPTANCE_ID"

export OUTPUT_DIR="$SESSION_ROOT/outputs"
export RUNS_DIR="$SESSION_ROOT/runs"
export CHECKPOINT_DB_PATH="$SESSION_ROOT/checkpoints/langgraph.sqlite"
export PATCH_COORDINATION_DIR="$SESSION_ROOT/coordination"
export EXECUTION_PROFILES_PATH="$SESSION_ROOT/execution_profiles.json"

export ENABLE_FILE_REPAIR="true"
export MAX_REPAIR_ATTEMPTS="1"
export MAX_FILE_REPAIR_ATTEMPTS="1"
export PATCH_REPO_LOCK_TIMEOUT_SECONDS="2"
```

先确认静态路径没有写错，并拒绝复用旧验收目录：

```bash
test -f "$PAPER" && echo "paper: ok"
test -d "$REPO" && echo "repo: ok"
test -d "$TRUSTED_AGENT_PREFIX" && echo "agent runtime: ok"
test -x "$CONDA_EXECUTABLE" && echo "conda executable: ok"
test -d "$REPRO_CONDA_PREFIX" && echo "reproduction environment: ok"
printf 'repo: %s\n' "$REPO"
printf 'agent prefix: %s\n' "$TRUSTED_AGENT_PREFIX"
printf 'reproduction prefix: %s\n' "$REPRO_CONDA_PREFIX"
printf 'checkpoint: %s\n' "$CHECKPOINT_DB_PATH"

if [ -e "$SESSION_ROOT" ]; then
  echo "ERROR: SESSION_ROOT already exists: $SESSION_ROOT" >&2
  return 1 2>/dev/null || exit 1
fi
```

预期五项都输出 `ok`，并确认 `REPO` 精确等于
`/data/tianshaoqi24/PST-Convolution-main`。如果目录存在检查失败，请更换
`ACCEPTANCE_ID`，不要删除或混用一份来源不明的旧验收状态。

然后创建会话目录，并把当前 shell 可能产生的临时文件、用户级文件、缓存、
Python 字节码和 pytest 临时目录全部重定向到该目录：

```bash
mkdir -p \
  "$SESSION_ROOT/home" \
  "$SESSION_ROOT/tmp" \
  "$SESSION_ROOT/cache" \
  "$SESSION_ROOT/config" \
  "$SESSION_ROOT/data" \
  "$SESSION_ROOT/pycache" \
  "$SESSION_ROOT/pytest-tmp" \
  "$SESSION_ROOT/pip-cache" \
  "$SESSION_ROOT/conda-pkgs" \
  "$SESSION_ROOT/torch-cache" \
  "$SESSION_ROOT/cuda-cache" \
  "$SESSION_ROOT/matplotlib" \
  "$SESSION_ROOT/numba-cache"

export PHASE14_ORIGINAL_HOME="$HOME"
export HOME="$SESSION_ROOT/home"
export TMPDIR="$SESSION_ROOT/tmp"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export XDG_CACHE_HOME="$SESSION_ROOT/cache"
export XDG_CONFIG_HOME="$SESSION_ROOT/config"
export XDG_DATA_HOME="$SESSION_ROOT/data"
export PYTHONPYCACHEPREFIX="$SESSION_ROOT/pycache"
export PYTEST_ADDOPTS="--basetemp=$SESSION_ROOT/pytest-tmp"
export PIP_CACHE_DIR="$SESSION_ROOT/pip-cache"
export CONDA_PKGS_DIRS="$SESSION_ROOT/conda-pkgs"
export TORCH_HOME="$SESSION_ROOT/torch-cache"
export CUDA_CACHE_PATH="$SESSION_ROOT/cuda-cache"
export MPLCONFIGDIR="$SESSION_ROOT/matplotlib"
export NUMBA_CACHE_DIR="$SESSION_ROOT/numba-cache"
```

`HOME` 也被临时切换到会话目录，因此即使某个第三方库忽略
`XDG_CACHE_HOME`，它也不会向原用户主目录写缓存。项目的 `.env` 仍由应用从
`PROJECT_ROOT` 读取；如果模型密钥只保存在原用户主目录的配置文件中，应把所需
变量导入当前 shell，而不是允许本次验收写回原主目录。

最后定义统一路径守卫，并检查所有可能写入的目录：

```bash
assert_under_allowed_root() {
  local resolved
  if ! resolved="$(/usr/bin/realpath -m -- "$1")"; then
    printf 'ERROR: failed to resolve path: %s\n' "$1" >&2
    return 1
  fi

  case "$resolved" in
    "$ALLOWED_ROOT"|"$ALLOWED_ROOT"/*)
      printf 'allowed: %s\n' "$resolved"
      ;;
    *)
      printf 'ERROR: path escapes %s: %s\n' \
        "$ALLOWED_ROOT" "$resolved" >&2
      return 1
      ;;
  esac
}

test -x /usr/bin/realpath || {
  echo "ERROR: trusted realpath executable is unavailable" >&2
  return 1 2>/dev/null || exit 1
}

for guarded_path in \
  "$PROJECT_ROOT" \
  "$PAPER" \
  "$REPO" \
  "$SESSION_ROOT" \
  "$OUTPUT_DIR" \
  "$RUNS_DIR" \
  "$CHECKPOINT_DB_PATH" \
  "$PATCH_COORDINATION_DIR" \
  "$EXECUTION_PROFILES_PATH" \
  "$REPRO_CONDA_PREFIX" \
  "$HOME" \
  "$TMPDIR" \
  "$XDG_CACHE_HOME" \
  "$PYTHONPYCACHEPREFIX"
do
  assert_under_allowed_root "$guarded_path" || {
    return 1 2>/dev/null || exit 1
  }
done
```

所有被路径守卫检查的可写路径都必须以
`allowed: /data/tianshaoqi24/` 开头。`TRUSTED_AGENT_PREFIX` 和
`CONDA_EXECUTABLE` 是精确指定的受信任只读入口，不放入可写路径守卫。
不要把循环变量改回小写 `path`：在 zsh 中，`path` 是与 `PATH` 绑定的特殊
数组，给它赋值会破坏当前 shell 的命令搜索路径。
任何一项失败都应立即停止，不要通过放宽守卫继续执行。`SESSION_ROOT` 只保存
Agent 的 checkpoint、artifact、profile、缓存和锁文件，不是仓库副本。

### 27.2 检查 Agent 环境、复现环境、pytest 和模型

先检查当前 shell 的 Python 是否精确来自受信任的 Agent 环境。Agent 环境可以
位于允许根目录之外，因此这里检查的是精确 prefix，而不是调用
`assert_under_allowed_root`：

```bash
python - <<'PY'
import os
import sys
from pathlib import Path


trusted_prefix = Path(os.environ["TRUSTED_AGENT_PREFIX"]).resolve()
executable = Path(sys.executable).resolve()
prefix = Path(sys.prefix).resolve()

print(f"trusted prefix: {trusted_prefix}")
print(f"sys.executable: {executable}")
print(f"sys.prefix:     {prefix}")

if prefix != trusted_prefix:
    raise SystemExit(
        f"ERROR: 当前 Python 前缀不是受信任的 Agent 环境: {prefix}"
    )

if executable != trusted_prefix and trusted_prefix not in executable.parents:
    raise SystemExit(
        f"ERROR: 当前 Python 不属于受信任的 Agent 环境: {executable}"
    )

print("trusted agent runtime: ok")
PY
```

确认 Agent CLI 和项目测试依赖已经可用：

```bash
which python
python --version
python -m pytest --version
python -m app.main version
```

不要执行 `python -m venv "$SESSION_ROOT/venv"`，也不要在本次验收中向
`agent` 环境安装 PyTorch。Agent 只负责运行 Graph 和 CLI。

然后通过 `conda run -p` 检查真正执行 PSTNet 命令的 `3d` 环境：

```bash
"$CONDA_EXECUTABLE" run \
  --no-capture-output \
  -p "$REPRO_CONDA_PREFIX" \
  python - <<'PY'
import os
import sys
from pathlib import Path

import pytest
import torch


expected_prefix = Path(os.environ["REPRO_CONDA_PREFIX"]).resolve()
actual_prefix = Path(sys.prefix).resolve()

print(f"python: {sys.executable}")
print(f"prefix: {actual_prefix}")
print(f"torch: {torch.__version__}")
print(f"pytest: {pytest.__version__}")

if actual_prefix != expected_prefix:
    raise SystemExit(
        f"ERROR: reproduction prefix mismatch: {actual_prefix}"
    )
PY
```

本机 `3d` 环境是 Python 3.8，因此 pytest 应使用仍支持 Python 3.8 的
`8.3.5`。如果上一步只因缺少 pytest 失败，可以在开始正式验收前安装一次：

```bash
"$CONDA_EXECUTABLE" run \
  --no-capture-output \
  -p "$REPRO_CONDA_PREFIX" \
  python -m pip install "pytest==8.3.5"
```

安装后重新运行环境检查。不要安装 pytest 8.4 或 9.x：它们分别要求更高版本的
Python。正式验收开始后不要再修改 `3d` 环境，否则已有 execution profile
fingerprint 和审批证据可能不再代表同一个执行环境。

文件修复规划会调用 LLM，因此先执行最小结构化输出探针：

```bash
python -m app.main probe-structured-output
```

只有下面条件成立才继续：

```text
succeeded=True
attempt_count>=1
value.status=ok
value.value=1
```

如果探针失败，先修复 API、模型或 Structured Output 配置，不要进入文件写入验收。

通用探针通过后，还要真实调用一次 `PaperSummary` 提取，避免 prompt 示例和
Pydantic Schema 类型不一致导致完整 Graph 安全降级为 `no_action`：

```bash
python -m app.main read-paper "$PAPER"

python - <<'PY'
import json
import os
from pathlib import Path


output_dir = Path(os.environ["OUTPUT_DIR"])
summary = json.loads(
    (output_dir / "paper_summary.json").read_text(encoding="utf-8")
)
trace = json.loads(
    (
        output_dir / "method_extractor_structured_attempts.json"
    ).read_text(encoding="utf-8")
)

print(f"succeeded: {trace['succeeded']}")
print(f"fallback_used: {trace['fallback_used']}")
print(
    "experiment_settings type:",
    type(summary["experiment_settings"]).__name__,
)
print(f"method_modules: {len(summary['method_modules'])}")

if not trace["succeeded"] or trace["fallback_used"]:
    raise SystemExit("ERROR: PaperSummary structured output failed")
if not isinstance(summary["experiment_settings"], list):
    raise SystemExit("ERROR: experiment_settings must be a list")
if not summary["method_modules"]:
    raise SystemExit("ERROR: method_modules is empty")
PY
```

只有 `succeeded=True`、`fallback_used=False`、
`experiment_settings type=list` 且 `method_modules` 大于 0 时才启动 Graph。

### 27.3 检查原始 PSTNet 仓库状态

确认接下来操作的就是原始 PSTNet 目录：

```bash
test -f "$REPO/README.md"
test -f "$REPO/train-ntu.py"
test -f "$REPO/modules/pst_convolutions.py"
git -C "$REPO" status --short --branch
```

检查是否已有 `HEAD`：

```bash
if git -C "$REPO" rev-parse --verify HEAD >/dev/null 2>&1; then
  echo "repository already has HEAD"
  git -C "$REPO" status --porcelain --untracked-files=no
else
  echo "repository has no HEAD; Phase 14 baseline will be the first commit"
fi
```

首次验收可能进入第二个分支；已经建立过 Phase 14 baseline 的重测应进入第一个
分支。不论是哪一种情况，只要已经存在 `HEAD`，
`status --porcelain --untracked-files=no` 就必须为空；存在用户 tracked 修改时
应停止验收，不能把它们混入自动修复基线。

### 27.4 注入一个可控、可验证的源码缺陷

先判断这是首次建立 baseline，还是在复用上一轮已经提交的 Phase 14 baseline：

```bash
if \
  git -C "$REPO" ls-files --error-unmatch \
    phase14_demo.py >/dev/null 2>&1 &&
  git -C "$REPO" ls-files --error-unmatch \
    tests/test_phase14_demo.py >/dev/null 2>&1
then
  export REUSE_PHASE14_BASELINE="true"
  echo "reusing committed Phase 14 baseline"
elif \
  test ! -e "$REPO/phase14_demo.py" &&
  test ! -e "$REPO/tests/test_phase14_demo.py"
then
  export REUSE_PHASE14_BASELINE="false"
  echo "creating first Phase 14 baseline"
else
  echo "ERROR: Phase 14 files are only partially present or untracked" >&2
  return 1 2>/dev/null || exit 1
fi
```

如果输出 `reusing committed Phase 14 baseline`，先验证仓库干净且受控缺陷仍在：

```bash
if [ "$REUSE_PHASE14_BASELINE" = "true" ]; then
  test -z "$(
    git -C "$REPO" status --porcelain --untracked-files=no
  )"
  grep -F \
    'shape mismatch: phase14 controlled source bug' \
    "$REPO/phase14_demo.py"
  grep -F \
    'assert add(2, 3) == 5' \
    "$REPO/tests/test_phase14_demo.py"
fi
```

三项检查都通过时，不要重新创建或提交文件，直接跳到本节后面的“手工运行失败
测试”。如果任意检查失败，应停止并人工检查仓库，不要覆盖已有文件。

只有 `REUSE_PHASE14_BASELINE=false` 时，才在原始仓库中新增最小演示源码：

```bash
if [ "$REUSE_PHASE14_BASELINE" = "false" ]; then
  cat > "$REPO/phase14_demo.py" <<'PY'
def add(left: int, right: int) -> int:
    """Phase 14 验收用函数；当前故意抛出 shape mismatch。"""

    raise RuntimeError("shape mismatch: phase14 controlled source bug")
PY
fi
```

新增一个真实行为测试：

```bash
if [ "$REUSE_PHASE14_BASELINE" = "false" ]; then
  mkdir -p "$REPO/tests"

  cat > "$REPO/tests/test_phase14_demo.py" <<'PY'
from phase14_demo import add


def test_add_returns_sum():
    assert add(2, 3) == 5
PY
fi
```

这里故意使用包含 `shape mismatch` 的异常信息，因为本项目的本地错误分类器能稳定把它识别成 `shape_mismatch`。普通 `RuntimeError` 会被归类为 `unknown`，command repair planner 会安全降级为 `no_repair`，无法稳定进入 file repair 分支。

为原始仓库建立可重复的 Git 基线。当前没有 `HEAD` 时，需要把现有 PSTNet 文件一起纳入第一次 commit；如果以后已经有 `HEAD`，则只暂存两个验收文件：

```bash
if [ "$REUSE_PHASE14_BASELINE" = "false" ]; then
  if git -C "$REPO" rev-parse --verify HEAD >/dev/null 2>&1; then
    git -C "$REPO" add -- \
      phase14_demo.py \
      tests/test_phase14_demo.py
  else
    git -C "$REPO" add -A
  fi

  git -C "$REPO" \
    -c user.name="Phase14 Acceptance" \
    -c user.email="phase14@example.invalid" \
    commit -m "phase14 acceptance baseline with controlled bug"
fi
```

这会真实改变原仓库 Git 历史。尤其在当前无 `HEAD` 的情况下，上述 commit 会成为 PSTNet 仓库的第一个 commit。

确认有效 `HEAD` 和 clean tracked tree：

```bash
git -C "$REPO" rev-parse HEAD
git -C "$REPO" status --porcelain --untracked-files=no
```

第二条命令不应输出任何内容。

手工运行失败测试：

```bash
cd "$REPO"
"$CONDA_EXECUTABLE" run \
  --no-capture-output \
  -p "$REPRO_CONDA_PREFIX" \
  python -m pytest \
  -q \
  -p no:cacheprovider \
  tests/test_phase14_demo.py
export PHASE14_EXPECTED_FAILURE_RC="$?"
cd "$PROJECT_ROOT"
echo "return code: $PHASE14_EXPECTED_FAILURE_RC"
```

预期：

```text
1 failed
RuntimeError: shape mismatch: phase14 controlled source bug
return code: 1
```

如果此时测试已经通过，说明可控缺陷没有建立成功，不要继续。

### 27.5 创建隔离 Execution Profile

不要修改项目现有的 `config/execution_profiles.local.json`。为本次验收单独创建
Conda profile，确保 Agent 进程和 PSTNet 命令使用不同环境：

```bash
cat > "$EXECUTION_PROFILES_PATH" <<JSON
{
  "profiles": [
    {
      "profile_id": "pstnet-phase14-3d",
      "backend": "conda",
      "workspace_root": "$REPO",
      "artifact_root": "$OUTPUT_DIR",
      "conda_executable": "$CONDA_EXECUTABLE",
      "conda_prefix": "$REPRO_CONDA_PREFIX",
      "env": {
        "HOME": "$HOME",
        "TMPDIR": "$TMPDIR",
        "TMP": "$TMP",
        "TEMP": "$TEMP",
        "XDG_CACHE_HOME": "$XDG_CACHE_HOME",
        "XDG_CONFIG_HOME": "$XDG_CONFIG_HOME",
        "XDG_DATA_HOME": "$XDG_DATA_HOME",
        "PYTHONPYCACHEPREFIX": "$PYTHONPYCACHEPREFIX",
        "PYTEST_ADDOPTS": "$PYTEST_ADDOPTS",
        "PIP_CACHE_DIR": "$PIP_CACHE_DIR",
        "CONDA_PKGS_DIRS": "$CONDA_PKGS_DIRS",
        "TORCH_HOME": "$TORCH_HOME",
        "CUDA_CACHE_PATH": "$CUDA_CACHE_PATH",
        "MPLCONFIGDIR": "$MPLCONFIGDIR",
        "NUMBA_CACHE_DIR": "$NUMBA_CACHE_DIR"
      }
    }
  ]
}
JSON

python -m json.tool "$EXECUTION_PROFILES_PATH"
```

从 Action 创建到 Patch Promotion 完成之前，不要修改这个 JSON，也不要安装、
升级或删除 `3d` 环境中的包。Profile 内容变化会改变 fingerprint；环境内容虽然
不会自动反映到当前 fingerprint 中，但验收期间改变依赖同样会破坏证据的一致性。
这些环境变量会传给 CondaRunner 启动的 preflight、executor 和 verifier 子进程，
保证它们使用 `$REPRO_CONDA_PREFIX`，同时把临时文件和缓存写入
`$SESSION_ROOT`。

### 27.6 定义 checkpoint 状态摘要命令

为了避免每次阅读完整 `StateSnapshot`，在当前 shell 中定义：

```bash
show_phase14_state() {
  python - "$1" <<'PY'
import json
import sys

from app.graph import build_graph


thread_id = sys.argv[1]
snapshot = build_graph().get_state(
    {"configurable": {"thread_id": thread_id}}
)
values = snapshot.values
proposal = values.get("file_repair_proposal") or {}
patch = values.get("pending_patch") or {}
verification = values.get("patch_verification_report") or {}
application = values.get("patch_application_record") or {}

summary = {
    "next": list(snapshot.next),
    "run_id": values.get("run_id"),
    "run_dir": values.get("run_dir"),
    "final_status": values.get("final_status"),
    "error": values.get("error"),
    "selected_run_command_index": values.get(
        "selected_run_command_index"
    ),
    "requires_approval": values.get("requires_approval"),
    "user_approval": values.get("user_approval"),
    "pending_action_hash": values.get("pending_action_hash"),
    "debug_error_type": (
        (values.get("debug_report") or {}).get("error_type")
    ),
    "debug_related_files": (
        (values.get("debug_report") or {}).get("related_files")
    ),
    "repair_kind": (
        (values.get("repair_proposal") or {}).get("kind")
    ),
    "file_repair_kind": proposal.get("kind"),
    "verification_targets": proposal.get("verification_targets"),
    "patch_id": patch.get("patch_id"),
    "patch_path": patch.get("patch_path"),
    "patch_files": [
        item.get("relative_path")
        for item in patch.get("files", [])
    ],
    "verification_status": verification.get("status"),
    "promotion_allowed": verification.get("promotion_allowed"),
    "behavioral_checks_run": verification.get(
        "behavioral_checks_run"
    ),
    "behavioral_checks_passed": verification.get(
        "behavioral_checks_passed"
    ),
    "worktree_path": verification.get("worktree_path"),
    "application_status": application.get("status"),
    "application_recovered": application.get("recovered"),
    "journal_path": application.get("journal_path"),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY
}
```

后续可随时运行：

```bash
show_phase14_state "$THREAD_ID"
```

### 27.7 启动 Graph 并停在命令选择

执行：

```bash
python -m app.main run-graph \
  "$PAPER" \
  "$REPO" \
  --thread-id "$THREAD_ID" \
  --execution-profile pstnet-phase14-3d
```

第一次运行应停在 `command_selection`。检查：

```bash
show_phase14_state "$THREAD_ID"
```

预期至少包含：

```json
{
  "next": ["command_selection"],
  "final_status": null
}
```

如果 Graph 在这里之前失败，先检查论文读取、模型结构化输出和 repo scan，不要继续审批。

### 27.8 选择并改写一个 Repo Root 命令

先打印 checkpoint 中的所有候选命令和 `cwd`：

```bash
python - "$THREAD_ID" <<'PY'
import sys

from app.graph import build_graph


snapshot = build_graph().get_state(
    {"configurable": {"thread_id": sys.argv[1]}}
)
for index, item in enumerate(snapshot.values.get("run_commands", [])):
    print(f"[{index}] {item.get('command')}")
    print(f"    cwd={item.get('cwd')}")
    print(f"    source={item.get('source')}")
PY
```

选择一个 `cwd` 等于下面路径的索引：

```text
/data/tianshaoqi24/PST-Convolution-main
```

例如索引为 `0`：

```bash
export DEMO_INDEX="0"
```

不要盲目使用 `0`。如果索引 `0` 的 `cwd` 是 `modules/`，应选择另一个位于仓库根目录的命令。当前命令编辑功能只修改 `command`，不会同时修改 `cwd`。

找到预填输入文件：

```bash
export COMMAND_INPUT="$(
  find "$RUNS_DIR" \
    -type f \
    -path '*/planning/command_selection_input.json' \
    -print |
  sort |
  tail -n 1
)"

printf 'command input: %s\n' "$COMMAND_INPUT"
python -m json.tool "$COMMAND_INPUT"
```

保留文件中的 `run_commands_hash`，把选中命令改成受控失败测试：

```bash
python - "$COMMAND_INPUT" "$DEMO_INDEX" <<'PY'
import json
import sys
from pathlib import Path


path = Path(sys.argv[1])
selected_index = int(sys.argv[2])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["selected_index"] = selected_index
payload["edits"] = [
    {
        "index": selected_index,
        "command": (
            "python -m pytest -q -p no:cacheprovider "
            "tests/test_phase14_demo.py"
        ),
    }
]
path.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

python -m json.tool "$COMMAND_INPUT"
```

确认 `run_commands_hash` 仍存在、`selected_index` 正确，然后恢复：

```bash
python -m app.main resume-command-selection \
  "$THREAD_ID" \
  --input "$COMMAND_INPUT"
```

由于 `python -m pytest` 被风险策略判定为 high risk，Graph 应停在 `human_review`：

```bash
show_phase14_state "$THREAD_ID"
```

预期：

```json
{
  "next": ["human_review"],
  "requires_approval": true
}
```

### 27.9 第一次命令执行审批

在审批前确认 pending action 的 program、args、cwd：

```bash
python - "$THREAD_ID" <<'PY'
import json
import sys

from app.graph import build_graph


snapshot = build_graph().get_state(
    {"configurable": {"thread_id": sys.argv[1]}}
)
print(
    json.dumps(
        snapshot.values.get("pending_action"),
        ensure_ascii=False,
        indent=2,
    )
)
PY
```

必须确认：

```text
program=python
args=["-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_phase14_demo.py"]
cwd=/data/tianshaoqi24/PST-Convolution-main
execution_profile_id=pstnet-phase14-3d
```

`-p no:cacheprovider` 禁止 pytest 在 PSTNet 仓库内创建或更新
`.pytest_cache`，避免测试缓存污染后续 Git diff 和 patch 授权边界。

批准第一次执行：

```bash
python -m app.main resume-review \
  "$THREAD_ID" \
  --decision approved \
  --feedback "运行 Phase 14 可控失败测试"
```

这次执行应经历：

```text
preflight
  -> smoke_test（没有可缩减参数，因此 skipped）
  -> executor（测试失败）
  -> log_debug
  -> repair_planner（shape_mismatch + related_files 确定性移交）
  -> file_repair_planner
  -> patch_builder
  -> patch_review interrupt
```

对本节受控缺陷，`repair_planner` 不再依赖 LLM 自由选择 command repair 类型。
当本地错误分类为 `shape_mismatch` 且 `debug_report.related_files` 非空时，它应
确定性生成 `kind=manual_only`，只负责把证据移交给受限文件修复流程。它不会
生成 patch，也不会绕过后续两次人工审批。

`log_debug` 还会从 traceback 中确定性提取真实存在且位于 `$REPO` 内的 Python
文件，并与模型返回的 `related_files` 合并。本例即使模型只返回测试文件，最终
也必须同时包含：

```text
tests/test_phase14_demo.py
phase14_demo.py
```

file repair planner 只能修改实现文件，不能修改 `tests/` 下的行为测试；同时会从
当前 pytest action 中确定性提取 `tests/test_phase14_demo.py` 作为
`verification_targets`。

其中 preflight 报告里的 `program_in_path` 应解析到 `3d` 环境，且
`torch_import_probe` 必须通过。可以在恢复命令返回后检查：

```bash
python -m json.tool "$OUTPUT_DIR/preflight_report.json"
```

如果报告仍解析到 `agent/bin/python`，说明本轮 Graph 没有使用
`pstnet-phase14-3d`，应停止并使用新的 `THREAD_ID` 重测，不能在旧 action 上
修改 profile 后继续审批。

检查状态：

```bash
show_phase14_state "$THREAD_ID"
```

理想结果：

```text
next=["patch_review"]
debug_error_type="shape_mismatch"
debug_related_files 包含 phase14_demo.py
repair_kind="manual_only"
file_repair_kind="patch"
patch_files=["phase14_demo.py"]
verification_targets=["tests/test_phase14_demo.py"]
```

LLM 规划具有不确定性。如果没有进入 `patch_review`，按下面顺序检查：

```bash
python -m json.tool "$OUTPUT_DIR/debug_report.json"
python -m json.tool "$OUTPUT_DIR/repair_proposal.json"
python -m json.tool "$OUTPUT_DIR/file_repair_proposal.json"
```

安全降级情况包括：

```text
debug_report.related_files 为空
repair_proposal.kind=no_repair
file_repair_proposal.kind=no_patch
pending_patch=None
```

这些情况说明系统拒绝在证据不足时写文件，不算安全机制失败。不要手工篡改 checkpoint 强行推进；保留 artifact，使用新的 `THREAD_ID` 重新验收或改进 Debug/File Repair Prompt。

### 27.10 审核第一次 Patch Review

提取 patch 路径：

```bash
export PATCH_PATH="$(
  python - "$THREAD_ID" <<'PY'
import sys

from app.graph import build_graph


snapshot = build_graph().get_state(
    {"configurable": {"thread_id": sys.argv[1]}}
)
print((snapshot.values.get("pending_patch") or {}).get("patch_path", ""))
PY
)"

printf 'patch path: %s\n' "$PATCH_PATH"
sed -n '1,240p' "$PATCH_PATH"
```

批准前逐项确认：

```text
只修改 phase14_demo.py
没有修改 tests/test_phase14_demo.py
没有修改 PSTNet 原有训练、数据集或 CUDA 文件
没有新增、删除或重命名文件
修改内容仅把受控异常替换为正确的 left + right
patch_path 位于本次 run/debug/patches 下
verification_targets 包含 tests/test_phase14_demo.py
```

如果任意条件不满足，拒绝：

```bash
python -m app.main resume-patch-review \
  "$THREAD_ID" \
  --decision rejected \
  --feedback "补丁超出 Phase 14 验收边界"
```

拒绝后流程应进入 Final Report，原始仓库保持刚创建的 baseline 状态。

只有 patch 精确且有界时才批准隔离验证：

```bash
python -m app.main resume-patch-review \
  "$THREAD_ID" \
  --decision approved \
  --feedback "补丁仅修复 phase14_demo.py，允许隔离验证"
```

### 27.11 检查隔离验证结论

恢复后再次检查：

```bash
show_phase14_state "$THREAD_ID"
```

#### 分支 A：行为验证通过

完整闭环需要满足：

```text
next=["patch_promotion_review"]
verification_status="behaviorally_verified"
promotion_allowed=true
behavioral_checks_run>=1
behavioral_checks_passed=behavioral_checks_run
worktree_path 非空
```

提取并检查 report：

```bash
export RUN_DIR="$(
  python - "$THREAD_ID" <<'PY'
import sys

from app.graph import build_graph


snapshot = build_graph().get_state(
    {"configurable": {"thread_id": sys.argv[1]}}
)
print(snapshot.values.get("run_dir", ""))
PY
)"

python -m json.tool \
  "$RUN_DIR/execution/patch_verification_report.json"
```

检查隔离 worktree 的真实 diff：

```bash
export PATCH_WORKTREE="$(
  python - "$THREAD_ID" <<'PY'
import sys

from app.graph import build_graph


snapshot = build_graph().get_state(
    {"configurable": {"thread_id": sys.argv[1]}}
)
report = snapshot.values.get("patch_verification_report") or {}
print(report.get("worktree_path", ""))
PY
)"

git -C "$PATCH_WORKTREE" diff --check HEAD
git -C "$PATCH_WORKTREE" diff -- phase14_demo.py
```

原始仓库此时仍必须是 before 状态：

```bash
git -C "$REPO" status --porcelain --untracked-files=no
grep -n "shape mismatch" "$REPO/phase14_demo.py"
```

tracked status 应为空，`grep` 应仍能找到受控异常。

#### 分支 B：只有结构验证

如果看到：

```text
verification_status="structurally_valid"
promotion_allowed=false
behavioral_checks_run=0
next 不包含 patch_promotion_review
```

说明 `verification_targets` 为空或没有可信测试。此时 Graph 应直接进入 Final Report，原始仓库相对 baseline 不产生新 diff。这是预期的 fail-closed 行为，不要手工调用 `resume-patch-promotion`。

#### 分支 C：验证失败或阻塞

如果状态是 `failed` 或 `blocked`，检查 report 中每个 check：

```text
git_apply_check
git_apply
after_sha256
worktree_diff_scope
python_syntax
targeted_tests
```

任意 required structural check 失败都不能 Promotion。

### 27.12 在 Promotion 中断期间测试清理保护

只有分支 A 才执行本步骤。Graph 正在等待 `patch_promotion_review` 时运行：

```bash
python -m app.main cleanup-patch-worktree \
  "$THREAD_ID" \
  --force
```

预期命令失败并提示：

```text
cannot clean a worktree while patch review is pending
```

再次检查 worktree 仍存在：

```bash
test -d "$PATCH_WORKTREE" && echo "protected worktree still exists"
```

### 27.13 批准 Promotion 并检查幂等 Apply 记录

批准前最后检查原仓库 diff 为空，然后执行：

```bash
git -C "$REPO" status --porcelain --untracked-files=no

python -m app.main resume-patch-promotion \
  "$THREAD_ID" \
  --decision approved \
  --feedback "隔离行为测试通过，允许应用到原始 PSTNet 仓库"
```

Patch Apply 成功后不会直接复用旧命令审批。源码变化改变了 `repo_patch_hash` 和 action hash，因此 Graph 应再次停在 `human_review`：

```bash
show_phase14_state "$THREAD_ID"
```

预期：

```text
next=["human_review"]
application_status="applied"
application_recovered=false
journal_path 非空
user_approval=null
pending_action_hash 已重新计算
```

检查原始仓库只修改了目标文件：

```bash
git -C "$REPO" status --short --untracked-files=no
git -C "$REPO" diff --check
git -C "$REPO" diff -- phase14_demo.py
```

预期 tracked status 只有：

```text
 M phase14_demo.py
```

检查 application record 和 journal：

```bash
python -m json.tool \
  "$RUN_DIR/execution/patch_application_record.json"

export JOURNAL_PATH="$(
  python - "$THREAD_ID" <<'PY'
import sys

from app.graph import build_graph


snapshot = build_graph().get_state(
    {"configurable": {"thread_id": sys.argv[1]}}
)
record = snapshot.values.get("patch_application_record") or {}
print(record.get("journal_path", ""))
PY
)"

python -m json.tool "$JOURNAL_PATH"
```

Journal 应满足：

```text
status="applied"
repository_state="after"
patch_sha256 与 pending_patch 相同
owner_run_id 与当前 run 对应
```

### 27.14 第二次命令审批并完成闭环

再次检查 pending action 仍是同一条 pytest 命令，但包含新的 `repo_patch_hash`。然后批准：

```bash
python -m app.main resume-review \
  "$THREAD_ID" \
  --decision approved \
  --feedback "源码已按已验证 patch 更新，重新运行行为测试"
```

这次预期：

```text
preflight passed
smoke_test skipped
executor succeeded
final_report generated
run_manifest generated
graph next=()
```

检查最终状态：

```bash
show_phase14_state "$THREAD_ID"

cd "$REPO"
"$CONDA_EXECUTABLE" run \
  --no-capture-output \
  -p "$REPRO_CONDA_PREFIX" \
  python -m pytest \
  -q \
  -p no:cacheprovider \
  tests/test_phase14_demo.py
cd "$PROJECT_ROOT"
```

预期：

```text
final_status="succeeded"
1 passed
```

检查最终 artifact：

```bash
test -f "$RUN_DIR/reports/final_report.md"
test -f "$RUN_DIR/reports/run_manifest.json"
test -f "$RUN_DIR/reports/artifact_index.json"

sed -n '1,260p' "$RUN_DIR/reports/final_report.md"
python -m json.tool "$RUN_DIR/reports/run_manifest.json"
```

Manifest 的 `file_repair` 区域至少应记录：

```text
verification.status=behaviorally_verified
verification.worktree_diff_sha256 非空
application.status=applied
application.recovered=false
application.journal_path 非空
```

### 27.15 流程结束后清理隔离 Worktree

此时不再处于审批中断，且 application 已成功，可以不带 `--force` 清理：

```bash
python -m app.main cleanup-patch-worktree "$THREAD_ID"
```

预期：

```text
removed patch worktree: <path>
```

检查：

```bash
test ! -e "$PATCH_WORKTREE"
git -C "$REPO" worktree list
```

这一步只删除隔离验证 worktree，不会回滚已经应用到 `$REPO` 的 patch。

### 27.16 验证原始 PSTNet 仓库的修改范围

本流程就是直接修改原始仓库，因此这里不再比较“前后完全一致”，而是确认相对 baseline 只有一个 tracked 文件发生变化：

```bash
export CHANGED_TRACKED="$(
  git -C "$REPO" diff --name-only HEAD
)"

printf 'changed tracked files:\n%s\n' "$CHANGED_TRACKED"
test "$CHANGED_TRACKED" = "phase14_demo.py"
```

继续检查 diff：

```bash
git -C "$REPO" status --short --untracked-files=no
git -C "$REPO" diff --check
git -C "$REPO" diff -- phase14_demo.py
git -C "$REPO" diff --exit-code HEAD -- tests/test_phase14_demo.py
```

预期：

```text
phase14_demo.py 是唯一 tracked 修改
tests/test_phase14_demo.py 与 baseline 完全一致
PSTNet 原有 train、datasets、models、modules 文件均无 diff
```

再检查最近一次 commit，确认 baseline 已经写入原仓库历史：

```bash
git -C "$REPO" log -1 --oneline
```

验收结束时原仓库会保留：

```text
一个名为 phase14 acceptance baseline with controlled bug 的 baseline commit
phase14_demo.py 的未提交修复 diff
可能由 pytest 产生的未跟踪 __pycache__ 文件
```

本教程不自动回滚、删除或提交这些内容。查看完报告、journal 和 diff 后，再由你决定是否保留验收文件、提交修复或人工清理。不要在检查完成前删除 `$SESSION_ROOT`。

### 27.17 专项安全分支验收

下面的分支不需要破坏刚完成的真实 thread，直接运行本章新增的专项测试。

#### 1. 无行为测试必须禁止 Promotion

```bash
cd "$PROJECT_ROOT"
python -m pytest \
  tests/test_patch_verification_semantics.py::test_no_behavior_test_is_only_structurally_valid \
  -q
```

预期 `1 passed`。该用例验证：

```text
status=structurally_valid
patch_verification_passed=False
promotion_allowed=False
```

#### 2. 有行为测试才允许 Promotion

```bash
python -m pytest \
  tests/test_patch_verification_semantics.py::test_passed_behavior_test_allows_promotion \
  -q
```

预期 `1 passed`。端到端 thread 还应已经验证 `next=["patch_promotion_review"]`。

#### 3. 篡改 Verification Report 必须失效

```bash
python -m pytest \
  tests/test_patch_authorization_boundaries.py::test_tampering_any_report_field_invalidates_hash \
  -q
```

预期 `1 passed`。该测试会修改 report 的 `summary` 但保留旧 hash，`validate_verification_hash()` 必须报告 report content changed。

再运行完整授权边界：

```bash
python -m pytest tests/test_patch_authorization_boundaries.py -q
```

确认 report、promotion、profile 或 hash 任一不一致都不能进入仓库写入。

#### 4. 模拟 Apply 各故障点并重放

```bash
python -m pytest tests/test_patch_application_recovery.py -q
```

重点检查 `after_git_apply_before_journal` 参数用例。预期重放后：

```text
repository_state=after
status=applied
recovered=True
不会第二次 git apply
```

#### 5. 手工验证同仓库跨进程互斥

在同一个 shell 中启动持锁进程：

```bash
python - "$REPO" <<'PY' &
import sys
import time

from app.tools.repository_lock_tools import acquire_repository_lock


with acquire_repository_lock(
    sys.argv[1],
    owner_run_id="manual-lock-holder",
    timeout_seconds=0,
):
    print("holder acquired lock", flush=True)
    time.sleep(8)
PY

export LOCK_HOLDER_PID="$!"
sleep 1
```

持锁期间运行第二个进程：

```bash
python - "$REPO" <<'PY'
import sys

from app.tools.repository_lock_tools import (
    RepositoryLockBusyError,
    acquire_repository_lock,
)


try:
    with acquire_repository_lock(
        sys.argv[1],
        owner_run_id="manual-lock-contender",
        timeout_seconds=0,
    ):
        raise SystemExit("ERROR: second process unexpectedly acquired lock")
except RepositoryLockBusyError as exc:
    print(f"expected: {exc}")
PY

wait "$LOCK_HOLDER_PID"
```

预期第二个进程输出：

```text
expected: repository is busy: /data/tianshaoqi24/PST-Convolution-main
```

同时运行自动化版本：

```bash
python -m pytest tests/test_repository_lock.py -q
```

#### 6. 清理保护

真实 thread 已在 27.12 验证 promotion interrupt 期间即使带 `--force` 也拒绝清理，并在 27.15 验证流程结束后可以清理。再运行自动化测试：

```bash
python -m pytest tests/test_patch_worktree_cleanup.py -q
```

### 27.18 最终验收清单

只有下面所有条件都成立，Phase 14 才算通过：

```text
[ ] 原始 PSTNet 仓库已建立明确的 baseline commit
[ ] 相对 baseline 只有 phase14_demo.py 一个 tracked 修改
[ ] 第一次命令执行前经过 human_review
[ ] 第一次 patch review 只允许隔离验证
[ ] verification=behaviorally_verified 且存在行为测试
[ ] promotion interrupt 期间不能清理 worktree
[ ] 第二次人工审批后才修改原始 PSTNet 仓库
[ ] application journal 最终为 applied/after
[ ] Patch 后 action hash 变化，并再次经过 human_review
[ ] 修复后的 pytest 命令成功
[ ] Final Report、Run Manifest 和 Artifact Index 均存在
[ ] 崩溃恢复、报告篡改、仓库锁专项测试全部通过
[ ] 流程结束后 worktree 能被显式清理
```

验收结束后可以取消本次 shell 的临时环境变量：

```bash
if [ -n "${PHASE14_ORIGINAL_HOME:-}" ]; then
  export HOME="$PHASE14_ORIGINAL_HOME"
fi

unset ALLOWED_ROOT PROJECT_ROOT PAPER REPO SESSION_ROOT THREAD_ID
unset ACCEPTANCE_ID TRUSTED_AGENT_PREFIX
unset CONDA_EXECUTABLE REPRO_CONDA_PREFIX
unset OUTPUT_DIR RUNS_DIR CHECKPOINT_DB_PATH PATCH_COORDINATION_DIR
unset EXECUTION_PROFILES_PATH ENABLE_FILE_REPAIR
unset MAX_REPAIR_ATTEMPTS MAX_FILE_REPAIR_ATTEMPTS
unset PATCH_REPO_LOCK_TIMEOUT_SECONDS
unset PHASE14_ORIGINAL_HOME
unset TMPDIR TMP TEMP
unset XDG_CACHE_HOME XDG_CONFIG_HOME XDG_DATA_HOME
unset PYTHONPYCACHEPREFIX PYTEST_ADDOPTS PIP_CACHE_DIR CONDA_PKGS_DIRS
unset TORCH_HOME CUDA_CACHE_PATH MPLCONFIGDIR NUMBA_CACHE_DIR
unset CHANGED_TRACKED
unset COMMAND_INPUT DEMO_INDEX PATCH_PATH PATCH_WORKTREE RUN_DIR
unset JOURNAL_PATH LOCK_HOLDER_PID REUSE_PHASE14_BASELINE
unset PHASE14_EXPECTED_FAILURE_RC
unset -f assert_under_allowed_root show_phase14_state
```

---

## 二十八、常见问题

### 第一次审批后被 `torch_import_probe` 阻止

先读取本轮独立的预检报告：

```bash
python -m json.tool "$OUTPUT_DIR/preflight_report.json"
```

如果 `program_in_path` 指向 `agent/bin/python`，说明启动 Graph 时误用了 local
profile。当前 thread 通常已经以 `final_status=blocked`、`next=[]` 结束，不能在
旧 action 上替换 profile 后继续审批。应保留该 run 作为安全阻断记录，更换
`ACCEPTANCE_ID`，然后用下面的参数重新启动：

```bash
--execution-profile pstnet-phase14-3d
```

如果已经指向 `$REPRO_CONDA_PREFIX/bin/python`，但仍无法导入 Torch 或 pytest，
重新执行 27.2 的复现环境检查。不要为了通过预检而向 Agent 环境安装 PyTorch，
也不要直接跳过 preflight。

### `shape_mismatch` 最终变成 `repair_kind=no_repair`

先检查：

```bash
python -m json.tool \
  "$OUTPUT_DIR/repair_planner_structured_attempts.json"
```

如果错误显示 `RepairStep.step_type` 使用了 `manual_review`、
`manual_modification` 等非法枚举，或者 `risk` 被写成说明文字，说明旧实现把
源码类错误交给 LLM 自由决定，结构校验失败后又安全降级为 `no_repair`。

当前实现做了两层修复：

1. `shape_mismatch + related_files` 由 command repair planner 确定性生成
   `manual_only`，稳定移交给 file repair planner。
2. `structured_llm.invoke()` 直接抛出的 Pydantic `ValidationError` 会携带错误
   和 JSON Schema 进入有限重试；普通 API、连接和 provider 能力错误仍不重试。

先验证：

```bash
python -m pytest \
  tests/test_smoke_repair_flow.py \
  tests/test_structured_output_tools.py \
  tests/test_repair_proposal_semantics.py \
  -q
```

旧 thread 已经 `next=[]` 时不能原地恢复。保留失败 run，增加
`ACCEPTANCE_ID` 后从 27.1 开始新一轮验收。

### `repair_kind=manual_only` 但 `file_repair_kind` 仍是 `manual_only`

检查 `show_phase14_state` 中的 `debug_related_files`。如果只有
`tests/test_phase14_demo.py`，而 traceback 明明还包含
`phase14_demo.py:4`，说明旧实现完全依赖模型填写相关文件，真正实现文件没有
进入 file repair 的安全白名单。模型只看到测试上下文时拒绝生成 patch 是正确的
安全行为。

当前实现会：

1. 从 Python 和 pytest traceback 中提取真实存在的仓库内 `.py` 文件。
2. 把确定性路径与模型 `related_files` 合并并去重。
3. 禁止 file repair proposal 修改 `tests/` 下的文件。
4. 从当前 pytest action 自动建立已有测试文件的行为验证目标。

运行专项测试：

```bash
python -m pytest \
  tests/test_smoke_repair_flow.py \
  tests/test_file_repair_planner_node.py \
  -q
```

通过后增加 `ACCEPTANCE_ID` 重新验收。不要手工把
`file_repair_proposal.kind` 改成 `patch`，因为那会绕过源码上下文白名单和模型
语义判断。

### `INVALID_CONCURRENT_GRAPH_UPDATE`

执行：

```bash
rg -n 'log_debug.*final_report|route_after_log_debug' app/graph.py
```

确认关键 route 只定义一次，并且不存在无条件 `log_debug -> final_report`。

### 原来的 `passed` 变成 `structurally_valid`

这是预期变化。语法和 apply 成功不等于行为正确，需要 targeted test 才能 promotion。

### `verification report content changed`

重新运行 verifier 并重新审批，不要手工更新 hash。

### `repository is busy`

另一个进程持有仓库锁。正常等待或检查持有者，不要删除 lock 文件绕过内核锁。

### Journal 是 `applying`

先只读检查：

```bash
git -C /data/tianshaoqi24/example-repo status --short
git -C /data/tianshaoqi24/example-repo diff --name-only HEAD
```

Exact after 会在重放时恢复；额外 tracked 修改会进入 `manual_intervention`。

### Worktree diff scope mismatch

检查：

```bash
git -C /data/tianshaoqi24/example-run/patch/worktree diff --name-only HEAD
git -C /data/tianshaoqi24/example-run/patch/worktree diff --cached --name-only
```

Tracked 修改集合必须与 bundle 文件集合完全相同。

---

## 二十九、Agent 知识点

1. **Graph determinism**：同一节点一次执行只能选择一个条件分支。
2. **Semantic status**：结构成功、行为验证和允许副作用必须分开表达。
3. **Trust-boundary revalidation**：promotion/apply 都重新读取事实和计算 hash。
4. **TOCTOU**：review 到 apply 之间的文件、profile 和报告都可能变化。
5. **Write-ahead log**：副作用前先记录意图，崩溃后结合现实状态恢复。
6. **Idempotency**：识别 before、after、conflict，而不是简单捕获异常。
7. **Concurrency control**：Checkpoint 隔离 state，repository lock 隔离共享资源。
8. **Fail closed**：无法证明安全时停止并要求人工介入。

---

## 三十、完成标准

- 两个关键 route 函数各只定义一次。
- `log_debug` 不再有无条件 final edge。
- 条件路由有明确 `Literal` 和 `path_map`。
- command、file、final 三条路径均有编译图测试。
- 没有行为测试时只能是 `structurally_valid`。
- 至少一个行为测试通过后才是 `behaviorally_verified`。
- 篡改 verification report 后旧审批失效。
- promotion/apply 都重新计算 verification hash。
- apply 独立检查 status、promotion、patch id/hash 和 profile。
- 复用 worktree 时 tracked diff 只能包含 bundle 文件。
- 同一 repo 同时只能有一个 patch apply。
- journal 在 `git apply` 前持久化。
- apply 后、checkpoint 前崩溃可用 `recovered=True` 恢复。
- 额外用户 tracked 修改会进入 `manual_intervention`。
- 审批中的 worktree 不能清理。
- 验收前 `ENABLE_FILE_REPAIR=false`。
- 全量测试通过且数量不少于修改前基线。

---

## 三十一、下一阶段

完成后按照最新路线进入：

```text
Phase 15：统一异常模型与 Run 原生 Artifact
```

它将解决节点异常直接中断、共享 `outputs/` 污染、失败缺少 manifest，以及错误分类和 artifact 不统一的问题。

Phase 14 让“修改仓库”变得安全；Phase 15 让“每次成功或失败”都有隔离、完整、可诊断的运行记录。

---

## 最后总结

```text
图只走一条路
状态不夸大结论
审批绑定当前事实
共享仓库修改互斥
副作用发生前有 journal
崩溃重放不重复写
无法证明安全时停止
```

完成这些收口后，Phase 13 的 file repair 才从演示能力升级为可以小范围、受控启用的工程能力。
