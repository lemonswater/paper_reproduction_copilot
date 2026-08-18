from app.failure_memory.repository import SqliteFailureCaseRepository
from app.failure_memory.retrieval import FailureCaseRetriever
from app.failure_memory.schemas import FailureQuery
from tests.helpers.failure_memory import (
    make_case,
    make_environment,
    make_signature,
)


def _save(repository, record, index):
    repository.create(
        record=record,
        operation_key=f"phase45:create:{index}",
        request_hash=f"{index:064x}",
    )


def test_exact_verified_case_ranks_first(tmp_path):
    repository = SqliteFailureCaseRepository(tmp_path / "cases.sqlite")
    repository.initialize()
    _save(
        repository,
        make_case(
            case_id="failure_" + "1" * 24,
            source_job_id="job-verified",
            status="run_verified",
        ),
        1,
    )
    _save(
        repository,
        make_case(
            case_id="failure_" + "2" * 24,
            source_job_id="job-candidate",
            status="candidate",
        ),
        2,
    )
    retriever = FailureCaseRetriever(
        repository=repository,
        candidate_limit=20,
        top_k=5,
        minimum_score=0.0,
    )
    pack = retriever.search(
        FailureQuery(
            signature=make_signature(),
            environment=make_environment(),
        )
    )
    assert pack.items[0].status == "run_verified"
    assert pack.items[0].authority == "verified_precedent"
    assert pack.items[0].compatibility == "exact_applicable"


def test_environment_drift_downgrades_compatibility(tmp_path):
    repository = SqliteFailureCaseRepository(tmp_path / "cases.sqlite")
    repository.initialize()
    _save(repository, make_case(status="run_verified"), 1)
    retriever = FailureCaseRetriever(
        repository=repository,
        candidate_limit=20,
        top_k=5,
        minimum_score=0.0,
    )
    pack = retriever.search(
        FailureQuery(
            signature=make_signature(),
            environment=make_environment(
                profile_fingerprint="different-profile"
            ),
        )
    )
    assert pack.items[0].authority == "verified_precedent"
    assert pack.items[0].compatibility == "review_required"


def test_deprecated_case_is_not_returned(tmp_path):
    repository = SqliteFailureCaseRepository(tmp_path / "cases.sqlite")
    repository.initialize()
    _save(repository, make_case(status="deprecated"), 1)
    retriever = FailureCaseRetriever(
        repository=repository,
        candidate_limit=20,
        top_k=5,
        minimum_score=0.0,
    )
    pack = retriever.search(
        FailureQuery(
            signature=make_signature(),
            environment=make_environment(),
        )
    )
    assert pack.items == []
