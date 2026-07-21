from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Confidence = Literal["low", "medium", "high"]


class Evidence(BaseModel):
    source_type: Literal["paper", "code", "readme", "config", "log"]
    source_path: str
    location: Optional[str] = None
    quote_or_summary: str
    confidence: Confidence = "medium"


class MethodModule(BaseModel):
    name: str
    description: str
    possible_keywords: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)


class PaperSummary(BaseModel):
    title: Optional[str] = None
    research_problem: str
    core_idea: str
    method_modules: list[MethodModule] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    experiment_settings: dict = Field(default_factory=dict)
    reproduction_risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


class RepoMap(BaseModel):
    repo_path: str
    readme_files: list[str] = Field(default_factory=list)
    train_entries: list[str] = Field(default_factory=list)
    eval_entries: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    model_files: list[str] = Field(default_factory=list)
    dataset_files: list[str] = Field(default_factory=list)
    loss_files: list[str] = Field(default_factory=list)
    important_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CodeCandidate(BaseModel):
    file_path: str
    symbols: list[str] = Field(default_factory=list)
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence = "medium"


class ModuleMapping(BaseModel):
    module_name: str
    candidates: list[CodeCandidate] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)

class ExperimentStep(BaseModel):
    order: int
    name: str
    action: str
    source: Literal["paper", "readme", "config", "script", "inferred", "need_confirm"]
    evidence: list[Evidence] = Field(default_factory=list)
    risk: str | None = None
    done: bool = False

class RunCommand(BaseModel):
    command: str
    cwd: str
    source: Literal["readme", "script", "config", "inferred", "need_confirm"]
    risk_level: Literal["low", "medium", "high"]
    reason: str

class ExperimentPlan(BaseModel):
    goal: str
    environment_steps: list[ExperimentStep] = Field(default_factory=list)
    data_steps: list[ExperimentStep] = Field(default_factory=list)
    train_steps: list[ExperimentStep] = Field(default_factory=list)
    eval_steps: list[ExperimentStep] = Field(default_factory=list)
    run_commands: list[RunCommand] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)

class ExecutionProfile(BaseModel):
    profile_id: str
    backend: Literal["local", "conda"]
    workspace_root: str
    artifact_root: str
    conda_executable: str | None = None
    conda_prefix: str | None = None
    env: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_backend_fields(self) -> "ExecutionProfile":
        if self.backend == "conda":
            if not self.conda_executable:
                raise ValueError("conda backend requires conda_executable")
            if not self.conda_prefix:
                raise ValueError("conda backend requires conda_prefix")

        return self

class ExecutableAction(BaseModel):
    action_id: str
    action_type: Literal["run_command"] = "run_command"
    program: str
    args: list[str] = Field(default_factory=list)
    cwd: str
    source: Literal["readme", "script", "config", "inferred", "need_confirm"]
    reason: str
    timeout_seconds: int = 300
    env_allowlist: dict[str, str] = Field(default_factory=dict)
    writable_paths: list[str] = Field(default_factory=list)
    risk: dict | None = None
    execution_profile_id: str
    execution_profile_fingerprint: str

class ApprovalRecord(BaseModel):
    approval_id: str
    action_id: str
    action_hash: str
    decision: Literal["approved", "rejected", "revise"]
    reviewer: str = "human"
    risk_level: str
    reviewed_at: str
    comment: str | None = None

class CommandEdit(BaseModel):
    index: int
    command: str

class CommandSelectionResponse(BaseModel):
    selected_index: int
    edits: list[CommandEdit] = Field(default_factory=list)
    run_commands_hash: str

class CommandSelectionRecord(BaseModel):
    selected_index: int
    edits: list[CommandEdit] = Field(default_factory=list)
    original_count: int
    run_commands_hash: str
    reviewed_at: str

class DebugReport(BaseModel):
    error_type: str
    most_likely_causes: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    check_order: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)

class PreflightItem(BaseModel):
    name: str
    category: Literal["static", "runtime", "smoke"] = "static"
    status: Literal["passed", "warning", "failed", "unknown"]
    evidence: str
    recommendation: str | None = None

class PreflightReport(BaseModel):
    action_id: str | None = None
    action_hash: str | None = None
    ready_to_execute: bool = False
    summary: str
    items: list[PreflightItem] = Field(default_factory=list)
    blocking_items: list[str] = Field(default_factory=list)
    generated_at: str

class SmokeTestReport(BaseModel):
    action_id: str | None = None
    action_hash: str | None = None
    status: Literal["passed", "failed", "skipped", "blocked"]

    summary: str
    applied_overrides: list[str] = Field(default_factory=list)
    command_preview: str | None = None
    log_path: str | None = None
    result: dict = Field(default_factory=dict)
    generated_at: str

class RepairStep(BaseModel):
    step_type: Literal[
        "edit_command",
        "manual_check",
        "rerun_smoke",
        "rerun_full",
    ]
    target: str
    change: str
    reason: str
    risk: Literal["low", "medium", "high"] = "low"

class RepairProposal(BaseModel):
    proposal_id: str | None = None
    source_error_type: str

    # edit_command: 当前阶段允许自动进入 bounded rerun
    # manual_only: 只给建议，不自动继续
    # no_repair: 暂无可靠修复路径
    kind: Literal["edit_command", "manual_only", "no_repair"] = "no_repair"

    summary: str
    root_cause: str

    # 只有 kind=edit_command 时才应提供。
    repaired_command: str | None = None
    changed_arguments: list[str] = Field(default_factory=list)

    steps: list[RepairStep] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    # 这一阶段所有 repair proposal 都应该保持 bounded=True。
    bounded: bool = True
