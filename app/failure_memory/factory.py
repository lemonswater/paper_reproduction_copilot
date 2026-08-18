from __future__ import annotations

from app.comparison.factory import build_run_evidence_reader
from app.config import settings
from app.failure_memory.evidence_reader import FailureEvidenceReader
from app.failure_memory.repository import SqliteFailureCaseRepository
from app.failure_memory.retrieval import FailureCaseRetriever
from app.failure_memory.service import FailureCaseService
from app.interaction.artifacts import ArtifactCatalog
from app.job_runtime.service import JobService


def build_failure_case_retriever() -> FailureCaseRetriever:
    """Graph 节点只需要只读 Retriever，不装配 Job/Artifact 写入链。"""

    repository = SqliteFailureCaseRepository(
        settings.failure_memory_db_path
    )
    repository.initialize()
    return FailureCaseRetriever(
        repository=repository,
        candidate_limit=settings.failure_memory_candidate_limit,
        top_k=settings.failure_memory_top_k,
        minimum_score=settings.failure_memory_minimum_score,
    )


def build_failure_case_service(
    *,
    job_service: JobService,
    artifact_catalog: ArtifactCatalog,
) -> FailureCaseService:
    repository = SqliteFailureCaseRepository(
        settings.failure_memory_db_path
    )
    repository.initialize()
    verified_runs = build_run_evidence_reader(
        jobs=job_service.store,
        artifact_catalog=artifact_catalog,
    )
    retriever = FailureCaseRetriever(
        repository=repository,
        candidate_limit=settings.failure_memory_candidate_limit,
        top_k=settings.failure_memory_top_k,
        minimum_score=settings.failure_memory_minimum_score,
    )
    evidence_reader = FailureEvidenceReader(
        verified_runs=verified_runs,
        artifact_catalog=artifact_catalog,
        max_json_bytes=settings.failure_memory_max_json_bytes,
        max_log_bytes=settings.failure_memory_max_log_bytes,
    )
    return FailureCaseService(
        repository=repository,
        evidence_reader=evidence_reader,
        verified_runs=verified_runs,
        retriever=retriever,
    )
