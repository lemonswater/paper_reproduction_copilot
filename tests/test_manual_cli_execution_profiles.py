from unittest.mock import patch

from app.execution.profile_store import compute_execution_profile_fingerprint
from app.main import plan_repair, run_smoke
from app.schemas import ExecutionProfile


def _test_profile() -> ExecutionProfile:
    return ExecutionProfile(
        profile_id="paper-conda",
        backend="conda",
        workspace_root="/tmp/paper-repo",
        artifact_root="/tmp/artifacts",
        conda_executable="/opt/conda/bin/conda",
        conda_prefix="/opt/conda/envs/paper",
    )


def test_run_smoke_binds_action_to_execution_profile() -> None:
    profile = _test_profile()
    fake_result = {
        "smoke_test_report": {"status": "passed"},
        "output_files": [],
    }

    with patch("app.main.get_execution_profile", return_value=profile), patch(
        "app.main.smoke_test_node",
        return_value=fake_result,
    ) as smoke_node, patch("app.main.print"):
        run_smoke(
            repo_path=profile.workspace_root,
            command="python train.py --epochs 1",
            cwd=None,
            source="script",
            reason="smoke test",
            execution_profile=profile.profile_id,
        )

    state = smoke_node.call_args.args[0]
    expected_fingerprint = compute_execution_profile_fingerprint(profile)
    assert state["execution_profile_id"] == profile.profile_id
    assert state["execution_profile_fingerprint"] == expected_fingerprint
    assert state["pending_action"]["execution_profile_id"] == profile.profile_id
    assert (
        state["pending_action"]["execution_profile_fingerprint"]
        == expected_fingerprint
    )


def test_plan_repair_binds_action_to_execution_profile(tmp_path) -> None:
    profile = _test_profile()
    log_path = tmp_path / "execution.log"
    log_path.write_text("RuntimeError: CUDA out of memory", encoding="utf-8")

    with patch("app.main.get_execution_profile", return_value=profile), patch(
        "app.main.log_debug_node",
        return_value={"debug_report": {"error_type": "cuda_oom"}},
    ) as debug_node, patch(
        "app.main.repair_planner_node",
        return_value={"repair_proposal": {"kind": "edit_command"}},
    ), patch("app.main.print"):
        plan_repair(
            repo_path=profile.workspace_root,
            log_path=str(log_path),
            command="python train.py --batch_size 8",
            cwd=None,
            source="script",
            reason="repair planning",
            execution_profile=profile.profile_id,
        )

    state = debug_node.call_args.args[0]
    expected_fingerprint = compute_execution_profile_fingerprint(profile)
    assert state["execution_profile_id"] == profile.profile_id
    assert state["pending_action"]["execution_profile_id"] == profile.profile_id
    assert (
        state["pending_action"]["execution_profile_fingerprint"]
        == expected_fingerprint
    )
