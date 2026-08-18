from __future__ import annotations

from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.storage.errors import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
)
from app.storage.ports import (
    ArtifactRepository,
    BlobStore,
    OpenedArtifact,
)


class BlobStoreRegistry:
    def __init__(
        self,
        stores: list[BlobStore],
    ):
        self._stores = {
            item.backend_name: item
            for item in stores
        }

    def get(self, backend: str) -> BlobStore:
        store = self._stores.get(backend)
        if store is None:
            raise ArtifactNotFoundError(
                "当前进程没有注册 Artifact backend："
                f"{backend}"
            )
        return store


class PublishedArtifactCatalog:
    def __init__(
        self,
        *,
        repository: ArtifactRepository,
        registry: BlobStoreRegistry,
    ):
        self.repository = repository
        self.registry = registry
        self.repository.initialize()

    def list_views(
        self,
        job: JobRecord,
    ) -> list[ArtifactView]:
        return [
            ArtifactView(
                artifact_id=(
                    item.descriptor.artifact_id
                ),
                run_id=item.descriptor.run_id,
                layer=item.descriptor.layer,
                relative_path=(
                    item.descriptor.relative_path
                ),
                media_type=(
                    item.descriptor.media_type
                ),
                sha256=item.descriptor.sha256,
                size_bytes=(
                    item.descriptor.size_bytes
                ),
                producer_node=(
                    item.descriptor.producer_node
                ),
                created_at=(
                    item.descriptor.created_at
                ),
                integrity_status="unchecked",
            )
            for item in (
                self.repository.list_for_job(
                    job.job_id
                )
            )
            if item.descriptor.run_id
            == job.run_id
        ]

    def open(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> OpenedArtifact:
        artifact = self.repository.find(
            job_id=job.job_id,
            artifact_id=artifact_id,
        )
        if artifact is None:
            raise ArtifactNotFoundError(
                "当前 Job 中不存在 "
                f"artifact_id={artifact_id}"
            )
        if artifact.descriptor.run_id != (
            job.run_id
        ):
            raise ArtifactIntegrityError(
                "Catalog Artifact run_id "
                "与 Job 不一致"
            )

        store = self.registry.get(
            artifact.backend
        )
        opened = store.open(
            artifact.object_key
        )
        if (
            opened.stat.sha256
            != artifact.descriptor.sha256
            or opened.stat.size_bytes
            != artifact.descriptor.size_bytes
        ):
            opened.body.close()
            raise ArtifactIntegrityError(
                "Blob 与 Catalog 当前 revision "
                "不一致"
            )
        return OpenedArtifact(
            artifact=artifact,
            blob=opened,
        )