from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas import (
    CodeMappingTarget,
    CodeMappingTargetCategory,
    Evidence,
)

MAPPING_TARGET_POLICY_VERSION = "phase23.5-v2"

_CATEGORY_ORDER: tuple[
    CodeMappingTargetCategory,
    ...,
] = (
    "core_method",
    "data_pipeline",
    "training_config",
    "evaluation_metric",
    "ablation_switch",
)

_ABLATION_MARKERS = (
    "ablation",
    "baseline",
    "variant",
    "without",
    "w/o",
    "non-decomposing",
    "remove",
    "消融",
    "基线",
    "变体",
    "非解耦",
    "去除",
    "不使用",
)


@dataclass(frozen=True)
class MappingAliasRule:
    canonical_key: str
    aliases: tuple[str, ...] = ()
    match_any: tuple[str, ...] = ()
    match_all: tuple[str, ...] = ()
    exclude_any: tuple[str, ...] = ()


@dataclass(frozen=True)
class MappingTargetBuildResult:
    targets: list[CodeMappingTarget]
    dropped: list[dict[str, str]]
    source_counts: dict[str, int]
    limits: dict[str, int]

    def artifact_payload(self) -> dict[str, Any]:
        return {
            "policy_version": (
                MAPPING_TARGET_POLICY_VERSION
            ),
            "source_counts": self.source_counts,
            "limits": self.limits,
            "selected_count": len(self.targets),
            "targets": [
                target.model_dump(mode="json")
                for target in self.targets
            ],
            "dropped": self.dropped,
        }


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalized(value: Any) -> str:
    text = unicodedata.normalize(
        "NFKC",
        _clean(value),
    ).casefold()
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text)


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


def _target_id(
    category: CodeMappingTargetCategory,
    canonical_key: str,
) -> str:
    digest = hashlib.sha256(
        f"{category}|{canonical_key}".encode()
    ).hexdigest()[:16]
    return f"mapping_target_{digest}"


def _normalized_terms(
    values: tuple[str, ...] | list[str],
) -> list[str]:
    return [
        term
        for term in (
            _normalized(value)
            for value in values
        )
        if term
    ]


def _alias_rule_matches(
    rule: MappingAliasRule,
    value: str,
) -> bool:
    normalized = _normalized(value)
    if not normalized:
        return False

    excluded_terms = _normalized_terms(
        rule.exclude_any
    )
    if any(term in normalized for term in excluded_terms):
        return False

    alias_terms = _normalized_terms(rule.aliases)
    if any(
        normalized == term
        or term in normalized
        or normalized in term
        for term in alias_terms
    ):
        return True

    all_terms = _normalized_terms(rule.match_all)
    if all_terms and not all(
        term in normalized
        for term in all_terms
    ):
        return False

    any_terms = _normalized_terms(rule.match_any)
    if any_terms:
        return any(
            term in normalized
            for term in any_terms
        )

    return bool(all_terms)


def _alias_rule_key(
    values: list[Any],
    alias_rules: list[MappingAliasRule],
) -> str | None:
    for value in values:
        cleaned = _clean(value)
        if not cleaned:
            continue
        for rule in alias_rules:
            if _alias_rule_matches(rule, cleaned):
                return _normalized(
                    rule.canonical_key
                )
    return None


def _parenthetical_acronym_key(
    value: str,
) -> str | None:
    """
    通用处理 "Long Name (ABC) Block" 与 "ABC Block" 这类同义写法。

    这里不写任何领域词，只把括号中的短缩写替换到原位置，避免
    PointNet、Transformer、CNN 等论文都需要各自硬编码。
    """

    name = _clean(value)
    if not name:
        return None

    matches = list(
        re.finditer(
            r"[\(（]([A-Za-z][A-Za-z0-9_-]{1,12})[\)）]",
            name,
        )
    )
    if not matches:
        return None

    key = name
    for match in reversed(matches):
        acronym = match.group(1)
        prefix = key[: match.start()]
        words = list(
            re.finditer(
                r"[A-Za-z][A-Za-z0-9]*",
                prefix,
            )
        )
        acronym_letters = re.sub(
            r"[^A-Za-z0-9]",
            "",
            acronym,
        ).casefold()
        phrase_start = match.start()
        if (
            acronym_letters
            and len(words) >= len(acronym_letters)
        ):
            candidate_words = words[
                -len(acronym_letters) :
            ]
            candidate_letters = "".join(
                word.group(0)[0]
                for word in candidate_words
            ).casefold()
            if candidate_letters == acronym_letters:
                phrase_start = (
                    candidate_words[0].start()
                )

        key = (
            key[:phrase_start]
            + acronym
            + key[match.end() :]
        )

    normalized = _normalized(key)
    return normalized or None


def _method_key(
    module: dict[str, Any],
    *,
    alias_rules: list[MappingAliasRule],
) -> str:
    name = _clean(module.get("name"))
    rule_key = _alias_rule_key(
        [
            name,
            module.get("description"),
            *list(
                module.get(
                    "possible_keywords"
                )
                or []
            ),
        ],
        alias_rules,
    )
    if rule_key:
        return rule_key

    acronym_key = _parenthetical_acronym_key(name)
    if acronym_key:
        return acronym_key

    # 中英文括号中的全称常用于表达同一模块的别名。
    for inner in re.findall(
        r"[\(（]([^\)）]+)[\)）]",
        name,
    ):
        rule_key = _alias_rule_key(
            [inner],
            alias_rules,
        )
        if rule_key:
            return rule_key

    return _normalized(name) or "unnamed-method"


def _string_tuple(
    payload: dict[str, Any],
    key: str,
) -> tuple[str, ...]:
    value = payload.get(key, [])
    if value is None:
        return ()
    if not isinstance(value, list):
        raise TypeError(
            f"mapping alias rule {key!r} must be a list"
        )
    return tuple(
        _clean(item)
        for item in value
        if _clean(item)
    )


def load_mapping_alias_rules(
    path: str | Path | None,
) -> list[MappingAliasRule]:
    """
    从可选 JSON 文件读取论文/领域别名规则。

    文件不存在时返回空规则，确保新论文默认走通用逻辑。
    """

    if path is None:
        return []

    resolved = Path(path)
    if not resolved.exists():
        return []

    try:
        payload = json.loads(
            resolved.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid mapping alias JSON: {resolved}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise TypeError(
            "mapping alias file must contain a JSON object"
        )

    rules_payload = payload.get("rules")
    if not isinstance(rules_payload, list):
        raise TypeError(
            "mapping alias file must contain a list field named 'rules'"
        )

    rules: list[MappingAliasRule] = []
    for index, item in enumerate(rules_payload):
        if not isinstance(item, dict):
            raise TypeError(
                f"mapping alias rule #{index} must be an object"
            )
        canonical_key = _clean(
            item.get("canonical_key")
        )
        if not canonical_key:
            raise ValueError(
                f"mapping alias rule #{index} missing canonical_key"
            )
        rules.append(
            MappingAliasRule(
                canonical_key=canonical_key,
                aliases=_string_tuple(
                    item,
                    "aliases",
                ),
                match_any=_string_tuple(
                    item,
                    "match_any",
                ),
                match_all=_string_tuple(
                    item,
                    "match_all",
                ),
                exclude_any=_string_tuple(
                    item,
                    "exclude_any",
                ),
            )
        )
    return rules


def _evidence_key(evidence: Evidence) -> str:
    return (
        evidence.evidence_id
        or evidence.content_hash
        or (
            f"{evidence.source_type}|"
            f"{evidence.source_path}|"
            f"{evidence.location or ''}|"
            f"{evidence.quote_or_summary}"
        )
    )


def _merge_evidence(
    modules: list[dict[str, Any]],
) -> list[Evidence]:
    output: list[Evidence] = []
    seen: set[str] = set()
    for module in modules:
        for payload in module.get("evidence") or []:
            try:
                evidence = Evidence.model_validate(
                    payload
                )
            except (TypeError, ValueError):
                continue
            key = _evidence_key(evidence)
            if key in seen:
                continue
            seen.add(key)
            output.append(evidence)
    return output


def _source_evidence_ids(
    evidence: list[Evidence],
) -> list[str]:
    return [
        value
        for value in dict.fromkeys(
            item.evidence_id
            for item in evidence
            if item.evidence_id
        )
        if value
    ]


def _is_ablation_text(value: Any) -> bool:
    normalized = _clean(value).casefold()
    return any(
        marker in normalized
        for marker in _ABLATION_MARKERS
    )


def _method_targets(
    modules: list[dict[str, Any]],
    *,
    alias_rules: list[MappingAliasRule],
) -> tuple[
    list[CodeMappingTarget],
    list[dict[str, Any]],
]:
    groups: dict[str, list[dict[str, Any]]] = {}
    ablation_modules: list[dict[str, Any]] = []

    for module in modules:
        if not isinstance(module, dict):
            continue
        name = _clean(module.get("name"))
        description = _clean(
            module.get("description")
        )
        if not name:
            continue
        if _is_ablation_text(
            f"{name} {description}"
        ):
            ablation_modules.append(module)
            continue
        groups.setdefault(
            _method_key(
                module,
                alias_rules=alias_rules,
            ),
            [],
        ).append(module)

    targets: list[CodeMappingTarget] = []
    for canonical_key, group in groups.items():
        names = _unique_text(
            [
                module.get("name")
                for module in group
            ]
        )
        descriptions = _unique_text(
            [
                module.get("description")
                for module in group
            ]
        )
        keywords = _unique_text(
            [
                keyword
                for module in group
                for keyword in (
                    module.get(
                        "possible_keywords"
                    )
                    or []
                )
            ]
        )
        evidence = _merge_evidence(group)
        targets.append(
            CodeMappingTarget(
                target_id=_target_id(
                    "core_method",
                    canonical_key,
                ),
                category="core_method",
                name=names[0],
                description="；".join(
                    descriptions[:3]
                ),
                aliases=names[1:],
                possible_keywords=keywords,
                evidence=evidence,
                source_evidence_ids=(
                    _source_evidence_ids(
                        evidence
                    )
                ),
            )
        )
    return targets, ablation_modules


def _named_value(value: Any) -> str:
    if isinstance(value, dict):
        return _clean(
            value.get("name")
            or value.get("value")
        )
    return _clean(value)


def _named_targets(
    *,
    values: list[Any],
    category: CodeMappingTargetCategory,
    description_prefix: str,
    generic_keywords: list[str],
    prefer_specific_names: bool = False,
) -> list[CodeMappingTarget]:
    targets: list[CodeMappingTarget] = []
    seen: set[str] = set()
    indexed_values = list(enumerate(values))
    if prefer_specific_names:
        indexed_values.sort(
            key=lambda item: (
                _is_generic_collection_name(
                    _named_value(item[1])
                ),
                item[0],
            )
        )

    for _, value in indexed_values:
        name = _named_value(value)
        canonical_key = _normalized(name)
        if not canonical_key or canonical_key in seen:
            continue
        seen.add(canonical_key)
        targets.append(
            CodeMappingTarget(
                target_id=_target_id(
                    category,
                    canonical_key,
                ),
                category=category,
                name=name,
                description=(
                    f"{description_prefix}：{name}"
                ),
                possible_keywords=_unique_text(
                    [
                        name,
                        *generic_keywords,
                    ]
                ),
            )
        )
    return targets


def _is_generic_collection_name(value: str) -> bool:
    normalized = _clean(value).casefold()
    return normalized.startswith(
        (
            "widely-used ",
            "widely used ",
            "commonly-used ",
            "commonly used ",
        )
    )


def _setting_evidence(
    settings_payload: list[dict[str, Any]],
) -> list[Evidence]:
    return _merge_evidence(
        [
            {
                "evidence": (
                    setting.get("evidence")
                    or []
                )
            }
            for setting in settings_payload
        ]
    )


def _aggregate_setting_target(
    *,
    category: CodeMappingTargetCategory,
    name: str,
    settings_payload: list[dict[str, Any]],
    extra_descriptions: list[str],
    generic_keywords: list[str],
) -> CodeMappingTarget | None:
    parts = _unique_text(
        [
            *[
                (
                    f"{_clean(item.get('name'))}="
                    f"{_clean(item.get('value'))}"
                )
                for item in settings_payload
                if _clean(item.get("name"))
            ],
            *extra_descriptions,
        ]
    )
    if not parts:
        return None

    evidence = _setting_evidence(
        settings_payload
    )
    aliases = _unique_text(
        [
            item.get("name")
            for item in settings_payload
        ]
    )
    return CodeMappingTarget(
        target_id=_target_id(
            category,
            _normalized(name),
        ),
        category=category,
        name=name,
        description="；".join(parts[:12]),
        aliases=aliases,
        possible_keywords=_unique_text(
            [
                *aliases,
                *generic_keywords,
            ]
        ),
        evidence=evidence,
        source_evidence_ids=(
            _source_evidence_ids(evidence)
        ),
    )


def build_code_mapping_targets(
    *,
    paper_summary: dict[str, Any],
    method_modules: list[dict[str, Any]],
    max_targets: int,
    category_limits: dict[
        CodeMappingTargetCategory,
        int,
    ],
    alias_rules: list[MappingAliasRule] | None = None,
) -> MappingTargetBuildResult:
    """构造五类映射目标，并在任何 Provider 调用前执行预算限制。"""

    method_targets, ablation_modules = (
        _method_targets(
            method_modules,
            alias_rules=alias_rules or [],
        )
    )
    data_targets = _named_targets(
        values=list(
            paper_summary.get("datasets") or []
        ),
        category="data_pipeline",
        description_prefix="论文数据集与数据处理入口",
        generic_keywords=[
            "dataset",
            "dataloader",
            "data loader",
            "preprocess",
            "preprocessing",
        ],
        prefer_specific_names=True,
    )
    metric_targets = _named_targets(
        values=list(
            paper_summary.get("metrics") or []
        ),
        category="evaluation_metric",
        description_prefix="论文评估指标与评估实现",
        generic_keywords=[
            "metric",
            "evaluation",
            "evaluate",
            "accuracy",
        ],
    )

    settings_payload = [
        item
        for item in (
            paper_summary.get(
                "experiment_settings"
            )
            or []
        )
        if isinstance(item, dict)
    ]
    ablation_settings = [
        item
        for item in settings_payload
        if _is_ablation_text(
            f"{item.get('name')} "
            f"{item.get('value')}"
        )
    ]
    training_settings = [
        item
        for item in settings_payload
        if item not in ablation_settings
    ]

    training_target = _aggregate_setting_target(
        category="training_config",
        name="Training and optimization configuration",
        settings_payload=training_settings,
        extra_descriptions=[],
        generic_keywords=[
            "argparse",
            "config",
            "optimizer",
            "scheduler",
            "learning rate",
            "batch size",
            "epochs",
        ],
    )
    ablation_target = _aggregate_setting_target(
        category="ablation_switch",
        name="Ablation variants and switches",
        settings_payload=ablation_settings,
        extra_descriptions=[
            (
                f"{_clean(module.get('name'))}: "
                f"{_clean(module.get('description'))}"
            )
            for module in ablation_modules
        ],
        generic_keywords=[
            "ablation",
            "baseline",
            "variant",
            "flag",
            "config",
        ],
    )

    candidates: dict[
        CodeMappingTargetCategory,
        list[CodeMappingTarget],
    ] = {
        "core_method": method_targets,
        "data_pipeline": data_targets,
        "training_config": (
            [training_target]
            if training_target is not None
            else []
        ),
        "evaluation_metric": metric_targets,
        "ablation_switch": (
            [ablation_target]
            if ablation_target is not None
            else []
        ),
    }

    selected: list[CodeMappingTarget] = []
    dropped: list[dict[str, str]] = []
    for category in _CATEGORY_ORDER:
        limit = category_limits.get(
            category,
            0,
        )
        category_candidates = candidates[
            category
        ]
        selected.extend(
            category_candidates[:limit]
        )
        dropped.extend(
            {
                "category": category,
                "name": target.name,
                "reason": "category_budget_exceeded",
            }
            for target in category_candidates[
                limit:
            ]
        )

    if len(selected) > max_targets:
        dropped.extend(
            {
                "category": target.category,
                "name": target.name,
                "reason": "total_budget_exceeded",
            }
            for target in selected[
                max_targets:
            ]
        )
        selected = selected[:max_targets]

    limits = {
        "max_targets": max_targets,
        **{
            f"max_{category}": (
                category_limits.get(
                    category,
                    0,
                )
            )
            for category in _CATEGORY_ORDER
        },
    }
    return MappingTargetBuildResult(
        targets=selected,
        dropped=dropped,
        source_counts={
            category: len(candidates[category])
            for category in _CATEGORY_ORDER
        },
        limits=limits,
    )


def legacy_method_targets(
    modules: list[dict[str, Any]],
) -> list[CodeMappingTarget]:
    """为旧测试、旧 checkpoint 和独立节点调用保留兼容入口。"""

    targets, _ = _method_targets(
        modules,
        alias_rules=[],
    )
    return targets


def mapping_targets_from_state(
    state: dict[str, Any],
) -> list[CodeMappingTarget]:
    """读取新目标；无新字段时从旧 method_modules 确定性迁移。"""

    targets: list[CodeMappingTarget] = []
    for payload in (
        state.get("mapping_targets") or []
    ):
        try:
            targets.append(
                CodeMappingTarget.model_validate(
                    payload
                )
            )
        except (TypeError, ValueError):
            continue
    if targets:
        return targets

    return legacy_method_targets(
        list(
            state.get("method_modules")
            or []
        )
    )
