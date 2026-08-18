from __future__ import annotations

import re
from pathlib import Path

ERROR_KEYWORDS = [
    "Traceback",
    "RuntimeError",
    "ValueError",
    "ImportError",
    "ModuleNotFoundError",
    "FileNotFoundError",
    "CUDA out of memory",
    "shape",
    "size mismatch"
]

def read_log(path: str, max_chars: int = 30000) -> str:
    log_path = Path(path)
    if not log_path.exists():
        raise FileNotFoundError(f"未找到日志文件：{path}")
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    return text[-max_chars:]

def extract_traceback(log_text: str) -> str:
    index = log_text.rfind("Traceback")
    if index >= 0:
        return log_text[index:]
    lines = log_text.splitlines()
    suspicious = [
        line for line in lines if any(keyword.lower() in line.lower() for keyword in ERROR_KEYWORDS)
    ]
    return "\n".join(suspicious[-80:])

def classify_error_heuristic(traceback: str) -> str:
    lower = traceback.lower()
    if "modulenotfounderror" in lower or "importerror" in lower:
        return "dependency_missing"
    if "filenotfounderror" in lower or "no such file" in lower:
        return "data_or_path_error"
    if "cuda out of memory" in lower:
        return "cuda_oom"
    if "size mismatch" in lower or "shape" in lower:
        return "shape_mismatch"
    if "permission denied" in lower:
        return "permission_error"
    return "unknown"


def extract_repo_traceback_paths(
    traceback: str,
    *,
    repo_path: str | None,
) -> list[str]:
    """
    从 Python/pytest traceback 中提取真实存在的仓库相对路径。

    模型可以补充语义关联，但不能成为错误文件白名单的唯一来源。这里只接受
    resolve 后仍位于 repo_path 内的已有 Python 普通文件，并按首次出现顺序去重。
    """

    if not repo_path or not traceback.strip():
        return []

    patterns = (
        re.compile(
            r"""File\s+["'](?P<path>[^"']+?\.py)["'],\s+line\s+\d+"""
        ),
        re.compile(
            r"""(?m)^\s*(?P<path>[^:\n]*?\.py):\d+(?::[^\n]*)?$"""
        ),
    )

    candidates: list[str] = []
    for pattern in patterns:
        candidates.extend(
            match.group("path").strip()
            for match in pattern.finditer(traceback)
        )

    repo = Path(repo_path).resolve()
    related_paths: list[str] = []
    seen: set[str] = set()

    for raw_path in candidates:
        candidate = Path(raw_path)
        unresolved = candidate if candidate.is_absolute() else repo / candidate

        try:
            target = unresolved.resolve()
        except OSError:
            continue

        if target == repo or repo not in target.parents:
            continue
        if not target.exists() or not target.is_file():
            continue
        if target.suffix.lower() != ".py" or unresolved.is_symlink():
            continue

        relative = target.relative_to(repo).as_posix()
        if relative in seen:
            continue

        seen.add(relative)
        related_paths.append(relative)

    return related_paths
