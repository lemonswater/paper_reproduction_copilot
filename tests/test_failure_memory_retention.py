from app.failure_memory.repository import SqliteFailureCaseRepository
from app.retention.service import RetentionService
from tests.helpers.failure_memory import make_case


class FakeRetentionHolds:
    def __init__(self, job_ids):
        self.job_ids = set(job_ids)

    def held_job_ids(self):
        return set(self.job_ids)


class FakeFailureReferences:
    def __init__(self, job_ids):
        self.job_ids = set(job_ids)

    def active_referenced_job_ids(self):
        return set(self.job_ids)


class FakeEmptyReferences:
    def active_referenced_job_ids(self):
        return set()


def _retention_for_blocked_ids(*, holds, memory):
    # 这个单元测试只调用无副作用的 _blocked_job_ids，
    # 不绕过生产构造器去调用 create_plan/execute_plan。
    service = object.__new__(RetentionService)
    service.repository = FakeRetentionHolds(holds)
    service.failure_memory = FakeFailureReferences(memory)
    service.project_memory = FakeEmptyReferences()
    service.knowledge_memory = FakeEmptyReferences()
    return service


def test_retention_unions_explicit_holds_and_failure_references():
    service = _retention_for_blocked_ids(
        holds={"job-manual-hold"},
        memory={"job-failed", "job-fixed"},
    )
    assert service._blocked_job_ids() == {
        "job-manual-hold",
        "job-failed",
        "job-fixed",
    }


def test_verified_case_references_source_and_child(tmp_path):
    repository = SqliteFailureCaseRepository(tmp_path / "cases.sqlite")
    repository.initialize()
    repository.create(
        record=make_case(status="run_verified"),
        operation_key="phase45:create:retention",
        request_hash="1" * 64,
    )
    assert repository.active_referenced_job_ids() == {
        "job-failed",
        "job-fixed",
    }


def test_deprecated_case_releases_retention_edges(tmp_path):
    repository = SqliteFailureCaseRepository(tmp_path / "cases.sqlite")
    repository.initialize()
    repository.create(
        record=make_case(status="deprecated"),
        operation_key="phase45:create:deprecated",
        request_hash="2" * 64,
    )
    assert repository.active_referenced_job_ids() == set()
