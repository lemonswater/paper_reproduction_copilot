"""Phase 30 Service Host 测试。"""

from __future__ import annotations

import threading

import pytest

from app.service_host import ServiceHost


class FakeWorker:
    def __init__(self):
        self.started = threading.Event()
        self.closed = False

    def run_forever(self, *, stop_event, **_kwargs):
        self.started.set()
        try:
            stop_event.wait(5)
        finally:
            # 模拟 JobWorker.run_forever() 自己的
            # finally/close 语义。
            self.closed = True


def test_host_starts_and_stops_both_workers():
    job_worker = FakeWorker()
    resource_worker = FakeWorker()
    host = ServiceHost(
        job_worker_factory=lambda: job_worker,
        resource_worker_factory=lambda: resource_worker,
        resource_poll_seconds=0.01,
    )

    host.start()
    assert job_worker.started.wait(1)
    assert resource_worker.started.wait(1)
    assert host.readiness() == "ready"

    host.stop(timeout_seconds=1)

    assert job_worker.closed
    assert resource_worker.closed
    assert all(
        not thread.is_alive()
        for thread in host.threads
    )


def test_factory_failure_does_not_start_half_a_stack():
    job_worker = FakeWorker()

    def fail_resource_factory():
        raise RuntimeError("resource init failed")

    host = ServiceHost(
        job_worker_factory=lambda: job_worker,
        resource_worker_factory=fail_resource_factory,
        resource_poll_seconds=0.01,
    )

    with pytest.raises(RuntimeError, match="resource init failed"):
        host.start()

    assert host.threads == []
    assert not job_worker.started.is_set()


def test_worker_failure_marks_host_not_ready():
    class CrashWorker:
        def run_forever(self, **_kwargs):
            raise RuntimeError("worker crashed")

    host = ServiceHost(
        job_worker_factory=lambda: CrashWorker(),
        resource_worker_factory=lambda: CrashWorker(),
        resource_poll_seconds=0.01,
    )

    host.start()
    # 等待线程退出
    for thread in host.threads:
        thread.join(timeout=2)

    assert host.readiness() == "not_ready"
