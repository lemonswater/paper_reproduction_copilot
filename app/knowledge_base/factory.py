from __future__ import annotations

from app.comparison.factory import build_run_evidence_reader
from app.config import settings
from app.interaction.artifacts import ArtifactCatalog
from app.job_runtime.service import JobService
from app.knowledge_base.projector import KnowledgeProjector
from app.knowledge_base.repository import SqliteKnowledgeRepository
from app.knowledge_base.retrieval import KnowledgeRetriever
from app.knowledge_base.service import KnowledgeService
from app.knowledge_base.source_reader import KnowledgeSourceReader


def build_knowledge_repository() -> SqliteKnowledgeRepository:
    repository = SqliteKnowledgeRepository(settings.knowledge_db_path)
    repository.initialize()
    return repository


def build_knowledge_service(
    *,
    job_service: JobService,
    artifact_catalog: ArtifactCatalog,
) -> KnowledgeService:
    repository = build_knowledge_repository()
    verified_runs = build_run_evidence_reader(
        jobs=job_service.store,
        artifact_catalog=artifact_catalog,
    )
    reader = KnowledgeSourceReader(
        verified_runs=verified_runs,
        artifact_catalog=artifact_catalog,
        max_artifact_bytes=settings.knowledge_max_artifact_bytes,
        max_sections=settings.knowledge_max_sections,
        max_facts=settings.knowledge_max_facts,
        max_mappings=settings.knowledge_max_mappings,
    )
    return KnowledgeService(
        repository=repository,
        source_reader=reader,
        projector=KnowledgeProjector(),
        retriever=KnowledgeRetriever(repository),
        minimum_equivalence_score=(
            settings.knowledge_minimum_equivalence_score
        ),
    )
