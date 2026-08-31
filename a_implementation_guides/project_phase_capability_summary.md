# 论文复现 Agent 全阶段功能与技术总览

> 最后同步日期：2026-08-19
>
> 当前代码基线：基础 00、V0-V7 以及 Phase 1 至 Phase 56 的核心能力已有源码实现。Phase 46
> 的 Identity、Repository、Evidence、Service 四组 44 个用例已通过执行进度点；API/Chat/Retention/
> Authority 集成组在本次文档同步时未取得完整退出结果，仍需单独复核。Phase 40
> Tool Contract 专项测试为 27 passed；Phase 41 已包含加密 Store、版本化 Reference、
> 用途约束、统一 Redactor、泄漏 Scanner、Doctor、CLI 与主要运行边界接线，Secret 专项和
> Container Plan 回归合计 101 passed（Python 3.10.20）。Phase 42 已将 Secret Redactor
> 接入 Chat Service，并完成对话只读边界、操作意图、stale/hash、幂等与 Safety Gate
> 回归；本次复核相关专项测试为 12 passed（Python 3.10.20）。Phase 43 的 Authority、Evidence、
> Execution/Patch Verifier、Graph Route 与 Import Boundary 专项测试为 26 passed（Python 3.10.20）。
> Phase 44 的通知 Repository、Projector、Service、Retention 和 SQLite Job Event Cursor 专项测试
> 为 26 passed（Python 3.10.20）。Phase 45 的 Identity、Repository、Evidence Reader、Retriever、
> Retention 和 Authority Boundary 实际 6 个专项测试文件为 22 passed（Python 3.10.20）。
> Phase 47 的确定性检索策略、shadow/active 路由和 Golden Promotion 专项测试为 11 passed；
> Phase 48 的 Skill Loader、Restricted Runtime、Registry、CUDA Diagnosis、Authority、Golden、Import
> Boundary 和 Debug 接线实际 8 个专项测试文件为 23 passed（Python 3.10.20）。Phase 49 的
> Evidence Graph、SQLite Repository、Relation Governance、Chat/Retention 接线和 Golden Eval 已实现，
> 本次复核 11 个专项测试文件共 19 passed。Phase 50 源码已实现；本次复核在 API 测试前已有 68 passed，
> Eval/Authority 两组另有 21 passed，API 组未取得完整退出结果。Phase 51 本次复核 13 个非 API 专项文件
> 共 112 passed；`tests/test_research_browser_api.py` 在当前 Python 3.9 环境首个用例超过 30 秒未结束，仍需
> 在项目 Python 3.10 环境收口 API 验证。Phase 52 已按教程实现，本次 Tool Calling、Chat、Model Gateway、
> Authority 和 Tool Registry 相关专项回归共 51 passed。Phase 53 的 MCP Gateway Schema、Policy、Repository、
> Gateway、Authority 及 Phase 52 回归共 40 passed。Phase 54 核心源码已经实现。当前环境已安装 MCP SDK；
> Phase 55 的 Surface Snapshot、Profile、Candidate/Baseline、Golden Eval 与 Readiness 已实现，九组专项测试
> 实测 `26 passed in 6.05s`。但最终 Baseline 尚未纳入 loopback HTTP，且 Phase 54 的真实 `tools/call`
> 相邻测试仍会长时间不结束。Phase 56 的有界业务调用、三 Profile 六操作 Runtime SLO 和 SDK 升级演练源码已经实现，真实 HTTP
> tools/call 的完整运行门禁仍需结合专项测试和 Runtime Report 持续复核。
>
> 本文是持续维护文档。后续每完成或调整一个 Phase，必须同步更新对应阶段的状态、功能、技术、
> 核心思路、流程和关键产物。

---

## 一、项目总体定位

本项目是一个面向论文复现任务的工程化 Agent。它不只是调用 LLM 生成摘要，而是把论文理解、
代码检索、实验规划、安全执行、故障诊断、人工审批、文件修复、持久化、Web 交互和证据追踪
组织成一条可恢复、可审计的工作流。

当前主要流程为：

```text
论文 / 仓库 / 数据集 / 日志
  -> 输入验证与不可变 Workspace
  -> 论文结构解析与 Evidence 抽取
  -> 仓库扫描与混合代码检索
  -> 论文模块和代码证据映射
  -> 结构化实验计划
  -> 命令选择与用户编辑
  -> Action 构建、Hash、风险与能力策略
  -> Human Review
  -> Preflight、Smoke Test、受监管执行
  -> 失败诊断与有界修复
  -> Patch 两阶段审批、隔离验证与应用
  -> Final Report、Run Manifest、Artifact Publication
  -> Job / Event / Checkpoint / Chat / Comparison / Rerun
  -> Tool Contract / Secret Reference / Redaction / Leak Scan
  -> Conversation Decision Eval / Permission Boundary Safety Gate
  -> Failure / Project Memory + Adaptive Retrieval Policy
  -> Restricted Agent Skill / Plugin Runtime
  -> Cross-Paper Evidence Knowledge Base
  -> Future Model Routing / Cost Budget / Provider Governance
```

系统同时包含五个平面：

| 平面 | 主要职责 | 关键模块 |
|---|---|---|
| Agent 工作流 | 理解、规划、路由、诊断、验证 | `app/graph.py`、`app/nodes/` |
| 执行数据面 | Workspace、进程、容器、资源和 Artifact | `app/execution/`、`app/workspace/`、`app/storage/` |
| 持久化控制面 | Job、Checkpoint、Lease、Event、Decision | `app/job_runtime/`、`app/persistence/`、`app/interaction/` |
| 用户交互面 | CLI、API、Web、Chat、预览和导出 | `app/main.py`、`app/api/`、`app/chat/` |
| 安全治理面 | Tool Contract、Secret 生命周期、脱敏和泄漏扫描 | `app/tool_contract/`、`app/secrets/` |

---

## 二、核心技术栈

| 技术 | 在项目中的用途 |
|---|---|
| Python 3.10+ | 主开发语言和执行运行时 |
| Pydantic v2 | State、Action、Artifact、Job、Chat、Tool Contract 等结构化契约 |
| LangChain | 模型 Provider 接入和 Structured Output |
| LangGraph | 状态图、条件路由、Interrupt、Checkpoint 与 Resume |
| Typer + Rich | CLI、人工审批和调试输出 |
| FastAPI + SSE | Job、Decision、Chat、Artifact 和事件流 API |
| SQLite | 单机 Job、Checkpoint、Chat、Retention、Embedding Cache 等持久化 |
| Fernet + HMAC-SHA256 | 本地 Secret 认证加密、版本 Fingerprint 和引用完整性 |
| PostgreSQL + SQLAlchemy/Alembic | 共享控制面、并发 Claim、Artifact Metadata 和生产迁移 |
| Local/S3 Blob Store | 内容寻址 Artifact 和跨 Worker 发布 |
| PyMuPDF | PDF block、字体、坐标和页码解析 |
| ripgrep + AST | 精确文本检索和 Python 符号抽取 |
| Embedding + Cosine/RRF | Dense、Lexical 和 Hybrid Evidence Retrieval |
| subprocess + psutil | 受监管进程、取消、超时、日志和资源限制 |
| Podman/OCI | 单主机强隔离和不可变运行环境身份 |
| OpenTelemetry | Trace、Metric、结构化日志和跨组件关联 |
| pytest + Ruff | 单元、契约、集成、故障注入和静态回归 |

---

## 三、基础阶段：00 与 V0-V7

### 00：项目脚手架

- **状态**：已实现。
- **实现功能**：建立目录结构、依赖、配置、模型入口、Schema、State 和基础 CLI。
- **所用技术**：`pyproject.toml`、dotenv、Pydantic、Typer、LangChain Provider 封装。
**核心思路**

这一阶段先建立“稳定内核”，而不是立即堆叠 Agent 节点。配置读取、模型创建、数据结构和命令入口都集中在固定模块中，上层节点只依赖这些抽象，不直接读取散落的环境变量，也不各自实例化 Provider。这样后续替换模型、增加字段或迁移运行方式时，变更能够收敛在边界层，而不会扩散到整张 Graph。

Schema 和 State 在这里承担跨阶段协议的作用：Schema 描述某类数据是否合法，State 描述节点之间允许共享哪些事实。先定义契约再实现行为，可以尽早暴露字段缺失、类型漂移和依赖反转问题，也为后续结构化输出、Checkpoint、API 和持久化复用同一套语义打下基础。

**实现流程**

1. 在 `pyproject.toml` 中固定运行依赖、开发依赖和 CLI 入口，形成可重复安装的项目骨架。
2. 从 `.env` 和环境变量加载配置，由 `settings` 统一完成类型转换、默认值和必填项校验。
3. 通过模型 Factory 根据配置创建 Chat Model，节点只请求模型能力，不感知具体 Provider 初始化细节。
4. 在 `schemas.py` 中定义领域对象，在 `state.py` 中定义 Graph 共享状态及字段合并方式。
5. 由 `main.py` 暴露最小 CLI，将输入解析后交给应用层函数，而不是把业务逻辑写进命令函数。
6. 用最小启动测试验证配置、模型工厂、Schema 导入和 CLI 帮助信息能够正常工作。
- **关键文件**：`app/config.py`、`app/model.py`、`app/schemas.py`、`app/state.py`、`app/main.py`。

### V0：论文结构化阅读

- **状态**：已实现，后续已被 Phase 18/19 增强。
- **实现功能**：读取 PDF/文本、切分内容、抽取论文摘要和方法模块。
- **所用技术**：PyMuPDF、文本 Chunk、Prompt、Pydantic Structured Output。
**核心思路**

论文原文长度大、章节组织复杂，不能把整篇文本作为一个无边界 Prompt 后直接相信模型回答。本阶段先把输入变成有大小限制的文本块，再要求模型返回 `PaperSummary`、方法模块等结构化对象，让“论文理解结果”从一次性自然语言回答升级为可被后续节点读取、校验和持久化的数据资产。

结构化输出并不意味着模型天然可靠。Prompt 负责说明任务和字段含义，Pydantic 负责检查字段是否存在、类型是否正确，本地代码再把通过校验的对象同时渲染为 JSON 和 Markdown。JSON 面向机器消费，Markdown 面向人工检查，两者来自同一对象，避免两套结果逐渐不一致。

**实现流程**

1. 校验论文路径和文件类型，并通过 reader 提取 PDF 或文本内容。
2. 按长度和语义边界切分论文，限制单次模型调用的上下文规模。
3. 将当前文本块填入 Prompt，调用带 `PaperSummary` 等 Schema 的 Structured Output 模型。
4. 使用 Pydantic 校验必填字段、列表元素和嵌套对象，解析失败时保留原始响应以便诊断。
5. 汇总各文本块的信息，消除明显重复并形成稳定的论文摘要与方法模块对象。
6. 将对象写成 JSON Artifact，同时生成便于学习和审阅的 Markdown Artifact。
- **关键产物**：`paper_summary.json`、`method_modules.json`。

### V1：代码仓库地图

- **状态**：已实现。
- **实现功能**：构建目录树、枚举文件、识别训练/评估/配置/模型/数据集文件。
- **所用技术**：`pathlib`、文件过滤、AST、启发式分类。
**核心思路**

直接让模型阅读整个仓库既昂贵又容易遗漏入口文件。本阶段先用确定性工具建立仓库地图，把目录、文件类型、训练入口、配置、模型、数据集和扩展模块组织成紧凑索引。这个索引不是对代码语义的最终解释，而是后续检索和推理的搜索空间边界。

扫描优先使用文件系统、后缀规则和 AST 等可重复方法，LLM 只在需要自然语言总结时参与。这样即使模型更换，仓库中“有哪些文件、哪些符号、入口在哪里”仍保持稳定，并且每个结论都能回到真实路径验证。

**实现流程**

1. 解析并规范化仓库根目录，拒绝不存在、越界或不是目录的输入。
2. 按忽略规则遍历文件树，跳过 `.git`、缓存、构建产物和超大文件等噪声。
3. 根据路径、后缀、文件名和 Python AST 提取文件类别、入口脚本与主要符号。
4. 将扫描结果组装成 `RepoMap`，保留路径、类别和必要的统计信息。
5. 从 `RepoMap` 生成面向机器的 JSON 和面向用户的仓库摘要。
6. 后续检索节点只在地图确认的仓库边界内读取文件和代码片段。
- **关键产物**：`repo_map.json`、`repo_summary.md`。

### V2：论文与代码证据化映射

- **状态**：已实现，后续已被 Phase 20/21 增强。
- **实现功能**：检索论文模块候选代码，生成带 Evidence 的论文代码映射。
- **所用技术**：ripgrep、代码片段、Pydantic、LLM Evidence Reasoning。
**核心思路**

论文模块名称和代码标识符往往不完全一致，但这不等于应让模型自由浏览并猜测。本阶段采用“候选召回在前、语义判断在后”的方式：先从论文方法模块生成检索目标，利用路径、关键词和符号找到候选，再只把有限代码片段交给模型判断对应关系。

映射结果必须携带文件路径、行号或代码片段等 Evidence。模型可以解释“为什么这个实现对应论文模块”，但不能创造不存在的文件或符号。证据化设计既减少上下文，也让人工能够复核错误映射，并为后续混合检索和引用校验提供统一接口。

**实现流程**

1. 从方法模块中提取名称、关键操作、输入输出和可能的实现术语。
2. 在 `RepoMap` 限定的路径内执行关键词、文件名和符号检索，生成初始候选。
3. 为候选读取带行号的有限代码窗口，拒绝把整个仓库无边界发送给模型。
4. 将论文模块描述和候选证据交给 Structured Output 模型生成映射草稿。
5. 本地校验映射引用的路径、行号和候选身份确实存在，并记录置信度与不确定项。
6. 输出 JSON 映射供规划节点使用，并生成 Markdown 版本供人工核对。
- **关键产物**：`paper_code_mapping.json`、`paper_code_mapping.md`。

### V3：复现实验计划

- **状态**：已实现。
- **实现功能**：生成环境、数据、训练、评估步骤和候选运行命令。
- **所用技术**：`ExperimentPlan`、`ExperimentStep`、Structured Output、Prompt 约束。
**核心思路**

论文摘要和代码映射回答“是什么、在哪里”，实验计划还要回答“按什么顺序、在什么环境、执行哪些步骤”。本阶段把已有证据转换成 `ExperimentPlan`，明确环境准备、数据准备、编译、训练和评估步骤，使计划能够被后续 Action Builder 消费，而不只是供人阅读的一段建议。

计划仍然只是 Proposal，不拥有执行权限。每条命令要保留来源、工作目录、风险和未确认参数，占位符不能被伪装成可直接执行的真实值。通过这种区分，模型负责组织候选方案，后续确定性节点和用户负责选择、补全、审批与执行。

**实现流程**

1. 汇总论文摘要、方法模块、仓库地图和论文代码映射，形成规划所需的最小证据集。
2. 在 Prompt 中明确 `ExperimentPlan` 字段、步骤顺序、命令格式和禁止虚构的约束。
3. 调用 Structured Output 模型生成环境、数据、训练、评估步骤及候选 `run_commands`。
4. 使用 Pydantic 校验步骤类型、命令字段和嵌套结构，并对占位符与风险做本地检查。
5. 将计划保存为 JSON，作为后续命令选择和 Action Builder 的唯一结构化输入。
6. 从同一对象渲染 Markdown，展示证据来源、未决参数和人工需要确认的事项。
- **关键产物**：`experiment_plan.json`、`experiment_plan.md`。

### V4：LangGraph、Checkpoint 与 Memory

- **状态**：已实现，后续升级为 Durable/Shared Checkpoint。
- **实现功能**：把线性 CLI 改造成 StateGraph，支持 `thread_id`、状态读取和恢复。
- **所用技术**：LangGraph `StateGraph`、条件边、SQLite Checkpointer。
**核心思路**

线性脚本只能从头执行，无法自然表达条件分支、人工暂停和失败恢复。本阶段将节点组织成 `StateGraph`：节点读取当前 State 并返回增量更新，条件边根据确定性状态选择下一步。Graph 因而成为工作流控制结构，而不是一串隐式函数调用。

State、Checkpoint 和 Artifact 的职责必须分开。State 保存当前图运行需要共享的事实，Checkpoint 保存某个 `thread_id` 的执行位置和可恢复状态，Artifact 保存可长期检查的业务结果。`show-state` 没有读到内容时，应检查是否使用了同一个 checkpointer、数据库和 thread identity，而不是从输出目录反推图状态。

**实现流程**

1. 定义 Graph State，明确每个字段由哪些节点读取、写入以及如何合并。
2. 将论文读取、仓库扫描、映射和规划函数包装成节点，并注册到 `StateGraph`。
3. 配置普通边和条件边，使成功、失败、等待审批等状态走向明确节点。
4. 使用持久化 checkpointer 编译 Graph，并将稳定 `thread_id` 放入 configurable 配置。
5. 调用 Graph 后由 checkpointer 在关键步骤保存 snapshot，Artifact 仍独立写入 Run 目录。
6. 通过 `show-state` 读取同一身份的 snapshot，必要时使用 resume 从中断点继续。
- **关键入口**：`run-graph`、`show-state`、`resume-review`。

### V5：日志 Debug

- **状态**：已实现，后续接入结构化错误、检索和修复链。
- **实现功能**：读取执行日志、提取 traceback、分类错误并生成 DebugReport。
- **所用技术**：日志裁剪、规则分类、LLM Structured Output、Artifact。
**核心思路**

失败诊断最重要的是证据保真。若先让模型概括再保存日志，关键 traceback、退出码或环境信息可能被丢失。因此本阶段先把原始日志作为 Artifact 保存，再用确定性规则提取 traceback、错误类型和末尾窗口，最后让模型基于有限证据提出原因与建议。

诊断结果是解释和下一步建议，不等于已经完成修复。它需要保留对应日志路径、错误片段和置信信息，使后续 Repair Proposal 能说明自己依据了什么，也使用户可以在模型判断错误时回到原始输出核查。

**实现流程**

1. 执行节点记录退出码、标准输出、标准错误和日志文件身份。
2. 失败时先固定原始日志 Artifact，避免后续裁剪覆盖唯一证据。
3. 从日志中提取 traceback、异常类型、关键上下文和受长度限制的尾部窗口。
4. 使用规则识别常见依赖、路径、参数、CUDA 和程序异常，再决定是否需要 LLM 诊断。
5. 将结构化错误证据交给模型生成原因、影响和候选解决方向，并用 Schema 校验。
6. 输出 `debug_report.json` 与 `debug_report.md`，供人工审阅或后续有界修复节点使用。
- **关键产物**：`debug_report.json`、`debug_report.md`。

### V6：Human-in-the-loop

- **状态**：已实现并多次强化。
- **实现功能**：高风险 Action 中断、人工批准/拒绝、恢复执行。
- **所用技术**：LangGraph `interrupt()`、`Command(resume=...)`、Approval Record。
**核心思路**

Agent 能生成命令并不意味着它有权执行命令。本阶段在 Proposal 与 Execution 之间加入明确的人工控制点：风险策略先判断动作是否需要审批，高风险动作通过 `interrupt()` 暂停并把完整上下文展示给用户，用户的决定再通过 `Command(resume=...)` 返回 Graph。

审批必须绑定动作内容，而不能只记录一个孤立的 `approved=True`。虽然最初版本主要建立中断恢复机制，后续阶段又补充 Action Hash、Version 和 stale 校验，但核心原则从这里确立：模型提出候选，确定性策略约束范围，用户拥有最终授权，执行器只接受完整有效的批准记录。

**实现流程**

1. 上游节点生成待执行 Action，并保留命令、工作目录、来源和风险信息。
2. Risk Check 使用确定性规则判定动作是否可直通、需要审批或必须拒绝。
3. 需要人工处理时调用 `interrupt()`，将审批卡片写入 Checkpoint 后暂停 Graph。
4. CLI 或 API 展示动作和风险，用户明确选择批准、拒绝或后续支持的编辑操作。
5. `Command(resume=decision)` 将决定送回原节点，本地代码校验决定结构及其适用对象。
6. 有效批准进入执行路径，拒绝或无效决定进入受控终态并保留审计记录。

### V7：Evaluation 与 Packaging

- **状态**：已实现，后续升级为 Phase 17/37 回归体系。
- **实现功能**：提供基础评测集、评分、报告和项目运行打包方式。
- **所用技术**：pytest、JSON Case、离线/Provider 分层、Typer。
**核心思路**

一次端到端运行成功只能说明某个样例在某次环境中通过，不能证明 Agent 能力稳定。本阶段建立最早的 Evaluation 骨架，把输入样例、期望结果、实际观察和评分逻辑分开，让行为变化能够被重复执行和比较。

离线测试优先验证 Schema、路由、安全边界等确定性能力，Provider 测试再验证真实模型表现。Packaging 则确保相同入口、依赖和配置能在不同环境复现评测，避免“功能正常”仅成立于开发者当前终端。

**实现流程**

1. 用 JSON 或 Python Fixture 描述输入、期望字段和允许的误差边界。
2. Case Loader 将样例解析成统一评测对象，并在运行前校验格式。
3. Runner 调用目标节点或工作流，收集原始输出、结构化结果和错误信息。
4. Observation 层把不同实现结果投影成统一可评分字段。
5. Scorer 计算正确性、完整性或安全性指标，并与阈值进行比较。
6. 汇总生成 Eval Report，并通过 pytest 或 CLI 作为后续变更的回归入口。

---

## 四、端到端执行闭环：Phase 1-9

### Phase 1：Action Builder

- **状态**：已实现。
- **实现功能**：把首个 `run_command` 转换为 `pending_action`。
- **技术**：命令解析、Pydantic `ExecutableAction`、Graph Node。
**核心思路**

`ExperimentPlan` 面向规划，可能包含多条候选命令、说明文字和尚未补全的参数；执行层需要的却是单一、明确、可校验的动作。本阶段引入 Action Builder 作为语义边界，把“建议做什么”转换成 `ExecutableAction`，并统一命令、参数、工作目录、来源和风险字段。

Action Builder 不负责审批，也不直接启动进程。它只构造待审对象并拒绝明显无效的计划，例如没有候选命令、索引越界或命令无法解析。这样 Risk Check、Human Review 和 Executor 都围绕同一种动作协议工作，避免各节点重复理解自然语言计划。

**实现流程**

1. 从 Graph State 读取通过 Schema 校验的 `ExperimentPlan` 和候选 `run_commands`。
2. 按默认规则或用户选择确定一个候选命令，缺失候选时返回结构化失败状态。
3. 解析命令文本，将可执行程序与参数转成明确结构，并规范化 `cwd`。
4. 构造 `ExecutableAction`，附带来源、理由、风险等级和必要的上下文身份。
5. 将动作写入 `pending_action`，但不设置任何批准或执行成功标记。
6. Graph 将结构化动作交给 Risk Check，进入后续策略与审批流程。

### Phase 2：Executor

- **状态**：已实现。
- **实现功能**：审批后执行命令，记录退出码、输出和状态。
- **技术**：`subprocess`、`shell=False`、Runner 抽象。
**核心思路**

执行器是最需要缩小输入面的节点。命令首先被解析为参数列表，再以 `shell=False` 交给进程 API，从而避免管道、重定向、命令替换和环境展开被 Shell 隐式解释。工作目录通过 `cwd` 参数传递，而不是依赖 `cd ... && ...` 修改当前 Shell 状态。

Executor 只消费已经满足执行条件的结构化 Action，并将进程结果重新转换成结构化状态。标准输出、标准错误、退出码和日志路径都是事实，不由模型判断；退出码为零也只表示进程协议成功，是否达到论文目标要由后续报告或评测解释。

**实现流程**

1. 从 State 读取 `pending_action`、审批状态和风险策略结果，缺少任一必要条件时拒绝执行。
2. 校验可执行程序、参数列表和工作目录，确保它们符合 Action Schema 与路径边界。
3. 通过 Runner 抽象以 `shell=False` 启动子进程，并显式传入 `cwd` 和受控环境变量。
4. 捕获标准输出、标准错误、退出码和执行异常，避免异常直接破坏 Graph 状态。
5. 将结果写为统一 execution result，并根据退出码设置 `succeeded` 或受控失败状态。
6. 把日志和结果交给后续 Final Report 或 Fail-to-Debug 路由处理。

### Phase 3：Fail-to-Debug

- **状态**：已实现。
- **实现功能**：论文程序执行失败后自动进入诊断，而 Agent 自身故障保持终止。
- **技术**：条件路由、错误分类、日志 Artifact。
**核心思路**

“执行失败”至少有两种完全不同的含义：论文仓库中的训练程序正常启动后返回非零退出码，属于被复现程序失败；节点自身出现类型错误、状态缺失或 Provider 异常，则属于 Agent 实现或基础设施失败。若两者走同一路由，Agent 可能把自己的 bug 错当成论文问题并生成误导性修复。

本阶段因此根据错误来源和已有证据做确定性分流。论文程序失败通常拥有 stdout、stderr 和 exit code，可以进入日志诊断；Agent 内部错误应形成 terminal error，保留 traceback 并停止自动动作。成功路径也显式进入最终报告，确保每个终态都有稳定出口。

**实现流程**

1. Executor 返回统一结果，其中明确包含启动是否成功、退出码、日志和错误来源。
2. 路由函数先判断 Agent 节点是否发生内部异常或状态契约错误。
3. 若是 Agent/Provider/环境级 terminal error，则保存错误证据并停止自动诊断链。
4. 若子进程成功且退出码为零，则进入 `final_report` 汇总成功事实。
5. 若论文程序返回非零退出码且日志可用，则进入 `log_debug` 提取和分析错误证据。
6. 诊断完成后再进入最终报告，确保失败也能形成可读、可追踪的结果。

### Phase 4：Final Report 与 Eval

- **状态**：已实现。
- **实现功能**：统一终态报告，并让评测覆盖完整主流程。
- **技术**：Markdown Renderer、Artifact Index、pytest Scorer。
**核心思路**

工作流终止不等于用户已经得到答案。用户需要知道做了什么、执行了哪条命令、在哪一步停止、产生了哪些文件以及下一步可以如何处理。本阶段将成功、被拒绝、环境阻断和执行失败统一投影到 Final Report，避免只有成功路径生成报告。

报告只总结 State 和已验证 Artifact 中存在的事实，不重新让模型发明执行结果。评测层则从同一终态对象构造 Observation，使“用户看到的结果”和“自动评分读取的结果”来自一致的数据源。

**实现流程**

1. 收集当前 Run 的论文分析、计划、Action、审批、执行结果、错误和 Artifact 索引。
2. 根据终态类型选择报告段落，明确区分成功、拒绝、阻断和失败。
3. 对引用的文件和日志进行存在性检查，不把缺失路径渲染成有效产物。
4. 以确定性模板生成 `final_report.md`，并在需要时生成结构化报告对象。
5. 将报告登记到 Artifact Index 和输出文件列表，纳入 Run 生命周期。
6. 由 Eval Adapter 将终态事实转换成 Observation，交给 Scorer 计算闭环指标。

### Phase 5：Durable Checkpoint 与 Resume

- **状态**：已实现。
- **实现功能**：跨进程持久恢复中断状态。
- **技术**：LangGraph SQLite Checkpointer、稳定 `thread_id`、连接生命周期。
**核心思路**

内存 Checkpoint 只能在同一 Python 进程中恢复，无法支撑用户关闭 CLI 后再审批。本阶段使用 SQLite 持久化 Graph snapshot，使 `interrupt()` 后的 State、下一节点和任务配置能够跨进程保留。恢复的关键不是重新运行相同命令，而是定位同一个持久化线程。

因此数据库路径、Graph 定义、checkpointer 生命周期和 `thread_id` 必须保持一致。若运行命令和 `show-state` 各自创建内存 checkpointer，或恢复时改变 thread identity，就会出现“图跑过但状态为空”。持久恢复同时要求节点具备幂等意识，不能在 resume 时重复执行中断前已完成的副作用。

**实现流程**

1. 在稳定路径创建 SQLite Checkpoint 数据库，并在 Graph 生命周期内保持连接有效。
2. 使用该 checkpointer 编译唯一 Graph，运行时传入稳定的 `thread_id`。
3. Graph 执行到 `interrupt()` 时写入 State、next node 和中断 payload，然后安全退出当前调用。
4. CLI 的 `show-state` 使用同一数据库与 `thread_id` 读取 `StateSnapshot`，展示等待状态。
5. 新进程收到用户决定后，以相同 configurable identity 调用 `Command(resume=...)`。
6. Graph 从保存位置继续，并通过状态标记避免重放已经完成的外部副作用。

### Phase 6：Structured Action 与 Approval Hash

- **状态**：已实现。
- **实现功能**：结构化 Action、Approval Record 和内容 Hash，拒绝旧审批执行新动作。
- **技术**：Pydantic、规范 JSON、SHA-256、Optimistic Concurrency。
**核心思路**

仅保存 `approved=True` 存在时间差风险：用户审批动作 A 后，State 中的 `pending_action` 可能因为编辑、恢复错误或并发更新变成动作 B，而 Executor 仍沿用旧批准。为避免批准与实际执行对象错位，本阶段为结构化 Action 计算规范化内容 Hash，并把它写入 Approval Record。

Hash 不是权限本身，而是把权限绑定到具体内容的身份凭据。计算前必须对字段和 JSON 序列化方式做规范化，Executor 在最后一刻重新计算当前动作 Hash；任何命令、参数、目录或关键属性变化都会导致不匹配，并以 `stale_approval` 失败关闭。

**实现流程**

1. 将候选命令解析为字段明确的 `ExecutableAction`，避免审批对象仍是松散字符串。
2. 对动作执行稳定字段排序和规范 JSON 序列化，排除非业务性的随机表示差异。
3. 计算 SHA-256 Action Hash，并在展示审批卡片时同时展示动作内容。
4. 用户批准后创建 `ApprovalRecord`，记录 decision、action hash、时间和必要身份。
5. Executor 读取当前 `pending_action` 后重新计算 Hash，并与 Approval Record 比较。
6. Hash 一致才允许执行；不一致时返回 `stale_approval`，要求基于新动作重新审批。

### Phase 7：Command Selection 与可编辑命令

- **状态**：已实现。
- **实现功能**：显示候选命令、用户选择索引并修改一个或多个命令。
- **技术**：LangGraph Interrupt、Command Hash、JSON 编辑模板。
**核心思路**

论文仓库往往提供多条训练、评估或扩展编译命令，模型无法知道用户当前拥有哪个数据集、希望先验证哪条路径。本阶段在规划与 Action Builder 之间增加命令选择中断：终端展示所有候选及其目录、来源和风险，由用户选择索引，并可对一条或多条候选命令进行修改。

编辑不是直接修改待执行进程，而是产生一组新的结构化候选。系统重新校验索引、命令和 Hash，随后才把选中项交给 Action Builder。这保证用户拥有最终控制权，同时保留模型原始建议和修改后的可审计差异。

**实现流程**

1. 从 `ExperimentPlan` 读取所有 `run_commands`，为每条命令分配稳定索引并展示元数据。
2. 通过 `interrupt()` 暂停 Graph，等待用户提交选择索引和可选的命令编辑集合。
3. 校验决定结构、候选列表版本和每个编辑索引，拒绝越界、空命令或过期提交。
4. 对指定候选应用编辑，同时保留未修改候选及原始来源信息。
5. 重新计算候选集合或选中命令的内容身份，将选择结果写入 State。
6. Action Builder 只消费最终选中的结构化命令，之后重新进行风险判断和审批。

### Phase 8：Run Manifest 与 Artifact 分层

- **状态**：已实现。
- **实现功能**：每次任务使用独立 Run 目录，区分 analysis/planning/execution/report。
- **技术**：内容 Hash、Artifact Record、Manifest、原子写入。
**核心思路**

所有执行都写到共享 `outputs/` 会造成覆盖、串读和无法判断文件来源。本阶段引入 Run 身份和分层目录，使每次工作流拥有独立的 analysis、planning、execution、repair 和 report 空间。Artifact 不只是路径，还应带有类型、Hash、创建阶段和相对位置等元数据。

Run Manifest 是本次运行的总索引，它描述输入身份、阶段状态和产物集合，但不替代文件内容。通过原子写入和内容 Hash，后续 API、比较、发布和 GC 可以先验证 Manifest，再访问对应 Artifact，避免依赖约定俗成的文件名猜测。

**实现流程**

1. 在任务开始时生成稳定 `run_id`，创建该 Run 独占的目录布局。
2. 各节点通过统一路径辅助函数选择所属层级，不再直接拼接全局 `outputs/`。
3. 写入 Artifact 时计算大小、媒体类型和 SHA-256，并形成 `ArtifactRecord`。
4. 将记录追加到 Run 的 Artifact Index，使用原子替换防止半写文件被观察到。
5. 终态汇总输入、状态、错误和 Artifact 记录，生成 `run_manifest.json`。
6. 后续读取者先验证 Run/Manifest/Artifact 身份，再展示、比较、发布或清理内容。

### Phase 9：Preflight 与环境就绪

- **状态**：已实现。
- **实现功能**：执行前检查入口脚本、依赖、路径、程序、环境和 GPU 等条件。
- **技术**：静态检查、受控 Probe、结构化 `PreflightReport`。
**核心思路**

训练启动后才发现入口脚本不存在、数据路径仍是占位符或 CUDA 不可用，会浪费大量时间并产生难以解释的失败。本阶段在正式执行前建立 Preflight，将能够低成本、无副作用判断的问题提前检查，并输出结构化就绪报告。

Preflight 分为静态检查和受控探测。静态检查只分析 Action、路径和配置；运行时 Probe 只执行白名单内的版本或能力查询，不借机运行任意模型命令。检查结果区分 ready、warning 和 blocked，只有满足硬性条件的动作才能继续。

**实现流程**

1. 读取结构化 Action 和 Execution Profile，检查必填字段、占位符和风险属性。
2. 验证工作目录、入口脚本、配置文件和声明的数据路径是否存在且位于允许边界。
3. 检查 Python、Conda、编译器或其他必需程序是否可解析，并核对声明依赖。
4. 在白名单内执行 Python/CUDA/GPU 等只读 Probe，设置严格超时和输出上限。
5. 将每项检查记录为 pass、warning 或 fail，汇总为 `PreflightReport` 和就绪状态。
6. `ready` 进入 Smoke/Executor，`blocked` 进入人工处理或最终报告，不启动正式训练。

---

## 五、安全执行与修复闭环：Phase 10-16

### Phase 10：Execution Backend 与环境隔离

- **状态**：已实现。
- **实现功能**：Local/Conda Runner、Execution Profile 和 Agent/论文环境隔离。
- **技术**：Runner Protocol、Profile Store、环境白名单、Fingerprint。
**核心思路**

Agent 自身依赖 LangGraph、Provider SDK 和服务端组件，论文仓库则可能要求完全不同的 Python、PyTorch、CUDA 和系统库。若二者共用当前进程环境，安装论文依赖可能破坏 Agent，Agent 的环境变量也可能意外泄露给论文程序。本阶段用 Execution Profile 描述目标运行环境，再由 Runner 抽象选择 Local 或 Conda 后端。

Profile 是声明，不是对环境可用性的保证。执行前要进行 Capability Check，确认对应解释器、Conda 环境和平台能力真实存在，并为环境计算可追踪 Fingerprint。Runner 只注入白名单环境变量，使相同 Action 在不同环境中的差异能够被记录和解释。

**实现流程**

1. 用户或规划阶段为 Action 关联 Execution Profile，声明 backend、环境名和所需能力。
2. Profile Store 读取并校验配置，拒绝未知 backend、缺失字段或越界路径。
3. Capability Check 探测解释器、Conda 环境、CUDA 等资源，生成可用性决定和环境身份。
4. Runner Resolver 根据 Profile 选择 LocalRunner 或 CondaRunner，而不是由节点拼接环境命令。
5. Runner 构造最小环境变量集合，通过参数列表启动目标程序并记录实际解释器。
6. 执行结果保存 profile id、fingerprint 和能力报告，供诊断、比较与重跑使用。

### Phase 11：Smoke Test 与 Bounded Repair

- **状态**：已实现。
- **实现功能**：正式执行前生成低成本 Smoke Action；失败后只允许一次有界命令修复。
- **技术**：参数裁剪、Repair Proposal、step budget、条件路由。
**核心思路**

Preflight 只能证明环境表面就绪，不能证明代码可以导入、模型可以构建或最小数据流能够运行。正式训练前先执行低成本 Smoke Action，可以在几秒或几分钟内发现 API 不兼容、扩展未编译和参数错误。Smoke 命令必须从原 Action 确定性派生，不能由模型随意替换成另一项任务。

Smoke 失败后允许模型提出命令级 Repair Proposal，但自动循环必须有严格预算。修复次数、可修改字段和允许增加的参数都受到限制，每次变化重新计算 Hash、评估风险并经过审批，防止 Agent 在失败后无限试错或逐步扩大权限。

**实现流程**

1. Preflight 通过后读取正式 Action，根据脚本类型和参数生成低成本 Smoke Action。
2. 对 epoch、batch、数据量、worker 或评估范围做有界缩减，同时保留入口与核心代码路径。
3. 使用同一 Execution Profile 和安全 Runner 执行 Smoke，记录独立日志与结果。
4. Smoke 成功时保留验证证据，并路由到正式 Executor。
5. Smoke 失败时在剩余 repair budget 内生成只修改允许字段的 Repair Proposal。
6. 对修复动作重新校验、Hash、风险判断和人工审批；预算耗尽或越界时停止并报告。

### Phase 12：Structured Output Reliability

- **状态**：已实现。
- **实现功能**：统一模型结构化输出重试、JSON fallback、raw/parsed/error Trace。
- **技术**：`with_structured_output(include_raw=True)`、Pydantic、Transport Retry、Telemetry。
**核心思路**

`with_structured_output()` 提高了返回 Schema 的概率，但不会消除字段遗漏、类型错误、Provider 工具调用差异或模型输出 Markdown 的情况。本阶段把每次结构化调用视为对不可靠外部系统的访问：既保留 `raw`、`parsed` 和 `parsing_error`，又区分传输失败、Schema 失败和业务身份失败。

重试需要分层且有上限。网络超时可以重试同一请求，Schema 失败可以附带精简纠错提示再次解析，必要时在 Provider 支持范围内切换 JSON Schema/JSON mode；但任何成功解析的对象仍需本地业务校验，例如 section id、路径或 action identity 必须与请求一致。Trace 记录每次尝试，避免最终失败只剩一条 Pydantic 异常。

**实现流程**

1. 根据目标 Pydantic Schema 和当前上下文构建 Prompt，显式说明字段与输出约束。
2. 使用 `include_raw=True` 调用 Structured Output，保留 Provider 原始消息和解析状态。
3. 若调用超时或网络异常，按 Transport Retry 策略退避重试，不在 Debug Console 重复触发慢调用。
4. 若 `parsed` 为空或存在 `parsing_error`，记录失败并按预算尝试 Schema 纠错或 JSON fallback。
5. 解析成功后运行领域 Validator，核对 section、chunk、路径、Hash 等请求身份。
6. 将每次 attempt 写入 structured trace；成功返回对象，耗尽预算则形成可诊断的 StageError。

### Phase 13：Manual File Repair 与 Patch Verification

- **状态**：已实现。
- **实现功能**：生成 Patch Proposal，在隔离 worktree 验证，再人工决定是否提升。
- **技术**：Git worktree、统一 Diff、文件 Hash、pytest/compile check、双审批。
**核心思路**

命令修复无法解决源码兼容性或实现 bug 时，Agent 可能需要提出文件补丁。但 Patch Draft 只是建议：它可能修改错误文件、使用过期源码上下文，甚至破坏仓库。因此本阶段将“同意验证补丁”和“同意写回原仓库”拆成两次审批，中间在隔离 Git worktree 中应用并测试。

补丁必须声明目标文件、原始内容 Hash、统一 Diff 和验证命令。隔离验证只能证明补丁在特定快照与测试集下可应用，不能自动授予生产写权限。验证报告和实际 diff 会再次展示给用户，由用户决定是否 Promotion，完整保留 Proposal、Approval、Verification 和最终应用记录。

**实现流程**

1. 从 Debug Report 和受限源码上下文生成 Patch Proposal，列出目标、原因和预期影响。
2. 本地校验路径范围、统一 Diff 格式、原始文件 Hash 和修改预算。
3. 第一次人工审批只授权“创建隔离环境并验证该补丁”，不授权修改原仓库。
4. 从目标提交或快照创建 Git worktree，在其中应用补丁并运行 compile、pytest 或指定验证命令。
5. 生成 Patch Verification Report，记录 apply 结果、测试输出、实际 diff 和残余风险。
6. 第二次人工审批决定是否提升；批准后才进入受控应用节点，拒绝则保留验证产物并结束。

### Phase 14：Graph 与文件修复安全收口

- **状态**：已实现。
- **实现功能**：修复错误路由、Patch stale、并发写和崩溃恢复问题。
- **技术**：唯一条件边、Repository Lock、Journal、Hash/Fencing、故障注入。
**核心思路**

即使补丁已经在 worktree 验证，写回原仓库时仍可能遭遇源码被用户修改、两个任务并发应用、进程在写入中途崩溃等问题。本阶段对 Graph 路由和文件写路径做安全收口，确保只有一个受控节点拥有原仓库写权限，并为每次写入建立锁、Journal 与恢复协议。

应用前重新比较 Patch Hash 和当前源码 Hash，任何漂移都要求重新验证。Journal 先记录计划修改及原始身份，再执行原子写入或受控 patch apply；崩溃恢复根据 Journal 判断尚未开始、部分完成或已经完成，避免盲目重复。Graph 条件边也保持唯一，防止同一状态同时进入两个写节点。

**实现流程**

1. 校验 Promotion Approval 绑定的 Patch Hash、验证报告和目标仓库身份。
2. 重新计算目标文件当前 Hash，与验证时基线比较，发现漂移立即返回 stale。
3. 获取仓库级锁并写入 apply Journal，记录事务 id、目标文件、原始 Hash 和预期 Hash。
4. 按确定顺序应用补丁，采用临时文件加原子替换或经过校验的 patch 工具。
5. 重新读取文件并验证内容 Hash，运行必要的快速检查，更新 Journal 为完成状态。
6. 释放锁并生成不可变应用记录；启动时若发现未完成 Journal，则先对账和恢复再接受新写入。

### Phase 15：统一错误模型与 Run-native Artifact

- **状态**：已实现。
- **实现功能**：统一 `StageError`，区分 user/agent/environment/provider/paper_program 错误。
- **技术**：错误 Guard、稳定 Error Code、Traceback Artifact、Run Layout。
**核心思路**

随着节点增多，各模块自行抛出字符串异常会导致 API、Graph 和报告对同一失败有不同解释。本阶段引入统一 `StageError`，用稳定 error code、category、stage、message、retryable 和 evidence reference 描述失败。可预期错误作为 State 数据进入终态，真正的编程错误仍保留 traceback，二者不再混在一个 `except Exception` 文本中。

错误内容在进入持久化边界前需要裁剪和脱敏，详细 traceback 作为 Run-native Artifact 保存，State 只保留安全摘要和引用。这样 CLI、Web、Job Event 和 Final Report 可以共享同一错误语义，重试策略也能基于 category 和 retryable 做确定性判断。

**实现流程**

1. 在节点边界捕获已知领域异常、环境异常、Provider 异常和论文程序结果。
2. Error Guard 根据来源映射稳定 category 与 error code，并判断是否允许重试。
3. 对 message、command、路径和 traceback 做长度限制与敏感信息脱敏。
4. 构造 `StageError` 写入 State，将完整 traceback 和诊断上下文写入当前 Run 的 Error Artifact。
5. 条件路由根据错误类别进入 retry、debug、human action 或 terminal，而不是依赖字符串匹配。
6. Final Report、API 和 Eval 从同一 `StageError` 投影用户视图和评分 Observation。

### Phase 16：安全执行边界与受监管进程

- **状态**：已实现。
- **实现功能**：进程组监管、取消、超时、输出上限、环境隔离和 Resource Budget。
- **技术**：`Popen(shell=False)`、psutil、Process Group、Signal、Execution Record。
**核心思路**

长时间训练不能使用一次阻塞 `subprocess.run()` 后只等待返回。Agent 需要知道进程是否仍存活、日志是否增长、用户是否取消、是否超过时间或资源预算，并在自身重启后判断遗留进程。本阶段建立 Process Supervisor，把启动、观察、控制和回收统一成受监管生命周期。

进程以独立进程组启动，取消和超时时先发送温和信号，再在 grace period 后升级终止整个子树。stdout/stderr 流式写入有界日志，State 和 Event 只保留 tail 或 Artifact 引用。Process Record 记录 pid、start identity、Action/Profile Hash 和终态，避免 PID 复用导致误杀无关进程。

**实现流程**

1. 校验 Action、Approval、Execution Profile 和 Resource Budget，生成不可混淆的 execution identity。
2. 以 `shell=False` 和独立 process group 启动进程，记录 pid、启动时间及进程身份信息。
3. 持续读取 stdout/stderr 写入日志 Artifact，只向事件流发送受限 tail 和进度信号。
4. 周期更新 heartbeat、运行时长和资源指标，并检查取消、超时及输出上限。
5. 需要停止时先向进程组发送 graceful signal，等待宽限期后再强制终止整个子进程树。
6. `wait`/reap 后写入最终 Process Record；恢复时按身份对账，区分仍运行、已退出和失联进程。

---

## 六、理解与检索质量：Phase 17-21

### Phase 17：Agent Regression Evaluation

- **状态**：已实现。
- **实现功能**：离线 Case、Provider Case、Observation、Scorer、Baseline 和报告。
- **技术**：pytest、Pydantic Eval Schema、Golden Fixture、Safety Metrics。
**核心思路**

Agent 由确定性代码、Prompt、模型和外部环境共同决定行为，普通单元测试无法覆盖“输出结构合法但质量下降”的情况。本阶段建立统一回归评测管线，将 Case、Runner、Observation、Scorer 和 Baseline 解耦。同一个 Case 可以在离线 Fixture 上稳定回归，也可以在 Provider 模式下重复采样真实模型表现。

安全指标与质量指标采用不同门槛。引用越权、执行越界等安全断言应零容忍，而召回率、字段完整度等质量指标可以比较基线和允许波动。报告记录 case-level 证据，而不只给总分，便于定位是 Parser、Retriever、Prompt 还是 Provider 引起回归。

**实现流程**

1. 用版本化 Eval Schema 定义 Case 输入、期望事实、阈值、suite 和运行模式。
2. Case Loader 扫描评测目录并进行格式校验，拒绝重复 id 和缺失 Fixture。
3. Runner 在 offline 或 provider 模式运行目标能力，捕获输出、Trace、延迟和失败类型。
4. Observation Adapter 将不同节点结果投影为稳定字段，隔离实现细节变化。
5. 多个 Scorer 分别计算正确性、完整性、证据、安全和性能指标。
6. 与版本化 Baseline 比较后生成明细报告；违反 Safety Gate 或超过回归阈值时测试失败。

### Phase 18：章节感知论文理解

- **状态**：已实现。
- **实现功能**：PDF Block 解析、章节识别、层级 Chunk、Evidence、缓存和 Reducer。
- **技术**：PyMuPDF 坐标/字体、Section Schema、Content Hash、逐块 Structured Output。
**核心思路**

把 PDF 提取文本简单拼接会丢失页码、标题层级、栏布局和块身份，导致模型把实验设置当作方法、把页眉当作正文。本阶段以 PDF block 为原子记录，保留页码、坐标、字体和顺序；经过规范化与章节识别后，每个 Chunk 都绑定 `section_id`、`chunk_id` 和来源 Evidence。

模型对每个 Chunk 只生成局部 `SectionExtractionDraft`，本地代码验证返回身份仍对应请求 Chunk。Reducer 再按章节层级合并局部结果、去重和处理冲突。单块失败只形成 terminal `StageError` 与 Trace，不应删除其他有效结果或让整篇论文无条件失败；内容 Hash 缓存则避免重复调用模型。

**实现流程**

1. 使用 PyMuPDF 提取带页码、坐标、字体和文本的 PDF blocks，保留原始来源身份。
2. 规范化空白、连字符和阅读顺序，标记重复页眉页脚等 marginalia。
3. 根据编号、字体、位置和文本特征识别章节标题，构建父子 `PaperSection` 层级。
4. 在章节边界内生成 `SectionChunk`，为内容、section 和 chunk 计算稳定 Hash/id。
5. 对每个 Chunk 先查内容身份缓存，未命中时调用 Structured Output 并校验返回身份。
6. Reducer 聚合有效抽取、处理重复和冲突，输出带页码 Evidence 的论文级结构化结果。

### Phase 19：高精度结构与 Golden Eval

- **状态**：已实现。
- **实现功能**：标题候选、跨行合并、重复页眉页脚、父子章节和真实论文 Golden Set。
- **技术**：确定性 Parser、Golden Annotation、Precision/Recall、层级一致性检查。
**核心思路**

Phase 18 建立了章节感知管线，但启发式 Parser 是否正确需要独立测量。如果标题边界本身错误，下游模型再强也只能在错误上下文中推理。本阶段把高精度结构解析作为独立能力，通过人工标注的 Golden Set 计算标题 Precision/Recall、层级关系和页码覆盖，避免用最终摘要质量掩盖 Parser 缺陷。

解析策略优先使用确定性版面特征，并针对跨行标题、重复页眉页脚、双栏顺序和附录编号建立可解释规则。合成 PDF Fixture 覆盖最小边界，真实论文 Golden Case 覆盖版式差异。规则修改必须同时通过两类测试，防止为一篇论文过拟合。

**实现流程**

1. 使用 PyMuPDF 动态创建小型 Fixture PDF，精确布置标题、正文、重复页眉和跨页内容。
2. 为代表性真实论文人工标注期望章节标题、页码、父子关系和应忽略块。
3. Parser 生成标题候选，执行跨行合并、重复 marginalia 过滤和编号层级解析。
4. 将实际 section tree 与 Golden Annotation 对齐，统计标题 Precision、Recall、F1 和层级一致率。
5. 输出逐项 mismatch，明确漏检、误检、边界偏移和父级错误，而不只返回总分。
6. 将最低阈值加入 pytest/评测门禁，Parser 变更未达标时阻止下游发布。

### Phase 20：Hybrid Evidence Retrieval

- **状态**：已实现。
- **实现功能**：融合路径、符号、关键词和语义目标，输出可验证候选证据。
- **技术**：BM25/词法信号、路径规则、RRF/加权排序、Evidence Boundary。
**核心思路**

论文术语与仓库命名不一致时，单纯关键词检索会漏掉候选；但直接使用语义相似度又可能把概念相近、实际无关的代码排在前面。本阶段采用 Hybrid Retrieval：路径、文件名、符号、精确词法、traceback 和语义目标分别召回，再经过归一化与融合排序。

确定性强证据拥有更高优先级。例如 traceback 明确指出的文件、AST 命中的类名和 README 指向的入口，不应被泛化语义分数覆盖。检索只返回有大小和数量限制的 Evidence Bundle，LLM 负责在候选中解释映射，最终路径与行号仍由本地 Boundary Validator 验证。

**实现流程**

1. 从论文模块、错误报告和实验计划构建结构化 query targets，而不是只生成一个搜索字符串。
2. 分别执行路径/文件名规则、AST 符号、ripgrep 词法和已知 traceback 召回。
3. 将不同通道结果转换成统一 Candidate，保留通道、原始分数、路径和代码范围。
4. 对分数做通道内归一化，使用加权或 RRF 融合，并对强确定性证据施加优先规则。
5. 去重和裁剪候选，读取受限代码窗口构成 bounded Evidence Bundle。
6. 下游映射模型只接收该 Bundle，本地校验其引用未越出候选文件和行范围。

### Phase 21：Dense Retrieval 与 Embedding Cache

- **状态**：已实现。
- **实现功能**：代码语义 Chunk、向量检索、Embedding Cache 与检索评测。
- **技术**：Embedding Backend Port、Cosine Similarity、SQLite Cache、Content Identity。
**核心思路**

当实现使用 `st_gcn_block`、`tube_embedding` 等非论文原词命名时，Dense Retrieval 能根据局部代码作用和论文模块描述发现语义对应关系。本阶段将代码按符号与局部上下文切成 Semantic Chunk，通过 Embedding Backend 生成向量，并与查询向量计算相似度，作为 Hybrid Retrieval 的一个召回通道。

向量不是权威证据，也不自动带来更高准确率。Embedding Cache 使用内容 Hash、模型身份和切分版本作为键，防止源码变化后复用旧向量；召回结果仍受仓库边界、文件类型和候选上限约束。是否启用 Dense、权重多大，必须通过检索 Golden Eval 比较 Recall、MRR 与误召回后决定。

**实现流程**

1. 根据语言和符号边界把代码切成 Semantic Chunk，保存路径、行范围、符号和规范文本。
2. 为 Chunk 内容、切分版本和仓库快照计算身份，组成可失效的 Embedding Cache Key。
3. 查询 SQLite Cache；未命中时通过 Embedding Backend 批量生成向量并持久化。
4. 对论文模块查询使用同一模型生成向量，计算 Cosine Similarity 并选取有界 top-k。
5. 将 Dense Candidate 与词法、路径和符号候选一起融合，保留通道来源与分数解释。
6. 在 Golden Query 上比较纯词法、Dense 和 Hybrid 指标，仅在收益满足阈值时调整默认策略。

---

## 七、任务运行与持久化：Phase 22-29

### Phase 22：异步 Job Runtime

- **状态**：已实现。
- **实现功能**：提交、Claim、Lease、Heartbeat、取消、重试、Crash Recovery。
- **技术**：SQLite Job Store、Worker Loop、幂等键、Fencing Token。
**核心思路**

论文分析、编译和训练可能持续数小时，不能要求提交请求始终保持连接。本阶段将“提交任务”和“执行任务”解耦：CLI/API 只创建持久 Job，Worker 通过 Claim 获取租约并驱动 Graph。用户可以随时离开，再通过 Job View 和 Event 观察状态。

Claim 不是永久所有权。Worker 周期发送 Heartbeat 延长 Lease，并携带 Fencing Token 写入状态；若进程崩溃或机器失联，Lease 过期后 Reconciler 才允许重新排队。旧 Worker 即使恢复，也因 token 过期不能覆盖新 Worker 的结果，从而解决 crash recovery 中最危险的“双执行、旧写入”歧义。

**实现流程**

1. API/CLI 校验任务请求和幂等键，将 Job 以 `queued` 状态持久化后立即返回 `job_id`。
2. Worker Loop 查询可领取任务，通过原子 Claim 设置 owner、lease deadline、attempt 和 fencing token。
3. Worker 载入输入与 Checkpoint，启动或恢复 Graph，并将阶段变化写成 Job Event。
4. 执行期间周期刷新 Heartbeat 与 Lease，所有状态写入都校验当前 owner/token。
5. Graph 进入 interrupt 时 Job 标记为 waiting；成功、失败或取消时写入明确 terminal 状态。
6. Reconciler 扫描过期 Lease，核对进程和 Checkpoint 后决定 requeue、fail 或保留，旧 Worker 写入被拒绝。

### Phase 23：统一交互 API 与 Event Stream

- **状态**：已实现。
- **实现功能**：统一 Job View、Allowed Operations、Decision Protocol、SSE Timeline。
- **技术**：FastAPI、Pydantic API Schema、SSE、Optimistic Concurrency。
**核心思路**

Graph 内部 State 很复杂，若前端根据状态字符串自行推测“现在可以批准、取消还是恢复”，前后端版本变化后容易出现越权或 stale 操作。本阶段由服务端把内部状态投影成稳定 Job View，并显式返回 `allowed_operations` 及每个操作所需的 expected version、generation 和目标 identity。

Decision Protocol 把用户意图变成带并发条件的 Envelope，服务端再次运行 Policy 后才写入决定。SSE 只传递事实事件和视图更新，不承担授权。这样 CLI、Web 和未来客户端使用同一交互协议，页面刷新或断线重连也不需要猜测 Graph 下一步。

**实现流程**

1. JobService 读取 Job、Graph snapshot、pending interrupt 和最新版本，构建内部聚合状态。
2. Projection 层只暴露稳定字段，并根据 Policy 计算当前 `allowed_operations`。
3. 客户端展示服务端提供的操作卡片，提交带 kind、expected version/generation、target hash 和 idempotency key 的 Decision。
4. 服务端重新读取最新状态，校验操作仍被允许且所有乐观并发条件一致。
5. 有效决定以 exactly-once 语义持久化并驱动 resume；stale 决定返回冲突和刷新后的视图。
6. Job Event 通过 SSE 推送，客户端按事件 id 断线续传并重新获取权威 Job View。

### Phase 24：Persistence Ports 与 Artifact Publication

- **状态**：已实现。
- **实现功能**：抽象 Job/Blob/Artifact 端口，将 Worker 本地产物发布为可共享 Artifact。
- **技术**：Protocol/Port Adapter、Local/S3 Blob、Catalog、SHA-256。
**核心思路**

本地 Run 文件不能直接作为多进程或远程客户端的公共接口，因为绝对路径只在生成它的 Worker 上有意义。本阶段定义 Persistence Ports，将 Job 控制状态、二进制内容和 Artifact 元数据分层：数据库保存小而可事务更新的控制记录，Blob Store 保存按内容寻址的大对象，Artifact Catalog 记录业务身份、媒体类型和 Blob 引用。

发布采用“先写内容、后登记可见记录”的顺序。只有 Blob 完整写入且 Hash/大小验证通过后，Catalog 才公开 Artifact；消费者通过 Artifact id 访问 Descriptor，不直接信任 Worker 路径。Port/Adapter 使本地 SQLite/文件系统和 PostgreSQL/S3 共享相同业务契约。

**实现流程**

1. Worker 在 Run 目录完成文件写入并关闭句柄，计算 SHA-256、大小和媒体类型。
2. 构造 Artifact Descriptor，包含 job/run/stage、逻辑名称、内容身份和来源相对路径。
3. 通过 BlobStore Port 以内容键写入本地或 S3，重复内容可幂等复用。
4. 回读或 HEAD 校验 Blob 的 Hash/大小，失败时不创建公共 Catalog 记录。
5. Artifact Repository 在事务中发布 Descriptor，并更新 Job/Run 的 Artifact 索引。
6. API 和其他 Worker 通过 Catalog 获取授权元数据，再从 BlobStore 读取内容，不依赖原主机路径。

### Phase 25：PostgreSQL Control Plane

- **状态**：已实现。
- **实现功能**：PostgreSQL Job Store、共享 Checkpoint、多 Worker 原子 Claim 和迁移。
- **技术**：SQLAlchemy、Alembic、PostgreSQL locking、LangGraph Postgres Saver。
**核心思路**

SQLite 适合单机，但多个 Worker 或服务实例共享任务时，进程内锁和本地 Checkpoint 无法保证原子 Claim。本阶段将控制面迁移到 PostgreSQL，利用事务、行锁、唯一约束和条件更新实现并发安全，同时接入共享 LangGraph Checkpoint，使任意合格 Worker 都能读取同一 Job 的恢复位置。

数据库并不会自动解决分布式语义。Job 状态转换、attempt、Lease、Fencing Token 和幂等键仍需在 Repository 层形成明确协议；Schema 变化通过 Alembic 前向迁移，切换前后要验证 SQLite/PostgreSQL Adapter 满足同一 Contract，避免业务代码绑定某个 SQL 实现。

**实现流程**

1. 定义 JobStore 和 Checkpoint Port 的共享语义，并为 SQLite/PostgreSQL 编写契约测试。
2. 使用 SQLAlchemy Model 与 Alembic Migration 创建 Job、Event、Decision、Lease 等表和约束。
3. 提交请求在事务中检查幂等键并创建唯一 Job，重复请求返回既有身份。
4. Worker 通过 `FOR UPDATE SKIP LOCKED` 或等价条件更新原子 Claim，生成新 fencing token。
5. Graph 使用 PostgreSQL Saver 读写相同 thread/checkpoint，Heartbeat 与终态更新校验 owner/token。
6. 通过并发与故障注入测试验证单任务不被双领、旧 Worker 不能写入、迁移可以安全回滚或前进。

### Phase 26：Workspace Materialization 与 Worker Affinity

- **状态**：已实现。
- **实现功能**：不可变 Workspace Manifest、Worker Capability、主机亲和和跨主机接管。
- **技术**：Content-addressed Blob、Manifest Hash、Capability Matching、Generation/Fencing。
**核心思路**

任务请求若只记录 `/data/.../repo`，换一台主机后该路径可能不存在或内容已变化。本阶段把论文、仓库和必要输入做成不可变 Workspace Manifest：每个文件或归档由内容 Hash 标识，Job 引用 Manifest identity，Worker 在本机受控根目录物化后才获得可执行路径。

调度同时考虑 Worker Capability Affinity，例如 GPU、磁盘、架构、容器和本地缓存。Workspace Binding 带 generation 和 fencing token，跨主机接管会创建新绑定，旧主机路径不会被复用。用户当前可以只用单机实现，但这套身份分离也能防止本机原路径漂移，并为清理和重跑提供稳定依据。

**实现流程**

1. 对论文、仓库和配置执行受控 Snapshot，将内容发布到 BlobStore 并生成 Workspace Manifest。
2. 计算 Manifest Hash，Job Request 只保存该身份和能力需求，不把提交主机绝对路径作为事实来源。
3. Scheduler 将 Job 需求与 Worker Capability/缓存/容量匹配，选择可执行 Worker。
4. Worker 在受控 workspace root 创建 staging，下载或复用已校验 Blob，逐项验证内容 Hash。
5. 原子提升 staging 为物化 Workspace，创建带 generation/token 的 Binding 后交给 Graph/Runner。
6. 接管时废弃旧 Binding 并重新物化；终态后由引用感知 GC 清理无租约、无保留引用的 Workspace。

### Phase 27：OCI Runtime 与强隔离

- **状态**：已实现。
- **实现功能**：Podman/OCI 执行、只读根、受控挂载、网络策略和环境身份。
- **技术**：OCI Image Digest、Container Plan、Podman Engine、Supervisor/Reconcile。
**核心思路**

Conda 可以隔离 Python 依赖，却不能限制进程读取宿主文件、访问网络、提升资源占用或影响其他进程。本阶段为高风险论文代码增加 OCI Runtime，通过镜像 Digest、只读根文件系统、受控挂载、网络策略、非特权用户和资源限制建立操作系统级边界。

模型和普通节点不能直接拼接 Podman 参数。确定性 Planner 根据 Action、Execution Profile、Workspace 和 Policy 生成 `ContainerPlan`，计算 Hash 并纳入审批；Runner 只执行经过验证的计划。Supervisor 继续负责容器内主进程的日志、超时和取消，Reconciler 处理 Agent 崩溃后遗留容器。

**实现流程**

1. 根据动作风险和 Profile 决定使用本地 Runner 还是 OCI Runner，高风险场景默认拒绝不安全降级。
2. 解析已 pin 的 image digest，生成包含用户、挂载、网络、资源和环境引用的 `ContainerPlan`。
3. 本地 Validator 检查只读/可写挂载范围、特权选项、设备、Secret 注入和网络策略。
4. 对规范计划计算 Hash，并与 Action/Approval/Run identity 一起持久化。
5. Podman Adapter 创建和启动容器，Supervisor 采集日志、心跳、资源、取消与超时状态。
6. 结束时记录容器和镜像身份并移除临时容器；重启后 Reconciler 按 label/identity 对账遗留实例。

### Phase 28：分布式可观测性与运行就绪

- **状态**：已实现。
- **实现功能**：Trace Context、结构化日志、指标、Readiness、Support Diagnosis。
- **技术**：OpenTelemetry Port/Adapter、JSON Logging、Span Link、Readiness Probe。
**核心思路**

任务跨越 API、Job Store、Worker、Graph、进程、容器和 Artifact 后，单个日志文件无法回答“某次请求最终启动了哪个进程、产出了哪个文件”。本阶段建立统一 Correlation Context，将 trace id、job id、run id、worker id、attempt、fencing token 和 process/container identity贯穿结构化日志、Span、Event 与 Artifact。

可观测性不仅服务排错，还要回答系统是否“准备好接任务”。Readiness 检查数据库、BlobStore、Checkpoint、Worker Lease、执行后端和必要密钥是否可用；Support Diagnosis 汇总组件状态和身份链，而不泄漏 Secret。指标关注队列时延、执行时长、失败类别、租约丢失和发布错误，避免只记录请求数量。

**实现流程**

1. API 接收或创建 Trace Context，将 trace/job identity 写入 Job 和首个 Event。
2. Worker Claim 后创建关联 Span，并附加 worker、attempt、lease 和 fencing 属性。
3. Graph 节点、Process Supervisor、Container Runner 和 Artifact Publisher 继承或链接同一上下文。
4. 所有模块输出结构化日志并统一脱敏，关键状态变化同时记录 Metric 和 Event。
5. Readiness Probe 分别检查控制面、存储、Checkpoint、Worker 和 Runtime，区分 ready/degraded/not-ready。
6. Support Diagnosis 按 job/run/trace 聚合时间线和组件健康信息，帮助定位跨层失败。

### Phase 29：受控资源获取与供应链安全

- **状态**：已实现。
- **实现功能**：HTTP/Git 资源请求、Policy、下载 Worker、Hash、发布和对账。
- **技术**：SSRF 防护、域名/IP Policy、Size/Type Limit、Git Pin、Artifact Publication。
**核心思路**

论文复现经常缺少数据、预训练权重、仓库子模块或依赖源码，但允许 Agent 根据网页文字直接下载会引入 SSRF、域名劫持、超大文件和供应链漂移风险。本阶段将资源获取建模为 `ResourceRequest`，模型最多提出 URI、用途和期望身份，确定性 Policy 决定是否允许、是否需要审批以及可用的 Fetcher。

下载与使用分离。HTTP/Git Worker 在隔离 staging 中获取资源，限制 DNS/IP、重定向、大小、类型和超时；Git 必须 pin commit，普通文件尽量提供期望 Hash。验证通过后资源发布为内容寻址 Artifact，Workspace 只物化已发布身份，原始网络地址不直接成为执行输入。

**实现流程**

1. LLM、用户或计划节点创建结构化 Resource Request，声明类型、URI、用途和可选 expected hash/commit。
2. Policy 规范化 URI，检查协议、域名、解析 IP、端口、资源类型和 Job 当前权限。
3. 中高风险请求生成审批卡片并绑定 Request Hash；拒绝项不进入任何网络代码。
4. 专用 Fetch Worker 在 staging 中执行 HTTP 下载或 Git fetch，限制重定向、大小、时间和文件类型。
5. 校验 SHA-256、Git commit、内容格式和恶意边界，失败时销毁 staging 并记录 StageError。
6. 验证成功后发布 Blob/Catalog Artifact，Workspace 通过 Artifact identity 物化；Reconciler 处理失败或遗留下载。

---

## 八、单机产品与知识交互：Phase 30-39

### Phase 30：对话式 Web Console 与单机部署

- **状态**：已实现。
- **实现功能**：任务提交、Timeline、审批、取消、恢复和单机服务启动。
- **技术**：FastAPI、SSE、静态 Web、API Token、Service Host。
**核心思路**

本阶段的目标不是在浏览器里复制 Graph 逻辑，而是为已有 Job/Decision/Event 协议提供轻量操作界面。前端只渲染服务端 Job View、Timeline 和 `allowed_operations`，不根据颜色、状态字符串或本地缓存自行判断是否可以审批、取消或恢复。

单机部署仍保持前后端边界：FastAPI 负责认证、输入校验、并发控制和状态投影，SSE 负责实时事件，静态 Web 负责展示与提交决定。这样未来更换前端不会改变 Agent 权限模型，也能在浏览器断线、刷新或服务重启后从持久状态恢复。

**实现流程**

1. Service Host 启动 FastAPI、Job Worker 和静态资源服务，并执行依赖就绪检查。
2. 用户在 Web 表单提交论文、仓库或已导入输入，API 校验后创建异步 Job。
3. 页面通过 Job API 获取权威视图，并订阅 SSE Timeline 显示阶段、日志摘要和 Artifact 事件。
4. 后端根据最新状态返回允许的审批、拒绝、取消或恢复操作及其并发字段。
5. 用户提交 Decision，API 调用 JobService/Policy 校验后驱动 Graph，而不是前端直接修改状态。
6. 页面收到后续事件或 stale 响应后刷新 Job View，终态展示报告和可访问 Artifact。

### Phase 31：Artifact-Grounded Chat Agent

- **状态**：已实现。
- **实现功能**：围绕单个 Job 对话，回答必须引用已发布 Artifact。
- **技术**：Chat Store、Context Builder、Structured `ChatDraft`、Citation Allowlist。
**核心思路**

Chat Agent 的知识范围被限制在当前 Job 已发布且用户可访问的 Artifact，而不是让模型凭训练记忆或任意文件回答。Context Builder 从 Catalog 选择安全文本片段，为每段分配本地 citation id；模型只生成 `ChatDraft` 和所引用 id，不能自行构造路径或 Blob key。

回答落库前，本地 Citation Validator 检查每个引用属于本次上下文、对应 Artifact 身份仍有效，并验证无证据场景是否明确拒答。对话是只读解释层，不拥有执行、审批或文件修改 Tool；用户表达操作意图时，系统应引导其使用正式 Decision Card，而不是把自然语言直接变成动作。

**实现流程**

1. API 验证用户可访问目标 Job/Conversation，并把问题作为用户消息持久化。
2. Context Builder 从已发布 Artifact、Run Manifest 和必要 Chat Memory 中选择受限文本证据。
3. 为证据生成本地 Citation Allowlist，裁剪长度并对内容执行 Secret Redaction。
4. 调用 Structured Output 模型生成答案草稿、citation ids 和必要的无证据说明。
5. 本地校验引用身份、证据覆盖和只读边界，越权引用或操作性输出按策略拒绝或降级。
6. 持久化通过校验的助手消息与引用记录，API 返回可点击但受授权控制的 Citation。

### Phase 32：Web Command Edit 与 Stale Recovery

- **状态**：已实现。
- **实现功能**：Web 编辑候选命令、Hash/Version 绑定和 stale 决策恢复。
- **技术**：Command Hash、Expected Version、Decision Protocol、Conflict Projection。
**核心思路**

Web 页面可能在用户阅读期间停留数分钟，而 Worker、另一个终端或恢复流程已经改变 pending command。若提交时只带“批准”，旧页面就可能批准新动作。本阶段将命令编辑、目标 Hash、Job Version 和 Graph Generation 一起放入 Decision Envelope，使用乐观并发检测 stale。

编辑后的命令被视为新 Proposal，而不是对已审批对象的原地修改。服务端重新解析、校验、计算 Hash 和评估风险；原审批自动失效。发生冲突时返回当前权威操作卡片和可解释原因，让前端刷新并要求用户重新确认，而不是静默覆盖。

**实现流程**

1. 页面加载当前 pending command、candidate version、action hash 和允许的 edit/approve 操作。
2. 用户在表单中修改命令或选择候选，前端提交原 expected version/generation/hash。
3. API 重新读取 Job 与 interrupt，校验目标身份和操作仍处于 allowed operations。
4. 服务端解析编辑内容，验证命令边界并创建新 Action/Command Hash。
5. 若状态未变化，则幂等保存决定并恢复 Graph；新动作重新经过 Risk Check 和审批。
6. 若任一 identity 不匹配，则返回 stale conflict、最新视图和恢复提示，不执行旧决定。

### Phase 33：受控本地输入导入

- **状态**：已实现。
- **实现功能**：将本地论文、仓库和日志导入受控 Blob/Workspace，而不是长期引用原路径。
- **技术**：Allowed Root、Staging、Snapshot、Hash、Manifest。
**核心思路**

单机用户习惯直接输入本地路径，但 Graph 长期保存绝对路径会受到文件被修改、删除或符号链接切换的影响。本阶段把本地路径限定为“导入时来源”：经过 Allowed Root、真实路径、文件类型和容量检查后，内容进入 staging，并被快照为不可变 Blob 或 Workspace Manifest。

导入完成后的 Job 只引用内容身份，原路径仅作为审计元数据，不再是执行事实。这样即使用户随后修改原仓库，当前 Job 仍复现导入时版本；若想使用新内容，需要重新导入形成新 identity，避免无记录漂移。

**实现流程**

1. 用户通过 CLI/Web 提交本地论文、仓库或日志路径及输入类型。
2. Import Service 解析 realpath，检查 Allowed Root、符号链接、文件类型、数量和总大小。
3. 将允许内容复制到项目受控 staging，避免直接在用户原目录上执行后续操作。
4. 对单文件计算 Hash，对仓库生成规范 Snapshot/Manifest，并验证复制前后身份一致。
5. 将内容发布到 BlobStore/Catalog，创建不可变 Input Reference 和来源审计记录。
6. Job Request 保存 Input Reference；物化与执行只读取该身份，不再依赖原绝对路径。

### Phase 34：Artifact 预览、下载与单 Job 导出

- **状态**：已实现。
- **实现功能**：安全文本预览、流式下载、导出包和临时文件 TTL。
- **技术**：Media Type Allowlist、Range/Size Limit、StreamingResponse、ZIP Manifest。
**核心思路**

用户需要查看日志、报告和结构化结果，但开放 `?path=` 下载会形成任意文件读取漏洞。本阶段所有预览和下载都从 Artifact id 出发：服务端先通过 Catalog 验证 Artifact 属于目标 Job、媒体类型允许、Blob 身份正确，再决定文本预览、流式下载或拒绝。

单 Job 导出不是简单压缩 Run 目录，而是依据 Catalog 选择已发布内容，并附带 Export Manifest、Hash 和缺失项说明。临时 ZIP 在受控目录生成，设置 TTL 和大小上限，用完后清理；Secret Scanner 和安全策略可阻止敏感 Artifact 被交付。

**实现流程**

1. 客户端提交 job id 与 artifact id，API 校验身份、归属和访问权限。
2. Repository 读取 Descriptor，BlobStore 校验内容存在、大小和 Hash 未漂移。
3. 文本预览执行媒体类型白名单、字节上限、编码处理和统一脱敏。
4. 文件下载使用受控 `StreamingResponse`，设置安全文件名、Content-Type 和必要范围限制。
5. 导出服务按 Job Artifact Catalog 生成清单，在临时目录打包并计算导出包 Hash。
6. 返回短生命周期下载引用；完成、过期或失败后清理临时文件并记录审计事件。

### Phase 35：单机 Retention、Quota 与 Auditable GC

- **状态**：已实现。
- **实现功能**：容量盘点、保留策略、Hold、Plan Hash、Sweep 和审计记录。
- **技术**：SQLite、Mark-and-Sweep、引用图、文件锁、两阶段删除。
**核心思路**

Run、Blob、Workspace、Chat 和导出包持续增长后，单机磁盘会成为可靠性风险；但直接按目录时间删除可能破坏仍被 Job、比较报告、重跑或人工 Hold 引用的数据。本阶段使用引用图和 Mark-and-Sweep 生成 GC Plan，先展示“为什么可删、预计释放多少”，再由用户确认。

确认绑定 Plan Hash，执行时重新获取锁并核对版本、引用和内容身份。新增引用、Hold 或计划漂移都会让删除失败关闭。删除顺序先处理无共享风险的派生/临时内容，再清理无引用 Blob，并保留 Tombstone/Audit，使空间管理成为可解释操作而不是后台黑盒。

**实现流程**

1. Inventory 扫描 Job、Run、Artifact、Blob、Workspace、Chat、Export 和临时文件的大小与时间。
2. Retention Policy 结合终态、年龄、最近访问、配额和 Hold 计算保留集合。
3. 构建引用图并执行 Mark 阶段，生成候选删除项、理由、预计释放空间和风险提示。
4. 对规范化 `GCPlan` 计算 Hash，展示给用户并要求显式确认或 dry-run 审阅。
5. 执行时获取 GC 锁，重新读取引用和 identity；任何漂移都废弃旧计划。
6. 按安全顺序 Sweep，记录每项结果、失败和释放字节，生成不可变 GC Audit/Tombstone。

### Phase 36：Chat Context Compaction 与引用保真记忆

- **状态**：已实现。
- **实现功能**：压缩长对话、保存用户约束/决策/问题并保留 Citation Anchor。
- **技术**：Memory Draft、Delta Hash、Parent Hash、Optimistic Version、Token Budget。
**核心思路**

长对话若始终把全部消息放入 Prompt，会超过上下文预算并反复发送相同 Artifact。简单摘要又可能丢掉“不要执行训练”“只使用某个数据集”等关键约束。本阶段将 Chat Memory 设计为结构化状态，分别保存用户约束、已确认决定、未解决问题、稳定事实和 Citation Anchor。

LLM 可以生成 Memory Draft，但本地代码负责从允许引用中投影 citation、校验父版本和计算 Hash。新记忆以 delta 和 parent identity 形成版本链，最近原始消息仍保留在上下文中；当摘要不确定或引用失效时，系统宁可少记，也不把推测升级为长期事实。

**实现流程**

1. Context Budgeter 统计系统提示、Artifact 证据、Memory 和最近消息的 token 使用。
2. 超过阈值时选择可压缩的旧消息窗口，保留最近交互和尚未解决的操作卡片。
3. 模型生成结构化 Memory Draft，分类约束、决定、事实、问题和 citation candidates。
4. 本地 Validator 只接受来自现有 Allowlist 的 Citation Anchor，并检查内容没有越权或 Secret。
5. 使用 parent hash、delta hash 和 optimistic version 持久化新 Memory Snapshot。
6. 后续 Context Builder 组合系统规则、有效 Memory、必要证据和最近消息，失效记忆被跳过或重建。

### Phase 37：Chat Grounding 与 Memory Golden Eval

- **状态**：已实现。
- **实现功能**：评估答案证据覆盖、引用正确性、记忆保真和无证据拒答。
- **技术**：Golden Cases、Provider/Offline Runner、Citation/Memory Scorer、Baseline。
**核心思路**

Chat 回答看起来流畅并不代表可信，它可能引用不存在的 Artifact、遗漏用户约束，或在无证据时编造结论。本阶段为 Grounding 与 Memory 建立 Golden Eval，明确评估 citation validity、evidence coverage、constraint retention、unsupported claim 和 refusal behavior，而不是使用主观“回答是否自然”。

Offline Runner 用固定 Draft 验证本地 Context、Citation 和 Memory 控制逻辑，Provider Runner 再多次调用真实模型评估波动。安全项采用 100% 门槛，质量项记录基线与统计分布；失败报告定位到具体 claim、citation 或 memory field，便于针对性修正。

**实现流程**

1. 创建包含 Job Artifact、对话历史、Memory 和期望事实的版本化 Chat Golden Case。
2. Offline 模式加载固定模型草稿，Provider 模式按 repetition 多次构建真实回答。
3. Runner 经过与生产一致的 Context Builder、Structured Output 和 Citation Validator 得到 Observation。
4. Scorer 分别检查引用存在性、引用对 claim 的支持、约束保留、拒答和 Secret/权限边界。
5. 聚合 case 与 repetition 指标，同 Baseline 比较质量变化并执行 Safety Gate。
6. 输出带失败证据的 JSON/Markdown Report，并纳入 CI 或发布前回归命令。

### Phase 38：Run Comparison 与 Evidence-Grounded Diff

- **状态**：已实现。
- **实现功能**：验证两个终态 Run，确定性比较配置、命令、环境和 Artifact 身份。
- **技术**：Verified Evidence Reader、Typed Diff、Content-addressed Report、Chat Citation。
**核心思路**

比较两个 Run 时，命令、配置、环境 Hash、退出码和 Artifact 内容差异都可以由确定性代码计算，不应让 LLM 浏览两份报告后自由总结。本阶段先构建 Verified Run Snapshot：只接受终态 Run，并逐层验证 Manifest、Catalog 和 Blob 身份，再生成类型化 Diff。

LLM 仅在类型化差异和允许的 Evidence 上解释“这些变化可能意味着什么”，不能改变事实 diff 或引用未验证文件。Comparison 自身也是内容寻址 Artifact，可被 Chat 通过 citation 引用，并进入 Retention 引用图，避免源 Run 被清理后报告失去依据。

**实现流程**

1. 用户选择两个 terminal Run，Comparison Service 校验访问权限、状态和不同身份。
2. Verified Evidence Reader 读取并验证双方 Manifest、Artifact Catalog、Blob Hash 和关键 Process Record。
3. 将配置、Action、环境、资源、状态和指标投影成稳定 `RunSnapshot`。
4. 确定性 Diff Engine 按字段计算 added、removed、changed 和 unchanged，并保留来源 citation。
5. 可选 LLM Explainer 只接收 Diff Bundle，生成受证据约束的解释和不确定性说明。
6. 发布 Comparison Report/Artifact，API 与 Chat 从同一验证结果展示差异。

### Phase 39：Rerun Proposal 与 Immutable Derivation

- **状态**：已实现。
- **实现功能**：从可信父 Run 创建结构化重跑提案，并派生全新 Job/Workspace。
- **技术**：Typed Command Template、Proposal Hash、Saga/Idempotency、Manifest Generation。
**核心思路**

用户通常希望在已有 Run 基础上修改 batch size、环境或命令后重试，但“复制旧状态继续跑”会错误继承 Checkpoint、Approval、PID 和临时路径。本阶段把 Rerun 建模为不可变派生：父 Run 只提供经过验证的输入身份和命令模板，新配置形成 `RerunProposal`，批准提交后创建全新 Job、Run 和 Workspace generation。

派生关系通过 parent run id、proposal hash 和变化集记录，便于后续比较；任何可执行内容变化都重新经过 Preflight、Risk 和 Human Review。Saga/Idempotency 处理“子 Manifest 已创建但 Job 提交失败”等中间状态，防止重复点击产生多个不可区分子任务。

**实现流程**

1. 校验父 Run 为可信终态，并通过 Verified Reader 获取输入、环境和命令模板身份。
2. 根据用户目标创建 Typed Rerun Proposal，只开放允许修改的参数、Profile 或资源字段。
3. 应用编辑后执行本地 Schema/Policy 校验，计算 proposal hash 并展示父子变化。
4. 用户提交带 idempotency key 和 expected parent identity 的创建请求。
5. Saga 先创建 child manifest/workspace generation，再原子提交全新 Job，并记录 lineage。
6. 子 Job 从正常 Graph 入口开始，重新执行选择、Preflight、风险和审批；失败步骤可安全对账重试。

---

## 九、通用 Agent 工程能力：Phase 40-45

### Phase 40：Tool Contract Testing

- **状态**：已实现；Python 3.10 环境专项测试 27 passed。
- **实现功能**：统一 Tool 输入、输出、副作用、Capability、Exposure、错误、超时和
  Hash-only Audit，并校验工具目录中未登记的公开能力。
- **所用技术**：Pydantic JSON Schema、Adapter/Registry、AST Inventory、Contract Test、SHA-256。
**核心思路**

普通 helper、Graph 内部函数和可暴露给模型的 Tool 具有不同信任级别。文件恰好位于 `app/tools` 并不构成授权；只有经过 Controlled Adapter 收窄输入、声明副作用与 Capability、显式注册并通过契约测试的函数，才进入 Agent 可调用目录。高风险 Patch、Executor 和 Resource 能力即使技术上可调用，也继续由专用工作流和审批协议控制。

Tool Contract 把模型调用边界变成可测试协议：输入先由 Pydantic 校验，执行异常映射为稳定错误，输出再次校验，审计只保存参数和结果的 Hash/安全摘要。AST Inventory 再反向检查公开 helper 是否遗漏登记或被意外暴露，使“新增一个函数”不会无声扩大 Agent 权限。

**实现流程**

1. 盘点现有 helper，区分纯只读能力、受控副作用能力和禁止作为普通 Tool 暴露的高风险能力。
2. 为允许能力定义 Pydantic Input/Output Schema、稳定名称、版本、超时、副作用和 Capability。
3. 使用 Controlled Adapter 包装原 helper，在调用前执行路径、大小、权限和参数边界检查。
4. 将 `ToolDefinition` 显式加入 Registry/Catalog；模型只能看到当前策略选择的子集。
5. Registry 执行输入校验、超时调用、错误映射和输出校验，并写入 Hash-only Audit Record。
6. Contract Test 验证成功/失败/超时语义，AST Inventory 验证未登记公开能力和禁止目录不会泄漏。
- **安全边界**：Patch、Executor、Resource 等模块继续由专用 Policy/Approval 控制，不进入普通 Agent Catalog。
- **关键产物**：`ToolContract`、`ToolDefinition`、`ToolExecutionResult`、
  `ToolCallRecord`、默认 Tool Catalog 和 Inventory Report。

### Phase 41：Local Secret Management 与统一脱敏

- **状态**：已实现；Secret 专项与 Container Plan 回归合计 101 passed，Chat Service 的直接 Redactor 装配已在 Phase 42 完成。
- **实现功能**：建立本地认证加密 Vault、版本化 Secret Reference、用途限制、短生命周期
  注入和 value-aware Redaction，防止凭据进入 Prompt、Chat Memory、Checkpoint、Event、
  Log、Artifact 和 Tool Audit。
- **所用技术**：Fernet 认证加密、SQLite、HMAC-SHA256 Fingerprint、Pydantic Reference、
  子进程最小环境、流式 byte Redactor、Canary Boundary Test。
**核心思路**

Secret 的首要原则是“引用流动，明文不流动”。控制面、Agent State、Checkpoint、Approval 和 Tool Audit 只传递 `name + version + fingerprint` 等不可逆 Reference；加密 material 仅保存在本地 Vault。只有 Provider、API Auth、Database Adapter、Execution Runner 和 Resource Worker 等受信任 Adapter，才能按声明用途在最后一刻解析指定版本。

加密静态存储只是第一层，真正风险集中在明文短暂出现后的传播路径。本阶段因此建立统一 value-aware Redactor 和 Scanner：注入子进程时使用最小环境且限制生命周期，日志、Event、Artifact、Chat 问答、错误和容器计划在持久化前脱敏，Canary 测试验证已知 Secret 不会穿过边界。轮换会产生新版本，撤销后旧 Reference 失败关闭，审批 Hash 仍绑定原 fingerprint。

**实现流程**

1. CLI 使用隐藏输入读取 Secret material，通过 Fernet 认证加密后保存到 SQLite Vault。
2. 为每个版本计算 HMAC-SHA256 fingerprint，向控制面返回不含明文的 `SecretReference`。
3. Job、Action 或 Adapter 声明 Secret 用途，Policy 校验调用方、用途、版本状态和批准身份。
4. 受信任 Adapter 在调用前短暂 resolve material，只注入目标请求或子进程所需位置。
5. Provider 响应、stdout/stderr、Event、Artifact、Chat、错误和 Audit 在写出前经过统一 Redactor。
6. Scanner/Doctor/Canary Test 检查存量与关键边界；轮换创建新版本，撤销使旧引用立即 fail closed。
- **安全边界**：不在 argv、State、ProcessRecord 和普通 Agent Tool 中传递 material；第一版不为
  OCI Action 提供不安全降级；轮换或撤销后旧引用 fail closed。
- **教程**：`52_phase_41_local_secret_management_and_redaction.md`。

### Phase 42：Conversation Decision Evaluation

- **状态**：已实现；本次复核对话决策、协议回归、exactly-once 和 Chat Secret 边界专项测试 12 passed。
- **实现功能**：评测 Chat 对只读问答、操作请求、不可用操作、来源 Prompt Injection、
  Citation、Secret Canary 和权限措辞的处理，并把 stale、hash 与幂等协议纳入统一回归门禁。
- **所用技术**：Advisory Intent Schema、Server Capability Projection、Mutation Guard、
  Offline Golden Case、Provider Repetition、Policy/API Contract Test、Safety Gate。
**核心思路**

用户在 Chat 中说“批准这个命令”只是自然语言意图，不是合法审批。模型只允许输出 `read_only`、`operation_request` 或 `unknown` 等 Advisory Intent，以及它认为用户想做的操作种类；它不能生成权威 `AllowedOperation`、目标 Hash、Version、Generation 或 `DecisionEnvelope`。真正可用操作始终由服务端根据最新 Job/Interrupt 状态投影。

本阶段一方面在生产边界加入 Mutation Guard，确保 Chat 没有执行 Tool、不会把分类结果直接送入 resume；另一方面建立专门评测，覆盖不可用操作、来源文本中的 Prompt Injection、虚假权限措辞、stale 决策、Hash 不匹配和幂等重放。Offline Case 验证确定性控制，Provider Repetition 测模型波动，所有权限与安全断言采用 100% Safety Gate。

**实现流程**

1. Chat Service 对用户问题和 Artifact 上下文先执行 Secret Redaction，并构造只读、带 Citation Allowlist 的 Prompt。
2. Structured Output 模型返回 `ChatDraft`、Advisory Intent 和可选 `ChatRequestedOperation`，但不获得任何 mutation Tool。
3. 本地 Projection 校验引用和意图结构，并从 InteractionService 独立获取当前 `AllowedOperation`。
4. Chat 回答只能解释操作是否当前可用并引导用户打开 Decision Card，不能创建批准记录或恢复 Graph。
5. 真实操作由 UI 提交 `DecisionEnvelope`，Policy 校验 version、generation、kind、target hash 和 idempotency key 后才执行 exactly-once resume。
6. Eval Runner 在 offline/provider suite 生成 Decision Observation，Scorer 检查只读边界、引用、Secret、stale/hash、幂等和权限措辞，Safety Gate 未满即失败。
- **安全边界**：Chat 不绑定 mutation Tool，不生成 operation identity，不把模型分类直接转换为
  审批或执行；所有安全断言必须 100% 通过。
- **教程**：`53_phase_42_conversation_decision_evaluation.md`。

### Phase 43：Planner / Executor / Verifier Authority Separation

- **状态**：已实现；Authority Schema、Role Guard、普通执行两段验证、Patch 两段验证、Graph
  路由和专项回归测试均已落地，本次复核 26 passed（Python 3.10.20）。
- **实现功能**：在继续使用单一 LangGraph 的前提下，把建议、受控执行和验证结论拆成三个
  独立 authority；Executor 只产出可验证 Evidence，Verifier 独立形成限定作用域的 Verdict，
  Role Guard 阻止节点越权写入共享 State。
- **所用技术**：Pydantic Role/Evidence/Verification Schema、SHA-256 Attestation Chain、
  Role Output Guard、LangGraph 两段路由、AST Import Boundary、Fail-Closed Verdict、
  Offline Golden Route Eval。
**核心思路**

职责分离的目标不是把一个 Graph 表面拆成三个 LLM，而是分开三种不可混用的权力。Planner 可以
根据论文、仓库和日志提出带内容身份的 Proposal，但不能批准自己的建议，也不能声称测试已通过；
Executor 只能消费已审批且 Hash 匹配的 Action，负责启动受控进程、收集退出状态和 Artifact，
却不能把 `returncode=0` 直接提升为权威成功结论；Verifier 只能读取既有事实，重算身份并形成
`verified / failed / inconclusive`，不能通过重新执行命令为缺失证据“补票”。

本阶段将执行事实和验证 Claim 分成两类不可变对象，并建立
`Proposal Hash -> Approval Hash -> Evidence Hash -> Verification Hash` 的证明链。Role Guard 在
节点输出合并进 State 之前检查字段权限，Hash 不一致、证据缺失或旧审批漂移时统一 fail closed。
普通命令和 Patch 验证都改为“Executor 收集 Evidence -> Verifier 形成 Verdict”的两段流程；
旧 Checkpoint 只通过明确的 legacy route 收尾，绝不重新运行有副作用的命令来伪造新证据。

**实现流程**

1. 定义 Planner、Executor、Verifier 的 Capability、允许字段和禁止字段，并为 Evidence、
   Verification 与 Hash-only Authority Audit 建立严格 Pydantic Schema。
2. 用稳定序列化和 SHA-256 绑定 Action、执行结果、Artifact 路径与验证结论；时间戳和对象自身
   Hash 不参与内容身份，业务字段和上游身份必须参与。
3. 调整普通 Executor，使成功和失败进程都只返回 `ExecutionResult + ExecutionEvidence`，
   不再直接写 `final_status` 或生成验证结论。
4. 新增 Execution Verifier，独立重算 Action/Evidence/Result 一致性，把结论限定在
   `execution_protocol`，再决定进入日志诊断还是最终报告。
5. 将 Patch worktree 检查拆为 Patch Verification Executor 和 Patch Verdict；前者只运行检查，
   后者只依据检查 Evidence 判断是否允许进入 Promotion Review。
6. 在 Graph 注册时采用 `node -> role_guarded_node -> error guard -> LangGraph`，同时保留旧
   `patch_verifier` 节点名和无 Evidence 的 legacy route，安全迁移已有 Checkpoint。
7. 通过 Schema/Hash 单测、Role Guard 越权测试、Verifier AST Import Boundary、Graph Route、
   Fake Runner 端到端测试和 Offline Golden Case 验证职责边界。
- **安全边界**：Verifier 不导入进程、网络或仓库写能力；Planner/Chat 不生成真实审批；Executor
  有 Evidence 时不得写最终结论；Patch promotion 只能消费身份匹配且行为验证通过的 Verdict。
- **关键产物**：`ExecutionEvidence`、`ExecutionVerificationRecord`、
  `PatchVerificationEvidence`、`AuthorityAuditRecord`、Execution/Patch 两段验证路由，以及
  Manifest 中的 Evidence/Verification identity。
- **教程**：`54_phase_43_planner_executor_verifier_authority_separation.md`。

### Phase 44：Long-Running Task Notification 与安全恢复

- **状态**：已实现；通知 Repository、Projector、Service、Retention 和 SQLite JobStore 全局
  Event Cursor 共 26 项专项测试通过（Python 3.10.20）。
- **实现功能**：把持久 Job Event 投影为站内通知 Inbox，支持审批/输入、成功/失败、Worker
  丢失/恢复通知、持久已读、SSE 断线续读，并让用户从通知安全回到当前有效操作。
- **所用技术**：Global Job Event Cursor、SQLite Materialized View、Transactional Projector、
  UNIQUE Source Event、Optimistic Concurrency、Allowed Operation Rebinding、SSE Last-Event-ID、
  Retention Saga。

**核心思路**

通知不成为第二套 Job 状态机，也不由 Graph 节点临时发送。`job_events` 继续是事实来源，
Notification Projector 按全局单调 cursor 增量消费事件，用 source event 唯一约束和“写通知 +
推进 cursor”同事务得到幂等物化视图。浏览器和 API 暂时离线不会影响事实记录，恢复后可以从持久
cursor 补齐。

通知里保存的 Job version、wait generation、expected node 只证明事件发生时的身份，不直接
授权现在执行。Notification Service 每次返回前都读取最新 Job，并与
`allowed_operations(job)` 精确匹配；旧通知保留审计价值，但变为 superseded，旧
DecisionEnvelope 必须返回 409。这避免用户第二天点击旧审批卡时恢复了已经变化的任务。

**实现流程**

1. 为 SQLite/PostgreSQL JobStore 增加跨 Job 的全局 Event Cursor，并冻结通知所需事件身份。
2. 定义 Notification Schema、Repository Port 和独立 SQLite 表，建立 source event 唯一约束。
3. 实现确定性 Projector，把等待、终态、lease 丢失和恢复事件映射为通知并原子推进 cursor。
4. 实现 Notification Service，读取通知后基于最新 Job Policy 重新绑定 current operation。
5. 提供 Inbox、未读、已读和 Notification SSE API，前端只做轻量 badge、列表与跳转。
6. 将 Notification DB 纳入 readiness、Storage Inventory 和按 Job 清理的 Retention Saga。
7. 用 Repository、重放、stale operation、SSE、lease recovery、API 和相邻阶段回归完成验收。
- **安全边界**：通知快照不是授权；未知外部进程副作用仍进入 reconciliation；不因通知恢复绕过
  Phase 42 Decision Protocol 或 Phase 43 authority guard；第一版不引入邮件、短信和消息队列。
- **关键产物**：`NotificationRecord`、`NotificationProjection`、持久 Projector Cursor、
  `NotificationService`、Notification SSE 和 Retention adapter。
- **教程**：`55_phase_44_long_running_task_notification_and_recovery.md`。

### Phase 45：Verified Failure Memory 与诊断检索

- **状态**：已实现；当前实际 6 个专项测试文件合计 22 passed（Python 3.10.20）。
- **实现功能**：从可信终态失败 Run 建立可晋升、可撤销的失败案例；人工确认并由真实派生 Run
  验证后形成 `run_verified` 先例；新失败进入 Debug 时检索相关案例，但不赋予执行权限。
- **实现技术**：Pydantic Failure Case Schema、Deterministic Fingerprint、SQLite CAS/Idempotency、
  Verified Run Evidence Reader、Rerun Lineage、Verification Attestation、Deterministic Rerank、
  Evidence Pack Allowlist、Retention Reference、Golden Eval。

**核心思路**

本阶段不直接实现泛化长期记忆，而是先选择“历史失败经验”这个来源和验证结果都相对明确的窄场景。
一次失败先从可信 Run Manifest、StageError、DebugReport 和发布 Artifact 生成 `candidate`；用户确认
诊断与修复方向后进入 `human_confirmed`；只有一个真正由失败 Run 派生的子 Job 在独立 Verifier 下
得到 `execution_protocol=verified`，案例才能进入 `run_verified`。过时案例只进入 `deprecated`，
不能原地复活。

错误症状和适用环境分开建模：确定性 fingerprint 描述 stage、code、exception、frame 和稳定 token，
环境身份描述仓库 commit、Execution Profile fingerprint 与 backend。检索同时返回 authority、
compatibility 和 score breakdown。即使历史案例已经验证，环境漂移时也只能作为需要复核的参考；
检索结果只进入 Debug Evidence Pack，仍不能创建 Action、Approval、Patch 或执行结果。

**实现流程**

1. 定义 Failure Signature、Source/Environment/Evidence、Remedy、Confirmation、Run Verification 和
   Case Lifecycle Schema，并用稳定 Case Hash 绑定语义内容。
2. 从 `VerifiedRunEvidenceReader` 读取终态失败 Run，只打开 Catalog 绑定且大小、Descriptor、Blob
   stat、SHA 与 JSON Schema 校验通过的 Artifact。
3. 使用去除绝对根、行号、PID、UUID 和地址噪声的确定性算法生成错误 fingerprint，候选文本经过
   Phase 41 统一脱敏后写入独立 SQLite Repository。
4. 通过 expected version、expected case hash 和 Idempotency-Key 推进 candidate、人工确认、验证
   和 deprecate；所有状态只允许单向迁移。
5. 验证升级要求 child Job 的 Phase 39 lineage 精确指向源失败 Run，并校验 child manifest、
   proposal hash、ExecutionVerificationRecord 和 verification hash。
6. Retriever 先按 stage/code 缩小候选，再按 signature、frame、token、环境和 authority 确定性
   rerank，返回有界 Failure Case Pack 和可解释 score breakdown。
7. `log_debug_node` 把 Pack 作为不可信历史证据加入 Prompt，并在本地过滤模型生成的 case id；
   Authority 测试确保它不能写执行或审批字段。
8. 活跃 Case 为源/验证 Job 建立 Retention 引用，DB/WAL/SHM 纳入 Inventory，并通过 Secret canary、
   Prompt injection、Golden 排序和相邻阶段回归完成验收。
- **安全边界**：检索不是授权；candidate/human_confirmed 不代表修复成功；run_verified 只证明限定
  执行协议；不保存完整日志/命令/Patch；不从任意用户文本创建可信案例；不自动执行历史修复。
- **关键产物**：`FailureCaseRecord`、`FailureSignature`、`FailureEvidenceReader`、
  `SqliteFailureCaseRepository`、`FailureCaseService`、`FailureCaseRetriever`、
  `debug/failure_case_pack.json` 和 Failure Memory Golden Cases。
- **教程**：`56_phase_45_verified_failure_memory_and_diagnostic_retrieval.md`。

### Phase 46：Project-Scoped Long-Term Memory 与可撤销事实治理

- **状态**：源码与专项测试已经落地；Identity、Repository、Evidence、Service 四组 44 个用例已
  通过执行进度点，API/Chat/Retention/Authority 集成组待单独完成回归确认。
- **实现功能**：建立显式 Project Registry 和 Job Binding，把跨 Job 稳定的用户约束、数据集逻辑
  绑定、默认 Execution Profile、复现目标与构建前置条件保存为有来源、有 Hash、可确认、可纠正、
  可撤销、可删除、可过期的项目事实，并作为只读 `project_fact` 来源进入 Chat Grounding。
- **实现技术**：Pydantic Typed Fact Schema、Project/Workspace Anchor、SQLite WAL、CAS、Idempotency、
  Append-Only Revision、Deleted Tombstone、Chat User Message Hash、Bounded Fact Pack、Citation Schema
  Versioning、Retention Reference、Readiness、Storage Inventory 和 Secret Scanner。

**核心思路**

项目长期记忆不复用 Conversation Memory 表，也不把 Failure Case 当成项目通用规则。系统先由用户
显式注册 `ProjectRecord`，冻结 anchor Job version、Workspace Manifest hash、论文 SHA 与仓库 commit；
后续 Job 通过明确 API 加入项目，不能根据本机路径、目录名或语义相似度自动归组。这样项目身份可以
跨 Run 和 commit 保持稳定，同时每次绑定仍保留当时的 Evidence identity。

一条事实先进入 `proposed`，只有已认证用户明确确认后才进入 `confirmed` 和 active pack。纠正不原地
覆盖正文，而是在一个 SQLite 事务中把旧事实变为 `superseded`，同时创建绑定旧 fact id/hash 的新
confirmed revision；撤销和过期使事实立即退出上下文；删除只允许对 proposed 或 terminal fact 执行，
正文被清空但 content hash、source 与终态事件保留为 tombstone。读取路径同步检查 `expires_at`，不依赖
后台 sweep 的及时性。

Project Fact 是信息而不是 authority。即使用户确认“默认允许联网”或文本中包含命令，也不能覆盖
Execution Profile、AllowedOperation、Approval 或 Executor。第一版只把 active confirmed facts 构造为
有界、可 Hash 的 Chat Grounding Source；模型引用仍受预算后 citation allowlist 限制。新增 Citation
字段时按 `phase36-v1`、`phase38-v2`、`phase46-v3` 分版本计算 Memory Hash，避免破坏历史对话记忆。

**实现流程**

1. 定义 Project、Anchor、Job Binding、类型化 Fact Value、Source、Confirmation、Terminal Event、
   Revision Link、Pack 与 mutation request/response Schema。
2. 从 JobStore 读取并校验 Workspace Manifest，提取唯一 paper SHA 与 repository identity；创建项目时
   原子写入 Project 和 anchor binding。
3. 实现 SQLite Project/Binding/Fact/Operation 表，以 `BEGIN IMMEDIATE` 完成 CAS、幂等、slot 唯一和
   correction 双记录原子切换。
4. Manual proposal 保存脱敏用户声明；Chat proposal 回读精确 `role=user` 消息并校验 message id、
   sequence 和 hash，拒绝 assistant 与 Conversation Memory 作为可信 source。
5. Service 推进 propose、confirm、correct、revoke、expire、delete 和 archive；Profile fact 的
   fingerprint/policy hash 由服务端真实配置计算，Dataset fact 只保存 Worker label。
6. Retriever 只返回 active Project 中尚未过期的 confirmed facts，按 category/key 稳定排序并受条数、
   字符预算和 Pack Hash 约束。
7. 扩展 Chat Citation 和 Memory Schema，把 Project Fact 作为只读 GroundingSource；兼容旧 Memory
   Hash，并继续执行 Prompt 数据隔离、operation guard 和 citation allowlist。
8. 活跃 Chat-backed fact 为源 Job 建立 Retention 引用；DB/WAL/SHM 纳入 Inventory、readiness 与
   Secret canary scan，最后执行生命周期、并发、Chat、Authority 和相邻阶段回归。
- **安全边界**：模型回答不能自动确认事实；Fact 不从路径隐式划分项目；Dataset 不保存宿主机路径；
  proposed/expired/revoked/deleted 不进入上下文；Fact 不改变 Action、Policy、Approval 或 Execution；
  Project Binding 本身不永久 hold 所有历史 Job。
- **关键产物**：`ProjectRecord`、`ProjectJobBinding`、`ProjectFactRecord`、
  `SqliteProjectMemoryRepository`、`ProjectMemoryService`、`ProjectFactRetriever`、`ProjectFactPack`、
  Project Memory API 和 `project_fact` Chat Citation。
- **教程**：`57_phase_46_project_scoped_long_term_memory_and_revocable_fact_governance.md`。

### Phase 47：检索质量自适应优化与可评测策略路由

- **状态**：源码与专项测试已落地；policy_schemas、policy、policy_eval、ranking 扩展、
  service 扩展、code_search_node 集成、config/state/.env.example 更新以及 4 组 11 个专项用例
  均已通过，Phase 20/21 相邻回归通过，Ruff 通过。
- **目标功能**：在 Phase 20/21 已有 sparse/dense 检索器之上增加确定性 Query Feature、版本化
  Retrieval Profile 和 Policy Rule，根据精确错误、symbol/path、论文语义或可信 traceback 选择
  已评测策略；支持 `off`、`shadow`、`active` 三种模式，并通过离线 baseline/challenger 对比生成
  只读 Promotion Proposal。
- **计划技术**：Pydantic strict schema、canonical JSON、SHA-256 identity、deterministic feature
  extraction、weighted RRF profile、capability-aware fallback、run-native Decision Artifact、Recall@K、
  MRR、Citation Coverage、provenance hard gate、Golden fixture dense hit 和 shadow deployment。

**核心思路**

本阶段不新增检索模型，而是治理现有通道的选择。查询正文先由确定性规则提取错误特征、symbol/path
线索、论文 Evidence 数量和可信 traceback path，Decision 只持久化 query hash 与有限特征；版本化
Policy 再把 Query Kind 映射到 Retrieval Profile。Profile 只能控制通道、权重、Top-K 和 RRF 参数，
不能改变 repo root，也不能授予 Dense 上传权限。Dense 是否可用仍由 Settings、Secret、上传授权和
Provider readiness 决定，不可用时只能进入显式离线 fallback。

上线采用兼容优先顺序：`off` 完全保留旧检索，`shadow` 记录 `applied=false` 的建议但仍执行旧策略，
`active` 才应用通过评测的 Profile。Golden Eval 对同一 Case 成对运行 baseline 和 challenger，比较
Recall、MRR、Citation Coverage、provenance、forbidden path 与延迟；只有通过硬门禁并产生明确
质量收益时才生成 Promotion Proposal。Proposal 不拥有写生产配置的权限，仍需人工检查、提升
policy/profile version 并重新回归。

**计划实现流程**

1. 定义 Query Feature、Profile、Rule、Policy、Decision、Golden Case、Metrics 和 Promotion Schema；
2. 实现 canonical JSON、Policy/Profile/Query/Decision Hash、本地有界 Policy loader 和确定性分类；
3. 为 `ranking.py` 增加显式 channel allowlist，为 `service.py` 增加 profile weights/top-k/rrf 参数；
4. 增加默认离线 fallback Policy，配置 mode/path，并只把 Policy Hash 和 Decision path 写入 State；
5. 在 `code_search_node` 中先做能力内预判，再按实际 Dense readiness 生成最终 Decision；
6. off/shadow 保持旧参数，active 才把 selected profile 传给 Evidence Service；
7. 每个 mapping target 发布不含原始 query、源码、向量和 Secret 的 Decision Artifact；
8. 用固定仓库与模拟 Dense hit 运行离线 Policy Eval，产出 JSON、Markdown 和 Promotion Proposal；
9. 依次完成 schema/router/service、Phase 20/21 相邻回归以及 off/shadow/active 手工验收；
10. 任何回归通过 `RETRIEVAL_POLICY_MODE=off` 回滚，不修改历史 Run。

- **安全边界**：LLM、Chat 和 Project Fact 不能写 Policy mode；Policy 不能启用 Dense/网络/Secret；
  shadow 不能改变 Evidence；检索分数不替代路径、revision 和 Hash；Proposal 不自动改生产配置。
- **计划关键产物**：`RetrievalPolicyConfig`、`RetrievalProfile`、`RetrievalDecision`、
  `config/retrieval_policy.json`、`retrieval_policy_eval.json`、`retrieval_policy_eval.md` 和
  `retrieval_policy_promotions.json`。
- **教程**：`58_phase_47_adaptive_retrieval_quality_optimization.md`。

### Phase 48：Agent Skill / Plugin 机制与受约束能力扩展

- **状态**：源码与教程均已完成；本次复核 8 个专项测试文件共 `23 passed`（Python 3.10.20），默认
  Feature Flag 仍为关闭。
- **目标功能**：把已经稳定的领域流程封装为有 Manifest、类型化输入输出、Tool/Capability 声明、
  内容身份、调用预算、审计记录和离线 Eval 的 Skill。第一版实现 `cuda_build_diagnosis`，但 Plugin
  Package 只能携带 Manifest 和 Hash 已声明的只读资源，不能动态加载包内 Python/native/shell 代码。
- **实现技术**：Pydantic strict schema、受控目录 Loader、symlink/path/resource Hash 校验、静态 builtin
  implementation allowlist、builtin 源码与 Skill/Tool Contract 组合 SHA-256、expected hash stale 防护、Restricted
  Runtime、三层 Capability 交集、Authority Key Guard、Feature Flag、Hash-only Audit、Golden Fixture 和
  Import Boundary 测试。

**核心思路**

Skill 是多个 Tool 组成的可复用领域工作流，Plugin Package 是 Skill 的数据分发与身份边界，两者都不
等于“允许任意插件代码进入 Host 进程”。第一版 Manifest 的 `implementation_id` 只能命中主项目
`app/skills/catalog.py` 中显式登记的 builtin 实现；Package 中出现未声明文件、符号链接、`.py`、`.so`
或资源 Hash 漂移时直接拒绝加载。这样先建立稳定扩展契约，将外部代码隔离、签名和依赖解析留给未来
真正需要第三方 Plugin 时处理。

Skill Handler 只能获得提供 `call_tool()` 的 Restricted Runtime。一次调用要求 Tool Contract 所需能力
包含于 Manifest 声明能力，并且 Manifest 能力继续包含于 Host 本次授予能力；同时 Tool 必须是
`AGENT_READ_ONLY`、幂等且副作用限于无副作用、文件读取或显式受限的 `rg` 进程。Manifest 是需求声明，
不是授权来源。Skill 输出先通过 Pydantic，再递归拒绝 Action、Approval、Execution、Patch 和 Verdict
字段，所以诊断建议仍必须回到 Planner -> Human Review -> Executor -> Verifier 主链。

Skill 内容身份绑定 Package、资源、builtin 实现源码、输入输出 Schema 和依赖 Tool Contract。调用者提交之前读取的
`expected_skill_sha256`；Manifest、Schema 或 Tool 漂移后旧请求在 Handler/Tool 执行前返回 stale。
CUDA 诊断通过已有日志与搜索 Tool 确定性产生 finding code、仓库相对路径、Tool Call Evidence Ref 和
人工检查建议，不额外调用 LLM。`log_debug_node` 只在 CUDA/build 与 failure 特征同时出现时旁路调用，
失败仅追加 warning，不能覆盖当前实验原始 `StageError`。

**实现流程**

1. 定义 Manifest、Invocation Context/Request、Tool Call Ref、Result、Failure、Audit Record 与 Catalog
   Schema，并拒绝未知字段和重复声明；
2. 在受控 `agent_skills/` 直接子目录发现 Package，有界读取 Manifest/Resource，拒绝 path escape、
   symlink、未声明文件、超大文件与资源 Hash 失配；
3. 建立 Restricted Runtime，逐次校验 Tool 声明、版本、exposure、幂等性、副作用、Capability 和调用
   预算，再以 `caller_kind=agent` 进入现有 Tool Registry；
4. 建立 Skill Registry，将 Manifest 与静态 builtin definition、Pydantic Schema 和 Tool Contract 绑定，
   计算 Skill Hash，并在 disabled/version/stale/capability 失败时保证零 Handler/Tool 调用；
5. 实现确定性 CUDA Build Diagnosis，调用日志读取、traceback 提取、错误分类、仓库路径校验和关键词
   搜索，输出 finding、证据引用、相关文件、检查建议与 `requires_main_agent_proposal=true`；
6. 增加 Package Manifest、默认关闭配置、Capability allowlist、可选 State 字段，以及 validate/list/
   invoke CLI；
7. 在 `log_debug_node` 中确定性选择 Skill，将 typed output 标记为不可信证据加入 Prompt，写 Result 和
   Hash-only Invocation Artifact，失败时保留原 Debug 路径；
8. 使用离线仓库/日志 Fixture 验证 `NVCC_NOT_FOUND`、真实 `setup.py` Evidence、最多五次 Tool Call、
   Authority forbidden keys 和输出置信度；
9. 增加 Loader、Runtime、disabled/stale、Authority、Import Boundary 和节点 Feature Flag 负向测试，
   并回归 Tool Contract、Secret、Authority、Failure/Project Memory 与 Retrieval Policy；
10. 先以 Feature Flag 关闭合并，再只启用一个 builtin Skill；发生回归时关闭全局开关，不改写历史
    Checkpoint 或 Artifact。

- **安全边界**：Plugin Manifest 不决定 import；Skill 不持有 Shell、Executor、Approval、Secret 或
  数据库；proposal-only 不等于可执行；审计不保存日志/源码正文；disabled/stale/capability denied
  必须零调用；同进程 duration 仅为软预算，不能冒充第三方代码强隔离。
- **计划关键产物**：`SkillManifest`、`SkillRegistry`、`SkillRuntime`、`SkillInvocationRecord`、
  `cuda_build_diagnosis`、`agent_skills/cuda_build_diagnosis/skill.json`、Skill Result/Invocation Artifact
  和 Offline Golden Case。
- **教程**：`59_phase_48_agent_skill_plugin_mechanism.md`。

### Phase 49：跨论文 Evidence Knowledge Base 与可治理关系图

- **状态**：已实现；本次复核 11 个专项测试文件共 `19 passed`（Python 3.10.20）；默认
  `KNOWLEDGE_BASE_ENABLED=false`。
- **目标功能**：把多个终态 Job 已发布的 Paper Document、Section、Fact、Paper-Code Mapping 投影成
  source-scoped Entity、Typed Relation 与独立 Provenance，在不物理合并同名概念的前提下提供跨论文
  查询、候选等价关系、人工 CAS Review、Chat Citation 和 Retention 引用治理。
- **实现技术**：Pydantic strict schema、VerifiedRunEvidenceReader、Artifact Catalog/Descriptor/Blob
  size 与 SHA-256 校验、内容寻址 Entity/Relation/Source Snapshot、SQLite WAL、原子 Batch、Operation
  Ledger、Idempotency-Key、Relation Version/Hash CAS、确定性词法召回、最多两跳图遍历、Query Pack、
  Chat Memory phase49-v4、Retention Port 和离线 Golden Eval。

**核心思路**

同名不等于同一实体。论文中的 Concept、Dataset 和 Metric 首先建立论文作用域内的 mention instance；
相似名称只允许形成 `equivalent_to(candidate)`，用户核对两侧 Evidence 后才能确认，确认后仍可撤销。
这样既保留每篇论文自己的语义和来源，也避免 Embedding、LLM 或规范化名称把不同 split、protocol 或
方法错误合并。代码映射同样只形成候选关系，不因为模型置信度高就升级为权威事实。

Entity/Relation 的稳定语义身份与某次 Run 的来源必须分离。同一论文重复执行可以复用 Entity，只新增
绑定 Job、Run、Artifact Hash、页码/block 或代码行的 Provenance；归档某个 Source Snapshot 后，仅该
来源退出检索，其他活动来源仍可支持同一节点。Repository 在一个 `BEGIN IMMEDIATE` 事务中写入 Batch
和幂等响应，任何 Hash 冲突或 Provenance 缺失都整体回滚。

检索只提供候选证据，不拥有 Authority。默认 Query 只遍历 `asserted/confirmed`，最大深度为 2，并将
候选关系单独返回。Chat Citation 绑定 Query Pack Hash、Subject Hash 和 Evidence Ref ID；Knowledge
内容不能改变 Tool Capability、审批、Action、Executor 或 Verifier。活动 Ingestion 同时作为 Retention
引用，防止原 Artifact 被 GC 后知识结论失去可验证来源。

**实现流程**

1. 定义 Entity、Relation、Evidence Ref、Provenance、Source Snapshot、Ingestion、Review、Query Pack
   等严格 Schema，并建立规范化 JSON、SHA-256、稳定 ID 与状态迁移纯函数；
2. 从 `job_id` 经 Verified Run 和固定 Artifact 路径读取论文结构、事实与 Mapping，逐层校验
   Catalog/Descriptor/Blob、Workspace paper SHA 和 Fact section identity；
3. 由无数据库、无 LLM 的 Projector 确定性生成 Paper、Section、Claim、Concept、Dataset、Metric、
   Repository Symbol 及 asserted/candidate Relation，每个 Subject 都附 Provenance；
4. 使用 SQLite 原子写入稳定节点、关系、Ingestion、Provenance 和 Operation Ledger，重复 Snapshot
   幂等，已确认关系在新观察到来时只追加 Provenance、不降级状态；
5. 实现词法候选召回与最多两跳遍历，活动 Provenance 过滤归档来源，严格区分 authoritative 和
   candidate Relation，并生成 Subject-to-Evidence 映射；
6. 提供 ingest/query/candidate/equivalence/review/archive CLI 与 API，候选等价要求两个 Entity 的旧
   Hash、服务端相似度门禁和两侧活动 Provenance；
7. 扩展 Chat Context/Citation/Prompt 和 Conversation Memory v4，保持 Phase 36/38/46 历史 Hash
   兼容，禁止候选关系进入默认回答；
8. 将 Knowledge DB 纳入 Readiness/Inventory，把活动 Source Job 加入 Retention Hold；
9. 用两篇离线 Fixture 测试身份、原子性、stale、候选隔离、Citation、Retention、Authority 和 Golden
   Recall，再用 PSTNet/P4Transformer 真实 Job 手工验收；
10. 先关闭 Feature Flag 完成专项与全量回归，再按隔离 DB、CLI、API、Chat 的顺序灰度启用。

- **安全边界**：不自动合并同名实体，不让相似度确认关系，不读取任意路径/SQL，不保存 PDF/源码全文，
  不导入 Shell/Executor/Patch/Approval，Knowledge 不证明当前实验成功；关闭 Feature Flag 后 Retention
  仍需读取旧 DB 的活动引用。
- **关键产物**：`KnowledgeEntityRecord`、`KnowledgeRelationRecord`、`KnowledgeProvenanceRecord`、
  `KnowledgeGraphBatch`、`SqliteKnowledgeRepository`、`KnowledgeRetriever`、`KnowledgeQueryPack`、
  Knowledge Chat Citation 和 `cross-paper-offline-v1` Golden Report。
- **教程**：`60_phase_49_cross_paper_evidence_knowledge_base.md`。

### Phase 50：模型路由、成本预算与 Provider 治理

- **状态**：源码已按教程实现，默认 `MODEL_ROUTING_MODE=off`。本次复核在 API 组前已有 68 passed，
  Eval/Authority 两组另有 21 passed；`tests/test_model_routing_api.py` 未取得完整退出结果，仍需单独收口。
- **目标功能**：让论文抽取、代码映射、实验规划、诊断、修复、Chat、Memory Compaction 和 Embedding
  都通过统一 Model Gateway 声明任务，在受信任 Provider/Secret 边界内完成确定性 Profile 选择、调用前
  预算预留、重试总用量结算、价格快照审计和 Golden Promotion Gate。
- **计划技术**：Pydantic strict schema、Task-aware deterministic router、版本化 JSON Policy、受信任
  Provider Binding、SQLite WAL、`BEGIN IMMEDIATE` Reservation、整数 micro USD、Decision/Policy Hash、
  Structured Output attempt usage 聚合、Embedding token 估算、off/shadow/active 灰度、Read-only API、
  CLI Doctor/Preview/Reconcile 和离线 Eval Proposal。

**核心思路**

路由不是让另一个 LLM 判断“该使用哪个模型”，而是把每次真实 Provider 调用建模为类型化 Task Request。
Request 只包含 task kind、workload、所需 structured capability、上下文/输出预算、质量等级和 Prompt/Schema
Hash；确定性 Router 按版本化 Policy 的候选顺序选择第一个满足能力、上下文和质量门禁的 Profile。
Policy 只能引用 `primary_chat`/`primary_embedding` 等受信任 Binding，不能携带 endpoint、Secret Name、
Header 或 import path，真正的凭证只在预算预留成功后由 Provider Factory 解析。

成本控制采用“先预留、后结算”。active 模式在一个短 `BEGIN IMMEDIATE` 事务中把当天和当前 Job 已结算
用量、活跃 reservation 与本次最大重试上限合并检查；超限时在 Secret 和网络请求前拒绝。完成后汇总
所有 Validation Retry 与 Transport Retry 的 usage，Provider 元数据完整时标记 `provider_reported`，
Embedding 或兼容接口缺失时标记 `estimated/reservation_upper_bound`。崩溃遗留 reservation 不静默释放，
而是保守结算为 `usage_unknown`，避免 Provider 已计费而本地记为零。

`off/shadow/active` 把兼容性、观测和行为变化分开。off 保持现有 legacy 行为且不写 Ledger；shadow 计算
建议 Profile 但仍执行 legacy，并建立用量基线；active 才执行 selected Profile 并强制预算。便宜模型必须
同时通过 Route Golden 和 Phase 18/37/42/47/49 对应业务 Golden，系统只生成 Promotion Proposal，
不会自动改写 Policy。模型强弱也不改变 Planner/Executor/Verifier、Human Review 和 Tool Authority。

**计划实现流程**

1. 定义 Task、Profile、Pricing、Route Request/Decision、Reservation、Usage、Invocation 和 Eval Schema，
   建立规范化 JSON、Token 估算、整数成本和 Decision Hash；
2. 有界读取本地 Policy，解析受控模型占位符，校验 Profile/Route 唯一性、workload、capability、context、
   output 与价格形态，拒绝路径逃逸和 symlink；
3. 实现确定性 Router，active 选择合格 candidate，off/shadow 使用 legacy，并在 active 拒绝未定价 Profile；
4. 使用 SQLite 原子预留 daily/per-job token/cost，幂等 settle，区分 settled/active reservation，并将过期
   reservation 保守转成 `usage_unknown`；
5. 建立 Trusted Provider Factory，只有它能把静态 Binding 映射到 Settings/Secret 和 Provider Client；
6. 建立 Model Gateway，按 route -> reserve -> secret -> invoke -> usage -> settle 编排，复用现有 Structured
   Output retry engine，并为 Embedding 增加 cache-identity-safe wrapper；
7. 接入论文抽取、Mapping、Plan、Debug、Repair、Chat、Memory 和 Dense Retrieval；Section Cache 与 Chat
   Memory Hash 绑定实际执行模型，确定性 reducer 和原 Authority 校验保持不变；
8. 增加只读 Budget/Invocation API，以及 doctor、route preview、summary、list、reconcile CLI；
9. 用 Fake Provider 离线测试预算前置、并发预留、重试 usage、stale decision、Secret 零解析、Authority 和
   API；再用业务 Golden 形成待人工评审的 Profile Promotion Proposal；
10. 按 off、shadow、单一低风险 Task active、其他 Task active 的顺序灰度，异常时回到 off 并保留 Ledger。

- **安全边界**：路由不读取 Prompt 指令决定模型；Policy 不拥有 endpoint/Secret；active 先 reserve 后
  Secret；Ledger 不保存 Prompt/Output；估算不能冒充 Provider usage；Promotion 不自动写 Policy；强模型
  不增加节点权限；成本估算不冒充 Provider 最终账单。
- **计划关键产物**：`ModelRoutingDocument`、`ModelRouteDecision`、`ModelInvocationRecord`、
  `SqliteModelLedger`、`ModelRouter`、`TrustedProviderFactory`、`ModelGateway`、`RoutedEmbeddingBackend`、
  Model Budget Summary、Routing Golden Report 和 Promotion Proposal。
- **教程**：`61_phase_50_model_routing_cost_budget_and_provider_governance.md`。

### Phase 51：受限研究型浏览器 Agent

- **状态**：源码已按教程实现，默认 `RESEARCH_BROWSER_ENABLED=false`。本次复核 13 个非 API 专项文件
  共 112 passed；`tests/test_research_browser_api.py` 在当前 Python 3.9 环境首个用例超过 30 秒未结束。
- **目标功能**：在不把通用 HTTP、Shell、网页交互或 Resource Approval 交给模型的前提下，让用户显式
  创建 Research Session，经过可信 Search、受控 Open、确定性 Extract/Cite、结构化 Synthesis 形成
  可验证 Evidence Pack，并把严格资源候选转交现有人工审批流。
- **所用技术**：Pydantic strict schema、版本化 Research Policy、专用 Search Secret Use、受信任
  Search Provider Binding、HTTPS/host/DNS/redirect/robots/媒体/字节/时间多层校验、无 Cookie 且
  `trust_env=False` 的流式 HTTP Transport、HTML/PDF 有界抽取、Snapshot/Block/Citation/Pack SHA-256、
  单个复合 NETWORK_READ Tool、Restricted Skill、SQLite WAL、Version/Lease、Model Gateway、Resource
  Idempotency Bridge、Chat Web Citation、Readiness、Golden Eval 和 Feature Flag 灰度。

**核心思路**

浏览器能力不是“给 LLM 一个可以访问任意 URL 的工具”，而是把联网研究拆成确定性控制面。Search
Provider endpoint 固定在受信任 Adapter 中，Search 结果只是线索；每个待打开 URL 都要重新规范化并
验证 HTTPS、默认端口、请求级 host 子集、公共 DNS 地址和每一跳 redirect。robots、响应 media type、
单页/总字节、PDF 页数、Block 数和总耗时继续限制资源消耗。应用层 DNS 检查不能冒充网络沙箱，生产
启用还需要 egress proxy 或固定解析结果的 Transport。

网页内容始终是不可信数据。HTML/PDF 先由确定性 Extractor 转成有界 Block，再由 Collector 创建同时
绑定 Snapshot body hash、Block ID 和 excerpt hash 的 Citation。LLM 只能通过 Phase 50 的 Model Gateway
组织已提供 Evidence，并从服务端允许集合选择 Citation/Candidate ID；未知 ID、本地 Hash 不匹配、预算
不足或结构化失败都不能变成可信结论。URL 负责定位，内容 Hash 才证明回答引用的是哪一版网页。

外部线索到本地资源需要再次降权。只有已抓取完整 PDF body hash 或 GitHub exact commit 可以形成
Resource Candidate，Candidate 仍不是 ResourceRequest、Approval 或 Download。用户提交 Candidate ID、
Candidate Hash 和 Pack Hash 后，Service 才用服务端保存的 URL/Hash 构造 Phase 29 Request；稳定
Idempotency Key 补偿两个 SQLite DB 之间的非原子写入，Research Browser 永远不调用 approve 或 worker。

Chat 同样没有网络 Authority。它只读取 `succeeded`、绑定当前 Job、Pack Hash 可重算的 Evidence Pack，
并生成含 Pack/Snapshot/Citation/Excerpt 完整身份的 `source_type=web` Citation。Research Session 使用
Version 和 Lease 防止旧客户端与旧 Worker 写入，Reconciler 将崩溃遗留运行态转为可重试；Policy 变更后
旧 Session 必须重新提交，不能在新边界下继续执行旧 Policy Hash。

**实现流程**

1. 定义 Request、Search Hit、Snapshot、Block、Citation、Resource Candidate、Report、Pack、Session、
   Event 和 Public Projection Schema，并实现规范化 JSON、URL、Hash、稳定 ID 与引用完整性校验；
2. 建立版本化 Research Policy，限定可信 Search Binding、host、媒体类型、redirect、robots、网络超时、
   单响应/总字节、PDF 页数、Block 和 Citation 数，拒绝路径逃逸、symlink 和请求 host 扩权；
3. 实现专用 Search Secret Use 和受信任 Provider Adapter，固定 endpoint，关闭代理环境与自动 redirect，
   流式限制响应体，原始 Query/Header/Provider body 不进入日志；
4. 实现 URL/DNS/redirect/robots Guard 和有界 Fetcher，再用无 JavaScript 的 HTML Parser、纯文本 Parser、
   PyMuPDF Page Extractor 生成确定性正文 Block；
5. Collector 按 Request host 子集执行 Search -> Fetch -> Extract -> Rank -> Cite，只生成完整 PDF Hash 或
   exact Git commit Candidate，单页失败可跳过，累计预算超限则终止；
6. 通过一个 NETWORK_READ Tool 和一个 builtin Restricted Skill 暴露复合能力，Manifest、Tool Contract、
   Host Context 三层同时授予 `network.read.research`，普通 Chat/Skill 不获得该能力；
7. 使用 SQLite 在同一事务提交 Session 状态与 Event，以 Version/Lease 控制 start/complete/fail，Pack 提交
   同时验证 Session、Request、Policy 和 Pack Hash，Lease 过期后由 Reconciler 回收；
8. 通过 `web_research_synthesis` Task 调用 Model Gateway，Prompt 把 Evidence 标记为不可信数据，本地验证
   Citation/Candidate 集合；预算拒绝或无效输出降级为 evidence-only/budget-denied Pack；
9. 增加 Resource Bridge、Public API、CLI、Doctor、Readiness、Retention Inventory 和低基数 Metrics；
   Resource Bridge 只提交服务端 Candidate，并保持 `awaiting_approval`；
10. 让 ChatContextBuilder 只读取当前 Job 的成功 Pack，扩展 Web Citation 和 Memory 兼容；使用 Fake Search、
    Fake Transport/DNS/robots/Gateway 做离线 Golden，再以 PSTNet 标题做一次真实 Provider 受控验收；
11. 按 Feature 关闭、Fixture、CLI、API、Chat 读取、egress guard 的顺序灰度；回滚只关闭 Flag，不改写
    历史 Pack、Resource 或 Hash。

- **安全边界**：不执行 JavaScript，不登录/提交表单/上传，不访问任意 endpoint，不信任网页指令，不调用
  Shell，不直接下载或审批资源，不让 Chat 自动搜索，不把应用层 SSRF 检查冒充强网络隔离，不把 URL
  冒充内容身份，不在 API/日志/Metric 中返回 Secret、Header、raw body、幂等键或 Lease。
- **关键产物**：`ResearchPolicyDocument`、`ResearchRequest`、`ResearchSourceSnapshot`、
  `ResearchCitation`、`ResearchEvidencePack`、`BraveSearchProvider`、`BoundedResearchFetcher`、
  `ResearchCollector`、`restricted_web_research` Skill、`SqliteResearchRepository`、
  `ResearchSynthesizer`、`ResearchBrowserService`、Web Chat Citation 和 Research Golden Report。
- **教程**：`62_phase_51_restricted_research_browser_agent.md`。

### Phase 52：受约束 Tool Calling 与复现 Agent 高层编排

- **状态**：源码已按教程实现；默认 `CHAT_TOOL_CALLING_ENABLED=false`。本次相关专项回归共 51 passed。
- **目标功能**：让 Chat Agent 根据用户问题按需选择当前复现 Job 的高层只读工具，动态补充状态、失败上下文
  和已有 Evidence；同时保持原 LangGraph 复现工作流、Decision Protocol、Executor、Repair 和 Final Report
  的权威边界不变。
- **技术**：Provider 原生 `bind_tools()`、静态 Tool Alias/Contract Binding、Pydantic strict input/output、
  受信任 Job Scope 和 Capability 注入、单调用 ToolMessage 配对、有界多轮循环、重复调用指纹、结果字符预算、
  Phase 50 Model Route/Reservation/Usage Ledger、GroundingSource/Citation 合并、SQLite Chat Trace Summary、
  Offline Scripted Model、Authority Negative Test 和 Feature Flag 灰度。

**核心思路**

Tool Calling 只解决“模型建议下一步查询哪类工具”，不负责授权和执行。模型只能看到三个静态 Provider Alias
以及不含 `job_id`、路径、actor 和 Capability 的输入 Schema；应用把 Alias 映射到本地 `ToolContract`，再由
`ToolRegistry` 校验 Exposure、Capability、Pydantic 输入、Handler 输出和稳定错误。当前 `job_id` 来自 Chat
API 路径并由 Host Context 注入，从协议上阻止模型借参数读取另一个 Job。

第一版目录只包含 `get_reproduction_status`、`search_reproduction_evidence` 和
`inspect_failure_context` 三个复合只读工具。`AGENT_READ_ONLY` 只是必要条件，静态 allowlist 还会拒绝网络、
进程、写入、控制和非幂等 Tool，所以 Phase 51 Live Browser、Shell、Patch、Approval、Cancel、Rerun 和
Executor 都不会因已注册在项目中而自动暴露给模型。

控制循环由应用显式实现：每个模型轮次最多一个 Tool Call，最多四个选择轮次和三次 Tool 执行；参数有
深度、字段、字符串和字节预算，相同内部 Tool Name+Args Hash 不能重复。Provider Call ID 只用于匹配
AIMessage/ToolMessage，本地 `toolcall_*` ID 用于审计。Tool Result 仍是不可信数据，只有服务端构造并通过
预算合并的 `GroundingSource` 可以进入最终回答 Citation 白名单。

Tool Selection 与最终回答使用两个 Model Task。前者通过 `chat_tool_selection` Route 使用 Tool Calling
Capability，后者继续使用原 Structured `ChatDraft`；这样模型的停止文本不会成为回答，操作意图仍不会自动
转换成 Decision。选择模型不可用或违反策略时，Chat 降级到 Phase 51 之前的 eager read-only Context；
Feature 关闭则完全走旧路径。Tool Trace Summary 与 assistant message 同事务持久化，幂等 replay 不重跑工具。

**实现流程**

1. 定义 Evidence Tool 输入输出、Provider Catalog、Normalized Call、Call Trace 和不可变 Trace Hash Schema；
2. 扩展 `ToolInvocationContext` 的 `job_id/granted_capabilities`，让 Registry 自身在 Handler 前拒绝缺失
   Capability，并让 Skill Runtime 继续传递已有 Host Grant；
3. 从 `ChatContextBuilder` 提取 Job-only Grounding，建立 Status、Evidence Search 和 Failure Context 三个
   复合只读 Tool，所有 Job Scope 都来自 Context；
4. 用静态 Alias 构造最小 Provider Tool Catalog，校验 Exposure、幂等、Effect、Capability、strict Schema、
   远程 `$ref` 和 Catalog Hash，不自动导出其他 Registry Tool；
5. 给 Model Routing 增加 `tool_calling` Capability 和 `chat_tool_selection` Task，通过 Gateway 完成 reserve、
   trusted provider、`bind_tools`、retry、usage 和 settle；
6. 显式实现 AIMessage -> Alias/Args 验证 -> Registry -> ToolMessage 循环，限制并行、轮数、次数、重复
   指纹、参数和结果预算，并保留 Provider Call ID 与本地 Audit ID 的独立身份；
7. 把 Tool Evidence 转成 GroundingSource，与 Job-only Base 按 Citation Identity 和总字符预算合并；停止后
   继续使用原 `build_budgeted_chat_prompt`、ChatDraft 和 Citation 白名单；
8. 给 Chat Message/SQLite 增加有界 Trace Summary，使 exchange 和 trace 原子提交，replay 返回第一次结果；
9. 增加 Feature Flag、Doctor、Readiness、Model Ledger 观察和安全降级，关闭时不构造 Tool Loop；
10. 用 Scripted Invoker 测试正常、未知、并行、跨 Job、重复、超限和 Mutation 请求，再运行 Model Gateway、
    Chat、Decision、Skill、Research Browser 与全量回归；
11. 按 Flag 关闭、Fake Provider、shadow、单 Job active 的顺序灰度，异常时关闭 Flag 并保留历史 Trace/Ledger。

- **安全边界**：模型不可提供 Job Scope，不自动导出内部 Tool，不暴露 Network/Process/Write/Mutation，
  不并行调用，不无限循环，不把 Tool Selection 文本当回答，不把 Tool Result 当控制指令，不绕过 Citation、
  Decision、Approval、Executor、Secret 或 Model Budget。
- **关键产物**：`ProviderToolCatalog`、`EvidenceToolOutput`、三个 Chat Evidence Tool、
  `RoutedToolCallingInvocation`、`GatewayToolTurnInvoker`、`BoundedToolCallingLoop`、`ToolLoopTrace`、
  Chat Tool Trace Summary、Tool Calling Doctor 和 Offline Golden Report。
- **教程**：`63_phase_52_bounded_tool_calling_and_reproduction_orchestration.md`。

### Phase 53：MCP 只读互操作网关、Schema Pinning 与证据溯源

- **状态**：已实现；本次 MCP Gateway 与 Phase 52 相关专项回归共 `40 passed`；默认
  `MCP_GATEWAY_ENABLED=false`。
- **目标功能**：让 Phase 52 的 Chat Tool Calling 通过一个受治理 MCP Client 查询经过审核的外部论文证据，
  同时确保远端发现、Tool Annotation 和 Server Instructions 都不能扩大本地权限。
- **技术**：MCP Specification `2026-07-28`、官方 Python SDK 2.x、Streamable HTTP、静态 Server/Tool
  Binding、输入输出 Schema Hash Pin、JSON Schema 2020-12 校验、Pydantic 本地规范化、SQLite Evidence Pack/
  Hash-only Audit、Job-bound MCP Citation、Capability Grant、Feature Flag、Doctor、Readiness 和 Retention。

**核心思路**

MCP 只负责 Host 与外部服务之间的互操作，不负责决定权限。模型只看到本地高层 Alias
`search_external_paper_evidence(query, limit)`；`server_id`、endpoint、remote tool name、Schema Pin、Job ID
和 Capability 都由受信任 Host 注入。远端 `tools/list` 只用于验证固定 Binding，不能自动成为 Provider
Catalog。即使远端新增 Shell 或删除工具，本地目录也不会变化。

第一版只连接 Operator 已启动的字面量 loopback Streamable HTTP endpoint，不支持 stdio 子进程、DNS、Redirect、
环境 Proxy、远端 OAuth、Prompts、Resources、Sampling、Elicitation 或 Tasks。发现、Schema 校验和调用位于同一
MCP Client 生命周期；只接受有界 `structured_content`，并通过远端 JSON Schema、本地 Pydantic、URL Policy
和结果预算后才形成 Evidence。

成功结果先写成绑定当前 Job、Server Profile、输入输出 Schema、Result、Pack 和 Item Hash 的
`McpEvidencePack`，再转换为 `source_type=mcp` 的 Chat Citation。失败只保存稳定错误码和 Hash，不保存远端错误
正文。MCP Tool 仍经过 ToolRegistry、`mcp.read.external` Capability、Phase 52 调用次数/重复指纹/结果预算和
最终 ChatDraft Citation 白名单。

**实现流程**

1. 增加 MCP optional dependency、Feature Flag、Policy/DB 路径和项目内数据目录校验；
2. 定义 Server Profile、Tool Binding、Observed Schema、Raw Result、Evidence Pack、Call Record 和稳定错误；
3. Policy 只允许固定 loopback IP、显式用户端口和 `/mcp`，拒绝 userinfo、query、fragment、symlink 和占位 Pin；
4. 官方 SDK Adapter 关闭 Redirect/Proxy，分页读取有界 Tool 目录，在同一连接中验证协议、Tool 和 Schema Hash；
5. 只消费 `structured_content`，拒绝 Text/Image/Audio/Resource Block 和未声明 Output Schema；
6. 将结构化结果规范化为 Job-bound Evidence Pack，并原子保存 Pack 与 Hash-only Call Audit；
7. 把 MCP Gateway 包装为一个声明 `NETWORK_READ` 的本地 ToolContract，要求 `mcp.read.external`；
8. 仅在两个 Feature Flag 和唯一 Policy Binding 同时有效时扩展 Phase 52 Catalog、Effect 和 Grant；
9. 扩展 Chat Citation 的 MCP Profile/Schema/Pack/Item Identity，增加只读 Pack API；
10. 增加 Inspect、Doctor、Local Readiness、Retention、In-memory MCP Fixture 和故障注入测试；
11. 按 SDK 离线、Schema 人工 Pin、Connect Doctor、单 Job Chat 的顺序灰度，异常时独立关闭 MCP Flag。

- **安全边界**：不启动 stdio Server，不自动注册远端 Tool，不信任 Annotation/Instructions，不向远端发送
  Job State、路径或 Secret，不提供通用 MCP Call API，不允许 Mutation，不把 Schema Pin 冒充 Server 实现
  安全证明。
- **关键产物**：`McpGatewayPolicy`、`McpServerProfile`、`McpToolBinding`、`SdkMcpClient`、
  `ReadOnlyMcpEvidenceGateway`、`McpEvidencePack`、`SqliteMcpEvidenceRepository`、MCP Tool Adapter、
  `source_type=mcp` Citation、Inspect/Doctor 和只读 Pack API。
- **教程**：`64_phase_53_mcp_read_only_interoperability_gateway.md`。

### Phase 54：只读 MCP Server Export、公开投影与本地访问控制

- **状态**：核心源码已经实现；默认 `MCP_EXPORT_ENABLED=false`。历史回归为 `60 passed, 4 skipped`；
  当前环境已补装 MCP SDK，Phase 55 目录契约专项已通过，但真实 `tools/call` 相邻测试仍会长时间不结束，
  因此 Phase 54 业务调用生命周期尚待 Phase 56 收口。
- **目标功能**：把本项目已经治理过的 Job 状态、Artifact 清单、最终报告和本地 Evidence 作为标准 MCP
  Tool/Resource 导出，使其他可信本机 MCP Host 可以查询复现进度和证据，但不能执行命令、修改文件、审批动作、
  枚举全部 Job 或读取任意路径。
- **实现技术**：官方 MCP Python SDK 2.x `MCPServer`、Streamable HTTP、独立 loopback ASGI 服务、Bearer Token、
  Secret Vault Use 约束、Pydantic 公开投影、Artifact Catalog/Delivery、Tool Registry Evidence、Hash-only SQLite
  Audit、进程内 Rate Limit、Feature Flag、Doctor、Retention 和 In-memory MCP Client Contract Test。

**核心思路**

Phase 53 是“本项目作为 MCP Client 消费外部证据”，Phase 54 则是“本项目作为 MCP Server 导出已有证据”。
协议方向虽然反转，Authority 原则不变：MCP handler 只负责协议适配，不能直接访问数据库、拼接文件路径或调用
Executor。所有结果必须先经过内部 Service 的 Job Scope 验证、Artifact Hash 校验、来源限制、Secret 脱敏和公开
Schema 投影，再交给 MCP SDK 序列化。

第一版采用独立 `127.0.0.1` Streamable HTTP 进程，而不挂载到主 FastAPI。这样 MCP SDK 生命周期、Bearer
认证和故障域不会污染现有 API。对外目录固定为四个只读 Tool 和两个 Resource Template；模型发现能力不能扩大
目录，Client 也不能提交 actor、capability、endpoint、路径或内部 tool name。Status 只公开业务状态，Artifact
只公开稳定身份与校验信息，Final Report 由服务端按 Catalog 选择，Evidence 固定为 `job/event/artifact/log`，并
显式禁止递归调用 Phase 53 Gateway 或 Research Browser。

调用审计只保存 operation、Job/输入/输出 Hash、数量、耗时和稳定错误码，不保存 Token、Header、query、报告或
Evidence 原文。Audit 不可写、Artifact 完整性失败、Secret 缺失或 Rate Limit 超限时均 fail closed。该设计使
MCP 成为受控互操作协议，而不是绕过 Chat、Decision、Approval 和 Execution Authority 的第二套控制面。

**实现流程**

1. 增加 MCP Export Feature Flag、loopback Host/Port、独立 Token Secret 名称、Audit DB 和结果预算配置；
2. 为 Secret Vault 增加 `mcp_export_auth` Use，并确保 Token 不进入日志、状态、Artifact 或 MCP Context；
3. 定义稳定错误、Job ID/Hash/Query 规范化函数以及不含路径和内部权限字段的公开 Pydantic Schema；
4. 实现 SQLite Hash-only Audit 和进程内滑动窗口 Rate Limiter，并规定 Audit 失败时拒绝返回结果；
5. 实现 `ReadOnlyMcpExportService`，复用 Interaction、Artifact Delivery 与本地 Evidence Tool Registry；
6. 在 Service 中绑定服务端 actor/capability，限制 Evidence 来源，校验 Artifact Hash，并对文本执行 Secret 脱敏；
7. 用 Factory 只构造本地 Job/Artifact/Event/Log 依赖，显式不注入 MCP Gateway、Research Browser 和 Mutation；
8. 用 `MCPServer` 注册四个 Tool、两个 Resource Template 和无私有状态的 `/healthz`；
9. 在 ASGI 外层使用独立 Bearer Middleware，并只监听字面量 `127.0.0.1`；
10. 增加 CLI Serve/Doctor、Retention 接线、Schema/Service/Authority/Auth/协议测试和真实 loopback 手工验收；
11. 先保持 Flag 关闭完成全量回归，再启用独立进程，并通过 Token、Hash、Rate Limit、Audit 故障注入验收。

- **安全边界**：不导出 Mutation、Shell、Patch、Approval、Cancel、Rerun、任意文件读取或 Job 枚举；不监听
  非 loopback 地址；不使用 wildcard Host/CORS；不把远端 Annotation 当授权；不向 Client 返回 Secret 原文、
  绝对路径或对象存储 Key；第一版不自制远程 OAuth。
- **关键产物**：`ReadOnlyMcpExportService`、四个公开输出 Schema、`SqliteMcpExportAuditRepository`、
  `InMemoryMcpExportRateLimiter`、`MCPServer` Tool/Resource、Bearer ASGI Middleware、Serve/Doctor、Retention
  接线和 MCP Contract/Authority 测试。
- **教程**：`65_phase_54_read_only_mcp_server_export.md`。

### Phase 55：MCP 互操作契约评测、Client Profile 与单机运行收口

- **状态**：核心源码已实现，九组专项测试实测 `26 passed in 6.05s`。当前 Bootstrap Baseline 已覆盖
  modern/legacy in-memory，但尚未晋升包含 loopback HTTP 的最终 Baseline；业务 `tools/call` 可靠性不属于本阶段
  Surface 目录测试，转由 Phase 56 收口。
- **目标功能**：通过真实 MCP Client 观察 Phase 54 的公开 Tool、Resource Template、Schema、Capability 和协议版本，
  将稳定 Surface 固化为可审核 Golden Baseline，并用 modern、legacy 和真实 loopback HTTP 三种 Client Profile
  建立离线门禁、发布门禁、Doctor 与单机运行手册。
- **实现技术**：官方 MCP Python SDK 2.x `Client`、in-memory transport、Streamable HTTP、Pydantic 契约 Schema、
  确定性 JSON 与 SHA-256 身份、Candidate/Baseline 双层模型、显式 Hash Promotion、原子文件发布、Profile 配置、
  AsyncIO 超时、Golden Eval、Readiness、Inspector 和可选官方 Conformance Runner。

**核心思路**

Phase 55 不再扩充 MCP Tool，而是回答“已经导出的 MCP 能力能否被真实 Client 稳定消费”。测试必须从协议侧调用
`list_tools`、`list_resource_templates`、`list_resources` 和 `list_prompts`，不能直接读取 Server 注册常量。观察结果先
规范化为与顺序无关的 Surface，再把 SDK、Python、Pydantic 和 negotiated protocol 放入独立 Runtime Fingerprint。
因此，依赖升级但公开 Schema 未变时可以记录环境漂移；Tool 名称、参数、输出或 Resource URI 变化时则必须阻断发布。

Golden 更新采用 Candidate 与 Baseline 分离：评测只能生成 Candidate，不能自动覆盖 Baseline。人工审核时必须同时提交
Candidate 的预期 Surface Hash；替换已有 Baseline 还必须提交当前 Baseline Hash，从而防止审核动作与实际文件之间发生
stale。Baseline 和报告使用同目录临时文件原子替换，并拒绝符号链接，避免半写入或路径重定向。Client Profile 只保存
Endpoint 和 Secret 名称，不保存 Token；真实 HTTP 连接继续保持字面量 loopback、Bearer、无代理和无重定向边界。

**实现流程**

1. 把 MCP SDK 加入开发测试依赖，移除关键协议测试中的 `pytest.importorskip()` 假绿路径；
2. 增加 Baseline、Profile、Report Root 和 Timeout 配置，并校验所有文件路径仍在项目 `ALLOWED_ROOT` 内；
3. 定义稳定错误、Surface/Runtime/Observation/Candidate/Baseline/Eval/Readiness Schema；
4. 对 JSON Schema、Annotation、Capability、Tool 和 Resource 进行确定性规范化并计算 SHA-256；
5. 使用真实 `mcp.Client` 分页观察 Server Surface，不调用任何业务 Tool；
6. 实现无自动晋升的 Candidate/Baseline Repository、原子写入、Hash 校验和符号链接拒绝；
7. 分别评测 in-memory modern、in-memory legacy 和 authenticated loopback HTTP Profile；
8. 把协议、SDK、Baseline、Profile、Secret、Export 配置聚合为 MCP Stack Readiness；
9. 增加 Candidate、Promotion、Offline/Release Eval、Doctor CLI 和机器可读 JSON/人工可读 Markdown 报告；
10. 增加 Schema、Profile、Snapshot、Golden、Evaluator、Authority、Readiness 和无 SDK 跳过测试；
11. 先用 in-memory Candidate 建立 Bootstrap Baseline，再以真实 HTTP Candidate 审核替换最终 Baseline；
12. 使用第二种 Client 做手工互操作验收，并把 Conformance Runner 限制为不能要求关闭认证的可选门禁。

- **安全边界**：不调用业务 Tool，不生成 Mutation，不自动接受 Drift，不把 Token 写入 Profile、命令行、报告或日志，
  不允许非 loopback Endpoint、代理、重定向、stdio 子进程或公网监听，也不为 Inspector/Conformance 临时关闭认证。
- **关键产物**：`McpSurfaceSnapshot`、`McpRuntimeFingerprint`、`McpClientProfile`、
  `McpContractCandidate`、`McpContractBaseline`、`McpContractEvalReport`、真实 Client Observer、Evaluator、Readiness、
  Candidate/Promotion/Eval/Doctor CLI、`config/mcp_export_contract_baseline.json` 和 `analysis/mcp_contract_eval/` 报告。
- **教程**：`66_phase_55_mcp_interoperability_contract_eval_and_single_host_operations.md`。

### Phase 56：MCP 业务调用可靠性、运行 SLO 与 SDK 升级演练

- **状态**：核心源码已实现。教程编写前已确认 Phase 55 专项通过，但 Phase 54
  `test_status_tool_returns_structured_content` 在当前 Python 3.10.20、`mcp==2.0.0` 组合下会长时间不结束；真实 HTTP
  `tools/call` 的完整运行门禁仍需结合专项测试和 Runtime Report 持续复核。
- **目标功能**：让 MCP 业务调用一定在边界内成功或失败；验证 modern、legacy 和真实 loopback HTTP 下的
  四个 Tool 与两个 Resource；生成不含业务正文的 Runtime SLO Report；用 before/after Report 做 SDK 升级演练。
- **计划技术**：MCP Server lifespan、async handler、项目受控 `ThreadPoolExecutor`、有限 worker/queue、
  Client/handler deadline、Phase 28 `TelemetryPort`、SDK 内置 OpenTelemetry、Pydantic 严格 Policy/Report、
  SHA-256、原子报告、真实 Uvicorn loopback 测试和项目内候选 venv。

**核心思路**

目录可发现与业务可调用是两种不同契约。Phase 55 证明 Client 看到了稳定 Surface，Phase 56 进一步从 Client 视角
调用六个只读业务接口。Server handler 改为 async 适配层，但内部同步 Service 仍由项目自己的有界 Executor 执行，
避免依赖 SDK 默认线程池的版本细节。Worker 与等待队列都有上限，满载快速返回 Busy；等待超时返回稳定 Timeout，
但不谎称已经运行的 Python 线程被终止，slot 也只有在真实 Future 结束后才释放。

Runtime Policy 固定 offline/release Profile、六个操作、样本数、成功率、P95、允许 SDK major/协议版本与升级退化阈值。
Probe 只保存状态、耗时、稳定错误码和输出 SHA-256，不保存 Job ID、Query、Token、Endpoint 或响应正文。Client Report、
Server Telemetry 和 Phase 54 Hash-only Audit 保持分层，用于区分协议等待、Executor 拥塞、Service 阻塞和晚完成。

SDK Upgrade 不由程序执行。Operator 在项目 `.runtime_envs/` 创建候选环境，分别用当前与候选 Client/Server 生成
release Report；比较器要求相同 Policy、相同 Contract Baseline、相同 Surface 和 Operation Coverage，并检查成功率
与延迟退化。Comparison 通过后仍需人工审核 release notes、更新 constraints 并重跑完整门禁。

**计划实现流程**

1. 锁定当前已验证 MCP Runtime 依赖组合，并增加 handler worker、queue、timeout、Policy 与 Report Root 配置；
2. 增加 Busy/Timeout 稳定错误和 lifespan 管理的有界 Call Executor；
3. 把四个 Tool、两个 Resource 改为显式 Context 的 async handler，统一通过 Executor 调用只读 Service；
4. 为 Client 构造、`call_tool`、`read_resource` 和测试外层增加明确 deadline；
5. 定义 Runtime Policy、Sample、Operation Summary、Profile Result、Report 与 Upgrade Comparison Schema；
6. 实现 modern/legacy/HTTP 共用的六操作 Probe，只持久化 Hash 与稳定结果分类；
7. 原子发布项目内 JSON/Markdown Report，并把最新有效 release Report 接入 MCP Stack Readiness；
8. 增加 Executor、Policy、Probe、Upgrade、Authority 和真实 Uvicorn HTTP 测试；
9. 先通过 offline Probe，再启动独立 MCP Export 完成 release Probe；
10. 生成包含 HTTP 的 Phase 55 Candidate，人工晋升最终 Baseline 后重跑 Contract 与 Runtime Gate；
11. 在项目内候选 venv 生成 before/after 报告，比较通过后才允许人工升级依赖。

- **安全边界**：不新增 MCP Tool，不开放 Mutation，不自动安装 SDK、不自动更新 constraints/Baseline；Metric
  不使用 Job/Request/Query 等高基数标签；Timeout 不冒充线程撤销；HTTP 继续只允许 loopback、Bearer、无代理和无重定向。
- **计划关键产物**：`McpExportCallExecutor`、`McpRuntimePolicy`、`McpRuntimeReport`、`McpProbeTarget`、
  Runtime Probe/Repository、Upgrade Comparator、`mcp-runtime-probe`/`mcp-runtime-compare` CLI、Runtime Readiness、
  `config/mcp_runtime_policy.json`、`constraints/mcp-runtime.txt` 与 `analysis/mcp_runtime/` 派生报告。
- **教程**：`67_phase_56_mcp_invocation_reliability_slo_and_sdk_upgrade_rehearsal.md`。

---

## 十、跨阶段核心工程思想

### 10.1 结构化契约优于自然语言约定

```text
Prompt 描述期望
Pydantic 定义协议
本地 Validator 验证业务身份
Hash 绑定审批与内容
```

### 10.2 确定性控制与概率性推理解耦

LLM 适合：摘要、语义映射、诊断候选、解释和规划草稿。

确定性代码负责：路径、权限、Hash、状态机、风险、资源、引用、执行与删除。

### 10.3 Proposal、Approval、Execution 分离

```text
Evidence -> Proposal -> User Decision -> Policy -> Approval -> Execution -> Verification
```

任何阶段都不能因为 Agent “认为合理”而跳过中间边界。

### 10.4 State、Checkpoint、Artifact 与 Memory 分层

| 类型 | 保存内容 | 生命周期 |
|---|---|---|
| State | 当前任务共享事实 | 单次 Graph |
| Checkpoint | Graph 执行位置和中断恢复 | Thread/Job |
| Artifact | 可验证输入、过程和结果文件 | Run/Retention Policy |
| Chat Memory | 压缩后的对话约束和引用 | Job Conversation |
| Future Long-term Memory | 经确认或验证的跨任务经验 | Project Scope |

### 10.5 内容身份与可恢复性

系统广泛使用 SHA-256、Version、Generation、Idempotency Key、Lease/Fencing Token 和
Expected Version。它们分别解决内容漂移、并发更新、重复请求和失联 Worker 旧写入问题。

### 10.6 默认拒绝和最小权限

```text
未知路径 -> 拒绝
未知命令 -> 审批或阻断
未知错误 -> 不自动重试
未知 Artifact -> 不引用
未知 Tool -> 不注册
未知网页内容 -> 不执行
```

---

## 十一、当前主要数据与产物

| 类别 | 典型内容 |
|---|---|
| Analysis | paper summary、sections、method modules、repo map、mapping |
| Planning | experiment plan、command selection、preflight、capability decision |
| Execution | process record、stdout/stderr、smoke result、debug report |
| Repair | repair proposal、patch bundle、verification、promotion record |
| Reports | final report、error report、run manifest、artifact index |
| Control | Job、Event、Interrupt、Decision、Checkpoint、Lease |
| Notification | 持久 Inbox、全局 Event Cursor、Read/Superseded、Current Operation |
| Interaction | Chat messages、memory、citation、timeline |
| Derived | comparison、rerun proposal、child run lineage |
| Failure Memory | failure signature、case lifecycle、source/verification evidence、diagnostic match |
| Project Memory | project registry、Job binding、typed fact、revision、citation、expiry/tombstone |
| Knowledge Base | source-scoped entity、typed relation、provenance、review、query pack、citation |
| Future Model Control | route decision、reservation、token/cost settlement、pricing/eval version |

---

## 十二、逐函数伪代码与输入输出分册

`python_source_code_reference.md` 保留全量索引和架构说明；下面六个分册使用当前 Python AST
重新生成，逐函数列出参数类型与业务含义、返回类型与业务含义，并按真实代码顺序改写赋值、分支、
循环、异常、上下文管理和返回语句。

| 分册 | 主要阶段范围 | 当前函数/方法数 |
|---|---|---:|
| [`python_source_code_reference_phase_00_v7.md`](python_source_code_reference_phase_00_v7.md) | 基础 00、V0-V7 | 424 |
| [`python_source_code_reference_phase_01_16.md`](python_source_code_reference_phase_01_16.md) | 端到端闭环、安全执行与修复 | 561 |
| [`python_source_code_reference_phase_17_29.md`](python_source_code_reference_phase_17_29.md) | 理解检索、异步运行、持久化、Workspace、资源与 OCI | 1520 |
| [`python_source_code_reference_phase_30_39.md`](python_source_code_reference_phase_30_39.md) | Web、Chat、Artifact、Retention、Comparison 与 Rerun | 684 |
| [`python_source_code_reference_phase_40_46.md`](python_source_code_reference_phase_40_46.md) | Tool Contract、Secret、决策/职责、通知、Failure/Project Memory | 767 |
| [`python_source_code_reference_phase_47_56.md`](python_source_code_reference_phase_47_56.md) | Adaptive Retrieval、Skill、Knowledge Base、Model Routing、Research Browser、Tool Calling 与 MCP | 1144 |

六个现有分册按当前 Python AST 合计覆盖 5100 个函数/方法，其中 Phase 47-56 的新增模块统一收录在
新分册中。
阶段归类以文件的主要职责为准；一个跨阶段持续修改的文件只进入一个主分册，函数条目中的真实源码路径
和行号才是最终定位依据。

重新生成命令：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
/home/tianshaoqi24/miniconda3/envs/agent/bin/python \
  a_implementation_guides/generate_function_reference.py
```

生成器只读取项目 Python AST，并更新六个函数分册，不修改
`app/` 或 `tests/`。

---

## 十三、后续同步维护规则

以后实现新功能时，必须同步更新本文、`python_source_code_reference.md` 和对应阶段分册：

1. 新增 Phase 教程时，在本文增加阶段状态、功能、技术、核心思路、流程和产物；
2. Phase 从“教程完成”进入“实现中”或“已实现”时，及时更新状态；
3. 新增或删除 `app/**/*.py` 时，更新 Python 文件索引；
4. 修改函数签名、职责、输入输出或主要流程时，重新运行函数参考生成器并抽样检查伪代码；
5. 引入新数据库、中间件、模型、运行时或外部服务时，更新技术栈；
6. 改变安全边界时，更新跨阶段核心思想和对应阶段说明；
7. 文档中的状态以当前源码和测试为准，不能仅因为教程存在就写成已实现；
8. 每次更新同时修改本文顶部“最后同步日期”和“当前代码基线”。

建议在每个后续 Phase 的完成清单中固定增加：

```text
[ ] 更新 project_phase_capability_summary.md
[ ] 更新 python_source_code_reference.md
[ ] 更新 a_implementation_guides/README.md 阶段索引
```
