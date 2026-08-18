from __future__ import annotations

import pytest

from app.command_selection import (
    CommandSelectionIntegrityError,
    CommandSelectionValidationError,
    StaleCommandSelectionError,
    apply_command_edits,
    compute_run_commands_hash,
    validate_command_selection_response,
)
from app.schemas import (
    CommandEdit,
    CommandSelectionResponse,
)

RUN_COMMANDS = [
    {
        "command": "python train.py --dataset_path <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "high",
        "reason": "main training entry",
    },
    {
        "command": "python test.py --checkpoint <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "medium",
        "reason": "evaluation entry",
    },
]


def _response(
    *,
    selected_index: int = 0,
    edits: list[CommandEdit] | None = None,
    run_commands_hash: str | None = None,
) -> CommandSelectionResponse:
    return CommandSelectionResponse(
        selected_index=selected_index,
        edits=edits or [],
        run_commands_hash=(
            run_commands_hash
            or compute_run_commands_hash(RUN_COMMANDS)
        ),
    )


def test_hash_ignores_dict_key_order_but_keeps_list_order():
    reordered_keys = [
        dict(reversed(list(item.items())))
        for item in RUN_COMMANDS
    ]

    assert compute_run_commands_hash(
        reordered_keys
    ) == compute_run_commands_hash(RUN_COMMANDS)
    assert compute_run_commands_hash(
        list(reversed(RUN_COMMANDS))
    ) != compute_run_commands_hash(RUN_COMMANDS)


def test_validates_normalizes_and_applies_multiple_edits():
    response = _response(
        selected_index=1,
        edits=[
            CommandEdit(
                index=0,
                command=(
                    "  python train.py "
                    "--dataset_path /data/ntu60  "
                ),
            ),
            CommandEdit(
                index=1,
                command=(
                    "python test.py --checkpoint "
                    "/data/best.pth"
                ),
            ),
        ],
    )

    normalized = validate_command_selection_response(
        run_commands=RUN_COMMANDS,
        response=response,
        expected_preview_hash=(
            compute_run_commands_hash(RUN_COMMANDS)
        ),
    )
    effective = apply_command_edits(
        RUN_COMMANDS,
        normalized.edits,
    )

    assert normalized.selected_index == 1
    assert normalized.edits[0].command.startswith("python")
    assert effective[0]["command"].endswith("/data/ntu60")
    assert effective[1]["cwd"] == RUN_COMMANDS[1]["cwd"]
    # 纯函数不能反向修改模型生成的原候选列表。
    assert RUN_COMMANDS[0]["command"].endswith("<path>")


def test_rejects_stale_request_hash():
    with pytest.raises(
        StaleCommandSelectionError,
        match="过期",
    ):
        validate_command_selection_response(
            run_commands=RUN_COMMANDS,
            response=_response(
                run_commands_hash="0" * 64
            ),
            expected_preview_hash=(
                compute_run_commands_hash(RUN_COMMANDS)
            ),
        )


def test_rejects_inconsistent_server_preview_hash():
    with pytest.raises(
        CommandSelectionIntegrityError,
        match="preview",
    ):
        validate_command_selection_response(
            run_commands=RUN_COMMANDS,
            response=_response(),
            expected_preview_hash="f" * 64,
        )


@pytest.mark.parametrize(
    ("selected_index", "edits", "message"),
    [
        (2, [], "selected_index"),
        (
            0,
            [CommandEdit(index=2, command="python x.py")],
            "修改索引",
        ),
        (
            0,
            [CommandEdit(index=0, command="   ")],
            "不能为空",
        ),
        (
            0,
            [
                CommandEdit(
                    index=0,
                    command="python x.py\nrm -rf x",
                )
            ],
            "控制字符",
        ),
    ],
)
def test_rejects_invalid_selection_semantics(
    selected_index,
    edits,
    message,
):
    with pytest.raises(
        CommandSelectionValidationError,
        match=message,
    ):
        validate_command_selection_response(
            run_commands=RUN_COMMANDS,
            response=_response(
                selected_index=selected_index,
                edits=edits,
            ),
        )


def test_duplicate_edit_indexes_are_rejected_by_schema():
    with pytest.raises(ValueError, match="重复"):
        _response(
            edits=[
                CommandEdit(index=0, command="python a.py"),
                CommandEdit(index=0, command="python b.py"),
            ]
        )
