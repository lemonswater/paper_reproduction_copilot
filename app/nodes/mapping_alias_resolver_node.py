from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.model_routing.errors import (
    ModelBudgetExceeded,
    ModelRouteUnavailable,
)
from app.model_routing.factory import build_model_gateway
from app.paper.indexer import load_paper_sections
from app.prompts.mapping_alias_prompt import (
    MAPPING_ALIAS_PROMPT_VERSION,
    MAPPING_ALIAS_RESOLUTION_PROMPT,
)
from app.schemas import MappingAliasBatchDecision
from app.tools.artifact_tools import (
    artifact_dir,
    artifact_state_update,
    register_existing_artifact,
    write_json_artifact,
)
from app.tools.error_tools import (
    build_stage_error,
    build_structured_stage_error,
    persist_stage_errors,
)
from app.tools.mapping_alias_tools import (
    AliasCandidateBuildResult,
    MAPPING_ALIAS_POLICY_VERSION,
    build_alias_candidate_groups,
    validate_and_apply_alias_decisions,
)
from app.tools.mapping_target_tools import (
    build_code_mapping_targets,
    load_mapping_alias_rules,
    prepare_mapping_method_modules,
)
from app.tools.structured_output_tools import (
    write_structured_output_trace,
)


_ALIAS_PROMPT_MAX_BYTES = 12_000


def _truncate_utf8(
    value: Any,
    max_bytes: int,
) -> str:
    encoded = str(value or "").encode("utf-8")
    if len(encoded) <= max_bytes:
        return encoded.decode("utf-8")
    return encoded[:max_bytes].decode(
        "utf-8",
        errors="ignore",
    )


def _paper_context(
    paper_summary: dict[str, Any],
) -> dict[str, str]:
    return {
        "title": _truncate_utf8(
            paper_summary.get("title"),
            500,
        ),
        "core_idea": _truncate_utf8(
            paper_summary.get("core_idea"),
            1_000,
        ),
    }


def _build_prompt(
    *,
    paper_summary: dict[str, Any],
    candidate_groups: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    context_json = json.dumps(
        _paper_context(paper_summary),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    included: list[dict[str, Any]] = []
    prompt = ""
    for group in candidate_groups:
        proposed = [*included, group]
        proposed_prompt = (
            MAPPING_ALIAS_RESOLUTION_PROMPT.format(
                paper_context=context_json,
                candidate_groups=json.dumps(
                    proposed,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
        )
        if (
            len(proposed_prompt.encode("utf-8"))
            > _ALIAS_PROMPT_MAX_BYTES
        ):
            break
        included = proposed
        prompt = proposed_prompt
    return prompt, included


def _section_titles(state: dict[str, Any]) -> list[str]:
    raw_path = state.get("paper_sections_path")
    if not raw_path:
        return []
    try:
        return [
            section.title
            for section in load_paper_sections(
                str(raw_path)
            )
        ]
    except (OSError, TypeError, ValueError):
        return []


def _limited_candidate_result(
    result: AliasCandidateBuildResult,
    groups: list[dict[str, Any]],
) -> AliasCandidateBuildResult:
    return AliasCandidateBuildResult(
        indexed_modules=result.indexed_modules,
        groups=groups,
        blocked_pairs=result.blocked_pairs,
    )


def _category_limits() -> dict[str, int]:
    return {
        "core_method": (
            settings.mapping_max_core_method_targets
        ),
        "data_pipeline": (
            settings.mapping_max_data_pipeline_targets
        ),
        "training_config": (
            settings.mapping_max_training_config_targets
        ),
        "evaluation_metric": (
            settings.mapping_max_evaluation_metric_targets
        ),
        "ablation_switch": (
            settings.mapping_max_ablation_switch_targets
        ),
    }


def mapping_alias_resolver_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    paper_summary = state.get("paper_summary")
    raw_method_modules = state.get("method_modules")
    if not isinstance(paper_summary, dict):
        paper_summary = {}
    if not isinstance(raw_method_modules, list):
        raw_method_modules = []

    prepared_modules = prepare_mapping_method_modules(
        paper_summary=paper_summary,
        method_modules=[
            module
            for module in raw_method_modules
            if isinstance(module, dict)
        ],
    )
    candidate_result = build_alias_candidate_groups(
        prepared_modules
    )
    prompt, prompt_groups = _build_prompt(
        paper_summary=paper_summary,
        candidate_groups=candidate_result.groups,
    )
    prompt_candidate_result = _limited_candidate_result(
        candidate_result,
        prompt_groups,
    )

    invocation = None
    response: MappingAliasBatchDecision | None = None
    trace_path: Path | None = None
    resolution_errors = []
    resolution_status = (
        "no_candidates"
        if not candidate_result.groups
        else "fallback"
    )

    if prompt_groups:
        try:
            invocation = build_model_gateway().invoke_structured(
                task_kind="mapping_alias_resolution",
                schema=MappingAliasBatchDecision,
                prompt=prompt,
                node_name="mapping_alias_resolver",
                job_id=state.get("job_id"),
                run_id=state.get("run_id"),
                quality_tier="balanced",
                requested_max_output_tokens=4096,
            )
        except (
            ModelRouteUnavailable,
            ModelBudgetExceeded,
        ) as exc:
            resolution_errors.append(
                build_stage_error(
                    stage="mapping_alias_resolver",
                    code=(
                        "MAPPING_ALIAS_MODEL_BUDGET_EXCEEDED"
                        if isinstance(
                            exc,
                            ModelBudgetExceeded,
                        )
                        else "MAPPING_ALIAS_MODEL_ROUTE_UNAVAILABLE"
                    ),
                    category="agent",
                    message=str(exc),
                    retryable=False,
                    terminal=False,
                    exception_type=type(exc).__name__,
                )
            )
        except Exception as exc:
            # 别名归并只是映射前的可选增强。Provider 临时异常、鉴权
            # 异常或客户端构造失败时保留原始目标，不能中断论文复现。
            resolution_errors.append(
                build_stage_error(
                    stage="mapping_alias_resolver",
                    code="MAPPING_ALIAS_MODEL_INVOCATION_FAILED",
                    category="agent",
                    message=str(exc),
                    retryable=False,
                    terminal=False,
                    exception_type=type(exc).__name__,
                )
            )
        else:
            trace_path = write_structured_output_trace(
                result=invocation.result,
                node_name="mapping_alias_resolver",
                schema_name="MappingAliasBatchDecision",
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
            if invocation.value is None:
                resolution_errors.append(
                    build_structured_stage_error(
                        stage="mapping_alias_resolver",
                        invocation=invocation,
                        terminal=False,
                    )
                )
            else:
                response = invocation.value
                resolution_status = "resolved"
    elif candidate_result.groups:
        resolution_status = "prompt_budget_exhausted"
        resolution_errors.append(
            build_stage_error(
                stage="mapping_alias_resolver",
                code="MAPPING_ALIAS_PROMPT_BUDGET_EXHAUSTED",
                category="agent",
                message=(
                    "疑似别名组超过受控 Prompt 预算，"
                    "已使用确定性目标构造结果。"
                ),
                terminal=False,
            )
        )

    resolved_modules, decision_records = (
        validate_and_apply_alias_decisions(
            prompt_candidate_result,
            response,
        )
    )
    accepted_count = sum(
        1
        for decision in decision_records
        if decision.get("accepted") is True
    )

    try:
        configured_alias_rules = load_mapping_alias_rules(
            settings.mapping_aliases_path
        )
    except (TypeError, ValueError) as exc:
        configured_alias_rules = []
        resolution_errors.append(
            build_stage_error(
                stage="mapping_alias_resolver",
                code="MAPPING_ALIASES_INVALID",
                category="user",
                message=str(exc),
                terminal=False,
                context={
                    "mapping_aliases_path": str(
                        settings.mapping_aliases_path
                    )
                },
            )
        )

    target_result = build_code_mapping_targets(
        paper_summary=paper_summary,
        method_modules=resolved_modules,
        section_titles=_section_titles(state),
        max_targets=settings.mapping_max_targets,
        category_limits=_category_limits(),
        alias_rules=configured_alias_rules,
        include_summary_components=False,
    )

    error_update = (
        persist_stage_errors(
            state=state,
            new_errors=resolution_errors,
        )
        if resolution_errors
        else {}
    )
    working_state = {**state, **error_update}
    _, candidate_record = write_json_artifact(
        state=working_state,
        relative_path=(
            "analysis/mapping_alias_candidates.json"
        ),
        payload={
            "policy_version": MAPPING_ALIAS_POLICY_VERSION,
            "prompt_version": MAPPING_ALIAS_PROMPT_VERSION,
            "candidate_group_count": len(
                candidate_result.groups
            ),
            "prompt_group_count": len(prompt_groups),
            "groups": candidate_result.groups,
            "blocked_pairs": (
                candidate_result.blocked_pairs
            ),
        },
        producer_node="mapping_alias_resolver",
    )
    _, decision_record = write_json_artifact(
        state=working_state,
        relative_path=(
            "analysis/mapping_alias_decisions.json"
        ),
        payload={
            "policy_version": MAPPING_ALIAS_POLICY_VERSION,
            "status": resolution_status,
            "accepted_count": accepted_count,
            "decisions": decision_records,
        },
        producer_node="mapping_alias_resolver",
    )
    targets_path, targets_record = write_json_artifact(
        state=working_state,
        relative_path="analysis/mapping_targets.json",
        payload=target_result.artifact_payload(),
        producer_node="mapping_alias_resolver",
    )
    records = [
        candidate_record,
        decision_record,
        targets_record,
    ]
    if trace_path is not None:
        records.append(
            register_existing_artifact(
                state=working_state,
                path=trace_path,
                producer_node="mapping_alias_resolver",
                media_type="application/json",
            )
        )

    return {
        "mapping_alias_decisions": decision_records,
        "mapping_alias_resolution_status": resolution_status,
        "mapping_targets": [
            target.model_dump(mode="json")
            for target in target_result.targets
        ],
        "mapping_targets_path": str(targets_path),
        **error_update,
        **artifact_state_update(
            working_state,
            records,
        ),
    }
