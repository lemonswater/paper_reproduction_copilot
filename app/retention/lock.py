"""单主机 Sweep 文件锁。"""
from __future__ import annotations
import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from app.retention.errors import RetentionConflict

class SingleHostSweepLock:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def acquire(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            except BlockingIOError:
                raise RetentionConflict(
                    "另一个 GC sweep 正在本机执行"
                ) from None
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
