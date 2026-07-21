from unittest.mock import patch

from app.execution.profile_store import compute_execution_profile_fingerprint
from app.nodes.repair_action_builder_node import repair_action_builder_node
from app.schemas import ExecutionProfile


def test_repair_action_builder_rebuilds_pending_action_and_increments_attempts():
    profile = ExecutionProfile(
        profile_id="paper-conda",
        backend="conda",
        workspace_root="/tmp/repo",
        artifact_root="/tmp/artifacts",
        conda_executable="/opt/conda/bin/conda",
        conda_prefix="/opt/conda/envs/paper",
    )
    state = {
        "repo_path": "/tmp/repo",
        "execution_profile_id": "paper-conda",
        "selected_run_command_index": 0,
        "edited_run_commands": [
            {
                "command": "python train.py --dataset_path /data/demo --batch_size 8 --epochs 100",
                "cwd": "/tmp/repo",
                "source": "script",
                "risk_level": "high",
                "reason": "demo command",
            }
        ],
        "repair_proposal": {
            "proposal_id": "repair_001",
            "source_error_type": "cuda_oom",
            "kind": "edit_command",
            "summary": "reduce batch size for smoke and rerun",
            "root_cause": "batch size too large",
            "repaired_command": "python train.py --dataset_path /data/demo --batch_size 1 --epochs 1",
            "changed_arguments": ["--batch_size 8 -> 1", "--epochs 100 -> 1"],
            "steps": [],
            "verification_steps": ["rerun smoke test", "rerun full executor"],
            "rollback_steps": [],
            "risks": [],
            "bounded": True,
        },
        "repair_attempt_count": 0,
        "repair_history": [],
        "user_approval": "approved",
        "approval_record": {"action_hash": "old_hash"},
        "preflight_report": {"ready_to_execute": True},
        "smoke_test_report": {"status": "failed"},
        "debug_report": {"error_type": "cuda_oom"},
        "execution_result": {"ok": False},
        "final_status": "failed",
    }

    with patch(
        "app.tools.repair_tools.get_execution_profile",
        return_value=profile,
    ):
        result = repair_action_builder_node(state)

    assert result["repair_attempt_count"] == 1
    assert result["pending_action"]["program"] == "python"
    assert "--batch_size" in result["pending_action"]["args"]
    assert result["execution_profile_id"] == "paper-conda"
    assert result["execution_profile_fingerprint"] == (
        compute_execution_profile_fingerprint(profile)
    )
    assert result["pending_action"]["execution_profile_id"] == "paper-conda"
    assert result["pending_action"]["execution_profile_fingerprint"] == (
        result["execution_profile_fingerprint"]
    )
    assert result["user_approval"] is None
    assert result["approval_record"] is None
    assert result["preflight_report"] is None
    assert result["smoke_test_report"] is None
    assert result["debug_report"] is None


def test_repair_action_builder_rejects_out_of_bounds_command():
    state = {
        "repair_proposal": {
            "proposal_id": "repair_001",
            "source_error_type": "dependency_missing",
            "kind": "edit_command",
            "summary": "install missing package",
            "root_cause": "package missing",
            "repaired_command": "pip install torch",
            "changed_arguments": [],
            "steps": [],
            "verification_steps": [],
            "rollback_steps": [],
            "risks": ["environment mutation"],
            "bounded": True,
        },
        "repair_attempt_count": 0,
    }

    result = repair_action_builder_node(state)

    assert result["final_status"] == "repair_out_of_bounds"
