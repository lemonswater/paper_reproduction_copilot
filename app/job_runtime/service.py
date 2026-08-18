from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from uuid import uuid4

from app.config import settings
from app.execution.cancellation import (
    request_run_cancellation,
)
from app.execution.profile_store import (
    get_execution_profile,
)
from app.job_runtime.process_reconcile import (
    JobReconciler,
)
from app.job_runtime.schemas import (
    JobEvent,
    JobRecord,
    JobRequest,
    TERMINAL_JOB_STATUSES,
    WAITABLE_JOB_STATUSES,
)
from app.job_runtime.factory import (
    build_job_store,
)
from app.job_runtime.ports import JobStore
from app.observability.context import (
    bind_telemetry_context,
)
from app.observability.instrumentation import (
    increment_counter_safe,
)
from app.observability.ports import TelemetryPort
from app.observability.runtime import (
    build_telemetry_runtime,
)
from app.tools.artifact_tools import build_run_id
from app.workspace.capabilities import (
    requirements_from_profile,
)
from app.workspace.paths import require_managed_run_root
from app.workspace.repository import validate_manifest_hash
from app.workspace.snapshot import WorkspaceSnapshotter


def _value_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


class JobService:
    def __init__(
        self,
        store: JobStore,
        *,
        workspace_snapshotter: WorkspaceSnapshotter,
        telemetry: TelemetryPort | None = None,
        capacity_guard=None,
    ):
        self.store = store
        self.workspace_snapshotter = workspace_snapshotter
        self.capacity_guard = capacity_guard
        self.telemetry = (
            telemetry
            if telemetry is not None
            else build_telemetry_runtime().telemetry
        )
        self.store.initialize()

    def _build_initial_manifest(
        self,
        *,
        job_id: str,
        run_id: str,
        request: JobRequest,
        external_data: list,
    ):
        """根据本地路径、published Resource 或可信父 Run 构建初始 workspace manifest。"""

        if request.derived_run is not None:
            source = request.derived_run.source
            parent_job = self.store.get(source.parent_job_id)
            if parent_job.status not in TERMINAL_JOB_STATUSES:
                raise ValueError("derived parent Job 必须是终态")
            if parent_job.run_id != source.parent_run_id:
                raise ValueError("derived parent run_id 不一致")
            if (
                parent_job.workspace_manifest_id
                != source.parent_workspace_manifest_id
            ):
                raise ValueError(
                    "derived parent workspace pointer 已变化"
                )

            parent = self.store.get_workspace_manifest(
                source.parent_workspace_manifest_id
            )
            validate_manifest_hash(parent)
            if (
                parent.manifest_hash
                != source.parent_workspace_manifest_hash
                or parent.generation
                != source.parent_workspace_generation
                or parent.job_id != source.parent_job_id
                or parent.run_id != source.parent_run_id
            ):
                raise ValueError(
                    "derived parent Workspace identity 不一致"
                )
            if list(request.dataset_refs) != list(parent.external_data):
                raise ValueError(
                    "derived Job dataset references 已漂移"
                )

            return self.workspace_snapshotter.derive_initial(
                job_id=job_id,
                run_id=run_id,
                parent=parent,
                source_host_id=settings.worker_host_id,
                external_data=external_data,
            )

        if (
            request.paper_resource is not None
            or request.repo_resource is not None
        ):
            return (
                self.workspace_snapshotter.snapshot_initial_from_resources(
                    job_id=job_id,
                    run_id=run_id,
                    paper_resource=request.paper_resource,
                    repo_resource=request.repo_resource,
                    log_path=request.log_path,
                    source_host_id=settings.worker_host_id,
                    external_data=external_data,
                )
            )
        # 本地路径分支：paper_path/repo_path 此时非 None（validator 保证）。
        return self.workspace_snapshotter.snapshot_initial(
            job_id=job_id,
            run_id=run_id,
            paper_path=request.paper_path,  # type: ignore[arg-type]
            repo_path=request.repo_path,  # type: ignore[arg-type]
            log_path=request.log_path,
            source_host_id=settings.worker_host_id,
            external_data=external_data,
        )

    def submit(
        self,
        *,
        request: JobRequest,
        thread_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[JobRecord, bool]:
        if self.capacity_guard is not None:
            self.capacity_guard.assert_can_submit()

        job_id = f"job_{uuid4().hex}"
        effective_thread_id = (
            thread_id.strip()
            if thread_id
            else job_id
        )
        if (
            not effective_thread_id
            or len(effective_thread_id) > 200
        ):
            raise ValueError(
                "thread_id 长度必须为 1..200"
            )

        effective_idempotency_key = (
            idempotency_key.strip()
            if idempotency_key
            else f"submit:{effective_thread_id}"
        )
        if (
            not effective_idempotency_key
            or len(effective_idempotency_key)
            > 300
        ):
            raise ValueError(
                "idempotency_key 长度必须为 1..300"
            )

        with bind_telemetry_context(
            job_id=job_id,
            thread_id=effective_thread_id,
        ):
            with self.telemetry.span(
                "job_service.submit",
                attributes={
                    "thread_id": effective_thread_id,
                    "profile_id": (
                        request.execution_profile_id
                    ),
                },
            ) as span:
                run_id = build_run_id(
                    effective_thread_id
                )
                runs_root = settings.runs_dir.resolve()
                run_dir = (
                    runs_root / run_id
                ).resolve()
                if (
                    run_dir == runs_root
                    or runs_root
                    not in run_dir.parents
                ):
                    raise ValueError(
                        "生成的 run_dir 逃逸 RUNS_DIR"
                    )

                profile = get_execution_profile(
                    request.execution_profile_id
                )
                requirements = (
                    requirements_from_profile(
                        profile
                    )
                )

                # 第一版 external_data 可从 JobRequest.dataset_refs 传入。
                external_data = list(
                    request.dataset_refs
                )
                required_dataset_labels = {
                    item.required_worker_label
                    for item in external_data
                }
                requirements = (
                    requirements.model_copy(
                        update={
                            "required_labels": sorted(
                                set(
                                    requirements.required_labels
                                )
                                | required_dataset_labels
                            )
                        }
                    )
                )

                manifest = self._build_initial_manifest(
                    job_id=job_id,
                    run_id=run_id,
                    request=request,
                    external_data=external_data,
                )

                submit_trace = span.carrier()
                span.set_attribute(
                    "run_id", run_id
                )
                try:
                    record, created = (
                        self.store.submit(
                            job_id=job_id,
                            idempotency_key=(
                                effective_idempotency_key
                            ),
                            thread_id=effective_thread_id,
                            run_id=run_id,
                            run_dir=str(run_dir),
                            request=request,
                            requirements=requirements,
                            initial_manifest=manifest,
                            max_attempts=settings.job_max_attempts,
                            submit_trace=submit_trace,
                        )
                    )
                except Exception:
                    increment_counter_safe(
                        self.telemetry,
                        "paper_copilot_jobs_submitted_total",
                        attributes={"outcome": "error"},
                    )
                    raise
                increment_counter_safe(
                    self.telemetry,
                    "paper_copilot_jobs_submitted_total",
                    attributes={
                        "outcome": (
                            "created"
                            if created
                            else "idempotent_hit"
                        )
                    },
                )
                return record, created

    def get(self, job_id: str) -> JobRecord:
        return self.store.get(job_id)

    def list(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[JobRecord]:
        return self.store.list_jobs(
            status=status,
            limit=limit,
        )

    def events(
        self,
        job_id: str,
        *,
        limit: int = 200,
    ) -> list[JobEvent]:
        return self.store.list_events(
            job_id,
            limit=limit,
        )

    def events_after(
        self,
        job_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        """供分页查询和 SSE 共用，API 不直接访问 Store。"""

        return self.store.list_events_after(
            job_id,
            after_event_id=after_event_id,
            limit=limit,
        )

    def events_global_after(
        self,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        """供可重放派生投影使用；API 不直接访问 Store。"""

        return self.store.list_events_global_after(
            after_event_id=after_event_id,
            limit=limit,
        )

    def resume(
        self,
        *,
        job_id: str,
        expected_node: str,
        value: Any,
        idempotency_key: str | None = None,
        expected_job_version: int | None = None,
        expected_wait_generation: int | None = None,
        actor: str = "cli",
    ) -> tuple[JobRecord, bool]:
        current = self.store.get(job_id)
        key = (
            idempotency_key.strip()
            if idempotency_key
            else (
                f"resume:{job_id}:"
                f"{current.wait_generation}:"
                f"{_value_hash(value)}"
            )
        )
        if not key or len(key) > 300:
            raise ValueError(
                "idempotency_key 长度必须为 1..300"
            )
        return self.store.queue_resume(
            job_id=job_id,
            expected_node=expected_node,
            value=value,
            idempotency_key=key,
            actor=actor,
            expected_job_version=(
                expected_job_version
            ),
            expected_wait_generation=(
                expected_wait_generation
            ),
        )

    def cancel(
        self,
        *,
        job_id: str,
        reason: str,
        idempotency_key: str | None = None,
        expected_job_version: int | None = None,
        actor: str = "cli",
    ) -> JobRecord:
        record = self.store.request_cancel(
            job_id=job_id,
            reason=reason,
            actor=actor,
            idempotency_key=idempotency_key,
            expected_job_version=(
                expected_job_version
            ),
        )

        # running/cancelling 时立即桥接已有 Process Supervisor。
        # 没有活动进程可能意味着当前在 LLM 节点，不算错误。
        if record.status == "cancelling":
            try:
                request_run_cancellation(
                    run_dir=record.run_dir,
                    reason=reason,
                    requested_by=actor,
                )
            except (
                ValueError,
                FileNotFoundError,
            ):
                pass
        return record

    def wait(
        self,
        *,
        job_id: str,
        timeout_seconds: float | None,
        poll_seconds: float = 0.5,
    ) -> JobRecord:
        deadline = (
            None
            if timeout_seconds is None
            else time.monotonic()
            + timeout_seconds
        )
        while True:
            record = self.store.get(job_id)
            if record.status in WAITABLE_JOB_STATUSES:
                return record
            if (
                deadline is not None
                and time.monotonic() >= deadline
            ):
                return record
            time.sleep(poll_seconds)

    def resolve_reconciliation(
        self,
        *,
        job_id: str,
        decision: str,
        confirm_requeue: bool,
        actor: str = "cli",
    ) -> JobRecord:
        reconciler = JobReconciler(
            store=self.store,
            actor=actor,
        )
        return reconciler.resolve(
            job_id=job_id,
            decision=decision,
            confirm_requeue=confirm_requeue,
        )

    def tail_log(
        self,
        *,
        job_id: str,
        lines: int = 100,
        max_bytes: int = 256 * 1024,
    ) -> tuple[str | None, str]:
        record = self.store.get(job_id)
        run_root = require_managed_run_root(record.run_dir)

        execution_dir = run_root / "execution"
        candidates = []
        legacy = execution_dir / "execution.log"
        if legacy.is_file():
            candidates.append(legacy)
        candidates.extend(
            execution_dir.glob(
                "processes/*/combined.log"
            )
        )
        candidates = [
            path.resolve()
            for path in candidates
            if path.is_file()
            and run_root in path.resolve().parents
        ]
        if not candidates:
            return None, ""

        latest = max(
            candidates,
            key=lambda path: path.stat().st_mtime,
        )
        size = latest.stat().st_size
        with latest.open("rb") as file_obj:
            file_obj.seek(
                max(0, size - max_bytes)
            )
            data = file_obj.read(max_bytes)

        text = data.decode(
            "utf-8",
            errors="replace",
        )
        return str(latest), "\n".join(
            text.splitlines()[-max(1, lines):]
        )


def build_job_service() -> JobService:
    """CLI、API 和 Worker 共用 Store/Blob 配置。"""

    from app.storage.factory import (
        build_artifact_storage,
    )

    storage = build_artifact_storage()
    return JobService(
        build_job_store(),
        workspace_snapshotter=WorkspaceSnapshotter(
            blob_store=storage.selected_store
        ),
    )
