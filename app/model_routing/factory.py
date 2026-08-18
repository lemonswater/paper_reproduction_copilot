from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.model_routing.catalog import load_model_catalog
from app.model_routing.embedding import RoutedEmbeddingBackend
from app.model_routing.errors import ModelCatalogError
from app.model_routing.gateway import ModelGateway
from app.model_routing.policy import ModelRouter
from app.model_routing.provider import TrustedProviderFactory
from app.model_routing.repository import SqliteModelLedger


@lru_cache(maxsize=1)
def build_model_gateway() -> ModelGateway:
    catalog = load_model_catalog(
        settings.model_routing_policy_path,
        allowed_root=settings.allowed_root,
        substitutions={
            "$OPENAI_MODEL": settings.openai_model,
            "$OPENAI_ECONOMY_MODEL": settings.openai_economy_model,
            "$OPENAI_STRONG_MODEL": settings.openai_strong_model,
            "$EMBEDDING_MODEL": settings.embedding_model,
        },
    )
    ledger = SqliteModelLedger(
        settings.model_routing_db_path,
        budget=catalog.document.budget,
    )

    from app.secrets.factory import build_secret_service

    providers = TrustedProviderFactory(build_secret_service())
    return ModelGateway(
        mode=settings.model_routing_mode,
        router=ModelRouter(catalog),
        ledger=ledger,
        providers=providers,
        structured_method=settings.structured_output_method,
        structured_strict=settings.structured_output_strict,
        raw_preview_chars=(
            settings.structured_output_raw_preview_chars
        ),
        provider_retry_base_seconds=(
            settings.provider_retry_base_seconds
        ),
    )


def _embedding_model_name(gateway: ModelGateway) -> str:
    """第一版要求两个 Embedding Route 的所有 Profile 使用同一模型。"""

    catalog = gateway.router.catalog
    model_names: set[str] = set()
    for task_kind in (
        "code_embedding_document",
        "code_embedding_query",
    ):
        route = catalog.route(task_kind)
        profile_ids = {
            route.legacy_profile_id,
            *route.candidate_profile_ids,
        }
        for profile_id in profile_ids:
            profile = catalog.profile(profile_id)
            if profile.enabled:
                model_names.add(profile.model_name)
    if len(model_names) != 1:
        raise ModelCatalogError(
            "Phase 50 第一版要求所有 Embedding Profile 使用同一 model_name"
        )
    return next(iter(model_names))


def build_routed_embedding_backend(
    *,
    job_id: str | None = None,
    run_id: str | None = None,
    node_name: str = "code_search",
) -> RoutedEmbeddingBackend:
    gateway = build_model_gateway()
    return RoutedEmbeddingBackend(
        gateway=gateway,
        model_name=_embedding_model_name(gateway),
        endpoint_identity=settings.embedding_base_url or "",
        job_id=job_id,
        run_id=run_id,
        node_name=node_name,
    )
