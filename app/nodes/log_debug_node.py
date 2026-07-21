import json
from pydantic import ValidationError

from app.config import settings
from app.model import get_chat_model
from app.prompts.debug_prompt import DEBUG_PROMPT
from app.schemas import DebugReport
from app.tools.log_tools import classify_error_heuristic, extract_traceback, read_log


def _build_fallback_report(
    *,
    error_type: str,
    traceback: str,
    log_path: str,
) -> DebugReport:
    """在没有错误证据或模型格式错误时返回保守、可继续流转的报告。"""

    if not traceback.strip():
        return DebugReport(
            error_type="unknown",
            most_likely_causes=[
                "日志中没有检测到 traceback 或已知错误关键字。",
            ],
            related_files=[],
            check_order=[
                f"确认 {log_path} 是失败执行产生的日志，而不是 --help 输出。",
                "重新执行失败命令，并同时保存 stdout、stderr 和返回码。",
                "使用新生成的失败日志重新运行 plan-repair。",
            ],
            suggested_fixes=[
                "先获取真实失败日志；当前证据不足，不应自动修改命令。",
            ],
            risks=[
                "根据没有错误信息的日志制定修复方案可能导致误判。",
            ],
            unresolved_questions=[
                "原命令的非零返回码和 stderr 是什么？",
            ],
        )

    return DebugReport(
        error_type=error_type,
        most_likely_causes=[
            "检测到了错误证据，但模型返回结果未通过 DebugReport 结构校验。",
        ],
        related_files=[],
        check_order=[
            "先根据原始 traceback 和错误类型初判进行人工排查。",
            "确认日志完整后重新生成结构化调试报告。",
        ],
        suggested_fixes=[
            "保留原始日志，在证据确认前不要自动执行修复命令。",
        ],
        risks=[
            "fallback 报告没有模型的上下文诊断，可能遗漏具体根因。",
        ],
        unresolved_questions=[
            "模型为何没有返回符合 DebugReport 的结构？",
        ],
    )


def _build_cuda_oom_report() -> DebugReport:
    """为证据明确的 CUDA OOM 提供无需 LLM 的确定性诊断。"""

    return DebugReport(
        error_type="cuda_oom",
        most_likely_causes=[
            "当前 batch size 导致单次前向或反向计算的 GPU 显存需求过高。",
            "GPU 上可能同时存在其他进程，导致可用显存不足。",
        ],
        related_files=["train-msr-small.py"],
        check_order=[
            "使用 nvidia-smi 检查 GPU 可用显存和其他占用进程。",
            "将命令中已有的 batch size 缩小为 1 后重新运行 smoke test。",
            "若仍然 OOM，再检查输入点数、clip length 和模型维度。",
        ],
        suggested_fixes=[
            "优先把已有 batch size 参数缩小为 1，不修改源码或依赖环境。",
        ],
        risks=[
            "batch size 变化会影响吞吐量，正式训练时可能需要重新评估学习率。",
        ],
        unresolved_questions=[
            "失败时 GPU 上是否存在其他占用显存的进程？",
        ],
    )

def log_debug_node(state: dict) -> dict:
    log_path = state.get("log_path")
    if not log_path:
        return {"error": "log_path is required"}

    log_text = read_log(log_path)
    traceback = extract_traceback(log_text)
    error_type = classify_error_heuristic(traceback)

    if error_type == "cuda_oom":
        report = _build_cuda_oom_report()
    elif not traceback.strip():
        report = _build_fallback_report(
            error_type=error_type,
            traceback=traceback,
            log_path=log_path,
        )
    else:
        llm = get_chat_model(temperature=0)
        structured_llm = llm.with_structured_output(
            DebugReport,
            include_raw=True,
        )

        try:
            result = structured_llm.invoke(
                DEBUG_PROMPT.format(
                    error_type=error_type,
                    traceback=traceback,
                    repo_map=json.dumps(
                        state.get("repo_map", {}),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    experiment_plan=json.dumps(
                        state.get("experiment_plan", {}),
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            )
            parsed = result.get("parsed") if isinstance(result, dict) else result
            report = DebugReport.model_validate(parsed)
            if report.error_type != error_type:
                report = report.model_copy(update={"error_type": error_type})
        except (AttributeError, TypeError, ValidationError):
            report = _build_fallback_report(
                error_type=error_type,
                traceback=traceback,
                log_path=log_path,
            )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "debug_report.json"
    md_path = settings.output_dir / "debug_report.md"

    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_render_debug_markdown(report), encoding="utf-8")

    return {
        "debug_report": report.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(json_path),
            str(md_path),
        ],
    }

def _render_debug_markdown(report: DebugReport) -> str:
    lines = ["# Debug Report", "", f"Error Type: `{report.error_type}`", ""]
    sections = [
        ("Most Likely Causes", report.most_likely_causes),
        ("Related Files", report.related_files),
        ("Check Order", report.check_order),
        ("Suggested Fixes", report.suggested_fixes),
        ("Risks", report.risks),
        ("Unresolved Questions", report.unresolved_questions),
    ]
    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("- None")
        else:
            for item in items:
                lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)
