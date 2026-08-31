MAPPING_ALIAS_PROMPT_VERSION = "phase23.6-v2"

MAPPING_ALIAS_RESOLUTION_PROMPT = """
你是论文方法名称的别名裁决器。输入已经由程序筛选为少量疑似别名组。

你的任务仅限判断：同一候选组中的名称是否指向同一个可映射的实现实体。

必须遵守：
1. decisions 中每个 group_id 必须来自输入，且每组最多返回一个 decision；
2. member_ids 必须列出本次裁决涉及的至少两个模块，只能来自该组 modules[].module_id；即使 should_merge=false 也不得省略，不得跨组移动模块；
3. 只有名称、功能描述和论文证据共同支持同一实现实体时才 should_merge=true；
4. 全称、论文简称、代码类名、snake_case 名称可以视为别名；
5. 主架构与内部组件不能仅因描述相关而合并；
6. encoder/decoder、input/output、teacher/student、普通卷积/转置卷积必须分开；
7. canonical_member_id 只能是 member_ids 中的一个 ID；合并时优先选择完整正式名称对应的 ID，不合并时可为 null；
8. 无法确认时 should_merge=false；禁止为了减少目标数量而猜测；
9. 只有证据充分时使用 confidence=high；medium/low 不会被程序自动合并；
10. reason 只写一句不超过80字的判定依据，不要复述输入；
11. 每个候选组都必须返回 decision，禁止输出别名列表、证据列表或其他字段。

论文上下文：
{paper_context}

疑似别名组：
{candidate_groups}
""".strip()
