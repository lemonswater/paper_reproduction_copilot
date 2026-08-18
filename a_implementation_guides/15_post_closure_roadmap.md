# 15. 端到端闭环完成后：下一阶段优先级路线图

这份文档专门回答一个问题：

> 当 `分析 -> 计划 -> 审批 -> 执行 -> 失败调试 -> final_report -> eval` 这条端到端闭环已经跑通之后，下一步最值得继续做什么？

这里的重点不再是“再补一个孤立功能点”，而是把项目从：

```text
能跑通一次的 Agent Demo
```

推进到：

```text
更稳定、更可恢复、更可评测、更接近真实研究工程助手的 Agent Prototype
```

---

## 一、先给结论：后续重点要从“补功能”切到“补系统能力”

在闭环完成之前，最重要的是把链路串起来：

```text
paper -> repo -> mapping -> plan -> action -> approval -> execute -> debug -> report
```

但闭环完成之后，优先级会发生明显变化。

这时候项目最缺的往往已经不是：

- 再多一个 node
- 再多一个 prompt
- 再多一个 outputs 文件

而是下面这些能力：

- 进程退出之后还能不能恢复
- 同一条任务链能不能稳定重复跑
- 每次改代码后能不能量化知道效果变好还是变差
- 执行失败后能不能继续自动往前推进，而不是只停在 debug report
- 系统的行为边界、风险边界、审计信息够不够清楚

所以后面的重点应该从“功能补洞”切换成：

```text
可靠性
可恢复性
可观测性
可评测性
有限自治
```

---

## 二、优先级总览

如果按“投入产出比 + 对整体能力的提升幅度”排序，我建议下一阶段按下面这个顺序推进：

### 第一优先级

1. 持久化 checkpoint 与真正可恢复的 resume
2. 可观测性与评测体系补全

### 第二优先级

3. 执行前环境预检（preflight check）
4. 从 debug 走向 repair proposal / rerun

### 第三优先级

5. 检索与证据质量升级
6. 产品化展示与开发者体验补全

你可以把它理解成：

```text
先保证“能稳”
再保证“能量化”
再提升“能自我推进”
最后再追求“更聪明、更好展示”
```

---

## 三、Phase 5：持久化 Checkpoint 与真正可恢复的 Resume

这是闭环完成后最值得优先做的方向。

### 1. 目标功能

把当前偏开发态的内存型恢复能力，升级成真正可跨进程恢复的执行能力。

希望最终支持：

- `run_graph` 跑到一半中断后，下次还能继续
- `human_review` interrupt 后，可以在新进程中 `resume`
- 能查看某个 `thread_id` 的最近状态、运行阶段和产物
- 能区分“已经执行过的动作”和“待执行动作”，避免恢复后重复副作用

### 2. 为什么它最优先

因为闭环做完后，系统最脆弱的地方通常不是推理本身，而是执行过程。

例如：

- 审批时中断
- 执行命令时间很长
- 进程异常退出
- 你想第二天继续接着调

如果这时 checkpoint 还是只存在内存里，那么很多“Agent 工作流能力”其实只是演示态，不算真正可靠。

### 3. 如何实现

建议优先改这些位置：

- [app/memory/checkpoint.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/memory/checkpoint.py:1)
  - 把 `InMemorySaver` 换成持久化 saver
  - 第一版可以优先选 SQLite，门槛低、调试方便

- [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:1)
  - 增加：
    - `list-runs`
    - `show-run`
    - `resume-review`
    - `resume-run`
  - 让 CLI 不只是“触发一次运行”，还能管理运行中的任务

- [app/state.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/state.py:1)
  - 补充更明确的运行态字段，例如：
    - `run_id`
    - `current_stage`
    - `retry_count`
    - `created_at`
    - `updated_at`
    - `artifacts`

- [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1)
  - 检查哪些节点在 resume 时可能重复执行
  - 对有副作用的节点补幂等保护

### 4. 核心思路

这一阶段最核心的不是“把 saver 换掉”这么简单，而是建立这套意识：

```text
图工作流里的每个节点，都要考虑：
1. 是否无副作用
2. 是否可重复执行
3. 恢复后如果重放，会不会产生错误结果
```

这就是 Agent 工程里很重要的“幂等性”和“durable execution”思维。

### 5. 涉及的 Agent 知识点

- durable execution
- checkpoint persistence
- interrupt / resume 语义
- idempotency
- side effect control
- run lifecycle management

### 6. 这一阶段的验收标准

至少做到：

- 用两条独立 CLI 命令也能恢复被中断的 review
- 执行到一半的任务可以重新查看状态
- 恢复后不会重复跑已经成功完成的阶段
- `show_state` 不再只是空壳，而是能看到真实有效的运行信息

### 7. 还能继续深挖什么

- Postgres checkpointer
- 多任务并发恢复
- artifact 版本索引
- 审批历史与审计日志

---

## 四、Phase 6：可观测性与评测体系补全

这是第二个非常值得优先做的方向。

### 1. 目标功能

让你每次改 prompt、改 schema、改 graph 路由之后，都能回答：

```text
系统到底更好了，还是更差了？
```

这一步要补的不只是 `eval_report.json`，还包括运行过程级别的观测信息。

### 2. 为什么它优先级很高

因为闭环完成之后，系统复杂度已经明显上来了：

- 有多个 node
- 有条件路由
- 有 interrupt / resume
- 有执行成功和失败分支
- 有 debug 分支
- 有 final_report 和 eval

这时如果没有观测和评测，你会很难定位：

- 是 mapping 质量差导致 plan 错
- 还是 plan 合理但 action_builder 取错命令
- 还是 executor 跑通了但 report 没写对

### 3. 如何实现

建议重点补这些部分：

- [app/evaluation/run_eval.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/evaluation/run_eval.py:1)
  - 不只统计 mapping score
  - 还统计：
    - `final_status`
    - 是否触发 debug
    - 是否生成 `final_report`
    - 是否进入 human review
    - 是否成功 resume

- `app/evaluation/cases/`
  - 增加更多 case 类型：
    - 纯分析 case
    - approval case
    - executor success case
    - executor fail -> debug case
    - resume case

- 建议新增：
  - `app/evaluation/scorers.py`
  - `app/evaluation/reporting.py`
  - 用于把“跑 case”和“算分/生成报告”解耦

- 可以新增一个统一运行日志模块，例如：
  - `app/runtime_logging.py`
  - 为每个 node 记录：
    - 开始时间
    - 结束时间
    - 输入摘要
    - 输出摘要
    - 错误信息

### 4. 核心思路

把“Agent 好不好”拆成多维指标，而不是只看最终有没有产物。

例如可以按下面这些维度记录：

- 结构化输出成功率
- 路由正确率
- 执行成功率
- debug 触发率
- debug 后定位有效率
- 人工介入率
- 平均运行耗时

### 5. 涉及的 Agent 知识点

- agent evaluation
- regression benchmarking
- route-level metrics
- observability
- failure analysis
- experiment tracking

### 6. 这一阶段的验收标准

至少做到：

- 有一组固定 case 能批量运行
- 每次改动后都能复跑并比较结果
- 失败 case 能看到失败发生在哪个阶段
- `eval_report.md` 能被人直接阅读，而不仅仅是机器 JSON

### 7. 还能继续深挖什么

- LLM-as-judge 评分
- 基于 diff 的回归评测
- node latency dashboard
- 成本统计和 token 统计

---

## 五、Phase 7：执行前环境预检（Preflight Check）

这是一个工程价值很高、但很容易被低估的方向。

### 1. 目标功能

在真正执行 `run_command` 之前，先做一次环境与依赖检查，尽量把明显问题前置暴露。

例如检查：

- Python 版本
- 虚拟环境是否激活
- 关键依赖是否安装
- GPU / CUDA 是否可用
- 数据路径是否存在
- 配置文件是否存在
- 输出目录是否可写

### 2. 为什么值得优先做

很多复现失败并不是“复杂 bug”，而是最基础的环境问题。

如果系统每次都要先真正执行一遍，失败后再 debug，效率会很低。

更好的做法是：

```text
先做 deterministic check
能提前发现的问题，就不要等执行时报错
```

### 3. 如何实现

建议新增：

- `app/tools/preflight_tools.py`
  - 封装环境探测逻辑

- `app/nodes/preflight_check_node.py`
  - 在 executor 前运行
  - 生成结构化 `PreflightReport`

- [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1)
  - 增加：
    - `PreflightItem`
    - `PreflightReport`

- [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1)
  - 路由改成：

```text
action_builder
  -> risk_check
  -> human_review
  -> preflight_check
  -> executor
```

### 4. 核心思路

这一步要坚持“工具优先、规则优先”。

也就是说，预检不应该一上来就让 LLM 猜环境，而应该尽量：

- 直接查文件
- 直接查命令返回
- 直接查目录
- 直接查依赖

LLM 可以在最后只负责“解释预检结果”和“给建议”。

### 5. 涉及的 Agent 知识点

- tool-first agent design
- deterministic validation
- environment reasoning
- execution gating
- failure prevention

### 6. 这一阶段的验收标准

至少做到：

- 缺依赖、缺路径、缺配置这类问题能在执行前发现
- preflight 结果能结构化落盘
- 明显不满足执行条件时，不再进入 executor

### 7. 还能继续深挖什么

- 自动生成环境安装建议
- 自动识别 README 中的依赖说明
- 针对不同 repo 类型做不同预检模板

---

## 六、Phase 8：从 Debug 走向 Repair Proposal / Rerun

这是后续最有“Agent 味道”的拓展方向。

### 1. 目标功能

把当前的失败链路：

```text
executor failed -> log_debug -> final_report
```

进一步升级成：

```text
executor failed
  -> log_debug
  -> repair proposal
  -> human review
  -> apply repair / rerun
  -> verify result
```

### 2. 为什么它值得做

因为这一步会让项目从：

```text
能分析失败
```

真正迈向：

```text
能基于失败继续推进任务
```

这也是很多 Agent 项目最核心的价值点之一。

### 3. 但要注意：不要一开始就做“自动改代码”

这里强烈建议分两层推进：

#### 第一层：Repair Proposal

先只输出：

- 改哪里
- 为什么改
- 怎么改
- 改完要怎么验证

也就是生成结构化修复方案，而不是立刻自动写文件。

#### 第二层：Bounded Repair Execution

等第一层稳定后，再考虑：

- 只允许改白名单目录
- 只允许改配置 / 启动命令 / 路径
- 改动前后都留 patch
- 改后必须 rerun 验证

### 4. 如何实现

建议新增：

- `app/nodes/repair_planner_node.py`
  - 根据 `debug_report` 生成修复方案

- `app/schemas.py`
  - 增加：
    - `RepairStep`
    - `RepairProposal`
    - `VerificationPlan`

- `app/prompts/repair_prompt.py`
  - 强约束模型只输出可执行、可验证、可回滚的修复建议

- [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1)
  - 在 `log_debug` 后增加 repair 分支

### 5. 核心思路

这一步最重要的不是“自动化程度越高越好”，而是：

```text
有界自治
```

也就是系统必须明确：

- 什么能自动做
- 什么必须人工审批
- 改完怎么验证
- 失败几次后停止

### 6. 涉及的 Agent 知识点

- repair loop
- bounded autonomy
- self-correction
- verification after action
- safety policy for file modification

### 7. 这一阶段的验收标准

至少做到：

- debug 后能输出结构化修复建议
- 修复建议里包含验证步骤
- 能明确区分“只建议”和“允许执行”

### 8. 还能继续深挖什么

- 自动生成 patch
- 自动重试有限次数
- 多轮 debug -> repair -> rerun 链
- 针对常见错误模式建立 repair template

---

## 七、Phase 9：检索与证据质量升级

这是提升“分析质量”的关键方向。

### 1. 目标功能

增强论文-代码映射、实验计划、debug 定位时使用的检索质量和证据质量。

### 2. 为什么它排在这个位置

因为它确实重要，但在闭环完成之后，它通常没有：

- 持久化恢复
- 评测体系
- preflight

这几项那么“基础设施级”。

换句话说，它更像：

```text
提高系统上限
```

而前面几项更像：

```text
提高系统下限和稳定性
```

### 3. 如何实现

建议从“混合检索”开始，不要一下子全改成 embedding。

可以分三步：

#### 第一步：继续保留 `rg`

因为：

- 快
- 透明
- 可解释

#### 第二步：补 symbol / AST / import 级线索

继续增强：

- [app/tools/code_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/code_tools.py:1)
- [app/tools/search_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/search_tools.py:1)

例如加入：

- 函数定义索引
- 类定义索引
- import 关系
- 调用链线索

#### 第三步：引入 embedding + rerank

可以考虑新增：

- `app/tools/index_tools.py`
- `app/tools/retrieval_tools.py`

让候选召回来自多路：

- keyword search
- symbol search
- semantic retrieval

最后再做 rerank。

### 4. 核心思路

这里不要只追求“搜得更多”，而是要追求：

- 候选更准
- 证据更短
- 证据更可解释
- 映射置信度更明确

### 5. 涉及的 Agent 知识点

- hybrid retrieval
- code intelligence
- grounding
- reranking
- confidence estimation

### 6. 这一阶段的验收标准

至少做到：

- mapping 结果的证据更稳定
- plan 中引用的命令或文件更少“拍脑袋”
- debug 结果能更频繁地关联到具体文件 / 函数 / 配置项

### 7. 还能继续深挖什么

- call graph
- cross-file reasoning
- section-to-code alignment
- 基于历史成功案例的 retrieval memory

---

## 八、Phase 10：展示层、README、开发者体验

这是“作品化”的关键方向。

### 1. 目标功能

让别人第一次打开仓库时，不需要读很多源码，也能快速理解：

- 这个 Agent 做什么
- 它能跑到哪一步
- 如何演示
- 安全边界是什么
- 当前局限是什么

### 2. 为什么它不是第一优先级

因为展示建立在真实能力之上。

如果系统本身还不稳，过早投入 UI 或包装，收益有限。

但在前面几项补得差不多后，这一步会明显提升项目的展示价值。

### 3. 如何实现

建议重点补：

- [README.md](/data/tianshaoqi24/agent/paper_reproduction_copilot/README.md:1)
  - 项目背景
  - 架构图
  - 快速开始
  - demo 命令
  - 安全边界
  - 当前限制

- 新增：
  - `docs/architecture.md`
  - `docs/demo_script.md`
  - `docs/evaluation_notes.md`

- 如果后面想补简单可视化，可以考虑：
  - 一个最小的 artifact viewer
  - 一个任务时间线页面
  - 一个运行结果汇总页面

### 4. 涉及的 Agent 知识点

- agent packaging
- developer experience
- reproducible demo design
- system boundary communication

### 5. 这一阶段的验收标准

至少做到：

- 新同学或面试官能按 README 跑通一次 demo
- 可以在 3 分钟内讲清系统架构
- 能展示成功路径和失败调试路径

---

## 九、哪些方向现在先不要太早做

闭环刚做完时，有几类方向看起来很吸引人，但不建议太早投入太多精力。

### 1. 长期记忆（Long-term Memory）

当前项目更需要的是：

- durable checkpoint
- run history
- case eval

而不是一上来就做“跨任务经验记忆”。

长期记忆很容易做成一个概念上很大、但短期收益有限的模块。

### 2. 多 Agent 协作

现在单 Agent 主链都还有很多值得打磨的地方：

- resume
- repair
- preflight
- eval

过早拆成多 agent，复杂度会明显上升。

### 3. 自动改代码且无审批

这会把风险边界一下子抬得很高。

更稳的顺序应该是：

```text
repair proposal
-> human review
-> bounded patch
-> rerun verify
```

而不是一步到位做“完全自动改仓库”。

---

## 十、如果只给你接下来两周，建议怎么排

### 第一周

1. 做持久化 checkpoint
2. 打通真正可恢复的 resume
3. 给运行状态补 run metadata
4. 增加 1 到 2 个 resume 相关测试

### 第二周

1. 补 eval case
2. 补 route-level 指标
3. 补 `eval_report.md`
4. 增加 preflight check 的最小版本

这两周做完后，你的项目会从：

```text
能跑通
```

升级成：

```text
能恢复、能比较、能更稳地跑
```

---

## 十一、如果只选一个最值得深挖的 Agent 知识方向

如果你现在想选一个方向深入，而不是平均铺开，我最建议你深挖：

```text
Durable Execution + Human-in-the-loop + Evaluation
```

原因是这三个点组合起来，最能体现你这个项目和普通“prompt + tools 脚本”的差异。

它会直接体现你理解了：

- Agent 不是一次性调用
- Agent 是有状态、有中断、有恢复的流程系统
- Agent 要考虑副作用和安全边界
- Agent 需要评测，而不是只凭感觉说“好像能用”

这也是最有工程深度、最有展示价值的一条主线。

---

## 十二、最后的整体建议

闭环完成之后，最应该避免的事情是：

```text
继续零散地加功能
```

更好的做法是按主线推进：

### 主线一：可靠性

- checkpoint 持久化
- resume 真恢复
- 幂等执行

### 主线二：可量化

- eval case
- route metrics
- failure analysis

### 主线三：有限自治

- preflight
- repair proposal
- rerun verify

### 主线四：能力上限

- retrieval upgrade
- better evidence
- smarter planning

### 主线五：作品化

- README
- docs
- demo
- 可视化展示

如果按这个节奏推进，你这个项目后面会越来越像一个真正的研究工程 Agent，而不只是一个课程式的阶段练习项目。
