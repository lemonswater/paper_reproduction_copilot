from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.retrieval.policy_schemas import (
    RetrievalDecision,
    RetrievalPolicyConfig,
    RetrievalPolicyMode,
    RetrievalProfile,
    RetrievalQueryFeatures,
)

MAX_POLICY_BYTES = 256 * 1024
FEATURE_VERSION = "phase47-v1"

_ERROR_PATTERN = re.compile(
    r"(?:\b[A-Z][A-Z0-9_]{3,}\b|"
    r"\b[A-Za-z]+(?:Error|Exception)\b|"
    r"(?i:undefined symbol|no such file|exit code|traceback))"
)
_PATH_PATTERN = re.compile(
    r"(?:^|\s)(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"
)
_SYMBOL_PATTERN = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_]*|"
    r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)$"
)


def canonical_json(value: Any) -> str:
    """生成稳定 JSON；Hash 身份不能依赖字典插入顺序。"""

    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_value(value: Any) -> str:
    """返回领域对象的 SHA-256 内容身份，不返回或隐藏原文。"""

    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def load_retrieval_policy(path: str | Path) -> RetrievalPolicyConfig:
    """从有界本地 JSON 加载 Policy，并由 Pydantic 拒绝未知字段。"""

    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"Retrieval Policy 不存在：{candidate}")
    if candidate.stat().st_size > MAX_POLICY_BYTES:
        raise ValueError("Retrieval Policy 文件过大")

    payload = json.loads(candidate.read_text(encoding="utf-8"))
    return RetrievalPolicyConfig.model_validate(payload)


def profile_by_id(
    policy: RetrievalPolicyConfig,
    profile_id: str,
) -> RetrievalProfile:
    """按稳定 ID 查询 profile；不存在时失败，不静默使用相似名称。"""

    for profile in policy.profiles:
        if profile.profile_id == profile_id:
            return profile
    raise KeyError(f"未知 retrieval profile：{profile_id}")


def _normalized_values(query: str, keywords: list[str]) -> list[str]:
    output: list[str] = []
    for raw in [query, *keywords]:
        normalized = " ".join(str(raw or "").split())
        if normalized and normalized not in output:
            output.append(normalized)
    return output


def build_query_features(
    *,
    query: str,
    keywords: list[str],
    preferred_paths: list[str] | None = None,
    paper_evidence_count: int = 0,
) -> RetrievalQueryFeatures:
    """
    只用确定性规则提取特征。

    query/keywords 是待检索文本；返回值只保存 query_sha256 和布尔/计数，
    不把潜在敏感 query 复制到 Decision Artifact。
    """

    values = _normalized_values(query, keywords)
    combined = "\n".join(values)
    tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", combined)
    paths = [
        " ".join(str(value or "").split())
        for value in (preferred_paths or [])
        if str(value or "").strip()
    ]

    has_error = bool(_ERROR_PATTERN.search(combined))
    has_path = bool(paths) or bool(_PATH_PATTERN.search(combined))
    has_traceback = bool(paths)
    has_symbol = any(
        bool(_SYMBOL_PATTERN.fullmatch(value))
        and (
            "_" in value
            or "." in value
            or any(character.isupper() for character in value[1:])
        )
        for value in keywords
    )
    has_semantic = (
        paper_evidence_count > 0
        or len(combined) >= 180
        or len(tokens) >= 28
    )

    # 优先级本身就是策略契约：可信 traceback > 精确错误 > symbol/path > 语义。
    if has_traceback:
        query_kind = "diagnostic"
    elif has_error:
        query_kind = "exact_error"
    elif (has_symbol or has_path) and not has_semantic:
        query_kind = "symbol_path"
    elif has_semantic and not (has_symbol or has_path):
        query_kind = "semantic_alignment"
    else:
        query_kind = "mixed"

    return RetrievalQueryFeatures(
        query_sha256=sha256_value(
            {
                "query": query,
                "keywords": keywords,
                "preferred_paths": paths,
            }
        ),
        query_kind=query_kind,
        token_count=len(tokens),
        keyword_count=len(keywords),
        paper_evidence_count=paper_evidence_count,
        preferred_path_count=len(paths),
        has_error_signature=has_error,
        has_symbol_hint=has_symbol,
        has_path_hint=has_path,
        has_traceback_path=has_traceback,
        has_semantic_description=has_semantic,
        feature_version=FEATURE_VERSION,
    )


def select_retrieval_profile(
    *,
    policy: RetrievalPolicyConfig,
    features: RetrievalQueryFeatures,
    dense_available: bool,
    mode: RetrievalPolicyMode,
) -> RetrievalDecision:
    """
    返回可审计决策。

    dense_available 必须由 Settings + capability/readiness 计算，不能由 query、
    LLM 或 Project Fact 提供。off 模式不会调用本函数。
    """

    reason_codes: list[str] = []
    selected_profile_id = policy.default_profile_id

    for rule in sorted(
        policy.rules,
        key=lambda item: (-item.priority, item.rule_id),
    ):
        if features.query_kind not in rule.query_kinds:
            continue
        if rule.requires_dense_available and not dense_available:
            reason_codes.append(
                f"RULE_SKIPPED_DENSE_UNAVAILABLE:{rule.rule_id}"
            )
            continue
        selected_profile_id = rule.profile_id
        reason_codes.append(f"RULE_MATCHED:{rule.rule_id}")
        break
    else:
        reason_codes.append("DEFAULT_PROFILE")

    selected = profile_by_id(policy, selected_profile_id)
    fallback_used = False
    if selected.requires_dense and not dense_available:
        selected = profile_by_id(policy, policy.fallback_profile_id)
        fallback_used = True
        reason_codes.append("FALLBACK_DENSE_UNAVAILABLE")

    policy_sha256 = sha256_value(policy)
    profile_sha256 = sha256_value(selected)
    decision_payload = {
        "policy_sha256": policy_sha256,
        "profile_sha256": profile_sha256,
        "policy_version": policy.policy_version,
        "mode": mode,
        "applied": mode == "active",
        "query_features": features.model_dump(mode="json"),
        "reason_codes": reason_codes,
        "dense_available": dense_available,
        "fallback_used": fallback_used,
    }

    return RetrievalDecision(
        decision_sha256=sha256_value(decision_payload),
        policy_sha256=policy_sha256,
        profile_sha256=profile_sha256,
        policy_version=policy.policy_version,
        mode=mode,
        applied=mode == "active",
        selected_profile=selected,
        query_features=features,
        reason_codes=reason_codes,
        dense_available=dense_available,
        fallback_used=fallback_used,
    )
