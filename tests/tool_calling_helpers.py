from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage

from app.chat.schemas import ChatCitation
from app.tool_calling.catalog import build_provider_tool_catalog
from app.tool_calling.model_adapter import (
    ToolModelTurn,
    normalize_tool_calls,
)
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
    ToolExposure,
    ToolRisk,
)


@dataclass
class HandlerRecorder:
    calls: list[tuple[str, str, dict]] = field(default_factory=list)


def _output(label: str) -> EvidenceToolOutput:
    return EvidenceToolOutput(
        summary=f"fixture:{label}",
        items=[
            ToolEvidenceItem(
                citation=ChatCitation(
                    citation_id="job:current",
                    source_type="job",
                    label="Current job state",
                    locator="version 1",
                ),
                content='{"status":"failed"}',
            )
        ],
    )


def build_fixture_registry(
    recorder: HandlerRecorder,
) -> ToolRegistry:
    registry = ToolRegistry()

    definitions = [
        (
            "chat.get_reproduction_status",
            EmptyToolInput,
            [ToolEffect.DATASTORE_READ],
            ["job.read.current"],
        ),
        (
            "chat.search_reproduction_evidence",
            SearchReproductionEvidenceInput,
            [ToolEffect.DATASTORE_READ, ToolEffect.FILESYSTEM_READ],
            ["job.read.current", "run.read.evidence"],
        ),
        (
            "chat.inspect_failure_context",
            InspectFailureContextInput,
            [ToolEffect.DATASTORE_READ, ToolEffect.FILESYSTEM_READ],
            ["job.read.current", "run.read.evidence"],
        ),
    ]

    for name, input_model, effects, capabilities in definitions:
        def handler(payload, context, tool_name=name):
            recorder.calls.append(
                (
                    tool_name,
                    context.job_id or "",
                    payload.model_dump(mode="json"),
                )
            )
            return _output(tool_name)

        registry.register(
            build_tool_definition(
                name=name,
                version="phase52-v1",
                summary=f"fixture tool {name}",
                input_model=input_model,
                output_model=EvidenceToolOutput,
                handler=handler,
                error_mapper=lambda exc: None,
                effects=effects,
                required_capabilities=capabilities,
                exposure=ToolExposure.AGENT_READ_ONLY,
                risk_level=ToolRisk.LOW,
                determinism=ToolDeterminism.DETERMINISTIC,
                idempotent=True,
                timeout_seconds=None,
                audit_event="tool.fixture.read",
                path_scopes=(
                    ["run"]
                    if ToolEffect.FILESYSTEM_READ in effects
                    else []
                ),
                declared_errors=[],
            )
        )
    return registry


def tool_call_message(
    alias: str,
    arguments: dict,
    *,
    call_id: str,
) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": alias,
                "args": arguments,
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def stop_message() -> AIMessage:
    return AIMessage(content="evidence is sufficient")


class ScriptedToolTurnInvoker:
    def __init__(self, messages: list[AIMessage]) -> None:
        self.messages = list(messages)
        self.received: list[list[BaseMessage]] = []

    def invoke(self, *, messages, catalog, job_id) -> ToolModelTurn:
        del catalog, job_id
        self.received.append(list(messages))
        if not self.messages:
            raise AssertionError("scripted tool turn 已耗尽")
        message = self.messages.pop(0)
        return ToolModelTurn(
            message=message,
            calls=normalize_tool_calls(message),
            invocation_id=None,
        )


def build_fixture_loop(
    *,
    invoker: ScriptedToolTurnInvoker,
    recorder: HandlerRecorder,
    max_model_rounds: int = 4,
    max_tool_calls: int = 3,
):
    from app.tool_calling.loop import BoundedToolCallingLoop

    registry = build_fixture_registry(recorder)
    return BoundedToolCallingLoop(
        registry=registry,
        catalog=build_provider_tool_catalog(registry),
        turn_invoker=invoker,
        max_model_rounds=max_model_rounds,
        max_tool_calls=max_tool_calls,
        max_arguments_bytes=8000,
        max_single_result_chars=12000,
        max_total_result_chars=24000,
    )
