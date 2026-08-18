from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.failure_memory.errors import FailureCaseIntegrityError
from app.failure_memory.schemas import (
    FailureCaseRecord,
    FailureSignature,
)
from app.schemas import StageError


FRAME_RE = re.compile(
    r'^\s*File\s+["\'](?P<path>.+?)["\'],\s*'
    r'line\s+\d+,\s*in\s+(?P<func>[^\s]+)\s*$',
    re.MULTILINE,
)
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{2,80}")
HEX_RE = re.compile(r"\b(?:0x)?[0-9a-fA-F]{8,}\b")
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,36}\b"
)
NUMBER_RE = re.compile(r"\b\d{2,}\b")

# 通用词会提高无关案例之间的相似度，所以不进入 fingerprint。
STOP_TOKENS = {
    "error",
    "exception",
    "traceback",
    "most",
    "recent",
    "call",
    "last",
    "file",
    "line",
    "python",
    "return",
    "failed",
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def _safe_frame_path(
    raw_path: str,
    *,
    repo_path: str | None,
) -> str:
    """只保留 repo-relative path；边界外只保留 basename。"""

    candidate = Path(raw_path)
    if repo_path:
        try:
            root = Path(repo_path).expanduser().resolve()
            resolved = candidate.expanduser().resolve()
            if resolved == root or root in resolved.parents:
                return resolved.relative_to(root).as_posix()
        except (OSError, RuntimeError, ValueError):
            pass
    return candidate.name or "unknown"


def extract_frame_keys(
    traceback_text: str,
    *,
    repo_path: str | None,
) -> list[str]:
    """行号不进入身份；函数名和安全路径共同描述调用位置。"""

    keys: list[str] = []
    for match in FRAME_RE.finditer(traceback_text):
        path = _safe_frame_path(
            match.group("path"),
            repo_path=repo_path,
        )
        key = f"{path}:{match.group('func')}".lower()
        if key not in keys:
            keys.append(key)
        if len(keys) >= 16:
            break
    return keys


def stable_traceback_for_tokens(
    traceback_text: str,
    *,
    repo_path: str | None,
) -> str:
    """先把 traceback 的绝对 File path 改成稳定安全路径。"""

    def replace(match: re.Match[str]) -> str:
        path = _safe_frame_path(
            match.group("path"),
            repo_path=repo_path,
        )
        return f"File {path} in {match.group('func')}"

    return FRAME_RE.sub(replace, traceback_text)


def normalize_failure_tokens(*parts: str) -> list[str]:
    """移除地址、UUID 和大数字后提取稳定标识符。"""

    material = "\n".join(parts)
    material = UUID_RE.sub(" ", material)
    material = HEX_RE.sub(" ", material)
    material = NUMBER_RE.sub(" ", material)

    tokens: list[str] = []
    for raw in TOKEN_RE.findall(material):
        token = raw.lower().strip("._-")
        if not token or token in STOP_TOKENS:
            continue
        # 绝对路径拆出的 home/data 用户名不应进入错误身份。
        if token in {"home", "data", "tmp", "users"}:
            continue
        if token not in tokens:
            tokens.append(token)
        if len(tokens) >= 64:
            break
    return sorted(tokens)


def build_failure_signature(
    *,
    stage_error: StageError,
    error_type: str,
    traceback_text: str,
    repo_path: str | None,
) -> FailureSignature:
    """构造与环境身份分离的 symptom fingerprint。"""

    frame_keys = extract_frame_keys(
        traceback_text,
        repo_path=repo_path,
    )
    tokens = normalize_failure_tokens(
        stage_error.code,
        stage_error.exception_type or "",
        stage_error.message,
        error_type,
        stable_traceback_for_tokens(
            traceback_text[-12000:],
            repo_path=repo_path,
        ),
    )
    payload = {
        "signature_version": "phase45-v1",
        "stage": stage_error.stage,
        "code": stage_error.code,
        "category": stage_error.category,
        "exception_type": stage_error.exception_type,
        "error_type": error_type,
        "normalized_tokens": tokens,
        "frame_keys": frame_keys,
    }
    return FailureSignature(
        **payload,
        signature_sha256=canonical_sha256(payload),
    )


def case_payload(record: FailureCaseRecord) -> dict[str, Any]:
    """Version/timestamp 是存储元数据，不参与语义内容身份。"""

    return record.model_dump(
        mode="json",
        exclude={
            "case_hash",
            "version",
            "created_at",
            "updated_at",
        },
    )


def compute_case_hash(record: FailureCaseRecord) -> str:
    return canonical_sha256(case_payload(record))


def validate_case_hash(record: FailureCaseRecord) -> None:
    expected = compute_case_hash(record)
    if expected != record.case_hash:
        raise FailureCaseIntegrityError(
            f"Failure Case hash 校验失败：{record.case_id}"
        )


def case_id_for_source(
    *,
    source_job_id: str,
    run_manifest_sha256: str,
    signature_sha256: str,
) -> str:
    digest = canonical_sha256(
        {
            "version": "phase45-v1",
            "source_job_id": source_job_id,
            "run_manifest_sha256": run_manifest_sha256,
            "signature_sha256": signature_sha256,
        }
    )
    return f"failure_{digest[:24]}"
