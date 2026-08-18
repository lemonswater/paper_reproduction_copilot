from __future__ import annotations

import app.model as model_module
from app.config import settings


class _FakeSecretMaterial:
    def reveal(self) -> str:
        return "test-provider-key"


class _FakeSecretService:
    def resolve_current(self, **_kwargs):
        return _FakeSecretMaterial()


def test_chat_model_sets_explicit_output_budget(monkeypatch):
    captured: dict = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        model_module,
        "ChatOpenAI",
        fake_chat_openai,
    )
    monkeypatch.setattr(
        settings,
        "openai_max_output_tokens",
        4096,
    )
    monkeypatch.setattr(
        settings,
        "openai_thinking_mode",
        "disabled",
    )

    model_module.get_chat_model(
        temperature=0,
        secret_service=_FakeSecretService(),
    )

    assert captured["max_completion_tokens"] == 4096
    assert captured["extra_body"] == {
        "thinking": {
            "type": "disabled",
        }
    }


def test_chat_model_omits_provider_specific_thinking_when_unset(monkeypatch):
    captured: dict = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        model_module,
        "ChatOpenAI",
        fake_chat_openai,
    )
    monkeypatch.setattr(
        settings,
        "openai_thinking_mode",
        None,
    )

    model_module.get_chat_model(
        temperature=0,
        secret_service=_FakeSecretService(),
    )

    assert "extra_body" not in captured
