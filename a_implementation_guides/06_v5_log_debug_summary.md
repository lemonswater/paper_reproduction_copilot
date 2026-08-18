# 06. V5 日志 Debug 学习总结

## 这一阶段的目标

这一章的重点，是让系统不仅能处理“正常复现流程”，也能在实验失败时对日志进行结构化分析。

输入不再只是论文和仓库，还加入了：

- `log_path`
- 训练日志
- 从日志中提取出的 traceback
- 前面阶段已经生成的 `repo_map`
- `experiment_plan`

输出则是：

```text
outputs/debug_report.json
outputs/debug_report.md
```

简单说，这一阶段解决的是“实验跑崩之后，系统能不能先帮我们做第一轮排查，而不是只停在报错现场”。

这里要特别区分两层：

- 目标层：希望系统能处理日志或 traceback 这类失败信息。
- 当前实现层：实际接口是通过 `log_path` 传入日志文件，再由节点内部抽取 traceback。

## 本阶段新增了什么能力

相较于前面的 V0-V4，V5 最大的变化是开始覆盖失败路径：

- 读取日志文件并截取有效报错上下文。
- 从长日志中优先提取 traceback。
- 先用启发式规则做第一轮错误分类。
- 再结合 `repo_map` 和 `experiment_plan` 让 LLM 生成结构化调试报告。
- 同时输出机器可读 JSON 和人工可读 Markdown。
- 为后续的人类审批、修复建议确认、失败恢复建立接口。

这意味着项目开始从“会分析、会规划”进一步走向“遇到问题也能辅助定位”。

## 为什么日志 Debug 这一步很重要

如果系统只能在理想路径上工作，那它更像一个演示脚本，而不是一个真正能辅助复现的 Agent。

实际复现实验时，最常见的情况反而是：

- 缺依赖
- 数据路径错误
- checkpoint 不存在
- 张量 shape 不匹配
- CUDA OOM
- 权限问题

所以 V5 的核心价值，不是让模型“解释一下报错”，而是让它开始具备失败场景下的诊断能力。

## app/tools/log_tools.py 在做什么

这一章新增的 [app/tools/log_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/log_tools.py:1) 负责日志侧的基础处理。

它拆成了三步：

- `read_log(path, max_chars=30000)`：读取日志尾部，避免把整份超长日志都送进模型。
- `extract_traceback(log_text)`：优先找最后一个 `Traceback`，找不到时退化为提取可疑报错行。
- `classify_error_heuristic(traceback)`：用关键词做第一轮粗分类。

这里最重要的工程思路是：不要一上来就把原始长日志整个扔给 LLM，而是先用规则方法做压缩和聚焦。

## 启发式分类为什么要先做一层

`classify_error_heuristic()` 的作用不是替代 LLM，而是先做一个低成本的错误初判。

当前主要覆盖这些类型：

- `dependency_missing`
- `data_or_path_error`
- `cuda_oom`
- `shape_mismatch`
- `permission_error`
- `unknown`

这样做有几个好处：

- 可以先给 prompt 一个初始判断，帮助模型聚焦。
- 即使 LLM 分析不稳定，系统也至少保留一个基础分类结果。
- 后面如果想做统计、路由或不同错误类型的专门处理，也更容易扩展。

## app/prompts/debug_prompt.py 的角色

[app/prompts/debug_prompt.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/prompts/debug_prompt.py:1) 的任务，是把“报错文本”升级成“有上下文的调试任务”。

它不仅提供 traceback，还把两类关键信息一起交给模型：

- `repo_map`
- `experiment_plan`

这样模型在分析时报错时，不只是看到一句 `RuntimeError`，还可以同时参考：

- 这个仓库里有哪些模块
- 计划里本来打算执行哪些步骤
- 哪些路径或脚本最可能相关

所以这个 prompt 的关键，不是让模型复述错误，而是要求它输出：

- 最可能原因
- 相关文件
- 排查顺序
- 修复建议
- 风险
- 还需要确认的问题

## app/schemas.py 中 DebugReport 的意义

这一阶段新增的 `DebugReport`，把调试结论固定成结构化对象。

核心字段包括：

- `error_type`
- `most_likely_causes`
- `related_files`
- `check_order`
- `suggested_fixes`
- `risks`
- `unresolved_questions`

这一步很重要，因为调试结果如果只是自然语言段落，后面很难继续做：

- 人工审批
- 修复方案确认
- 自动生成下一步操作建议
- 对不同报错类型做统计

所以 `DebugReport` 的价值，在于把“调试结论”也纳入统一的数据接口。

## app/nodes/log_debug_node.py 在做什么

[app/nodes/log_debug_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/log_debug_node.py:1) 是这一阶段的主节点。

它的大致流程是：

1. 从 `state` 中读取 `log_path`。
2. 用 `read_log()` 读取日志尾部。
3. 用 `extract_traceback()` 抽取关键报错片段。
4. 用 `classify_error_heuristic()` 做初步分类。
5. 构造 `structured_llm = llm.with_structured_output(DebugReport)`。
6. 把 `error_type`、`traceback`、`repo_map`、`experiment_plan` 填进 `DEBUG_PROMPT`。
7. 调用模型生成 `DebugReport`。
8. 把结果写入：
   - `debug_report.json`
   - `debug_report.md`
9. 把 `debug_report` 和新增输出文件路径回写到 `state`。

这说明 V5 的调试能力并不是独立脚本，而是已经被设计成图工作流中的一个正式节点。

## Markdown 报告为什么仍然重要

和前面几个阶段一样，这一章也同时保留了 JSON 与 Markdown 两种输出：

- JSON 适合程序继续处理。
- Markdown 适合人快速浏览和决策。

`_render_debug_markdown()` 的意义，就是把结构化调试结果整理成一份人能立刻阅读的报告，方便你快速看到：

- 报错属于哪一类
- 最可能的几个原因是什么
- 应该先查什么、后查什么
- 哪些修复动作有风险
- 还有哪些点没确认

## 这一阶段和 V4 Graph 的关系

V5 不是重新做一条独立链路，而是在 V4 的 LangGraph 基础上增加一个失败分析分支。

接入方式是：

- 在 `app/graph.py` 中注册 `log_debug` 节点。
- 在 `route_after_plan()` 里根据 `log_path` 是否存在决定是否进入 debug 分支。

逻辑上就是：

```text
experiment_plan
  -> 有 log_path：进入 log_debug
  -> 没有 log_path：直接结束
```

这一步的意义在于，图已经不再只是“顺着理想主链跑完”，而是开始根据状态条件进入不同分支。

## 本阶段验收标准

这一阶段完成后，至少应该满足：

- 给定一份真实日志文件，并通过 `log_path` 传入 state，可以成功生成 `debug_report.json` 和 `debug_report.md`。
- 报告里不仅有错误类型，还有原因分析。
- 能列出可能关联的 repo 文件，而不是只看最后一行异常文本。
- 能给出排查顺序，而不是无序罗列建议。
- 修复建议会附带风险提醒。
- 仍然不确定的信息会写进 `unresolved_questions`。

## 目前的状态：知识已经学完，但功能还没有验证

你这次的学习重点已经完成，但当前还有一个很重要的现实情况：

- 这套 V5 逻辑目前还没有做端到端测试。

这意味着我们现在总结的是“设计和实现思路已经清楚”，但还不能完全确认：

- `log_debug_node` 是否已经正确接入当前 graph
- `DebugReport` 的 schema 与 prompt 是否完全对齐
- 从真实日志中抽取 traceback 后，LLM 是否稳定返回可解析结果
- 输出文件是否会按预期落到 `outputs/`
- `state` 中的 `debug_report` 是否能被后续流程正确接住

所以这一阶段可以认为是：

- 理论和实现路径已经打通
- 但功能效果还需要实测验收

## 本阶段容易遇到的问题及解决思路

### 1. 只看最后一行错误，忽略 traceback 中间路径

这是最常见的调试误区。

很多关键线索其实藏在：

- 哪个文件抛错
- 哪个函数调用链触发
- 哪一层数据进入模型时出问题

解决思路：

- 优先抽取完整 traceback，而不是只保留最后一行异常名。
- 在 prompt 中强调“如果出现文件路径，要优先关联 repo 文件”。

### 2. 长日志过大，直接喂模型会稀释重点

训练日志通常非常长，里面包含大量正常输出。

解决思路：

- 只截取尾部 `max_chars`。
- 先用规则方法提取 traceback 或可疑错误行，再送进 LLM。

### 3. 模型容易只做“错误翻译”，不给排查顺序

如果 prompt 约束不够，模型很可能只会说“这是一个 CUDA OOM 错误”。

解决思路：

- 明确要求输出 `check_order`。
- 要求每条建议带有风险说明，而不是只报术语定义。

### 4. shape mismatch 和 OOM 的建议容易太空泛

比如模型可能只说：

- 检查 shape
- 减小 batch size

这种建议方向没错，但不够可执行。

解决思路：

- 在 prompt 或后续调试规则中引导它关注：
  - 数据维度
  - `forward()` 输入输出
  - loss 输入格式
  - batch size
  - `num_workers`
  - mixed precision
  - gradient accumulation

### 5. 调试建议和自动修改之间的边界要清楚

这一章强调的是“诊断与建议”，不是“自动替你改配置”。

解决思路：

- Prompt 中明确要求：如果需要改配置，只给 proposal，不直接修改。
- 把高风险动作保留给人确认。

## 这一阶段最重要的理解

V5 表面上是在“读取日志并分析错误”，但本质上是在给整个系统补齐失败路径能力。

它带来的关键变化是：

- 系统不再只会走成功链路
- 调试结果开始结构化
- 失败信息也能进入 state 和图工作流
- 后续人工确认、修复建议审批、失败恢复都更容易接入

如果这一阶段做好，项目会从“一个能分析论文的助手”，进一步变成“一个在实验失败时也能协助定位问题的复现 Copilot”。
