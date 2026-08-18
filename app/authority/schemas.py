from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.schemas import PatchVerificationCheck

AuthorityRole = Literal["planner", "executor", "verifier"]

AuthorityCapability = Literal[
    "read_evidence",
    "create_proposal",
    "execute_action",
    "apply_repository_change",
    "verify_evidence",
    "project_terminal_status",
]

VerificationVerdict = Literal[
    "verified",
    "failed",
    "inconclusive",
]

SHA256_PATTERN = r"^[0-9a-f]{64}$"


class AuthorityModel(BaseModel):
    """Authority 数据默认拒绝未知字段，防止权限字段静默扩张。"""

    model_config = ConfigDict(extra="forbid")


class NodeAuthorityContract(AuthorityModel):
    """声明某类节点拥有的角色和能力。"""

    role: AuthorityRole
    capabilities: set[AuthorityCapability] = Field(
        default_factory=set
    )
    forbidden_output_fields: set[str] = Field(
        default_factory=set
    )


class AuthorityAuditRecord(AuthorityModel):
    """只记录 authority 元数据和 Hash，不记录节点原始输入输出。"""

    schema_version: Literal["phase43-v1"] = "phase43-v1"
    node_name: str = Field(min_length=1, max_length=128)
    role: AuthorityRole
    capabilities: list[AuthorityCapability] = Field(
        default_factory=list
    )
    output_fields: list[str] = Field(default_factory=list)
    output_sha256: str = Field(pattern=SHA256_PATTERN)
    recorded_at: str


class ExecutionEvidence(AuthorityModel):
    """Executor 对一次受监管进程执行所保留的不可变事实摘要。

    这里不保存完整 stdout/stderr。完整内容继续位于 Artifact，避免
    Checkpoint 膨胀，也避免把日志中的潜在敏感信息复制到控制状态。
    """

    schema_version: Literal["phase43-v1"] = "phase43-v1"
    evidence_id: str = Field(min_length=1, max_length=160)

    action_id: str = Field(min_length=1, max_length=160)
    action_sha256: str = Field(pattern=SHA256_PATTERN)

    execution_id: str | None = None
    execution_profile_id: str | None = None
    execution_profile_fingerprint: str | None = None
    execution_backend: str | None = None

    end_reason: str = Field(min_length=1, max_length=80)
    returncode: int | None = None

    process_record_path: str | None = None
    combined_log_path: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    resource_usage: dict[str, Any] = Field(default_factory=dict)

    recorded_at: str
    evidence_sha256: str = Field(pattern=SHA256_PATTERN)


class VerificationCheck(AuthorityModel):
    """Verifier 的单项确定性检查。"""

    name: str = Field(min_length=1, max_length=128)
    passed: bool
    detail: str = Field(default="", max_length=2000)


class ExecutionVerificationRecord(AuthorityModel):
    """对 ExecutionEvidence 的限定作用域结论。

    claim_scope 固定为 execution_protocol。即使 verdict=verified，也只说明
    Action/证据身份一致且受监管进程正常退出，不说明论文指标已复现。
    """

    schema_version: Literal["phase43-v1"] = "phase43-v1"
    verification_id: str = Field(min_length=1, max_length=180)
    claim_scope: Literal["execution_protocol"] = (
        "execution_protocol"
    )

    action_id: str
    action_sha256: str = Field(pattern=SHA256_PATTERN)
    evidence_id: str
    evidence_sha256: str = Field(pattern=SHA256_PATTERN)

    verdict: VerificationVerdict
    projected_final_status: str
    checks: list[VerificationCheck] = Field(default_factory=list)
    summary: str = Field(min_length=1, max_length=4000)

    verified_at: str
    verification_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_scope_semantics(
        self,
    ) -> ExecutionVerificationRecord:
        if self.verdict == "verified":
            if self.projected_final_status != "succeeded":
                raise ValueError(
                    "verified execution_protocol 必须投影为 succeeded"
                )
            if not self.checks or not all(
                item.passed for item in self.checks
            ):
                raise ValueError(
                    "verified 要求所有确定性检查通过"
                )
        return self


class PatchVerificationEvidence(AuthorityModel):
    """Patch Executor 运行检查后的原始证据，不包含 promotion verdict。"""

    schema_version: Literal["phase43-v1"] = "phase43-v1"
    evidence_id: str = Field(min_length=1, max_length=180)

    patch_id: str
    patch_sha256: str = Field(pattern=SHA256_PATTERN)
    execution_profile_id: str
    execution_profile_fingerprint: str
    execution_backend: Literal["local", "conda"]

    worktree_path: str | None = None
    worktree_diff_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    checks: list[PatchVerificationCheck] = Field(
        default_factory=list
    )

    collected_at: str
    evidence_sha256: str = Field(pattern=SHA256_PATTERN)
