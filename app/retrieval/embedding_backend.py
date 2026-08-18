from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from langchain_openai import OpenAIEmbeddings

from app.config import settings


class EmbeddingProviderError(RuntimeError):
    """Embedding Provider 配置、传输或返回值错误。"""


@dataclass(frozen=True)
class EmbeddingBackendIdentity:
    provider_namespace: str
    model: str


@runtime_checkable
class EmbeddingBackend(Protocol):
    @property
    def identity(
        self,
    ) -> EmbeddingBackendIdentity:
        ...

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        ...

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        ...


def validate_vectors(
    vectors: list[list[float]],
    *,
    expected_count: int,
    expected_dimensions: int | None = None,
) -> int:
    """验证 Provider 没有返回空向量、NaN、Inf 或维度漂移。"""

    if len(vectors) != expected_count:
        raise EmbeddingProviderError(
            "Embedding 返回数量不一致："
            f"expected={expected_count}, "
            f"actual={len(vectors)}"
        )
    if not vectors:
        raise EmbeddingProviderError(
            "Embedding 返回为空"
        )

    dimensions = len(vectors[0])
    if dimensions < 1:
        raise EmbeddingProviderError(
            "Embedding 向量维度必须大于 0"
        )
    if (
        expected_dimensions is not None
        and dimensions != expected_dimensions
    ):
        raise EmbeddingProviderError(
            "Embedding 维度与缓存不一致："
            f"expected={expected_dimensions}, "
            f"actual={dimensions}"
        )

    for vector in vectors:
        if len(vector) != dimensions:
            raise EmbeddingProviderError(
                "同一次 Embedding 返回了不同维度"
            )
        if not all(
            math.isfinite(float(value))
            for value in vector
        ):
            raise EmbeddingProviderError(
                "Embedding 向量包含 NaN 或 Inf"
            )
    return dimensions


class OpenAICompatibleEmbeddingBackend:
    """
    复用项目已有 langchain-openai 依赖。

    tiktoken_enabled=False：
        避免 OpenAI-compatible 自定义模型因 tokenizer 名称未知而失败。

    check_embedding_ctx_length=False：
        chunker 已负责限制输入；长度错误由 Provider 明确返回。
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        if not api_key.strip():
            raise EmbeddingProviderError(
                "EMBEDDING_API_KEY 未配置"
            )
        if not base_url.strip():
            raise EmbeddingProviderError(
                "EMBEDDING_BASE_URL 未配置"
            )
        if not model.strip():
            raise EmbeddingProviderError(
                "EMBEDDING_MODEL 未配置"
            )

        # Namespace 只保存 endpoint hash，不把完整内部地址写入 cache key。
        endpoint_hash = hashlib.sha256(
            base_url.rstrip("/").encode(
                "utf-8"
            )
        ).hexdigest()[:16]
        self._identity = EmbeddingBackendIdentity(
            provider_namespace=(
                f"openai-compatible:{endpoint_hash}"
            ),
            model=model,
        )
        self._client = OpenAIEmbeddings(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout_seconds,
            max_retries=max_retries,
            tiktoken_enabled=False,
            check_embedding_ctx_length=False,
        )

    @property
    def identity(
        self,
    ) -> EmbeddingBackendIdentity:
        return self._identity

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self._client.embed_documents(
                texts
            )
        except Exception as exc:
            # 不把 Provider 原始对象或请求 headers 写入错误。
            raise EmbeddingProviderError(
                "Embedding document request failed: "
                f"{type(exc).__name__}"
            ) from exc

        validate_vectors(
            vectors,
            expected_count=len(texts),
        )
        return [
            [float(value) for value in vector]
            for vector in vectors
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        if not text.strip():
            raise EmbeddingProviderError(
                "Embedding query 不能为空"
            )
        try:
            vector = self._client.embed_query(text)
        except Exception as exc:
            raise EmbeddingProviderError(
                "Embedding query request failed: "
                f"{type(exc).__name__}"
            ) from exc

        validate_vectors(
            [vector],
            expected_count=1,
        )
        return [
            float(value)
            for value in vector
        ]


def get_embedding_backend(
    *,
    secret_service=None,
    job_id: str | None = None,
    run_id: str | None = None,
) -> EmbeddingBackend:
    if settings.model_routing_mode != "off":
        from app.model_routing.factory import (
            build_routed_embedding_backend,
        )

        return build_routed_embedding_backend(
            job_id=job_id,
            run_id=run_id,
            node_name="code_search",
        )

    # 下面保留 Phase 21 旧实现，off 模式不改变行为。
    if secret_service is None:
        from app.secrets.factory import build_secret_service
        from app.secrets.schemas import SecretUse

        secret_service = build_secret_service()
        material = secret_service.resolve_current(
            name=settings.embedding_api_key_secret_name,
            use=SecretUse.EMBEDDING,
            actor="embedding:backend",
        )
        api_key_value = material.reveal()
    else:
        from app.secrets.schemas import SecretUse

        material = secret_service.resolve_current(
            name=settings.embedding_api_key_secret_name,
            use=SecretUse.EMBEDDING,
            actor="embedding:backend",
        )
        api_key_value = material.reveal()

    return OpenAICompatibleEmbeddingBackend(
        api_key=api_key_value,
        base_url=(
            settings.embedding_base_url or ""
        ),
        model=settings.embedding_model,
        timeout_seconds=(
            settings.embedding_timeout_seconds
        ),
        max_retries=(
            settings.embedding_max_retries
        ),
    )