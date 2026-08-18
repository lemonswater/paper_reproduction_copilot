from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import (
    ArtifactLayer,
    ArtifactRecord,
)


class StorageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArtifactDescriptor(StorageModel):
    """
    持久 Catalog 中的公开身份。

    故意不包含 absolute_path。
    """

    artifact_id: str
    run_id: str
    layer: ArtifactLayer
    relative_path: str
    media_type: str
    sha256: str
    size_bytes: int = Field(ge=0)
    producer_node: str
    created_at: str

    @classmethod
    def from_record(
        cls,
        record: ArtifactRecord,
    ) -> ArtifactDescriptor:
        return cls(
            artifact_id=record.artifact_id,
            run_id=record.run_id,
            layer=record.layer,
            relative_path=record.relative_path,
            media_type=record.media_type,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
            producer_node=record.producer_node,
            created_at=record.created_at,
        )


class BlobStat(StorageModel):
    backend: str
    object_key: str
    size_bytes: int = Field(ge=0)
    sha256: str
    etag: str | None = None
    version_id: str | None = None


class PublishedArtifact(StorageModel):
    job_id: str
    descriptor: ArtifactDescriptor
    backend: str
    object_key: str
    etag: str | None = None
    object_version_id: str | None = None
    revision: int = Field(ge=1)
    published_at: str


class ArtifactPublicationReport(StorageModel):
    status: Literal["completed"] = "completed"
    artifact_count: int = Field(ge=0)
    published_count: int = Field(ge=0)
    reused_count: int = Field(ge=0)
    backend: str
    artifact_ids: list[str] = Field(
        default_factory=list
    )