from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.interaction.artifacts import ArtifactCatalog
from app.interaction.schemas import ArtifactView
from app.knowledge_base.errors import (
    KnowledgeConflictError,
    KnowledgeIntegrityError,
    KnowledgeLimitExceededError,
    KnowledgeNotFoundError,
)
from app.paper.schemas import (
    PaperDocument,
    PaperFactRecord,
    PaperSection,
)
from app.run_evidence.reader import VerifiedRunEvidenceReader
from app.run_evidence.schemas import VerifiedRunEvidence
from app.schemas import ModuleMapping, PaperSummary


PAPER_DOCUMENT_PATH = "analysis/paper_document.json"
PAPER_SECTIONS_PATH = "analysis/paper_sections.json"
PAPER_FACT_INDEX_PATH = "analysis/paper_fact_index.json"
PAPER_SUMMARY_PATH = "analysis/paper_summary.json"
PAPER_CODE_MAPPING_PATH = "analysis/paper_code_mapping.json"

REQUIRED_PATHS = {
    PAPER_DOCUMENT_PATH,
    PAPER_SECTIONS_PATH,
    PAPER_FACT_INDEX_PATH,
    PAPER_SUMMARY_PATH,
}


@dataclass(frozen=True)
class KnowledgeSourceBundle:
    verified_run: VerifiedRunEvidence
    artifacts: dict[str, ArtifactView]
    document: PaperDocument
    sections: tuple[PaperSection, ...]
    facts: tuple[PaperFactRecord, ...]
    summary: PaperSummary
    mappings: tuple[ModuleMapping, ...]


class KnowledgeSourceReader:
    def __init__(
        self,
        *,
        verified_runs: VerifiedRunEvidenceReader,
        artifact_catalog: ArtifactCatalog,
        max_artifact_bytes: int,
        max_sections: int,
        max_facts: int,
        max_mappings: int,
    ) -> None:
        self.verified_runs = verified_runs
        self.artifact_catalog = artifact_catalog
        self.max_artifact_bytes = max_artifact_bytes
        self.max_sections = max_sections
        self.max_facts = max_facts
        self.max_mappings = max_mappings

    @staticmethod
    def _artifact_map(
        evidence: VerifiedRunEvidence,
    ) -> dict[str, ArtifactView]:
        result = {item.relative_path: item for item in evidence.artifacts}
        if len(result) != len(evidence.artifacts):
            raise KnowledgeIntegrityError("Artifact relative_path 重复")
        missing = REQUIRED_PATHS - set(result)
        if missing:
            raise KnowledgeNotFoundError(
                f"Knowledge ingestion 缺少必需 Artifact：{sorted(missing)}"
            )
        return result

    def _read_json(
        self,
        *,
        evidence: VerifiedRunEvidence,
        view: ArtifactView,
    ) -> Any:
        if view.size_bytes > self.max_artifact_bytes:
            raise KnowledgeLimitExceededError(
                f"Knowledge Artifact 超过读取上限：{view.relative_path}"
            )
        opened = self.artifact_catalog.open(
            job=evidence.job,
            artifact_id=view.artifact_id,
        )
        try:
            descriptor = opened.artifact.descriptor
            stat = opened.blob.stat
            if (
                descriptor.artifact_id != view.artifact_id
                or descriptor.relative_path != view.relative_path
                or descriptor.run_id != evidence.job.run_id
                or descriptor.sha256 != view.sha256
                or descriptor.size_bytes != view.size_bytes
                or stat.sha256 != view.sha256
                or stat.size_bytes != view.size_bytes
            ):
                raise KnowledgeIntegrityError(
                    "Knowledge Artifact Catalog/Descriptor/Blob identity 不一致"
                )
            raw = opened.blob.body.read(self.max_artifact_bytes + 1)
        finally:
            opened.blob.body.close()

        if len(raw) > self.max_artifact_bytes or len(raw) != view.size_bytes:
            raise KnowledgeIntegrityError("Knowledge Artifact 读取大小不一致")
        if hashlib.sha256(raw).hexdigest() != view.sha256:
            raise KnowledgeIntegrityError("Knowledge Artifact SHA-256 不一致")
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KnowledgeIntegrityError(
                f"Knowledge Artifact 不是有效 JSON：{view.relative_path}"
            ) from exc

    def _load_model(
        self,
        *,
        evidence: VerifiedRunEvidence,
        view: ArtifactView,
        model: type[BaseModel],
    ) -> BaseModel:
        payload = self._read_json(evidence=evidence, view=view)
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            raise KnowledgeConflictError(
                f"Knowledge Artifact Schema 无效：{view.relative_path}"
            ) from exc

    def _load_list(
        self,
        *,
        evidence: VerifiedRunEvidence,
        view: ArtifactView,
        model: type[BaseModel],
        limit: int,
    ) -> tuple[BaseModel, ...]:
        payload = self._read_json(evidence=evidence, view=view)
        if not isinstance(payload, list):
            raise KnowledgeConflictError(
                f"Knowledge Artifact 顶层必须是 list：{view.relative_path}"
            )
        if len(payload) > limit:
            raise KnowledgeLimitExceededError(
                f"Knowledge Artifact 条目超过上限：{view.relative_path}"
            )
        try:
            return tuple(model.model_validate(item) for item in payload)
        except ValidationError as exc:
            raise KnowledgeConflictError(
                f"Knowledge Artifact list item 无效：{view.relative_path}"
            ) from exc

    @staticmethod
    def _paper_sha256(evidence: VerifiedRunEvidence) -> str:
        entries = [
            item for item in evidence.workspace.entries if item.role == "paper"
        ]
        if len(entries) != 1:
            raise KnowledgeIntegrityError(
                "Workspace Manifest 必须包含唯一 paper entry"
            )
        return entries[0].sha256

    def read(self, job_id: str) -> KnowledgeSourceBundle:
        evidence = self.verified_runs.read(job_id)
        artifacts = self._artifact_map(evidence)
        document = self._load_model(
            evidence=evidence,
            view=artifacts[PAPER_DOCUMENT_PATH],
            model=PaperDocument,
        )
        assert isinstance(document, PaperDocument)
        if document.source_sha256 != self._paper_sha256(evidence):
            raise KnowledgeIntegrityError(
                "PaperDocument source_sha256 与 Workspace paper entry 不一致"
            )

        sections = self._load_list(
            evidence=evidence,
            view=artifacts[PAPER_SECTIONS_PATH],
            model=PaperSection,
            limit=self.max_sections,
        )
        facts = self._load_list(
            evidence=evidence,
            view=artifacts[PAPER_FACT_INDEX_PATH],
            model=PaperFactRecord,
            limit=self.max_facts,
        )
        summary = self._load_model(
            evidence=evidence,
            view=artifacts[PAPER_SUMMARY_PATH],
            model=PaperSummary,
        )
        assert isinstance(summary, PaperSummary)

        mapping_view = artifacts.get(PAPER_CODE_MAPPING_PATH)
        mappings: tuple[BaseModel, ...] = ()
        if mapping_view is not None:
            mappings = self._load_list(
                evidence=evidence,
                view=mapping_view,
                model=ModuleMapping,
                limit=self.max_mappings,
            )

        typed_sections = tuple(
            item for item in sections if isinstance(item, PaperSection)
        )
        typed_facts = tuple(
            item for item in facts if isinstance(item, PaperFactRecord)
        )
        typed_mappings = tuple(
            item for item in mappings if isinstance(item, ModuleMapping)
        )
        if len(typed_sections) != len(sections):
            raise KnowledgeIntegrityError("PaperSection 类型投影失败")
        if len(typed_facts) != len(facts):
            raise KnowledgeIntegrityError("PaperFactRecord 类型投影失败")
        if len(typed_mappings) != len(mappings):
            raise KnowledgeIntegrityError("ModuleMapping 类型投影失败")

        section_ids = {item.section_id for item in typed_sections}
        if len(section_ids) != len(typed_sections):
            raise KnowledgeIntegrityError("Paper section_id 重复")
        if any(
            fact.evidence.document_id != document.document_id
            or fact.evidence.section_id not in section_ids
            for fact in typed_facts
        ):
            raise KnowledgeIntegrityError(
                "Paper Fact evidence 不属于当前 document/section"
            )

        return KnowledgeSourceBundle(
            verified_run=evidence,
            artifacts=artifacts,
            document=document,
            sections=typed_sections,
            facts=typed_facts,
            summary=summary,
            mappings=typed_mappings,
        )
