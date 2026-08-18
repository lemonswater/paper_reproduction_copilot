from __future__ import annotations

import time

from app.observability.readiness import (
    ReadinessProbe,
    ReadinessService,
    build_liveness_probe,
)


def test_liveness_always_true():
    assert build_liveness_probe() is True


def test_service_ready():
    probe = ReadinessProbe(
        name="always_ready",
        is_critical=True,
        check=lambda: "ready",
        timeout_seconds=1.0,
    )
    service = ReadinessService(component="api", probes=[probe])
    report = service.check()
    assert report.status == "ready"
    assert len(report.checks) == 1
    check = report.checks[0]
    assert check.name == "always_ready"
    assert check.status == "ready"
    assert check.latency_seconds >= 0


def test_service_not_ready_on_critical_fail():
    probe = ReadinessProbe(
        name="critical_fail",
        is_critical=True,
        check=lambda: "not_ready",
        timeout_seconds=1.0,
    )
    service = ReadinessService(component="api", probes=[probe])
    report = service.check()
    assert report.status == "not_ready"


def test_service_degraded_non_critical():
    probes = [
        ReadinessProbe(
            name="critical_ok",
            is_critical=True,
            check=lambda: "ready",
            timeout_seconds=1.0,
        ),
        ReadinessProbe(
            name="non_critical_degraded",
            is_critical=False,
            check=lambda: "degraded",
            timeout_seconds=1.0,
        ),
    ]
    service = ReadinessService(component="api", probes=probes)
    report = service.check()
    assert report.status == "degraded"


def test_service_degraded_non_critical_not_ready():
    probes = [
        ReadinessProbe(
            name="critical_ok",
            is_critical=True,
            check=lambda: "ready",
            timeout_seconds=1.0,
        ),
        ReadinessProbe(
            name="non_critical_not_ready",
            is_critical=False,
            check=lambda: "not_ready",
            timeout_seconds=1.0,
        ),
    ]
    service = ReadinessService(component="api", probes=probes)
    report = service.check()
    assert report.status == "degraded"


def test_service_timeout():
    def slow_check():
        time.sleep(1.0)
        return "ready"

    probe = ReadinessProbe(
        name="slow_critical",
        is_critical=True,
        check=slow_check,
        timeout_seconds=0.1,
    )
    service = ReadinessService(component="api", probes=[probe])
    report = service.check()
    assert report.status == "not_ready"
    assert report.checks[0].status == "not_ready"


def test_report_sorted_checks():
    probes = [
        ReadinessProbe(
            name="b",
            is_critical=True,
            check=lambda: "ready",
            timeout_seconds=1.0,
        ),
        ReadinessProbe(
            name="a",
            is_critical=True,
            check=lambda: "ready",
            timeout_seconds=1.0,
        ),
    ]
    service = ReadinessService(component="api", probes=probes)
    report = service.check()
    assert report.checks[0].name == "a"
    assert report.checks[1].name == "b"


def test_cache_ttl_returns_same_report():
    probe = ReadinessProbe(
        name="always_ready",
        is_critical=True,
        check=lambda: "ready",
        timeout_seconds=1.0,
    )
    service = ReadinessService(component="api", probes=[probe])
    report1 = service.cached_report()
    report2 = service.cached_report()
    assert id(report1) == id(report2)
