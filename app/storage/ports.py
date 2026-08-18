from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Literal, Protocol

from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)


@dataclass(frozen=True)
class OpenedBlob:
    """body 必须由响应迭代器最终关闭。"""

    stat: BlobStat
    body: BinaryIO


@dataclass(frozen=True)
class OpenedArtifact:
    """Catalog 已鉴权定位的元数据与后端流。"""

    artifact: PublishedArtifact
    blob: OpenedBlob


class BlobStore(Protocol):
    backend_name: str
    sharing_scope: Literal["host", "shared"]

    def ensure_ready(self) -> None:
        ...

    def stat(
        self,
        object_key: str,
    ) -> BlobStat | None:
        ...

    def put_file(
        self,
        *,
        object_key: str,
        source_path: Path,
        expected_sha256: str,
        expected_size: int,
        media_type: str,
    ) -> BlobStat:
        ...

    def open(
        self,
        object_key: str,
    ) -> OpenedBlob:
        ...


class ArtifactRepository(Protocol):
    def initialize(self) -> None:
        ...

    def publish(
        self,
        *,
        job_id: str,
        descriptor: ArtifactDescriptor,
        blob: BlobStat,
    ) -> PublishedArtifact:
        ...

    def find(
        self,
        *,
        job_id: str,
        artifact_id: str,
    ) -> PublishedArtifact | None:
        ...

    def list_for_job(
        self,
        job_id: str,
    ) -> list[PublishedArtifact]:
        ...