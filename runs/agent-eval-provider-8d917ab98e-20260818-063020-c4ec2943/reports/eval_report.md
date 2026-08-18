# Agent Evaluation Report

## Summary

- Eval ID：`agent-eval-provider-8d917ab98e`
- Suite：`provider`
- Passed：`False`
- Overall score：`0.5182`
- Cases：`1/4`
- Revision：`239441e26eb044e38a3a5a2ffa131464c66bda9d`
- Dirty worktree：`True`

## Category Scores

| Category | Score |
|---|---:|
| efficiency | 1.0000 |
| evidence | 0.2500 |
| quality | 0.0417 |
| schema | 0.3889 |

## Problem Coverage

- Problem 2：`provider_pstnet_mapping`, `provider_p4transformer_mapping`
- Problem 7：`provider_pstnet_mapping`, `provider_p4transformer_mapping`
- Problem 8：`provider_pstnet_mapping`, `provider_p4transformer_mapping`

## Case Details

### provider_pstnet_mapping

- Passed：`False`
- Score：`0.3333`
- Runner：`live_graph`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-provider-8d917ab98e-20260818-063020-c4ec2943/traces/eval_cases/provider_pstnet_mapping/observation.json`

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
- Score：`0.4062`
- Runner：`live_graph`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-provider-8d917ab98e-20260818-063020-c4ec2943/traces/eval_cases/provider_pstnet_section_understanding/observation.json`

#### schema

- Passed：`False`
- Score：`0.5000`
- `FAIL` `SCHEMA_REQUIRED:SectionExtractionDraft`：必须观察到指定 Schema
  - expected：`"SectionExtractionDraft"`
  - actual：`[]`
- `FAIL` `SCHEMA_SUCCESS_RATE`：Schema 成功率达到下限
  - expected：`0.9`
  - actual：`0.0`
- `PASS` `SCHEMA_FALLBACK_COUNT`：fallback 不超过预算
  - expected：`0`
  - actual：`0`
- `PASS` `SCHEMA_RETRY_COUNT`：重试不超过预算
  - expected：`6`
  - actual：`0`

#### evidence

- Passed：`False`
- Score：`0.0000`
- `FAIL` `ARTIFACT_REQUIRED:analysis/paper_document.json`：必须生成 Artifact
  - expected：`true`
  - actual：`false`
- `FAIL` `ARTIFACT_REQUIRED:analysis/paper_blocks.json`：必须生成 Artifact
  - expected：`true`
  - actual：`false`
- `FAIL` `ARTIFACT_REQUIRED:analysis/paper_sections.json`：必须生成 Artifact
  - expected：`true`
  - actual：`false`
- `FAIL` `ARTIFACT_REQUIRED:analysis/paper_parse_report.json`：必须生成 Artifact
  - expected：`true`
  - actual：`false`
- `FAIL` `ARTIFACT_REQUIRED:analysis/paper_fact_index.json`：必须生成 Artifact
  - expected：`true`
  - actual：`false`
- `FAIL` `ARTIFACT_REQUIRED:analysis/paper_conflicts.json`：必须生成 Artifact
  - expected：`true`
  - actual：`false`
- `FAIL` `EVIDENCE_PAPER_PROVENANCE_RATIO`：论文 Evidence provenance 完整度达到下限
  - expected：`0.95`
  - actual：`0.0`

#### quality

- Passed：`False`
- Score：`0.1250`
- `FAIL` `QUALITY_PAPER_SETTING:training epochs`：必须抽取指定实验设置
  - expected：`"training epochs"`
  - actual：`[]`
- `FAIL` `QUALITY_PAPER_SETTING:optimizer`：必须抽取指定实验设置
  - expected：`"optimizer"`
  - actual：`[]`
- `FAIL` `QUALITY_PAPER_SETTING:initial learning rate`：必须抽取指定实验设置
  - expected：`"initial learning rate"`
  - actual：`[]`
- `FAIL` `QUALITY_PAPER_SETTING:learning rate decay epochs`：必须抽取指定实验设置
  - expected：`"learning rate decay epochs"`
  - actual：`[]`
- `FAIL` `QUALITY_PAPER_SETTING:MSR-Action3D batch size`：必须抽取指定实验设置
  - expected：`"MSR-Action3D batch size"`
  - actual：`[]`
- `FAIL` `QUALITY_PAPER_SETTING:NTU batch size`：必须抽取指定实验设置
  - expected：`"NTU batch size"`
  - actual：`[]`
- `FAIL` `QUALITY_PAPER_SETTING:Synthia batch size`：必须抽取指定实验设置
  - expected：`"Synthia batch size"`
  - actual：`[]`
- `PASS` `QUALITY_PAPER_CONFLICTS`：论文事实冲突不超过阈值
  - expected：`0`
  - actual：`0`

#### efficiency

- Passed：`True`
- Score：`1.0000`
- `PASS` `EFFICIENCY_LLM_CALLS`：效率指标不超过预算
  - expected：`30`
  - actual：`0`
- `PASS` `EFFICIENCY_HUMAN`：效率指标不超过预算
  - expected：`1`
  - actual：`0`

### provider_p4transformer_mapping

- Passed：`False`
- Score：`0.3333`
- Runner：`live_graph`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-provider-8d917ab98e-20260818-063020-c4ec2943/traces/eval_cases/provider_p4transformer_mapping/observation.json`

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

### provider_retrieval_obfuscated_semantics

- Passed：`True`
- Score：`1.0000`
- Runner：`semantic_code_retrieval`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-provider-8d917ab98e-20260818-063020-c4ec2943/traces/eval_cases/provider_retrieval_obfuscated_semantics/observation.json`

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
  - actual：`482.10261506028473`
- `PASS` `EFFICIENCY_LLM_CALLS`：效率指标不超过预算
  - expected：`0`
  - actual：`0`
- `PASS` `EFFICIENCY_EMBEDDING_DOCUMENT_CALLS`：效率指标不超过预算
  - expected：`10`
  - actual：`0`
- `PASS` `EFFICIENCY_EMBEDDING_QUERY_CALLS`：效率指标不超过预算
  - expected：`1`
  - actual：`0`
