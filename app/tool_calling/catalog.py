from __future__ import annotations

from typing import Any

from app.tool_calling.errors import ToolCatalogError
from app.tool_calling.identity import sha256_value
from app.tool_calling.schemas import (
    ProviderToolBinding,
    ProviderToolCatalog,
    ProviderToolSpec,
)
from app.tool_contracts.registry import ToolRegistry
from app.tool_contracts.schemas import (
    ToolEffect,
    ToolExposure,
)


STATIC_BINDINGS = {
    "get_reproduction_status": "chat.get_reproduction_status",
    "search_reproduction_evidence": "chat.search_reproduction_evidence",
    "inspect_failure_context": "chat.inspect_failure_context",
}

SAFE_EFFECTS = {
    ToolEffect.NONE,
    ToolEffect.DATASTORE_READ,
    ToolEffect.FILESYSTEM_READ,
}

GRANTED_CAPABILITIES = {
    "job.read.current",
    "run.read.evidence",
}


def _walk_schema(value: Any) -> None:
    """拒绝远程引用和异常大的模型输入 Schema。"""

    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and (
                not isinstance(child, str)
                or not child.startswith("#/$defs/")
            ):
                raise ToolCatalogError("Provider Tool Schema 包含外部 $ref")
            _walk_schema(child)
    elif isinstance(value, list):
        for child in value:
            _walk_schema(child)


def _strict_parameters(schema: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(schema)
    if parameters.get("type") != "object":
        raise ToolCatalogError("Tool input schema 顶层必须是 object")
    if parameters.get("additionalProperties") is not False:
        raise ToolCatalogError("Tool input schema 必须拒绝未知字段")
    _walk_schema(parameters)
    if len(str(parameters)) > 20000:
        raise ToolCatalogError("Tool input schema 超过大小限制")
    return parameters


def build_provider_tool_catalog(
    registry: ToolRegistry,
    *,
    static_bindings: dict[str, str] | None = None,
    safe_effects: set[ToolEffect] | None = None,
    granted_capabilities: set[str] | None = None,
    authority_fingerprint: str | None = None,
) -> ProviderToolCatalog:
    selected_bindings = dict(STATIC_BINDINGS if static_bindings is None else static_bindings)
    selected_effects = set(SAFE_EFFECTS if safe_effects is None else safe_effects)
    selected_capabilities = set(GRANTED_CAPABILITIES if granted_capabilities is None else granted_capabilities)
    bindings: list[ProviderToolBinding] = []

    for alias, internal_name in selected_bindings.items():
        try:
            definition = registry.get(internal_name)
        except Exception as exc:
            raise ToolCatalogError(
                f"静态 Tool Binding 不可用：{internal_name}"
            ) from exc

        contract = definition.contract
        if contract.exposure != ToolExposure.AGENT_READ_ONLY:
            raise ToolCatalogError("Chat Tool 必须是 agent_read_only")
        if not set(contract.effects).issubset(selected_effects):
            raise ToolCatalogError("Chat Tool 包含网络、进程、写入或控制副作用")
        if not contract.idempotent:
            raise ToolCatalogError("第一版 Chat Tool 必须是幂等读取")
        if not set(contract.required_capabilities).issubset(
            selected_capabilities
        ):
            raise ToolCatalogError("Chat Tool 要求了未授予 Capability")

        spec = ProviderToolSpec(
            function={
                "name": alias,
                "description": contract.summary,
                "parameters": _strict_parameters(contract.input_schema),
                "strict": True,
            }
        )
        bindings.append(
            ProviderToolBinding(
                alias=alias,
                internal_name=internal_name,
                spec=spec,
            )
        )

    hash_payload = {
        "bindings": [
            {
                "alias": item.alias,
                "internal_name": item.internal_name,
                "spec": item.spec.model_dump(mode="json"),
            }
            for item in bindings
        ],
        "authority_fingerprint": authority_fingerprint,
    }
    return ProviderToolCatalog(
        bindings=bindings,
        catalog_sha256=sha256_value(hash_payload),
    )


def provider_specs(catalog: ProviderToolCatalog) -> list[dict[str, Any]]:
    return [item.spec.model_dump(mode="json") for item in catalog.bindings]
