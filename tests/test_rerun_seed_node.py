# tests/test_rerun_seed_node.py
from __future__ import annotations

from app.config import settings
from app.nodes.rerun_seed_node import rerun_seed_node


def test_normal_job_is_noop() -> None:
    assert rerun_seed_node({}) == {}


def test_rerun_seed_overrides_commands_and_clears_approval(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "runs_dir", tmp_path)
    run_dir = tmp_path / "run-child"
    state = {
        "run_id": "run-child",
        "run_dir": str(run_dir),
        "artifact_records": [],
        "output_files": [],
        "run_commands": [
            {
                "command": "python wrong.py",
                "cwd": "/wrong",
                "source": "inferred",
                "risk_level": "low",
                "reason": "LLM candidate",
            }
        ],
        "pending_action": {"command": "old"},
        "pending_action_hash": "a" * 64,
        "user_approval": "approved",
        "approval_record": {"decision": "approved"},
        "rerun_seed": {
            "proposal_id": "rerun_" + "1" * 24,
            "proposal_hash": "2" * 64,
            "source": {"parent_job_id": "job-parent"},
            "template_hash": "3" * 64,
            "run_command": {
                "command": "python train.py --epochs 100",
                "cwd": str(tmp_path / "repo"),
                "source": "config",
                "risk_level": "high",
                "reason": "trusted rerun seed",
            },
        },
    }
    update = rerun_seed_node(state)
    assert update["run_commands"][0]["command"].endswith("--epochs 100")
    assert update["pending_action"] is None
    assert update["pending_action_hash"] is None
    assert update["user_approval"] is None
    assert update["approval_record"] is None
    assert update["requires_approval"] is False
    assert update["rerun_seed_path"].endswith("planning/rerun_seed.json")
    assert len(update["artifact_records"]) == 1
