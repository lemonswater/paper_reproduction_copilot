# 01. V0 论文结构化阅读

## 目标

输入论文文件，输出复现导向的结构化摘要：

```text
outputs/paper_summary.json
outputs/method_modules.json
```

重点不是“中文总结写得好”，而是能提取复现需要的信息，并明确哪些信息缺失。

## 本阶段要新增的文件

```text
app/tools/paper_tools.py
app/prompts/paper_prompt.py
app/nodes/paper_reader_node.py
app/nodes/method_extractor_node.py
```

## app/tools/paper_tools.py

```python
from pathlib import Path

import fitz


# 逐页读取 PDF 论文文本，并为每页补上页码标记。
def read_pdf(path: str) -> str:
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"paper not found: {path}")

    chunks: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                chunks.append(f"[page {page_index + 1}]\n{text}")
    return "\n\n".join(chunks)


# 读取 markdown 或纯文本格式的论文内容。
def read_text_file(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"paper not found: {path}")
    return file_path.read_text(encoding="utf-8", errors="ignore")


# 根据文件后缀选择合适的论文读取方式。
def read_paper(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix in {".md", ".txt"}:
        return read_text_file(path)
    raise ValueError(f"unsupported paper format: {suffix}")


# 将长文本切成带 overlap 的 chunk，便于分段送入模型。
def split_text(text: str, chunk_size: int = 5000, overlap: int = 500) -> list[dict]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[dict] = []
    start = 0
    chunk_id = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(
            {
                "chunk_id": chunk_id,
                "start": start,
                "end": end,
                "text": text[start:end],
            }
        )
        chunk_id += 1
        start = end - overlap
        if start < 0:
            start = 0
        if end == len(text):
            break
    return chunks
```

## app/prompts/paper_prompt.py

```python
PAPER_SUMMARY_PROMPT = """
你是一个论文复现助手。请从论文文本中提取复现需要的信息。

要求：
1. 不要只做摘要，要提取可复现信息。
2. 不确定的信息必须写入 unresolved_questions。
3. 如果论文没有明确给出 batch size、learning rate、optimizer 等训练设置，不要猜。
4. method_modules 中每个模块都要给出 possible_keywords，后续用于搜索代码。
5. evidence 中引用简短证据摘要，不要大段复制论文。

论文文本：
{paper_text}
"""
```

## app/nodes/paper_reader_node.py

```python
from app.tools.paper_tools import read_paper, split_text


# 读取论文并把切分后的文本块写入 state。
def paper_reader_node(state: dict) -> dict:
    paper_path = state.get("paper_path")
    if not paper_path:
        return {"error": "paper_path is required"}

    paper_text = read_paper(paper_path)
    chunks = split_text(paper_text)

    return {
        "paper_text_chunks": chunks,
        "output_files": state.get("output_files", []),
    }
```

## app/nodes/method_extractor_node.py

```python
import json
from pathlib import Path

from app.config import settings
from app.model import get_chat_model
from app.prompts.paper_prompt import PAPER_SUMMARY_PROMPT
from app.schemas import PaperSummary


# 在字符数限制内合并前几个 chunk，控制送入模型的上下文长度。
def _merge_chunks(chunks: list[dict], max_chars: int = 24000) -> str:
    text_parts: list[str] = []
    total = 0
    for chunk in chunks:
        text = chunk["text"]
        if total + len(text) > max_chars:
            break
        text_parts.append(text)
        total += len(text)
    return "\n\n".join(text_parts)


# 调用 LLM 抽取论文的结构化摘要并写出结果文件。
def method_extractor_node(state: dict) -> dict:
    chunks = state.get("paper_text_chunks", [])
    if not chunks:
        return {"error": "paper_text_chunks is empty"}

    paper_text = _merge_chunks(chunks)
    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(PaperSummary)

    summary: PaperSummary = structured_llm.invoke(
        PAPER_SUMMARY_PROMPT.format(paper_text=paper_text)
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    paper_summary_path = settings.output_dir / "paper_summary.json"
    method_modules_path = settings.output_dir / "method_modules.json"

    paper_summary_path.write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    method_modules_path.write_text(
        json.dumps(
            [m.model_dump() for m in summary.method_modules],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "paper_summary": summary.model_dump(),
        "method_modules": [m.model_dump() for m in summary.method_modules],
        "output_files": [
            *state.get("output_files", []),
            str(paper_summary_path),
            str(method_modules_path),
        ],
    }
```

## CLI 入口

在 `app/main.py` 增加：

```python
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.method_extractor_node import method_extractor_node


# 运行论文阅读完整流程，并输出生成的结果文件路径。
@app.command()
def read_paper(paper_path: str):
    state = {"paper_path": paper_path, "output_files": []}
    state.update(paper_reader_node(state))
    state.update(method_extractor_node(state))
    print("[green]paper reading finished[/green]")
    print(state["output_files"])
```

## 运行方式

```bash
python -m app.main read-paper data/example_paper.pdf
```

## 本阶段验收

检查：

```text
outputs/paper_summary.json
outputs/method_modules.json
```

你要能回答：

- 论文研究问题是什么？
- 核心方法拆成了哪些模块？
- 哪些训练设置是论文明确给出的？
- 哪些信息需要去代码里确认？

## 常见坑

- PDF 解析会丢公式和表格，V0 先接受这个限制。
- 不要把整篇论文一次塞进模型，先切 chunk。
- 不要让模型猜 batch size、learning rate 这类字段。
- 后续 V2 要依赖 `possible_keywords`，所以 V0 抽取时就要认真生成关键词。
