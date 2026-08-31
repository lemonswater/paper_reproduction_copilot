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

MAPPING_TARGET_POLICY_VERSION = "phase23.6-v2"

# mapping_alias_resolver_node 只在一次目标构造调用内附加这些字段，
# 不把内部聚类标记写回 paper_summary 或 method_modules Artifact。
_ALIAS_CLUSTER_KEY_FIELD = "_mapping_alias_cluster_key"
_ALIAS_CANONICAL_NAME_FIELD = "_mapping_alias_canonical_name"
_ALIAS_NAMES_FIELD = "_mapping_alias_names"

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

_NON_ACTIONABLE_METHOD_NAME_PATTERNS = (
    re.compile(r"(?:公式|方程)$"),
    re.compile(r"(?:符号|记号).*(?:定义|说明)$"),
    re.compile(r"(?:输入|输出).*(?:特征图?|张量|维度|尺寸|形状)$"),
    re.compile(r"(?:目的|动机|能力来源)$"),
    re.compile(
        r"^(?:integrate|integration).*(?:network|model)s?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^experimental[_ -]?evaluation$",
        re.IGNORECASE,
    ),
    re.compile(r"^(?:常用|默认).*(?:核|大小|尺寸)$"),
    re.compile(r"(?:formula|equation)$", re.IGNORECASE),
    re.compile(
        r"(?:symbol|notation).*(?:definition|description)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:input|output).*(?:feature|tensor|dimension|shape)s?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:purpose|motivation|capability source)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:common|commonly used|default).*(?:kernel|size)$",
        re.IGNORECASE,
    ),
)

_METHOD_ARCHITECTURE_MARKERS = (
    "architecture",
    "network",
    "model",
    "framework",
    "backbone",
    "autoencoder",
    "encoder",
    "decoder",
    "cnn",
    "transformer",
    "网络",
    "架构",
    "模型",
    "框架",
    "自编码器",
    "编码器",
    "解码器",
)

_METHOD_OPERATOR_MARKERS = (
    "operator",
    "module",
    "layer",
    "block",
    "convolution",
    "attention",
    "aggregation",
    "pooling",
    "sampling",
    "算子",
    "模块",
    "层",
    "块",
    "卷积",
    "注意力",
    "聚合",
    "池化",
    "采样",
)

_METHOD_COMPONENT_MARKERS = (
    "kernel",
    "function",
    "mechanism",
    "operation",
    "branch",
    "head",
    "核",
    "函数",
    "机制",
    "操作",
    "分支",
)

_ARCHITECTURE_HEADS = {
    "transformer": "Transformer",
    "transformers": "Transformer",
    "encoder": "Encoder",
    "encoders": "Encoder",
    "decoder": "Decoder",
    "decoders": "Decoder",
    "network": "Network",
    "networks": "Network",
    "net": "Net",
    "nets": "Net",
    "model": "Model",
    "models": "Model",
    "architecture": "Architecture",
    "architectures": "Architecture",
    "framework": "Framework",
    "frameworks": "Framework",
}

_ARCHITECTURE_COMPOSITE_HEADS = {
    "Transformer",
    "Encoder",
    "Decoder",
}

_ARCHITECTURE_LEADING_WORDS = {
    "a",
    "an",
    "the",
    "our",
    "proposed",
    "novel",
    "new",
}

_GENERIC_SECTION_NAMES = {
    "abstract",
    "introduction",
    "relatedwork",
    "background",
    "method",
    "methods",
    "experiments",
    "results",
    "conclusion",
    "references",
    "appendix",
}

_IDENTITY_DETAIL_MARKERS = (
    "input",
    "output",
    "featureupdate",
    "components",
    "component",
    "输入",
    "输出",
    "特征更新",
    "组件",
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


def _identifier_words(value: str) -> list[str]:
    """将连字符架构短语拆成可用于缩写的英文/数字词。"""

    return re.findall(
        r"[A-Za-z][A-Za-z0-9]*|\d+[A-Za-z]*",
        value.replace("-", " "),
    )


def _looks_like_short_identifier(value: str) -> bool:
    words = _identifier_words(value)
    if len(words) != 1:
        return False
    token = words[0]
    if not token[0].isalpha():
        return False
    if token.isupper():
        return len(token) <= 10 or any(
            character.isdigit()
            for character in token
        )
    return bool(
        re.fullmatch(r"[A-Z]{2,}[A-Za-z0-9]{1,15}", token)
        or re.search(r"[a-z][A-Z]|[A-Za-z]\d|\d[A-Za-z]", token)
    )


def _display_architecture_word(value: str) -> str:
    if re.fullmatch(r"\d+[A-Za-z]*", value):
        return value.upper()
    if value.isupper():
        return value.capitalize()
    return value[0].upper() + value[1:]


def _architecture_phrase_candidates(
    value: str,
) -> list[str]:
    """从无分隔符标题生成紧凑名和缩写名。"""

    words = _identifier_words(value)
    if not words:
        return []

    head_index = None
    canonical_head = None
    for index, word in enumerate(words):
        candidate = _ARCHITECTURE_HEADS.get(
            word.casefold()
        )
        if candidate is not None:
            head_index = index
            canonical_head = candidate
            break
    if head_index is None or canonical_head is None:
        return []

    modifiers = words[:head_index]
    while (
        modifiers
        and modifiers[0].casefold()
        in _ARCHITECTURE_LEADING_WORDS
    ):
        modifiers.pop(0)
    if not modifiers:
        return []

    # “PSTNET ARCHITECTURES”“PROPOSED MAPLE FRAMEWORK”中，架构词
    # 前的短标识已经是方法名，无需再次生成首字母缩写。
    immediate = modifiers[-1]
    if (
        canonical_head
        not in _ARCHITECTURE_COMPOSITE_HEADS
        and _looks_like_short_identifier(immediate)
    ):
        return [immediate]

    if canonical_head not in _ARCHITECTURE_COMPOSITE_HEADS:
        return []
    if len(modifiers) > 5:
        return []

    compact_parts: list[str] = []
    initial_parts: list[str] = []
    for word in modifiers:
        display = _display_architecture_word(word)
        compact_parts.append(display)
        dimension = re.fullmatch(
            r"(\d+)[dD]",
            word,
        )
        initial_parts.append(
            dimension.group(1)
            if dimension is not None
            else display[0].upper()
        )

    compact_name = "".join(
        [*compact_parts, canonical_head]
    )
    abbreviated_name = "".join(
        [*initial_parts, canonical_head]
    )
    if len(modifiers) == 1:
        return _unique_text(
            [compact_name, abbreviated_name]
        )
    return _unique_text(
        [abbreviated_name, compact_name]
    )


def _explicit_title_identifier(
    title: str,
) -> str | None:
    parts = re.split(
        r"\s*(?::|：|—|–|\|)\s*",
        title,
        maxsplit=1,
    )
    if len(parts) != 2:
        return None
    prefix = _clean(parts[0])
    if _looks_like_short_identifier(prefix):
        return prefix
    candidates = _architecture_phrase_candidates(prefix)
    return candidates[0] if candidates else None


def _architecture_identity_target(
    *,
    paper_summary: dict[str, Any],
    section_titles: list[str],
) -> CodeMappingTarget | None:
    """从确定性标题结构推导论文整体架构目标，不依赖 LLM 模块命名。"""

    title = _clean(paper_summary.get("title"))
    ranked: list[tuple[int, str, list[str]]] = []
    if title:
        explicit = _explicit_title_identifier(title)
        if explicit:
            ranked.append(
                (120, explicit, [title])
            )
        phrase_names = _architecture_phrase_candidates(
            title
        )
        for offset, name in enumerate(phrase_names):
            ranked.append(
                (
                    100 - offset,
                    name,
                    [title, *phrase_names],
                )
            )

    for raw_title in section_titles:
        section_title = _clean(raw_title)
        if (
            not section_title
            or _normalized(section_title)
            in _GENERIC_SECTION_NAMES
        ):
            continue
        phrase_names = _architecture_phrase_candidates(
            section_title
        )
        for offset, name in enumerate(phrase_names):
            ranked.append(
                (
                    90 - offset,
                    name,
                    [section_title, *phrase_names],
                )
            )

    if not ranked:
        return None

    grouped: dict[str, dict[str, Any]] = {}
    for score, name, aliases in ranked:
        key = _normalized(name)
        if not key:
            continue
        item = grouped.setdefault(
            key,
            {
                "score": score,
                "name": name,
                "aliases": [],
            },
        )
        item["score"] = max(item["score"], score)
        item["aliases"] = _unique_text(
            [*item["aliases"], *aliases]
        )
    if not grouped:
        return None

    selected = max(
        grouped.values(),
        key=lambda item: item["score"],
    )
    name = selected["name"]
    aliases = _unique_text(
        [
            *selected["aliases"],
            f"{name} architecture",
        ]
    )
    aliases = [
        alias
        for alias in aliases
        if _normalized(alias) != _normalized(name)
    ]
    autoencoder_keywords: list[str] = []
    if re.search(
        r"auto\s*encoder|自编码器",
        title,
        flags=re.IGNORECASE,
    ):
        autoencoder_keywords = [
            "autoencoder",
            "auto_encoder",
            "masked autoencoder",
            "mae",
        ]
    return CodeMappingTarget(
        target_id=_target_id(
            "core_method",
            _normalized(name),
        ),
        category="core_method",
        name=name,
        description=(
            f"论文整体网络架构：{title or name}"
        ),
        aliases=aliases,
        possible_keywords=_unique_text(
            [
                name,
                *aliases,
                "architecture",
                "network",
                "model",
                "classifier",
                *autoencoder_keywords,
            ]
        ),
    )


def _architecture_keys_match(
    identity_keys: set[str],
    target_keys: set[str],
) -> bool:
    identity_keys = {
        key.replace("_", "")
        for key in identity_keys
    }
    target_keys = {
        key.replace("_", "")
        for key in target_keys
    }
    if identity_keys & target_keys:
        return True

    for identity_key in identity_keys:
        for target_key in target_keys:
            if not identity_key or not target_key:
                continue
            # “Point Spatio-Temporal Transformer Networks”与
            # point_spatio_temporal_transformer 是同一个架构名。
            if (
                target_key.endswith("transformer")
                and len(target_key) >= 12
                and target_key in identity_key
            ):
                return True
            # “PST-Transformer输入/组件”等是架构说明，不应各占一个
            # core_method 预算；把关键词合入主架构目标即可。
            if (
                identity_key in target_key
                and any(
                    marker in target_key
                    for marker in _IDENTITY_DETAIL_MARKERS
                )
            ):
                return True
    return False


def _merge_architecture_identity(
    method_targets: list[CodeMappingTarget],
    identity: CodeMappingTarget | None,
) -> list[CodeMappingTarget]:
    if identity is None:
        return method_targets

    identity_keys = {
        _normalized(identity.name),
        *(
            _normalized(alias)
            for alias in identity.aliases
        ),
    }
    merged_identity = identity
    remaining: list[CodeMappingTarget] = []
    matched = False
    for target in method_targets:
        target_keys = {
            _normalized(target.name),
            *(
                _normalized(alias)
                for alias in target.aliases
            ),
        }
        if not _architecture_keys_match(
            identity_keys,
            target_keys,
        ):
            remaining.append(target)
            continue

        matched = True
        merged_identity = merged_identity.model_copy(
            update={
                "description": "；".join(
                    _unique_text(
                        [
                            target.description,
                            merged_identity.description,
                        ]
                    )[:3]
                ),
                "aliases": _unique_text(
                    [
                        *target.aliases,
                        target.name,
                        merged_identity.name,
                        *merged_identity.aliases,
                    ]
                ),
                "possible_keywords": _unique_text(
                    [
                        *target.possible_keywords,
                        *merged_identity.possible_keywords,
                    ]
                ),
                "evidence": [
                    *target.evidence,
                    *merged_identity.evidence,
                ],
                "source_evidence_ids": _unique_text(
                    [
                        *target.source_evidence_ids,
                        *merged_identity.source_evidence_ids,
                    ]
                ),
            }
        )
    merged_identity = merged_identity.model_copy(
        update={
            "aliases": [
                alias
                for alias in merged_identity.aliases
                if _normalized(alias)
                != _normalized(merged_identity.name)
            ]
        }
    )
    remaining.sort(
        key=_method_target_priority,
        reverse=True,
    )
    return [
        merged_identity if matched else identity,
        *remaining,
    ]


def _summary_component_modules(
    paper_summary: dict[str, Any],
    method_modules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """从规约结果的全部语义字段补回被遗漏的具名核心算子。"""

    values = [
        _clean(paper_summary.get("title")),
        _clean(paper_summary.get("core_idea")),
    ]
    for setting in (
        paper_summary.get("experiment_settings")
        or []
    ):
        if not isinstance(setting, dict):
            continue
        evidence_text = [
            _clean(
                evidence.get("quote_or_summary")
                or evidence.get("summary")
            )
            for evidence in setting.get("evidence") or []
            if isinstance(evidence, dict)
        ]
        values.append(
            " ".join(
                [
                    _clean(setting.get("name")),
                    _clean(setting.get("value")),
                    *evidence_text,
                ]
            )
        )
    for module in method_modules:
        if not isinstance(module, dict):
            continue
        module_evidence_text = [
            _clean(
                evidence.get("quote_or_summary")
                or evidence.get("summary")
            )
            for evidence in module.get("evidence") or []
            if isinstance(evidence, dict)
        ]
        values.append(
            " ".join(
                [
                    _clean(module.get("name")),
                    _clean(module.get("description")),
                    *[
                        _clean(keyword)
                        for keyword in (
                            module.get("possible_keywords")
                            or []
                        )
                    ],
                    *module_evidence_text,
                ]
            )
        )
    material = " ".join(values)
    modules: list[dict[str, Any]] = []

    if re.search(
        r"(?<![A-Za-z0-9])P4D?Conv(?![A-Za-z0-9])|"
        r"Point\s*4D\s*Convolution|4D\s*卷积",
        material,
        flags=re.IGNORECASE,
    ):
        modules.append(
            {
                "name": "Point 4D Convolution",
                "description": "论文实验或架构描述中明确出现的四维点卷积算子。",
                "possible_keywords": [
                    "P4Conv",
                    "P4DConv",
                    "4D convolution",
                    "point_4d_convolution",
                ],
                _ALIAS_NAMES_FIELD: [
                    "P4Conv",
                    "P4DConv",
                ],
            }
        )

    if re.search(
        r"masked(?:\s+pseudo[- ]labeling)?\s+auto\s*encoder|"
        r"掩码[^。；,，]{0,20}自编码器",
        material,
        flags=re.IGNORECASE,
    ):
        modules.append(
            {
                "name": "masked autoencoder",
                "description": "论文方法中用于掩码特征重建的自编码器分支。",
                "possible_keywords": [
                    "masked autoencoder",
                    "mask embedding",
                    "autoencoder",
                    "mae",
                    "msr_mae",
                ],
            }
        )
    return modules


def prepare_mapping_method_modules(
    *,
    paper_summary: dict[str, Any],
    method_modules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """返回预算截断前参与别名解析的完整核心方法事实。"""

    prepared = [
        dict(module)
        for module in method_modules
        if isinstance(module, dict)
    ]
    return [
        *prepared,
        *_summary_component_modules(
            paper_summary,
            prepared,
        ),
    ]


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
    alias_cluster_key = _clean(
        module.get(_ALIAS_CLUSTER_KEY_FIELD)
    )
    if alias_cluster_key:
        return _normalized(alias_cluster_key)

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


def _is_non_actionable_method_fact(name: str) -> bool:
    """识别公式、符号和输入维度等不能独立映射到实现的说明性事实。"""

    cleaned = _clean(name)
    return any(
        pattern.search(cleaned)
        for pattern in _NON_ACTIONABLE_METHOD_NAME_PATTERNS
    )


def _contains_marker(
    value: str,
    markers: tuple[str, ...],
) -> bool:
    normalized = value.casefold()
    return any(
        marker.casefold() in normalized
        for marker in markers
    )


def _method_target_priority(
    target: CodeMappingTarget,
) -> int:
    """优先保留具名架构、网络和算子，再保留内部实现组件。"""

    name = _clean(target.name)
    name_material = " ".join(
        [
            name,
            *target.aliases,
        ]
    )
    score = 0

    # 论文方法名通常含缩写、数字或 CamelCase，例如 TA、P4D、PSTNet。
    if re.search(
        r"(?:\b[A-Z]{2,}[A-Za-z0-9_-]*\b|"
        r"\b[A-Za-z]+\d+[A-Za-z0-9_-]*\b)",
        name_material,
    ):
        score += 40
    if _contains_marker(
        name_material,
        _METHOD_ARCHITECTURE_MARKERS,
    ):
        score += 30
    if _contains_marker(
        name,
        _METHOD_OPERATOR_MARKERS,
    ):
        score += 20
    if _contains_marker(
        name,
        _METHOD_COMPONENT_MARKERS,
    ):
        score += 10
    return score


def _method_targets(
    modules: list[dict[str, Any]],
    *,
    alias_rules: list[MappingAliasRule],
) -> tuple[
    list[CodeMappingTarget],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    groups: dict[str, list[dict[str, Any]]] = {}
    ablation_modules: list[dict[str, Any]] = []
    non_actionable_modules: list[dict[str, Any]] = []

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
        if _is_non_actionable_method_fact(name):
            non_actionable_modules.append(module)
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
                *[
                    module.get(
                        _ALIAS_CANONICAL_NAME_FIELD
                    )
                    for module in group
                ],
                *[
                    module.get("name")
                    for module in group
                ],
            ]
        )
        configured_aliases = _unique_text(
            [
                alias
                for module in group
                for alias in (
                    module.get(_ALIAS_NAMES_FIELD)
                    or []
                )
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
                aliases=[
                    alias
                    for alias in _unique_text(
                        [
                            *names[1:],
                            *configured_aliases,
                        ]
                    )
                    if _normalized(alias)
                    != _normalized(names[0])
                ],
                possible_keywords=_unique_text(
                    [
                        *keywords,
                        *configured_aliases,
                    ]
                ),
                evidence=evidence,
                source_evidence_ids=(
                    _source_evidence_ids(
                        evidence
                    )
                ),
            )
        )
    targets.sort(
        key=_method_target_priority,
        reverse=True,
    )
    return (
        targets,
        ablation_modules,
        non_actionable_modules,
    )


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
    section_titles: list[str] | None = None,
    max_targets: int,
    category_limits: dict[
        CodeMappingTargetCategory,
        int,
    ],
    alias_rules: list[MappingAliasRule] | None = None,
    include_summary_components: bool = True,
) -> MappingTargetBuildResult:
    """构造五类映射目标，并在任何 Provider 调用前执行预算限制。"""

    (
        method_targets,
        ablation_modules,
        non_actionable_modules,
    ) = (
        _method_targets(
            (
                prepare_mapping_method_modules(
                    paper_summary=paper_summary,
                    method_modules=method_modules,
                )
                if include_summary_components
                else method_modules
            ),
            alias_rules=alias_rules or [],
        )
    )
    method_targets = _merge_architecture_identity(
        method_targets,
        _architecture_identity_target(
            paper_summary=paper_summary,
            section_titles=section_titles or [],
        ),
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
    dropped: list[dict[str, str]] = [
        {
            "category": "core_method",
            "name": _clean(module.get("name")),
            "reason": "non_actionable_method_fact",
        }
        for module in non_actionable_modules
    ]
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

    targets, _, _ = _method_targets(
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
