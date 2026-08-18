from __future__ import annotations

import hashlib

import pytest

from app.storage.errors import (
    ArtifactIntegrityError,
)
from app.storage.local_blob_store import (
    LocalBlobStore,
)


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_local_blob_put_is_idempotent(
    tmp_path,
) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"artifact")
    digest = _digest(b"artifact")
    store = LocalBlobStore(
        tmp_path / "blob-store"
    )

    first = store.put_file(
        object_key=f"sha256/{digest}",
        source_path=source,
        expected_sha256=digest,
        expected_size=8,
        media_type="application/octet-stream",
    )
    second = store.put_file(
        object_key=f"sha256/{digest}",
        source_path=source,
        expected_sha256=digest,
        expected_size=8,
        media_type="application/octet-stream",
    )

    assert first == second
    opened = store.open(
        f"sha256/{digest}"
    )
    try:
        assert opened.body.read() == b"artifact"
    finally:
        opened.body.close()


def test_local_blob_rejects_path_escape(
    tmp_path,
) -> None:
    store = LocalBlobStore(
        tmp_path / "blob-store"
    )

    with pytest.raises(
        ArtifactIntegrityError,
        match="object_key",
    ):
        store.stat("../outside")


def test_local_blob_rejects_source_hash_change(
    tmp_path,
) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"changed")
    store = LocalBlobStore(
        tmp_path / "blob-store"
    )

    with pytest.raises(
        ArtifactIntegrityError,
        match="SHA-256",
    ):
        store.put_file(
            object_key="sha256/expected",
            source_path=source,
            expected_sha256=_digest(b"old"),
            expected_size=len(b"changed"),
            media_type=(
                "application/octet-stream"
            ),
        )