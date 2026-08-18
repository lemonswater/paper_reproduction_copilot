from app.chat.context import ChatContextBuilder, _keywords
from app.comparison.schemas import (
    ComparisonListItem,
    ComparisonListResponse,
)
from tests.helpers.comparison import make_report


class FakeComparisonReader:
    def __init__(self):
        self.report = make_report()

    def get(self, comparison_id: str):
        assert comparison_id == self.report.comparison_id
        return self.report

    def list_for_job(self, job_id: str, *, limit: int = 100):
        assert job_id == "job-target"
        assert limit == 3
        item = ComparisonListItem.from_report(self.report)
        return ComparisonListResponse(items=[item], count=1)


def test_chat_builds_bounded_comparison_source() -> None:
    reader = FakeComparisonReader()
    builder = ChatContextBuilder(
        interaction=object(),
        artifact_catalog=object(),
        artifacts_to_open=1,
        source_limit=8,
        artifact_max_bytes=4096,
        total_context_chars=20000,
        log_max_bytes=4096,
        comparison_reader=reader,
        comparison_limit=3,
        comparison_max_chars=12000,
    )

    sources = builder._comparison_sources(
        job_id="job-target",
        keywords=_keywords("比较两个 run 的差异"),
    )

    assert len(sources) == 1
    source = sources[0]
    assert source.citation.source_type == "comparison"
    assert source.citation.citation_id == (
        f"comparison:{reader.report.comparison_id}"
    )
    assert source.citation.comparison_hash == reader.report.comparison_hash
    assert source.citation.base_job_id == "job-base"
    assert source.citation.target_job_id == "job-target"
    assert "comparison_hash" in source.content
    assert "/data/" not in source.content


def test_chat_skips_comparison_when_projection_exceeds_budget() -> None:
    reader = FakeComparisonReader()
    builder = ChatContextBuilder(
        interaction=object(),
        artifact_catalog=object(),
        artifacts_to_open=1,
        source_limit=8,
        artifact_max_bytes=4096,
        total_context_chars=20000,
        log_max_bytes=4096,
        comparison_reader=reader,
        comparison_limit=3,
        comparison_max_chars=1,
    )
    assert builder._comparison_sources(
        job_id="job-target",
        keywords=set(),
    ) == []
