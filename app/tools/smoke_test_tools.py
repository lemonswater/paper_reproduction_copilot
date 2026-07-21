from datetime import datetime, timezone
import shlex
from typing import Any

from app.config import settings
from app.schemas import SmokeTestReport


# 这些是“常见而相对安全”的收缩参数。
# 原则：
# - 只覆盖命令里已存在的 flag
# - 不主动给命令加未知 flag
SMOKE_OVERRIDE_VALUES = {
    "--batch_size": "1",
    "--batch-size": "1",
    "--epochs": "1",
    "--epoch": "1",
    "--max_epochs": "1",
    "--max-epochs": "1",
    "--num_workers": "0",
    "--num-workers": "0",
    "--workers": "0",
    "--max_steps": "1",
    "--max-steps": "1",
    "--train_steps": "1",
    "--train-steps": "1",
    "--limit_train_batches": "1",
    "--limit-val-batches": "1",
    "--limit_val_batches": "1",
}


SUPPORTED_SMOKE_PROGRAMS = {
    "python",
    "torchrun",
    "accelerate",
    "bash",
}

def _set_flag_value(args: list[str], flag: str, new_value: str) -> tuple[list[str], bool]:
    """
    支持两类常见 flag 形式：
    1. --batch_size 16
    2. --batch_size=16
    """
    updated = list(args)
    changed = False

    index = 0
    while index < len(updated):
        token = updated[index]

        if token == flag and index + 1 < len(updated):
            if updated[index + 1] != new_value:
                updated[index + 1] = new_value
                changed = True
            index += 2
            continue

        prefix = f"{flag}="
        if token.startswith(prefix):
            if token != f"{flag}={new_value}":
                updated[index] = f"{flag}={new_value}"
                changed = True

        index += 1

    return updated, changed

def _render_action_preview(action: dict[str, Any]) -> str:
    program = action.get("program", "")
    args = action.get("args", [])
    return " ".join([shlex.quote(program), *[shlex.quote(arg) for arg in args]]).strip()

def derive_smoke_test_action(action: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str]:
    """
    从 full action 派生 smoke action。

    返回：
    - smoke_action：派生出的结构化动作；如果无法安全派生则返回 None
    - overrides：本次实际做了哪些缩减
    - summary：给 node / report 用的人类可读摘要
    """
    program = action.get("program", "")
    args = list(action.get("args", []))

    if program not in SUPPORTED_SMOKE_PROGRAMS:
        return None, [], f"program not supported for smoke reduction: {program}"

    updated_args = list(args)
    overrides: list[str] = []

    for flag, value in SMOKE_OVERRIDE_VALUES.items():
        updated_args, changed = _set_flag_value(updated_args, flag, value)
        if changed:
            overrides.append(f"{flag} -> {value}")

    if not overrides:
        return None, [], "no known safe reductions found in command arguments"

    smoke_action = {
        **action,
        # 给 smoke action 一个新的 action_id，避免和 full action 混淆。
        "action_id": f"{action.get('action_id', 'action')}_smoke",
        "args": updated_args,
        "reason": f"smoke test derived from: {action.get('reason', 'unknown reason')}",
        # smoke timeout 必须明显更短。
        "timeout_seconds": min(
            int(action.get("timeout_seconds", 300)),
            settings.smoke_test_timeout_seconds,
        ),
    }

    return smoke_action, overrides, "derived smoke action with bounded argument reductions"

def build_smoke_test_report(
    *,
    action: dict[str, Any],
    action_hash: str | None,
    status: str,
    summary: str,
    applied_overrides: list[str],
    result: dict[str, Any] | None = None,
    log_path: str | None = None,
) -> SmokeTestReport:
    return SmokeTestReport(
        action_id=action.get("action_id"),
        action_hash=action_hash,
        status=status,  # type: ignore[arg-type]
        summary=summary,
        applied_overrides=applied_overrides,
        command_preview=_render_action_preview(action),
        log_path=log_path,
        result=result or {},
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

def render_smoke_test_report_md(report: SmokeTestReport) -> str:
    lines = ["# Smoke Test Report", ""]

    lines += [
        "## Summary",
        "",
        f"- Action ID: `{report.action_id or 'N/A'}`",
        f"- Action Hash: `{report.action_hash or 'N/A'}`",
        f"- Status: `{report.status}`",
        f"- Summary: {report.summary}",
        f"- Command Preview: `{report.command_preview or 'N/A'}`",
        f"- Log Path: `{report.log_path or 'N/A'}`",
        "",
    ]

    lines += ["## Applied Overrides", ""]
    if not report.applied_overrides:
        lines.append("- None")
    else:
        for item in report.applied_overrides:
            lines.append(f"- {item}")
    lines.append("")

    if report.result:
        lines += [
            "## Result",
            "",
            f"- OK: `{report.result.get('ok')}`",
            f"- Return Code: `{report.result.get('returncode')}`",
            "",
        ]

    return "\n".join(lines)