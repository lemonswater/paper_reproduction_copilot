from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage

from app.model_routing.factory import build_model_gateway
from app.tool_calling.errors import ToolModelUnavailable
from app.tool_calling.schemas import (
    NormalizedToolCall,
    ProviderToolCatalog,
)


@dataclass(frozen=True)
class ToolModelTurn:
    message: AIMessage
    calls: list[NormalizedToolCall]
    invocation_id: str | None


class ToolTurnInvoker(Protocol):
    def invoke(
        self,
        *,
        messages: list[BaseMessage],
        catalog: ProviderToolCatalog,
        job_id: str,
    ) -> ToolModelTurn:
        ...


def normalize_tool_calls(message: AIMessage) -> list[NormalizedToolCall]:
    normalized: list[NormalizedToolCall] = []
    for raw in message.tool_calls or []:
        name = raw.get("name")
        arguments = raw.get("args")
        call_id = raw.get("id")
        if (
            not isinstance(name, str)
            or not isinstance(arguments, dict)
            or not isinstance(call_id, str)
        ):
            raise ToolModelUnavailable(
                "Provider 返回了无效 Tool Call 结构"
            )
        normalized.append(
            NormalizedToolCall(
                provider_call_id=call_id,
                alias=name,
                arguments=arguments,
            )
        )
    return normalized


class GatewayToolTurnInvoker:
    def invoke(
        self,
        *,
        messages: list[BaseMessage],
        catalog: ProviderToolCatalog,
        job_id: str,
    ) -> ToolModelTurn:
        try:
            routed = build_model_gateway().invoke_tool_calling(
                messages=messages,
                tools=[
                    item.spec.model_dump(mode="json")
                    for item in catalog.bindings
                ],
                node_name="chat_tool_selection",
                job_id=job_id,
                quality_tier="economy",
                requested_max_output_tokens=768,
            )
            calls = normalize_tool_calls(routed.message)
        except Exception as exc:
            # 原始 Provider 错误由 Model Gateway/Ledger 处理；上层只看到稳定类型。
            raise ToolModelUnavailable(
                "Tool Selection Model 当前不可用"
            ) from exc

        return ToolModelTurn(
            message=routed.message,
            calls=calls,
            invocation_id=routed.invocation_id,
        )
