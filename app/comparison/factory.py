from __future__ import annotations

from app.comparison.repository import FileComparisonRepository
from app.comparison.service import ComparisonJobReader, ComparisonService
from app.config import settings
from app.interaction.artifacts import ArtifactCatalog
from app.run_evidence.reader import VerifiedRunEvidenceReader


def build_comparison_repository() -> FileComparisonRepository:
    return FileComparisonRepository(
        settings.comparison_root,
        max_report_bytes=settings.comparison_report_max_bytes,
        list_scan_limit=settings.comparison_list_scan_limit,
        staging_ttl_seconds=settings.comparison_staging_ttl_seconds,
    )


def build_run_evidence_reader(
    *,
    jobs: ComparisonJobReader,
    artifact_catalog: ArtifactCatalog,
) -> VerifiedRunEvidenceReader:
    return VerifiedRunEvidenceReader(
        jobs=jobs,
        artifact_catalog=artifact_catalog,
        max_manifest_bytes=settings.comparison_manifest_max_bytes,
        max_artifacts=settings.comparison_max_artifacts,
    )


def build_comparison_service(
    *,
    jobs: ComparisonJobReader,
    artifact_catalog: ArtifactCatalog,
    evidence_reader: VerifiedRunEvidenceReader | None = None,
) -> ComparisonService:
    selected_reader = evidence_reader or build_run_evidence_reader(
        jobs=jobs,
        artifact_catalog=artifact_catalog,
    )
    return ComparisonService(
        evidence_reader=selected_reader,
        repository=build_comparison_repository(),
        max_changes=settings.comparison_max_changes,
    )
