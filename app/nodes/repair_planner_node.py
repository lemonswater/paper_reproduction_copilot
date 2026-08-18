from __future__ import annotations

import json
import shlex
from uuid import uuid4

from app.config import settings
from app.model_routing.factory import build_model_gateway
from app.prompts.repair_prompt import REPAIR_PROMPT
from app.schemas import RepairProposal
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
from app.tools.repair_tools import render_repair_proposal_md
from app.tools.structured_output_tools import (
    write_structured_output_trace,
)

CUDA_OOM_BATCH_FLAGS = ("--batch-size", "--batch_size", "-b")


def _build_cuda_oom_repair_proposal(
    pending_action: dict,
) -> RepairProposal | None:
    """仅缩小命令中已有的 batch 参数，不引入新的执行语义。"""

    program = str(pending_action.get("program") or "").strip()
    args = list(pending_action.get("args") or [])
    if not program or not args:
        return None

    updated_args = list(args)
    changed_argument: str | None = None
    rollback_argument: str | None = None

    for index, token in enumerate(updated_args):
        if token in CUDA_OOM_BATCH_FLAGS and index + 1 < len(updated_args):
            old_value = updated_args[index + 1]
            if old_value == "1":
                return None
            updated_args[index + 1] = "1"
            changed_argument = f"{token} {old_value} -> 1"
            rollback_argument = f"将 {token} 从 1 恢复为 {old_value}"
            break

        for flag in CUDA_OOM_BATCH_FLAGS:
            prefix = f"{flag}="
            if token.startswith(prefix):
                old_value = token[len(prefix):]
                if old_value == "1":
                    return None
                updated_args[index] = f"{flag}=1"
                changed_argument = f"{flag}={old_value} -> {flag}=1"
                rollback_argument = f"将 {flag}=1 恢复为 {flag}={old_value}"
                break
        if changed_argument:
            break

    if not changed_argument or not rollback_argument:
        return None

    repaired_command = shlex.join([program, *updated_args])
    return RepairProposal(
        proposal_id=f"repair_{uuid4().hex[:12]}",
        source_error_type="cuda_oom",
        kind="edit_command",
        summary="检测到 CUDA OOM，将已有 batch size 有界缩小为 1。",
        root_cause="当前 batch size 导致单次计算的 GPU 显存需求过高。",
        repaired_command=repaired_command,
        changed_arguments=[changed_argument],
        steps=[
            {
                "step_type": "edit_command",
                "target": "run_command",
                "change": changed_argument,
                "reason": "降低单次迭代的 GPU 显存占用",
                "risk": "low",
            },
            {
                "step_type": "rerun_smoke",
                "target": "smoke_test",
                "change": "使用修复后的命令重新运行 smoke test",
                "reason": "先验证最小负载能否通过",
                "risk": "low",
            },
        ],
        verification_steps=[
            "使用 batch size 1 重新运行 smoke test",
            "smoke test 通过后再运行 full executor",
        ],
        rollback_steps=[rollback_argument],
        risks=[
            "batch size 变化会影响吞吐量，正式复现时可能需要重新调整学习率。",
        ],
        bounded=True,
    )


def _build_no_repair_proposal(
    *,
    error_type: str,
    summary: str,
    root_cause: str,
) -> RepairProposal:
    """在证据不足或模型格式错误时生成保守的有界结果。"""

    return RepairProposal(
        proposal_id=f"repair_{uuid4().hex[:12]}",
        source_error_type=error_type,
        kind="no_repair",
        summary=summary,
        root_cause=root_cause,
        repaired_command=None,
        changed_arguments=[],
        steps=[],
        verification_steps=[
            "获取真实失败日志后重新运行 smoke test",
            "smoke test 通过后再运行 full executor",
        ],
        rollback_steps=[],
        risks=["证据不足时自动修改命令可能掩盖真实问题"],
        bounded=True,
    )


def _build_file_repair_handoff_proposal(
    *,
    error_type: str,
    related_files: list[str],
) -> RepairProposal:
    """
    将证据明确的源码类错误移交给受限文件修复流程。

    command repair planner 不在这里猜测命令参数或生成 patch；后续仍需经过
    file repair planner、patch 审批、隔离验证和 promotion 审批。
    """

    targets = ", ".join(related_files)
    return RepairProposal(
        proposal_id=f"repair_{uuid4().hex[:12]}",
        source_error_type=error_type,
        kind="manual_only",
        summary="错误已定位到仓库文件，移交受限文件修复流程审查。",
        root_cause=(
            "traceback 显示 shape mismatch，并关联到仓库内的源码或测试文件。"
        ),
        repaired_command=None,
        changed_arguments=[],
        steps=[
            {
                "step_type": "manual_check",
                "target": targets,
                "change": "检查相关文件并生成最小、可审阅的文件修复建议",
                "reason": "当前错误不能通过有界命令参数修改可靠解决",
                "risk": "medium",
            },
        ],
        verification_steps=[
            "只在隔离 worktree 中应用候选 patch",
            "运行原失败行为测试验证 patch",
        ],
        rollback_steps=[],
        risks=[
            "shape mismatch 也可能来自输入或配置，文件修复规划仍需验证证据。",
        ],
        bounded=True,
    )


def repair_planner_node(state: dict) -> dict:
    debug_report = state.get("debug_report")
    if not debug_report:
        proposal = _build_no_repair_proposal(
            error_type="unknown",
            summary="缺少 debug_report，无法生成修复计划",
            root_cause="debug_report 不可用",
        )
        _, json_record = write_json_artifact(
            state=state,
            relative_path="debug/repair_proposal.json",
            payload=proposal.model_dump(),
            producer_node="repair_planner",
        )
        _, md_record = write_text_artifact(
            state=state,
            relative_path="debug/repair_proposal.md",
            text=render_repair_proposal_md(proposal.model_dump()),
            producer_node="repair_planner",
            media_type="text/markdown",
        )
        payload = {
            "repair_proposal": proposal.model_dump(),
            **artifact_state_update(
                state,
                [json_record, md_record],
            ),
        }
        return stage_error_result(
            state={**state, **payload},
            stage="repair_planner",
            code="DEBUG_REPORT_REQUIRED",
            category="agent",
            message="缺少 debug_report，无法生成修复计划",
            extra_update=payload,
        )

    error_type = str(debug_report.get("error_type") or "unknown")
    trace_path = None
    invocation = None

    related_files = [
        str(path)
        for path in (debug_report.get("related_files") or [])
        if str(path).strip()
    ]

    deterministic_proposal = None
    if error_type == "cuda_oom":
        deterministic_proposal = _build_cuda_oom_repair_proposal(
            state.get("pending_action") or {}
        )
    elif error_type == "shape_mismatch" and related_files:
        deterministic_proposal = _build_file_repair_handoff_proposal(
            error_type=error_type,
            related_files=related_files,
        )

    if deterministic_proposal is not None:
        proposal = deterministic_proposal

    elif error_type == "unknown":
        proposal = _build_no_repair_proposal(
            error_type=error_type,
            summary="错误证据不足，不能生成可靠的自动修复命令。",
            root_cause="调试报告未识别出具体错误类型。",
        )

    else:
        prompt = REPAIR_PROMPT.format(
            execution_mode=state.get("active_execution_mode", "unknown"),
            pending_action=json.dumps(
                state.get("pending_action", {}),
                ensure_ascii=False,
                indent=2,
            ),
            preflight_report=json.dumps(
                state.get("preflight_report", {}),
                ensure_ascii=False,
                indent=2,
            ),
            smoke_test_report=json.dumps(
                state.get("smoke_test_report", {}),
                ensure_ascii=False,
                indent=2,
            ),
            debug_report=json.dumps(
                debug_report,
                ensure_ascii=False,
                indent=2,
            ),
        )

        invocation = build_model_gateway().invoke_structured(
            task_kind="repair_plan",
            schema=RepairProposal,
            prompt=prompt,
            node_name="repair_planner",
            job_id=state.get("job_id"),
            run_id=state.get("run_id"),
            quality_tier="high",
        )

        if invocation.value is not None:
            proposal = invocation.value
        else:
            proposal = _build_no_repair_proposal(
                error_type=error_type,
                summary=(
                    "模型在有限重试后仍未返回合法 RepairProposal，"
                    "已安全降级。"
                ),
                root_cause="结构化输出校验连续失败。",
            )

        trace_path = write_structured_output_trace(
            result=invocation.result,
            node_name="repair_planner",
            schema_name="RepairProposal",
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

    if not proposal.proposal_id:
        proposal = proposal.model_copy(
            update={"proposal_id": f"repair_{uuid4().hex[:12]}"}
        )

    _, json_record = write_json_artifact(
        state=state,
        relative_path="debug/repair_proposal.json",
        payload=proposal.model_dump(),
        producer_node="repair_planner",
    )
    _, md_record = write_text_artifact(
        state=state,
        relative_path="debug/repair_proposal.md",
        text=render_repair_proposal_md(proposal.model_dump()),
        producer_node="repair_planner",
        media_type="text/markdown",
    )

    records = [json_record, md_record]
    if trace_path is not None:
        records.append(
            register_existing_artifact(
                state=state,
                path=trace_path,
                producer_node="repair_planner",
                media_type="application/json",
            )
        )

    payload = {
        "repair_proposal": proposal.model_dump(),
        **artifact_state_update(state, records),
    }

    if invocation is not None and invocation.value is None:
        payload.update(
            structured_failure_update(
                state={**state, **payload},
                stage="repair_planner",
                invocation=invocation,
                terminal=False,
            )
        )

    return payload
