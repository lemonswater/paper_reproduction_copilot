import pytest
from pydantic import ValidationError

from app.research_browser.schemas import (
    ResearchEvidencePack,
    ResearchRequest,
    ResearchSynthesisDraft,
)


def test_request_normalizes_and_deduplicates_hosts() -> None:
    request = ResearchRequest(
        query="  PSTNet   official paper  ",
        purpose="  verify   method  ",
        allowed_hosts=["EXAMPLE.ORG", "example.org"],
    )
    assert request.query == "PSTNet official paper"
    assert request.allowed_hosts == ["example.org"]


def test_request_rejects_url_in_host_scope() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(
            query="PSTNet",
            purpose="verify paper",
            allowed_hosts=["https://example.org"],
        )


def test_request_rejects_control_characters() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(
            query="PSTNet\x00paper",
            purpose="verify",
        )


def test_request_rejects_empty_query() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(
            query="",
            purpose="verify",
        )


def test_synthesis_draft_rejects_duplicate_citation_ids() -> None:
    with pytest.raises(ValidationError):
        ResearchSynthesisDraft(
            answer="test",
            citation_ids=["rcit_a", "rcit_a"],
        )


def test_synthesis_draft_rejects_duplicate_resource_candidate_ids() -> None:
    with pytest.raises(ValidationError):
        ResearchSynthesisDraft(
            answer="test",
            citation_ids=["rcit_a"],
            resource_candidate_ids=["rcand_b", "rcand_b"],
        )


def test_request_defaults() -> None:
    request = ResearchRequest(
        query="test query",
        purpose="test purpose",
    )
    assert request.schema_version == "phase51-v1"
    assert request.max_results == 8
    assert request.max_sources == 3
    assert request.allow_pdf is True
    assert request.allowed_hosts == []


def test_request_rejects_too_many_hosts() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(
            query="test",
            purpose="test",
            allowed_hosts=[f"h{i}.com" for i in range(13)],
        )
