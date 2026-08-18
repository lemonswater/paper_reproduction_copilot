from __future__ import annotations

from app.project_memory.identity import (
    compute_content_hash,
    compute_fact_hash,
    compute_project_hash,
)
from app.project_memory.schemas import (
    ManualUserFactSource,
    ProjectAnchor,
    ProjectFactContent,
    ProjectFactRecord,
    ProjectRecord,
    TextFactValue,
)


NOW = "2026-08-11T10:00:00+00:00"


def fixed_clock() -> str:
    return NOW


def make_anchor(
    *,
    job_id: str = "job-anchor-001",
    job_version: int = 0,
    workspace_manifest_hash: str = "a" * 64,
    paper_sha256: str = "b" * 64,
    repository_commit: str = "c" * 40,
) -> ProjectAnchor:
    return ProjectAnchor(
        job_id=job_id,
        job_version=job_version,
        run_id=f"run-{job_id}",
        workspace_manifest_id=f"manifest-{job_id}",
        workspace_manifest_hash=workspace_manifest_hash,
        paper_sha256=paper_sha256,
        repository_commit=repository_commit,
        repository_clean=True,
    )


def make_project(
    *,
    project_id: str = "project_" + "1" * 24,
    display_name: str = "Test Project",
    status: str = "active",
    anchor: ProjectAnchor | None = None,
    version: int = 0,
) -> ProjectRecord:
    raw = ProjectRecord(
        project_id=project_id,
        display_name=display_name,
        status=status,
        anchor=anchor or make_anchor(),
        version=version,
        record_hash="0" * 64,
        created_by="local-user",
        created_at=NOW,
        updated_at=NOW,
    )
    payload = raw.model_dump(mode="json")
    payload["record_hash"] = compute_project_hash(raw)
    return ProjectRecord.model_validate(payload)


def make_text_content(
    *,
    category: str = "user_constraint",
    key: str = "network_access",
    text: str = "default offline",
) -> ProjectFactContent:
    return ProjectFactContent(
        category=category,
        key=key,
        value=TextFactValue(text=text),
    )


def confirmed_fact(
    *,
    project_id: str = "project_" + "1" * 24,
    fact_id: str = "fact_" + "2" * 24,
    key: str = "network_access",
    text: str = "default offline",
    version: int = 1,
) -> ProjectFactRecord:
    content = make_text_content(key=key, text=text)
    raw = ProjectFactRecord(
        fact_id=fact_id,
        project_id=project_id,
        version=version,
        status="confirmed",
        authority="explicit_user",
        content=content,
        content_hash=compute_content_hash(content),
        source=ManualUserFactSource(
            actor="local-user",
            source_note="manual acceptance fixture",
            request_sha256="3" * 64,
        ),
        confirmation={
            "actor": "local-user",
            "reason": "fixture confirmation",
            "confirmed_at": NOW,
        },
        created_at=NOW,
        updated_at=NOW,
        record_hash="0" * 64,
    )
    payload = raw.model_dump(mode="json")
    payload["record_hash"] = compute_fact_hash(raw)
    return ProjectFactRecord.model_validate(payload)


def proposed_fact(
    *,
    project_id: str = "project_" + "1" * 24,
    fact_id: str = "fact_" + "3" * 24,
    key: str = "build_prereq",
    text: str = "check gcc before build",
) -> ProjectFactRecord:
    content = make_text_content(
        category="build_prerequisite",
        key=key,
        text=text,
    )
    raw = ProjectFactRecord(
        fact_id=fact_id,
        project_id=project_id,
        version=0,
        status="proposed",
        authority="unconfirmed_proposal",
        content=content,
        content_hash=compute_content_hash(content),
        source=ManualUserFactSource(
            actor="local-user",
            source_note="manual proposal fixture",
            request_sha256="4" * 64,
        ),
        created_at=NOW,
        updated_at=NOW,
        record_hash="0" * 64,
    )
    payload = raw.model_dump(mode="json")
    payload["record_hash"] = compute_fact_hash(raw)
    return ProjectFactRecord.model_validate(payload)
