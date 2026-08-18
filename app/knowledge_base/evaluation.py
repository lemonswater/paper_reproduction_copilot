from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge_base.retrieval import KnowledgeRetriever
from app.knowledge_base.schemas import (
    KnowledgeEntityKind,
    KnowledgeQueryRequest,
    KnowledgeRelationType,
)


class KnowledgeEvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeGoldenCase(KnowledgeEvalModel):
    case_id: str
    query: str
    entity_kinds: list[KnowledgeEntityKind] = Field(default_factory=list)
    expected_entity_names: list[str] = Field(min_length=1)
    expected_relation_types: list[KnowledgeRelationType] = Field(
        default_factory=list
    )
    max_depth: int = Field(default=1, ge=0, le=2)
    minimum_entity_recall: float = Field(default=1.0, ge=0.0, le=1.0)
    minimum_evidence_coverage: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )


class KnowledgeGoldenCaseResult(KnowledgeEvalModel):
    case_id: str
    passed: bool
    entity_recall: float
    relation_recall: float
    evidence_coverage: float
    candidate_leak_count: int = Field(ge=0)
    missing_entities: list[str]
    missing_relation_types: list[str]
    pack_hash: str


class KnowledgeGoldenReport(KnowledgeEvalModel):
    suite_id: str
    passed: bool
    case_count: int = Field(ge=0)
    passed_count: int = Field(ge=0)
    results: list[KnowledgeGoldenCaseResult]


def load_knowledge_golden_cases(
    path: Path,
) -> tuple[str, list[KnowledgeGoldenCase]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Knowledge Golden suite 顶层必须是 object")
    suite_id = str(payload.get("suite_id", "")).strip()
    raw_cases = payload.get("cases")
    if not suite_id or not isinstance(raw_cases, list):
        raise ValueError("Knowledge Golden suite 缺少 suite_id/cases")
    cases = [KnowledgeGoldenCase.model_validate(item) for item in raw_cases]
    if not cases or len({item.case_id for item in cases}) != len(cases):
        raise ValueError("Knowledge Golden case 为空或 case_id 重复")
    return suite_id, cases


def evaluate_knowledge_cases(
    *,
    retriever: KnowledgeRetriever,
    suite_id: str,
    cases: list[KnowledgeGoldenCase],
) -> KnowledgeGoldenReport:
    results = []
    for case in cases:
        pack = retriever.query(
            KnowledgeQueryRequest(
                query=case.query,
                entity_kinds=case.entity_kinds,
                max_entities=50,
                max_relations=100,
                max_depth=case.max_depth,
                include_candidates=False,
            )
        )
        names = {
            item.entity.display_name.casefold()
            for item in pack.entities
        }
        expected_names = {
            item.casefold() for item in case.expected_entity_names
        }
        missing_entities = sorted(expected_names - names)
        entity_recall = (
            1.0 - len(missing_entities) / len(expected_names)
        )

        relation_types = {
            item.relation_type
            for item in pack.authoritative_relations
        }
        expected_relation_types = set(case.expected_relation_types)
        missing_relations = sorted(
            expected_relation_types - relation_types
        )
        relation_recall = (
            1.0
            if not expected_relation_types
            else 1.0
            - len(missing_relations) / len(expected_relation_types)
        )

        authoritative_subjects = {
            item.entity.entity_id for item in pack.entities
        } | {
            item.relation_id for item in pack.authoritative_relations
        }
        evidenced_subjects = {
            item.subject_id for item in pack.subject_evidence
        }
        evidence_coverage = (
            1.0
            if not authoritative_subjects
            else len(authoritative_subjects & evidenced_subjects)
            / len(authoritative_subjects)
        )
        candidate_leaks = len(pack.candidate_relations)
        passed = (
            entity_recall >= case.minimum_entity_recall
            and not missing_relations
            and evidence_coverage >= case.minimum_evidence_coverage
            and candidate_leaks == 0
        )
        results.append(
            KnowledgeGoldenCaseResult(
                case_id=case.case_id,
                passed=passed,
                entity_recall=entity_recall,
                relation_recall=relation_recall,
                evidence_coverage=evidence_coverage,
                candidate_leak_count=candidate_leaks,
                missing_entities=missing_entities,
                missing_relation_types=missing_relations,
                pack_hash=pack.pack_hash,
            )
        )
    passed_count = sum(item.passed for item in results)
    return KnowledgeGoldenReport(
        suite_id=suite_id,
        passed=passed_count == len(results),
        case_count=len(results),
        passed_count=passed_count,
        results=results,
    )
