from copy import deepcopy
import shlex
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
        return False, "empty repaired_command"

    if any(marker in stripped for marker in UNSUPPORTED_REPAIR_SHELL_MARKERS):
        return False, "repaired_command contains unsupported shell syntax"

    try:
        tokens = shlex.split(stripped)
    except ValueError as exc:
        return False, f"invalid repaired_command quoting: {exc}"

    if not tokens:
        return False, "empty repaired_command after shlex parsing"

    if tokens[0] in BLOCKED_REPAIR_PROGRAMS:
        return False, f"repaired_command uses blocked program: {tokens[0]}"

    return True, "ok"

def render_repair_proposal_md(proposal: dict[str, Any]) -> str:
    lines = ["# Repair Proposal", ""]

    lines += [
        "## Summary",
        "",
        f"- Proposal ID: `{proposal.get('proposal_id', 'N/A')}`",
        f"- Error Type: `{proposal.get('source_error_type', 'unknown')}`",
        f"- Kind: `{proposal.get('kind', 'unknown')}`",
        f"- Bounded: `{proposal.get('bounded', False)}`",
        f"- Summary: {proposal.get('summary', 'N/A')}",
        f"- Root Cause: {proposal.get('root_cause', 'N/A')}",
        "",
    ]

    repaired_command = proposal.get("repaired_command")
    lines += ["## Repaired Command", ""]
    if repaired_command:
        lines.append(f"- `{repaired_command}`")
    else:
        lines.append("- None")
    lines.append("")

    sections = [
        ("Changed Arguments", proposal.get("changed_arguments", [])),
        ("Verification Steps", proposal.get("verification_steps", [])),
        ("Rollback Steps", proposal.get("rollback_steps", [])),
        ("Risks", proposal.get("risks", [])),
    ]
    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("- None")
        else:
            for item in items:
                lines.append(f"- {item}")
        lines.append("")

    steps = proposal.get("steps", [])
    lines += ["## Steps", ""]
    if not steps:
        lines.append("- None")
        lines.append("")
    else:
        for step in steps:
            lines.append(
                f"- `{step.get('step_type', 'unknown')}` on `{step.get('target', '')}`: {step.get('change', '')}"
            )
            lines.append(f"  reason: {step.get('reason', '')}")
            lines.append(f"  risk: `{step.get('risk', 'unknown')}`")
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
        raise ValueError("cannot apply repair: no effective run commands found")

    if selected_index is None or selected_index < 0 or selected_index >= len(effective_commands):
        raise ValueError(f"selected_run_command_index out of range: {selected_index}")

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
            "cannot apply repair: execution profile mismatch between state "
            "and pending_action"
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
    reason = target_command.get("reason", "repair proposal generated command")

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
