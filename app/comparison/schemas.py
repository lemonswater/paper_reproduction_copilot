from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


ComparisonCategory = Literal[
    "input",
    "repository",
    "environment",
    "command",
    "execution",
    "error",
    "repair",
    "artifact",
]

ChangeKind = Literal[
    "added",
    "removed",
    "changed",
]

ChangeImportance = Literal[
    "high",
    "medium",
    "low",
]

EvidenceTrust = Literal[
    "control_plane",
    "verified_content",
    "catalog_identity",
]


class ComparisonModel(BaseModel):
    """Comparison 协议拒绝未知字段，防止版本漂移。"""

    model_config = ConfigDict(extra="forbid")


class ComparisonCreateRequest(ComparisonModel):
    base_job_id: str = Field(min_length=1, max_length=200)
    target_job_id: str = Field(min_length=1, max_length=200)
    # 默认拒绝跨论文比较；显式开启也只生成诊断警告。
    allow_cross_paper: bool = False

    @model_validator(mode="after")
    def reject_self_comparison(self) -> "ComparisonCreateRequest":
        if self.base_job_id == self.target_job_id:
            raise ValueError("base_job_id 与 target_job_id 不能相同")
        return self


class ComparisonEvidence(ComparisonModel):
    """Change 的有界证据身份，不含绝对路径和 Blob object key。"""

    trust: EvidenceTrust
    source_type: Literal[
        "job",
        "workspace_manifest",
        "run_manifest",
        "artifact_catalog",
    ]
    job_id: str
    run_id: str
    locator: str
    artifact_id: str | None = None
    relative_path: str | None = None
    sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    manifest_id: str | None = None
    manifest_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )


class CommandSnapshot(ComparisonModel):
    """Command 的可公开投影。display 已脱敏，raw 只保留 hash。"""

    present: bool = False
    display: str | None = Field(default=None, max_length=4000)
    command_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    cwd_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    source: str | None = None
    risk_level: str | None = None
    parse_degraded: bool = False


class DatasetIdentity(ComparisonModel):
    name: str
    uri_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fingerprint: str | None = None
    required_worker_label: str


class ErrorIdentity(ComparisonModel):
    code: str
    category: str
    stage: str
    terminal: bool
    # 错误消息可能包含路径或 Provider 细节，只比较内容身份。
    message_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ArtifactIdentity(ComparisonModel):
    artifact_id: str
    relative_path: str
    layer: str
    media_type: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    producer_node: str


class ExecutionFacts(ComparisonModel):
    final_status: str | None = None
    ok: bool | None = None
    returncode: int | None = None
    end_reason: str | None = None
    peak_rss_bytes: int | None = Field(default=None, ge=0)
    total_cpu_seconds: float | None = Field(default=None, ge=0.0)
    peak_process_count: int | None = Field(default=None, ge=0)
    total_write_bytes: int | None = Field(default=None, ge=0)


class RunSnapshot(ComparisonModel):
    snapshot_version: Literal["phase38-v1"] = "phase38-v1"
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    job_id: str
    run_id: str
    job_status: Literal["succeeded", "failed", "cancelled"]
    experiment_goal: str

    workspace_manifest_id: str
    workspace_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    workspace_manifest_generation: int = Field(ge=0)
    paper_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository_commit: str
    repository_clean: bool
    datasets: list[DatasetIdentity] = Field(default_factory=list)

    execution_profile_id: str
    execution_policy_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_backend: str
    execution_profile_fingerprint: str | None = None

    selected_command: CommandSnapshot
    execution: ExecutionFacts
    smoke_test_status: str | None = None
    smoke_test_passed: bool | None = None
    repair_attempt_count: int = Field(default=0, ge=0)
    file_repair_attempt_count: int = Field(default=0, ge=0)
    errors: list[ErrorIdentity] = Field(default_factory=list)
    artifacts: list[ArtifactIdentity] = Field(default_factory=list)

    run_manifest_artifact_id: str
    run_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RunChange(ComparisonModel):
    category: ComparisonCategory
    kind: ChangeKind
    importance: ChangeImportance
    field_path: str = Field(min_length=1, max_length=500)
    base_value: Any = None
    target_value: Any = None
    message: str = Field(min_length=1, max_length=1000)
    evidence: list[ComparisonEvidence] = Field(
        min_length=1,
        max_length=4,
    )


class ComparisonSummary(ComparisonModel):
    change_count: int = Field(ge=0)
    high_count: int = Field(ge=0)
    medium_count: int = Field(ge=0)
    low_count: int = Field(ge=0)
    changed_categories: list[ComparisonCategory] = Field(default_factory=list)
    artifact_added: int = Field(ge=0)
    artifact_removed: int = Field(ge=0)
    artifact_changed: int = Field(ge=0)
    scope_warnings: list[str] = Field(default_factory=list, max_length=20)


class ComparisonReport(ComparisonModel):
    schema_version: Literal["phase38-v1"] = "phase38-v1"
    comparator_version: Literal["phase38-v1"] = "phase38-v1"
    comparison_id: str = Field(pattern=r"^comparison_[0-9a-f]{24}$")
    comparison_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: str
    allow_cross_paper: bool
    base: RunSnapshot
    target: RunSnapshot
    summary: ComparisonSummary
    changes: list[RunChange]

    @model_validator(mode="after")
    def validate_summary_counts(self) -> "ComparisonReport":
        if self.base.job_id == self.target.job_id:
            raise ValueError("Comparison 不能比较同一 Job")
        if self.summary.change_count != len(self.changes):
            raise ValueError("summary.change_count 与 changes 数量不一致")
        importance_counts = {
            "high": self.summary.high_count,
            "medium": self.summary.medium_count,
            "low": self.summary.low_count,
        }
        for name, expected in importance_counts.items():
            actual = sum(item.importance == name for item in self.changes)
            if actual != expected:
                raise ValueError(f"summary {name}_count 不一致")
        actual_categories = sorted({item.category for item in self.changes})
        if sorted(self.summary.changed_categories) != actual_categories:
            raise ValueError("summary.changed_categories 不一致")
        return self


class ComparisonListItem(ComparisonModel):
    comparison_id: str
    comparison_hash: str
    base_job_id: str
    base_run_id: str
    target_job_id: str
    target_run_id: str
    change_count: int
    high_count: int
    changed_categories: list[ComparisonCategory]
    created_at: str

    @classmethod
    def from_report(cls, report: ComparisonReport) -> "ComparisonListItem":
        return cls(
            comparison_id=report.comparison_id,
            comparison_hash=report.comparison_hash,
            base_job_id=report.base.job_id,
            base_run_id=report.base.run_id,
            target_job_id=report.target.job_id,
            target_run_id=report.target.run_id,
            change_count=report.summary.change_count,
            high_count=report.summary.high_count,
            changed_categories=report.summary.changed_categories,
            created_at=report.created_at,
        )


class ComparisonListResponse(ComparisonModel):
    items: list[ComparisonListItem]
    count: int = Field(ge=0)
