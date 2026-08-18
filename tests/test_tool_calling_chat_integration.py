from __future__ import annotations

from app.chat.schemas import ChatDraft
from tests.test_chat_service import _service
from tests.tool_calling_helpers import (
    HandlerRecorder,
    ScriptedToolTurnInvoker,
    build_fixture_loop,
    stop_message,
    tool_call_message,
)


def test_tool_evidence_enters_final_citation_allowlist(tmp_path) -> None:
    recorder = HandlerRecorder()
    loop = build_fixture_loop(
        recorder=recorder,
        invoker=ScriptedToolTurnInvoker(
            [
                tool_call_message(
                    "get_reproduction_status",
                    {},
                    call_id="provider-call-1",
                ),
                stop_message(),
            ]
        ),
    )
    service = _service(
        tmp_path,
        lambda prompt, job_id: ChatDraft(
            answer="当前任务失败。",
            citation_ids=["job:current"],
        ),
        tool_loop=loop,
    )

    response = service.ask(
        job_id="job-1",
        question="当前是什么状态？",
        idempotency_key="tool-chat-1",
    )

    assert response.assistant_message.content == "当前任务失败。"
    assert response.assistant_message.citations[0].citation_id == (
        "job:current"
    )
    assert response.assistant_message.tool_trace is not None
    assert response.assistant_message.tool_trace.status == "completed"
    assert len(recorder.calls) == 1


def test_idempotent_replay_does_not_run_tool_loop_twice(tmp_path) -> None:
    recorder = HandlerRecorder()
    loop = build_fixture_loop(
        recorder=recorder,
        invoker=ScriptedToolTurnInvoker(
            [
                tool_call_message(
                    "get_reproduction_status",
                    {},
                    call_id="provider-call-1",
                ),
                stop_message(),
            ]
        ),
    )
    service = _service(
        tmp_path,
        lambda prompt, job_id: ChatDraft(
            answer="当前任务失败。",
            citation_ids=["job:current"],
        ),
        tool_loop=loop,
    )

    first = service.ask(
        job_id="job-1",
        question="当前是什么状态？",
        idempotency_key="tool-replay-1",
    )
    second = service.ask(
        job_id="job-1",
        question="当前是什么状态？",
        idempotency_key="tool-replay-1",
    )

    assert len(recorder.calls) == 1
    assert second.replayed is True
    assert second.assistant_message.tool_trace == (
        first.assistant_message.tool_trace
    )


def test_tool_selection_free_text_is_discarded(tmp_path) -> None:
    recorder = HandlerRecorder()
    loop = build_fixture_loop(
        recorder=recorder,
        invoker=ScriptedToolTurnInvoker(
            # 这段错误声明不能成为最终 ChatMessage。
            [stop_message().model_copy(update={"content": "已执行修复"})]
        ),
    )
    service = _service(
        tmp_path,
        lambda prompt, job_id: ChatDraft(
            answer="当前证据只显示任务失败。",
            citation_ids=["job:current"],
        ),
        tool_loop=loop,
    )

    response = service.ask(
        job_id="job-1",
        question="修好了吗？",
        idempotency_key="discard-selection-text",
    )

    assert "已执行修复" not in response.assistant_message.content
    assert "任务失败" in response.assistant_message.content


def test_feature_disabled_uses_legacy_context(tmp_path) -> None:
    service = _service(
        tmp_path,
        lambda prompt, job_id: ChatDraft(
            answer="来自旧 Context。",
            citation_ids=["artifact:report:1"],
        ),
        tool_loop=None,
    )

    response = service.ask(
        job_id="job-1",
        question="为什么失败？",
        idempotency_key="tool-disabled",
    )

    assert response.assistant_message.tool_trace is None
    assert response.assistant_message.citations[0].artifact_id == "report"
