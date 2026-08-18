from __future__ import annotations

"""后端无关的 JobStore contract。

每个 contract 是普通函数，接收一个实现了 ``app.job_runtime.ports.JobStore``
的 store 实例。SQLite 与 PostgreSQL 后端都必须通过同一组 contract，factory
切换才可信。

contract 不依赖调用方 wall clock：所有时间由后端自行决定（SQLite 使用
``time.time()``，PostgreSQL 使用 ``clock_timestamp()``），因此不传 ``now``。
"""

from app.job_runtime.errors import (
    JobConflictError,
    LeaseLostError,
)
from app.job_runtime.schemas import (
    JobInterrupt,
    JobRequest,
)
from tests.workspace_helpers import (
    manifest_fixture,
    requirements_fixture,
    worker_fixture,
)


def _request() -> JobRequest:
    return JobRequest(
        paper_path="/data/paper.pdf",
        repo_path="/data/repo",
        execution_profile_id="local",
    )


def submit_fixture(
    store,
    *,
    suffix: str = "1",
    max_attempts: int = 3,
):
    """提交一个可复用的 Job；suffix 决定唯一身份。"""

    return store.submit(
        job_id=f"job-{suffix}",
        idempotency_key=f"submit-{suffix}",
        thread_id=f"thread-{suffix}",
        run_id=f"run-{suffix}",
        run_dir=f"/data/runs/run-{suffix}",
        request=_request(),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix=suffix),
        max_attempts=max_attempts,
    )


def _register_and_claim(
    store,
    *,
    worker_id: str = "worker-a",
    session_id: str | None = None,
    host_id: str = "host-a",
    lease_seconds: float = 30,
    session_lease_seconds: float = 30,
):
    """注册 worker 并 claim，返回 claim 结果。

    ``session_lease_seconds`` 控制 worker session lease，与 job claim
    的 ``lease_seconds`` 分离，避免 lease=0 测试同时让 session 过期。
    """
    if session_id is None:
        session_id = f"session-{worker_id}"
    worker = worker_fixture(
        worker_id=worker_id,
        session_id=session_id,
        host_id=host_id,
    )
    store.register_worker(
        worker=worker,
        lease_seconds=session_lease_seconds,
    )
    return store.claim_next(
        worker=worker,
        lease_seconds=lease_seconds,
    )


def contract_submit_is_idempotent(store) -> None:
    first, created = submit_fixture(store)
    second, replay_created = submit_fixture(store)
    assert created is True
    assert replay_created is False
    assert first.job_id == second.job_id


def contract_submit_conflict_on_different_request(
    store,
) -> None:
    store.submit(
        job_id="job-c1",
        idempotency_key="submit-conflict",
        thread_id="thread-c1",
        run_id="run-c1",
        run_dir="/data/runs/run-c1",
        request=_request(),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix="c1"),
        max_attempts=3,
    )
    different = JobRequest(
        paper_path="/data/other.pdf",
        repo_path="/data/repo",
        execution_profile_id="local",
    )
    try:
        store.submit(
            job_id="job-c2",
            idempotency_key="submit-conflict",
            thread_id="thread-c2",
            run_id="run-c2",
            run_dir="/data/runs/run-c2",
            request=different,
            requirements=requirements_fixture(),
            initial_manifest=manifest_fixture(suffix="c2"),
            max_attempts=3,
        )
    except JobConflictError:
        return
    raise AssertionError(
        "相同 idempotency_key 不同请求应冲突"
    )


def contract_claim_is_exclusive(store) -> None:
    submit_fixture(store)
    first = _register_and_claim(
        store, worker_id="worker-a"
    )
    second = _register_and_claim(
        store, worker_id="worker-b"
    )
    assert first is not None
    assert second is None


def contract_heartbeat_observes_cancel(
    store,
) -> None:
    submit_fixture(store)
    claim = _register_and_claim(
        store, worker_id="worker-a"
    )
    assert claim is not None
    store.request_cancel(
        job_id=claim.job.job_id,
        reason="user",
        actor="user",
    )
    hb = store.heartbeat(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        lease_seconds=30,
    )
    assert hb.cancel_requested is True


def contract_wait_resume_succeed(store) -> None:
    submit_fixture(store)
    claim = _register_and_claim(
        store, worker_id="worker-a"
    )
    assert claim is not None
    waiting = store.mark_waiting(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        interrupts=[JobInterrupt(node="review")],
        result={"run_id": claim.job.run_id},
        actor="worker-a",
    )
    assert waiting.status == "waiting_for_input"
    assert waiting.wait_generation == 1
    assert waiting.interrupt_nodes == ["review"]

    queued, created = store.queue_resume(
        job_id=claim.job.job_id,
        expected_node="review",
        value="approved",
        idempotency_key="resume-1",
        actor="user",
        expected_job_version=waiting.version,
        expected_wait_generation=waiting.wait_generation,
    )
    assert created is True
    assert queued.status == "queued"

    resume_claim = _register_and_claim(
        store,
        worker_id="worker-b",
        session_id="session-b",
    )
    assert resume_claim is not None
    assert resume_claim.resume_request is not None
    assert (
        resume_claim.resume_request.expected_node
        == "review"
    )

    done = store.mark_succeeded(
        job_id=resume_claim.job.job_id,
        claim_token=resume_claim.claim_token,
        result={"final_status": "succeeded"},
        actor="worker-b",
    )
    assert done.status == "succeeded"


def contract_resume_is_idempotent(store) -> None:
    submit_fixture(store)
    claim = _register_and_claim(
        store, worker_id="worker-a"
    )
    waiting = store.mark_waiting(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        interrupts=[JobInterrupt(node="review")],
        result={},
        actor="worker-a",
    )
    first, created1 = store.queue_resume(
        job_id=claim.job.job_id,
        expected_node="review",
        value="approved",
        idempotency_key="resume-idem",
        actor="user",
        expected_wait_generation=waiting.wait_generation,
    )
    second, created2 = store.queue_resume(
        job_id=claim.job.job_id,
        expected_node="review",
        value="approved",
        idempotency_key="resume-idem",
        actor="user",
        expected_wait_generation=waiting.wait_generation,
    )
    assert created1 is True
    assert created2 is False
    assert first.job_id == second.job_id


def contract_stale_wait_generation_resume_rejected(
    store,
) -> None:
    submit_fixture(store)
    claim = _register_and_claim(
        store, worker_id="worker-a"
    )
    waiting = store.mark_waiting(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        interrupts=[JobInterrupt(node="review")],
        result={},
        actor="worker-a",
    )
    try:
        store.queue_resume(
            job_id=claim.job.job_id,
            expected_node="review",
            value="approved",
            idempotency_key="resume-stale",
            actor="user",
            expected_wait_generation=(
                waiting.wait_generation + 999
            ),
        )
    except JobConflictError:
        return
    raise AssertionError(
        "过期 wait_generation 的 resume 应被拒绝"
    )


def contract_cancel_command_is_idempotent(
    store,
) -> None:
    submit_fixture(store)
    first = store.request_cancel(
        job_id="job-1",
        reason="user",
        actor="user",
        idempotency_key="cancel-1",
    )
    second = store.request_cancel(
        job_id="job-1",
        reason="user",
        actor="user",
        idempotency_key="cancel-1",
    )
    assert first.status == "cancelled"
    assert second.status == "cancelled"
    assert first.version == second.version


def contract_terminal_fencing(store) -> None:
    submit_fixture(store)
    claim = _register_and_claim(
        store, worker_id="worker-a"
    )
    store.mark_succeeded(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        result={},
        actor="worker-a",
    )
    try:
        store.mark_cancelled(
            job_id=claim.job.job_id,
            claim_token=claim.claim_token,
            reason="late",
            actor="worker-a",
        )
    except LeaseLostError:
        return
    raise AssertionError(
        "terminal Job 后旧 token 不能再写终态"
    )


def contract_lease_requeue_fences_old_token(
    store,
) -> None:
    submit_fixture(store)
    claim = _register_and_claim(
        store, worker_id="worker-a", lease_seconds=0
    )
    expired = store.list_expired_running(limit=10)
    assert any(
        j.job_id == claim.job.job_id for j in expired
    )
    store.requeue_expired(
        job_id=claim.job.job_id,
        expired_claim_token=claim.claim_token,
        detail="lease expired",
        actor="reconciler",
    )
    try:
        store.heartbeat(
            job_id=claim.job.job_id,
            claim_token=claim.claim_token,
            lease_seconds=30,
        )
    except LeaseLostError:
        return
    raise AssertionError(
        "requeue 后旧 token 不能 heartbeat"
    )


def contract_retry_scheduled_not_immediately_claimable(
    store,
) -> None:
    submit_fixture(store, max_attempts=3)
    claim = _register_and_claim(
        store, worker_id="worker-a"
    )
    failed = store.mark_failed(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        error={"type": "Transient", "message": "boom"},
        actor="worker-a",
        retryable=True,
    )
    assert failed.status == "queued"
    # backoff 把 available_at 推到未来，立即 claim 拿不到。
    assert (
        _register_and_claim(
            store, worker_id="worker-b"
        )
        is None
    )


def contract_event_ordering_and_events_after(
    store,
) -> None:
    submit_fixture(store)
    events = store.list_events("job-1")
    types = [e.event_type for e in events]
    assert "job_submitted" in types
    # list_events 返回 event_id 升序，最后一个是当前最大游标。
    cursor = events[-1].event_id
    _register_and_claim(
        store, worker_id="worker-a"
    )
    tail = store.list_events_after(
        "job-1",
        after_event_id=cursor,
    )
    assert len(tail) >= 1
    assert all(e.event_id > cursor for e in tail)


def contract_global_event_cursor(store) -> None:
    """Phase 44：list_events_global_after 按全局 event_id 增序返回跨 Job 事件。"""

    submit_fixture(store, suffix="g1")
    submit_fixture(store, suffix="g2")

    initial = store.list_events_global_after(
        after_event_id=0,
        limit=100,
    )
    assert len(initial) >= 2
    assert all(
        initial[i].event_id < initial[i + 1].event_id
        for i in range(len(initial) - 1)
    )
    job_ids = {e.job_id for e in initial}
    assert "job-g1" in job_ids
    assert "job-g2" in job_ids

    cursor = initial[-1].event_id
    _register_and_claim(
        store, worker_id="worker-g"
    )
    tail = store.list_events_global_after(
        after_event_id=cursor,
        limit=100,
    )
    assert len(tail) >= 1
    assert all(e.event_id > cursor for e in tail)


def contract_waiting_event_carries_identity(store) -> None:
    """Phase 44：job_waiting_for_input 事件携带 job_version、wait_generation。"""

    submit_fixture(store, suffix="we")
    claim = _register_and_claim(
        store, worker_id="worker-we"
    )
    store.mark_waiting(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={"message": "ok"},
            )
        ],
        result={},
        actor="worker-we",
    )
    events = store.list_events_after(
        "job-we",
        after_event_id=0,
    )
    waiting = next(
        e for e in events
        if e.event_type == "job_waiting_for_input"
    )
    assert "job_version" in waiting.payload
    assert "wait_generation" in waiting.payload
    assert "interrupt_nodes" in waiting.payload


ALL_CONTRACTS = [
    contract_submit_is_idempotent,
    contract_submit_conflict_on_different_request,
    contract_claim_is_exclusive,
    contract_heartbeat_observes_cancel,
    contract_wait_resume_succeed,
    contract_resume_is_idempotent,
    contract_stale_wait_generation_resume_rejected,
    contract_cancel_command_is_idempotent,
    contract_terminal_fencing,
    contract_lease_requeue_fences_old_token,
    contract_retry_scheduled_not_immediately_claimable,
    contract_event_ordering_and_events_after,
    contract_global_event_cursor,
    contract_waiting_event_carries_identity,
]
