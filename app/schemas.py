from typing import Literal, Optional

from pydantic import BaseModel, Field

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

class DebugReport(BaseModel):
    error_type: str
    most_likely_causes: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    check_order: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)