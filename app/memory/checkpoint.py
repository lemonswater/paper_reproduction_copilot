import atexit
import sqlite3
from typing import Optional
from langgraph.checkpoint.sqlite import SqliteSaver
from app.config import settings

_conn: Optional[sqlite3.Connection] = None
_checkpointer: Optional[SqliteSaver] = None

def build_checkpointer() -> SqliteSaver:
    global _conn, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(
        settings.checkpoint_db_path,
        check_same_thread=False
    )
    _checkpointer = SqliteSaver(_conn)
    return _checkpointer

def close_checkpointer() -> None:
    global _conn, _checkpointer

    if _conn is not None:
        _conn.close()

    _conn = None
    _checkpointer = None

atexit.register(close_checkpointer)