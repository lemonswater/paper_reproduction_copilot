from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from app.knowledge_base.errors import (
    KnowledgeConflictError,
    KnowledgeIntegrityError,
    KnowledgeNotFoundError,
    KnowledgeStaleReviewError,
)
from app.knowledge_base.identity import (
    graph_batch_hash,
    utc_now,
    validate_entity_hash,
    validate_provenance_hash,
    validate_relation_hash,
    validate_snapshot_hash,
)
from app.knowledge_base.schemas import (
    KnowledgeEntityKind,
    KnowledgeEntityRecord,
    KnowledgeGraphBatch,
    KnowledgeIngestionRecord,
    KnowledgeProvenanceRecord,
    KnowledgeRelationRecord,
)


class SqliteKnowledgeRepository:
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
                CREATE TABLE IF NOT EXISTS knowledge_entities (
                    entity_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    canonical_key TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_kg_entity_search
                    ON knowledge_entities(kind, canonical_key, display_name);

                CREATE TABLE IF NOT EXISTS knowledge_relations (
                    relation_id TEXT PRIMARY KEY,
                    relation_type TEXT NOT NULL,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    relation_hash TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(source_entity_id)
                        REFERENCES knowledge_entities(entity_id),
                    FOREIGN KEY(target_entity_id)
                        REFERENCES knowledge_entities(entity_id)
                );
                CREATE INDEX IF NOT EXISTS idx_kg_relation_source
                    ON knowledge_relations(source_entity_id, status);
                CREATE INDEX IF NOT EXISTS idx_kg_relation_target
                    ON knowledge_relations(target_entity_id, status);
                CREATE INDEX IF NOT EXISTS idx_kg_relation_status
                    ON knowledge_relations(status, relation_type);

                CREATE TABLE IF NOT EXISTS knowledge_ingestions (
                    ingestion_id TEXT PRIMARY KEY,
                    source_snapshot_id TEXT NOT NULL UNIQUE,
                    source_snapshot_hash TEXT NOT NULL UNIQUE,
                    source_job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    batch_hash TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_kg_ingestion_job
                    ON knowledge_ingestions(source_job_id, status);

                CREATE TABLE IF NOT EXISTS knowledge_provenance (
                    provenance_id TEXT PRIMARY KEY,
                    subject_kind TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    source_snapshot_id TEXT NOT NULL,
                    provenance_hash TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_snapshot_id)
                        REFERENCES knowledge_ingestions(source_snapshot_id)
                );
                CREATE INDEX IF NOT EXISTS idx_kg_provenance_subject
                    ON knowledge_provenance(subject_id, source_snapshot_id);

                CREATE TABLE IF NOT EXISTS knowledge_operations (
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
    def _entity(row: sqlite3.Row) -> KnowledgeEntityRecord:
        try:
            record = KnowledgeEntityRecord.model_validate_json(
                row["record_json"]
            )
            validate_entity_hash(record)
        except (ValidationError, ValueError) as exc:
            raise KnowledgeIntegrityError("Knowledge Entity row 损坏") from exc
        if (
            record.entity_id != row["entity_id"]
            or record.kind != row["kind"]
            or record.scope_key != row["scope_key"]
            or record.canonical_key != row["canonical_key"]
            or record.record_hash != row["record_hash"]
        ):
            raise KnowledgeIntegrityError(
                "Knowledge Entity 索引列与 JSON 不一致"
            )
        return record

    @staticmethod
    def _relation(row: sqlite3.Row) -> KnowledgeRelationRecord:
        try:
            record = KnowledgeRelationRecord.model_validate_json(
                row["record_json"]
            )
            validate_relation_hash(record)
        except (ValidationError, ValueError) as exc:
            raise KnowledgeIntegrityError("Knowledge Relation row 损坏") from exc
        if (
            record.relation_id != row["relation_id"]
            or record.status != row["status"]
            or record.version != row["version"]
            or record.relation_hash != row["relation_hash"]
        ):
            raise KnowledgeIntegrityError(
                "Knowledge Relation 索引列与 JSON 不一致"
            )
        return record

    @staticmethod
    def _provenance(row: sqlite3.Row) -> KnowledgeProvenanceRecord:
        try:
            record = KnowledgeProvenanceRecord.model_validate_json(
                row["record_json"]
            )
            validate_provenance_hash(record)
        except (ValidationError, ValueError) as exc:
            raise KnowledgeIntegrityError("Knowledge Provenance row 损坏") from exc
        if (
            record.provenance_id != row["provenance_id"]
            or record.subject_id != row["subject_id"]
            or record.source_snapshot_id != row["source_snapshot_id"]
            or record.provenance_hash != row["provenance_hash"]
        ):
            raise KnowledgeIntegrityError(
                "Knowledge Provenance 索引列与 JSON 不一致"
            )
        return record

    @staticmethod
    def _ingestion(row: sqlite3.Row) -> KnowledgeIngestionRecord:
        try:
            record = KnowledgeIngestionRecord.model_validate_json(
                row["record_json"]
            )
            validate_snapshot_hash(record.source)
        except (ValidationError, ValueError) as exc:
            raise KnowledgeIntegrityError("Knowledge Ingestion row 损坏") from exc
        if (
            record.ingestion_id != row["ingestion_id"]
            or record.source.snapshot_id != row["source_snapshot_id"]
            or record.source.snapshot_hash != row["source_snapshot_hash"]
            or record.status != row["status"]
            or record.batch_hash != row["batch_hash"]
            or record.request_hash != row["request_hash"]
        ):
            raise KnowledgeIntegrityError(
                "Knowledge Ingestion 索引列与 JSON 不一致"
            )
        return record

    @staticmethod
    def _replay(
        connection: sqlite3.Connection,
        *,
        operation_key: str,
        request_hash: str,
        response_kind: str,
    ) -> dict | None:
        row = connection.execute(
            "SELECT * FROM knowledge_operations WHERE operation_key=?",
            (operation_key,),
        ).fetchone()
        if row is None:
            return None
        if row["request_hash"] != request_hash:
            raise KnowledgeConflictError(
                "同一 Idempotency-Key 对应不同 Knowledge request"
            )
        if row["response_kind"] != response_kind:
            raise KnowledgeConflictError("Knowledge operation kind 冲突")
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
            INSERT INTO knowledge_operations(
              operation_key, request_hash, response_kind, response_json
            ) VALUES (?, ?, ?, ?)
            """,
            (
                operation_key,
                request_hash,
                response_kind,
                json.dumps(
                    response,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ),
        )

    @staticmethod
    def _insert_entity(
        connection: sqlite3.Connection,
        record: KnowledgeEntityRecord,
    ) -> bool:
        row = connection.execute(
            "SELECT * FROM knowledge_entities WHERE entity_id=?",
            (record.entity_id,),
        ).fetchone()
        if row is not None:
            current = SqliteKnowledgeRepository._entity(row)
            if current.record_hash != record.record_hash:
                raise KnowledgeConflictError(
                    f"Entity identity collision：{record.entity_id}"
                )
            return False
        connection.execute(
            """
            INSERT INTO knowledge_entities(
              entity_id, kind, scope_key, canonical_key, display_name,
              record_hash, record_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.entity_id,
                record.kind,
                record.scope_key,
                record.canonical_key,
                record.display_name,
                record.record_hash,
                record.model_dump_json(),
                record.created_at,
            ),
        )
        return True

    @staticmethod
    def _insert_relation(
        connection: sqlite3.Connection,
        record: KnowledgeRelationRecord,
    ) -> bool:
        row = connection.execute(
            "SELECT * FROM knowledge_relations WHERE relation_id=?",
            (record.relation_id,),
        ).fetchone()
        if row is not None:
            current = SqliteKnowledgeRepository._relation(row)
            same_identity = (
                current.relation_type == record.relation_type
                and current.source_entity_id == record.source_entity_id
                and current.target_entity_id == record.target_entity_id
            )
            if not same_identity:
                raise KnowledgeConflictError(
                    f"Relation identity collision：{record.relation_id}"
                )
            # 新 Snapshot 重新观察到旧 candidate 时，保留人工生命周期
            # 状态，只在后续插入新的 Provenance，绝不降级 confirmed。
            if record.status == "candidate":
                return False
            if current.relation_hash != record.relation_hash:
                raise KnowledgeConflictError(
                    f"Asserted Relation 内容冲突：{record.relation_id}"
                )
            return False
        connection.execute(
            """
            INSERT INTO knowledge_relations(
              relation_id, relation_type, source_entity_id,
              target_entity_id, status, version, relation_hash,
              record_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.relation_id,
                record.relation_type,
                record.source_entity_id,
                record.target_entity_id,
                record.status,
                record.version,
                record.relation_hash,
                record.model_dump_json(),
                record.updated_at,
            ),
        )
        return True

    @staticmethod
    def _insert_provenance(
        connection: sqlite3.Connection,
        record: KnowledgeProvenanceRecord,
    ) -> bool:
        row = connection.execute(
            "SELECT * FROM knowledge_provenance WHERE provenance_id=?",
            (record.provenance_id,),
        ).fetchone()
        if row is not None:
            current = SqliteKnowledgeRepository._provenance(row)
            if current.provenance_hash != record.provenance_hash:
                raise KnowledgeConflictError(
                    f"Provenance identity collision：{record.provenance_id}"
                )
            return False
        connection.execute(
            """
            INSERT INTO knowledge_provenance(
              provenance_id, subject_kind, subject_id,
              source_snapshot_id, provenance_hash, record_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.provenance_id,
                record.subject_kind,
                record.subject_id,
                record.source_snapshot_id,
                record.provenance_hash,
                record.model_dump_json(),
                record.created_at,
            ),
        )
        return True

    @staticmethod
    def _validate_batch(batch: KnowledgeGraphBatch) -> None:
        validate_snapshot_hash(batch.source)
        entity_ids = [item.entity_id for item in batch.entities]
        relation_ids = [item.relation_id for item in batch.relations]
        provenance_ids = [item.provenance_id for item in batch.provenance]
        if len(entity_ids) != len(set(entity_ids)):
            raise KnowledgeConflictError("Batch Entity ID 重复")
        if len(relation_ids) != len(set(relation_ids)):
            raise KnowledgeConflictError("Batch Relation ID 重复")
        if len(provenance_ids) != len(set(provenance_ids)):
            raise KnowledgeConflictError("Batch Provenance ID 重复")

        subjects = set(entity_ids) | set(relation_ids)
        proven_subjects: set[str] = set()
        for entity in batch.entities:
            validate_entity_hash(entity)
        for relation in batch.relations:
            validate_relation_hash(relation)
            if (
                relation.source_entity_id not in entity_ids
                or relation.target_entity_id not in entity_ids
            ):
                raise KnowledgeConflictError(
                    "Batch Relation endpoint 不在当前 Entity 集合"
                )
        for item in batch.provenance:
            validate_provenance_hash(item)
            if item.source_snapshot_id != batch.source.snapshot_id:
                raise KnowledgeConflictError(
                    "Batch Provenance snapshot identity 不一致"
                )
            if item.subject_id not in subjects:
                raise KnowledgeConflictError(
                    "Batch Provenance 引用了未知 Subject"
                )
            proven_subjects.add(item.subject_id)
        if subjects != proven_subjects:
            raise KnowledgeConflictError(
                "Batch 中每个 Entity/Relation 都必须至少有一个 Provenance"
            )

    def ingest_batch(
        self,
        *,
        batch: KnowledgeGraphBatch,
        ingestion: KnowledgeIngestionRecord,
        idempotency_key: str,
    ) -> tuple[KnowledgeIngestionRecord, bool]:
        self._validate_batch(batch)
        if ingestion.source != batch.source or ingestion.status != "active":
            raise KnowledgeConflictError("Ingestion 与 Batch source/status 不一致")
        if ingestion.batch_hash != graph_batch_hash(batch):
            raise KnowledgeConflictError("Ingestion batch_hash 不一致")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=idempotency_key,
                request_hash=ingestion.request_hash,
                response_kind="ingestion",
            )
            if replay is not None:
                return (
                    KnowledgeIngestionRecord.model_validate(
                        replay["ingestion"]
                    ),
                    True,
                )

            existing = connection.execute(
                """
                SELECT * FROM knowledge_ingestions
                WHERE source_snapshot_hash=?
                """,
                (batch.source.snapshot_hash,),
            ).fetchone()
            if existing is not None:
                current = self._ingestion(existing)
                if current.batch_hash != ingestion.batch_hash:
                    raise KnowledgeConflictError(
                        "同一 Source Snapshot 对应不同 Graph Batch"
                    )
                self._save_operation(
                    connection,
                    operation_key=idempotency_key,
                    request_hash=ingestion.request_hash,
                    response_kind="ingestion",
                    response={"ingestion": current.model_dump(mode="json")},
                )
                connection.commit()
                return current, True

            created_entities = sum(
                self._insert_entity(connection, item)
                for item in batch.entities
            )
            created_relations = sum(
                self._insert_relation(connection, item)
                for item in batch.relations
            )
            final_record = ingestion.model_copy(
                update={
                    "entity_count": len(batch.entities),
                    "relation_count": len(batch.relations),
                    "created_entity_count": created_entities,
                    "created_relation_count": created_relations,
                }
            )
            connection.execute(
                """
                INSERT INTO knowledge_ingestions(
                  ingestion_id, source_snapshot_id, source_snapshot_hash,
                  source_job_id, status, batch_hash, request_hash,
                  record_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    final_record.ingestion_id,
                    final_record.source.snapshot_id,
                    final_record.source.snapshot_hash,
                    final_record.source.job_id,
                    final_record.status,
                    final_record.batch_hash,
                    final_record.request_hash,
                    final_record.model_dump_json(),
                    final_record.created_at,
                ),
            )
            for item in batch.provenance:
                self._insert_provenance(connection, item)
            self._save_operation(
                connection,
                operation_key=idempotency_key,
                request_hash=ingestion.request_hash,
                response_kind="ingestion",
                response={
                    "ingestion": final_record.model_dump(mode="json")
                },
            )
            connection.commit()
        return final_record, False

    def get_entity(self, entity_id: str) -> KnowledgeEntityRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_entities WHERE entity_id=?",
                (entity_id,),
            ).fetchone()
        if row is None:
            raise KnowledgeNotFoundError(f"未找到 entity_id={entity_id}")
        return self._entity(row)

    def get_relation(self, relation_id: str) -> KnowledgeRelationRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_relations WHERE relation_id=?",
                (relation_id,),
            ).fetchone()
        if row is None:
            raise KnowledgeNotFoundError(f"未找到 relation_id={relation_id}")
        return self._relation(row)

    def get_ingestion(self, ingestion_id: str) -> KnowledgeIngestionRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_ingestions WHERE ingestion_id=?",
                (ingestion_id,),
            ).fetchone()
        if row is None:
            raise KnowledgeNotFoundError(
                f"未找到 ingestion_id={ingestion_id}"
            )
        return self._ingestion(row)

    def list_candidate_relations(
        self,
        *,
        limit: int,
    ) -> list[KnowledgeRelationRecord]:
        bounded = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT r.* FROM knowledge_relations AS r
                JOIN knowledge_provenance AS p
                  ON p.subject_id=r.relation_id
                JOIN knowledge_ingestions AS i
                  ON i.source_snapshot_id=p.source_snapshot_id
                WHERE r.status='candidate' AND i.status='active'
                ORDER BY r.updated_at DESC, r.relation_id
                LIMIT ?
                """,
                (bounded,),
            ).fetchall()
        return [self._relation(row) for row in rows]

    def search_entities(
        self,
        *,
        terms: list[str],
        kinds: list[KnowledgeEntityKind],
        limit: int,
    ) -> list[KnowledgeEntityRecord]:
        bounded = max(1, min(limit, 500))
        clauses = ["i.status='active'"]
        parameters: list[object] = []
        if kinds:
            placeholders = ",".join("?" for _ in kinds)
            clauses.append(f"e.kind IN ({placeholders})")
            parameters.extend(kinds)
        if terms:
            term_clauses: list[str] = []
            for term in terms[:16]:
                term_clauses.append(
                    "(e.canonical_key LIKE ? ESCAPE '\\' "
                    "OR e.display_name LIKE ? ESCAPE '\\')"
                )
                escaped = (
                    term.replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                )
                pattern = f"%{escaped}%"
                parameters.extend([pattern, pattern])
            clauses.append("(" + " OR ".join(term_clauses) + ")")
        parameters.append(bounded)
        query = f"""
            SELECT DISTINCT e.* FROM knowledge_entities AS e
            JOIN knowledge_provenance AS p ON p.subject_id=e.entity_id
            JOIN knowledge_ingestions AS i
              ON i.source_snapshot_id=p.source_snapshot_id
            WHERE {' AND '.join(clauses)}
            ORDER BY e.kind, e.canonical_key, e.entity_id
            LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._entity(row) for row in rows]

    def relations_for_entities(
        self,
        *,
        entity_ids: list[str],
        include_candidates: bool,
        limit: int,
    ) -> list[KnowledgeRelationRecord]:
        ids = sorted(set(entity_ids))[:500]
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        statuses = ["asserted", "confirmed"]
        if include_candidates:
            statuses.append("candidate")
        status_marks = ",".join("?" for _ in statuses)
        parameters: list[object] = [*ids, *ids, *statuses]
        parameters.append(max(1, min(limit, 1000)))
        query = f"""
            SELECT DISTINCT r.* FROM knowledge_relations AS r
            JOIN knowledge_provenance AS p ON p.subject_id=r.relation_id
            JOIN knowledge_ingestions AS i
              ON i.source_snapshot_id=p.source_snapshot_id
            WHERE (
              r.source_entity_id IN ({placeholders})
              OR r.target_entity_id IN ({placeholders})
            )
              AND r.status IN ({status_marks})
              AND i.status='active'
            ORDER BY r.relation_type, r.relation_id
            LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._relation(row) for row in rows]

    def active_entities_by_ids(
        self,
        *,
        entity_ids: list[str],
        limit: int,
    ) -> list[KnowledgeEntityRecord]:
        ids = sorted(set(entity_ids))[:1000]
        if not ids:
            return []
        marks = ",".join("?" for _ in ids)
        parameters: list[object] = [
            *ids,
            max(1, min(limit, 1000)),
        ]
        query = f"""
            SELECT DISTINCT e.* FROM knowledge_entities AS e
            JOIN knowledge_provenance AS p ON p.subject_id=e.entity_id
            JOIN knowledge_ingestions AS i
              ON i.source_snapshot_id=p.source_snapshot_id
            WHERE e.entity_id IN ({marks}) AND i.status='active'
            ORDER BY e.entity_id
            LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._entity(row) for row in rows]

    def provenance_for_subjects(
        self,
        *,
        subject_ids: list[str],
        limit: int,
    ) -> list[KnowledgeProvenanceRecord]:
        ids = sorted(set(subject_ids))[:1000]
        if not ids:
            return []
        marks = ",".join("?" for _ in ids)
        parameters: list[object] = [*ids, max(1, min(limit, 5000))]
        query = f"""
            SELECT p.* FROM knowledge_provenance AS p
            JOIN knowledge_ingestions AS i
              ON i.source_snapshot_id=p.source_snapshot_id
            WHERE p.subject_id IN ({marks}) AND i.status='active'
            ORDER BY p.subject_id, p.provenance_id
            LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._provenance(row) for row in rows]

    def create_candidate_relation(
        self,
        *,
        relation: KnowledgeRelationRecord,
        provenance: list[KnowledgeProvenanceRecord],
        expected_entity_hashes: dict[str, str],
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[KnowledgeRelationRecord, bool]:
        validate_relation_hash(relation)
        if relation.status != "candidate":
            raise KnowledgeConflictError("只能通过该接口创建 candidate")
        endpoint_ids = {
            relation.source_entity_id,
            relation.target_entity_id,
        }
        if set(expected_entity_hashes) != endpoint_ids:
            raise KnowledgeConflictError("Expected Entity Hash 集合不完整")
        if not provenance:
            raise KnowledgeConflictError("Candidate 必须有 Provenance")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=idempotency_key,
                request_hash=request_hash,
                response_kind="relation",
            )
            if replay is not None:
                return (
                    KnowledgeRelationRecord.model_validate(
                        replay["relation"]
                    ),
                    True,
                )
            for entity_id, expected_hash in expected_entity_hashes.items():
                row = connection.execute(
                    "SELECT * FROM knowledge_entities WHERE entity_id=?",
                    (entity_id,),
                ).fetchone()
                if row is None:
                    raise KnowledgeNotFoundError(
                        f"未找到 entity_id={entity_id}"
                    )
                if self._entity(row).record_hash != expected_hash:
                    raise KnowledgeStaleReviewError(
                        f"Entity 已变化：{entity_id}"
                    )
            marks = ",".join("?" for _ in endpoint_ids)
            support_rows = connection.execute(
                f"""
                SELECT p.* FROM knowledge_provenance AS p
                JOIN knowledge_ingestions AS i
                  ON i.source_snapshot_id=p.source_snapshot_id
                WHERE p.subject_id IN ({marks}) AND i.status='active'
                """,
                tuple(sorted(endpoint_ids)),
            ).fetchall()
            support: dict[tuple[str, str], set[str]] = {}
            for row in support_rows:
                item = self._provenance(row)
                support.setdefault(
                    (item.source_snapshot_id, item.subject_id),
                    set(),
                ).update(
                    ref.evidence_ref_id for ref in item.evidence
                )
            covered_endpoints: set[str] = set()
            for item in provenance:
                validate_provenance_hash(item)
                if item.subject_id != relation.relation_id:
                    raise KnowledgeConflictError(
                        "Candidate Provenance subject 不一致"
                    )
                candidate_refs = {
                    ref.evidence_ref_id for ref in item.evidence
                }
                matches = {
                    endpoint_id
                    for endpoint_id in endpoint_ids
                    if candidate_refs
                    <= support.get(
                        (item.source_snapshot_id, endpoint_id),
                        set(),
                    )
                }
                if not matches:
                    raise KnowledgeConflictError(
                        "Candidate Provenance 不是端点的活动 Evidence"
                    )
                covered_endpoints.update(matches)
            if covered_endpoints != endpoint_ids:
                raise KnowledgeConflictError(
                    "Candidate Provenance 未覆盖两个端点"
                )
            self._insert_relation(connection, relation)
            stored_row = connection.execute(
                "SELECT * FROM knowledge_relations WHERE relation_id=?",
                (relation.relation_id,),
            ).fetchone()
            if stored_row is None:
                raise KnowledgeIntegrityError(
                    "Candidate Relation 写入后不可读取"
                )
            stored_relation = self._relation(stored_row)
            for item in provenance:
                self._insert_provenance(connection, item)
            self._save_operation(
                connection,
                operation_key=idempotency_key,
                request_hash=request_hash,
                response_kind="relation",
                response={
                    "relation": stored_relation.model_dump(mode="json")
                },
            )
            connection.commit()
        return stored_relation, False

    def replace_relation(
        self,
        *,
        relation: KnowledgeRelationRecord,
        expected_version: int,
        expected_hash: str,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[KnowledgeRelationRecord, bool]:
        validate_relation_hash(relation)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=idempotency_key,
                request_hash=request_hash,
                response_kind="relation",
            )
            if replay is not None:
                return (
                    KnowledgeRelationRecord.model_validate(
                        replay["relation"]
                    ),
                    True,
                )
            row = connection.execute(
                "SELECT * FROM knowledge_relations WHERE relation_id=?",
                (relation.relation_id,),
            ).fetchone()
            if row is None:
                raise KnowledgeNotFoundError(
                    f"未找到 relation_id={relation.relation_id}"
                )
            current = self._relation(row)
            if (
                current.version != expected_version
                or current.relation_hash != expected_hash
            ):
                raise KnowledgeStaleReviewError(
                    "Relation version/hash 已变化"
                )
            if relation.version != current.version + 1:
                raise KnowledgeConflictError("Relation version 没有递增")
            changed = connection.execute(
                """
                UPDATE knowledge_relations SET
                  status=?, version=?, relation_hash=?,
                  record_json=?, updated_at=?
                WHERE relation_id=? AND version=? AND relation_hash=?
                """,
                (
                    relation.status,
                    relation.version,
                    relation.relation_hash,
                    relation.model_dump_json(),
                    relation.updated_at,
                    relation.relation_id,
                    expected_version,
                    expected_hash,
                ),
            ).rowcount
            if changed != 1:
                raise KnowledgeStaleReviewError("Relation review CAS 失败")
            self._save_operation(
                connection,
                operation_key=idempotency_key,
                request_hash=request_hash,
                response_kind="relation",
                response={"relation": relation.model_dump(mode="json")},
            )
            connection.commit()
        return relation, False

    def archive_ingestion(
        self,
        *,
        ingestion_id: str,
        actor: str,
        reason: str,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[KnowledgeIngestionRecord, bool]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(
                connection,
                operation_key=idempotency_key,
                request_hash=request_hash,
                response_kind="ingestion",
            )
            if replay is not None:
                return (
                    KnowledgeIngestionRecord.model_validate(
                        replay["ingestion"]
                    ),
                    True,
                )
            row = connection.execute(
                "SELECT * FROM knowledge_ingestions WHERE ingestion_id=?",
                (ingestion_id,),
            ).fetchone()
            if row is None:
                raise KnowledgeNotFoundError(
                    f"未找到 ingestion_id={ingestion_id}"
                )
            current = self._ingestion(row)
            if current.status == "archived":
                final_record = current
            elif current.status != "active":
                raise KnowledgeConflictError("只有 active ingestion 可归档")
            else:
                final_record = current.model_copy(
                    update={
                        "status": "archived",
                        "archived_by": actor,
                        "archived_at": utc_now(),
                        "archive_reason": reason.strip(),
                    }
                )
                connection.execute(
                    """
                    UPDATE knowledge_ingestions
                    SET status=?, record_json=? WHERE ingestion_id=?
                    """,
                    (
                        final_record.status,
                        final_record.model_dump_json(),
                        ingestion_id,
                    ),
                )
            self._save_operation(
                connection,
                operation_key=idempotency_key,
                request_hash=request_hash,
                response_kind="ingestion",
                response={
                    "ingestion": final_record.model_dump(mode="json")
                },
            )
            connection.commit()
        return final_record, False

    def active_referenced_job_ids(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT source_job_id FROM knowledge_ingestions
                WHERE status='active'
                """
            ).fetchall()
        return {str(row[0]) for row in rows}
