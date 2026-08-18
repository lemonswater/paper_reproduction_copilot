"""命令选择领域模块：纯内存 hash、编辑规范化、索引校验。

不访问数据库、不读取 checkpoint、不调用 LLM，也不执行命令。
同时被 Interaction 层和 Graph 节点复用。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from copy import deepcopy
from typing import Any

from app.schemas import (
    MAX_COMMAND_EDIT_CHARS,
    MAX_COMMAND_SELECTION_EDITS,
    CommandEdit,
    CommandSelectionResponse,
)


class CommandSelectionValidationError(ValueError):
    """用户提交的选择或编辑不满足命令选择领域约束。"""


class StaleCommandSelectionError(
    CommandSelectionValidationError
):
    """请求绑定的候选命令列表已经不是当前列表。"""


class CommandSelectionIntegrityError(
    CommandSelectionValidationError
):
    """服务端 interrupt preview 自身不完整或 hash 不自洽。"""


RUN_COMMANDS_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def compute_run_commands_hash(
    run_commands: list[dict[str, Any]],
) -> str:
    """计算键顺序无关、列表顺序敏感的稳定 SHA-256。"""

    canonical_json = json.dumps(
        run_commands,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()


def _validated_command_text(
    command: str,
    *,
    index: int,
) -> str:
    """返回规范化命令，但不在这里判断命令风险。"""

    normalized = command.strip()
    if not normalized:
        raise CommandSelectionValidationError(
            f"修改后的命令不能为空：index={index}"
        )
    if len(normalized) > MAX_COMMAND_EDIT_CHARS:
        raise CommandSelectionValidationError(
            "修改后的命令过长："
            f"index={index}, max={MAX_COMMAND_EDIT_CHARS}"
        )

    # NUL、换行和其他 ASCII 控制字符会让显示、shlex 和审计内容产生歧义。
    if any(
        ord(character) < 32 or ord(character) == 127
        for character in normalized
    ):
        raise CommandSelectionValidationError(
            f"修改后的命令包含控制字符：index={index}"
        )
    return normalized


def normalize_command_edits(
    edits: list[CommandEdit],
    *,
    command_count: int,
) -> list[CommandEdit]:
    """校验索引唯一性和范围，并返回规范化的新对象。"""

    if command_count < 1:
        raise CommandSelectionIntegrityError(
            "当前 command_selection 没有候选命令"
        )
    if len(edits) > MAX_COMMAND_SELECTION_EDITS:
        raise CommandSelectionValidationError(
            "一次 decision 的命令编辑数量过多"
        )

    seen: set[int] = set()
    normalized: list[CommandEdit] = []
    for edit in edits:
        if edit.index in seen:
            raise CommandSelectionValidationError(
                f"命令编辑索引重复：{edit.index}"
            )
        seen.add(edit.index)

        if edit.index >= command_count:
            raise CommandSelectionValidationError(
                f"修改索引超出范围：{edit.index}"
            )
        normalized.append(
            CommandEdit(
                index=edit.index,
                command=_validated_command_text(
                    edit.command,
                    index=edit.index,
                ),
            )
        )
    return normalized


def validate_command_selection_response(
    *,
    run_commands: list[dict[str, Any]],
    response: CommandSelectionResponse,
    expected_preview_hash: str | None = None,
) -> CommandSelectionResponse:
    """把 response 绑定到当前候选列表并返回规范化结果。"""

    if not run_commands:
        raise CommandSelectionIntegrityError(
            "当前 command_selection 没有候选命令"
        )
    for index, item in enumerate(run_commands):
        if not isinstance(item, dict):
            raise CommandSelectionIntegrityError(
                f"候选命令不是对象：index={index}"
            )
        if not isinstance(item.get("command"), str):
            raise CommandSelectionIntegrityError(
                f"候选命令缺少 command：index={index}"
            )

    current_hash = compute_run_commands_hash(run_commands)
    if (
        expected_preview_hash is not None
        and not RUN_COMMANDS_HASH_PATTERN.fullmatch(
            expected_preview_hash
        )
    ):
        raise CommandSelectionIntegrityError(
            "interrupt preview 的 run_commands_hash 格式无效"
        )
    if (
        expected_preview_hash is not None
        and not hmac.compare_digest(
            expected_preview_hash,
            current_hash,
        )
    ):
        raise CommandSelectionIntegrityError(
            "interrupt preview 的 run_commands_hash 与内容不一致"
        )

    if not RUN_COMMANDS_HASH_PATTERN.fullmatch(
        response.run_commands_hash
    ):
        raise StaleCommandSelectionError(
            "命令选择已经过期：run_commands_hash 格式无效"
        )
    if not hmac.compare_digest(
        response.run_commands_hash,
        current_hash,
    ):
        raise StaleCommandSelectionError(
            "命令选择已经过期：run_commands_hash 不匹配"
        )

    if response.selected_index >= len(run_commands):
        raise CommandSelectionValidationError(
            "selected_index 超出范围："
            f"{response.selected_index}"
        )

    normalized_edits = normalize_command_edits(
        response.edits,
        command_count=len(run_commands),
    )
    return response.model_copy(
        update={
            "edits": normalized_edits,
            "run_commands_hash": current_hash,
        }
    )


def apply_command_edits(
    run_commands: list[dict[str, Any]],
    edits: list[CommandEdit],
) -> list[dict[str, Any]]:
    """纯函数：复制候选列表，并只替换允许修改的 command 字段。"""

    normalized_edits = normalize_command_edits(
        edits,
        command_count=len(run_commands),
    )
    effective_commands = deepcopy(run_commands)
    for edit in normalized_edits:
        effective_commands[edit.index]["command"] = (
            edit.command
        )
    return effective_commands
