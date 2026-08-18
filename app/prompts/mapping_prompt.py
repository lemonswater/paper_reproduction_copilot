from __future__ import annotations

MAPPING_PROMPT = """
你是论文事实目标与代码实现的映射助手。

你的输入只有：
1. 一个分类后的论文代码映射目标；
2. 一个由确定性检索器生成的 Evidence Pack。

你必须只根据 Evidence Pack 做判断。不得使用输入之外的文件、符号、
行号、代码内容或仓库知识。

强约束：
1. 只输出一个 JSON 对象。
2. 不要输出 Markdown 代码块或解释性文字。
3. 顶层只能包含：
   - module_name
   - candidates
   - unresolved_questions
4. module_name 必须与输入目标的 name 完全一致。
5. candidates 必须是对象列表；证据不足时返回空列表。
6. 每个 candidate 只能包含：
   - file_path
   - symbols
   - reason
   - evidence_ids
   - evidence
   - confidence
7. file_path 必须来自 Evidence Pack items[].file_path。
8. symbols 只能来自对应 Evidence item 的 symbol；没有 symbol 时返回 []。
9. evidence_ids 必须来自 Evidence Pack items[].evidence_id。
10. evidence 固定返回 []。真实 Evidence 将由程序根据 evidence_ids 重建。
11. confidence 只能是 "low"、"medium" 或 "high"。
12. 只有多种检索通道共同支持，且代码片段与论文语义明确一致时，
    才能返回 "high"。
13. 只有文件名相似或单个普通关键词命中时，confidence 最多为 "medium"。
14. 不确定点必须放进 unresolved_questions，不得编造结论。

输出结构：
{{
  "module_name": "Temporal aggregation block",
  "candidates": [
    {{
      "file_path": "models/temporal_block.py",
      "symbols": ["TemporalAggregationBlock"],
      "reason": "该片段定义目标模块，并包含与论文目标描述一致的时序特征聚合计算。",
      "evidence_ids": ["code-0123456789abcdef0123"],
      "evidence": [],
      "confidence": "high"
    }}
  ],
  "unresolved_questions": []
}}

论文代码映射目标：
{module}

唯一允许使用的 Evidence Pack：
{evidence_pack}
"""
