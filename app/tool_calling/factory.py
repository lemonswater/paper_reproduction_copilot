from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.chat.context import ChatContextBuilder
from app.config import settings
from app.model_routing.factory import build_model_gateway
from app.tool_calling.catalog import (
    GRANTED_CAPABILITIES,
    SAFE_EFFECTS,
    STATIC_BINDINGS,
    build_provider_tool_catalog,
)
from app.tool_calling.evidence_tools import (
    ChatEvidenceToolBindings,
    build_chat_evidence_tool_registry,
)
from app.tool_calling.loop import BoundedToolCallingLoop
from app.tool_calling.model_adapter import GatewayToolTurnInvoker


def build_chat_tool_calling_loop(
    *,
    context_builder: ChatContextBuilder,
) -> BoundedToolCallingLoop:
    from app.tool_contracts.schemas import ToolEffect

    mcp_gateway = None
    static_bindings = dict(STATIC_BINDINGS)
    safe_effects = set(SAFE_EFFECTS)
    granted_capabilities = set(GRANTED_CAPABILITIES)
    authority_fingerprint = None

    if settings.mcp_gateway_enabled:
        from app.mcp_gateway.factory import build_read_only_mcp_gateway
        from app.mcp_gateway.tool_adapter import (
            MCP_CAPABILITY,
            MCP_INTERNAL_TOOL_NAME,
            MCP_PROVIDER_ALIAS,
        )

        mcp_gateway = build_read_only_mcp_gateway()
        static_bindings[MCP_PROVIDER_ALIAS] = MCP_INTERNAL_TOOL_NAME
        safe_effects.add(ToolEffect.NETWORK_READ)
        granted_capabilities.add(MCP_CAPABILITY)
        authority_fingerprint = mcp_gateway.authority_fingerprint

    registry = build_chat_evidence_tool_registry(
        ChatEvidenceToolBindings(
            context_builder=context_builder,
            mcp_gateway=mcp_gateway,
        )
    )
    catalog = build_provider_tool_catalog(
        registry,
        static_bindings=static_bindings,
        safe_effects=safe_effects,
        granted_capabilities=granted_capabilities,
        authority_fingerprint=authority_fingerprint,
    )
    return BoundedToolCallingLoop(
        registry=registry,
        catalog=catalog,
        turn_invoker=GatewayToolTurnInvoker(),
        max_model_rounds=settings.chat_tool_max_model_rounds,
        max_tool_calls=settings.chat_tool_max_calls,
        max_arguments_bytes=settings.chat_tool_max_arguments_bytes,
        max_single_result_chars=(
            settings.chat_tool_max_result_chars
        ),
        max_total_result_chars=(
            settings.chat_tool_total_result_chars
        ),
        granted_capabilities=granted_capabilities,
    )


class ToolCallingDoctorReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    ready: bool
    catalog_sha256: str | None = None
    tools: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


def doctor_chat_tool_calling(
    *,
    context_builder: ChatContextBuilder,
) -> ToolCallingDoctorReport:
    if not settings.chat_tool_calling_enabled:
        return ToolCallingDoctorReport(
            enabled=False,
            ready=False,
            issues=["chat_tool_calling_disabled"],
        )

    issues: list[str] = []
    try:
        registry = build_chat_evidence_tool_registry(
            ChatEvidenceToolBindings(context_builder=context_builder)
        )
        catalog = build_provider_tool_catalog(registry)
    except Exception as exc:
        return ToolCallingDoctorReport(
            enabled=True,
            ready=False,
            issues=[f"catalog_invalid:{type(exc).__name__}"],
        )

    # 只读取版本化 Model Catalog，不解析 Secret、不构造 Provider Client。
    try:
        gateway = build_model_gateway()
        route = gateway.router.catalog.route("chat_tool_selection")
        if "tool_calling" not in route.required_capabilities:
            issues.append("model_route_missing_tool_calling")
    except Exception as exc:
        issues.append(f"model_route_invalid:{type(exc).__name__}")

    return ToolCallingDoctorReport(
        enabled=True,
        ready=not issues,
        catalog_sha256=catalog.catalog_sha256,
        tools=[item.alias for item in catalog.bindings],
        issues=issues,
    )
