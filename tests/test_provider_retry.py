from __future__ import annotations

from app.tools.structured_output_tools import (
    _invoke_with_transport_retry,
)


def test_transient_provider_error_is_retried(monkeypatch):
    calls = {"count": 0}
    monkeypatch.setattr(
        "app.tools.structured_output_tools.time.sleep",
        lambda seconds: None,
    )

    def invoke():
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("provider timed out")
        return {"parsed": {"status": "ok"}}

    response, attempts, error = _invoke_with_transport_retry(
        invoke=invoke,
        prompt_kind="original",
        attempt_number_start=1,
        max_retries=2,
        base_seconds=0,
    )

    assert error is None
    assert response == {"parsed": {"status": "ok"}}
    assert calls["count"] == 3
    assert [item.status for item in attempts] == [
        "provider_retry",
        "provider_retry",
    ]


def test_nontransient_provider_error_is_not_retried(
    monkeypatch,
):
    calls = {"count": 0}
    monkeypatch.setattr(
        "app.tools.structured_output_tools.time.sleep",
        lambda seconds: None,
    )

    def invoke():
        calls["count"] += 1
        raise RuntimeError("model does not exist")

    response, attempts, error = _invoke_with_transport_retry(
        invoke=invoke,
        prompt_kind="original",
        attempt_number_start=1,
        max_retries=2,
        base_seconds=0,
    )

    assert response is None
    assert isinstance(error, RuntimeError)
    assert calls["count"] == 1
    assert [item.status for item in attempts] == [
        "invoke_error",
    ]