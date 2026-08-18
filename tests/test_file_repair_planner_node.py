from __future__ import annotations

from unittest.mock import patch

from app.config import settings
from app.nodes.file_repair_planner_node import file_repair_planner_node
from app.schemas import FileRepairProposal
from app.tools.structured_output_tools import StructuredInvocationResult
from tests.helpers.model_routing import ScriptedModelGateway


def _make_state(tmp_path) -> tuple[dict, str, str]:
    repo = tmp_path / "repo"
    test_file = repo / "tests" / "test_phase14_demo.py"
    source_file = repo / "phase14_demo.py"
    test_file.parent.mkdir(parents=True)

    source_text = (
        "def add(left, right):\n"
        '    raise RuntimeError("shape mismatch")\n'
    )
    test_text = (
        "from phase14_demo import add\n\n"
        "def test_add_returns_sum():\n"
        "    assert add(2, 3) == 5\n"
    )
    source_file.write_text(source_text, encoding="utf-8")
    test_file.write_text(test_text, encoding="utf-8")

    log_path = tmp_path / "execution.log"
    log_path.write_text(
        "Traceback (most recent call last):\n"
        "tests/test_phase14_demo.py:4:\n"
        "phase14_demo.py:2: RuntimeError: shape mismatch\n",
        encoding="utf-8",
    )

    state = {
        "repo_path": str(repo),
        "log_path": str(log_path),
        "debug_report": {
            "error_type": "shape_mismatch",
            "related_files": [
                "tests/test_phase14_demo.py",
                "phase14_demo.py",
            ],
        },
        "pending_action": {
            "program": "python",
            "args": [
                "-m",
                "pytest",
                "-q",
                "tests/test_phase14_demo.py",
            ],
        },
        "file_repair_attempt_count": 0,
        "output_files": [],
    }
    return state, source_text, test_text


def _invocation(proposal: FileRepairProposal) -> StructuredInvocationResult:
    return StructuredInvocationResult(
        value=proposal,
        attempts=[],
        method="json_schema",
        strict=True,
        max_retries=2,
    )


def test_file_repair_adds_pytest_target_from_pending_action(
    tmp_path,
    run_state,
    monkeypatch,
):
    state, source_text, _ = _make_state(tmp_path)
    state = {**run_state, **state}
    proposal = FileRepairProposal(
        kind="patch",
        summary="replace controlled failure",
        root_cause="source always raises",
        edits=[
            {
                "relative_path": "phase14_demo.py",
                "reason": "restore expected behavior",
                "replacements": [
                    {
                        "old_text": source_text,
                        "new_text": (
                            "def add(left, right):\n"
                            "    return left + right\n"
                        ),
                        "reason": "implement the tested contract",
                    }
                ],
            }
        ],
        verification_targets=[],
        risks=[],
        bounded=True,
    )
    monkeypatch.setattr(settings, "enable_file_repair", True)
    monkeypatch.setattr(settings, "max_file_repair_attempts", 1)

    gateway = ScriptedModelGateway([_invocation(proposal)])
    with patch(
        "app.nodes.file_repair_planner_node.build_model_gateway",
        return_value=gateway,
    ):
        result = file_repair_planner_node(state)

    assert result["file_repair_proposal"]["kind"] == "patch"
    assert result["file_repair_proposal"]["verification_targets"] == [
        "tests/test_phase14_demo.py"
    ]


def test_file_repair_rejects_test_file_edit(
    tmp_path,
    run_state,
    monkeypatch,
):
    state, _, test_text = _make_state(tmp_path)
    state = {**run_state, **state}
    proposal = FileRepairProposal(
        kind="patch",
        summary="weaken test",
        root_cause="test currently fails",
        edits=[
            {
                "relative_path": "tests/test_phase14_demo.py",
                "reason": "make test pass",
                "replacements": [
                    {
                        "old_text": test_text,
                        "new_text": "def test_add_returns_sum():\n    pass\n",
                        "reason": "remove assertion",
                    }
                ],
            }
        ],
        verification_targets=["tests/test_phase14_demo.py"],
        risks=[],
        bounded=True,
    )
    monkeypatch.setattr(settings, "enable_file_repair", True)
    monkeypatch.setattr(settings, "max_file_repair_attempts", 1)

    gateway = ScriptedModelGateway([_invocation(proposal)])
    with patch(
        "app.nodes.file_repair_planner_node.build_model_gateway",
        return_value=gateway,
    ):
        result = file_repair_planner_node(state)

    assert result["file_repair_proposal"]["kind"] == "no_patch"
    assert result["file_repair_proposal"]["edits"] == []
    assert "测试" in result["file_repair_proposal"]["summary"]
