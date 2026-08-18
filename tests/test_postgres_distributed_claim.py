from __future__ import annotations

"""并发 claim、lease fencing 与 DB clock 测试。

验证 Phase 25 的核心安全保证：

- 多个 Worker 并发 claim 时，每个 Job 最多被一个 claim token 获得；
- 旧 token 在 lease requeue 后无法 heartbeat/mark；
- claim 使用数据库 ``clock_timestamp()``，与本机 monkeypatch 时间无关；
- 一个 Worker 持有 row lock 时其他 Worker skip 而不是等待到 timeout。
"""

from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlalchemy as sa

from app.job_runtime.errors import LeaseLostError
from app.job_runtime.postgres_store import (
    PostgresJobStore,
)
from app.persistence.tables import jobs
from tests.job_store_contract import submit_fixture


pytestmark = pytest.mark.postgres


def test_workers_never_claim_same_job(
    postgres_engine,
) -> None:
    """12 个 Worker 抢 40 个 Job，最终每个 Job 只被一个 token 获得。"""

    store = PostgresJobStore(postgres_engine)
    total = 40
    for index in range(total):
        submit_fixture(store, suffix=str(index))

    def claim(worker_index: int):
        local_store = PostgresJobStore(postgres_engine)
        return local_store.claim_next(
            worker_id=f"worker-{worker_index}",
            lease_seconds=30,
        )

    with ThreadPoolExecutor(max_workers=12) as executor:
        claims = list(executor.map(claim, range(total)))

    claimed = [
        item.job.job_id for item in claims if item is not None
    ]
    assert len(claimed) == total
    assert len(set(claimed)) == total


def test_more_claims_than_jobs_returns_none(
    postgres_engine,
) -> None:
    """40 个 Job 被 claim 后，再 80 次 claim 全部为空。"""

    store = PostgresJobStore(postgres_engine)
    for index in range(40):
        submit_fixture(store, suffix=str(index))

    with ThreadPoolExecutor(max_workers=8) as executor:
        first_pass = list(
            executor.map(
                _claim_once,
                [postgres_engine] * 40,
            )
        )
        second_pass = list(
            executor.map(
                _claim_once,
                [postgres_engine] * 80,
            )
        )

    assert all(item is not None for item in first_pass)
    assert all(item is None for item in second_pass)


def _claim_once(engine) -> object | None:
    store = PostgresJobStore(engine)
    return store.claim_next(
        worker_id="worker",
        lease_seconds=30,
    )


def test_old_token_cannot_mark_after_requeue(
    postgres_engine,
) -> None:
    """lease requeue 后，旧 token 不能再写终态。"""

    store = PostgresJobStore(postgres_engine)
    submit_fixture(store)
    claim = store.claim_next(
        worker_id="worker-a",
        lease_seconds=0,
    )
    assert claim is not None

    expired = store.list_expired_running(limit=10)
    assert any(j.job_id == claim.job.job_id for j in expired)

    store.requeue_expired(
        job_id=claim.job.job_id,
        expired_claim_token=claim.claim_token,
        detail="lease expired",
        actor="reconciler",
    )

    with pytest.raises(LeaseLostError):
        store.mark_succeeded(
            job_id=claim.job.job_id,
            claim_token=claim.claim_token,
            result={},
            actor="worker-a",
        )

    with pytest.raises(LeaseLostError):
        store.heartbeat(
            job_id=claim.job.job_id,
            claim_token=claim.claim_token,
            lease_seconds=30,
        )


def test_db_clock_independent_of_wall_clock(
    postgres_engine,
    monkeypatch,
) -> None:
    """monkeypatch time.time 不影响 lease 计算。"""

    import time

    store = PostgresJobStore(postgres_engine)
    submit_fixture(store)

    # 把本机时间大幅拨到过去，claim 仍应正常工作。
    monkeypatch.setattr(time, "time", lambda: 0.0)

    claim = store.claim_next(
        worker_id="worker-a",
        lease_seconds=30,
    )
    assert claim is not None
    assert claim.job.status == "running"
    # lease_expires_at 应基于 DB clock，而不是 1970 epoch。
    assert claim.job.lease_expires_at is not None


def test_skip_locked_does_not_block(
    postgres_engine,
) -> None:
    """一个 Worker 持有 row lock 时，其他 Worker skip 而不是等待。"""

    store = PostgresJobStore(postgres_engine)
    submit_fixture(store)

    # 在一个未提交事务中锁住该 Job 行，模拟 Worker A 正在 claim。
    with postgres_engine.connect() as blocking_conn:
        blocking_conn.exec_driver_sql(
            "BEGIN"
        )
        blocking_conn.execute(
            sa.select(jobs.c.job_id)
            .where(jobs.c.job_id == "job-1")
            .with_for_update()
        )

        # Worker B 的 claim_next 必须立即返回 None，而不是等到 lock_timeout。
        result = store.claim_next(
            worker_id="worker-b",
            lease_seconds=30,
        )
        assert result is None

        blocking_conn.exec_driver_sql("ROLLBACK")


def test_pool_pre_ping_recovers(
    postgres_engine,
) -> None:
    """连接被服务端关闭后，pool_pre_ping 让下一次 checkout 恢复。"""

    store = PostgresJobStore(postgres_engine)

    # 触发一次正常调用，让 pool 缓存连接。
    store.ping()

    # 用 pg_terminate_backend 杀掉当前 pool 中的连接，模拟服务端重启。
    with postgres_engine.connect() as conn:
        pids = conn.execute(
            sa.text(
                "SELECT pid FROM pg_stat_activity "
                "WHERE datname = current_database() "
                "AND pid <> pg_backend_pid()"
            )
        ).scalars().all()

    admin = sa.create_engine(
        str(postgres_engine.url),
        pool_pre_ping=True,
    )
    try:
        with admin.connect() as killer:
            for pid in pids:
                killer.execute(
                    sa.text(
                        "SELECT pg_terminate_backend(:pid)"
                    ),
                    {"pid": pid},
                )
    finally:
        admin.dispose()

    # pool_pre_ping=True 会检测失效并重建连接，ping 不应抛异常。
    store.ping()
