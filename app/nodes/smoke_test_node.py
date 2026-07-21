from app.config import settings
from app.tools.action_tools import compute_action_hash
from app.tools.exec_tools import run_action_safe
from app.tools.smoke_test_tools import (
    build_smoke_test_report,
    derive_smoke_test_action,
    render_smoke_test_report_md,
)


def smoke_test_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {
            "smoke_test_report": None,
            "smoke_test_status": "blocked",
            "smoke_test_passed": False,
            "final_status": "blocked",
            "error": "missing pending_action before smoke_test",
        }

    smoke_action, overrides, summary = derive_smoke_test_action(pending_action)

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = settings.output_dir / "smoke_test_report.json"
    report_md_path = settings.output_dir / "smoke_test_report.md"

    if smoke_action is None:
        # 当前命令不适合被安全缩减，这不算失败，只是跳过。
        report = build_smoke_test_report(
            action=pending_action,
            action_hash=state.get("pending_action_hash"),
            status="skipped",
            summary=summary,
            applied_overrides=[],
            result={},
            log_path=None,
        )

        report_json_path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        report_md_path.write_text(
            render_smoke_test_report_md(report),
            encoding="utf-8",
        )

        return {
            "smoke_test_report": report.model_dump(),
            "smoke_test_status": "skipped",
            # skipped 在图路由上等价于“允许继续 full executor”
            "smoke_test_passed": True,
            "output_files": [
                *state.get("output_files", []),
                str(report_json_path),
                str(report_md_path),
            ],
        }

    smoke_action_hash = compute_action_hash(smoke_action)
    result = run_action_safe(smoke_action)

    smoke_log_path = settings.output_dir / "smoke_test.log"
    smoke_log_path.write_text(result["combined_output"], encoding="utf-8")

    status = "passed" if result["ok"] else "failed"
    report = build_smoke_test_report(
        action=smoke_action,
        action_hash=smoke_action_hash,
        status=status,
        summary=summary,
        applied_overrides=overrides,
        result=result,
        log_path=str(smoke_log_path),
    )

    report_json_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_md_path.write_text(
        render_smoke_test_report_md(report),
        encoding="utf-8",
    )

    payload = {
        "active_execution_mode": "smoke",
        "smoke_test_report": report.model_dump(),
        "smoke_test_status": status,
        "smoke_test_passed": status == "passed",
        "smoke_test_log_path": str(smoke_log_path),
        "output_files": [
            *state.get("output_files", []),
            str(smoke_log_path),
            str(report_json_path),
            str(report_md_path),
        ],
    }

    if status == "failed":
        payload["log_path"] = str(smoke_log_path)
        payload["final_status"] = "failed"
        payload["last_action_result"] = {
            "status": "smoke_failed",
            "pending_action": smoke_action,
            "returncode": result["returncode"],
        }

    return payload