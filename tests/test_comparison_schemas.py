import pytest
from pydantic import ValidationError

from app.comparison.identity import (
    compute_comparison_hash,
    validate_report_identity,
)
from app.comparison.schemas import ComparisonCreateRequest
from tests.helpers.comparison import make_report


def test_comparison_request_rejects_same_job() -> None:
    with pytest.raises(ValidationError):
        ComparisonCreateRequest(
            base_job_id="job-1",
            target_job_id="job-1",
        )


def test_comparison_hash_ignores_created_at() -> None:
    first = make_report(created_at="2026-08-09T00:00:00+00:00")
    second = first.model_copy(
        update={"created_at": "2026-08-10T00:00:00+00:00"}
    )
    assert compute_comparison_hash(first) == compute_comparison_hash(second)


def test_report_identity_detects_snapshot_tampering() -> None:
    report = make_report()
    tampered_base = report.base.model_copy(
        update={"experiment_goal": "被篡改的目标"}
    )
    tampered = report.model_copy(update={"base": tampered_base})
    with pytest.raises(Exception, match="Snapshot hash"):
        validate_report_identity(tampered)
