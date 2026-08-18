from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.retrieval.embedding_backend import (
    EmbeddingBackendIdentity,
    EmbeddingProviderError,
)


def build_embedding_cache_key(
    *,
    identity: EmbeddingBackendIdentity,
    cache_version: str,
    value_kind: str,
    content_hash: str,
) -> str:
    """
    API key 不得进入 key。

    value_kind 区分 document/query，避免相同文本在未来采用不同
    Provider instruction 时错误复用。
    """

    payload = "|".join(
        [
            identity.provider_namespace,
            identity.model,
            cache_version,
            value_kind,
            content_hash,
        ]
    )
    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def _decode_vector(
    raw_value: str,
    *,
    expected_dimensions: int,
) -> list[float]:
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise EmbeddingProviderError(
            "Embedding cache vector JSON 损坏"
        ) from exc

    if (
        not isinstance(payload, list)
        or len(payload) != expected_dimensions
    ):
        raise EmbeddingProviderError(
            "Embedding cache vector 维度损坏"
        )
    vector = [float(value) for value in payload]
    if not all(math.isfinite(value) for value in vector):
        raise EmbeddingProviderError(
            "Embedding cache vector 包含 NaN 或 Inf"
        )
    return vector


class SQLiteEmbeddingCache:
    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._initialize()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=15,
        )
        connection.execute(
            "PRAGMA journal_mode=WAL"
        )
        connection.execute(
            "PRAGMA busy_timeout=15000"
        )
        return connection

    def _initialize(
        self,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    cache_key TEXT PRIMARY KEY,
                    provider_namespace TEXT NOT NULL,
                    model TEXT NOT NULL,
                    cache_version TEXT NOT NULL,
                    value_kind TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    dimensions INTEGER NOT NULL,
                    vector_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def get_many(
        self,
        keys: list[str],
    ) -> dict[str, list[float]]:
        unique_keys = list(
            dict.fromkeys(keys)
        )
        if not unique_keys:
            return {}

        output: dict[str, list[float]] = {}
        # SQLite 默认变量数可能为 999，按 500 分批读取。
        with self._connect() as connection:
            for offset in range(
                0,
                len(unique_keys),
                500,
            ):
                batch = unique_keys[
                    offset:offset + 500
                ]
                placeholders = ",".join(
                    "?"
                    for _ in batch
                )
                rows = connection.execute(
                    (
                        "SELECT cache_key, dimensions, "
                        "vector_json "
                        "FROM embedding_cache "
                        f"WHERE cache_key IN ({placeholders})"
                    ),
                    batch,
                ).fetchall()
                for key, dimensions, raw_vector in rows:
                    try:
                        output[str(key)] = _decode_vector(
                            str(raw_vector),
                            expected_dimensions=int(
                                dimensions
                            ),
                        )
                    except EmbeddingProviderError:
                        # 损坏项当作 cache miss，稍后由 Provider 重建。
                        connection.execute(
                            (
                                "DELETE FROM embedding_cache "
                                "WHERE cache_key = ?"
                            ),
                            (key,),
                        )
        return output

    def put_many(
        self,
        *,
        identity: EmbeddingBackendIdentity,
        cache_version: str,
        value_kind: str,
        values: list[
            tuple[str, str, list[float]]
        ],
    ) -> None:
        """
        values:
            (cache_key, content_hash, vector)
        """

        if not values:
            return
        created_at = datetime.now(
            timezone.utc
        ).isoformat()
        rows = []
        for key, content_hash, vector in values:
            if not vector or not all(
                math.isfinite(float(value))
                for value in vector
            ):
                raise EmbeddingProviderError(
                    "拒绝缓存无效 Embedding 向量"
                )
            rows.append(
                (
                    key,
                    identity.provider_namespace,
                    identity.model,
                    cache_version,
                    value_kind,
                    content_hash,
                    len(vector),
                    json.dumps(
                        [
                            float(value)
                            for value in vector
                        ],
                        separators=(",", ":"),
                    ),
                    created_at,
                )
            )

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO embedding_cache (
                    cache_key,
                    provider_namespace,
                    model,
                    cache_version,
                    value_kind,
                    content_hash,
                    dimensions,
                    vector_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )