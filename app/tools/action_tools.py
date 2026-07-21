import hashlib
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from app.schemas import ApprovalRecord, ExecutableAction

UNSUPPORTED_SHELL_MARKERS = [
    "&&",
    "||",
    ";",
    "|",
    ">",
    "<",
    "$(",
    "`"
]

PLACEHOLDER_MARKERS = {
    "[需要确认参数]",
    "<需要确认>",
    "<todo>",
    "TODO"
}

def _strip_leading_cd(command: str, cwd: str) -> tuple[str, str]:
    stripped = command.strip()
    if not stripped.startswith("cd "):
        return stripped, cwd
    
    if "&&" not in stripped:
        return stripped, cwd

    left, right = stripped.split("&&", 1)
    left = left.strip()
    right = right.strip()

    try:
        tokens = shlex.split(left)
    except ValueError:
        return stripped, cwd

    if len(tokens) == 2 and tokens[0] == "cd":
        return right, tokens[1]

    return stripped, cwd

def _contains_unsupported_shell_syntax(command: str) -> str:
    return any(marker in command for marker in UNSUPPORTED_SHELL_MARKERS)

def _contains_bracket_placeholder(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    return any(
        token.startswith("[") and token.endswith("]") and len(token) > 2
        for token in tokens
    )

def _contains_placeholder(command: str) -> bool:
    lowered = command.lower()
    return (
        any(marker.lower() in lowered for marker in PLACEHOLDER_MARKERS)
        or _contains_bracket_placeholder(command)
    )

def build_run_action_from_command(
    *,
    command: str,
    cwd: str,
    source: str,
    reason: str,
    timeout_seconds: int = 300,
    execution_profile_id: str,
    execution_profile_fingerprint: str,
) -> dict:
    normalized_command, normalized_cwd = _strip_leading_cd(command, cwd)
    if _contains_unsupported_shell_syntax(normalized_command):
        raise ValueError(
            "运行命令中不支持的 shell 语法，请将其转换为单个可执行命令。"
        )

    if _contains_placeholder(normalized_command):
        raise ValueError(
            "运行命令仍包含未解决的占位符，请勿执行。"
        )

    try:
        tokens = shlex.split(normalized_command)
    except ValueError as exc:
        raise ValueError(f"invalid shell quoting: {exc}") from exc

    if not tokens:
        raise ValueError("empty run command")

    action = ExecutableAction(
        action_id=f"action_{uuid4().hex[:12]}",
        action_type="run_command",
        program=tokens[0],
        args=tokens[1:],
        cwd=str(Path(normalized_cwd)),
        source=source,
        reason=reason,
        timeout_seconds=timeout_seconds,
        writable_paths=[str(Path(normalized_cwd))],
        execution_profile_id=execution_profile_id,
        execution_profile_fingerprint=execution_profile_fingerprint,
    )

    return action.model_dump()

def compute_action_hash(action: dict) -> str:
    material = {
        "action_type": action.get("action_type"),
        "program": action.get("program"),
        "args": action.get("args", []),
        "cwd": action.get("cwd"),
        "env_allowlist": action.get("env_allowlist", {}),
        "timeout_seconds": action.get("timeout_seconds"),
        "writable_paths": action.get("writable_paths", []),

        # 审批必须同时绑定执行环境。
        "execution_profile_id": action.get("execution_profile_id"),
        "execution_profile_fingerprint": action.get(
            "execution_profile_fingerprint"
        ),
    }

    payload = json.dumps(material, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def build_approval_record(
    *,
    action: dict,
    action_hash: str,
    decision: str,
    risk_level: str,
    comment: str | None
) -> dict:
    record = ApprovalRecord(
        approval_id=f"approval_{uuid4().hex[:12]}",
        action_id=action["action_id"],
        action_hash=action_hash,
        decision=decision,
        reviewer="human",
        risk_level=risk_level,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        comment=comment,
    )
    return record.model_dump()
