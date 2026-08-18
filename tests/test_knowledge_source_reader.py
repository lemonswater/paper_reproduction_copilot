import pytest

from app.knowledge_base.errors import KnowledgeIntegrityError
from app.knowledge_base.source_reader import KnowledgeSourceReader
from tests.helpers.knowledge_base import (
    FakeVerifiedRuns,
    make_source_fixture,
)


def _reader(evidence, catalog):
    return KnowledgeSourceReader(
        verified_runs=FakeVerifiedRuns(evidence),
        artifact_catalog=catalog,
        max_artifact_bytes=2 * 1024 * 1024,
        max_sections=100,
        max_facts=100,
        max_mappings=100,
    )


def test_reader_loads_only_fixed_verified_artifacts():
    evidence, catalog = make_source_fixture()
    bundle = _reader(evidence, catalog).read("job-a")
    assert bundle.document.source_sha256 == "a" * 64
    assert bundle.sections[0].section_id == "section-method"
    assert bundle.facts[0].name == "PST convolution"


def test_reader_rejects_tampered_blob():
    evidence, catalog = make_source_fixture()
    first_id = evidence.artifacts[0].artifact_id
    catalog.blobs[first_id] += b"tampered"
    with pytest.raises(KnowledgeIntegrityError):
        _reader(evidence, catalog).read("job-a")


def test_reader_rejects_workspace_paper_identity_drift():
    evidence, catalog = make_source_fixture()
    evidence.workspace.entries[0].sha256 = "f" * 64
    with pytest.raises(KnowledgeIntegrityError):
        _reader(evidence, catalog).read("job-a")
