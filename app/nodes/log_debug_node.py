import json
from app.config import settings
from app.model import get_chat_model
from app.prompts.debug_prompt import DEBUG_PROMPT
from app.schemas import DebugReport
from app.tools.log_tools import classify_error_heuristic, extract_traceback, read_log

def log_debug_node(state: dict) -> dict:
    log_path = state.get("log_path")
    if not log_path:
        return {"error": "log_path is required"}

    log_text = read_log(log_path)
    traceback = extract_traceback(log_text)
    error_type = classify_error_heuristic(traceback)

    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(DebugReport)

    report: DebugReport = structured_llm.invoke(
        DEBUG_PROMPT.format(
            error_type=error_type,
            traceback=traceback,
            repo_map=json.dumps(state.get("repo_map", {}), ensure_ascii=False, indent=2),
            experiment_plan=json.dumps(
                state.get("experiment_plan", {}),
                ensure_ascii=False,
                indent=2,
            ),
        )
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