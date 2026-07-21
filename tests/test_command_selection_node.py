import json
from unittest.mock import patch

import pytest

from app.config import settings
from app.nodes.action_builder_node import action_builder_node
from app.nodes.command_selection_node import (
    build_command_selection_template,
    command_selection_node,
    compute_run_commands_hash,
)


def test_command_selection_selects_index_without_edits(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

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
        "output_files": [],
    }
    run_commands_hash = compute_run_commands_hash(state["run_commands"])

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

    input_path = tmp_path / "command_selection_input.json"
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


def test_command_selection_applies_multiple_command_edits(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

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
        "output_files": [],
    }
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
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

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
        "output_files": [],
    }
    input_path = tmp_path / "command_selection_input.json"
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
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

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
        "output_files": [],
    }
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
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)

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
    input_path = tmp_path / "command_selection_input.json"
    old_payload = build_command_selection_template(old_commands)
    old_payload["edits"][0]["command"] = "python old.py --help"
    input_path.write_text(json.dumps(old_payload), encoding="utf-8")

    response = build_command_selection_template(new_commands)
    response["selected_index"] = 1
    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value=response,
    ), patch("app.nodes.command_selection_node.print"):
        result = command_selection_node(
            {"run_commands": new_commands, "output_files": []}
        )

    assert result["selected_run_command_index"] == 1
    assert json.loads(input_path.read_text(encoding="utf-8")) == (
        build_command_selection_template(new_commands)
    )
    backups = list(tmp_path.glob("command_selection_input.stale-*.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8")) == old_payload


def test_command_selection_rejects_stale_response_hash(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "output_dir", tmp_path)
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

    with patch(
        "app.nodes.command_selection_node.interrupt",
        return_value=stale_response,
    ), patch("app.nodes.command_selection_node.print"):
        with pytest.raises(ValueError, match="stale command selection response"):
            command_selection_node(
                {"run_commands": current_commands, "output_files": []}
            )


def test_action_builder_uses_selected_index_from_edited_run_commands() -> None:
    state = {
        "repo_path": "/repo",
        "selected_run_command_index": 1,
        "edited_run_commands": [
            {
                "command": "python train.py --dataset_path /data/demo",
                "cwd": "/repo",
                "source": "script",
                "reason": "train model",
            },
            {
                "command": "python setup.py install",
                "cwd": "/repo/modules",
                "source": "inferred",
                "reason": "build extension",
            },
        ],
    }

    result = action_builder_node(state)

    assert result["pending_action"]["program"] == "python"
    assert result["pending_action"]["args"] == ["setup.py", "install"]
    assert result["pending_action"]["cwd"] == "/repo/modules"
    assert result["pending_action_hash"]
