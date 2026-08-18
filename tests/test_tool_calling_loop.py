from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage

from app.tool_calling.identity import validate_trace_hash
from tests.tool_calling_helpers import (
    HandlerRecorder,
    ScriptedToolTurnInvoker,
    build_fixture_loop,
    stop_message,
    tool_call_message,
)


REQUEST_HASH = "a" * 64


def _run(loop):
    return loop.run(
        job_id="job-1",
        job_status="failed",
        question="为什么失败？",
        request_sha256=REQUEST_HASH,
    )


def test_no_tool_call_finishes_without_handler() -> None:
    recorder = HandlerRecorder()
    invoker = ScriptedToolTurnInvoker([stop_message()])
    outcome = _run(
        build_fixture_loop(invoker=invoker, recorder=recorder)
    )

    assert outcome.trace.status == "no_tools_needed"
    assert outcome.trace.calls == []
    assert outcome.sources == []
    assert recorder.calls == []
    validate_trace_hash(outcome.trace)


def test_one_tool_call_returns_evidence_then_stops() -> None:
    recorder = HandlerRecorder()
    invoker = ScriptedToolTurnInvoker(
        [
            tool_call_message(
                "inspect_failure_context",
                {"focus": "CUDA build", "limit": 3},
                call_id="provider-call-1",
            ),
            stop_message(),
        ]
    )
    outcome = _run(
        build_fixture_loop(invoker=invoker, recorder=recorder)
    )

    assert outcome.trace.status == "completed"
    assert len(outcome.trace.calls) == 1
    assert outcome.trace.calls[0].status == "succeeded"
    assert outcome.trace.calls[0].tool_name == (
        "chat.inspect_failure_context"
    )
    assert recorder.calls[0][1] == "job-1"
    assert outcome.sources[0].citation.citation_id == "job:current"

    # 第二次模型调用收到的 ToolMessage 必须使用 Provider Call ID。
    second_turn_messages = invoker.received[1]
    tool_message = next(
        item
        for item in second_turn_messages
        if isinstance(item, ToolMessage)
    )
    assert tool_message.tool_call_id == "provider-call-1"


def test_model_cannot_supply_another_job_id() -> None:
    recorder = HandlerRecorder()
    invoker = ScriptedToolTurnInvoker(
        [
            tool_call_message(
                "get_reproduction_status",
                {"job_id": "job-2"},
                call_id="provider-call-cross-job",
            ),
            stop_message(),
        ]
    )
    outcome = _run(
        build_fixture_loop(invoker=invoker, recorder=recorder)
    )

    assert recorder.calls == []
    assert outcome.trace.calls[0].status == "failed"
    assert outcome.trace.calls[0].error_code == "TOOL_INPUT_INVALID"


def test_unknown_tool_is_blocked_without_directory_disclosure() -> None:
    recorder = HandlerRecorder()
    invoker = ScriptedToolTurnInvoker(
        [
            tool_call_message(
                "cancel_job",
                {},
                call_id="provider-call-mutation",
            )
        ]
    )
    outcome = _run(
        build_fixture_loop(invoker=invoker, recorder=recorder)
    )

    assert outcome.trace.status == "policy_blocked"
    assert outcome.trace.calls == []
    assert recorder.calls == []


def test_parallel_tool_calls_are_blocked() -> None:
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_reproduction_status",
                "args": {},
                "id": "call-1",
                "type": "tool_call",
            },
            {
                "name": "inspect_failure_context",
                "args": {},
                "id": "call-2",
                "type": "tool_call",
            },
        ],
    )
    recorder = HandlerRecorder()
    outcome = _run(
        build_fixture_loop(
            invoker=ScriptedToolTurnInvoker([message]),
            recorder=recorder,
        )
    )

    assert outcome.trace.status == "policy_blocked"
    assert recorder.calls == []


def test_repeated_tool_fingerprint_stops_loop() -> None:
    repeated = tool_call_message(
        "get_reproduction_status",
        {},
        call_id="call-first",
    )
    repeated_again = tool_call_message(
        "get_reproduction_status",
        {},
        call_id="call-second",
    )
    recorder = HandlerRecorder()
    outcome = _run(
        build_fixture_loop(
            invoker=ScriptedToolTurnInvoker(
                [repeated, repeated_again]
            ),
            recorder=recorder,
        )
    )

    assert outcome.trace.status == "policy_blocked"
    assert len(recorder.calls) == 1
    assert len(outcome.trace.calls) == 1


def test_tool_call_limit_is_hard_boundary() -> None:
    recorder = HandlerRecorder()
    invoker = ScriptedToolTurnInvoker(
        [
            tool_call_message(
                "get_reproduction_status", {}, call_id="call-1"
            ),
            tool_call_message(
                "inspect_failure_context",
                {"focus": "first", "limit": 2},
                call_id="call-2",
            ),
        ]
    )
    outcome = _run(
        build_fixture_loop(
            invoker=invoker,
            recorder=recorder,
            max_model_rounds=2,
            max_tool_calls=1,
        )
    )

    assert outcome.trace.status == "limit_reached"
    assert len(recorder.calls) == 1
    assert len(outcome.trace.calls) == 1


def test_tool_selection_text_never_becomes_final_answer() -> None:
    recorder = HandlerRecorder()
    invoker = ScriptedToolTurnInvoker(
        [AIMessage(content="I already fixed the repository")]
    )
    outcome = _run(
        build_fixture_loop(invoker=invoker, recorder=recorder)
    )

    assert outcome.trace.status == "no_tools_needed"
    assert outcome.sources == []
    # Outcome 没有 answer 字段，普通模型文本不会进入 ChatMessage。
    assert not hasattr(outcome, "answer")
