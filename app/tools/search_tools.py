from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app.tools.repo_tools import IGNORE_DIRS

_FALLBACK_SUFFIXES = {
    ".py",
    ".md",
    ".rst",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
}


class SearchToolError(RuntimeError):
    """搜索工具执行失败，而不是正常的零命中。"""


def _resolve_repo(repo_path: str) -> Path:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"未找到代码仓库：{repo_path}"
        )
    return root


def _relative_path(root: Path, raw_path: str) -> str:
    path = Path(raw_path)
    resolved = (
        path.resolve()
        if path.is_absolute()
        else (root / path).resolve()
    )
    if resolved == root or root not in resolved.parents:
        raise SearchToolError(
            f"rg 返回了仓库边界外路径：{raw_path}"
        )
    return resolved.relative_to(root).as_posix()


def _parse_rg_json(
    *,
    root: Path,
    stdout: str,
    max_results: int,
) -> list[dict]:
    matches: list[dict] = []

    for raw_line in stdout.splitlines():
        if len(matches) >= max_results:
            break
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise SearchToolError(
                "无法解析 rg --json 输出"
            ) from exc

        if event.get("type") != "match":
            continue

        data = event.get("data") or {}
        path_data = data.get("path") or {}
        lines_data = data.get("lines") or {}
        raw_path = str(path_data.get("text") or "")
        line_number = int(data.get("line_number") or 0)
        if not raw_path or line_number < 1:
            continue

        matches.append(
            {
                "file_path": _relative_path(
                    root,
                    raw_path,
                ),
                "line": line_number,
                "text": str(
                    lines_data.get("text") or ""
                ).strip(),
            }
        )

    return matches


def _python_literal_search(
    *,
    root: Path,
    query: str,
    max_results: int,
    ignore_case: bool,
) -> list[dict]:
    """rg 不存在时的确定性 fallback。"""

    needle = query.casefold() if ignore_case else query
    matches: list[dict] = []

    for path in sorted(root.rglob("*")):
        if len(matches) >= max_results:
            break
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix.casefold()
            not in _FALLBACK_SUFFIXES
            or any(
                part in IGNORE_DIRS
                or part == ".pytest_cache"
                for part in path.relative_to(root).parts
            )
        ):
            continue

        try:
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            lines = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
        except OSError as exc:
            raise SearchToolError(
                f"读取搜索文件失败：{path}"
            ) from exc

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            haystack = (
                line.casefold()
                if ignore_case
                else line
            )
            if needle not in haystack:
                continue
            matches.append(
                {
                    "file_path": (
                        path.relative_to(root).as_posix()
                    ),
                    "line": line_number,
                    "text": line.strip(),
                }
            )
            if len(matches) >= max_results:
                break

    return matches


def search_text(
    repo_path: str,
    query: str,
    max_results: int = 20,
    *,
    literal: bool = True,
    ignore_case: bool = True,
    timeout_seconds: int = 10,
) -> list[dict]:
    """搜索文本，并区分零命中、工具错误和工具超时。"""

    root = _resolve_repo(repo_path)
    value = query.strip()
    if not value or max_results <= 0:
        return []
    if timeout_seconds < 1 or timeout_seconds > 60:
        raise ValueError("timeout_seconds 必须位于 1 到 60 秒之间")

    rg = shutil.which("rg")
    if rg is None:
        if not literal:
            raise SearchToolError(
                "regex 搜索要求安装 rg；"
                "Python fallback 只支持 literal"
            )
        return _python_literal_search(
            root=root,
            query=value,
            max_results=max_results,
            ignore_case=ignore_case,
        )

    args = [
        rg,
        "--json",
        "--line-number",
        "--color",
        "never",
    ]
    if literal:
        args.append("--fixed-strings")
    if ignore_case:
        args.append("--ignore-case")

    for ignored in sorted({*IGNORE_DIRS, ".pytest_cache"}):
        args.extend(["--glob", f"!{ignored}/**"])

    args.extend(["--", value, str(root)])

    try:
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise SearchToolError(
            f"rg 搜索在 {timeout_seconds} 秒后超时"
        ) from exc
    except OSError as exc:
        if literal:
            return _python_literal_search(
                root=root,
                query=value,
                max_results=max_results,
                ignore_case=ignore_case,
            )
        raise SearchToolError(f"无法启动 rg：{exc}") from exc

    if result.returncode == 1:
        return []
    if result.returncode != 0:
        message = result.stderr.strip() or (
            f"rg exited with {result.returncode}"
        )
        raise SearchToolError(message)

    return _parse_rg_json(
        root=root,
        stdout=result.stdout,
        max_results=max_results,
    )


def search_keywords(
    repo_path: str,
    keywords: list[str],
    max_per_keyword: int = 10,
    *,
    timeout_seconds: int = 10,
) -> list[dict]:
    all_matches: list[dict] = []
    seen: set[tuple[str, int, str]] = set()

    for keyword in keywords:
        value = keyword.strip()
        if not value:
            continue
        for match in search_text(
            repo_path,
            value,
            max_results=max_per_keyword,
            literal=True,
            timeout_seconds=timeout_seconds,
        ):
            key = (
                match["file_path"],
                match["line"],
                match["text"],
            )
            if key in seen:
                continue
            seen.add(key)
            all_matches.append(
                {
                    **match,
                    "keyword": value,
                }
            )

    return all_matches