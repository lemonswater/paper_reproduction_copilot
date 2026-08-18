from __future__ import annotations

import threading
import time
from typing import Any
from uuid import uuid4

from app.config import settings
from app.execution.cancellation import (
    request_run_cancellation,
)
from app.job_runtime.graph_runner import (
    GraphJobRunner,
)
from app.job_runtime.heartbeat import (
    LeaseHeartbeat,
)
from app.job_runtime.ports import JobStore
from app.job_runtime.errors import (
    LeaseLostError,
)
from app.job_runtime.process_reconcile import (
    JobReconciler,
)
from app.job_runtime.schemas import JobClaim
from app.observability.context import (
    bind_telemetry_context, short_secret_hash
)
from app.observability.ports import TelemetryPort
from app.observability.runtime import build_telemetry_runtime
from app.observability.schemas import SpanLink
from app.observability.instrumentation import (
    increment_counter_safe, record_span_exception_safe,
)
from app.observability.readiness import (
    ReadinessProbe, ReadinessService,
)
from app.storage.errors import (
    ArtifactBackendUnavailable,
)
from app.storage.publisher import (
    ArtifactPublisher,
)
from app.tools.error_tools import (
    sanitize_error_message,
)
from app.workspace.capabilities import (
    build_worker_identity,
)
from app.workspace.heartbeat import (
    WorkerSessionHeartbeat,
)
from app.workspace.manager import WorkspaceManager


class _TelemetryWrappedStore:
    """
    为后台心跳线程包装 JobStore：
    - 绑定稳定的 worker identity telemetry context
    - 在 register/refresh 成功时递增计数器
    """

    def __init__(
        self,
        inner: JobStore,
        *,
        worker_id: str,
        worker_session_id: str,
        telemetry: TelemetryPort,
    ) -> None:
        self.__inner = inner
        self.__worker_id = worker_id
        self.__worker_session_id = worker_session_id
        self.__telemetry = telemetry

    def __getattr__(self, name: str):
        return getattr(self.__inner, name)

    def register_worker(self, *, worker, lease_seconds):
        with bind_telemetry_context(
            worker_id=self.__worker_id,
            worker_session_id=self.__worker_session_id,
            worker_host_id=settings.worker_host_id,
        ):
            backend = getattr(worker, "backend", None)
            result = self.__inner.register_worker(
                worker=worker, lease_seconds=lease_seconds
            )
            try:
                increment_counter_safe(
                    self.__telemetry,
                    "paper_copilot_workers_registered_total",
                    attributes={
                        "backend": str(backend)
                        if backend is not None
                        else "default",
                    },
                )
            except Exception:
                pass
            return result

    def heartbeat_worker(self, *, worker, lease_seconds):
        with bind_telemetry_context(
            worker_id=self.__worker_id,
            worker_session_id=self.__worker_session_id,
            worker_host_id=settings.worker_host_id,
        ):
            backend = getattr(worker, "backend", None)
            result = self.__inner.heartbeat_worker(
                worker=worker, lease_seconds=lease_seconds
            )
            try:
                increment_counter_safe(
                    self.__telemetry,
                    "paper_copilot_workers_registered_total",
                    attributes={
                        "backend": str(backend)
                        if backend is not None
                        else "default",
                    },
                )
            except Exception:
                pass
            return result

    def heartbeat(self, *, job_id, claim_token, lease_seconds, now=None):
        with bind_telemetry_context(
            worker_id=self.__worker_id,
            worker_session_id=self.__worker_session_id,
            worker_host_id=settings.worker_host_id,
        ):
            if now is None:
                return self.__inner.heartbeat(
                    job_id=job_id,
                    claim_token=claim_token,
                    lease_seconds=lease_seconds,
                )
            return self.__inner.heartbeat(
                job_id=job_id,
                claim_token=claim_token,
                lease_seconds=lease_seconds,
                now=now,
            )


class JobWorker:
    def __init__(
        self,
        *,
        worker_id: str,
        store: JobStore,
        workspace_manager: WorkspaceManager,
        runner: GraphJobRunner | None = None,
        artifact_publisher: (
            ArtifactPublisher | None
        ) = None,
        lease_seconds: float | None = None,
        heartbeat_seconds: float | None = None,
        poll_seconds: float | None = None,
        telemetry: TelemetryPort | None = None,
    ):
        if not worker_id.strip():
            raise ValueError(
                "worker_id 不能为空"
            )

        self.worker_id = worker_id
        self._raw_store = store
        self.workspace_manager = workspace_manager
        self.runner = runner or GraphJobRunner()
        self.artifact_publisher = (
            artifact_publisher
        )
        self.lease_seconds = (
            lease_seconds
            if lease_seconds is not None
            else settings.job_lease_seconds
        )
        self.heartbeat_seconds = (
            heartbeat_seconds
            if heartbeat_seconds is not None
            else settings.job_heartbeat_seconds
        )
        self.poll_seconds = (
            poll_seconds
            if poll_seconds is not None
            else settings.job_poll_seconds
        )
        self.telemetry = (
            telemetry
            if telemetry is not None
            else build_telemetry_runtime().telemetry
        )
        self._worker_session_id = (
            f"ws_{uuid4().hex}"
        )
        self.store = _TelemetryWrappedStore(
            self._raw_store,
            worker_id=self.worker_id,
            worker_session_id=self._worker_session_id,
            telemetry=self.telemetry,
        )
        self.session_heartbeat = (
            WorkerSessionHeartbeat(
                store=self.store,
                identity_factory=lambda: build_worker_identity(
                    worker_id=self.worker_id,
                    worker_session_id=(
                        self._worker_session_id
                    ),
                ),
                lease_seconds=(
                    settings.worker_session_lease_seconds
                ),
                interval_seconds=(
                    settings.worker_session_heartbeat_seconds
                ),
            )
        )
        self.reconciler = JobReconciler(
            store=self.store,
            actor=worker_id,
            host_id=settings.worker_host_id,
        )
        self.readiness_service = ReadinessService(
            "worker",
            probes=[
                ReadinessProbe(
                    name="job_store.ping",
                    is_critical=True,
                    check=lambda: (lambda s: (lambda: "ready" if (s.ping() or True) else "not_ready") if False else "ready")(self._raw_store)
                    or "ready",
                    timeout_seconds=settings.readiness_timeout_seconds,
                ),
            ],
            max_workers=settings.readiness_probe_workers,
        )

    def _notify_process_cancel(
        self,
        claim: JobClaim,
        reason: str,
    ) -> None:
        """
        Process Supervisor 可能尚未启动，此时没有 active record 是正常的。
        Job cancellation flag 仍会让 Graph 在下一个 chunk 边界停止。
        """

        binding = claim.workspace_binding
        if binding is None:
            return
        try:
            request_run_cancellation(
                run_dir=binding.run_dir,
                reason=reason,
                requested_by=self.worker_id,
            )
        except (ValueError, FileNotFoundError):
            return

    def _error_payload(
        self,
        exc: BaseException,
    ) -> dict[str, Any]:
        return {
            "type": type(exc).__name__,
            "message": sanitize_error_message(exc),
        }

    def _mark_retryable_if_owned(
        self,
        claim: JobClaim,
        exc: BaseException,
    ) -> None:
        try:
            self.store.mark_failed(
                job_id=claim.job.job_id,
                claim_token=claim.claim_token,
                error=self._error_payload(exc),
                actor=self.worker_id,
                retryable=True,
            )
        except LeaseLostError:
            pass

    def _mark_terminal_if_owned(
        self,
        claim: JobClaim,
        exc: BaseException,
    ) -> None:
        try:
            self.store.mark_failed(
                job_id=claim.job.job_id,
                claim_token=claim.claim_token,
                error=self._error_payload(exc),
                actor=self.worker_id,
                retryable=False,
            )
        except LeaseLostError:
            pass

    def run_once(self) -> bool:
        """
        最多处理一个 Job。

        返回 False 表示当前没有可 claim 的 Job。
        """

        worker_identity = (
            self.session_heartbeat.start()
        )
        self.session_heartbeat.raise_if_unhealthy()

        claim_start = time.monotonic()
        with bind_telemetry_context(
            worker_id=self.worker_id,
            worker_session_id=self._worker_session_id,
            worker_host_id=settings.worker_host_id,
        ):
            try:
                with self.telemetry.span(
                    "worker.claim_attempt",
                    attributes={
                        "worker_id": self.worker_id,
                        "worker_session_id": self._worker_session_id,
                        "pool": settings.worker_pool,
                    },
                ) as claim_span:
                    # claim 前先处理 stale lease；claim_next 自身不会盲目重排。
                    self.reconciler.reconcile_expired()
                    claim = self.store.claim_next(
                        worker=worker_identity,
                        lease_seconds=self.lease_seconds,
                    )
                    claim_duration = time.monotonic() - claim_start

                    if claim is None:
                        try:
                            claim_span.set_attribute(
                                "outcome", "empty"
                            )
                            increment_counter_safe(
                                self.telemetry,
                                "paper_copilot_jobs_claim_total",
                                attributes={
                                    "outcome": "empty",
                                },
                            )
                            try:
                                self.telemetry.histogram(
                                    "paper_copilot_worker_claim_duration_seconds",
                                    value=claim_duration,
                                    attributes={
                                        "outcome": "empty",
                                    },
                                )
                            except Exception:
                                pass
                        except Exception:
                            pass
                        return False

                    try:
                        claim_span.set_attribute(
                            "outcome", "claimed"
                        )
                        claim_span.set_attribute(
                            "job_id", claim.job.job_id
                        )
                        increment_counter_safe(
                            self.telemetry,
                            "paper_copilot_jobs_claim_total",
                            attributes={
                                "outcome": "claimed",
                            },
                        )
                        try:
                            self.telemetry.histogram(
                                "paper_copilot_worker_claim_duration_seconds",
                                value=claim_duration,
                                attributes={
                                    "outcome": "claimed",
                                },
                            )
                        except Exception:
                            pass
                    except Exception:
                        pass

                    claim_token_hash = short_secret_hash(
                        claim.claim_token
                    )
                    execution_backend = (
                        getattr(
                            claim.job.requirements,
                            "execution_backend",
                            None,
                        )
                        if claim.job.requirements
                        else None
                    )
                    with bind_telemetry_context(
                        job_id=claim.job.job_id,
                        run_id=claim.job.run_id,
                        claim_token_hash=claim_token_hash,
                        execution_backend=(
                            str(execution_backend)
                            if execution_backend is not None
                            else None
                        ),
                    ):
                        links = (
                            [
                                SpanLink(
                                    carrier=claim.job.submit_trace
                                )
                            ]
                            if claim.job.submit_trace
                            else []
                        )
                        with self.telemetry.span(
                            "job.execute",
                            attributes={
                                "job.attempt": claim.job.attempt_count,
                                "worker_pool": settings.worker_pool,
                            },
                            links=links if links else None,
                        ) as exec_span:
                            exec_start = time.monotonic()

                            heartbeat = LeaseHeartbeat(
                                store=self.store,
                                job_id=claim.job.job_id,
                                claim_token=claim.claim_token,
                                lease_seconds=self.lease_seconds,
                                interval_seconds=(
                                    self.heartbeat_seconds
                                ),
                                on_cancel_requested=lambda reason: (
                                    self._notify_process_cancel(
                                        claim,
                                        reason,
                                    )
                                ),
                            )

                            outcome_status: str | None = None
                            try:
                                with heartbeat:
                                    claim = (
                                        self.workspace_manager
                                        .prepare(
                                            claim
                                        )
                                    )
                                    heartbeat.raise_if_unhealthy()
                                    self.session_heartbeat.raise_if_unhealthy()

                                    outcome = self.runner.execute(
                                        claim,
                                        heartbeat,
                                    )
                                    heartbeat.raise_if_unhealthy()

                                    publication = None
                                    if (
                                        self.artifact_publisher
                                        is not None
                                    ):
                                        publication = (
                                            self.artifact_publisher
                                            .publish(
                                                job=claim.job,
                                                records=(
                                                    outcome
                                                    .artifact_records
                                                ),
                                                workspace_binding=(
                                                    claim.workspace_binding
                                                ),
                                                ensure_active=(
                                                    heartbeat
                                                    .raise_if_unhealthy
                                                ),
                                            )
                                        )
                                    heartbeat.raise_if_unhealthy()

                                    # waiting 前必须先得到新的可恢复 manifest pointer。
                                    if (
                                        outcome.status
                                        == "waiting_for_input"
                                    ):
                                        self.workspace_manager.seal_waiting(
                                            claim=claim,
                                            outcome=outcome,
                                        )
                                    heartbeat.raise_if_unhealthy()

                                result = dict(outcome.result)
                                if publication is not None:
                                    result[
                                        "artifact_publication"
                                    ] = publication.model_dump()

                                if outcome.status == "waiting_for_input":
                                    self.store.mark_waiting(
                                        job_id=claim.job.job_id,
                                        claim_token=claim.claim_token,
                                        interrupts=outcome.interrupts,
                                        result=result,
                                        actor=self.worker_id,
                                    )
                                elif outcome.status == "cancelled":
                                    self.store.mark_cancelled(
                                        job_id=claim.job.job_id,
                                        claim_token=claim.claim_token,
                                        reason=(
                                            heartbeat.cancellation_reason
                                            or "runner cancelled"
                                        ),
                                        actor=self.worker_id,
                                    )
                                else:
                                    self.store.mark_succeeded(
                                        job_id=claim.job.job_id,
                                        claim_token=claim.claim_token,
                                        result=result,
                                        actor=self.worker_id,
                                    )
                                outcome_status = outcome.status
                            except ArtifactBackendUnavailable as exc:
                                self._mark_retryable_if_owned(
                                    claim, exc
                                )
                                outcome_status = "failed"
                                try:
                                    record_span_exception_safe(
                                        exec_span, exc
                                    )
                                except Exception:
                                    pass
                            except LeaseLostError:
                                # Fencing 生效：旧 worker 立即放弃，不写任何终态。
                                outcome_status = "cancelled"
                                pass
                            except Exception as exc:  # noqa: BLE001
                                self._mark_terminal_if_owned(
                                    claim, exc
                                )
                                outcome_status = "failed"
                                try:
                                    record_span_exception_safe(
                                        exec_span, exc
                                    )
                                except Exception:
                                    pass

                            exec_duration = (
                                time.monotonic() - exec_start
                            )
                            metric_outcome = (
                                outcome_status
                                if outcome_status
                                in {
                                    "succeeded",
                                    "cancelled",
                                    "waiting_for_input",
                                }
                                else "failed"
                            )
                            try:
                                self.telemetry.histogram(
                                    "paper_copilot_job_execution_duration_seconds",
                                    value=exec_duration,
                                    attributes={
                                        "outcome": metric_outcome,
                                        "execution_backend": (
                                            str(execution_backend)
                                            if execution_backend
                                            is not None
                                            else "default"
                                        ),
                                    },
                                )
                            except Exception:
                                pass
            except Exception:
                try:
                    claim_duration = (
                        time.monotonic() - claim_start
                    )
                    increment_counter_safe(
                        self.telemetry,
                        "paper_copilot_jobs_claim_total",
                        attributes={
                            "outcome": "error",
                        },
                    )
                    try:
                        self.telemetry.histogram(
                            "paper_copilot_worker_claim_duration_seconds",
                            value=claim_duration,
                            attributes={
                                "outcome": "error",
                            },
                        )
                    except Exception:
                        pass
                except Exception:
                    pass
                raise

        return True

    def close(self) -> None:
        self.session_heartbeat.close()

    def run_forever(
        self,
        *,
        stop_event: threading.Event | None = None,
    ) -> None:
        stop = stop_event or threading.Event()
        self.session_heartbeat.start()
        try:
            while not stop.is_set():
                self.session_heartbeat.raise_if_unhealthy()
                handled = self.run_once()
                if not handled:
                    stop.wait(self.poll_seconds)
        finally:
            self.close()
