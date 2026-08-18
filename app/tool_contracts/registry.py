from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Optional, Protocol
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.tool_contracts.errors import ToolRegistryError
from app.tool_contracts.schemas import (
    ContractIssue,
    ToolCallRecord,
    ToolContract,
    ToolDeterminism,
    ToolEffect,
    ToolErrorSpec,
    ToolExecutionResult,
    ToolExposure,
    ToolFailure,
    ToolInvocationContext,
    ToolRisk,
)

ToolHandler = Callable[[BaseModel, ToolInvocationContext], object]
ToolErrorMapper = Callable[[BaseException], Optional[ToolFailure]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_payload(value: object) -> bytes:
    if isinstance(value, BaseModel):
        material = value.model_dump(mode="json")
    else:
        material = value
    return json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_payload(value)).hexdigest()


@dataclass(frozen=True)
class ToolDefinition:
    contract: ToolContract
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: ToolHandler
    error_mapper: ToolErrorMapper


class ToolAuditSink(Protocol):
    def write(self, record: ToolCallRecord) -> None:
        ...


class InMemoryToolAuditSink:
    """测试和未来单进程 Skill Runtime 使用的最小审计 Sink。"""

    def __init__(self) -> None:
        self.records: list[ToolCallRecord] = []

    def write(self, record: ToolCallRecord) -> None:
        self.records.append(record)


class NullToolAuditSink:
    def write(self, record: ToolCallRecord) -> None:
        del record


def build_tool_definition(
    *,
    name: str,
    version: str,
    summary: str,
    input_model: type[BaseModel],
    output_model: type[BaseModel],
    handler: ToolHandler,
    error_mapper: ToolErrorMapper,
    effects: list[ToolEffect],
    required_capabilities: list[str],
    exposure: ToolExposure,
    risk_level: ToolRisk,
    determinism: ToolDeterminism,
    idempotent: bool,
    timeout_seconds: int | None,
    audit_event: str,
    path_scopes: list[str],
    declared_errors: list[ToolErrorSpec],
) -> ToolDefinition:
    contract = ToolContract(
        name=name,
        version=version,
        summary=summary,
        input_schema=input_model.model_json_schema(),
        output_schema=output_model.model_json_schema(),
        effects=effects,
        required_capabilities=required_capabilities,
        exposure=exposure,
        risk_level=risk_level,
        determinism=determinism,
        idempotent=idempotent,
        timeout_seconds=timeout_seconds,
        audit_event=audit_event,
        path_scopes=path_scopes,
        declared_errors=declared_errors,
    )
    return ToolDefinition(
        contract=contract,
        input_model=input_model,
        output_model=output_model,
        handler=handler,
        error_mapper=error_mapper,
    )


class ToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        name = definition.contract.name
        if name in self._definitions:
            raise ToolRegistryError(f"工具重复注册：{name}")
        self._definitions[name] = definition

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise ToolRegistryError(f"工具未注册：{name}") from exc

    def names(self) -> list[str]:
        return sorted(self._definitions)

    def catalog_snapshot(self) -> list[dict[str, Any]]:
        """导出内部契约快照；它不是可以直接交给模型的授权列表。"""

        return [
            self._definitions[name].contract.model_dump(mode="json")
            for name in self.names()
        ]

    def validate_definitions(self) -> list[ContractIssue]:
        issues: list[ContractIssue] = []
        for name in self.names():
            definition = self._definitions[name]
            contract = definition.contract

            if contract.input_schema != definition.input_model.model_json_schema():
                issues.append(
                    ContractIssue(
                        code="INPUT_SCHEMA_DRIFT",
                        target=name,
                        message="contract input_schema 与 input_model 不一致",
                    )
                )
            if contract.output_schema != definition.output_model.model_json_schema():
                issues.append(
                    ContractIssue(
                        code="OUTPUT_SCHEMA_DRIFT",
                        target=name,
                        message="contract output_schema 与 output_model 不一致",
                    )
                )

            parameters = list(inspect.signature(definition.handler).parameters.values())
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
                issues.append(
                    ContractIssue(
                        code="INVALID_HANDLER_SIGNATURE",
                        target=name,
                        message="handler 必须接收 payload 和 context 两个参数",
                    )
                )
        return issues

    def invoke(
        self,
        *,
        name: str,
        raw_input: dict[str, Any],
        context: ToolInvocationContext,
        audit_sink: ToolAuditSink | None = None,
    ) -> ToolExecutionResult:
        definition = self.get(name)
        sink = audit_sink or NullToolAuditSink()
        started_at = _utc_now()
        started = perf_counter()
        input_sha256 = _sha256(raw_input)

        allowed_exposures = {
            "agent": {ToolExposure.AGENT_READ_ONLY},
            "trusted_node": {
                ToolExposure.AGENT_READ_ONLY,
                ToolExposure.TRUSTED_NODE_ONLY,
            },
            "operator": set(ToolExposure),
        }
        if definition.contract.exposure not in allowed_exposures[
            context.caller_kind
        ]:
            return self._failed_result(
                definition=definition,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=ToolFailure(
                    code="TOOL_ACCESS_DENIED",
                    category="policy",
                    retryable=False,
                    message="当前调用方类型无权使用该工具",
                ),
            )

        missing_capabilities = sorted(
            set(definition.contract.required_capabilities)
            - set(context.granted_capabilities)
        )
        if missing_capabilities:
            return self._failed_result(
                definition=definition,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=ToolFailure(
                    code="TOOL_CAPABILITY_DENIED",
                    category="policy",
                    retryable=False,
                    message="当前调用上下文缺少工具要求的 Capability",
                ),
            )

        try:
            payload = definition.input_model.model_validate(raw_input)
        except ValidationError:
            return self._failed_result(
                definition=definition,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=ToolFailure(
                    code="TOOL_INPUT_INVALID",
                    category="user",
                    retryable=False,
                    message="工具输入不符合公开 Schema",
                ),
            )

        try:
            raw_output = definition.handler(payload, context)
        except Exception as exc:  # noqa: BLE001
            mapper_failed = False
            try:
                mapped = definition.error_mapper(exc)
            except Exception:  # noqa: BLE001
                # 错误映射器本身也是受契约约束的代码，不能泄漏第二个异常。
                mapper_failed = True
                mapped = ToolFailure(
                    code="TOOL_ERROR_MAPPER_FAILED",
                    category="tool",
                    retryable=False,
                    message="工具错误映射器执行失败",
                )
            declared_codes = {
                item.code for item in definition.contract.declared_errors
            }
            if mapped is None:
                mapped = ToolFailure(
                    code="TOOL_UNDECLARED_EXCEPTION",
                    category="tool",
                    retryable=False,
                    message="工具抛出了契约未声明的异常",
                )
            elif not mapper_failed and mapped.code not in declared_codes:
                mapped = ToolFailure(
                    code="TOOL_ERROR_NOT_DECLARED",
                    category="tool",
                    retryable=False,
                    message="错误映射器返回了契约未声明的错误码",
                )
            return self._failed_result(
                definition=definition,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=mapped,
            )

        try:
            output = definition.output_model.model_validate(raw_output)
        except ValidationError:
            return self._failed_result(
                definition=definition,
                context=context,
                sink=sink,
                started=started,
                started_at=started_at,
                input_sha256=input_sha256,
                failure=ToolFailure(
                    code="TOOL_OUTPUT_INVALID",
                    category="tool",
                    retryable=False,
                    message="工具输出不符合公开 Schema",
                ),
            )

        output_payload = output.model_dump(mode="json")
        record = ToolCallRecord(
            call_id=f"toolcall_{uuid4().hex[:16]}",
            tool_name=definition.contract.name,
            tool_version=definition.contract.version,
            status="succeeded",
            input_sha256=input_sha256,
            output_sha256=_sha256(output_payload),
            effects=definition.contract.effects,
            actor=context.actor,
            request_id=context.request_id,
            job_id=context.job_id,
            caller_kind=context.caller_kind,
            started_at=started_at,
            finished_at=_utc_now(),
            duration_ms=(perf_counter() - started) * 1000,
        )
        sink.write(record)
        return ToolExecutionResult(
            output=output_payload,
            record=record,
        )

    @staticmethod
    def _failed_result(
        *,
        definition: ToolDefinition,
        context: ToolInvocationContext,
        sink: ToolAuditSink,
        started: float,
        started_at: str,
        input_sha256: str,
        failure: ToolFailure,
    ) -> ToolExecutionResult:
        record = ToolCallRecord(
            call_id=f"toolcall_{uuid4().hex[:16]}",
            tool_name=definition.contract.name,
            tool_version=definition.contract.version,
            status="failed",
            input_sha256=input_sha256,
            error_code=failure.code,
            effects=definition.contract.effects,
            actor=context.actor,
            request_id=context.request_id,
            job_id=context.job_id,
            caller_kind=context.caller_kind,
            started_at=started_at,
            finished_at=_utc_now(),
            duration_ms=(perf_counter() - started) * 1000,
        )
        sink.write(record)
        return ToolExecutionResult(
            failure=failure,
            record=record,
        )
