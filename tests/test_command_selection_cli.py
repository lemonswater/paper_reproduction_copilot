from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer

from app.main import resume_command_selection
from app.nodes.command_selection_node import (
    build_command_selection_template,
    compute_run_commands_hash,
)


class FakeGraph:
    def __init__(self, values: dict, next_nodes: tuple[str, ...] = ("command_selection",)):
        self.snapshot = SimpleNamespace(values=values, next=next_nodes)
        self.invocations: list[tuple[object, dict]] = []

    def get_state(self, config: dict) -> SimpleNamespace:
        return self.snapshot

    def invoke(self, command: object, config: dict) -> dict:
        self.invocations.append((command, config))
        return {"final_status": "paused_or_finished"}


def test_resume_command_selection_loads_generated_input(tmp_path) -> None:
    run_dir = tmp_path / "run-001"
    input_path = run_dir / "planning" / "command_selection_input.json"
    input_path.parent.mkdir(parents=True)
    run_commands = [
        {
            "command": "python eval.py",
            "cwd": "/repo",
            "source": "script",
            "risk_level": "medium",
            "reason": "run eval",
        },
        {
            "command": "python eval.py --help",
            "cwd": "/repo",
            "source": "script",
            "risk_level": "medium",
            "reason": "show help",
        },
    ]
    payload = {
        "run_commands_hash": compute_run_commands_hash(run_commands),
        "selected_index": 1,
        "edits": [
            {"index": 1, "command": "python eval.py --help"},
        ],
    }
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    graph = FakeGraph(
        {"run_dir": str(run_dir), "run_commands": run_commands}
    )

    with patch("app.main.build_graph", return_value=graph), patch("app.main.print"):
        resume_command_selection(
            thread_id="thread-001",
            selected_index=None,
            input=None,
        )

    assert len(graph.invocations) == 1
    command, config = graph.invocations[0]
    assert command.resume == payload
    assert config == {"configurable": {"thread_id": "thread-001"}}


def test_resume_command_selection_generates_missing_input_before_resume(
    tmp_path,
) -> None:
    run_dir = tmp_path / "run-002"
    run_commands = [
        {
            "command": "python train.py --help",
            "cwd": "/repo",
            "source": "script",
            "risk_level": "medium",
            "reason": "test command",
        }
    ]
    graph = FakeGraph(
        {
            "run_dir": str(run_dir),
            "run_commands": run_commands,
        }
    )

    with patch("app.main.build_graph", return_value=graph), patch("app.main.print"):
        resume_command_selection(
            thread_id="thread-002",
            selected_index=None,
            input=None,
        )

    input_path = run_dir / "planning" / "command_selection_input.json"
    assert json.loads(input_path.read_text(encoding="utf-8")) == {
        "run_commands_hash": compute_run_commands_hash(run_commands),
        "selected_index": 0,
        "edits": [
            {"index": 0, "command": "python train.py --help"},
        ],
    }
    assert graph.invocations == []


def test_resume_command_selection_refreshes_stale_generated_input(
    tmp_path,
) -> None:
    run_dir = tmp_path / "run-stale"
    input_path = run_dir / "planning" / "command_selection_input.json"
    input_path.parent.mkdir(parents=True)
    old_commands = [
        {
            "command": "python old.py",
            "cwd": "/repo",
            "source": "script",
            "risk_level": "medium",
            "reason": "old command",
        }
    ]
    current_commands = [
        *old_commands,
        {
            "command": "python current.py",
            "cwd": "/repo",
            "source": "script",
            "risk_level": "medium",
            "reason": "current command",
        },
    ]
    # 模拟升级前的旧输入文件：有人工编辑，但还没有 run_commands_hash。
    old_payload = {
        "selected_index": 0,
        "edits": [{"index": 0, "command": "python old.py --help"}],
    }
    input_path.write_text(json.dumps(old_payload), encoding="utf-8")
    graph = FakeGraph(
        {"run_dir": str(run_dir), "run_commands": current_commands}
    )

    with patch("app.main.build_graph", return_value=graph), patch("app.main.print"):
        resume_command_selection(
            thread_id="thread-stale",
            selected_index=None,
            input=None,
        )

    assert json.loads(input_path.read_text(encoding="utf-8")) == (
        build_command_selection_template(current_commands)
    )
    backups = list(input_path.parent.glob("command_selection_input.stale-*.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8")) == old_payload
    assert graph.invocations == []


def test_resume_command_selection_rejects_stale_explicit_input(
    tmp_path,
) -> None:
    run_dir = tmp_path / "run-explicit"
    current_commands = [
        {
            "command": "python current.py",
            "cwd": "/repo",
            "source": "script",
            "risk_level": "medium",
            "reason": "current command",
        }
    ]
    stale_input = tmp_path / "stale.json"
    stale_input.write_text(
        json.dumps(build_command_selection_template([])),
        encoding="utf-8",
    )
    graph = FakeGraph(
        {"run_dir": str(run_dir), "run_commands": current_commands}
    )

    with patch("app.main.build_graph", return_value=graph), patch("app.main.print"):
        with pytest.raises(typer.BadParameter, match="命令选择输入已经过期"):
            resume_command_selection(
                thread_id="thread-explicit",
                selected_index=None,
                input=str(stale_input),
            )

    assert graph.invocations == []


def test_resume_command_selection_rejects_wrong_interrupt(tmp_path) -> None:
    graph = FakeGraph(
        {"run_dir": str(tmp_path / "run-003")},
        next_nodes=("human_review",),
    )

    with patch("app.main.build_graph", return_value=graph), patch("app.main.print"):
        with pytest.raises(
            typer.BadParameter,
            match="当前未在 command_selection 节点等待",
        ):
            resume_command_selection(
                thread_id="thread-003",
                selected_index=0,
                input=None,
            )

    assert graph.invocations == []
