# Chat Provider 难度矩阵

这组 Case 使用真实 Chat Provider，统一带有 `difficulty-matrix-v1` 标签。每个难度的 3–5 个 Case 分别
收录在 `difficulty_easy.json`、`difficulty_medium.json` 和 `difficulty_hard.json` 三个强类型 Case Bundle
中。难度不是按问题长度划分，而是按模型必须同时处理的证据数量、对话历史、记忆压缩、冲突和安全边界划分。

| 难度 | Case | 主要测量目标 | Repetitions |
|---|---|---|---:|
| Easy | `chat_provider_easy_status_grounding` | 单一 Job Evidence 的状态与阶段问答 | 1 |
| Easy | `chat_provider_easy_artifact_fact_lookup` | 单一 Artifact 的事实抽取与 Citation | 1 |
| Easy | `chat_provider_easy_partial_metric_refusal` | 只有中间指标时拒绝编造最终指标 | 1 |
| Easy | `chat_provider_easy_intermediate_metric_qualification` | 自然询问进展时报告中间指标但不升级为最终结果 | 1 |
| Easy | `chat_provider_easy_compaction_threshold` | 4 轮历史刚好达到门槛，验证压缩必须真正触发 | 1 |
| Medium | `chat_provider_medium_multi_source_failure_synthesis` | Job、日志和配置三来源合并 | 2 |
| Medium | `chat_provider_medium_constraint_correction_memory` | 20 轮混合历史中的更正、过期草案、建议和噪声 | 2 |
| Medium | `chat_provider_medium_memory_partition` | Constraint、Decision、Open Question 分区 | 2 |
| Hard | `chat_provider_hard_conflicting_evidence_authority` | 当前状态与过期报告冲突、两轮问答 | 3 |
| Hard | `chat_provider_hard_long_history_memory_partition` | 单次运行连续生成 Memory v1→v2→v3，验证跨代更正和保真 | 3 |
| Hard | `chat_provider_hard_injection_citation_selection` | Prompt Injection、可信来源和 Citation 选择 | 3 |

建议先逐个 Case 运行，再运行同一难度的三个 Case，最后才运行完整 `chat_provider` Suite。真实 Provider
结果允许按 repetition 计算普通行为通过率，但 Safety 断言始终要求 100% 通过。
压缩场景把预置对话放在 Fixture 的 `seed_exchanges` 中；每个 exchange 会写入一条 User
和一条 Assistant Message。Case 同时断言 Memory 版本、`covered_through_sequence`、最少/最多压缩
调用次数、语义文本压缩率、语义分区、旧值排除、Citation、来源序号和 Hash 完整性。

```bash
python -m app.evaluation.run_eval run \
  --suite chat_provider \
  --case-id chat_provider_easy_status_grounding
```

完整 Suite 还包含原有的四个 Chat Provider Case。难度矩阵的 11 个 Case 最多产生 35 次回答模型调用和 14 次记忆
模型调用；压缩 Case 使用最小/最大调用次数双向断言，不允许“未触发压缩却通过”。
