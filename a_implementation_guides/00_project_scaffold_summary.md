# 00. 项目脚手架学习总结

## 这一阶段的目标

这一章的重点不是实现复杂的 Agent 能力，而是先把项目的“地基”搭稳：

- 固定项目目录结构，让后续 V0、V1、V2 等阶段都知道代码该放在哪里。
- 准备依赖管理、环境变量、模型封装、数据结构、状态结构和 CLI 入口。
- 保证最小命令可以运行，为后续逐步增加功能留出稳定接口。

简单说，这一阶段解决的是“项目怎么长大才不会乱”的问题。

## 项目目录的分工

推荐目录把核心代码放在 `app/` 下，并提前划分出几个职责区：

- `config.py`：读取 `.env` 里的配置，比如模型、embedding、输出目录、最大步数。
- `model.py`：统一创建聊天模型和 embedding 模型，避免各个节点里到处直接初始化模型。
- `schemas.py`：定义结构化数据模型，比如论文摘要、证据、仓库映射、代码候选等。
- `state.py`：定义整个任务流转时共享的状态字段，为后续 LangGraph 接入做准备。
- `main.py`：提供 CLI 命令入口，方便每个阶段独立演示和测试。
- `nodes/`、`tools/`、`prompts/`、`memory/`、`evaluation/`：预留给后续 Agent 节点、工具、提示词、记忆和评估模块。
- `outputs/`、`data/`、`tests/`：分别存放输出结果、输入数据和测试。

这个结构的好处是：功能还没复杂起来时，边界已经先画好了。

## 依赖管理

`pyproject.toml` 是项目依赖和开发配置的入口。当前阶段需要的核心依赖包括：

- `langchain`：构建 LLM 应用的基础组件。
- `langchain-openai`：对 OpenAI 兼容模型和 embedding 接口进行封装。
- `langgraph`：后续实现图式工作流。
- `pydantic`：定义结构化 schema。
- `typer`：实现命令行入口。
- `rich`：让 CLI 输出更友好。
- `pymupdf`：后续读取 PDF 论文。
- `python-dotenv`：从 `.env` 加载环境变量。

开发依赖里保留 `pytest` 和 `ruff`，分别用于测试和代码风格检查。

## 环境变量配置

`.env.example` 只应该放占位符和默认配置，不应该放真实密钥。真实密钥应该写到本地 `.env`，并避免提交到仓库。

当前配置分成两组：

- 聊天模型：
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `OPENAI_MODEL`
- Embedding 模型：
  - `EMBEDDING_API_KEY`
  - `EMBEDDING_BASE_URL`
  - `EMBEDDING_MODEL`

另外还有项目运行配置：

- `OUTPUT_DIR=outputs`
- `MAX_STEPS=20`

这样做的核心意义是：代码不绑定具体服务商，只要接口兼容，就可以通过环境变量切换模型。

## 配置读取

`app/config.py` 使用 `load_dotenv()` 读取 `.env`，再用 `Settings` 统一保存配置。

这一层的价值是把环境变量访问集中起来。后续代码只需要从 `settings` 里取值，不需要反复写 `os.getenv(...)`。

同时，`settings.output_dir.mkdir(parents=True, exist_ok=True)` 会确保输出目录存在，避免运行时因为目录不存在而失败。

## 模型封装

`app/model.py` 提供两个函数：

- `get_chat_model()`：创建聊天模型，用于后续论文阅读、仓库分析、计划生成等节点。
- `get_embedding_model()`：创建 embedding 模型，用于后续检索、相似度匹配或 RAG。

把模型初始化集中封装的好处是：

- 后续要换模型或 base URL，只改配置层和模型层即可。
- 节点代码不用关心模型细节，只关心“我要一个聊天模型”或“我要一个 embedding 模型”。
- 更方便测试时替换 mock 模型。

## Schema 是项目地基

`app/schemas.py` 定义了后续各阶段会反复使用的数据结构。

几个核心对象：

- `Evidence`：记录证据来源、路径、位置、摘要和置信度。
- `MethodModule`：表示论文里的方法模块。
- `PaperSummary`：表示论文阅读后的结构化摘要。
- `RepoMap`：表示对代码仓库的结构扫描结果。
- `CodeCandidate`：表示某个论文模块可能对应的代码文件或符号。
- `ModuleMapping`：表示论文模块到代码候选的映射。

这一章强调：后续节点尽量返回结构化对象，而不是随手返回字符串。这样项目越做越大时，数据接口仍然清楚。

## State 的作用

`app/state.py` 里的 `ReproductionState` 是整个任务流的共享状态。

它提前列出了后续可能需要保存的信息：

- 用户输入和路径：`user_query`、`paper_path`、`repo_path`、`log_path`。
- 中间结果：`paper_summary`、`repo_map`、`paper_code_mapping`、`experiment_plan`。
- 人类审批：`pending_action`、`requires_approval`、`user_approval`。
- 运行控制：`step_count`、`max_steps`、`error`。
- 输出结果：`output_files`、`final_report`。

V0 到 V3 可以先不真正使用 LangGraph，但提前定义 State 能让 V4 接入 LangGraph 时更自然。

## CLI 入口

`app/main.py` 使用 `typer` 定义命令行入口。

当前阶段只需要两个最小命令：

- `python -m app.main version`
- `python -m app.main init-outputs`

CLI 的意义是让每个阶段都有可运行、可演示、可验收的入口，而不是只有零散函数。

## 本阶段验收标准

这一阶段完成后，至少应该满足：

- 项目目录结构已经创建。
- `.env.example` 使用占位符，没有真实密钥。
- `pyproject.toml` 记录了核心依赖。
- `config.py` 可以正确读取环境变量。
- `model.py` 可以统一创建模型实例。
- `schemas.py` 和 `state.py` 已经定义好核心数据结构。
- `python -m app.main version` 可以输出版本信息。
- `python -m app.main init-outputs` 可以创建或确认 `outputs/` 目录。

## 关键收获

这一章真正要学会的是工程化思维：

- 先定目录边界，再写功能代码。
- 先定结构化数据，再让 Agent 产出内容。
- 先封装模型入口，再在节点里调用。
- 先保留 CLI 验收命令，再逐阶段扩展能力。
- 配置、模型、schema、state、CLI 是后续所有阶段的基础设施。

如果这一阶段做扎实，后面实现论文阅读、仓库扫描、代码映射、实验计划和 LangGraph 工作流时，就不会变成一堆难以维护的脚本。
