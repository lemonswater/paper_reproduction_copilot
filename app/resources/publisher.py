from __future__ import annotations

"""Phase 29 发布不可变 ResourceManifest。

content-addressed Blob：``sha256`` 是最终身份，ETag 不能替代 hash。
Publisher 会再次 canonicalize source/redirect URL，不盲信调用者。
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app.resources.errors import ResourceIntegrityError
from app.resources.request_hash import canonicalize_url
from app.resources.schemas import ResourceManifest
from app.storage.ports import BlobStore


def resource_object_key(sha256: str) -> str:
    return f"resources/sha256/{sha256[:2]}/{sha256}"


def resource_manifest_sha256(payload: dict) -> str:
    """payload 不包含 manifest_sha256，避免自引用 hash。"""

    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ResourcePublisher:
    def __init__(self, blob_store: BlobStore):
        self.blob_store = blob_store

    def publish_file(
        self,
        *,
        resource_id: str,
        kind: str,
        source_url: str,
        redirect_chain: list[str],
        source: Path,
        sha256: str,
        size_bytes: int,
        media_type: str,
        git_commit: str | None = None,
    ) -> ResourceManifest:
        key = resource_object_key(sha256)
        stat = self.blob_store.put_file(
            object_key=key,
            source_path=source,
            expected_sha256=sha256,
            expected_size=size_bytes,
            media_type=media_type,
        )
        if (
            stat.sha256 != sha256
            or stat.size_bytes != size_bytes
        ):
            raise ResourceIntegrityError(
                "BlobStore publication identity mismatch"
            )

        # canonicalize_url 会再次拒绝 credentials/query/fragment。
        payload = {
            "manifest_version": "phase29-v1",
            "resource_id": resource_id,
            "kind": kind,
            "source_url_sanitized": canonicalize_url(
                source_url
            ),
            "redirect_chain_sanitized": [
                canonicalize_url(item)
                for item in redirect_chain
            ],
            "object_key": stat.object_key,
            "sha256": stat.sha256,
            "size_bytes": stat.size_bytes,
            "media_type": media_type,
            "git_commit": git_commit,
            "acquired_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
        return ResourceManifest(
            **payload,
            manifest_sha256=resource_manifest_sha256(
                payload
            ),
        )

    def manifest_exists(
        self, *, sha256: str, size_bytes: int
    ) -> bool:
        """同 expected hash 已存在时校验 metadata 后复用，不重复下载。"""

        existing = self.blob_store.stat(
            resource_object_key(sha256)
        )
        return (
            existing is not None
            and existing.sha256 == sha256
            and existing.size_bytes == size_bytes
        )
