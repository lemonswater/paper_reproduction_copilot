from unittest.mock import patch

from app.config import settings
from app.graph import (
    route_after_log_debug,
    route_after_preflight,
    route_after_repair_action_builder,
    route_after_repair_planner,
    route_after_smoke_test,
)
from app.nodes.repair_planner_node import repair_planner_node
from app.nodes.log_debug_node import log_debug_node


def test_route_after_preflight_goes_to_smoke_when_passed():
    assert route_after_preflight({"preflight_passed": True}) == "smoke_test"


def test_route_after_smoke_test_goes_to_executor_when_passed():
    assert route_after_smoke_test({"smoke_test_status": "passed"}) == "executor"


def test_route_after_smoke_test_goes_to_executor_when_skipped():
    assert route_after_smoke_test({"smoke_test_status": "skipped"}) == "executor"


def test_route_after_smoke_test_goes_to_log_debug_when_failed():
    state = {
        "smoke_test_status": "failed",
        "log_path": "outputs/smoke_test.log",
    }
    assert route_after_smoke_test(state) == "log_debug"


def test_route_after_log_debug_goes_to_repair_planner_before_limit():
    assert route_after_log_debug({"repair_attempt_count": 0}) == "repair_planner"


def test_route_after_repair_planner_goes_to_repair_action_builder_for_edit_command():
    state = {
        "repair_proposal": {
            "kind": "edit_command",
            "repaired_command": "python train.py --batch_size 1",
        }
    }
    assert route_after_repair_planner(state) == "repair_action_builder"


def test_route_after_repair_action_builder_returns_to_risk_check():
    assert route_after_repair_action_builder({"pending_action": {"action_type": "run_command"}}) == "risk_check"


def test_cuda_oom_builds_bounded_batch_size_repair_without_llm(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")
    state = {
        "debug_report": {"error_type": "cuda_oom"},
        "pending_action": {
            "program": "python",
            "args": [
                "train-msr-small.py",
                "--data-path",
                "/data/msr",
                "--batch-size",
                "8",
                "--epochs",
                "100",
            ],
        },
        "output_files": [],
    }

    with patch("app.nodes.repair_planner_node.get_chat_model") as get_model:
        result = repair_planner_node(state)

    get_model.assert_not_called()
    proposal = result["repair_proposal"]
    assert proposal["kind"] == "edit_command"
    assert "--batch-size 1" in proposal["repaired_command"]
    assert proposal["changed_arguments"] == ["--batch-size 8 -> 1"]


def test_cuda_oom_debug_report_does_not_require_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")
    log_path = tmp_path / "execution.log"
    log_path.write_text(
        "Traceback (most recent call last):\n"
        "RuntimeError: CUDA out of memory\n",
        encoding="utf-8",
    )

    with patch("app.nodes.log_debug_node.get_chat_model") as get_model:
        result = log_debug_node(
            {"log_path": str(log_path), "output_files": []}
        )

    get_model.assert_not_called()
    assert result["debug_report"]["error_type"] == "cuda_oom"
