import json
from app.config import settings
from app.model import get_chat_model
from app.prompts.plan_prompt import EXPERIMENT_PLAN_PROMPT
from app.schemas import ExperimentPlan

def experiment_plan_node(state: dict) -> dict:
    paper_summary = state.get("paper_summary")
    repo_map = state.get("repo_map")
    paper_code_mapping = state.get("paper_code_mapping")
    if not paper_summary or not repo_map or not paper_code_mapping:
        return {"error": "ecperiment plan requires paper_summary, repo_map and mapping"}
    
    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(ExperimentPlan)

    plan: ExperimentPlan = structured_llm.invoke(
        EXPERIMENT_PLAN_PROMPT.format(
            paper_summary=json.dumps(paper_summary, ensure_ascii=False, indent=2),
            repo_map=json.dumps(repo_map, ensure_ascii=False, indent=2),
            paper_code_mapping=json.dumps(paper_code_mapping, ensure_ascii=False, indent=2),
            experiment_goal=state.get("experiment_goal") or "复现论文 main result"
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
            str(md_path)
        ]
    }

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