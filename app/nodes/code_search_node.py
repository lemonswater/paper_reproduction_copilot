from __future__ import annotations

import re

from app.config import settings
from app.retrieval import (
    EmbeddingProviderError,
    PreparedDenseRetriever,
    SQLiteEmbeddingCache,
    build_evidence_pack,
    build_lexical_query,
    build_query_features,
    build_repository_index,
    build_semantic_chunks,
    build_semantic_query,
    get_embedding_backend,
    load_retrieval_policy,
    select_retrieval_profile,
    sha256_value,
)
from app.retrieval.policy_schemas import (
    RetrievalDecision,
    RetrievalPolicyConfig,
    RetrievalPolicyMode,
)
from app.retrieval.schemas import (
    DenseRetrievalReport,
)
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import (
    stage_error_result,
)
from app.tools.mapping_target_tools import (
    mapping_targets_from_state,
)
from app.tools.search_tools import (
    SearchToolError,
)


def _slug(value: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        value.casefold(),
    ).strip("-")
    return (slug or "target")[:60]


def _legacy_search_result(
    pack: dict,
) -> dict:
    """保持旧 mapping/report fixture 可读取。"""

    items = list(pack.get("items") or [])
    return {
        "keywords": list(
            pack.get("keywords") or []
        ),
        "matches": [
            {
                "file_path": item["file_path"],
                "line": item["start_line"],
                "text": (
                    item["text"].splitlines()[0]
                    if item.get("text")
                    else ""
                ),
                "keyword": "hybrid",
            }
            for item in items
        ],
        "candidate_files": [
            item["file_path"]
            for item in items
        ],
        "code_slices": [
            {
                "file_path": item["file_path"],
                "content": item["text"],
            }
            for item in items
        ],
    }


def _dense_flags(
    state: dict,
) -> tuple[bool, bool]:
    enabled = bool(
        state.get(
            "enable_dense_retrieval",
            settings.enable_dense_retrieval,
        )
    )
    required = bool(
        state.get(
            "dense_retrieval_required",
            settings.dense_retrieval_required,
        )
    )
    # required 本身意味着用户要求启用。
    return enabled or required, required


def _prepare_dense(
    *,
    repo_path: str,
    index,
    state: dict | None = None,
) -> tuple[
    PreparedDenseRetriever,
    dict,
]:
    if not settings.allow_code_embedding_upload:
        raise EmbeddingProviderError(
            "Dense Retrieval 已开启，但 "
            "ALLOW_CODE_EMBEDDING_UPLOAD=false"
        )

    chunks, manifest = build_semantic_chunks(
        repo_path=repo_path,
        index=index,
        chunk_policy_version=(
            settings
            .semantic_chunk_policy_version
        ),
        max_lines=(
            settings.semantic_chunk_max_lines
        ),
        overlap_lines=(
            settings
            .semantic_chunk_overlap_lines
        ),
        max_chunks=settings.semantic_max_chunks,
    )
    run_state = state or {}
    backend = get_embedding_backend(
        job_id=run_state.get("job_id"),
        run_id=run_state.get("run_id"),
    )
    cache = SQLiteEmbeddingCache(
        settings.embedding_cache_db_path
    )
    retriever = PreparedDenseRetriever.prepare(
        chunks=chunks,
        backend=backend,
        cache=cache,
        cache_version=(
            settings.embedding_cache_version
        ),
        batch_size=settings.embedding_batch_size,
    )
    return (
        retriever,
        manifest.model_dump(mode="json"),
    )


def _fallback_report(
    *,
    enabled: bool,
    required: bool,
    reason: str | None,
) -> DenseRetrievalReport:
    return DenseRetrievalReport(
        enabled=enabled,
        required=required,
        fallback_reason=reason,
    )


def _mapping_targets(state: dict) -> list[dict]:
    return [
        target.model_dump(mode="json")
        for target in mapping_targets_from_state(
            state
        )
    ]


def _policy_mode() -> RetrievalPolicyMode:
    """Settings 已在启动时验证，这里只做类型收窄。"""

    return settings.retrieval_policy_mode  # type: ignore[return-value]


def _paper_evidence_count(target: dict) -> int:
    """只统计结构化 Evidence 项数，不解析或信任其自然语言内容。"""

    values = target.get("evidence") or []
    return sum(isinstance(item, dict) for item in values)


def _target_keywords(
    target: dict,
    target_name: str,
) -> list[str]:
    """保持当前节点的关键词构造顺序，并确定性去重。"""

    values = [
        target_name,
        *[
            str(value)
            for value in target.get("possible_keywords") or []
        ],
        *[
            str(value)
            for value in target.get("aliases") or []
        ],
    ]
    return list(
        dict.fromkeys(
            value.strip()
            for value in values
            if value.strip()
        )
    )


def _policy_decision(
    *,
    policy: RetrievalPolicyConfig,
    mode: RetrievalPolicyMode,
    target_payload: dict,
    lexical_query: str,
    keywords: list[str],
    dense_available: bool,
) -> RetrievalDecision:
    """为一个 mapping target 生成不含 query 原文的 Decision。"""

    features = build_query_features(
        query=lexical_query,
        keywords=keywords,
        preferred_paths=[],
        paper_evidence_count=_paper_evidence_count(target_payload),
    )
    return select_retrieval_profile(
        policy=policy,
        features=features,
        dense_available=dense_available,
        mode=mode,
    )


def code_search_node(
    state: dict,
) -> dict:
    repo_path = state.get("repo_path")
    targets = _mapping_targets(state)
    if not repo_path:
        return stage_error_result(
            state=state,
            stage="code_search",
            code="REPO_PATH_REQUIRED",
            category="user",
            message=(
                "代码检索必须提供 repo_path"
            ),
            extra_update={
                "code_search_results": {},
                "code_evidence_packs": {},
            },
        )
    if not targets:
        return stage_error_result(
            state=state,
            stage="code_search",
            code="MAPPING_TARGETS_REQUIRED",
            category="agent",
            message=(
                "代码检索需要 mapping_targets；"
                "旧 checkpoint 可由 method_modules 兼容生成"
            ),
            extra_update={
                "code_search_results": {},
                "code_evidence_packs": {},
            },
        )

    try:
        index = build_repository_index(
            repo_path,
            index_version=(
                settings.retrieval_index_version
            ),
            max_file_bytes=(
                settings.retrieval_max_file_bytes
            ),
        )
    except (
        FileNotFoundError,
        OSError,
    ) as exc:
        return stage_error_result(
            state=state,
            stage="code_search",
            code="REPO_INDEX_FAILED",
            category="environment",
            message=str(exc),
            extra_update={
                "code_search_results": {},
                "code_evidence_packs": {},
            },
        )

    index_path, index_record = (
        write_json_artifact(
            state=state,
            relative_path=(
                "analysis/retrieval/"
                "repo_index.json"
            ),
            payload=index.model_dump(
                mode="json"
            ),
            producer_node="code_search",
        )
    )
    records = [index_record]

    mode = _policy_mode()
    policy: RetrievalPolicyConfig | None = None
    policy_sha256: str | None = None

    if mode != "off":
        try:
            policy = load_retrieval_policy(
                settings.retrieval_policy_path
            )
            policy_sha256 = sha256_value(policy)
        except (OSError, ValueError, KeyError) as exc:
            # shadow/active 都要求操作员配置可审计；配置损坏不能悄悄忽略。
            return stage_error_result(
                state=state,
                stage="code_search",
                code="RETRIEVAL_POLICY_INVALID",
                category="agent",
                message=f"{type(exc).__name__}: {exc}",
                extra_update={
                    "repo_index_path": str(index_path),
                    "code_search_results": {},
                    "code_evidence_packs": {},
                    "retrieval_policy_decision_paths": {},
                    **artifact_state_update(state, records),
                },
            )

    dense_enabled, dense_required = (
        _dense_flags(state)
    )
    dense_retriever = None
    dense_fallback_reason = None
    semantic_manifest_path = None

    # Policy 只能在已有 Dense 开关和上传授权内做选择，不能自行开启能力。
    dense_permitted = bool(
        dense_enabled
        and settings.allow_code_embedding_upload
    )

    policy_requests_dense = False
    if mode == "active" and policy is not None:
        for position, target in enumerate(targets):
            target_name = str(
                target.get("name")
                or f"unnamed_target_{position}"
            )
            target_payload = {**target, "name": target_name}
            keywords = _target_keywords(target, target_name)
            lexical_query = build_lexical_query(target_payload)
            preview = _policy_decision(
                policy=policy,
                mode=mode,
                target_payload=target_payload,
                lexical_query=lexical_query,
                keywords=keywords,
                dense_available=dense_permitted,
            )
            if (
                dense_required
                and dense_permitted
                and "dense"
                not in preview.selected_profile.enabled_channels
            ):
                # 显式 --require-dense 与 sparse profile 冲突时不能静默忽略任一方。
                return stage_error_result(
                    state=state,
                    stage="code_search",
                    code="DENSE_REQUIRED_PROFILE_CONFLICT",
                    category="user",
                    message=(
                        f"target={target_name} 要求 Dense，"
                        f"但 profile={preview.selected_profile.profile_id} "
                        "未启用 dense"
                    ),
                    extra_update={
                        "repo_index_path": str(index_path),
                        "code_search_results": {},
                        "code_evidence_packs": {},
                        "retrieval_policy_decision_paths": {},
                        **artifact_state_update(state, records),
                    },
                )
            if "dense" in preview.selected_profile.enabled_channels:
                policy_requests_dense = True
                break

        # 用户明确 required 时仍保留 required 语义；否则仅在 profile 请求时准备。
        dense_enabled = dense_required or policy_requests_dense

    if dense_enabled:
        if not settings.allow_code_embedding_upload:
            dense_fallback_reason = (
                "Dense Retrieval 已开启，但 "
                "ALLOW_CODE_EMBEDDING_UPLOAD=false"
            )
            if dense_required:
                return stage_error_result(
                    state=state,
                    stage="code_search",
                    code=(
                        "DENSE_UPLOAD_NOT_ALLOWED"
                    ),
                    category="user",
                    message=(
                        dense_fallback_reason
                    ),
                    extra_update={
                        "repo_index_path": str(
                            index_path
                        ),
                        **artifact_state_update(
                            state,
                            records,
                        ),
                    },
                )
        else:
            try:
                (
                    dense_retriever,
                    semantic_manifest,
                ) = _prepare_dense(
                    repo_path=str(repo_path),
                    index=index,
                    state=state,
                )
                (
                    manifest_path,
                    manifest_record,
                ) = write_json_artifact(
                    state=state,
                    relative_path=(
                        "analysis/retrieval/"
                        "semantic_index_manifest.json"
                    ),
                    payload=semantic_manifest,
                    producer_node="code_search",
                )
                semantic_manifest_path = str(
                    manifest_path
                )
                records.append(manifest_record)
            except (
                EmbeddingProviderError,
                OSError,
                ValueError,
            ) as exc:
                dense_fallback_reason = (
                    f"{type(exc).__name__}: {exc}"
                )
                if dense_required:
                    return stage_error_result(
                        state=state,
                        stage="code_search",
                        code=(
                            "DENSE_PREPARATION_FAILED"
                        ),
                        category="provider",
                        message=(
                            dense_fallback_reason
                        ),
                        extra_update={
                            "repo_index_path": str(
                                index_path
                            ),
                            "code_search_results": {},
                            "code_evidence_packs": {},
                            **artifact_state_update(
                                state,
                                records,
                            ),
                        },
                    )

    packs: dict[str, dict] = {}
    pack_paths: dict[str, str] = {}
    dense_report_paths: dict[str, str] = {}
    policy_decision_paths: dict[str, str] = {}
    legacy_results: dict[str, dict] = {}

    for position, target in enumerate(
        targets
    ):
        target_name = str(
            target.get("name")
            or f"unnamed_target_{position}"
        )
        target_id = str(
            target.get("target_id")
            or target_name
        )
        target_category = str(
            target.get("category")
            or "core_method"
        )
        target_payload = {
            **target,
            "name": target_name,
        }
        keywords = _target_keywords(
            target,
            target_name,
        )
        lexical_query = build_lexical_query(
            target_payload
        )

        decision: RetrievalDecision | None = None
        if policy is not None:
            # 使用实际 Dense preparation 结果，而不是预判结果。
            decision = _policy_decision(
                policy=policy,
                mode=mode,
                target_payload=target_payload,
                lexical_query=lexical_query,
                keywords=keywords,
                dense_available=(dense_retriever is not None),
            )

            decision_path, decision_record = write_json_artifact(
                state=state,
                relative_path=(
                    "analysis/retrieval/policy_decisions/"
                    f"{position:02d}_"
                    f"{_slug(target_category)}_"
                    f"{_slug(target_name)}.json"
                ),
                payload=decision.model_dump(mode="json"),
                producer_node="code_search",
            )
            policy_decision_paths[target_id] = str(decision_path)
            records.append(decision_record)

        dense_hits = []

        profile_uses_dense = bool(
            decision is not None
            and decision.applied
            and "dense" in decision.selected_profile.enabled_channels
        )

        # off/shadow 保持旧行为；active 只为选中 dense profile 的 target 调用。
        should_rank_dense = bool(
            dense_retriever is not None
            and (
                mode in {"off", "shadow"}
                or profile_uses_dense
            )
        )

        if should_rank_dense:
            try:
                semantic_query = (
                    build_semantic_query(
                        target_payload,
                        max_chars=(
                            settings
                            .semantic_query_max_chars
                        ),
                    )
                )
                (
                    dense_hits,
                    dense_report,
                ) = dense_retriever.rank(
                    query=semantic_query,
                    min_similarity=(
                        settings
                        .dense_min_similarity
                    ),
                    max_hits=(
                        settings.dense_max_hits
                    ),
                    required=dense_required,
                )
            except (
                EmbeddingProviderError,
                OSError,
                ValueError,
            ) as exc:
                reason = (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )
                if dense_required:
                    return stage_error_result(
                        state=state,
                        stage="code_search",
                        code=(
                            "DENSE_QUERY_FAILED"
                        ),
                        category="provider",
                        message=(
                            f"{target_name}: "
                            f"{reason}"
                        ),
                        extra_update={
                            "code_search_results": (
                                legacy_results
                            ),
                            "code_evidence_packs": (
                                packs
                            ),
                            **artifact_state_update(
                                state,
                                records,
                            ),
                        },
                    )
                dense_report = (
                    _fallback_report(
                        enabled=True,
                        required=False,
                        reason=reason,
                    )
                )
        else:
            profile_reason = (
                "ACTIVE_PROFILE_DENSE_DISABLED"
                if mode == "active" and dense_retriever is not None
                else dense_fallback_reason
            )
            dense_report = _fallback_report(
                enabled=dense_enabled,
                required=dense_required,
                reason=profile_reason,
            )

        dense_relative_path = (
            "analysis/retrieval/dense_reports/"
            f"{position:02d}_"
            f"{_slug(target_category)}_"
            f"{_slug(target_name)}.json"
        )
        (
            dense_report_path,
            dense_report_record,
        ) = write_json_artifact(
            state=state,
            relative_path=(
                dense_relative_path
            ),
            payload=dense_report.model_dump(
                mode="json"
            ),
            producer_node="code_search",
        )
        dense_report_paths[target_id] = str(
            dense_report_path
        )
        records.append(
            dense_report_record
        )

        active_profile = (
            decision.selected_profile
            if decision is not None and decision.applied
            else None
        )
        active_dense_hits = (
            dense_hits
            if (
                active_profile is None
                or "dense" in active_profile.enabled_channels
            )
            else []
        )

        try:
            _, pack = build_evidence_pack(
                repo_path=repo_path,
                query=lexical_query,
                keywords=keywords,
                index=index,
                index_version=(
                    settings
                    .retrieval_index_version
                ),
                max_file_bytes=(
                    settings
                    .retrieval_max_file_bytes
                ),
                top_k=(
                    active_profile.top_k
                    if active_profile is not None
                    else settings.retrieval_top_k
                ),
                context_lines=(
                    settings
                    .retrieval_context_lines
                ),
                max_span_lines=(
                    settings
                    .retrieval_max_span_lines
                ),
                rrf_k=(
                    active_profile.rrf_k
                    if active_profile is not None
                    else settings.retrieval_rrf_k
                ),
                dense_hits=active_dense_hits,
                enabled_channels=(
                    active_profile.enabled_channels
                    if active_profile is not None
                    else None
                ),
                channel_weights=(
                    active_profile.channel_weights
                    if active_profile is not None
                    else None
                ),
            )
        except (
            SearchToolError,
            OSError,
            ValueError,
        ) as exc:
            return stage_error_result(
                state=state,
                stage="code_search",
                code=(
                    "HYBRID_RETRIEVAL_FAILED"
                ),
                category="environment",
                message=(
                    f"{target_name}: {exc}"
                ),
                extra_update={
                    "code_search_results": (
                        legacy_results
                    ),
                    "code_evidence_packs": packs,
                    **artifact_state_update(
                        state,
                        records,
                    ),
                },
            )

        pack_payload = pack.model_dump(
            mode="json"
        )
        relative_path = (
            "analysis/retrieval/evidence_packs/"
            f"{position:02d}_"
            f"{_slug(target_category)}_"
            f"{_slug(target_name)}.json"
        )
        pack_path, pack_record = (
            write_json_artifact(
                state=state,
                relative_path=relative_path,
                payload=pack_payload,
                producer_node="code_search",
            )
        )
        packs[target_id] = pack_payload
        pack_paths[target_id] = str(
            pack_path
        )
        legacy_results[target_name] = (
            _legacy_search_result(
                pack_payload
            )
        )
        records.append(pack_record)

    return {
        "repo_index_path": str(index_path),
        "semantic_index_manifest_path": (
            semantic_manifest_path
        ),
        "dense_retrieval_report_paths": (
            dense_report_paths
        ),
        "retrieval_policy_decision_paths": (
            policy_decision_paths
        ),
        "retrieval_policy_sha256": policy_sha256,
        "code_evidence_pack_paths": (
            pack_paths
        ),
        "code_evidence_packs": packs,
        "code_search_results": legacy_results,
        **artifact_state_update(
            state,
            records,
        ),
    }
