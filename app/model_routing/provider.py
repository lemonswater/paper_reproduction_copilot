from __future__ import annotations

from typing import Any, Protocol

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.config import settings
from app.model_routing.errors import ModelProviderBindingError
from app.model_routing.schemas import ModelProfile
from app.retrieval.embedding_backend import (
    EmbeddingBackend,
    OpenAICompatibleEmbeddingBackend,
)
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService


class ProviderFactoryPort(Protocol):
    def build_chat(
        self,
        profile: ModelProfile,
        *,
        max_output_tokens: int,
    ) -> Any:
        ...

    def build_embedding(
        self,
        profile: ModelProfile,
    ) -> EmbeddingBackend:
        ...


class TrustedProviderFactory:
    """唯一允许把 profile binding 转成 endpoint + Secret 的边界。"""

    def __init__(self, secret_service: SecretService) -> None:
        self.secret_service = secret_service

    def build_chat(
        self,
        profile: ModelProfile,
        *,
        max_output_tokens: int,
    ) -> Any:
        if (
            profile.workload_kind != "chat"
            or profile.provider_binding != "primary_chat"
        ):
            raise ModelProviderBindingError(
                "MODEL_CHAT_PROVIDER_BINDING_DENIED"
            )
        if max_output_tokens > profile.max_output_tokens:
            raise ModelProviderBindingError(
                "MODEL_OUTPUT_LIMIT_EXCEEDED"
            )

        material = self.secret_service.resolve_current(
            name=settings.openai_api_key_secret_name,
            use=SecretUse.PROVIDER,
            actor=f"model-gateway:{profile.profile_id}",
        )
        options: dict[str, Any] = {
            "model": profile.model_name,
            "api_key": SecretStr(material.reveal()),
            "base_url": settings.openai_base_url,
            "temperature": 0,
            "max_completion_tokens": max_output_tokens,
        }
        # 只有当前受信任 Provider 已配置 MiMo 扩展时才传 extra_body。
        thinking_mode = profile.thinking_mode or settings.openai_thinking_mode
        if settings.openai_thinking_mode is not None and thinking_mode is not None:
            options["extra_body"] = {
                "thinking": {"type": thinking_mode}
            }
        return ChatOpenAI(**options)

    def build_embedding(
        self,
        profile: ModelProfile,
    ) -> EmbeddingBackend:
        if (
            profile.workload_kind != "embedding"
            or profile.provider_binding != "primary_embedding"
        ):
            raise ModelProviderBindingError(
                "MODEL_EMBEDDING_PROVIDER_BINDING_DENIED"
            )
        material = self.secret_service.resolve_current(
            name=settings.embedding_api_key_secret_name,
            use=SecretUse.EMBEDDING,
            actor=f"model-gateway:{profile.profile_id}",
        )
        return OpenAICompatibleEmbeddingBackend(
            api_key=material.reveal(),
            base_url=settings.embedding_base_url or "",
            model=profile.model_name,
            timeout_seconds=settings.embedding_timeout_seconds,
            # Retry 由 Gateway 计数；底层不能再隐藏重试次数。
            max_retries=0,
        )
