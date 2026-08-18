from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.chat.schemas import ChatCitation


class ToolCallingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


EvidenceSourceType = Literal[
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


def _safe_query(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValueError("query 不能为空")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("query 不能包含控制字符")
    return normalized


class EmptyToolInput(ToolCallingModel):
    """无模型参数；当前 Job 由 ToolInvocationContext 注入。"""


class SearchReproductionEvidenceInput(ToolCallingModel):
    query: str = Field(min_length=1, max_length=500)
    source_types: list[EvidenceSourceType] = Field(
        default_factory=lambda: [
            "event",
            "artifact",
            "log",
            "comparison",
            "project_fact",
            "knowledge",
            "web",
        ],
        min_length=1,
        max_length=8,
    )
    limit: int = Field(default=5, ge=1, le=6)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return _safe_query(value)

    @field_validator("source_types")
    @classmethod
    def validate_source_types(
        cls,
        values: list[EvidenceSourceType],
    ) -> list[EvidenceSourceType]:
        if len(values) != len(set(values)):
            raise ValueError("source_types 不能重复")
        return values


class InspectFailureContextInput(ToolCallingModel):
    focus: str = Field(default="当前失败原因", min_length=1, max_length=300)
    limit: int = Field(default=5, ge=1, le=6)

    @field_validator("focus")
    @classmethod
    def validate_focus(cls, value: str) -> str:
        return _safe_query(value)


class ToolEvidenceItem(ToolCallingModel):
    """可进入最终 Grounding 的服务端证据。"""

    citation: ChatCitation
    content: str = Field(min_length=1, max_length=6000)


class EvidenceToolOutput(ToolCallingModel):
    summary: str = Field(min_length=1, max_length=500)
    items: list[ToolEvidenceItem] = Field(default_factory=list, max_length=6)
    truncated: bool = False


class ProviderToolSpec(ToolCallingModel):
    """交给 Provider 的最小工具投影，不包含内部权限字段。"""

    type: Literal["function"] = "function"
    function: dict[str, Any]

    @model_validator(mode="after")
    def validate_function_shape(self) -> "ProviderToolSpec":
        if set(self.function) != {
            "name",
            "description",
            "parameters",
            "strict",
        }:
            raise ValueError("Provider function schema 字段不完整")
        if self.function["strict"] is not True:
            raise ValueError("Provider tool 必须使用 strict schema")
        return self


class ProviderToolBinding(ToolCallingModel):
    alias: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    internal_name: str = Field(
        pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
    )
    spec: ProviderToolSpec


class ProviderToolCatalog(ToolCallingModel):
    version: Literal["phase52-v1"] = "phase52-v1"
    bindings: list[ProviderToolBinding] = Field(min_length=1, max_length=8)
    catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_unique_bindings(self) -> "ProviderToolCatalog":
        aliases = [item.alias for item in self.bindings]
        names = [item.internal_name for item in self.bindings]
        if len(aliases) != len(set(aliases)):
            raise ValueError("Provider Tool alias 不能重复")
        if len(names) != len(set(names)):
            raise ValueError("内部 Tool name 不能重复")
        return self

    def by_alias(self, alias: str) -> ProviderToolBinding | None:
        return next(
            (item for item in self.bindings if item.alias == alias),
            None,
        )


class NormalizedToolCall(ToolCallingModel):
    provider_call_id: str = Field(min_length=1, max_length=200)
    alias: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    arguments: dict[str, Any]


ToolLoopStatus = Literal[
    "disabled",
    "no_tools_needed",
    "completed",
    "limit_reached",
    "policy_blocked",
    "planner_unavailable",
]


class ToolLoopCallTrace(ToolCallingModel):
    round_index: int = Field(ge=1, le=10)
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


class ToolLoopTrace(ToolCallingModel):
    trace_id: str = Field(pattern=r"^tooltrace_[0-9a-f]{24}$")
    version: Literal["phase52-v1"] = "phase52-v1"
    job_id: str
    status: ToolLoopStatus
    catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_invocation_ids: list[str] = Field(default_factory=list, max_length=4)
    calls: list[ToolLoopCallTrace] = Field(default_factory=list, max_length=3)
    started_at: str
    finished_at: str
    trace_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_call_count(self) -> "ToolLoopTrace":
        if len(self.calls) > 3:
            raise ValueError("Tool Loop 调用数超过第一版上限")
        return self
