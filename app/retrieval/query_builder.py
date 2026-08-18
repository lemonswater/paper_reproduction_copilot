from __future__ import annotations

from typing import Any


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _append_unique(
    output: list[str],
    value: Any,
) -> None:
    normalized = _clean(value)
    if normalized and normalized not in output:
        output.append(normalized)


def build_lexical_query(
    module: dict[str, Any],
) -> str:
    """
    Phase 20 sparse 通道继续使用短查询。

    不把大量 PaperEvidence 塞给 literal rg，否则长句几乎不会逐行命中。
    """

    values: list[str] = []
    _append_unique(values, module.get("name"))
    _append_unique(
        values,
        module.get("description"),
    )
    return "\n".join(values)


def build_semantic_query(
    module: dict[str, Any],
    *,
    max_chars: int = 6000,
) -> str:
    """
    为 Dense Retrieval 提供包含论文语义和行为线索的查询。

    查询只来自已经结构化、可追踪的 CodeMappingTarget，不让模型临时扩写。
    """

    if max_chars < 200:
        raise ValueError(
            "semantic query max_chars 不能小于 200"
        )

    lines: list[str] = []
    category = _clean(
        module.get("category")
    )
    name = _clean(module.get("name"))
    description = _clean(
        module.get("description")
    )
    if category:
        lines.append(
            f"mapping target category: {category}"
        )
    if name:
        lines.append(f"paper target: {name}")
    if description:
        lines.append(
            f"module behavior: {description}"
        )

    keywords: list[str] = []
    for value in (
        module.get("possible_keywords") or []
    ):
        _append_unique(keywords, value)
    if keywords:
        lines.append(
            "paper terminology: "
            + ", ".join(keywords)
        )

    evidence_values: list[str] = []
    for evidence in module.get(
        "evidence",
        [],
    ):
        if not isinstance(evidence, dict):
            continue
        _append_unique(
            evidence_values,
            evidence.get("quote_or_summary")
            or evidence.get("summary")
            or evidence.get("text"),
        )

    for value in evidence_values:
        candidate = (
            "paper evidence: "
            f"{value}"
        )
        if (
            len("\n".join([*lines, candidate]))
            > max_chars
        ):
            break
        lines.append(candidate)

    query = "\n".join(lines).strip()
    if not query:
        raise ValueError(
            "CodeMappingTarget 无法构造 semantic query"
        )
    return query[:max_chars]
