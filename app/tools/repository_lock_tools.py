from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from app.config import settings


class RepositoryLockBusyError(RuntimeError):
    """同一个 repo 正在被另一个 patch apply 持有。"""


def repository_lock_key(repo_path: str | Path) -> str:
    canonical = str(Path(repo_path).resolve())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@contextmanager
def acquire_repository_lock(
    repo_path: str | Path,
    *,
    owner_run_id: str,
    timeout_seconds: float,
) -> Generator[str, None, None]:
    """获取跨进程排他锁；锁文件不写入论文仓库。"""

    lock_key = repository_lock_key(repo_path)
    lock_dir = settings.patch_coordination_dir / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{lock_key}.lock"

    lock_file: TextIO = lock_path.open("a+", encoding="utf-8")
    deadline = time.monotonic() + max(timeout_seconds, 0.0)

    try:
        while True:
            try:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RepositoryLockBusyError(
                        f"repository is busy: {Path(repo_path).resolve()}"
                    )
                time.sleep(0.05)

        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(
            json.dumps(
                {
                    "owner_run_id": owner_run_id,
                    "pid": os.getpid(),
                    "repo_path": str(Path(repo_path).resolve()),
                    "acquired_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        lock_file.flush()
        os.fsync(lock_file.fileno())
        yield lock_key
    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()
