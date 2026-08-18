from __future__ import annotations

PAPER_SECTION_EXTRACTION_PROMPT_VERSION = "phase18-v1"


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

原文 blocks：
{section_text}
""".strip()
