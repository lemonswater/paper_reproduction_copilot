from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat_routes import router
from app.chat.errors import ChatUnavailableError
from app.chat.schemas import (
    ChatAskResponse,
    ChatMessage,
    ChatMessagePage,
    ConversationMemoryView,
)


def _message(
    role: Literal["user", "assistant"],
    sequence: int,
) -> ChatMessage:
    return ChatMessage(
        message_id=f"message-{sequence}",
        job_id="job-1",
        sequence=sequence,
        role=role,
        content="question" if role == "user" else "answer",
        reply_to=(
            f"message-{sequence - 1}"
            if role == "assistant"
            else None
        ),
        created_at="2026-08-01T00:00:00Z",
    )


class FakeChatService:
    def list_messages(self, **_kwargs):
        return ChatMessagePage(
            items=[_message("user", 1), _message("assistant", 2)],
            next_after=2,
        )

    def list_recent_messages(self, **_kwargs):
        return ChatMessagePage(
            items=[_message("user", 201), _message("assistant", 202)],
            next_after=202,
        )

    def get_memory(self, **_kwargs):
        return ConversationMemoryView(
            job_id="job-1",
            version=2,
            covered_through_sequence=200,
            summary="The user requested a CPU-only validation.",
            user_constraints=[],
            decisions=[],
            open_questions=[],
            citation_anchors=[],
            memory_sha256="a" * 64,
            created_at="2026-08-08T00:00:00+00:00",
        )

    def ask(self, **kwargs):
        assert kwargs["idempotency_key"] == "ask-api-1"
        return ChatAskResponse(
            user_message=_message("user", 1),
            assistant_message=_message("assistant", 2),
        )


def _client(service) -> TestClient:
    app = FastAPI()
    app.state.api_token = None
    app.state.chat_service = service
    app.include_router(router)
    return TestClient(app)


def test_chat_history_and_ask_contract():
    client = _client(FakeChatService())

    history = client.get("/v1/jobs/job-1/chat")
    answer = client.post(
        "/v1/jobs/job-1/chat",
        headers={"Idempotency-Key": "ask-api-1"},
        json={"question": "Why?"},
    )

    assert history.status_code == 200
    assert history.json()["next_after"] == 2
    assert answer.status_code == 200
    assert answer.json()["assistant_message"]["content"] == "answer"


def test_disabled_chat_returns_503():
    response = _client(None).get(
        "/v1/jobs/job-1/chat"
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "CHAT_DISABLED"


def test_recent_history_and_memory_contract():
    client = _client(FakeChatService())

    recent = client.get("/v1/jobs/job-1/chat/recent?limit=100")
    memory = client.get("/v1/jobs/job-1/chat/memory")

    assert recent.status_code == 200
    assert [
        item["sequence"] for item in recent.json()["items"]
    ] == [201, 202]
    assert memory.status_code == 200
    assert memory.json()["version"] == 2
    assert memory.json()["covered_through_sequence"] == 200


def test_unavailable_memory_returns_explicit_503():
    class UnavailableMemoryService(FakeChatService):
        def get_memory(self, **_kwargs):
            raise ChatUnavailableError(
                "Chat Memory integrity check failed"
            )

    response = _client(UnavailableMemoryService()).get(
        "/v1/jobs/job-1/chat/memory"
    )

    assert response.status_code == 503
    assert (
        response.json()["detail"]["code"]
        == "CHAT_MEMORY_UNAVAILABLE"
    )
