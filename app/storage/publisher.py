from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from app.job_runtime.schemas import JobRecord
from app.observability.context import bind_telemetry_context
from app.observability.ports import TelemetryPort
from app.observability.runtime import build_telemetry_runtime
from app.schemas import ArtifactRecord
from app.storage.errors import (
    ArtifactIntegrityError,
)
from app.storage.ports import (
    ArtifactRepository,
    BlobStore,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    ArtifactPublicationReport,
)
from app.tools.artifact_tools import sha256_file
from app.workspace.paths import (
    require_managed_run_root,
    require_workspace_relative_path,
)
from app.workspace.schemas import WorkspaceBinding


def artifact_object_key(
    record: ArtifactRecord,
) -> str:
    """使用内容地址，不把本地路径写入 object key。"""

    return (
        f"sha256/{record.sha256[:2]}/"
        f"{record.sha256}"
    )


class ArtifactPublisher:
    def __init__(
        self,
        *,
        repository: ArtifactRepository,
        blob_store: BlobStore,
        telemetry: TelemetryPort | None = None,
    ):
        self.repository = repository
        self.blob_store = blob_store
        self.telemetry = (
            telemetry
            if telemetry is not None
            else build_telemetry_runtime().telemetry
        )
        self.repository.initialize()

    def _source_path(
        self,
        *,
        job: JobRecord,
        record: ArtifactRecord,
        workspace_binding: (
            WorkspaceBinding | None
        ) = None,
    ) -> Path:
        if record.run_id != job.run_id:
            raise ArtifactIntegrityError(
                "Artifact run_id 与 Job 不一致"
            )

        run_root = require_managed_run_root(
            workspace_binding.run_dir
            if workspace_binding is not None
            else job.run_dir
        )
        logical = require_workspace_relative_path(
            record.relative_path
        )
        source = run_root.joinpath(
            *logical.parts
        ).resolve()
        if (
            source == run_root
            or run_root not in source.parents
        ):
            raise ArtifactIntegrityError(
                "Artifact source 逃逸 run_dir"
            )
        if not source.is_file():
            raise ArtifactIntegrityError(
                "Artifact source 不存在"
            )
        if source.stat().st_size != (
            record.size_bytes
        ):
            raise ArtifactIntegrityError(
                "Artifact source 大小变化"
            )
        if sha256_file(source) != record.sha256:
            raise ArtifactIntegrityError(
                "Artifact source SHA-256 变化"
            )
        return source

    def publish(
        self,
        *,
        job: JobRecord,
        records: Iterable[
            ArtifactRecord | dict
        ],
        workspace_binding: (
            WorkspaceBinding | None
        ) = None,
        ensure_active: Callable[
            [],
            None,
        ] = lambda: None,
    ) -> ArtifactPublicationReport:
        with bind_telemetry_context(
            job_id=job.job_id,
            run_id=job.run_id,
            stage="artifact_publish",
        ):
            try:
                with self.telemetry.span(
                    "artifact.publish",
                    attributes={
                        "job_id": job.job_id,
                        "backend": (
                            self.blob_store.backend_name
                        ),
                    },
                ) as span:
                    # 同一个 checkpoint 中同一 artifact_id 只发布最后一条。
                    latest: dict[str, ArtifactRecord] = {}
                    for raw in records:
                        record = (
                            raw
                            if isinstance(
                                raw,
                                ArtifactRecord,
                            )
                            else ArtifactRecord.model_validate(
                                raw
                            )
                        )
                        latest[record.artifact_id] = record

                    published_count = 0
                    reused_count = 0
                    artifact_ids: list[str] = []
                    span.set_attribute(
                        "artifact_count",
                        len(latest),
                    )

                    for record in sorted(
                        latest.values(),
                        key=lambda item: (
                            item.layer,
                            item.relative_path,
                        ),
                    ):
                        ensure_active()
                        with bind_telemetry_context(
                            graph_node="artifact.publish_one"
                        ):
                            source = self._source_path(
                                job=job,
                                record=record,
                                workspace_binding=workspace_binding,
                            )
                            descriptor = ArtifactDescriptor.from_record(
                                record
                            )
                            current = self.repository.find(
                                job_id=job.job_id,
                                artifact_id=record.artifact_id,
                            )

                            reusable = (
                                current is not None
                                and current.backend
                                == self.blob_store.backend_name
                                and current.descriptor.sha256
                                == record.sha256
                            )
                            if reusable:
                                blob = self.blob_store.stat(
                                    current.object_key
                                )
                                if (
                                    blob is None
                                    or blob.sha256
                                    != record.sha256
                                    or blob.size_bytes
                                    != record.size_bytes
                                ):
                                    raise ArtifactIntegrityError(
                                        "Catalog 当前 Blob 不可用"
                                    )
                                reused_count += 1
                            else:
                                blob = self.blob_store.put_file(
                                    object_key=(
                                        artifact_object_key(
                                            record
                                        )
                                    ),
                                    source_path=source,
                                    expected_sha256=(
                                        record.sha256
                                    ),
                                    expected_size=(
                                        record.size_bytes
                                    ),
                                    media_type=(
                                        record.media_type
                                    ),
                                )
                                self.repository.publish(
                                    job_id=job.job_id,
                                    descriptor=descriptor,
                                    blob=blob,
                                )
                                published_count += 1

                            artifact_ids.append(
                                record.artifact_id
                            )
                            ensure_active()

                    span.set_attribute(
                        "published_count",
                        published_count,
                    )
                    span.set_attribute(
                        "reused_count",
                        reused_count,
                    )
                    return ArtifactPublicationReport(
                        artifact_count=len(latest),
                        published_count=published_count,
                        reused_count=reused_count,
                        backend=(
                            self.blob_store.backend_name
                        ),
                        artifact_ids=artifact_ids,
                    )
            except Exception:
                raise