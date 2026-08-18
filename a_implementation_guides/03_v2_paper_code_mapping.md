# 03. V2 论文-代码证据化映射

## 目标

这是整个项目最重要的面试展示版本。输入 V0 的 `method_modules` 和 V1 的 `repo_map`，输出：

```text
outputs/paper_code_mapping.json
outputs/paper_code_mapping.md
```

核心要求：

```text
论文模块 -> 候选代码文件 -> 关键类/函数 -> 证据 -> 置信度 -> 待确认问题
```

不要强行断言。找不到就写 `low confidence` 或 `need_confirm`。

## 本阶段要新增的文件

```text
app/tools/search_tools.py
app/prompts/mapping_prompt.py
app/nodes/code_search_node.py
app/nodes/mapping_node.py
```

## app/tools/search_tools.py

```python
import subprocess
from pathlib import Path


# 调用 ripgrep 在仓库中搜索指定文本，并返回匹配位置。
def search_text(repo_path: str, query: str, max_results: int = 20) -> list[dict]:
    root = Path(repo_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"repo not found: {repo_path}")

    result = subprocess.run(
        [
            "rg",
            "--line-number",
            "--no-heading",
            "--glob",
            "!{.git,__pycache__,outputs,checkpoints,wandb}/**",
            query,
            str(root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    matches: list[dict] = []
    for line in result.stdout.splitlines()[:max_results]:
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        file_path, line_no, text = parts
        matches.append(
            {
                "file_path": str(Path(file_path).relative_to(root)),
                "line": int(line_no),
                "text": text.strip(),
            }
        )
    return matches


# 针对多个关键词执行搜索，并对结果做去重聚合。
def search_keywords(repo_path: str, keywords: list[str], max_per_keyword: int = 10) -> list[dict]:
    all_matches: list[dict] = []
    seen: set[tuple[str, int, str]] = set()

    for keyword in keywords:
        if not keyword.strip():
            continue
        for match in search_text(repo_path, keyword, max_results=max_per_keyword):
            key = (match["file_path"], match["line"], match["text"])
            if key not in seen:
                seen.add(key)
                match["keyword"] = keyword
                all_matches.append(match)
    return all_matches
```

如果你的环境没有 `rg`，可以先安装 ripgrep；如果暂时不装，也可以用 Python `Path.rglob()` 做慢一点的 fallback。

## app/prompts/mapping_prompt.py

```python
MAPPING_PROMPT = """
你是一个论文复现代码定位助手。

任务：
根据论文方法模块、代码搜索结果和关键代码片段，判断该模块可能对应哪些代码文件。

要求：
1. 每个候选文件都必须给出证据。
2. 如果只是文件名相似，置信度最多 medium。
3. 如果能看到类名、函数名、forward 逻辑、config 参数与论文模块对应，可以给 high。
4. 不确定时写 unresolved_questions，不要编造。
5. 输出必须符合结构化 schema。

论文模块：
{module}

搜索结果：
{search_results}

代码片段：
{code_slices}
"""
```

## app/nodes/code_search_node.py

```python
from pathlib import Path

from app.tools.code_tools import read_file_slice
from app.tools.search_tools import search_keywords


# 根据匹配频次为每个模块挑选优先查看的候选文件。
def _candidate_files_from_matches(matches: list[dict], limit: int = 8) -> list[str]:
    scores: dict[str, int] = {}
    for match in matches:
        file_path = match["file_path"]
        scores[file_path] = scores.get(file_path, 0) + 1
    return [
        file_path
        for file_path, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


# 为每个论文模块搜索候选代码文件并抽取有限代码片段。
def code_search_node(state: dict) -> dict:
    repo_path = state.get("repo_path")
    modules = state.get("method_modules", [])
    if not repo_path:
        return {"error": "repo_path is required"}
    if not modules:
        return {"error": "method_modules is empty"}

    module_search_results: dict[str, dict] = {}
    root = Path(repo_path).resolve()

    for module in modules:
        module_name = module["name"]
        keywords = [module_name, *module.get("possible_keywords", [])]
        matches = search_keywords(repo_path, keywords)
        candidate_files = _candidate_files_from_matches(matches)

        slices: list[dict] = []
        for rel_path in candidate_files[:5]:
            abs_path = root / rel_path
            if abs_path.exists() and abs_path.suffix in {".py", ".yaml", ".yml", ".json", ".md"}:
                slices.append(
                    {
                        "file_path": rel_path,
                        "content": read_file_slice(str(abs_path), 1, 160),
                    }
                )

        module_search_results[module_name] = {
            "keywords": keywords,
            "matches": matches,
            "candidate_files": candidate_files,
            "code_slices": slices,
        }

    return {"code_search_results": module_search_results}
```

## app/nodes/mapping_node.py

```python
import json
from pathlib import Path

from app.config import settings
from app.model import get_chat_model
from app.prompts.mapping_prompt import MAPPING_PROMPT
from app.schemas import ModuleMapping


# 调用 LLM 为每个论文模块生成基于证据的代码映射结果。
def mapping_node(state: dict) -> dict:
    modules = state.get("method_modules", [])
    search_results = state.get("code_search_results", {})
    if not modules or not search_results:
        return {"error": "mapping requires method_modules and code_search_results"}

    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(ModuleMapping)

    mappings: list[dict] = []
    for module in modules:
        module_name = module["name"]
        result = search_results.get(module_name, {})
        mapping: ModuleMapping = structured_llm.invoke(
            MAPPING_PROMPT.format(
                module=json.dumps(module, ensure_ascii=False, indent=2),
                search_results=json.dumps(result.get("matches", []), ensure_ascii=False, indent=2),
                code_slices=json.dumps(result.get("code_slices", []), ensure_ascii=False, indent=2),
            )
        )
        mappings.append(mapping.model_dump())

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "paper_code_mapping.json"
    md_path = settings.output_dir / "paper_code_mapping.md"

    json_path.write_text(json.dumps(mappings, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_mapping_markdown(mappings), encoding="utf-8")

    return {
        "paper_code_mapping": mappings,
        "output_files": [
            *state.get("output_files", []),
            str(json_path),
            str(md_path),
        ],
    }


# 把结构化 mapping 结果渲染成便于人工检查的 markdown 报告。
def _render_mapping_markdown(mappings: list[dict]) -> str:
    lines = ["# Paper-Code Mapping", ""]
    for mapping in mappings:
        lines.append(f"## {mapping['module_name']}")
        lines.append("")
        unresolved = mapping.get("unresolved_questions", [])
        if unresolved:
            lines.append("### Unresolved Questions")
            for item in unresolved:
                lines.append(f"- {item}")
            lines.append("")

        lines.append("| Candidate File | Symbols | Confidence | Reason |")
        lines.append("|---|---|---|---|")
        for candidate in mapping.get("candidates", []):
            symbols = ", ".join(candidate.get("symbols", []))
            reason = candidate.get("reason", "").replace("\n", " ")
            lines.append(
                f"| `{candidate['file_path']}` | {symbols} | "
                f"{candidate.get('confidence', 'medium')} | {reason} |"
            )
        lines.append("")
    return "\n".join(lines)
```

## CLI 入口

```python
from app.nodes.code_search_node import code_search_node
from app.nodes.mapping_node import mapping_node


# 串联论文阅读、仓库扫描和代码映射流程，生成最终 mapping 产物。
@app.command()
def map_code(paper_path: str, repo_path: str):
    state = {
        "paper_path": paper_path,
        "repo_path": repo_path,
        "output_files": [],
    }
    state.update(paper_reader_node(state))
    state.update(method_extractor_node(state))
    state.update(repo_scan_node(state))
    state.update(code_search_node(state))
    state.update(mapping_node(state))
    print("[green]paper-code mapping finished[/green]")
    print(state["output_files"])
```

## 本阶段验收

你需要打开 `outputs/paper_code_mapping.md` 检查：

- 每个论文模块是否至少有候选代码文件。
- 候选文件是否有证据，而不是只靠猜。
- 置信度是否合理。
- 找不到的内容是否写入 unresolved questions。

## 面试讲法

你可以这样讲：

```text
我没有让模型直接读整个仓库，而是先由论文模块生成关键词，
再用只读工具搜索候选文件，读取有限代码片段，
最后让 LLM 基于证据生成 mapping。
每个 mapping 都有 evidence、confidence 和 unresolved_questions，
这样可以降低幻觉，也方便人工复核。
```
