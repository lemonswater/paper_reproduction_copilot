# 08. V7 评测与项目包装学习总结

## 这一阶段的目标

这一章的重点，不再是继续往图里堆新节点，而是把整个项目从“自己能跑通”整理成“别人能理解、能验证、能展示”的作品。

这一阶段要补齐的核心内容包括：

- 固定评测 case
- 期望结果定义
- 评测脚本
- 失败分析
- README
- 架构说明
- 演示脚本
- 面试表达

简单说，这一阶段解决的是“项目如何从开发状态，进入可演示、可复盘、可面试介绍的状态”。

## 本阶段新增了什么能力

相较于前面的 V0-V6，V7 最大的变化不是新增业务能力，而是新增了一套“项目交付与展示能力”：

- 用固定 case 评估图流程，而不是只靠临时手测。
- 用统一报告记录效果，而不是只展示几张输出文件截图。
- 用 README、架构文档和 demo script 组织叙事。
- 把“做了什么”提升成“能不能讲清楚、能不能证明有效、能不能展示边界”。

这意味着项目开始从“开发练习”走向“作品集项目”。

## 为什么评测与包装同样重要

如果项目只有代码，没有评测和说明，别人很难判断：

- 它到底稳定不稳定
- 它在哪些 case 上表现正常
- 它失败时会怎样
- 它和普通脚本相比有什么工程价值

所以这一章的重点不是再增强模型能力，而是建立：

- 可重复验证的 case
- 可解释的失败记录
- 可展示的项目叙事

## case 文件在这一阶段的作用

V7 把评测输入固定成 JSON case 文件，核心字段包括：

- `case_id`
- `type`
- `input`
- `expected`

其中：

- `input` 描述实际输入，如 `paper_path`、`repo_path`、`log_path`
- `expected` 描述你希望系统满足的结果

这种设计很重要，因为它把“随手跑一次”变成了“可重复的标准样例”。

## expected 为什么要显式写出来

如果只有输入，没有期望结果，那评测就仍然是主观的。

这一章强调要把至少一部分标准提前写进 case，例如：

- `must_find_files`
- `must_include_modules`
- `must_not_claim`

这代表项目开始有了明确的验收意识：

- 哪些信息必须找出来
- 哪些模块必须提到
- 哪些内容绝对不能瞎说

## app/evaluation/run_eval.py 在做什么

[app/evaluation/run_eval.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/evaluation/run_eval.py:1) 是这一阶段最核心的评测入口。

它的整体职责是：

- 读取全部 case
- 对每个 case 跑一遍图
- 对可自动评测的类型做规则打分
- 最后生成统一的评测报告

它把“临时测试”升级成了“批量评测脚本”。

## run_eval.py 的执行链路

这份脚本主要由四部分组成：

- `load_cases()`
  - 从 `app/evaluation/cases/*.json` 读取全部评测样例

- `score_mapping_case()`
  - 对 `paper_code_mapping` 类型做基础规则打分

- `run_case()`
  - 针对单个 case 调用 `build_graph()` 跑整条流程
  - 用 `case_id` 作为 `thread_id`
  - 汇总输出文件和得分

- `main()`
  - 批量运行所有 case
  - 写出 `outputs/eval_report.json`

它的设计非常符合 MVP 阶段需求：先把评测闭环搭起来，再逐步增强精度。

## 当前自动打分的思路

当前 `score_mapping_case()` 使用的是一种很轻量的规则评测方式：

- 读取 `outputs/paper_code_mapping.json`
- 检查 `must_find_files` 是否出现在输出文本中
- 检查 `must_not_claim` 是否被错误声称
- 用召回减去幻觉惩罚得到 `score`

这套方法的特点是：

- 简单
- 易实现
- 可快速跑通

但它也很明显不是最终形态，因为它依赖字符串命中，而不是更强的语义评测。

## 为什么这里先做“半自动评测”而不是复杂打分器

这一章很强调一个现实思路：

- 不要一开始就追求复杂评测框架
- 先有固定 case、固定脚本、固定输出

这样做的价值是：

- 先把评测流程工程化
- 先能看到失败模式
- 先能给项目一个最小可比较基线

也就是说，V7 的目标不是“做最强评测器”，而是“让项目具备评测能力”。

## eval_report 的意义

V7 引入 `eval_report` 的核心意义，不是只为了导出一个文件，而是为了把项目效果沉淀成可以复盘的记录。

理想中的 `eval_report` 至少应该能回答：

- 跑了多少个 case
- 哪些 case 通过
- 哪些关键文件找到了
- 有没有出现明显幻觉
- 失败原因是什么
- 下一步该改哪里

这也是为什么教程里除了 `eval_report.json`，还建议后续做 `eval_report.md`，因为：

- JSON 更适合程序消费
- Markdown 更适合人展示和讲解

## docs/architecture.md 和 docs/demo_script.md 为什么重要

这一章不只是强调评测，也强调“能不能讲清楚项目”。

其中：

- `docs/architecture.md`
  - 用来解释整体工作流、State、工具边界

- `docs/demo_script.md`
  - 用来组织一次几分钟的稳定演示

它们的价值在于：

- 避免每次演示都临场发挥
- 避免只展示输出，不解释设计思路
- 帮助你把技术点讲成完整故事

## README 在这一阶段的角色

README 在这一章里被提升成一个非常关键的交付物。

教程里明确要求 README 至少包含：

- 项目背景
- 核心能力
- 架构图
- 快速开始
- 完整 demo
- 输出样例
- 评测方式
- 安全边界
- 已知限制
- 后续计划

这里最值得注意的是：

- 安全边界一定要写

因为项目既然引入了 shell 风险判断和 human review，面试或展示时别人很可能会追问：

- 你有没有让 Agent 直接执行命令
- 哪些动作会被拦截
- 哪些操作必须审批

README 正是解释这些边界的最好位置。

## 面试讲法为什么也被放进这一章

这一章最后给了“简历描述”和“3 分钟演示”的建议，其实是在提醒你：

- 工程项目不只是实现出来
- 还要能用几句话讲清楚它的价值、边界和亮点

也就是说，V7 本质上是在补“项目表达能力”。

## 本阶段的理想验收标准

这一阶段从目标上至少应该满足：

- 有固定 case 文件
- 有对应 expected 结果
- 有统一评测脚本
- 能生成评测报告
- 有 README、架构说明、demo script
- 能做一次几分钟的稳定演示

如果这些都具备，项目就不再只是“若干代码文件的集合”，而更像一个完整作品。

## 当前仓库已经落地的部分

结合当前项目状态，这一章已经有一些内容落地了：

- 已有评测脚本：
  - [app/evaluation/run_eval.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/evaluation/run_eval.py:1)

- 已有固定 case：
  - [case_003_mapping.json](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/evaluation/cases/case_003_mapping.json:1)

- 已有核心输出产物：
  - [paper_summary.json](/data/tianshaoqi24/agent/paper_reproduction_copilot/outputs/paper_summary.json:1)
  - [repo_map.json](/data/tianshaoqi24/agent/paper_reproduction_copilot/outputs/repo_map.json:1)
  - [paper_code_mapping.json](/data/tianshaoqi24/agent/paper_reproduction_copilot/outputs/paper_code_mapping.json:1)
  - [experiment_plan.json](/data/tianshaoqi24/agent/paper_reproduction_copilot/outputs/experiment_plan.json:1)

这说明 V7 的“评测闭环雏形”已经开始出现。

## 当前还没有完全补齐的部分

从当前仓库来看，这一章还有一些目标尚未完全落地：

- 目前 `cases/` 目录里只有一个 case，不是教程里提到的多 case 集合
- `must_include_modules` 已经写在 case 中，但当前打分代码还没有真正使用
- `eval_report.md` 还没有生成逻辑
- `docs/architecture.md` 目前还不存在
- `docs/demo_script.md` 目前还不存在
- [README.md](/data/tianshaoqi24/agent/paper_reproduction_copilot/README.md:1) 当前还是空文件

所以当前最准确的判断是：

- V7 的评测脚本骨架已经有了
- 但项目包装材料还没有完全补齐

## 本阶段容易遇到的问题及解决思路

### 1. 只有 case，没有 expected，最后还是主观评估

解决思路：

- 在 case 里显式写 `must_find`、`must_not_claim`、关键模块等约束

### 2. 只展示“成功 case”，不展示失败分析

这样会让项目看起来更像 demo，而不是工程化作品。

解决思路：

- 至少保留一个失败 case
- 把失败原因和改进方向写进评测报告

### 3. 评测脚本能跑，但输出不可复盘

如果只在终端里看一下结果，后面很难比较版本变化。

解决思路：

- 固定输出 `eval_report.json`
- 后续补 `eval_report.md`

### 4. README 太空，无法支撑展示

没有 README，项目就很难被快速理解。

解决思路：

- 补齐项目背景、能力、流程、评测、安全边界、限制和后续计划

### 5. 把“包装”误解成“写漂亮文案”

这一章真正要做的不是润色，而是把：

- case
- 评测
- 报告
- 演示
- 安全边界

组织成可验证、可讲述、可复盘的结构。

## 这一阶段最重要的理解

V7 表面上是在“写评测和 README”，但本质上是在完成项目的最后一公里：

- 从代码实现走向效果验证
- 从个人调试走向公开展示
- 从功能堆叠走向系统叙事

如果这一阶段做扎实，项目就不仅是“你自己知道它能做什么”，而是“别人也能看懂、跑通、验证并认可它的价值”。
