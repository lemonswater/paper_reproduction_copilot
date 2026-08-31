from __future__ import annotations

import hashlib
import itertools
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.schemas import MappingAliasBatchDecision


MAPPING_ALIAS_POLICY_VERSION = "phase23.6-v2"
ALIAS_CLUSTER_KEY_FIELD = "_mapping_alias_cluster_key"
ALIAS_CANONICAL_NAME_FIELD = "_mapping_alias_canonical_name"
ALIAS_NAMES_FIELD = "_mapping_alias_names"

_PAIR_SCORE_THRESHOLD = 55
_GENERIC_FORMS = {
    "architecture",
    "autoencoder",
    "block",
    "component",
    "convolution",
    "encoder",
    "framework",
    "method",
    "model",
    "module",
    "network",
    "transformer",
}
_SAFE_SUFFIX_ABBREVIATIONS = {
    "attention": "attn",
    "autoencoder": "ae",
    "convolution": "conv",
    "decoder": "dec",
    "encoder": "enc",
    "network": "net",
}
_CONFLICT_FAMILIES = (
    (("encoder", "编码器"), ("decoder", "解码器")),
    (("teacher", "教师"), ("student", "学生")),
    (("input", "输入"), ("output", "输出")),
)
_TRANSPOSE_MARKERS = (
    "transpose",
    "transposed",
    "transconv",
    "deconvolution",
    "转置",
)
_DETAIL_NAME_MARKERS = (
    "architecture",
    "framework",
    "component",
    "架构",
    "框架",
    "组件",
)


@dataclass(frozen=True)
class AliasCandidateBuildResult:
    indexed_modules: list[dict[str, Any]]
    groups: list[dict[str, Any]]
    blocked_pairs: list[dict[str, Any]]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalized(value: Any) -> str:
    text = unicodedata.normalize(
        "NFKC",
        _clean(value),
    ).casefold()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)


def _unique_text(values: list[Any]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean(value)
        key = _normalized(cleaned)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output


def _identifier_words(value: str) -> list[str]:
    separated = re.sub(
        r"(?<=[a-z])(?=[A-Z])",
        " ",
        value.replace("_", " ").replace("-", " "),
    )
    return re.findall(
        r"\d+[A-Za-z]*|[A-Za-z]+|[\u4e00-\u9fff]+",
        separated,
    )


def _abbreviation_forms(value: str) -> set[str]:
    words = _identifier_words(value)
    if len(words) < 2 or any(
        re.fullmatch(r"[\u4e00-\u9fff]+", word)
        for word in words
    ):
        return set()

    prefix_options: list[list[str]] = []
    for word in words[:-1]:
        lowered = word.casefold()
        if lowered[0].isdigit():
            digits = "".join(
                character
                for character in lowered
                if character.isdigit()
            )
            prefix_options.append(
                list(dict.fromkeys([lowered, digits]))
            )
        else:
            prefix_options.append([lowered[0]])

    suffix = words[-1].casefold()
    suffix_options = [
        _SAFE_SUFFIX_ABBREVIATIONS.get(
            suffix,
            suffix,
        )
    ]
    return {
        "".join([*prefix, ending])
        for prefix in itertools.product(
            *prefix_options
        )
        for ending in suffix_options
        if "".join([*prefix, ending])
    }


def _forms(value: Any) -> set[str]:
    cleaned = _clean(value)
    normalized = _normalized(cleaned)
    if not normalized:
        return set()
    return {
        normalized,
        *_abbreviation_forms(cleaned),
    }


def _evidence_ids(module: dict[str, Any]) -> set[str]:
    return {
        str(evidence.get("evidence_id"))
        for evidence in module.get("evidence") or []
        if isinstance(evidence, dict)
        and evidence.get("evidence_id")
    }


def _module_signature(
    module: dict[str, Any],
) -> dict[str, Any]:
    name = _clean(module.get("name"))
    keywords = _unique_text(
        list(module.get("possible_keywords") or [])
    )
    name_forms = _forms(name)
    keyword_forms = {
        form
        for keyword in keywords
        for form in _forms(keyword)
        if form not in _GENERIC_FORMS
    }
    tokens = {
        token.casefold()
        for token in _identifier_words(name)
        if len(token) >= 2
        and token.casefold() not in _GENERIC_FORMS
    }
    return {
        "name": name,
        "name_forms": name_forms,
        "keyword_forms": keyword_forms,
        "tokens": tokens,
        "evidence_ids": _evidence_ids(module),
    }


def alias_conflicts(
    left_name: str,
    right_name: str,
) -> list[str]:
    left = _normalized(left_name)
    right = _normalized(right_name)
    conflicts: list[str] = []

    left_transpose = any(
        _normalized(marker) in left
        for marker in _TRANSPOSE_MARKERS
    )
    right_transpose = any(
        _normalized(marker) in right
        for marker in _TRANSPOSE_MARKERS
    )
    if left_transpose != right_transpose:
        conflicts.append("transpose_vs_forward")

    for first, second in _CONFLICT_FAMILIES:
        left_first = any(
            _normalized(marker) in left
            for marker in first
        )
        left_second = any(
            _normalized(marker) in left
            for marker in second
        )
        right_first = any(
            _normalized(marker) in right
            for marker in first
        )
        right_second = any(
            _normalized(marker) in right
            for marker in second
        )
        if (
            left_first
            and right_second
        ) or (
            left_second
            and right_first
        ):
            conflicts.append(
                f"{first[0]}_vs_{second[0]}"
            )
    return conflicts


def _pair_support(
    left: dict[str, Any],
    right: dict[str, Any],
) -> tuple[int, list[str]]:
    score = 0
    signals: list[str] = []
    left_name = left["name_forms"]
    right_name = right["name_forms"]
    left_keywords = left["keyword_forms"]
    right_keywords = right["keyword_forms"]

    if left_name & right_name:
        score += 90
        signals.append("name_or_abbreviation_match")
    if (
        left_name & right_keywords
        or right_name & left_keywords
    ):
        score += 75
        signals.append("name_keyword_match")
    if left_keywords & right_keywords:
        score += 45
        signals.append("keyword_match")

    left_normalized = _normalized(left["name"])
    right_normalized = _normalized(right["name"])
    if (
        min(
            len(left_normalized),
            len(right_normalized),
        ) >= 4
        and (
            left_normalized in right_normalized
            or right_normalized in left_normalized
        )
    ):
        score += 45
        signals.append("name_containment")

    shared_evidence = (
        left["evidence_ids"]
        & right["evidence_ids"]
    )
    if shared_evidence:
        score += 35
        signals.append("shared_paper_evidence")

    union = left["tokens"] | right["tokens"]
    overlap = left["tokens"] & right["tokens"]
    token_ratio = (
        len(overlap) / len(union)
        if union
        else 0.0
    )
    if token_ratio >= 0.6:
        score += 60
        signals.append("strong_token_overlap")
    elif token_ratio >= 0.4:
        score += 30
        signals.append("token_overlap")

    return score, signals


def _module_id(
    index: int,
    module: dict[str, Any],
) -> str:
    material = "|".join(
        [
            str(index),
            _normalized(module.get("name")),
            _normalized(module.get("description")),
        ]
    )
    digest = hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()[:16]
    return f"alias_module_{digest}"


def _compact_module(
    module_id: str,
    module: dict[str, Any],
) -> dict[str, Any]:
    evidence = [
        {
            "evidence_id": item.get("evidence_id"),
            "quote_or_summary": _clean(
                item.get("quote_or_summary")
            )[:220],
        }
        for item in module.get("evidence") or []
        if isinstance(item, dict)
    ][:2]
    return {
        "module_id": module_id,
        "name": _clean(module.get("name")),
        "description": _clean(
            module.get("description")
        )[:320],
        "possible_keywords": _unique_text(
            list(
                module.get("possible_keywords")
                or []
            )
        )[:8],
        "evidence": evidence,
    }


def build_alias_candidate_groups(
    modules: list[dict[str, Any]],
    *,
    max_groups: int = 8,
    max_group_modules: int = 5,
) -> AliasCandidateBuildResult:
    indexed = [
        {
            "module_id": _module_id(index, module),
            "module": dict(module),
            "signature": _module_signature(module),
        }
        for index, module in enumerate(modules)
        if isinstance(module, dict)
        and _clean(module.get("name"))
    ]
    supports: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}
    blocked: list[dict[str, Any]] = []

    for left, right in itertools.combinations(
        indexed,
        2,
    ):
        score, signals = _pair_support(
            left["signature"],
            right["signature"],
        )
        if score < _PAIR_SCORE_THRESHOLD:
            continue
        conflicts = alias_conflicts(
            left["signature"]["name"],
            right["signature"]["name"],
        )
        pair_key = tuple(
            sorted(
                [
                    left["module_id"],
                    right["module_id"],
                ]
            )
        )
        support = {
            "left_id": pair_key[0],
            "right_id": pair_key[1],
            "score": score,
            "signals": signals,
        }
        if conflicts:
            blocked.append(
                {
                    **support,
                    "conflicts": conflicts,
                }
            )
            continue
        supports[pair_key] = support

    by_id = {
        item["module_id"]: item
        for item in indexed
    }
    # 使用 complete-linkage 贪心聚类，避免 A-B、A-C 两条弱边把彼此
    # 无支持的 B/C 串成一个大组。每个模块只进入一个候选组。
    clusters: list[set[str]] = []
    cluster_by_module: dict[str, int] = {}
    ranked_pairs = sorted(
        supports.items(),
        key=lambda item: (
            -item[1]["score"],
            item[0],
        ),
    )

    def fully_supported(values: set[str]) -> bool:
        return all(
            tuple(sorted([left, right])) in supports
            for left, right in itertools.combinations(
                values,
                2,
            )
        )

    for pair, _support in ranked_pairs:
        left_id, right_id = pair
        left_cluster = cluster_by_module.get(left_id)
        right_cluster = cluster_by_module.get(right_id)
        if left_cluster is None and right_cluster is None:
            cluster_index = len(clusters)
            clusters.append({left_id, right_id})
            cluster_by_module[left_id] = cluster_index
            cluster_by_module[right_id] = cluster_index
            continue
        if left_cluster == right_cluster:
            continue

        if left_cluster is None or right_cluster is None:
            cluster_index = (
                right_cluster
                if left_cluster is None
                else left_cluster
            )
            assert cluster_index is not None
            new_id = (
                left_id
                if left_cluster is None
                else right_id
            )
            proposed = {
                *clusters[cluster_index],
                new_id,
            }
            if (
                len(proposed) <= max_group_modules
                and fully_supported(proposed)
            ):
                clusters[cluster_index] = proposed
                cluster_by_module[new_id] = cluster_index
            continue

        proposed = {
            *clusters[left_cluster],
            *clusters[right_cluster],
        }
        if (
            len(proposed) > max_group_modules
            or not fully_supported(proposed)
        ):
            continue
        clusters[left_cluster] = proposed
        clusters[right_cluster] = set()
        for module_id in proposed:
            cluster_by_module[module_id] = left_cluster

    ranked_components = sorted(
        [cluster for cluster in clusters if len(cluster) >= 2],
        key=lambda component: (
            -max(
                support["score"]
                for pair, support in supports.items()
                if set(pair) <= component
            ),
            sorted(component),
        ),
    )[:max_groups]

    groups: list[dict[str, Any]] = []
    for component in ranked_components:
        ranked_ids = sorted(
            component,
            key=lambda module_id: (
                -sum(
                    support["score"]
                    for pair, support in supports.items()
                    if module_id in pair
                    and set(pair) <= component
                ),
                by_id[module_id]["signature"]["name"],
            ),
        )[:max_group_modules]
        group_material = "|".join(sorted(ranked_ids))
        group_id = "alias_group_" + hashlib.sha256(
            group_material.encode("utf-8")
        ).hexdigest()[:16]
        group_support = [
            support
            for pair, support in supports.items()
            if set(pair) <= set(ranked_ids)
        ]
        groups.append(
            {
                "group_id": group_id,
                "modules": [
                    _compact_module(
                        module_id,
                        by_id[module_id]["module"],
                    )
                    for module_id in ranked_ids
                ],
                "pair_support": sorted(
                    group_support,
                    key=lambda item: (
                        -item["score"],
                        item["left_id"],
                        item["right_id"],
                    ),
                ),
            }
        )

    return AliasCandidateBuildResult(
        indexed_modules=indexed,
        groups=groups,
        blocked_pairs=blocked,
    )


def _canonical_name_score(
    name: str,
    llm_name: str | None,
) -> tuple[int, int, str]:
    normalized = _normalized(name)
    words = _identifier_words(name)
    score = min(len(name), 50) + len(words) * 8
    if any(character.isspace() for character in name):
        score += 20
    if (
        len(normalized) <= 10
        and not any(character.isspace() for character in name)
    ):
        score -= 15
    if any(
        _normalized(marker) in normalized
        for marker in _DETAIL_NAME_MARKERS
    ):
        score -= 25
    if llm_name and normalized == _normalized(llm_name):
        score += 15
    return score, len(name), name


def _validated_canonical_name(
    modules: list[dict[str, Any]],
    llm_name: str | None,
) -> str:
    names = _unique_text(
        [module.get("name") for module in modules]
    )
    if not names:
        return "unnamed method"
    return max(
        names,
        key=lambda name: _canonical_name_score(
            name,
            llm_name,
        ),
    )


def validate_and_apply_alias_decisions(
    candidate_result: AliasCandidateBuildResult,
    response: MappingAliasBatchDecision | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    indexed_by_id = {
        item["module_id"]: item
        for item in candidate_result.indexed_modules
    }
    groups_by_id = {
        group["group_id"]: group
        for group in candidate_result.groups
    }
    raw_decisions = (
        response.decisions
        if response is not None
        else []
    )
    decisions_by_group = {
        decision.group_id: decision
        for decision in raw_decisions
        if decision.group_id in groups_by_id
    }
    records: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    used_module_ids: set[str] = set()

    for group_id, group in groups_by_id.items():
        decision = decisions_by_group.get(group_id)
        if decision is None:
            records.append(
                {
                    "group_id": group_id,
                    "status": "not_returned",
                    "accepted": False,
                }
            )
            continue
        base_record = {
            **decision.model_dump(mode="json"),
            "accepted": False,
        }
        if not decision.should_merge:
            records.append(
                {
                    **base_record,
                    "status": "kept_separate",
                }
            )
            continue
        if decision.confidence != "high":
            records.append(
                {
                    **base_record,
                    "status": "confidence_too_low",
                }
            )
            continue

        allowed_ids = {
            module["module_id"]
            for module in group["modules"]
        }
        member_ids = list(
            dict.fromkeys(decision.member_ids)
        )
        if (
            len(member_ids) < 2
            or not set(member_ids) <= allowed_ids
        ):
            records.append(
                {
                    **base_record,
                    "status": "invalid_member_ids",
                }
            )
            continue
        if set(member_ids) & used_module_ids:
            records.append(
                {
                    **base_record,
                    "status": "overlapping_group",
                }
            )
            continue

        support_by_pair = {
            tuple(
                sorted(
                    [
                        support["left_id"],
                        support["right_id"],
                    ]
                )
            ): support
            for support in group["pair_support"]
        }
        insufficient_pairs: list[list[str]] = []
        conflicts: list[str] = []
        for left_id, right_id in itertools.combinations(
            member_ids,
            2,
        ):
            support = support_by_pair.get(
                tuple(sorted([left_id, right_id]))
            )
            if (
                support is None
                or support["score"]
                < _PAIR_SCORE_THRESHOLD
            ):
                insufficient_pairs.append(
                    [left_id, right_id]
                )
            conflicts.extend(
                alias_conflicts(
                    indexed_by_id[left_id]["module"].get(
                        "name", ""
                    ),
                    indexed_by_id[right_id]["module"].get(
                        "name", ""
                    ),
                )
            )
        if insufficient_pairs or conflicts:
            records.append(
                {
                    **base_record,
                    "status": (
                        "hard_conflict"
                        if conflicts
                        else "insufficient_pair_support"
                    ),
                    "program_conflicts": _unique_text(
                        conflicts
                    ),
                    "insufficient_pairs": (
                        insufficient_pairs
                    ),
                }
            )
            continue

        member_modules = [
            indexed_by_id[module_id]["module"]
            for module_id in member_ids
        ]
        canonical_module = indexed_by_id.get(
            decision.canonical_member_id or ""
        )
        llm_canonical_name = (
            canonical_module["module"].get("name")
            if canonical_module is not None
            and decision.canonical_member_id in member_ids
            else None
        )
        canonical_name = _validated_canonical_name(
            member_modules,
            llm_canonical_name,
        )
        member_names = _unique_text(
            [
                module.get("name")
                for module in member_modules
            ]
        )
        member_name_forms = {
            form
            for name in member_names
            for form in _forms(name)
        }
        allowed_alias_values = _unique_text(
            [
                *member_names,
                *[
                    keyword
                    for module in member_modules
                    for keyword in (
                        module.get("possible_keywords")
                        or []
                    )
                    if _forms(keyword)
                    & member_name_forms
                ],
            ]
        )
        aliases = _unique_text(
            [
                *member_names,
                *allowed_alias_values,
            ]
        )
        aliases = [
            alias
            for alias in aliases
            if _normalized(alias)
            != _normalized(canonical_name)
        ]
        cluster_key = f"llm-alias:{group_id}"
        accepted_item = {
            "group_id": group_id,
            "member_ids": member_ids,
            "canonical_name": canonical_name,
            "aliases": aliases,
            "cluster_key": cluster_key,
        }
        accepted.append(accepted_item)
        used_module_ids.update(member_ids)
        records.append(
            {
                **base_record,
                **accepted_item,
                "status": "merged",
                "accepted": True,
            }
        )

    annotations = {
        module_id: accepted_item
        for accepted_item in accepted
        for module_id in accepted_item["member_ids"]
    }
    prepared_modules: list[dict[str, Any]] = []
    for item in candidate_result.indexed_modules:
        module = dict(item["module"])
        annotation = annotations.get(item["module_id"])
        if annotation is not None:
            module[ALIAS_CLUSTER_KEY_FIELD] = (
                annotation["cluster_key"]
            )
            module[ALIAS_CANONICAL_NAME_FIELD] = (
                annotation["canonical_name"]
            )
            module[ALIAS_NAMES_FIELD] = list(
                annotation["aliases"]
            )
        prepared_modules.append(module)
    return prepared_modules, records
