# 01. V0 论文结构化阅读学习总结

## 这一阶段的目标

这一章的重点是把“读论文”这件事，从人工阅读变成一个可运行的结构化流程：

- 输入论文文件路径。
- 自动读取 PDF 或文本内容。
- 切分长文本，避免一次塞给模型过多内容。
- 让模型输出符合 schema 的结构化结果，而不是随意的自然语言摘要。
- 把结果落盘为后续阶段可复用的 JSON 文件。

简单说，这一阶段解决的是“如何先把论文读成机器可消费的数据结构”。

## 本阶段新增了什么能力

相较于 00 阶段的项目地基，V0 真正开始接触论文内容本身，新增了 4 类能力：

- 论文文件读取：支持从 `.pdf`、`.md`、`.txt` 中读取内容。
- 长文本切块：把整篇论文切成多个 chunk，方便后续送入模型。
- 结构化抽取：让模型围绕 `PaperSummary` 生成复现导向的信息。
- 结果输出：把论文摘要和方法模块分别写入 `outputs/`。

这意味着项目从“框架可运行”迈向了“第一条有业务价值的最小工作流”。

## 本阶段新增文件的分工

这一章新增了 4 个核心文件：

- `app/tools/paper_tools.py`：负责论文读取和文本切块。
- `app/prompts/paper_prompt.py`：定义论文摘要抽取的提示词模板。
- `app/nodes/paper_reader_node.py`：把论文路径转成 `paper_text_chunks`。
- `app/nodes/method_extractor_node.py`：调用 LLM，把论文 chunk 合并后抽成 `PaperSummary`。

这几个文件一起构成了一条很清晰的 V0 链路：

- 读文件
- 切 chunk
- 拼接可控长度的论文文本
- 调模型做结构化抽取
- 保存输出

## 论文读取工具的作用

`app/tools/paper_tools.py` 是这个阶段的基础工具层，主要负责三件事：

- `read_pdf()`：逐页读取 PDF，并给每页文本加上页码标记。
- `read_text_file()`：读取普通文本文件。
- `read_paper()`：根据后缀决定调用哪种读取方式。

其中一个很实用的细节是：PDF 内容在读取后会变成类似 `[page 3]` 这样的文本块。这样后续即使没有精准引用系统，也能在 prompt 或证据里保留基本页码语境。

## 为什么要切 chunk

整篇论文往往很长，直接一次塞给模型会有几个问题：

- 容易超过上下文长度限制。
- 成本更高。
- 模型更容易丢掉重点信息。
- 调试时很难判断到底是内容太长，还是 prompt 或 schema 有问题。

所以 `split_text()` 会把文本切成固定大小的 chunk，并保留一定 overlap。

这样做的价值是：

- 后续可以逐块处理或按需合并。
- 即使当前阶段先只处理前一部分文本，整体流程也已经具备扩展性。
- 为后面做检索、映射和更细粒度抽取打下基础。

## Node 的职责划分

V0 的流程虽然短，但节点职责已经很清楚：

- `paper_reader_node()`：只关心输入文件，输出切好的文本块。
- `method_extractor_node()`：只关心从文本块中抽取结构化摘要。

这种拆法有两个好处：

- 读取逻辑和 LLM 抽取逻辑分开，后续更容易调试。
- 即使以后换 PDF 解析方式，或换摘要抽取 prompt，也不会把整条链缠在一起。

## 结构化抽取是本阶段的核心

这一阶段最关键的不是“让模型总结论文”，而是“让模型按 schema 输出”。

代码里使用的是：

- `get_chat_model(temperature=0)`：构造聊天模型。
- `llm.with_structured_output(PaperSummary)`：要求模型输出匹配 `PaperSummary` 的结构。

这里的核心思想是：

- prompt 提供任务语义。
- `PaperSummary` 提供输出约束。
- LangChain 负责把模型返回结果解析并交给 Pydantic 校验。

如果模型返回字段缺失、字段名不对、或类型不匹配，就会在这里暴露出来，而不是悄悄把脏数据继续传到后面阶段。

## Prompt 在这一阶段扮演的角色

`PAPER_SUMMARY_PROMPT` 并不是普通摘要模板，而是“抽取规约”。

它至少要告诉模型这些事：

- 目标不是写读后感，而是提取复现需要的信息。
- 论文没明确写的设置不能猜。
- 不确定的信息要放进 `unresolved_questions`。
- `method_modules` 里的模块要带 `possible_keywords`，为后续代码搜索服务。

换句话说，prompt 不是只负责“让回答看起来正确”，而是负责把模型引导到后续工作流真正需要的数据形状上。

## 结果输出与落盘

这一阶段最终会生成两个输出文件：

- `outputs/paper_summary.json`
- `outputs/method_modules.json`

这里的设计很合理：

- `paper_summary.json` 保存完整结构化摘要。
- `method_modules.json` 单独拆出方法模块，方便后续 V2 做论文到代码的映射。

这体现了一个工程化思路：不是只求“能看”，而是从一开始就考虑后续阶段如何复用这些结果。

## CLI 如何把整条链串起来

在 `app/main.py` 里新增的 `read-paper` 命令，是本阶段的验收入口：

- 先构造最小 `state`
- 调 `paper_reader_node()`
- 再调 `method_extractor_node()`
- 最后打印输出文件列表

这让 V0 阶段不只是若干函数，而是一条可以端到端演示的工作流。

命令形式是：

```bash
python -m app.main read-paper data/example_paper.pdf
```

## 本阶段验收标准

这一阶段完成后，至少应该满足：

- 可以读取 PDF、Markdown 或文本形式的论文。
- 可以把论文内容切成多个 chunk。
- 可以把部分论文文本送入模型进行结构化抽取。
- 可以生成 `paper_summary.json` 和 `method_modules.json`。
- 结果里能够回答研究问题、核心方法模块、已知训练设定和未解决问题。

如果这些都跑通，说明项目已经具备了“把论文读成结构化数据”的第一步能力。

## 关键收获

这一章最值得记住的，不是某个 API，而是几条方法论：

- 论文阅读任务要尽早结构化，不能只停留在自然语言总结。
- Prompt 只写“帮我总结一下”远远不够，必须围绕后续任务设计字段。
- Schema 是约束输出质量的重要手段，不只是类型注解。
- 长文本处理必须从一开始就考虑 chunk，而不是等上下文爆掉再补救。
- 中间结果要落盘，方便调试、复查和后续阶段复用。

## 本阶段遇到的问题及对应解决方案

这一阶段真正的难点，不在“能不能调到模型”，而在“怎么让返回结果稳定符合 schema”。这次实践里主要遇到了几类问题。

### 1. `PaperSummary` 校验失败

典型报错是：

- `research_problem` 缺失
- `core_idea` 缺失
- `datasets` 中的元素不是字符串，而是对象

根因是：模型返回的 JSON 结构和 `app/schemas.py` 里的 `PaperSummary` 不一致。

解决思路：

- 先明确问题不在 PDF 读取，而在结构化抽取阶段。
- 对照 schema 检查必填字段和字段类型。
- 强化 prompt，把字段名、字段类型、禁止新增字段、示例结构都写清楚。
- 明确要求只输出 JSON，不输出解释，不输出 Markdown 代码块。

### 2. 模型“内容大致正确”，但字段形状不对

实践中很容易出现这种情况：

- `title`、`research_problem`、`core_idea` 基本正确
- 但 `method_modules` 用了 `module_name`
- `unresolved_questions` 返回成对象数组，而不是 `list[str]`

这说明“语义答对了”不等于“结构答对了”。

解决思路：

- 不能只看 plain 文本回答是否像样。
- 必须对照 schema 一项项看字段名和字段类型。
- Prompt 里要显式禁止 `paper_info`、`module_name`、`components` 这类额外结构。

### 3. 在 prompt 中直接写 JSON 示例，触发 `.format()` 报错

当 prompt 模板里直接写：

```python
{
    "title": "..."
}
```

再执行：

```python
PAPER_SUMMARY_PROMPT.format(paper_text=paper_text)
```

就可能触发 `KeyError`，因为 `str.format()` 会把 JSON 里的 `{}` 当成占位符解析。

解决方案：

- Prompt 保持普通字符串模板。
- JSON 示例里的字面量大括号写成 `{{` 和 `}}`。
- 只保留真正要替换的 `{paper_text}`。

### 4. 把 prompt 改成 `f"""..."""` 后出现 `NameError`

如果把：

```python
PAPER_SUMMARY_PROMPT = """
...
{paper_text}
"""
```

改成：

```python
PAPER_SUMMARY_PROMPT = f"""
...
{paper_text}
"""
```

会在导入模块时直接报 `NameError: name 'paper_text' is not defined`。

根因是：f-string 会在定义字符串时立刻求值，而 `paper_text` 只在后续节点函数里才存在。

解决方案：

- Prompt 模板不要改成 f-string。
- 保持普通字符串，然后在运行时再调用 `.format(paper_text=paper_text)`。

### 5. 想看模型原始返回，但调试时只看到异常

默认 `with_structured_output(PaperSummary)` 更关注解析后的结果，结构不匹配时容易直接抛出异常，不方便观察模型原始输出。

解决方案：

- 使用 `include_raw=True`，让返回值里同时包含：
  - `raw`
  - `parsed`
  - `parsing_error`
- 这样可以区分：
  - 模型到底原始返回了什么
  - 解析后的结构长什么样
  - 失败究竟发生在解析前还是校验阶段

### 6. 在 VS Code Debug Console 里直接执行 `invoke(...)` 超时

在调试器里执行：

```python
llm.with_structured_output(...).invoke(prompt)
```

本质上是在断点状态下触发一次真实的远程模型调用，3 秒内没返回时，调试器就会报 evaluation timeout 警告。

解决思路：

- 这不一定是业务逻辑错了，很多时候只是调用慢。
- Debug Console 更适合查看变量，不适合频繁临时发远程请求。
- 更稳的做法是把 `prompt`、`result` 先写成中间变量，再在断点处查看它们。

## 本阶段最重要的理解

V0 看起来只是“读论文 + 调模型”，但真正要掌握的是：

- 论文结构化阅读不是摘要任务，而是信息抽取任务。
- 模型输出要为后续阶段服务，所以 schema 和 prompt 必须一起设计。
- 只看自然语言回答很容易误判，必须同时看结构是否可验证、可落盘、可复用。

如果这一阶段学扎实，后面的仓库扫描、代码映射和实验计划都会轻松很多，因为它们都依赖这里产出的 `PaperSummary` 和 `method_modules`。

## 局限性
- 文档划分只能通过固定chunk length和 overlap 来进行划分，无法通过语义相似性等进行划分
