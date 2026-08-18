from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.skills.loader import DiscoveredSkillPackage
from app.skills.runtime import SkillRuntime, SkillRuntimeError
from app.skills.schemas import (
    SkillCatalogEntry,
    SkillExecutionResult,
    SkillFailure,
    SkillInvocationContext,
    SkillInvocationRecord,
    SkillInvocationRequest,
)
from app.tool_contracts.registry import ToolRegistry
from app.tool_contracts.schemas import ToolEffect, ToolExposure


SkillHandler = Callable[[BaseModel, SkillRuntime], object]


class SkillRegistryError(ValueError):
    """Skill 定义或绑定不符合系统约束。"""


@dataclass(frozen=True)
class SkillDefinition:
    implementation_id: str
    input_schema_id: str
    output_schema_id: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: SkillHandler


@dataclass(frozen=True)
class BoundSkill:
    package: DiscoveredSkillPackage
    definition: SkillDefinition
    enabled: bool
    skill_sha256: str


class SkillAuditSink(Protocol):
    def write(self, record: SkillInvocationRecord) -> None:
        ...


class InMemorySkillAuditSink:
    def __init__(self) -> None:
        self.records: list[SkillInvocationRecord] = []

    def write(self, record: SkillInvocationRecord) -> None:
        self.records.append(record)


class NullSkillAuditSink:
    def write(self, record: SkillInvocationRecord) -> None:
        del record


FORBIDDEN_OUTPUT_KEYS = {
    "command",
    "program",
    "args",
    "cwd",
    "pending_action",
    "pending_action_hash",
    "approval_record",
    "user_approval",
    "execution_result",
    "execution_evidence",
    "execution_verification",
    "pending_patch",
    "pending_patch_hash",
    "patch_approval",
    "patch_approval_record",
    "patch_application_record",
    "final_status",
}

SAFE_SKILL_EFFECTS = {
    ToolEffect.NONE,
    ToolEffect.FILESYSTEM_READ,
    ToolEffect.PROCESS_SPAWN,
    ToolEffect.NETWORK_READ,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json_bytes(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _assert_no_authority_keys(value: Any, *, path: str = "output") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_OUTPUT_KEYS:
                raise SkillRegistryError(
                    f"Skill Output 包含职责越权字段：{path}.{normalized}"
                )
            _assert_no_authority_keys(
                child,
                path=f"{path}.{normalized}",
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_authority_keys(
                child,
                path=f"{path}[{index}]",
            )


class SkillRegistry:
    def __init__(self, *, tool_registry: ToolRegistry) -> None:
        self._tool_registry = tool_registry
        self._skills: dict[str, BoundSkill] = {}

    def register(
        self,
        *,
        package: DiscoveredSkillPackage,
        definition: SkillDefinition,
        enabled: bool,
    ) -> BoundSkill:
        manifest = package.manifest
        if manifest.skill_id in self._skills:
            raise SkillRegistryError(
                f"Skill 重复注册：{manifest.skill_id}"
            )
        if manifest.implementation_id != definition.implementation_id:
            raise SkillRegistryError("Manifest implementation_id 未命中内置实现")
        if manifest.input_schema_id != definition.input_schema_id:
            raise SkillRegistryError("Skill input_schema_id 与实现不一致")
        if manifest.output_schema_id != definition.output_schema_id:
            raise SkillRegistryError("Skill output_schema_id 与实现不一致")

        parameters = list(
            inspect.signature(definition.handler).parameters.values()
        )
        if (
            len(parameters) != 2
            or any(
                item.kind
                in {
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                }
                for item in parameters
            )
        ):
            raise SkillRegistryError(
                "Skill Handler 必须只接收 payload 和 runtime"
            )

        tool_contracts: list[dict[str, Any]] = []
        manifest_capabilities = set(manifest.required_capabilities)
        for requirement in sorted(
            manifest.required_tools,
            key=lambda item: item.name,
        ):
            try:
                tool = self._tool_registry.get(requirement.name)
            except Exception as exc:
                raise SkillRegistryError(
                    f"Skill Tool 未注册：{requirement.name}"
                ) from exc
            contract = tool.contract
            if contract.version != requirement.version:
                raise SkillRegistryError(
                    f"Skill Tool 版本不匹配：{requirement.name}"
                )
            if contract.exposure != ToolExposure.AGENT_READ_ONLY:
                raise SkillRegistryError(
                    f"Skill Tool 不是 agent_read_only：{requirement.name}"
                )
            # NETWORK_READ 工具天然不幂等，但它是受控研究浏览器专用。
            is_network_read = ToolEffect.NETWORK_READ in contract.effects
            if not contract.idempotent and not is_network_read:
                raise SkillRegistryError(
                    f"Skill Tool 不是幂等工具：{requirement.name}"
                )
            if not set(contract.effects).issubset(SAFE_SKILL_EFFECTS):
                raise SkillRegistryError(
                    f"Skill Tool 副作用越界：{requirement.name}"
                )
            if not set(contract.required_capabilities).issubset(
                manifest_capabilities
            ):
                raise SkillRegistryError(
                    f"Skill 未声明 Tool 所需能力：{requirement.name}"
                )
            if (
                ToolEffect.PROCESS_SPAWN in contract.effects
                and "process.spawn.rg"
                not in contract.required_capabilities
            ):
                raise SkillRegistryError(
                    f"Skill Tool 进程能力不是受限 rg：{requirement.name}"
                )
            if ToolEffect.NETWORK_READ in contract.effects and (
                contract.name != "browser.collect_research_evidence"
                or set(contract.required_capabilities)
                != {"network.read.research"}
            ):
                raise SkillRegistryError(
                    "Skill 网络能力不是受限研究读取"
                )
            tool_contracts.append(contract.model_dump(mode="json"))

        implementation_module = inspect.getmodule(definition.handler)
        if implementation_module is None:
            raise SkillRegistryError("无法确定 Skill 实现模块")
        try:
            implementation_source = inspect.getsource(
                implementation_module
            )
        except (OSError, TypeError) as exc:
            raise SkillRegistryError(
                "无法读取 builtin Skill 实现源码身份"
            ) from exc

        skill_sha256 = _sha256(
            {
                "package_sha256": package.package_sha256,
                "implementation_id": definition.implementation_id,
                "implementation_source_sha256": _sha256(
                    implementation_source
                ),
                "input_schema": definition.input_model.model_json_schema(),
                "output_schema": definition.output_model.model_json_schema(),
                "tool_contracts": tool_contracts,
            }
        )
        bound = BoundSkill(
            package=package,
            definition=definition,
            enabled=enabled,
            skill_sha256=skill_sha256,
        )
        self._skills[manifest.skill_id] = bound
        return bound

    def get(self, skill_id: str) -> BoundSkill:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise SkillRegistryError(f"Skill 未注册：{skill_id}") from exc

    def names(self) -> list[str]:
        return sorted(self._skills)

    def catalog_snapshot(self) -> list[SkillCatalogEntry]:
        entries: list[SkillCatalogEntry] = []
        for name in self.names():
            bound = self._skills[name]
            manifest = bound.package.manifest
            entries.append(
                SkillCatalogEntry(
                    skill_id=manifest.skill_id,
                    skill_version=manifest.skill_version,
                    display_name=manifest.display_name,
                    summary=manifest.summary,
                    side_effect_level=manifest.side_effect_level,
                    required_tools=[
                        item.name for item in manifest.required_tools
                    ],
                    required_capabilities=list(
                        manifest.required_capabilities
                    ),
                    prompt_or_policy_version=(
                        manifest.prompt_or_policy_version
                    ),
                    eval_suite=manifest.eval_suite,
                    feature_flag=manifest.feature_flag,
                    enabled=bound.enabled,
                    skill_sha256=bound.skill_sha256,
                    input_schema=(
                        bound.definition.input_model.model_json_schema()
                    ),
                    output_schema=(
                        bound.definition.output_model.model_json_schema()
                    ),
                )
            )
        return entries

    def invoke(
        self,
        *,
        request: SkillInvocationRequest,
        context: SkillInvocationContext,
        audit_sink: SkillAuditSink | None = None,
    ) -> SkillExecutionResult:
        bound = self.get(request.skill_id)
        sink = audit_sink or NullSkillAuditSink()
        started_at = _utc_now()
        started = perf_counter()
        input_sha256 = _sha256(request.input_payload)
        runtime: SkillRuntime | None = None

        if not bound.enabled:
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=SkillFailure(
                    code="SKILL_DISABLED",
                    category="policy",
                    message="Skill 当前未启用",
                ),
            )
        manifest = bound.package.manifest
        if request.skill_version != manifest.skill_version:
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=SkillFailure(
                    code="SKILL_VERSION_MISMATCH",
                    category="policy",
                    message="请求的 Skill 版本已失效",
                ),
            )
        if request.expected_skill_sha256 != bound.skill_sha256:
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=SkillFailure(
                    code="SKILL_STALE_IDENTITY",
                    category="policy",
                    message="Skill 内容身份已变化，请重新读取 Catalog",
                ),
            )
        if not set(manifest.required_capabilities).issubset(
            set(context.granted_capabilities)
        ):
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=SkillFailure(
                    code="SKILL_CAPABILITY_NOT_GRANTED",
                    category="policy",
                    message="本次调用没有获得 Skill 所需能力",
                ),
            )

        try:
            payload = bound.definition.input_model.model_validate(
                request.input_payload
            )
        except ValidationError:
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=SkillFailure(
                    code="SKILL_INPUT_INVALID",
                    category="user",
                    message="Skill 输入不符合公开 Schema",
                ),
            )

        runtime = SkillRuntime(
            manifest=manifest,
            tool_registry=self._tool_registry,
            context=context,
        )
        try:
            raw_output = bound.definition.handler(payload, runtime)
            output = bound.definition.output_model.model_validate(raw_output)
            output_payload = output.model_dump(mode="json")
            _assert_no_authority_keys(output_payload)
        except SkillRuntimeError as exc:
            failure = SkillFailure(
                code=exc.code,
                category=exc.category,
                message=exc.safe_message,
                retryable=exc.retryable,
            )
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=failure,
                runtime=runtime,
            )
        except ValidationError:
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=SkillFailure(
                    code="SKILL_OUTPUT_INVALID",
                    category="skill",
                    message="Skill 输出不符合公开 Schema",
                ),
                runtime=runtime,
            )
        except SkillRegistryError:
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=SkillFailure(
                    code="SKILL_AUTHORITY_VIOLATION",
                    category="policy",
                    message="Skill 输出包含职责越权字段",
                ),
                runtime=runtime,
            )
        except Exception:  # noqa: BLE001
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=SkillFailure(
                    code="SKILL_UNDECLARED_EXCEPTION",
                    category="skill",
                    message="Skill Handler 发生未声明异常",
                ),
                runtime=runtime,
            )

        duration_ms = (perf_counter() - started) * 1000
        if duration_ms > manifest.max_duration_ms:
            return self._failed_result(
                bound=bound,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=SkillFailure(
                    code="SKILL_DURATION_BUDGET_EXCEEDED",
                    category="skill",
                    message="Skill 总耗时超过 Manifest 预算",
                ),
                runtime=runtime,
            )

        record = SkillInvocationRecord(
            invocation_id=f"skillcall_{uuid4().hex[:16]}",
            skill_id=manifest.skill_id,
            skill_version=manifest.skill_version,
            skill_sha256=bound.skill_sha256,
            status="succeeded",
            input_sha256=input_sha256,
            output_sha256=_sha256(output_payload),
            tool_calls=runtime.tool_call_refs,
            actor=context.actor,
            request_id=context.request_id,
            job_id=context.job_id,
            started_at=started_at,
            finished_at=_utc_now(),
            duration_ms=duration_ms,
        )
        sink.write(record)
        return SkillExecutionResult(
            output=output_payload,
            record=record,
        )

    @staticmethod
    def _failed_result(
        *,
        bound: BoundSkill,
        context: SkillInvocationContext,
        sink: SkillAuditSink,
        started: float,
        started_at: str,
        input_sha256: str,
        failure: SkillFailure,
        runtime: SkillRuntime | None = None,
    ) -> SkillExecutionResult:
        manifest = bound.package.manifest
        record = SkillInvocationRecord(
            invocation_id=f"skillcall_{uuid4().hex[:16]}",
            skill_id=manifest.skill_id,
            skill_version=manifest.skill_version,
            skill_sha256=bound.skill_sha256,
            status="failed",
            input_sha256=input_sha256,
            failure_code=failure.code,
            tool_calls=(runtime.tool_call_refs if runtime else []),
            actor=context.actor,
            request_id=context.request_id,
            job_id=context.job_id,
            started_at=started_at,
            finished_at=_utc_now(),
            duration_ms=(perf_counter() - started) * 1000,
        )
        sink.write(record)
        return SkillExecutionResult(
            failure=failure,
            record=record,
        )
