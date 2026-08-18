from __future__ import annotations

import re

from app.knowledge_base.identity import (
    normalize_knowledge_key,
    sha256_value,
)
from app.knowledge_base.ports import KnowledgeRepository
from app.knowledge_base.schemas import (
    KnowledgeEntityHit,
    KnowledgeEntityRecord,
    KnowledgeQueryPack,
    KnowledgeQueryRequest,
    KnowledgeSubjectEvidence,
)


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def knowledge_terms(value: str) -> list[str]:
    normalized = normalize_knowledge_key(value)
    result: set[str] = set(TOKEN_RE.findall(normalized))
    for token in list(result):
        if any("\u4e00" <= char <= "\u9fff" for char in token):
            # 中文没有空格时加入二元组，避免整句只能精确 LIKE。
            result.update(
                token[index : index + 2]
                for index in range(max(0, len(token) - 1))
            )
    return sorted(item for item in result if item)


def entity_similarity(
    query: str,
    entity: KnowledgeEntityRecord,
) -> tuple[float, list[str]]:
    query_set = set(knowledge_terms(query))
    entity_set = set(
        knowledge_terms(
            " ".join(
                [
                    entity.canonical_key,
                    entity.display_name,
                    entity.description or "",
                ]
            )
        )
    )
    if not query_set or not entity_set:
        return 0.0, []
    matched = sorted(query_set & entity_set)
    union = query_set | entity_set
    jaccard = len(matched) / len(union)
    canonical_query = normalize_knowledge_key(query)
    exact_bonus = 0.45 if canonical_query == entity.canonical_key else 0.0
    contains_bonus = (
        0.20
        if canonical_query in entity.canonical_key
        or entity.canonical_key in canonical_query
        else 0.0
    )
    score = min(1.0, jaccard + exact_bonus + contains_bonus)
    return score, matched


class KnowledgeRetriever:
    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    def query(self, request: KnowledgeQueryRequest) -> KnowledgeQueryPack:
        terms = knowledge_terms(request.query)
        initial = self.repository.search_entities(
            terms=terms[:16],
            kinds=request.entity_kinds,
            limit=min(500, request.max_entities * 8),
        )
        scored: list[KnowledgeEntityHit] = []
        for entity in initial:
            score, matched = entity_similarity(request.query, entity)
            if score > 0:
                scored.append(
                    KnowledgeEntityHit(
                        entity=entity,
                        score=score,
                        matched_terms=matched,
                    )
                )
        scored.sort(
            key=lambda item: (
                -item.score,
                item.entity.kind,
                item.entity.entity_id,
            )
        )
        selected = {
            item.entity.entity_id: item
            for item in scored[: request.max_entities]
        }
        frontier = set(selected)
        relations = {}
        truncated = len(scored) > request.max_entities

        for depth in range(request.max_depth):
            if not frontier or len(relations) >= request.max_relations:
                break
            page = self.repository.relations_for_entities(
                entity_ids=sorted(frontier),
                include_candidates=request.include_candidates,
                limit=request.max_relations - len(relations),
            )
            next_ids: set[str] = set()
            for relation in page:
                relations[relation.relation_id] = relation
                next_ids.update(
                    {
                        relation.source_entity_id,
                        relation.target_entity_id,
                    }
                )
            next_ids -= set(selected)
            room = request.max_entities - len(selected)
            if room <= 0:
                truncated = truncated or bool(next_ids)
                break
            expanded = self.repository.active_entities_by_ids(
                entity_ids=sorted(next_ids),
                limit=room,
            )
            for entity in expanded:
                selected[entity.entity_id] = KnowledgeEntityHit(
                    entity=entity,
                    score=max(0.05, 0.25 / (depth + 1)),
                    matched_terms=[],
                )
            if len(expanded) < len(next_ids):
                truncated = True
            frontier = {item.entity_id for item in expanded}

        ordered_hits = sorted(
            selected.values(),
            key=lambda item: (-item.score, item.entity.entity_id),
        )
        selected_ids = set(selected)
        complete_relations = [
            item
            for item in relations.values()
            if {
                item.source_entity_id,
                item.target_entity_id,
            } <= selected_ids
        ]
        if len(complete_relations) != len(relations):
            truncated = True
        ordered_relations = sorted(
            complete_relations,
            key=lambda item: item.relation_id,
        )
        authoritative = [
            item
            for item in ordered_relations
            if item.status in {"asserted", "confirmed"}
        ]
        candidates = [
            item
            for item in ordered_relations
            if item.status == "candidate"
        ]
        subject_ids = [
            item.entity.entity_id for item in ordered_hits
        ] + [item.relation_id for item in ordered_relations]
        provenance = self.repository.provenance_for_subjects(
            subject_ids=subject_ids,
            limit=min(5000, max(1, len(subject_ids) * 16)),
        )
        evidence = {
            ref.evidence_ref_id: ref
            for item in provenance
            for ref in item.evidence
        }
        by_subject: dict[str, set[str]] = {}
        for item in provenance:
            by_subject.setdefault(item.subject_id, set()).update(
                ref.evidence_ref_id for ref in item.evidence
            )
        query_hash = sha256_value(request.model_dump(mode="json"))
        draft = KnowledgeQueryPack(
            query_hash=query_hash,
            entities=ordered_hits,
            authoritative_relations=authoritative,
            candidate_relations=candidates,
            evidence_refs=sorted(
                evidence.values(),
                key=lambda item: item.evidence_ref_id,
            ),
            subject_evidence=[
                KnowledgeSubjectEvidence(
                    subject_id=subject_id,
                    evidence_ref_ids=sorted(ref_ids),
                )
                for subject_id, ref_ids in sorted(by_subject.items())
            ],
            truncated=truncated,
            pack_hash="0" * 64,
        )
        pack_hash = sha256_value(
            draft.model_dump(mode="json", exclude={"pack_hash"})
        )
        return draft.model_copy(update={"pack_hash": pack_hash})
