import json
import shlex
from uuid import uuid4

from pydantic import ValidationError

from app.config import settings
from app.model import get_chat_model
from app.prompts.repair_prompt import REPAIR_PROMPT
from app.schemas import RepairProposal
from app.tools.repair_tools import render_repair_proposal_md


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


def repair_planner_node(state: dict) -> dict:
    debug_report = state.get("debug_report")
    if not debug_report:
        return {
            "repair_proposal": {
                "proposal_id": None,
                "source_error_type": "unknown",
                "kind": "no_repair",
                "summary": "missing debug_report, cannot plan repair",
                "root_cause": "debug_report not available",
                "repaired_command": None,
                "changed_arguments": [],
                "steps": [],
                "verification_steps": [],
                "rollback_steps": [],
                "risks": [],
                "bounded": True,
            }
        }

    error_type = str(debug_report.get("error_type") or "unknown")
    deterministic_proposal = None
    if error_type == "cuda_oom":
        deterministic_proposal = _build_cuda_oom_repair_proposal(
            state.get("pending_action") or {}
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
        llm = get_chat_model(temperature=0)
        structured_llm = llm.with_structured_output(
            RepairProposal,
            include_raw=True,
        )

        try:
            result = structured_llm.invoke(
                REPAIR_PROMPT.format(
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
            )
            parsed = result.get("parsed") if isinstance(result, dict) else result
            proposal = RepairProposal.model_validate(parsed)
        except (AttributeError, TypeError, ValidationError):
            proposal = _build_no_repair_proposal(
                error_type=error_type,
                summary="模型的 repair proposal 未通过结构校验，已安全降级。",
                root_cause="模型输出不符合 RepairProposal schema。",
            )

    if not proposal.proposal_id:
        proposal = proposal.model_copy(
            update={"proposal_id": f"repair_{uuid4().hex[:12]}"}
        )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "repair_proposal.json"
    md_path = settings.output_dir / "repair_proposal.md"

    json_path.write_text(
        proposal.model_dump_json(indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        render_repair_proposal_md(proposal.model_dump()),
        encoding="utf-8",
    )

    return {
        "repair_proposal": proposal.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(json_path),
            str(md_path),
        ],
    }
