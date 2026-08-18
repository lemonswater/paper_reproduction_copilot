from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from app.model_routing.schemas import ModelBudgetPolicy
from tests.helpers.model_routing import (
    FakeProviders,
    TEST_PRICING,
    build_test_document,
    build_test_gateway,
)


TOOL_TEST_BUDGET = ModelBudgetPolicy(
    daily_total_token_limit=100000,
    daily_cost_limit_micro_usd=100000,
    per_job_total_token_limit=50000,
    per_job_cost_limit_micro_usd=50000,
    reservation_ttl_seconds=300,
    allow_unpriced_in_active=False,
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_reproduction_status",
            "description": "read current job status",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]


class FakeToolBoundModel:
    def __init__(self, message: AIMessage) -> None:
        self.message = message
        self.bind_calls: list[dict] = []
        self.invoke_calls = 0

    def bind_tools(self, tools, **kwargs):
        self.bind_calls.append({"tools": tools, **kwargs})
        return self

    def invoke(self, messages):
        self.invoke_calls += 1
        assert isinstance(messages[0], HumanMessage)
        return self.message


def _gateway(tmp_path, chat, *, mode="active"):
    pricing = {
        "legacy_chat": TEST_PRICING,
        "strong_chat": TEST_PRICING,
        "economy_chat": TEST_PRICING,
    }
    document = build_test_document(
        pricing_override=pricing,
        budget=TOOL_TEST_BUDGET,
    )
    providers = FakeProviders(chat=chat)
    gateway = build_test_gateway(
        tmp_path,
        mode=mode,
        providers=providers,
        document=document,
    )
    return gateway, providers


def test_gateway_binds_strict_single_tool_calling(tmp_path) -> None:
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_reproduction_status",
                "args": {},
                "id": "provider-call-1",
                "type": "tool_call",
            }
        ],
        usage_metadata={
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
        },
    )
    chat = FakeToolBoundModel(message)
    gateway, providers = _gateway(tmp_path, chat)

    result = gateway.invoke_tool_calling(
        messages=[HumanMessage(content="status?")],
        tools=TOOLS,
        node_name="chat_tool_selection",
        job_id="job-1",
    )

    assert result.message is message
    assert providers.chat_builds == 1
    assert chat.bind_calls[0]["strict"] is True
    assert chat.bind_calls[0]["parallel_tool_calls"] is False
    assert chat.bind_calls[0]["tool_choice"] == "auto"
    assert result.ledger_record is not None
    assert result.ledger_record.task_kind == "chat_tool_selection"
    assert result.ledger_record.actual_input_tokens == 100
    assert result.ledger_record.actual_output_tokens == 20


def test_gateway_missing_usage_uses_reservation_upper_bound(
    tmp_path,
) -> None:
    chat = FakeToolBoundModel(AIMessage(content="stop"))
    gateway, _ = _gateway(tmp_path, chat)

    result = gateway.invoke_tool_calling(
        messages=[HumanMessage(content="status?")],
        tools=TOOLS,
        node_name="chat_tool_selection",
        job_id="job-1",
    )

    assert result.ledger_record is not None
    assert result.ledger_record.usage_quality == "reservation_upper_bound"
    assert result.ledger_record.actual_input_tokens == (
        result.ledger_record.reserved_input_tokens
    )


def test_gateway_off_mode_does_not_write_ledger(tmp_path) -> None:
    chat = FakeToolBoundModel(AIMessage(content="stop"))
    gateway, _ = _gateway(tmp_path, chat, mode="off")

    result = gateway.invoke_tool_calling(
        messages=[HumanMessage(content="status?")],
        tools=TOOLS,
        node_name="chat_tool_selection",
        job_id="job-1",
    )

    assert result.invocation_id is None
    assert result.ledger_record is None
