from __future__ import annotations

from pathlib import Path, PurePosixPath

from app.config import settings
from app.workspace.errors import WorkspaceIntegrityError

RUN_LAYERS = {
    "inputs",
    "analysis",
    "planning",
    "execution",
    "debug",
    "patches",
    "reports",
    "traces",
}


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def managed_run_roots() -> tuple[Path, ...]:
    return (
        settings.runs_dir.expanduser().resolve(),
        settings.worker_workspace_root.expanduser().resolve(),
    )


def require_managed_run_root(raw_path: str | Path) -> Path:
    candidate = Path(raw_path).expanduser().resolve()
    roots = managed_run_roots()
    if not any(
        candidate != root and root in candidate.parents
        for root in roots
    ):
        raise WorkspaceIntegrityError(
            f"run_dir 不在受信任 run root 内：{candidate}"
        )
    return candidate


def require_workspace_relative_path(value: str) -> PurePosixPath:
    logical = PurePosixPath(value)
    if (
        logical.is_absolute()
        or not logical.parts
        or any(part in {"", ".", ".."} for part in logical.parts)
    ):
        raise WorkspaceIntegrityError(
            f"无效 workspace logical_path：{value!r}"
        )
    return logical


def resolve_inside(root: Path, logical_path: str) -> Path:
    logical = require_workspace_relative_path(logical_path)
    target = root.joinpath(*logical.parts).resolve()
    if target == root or root not in target.parents:
        raise WorkspaceIntegrityError("workspace path 逃逸 root")
    return target


def create_run_layout_at(run_root: Path) -> dict[str, str]:
    checked = require_managed_run_root(run_root)
    layout = {"run_root": str(checked)}
    for layer in sorted(RUN_LAYERS):
        directory = checked / layer
        directory.mkdir(parents=True, exist_ok=True)
        layout[f"{layer}_dir"] = str(directory)
    return layout
