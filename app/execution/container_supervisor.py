from __future__ import annotations

"""Phase 27 容器生命周期 Supervisor。

关键顺序：``create -> write record -> start -> inspect``。
这是 write-ahead identity journal：先持久化 container ID，再启动容器。

timeout/cancel/lease loss 发生时：
``record stop_requested -> engine.stop(exact ID) -> inspect -> terminated``
如果 inspect 失败，不能假定容器已停止，应写 ``reconciliation_required``。
"""


import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.execution.container_engine import ContainerEngine
from app.execution.container_errors import (
    ContainerIdentityMismatch,
    ContainerStateAmbiguous,
)
from app.execution.container_plan import (
    build_podman_create_tokens,
    plan_sha256,
)
from app.execution.container_records import (
    write_container_record,
)
from app.execution.container_schemas import (
    ContainerPlan,
    ContainerRuntimeRecord,
)
from app.observability.instrumentation import record_span_exception_safe
from app.observability.ports import TelemetryPort
from app.observability.runtime import build_telemetry_runtime as _build_tel


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContainerSupervisor:
    """管理容器的 create/start/inspect/stop/remove 生命周期。"""

    def __init__(
        self,
        engine: ContainerEngine,
        *,
        telemetry: TelemetryPort | None = None,
    ):
        self.engine = engine
        try:
            self.telemetry: TelemetryPort = (
                telemetry if telemetry is not None else _build_tel().telemetry
            )
        except Exception:
            from app.observability.noop import NoOpTelemetry
            self.telemetry = NoOpTelemetry()

    def _assert_owned(
        self,
        record: ContainerRuntimeRecord,
        labels: dict[str, str],
    ) -> None:
        """验证 container ownership labels 与 record 一致。"""

        expected = {
            "io.paper-copilot.managed": "true",
            "io.paper-copilot.job-id": record.job_id,
            "io.paper-copilot.run-id": record.run_id,
            "io.paper-copilot.ownership-hash": (
                record.ownership_token_hash
            ),
        }
        if any(
            labels.get(key) != value
            for key, value in expected.items()
        ):
            raise ContainerIdentityMismatch(
                "container ownership labels 不匹配"
            )

    def execute(
        self,
        *,
        plan: ContainerPlan,
        run_dir: Path,
    ) -> ContainerRuntimeRecord:
        """主执行顺序：create -> record -> start -> inspect。"""

        telemetry = self.telemetry
        start = time.monotonic()
        backend = getattr(settings, "container_runtime", None) or "podman"
        container_name = plan.name

        try:
            with telemetry.span(
                "container.run",
                attributes={
                    "backend": backend,
                    "container_name": container_name,
                },
            ) as _span:
                try:
                    tokens = build_podman_create_tokens(plan)
                    container_id = self.engine.create(tokens)

                    now = _now_iso()
                    record = ContainerRuntimeRecord(
                        job_id=plan.job_id,
                        run_id=plan.run_id,
                        ownership_token_hash=plan.ownership_token_hash,
                        container_id=container_id,
                        container_name=plan.name,
                        image_ref=plan.image_ref,
                        plan_sha256=plan_sha256(plan),
                        status="created",
                        created_at=now,
                        updated_at=now,
                    )
                    write_container_record(run_dir, record)

                    attach_code = self.engine.start_attach(container_id)
                    inspected = self.engine.inspect(container_id)
                    self._assert_owned(record, inspected.labels)
                    if inspected.container_id != container_id:
                        raise ContainerIdentityMismatch(
                            "inspect container ID 不匹配"
                        )
                    if inspected.running:
                        record.status = "reconciliation_required"
                        record.updated_at = _now_iso()
                        write_container_record(run_dir, record)
                        raise ContainerStateAmbiguous(
                            f"attach exited with {attach_code}, "
                            "but container is still running"
                        )

                    record.status = "exited"
                    record.exit_code = inspected.exit_code
                    record.oom_killed = inspected.oom_killed
                    record.updated_at = _now_iso()
                    write_container_record(run_dir, record)

                    duration = time.monotonic() - start
                    try:
                        exit_code = (
                            int(record.exit_code)
                            if record.exit_code is not None
                            else -1
                        )
                        outcome = (
                            "succeeded" if exit_code == 0 else "failed"
                        )
                        telemetry.histogram(
                            "paper_copilot_container_runtime_seconds",
                            duration,
                            {"backend": backend, "outcome": outcome},
                        )
                    except Exception:
                        pass
                    return record
                except Exception as exc:
                    duration = time.monotonic() - start
                    try:
                        record_span_exception_safe(_span, exc)
                    except Exception:
                        pass
                    try:
                        telemetry.histogram(
                            "paper_copilot_container_runtime_seconds",
                            duration,
                            {"backend": backend, "outcome": "error"},
                        )
                    except Exception:
                        pass
                    raise
        except Exception:
            raise

    def stop_and_remove(
        self,
        *,
        record: ContainerRuntimeRecord,
        run_dir: Path,
    ) -> ContainerRuntimeRecord:
        """按精确 ID 停止并移除容器。

        调用者必须先通过 ``_assert_owned`` 验证 ownership。
        如果 inspect 失败，写 ``reconciliation_required`` 而不是假定停止。
        """

        try:
            inspected = self.engine.inspect(
                record.container_id
            )
        except Exception:  # noqa: BLE001
            record.status = "reconciliation_required"
            record.updated_at = _now_iso()
            write_container_record(run_dir, record)
            return record

        if inspected.running:
            record.status = "stop_requested"
            record.updated_at = _now_iso()
            write_container_record(run_dir, record)
            self.engine.stop(
                record.container_id,
                settings.container_stop_timeout_seconds,
            )
            inspected = self.engine.inspect(
                record.container_id
            )
            if inspected.running:
                record.status = "reconciliation_required"
                record.updated_at = _now_iso()
                write_container_record(run_dir, record)
                return record

        record.status = "removed"
        record.exit_code = inspected.exit_code
        record.oom_killed = inspected.oom_killed
        record.updated_at = _now_iso()
        write_container_record(run_dir, record)
        self.engine.remove(record.container_id)
        return record
