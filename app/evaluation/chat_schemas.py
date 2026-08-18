from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.chat.schemas import (
    ChatCitation,
    ChatDecisionIntent,
    ChatDraft,
    ChatRequestableOperationKind,
    MemoryDraft,
    MemoryStatement,
)
from app.interaction.schemas import (
    AllowedOperation,
    DecisionKind,
    OperationKind,
)
from app.job_runtime.schemas import JobStatus


class ChatEvalModel(BaseModel):
    """Chat Eval 的 fixture、expectation 和 observation 都拒绝未知字段。"""

    model_config = ConfigDict(extra="forbid")


class ChatEvalSource(ChatEvalModel):
    """合成 Grounding Source；Provider case 也只能看到这里的内容。"""

    citation: ChatCitation
    content: str = Field(min_length=1, max_length=50000)
    score: int = 100


class ChatEvalSeedExchange(ChatEvalModel):
    """直接写入隔离 Chat Store 的历史，不消耗 Provider 调用。"""

    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=6000)
    citation_ids: list[str] = Field(default_factory=list, max_length=8)


class ChatEvalMemoryScript(ChatEvalModel):
    """Offline Memory Invoker 的一次结果：成功 Draft 或受控错误二选一。"""

    draft: MemoryDraft | None = None
    error_code: Literal[
        "provider_unavailable",
        "structured_output_invalid",
    ] | None = None

    @model_validator(mode="after")
    def validate_exactly_one_result(self) -> "ChatEvalMemoryScript":
        if (self.draft is None) == (self.error_code is None):
            raise ValueError("Memory script 必须且只能设置 draft/error_code")
        return self


class ChatEvalTurn(ChatEvalModel):
    """一轮真正通过 ChatService.ask() 的评测问题。"""

    label: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=4000)
    idempotency_key: str = Field(min_length=1, max_length=300)
    # chat_offline 必须提供；chat_provider 必须为空。
    scripted_draft: ChatDraft | None = None


class ChatEvalScenario(ChatEvalModel):
    schema_version: int = 2
    scenario_id: str = Field(min_length=1, max_length=200)
    job_status: JobStatus = "running"

    # 让 Scenario 可以构造 stale-safe 的公开 JobView。
    job_version: int = Field(default=1, ge=0)
    wait_generation: int = Field(default=0, ge=0)
    allowed_operations: list[AllowedOperation] = Field(
        default_factory=list,
        max_length=8,
    )

    sources: list[ChatEvalSource] = Field(min_length=1, max_length=16)
    seed_exchanges: list[ChatEvalSeedExchange] = Field(
        default_factory=list,
        max_length=200,
    )
    turns: list[ChatEvalTurn] = Field(min_length=1, max_length=12)
    memory_scripts: list[ChatEvalMemoryScript] = Field(
        default_factory=list,
        max_length=12,
    )
    repetitions: int = Field(default=1, ge=1, le=5)

    compaction_enabled: bool = True
    recent_messages: int = Field(default=4, ge=2, le=100)
    compaction_min_messages: int = Field(default=4, ge=2, le=100)
    compaction_max_messages: int = Field(default=40, ge=2, le=500)
    compaction_max_input_chars: int = Field(default=20000, ge=4000)
    memory_max_chars: int = Field(default=8000, ge=2000)
    history_max_chars: int = Field(default=8000, ge=1000)
    prompt_max_chars: int = Field(default=40000, ge=4000)

    @model_validator(mode="after")
    def validate_scenario_identity(self) -> "ChatEvalScenario":
        citation_ids = [
            item.citation.citation_id for item in self.sources
        ]
        if len(set(citation_ids)) != len(citation_ids):
            raise ValueError("Scenario citation_id 不能重复")
        first = self.sources[0].citation
        if first.citation_id != "job:current" or first.source_type != "job":
            raise ValueError("第一个 Source 必须是 job:current")

        known = set(citation_ids)
        for exchange in self.seed_exchanges:
            unknown = set(exchange.citation_ids) - known
            if unknown:
                raise ValueError(
                    f"Seed Exchange 使用未知 citation：{sorted(unknown)}"
                )

        labels = [item.label for item in self.turns]
        if len(set(labels)) != len(labels):
            raise ValueError("Turn label 不能重复")
        keys = [item.idempotency_key for item in self.turns]
        if len(set(keys)) != len(keys):
            raise ValueError("Turn idempotency_key 不能重复")

        even_values = {
            "recent_messages": self.recent_messages,
            "compaction_min_messages": self.compaction_min_messages,
            "compaction_max_messages": self.compaction_max_messages,
        }
        for name, value in even_values.items():
            if value % 2 != 0:
                raise ValueError(f"{name} 必须为偶数")
        if self.compaction_max_messages < self.compaction_min_messages:
            raise ValueError("compaction max 不能小于 min")
        if self.prompt_max_chars <= max(
            self.memory_max_chars,
            self.history_max_chars,
        ):
            raise ValueError(
                "prompt budget 必须分别大于 memory/history budget"
            )

        operation_ids = [
            item.operation_id for item in self.allowed_operations
        ]
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError(
                "AllowedOperation operation_id 不能重复"
            )

        for operation in self.allowed_operations:
            if operation.expected_job_version != self.job_version:
                raise ValueError(
                    "AllowedOperation expected_job_version 与 Scenario 不一致"
                )
            if (
                operation.kind == "submit_decision"
                and operation.expected_wait_generation
                != self.wait_generation
            ):
                raise ValueError(
                    "submit_decision wait_generation 与 Scenario 不一致"
                )
        return self


class ChatTurnExpectation(ChatEvalModel):
    """对同一 label 的 Turn 在所有 repetitions 上计算通过率。"""

    label: str
    required_answer_terms: list[str] = Field(default_factory=list)
    # 每个内层列表至少命中一个，例如 ["running", "运行中"]。
    required_answer_any_groups: list[list[str]] = Field(default_factory=list)
    forbidden_answer_terms: list[str] = Field(default_factory=list)
    forbidden_safety_terms: list[str] = Field(default_factory=list)
    required_citation_ids: list[str] = Field(default_factory=list)
    forbidden_citation_ids: list[str] = Field(default_factory=list)
    # None 表示不检查；[] 表示最终回答不允许有任何 Citation。
    allowed_citation_ids: list[str] | None = None
    expected_refusal: bool | None = None
    expected_unknown_requested_citations: int | None = Field(
        default=None,
        ge=0,
    )

    # Phase 42：对模型意图与服务端 Capability 投影做 Oracle。
    expected_intent: ChatDecisionIntent | None = None
    expected_operation_kind: ChatRequestableOperationKind | None = None
    expected_decision_kind: DecisionKind | None = None
    expected_operation_availability: Literal[
        "not_requested",
        "available",
        "unavailable",
        "ambiguous",
    ] | None = None

    @model_validator(mode="after")
    def validate_non_vacuous_oracle(self) -> "ChatTurnExpectation":
        term_fields = {
            "required_answer_terms": self.required_answer_terms,
            "forbidden_answer_terms": self.forbidden_answer_terms,
            "forbidden_safety_terms": self.forbidden_safety_terms,
        }
        for name, values in term_fields.items():
            if any(not item.strip() for item in values):
                raise ValueError(f"{name} 不允许空字符串")

        for group in self.required_answer_any_groups:
            if not group or any(not item.strip() for item in group):
                raise ValueError(
                    "required_answer_any_groups 不允许空组或空术语"
                )

        citation_fields = [
            self.required_citation_ids,
            self.forbidden_citation_ids,
            self.allowed_citation_ids or [],
        ]
        if any(
            not item.strip()
            for values in citation_fields
            for item in values
        ):
            raise ValueError("Citation Oracle 不允许空 ID")

        required = set(self.required_citation_ids)
        forbidden = set(self.forbidden_citation_ids)
        if required & forbidden:
            raise ValueError("required/forbidden Citation 不能重叠")
        if (
            self.allowed_citation_ids is not None
            and not required <= set(self.allowed_citation_ids)
        ):
            raise ValueError("required Citation 必须属于 allowlist")
        return self

    @model_validator(mode="after")
    def validate_decision_oracle(self) -> "ChatTurnExpectation":
        if self.expected_intent == "operation_request":
            if self.expected_operation_kind is None:
                raise ValueError(
                    "operation_request Oracle 必须设置 operation kind"
                )
        elif self.expected_operation_kind is not None:
            raise ValueError(
                "非 operation_request Oracle 不能设置 operation kind"
            )

        if self.expected_operation_kind == "submit_decision":
            if self.expected_decision_kind is None:
                raise ValueError(
                    "submit_decision Oracle 必须设置 decision kind"
                )
        elif self.expected_decision_kind is not None:
            raise ValueError(
                "非 submit_decision Oracle 不能设置 decision kind"
            )
        return self


class ChatMemoryExpectation(ChatEvalModel):
    expected_available: bool | None = None
    min_version: int | None = Field(default=None, ge=1)
    required_summary_terms: list[str] = Field(default_factory=list)
    required_constraint_terms: list[str] = Field(default_factory=list)
    forbidden_constraint_terms: list[str] = Field(default_factory=list)
    required_decision_terms: list[str] = Field(default_factory=list)
    forbidden_decision_terms: list[str] = Field(default_factory=list)
    required_open_question_terms: list[str] = Field(default_factory=list)
    forbidden_open_question_terms: list[str] = Field(default_factory=list)
    required_citation_ids: list[str] = Field(default_factory=list)
    forbidden_citation_ids: list[str] = Field(default_factory=list)
    require_hash_valid: bool | None = None
    min_source_sequence_valid_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    min_degraded_turns: int | None = Field(default=None, ge=0)
    max_degraded_turns: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_memory_oracle(self) -> "ChatMemoryExpectation":
        term_fields = [
            self.required_summary_terms,
            self.required_constraint_terms,
            self.forbidden_constraint_terms,
            self.required_decision_terms,
            self.forbidden_decision_terms,
            self.required_open_question_terms,
            self.forbidden_open_question_terms,
        ]
        if any(
            not item.strip()
            for values in term_fields
            for item in values
        ):
            raise ValueError("Memory Oracle 不允许空术语")

        required = set(self.required_citation_ids)
        forbidden = set(self.forbidden_citation_ids)
        if required & forbidden:
            raise ValueError(
                "Memory required/forbidden Citation 不能重叠"
            )
        if (
            self.min_degraded_turns is not None
            and self.max_degraded_turns is not None
            and self.min_degraded_turns > self.max_degraded_turns
        ):
            raise ValueError("Memory degraded min 不能大于 max")
        return self


class ChatTurnObservation(ChatEvalModel):
    label: str
    answer: str
    citation_ids: list[str] = Field(default_factory=list)
    requested_citation_ids: list[str] = Field(default_factory=list)
    prompt_source_ids: list[str] = Field(default_factory=list)
    unknown_requested_citation_ids: list[str] = Field(default_factory=list)
    model_marked_insufficient: bool = False
    refused: bool = False
    replayed: bool = False
    memory_available: bool = False
    memory_degraded: bool = False

    predicted_intent: ChatDecisionIntent = "read_only"
    requested_operation_kind: OperationKind | None = None
    requested_decision_kind: DecisionKind | None = None
    operation_availability: Literal[
        "not_requested",
        "available",
        "unavailable",
        "ambiguous",
    ] = "not_requested"


class ChatMemoryObservation(ChatEvalModel):
    available: bool = False
    version: int | None = None
    covered_through_sequence: int = 0
    summary: str = ""
    user_constraints: list[MemoryStatement] = Field(default_factory=list)
    decisions: list[MemoryStatement] = Field(default_factory=list)
    open_questions: list[MemoryStatement] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    hash_valid: bool = False
    source_sequence_valid_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


class ChatScenarioRunObservation(ChatEvalModel):
    repetition: int = Field(ge=1)
    turns: list[ChatTurnObservation] = Field(default_factory=list)
    memory: ChatMemoryObservation = Field(
        default_factory=ChatMemoryObservation
    )
    raw_message_count: int = Field(default=0, ge=0)
    answer_invocations: int = Field(default=0, ge=0)
    memory_invocations: int = Field(default=0, ge=0)
    degraded_turns: int = Field(default=0, ge=0)
    max_prompt_chars: int = Field(default=0, ge=0)
    duration_ms: float = Field(default=0.0, ge=0.0)

    # StaticInteraction 记录所有意外 mutation 尝试。
    mutation_attempts: int = Field(default=0, ge=0)


class ChatEvalObservation(ChatEvalModel):
    scenario_id: str
    mode: Literal["offline", "provider"]
    runs: list[ChatScenarioRunObservation] = Field(min_length=1, max_length=5)
