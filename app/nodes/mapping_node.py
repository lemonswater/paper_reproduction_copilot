from __future__ import annotations

import json
import re

from app.config import settings
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
    build_structured_stage_error,
    persist_stage_errors,
    stage_error_result,
)
from app.tools.mapping_target_tools import (
    mapping_targets_from_state,
)
from app.tools.structured_output_tools import (
    write_structured_output_trace,
)


def _trace_slug(value: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        value.lower(),
    ).strip("-")
    return (slug or "module")[:60]


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
        target_payload = target.model_dump(
            mode="json"
        )
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

        prompt = MAPPING_PROMPT.format(
            module=json.dumps(
                target_payload,
                ensure_ascii=False,
                indent=2,
            ),
            evidence_pack=json.dumps(
                pack_payload,
                ensure_ascii=False,
                indent=2,
            ),
        )

        invocation = model_gateway.invoke_structured(
            task_kind="paper_code_mapping",
            schema=ModuleMapping,
            prompt=prompt,
            node_name=f"mapping:{target.target_id}",
            job_id=state.get("job_id"),
            run_id=state.get("run_id"),
            quality_tier="high",
        )

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
