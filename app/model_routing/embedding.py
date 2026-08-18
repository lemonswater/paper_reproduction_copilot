from __future__ import annotations

import hashlib

from app.model_routing.errors import ModelProviderBindingError
from app.model_routing.gateway import ModelGateway
from app.retrieval.embedding_backend import (
    EmbeddingBackend,
    EmbeddingBackendIdentity,
)


class RoutedEmbeddingBackend:
    def __init__(
        self,
        *,
        gateway: ModelGateway,
        model_name: str,
        endpoint_identity: str,
        job_id: str | None,
        run_id: str | None,
        node_name: str,
    ) -> None:
        self.gateway = gateway
        self.model_name = model_name
        self.job_id = job_id
        self.run_id = run_id
        self.node_name = node_name
        endpoint_hash = hashlib.sha256(
            endpoint_identity.rstrip("/").encode("utf-8")
        ).hexdigest()[:16]
        self._identity = EmbeddingBackendIdentity(
            provider_namespace=f"openai-compatible:{endpoint_hash}",
            model=model_name,
        )

    @property
    def identity(self) -> EmbeddingBackendIdentity:
        return self._identity

    def _backend_for_profile(self, profile) -> EmbeddingBackend:
        if profile.model_name != self.model_name:
            raise ModelProviderBindingError(
                "MODEL_EMBEDDING_CACHE_IDENTITY_MISMATCH"
            )
        return self.gateway.providers.build_embedding(profile)

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []
        invocation = self.gateway.invoke_embedding(
            task_kind="code_embedding_document",
            texts=texts,
            node_name=self.node_name,
            job_id=self.job_id,
            run_id=self.run_id,
            invoke=lambda profile: self._backend_for_profile(
                profile
            ).embed_documents(texts),
        )
        return invocation.value

    def embed_query(self, text: str) -> list[float]:
        invocation = self.gateway.invoke_embedding(
            task_kind="code_embedding_query",
            texts=[text],
            node_name=self.node_name,
            job_id=self.job_id,
            run_id=self.run_id,
            invoke=lambda profile: self._backend_for_profile(
                profile
            ).embed_query(text),
        )
        return invocation.value
