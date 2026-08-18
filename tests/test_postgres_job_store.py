from __future__ import annotations

"""PostgreSQL JobStore contract tests.

把后端无关的 contract 逐个应用到 ``PostgresJobStore``。只有 SQLite 与
PostgreSQL 都通过同一组 contract，factory 切换才可信。

所有测试都需要 ``TEST_DATABASE_URL``；未设置时由 ``postgres_engine`` fixture
自动 skip。每个测试用例使用独立的 ``PostgresJobStore`` 实例，但共享同一个
``postgres_engine``（schema 在 fixture 期间只创建一次）。
"""

import pytest

from app.job_runtime.postgres_store import (
    PostgresJobStore,
)
from tests.job_store_contract import (
    ALL_CONTRACTS,
)


pytestmark = pytest.mark.postgres


@pytest.fixture
def store(postgres_engine):
    return PostgresJobStore(postgres_engine)


def test_postgres_ping(store) -> None:
    # initialize 只 ping，不 create_all；schema 由 fixture 创建。
    store.ping()


def test_postgres_close_is_noop(store) -> None:
    # Engine 由 persistence 模块统一释放，close 不抛异常即可。
    store.close()


@pytest.mark.parametrize(
    "contract",
    ALL_CONTRACTS,
    ids=[c.__name__ for c in ALL_CONTRACTS],
)
def test_postgres_contract(store, contract) -> None:
    """每个 contract 在 PostgreSQL 后端上都必须通过。"""

    contract(store)
