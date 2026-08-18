from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.storage.artifact_repository import (
    SqliteArtifactRepository,
)
from app.storage.catalog import (
    BlobStoreRegistry,
    PublishedArtifactCatalog,
)
from app.storage.local_blob_store import (
    LocalBlobStore,
)
from app.storage.ports import (
    ArtifactRepository,
    BlobStore,
)
from app.storage.publisher import (
    ArtifactPublisher,
)


@dataclass(frozen=True)
class ArtifactStorageBundle:
    repository: ArtifactRepository
    stores: list[BlobStore]
    selected_store: BlobStore
    publisher: ArtifactPublisher
    catalog: PublishedArtifactCatalog


def build_artifact_storage() -> (
    ArtifactStorageBundle
):
    if settings.job_store_backend == "sqlite":
        repository: ArtifactRepository = (
            SqliteArtifactRepository(
                settings.artifact_catalog_db_path
            )
        )
    elif settings.job_store_backend == "postgresql":
        from app.storage.postgres_artifact_repository import (
            PostgresArtifactRepository,
        )

        repository = PostgresArtifactRepository()
    else:
        raise ValueError(
            "不支持的 metadata backend"
        )

    repository.initialize()

    local = LocalBlobStore(
        settings.artifact_local_store_dir
    )
    local.ensure_ready()
    stores: list[BlobStore] = [local]

    if settings.artifact_blob_backend == "local":
        selected: BlobStore = local
    elif (
        settings.artifact_blob_backend
        == "s3"
    ):
        # 动态 import：只使用 local 时不强制安装 boto3。
        from app.storage.s3_blob_store import (
            S3BlobStore,
        )

        selected = S3BlobStore(
            bucket=(
                settings.artifact_s3_bucket
            ),
            prefix=(
                settings.artifact_s3_prefix
            ),
            endpoint_url=(
                settings
                .artifact_s3_endpoint_url
            ),
            region=(
                settings.artifact_s3_region
            ),
            force_path_style=(
                settings
                .artifact_s3_force_path_style
            ),
            auto_create_bucket=(
                settings
                .artifact_s3_auto_create_bucket
            ),
            connect_timeout=(
                settings
                .artifact_s3_connect_timeout_seconds
            ),
            read_timeout=(
                settings
                .artifact_s3_read_timeout_seconds
            ),
            max_attempts=(
                settings
                .artifact_s3_max_attempts
            ),
        )
        stores.append(selected)
    else:
        raise ValueError(
            "不支持的 ARTIFACT_BLOB_BACKEND："
            f"{settings.artifact_blob_backend}"
        )

    registry = BlobStoreRegistry(stores)
    return ArtifactStorageBundle(
        repository=repository,
        stores=stores,
        selected_store=selected,
        publisher=ArtifactPublisher(
            repository=repository,
            blob_store=selected,
        ),
        catalog=PublishedArtifactCatalog(
            repository=repository,
            registry=registry,
        ),
    )