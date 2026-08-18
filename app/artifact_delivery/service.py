from __future__ import annotations

import codecs
import hashlib
import json
import os
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from app.artifact_delivery.errors import (
    ArtifactExportLimitExceeded,
    ArtifactPreviewUnsupported,
)
from app.artifact_delivery.schemas import (
    ArtifactPreviewResponse,
    ExportArtifactEntry,
    JobExportManifest,
    PreparedJobExport,
)
from app.interaction.artifacts import ArtifactCatalog
from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.storage.errors import ArtifactIntegrityError
from app.storage.schemas import ArtifactDescriptor

# 预览需要媒体类型和扩展名同时命中。HTML/SVG 不在其中。
SAFE_PREVIEW_MEDIA_TYPES = {
    "application/json",
    "application/x-yaml",
    "text/csv",
    "text/markdown",
    "text/plain",
    "text/x-diff",
    "text/x-python",
    "text/yaml",
}

SAFE_PREVIEW_SUFFIXES = {
    ".csv",
    ".diff",
    ".json",
    ".jsonl",
    ".log",
    ".markdown",
    ".md",
    ".patch",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """manifest hash 使用稳定 JSON 编码，不能依赖缩进或 key 顺序。"""

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def preview_supported(*, media_type: str, relative_path: str) -> bool:
    """公开给 API 与 Web 共用的确定性预览能力判断。"""

    normalized_media_type = media_type.split(";", 1)[0].strip().lower()
    suffix = PurePosixPath(relative_path).suffix.lower()
    return (
        normalized_media_type in SAFE_PREVIEW_MEDIA_TYPES
        and suffix in SAFE_PREVIEW_SUFFIXES
    )


def _archive_path(relative_path: str) -> str:
    """把 Catalog 相对路径变成安全 ZIP member 名称。"""

    if "\x00" in relative_path or "\\" in relative_path:
        raise ArtifactIntegrityError("Artifact 导出路径包含非法字符")

    parts = relative_path.split("/")
    if (
        not relative_path
        or relative_path.startswith("/")
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ArtifactIntegrityError("Artifact 导出路径不是安全相对路径")

    normalized = PurePosixPath(relative_path)
    if normalized.is_absolute():
        raise ArtifactIntegrityError("Artifact 导出路径不能是绝对路径")

    return str(PurePosixPath("artifacts") / normalized)


def _zip_info(name: str) -> zipfile.ZipInfo:
    """使用普通文件权限，避免把宿主机权限带入导出包。"""

    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def _same_snapshot(
    view: ArtifactView,
    descriptor: ArtifactDescriptor,
) -> bool:
    """list_views() 后到 open() 前不能发生身份漂移。"""

    return all(
        (
            descriptor.artifact_id == view.artifact_id,
            descriptor.run_id == view.run_id,
            descriptor.layer == view.layer,
            descriptor.relative_path == view.relative_path,
            descriptor.media_type == view.media_type,
            descriptor.sha256 == view.sha256,
            descriptor.size_bytes == view.size_bytes,
            descriptor.producer_node == view.producer_node,
            descriptor.created_at == view.created_at,
        )
    )


class ArtifactDeliveryService:
    def __init__(
        self,
        *,
        catalog: ArtifactCatalog,
        preview_max_bytes: int,
        stream_chunk_bytes: int,
        export_allowed_root: Path,
        export_staging_root: Path,
        export_max_artifacts: int,
        export_max_uncompressed_bytes: int,
        export_max_archive_bytes: int,
        export_staging_ttl_seconds: int,
    ) -> None:
        self.catalog = catalog
        self.preview_max_bytes = preview_max_bytes
        self.stream_chunk_bytes = stream_chunk_bytes
        self.export_allowed_root = export_allowed_root
        self.export_staging_root = export_staging_root
        self.export_max_artifacts = export_max_artifacts
        self.export_max_uncompressed_bytes = (
            export_max_uncompressed_bytes
        )
        self.export_max_archive_bytes = export_max_archive_bytes
        self.export_staging_ttl_seconds = export_staging_ttl_seconds

    def list_views(self, job: JobRecord) -> list[ArtifactView]:
        """只增加能力标记，不暴露 BlobStore 内部字段。"""

        return [
            item.model_copy(
                update={
                    "preview_supported": preview_supported(
                        media_type=item.media_type,
                        relative_path=item.relative_path,
                    )
                }
            )
            for item in self.catalog.list_views(job)
        ]

    def preview(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> ArtifactPreviewResponse:
        """读取最多 max + 1 字节，额外一字节只用于判断截断。"""

        opened = self.catalog.open(job=job, artifact_id=artifact_id)
        descriptor = opened.artifact.descriptor
        try:
            if not preview_supported(
                media_type=descriptor.media_type,
                relative_path=descriptor.relative_path,
            ):
                raise ArtifactPreviewUnsupported(
                    "该 Artifact 类型不支持网页内预览，请使用下载"
                )

            raw = opened.blob.body.read(self.preview_max_bytes + 1)
        finally:
            # 不论类型拒绝、解码失败还是正常返回，都关闭本地/S3 body。
            opened.blob.body.close()

        if descriptor.size_bytes <= self.preview_max_bytes:
            if (
                len(raw) != descriptor.size_bytes
                or hashlib.sha256(raw).hexdigest() != descriptor.sha256
            ):
                raise ArtifactIntegrityError(
                    "Artifact 预览时大小或 SHA-256 校验失败"
                )
        elif len(raw) != self.preview_max_bytes + 1:
            # 声明为大文件却提前 EOF，说明 descriptor/blob 已漂移。
            raise ArtifactIntegrityError(
                "Artifact 预览流早于声明大小结束"
            )

        truncated = descriptor.size_bytes > self.preview_max_bytes
        bounded = raw[: self.preview_max_bytes]

        if b"\x00" in bounded:
            raise ArtifactPreviewUnsupported(
                "Artifact 内容包含 NUL，不能作为文本预览"
            )

        # final=False 允许 decoder 暂存被字节上限截断的 UTF-8 尾部；
        # 中间位置的非法字节仍会严格报错。
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        try:
            content = decoder.decode(
                bounded,
                final=not truncated,
            )
        except UnicodeDecodeError as exc:
            raise ArtifactPreviewUnsupported(
                "Artifact 不是有效 UTF-8 文本"
            ) from exc

        buffered_tail, _decoder_state = decoder.getstate()
        decoded_bytes = len(bounded) - len(buffered_tail)

        # 允许换行、回车和制表符，拒绝其他 C0 控制字符。
        if any(ord(char) < 32 and char not in "\n\r\t" for char in content):
            raise ArtifactPreviewUnsupported(
                "Artifact 包含不允许的控制字符"
            )

        return ArtifactPreviewResponse(
            artifact_id=descriptor.artifact_id,
            relative_path=descriptor.relative_path,
            media_type=descriptor.media_type,
            sha256=descriptor.sha256,
            total_size_bytes=descriptor.size_bytes,
            returned_bytes=decoded_bytes,
            truncated=truncated,
            content=content,
        )

    def _prepare_staging(self) -> Path:
        """创建项目内 staging，并顺带清理崩溃遗留的小范围文件。"""

        allowed_root = self.export_allowed_root.expanduser().resolve()
        if not allowed_root.is_dir():
            raise ArtifactIntegrityError("导出 allowed root 不存在或不是目录")

        configured = self.export_staging_root.expanduser()
        if not configured.is_absolute():
            configured = allowed_root / configured

        # strict=False 会解析已经存在的父目录和软链接，但不要求叶子存在。
        resolved = configured.resolve(strict=False)
        if resolved == allowed_root or allowed_root not in resolved.parents:
            raise ArtifactIntegrityError("导出 staging root 越出允许目录")

        if configured.exists() and configured.is_symlink():
            raise ArtifactIntegrityError("导出 staging root 不能是软链接")

        configured.mkdir(parents=True, exist_ok=True, mode=0o700)
        # mkdir 与后续使用之间再次解析，避免配置指向意外位置。
        resolved = configured.resolve()
        if allowed_root not in resolved.parents:
            raise ArtifactIntegrityError("导出 staging root 越出允许目录")

        cutoff = time.time() - self.export_staging_ttl_seconds
        for candidate in resolved.iterdir():
            # 只处理当前目录直属、由本服务命名的临时文件。
            if not candidate.is_file() or candidate.suffix not in {".part", ".zip"}:
                continue
            try:
                if candidate.stat().st_mtime < cutoff:
                    candidate.unlink()
            except FileNotFoundError:
                pass

        return resolved

    def _snapshot_entries(
        self,
        job: JobRecord,
    ) -> tuple[list[ArtifactView], list[ExportArtifactEntry], int]:
        views = self.catalog.list_views(job)
        if len(views) > self.export_max_artifacts:
            raise ArtifactExportLimitExceeded(
                "当前 Job 的 Artifact 数量超过导出上限"
            )

        total = sum(item.size_bytes for item in views)
        if total > self.export_max_uncompressed_bytes:
            raise ArtifactExportLimitExceeded(
                "当前 Job 的 Artifact 未压缩总大小超过导出上限"
            )

        entries: list[ExportArtifactEntry] = []
        archive_paths: set[str] = set()
        archive_paths_casefold: set[str] = set()
        artifact_ids: set[str] = set()
        for view in sorted(views, key=lambda item: (item.layer, item.relative_path)):
            if view.run_id != job.run_id:
                raise ArtifactIntegrityError("Artifact run_id 与当前 Job 不一致")
            if view.artifact_id in artifact_ids:
                raise ArtifactIntegrityError("导出中出现重复 artifact_id")
            artifact_ids.add(view.artifact_id)
            archive_path = _archive_path(view.relative_path)
            folded_path = archive_path.casefold()
            if (
                archive_path in archive_paths
                or folded_path in archive_paths_casefold
            ):
                raise ArtifactIntegrityError("导出中出现重复 Artifact 路径")
            archive_paths.add(archive_path)
            archive_paths_casefold.add(folded_path)
            entries.append(
                ExportArtifactEntry(
                    artifact_id=view.artifact_id,
                    run_id=view.run_id,
                    layer=view.layer,
                    relative_path=view.relative_path,
                    archive_path=archive_path,
                    media_type=view.media_type,
                    sha256=view.sha256,
                    size_bytes=view.size_bytes,
                    producer_node=view.producer_node,
                    created_at=view.created_at,
                )
            )

        return views, entries, total

    def _write_artifact(
        self,
        *,
        archive: zipfile.ZipFile,
        job: JobRecord,
        view: ArtifactView,
        entry: ExportArtifactEntry,
    ) -> None:
        opened = self.catalog.open(job=job, artifact_id=view.artifact_id)
        descriptor = opened.artifact.descriptor
        digest = hashlib.sha256()
        written = 0

        try:
            if not _same_snapshot(view, descriptor):
                raise ArtifactIntegrityError(
                    "Artifact 在导出快照建立后发生变化"
                )

            with archive.open(_zip_info(entry.archive_path), mode="w") as target:
                while True:
                    chunk = opened.blob.body.read(self.stream_chunk_bytes)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > view.size_bytes:
                        raise ArtifactIntegrityError(
                            "Artifact 实际大小超过导出快照"
                        )
                    digest.update(chunk)
                    target.write(chunk)
        finally:
            opened.blob.body.close()

        if written != view.size_bytes or digest.hexdigest() != view.sha256:
            raise ArtifactIntegrityError(
                "Artifact 导出时大小或 SHA-256 校验失败"
            )

    def build_export(
        self,
        *,
        job: JobRecord,
        public_job: dict[str, Any],
    ) -> PreparedJobExport:
        """完整构建成功后才返回 PreparedJobExport。"""

        views, entries, total = self._snapshot_entries(job)
        # 用 artifact_id 关联排序后的 manifest entry，避免依赖两个列表顺序。
        entries_by_id = {item.artifact_id: item for item in entries}

        staging_root = self._prepare_staging()
        token = uuid4().hex
        part_path = staging_root / f"{token}.part"
        final_path = staging_root / f"{token}.zip"

        generated_at = utc_now()
        manifest_without_hash: dict[str, Any] = {
            "manifest_version": "phase34-v1",
            "generated_at": generated_at,
            "job_id": job.job_id,
            "run_id": job.run_id,
            "artifact_count": len(entries),
            "total_uncompressed_bytes": total,
            "job": public_job,
            "artifacts": [item.model_dump(mode="json") for item in entries],
        }
        manifest_hash = hashlib.sha256(
            canonical_json_bytes(manifest_without_hash)
        ).hexdigest()
        manifest = JobExportManifest(
            **manifest_without_hash,
            manifest_sha256=manifest_hash,
        )

        try:
            with zipfile.ZipFile(
                part_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
                allowZip64=True,
            ) as archive:
                # 先写公开 Job 投影；禁止直接 dump 内部 JobRecord。
                archive.writestr(
                    _zip_info("metadata/job.json"),
                    json.dumps(
                        public_job,
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    ).encode("utf-8"),
                )

                for view in sorted(
                    views,
                    key=lambda item: (item.layer, item.relative_path),
                ):
                    self._write_artifact(
                        archive=archive,
                        job=job,
                        view=view,
                        entry=entries_by_id[view.artifact_id],
                    )

                archive.writestr(
                    _zip_info("metadata/export_manifest.json"),
                    json.dumps(
                        manifest.model_dump(mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    ).encode("utf-8"),
                )

            archive_size = part_path.stat().st_size
            if archive_size > self.export_max_archive_bytes:
                raise ArtifactExportLimitExceeded(
                    "生成的 ZIP 大小超过导出上限"
                )

            archive_digest = hashlib.sha256()
            with part_path.open("rb") as stream:
                while True:
                    chunk = stream.read(self.stream_chunk_bytes)
                    if not chunk:
                        break
                    archive_digest.update(chunk)

            os.replace(part_path, final_path)

            safe_job = _SAFE_FILENAME.sub("_", job.job_id).strip("._") or "job"
            safe_run = _SAFE_FILENAME.sub("_", job.run_id).strip("._") or "run"
            filename = f"paper-copilot-{safe_job[:60]}-{safe_run[:60]}.zip"

            return PreparedJobExport(
                path=final_path,
                filename=filename,
                size_bytes=archive_size,
                sha256=archive_digest.hexdigest(),
                manifest=manifest,
            )
        except Exception:
            # part 或 rename 后的 final 都可能存在；失败时不能留下垃圾。
            part_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise
