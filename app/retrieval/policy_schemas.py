from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.retrieval.schemas import (
    ChannelHit,
    RetrievalChannel,
)

RetrievalPolicyMode = Literal[
    "off",
    "shadow",
    "active",
]

RetrievalQueryKind = Literal[
    "exact_error",
    "symbol_path",
    "semantic_alignment",
    "diagnostic",
    "mixed",
]


class RetrievalPolicyModel(BaseModel):
    """所有策略对象拒绝未知字段，避免配置拼写错误被静默忽略。"""

    model_config = ConfigDict(extra="forbid")


class RetrievalQueryFeatures(RetrievalPolicyModel):
    """只保存确定性特征和 query hash，不复制原始查询正文。"""

    query_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    query_kind: RetrievalQueryKind
    token_count: int = Field(ge=0)
    keyword_count: int = Field(ge=0)
    paper_evidence_count: int = Field(ge=0)
    preferred_path_count: int = Field(ge=0)

    has_error_signature: bool = False
    has_symbol_hint: bool = False
    has_path_hint: bool = False
    has_traceback_path: bool = False
    has_semantic_description: bool = False

    feature_version: str = "phase47-v1"


class RetrievalProfile(RetrievalPolicyModel):
    """一组经过评测的检索通道、融合权重和资源上限。"""

    profile_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]{2,63}$",
    )
    profile_version: str
    description: str

    enabled_channels: list[RetrievalChannel] = Field(
        min_length=1,
    )
    channel_weights: dict[RetrievalChannel, float]

    top_k: int = Field(default=8, ge=1, le=50)
    rrf_k: int = Field(default=60, ge=1, le=500)
    requires_dense: bool = False

    # 这些预算同时用于离线门禁和运行时审计。
    max_duration_ms: float = Field(default=3000, gt=0)
    max_embedding_query_calls: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_profile(self) -> RetrievalProfile:
        if len(set(self.enabled_channels)) != len(
            self.enabled_channels
        ):
            raise ValueError("enabled_channels 不能重复")

        unknown_weights = set(self.channel_weights) - set(
            self.enabled_channels
        )
        if unknown_weights:
            raise ValueError(
                "channel_weights 包含未启用通道："
                f"{sorted(unknown_weights)}"
            )
        if any(value <= 0 for value in self.channel_weights.values()):
            raise ValueError("所有 channel weight 必须大于 0")

        if self.requires_dense and "dense" not in self.enabled_channels:
            raise ValueError(
                "requires_dense=true 时必须启用 dense 通道"
            )
        if (
            "dense" not in self.enabled_channels
            and self.max_embedding_query_calls != 0
        ):
            raise ValueError(
                "不含 dense 的 profile 不能声明 embedding 调用预算"
            )
        if (
            "import_graph" in self.enabled_channels
            and "symbol" not in self.enabled_channels
        ):
            raise ValueError(
                "import_graph 依赖 symbol 种子，必须同时启用 symbol"
            )
        return self


class RetrievalPolicyRule(RetrievalPolicyModel):
    rule_id: str = Field(
        pattern=r"^[a-z][a-z0-9_]{2,63}$",
    )
    priority: int = Field(ge=0, le=10000)
    query_kinds: list[RetrievalQueryKind] = Field(min_length=1)
    profile_id: str
    requires_dense_available: bool = False

    @model_validator(mode="after")
    def validate_query_kinds(self) -> RetrievalPolicyRule:
        if len(set(self.query_kinds)) != len(self.query_kinds):
            raise ValueError("rule query_kinds 不能重复")
        return self


class RetrievalPolicyConfig(RetrievalPolicyModel):
    schema_version: str = "phase47-v1"
    policy_version: str
    default_profile_id: str
    fallback_profile_id: str
    profiles: list[RetrievalProfile] = Field(min_length=1)
    rules: list[RetrievalPolicyRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> RetrievalPolicyConfig:
        profile_ids = [item.profile_id for item in self.profiles]
        if len(set(profile_ids)) != len(profile_ids):
            raise ValueError("profile_id 不能重复")

        known = set(profile_ids)
        if self.default_profile_id not in known:
            raise ValueError("default_profile_id 不存在")
        if self.fallback_profile_id not in known:
            raise ValueError("fallback_profile_id 不存在")

        fallback = next(
            item
            for item in self.profiles
            if item.profile_id == self.fallback_profile_id
        )
        if fallback.requires_dense or "dense" in fallback.enabled_channels:
            raise ValueError("fallback profile 必须完全离线可用")

        rule_ids = [item.rule_id for item in self.rules]
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("rule_id 不能重复")
        for rule in self.rules:
            if rule.profile_id not in known:
                raise ValueError(
                    f"rule 引用了未知 profile：{rule.profile_id}"
                )
        return self


class RetrievalDecision(RetrievalPolicyModel):
    """运行时可持久化审计记录，不保存 query 正文和源码。"""

    decision_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    policy_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    profile_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )

    policy_version: str
    mode: RetrievalPolicyMode
    applied: bool
    selected_profile: RetrievalProfile
    query_features: RetrievalQueryFeatures
    reason_codes: list[str] = Field(default_factory=list)
    dense_available: bool
    fallback_used: bool = False


class RetrievalPolicyGoldenCase(RetrievalPolicyModel):
    """独立于通用 EvalCase 的窄型检索策略 Golden Case。"""

    case_id: str
    description: str
    repo_path: str
    query: str
    keywords: list[str] = Field(default_factory=list)
    preferred_paths: list[str] = Field(default_factory=list)
    paper_evidence_count: int = Field(default=0, ge=0)
    expected_query_kind: RetrievalQueryKind

    required_paths: list[str] = Field(min_length=1)
    forbidden_paths: list[str] = Field(default_factory=list)
    baseline_profile_id: str
    challenger_profile_ids: list[str] = Field(min_length=1)

    # 离线 Case 可以提供固定 dense hit，只评测 fusion，不调用 Provider。
    simulated_dense_hits: list[ChannelHit] = Field(default_factory=list)


class RetrievalProfileCaseMetrics(RetrievalPolicyModel):
    case_id: str
    profile_id: str
    query_kind: RetrievalQueryKind
    recall_at_k: float = Field(ge=0, le=1)
    mean_reciprocal_rank: float = Field(ge=0, le=1)
    citation_coverage: float = Field(ge=0, le=1)
    provenance_ratio: float = Field(ge=0, le=1)
    forbidden_path_count: int = Field(ge=0)
    duration_ms: float = Field(ge=0)
    observed_paths: list[str] = Field(default_factory=list)
    passed_hard_gate: bool


class RetrievalProfileAggregate(RetrievalPolicyModel):
    profile_id: str
    case_count: int = Field(ge=1)
    mean_recall_at_k: float = Field(ge=0, le=1)
    mean_reciprocal_rank: float = Field(ge=0, le=1)
    mean_citation_coverage: float = Field(ge=0, le=1)
    mean_provenance_ratio: float = Field(ge=0, le=1)
    mean_duration_ms: float = Field(ge=0)
    hard_gate_passed: bool


class RetrievalPromotionProposal(RetrievalPolicyModel):
    proposal_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    policy_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    case_id: str
    baseline_profile_id: str
    challenger_profile_id: str
    eligible: bool
    reason_codes: list[str] = Field(default_factory=list)
    # proposed 只表示等待人工检查，不能自动写生产配置。
    status: Literal["proposed"] = "proposed"


class RetrievalPolicyEvalReport(RetrievalPolicyModel):
    eval_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    policy_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    generated_at: str
    case_metrics: list[RetrievalProfileCaseMetrics]
    profile_aggregates: list[RetrievalProfileAggregate]
    promotion_proposals: list[RetrievalPromotionProposal]
