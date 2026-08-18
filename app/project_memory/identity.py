from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from app.project_memory.errors import ProjectMemoryIntegrityError
from app.project_memory.schemas import (
    ProjectFactContent,
    ProjectFactPack,
    ProjectFactRecord,
    ProjectRecord,
)


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def new_project_id() -> str:
    # 随机稳定 ID 不泄露本机路径或论文名。
    return f"project_{uuid4().hex[:24]}"


def new_fact_id() -> str:
    return f"fact_{uuid4().hex[:24]}"


def compute_content_hash(content: ProjectFactContent) -> str:
    return canonical_sha256(content.model_dump(mode="json"))


def compute_project_hash(project: ProjectRecord) -> str:
    payload = project.model_dump(mode="json")
    payload.pop("record_hash", None)
    return canonical_sha256(payload)


def compute_fact_hash(fact: ProjectFactRecord) -> str:
    payload = fact.model_dump(mode="json")
    payload.pop("record_hash", None)
    return canonical_sha256(payload)


def compute_pack_hash(pack: ProjectFactPack) -> str:
    payload = pack.model_dump(mode="json")
    payload.pop("pack_hash", None)
    return canonical_sha256(payload)


def validate_project_hash(project: ProjectRecord) -> None:
    if compute_project_hash(project) != project.record_hash:
        raise ProjectMemoryIntegrityError("Project record hash 不一致")


def validate_fact_hash(fact: ProjectFactRecord) -> None:
    if fact.content is not None:
        if compute_content_hash(fact.content) != fact.content_hash:
            raise ProjectMemoryIntegrityError("Project fact content hash 不一致")
    if compute_fact_hash(fact) != fact.record_hash:
        raise ProjectMemoryIntegrityError("Project fact record hash 不一致")
