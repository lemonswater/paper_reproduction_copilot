from __future__ import annotations

from app.config import settings
from app.project_memory.evidence import (
    ProjectChatEvidenceReader,
    ProjectJobEvidenceReader,
)
from app.project_memory.repository import SqliteProjectMemoryRepository
from app.project_memory.retrieval import ProjectFactRetriever
from app.project_memory.service import ProjectMemoryService, utc_now
from app.secrets.factory import build_secret_service


def build_project_memory_service(*, job_service, chat_repository):
    repository = SqliteProjectMemoryRepository(
        settings.project_memory_db_path
    )
    repository.initialize()
    retriever = ProjectFactRetriever(
        repository,
        top_k=settings.project_memory_top_k,
        max_chars=settings.project_memory_pack_max_chars,
        clock=utc_now,
    )
    redactor = build_secret_service().build_redactor(
        actor="runtime:project-memory-redactor"
    )
    return ProjectMemoryService(
        repository=repository,
        jobs=ProjectJobEvidenceReader(job_service),
        chats=ProjectChatEvidenceReader(chat_repository),
        retriever=retriever,
        redactor=redactor,
    )
