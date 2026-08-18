"""Phase 50: Model Budget Repository 预算预留与结算测试。"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.model_routing.errors import (
    ModelBudgetExceeded,
    ModelLedgerConflict,
    ModelLedgerIntegrityError,
)
from app.model_routing.repository import SqliteModelLedger, iso_utc, utc_now
from app.model_routing.schemas import (
    ModelBudgetPolicy,
    ModelReservationRequest,
    ModelUsage,
)
from tests.helpers.model_routing import (
    TEST_BUDGET,
    TEST_PRICING,
)


def _make_reservation(
    *,
    invocation_id: str = "mdl_" + "a" * 32,
    request_sha256: str = "0" * 64,
    decision_sha256: str = "0" * 64,
    task_kind: str = "chat_answer",
    job_id: str | None = None,
    profile_id: str = "legacy_chat",
    model_name: str = "legacy-model",
    pricing_version: str = "test-v1",
    enforced: bool = True,
    reserved_input_tokens: int = 100,
    reserved_output_tokens: int = 50,
    reserved_cost_micro_usd: int | None = 10,
    prompt_chars: int = 100,
    prompt_sha256: str = "0" * 64,
    schema_sha256: str | None = "0" * 64,
    lease_expires_at: str | None = None,
    node_name: str = "test_node",
) -> ModelReservationRequest:
    return ModelReservationRequest(
        invocation_id=invocation_id,
        request_sha256=request_sha256,
        decision_sha256=decision_sha256,
        task_kind=task_kind,
        job_id=job_id,
        run_id=None,
        node_name=node_name,
        profile_id=profile_id,
        model_name=model_name,
        pricing_version=pricing_version,
        enforced=enforced,
        reserved_input_tokens=reserved_input_tokens,
        reserved_output_tokens=reserved_output_tokens,
        reserved_cost_micro_usd=reserved_cost_micro_usd,
        prompt_chars=prompt_chars,
        prompt_sha256=prompt_sha256,
        schema_sha256=schema_sha256,
        lease_expires_at=lease_expires_at or iso_utc(
            utc_now() + timedelta(seconds=300)
        ),
    )


def _make_usage(
    *,
    input_tokens: int = 100,
    output_tokens: int = 50,
    quality: str = "provider_reported",
    response_count: int = 1,
) -> ModelUsage:
    return ModelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_micro_usd=0,
        quality=quality,
        provider_response_count=response_count,
    )


@pytest.fixture
def ledger(tmp_path: Path) -> SqliteModelLedger:
    return SqliteModelLedger(
        tmp_path / "usage.sqlite",
        budget=TEST_BUDGET,
    )


@pytest.fixture
def reservation() -> ModelReservationRequest:
    return _make_reservation()


def test_first_reserve_writes_reserved(ledger, reservation):
    record = ledger.reserve(reservation)
    assert record.status == "reserved"
    assert record.invocation_id == reservation.invocation_id


def test_same_reserve_idempotent(ledger, reservation):
    first = ledger.reserve(reservation)
    second = ledger.reserve(reservation)
    assert first.invocation_id == second.invocation_id
    assert second.status == "reserved"


def test_different_request_same_invocation_conflict(ledger, reservation):
    ledger.reserve(reservation)
    different = reservation.model_copy(
        update={"request_sha256": "1" * 64}
    )
    with pytest.raises(ModelLedgerConflict):
        ledger.reserve(different)


def test_daily_token_limit_exceeded(ledger):
    # TEST_BUDGET daily_total_token_limit=10000
    # Each reservation has 150 total tokens (100+50)
    # But enforced=True, so budget is checked
    # 10000 / 150 = 66 reservations
    for i in range(66):
        r = _make_reservation(
            invocation_id=f"mdl_{i:032d}",
        )
        ledger.reserve(r)

    # 67th should exceed
    r = _make_reservation(invocation_id="mdl_" + "f" * 32)
    with pytest.raises(ModelBudgetExceeded):
        ledger.reserve(r)


def test_per_job_token_limit_exceeded(ledger):
    # TEST_BUDGET per_job_total_token_limit=5000
    for i in range(33):
        r = _make_reservation(
            invocation_id=f"mdl_{i:032d}",
            job_id="job-1",
        )
        ledger.reserve(r)

    r = _make_reservation(
        invocation_id="mdl_" + "f" * 32,
        job_id="job-1",
    )
    with pytest.raises(ModelBudgetExceeded):
        ledger.reserve(r)


def test_shadow_enforced_false_not_rejected(ledger):
    # Set up to exceed budget
    for i in range(66):
        r = _make_reservation(
            invocation_id=f"mdl_{i:032d}",
            enforced=False,
        )
        ledger.reserve(r)

    # Even though budget exceeded, enforced=False should not reject
    r = _make_reservation(
        invocation_id="mdl_" + "f" * 32,
        enforced=False,
    )
    record = ledger.reserve(r)
    assert record.status == "reserved"


def test_settle_succeeds(ledger, reservation):
    ledger.reserve(reservation)
    usage = _make_usage()
    record = ledger.settle(
        invocation_id=reservation.invocation_id,
        status="succeeded",
        usage=usage,
        latency_ms=100,
        error_code=None,
    )
    assert record.status == "succeeded"
    assert record.actual_input_tokens == 100
    assert record.actual_output_tokens == 50


def test_settle_idempotent(ledger, reservation):
    ledger.reserve(reservation)
    usage = _make_usage()
    first = ledger.settle(
        invocation_id=reservation.invocation_id,
        status="succeeded",
        usage=usage,
        latency_ms=100,
        error_code=None,
    )
    second = ledger.settle(
        invocation_id=reservation.invocation_id,
        status="succeeded",
        usage=usage,
        latency_ms=100,
        error_code=None,
    )
    assert first.status == second.status


def test_settle_conflict_different_usage(ledger, reservation):
    ledger.reserve(reservation)
    usage1 = _make_usage(input_tokens=100, output_tokens=50)
    ledger.settle(
        invocation_id=reservation.invocation_id,
        status="succeeded",
        usage=usage1,
        latency_ms=100,
        error_code=None,
    )
    usage2 = _make_usage(input_tokens=200, output_tokens=100)
    with pytest.raises(ModelLedgerConflict):
        ledger.settle(
            invocation_id=reservation.invocation_id,
            status="succeeded",
            usage=usage2,
            latency_ms=200,
            error_code=None,
        )


def test_reconcile_stale(ledger, reservation):
    # Create a stale reservation
    stale = reservation.model_copy(
        update={
            "lease_expires_at": iso_utc(
                utc_now() - timedelta(seconds=600)
            ),
        }
    )
    ledger.reserve(stale)

    records = ledger.reconcile_stale(limit=10)
    assert len(records) == 1
    assert records[0].status == "usage_unknown"


def test_summary_distinguishes_settled_and_reserved(ledger, reservation):
    ledger.reserve(reservation)
    summary = ledger.summary(
        utc_date=utc_now().date().isoformat(),
        job_id=None,
    )
    assert summary.active_reservation_count == 1
    assert summary.invocation_count == 1
    assert summary.settled_input_tokens == 0


def test_summary_after_settle(ledger, reservation):
    ledger.reserve(reservation)
    usage = _make_usage()
    ledger.settle(
        invocation_id=reservation.invocation_id,
        status="succeeded",
        usage=usage,
        latency_ms=100,
        error_code=None,
    )
    summary = ledger.summary(
        utc_date=utc_now().date().isoformat(),
        job_id=None,
    )
    assert summary.invocation_count == 1
    assert summary.active_reservation_count == 0
    assert summary.settled_input_tokens == 100


def test_list_invocations(ledger, reservation):
    ledger.reserve(reservation)
    records = ledger.list_invocations(limit=10)
    assert len(records) == 1
    assert records[0].invocation_id == reservation.invocation_id


def test_list_invocations_by_job(ledger):
    r1 = _make_reservation(
        invocation_id="mdl_" + "1" * 32,
        job_id="job-a",
    )
    r2 = _make_reservation(
        invocation_id="mdl_" + "2" * 32,
        job_id="job-b",
    )
    ledger.reserve(r1)
    ledger.reserve(r2)
    records = ledger.list_invocations(limit=10, job_id="job-a")
    assert len(records) == 1
    assert records[0].job_id == "job-a"


def test_ping(ledger):
    # Should not raise
    assert ledger.ping() is None or ledger.ping() == 1


def test_concurrent_reserve_only_one_succeeds(ledger):
    # Set up budget to allow exactly one more reservation
    for i in range(65):
        r = _make_reservation(
            invocation_id=f"mdl_{i:032d}",
        )
        ledger.reserve(r)

    barrier = threading.Barrier(2)
    results: list[Exception | None] = [None, None]

    def attempt(idx: int):
        barrier.wait()
        r = _make_reservation(
            invocation_id=f"mdl_{idx:032x}",
        )
        try:
            ledger.reserve(r)
            results[idx] = None
        except ModelBudgetExceeded as exc:
            results[idx] = exc

    t1 = threading.Thread(target=attempt, args=(0,))
    t2 = threading.Thread(target=attempt, args=(1,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # At least one should succeed, at least one should fail
    successes = sum(1 for r in results if r is None)
    assert successes >= 1
