from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.model_routing.errors import ModelCatalogError
from app.model_routing.identity import sha256_value
from app.model_routing.schemas import (
    ModelProfile,
    ModelRoutingDocument,
    ModelTaskKind,
    ModelTaskRoute,
)


MAX_POLICY_BYTES = 1_000_000


@dataclass(frozen=True)
class LoadedModelCatalog:
    document: ModelRoutingDocument
    policy_sha256: str
    profiles_by_id: dict[str, ModelProfile]
    routes_by_task: dict[ModelTaskKind, ModelTaskRoute]

    def profile(self, profile_id: str) -> ModelProfile:
        try:
            return self.profiles_by_id[profile_id]
        except KeyError as exc:
            raise ModelCatalogError(
                f"未知 model profile：{profile_id}"
            ) from exc

    def route(self, task_kind: ModelTaskKind) -> ModelTaskRoute:
        try:
            return self.routes_by_task[task_kind]
        except KeyError as exc:
            raise ModelCatalogError(
                f"未配置 model task route：{task_kind}"
            ) from exc


def _safe_policy_file(
    path: Path,
    *,
    allowed_root: Path,
) -> Path:
    root = allowed_root.expanduser().resolve()
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ModelCatalogError("Model policy 不能是 symlink")
    resolved = candidate.resolve()
    if resolved == root or root not in resolved.parents:
        raise ModelCatalogError("Model policy 必须位于 ALLOWED_ROOT 内")
    if not resolved.is_file():
        raise ModelCatalogError(f"Model policy 不存在：{resolved}")
    if resolved.stat().st_size > MAX_POLICY_BYTES:
        raise ModelCatalogError("Model policy 文件过大")
    return resolved


@dataclass(frozen=True)
class _ResolvedCatalog:
    document: ModelRoutingDocument
    profiles_by_id: dict[str, ModelProfile]
    routes_by_task: dict[ModelTaskKind, ModelTaskRoute]


def _validate_cross_references_then_resolve(
    document: ModelRoutingDocument,
    *,
    substitutions: dict[str, str],
) -> _ResolvedCatalog:
    """先校验交叉引用，再替换占位符。

    校验逻辑（重复 ID、未知引用、workload 匹配、max_output_tokens）
    不依赖 model_name，因此可以在占位符替换之前完成。这样即使
    substitutions 为空，也能正确报告结构性错误。
    """
    profiles_by_id, routes_by_task = _validate_cross_references(document)
    resolved = _resolve_model_placeholders(
        document,
        substitutions=substitutions,
    )
    # 替换后重新构建索引，使 profiles_by_id 中的 profile 携带真实 model_name。
    profiles_by_id = {
        p.profile_id: p for p in resolved.profiles
    }
    return _ResolvedCatalog(
        document=resolved,
        profiles_by_id=profiles_by_id,
        routes_by_task=routes_by_task,
    )


def _resolve_model_placeholders(
    document: ModelRoutingDocument,
    *,
    substitutions: dict[str, str],
) -> ModelRoutingDocument:
    profiles: list[ModelProfile] = []
    for profile in document.profiles:
        model_name = profile.model_name
        if model_name.startswith("$"):
            replacement = substitutions.get(model_name)
            if replacement is None or not replacement.strip():
                raise ModelCatalogError(
                    f"未提供模型占位符：{model_name}"
                )
            model_name = replacement.strip()
        profiles.append(
            profile.model_copy(update={"model_name": model_name})
        )
    return document.model_copy(update={"profiles": profiles})


def _validate_cross_references(
    document: ModelRoutingDocument,
) -> tuple[
    dict[str, ModelProfile],
    dict[ModelTaskKind, ModelTaskRoute],
]:
    profiles_by_id: dict[str, ModelProfile] = {}
    for profile in document.profiles:
        if profile.profile_id in profiles_by_id:
            raise ModelCatalogError(
                f"重复 profile_id：{profile.profile_id}"
            )
        profiles_by_id[profile.profile_id] = profile

    routes_by_task: dict[ModelTaskKind, ModelTaskRoute] = {}
    for route in document.routes:
        if route.task_kind in routes_by_task:
            raise ModelCatalogError(
                f"重复 task route：{route.task_kind}"
            )
        routes_by_task[route.task_kind] = route

        referenced = [
            route.legacy_profile_id,
            *route.candidate_profile_ids,
        ]
        for profile_id in referenced:
            profile = profiles_by_id.get(profile_id)
            if profile is None:
                raise ModelCatalogError(
                    f"Route 引用了未知 profile：{profile_id}"
                )
            if profile.workload_kind != route.workload_kind:
                raise ModelCatalogError(
                    f"Route/Profile workload 不一致：{route.task_kind}"
                )
            if route.max_output_tokens > profile.max_output_tokens:
                raise ModelCatalogError(
                    "Route max_output_tokens 超过 Profile 上限："
                    f"task={route.task_kind}, profile={profile_id}"
                )
    return profiles_by_id, routes_by_task


def load_model_catalog(
    path: Path,
    *,
    allowed_root: Path,
    substitutions: dict[str, str],
) -> LoadedModelCatalog:
    resolved = _safe_policy_file(path, allowed_root=allowed_root)
    try:
        raw = resolved.read_text(encoding="utf-8")
        document = ModelRoutingDocument.model_validate_json(raw)
    except (OSError, UnicodeError, ValidationError) as exc:
        raise ModelCatalogError(
            f"Model policy 无法读取或校验：{type(exc).__name__}"
        ) from exc

    document = _validate_cross_references_then_resolve(
        document,
        substitutions=substitutions,
    )
    return LoadedModelCatalog(
        document=document.document,
        # Hash 使用替换后的真实 model name；环境变化会使旧 Decision 失效。
        policy_sha256=sha256_value(document.document),
        profiles_by_id=document.profiles_by_id,
        routes_by_task=document.routes_by_task,
    )
