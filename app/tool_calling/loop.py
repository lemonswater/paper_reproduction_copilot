from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.chat.context import (
    GroundingBundle,
    GroundingSource,
)
from app.chat.schemas import (
    ChatToolCallSummary,
    ChatToolTraceSummary,
)
from app.prompts.tool_calling_prompt import (
    TOOL_SELECTION_SYSTEM_PROMPT,
    build_tool_selection_user_message,
)
from app.tool_calling.catalog import GRANTED_CAPABILITIES
from app.tool_calling.errors import (
    ToolLoopPolicyError,
    ToolModelUnavailable,
)
from app.tool_calling.identity import (
    canonical_json_bytes,
    compute_trace_hash,
    sha256_value,
    tool_call_fingerprint,
    trace_id_for,
)
from app.tool_calling.model_adapter import ToolTurnInvoker
from app.tool_calling.schemas import (
    EvidenceToolOutput,
    ProviderToolCatalog,
    ToolLoopCallTrace,
    ToolLoopTrace,
)
from app.tool_contracts.registry import ToolRegistry
from app.tool_contracts.schemas import ToolInvocationContext


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ToolLoopOutcome:
    trace: ToolLoopTrace
    sources: list[GroundingSource]


def _validate_json_shape(
    value: Any,
    *,
    depth: int = 0,
) -> None:
    if depth > 8:
        raise ToolLoopPolicyError("Tool arguments 嵌套过深")
    if isinstance(value, dict):
        if len(value) > 32:
            raise ToolLoopPolicyError("Tool arguments 字段过多")
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > 100:
                raise ToolLoopPolicyError("Tool arguments key 无效")
            _validate_json_shape(child, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > 50:
            raise ToolLoopPolicyError("Tool arguments 列表过长")
        for child in value:
            _validate_json_shape(child, depth=depth + 1)
    elif isinstance(value, str):
        if len(value) > 2000:
            raise ToolLoopPolicyError("Tool argument 字符串过长")
        if any(ord(character) == 0 for character in value):
            raise ToolLoopPolicyError("Tool arguments 包含 NUL")
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise ToolLoopPolicyError("Tool arguments 包含非 JSON 类型")


def _safe_tool_message(
    *,
    output: EvidenceToolOutput | None,
    failure_code: str | None,
) -> str:
    if failure_code is not None:
        payload = {
            "status": "failed",
            "error_code": failure_code,
            "message": "只读工具未能返回可用证据",
        }
    elif output is not None:
        payload = {
            "status": "succeeded",
            "summary": output.summary,
            "truncated": output.truncated,
            "evidence": [
                {
                    "citation_id": item.citation.citation_id,
                    "source_type": item.citation.source_type,
                    "label": item.citation.label,
                    "content": item.content,
                }
                for item in output.items
            ],
        }
    else:
        raise AssertionError("ToolMessage 必须包含 output 或 failure")

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def merge_grounding_sources(
    *,
    base: GroundingBundle,
    additions: list[GroundingSource],
    source_limit: int,
    total_chars: int,
) -> GroundingBundle:
    """按 Citation Identity 合并，永远保留 job:current。"""

    selected: list[GroundingSource] = list(base.sources)
    by_id = {
        item.citation.citation_id: item
        for item in selected
    }
    used_chars = sum(len(item.content) for item in selected)

    for source in additions:
        citation_id = source.citation.citation_id
        previous = by_id.get(citation_id)
        if previous is not None:
            # 同 ID、不同身份或不同正文表示上游发生协议冲突，不能覆盖。
            if (
                previous.citation != source.citation
                or previous.content != source.content
            ):
                raise ToolLoopPolicyError(
                    "Tool Evidence Citation identity 冲突"
                )
            continue
        if len(selected) >= source_limit:
            break
        if used_chars + len(source.content) > total_chars:
            continue
        selected.append(source)
        by_id[citation_id] = source
        used_chars += len(source.content)

    return GroundingBundle(job=base.job, sources=selected)


class BoundedToolCallingLoop:
    def __init__(
        self,
        *,
        registry: ToolRegistry,
        catalog: ProviderToolCatalog,
        turn_invoker: ToolTurnInvoker,
        max_model_rounds: int,
        max_tool_calls: int,
        max_arguments_bytes: int,
        max_single_result_chars: int,
        max_total_result_chars: int,
        granted_capabilities: set[str] | None = None,
    ) -> None:
        if not 1 <= max_model_rounds <= 6:
            raise ValueError("max_model_rounds 超出范围")
        if not 1 <= max_tool_calls <= 3:
            raise ValueError("max_tool_calls 超出范围")
        if max_model_rounds < max_tool_calls:
            raise ValueError("模型轮数不能小于 Tool 调用数")
        self.registry = registry
        self.catalog = catalog
        self.turn_invoker = turn_invoker
        self.max_model_rounds = max_model_rounds
        self.max_tool_calls = max_tool_calls
        self.max_arguments_bytes = max_arguments_bytes
        self.max_single_result_chars = max_single_result_chars
        self.max_total_result_chars = max_total_result_chars
        self.granted_capabilities = set(
            GRANTED_CAPABILITIES
            if granted_capabilities is None
            else granted_capabilities
        )

    def _finish_trace(
        self,
        *,
        job_id: str,
        request_sha256: str,
        status: str,
        started_at: str,
        invocation_ids: list[str],
        calls: list[ToolLoopCallTrace],
    ) -> ToolLoopTrace:
        draft = ToolLoopTrace(
            trace_id=trace_id_for(
                job_id=job_id,
                request_sha256=request_sha256,
            ),
            job_id=job_id,
            status=status,
            catalog_sha256=self.catalog.catalog_sha256,
            request_sha256=request_sha256,
            model_invocation_ids=invocation_ids,
            calls=calls,
            started_at=started_at,
            finished_at=utc_now(),
            trace_sha256="0" * 64,
        )
        return draft.model_copy(
            update={"trace_sha256": compute_trace_hash(draft)}
        )

    def run(
        self,
        *,
        job_id: str,
        job_status: str,
        question: str,
        request_sha256: str,
    ) -> ToolLoopOutcome:
        started_at = utc_now()
        messages: list[BaseMessage] = [
            SystemMessage(content=TOOL_SELECTION_SYSTEM_PROMPT),
            HumanMessage(
                content=build_tool_selection_user_message(
                    question=question,
                    job_status=job_status,
                )
            ),
        ]
        seen_fingerprints: set[str] = set()
        invocation_ids: list[str] = []
        traces: list[ToolLoopCallTrace] = []
        sources: list[GroundingSource] = []
        total_result_chars = 0
        status = "limit_reached"

        for round_index in range(1, self.max_model_rounds + 1):
            try:
                turn = self.turn_invoker.invoke(
                    messages=messages,
                    catalog=self.catalog,
                    job_id=job_id,
                )
            except ToolModelUnavailable:
                status = "planner_unavailable"
                break

            messages.append(turn.message)
            if turn.invocation_id is not None:
                invocation_ids.append(turn.invocation_id)

            if not turn.calls:
                status = (
                    "no_tools_needed"
                    if not traces
                    else "completed"
                )
                break

            # 即使 Provider 忽略 parallel_tool_calls=False，本地也只接受一个。
            if len(turn.calls) != 1:
                status = "policy_blocked"
                break

            call = turn.calls[0]
            binding = self.catalog.by_alias(call.alias)
            if binding is None:
                # 不反馈真实 Catalog，避免未知名称变成目录探测接口。
                status = "policy_blocked"
                break

            if len(traces) >= self.max_tool_calls:
                status = "limit_reached"
                break

            try:
                _validate_json_shape(call.arguments)
                argument_bytes = canonical_json_bytes(call.arguments)
                if len(argument_bytes) > self.max_arguments_bytes:
                    raise ToolLoopPolicyError(
                        "Tool arguments 超过字节预算"
                    )
            except ToolLoopPolicyError:
                status = "policy_blocked"
                break

            fingerprint = tool_call_fingerprint(
                internal_name=binding.internal_name,
                arguments=call.arguments,
            )
            if fingerprint in seen_fingerprints:
                status = "policy_blocked"
                break
            seen_fingerprints.add(fingerprint)

            result = self.registry.invoke(
                name=binding.internal_name,
                raw_input=call.arguments,
                context=ToolInvocationContext(
                    actor="agent:chat-tool-calling",
                    request_id=request_sha256,
                    caller_kind="agent",
                    job_id=job_id,
                    granted_capabilities=set(self.granted_capabilities),
                ),
            )

            if result.failure is not None:
                traces.append(
                    ToolLoopCallTrace(
                        round_index=round_index,
                        call_id=result.record.call_id,
                        tool_name=binding.internal_name,
                        status="failed",
                        input_sha256=result.record.input_sha256,
                        output_sha256=None,
                        error_code=result.failure.code,
                    )
                )
                messages.append(
                    ToolMessage(
                        content=_safe_tool_message(
                            output=None,
                            failure_code=result.failure.code,
                        ),
                        tool_call_id=call.provider_call_id,
                        name=call.alias,
                    )
                )
                continue

            try:
                output = EvidenceToolOutput.model_validate(result.output)
            except Exception:
                traces.append(
                    ToolLoopCallTrace(
                        round_index=round_index,
                        call_id=result.record.call_id,
                        tool_name=binding.internal_name,
                        status="failed",
                        input_sha256=result.record.input_sha256,
                        output_sha256=result.record.output_sha256,
                        error_code="TOOL_EVIDENCE_OUTPUT_INVALID",
                    )
                )
                status = "policy_blocked"
                break

            tool_message = _safe_tool_message(
                output=output,
                failure_code=None,
            )
            if len(tool_message) > self.max_single_result_chars:
                traces.append(
                    ToolLoopCallTrace(
                        round_index=round_index,
                        call_id=result.record.call_id,
                        tool_name=binding.internal_name,
                        status="failed",
                        input_sha256=result.record.input_sha256,
                        output_sha256=result.record.output_sha256,
                        error_code="TOOL_RESULT_BUDGET_EXCEEDED",
                    )
                )
                messages.append(
                    ToolMessage(
                        content=_safe_tool_message(
                            output=None,
                            failure_code="TOOL_RESULT_BUDGET_EXCEEDED",
                        ),
                        tool_call_id=call.provider_call_id,
                        name=call.alias,
                    )
                )
                continue
            if (
                total_result_chars + len(tool_message)
                > self.max_total_result_chars
            ):
                status = "limit_reached"
                break

            citation_ids = [
                item.citation.citation_id
                for item in output.items
            ]
            traces.append(
                ToolLoopCallTrace(
                    round_index=round_index,
                    call_id=result.record.call_id,
                    tool_name=binding.internal_name,
                    status="succeeded",
                    input_sha256=result.record.input_sha256,
                    output_sha256=result.record.output_sha256,
                    citation_ids=citation_ids,
                )
            )
            total_result_chars += len(tool_message)
            sources.extend(
                GroundingSource(
                    citation=item.citation,
                    content=item.content,
                    score=100,
                )
                for item in output.items
            )
            messages.append(
                ToolMessage(
                    content=tool_message,
                    tool_call_id=call.provider_call_id,
                    name=call.alias,
                )
            )

        trace = self._finish_trace(
            job_id=job_id,
            request_sha256=request_sha256,
            status=status,
            started_at=started_at,
            invocation_ids=invocation_ids,
            calls=traces,
        )
        return ToolLoopOutcome(trace=trace, sources=sources)


def public_trace_summary(trace: ToolLoopTrace) -> ChatToolTraceSummary:
    return ChatToolTraceSummary(
        trace_id=trace.trace_id,
        status=trace.status,
        catalog_sha256=trace.catalog_sha256,
        calls=[
            ChatToolCallSummary(
                call_id=item.call_id,
                tool_name=item.tool_name,
                status=item.status,
                input_sha256=item.input_sha256,
                output_sha256=item.output_sha256,
                error_code=item.error_code,
                citation_ids=item.citation_ids,
            )
            for item in trace.calls
        ],
        trace_sha256=trace.trace_sha256,
    )
