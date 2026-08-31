from __future__ import annotations

from pathlib import Path

IGNORE_DIRS = {
    ".git",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "log",
    "logs",
    "output",
    "outputs",
    "result",
    "results",
    "run",
    "runs",
    "artifact",
    "artifacts",
    "best_model",
    "best_models",
    "build",
    "dist",
    "checkpoint",
    "checkpoints",
    "wandb",
}

# 论文-代码映射只消费 Python 源码、配置、实验脚本和说明文档。CUDA/C++
# 源码、模型权重、数据二进制、共享库、压缩包和普通日志即使文件名包含
# model/train，也不应成为 RepositoryIndex 或映射候选。
MAPPING_CODE_SUFFIXES = {
    ".py",
}
MAPPING_CONFIG_SUFFIXES = {
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
}
MAPPING_DOC_SUFFIXES = {
    ".md",
    ".rst",
    ".txt",
}
MAPPING_SCRIPT_SUFFIXES = {
    ".sh",
}
MAPPING_RELEVANT_SUFFIXES = (
    MAPPING_CODE_SUFFIXES
    | MAPPING_CONFIG_SUFFIXES
    | MAPPING_DOC_SUFFIXES
    | MAPPING_SCRIPT_SUFFIXES
)
MAPPING_RELEVANT_FILENAMES = {
    "dockerfile",
    "makefile",
}


def _resolve_repo(repo_path: str) -> Path:
    """解析并验证仓库根目录，供本模块三个公开函数复用。"""

    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"未找到代码仓库：{repo_path}")
    return root


def _ignored(relative_path: Path) -> bool:
    """只检查仓库相对路径，避免宿主机父目录名称影响过滤结果。"""

    return any(
        part.casefold() in IGNORE_DIRS
        or part.casefold().endswith(".egg-info")
        for part in relative_path.parts
    )


def is_mapping_relevant_file(
    relative_path: str | Path,
) -> bool:
    """判断仓库相对路径是否属于论文映射可消费的文本文件。"""

    relative = Path(relative_path)
    if _ignored(relative):
        return False
    return (
        relative.suffix.casefold()
        in MAPPING_RELEVANT_SUFFIXES
        or relative.name.casefold()
        in MAPPING_RELEVANT_FILENAMES
    )


def get_file_tree(repo_path: str, max_depth: int = 3) -> str:
    root = _resolve_repo(repo_path)
    if max_depth < 1:
        return root.name + "/"

    lines: list[str] = [root.name + "/"]

    def walk(path: Path, depth: int, prefix: str = "") -> None:
        if depth > max_depth:
            return

        children = []
        for candidate in path.iterdir():
            relative = candidate.relative_to(root)
            if _ignored(relative) or candidate.is_symlink():
                # 即使链接最终仍位于仓库内，也不递归符号链接；这样行为更容易审计。
                continue
            children.append(candidate)

        children.sort(
            key=lambda item: (item.is_file(), item.name.lower())
        )
        for index, child in enumerate(children):
            last = index == len(children) - 1
            connector = "└── " if last else "├── "
            lines.append(
                prefix
                + connector
                + child.name
                + ("/" if child.is_dir() else "")
            )
            if child.is_dir():
                extension = "    " if last else "│   "
                walk(child, depth + 1, prefix + extension)

    walk(root, 1)
    return "\n".join(lines)


def list_files(
    repo_path: str,
    suffixes: tuple[str, ...] | None = None,
) -> list[str]:
    root = _resolve_repo(repo_path)
    normalized_suffixes = (
        tuple(value.lower() for value in suffixes)
        if suffixes is not None
        else None
    )

    files: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if _ignored(relative) or path.is_symlink():
            continue
        if not path.is_file():
            continue
        if (
            normalized_suffixes is not None
            and path.suffix.lower() not in normalized_suffixes
        ):
            continue
        files.append(relative.as_posix())
    return sorted(files)


def classify_repo_file(repo_path: str) -> dict[str, list[str]]:
    files = [
        item
        for item in list_files(repo_path)
        if is_mapping_relevant_file(item)
    ]

    def contains_any(path: str, keywords: list[str]) -> bool:
        lower = path.lower()
        return any(keyword in lower for keyword in keywords)

    return {
        "readme_files": [
            item
            for item in files
            if Path(item).name.lower().startswith("readme")
        ],
        "train_entries": [
            item
            for item in files
            if Path(item).suffix.casefold()
            in {".py", ".sh"}
            and contains_any(
                Path(item).name,
                ["train", "finetune"],
            )
        ],
        "eval_entries": [
            item
            for item in files
            if Path(item).suffix.casefold()
            in {".py", ".sh"}
            and contains_any(
                Path(item).name,
                ["eval", "test", "infer"],
            )
        ],
        "config_files": [
            item
            for item in files
            if item.endswith(
                (".yaml", ".yml", ".json", ".toml", ".ini", ".cfg")
            )
            or contains_any(item, ["config", "configs"])
        ],
        "model_files": [
            item
            for item in files
            if Path(item).suffix.casefold()
            in MAPPING_CODE_SUFFIXES
            if contains_any(item, ["model", "models", "network", "net"])
        ],
        "dataset_files": [
            item
            for item in files
            if contains_any(item, ["dataset", "data", "dataloader"])
        ],
        "loss_files": [
            item
            for item in files
            if contains_any(item, ["loss", "criterion"])
        ],
    }
