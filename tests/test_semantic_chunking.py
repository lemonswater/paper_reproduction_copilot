from __future__ import annotations

from app.retrieval.chunking import (
    build_semantic_chunks,
)
from app.retrieval.indexer import (
    build_repository_index,
)


def test_semantic_chunks_use_symbol_windows_and_redact(
    tmp_path,
):
    source = tmp_path / "operator.py"
    source.write_text(
        "\n".join(
            [
                'API_KEY = "do-not-upload-this"',
                "",
                "class LocalMixer:",
                "    def forward(self, frames):",
                "        groups = radius_neighbors(frames)",
                "        return weighted_pool(groups)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )

    chunks, manifest = build_semantic_chunks(
        repo_path=tmp_path,
        index=index,
        chunk_policy_version="test-v1",
        max_lines=8,
        overlap_lines=2,
        max_chunks=30,
    )

    assert chunks
    assert any(
        chunk.symbol == "LocalMixer.forward"
        for chunk in chunks
    )
    assert all(
        "do-not-upload-this"
        not in chunk.embedding_text
        for chunk in chunks
    )
    assert any(
        "<REDACTED>" in chunk.embedding_text
        for chunk in chunks
    )
    assert manifest.redacted_line_count == 1
    payload = manifest.model_dump(
        mode="json"
    )
    assert "embedding_text" not in str(payload)


def test_private_key_file_is_skipped(
    tmp_path,
):
    (tmp_path / "unsafe.py").write_text(
        "\n".join(
            [
                "-----BEGIN PRIVATE KEY-----",
                "private-material",
                "-----END PRIVATE KEY-----",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "safe.py").write_text(
        "def useful_operator(x):\n    return x\n",
        encoding="utf-8",
    )
    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )

    chunks, manifest = build_semantic_chunks(
        repo_path=tmp_path,
        index=index,
        chunk_policy_version="test-v1",
        max_lines=8,
        overlap_lines=0,
    )

    assert {
        chunk.file_path
        for chunk in chunks
    } == {"safe.py"}
    assert (
        "PRIVATE_KEY_FILE_SKIPPED:unsafe.py"
        in manifest.warnings
    )


def test_stale_source_is_not_embedded(
    tmp_path,
):
    path = tmp_path / "operator.py"
    path.write_text(
        "def original(x):\n    return x\n",
        encoding="utf-8",
    )
    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )
    path.write_text(
        "def changed(x):\n    return x + 1\n",
        encoding="utf-8",
    )

    chunks, manifest = build_semantic_chunks(
        repo_path=tmp_path,
        index=index,
        chunk_policy_version="test-v1",
    )

    assert chunks == []
    assert (
        "STALE_SOURCE_SKIPPED:operator.py"
        in manifest.warnings
    )