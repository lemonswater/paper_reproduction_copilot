# 最终报告

## 运行摘要

- 论文路径：`pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf`
- 仓库路径：`/data/tianshaoqi24/PST-Convolution-main/`
- 实验目标：复现论文 main result
- 最终状态：`provider_failed`
- 用户审批：`not_recorded`

## 结构化错误摘要

- `PAPER_SECTION_EVIDENCE_INVALID`：category=`agent`，stage=`method_extractor`，terminal=`False`
- 说明：Unknown evidence block_ids: ['p016-b0086-6bd8ca2f050']
- `PROVIDER_INVOKE_FAILED`：category=`provider`，stage=`method_extractor`，terminal=`False`
- 说明：Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=<redacted>, prompt_tokens=<redacted>, total_tokens=<redacted>, completion_tokens_details=<redacted>, prompt_tokens_details=<redacted>
- `PAPER_SECTION_EVIDENCE_INVALID`：category=`agent`，stage=`method_extractor`，terminal=`False`
- 说明：Unknown evidence block_ids: ['p005-b0079-2bc54e2f46']
- `PROVIDER_ERROR`：category=`provider`，stage=`mapping`，terminal=`True`
- 说明：MODEL_ROUTE_INPUT_LIMIT_EXCEEDED

## 结果解释

- 当前 run 因终止性阶段错误结束，请先处理 Error Report。

## 论文摘要

- 标题：None
- 研究问题：点云序列的表示；动态点云语义分割；PSTNet是否有效捕获点云序列中的动态。
- 核心思路：将PST操作融入深度分层网络以处理不同动态点云任务；为语义分割等密集点预测任务开发了PST转置卷积；3D 卷积核 W ∈ R^{C′×C×l×h×w}，其中 (l, h, w) 是核大小，C′ 是输出特征维度；W(i,j)_k ∈ R^{C′×C} 是核位置 (k, i, j) 的权重，F(x+i,y+j)_{t+k} ∈ R^{C×1} 是输入位置 (t+k, x+i, y+j) 的像素特征。

## 仓库要点

- 重要文件：`.pytest_cache/.gitignore`
- 重要文件：`.pytest_cache/CACHEDIR.TAG`
- 重要文件：`.pytest_cache/README.md`
- 重要文件：`.pytest_cache/v/cache/lastfailed`
- 重要文件：`.pytest_cache/v/cache/nodeids`
- 重要文件：`README.md`
- 重要文件：`data/ntu/ntu120.list`
- 重要文件：`data/ntu/ntu60.list`
- 重要文件：`datasets/msr.py`
- 重要文件：`datasets/ntu60.py`

## 论文与代码映射摘要

- 无

## 实验计划摘要

- 目标：不适用
- 环境步骤数：0
- 数据步骤数：0
- 训练步骤数：0
- 评估步骤数：0
- 运行命令数：0

## 审批摘要

- 无

## Execution Verification

- 无

## 执行摘要

- 无

## Execution Supervision

- 无

## 预检摘要

- 无

## 调试摘要

- 无

## 冒烟测试摘要

- 无

## 修复摘要

- 无

## 文件修复总结

- 无

## 输出文件

- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/inputs/run_request.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/inputs/input_validation_report.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_document.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_blocks.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_parse_report.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/reports/error_report.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/reports/error_report.md`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-5d205c6c76be-c000-c96e215dd8_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections/extractions/sec-5d205c6c76be-c000-c96e215dd8.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-f10e6346bc8e-c000-5f393cc0c4_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections/extractions/sec-f10e6346bc8e-c000-5f393cc0c4.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-921282d36d4c-c000-5759ff58ba_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections/extractions/sec-921282d36d4c-c000-5759ff58ba.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-80607dc4891e-c000-3f0092e436_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections/extractions/sec-80607dc4891e-c000-3f0092e436.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-80607dc4891e-c001-3a9e4920bc_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections/extractions/sec-80607dc4891e-c001-3a9e4920bc.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-254b22b38ae4-c000-0548af81bd_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-e640cdcacfb7-c000-c20b4c820a_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections/extractions/sec-e640cdcacfb7-c000-c20b4c820a.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-0f23881af40f-c000-e797672d4a_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections/extractions/sec-0f23881af40f-c000-e797672d4a.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-195a24050d3a-c000-ded1b046c4_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections/extractions/sec-195a24050d3a-c000-ded1b046c4.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-ded2c58b059c-c000-8d92c30c2c_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_sections/extractions/sec-ded2c58b059c-c000-8d92c30c2c.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-fb61d38a0743-c000-752b93f948_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/structured/method_extractor_sec-fb61d38a0743-c001-85101da643_structured_attempts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_summary.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/method_modules.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_fact_index.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/paper_conflicts.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/mapping_targets.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/repo_map.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/repo_summary.md`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/repo_index.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/semantic_index_manifest.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/dense_reports/00_core-method_pst.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/evidence_packs/00_core-method_pst.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/dense_reports/01_core-method_pst-transposed-convolution.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/evidence_packs/01_core-method_pst-transposed-convolution.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/dense_reports/02_core-method_deep-hierarchical-networks.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/evidence_packs/02_core-method_deep-hierarchical-networks.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/dense_reports/03_core-method_pst-convolution.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/evidence_packs/03_core-method_pst-convolution.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/dense_reports/04_core-method_3d.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/evidence_packs/04_core-method_3d.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/dense_reports/05_core-method_pstnet.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/evidence_packs/05_core-method_pstnet.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/dense_reports/06_data-pipeline_msr-action3d.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/evidence_packs/06_data-pipeline_msr-action3d.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/dense_reports/07_training-config_training-and-optimization-configuration.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/analysis/retrieval/evidence_packs/07_training-config_training-and-optimization-configuration.json`
- `/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/errors/error_561e812dff4d4711.traceback.txt`
