from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.knowledge_base.errors import KnowledgeIntegrityError
from app.knowledge_base.identity import (
    build_entity_id,
    build_evidence_ref_id,
    build_provenance_id,
    build_relation_id,
    entity_record_hash,
    normalize_knowledge_key,
    provenance_record_hash,
    relation_record_hash,
    sha256_value,
    source_snapshot_hash,
    utc_now,
)
from app.knowledge_base.schemas import (
    KnowledgeEntityKind,
    KnowledgeEntityRecord,
    KnowledgeEvidenceRef,
    KnowledgeGraphBatch,
    KnowledgeProvenanceRecord,
    KnowledgeRelationRecord,
    KnowledgeRelationStatus,
    KnowledgeRelationType,
    KnowledgeSourceSnapshot,
)
from app.knowledge_base.source_reader import (
    PAPER_CODE_MAPPING_PATH,
    PAPER_DOCUMENT_PATH,
    PAPER_FACT_INDEX_PATH,
    PAPER_SECTIONS_PATH,
    KnowledgeSourceBundle,
)
from app.paper.schemas import PaperFactRecord, PaperSection
from app.schemas import CodeCandidate, Evidence, ModuleMapping


FACT_ENTITY_KINDS: dict[str, KnowledgeEntityKind] = {
    "method_module": "concept_instance",
    "dataset": "dataset_mention",
    "metric": "metric_mention",
}

FACT_RELATIONS: dict[str, KnowledgeRelationType] = {
    "method_module": "claim_describes_concept",
    "dataset": "paper_uses_dataset",
    "metric": "paper_reports_metric",
}

CONFIDENCE_VALUES = {
    "low": 0.40,
    "medium": 0.70,
    "high": 0.90,
}


class KnowledgeProjector:
    """将可信运行 Artifact 确定性投影为 source-scoped Evidence Graph。"""

    @staticmethod
    def _source_snapshot(
        bundle: KnowledgeSourceBundle,
    ) -> KnowledgeSourceSnapshot:
        artifact_hashes = {
            path: view.sha256
            for path, view in sorted(bundle.artifacts.items())
            if path in {
                PAPER_DOCUMENT_PATH,
                PAPER_SECTIONS_PATH,
                PAPER_FACT_INDEX_PATH,
                "analysis/paper_summary.json",
                PAPER_CODE_MAPPING_PATH,
            }
        }
        draft = KnowledgeSourceSnapshot(
            snapshot_id="kgsnap_" + "0" * 24,
            job_id=bundle.verified_run.job.job_id,
            run_id=bundle.verified_run.job.run_id,
            paper_sha256=bundle.document.source_sha256,
            repository_commit=(
                bundle.verified_run.workspace.repository.commit_sha
            ),
            workspace_manifest_hash=(
                bundle.verified_run.workspace.manifest_hash
            ),
            artifact_hashes=artifact_hashes,
            snapshot_hash="0" * 64,
        )
        digest = source_snapshot_hash(draft)
        return draft.model_copy(
            update={
                "snapshot_id": f"kgsnap_{digest[:24]}",
                "snapshot_hash": digest,
            }
        )

    @staticmethod
    def _entity(
        *,
        kind: KnowledgeEntityKind,
        scope_key: str,
        canonical_key: str,
        display_name: str,
        description: str | None,
        attributes: dict,
        now: str,
    ) -> KnowledgeEntityRecord:
        canonical = normalize_knowledge_key(canonical_key)
        draft = KnowledgeEntityRecord(
            entity_id=build_entity_id(
                kind=kind,
                scope_key=scope_key,
                canonical_key=canonical,
            ),
            kind=kind,
            scope_key=scope_key,
            canonical_key=canonical,
            display_name=display_name.strip(),
            description=description.strip() if description else None,
            attributes=attributes,
            record_hash="0" * 64,
            created_at=now,
        )
        return draft.model_copy(
            update={"record_hash": entity_record_hash(draft)}
        )

    @staticmethod
    def _relation(
        *,
        relation_type: KnowledgeRelationType,
        source_entity_id: str,
        target_entity_id: str,
        status: KnowledgeRelationStatus,
        confidence: float,
        proposal_reason: str | None = None,
        now: str,
    ) -> KnowledgeRelationRecord:
        source_id = source_entity_id
        target_id = target_entity_id
        if relation_type == "equivalent_to":
            source_id, target_id = sorted([source_id, target_id])
        authority = (
            "deterministic_source"
            if status == "asserted"
            else "model_candidate"
        )
        draft = KnowledgeRelationRecord(
            relation_id=build_relation_id(
                relation_type=relation_type,
                source_entity_id=source_id,
                target_entity_id=target_id,
            ),
            relation_type=relation_type,
            source_entity_id=source_id,
            target_entity_id=target_id,
            status=status,
            authority=authority,
            confidence=confidence,
            relation_hash="0" * 64,
            version=0,
            created_at=now,
            updated_at=now,
            proposal_reason=proposal_reason,
        )
        return draft.model_copy(
            update={"relation_hash": relation_record_hash(draft)}
        )

    @staticmethod
    def _paper_ref(
        *,
        bundle: KnowledgeSourceBundle,
        artifact_path: str,
        content_hash: str,
        section_id: str | None = None,
        block_ids: list[str] | None = None,
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> KnowledgeEvidenceRef:
        view = bundle.artifacts[artifact_path]
        locator = {
            "document_id": bundle.document.document_id,
            "section_id": section_id,
            "block_ids": sorted(block_ids or []),
            "page_start": page_start,
            "page_end": page_end,
        }
        return KnowledgeEvidenceRef(
            evidence_ref_id=build_evidence_ref_id(
                artifact_id=view.artifact_id,
                content_hash=content_hash,
                locator=locator,
            ),
            kind="paper_artifact",
            job_id=bundle.verified_run.job.job_id,
            run_id=bundle.verified_run.job.run_id,
            artifact_id=view.artifact_id,
            artifact_path=view.relative_path,
            artifact_sha256=view.sha256,
            content_hash=content_hash,
            document_id=bundle.document.document_id,
            paper_sha256=bundle.document.source_sha256,
            section_id=section_id,
            block_ids=sorted(block_ids or []),
            page_start=page_start,
            page_end=page_end,
        )

    @staticmethod
    def _code_ref(
        *,
        bundle: KnowledgeSourceBundle,
        evidence: Evidence,
    ) -> KnowledgeEvidenceRef:
        required = {
            "repo_fingerprint": evidence.repo_fingerprint,
            "repo_revision": evidence.repo_revision,
            "file_path": evidence.source_path,
            "file_sha256": evidence.file_sha256,
            "start_line": evidence.start_line,
            "end_line": evidence.end_line,
            "content_hash": evidence.content_hash,
        }
        if evidence.source_type != "code" or any(
            value is None for value in required.values()
        ):
            raise KnowledgeIntegrityError(
                "Code mapping Evidence 缺少 Phase 20 provenance"
            )
        view = bundle.artifacts[PAPER_CODE_MAPPING_PATH]
        locator = {
            "repo_fingerprint": evidence.repo_fingerprint,
            "repo_revision": evidence.repo_revision,
            "file_path": evidence.source_path,
            "file_sha256": evidence.file_sha256,
            "start_line": evidence.start_line,
            "end_line": evidence.end_line,
        }
        assert evidence.content_hash is not None
        return KnowledgeEvidenceRef(
            evidence_ref_id=build_evidence_ref_id(
                artifact_id=view.artifact_id,
                content_hash=evidence.content_hash,
                locator=locator,
            ),
            kind="code_artifact",
            job_id=bundle.verified_run.job.job_id,
            run_id=bundle.verified_run.job.run_id,
            artifact_id=view.artifact_id,
            artifact_path=view.relative_path,
            artifact_sha256=view.sha256,
            content_hash=evidence.content_hash,
            repo_fingerprint=evidence.repo_fingerprint,
            repo_revision=evidence.repo_revision,
            file_path=evidence.source_path,
            file_sha256=evidence.file_sha256,
            start_line=evidence.start_line,
            end_line=evidence.end_line,
        )

    @staticmethod
    def _provenance(
        *,
        subject_kind: str,
        subject_id: str,
        snapshot: KnowledgeSourceSnapshot,
        evidence: Iterable[KnowledgeEvidenceRef],
        authority: str,
        now: str,
    ) -> KnowledgeProvenanceRecord:
        refs = sorted(
            {item.evidence_ref_id: item for item in evidence}.values(),
            key=lambda item: item.evidence_ref_id,
        )
        draft = KnowledgeProvenanceRecord(
            provenance_id=build_provenance_id(
                subject_id=subject_id,
                source_snapshot_id=snapshot.snapshot_id,
                evidence_ref_ids=[item.evidence_ref_id for item in refs],
            ),
            subject_kind=subject_kind,
            subject_id=subject_id,
            source_snapshot_id=snapshot.snapshot_id,
            authority=authority,
            evidence=refs,
            provenance_hash="0" * 64,
            created_at=now,
        )
        return draft.model_copy(
            update={
                "provenance_hash": provenance_record_hash(draft)
            }
        )

    @staticmethod
    def _fact_ref(
        bundle: KnowledgeSourceBundle,
        fact: PaperFactRecord,
    ) -> KnowledgeEvidenceRef:
        evidence = fact.evidence
        return KnowledgeProjector._paper_ref(
            bundle=bundle,
            artifact_path=PAPER_FACT_INDEX_PATH,
            content_hash=evidence.content_hash,
            section_id=evidence.section_id,
            block_ids=evidence.block_ids,
            page_start=evidence.page_start,
            page_end=evidence.page_end,
        )

    @staticmethod
    def _symbol_key(
        candidate: CodeCandidate,
        symbol: str,
        file_sha256: str,
    ) -> str:
        return "|".join([candidate.file_path, symbol, file_sha256])

    def project(self, bundle: KnowledgeSourceBundle) -> KnowledgeGraphBatch:
        now = utc_now()
        snapshot = self._source_snapshot(bundle)
        entities: dict[str, KnowledgeEntityRecord] = {}
        relations: dict[str, KnowledgeRelationRecord] = {}
        provenance: dict[str, KnowledgeProvenanceRecord] = {}

        def add_entity(
            entity: KnowledgeEntityRecord,
            refs: list[KnowledgeEvidenceRef],
            authority: str = "deterministic_source",
        ) -> None:
            old = entities.get(entity.entity_id)
            if old is not None and old.record_hash != entity.record_hash:
                raise KnowledgeIntegrityError(
                    f"同一 Entity ID 出现不同内容：{entity.entity_id}"
                )
            entities[entity.entity_id] = entity
            item = self._provenance(
                subject_kind="entity",
                subject_id=entity.entity_id,
                snapshot=snapshot,
                evidence=refs,
                authority=authority,
                now=now,
            )
            provenance[item.provenance_id] = item

        def add_relation(
            relation: KnowledgeRelationRecord,
            refs: list[KnowledgeEvidenceRef],
        ) -> None:
            old = relations.get(relation.relation_id)
            if old is not None and old.relation_hash != relation.relation_hash:
                raise KnowledgeIntegrityError(
                    f"同一 Relation ID 出现不同内容：{relation.relation_id}"
                )
            relations[relation.relation_id] = relation
            item = self._provenance(
                subject_kind="relation",
                subject_id=relation.relation_id,
                snapshot=snapshot,
                evidence=refs,
                authority=relation.authority,
                now=now,
            )
            provenance[item.provenance_id] = item

        paper_title = (
            bundle.summary.title
            or Path(bundle.document.source_path).stem
        )
        paper_ref = self._paper_ref(
            bundle=bundle,
            artifact_path=PAPER_DOCUMENT_PATH,
            content_hash=bundle.document.source_sha256,
        )
        paper = self._entity(
            kind="paper",
            scope_key=bundle.document.source_sha256,
            canonical_key=bundle.document.source_sha256,
            display_name=paper_title,
            description=None,
            attributes={
                "paper_sha256": bundle.document.source_sha256,
                "document_id": bundle.document.document_id,
            },
            now=now,
        )
        add_entity(paper, [paper_ref])

        section_entities: dict[str, KnowledgeEntityRecord] = {}
        for section in bundle.sections:
            section_ref = self._paper_ref(
                bundle=bundle,
                artifact_path=PAPER_SECTIONS_PATH,
                content_hash=section.content_hash,
                section_id=section.section_id,
                page_start=section.page_start,
                page_end=section.page_end,
            )
            entity = self._entity(
                kind="section",
                scope_key=paper.entity_id,
                canonical_key=(
                    f"{section.section_id}|{section.content_hash}"
                ),
                display_name=section.title,
                description=None,
                attributes={
                    "section_id": section.section_id,
                    "section_kind": section.kind,
                    "page_start": section.page_start,
                    "page_end": section.page_end,
                },
                now=now,
            )
            section_entities[section.section_id] = entity
            add_entity(entity, [section_ref])
            add_relation(
                self._relation(
                    relation_type="paper_has_section",
                    source_entity_id=paper.entity_id,
                    target_entity_id=entity.entity_id,
                    status="asserted",
                    confidence=1.0,
                    now=now,
                ),
                [paper_ref, section_ref],
            )

        concept_entities: dict[str, KnowledgeEntityRecord] = {}
        for fact in bundle.facts:
            section = section_entities[fact.evidence.section_id]
            ref = self._fact_ref(bundle, fact)
            claim = self._entity(
                kind="claim",
                scope_key=paper.entity_id,
                canonical_key=(
                    f"{fact.fact_id}|{fact.category}|"
                    f"{fact.evidence.content_hash}"
                ),
                display_name=fact.name,
                description=fact.value,
                attributes={
                    "fact_id": fact.fact_id,
                    "category": fact.category,
                    "normalized_key": fact.normalized_key,
                    "confidence": fact.evidence.confidence,
                },
                now=now,
            )
            add_entity(claim, [ref])
            add_relation(
                self._relation(
                    relation_type="section_supports_claim",
                    source_entity_id=section.entity_id,
                    target_entity_id=claim.entity_id,
                    status="asserted",
                    confidence=fact.evidence.confidence,
                    now=now,
                ),
                [ref],
            )

            kind = FACT_ENTITY_KINDS.get(fact.category)
            if kind is None:
                continue
            mention = self._entity(
                kind=kind,
                scope_key=paper.entity_id,
                canonical_key=f"{fact.normalized_key}|{fact.fact_id}",
                display_name=fact.name,
                description=fact.value,
                attributes={
                    "fact_id": fact.fact_id,
                    "normalized_key": fact.normalized_key,
                },
                now=now,
            )
            add_entity(mention, [ref])
            relation_type = FACT_RELATIONS[fact.category]
            relation_source = (
                claim.entity_id
                if fact.category == "method_module"
                else paper.entity_id
            )
            add_relation(
                self._relation(
                    relation_type=relation_type,
                    source_entity_id=relation_source,
                    target_entity_id=mention.entity_id,
                    status="asserted",
                    confidence=fact.evidence.confidence,
                    now=now,
                ),
                [ref],
            )
            if fact.category == "method_module":
                concept_entities[
                    normalize_knowledge_key(fact.name)
                ] = mention

        for mapping in bundle.mappings:
            self._project_mapping(
                bundle=bundle,
                mapping=mapping,
                concept_entities=concept_entities,
                now=now,
                add_entity=add_entity,
                add_relation=add_relation,
            )

        return KnowledgeGraphBatch(
            source=snapshot,
            entities=sorted(entities.values(), key=lambda item: item.entity_id),
            relations=sorted(
                relations.values(),
                key=lambda item: item.relation_id,
            ),
            provenance=sorted(
                provenance.values(),
                key=lambda item: item.provenance_id,
            ),
        )

    def _project_mapping(
        self,
        *,
        bundle: KnowledgeSourceBundle,
        mapping: ModuleMapping,
        concept_entities: dict[str, KnowledgeEntityRecord],
        now: str,
        add_entity,
        add_relation,
    ) -> None:
        """Code mapping 是模型候选，只产生 candidate relation。"""

        concept = concept_entities.get(
            normalize_knowledge_key(mapping.module_name)
        )
        if concept is None:
            return
        for candidate in mapping.candidates:
            refs = [
                self._code_ref(bundle=bundle, evidence=item)
                for item in candidate.evidence
                if item.source_type == "code"
            ]
            if not refs:
                continue
            repo_scope = refs[0].repo_fingerprint
            file_sha256 = refs[0].file_sha256
            if repo_scope is None or file_sha256 is None:
                raise KnowledgeIntegrityError(
                    "Code Evidence 缺少 repository/file identity"
                )
            symbols = candidate.symbols or ["<module>"]
            for symbol in symbols:
                entity = self._entity(
                    kind="repository_symbol",
                    scope_key=repo_scope,
                    canonical_key=self._symbol_key(
                        candidate,
                        symbol,
                        file_sha256,
                    ),
                    display_name=symbol,
                    description=candidate.reason,
                    attributes={
                        "file_path": candidate.file_path,
                        "confidence": candidate.confidence,
                    },
                    now=now,
                )
                add_entity(entity, refs, "model_candidate")
                add_relation(
                    self._relation(
                        relation_type="concept_implemented_by_symbol",
                        source_entity_id=concept.entity_id,
                        target_entity_id=entity.entity_id,
                        status="candidate",
                        confidence=CONFIDENCE_VALUES[candidate.confidence],
                        proposal_reason=(
                            "Phase 20 paper-code mapping candidate"
                        ),
                        now=now,
                    ),
                    refs,
                )
