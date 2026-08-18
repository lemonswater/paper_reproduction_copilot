from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.knowledge_base.schemas import (
    KnowledgeEntityKind,
    KnowledgeEntityRecord,
    KnowledgeEvidenceRef,
    KnowledgeGraphBatch,
    KnowledgeProvenanceRecord,
    KnowledgeRelationRecord,
    KnowledgeRelationType,
    KnowledgeSourceSnapshot,
)


SYMMETRIC_RELATIONS = {"equivalent_to"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_bytes(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def normalize_knowledge_key(value: str) -> str:
    """Unicode 规范化用于检索键，不声称解决语义等价。"""

    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        raise ValueError("Knowledge canonical key 不能为空")
    if len(normalized) > 500:
        raise ValueError("Knowledge canonical key 超过 500 字符")
    return normalized


def build_entity_id(
    *,
    kind: KnowledgeEntityKind,
    scope_key: str,
    canonical_key: str,
) -> str:
    identity = {
        "kind": kind,
        "scope_key": scope_key,
        "canonical_key": canonical_key,
    }
    return f"kgent_{sha256_value(identity)[:24]}"


def build_relation_id(
    *,
    relation_type: KnowledgeRelationType,
    source_entity_id: str,
    target_entity_id: str,
) -> str:
    source = source_entity_id
    target = target_entity_id
    if relation_type in SYMMETRIC_RELATIONS:
        source, target = sorted([source, target])
    identity = {
        "relation_type": relation_type,
        "source_entity_id": source,
        "target_entity_id": target,
    }
    return f"kgrel_{sha256_value(identity)[:24]}"


def build_evidence_ref_id(
    *,
    artifact_id: str,
    content_hash: str,
    locator: dict[str, Any],
) -> str:
    identity = {
        "artifact_id": artifact_id,
        "content_hash": content_hash,
        "locator": locator,
    }
    return f"kgev_{sha256_value(identity)[:24]}"


def build_provenance_id(
    *,
    subject_id: str,
    source_snapshot_id: str,
    evidence_ref_ids: list[str],
) -> str:
    identity = {
        "subject_id": subject_id,
        "source_snapshot_id": source_snapshot_id,
        "evidence_ref_ids": sorted(set(evidence_ref_ids)),
    }
    return f"kgprov_{sha256_value(identity)[:24]}"


def entity_record_hash(entity: KnowledgeEntityRecord) -> str:
    payload = entity.model_dump(
        mode="json",
        exclude={"record_hash", "created_at"},
    )
    return sha256_value(payload)


def relation_record_hash(relation: KnowledgeRelationRecord) -> str:
    payload = relation.model_dump(
        mode="json",
        exclude={"relation_hash", "created_at", "updated_at"},
    )
    return sha256_value(payload)


def provenance_record_hash(
    provenance: KnowledgeProvenanceRecord,
) -> str:
    payload = provenance.model_dump(
        mode="json",
        exclude={"provenance_hash", "created_at"},
    )
    return sha256_value(payload)


def source_snapshot_hash(snapshot: KnowledgeSourceSnapshot) -> str:
    payload = snapshot.model_dump(
        mode="json",
        exclude={"snapshot_id", "snapshot_hash"},
    )
    return sha256_value(payload)


def graph_batch_hash(batch: KnowledgeGraphBatch) -> str:
    """只绑定稳定内容 Hash，不让 created_at 破坏重复投影身份。"""

    return sha256_value(
        {
            "source_snapshot_hash": batch.source.snapshot_hash,
            "entities": sorted(
                (item.entity_id, item.record_hash)
                for item in batch.entities
            ),
            "relations": sorted(
                (item.relation_id, item.relation_hash)
                for item in batch.relations
            ),
            "provenance": sorted(
                (item.provenance_id, item.provenance_hash)
                for item in batch.provenance
            ),
        }
    )


def validate_entity_hash(entity: KnowledgeEntityRecord) -> None:
    if entity.record_hash != entity_record_hash(entity):
        raise ValueError("Knowledge Entity record_hash 不一致")


def validate_relation_hash(relation: KnowledgeRelationRecord) -> None:
    if relation.relation_hash != relation_record_hash(relation):
        raise ValueError("Knowledge Relation relation_hash 不一致")


def validate_provenance_hash(
    provenance: KnowledgeProvenanceRecord,
) -> None:
    if provenance.provenance_hash != provenance_record_hash(provenance):
        raise ValueError("Knowledge Provenance hash 不一致")


def validate_snapshot_hash(snapshot: KnowledgeSourceSnapshot) -> None:
    if snapshot.snapshot_hash != source_snapshot_hash(snapshot):
        raise ValueError("Knowledge Source Snapshot hash 不一致")


def reviewed_relation(
    relation: KnowledgeRelationRecord,
    *,
    decision: str,
    actor: str,
    reason: str,
    now: str | None = None,
) -> KnowledgeRelationRecord:
    """纯函数：执行单向 lifecycle transition，不写数据库。"""

    if decision in {"confirmed", "rejected"}:
        if relation.status != "candidate":
            raise ValueError("只有 candidate 可以 confirm/reject")
    elif decision == "revoked":
        if relation.status != "confirmed":
            raise ValueError("只有 confirmed relation 可以 revoke")
    else:
        raise ValueError("未知 Relation review decision")

    updated = relation.model_copy(
        update={
            "status": decision,
            "authority": "explicit_user",
            "version": relation.version + 1,
            "updated_at": now or utc_now(),
            "reviewed_by": actor,
            "review_reason": reason.strip(),
            "relation_hash": "0" * 64,
        }
    )
    return updated.model_copy(
        update={"relation_hash": relation_record_hash(updated)}
    )
