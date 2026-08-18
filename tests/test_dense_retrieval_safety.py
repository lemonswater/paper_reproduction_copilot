from __future__ import annotations

import pytest

from app.config import settings
from app.nodes.code_search_node import (
    _dense_flags,
    _prepare_dense,
)
from app.retrieval.embedding_backend import (
    EmbeddingProviderError,
    validate_vectors,
)


def test_required_implies_dense_enabled():
    enabled, required = _dense_flags(
        {
            "enable_dense_retrieval": False,
            "dense_retrieval_required": True,
        }
    )

    assert enabled is True
    assert required is True


def test_remote_code_upload_requires_explicit_setting(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "allow_code_embedding_upload",
        False,
    )

    with pytest.raises(
        EmbeddingProviderError,
        match="ALLOW_CODE_EMBEDDING_UPLOAD=false",
    ):
        # Guard 在读取 index 或源码之前执行。
        _prepare_dense(
            repo_path="/unused",
            index=None,
        )


@pytest.mark.parametrize(
    "vector",
    [
        [float("nan"), 0.0],
        [float("inf"), 0.0],
        [],
    ],
)
def test_invalid_provider_vectors_are_rejected(
    vector,
):
    with pytest.raises(
        EmbeddingProviderError
    ):
        validate_vectors(
            [vector],
            expected_count=1,
        )