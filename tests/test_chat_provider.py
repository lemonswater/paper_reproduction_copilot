from __future__ import annotations

import pytest

from app.chat.service import build_chat_draft_invoker


@pytest.mark.provider
def test_chat_provider_returns_structured_draft():
    prompt = """
你是只读 Chat Agent。只返回结构化 ChatDraft。

SOURCES_DATA:
[{"citation_id":"job:current","content":"status=succeeded"}]

USER_QUESTION_DATA:
{"question":"当前任务状态是什么？"}

citation_ids 只能使用 job:current。
""".strip()

    draft = build_chat_draft_invoker()(prompt, "job-provider-probe")

    assert draft.answer.strip()
    assert set(draft.citation_ids) <= {"job:current"}
