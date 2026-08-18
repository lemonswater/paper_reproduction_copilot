from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArtifactDeliveryModel(BaseModel):
    """交付 API 的结构化对象都拒绝未知字段。"""

    model_config = ConfigDict(extra="forbid")


class ArtifactPreviewResponse(ArtifactDeliveryModel):
    artifact_id: str
    relative_path: str
    media_type: str
    sha256: str
    total_size_bytes: int = Field(ge=0)
    returned_bytes: int = Field(ge=0)
    truncated: bool
    encoding: str = "utf-8"
    content: str


class ExportArtifactEntry(ArtifactDeliveryModel):
    artifact_id: str
    run_id: str
    layer: str
    relative_path: str
    archive_path: str
    media_type: str
    sha256: str
    size_bytes: int = Field(ge=0)
    producer_node: str
    created_at: str


class JobExportManifest(ArtifactDeliveryModel):
    manifest_version: str = "phase34-v1"
    generated_at: str
    job_id: str
    run_id: str
    artifact_count: int = Field(ge=0)
    total_uncompressed_bytes: int = Field(ge=0)
    job: dict[str, Any]
    artifacts: list[ExportArtifactEntry]
    manifest_sha256: str


@dataclass(frozen=True)
class PreparedJobExport:
    """已经完成校验、可以开始响应的临时 ZIP。"""

    path: Path
    filename: str
    size_bytes: int
    sha256: str
    manifest: JobExportManifest
