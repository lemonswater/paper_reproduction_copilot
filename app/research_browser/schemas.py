from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.research_browser.identity import (
    sha256_text,
    sha256_value,
    stable_id,
    without_hash,
)


SHA256_PATTERN = r"^[0-9a-f]{64}$"

ResearchStatus = Literal[
    "submitted",
    "running",
    "succeeded",
    "failed_retryable",
    "failed_terminal",
    "cancelled",
    "reconciliation_required",
]

ResearchSourceKind = Literal["html", "text", "pdf"]
ResearchSynthesisStatus = Literal[
    "succeeded",
    "evidence_only",
    "insufficient_evidence",
    "budget_denied",
]
ResearchCandidateKind = Literal["paper_pdf", "git_repository"]


def normalize_host_values(values: list[str]) -> list[str]:
    """把用户/Policy host 转成稳定 IDNA 小写形式。"""

    normalized: list[str] = []
    for value in values:
        host = value.strip().rstrip(".").lower()
        if (
            not host
            or "/" in host
            or "\\" in host
            or ":" in host
            or "@" in host
            or host.startswith(".")
        ):
            raise ValueError("allowed_hosts 必须只包含 host，不是 URL")
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("allowed host IDNA 编码失败") from exc
        if host not in normalized:
            normalized.append(host)
    return normalized


class ResearchModel(BaseModel):
    """所有持久化/公开对象拒绝未知字段，避免协议静默漂移。"""

    model_config = ConfigDict(extra="forbid")


class ResearchRequest(ResearchModel):
    """用户显式提交的研究请求，不包含 Provider endpoint 或 Header。"""

    schema_version: Literal["phase51-v1"] = "phase51-v1"
    # 第一版绑定 Brave Web Search 的 400 字符上限。
    query: str = Field(min_length=2, max_length=400)
    purpose: str = Field(min_length=2, max_length=500)
    job_id: str | None = Field(default=None, min_length=1, max_length=200)
    project_id: str | None = Field(default=None, max_length=200)
    allowed_hosts: list[str] = Field(default_factory=list, max_length=12)
    max_results: int = Field(default=8, ge=1, le=20)
    max_sources: int = Field(default=3, ge=1, le=5)
    allow_pdf: bool = True

    @field_validator("query", "purpose")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in value
        ):
            raise ValueError("Research 文本不能包含 ASCII 控制字符")
        normalized = " ".join(value.strip().split())
        return normalized

    @field_validator("allowed_hosts")
    @classmethod
    def normalize_hosts(cls, values: list[str]) -> list[str]:
        return normalize_host_values(values)


class ResearchPolicyDocument(ResearchModel):
    schema_version: Literal["phase51-v1"] = "phase51-v1"
    policy_version: str = Field(min_length=1, max_length=100)
    search_provider_binding: Literal["brave_search", "fixture_search"]
    allowed_hosts: list[str] = Field(min_length=1, max_length=100)
    allowed_media_types: list[Literal[
        "text/html",
        "text/plain",
        "application/pdf",
    ]] = Field(min_length=1)
    user_agent: str = Field(min_length=1, max_length=200)
    max_redirects: int = Field(default=4, ge=0, le=8)
    connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    read_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    total_timeout_seconds: float = Field(default=90.0, gt=0, le=120)
    max_response_bytes: int = Field(default=2_000_000, ge=1024, le=8_000_000)
    max_total_bytes: int = Field(default=5_000_000, ge=1024, le=20_000_000)
    max_pdf_pages: int = Field(default=80, ge=1, le=300)
    max_blocks_per_source: int = Field(default=160, ge=1, le=256)
    max_citations: int = Field(default=24, ge=1, le=40)
    min_host_interval_seconds: float = Field(default=1.0, ge=0.1, le=30)
    robots_required: Literal[True] = True

    @field_validator("allowed_hosts")
    @classmethod
    def normalize_policy_hosts(cls, values: list[str]) -> list[str]:
        # 与请求 host 规则相同，但 Policy 至少需要一个 host。
        return normalize_host_values(values)

    @model_validator(mode="after")
    def validate_budgets(self) -> "ResearchPolicyDocument":
        if self.max_total_bytes < self.max_response_bytes:
            raise ValueError("max_total_bytes 不能小于 max_response_bytes")
        if len(self.allowed_media_types) != len(set(self.allowed_media_types)):
            raise ValueError("allowed_media_types 不能重复")
        return self


class ProviderSearchHit(ResearchModel):
    """Search Provider Adapter 的原始有界输出；尚未成为可信引用。"""

    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2048)
    snippet: str = Field(default="", max_length=2000)
    rank: int = Field(ge=1, le=100)


class ResearchSearchHit(ResearchModel):
    """经过 URL Policy 和身份计算后的 Search Hit。"""

    hit_id: str = Field(pattern=r"^rhit_[0-9a-f]{24}$")
    canonical_url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=500)
    snippet: str = Field(default="", max_length=2000)
    rank: int = Field(ge=1, le=100)
    hit_sha256: str = Field(pattern=SHA256_PATTERN)


class ExtractedBlock(ResearchModel):
    """正文中可独立引用的有界单元。"""

    block_id: str = Field(pattern=r"^rblk_[0-9a-f]{24}$")
    kind: Literal[
        "title",
        "heading",
        "paragraph",
        "list_item",
        "code",
        "pdf_page",
    ]
    locator: str = Field(min_length=1, max_length=500)
    heading_path: list[str] = Field(default_factory=list, max_length=12)
    text: str = Field(min_length=1, max_length=8000)
    text_sha256: str = Field(pattern=SHA256_PATTERN)

    @field_validator("text")
    @classmethod
    def remove_nul(cls, value: str) -> str:
        normalized = " ".join(value.replace("\x00", " ").split())
        if not normalized:
            raise ValueError("ExtractedBlock 文本不能为空")
        return normalized


class ResearchSourceSnapshot(ResearchModel):
    """一次抓取的可复核内容身份；不保存原始 Header/Cookie/HTML。"""

    snapshot_id: str = Field(pattern=r"^rsnap_[0-9a-f]{24}$")
    canonical_url: str = Field(min_length=1, max_length=2048)
    redirect_chain: list[str] = Field(min_length=1, max_length=8)
    fetched_at: str
    status_code: Literal[200] = 200
    media_type: str = Field(min_length=1, max_length=200)
    source_kind: ResearchSourceKind
    body_sha256: str = Field(pattern=SHA256_PATTERN)
    body_size_bytes: int = Field(ge=0)
    normalized_text_sha256: str = Field(pattern=SHA256_PATTERN)
    title: str | None = Field(default=None, max_length=500)
    blocks: list[ExtractedBlock] = Field(min_length=1, max_length=256)
    robots_status: Literal["allowed", "not_present"]
    fetch_policy_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_redirect_terminal(self) -> "ResearchSourceSnapshot":
        if self.redirect_chain[-1] != self.canonical_url:
            raise ValueError("redirect_chain 末项必须等于 canonical_url")
        block_ids = [item.block_id for item in self.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("Snapshot block_id 不能重复")
        return self


class ResearchCitation(ResearchModel):
    """引用必须同时绑定 Snapshot 与 Block，不能只保存一段引文。"""

    citation_id: str = Field(pattern=r"^rcit_[0-9a-f]{24}$")
    snapshot_id: str = Field(pattern=r"^rsnap_[0-9a-f]{24}$")
    snapshot_body_sha256: str = Field(pattern=SHA256_PATTERN)
    block_id: str = Field(pattern=r"^rblk_[0-9a-f]{24}$")
    canonical_url: str = Field(min_length=1, max_length=2048)
    label: str = Field(min_length=1, max_length=500)
    locator: str = Field(min_length=1, max_length=500)
    excerpt: str = Field(min_length=1, max_length=1200)
    excerpt_sha256: str = Field(pattern=SHA256_PATTERN)
    relevance_score: float = Field(ge=0.0, le=1.0)


class ResearchResourceCandidate(ResearchModel):
    """服务端产生的资源候选；它不是 ResourceRequest 或 Approval。"""

    candidate_id: str = Field(pattern=r"^rcand_[0-9a-f]{24}$")
    kind: ResearchCandidateKind
    source_url_sanitized: str = Field(min_length=1, max_length=2048)
    expected_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    expected_git_commit: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40,64}$",
    )
    citation_ids: list[str] = Field(min_length=1, max_length=8)
    reason: str = Field(min_length=1, max_length=1000)
    candidate_sha256: str = Field(pattern=SHA256_PATTERN)
    requires_explicit_user_review: Literal[True] = True

    @model_validator(mode="after")
    def validate_resource_identity(self) -> "ResearchResourceCandidate":
        if self.kind == "paper_pdf":
            if self.expected_sha256 is None:
                raise ValueError("paper_pdf candidate 必须绑定完整响应 SHA-256")
            if self.expected_git_commit is not None:
                raise ValueError("paper_pdf candidate 不能携带 git commit")
        else:
            if self.expected_git_commit is None:
                raise ValueError("git_repository candidate 必须绑定 exact commit")
            if self.expected_sha256 is not None:
                raise ValueError("git_repository candidate 不能携带文件 SHA-256")
        if len(self.citation_ids) != len(set(self.citation_ids)):
            raise ValueError("candidate citation_ids 不能重复")
        return self


class ResearchEvidenceDraft(ResearchModel):
    """复合 Tool/Skill 的输出；Service 持久化前还会重算所有身份。"""

    search_hits: list[ResearchSearchHit] = Field(max_length=20)
    snapshots: list[ResearchSourceSnapshot] = Field(max_length=5)
    citations: list[ResearchCitation] = Field(max_length=40)
    resource_candidates: list[ResearchResourceCandidate] = Field(max_length=12)
    skipped: list[str] = Field(default_factory=list, max_length=20)


class ResearchSynthesisDraft(ResearchModel):
    """LLM 唯一允许返回的结构，不允许返回 URL、命令或审批字段。"""

    answer: str = Field(min_length=1, max_length=6000)
    citation_ids: list[str] = Field(default_factory=list, max_length=12)
    resource_candidate_ids: list[str] = Field(default_factory=list, max_length=6)
    insufficient_evidence: bool = False

    @field_validator("citation_ids", "resource_candidate_ids")
    @classmethod
    def reject_duplicate_ids(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("引用/候选 ID 不能重复")
        return values

    @model_validator(mode="after")
    def validate_citation_requirement(self) -> "ResearchSynthesisDraft":
        if not self.insufficient_evidence and not self.citation_ids:
            raise ValueError("citation_ids 不能为空，除非 insufficient_evidence=True")
        return self


class ResearchReport(ResearchModel):
    synthesis_status: ResearchSynthesisStatus
    answer: str
    citations: list[ResearchCitation] = Field(max_length=12)
    resource_candidates: list[ResearchResourceCandidate] = Field(max_length=6)
    model_invocation_id: str | None = None
    model_decision_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)


class ResearchEvidencePack(ResearchModel):
    schema_version: Literal["phase51-v1"] = "phase51-v1"
    pack_id: str = Field(pattern=r"^rpack_[0-9a-f]{24}$")
    session_id: str = Field(pattern=r"^research_[0-9a-f]{24}$")
    request_sha256: str = Field(pattern=SHA256_PATTERN)
    policy_sha256: str = Field(pattern=SHA256_PATTERN)
    search_hits: list[ResearchSearchHit] = Field(max_length=20)
    snapshots: list[ResearchSourceSnapshot] = Field(max_length=5)
    citations: list[ResearchCitation] = Field(max_length=40)
    resource_candidates: list[ResearchResourceCandidate] = Field(max_length=12)
    report: ResearchReport
    pack_sha256: str = Field(pattern=SHA256_PATTERN)
    created_at: str

    @model_validator(mode="after")
    def validate_references(self) -> "ResearchEvidencePack":
        for hit in self.search_hits:
            identity = {
                "url": hit.canonical_url,
                "title": hit.title,
                "snippet": hit.snippet,
                "rank": hit.rank,
            }
            if hit.hit_sha256 != sha256_value(identity):
                raise ValueError("Search Hit Hash 不匹配")
            if hit.hit_id != stable_id("rhit", identity):
                raise ValueError("Search Hit ID 不匹配")
        snapshots = {item.snapshot_id: item for item in self.snapshots}
        if len(snapshots) != len(self.snapshots):
            raise ValueError("Pack snapshot_id 不能重复")
        for snapshot in self.snapshots:
            expected_snapshot_id = stable_id(
                "rsnap",
                {
                    "url": snapshot.canonical_url,
                    "body_sha256": snapshot.body_sha256,
                    "policy_sha256": snapshot.fetch_policy_sha256,
                },
            )
            if snapshot.snapshot_id != expected_snapshot_id:
                raise ValueError("Snapshot ID 不匹配")
            normalized_text = "\n".join(
                block.text for block in snapshot.blocks
            )
            if (
                sha256_text(normalized_text)
                != snapshot.normalized_text_sha256
            ):
                raise ValueError("Snapshot normalized text Hash 不匹配")
        blocks = {
            (snapshot.snapshot_id, block.block_id): block
            for snapshot in self.snapshots
            for block in snapshot.blocks
        }
        citation_ids = {item.citation_id for item in self.citations}
        if len(citation_ids) != len(self.citations):
            raise ValueError("Pack citation_id 不能重复")
        citation_by_id = {
            item.citation_id: item for item in self.citations
        }
        for citation in self.citations:
            snapshot = snapshots.get(citation.snapshot_id)
            if snapshot is None:
                raise ValueError("Citation 引用了未知 Snapshot")
            if snapshot.body_sha256 != citation.snapshot_body_sha256:
                raise ValueError("Citation Snapshot Hash 不匹配")
            block = blocks.get((citation.snapshot_id, citation.block_id))
            if block is None:
                raise ValueError("Citation 引用了未知 Block")
            if sha256_text(block.text) != block.text_sha256:
                raise ValueError("Block 文本 Hash 不匹配")
            if block.block_id != stable_id(
                "rblk",
                {
                    "locator": block.locator,
                    "text_sha256": block.text_sha256,
                },
            ):
                raise ValueError("Block ID 不匹配")
            if citation.excerpt != block.text[:1200]:
                raise ValueError("Citation excerpt 不是对应 Block 的有界前缀")
            if sha256_text(citation.excerpt) != citation.excerpt_sha256:
                raise ValueError("Citation excerpt Hash 不匹配")
            if citation.citation_id != stable_id(
                "rcit",
                {
                    "snapshot_id": citation.snapshot_id,
                    "block_id": citation.block_id,
                    "excerpt_sha256": citation.excerpt_sha256,
                },
            ):
                raise ValueError("Citation ID 不匹配")
        candidate_by_id = {
            item.candidate_id: item for item in self.resource_candidates
        }
        if len(candidate_by_id) != len(self.resource_candidates):
            raise ValueError("Pack candidate_id 不能重复")
        for candidate in self.resource_candidates:
            if not set(candidate.citation_ids).issubset(citation_ids):
                raise ValueError("Resource Candidate 引用了未知 Citation")
            if candidate.kind == "paper_pdf":
                candidate_snapshot_ids = {
                    citation_by_id[item].snapshot_id
                    for item in candidate.citation_ids
                }
                if len(candidate_snapshot_ids) != 1:
                    raise ValueError("PDF Candidate 必须只引用一个 Snapshot")
                candidate_snapshot = snapshots[
                    next(iter(candidate_snapshot_ids))
                ]
                if (
                    candidate_snapshot.source_kind != "pdf"
                    or candidate.expected_sha256
                    != candidate_snapshot.body_sha256
                    or candidate.source_url_sanitized
                    != candidate_snapshot.canonical_url
                ):
                    raise ValueError("PDF Candidate 与 Snapshot 身份不一致")
                candidate_identity = {
                    "kind": "paper_pdf",
                    "snapshot": candidate_snapshot.snapshot_id,
                }
            else:
                commit = candidate.expected_git_commit or ""
                repository_path = urlsplit(
                    candidate.source_url_sanitized
                ).path.rstrip("/")
                if not all(
                    urlsplit(citation_by_id[item].canonical_url).hostname
                    == "github.com"
                    and urlsplit(
                        citation_by_id[item].canonical_url
                    ).path.startswith(f"{repository_path}/commit/{commit}")
                    for item in candidate.citation_ids
                ):
                    raise ValueError("Git Candidate Evidence 未绑定 exact commit")
                candidate_identity = {
                    "kind": "git_repository",
                    "url": candidate.source_url_sanitized,
                    "commit": candidate.expected_git_commit,
                }
            if candidate.candidate_id != stable_id(
                "rcand",
                candidate_identity,
            ):
                raise ValueError("Resource Candidate ID 不匹配")
            if (
                sha256_value(without_hash(candidate, "candidate_sha256"))
                != candidate.candidate_sha256
            ):
                raise ValueError("Resource Candidate Hash 不匹配")
        report_ids = {item.citation_id for item in self.report.citations}
        if not report_ids.issubset(citation_ids):
            raise ValueError("Report 引用了 Pack 外 Citation")
        if any(
            citation_by_id[item.citation_id] != item
            for item in self.report.citations
        ):
            raise ValueError("Report Citation 内容与 Pack 不一致")
        candidate_ids = set(candidate_by_id)
        report_candidate_ids = {
            item.candidate_id for item in self.report.resource_candidates
        }
        if not report_candidate_ids.issubset(candidate_ids):
            raise ValueError("Report 引用了 Pack 外 Resource Candidate")
        if any(
            candidate_by_id[item.candidate_id] != item
            for item in self.report.resource_candidates
        ):
            raise ValueError("Report Resource Candidate 内容与 Pack 不一致")
        expected_pack_id = stable_id(
            "rpack",
            {
                "session_id": self.session_id,
                "request_sha256": self.request_sha256,
                "snapshots": [
                    item.snapshot_id for item in self.snapshots
                ],
            },
        )
        if self.pack_id != expected_pack_id:
            raise ValueError("Pack ID 不匹配")
        return self


class ResearchRecord(ResearchModel):
    session_id: str = Field(pattern=r"^research_[0-9a-f]{24}$")
    idempotency_key: str = Field(min_length=1, max_length=300)
    request: ResearchRequest
    request_sha256: str = Field(pattern=SHA256_PATTERN)
    policy_sha256: str = Field(pattern=SHA256_PATTERN)
    status: ResearchStatus
    version: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    lease_token: str | None = Field(default=None, pattern=r"^rlease_[0-9a-f]{32}$")
    lease_expires_at: str | None = None
    pack_id: str | None = Field(default=None, pattern=r"^rpack_[0-9a-f]{24}$")
    error_code: str | None = Field(default=None, max_length=100)
    created_at: str
    updated_at: str

    @model_validator(mode="after")
    def validate_status_shape(self) -> "ResearchRecord":
        owned = self.status == "running"
        if owned != (self.lease_token is not None and self.lease_expires_at is not None):
            raise ValueError("只有 running Session 可以携带完整 Lease")
        if self.status == "succeeded" and self.pack_id is None:
            raise ValueError("succeeded Session 必须引用 Evidence Pack")
        return self


class ResearchPublicRecord(ResearchModel):
    """API/CLI 公开投影：不暴露幂等键、Lease Token 或 Lease 到期时间。"""

    session_id: str
    request: ResearchRequest
    request_sha256: str
    policy_sha256: str
    status: ResearchStatus
    version: int
    attempt_count: int
    pack_id: str | None
    error_code: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_record(cls, record: ResearchRecord) -> "ResearchPublicRecord":
        return cls.model_validate(
            record.model_dump(
                exclude={
                    "idempotency_key",
                    "lease_token",
                    "lease_expires_at",
                }
            )
        )


class ResearchEvent(ResearchModel):
    event_id: int = Field(ge=1)
    session_id: str = Field(pattern=r"^research_[0-9a-f]{24}$")
    event_type: str = Field(min_length=1, max_length=100)
    actor: str = Field(min_length=1, max_length=200)
    payload: dict[str, str | int | bool | None] = Field(default_factory=dict)
    created_at: str


class ResearchResourceSelection(ResearchModel):
    """公开 mutation 只提交服务端候选身份，不重新提交 URL。"""

    candidate_id: str = Field(pattern=r"^rcand_[0-9a-f]{24}$")
    candidate_sha256: str = Field(pattern=SHA256_PATTERN)
    expected_pack_sha256: str = Field(pattern=SHA256_PATTERN)
    purpose: str = Field(min_length=1, max_length=500)


class ResearchResourceLinkResponse(ResearchModel):
    """Resource Bridge 公开投影，不暴露 Resource 幂等键或 Worker Claim。"""

    session_id: str
    candidate_id: str
    resource_id: str
    resource_request_sha256: str
    resource_status: str
    resource_version: int


class ResearchHealthReport(ResearchModel):
    enabled: bool
    ready: bool
    status: Literal["disabled", "ready", "degraded", "not_ready"]
    policy_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    database_ready: bool
    search_secret_ready: bool
    network_guard: Literal["application_only", "egress_proxy"]
    issues: list[str] = Field(default_factory=list)
