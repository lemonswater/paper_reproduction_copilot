"""Phase 46: Project Memory Service 测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.project_memory.errors import ProjectMemoryConflictError
from app.project_memory.identity import compute_content_hash, compute_fact_hash
from app.project_memory.repository import SqliteProjectMemoryRepository
from app.project_memory.retrieval import ProjectFactRetriever
from app.project_memory.evidence import ProjectJobSnapshot
from app.project_memory.schemas import (
    ChatUserMessageFactSource,
    DatasetBindingFactValue,
    ExecutionProfileDraftValue,
    ManualFactProposalRequest,
    ManualUserFactSource,
    ProjectAnchor,
    ProjectCreateRequest,
    ProjectFactContent,
    ProjectFactDraftContent,
    ProjectFactRecord,
    TextFactValue,
)
from app.project_memory.service import ProjectMemoryService
from app.secrets.redaction import SecretRedactor
from tests.helpers.project_memory import NOW, fixed_clock, make_anchor


@pytest.fixture
def service(tmp_path):
    repo = SqliteProjectMemoryRepository(tmp_path / "pm.db")
    repo.initialize()

    jobs = MagicMock()
    anchor = make_anchor()
    jobs.read.return_value = ProjectJobSnapshot(anchor=anchor)

    chats = MagicMock()

    retriever = ProjectFactRetriever(
        repo,
        top_k=20,
        max_chars=20000,
        clock=fixed_clock,
    )

    redactor = SecretRedactor()

    svc = ProjectMemoryService(
        repository=repo,
        jobs=jobs,
        chats=chats,
        retriever=retriever,
        redactor=redactor,
        clock=fixed_clock,
    )
    svc._test_anchor = anchor
    return svc


def _create_project(service):
    request = ProjectCreateRequest(
        display_name="Test Project",
        anchor_job_id=service._test_anchor.job_id,
        expected_anchor_job_version=service._test_anchor.job_version,
        expected_workspace_manifest_hash=service._test_anchor.workspace_manifest_hash,
    )
    return service.create_project(
        request=request,
        idempotency_key="key-create-1",
        actor="local-user",
    )


def test_create_project_and_auto_bind_anchor(service):
    result = _create_project(service)
    assert result.replayed is False
    project = result.project
    assert project.status == "active"
    bindings = service.repository.list_bindings(project.project_id)
    assert len(bindings) == 1
    assert bindings[0].role == "anchor"


def test_idempotent_create_returns_same_project(service):
    result1 = _create_project(service)
    result2 = _create_project(service)
    assert result1.replayed is False
    assert result2.replayed is True
    assert result1.project.project_id == result2.project.project_id


def test_archived_project_cannot_bind_job(service):
    result = _create_project(service)
    project = result.project

    # Archive the project
    from app.project_memory.schemas import ProjectArchiveRequest

    service.archive_project(
        project_id=project.project_id,
        request=ProjectArchiveRequest(
            expected_version=project.version,
            expected_record_hash=project.record_hash,
            reason="test archive",
        ),
        idempotency_key="key-archive-1",
        actor="local-user",
    )

    # Try to bind a new job
    from app.project_memory.schemas import ProjectBindJobRequest

    with pytest.raises(ProjectMemoryConflictError):
        service.bind_job(
            project_id=project.project_id,
            request=ProjectBindJobRequest(
                job_id="job-new-001",
                expected_job_version=0,
                expected_workspace_manifest_hash="d" * 64,
            ),
            expected_project_version=1,
            expected_project_hash=service.repository.get_project(project.project_id).record_hash,
            idempotency_key="key-bind-1",
            actor="local-user",
        )


def test_manual_proposal_stays_proposed(service):
    result = _create_project(service)
    project_id = result.project.project_id

    content = ProjectFactDraftContent(
        category="user_constraint",
        key="network_access",
        value=TextFactValue(text="default offline"),
    )
    request = ManualFactProposalRequest(
        content=content,
        source_note="manual proposal",
    )
    fact_result = service.propose_manual(
        project_id=project_id,
        request=request,
        idempotency_key="key-propose-1",
        actor="local-user",
    )
    assert fact_result.fact.status == "proposed"
    assert fact_result.fact.authority == "unconfirmed_proposal"

    # Proposed should NOT appear in active pack
    pack = service.retriever.for_project(project_id)
    assert len(pack.items) == 0


def test_confirm_makes_fact_active(service):
    result = _create_project(service)
    project_id = result.project.project_id

    content = ProjectFactDraftContent(
        category="user_constraint",
        key="network_access",
        value=TextFactValue(text="default offline"),
    )
    propose_result = service.propose_manual(
        project_id=project_id,
        request=ManualFactProposalRequest(
            content=content,
            source_note="manual proposal",
        ),
        idempotency_key="key-propose-2",
        actor="local-user",
    )

    from app.project_memory.schemas import FactConfirmRequest

    confirm_result = service.confirm(
        fact_id=propose_result.fact.fact_id,
        request=FactConfirmRequest(
            expected_version=propose_result.fact.version,
            expected_record_hash=propose_result.fact.record_hash,
            reason="test confirm",
        ),
        idempotency_key="key-confirm-1",
        actor="local-user",
    )
    assert confirm_result.fact.status == "confirmed"

    # Should appear in active pack
    pack = service.retriever.for_project(project_id)
    assert len(pack.items) == 1
    assert pack.items[0].fact_id == propose_result.fact.fact_id


def test_revoke_removes_from_active(service):
    result = _create_project(service)
    project_id = result.project.project_id

    content = ProjectFactDraftContent(
        category="user_constraint",
        key="network_access",
        value=TextFactValue(text="default offline"),
    )
    propose_result = service.propose_manual(
        project_id=project_id,
        request=ManualFactProposalRequest(
            content=content,
            source_note="manual proposal",
        ),
        idempotency_key="key-propose-3",
        actor="local-user",
    )

    from app.project_memory.schemas import FactConfirmRequest, FactTerminalRequest

    confirm_result = service.confirm(
        fact_id=propose_result.fact.fact_id,
        request=FactConfirmRequest(
            expected_version=propose_result.fact.version,
            expected_record_hash=propose_result.fact.record_hash,
            reason="test confirm",
        ),
        idempotency_key="key-confirm-2",
        actor="local-user",
    )

    service.revoke(
        fact_id=propose_result.fact.fact_id,
        request=FactTerminalRequest(
            expected_version=confirm_result.fact.version,
            expected_record_hash=confirm_result.fact.record_hash,
            reason="test revoke",
        ),
        idempotency_key="key-revoke-1",
        actor="local-user",
    )

    pack = service.retriever.for_project(project_id)
    assert len(pack.items) == 0


def test_confirmed_cannot_directly_delete(service):
    result = _create_project(service)
    project_id = result.project.project_id

    content = ProjectFactDraftContent(
        category="user_constraint",
        key="network_access",
        value=TextFactValue(text="default offline"),
    )
    propose_result = service.propose_manual(
        project_id=project_id,
        request=ManualFactProposalRequest(
            content=content,
            source_note="manual proposal",
        ),
        idempotency_key="key-propose-4",
        actor="local-user",
    )

    from app.project_memory.schemas import FactConfirmRequest, FactTerminalRequest

    confirm_result = service.confirm(
        fact_id=propose_result.fact.fact_id,
        request=FactConfirmRequest(
            expected_version=propose_result.fact.version,
            expected_record_hash=propose_result.fact.record_hash,
            reason="test confirm",
        ),
        idempotency_key="key-confirm-3",
        actor="local-user",
    )

    with pytest.raises(ProjectMemoryConflictError):
        service.delete(
            fact_id=propose_result.fact.fact_id,
            request=FactTerminalRequest(
                expected_version=confirm_result.fact.version,
                expected_record_hash=confirm_result.fact.record_hash,
                reason="test delete",
            ),
            idempotency_key="key-delete-1",
            actor="local-user",
        )


def test_terminal_fact_can_be_deleted(service):
    result = _create_project(service)
    project_id = result.project.project_id

    content = ProjectFactDraftContent(
        category="user_constraint",
        key="network_access",
        value=TextFactValue(text="default offline"),
    )
    propose_result = service.propose_manual(
        project_id=project_id,
        request=ManualFactProposalRequest(
            content=content,
            source_note="manual proposal",
        ),
        idempotency_key="key-propose-5",
        actor="local-user",
    )

    from app.project_memory.schemas import FactTerminalRequest

    # Revoke first, then delete
    service.revoke(
        fact_id=propose_result.fact.fact_id,
        request=FactTerminalRequest(
            expected_version=propose_result.fact.version,
            expected_record_hash=propose_result.fact.record_hash,
            reason="test revoke",
        ),
        idempotency_key="key-revoke-2",
        actor="local-user",
    )

    revoked = service.repository.get_fact(propose_result.fact.fact_id)
    delete_result = service.delete(
        fact_id=propose_result.fact.fact_id,
        request=FactTerminalRequest(
            expected_version=revoked.version,
            expected_record_hash=revoked.record_hash,
            reason="test delete",
        ),
        idempotency_key="key-delete-2",
        actor="local-user",
    )
    assert delete_result.fact.status == "deleted"
    assert delete_result.fact.content is None


def test_correction_creates_successor(service):
    result = _create_project(service)
    project_id = result.project.project_id

    content = ProjectFactDraftContent(
        category="user_constraint",
        key="network_access",
        value=TextFactValue(text="default offline"),
    )
    propose_result = service.propose_manual(
        project_id=project_id,
        request=ManualFactProposalRequest(
            content=content,
            source_note="manual proposal",
        ),
        idempotency_key="key-propose-6",
        actor="local-user",
    )

    from app.project_memory.schemas import FactConfirmRequest, FactCorrectRequest

    confirm_result = service.confirm(
        fact_id=propose_result.fact.fact_id,
        request=FactConfirmRequest(
            expected_version=propose_result.fact.version,
            expected_record_hash=propose_result.fact.record_hash,
            reason="test confirm",
        ),
        idempotency_key="key-confirm-4",
        actor="local-user",
    )

    new_content = ProjectFactDraftContent(
        category="user_constraint",
        key="network_access",
        value=TextFactValue(text="allow internet"),
    )
    correct_result = service.correct(
        fact_id=propose_result.fact.fact_id,
        request=FactCorrectRequest(
            expected_version=confirm_result.fact.version,
            expected_record_hash=confirm_result.fact.record_hash,
            content=new_content,
            reason="corrected to allow internet",
        ),
        idempotency_key="key-correct-1",
        actor="local-user",
    )
    assert correct_result.previous.status == "superseded"
    assert correct_result.successor.status == "confirmed"
    assert correct_result.successor.supersedes_fact_id == propose_result.fact.fact_id

    # Pack should contain only the successor
    pack = service.retriever.for_project(project_id)
    assert len(pack.items) == 1
    assert pack.items[0].fact_id == correct_result.successor.fact_id


def test_correction_cannot_change_category_key(service):
    result = _create_project(service)
    project_id = result.project.project_id

    content = ProjectFactDraftContent(
        category="user_constraint",
        key="network_access",
        value=TextFactValue(text="default offline"),
    )
    propose_result = service.propose_manual(
        project_id=project_id,
        request=ManualFactProposalRequest(
            content=content,
            source_note="manual proposal",
        ),
        idempotency_key="key-propose-7",
        actor="local-user",
    )

    from app.project_memory.schemas import FactConfirmRequest, FactCorrectRequest

    confirm_result = service.confirm(
        fact_id=propose_result.fact.fact_id,
        request=FactConfirmRequest(
            expected_version=propose_result.fact.version,
            expected_record_hash=propose_result.fact.record_hash,
            reason="test confirm",
        ),
        idempotency_key="key-confirm-5",
        actor="local-user",
    )

    new_content = ProjectFactDraftContent(
        category="user_constraint",
        key="different_key",
        value=TextFactValue(text="allow internet"),
    )
    with pytest.raises(ProjectMemoryConflictError):
        service.correct(
            fact_id=propose_result.fact.fact_id,
            request=FactCorrectRequest(
                expected_version=confirm_result.fact.version,
                expected_record_hash=confirm_result.fact.record_hash,
                content=new_content,
                reason="changed key",
            ),
            idempotency_key="key-correct-2",
            actor="local-user",
        )


def test_dataset_binding_rejects_absolute_path(service):
    result = _create_project(service)
    project_id = result.project.project_id

    content = ProjectFactDraftContent(
        category="dataset_binding",
        key="ntu60",
        value=DatasetBindingFactValue(
            dataset_name="NTU60",
            required_worker_label="/data/datasets/ntu60",
        ),
    )
    with pytest.raises(ValueError):
        service.propose_manual(
            project_id=project_id,
            request=ManualFactProposalRequest(
                content=content,
                source_note="manual proposal",
            ),
            idempotency_key="key-propose-8",
            actor="local-user",
        )
