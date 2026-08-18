"""Retention 审计账本：保存 Plan、确认、逐步 journal 和 hold。"""
from __future__ import annotations
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from app.retention.errors import RetentionConflict, RetentionNotFound
from app.retention.schemas import (
    CleanupPlan,
    CleanupStep,
    RetentionHold,
)

def _iso(value: float | None = None) -> str:
    return datetime.fromtimestamp(
        time.time() if value is None else value,
        tz=timezone.utc,
    ).isoformat()

class SqliteRetentionRepository:
    """保存 Plan、确认、逐步 journal 和 hold。"""

    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS retention_plans (
                    plan_id TEXT PRIMARY KEY,
                    plan_hash TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    confirmed_at REAL,
                    completed_at REAL,
                    failure_code TEXT
                );

                CREATE TABLE IF NOT EXISTS retention_steps (
                    plan_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detail TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (plan_id, job_id, step_name),
                    FOREIGN KEY (plan_id)
                        REFERENCES retention_plans(plan_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS retention_holds (
                    job_id TEXT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _plan(row: sqlite3.Row) -> CleanupPlan:
        payload = json.loads(row["payload_json"])
        payload.update(
            {
                "status": row["status"],
                "confirmed_at": (
                    _iso(row["confirmed_at"])
                    if row["confirmed_at"] is not None
                    else None
                ),
                "completed_at": (
                    _iso(row["completed_at"])
                    if row["completed_at"] is not None
                    else None
                ),
                "failure_code": row["failure_code"],
            }
        )
        return CleanupPlan.model_validate(payload)

    def create_plan(self, plan: CleanupPlan) -> CleanupPlan:
        payload = plan.model_dump(
            mode="json",
            exclude={
                "status",
                "confirmed_at",
                "completed_at",
                "failure_code",
            },
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO retention_plans (
                    plan_id, plan_hash, status, payload_json,
                    created_at, expires_at
                ) VALUES (?, ?, 'planned', ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    plan.plan_hash,
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    datetime.fromisoformat(plan.created_at).timestamp(),
                    datetime.fromisoformat(plan.expires_at).timestamp(),
                ),
            )
        return self.get_plan(plan.plan_id)

    def get_plan(self, plan_id: str) -> CleanupPlan:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM retention_plans WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
        if row is None:
            raise RetentionNotFound(f"cleanup plan 不存在：{plan_id}")
        return self._plan(row)

    def confirm_plan(self, *, plan_id: str, plan_hash: str) -> CleanupPlan:
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """
                UPDATE retention_plans
                SET status = 'confirmed', confirmed_at = ?
                WHERE plan_id = ?
                  AND plan_hash = ?
                  AND status = 'planned'
                  AND expires_at > ?
                """,
                (now, plan_id, plan_hash, now),
            ).rowcount
            if changed != 1:
                raise RetentionConflict(
                    "Plan 不存在、已过期、状态已变化或 hash 不匹配"
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self.get_plan(plan_id)

    def claim_sweep(self, *, plan_id: str, plan_hash: str) -> CleanupPlan:
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM retention_plans WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()
            if (
                row is None
                or row["plan_hash"] != plan_hash
                or row["expires_at"] <= now
                or row["status"] not in {"confirmed", "failed", "sweeping"}
            ):
                raise RetentionConflict(
                    "Plan 不能执行：状态、过期时间或 hash 不匹配"
                )
            connection.execute(
                """
                UPDATE retention_plans
                SET status = 'sweeping', failure_code = NULL
                WHERE plan_id = ?
                """,
                (plan_id,),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self.get_plan(plan_id)

    def step_completed(
        self,
        *,
        plan_id: str,
        job_id: str,
        step_name: str,
    ) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT status FROM retention_steps
                WHERE plan_id = ? AND job_id = ? AND step_name = ?
                """,
                (plan_id, job_id, step_name),
            ).fetchone()
        return row is not None and row["status"] == "completed"

    def record_step(
        self,
        *,
        plan_id: str,
        job_id: str,
        step_name: str,
        status: str,
        detail: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO retention_steps (
                    plan_id, job_id, step_name, status, detail, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(plan_id, job_id, step_name) DO UPDATE SET
                    status = excluded.status,
                    detail = excluded.detail,
                    updated_at = excluded.updated_at
                """,
                (plan_id, job_id, step_name, status, detail, time.time()),
            )

    def list_steps(self, plan_id: str) -> list[CleanupStep]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM retention_steps
                WHERE plan_id = ?
                ORDER BY updated_at, job_id, step_name
                """,
                (plan_id,),
            ).fetchall()
        return [
            CleanupStep(
                plan_id=row["plan_id"],
                job_id=row["job_id"],
                step_name=row["step_name"],
                status=row["status"],
                detail=row["detail"],
                updated_at=_iso(row["updated_at"]),
            )
            for row in rows
        ]

    def finish_plan(self, *, plan_id: str) -> CleanupPlan:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE retention_plans
                SET status = 'completed', completed_at = ?, failure_code = NULL
                WHERE plan_id = ? AND status = 'sweeping'
                """,
                (time.time(), plan_id),
            )
        return self.get_plan(plan_id)

    def fail_plan(self, *, plan_id: str, code: str) -> CleanupPlan:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE retention_plans
                SET status = 'failed', failure_code = ?
                WHERE plan_id = ? AND status = 'sweeping'
                """,
                (code[:200], plan_id),
            )
        return self.get_plan(plan_id)

    def put_hold(self, *, job_id: str, reason: str, actor: str) -> RetentionHold:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO retention_holds (job_id, reason, actor, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    reason = excluded.reason,
                    actor = excluded.actor,
                    created_at = excluded.created_at
                """,
                (job_id, reason, actor, now),
            )
        return RetentionHold(
            job_id=job_id,
            reason=reason,
            actor=actor,
            created_at=_iso(now),
        )

    def delete_hold(self, job_id: str) -> bool:
        with self._connect() as connection:
            return (
                connection.execute(
                    "DELETE FROM retention_holds WHERE job_id = ?",
                    (job_id,),
                ).rowcount
                == 1
            )

    def held_job_ids(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT job_id FROM retention_holds"
            ).fetchall()
        return {str(row["job_id"]) for row in rows}

    def list_holds(self) -> list[RetentionHold]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM retention_holds
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            RetentionHold(
                job_id=row["job_id"],
                reason=row["reason"],
                actor=row["actor"],
                created_at=_iso(row["created_at"]),
            )
            for row in rows
        ]
