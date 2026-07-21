from app.config import settings
from app.tools.preflight_tools import build_preflight_report, render_preflight_report_md


def preflight_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {
            "preflight_report": None,
            "preflight_passed": False,
            "final_status": "blocked",
            "error": "missing pending_action before preflight",
        }

    action_hash = state.get("pending_action_hash")
    report = build_preflight_report(
        pending_action,
        repo_path=state.get("repo_path"),
        action_hash=action_hash,
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = settings.output_dir / "preflight_report.json"
    report_md_path = settings.output_dir / "preflight_report.md"

    report_json_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_md_path.write_text(
        render_preflight_report_md(report),
        encoding="utf-8",
    )

    payload = {
        "preflight_report": report.model_dump(),
        "preflight_passed": report.ready_to_execute,
        "preflight_report_path": str(report_json_path),
        "output_files": [
            *state.get("output_files", []),
            str(report_json_path),
            str(report_md_path),
        ],
    }
    
    if not state.get("requires_approval") and not state.get("user_approval"):
        payload["user_approval"] = "not_required"

    if report.ready_to_execute:
        return payload

    payload["final_status"] = "blocked"
    payload["error"] = report.summary
    payload["last_action_result"] = {
        "status": "blocked_by_preflight",
        "pending_action": pending_action,
        "blocking_items": report.blocking_items,
    }
    return payload