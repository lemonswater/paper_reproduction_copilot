# 14. 端到端闭环第四阶段：统一 `final_report`，升级 `eval`

## 这一阶段的目标

第三阶段你已经把失败路径闭环推进到了：

```text
experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
  -> executor
      -> success -> END
      -> failed -> log_debug -> END
```

这已经说明：

- Agent 能分析论文和代码
- 能给出计划
- 能构造待执行动作
- 能走审批链
- 能真正执行
- 失败后还能自动做日志诊断

但现在还缺最后一段“收口”能力：

1. **跑完以后，没有一个统一的最终报告**  
   现在产物分散在：
   - `paper_summary.json`
   - `repo_map.json`
   - `paper_code_mapping.json`
   - `experiment_plan.json`
   - `execution.log`
   - `debug_report.json`

2. **评测脚本还停留在比较早期的形态**  
   当前 [app/evaluation/run_eval.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/evaluation/run_eval.py:1) 主要还是：
   - 读取固定 case
   - 跑 graph
   - 对 mapping 做一个基础规则分数

   但还没有真正利用：
   - `final_status`
   - `final_report`
   - `debug_report`
   - 审批链 / 执行链路的结果

所以第四阶段的目标就是：

```text
graph 跑完
-> 输出统一 final_report.md
-> eval 脚本能汇总更多维度
-> 同时生成 eval_report.json 和 eval_report.md
```

这一阶段做完后，你的项目就不再只是“很多阶段性产物的集合”，而是开始具备：

- 最终对外展示报告
- 统一评测结果
- 更完整的 demo 和复盘能力

---

## 这一阶段要解决的核心问题

可以把这一步理解成补两条“最后一公里”：

### 1. `final_report`：让整条链有统一出口

你希望最终用户看到的不是一堆散落文件，而是一份可以直接阅读的报告：

```text
这篇论文要复现什么
仓库里关键代码在哪
模型计划做什么
审批结果是什么
执行成功还是失败
如果失败，原因是什么
```

### 2. `eval`：让系统能被批量验证和比较

你希望的不只是：

```text
好像跑通了一次
```

而是：

```text
这组 case 跑完后：
- 成功多少个
- 失败多少个
- 哪些触发了 debug
- 哪些生成了 final_report
- mapping 得分是多少
```

---

## 这一阶段建议新增 / 修改的文件

```text
app/nodes/final_report_node.py
app/graph.py
app/evaluation/run_eval.py
tests/test_final_report_node.py
tests/test_eval_reporting.py
```

如果你后面想继续往“展示材料”走，还可以补：

```text
README.md
docs/architecture.md
docs/demo_script.md
```

但这些更偏展示收尾，不是这份 phase 文档的核心。

---

## 一、先明确 Phase 4 的目标图

建议你把这一阶段的 graph 理解成下面这版：

```text
START
  -> paper_reader
  -> method_extractor
  -> repo_scan
  -> code_search
  -> mapping
  -> experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
  -> executor
      -> failed + log_path -> log_debug -> final_report -> END
      -> 其他状态 -> final_report -> END
```

这个设计里最关键的变化是：

- 成功路径不再直接 `END`
- 失败路径在 `log_debug` 后也不再直接 `END`
- 两条路径最后都收敛到：

```text
final_report
```

这样整个项目终于有了一个统一出口。

---

## 二、新增 `app/nodes/final_report_node.py`

### 这个节点解决什么问题

当前状态里其实已经有足够多的信息，可以生成一份不错的最终报告：

- `paper_summary`
- `repo_map`
- `paper_code_mapping`
- `experiment_plan`
- `pending_action`
- `user_approval`
- `execution_result`
- `final_status`
- `debug_report`

所以这一阶段不一定非要再调一次 LLM。

我更建议你先用**纯规则 + markdown 渲染**的方式做 `final_report_node`，原因是：

1. 更稳定  
2. 更容易测试  
3. 不会给“最终收口”又引入新的 LLM 不确定性  

等后面你想把报告写得更像“自然语言总结”，再额外加一个 LLM 报告增强版也不迟。

### 这个节点应该输出什么

建议它输出两样东西：

1. `outputs/final_report.md`
2. state 里的：

```python
{
    "final_report": "...markdown content...",
    "output_files": [..., "outputs/final_report.md"]
}
```

### 建议新文件完整代码

```python
from app.config import settings


def final_report_node(state: dict) -> dict:
    """
    汇总整条闭环执行后的关键信息，输出最终 markdown 报告。

    这一阶段先不再调用 LLM，而是使用确定性渲染：
    1. 更稳定；
    2. 更容易测试；
    3. 更适合“最终收口”场景。
    """

    report_text = _render_final_report(state)

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = settings.output_dir / "final_report.md"
    report_path.write_text(report_text, encoding="utf-8")

    return {
        "final_report": report_text,
        "output_files": [
            *state.get("output_files", []),
            str(report_path),
        ],
    }


def _render_section(title: str, items: list[str]) -> list[str]:
    """
    把一个 section 渲染成 markdown 片段。
    如果内容为空，就写一个明确的占位说明，避免报告结构忽隐忽现。
    """
    lines = [f"## {title}", ""]
    if not items:
        lines.append("- None")
        lines.append("")
        return lines

    for item in items:
        lines.append(f"- {item}")
    lines.append("")
    return lines


def _render_final_report(state: dict) -> str:
    """
    将 state 中已经积累的结构化结果组织成最终 markdown 报告。
    """

    lines: list[str] = ["# Final Report", ""]

    # 1. 基本信息
    lines += _render_section(
        "Run Summary",
        [
            f"Paper Path: `{state.get('paper_path', '')}`" if state.get("paper_path") else "Paper Path: N/A",
            f"Repo Path: `{state.get('repo_path', '')}`" if state.get("repo_path") else "Repo Path: N/A",
            f"Experiment Goal: {state.get('experiment_goal', 'N/A')}",
            f"Final Status: `{state.get('final_status', 'unknown')}`",
            f"User Approval: `{state.get('user_approval', 'not_recorded')}`",
        ],
    )

    # 2. 论文摘要信息
    paper_summary = state.get("paper_summary", {})
    lines += _render_section(
        "Paper Summary",
        [
            f"Title: {paper_summary.get('title', 'N/A')}",
            f"Research Problem: {paper_summary.get('research_problem', 'N/A')}",
            f"Core Idea: {paper_summary.get('core_idea', 'N/A')}",
        ],
    )

    # 3. RepoMap 摘要
    repo_map = state.get("repo_map", {})
    important_files = repo_map.get("important_files", [])
    lines += _render_section(
        "Repository Highlights",
        [f"Important File: `{path}`" for path in important_files[:10]],
    )

    # 4. 映射结果摘要
    mappings = state.get("paper_code_mapping", [])
    mapping_items: list[str] = []
    for mapping in mappings:
        module_name = mapping.get("module_name", "Unknown Module")
        candidates = mapping.get("candidates", [])
        if not candidates:
            mapping_items.append(f"{module_name}: no confident code candidate found")
            continue

        top_candidate = candidates[0]
        mapping_items.append(
            f"{module_name}: top candidate is `{top_candidate.get('file_path', 'N/A')}` "
            f"(confidence={top_candidate.get('confidence', 'unknown')})"
        )
    lines += _render_section("Paper-Code Mapping Summary", mapping_items)

    # 5. 实验计划摘要
    plan = state.get("experiment_plan", {})
    run_commands = state.get("run_commands", [])
    lines += _render_section(
        "Experiment Plan Summary",
        [
            f"Goal: {plan.get('goal', 'N/A')}",
            f"Environment Steps: {len(plan.get('environment_steps', []))}",
            f"Data Steps: {len(plan.get('data_steps', []))}",
            f"Train Steps: {len(plan.get('train_steps', []))}",
            f"Eval Steps: {len(plan.get('eval_steps', []))}",
            f"Run Commands: {len(run_commands)}",
        ],
    )

    # 6. 审批与待执行动作
    pending_action = state.get("pending_action")
    review_items: list[str] = []
    if pending_action:
        review_items.append(f"Pending Action Type: `{pending_action.get('type', 'unknown')}`")
        review_items.append(f"Pending Command: `{pending_action.get('command', '')}`")
        review_items.append(f"Action Source: `{pending_action.get('source', 'unknown')}`")
    human_feedback = state.get("human_feedback")
    if human_feedback:
        review_items.append(f"Human Feedback: {human_feedback}")
    lines += _render_section("Approval Summary", review_items)

    # 7. 执行结果摘要
    execution_result = state.get("execution_result", {})
    execution_items: list[str] = []
    if execution_result:
        execution_items.extend(
            [
                f"Execution OK: `{execution_result.get('ok')}`",
                f"Return Code: `{execution_result.get('returncode')}`",
                f"Execution Log Path: `{state.get('execution_log_path', '')}`"
                if state.get("execution_log_path")
                else "Execution Log Path: N/A",
            ]
        )
    lines += _render_section("Execution Summary", execution_items)

    # 8. Debug 结果摘要
    debug_report = state.get("debug_report", {})
    debug_items: list[str] = []
    if debug_report:
        debug_items.append(f"Error Type: `{debug_report.get('error_type', 'unknown')}`")
        for cause in debug_report.get("most_likely_causes", [])[:5]:
            debug_items.append(f"Possible Cause: {cause}")
    lines += _render_section("Debug Summary", debug_items)

    # 9. 输出文件列表
    lines += _render_section(
        "Output Files",
        [f"`{path}`" for path in state.get("output_files", [])],
    )

    return "\n".join(lines)
```

---

## 三、修改 `app/graph.py`

### 这一步要解决什么问题

现在你的图大致是：

```text
executor
  -> failed -> log_debug -> END
  -> success -> END
```

但第四阶段希望两条路径都统一收口到：

```text
final_report
```

所以 graph 要新增：

- `final_report_node`
- `route_after_executor()` 的非失败分支要去 `final_report`
- `log_debug` 后不再直接 `END`，而是去 `final_report`

### 建议修改后的完整代码

```python
from langgraph.graph import END, START, StateGraph

from app.nodes.action_builder_node import action_builder_node
from app.nodes.executor_node import executor_node
from app.nodes.final_report_node import final_report_node
from app.nodes.code_search_node import code_search_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.human_review_node import human_review_node
from app.nodes.log_debug_node import log_debug_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.risk_check_node import risk_check_node
from app.memory.checkpoint import build_checkpointer
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
    """
    Phase 4 的改法：
    - 执行失败且有 log_path -> 进入 log_debug
    - 其他所有状态 -> 进入 final_report

    这样成功、拒绝、revise、unsupported_action 等情况
    都有统一的报告出口。
    """
    if state.get("final_status") == "failed" and state.get("log_path"):
        return "log_debug"
    return "final_report"


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

    # 审批与执行链
    builder.add_node("risk_check", risk_check_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("executor", executor_node)

    # 失败分析与最终报告
    builder.add_node("log_debug", log_debug_node)
    builder.add_node("final_report", final_report_node)

    # 主链
    builder.add_edge(START, "paper_reader")
    builder.add_edge("paper_reader", "method_extractor")
    builder.add_edge("method_extractor", "repo_scan")
    builder.add_edge("repo_scan", "code_search")
    builder.add_edge("code_search", "mapping")
    builder.add_edge("mapping", "experiment_plan")
    builder.add_edge("experiment_plan", "action_builder")

    builder.add_conditional_edges("action_builder", route_after_action_builder)
    builder.add_conditional_edges("risk_check", route_after_risk_check)
    builder.add_edge("human_review", "executor")
    builder.add_conditional_edges("executor", route_after_executor)

    # Phase 4 的关键变化：
    # debug 之后不再直接结束，而是统一进入 final_report。
    builder.add_edge("log_debug", "final_report")

    # final_report 是整个闭环的统一出口。
    builder.add_edge("final_report", END)

    return builder.compile(checkpointer=build_checkpointer())
```

---

## 四、修改 `app/evaluation/run_eval.py`

### 这一步要解决什么问题

当前的 `run_eval.py` 还比较早期，它的问题主要有这几类：

1. 输出报告只有 `eval_report.json`
2. 对 graph 的最终状态利用不够
3. 只对 mapping 做了最基础规则分数
4. 没有反映：
   - `final_status`
   - 是否生成了 `debug_report`
   - 是否生成了 `final_report`

第四阶段我们不追求一步到位做复杂评测器，但至少要做到：

- 每个 case 的最终状态能记录
- 是否产出 `final_report.md` 能记录
- 是否产出 `debug_report.md` 能记录
- 最后除了 JSON 还能生成一个更好读的 `eval_report.md`

### 建议修改后的完整代码

```python
import json
from pathlib import Path

from app.graph import build_graph


CASE_DIR = Path("app/evaluation/cases")
OUTPUT_DIR = Path("outputs")


def load_cases() -> list[dict]:
    """
    读取评测目录下全部 case 定义文件。
    """
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CASE_DIR.glob("*.json"))
    ]


def score_mapping_case(case: dict) -> dict:
    """
    对 paper_code_mapping 类型 case 做基础规则打分。
    当前仍然保持轻量策略：
    - must_find_files 命中率
    - must_not_claim 惩罚
    """
    mapping_path = OUTPUT_DIR / "paper_code_mapping.json"
    if not mapping_path.exists():
        return {"score": 0, "reason": "missing paper_code_mapping.json"}

    mapping_text = mapping_path.read_text(encoding="utf-8")
    expected = case.get("expected", {})

    must_find = expected.get("must_find_files", [])
    found_count = sum(1 for item in must_find if item in mapping_text)

    forbidden = expected.get("must_not_claim", [])
    forbidden_count = sum(1 for item in forbidden if item in mapping_text)

    file_recall = found_count / max(len(must_find), 1)
    hallucination_penalty = forbidden_count

    return {
        "file_recall": file_recall,
        "forbidden_claims": forbidden_count,
        "score": max(file_recall - hallucination_penalty, 0),
    }


def run_case(case: dict) -> dict:
    """
    运行单个 case，并返回用于最终汇总的结构化结果。
    """
    graph = build_graph()
    case_id = case["case_id"]
    config = {"configurable": {"thread_id": case_id}}
    inputs = case["input"]

    result = graph.invoke(
        {
            "paper_path": inputs.get("paper_path"),
            "repo_path": inputs.get("repo_path"),
            "log_path": inputs.get("log_path"),
            "experiment_goal": inputs.get("experiment_goal", "复现论文 main result"),
            "output_files": [],
            "step_count": 0,
            "max_steps": 20,
        },
        config=config,
    )

    if case["type"] == "paper_code_mapping":
        score = score_mapping_case(case)
    else:
        score = {"score": None, "reason": "manual review required"}

    output_files = result.get("output_files", [])
    has_final_report = any(path.endswith("final_report.md") for path in output_files)
    has_debug_report = any(path.endswith("debug_report.md") for path in output_files)

    return {
        "case_id": case_id,
        "type": case["type"],
        "final_status": result.get("final_status"),
        "output_files": output_files,
        "has_final_report": has_final_report,
        "has_debug_report": has_debug_report,
        "score": score,
    }


def render_eval_report_md(reports: list[dict]) -> str:
    """
    将结构化评测结果渲染成人可读 markdown 报告。
    """
    lines = ["# Eval Report", ""]

    total = len(reports)
    success_count = sum(1 for item in reports if item.get("final_status") == "succeeded")
    fail_count = sum(1 for item in reports if item.get("final_status") == "failed")
    final_report_count = sum(1 for item in reports if item.get("has_final_report"))
    debug_report_count = sum(1 for item in reports if item.get("has_debug_report"))

    lines += [
        "## Summary",
        "",
        f"- Case Count: {total}",
        f"- Succeeded: {success_count}",
        f"- Failed: {fail_count}",
        f"- Final Report Generated: {final_report_count}/{total}",
        f"- Debug Report Generated: {debug_report_count}/{total}",
        "",
    ]

    lines += ["## Case Details", ""]

    for report in reports:
        lines.append(f"### {report['case_id']}")
        lines.append("")
        lines.append(f"- Type: `{report['type']}`")
        lines.append(f"- Final Status: `{report.get('final_status', 'unknown')}`")
        lines.append(f"- Has Final Report: `{report.get('has_final_report')}`")
        lines.append(f"- Has Debug Report: `{report.get('has_debug_report')}`")

        score = report.get("score", {})
        if score:
            lines.append(f"- Score: `{score.get('score')}`")
            if "file_recall" in score:
                lines.append(f"- Mapping File Recall: `{score.get('file_recall')}`")
            if "forbidden_claims" in score:
                lines.append(f"- Forbidden Claims: `{score.get('forbidden_claims')}`")
            if score.get("reason"):
                lines.append(f"- Note: {score['reason']}")

        output_files = report.get("output_files", [])
        if output_files:
            lines.append("- Output Files:")
            for path in output_files:
                lines.append(f"  - `{path}`")

        lines.append("")

    return "\n".join(lines)


def main():
    reports = [run_case(case) for case in load_cases()]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    report_json_path = OUTPUT_DIR / "eval_report.json"
    report_md_path = OUTPUT_DIR / "eval_report.md"

    report_json_path.write_text(
        json.dumps(reports, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_path.write_text(
        render_eval_report_md(reports),
        encoding="utf-8",
    )

    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

---

## 五、新增测试：`tests/test_final_report_node.py`

### 这一步的重点

这份测试的目标不是测 markdown 每个字符都一模一样，而是测：

- `final_report_node()` 能生成报告
- 报告文件能落盘
- 报告里确实包含关键字段

### 新文件完整代码

```python
from unittest.mock import patch

from app.nodes.final_report_node import final_report_node


def test_final_report_node_writes_report_and_returns_output_file(tmp_path) -> None:
    state = {
        "paper_path": "pdf/demo.pdf",
        "repo_path": "/tmp/demo-repo",
        "experiment_goal": "复现论文 main result",
        "final_status": "failed",
        "user_approval": "approved",
        "paper_summary": {
            "title": "Demo Paper",
            "research_problem": "Demo problem",
            "core_idea": "Demo idea",
        },
        "repo_map": {
            "important_files": ["train.py", "models/model.py"],
        },
        "paper_code_mapping": [
            {
                "module_name": "Transformer",
                "candidates": [
                    {
                        "file_path": "models/model.py",
                        "confidence": "high",
                    }
                ],
            }
        ],
        "experiment_plan": {
            "goal": "复现论文 main result",
            "environment_steps": [],
            "data_steps": [],
            "train_steps": [],
            "eval_steps": [],
        },
        "run_commands": [
            {"command": "python train.py"}
        ],
        "pending_action": {
            "type": "run_command",
            "command": "python train.py",
            "source": "experiment_plan",
        },
        "execution_result": {
            "ok": False,
            "returncode": 1,
        },
        "execution_log_path": "outputs/execution.log",
        "debug_report": {
            "error_type": "cuda_oom",
            "most_likely_causes": ["batch size too large"],
        },
        "output_files": [],
    }

    with patch("app.nodes.final_report_node.settings.output_dir", tmp_path):
        result = final_report_node(state)

    assert "final_report" in result
    assert "Final Status" in result["final_report"]
    assert "Demo Paper" in result["final_report"]
    assert any(path.endswith("final_report.md") for path in result["output_files"])
```

---

## 六、新增测试：`tests/test_eval_reporting.py`

### 这一步的重点

评测脚本里最容易测试的是“报告渲染逻辑”，而不是立刻去 mock 整个 graph。

所以建议先给：

```python
render_eval_report_md()
```

补一个小测试。

### 新文件完整代码

```python
from app.evaluation.run_eval import render_eval_report_md


def test_render_eval_report_md_contains_summary_and_case_details() -> None:
    reports = [
        {
            "case_id": "case_success",
            "type": "paper_code_mapping",
            "final_status": "succeeded",
            "has_final_report": True,
            "has_debug_report": False,
            "output_files": ["outputs/final_report.md"],
            "score": {
                "score": 1.0,
                "file_recall": 1.0,
                "forbidden_claims": 0,
            },
        },
        {
            "case_id": "case_fail",
            "type": "paper_code_mapping",
            "final_status": "failed",
            "has_final_report": True,
            "has_debug_report": True,
            "output_files": ["outputs/final_report.md", "outputs/debug_report.md"],
            "score": {
                "score": 0.5,
                "file_recall": 0.5,
                "forbidden_claims": 0,
            },
        },
    ]

    text = render_eval_report_md(reports)

    assert "# Eval Report" in text
    assert "## Summary" in text
    assert "Succeeded: 1" in text
    assert "Failed: 1" in text
    assert "### case_success" in text
    assert "### case_fail" in text
    assert "Has Debug Report: `True`" in text
```

---

## 七、这一阶段怎么运行验证

### 1. 先跑新增测试

```bash
python -m pytest tests/test_final_report_node.py
python -m pytest tests/test_eval_reporting.py
```

### 2. 再一起回归前面阶段

```bash
python -m pytest \
  tests/test_action_builder_node.py \
  tests/test_review_flow.py \
  tests/test_executor_node.py \
  tests/test_fail_to_debug_flow.py \
  tests/test_final_report_node.py \
  tests/test_eval_reporting.py
```

### 3. 手工跑评测

如果你想验证 `run_eval.py` 的最终效果，可以执行：

```bash
python -m app.evaluation.run_eval
```

运行后建议重点检查：

- `outputs/eval_report.json`
- `outputs/eval_report.md`
- 某个 case 跑完后是否产生 `final_report.md`

### 4. 手工跑 graph

如果你想看 final report 是否真的成为统一出口，可以跑：

```bash
python -m app.main run-graph "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" /data/tianshaoqi24/P4Transformer/ --thread-id final-001
```

然后看：

```text
outputs/final_report.md
```

---

## 八、这一阶段完成后的预期效果

这一阶段做完后，你的整条闭环会从：

```text
executor
  -> failed -> log_debug -> END
  -> success -> END
```

升级成：

```text
executor
  -> failed -> log_debug -> final_report -> END
  -> success -> final_report -> END
  -> rejected / revise / unsupported -> final_report -> END
```

这代表：

- 不同路径终于有了统一出口
- 你不再需要手动拼接散落产物
- `eval` 也开始真正能“看懂闭环结果”

这一步做完后，这个项目在工程完整性上会明显更像一个作品，而不只是“阶段性练习”。

---

## 九、这一阶段最常见的坑

### 1. `final_report_node` 里又调用 LLM，导致最终收口不稳定

这一步其实更适合先用规则渲染，而不是再引入一层不确定性。

建议先做：

- 纯 markdown 汇总

后面如果你想让报告更像“自然语言总结”，再额外做一个增强版。

### 2. graph 里 success 路径没有进 `final_report`

如果你只处理了 fail -> final_report，成功路径仍然直接 `END`，就失去了“统一出口”的意义。

### 3. `run_eval.py` 只写 JSON，不写 Markdown

JSON 对程序很友好，但对人展示不够好。

第四阶段的一个重点，就是把结果做成：

- `eval_report.json`
- `eval_report.md`

### 4. `final_report` 只复述状态，不体现执行 / debug 结果

最终报告至少要覆盖：

- 分析
- 计划
- 审批
- 执行
- debug

否则它就只是“换皮的状态 dump”。

### 5. 把 README / docs 的工作和 final_report/eval 混在一起

这两者相关，但不是同一件事。

- `final_report` 是单次运行收口
- `eval_report` 是批量 case 结果
- `README/docs` 是项目展示材料

第四阶段先把前两者补稳就够了。

---

## 十、这一步做完后，项目就进入什么状态了

如果你完成了 phase 1 到 phase 4，项目大致就会具备：

```text
输入论文和 repo
-> 结构化分析
-> 代码映射
-> 实验计划
-> 动作构造
-> 风险判断
-> 人工审批
-> 执行
-> 失败自动 debug
-> 最终报告
-> 批量评测
```

这已经非常接近一个完整的 Agent MVP 了。

你后面还可以继续做：

- 持久化 checkpoint
- 真正可恢复的 interrupt / resume
- 更强的 eval case
- README / docs / demo 打包

但从“闭环能力”角度看，phase 4 已经把最后一个最关键的收口点补上了。
