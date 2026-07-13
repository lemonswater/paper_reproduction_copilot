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
    experiment_plan: list[dict[str, Any]]
    debug_report: dict[str, Any]

    pending_action: Optional[dict[str, Any]]
    requires_approval: bool
    user_approval: Optional[str]

    output_files: list[str]
    final_report: Optional[str]
    messages: list[dict[str, Any]]
    step_count: int
    max_steps: int
    error: Optional[str]
    code_search_results: dict[str, Any]
