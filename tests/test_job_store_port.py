from __future__ import annotations

from app.job_runtime.ports import JobStore
from app.job_runtime.store import (
    SqliteJobStore,
)


def test_sqlite_store_implements_job_store(
    tmp_path,
) -> None:
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )

    assert isinstance(store, JobStore)