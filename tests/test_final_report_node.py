from __future__ import annotations

import json
from pathlib import Path

from app.nodes.final_report_node import final_report_node


def test_final_report_node_writes_supervision_summary(run_state) -> None:
    process_record_path = (
        Path(run_state["run_dir"])
        / "execution"
        / "attempts"
        / "exec-test"
        / "process_record.json"
    )
    process_record_path.parent.mkdir(parents=True)
    process_record_path.write_text(
        json.dumps(
            {
                "execution_id": "exec-test",
                "pid": 123,
                "pgid": 123,
                "duration_seconds": 1.25,
                "end_reason": "memory_limit",
                "termination_signal": 15,
                "hard_kill_used": False,
                "resource_usage": {
                    "peak_rss_bytes": 2048,
                    "peak_process_count": 2,
                    "total_cpu_seconds": 0.5,
                    "total_write_bytes": 128,
                },
            }
        ),
        encoding="utf-8",
    )
    state = {
        **run_state,
        "paper_path": "pdf/demo.pdf",
        "repo_path": "/tmp/demo-repo",
        "experiment_goal": "复现论文 main result",
        "final_status": "failed",
        "user_approval": "approved",
        "execution_profile_id": "test-local",
        "paper_summary": {
            "title": "Demo Paper",
            "research_problem": "Demo problem",
            "core_idea": "Demo idea",
        },
        "repo_map": {"important_files": ["train.py"]},
        "paper_code_mapping": [
            {
                "module_name": "MSR-Action3D",
                "target_category": "data_pipeline",
                "candidates": [],
            }
        ],
        "experiment_plan": {"goal": "复现论文 main result"},
        "run_commands": [{"command": "python train.py"}],
        "pending_action": {
            "action_type": "run_command",
            "program": "python",
            "args": ["train.py"],
            "network_access": "none",
            "source": "script",
        },
        "execution_result": {
            "ok": False,
            "returncode": -15,
            "execution_backend": "local",
            "log_truncated": True,
        },
        "active_execution_id": "exec-test",
        "active_process_record_path": str(process_record_path),
        "execution_end_reason": "memory_limit",
        "execution_resource_usage": {
            "peak_rss_bytes": 2048,
            "peak_process_count": 2,
            "total_cpu_seconds": 0.5,
            "total_write_bytes": 128,
        },
        "preflight_report": {
            "execution_enforcement_mode": "best_effort"
        },
        "debug_report": {},
    }

    result = final_report_node(state)
    report = result["final_report"]

    assert "Demo Paper" in report
    assert "Execution Supervision" in report
    assert "exec-test" in report
    assert "memory_limit" in report
    assert "2048" in report
    assert "未提供 OS 级网络隔离" in report
    assert "可进入 Debug/Repair" in report
    assert "[data_pipeline] MSR-Action3D" in report
    report_path = Path(run_state["run_dir"]) / "reports" / "final_report.md"
    assert report_path.exists()
    assert str(report_path) in result["output_files"]


def test_final_report_distinguishes_user_cancellation(run_state) -> None:
    state = {
        **run_state,
        "final_status": "cancelled",
        "cancellation_requested": True,
        "cancellation_reason": "user stop",
    }

    report = final_report_node(state)["final_report"]

    assert "用户请求取消" in report
    assert "取消不是论文复现失败" in report
