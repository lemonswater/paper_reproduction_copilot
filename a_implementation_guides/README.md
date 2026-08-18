# 论文复现辅助 Agent 阶段实现指南

这个文件夹是 `plan.md` 的落地版：每个阶段一个 Markdown，包含本阶段目标、要创建的文件、核心代码骨架、运行方式和验收标准。建议你按顺序推进，不要跳着把所有模块一次性写完。

## 推荐阅读顺序

```text
00_project_scaffold.md
01_v0_paper_reading.md
02_v1_repo_map.md
03_v2_paper_code_mapping.md
04_v3_experiment_plan.md
05_v4_langgraph_checkpoint_memory.md
06_v5_log_debug.md
07_v6_human_review.md
08_v7_evaluation_packaging.md
09_overall_agent_summary.md
10_end_to_end_closure_tutorial.md
11_phase_1_action_builder.md
12_phase_2_executor.md
13_phase_3_fail_to_debug.md
14_phase_4_final_report_and_eval.md
15_post_closure_roadmap.md
16_phase_5_durable_checkpoint_and_resume.md
17_phase_6_structured_action_and_approval_hash.md
18_phase_7_command_selection_and_editable_run_commands.md
19_phase_8_run_manifest_and_artifact_layering.md
20_phase_9_preflight_check_and_environment_readiness.md
21_phase_10_execution_backend_and_environment_isolation.md
22_phase_11_smoke_test_and_bounded_repair.md
23_phase_12_structured_output_reliability.md
24_phase_13_manual_file_repair_review_and_patch_level_verification.md
25_phase_14_graph_and_file_repair_safety_closure.md
26_phase_15_unified_error_and_run_native_artifacts.md
27_phase_16_safe_execution_boundary_and_supervised_process.md
28_phase_17_agent_regression_evaluation.md
29_phase_18_section_aware_paper_understanding.md
30_phase_19_high_precision_paper_structure_and_golden_eval.md
31_phase_20_hybrid_evidence_retrieval.md
32_phase_21_dense_semantic_retrieval_and_embedding_cache.md
33_phase_22_async_job_runtime_heartbeat_and_crash_recovery.md
34_phase_23_unified_task_interaction_api_decision_protocol_and_event_stream.md
35_phase_24_persistence_ports_artifact_publication_and_object_storage.md
36_phase_25_postgresql_control_plane_shared_checkpoint_and_multi_worker_claim.md
37_phase_26_workspace_materialization_worker_capability_affinity_and_cross_host_handoff.md
38_phase_27_oci_container_execution_immutable_environment_identity_and_strong_runtime_isolation.md
39_phase_28_distributed_observability_and_operational_readiness.md
40_phase_29_controlled_resource_acquisition_and_supply_chain_safety.md
41_phase_30_conversational_web_console_and_single_host_deployment.md
42_phase_31_artifact_grounded_chat_agent.md
43_phase_32_web_command_edit_and_stale_decision_recovery.md
44_phase_33_controlled_local_input_import.md
45_phase_34_artifact_preview_safe_download_and_single_job_export.md
46_phase_35_single_host_retention_quota_and_auditable_gc.md
47_phase_36_chat_context_compaction_and_citation_preserving_memory.md
48_phase_37_chat_grounding_citation_and_memory_golden_eval.md
49_phase_38_run_comparison_and_evidence_grounded_diff.md
50_phase_39_evidence_grounded_rerun_proposal_and_immutable_run_derivation.md
51_phase_40_tool_contract_testing.md
52_phase_41_local_secret_management_and_redaction.md
53_phase_42_conversation_decision_evaluation.md
54_phase_43_planner_executor_verifier_authority_separation.md
55_phase_44_long_running_task_notification_and_recovery.md
56_phase_45_verified_failure_memory_and_diagnostic_retrieval.md
57_phase_46_project_scoped_long_term_memory_and_revocable_fact_governance.md
58_phase_47_adaptive_retrieval_quality_optimization.md
59_phase_48_agent_skill_plugin_mechanism.md
60_phase_49_cross_paper_evidence_knowledge_base.md
61_phase_50_model_routing_cost_budget_and_provider_governance.md
62_phase_51_restricted_research_browser_agent.md
63_phase_52_bounded_tool_calling_and_reproduction_orchestration.md
64_phase_53_mcp_read_only_interoperability_gateway.md
65_phase_54_read_only_mcp_server_export.md
66_phase_55_mcp_interoperability_contract_eval_and_single_host_operations.md
67_phase_56_mcp_invocation_reliability_slo_and_sdk_upgrade_rehearsal.md
```

## 补充参考

下面这些文档不是严格按阶段推进的主线教程，但在日常调试和理解命令流时很有用：

```text
project_phase_capability_summary.md
python_source_code_reference.md
python_source_code_reference_phase_00_v7.md
python_source_code_reference_phase_01_16.md
python_source_code_reference_phase_17_29.md
python_source_code_reference_phase_30_39.md
python_source_code_reference_phase_40_46.md
python_source_code_reference_phase_47_56.md
12_run_graph_command_flow.md
cli_command_playbook.md
29_phase_18_paper_section_parsing_problem_analysis.md
```

其中 `project_phase_capability_summary.md` 是阶段能力总览，`python_source_code_reference.md`
保留架构说明和旧版全量索引，六个 `python_source_code_reference_phase_*.md` 分册则逐函数记录
真实源码布局、输入输出语义和伪代码。以后每完成或调整一个 Phase，都必须同步更新这些文档；
函数分册可运行 `generate_function_reference.py` 统一生成。如果阶段索引发生变化，还要同步更新本文件。

## 阶段关系

```text
V0 论文结构化阅读
   ↓
V1 代码仓库地图
   ↓
V2 论文-代码证据化映射
   ↓
V3 复现实验计划
   ↓
V4 LangGraph + Checkpoint + Memory
   ↓
V5 日志 Debug
   ↓
V6 Human-in-the-loop
   ↓
V7 评测与项目包装
   ↓
整体总结与端到端闭环
   ↓
闭环后的下一阶段路线图
   ↓
Durable Checkpoint + Structured Action + Human Review
   ↓
Command Selection + Run Manifest + Artifact Layering
   ↓
Preflight Check
   ↓
Execution Backend + Agent/论文环境隔离
   ↓
Smoke Test
   ↓
Repair Proposal + 单次 Bounded Repair
   ↓
Structured Output Reliability
   ↓
Manual File Repair Review + Patch-Level Verification
   ↓
Graph + File Repair Safety Closure
   ↓
Unified Error Model + Run-Native Artifacts
   ↓
Safe Execution Boundary + Supervised Process
   ↓
Agent Regression Evaluation
   ↓
章节感知论文理解
   ↓
高精度论文章节结构与 Golden 评测闭环
   ↓
混合 Code Evidence 检索与可验证映射
   ↓
Dense Semantic Retrieval + Embedding Cache
   ↓
异步 Job Runtime + Heartbeat + Lease + 崩溃恢复
   ↓
统一任务交互 API + Decision Protocol + Event Stream
   ↓
Persistence Ports + Artifact Publication + Object Storage
   ↓
Relational JobRepository + Shared Checkpoint + Distributed Worker Claim
   ↓
Workspace Materialization + Worker Capability/Affinity
   ↓
单主机 OCI 安全执行 + Immutable Environment Identity
   ↓
Distributed Observability + Operational Readiness
   ↓
Controlled Resource Acquisition + Supply-Chain Safety
   ↓
Conversational Web Console + Single-Host Deployment
   ↓
Artifact-Grounded Chat Agent
   ↓
Web Command Edit + Stale Decision Recovery
   ↓
Controlled Local Input Import
   ↓
Artifact Preview + Safe Download + Single-Job Export
   ↓
Single-Host Retention + Quota + Auditable GC
   ↓
Chat Context Compaction + Citation-Preserving Memory
   ↓
Chat Grounding + Citation + Memory Golden Eval
   ↓
Run Comparison + Evidence-Grounded Diff
   ↓
Evidence-Grounded Rerun Proposal + Immutable Run Derivation
   ↓
Tool Contract Testing（Phase 40，已实现）
   ↓
Local Secret Management + Redaction（Phase 41，核心实现已完成）
   ↓
Conversation Decision Evaluation（Phase 42，已实现）
   ↓
Planner / Executor / Verifier Separation（Phase 43，已实现）
   ↓
Long-Running Task Notification + Recovery（Phase 44，已实现）
   ↓
Verified Failure Memory + Diagnostic Retrieval（Phase 45，已实现）
   ↓
Project-Scoped Long-Term Memory + Revocable Fact Governance（Phase 46，已实现）
   ↓
Adaptive Retrieval Quality Optimization（Phase 47，已实现，11 项专项测试通过）
   ↓
Agent Skill / Plugin Mechanism（Phase 48，已实现，23 项专项测试通过）
   ↓
Cross-Paper Evidence Knowledge Base（Phase 49，已实现，19 项专项测试通过）
   ↓
Model Routing + Cost Budget + Provider Governance（Phase 50，源码已实现，完整测试仍需收口）
   ↓
Restricted Research Browser Agent（Phase 51，已实现；非 API 专项 112 passed，API 启动测试待收口）
   ↓
Bounded Tool Calling + Reproduction Orchestration（Phase 52，已实现；本次专项回归 51 passed）
   ↓
MCP Read-only Interoperability Gateway + Schema Pinning（Phase 53，已实现；本次专项回归 40 passed）
   ↓
Read-only MCP Server Export + Public Projection（Phase 54，核心实现已完成；60 passed，4 个协议测试因 SDK 缺失而 skipped）
   ↓
MCP Interoperability Contract Eval + Single-Host Operations（Phase 55，源码已实现，运行门禁持续收口）
   ↓
MCP Invocation Reliability + SLO + SDK Upgrade Rehearsal（Phase 56，源码已实现）
```

Phase 39 之后的阶段范围、优先级和安全边界，以
[`agent_project_analysis_and_technical_roadmap.md`](agent_project_analysis_and_technical_roadmap.md#十三phase-39-之后的单机单用户待实现路线)
中的当前待实现路线为准。`Conversational Rerun Drafting` 已暂时移入 Deferred。

## Memory 应该什么时候做

本项目里不要一开始就做长期记忆。推荐拆成三层：

```text
State：
    从 V0 就开始设计。
    保存单次任务中的论文摘要、repo map、mapping、实验计划。

Artifacts：
    从 V0 就开始保存。
    早期阶段使用 outputs/；Phase 15 后直接写入 runs/<run_id>/，
    并记录 SHA-256、producer 和生成时间。

Checkpoint：
    V4 再接入。
    配合 LangGraph thread_id 实现中断恢复，这是面试里最值得讲的 memory 能力。

Long-term Memory / Store：
    V7 之后再考虑。
    用于保存跨任务经验，比如常见错误模式、用户偏好、历史复现模板。
```

所以你的实现顺序应该是：

```text
先有结构化 State
再有 Artifact 落盘
再有 LangGraph checkpoint
最后才考虑长期记忆
```

## 每个阶段的最低验收方式

每阶段完成后，都至少保留：

- 一个命令行入口。
- 一个最小输入 case。
- 一个可追踪的 Artifact 产物。
- 一个 README 中可复现的运行命令。
- 一个失败记录，说明当前阶段还做不到什么。

这样后面做评测和简历包装时会轻松很多。
