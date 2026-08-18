from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.chat.context import ChatContextBuilder, GroundingBundle
from app.tool_calling.schemas import (
    EmptyToolInput,
    EvidenceToolOutput,
    InspectFailureContextInput,
    SearchReproductionEvidenceInput,
    ToolEvidenceItem,
)
from app.tool_contracts.registry import (
    ToolRegistry,
    build_tool_definition,
)
from app.tool_contracts.schemas import (
    ToolDeterminism,
    ToolEffect,
    ToolErrorSpec,
    ToolExposure,
    ToolFailure,
    ToolInvocationContext,
    ToolRisk,
)

if TYPE_CHECKING:
    from app.mcp_gateway.tool_adapter import McpEvidenceGatewayPort

VERSION = "phase52-v1"
MAX_TOOL_RESULT_CHARS = 12000


@dataclass(frozen=True)
class ChatEvidenceToolBindings:
    context_builder: ChatContextBuilder
    mcp_gateway: "McpEvidenceGatewayPort | None" = None


def _require_job_id(context: ToolInvocationContext) -> str:
    if context.job_id is None or not context.job_id.strip():
        raise ValueError("missing job_id")
    return context.job_id


def _bounded_output(
    *,
    bundle: GroundingBundle,
    summary: str,
    source_types: set[str] | None,
    limit: int,
) -> EvidenceToolOutput:
    items: list[ToolEvidenceItem] = []
    used_chars = 0
    truncated = False
    for source in bundle.sources:
        if source_types is not None and source.citation.source_type not in source_types:
            continue
        if len(items) >= limit:
            truncated = True
            break
        content = source.content[:6000]
        if used_chars + len(content) > MAX_TOOL_RESULT_CHARS:
            truncated = True
            continue
        if not content.strip():
            continue
        items.append(ToolEvidenceItem(citation=source.citation, content=content))
        used_chars += len(content)
    return EvidenceToolOutput(summary=summary, items=items, truncated=truncated)


def _map_evidence_error(exc: BaseException) -> ToolFailure | None:
    if isinstance(exc, ValueError):
        return ToolFailure(
            code="TOOL_EVIDENCE_SCOPE_INVALID",
            category="policy",
            retryable=False,
            message="Tool missing valid Job Scope",
        )
    if isinstance(exc, (FileNotFoundError, PermissionError, OSError)):
        return ToolFailure(
            code="TOOL_EVIDENCE_UNAVAILABLE",
            category="environment",
            retryable=False,
            message="Job evidence temporarily unavailable",
        )
    return None


EVIDENCE_ERRORS = [
    ToolErrorSpec(
        code="TOOL_EVIDENCE_SCOPE_INVALID",
        category="policy",
        retryable=False,
        summary="Trusted context has no Job Scope",
    ),
    ToolErrorSpec(
        code="TOOL_EVIDENCE_UNAVAILABLE",
        category="environment",
        retryable=False,
        summary="Job public evidence cannot be read",
    ),
]


def build_chat_evidence_tool_registry(
    bindings: ChatEvidenceToolBindings,
) -> ToolRegistry:
    registry = ToolRegistry()

    def get_status(payload: EmptyToolInput, context: ToolInvocationContext) -> EvidenceToolOutput:
        del payload
        job_id = _require_job_id(context)
        bundle = bindings.context_builder.build_job_only(job_id=job_id, question="status")
        return _bounded_output(bundle=bundle, summary="Current Job status", source_types={"job"}, limit=1)

    registry.register(
        build_tool_definition(
            name="chat.get_reproduction_status",
            version=VERSION,
            summary="Read current reproduction Job status",
            input_model=EmptyToolInput,
            output_model=EvidenceToolOutput,
            handler=get_status,
            error_mapper=_map_evidence_error,
            effects=[ToolEffect.DATASTORE_READ],
            required_capabilities=["job.read.current"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.chat.get_reproduction_status",
            path_scopes=[],
            declared_errors=EVIDENCE_ERRORS,
        )
    )

    def search_evidence(payload: SearchReproductionEvidenceInput, context: ToolInvocationContext) -> EvidenceToolOutput:
        job_id = _require_job_id(context)
        bundle = bindings.context_builder.build(job_id=job_id, question=payload.query)
        return _bounded_output(bundle=bundle, summary="Evidence matching query", source_types=set(payload.source_types), limit=payload.limit)

    registry.register(
        build_tool_definition(
            name="chat.search_reproduction_evidence",
            version=VERSION,
            summary="Search reproduction evidence by query",
            input_model=SearchReproductionEvidenceInput,
            output_model=EvidenceToolOutput,
            handler=search_evidence,
            error_mapper=_map_evidence_error,
            effects=[ToolEffect.DATASTORE_READ, ToolEffect.FILESYSTEM_READ],
            required_capabilities=["job.read.current", "run.read.evidence"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.chat.search_reproduction_evidence",
            path_scopes=["run"],
            declared_errors=EVIDENCE_ERRORS,
        )
    )

    def inspect_failure(payload: InspectFailureContextInput, context: ToolInvocationContext) -> EvidenceToolOutput:
        job_id = _require_job_id(context)
        query = "failure error traceback debug_report final_report " + payload.focus
        bundle = bindings.context_builder.build(job_id=job_id, question=query)
        return _bounded_output(bundle=bundle, summary="Failure diagnostic context", source_types={"job", "event", "log", "artifact"}, limit=payload.limit)

    registry.register(
        build_tool_definition(
            name="chat.inspect_failure_context",
            version=VERSION,
            summary="Read failure context for current Job",
            input_model=InspectFailureContextInput,
            output_model=EvidenceToolOutput,
            handler=inspect_failure,
            error_mapper=_map_evidence_error,
            effects=[ToolEffect.DATASTORE_READ, ToolEffect.FILESYSTEM_READ],
            required_capabilities=["job.read.current", "run.read.evidence"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.chat.inspect_failure_context",
            path_scopes=["run"],
            declared_errors=EVIDENCE_ERRORS,
        )
    )

    if bindings.mcp_gateway is not None:
        from app.mcp_gateway.tool_adapter import register_mcp_evidence_tool

        register_mcp_evidence_tool(
            registry=registry,
            gateway=bindings.mcp_gateway,
        )

    return registry
