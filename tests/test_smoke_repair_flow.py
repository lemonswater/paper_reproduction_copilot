from __future__ import annotations

from unittest.mock import patch

from app.config import settings
from app.graph import (
    route_after_log_debug,
    route_after_preflight,
    route_after_repair_action_builder,
    route_after_repair_planner,
    route_after_smoke_test,
)
from app.nodes.log_debug_node import log_debug_node
from app.nodes.repair_planner_node import repair_planner_node
from app.schemas import DebugReport
from app.tools.log_tools import extract_repo_traceback_paths
from app.tools.structured_output_tools import StructuredInvocationResult
from tests.helpers.model_routing import ScriptedModelGateway


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
    run_state,
):
    state = {
        **run_state,
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
    }

    with patch("app.nodes.repair_planner_node.build_model_gateway") as get_model:
        result = repair_planner_node(state)

    get_model.assert_not_called()
    proposal = result["repair_proposal"]
    assert proposal["kind"] == "edit_command"
    assert "--batch-size 1" in proposal["repaired_command"]
    assert proposal["changed_arguments"] == ["--batch-size 8 -> 1"]


def test_cuda_oom_debug_report_does_not_require_llm(
    tmp_path,
    run_state,
):
    log_path = tmp_path / "execution.log"
    log_path.write_text(
        "Traceback (most recent call last):\n"
        "RuntimeError: CUDA out of memory\n",
        encoding="utf-8",
    )

    with patch("app.nodes.log_debug_node.build_model_gateway") as get_model:
        result = log_debug_node(
            {**run_state, "log_path": str(log_path)}
        )

    get_model.assert_not_called()
    assert result["debug_report"]["error_type"] == "cuda_oom"


def test_shape_mismatch_with_related_files_hands_off_to_file_repair(
    run_state,
    monkeypatch,
):
    monkeypatch.setattr(settings, "enable_file_repair", True)
    monkeypatch.setattr(settings, "max_file_repair_attempts", 1)
    state = {
        **run_state,
        "debug_report": {
            "error_type": "shape_mismatch",
            "related_files": [
                "tests/test_phase14_demo.py",
                "phase14_demo.py",
            ],
        },
        "file_repair_attempt_count": 0,
    }

    with patch("app.nodes.repair_planner_node.build_model_gateway") as get_model:
        result = repair_planner_node(state)

    get_model.assert_not_called()
    proposal = result["repair_proposal"]
    assert proposal["kind"] == "manual_only"
    assert proposal["repaired_command"] is None
    assert proposal["steps"][0]["step_type"] == "manual_check"
    assert proposal["steps"][0]["risk"] == "medium"

    route_state = {**state, **result}
    assert route_after_repair_planner(route_state) == (
        "file_repair_planner"
    )


def test_traceback_paths_are_limited_to_existing_repo_python_files(tmp_path):
    repo = tmp_path / "repo"
    test_file = repo / "tests" / "test_demo.py"
    source_file = repo / "demo.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_demo(): pass\n", encoding="utf-8")
    source_file.write_text("def demo(): pass\n", encoding="utf-8")

    traceback = (
        "tests/test_demo.py:5:\n"
        "demo.py:4: RuntimeError\n"
        f'  File "{tmp_path / "outside.py"}", line 9, in run\n'
    )

    assert extract_repo_traceback_paths(
        traceback,
        repo_path=str(repo),
    ) == [
        "tests/test_demo.py",
        "demo.py",
    ]


def test_log_debug_merges_traceback_paths_with_model_related_files(
    tmp_path,
    run_state,
    monkeypatch,
):
    repo = tmp_path / "repo"
    test_file = repo / "tests" / "test_demo.py"
    source_file = repo / "demo.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_demo(): pass\n", encoding="utf-8")
    source_file.write_text("def demo(): pass\n", encoding="utf-8")

    log_path = tmp_path / "execution.log"
    log_path.write_text(
        "Traceback (most recent call last):\n"
        "tests/test_demo.py:5:\n"
        "demo.py:4: RuntimeError: shape mismatch\n",
        encoding="utf-8",
    )
    invocation = StructuredInvocationResult(
        value=DebugReport(
            error_type="shape_mismatch",
            most_likely_causes=[],
            related_files=["tests/test_demo.py"],
            check_order=[],
            suggested_fixes=[],
            risks=[],
            unresolved_questions=[],
        ),
        attempts=[],
        method="json_schema",
        strict=True,
        max_retries=2,
    )
    gateway = ScriptedModelGateway([invocation])
    with patch(
        "app.nodes.log_debug_node.build_model_gateway",
        return_value=gateway,
    ):
        result = log_debug_node(
            {
                **run_state,
                "log_path": str(log_path),
                "repo_path": str(repo),
            }
        )

    assert result["debug_report"]["related_files"] == [
        "tests/test_demo.py",
        "demo.py",
    ]
