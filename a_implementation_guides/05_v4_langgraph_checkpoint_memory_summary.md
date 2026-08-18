# 05. V4 LangGraph、Checkpoint 与 Memory 学习总结

## 这一阶段的目标

这一章的重点，是把前面 V0-V3 那种线性 CLI 串联流程，升级成一个真正的图式工作流。

输入不再只是“调用一串函数”，而是要把这些节点放进 LangGraph 的状态机里，让它具备：

- 统一的 state 流转
- 基于 `thread_id` 的任务身份
- checkpoint 保存与恢复能力
- 后续接入 interrupt、审批、debug 分支的扩展基础

简单说，这一阶段解决的是“项目怎么从一条顺序脚本，进化成一个可恢复、可扩展、可解释的图工作流”。

## 本阶段新增了什么能力

相较于前面几个阶段，V4 最大的变化不是新加了某个业务节点，而是给整个系统换了一种运行方式：

- 把线性调用改造成 `StateGraph`
- 使用统一 `ReproductionState` 作为图的状态结构
- 引入 checkpointer，开始保存 thread 级别的状态
- 提供 `run-graph` 和 `show-state` 两个新的 CLI 入口
- 为后续的 human review、log debug、resume 机制打下基础

这意味着项目开始从“能跑流程”进入“能管理流程”的阶段。

## 为什么这一阶段很关键

在 V0-V3 中，流程虽然已经能工作，但它本质上还是：

```python
state.update(node_a(state))
state.update(node_b(state))
state.update(node_c(state))
```

这种写法的问题是：

- 流程是固定直线，分支扩展不自然
- 任务中断后很难恢复
- 多轮交互时没有 thread 概念
- 后续如果加入人工审批、异常分支、debug 分支，会越来越难维护

所以 V4 的核心意义不是“接入一个新库”，而是给整个项目建立状态机式的执行骨架。

## 这一阶段最重要的三个概念

这一章最应该彻底分清的，是下面三件事：

```text
State = 单次任务运行中的工作记忆
Checkpoint = 某个 thread 在某一时刻的持久化快照
Store / Long-term Memory = 跨 thread 的长期记忆
```

它们的区别非常重要：

- `State` 是这一次任务在节点之间流转的数据。
- `Checkpoint` 是把某个 thread 当前的 state 存起来，方便恢复。
- `Store / Long-term Memory` 则是跨任务、跨 thread 的长期知识积累。

V4 做的是前两者，不是第三者。

## 为什么 V4 只做 checkpoint，不做长期 memory

这一章的一个重要取舍是：先把“短期 thread memory”做好，再谈长期 memory。

原因是：

- MVP 阶段更需要的是流程可恢复，而不是知识库积累。
- 如果连当前任务的状态都管理不好，长期 memory 会让系统更复杂。
- checkpoint 是后续 interrupt、resume、审批的前置能力。

所以 V4 的重点不是“记住历史经验”，而是“记住当前任务走到了哪里”。

## app/memory/checkpoint.py 的作用

这一阶段新增的 [app/memory/checkpoint.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/memory/checkpoint.py:1) 很短，但意义很大。

它通过 `build_checkpointer()` 返回一个 `InMemorySaver()`。

这代表：

- 当前阶段的 checkpoint 先保存在内存里
- 同一个 Python 进程里可以取回
- 但一旦进程结束，checkpoint 就会丢失

这是一种非常适合开发验证阶段的实现：

- 上手简单
- 不需要额外数据库
- 足够验证 LangGraph 的 thread / checkpoint 机制

但它的局限也非常明确：不能跨进程持久化。

## InMemorySaver 的意义与局限

`InMemorySaver` 最大的价值，是让你在不引入 SQLite、Postgres、Redis 的情况下，先把 checkpoint 机制跑通。

它适合回答的问题是：

- 图在同一进程里能不能保存状态
- `thread_id` 能不能把不同任务区分开
- `get_state()` 和 `invoke()` 的基本机制是否正常

但它不适合回答：

- 进程结束后还能不能恢复
- 两条独立命令之间能不能共享 checkpoint

这意味着：

- 在同一个进程内测试，它通常够用
- 在命令行里先 `run-graph` 再单独执行 `show-state`，大概率会看到空快照

这不是 LangGraph 坏了，而是 `InMemorySaver` 的天然行为。

## app/graph.py 在做什么

这一阶段新增的 [app/graph.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/graph.py:1) 是整个 V4 的核心。

它做了几件关键事情：

- 创建 `StateGraph(ReproductionState)`
- 把前面各阶段的节点注册进去
- 定义边和执行顺序
- 编译图并挂上 checkpointer

这里最重要的变化是：

- V0-V3：节点只是普通函数
- V4：节点开始成为图中的状态转换单元

也就是说，节点没有变，但“节点是怎么被组织起来的”彻底变了。

## graph 的主链路是什么

当前图的执行顺序是：

```text
START
  -> paper_reader
  -> method_extractor
  -> repo_scan
  -> code_search
  -> mapping
  -> experiment_plan
  -> END
```

这是把前面阶段的线性流程原样搬进图里，作为最初版本。

这么做的好处是：

- 先保证图式版本和线性版本的业务链路一致
- 等基础跑通后，再逐步引入分支和恢复逻辑

## `route_after_plan()` 为什么存在

虽然当前 `route_after_plan()` 只是简单返回 `END`，但它的存在非常关键。

这说明图的终点不是写死在普通边上的，而是已经为“条件分支”留好了接口。

它代表一种设计意识：

- 现在先结束
- 以后这里可以根据 state 决定去 debug、审批、人工 review、继续执行等不同分支

所以这个函数的价值不在“当前逻辑复杂”，而在“它定义了未来流程扩展的位置”。

## ReproductionState 在图里为什么更重要了

在 V0-V3 里，`ReproductionState` 更像是“结构说明”和“类型提示”。

但到了 V4，情况不一样了。

因为：

- 线性 CLI 里，`state` 只是普通 `dict`
- LangGraph 里，`StateGraph(ReproductionState)` 会把 state 结构当成图的核心接口

这意味着：

- 节点读什么、写什么，必须更严格地对齐
- 中间字段如果没有进入 state 结构，后续节点可能读不到

换句话说，V4 之后 `state.py` 不再只是“文档化”，而是真正参与流程边界定义。

## 线性 CLI 和 LangGraph 的本质区别

这是这一章最需要建立的直觉。

在线性 CLI 里，流程像这样：

```python
state.update(node_a(state))
state.update(node_b(state))
```

只要某个节点返回了一个新键，比如 `code_search_results`，这个键就会直接进入 `state`。

但在 LangGraph 里，状态的传递变成了：

- 图按 `ReproductionState` 组织 state
- 节点之间通过图的 state 接口交换数据

这就要求你比以前更认真地维护：

- state 里有哪些字段
- 每个节点写哪些字段
- 下一个节点读哪些字段

所以很多“线性 CLI 正常、graph 版本却断掉”的问题，本质上都是 state 对齐问题。

## thread_id 在这一阶段的意义

V4 开始，每次运行不再只是“跑一次命令”，而是“在某个 thread 上跑一次任务”。

`thread_id` 的作用是：

- 标识同一个任务流
- 让同一个任务的 checkpoint 能被识别
- 为后续恢复、审批和中断继续提供锚点

这意味着：

- 如果想恢复同一个任务，必须使用同一个 `thread_id`
- 如果换了 `thread_id`，LangGraph 会把它看作一个新任务

这个概念在后面的 interrupt / human review 阶段会变得更重要。

## CLI 入口在这一阶段的变化

V4 新增了两个非常关键的命令：

- `run-graph`
- `show-state`

`run-graph` 的作用是：

- 构造初始输入 state
- 绑定 `thread_id`
- 调用 `graph.invoke(...)`

`show-state` 的作用是：

- 基于相同的 `thread_id`
- 调用 `graph.get_state(config)`
- 查看某个 thread 的当前状态快照

这两个 CLI 命令一起，构成了 V4 的最小可演示闭环：

- 跑图
- 看图状态

## 本阶段验收标准

这一阶段完成后，至少应该满足：

- 图能够按节点顺序运行。
- 可以通过 `thread_id` 区分不同任务。
- 可以解释每个 node 读取和写入哪些 state 字段。
- 可以说明 `State`、`Checkpoint`、`Store` 的区别。
- 可以说明为什么当前只用了 `InMemorySaver`。

如果这些都能讲清楚，就说明你不只是“会用 LangGraph API”，而是真的理解了这一阶段的设计目标。

## 这一阶段的关键收获

这一章最重要的收获，不是某个函数的写法，而是下面这些工程观念：

- 图工作流比线性脚本更适合复杂 Agent 系统。
- state 是节点之间的共享协议，不只是一个临时字典。
- checkpoint 解决的是 thread 级恢复问题，不是长期知识记忆问题。
- `thread_id` 是后续恢复、审批和中断执行的基础。
- 在图系统里，节点逻辑和状态结构必须一起设计。

## 本阶段容易遇到的问题及解决思路

这一阶段最容易误判的，恰恰不是业务逻辑，而是 checkpoint 和 state 机制本身。

### 1. `show-state` 为空，误以为 checkpoint 没工作

典型现象是：

- 先执行 `python -m app.main run-graph ...`
- 再执行 `python -m app.main show-state --thread-id ...`
- 看到空的 `StateSnapshot(values={})`

根因通常不是图没跑，而是：

- 当前使用的是 `InMemorySaver`
- 两条命令是两个独立 Python 进程
- 第一条命令结束后，内存里的 checkpoint 已经丢了

解决思路：

- 理解 `InMemorySaver` 的边界：它不能跨进程持久化。
- 如果想真正跨命令恢复，要换成 SQLite、Postgres 或 Redis 等持久化 saver。

### 2. 线性 CLI 正常，graph 版本却只跑到一半

这种现象在 V4 很典型：

- 线性 `state.update(...)` 版本正常
- 进入 graph 后，前半段产物有，后半段产物没出

常见根因是：

- graph 使用了 `ReproductionState`
- 某些中间字段没有完整纳入 state 结构
- 后续节点读不到需要的数据

解决思路：

- 对照 `app/state.py` 检查所有中间字段是否都声明了
- 对照每个节点的输入输出字段，确保写入和读取严格对齐

### 3. 图“finished”了，但状态和产物不完整

这类问题很容易误导人，以为“finished 就说明都成功了”。

实际上：

- 图可以走到 `END`
- 但中间某些节点可能返回了 `error`
- 或某些字段没有被正确承接

解决思路：

- 不要只看 “graph finished”
- 还要看最终返回的 state 里有哪些字段
- 还要看预期输出文件是否都生成了

### 4. 把 checkpoint 当成长期 memory

这也是一个很常见的概念性误区。

checkpoint 解决的是：

- 当前 thread 的执行位置和状态恢复

它不解决：

- 跨任务知识积累
- 长期经验记忆
- 不同 thread 之间的共享知识

解决思路：

- 把 checkpoint 只看作“短期 thread memory”
- 把长期 memory 留到后面阶段再设计

## 本阶段最重要的理解

V4 看起来像是在“把代码改成 LangGraph”，但本质上是在做一件更底层的事情：

- 从顺序脚本转向状态机
- 从一次性执行转向 thread 化任务管理
- 从隐式数据流转转向显式 state 协议

如果这一阶段做扎实，后面的 interrupt、human review、resume、debug 分支和评测体系，都会更自然，因为它们都建立在这套 graph + state + checkpoint 机制上。

## 局限性

这一阶段仍然有几个明显局限：

- `InMemorySaver` 不能跨进程持久化。
- 当前图结构仍然比较线性，条件分支还很少。
- 如果 state 结构定义不完整，graph 版本会比线性版本更容易暴露问题。
- 这一阶段只解决短期 thread memory，不涉及长期 memory/store。
