# 09. Agent 开发全流程总览总结

这份文档把 `00` 到 `08` 这几章串成一个整体，重点不是重复每一章的原文，而是从 Agent 开发视角总结：

1. 实现了什么功能
2. 这些功能是怎么实现的
3. 涉及了哪些 Agent 相关知识点
4. 后续还能往哪里扩展

最后会结合当前项目状态，给出下一步比较值得继续推进的方向。

---

## 00. 项目脚手架

### 1. 实现的功能

- 搭好项目目录结构
- 固定依赖管理方式
- 统一读取环境变量
- 统一封装模型创建入口
- 定义基础 schema 和 state
- 提供最小 CLI 入口

### 2. 如何实现的

- [pyproject.toml](/data/tianshaoqi24/agent/paper_reproduction_copilot/pyproject.toml:1)
  - 管理依赖、Python 版本和开发工具

- [app/config.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/config.py:1)
  - 读取 `.env`
  - 统一管理模型名、API、输出目录、最大步数等配置

- [app/model.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/model.py:1)
  - 用 `get_chat_model()` 和 `get_embedding_model()` 统一创建模型
  - 把模型依赖从业务节点里抽离出来

- [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1)
  - 定义 `PaperSummary`、`RepoMap`、`ModuleMapping` 等结构化对象

- [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1)
  - 定义 `ReproductionState`
  - 提前规划整条图工作流会共享哪些字段

- [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:1)
  - 提供 `version`、`init_outputs` 等最小命令入口

核心思路是：先搭地基，再逐章往上堆能力。

### 3. 涉及到的 Agent 知识点

- 配置管理
- 模型封装
- 结构化输出的 schema 设计
- 工作流共享状态设计
- CLI 作为 Agent 调试与演示入口

### 4. 可扩展功能或可深挖知识点

- 配置分层：dev / test / prod
- 模型路由：不同节点用不同模型
- 更严格的 state typing
- 更完整的日志系统和 tracing

---

## 01. V0 论文结构化阅读

### 1. 实现的功能

- 读取 PDF / Markdown / 纯文本论文
- 将长文切成 chunk
- 调用 LLM 抽取结构化论文摘要
- 生成：
  - `paper_summary.json`
  - `method_modules.json`

### 2. 如何实现的

- [app/tools/paper_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/paper_tools.py:1)
  - 负责读取不同格式的论文
  - 把长文本切成带 overlap 的 chunk

- [app/prompts/paper_prompt.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/prompts/paper_prompt.py:1)
  - 约束模型输出 `PaperSummary` 需要的字段

- [app/nodes/paper_reader_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/paper_reader_node.py:1)
  - 读取论文并把 chunk 写入 state

- [app/nodes/method_extractor_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/method_extractor_node.py:1)
  - 调用 `llm.with_structured_output(PaperSummary)`
  - 生成结构化摘要并落盘

核心思路是：先把论文从原始文本变成稳定、可复用的结构化对象。

### 3. 涉及到的 Agent 知识点

- 文档读取与预处理
- chunking
- prompt 约束
- Pydantic 结构化输出
- LLM 输出校验与调试

### 4. 可扩展功能或可深挖知识点

- 更智能的 chunk 选择，而不是只取前几个 chunk
- 章节级抽取与 evidence 对齐
- 多轮阅读：先粗读再精读
- RAG 式论文问答

---

## 02. V1 代码仓库地图

### 1. 实现的功能

- 扫描代码仓库结构
- 构建 RepoMap
- 启发式识别训练、评估、配置、模型、数据等文件
- 生成：
  - `repo_map.json`
  - `repo_summary.md`

### 2. 如何实现的

- [app/tools/repo_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/repo_tools.py:1)
  - 列目录树
  - 枚举文件
  - 按关键词做启发式分类

- [app/tools/code_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/code_tools.py:1)
  - 抽取代码片段
  - 用 AST 提取 Python 符号

- [app/nodes/repo_scan_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/repo_scan_node.py:1)
  - 串起扫描逻辑
  - 组织成 `RepoMap`
  - 输出 JSON + Markdown

核心思路是：先建立代码仓库的“全局地图”，再做更细的语义定位。

### 3. 涉及到的 Agent 知识点

- Tool use
- 文件系统观察
- 启发式信息抽取
- 代码结构理解
- 中间状态落盘

### 4. 可扩展功能或可深挖知识点

- 支持更多语言的符号抽取
- 基于导入关系构建模块图
- README / config / script 联合解析
- Git 历史分析

---

## 03. V2 论文-代码证据化映射

### 1. 实现的功能

- 根据论文模块在仓库里搜索候选实现
- 抽取相关代码片段
- 用 LLM 生成“论文模块 -> 代码候选”的证据化映射
- 生成：
  - `paper_code_mapping.json`
  - `paper_code_mapping.md`

### 2. 如何实现的

- [app/tools/search_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/search_tools.py:1)
  - 用 `rg` 搜关键词
  - 聚合并去重搜索结果

- [app/prompts/mapping_prompt.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/prompts/mapping_prompt.py:1)
  - 要求模型基于 evidence 做映射，而不是只靠文件名猜

- [app/nodes/code_search_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/code_search_node.py:1)
  - 先做搜索
  - 为每个方法模块选候选文件
  - 抽取有限上下文代码片段

- [app/nodes/mapping_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/mapping_node.py:1)
  - 调 LLM 生成结构化 `ModuleMapping`
  - 渲染成 Markdown 报告

核心思路是：不要让 LLM 直接“读整个仓库拍脑袋”，而是先检索，再让模型在有限证据上做判断。

### 3. 涉及到的 Agent 知识点

- Retrieval + LLM 组合
- Evidence-based reasoning
- 候选筛选
- 代码片段控制上下文长度
- 幻觉抑制

### 4. 可扩展功能或可深挖知识点

- 关键词搜索升级为 embedding 检索
- 基于调用图的候选扩展
- 自动计算 mapping 置信度
- 让模型输出更细粒度的证据链

---

## 04. V3 复现实验计划生成

### 1. 实现的功能

- 基于论文摘要、仓库地图和代码映射生成实验计划
- 把步骤拆成环境、数据、训练、评估四类
- 单独输出可执行命令建议
- 生成：
  - `experiment_plan.json`
  - `experiment_plan.md`

### 2. 如何实现的

- [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:57)
  - 增加 `ExperimentStep`、`RunCommand`、`ExperimentPlan`

- [app/prompts/plan_prompt.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/prompts/plan_prompt.py:1)
  - 强约束模型只输出合法 JSON
  - 强调来源、风险、不确定项

- [app/nodes/experiment_plan_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/experiment_plan_node.py:1)
  - 将前面阶段的结果作为输入
  - 生成结构化实验计划
  - 输出 JSON 与 Markdown

核心思路是：把“分析结果”转成“行动方案”，并显式记录不确定项与风险。

### 3. 涉及到的 Agent 知识点

- Plan generation
- 结构化任务分解
- Action proposal
- 风险标记
- 机器可读 + 人类可读双输出

### 4. 可扩展功能或可深挖知识点

- 自动把 plan 转成待审批 `pending_action`
- 环境依赖对齐检查
- 从 README / shell script 自动抽取命令
- 对计划做可执行性验证

---

## 05. V4 LangGraph、Checkpoint 与 Memory

### 1. 实现的功能

- 把线性 CLI 串联升级成 `StateGraph`
- 引入 `thread_id`
- 支持 checkpoint
- 提供 `run_graph` 与 `show_state`

### 2. 如何实现的

- [app/memory/checkpoint.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/memory/checkpoint.py:1)
  - 当前使用 `InMemorySaver`

- [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1)
  - 注册节点
  - 定义主链路和条件路由
  - 编译 graph

- [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:79)
  - 增加 `run_graph`
  - 增加 `show_state`

核心思路是：让节点不再只是顺序函数，而是变成状态图中的状态转换单元。

### 3. 涉及到的 Agent 知识点

- LangGraph
- StateGraph
- Checkpoint
- thread_id
- 恢复与可中断工作流

### 4. 可扩展功能或可深挖知识点

- 持久化 checkpointer：SQLite / Postgres
- 更细的 router 设计
- 多分支恢复
- 长期 memory 和短期 checkpoint 分层

---

## 06. V5 日志 Debug

### 1. 实现的功能

- 读取日志文件
- 提取 traceback
- 启发式分类错误类型
- 结合 repo map 和 experiment plan 生成结构化 debug 报告
- 生成：
  - `debug_report.json`
  - `debug_report.md`

### 2. 如何实现的

- [app/tools/log_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/log_tools.py:1)
  - 读日志尾部
  - 提取 traceback
  - 初步分类错误

- [app/prompts/debug_prompt.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/prompts/debug_prompt.py:1)
  - 把 traceback、repo map、experiment plan 组装成调试任务

- [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:88)
  - 增加 `DebugReport`

- [app/nodes/log_debug_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/log_debug_node.py:1)
  - 生成结构化调试报告
  - 输出 JSON + Markdown

- [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:15)
  - 在 `route_after_plan()` 中加入 log debug 分支

核心思路是：失败信息也进入图工作流，并被结构化处理，而不是只在终端里留下一条报错。

### 3. 涉及到的 Agent 知识点

- Failure-path handling
- Tool + heuristic + LLM 混合诊断
- 错误分类
- 结构化调试报告
- 条件分支工作流

### 4. 可扩展功能或可深挖知识点

- 支持直接传 `traceback_text`
- 自动关联 repo 中的具体函数或配置项
- 结合历史失败日志做模式识别
- 自动生成修复 proposal

---

## 07. V6 Human-in-the-loop 安全审批

### 1. 实现的功能

- 对命令进行风险评估
- 对待执行动作进行审批判断
- 高风险动作触发人工审核
- 使用 `interrupt()` 暂停图
- 为 `resume` 恢复留出接口

### 2. 如何实现的

- [app/tools/safe_shell_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/safe_shell_tools.py:1)
  - 定义 `blocked` / `high` / `medium`
  - 对命令做风控分类

- [app/nodes/risk_check_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/risk_check_node.py:1)
  - 根据 `pending_action` 生成风险判断结果
  - 决定 `requires_approval`

- [app/nodes/human_review_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/human_review_node.py:1)
  - 用 `interrupt()` 暂停等待人工输入

- [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:15)
  - 将审批分支接进 graph

- [tests/test_review_flow.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/tests/test_review_flow.py:1)
  - 已对命令风控、risk_check、human_review 做节点级测试

核心思路是：Agent 先提出动作，但真正执行前必须经过风险检查和人工审批。

### 3. 涉及到的 Agent 知识点

- Human-in-the-loop
- Tool safety boundary
- Interrupt / resume
- Proposal-only action design
- Side effect control

### 4. 可扩展功能或可深挖知识点

- 审批通过后接真实执行节点
- 审批记录与审计日志
- 更细粒度的命令策略引擎
- 多级审批和批量审批

---

## 08. V7 评测与项目包装

### 1. 实现的功能

- 定义固定评测 case
- 提供统一评测入口
- 对 mapping 类型进行基础规则打分
- 生成 `eval_report.json`
- 开始整理 README、架构、demo、面试表达这些交付材料

### 2. 如何实现的

- [app/evaluation/cases/case_003_mapping.json](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/evaluation/cases/case_003_mapping.json:1)
  - 固定输入与 expected

- [app/evaluation/run_eval.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/evaluation/run_eval.py:1)
  - 批量读取 case
  - 调 graph
  - 生成评测报告

- [README.md](/data/tianshaoqi24/agent/paper_reproduction_copilot/README.md:1)
  - 理论上要承载项目背景、能力、演示方式、安全边界

核心思路是：让项目从“自己能跑”升级为“别人能验证、能理解、能展示”。

### 3. 涉及到的 Agent 知识点

- Agent evaluation
- Fixed-case benchmarking
- Failure analysis
- Project packaging
- Demo script 与面试表达

### 4. 可扩展功能或可深挖知识点

- 多 case 批量评测
- 更丰富的自动打分维度
- `eval_report.md`
- 完整 README / architecture / demo 文档

---

## 跨阶段串起来后的核心 Agent 知识图谱

把这几章串起来之后，这个项目其实已经覆盖了一个比较完整的 Agent MVP 路线：

- 输入理解
  - 论文读取
  - 仓库扫描
  - 日志读取

- 结构化表示
  - `PaperSummary`
  - `RepoMap`
  - `ModuleMapping`
  - `ExperimentPlan`
  - `DebugReport`

- 工具使用
  - 文件系统工具
  - 代码搜索工具
  - 日志分析工具
  - 命令风险评估工具

- 工作流编排
  - `StateGraph`
  - `thread_id`
  - checkpoint
  - 条件路由

- 人类协作
  - approval
  - interrupt / resume

- 可靠性建设
  - 结构化输出约束
  - 节点级测试
  - 固定 case 评测

这其实已经不是“单个 prompt 应用”，而是一个有状态、有工具、有分支、有安全边界的 Agent 原型。

---

## 当前项目开发现状判断

结合现在仓库里的实现情况，可以把当前状态概括为：

- 基础分析链路已经具备
  - 论文阅读
  - 仓库扫描
  - 代码映射
  - 实验计划

- 扩展分支已经具备原型
  - 日志 debug
  - human review

- 图工作流骨架已经具备
  - LangGraph
  - checkpoint
  - router

- 局部测试和评测已经开始补
  - V6 有 `14 passed` 的节点级测试
  - V7 有最小评测脚本

但同时还有一些明显的“下一步工程化缺口”：

- 某些分支还没完全做端到端验证
- 审批之后还没有真正执行动作的 executor 节点
- 评测 case 和展示材料还不完整
- checkpoint 仍然是内存型，不适合真正恢复跨进程任务

也就是说，当前项目已经从“概念验证”走到了“Agent MVP”，下一步最适合做的是从 MVP 走向更可靠的 demo / prototype。

---

## 下一步建议：按优先级推进什么

### 方向一：补齐端到端闭环

这是最值得优先做的。

建议继续做：

- 为 V5 增加端到端测试
  - 输入日志
  - 生成 `debug_report`
  - 验证 graph 是否真的走到 debug 分支

- 为 V6 增加 graph 级 interrupt / resume 测试
  - 不只是节点单测
  - 而是真正验证暂停、恢复、审批结果回写

- 为 V7 跑通真实 `eval_report.json`

这样做的价值是：把“代码写了”升级成“闭环跑通了”。

### 方向二：从 proposal-only 走向受控执行

这是这个项目最自然的下一步。

可以新增：

- `executor_node`
  - 只执行审批通过的 `pending_action`

- `action_builder_node`
  - 从 `ExperimentPlan.run_commands` 自动生成 `pending_action`

- `execution_result`
  - 执行后把 stdout / stderr / returncode 写回 state

这样整条链会变成：

```text
分析 -> 计划 -> 待执行动作 -> 风控 -> 人工审批 -> 受控执行 -> 日志诊断
```

这会让项目真正接近“复现 Copilot”。

### 方向三：把 memory 做成真正可恢复

当前 V4 还是 `InMemorySaver`，这更适合开发演示。

下一步可以做：

- SQLite checkpointer
- Postgres checkpointer
- 更明确的 resume CLI
- 中断后的任务列表查看

这样就能真正支持：

- 命令行退出后恢复
- 审批后恢复
- 失败后恢复

### 方向四：增强检索与证据质量

当前 V2 更多还是基于关键词搜索。

后面可以拓展：

- embedding 检索
- chunk rerank
- 代码调用图辅助定位
- 证据打分与排序

这会直接提升：

- 论文-代码映射质量
- 实验计划质量
- debug 时的文件关联质量

### 方向五：把评测体系补全

这是让项目更像成熟作品的关键。

建议继续做：

- 补 `case_001_paper.json`
- 补 `case_002_repo.json`
- 扩展更多 mapping / debug / approval case
- 让 `must_include_modules` 真正参与打分
- 增加 `eval_report.md`
- 记录失败 case 和修复前后对比

这样项目就有了持续迭代的量化依据。

### 方向六：把展示材料补齐

如果想把这个项目用于面试、汇报、作品集，这一步非常重要。

建议补：

- 完整的 `README.md`
- `docs/architecture.md`
- `docs/demo_script.md`
- 一个 3 分钟 demo 路线
- 一段简历描述

这样别人第一次看到仓库时，就能快速理解：

- 你做了什么
- 为什么这么设计
- 它的亮点和边界是什么

---

## 在这个项目基础上还能拓展成什么

如果继续往前走，这个项目可以拓展成几种更完整的形态。

### 1. 论文复现助手

把重点放在：

- 论文理解
- 代码对齐
- 计划生成
- 日志诊断
- 审批执行

这会是最贴近当前主题的产品形态。

### 2. 通用代码库理解 Agent

弱化“论文复现”，强化：

- repo map
- code search
- evidence mapping
- execution planning

这样可以推广到：

- 新项目 onboarding
- 遗留代码理解
- 配置排查

### 3. 研究工程工作流 Agent

结合论文、代码、训练、日志、实验计划、执行审批，进一步拓展成：

- 实验管理
- 失败重试
- 多轮修复
- 结果汇总

这会更接近一个真正的“研究工程自动化助手”。

---

## 最后的整体理解

这几章串起来之后，你已经不是在做一个“会聊天的模型调用脚本”，而是在逐步搭建一个真正的 Agent：

- 它能读取多源输入
- 能把输入结构化
- 能调用工具收集证据
- 能在状态图中推进任务
- 能处理失败路径
- 能请求人工介入
- 能开始做评测和包装

下一步最值得做的，不是再随意加一个新功能，而是把“闭环、执行、恢复、评测、展示”这几条主线补实。这样这个项目就会从课程式实现，成长为一个更完整、更可信、更有展示价值的 Agent 原型。
