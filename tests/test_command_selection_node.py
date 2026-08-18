from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.nodes.action_builder_node import action_builder_node
from app.nodes.command_selection_node import (
    build_command_selection_template,
    command_selection_node,
    command_selection_prepare_node,
    compute_run_commands_hash,
)


def _prepare(state: dict, run_state: dict) -> dict:
    working_state = {**run_state, **state}
    working_state.update(command_selection_prepare_node(working_state))
    return working_state


def test_command_selection_selects_index_without_edits(run_state) -> None:

    state = {
        "run_commands": [
            {
                "command": "python a.py",
                "cwd": "/repo",
                "source": "script",
                "risk_level": "medium",
                "reason": "run a",
            },
            {
                "command": "python b.py",
                "cwd": "/repo",
                "source": "script",
                "risk_level": "medium",
                "reason": "run b",
            },
        ],
    }
    state = _prepare(state, run_state)
    run_commands_hash = compute_run_commands_hash(state["run_commands"])
    input_record = next(
        record
        for record in state["artifact_records"]
        if record["relative_path"]
        == "planning/command_selection_input.json"
    )
    assert input_record["run_id"] == run_state["run_id"]
    assert state["command_selection_input_path"] == (
        input_record["absolute_path"]
    )

    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value={
            "run_commands_hash": run_commands_hash,
            "selected_index": 1,
            "edits": [],
        },
    ), patch("app.nodes.command_selection_node.print"):
        result = command_selection_node(state)

    assert result["selected_run_command_index"] == 1
    assert result["edited_run_commands"][1]["command"] == "python b.py"
    assert result["command_selection_record"]["selected_index"] == 1

    input_path = Path(state["command_selection_input_path"])
    assert input_path.exists()
    assert json.loads(input_path.read_text(encoding="utf-8")) == {
        "run_commands_hash": run_commands_hash,
        "selected_index": 0,
        "edits": [
            {"index": 0, "command": "python a.py"},
            {"index": 1, "command": "python b.py"},
        ],
    }
    assert str(input_path) in result["output_files"]
    expected_records = {
        "planning/command_selection_input.json",
        "planning/command_selection_record.json",
        "planning/effective_run_commands.json",
    }
    selected_records = [
        record
        for record in result["artifact_records"]
        if record["relative_path"] in expected_records
    ]
    assert {
        record["relative_path"] for record in selected_records
    } == expected_records
    assert all(
        record["run_id"] == run_state["run_id"]
        for record in selected_records
    )
    assert all(
        Path(run_state["run_dir"])
        in Path(record["absolute_path"]).parents
        for record in selected_records
    )


def test_command_selection_applies_multiple_command_edits(run_state) -> None:

    state = {
        "run_commands": [
            {
                "command": "python train-ntu60.py --dataset_path <path>",
                "cwd": "/repo",
                "source": "script",
                "risk_level": "high",
                "reason": "train ntu",
            },
            {
                "command": "python setup.py install",
                "cwd": "/repo/modules",
                "source": "inferred",
                "risk_level": "medium",
                "reason": "build extension",
            },
        ],
    }
    state = _prepare(state, run_state)
    run_commands_hash = compute_run_commands_hash(state["run_commands"])

    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value={
            "run_commands_hash": run_commands_hash,
            "selected_index": 0,
            "edits": [
                {
                    "index": 0,
                    "command": "python train-ntu60.py --dataset_path /data/ntu60 --batch_size 8",
                },
                {
                    "index": 1,
                    "command": "python setup.py install",
                },
            ],
        },
    ), patch("app.nodes.command_selection_node.print"):
        result = command_selection_node(state)

    assert result["selected_run_command_index"] == 0
    assert (
        result["edited_run_commands"][0]["command"]
        == "python train-ntu60.py --dataset_path /data/ntu60 --batch_size 8"
    )
    assert len(result["command_selection_record"]["edits"]) == 2


def test_command_selection_does_not_overwrite_edited_input(
    run_state,
) -> None:
    state = {
        "run_commands": [
            {
                "command": "python train.py --epochs 100",
                "cwd": "/repo",
                "source": "script",
                "risk_level": "medium",
                "reason": "run training",
            }
        ],
    }
    state = _prepare(state, run_state)
    input_path = Path(state["command_selection_input_path"])
    edited_payload = {
        "run_commands_hash": compute_run_commands_hash(state["run_commands"]),
        "selected_index": 0,
        "edits": [
            {"index": 0, "command": "python train.py --epochs 1"},
        ],
    }
    input_path.write_text(
        json.dumps(edited_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value=edited_payload,
    ), patch("app.nodes.command_selection_node.print"):
        result = command_selection_node(state)

    assert json.loads(input_path.read_text(encoding="utf-8")) == edited_payload
    assert (
        result["edited_run_commands"][0]["command"]
        == "python train.py --epochs 1"
    )


def test_command_selection_clears_stale_execution_state(
    run_state,
) -> None:
    state = {
        "run_commands": [
            {
                "command": "python train.py",
                "cwd": "/repo",
                "source": "script",
                "risk_level": "medium",
                "reason": "run training",
            }
        ],
        "pending_action": {"action_id": "stale-action"},
        "pending_action_hash": "stale-hash",
        "requires_approval": True,
        "user_approval": "approved",
        "approval_record": {"approval_id": "stale-approval"},
        "preflight_report": {"ready_to_execute": True},
        "preflight_passed": True,
        "execution_result": {"ok": True},
        "final_status": "succeeded",
    }
    state = _prepare(state, run_state)
    run_commands_hash = compute_run_commands_hash(state["run_commands"])

    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value={
            "run_commands_hash": run_commands_hash,
            "selected_index": 0,
            "edits": [
                {"index": 0, "command": "python train.py --help"},
            ],
        },
    ), patch("app.nodes.command_selection_node.print"):
        result = command_selection_node(state)

    assert result["pending_action"] is None
    assert result["pending_action_hash"] is None
    assert result["approval_record"] is None
    assert result["preflight_report"] is None
    assert result["preflight_passed"] is False
    assert result["execution_result"] == {}
    assert result["final_status"] is None


def test_command_selection_refreshes_stale_input_and_keeps_backup(
    run_state,
) -> None:
    old_commands = [
        {
            "command": "python old.py",
            "cwd": "/repo",
            "source": "script",
            "risk_level": "medium",
            "reason": "old command",
        }
    ]
    new_commands = [
        *old_commands,
        {
            "command": "python new.py",
            "cwd": "/repo",
            "source": "script",
            "risk_level": "medium",
            "reason": "new command",
        },
    ]
    state = _prepare({"run_commands": old_commands}, run_state)
    input_path = Path(state["command_selection_input_path"])
    old_payload = build_command_selection_template(old_commands)
    old_payload["edits"][0]["command"] = "python old.py --help"
    input_path.write_text(json.dumps(old_payload), encoding="utf-8")

    state["run_commands"] = new_commands
    state.update(command_selection_prepare_node(state))
    response = build_command_selection_template(new_commands)
    response["selected_index"] = 1
    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value=response,
    ), patch("app.nodes.command_selection_node.print"):
        result = command_selection_node(state)

    assert result["selected_run_command_index"] == 1
    assert json.loads(input_path.read_text(encoding="utf-8")) == (
        build_command_selection_template(new_commands)
    )
    backups = list(
        input_path.parent.glob("command_selection_input.stale-*.json")
    )
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8")) == old_payload


def test_command_selection_rejects_stale_response_hash(
    run_state,
) -> None:
    current_commands = [
        {
            "command": "python current.py",
            "cwd": "/repo",
            "source": "script",
            "risk_level": "medium",
            "reason": "current command",
        }
    ]
    stale_response = {
        "run_commands_hash": compute_run_commands_hash([]),
        "selected_index": 0,
        "edits": [],
    }
    state = _prepare(
        {"run_commands": current_commands},
        run_state,
    )

    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value=stale_response,
    ), patch("app.nodes.command_selection_node.print"):
        with pytest.raises(ValueError, match="命令选择已经过期"):
            command_selection_node(
                state
            )


def test_action_builder_uses_selected_index_from_edited_run_commands(
    tmp_path,
) -> None:
    from app.schemas import ExecutionProfile

    repo = tmp_path / "repo"
    modules = repo / "modules"
    modules.mkdir(parents=True)
    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(repo),
        artifact_root=str(tmp_path / "runs"),
        writable_roots=[str(repo)],
    )
    state = {
        "execution_profile_id": profile.profile_id,
        "repo_path": str(repo),
        "selected_run_command_index": 1,
        "edited_run_commands": [
            {
                "command": "python train.py --dataset_path /data/demo",
                "cwd": str(repo),
                "source": "script",
                "reason": "train model",
            },
            {
                "command": "python setup.py install",
                "cwd": str(modules),
                "source": "inferred",
                "reason": "build extension",
            },
        ],
    }

    with patch(
        "app.nodes.action_builder_node.get_execution_profile",
        return_value=profile,
    ):
        result = action_builder_node(state)

    assert result["pending_action"]["program"] == "python"
    assert result["pending_action"]["args"] == ["setup.py", "install"]
    assert result["pending_action"]["cwd"] == str(modules)
    assert result["pending_action_hash"]
