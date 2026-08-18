from __future__ import annotations

from types import SimpleNamespace

from app.chat.context import GroundingBundle, GroundingSource
from app.chat.schemas import ChatCitation
from app.tool_calling.evidence_tools import (
    ChatEvidenceToolBindings,
    build_chat_evidence_tool_registry,
)
from app.tool_contracts.schemas import ToolInvocationContext


class FakeContextBuilder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def _bundle(self, job_id: str) -> GroundingBundle:
        return GroundingBundle(
            job=SimpleNamespace(job_id=job_id, status="failed"),
            sources=[
                GroundingSource(
                    citation=ChatCitation(
                        citation_id="job:current",
                        source_type="job",
                        label="Current job state",
                        locator="version 1",
                    ),
                    content='{"status":"failed"}',
                    score=100,
                )
            ],
        )

    def build_job_only(self, *, job_id: str, question: str):
        self.calls.append(("job_only", job_id, question))
        return self._bundle(job_id)

    def build(self, *, job_id: str, question: str):
        self.calls.append(("full", job_id, question))
        return self._bundle(job_id)


def _context(job_id: str = "job-server") -> ToolInvocationContext:
    return ToolInvocationContext(
        actor="test",
        request_id="request-1",
        caller_kind="agent",
        job_id=job_id,
        granted_capabilities={
            "job.read.current",
            "run.read.evidence",
        },
    )


def test_status_tool_uses_server_job_scope() -> None:
    builder = FakeContextBuilder()
    registry = build_chat_evidence_tool_registry(
        ChatEvidenceToolBindings(context_builder=builder)
    )

    result = registry.invoke(
        name="chat.get_reproduction_status",
        raw_input={},
        context=_context(),
    )

    assert result.failure is None
    assert builder.calls[0][1] == "job-server"
    assert result.record.job_id == "job-server"


def test_model_job_id_is_rejected_before_context_builder() -> None:
    builder = FakeContextBuilder()
    registry = build_chat_evidence_tool_registry(
        ChatEvidenceToolBindings(context_builder=builder)
    )

    result = registry.invoke(
        name="chat.get_reproduction_status",
        raw_input={"job_id": "job-attacker"},
        context=_context(),
    )

    assert result.failure is not None
    assert result.failure.code == "TOOL_INPUT_INVALID"
    assert builder.calls == []


def test_missing_server_job_scope_fails_closed() -> None:
    builder = FakeContextBuilder()
    registry = build_chat_evidence_tool_registry(
        ChatEvidenceToolBindings(context_builder=builder)
    )

    result = registry.invoke(
        name="chat.get_reproduction_status",
        raw_input={},
        context=_context(job_id="").model_copy(update={"job_id": None}),
    )

    assert result.failure is not None
    assert result.failure.code == "TOOL_EVIDENCE_SCOPE_INVALID"
    assert builder.calls == []
