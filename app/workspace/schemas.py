from __future__ import annotations

import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class WorkspaceModel(BaseModel):
    """共享控制面对象拒绝未知字段，防止版本漂移被静默吞掉。"""

    model_config = ConfigDict(extra="forbid")


class WorkerCapabilities(WorkspaceModel):
    """Worker 启动时从受信任配置加载的可调度能力。"""

    execution_profile_ids: list[str] = Field(min_length=1)
    execution_backends: list[Literal["local", "conda", "oci"]] = Field(
        min_length=1
    )
    # 代码根据本机 profile 计算并覆盖，不能盲信 JSON 文件。
    execution_policy_hashes: dict[str, str] = Field(default_factory=dict)
    cpu_count: int = Field(ge=1)
    memory_bytes: int = Field(ge=1)
    workspace_free_bytes: int = Field(ge=0)
    gpu_count: int = Field(default=0, ge=0)
    cuda_major: int | None = Field(default=None, ge=1)
    labels: list[str] = Field(default_factory=list)
    # key 是受信任 dataset label；API 公开视图不能返回 host-local path。
    dataset_mounts: dict[str, str] = Field(default_factory=dict)
    capability_version: str = "phase26-v1"

    @field_validator(
        "execution_profile_ids",
        "execution_backends",
        "labels",
    )
    @classmethod
    def unique_non_empty(cls, values: list[str]) -> list[str]:
        normalized = sorted({str(item).strip() for item in values})
        if any(not item for item in normalized):
            raise ValueError("capability 列表不能包含空字符串")
        return normalized

    @model_validator(mode="after")
    def validate_cuda(self) -> WorkerCapabilities:
        if self.gpu_count == 0 and self.cuda_major is not None:
            raise ValueError("没有 GPU 时不能声明 cuda_major")
        return self


class WorkerIdentity(WorkspaceModel):
    worker_id: str = Field(min_length=1, max_length=200)
    worker_session_id: str = Field(min_length=1, max_length=200)
    host_id: str = Field(min_length=1, max_length=200)
    pool: str = Field(min_length=1, max_length=100)
    workspace_root: str = Field(min_length=1)
    capabilities: WorkerCapabilities


class WorkerSession(WorkerIdentity):
    status: Literal["active", "draining", "offline"]
    registered_at: str
    heartbeat_at: str
    lease_expires_at: str


class JobRequirements(WorkspaceModel):
    """由受信任 Execution Profile 派生，不能接受 LLM 自由生成。"""

    worker_pool: str = "default"
    execution_profile_id: str = Field(min_length=1)
    execution_policy_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_backend: Literal["local", "conda", "oci"]
    min_workspace_free_bytes: int = Field(default=0, ge=0)
    min_gpu_count: int = Field(default=0, ge=0)
    cuda_major: int | None = Field(default=None, ge=1)
    required_labels: list[str] = Field(default_factory=list)

    @field_validator("required_labels")
    @classmethod
    def normalize_labels(cls, values: list[str]) -> list[str]:
        labels = sorted({item.strip() for item in values})
        if any(not item for item in labels):
            raise ValueError("required_labels 不能包含空字符串")
        return labels


class RepositoryIdentity(WorkspaceModel):
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    branch: str = Field(min_length=1)
    clean: bool
    # dirty/host-affine fallback 没有可迁移 bundle。
    bundle_logical_path: str | None = None
    has_submodules: bool = False
    has_lfs: bool = False


WorkspaceEntryRole = Literal[
    "paper",
    "input_log",
    "repository_bundle",
    "run_artifact",
    "process_record",
    "process_log",
]


class WorkspaceBlobEntry(WorkspaceModel):
    logical_path: str
    role: WorkspaceEntryRole
    object_key: str
    sha256: str
    size_bytes: int = Field(ge=0)
    media_type: str = "application/octet-stream"
    executable: bool = False

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        lowered = value.lower()
        if not SHA256_PATTERN.fullmatch(lowered):
            raise ValueError("sha256 必须是 64 位小写十六进制")
        return lowered


class ExternalDataReference(WorkspaceModel):
    """数据集只保存引用和可达性要求，不自动上传内容。"""

    name: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    fingerprint: str | None = None
    required_worker_label: str = Field(min_length=1)


class WorkspaceSourcePaths(WorkspaceModel):
    """仅供同一 affinity host 复用；不能把这些路径当跨主机地址。"""

    run_dir: str | None = None
    repo_path: str
    paper_path: str
    log_path: str | None = None


WorkspaceMaterializationMode = Literal[
    "auto",
    "host_paths",
    "blob_entries",
]


class WorkspaceManifest(WorkspaceModel):
    manifest_version: Literal[
        "phase26-v1",
        "phase39-v2",
    ] = "phase39-v2"
    manifest_id: str
    manifest_hash: str
    job_id: str
    run_id: str
    generation: int = Field(ge=0)
    parent_manifest_id: str | None = None
    source_host_id: str
    source_worker_session_id: str | None = None
    entries: list[WorkspaceBlobEntry]
    repository: RepositoryIdentity
    external_data: list[ExternalDataReference] = Field(
        default_factory=list
    )
    portable: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    source_paths: WorkspaceSourcePaths | None = None

    # auto 保持 phase26 语义：portable 从 Blob，non-portable 从 host path。
    materialization_mode: WorkspaceMaterializationMode = "auto"
    created_at: str

    def resolved_materialization_mode(
        self,
    ) -> Literal["host_paths", "blob_entries"]:
        if self.materialization_mode != "auto":
            return self.materialization_mode
        return "blob_entries" if self.portable else "host_paths"

    @model_validator(mode="after")
    def validate_portability(self) -> WorkspaceManifest:
        logical_paths = [item.logical_path for item in self.entries]
        if len(logical_paths) != len(set(logical_paths)):
            raise ValueError("manifest logical_path 重复")
        if self.manifest_version == "phase26-v1":
            if self.materialization_mode != "auto":
                raise ValueError("phase26-v1 只能使用 auto materialization")

        if self.portable and self.blocked_reasons:
            raise ValueError("portable manifest 不能包含 blocked_reasons")
        if not self.portable and not self.blocked_reasons:
            raise ValueError("non-portable manifest 必须说明原因")
        if self.portable and self.materialization_mode == "host_paths":
            raise ValueError("portable manifest 不能强制复用 host_paths")

        mode = self.resolved_materialization_mode()
        if mode == "host_paths" and self.source_paths is None:
            raise ValueError("host_paths materialization 缺少 source_paths")
        if mode == "blob_entries":
            paper = [item for item in self.entries if item.role == "paper"]
            bundles = [
                item
                for item in self.entries
                if item.role == "repository_bundle"
            ]
            if len(paper) != 1 or len(bundles) != 1:
                raise ValueError(
                    "blob_entries materialization 需要唯一 paper 和 repository bundle"
                )
            if not self.repository.clean:
                raise ValueError("blob_entries 不能物化 dirty repository")
        return self


class WorkspaceBinding(WorkspaceModel):
    assignment_id: str
    assignment_epoch: int = Field(ge=1)
    assignment_token: str
    job_id: str
    run_id: str
    manifest_id: str
    manifest_hash: str
    manifest_generation: int = Field(ge=0)
    worker_session_id: str
    host_id: str
    workspace_root: str
    run_dir: str
    repo_path: str
    paper_path: str
    log_path: str | None = None
    status: Literal[
        "materializing",
        "ready",
        "released",
        "failed",
        "garbage_collected",
    ]
    created_at: str
    updated_at: str


class SchedulingExplanation(WorkspaceModel):
    compatible: bool
    reasons: list[str] = Field(default_factory=list)
