from __future__ import annotations

from typing import Any

from app.skills.schemas import (
    SkillInvocationContext,
    SkillManifest,
    SkillToolCallRef,
)
from app.tool_contracts.registry import (
    InMemoryToolAuditSink,
    ToolRegistry,
)
from app.tool_contracts.schemas import (
    ToolEffect,
    ToolExposure,
    ToolInvocationContext,
)


SAFE_SKILL_EFFECTS = {
    ToolEffect.NONE,
    ToolEffect.FILESYSTEM_READ,
    ToolEffect.PROCESS_SPAWN,
    ToolEffect.NETWORK_READ,
}


class SkillRuntimeError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        category: str,
        message: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.category = category
        self.safe_message = message
        self.retryable = retryable


class SkillRuntime:
    """只允许调用 Manifest 声明的只读 Tool。"""

    def __init__(
        self,
        *,
        manifest: SkillManifest,
        tool_registry: ToolRegistry,
        context: SkillInvocationContext,
    ) -> None:
        self._manifest = manifest
        self._tool_registry = tool_registry
        self._context = context
        self._requirements = {
            item.name: item.version
            for item in manifest.required_tools
        }
        self._audit_sink = InMemoryToolAuditSink()
        self._tool_call_refs: list[SkillToolCallRef] = []

    @property
    def tool_call_refs(self) -> list[SkillToolCallRef]:
        return list(self._tool_call_refs)

    def call_tool(
        self,
        name: str,
        raw_input: dict[str, Any],
    ) -> dict[str, Any]:
        if name not in self._requirements:
            raise SkillRuntimeError(
                code="SKILL_TOOL_NOT_DECLARED",
                category="policy",
                message="Skill 尝试调用 Manifest 未声明的工具",
            )
        if len(self._tool_call_refs) >= self._manifest.max_tool_calls:
            raise SkillRuntimeError(
                code="SKILL_TOOL_BUDGET_EXCEEDED",
                category="policy",
                message="Skill Tool 调用次数超过 Manifest 预算",
            )

        try:
            definition = self._tool_registry.get(name)
        except Exception as exc:  # Registry 错误不能泄漏内部细节。
            raise SkillRuntimeError(
                code="SKILL_TOOL_UNAVAILABLE",
                category="tool",
                message="Skill 声明的工具当前不可用",
            ) from exc

        contract = definition.contract
        if contract.version != self._requirements[name]:
            raise SkillRuntimeError(
                code="SKILL_TOOL_VERSION_MISMATCH",
                category="policy",
                message="Skill 要求的 Tool 版本与 Registry 不一致",
            )
        if contract.exposure != ToolExposure.AGENT_READ_ONLY:
            raise SkillRuntimeError(
                code="SKILL_TOOL_EXPOSURE_DENIED",
                category="policy",
                message="Skill 只能调用 agent_read_only 工具",
            )
        # NETWORK_READ 工具（如受限研究浏览器）天然不幂等：
        # 重复调用会消耗搜索配额且网页内容可能变化。
        is_network_read = ToolEffect.NETWORK_READ in contract.effects
        if not contract.idempotent and not is_network_read:
            raise SkillRuntimeError(
                code="SKILL_TOOL_NOT_IDEMPOTENT",
                category="policy",
                message="第一版 Skill 只能调用幂等工具",
            )
        if not set(contract.effects).issubset(SAFE_SKILL_EFFECTS):
            raise SkillRuntimeError(
                code="SKILL_TOOL_EFFECT_DENIED",
                category="policy",
                message="Skill Tool 包含禁止的写入或控制副作用",
            )

        manifest_capabilities = set(
            self._manifest.required_capabilities
        )
        granted_capabilities = set(
            self._context.granted_capabilities
        )
        tool_capabilities = set(contract.required_capabilities)
        if not tool_capabilities.issubset(manifest_capabilities):
            raise SkillRuntimeError(
                code="SKILL_CAPABILITY_NOT_DECLARED",
                category="policy",
                message="Tool 能力没有在 Skill Manifest 中完整声明",
            )
        if not manifest_capabilities.issubset(granted_capabilities):
            raise SkillRuntimeError(
                code="SKILL_CAPABILITY_NOT_GRANTED",
                category="policy",
                message="本次调用没有获得 Skill 所需全部能力",
            )
        if (
            ToolEffect.PROCESS_SPAWN in contract.effects
            and "process.spawn.rg" not in tool_capabilities
        ):
            raise SkillRuntimeError(
                code="SKILL_PROCESS_CAPABILITY_INVALID",
                category="policy",
                message="Skill 只允许显式声明的有界 rg 进程能力",
            )
        if ToolEffect.NETWORK_READ in contract.effects and (
            contract.name != "browser.collect_research_evidence"
            or set(contract.required_capabilities) != {"network.read.research"}
        ):
            raise SkillRuntimeError(
                code="SKILL_NETWORK_CAPABILITY_INVALID",
                category="policy",
                message="Skill 只允许显式声明的受限研究网络能力",
            )

        result = self._tool_registry.invoke(
            name=name,
            raw_input=raw_input,
            context=ToolInvocationContext(
                actor=self._context.actor,
                request_id=self._context.request_id,
                caller_kind="agent",
                workspace_root=self._context.workspace_root,
                run_root=self._context.run_root,
                granted_capabilities=granted_capabilities,
            ),
            audit_sink=self._audit_sink,
        )
        reference = SkillToolCallRef(
            call_id=result.record.call_id,
            tool_name=result.record.tool_name,
            tool_version=result.record.tool_version,
            status=result.record.status,
            input_sha256=result.record.input_sha256,
            output_sha256=result.record.output_sha256,
            error_code=result.record.error_code,
        )
        self._tool_call_refs.append(reference)

        if result.failure is not None:
            raise SkillRuntimeError(
                code="SKILL_TOOL_CALL_FAILED",
                category="tool",
                message=(
                    "Skill Tool 调用失败："
                    f"{result.failure.code}"
                ),
                retryable=result.failure.retryable,
            )
        return result.output or {}
