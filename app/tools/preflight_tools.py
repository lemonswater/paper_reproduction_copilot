import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from app.schemas import ExecutableAction, PreflightItem, PreflightReport
from app.execution.base import ExecutionRunner
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile
)
from app.execution.registry import build_execution_runner

PLACEHOLDER_MARKERS = (
    "<path",
    "<todo>",
    "TODO",
    "[需要确认参数]",
    "<需要确认>",
)

PATH_LIKE_FLAGS = {
    "--dataset_path": "dataset path",
    "--data_root": "data root",
    "--data-dir": "data directory",
    "--config": "config file",
    "--cfg": "config file",
    "--weights": "weights file",
    "--pretrained": "pretrained weights",
    "--checkpoint": "checkpoint file",
    "--ckpt": "checkpoint file",
    "--resume": "checkpoint file",
}

UNSUPPORTED_PREFLIGHT_TEXT_MARKERS = (
    "&&",
    "||",
    ";",
    "|",
    "$(",
    "`",
)

UNSUPPORTED_PREFLIGHT_TOKENS = {"<", ">", ">>", "<<"}

def _resolve_action_runner(action: dict) -> tuple[ExecutionRunner, str]:
    profile_id = action.get("execution_profile_id")
    if not profile_id:
        raise ValueError("缺少 execution_profile_id")
    
    profile = get_execution_profile(profile_id)
    current_fingerprint = compute_execution_profile_fingerprint(profile)
    expected_fingerprint = action.get("execution_profile_fingerprint")
    if expected_fingerprint != current_fingerprint:
        raise ValueError("execution profile fingerprint 不匹配")

    return build_execution_runner(profile), current_fingerprint

def _contains_bracket_placeholder(value: str) -> bool:
    try:
        tokens = shlex.split(value)
    except ValueError:
        tokens = value.split()

    return any(
        token.startswith("[") and token.endswith("]") and len(token) > 2
        for token in tokens
    )

def _contains_placeholder(value: str) -> bool:
    lowered = value.lower()
    return (
        any(marker.lower() in lowered for marker in PLACEHOLDER_MARKERS)
        or _contains_bracket_placeholder(value)
    )

def _strip_leading_cd_for_preflight(command: str, cwd: str) -> tuple[str, str]:
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

def _contains_unsupported_preflight_shell_syntax(command: str) -> bool:
    return any(marker in command for marker in UNSUPPORTED_PREFLIGHT_TEXT_MARKERS)

def _resolve_path(candidate: str, cwd: Path) -> Path:
    path = Path(candidate)
    if path.is_absolute():
        return path
    return (cwd / path).resolve()

def _add_item(
    items: list[PreflightItem],
    *,
    name: str,
    category: str,
    status: str,
    evidence: str,
    recommendation: str | None = None
) -> None:
    items.append(
        PreflightItem(
            name=name,
            category=category,
            status=status,
            evidence=evidence,
            recommendation=recommendation
        )
    )

def _extract_flag_values(args: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}

    index = 0
    while index < len(args):
        token = args[index]

        if token in PATH_LIKE_FLAGS and index + 1 < len(args):
            values[token] = args[index + 1]
            index += 2
            continue

        if token.startswith("--") and "=" in token:
            key, value = token.split("=", 1)
            if key in PATH_LIKE_FLAGS:
                values[key] = value

        index += 1

    return values

def _detect_entry_script(program: str, args: list[str], cwd: Path) -> Path | None:
    if not args:
        return None

    if program == "python":
        first = args[0]
        if first == "-m":
            return None
        if first.startswith("-"):
            return None
        return _resolve_path(first, cwd)

    if program == "bash":
        first = args[0]
        if first.startswith("-"):
            return None
        return _resolve_path(first, cwd)

    return None

def _detect_dependency_files(repo_path: str | None) -> list[Path]:
    if not repo_path:
        return []

    repo_dir = Path(repo_path)
    candidates = [
        repo_dir / "requirements.txt",
        repo_dir / "pyproject.toml",
        repo_dir / "environment.yml",
        repo_dir / "environment.yaml",
    ]
    return [path for path in candidates if path.exists()]

def _run_probe(
    runner: ExecutionRunner,
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 8,
) -> tuple[bool, str]:
    if not command:
        return False, "empty probe command"

    result = runner.probe(
        program=command[0],
        args=command[1:],
        cwd=str(cwd),
        timeout_seconds=timeout_seconds,
    )

    return result["ok"], result["combined_output"]

def build_preflight_action_from_command(
    *,
    command: str,
    cwd: str,
    source: str,
    reason: str,
    timeout_seconds: int = 300,
    execution_profile_id: str,
    execution_profile_fingerprint: str,
) -> dict:
    normalized_command, normalized_cwd = _strip_leading_cd_for_preflight(command, cwd)

    if _contains_unsupported_preflight_shell_syntax(normalized_command):
        raise ValueError(
            "预检命令中不支持的 shell 语法，请将其限制为单个可执行文件调用。"
        )

    try:
        tokens = shlex.split(normalized_command)
    except ValueError as exc:
        raise ValueError(f"invalid shell quoting: {exc}") from exc

    if not tokens:
        raise ValueError("empty preflight command")

    if any(token in UNSUPPORTED_PREFLIGHT_TEXT_MARKERS for token in tokens):
        raise ValueError(
            "预检命令不支持 shell 重定向，请传递具体的参数值。"
        )

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

def collect_static_preflight_items(runner: ExecutionRunner, action: dict, repo_path: str | None) -> list[PreflightItem]:
    items: list[PreflightItem] = []

    program = action.get("program", "")
    args = action.get("args", [])
    cwd = Path(action.get("cwd") or ".")

    if cwd.exists() and cwd.is_dir():
        _add_item(
            items,
            name="working_directory_exists",
            category="static",
            status="passed",
            evidence=f"working directory exists: {cwd}",
        )
    else:
        _add_item(
            items,
            name="working_directory_exists",
            category="static",
            status="failed",
            evidence=f"working directory missing: {cwd}",
            recommendation="请确认 repo_path / cwd 是否正确。",
        )

    if cwd.exists():
        if os.access(cwd, os.W_OK):
            _add_item(
                items,
                name="working_directory_writable",
                category="static",
                status="passed",
                evidence=f"working directory is writable: {cwd}",
            )
        else:
            _add_item(
                items,
                name="working_directory_writable",
                category="static",
                status="failed",
                evidence=f"working directory is not writable: {cwd}",
                recommendation="请确认目录权限，或把动作切到可写目录。",
            )

    resolved_program = runner.which(str(program), str(cwd))
    if resolved_program:
        _add_item(
            items,
            name="program_in_path",
            category="static",
            status="passed",
            evidence=f"program resolved to: {resolved_program}",
        )
    else:
        _add_item(
            items,
            name="program_in_path",
            category="static",
            status="failed",
            evidence=f"program not found in PATH: {program}",
            recommendation="请确认虚拟环境是否激活，或确认命令程序是否已安装。",
        )

    joined = " ".join([program, *args]).strip()
    if _contains_placeholder(joined):
        _add_item(
            items,
            name="command_placeholders_resolved",
            category="static",
            status="failed",
            evidence=f"command still contains placeholders: {joined}",
            recommendation="请把 <path> / TODO / [需要确认参数] 替换成真实值。",
        )
    else:
        _add_item(
            items,
            name="command_placeholders_resolved",
            category="static",
            status="passed",
            evidence="no unresolved placeholders detected in command arguments",
        )

    entry_script = _detect_entry_script(program, args, cwd)
    if entry_script is not None:
        if entry_script.exists():
            _add_item(
                items,
                name="entry_script_exists",
                category="static",
                status="passed",
                evidence=f"entry script exists: {entry_script}",
            )
        else:
            _add_item(
                items,
                name="entry_script_exists",
                category="static",
                status="failed",
                evidence=f"entry script missing: {entry_script}",
                recommendation="请确认命令里的脚本路径是否正确。",
            )

    for flag, raw_value in _extract_flag_values(args).items():
        label = PATH_LIKE_FLAGS[flag]

        if _contains_placeholder(raw_value):
            _add_item(
                items,
                name=f"{flag}_resolved",
                category="static",
                status="failed",
                evidence=f"{label} still contains placeholder: {raw_value}",
                recommendation=f"把 {flag} 替换成真实路径。",
            )
            continue

        target_path = _resolve_path(raw_value, cwd)
        if target_path.exists():
            _add_item(
                items,
                name=f"{flag}_exists",
                category="static",
                status="passed",
                evidence=f"{label} exists: {target_path}",
            )
        else:
            _add_item(
                items,
                name=f"{flag}_exists",
                category="static",
                status="failed",
                evidence=f"{label} missing: {target_path}",
                recommendation=f"请确认 {flag} 指向的路径存在。",
            )

    dependency_files = _detect_dependency_files(repo_path)
    if dependency_files:
        _add_item(
            items,
            name="dependency_manifest_detected",
            category="static",
            status="passed",
            evidence="detected dependency files: "
            + ", ".join(str(path.name) for path in dependency_files),
        )
    else:
        _add_item(
            items,
            name="dependency_manifest_detected",
            category="static",
            status="warning",
            evidence="no requirements.txt / pyproject.toml / environment.yml detected",
            recommendation="后续可以从 README 或安装脚本中补充依赖来源。",
        )

    return items

def collect_runtime_preflight_items(action: dict, runner: ExecutionRunner) -> list[PreflightItem]:
    items: list[PreflightItem] = []

    program = action.get("program", "")
    cwd = Path(action.get("cwd") or ".")

    if not runner.which(str(program), str(cwd)):
        return items

    if program == "python":
        ok, evidence = _run_probe(
            runner,
            ["python", "--version"],
            cwd=cwd
        )
        _add_item(
            items,
            name="python_version_probe",
            category="runtime",
            status="passed" if ok else "failed",
            evidence=evidence,
            recommendation=None if ok else "确认 python 可执行程序是否可用。",
        )

        ok, evidence = _run_probe(
            runner,
            ["python", "-c", "import torch; print(torch.__version__)"],
            cwd=cwd,
        )
        _add_item(
            items,
            name="torch_import_probe",
            category="runtime",
            status="passed" if ok else "failed",
            evidence=evidence,
            recommendation=None if ok else "确认当前环境已安装可导入的 PyTorch。",
        )

        ok, evidence = _run_probe(
            runner,
            ["python", "-c", "import torch; print(torch.cuda.is_available())"],
            cwd=cwd,
        )
        _add_item(
            items,
            name="cuda_available_probe",
            category="runtime",
            status="passed" if ok else "warning",
            evidence=evidence,
            recommendation=None if ok else "如果需要 GPU，请检查 CUDA / 驱动 / PyTorch 兼容性。",
        )

    elif program == "torchrun":
        ok, evidence = _run_probe(runner, ["torchrun", "--help"], cwd=cwd)
        _add_item(
            items,
            name="torchrun_help_probe",
            category="runtime",
            status="passed" if ok else "failed",
            evidence=evidence,
            recommendation=None if ok else "确认 torchrun 是否在当前环境中可用。",
        )

    else:
        ok, evidence = _run_probe(runner, [program, "--help"], cwd=cwd)
        _add_item(
            items,
            name="program_help_probe",
            category="runtime",
            status="passed" if ok else "warning",
            evidence=evidence,
            recommendation=None if ok else "确认该命令在当前环境中可执行。",
        )

    return items

def build_preflight_report(
    action: dict,
    *,
    repo_path: str | None = None,
    action_hash: str | None = None,
) -> PreflightReport:
    try:
        runner, _ = _resolve_action_runner(action)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        item = PreflightItem(
            name="execution_profile_ready",
            category="runtime",
            status="failed",
            evidence=str(exc),
            recommendation="检查 execution profile 配置并重新构建动作。",
        )

        return PreflightReport(
            action_id=action.get("action_id"),
            action_hash=action_hash,
            ready_to_execute=False,
            summary="preflight blocked execution: execution_profile_ready",
            items=[item],
            blocking_items=[item.name],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
    static_items = collect_static_preflight_items(runner, action, repo_path=repo_path)
    runtime_items = collect_runtime_preflight_items(action, runner=runner)
    items = [*static_items, *runtime_items]

    blocking_items = [item.name for item in items if item.status == "failed"]
    ready_to_execute = len(blocking_items) == 0

    if ready_to_execute:
        summary = "preflight passed: no blocking issues detected"
    else:
        summary = (
            "preflight blocked execution: "
            + ", ".join(blocking_items)
        )

    return PreflightReport(
        action_id=action.get("action_id"),
        action_hash=action_hash,
        ready_to_execute=ready_to_execute,
        summary=summary,
        items=items,
        blocking_items=blocking_items,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

def render_preflight_report_md(report: PreflightReport) -> str:
    lines = ["# Preflight Report", ""]

    lines += [
        "## Summary",
        "",
        f"- Action ID: `{report.action_id or 'N/A'}`",
        f"- Action Hash: `{report.action_hash or 'N/A'}`",
        f"- Ready To Execute: `{report.ready_to_execute}`",
        f"- Generated At: `{report.generated_at}`",
        f"- Summary: {report.summary}",
        "",
    ]

    if report.blocking_items:
        lines += ["## Blocking Items", ""]
        for item in report.blocking_items:
            lines.append(f"- {item}")
        lines.append("")

    lines += ["## Items", ""]
    for item in report.items:
        lines.append(f"### {item.name}")
        lines.append("")
        lines.append(f"- Category: `{item.category}`")
        lines.append(f"- Status: `{item.status}`")
        lines.append(f"- Evidence: {item.evidence}")
        if item.recommendation:
            lines.append(f"- Recommendation: {item.recommendation}")
        lines.append("")

    return "\n".join(lines)
