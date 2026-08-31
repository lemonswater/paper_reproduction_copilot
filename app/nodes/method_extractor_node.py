from __future__ import annotations

from app.config import settings
from app.model_routing.factory import build_model_gateway
from app.model_routing.gateway import (
    RoutedStructuredInvocation,
)
from app.paper.chunking import (
    build_section_chunks,
    select_extraction_chunks,
)
from app.paper.evidence import (
    InvalidEvidenceReference,
    validate_extraction_evidence_references,
    validate_extraction_identity,
)
from app.paper.extraction_cache import (
    build_section_cache_key,
    load_valid_section_cache,
    section_cache_relative_path,
    write_section_cache,
)
from app.paper.indexer import (
    load_paper_blocks,
    load_paper_sections,
)
from app.paper.reducer import reduce_section_extractions
from app.paper.schemas import (
    PaperDocument,
    SectionChunk,
    SectionExtractionDraft,
)
from app.prompts.paper_section_prompt import (
    PAPER_SECTION_EXTRACTION_PROMPT,
    PAPER_SECTION_EXTRACTION_PROMPT_VERSION,
    PAPER_SECTION_EMPTY_RESULT_RETRY_PROMPT,
    PAPER_SECTION_FAILURE_RETRY_PROMPT,
    PAPER_SECTION_METHOD_EMPTY_RETRY_PROMPT,
    PAPER_SECTION_TRUNCATION_RETRY_PROMPT,
)
from app.schemas import PaperSummary
from app.tools.artifact_tools import (
    artifact_dir,
    artifact_state_update,
    register_existing_artifact,
    resolve_artifact_path,
    write_json_artifact,
)
from app.tools.error_tools import (
    build_stage_error,
    build_structured_stage_error,
    persist_stage_errors,
    stage_error_result,
)
from app.tools.mapping_target_tools import (
    build_code_mapping_targets,
    load_mapping_alias_rules,
)
from app.tools.structured_output_tools import (
    write_structured_output_trace,
)


def _build_method_extraction_fallback() -> PaperSummary:
    """结构化提取失败时不编造论文方法，确保下游不会生成可执行命令。"""

    return PaperSummary(
        title=None,
        research_problem="unknown",
        core_idea="unknown",
        method_modules=[],
        datasets=[],
        metrics=[],
        experiment_settings=[],
        reproduction_risks=[
            "论文结构化提取失败，当前结果不能用于可靠复现。",
        ],
        unresolved_questions=[
            "模型为什么没有返回符合 PaperSummary 的结构？",
            "需要重新检查论文文本提取结果和 structured output provider。",
        ],
    )

def _invocation_is_truncation(
    invocation: RoutedStructuredInvocation,
) -> bool:
    """判断调用失败是不是因为输出在 JSON 完成前被截断。"""

    if invocation.result is None:
        return False
    for attempt in invocation.result.attempts:
        if attempt.truncated:
            return True
        if attempt.error_type and "length" in attempt.error_type.lower():
            return True
        finish_reason = (
            str(attempt.finish_reason).strip().lower()
            if attempt.finish_reason
            else ""
        )
        if finish_reason in {"length", "max_tokens", "max_output_tokens"}:
            return True
    return False


def _requires_method_module_retry(
    chunk: SectionChunk,
    *,
    document_root_section_id: str | None,
) -> bool:
    """论文根标题即使被分类为 method，也不要求产出可实现模块。"""

    is_document_root_title = (
        chunk.page_start == 1
        and chunk.section_id
        == document_root_section_id
    )
    return (
        chunk.section_kind == "method"
        and not is_document_root_title
    )


def _extraction_is_blank(
    extraction: SectionExtractionDraft,
) -> bool:
    """拒绝用空 summary 和全部空事实列表伪装成成功抽取。"""

    if extraction.summary.strip():
        return False
    return not any(
        (
            extraction.research_problem_candidates,
            extraction.core_idea_candidates,
            extraction.method_modules,
            extraction.datasets,
            extraction.metrics,
            extraction.experiment_settings,
            extraction.reproduction_risks,
            extraction.unresolved_questions,
            extraction.table_claims_unresolved,
        )
    )


def _invoke_section_attempt(
    model_gateway,
    *,
    chunk: SectionChunk,
    prompt: str,
    state: dict,
    generated_records: list,
    attempt_label: str = "",
    route_preview=None,
) -> tuple[RoutedStructuredInvocation, str]:
    """对单个 chunk 执行一次 preview + invoke，并登记调用 trace。"""

    if route_preview is None:
        route_preview = model_gateway.preview_structured(
            task_kind="paper_section_extraction",
            schema=SectionExtractionDraft,
            prompt=prompt,
            node_name=f"method_extractor:{chunk.chunk_id}{attempt_label}",
            job_id=state.get("job_id"),
            run_id=state.get("run_id"),
            quality_tier="high",
        )
    invocation = model_gateway.invoke_structured(
        task_kind="paper_section_extraction",
        schema=SectionExtractionDraft,
        prompt=prompt,
        node_name=f"method_extractor:{chunk.chunk_id}{attempt_label}",
        job_id=state.get("job_id"),
        run_id=state.get("run_id"),
        quality_tier="high",
        expected_decision_sha256=(
            route_preview.decision_sha256
        ),
    )

    trace_path = write_structured_output_trace(
        result=invocation.result,
        node_name=f"method_extractor_{chunk.chunk_id}{attempt_label}",
        schema_name="SectionExtractionDraft",
        output_dir=artifact_dir(
            state,
            "traces",
            "structured",
        ),
        fallback_used=invocation.value is None,
        model_invocation_id=invocation.invocation_id,
        model_decision_sha256=(
            invocation.decision.decision_sha256
        ),
        model_profile_id=(
            invocation.decision.executed_profile_id
        ),
        model_name=(
            invocation.decision.executed_model_name
        ),
        model_usage_quality=(
            invocation.ledger_record.usage_quality
            if invocation.ledger_record is not None
            else None
        ),
    )
    generated_records.append(
        register_existing_artifact(
            state=state,
            path=trace_path,
            producer_node="method_extractor",
            media_type="application/json",
        )
    )
    return invocation, route_preview.executed_model_name


def method_extractor_node(state: dict) -> dict:
    document_payload = state.get("paper_document")
    blocks_path = state.get("paper_blocks_path")
    sections_path = state.get("paper_sections_path")

    if not document_payload or not blocks_path or not sections_path:
        return stage_error_result(
            state=state,
            stage="method_extractor",
            code="PAPER_INDEX_MISSING",
            category="agent",
            message="paper_reader 没有提供完整论文索引",
            terminal=True,
            extra_update={
                "paper_summary": {},
                "method_modules": [],
                "mapping_targets": [],
            },
        )

    document = PaperDocument.model_validate(document_payload)
    blocks = load_paper_blocks(str(blocks_path))
    sections = load_paper_sections(str(sections_path))
    blocks_by_id = {
        block.block_id: block
        for block in blocks
    }
    document_root_section_id = (
        sections[0].section_id
        if sections
        else None
    )

    all_chunks = build_section_chunks(
        sections,
        blocks,
        target_chars=settings.paper_section_chunk_chars,
    )
    selected_chunks = select_extraction_chunks(
        all_chunks,
        max_calls=settings.paper_max_section_llm_calls,
    )
    if not selected_chunks:
        return stage_error_result(
            state=state,
            stage="method_extractor",
            code="PAPER_SECTION_CHUNKS_EMPTY",
            category="agent",
            message="论文索引没有生成可抽取的 section chunk",
            terminal=True,
            extra_update={
                "paper_summary": {},
                "method_modules": [],
                "mapping_targets": [],
            },
        )

    model_gateway = build_model_gateway()
    extractions: list[SectionExtractionDraft] = []
    section_errors = []
    generated_records = []

    method = settings.structured_output_method
    strict = settings.structured_output_strict
    schema_version = settings.paper_extraction_version

    for chunk in selected_chunks:
        prompt = PAPER_SECTION_EXTRACTION_PROMPT.format(
            section_id=chunk.section_id,
            chunk_id=chunk.chunk_id,
            section_title=chunk.section_title,
            section_kind=chunk.section_kind,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            section_text=chunk.text,
        )
        requires_method_modules = (
            _requires_method_module_retry(
                chunk,
                document_root_section_id=(
                    document_root_section_id
                ),
            )
        )
        route_preview = model_gateway.preview_structured(
            task_kind="paper_section_extraction",
            schema=SectionExtractionDraft,
            prompt=prompt,
            node_name=f"method_extractor:{chunk.chunk_id}",
            job_id=state.get("job_id"),
            run_id=state.get("run_id"),
            quality_tier="high",
        )
        # Cache 必须绑定实际执行模型，不再绑定全局默认模型。
        model_name = route_preview.executed_model_name
        cache_key = build_section_cache_key(
            source_sha256=document.source_sha256,
            chunk=chunk,
            prompt_version=PAPER_SECTION_EXTRACTION_PROMPT_VERSION,
            schema_version=schema_version,
            model_name=model_name,
            method=method,
            strict=strict,
        )

        cached = load_valid_section_cache(
            state=state,
            chunk=chunk,
            expected_cache_key=cache_key,
            prompt_version=PAPER_SECTION_EXTRACTION_PROMPT_VERSION,
            schema_version=schema_version,
            model_name=model_name,
            method=method,
            strict=strict,
        )
        if cached is not None:
            try:
                validate_extraction_identity(cached, chunk)
                validate_extraction_evidence_references(
                    extraction=cached,
                    chunk=chunk,
                    blocks_by_id=blocks_by_id,
                )
            except (ValueError, InvalidEvidenceReference) as exc:
                # 旧缓存可能来自更宽松的业务规则。记录后重新请求模型，
                # 不能继续使用，也不能让整个文档立即终止。
                section_errors.append(
                    build_stage_error(
                        stage="method_extractor",
                        code="PAPER_SECTION_CACHE_INVALID",
                        category="agent",
                        message=str(exc),
                        terminal=False,
                        context={
                            "section_id": chunk.section_id,
                            "chunk_id": chunk.chunk_id,
                        },
                    )
                )
                cached = None

        if (
            cached is not None
            and _extraction_is_blank(cached)
        ):
            section_errors.append(
                build_stage_error(
                    stage="method_extractor",
                    code="PAPER_SECTION_EMPTY_EXTRACTION",
                    category="agent",
                    message="章节缓存为空抽取，已失效并重新请求。",
                    terminal=False,
                    context={
                        "section_id": chunk.section_id,
                        "chunk_id": chunk.chunk_id,
                    },
                )
            )
            cached = None

        if (
            cached is not None
            and requires_method_modules
            and not cached.method_modules
        ):
            # 方法章节缓存本身就是一次空抽取的产物，作废后重新请求，
            # 避免空结果被无限期复用。
            section_errors.append(
                build_stage_error(
                    stage="method_extractor",
                    code="PAPER_SECTION_EMPTY_METHOD_MODULES",
                    category="agent",
                    message="方法章节缓存未识别出任何方法模块，已失效并重新请求。",
                    terminal=False,
                    context={
                        "section_id": chunk.section_id,
                        "chunk_id": chunk.chunk_id,
                    },
                )
            )
            cached = None

        if cached is not None:
            # 即使上次进程在“写缓存”和“提交节点 state”之间退出，
            # 恢复后也能把已存在的缓存重新登记进 manifest。
            cache_path = resolve_artifact_path(
                state,
                section_cache_relative_path(chunk),
            )
            generated_records.append(
                register_existing_artifact(
                    state=state,
                    path=cache_path,
                    producer_node="method_extractor",
                    media_type="application/json",
                )
            )
            extractions.append(cached)
            continue

        invocation, _ = _invoke_section_attempt(
            model_gateway,
            chunk=chunk,
            prompt=prompt,
            state=state,
            generated_records=generated_records,
            route_preview=route_preview,
        )

        if (
            invocation.value is None
            and (
                requires_method_modules
                or _invocation_is_truncation(invocation)
            )
        ):
            retry_prompt = prompt + "\n\n" + (
                PAPER_SECTION_TRUNCATION_RETRY_PROMPT
                if _invocation_is_truncation(invocation)
                else PAPER_SECTION_FAILURE_RETRY_PROMPT
            )
            retry_invocation, _ = _invoke_section_attempt(
                model_gateway,
                chunk=chunk,
                prompt=retry_prompt,
                state=state,
                generated_records=generated_records,
                attempt_label="_retry1",
                )
            invocation = retry_invocation

        if invocation.value is None:
            section_errors.append(
                build_structured_stage_error(
                    stage="method_extractor",
                    invocation=invocation,
                    terminal=False,
                    context={
                        "section_id": chunk.section_id,
                        "chunk_id": chunk.chunk_id,
                        "pages": [
                            chunk.page_start,
                            chunk.page_end,
                        ],
                    },
                )
            )
            continue

        extraction = invocation.value
        if _extraction_is_blank(extraction):
            empty_retry_prompt = (
                prompt
                + "\n\n"
                + PAPER_SECTION_EMPTY_RESULT_RETRY_PROMPT
            )
            empty_retry_invocation, _ = _invoke_section_attempt(
                model_gateway,
                chunk=chunk,
                prompt=empty_retry_prompt,
                state=state,
                generated_records=generated_records,
                attempt_label="_empty_retry1",
            )
            if (
                empty_retry_invocation.value is not None
                and not _extraction_is_blank(
                    empty_retry_invocation.value
                )
            ):
                extraction = empty_retry_invocation.value

        if _extraction_is_blank(extraction):
            section_errors.append(
                build_stage_error(
                    stage="method_extractor",
                    code="PAPER_SECTION_EXTRACTION_EMPTY",
                    category="agent",
                    message=(
                        "章节抽取在专门重试后仍为空，"
                        "该结果不会写入缓存或参与论文规约。"
                    ),
                    terminal=False,
                    context={
                        "section_id": chunk.section_id,
                        "chunk_id": chunk.chunk_id,
                    },
                )
            )
            continue

        # 方法章节空抽取时用专门提示词重试一次，避免空结果被当作有效抽取。
        if (
            requires_method_modules
            and not extraction.method_modules
        ):
            method_retry_prompt = prompt + "\n\n" + PAPER_SECTION_METHOD_EMPTY_RETRY_PROMPT
            method_retry_invocation, _ = _invoke_section_attempt(
                model_gateway,
                chunk=chunk,
                prompt=method_retry_prompt,
                state=state,
                generated_records=generated_records,
                attempt_label="_method_retry1",
                )
            if (
                method_retry_invocation.value is not None
                and not _extraction_is_blank(
                    method_retry_invocation.value
                )
            ):
                extraction = method_retry_invocation.value

        # 方法章节重试后仍未识别出任何方法模块，记录错误但不阻断流程。
        if (
            requires_method_modules
            and not extraction.method_modules
        ):
            section_errors.append(
                build_stage_error(
                    stage="method_extractor",
                    code="PAPER_SECTION_METHOD_MODULES_EMPTY",
                    category="agent",
                    message="方法章节重试后仍未识别出任何方法模块。",
                    terminal=False,
                    context={
                        "section_id": chunk.section_id,
                        "chunk_id": chunk.chunk_id,
                    },
                )
            )

        try:
            validate_extraction_identity(extraction, chunk)
            validate_extraction_evidence_references(
                extraction=extraction,
                chunk=chunk,
                blocks_by_id=blocks_by_id,
            )
        except (ValueError, InvalidEvidenceReference) as exc:
            section_errors.append(
                build_stage_error(
                    stage="method_extractor",
                    code="PAPER_SECTION_EVIDENCE_INVALID",
                    category="agent",
                    message=str(exc),
                    terminal=False,
                    context={
                        "section_id": chunk.section_id,
                        "chunk_id": chunk.chunk_id,
                    },
                )
            )
            continue

        # 只有 schema、identity 和 Evidence 引用全部通过后才能写缓存。
        _, cache_record = write_section_cache(
            state=state,
            chunk=chunk,
            cache_key=cache_key,
            prompt_version=PAPER_SECTION_EXTRACTION_PROMPT_VERSION,
            schema_version=schema_version,
            model_name=model_name,
            method=method,
            strict=strict,
            extraction=extraction,
        )
        generated_records.append(cache_record)
        extractions.append(extraction)

    if not extractions:
        summary = _build_method_extraction_fallback()
        facts = []
        conflicts = []
        section_errors.append(
            build_stage_error(
                stage="method_extractor",
                code="ALL_PAPER_SECTIONS_FAILED",
                category="agent",
                message="所有选中的论文 section 均抽取失败",
                terminal=True,
                context={
                    "selected_chunk_count": len(selected_chunks),
                },
            )
        )
    else:
        summary, facts, conflicts = reduce_section_extractions(
            document=document,
            sections=sections,
            chunks=selected_chunks,
            blocks=blocks,
            extractions=extractions,
        )

        if section_errors:
            failed_questions = [
                (
                    "章节抽取存在局部失败："
                    f"{error.context.get('chunk_id', error.code)}"
                )
                for error in section_errors
            ]
            summary = summary.model_copy(
                update={
                    "unresolved_questions": [
                        *summary.unresolved_questions,
                        *failed_questions,
                    ]
                }
            )

    try:
        mapping_alias_rules = load_mapping_alias_rules(
            settings.mapping_aliases_path
        )
    except (TypeError, ValueError) as exc:
        section_errors.append(
            build_stage_error(
                stage="method_extractor",
                code="MAPPING_ALIASES_INVALID",
                category="user",
                message=str(exc),
                terminal=False,
                context={
                    "mapping_aliases_path": str(
                        settings.mapping_aliases_path
                    ),
                },
            )
        )
        mapping_alias_rules = []

    # 先持久化 StageError，得到 error report 的 ArtifactRecord。
    error_update = (
        persist_stage_errors(
            state=state,
            new_errors=section_errors,
        )
        if section_errors
        else {}
    )
    working_state = {**state, **error_update}

    mapping_target_result = build_code_mapping_targets(
        paper_summary=summary.model_dump(
            mode="json"
        ),
        method_modules=[
            module.model_dump(mode="json")
            for module in summary.method_modules
        ],
        section_titles=[
            section.title
            for section in sections
        ],
        max_targets=settings.mapping_max_targets,
        category_limits={
            "core_method": (
                settings
                .mapping_max_core_method_targets
            ),
            "data_pipeline": (
                settings
                .mapping_max_data_pipeline_targets
            ),
            "training_config": (
                settings
                .mapping_max_training_config_targets
            ),
            "evaluation_metric": (
                settings
                .mapping_max_evaluation_metric_targets
            ),
            "ablation_switch": (
                settings
                .mapping_max_ablation_switch_targets
            ),
        },
        alias_rules=mapping_alias_rules,
    )

    _, summary_record = write_json_artifact(
        state=working_state,
        relative_path="analysis/paper_summary.json",
        payload=summary.model_dump(mode="json"),
        producer_node="method_extractor",
    )
    _, modules_record = write_json_artifact(
        state=working_state,
        relative_path="analysis/method_modules.json",
        payload=[
            module.model_dump(mode="json")
            for module in summary.method_modules
        ],
        producer_node="method_extractor",
    )
    _, facts_record = write_json_artifact(
        state=working_state,
        relative_path="analysis/paper_fact_index.json",
        payload=[
            fact.model_dump(mode="json")
            for fact in facts
        ],
        producer_node="method_extractor",
    )
    _, conflicts_record = write_json_artifact(
        state=working_state,
        relative_path="analysis/paper_conflicts.json",
        payload=[
            conflict.model_dump(mode="json")
            for conflict in conflicts
        ],
        producer_node="method_extractor",
    )
    targets_path, targets_record = write_json_artifact(
        state=working_state,
        relative_path="analysis/mapping_targets.json",
        payload=(
            mapping_target_result
            .artifact_payload()
        ),
        producer_node="method_extractor",
    )

    output_records = [
        *generated_records,
        summary_record,
        modules_record,
        facts_record,
        conflicts_record,
        targets_record,
    ]
    return {
        "paper_summary": summary.model_dump(mode="json"),
        "method_modules": [
            module.model_dump(mode="json")
            for module in summary.method_modules
        ],
        "mapping_targets": [
            target.model_dump(mode="json")
            for target in (
                mapping_target_result.targets
            )
        ],
        "mapping_targets_path": str(
            targets_path
        ),
        **error_update,
        **artifact_state_update(
            working_state,
            output_records,
        ),
    }
