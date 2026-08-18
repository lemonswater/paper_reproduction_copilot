from __future__ import annotations

from app.chat.schemas import ChatDraft
from app.mcp_gateway.gateway import ReadOnlyMcpEvidenceGateway
from app.mcp_gateway.repository import SqliteMcpEvidenceRepository
from app.mcp_gateway.tool_adapter import (
    MCP_CAPABILITY,
    MCP_INTERNAL_TOOL_NAME,
    MCP_PROVIDER_ALIAS,
    register_mcp_evidence_tool,
)
from app.tool_calling.catalog import build_provider_tool_catalog
from app.tool_calling.loop import BoundedToolCallingLoop
from app.tool_contracts.registry import ToolRegistry
from app.tool_contracts.schemas import ToolEffect
from tests.mcp_gateway_helpers import FakeMcpClient, make_policy
from tests.test_chat_service import _service
from tests.tool_calling_helpers import (
    ScriptedToolTurnInvoker,
    stop_message,
    tool_call_message,
)


def test_mcp_evidence_enters_final_chat_citation_allowlist(tmp_path) -> None:
    repository = SqliteMcpEvidenceRepository(tmp_path / "mcp.sqlite")
    repository.initialize()
    gateway = ReadOnlyMcpEvidenceGateway(
        policy=make_policy(),
        client=FakeMcpClient(),
        repository=repository,
    )
    registry = ToolRegistry()
    register_mcp_evidence_tool(registry=registry, gateway=gateway)
    catalog = build_provider_tool_catalog(
        registry,
        static_bindings={MCP_PROVIDER_ALIAS: MCP_INTERNAL_TOOL_NAME},
        safe_effects={ToolEffect.NETWORK_READ},
        granted_capabilities={MCP_CAPABILITY},
        authority_fingerprint=gateway.authority_fingerprint,
    )
    loop = BoundedToolCallingLoop(
        registry=registry,
        catalog=catalog,
        turn_invoker=ScriptedToolTurnInvoker(
            [
                tool_call_message(
                    MCP_PROVIDER_ALIAS,
                    {"query": "PSTNet", "limit": 1},
                    call_id="provider-mcp-call-1",
                ),
                stop_message(),
            ]
        ),
        max_model_rounds=4,
        max_tool_calls=3,
        max_arguments_bytes=8000,
        max_single_result_chars=12000,
        max_total_result_chars=24000,
        granted_capabilities={MCP_CAPABILITY},
    )

    expected_citation_id: list[str] = []

    def draft_invoker(prompt: str, job_id: str) -> ChatDraft:
        del job_id
        marker = "mcpcit_"
        start = prompt.index(marker)
        citation_id = prompt[start : start + len(marker) + 24]
        expected_citation_id.append(citation_id)
        return ChatDraft(
            answer="外部只读证据提到了 PSTNet。",
            citation_ids=[citation_id],
        )

    service = _service(
        tmp_path,
        draft_invoker,
        tool_loop=loop,
    )
    response = service.ask(
        job_id="job-1",
        question="有没有外部证据介绍 PSTNet？",
        idempotency_key="mcp-chat-1",
    )

    assert response.assistant_message.citations[0].source_type == "mcp"
    assert response.assistant_message.citations[0].citation_id == (
        expected_citation_id[0]
    )
    assert response.assistant_message.tool_trace is not None
    assert response.assistant_message.tool_trace.calls[0].tool_name == (
        MCP_INTERNAL_TOOL_NAME
    )
