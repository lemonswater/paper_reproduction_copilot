"""Phase 50 弃用说明。

本模块是 Phase 50 之前的旧模型入口，仅保留给 `structured-output-probe`
等 CLI 回退使用。Phase 50 之后所有 LLM 调用应通过
``app.model_routing.gateway.ModelGateway`` 进行路由、预算预留和审计。

使用 ``get_chat_model()`` 会绕过预算边界和路由策略，不应在生产路径中调用。
"""

from __future__ import annotations

import warnings
from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr

from app.config import settings
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService


def _service(injected: SecretService | None) -> SecretService:
    if injected is not None:
        return injected
    from app.secrets.factory import build_secret_service

    return build_secret_service()


def get_chat_model(
    temperature: float = 0,
    *,
    secret_service: SecretService | None = None,
):
    warnings.warn(
        "get_chat_model() is deprecated since Phase 50; "
        "use app.model_routing.factory.build_model_gateway() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    material = _service(secret_service).resolve_current(
        name=settings.openai_api_key_secret_name,
        use=SecretUse.PROVIDER,
        actor="provider:chat",
    )
    model_options: dict[str, Any] = {
        "model": settings.openai_model,
        # SecretStr 防止 Provider Client repr 意外显示明文。
        "api_key": SecretStr(material.reveal()),
        "base_url": settings.openai_base_url,
        "temperature": temperature,
        "max_completion_tokens": settings.openai_max_output_tokens,
    }
    if settings.openai_thinking_mode is not None:
        # thinking 是 MiMo 扩展字段，OpenAI SDK 要求通过 extra_body 传递。
        model_options["extra_body"] = {
            "thinking": {
                "type": settings.openai_thinking_mode,
            }
        }

    return ChatOpenAI(
        **model_options,
    )


def get_embedding_model(
    *,
    secret_service: SecretService | None = None,
):
    material = _service(secret_service).resolve_current(
        name=settings.embedding_api_key_secret_name,
        use=SecretUse.EMBEDDING,
        actor="provider:embedding",
    )
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=SecretStr(material.reveal()),
        base_url=settings.embedding_base_url,
    )
