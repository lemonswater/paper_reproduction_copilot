"""Phase 30 单进程 Stack Host。

单用户本机部署的轻量编排器，不替代 systemd/Kubernetes。
在同一个进程内启动 JobWorker 线程和 ResourceWorker 轮询线程，
API 主线程由 Uvicorn 负责。
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)


class ServiceHost:
    """协调 API、Job Worker 和 Resource Worker 的单进程编排器。"""

    def __init__(
        self,
        *,
        job_worker_factory: Callable[[], object],
        resource_worker_factory: Callable[[], object],
        resource_poll_seconds: float,
    ):
        self.job_worker_factory = job_worker_factory
        self.resource_worker_factory = (
            resource_worker_factory
        )
        self.resource_poll_seconds = resource_poll_seconds
        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []
        self.job_worker = None
        self.resource_worker = None
        self.failure: BaseException | None = None
        self._failure_lock = threading.Lock()

    def _run_worker(
        self,
        name: str,
        worker,
        **kwargs,
    ) -> None:
        try:
            worker.run_forever(**kwargs)
        except Exception as exc:
            # 不让后台线程静默死亡；readiness 必须能观察到。
            log.exception(
                "embedded %s stopped unexpectedly", name
            )
            with self._failure_lock:
                self.failure = exc
            self.stop_event.set()

    def readiness(self) -> str:
        with self._failure_lock:
            if self.failure is not None:
                return "not_ready"
        if not self.threads or any(
            not thread.is_alive()
            for thread in self.threads
        ):
            return "not_ready"
        return "ready"

    def start(self) -> None:
        self.job_worker = self.job_worker_factory()
        self.resource_worker = (
            self.resource_worker_factory()
        )

        self.threads = [
            threading.Thread(
                name="job-worker",
                target=self._run_worker,
                kwargs={
                    "name": "job-worker",
                    "worker": self.job_worker,
                    "stop_event": self.stop_event,
                },
                daemon=False,
            ),
            threading.Thread(
                name="resource-worker",
                target=self._run_worker,
                kwargs={
                    "name": "resource-worker",
                    "worker": self.resource_worker,
                    "stop_event": self.stop_event,
                    "poll_seconds": (
                        self.resource_poll_seconds
                    ),
                },
                daemon=False,
            ),
        ]
        for thread in self.threads:
            thread.start()

    def stop(
        self, timeout_seconds: float = 15.0
    ) -> None:
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=timeout_seconds)

        alive = [
            thread.name
            for thread in self.threads
            if thread.is_alive()
        ]
        if alive:
            raise RuntimeError(
                f"workers 未在预算内退出：{alive}"
            )
