from __future__ import annotations

PAPER_SECTION_EXTRACTION_PROMPT_VERSION = "phase18-v2"


PAPER_SECTION_EXTRACTION_PROMPT = """
你是一个论文复现信息抽取助手。当前输入只包含论文中的一个章节片段，
请从该片段中提取有原文证据支持的复现事实。

章节元数据：
- section_id: {section_id}
- chunk_id: {chunk_id}
- 章节标题: {section_title}
- 章节类型: {section_kind}
- 页码范围: {page_start}-{page_end}

每个原文 block 的格式如下：
[block_id][page N] 原始论文文本

严格要求：
1. 只能提取下方原文 block 明确支持的事实。
2. 每条事实都必须引用当前章节片段中实际出现的一个或多个 block_id。
3. 不得编造页码、哈希、section_id、block_id、数据集、指标、超参数或实验结果。
4. 原文没有提供某个值时，应省略该事实，不得根据常识或其他论文进行猜测。
5. 不同数据集、模型变体或实验使用不同设置时，必须分别保留，不能合并或相互覆盖。
6. 实验设置的名称必须包含必要的数据集、模型变体或实验作用域；
   例如应写成“某数据集 batch size”，不能只写“batch size”。
7. 不得把 Related Work 中描述的其他论文方法当作本文的方法或实验设置。
8. 表格标题不能作为表格单元格内容的证据。如果表格单元格缺失、解析失败或含义不明确，
   必须将问题写入 table_claims_unresolved，不得猜测表格结果。
9. 输出中的 section_id 和 chunk_id 必须与上方章节元数据完全一致。
10. 只返回调用方要求的结构化结果，不要添加 Markdown 代码围栏或 schema 之外的说明文字。
11. summary 最多 120 个中文字符或 240 个英文字符；每条事实只写一句短摘要。
12. method_modules、datasets、metrics、experiment_settings 各最多保留 8 项；
    其余事实列表各最多 5 项，优先保留与论文方法和复现实验直接相关的事实。
13. EvidenceDraft.summary 只概括证据作用，不要重复整段论文原文。

原文 blocks：
{section_text}
""".strip()


PAPER_SECTION_TRUNCATION_RETRY_PROMPT = """
上一轮对本章节的抽取在 JSON 对象完成前被截断，未通过解析。

请重新生成完整结果，并遵守以下额外限制：
1. 使用紧凑单行 JSON，不要缩进、换行、解释或 Markdown。
2. 所有必需顶层字段都必须存在，所有字符串必须闭合。
3. 每个列表只保留完成任务所需的最少项目；没有可靠内容时返回 []。
4. 字符串使用简短摘要，不要重复论文原文或 schema 说明。
5. 必须在输出预算内返回完整、可被 json.loads() 解析的 JSON 对象。
""".strip()


PAPER_SECTION_FAILURE_RETRY_PROMPT = """
上一轮对本章节的结构化抽取没有通过校验。

请重新审视上方原文 blocks，只返回符合 schema 的 JSON 对象：
1. 使用紧凑单行 JSON，不要缩进、换行、解释或 Markdown。
2. 所有必需顶层字段都必须存在，所有字符串必须闭合。
3. 每个列表只保留原文明确支持的条目；没有可靠内容时返回 []。
4. 只修复结构，不要新增没有原文证据支持的事实。
""".strip()


PAPER_SECTION_EMPTY_RESULT_RETRY_PROMPT = """
上一轮返回了结构合法但内容完全为空的结果，不能证明已经阅读当前章节。

请重新检查原文 blocks，并至少完成以下一项：
1. 若存在方法、数据集、指标或实验设置，提取最关键的 1-6 项并引用 block_id；
2. 若本片段确实只有标题、页眉或无意义残片，在 summary 中简要说明原因；
3. 不得通过空 summary 加全部空列表来结束抽取。

保持紧凑 JSON，只返回符合 schema 的对象。
""".strip()


PAPER_SECTION_METHOD_EMPTY_RETRY_PROMPT = """
上一轮对本方法章节的抽取没有识别出任何方法模块（method_modules 为空）。

请重新阅读上方原文片段，专门针对方法模块进行识别：
1. 本节是否定义了新的网络结构、子模块、组件、算子、归一化/注意力机制、
   损失函数或训练技巧？
2. 如果有，请为每个模块填写 MethodModuleDraft：
   - name：论文中使用的名称（如 PST-Conv、PointNet++ backbone）；
   - description：一句设计意图或作用，必须引用本节出现的 block_id；
   - possible_keywords：可能的代码实现关键词（如 conv1d、separable、mlp）；
   - evidence：引用支撑该模块的 block_id。
3. 如果本节确实没有定义新的可映射模块，不要编造，直接把
   "本节未定义新的可映射方法模块，原因：..." 写入 summary 或
   unresolved_questions。

只返回符合 schema 的 JSON 对象。
""".strip()
