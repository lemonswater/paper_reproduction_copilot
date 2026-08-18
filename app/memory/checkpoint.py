from __future__ import annotations

import atexit
import sqlite3
import threading
from typing import Any

from app.config import settings


_lock = threading.Lock()
_checkpointer: Any | None = None
_sqlite_connection: sqlite3.Connection | None = None
_postgres_pool: Any | None = None


def _build_sqlite_checkpointer():
    from langgraph.checkpoint.sqlite import (
        SqliteSaver,
    )

    global _sqlite_connection
    settings.checkpoint_db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    _sqlite_connection = sqlite3.connect(
        settings.checkpoint_db_path,
        check_same_thread=False,
        timeout=30,
    )
    _sqlite_connection.execute(
        "PRAGMA journal_mode=WAL"
    )
    _sqlite_connection.execute(
        "PRAGMA synchronous=NORMAL"
    )
    _sqlite_connection.execute(
        "PRAGMA busy_timeout=30000"
    )
    return SqliteSaver(_sqlite_connection)


def _build_postgres_checkpointer():
    from langgraph.checkpoint.postgres import (
        PostgresSaver,
    )
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    from app.persistence.database import (
        psycopg_conninfo,
    )

    global _postgres_pool
    _postgres_pool = ConnectionPool(
        conninfo=psycopg_conninfo(),
        min_size=(
            settings
            .checkpoint_postgres_pool_min_size
        ),
        max_size=(
            settings
            .checkpoint_postgres_pool_max_size
        ),
        timeout=(
            settings.database_pool_timeout_seconds
        ),
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=True,
        name="langgraph-checkpoint",
    )
    _postgres_pool.wait()
    return PostgresSaver(_postgres_pool)


def build_checkpointer():
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    with _lock:
        if _checkpointer is not None:
            return _checkpointer
        if settings.checkpoint_backend == "sqlite":
            _checkpointer = (
                _build_sqlite_checkpointer()
            )
        elif settings.checkpoint_backend == "postgresql":
            _checkpointer = (
                _build_postgres_checkpointer()
            )
        else:
            raise ValueError(
                "不支持的 CHECKPOINT_BACKEND"
            )
        return _checkpointer


def setup_checkpointer() -> None:
    """显式创建/升级 Saver 自有表；只由迁移 CLI 调用。"""

    saver = build_checkpointer()
    saver.setup()


def close_checkpointer() -> None:
    global _checkpointer
    global _sqlite_connection
    global _postgres_pool

    with _lock:
        _checkpointer = None
        if _sqlite_connection is not None:
            _sqlite_connection.close()
            _sqlite_connection = None
        if _postgres_pool is not None:
            _postgres_pool.close()
            _postgres_pool = None


atexit.register(close_checkpointer)
