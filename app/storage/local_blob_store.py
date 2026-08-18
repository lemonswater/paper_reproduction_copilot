from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
from uuid import uuid4

from app.storage.errors import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
)
from app.storage.ports import OpenedBlob
from app.storage.schemas import BlobStat
from app.tools.artifact_tools import sha256_file


class LocalBlobStore:
    backend_name = "local"
    sharing_scope = "host"

    def __init__(self, root: Path):
        self.root = root.resolve()

    def ensure_ready(self) -> None:
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _path(self, object_key: str) -> Path:
        logical = PurePosixPath(object_key)
        if (
            logical.is_absolute()
            or not logical.parts
            or any(
                part in {"", ".", ".."}
                for part in logical.parts
            )
        ):
            raise ArtifactIntegrityError(
                "无效的 object_key"
            )

        candidate = (
            self.root.joinpath(
                *logical.parts
            ).resolve()
        )
        if self.root not in candidate.parents:
            raise ArtifactIntegrityError(
                "object_key 逃逸 Blob root"
            )
        return candidate

    def stat(
        self,
        object_key: str,
    ) -> BlobStat | None:
        path = self._path(object_key)
        if not path.is_file():
            return None
        digest = sha256_file(path)
        return BlobStat(
            backend=self.backend_name,
            object_key=object_key,
            size_bytes=path.stat().st_size,
            sha256=digest,
            etag=digest,
        )

    def put_file(
        self,
        *,
        object_key: str,
        source_path: Path,
        expected_sha256: str,
        expected_size: int,
        media_type: str,
    ) -> BlobStat:
        del media_type
        self.ensure_ready()
        source = source_path.resolve()
        if not source.is_file():
            raise ArtifactNotFoundError(
                f"待发布文件不存在：{source}"
            )
        if source.stat().st_size != expected_size:
            raise ArtifactIntegrityError(
                "待发布文件大小与 ArtifactRecord 不一致"
            )
        if sha256_file(source) != expected_sha256:
            raise ArtifactIntegrityError(
                "待发布文件 SHA-256 与 ArtifactRecord 不一致"
            )

        existing = self.stat(object_key)
        if existing is not None:
            if (
                existing.sha256 != expected_sha256
                or existing.size_bytes != expected_size
            ):
                raise ArtifactIntegrityError(
                    "已有 Blob 与目标内容不一致"
                )
            return existing

        target = self._path(object_key)
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temp = target.with_name(
            f".{target.name}.{uuid4().hex}.tmp"
        )
        digest = hashlib.sha256()
        copied = 0
        try:
            with (
                source.open("rb") as source_file,
                temp.open("xb") as target_file,
            ):
                while True:
                    chunk = source_file.read(
                        1024 * 1024
                    )
                    if not chunk:
                        break
                    target_file.write(chunk)
                    digest.update(chunk)
                    copied += len(chunk)
                target_file.flush()
                os.fsync(target_file.fileno())

            if (
                copied != expected_size
                or digest.hexdigest()
                != expected_sha256
            ):
                raise ArtifactIntegrityError(
                    "复制期间源文件发生变化"
                )

            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()

        stored = self.stat(object_key)
        if stored is None:
            raise ArtifactIntegrityError(
                "Blob 原子写入后不可见"
            )
        return stored

    def open(
        self,
        object_key: str,
    ) -> OpenedBlob:
        stat = self.stat(object_key)
        if stat is None:
            raise ArtifactNotFoundError(
                "Artifact Blob 不存在"
            )
        path = self._path(object_key)
        return OpenedBlob(
            stat=stat,
            body=path.open("rb"),
        )

    # ------------------------------------------------------------------
    # Phase 35: Retention methods
    # ------------------------------------------------------------------

    def delete_if_matches(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_size: int,
    ) -> bool:
        """只有磁盘上的对象仍与 Plan 身份一致时才删除。"""
        path = self._path(object_key)
        if not path.exists() and not path.is_symlink():
            return False
        if path.is_symlink() or not path.is_file():
            raise ArtifactIntegrityError("待删除 Blob 不是普通文件")

        stat_result = path.stat(follow_symlinks=False)
        if stat_result.st_size != expected_size:
            raise ArtifactIntegrityError("待删除 Blob size 已变化")
        if sha256_file(path) != expected_sha256:
            raise ArtifactIntegrityError("待删除 Blob SHA-256 已变化")

        path.unlink()

        parent = path.parent
        while parent != self.root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
        return True
