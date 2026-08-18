from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


SHA256_PATTERN = r"^[0-9a-f]{64}$"

ModelRoutingMode = Literal["off", "shadow", "active"]
ModelWorkloadKind = Literal["chat", "embedding"]
ModelQualityTier = Literal["economy", "balanced", "high"]
ModelCapability = Literal[
    "structured_json_schema",
    "structured_function_calling",
    "structured_json_mode",
    "long_context",
    "tool_calling",
    "embedding",
]
ModelBillingMode = Literal["priced", "free", "unpriced"]
ModelUsageQuality = Literal[
    "provider_reported",
    "estimated",
    "reservation_upper_bound",
    "not_applicable",
]
ModelInvocationStatus = Literal[
    "reserved",
    "succeeded",
    "failed",
    "usage_unknown",
]

# 每个真实模型调用点都必须选择一个稳定 task_kind。
ModelTaskKind = Literal[
    "paper_section_extraction",
    "paper_code_mapping",
    "experiment_plan",
    "failure_debug",
    "repair_plan",
    "file_repair_plan",
    "chat_answer",
    "chat_tool_selection",
    "chat_memory_compaction",
    "code_embedding_document",
    "code_embedding_query",
    "evaluation_probe",
    "web_research_synthesis",
]


class RoutingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelPricing(RoutingModel):
    """价格单位是每一百万 Token 对应的 micro USD。"""

    pricing_version: str = Field(min_length=1, max_length=100)
    billing_mode: ModelBillingMode
    input_micro_usd_per_million: int | None = Field(default=None, ge=0)
    output_micro_usd_per_million: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_price_shape(self) -> "ModelPricing":
        if self.billing_mode == "priced":
            if (
                self.input_micro_usd_per_million is None
                or self.output_micro_usd_per_million is None
            ):
                raise ValueError("priced profile 必须提供 input/output 价格")
        elif self.billing_mode == "free":
            if self.input_micro_usd_per_million not in {None, 0}:
                raise ValueError("free profile 的 input 价格必须为 0 或 null")
            if self.output_micro_usd_per_million not in {None, 0}:
                raise ValueError("free profile 的 output 价格必须为 0 或 null")
        else:
            if (
                self.input_micro_usd_per_million is not None
                or self.output_micro_usd_per_million is not None
            ):
                raise ValueError("unpriced profile 不能携带猜测价格")
        return self


class ModelProfile(RoutingModel):
    profile_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,79}$")
    workload_kind: ModelWorkloadKind
    # 第一版只允许这两个 Python 代码内的受信任 binding。
    provider_binding: Literal["primary_chat", "primary_embedding"]
    # Catalog Loader 会把 $OPENAI_MODEL / $EMBEDDING_MODEL 替换成真实值。
    model_name: str = Field(min_length=1, max_length=200)
    quality_tier: ModelQualityTier
    quality_rank: int = Field(ge=0, le=100)
    capabilities: set[ModelCapability] = Field(default_factory=set)
    context_window_tokens: int = Field(ge=1)
    max_output_tokens: int = Field(ge=0)
    thinking_mode: Literal["disabled", "enabled"] | None = None
    enabled: bool = True
    pricing: ModelPricing

    @model_validator(mode="after")
    def validate_workload(self) -> "ModelProfile":
        if self.workload_kind == "embedding":
            if self.provider_binding != "primary_embedding":
                raise ValueError("embedding profile 必须使用 primary_embedding")
            if "embedding" not in self.capabilities:
                raise ValueError("embedding profile 必须声明 embedding capability")
            if self.max_output_tokens != 0:
                raise ValueError("embedding profile 的 max_output_tokens 必须为 0")
            if self.thinking_mode is not None:
                raise ValueError("embedding profile 不支持 thinking_mode")
        else:
            if self.provider_binding != "primary_chat":
                raise ValueError("chat profile 必须使用 primary_chat")
            if "embedding" in self.capabilities:
                raise ValueError("chat profile 不能声明 embedding capability")
            if self.max_output_tokens < 1:
                raise ValueError("chat profile 的 max_output_tokens 必须大于 0")
        return self


class ModelTaskRoute(RoutingModel):
    task_kind: ModelTaskKind
    workload_kind: ModelWorkloadKind
    required_capabilities: set[ModelCapability] = Field(default_factory=set)
    # 顺序即确定性优先级，不按运行时随机排序。
    candidate_profile_ids: list[str] = Field(min_length=1, max_length=20)
    # off/shadow 执行这个 Profile，以保持旧行为。
    legacy_profile_id: str = Field(min_length=1, max_length=80)
    minimum_quality_rank: int = Field(ge=0, le=100)
    max_input_tokens: int = Field(ge=1)
    max_output_tokens: int = Field(ge=0)
    validation_max_retries: int = Field(ge=0, le=5)
    provider_max_retries: int = Field(ge=0, le=5)

    @field_validator("candidate_profile_ids")
    @classmethod
    def validate_candidate_ids(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("candidate_profile_ids 不能重复")
        return values

    @model_validator(mode="after")
    def validate_embedding_limits(self) -> "ModelTaskRoute":
        if self.workload_kind == "embedding":
            if self.max_output_tokens != 0:
                raise ValueError("embedding route 的 max_output_tokens 必须为 0")
            if self.required_capabilities != {"embedding"}:
                raise ValueError("embedding route 必须且只能要求 embedding")
        return self


class ModelBudgetPolicy(RoutingModel):
    # None 表示不设置该维度，而不是无限的价格已知。
    daily_total_token_limit: int | None = Field(default=None, ge=1)
    daily_cost_limit_micro_usd: int | None = Field(default=None, ge=0)
    per_job_total_token_limit: int | None = Field(default=None, ge=1)
    per_job_cost_limit_micro_usd: int | None = Field(default=None, ge=0)
    reservation_ttl_seconds: int = Field(default=900, ge=30, le=86400)
    allow_unpriced_in_active: bool = False


class ModelRoutingDocument(RoutingModel):
    schema_version: Literal["phase50-v1"] = "phase50-v1"
    policy_version: str = Field(min_length=1, max_length=100)
    profiles: list[ModelProfile] = Field(min_length=1, max_length=100)
    routes: list[ModelTaskRoute] = Field(min_length=1, max_length=100)
    budget: ModelBudgetPolicy


class ModelRouteRequest(RoutingModel):
    schema_version: Literal["phase50-v1"] = "phase50-v1"
    task_kind: ModelTaskKind
    workload_kind: ModelWorkloadKind
    required_capabilities: set[ModelCapability] = Field(default_factory=set)
    requested_quality_tier: ModelQualityTier = "balanced"
    estimated_input_tokens: int = Field(ge=1)
    requested_max_output_tokens: int = Field(ge=0)
    prompt_sha256: str = Field(pattern=SHA256_PATTERN)
    prompt_chars: int = Field(ge=0)
    schema_name: str | None = Field(default=None, max_length=200)
    schema_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    job_id: str | None = Field(default=None, max_length=200)
    run_id: str | None = Field(default=None, max_length=300)
    node_name: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_workload_shape(self) -> "ModelRouteRequest":
        if self.workload_kind == "embedding":
            if self.requested_max_output_tokens != 0:
                raise ValueError("embedding request 不能申请 output token")
            if self.schema_name is not None or self.schema_sha256 is not None:
                raise ValueError("embedding request 不能携带 structured schema")
        elif (self.schema_name is None) != (self.schema_sha256 is None):
            raise ValueError("schema_name 与 schema_sha256 必须同时出现")
        return self


class ModelRouteDecision(RoutingModel):
    schema_version: Literal["phase50-v1"] = "phase50-v1"
    mode: ModelRoutingMode
    request_sha256: str = Field(pattern=SHA256_PATTERN)
    policy_sha256: str = Field(pattern=SHA256_PATTERN)
    selected_profile_id: str
    executed_profile_id: str
    selected_model_name: str
    executed_model_name: str
    pricing_version: str
    reason_codes: list[str] = Field(min_length=1, max_length=20)
    max_billable_attempts: int = Field(ge=1)
    decision_sha256: str = Field(pattern=SHA256_PATTERN)


class ModelReservationRequest(RoutingModel):
    invocation_id: str = Field(pattern=r"^mdl_[0-9a-f]{32}$")
    request_sha256: str = Field(pattern=SHA256_PATTERN)
    decision_sha256: str = Field(pattern=SHA256_PATTERN)
    task_kind: ModelTaskKind
    job_id: str | None = Field(default=None, max_length=200)
    run_id: str | None = Field(default=None, max_length=300)
    node_name: str = Field(min_length=1, max_length=120)
    profile_id: str = Field(min_length=1, max_length=80)
    model_name: str = Field(min_length=1, max_length=200)
    pricing_version: str = Field(min_length=1, max_length=100)
    enforced: bool
    reserved_input_tokens: int = Field(ge=0)
    reserved_output_tokens: int = Field(ge=0)
    reserved_cost_micro_usd: int | None = Field(default=None, ge=0)
    prompt_chars: int = Field(ge=0)
    prompt_sha256: str = Field(pattern=SHA256_PATTERN)
    schema_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    lease_expires_at: str

    @property
    def reserved_total_tokens(self) -> int:
        return self.reserved_input_tokens + self.reserved_output_tokens


class ModelUsage(RoutingModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost_micro_usd: int | None = Field(default=None, ge=0)
    quality: ModelUsageQuality
    provider_response_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> "ModelUsage":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens 必须等于 input_tokens + output_tokens")
        return self


class ModelInvocationRecord(RoutingModel):
    invocation_id: str = Field(pattern=r"^mdl_[0-9a-f]{32}$")
    request_sha256: str = Field(pattern=SHA256_PATTERN)
    decision_sha256: str = Field(pattern=SHA256_PATTERN)
    task_kind: ModelTaskKind
    job_id: str | None
    run_id: str | None
    node_name: str
    profile_id: str
    model_name: str
    pricing_version: str
    enforced: bool
    status: ModelInvocationStatus
    reserved_input_tokens: int = Field(ge=0)
    reserved_output_tokens: int = Field(ge=0)
    reserved_cost_micro_usd: int | None = Field(default=None, ge=0)
    actual_input_tokens: int | None = Field(default=None, ge=0)
    actual_output_tokens: int | None = Field(default=None, ge=0)
    actual_cost_micro_usd: int | None = Field(default=None, ge=0)
    usage_quality: ModelUsageQuality | None = None
    provider_response_count: int | None = Field(default=None, ge=0)
    prompt_chars: int = Field(ge=0)
    prompt_sha256: str = Field(pattern=SHA256_PATTERN)
    schema_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    latency_ms: int | None = Field(default=None, ge=0)
    error_code: str | None = Field(default=None, max_length=120)
    created_at: str
    updated_at: str
    lease_expires_at: str


class ModelBudgetSummary(RoutingModel):
    utc_date: str
    job_id: str | None = None
    settled_input_tokens: int = Field(ge=0)
    settled_output_tokens: int = Field(ge=0)
    active_reserved_tokens: int = Field(ge=0)
    settled_cost_micro_usd: int = Field(ge=0)
    active_reserved_cost_micro_usd: int = Field(ge=0)
    invocation_count: int = Field(ge=0)
    active_reservation_count: int = Field(ge=0)
    unpriced_invocation_count: int = Field(ge=0)


class ModelRoutingEvaluationCase(RoutingModel):
    case_id: str = Field(min_length=1, max_length=200)
    request: ModelRouteRequest
    expected_profile_id: str
    forbidden_profile_ids: list[str] = Field(default_factory=list)


class ModelRoutingEvaluationReport(RoutingModel):
    suite_version: str
    policy_sha256: str = Field(pattern=SHA256_PATTERN)
    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_case_ids: list[str]
    route_accuracy: float = Field(ge=0.0, le=1.0)
    passed: bool


class ModelProfilePromotionProposal(RoutingModel):
    """只是一份 Proposal；不能自动覆盖生产 policy。"""

    proposal_id: str = Field(pattern=r"^mdlprom_[0-9a-f]{24}$")
    task_kind: ModelTaskKind
    baseline_profile_id: str
    challenger_profile_id: str
    baseline_policy_sha256: str = Field(pattern=SHA256_PATTERN)
    eval_report_sha256: str = Field(pattern=SHA256_PATTERN)
    quality_gate_passed: bool
    estimated_saving_percent: float | None = Field(default=None, ge=0.0, le=100.0)
    requires_explicit_user_review: Literal[True] = True
