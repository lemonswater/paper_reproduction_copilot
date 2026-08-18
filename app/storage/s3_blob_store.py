from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    ConnectionClosedError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from app.storage.errors import (
    ArtifactBackendUnavailable,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStorageError,
)
from app.storage.ports import OpenedBlob
from app.storage.schemas import BlobStat
from app.tools.artifact_tools import sha256_file


_TRANSIENT_CODES = {
    "RequestTimeout",
    "SlowDown",
    "Throttling",
    "TooManyRequestsException",
    "ServiceUnavailable",
    "InternalError",
}

_NOT_FOUND_CODES = {
    "404",
    "NoSuchKey",
    "NotFound",
}


class S3BlobStore:
    backend_name = "s3"
    sharing_scope = "shared"

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str,
        endpoint_url: str | None,
        region: str,
        force_path_style: bool,
        auto_create_bucket: bool,
        connect_timeout: float,
        read_timeout: float,
        max_attempts: int,
        client: Any | None = None,
    ):
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.region = region
        self.auto_create_bucket = (
            auto_create_bucket
        )
        self.client = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            config=Config(
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                retries={
                    "mode": "standard",
                    "max_attempts": max_attempts,
                },
                s3={
                    "addressing_style": (
                        "path"
                        if force_path_style
                        else "auto"
                    )
                },
            ),
        )

    def _key(self, object_key: str) -> str:
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
        normalized = "/".join(logical.parts)
        if self.prefix:
            return f"{self.prefix}/{normalized}"
        return normalized

    def _raise_backend(
        self,
        exc: BaseException,
    ) -> NoReturn:
        if isinstance(
            exc,
            (
                EndpointConnectionError,
                ConnectTimeoutError,
                ConnectionClosedError,
                ReadTimeoutError,
            ),
        ):
            raise ArtifactBackendUnavailable(
                "S3 backend 暂时不可用"
            ) from exc

        if isinstance(exc, ClientError):
            error = exc.response.get(
                "Error",
                {},
            )
            code = str(error.get("Code", ""))
            status = int(
                exc.response.get(
                    "ResponseMetadata",
                    {},
                ).get("HTTPStatusCode", 0)
                or 0
            )
            if (
                code in _TRANSIENT_CODES
                or status == 429
                or status >= 500
            ):
                raise ArtifactBackendUnavailable(
                    "S3 backend 暂时不可用"
                ) from exc
            raise ArtifactStorageError(
                "S3 backend 请求失败"
            ) from exc

        raise ArtifactStorageError(
            "S3 SDK 调用失败"
        ) from exc

    def ensure_ready(self) -> None:
        try:
            self.client.head_bucket(
                Bucket=self.bucket
            )
            return
        except ClientError as exc:
            status = int(
                exc.response.get(
                    "ResponseMetadata",
                    {},
                ).get("HTTPStatusCode", 0)
                or 0
            )
            code = str(
                exc.response.get(
                    "Error",
                    {},
                ).get("Code", "")
            )
            missing = (
                status == 404
                or code in {
                    "404",
                    "NoSuchBucket",
                    "NotFound",
                }
            )
            if not (
                missing
                and self.auto_create_bucket
            ):
                self._raise_backend(exc)
        except BotoCoreError as exc:
            self._raise_backend(exc)

        create_kwargs = {
            "Bucket": self.bucket,
        }
        if self.region != "us-east-1":
            create_kwargs[
                "CreateBucketConfiguration"
            ] = {
                "LocationConstraint": (
                    self.region
                )
            }

        try:
            self.client.create_bucket(
                **create_kwargs
            )
        except (
            ClientError,
            BotoCoreError,
        ) as exc:
            self._raise_backend(exc)

    def stat(
        self,
        object_key: str,
    ) -> BlobStat | None:
        key = self._key(object_key)
        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=key,
            )
        except ClientError as exc:
            code = str(
                exc.response.get(
                    "Error",
                    {},
                ).get("Code", "")
            )
            status = int(
                exc.response.get(
                    "ResponseMetadata",
                    {},
                ).get("HTTPStatusCode", 0)
                or 0
            )
            if (
                code in _NOT_FOUND_CODES
                or status == 404
            ):
                return None
            self._raise_backend(exc)
        except BotoCoreError as exc:
            self._raise_backend(exc)

        metadata = response.get(
            "Metadata",
            {},
        )
        sha256 = str(
            metadata.get("sha256", "")
        )
        if not sha256:
            raise ArtifactIntegrityError(
                "S3 对象缺少 sha256 metadata"
            )
        return BlobStat(
            backend=self.backend_name,
            object_key=object_key,
            size_bytes=int(
                response["ContentLength"]
            ),
            sha256=sha256,
            etag=str(
                response.get("ETag", "")
            ).strip('"')
            or None,
            version_id=response.get(
                "VersionId"
            ),
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
        source = source_path.resolve()
        if not source.is_file():
            raise ArtifactNotFoundError(
                "待发布 Artifact 文件不存在"
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
                    "已有 S3 Blob 与目标内容不一致"
                )
            return existing

        key = self._key(object_key)
        try:
            self.client.upload_file(
                str(source),
                self.bucket,
                key,
                ExtraArgs={
                    "ContentType": media_type,
                    "Metadata": {
                        "sha256": expected_sha256,
                        "size-bytes": str(
                            expected_size
                        ),
                    },
                },
            )
        except (
            ClientError,
            BotoCoreError,
        ) as exc:
            self._raise_backend(exc)

        stored = self.stat(object_key)
        if stored is None:
            raise ArtifactBackendUnavailable(
                "S3 上传完成后对象仍不可见"
            )
        if (
            stored.sha256 != expected_sha256
            or stored.size_bytes != expected_size
        ):
            raise ArtifactIntegrityError(
                "S3 上传后完整性校验失败"
            )
        return stored

    def open(
        self,
        object_key: str,
    ) -> OpenedBlob:
        key = self._key(object_key)
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=key,
            )
        except ClientError as exc:
            code = str(
                exc.response.get(
                    "Error",
                    {},
                ).get("Code", "")
            )
            if code in _NOT_FOUND_CODES:
                raise ArtifactNotFoundError(
                    "Artifact Blob 不存在"
                ) from exc
            self._raise_backend(exc)
        except BotoCoreError as exc:
            self._raise_backend(exc)

        metadata = response.get(
            "Metadata",
            {},
        )
        stat = BlobStat(
            backend=self.backend_name,
            object_key=object_key,
            size_bytes=int(
                response["ContentLength"]
            ),
            sha256=str(
                metadata.get("sha256", "")
            ),
            etag=str(
                response.get("ETag", "")
            ).strip('"')
            or None,
            version_id=response.get(
                "VersionId"
            ),
        )
        if not stat.sha256:
            response["Body"].close()
            raise ArtifactIntegrityError(
                "S3 下载对象缺少 sha256 metadata"
            )
        return OpenedBlob(
            stat=stat,
            body=response["Body"],
        )