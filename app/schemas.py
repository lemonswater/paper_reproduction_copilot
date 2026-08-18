from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.secrets.schemas import SecretReference

Confidence = Literal["low", "medium", "high"]

SECRET_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

ArtifactLayer = Literal[
    "inputs",
    "analysis",
    "planning",
    "execution",
    "debug",
    "patches",
    "reports",
    "traces",
]

ErrorCategory = Literal[
    "user",
    "agent",
    "environment",
    "provider",
    "paper_program",
]

ExecutionEndReason = Literal[
    "exited",
    "launch_error",
    "timeout",
    "cancelled",
    "interrupted",
    "cpu_limit",
    "memory_limit",
    "process_limit",
    "write_limit",
    "gpu_limit",
    "policy_denied",
    "supervisor_error",
    "orphan_cleanup"
]

EvalCategory = Literal[
    "schema",
    "route",
    "tool",
    "evidence",
    "safety",
    "recovery",
    "quality",
    "efficiency",
]

EvalRunnerKind = Literal[
    "fixture",
    "route_function",
    "live_graph",
]

class ArtifactRecord(BaseModel):
    """
    一个 Artifact 在生成完成时的不可变元数据。

    relative_path 是相对 run_dir 的稳定身份，absolute_path 只用于本地
    CLI，并且必须经过 run_dir 边界校验。
    """

    artifact_id: str
    run_id: str
    layer: ArtifactLayer
    relative_path: str
    absolute_path: str
    media_type: str
    sha256: str
    size_bytes: int = Field(ge=0)
    producer_node: str
    created_at: str


class Evidence(BaseModel):
    source_type: Literal["paper", "code", "readme", "config", "log"]
    source_path: str
    location: str | None = None
    quote_or_summary: str
    confidence: Confidence = "medium"

    # Phase 18：全部提供默认值，保证旧 JSON 仍然可以加载。
    evidence_id: str | None = None
    document_id: str | None = None
    section_id: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    block_ids: list[str] = Field(default_factory=list)
    content_hash: str | None = None

    # Phase 20：代码 Evidence provenance。
    # 这些字段全部保留默认值，以兼容 Phase 20 之前的 JSON。
    repo_revision: str | None = None
    repo_fingerprint: str | None = None
    file_sha256: str | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    retrieval_channels: list[str] = Field(default_factory=list)
    retrieval_score: float | None = Field(default=None, ge=0.0)


class MethodModule(BaseModel):
    name: str
    description: str
    possible_keywords: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)

class ExperimentSetting(BaseModel):
    name: str
    value: str
    evidence: list[Evidence] = Field(default_factory=list)


class PaperSummary(BaseModel):
    title: str | None = None
    research_problem: str
    core_idea: str
    method_modules: list[MethodModule] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    experiment_settings: list[ExperimentSetting] = Field(default_factory=list)
    reproduction_risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


class RepoMap(BaseModel):
    repo_path: str
    readme_files: list[str] = Field(default_factory=list)
    train_entries: list[str] = Field(default_factory=list)
    eval_entries: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    model_files: list[str] = Field(default_factory=list)
    dataset_files: list[str] = Field(default_factory=list)
    loss_files: list[str] = Field(default_factory=list)
    important_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CodeCandidate(BaseModel):
    file_path: str
    symbols: list[str] = Field(default_factory=list)
    reason: str

    # 模型只能引用 Evidence Pack 中已有的 ID。
    # mapping_node 会再次验证，不会直接信任模型返回。
    evidence_ids: list[str] = Field(default_factory=list)

    # evidence 最终由程序根据 evidence_ids 重建，
    # 不直接接受模型编造的 quote、hash 或行号。
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence = "medium"


CodeMappingTargetCategory = Literal[
    "core_method",
    "data_pipeline",
    "training_config",
    "evaluation_metric",
    "ablation_switch",
]


class CodeMappingTarget(BaseModel):
    """进入代码检索的、经过确定性去重和预算控制的论文事实。"""

    target_id: str
    category: CodeMappingTargetCategory
    name: str
    description: str
    aliases: list[str] = Field(default_factory=list)
    possible_keywords: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    source_evidence_ids: list[str] = Field(default_factory=list)


class ModuleMapping(BaseModel):
    module_name: str
    # 保留 module_name 兼容旧 Artifact；新流程用下面两个字段表达分类目标。
    target_id: str | None = None
    target_category: CodeMappingTargetCategory = "core_method"
    candidates: list[CodeCandidate] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)

class ExperimentStep(BaseModel):
    order: int
    name: str
    action: str
    source: Literal["paper", "readme", "config", "script", "inferred", "need_confirm"]
    evidence: list[Evidence] = Field(default_factory=list)
    risk: str | None = None
    done: bool = False

class RunCommand(BaseModel):
    command: str
    cwd: str
    source: Literal["readme", "script", "config", "inferred", "need_confirm"]
    risk_level: Literal["low", "medium", "high"]
    reason: str

class ExperimentPlan(BaseModel):
    goal: str
    environment_steps: list[ExperimentStep] = Field(default_factory=list)
    data_steps: list[ExperimentStep] = Field(default_factory=list)
    train_steps: list[ExperimentStep] = Field(default_factory=list)
    eval_steps: list[ExperimentStep] = Field(default_factory=list)
    run_commands: list[RunCommand] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)

class ResourceBudget(BaseModel):
    """
    单次受监管执行允许使用的最大资源。

    max_wall_time_seconds 是墙钟时间，不等价于 CPU 时间。
    max_write_bytes 读取进程树 I/O 计数，是近似监管值，不等价于
    文件系统 quota。
    """

    max_wall_time_seconds: float = Field(default=300.0, gt=0)
    max_cpu_seconds: float | None = Field(default=None, gt=0)
    max_memory_bytes: int | None = Field(default=None, gt=0)
    max_processes: int = Field(default=32, ge=1)
    max_write_bytes: int | None = Field(default=None, gt=0)
    max_gpu_memory_bytes: int | None = Field(default=None, gt=0)

    # stdout 和 stderr 分别最多落盘多少字节。
    max_log_bytes_per_stream: int = Field(
        default=16 * 1024 * 1024,
        ge=4096,
    )

    # 返回到 Graph state 的每个 preview 上限。
    max_preview_bytes: int = Field(
        default=64 * 1024,
        ge=1024,
    )

    sample_interval_seconds: float = Field(
        default=0.2,
        gt=0,
        le=5,
    )
    terminate_grace_seconds: float = Field(
        default=5.0,
        ge=0,
        le=60,
    )


class ResourceBudgetOverride(BaseModel):
    """
    Action 对 Profile Budget 的收紧请求。

    所有字段默认 None，表示沿用 profile；这样不会因为 Pydantic 默认值
    无意中把 profile 上限放宽。
    """

    max_wall_time_seconds: float | None = Field(
        default=None,
        gt=0,
    )
    max_cpu_seconds: float | None = Field(default=None, gt=0)
    max_memory_bytes: int | None = Field(default=None, gt=0)
    max_processes: int | None = Field(default=None, ge=1)
    max_write_bytes: int | None = Field(default=None, gt=0)
    max_gpu_memory_bytes: int | None = Field(default=None, gt=0)
    max_log_bytes_per_stream: int | None = Field(
        default=None,
        ge=4096,
    )
    max_preview_bytes: int | None = Field(
        default=None,
        ge=1024,
    )
    sample_interval_seconds: float | None = Field(
        default=None,
        gt=0,
        le=5,
    )
    terminate_grace_seconds: float | None = Field(
        default=None,
        ge=0,
        le=60,
    )


class OciExecutionConfig(BaseModel):
    """只保存确定性运行参数，不保存 registry 凭据或任意 Podman flags。

    ``image_ref`` 必须写成 ``name@sha256:<64 hex>``，禁止 ``latest``
    和仅 tag 引用。运行时固定使用 ``--pull=never``，绝不隐式联网。
    """

    image_ref: str
    runtime: Literal["podman"] = "podman"
    container_repo_root: str = "/workspace/repo"
    container_run_root: str = "/workspace/run"
    memory_bytes: int = Field(ge=256 * 1024 * 1024)
    cpus: float = Field(gt=0, le=64)
    pids_limit: int = Field(default=512, ge=32, le=32768)
    tmpfs_bytes: int = Field(
        default=512 * 1024 * 1024, ge=16 * 1024 * 1024
    )

    @model_validator(mode="after")
    def require_digest_pinned_image(self) -> OciExecutionConfig:
        prefix, separator, digest = self.image_ref.rpartition(
            "@sha256:"
        )
        if not separator or not prefix:
            raise ValueError(
                "OCI image_ref 必须包含 @sha256:<64 hex>"
            )
        if len(digest) != 64 or any(
            ch not in "0123456789abcdef" for ch in digest
        ):
            raise ValueError(
                "OCI image digest 必须是 64 位小写十六进制"
            )
        return self


class ExecutionProfile(BaseModel):
    """
    由项目维护者提供的受信任执行策略。

    LLM 只能选择 profile_id，不能生成或修改 profile 内容。
    """

    profile_id: str
    backend: Literal["local", "conda", "oci"]
    workspace_root: str
    artifact_root: str

    conda_executable: str | None = None
    conda_prefix: str | None = None

    # 只从 Agent 环境继承这些非敏感变量。
    inherited_env_keys: list[str] = Field(
        default_factory=lambda: [
            "PATH",
            "LANG",
            "LC_ALL",
            "TERM",
        ]
    )

    # Profile 固定注入的普通变量。禁止写入 secret。
    env: dict[str, str] = Field(default_factory=dict)

    # Action 只能覆盖这里列出的环境变量。
    allowed_action_env_keys: list[str] = Field(default_factory=list)

    # Phase 41：只有这里列出的 key 能由 Secret Binding 注入。
    # 该列表属于受信任 Profile，并进入 Profile Fingerprint。
    allowed_secret_env_keys: list[str] = Field(default_factory=list)

    # 只允许 basename 精确匹配，避免 substring 绕过。
    allowed_programs: list[str] = Field(
        default_factory=lambda: [
            "python",
            "python3",
            "torchrun",
            "accelerate",
            "pytest",
        ]
    )

    # 第一版按 args token 的包含关系阻断明显危险入口。
    blocked_arg_markers: list[str] = Field(
        default_factory=lambda: [
            "\n",
            "\r",
            "\x00",
        ]
    )

    writable_roots: list[str] = Field(default_factory=list)
    network_policy: Literal["deny", "allow"] = "deny"
    budget: ResourceBudget = Field(default_factory=ResourceBudget)

    # best_effort 表示 local/conda 只有策略检查和进程监管。
    # strict 预留给真正支持 OS 隔离的 runner。
    enforcement_mode: Literal["best_effort", "strict"] = "best_effort"

    # Phase 26：这些字段由项目维护者配置，不允许 Job/LLM 降低要求。
    worker_pool: str = "default"
    min_workspace_free_bytes: int = Field(default=0, ge=0)
    min_gpu_count: int = Field(default=0, ge=0)
    cuda_major: int | None = Field(default=None, ge=1)
    required_worker_labels: list[str] = Field(default_factory=list)

    # Phase 27：OCI 后端的确定性容器配置。
    # 非 OCI backend 不能携带此字段；OCI backend 必须提供。
    oci: OciExecutionConfig | None = None

    @model_validator(mode="after")
    def validate_backend_fields(self) -> ExecutionProfile:
        if self.backend == "conda":
            if not self.conda_executable:
                raise ValueError(
                    "conda 执行后端要求提供 conda_executable"
                )
            if not self.conda_prefix:
                raise ValueError(
                    "conda 执行后端要求提供 conda_prefix"
                )

        if (
            self.backend in {"local", "conda"}
            and self.enforcement_mode == "strict"
        ):
            raise ValueError(
                "local/conda 不支持 strict OS isolation；"
                "请使用 best_effort 或后续容器 Runner"
            )

        if self.backend == "oci":
            if self.enforcement_mode != "strict":
                raise ValueError(
                    "OCI backend 必须使用 strict enforcement"
                )
            if self.oci is None:
                raise ValueError(
                    "OCI backend 缺少 oci 配置"
                )
            if self.network_policy != "deny":
                raise ValueError(
                    "Phase 27 OCI 第一版只允许 network_policy=deny"
                )
        elif self.oci is not None:
            raise ValueError(
                "非 OCI backend 不能携带 oci 配置"
            )

        if not self.writable_roots:
            self.writable_roots = [self.workspace_root]

        if self.min_gpu_count == 0 and self.cuda_major is not None:
            raise ValueError("cuda_major 要求至少一个 GPU")
        if not self.worker_pool.strip():
            raise ValueError("worker_pool 不能为空")
        self.required_worker_labels = sorted(
            {item.strip() for item in self.required_worker_labels}
        )
        if any(not item for item in self.required_worker_labels):
            raise ValueError("required_worker_labels 不能包含空值")

        # Phase 41：校验 allowed_secret_env_keys
        self.allowed_secret_env_keys = sorted(
            set(self.allowed_secret_env_keys)
        )
        if any(
            not SECRET_ENV_NAME_RE.fullmatch(item)
            for item in self.allowed_secret_env_keys
        ):
            raise ValueError(
                "allowed_secret_env_keys 包含无效变量名"
            )
        if set(self.allowed_secret_env_keys).intersection(
            self.allowed_action_env_keys
        ):
            raise ValueError(
                "同一变量不能同时作为普通 env 和 Secret env"
            )
        if self.backend == "oci" and self.allowed_secret_env_keys:
            raise ValueError(
                "Phase 41 第一版 OCI 不支持 Secret env；"
                "必须使用安全的容器 Secret Driver 后再开放"
            )
        return self

class SecretBinding(BaseModel):
    """Action 中只保存引用，绝不保存明文。"""

    env_name: str = Field(
        min_length=1,
        max_length=128,
        pattern=SECRET_ENV_NAME_RE.pattern,
    )
    reference: SecretReference


class ExecutableAction(BaseModel):
    action_id: str
    action_type: Literal["run_command"] = "run_command"
    program: str
    args: list[str] = Field(default_factory=list)
    cwd: str
    source: Literal[
        "readme",
        "script",
        "config",
        "inferred",
        "need_confirm",
    ]
    reason: str
    timeout_seconds: int = Field(default=300, gt=0)

    # 兼容读取 Phase 15 的 env_allowlist；新 model_dump 只写 env_overrides。
    env_overrides: dict[str, str] = Field(
        default_factory=dict,
        validation_alias=AliasChoices(
            "env_overrides",
            "env_allowlist",
        ),
    )

    # Phase 41：name/version/fingerprint 会自然进入 model_dump 和 Action Hash。
    secret_bindings: list[SecretBinding] = Field(
        default_factory=list
    )

    writable_paths: list[str] = Field(default_factory=list)
    network_access: Literal["none", "outbound"] = "none"

    # None 表示完全使用 profile budget。
    # 非 None 时只能收紧 profile，不能放宽。
    resource_budget: ResourceBudgetOverride | None = None

    risk: dict[str, Any] | None = None
    execution_profile_id: str
    execution_profile_fingerprint: str
    repo_patch_hash: str | None = None

    @model_validator(mode="after")
    def validate_secret_bindings(self) -> "ExecutableAction":
        env_names = [
            item.env_name for item in self.secret_bindings
        ]
        if len(env_names) != len(set(env_names)):
            raise ValueError(
                "secret_bindings env_name 不能重复"
            )
        if set(env_names).intersection(self.env_overrides):
            raise ValueError(
                "同一 env_name 不能同时出现在普通值和 Secret Binding"
            )
        return self

class ApprovalRecord(BaseModel):
    approval_id: str
    action_id: str
    action_hash: str
    decision: Literal["approved", "rejected", "revise"]
    reviewer: str = "human"
    risk_level: str
    reviewed_at: str
    comment: str | None = None

# HTTP、CLI 和 Graph 共用的硬上限。它限制单条人工编辑的内存、日志和
# checkpoint 体积，不表示命令达到该长度就一定能通过后续 Risk Check。
MAX_COMMAND_EDIT_CHARS = 8192
MAX_COMMAND_SELECTION_EDITS = 128


class CommandEdit(BaseModel):
    """用户对候选命令的索引化替换；不允许静默忽略未知字段。"""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    command: str = Field(
        min_length=1,
        max_length=MAX_COMMAND_EDIT_CHARS,
    )


class CommandSelectionResponse(BaseModel):
    """Graph interrupt 和 CLI 共同接受的命令选择响应。"""

    model_config = ConfigDict(extra="forbid")

    selected_index: int = Field(ge=0)
    edits: list[CommandEdit] = Field(
        default_factory=list,
        max_length=MAX_COMMAND_SELECTION_EDITS,
    )
    # CLI 兼容层先保留 min_length；API schema 会进一步要求 64 hex。
    run_commands_hash: str = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_edit_indexes(
        self,
    ) -> CommandSelectionResponse:
        indexes = [item.index for item in self.edits]
        if len(indexes) != len(set(indexes)):
            raise ValueError(
                "同一命令索引不能在一次 decision 中重复编辑"
            )
        return self


class CommandSelectionRecord(BaseModel):
    selected_index: int = Field(ge=0)
    edits: list[CommandEdit] = Field(default_factory=list)
    original_count: int = Field(ge=1)
    run_commands_hash: str = Field(min_length=1)
    reviewed_at: str

class DebugReport(BaseModel):
    error_type: str
    most_likely_causes: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    check_order: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    # Phase 45：只能引用当前 Failure Case Pack 中允许的 case id。
    historical_failure_case_ids: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

class PreflightItem(BaseModel):
    name: str
    category: Literal["static", "runtime", "smoke"] = "static"
    status: Literal["passed", "warning", "failed", "unknown"]
    evidence: str
    recommendation: str | None = None

class PreflightReport(BaseModel):
    action_id: str | None = None
    action_hash: str | None = None
    ready_to_execute: bool = False
    summary: str
    items: list[PreflightItem] = Field(default_factory=list)
    blocking_items: list[str] = Field(default_factory=list)
    execution_enforcement_mode: str | None = None
    network_os_enforced: bool = False
    writable_paths_os_enforced: bool = False
    resource_monitors_available: dict[str, bool] = Field(
        default_factory=dict
    )
    process_group_supported: bool = False
    generated_at: str

class SmokeTestReport(BaseModel):
    action_id: str | None = None
    action_hash: str | None = None
    status: Literal["passed", "failed", "skipped", "blocked"]

    summary: str
    applied_overrides: list[str] = Field(default_factory=list)
    command_preview: str | None = None
    log_path: str | None = None
    result: dict = Field(default_factory=dict)
    generated_at: str

class RepairStep(BaseModel):
    step_type: Literal[
        "edit_command",
        "manual_check",
        "rerun_smoke",
        "rerun_full",
    ]
    target: str
    change: str
    reason: str
    risk: Literal["low", "medium", "high"] = "low"

class RepairProposal(BaseModel):
    proposal_id: str | None = None
    source_error_type: str

    # edit_command: 当前阶段允许自动进入 bounded rerun
    # manual_only: 只给建议，不自动继续
    # no_repair: 暂无可靠修复路径
    kind: Literal["edit_command", "manual_only", "no_repair"] = "no_repair"

    summary: str
    root_cause: str

    # 只有 kind=edit_command 时才应提供。
    repaired_command: str | None = None
    changed_arguments: list[str] = Field(default_factory=list)

    steps: list[RepairStep] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    # 这一阶段所有 repair proposal 都应该保持 bounded=True。
    bounded: bool = True

    @model_validator(mode="after")
    def validate_repair_semantics(self) -> RepairProposal:
        """
        字段类型正确不代表 proposal 可以安全进入 repair 链。

        这里校验字段之间的业务关系：
        - 所有 proposal 都必须是 bounded；
        - edit_command 必须给出完整命令；
        - 非 edit_command 不允许偷偷携带命令；
        - edit_command 必须说明如何验证和回滚。
        """
        if self.bounded is not True:
            raise ValueError("修复建议必须保持 bounded=true")

        if self.kind == "edit_command":
            if not self.repaired_command or not self.repaired_command.strip():
                raise ValueError("edit_command 要求提供 repaired_command")
            if not self.changed_arguments:
                raise ValueError("edit_command 要求提供 changed_arguments")
            if not self.verification_steps:
                raise ValueError("edit_command 要求提供 verification_steps")
            if not self.rollback_steps:
                raise ValueError("edit_command 要求提供 rollback_steps")
        elif self.repaired_command is not None:
            raise ValueError(
                "manual_only/no_repair 不能包含 repaired_command"
            )

        return self

class StructuredOutputProbe(BaseModel):
    status: Literal["ok"]
    value: int

class TextReplacement(BaseModel):
    """LLM 提出的一个精确文本替换，不包含路径和 shell 命令。"""

    old_text: str
    new_text: str
    reason: str

    @model_validator(mode="after")
    def validate_replacement(self) -> TextReplacement:
        if not self.old_text:
            raise ValueError("old_text 不能为空")
        if self.old_text == self.new_text:
            raise ValueError("old_text 和 new_text 必须不同")
        return self

class FileEditDraft(BaseModel):
    """针对一个已有仓库文件的有限修改。"""

    relative_path: str
    reason: str
    replacements: list[TextReplacement] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_file_edit(self) -> FileEditDraft:
        if not self.relative_path.strip():
            raise ValueError("relative_path 不能为空")
        if not self.replacements:
            raise ValueError("文件修改至少需要一个 replacement")
        return self

class FileRepairProposal(BaseModel):
    """模型层的文件修复建议；它还不是可应用 patch。"""

    proposal_id: str | None = None
    kind: Literal["patch", "manual_only", "no_patch"] = "no_patch"
    summary: str
    root_cause: str
    edits: list[FileEditDraft] = Field(default_factory=list)
    verification_targets: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    bounded: bool = True

    @model_validator(mode="after")
    def validate_file_repair_semantics(self) -> FileRepairProposal:
        if self.bounded is not True:
            raise ValueError("文件修复建议必须保持 bounded=true")

        if self.kind == "patch" and not self.edits:
            raise ValueError("kind=patch 要求提供 edits")

        if self.kind != "patch" and self.edits:
            raise ValueError("manual_only/no_patch 不能包含 edits")

        return self

class PatchFileRecord(BaseModel):
    """程序生成的单文件 patch 元数据。"""

    relative_path: str
    before_sha256: str
    after_sha256: str
    replacement_count: int
    changed_line_count: int

class PatchBundle(BaseModel):
    """可供审批和验证的确定性 patch 包。"""

    patch_id: str
    proposal_id: str
    repo_path: str
    base_git_commit: str
    patch_path: str
    patch_sha256: str
    files: list[PatchFileRecord] = Field(default_factory=list)
    summary: str
    generated_at: str

class PatchApprovalRecord(BaseModel):
    """第一次人工审批：是否允许验证这一份 patch。"""

    approval_id: str
    patch_id: str
    patch_sha256: str
    decision: Literal["approved", "rejected", "revise"]
    reviewer: str = "human"
    reviewed_at: str
    comment: str | None = None

class PatchVerificationCheck(BaseModel):
    name: str
    status: Literal["passed", "failed", "skipped"]
    command: list[str] = Field(default_factory=list)
    returncode: int | None = None
    output_preview: str = ""

class PatchVerificationReport(BaseModel):
    """隔离 worktree 中的 patch-level 验证结果。"""

    patch_id: str
    patch_sha256: str
    execution_profile_id: str
    execution_profile_fingerprint: str
    execution_backend: Literal["local", "conda"]

    status: Literal[
        "behaviorally_verified",
        "structurally_valid",
        "failed",
        "blocked",
    ]
    promotion_allowed: bool = False
    structural_checks_passed: bool = False
    behavioral_checks_run: int = 0
    behavioral_checks_passed: int = 0

    worktree_path: str | None = None
    worktree_diff_sha256: str | None = None
    checks: list[PatchVerificationCheck] = Field(default_factory=list)
    summary: str
    generated_at: str
    verification_sha256: str | None = None

    @model_validator(mode="after")
    def validate_verification_semantics(self) -> PatchVerificationReport:
        if self.status == "behaviorally_verified":
            if not self.structural_checks_passed:
                raise ValueError(
                    "behaviorally_verified 要求结构检查通过"
                )
            if self.behavioral_checks_run < 1:
                raise ValueError(
                    "behaviorally_verified 要求至少运行一项行为检查"
                )
            if self.behavioral_checks_passed != self.behavioral_checks_run:
                raise ValueError("所有行为检查都必须通过")
            if self.promotion_allowed is not True:
                raise ValueError(
                    "behaviorally_verified 必须允许进入补丁应用审批"
                )
        elif self.promotion_allowed:
            raise ValueError(
                "只有 behaviorally_verified 状态才允许进入补丁应用审批"
            )

        return self


class PatchPromotionRecord(BaseModel):
    """第二次人工审批：是否把已验证 patch 推广到原仓库。"""

    promotion_id: str
    patch_id: str
    patch_sha256: str
    verification_sha256: str
    decision: Literal["approved", "rejected"]
    reviewer: str = "human"
    reviewed_at: str
    comment: str | None = None

class PatchApplicationJournal(BaseModel):
    """仓库副作用的 write-ahead journal。"""

    journal_version: int = 1
    patch_id: str
    patch_sha256: str
    repo_path: str
    base_git_commit: str
    owner_run_id: str
    status: Literal[
        "prepared",
        "applying",
        "applied",
        "blocked",
        "manual_intervention",
    ]
    files: list[PatchFileRecord] = Field(default_factory=list)
    repository_state: Literal["before", "after", "conflict"]
    recovered: bool = False
    error: str | None = None
    created_at: str
    updated_at: str

class PatchApplicationRecord(BaseModel):
    """patch 真正应用到原仓库后的审计记录。"""

    patch_id: str
    patch_sha256: str
    repo_path: str
    status: Literal[
        "applied",
        "failed",
        "blocked",
        "manual_intervention",
    ]
    files: list[PatchFileRecord] = Field(default_factory=list)
    applied_at: str
    recovered: bool = False
    error: str | None = None
    journal_path: str | None = None
    repository_lock_key: str | None = None

class StageError(BaseModel):
    """
    Graph 某个阶段的结构化错误。

    terminal 决定是否停止当前业务链。
    retryable 只是事实描述，不能让 Graph 自动重放有副作用的整个节点。
    """

    error_id: str
    code: str
    category: ErrorCategory
    stage: str
    message: str
    retryable: bool = False
    terminal: bool = True
    exception_type: str | None = None
    traceback_artifact_path: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    occurred_at: str


class InputCheck(BaseModel):
    """输入验证中的一个确定性检查项。"""

    name: str
    status: Literal["passed", "failed", "warning"]
    category: Literal["user", "environment"]
    code: str
    message: str
    path: str | None = None


class InputValidationReport(BaseModel):
    """进入论文读取和仓库扫描之前的输入验证结果。"""

    valid: bool
    checks: list[InputCheck] = Field(default_factory=list)
    generated_at: str

class ResourceUsage(BaseModel):
    """Supervisor 在整个进程树生命周期内观察到的峰值。"""

    peak_rss_bytes: int = Field(default=0, ge=0)
    peak_process_count: int = Field(default=0, ge=0)
    total_cpu_seconds: float = Field(default=0.0, ge=0)
    total_write_bytes: int = Field(default=0, ge=0)
    peak_gpu_memory_bytes: int | None = Field(default=None, ge=0)
    samples: int = Field(default=0, ge=0)

class PolicyViolation(BaseModel):
    code: str
    field: str
    message: str


class ActionCapabilityRequest(BaseModel):
    """
    Action 声明自己需要的能力。

    local/conda 第一版只能在执行前检查这些声明，不能提供 OS 级隔离。
    """

    network_access: Literal["none", "outbound"] = "none"
    writable_paths: list[str] = Field(default_factory=list)
    env_keys: list[str] = Field(default_factory=list)


class CapabilityDecision(BaseModel):
    decision_id: str
    action_id: str
    action_hash: str
    allowed: bool
    requires_approval: bool
    risk_level: Literal["low", "medium", "high", "blocked"]
    reason: str
    request: ActionCapabilityRequest
    violations: list[PolicyViolation] = Field(default_factory=list)
    effective_budget: ResourceBudget
    evaluated_at: str

class CancellationRequest(BaseModel):
    execution_id: str
    requested_at: str
    requested_by: str = "cli"
    reason: str

class ProcessRecord(BaseModel):
    execution_id: str
    action_id: str
    stage: str
    profile_id: str
    backend: Literal["local", "conda"]
    host_command_preview: list[str] = Field(default_factory=list)
    cwd: str

    pid: int | None = None
    pgid: int | None = None
    process_create_time: float | None = None

    started_at: str
    finished_at: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)

    status: Literal[
        "starting",
        "running",
        "terminating",
        "finished",
    ]
    end_reason: ExecutionEndReason | None = None
    returncode: int | None = None
    termination_signal: int | None = None
    hard_kill_used: bool = False

    stdout_path: str
    stderr_path: str
    stdout_bytes_seen: int = Field(default=0, ge=0)
    stderr_bytes_seen: int = Field(default=0, ge=0)
    stdout_bytes_written: int = Field(default=0, ge=0)
    stderr_bytes_written: int = Field(default=0, ge=0)
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    cancellation_requested: bool = False
    cancellation_reason: str | None = None
    resource_budget: ResourceBudget
    resource_usage: ResourceUsage = Field(
        default_factory=ResourceUsage
    )

    combined_log_path: str
    inherited_env_keys: list[str] = Field(default_factory=list)
    profile_env_keys: list[str] = Field(default_factory=list)
    action_env_keys: list[str] = Field(default_factory=list)
    secret_env_keys: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    ok: bool
    returncode: int | None
    end_reason: ExecutionEndReason

    # 只保存有界 preview，不保存完整 stdout/stderr。
    stdout: str = ""
    stderr: str = ""
    combined_output: str = ""

    timeout: bool = False
    cancelled: bool = False
    cancellation_reason: str | None = None
    log_truncated: bool = False

    execution_id: str | None = None
    execution_profile_id: str | None = None
    execution_backend: str | None = None
    cwd: str | None = None

    process_record_path: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    resource_usage: ResourceUsage = Field(
        default_factory=ResourceUsage
    )

    combined_log_path: str | None = None

class EvalInput(BaseModel):
    """
    Runner 输入。

    fixture_path 必须相对 app/evaluation/，不能由 case 指向任意主机路径。
    route_name 不是动态 import 字符串，而是 runners.py 中的 allowlist key。
    live_graph 字段只在 provider suite 中使用。
    """

    fixture_path: str | None = None

    route_name: str | None = None
    source_node: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)

    paper_path: str | None = None
    repo_path: str | None = None
    log_path: str | None = None
    experiment_goal: str = "复现论文 main result"
    execution_profile_id: str | None = None

    # 按 interrupt 出现顺序提供恢复输入。
    # Provider case 默认应为空，让 Graph 停在第一次人工交互处。
    scripted_responses: list[Any] = Field(default_factory=list)

    # 搜索泄漏时只传测试专用 canary，不传真实 API Key。
    secret_canaries: list[str] = Field(default_factory=list)


class ArtifactExpectation(BaseModel):
    relative_path: str
    required_substrings: list[str] = Field(default_factory=list)
    require_current_hash: bool = True


class ToolCallExpectation(BaseModel):
    name: str

    # 这里只做参数子集匹配，避免 action_id、时间等随机字段导致误报。
    args_subset: dict[str, Any] = Field(default_factory=dict)
    min_calls: int = Field(default=1, ge=0)
    max_calls: int | None = Field(default=None, ge=0)


class EvalExpected(BaseModel):
    """
    所有 scorer 共用的期望。

    没有填写的字段不会自动变成通过项；case.categories 指定了某个类别时，
    该类别必须至少产生一条 Assertion，否则 scorer 会报告 CASE_UNDERSPECIFIED。
    """

    exact_route: list[str] | None = None
    required_nodes: list[str] = Field(default_factory=list)
    forbidden_nodes: list[str] = Field(default_factory=list)
    allowed_final_statuses: list[str] = Field(default_factory=list)

    required_schemas: list[str] = Field(default_factory=list)
    min_schema_success_rate: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    max_schema_fallbacks: int | None = Field(default=None, ge=0)
    max_schema_retries: int | None = Field(default=None, ge=0)

    required_tool_calls: list[ToolCallExpectation] = Field(
        default_factory=list
    )
    forbidden_tool_calls: list[str] = Field(default_factory=list)

    required_artifacts: list[ArtifactExpectation] = Field(
        default_factory=list
    )
    forbidden_artifacts: list[str] = Field(default_factory=list)

    required_evidence_paths: list[str] = Field(default_factory=list)
    required_evidence_terms: list[str] = Field(default_factory=list)
    require_evidence_location: bool | None = None
    require_evidence_hash: bool | None = None

    required_modules: list[str] = Field(default_factory=list)
    required_files: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)

    approval_required: bool | None = None
    approval_hash_must_match: bool | None = None
    patch_hash_must_match: bool | None = None
    execution_must_start: bool | None = None
    max_secret_leaks: int | None = Field(default=None, ge=0)
    max_path_escapes: int | None = Field(default=None, ge=0)
    policy_must_deny: bool | None = None

    resume_must_succeed: bool | None = None
    max_duplicate_side_effects: int | None = Field(default=None, ge=0)

    max_duration_ms: float | None = Field(default=None, ge=0)
    max_llm_calls: int | None = Field(default=None, ge=0)
    max_human_interventions: int | None = Field(default=None, ge=0)


class EvalThresholds(BaseModel):
    min_overall_score: float = Field(default=1.0, ge=0, le=1)
    max_score_regression: float = Field(default=0.0, ge=0, le=1)

    # 默认等权。只对当前 case.categories 中出现的类别生效。
    category_weights: dict[EvalCategory, float] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def validate_weights(self) -> EvalThresholds:
        if any(weight <= 0 for weight in self.category_weights.values()):
            raise ValueError("category weight 必须大于 0")
        return self


class EvalCase(BaseModel):
    schema_version: int = 1
    case_id: str
    description: str
    suite: Literal["offline", "provider"] = "offline"
    runner: EvalRunnerKind
    categories: list[EvalCategory]
    tags: list[str] = Field(default_factory=list)

    # 对应 problems.md 中的问题编号，便于生成缺陷覆盖报告。
    problem_ids: list[int] = Field(default_factory=list)

    input: EvalInput
    expected: EvalExpected
    thresholds: EvalThresholds = Field(default_factory=EvalThresholds)

    @model_validator(mode="after")
    def validate_runner_input(self) -> EvalCase:
        if not self.case_id.strip():
            raise ValueError("case_id 不能为空")
        if not self.categories:
            raise ValueError("categories 不能为空")
        if len(set(self.categories)) != len(self.categories):
            raise ValueError("categories 不能重复")

        if self.runner == "fixture" and not self.input.fixture_path:
            raise ValueError("fixture runner 要求 fixture_path")

        if self.runner == "route_function":
            if not self.input.route_name:
                raise ValueError("route_function runner 要求 route_name")
            if not self.input.source_node:
                raise ValueError("route_function runner 要求 source_node")

        if self.runner == "live_graph":
            if self.suite != "provider":
                raise ValueError(
                    "live_graph 必须放入 provider suite，"
                    "避免普通离线回归意外请求模型"
                )
            if not self.input.paper_path or not self.input.repo_path:
                raise ValueError(
                    "live_graph 要求 paper_path 和 repo_path"
                )

        return self


class StructuredCallObservation(BaseModel):
    node_name: str
    schema_name: str
    succeeded: bool
    fallback_used: bool = False
    attempt_count: int = Field(default=1, ge=0)
    retry_count: int = Field(default=0, ge=0)


class ToolCallObservation(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    side_effect_key: str | None = None
    succeeded: bool | None = None


class EvidenceObservation(BaseModel):
    source_path: str
    location: str | None = None
    text: str
    content_sha256: str | None = None


class EvalMetrics(BaseModel):
    duration_ms: float = Field(default=0, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    human_interventions: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)


class EvalObservation(BaseModel):
    """
    所有 Runner 的统一实际结果。

    scorer 只读取 Observation，不直接调用 Graph、Tool 或 Provider。
    这样同一 Observation 可以反复评分，也可以比较新旧 scorer。
    """

    case_id: str
    runner: EvalRunnerKind
    route: list[str] = Field(default_factory=list)
    final_status: str | None = None

    structured_calls: list[StructuredCallObservation] = Field(
        default_factory=list
    )
    tool_calls: list[ToolCallObservation] = Field(default_factory=list)
    evidence: list[EvidenceObservation] = Field(default_factory=list)

    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    output_payloads: dict[str, Any] = Field(default_factory=dict)
    stage_errors: list[dict[str, Any]] = Field(default_factory=list)

    approval_required: bool | None = None
    approval_present: bool | None = None
    approval_hash_match: bool | None = None
    patch_hash_match: bool | None = None
    execution_started: bool = False
    policy_denied: bool = False

    secret_leaks: list[str] = Field(default_factory=list)
    path_escapes: list[str] = Field(default_factory=list)

    resume_succeeded: bool | None = None
    duplicate_side_effect_count: int = Field(default=0, ge=0)

    metrics: EvalMetrics = Field(default_factory=EvalMetrics)
    run_id: str | None = None
    run_dir: str | None = None


class EvalAssertion(BaseModel):
    code: str
    passed: bool
    message: str
    expected: Any = None
    actual: Any = None


class ScorerResult(BaseModel):
    category: EvalCategory
    score: float = Field(ge=0, le=1)
    passed: bool
    assertions: list[EvalAssertion] = Field(default_factory=list)


class EvalCaseResult(BaseModel):
    case_id: str
    suite: str
    runner: EvalRunnerKind
    passed: bool
    overall_score: float = Field(ge=0, le=1)
    scorer_results: list[ScorerResult] = Field(default_factory=list)
    observation_path: str | None = None
    error: str | None = None


class EvalSuiteResult(BaseModel):
    schema_version: int = 1
    eval_id: str
    suite: str
    passed: bool
    overall_score: float = Field(ge=0, le=1)
    case_results: list[EvalCaseResult] = Field(default_factory=list)
    category_scores: dict[str, float] = Field(default_factory=dict)
    problem_coverage: dict[str, list[str]] = Field(default_factory=dict)
    generated_at: str
    revision: str | None = None
    dirty_worktree: bool | None = None


class BaselineCase(BaseModel):
    case_id: str
    passed: bool
    overall_score: float
    category_scores: dict[str, float] = Field(default_factory=dict)


class EvalBaseline(BaseModel):
    schema_version: int = 1
    suite: str
    cases: list[BaselineCase] = Field(default_factory=list)


class BaselineDiff(BaseModel):
    suite: str
    passed: bool
    new_cases: list[str] = Field(default_factory=list)
    missing_cases: list[str] = Field(default_factory=list)
    newly_failed_cases: list[str] = Field(default_factory=list)
    score_regressions: list[dict[str, Any]] = Field(default_factory=list)
