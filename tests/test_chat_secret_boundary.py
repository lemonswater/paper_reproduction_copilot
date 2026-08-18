from __future__ import annotations

from app.secrets.redaction import SecretRedactor


SECRET = "sk-chat-canary-1234567890"


def test_chat_redactor_removes_known_secret_from_question() -> None:
    redactor = SecretRedactor.from_values([SECRET])
    question = f"请帮我检查这个值：{SECRET}"

    normalized = redactor.redact_text(question, max_chars=4000)

    assert SECRET not in normalized
    assert "<redacted>" in normalized


def test_chat_redactor_removes_known_secret_from_model_answer() -> None:
    redactor = SecretRedactor.from_values([SECRET])
    answer = f"模型错误回显了 {SECRET}"

    persisted = redactor.redact_text(answer, max_chars=6000)

    assert SECRET not in persisted
    assert "<redacted>" in persisted
