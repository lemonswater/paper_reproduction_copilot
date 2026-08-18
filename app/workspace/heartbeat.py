from __future__ import annotations

import threading
from collections.abc import Callable

from app.job_runtime.ports import JobStore
from app.workspace.schemas import WorkerIdentity


class WorkerSessionHeartbeat:
    """Worker 空闲或执行 Graph 时都续 session lease。"""

    def __init__(
        self,
        *,
        store: JobStore,
        identity_factory: Callable[[], WorkerIdentity],
        lease_seconds: float,
        interval_seconds: float,
    ):
        self.store = store
        self.identity_factory = identity_factory
        self.lease_seconds = lease_seconds
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._identity: WorkerIdentity | None = None
        self._error: BaseException | None = None

    @property
    def identity(self) -> WorkerIdentity:
        with self._lock:
            if self._identity is None:
                raise RuntimeError(
                    "Worker session 尚未启动"
                )
            return self._identity

    def _refresh(self) -> None:
        identity = self.identity_factory()
        self.store.heartbeat_worker(
            worker=identity,
            lease_seconds=self.lease_seconds,
        )
        with self._lock:
            self._identity = identity

    def _loop(self) -> None:
        while not self._stop.wait(
            self.interval_seconds
        ):
            try:
                self._refresh()
            except BaseException as exc:  # noqa: BLE001
                with self._lock:
                    self._error = exc
                return

    def start(self) -> WorkerIdentity:
        with self._lock:
            existing = self._thread
            current_identity = self._identity
        if existing is not None:
            if current_identity is None:
                raise RuntimeError(
                    "Worker heartbeat 状态不一致"
                )
            return current_identity

        identity = self.identity_factory()
        self.store.register_worker(
            worker=identity,
            lease_seconds=self.lease_seconds,
        )
        thread = threading.Thread(
            target=self._loop,
            name=(
                f"worker-session-"
                f"{identity.worker_session_id}"
            ),
            daemon=True,
        )
        with self._lock:
            if self._thread is not None:
                raise RuntimeError(
                    "Worker heartbeat 被并发启动"
                )
            self._identity = identity
            self._thread = thread
        thread.start()
        return identity

    def raise_if_unhealthy(self) -> None:
        with self._lock:
            error = self._error
        if error is not None:
            raise RuntimeError(
                "Worker session heartbeat failed"
            ) from error

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(
                timeout=max(
                    self.interval_seconds * 2,
                    1.0,
                )
            )
        identity = self._identity
        if identity is not None:
            try:
                self.store.drain_worker(
                    worker_session_id=(
                        identity.worker_session_id
                    )
                )
            except Exception:  # noqa: BLE001, S110
                # 关闭路径不能覆盖当前 Job 的真实结果。
                pass
