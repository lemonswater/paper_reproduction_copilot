from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.paper.schemas import SectionChunk, SectionExtractionDraft
from app.schemas import ArtifactRecord
from app.tools.artifact_tools import (
    resolve_artifact_path,
    write_json_artifact,
)

StructuredMethod = Literal[
    "json_schema",
    "function_calling",
    "json_mode",
]

# 防止损坏或异常缓存文件被无限读入内存。
MAX_SECTION_CACHE_BYTES = 2 * 1024 * 1024

# 当前 chunk_id 由 section_id、序号和 hash 构成，正常情况下只需要
# 字母、数字、点、下划线和连字符。这里再次校验，避免路径逃逸。
_SAFE_CHUNK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


class SectionExtractionCacheEntry(BaseModel):
    """一个章节抽取缓存文件的完整 envelope。"""

    model_config = ConfigDict(extra="forbid")

    cache_version: int = Field(default=1, ge=1)
    cache_key: str = Field(min_length=64, max_length=64)
    chunk_id: str
    section_id: str
    prompt_version: str
    schema_version: str
    model_name: str
    method: StructuredMethod
    strict: bool
    extraction: SectionExtractionDraft


def _sha256_json(payload: dict[str, object]) -> str:
    """使用规范 JSON 计算稳定 hash，避免字符串拼接歧义。"""

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_section_cache_key(
    *,
    source_sha256: str,
    chunk: SectionChunk,
    prompt_version: str,
    schema_version: str,
    model_name: str,
    method: StructuredMethod,
    strict: bool,
) -> str:
    """
    生成涵盖输入、Prompt、Schema 和 Provider 配置的缓存键。

    chunk_id/section_id 也进入 key，因为结构化输出会原样返回这两个值。
    即使两个 chunk 的正文 hash 相同，也不能互换业务身份。
    """

    return _sha256_json(
        {
            "source_sha256": source_sha256,
            "chunk_content_hash": chunk.content_hash,
            "chunk_id": chunk.chunk_id,
            "section_id": chunk.section_id,
            "prompt_version": prompt_version,
            "schema_version": schema_version,
            "model_name": model_name,
            "method": method,
            "strict": strict,
        }
    )


def section_cache_relative_path(chunk: SectionChunk) -> str:
    """生成受控的 run-relative 缓存路径。"""

    chunk_id = chunk.chunk_id
    if not _SAFE_CHUNK_ID_RE.fullmatch(chunk_id):
        raise ValueError(f"不安全的 section chunk_id：{chunk_id!r}")
    if chunk_id in {".", ".."}:
        raise ValueError(f"不安全的 section chunk_id：{chunk_id!r}")

    return (
        "analysis/paper_sections/extractions/"
        f"{chunk_id}.json"
    )


def load_valid_section_cache(
    *,
    state: dict,
    chunk: SectionChunk,
    expected_cache_key: str,
    prompt_version: str,
    schema_version: str,
    model_name: str,
    method: StructuredMethod,
    strict: bool,
) -> SectionExtractionDraft | None:
    """
    读取并严格校验缓存；不存在、损坏或过期时返回 None。

    路径安全错误不吞掉，因为这代表程序生成了非法 chunk_id；
    文件缺失、JSON 损坏和旧 schema 则属于正常 cache miss。
    """

    relative_path = section_cache_relative_path(chunk)
    path = resolve_artifact_path(state, relative_path)

    if not path.is_file():
        return None

    try:
        if path.stat().st_size > MAX_SECTION_CACHE_BYTES:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        entry = SectionExtractionCacheEntry.model_validate(payload)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValidationError,
    ):
        return None

    if entry.cache_key != expected_cache_key:
        return None
    if entry.chunk_id != chunk.chunk_id:
        return None
    if entry.section_id != chunk.section_id:
        return None
    if entry.prompt_version != prompt_version:
        return None
    if entry.schema_version != schema_version:
        return None
    if entry.model_name != model_name:
        return None
    if entry.method != method:
        return None
    if entry.strict is not strict:
        return None

    # extraction 已由 Pydantic 校验；这里再验证它没有篡改业务身份。
    if entry.extraction.section_id != chunk.section_id:
        return None
    if entry.extraction.chunk_id != chunk.chunk_id:
        return None

    return entry.extraction


def write_section_cache(
    *,
    state: dict,
    chunk: SectionChunk,
    cache_key: str,
    prompt_version: str,
    schema_version: str,
    model_name: str,
    method: StructuredMethod,
    strict: bool,
    extraction: SectionExtractionDraft,
) -> tuple[Path, ArtifactRecord]:
    """
    原子写入一个通过业务校验的章节抽取结果。

    write_json_artifact() 已使用项目现有原子写入和路径边界，
    不要在这里再实现 tempfile 或直接写工作区任意路径。
    """

    if extraction.section_id != chunk.section_id:
        raise ValueError(
            "不能缓存 section_id 与当前 chunk 不一致的 extraction"
        )
    if extraction.chunk_id != chunk.chunk_id:
        raise ValueError(
            "不能缓存 chunk_id 与当前 chunk 不一致的 extraction"
        )

    entry = SectionExtractionCacheEntry(
        cache_key=cache_key,
        chunk_id=chunk.chunk_id,
        section_id=chunk.section_id,
        prompt_version=prompt_version,
        schema_version=schema_version,
        model_name=model_name,
        method=method,
        strict=strict,
        extraction=extraction,
    )
    return write_json_artifact(
        state=state,
        relative_path=section_cache_relative_path(chunk),
        payload=entry.model_dump(mode="json"),
        producer_node="method_extractor",
    )