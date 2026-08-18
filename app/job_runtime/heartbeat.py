from __future__ import annotations

import threading
from collections.abc import Callable

from app.job_runtime.errors import (
    LeaseLostError,
)
from app.job_runtime.store import (
    SqliteJobStore,
)


class JobCancellationRequested(RuntimeError):
    pass


class LeaseHeartbeat:
    """
    为一次 claim 维护 lease。

    线程本身不抛异常到 worker 主线程，而是保存错误；Graph runner 在节点
    chunk 边界调用 raise_if_unhealthy()，以协作方式停止。
    """

    def __init__(
        self,
        *,
        store: SqliteJobStore,
        job_id: str,
        claim_token: str,
        lease_seconds: float,
        interval_seconds: float,
        on_cancel_requested: (
            Callable[[str], None] | None
        ) = None,
    ):
        if interval_seconds <= 0:
            raise ValueError(
                "heartbeat interval 必须大于 0"
            )
        if lease_seconds <= interval_seconds * 2:
            raise ValueError(
                "lease 必须大于两倍 heartbeat interval"
            )

        self.store = store
        self.job_id = job_id
        self.claim_token = claim_token
        self.lease_seconds = lease_seconds
        self.interval_seconds = interval_seconds
        self.on_cancel_requested = (
            on_cancel_requested
        )

        self._stop_event = threading.Event()
        self._cancel_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._error: BaseException | None = None
        self._cancellation_reason: str | None = None
        self._cancel_callback_called = False

    @property
    def cancellation_requested(self) -> bool:
        return self._cancel_event.is_set()

    @property
    def cancellation_reason(self) -> str | None:
        return self._cancellation_reason

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError(
                "heartbeat 已经启动"
            )
        self._thread = threading.Thread(
            target=self._run,
            name=f"job-heartbeat-{self.job_id}",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.wait(
            self.interval_seconds
        ):
            try:
                result = self.store.heartbeat(
                    job_id=self.job_id,
                    claim_token=self.claim_token,
                    lease_seconds=self.lease_seconds,
                )
            except BaseException as exc:  # noqa: BLE001
                self._error = exc
                self._stop_event.set()
                return

            if result.cancel_requested:
                self._cancellation_reason = (
                    result.cancellation_reason
                    or "job cancellation requested"
                )
                self._cancel_event.set()

                if (
                    self.on_cancel_requested
                    is not None
                    and not self._cancel_callback_called
                ):
                    self._cancel_callback_called = True
                    try:
                        self.on_cancel_requested(
                            self._cancellation_reason
                        )
                    except BaseException as exc:  # noqa: BLE001
                        # 无法通知 Supervisor 时不能假装取消已经生效。
                        self._error = exc
                        self._stop_event.set()
                        return

    def raise_if_unhealthy(self) -> None:
        if self._error is not None:
            if isinstance(
                self._error,
                LeaseLostError,
            ):
                raise self._error
            raise RuntimeError(
                "Job heartbeat 失败"
            ) from self._error

        if self._cancel_event.is_set():
            raise JobCancellationRequested(
                self._cancellation_reason
                or "job cancellation requested"
            )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(
                timeout=max(
                    self.interval_seconds * 2,
                    1.0,
                )
            )

    def __enter__(self) -> LeaseHeartbeat:
        self.start()
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> None:
        self.stop()