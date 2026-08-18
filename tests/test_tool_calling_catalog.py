from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.chat.context import GroundingBundle, GroundingSource
from app.chat.schemas import ChatCitation
from app.tool_calling.catalog import (
    STATIC_BINDINGS,
    build_provider_tool_catalog,
)
from app.tool_calling.evidence_tools import (
    ChatEvidenceToolBindings,
    build_chat_evidence_tool_registry,
)
from app.tool_calling.errors import ToolCatalogError
from app.tool_calling.schemas import EvidenceToolOutput
from app.tool_contracts.registry import (
    ToolRegistry,
    build_tool_definition,
)
from app.tool_contracts.schemas import (
    ToolDeterminism,
    ToolEffect,
    ToolExposure,
    ToolRisk,
)


class _FakeContextBuilder:
    def build(self, *, job_id: str, question: str):
        return GroundingBundle(
            job=SimpleNamespace(job_id=job_id, status="failed"),
            sources=[
                GroundingSource(
                    citation=ChatCitation(
                        citation_id="job:current",
                        source_type="job",
                        label="Current job state",
                    ),
                    content="status=failed",
                    score=100,
                )
            ],
        )

    def build_job_only(self, *, job_id: str, question: str):
        return self.build(job_id=job_id, question=question)


@pytest.fixture
def chat_tool_registry() -> ToolRegistry:
    return build_chat_evidence_tool_registry(
        ChatEvidenceToolBindings(
            context_builder=_FakeContextBuilder(),
        )
    )


@pytest.fixture
def registry_with_research_tool(chat_tool_registry) -> ToolRegistry:
    """Register a research browser tool in addition to chat tools."""

    chat_tool_registry.register(
        build_tool_definition(
            name="browser.collect_research_evidence",
            version="phase52-v1",
            summary="Collect research evidence from web",
            input_model=EvidenceToolOutput,
            output_model=EvidenceToolOutput,
            handler=lambda payload, context: payload,
            error_mapper=lambda exc: None,
            effects=[ToolEffect.NETWORK_READ],
            required_capabilities=["job.read.current"],
            exposure=ToolExposure.TRUSTED_NODE_ONLY,
            risk_level=ToolRisk.MEDIUM,
            determinism=ToolDeterminism.PROVIDER_DEPENDENT,
            idempotent=False,
            timeout_seconds=60,
            audit_event="tool.browser.collect_research_evidence",
            path_scopes=[],
            declared_errors=[],
        )
    )
    return chat_tool_registry


def test_catalog_contains_only_static_read_tools(
    chat_tool_registry,
) -> None:
    catalog = build_provider_tool_catalog(chat_tool_registry)

    assert {item.alias for item in catalog.bindings} == set(
        STATIC_BINDINGS
    )
    assert all(
        "job_id"
        not in item.spec.function["parameters"].get("properties", {})
        for item in catalog.bindings
    )
    assert len(catalog.catalog_sha256) == 64


def test_catalog_does_not_auto_expose_research_network_tool(
    registry_with_research_tool,
) -> None:
    catalog = build_provider_tool_catalog(registry_with_research_tool)

    assert all(
        item.internal_name != "browser.collect_research_evidence"
        for item in catalog.bindings
    )


def test_catalog_rejects_write_effect(chat_tool_registry) -> None:
    name = "chat.search_reproduction_evidence"
    original = chat_tool_registry.get(name)
    chat_tool_registry._definitions[name] = replace(
        original,
        contract=original.contract.model_copy(
            update={"effects": [ToolEffect.FILESYSTEM_WRITE]}
        ),
    )

    with pytest.raises(ToolCatalogError):
        build_provider_tool_catalog(chat_tool_registry)


def test_catalog_hash_is_stable(chat_tool_registry) -> None:
    catalog_a = build_provider_tool_catalog(chat_tool_registry)
    catalog_b = build_provider_tool_catalog(
        build_chat_evidence_tool_registry(
            ChatEvidenceToolBindings(
                context_builder=_FakeContextBuilder(),
            )
        )
    )
    assert catalog_a.catalog_sha256 == catalog_b.catalog_sha256


def test_catalog_by_alias_returns_binding(chat_tool_registry) -> None:
    catalog = build_provider_tool_catalog(chat_tool_registry)
    binding = catalog.by_alias("get_reproduction_status")
    assert binding is not None
    assert binding.internal_name == "chat.get_reproduction_status"


def test_catalog_by_alias_returns_none_for_unknown(
    chat_tool_registry,
) -> None:
    catalog = build_provider_tool_catalog(chat_tool_registry)
    assert catalog.by_alias("cancel_job") is None
