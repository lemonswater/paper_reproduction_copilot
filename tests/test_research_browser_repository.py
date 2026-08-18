from datetime import datetime, timedelta, timezone

import pytest

from app.research_browser.errors import ResearchConflict, ResearchIntegrityError
from app.research_browser.identity import request_sha256, sha256_value, without_hash
from app.research_browser.repository import SqliteResearchRepository

from tests.research_browser_helpers import (
    evidence_pack,
    research_request,
)


def test_submit_and_get(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    record, created = repo.submit(
        session_id="research_" + "a" * 24,
        idempotency_key="key-1",
        request=request,
        request_sha256=request_sha256(request),
        policy_sha256="1" * 64,
        actor="test",
    )
    assert created is True
    assert record.status == "submitted"
    assert record.version == 0
    fetched = repo.get(record.session_id)
    assert fetched.session_id == record.session_id


def test_idempotent_submit_returns_same_record(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    record1, created1 = repo.submit(
        session_id="research_" + "b" * 24,
        idempotency_key="key-2",
        request=request,
        request_sha256=request_sha256(request),
        policy_sha256="1" * 64,
        actor="test",
    )
    record2, created2 = repo.submit(
        session_id="research_" + "c" * 24,
        idempotency_key="key-2",
        request=request,
        request_sha256=request_sha256(request),
        policy_sha256="1" * 64,
        actor="test",
    )
    assert created1 is True
    assert created2 is False
    assert record1.session_id == record2.session_id


def test_same_key_different_request_raises_conflict(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request1 = research_request()
    repo.submit(
        session_id="research_" + "d" * 24,
        idempotency_key="key-3",
        request=request1,
        request_sha256=request_sha256(request1),
        policy_sha256="1" * 64,
        actor="test",
    )
    request2 = research_request(query="different query entirely")
    with pytest.raises(ResearchConflict):
        repo.submit(
            session_id="research_" + "e" * 24,
            idempotency_key="key-3",
            request=request2,
            request_sha256=request_sha256(request2),
            policy_sha256="1" * 64,
            actor="test",
        )


def test_start_requires_submitted_status(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    record, _ = repo.submit(
        session_id="research_" + "f" * 24,
        idempotency_key="key-4",
        request=request,
        request_sha256=request_sha256(request),
        policy_sha256="1" * 64,
        actor="test",
    )
    running = repo.start(
        session_id=record.session_id,
        expected_version=0,
        lease_token="rlease_" + "a" * 32,
        lease_seconds=60,
        actor="worker",
    )
    assert running.status == "running"
    assert running.lease_token is not None
    with pytest.raises(ResearchConflict):
        repo.start(
            session_id=record.session_id,
            expected_version=1,
            lease_token="rlease_" + "b" * 32,
            lease_seconds=60,
            actor="worker2",
        )


def test_complete_requires_current_lease(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    request_hash = request_sha256(request)
    record, _ = repo.submit(
        session_id="research_" + "1" * 24,
        idempotency_key="repo-1",
        request=request,
        request_sha256=request_hash,
        policy_sha256="1" * 64,
        actor="test",
    )
    repo.start(
        session_id=record.session_id,
        expected_version=record.version,
        lease_token="rlease_" + "c" * 32,
        lease_seconds=60,
        actor="worker:test",
    )
    with pytest.raises(ResearchConflict):
        repo.complete(
            session_id=record.session_id,
            lease_token="rlease_" + "d" * 32,
            pack=evidence_pack(
                session_id=record.session_id,
                request_hash=request_hash,
            ),
            actor="worker:stale",
        )
    assert repo.get(record.session_id).status == "running"


def test_complete_succeeds_with_correct_lease(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    request_hash = request_sha256(request)
    record, _ = repo.submit(
        session_id="research_" + "2" * 24,
        idempotency_key="key-5",
        request=request,
        request_sha256=request_hash,
        policy_sha256="1" * 64,
        actor="test",
    )
    lease = "rlease_" + "e" * 32
    repo.start(
        session_id=record.session_id,
        expected_version=0,
        lease_token=lease,
        lease_seconds=60,
        actor="worker",
    )
    pack = evidence_pack(
        session_id=record.session_id,
        request_hash=request_hash,
    )
    completed = repo.complete(
        session_id=record.session_id,
        lease_token=lease,
        pack=pack,
        actor="worker",
    )
    assert completed.status == "succeeded"
    assert completed.pack_id is not None
    assert completed.lease_token is None


def test_fail_requires_current_lease(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    record, _ = repo.submit(
        session_id="research_" + "3" * 24,
        idempotency_key="key-6",
        request=request,
        request_sha256=request_sha256(request),
        policy_sha256="1" * 64,
        actor="test",
    )
    repo.start(
        session_id=record.session_id,
        expected_version=0,
        lease_token="rlease_" + "f" * 32,
        lease_seconds=60,
        actor="worker",
    )
    with pytest.raises(ResearchConflict):
        repo.fail(
            session_id=record.session_id,
            lease_token="rlease_" + "1" * 32,
            error_code="SOME_ERROR",
            retryable=True,
            actor="other",
        )


def test_cancel_rejected_when_running(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    record, _ = repo.submit(
        session_id="research_" + "4" * 24,
        idempotency_key="key-7",
        request=request,
        request_sha256=request_sha256(request),
        policy_sha256="1" * 64,
        actor="test",
    )
    repo.start(
        session_id=record.session_id,
        expected_version=0,
        lease_token="rlease_" + "2" * 32,
        lease_seconds=60,
        actor="worker",
    )
    with pytest.raises(ResearchConflict):
        repo.cancel(
            session_id=record.session_id,
            expected_version=1,
            actor="user",
        )


def test_requeue_expired_lease(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    record, _ = repo.submit(
        session_id="research_" + "5" * 24,
        idempotency_key="repo-2",
        request=request,
        request_sha256=request_sha256(request),
        policy_sha256="1" * 64,
        actor="test",
    )
    repo.start(
        session_id=record.session_id,
        expected_version=0,
        lease_token="rlease_" + "3" * 32,
        lease_seconds=30,
        actor="worker:test",
    )
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    assert repo.requeue_expired(now=future, actor="reconciler") == 1
    recovered = repo.get(record.session_id)
    assert recovered.status == "failed_retryable"
    assert recovered.lease_token is None


def test_get_pack_returns_validated_pack(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    request_hash = request_sha256(request)
    record, _ = repo.submit(
        session_id="research_" + "6" * 24,
        idempotency_key="key-8",
        request=request,
        request_sha256=request_hash,
        policy_sha256="1" * 64,
        actor="test",
    )
    lease = "rlease_" + "4" * 32
    repo.start(
        session_id=record.session_id,
        expected_version=0,
        lease_token=lease,
        lease_seconds=60,
        actor="worker",
    )
    pack = evidence_pack(
        session_id=record.session_id,
        request_hash=request_hash,
    )
    repo.complete(
        session_id=record.session_id,
        lease_token=lease,
        pack=pack,
        actor="worker",
    )
    fetched = repo.get_pack(record.session_id)
    assert fetched.pack_id == pack.pack_id
    assert fetched.pack_sha256 == pack.pack_sha256


def test_list_packs_for_job_returns_succeeded(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request(job_id="job-list-packs")
    request_hash = request_sha256(request)
    record, _ = repo.submit(
        session_id="research_" + "7" * 24,
        idempotency_key="key-9",
        request=request,
        request_sha256=request_hash,
        policy_sha256="1" * 64,
        actor="test",
    )
    lease = "rlease_" + "5" * 32
    repo.start(
        session_id=record.session_id,
        expected_version=0,
        lease_token=lease,
        lease_seconds=60,
        actor="worker",
    )
    pack = evidence_pack(
        session_id=record.session_id,
        request_hash=request_hash,
    )
    repo.complete(
        session_id=record.session_id,
        lease_token=lease,
        pack=pack,
        actor="worker",
    )
    packs = repo.list_packs_for_job(job_id="job-list-packs", limit=10)
    assert len(packs) == 1
    assert packs[0].pack_id == pack.pack_id


def test_list_packs_for_job_excludes_non_succeeded(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request(job_id="job-exclude")
    record, _ = repo.submit(
        session_id="research_" + "8" * 24,
        idempotency_key="key-10",
        request=request,
        request_sha256=request_sha256(request),
        policy_sha256="1" * 64,
        actor="test",
    )
    packs = repo.list_packs_for_job(job_id="job-exclude", limit=10)
    assert len(packs) == 0


def test_record_resource_link_is_idempotent(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    request_hash = request_sha256(request)
    record, _ = repo.submit(
        session_id="research_" + "9" * 24,
        idempotency_key="key-11",
        request=request,
        request_sha256=request_hash,
        policy_sha256="1" * 64,
        actor="test",
    )
    lease = "rlease_" + "6" * 32
    repo.start(
        session_id=record.session_id,
        expected_version=0,
        lease_token=lease,
        lease_seconds=60,
        actor="worker",
    )
    pack = evidence_pack(
        session_id=record.session_id,
        request_hash=request_hash,
    )
    repo.complete(
        session_id=record.session_id,
        lease_token=lease,
        pack=pack,
        actor="worker",
    )
    link_id_1 = repo.record_resource_link(
        session_id=record.session_id,
        candidate_id="rcand_" + "a" * 24,
        candidate_sha256="1" * 64,
        pack_sha256=pack.pack_sha256,
        idempotency_key="research-resource:test:rcand_a",
        resource_id="res_1",
    )
    link_id_2 = repo.record_resource_link(
        session_id=record.session_id,
        candidate_id="rcand_" + "a" * 24,
        candidate_sha256="1" * 64,
        pack_sha256=pack.pack_sha256,
        idempotency_key="research-resource:test:rcand_a",
        resource_id="res_2",
    )
    assert link_id_1 == link_id_2


def test_record_resource_link_rejects_hash_mismatch(tmp_path) -> None:
    repo = SqliteResearchRepository(tmp_path / "r.sqlite")
    repo.initialize()
    request = research_request()
    request_hash = request_sha256(request)
    record, _ = repo.submit(
        session_id="research_" + "ab" * 12,
        idempotency_key="key-12",
        request=request,
        request_sha256=request_hash,
        policy_sha256="1" * 64,
        actor="test",
    )
    lease = "rlease_" + "7" * 32
    repo.start(
        session_id=record.session_id,
        expected_version=0,
        lease_token=lease,
        lease_seconds=60,
        actor="worker",
    )
    pack = evidence_pack(
        session_id=record.session_id,
        request_hash=request_hash,
    )
    repo.complete(
        session_id=record.session_id,
        lease_token=lease,
        pack=pack,
        actor="worker",
    )
    # First insert succeeds
    repo.record_resource_link(
        session_id=record.session_id,
        candidate_id="rcand_" + "b" * 24,
        candidate_sha256="1" * 64,
        pack_sha256=pack.pack_sha256,
        idempotency_key="research-resource:test:rcand_b_v1",
        resource_id="res_3",
    )
    # Second insert with different hash for same candidate should fail
    with pytest.raises(ResearchConflict):
        repo.record_resource_link(
            session_id=record.session_id,
            candidate_id="rcand_" + "b" * 24,
            candidate_sha256="2" * 64,
            pack_sha256=pack.pack_sha256,
            idempotency_key="research-resource:test:rcand_b_v2",
            resource_id="res_4",
        )
