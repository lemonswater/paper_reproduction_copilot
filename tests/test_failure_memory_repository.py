import pytest

from app.failure_memory.errors import FailureCaseConflictError
from app.failure_memory.identity import compute_case_hash
from app.failure_memory.repository import SqliteFailureCaseRepository
from tests.helpers.failure_memory import make_case


def _repository(tmp_path):
    repository = SqliteFailureCaseRepository(
        tmp_path / "failure-memory.sqlite"
    )
    repository.initialize()
    return repository


def test_create_and_idempotent_replay(tmp_path):
    repository = _repository(tmp_path)
    record = make_case()
    created = repository.create(
        record=record,
        operation_key="phase45:create:key-1",
        request_hash="a" * 64,
    )
    replay = repository.create(
        record=record,
        operation_key="phase45:create:key-1",
        request_hash="a" * 64,
    )
    assert created == replay


def test_idempotency_key_rejects_different_request(tmp_path):
    repository = _repository(tmp_path)
    repository.create(
        record=make_case(),
        operation_key="phase45:create:key-1",
        request_hash="a" * 64,
    )
    with pytest.raises(FailureCaseConflictError):
        repository.find_replay(
            operation_key="phase45:create:key-1",
            request_hash="b" * 64,
        )


def test_replace_uses_version_and_case_hash_cas(tmp_path):
    repository = _repository(tmp_path)
    current = repository.create(
        record=make_case(),
        operation_key="phase45:create:key-1",
        request_hash="a" * 64,
    )
    draft = current.model_copy(
        update={
            "version": 1,
            "status": "deprecated",
            "deprecation_reason": "test",
            "case_hash": "0" * 64,
        }
    )
    updated = draft.model_copy(
        update={"case_hash": compute_case_hash(draft)}
    )
    stored = repository.replace(
        record=updated,
        expected_version=0,
        expected_case_hash=current.case_hash,
        operation_key="phase45:deprecate:key-2",
        request_hash="b" * 64,
    )
    assert stored.status == "deprecated"
    assert stored.version == 1

    with pytest.raises(FailureCaseConflictError):
        repository.replace(
            record=updated,
            expected_version=0,
            expected_case_hash=current.case_hash,
            operation_key="phase45:deprecate:key-3",
            request_hash="c" * 64,
        )


def test_active_references_exclude_deprecated(tmp_path):
    repository = _repository(tmp_path)
    repository.create(
        record=make_case(status="run_verified"),
        operation_key="phase45:create:key-1",
        request_hash="a" * 64,
    )
    assert repository.active_referenced_job_ids() == {
        "job-failed",
        "job-fixed",
    }
