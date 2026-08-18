# 02. V1 代码仓库地图

## 目标

输入本地代码仓库路径，输出：

```text
outputs/repo_map.json
outputs/repo_summary.md
```

这个阶段的核心思想是：先建代码地图，再决定读哪些文件。不要让 Agent 盲读整个仓库。

## 本阶段要新增的文件

```text
app/tools/repo_tools.py
app/tools/code_tools.py
app/nodes/repo_scan_node.py
```

## app/tools/repo_tools.py

```python
from pathlib import Path


IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "outputs",
    "checkpoints",
    "wandb",
}


# 生成仓库的文本目录树，帮助快速建立全局结构视图。
def get_file_tree(repo_path: str, max_depth: int = 3) -> str:
    root = Path(repo_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"repo not found: {repo_path}")

    lines: list[str] = [root.name + "/"]

    # 递归遍历目录并把每一层格式化成树形文本。
    def walk(path: Path, depth: int, prefix: str = "") -> None:
        if depth > max_depth:
            return
        children = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        children = [p for p in children if p.name not in IGNORE_DIRS]
        for index, child in enumerate(children):
            connector = "└── " if index == len(children) - 1 else "├── "
            lines.append(prefix + connector + child.name + ("/" if child.is_dir() else ""))
            if child.is_dir():
                extension = "    " if index == len(children) - 1 else "│   "
                walk(child, depth + 1, prefix + extension)

    walk(root, 1)
    return "\n".join(lines)


# 递归列出仓库中的文件，并可按后缀进行过滤。
def list_files(repo_path: str, suffixes: tuple[str, ...] | None = None) -> list[str]:
    root = Path(repo_path).resolve()
    files: list[str] = []
    for path in root.rglob("*"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_file() and (suffixes is None or path.suffix in suffixes):
            files.append(str(path.relative_to(root)))
    return sorted(files)


# 按文件名和路径中的关键词，对仓库文件做启发式分类。
def classify_repo_files(repo_path: str) -> dict[str, list[str]]:
    files = list_files(repo_path)

    # 判断文件路径中是否出现任一目标关键词。
    def contains_any(path: str, keywords: list[str]) -> bool:
        lower = path.lower()
        return any(keyword in lower for keyword in keywords)

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
        "loss_files": [f for f in files if contains_any(f, ["loss", "criterion"])],
    }
```

## app/tools/code_tools.py

```python
import ast
from pathlib import Path


# 读取指定行区间的代码片段，并为每行补上行号。
def read_file_slice(path: str, start_line: int = 1, end_line: int = 120) -> str:
    file_path = Path(path)
    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = max(start_line, 1)
    end = min(end_line, len(lines))
    numbered = [
        f"{line_no}: {lines[line_no - 1]}"
        for line_no in range(start, end + 1)
    ]
    return "\n".join(numbered)


# 用 AST 提取 Python 文件中的类和函数定义信息。
def extract_python_symbols(path: str) -> list[dict]:
    file_path = Path(path)
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)

    symbols: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(
                {
                    "type": "class",
                    "name": node.name,
                    "line": node.lineno,
                }
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                {
                    "type": "function",
                    "name": node.name,
                    "line": node.lineno,
                }
            )
    return sorted(symbols, key=lambda item: item["line"])
```

## app/nodes/repo_scan_node.py

```python
import json

from app.config import settings
from app.schemas import RepoMap
from app.tools.repo_tools import classify_repo_files, get_file_tree


# 扫描仓库、构建 RepoMap，并把扫描结果写入输出文件。
def repo_scan_node(state: dict) -> dict:
    repo_path = state.get("repo_path")
    if not repo_path:
        return {"error": "repo_path is required"}

    tree = get_file_tree(repo_path)
    classified = classify_repo_files(repo_path)
    important_files = sorted(
        set(
            classified["readme_files"]
            + classified["train_entries"]
            + classified["eval_entries"]
            + classified["config_files"]
            + classified["model_files"]
            + classified["dataset_files"]
            + classified["loss_files"]
        )
    )

    repo_map = RepoMap(
        repo_path=repo_path,
        important_files=important_files,
        **classified,
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    repo_map_path = settings.output_dir / "repo_map.json"
    repo_summary_path = settings.output_dir / "repo_summary.md"

    repo_map_path.write_text(repo_map.model_dump_json(indent=2), encoding="utf-8")
    repo_summary_path.write_text(
        "# Repo Summary\n\n"
        "## File Tree\n\n"
        f"```text\n{tree}\n```\n\n"
        "## Important Files\n\n"
        f"```json\n{json.dumps(repo_map.model_dump(), ensure_ascii=False, indent=2)}\n```\n",
        encoding="utf-8",
    )

    return {
        "repo_tree": tree,
        "repo_map": repo_map.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(repo_map_path),
            str(repo_summary_path),
        ],
    }
```

## CLI 入口

在 `app/main.py` 增加：

```python
from app.nodes.repo_scan_node import repo_scan_node


# 运行仓库扫描流程，并输出仓库地图相关文件。
@app.command()
def scan_repo(repo_path: str):
    state = {"repo_path": repo_path, "output_files": []}
    state.update(repo_scan_node(state))
    print("[green]repo scan finished[/green]")
    print(state["output_files"])
```

## 运行方式

```bash
python -m app.main scan-repo /path/to/paper-official-repo
```

## 本阶段验收

你要能从 `outputs/repo_map.json` 中看到：

- README 在哪里。
- train / eval 入口在哪里。
- config 文件在哪里。
- model / dataset / loss 相关文件在哪里。
- 哪些文件需要下一阶段优先读取。

## 常见坑

- 目录扫描需要忽略 `.git`、`outputs`、`checkpoints`、`wandb`。
- 启发式分类会误判，V1 允许误判，但要记录 warnings。
- 如果 repo 很大，不要一次读所有代码文件，只保留文件路径和符号信息。
