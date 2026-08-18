from __future__ import annotations

import hashlib
import json
from typing import Any

from app.comparison.errors import ComparisonIntegrityError
from app.comparison.schemas import ComparisonReport, RunSnapshot


def canonical_json_bytes(value: Any) -> bytes:
    """使用稳定 JSON 编码，避免字典顺序改变内容身份。"""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_text(value: str) -> str:
    """敏感文本只进入不可逆内容身份，不直接写入 Comparison。"""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def compute_snapshot_hash(snapshot: RunSnapshot | dict[str, Any]) -> str:
    payload = (
        snapshot.model_dump(mode="json")
        if isinstance(snapshot, RunSnapshot)
        else dict(snapshot)
    )
    # snapshot_hash 是当前 payload 的结果，不能参与自身计算。
    payload.pop("snapshot_hash", None)
    return sha256_payload(payload)


def validate_snapshot_hash(snapshot: RunSnapshot) -> None:
    if compute_snapshot_hash(snapshot) != snapshot.snapshot_hash:
        raise ComparisonIntegrityError("RunSnapshot hash 校验失败")


def compute_comparison_hash(
    report: ComparisonReport | dict[str, Any],
) -> str:
    payload = (
        report.model_dump(mode="json")
        if isinstance(report, ComparisonReport)
        else dict(report)
    )
    # 创建时间和外层身份不影响比较内容；同一对快照可幂等重放。
    payload.pop("comparison_id", None)
    payload.pop("comparison_hash", None)
    payload.pop("created_at", None)
    return sha256_payload(payload)


def comparison_id_for_hash(comparison_hash: str) -> str:
    return f"comparison_{comparison_hash[:24]}"


def validate_report_identity(report: ComparisonReport) -> None:
    validate_snapshot_hash(report.base)
    validate_snapshot_hash(report.target)
    actual_hash = compute_comparison_hash(report)
    if actual_hash != report.comparison_hash:
        raise ComparisonIntegrityError("Comparison hash 校验失败")
    if comparison_id_for_hash(actual_hash) != report.comparison_id:
        raise ComparisonIntegrityError("comparison_id 与内容 hash 不一致")
