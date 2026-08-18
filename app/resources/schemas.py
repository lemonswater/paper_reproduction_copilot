from __future__ import annotations

"""Phase 29 Resource schemas。

身份约束：
- paper_pdf：URL HTTPS PDF，expected_sha256 可选（用户可能只知道 URL）。
- git_repository：必须提供 exact commit；不接受下载文件 expected_sha256。
- checkpoint：必须在下载前提供 expected_sha256；获取阶段绝不反序列化。
"""

import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")

ResourceKind = Literal[
    "paper_pdf", "git_repository", "checkpoint"
]
ResourceStatus = Literal[
    "awaiting_approval",
    "queued",
    "fetching",
    "validating",
    "published",
    "rejected",
    "cancelled",
    "failed_retryable",
    "failed_terminal",
    "reconciliation_required",
]

TERMINAL_RESOURCE_STATUSES = {
    "published",
    "rejected",
    "cancelled",
    "failed_terminal",
}


class ResourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceRequest(ResourceModel):
    kind: ResourceKind
    source_url: str = Field(min_length=1, max_length=2048)
    expected_sha256: str | None = None
    expected_git_commit: str | None = None
    purpose: str = Field(min_length=1, max_length=500)

    @field_validator("expected_sha256")
    @classmethod
    def validate_sha(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if not SHA256_RE.fullmatch(lowered):
            raise ValueError(
                "expected_sha256 必须是 64 位小写十六进制"
            )
        return lowered

    @field_validator("expected_git_commit")
    @classmethod
    def validate_commit(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if not COMMIT_RE.fullmatch(lowered):
            raise ValueError(
                "expected_git_commit 必须是完整 commit SHA"
            )
        return lowered

    @model_validator(mode="after")
    def validate_identity_requirement(
        self,
    ) -> "ResourceRequest":
        if self.kind == "git_repository":
            if self.expected_git_commit is None:
                raise ValueError(
                    "Git resource 必须指定 exact commit"
                )
            if self.expected_sha256 is not None:
                raise ValueError(
                    "Git request 不使用下载文件 expected_sha256"
                )
        elif self.kind == "checkpoint":
            if self.expected_sha256 is None:
                raise ValueError(
                    "Checkpoint 必须在下载前指定 expected_sha256"
                )
            if self.expected_git_commit is not None:
                raise ValueError(
                    "非 Git resource 不能指定 expected_git_commit"
                )
        else:
            # paper_pdf
            if self.expected_git_commit is not None:
                raise ValueError(
                    "PDF 不能指定 expected_git_commit"
                )
        return self


class ResourceApproval(ResourceModel):
    decision: Literal["approved", "rejected"]
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decided_by: str = Field(min_length=1, max_length=200)
    decided_at: str
    reason: str | None = Field(
        default=None, max_length=500
    )


class ResourceManifest(ResourceModel):
    manifest_version: Literal["phase29-v1"] = "phase29-v1"
    # 计算时排除本字段自身；Job 用它冻结完整 Resource metadata snapshot。
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    resource_id: str
    kind: ResourceKind
    source_url_sanitized: str
    redirect_chain_sanitized: list[str] = Field(
        default_factory=list
    )
    object_key: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: str
    git_commit: str | None = None
    acquired_at: str


class ResourceRecord(ResourceModel):
    resource_id: str
    idempotency_key: str
    request: ResourceRequest
    request_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    approval: ResourceApproval | None = None
    status: ResourceStatus
    version: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    worker_id: str | None = None
    claim_token: str | None = None
    heartbeat_at: str | None = None
    lease_expires_at: str | None = None
    manifest: ResourceManifest | None = None
    error: dict | None = None
    created_at: str
    updated_at: str


class ResourceEvent(ResourceModel):
    event_id: int
    resource_id: str
    event_type: str
    actor: str
    payload: dict = Field(default_factory=dict)
    created_at: str
