from __future__ import annotations

from dataclasses import dataclass

from app.research_browser.collector import ResearchCollector
from app.tool_contracts.models import ResearchCollectInput, ResearchCollectOutput
from app.tool_contracts.registry import build_tool_definition
from app.tool_contracts.schemas import (
    ToolDeterminism,
    ToolEffect,
    ToolErrorSpec,
    ToolExposure,
    ToolFailure,
    ToolRisk,
)


@dataclass(frozen=True)
class ResearchToolBindings:
    collector: ResearchCollector


def _map_research_error(exc: BaseException) -> ToolFailure | None:
    name = type(exc).__name__
    if name in {"ResearchUrlRejected", "ResearchRobotsDenied", "ResearchPolicyError"}:
        return ToolFailure(
            code="TOOL_RESEARCH_POLICY_DENIED",
            category="policy",
            retryable=False,
            message="研究请求或目标地址违反本地网络策略",
        )
    if name in {"ResearchLimitExceeded", "ResearchContentRejected"}:
        return ToolFailure(
            code="TOOL_RESEARCH_CONTENT_REJECTED",
            category="tool",
            retryable=False,
            message="研究响应超过预算或内容类型不受支持",
        )
    if name == "ResearchTransportUnavailable":
        return ToolFailure(
            code="TOOL_RESEARCH_NETWORK_UNAVAILABLE",
            category="environment",
            retryable=True,
            message="研究网络服务暂时不可用",
        )
    return None


def build_research_tool_definition(bindings: ResearchToolBindings):
    def handler(payload: ResearchCollectInput, context):
        # context 由 Registry 创建；网页或模型不能修改 caller_kind/capability。
        del context
        return ResearchCollectOutput(
            evidence=bindings.collector.collect(payload.request)
        )

    return build_tool_definition(
        name="browser.collect_research_evidence",
        version="phase40-v1",
        summary="在本地 Policy 约束下搜索并抽取有界公开网页证据",
        input_model=ResearchCollectInput,
        output_model=ResearchCollectOutput,
        handler=handler,
        error_mapper=_map_research_error,
        effects=[ToolEffect.NETWORK_READ],
        required_capabilities=["network.read.research"],
        exposure=ToolExposure.AGENT_READ_ONLY,
        risk_level=ToolRisk.MEDIUM,
        determinism=ToolDeterminism.PROVIDER_DEPENDENT,
        # 重复调用会消耗 Provider 配额，网页内容也可能变化，不能标成幂等。
        idempotent=False,
        timeout_seconds=120,
        audit_event="tool.browser.collect_research_evidence",
        path_scopes=[],
        declared_errors=[
            ToolErrorSpec(
                code="TOOL_RESEARCH_POLICY_DENIED",
                category="policy",
                summary="URL、DNS、robots 或 allowlist 拒绝请求",
            ),
            ToolErrorSpec(
                code="TOOL_RESEARCH_CONTENT_REJECTED",
                category="tool",
                summary="响应大小、类型或正文不满足抽取约束",
            ),
            ToolErrorSpec(
                code="TOOL_RESEARCH_NETWORK_UNAVAILABLE",
                category="environment",
                retryable=True,
                summary="Search Provider 或目标站点暂时不可用",
            ),
        ],
    )
