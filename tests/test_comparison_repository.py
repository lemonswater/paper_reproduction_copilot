import json

import pytest

from app.comparison.errors import (
    ComparisonIntegrityError,
    ComparisonNotFoundError,
)
from app.comparison.repository import FileComparisonRepository
from tests.helpers.comparison import make_report


def _repository(tmp_path):
    return FileComparisonRepository(
        tmp_path / "project-comparisons",
        max_report_bytes=1024 * 1024,
        list_scan_limit=100,
        staging_ttl_seconds=60,
    )


def test_repository_round_trip_is_idempotent(tmp_path) -> None:
    repository = _repository(tmp_path)
    report = make_report()

    first = repository.save(report)
    second = repository.save(report)

    assert first.comparison_id == second.comparison_id
    assert repository.get(report.comparison_id) == report
    directory = repository.root / report.comparison_id
    assert (directory / "comparison.json").is_file()
    assert (directory / "comparison.md").is_file()
    assert list(repository.staging_root.iterdir()) == []


def test_repository_detects_json_tampering(tmp_path) -> None:
    repository = _repository(tmp_path)
    report = repository.save(make_report())
    path = repository.root / report.comparison_id / "comparison.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["base"]["experiment_goal"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ComparisonIntegrityError):
        repository.get(report.comparison_id)


def test_repository_rejects_path_like_id(tmp_path) -> None:
    repository = _repository(tmp_path)
    with pytest.raises(ComparisonNotFoundError):
        repository.get("../../runs/run-1")


def test_list_for_job_returns_both_comparison_sides(tmp_path) -> None:
    repository = _repository(tmp_path)
    report = repository.save(make_report())

    base_page = repository.list_for_job("job-base")
    target_page = repository.list_for_job("job-target")

    assert [item.comparison_id for item in base_page.items] == [
        report.comparison_id
    ]
    assert [item.comparison_id for item in target_page.items] == [
        report.comparison_id
    ]
