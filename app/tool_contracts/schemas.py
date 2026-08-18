from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    """所有公开契约对象都拒绝未知字段，避免协议静默漂移。"""

    model_config = ConfigDict(extra="forbid")


class ToolEffect(str, Enum):
    NONE = "none"
    DATASTORE_READ = "datastore_read"
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    PROCESS_SPAWN = "process_spawn"
    PROCESS_CONTROL = "process_control"
    NETWORK_READ = "network_read"
    NETWORK_WRITE = "network_write"
    REPOSITORY_WRITE = "repository_write"
    ENVIRONMENT_WRITE = "environment_write"


class ToolExposure(str, Enum):
    AGENT_READ_ONLY = "agent_read_only"
    TRUSTED_NODE_ONLY = "trusted_node_only"
    CONTROLLED_ACTION_ONLY = "controlled_action_only"


class ToolRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolDeterminism(str, Enum):
    DETERMINISTIC = "deterministic"
    ENVIRONMENT_DEPENDENT = "environment_dependent"
    PROVIDER_DEPENDENT = "provider_dependent"


class ToolErrorSpec(ContractModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    category: Literal["user", "environment", "policy", "tool"]
    retryable: bool = False
    summary: str = Field(min_length=1, max_length=300)


class ToolContract(ContractModel):
    name: str = Field(
        pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
    )
    version: str = Field(pattern=r"^phase[1-9][0-9]*-v[1-9][0-9]*$")
    summary: str = Field(min_length=1, max_length=300)
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    effects: list[ToolEffect] = Field(min_length=1)
    required_capabilities: list[str] = Field(default_factory=list)
    exposure: ToolExposure
    risk_level: ToolRisk
    determinism: ToolDeterminism
    idempotent: bool
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    audit_event: str = Field(
        pattern=r"^tool\.[a-z][a-z0-9_.]*$"
    )
    path_scopes: list[Literal["workspace", "run"]] = Field(
        default_factory=list
    )
    declared_errors: list[ToolErrorSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_security_metadata(self) -> ToolContract:
        effect_set = set(self.effects)
        if ToolEffect.NONE in effect_set and len(effect_set) != 1:
            raise ValueError("none 不能与其他副作用同时声明")

        if effect_set != {ToolEffect.NONE} and not self.required_capabilities:
            raise ValueError("存在副作用的工具必须声明 required_capabilities")

        if (
            ToolEffect.PROCESS_SPAWN in effect_set
            or ToolEffect.NETWORK_READ in effect_set
            or ToolEffect.NETWORK_WRITE in effect_set
        ) and self.timeout_seconds is None:
            raise ValueError("进程或网络工具必须声明 timeout_seconds")

        write_effects = {
            ToolEffect.FILESYSTEM_WRITE,
            ToolEffect.PROCESS_CONTROL,
            ToolEffect.NETWORK_WRITE,
            ToolEffect.REPOSITORY_WRITE,
            ToolEffect.ENVIRONMENT_WRITE,
        }
        if (
            self.exposure == ToolExposure.AGENT_READ_ONLY
            and effect_set.intersection(write_effects)
        ):
            raise ValueError("agent_read_only 工具不能声明写或控制副作用")

        if (
            self.exposure == ToolExposure.AGENT_READ_ONLY
            and self.risk_level == ToolRisk.HIGH
        ):
            raise ValueError("高风险工具不能直接标记为 agent_read_only")

        error_codes = [item.code for item in self.declared_errors]
        if len(error_codes) != len(set(error_codes)):
            raise ValueError("declared_errors code 不能重复")
        return self


class ToolInvocationContext(ContractModel):
    """受信任 Host 提供的边界，不属于模型 Tool 参数。"""

    actor: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    caller_kind: Literal["agent", "trusted_node", "operator"]
    job_id: str | None = None
    workspace_root: str | None = None
    run_root: str | None = None
    granted_capabilities: set[str] = Field(default_factory=set, max_length=64)


class ToolFailure(ContractModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    category: Literal["user", "environment", "policy", "tool"]
    retryable: bool = False
    message: str = Field(min_length=1, max_length=1000)


class ToolCallRecord(ContractModel):
    call_id: str = Field(pattern=r"^toolcall_[0-9a-f]{16}$")
    tool_name: str
    tool_version: str
    status: Literal["succeeded", "failed"]
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    error_code: str | None = None
    effects: list[ToolEffect]
    actor: str
    request_id: str
    job_id: str | None = None
    caller_kind: Literal["agent", "trusted_node", "operator"]
    started_at: str
    finished_at: str
    duration_ms: float = Field(ge=0)


class ToolExecutionResult(ContractModel):
    output: dict[str, Any] | None = None
    failure: ToolFailure | None = None
    record: ToolCallRecord

    @model_validator(mode="after")
    def validate_result_shape(self) -> ToolExecutionResult:
        if self.record.status == "succeeded":
            if self.output is None or self.failure is not None:
                raise ValueError("成功结果必须只有 output")
        else:
            if self.failure is None or self.output is not None:
                raise ValueError("失败结果必须只有 failure")
        return self


class ContractIssue(ContractModel):
    code: str
    target: str
    message: str


class ContractValidationReport(ContractModel):
    ok: bool
    contracts_checked: int = Field(ge=0)
    modules_checked: int = Field(ge=0)
    issues: list[ContractIssue] = Field(default_factory=list)
