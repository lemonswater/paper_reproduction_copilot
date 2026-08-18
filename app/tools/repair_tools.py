from __future__ import annotations

import shlex
from copy import deepcopy
from typing import Any

from app.config import settings
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.tools.action_tools import build_run_action_from_command, compute_action_hash

UNSUPPORTED_REPAIR_SHELL_MARKERS = [
    "&&",
    "||",
    ";",
    "|",
    ">",
    "<",
    "$(",
    "`",
]


BLOCKED_REPAIR_PROGRAMS = {
    "pip",
    "conda",
    "sudo",
    "rm",
    "git",
    "apt",
    "apt-get",
}

def validate_bounded_repair_command(command: str) -> tuple[bool, str]:
    """
    校验 repair proposal 给出的新命令是否仍然在本阶段允许的边界内。
    """
    stripped = command.strip()
    if not stripped:
        return False, "repaired_command 不能为空"

    if any(marker in stripped for marker in UNSUPPORTED_REPAIR_SHELL_MARKERS):
        return False, "repaired_command 包含不支持的 shell 语法"

    try:
        tokens = shlex.split(stripped)
    except ValueError as exc:
        return False, f"repaired_command 的引号无效：{exc}"

    if not tokens:
        return False, "经过 shlex 解析后 repaired_command 为空"

    if tokens[0] in BLOCKED_REPAIR_PROGRAMS:
        return False, f"repaired_command 使用了被阻止的程序：{tokens[0]}"

    return True, "ok"

def render_repair_proposal_md(proposal: dict[str, Any]) -> str:
    lines = ["# 修复建议", ""]

    lines += [
        "## 摘要",
        "",
        f"- 建议 ID：`{proposal.get('proposal_id', '不适用')}`",
        f"- 错误类型：`{proposal.get('source_error_type', 'unknown')}`",
        f"- 类型：`{proposal.get('kind', 'unknown')}`",
        f"- 是否有界：`{proposal.get('bounded', False)}`",
        f"- 摘要：{proposal.get('summary', '不适用')}",
        f"- 根本原因：{proposal.get('root_cause', '不适用')}",
        "",
    ]

    repaired_command = proposal.get("repaired_command")
    lines += ["## 修复后的命令", ""]
    if repaired_command:
        lines.append(f"- `{repaired_command}`")
    else:
        lines.append("- 无")
    lines.append("")

    sections = [
        ("已修改参数", proposal.get("changed_arguments", [])),
        ("验证步骤", proposal.get("verification_steps", [])),
        ("回滚步骤", proposal.get("rollback_steps", [])),
        ("风险", proposal.get("risks", [])),
    ]
    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("- 无")
        else:
            for item in items:
                lines.append(f"- {item}")
        lines.append("")

    steps = proposal.get("steps", [])
    lines += ["## 步骤", ""]
    if not steps:
        lines.append("- 无")
        lines.append("")
    else:
        for step in steps:
            lines.append(
                f"- `{step.get('step_type', 'unknown')}` 作用于 "
                f"`{step.get('target', '')}`：{step.get('change', '')}"
            )
            lines.append(f"  原因：{step.get('reason', '')}")
            lines.append(f"  风险：`{step.get('risk', 'unknown')}`")
        lines.append("")

    return "\n".join(lines)

def apply_command_repair_to_state(state: dict[str, Any], repaired_command: str) -> dict[str, Any]:
    """
    把 bounded repair 作用到当前“被选中的命令”上，并重新生成 pending_action。
    """
    effective_commands = deepcopy(
        state.get("edited_run_commands") or state.get("run_commands") or []
    )
    selected_index = state.get("selected_run_command_index", 0)

    if not effective_commands:
        raise ValueError("无法应用修复：未找到有效的运行命令")

    if selected_index is None or selected_index < 0 or selected_index >= len(effective_commands):
        raise ValueError(f"selected_run_command_index 超出范围：{selected_index}")

    target_command = effective_commands[selected_index]
    target_command["command"] = repaired_command

    previous_action = state.get("pending_action") or {}
    state_profile_id = state.get("execution_profile_id")
    action_profile_id = previous_action.get("execution_profile_id")
    if (
        state_profile_id
        and action_profile_id
        and state_profile_id != action_profile_id
    ):
        raise ValueError(
            "无法应用修复：state 与 pending_action 中的执行环境配置不匹配"
        )

    profile_id = (
        action_profile_id
        or state_profile_id
        or settings.default_execution_profile
    )
    profile = get_execution_profile(profile_id)
    profile_fingerprint = compute_execution_profile_fingerprint(profile)

    cwd = (
        target_command.get("cwd")
        or state.get("repo_path")
        or profile.workspace_root
    )
    source = target_command.get("source", "inferred")
    reason = target_command.get("reason", "由修复建议生成的命令")

    new_action = build_run_action_from_command(
        command=repaired_command,
        cwd=cwd,
        source=source,
        reason=reason,
        timeout_seconds=300,
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint=profile_fingerprint,
    )

    return {
        "execution_profile_id": profile.profile_id,
        "execution_profile_fingerprint": profile_fingerprint,
        "edited_run_commands": effective_commands,
        "pending_action": new_action,
        "pending_action_hash": compute_action_hash(new_action),
    }
