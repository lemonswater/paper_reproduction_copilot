from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.job_runtime.errors import (
    JobConflictError,
    JobNotFoundError,
    JobStoreError,
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
from app.observability.schemas import TraceCarrier
from app.workspace.capabilities import (
    explain_compatibility,
)
from app.workspace.repository import (
    validate_manifest_hash,
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


def _dump_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def _load_json(
    value: str | None,
    default: Any,
) -> Any:
    if value is None:
        return default
    return json.loads(value)


def _iso(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None

    from datetime import datetime, timezone

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).isoformat()


class SqliteJobStore:
    """
    每个方法创建自己的 SQLite connection。

    这样 heartbeat thread、worker 主线程和 CLI 可以安全并发使用同一个
    store 对象，不共享 sqlite3.Connection。
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(
            "PRAGMA journal_mode=WAL"
        )
        connection.execute(
            "PRAGMA synchronous=NORMAL"
        )
        connection.execute(
            "PRAGMA busy_timeout=30000"
        )
        connection.execute(
            "PRAGMA foreign_keys=ON"
        )
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,

                    thread_id TEXT NOT NULL UNIQUE,
                    run_id TEXT NOT NULL UNIQUE,
                    run_dir TEXT NOT NULL UNIQUE,
                    request_json TEXT NOT NULL,

                    requirements_json TEXT NOT NULL,
                    required_worker_pool TEXT NOT NULL,
                    required_profile_id TEXT NOT NULL,
                    required_policy_hash TEXT NOT NULL,
                    required_backend TEXT NOT NULL,
                    min_workspace_free_bytes INTEGER NOT NULL DEFAULT 0,
                    min_gpu_count INTEGER NOT NULL DEFAULT 0,
                    required_cuda_major INTEGER,
                    required_labels_json TEXT NOT NULL DEFAULT '[]',
                    affinity_host_id TEXT,
                    workspace_manifest_id TEXT NOT NULL,
                    workspace_manifest_generation INTEGER NOT NULL DEFAULT 0,
                    workspace_assignment_epoch INTEGER NOT NULL DEFAULT 0,

                    status TEXT NOT NULL CHECK (
                        status IN (
                            'queued',
                            'running',
                            'waiting_for_input',
                            'cancelling',
                            'succeeded',
                            'failed',
                            'cancelled',
                            'reconciliation_required'
                        )
                    ),
                    version INTEGER NOT NULL DEFAULT 0,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL,
                    wait_generation INTEGER NOT NULL DEFAULT 0,

                    worker_id TEXT,
                    worker_session_id TEXT,
                    worker_host_id TEXT,
                    claim_token TEXT,
                    workspace_assignment_token TEXT,
                    claimed_at REAL,
                    heartbeat_at REAL,
                    lease_expires_at REAL,
                    available_at REAL NOT NULL,

                    interrupt_nodes_json TEXT NOT NULL DEFAULT '[]',
                    interrupts_json TEXT NOT NULL DEFAULT '[]',
                    pending_resume_id TEXT,

                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    cancellation_reason TEXT,

                    result_json TEXT,
                    error_json TEXT,
                    reconciliation_json TEXT,
                    submit_trace_json TEXT,

                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_claim
                ON jobs (
                    status,
                    cancel_requested,
                    available_at,
                    created_at
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_lease
                ON jobs (
                    status,
                    lease_expires_at
                );

                CREATE TABLE IF NOT EXISTS job_resumes (
                    resume_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    wait_generation INTEGER NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    expected_node TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    value_hash TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('pending', 'consumed')
                    ),
                    created_at REAL NOT NULL,
                    consumed_at REAL,
                    FOREIGN KEY(job_id)
                        REFERENCES jobs(job_id)
                        ON DELETE CASCADE,
                    UNIQUE(job_id, wait_generation)
                );

                CREATE TABLE IF NOT EXISTS job_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(job_id)
                        REFERENCES jobs(job_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS job_commands (
                    command_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    command_type TEXT NOT NULL CHECK (
                        command_type IN ('cancel')
                    ),
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(job_id)
                        REFERENCES jobs(job_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_job_commands_job
                ON job_commands(job_id, command_id);

                CREATE INDEX IF NOT EXISTS idx_job_events_job
                ON job_events(job_id, event_id);

                CREATE TABLE IF NOT EXISTS worker_sessions (
                    worker_session_id TEXT PRIMARY KEY,
                    worker_id TEXT NOT NULL,
                    host_id TEXT NOT NULL,
                    worker_pool TEXT NOT NULL,
                    workspace_root TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('active', 'draining', 'offline')
                    ),
                    registered_at REAL NOT NULL,
                    heartbeat_at REAL NOT NULL,
                    lease_expires_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_worker_sessions_schedulable
                ON worker_sessions (
                    status,
                    worker_pool,
                    lease_expires_at
                );

                CREATE TABLE IF NOT EXISTS workspace_manifests (
                    manifest_id TEXT PRIMARY KEY,
                    manifest_hash TEXT NOT NULL UNIQUE,
                    job_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    generation INTEGER NOT NULL CHECK (generation >= 0),
                    parent_manifest_id TEXT,
                    portable INTEGER NOT NULL,
                    source_host_id TEXT NOT NULL,
                    source_worker_session_id TEXT,
                    manifest_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    UNIQUE(job_id, generation)
                );

                CREATE INDEX IF NOT EXISTS idx_workspace_manifests_job_gen
                ON workspace_manifests(job_id, generation);

                CREATE TABLE IF NOT EXISTS workspace_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    assignment_epoch INTEGER NOT NULL,
                    assignment_token TEXT NOT NULL,
                    manifest_id TEXT NOT NULL,
                    manifest_hash TEXT NOT NULL,
                    manifest_generation INTEGER NOT NULL,
                    worker_session_id TEXT NOT NULL,
                    host_id TEXT NOT NULL,
                    workspace_root TEXT NOT NULL,
                    run_dir TEXT NOT NULL,
                    repo_path TEXT NOT NULL,
                    paper_path TEXT NOT NULL,
                    log_path TEXT,
                    status TEXT NOT NULL CHECK (
                        status IN (
                            'materializing',
                            'ready',
                            'released',
                            'failed',
                            'garbage_collected'
                        )
                    ),
                    error_code TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(job_id, assignment_epoch)
                );

                CREATE INDEX IF NOT EXISTS idx_workspace_assignments_job
                ON workspace_assignments(job_id, assignment_epoch);
                """
            )
            self._migrate_columns(connection)

    def _migrate_columns(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        """为 Phase 26 之前创建的 jobs 表补列；新表已含则跳过。"""

        existing = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(jobs)"
            ).fetchall()
        }
        additions = {
            "requirements_json": "TEXT NOT NULL DEFAULT '{}'",
            "required_worker_pool": "TEXT NOT NULL DEFAULT 'default'",
            "required_profile_id": "TEXT NOT NULL DEFAULT ''",
            "required_policy_hash": "TEXT NOT NULL DEFAULT ''",
            "required_backend": "TEXT NOT NULL DEFAULT 'local'",
            "min_workspace_free_bytes": "INTEGER NOT NULL DEFAULT 0",
            "min_gpu_count": "INTEGER NOT NULL DEFAULT 0",
            "required_cuda_major": "INTEGER",
            "required_labels_json": "TEXT NOT NULL DEFAULT '[]'",
            "affinity_host_id": "TEXT",
            "workspace_manifest_id": "TEXT NOT NULL DEFAULT ''",
            "workspace_manifest_generation": "INTEGER NOT NULL DEFAULT 0",
            "workspace_assignment_epoch": "INTEGER NOT NULL DEFAULT 0",
            "worker_session_id": "TEXT",
            "worker_host_id": "TEXT",
            "workspace_assignment_token": "TEXT",
        }
        for column, definition in additions.items():
            if column not in existing:
                connection.execute(
                    f"ALTER TABLE jobs ADD COLUMN "
                    f"{column} {definition}"
                )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    def close(self) -> None:
        # SQLite 实现每次方法调用创建 connection，没有常驻 pool。
        return None

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
        now: float,
    ) -> None:
        connection.execute(
            """
            INSERT INTO job_events (
                job_id,
                event_type,
                actor,
                payload_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                job_id,
                event_type,
                actor[:100],
                _dump_json(payload),
                now,
            ),
        )

    def _row_to_record(
        self,
        row: sqlite3.Row,
    ) -> JobRecord:
        return JobRecord(
            job_id=row["job_id"],
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            thread_id=row["thread_id"],
            run_id=row["run_id"],
            run_dir=row["run_dir"],
            request=JobRequest.model_validate(
                _load_json(
                    row["request_json"],
                    {},
                )
            ),
            requirements=JobRequirements.model_validate(
                _load_json(
                    row["requirements_json"],
                    {},
                )
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
            available_at=_iso(
                row["available_at"]
            ),
            interrupt_nodes=_load_json(
                row["interrupt_nodes_json"],
                [],
            ),
            interrupts=[
                JobInterrupt.model_validate(item)
                for item in _load_json(
                    row["interrupts_json"],
                    [],
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
            result=_load_json(
                row["result_json"],
                None,
            ),
            error=_load_json(
                row["error_json"],
                None,
            ),
            reconciliation=_load_json(
                row["reconciliation_json"],
                None,
            ),
            submit_trace=(
                TraceCarrier.model_validate(
                    _load_json(
                        row["submit_trace_json"],
                        {},
                    )
                )
                if row["submit_trace_json"]
                else None
            ),
            created_at=_iso(row["created_at"]),
            updated_at=_iso(row["updated_at"]),
        )

    def _row_to_resume(
        self,
        row: sqlite3.Row,
    ) -> JobResumeRequest:
        return JobResumeRequest(
            resume_id=row["resume_id"],
            job_id=row["job_id"],
            wait_generation=row[
                "wait_generation"
            ],
            idempotency_key=row[
                "idempotency_key"
            ],
            expected_node=row["expected_node"],
            value=_load_json(
                row["value_json"],
                None,
            ),
            value_hash=row["value_hash"],
            status=row["status"],
            created_at=_iso(row["created_at"]),
            consumed_at=_iso(
                row["consumed_at"]
            ),
        )

    def _row_to_worker_session(
        self,
        row: sqlite3.Row,
    ) -> WorkerSession:
        return WorkerSession(
            worker_id=str(row["worker_id"]),
            worker_session_id=str(row["worker_session_id"]),
            host_id=str(row["host_id"]),
            pool=str(row["worker_pool"]),
            workspace_root=str(row["workspace_root"]),
            capabilities=WorkerCapabilities.model_validate(
                _load_json(row["capabilities_json"], {})
            ),
            status=str(row["status"]),
            registered_at=_iso(row["registered_at"]),
            heartbeat_at=_iso(row["heartbeat_at"]),
            lease_expires_at=_iso(
                row["lease_expires_at"]
            ),
        )

    def _upsert_manifest(
        self,
        connection: sqlite3.Connection,
        manifest: WorkspaceManifest,
        *,
        now: float,
    ) -> None:
        """幂等写入 manifest row；manifest_hash 冲突时校验 identity。"""

        existing = connection.execute(
            """
            SELECT * FROM workspace_manifests
            WHERE manifest_hash = ?
            """,
            (manifest.manifest_hash,),
        ).fetchone()
        if existing is not None:
            if (
                existing["manifest_id"]
                != manifest.manifest_id
                or existing["job_id"] != manifest.job_id
                or existing["generation"]
                != manifest.generation
            ):
                raise JobConflictError(
                    "manifest hash 命中了不同 identity"
                )
            return
        try:
            connection.execute(
                """
                INSERT INTO workspace_manifests (
                    manifest_id,
                    manifest_hash,
                    job_id,
                    run_id,
                    generation,
                    parent_manifest_id,
                    portable,
                    source_host_id,
                    source_worker_session_id,
                    manifest_json,
                    created_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    manifest.manifest_id,
                    manifest.manifest_hash,
                    manifest.job_id,
                    manifest.run_id,
                    manifest.generation,
                    manifest.parent_manifest_id,
                    int(manifest.portable),
                    manifest.source_host_id,
                    manifest.source_worker_session_id,
                    _dump_json(manifest.model_dump()),
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise JobConflictError(
                "workspace_manifest 唯一约束冲突"
            ) from exc

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
        submit_trace: TraceCarrier | None = None,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
        """
        返回 ``(record, created)``。

        同一个 idempotency key + 同一个请求返回旧 Job；
        同 key 不同请求必须冲突，不能悄悄复用。
        """

        current = time.time() if now is None else now
        request_payload = request.model_dump()
        requirements_payload = requirements.model_dump()
        # request_hash 只覆盖调用方意图（thread_id + request +
        # requirements），不含 workspace_manifest_hash：初始 manifest
        # 内嵌新生成的 job_id/run_id，属于派生数据，纳入会让相同请求
        # 的幂等重放误判为冲突。manifest 自身由 manifest_hash 唯一约束
        # 与 _upsert_manifest 单独校验，无需进入 request_hash。
        request_hash = _json_hash(
            {
                "thread_id": thread_id,
                "request": request_payload,
                "requirements": requirements_payload,
            }
        )
        # non-portable 初始 manifest 绑定源 host；portable 则不绑。
        affinity_host_id = (
            None
            if initial_manifest.portable
            else initial_manifest.source_host_id
        )

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if (
                    existing["request_hash"]
                    != request_hash
                ):
                    raise JobConflictError(
                        "相同 idempotency_key "
                        "对应了不同 Job 请求"
                    )
                connection.commit()
                return (
                    self._row_to_record(existing),
                    False,
                )

            self._upsert_manifest(
                connection,
                initial_manifest,
                now=current,
            )

            try:
                connection.execute(
                    """
                    INSERT INTO jobs (
                        job_id,
                        idempotency_key,
                        request_hash,
                        thread_id,
                        run_id,
                        run_dir,
                        request_json,
                        requirements_json,
                        required_worker_pool,
                        required_profile_id,
                        required_policy_hash,
                        required_backend,
                        min_workspace_free_bytes,
                        min_gpu_count,
                        required_cuda_major,
                        required_labels_json,
                        affinity_host_id,
                        workspace_manifest_id,
                        workspace_manifest_generation,
                        workspace_assignment_epoch,
                        status,
                        version,
                        attempt_count,
                        max_attempts,
                        wait_generation,
                        available_at,
                        submit_trace_json,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        'queued', 0, 0, ?, 0,
                        ?, ?,
                        ?, ?
                    )
                    """,
                    (
                        job_id,
                        idempotency_key,
                        request_hash,
                        thread_id,
                        run_id,
                        run_dir,
                        _dump_json(request_payload),
                        _dump_json(requirements_payload),
                        requirements.worker_pool,
                        requirements.execution_profile_id,
                        requirements.execution_policy_hash,
                        requirements.execution_backend,
                        requirements.min_workspace_free_bytes,
                        requirements.min_gpu_count,
                        requirements.cuda_major,
                        _dump_json(
                            requirements.required_labels
                        ),
                        affinity_host_id,
                        initial_manifest.manifest_id,
                        initial_manifest.generation,
                        0,
                        max_attempts,
                        current,
                        (
                            _dump_json(
                                submit_trace.model_dump()
                            )
                            if submit_trace is not None
                            else None
                        ),
                        current,
                        current,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise JobConflictError(
                    "thread_id、run_id、run_dir 或 "
                    "idempotency_key 已被其他 Job 使用"
                ) from exc

            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_submitted",
                actor="service",
                payload={
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "workspace_manifest_id": (
                        initial_manifest.manifest_id
                    ),
                },
                now=current,
            )
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_record(row), True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, job_id: str) -> JobRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise JobNotFoundError(
                f"未找到 job_id={job_id}"
            )
        return self._row_to_record(row)

    def list_jobs(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[JobRecord]:
        bounded_limit = max(1, min(limit, 500))
        with self._connect() as connection:
            if status is None:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM jobs
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (bounded_limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (status, bounded_limit),
                ).fetchall()
        return [
            self._row_to_record(row)
            for row in rows
        ]

    def list_events(
        self,
        job_id: str,
        *,
        limit: int = 200,
    ) -> list[JobEvent]:
        # 先确认 Job 存在，使拼错 ID 得到明确错误。
        self.get(job_id)
        bounded_limit = max(1, min(limit, 1000))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM job_events
                WHERE job_id = ?
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (job_id, bounded_limit),
            ).fetchall()
        return [
            JobEvent(
                event_id=row["event_id"],
                job_id=row["job_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                payload=_load_json(
                    row["payload_json"],
                    {},
                ),
                created_at=_iso(
                    row["created_at"]
                ),
            )
            for row in rows
        ]

    def list_events_after(
        self,
        job_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        """
        返回 event_id 严格大于游标的事件。

        event_id 是数据库内单调递增游标；客户端不得用数组下标或时间戳续读。
        """

        self.get(job_id)
        bounded_after = max(0, after_event_id)
        bounded_limit = max(
            1,
            min(limit, 1000),
        )

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM job_events
                WHERE job_id = ?
                  AND event_id > ?
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (
                    job_id,
                    bounded_after,
                    bounded_limit,
                ),
            ).fetchall()

        return [
            JobEvent(
                event_id=row["event_id"],
                job_id=row["job_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                payload=_load_json(
                    row["payload_json"],
                    {},
                ),
                created_at=_iso(
                    row["created_at"]
                ),
            )
            for row in rows
        ]

    def list_events_global_after(
        self,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        """Notification 等派生投影使用的全局持久游标。"""

        bounded_after = max(0, after_event_id)
        bounded_limit = max(1, min(limit, 1000))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM job_events
                WHERE event_id > ?
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (bounded_after, bounded_limit),
            ).fetchall()

        return [
            JobEvent(
                event_id=row["event_id"],
                job_id=row["job_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                payload=_load_json(row["payload_json"], {}),
                created_at=_iso(row["created_at"]),
            )
            for row in rows
        ]

    def _load_pending_resume(
        self,
        connection: sqlite3.Connection,
        resume_id: str | None,
    ) -> JobResumeRequest | None:
        if resume_id is None:
            return None
        row = connection.execute(
            """
            SELECT *
            FROM job_resumes
            WHERE resume_id = ?
            """,
            (resume_id,),
        ).fetchone()
        if row is None:
            raise JobStoreError(
                "Job 指向不存在的 pending resume"
            )
        return self._row_to_resume(row)

    def claim_next(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
        now: float | None = None,
    ) -> JobClaim | None:
        """
        只 claim 已经是 queued 且 capability 匹配的 Job。

        stale running Job 必须先由 JobReconciler 判定，不能在这里盲目重排。
        SQLite 使用 Python ``explain_compatibility`` 过滤，与 Postgres SQL 语义对照。
        """

        current = time.time() if now is None else now
        token = f"claim_{uuid4().hex}"
        assignment_token = f"wa_{uuid4().hex}"
        lease_expires = current + lease_seconds

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            session = connection.execute(
                """
                SELECT * FROM worker_sessions
                WHERE worker_session_id = ?
                """,
                (worker.worker_session_id,),
            ).fetchone()
            if session is None:
                raise JobConflictError(
                    "Worker 尚未注册"
                )
            if session["status"] != "active":
                connection.commit()
                return None
            if session["lease_expires_at"] <= current:
                raise JobConflictError(
                    "Worker session lease 已过期"
                )

            candidates = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE status = 'queued'
                  AND cancel_requested = 0
                  AND available_at <= ?
                ORDER BY available_at ASC, created_at ASC
                """,
                (current,),
            ).fetchall()
            chosen = None
            for candidate in candidates:
                requirements = JobRequirements.model_validate(
                    _load_json(
                        candidate["requirements_json"],
                        {},
                    )
                )
                explanation = explain_compatibility(
                    requirements=requirements,
                    worker=worker,
                    affinity_host_id=candidate[
                        "affinity_host_id"
                    ],
                )
                if explanation.compatible:
                    chosen = candidate
                    break
            if chosen is None:
                connection.commit()
                return None

            updated = connection.execute(
                """
                UPDATE jobs
                SET status = 'running',
                    version = version + 1,
                    attempt_count = attempt_count + 1,
                    worker_id = ?,
                    worker_session_id = ?,
                    worker_host_id = ?,
                    claim_token = ?,
                    workspace_assignment_token = ?,
                    workspace_assignment_epoch =
                        workspace_assignment_epoch + 1,
                    claimed_at = ?,
                    heartbeat_at = ?,
                    lease_expires_at = ?,
                    interrupt_nodes_json = '[]',
                    interrupts_json = '[]',
                    error_json = NULL,
                    reconciliation_json = NULL,
                    updated_at = ?
                WHERE job_id = ?
                  AND status = 'queued'
                  AND cancel_requested = 0
                """,
                (
                    worker.worker_id,
                    worker.worker_session_id,
                    worker.host_id,
                    token,
                    assignment_token,
                    current,
                    current,
                    lease_expires,
                    current,
                    chosen["job_id"],
                ),
            )
            if updated.rowcount != 1:
                raise JobConflictError(
                    "Job claim 竞争失败"
                )

            self._append_event(
                connection,
                job_id=chosen["job_id"],
                event_type="job_claimed",
                actor=worker.worker_id,
                payload={
                    "claim_token_suffix": token[-12:],
                    "worker_session_id": (
                        worker.worker_session_id
                    ),
                    "host_id": worker.host_id,
                    "lease_expires_at": _iso(
                        lease_expires
                    ),
                    "job_version": int(chosen["version"]) + 1,
                    "attempt_count": int(chosen["attempt_count"]) + 1,
                },
                now=current,
            )
            claimed_row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (chosen["job_id"],),
            ).fetchone()
            assert claimed_row is not None
            resume = self._load_pending_resume(
                connection,
                claimed_row["pending_resume_id"],
            )
            connection.commit()
            record = self._row_to_record(
                claimed_row
            )
            return JobClaim(
                job=record,
                claim_token=token,
                worker=worker,
                resume_request=resume,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def heartbeat(
        self,
        *,
        job_id: str,
        claim_token: str,
        lease_seconds: float,
        now: float | None = None,
    ) -> HeartbeatResult:
        current = time.time() if now is None else now
        lease_expires = current + lease_seconds

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE jobs
                SET heartbeat_at = ?,
                    lease_expires_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                  AND status IN (
                      'running',
                      'cancelling'
                  )
                  AND claim_token = ?
                """,
                (
                    current,
                    lease_expires,
                    current,
                    job_id,
                    claim_token,
                ),
            )
            if updated.rowcount != 1:
                raise LeaseLostError(
                    "heartbeat 被拒绝：claim 已失效"
                )
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return HeartbeatResult(
                lease_renewed=True,
                cancel_requested=bool(
                    row["cancel_requested"]
                ),
                cancellation_reason=row[
                    "cancellation_reason"
                ],
                lease_expires_at=_iso(
                    lease_expires
                ),
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _consume_pending_resume(
        self,
        connection: sqlite3.Connection,
        *,
        resume_id: str | None,
        now: float,
    ) -> None:
        if resume_id is None:
            return
        connection.execute(
            """
            UPDATE job_resumes
            SET status = 'consumed',
                consumed_at = COALESCE(
                    consumed_at,
                    ?
                )
            WHERE resume_id = ?
            """,
            (now, resume_id),
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
        current = time.time() if now is None else now
        nodes = list(
            dict.fromkeys(
                item.node for item in interrupts
            )
        )

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if (
                row is None
                or row["status"]
                not in {"running", "cancelling"}
                or row["claim_token"] != claim_token
            ):
                raise LeaseLostError(
                    "mark_waiting 被拒绝：claim 已失效"
                )

            self._consume_pending_resume(
                connection,
                resume_id=row["pending_resume_id"],
                now=current,
            )

            # Graph 刚返回 interrupt、Job 同时收到 cancel 时，取消优先。
            # 不能生成带 cancel_requested=true 的 waiting Job。
            if row["cancel_requested"]:
                connection.execute(
                    """
                    UPDATE jobs
                    SET status = 'cancelled',
                        version = version + 1,
                        worker_id = NULL,
                        worker_session_id = NULL,
                        worker_host_id = NULL,
                        claim_token = NULL,
                        workspace_assignment_token = NULL,
                        claimed_at = NULL,
                        heartbeat_at = NULL,
                        lease_expires_at = NULL,
                        interrupt_nodes_json = '[]',
                        interrupts_json = '[]',
                        pending_resume_id = NULL,
                        updated_at = ?
                    WHERE job_id = ?
                      AND claim_token = ?
                    """,
                    (
                        current,
                        job_id,
                        claim_token,
                    ),
                )
                self._append_event(
                    connection,
                    job_id=job_id,
                    event_type="job_cancelled",
                    actor=actor,
                    payload={
                        "reason": row[
                            "cancellation_reason"
                        ]
                    },
                    now=current,
                )
                cancelled = connection.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE job_id = ?
                    """,
                    (job_id,),
                ).fetchone()
                connection.commit()
                assert cancelled is not None
                return self._row_to_record(
                    cancelled
                )

            connection.execute(
                """
                UPDATE jobs
                SET status = 'waiting_for_input',
                    version = version + 1,
                    wait_generation = wait_generation + 1,
                    worker_id = NULL,
                    worker_session_id = NULL,
                    worker_host_id = NULL,
                    claim_token = NULL,
                    workspace_assignment_token = NULL,
                    claimed_at = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = NULL,
                    interrupt_nodes_json = ?,
                    interrupts_json = ?,
                    pending_resume_id = NULL,
                    result_json = ?,
                    updated_at = ?
                WHERE job_id = ?
                  AND claim_token = ?
                """,
                (
                    _dump_json(nodes),
                    _dump_json(
                        [
                            item.model_dump()
                            for item in interrupts
                        ]
                    ),
                    _dump_json(result),
                    current,
                    job_id,
                    claim_token,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_waiting_for_input",
                actor=actor,
                payload={
                    "job_version": int(row["version"]) + 1,
                    "wait_generation": int(row["wait_generation"]) + 1,
                    "interrupt_nodes": nodes,
                },
                now=current,
            )
            updated = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._row_to_record(updated)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_succeeded(
        self,
        *,
        job_id: str,
        claim_token: str,
        result: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        current = time.time() if now is None else now

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if (
                row is None
                or row["status"]
                not in {"running", "cancelling"}
                or row["claim_token"] != claim_token
            ):
                raise LeaseLostError(
                    "mark_succeeded 被拒绝：claim 已失效"
                )

            target_status = (
                "cancelled"
                if row["cancel_requested"]
                else "succeeded"
            )
            self._consume_pending_resume(
                connection,
                resume_id=row["pending_resume_id"],
                now=current,
            )
            connection.execute(
                """
                UPDATE jobs
                SET status = ?,
                    version = version + 1,
                    worker_id = NULL,
                    worker_session_id = NULL,
                    worker_host_id = NULL,
                    claim_token = NULL,
                    workspace_assignment_token = NULL,
                    claimed_at = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = NULL,
                    interrupt_nodes_json = '[]',
                    interrupts_json = '[]',
                    pending_resume_id = NULL,
                    result_json = ?,
                    updated_at = ?
                WHERE job_id = ?
                  AND claim_token = ?
                """,
                (
                    target_status,
                    _dump_json(result),
                    current,
                    job_id,
                    claim_token,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_cancelled"
                    if target_status == "cancelled"
                    else "job_succeeded"
                ),
                actor=actor,
                payload={
                    "job_version": int(row["version"]) + 1,
                    "final_status": result.get(
                        "final_status"
                    ),
                },
                now=current,
            )
            updated = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._row_to_record(updated)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_cancelled(
        self,
        *,
        job_id: str,
        claim_token: str,
        reason: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        current = time.time() if now is None else now

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if (
                row is None
                or row["status"]
                not in {"running", "cancelling"}
                or row["claim_token"] != claim_token
            ):
                raise LeaseLostError(
                    "mark_cancelled 被拒绝：claim 已失效"
                )
            self._consume_pending_resume(
                connection,
                resume_id=row["pending_resume_id"],
                now=current,
            )
            connection.execute(
                """
                UPDATE jobs
                SET status = 'cancelled',
                    version = version + 1,
                    worker_id = NULL,
                    worker_session_id = NULL,
                    worker_host_id = NULL,
                    claim_token = NULL,
                    workspace_assignment_token = NULL,
                    claimed_at = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = NULL,
                    pending_resume_id = NULL,
                    cancel_requested = 1,
                    cancellation_reason = ?,
                    updated_at = ?
                WHERE job_id = ?
                  AND claim_token = ?
                """,
                (
                    reason[:500],
                    current,
                    job_id,
                    claim_token,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_cancelled",
                actor=actor,
                payload={"reason": reason[:500]},
                now=current,
            )
            updated = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._row_to_record(updated)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

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
        """
        只有明确的 Job Runtime 瞬时错误才允许 retryable=True。

        未知 Graph 异常默认进入 failed；worker crash 由 lease reconcile 处理。
        """

        current = time.time() if now is None else now
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if (
                row is None
                or row["status"]
                not in {"running", "cancelling"}
                or row["claim_token"] != claim_token
            ):
                raise LeaseLostError(
                    "mark_failed 被拒绝：claim 已失效"
                )

            can_retry = (
                retryable
                and not row["cancel_requested"]
                and row["attempt_count"]
                < row["max_attempts"]
            )
            if can_retry:
                # Job-level retry 使用有上限的指数退避。
                delay = min(
                    60.0,
                    2.0 ** max(
                        row["attempt_count"] - 1,
                        0,
                    ),
                )
                target_status = "queued"
                available_at = current + delay
                event_type = "job_retry_scheduled"
            else:
                target_status = (
                    "cancelled"
                    if row["cancel_requested"]
                    else "failed"
                )
                available_at = current
                event_type = (
                    "job_cancelled"
                    if target_status == "cancelled"
                    else "job_failed"
                )

            if not can_retry:
                self._consume_pending_resume(
                    connection,
                    resume_id=row[
                        "pending_resume_id"
                    ],
                    now=current,
                )

            connection.execute(
                """
                UPDATE jobs
                SET status = ?,
                    version = version + 1,
                    worker_id = NULL,
                    worker_session_id = NULL,
                    worker_host_id = NULL,
                    claim_token = NULL,
                    workspace_assignment_token = NULL,
                    claimed_at = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = NULL,
                    pending_resume_id = CASE
                        WHEN ? = 1
                        THEN pending_resume_id
                        ELSE NULL
                    END,
                    available_at = ?,
                    error_json = ?,
                    updated_at = ?
                WHERE job_id = ?
                  AND claim_token = ?
                """,
                (
                    target_status,
                    int(can_retry),
                    available_at,
                    _dump_json(error),
                    current,
                    job_id,
                    claim_token,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=event_type,
                actor=actor,
                payload={
                    "job_version": int(row["version"]) + 1,
                    "retryable": retryable,
                    "error_type": error.get("type"),
                    "available_at": _iso(
                        available_at
                    ),
                },
                now=current,
            )
            updated = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._row_to_record(updated)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

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
        """
        返回 ``(job, created)``。

        resume 同时绑定：
        - job_id
        - 当前 wait_generation
        - expected_node
        - value hash
        """

        current = time.time() if now is None else now
        value_hash = _json_hash(value)

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT *
                FROM job_resumes
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if (
                    existing["job_id"] != job_id
                    or existing["expected_node"]
                    != expected_node
                    or existing["value_hash"]
                    != value_hash
                ):
                    raise JobConflictError(
                        "相同 resume idempotency_key "
                        "对应不同输入"
                    )
                job_row = connection.execute(
                    "SELECT * FROM jobs WHERE job_id = ?",
                    (job_id,),
                ).fetchone()
                connection.commit()
                assert job_row is not None
                return (
                    self._row_to_record(job_row),
                    False,
                )

            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise JobNotFoundError(
                    f"未找到 job_id={job_id}"
                )
            if (
                expected_job_version is not None
                and row["version"]
                != expected_job_version
            ):
                raise JobConflictError(
                    "Job version 已变化："
                    f"expected={expected_job_version}, "
                    f"current={row['version']}"
                )

            if (
                expected_wait_generation
                is not None
                and row["wait_generation"]
                != expected_wait_generation
            ):
                raise JobConflictError(
                    "interrupt generation 已变化："
                    f"expected={expected_wait_generation}, "
                    f"current={row['wait_generation']}"
                )
            if row["status"] != "waiting_for_input":
                raise JobConflictError(
                    "只有 waiting_for_input Job "
                    "可以 queue resume"
                )

            interrupt_nodes = _load_json(
                row["interrupt_nodes_json"],
                [],
            )
            if expected_node not in interrupt_nodes:
                raise JobConflictError(
                    f"resume 节点不匹配："
                    f"expected={expected_node}, "
                    f"current={interrupt_nodes}"
                )

            resume_id = f"resume_{uuid4().hex}"
            try:
                connection.execute(
                    """
                    INSERT INTO job_resumes (
                        resume_id,
                        job_id,
                        wait_generation,
                        idempotency_key,
                        expected_node,
                        value_json,
                        value_hash,
                        status,
                        created_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?,
                        'pending', ?
                    )
                    """,
                    (
                        resume_id,
                        job_id,
                        row["wait_generation"],
                        idempotency_key,
                        expected_node,
                        _dump_json(value),
                        value_hash,
                        current,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise JobConflictError(
                    "当前 interrupt generation "
                    "已经存在 resume"
                ) from exc

            connection.execute(
                """
                UPDATE jobs
                SET status = 'queued',
                    version = version + 1,
                    pending_resume_id = ?,
                    available_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                  AND status = 'waiting_for_input'
                """,
                (
                    resume_id,
                    current,
                    current,
                    job_id,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="job_resume_queued",
                actor=actor,
                payload={
                    "resume_id": resume_id,
                    "wait_generation": row[
                        "wait_generation"
                    ],
                    "expected_node": expected_node,
                    "value_hash": value_hash,
                },
                now=current,
            )
            updated = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._row_to_record(updated), True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

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
        current = time.time() if now is None else now
        bounded_reason = (
            reason.strip()
            or "user requested cancellation"
        )[:500]

        # CLI 旧调用可以不传 key；HTTP 写请求必须传。
        effective_key = (
            idempotency_key.strip()
            if idempotency_key
            else None
        )
        if (
            effective_key is not None
            and (
                not effective_key
                or len(effective_key) > 300
            )
        ):
            raise ValueError(
                "idempotency_key 长度必须为 1..300"
            )
        request_hash = _json_hash(
            {
                "job_id": job_id,
                "command_type": "cancel",
                "reason": bounded_reason,
            }
        )

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")

            # 幂等重放优先于版本校验。
            if effective_key is not None:
                existing = connection.execute(
                    """
                    SELECT *
                    FROM job_commands
                    WHERE idempotency_key = ?
                    """,
                    (effective_key,),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["job_id"] != job_id
                        or existing["command_type"]
                        != "cancel"
                        or existing["request_hash"]
                        != request_hash
                    ):
                        raise JobConflictError(
                            "相同 cancel idempotency_key "
                            "对应不同请求"
                        )

                    replayed_job = connection.execute(
                        """
                        SELECT *
                        FROM jobs
                        WHERE job_id = ?
                        """,
                        (job_id,),
                    ).fetchone()
                    if replayed_job is None:
                        raise JobNotFoundError(
                            f"未找到 job_id={job_id}"
                        )
                    connection.commit()
                    return self._row_to_record(
                        replayed_job
                    )

            row = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                raise JobNotFoundError(
                    f"未找到 job_id={job_id}"
                )

            if (
                expected_job_version is not None
                and row["version"]
                != expected_job_version
            ):
                raise JobConflictError(
                    "Job version 已变化："
                    f"expected={expected_job_version}, "
                    f"current={row['version']}"
                )

            terminal = row["status"] in {
                "succeeded",
                "failed",
                "cancelled",
            }

            if not terminal:
                if row["status"] in {
                    "queued",
                    "waiting_for_input",
                }:
                    target_status = "cancelled"
                    clear_ownership = True
                elif row["status"] in {
                    "running",
                    "cancelling",
                }:
                    target_status = "cancelling"
                    clear_ownership = False
                else:
                    # reconciliation_required 不能靠 API 猜测孤儿进程状态。
                    target_status = (
                        "reconciliation_required"
                    )
                    clear_ownership = True

                if clear_ownership:
                    self._consume_pending_resume(
                        connection,
                        resume_id=row[
                            "pending_resume_id"
                        ],
                        now=current,
                    )
                    ownership_sql = """
                        worker_id = NULL,
                        worker_session_id = NULL,
                        worker_host_id = NULL,
                        claim_token = NULL,
                        workspace_assignment_token = NULL,
                        claimed_at = NULL,
                        heartbeat_at = NULL,
                        lease_expires_at = NULL,
                        pending_resume_id = NULL,
                    """
                else:
                    ownership_sql = ""

                connection.execute(
                    f"""
                    UPDATE jobs
                    SET status = ?,
                        version = version + 1,
                        {ownership_sql}
                        cancel_requested = 1,
                        cancellation_reason = ?,
                        updated_at = ?
                    WHERE job_id = ?
                    """,
                    (
                        target_status,
                        bounded_reason,
                        current,
                        job_id,
                    ),
                )
                self._append_event(
                    connection,
                    job_id=job_id,
                    event_type=(
                        "job_cancelled"
                        if target_status
                        == "cancelled"
                        else "job_cancel_requested"
                    ),
                    actor=actor,
                    payload={
                        "reason": bounded_reason
                    },
                    now=current,
                )

            if effective_key is not None:
                connection.execute(
                    """
                    INSERT INTO job_commands (
                        command_id,
                        job_id,
                        command_type,
                        idempotency_key,
                        request_hash,
                        created_at
                    )
                    VALUES (?, ?, 'cancel', ?, ?, ?)
                    """,
                    (
                        f"command_{uuid4().hex}",
                        job_id,
                        effective_key,
                        request_hash,
                        current,
                    ),
                )

            updated = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._row_to_record(updated)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_expired_running(
        self,
        *,
        now: float | None = None,
        limit: int = 100,
    ) -> list[JobRecord]:
        current = time.time() if now is None else now
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE status IN (
                    'running',
                    'cancelling'
                )
                  AND lease_expires_at <= ?
                ORDER BY lease_expires_at ASC
                LIMIT ?
                """,
                (current, max(1, min(limit, 500))),
            ).fetchall()
        return [
            self._row_to_record(row)
            for row in rows
        ]

    def requeue_expired(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        current = time.time() if now is None else now
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if (
                row is None
                or row["claim_token"]
                != expired_claim_token
                or row["status"]
                not in {"running", "cancelling"}
                or row["lease_expires_at"] > current
            ):
                raise LeaseLostError(
                    "stale Job 已被其他 worker 处理"
                )

            if row["cancel_requested"]:
                status = "cancelled"
            elif (
                row["attempt_count"]
                >= row["max_attempts"]
            ):
                status = "failed"
            else:
                status = "queued"

            error = None
            if status == "failed":
                error = {
                    "type": "LeaseAttemptsExhausted",
                    "message": detail[:1000],
                }

            connection.execute(
                """
                UPDATE jobs
                SET status = ?,
                    version = version + 1,
                    worker_id = NULL,
                    worker_session_id = NULL,
                    worker_host_id = NULL,
                    claim_token = NULL,
                    workspace_assignment_token = NULL,
                    claimed_at = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = NULL,
                    available_at = ?,
                    error_json = ?,
                    updated_at = ?
                WHERE job_id = ?
                  AND claim_token = ?
                """,
                (
                    status,
                    current,
                    (
                        _dump_json(error)
                        if error is not None
                        else None
                    ),
                    current,
                    job_id,
                    expired_claim_token,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_lease_requeued"
                    if status == "queued"
                    else f"job_{status}"
                ),
                actor=actor,
                payload={
                    "job_version": int(row["version"]) + 1,
                    "attempt_count": int(row["attempt_count"]),
                    "detail_code": "lease_expired_requeued",
                },
                now=current,
            )
            updated = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._row_to_record(updated)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def require_reconciliation(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        reconciliation: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        current = time.time() if now is None else now
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated_count = connection.execute(
                """
                UPDATE jobs
                SET status = 'reconciliation_required',
                    version = version + 1,
                    worker_id = NULL,
                    worker_session_id = NULL,
                    worker_host_id = NULL,
                    claim_token = NULL,
                    workspace_assignment_token = NULL,
                    claimed_at = NULL,
                    heartbeat_at = NULL,
                    lease_expires_at = NULL,
                    reconciliation_json = ?,
                    updated_at = ?
                WHERE job_id = ?
                  AND claim_token = ?
                  AND status IN (
                      'running',
                      'cancelling'
                  )
                  AND lease_expires_at <= ?
                """,
                (
                    _dump_json(reconciliation),
                    current,
                    job_id,
                    expired_claim_token,
                    current,
                ),
            ).rowcount
            if updated_count != 1:
                raise LeaseLostError(
                    "require_reconciliation 被拒绝："
                    "stale claim 已变化"
                )
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            assert row is not None
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "job_reconciliation_required"
                ),
                actor=actor,
                payload={
                    "job_version": int(row["version"]),
                    "detail_code": (
                        "lease_expired_reconciliation_required"
                    ),
                    "disposition": reconciliation.get(
                        "disposition"
                    ),
                },
                now=current,
            )
            connection.commit()
            assert row is not None
            return self._row_to_record(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def resolve_reconciliation(
        self,
        *,
        job_id: str,
        decision: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        """
        process_reconcile.py 完成进程身份检查后才能调用。

        decision 只允许：
        - requeue
        - failed
        - cancelled
        """

        if decision not in {
            "requeue",
            "failed",
            "cancelled",
        }:
            raise ValueError(
                f"无效 reconciliation decision：{decision}"
            )

        current = time.time() if now is None else now
        target_status = (
            "queued"
            if decision == "requeue"
            else decision
        )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated_count = connection.execute(
                """
                UPDATE jobs
                SET status = ?,
                    version = version + 1,
                    available_at = ?,
                    reconciliation_json = NULL,
                    error_json = CASE
                        WHEN ? = 'failed'
                        THEN ?
                        ELSE error_json
                    END,
                    updated_at = ?
                WHERE job_id = ?
                  AND status = 'reconciliation_required'
                """,
                (
                    target_status,
                    current,
                    target_status,
                    _dump_json(
                        {
                            "type": (
                                "ManualReconciliation"
                            ),
                            "message": detail[:1000],
                        }
                    ),
                    current,
                    job_id,
                ),
            ).rowcount
            if updated_count != 1:
                raise JobConflictError(
                    "Job 当前不在 "
                    "reconciliation_required"
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
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_record(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # Phase 26：Worker session 与 workspace 持久化（SQLite 等价实现）。
    # ------------------------------------------------------------------

    def _owned_job(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        claim_token: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if (
            row is None
            or row["status"]
            not in {"running", "cancelling"}
            or row["claim_token"] != claim_token
        ):
            raise LeaseLostError("Job claim 已失效")
        return row

    def _binding_from_row(
        self,
        row: sqlite3.Row,
    ) -> WorkspaceBinding:
        return WorkspaceBinding(
            assignment_id=str(row["assignment_id"]),
            assignment_epoch=int(row["assignment_epoch"]),
            assignment_token=str(row["assignment_token"]),
            job_id=str(row["job_id"]),
            run_id=str(row["run_id"]),
            manifest_id=str(row["manifest_id"]),
            manifest_hash=str(row["manifest_hash"]),
            manifest_generation=int(
                row["manifest_generation"]
            ),
            worker_session_id=str(
                row["worker_session_id"]
            ),
            host_id=str(row["host_id"]),
            workspace_root=str(row["workspace_root"]),
            run_dir=str(row["run_dir"]),
            repo_path=str(row["repo_path"]),
            paper_path=str(row["paper_path"]),
            log_path=row["log_path"],
            status=str(row["status"]),
            created_at=_iso(row["created_at"]),
            updated_at=_iso(row["updated_at"]),
        )

    def _manifest_from_row(
        self,
        row: sqlite3.Row,
    ) -> WorkspaceManifest:
        manifest = WorkspaceManifest.model_validate(
            _load_json(row["manifest_json"], {})
        )
        validate_manifest_hash(manifest)
        if (
            manifest.manifest_id != row["manifest_id"]
            or manifest.manifest_hash
            != row["manifest_hash"]
        ):
            raise JobConflictError(
                "manifest row identity 与 JSON 不一致"
            )
        return manifest

    def register_worker(
        self,
        *,
        worker: WorkerIdentity,
        lease_seconds: float,
    ) -> WorkerSession:
        current = time.time()
        lease_expires = current + lease_seconds
        caps = worker.capabilities
        caps_payload = _dump_json(caps.model_dump())

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT * FROM worker_sessions
                WHERE worker_session_id = ?
                """,
                (worker.worker_session_id,),
            ).fetchone()
            values = (
                worker.worker_id,
                worker.host_id,
                worker.pool,
                worker.workspace_root,
                caps_payload,
                "active",
                current,
                current,
                lease_expires,
            )
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO worker_sessions (
                        worker_session_id,
                        worker_id,
                        host_id,
                        worker_pool,
                        workspace_root,
                        capabilities_json,
                        status,
                        registered_at,
                        heartbeat_at,
                        lease_expires_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        worker.worker_session_id,
                        *values,
                    ),
                )
            else:
                immutable = (
                    existing["worker_id"],
                    existing["host_id"],
                    existing["workspace_root"],
                )
                expected = (
                    worker.worker_id,
                    worker.host_id,
                    worker.workspace_root,
                )
                if immutable != expected:
                    raise JobConflictError(
                        "worker_session_id 被不同身份复用"
                    )
                connection.execute(
                    """
                    UPDATE worker_sessions
                    SET worker_id = ?,
                        host_id = ?,
                        worker_pool = ?,
                        workspace_root = ?,
                        capabilities_json = ?,
                        status = 'active',
                        heartbeat_at = ?,
                        lease_expires_at = ?
                    WHERE worker_session_id = ?
                    """,
                    (
                        worker.worker_id,
                        worker.host_id,
                        worker.pool,
                        worker.workspace_root,
                        caps_payload,
                        current,
                        lease_expires,
                        worker.worker_session_id,
                    ),
                )
            row = connection.execute(
                """
                SELECT * FROM worker_sessions
                WHERE worker_session_id = ?
                """,
                (worker.worker_session_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_worker_session(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

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
        current = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE worker_sessions
                SET status = 'draining',
                    heartbeat_at = ?
                WHERE worker_session_id = ?
                """,
                (current, worker_session_id),
            ).rowcount
            if updated != 1:
                raise JobNotFoundError(
                    "Worker session 不存在"
                )
            row = connection.execute(
                """
                SELECT * FROM worker_sessions
                WHERE worker_session_id = ?
                """,
                (worker_session_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_worker_session(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_workers(
        self,
        *,
        include_expired: bool = False,
        limit: int = 100,
    ) -> list[WorkerSession]:
        bounded = max(1, min(limit, 500))
        current = time.time()
        with self._connect() as connection:
            if include_expired:
                rows = connection.execute(
                    """
                    SELECT * FROM worker_sessions
                    ORDER BY registered_at DESC
                    LIMIT ?
                    """,
                    (bounded,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM worker_sessions
                    WHERE lease_expires_at > ?
                    ORDER BY registered_at DESC
                    LIMIT ?
                    """,
                    (current, bounded),
                ).fetchall()
        return [
            self._row_to_worker_session(row)
            for row in rows
        ]

    def get_workspace_manifest(
        self,
        manifest_id: str,
    ) -> WorkspaceManifest:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM workspace_manifests
                WHERE manifest_id = ?
                """,
                (manifest_id,),
            ).fetchone()
        if row is None:
            raise JobNotFoundError(
                f"未找到 manifest_id={manifest_id}"
            )
        return self._manifest_from_row(row)

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
        validate_manifest_hash(manifest)
        current = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            job = self._owned_job(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            if (
                job["workspace_assignment_token"]
                != assignment_token
            ):
                raise LeaseLostError(
                    "workspace assignment token 已失效"
                )
            if (
                job["worker_session_id"]
                != worker.worker_session_id
            ):
                raise LeaseLostError(
                    "worker session 已失效"
                )
            if (
                job["workspace_manifest_id"]
                != manifest.manifest_id
            ):
                raise JobConflictError(
                    "claim 使用了过期 workspace manifest"
                )

            epoch = int(job["workspace_assignment_epoch"])
            existing = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE job_id = ? AND assignment_epoch = ?
                """,
                (job_id, epoch),
            ).fetchone()
            if existing is not None:
                expected = {
                    "assignment_token": assignment_token,
                    "manifest_id": manifest.manifest_id,
                    "manifest_hash": manifest.manifest_hash,
                    "worker_session_id": (
                        worker.worker_session_id
                    ),
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
                connection.commit()
                return self._binding_from_row(existing)

            assignment_id = f"was_{uuid4().hex}"
            connection.execute(
                """
                INSERT INTO workspace_assignments (
                    assignment_id,
                    job_id,
                    run_id,
                    assignment_epoch,
                    assignment_token,
                    manifest_id,
                    manifest_hash,
                    manifest_generation,
                    worker_session_id,
                    host_id,
                    workspace_root,
                    run_dir,
                    repo_path,
                    paper_path,
                    log_path,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    'materializing', ?, ?
                )
                """,
                (
                    assignment_id,
                    job_id,
                    job["run_id"],
                    epoch,
                    assignment_token,
                    manifest.manifest_id,
                    manifest.manifest_hash,
                    manifest.generation,
                    worker.worker_session_id,
                    worker.host_id,
                    workspace_root,
                    run_dir,
                    repo_path,
                    paper_path,
                    log_path,
                    current,
                    current,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="workspace_materializing",
                actor=worker.worker_id,
                payload={
                    "assignment_id": assignment_id,
                    "assignment_epoch": epoch,
                    "manifest_id": manifest.manifest_id,
                    "host_id": worker.host_id,
                },
                now=current,
            )
            row = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE assignment_id = ?
                """,
                (assignment_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._binding_from_row(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_workspace_ready(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
    ) -> WorkspaceBinding:
        current = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            job = self._owned_job(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            if (
                job["workspace_assignment_token"]
                != assignment_token
            ):
                raise LeaseLostError(
                    "workspace assignment token 已失效"
                )
            row = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE job_id = ? AND assignment_token = ?
                """,
                (job_id, assignment_token),
            ).fetchone()
            if row is None:
                raise JobConflictError(
                    "workspace assignment 不存在"
                )
            if row["status"] == "ready":
                connection.commit()
                return self._binding_from_row(row)
            if row["status"] != "materializing":
                raise JobConflictError(
                    f"不能从 {row['status']} 转成 ready"
                )
            result = connection.execute(
                """
                UPDATE workspace_assignments
                SET status = 'ready', updated_at = ?
                WHERE assignment_id = ?
                  AND status = 'materializing'
                """,
                (current, row["assignment_id"]),
            )
            if result.rowcount != 1:
                raise LeaseLostError(
                    "workspace ready fencing 失败"
                )
            # 当前 epoch 已 ready 后，旧目录才允许进入 GC 候选。
            connection.execute(
                """
                UPDATE workspace_assignments
                SET status = 'released', updated_at = ?
                WHERE job_id = ?
                  AND assignment_epoch < ?
                  AND status = 'ready'
                """,
                (
                    current,
                    job_id,
                    int(row["assignment_epoch"]),
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="workspace_ready",
                actor=job["worker_id"],
                payload={
                    "assignment_id": row["assignment_id"],
                    "assignment_epoch": int(
                        row["assignment_epoch"]
                    ),
                    "manifest_id": row["manifest_id"],
                },
                now=current,
            )
            ready = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE assignment_id = ?
                """,
                (row["assignment_id"],),
            ).fetchone()
            connection.commit()
            assert ready is not None
            return self._binding_from_row(ready)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def fail_workspace_assignment(
        self,
        *,
        job_id: str,
        claim_token: str,
        assignment_token: str,
        reason: str,
    ) -> WorkspaceBinding:
        current = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            job = self._owned_job(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            if (
                job["workspace_assignment_token"]
                != assignment_token
            ):
                raise LeaseLostError(
                    "workspace assignment token 已失效"
                )
            row = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE job_id = ? AND assignment_token = ?
                """,
                (job_id, assignment_token),
            ).fetchone()
            if row is None:
                raise JobConflictError(
                    "workspace assignment 不存在"
                )
            if row["status"] != "materializing":
                connection.commit()
                return self._binding_from_row(row)
            connection.execute(
                """
                UPDATE workspace_assignments
                SET status = 'failed',
                    error_code = ?,
                    updated_at = ?
                WHERE assignment_id = ?
                  AND status = 'materializing'
                """,
                (
                    reason[:120],
                    current,
                    row["assignment_id"],
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=(
                    "workspace_materialization_failed"
                ),
                actor=job["worker_id"],
                payload={
                    "assignment_id": row["assignment_id"],
                    "error_code": reason[:120],
                },
                now=current,
            )
            failed = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE assignment_id = ?
                """,
                (row["assignment_id"],),
            ).fetchone()
            connection.commit()
            assert failed is not None
            return self._binding_from_row(failed)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def current_workspace_binding(
        self,
        job_id: str,
    ) -> WorkspaceBinding | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE job_id = ?
                ORDER BY assignment_epoch DESC
                LIMIT 1
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return self._binding_from_row(row)

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
        validate_manifest_hash(manifest)
        current = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._owned_job(
                connection,
                job_id=job_id,
                claim_token=claim_token,
            )
            if (
                row["workspace_assignment_token"]
                != assignment_token
            ):
                raise LeaseLostError(
                    "workspace assignment 已失效"
                )
            if (
                manifest.job_id != job_id
                or manifest.run_id != row["run_id"]
            ):
                raise JobConflictError(
                    "manifest Job identity 不一致"
                )
            if (
                row["workspace_manifest_id"]
                == manifest.manifest_id
            ):
                existing = connection.execute(
                    """
                    SELECT * FROM workspace_manifests
                    WHERE manifest_id = ?
                    """,
                    (manifest.manifest_id,),
                ).fetchone()
                if (
                    existing is None
                    or existing["manifest_hash"]
                    != manifest.manifest_hash
                ):
                    raise JobConflictError(
                        "manifest_id 内容冲突"
                    )
                connection.commit()
                return self._row_to_record(row)
            if (
                manifest.parent_manifest_id
                != row["workspace_manifest_id"]
            ):
                raise JobConflictError(
                    "manifest parent 不是当前 head"
                )
            if (
                manifest.generation
                != row["workspace_manifest_generation"] + 1
            ):
                raise JobConflictError(
                    "manifest generation 不连续"
                )
            if manifest.portable and affinity_host_id is not None:
                raise JobConflictError(
                    "portable manifest 不应设置 affinity"
                )
            if (
                not manifest.portable
                and affinity_host_id != row["worker_host_id"]
            ):
                raise JobConflictError(
                    "non-portable manifest 必须绑定当前 worker host"
                )

            self._upsert_manifest(
                connection,
                manifest,
                now=current,
            )
            updated = connection.execute(
                """
                UPDATE jobs
                SET workspace_manifest_id = ?,
                    workspace_manifest_generation = ?,
                    affinity_host_id = ?,
                    updated_at = ?
                WHERE job_id = ?
                  AND claim_token = ?
                  AND workspace_assignment_token = ?
                """,
                (
                    manifest.manifest_id,
                    manifest.generation,
                    affinity_host_id,
                    current,
                    job_id,
                    claim_token,
                    assignment_token,
                ),
            )
            if updated.rowcount != 1:
                raise LeaseLostError(
                    "seal_workspace_manifest fencing 失败"
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
            final = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            connection.commit()
            assert final is not None
            return self._row_to_record(final)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_workspace_gc_candidates(
        self,
        *,
        host_id: str,
        older_than: str,
        limit: int = 100,
    ) -> list[WorkspaceBinding]:
        bounded = max(1, min(limit, 500))
        # older_than 为 ISO 时间戳；SQLite 用字符串比较 ISO8601 即可。
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE host_id = ?
                  AND status = 'released'
                  AND updated_at <= ?
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (host_id, older_than, bounded),
            ).fetchall()
        return [
            self._binding_from_row(row) for row in rows
        ]

    def mark_workspace_garbage_collected(
        self,
        *,
        assignment_id: str,
        assignment_token: str,
        host_id: str,
    ) -> WorkspaceBinding:
        current = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE workspace_assignments
                SET status = 'garbage_collected',
                    updated_at = ?
                WHERE assignment_id = ?
                  AND assignment_token = ?
                  AND host_id = ?
                  AND status = 'released'
                """,
                (
                    current,
                    assignment_id,
                    assignment_token,
                    host_id,
                ),
            )
            if updated.rowcount != 1:
                raise LeaseLostError(
                    "workspace GC fencing 失败"
                )
            row = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE assignment_id = ?
                """,
                (assignment_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._binding_from_row(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # Phase 35: Retention methods
    # ------------------------------------------------------------------

    def list_retention_candidates(
        self,
        *,
        updated_before: float,
        limit: int,
    ) -> list[JobRecord]:
        bounded = max(1, min(limit, 100))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM jobs
                WHERE status IN ('succeeded', 'failed', 'cancelled')
                  AND updated_at <= ?
                ORDER BY updated_at ASC, job_id ASC
                LIMIT ?
                """,
                (updated_before, bounded),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_workspace_bindings_for_retention(
        self,
        job_id: str,
    ) -> list[WorkspaceBinding]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM workspace_assignments
                WHERE job_id = ?
                ORDER BY assignment_epoch ASC
                """,
                (job_id,),
            ).fetchall()
        return [self._binding_from_row(row) for row in rows]

    def list_workspace_manifests_for_retention(
        self,
        job_id: str,
    ) -> list[WorkspaceManifest]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM workspace_manifests
                WHERE job_id = ?
                ORDER BY generation ASC
                """,
                (job_id,),
            ).fetchall()
        return [self._manifest_from_row(row) for row in rows]

    def count_workspace_blob_references(
        self,
        *,
        object_key: str,
    ) -> int:
        count = 0
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT manifest_json FROM workspace_manifests"
            ).fetchall()
        for row in rows:
            manifest = WorkspaceManifest.model_validate_json(
                row["manifest_json"]
            )
            count += sum(
                1 for entry in manifest.entries if entry.object_key == object_key
            )
        return count

    def delete_job_for_retention(
        self,
        *,
        job_id: str,
        expected_version: int,
        expected_status: str,
    ) -> bool:
        if expected_status not in {"succeeded", "failed", "cancelled"}:
            raise JobConflictError("Retention 只能删除终态 Job")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status, version FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                connection.commit()
                return False
            if row["status"] != expected_status or row["version"] != expected_version:
                raise JobConflictError("Job 状态或 version 已变化，拒绝 GC")

            connection.execute(
                "DELETE FROM workspace_assignments WHERE job_id = ?",
                (job_id,),
            )
            connection.execute(
                "DELETE FROM workspace_manifests WHERE job_id = ?",
                (job_id,),
            )
            changed = connection.execute(
                """
                DELETE FROM jobs
                WHERE job_id = ? AND version = ? AND status = ?
                """,
                (job_id, expected_version, expected_status),
            ).rowcount
            if changed != 1:
                raise JobConflictError("Job retention fencing 失败")
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()