# Agent Evaluation Report

## Summary

- Eval ID：`agent-eval-provider-5f527f92fe`
- Suite：`provider`
- Passed：`False`
- Overall score：`0.5964`
- Cases：`1/4`
- Revision：`239441e26eb044e38a3a5a2ffa131464c66bda9d`
- Dirty worktree：`True`

## Category Scores

| Category | Score |
|---|---:|
| efficiency | 1.0000 |
| evidence | 0.5000 |
| quality | 0.0417 |
| schema | 0.4722 |

## Problem Coverage

- Problem 2：`provider_pstnet_mapping`, `provider_p4transformer_mapping`
- Problem 7：`provider_pstnet_mapping`, `provider_p4transformer_mapping`
- Problem 8：`provider_pstnet_mapping`, `provider_p4transformer_mapping`

## Case Details

### provider_pstnet_mapping

- Passed：`False`
- Score：`0.3333`
- Runner：`live_graph`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-provider-5f527f92fe-20260818-075759-1ca0a8cf/traces/eval_cases/provider_pstnet_mapping/observation.json`

#### schema

- Passed：`False`
- Score：`0.3333`
- `FAIL` `SCHEMA_REQUIRED:PaperSummary`：必须观察到指定 Schema
  - expected：`"PaperSummary"`
  - actual：`[]`
- `FAIL` `SCHEMA_REQUIRED:ModuleMapping`：必须观察到指定 Schema
  - expected：`"ModuleMapping"`
  - actual：`[]`
- `FAIL` `SCHEMA_REQUIRED:ExperimentPlan`：必须观察到指定 Schema
  - expected：`"ExperimentPlan"`
  - actual：`[]`
- `FAIL` `SCHEMA_SUCCESS_RATE`：Schema 成功率达到下限
  - expected：`1.0`
  - actual：`0.0`
- `PASS` `SCHEMA_FALLBACK_COUNT`：fallback 不超过预算
  - expected：`1`
  - actual：`0`
- `PASS` `SCHEMA_RETRY_COUNT`：重试不超过预算
  - expected：`3`
  - actual：`0`

#### evidence

- Passed：`False`
- Score：`0.0000`
- `FAIL` `EVIDENCE_PATH:models/model.py`：必须存在来源路径
  - expected：`"models/model.py"`
  - actual：`[]`

#### quality

- Passed：`False`
- Score：`0.0000`
- `FAIL` `QUALITY_FILE:models/model.py`：必须找到文件
  - expected：`"models/model.py"`
  - actual：`false`

#### efficiency

- Passed：`True`
- Score：`1.0000`
- `PASS` `EFFICIENCY_LLM_CALLS`：效率指标不超过预算
  - expected：`12`
  - actual：`0`
- `PASS` `EFFICIENCY_HUMAN`：效率指标不超过预算
  - expected：`1`
  - actual：`0`

### provider_pstnet_section_understanding

- Passed：`False`
- Score：`0.7188`
- Runner：`live_graph`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-provider-5f527f92fe-20260818-075759-1ca0a8cf/traces/eval_cases/provider_pstnet_section_understanding/observation.json`

#### schema

- Passed：`False`
- Score：`0.7500`
- `PASS` `SCHEMA_REQUIRED:SectionExtractionDraft`：必须观察到指定 Schema
  - expected：`"SectionExtractionDraft"`
  - actual：`["SectionExtractionDraft"]`
- `PASS` `SCHEMA_SUCCESS_RATE`：Schema 成功率达到下限
  - expected：`0.9`
  - actual：`0.9166666666666666`
- `FAIL` `SCHEMA_FALLBACK_COUNT`：fallback 不超过预算
  - expected：`0`
  - actual：`1`
- `PASS` `SCHEMA_RETRY_COUNT`：重试不超过预算
  - expected：`6`
  - actual：`0`

#### evidence

- Passed：`True`
- Score：`1.0000`
- `PASS` `ARTIFACT_REQUIRED:analysis/paper_document.json`：必须生成 Artifact
  - expected：`true`
  - actual：`true`
- `PASS` `ARTIFACT_HASH:analysis/paper_document.json`：hash 必须有效
  - expected：`"current"`
  - actual：`"current"`
- `PASS` `ARTIFACT_REQUIRED:analysis/paper_blocks.json`：必须生成 Artifact
  - expected：`true`
  - actual：`true`
- `PASS` `ARTIFACT_HASH:analysis/paper_blocks.json`：hash 必须有效
  - expected：`"current"`
  - actual：`"current"`
- `PASS` `ARTIFACT_REQUIRED:analysis/paper_sections.json`：必须生成 Artifact
  - expected：`true`
  - actual：`true`
- `PASS` `ARTIFACT_HASH:analysis/paper_sections.json`：hash 必须有效
  - expected：`"current"`
  - actual：`"current"`
- `PASS` `ARTIFACT_REQUIRED:analysis/paper_parse_report.json`：必须生成 Artifact
  - expected：`true`
  - actual：`true`
- `PASS` `ARTIFACT_HASH:analysis/paper_parse_report.json`：hash 必须有效
  - expected：`"current"`
  - actual：`"current"`
- `PASS` `ARTIFACT_REQUIRED:analysis/paper_fact_index.json`：必须生成 Artifact
  - expected：`true`
  - actual：`true`
- `PASS` `ARTIFACT_HASH:analysis/paper_fact_index.json`：hash 必须有效
  - expected：`"current"`
  - actual：`"current"`
- `PASS` `ARTIFACT_REQUIRED:analysis/paper_conflicts.json`：必须生成 Artifact
  - expected：`true`
  - actual：`true`
- `PASS` `ARTIFACT_HASH:analysis/paper_conflicts.json`：hash 必须有效
  - expected：`"current"`
  - actual：`"current"`
- `PASS` `EVIDENCE_PAPER_PROVENANCE_RATIO`：论文 Evidence provenance 完整度达到下限
  - expected：`0.95`
  - actual：`1.0`

#### quality

- Passed：`False`
- Score：`0.1250`
- `FAIL` `QUALITY_PAPER_SETTING:training epochs`：必须抽取指定实验设置
  - expected：`"training epochs"`
  - actual：`["MSR-Action3D片段长度", "MSR-Action3D时间核大小l=1", "MSR-Action3D时间核大小l≥3"]`
- `FAIL` `QUALITY_PAPER_SETTING:optimizer`：必须抽取指定实验设置
  - expected：`"optimizer"`
  - actual：`["MSR-Action3D片段长度", "MSR-Action3D时间核大小l=1", "MSR-Action3D时间核大小l≥3"]`
- `FAIL` `QUALITY_PAPER_SETTING:initial learning rate`：必须抽取指定实验设置
  - expected：`"initial learning rate"`
  - actual：`["MSR-Action3D片段长度", "MSR-Action3D时间核大小l=1", "MSR-Action3D时间核大小l≥3"]`
- `FAIL` `QUALITY_PAPER_SETTING:learning rate decay epochs`：必须抽取指定实验设置
  - expected：`"learning rate decay epochs"`
  - actual：`["MSR-Action3D片段长度", "MSR-Action3D时间核大小l=1", "MSR-Action3D时间核大小l≥3"]`
- `FAIL` `QUALITY_PAPER_SETTING:MSR-Action3D batch size`：必须抽取指定实验设置
  - expected：`"MSR-Action3D batch size"`
  - actual：`["MSR-Action3D片段长度", "MSR-Action3D时间核大小l=1", "MSR-Action3D时间核大小l≥3"]`
- `FAIL` `QUALITY_PAPER_SETTING:NTU batch size`：必须抽取指定实验设置
  - expected：`"NTU batch size"`
  - actual：`["MSR-Action3D片段长度", "MSR-Action3D时间核大小l=1", "MSR-Action3D时间核大小l≥3"]`
- `FAIL` `QUALITY_PAPER_SETTING:Synthia batch size`：必须抽取指定实验设置
  - expected：`"Synthia batch size"`
  - actual：`["MSR-Action3D片段长度", "MSR-Action3D时间核大小l=1", "MSR-Action3D时间核大小l≥3"]`
- `PASS` `QUALITY_PAPER_CONFLICTS`：论文事实冲突不超过阈值
  - expected：`0`
  - actual：`0`

#### efficiency

- Passed：`True`
- Score：`1.0000`
- `PASS` `EFFICIENCY_LLM_CALLS`：效率指标不超过预算
  - expected：`30`
  - actual：`12`
- `PASS` `EFFICIENCY_HUMAN`：效率指标不超过预算
  - expected：`1`
  - actual：`0`

### provider_p4transformer_mapping

- Passed：`False`
- Score：`0.3333`
- Runner：`live_graph`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-provider-5f527f92fe-20260818-075759-1ca0a8cf/traces/eval_cases/provider_p4transformer_mapping/observation.json`

#### schema

- Passed：`False`
- Score：`0.3333`
- `FAIL` `SCHEMA_REQUIRED:PaperSummary`：必须观察到指定 Schema
  - expected：`"PaperSummary"`
  - actual：`["SectionExtractionDraft"]`
- `FAIL` `SCHEMA_REQUIRED:ModuleMapping`：必须观察到指定 Schema
  - expected：`"ModuleMapping"`
  - actual：`["SectionExtractionDraft"]`
- `FAIL` `SCHEMA_REQUIRED:ExperimentPlan`：必须观察到指定 Schema
  - expected：`"ExperimentPlan"`
  - actual：`["SectionExtractionDraft"]`
- `FAIL` `SCHEMA_SUCCESS_RATE`：Schema 成功率达到下限
  - expected：`1.0`
  - actual：`0.9166666666666666`
- `PASS` `SCHEMA_FALLBACK_COUNT`：fallback 不超过预算
  - expected：`1`
  - actual：`1`
- `PASS` `SCHEMA_RETRY_COUNT`：重试不超过预算
  - expected：`3`
  - actual：`0`

#### evidence

- Passed：`False`
- Score：`0.0000`
- `FAIL` `EVIDENCE_PATH:models/model.py`：必须存在来源路径
  - expected：`"models/model.py"`
  - actual：`["/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf", "/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf", "/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf", "/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf", "/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf", "paper-8624859bf40594eb", "paper-8624859bf40594eb", "paper-8624859bf40594eb", "paper-8624859bf40594eb", "paper-8624859bf40594eb", "paper-8624859bf40594eb", "/data/tianshaoqi24/agent/paper_r...<truncated>`

#### quality

- Passed：`False`
- Score：`0.0000`
- `FAIL` `QUALITY_FILE:models/model.py`：必须找到文件
  - expected：`"models/model.py"`
  - actual：`false`

#### efficiency

- Passed：`True`
- Score：`1.0000`
- `PASS` `EFFICIENCY_LLM_CALLS`：效率指标不超过预算
  - expected：`12`
  - actual：`12`
- `PASS` `EFFICIENCY_HUMAN`：效率指标不超过预算
  - expected：`1`
  - actual：`0`

### provider_retrieval_obfuscated_semantics

- Passed：`True`
- Score：`1.0000`
- Runner：`semantic_code_retrieval`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-provider-5f527f92fe-20260818-075759-1ca0a8cf/traces/eval_cases/provider_retrieval_obfuscated_semantics/observation.json`

#### evidence

- Passed：`True`
- Score：`1.0000`
- `PASS` `EVIDENCE_RETRIEVAL_PATH:obfuscated/operator_core.py`：目标文件必须进入检索 top-k
  - expected：`"obfuscated/operator_core.py"`
  - actual：`["obfuscated/operator_core.py", "modules/pst_convolutions.py", "models/sequence_classification.py", "notes/pstconv_overview.md", "train_msr.py", "obfuscated/image_filter.py", "datasets/msr.py"]`
- `PASS` `EVIDENCE_RETRIEVAL_RANK:obfuscated/operator_core.py`：目标文件排名必须达到上限
  - expected：`2`
  - actual：`1`
- `PASS` `EVIDENCE_RETRIEVAL_CHANNEL:dense`：必须观察到指定检索通道
  - expected：`"dense"`
  - actual：`["dense"]`
- `PASS` `EVIDENCE_RETRIEVAL_PROVENANCE_RATIO`：Code Evidence provenance 达到下限
  - expected：`1.0`
  - actual：`1.0`

#### efficiency

- Passed：`True`
- Score：`1.0000`
- `PASS` `EFFICIENCY_DURATION`：效率指标不超过预算
  - expected：`120000.0`
  - actual：`246.1782320169732`
- `PASS` `EFFICIENCY_LLM_CALLS`：效率指标不超过预算
  - expected：`0`
  - actual：`0`
- `PASS` `EFFICIENCY_EMBEDDING_DOCUMENT_CALLS`：效率指标不超过预算
  - expected：`10`
  - actual：`0`
- `PASS` `EFFICIENCY_EMBEDDING_QUERY_CALLS`：效率指标不超过预算
  - expected：`1`
  - actual：`0`
