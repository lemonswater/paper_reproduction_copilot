from __future__ import annotations

import atexit
import os
import threading
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url

from app.config import settings
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService


_lock = threading.Lock()
_engine: Engine | None = None
_engine_pid: int | None = None


def require_database_url(
    *,
    secret_service: SecretService | None = None,
) -> str:
    if secret_service is None:
        from app.secrets.factory import build_secret_service

        secret_service = build_secret_service()

    material = secret_service.resolve_current(
        name=settings.database_url_secret_name,
        use=SecretUse.DATABASE,
        actor="database:engine",
    )
    value = material.reveal()
    parsed = make_url(value)
    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError(
            "Phase 41 DATABASE_URL Secret 必须指向 PostgreSQL"
        )
    return value


def build_engine() -> Engine:
    """返回当前进程唯一 Engine；fork 后重新创建 pool。"""

    global _engine, _engine_pid
    pid = os.getpid()
    with _lock:
        if _engine is not None and _engine_pid == pid:
            return _engine

        if _engine is not None:
            # 子进程不能继承父进程已经建立的 socket。
            _engine.dispose(close=False)

        options = (
            "-c statement_timeout="
            f"{settings.database_statement_timeout_ms} "
            "-c lock_timeout="
            f"{settings.database_lock_timeout_ms}"
        )
        _engine = sa.create_engine(
            require_database_url(),
            pool_pre_ping=True,
            hide_parameters=True,
            pool_size=settings.database_pool_size,
            max_overflow=(
                settings.database_max_overflow
            ),
            pool_timeout=(
                settings.database_pool_timeout_seconds
            ),
            connect_args={
                "options": options,
                "application_name": (
                    "paper-reproduction-copilot"
                ),
            },
        )
        _engine_pid = pid
        return _engine


def database_clock(
    connection: sa.Connection,
) -> datetime:
    """
    使用真实推进的数据库时钟。

    PostgreSQL now()/CURRENT_TIMESTAMP 在一个事务中固定；lease 语义使用
    clock_timestamp() 更明确。
    """

    return connection.execute(
        sa.select(sa.func.clock_timestamp())
    ).scalar_one()


def psycopg_conninfo() -> str:
    """把 SQLAlchemy URL 转为 Psycopg 可接受的 URL。"""

    parsed = make_url(require_database_url())
    return parsed.set(
        drivername="postgresql"
    ).render_as_string(hide_password=False)


def ping_database() -> None:
    with build_engine().connect() as connection:
        connection.execute(sa.text("SELECT 1"))


def close_engine() -> None:
    global _engine, _engine_pid
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _engine_pid = None


atexit.register(close_engine)
