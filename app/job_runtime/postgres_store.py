from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.job_runtime.errors import (
    JobBackendUnavailable,
    JobConflictError,
    JobNotFoundError,
    LeaseLostError,
)
from app.job_runtime.schemas import (
    HeartbeatResult,
    JobClaim,
    JobEvent,
    JobInterrupt,
    JobRecord,
    JobRequest,
    JobResumeRequest,
)
from app.persistence.database import (
    build_engine,
    database_clock,
)
from app.persistence.tables import (
    job_commands,
    job_events,
    job_resumes,
    jobs,
    worker_sessions,
    workspace_assignments,
    workspace_manifests,
)
from app.workspace.repository import (
    binding_from_row,
    manifest_from_row,
)
from app.workspace.schemas import (
    JobRequirements,
    WorkerCapabilities,
    WorkerIdentity,
    WorkerSession,
    WorkspaceBinding,
    WorkspaceManifest,
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _json_hash(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _row_to_worker_session(row: RowMapping) -> WorkerSession:
    return WorkerSession(
        worker_id=str(row["worker_id"]),
        worker_session_id=str(row["worker_session_id"]),
        host_id=str(row["host_id"]),
        pool=str(row["worker_pool"]),
        workspace_root=str(row["workspace_root"]),
        capabilities=WorkerCapabilities.model_validate(
            row["capabilities_json"]
        ),
        status=str(row["status"]),
        registered_at=row["registered_at"].isoformat(),
        heartbeat_at=row["heartbeat_at"].isoformat(),
        lease_expires_at=row["lease_expires_at"].isoformat(),
    )


class PostgresJobStore:
    """PostgreSQL JobStore；schema 只能由 Alembic 创建。"""

    def __init__(self, engine: Engine | None = None):
        self.engine = engine or build_engine()

    def initialize(self) -> None:
        # 不在应用启动时 create_all 或执行 Alembic。
        self.ping()

    def ping(self) -> None:
        try:
            with self.engine.connect() as connection:
                connection.execute(sa.text("SELECT 1"))
        except DBAPIError as exc:
            raise JobBackendUnavailable(
                "PostgreSQL JobStore 不可用"
            ) from exc

    def close(self) -> None:
        # 全局 Engine 由 app.persistence.database 统一释放。
        return None

    def _append_event(
        self,
        connection: sa.Connection,
        *,
        job_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        connection.execute(
            job_events.insert().values(
                job_id=job_id,
                event_type=event_type,
                actor=actor[:100],
                payload_json=payload,
                created_at=now,
            )
        )

    def _row_to_record(
        self,
        row: RowMapping,
    ) -> JobRecord:
        return JobRecord(
            job_id=row["job_id"],
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            thread_id=row["thread_id"],
            run_id=row["run_id"],
            run_dir=row["run_dir"],
            request=JobRequest.model_validate(
                row["request_json"]
            ),
            requirements=JobRequirements.model_validate(
                row["requirements_json"]
            ),
            affinity_host_id=row["affinity_host_id"],
            workspace_manifest_id=str(
                row["workspace_manifest_id"]
            ),
            workspace_manifest_generation=int(
                row["workspace_manifest_generation"]
            ),
            workspace_assignment_epoch=int(
                row["workspace_assignment_epoch"]
            ),
            status=row["status"],
            version=row["version"],
            attempt_count=row["attempt_count"],
            max_attempts=row["max_attempts"],
            wait_generation=row["wait_generation"],
            worker_id=row["worker_id"],
            worker_session_id=row["worker_session_id"],
            worker_host_id=row["worker_host_id"],
            claim_token=row["claim_token"],
            workspace_assignment_token=row[
                "workspace_assignment_token"
            ],
            claimed_at=_iso(row["claimed_at"]),
            heartbeat_at=_iso(row["heartbeat_at"]),
            lease_expires_at=_iso(
                row["lease_expires_at"]
            ),
            available_at=_iso(row["available_at"]),
            interrupt_nodes=list(
                row["interrupt_nodes_json"] or []
            ),
            interrupts=[
                JobInterrupt.model_validate(item)
                for item in (
                    row["interrupts_json"] or []
                )
            ],
            pending_resume_id=row[
                "pending_resume_id"
            ],
            cancel_requested=bool(
                row["cancel_requested"]
            ),
            cancellation_reason=row[
                "cancellation_reason"
            ],
            result=row["result_json"],
            error=row["error_json"],
            reconciliation=row[
                "reconciliation_json"
            ],
            created_at=_iso(row["created_at"]),
            updated_at=_iso(row["updated_at"]),
        )

    def _row_to_resume(
        self,
        row: RowMapping,
    ) -> JobResumeRequest:
        return JobResumeRequest(
            resume_id=row["resume_id"],
            job_id=row["job_id"],
            wait_generation=row["wait_generation"],
            idempotency_key=row["idempotency_key"],
            expected_node=row["expected_node"],
            value=row["value_json"],
            value_hash=row["value_hash"],
            status=row["status"],
            created_at=_iso(row["created_at"]),
            consumed_at=_iso(row["consumed_at"]),
        )

    def _get_row(
        self,
        connection: sa.Connection,
        job_id: str,
        *,
        for_update: bool = False,
    ) -> RowMapping:
        statement = sa.select(jobs).where(
            jobs.c.job_id == job_id
        )
        if for_update:
            statement = statement.with_for_update()
        row = connection.execute(
            statement
        ).mappings().one_or_none()
        if row is None:
            raise JobNotFoundError(
                f"未找到 job_id={job_id}"
            )
        return row

    def _owned_row(
        self,
        connection: sa.Connection,
        *,
        job_id: str,
        claim_token: str,
    ) -> RowMapping:
        row = self._get_row(
            connection,
            job_id,
            for_update=True,
        )
        if (
            row["status"]
            not in {"running", "cancelling"}
            or row["claim_token"] != claim_token
        ):
            raise LeaseLostError(
                "Job claim 已失效"
            )
        return row

    def get(self, job_id: str) -> JobRecord:
        with self.engine.connect() as connection:
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def submit(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        thread_id: str,
        run_id: str,
        run_dir: str,
        request: JobRequest,
        requirements: JobRequirements,
        initial_manifest: WorkspaceManifest,
        max_attempts: int,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
        # PostgreSQL backend 忽略调用方 wall clock，统一使用 DB clock。
        del now
        request_payload = request.model_dump()
        requirements_payload = requirements.model_dump()
        request_hash = _json_hash(
            {
                "thread_id": thread_id,
                "request": request_payload,
                "requirements": requirements_payload,
            }
        )

        try:
            with self.engine.begin() as connection:
                current = database_clock(connection)

                # 先持久化初始 workspace manifest（generation 0）。
                # manifest_hash 唯一；同内容重放走 on_conflict_do_nothing。
                connection.execute(
                    insert(workspace_manifests)
                    .values(
                        manifest_id=initial_manifest.manifest_id,
                        manifest_hash=initial_manifest.manifest_hash,
                        job_id=initial_manifest.job_id,
                        run_id=initial_manifest.run_id,
                        generation=initial_manifest.generation,
                        parent_manifest_id=(
                            initial_manifest.parent_manifest_id
                        ),
                        portable=initial_manifest.portable,
                        source_host_id=(
                            initial_manifest.source_host_id
                        ),
                        source_worker_session_id=(
                            initial_manifest.source_worker_session_id
                        ),
                        manifest_json=(
                            initial_manifest.model_dump()
                        ),
                        created_at=datetime.fromisoformat(
                            initial_manifest.created_at
                        ),
                    )
                    .on_conflict_do_nothing(
                        index_elements=[
                            workspace_manifests.c.manifest_hash
                        ]
                    )
                )

                statement = (
                    insert(jobs)
                    .values(
                        job_id=job_id,
                        idempotency_key=idempotency_key,
                        request_hash=request_hash,
                        thread_id=thread_id,
                        run_id=run_id,
                        run_dir=run_dir,
                        request_json=request_payload,
                        requirements_json=requirements_payload,
                        required_worker_pool=(
                            requirements.worker_pool
                        ),
                        required_profile_id=(
                            requirements.execution_profile_id
                        ),
                        required_policy_hash=(
                            requirements.execution_policy_hash
                        ),
                        required_backend=(
                            requirements.execution_backend
                        ),
                        min_workspace_free_bytes=(
                            requirements.min_workspace_free_bytes
                        ),
                        min_gpu_count=(
                            requirements.min_gpu_count
                        ),
                        required_cuda_major=(
                            requirements.cuda_major
                        ),
                        required_labels_json=(
                            requirements.required_labels
                        ),
                        workspace_manifest_id=(
                            initial_manifest.manifest_id
                        ),
                        status="queued",
                        version=0,
                        attempt_count=0,
                        max_attempts=max_attempts,
                        wait_generation=0,
                        available_at=current,
                        created_at=current,
                        updated_at=current,
                    )
                    .on_conflict_do_nothing()
                    .returning(jobs.c.job_id)
                )
                inserted = connection.execute(
                    statement
                ).scalar_one_or_none()

                if inserted is None:
                    existing = connection.execute(
                        sa.select(jobs).where(
                            jobs.c.idempotency_key
                            == idempotency_key
                        )
                    ).mappings().one_or_none()
                    if existing is None:
                        raise JobConflictError(
                            "thread_id、run_id 或 run_dir 已存在"
                        )
                    if existing["request_hash"] != request_hash:
                        raise JobConflictError(
                            "相同 idempotency_key 对应不同请求"
                        )
                    return self._row_to_record(existing), False

                self._append_event(
                    connection,
                    job_id=job_id,
                    event_type="job_submitted",
                    actor="client",
                    payload={
                        "thread_id": thread_id,
                        "run_id": run_id,
                        "workspace_manifest_id": (
                            initial_manifest.manifest_id
                        ),
                    },
                    now=current,
                )
                row = self._get_row(connection, job_id)
                return self._row_to_record(row), True
        except IntegrityError as exc:
            raise JobConflictError(
                "Job 唯一身份冲突"
            ) from exc
        except DBAPIError as exc:
            raise JobBackendUnavailable(
                "PostgreSQL submit 失败"
            ) from exc

    def list_jobs(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[JobRecord]:
        statement = sa.select(jobs)
        if status is not None:
            statement = statement.where(
                jobs.c.status == status
            )
        statement = statement.order_by(
            jobs.c.created_at.desc()
        ).limit(max(1, min(limit, 500)))
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement
            ).mappings().all()
        return [self._row_to_record(row) for row in rows]

    def _event_from_row(
        self,
        row: RowMapping,
    ) -> JobEvent:
        return JobEvent(
            event_id=row["event_id"],
            job_id=row["job_id"],
            event_type=row["event_type"],
            actor=row["actor"],
            payload=row["payload_json"],
            created_at=_iso(row["created_at"]),
        )

    def list_events(
        self,
        job_id: str,
        *,
        limit: int = 200,
    ) -> list[JobEvent]:
        statement = (
            sa.select(job_events)
            .where(job_events.c.job_id == job_id)
            .order_by(job_events.c.event_id.desc())
            .limit(max(1, min(limit, 1000)))
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement
            ).mappings().all()
        rows.reverse()
        return [self._event_from_row(row) for row in rows]

    def list_events_after(
        self,
        job_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        statement = (
            sa.select(job_events)
            .where(
                job_events.c.job_id == job_id,
                job_events.c.event_id > after_event_id,
            )
            .order_by(job_events.c.event_id.asc())
            .limit(max(1, min(limit, 1000)))
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement
            ).mappings().all()
        return [self._event_from_row(row) for row in rows]

    def list_events_global_after(
        self,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        statement = (
            sa.select(job_events)
            .where(
                job_events.c.event_id > max(0, after_event_id)
            )
            .order_by(job_events.c.event_id.asc())
            .limit(max(1, min(limit, 1000)))
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement
            ).mappings().all()
        return [self._event_from_row(row) for row in rows]

    def claim_next(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
        now: float | None = None,
    ) -> JobClaim | None:
        del now
        claim_token = f"claim_{uuid4().hex}"
        assignment_token = f"wa_{uuid4().hex}"

        with self.engine.begin() as connection:
            current = database_clock(connection)

            session = connection.execute(
                sa.select(worker_sessions).where(
                    worker_sessions.c.worker_session_id
                    == worker.worker_session_id
                )
            ).mappings().one_or_none()
            if session is None:
                raise JobConflictError("Worker 尚未注册")
            if session["status"] != "active":
                return None
            if session["lease_expires_at"] <= current:
                raise JobConflictError("Worker session lease 已过期")

            caps = WorkerCapabilities.model_validate(
                session["capabilities_json"]
            )

            profile_pairs = [
                sa.and_(
                    jobs.c.required_profile_id == profile_id,
                    jobs.c.required_policy_hash == policy_hash,
                )
                for profile_id, policy_hash
                in caps.execution_policy_hashes.items()
            ]
            if not profile_pairs:
                return None

            # required_labels_json <@ worker labels。
            # 绑定参数显式 cast JSONB，避免驱动把 list 当普通 SQL array。
            labels_cover = jobs.c.required_labels_json.op("<@")(
                sa.cast(
                    sa.bindparam(
                        "worker_labels",
                        value=caps.labels,
                    ),
                    JSONB,
                )
            )

            filters = [
                jobs.c.status == "queued",
                jobs.c.cancel_requested.is_(False),
                jobs.c.available_at <= current,
                jobs.c.required_worker_pool == worker.pool,
                jobs.c.required_profile_id.in_(
                    caps.execution_profile_ids
                ),
                sa.or_(*profile_pairs),
                jobs.c.required_backend.in_(
                    caps.execution_backends
                ),
                jobs.c.min_workspace_free_bytes
                <= caps.workspace_free_bytes,
                jobs.c.min_gpu_count <= caps.gpu_count,
                sa.or_(
                    jobs.c.required_cuda_major.is_(None),
                    jobs.c.required_cuda_major == caps.cuda_major,
                ),
                labels_cover,
                sa.or_(
                    jobs.c.affinity_host_id.is_(None),
                    jobs.c.affinity_host_id == worker.host_id,
                ),
            ]

            candidate = connection.execute(
                sa.select(jobs.c.job_id)
                .where(*filters)
                .order_by(
                    jobs.c.available_at.asc(),
                    jobs.c.created_at.asc(),
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            ).scalar_one_or_none()
            if candidate is None:
                return None

            lease_expires = current + timedelta(
                seconds=lease_seconds
            )
            connection.execute(
                jobs.update()
                .where(jobs.c.job_id == candidate)
                .values(
                    status="running",
                    version=jobs.c.version + 1,
                    attempt_count=(
                        jobs.c.attempt_count + 1
                    ),
                    worker_id=worker.worker_id,
                    worker_session_id=worker.worker_session_id,
                    worker_host_id=worker.host_id,
                    claim_token=claim_token,
                    workspace_assignment_token=assignment_token,
                    workspace_assignment_epoch=(
                        jobs.c.workspace_assignment_epoch + 1
                    ),
                    claimed_at=current,
                    heartbeat_at=current,
                    lease_expires_at=lease_expires,
                    updated_at=current,
                )
            )
            row = self._get_row(connection, candidate)

            resume = None
            if row["pending_resume_id"] is not None:
                resume_row = connection.execute(
                    sa.select(job_resumes).where(
                        job_resumes.c.resume_id
                        == row["pending_resume_id"]
                    )
                ).mappings().one_or_none()
                if resume_row is None or resume_row["status"] != "pending":
                    raise JobConflictError(
                        "pending_resume_id 无有效 resume"
                    )
                resume = self._row_to_resume(resume_row)

            self._append_event(
                connection,
                job_id=candidate,
                event_type="job_claimed",
                actor=worker.worker_id,
                payload={
                    "attempt_count": row["attempt_count"],
                    "worker_session_id": worker.worker_session_id,
                    "host_id": worker.host_id,
                    "workspace_assignment_epoch": row[
                        "workspace_assignment_epoch"
                    ],
                    "job_version": row["version"],
                },
                now=current,
            )
            return JobClaim(
                job=self._row_to_record(row),
                claim_token=claim_token,
                worker=worker,
                resume_request=resume,
            )

    def heartbeat(
        self,
        *,
        job_id: str,
        claim_token: str,
        lease_seconds: float,
        now: float | None = None,
    ) -> HeartbeatResult:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            lease_expires = current + timedelta(
                seconds=lease_seconds
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    heartbeat_at=current,
                    lease_expires_at=lease_expires,
                    updated_at=current,
                )
            )
            return HeartbeatResult(
                lease_renewed=True,
                cancel_requested=bool(
                    row["cancel_requested"]
                ),
                cancellation_reason=row[
                    "cancellation_reason"
                ],
                lease_expires_at=lease_expires.isoformat(),
            )

    def _consume_pending_resume(
        self,
        connection: sa.Connection,
        *,
        pending_resume_id: str | None,
        now: datetime,
    ) -> None:
        if pending_resume_id is None:
            return
        connection.execute(
            job_resumes.update()
            .where(
                job_resumes.c.resume_id
                == pending_resume_id,
                job_resumes.c.status == "pending",
            )
            .values(
                status="consumed",
                consumed_at=now,
            )
        )

    def mark_waiting(
        self,
        *,
        job_id: str,
        claim_token: str,
        interrupts: list[JobInterrupt],
        result: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            self._consume_pending_resume(
                connection,
                pending_resume_id=row[
                    "pending_resume_id"
                ],
                now=current,
            )
            nodes = sorted(
                {item.node for item in interrupts}
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    status="waiting_for_input",
                    version=jobs.c.version + 1,
                    wait_generation=(
                        jobs.c.wait_generation + 1
                    ),
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    pending_resume_id=None,
                    interrupt_nodes_json=nodes,
                    interrupts_json=[
                        item.model_dump()
                        for item in interrupts
                    ],
                    result_json=result,
                    error_json=None,
                    updated_at=current,
                )
            )
            updated = self._get_row(connection, job_id)
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_waiting_for_input",
                actor=actor,
                payload={
                    "job_version": updated["version"],
                    "wait_generation": updated["wait_generation"],
                    "interrupt_nodes": nodes,
                },
                now=current,
            )
            return self._row_to_record(updated)

    def mark_succeeded(
        self,
        *,
        job_id: str,
        claim_token: str,
        result: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            self._consume_pending_resume(
                connection,
                pending_resume_id=row[
                    "pending_resume_id"
                ],
                now=current,
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    status="succeeded",
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    pending_resume_id=None,
                    interrupt_nodes_json=[],
                    interrupts_json=[],
                    result_json=result,
                    error_json=None,
                    updated_at=current,
                )
            )
            updated = self._get_row(connection, job_id)
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_succeeded",
                actor=actor,
                payload={
                    "job_version": updated["version"],
                    "final_status": result.get("final_status"),
                },
                now=current,
            )
            return self._row_to_record(updated)

    def mark_cancelled(
        self,
        *,
        job_id: str,
        claim_token: str,
        reason: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            self._consume_pending_resume(
                connection,
                pending_resume_id=row[
                    "pending_resume_id"
                ],
                now=current,
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    status="cancelled",
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    pending_resume_id=None,
                    cancel_requested=True,
                    cancellation_reason=reason[:500],
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_cancelled",
                actor=actor,
                payload={"reason": reason[:500]},
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def mark_failed(
        self,
        *,
        job_id: str,
        claim_token: str,
        error: dict[str, Any],
        actor: str,
        retryable: bool = False,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            can_retry = (
                retryable
                and not row["cancel_requested"]
                and row["attempt_count"]
                < row["max_attempts"]
            )
            if can_retry:
                delay = min(
                    60.0,
                    2.0
                    ** max(
                        row["attempt_count"] - 1,
                        0,
                    ),
                )
                target = "queued"
                available_at = current + timedelta(
                    seconds=delay
                )
                event_type = "job_retry_scheduled"
                pending_resume_id = row[
                    "pending_resume_id"
                ]
            else:
                target = (
                    "cancelled"
                    if row["cancel_requested"]
                    else "failed"
                )
                available_at = current
                event_type = f"job_{target}"
                pending_resume_id = None
                self._consume_pending_resume(
                    connection,
                    pending_resume_id=row[
                        "pending_resume_id"
                    ],
                    now=current,
                )

            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                )
                .values(
                    status=target,
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    pending_resume_id=pending_resume_id,
                    available_at=available_at,
                    error_json=error,
                    updated_at=current,
                )
            )
            updated = self._get_row(connection, job_id)
            self._append_event(
                connection,
                job_id=job_id,
                event_type=event_type,
                actor=actor,
                payload={
                    "job_version": updated["version"],
                    "retryable": retryable,
                    "error_type": error.get("type"),
                    "available_at": (
                        available_at.isoformat()
                    ),
                },
                now=current,
            )
            return self._row_to_record(updated)

    def queue_resume(
        self,
        *,
        job_id: str,
        expected_node: str,
        value: Any,
        idempotency_key: str,
        actor: str,
        expected_job_version: int | None = None,
        expected_wait_generation: int | None = None,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
        del now
        value_hash = _json_hash(value)
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._get_row(
                connection,
                job_id,
                for_update=True,
            )
            replay = connection.execute(
                sa.select(job_resumes).where(
                    job_resumes.c.idempotency_key
                    == idempotency_key
                )
            ).mappings().one_or_none()
            if replay is not None:
                if (
                    replay["job_id"] != job_id
                    or replay["expected_node"]
                    != expected_node
                    or replay["value_hash"] != value_hash
                ):
                    raise JobConflictError(
                        "resume idempotency key 冲突"
                    )
                return self._row_to_record(row), False

            if row["status"] != "waiting_for_input":
                raise JobConflictError(
                    "Job 当前不在 waiting_for_input"
                )
            if (
                expected_job_version is not None
                and row["version"]
                != expected_job_version
            ):
                raise JobConflictError("Job version 已变化")
            if (
                expected_wait_generation is not None
                and row["wait_generation"]
                != expected_wait_generation
            ):
                raise JobConflictError(
                    "wait_generation 已变化"
                )
            nodes = sorted(
                set(row["interrupt_nodes_json"] or [])
            )
            if nodes != [expected_node]:
                raise JobConflictError(
                    "resume node 与当前 interrupt 不匹配"
                )
            same_generation = connection.execute(
                sa.select(job_resumes.c.resume_id).where(
                    job_resumes.c.job_id == job_id,
                    job_resumes.c.wait_generation
                    == row["wait_generation"],
                )
            ).scalar_one_or_none()
            if same_generation is not None:
                raise JobConflictError(
                    "当前 generation 已存在 resume"
                )

            resume_id = f"resume_{uuid4().hex}"
            connection.execute(
                job_resumes.insert().values(
                    resume_id=resume_id,
                    job_id=job_id,
                    wait_generation=row[
                        "wait_generation"
                    ],
                    idempotency_key=idempotency_key,
                    expected_node=expected_node,
                    value_json=value,
                    value_hash=value_hash,
                    status="pending",
                    created_at=current,
                )
            )
            connection.execute(
                jobs.update()
                .where(jobs.c.job_id == job_id)
                .values(
                    status="queued",
                    version=jobs.c.version + 1,
                    pending_resume_id=resume_id,
                    interrupt_nodes_json=[],
                    interrupts_json=[],
                    available_at=current,
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_resume_queued",
                actor=actor,
                payload={
                    "expected_node": expected_node,
                    "wait_generation": row[
                        "wait_generation"
                    ],
                },
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            ), True

    def request_cancel(
        self,
        *,
        job_id: str,
        reason: str,
        actor: str,
        idempotency_key: str | None = None,
        expected_job_version: int | None = None,
        now: float | None = None,
    ) -> JobRecord:
        del now
        command_key = idempotency_key or (
            f"cancel:{job_id}:{uuid4().hex}"
        )
        request_hash = _json_hash(
            {"job_id": job_id, "reason": reason}
        )
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._get_row(
                connection,
                job_id,
                for_update=True,
            )
            existing = connection.execute(
                sa.select(job_commands).where(
                    job_commands.c.idempotency_key
                    == command_key
                )
            ).mappings().one_or_none()
            if existing is not None:
                if (
                    existing["job_id"] != job_id
                    or existing["request_hash"]
                    != request_hash
                ):
                    raise JobConflictError(
                        "cancel idempotency key 冲突"
                    )
                return self._row_to_record(row)

            if (
                expected_job_version is not None
                and row["version"]
                != expected_job_version
            ):
                raise JobConflictError("Job version 已变化")
            connection.execute(
                job_commands.insert().values(
                    command_id=f"command_{uuid4().hex}",
                    job_id=job_id,
                    command_type="cancel",
                    idempotency_key=command_key,
                    request_hash=request_hash,
                    created_at=current,
                )
            )
            if row["status"] in {
                "succeeded",
                "failed",
                "cancelled",
            }:
                return self._row_to_record(row)

            if row["status"] in {
                "queued",
                "waiting_for_input",
                "reconciliation_required",
            }:
                target = "cancelled"
                owner_values = {
                    "worker_id": None,
                    "claim_token": None,
                    "claimed_at": None,
                    "heartbeat_at": None,
                    "lease_expires_at": None,
                    "pending_resume_id": None,
                }
                self._consume_pending_resume(
                    connection,
                    pending_resume_id=row[
                        "pending_resume_id"
                    ],
                    now=current,
                )
            else:
                target = "cancelling"
                owner_values = {}

            connection.execute(
                jobs.update()
                .where(jobs.c.job_id == job_id)
                .values(
                    status=target,
                    version=jobs.c.version + 1,
                    cancel_requested=True,
                    cancellation_reason=reason[:500],
                    updated_at=current,
                    **owner_values,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_cancelled"
                    if target == "cancelled"
                    else "job_cancellation_requested"
                ),
                actor=actor,
                payload={"reason": reason[:500]},
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def list_expired_running(
        self,
        *,
        now: float | None = None,
        limit: int = 100,
    ) -> list[JobRecord]:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            rows = connection.execute(
                sa.select(jobs)
                .where(
                    jobs.c.status.in_(
                        ["running", "cancelling"]
                    ),
                    jobs.c.lease_expires_at <= current,
                )
                .order_by(jobs.c.lease_expires_at)
                .limit(max(1, min(limit, 500)))
            ).mappings().all()
        return [self._row_to_record(row) for row in rows]

    def _lock_expired(
        self,
        connection: sa.Connection,
        *,
        job_id: str,
        expired_claim_token: str,
        current: datetime,
    ) -> RowMapping:
        row = self._get_row(
            connection,
            job_id,
            for_update=True,
        )
        if (
            row["status"]
            not in {"running", "cancelling"}
            or row["claim_token"]
            != expired_claim_token
            or row["lease_expires_at"] > current
        ):
            raise LeaseLostError(
                "stale Job 已被其他 Worker 处理"
            )
        return row

    def requeue_expired(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._lock_expired(
                connection,
                job_id=job_id,
                expired_claim_token=expired_claim_token,
                current=current,
            )
            if row["cancel_requested"]:
                target = "cancelled"
            elif row["attempt_count"] >= row["max_attempts"]:
                target = "failed"
            else:
                target = "queued"
            error = (
                {
                    "type": "LeaseAttemptsExhausted",
                    "message": detail[:1000],
                }
                if target == "failed"
                else None
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token
                    == expired_claim_token,
                )
                .values(
                    status=target,
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    available_at=current,
                    error_json=error,
                    updated_at=current,
                )
            )
            updated = self._get_row(connection, job_id)
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_lease_requeued"
                    if target == "queued"
                    else f"job_{target}"
                ),
                actor=actor,
                payload={
                    "job_version": updated["version"],
                    "attempt_count": updated["attempt_count"],
                    "detail_code": "lease_expired_requeued",
                },
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def require_reconciliation(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        reconciliation: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        with self.engine.begin() as connection:
            current = database_clock(connection)
            self._lock_expired(
                connection,
                job_id=job_id,
                expired_claim_token=expired_claim_token,
                current=current,
            )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token
                    == expired_claim_token,
                )
                .values(
                    status="reconciliation_required",
                    version=jobs.c.version + 1,
                    worker_id=None,
                    claim_token=None,
                    claimed_at=None,
                    heartbeat_at=None,
                    lease_expires_at=None,
                    reconciliation_json=reconciliation,
                    updated_at=current,
                )
            )
            updated = self._get_row(connection, job_id)
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_reconciliation_required"
                ),
                actor=actor,
                payload={
                    "job_version": updated["version"],
                    "detail_code": (
                        "lease_expired_reconciliation_required"
                    ),
                    "disposition": reconciliation.get(
                        "disposition"
                    ),
                },
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def resolve_reconciliation(
        self,
        *,
        job_id: str,
        decision: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        del now
        if decision not in {
            "requeue",
            "failed",
            "cancelled",
        }:
            raise ValueError(
                "无效 reconciliation decision"
            )
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._get_row(
                connection,
                job_id,
                for_update=True,
            )
            if row["status"] != "reconciliation_required":
                raise JobConflictError(
                    "Job 当前不需要 reconciliation"
                )
            target = (
                "queued"
                if decision == "requeue"
                else decision
            )
            error = (
                {
                    "type": "ManualReconciliation",
                    "message": detail[:1000],
                }
                if target == "failed"
                else row["error_json"]
            )
            connection.execute(
                jobs.update()
                .where(jobs.c.job_id == job_id)
                .values(
                    status=target,
                    version=jobs.c.version + 1,
                    available_at=current,
                    reconciliation_json=None,
                    error_json=error,
                    updated_at=current,
                )
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_reconciliation_resolved"
                ),
                actor=actor,
                payload={
                    "decision": decision,
                    "detail": detail[:1000],
                },
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    # ------------------------------------------------------------------
    # Phase 26: Worker session lifecycle
    # ------------------------------------------------------------------

    def register_worker(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
    ) -> WorkerSession:
        with self.engine.begin() as connection:
            current = database_clock(connection)
            lease_expires = current + timedelta(seconds=lease_seconds)
            caps = worker.capabilities

            # session_id 每次进程启动唯一；重复注册同一 session 必须内容一致。
            existing = connection.execute(
                sa.select(worker_sessions).where(
                    worker_sessions.c.worker_session_id
                    == worker.worker_session_id
                )
            ).mappings().one_or_none()

            values = {
                "worker_session_id": worker.worker_session_id,
                "worker_id": worker.worker_id,
                "host_id": worker.host_id,
                "worker_pool": worker.pool,
                "workspace_root": worker.workspace_root,
                "capabilities_json": caps.model_dump(),
                "profile_ids_json": caps.execution_profile_ids,
                "profile_hashes_json": caps.execution_policy_hashes,
                "backends_json": caps.execution_backends,
                "labels_json": caps.labels,
                "workspace_free_bytes": caps.workspace_free_bytes,
                "gpu_count": caps.gpu_count,
                "cuda_major": caps.cuda_major,
                "status": "active",
                "heartbeat_at": current,
                "lease_expires_at": lease_expires,
            }

            if existing is None:
                connection.execute(
                    worker_sessions.insert().values(
                        **values,
                        registered_at=current,
                    )
                )
            else:
                immutable_identity = (
                    existing["worker_id"],
                    existing["host_id"],
                    existing["workspace_root"],
                )
                expected_identity = (
                    worker.worker_id,
                    worker.host_id,
                    worker.workspace_root,
                )
                if immutable_identity != expected_identity:
                    raise JobConflictError(
                        "worker_session_id 被不同身份复用"
                    )
                connection.execute(
                    worker_sessions.update()
                    .where(
                        worker_sessions.c.worker_session_id
                        == worker.worker_session_id
                    )
                    .values(**values)
                )

            row = connection.execute(
                sa.select(worker_sessions).where(
                    worker_sessions.c.worker_session_id
                    == worker.worker_session_id
                )
            ).mappings().one()
            return _row_to_worker_session(row)

    def heartbeat_worker(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
    ) -> WorkerSession:
        # 重新加载 capability 可以更新磁盘余量；session 身份不能改变。
        return self.register_worker(
            worker=worker,
            lease_seconds=lease_seconds,
        )

    def drain_worker(
        self,
        *,
        worker_session_id: str,
    ) -> WorkerSession:
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = connection.execute(
                worker_sessions.update()
                .where(
                    worker_sessions.c.worker_session_id
                    == worker_session_id
                )
                .values(status="draining", heartbeat_at=current)
                .returning(worker_sessions)
            ).mappings().one_or_none()
            if row is None:
                raise JobNotFoundError("Worker session 不存在")
            return _row_to_worker_session(row)

    def list_workers(
        self,
        *,
        include_expired: bool = False,
        limit: int = 100,
    ) -> list[WorkerSession]:
        statement = sa.select(worker_sessions)
        if not include_expired:
            statement = statement.where(
                worker_sessions.c.status != "offline"
            )
        statement = statement.order_by(
            worker_sessions.c.registered_at.desc()
        ).limit(max(1, min(limit, 500)))
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement
            ).mappings().all()
        return [_row_to_worker_session(row) for row in rows]

    # ------------------------------------------------------------------
    # Phase 26: Workspace manifest / assignment persistence
    # ------------------------------------------------------------------

    def get_workspace_manifest(
        self,
        manifest_id: str,
    ) -> WorkspaceManifest:
        with self.engine.connect() as connection:
            row = connection.execute(
                sa.select(workspace_manifests).where(
                    workspace_manifests.c.manifest_id
                    == manifest_id
                )
            ).mappings().one_or_none()
            if row is None:
                raise JobNotFoundError(
                    f"未找到 workspace manifest：{manifest_id}"
                )
            return manifest_from_row(row)

    def begin_workspace_assignment(
        self,
        *,
        job_id: str,
        claim_token: str,
        worker: WorkerIdentity,
        manifest: WorkspaceManifest,
        assignment_token: str,
        workspace_root: str,
        run_dir: str,
        repo_path: str,
        paper_path: str,
        log_path: str | None,
    ) -> WorkspaceBinding:
        from app.workspace.repository import validate_manifest_hash

        validate_manifest_hash(manifest)
        with self.engine.begin() as connection:
            current = database_clock(connection)
            job = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            if job["workspace_assignment_token"] != assignment_token:
                raise LeaseLostError("workspace assignment token 已失效")
            if job["worker_session_id"] != worker.worker_session_id:
                raise LeaseLostError("worker session 已失效")
            if job["workspace_manifest_id"] != manifest.manifest_id:
                raise JobConflictError("claim 使用了过期 workspace manifest")

            epoch = int(job["workspace_assignment_epoch"])
            existing = connection.execute(
                sa.select(workspace_assignments)
                .where(
                    workspace_assignments.c.job_id == job_id,
                    workspace_assignments.c.assignment_epoch == epoch,
                )
                .with_for_update()
            ).mappings().one_or_none()
            if existing is not None:
                # DB commit 已成功但 Worker 没收到响应时，prepare 会重试。
                # 只有完全相同的 assignment 才能幂等返回，不能吞掉真实冲突。
                expected = {
                    "assignment_token": assignment_token,
                    "manifest_id": manifest.manifest_id,
                    "manifest_hash": manifest.manifest_hash,
                    "worker_session_id": worker.worker_session_id,
                    "host_id": worker.host_id,
                    "workspace_root": workspace_root,
                    "run_dir": run_dir,
                    "repo_path": repo_path,
                    "paper_path": paper_path,
                    "log_path": log_path,
                }
                mismatches = [
                    key
                    for key, value in expected.items()
                    if existing[key] != value
                ]
                if mismatches:
                    raise JobConflictError(
                        "同一 assignment epoch 已被不同内容占用："
                        + ", ".join(mismatches)
                    )
                return binding_from_row(existing)

            assignment_id = f"was_{uuid4().hex}"
            connection.execute(
                workspace_assignments.insert().values(
                    assignment_id=assignment_id,
                    job_id=job_id,
                    run_id=job["run_id"],
                    assignment_epoch=epoch,
                    assignment_token=assignment_token,
                    manifest_id=manifest.manifest_id,
                    manifest_hash=manifest.manifest_hash,
                    manifest_generation=manifest.generation,
                    worker_session_id=worker.worker_session_id,
                    host_id=worker.host_id,
                    workspace_root=workspace_root,
                    run_dir=run_dir,
                    repo_path=repo_path,
                    paper_path=paper_path,
                    log_path=log_path,
                    status="materializing",
                    created_at=current,
                    updated_at=current,
                )
            )
            row = connection.execute(
                sa.select(workspace_assignments).where(
                    workspace_assignments.c.assignment_id == assignment_id
                )
            ).mappings().one()
            self._append_event(
                connection,
                job_id=job_id,
                event_type="workspace_materializing",
                actor=worker.worker_id,
                payload={
                    "assignment_id": assignment_id,
                    "assignment_epoch": row["assignment_epoch"],
                    "manifest_id": manifest.manifest_id,
                    "host_id": worker.host_id,
                },
                now=current,
            )
            return binding_from_row(row)

    def mark_workspace_ready(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
    ) -> WorkspaceBinding:
        with self.engine.begin() as connection:
            current = database_clock(connection)
            job = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            if job["workspace_assignment_token"] != assignment_token:
                raise LeaseLostError("workspace assignment token 已失效")

            row = connection.execute(
                sa.select(workspace_assignments)
                .where(
                    workspace_assignments.c.job_id == job_id,
                    workspace_assignments.c.assignment_token
                    == assignment_token,
                )
                .with_for_update()
            ).mappings().one_or_none()
            if row is None:
                raise JobConflictError("workspace assignment 不存在")
            if row["status"] == "ready":
                return binding_from_row(row)
            if row["status"] != "materializing":
                raise JobConflictError(
                    f"不能从 {row['status']} 转成 ready"
                )

            result = connection.execute(
                workspace_assignments.update()
                .where(
                    workspace_assignments.c.assignment_id
                    == row["assignment_id"],
                    workspace_assignments.c.status == "materializing",
                )
                .values(status="ready", updated_at=current)
            )
            if result.rowcount != 1:
                raise LeaseLostError("workspace ready fencing 失败")

            # 当前 epoch 已 ready 后，旧目录才允许进入 GC 候选。
            connection.execute(
                workspace_assignments.update()
                .where(
                    workspace_assignments.c.job_id == job_id,
                    workspace_assignments.c.assignment_epoch
                    < row["assignment_epoch"],
                    workspace_assignments.c.status == "ready",
                )
                .values(status="released", updated_at=current)
            )
            ready = connection.execute(
                sa.select(workspace_assignments).where(
                    workspace_assignments.c.assignment_id
                    == row["assignment_id"]
                )
            ).mappings().one()
            self._append_event(
                connection,
                job_id=job_id,
                event_type="workspace_ready",
                actor=str(job["worker_id"]),
                payload={
                    "assignment_id": row["assignment_id"],
                    "assignment_epoch": row["assignment_epoch"],
                    "manifest_id": row["manifest_id"],
                },
                now=current,
            )
            return binding_from_row(ready)

    def fail_workspace_assignment(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
        reason: str,
    ) -> WorkspaceBinding:
        with self.engine.begin() as connection:
            current = database_clock(connection)
            job = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            if job["workspace_assignment_token"] != assignment_token:
                raise LeaseLostError("workspace assignment token 已失效")
            row = connection.execute(
                sa.select(workspace_assignments)
                .where(
                    workspace_assignments.c.job_id == job_id,
                    workspace_assignments.c.assignment_token
                    == assignment_token,
                )
                .with_for_update()
            ).mappings().one_or_none()
            if row is None:
                raise JobConflictError("workspace assignment 不存在")
            if row["status"] != "materializing":
                # ready 可能表示上一请求已提交、只是响应丢失；不能反向覆盖。
                return binding_from_row(row)

            connection.execute(
                workspace_assignments.update()
                .where(
                    workspace_assignments.c.assignment_id
                    == row["assignment_id"],
                    workspace_assignments.c.status == "materializing",
                )
                .values(
                    status="failed",
                    error_code=reason[:120],
                    updated_at=current,
                )
            )
            failed = connection.execute(
                sa.select(workspace_assignments).where(
                    workspace_assignments.c.assignment_id
                    == row["assignment_id"]
                )
            ).mappings().one()
            self._append_event(
                connection,
                job_id=job_id,
                event_type="workspace_materialization_failed",
                actor=str(job["worker_id"]),
                payload={
                    "assignment_id": row["assignment_id"],
                    "error_code": reason[:120],
                },
                now=current,
            )
            return binding_from_row(failed)

    def current_workspace_binding(
        self,
        job_id: str,
    ) -> WorkspaceBinding | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                sa.select(workspace_assignments)
                .where(
                    workspace_assignments.c.job_id == job_id
                )
                .order_by(
                    workspace_assignments.c.assignment_epoch.desc()
                )
                .limit(1)
            ).mappings().one_or_none()
            if row is None:
                return None
            return binding_from_row(row)

    def seal_workspace_manifest(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
        manifest: WorkspaceManifest,
        affinity_host_id: str | None,
        actor: str,
    ) -> JobRecord:
        from app.workspace.repository import validate_manifest_hash

        validate_manifest_hash(manifest)
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = self._owned_row(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            if row["workspace_assignment_token"] != assignment_token:
                raise LeaseLostError("workspace assignment 已失效")
            if manifest.job_id != job_id or manifest.run_id != row["run_id"]:
                raise JobConflictError("manifest Job identity 不一致")
            if row["workspace_manifest_id"] == manifest.manifest_id:
                # DB commit 成功但客户端未收到响应时的同内容重放。
                existing = connection.execute(
                    sa.select(workspace_manifests).where(
                        workspace_manifests.c.manifest_id
                        == manifest.manifest_id
                    )
                ).mappings().one()
                if existing["manifest_hash"] != manifest.manifest_hash:
                    raise JobConflictError("manifest_id 内容冲突")
                return self._row_to_record(row)
            if manifest.parent_manifest_id != row["workspace_manifest_id"]:
                raise JobConflictError("manifest parent 不是当前 head")
            if manifest.generation != row["workspace_manifest_generation"] + 1:
                raise JobConflictError("manifest generation 不连续")
            if manifest.portable and affinity_host_id is not None:
                raise JobConflictError("portable manifest 不应设置 affinity")
            if not manifest.portable and affinity_host_id != row["worker_host_id"]:
                raise JobConflictError(
                    "non-portable manifest 必须绑定当前 worker host"
                )

            insert_manifest = insert(
                workspace_manifests
            ).values(
                manifest_id=manifest.manifest_id,
                manifest_hash=manifest.manifest_hash,
                job_id=manifest.job_id,
                run_id=manifest.run_id,
                generation=manifest.generation,
                parent_manifest_id=manifest.parent_manifest_id,
                portable=manifest.portable,
                source_host_id=manifest.source_host_id,
                source_worker_session_id=(
                    manifest.source_worker_session_id
                ),
                manifest_json=manifest.model_dump(),
                created_at=datetime.fromisoformat(
                    manifest.created_at
                ),
            ).on_conflict_do_nothing(
                index_elements=[workspace_manifests.c.manifest_hash]
            )
            connection.execute(insert_manifest)
            stored = connection.execute(
                sa.select(workspace_manifests).where(
                    workspace_manifests.c.manifest_hash
                    == manifest.manifest_hash
                )
            ).mappings().one()
            if (
                stored["manifest_id"] != manifest.manifest_id
                or stored["job_id"] != job_id
                or stored["generation"] != manifest.generation
            ):
                raise JobConflictError(
                    "manifest hash 命中了不同 identity"
                )
            connection.execute(
                jobs.update()
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.claim_token == claim_token,
                    jobs.c.workspace_assignment_token == assignment_token,
                )
                .values(
                    workspace_manifest_id=manifest.manifest_id,
                    workspace_manifest_generation=manifest.generation,
                    affinity_host_id=affinity_host_id,
                    updated_at=current,
                )
            )
            event_type = (
                "workspace_sealed"
                if manifest.portable
                else "workspace_portability_blocked"
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=event_type,
                actor=actor,
                payload={
                    "manifest_id": manifest.manifest_id,
                    "generation": manifest.generation,
                    "portable": manifest.portable,
                    "blocked_reasons": manifest.blocked_reasons,
                    "affinity_host_id": affinity_host_id,
                },
                now=current,
            )
            return self._row_to_record(
                self._get_row(connection, job_id)
            )

    def list_workspace_gc_candidates(
        self,
        *,
        host_id: str,
        older_than: str,
        limit: int = 100,
    ) -> list[WorkspaceBinding]:
        statement = (
            sa.select(workspace_assignments)
            .where(
                workspace_assignments.c.host_id == host_id,
                workspace_assignments.c.status.in_(
                    ["released", "failed"]
                ),
                workspace_assignments.c.updated_at
                <= datetime.fromisoformat(older_than),
            )
            .order_by(
                workspace_assignments.c.updated_at.asc()
            )
            .limit(max(1, min(limit, 500)))
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement
            ).mappings().all()
        return [binding_from_row(row) for row in rows]

    def mark_workspace_garbage_collected(
        self,
        *,
        assignment_id: str,
        assignment_token: str,
        host_id: str,
    ) -> WorkspaceBinding:
        with self.engine.begin() as connection:
            current = database_clock(connection)
            row = connection.execute(
                workspace_assignments.update()
                .where(
                    workspace_assignments.c.assignment_id
                    == assignment_id,
                    workspace_assignments.c.assignment_token
                    == assignment_token,
                    workspace_assignments.c.host_id == host_id,
                    workspace_assignments.c.status.in_(
                        ["released", "failed"]
                    ),
                )
                .values(
                    status="garbage_collected",
                    updated_at=current,
                )
                .returning(workspace_assignments)
            ).mappings().one_or_none()
            if row is None:
                raise JobConflictError(
                    "workspace assignment 不存在或状态不允许 GC"
                )
            return binding_from_row(row)
