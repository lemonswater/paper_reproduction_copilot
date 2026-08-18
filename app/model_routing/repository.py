from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.model_routing.errors import (
    ModelBudgetExceeded,
    ModelLedgerConflict,
    ModelLedgerIntegrityError,
)
from app.model_routing.schemas import (
    ModelBudgetPolicy,
    ModelBudgetSummary,
    ModelInvocationRecord,
    ModelReservationRequest,
    ModelUsage,
)


TERMINAL_STATUSES = {
    "succeeded",
    "failed",
    "usage_unknown",
}
ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,119}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime 必须包含 timezone")
    return value.astimezone(timezone.utc).isoformat()


class SqliteModelLedger:
    def __init__(
        self,
        path: Path,
        *,
        budget: ModelBudgetPolicy,
    ) -> None:
        self.path = path
        self.budget = budget
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=30.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS model_invocations (
                    invocation_id TEXT PRIMARY KEY,
                    request_sha256 TEXT NOT NULL,
                    decision_sha256 TEXT NOT NULL,
                    task_kind TEXT NOT NULL,
                    job_id TEXT,
                    run_id TEXT,
                    node_name TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    pricing_version TEXT NOT NULL,
                    enforced INTEGER NOT NULL CHECK(enforced IN (0, 1)),
                    status TEXT NOT NULL,
                    reserved_input_tokens INTEGER NOT NULL,
                    reserved_output_tokens INTEGER NOT NULL,
                    reserved_cost_micro_usd INTEGER,
                    actual_input_tokens INTEGER,
                    actual_output_tokens INTEGER,
                    actual_cost_micro_usd INTEGER,
                    usage_quality TEXT,
                    provider_response_count INTEGER,
                    prompt_chars INTEGER NOT NULL,
                    prompt_sha256 TEXT NOT NULL,
                    schema_sha256 TEXT,
                    latency_ms INTEGER,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    lease_expires_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_model_invocations_date
                    ON model_invocations(created_at, status);
                CREATE INDEX IF NOT EXISTS idx_model_invocations_job
                    ON model_invocations(job_id, created_at, status);
                CREATE INDEX IF NOT EXISTS idx_model_invocations_task
                    ON model_invocations(task_kind, created_at);
                """
            )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    @staticmethod
    def _record(row: sqlite3.Row) -> ModelInvocationRecord:
        try:
            record = ModelInvocationRecord(
                invocation_id=row["invocation_id"],
                request_sha256=row["request_sha256"],
                decision_sha256=row["decision_sha256"],
                task_kind=row["task_kind"],
                job_id=row["job_id"],
                run_id=row["run_id"],
                node_name=row["node_name"],
                profile_id=row["profile_id"],
                model_name=row["model_name"],
                pricing_version=row["pricing_version"],
                enforced=bool(row["enforced"]),
                status=row["status"],
                reserved_input_tokens=row["reserved_input_tokens"],
                reserved_output_tokens=row["reserved_output_tokens"],
                reserved_cost_micro_usd=row["reserved_cost_micro_usd"],
                actual_input_tokens=row["actual_input_tokens"],
                actual_output_tokens=row["actual_output_tokens"],
                actual_cost_micro_usd=row["actual_cost_micro_usd"],
                usage_quality=row["usage_quality"],
                provider_response_count=row["provider_response_count"],
                prompt_chars=row["prompt_chars"],
                prompt_sha256=row["prompt_sha256"],
                schema_sha256=row["schema_sha256"],
                latency_ms=row["latency_ms"],
                error_code=row["error_code"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                lease_expires_at=row["lease_expires_at"],
            )
        except Exception as exc:
            raise ModelLedgerIntegrityError(
                "Model invocation row 无法通过 Schema"
            ) from exc
        return record

    @staticmethod
    def _load(
        connection: sqlite3.Connection,
        invocation_id: str,
    ) -> ModelInvocationRecord | None:
        row = connection.execute(
            "SELECT * FROM model_invocations WHERE invocation_id=?",
            (invocation_id,),
        ).fetchone()
        return None if row is None else SqliteModelLedger._record(row)

    @staticmethod
    def _usage_totals(
        connection: sqlite3.Connection,
        *,
        utc_date: str,
        job_id: str | None,
    ) -> tuple[int, int]:
        where = "substr(created_at, 1, 10)=?"
        params: list[str] = [utc_date]
        if job_id is not None:
            where += " AND job_id=?"
            params.append(job_id)

        row = connection.execute(
            f"""
            SELECT
              COALESCE(SUM(
                CASE
                  WHEN status='reserved'
                    THEN reserved_input_tokens + reserved_output_tokens
                  ELSE COALESCE(actual_input_tokens, 0)
                     + COALESCE(actual_output_tokens, 0)
                END
              ), 0) AS total_tokens,
              COALESCE(SUM(
                CASE
                  WHEN status='reserved'
                    THEN COALESCE(reserved_cost_micro_usd, 0)
                  ELSE COALESCE(actual_cost_micro_usd, 0)
                END
              ), 0) AS total_cost
            FROM model_invocations
            WHERE {where}
            """,
            tuple(params),
        ).fetchone()
        return int(row["total_tokens"]), int(row["total_cost"])

    @staticmethod
    def _check_limit(
        *,
        scope: str,
        limit: int | None,
        used_or_reserved: int,
        requested: int,
    ) -> None:
        if limit is None:
            return
        if used_or_reserved + requested > limit:
            raise ModelBudgetExceeded(
                scope=scope,
                limit=limit,
                used_or_reserved=used_or_reserved,
                requested=requested,
            )

    def reserve(
        self,
        request: ModelReservationRequest,
        *,
        now: datetime | None = None,
    ) -> ModelInvocationRecord:
        current_time = now or utc_now()
        created_at = iso_utc(current_time)
        utc_date = created_at[:10]

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._load(connection, request.invocation_id)
            if existing is not None:
                if (
                    existing.request_sha256 != request.request_sha256
                    or existing.decision_sha256 != request.decision_sha256
                ):
                    raise ModelLedgerConflict(
                        "同一 invocation_id 对应不同 request/decision"
                    )
                connection.commit()
                return existing

            if request.enforced:
                daily_tokens, daily_cost = self._usage_totals(
                    connection,
                    utc_date=utc_date,
                    job_id=None,
                )
                self._check_limit(
                    scope="daily_total_tokens",
                    limit=self.budget.daily_total_token_limit,
                    used_or_reserved=daily_tokens,
                    requested=request.reserved_total_tokens,
                )
                if request.reserved_cost_micro_usd is not None:
                    self._check_limit(
                        scope="daily_cost_micro_usd",
                        limit=self.budget.daily_cost_limit_micro_usd,
                        used_or_reserved=daily_cost,
                        requested=request.reserved_cost_micro_usd,
                    )

                if request.job_id is not None:
                    job_tokens, job_cost = self._usage_totals(
                        connection,
                        utc_date=utc_date,
                        job_id=request.job_id,
                    )
                    self._check_limit(
                        scope=f"job:{request.job_id}:total_tokens",
                        limit=self.budget.per_job_total_token_limit,
                        used_or_reserved=job_tokens,
                        requested=request.reserved_total_tokens,
                    )
                    if request.reserved_cost_micro_usd is not None:
                        self._check_limit(
                            scope=f"job:{request.job_id}:cost_micro_usd",
                            limit=self.budget.per_job_cost_limit_micro_usd,
                            used_or_reserved=job_cost,
                            requested=request.reserved_cost_micro_usd,
                        )

            connection.execute(
                """
                INSERT INTO model_invocations(
                  invocation_id, request_sha256, decision_sha256,
                  task_kind, job_id, run_id, node_name,
                  profile_id, model_name, pricing_version, enforced, status,
                  reserved_input_tokens, reserved_output_tokens,
                  reserved_cost_micro_usd,
                  prompt_chars, prompt_sha256, schema_sha256,
                  created_at, updated_at, lease_expires_at
                ) VALUES (
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'reserved',
                  ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    request.invocation_id,
                    request.request_sha256,
                    request.decision_sha256,
                    request.task_kind,
                    request.job_id,
                    request.run_id,
                    request.node_name,
                    request.profile_id,
                    request.model_name,
                    request.pricing_version,
                    int(request.enforced),
                    request.reserved_input_tokens,
                    request.reserved_output_tokens,
                    request.reserved_cost_micro_usd,
                    request.prompt_chars,
                    request.prompt_sha256,
                    request.schema_sha256,
                    created_at,
                    created_at,
                    request.lease_expires_at,
                ),
            )
            saved = self._load(connection, request.invocation_id)
            if saved is None:
                raise ModelLedgerIntegrityError("Reservation 写入后不可见")
            connection.commit()
            return saved
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def settle(
        self,
        *,
        invocation_id: str,
        status: str,
        usage: ModelUsage,
        latency_ms: int,
        error_code: str | None,
        now: datetime | None = None,
    ) -> ModelInvocationRecord:
        if status not in TERMINAL_STATUSES:
            raise ValueError("settle status 必须是终态")
        if error_code is not None and not ERROR_CODE_PATTERN.fullmatch(error_code):
            raise ValueError("error_code 格式无效")

        updated_at = iso_utc(now or utc_now())
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = self._load(connection, invocation_id)
            if current is None:
                raise ModelLedgerConflict("待结算 invocation 不存在")

            if current.status in TERMINAL_STATUSES:
                same = (
                    current.status == status
                    and current.actual_input_tokens == usage.input_tokens
                    and current.actual_output_tokens == usage.output_tokens
                    and current.actual_cost_micro_usd == usage.cost_micro_usd
                    and current.usage_quality == usage.quality
                    and current.provider_response_count
                    == usage.provider_response_count
                    and current.latency_ms == latency_ms
                    and current.error_code == error_code
                )
                if not same:
                    raise ModelLedgerConflict(
                        "Invocation 已按不同结果结算"
                    )
                connection.commit()
                return current

            if current.status != "reserved":
                raise ModelLedgerIntegrityError(
                    f"非法 invocation 状态：{current.status}"
                )

            connection.execute(
                """
                UPDATE model_invocations
                SET status=?, actual_input_tokens=?, actual_output_tokens=?,
                    actual_cost_micro_usd=?, usage_quality=?,
                    provider_response_count=?, latency_ms=?, error_code=?,
                    updated_at=?
                WHERE invocation_id=? AND status='reserved'
                """,
                (
                    status,
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.cost_micro_usd,
                    usage.quality,
                    usage.provider_response_count,
                    latency_ms,
                    error_code,
                    updated_at,
                    invocation_id,
                ),
            )
            if connection.total_changes != 1:
                raise ModelLedgerConflict("Invocation 结算 CAS 失败")
            saved = self._load(connection, invocation_id)
            if saved is None:
                raise ModelLedgerIntegrityError("结算后 Invocation 丢失")
            connection.commit()
            return saved
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def reconcile_stale(
        self,
        *,
        now: datetime | None = None,
        limit: int = 100,
    ) -> list[ModelInvocationRecord]:
        if limit < 1 or limit > 1000:
            raise ValueError("reconcile limit 必须为 1..1000")
        current_time = now or utc_now()
        current_iso = iso_utc(current_time)

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT invocation_id
                FROM model_invocations
                WHERE status='reserved' AND lease_expires_at < ?
                ORDER BY lease_expires_at, invocation_id
                LIMIT ?
                """,
                (current_iso, limit),
            ).fetchall()
            invocation_ids = [str(row["invocation_id"]) for row in rows]

            for invocation_id in invocation_ids:
                connection.execute(
                    """
                    UPDATE model_invocations
                    SET status='usage_unknown',
                        actual_input_tokens=reserved_input_tokens,
                        actual_output_tokens=reserved_output_tokens,
                        actual_cost_micro_usd=reserved_cost_micro_usd,
                        usage_quality='reservation_upper_bound',
                        provider_response_count=0,
                        latency_ms=0,
                        error_code='MODEL_RESERVATION_EXPIRED',
                        updated_at=?
                    WHERE invocation_id=? AND status='reserved'
                    """,
                    (current_iso, invocation_id),
                )

            records = []
            for invocation_id in invocation_ids:
                record = self._load(connection, invocation_id)
                if record is None:
                    raise ModelLedgerIntegrityError(
                        "Reconcile 后 Invocation 丢失"
                    )
                records.append(record)
            connection.commit()
            return records
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def summary(
        self,
        *,
        utc_date: str,
        job_id: str | None = None,
    ) -> ModelBudgetSummary:
        with self._connect() as connection:
            where = "substr(created_at, 1, 10)=?"
            params: list[str] = [utc_date]
            if job_id is not None:
                where += " AND job_id=?"
                params.append(job_id)
            row = connection.execute(
                f"""
                SELECT
                  COALESCE(SUM(CASE WHEN status!='reserved'
                    THEN COALESCE(actual_input_tokens, 0) ELSE 0 END), 0)
                    AS settled_input,
                  COALESCE(SUM(CASE WHEN status!='reserved'
                    THEN COALESCE(actual_output_tokens, 0) ELSE 0 END), 0)
                    AS settled_output,
                  COALESCE(SUM(CASE WHEN status='reserved'
                    THEN reserved_input_tokens + reserved_output_tokens
                    ELSE 0 END), 0) AS reserved_tokens,
                  COALESCE(SUM(CASE WHEN status!='reserved'
                    THEN COALESCE(actual_cost_micro_usd, 0) ELSE 0 END), 0)
                    AS settled_cost,
                  COALESCE(SUM(CASE WHEN status='reserved'
                    THEN COALESCE(reserved_cost_micro_usd, 0) ELSE 0 END), 0)
                    AS reserved_cost,
                  COUNT(*) AS invocation_count,
                  COALESCE(SUM(CASE WHEN status='reserved' THEN 1 ELSE 0 END), 0)
                    AS active_count,
                  COALESCE(SUM(CASE
                    WHEN reserved_cost_micro_usd IS NULL THEN 1 ELSE 0 END
                  ), 0) AS unpriced_count
                FROM model_invocations
                WHERE {where}
                """,
                tuple(params),
            ).fetchone()
        return ModelBudgetSummary(
            utc_date=utc_date,
            job_id=job_id,
            settled_input_tokens=int(row["settled_input"]),
            settled_output_tokens=int(row["settled_output"]),
            active_reserved_tokens=int(row["reserved_tokens"]),
            settled_cost_micro_usd=int(row["settled_cost"]),
            active_reserved_cost_micro_usd=int(row["reserved_cost"]),
            invocation_count=int(row["invocation_count"]),
            active_reservation_count=int(row["active_count"]),
            unpriced_invocation_count=int(row["unpriced_count"]),
        )

    def list_invocations(
        self,
        *,
        limit: int = 100,
        job_id: str | None = None,
    ) -> list[ModelInvocationRecord]:
        if limit < 1 or limit > 500:
            raise ValueError("limit 必须为 1..500")
        with self._connect() as connection:
            if job_id is None:
                rows = connection.execute(
                    """
                    SELECT * FROM model_invocations
                    ORDER BY created_at DESC, invocation_id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM model_invocations
                    WHERE job_id=?
                    ORDER BY created_at DESC, invocation_id DESC
                    LIMIT ?
                    """,
                    (job_id, limit),
                ).fetchall()
        return [self._record(row) for row in rows]
