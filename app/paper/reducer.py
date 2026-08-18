from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Literal

from app.paper.evidence import resolve_evidence, to_legacy_evidence
from app.paper.normalization import normalize_key
from app.paper.schemas import (
    EvidenceDraft,
    PaperBlock,
    PaperConflict,
    PaperDocument,
    PaperFactRecord,
    PaperSection,
    SectionChunk,
    SectionExtractionDraft,
)
from app.schemas import (
    Evidence,
    ExperimentSetting,
    MethodModule,
    PaperSummary,
)

FactCategory = Literal[
    "research_problem",
    "core_idea",
    "method_module",
    "dataset",
    "metric",
    "experiment_setting",
    "reproduction_risk",
]

# 同一类别有多个候选时，优先使用更适合支持该事实的章节。
_SECTION_KIND_PRIORITY = {
    "abstract": 0,
    "introduction": 1,
    "method": 2,
    "implementation": 3,
    "datasets": 4,
    "experiments": 5,
    "results": 6,
    "ablation": 7,
    "conclusion": 8,
    "appendix": 9,
    "limitations": 10,
    "related_work": 50,
    "references": 60,
    "other": 70,
}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_fact_id(
    *,
    category: FactCategory,
    name: str,
    value: str,
    evidence_id: str,
) -> str:
    """用事实内容和 Evidence 身份生成稳定 ID。"""

    seed = (
        f"{category}|{normalize_key(name)}|"
        f"{normalize_key(value)}|{evidence_id}"
    )
    return f"pfact-{_sha256(seed)[:16]}"


def deduplicate_facts(
    facts: list[PaperFactRecord],
) -> list[PaperFactRecord]:
    """仅删除类别、名称、值和证据来源都相同的完全重复项。"""

    unique: dict[
        tuple[str, str, str, str],
        PaperFactRecord,
    ] = {}
    for fact in facts:
        key = (
            fact.category,
            fact.normalized_key,
            normalize_key(fact.value),
            fact.evidence.content_hash,
        )
        unique.setdefault(key, fact)
    return list(unique.values())


def find_experiment_setting_conflicts(
    facts: list[PaperFactRecord],
) -> list[PaperConflict]:
    """同名设置出现不同值时保留所有事实，并生成冲突记录。"""

    groups: dict[str, list[PaperFactRecord]] = defaultdict(list)
    for fact in facts:
        if fact.category == "experiment_setting":
            groups[fact.normalized_key].append(fact)

    conflicts: list[PaperConflict] = []
    for normalized_key, group in groups.items():
        normalized_values = {
            normalize_key(fact.value)
            for fact in group
            if normalize_key(fact.value)
        }
        if len(normalized_values) <= 1:
            continue

        ordered = sorted(
            group,
            key=lambda fact: (
                fact.evidence.page_start,
                fact.fact_id,
            ),
        )
        seed = "|".join(fact.fact_id for fact in ordered)
        values = list(
            dict.fromkeys(fact.value for fact in ordered)
        )
        conflicts.append(
            PaperConflict(
                conflict_id=f"pconf-{_sha256(seed)[:16]}",
                normalized_key=normalized_key,
                fact_ids=[fact.fact_id for fact in ordered],
                values=values,
                reason=(
                    "同一规范化实验设置存在多个有原文证据支持的值；"
                    "系统保留全部值，等待后续结合数据集、模型变体或"
                    "人工信息消解。"
                ),
            )
        )

    return conflicts


def _make_fact(
    *,
    category: FactCategory,
    name: str,
    value: str,
    evidence_draft: EvidenceDraft,
    document: PaperDocument,
    section: PaperSection,
    chunk: SectionChunk,
    blocks_by_id: dict[str, PaperBlock],
) -> PaperFactRecord:
    """把模型草稿解析成不可伪造来源字段的事实记录。"""

    evidence = resolve_evidence(
        draft=evidence_draft,
        document=document,
        section=section,
        chunk=chunk,
        blocks_by_id=blocks_by_id,
    )
    return PaperFactRecord(
        fact_id=make_fact_id(
            category=category,
            name=name,
            value=value,
            evidence_id=evidence.evidence_id,
        ),
        category=category,
        name=name,
        value=value,
        normalized_key=normalize_key(name),
        evidence=evidence,
    )


def _fact_sort_key(
    fact: PaperFactRecord,
    sections_by_id: dict[str, PaperSection],
) -> tuple[int, int, str]:
    """让摘要输出不受字典顺序或 provider 返回顺序影响。"""

    section = sections_by_id.get(fact.evidence.section_id)
    priority = _SECTION_KIND_PRIORITY.get(
        section.kind if section else "other",
        70,
    )
    return (
        priority,
        fact.evidence.page_start,
        fact.fact_id,
    )


def _unique_values(
    facts: list[PaperFactRecord],
) -> list[str]:
    """按首次出现顺序返回非空且规范化后唯一的值。"""

    values: list[str] = []
    seen: set[str] = set()
    for fact in facts:
        value = fact.value.strip()
        key = normalize_key(value)
        if not value or not key or key in seen:
            continue
        seen.add(key)
        values.append(value)
    return values


def _legacy_evidence_list(
    facts: list[PaperFactRecord],
    *,
    document: PaperDocument,
    sections_by_id: dict[str, PaperSection],
) -> list[Evidence]:
    """转换并按 evidence_id 去重当前 PaperSummary 的 Evidence。"""

    result: list[Evidence] = []
    seen: set[str] = set()
    for fact in facts:
        evidence_id = fact.evidence.evidence_id
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        section = sections_by_id.get(fact.evidence.section_id)
        section_title = section.title if section else "Unknown section"
        result.append(
            to_legacy_evidence(
                fact.evidence,
                source_path=document.source_path,
                section_title=section_title,
            )
        )
    return result


def build_compatible_paper_summary(
    *,
    document: PaperDocument,
    blocks: list[PaperBlock],
    sections: list[PaperSection],
    facts: list[PaperFactRecord],
    conflicts: list[PaperConflict],
    extractions: list[SectionExtractionDraft],
    method_keywords: dict[str, list[str]],
) -> PaperSummary:
    """将事实索引确定性地投影为项目已有的 PaperSummary。"""

    sections_by_id = {
        section.section_id: section for section in sections
    }
    ordered_facts = sorted(
        facts,
        key=lambda fact: _fact_sort_key(fact, sections_by_id),
    )

    def category_facts(category: FactCategory) -> list[PaperFactRecord]:
        return [
            fact
            for fact in ordered_facts
            if fact.category == category
        ]

    research_values = _unique_values(
        category_facts("research_problem")
    )
    core_values = _unique_values(category_facts("core_idea"))

    # 当前 PaperSummary 没有 title Evidence 字段，标题只从确定性解析出的
    # title block 获取；找不到时保持 None，不让 LLM 猜测。
    title = next(
        (
            block.text.strip()
            for block in blocks
            if block.block_type == "title"
            and not block.excluded
            and block.text.strip()
        ),
        None,
    )

    method_groups: dict[str, list[PaperFactRecord]] = defaultdict(list)
    for fact in category_facts("method_module"):
        method_groups[fact.normalized_key].append(fact)

    method_modules: list[MethodModule] = []
    for normalized_name, group in method_groups.items():
        descriptions = _unique_values(group)
        missing_info: list[str] = []
        if len(descriptions) > 1:
            missing_info.append(
                "同一方法模块存在多个描述，完整事实已保留在 "
                "paper_fact_index.json。"
            )
        method_modules.append(
            MethodModule(
                name=group[0].name,
                description=(
                    descriptions[0]
                    if descriptions
                    else "论文中未抽取到有证据支持的模块描述。"
                ),
                possible_keywords=method_keywords.get(
                    normalized_name,
                    [],
                ),
                evidence=_legacy_evidence_list(
                    group,
                    document=document,
                    sections_by_id=sections_by_id,
                ),
                missing_info=missing_info,
            )
        )

    setting_groups: dict[
        tuple[str, str],
        list[PaperFactRecord],
    ] = defaultdict(list)
    for fact in category_facts("experiment_setting"):
        # name 相同但 value 不同的设置不能互相覆盖。
        key = (fact.normalized_key, normalize_key(fact.value))
        setting_groups[key].append(fact)

    experiment_settings = [
        ExperimentSetting(
            name=group[0].name,
            value=group[0].value,
            evidence=_legacy_evidence_list(
                group,
                document=document,
                sections_by_id=sections_by_id,
            ),
        )
        for group in setting_groups.values()
    ]

    unresolved: list[str] = []
    for extraction in extractions:
        unresolved.extend(extraction.unresolved_questions)
        unresolved.extend(extraction.table_claims_unresolved)
    unresolved.extend(
        (
            f"实验设置冲突 {conflict.normalized_key!r}："
            f"{', '.join(conflict.values)}"
        )
        for conflict in conflicts
    )
    unresolved = list(
        dict.fromkeys(
            item.strip()
            for item in unresolved
            if item.strip()
        )
    )

    return PaperSummary(
        title=title,
        research_problem=(
            "；".join(research_values[:3])
            if research_values
            else "论文中未抽取到有原文证据支持的研究问题。"
        ),
        core_idea=(
            "；".join(core_values[:3])
            if core_values
            else "论文中未抽取到有原文证据支持的核心思路。"
        ),
        method_modules=method_modules,
        datasets=_unique_values(category_facts("dataset")),
        metrics=_unique_values(category_facts("metric")),
        experiment_settings=experiment_settings,
        reproduction_risks=_unique_values(
            category_facts("reproduction_risk")
        ),
        unresolved_questions=unresolved,
    )


def reduce_section_extractions(
    *,
    document: PaperDocument,
    sections: list[PaperSection],
    chunks: list[SectionChunk],
    blocks: list[PaperBlock],
    extractions: list[SectionExtractionDraft],
) -> tuple[
    PaperSummary,
    list[PaperFactRecord],
    list[PaperConflict],
]:
    """规约局部抽取，返回兼容摘要、事实索引和冲突索引。"""

    sections_by_id = {
        section.section_id: section for section in sections
    }
    chunks_by_id = {
        chunk.chunk_id: chunk for chunk in chunks
    }
    blocks_by_id = {
        block.block_id: block for block in blocks
    }

    facts: list[PaperFactRecord] = []
    method_keywords: dict[str, list[str]] = defaultdict(list)

    for extraction in extractions:
        chunk = chunks_by_id.get(extraction.chunk_id)
        section = sections_by_id.get(extraction.section_id)
        if chunk is None or section is None:
            raise ValueError(
                "SectionExtractionDraft 引用了不属于当前论文索引的 "
                f"section/chunk：{extraction.section_id}/"
                f"{extraction.chunk_id}"
            )
        if chunk.section_id != section.section_id:
            raise ValueError(
                f"chunk {chunk.chunk_id!r} 不属于 "
                f"section {section.section_id!r}"
            )

        candidates = [
            (
                "research_problem",
                "research problem",
                item.value,
                item.evidence,
            )
            for item in extraction.research_problem_candidates
        ]
        candidates.extend(
            (
                "core_idea",
                "core idea",
                item.value,
                item.evidence,
            )
            for item in extraction.core_idea_candidates
        )
        candidates.extend(
            (
                "dataset",
                item.name,
                item.name,
                item.evidence,
            )
            for item in extraction.datasets
        )
        candidates.extend(
            (
                "metric",
                item.name,
                item.name,
                item.evidence,
            )
            for item in extraction.metrics
        )
        candidates.extend(
            (
                "experiment_setting",
                item.name,
                item.value,
                item.evidence,
            )
            for item in extraction.experiment_settings
        )
        candidates.extend(
            (
                "reproduction_risk",
                "reproduction risk",
                item.value,
                item.evidence,
            )
            for item in extraction.reproduction_risks
        )

        for category, name, value, evidence_draft in candidates:
            facts.append(
                _make_fact(
                    category=category,
                    name=name,
                    value=value,
                    evidence_draft=evidence_draft,
                    document=document,
                    section=section,
                    chunk=chunk,
                    blocks_by_id=blocks_by_id,
                )
            )

        for item in extraction.method_modules:
            normalized_name = normalize_key(item.name)
            for keyword in item.possible_keywords:
                if keyword and keyword not in method_keywords[normalized_name]:
                    method_keywords[normalized_name].append(keyword)
            facts.append(
                _make_fact(
                    category="method_module",
                    name=item.name,
                    value=item.description,
                    evidence_draft=item.evidence,
                    document=document,
                    section=section,
                    chunk=chunk,
                    blocks_by_id=blocks_by_id,
                )
            )

    facts = deduplicate_facts(facts)
    conflicts = find_experiment_setting_conflicts(facts)
    summary = build_compatible_paper_summary(
        document=document,
        blocks=blocks,
        sections=sections,
        facts=facts,
        conflicts=conflicts,
        extractions=extractions,
        method_keywords=dict(method_keywords),
    )
    return summary, facts, conflicts