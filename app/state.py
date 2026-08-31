from __future__ import annotations

from typing import Any, TypedDict


class ReproductionState(TypedDict, total=False):
    task_id: str
    # Phase 22：只有异步 Job 运行时才存在。
    # 旧同步 CLI 不提供时保持兼容。
    job_id: str | None
    thread_id: str | None
    user_query: str
    paper_path: str | None
    repo_path: str | None
    log_path: str | None
    experiment_goal: str | None

    paper_text_chunks: list[dict[str, Any]]
    paper_summary: dict[str, Any]
    method_modules: list[dict[str, Any]]
    mapping_alias_decisions: list[dict[str, Any]]
    mapping_alias_resolution_status: str | None
    mapping_targets: list[dict[str, Any]]
    mapping_targets_path: str | None
    repo_map: dict[str, Any]
    paper_code_mapping: list[dict[str, Any]]
    experiment_plan: dict[str, Any]
    debug_report: dict[str, Any]
    run_commands: list[dict[str, Any]]

    edited_run_commands: list[dict[str, Any]]
    selected_run_command_index: int | None
    command_selection_record: dict[str, Any] | None

    pending_action: dict[str, Any] | None
    pending_action_hash: str | None
    requires_approval: bool
    user_approval: str | None
    human_feedback: str | None
    approval_record: dict[str, Any] | None

    preflight_report: dict[str, Any] | None
    preflight_passed: bool
    preflight_report_path: str | None
    
    active_execution_mode: str | None
    smoke_test_report: dict[str, Any] | None
    smoke_test_status: str | None
    smoke_test_passed: bool
    smoke_test_log_path: str | None

    repair_proposal: dict[str, Any] | None
    repair_attempt_count: int
    repair_history: list[dict[str, Any]]

    execution_result: dict[str, Any]
    execution_log_path: str | None

    # Phase 43：Executor 只生产 Evidence；Verifier 独立生成结论。
    execution_evidence: dict[str, Any] | None
    execution_verification: dict[str, Any] | None
    execution_verification_hash: str | None

    last_action_result: dict[str, Any]
    final_status: str | None

    output_files: list[str]
    final_report: str | None
    messages: list[dict[str, Any]]
    step_count: int
    max_steps: int
    error: str | None
    code_search_results: dict[str, Any]

    # RepositoryIndex 本体写 Artifact，state 只保存路径。
    repo_index_path: str | None

    # mapping target_id -> EvidencePack Artifact 绝对路径。
    code_evidence_pack_paths: dict[str, str]

    # mapping target_id -> 有限 top-k pack，供紧邻的 mapping 节点使用。
    code_evidence_packs: dict[str, dict[str, Any]]

    # log_debug 使用的 traceback-boosted Evidence Pack。
    debug_evidence_pack: dict[str, Any] | None
    debug_evidence_pack_path: str | None

    # Phase 45：历史失败案例只作为 Debug 的有界只读证据。
    failure_case_pack: dict[str, Any] | None
    failure_case_pack_path: str | None

    run_id: str | None
    run_dir: str | None
    run_started_at: str | None

    # 输入验证必须发生在 paper_reader 之前。
    input_validation_report: dict[str, Any] | None
    inputs_validated: bool

    # StageError 是新的错误事实；error 字符串暂时保留兼容旧报告。
    stage_errors: list[dict[str, Any]]
    active_stage_error: dict[str, Any] | None
    error_report_json_path: str | None
    error_report_md_path: str | None

    # 每个节点写文件后立即登记，不再等 manifest 节点复制。
    artifact_records: list[dict[str, Any]]
    artifact_index_path: str | None
    run_manifest_path: str | None

    # prepare node 在 interrupt 前保存并登记模板。
    command_selection_input_path: str | None
    command_selection_input_status: str | None

    execution_profile_id: str
    execution_profile_fingerprint: str

     # LLM 生成的文件级修复建议。
    file_repair_proposal: dict[str, Any] | None

    # 程序根据 proposal 和真实文件生成的确定性 patch。
    pending_patch: dict[str, Any] | None
    pending_patch_hash: str | None

    # 第一次人工审批，绑定 pending_patch_hash。
    patch_approval: str | None
    patch_feedback: str | None
    patch_approval_record: dict[str, Any] | None

    # Phase 43：Patch Executor 运行 worktree 检查后先写原始证据。
    patch_verification_evidence: dict[str, Any] | None

    # Patch Verifier 才能写下面三个既有字段。
    patch_verification_report: dict[str, Any] | None
    patch_verification_passed: bool
    patch_verification_hash: str | None

    # 第二次人工确认，绑定 patch hash + verification hash。
    patch_promotion_decision: str | None
    patch_promotion_feedback: str | None
    patch_promotion_record: dict[str, Any] | None

    # patch 应用到原仓库后的记录。
    patch_application_record: dict[str, Any] | None
    applied_patch_hash: str | None

    # 单独限制 file-level repair 次数，不与 command repair 混用。
    file_repair_attempt_count: int
    file_repair_history: list[dict[str, Any]]

    capability_decision: dict[str, Any] | None
    capability_report_path: str | None

    active_execution_id: str | None
    active_process_record_path: str | None
    execution_end_reason: str | None
    execution_resource_usage: dict[str, Any] | None

    cancellation_requested: bool
    cancellation_reason: str | None

    # PaperDocument 使用 JSON dict 存入 checkpoint，恢复后再 model_validate。
    paper_document: dict[str, Any]
    paper_blocks_path: str | None
    paper_sections_path: str | None
    paper_parse_report_path: str | None

    # CLI 可以对单次运行覆盖是否启用 Dense；
    # 远程上传授权不能由 LLM 或 state 覆盖，只读取 Settings。
    enable_dense_retrieval: bool
    dense_retrieval_required: bool

    # Manifest 不含源码正文和向量。
    semantic_index_manifest_path: str | None

    # mapping target_id -> DenseRetrievalReport Artifact 路径。
    dense_retrieval_report_paths: dict[str, str]

    # Phase 47：mapping target_id -> RetrievalDecision Artifact 路径。
    retrieval_policy_decision_paths: dict[str, str]

    # 实际加载的 Policy 内容身份，不保存完整配置到 checkpoint。
    retrieval_policy_sha256: str | None

    # Phase 39：只在 derived Job 中存在；普通 Job 为 None 或缺省。
    rerun_seed: dict[str, Any] | None
    rerun_seed_path: str | None

    # Phase 43：Role Guard 写入的 Hash-only 审计记录。
    authority_audit_records: list[dict[str, Any]]

    # Phase 48：Skill typed output，只作为诊断证据，不能写执行权限字段。
    skill_results: dict[str, dict[str, Any]]

    # skill_id -> 当前 Run 内 Skill Result Artifact 路径。
    skill_result_paths: dict[str, str]

    # skill_id -> Hash-only Skill Invocation Record Artifact 路径。
    skill_invocation_record_paths: dict[str, str]
