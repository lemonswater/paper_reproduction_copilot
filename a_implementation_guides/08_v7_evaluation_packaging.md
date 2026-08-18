# 08. V7 评测与项目包装

## 目标

把项目从“能跑”整理成“能面试展示”。这一阶段要补齐：

```text
固定 case
期望结果
评测脚本
失败分析
README
架构图
演示脚本
简历描述
```

## 本阶段要新增的文件

```text
app/evaluation/cases/case_001_paper.json
app/evaluation/cases/case_002_repo.json
app/evaluation/cases/case_003_mapping.json
app/evaluation/run_eval.py
docs/architecture.md
docs/demo_script.md
README.md
```

## case 文件格式

```json
{
  "case_id": "case_003_mapping",
  "type": "paper_code_mapping",
  "input": {
    "paper_path": "data/cases/example/paper.pdf",
    "repo_path": "data/cases/example/repo"
  },
  "expected": {
    "must_find_files": [
      "models/model.py",
      "train.py"
    ],
    "must_include_modules": [
      "Temporal Attention",
      "Graph Encoder"
    ],
    "must_not_claim": [
      "batch size is 64"
    ]
  }
}
```

## app/evaluation/run_eval.py

先做半自动评测，不要一开始追求复杂打分器。核心是跑固定 case 并检查关键产物。

```python
import json
from pathlib import Path

from app.graph import build_graph


CASE_DIR = Path("app/evaluation/cases")
OUTPUT_DIR = Path("outputs")


# 读取评测目录下的全部 case 定义文件。
def load_cases() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CASE_DIR.glob("*.json"))
    ]


# 对 paper-code mapping case 进行基础规则打分。
def score_mapping_case(case: dict) -> dict:
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


# 运行单个评测 case，并汇总输出文件和得分结果。
def run_case(case: dict) -> dict:
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
        },
        config=config,
    )

    if case["type"] == "paper_code_mapping":
        score = score_mapping_case(case)
    else:
        score = {"score": None, "reason": "manual review required"}

    return {
        "case_id": case_id,
        "type": case["type"],
        "output_files": result.get("output_files", []),
        "score": score,
    }


# 运行全部评测 case，并写出最终评测报告。
def main():
    reports = [run_case(case) for case in load_cases()]
    report_path = OUTPUT_DIR / "eval_report.json"
    report_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

## eval_report.md 模板

```markdown
# Eval Report

## Summary

| Metric | Result |
|---|---|
| Case Count | 5 |
| Mapping File Recall | 0.8 |
| Forbidden Claims | 0 |
| Resume Success | 1/1 |
| Approval Compliance | 1/1 |

## Case Details

### case_003_mapping

- Input: paper + official repo
- Expected files: `models/model.py`, `train.py`
- Actual result: found `models/model.py`, missed `train.py`
- Failure reason: train entry was named `main.py`; heuristic needs README command parsing
- Next fix: add README command extractor
```

## docs/architecture.md 建议内容

~~~markdown
# Architecture

```text
Paper Reader
   ↓
Method Extractor
   ↓
Repo Scanner
   ↓
Code Search
   ↓
Mapping
   ↓
Experiment Planner
   ↓
Debug / Human Review / Report
```

## State

- paper_summary
- method_modules
- repo_map
- paper_code_mapping
- experiment_plan
- debug_report
- pending_action

## Tool Boundary

- read-only tools
- output-writing tools
- proposal-only risky tools
~~~

注意：这里用 `~~~markdown` 包住示例，是为了避免内层代码块提前结束。

## docs/demo_script.md 建议内容

~~~markdown
# Demo Script

## 1. 背景

论文复现的信息分散在论文、README、配置、训练脚本和日志中。

## 2. 运行

```bash
python -m app.main run-graph data/case_001/paper.pdf data/case_001/repo --thread-id demo-001
```

## 3. 展示产物

- outputs/paper_summary.json
- outputs/repo_map.json
- outputs/paper_code_mapping.md
- outputs/experiment_plan.md

## 4. 重点讲解

- LangGraph StateGraph
- evidence-based mapping
- checkpoint resume
- human-in-the-loop
- evaluation cases
~~~

## README 必须包含

```text
1. 项目背景
2. 核心能力
3. 架构图
4. 快速开始
5. 一个完整 demo
6. 输出样例
7. 评测方式
8. 安全边界
9. 已知限制
10. 后续计划
```

## 简历描述

```text
基于 LangGraph 设计并实现论文复现辅助 Agent，支持论文结构化解析、代码仓库扫描、论文方法到代码实现的证据化映射、复现实验计划生成、训练日志诊断和 Markdown 报告输出。系统采用 StateGraph 编排多阶段工作流，通过结构化 State 管理论文、代码、日志和实验计划等上下文，并接入 checkpoint 支持任务中断恢复；针对文件修改和命令执行设计 human-in-the-loop 审批流程，提升 Agent 执行安全性。项目构建多组真实 case 进行评测，记录工具调用轨迹、映射证据质量和失败模式，用于持续优化可靠性。
```

## 本阶段验收

你应该能完成一次 3 分钟演示：

```text
1. 展示输入论文和 repo。
2. 运行 graph。
3. 展示 paper_code_mapping.md。
4. 展示 experiment_plan.md。
5. 解释 checkpoint 和 human review。
6. 展示 eval_report。
```

## 常见坑

- 不要只展示“跑通了”，要展示一个失败 case 和改进方向。
- README 里一定要写安全边界，否则 shell 工具会被面试官追问。
- 评测不必复杂，但必须有固定 case 和期望结果。
