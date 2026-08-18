from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from app.project_memory.errors import (
    ProjectFactNotFoundError,
    ProjectMemoryConflictError,
    ProjectMemoryIntegrityError,
    ProjectNotFoundError,
)
from app.project_memory.identity import (
    compute_fact_hash,
    validate_fact_hash,
    validate_project_hash,
)
from app.project_memory.schemas import (
    ChatUserMessageFactSource,
    ProjectFactCorrectionResponse,
    ProjectFactRecord,
    ProjectJobBinding,
    ProjectRecord,
)


class SqliteProjectMemoryRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    record_hash TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS project_job_bindings (
                    job_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    binding_json TEXT NOT NULL,
                    bound_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_project_bindings_project
                    ON project_job_bindings(project_id, bound_at);

                CREATE TABLE IF NOT EXISTS project_facts (
                    fact_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    category TEXT,
                    fact_key TEXT,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    expires_at TEXT,
                    source_job_id TEXT,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_project_facts_lookup
                    ON project_facts(project_id, status, category, fact_key);
                CREATE INDEX IF NOT EXISTS idx_project_facts_expiry
                    ON project_facts(project_id, status, expires_at);
                CREATE INDEX IF NOT EXISTS idx_project_facts_source_job
                    ON project_facts(source_job_id, status);

                CREATE TABLE IF NOT EXISTS project_memory_operations (
                    operation_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    response_kind TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    @staticmethod
    def _project(row: sqlite3.Row) -> ProjectRecord:
        try:
            record = ProjectRecord.model_validate_json(row["record_json"])
            validate_project_hash(record)
        except (ValidationError, ProjectMemoryIntegrityError) as exc:
            raise ProjectMemoryIntegrityError("Project row 损坏") from exc
        if (
            record.project_id != row["project_id"]
            or record.status != row["status"]
            or record.version != row["version"]
            or record.record_hash != row["record_hash"]
        ):
            raise ProjectMemoryIntegrityError("Project 索引列与 JSON 不一致")
        return record

    @staticmethod
    def _fact(row: sqlite3.Row) -> ProjectFactRecord:
        try:
            record = ProjectFactRecord.model_validate_json(row["record_json"])
            validate_fact_hash(record)
        except (ValidationError, ProjectMemoryIntegrityError) as exc:
            raise ProjectMemoryIntegrityError("Project fact row 损坏") from exc
        if (
            record.fact_id != row["fact_id"]
            or record.project_id != row["project_id"]
            or record.status != row["status"]
            or record.version != row["version"]
            or record.record_hash != row["record_hash"]
        ):
            raise ProjectMemoryIntegrityError("Fact 索引列与 JSON 不一致")
        return record

    @staticmethod
    def _source_job_id(fact: ProjectFactRecord) -> str | None:
        if isinstance(fact.source, ChatUserMessageFactSource):
            return fact.source.job_id
        return None

    @staticmethod
    def _fact_columns(fact: ProjectFactRecord) -> tuple:
        category = fact.content.category if fact.content is not None else None
        key = fact.content.key if fact.content is not None else None
        return (
            fact.project_id,
            category,
            key,
            fact.status,
            fact.version,
            fact.content_hash,
            fact.record_hash,
            fact.expires_at,
            SqliteProjectMemoryRepository._source_job_id(fact),
            fact.model_dump_json(),
            fact.created_at,
            fact.updated_at,
        )

    @staticmethod
    def _replay(
        connection: sqlite3.Connection,
        *,
        operation_key: str,
        request_hash: str,
        response_kind: str,
    ) -> dict | None:
        row = connection.execute(
            "SELECT * FROM project_memory_operations WHERE operation_key=?",
            (operation_key,),
        ).fetchone()
        if row is None:
            return None
        if row["request_hash"] != request_hash:
            raise ProjectMemoryConflictError(
                "同一 Idempotency-Key 对应不同 request payload"
            )
        if row["response_kind"] != response_kind:
            raise ProjectMemoryConflictError("幂等 operation kind 冲突")
        return json.loads(row["response_json"])

    @staticmethod
    def _save_operation(
        connection: sqlite3.Connection,
        *,
        operation_key: str,
        request_hash: str,
        response_kind: str,
        response: dict,
    ) -> None:
        connection.execute(
            """
            INSERT INTO project_memory_operations(
                operation_key, request_hash, response_kind, response_json
            ) VALUES (?, ?, ?, ?)
            """,
            (
                operation_key,
                request_hash,
                response_kind,
                json.dumps(response, ensure_ascii=False, separators=(",", ":")),
            ),
        )

    def get_project(self, project_id: str) -> ProjectRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE project_id=?",
                (project_id,),
            ).fetchone()
        if row is None:
            raise ProjectNotFoundError(f"未找到 project_id={project_id}")
        return self._project(row)

    def list_projects(
        self,
        *,
        include_archived: bool,
        limit: int,
    ) -> list[ProjectRecord]:
        bounded = max(1, min(limit, 500))
        query = "SELECT * FROM projects"
        parameters: tuple = ()
        if not include_archived:
            query += " WHERE status='active'"
        query += " ORDER BY created_at DESC, project_id DESC LIMIT ?"
        parameters += (bounded,)
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._project(row) for row in rows]

    def project_for_job(self, job_id: str) -> ProjectRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT p.* FROM projects AS p
                JOIN project_job_bindings AS b ON b.project_id=p.project_id
                WHERE b.job_id=?
                """,
                (job_id,),
            ).fetchone()
        return self._project(row) if row is not None else None

    def list_bindings(self, project_id: str) -> list[ProjectJobBinding]:
        # 先验证项目存在，避免把不存在和空集合混为一谈。
        self.get_project(project_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT binding_json FROM project_job_bindings
                WHERE project_id=? ORDER BY bound_at, job_id
                """,
                (project_id,),
            ).fetchall()
        return [
            ProjectJobBinding.model_validate_json(row["binding_json"])
            for row in rows
        ]

    def get_fact(self, fact_id: str) -> ProjectFactRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM project_facts WHERE fact_id=?",
                (fact_id,),
            ).fetchone()
        if row is None:
            raise ProjectFactNotFoundError(f"未找到 fact_id={fact_id}")
        return self._fact(row)

    def list_facts(
        self,
        *,
        project_id: str,
        include_terminal: bool,
        limit: int,
    ) -> list[ProjectFactRecord]:
        self.get_project(project_id)
        query = "SELECT * FROM project_facts WHERE project_id=?"
        params: list[object] = [project_id]
        if not include_terminal:
            query += " AND status IN ('proposed','confirmed')"
        query += " ORDER BY created_at DESC, fact_id DESC LIMIT ?"
        params.append(max(1, min(limit, 1000)))
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._fact(row) for row in rows]

    def active_facts(
        self,
        *,
        project_id: str,
        now: str,
        limit: int,
    ) -> list[ProjectFactRecord]:
        project = self.get_project(project_id)
        if project.status != "active":
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM project_facts
                WHERE project_id=?
                  AND status='confirmed'
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY category, fact_key, created_at DESC, fact_id DESC
                LIMIT ?
                """,
                (project_id, now, max(1, min(limit, 500))),
            ).fetchall()
        return [self._fact(row) for row in rows]

    def active_referenced_job_ids(self) -> set[str]:
        # 读取时再次检查 expires_at，避免 sweep 延迟导致无意义永久 hold。
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT f.source_job_id
                FROM project_facts AS f
                JOIN projects AS p ON p.project_id=f.project_id
                WHERE f.source_job_id IS NOT NULL
                  AND f.status='confirmed'
                  AND p.status='active'
                  AND (f.expires_at IS NULL OR f.expires_at > ?)
                """,
                (now,),
            ).fetchall()
        return {str(row[0]) for row in rows}

    def create_project(
        self,
        *,
        project: ProjectRecord,
        anchor_binding: ProjectJobBinding,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectRecord, bool]:
        validate_project_hash(project)
        if anchor_binding.project_id != project.project_id:
            raise ProjectMemoryConflictError("Anchor binding project_id 不一致")
        if anchor_binding.job_id != project.anchor.job_id:
            raise ProjectMemoryConflictError("Anchor binding job_id 不一致")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="project",
            )
            if replay is not None:
                return ProjectRecord.model_validate(replay["project"]), True

            connection.execute(
                """
                INSERT INTO projects(
                  project_id, status, version, record_hash,
                  record_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    project.status,
                    project.version,
                    project.record_hash,
                    project.model_dump_json(),
                    project.created_at,
                    project.updated_at,
                ),
            )
            try:
                connection.execute(
                    """
                    INSERT INTO project_job_bindings(
                      job_id, project_id, binding_json, bound_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        anchor_binding.job_id,
                        anchor_binding.project_id,
                        anchor_binding.model_dump_json(),
                        anchor_binding.bound_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ProjectMemoryConflictError(
                    "Job 已绑定某个 Project"
                ) from exc
            self._save_operation(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="project",
                response={"project": project.model_dump(mode="json")},
            )
            connection.commit()
        return project, False

    def archive_project(
        self,
        *,
        project: ProjectRecord,
        expected_version: int,
        expected_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectRecord, bool]:
        validate_project_hash(project)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="project",
            )
            if replay is not None:
                return ProjectRecord.model_validate(replay["project"]), True
            row = connection.execute(
                "SELECT * FROM projects WHERE project_id=?",
                (project.project_id,),
            ).fetchone()
            if row is None:
                raise ProjectNotFoundError(
                    f"未找到 project_id={project.project_id}"
                )
            current = self._project(row)
            if (
                current.version != expected_version
                or current.record_hash != expected_hash
            ):
                raise ProjectMemoryConflictError("Project version/hash 已变化")
            if current.status != "active" or project.status != "archived":
                raise ProjectMemoryConflictError("Project archive 状态迁移非法")
            if project.version != current.version + 1:
                raise ProjectMemoryConflictError("Project version 没有递增")

            changed = connection.execute(
                """
                UPDATE projects SET
                  status=?, version=?, record_hash=?, record_json=?, updated_at=?
                WHERE project_id=? AND version=? AND record_hash=?
                """,
                (
                    project.status,
                    project.version,
                    project.record_hash,
                    project.model_dump_json(),
                    project.updated_at,
                    project.project_id,
                    expected_version,
                    expected_hash,
                ),
            ).rowcount
            if changed != 1:
                raise ProjectMemoryConflictError("Project archive CAS 失败")
            self._save_operation(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="project",
                response={"project": project.model_dump(mode="json")},
            )
            connection.commit()
        return project, False

    def bind_job(
        self,
        *,
        binding: ProjectJobBinding,
        expected_project_version: int,
        expected_project_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectJobBinding, bool]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="binding",
            )
            if replay is not None:
                return ProjectJobBinding.model_validate(replay["binding"]), True
            row = connection.execute(
                "SELECT * FROM projects WHERE project_id=?",
                (binding.project_id,),
            ).fetchone()
            if row is None:
                raise ProjectNotFoundError(
                    f"未找到 project_id={binding.project_id}"
                )
            project = self._project(row)
            if (
                project.version != expected_project_version
                or project.record_hash != expected_project_hash
            ):
                raise ProjectMemoryConflictError("Project version/hash 已变化")
            if project.status != "active":
                raise ProjectMemoryConflictError("Archived Project 不能绑定 Job")
            try:
                connection.execute(
                    """
                    INSERT INTO project_job_bindings(
                      job_id, project_id, binding_json, bound_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        binding.job_id,
                        binding.project_id,
                        binding.model_dump_json(),
                        binding.bound_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ProjectMemoryConflictError(
                    "Job 已绑定某个 Project"
                ) from exc
            self._save_operation(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="binding",
                response={"binding": binding.model_dump(mode="json")},
            )
            connection.commit()
        return binding, False

    def create_fact(
        self,
        *,
        fact: ProjectFactRecord,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectFactRecord, bool]:
        validate_fact_hash(fact)
        if fact.status != "proposed":
            raise ProjectMemoryConflictError("create_fact 只能写 proposed")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="fact",
            )
            if replay is not None:
                return ProjectFactRecord.model_validate(replay["fact"]), True
            project_row = connection.execute(
                "SELECT * FROM projects WHERE project_id=?",
                (fact.project_id,),
            ).fetchone()
            if project_row is None:
                raise ProjectNotFoundError(
                    f"未找到 project_id={fact.project_id}"
                )
            if self._project(project_row).status != "active":
                raise ProjectMemoryConflictError("Archived Project 不能新增 Fact")
            connection.execute(
                """
                INSERT INTO project_facts(
                  fact_id, project_id, category, fact_key, status, version,
                  content_hash, record_hash, expires_at, source_job_id,
                  record_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fact.fact_id, *self._fact_columns(fact)),
            )
            self._save_operation(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="fact",
                response={"fact": fact.model_dump(mode="json")},
            )
            connection.commit()
        return fact, False

    def replace_fact(
        self,
        *,
        fact: ProjectFactRecord,
        expected_version: int,
        expected_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> tuple[ProjectFactRecord, bool]:
        validate_fact_hash(fact)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="fact",
            )
            if replay is not None:
                return ProjectFactRecord.model_validate(replay["fact"]), True
            row = connection.execute(
                "SELECT * FROM project_facts WHERE fact_id=?",
                (fact.fact_id,),
            ).fetchone()
            if row is None:
                raise ProjectFactNotFoundError(
                    f"未找到 fact_id={fact.fact_id}"
                )
            current = self._fact(row)
            if (
                current.version != expected_version
                or current.record_hash != expected_hash
            ):
                raise ProjectMemoryConflictError("Project Fact version/hash 已变化")
            if fact.version != current.version + 1:
                raise ProjectMemoryConflictError("Project Fact version 没有递增")
            if (
                fact.project_id != current.project_id
                or fact.created_at != current.created_at
                or fact.source != current.source
                or fact.content_hash != current.content_hash
            ):
                raise ProjectMemoryConflictError("Fact immutable identity 被修改")

            if fact.status == "confirmed" and fact.content is not None:
                conflict = connection.execute(
                    """
                    SELECT fact_id FROM project_facts
                    WHERE project_id=? AND category=? AND fact_key=?
                      AND status='confirmed'
                      AND (expires_at IS NULL OR expires_at > ?)
                      AND fact_id<>?
                    LIMIT 1
                    """,
                    (
                        fact.project_id,
                        fact.content.category,
                        fact.content.key,
                        fact.updated_at,
                        fact.fact_id,
                    ),
                ).fetchone()
                if conflict is not None:
                    raise ProjectMemoryConflictError(
                        "slot 已有 active fact；请使用 correct"
                    )

            columns = self._fact_columns(fact)
            changed = connection.execute(
                """
                UPDATE project_facts SET
                  project_id=?, category=?, fact_key=?, status=?, version=?,
                  content_hash=?, record_hash=?, expires_at=?, source_job_id=?,
                  record_json=?, created_at=?, updated_at=?
                WHERE fact_id=? AND version=? AND record_hash=?
                """,
                (*columns, fact.fact_id, expected_version, expected_hash),
            ).rowcount
            if changed != 1:
                raise ProjectMemoryConflictError("Project Fact CAS 失败")
            self._save_operation(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="fact",
                response={"fact": fact.model_dump(mode="json")},
            )
            connection.commit()
        return fact, False

    def replace_with_successor(
        self,
        *,
        previous: ProjectFactRecord,
        successor: ProjectFactRecord,
        expected_version: int,
        expected_hash: str,
        operation_key: str,
        request_hash: str,
    ) -> ProjectFactCorrectionResponse:
        validate_fact_hash(previous)
        validate_fact_hash(successor)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="fact_correction",
            )
            if replay is not None:
                return ProjectFactCorrectionResponse.model_validate(
                    {**replay, "replayed": True}
                )
            row = connection.execute(
                "SELECT * FROM project_facts WHERE fact_id=?",
                (previous.fact_id,),
            ).fetchone()
            if row is None:
                raise ProjectFactNotFoundError(
                    f"未找到 fact_id={previous.fact_id}"
                )
            current = self._fact(row)
            if (
                current.version != expected_version
                or current.record_hash != expected_hash
            ):
                raise ProjectMemoryConflictError("Project Fact version/hash 已变化")
            if current.status != "confirmed":
                raise ProjectMemoryConflictError("只有 confirmed fact 可以 correct")
            if (
                previous.status != "superseded"
                or previous.version != current.version + 1
                or previous.superseded_by_fact_id != successor.fact_id
                or previous.source != current.source
                or previous.created_at != current.created_at
                or previous.content_hash != current.content_hash
                or successor.supersedes_fact_id != current.fact_id
                or successor.supersedes_record_hash != current.record_hash
                or successor.project_id != current.project_id
            ):
                raise ProjectMemoryConflictError("Correction revision identity 不一致")
            if current.content is None or successor.content is None:
                raise ProjectMemoryConflictError("Correction 缺少内容")
            if (
                successor.content.category != current.content.category
                or successor.content.key != current.content.key
            ):
                raise ProjectMemoryConflictError("Correction 不能改变 slot")

            conflict = connection.execute(
                """
                SELECT fact_id FROM project_facts
                WHERE project_id=? AND category=? AND fact_key=?
                  AND status='confirmed'
                  AND (expires_at IS NULL OR expires_at > ?)
                  AND fact_id<>?
                LIMIT 1
                """,
                (
                    current.project_id,
                    current.content.category,
                    current.content.key,
                    successor.created_at,
                    current.fact_id,
                ),
            ).fetchone()
            if conflict is not None:
                raise ProjectMemoryConflictError("slot 存在另一个 active fact")

            changed = connection.execute(
                """
                UPDATE project_facts SET
                  project_id=?, category=?, fact_key=?, status=?, version=?,
                  content_hash=?, record_hash=?, expires_at=?, source_job_id=?,
                  record_json=?, created_at=?, updated_at=?
                WHERE fact_id=? AND version=? AND record_hash=?
                """,
                (
                    *self._fact_columns(previous),
                    current.fact_id,
                    expected_version,
                    expected_hash,
                ),
            ).rowcount
            if changed != 1:
                raise ProjectMemoryConflictError("Correction previous CAS 失败")
            connection.execute(
                """
                INSERT INTO project_facts(
                  fact_id, project_id, category, fact_key, status, version,
                  content_hash, record_hash, expires_at, source_job_id,
                  record_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (successor.fact_id, *self._fact_columns(successor)),
            )
            response = ProjectFactCorrectionResponse(
                previous=previous,
                successor=successor,
                replayed=False,
            )
            self._save_operation(
                connection,
                operation_key=operation_key,
                request_hash=request_hash,
                response_kind="fact_correction",
                response=response.model_dump(mode="json"),
            )
            connection.commit()
        return response

    def expire_due(self, *, project_id: str, now: str, actor: str) -> int:
        changed = 0
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT * FROM project_facts
                WHERE project_id=? AND status IN ('proposed','confirmed')
                  AND expires_at IS NOT NULL AND expires_at <= ?
                ORDER BY fact_id
                """,
                (project_id, now),
            ).fetchall()
            for row in rows:
                current = self._fact(row)
                raw = current.model_dump(mode="json")
                raw.update(
                    {
                        "version": current.version + 1,
                        "status": "expired",
                        "terminal_event": {
                            "status": "expired",
                            "actor": actor,
                            "reason": "expires_at reached",
                            "occurred_at": now,
                        },
                        "updated_at": now,
                        "record_hash": "0" * 64,
                    }
                )
                draft = ProjectFactRecord.model_validate(raw)
                raw["record_hash"] = compute_fact_hash(draft)
                expired = ProjectFactRecord.model_validate(raw)
                columns = self._fact_columns(expired)
                updated = connection.execute(
                    """
                    UPDATE project_facts SET
                      project_id=?, category=?, fact_key=?, status=?, version=?,
                      content_hash=?, record_hash=?, expires_at=?, source_job_id=?,
                      record_json=?, created_at=?, updated_at=?
                    WHERE fact_id=? AND version=? AND record_hash=?
                    """,
                    (
                        *columns,
                        current.fact_id,
                        current.version,
                        current.record_hash,
                    ),
                ).rowcount
                changed += updated
            connection.commit()
        return changed
