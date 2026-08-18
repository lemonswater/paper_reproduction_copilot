from __future__ import annotations

"""SQLite JobStore contract tests.

与 ``test_postgres_job_store.py`` 共享同一组 contract，确保 SQLite 与
PostgreSQL 后端行为一致。SQLite 已有细粒度测试，这里只是把 contract 作为
等价性护栏。
"""

import pytest

from app.job_runtime.store import SqliteJobStore
from tests.job_store_contract import (
    ALL_CONTRACTS,
)


@pytest.fixture
def store(tmp_path):
    sqlite_store = SqliteJobStore(
        tmp_path / "contract.sqlite"
    )
    sqlite_store.initialize()
    return sqlite_store


@pytest.mark.parametrize(
    "contract",
    ALL_CONTRACTS,
    ids=[c.__name__ for c in ALL_CONTRACTS],
)
def test_sqlite_contract(store, contract) -> None:
    """每个 contract 在 SQLite 后端上都必须通过。"""

    contract(store)
