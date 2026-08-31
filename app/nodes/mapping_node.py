from __future__ import annotations

import json
import re

from app.config import settings
from app.model_routing.errors import (
    ModelBudgetExceeded,
    ModelRouteUnavailable,
)
from app.model_routing.factory import build_model_gateway
from app.prompts.mapping_prompt import MAPPING_PROMPT
from app.retrieval.schemas import (
    CodeEvidence,
    EvidencePack,
)
from app.retrieval.service import validate_code_evidence
from app.schemas import (
    CodeCandidate,
    CodeMappingTarget,
    Evidence,
    ModuleMapping,
)
from app.tools.artifact_tools import (
    artifact_dir,
    artifact_state_update,
    register_existing_artifact,
    write_json_artifact,
    write_text_artifact,
)
from app.tools.error_tools import (
    build_stage_error,
    build_structured_stage_error,
    persist_stage_errors,
    stage_error_result,
)
from app.tools.mapping_target_tools import (
    mapping_targets_from_state,
)
from app.tools.mapping_alias_tools import alias_conflicts
from app.tools.structured_output_tools import (
    write_structured_output_trace,
)

_MAPPING_EVIDENCE_ITEM_LIMIT = 6
_MAPPING_EVIDENCE_TEXT_BUDGET_BYTES = 16_000
_MAPPING_EVIDENCE_ITEM_MAX_BYTES = 3_200
_STRONG_EVIDENCE_RELATIVE_SCORE = 0.95
_STRONG_EVIDENCE_MAX_CANDIDATES = 2
_GENERIC_IDENTITY_TOKENS = {
    "architecture",
    "block",
    "component",
    "framework",
    "implementation",
    "method",
    "model",
    "module",
    "network",
    "operator",
}


def _trace_slug(value: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        value.lower(),
    ).strip("-")
    return (slug or "module")[:60]


def _truncate_utf8(value: object, max_bytes: int) -> str:
    """按路由器采用的 UTF-8 字节口径限制提示词字段。"""

    if max_bytes <= 0:
        return ""
    text = str(value or "")
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    suffix = "\n...[truncated]"
    suffix_bytes = suffix.encode("utf-8")
    if max_bytes <= len(suffix_bytes):
        return encoded[:max_bytes].decode(
            "utf-8",
            errors="ignore",
        )
    prefix = encoded[
        : max(0, max_bytes - len(suffix_bytes))
    ].decode("utf-8", errors="ignore")
    return prefix.rstrip() + suffix


def _compact_text_list(
    values: object,
    *,
    max_items: int,
    item_max_bytes: int,
) -> list[str]:
    if not isinstance(values, list):
        return []
    output: list[str] = []
    for value in values[:max_items]:
        compact = _truncate_utf8(
            value,
            item_max_bytes,
        ).strip()
        if compact:
            output.append(compact)
    return output


def _compact_mapping_target(
    target: CodeMappingTarget,
) -> dict:
    """只发送语义检索所需字段，完整论文 Evidence 仍保留在 Artifact。"""

    return {
        "target_id": target.target_id,
        "category": target.category,
        "name": target.name,
        "description": _truncate_utf8(
            target.description,
            2_500,
        ),
        "aliases": _compact_text_list(
            target.aliases,
            max_items=8,
            item_max_bytes=120,
        ),
        "possible_keywords": _compact_text_list(
            target.possible_keywords,
            max_items=16,
            item_max_bytes=120,
        ),
    }


def _compact_evidence_pack(
    pack_payload: dict,
) -> dict:
    """删除绑定阶段才需要的哈希和检索诊断，保留可判读代码证据。"""

    compact_items: list[dict] = []
    remaining_text_bytes = (
        _MAPPING_EVIDENCE_TEXT_BUDGET_BYTES
    )
    raw_items = pack_payload.get("items")
    if not isinstance(raw_items, list):
        raw_items = []

    for item in raw_items[
        :_MAPPING_EVIDENCE_ITEM_LIMIT
    ]:
        if not isinstance(item, dict):
            continue
        text_budget = min(
            _MAPPING_EVIDENCE_ITEM_MAX_BYTES,
            remaining_text_bytes,
        )
        evidence_text = _truncate_utf8(
            item.get("text"),
            text_budget,
        )
        remaining_text_bytes = max(
            0,
            remaining_text_bytes
            - len(evidence_text.encode("utf-8")),
        )
        compact_items.append(
            {
                key: value
                for key, value in {
                    "evidence_id": item.get(
                        "evidence_id"
                    ),
                    "file_path": item.get(
                        "file_path"
                    ),
                    "symbol": item.get("symbol"),
                    "start_line": item.get(
                        "start_line"
                    ),
                    "end_line": item.get("end_line"),
                    "retrieval_channels": item.get(
                        "retrieval_channels"
                    )
                    or [],
                    "fused_score": item.get(
                        "fused_score"
                    ),
                    "text": evidence_text,
                }.items()
                if value is not None
            }
        )

    return {
        "query": _truncate_utf8(
            pack_payload.get("query"),
            1_500,
        ),
        "keywords": _compact_text_list(
            pack_payload.get("keywords"),
            max_items=16,
            item_max_bytes=120,
        ),
        "items": compact_items,
    }


def _build_mapping_prompt(
    *,
    target: CodeMappingTarget,
    pack_payload: dict,
) -> str:
    return MAPPING_PROMPT.format(
        module=json.dumps(
            _compact_mapping_target(target),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        evidence_pack=json.dumps(
            _compact_evidence_pack(pack_payload),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    )


def _build_mapping_fallback(
    target: CodeMappingTarget,
) -> ModuleMapping:
    return ModuleMapping(
        module_name=target.name,
        target_id=target.target_id,
        target_category=target.category,
        candidates=[],
        unresolved_questions=[
            "该模块的结构化映射调用失败，未生成可信代码候选。",
        ],
    )


def _render_mapping_markdown(
    mappings: list[dict],
) -> str:
    lines = ["# 论文与代码映射", ""]
    for mapping in mappings:
        lines.append(
            f"> 分类：`{mapping.get('target_category', 'core_method')}`"
        )
        lines.append("")
        lines.append(
            f"## {mapping['module_name']}"
        )
        lines.append("")
        unresolved = mapping.get(
            "unresolved_questions",
            [],
        )
        if unresolved:
            lines.append("### 待解决问题")
            for item in unresolved:
                lines.append(f"- {item}")
            lines.append("")

        lines.append(
            "| 候选文件 | 符号 | Evidence IDs | 置信度 | 原因 |"
        )
        lines.append("|---|---|---|---|---|")
        for candidate in mapping.get(
            "candidates",
            [],
        ):
            symbols = ", ".join(
                candidate.get("symbols", [])
            )
            evidence_ids = ", ".join(
                candidate.get("evidence_ids", [])
            )
            reason = candidate.get(
                "reason",
                "",
            ).replace("\n", " ")
            lines.append(
                f"| `{candidate['file_path']}` | "
                f"{symbols} | {evidence_ids} | "
                f"{candidate.get('confidence', 'medium')} | "
                f"{reason} |"
            )
        lines.append("")
    return "\n".join(lines)


def _compact_excerpt(
    text: str,
    limit: int = 800,
) -> str:
    """业务输出保存有限引用，完整片段仍在 Evidence Pack Artifact。"""

    normalized = "\n".join(
        line.rstrip()
        for line in text.strip().splitlines()
    )
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "\n...[truncated]"


def _to_business_evidence(
    evidence: CodeEvidence,
) -> Evidence:
    """只根据已验证 CodeEvidence 构造业务 Evidence。"""

    return Evidence(
        source_type="code",
        source_path=evidence.file_path,
        location=(
            f"lines {evidence.start_line}-"
            f"{evidence.end_line}"
        ),
        quote_or_summary=_compact_excerpt(
            evidence.text
        ),
        confidence=(
            "high"
            if len(evidence.retrieval_channels) >= 2
            else "medium"
        ),
        evidence_id=evidence.evidence_id,
        content_hash=evidence.content_hash,
        repo_revision=evidence.repo_revision,
        repo_fingerprint=(
            evidence.repo_fingerprint
        ),
        file_sha256=evidence.file_sha256,
        start_line=evidence.start_line,
        end_line=evidence.end_line,
        retrieval_channels=list(
            evidence.retrieval_channels
        ),
        retrieval_score=evidence.fused_score,
    )


def _identity_tokens(value: object) -> set[str]:
    text = re.sub(
        r"(?<=[a-z])(?=[A-Z])",
        " ",
        str(value or ""),
    ).casefold()
    raw_tokens = re.findall(
        r"[a-z0-9]+|[\u4e00-\u9fff]+",
        text,
    )
    tokens: set[str] = set()
    for token in raw_tokens:
        if (
            len(token) < 3
            or token in _GENERIC_IDENTITY_TOKENS
        ):
            continue
        tokens.add(token)
        if token.endswith("ed") and len(token) > 5:
            tokens.add(token[:-2])
        if token.endswith("ing") and len(token) > 6:
            tokens.add(token[:-3])
        if token.endswith("ing") and len(token) > 7:
            tokens.add(token[:-3] + "e")
        if token.endswith("s") and len(token) > 4:
            tokens.add(token[:-1])
        if token == "autoencoder":
            tokens.add("mae")
        if token == "convolution":
            tokens.add("conv")
    return tokens


def _target_identity_tokens(
    target: CodeMappingTarget,
) -> set[str]:
    return {
        token
        for value in [
            target.name,
            *target.aliases,
            *target.possible_keywords,
        ]
        for token in _identity_tokens(value)
    }


def _evidence_identity_tokens(
    evidence: CodeEvidence,
) -> set[str]:
    return _identity_tokens(
        " ".join(
            [
                evidence.file_path,
                evidence.symbol or "",
                evidence.text,
            ]
        )
    )


def _recover_empty_mapping_from_strong_evidence(
    *,
    target: CodeMappingTarget,
    mapping: ModuleMapping,
    pack_payload: dict,
    repo_path: str,
) -> ModuleMapping:
    """仅用多通道、身份一致且无硬冲突的有效 Evidence 补空候选。"""

    if (
        target.category != "core_method"
        or mapping.candidates
    ):
        return mapping
    try:
        pack = EvidencePack.model_validate(pack_payload)
    except (TypeError, ValueError):
        return mapping

    valid_items = [
        item
        for item in pack.items
        if validate_code_evidence(
            repo_path=repo_path,
            evidence=item,
        )
    ]
    if not valid_items:
        return mapping

    max_score = max(
        item.fused_score
        for item in valid_items
    )
    minimum_score = (
        max_score * _STRONG_EVIDENCE_RELATIVE_SCORE
    )
    target_tokens = _target_identity_tokens(target)
    if not target_tokens:
        return mapping

    selected: list[CodeEvidence] = []
    seen_paths: set[str] = set()
    for item in valid_items:
        channels = set(item.retrieval_channels)
        independent_channels = channels & {
            "dense",
            "bm25",
            "keyword",
            "path",
            "import_graph",
        }
        if (
            item.fused_score < minimum_score
            or not item.symbol
            or "symbol" not in channels
            or len(independent_channels) < 2
            or item.file_path in seen_paths
            or alias_conflicts(
                target.name,
                item.symbol,
            )
            or not (
                target_tokens
                & _evidence_identity_tokens(item)
            )
        ):
            continue
        selected.append(item)
        seen_paths.add(item.file_path)
        if (
            len(selected)
            >= _STRONG_EVIDENCE_MAX_CANDIDATES
        ):
            break

    if not selected:
        return mapping

    recovered = mapping.model_copy(
        update={
            "candidates": [
                CodeCandidate(
                    file_path=item.file_path,
                    symbols=[item.symbol]
                    if item.symbol
                    else [],
                    reason=(
                        "映射模型未保留候选；程序仅依据当前 Evidence "
                        "Pack 中符号命中、至少三种检索通道、相对高分"
                        "和目标身份词一致性补回该候选。"
                    ),
                    evidence_ids=[item.evidence_id],
                    confidence="medium",
                )
                for item in selected
            ],
            "unresolved_questions": list(
                dict.fromkeys(
                    [
                        *mapping.unresolved_questions,
                        (
                            "映射模型返回空候选；已应用受约束的强 Evidence "
                            "兜底，仍需结合完整模块调用关系复核。"
                        ),
                    ]
                )
            ),
        }
    )
    return bind_mapping_to_evidence_pack(
        mapping=recovered,
        pack_payload=pack_payload,
        repo_path=repo_path,
    )


def bind_mapping_to_evidence_pack(
    *,
    mapping: ModuleMapping,
    pack_payload: dict,
    repo_path: str,
) -> ModuleMapping:
    """
    将不可信模型选择绑定到当前仓库中的有效 Evidence。

    安全语义：
    - 不在 pack 中的文件直接删除；
    - 不存在的 evidence_id 直接忽略；
    - 已过期 Evidence 直接忽略；
    - symbols 只能来自被选 Evidence；
    - 最终 evidence 由程序重建。
    """

    pack = EvidencePack.model_validate(
        pack_payload
    )
    valid_items = [
        item
        for item in pack.items
        if validate_code_evidence(
            repo_path=repo_path,
            evidence=item,
        )
    ]
    by_id = {
        item.evidence_id: item
        for item in valid_items
    }
    by_path: dict[str, list[CodeEvidence]] = {}
    for item in valid_items:
        by_path.setdefault(
            item.file_path,
            [],
        ).append(item)

    bound_candidates: list[CodeCandidate] = []
    dropped: list[str] = []

    for candidate in mapping.candidates:
        if candidate.file_path not in by_path:
            dropped.append(
                f"{candidate.file_path} 不在有效 Evidence Pack 中"
            )
            continue

        selected = [
            by_id[evidence_id]
            for evidence_id in dict.fromkeys(
                candidate.evidence_ids
            )
            if evidence_id in by_id
            and by_id[evidence_id].file_path
            == candidate.file_path
        ]

        # 兼容模型漏填 evidence_ids：只允许退化到同一 pack 中
        # 同一路径的 Evidence，绝不在仓库中自行扩大读取范围。
        if not selected:
            selected = by_path[
                candidate.file_path
            ][:1]

        if not selected:
            dropped.append(
                f"{candidate.file_path} 没有可用 Evidence"
            )
            continue

        allowed_symbols = {
            item.symbol
            for item in selected
            if item.symbol
        }
        symbols = [
            symbol
            for symbol in dict.fromkeys(
                candidate.symbols
            )
            if symbol in allowed_symbols
        ]

        bound_candidates.append(
            candidate.model_copy(
                update={
                    "symbols": symbols,
                    "evidence_ids": [
                        item.evidence_id
                        for item in selected
                    ],
                    "evidence": [
                        _to_business_evidence(item)
                        for item in selected
                    ],
                }
            )
        )

    unresolved = list(
        mapping.unresolved_questions
    )
    if len(valid_items) < len(pack.items):
        unresolved.append(
            "部分 Code Evidence 因仓库 revision、文件 hash "
            "或片段 hash 变化而失效，已停止使用。"
        )
    unresolved.extend(
        f"已丢弃无依据候选：{message}"
        for message in dropped
    )

    return mapping.model_copy(
        update={
            "candidates": bound_candidates,
            "unresolved_questions": list(
                dict.fromkeys(unresolved)
            ),
        }
    )


def mapping_node(state: dict) -> dict:
    targets = mapping_targets_from_state(
        state
    )
    evidence_packs = state.get(
        "code_evidence_packs",
        {},
    )
    repo_path = state.get("repo_path")
    if (
        not targets
        or not evidence_packs
        or not repo_path
    ):
        return stage_error_result(
            state=state,
            stage="mapping",
            code="MAPPING_INPUT_MISSING",
            category="agent",
            message=(
                "代码映射需要 mapping_targets、"
                "code_evidence_packs 和 repo_path"
            ),
            extra_update={
                "paper_code_mapping": [],
            },
        )

    model_gateway = build_model_gateway()
    mappings: list[dict] = []
    trace_records = []
    structured_errors = []

    for index, target in enumerate(targets):
        target_name = target.name
        pack_payload = (
            evidence_packs.get(
                target.target_id
            )
            or evidence_packs.get(
                target_name
            )
        )
        if not isinstance(pack_payload, dict):
            mappings.append(
                _build_mapping_fallback(
                    target
                ).model_dump()
            )
            continue

        prompt = _build_mapping_prompt(
            target=target,
            pack_payload=pack_payload,
        )

        try:
            invocation = model_gateway.invoke_structured(
                task_kind="paper_code_mapping",
                schema=ModuleMapping,
                prompt=prompt,
                node_name=(
                    f"mapping:{target.target_id}"
                ),
                job_id=state.get("job_id"),
                run_id=state.get("run_id"),
                quality_tier="high",
            )
        except (
            ModelRouteUnavailable,
            ModelBudgetExceeded,
        ) as exc:
            mapping = _build_mapping_fallback(target)
            error_code = (
                "MAPPING_MODEL_BUDGET_EXCEEDED"
                if isinstance(exc, ModelBudgetExceeded)
                else "MAPPING_MODEL_ROUTE_UNAVAILABLE"
            )
            structured_errors.append(
                build_stage_error(
                    stage="mapping",
                    code=error_code,
                    category="agent",
                    message=str(exc),
                    retryable=False,
                    terminal=False,
                    exception_type=type(exc).__name__,
                    context={
                        "target_id": target.target_id,
                        "target_category": (
                            target.category
                        ),
                        "target_name": target_name,
                    },
                )
            )
            mappings.append(
                mapping.model_dump(mode="json")
            )
            continue

        if invocation.value is not None:
            mapping = invocation.value
            unresolved = list(
                mapping.unresolved_questions
            )
            if mapping.module_name != target_name:
                unresolved.append(
                    "模型返回的 module_name 与输入不一致，"
                    "已使用输入目标名覆盖。"
                )
            mapping = mapping.model_copy(
                update={
                    "module_name": target_name,
                    "target_id": target.target_id,
                    "target_category": (
                        target.category
                    ),
                    "unresolved_questions": (
                        unresolved
                    ),
                }
            )

            # 结构校验成功不等于业务可信。
            # 此步骤执行文件、symbol、ID、hash 四重绑定。
            mapping = bind_mapping_to_evidence_pack(
                mapping=mapping,
                pack_payload=pack_payload,
                repo_path=str(repo_path),
            )
            mapping = _recover_empty_mapping_from_strong_evidence(
                target=target,
                mapping=mapping,
                pack_payload=pack_payload,
                repo_path=str(repo_path),
            )
        else:
            mapping = _build_mapping_fallback(
                target
            )
            structured_errors.append(
                build_structured_stage_error(
                    stage="mapping",
                    invocation=invocation,
                    terminal=False,
                    context={
                        "target_id": (
                            target.target_id
                        ),
                        "target_category": (
                            target.category
                        ),
                        "target_name": target_name,
                    },
                )
            )

        trace_path = write_structured_output_trace(
            result=invocation.result,
            node_name=(
                f"mapping_{index:02d}_"
                f"{_trace_slug(target.category)}_"
                f"{_trace_slug(target_name)}"
            ),
            schema_name="ModuleMapping",
            output_dir=artifact_dir(
                state,
                "traces",
                "structured",
            ),
            fallback_used=(
                invocation.value is None
            ),
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

        mappings.append(
            mapping.model_dump(mode="json")
        )
        trace_records.append(
            register_existing_artifact(
                state=state,
                path=trace_path,
                producer_node="mapping",
                media_type="application/json",
            )
        )

    _, json_record = write_json_artifact(
        state=state,
        relative_path=(
            "analysis/paper_code_mapping.json"
        ),
        payload=mappings,
        producer_node="mapping",
    )
    _, md_record = write_text_artifact(
        state=state,
        relative_path=(
            "analysis/paper_code_mapping.md"
        ),
        text=_render_mapping_markdown(mappings),
        producer_node="mapping",
        media_type="text/markdown",
    )

    payload = {
        "paper_code_mapping": mappings,
        **artifact_state_update(
            state,
            [
                json_record,
                md_record,
                *trace_records,
            ],
        ),
    }

    if structured_errors:
        working_state = {
            **state,
            **payload,
        }
        payload.update(
            persist_stage_errors(
                state=working_state,
                new_errors=structured_errors,
            )
        )

    return payload
