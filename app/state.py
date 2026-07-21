from typing import Any, Optional, TypedDict


class ReproductionState(TypedDict, total=False):
    task_id: str
    user_query: str
    paper_path: Optional[str]
    repo_path: Optional[str]
    log_path: Optional[str]
    experiment_goal: Optional[str]

    paper_text_chunks: list[dict[str, Any]]
    paper_summary: dict[str, Any]
    method_modules: list[dict[str, Any]]
    repo_map: dict[str, Any]
    paper_code_mapping: list[dict[str, Any]]
    experiment_plan: dict[str, Any]
    debug_report: dict[str, Any]
    run_commands: list[dict[str, Any]]

    edited_run_commands: list[dict[str, Any]]
    selected_run_command_index: Optional[int]
    command_selection_record: Optional[dict[str, Any]]

    pending_action: Optional[dict[str, Any]]
    pending_action_hash: Optional[str]
    requires_approval: bool
    user_approval: Optional[str]
    human_feedback: Optional[str]
    approval_record: Optional[dict[str, Any]]

    preflight_report: Optional[dict[str, Any]]
    preflight_passed: bool
    preflight_report_path: Optional[str]
    
    active_execution_mode: Optional[str]
    smoke_test_report: Optional[dict[str, Any]]
    smoke_test_status: Optional[str]
    smoke_test_passed: bool
    smoke_test_log_path: Optional[str]

    repair_proposal: Optional[dict[str, Any]]
    repair_attempt_count: int
    repair_history: list[dict[str, Any]]

    execution_result: dict[str, Any]
    execution_log_path: Optional[str]
    last_action_result: dict[str, Any]
    final_status: Optional[str]

    output_files: list[str]
    final_report: Optional[str]
    messages: list[dict[str, Any]]
    step_count: int
    max_steps: int
    error: Optional[str]
    code_search_results: dict[str, Any]

    run_id: Optional[str]
    run_dir: Optional[str]
    run_started_at: Optional[str]

    artifact_records: list[dict[str, Any]]
    artifact_index_path: Optional[str]
    run_manifest_path: Optional[str]
    execution_profile_id: str
    execution_profile_fingerprint: str