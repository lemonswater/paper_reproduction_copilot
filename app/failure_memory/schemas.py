from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


SHA256 = r"^[0-9a-f]{64}$"

FailureCaseStatus = Literal[
    "candidate",
    "human_confirmed",
    "run_verified",
    "deprecated",
]

FailureCaseAuthority = Literal[
    "unverified_candidate",
    "human_confirmed_advice",
    "verified_precedent",
]

FailureCompatibility = Literal[
    "exact_applicable",
    "review_required",
    "reference_only",
    "incompatible",
]


class FailureMemoryModel(BaseModel):
    """长期记忆协议拒绝未知字段，避免静默扩大事实范围。"""

    model_config = ConfigDict(extra="forbid")


class FailureEnvironmentIdentity(FailureMemoryModel):
    """只保存稳定环境身份，不复制 PATH、env value 或 Secret。"""

    execution_profile_id: str = Field(min_length=1, max_length=200)
    execution_profile_fingerprint: str = Field(
        min_length=1,
        max_length=200,
    )
    execution_backend: Literal["local", "conda", "oci"]
    repository_commit: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40,64}$",
    )
    # dirty 工作区即使 HEAD 相同也不能判定为 exact applicable。
    repository_clean: bool | None = None


class FailureSignature(FailureMemoryModel):
    """由确定性代码生成的、与运行随机噪声无关的错误身份。"""

    signature_version: Literal["phase45-v1"] = "phase45-v1"
    stage: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)
    exception_type: str | None = Field(default=None, max_length=200)
    error_type: str = Field(min_length=1, max_length=128)
    normalized_tokens: list[str] = Field(
        default_factory=list,
        max_length=64,
    )
    frame_keys: list[str] = Field(
        default_factory=list,
        max_length=16,
    )
    signature_sha256: str = Field(pattern=SHA256)


class FailureEvidenceReference(FailureMemoryModel):
    """指向原 Run 中经过 Catalog 校验的 Artifact。"""

    purpose: Literal[
        "run_manifest",
        "error_report",
        "debug_report",
        "execution_verification",
        "process_log",
    ]
    artifact_id: str = Field(min_length=1, max_length=300)
    relative_path: str = Field(min_length=1, max_length=1000)
    sha256: str = Field(pattern=SHA256)
    size_bytes: int = Field(ge=0)


class FailureSourceIdentity(FailureMemoryModel):
    """candidate 创建时冻结的源失败 Run 身份。"""

    job_id: str = Field(min_length=1, max_length=200)
    job_version: int = Field(ge=0)
    run_id: str = Field(min_length=1, max_length=300)
    workspace_manifest_id: str = Field(min_length=1, max_length=200)
    workspace_manifest_hash: str = Field(pattern=SHA256)
    run_manifest_artifact_id: str = Field(min_length=1, max_length=300)
    run_manifest_sha256: str = Field(pattern=SHA256)
    final_status: str = Field(min_length=1, max_length=100)
    environment: FailureEnvironmentIdentity
    evidence: list[FailureEvidenceReference] = Field(
        min_length=1,
        max_length=8,
    )


class FailureRemedy(FailureMemoryModel):
    """人工确认的修复方向；它仍然不是 ExecutableAction。"""

    kind: Literal[
        "command_edit",
        "environment_change",
        "dependency_change",
        "source_patch",
        "data_fix",
        "manual_check",
        "unknown",
    ] = "unknown"
    summary: str = Field(min_length=1, max_length=2000)
    steps: list[str] = Field(default_factory=list, max_length=12)
    risks: list[str] = Field(default_factory=list, max_length=12)


class HumanConfirmation(FailureMemoryModel):
    actor: str = Field(min_length=1, max_length=100)
    diagnosis_summary: str = Field(min_length=1, max_length=2000)
    remedy: FailureRemedy
    applicability_note: str = Field(min_length=1, max_length=1000)
    confirmed_at: str


class FailureRunVerification(FailureMemoryModel):
    """失败源的派生子 Run 对修复提案的限定验证。"""

    job_id: str = Field(min_length=1, max_length=200)
    run_id: str = Field(min_length=1, max_length=300)
    run_manifest_artifact_id: str = Field(min_length=1, max_length=300)
    run_manifest_sha256: str = Field(pattern=SHA256)
    proposal_id: str = Field(min_length=1, max_length=200)
    proposal_hash: str = Field(pattern=SHA256)
    execution_verification_id: str = Field(min_length=1, max_length=300)
    execution_verification_sha256: str = Field(pattern=SHA256)
    environment: FailureEnvironmentIdentity
    verified_at: str


class FailureCaseRecord(FailureMemoryModel):
    case_version: Literal["phase45-v1"] = "phase45-v1"
    case_id: str = Field(pattern=r"^failure_[0-9a-f]{24}$")
    case_hash: str = Field(pattern=SHA256)
    version: int = Field(ge=0)
    status: FailureCaseStatus

    signature: FailureSignature
    source: FailureSourceIdentity
    candidate_diagnosis: str = Field(min_length=1, max_length=2000)
    candidate_remedy: FailureRemedy
    confirmation: HumanConfirmation | None = None
    verification: FailureRunVerification | None = None
    deprecation_reason: str | None = Field(default=None, max_length=1000)

    created_at: str
    updated_at: str

    @model_validator(mode="after")
    def validate_lifecycle_shape(self) -> "FailureCaseRecord":
        if self.status == "candidate":
            if self.confirmation is not None or self.verification is not None:
                raise ValueError("candidate 不能已有确认或验证")
        elif self.status == "human_confirmed":
            if self.confirmation is None or self.verification is not None:
                raise ValueError("human_confirmed 要求确认且不能已有验证")
        elif self.status == "run_verified":
            if self.confirmation is None or self.verification is None:
                raise ValueError("run_verified 要求确认和验证")
        elif not self.deprecation_reason:
            raise ValueError("deprecated 必须说明原因")
        return self


class FailureCaseCreateRequest(FailureMemoryModel):
    source_job_id: str = Field(min_length=1, max_length=200)
    expected_source_job_version: int = Field(ge=0)
    expected_run_manifest_sha256: str = Field(pattern=SHA256)


class FailureCaseConfirmRequest(FailureMemoryModel):
    expected_version: int = Field(ge=0)
    expected_case_hash: str = Field(pattern=SHA256)
    diagnosis_summary: str = Field(min_length=1, max_length=2000)
    remedy: FailureRemedy
    applicability_note: str = Field(min_length=1, max_length=1000)


class FailureCaseVerifyRequest(FailureMemoryModel):
    expected_version: int = Field(ge=0)
    expected_case_hash: str = Field(pattern=SHA256)
    verification_job_id: str = Field(min_length=1, max_length=200)
    expected_verification_manifest_sha256: str = Field(pattern=SHA256)


class FailureCaseDeprecateRequest(FailureMemoryModel):
    expected_version: int = Field(ge=0)
    expected_case_hash: str = Field(pattern=SHA256)
    reason: str = Field(min_length=1, max_length=1000)


class FailureCaseMutationResponse(FailureMemoryModel):
    case: FailureCaseRecord
    replayed: bool = False


class FailureQuery(FailureMemoryModel):
    signature: FailureSignature
    environment: FailureEnvironmentIdentity


class FailureScoreBreakdown(FailureMemoryModel):
    signature: float = Field(ge=0.0, le=1.0)
    stage_code: float = Field(ge=0.0, le=1.0)
    frames: float = Field(ge=0.0, le=1.0)
    tokens: float = Field(ge=0.0, le=1.0)
    environment: float = Field(ge=0.0, le=1.0)
    authority: float = Field(ge=0.0, le=1.0)
    total: float = Field(ge=0.0, le=1.0)


class FailureCaseMatch(FailureMemoryModel):
    case_id: str
    status: FailureCaseStatus
    authority: FailureCaseAuthority
    compatibility: FailureCompatibility
    score: FailureScoreBreakdown
    diagnosis_summary: str
    remedy: FailureRemedy
    applicability_note: str
    source_environment: FailureEnvironmentIdentity
    verification_environment: FailureEnvironmentIdentity | None = None
    evidence: list[FailureEvidenceReference] = Field(default_factory=list)


class FailureCasePack(FailureMemoryModel):
    query_signature_sha256: str = Field(pattern=SHA256)
    items: list[FailureCaseMatch] = Field(default_factory=list)
    generated_at: str
