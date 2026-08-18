from __future__ import annotations

from app.observability.context import (
    bind_telemetry_context,
    current_telemetry_context,
    short_secret_hash,
)


def test_bind_merges():
    with bind_telemetry_context(request_id="a") as ctx:
        assert ctx.request_id == "a"
        assert current_telemetry_context().request_id == "a"


def test_bind_does_not_mutate_outer():
    outer_before = current_telemetry_context()
    with bind_telemetry_context(request_id="a", job_id="b") as c1:
        assert c1.request_id == "a"
        assert c1.job_id == "b"
    outer_after = current_telemetry_context()
    assert outer_after.request_id != "a"
    assert outer_after.job_id != "b"
    assert outer_before.model_dump() == outer_after.model_dump()


def test_bind_skips_none_updates():
    with bind_telemetry_context(request_id=None, job_id="j") as ctx:
        assert ctx.request_id is None
        assert ctx.job_id == "j"
    with bind_telemetry_context(request_id="r") as _:
        with bind_telemetry_context(request_id=None, job_id="j2") as ctx2:
            assert ctx2.request_id == "r"
            assert ctx2.job_id == "j2"


def test_context_returns_copy():
    ctx1 = current_telemetry_context()
    ctx2 = current_telemetry_context()
    assert ctx1.model_dump() == ctx2.model_dump()
    assert id(ctx1) != id(ctx2)


def test_short_secret_hash_deterministic():
    h1 = short_secret_hash("hello")
    h2 = short_secret_hash("hello")
    h3 = short_secret_hash("world")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 16


def test_short_secret_hash_none():
    assert short_secret_hash(None) is None


def test_short_secret_hash_empty():
    assert short_secret_hash("") is None
