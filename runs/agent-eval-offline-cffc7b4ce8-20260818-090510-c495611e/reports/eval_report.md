# Agent Evaluation Report

## Summary

- Eval ID：`agent-eval-offline-cffc7b4ce8`
- Suite：`offline`
- Passed：`False`
- Overall score：`0.9979`
- Cases：`5/6`
- Revision：`239441e26eb044e38a3a5a2ffa131464c66bda9d`
- Dirty worktree：`True`

## Category Scores

| Category | Score |
|---|---:|
| efficiency | 1.0000 |
| evidence | 1.0000 |
| quality | 0.9936 |
| route | 1.0000 |

## Problem Coverage

- Problem 2：`mapping_quality_maple`, `mapping_quality_p4transformer`, `mapping_quality_psttransformer`
- Problem 7：`mapping_quality_maple`, `mapping_quality_p4transformer`, `mapping_quality_psttransformer`
- Problem 8：`mapping_quality_maple`, `mapping_quality_p4transformer`, `mapping_quality_psttransformer`

## Baseline Diff

- Passed：`True`
- New cases：`['mapping_quality_maple', 'mapping_quality_p4transformer', 'mapping_quality_psttransformer', 'offline_maple_paper_parser', 'offline_p4transformer_paper_parser', 'offline_psttransformer_paper_parser']`
- Missing cases：`[]`
- Newly failed：`[]`
- Score regressions：`0`

## Case Details

### offline_maple_paper_parser

- Passed：`True`
- Score：`1.0000`
- Runner：`paper_parser`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-offline-cffc7b4ce8-20260818-090510-c495611e/traces/eval_cases/offline_maple_paper_parser/observation.json`

#### route

- Passed：`True`
- Score：`1.0000`
- `PASS` `FINAL_STATUS_ALLOWED`：final_status 必须属于允许集合
  - expected：`["succeeded"]`
  - actual：`"succeeded"`

#### quality

- Passed：`True`
- Score：`1.0000`
- `PASS` `QUALITY_PAPER_INDEXED_PAGE_RATIO`：论文页索引覆盖率达到下限
  - expected：`1.0`
  - actual：`1.0`
- `PASS` `QUALITY_PAPER_SECTION_KIND:abstract`：必须识别指定章节类型
  - expected：`"abstract"`
  - actual：`["ablation", "abstract", "conclusion", "datasets", "experiments", "implementation", "introduction", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:introduction`：必须识别指定章节类型
  - expected：`"introduction"`
  - actual：`["ablation", "abstract", "conclusion", "datasets", "experiments", "implementation", "introduction", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:related_work`：必须识别指定章节类型
  - expected：`"related_work"`
  - actual：`["ablation", "abstract", "conclusion", "datasets", "experiments", "implementation", "introduction", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:method`：必须识别指定章节类型
  - expected：`"method"`
  - actual：`["ablation", "abstract", "conclusion", "datasets", "experiments", "implementation", "introduction", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:experiments`：必须识别指定章节类型
  - expected：`"experiments"`
  - actual：`["ablation", "abstract", "conclusion", "datasets", "experiments", "implementation", "introduction", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:implementation`：必须识别指定章节类型
  - expected：`"implementation"`
  - actual：`["ablation", "abstract", "conclusion", "datasets", "experiments", "implementation", "introduction", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:ablation`：必须识别指定章节类型
  - expected：`"ablation"`
  - actual：`["ablation", "abstract", "conclusion", "datasets", "experiments", "implementation", "introduction", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:conclusion`：必须识别指定章节类型
  - expected：`"conclusion"`
  - actual：`["ablation", "abstract", "conclusion", "datasets", "experiments", "implementation", "introduction", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:references`：必须识别指定章节类型
  - expected：`"references"`
  - actual：`["ablation", "abstract", "conclusion", "datasets", "experiments", "implementation", "introduction", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Introduction`：必须识别指定章节标题
  - expected：`"Introduction"`
  - actual：`["MAPLE: Masked Pseudo-Labeling autoEncoder for", "Semi-supervised Point Cloud Action Recognition", "Xiaodong Chen∗", "Wu Liu†", "Xinchen Liu", "Yongdong Zhang", "Jungong Han", "Tao Mei", "KEYWORDS", "ABSTRACT", "INTRODUCTION", "CCS CONCEPTS", "RELATED WORK", "(a) Data Preparation", "(b) Spatial Extractor", "(c) Temporal Aggregator", "(d) Prediction Head", "Input Data Point Cloud Video", "Output ࢟࢏", "Class Label", "Classification", "Temporal", "Spatial", "Transformer", "Spatial", "Transformer", "Padding", "Head", "Encoder", "Pos. Emb. ~ +", "Point 4D Convolution", "Pooling", "Pooling", "P4Conv", "Position Embedding", "+ Element-wise Add", "Encode Local Area with Point", "4D Convolution (P4Conv)", "Share Weight", "THE PROPOSED MAPLE FRAMEWORK", "Kullback-Leibler Divergence Loss", "Cross-en...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Related Work`：必须识别指定章节标题
  - expected：`"Related Work"`
  - actual：`["MAPLE: Masked Pseudo-Labeling autoEncoder for", "Semi-supervised Point Cloud Action Recognition", "Xiaodong Chen∗", "Wu Liu†", "Xinchen Liu", "Yongdong Zhang", "Jungong Han", "Tao Mei", "KEYWORDS", "ABSTRACT", "INTRODUCTION", "CCS CONCEPTS", "RELATED WORK", "(a) Data Preparation", "(b) Spatial Extractor", "(c) Temporal Aggregator", "(d) Prediction Head", "Input Data Point Cloud Video", "Output ࢟࢏", "Class Label", "Classification", "Temporal", "Spatial", "Transformer", "Spatial", "Transformer", "Padding", "Head", "Encoder", "Pos. Emb. ~ +", "Point 4D Convolution", "Pooling", "Pooling", "P4Conv", "Position Embedding", "+ Element-wise Add", "Encode Local Area with Point", "4D Convolution (P4Conv)", "Share Weight", "THE PROPOSED MAPLE FRAMEWORK", "Kullback-Leibler Divergence Loss", "Cross-en...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:The Proposed MAPLE Framework`：必须识别指定章节标题
  - expected：`"The Proposed MAPLE Framework"`
  - actual：`["MAPLE: Masked Pseudo-Labeling autoEncoder for", "Semi-supervised Point Cloud Action Recognition", "Xiaodong Chen∗", "Wu Liu†", "Xinchen Liu", "Yongdong Zhang", "Jungong Han", "Tao Mei", "KEYWORDS", "ABSTRACT", "INTRODUCTION", "CCS CONCEPTS", "RELATED WORK", "(a) Data Preparation", "(b) Spatial Extractor", "(c) Temporal Aggregator", "(d) Prediction Head", "Input Data Point Cloud Video", "Output ࢟࢏", "Class Label", "Classification", "Temporal", "Spatial", "Transformer", "Spatial", "Transformer", "Padding", "Head", "Encoder", "Pos. Emb. ~ +", "Point 4D Convolution", "Pooling", "Pooling", "P4Conv", "Position Embedding", "+ Element-wise Add", "Encode Local Area with Point", "4D Convolution (P4Conv)", "Share Weight", "THE PROPOSED MAPLE FRAMEWORK", "Kullback-Leibler Divergence Loss", "Cross-en...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Experiments`：必须识别指定章节标题
  - expected：`"Experiments"`
  - actual：`["MAPLE: Masked Pseudo-Labeling autoEncoder for", "Semi-supervised Point Cloud Action Recognition", "Xiaodong Chen∗", "Wu Liu†", "Xinchen Liu", "Yongdong Zhang", "Jungong Han", "Tao Mei", "KEYWORDS", "ABSTRACT", "INTRODUCTION", "CCS CONCEPTS", "RELATED WORK", "(a) Data Preparation", "(b) Spatial Extractor", "(c) Temporal Aggregator", "(d) Prediction Head", "Input Data Point Cloud Video", "Output ࢟࢏", "Class Label", "Classification", "Temporal", "Spatial", "Transformer", "Spatial", "Transformer", "Padding", "Head", "Encoder", "Pos. Emb. ~ +", "Point 4D Convolution", "Pooling", "Pooling", "P4Conv", "Position Embedding", "+ Element-wise Add", "Encode Local Area with Point", "4D Convolution (P4Conv)", "Share Weight", "THE PROPOSED MAPLE FRAMEWORK", "Kullback-Leibler Divergence Loss", "Cross-en...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Conclusion`：必须识别指定章节标题
  - expected：`"Conclusion"`
  - actual：`["MAPLE: Masked Pseudo-Labeling autoEncoder for", "Semi-supervised Point Cloud Action Recognition", "Xiaodong Chen∗", "Wu Liu†", "Xinchen Liu", "Yongdong Zhang", "Jungong Han", "Tao Mei", "KEYWORDS", "ABSTRACT", "INTRODUCTION", "CCS CONCEPTS", "RELATED WORK", "(a) Data Preparation", "(b) Spatial Extractor", "(c) Temporal Aggregator", "(d) Prediction Head", "Input Data Point Cloud Video", "Output ࢟࢏", "Class Label", "Classification", "Temporal", "Spatial", "Transformer", "Spatial", "Transformer", "Padding", "Head", "Encoder", "Pos. Emb. ~ +", "Point 4D Convolution", "Pooling", "Pooling", "P4Conv", "Position Embedding", "+ Element-wise Add", "Encode Local Area with Point", "4D Convolution (P4Conv)", "Share Weight", "THE PROPOSED MAPLE FRAMEWORK", "Kullback-Leibler Divergence Loss", "Cross-en...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_EXACT:THE PROPOSED MAPLE FRAMEWORK`：必须识别完整逻辑章节标题
  - expected：`"THE PROPOSED MAPLE FRAMEWORK"`
  - actual：`["MAPLE: Masked Pseudo-Labeling autoEncoder for", "Semi-supervised Point Cloud Action Recognition", "Xiaodong Chen∗", "Wu Liu†", "Xinchen Liu", "Yongdong Zhang", "Jungong Han", "Tao Mei", "KEYWORDS", "ABSTRACT", "INTRODUCTION", "CCS CONCEPTS", "RELATED WORK", "(a) Data Preparation", "(b) Spatial Extractor", "(c) Temporal Aggregator", "(d) Prediction Head", "Input Data Point Cloud Video", "Output ࢟࢏", "Class Label", "Classification", "Temporal", "Spatial", "Transformer", "Spatial", "Transformer", "Padding", "Head", "Encoder", "Pos. Emb. ~ +", "Point 4D Convolution", "Pooling", "Pooling", "P4Conv", "Position Embedding", "+ Element-wise Add", "Encode Local Area with Point", "4D Convolution (P4Conv)", "Share Weight", "THE PROPOSED MAPLE FRAMEWORK", "Kullback-Leibler Divergence Loss", "Cross-en...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_COUNT_MIN`：section 数量不能因过度过滤低于下限
  - expected：`70`
  - actual：`82`
- `PASS` `QUALITY_PAPER_SECTION_COUNT_MAX`：section 数量不能因误检超过上限
  - expected：`95`
  - actual：`82`
- `PASS` `QUALITY_PAPER_PARENT:3.1`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "3.1", "parent_number": "3"}`
  - actual：`[{"number": "3.1", "title": "Preliminary", "parent_number": "3", "parent_title": "THE PROPOSED MAPLE FRAMEWORK"}]`
- `PASS` `QUALITY_PAPER_PARENT:3.2`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "3.2", "parent_number": "3"}`
  - actual：`[{"number": "3.2", "title": "Decoupled Spatial-temporal TransFormer", "parent_number": "3", "parent_title": "THE PROPOSED MAPLE FRAMEWORK"}]`
- `PASS` `QUALITY_PAPER_PARENT:3.3`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "3.3", "parent_number": "3"}`
  - actual：`[{"number": "3.3", "title": "Masked Pseudo-labeling Autoencoder", "parent_number": "3", "parent_title": "THE PROPOSED MAPLE FRAMEWORK"}]`
- `PASS` `QUALITY_PAPER_PARENT:4.1`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "4.1", "parent_number": "4"}`
  - actual：`[{"number": "4.1", "title": "Dataset", "parent_number": "4", "parent_title": "EXPERIMENTS"}]`
- `PASS` `QUALITY_PAPER_PARENT:4.2`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "4.2", "parent_number": "4"}`
  - actual：`[{"number": "4.2", "title": "Implementation Details and Approaches", "parent_number": "4", "parent_title": "EXPERIMENTS"}]`
- `PASS` `QUALITY_PAPER_PARENT:4.5`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "4.5", "parent_number": "4"}`
  - actual：`[{"number": "4.5", "title": "Ablation Study and Visualization", "parent_number": "4", "parent_title": "EXPERIMENTS"}]`
- `PASS` `QUALITY_PAPER_OCR_REQUIRED`：需要 OCR 的页面数不超过阈值
  - expected：`0`
  - actual：`[]`

#### efficiency

- Passed：`True`
- Score：`1.0000`
- `PASS` `EFFICIENCY_DURATION`：效率指标不超过预算
  - expected：`15000.0`
  - actual：`3568.9506320049986`

### mapping_quality_maple

- Passed：`True`
- Score：`1.0000`
- Runner：`fixture`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-offline-cffc7b4ce8-20260818-090510-c495611e/traces/eval_cases/mapping_quality_maple/observation.json`

#### evidence

- Passed：`True`
- Score：`1.0000`
- `PASS` `EVIDENCE_PATH:modules/point_4d_convolution.py`：必须存在来源路径
  - expected：`"modules/point_4d_convolution.py"`
  - actual：`["modules/point_4d_convolution.py", "models/msr_mae.py"]`
- `PASS` `EVIDENCE_PATH:models/msr_mae.py`：必须存在来源路径
  - expected：`"models/msr_mae.py"`
  - actual：`["modules/point_4d_convolution.py", "models/msr_mae.py"]`
- `PASS` `EVIDENCE_LOCATION`：Evidence location 完整度符合预期
  - expected：`true`
  - actual：`true`
- `PASS` `EVIDENCE_HASH`：Evidence hash 完整度符合预期
  - expected：`true`
  - actual：`true`

#### quality

- Passed：`True`
- Score：`1.0000`
- `PASS` `QUALITY_MODULE:P4Transformer`：必须覆盖模块
  - expected：`"P4Transformer"`
  - actual：`true`
- `PASS` `QUALITY_MODULE:P4DConv`：必须覆盖模块
  - expected：`"P4DConv"`
  - actual：`true`
- `PASS` `QUALITY_FILE:modules/point_4d_convolution.py`：必须找到文件
  - expected：`"modules/point_4d_convolution.py"`
  - actual：`true`
- `PASS` `QUALITY_FILE:models/msr_mae.py`：必须找到文件
  - expected：`"models/msr_mae.py"`
  - actual：`true`

### mapping_quality_p4transformer

- Passed：`True`
- Score：`1.0000`
- Runner：`fixture`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-offline-cffc7b4ce8-20260818-090510-c495611e/traces/eval_cases/mapping_quality_p4transformer/observation.json`

#### evidence

- Passed：`True`
- Score：`1.0000`
- `PASS` `EVIDENCE_PATH:modules/point_4d_convolution.py`：必须存在来源路径
  - expected：`"modules/point_4d_convolution.py"`
  - actual：`["modules/point_4d_convolution.py", "models/sequence_classification.py"]`
- `PASS` `EVIDENCE_PATH:models/sequence_classification.py`：必须存在来源路径
  - expected：`"models/sequence_classification.py"`
  - actual：`["modules/point_4d_convolution.py", "models/sequence_classification.py"]`
- `PASS` `EVIDENCE_LOCATION`：Evidence location 完整度符合预期
  - expected：`true`
  - actual：`true`
- `PASS` `EVIDENCE_HASH`：Evidence hash 完整度符合预期
  - expected：`true`
  - actual：`true`

#### quality

- Passed：`True`
- Score：`1.0000`
- `PASS` `QUALITY_MODULE:P4Transformer`：必须覆盖模块
  - expected：`"P4Transformer"`
  - actual：`true`
- `PASS` `QUALITY_MODULE:P4DConv`：必须覆盖模块
  - expected：`"P4DConv"`
  - actual：`true`
- `PASS` `QUALITY_FILE:modules/point_4d_convolution.py`：必须找到文件
  - expected：`"modules/point_4d_convolution.py"`
  - actual：`true`
- `PASS` `QUALITY_FILE:models/sequence_classification.py`：必须找到文件
  - expected：`"models/sequence_classification.py"`
  - actual：`true`

### mapping_quality_psttransformer

- Passed：`True`
- Score：`1.0000`
- Runner：`fixture`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-offline-cffc7b4ce8-20260818-090510-c495611e/traces/eval_cases/mapping_quality_psttransformer/observation.json`

#### evidence

- Passed：`True`
- Score：`1.0000`
- `PASS` `EVIDENCE_PATH:modules/pst_convolution.py`：必须存在来源路径
  - expected：`"modules/pst_convolution.py"`
  - actual：`["modules/pst_convolution.py", "models/sequence_classification.py"]`
- `PASS` `EVIDENCE_PATH:models/sequence_classification.py`：必须存在来源路径
  - expected：`"models/sequence_classification.py"`
  - actual：`["modules/pst_convolution.py", "models/sequence_classification.py"]`
- `PASS` `EVIDENCE_LOCATION`：Evidence location 完整度符合预期
  - expected：`true`
  - actual：`true`
- `PASS` `EVIDENCE_HASH`：Evidence hash 完整度符合预期
  - expected：`true`
  - actual：`true`

#### quality

- Passed：`True`
- Score：`1.0000`
- `PASS` `QUALITY_MODULE:PSTTransformer`：必须覆盖模块
  - expected：`"PSTTransformer"`
  - actual：`true`
- `PASS` `QUALITY_MODULE:P4DConv`：必须覆盖模块
  - expected：`"P4DConv"`
  - actual：`true`
- `PASS` `QUALITY_FILE:modules/pst_convolution.py`：必须找到文件
  - expected：`"modules/pst_convolution.py"`
  - actual：`true`
- `PASS` `QUALITY_FILE:models/sequence_classification.py`：必须找到文件
  - expected：`"models/sequence_classification.py"`
  - actual：`true`

### offline_p4transformer_paper_parser

- Passed：`True`
- Score：`1.0000`
- Runner：`paper_parser`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-offline-cffc7b4ce8-20260818-090510-c495611e/traces/eval_cases/offline_p4transformer_paper_parser/observation.json`

#### route

- Passed：`True`
- Score：`1.0000`
- `PASS` `FINAL_STATUS_ALLOWED`：final_status 必须属于允许集合
  - expected：`["succeeded", "partial"]`
  - actual：`"partial"`

#### quality

- Passed：`True`
- Score：`1.0000`
- `PASS` `QUALITY_PAPER_INDEXED_PAGE_RATIO`：论文页索引覆盖率达到下限
  - expected：`1.0`
  - actual：`1.0`
- `PASS` `QUALITY_PAPER_SECTION_KIND:abstract`：必须识别指定章节类型
  - expected：`"abstract"`
  - actual：`["abstract", "conclusion", "experiments", "introduction", "method", "other", "references", "related_work"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:introduction`：必须识别指定章节类型
  - expected：`"introduction"`
  - actual：`["abstract", "conclusion", "experiments", "introduction", "method", "other", "references", "related_work"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:related_work`：必须识别指定章节类型
  - expected：`"related_work"`
  - actual：`["abstract", "conclusion", "experiments", "introduction", "method", "other", "references", "related_work"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:method`：必须识别指定章节类型
  - expected：`"method"`
  - actual：`["abstract", "conclusion", "experiments", "introduction", "method", "other", "references", "related_work"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:experiments`：必须识别指定章节类型
  - expected：`"experiments"`
  - actual：`["abstract", "conclusion", "experiments", "introduction", "method", "other", "references", "related_work"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:conclusion`：必须识别指定章节类型
  - expected：`"conclusion"`
  - actual：`["abstract", "conclusion", "experiments", "introduction", "method", "other", "references", "related_work"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:references`：必须识别指定章节类型
  - expected：`"references"`
  - actual：`["abstract", "conclusion", "experiments", "introduction", "method", "other", "references", "related_work"]`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Abstract`：必须识别指定章节标题
  - expected：`"Abstract"`
  - actual：`["Point 4D Transformer Networks for Spatio-Temporal Modeling", "in Point Cloud Videos", "Yi Yang", "Hehe Fan", "School of Computing", "National University of Singapore", "ReLER", "University of Technology Sydney", "Mohan Kankanhalli", "School of Computing", "National University of Singapore", "Abstract", "Introduction", "Related Work", "Point 4D Transformer Networks", "Experiments", "NTU RGB+D 60 and NTU RGB+D 120", "Conclusion", "Acknowledgments", "References"]`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Introduction`：必须识别指定章节标题
  - expected：`"Introduction"`
  - actual：`["Point 4D Transformer Networks for Spatio-Temporal Modeling", "in Point Cloud Videos", "Yi Yang", "Hehe Fan", "School of Computing", "National University of Singapore", "ReLER", "University of Technology Sydney", "Mohan Kankanhalli", "School of Computing", "National University of Singapore", "Abstract", "Introduction", "Related Work", "Point 4D Transformer Networks", "Experiments", "NTU RGB+D 60 and NTU RGB+D 120", "Conclusion", "Acknowledgments", "References"]`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Related Work`：必须识别指定章节标题
  - expected：`"Related Work"`
  - actual：`["Point 4D Transformer Networks for Spatio-Temporal Modeling", "in Point Cloud Videos", "Yi Yang", "Hehe Fan", "School of Computing", "National University of Singapore", "ReLER", "University of Technology Sydney", "Mohan Kankanhalli", "School of Computing", "National University of Singapore", "Abstract", "Introduction", "Related Work", "Point 4D Transformer Networks", "Experiments", "NTU RGB+D 60 and NTU RGB+D 120", "Conclusion", "Acknowledgments", "References"]`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Point 4D Transformer Networks`：必须识别指定章节标题
  - expected：`"Point 4D Transformer Networks"`
  - actual：`["Point 4D Transformer Networks for Spatio-Temporal Modeling", "in Point Cloud Videos", "Yi Yang", "Hehe Fan", "School of Computing", "National University of Singapore", "ReLER", "University of Technology Sydney", "Mohan Kankanhalli", "School of Computing", "National University of Singapore", "Abstract", "Introduction", "Related Work", "Point 4D Transformer Networks", "Experiments", "NTU RGB+D 60 and NTU RGB+D 120", "Conclusion", "Acknowledgments", "References"]`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Experiments`：必须识别指定章节标题
  - expected：`"Experiments"`
  - actual：`["Point 4D Transformer Networks for Spatio-Temporal Modeling", "in Point Cloud Videos", "Yi Yang", "Hehe Fan", "School of Computing", "National University of Singapore", "ReLER", "University of Technology Sydney", "Mohan Kankanhalli", "School of Computing", "National University of Singapore", "Abstract", "Introduction", "Related Work", "Point 4D Transformer Networks", "Experiments", "NTU RGB+D 60 and NTU RGB+D 120", "Conclusion", "Acknowledgments", "References"]`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Conclusion`：必须识别指定章节标题
  - expected：`"Conclusion"`
  - actual：`["Point 4D Transformer Networks for Spatio-Temporal Modeling", "in Point Cloud Videos", "Yi Yang", "Hehe Fan", "School of Computing", "National University of Singapore", "ReLER", "University of Technology Sydney", "Mohan Kankanhalli", "School of Computing", "National University of Singapore", "Abstract", "Introduction", "Related Work", "Point 4D Transformer Networks", "Experiments", "NTU RGB+D 60 and NTU RGB+D 120", "Conclusion", "Acknowledgments", "References"]`
- `PASS` `QUALITY_PAPER_SECTION_EXACT:Point 4D Transformer Networks for Spatio-Temporal Modeling`：必须识别完整逻辑章节标题
  - expected：`"Point 4D Transformer Networks for Spatio-Temporal Modeling"`
  - actual：`["Point 4D Transformer Networks for Spatio-Temporal Modeling", "in Point Cloud Videos", "Yi Yang", "Hehe Fan", "School of Computing", "National University of Singapore", "ReLER", "University of Technology Sydney", "Mohan Kankanhalli", "School of Computing", "National University of Singapore", "Abstract", "Introduction", "Related Work", "Point 4D Transformer Networks", "Experiments", "NTU RGB+D 60 and NTU RGB+D 120", "Conclusion", "Acknowledgments", "References"]`
- `PASS` `QUALITY_PAPER_SECTION_COUNT_MIN`：section 数量不能因过度过滤低于下限
  - expected：`15`
  - actual：`20`
- `PASS` `QUALITY_PAPER_SECTION_COUNT_MAX`：section 数量不能因误检超过上限
  - expected：`25`
  - actual：`20`
- `PASS` `QUALITY_PAPER_OCR_REQUIRED`：需要 OCR 的页面数不超过阈值
  - expected：`0`
  - actual：`[]`

#### efficiency

- Passed：`True`
- Score：`1.0000`
- `PASS` `EFFICIENCY_DURATION`：效率指标不超过预算
  - expected：`15000.0`
  - actual：`3704.925078083761`

### offline_psttransformer_paper_parser

- Passed：`False`
- Score：`0.9872`
- Runner：`paper_parser`
- Observation：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/agent-eval-offline-cffc7b4ce8-20260818-090510-c495611e/traces/eval_cases/offline_psttransformer_paper_parser/observation.json`

#### route

- Passed：`True`
- Score：`1.0000`
- `PASS` `FINAL_STATUS_ALLOWED`：final_status 必须属于允许集合
  - expected：`["succeeded", "partial"]`
  - actual：`"partial"`

#### quality

- Passed：`False`
- Score：`0.9615`
- `PASS` `QUALITY_PAPER_INDEXED_PAGE_RATIO`：论文页索引覆盖率达到下限
  - expected：`1.0`
  - actual：`1.0`
- `PASS` `QUALITY_PAPER_SECTION_KIND:introduction`：必须识别指定章节类型
  - expected：`"introduction"`
  - actual：`["ablation", "conclusion", "datasets", "experiments", "introduction", "limitations", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:related_work`：必须识别指定章节类型
  - expected：`"related_work"`
  - actual：`["ablation", "conclusion", "datasets", "experiments", "introduction", "limitations", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:method`：必须识别指定章节类型
  - expected：`"method"`
  - actual：`["ablation", "conclusion", "datasets", "experiments", "introduction", "limitations", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:experiments`：必须识别指定章节类型
  - expected：`"experiments"`
  - actual：`["ablation", "conclusion", "datasets", "experiments", "introduction", "limitations", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:ablation`：必须识别指定章节类型
  - expected：`"ablation"`
  - actual：`["ablation", "conclusion", "datasets", "experiments", "introduction", "limitations", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:conclusion`：必须识别指定章节类型
  - expected：`"conclusion"`
  - actual：`["ablation", "conclusion", "datasets", "experiments", "introduction", "limitations", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:references`：必须识别指定章节类型
  - expected：`"references"`
  - actual：`["ablation", "conclusion", "datasets", "experiments", "introduction", "limitations", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:datasets`：必须识别指定章节类型
  - expected：`"datasets"`
  - actual：`["ablation", "conclusion", "datasets", "experiments", "introduction", "limitations", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_KIND:results`：必须识别指定章节类型
  - expected：`"results"`
  - actual：`["ablation", "conclusion", "datasets", "experiments", "introduction", "limitations", "method", "other", "references", "related_work", "results"]`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Introduction`：必须识别指定章节标题
  - expected：`"Introduction"`
  - actual：`["Point Spatio-Temporal Transformer Networks", "for Point Cloud Video Modeling", "Hehe Fan", ", Yi Yang", ", Senior Member, IEEE, and Mohan Kankanhalli", ", Fellow, IEEE", "INTRODUCTION", "However, because points may flow in and out across", "frames, accurately tracking points is extremely difficult,", "especially", "long", "avoid", "point", "tracking,", "PSTNet [12] limits the temporal modeling range by observ-", "ing only a few frames (temporal window) for each local", "area, assuming that a point would not escape from the area", "in a short period of time, as shown in Fig. 1b. However,", "when frame sampling frequency is low or objects move fast,", "points may still escape from local areas. Moreover, the opti-", "mal temporal window size for different motions is usually", "different. Us...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Related Work`：必须识别指定章节标题
  - expected：`"Related Work"`
  - actual：`["Point Spatio-Temporal Transformer Networks", "for Point Cloud Video Modeling", "Hehe Fan", ", Yi Yang", ", Senior Member, IEEE, and Mohan Kankanhalli", ", Fellow, IEEE", "INTRODUCTION", "However, because points may flow in and out across", "frames, accurately tracking points is extremely difficult,", "especially", "long", "avoid", "point", "tracking,", "PSTNet [12] limits the temporal modeling range by observ-", "ing only a few frames (temporal window) for each local", "area, assuming that a point would not escape from the area", "in a short period of time, as shown in Fig. 1b. However,", "when frame sampling frequency is low or objects move fast,", "points may still escape from local areas. Moreover, the opti-", "mal temporal window size for different motions is usually", "different. Us...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Point Spatio-Temporal Transformer`：必须识别指定章节标题
  - expected：`"Point Spatio-Temporal Transformer"`
  - actual：`["Point Spatio-Temporal Transformer Networks", "for Point Cloud Video Modeling", "Hehe Fan", ", Yi Yang", ", Senior Member, IEEE, and Mohan Kankanhalli", ", Fellow, IEEE", "INTRODUCTION", "However, because points may flow in and out across", "frames, accurately tracking points is extremely difficult,", "especially", "long", "avoid", "point", "tracking,", "PSTNet [12] limits the temporal modeling range by observ-", "ing only a few frames (temporal window) for each local", "area, assuming that a point would not escape from the area", "in a short period of time, as shown in Fig. 1b. However,", "when frame sampling frequency is low or objects move fast,", "points may still escape from local areas. Moreover, the opti-", "mal temporal window size for different motions is usually", "different. Us...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Experiments`：必须识别指定章节标题
  - expected：`"Experiments"`
  - actual：`["Point Spatio-Temporal Transformer Networks", "for Point Cloud Video Modeling", "Hehe Fan", ", Yi Yang", ", Senior Member, IEEE, and Mohan Kankanhalli", ", Fellow, IEEE", "INTRODUCTION", "However, because points may flow in and out across", "frames, accurately tracking points is extremely difficult,", "especially", "long", "avoid", "point", "tracking,", "PSTNet [12] limits the temporal modeling range by observ-", "ing only a few frames (temporal window) for each local", "area, assuming that a point would not escape from the area", "in a short period of time, as shown in Fig. 1b. However,", "when frame sampling frequency is low or objects move fast,", "points may still escape from local areas. Moreover, the opti-", "mal temporal window size for different motions is usually", "different. Us...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_TITLE:Conclusion`：必须识别指定章节标题
  - expected：`"Conclusion"`
  - actual：`["Point Spatio-Temporal Transformer Networks", "for Point Cloud Video Modeling", "Hehe Fan", ", Yi Yang", ", Senior Member, IEEE, and Mohan Kankanhalli", ", Fellow, IEEE", "INTRODUCTION", "However, because points may flow in and out across", "frames, accurately tracking points is extremely difficult,", "especially", "long", "avoid", "point", "tracking,", "PSTNet [12] limits the temporal modeling range by observ-", "ing only a few frames (temporal window) for each local", "area, assuming that a point would not escape from the area", "in a short period of time, as shown in Fig. 1b. However,", "when frame sampling frequency is low or objects move fast,", "points may still escape from local areas. Moreover, the opti-", "mal temporal window size for different motions is usually", "different. Us...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_EXACT:POINT SPATIO-TEMPORAL TRANSFORMER`：必须识别完整逻辑章节标题
  - expected：`"POINT SPATIO-TEMPORAL TRANSFORMER"`
  - actual：`["Point Spatio-Temporal Transformer Networks", "for Point Cloud Video Modeling", "Hehe Fan", ", Yi Yang", ", Senior Member, IEEE, and Mohan Kankanhalli", ", Fellow, IEEE", "INTRODUCTION", "However, because points may flow in and out across", "frames, accurately tracking points is extremely difficult,", "especially", "long", "avoid", "point", "tracking,", "PSTNet [12] limits the temporal modeling range by observ-", "ing only a few frames (temporal window) for each local", "area, assuming that a point would not escape from the area", "in a short period of time, as shown in Fig. 1b. However,", "when frame sampling frequency is low or objects move fast,", "points may still escape from local areas. Moreover, the opti-", "mal temporal window size for different motions is usually", "different. Us...<truncated>`
- `PASS` `QUALITY_PAPER_SECTION_COUNT_MIN`：section 数量不能因过度过滤低于下限
  - expected：`500`
  - actual：`571`
- `PASS` `QUALITY_PAPER_SECTION_COUNT_MAX`：section 数量不能因误检超过上限
  - expected：`650`
  - actual：`571`
- `PASS` `QUALITY_PAPER_PARENT:3.1`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "3.1", "parent_number": "3"}`
  - actual：`[{"number": "3.1", "title": "Preliminary: Transformer", "parent_number": "3", "parent_title": "POINT SPATIO-TEMPORAL TRANSFORMER"}]`
- `FAIL` `QUALITY_PAPER_PARENT:3.2`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "3.2", "parent_number": "3"}`
  - actual：`[{"number": "3.2", "title": "PST-Transformer for Point Cloud Video", "parent_number": null, "parent_title": null}]`
- `PASS` `QUALITY_PAPER_PARENT:3.2.1`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "3.2.1", "parent_number": "3.2"}`
  - actual：`[{"number": "3.2.1", "title": "Spatio-Temporal Structure Preservation", "parent_number": "3.2", "parent_title": "PST-Transformer for Point Cloud Video"}]`
- `PASS` `QUALITY_PAPER_PARENT:4.1`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "4.1", "parent_number": "4"}`
  - actual：`[{"number": "4.1", "title": "3D Action Recognition", "parent_number": "4", "parent_title": "EXPERIMENTS"}]`
- `PASS` `QUALITY_PAPER_PARENT:4.1.1`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "4.1.1", "parent_number": "4.1"}`
  - actual：`[{"number": "4.1.1", "title": "MSR-Action3D", "parent_number": "4.1", "parent_title": "3D Action Recognition"}]`
- `PASS` `QUALITY_PAPER_PARENT:4.3`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "4.3", "parent_number": "4"}`
  - actual：`[{"number": "4.3", "title": "Ablation Study", "parent_number": "4", "parent_title": "EXPERIMENTS"}]`
- `PASS` `QUALITY_PAPER_PARENT:4.3.1`：子章节必须绑定到显式父编号
  - expected：`{"child_number": "4.3.1", "parent_number": "4.3"}`
  - actual：`[{"number": "4.3.1", "title": "Spatio-Temporal Encoding", "parent_number": "4.3", "parent_title": "Ablation Study"}]`
- `PASS` `QUALITY_PAPER_OCR_REQUIRED`：需要 OCR 的页面数不超过阈值
  - expected：`0`
  - actual：`[]`

#### efficiency

- Passed：`True`
- Score：`1.0000`
- `PASS` `EFFICIENCY_DURATION`：效率指标不超过预算
  - expected：`15000.0`
  - actual：`3589.857045910321`
