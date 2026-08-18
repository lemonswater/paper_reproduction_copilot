"""Chat schema：消息、citation、draft 和 API 响应。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.interaction.schemas import (
    AllowedOperation,
    DecisionKind,
)

ChatRole = Literal["user", "assistant"]
CitationSourceType = Literal[
    "job",
    "event",
    "artifact",
    "log",
    "comparison",
    "project_fact",
    "knowledge",
    "web",
    "mcp",
]


class ChatModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatCitation(ChatModel):
    """服务端根据本地 GroundingSource 构造，不能直接相信模型字段。"""

    citation_id: str
    source_type: CitationSourceType
    label: str
    artifact_id: str | None = None
    relative_path: str | None = None
    artifact_sha256: str | None = None
    event_id: int | None = None
    locator: str | None = None

    # Phase 38：只暴露内容身份与两端 Job，不返回 Comparison 文件路径。
    comparison_id: str | None = Field(
        default=None,
        pattern=r"^comparison_[0-9a-f]{24}$",
    )
    comparison_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    base_job_id: str | None = None
    target_job_id: str | None = None

    # Phase 46：Project Fact citation 身份。
    project_id: str | None = Field(
        default=None,
        pattern=r"^project_[0-9a-f]{24}$",
    )
    project_fact_id: str | None = Field(
        default=None,
        pattern=r"^fact_[0-9a-f]{24}$",
    )
    project_fact_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )

    # Phase 49：Knowledge Query Pack 中的稳定 Subject 引用。
    knowledge_pack_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    knowledge_subject_id: str | None = Field(
        default=None,
        pattern=r"^kg(?:ent|rel)_[0-9a-f]{24}$",
    )
    knowledge_subject_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    knowledge_evidence_ref_ids: list[str] = Field(
        default_factory=list,
        max_length=64,
    )

    # Phase 51：Web 引用绑定 Research Pack、Snapshot 和 excerpt 内容身份。
    research_pack_id: str | None = Field(
        default=None,
        pattern=r"^rpack_[0-9a-f]{24}$",
    )
    research_pack_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    research_snapshot_id: str | None = Field(
        default=None,
        pattern=r"^rsnap_[0-9a-f]{24}$",
    )
    research_snapshot_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    research_citation_id: str | None = Field(
        default=None,
        pattern=r"^rcit_[0-9a-f]{24}$",
    )
    research_excerpt_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    canonical_url: str | None = None

    # Phase 53：MCP 证据绑定本地 Profile、Schema、Pack 和 Item。
    mcp_server_id: str | None = Field(
        default=None,
        pattern=r"^mcpserver_[a-z0-9][a-z0-9_-]{2,63}$",
    )
    mcp_binding_id: str | None = Field(
        default=None,
        pattern=r"^mcpbind_[a-z0-9][a-z0-9_-]{2,63}$",
    )
    mcp_profile_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    mcp_input_schema_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    mcp_output_schema_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    mcp_pack_id: str | None = Field(
        default=None,
        pattern=r"^mcppack_[0-9a-f]{24}$",
    )
    mcp_pack_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    mcp_item_id: str | None = Field(
        default=None,
        pattern=r"^mcpitem_[0-9a-f]{24}$",
    )
    mcp_item_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    mcp_source_uri: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_citation_identity(self) -> "ChatCitation":
        comparison_values = (
            self.comparison_id,
            self.comparison_hash,
            self.base_job_id,
            self.target_job_id,
        )
        project_values = (
            self.project_id,
            self.project_fact_id,
            self.project_fact_hash,
        )
        if self.source_type == "comparison":
            if any(value is None for value in comparison_values):
                raise ValueError(
                    "comparison citation 必须包含完整 comparison identity"
                )
        elif any(value is not None for value in comparison_values):
            raise ValueError(
                "非 comparison citation 不能携带 comparison identity"
            )
        if self.source_type == "project_fact":
            if any(value is None for value in project_values):
                raise ValueError(
                    "project_fact citation 必须包含完整事实身份"
                )
        elif any(value is not None for value in project_values):
            raise ValueError(
                "非 project_fact citation 不能携带项目事实身份"
            )
        knowledge_values = (
            self.knowledge_pack_hash,
            self.knowledge_subject_id,
            self.knowledge_subject_hash,
        )
        if self.source_type == "knowledge":
            if any(value is None for value in knowledge_values):
                raise ValueError(
                    "knowledge citation 必须包含 Pack/Subject identity"
                )
            if not self.knowledge_evidence_ref_ids:
                raise ValueError(
                    "knowledge citation 必须包含 Evidence Ref"
                )
            if len(self.knowledge_evidence_ref_ids) != len(
                set(self.knowledge_evidence_ref_ids)
            ):
                raise ValueError("knowledge Evidence Ref 不能重复")
        elif any(value is not None for value in knowledge_values) or (
            self.knowledge_evidence_ref_ids
        ):
            raise ValueError(
                "非 knowledge citation 不能携带 Knowledge identity"
            )
        web_values = (
            self.research_pack_id,
            self.research_pack_hash,
            self.research_snapshot_id,
            self.research_snapshot_sha256,
            self.research_citation_id,
            self.research_excerpt_sha256,
            self.canonical_url,
        )
        if self.source_type == "web":
            if any(value is None for value in web_values):
                raise ValueError(
                    "web citation 必须包含完整 Research identity"
                )
        elif any(value is not None for value in web_values):
            raise ValueError(
                "非 web citation 不能携带 Research identity"
            )
        mcp_values = (
            self.mcp_server_id,
            self.mcp_binding_id,
            self.mcp_profile_sha256,
            self.mcp_input_schema_sha256,
            self.mcp_output_schema_sha256,
            self.mcp_pack_id,
            self.mcp_pack_sha256,
            self.mcp_item_id,
            self.mcp_item_sha256,
            self.mcp_source_uri,
        )
        if self.source_type == "mcp":
            if any(value is None for value in mcp_values):
                raise ValueError(
                    "mcp citation 必须包含完整 Profile/Schema/Pack/Item identity"
                )
        elif any(value is not None for value in mcp_values):
            raise ValueError(
                "非 mcp citation 不能携带 MCP identity"
            )
        return self


ChatToolLoopStatus = Literal[
    "disabled",
    "no_tools_needed",
    "completed",
    "limit_reached",
    "policy_blocked",
    "planner_unavailable",
]


class ChatToolCallSummary(ChatModel):
    call_id: str
    tool_name: str
    status: Literal["succeeded", "failed", "blocked"]
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    error_code: str | None = None
    citation_ids: list[str] = Field(default_factory=list, max_length=8)


class ChatToolTraceSummary(ChatModel):
    trace_id: str = Field(pattern=r"^tooltrace_[0-9a-f]{24}$")
    version: Literal["phase52-v1"] = "phase52-v1"
    status: ChatToolLoopStatus
    catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    calls: list[ChatToolCallSummary] = Field(default_factory=list, max_length=3)
    trace_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ChatMessage(ChatModel):
    message_id: str
    job_id: str
    sequence: int = Field(ge=1)
    role: ChatRole
    content: str = Field(min_length=1, max_length=6000)
    citations: list[ChatCitation] = Field(default_factory=list)
    tool_trace: ChatToolTraceSummary | None = None
    reply_to: str | None = None
    created_at: str

    @model_validator(mode="after")
    def validate_tool_trace_role(self) -> "ChatMessage":
        if self.role == "user" and self.tool_trace is not None:
            raise ValueError("user message 不能携带 Tool Trace")
        return self


class ChatMessagePage(ChatModel):
    items: list[ChatMessage]
    next_after: int = Field(ge=0)


class ChatAskRequest(ChatModel):
    question: str = Field(min_length=1, max_length=4000)


ChatDecisionIntent = Literal[
    "read_only",
    "operation_request",
    "unknown",
]

# Chat 只允许“请求”用户可主动发起的操作类型。
# operator_reconciliation_required 是提示状态，不是 Chat 可请求的动作。
ChatRequestableOperationKind = Literal[
    "submit_decision",
    "cancel",
    "create_rerun_proposal",
]


class ChatRequestedOperation(ChatModel):
    """LLM 输出的非权威操作分类，不包含任何可执行身份。"""

    kind: ChatRequestableOperationKind
    decision_kind: DecisionKind | None = None

    @model_validator(mode="after")
    def validate_decision_kind(self) -> "ChatRequestedOperation":
        if self.kind == "submit_decision":
            if self.decision_kind is None:
                raise ValueError(
                    "submit_decision 必须说明 decision_kind"
                )
        elif self.decision_kind is not None:
            raise ValueError(
                "非 submit_decision 不能携带 decision_kind"
            )
        return self


class ChatDraft(ChatModel):
    """LLM 唯一允许返回的结构。

    intent/requested_operation 仅用于解释和评测。ChatService 不会把它们
    转换成 DecisionEnvelope，也不会据此调用任何 mutation。
    """

    answer: str = Field(min_length=1, max_length=6000)
    citation_ids: list[str] = Field(default_factory=list, max_length=8)
    insufficient_evidence: bool = False

    # 默认 read_only 让 Phase 37 的旧离线 Fixture 保持兼容。
    # 新的 Provider Prompt 会要求模型显式填写。
    intent: ChatDecisionIntent = "read_only"
    requested_operation: ChatRequestedOperation | None = None

    @model_validator(mode="after")
    def validate_operation_intent(self) -> "ChatDraft":
        if self.intent == "operation_request":
            if self.requested_operation is None:
                raise ValueError(
                    "operation_request 必须携带 requested_operation"
                )
        elif self.requested_operation is not None:
            raise ValueError(
                "read_only/unknown 不能携带 requested_operation"
            )
        return self


class MemoryStatement(ChatModel):
    """一条可追溯到原始消息 sequence 的会话信息。"""

    text: str = Field(min_length=1, max_length=1000)
    source_sequences: list[int] = Field(
        min_length=1,
        max_length=8,
    )


class MemoryDraft(ChatModel):
    """LLM 只返回候选内容和 ID，不返回持久化 identity。"""

    summary: str = Field(min_length=1, max_length=4000)
    user_constraints: list[MemoryStatement] = Field(
        default_factory=list,
        max_length=20,
    )
    decisions: list[MemoryStatement] = Field(
        default_factory=list,
        max_length=20,
    )
    open_questions: list[MemoryStatement] = Field(
        default_factory=list,
        max_length=20,
    )
    citation_ids_to_preserve: list[str] = Field(
        default_factory=list,
        max_length=32,
    )


class ConversationMemoryBody(ChatModel):
    summary: str = Field(min_length=1, max_length=4000)
    user_constraints: list[MemoryStatement] = Field(
        default_factory=list,
        max_length=20,
    )
    decisions: list[MemoryStatement] = Field(
        default_factory=list,
        max_length=20,
    )
    open_questions: list[MemoryStatement] = Field(
        default_factory=list,
        max_length=20,
    )
    # 完整 citation 由服务端从原消息/parent memory 投影。
    citation_anchors: list[ChatCitation] = Field(
        default_factory=list,
        max_length=32,
    )
    # 旧 body JSON 没有该字段，默认值必须保持 phase36-v1。
    citation_schema_version: Literal[
        "phase36-v1",
        "phase38-v2",
        "phase46-v3",
        "phase49-v4",
        "phase51-v5",
    ] = "phase36-v1"

    @model_validator(mode="after")
    def validate_citation_schema(self) -> "ConversationMemoryBody":
        if self.citation_schema_version == "phase36-v1" and any(
            item.source_type == "comparison"
            for item in self.citation_anchors
        ):
            raise ValueError(
                "comparison citation 必须使用 phase38-v2 memory body"
            )
        if (
            self.citation_schema_version
            in ("phase36-v1", "phase38-v2")
            and any(
                item.source_type == "project_fact"
                for item in self.citation_anchors
            )
        ):
            raise ValueError(
                "project_fact citation 必须使用 phase46-v3 memory body"
            )
        if (
            self.citation_schema_version != "phase49-v4"
            and self.citation_schema_version != "phase51-v5"
            and any(
                item.source_type == "knowledge"
                for item in self.citation_anchors
            )
        ):
            raise ValueError(
                "knowledge citation 必须使用 phase49-v4 memory body"
            )
        if (
            self.citation_schema_version != "phase51-v5"
            and any(
                item.source_type == "web"
                for item in self.citation_anchors
            )
        ):
            raise ValueError(
                "web citation 必须使用 phase51-v5 memory body"
            )
        return self


class ConversationMemory(ChatModel):
    memory_id: str
    job_id: str
    version: int = Field(ge=1)
    covered_from_sequence: int = Field(ge=1)
    covered_through_sequence: int = Field(ge=2)
    delta_messages_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parent_memory_id: str | None = None
    parent_memory_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    body: ConversationMemoryBody
    memory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_version: str
    model_name: str
    structured_method: str
    strict: bool
    created_at: str


class ConversationMemoryView(ChatModel):
    """公开透明视图，不返回 Provider 配置和内部 delta hash。"""

    job_id: str
    version: int
    covered_through_sequence: int
    summary: str
    user_constraints: list[MemoryStatement]
    decisions: list[MemoryStatement]
    open_questions: list[MemoryStatement]
    citation_anchors: list[ChatCitation]
    memory_sha256: str
    created_at: str

    @classmethod
    def from_memory(
        cls,
        memory: ConversationMemory,
    ) -> "ConversationMemoryView":
        return cls(
            job_id=memory.job_id,
            version=memory.version,
            covered_through_sequence=memory.covered_through_sequence,
            summary=memory.body.summary,
            user_constraints=memory.body.user_constraints,
            decisions=memory.body.decisions,
            open_questions=memory.body.open_questions,
            citation_anchors=memory.body.citation_anchors,
            memory_sha256=memory.memory_sha256,
            created_at=memory.created_at,
        )


class ChatMemoryStatus(ChatModel):
    enabled: bool
    available: bool
    version: int | None = None
    covered_through_sequence: int = 0
    degraded: bool = False


class ChatAskResponse(ChatModel):
    user_message: ChatMessage
    assistant_message: ChatMessage
    replayed: bool = False
    # 只返回当前服务端 capability；Chat Agent 不生成、更不执行 operation。
    allowed_operations: list[AllowedOperation] = Field(
        default_factory=list
    )
    memory: ChatMemoryStatus = Field(
        default_factory=lambda: ChatMemoryStatus(
            enabled=False,
            available=False,
        )
    )
