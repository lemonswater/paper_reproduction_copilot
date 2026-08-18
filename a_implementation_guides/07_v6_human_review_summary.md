# 07. V6 Human-in-the-loop 安全审批学习总结

## 这一阶段的目标

这一章的重点，是让系统在准备产生副作用之前先停下来，等待人工确认，而不是让 Agent 直接拥有任意执行权限。

这里的“副作用”主要包括：

- 执行命令
- 修改配置
- 写用户仓库文件

而像论文阅读、仓库扫描、日志分析这类只读工作，则不需要额外审批。

简单说，这一阶段解决的是“Agent 可以提出行动建议，但真正动手前必须先过一道安全闸门”。

## 本阶段新增了什么能力

相较于前面的 V0-V5，V6 最大的变化不是新增一个分析节点，而是新增了一套“执行前风控与人工审批”机制：

- 对命令做风险分级。
- 对不同类型的待执行动作做审批判断。
- 对高风险动作触发人工确认。
- 使用 LangGraph 的 `interrupt()` 暂停图执行。
- 为后续 resume、真正执行命令、修改配置打下基础。

这意味着项目开始从“能分析、能规划、能调试”进一步走向“能受控地行动”。

## 为什么这一阶段很关键

如果 Agent 只有分析能力，那它最多是一个顾问。

但一旦系统开始接触：

- shell 命令
- 配置修改
- 仓库写操作

就必须解决一个更重要的问题：如何控制副作用风险。

所以 V6 的核心价值，不是让 Agent 真的去执行更多事情，而是先建立“什么能做、什么必须审、什么绝对不能做”的规则体系。

## 本阶段的安全原则

这一章最重要的一组原则是：

```text
只读分析工具：默认允许
写 outputs 文件：允许
修改用户 repo：必须审批
执行命令：必须审批
危险命令：禁止
```

这组规则的意义在于，系统并没有把所有能力一刀切地关闭，而是按风险等级做分层管理。

## app/tools/safe_shell_tools.py 在做什么

[app/tools/safe_shell_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/safe_shell_tools.py:1) 是这一阶段的第一道安全检查。

它的核心职责是：

- 解析命令
- 判断命令风险等级
- 给出原因
- 标记是否应直接阻断

其中最关键的结构有两个：

- `RiskLevel`：定义风险等级，允许值是 `low`、`medium`、`high`、`blocked`
- `CommandRisk`：统一保存命令、风险等级、原因和是否阻断

最核心的函数是 `assess_command_risk()`：

- 先用 `shlex.split()` 按 shell 规则拆命令
- 空命令直接阻断
- 如果命令前缀命中 `BLOCKED_TOKENS`，直接判成 `blocked`
- 环境变更类命令，如 `pip install`、`conda install`、`python -m ...`，判成 `high`
- 训练/脚本执行类命令，如 `python`、`torchrun`、`accelerate`，判成 `medium`
- 其他未知命令默认也要求人工复核

这一层的设计思想非常明确：先做保守风控，而不是让 Agent 自己随意解释命令是否安全。

## 为什么命令风控要单独拆成工具层

如果把命令风险判断直接散落在节点里，会有几个问题：

- 规则不集中，后面不好维护
- 不同节点容易出现不一致判断
- 测试时不容易单独验证

把它独立成 `safe_shell_tools.py` 后，命令安全策略就成了一套可复用、可单测、可扩展的基础设施。

## app/nodes/risk_check_node.py 在做什么

[app/nodes/risk_check_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/risk_check_node.py:1) 是图里的“动作风控节点”。

它处理的是 `state["pending_action"]`，也就是：

- 前面的节点已经决定“下一步想做什么”
- 但还没真正执行
- 先把动作描述放进 `pending_action`
- 再交给 `risk_check_node()` 做风险判断

它的逻辑分成三类：

- 没有 `pending_action`
  - 说明没有待执行动作
  - 直接返回 `requires_approval=False`

- `type == "run_command"`
  - 调用 `assess_command_risk()`
  - 把风险结果写回 `pending_action["risk"]`
  - 如果是 `blocked`，直接写 `error`
  - 如果不是 `blocked`，设置 `requires_approval=True`

- `type in {"modify_config", "write_repo_file"}`
  - 一律视为高风险
  - 需要人工审批

- 其他未知动作
  - 默认按 `medium` 处理
  - 同样进入审批流程

所以这个节点的本质，是把“一个准备执行的动作”转换成“可审批的安全对象”。

## blocked 和 requires_approval 的区别

这是这一章特别容易混淆，但又非常重要的点。

- `blocked`
  - 表示系统认为这个动作本身就不应该执行
  - 例如 `rm`、`sudo`、`dd`
  - 这种情况不会进入人工审批，而是直接报错

- `requires_approval`
  - 表示这个动作不是绝对禁止，但不能自动执行
  - 需要人确认后才能继续

也就是说：

- `blocked` 是硬拦截
- `requires_approval` 是人工闸门

## app/nodes/human_review_node.py 在做什么

[app/nodes/human_review_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/human_review_node.py:1) 是这一阶段最关键的交互节点。

它使用 LangGraph 的 `interrupt()` 机制来暂停图执行，等待外部输入审批结果。

它的流程很简单，但概念非常重要：

1. 先看当前是否真的需要审批。
2. 如果不需要，直接返回 `not_required`。
3. 如果需要审批但没有 `pending_action`，返回 `missing_action`。
4. 如果审批条件齐全，就构造一个 payload：
   - 提示信息
   - 当前待审批动作
   - 允许的返回值
5. 调用 `interrupt(payload)` 暂停图。
6. 等外部用 `resume` 恢复后，把审批结果写回：
   - `user_approval`
   - `human_feedback`

这一步的意义不在于“多了一个函数”，而在于图第一次真正具备了 human-in-the-loop 的暂停与恢复能力。

## 为什么 interrupt 机制很重要

`interrupt()` 带来的不是普通函数返回，而是工作流层面的暂停点。

它意味着：

- 图执行可以中断
- 可以把当前任务挂起等待人类决策
- 后续可以用相同 `thread_id` 恢复
- 审批流程可以和 checkpoint 机制结合起来

这正是 V4 引入 checkpoint 与 `thread_id` 的原因之一。V6 让这些基础设施开始真正发挥作用。

## interrupt 的一个关键注意点

这一章有一个非常重要的工程细节：

- 调用 `interrupt()` 的节点在恢复时，会从节点开头重新执行。

这意味着：

- `interrupt()` 之前的逻辑必须尽量幂等
- 不要在 `interrupt()` 前面写会产生副作用的操作
- 比如不要先写文件、删文件、改配置，再去等审批

当前 `human_review_node()` 只构造 payload，不做真实写操作，这就是一种比较安全的设计。

## 这一阶段和 Graph 的关系

V6 不是单独加一个“审批脚本”，而是把审批逻辑接进已有的 LangGraph 工作流。

图里的核心路由变成：

```text
experiment_plan
  -> 如果有 pending_action：进入 risk_check
  -> 否则如果有 log_path：进入 log_debug
  -> 否则结束

risk_check
  -> 如果 requires_approval：进入 human_review
  -> 否则结束
```

这说明图已经不仅有“成功主链”和“日志 debug 分支”，还开始拥有“人工审核分支”。

## pending_action 为什么是这一阶段的关键接口

`pending_action` 是 V6 最核心的状态字段之一。

因为它把“建议”与“执行”之间插入了一层显式状态：

- 不是节点直接执行某件事
- 而是节点先声明“我想做这个动作”
- 再交给风控与人工审核决定

这个设计非常关键，因为它让后续的命令执行、配置修改、审批记录、失败恢复都能基于统一接口扩展。

## CLI resume 的意义

这一阶段教程里还引入了 `resume_review` 这个思路。

它的作用是：

- 使用相同的 `thread_id`
- 通过 `Command(resume=...)`
- 把人工审批结果送回此前被 `interrupt()` 挂起的图

这一步代表 V6 不只是“停一下问人”，而是已经开始建立“暂停 -> 人工反馈 -> 恢复执行”的闭环。

## 本阶段的验收标准

这一阶段从设计上至少应该满足：

- 构造 `pending_action` 后，系统可以进入 `risk_check_node`
- 命令可以被分成 `blocked` / `high` / `medium`
- 高风险但非禁止动作会进入人工审批
- `human_review_node` 可以触发 `interrupt`
- 使用相同 `thread_id` 和 `Command(resume=...)` 理论上可以恢复图执行

## 当前已经验证成功的部分

这次你已经补上了 V6 的一组节点级测试，并且测试结果是：

```text
python -m pytest tests/test_review_flow.py
14 passed in 0.11s
```

对应的测试文件是：

- [tests/test_review_flow.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/tests/test_review_flow.py:1)

这说明当前至少有下面这些逻辑已经测通：

- `assess_command_risk()` 对常见命令的风险分类
- `risk_check_node()` 对 `run_command`、`modify_config`、`write_repo_file` 的判断
- `human_review_node()` 在 `not_required`、`missing_action`、有审批结果时的返回逻辑
- `risk_check + human_review` 的节点级串联流程

也就是说，V6 的基础审批链路已经通过了单元测试。

## 当前还没有完全验证的部分

虽然节点级测试已经通过，但目前还不能说 V6 的整条图式审批流程已经端到端完全验证成功。

当前还需要和“已经测通”区分开的部分包括：

- 是否已经有前置节点会自动产出 `pending_action`
- `interrupt()` 触发后的真实 graph 暂停行为
- 使用 CLI 的 `resume_review` 恢复图执行是否完全打通
- 审批通过后，后续动作是否已经真正接入执行链

所以当前最准确的判断是：

- 节点级逻辑：已经成功验证
- LangGraph 端到端审批恢复链：还需要后续补测

## 本阶段容易遇到的问题及解决思路

### 1. 把“审批”理解成“直接执行”

这一章的重点其实不是立即执行命令，而是先建立审批机制。

解决思路：

- 把 V6 看成 proposal-only 阶段
- 先把风险标注、人工确认、恢复接口搭起来

### 2. 不区分 blocked 和 requires_approval

这会导致逻辑混乱：

- 有些命令应该直接禁止
- 有些命令只是需要人确认

解决思路：

- 明确 `blocked` 是硬拒绝
- 明确 `requires_approval` 是待审批

### 3. 在 interrupt 前面做副作用操作

如果节点恢复时从头重跑，就可能重复执行。

解决思路：

- `interrupt()` 前尽量只做纯计算和 payload 构造
- 不要先写文件再等审批

### 4. 图里没有 pending_action，就永远进不了审批分支

这是当前开发阶段最常见的现实问题。

解决思路：

- 先手工构造 `pending_action` 做节点级测试
- 等后续阶段再让前置节点自动产出动作

### 5. 单元测试通过，不等于端到端恢复已经完全验证

这一点很容易被忽略。

解决思路：

- 单元测试先确认节点逻辑正确
- 后面再补 graph interrupt/resume 的集成测试

## 这一阶段最重要的理解

V6 表面上是在“做人类审批”，但本质上是在给 Agent 建立一套安全边界。

它带来的关键变化是：

- Agent 不再默认拥有任意执行权
- 待执行动作被显式表示成 `pending_action`
- 风险判断和动作执行开始解耦
- 图开始支持真正的人类介入
- 后续自动执行、恢复和审计都有了结构化入口

如果这一阶段做扎实，项目就不只是“会分析论文、会生成计划”的 Copilot，而是开始具备“受控行动能力”的 Agent 雏形。
