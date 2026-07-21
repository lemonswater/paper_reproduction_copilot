from unittest.mock import patch

from app.nodes.final_report_node import final_report_node


def test_final_report_node_writes_report_and_returns_output_file(tmp_path) -> None:
    state = {
        "paper_path": "pdf/demo.pdf",
        "repo_path": "/tmp/demo-repo",
        "experiment_goal": "复现论文 main result",
        "final_status": "failed",
        "user_approval": "approved",
        "paper_summary": {
            "title": "Demo Paper",
            "research_problem": "Demo problem",
            "core_idea": "Demo idea",
        },
        "repo_map": {
            "important_files": ["train.py", "models/model.py"],
        },
        "paper_code_mapping": [
            {
                "module_name": "Transformer",
                "candidates": [
                    {
                        "file_path": "models/model.py",
                        "confidence": "high",
                    }
                ],
            }
        ],
        "experiment_plan": {
            "goal": "复现论文 main result",
            "environment_steps": [],
            "data_steps": [],
            "train_steps": [],
            "eval_steps": [],
        },
        "run_commands": [
            {"command": "python train.py"}
        ],
        "pending_action": {
            "type": "run_command",
            "command": "python train.py",
            "source": "experiment_plan",
        },
        "execution_result": {
            "ok": False,
            "returncode": 1,
        },
        "execution_log_path": "outputs/execution.log",
        "debug_report": {
            "error_type": "cuda_oom",
            "most_likely_causes": ["batch size too large"],
        },
        "output_files": [],
    }

    with patch("app.nodes.final_report_node.settings.output_dir", tmp_path):
        result = final_report_node(state)

    assert "final_report" in result
    assert "Final Status" in result["final_report"]
    assert "Demo Paper" in result["final_report"]
    assert any(path.endswith("final_report.md") for path in result["output_files"])