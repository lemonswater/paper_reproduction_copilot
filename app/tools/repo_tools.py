from pathlib import Path

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    "outputs",
    "checkpoints",
    "wandb"
}

def get_file_tree(repo_path: str, max_depth: int = 3) -> str:
    root = Path(repo_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"repo not found: {repo_path}")
    
    lines: list[str] = [root.name + "/"]

    def walk(path: Path, depth: int, prefix: str = "") -> None:
        if depth > max_depth:
            return
        children = sorted(path.iterdir(), key = lambda p: (p.is_file(), p.name.lower()))
        children = [p for p in children if p.name not in IGNORE_DIRS]
        for index, child in enumerate(children):
            connector = "└── " if index == len(children) - 1 else "├── "
            lines.append(prefix + connector + child.name + ("/" if child.is_dir() else ""))
            if child.is_dir():
                extension = " " if index == len(children) - 1 else "|  "
                walk(child, depth + 1, prefix + extension)
    walk(root, 1)
    return "\n".join(lines)

def list_files(repo_path: str, suffixes: tuple[str, ...] | None = None) -> list[str]:
    root  =Path(repo_path).resolve()
    files: list[str] = []
    for path in root.rglob("*"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_file() and (suffixes is None or path.suffix in suffixes):
            files.append(str(path.relative_to(root)))
    return sorted(files)

def classify_repo_file(repo_path: str) -> dict[str, list[str]]:
    files = list_files(repo_path)
    
    def contains_any(path: str, keywords: list[str]) -> bool:
        lower = path.lower()
        return any(keyword in lower for keyword in  keywords)

    return {
        "readme_files": [f for f in files if Path(f).name.lower().startswith("readme")],
        "train_entries": [f for f in files if contains_any(f, ["train", "finetune"])],
        "eval_entries": [f for f in files if contains_any(f, ["eval", "test", "infer"])],
        "config_files": [
            f for f in files
            if f.endswith((".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"))
            or contains_any(f, ["config", "configs"])
        ],
        "model_files": [f for f in files if contains_any(f, ["model", "models", "network", "net"])],
        "dataset_files": [f for f in files if contains_any(f, ["dataset", "data", "dataloader"])],
        "loss_files": [f for f in files if contains_any(f, ["loss", "criterion"])]
    }