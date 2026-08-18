from __future__ import annotations

import hashlib
from io import BytesIO

import pytest

pytest.importorskip("boto3")

from botocore.exceptions import (
    EndpointConnectionError,
)

from app.storage.errors import (
    ArtifactBackendUnavailable,
)
from app.storage.s3_blob_store import (
    S3BlobStore,
)


class FakeS3:
    def __init__(self):
        self.objects = {}

    def head_bucket(self, *, Bucket):
        return {}

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            error = {
                "Error": {"Code": "404"},
                "ResponseMetadata": {
                    "HTTPStatusCode": 404
                },
            }
            from botocore.exceptions import (
                ClientError,
            )

            raise ClientError(
                error,
                "HeadObject",
            )
        value = self.objects[Key]
        return {
            "ContentLength": len(
                value["body"]
            ),
            "Metadata": value["metadata"],
            "ETag": '"fake-etag"',
        }

    def upload_file(
        self,
        filename,
        bucket,
        key,
        ExtraArgs,
    ):
        with open(filename, "rb") as file_obj:
            body = file_obj.read()
        self.objects[key] = {
            "body": body,
            "metadata": ExtraArgs["Metadata"],
        }

    def get_object(self, *, Bucket, Key):
        value = self.objects[Key]
        return {
            "Body": BytesIO(value["body"]),
            "ContentLength": len(
                value["body"]
            ),
            "Metadata": value["metadata"],
            "ETag": '"fake-etag"',
        }


class UnavailableS3(FakeS3):
    def head_object(self, *, Bucket, Key):
        del Bucket, Key
        raise EndpointConnectionError(
            endpoint_url=(
                "http://127.0.0.1:1"
            )
        )


def _store(client) -> S3BlobStore:
    return S3BlobStore(
        bucket="test",
        prefix="copilot",
        endpoint_url=None,
        region="us-east-1",
        force_path_style=True,
        auto_create_bucket=False,
        connect_timeout=1,
        read_timeout=1,
        max_attempts=1,
        client=client,
    )


def test_s3_store_round_trip(
    tmp_path,
) -> None:
    source = tmp_path / "artifact.bin"
    source.write_bytes(b"s3 artifact")

    digest = hashlib.sha256(
        b"s3 artifact"
    ).hexdigest()
    fake = FakeS3()
    store = _store(fake)

    stored = store.put_file(
        object_key=f"sha256/{digest}",
        source_path=source,
        expected_sha256=digest,
        expected_size=len(b"s3 artifact"),
        media_type=(
            "application/octet-stream"
        ),
    )
    opened = store.open(
        f"sha256/{digest}"
    )
    try:
        assert (
            opened.body.read()
            == b"s3 artifact"
        )
    finally:
        opened.body.close()

    assert stored.sha256 == digest
    assert (
        "copilot/sha256/"
        in next(iter(fake.objects))
    )


def test_s3_network_error_is_retryable() -> None:
    store = _store(UnavailableS3())

    with pytest.raises(
        ArtifactBackendUnavailable
    ):
        store.stat("sha256/missing")