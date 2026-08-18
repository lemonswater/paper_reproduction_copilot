# 00. 项目脚手架

## 目标

先把项目骨架搭出来，保证后续每个阶段都能按固定位置添加代码。这个阶段不追求 Agent 智能，只追求目录清晰、数据结构稳定、命令可运行。

## 建议目录

```text
paper_reproduction_copilot/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── model.py
│   ├── schemas.py
│   ├── state.py
│   ├── graph.py
│   ├── nodes/
│   │   └── __init__.py
│   ├── tools/
│   │   └── __init__.py
│   ├── prompts/
│   │   └── __init__.py
│   ├── memory/
│   │   └── __init__.py
│   └── evaluation/
│       └── __init__.py
├── outputs/
├── tests/
├── data/
├── .env.example
├── pyproject.toml
└── README.md
```

## pyproject.toml 参考

```toml
[project]
name = "paper-reproduction-copilot"
version = "0.1.0"
description = "A LangGraph-based copilot for paper reproduction tasks."
requires-python = ">=3.10"
dependencies = [
    "langchain>=0.3",
    "langchain-openai>=0.2",
    "langgraph>=0.2",
    "pydantic>=2",
    "typer>=0.12",
    "rich>=13",
    "pymupdf>=1.24",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "ruff>=0.6",
]

[tool.ruff]
line-length = 100
```

## .env.example 参考

```text
OPENAI_API_KEY=your_openai_compatible_api_key
OPENAI_BASE_URL=https://api.xiaomimimo.com/v1
OPENAI_MODEL=mimo-v2.5-pro

EMBEDDING_API_KEY=your_embedding_api_key
EMBEDDING_BASE_URL=https://tokendance.space/gateway/v1
EMBEDDING_MODEL=qwen-text-embedding-v4

OUTPUT_DIR=outputs
MAX_STEPS=20
```

## app/config.py

```python
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    openai_model: str = os.getenv("OPENAI_MODEL", "mimo-v2.5-pro")
    embedding_api_key: str | None = os.getenv("EMBEDDING_API_KEY")
    embedding_base_url: str | None = os.getenv("EMBEDDING_BASE_URL")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "qwen-text-embedding-v4")
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
    max_steps: int = int(os.getenv("MAX_STEPS", "20"))


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
```

## app/model.py

这里先封装模型获取函数，后续节点不要直接散落初始化模型的代码。

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings


# 统一创建聊天模型实例，供各个节点复用。
def get_chat_model(temperature: float = 0):
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=temperature,
    )


# 统一创建 embedding 模型实例，供检索或向量化任务使用。
def get_embedding_model():
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
    )
```

## app/schemas.py

结构化 schema 是项目的地基。后续所有节点尽量返回这些对象，而不是随手返回字符串。

```python
from typing import Literal

from pydantic import BaseModel, Field


Confidence = Literal["low", "medium", "high"]


class Evidence(BaseModel):
    source_type: Literal["paper", "code", "readme", "config", "log"]
    source_path: str
    location: str | None = None
    quote_or_summary: str
    confidence: Confidence = "medium"


class MethodModule(BaseModel):
    name: str
    description: str
    possible_keywords: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)


class PaperSummary(BaseModel):
    title: str | None = None
    research_problem: str
    core_idea: str
    method_modules: list[MethodModule] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    experiment_settings: dict = Field(default_factory=dict)
    reproduction_risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


class RepoMap(BaseModel):
    repo_path: str
    readme_files: list[str] = Field(default_factory=list)
    train_entries: list[str] = Field(default_factory=list)
    eval_entries: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    model_files: list[str] = Field(default_factory=list)
    dataset_files: list[str] = Field(default_factory=list)
    loss_files: list[str] = Field(default_factory=list)
    important_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CodeCandidate(BaseModel):
    file_path: str
    symbols: list[str] = Field(default_factory=list)
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence = "medium"


class ModuleMapping(BaseModel):
    module_name: str
    candidates: list[CodeCandidate] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
```

## app/state.py

V0 到 V3 可以先不用 LangGraph，但先把 State 定义好。V4 接入 LangGraph 时直接复用。

```python
from typing import Any, Optional, TypedDict


class ReproductionState(TypedDict, total=False):
    task_id: str
    user_query: str
    paper_path: Optional[str]
    repo_path: Optional[str]
    log_path: Optional[str]
    experiment_goal: Optional[str]

    paper_text_chunks: list[dict[str, Any]]
    paper_summary: dict[str, Any]
    method_modules: list[dict[str, Any]]
    repo_map: dict[str, Any]
    paper_code_mapping: list[dict[str, Any]]
    experiment_plan: list[dict[str, Any]]
    debug_report: dict[str, Any]

    pending_action: Optional[dict[str, Any]]
    requires_approval: bool
    user_approval: Optional[str]

    output_files: list[str]
    final_report: Optional[str]
    messages: list[dict[str, Any]]
    step_count: int
    max_steps: int
    error: Optional[str]
```

## app/main.py

先准备 CLI 框架。每个阶段新增一个命令，方便演示和测试。

```python
from pathlib import Path

import typer
from rich import print


app = typer.Typer(help="Paper Reproduction Copilot")


# 输出项目版本信息，便于检查 CLI 是否可正常运行。
@app.command()
def version():
    print("[green]paper-reproduction-copilot 0.1.0[/green]")


# 初始化 outputs 目录，保证后续阶段有固定输出位置。
@app.command()
def init_outputs():
    Path("outputs").mkdir(exist_ok=True)
    print("[green]outputs/ is ready[/green]")


if __name__ == "__main__":
    app()
```

## 本阶段验收

```bash
python -m app.main version
python -m app.main init-outputs
```

能正常输出即可进入 V0。
