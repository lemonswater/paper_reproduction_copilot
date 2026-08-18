from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import settings
from app.paper.extraction_cache import (
    build_section_cache_key,
    load_valid_section_cache,
    section_cache_relative_path,
    write_section_cache,
)
from app.paper.schemas import SectionChunk, SectionExtractionDraft
from app.tools.artifact_tools import create_run_layout


def _chunk() -> SectionChunk:
    return SectionChunk(
        chunk_id="sec-impl-c000-abc123",
        section_id="sec-impl",
        section_title="Implementation Details",
        section_kind="implementation",
        page_start=14,
        page_end=14,
        block_ids=["p014-b0001"],
        text="[p014-b0001][page 14] We train for 35 epochs.",
        content_hash="chunk-content-hash",
    )


def _extraction() -> SectionExtractionDraft:
    return SectionExtractionDraft(
        section_id="sec-impl",
        chunk_id="sec-impl-c000-abc123",
        summary="The paper provides implementation details.",
    )


@pytest.fixture
def cache_state(tmp_path: Path, monkeypatch) -> dict:
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(settings, "runs_dir", runs_dir)
    layout = create_run_layout("paper-cache-test")
    return {
        "run_id": "paper-cache-test",
        "run_dir": layout["run_root"],
        "output_files": [],
        "artifact_records": [],
        "stage_errors": [],
    }


def _cache_key(chunk: SectionChunk) -> str:
    return build_section_cache_key(
        source_sha256="paper-source-hash",
        chunk=chunk,
        prompt_version="phase18-v1",
        schema_version="phase18-v1",
        model_name="test-model",
        method="json_schema",
        strict=True,
    )


def _write(cache_state: dict, chunk: SectionChunk):
    return write_section_cache(
        state=cache_state,
        chunk=chunk,
        cache_key=_cache_key(chunk),
        prompt_version="phase18-v1",
        schema_version="phase18-v1",
        model_name="test-model",
        method="json_schema",
        strict=True,
        extraction=_extraction(),
    )


def _load(
    cache_state: dict,
    chunk: SectionChunk,
    *,
    expected_cache_key: str | None = None,
) -> SectionExtractionDraft | None:
    return load_valid_section_cache(
        state=cache_state,
        chunk=chunk,
        expected_cache_key=expected_cache_key or _cache_key(chunk),
        prompt_version="phase18-v1",
        schema_version="phase18-v1",
        model_name="test-model",
        method="json_schema",
        strict=True,
    )


def test_cache_round_trip_returns_valid_extraction(
    cache_state: dict,
) -> None:
    chunk = _chunk()

    path, record = _write(cache_state, chunk)
    loaded = _load(cache_state, chunk)

    assert path.is_file()
    assert record.relative_path == section_cache_relative_path(chunk)
    assert loaded == _extraction()


def test_cache_key_change_causes_miss(cache_state: dict) -> None:
    chunk = _chunk()
    _write(cache_state, chunk)

    loaded = _load(
        cache_state,
        chunk,
        expected_cache_key="0" * 64,
    )

    assert loaded is None


def test_corrupt_json_is_a_cache_miss(cache_state: dict) -> None:
    chunk = _chunk()
    path, _ = _write(cache_state, chunk)
    path.write_text("{not-json", encoding="utf-8")

    assert _load(cache_state, chunk) is None


def test_invalid_extraction_schema_is_a_cache_miss(
    cache_state: dict,
) -> None:
    chunk = _chunk()
    path, _ = _write(cache_state, chunk)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["extraction"].pop("summary")
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    assert _load(cache_state, chunk) is None


def test_write_rejects_mismatched_chunk_identity(
    cache_state: dict,
) -> None:
    chunk = _chunk()
    wrong = _extraction().model_copy(
        update={"chunk_id": "another-chunk"}
    )

    with pytest.raises(ValueError, match="chunk_id"):
        write_section_cache(
            state=cache_state,
            chunk=chunk,
            cache_key=_cache_key(chunk),
            prompt_version="phase18-v1",
            schema_version="phase18-v1",
            model_name="test-model",
            method="json_schema",
            strict=True,
            extraction=wrong,
        )


def test_unsafe_chunk_id_is_rejected() -> None:
    unsafe = _chunk().model_copy(
        update={"chunk_id": "../../outside"}
    )

    with pytest.raises(ValueError, match="不安全"):
        section_cache_relative_path(unsafe)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("prompt_version", "phase18-v2"),
        ("schema_version", "phase18-v2"),
        ("model_name", "another-model"),
        ("method", "function_calling"),
        ("strict", False),
    ],
)
def test_cache_key_covers_extraction_configuration(
    field: str,
    value: object,
) -> None:
    chunk = _chunk()
    base = {
        "source_sha256": "paper-source-hash",
        "chunk": chunk,
        "prompt_version": "phase18-v1",
        "schema_version": "phase18-v1",
        "model_name": "test-model",
        "method": "json_schema",
        "strict": True,
    }
    original = build_section_cache_key(**base)
    changed = build_section_cache_key(
        **{**base, field: value}
    )

    assert changed != original