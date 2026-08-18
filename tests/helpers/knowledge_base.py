from __future__ import annotations

import hashlib
import io
import json
from types import SimpleNamespace

from app.knowledge_base.identity import (
    build_entity_id,
    build_evidence_ref_id,
    build_provenance_id,
    build_relation_id,
    entity_record_hash,
    graph_batch_hash,
    normalize_knowledge_key,
    provenance_record_hash,
    relation_record_hash,
    sha256_value,
    source_snapshot_hash,
)
from app.knowledge_base.schemas import (
    KnowledgeEntityRecord,
    KnowledgeEvidenceRef,
    KnowledgeGraphBatch,
    KnowledgeIngestionRecord,
    KnowledgeProvenanceRecord,
    KnowledgeRelationRecord,
    KnowledgeSourceSnapshot,
)
from app.paper.schemas import (
    PaperDocument,
    PaperEvidence,
    PaperFactRecord,
    PaperSection,
)
from app.schemas import PaperSummary


NOW = "2026-08-11T00:00:00+00:00"


class FakeVerifiedRuns:
    def __init__(self, evidence) -> None:
        self.evidence = evidence

    def read(self, job_id: str):
        assert job_id == self.evidence.job.job_id
        return self.evidence


class FakeArtifactCatalog:
    def __init__(self, views, blobs) -> None:
        self.views = {item.artifact_id: item for item in views}
        self.blobs = dict(blobs)

    def open(self, *, job, artifact_id: str):
        del job
        view = self.views[artifact_id]
        raw = self.blobs[artifact_id]
        descriptor = SimpleNamespace(
            artifact_id=view.artifact_id,
            relative_path=view.relative_path,
            run_id=view.run_id,
            sha256=view.sha256,
            size_bytes=view.size_bytes,
        )
        stat = SimpleNamespace(
            sha256=view.sha256,
            size_bytes=view.size_bytes,
        )
        return SimpleNamespace(
            artifact=SimpleNamespace(descriptor=descriptor),
            blob=SimpleNamespace(stat=stat, body=io.BytesIO(raw)),
        )


def _view(artifact_id: str, path: str, run_id: str, raw: bytes):
    return SimpleNamespace(
        artifact_id=artifact_id,
        relative_path=path,
        run_id=run_id,
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
    )


def make_source_fixture():
    paper_sha = "a" * 64
    document = PaperDocument(
        document_id="paper-doc-a",
        source_path="pdf/paper-a.pdf",
        source_sha256=paper_sha,
        parser_version="phase19-v1",
        page_count=8,
        indexed_page_count=8,
        block_count=20,
        section_count=1,
        blocks_artifact="analysis/paper_blocks.jsonl",
        sections_artifact="analysis/paper_sections.json",
        parse_report_artifact="analysis/paper_parse_report.json",
    )
    section = PaperSection(
        section_id="section-method",
        number="3",
        title="Method",
        normalized_title="method",
        level=1,
        kind="method",
        page_start=3,
        page_end=4,
        block_ids=["block-1"],
        content_hash="b" * 64,
    )
    evidence = PaperEvidence(
        evidence_id="paper-evidence-1",
        document_id=document.document_id,
        section_id=section.section_id,
        block_ids=["block-1"],
        page_start=3,
        page_end=3,
        text="PST convolution aggregates local point tubes.",
        summary="local spatio-temporal aggregation",
        content_hash="c" * 64,
        confidence=0.9,
    )
    fact = PaperFactRecord(
        fact_id="fact-method-1",
        category="method_module",
        name="PST convolution",
        value="Aggregates local point tubes.",
        normalized_key="pst convolution",
        evidence=evidence,
    )
    summary = PaperSummary(
        title="Paper A",
        research_problem="Model dynamic point clouds.",
        core_idea="Use local spatio-temporal aggregation.",
    )
    payloads = {
        "analysis/paper_document.json": document.model_dump(mode="json"),
        "analysis/paper_sections.json": [section.model_dump(mode="json")],
        "analysis/paper_fact_index.json": [fact.model_dump(mode="json")],
        "analysis/paper_summary.json": summary.model_dump(mode="json"),
    }
    blobs = {
        path: json.dumps(payload).encode("utf-8")
        for path, payload in payloads.items()
    }
    views = [
        _view(f"artifact-{index}", path, "run-a", raw)
        for index, (path, raw) in enumerate(blobs.items(), start=1)
    ]
    evidence_run = SimpleNamespace(
        job=SimpleNamespace(job_id="job-a", run_id="run-a"),
        workspace=SimpleNamespace(
            manifest_hash="d" * 64,
            entries=[SimpleNamespace(role="paper", sha256=paper_sha)],
            repository=SimpleNamespace(commit_sha="e" * 40),
        ),
        artifacts=tuple(views),
    )
    catalog = FakeArtifactCatalog(
        views,
        {view.artifact_id: blobs[view.relative_path] for view in views},
    )
    return evidence_run, catalog


def _entity(*, kind: str, scope: str, key: str, name: str):
    canonical = normalize_knowledge_key(key)
    draft = KnowledgeEntityRecord(
        entity_id=build_entity_id(
            kind=kind,
            scope_key=scope,
            canonical_key=canonical,
        ),
        kind=kind,
        scope_key=scope,
        canonical_key=canonical,
        display_name=name,
        record_hash="0" * 64,
        created_at=NOW,
    )
    return draft.model_copy(
        update={"record_hash": entity_record_hash(draft)}
    )


def _relation(*, relation_type: str, source: str, target: str):
    draft = KnowledgeRelationRecord(
        relation_id=build_relation_id(
            relation_type=relation_type,
            source_entity_id=source,
            target_entity_id=target,
        ),
        relation_type=relation_type,
        source_entity_id=source,
        target_entity_id=target,
        status="asserted",
        authority="deterministic_source",
        confidence=1.0,
        relation_hash="0" * 64,
        version=0,
        created_at=NOW,
        updated_at=NOW,
    )
    return draft.model_copy(
        update={"relation_hash": relation_record_hash(draft)}
    )


def make_graph_batch(
    *,
    job_id: str,
    paper_name: str,
    concept_name: str,
    dataset_name: str | None = None,
) -> KnowledgeGraphBatch:
    paper_sha = sha256_value({"paper": paper_name})
    snapshot_draft = KnowledgeSourceSnapshot(
        snapshot_id="kgsnap_" + "0" * 24,
        job_id=job_id,
        run_id=f"run-{job_id}",
        paper_sha256=paper_sha,
        repository_commit="e" * 40,
        workspace_manifest_hash=sha256_value({"job": job_id}),
        artifact_hashes={
            "analysis/paper_document.json": "1" * 64,
            "analysis/paper_sections.json": "2" * 64,
            "analysis/paper_fact_index.json": "3" * 64,
        },
        snapshot_hash="0" * 64,
    )
    snapshot_hash = source_snapshot_hash(snapshot_draft)
    snapshot = snapshot_draft.model_copy(
        update={
            "snapshot_id": f"kgsnap_{snapshot_hash[:24]}",
            "snapshot_hash": snapshot_hash,
        }
    )
    paper = _entity(
        kind="paper",
        scope=paper_sha,
        key=paper_sha,
        name=paper_name,
    )
    concept = _entity(
        kind="concept_instance",
        scope=paper.entity_id,
        key=f"{concept_name}|fact-method",
        name=concept_name,
    )
    entities = [paper, concept]
    relations = []
    if dataset_name is not None:
        dataset = _entity(
            kind="dataset_mention",
            scope=paper.entity_id,
            key=f"{dataset_name}|fact-dataset",
            name=dataset_name,
        )
        entities.append(dataset)
        relations.append(
            _relation(
                relation_type="paper_uses_dataset",
                source=paper.entity_id,
                target=dataset.entity_id,
            )
        )

    view_hash = "3" * 64
    evidence_ref = KnowledgeEvidenceRef(
        evidence_ref_id=build_evidence_ref_id(
            artifact_id=f"artifact-{job_id}",
            content_hash=paper_sha,
            locator={"document_id": f"doc-{job_id}"},
        ),
        kind="paper_artifact",
        job_id=job_id,
        run_id=snapshot.run_id,
        artifact_id=f"artifact-{job_id}",
        artifact_path="analysis/paper_fact_index.json",
        artifact_sha256=view_hash,
        content_hash=paper_sha,
        document_id=f"doc-{job_id}",
        paper_sha256=paper_sha,
    )
    provenance = []
    for subject_kind, subject_id in [
        *[("entity", item.entity_id) for item in entities],
        *[("relation", item.relation_id) for item in relations],
    ]:
        draft = KnowledgeProvenanceRecord(
            provenance_id=build_provenance_id(
                subject_id=subject_id,
                source_snapshot_id=snapshot.snapshot_id,
                evidence_ref_ids=[evidence_ref.evidence_ref_id],
            ),
            subject_kind=subject_kind,
            subject_id=subject_id,
            source_snapshot_id=snapshot.snapshot_id,
            authority="deterministic_source",
            evidence=[evidence_ref],
            provenance_hash="0" * 64,
            created_at=NOW,
        )
        provenance.append(
            draft.model_copy(
                update={
                    "provenance_hash": provenance_record_hash(draft)
                }
            )
        )
    return KnowledgeGraphBatch(
        source=snapshot,
        entities=entities,
        relations=relations,
        provenance=provenance,
    )


def ingest_batch(repository, batch, *, key: str):
    request_hash = sha256_value(
        {"operation": "test-ingest", "snapshot": batch.source.snapshot_hash}
    )
    ingestion = KnowledgeIngestionRecord(
        ingestion_id=f"kging_{batch.source.snapshot_hash[:24]}",
        source=batch.source,
        status="active",
        entity_count=0,
        relation_count=0,
        created_entity_count=0,
        created_relation_count=0,
        batch_hash=graph_batch_hash(batch),
        request_hash=request_hash,
        created_by="test",
        created_at=NOW,
    )
    return repository.ingest_batch(
        batch=batch,
        ingestion=ingestion,
        idempotency_key=key,
    )
