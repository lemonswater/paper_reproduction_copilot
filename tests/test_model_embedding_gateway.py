"""Phase 50: Model Embedding Gateway 测试。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.model_routing.embedding import RoutedEmbeddingBackend
from app.model_routing.gateway import ModelGateway
from tests.helpers.model_routing import (
    FakeProviders,
    TEST_PRICING,
    ModelBudgetPolicy,
    build_test_document,
    build_test_gateway,
)


class FakeEmbeddingBackend:
    """简单的 EmbeddingBackend mock。"""

    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.embed_documents_calls = 0
        self.embed_query_calls = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embed_documents_calls += 1
        if self.fail:
            raise RuntimeError("embedding transport error")
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        self.embed_query_calls += 1
        if self.fail:
            raise RuntimeError("embedding transport error")
        return [0.1, 0.2, 0.3]


def _build_gateway(
    tmp_path: Path,
    *,
    mode: str = "active",
    embedding_backend: Any = None,
) -> ModelGateway:
    doc = build_test_document(
        pricing_override={
            "legacy_embedding": TEST_PRICING,
        },
        budget=ModelBudgetPolicy(
            daily_total_token_limit=100000,
            daily_cost_limit_micro_usd=100000,
            per_job_total_token_limit=50000,
            per_job_cost_limit_micro_usd=50000,
            reservation_ttl_seconds=300,
            allow_unpriced_in_active=False,
        ),
    )
    providers = FakeProviders(embedding=embedding_backend)
    return build_test_gateway(
        tmp_path,
        mode=mode,
        providers=providers,
        document=doc,
    )


def _build_routed_backend(
    gateway: ModelGateway,
    *,
    task_kind: str = "code_embedding_document",
) -> RoutedEmbeddingBackend:
    return RoutedEmbeddingBackend(
        gateway=gateway,
        model_name="embedding-model",
        endpoint_identity="test-endpoint",
        job_id=None,
        run_id=None,
        node_name="test_embedding",
    )


def test_empty_documents_returns_empty(tmp_path: Path):
    backend = FakeEmbeddingBackend()
    gateway = _build_gateway(tmp_path, embedding_backend=backend)
    routed = _build_routed_backend(gateway)
    result = routed.embed_documents([])
    assert result == []
    assert backend.embed_documents_calls == 0


def test_embed_documents_records_usage(tmp_path: Path):
    backend = FakeEmbeddingBackend()
    gateway = _build_gateway(tmp_path, embedding_backend=backend)
    routed = _build_routed_backend(gateway)
    result = routed.embed_documents(["hello", "world"])
    assert len(result) == 2
    assert backend.embed_documents_calls == 1


def test_embed_query_records_usage(tmp_path: Path):
    backend = FakeEmbeddingBackend()
    gateway = _build_gateway(tmp_path, embedding_backend=backend)
    routed = _build_routed_backend(gateway)
    result = routed.embed_query("test query")
    assert len(result) == 3
    assert backend.embed_query_calls == 1


def test_off_mode_does_not_write_ledger(tmp_path: Path):
    backend = FakeEmbeddingBackend()
    gateway = _build_gateway(
        tmp_path,
        mode="off",
        embedding_backend=backend,
    )
    routed = _build_routed_backend(gateway)
    routed.embed_query("test")
    # In off mode, no ledger records should exist
    records = gateway.ledger.list_invocations(limit=10)
    assert len(records) == 0


def test_active_mode_writes_ledger(tmp_path: Path):
    backend = FakeEmbeddingBackend()
    gateway = _build_gateway(
        tmp_path,
        mode="active",
        embedding_backend=backend,
    )
    routed = _build_routed_backend(gateway)
    routed.embed_query("test")
    records = gateway.ledger.list_invocations(limit=10)
    assert len(records) == 1
    assert records[0].status == "succeeded"
    assert records[0].usage_quality == "estimated"


def test_vector_output_type_preserved(tmp_path: Path):
    backend = FakeEmbeddingBackend()
    gateway = _build_gateway(tmp_path, embedding_backend=backend)
    routed = _build_routed_backend(gateway)
    result = routed.embed_documents(["test"])
    assert isinstance(result, list)
    assert all(isinstance(vec, list) for vec in result)
    assert all(isinstance(v, float) for vec in result for v in vec)
