from __future__ import annotations

import json

from app.config import settings
from app.model_routing.factory import build_model_gateway
from app.prompts.plan_prompt import EXPERIMENT_PLAN_PROMPT
from app.schemas import ExperimentPlan
from app.tools.artifact_tools import (
    artifact_dir,
    artifact_state_update,
    register_existing_artifact,
    write_json_artifact,
    write_text_artifact,
)
from app.tools.error_tools import (
    stage_error_result,
    structured_failure_update,
)
from app.tools.structured_output_tools import (
    write_structured_output_trace,
)


def _build_plan_fallback(*, goal: str, reason: str) -> ExperimentPlan:
    return ExperimentPlan(
        goal=goal,
        environment_steps=[],
        data_steps=[],
        train_steps=[],
        eval_steps=[],
        run_commands=[],
        risks=[
            "实验计划缺少可信结构化结果，禁止进入自动执行。",
        ],
        unresolved_questions=[reason],
    )


def _render_steps(title: str, steps: list) -> list[str]:
    lines = [f"## {title}", ""]
    if not steps:
        lines.append("- 暂无明确步骤")
        lines.append("")
        return lines

    for step in steps:
        lines.append(f"### {step.order}. {step.name}")
        lines.append("")
        lines.append(f"- 动作：{step.action}")
        lines.append(f"- 来源：{step.source}")
        if step.risk:
            lines.append(f"- 风险：{step.risk}")
        lines.append("")
    return lines


def _render_plan_markdown(plan: ExperimentPlan) -> str:
    lines = ["# 实验计划", "", f"目标：{plan.goal}", ""]
    lines += _render_steps("环境", plan.environment_steps)
    lines += _render_steps("数据", plan.data_steps)
    lines += _render_steps("训练", plan.train_steps)
    lines += _render_steps("评估", plan.eval_steps)

    lines += ["## 运行命令", ""]
    for command in plan.run_commands:
        lines.append(f"```bash\n{command.command}\n```")
        lines.append(f"- 工作目录（cwd）：`{command.cwd}`")
        lines.append(f"- 来源：{command.source}")
        lines.append(f"- 风险：{command.risk_level}")
        lines.append(f"- 原因：{command.reason}")
        lines.append("")

    if plan.unresolved_questions:
        lines += ["## 待解决问题", ""]
        for item in plan.unresolved_questions:
            lines.append(f"- {item}")
    return "\n".join(lines)


def experiment_plan_node(state: dict) -> dict:
    paper_summary = state.get("paper_summary")
    repo_map = state.get("repo_map")
    paper_code_mapping = state.get("paper_code_mapping")
    experiment_goal = state.get("experiment_goal") or "复现论文 main result"
    trace_path = None
    invocation = None

    missing_inputs = [
        name
        for name, value in (
            ("paper_summary", paper_summary),
            ("repo_map", repo_map),
            ("paper_code_mapping", paper_code_mapping),
        )
        if not value
    ]

    if missing_inputs:
        # 输入不足时没有调用模型，因此也不生成 structured attempt trace。
        plan = _build_plan_fallback(
            goal=experiment_goal,
            reason=("缺少实验规划输入：" + ", ".join(missing_inputs)),
        )
    else:
        prompt = EXPERIMENT_PLAN_PROMPT.format(
            paper_summary=json.dumps(
                paper_summary,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            repo_map=json.dumps(
                repo_map,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            paper_code_mapping=json.dumps(
                paper_code_mapping,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            experiment_goal=experiment_goal,
        )

        invocation = build_model_gateway().invoke_structured(
            task_kind="experiment_plan",
            schema=ExperimentPlan,
            prompt=prompt,
            node_name="experiment_plan",
            job_id=state.get("job_id"),
            run_id=state.get("run_id"),
            quality_tier="balanced",
        )

        if invocation.value is not None:
            plan = invocation.value

            # goal 来自用户输入，不允许模型悄悄改写任务目标。
            if plan.goal != experiment_goal:
                plan = plan.model_copy(update={"goal": experiment_goal})
        else:
            plan = _build_plan_fallback(
                goal=experiment_goal,
                reason=("模型在有限重试后仍未返回合法 ExperimentPlan。"),
            )

        trace_path = write_structured_output_trace(
            result=invocation.result,
            node_name="experiment_plan",
            schema_name="ExperimentPlan",
            output_dir=artifact_dir(
                state,
                "traces",
                "structured",
            ),
            fallback_used=invocation.value is None,
            model_invocation_id=invocation.invocation_id,
            model_decision_sha256=(
                invocation.decision.decision_sha256
            ),
            model_profile_id=(
                invocation.decision.executed_profile_id
            ),
            model_name=(
                invocation.decision.executed_model_name
            ),
            model_usage_quality=(
                invocation.ledger_record.usage_quality
                if invocation.ledger_record is not None
                else None
            ),
        )

    _, json_record = write_json_artifact(
        state=state,
        relative_path="planning/experiment_plan.json",
        payload=plan.model_dump(),
        producer_node="experiment_plan",
    )
    _, md_record = write_text_artifact(
        state=state,
        relative_path="planning/experiment_plan.md",
        text=_render_plan_markdown(plan),
        producer_node="experiment_plan",
        media_type="text/markdown",
    )

    records = [json_record, md_record]
    if trace_path is not None:
        records.append(
            register_existing_artifact(
                state=state,
                path=trace_path,
                producer_node="experiment_plan",
                media_type="application/json",
            )
        )

    payload = {
        "experiment_plan": plan.model_dump(),
        "run_commands": [command.model_dump() for command in plan.run_commands],
        **artifact_state_update(state, records),
    }

    if missing_inputs:
        return stage_error_result(
            state={**state, **payload},
            stage="experiment_plan",
            code="EXPERIMENT_PLAN_INPUT_MISSING",
            category="agent",
            message="缺少实验规划输入：" + ", ".join(missing_inputs),
            extra_update=payload,
        )

    if invocation is not None and invocation.value is None:
        working_state = {**state, **payload}
        return {
            **payload,
            **structured_failure_update(
                state=working_state,
                stage="experiment_plan",
                invocation=invocation,
                terminal=True,
            ),
        }

    return payload
