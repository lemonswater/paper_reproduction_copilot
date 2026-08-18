from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


SHA256_PATTERN = r"^[0-9a-f]{64}$"

KnowledgeEntityKind = Literal[
    "paper",
    "section",
    "claim",
    "concept_instance",
    "dataset_mention",
    "metric_mention",
    "repository_symbol",
]

KnowledgeRelationType = Literal[
    "paper_has_section",
    "section_supports_claim",
    "claim_describes_concept",
    "paper_uses_dataset",
    "paper_reports_metric",
    "concept_implemented_by_symbol",
    "equivalent_to",
]

KnowledgeRelationStatus = Literal[
    "asserted",
    "candidate",
    "confirmed",
    "rejected",
    "revoked",
]

KnowledgeAuthority = Literal[
    "deterministic_source",
    "model_candidate",
    "deterministic_similarity",
    "explicit_user",
    "verified_run",
]

KnowledgeEvidenceKind = Literal[
    "paper_artifact",
    "code_artifact",
]


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeEvidenceRef(KnowledgeModel):
    """只保存可定位身份，不把 PDF/源码全文复制到 Knowledge DB。"""

    evidence_ref_id: str = Field(pattern=r"^kgev_[0-9a-f]{24}$")
    kind: KnowledgeEvidenceKind
    job_id: str = Field(min_length=1, max_length=200)
    run_id: str = Field(min_length=1, max_length=300)
    artifact_id: str = Field(min_length=1, max_length=300)
    artifact_path: str = Field(min_length=1, max_length=500)
    artifact_sha256: str = Field(pattern=SHA256_PATTERN)
    content_hash: str = Field(pattern=SHA256_PATTERN)

    document_id: str | None = None
    paper_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    section_id: str | None = None
    block_ids: list[str] = Field(default_factory=list, max_length=64)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)

    repo_fingerprint: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    repo_revision: str | None = Field(default=None, max_length=100)
    file_path: str | None = Field(default=None, max_length=500)
    file_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)

    @field_validator("artifact_path")
    @classmethod
    def validate_artifact_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("artifact_path 必须是安全相对路径")
        return value

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("file_path 必须是安全仓库相对路径")
        return value

    @model_validator(mode="after")
    def validate_locator_shape(self) -> "KnowledgeEvidenceRef":
        if self.page_start and self.page_end and self.page_end < self.page_start:
            raise ValueError("paper evidence 页码范围无效")
        if self.start_line and self.end_line and self.end_line < self.start_line:
            raise ValueError("code evidence 行号范围无效")

        required_paper_values = (
            self.document_id,
            self.paper_sha256,
        )
        code_values = (
            self.repo_fingerprint,
            self.repo_revision,
            self.file_path,
            self.file_sha256,
            self.start_line,
            self.end_line,
        )
        if self.kind == "paper_artifact":
            if any(value is None for value in required_paper_values):
                raise ValueError("paper_artifact 必须包含论文身份")
            if any(value is not None for value in code_values):
                raise ValueError("paper_artifact 不能携带 code identity")
        else:
            if any(value is None for value in code_values):
                raise ValueError("code_artifact 必须包含完整代码身份")
            paper_values = required_paper_values + (self.section_id,)
            if any(value is not None for value in paper_values):
                raise ValueError("code_artifact 不能携带 paper identity")
        return self


class KnowledgeEntityRecord(KnowledgeModel):
    schema_version: Literal["phase49-v1"] = "phase49-v1"
    entity_id: str = Field(pattern=r"^kgent_[0-9a-f]{24}$")
    kind: KnowledgeEntityKind

    # source-scoped 类型必须包含 paper/repository identity，不能只用名称。
    scope_key: str = Field(min_length=1, max_length=300)
    canonical_key: str = Field(min_length=1, max_length=500)
    display_name: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=4000)
    attributes: dict[
        str,
        str | int | float | bool | list[str],
    ] = Field(default_factory=dict, max_length=40)
    record_hash: str = Field(pattern=SHA256_PATTERN)
    created_at: str


class KnowledgeRelationRecord(KnowledgeModel):
    schema_version: Literal["phase49-v1"] = "phase49-v1"
    relation_id: str = Field(pattern=r"^kgrel_[0-9a-f]{24}$")
    relation_type: KnowledgeRelationType
    source_entity_id: str = Field(pattern=r"^kgent_[0-9a-f]{24}$")
    target_entity_id: str = Field(pattern=r"^kgent_[0-9a-f]{24}$")
    status: KnowledgeRelationStatus
    authority: KnowledgeAuthority
    confidence: float = Field(ge=0.0, le=1.0)
    relation_hash: str = Field(pattern=SHA256_PATTERN)
    version: int = Field(ge=0)
    created_at: str
    updated_at: str
    reviewed_by: str | None = Field(default=None, max_length=200)
    proposal_reason: str | None = Field(default=None, max_length=1000)
    review_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_lifecycle_shape(self) -> "KnowledgeRelationRecord":
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("Knowledge Relation 不允许自环")
        if self.status == "asserted":
            if self.authority not in {
                "deterministic_source",
                "verified_run",
            }:
                raise ValueError("asserted relation authority 无效")
            if any(
                value is not None
                for value in (
                    self.reviewed_by,
                    self.proposal_reason,
                    self.review_reason,
                )
            ):
                raise ValueError("asserted relation 不携带人工 review")
        elif self.status == "candidate":
            if self.authority not in {
                "model_candidate",
                "deterministic_similarity",
            }:
                raise ValueError("candidate relation authority 无效")
            if self.reviewed_by is not None:
                raise ValueError("未审 candidate 不能携带 reviewed_by")
            if not self.proposal_reason:
                raise ValueError("candidate 必须记录 proposal_reason")
        else:
            if self.reviewed_by is None or not self.review_reason:
                raise ValueError("人工终态 relation 必须记录 reviewer 和 reason")
            if self.authority != "explicit_user":
                raise ValueError("人工终态 relation authority 必须是 explicit_user")
            if not self.proposal_reason:
                raise ValueError("人工终态 relation 必须保留原始 proposal_reason")
        return self


class KnowledgeProvenanceRecord(KnowledgeModel):
    """把稳定语义身份与某次 Run 的观察来源分开。"""

    provenance_id: str = Field(pattern=r"^kgprov_[0-9a-f]{24}$")
    subject_kind: Literal["entity", "relation"]
    subject_id: str = Field(pattern=r"^kg(?:ent|rel)_[0-9a-f]{24}$")
    source_snapshot_id: str = Field(pattern=r"^kgsnap_[0-9a-f]{24}$")
    authority: KnowledgeAuthority
    evidence: list[KnowledgeEvidenceRef] = Field(min_length=1, max_length=32)
    provenance_hash: str = Field(pattern=SHA256_PATTERN)
    created_at: str

    @model_validator(mode="after")
    def validate_subject_prefix(self) -> "KnowledgeProvenanceRecord":
        expected = "kgent_" if self.subject_kind == "entity" else "kgrel_"
        if not self.subject_id.startswith(expected):
            raise ValueError("Provenance subject_kind 与 subject_id 不一致")
        return self


class KnowledgeSourceSnapshot(KnowledgeModel):
    snapshot_id: str = Field(pattern=r"^kgsnap_[0-9a-f]{24}$")
    projector_version: Literal["phase49-v1"] = "phase49-v1"
    job_id: str
    run_id: str
    paper_sha256: str = Field(pattern=SHA256_PATTERN)
    repository_commit: str | None = Field(default=None, max_length=100)
    workspace_manifest_hash: str = Field(pattern=SHA256_PATTERN)
    artifact_hashes: dict[str, str] = Field(min_length=3, max_length=8)
    snapshot_hash: str = Field(pattern=SHA256_PATTERN)


class KnowledgeIngestionRecord(KnowledgeModel):
    ingestion_id: str = Field(pattern=r"^kging_[0-9a-f]{24}$")
    source: KnowledgeSourceSnapshot
    status: Literal["active", "archived", "failed"]
    entity_count: int = Field(ge=0)
    relation_count: int = Field(ge=0)
    created_entity_count: int = Field(ge=0)
    created_relation_count: int = Field(ge=0)
    error_code: str | None = None
    batch_hash: str = Field(pattern=SHA256_PATTERN)
    request_hash: str = Field(pattern=SHA256_PATTERN)
    created_by: str
    created_at: str
    archived_by: str | None = None
    archived_at: str | None = None
    archive_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_archive_shape(self) -> "KnowledgeIngestionRecord":
        archive_values = (
            self.archived_by,
            self.archived_at,
            self.archive_reason,
        )
        if self.status == "archived":
            if any(value is None for value in archive_values):
                raise ValueError("archived ingestion 必须有完整归档记录")
        elif any(value is not None for value in archive_values):
            raise ValueError("非 archived ingestion 不能携带归档字段")
        return self


class KnowledgeGraphBatch(KnowledgeModel):
    source: KnowledgeSourceSnapshot
    entities: list[KnowledgeEntityRecord] = Field(max_length=20_000)
    relations: list[KnowledgeRelationRecord] = Field(max_length=50_000)
    provenance: list[KnowledgeProvenanceRecord] = Field(max_length=100_000)


class KnowledgeIngestRequest(KnowledgeModel):
    job_id: str = Field(min_length=1, max_length=200)


class KnowledgeArchiveRequest(KnowledgeModel):
    reason: str = Field(min_length=1, max_length=1000)


class KnowledgeIngestResponse(KnowledgeModel):
    ingestion: KnowledgeIngestionRecord
    replayed: bool


class KnowledgeRelationReviewRequest(KnowledgeModel):
    decision: Literal["confirmed", "rejected", "revoked"]
    expected_version: int = Field(ge=0)
    expected_relation_hash: str = Field(pattern=SHA256_PATTERN)
    reason: str = Field(min_length=1, max_length=1000)


class KnowledgeRelationMutationResponse(KnowledgeModel):
    relation: KnowledgeRelationRecord
    replayed: bool


class KnowledgeEquivalenceProposalRequest(KnowledgeModel):
    source_entity_id: str = Field(pattern=r"^kgent_[0-9a-f]{24}$")
    target_entity_id: str = Field(pattern=r"^kgent_[0-9a-f]{24}$")
    expected_source_hash: str = Field(pattern=SHA256_PATTERN)
    expected_target_hash: str = Field(pattern=SHA256_PATTERN)
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_distinct_entities(
        self,
    ) -> "KnowledgeEquivalenceProposalRequest":
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("等价候选不能引用同一 Entity")
        return self


class KnowledgeQueryRequest(KnowledgeModel):
    query: str = Field(min_length=1, max_length=1000)
    entity_kinds: list[KnowledgeEntityKind] = Field(
        default_factory=list,
        max_length=8,
    )
    max_entities: int = Field(default=20, ge=1, le=100)
    max_relations: int = Field(default=40, ge=1, le=200)
    max_depth: int = Field(default=1, ge=0, le=2)
    include_candidates: bool = False


class KnowledgeEntityHit(KnowledgeModel):
    entity: KnowledgeEntityRecord
    score: float = Field(ge=0.0, le=1.0)
    matched_terms: list[str] = Field(default_factory=list)


class KnowledgeSubjectEvidence(KnowledgeModel):
    subject_id: str = Field(pattern=r"^kg(?:ent|rel)_[0-9a-f]{24}$")
    evidence_ref_ids: list[str] = Field(min_length=1, max_length=64)


class KnowledgeQueryPack(KnowledgeModel):
    query_hash: str = Field(pattern=SHA256_PATTERN)
    entities: list[KnowledgeEntityHit]
    authoritative_relations: list[KnowledgeRelationRecord]
    candidate_relations: list[KnowledgeRelationRecord]
    evidence_refs: list[KnowledgeEvidenceRef]
    subject_evidence: list[KnowledgeSubjectEvidence]
    truncated: bool
    pack_hash: str = Field(pattern=SHA256_PATTERN)
