from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.config import settings
from app.evaluation.case_loader import resolve_evaluation_path
from app.evaluation.chat_runner import run_chat_eval_case
from app.evaluation.observation import observation_from_graph_state
from app.evaluation.schemas import (
    CodeRetrievalObservation,
    EvalCase,
    EvalMetrics,
    EvalObservation,
    PaperSectionObservation,
)
from app.graph import (
    build_graph,
    route_after_action_builder,
    route_after_executor,
    route_after_human_review,
    route_after_input_validation,
    route_after_log_debug,
    route_after_patch_apply,
    route_after_patch_builder,
    route_after_patch_promotion_review,
    route_after_patch_review,
    route_after_patch_verifier,
    route_after_preflight,
    route_after_repair_action_builder,
    route_after_repair_planner,
    route_after_risk_check,
    route_after_smoke_test,
)
from app.paper.indexer import parse_paper_source
from app.retrieval import (
    PreparedDenseRetriever,
    SQLiteEmbeddingCache,
    build_evidence_pack,
    build_repository_index,
    build_semantic_chunks,
    get_embedding_backend,
)
from app.retrieval.indexer import (
    build_repository_index,
)
from app.retrieval.service import (
    build_evidence_pack,
)

RouteCallable = Callable[[dict[str, Any]], str]


# JSON 只能选择这些确定性 route，不能动态 import 任意函数。
ROUTE_FUNCTIONS: dict[str, RouteCallable] = {
    "route_after_input_validation": route_after_input_validation,
    "route_after_action_builder": route_after_action_builder,
    "route_after_risk_check": route_after_risk_check,
    "route_after_human_review": route_after_human_review,
    "route_after_preflight": route_after_preflight,
    "route_after_smoke_test": route_after_smoke_test,
    "route_after_executor": route_after_executor,
    "route_after_log_debug": route_after_log_debug,
    "route_after_repair_planner": route_after_repair_planner,
    "route_after_repair_action_builder": (
        route_after_repair_action_builder
    ),
    "route_after_patch_builder": route_after_patch_builder,
    "route_after_patch_review": route_after_patch_review,
    "route_after_patch_verifier": route_after_patch_verifier,
    "route_after_patch_promotion_review": (
        route_after_patch_promotion_review
    ),
    "route_after_patch_apply": route_after_patch_apply,
}


def run_fixture_case(case: EvalCase) -> EvalObservation:
    fixture_path = resolve_evaluation_path(
        str(case.input.fixture_path)
    )
    return EvalObservation.model_validate_json(
        fixture_path.read_text(encoding="utf-8")
    )


def run_route_case(case: EvalCase) -> EvalObservation:
    route_name = str(case.input.route_name)
    try:
        route = ROUTE_FUNCTIONS[route_name]
    except KeyError:
        raise ValueError(
            f"route_name 不在 allowlist：{route_name}"
        ) from None

    started = time.perf_counter()
    # 仅对 allowlist 中的纯路由函数临时覆盖确定性配置。
    # ExitStack 离开后立即恢复，不污染其他 case 或生产 Graph。
    with ExitStack() as stack:
        for name, value in case.input.route_settings.items():
            stack.enter_context(
                patch.object(settings, name, value)
            )
        target = route(dict(case.input.state))
    duration_ms = (time.perf_counter() - started) * 1000

    return EvalObservation(
        case_id=case.case_id,
        runner="route_function",
        route=[str(case.input.source_node), target],
        final_status=case.input.state.get("final_status"),
        stage_errors=list(
            case.input.state.get("stage_errors", [])
        ),
        metrics=EvalMetrics(duration_ms=duration_ms),
    )


def _consume_graph_stream(
    graph: Any,
    graph_input: dict[str, Any] | Command,
    *,
    config: dict[str, Any],
    route: list[str],
) -> int:
    """
    消费一次 Graph stream，并返回本次遇到的 interrupt 数量。

    stream_mode=updates 的普通 chunk 形如：
        {"paper_reader": {...}}

    interrupt chunk 的 key 通常以 "__" 开头，不把它当作业务节点。
    """

    interrupt_count = 0
    for chunk in graph.stream(
        graph_input,
        config=config,
        stream_mode="updates",
    ):
        if not isinstance(chunk, dict):
            continue

        for key in chunk:
            if key == "__interrupt__":
                interrupt_count += 1
            elif not key.startswith("__"):
                route.append(key)

    return interrupt_count


def run_live_graph_case(case: EvalCase) -> EvalObservation:
    """
    运行少量真实 Provider case。

    注意：
    1. 只允许 provider suite 调用；
    2. 默认不提供 scripted approval，因此不会自动批准危险 Action；
    3. case 的 paper_path/repo_path 仍会经过 Graph 输入验证；
    4. 每个 case 使用 MemorySaver 和唯一 thread_id，避免污染正式 checkpoint。
    """

    if case.input.scripted_responses:
        raise ValueError(
            "Phase 17 provider runner 暂不接受 scripted_responses；"
            "真实 Graph 必须停在第一次 interrupt，避免评测自动执行 Action"
        )

    if case.suite != "provider":
        raise ValueError("live_graph 只允许 provider suite")

    thread_id = (
        f"eval-{case.case_id}-{uuid4().hex[:10]}"
    )
    config = {"configurable": {"thread_id": thread_id}}
    graph = build_graph(checkpointer=MemorySaver())

    initial_state = {
        "task_id": thread_id,
        "paper_path": case.input.paper_path,
        "repo_path": case.input.repo_path,
        "log_path": case.input.log_path,
        "experiment_goal": case.input.experiment_goal,
        "execution_profile_id": (
            case.input.execution_profile_id
            or settings.default_execution_profile
        ),
        "output_files": [],
        "artifact_records": [],
        "stage_errors": [],
        "inputs_validated": False,
        "step_count": 0,
        "max_steps": settings.max_steps,
    }

    route: list[str] = []
    human_interventions = 0
    started = time.perf_counter()

    human_interventions += _consume_graph_stream(
        graph,
        initial_state,
        config=config,
        route=route,
    )

    for response in case.input.scripted_responses:
        snapshot = graph.get_state(config)
        if not snapshot.next:
            break

        human_interventions += _consume_graph_stream(
            graph,
            Command(resume=response),
            config=config,
            route=route,
        )

    snapshot = graph.get_state(config)
    final_state = dict(snapshot.values)
    duration_ms = (time.perf_counter() - started) * 1000

    return observation_from_graph_state(
        case=case,
        state=final_state,
        route=route,
        duration_ms=duration_ms,
        human_interventions=human_interventions,
        resume_succeeded=(
            bool(case.input.scripted_responses)
            and not bool(snapshot.next)
        ),
    )

def _resolve_eval_paper_path(raw_path: str) -> Path:
    """限制离线 case 只能读取 ALLOWED_ROOT 内的真实论文。"""

    path = Path(raw_path).expanduser().resolve()
    allowed_root = settings.allowed_root.resolve()
    if path == allowed_root or allowed_root not in path.parents:
        raise ValueError("评测论文路径位于 ALLOWED_ROOT 之外")
    if not path.is_file():
        raise FileNotFoundError(f"未找到评测论文：{path}")
    return path


def run_paper_parser_case(
    case: EvalCase,
) -> EvalObservation:
    """运行确定性 parser，不调用 Provider。"""

    if not case.input.paper_path:
        raise ValueError(
            "paper_parser case requires paper_path"
        )
    if case.suite != "offline":
        raise ValueError(
            "paper_parser case must use offline suite"
        )

    paper_path = _resolve_eval_paper_path(
        case.input.paper_path
    )
    started = time.perf_counter()
    parsed = parse_paper_source(paper_path)
    duration_ms = (
        time.perf_counter() - started
    ) * 1000

    section_by_id = {
        section.section_id: section
        for section in parsed.sections
    }
    section_observations = []

    for section in parsed.sections:
        parent = (
            section_by_id.get(section.parent_id)
            if section.parent_id
            else None
        )
        section_observations.append(
            PaperSectionObservation(
                number=section.number,
                title=section.title,
                parent_number=(
                    parent.number
                    if parent is not None
                    else None
                ),
                parent_title=(
                    parent.title
                    if parent is not None
                    else None
                ),
            )
        )

    return EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        route=["paper_parser"],
        final_status=parsed.report.status,
        paper_page_count=parsed.report.page_count,
        paper_indexed_pages=(
            parsed.report.indexed_pages
        ),
        paper_section_titles=[
            section.title
            for section in parsed.sections
        ],
        paper_section_kinds=[
            section.kind
            for section in parsed.sections
        ],
        paper_sections=section_observations,
        paper_ocr_required_pages=(
            parsed.report.ocr_required_pages
        ),
        metrics=EvalMetrics(
            duration_ms=duration_ms
        ),
    )

def _resolve_eval_repo_path(
    raw_path: str,
) -> Path:
    """
    相对路径只允许指向 app/evaluation 内的 fixture repo；
    绝对路径只允许位于 ALLOWED_ROOT 内，用于本机手工 Golden。
    """

    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        path = candidate.resolve()
        allowed_root = settings.allowed_root.resolve()
        if (
            path == allowed_root
            or allowed_root not in path.parents
        ):
            raise ValueError(
                "评测仓库位于 ALLOWED_ROOT 之外"
            )
    else:
        path = resolve_evaluation_path(
            raw_path
        ).resolve()

    if not path.is_dir():
        raise FileNotFoundError(
            f"未找到评测仓库：{path}"
        )
    return path


def run_code_retrieval_case(
    case: EvalCase,
) -> EvalObservation:
    """运行确定性索引、混合排名和 Evidence 构造，不调用 Provider。"""

    if case.suite != "offline":
        raise ValueError(
            "code_retrieval case must use offline suite"
        )
    if (
        not case.input.repo_path
        or not case.input.retrieval_query
    ):
        raise ValueError(
            "code_retrieval case requires "
            "repo_path and retrieval_query"
        )

    repo_path = _resolve_eval_repo_path(
        case.input.repo_path
    )
    started = time.perf_counter()
    index = build_repository_index(
        repo_path,
        index_version=(
            settings.retrieval_index_version
        ),
        max_file_bytes=(
            settings.retrieval_max_file_bytes
        ),
    )
    _, pack = build_evidence_pack(
        repo_path=repo_path,
        query=case.input.retrieval_query,
        keywords=(
            case.input.retrieval_keywords
        ),
        index=index,
        index_version=(
            settings.retrieval_index_version
        ),
        max_file_bytes=(
            settings.retrieval_max_file_bytes
        ),
        top_k=settings.retrieval_top_k,
        context_lines=(
            settings.retrieval_context_lines
        ),
        max_span_lines=(
            settings.retrieval_max_span_lines
        ),
        rrf_k=settings.retrieval_rrf_k,
    )
    duration_ms = (
        time.perf_counter() - started
    ) * 1000

    observations = []
    for rank, item in enumerate(
        pack.items,
        start=1,
    ):
        complete = bool(
            item.evidence_id
            and item.repo_fingerprint
            and item.file_sha256
            and item.content_hash
            and item.start_line <= item.end_line
        )
        observations.append(
            CodeRetrievalObservation(
                rank=rank,
                file_path=item.file_path,
                symbol=item.symbol,
                retrieval_channels=list(
                    item.retrieval_channels
                ),
                fused_score=item.fused_score,
                evidence_id=item.evidence_id,
                repo_revision=(
                    item.repo_revision
                ),
                repo_fingerprint=(
                    item.repo_fingerprint
                ),
                file_sha256=item.file_sha256,
                start_line=item.start_line,
                end_line=item.end_line,
                content_hash=item.content_hash,
                provenance_complete=complete,
            )
        )

    return EvalObservation(
        case_id=case.case_id,
        runner="code_retrieval",
        route=[
            "repository_index",
            "hybrid_retrieval",
        ],
        final_status="succeeded",
        code_retrieval=observations,
        metrics=EvalMetrics(
            duration_ms=duration_ms
        ),
    )

def run_semantic_code_retrieval_case(
    case: EvalCase,
) -> EvalObservation:
    """
    运行真实 Embedding Provider。

    只在显式选择 provider case 时执行。
    """

    if case.suite != "provider":
        raise ValueError(
            "semantic_code_retrieval "
            "case must use provider suite"
        )
    if (
        not case.input.repo_path
        or not case.input.retrieval_query
    ):
        raise ValueError(
            "semantic_code_retrieval requires "
            "repo_path and retrieval_query"
        )
    if not settings.allow_code_embedding_upload:
        raise ValueError(
            "Provider eval 要求 "
            "ALLOW_CODE_EMBEDDING_UPLOAD=true"
        )

    repo_path = _resolve_eval_repo_path(
        case.input.repo_path
    )
    started = time.perf_counter()
    index = build_repository_index(
        repo_path,
        index_version=(
            settings.retrieval_index_version
        ),
        max_file_bytes=(
            settings.retrieval_max_file_bytes
        ),
    )
    chunks, _ = build_semantic_chunks(
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
    retriever = PreparedDenseRetriever.prepare(
        chunks=chunks,
        backend=get_embedding_backend(),
        cache=SQLiteEmbeddingCache(
            settings.embedding_cache_db_path
        ),
        cache_version=(
            settings.embedding_cache_version
        ),
        batch_size=settings.embedding_batch_size,
    )
    dense_hits, dense_report = retriever.rank(
        query=case.input.retrieval_query,
        min_similarity=(
            settings.dense_min_similarity
        ),
        max_hits=settings.dense_max_hits,
        required=True,
    )
    _, pack = build_evidence_pack(
        repo_path=repo_path,
        query=case.input.retrieval_query,
        keywords=(
            case.input.retrieval_keywords
        ),
        index=index,
        index_version=(
            settings.retrieval_index_version
        ),
        max_file_bytes=(
            settings.retrieval_max_file_bytes
        ),
        top_k=settings.retrieval_top_k,
        context_lines=(
            settings.retrieval_context_lines
        ),
        max_span_lines=(
            settings.retrieval_max_span_lines
        ),
        rrf_k=settings.retrieval_rrf_k,
        dense_hits=dense_hits,
    )
    duration_ms = (
        time.perf_counter() - started
    ) * 1000

    observations = []
    for rank, item in enumerate(
        pack.items,
        start=1,
    ):
        observations.append(
            CodeRetrievalObservation(
                rank=rank,
                file_path=item.file_path,
                symbol=item.symbol,
                retrieval_channels=list(
                    item.retrieval_channels
                ),
                fused_score=item.fused_score,
                evidence_id=item.evidence_id,
                repo_revision=(
                    item.repo_revision
                ),
                repo_fingerprint=(
                    item.repo_fingerprint
                ),
                file_sha256=item.file_sha256,
                start_line=item.start_line,
                end_line=item.end_line,
                content_hash=item.content_hash,
                provenance_complete=bool(
                    item.evidence_id
                    and item.repo_fingerprint
                    and item.file_sha256
                    and item.content_hash
                    and (
                        item.start_line
                        <= item.end_line
                    )
                ),
            )
        )

    return EvalObservation(
        case_id=case.case_id,
        runner="semantic_code_retrieval",
        route=[
            "repository_index",
            "semantic_chunking",
            "embedding_provider",
            "dense_hybrid_retrieval",
        ],
        final_status="succeeded",
        code_retrieval=observations,
        embedding_provider_namespace=(
            dense_report.provider_namespace
        ),
        embedding_model=dense_report.model,
        embedding_dimensions=(
            dense_report.embedding_dimensions
        ),
        dense_fallback_reason=(
            dense_report.fallback_reason
        ),
        metrics=EvalMetrics(
            duration_ms=duration_ms,
            embedding_document_calls=(
                dense_report
                .embedding_document_calls
            ),
            embedding_query_calls=(
                dense_report
                .embedding_query_calls
            ),
            embedding_cache_hits=(
                dense_report.cache_hits
            ),
            embedding_cache_misses=(
                dense_report.cache_misses
            ),
        ),
    )

def run_case(
    case: EvalCase,
    *,
    work_dir: Path | None = None,
) -> EvalObservation:
    if case.runner == "fixture":
        observation = run_fixture_case(case)
    elif case.runner == "route_function":
        observation = run_route_case(case)
    elif case.runner == "paper_parser":
        observation = run_paper_parser_case(
            case
        )
    elif case.runner == "code_retrieval":
        observation = run_code_retrieval_case(
            case
        )
    elif case.runner == "semantic_code_retrieval":
        observation = (
            run_semantic_code_retrieval_case(
                case
            )
        )
    elif case.runner == "live_graph":
        observation = run_live_graph_case(case)
    elif case.runner in {"chat_scenario", "chat_provider"}:
        if work_dir is None:
            raise ValueError("Chat Eval runner 要求 work_dir")
        observation = run_chat_eval_case(
            case,
            work_dir=work_dir,
            provider=(case.runner == "chat_provider"),
        )
    else:
        raise ValueError(
            f"不支持的 runner：{case.runner}"
        )

    if observation.case_id != case.case_id:
        raise ValueError(
            "Observation case_id 与 Case 不一致："
            f"{observation.case_id} != "
            f"{case.case_id}"
        )
    return observation