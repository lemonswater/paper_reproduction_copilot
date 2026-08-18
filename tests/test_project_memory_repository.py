"""Phase 46: Project Memory Repository 测试。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.project_memory.errors import (
    ProjectFactNotFoundError,
    ProjectMemoryConflictError,
    ProjectMemoryIntegrityError,
    ProjectNotFoundError,
)
from app.project_memory.identity import (
    compute_fact_hash,
)
from app.project_memory.repository import SqliteProjectMemoryRepository
from app.project_memory.schemas import (
    ChatUserMessageFactSource,
    ManualUserFactSource,
    ProjectFactConfirmation,
    ProjectFactContent,
    ProjectFactRecord,
    ProjectJobBinding,
    ProjectRecord,
    TextFactValue,
)
from tests.helpers.project_memory import (
    NOW,
    confirmed_fact,
    make_anchor,
    make_project,
    make_text_content,
    proposed_fact,
)


@pytest.fixture
def repo(tmp_path):
    r = SqliteProjectMemoryRepository(tmp_path / "pm.db")
    r.initialize()
    return r


def _binding_for(project: ProjectRecord) -> ProjectJobBinding:
    return ProjectJobBinding(
        project_id=project.project_id,
        job_id=project.anchor.job_id,
        job_version_at_binding=project.anchor.job_version,
        run_id=project.anchor.run_id,
        workspace_manifest_id=project.anchor.workspace_manifest_id,
        workspace_manifest_hash=project.anchor.workspace_manifest_hash,
        paper_sha256=project.anchor.paper_sha256,
        repository_commit=project.anchor.repository_commit,
        role="anchor",
        bound_by="local-user",
        bound_at=NOW,
    )


def test_create_project_and_anchor_binding_are_atomic(repo, tmp_path):
    project = make_project()
    binding = _binding_for(project)
    saved, replayed = repo.create_project(
        project=project,
        anchor_binding=binding,
        operation_key="op:create:1",
        request_hash="h1",
    )
    assert replayed is False
    assert saved.project_id == project.project_id
    fetched = repo.get_project(project.project_id)
    assert fetched.record_hash == project.record_hash
    bindings = repo.list_bindings(project.project_id)
    assert len(bindings) == 1
    assert bindings[0].job_id == project.anchor.job_id


def test_one_job_cannot_bind_two_projects(repo):
    project = make_project()
    repo.create_project(
        project=project,
        anchor_binding=_binding_for(project),
        operation_key="op:create:1",
        request_hash="h1",
    )
    project2 = make_project(
        project_id="project_" + "9" * 24,
        anchor=make_anchor(),
    )
    with pytest.raises(ProjectMemoryConflictError):
        repo.create_project(
            project=project2,
            anchor_binding=_binding_for(project2),
            operation_key="op:create:2",
            request_hash="h2",
        )


def test_idempotent_create_returns_original_project(repo):
    project = make_project()
    binding = _binding_for(project)
    saved1, replayed1 = repo.create_project(
        project=project,
        anchor_binding=binding,
        operation_key="op:create:1",
        request_hash="h1",
    )
    saved2, replayed2 = repo.create_project(
        project=project,
        anchor_binding=binding,
        operation_key="op:create:1",
        request_hash="h1",
    )
    assert replayed1 is False
    assert replayed2 is True
    assert saved1.project_id == saved2.project_id
    assert saved1.record_hash == saved2.record_hash


def test_same_idempotency_key_different_payload_conflicts(repo):
    project = make_project()
    repo.create_project(
        project=project,
        anchor_binding=_binding_for(project),
        operation_key="op:create:1",
        request_hash="h1",
    )
    project2 = make_project(
        project_id="project_" + "8" * 24,
    )
    with pytest.raises(ProjectMemoryConflictError):
        repo.create_project(
            project=project2,
            anchor_binding=_binding_for(project2),
            operation_key="op:create:1",
            request_hash="h2",
        )


def test_stale_project_hash_rejects_job_binding(repo):
    project = make_project()
    repo.create_project(
        project=project,
        anchor_binding=_binding_for(project),
        operation_key="op:create:1",
        request_hash="h1",
    )
    member_binding = ProjectJobBinding(
        project_id=project.project_id,
        job_id="job-member-001",
        job_version_at_binding=0,
        run_id="run-job-member-001",
        workspace_manifest_id="manifest-member-001",
        workspace_manifest_hash="d" * 64,
        paper_sha256=project.anchor.paper_sha256,
        repository_commit=project.anchor.repository_commit,
        role="member",
        bound_by="local-user",
        bound_at=NOW,
    )
    with pytest.raises(ProjectMemoryConflictError):
        repo.bind_job(
            binding=member_binding,
            expected_project_version=99,
            expected_project_hash="0" * 64,
            operation_key="op:bind:1",
            request_hash="h3",
        )


def test_create_proposed_and_confirm_fact(repo):
    project = make_project()
    repo.create_project(
        project=project,
        anchor_binding=_binding_for(project),
        operation_key="op:create:1",
        request_hash="h1",
    )
    fact = proposed_fact(project_id=project.project_id)
    saved, replayed = repo.create_fact(
        fact=fact,
        operation_key="op:propose:1",
        request_hash="h4",
    )
    assert replayed is False
    assert saved.status == "proposed"

    # Confirm it
    confirmed_raw = saved.model_dump(mode="json")
    confirmed_raw.update({
        "version": saved.version + 1,
        "status": "confirmed",
        "authority": "explicit_user",
        "confirmation": {
            "actor": "local-user",
            "reason": "test confirm",
            "confirmed_at": NOW,
        },
        "updated_at": NOW,
        "record_hash": "0" * 64,
    })
    draft = ProjectFactRecord.model_validate(confirmed_raw)
    confirmed_raw["record_hash"] = compute_fact_hash(draft)
    confirmed = ProjectFactRecord.model_validate(confirmed_raw)

    result, replayed2 = repo.replace_fact(
        fact=confirmed,
        expected_version=saved.version,
        expected_hash=saved.record_hash,
        operation_key="op:confirm:1",
        request_hash="h5",
    )
    assert replayed2 is False
    assert result.status == "confirmed"


def test_stale_fact_version_rejects_mutation(repo):
    project = make_project()
    repo.create_project(
        project=project,
        anchor_binding=_binding_for(project),
        operation_key="op:create:1",
        request_hash="h1",
    )
    fact = proposed_fact(project_id=project.project_id)
    saved, _ = repo.create_fact(
        fact=fact,
        operation_key="op:propose:1",
        request_hash="h4",
    )
    # Try to confirm with wrong version
    confirmed_raw = saved.model_dump(mode="json")
    confirmed_raw.update({
        "version": 99,
        "status": "confirmed",
        "authority": "explicit_user",
        "confirmation": {
            "actor": "local-user",
            "reason": "stale",
            "confirmed_at": NOW,
        },
        "updated_at": NOW,
        "record_hash": "0" * 64,
    })
    draft = ProjectFactRecord.model_validate(confirmed_raw)
    confirmed_raw["record_hash"] = compute_fact_hash(draft)
    confirmed = ProjectFactRecord.model_validate(confirmed_raw)

    with pytest.raises(ProjectMemoryConflictError):
        repo.replace_fact(
            fact=confirmed,
            expected_version=88,
            expected_hash="0" * 64,
            operation_key="op:confirm:1",
            request_hash="h5",
        )


def test_active_query_excludes_expired_even_before_sweep(repo):
    project = make_project()
    repo.create_project(
        project=project,
        anchor_binding=_binding_for(project),
        operation_key="op:create:1",
        request_hash="h1",
    )
    # Create a confirmed fact with expiry in the past
    fact = confirmed_fact(project_id=project.project_id)
    raw = fact.model_dump(mode="json")
    raw["expires_at"] = "2026-01-01T00:00:00+00:00"
    raw["record_hash"] = "0" * 64
    draft = ProjectFactRecord.model_validate(raw)
    raw["record_hash"] = compute_fact_hash(draft)
    expired_fact = ProjectFactRecord.model_validate(raw)

    # We need to insert it as confirmed directly
    # First create as proposed, then confirm
    proposed_raw = expired_fact.model_dump(mode="json")
    proposed_raw.update({
        "version": 0,
        "status": "proposed",
        "authority": "unconfirmed_proposal",
        "confirmation": None,
        "record_hash": "0" * 64,
    })
    draft_p = ProjectFactRecord.model_validate(proposed_raw)
    proposed_raw["record_hash"] = compute_fact_hash(draft_p)
    proposed = ProjectFactRecord.model_validate(proposed_raw)

    saved, _ = repo.create_fact(
        fact=proposed,
        operation_key="op:propose:2",
        request_hash="h6",
    )

    # Now confirm with the expired-at
    confirm_raw = saved.model_dump(mode="json")
    confirm_raw.update({
        "version": saved.version + 1,
        "status": "confirmed",
        "authority": "explicit_user",
        "confirmation": {
            "actor": "local-user",
            "reason": "test",
            "confirmed_at": NOW,
        },
        "expires_at": "2026-01-01T00:00:00+00:00",
        "updated_at": NOW,
        "record_hash": "0" * 64,
    })
    draft_c = ProjectFactRecord.model_validate(confirm_raw)
    confirm_raw["record_hash"] = compute_fact_hash(draft_c)
    confirmed = ProjectFactRecord.model_validate(confirm_raw)

    repo.replace_fact(
        fact=confirmed,
        expected_version=saved.version,
        expected_hash=saved.record_hash,
        operation_key="op:confirm:2",
        request_hash="h7",
    )

    # Query active facts with a current time - should exclude the expired one
    active = repo.active_facts(
        project_id=project.project_id,
        now="2026-08-11T10:00:00+00:00",
        limit=100,
    )
    assert len(active) == 0


def test_deleted_tombstone_has_no_content(repo):
    project = make_project()
    repo.create_project(
        project=project,
        anchor_binding=_binding_for(project),
        operation_key="op:create:1",
        request_hash="h1",
    )
    fact = proposed_fact(project_id=project.project_id)
    saved, _ = repo.create_fact(
        fact=fact,
        operation_key="op:propose:1",
        request_hash="h4",
    )
    # Delete the proposed fact
    del_raw = saved.model_dump(mode="json")
    del_raw.update({
        "version": saved.version + 1,
        "status": "deleted",
        "content": None,
        "terminal_event": {
            "status": "deleted",
            "actor": "local-user",
            "reason": "test delete",
            "occurred_at": NOW,
        },
        "updated_at": NOW,
        "record_hash": "0" * 64,
    })
    draft = ProjectFactRecord.model_validate(del_raw)
    del_raw["record_hash"] = compute_fact_hash(draft)
    deleted = ProjectFactRecord.model_validate(del_raw)

    result, _ = repo.replace_fact(
        fact=deleted,
        expected_version=saved.version,
        expected_hash=saved.record_hash,
        operation_key="op:delete:1",
        request_hash="h8",
    )
    assert result.status == "deleted"
    assert result.content is None
    assert result.content_hash == saved.content_hash


def test_project_not_found_raises(repo):
    with pytest.raises(ProjectNotFoundError):
        repo.get_project("project_" + "0" * 24)


def test_fact_not_found_raises(repo):
    with pytest.raises(ProjectFactNotFoundError):
        repo.get_fact("fact_" + "0" * 24)


def test_active_referenced_job_ids_excludes_non_chat_source(repo):
    project = make_project()
    repo.create_project(
        project=project,
        anchor_binding=_binding_for(project),
        operation_key="op:create:1",
        request_hash="h1",
    )
    # Create a manual confirmed fact
    fact = confirmed_fact(project_id=project.project_id)
    # Insert as proposed first
    proposed_raw = fact.model_dump(mode="json")
    proposed_raw.update({
        "version": 0,
        "status": "proposed",
        "authority": "unconfirmed_proposal",
        "confirmation": None,
        "record_hash": "0" * 64,
    })
    draft = ProjectFactRecord.model_validate(proposed_raw)
    proposed_raw["record_hash"] = compute_fact_hash(draft)
    proposed = ProjectFactRecord.model_validate(proposed_raw)

    saved, _ = repo.create_fact(
        fact=proposed,
        operation_key="op:propose:3",
        request_hash="h9",
    )

    # Confirm
    confirm_raw = saved.model_dump(mode="json")
    confirm_raw.update({
        "version": saved.version + 1,
        "status": "confirmed",
        "authority": "explicit_user",
        "confirmation": {
            "actor": "local-user",
            "reason": "test",
            "confirmed_at": NOW,
        },
        "updated_at": NOW,
        "record_hash": "0" * 64,
    })
    draft_c = ProjectFactRecord.model_validate(confirm_raw)
    confirm_raw["record_hash"] = compute_fact_hash(draft_c)
    confirmed = ProjectFactRecord.model_validate(confirm_raw)

    repo.replace_fact(
        fact=confirmed,
        expected_version=saved.version,
        expected_hash=saved.record_hash,
        operation_key="op:confirm:3",
        request_hash="h10",
    )

    # Manual source should not contribute to referenced job IDs
    ids = repo.active_referenced_job_ids()
    assert len(ids) == 0


def test_active_referenced_job_ids_includes_chat_source(repo):
    project = make_project()
    repo.create_project(
        project=project,
        anchor_binding=_binding_for(project),
        operation_key="op:create:1",
        request_hash="h1",
    )
    # Create a chat-backed confirmed fact
    content = make_text_content()
    from app.project_memory.identity import compute_content_hash

    raw = ProjectFactRecord(
        fact_id="fact_" + "5" * 24,
        project_id=project.project_id,
        version=0,
        status="proposed",
        authority="unconfirmed_proposal",
        content=content,
        content_hash=compute_content_hash(content),
        source=ChatUserMessageFactSource(
            actor="local-user",
            job_id="job-chat-source-001",
            message_id="msg-001",
            message_sequence=1,
            message_sha256="e" * 64,
        ),
        created_at=NOW,
        updated_at=NOW,
        record_hash="0" * 64,
    )
    payload = raw.model_dump(mode="json")
    payload["record_hash"] = compute_fact_hash(raw)
    proposed = ProjectFactRecord.model_validate(payload)

    saved, _ = repo.create_fact(
        fact=proposed,
        operation_key="op:propose:4",
        request_hash="h11",
    )

    # Confirm
    confirm_raw = saved.model_dump(mode="json")
    confirm_raw.update({
        "version": saved.version + 1,
        "status": "confirmed",
        "authority": "explicit_user",
        "confirmation": {
            "actor": "local-user",
            "reason": "test",
            "confirmed_at": NOW,
        },
        "updated_at": NOW,
        "record_hash": "0" * 64,
    })
    draft_c = ProjectFactRecord.model_validate(confirm_raw)
    confirm_raw["record_hash"] = compute_fact_hash(draft_c)
    confirmed = ProjectFactRecord.model_validate(confirm_raw)

    repo.replace_fact(
        fact=confirmed,
        expected_version=saved.version,
        expected_hash=saved.record_hash,
        operation_key="op:confirm:4",
        request_hash="h12",
    )

    ids = repo.active_referenced_job_ids()
    assert "job-chat-source-001" in ids
