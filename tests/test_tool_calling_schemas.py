from __future__ import annotations

import pytest

from app.tool_calling.schemas import (
    EmptyToolInput,
    EvidenceToolOutput,
    InspectFailureContextInput,
    NormalizedToolCall,
    ProviderToolBinding,
    ProviderToolCatalog,
    ProviderToolSpec,
    SearchReproductionEvidenceInput,
    ToolEvidenceItem,
    ToolLoopCallTrace,
    ToolLoopTrace,
)
from app.chat.schemas import ChatCitation


def test_empty_tool_input_accepts_no_fields() -> None:
    model = EmptyToolInput()
    assert model.model_dump() == {}


def test_search_input_rejects_empty_query() -> None:
    with pytest.raises(Exception):
        SearchReproductionEvidenceInput(query="")


def test_search_input_rejects_duplicate_source_types() -> None:
    with pytest.raises(Exception):
        SearchReproductionEvidenceInput(
            query="test",
            source_types=["job", "job"],
        )


def test_search_input_rejects_control_chars_in_query() -> None:
    with pytest.raises(Exception):
        SearchReproductionEvidenceInput(query="test\x00bad")


def test_inspect_failure_input_defaults() -> None:
    model = InspectFailureContextInput()
    assert model.focus == "当前失败原因"
    assert model.limit == 5


def test_inspect_failure_input_rejects_empty_focus() -> None:
    with pytest.raises(Exception):
        InspectFailureContextInput(focus="")


def test_tool_evidence_item_requires_content() -> None:
    citation = ChatCitation(
        citation_id="job:current",
        source_type="job",
        label="test",
    )
    with pytest.raises(Exception):
        ToolEvidenceItem(citation=citation, content="")


def test_evidence_tool_output_max_items() -> None:
    citation = ChatCitation(
        citation_id="job:current",
        source_type="job",
        label="test",
    )
    items = [
        ToolEvidenceItem(citation=citation, content=f"item {i}")
        for i in range(7)
    ]
    with pytest.raises(Exception):
        EvidenceToolOutput(summary="test", items=items)


def test_provider_tool_spec_requires_strict() -> None:
    with pytest.raises(Exception):
        ProviderToolSpec(
            function={
                "name": "test_tool",
                "description": "test",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "strict": False,
            }
        )


def test_provider_tool_spec_requires_all_fields() -> None:
    with pytest.raises(Exception):
        ProviderToolSpec(
            function={
                "name": "test_tool",
                "description": "test",
                "strict": True,
            }
        )


def test_provider_tool_catalog_rejects_duplicate_aliases() -> None:
    spec = ProviderToolSpec(
        function={
            "name": "test_tool",
            "description": "test",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "strict": True,
        }
    )
    binding = ProviderToolBinding(
        alias="test_tool",
        internal_name="chat.test_tool",
        spec=spec,
    )
    with pytest.raises(Exception):
        ProviderToolCatalog(
            bindings=[binding, binding],
            catalog_sha256="a" * 64,
        )


def test_normalized_tool_call_validates_pattern() -> None:
    with pytest.raises(Exception):
        NormalizedToolCall(
            provider_call_id="",
            alias="bad",
            arguments={},
        )


def test_tool_loop_trace_validates_call_count() -> None:
    with pytest.raises(Exception):
        ToolLoopTrace(
            trace_id="tooltrace_" + "a" * 24,
            job_id="job-1",
            status="completed",
            catalog_sha256="a" * 64,
            request_sha256="a" * 64,
            started_at="2024-01-01T00:00:00Z",
            finished_at="2024-01-01T00:00:01Z",
            trace_sha256="a" * 64,
            calls=[
                ToolLoopCallTrace(
                    round_index=1,
                    call_id="c1",
                    tool_name="chat.test",
                    status="succeeded",
                    input_sha256="a" * 64,
                )
                for _ in range(4)
            ],
        )


def test_tool_loop_call_trace_validates_status() -> None:
    with pytest.raises(Exception):
        ToolLoopCallTrace(
            round_index=1,
            call_id="c1",
            tool_name="chat.test",
            status="invalid_status",
            input_sha256="a" * 64,
        )
