# 06. V5 日志 Debug

## 目标

目标上，这一阶段希望系统能处理训练日志或 traceback 一类失败信息。

当前这版实现里，实际输入接口是：

- 通过 `state["log_path"]` 传入日志文件路径
- 节点内部先读取日志文件
- 再从日志中提取 traceback

输出：

```text
outputs/debug_report.json
outputs/debug_report.md
```

这一步要体现 Agent 能处理失败路径，而不是只处理理想流程。

## 本阶段要新增的文件

```text
app/tools/log_tools.py
app/prompts/debug_prompt.py
app/nodes/log_debug_node.py
```

## app/tools/log_tools.py

```python
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
    "size mismatch",
]


# 读取日志文件尾部内容，控制输入模型的最大字符数。
def read_log(path: str, max_chars: int = 30000) -> str:
    log_path = Path(path)
    if not log_path.exists():
        raise FileNotFoundError(f"log not found: {path}")
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    return text[-max_chars:]


# 从日志中优先提取 traceback，不存在时退化为可疑报错行集合。
def extract_traceback(log_text: str) -> str:
    index = log_text.rfind("Traceback")
    if index >= 0:
        return log_text[index:]
    lines = log_text.splitlines()
    suspicious = [
        line
        for line in lines
        if any(keyword.lower() in line.lower() for keyword in ERROR_KEYWORDS)
    ]
    return "\n".join(suspicious[-80:])


# 用启发式规则对错误类型做第一轮粗分类。
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
```

## app/prompts/debug_prompt.py

```python
DEBUG_PROMPT = """
你是一个深度学习实验 Debug 助手。

请根据 traceback、repo map 和实验计划，输出错误诊断报告。

要求：
1. 不要只翻译错误，要给出排查顺序。
2. 如果错误栈里出现文件路径，要优先关联 repo 中的文件。
3. 每个修复建议要说明风险。
4. 如果需要修改配置，只生成 proposal，不要直接修改。

错误类型初判：
{error_type}

Traceback：
{traceback}

Repo Map：
{repo_map}

Experiment Plan：
{experiment_plan}
"""
```

## app/schemas.py 增加

```python
class DebugReport(BaseModel):
    error_type: str
    most_likely_causes: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    check_order: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
```

## app/nodes/log_debug_node.py

```python
import json

from app.config import settings
from app.model import get_chat_model
from app.prompts.debug_prompt import DEBUG_PROMPT
from app.schemas import DebugReport
from app.tools.log_tools import classify_error_heuristic, extract_traceback, read_log


# 结合日志、repo map 和实验计划生成结构化调试报告。
def log_debug_node(state: dict) -> dict:
    log_path = state.get("log_path")
    if not log_path:
        return {"error": "log_path is required"}

    log_text = read_log(log_path)
    traceback = extract_traceback(log_text)
    error_type = classify_error_heuristic(traceback)

    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(DebugReport)

    report: DebugReport = structured_llm.invoke(
        DEBUG_PROMPT.format(
            error_type=error_type,
            traceback=traceback,
            repo_map=json.dumps(state.get("repo_map", {}), ensure_ascii=False, indent=2),
            experiment_plan=json.dumps(
                state.get("experiment_plan", {}),
                ensure_ascii=False,
                indent=2,
            ),
        )
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "debug_report.json"
    md_path = settings.output_dir / "debug_report.md"

    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_render_debug_markdown(report), encoding="utf-8")

    return {
        "debug_report": report.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(json_path),
            str(md_path),
        ],
    }


# 将调试报告渲染成便于人工阅读的 markdown 文档。
def _render_debug_markdown(report: DebugReport) -> str:
    lines = ["# Debug Report", "", f"Error Type: `{report.error_type}`", ""]
    sections = [
        ("Most Likely Causes", report.most_likely_causes),
        ("Related Files", report.related_files),
        ("Check Order", report.check_order),
        ("Suggested Fixes", report.suggested_fixes),
        ("Risks", report.risks),
        ("Unresolved Questions", report.unresolved_questions),
    ]
    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("- None")
        else:
            for item in items:
                lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)
```

## 接入 graph router

在 `app/graph.py` 中，先引入节点：

```python
from app.nodes.log_debug_node import log_debug_node

builder.add_node("log_debug", log_debug_node)
builder.add_edge("log_debug", END)
```

然后把 V4 中的 `route_after_plan` 改成：

```python
# 根据是否提供日志路径，决定实验计划后是否进入调试节点。
def route_after_plan(state: ReproductionState) -> str:
    if state.get("log_path"):
        return "log_debug"
    return END
```

这样有日志时进入 `log_debug_node`，没有日志时直接结束。

## 运行方式
```python
python -m app.main run-graph "pdf/Point Spatio-Temporal Transformer Networks.pdf" /data/tianshaoqi24/P4Transformer /tmp/test_oom.log --thread-id debug-001 --goal "复现论文 main result"
```

## 本阶段验收

给定一份真实日志文件，并通过 `log_path` 传入 state，节点从日志中抽取 traceback 后，Agent 输出：

- 错误类型。
- 最可能原因。
- 相关文件。
- 排查顺序。
- 修复建议。
- 哪些操作需要人工确认。

如果后面想扩展成“直接传 traceback 字符串也能分析”，则需要额外增加类似 `traceback_text` 或 `log_text` 的 state 字段，并在 `log_debug_node()` 中增加对应分支。

## 常见坑

- 不要只让 LLM 看错误最后一行，traceback 中间的文件路径很重要。
- shape mismatch 要引导检查数据维度、模型 forward、loss 输入。
- CUDA OOM 的建议要包含 batch size、num_workers、mixed precision、gradient accumulation 等方向，但不要自动改配置。
