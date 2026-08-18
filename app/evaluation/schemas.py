from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.chat_schemas import (
    ChatEvalObservation,
    ChatMemoryExpectation,
    ChatTurnExpectation,
)

EvalCategory = Literal[
    "schema",
    "route",
    "tool",
    "evidence",
    "safety",
    "recovery",
    "quality",
    "efficiency",
    "decision",
]

EvalSuiteName = Literal[
    "offline",
    "provider",
    "chat_offline",
    "chat_provider",
    "decision_offline",
    "decision_provider",
]

EvalRunnerKind = Literal[
    "fixture",
    "route_function",
    "live_graph",
    "paper_parser",
    "code_retrieval",
    "semantic_code_retrieval",
    "chat_scenario",
    "chat_provider",
    "conversation_decision",
    "conversation_decision_provider",
]

RouteSettingName = Literal["enable_file_repair"]


class EvalModel(BaseModel):
    """Golden Case 必须拒绝拼写错误和未知字段。"""

    model_config = ConfigDict(extra="forbid")


class EvalInput(EvalModel):
    """
    Runner 输入。

    fixture_path 只能相对 app/evaluation/；route_name 只能命中
    runners.py 的 allowlist。route_settings 只用于隔离环境差异的
    route_function case，不能影响真实 Graph。
    """

    fixture_path: str | None = None

    route_name: str | None = None
    source_node: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    route_settings: dict[RouteSettingName, bool] = Field(
        default_factory=dict
    )

    paper_path: str | None = None
    repo_path: str | None = None

    # code_retrieval 是纯确定性 runner，不调用 Provider。
    retrieval_query: str | None = None
    retrieval_keywords: list[str] = Field(
        default_factory=list
    )
    log_path: str | None = None
    experiment_goal: str = "复现论文 main result"
    execution_profile_id: str | None = None
    scripted_responses: list[Any] = Field(default_factory=list)
    secret_canaries: list[str] = Field(default_factory=list)


class ArtifactExpectation(EvalModel):
    relative_path: str
    required_substrings: list[str] = Field(default_factory=list)
    require_current_hash: bool = True


class ToolCallExpectation(EvalModel):
    name: str
    args_subset: dict[str, Any] = Field(default_factory=dict)
    min_calls: int = Field(default=1, ge=0)
    max_calls: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_call_range(self) -> ToolCallExpectation:
        if (
            self.max_calls is not None
            and self.max_calls < self.min_calls
        ):
            raise ValueError("max_calls 不能小于 min_calls")
        return self

class SectionParentExpectation(EvalModel):
    """使用显式编号表达稳定的 Golden 父子关系。"""

    child_number: str
    parent_number: str

class EvalExpected(EvalModel):
    """所有 Scorer 共用的强类型期望。"""

    exact_route: list[str] | None = None
    required_nodes: list[str] = Field(default_factory=list)
    forbidden_nodes: list[str] = Field(default_factory=list)
    allowed_final_statuses: list[str] = Field(default_factory=list)

    required_schemas: list[str] = Field(default_factory=list)
    min_schema_success_rate: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    max_schema_fallbacks: int | None = Field(default=None, ge=0)
    max_schema_retries: int | None = Field(default=None, ge=0)

    required_tool_calls: list[ToolCallExpectation] = Field(
        default_factory=list
    )
    forbidden_tool_calls: list[str] = Field(default_factory=list)

    required_artifacts: list[ArtifactExpectation] = Field(
        default_factory=list
    )
    forbidden_artifacts: list[str] = Field(default_factory=list)

    required_evidence_paths: list[str] = Field(default_factory=list)
    # Phase 20：只约束稳定检索事实，不锁死浮点 score。
    required_retrieval_paths: list[str] = Field(default_factory=list)
    forbidden_retrieval_paths: list[str] = Field(default_factory=list)
    max_retrieval_rank_by_path: dict[str, int] = Field(default_factory=dict)
    required_retrieval_channels: list[str] = Field(default_factory=list)
    min_retrieval_provenance_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    required_evidence_terms: list[str] = Field(default_factory=list)
    require_evidence_location: bool | None = None
    require_evidence_hash: bool | None = None

    required_modules: list[str] = Field(default_factory=list)
    required_files: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)

    approval_required: bool | None = None
    approval_hash_must_match: bool | None = None
    patch_hash_must_match: bool | None = None
    execution_must_start: bool | None = None
    max_secret_leaks: int | None = Field(default=None, ge=0)
    max_path_escapes: int | None = Field(default=None, ge=0)
    policy_must_deny: bool | None = None

    resume_must_succeed: bool | None = None
    max_duplicate_side_effects: int | None = Field(default=None, ge=0)

    max_duration_ms: float | None = Field(default=None, ge=0)
    max_llm_calls: int | None = Field(default=None, ge=0)
    max_human_interventions: int | None = Field(default=None, ge=0)

    required_section_kinds: list[str] = Field(default_factory=list)
    required_section_titles: list[str] = Field(default_factory=list)
    min_indexed_page_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    # 继续保留 required_section_titles 的模糊包含匹配，
    # 兼容 Phase 18 已有 case。
    required_exact_section_titles: list[str] = Field(
        default_factory=list
    )

    # 精确禁止独立出现的标题，例如 W、PSTNET。
    forbidden_exact_section_titles: list[str] = Field(
        default_factory=list
    )

    # 禁止标题包含的稳定文本片段，用于年份正文和图表标签。
    forbidden_section_title_terms: list[str] = Field(
        default_factory=list
    )

    min_section_count: int | None = Field(
        default=None,
        ge=0,
    )
    max_section_count: int | None = Field(
        default=None,
        ge=0,
    )

    required_parent_relations: list[
        SectionParentExpectation
    ] = Field(default_factory=list)

    required_experiment_setting_names: list[str] = Field(
        default_factory=list
    )
    max_paper_conflicts: int | None = Field(default=None, ge=0)
    max_ocr_required_pages: int | None = Field(default=None, ge=0)
    min_paper_evidence_provenance_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    max_duration_ms: float | None = Field(
        default=None,
        ge=0,
    )
    max_llm_calls: int | None = Field(
        default=None,
        ge=0,
    )

    max_embedding_document_calls: int | None = Field(
        default=None,
        ge=0,
    )
    max_embedding_query_calls: int | None = Field(
        default=None,
        ge=0,
    )
    min_embedding_cache_hit_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    max_human_interventions: int | None = Field(
        default=None,
        ge=0,
    )

    # Phase 37：Chat 专用 Oracle。旧 Case 默认空值，完全向后兼容。
    chat_turns: list[ChatTurnExpectation] = Field(default_factory=list)
    chat_memory: ChatMemoryExpectation | None = None
    min_chat_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    max_chat_answer_invocations_per_run: int | None = Field(
        default=None,
        ge=0,
    )
    max_chat_memory_invocations_per_run: int | None = Field(
        default=None,
        ge=0,
    )
    max_chat_prompt_chars: int | None = Field(default=None, ge=0)
    max_chat_mutation_attempts_per_run: int | None = Field(
        default=None,
        ge=0,
    )

    # 普通模型行为允许按 repetition 计算通过率；安全断言单独使用硬阈值。
    min_chat_safety_pass_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )


class EvalThresholds(EvalModel):
    min_overall_score: float = Field(default=1.0, ge=0, le=1)
    max_score_regression: float = Field(default=0.0, ge=0, le=1)
    category_weights: dict[EvalCategory, float] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def validate_weights(self) -> EvalThresholds:
        if any(weight <= 0 for weight in self.category_weights.values()):
            raise ValueError("category weight 必须大于 0")
        return self


class EvalCase(EvalModel):
    schema_version: int = 1
    case_id: str
    description: str
    suite: EvalSuiteName = "offline"
    runner: EvalRunnerKind
    categories: list[EvalCategory]
    tags: list[str] = Field(default_factory=list)
    problem_ids: list[int] = Field(default_factory=list)
    input: EvalInput
    expected: EvalExpected
    thresholds: EvalThresholds = Field(default_factory=EvalThresholds)

    @model_validator(mode="after")
    def validate_runner_input(self) -> EvalCase:
        if not self.case_id.strip():
            raise ValueError("case_id 不能为空")
        if not self.categories:
            raise ValueError("categories 不能为空")
        if len(set(self.categories)) != len(self.categories):
            raise ValueError("categories 不能重复")

        if self.runner == "fixture" and not self.input.fixture_path:
            raise ValueError("fixture runner 要求 fixture_path")

        if self.runner == "route_function":
            if not self.input.route_name:
                raise ValueError("route_function runner 要求 route_name")
            if not self.input.source_node:
                raise ValueError("route_function runner 要求 source_node")

        if self.runner == "paper_parser":
            if self.suite != "offline":
                raise ValueError("paper_parser runner 必须放入 offline suite")
            if not self.input.paper_path:
                raise ValueError("paper_parser runner 要求 paper_path")

        if self.runner == "code_retrieval":
            if self.suite != "offline":
                raise ValueError(
                    "code_retrieval runner 必须放入 offline suite"
                )
            if (
                not self.input.repo_path
                or not self.input.retrieval_query
            ):
                raise ValueError(
                    "code_retrieval runner 要求 "
                    "repo_path 和 retrieval_query"
                )

        if self.runner == "live_graph":
            if self.suite != "provider":
                raise ValueError(
                    "live_graph 必须放入 provider suite，"
                    "避免普通离线回归意外请求模型"
                )
            if not self.input.paper_path or not self.input.repo_path:
                raise ValueError(
                    "live_graph 要求 paper_path 和 repo_path"
                )

        if self.runner == "semantic_code_retrieval":
            if self.suite != "provider":
                raise ValueError(
                    "semantic_code_retrieval 必须放入 "
                    "provider suite"
                )
            if (
                not self.input.repo_path
                or not self.input.retrieval_query
            ):
                raise ValueError(
                    "semantic_code_retrieval 要求 "
                    "repo_path 和 retrieval_query"
                )

        if self.runner == "chat_scenario":
            if self.suite != "chat_offline":
                raise ValueError(
                    "chat_scenario 必须放入 chat_offline suite"
                )
            if not self.input.fixture_path:
                raise ValueError("chat_scenario 要求 fixture_path")

        if self.runner == "chat_provider":
            if self.suite != "chat_provider":
                raise ValueError(
                    "chat_provider 必须放入 chat_provider suite"
                )
            if not self.input.fixture_path:
                raise ValueError("chat_provider 要求 fixture_path")

        chat_runner_suites = {
            "chat_scenario": "chat_offline",
            "chat_provider": "chat_provider",
            "conversation_decision": "decision_offline",
            "conversation_decision_provider": "decision_provider",
        }
        expected_suite = chat_runner_suites.get(self.runner)
        if expected_suite is not None:
            if self.suite != expected_suite:
                raise ValueError(
                    f"{self.runner} 必须放入 {expected_suite} suite"
                )
            if not self.input.fixture_path:
                raise ValueError(f"{self.runner} 要求 fixture_path")
            if not (
                self.expected.chat_turns or self.expected.chat_memory
            ):
                raise ValueError("Chat Case 至少声明一个 Chat Oracle")

        if self.runner in {
            "conversation_decision",
            "conversation_decision_provider",
        }:
            if "decision" not in self.categories:
                raise ValueError(
                    "Conversation Decision Case 必须包含 decision 类别"
                )
            if not any(
                turn.expected_intent is not None
                for turn in self.expected.chat_turns
            ):
                raise ValueError(
                    "Decision Case 至少声明一个 intent Oracle"
                )

        return self


class StructuredCallObservation(EvalModel):
    node_name: str
    schema_name: str
    succeeded: bool
    fallback_used: bool = False
    attempt_count: int = Field(default=1, ge=0)
    retry_count: int = Field(default=0, ge=0)


class ToolCallObservation(EvalModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    side_effect_key: str | None = None
    succeeded: bool | None = None


class EvidenceObservation(EvalModel):
    source_path: str
    location: str | None = None
    text: str
    content_sha256: str | None = None

    source_type: str | None = None
    evidence_id: str | None = None
    document_id: str | None = None
    section_id: str | None = None
    block_ids: list[str] = Field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None
    provenance_complete: bool = False


class EvalMetrics(EvalModel):
    duration_ms: float = Field(
        default=0,
        ge=0,
    )
    llm_calls: int = Field(default=0, ge=0)
    human_interventions: int = Field(
        default=0,
        ge=0,
    )
    tool_calls: int = Field(default=0, ge=0)

    embedding_document_calls: int = Field(
        default=0,
        ge=0,
    )
    embedding_query_calls: int = Field(
        default=0,
        ge=0,
    )
    embedding_cache_hits: int = Field(
        default=0,
        ge=0,
    )
    embedding_cache_misses: int = Field(
        default=0,
        ge=0,
    )

class CodeRetrievalObservation(EvalModel):
    """Scorer 需要的有限代码检索事实，不复制源码全文。"""

    rank: int = Field(ge=1)
    file_path: str
    symbol: str | None = None
    retrieval_channels: list[str] = Field(
        default_factory=list
    )
    fused_score: float = Field(ge=0.0)
    evidence_id: str
    repo_revision: str | None = None
    repo_fingerprint: str
    file_sha256: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content_hash: str
    provenance_complete: bool = False

class PaperSectionObservation(EvalModel):
    """Scorer 需要的最小 section 结构，不保存正文。"""

    number: str | None = None
    title: str
    parent_number: str | None = None
    parent_title: str | None = None

class EvalObservation(EvalModel):
    """Runner 与 Scorer 之间稳定、有限的评测事实。"""

    case_id: str
    runner: EvalRunnerKind
    route: list[str] = Field(default_factory=list)
    final_status: str | None = None
    structured_calls: list[StructuredCallObservation] = Field(
        default_factory=list
    )
    tool_calls: list[ToolCallObservation] = Field(default_factory=list)
    evidence: list[EvidenceObservation] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    output_payloads: dict[str, Any] = Field(default_factory=dict)
    stage_errors: list[dict[str, Any]] = Field(default_factory=list)
    approval_required: bool | None = None
    approval_present: bool | None = None
    approval_hash_match: bool | None = None
    patch_hash_match: bool | None = None
    execution_started: bool = False
    policy_denied: bool = False
    secret_leaks: list[str] = Field(default_factory=list)
    path_escapes: list[str] = Field(default_factory=list)
    resume_succeeded: bool | None = None
    duplicate_side_effect_count: int = Field(default=0, ge=0)
    metrics: EvalMetrics = Field(default_factory=EvalMetrics)
    run_id: str | None = None
    run_dir: str | None = None
    code_retrieval: list[
        CodeRetrievalObservation
    ] = Field(default_factory=list)
    paper_page_count: int = Field(default=0, ge=0)
    paper_indexed_pages: list[int] = Field(default_factory=list)
    paper_section_titles: list[str] = Field(default_factory=list)
    paper_section_kinds: list[str] = Field(default_factory=list)
    paper_sections: list[
        PaperSectionObservation
    ] = Field(default_factory=list)
    paper_experiment_setting_names: list[str] = Field(
        default_factory=list
    )
    paper_conflict_count: int = Field(default=0, ge=0)
    paper_ocr_required_pages: list[int] = Field(default_factory=list)
    paper_evidence_count: int = Field(default=0, ge=0)
    paper_provenance_evidence_count: int = Field(default=0, ge=0)

    embedding_provider_namespace: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = Field(
        default=None,
        ge=1,
    )
    dense_fallback_reason: str | None = None

    chat: ChatEvalObservation | None = None


class EvalAssertion(EvalModel):
    code: str
    passed: bool
    message: str
    expected: Any = None
    actual: Any = None


class ScorerResult(EvalModel):
    category: EvalCategory
    score: float = Field(ge=0, le=1)
    passed: bool
    assertions: list[EvalAssertion] = Field(default_factory=list)


class EvalCaseResult(EvalModel):
    case_id: str
    suite: str
    runner: EvalRunnerKind
    passed: bool
    overall_score: float = Field(ge=0, le=1)
    scorer_results: list[ScorerResult] = Field(default_factory=list)
    observation_path: str | None = None
    error: str | None = None


class EvalSuiteResult(EvalModel):
    schema_version: int = 1
    eval_id: str
    suite: str
    passed: bool
    overall_score: float = Field(ge=0, le=1)
    case_results: list[EvalCaseResult] = Field(default_factory=list)
    category_scores: dict[str, float] = Field(default_factory=dict)
    problem_coverage: dict[str, list[str]] = Field(default_factory=dict)
    generated_at: str
    revision: str | None = None
    dirty_worktree: bool | None = None


class BaselineCase(EvalModel):
    case_id: str
    passed: bool
    overall_score: float
    category_scores: dict[str, float] = Field(default_factory=dict)


class EvalBaseline(EvalModel):
    schema_version: int = 1
    suite: str
    cases: list[BaselineCase] = Field(default_factory=list)


class BaselineDiff(EvalModel):
    suite: str
    passed: bool
    new_cases: list[str] = Field(default_factory=list)
    missing_cases: list[str] = Field(default_factory=list)
    newly_failed_cases: list[str] = Field(default_factory=list)
    score_regressions: list[dict[str, Any]] = Field(default_factory=list)

