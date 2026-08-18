from __future__ import annotations

from app.project_memory.identity import compute_pack_hash
from app.project_memory.schemas import (
    ProjectFactPack,
    ProjectFactPackItem,
)


CATEGORY_PRIORITY = {
    "user_constraint": 100,
    "reproduction_goal": 90,
    "dataset_binding": 80,
    "execution_default": 75,
    "build_prerequisite": 70,
    "project_note": 20,
}


class ProjectFactRetriever:
    def __init__(self, repository, *, top_k: int, max_chars: int, clock):
        self.repository = repository
        self.top_k = top_k
        self.max_chars = max_chars
        self.clock = clock

    def for_project(self, project_id: str) -> ProjectFactPack:
        now = self.clock()
        # expire_due 用于审计落库；active_facts 自身仍会同步排除过期项。
        self.repository.expire_due(
            project_id=project_id,
            now=now,
            actor="system:expiry",
        )
        project = self.repository.get_project(project_id)
        records = self.repository.active_facts(
            project_id=project_id,
            now=now,
            limit=max(self.top_k * 4, self.top_k),
        )
        records.sort(
            key=lambda item: (
                -CATEGORY_PRIORITY[item.content.category],
                item.content.key,
                item.created_at,
                item.fact_id,
            )
        )

        items: list[ProjectFactPackItem] = []
        used = 0
        for record in records:
            if record.content is None:
                continue
            item = ProjectFactPackItem(
                fact_id=record.fact_id,
                fact_hash=record.record_hash,
                category=record.content.category,
                key=record.content.key,
                value=record.content.value,
                source_kind=record.source.kind,
                expires_at=record.expires_at,
            )
            size = len(item.model_dump_json())
            if used + size > self.max_chars:
                continue
            items.append(item)
            used += size
            if len(items) >= self.top_k:
                break

        draft = ProjectFactPack(
            project_id=project.project_id,
            project_hash=project.record_hash,
            items=items,
            pack_hash="0" * 64,
            generated_at=now,
        )
        payload = draft.model_dump(mode="json")
        payload["pack_hash"] = compute_pack_hash(draft)
        return ProjectFactPack.model_validate(payload)

    def for_job(self, job_id: str) -> ProjectFactPack | None:
        project = self.repository.project_for_job(job_id)
        if project is None or project.status != "active":
            return None
        return self.for_project(project.project_id)
