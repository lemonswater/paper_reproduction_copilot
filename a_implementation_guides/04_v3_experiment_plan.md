# 04. V3 复现实验计划生成

## 目标

基于论文摘要、repo map 和 paper-code mapping，生成可人工执行的复现实验计划：

```text
outputs/experiment_plan.md
outputs/experiment_plan.json
```

注意：这个阶段仍然不自动执行训练命令，只生成计划和命令来源。

## 本阶段要新增的文件

```text
app/schemas.py             # 增加 ExperimentStep / ExperimentPlan
app/prompts/plan_prompt.py
app/nodes/experiment_plan_node.py
```

## app/schemas.py 增加

```python
from typing import Literal


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
```

## app/prompts/plan_prompt.py

```python
EXPERIMENT_PLAN_PROMPT = """
你是一个论文复现实验规划助手。

请根据论文摘要、代码仓库地图和论文-代码映射，生成可人工执行的复现实验计划。

要求：
1. 不要自动执行任何命令。
2. 每个命令必须标记来源：readme、script、config、inferred 或 need_confirm。
3. 如果 README 没有明确说明，不要假装确定。
4. 数据集路径、batch size、GPU 数量、checkpoint 路径等不确定信息要写入 unresolved_questions。
5. 对安装依赖、修改配置、运行训练等动作标记风险。

论文摘要：
{paper_summary}

仓库地图：
{repo_map}

论文-代码映射：
{paper_code_mapping}

用户实验目标：
{experiment_goal}
"""
```

## app/nodes/experiment_plan_node.py

```python
import json

from app.config import settings
from app.model import get_chat_model
from app.prompts.plan_prompt import EXPERIMENT_PLAN_PROMPT
from app.schemas import ExperimentPlan


# 基于论文摘要、repo map 和 mapping 生成结构化复现实验计划。
def experiment_plan_node(state: dict) -> dict:
    paper_summary = state.get("paper_summary")
    repo_map = state.get("repo_map")
    paper_code_mapping = state.get("paper_code_mapping")
    if not paper_summary or not repo_map or not paper_code_mapping:
        return {"error": "experiment plan requires paper_summary, repo_map and mapping"}

    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(ExperimentPlan)

    plan: ExperimentPlan = structured_llm.invoke(
        EXPERIMENT_PLAN_PROMPT.format(
            paper_summary=json.dumps(paper_summary, ensure_ascii=False, indent=2),
            repo_map=json.dumps(repo_map, ensure_ascii=False, indent=2),
            paper_code_mapping=json.dumps(paper_code_mapping, ensure_ascii=False, indent=2),
            experiment_goal=state.get("experiment_goal") or "复现论文 main result",
        )
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "experiment_plan.json"
    md_path = settings.output_dir / "experiment_plan.md"

    json_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_render_plan_markdown(plan), encoding="utf-8")

    return {
        "experiment_plan": plan.model_dump(),
        "run_commands": [cmd.model_dump() for cmd in plan.run_commands],
        "output_files": [
            *state.get("output_files", []),
            str(json_path),
            str(md_path),
        ],
    }


# 将某一类实验步骤渲染成 markdown 片段。
def _render_steps(title: str, steps: list) -> list[str]:
    lines = [f"## {title}", ""]
    if not steps:
        lines.append("- 暂无明确步骤")
        lines.append("")
        return lines

    for step in steps:
        lines.append(f"### {step.order}. {step.name}")
        lines.append("")
        lines.append(f"- Action: {step.action}")
        lines.append(f"- Source: {step.source}")
        if step.risk:
            lines.append(f"- Risk: {step.risk}")
        lines.append("")
    return lines


# 将完整实验计划对象渲染成 markdown 报告。
def _render_plan_markdown(plan: ExperimentPlan) -> str:
    lines = ["# Experiment Plan", "", f"Goal: {plan.goal}", ""]
    lines += _render_steps("Environment", plan.environment_steps)
    lines += _render_steps("Data", plan.data_steps)
    lines += _render_steps("Train", plan.train_steps)
    lines += _render_steps("Eval", plan.eval_steps)

    lines += ["## Run Commands", ""]
    for command in plan.run_commands:
        lines.append(f"```bash\n{command.command}\n```")
        lines.append(f"- cwd: `{command.cwd}`")
        lines.append(f"- source: {command.source}")
        lines.append(f"- risk: {command.risk_level}")
        lines.append(f"- reason: {command.reason}")
        lines.append("")

    if plan.unresolved_questions:
        lines += ["## Unresolved Questions", ""]
        for item in plan.unresolved_questions:
            lines.append(f"- {item}")
    return "\n".join(lines)
```

## CLI 入口

在 `map_code` 的基础上继续调用：

```python
from app.nodes.experiment_plan_node import experiment_plan_node


# 串联前面阶段并生成最终的复现实验计划。
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
```

## 本阶段验收

检查 `outputs/experiment_plan.md`：

- 是否有环境、数据、训练、评估四类步骤。
- 命令是否标记了来源。
- 不确定路径和参数是否进入 unresolved questions。
- 高风险动作是否被标记，而不是直接执行。

## 常见坑

- 不要因为 README 没写命令，就让模型编一个看似合理的命令。
- 安装依赖和运行训练都算有风险，后续 V6 再加审批。
- 实验计划要“人能照着做”，而不是写成泛泛建议。
