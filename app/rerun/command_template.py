# app/rerun/command_template.py
from __future__ import annotations

import hashlib
import re
import shlex
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

from app.rerun.errors import (
    RerunCommandRejectedError,
    RerunConflictError,
    RerunIntegrityError,
)
from app.rerun.identity import (
    command_template_hash,
    validate_command_template_hash,
)
from app.rerun.schemas import (
    RerunArgumentEdit,
    RerunCommandTemplate,
    RerunTemplateArg,
)
from app.workspace.schemas import (
    ExternalDataReference,
    WorkspaceManifest,
)

_FORBIDDEN_SHELL = re.compile(r"[|&;<>`\n\r]|\$\(")
_OPTION = re.compile(r"^--[A-Za-z0-9][A-Za-z0-9_-]*$")
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_SECRET_PARTS = {
    "api-key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_secret_option(option: str) -> bool:
    normalized = option.lower().lstrip("-").replace("_", "-")
    return any(part in normalized for part in _SECRET_PARTS)


def _reject_shell_text(value: str, *, field: str) -> None:
    if not value or "\x00" in value or _FORBIDDEN_SHELL.search(value):
        raise RerunCommandRejectedError(
            f"{field} 包含空值、NUL 或不支持的 Shell 语法"
        )


def _pure_absolute(value: str, *, field: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts:
        raise RerunCommandRejectedError(
            f"{field} 必须是无 .. 的绝对 POSIX 路径"
        )
    return path


def _relative_under(
    value: PurePosixPath,
    root: PurePosixPath,
) -> str | None:
    try:
        relative = value.relative_to(root)
    except ValueError:
        return None
    text = relative.as_posix()
    return text if text else "."


def _dataset_root(reference: ExternalDataReference) -> PurePosixPath | None:
    parsed = urlparse(reference.uri)
    if parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"}:
            return None
        return _pure_absolute(
            unquote(parsed.path),
            field=f"dataset {reference.name} uri",
        )
    if not parsed.scheme and reference.uri.startswith("/"):
        return _pure_absolute(
            reference.uri,
            field=f"dataset {reference.name} uri",
        )
    return None


def _normalize_option_equals(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    for token in argv:
        if token.startswith("--") and "=" in token:
            option, value = token.split("=", 1)
            if not _OPTION.fullmatch(option):
                raise RerunCommandRejectedError(
                    f"非法长选项：{option!r}"
                )
            normalized.extend([option, value])
        else:
            normalized.append(token)
    return normalized


def _parse_parent_argv(
    command: str,
    *,
    max_command_chars: int,
    max_argv_items: int,
) -> list[str]:
    if len(command) > max_command_chars:
        raise RerunCommandRejectedError("父命令超过字符上限")
    _reject_shell_text(command, field="parent command")
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as exc:
        raise RerunCommandRejectedError(
            "父命令不是合法的单进程 argv"
        ) from exc
    if not argv or len(argv) > max_argv_items:
        raise RerunCommandRejectedError(
            "父命令 argv 为空或超过数量上限"
        )
    if _ENV_ASSIGNMENT.match(argv[0]):
        raise RerunCommandRejectedError(
            "第一版不继承命令前的环境变量赋值"
        )
    normalized = _normalize_option_equals(argv)
    for token in normalized:
        if _OPTION.fullmatch(token) and _is_secret_option(token):
            raise RerunCommandRejectedError(
                f"父命令包含 secret-like 参数：{token}"
            )
    return normalized


def _find_edit_span(
    argv: list[str],
    edit: RerunArgumentEdit,
) -> tuple[int, int]:
    indexes = [
        index
        for index, token in enumerate(argv)
        if token == edit.option
    ]
    if len(indexes) != 1:
        raise RerunCommandRejectedError(
            f"{edit.option} 必须在父命令中恰好出现一次"
        )
    start = indexes[0]
    next_index = start + 1

    if edit.expected_old_value is None:
        # expected_old_value=None 表示调用方确认它是无值 flag。
        if next_index < len(argv) and not argv[next_index].startswith("--"):
            raise RerunCommandRejectedError(
                f"{edit.option} 当前看起来带值；请提交 expected_old_value"
            )
        return start, start + 1

    if next_index >= len(argv) or argv[next_index] != edit.expected_old_value:
        raise RerunConflictError(
            f"{edit.option} 的旧值已变化或与 expected_old_value 不一致"
        )
    return start, start + 2


def _validate_new_value(value: str) -> None:
    _reject_shell_text(value, field="new option value")
    if value.startswith("/"):
        raise RerunCommandRejectedError(
            "参数编辑不能注入新的主机绝对路径"
        )
    if value.startswith("${"):
        raise RerunCommandRejectedError(
            "参数编辑不能伪造内部模板占位符"
        )


def apply_argument_edits(
    argv: list[str],
    edits: list[RerunArgumentEdit],
) -> list[str]:
    result = list(argv)
    seen: set[str] = set()
    for edit in edits:
        if edit.option in seen:
            raise RerunCommandRejectedError("同一 option 不能重复编辑")
        seen.add(edit.option)
        if _is_secret_option(edit.option):
            raise RerunCommandRejectedError(
                "禁止修改 secret-like option"
            )
        start, end = _find_edit_span(result, edit)
        if edit.operation == "remove":
            result[start:end] = []
        else:
            assert edit.value is not None
            _validate_new_value(edit.value)
            result[start:end] = [edit.option, edit.value]
    return result


def _template_arg(
    token: str,
    *,
    repo_root: PurePosixPath,
    run_root: PurePosixPath,
    datasets: list[ExternalDataReference],
) -> RerunTemplateArg:
    if not token.startswith("/"):
        return RerunTemplateArg(kind="literal", value=token)

    absolute = _pure_absolute(token, field="command argument")
    repo_relative = _relative_under(absolute, repo_root)
    if repo_relative is not None:
        return RerunTemplateArg(
            kind="repo_path",
            relative_path=repo_relative,
        )

    run_relative = _relative_under(absolute, run_root)
    if run_relative is not None:
        return RerunTemplateArg(
            kind="run_path",
            relative_path=run_relative,
        )

    matches: list[tuple[ExternalDataReference, str]] = []
    for reference in datasets:
        root = _dataset_root(reference)
        if root is None:
            continue
        relative = _relative_under(absolute, root)
        if relative is not None:
            matches.append((reference, relative))
    if len(matches) == 1:
        reference, relative = matches[0]
        return RerunTemplateArg(
            kind="dataset_path",
            dataset_label=reference.required_worker_label,
            relative_path=relative,
        )
    if len(matches) > 1:
        raise RerunCommandRejectedError(
            "绝对路径同时匹配多个 dataset reference"
        )
    raise RerunCommandRejectedError(
        "命令包含无法解释的主机绝对路径"
    )


def build_command_template(
    *,
    selected_action: Any,
    run_manifest: dict,
    workspace: WorkspaceManifest,
    edits: list[RerunArgumentEdit],
    max_command_chars: int,
    max_argv_items: int,
) -> RerunCommandTemplate:
    if not isinstance(selected_action, dict):
        raise RerunCommandRejectedError(
            "父 run_manifest 缺少 selected_run_command"
        )
    command = str(selected_action.get("command") or "").strip()
    cwd = str(selected_action.get("cwd") or "").strip()
    repo_path = str(run_manifest.get("repo_path") or "").strip()
    run_dir = str(run_manifest.get("run_dir") or "").strip()
    if not command or not cwd or not repo_path or not run_dir:
        raise RerunCommandRejectedError(
            "父命令缺少 command、cwd、repo_path 或 run_dir"
        )

    repo_root = _pure_absolute(repo_path, field="parent repo_path")
    run_root = _pure_absolute(run_dir, field="parent run_dir")
    cwd_path = _pure_absolute(cwd, field="parent command cwd")
    cwd_relative = _relative_under(cwd_path, repo_root)
    if cwd_relative is None:
        raise RerunCommandRejectedError(
            "父命令 cwd 不在父 repository 内"
        )

    argv = _parse_parent_argv(
        command,
        max_command_chars=max_command_chars,
        max_argv_items=max_argv_items,
    )
    edited_argv = apply_argument_edits(argv, edits)
    if not edited_argv:
        raise RerunCommandRejectedError("编辑后命令为空")

    template_args = [
        _template_arg(
            token,
            repo_root=repo_root,
            run_root=run_root,
            datasets=workspace.external_data,
        )
        for token in edited_argv
    ]
    draft = RerunCommandTemplate(
        argv=template_args,
        cwd_relative=cwd_relative,
        source="config",
        risk_level="high",
        reason="由可信父运行派生；必须重新完成预检与审批。",
        parent_command_sha256=_sha256_text(command),
        template_hash="0" * 64,
    )
    return draft.model_copy(
        update={"template_hash": command_template_hash(draft)}
    )


def _resolve_inside(root: Path, relative_path: str) -> Path:
    if relative_path == ".":
        return root.resolve()
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise RerunIntegrityError("模板相对路径非法")
    target = (root / Path(*pure.parts)).resolve()
    root = root.resolve()
    if target != root and root not in target.parents:
        raise RerunIntegrityError("模板路径逃逸运行时根目录")
    return target


def resolve_command_template(
    *,
    template: RerunCommandTemplate,
    repo_path: str,
    run_dir: str,
    dataset_mounts: dict[str, str],
) -> dict[str, str]:
    validate_command_template_hash(template)
    repo_root = Path(repo_path).resolve()
    child_run_root = Path(run_dir).resolve()
    argv: list[str] = []
    for item in template.argv:
        if item.kind == "literal":
            assert item.value is not None
            argv.append(item.value)
        elif item.kind == "repo_path":
            assert item.relative_path is not None
            argv.append(
                str(_resolve_inside(repo_root, item.relative_path))
            )
        elif item.kind == "run_path":
            assert item.relative_path is not None
            argv.append(
                str(_resolve_inside(child_run_root, item.relative_path))
            )
        else:
            assert item.dataset_label is not None
            assert item.relative_path is not None
            raw_mount = dataset_mounts.get(item.dataset_label)
            if not raw_mount:
                raise RerunIntegrityError(
                    f"Worker 缺少数据集挂载：{item.dataset_label}"
                )
            mount_root = Path(raw_mount).resolve()
            argv.append(
                str(_resolve_inside(mount_root, item.relative_path))
            )

    cwd = _resolve_inside(repo_root, template.cwd_relative)
    return {
        "command": shlex.join(argv),
        "cwd": str(cwd),
        "source": template.source,
        "risk_level": template.risk_level,
        "reason": template.reason,
    }
