# app/rerun/factory.py
from __future__ import annotations

from app.comparison.factory import (
    build_comparison_service,
    build_run_evidence_reader,
)
from app.config import settings
from app.interaction.artifacts import ArtifactCatalog
from app.job_runtime.service import JobService
from app.rerun.repository import SqliteRerunRepository
from app.rerun.service import RerunService


def build_rerun_service(
    *,
    job_service: JobService,
    artifact_catalog: ArtifactCatalog,
    comparison_service=None,
) -> RerunService:
    reader = build_run_evidence_reader(
        jobs=job_service.store,
        artifact_catalog=artifact_catalog,
    )
    selected_comparison = (
        comparison_service
        if comparison_service is not None
        else build_comparison_service(
            jobs=job_service.store,
            artifact_catalog=artifact_catalog,
            evidence_reader=reader,
        )
    )
    return RerunService(
        repository=SqliteRerunRepository(settings.rerun_db_path),
        evidence_reader=reader,
        job_service=job_service,
        comparison_reader=selected_comparison,
        proposal_ttl_seconds=settings.rerun_proposal_ttl_seconds,
        max_command_chars=settings.rerun_max_command_chars,
        max_argv_items=settings.rerun_max_argv_items,
        max_edits=settings.rerun_max_edits,
    )
