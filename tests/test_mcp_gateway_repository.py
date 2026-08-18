from __future__ import annotations

import tempfile
from pathlib import Path

from app.mcp_gateway.identity import build_evidence_item, compute_pack_hash, sha256_value, stable_id
from app.mcp_gateway.repository import SqliteMcpEvidenceRepository
from app.mcp_gateway.schemas import McpCallRecord, McpEvidencePack


def _make_pack(job_id: str = "job_test") -> McpEvidencePack:
    item = build_evidence_item(server_id="mcpserver_scholar_local", binding_id="mcpbind_scholar_search_v1", title="PSTNet", source_uri="https://example.org/pstnet", excerpt="Point spatio-temporal evidence.", locator="fixture:paper:1")
    pack_identity = {"job_id": job_id, "server_id": "mcpserver_scholar_local", "binding_id": "mcpbind_scholar_search_v1", "profile_sha256": "a" * 64, "request_sha256": "b" * 64, "result_sha256": "c" * 64}
    draft = McpEvidencePack(pack_id=stable_id("mcppack", pack_identity), job_id=job_id, server_id="mcpserver_scholar_local", binding_id="mcpbind_scholar_search_v1", profile_sha256="a" * 64, input_schema_sha256="d" * 64, output_schema_sha256="e" * 64, request_sha256="b" * 64, result_sha256="c" * 64, created_at="2026-01-01T00:00:00+00:00", items=[item], truncated=False, pack_sha256="0" * 64)
    return draft.model_copy(update={"pack_sha256": compute_pack_hash(draft)})


def _make_call_record(pack: McpEvidencePack, status: str = "succeeded") -> McpCallRecord:
    return McpCallRecord(call_id=stable_id("mcpcall", {"job_id": pack.job_id, "pack_id": pack.pack_id}), job_id=pack.job_id, server_id=pack.server_id, binding_id=pack.binding_id, profile_sha256=pack.profile_sha256, request_sha256=pack.request_sha256, result_sha256=pack.result_sha256 if status == "succeeded" else None, status=status, error_code=None if status == "succeeded" else "MCP_REMOTE_TOOL_FAILED", protocol_version="2026-07-28" if status == "succeeded" else None, started_at="2026-01-01T00:00:00+00:00", finished_at="2026-01-01T00:00:01+00:00", duration_ms=1000.0)


def test_put_and_get_success() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteMcpEvidenceRepository(Path(tmp) / "mcp.db")
        repo.initialize()
        pack = _make_pack()
        record = _make_call_record(pack)
        repo.put_success(pack=pack, record=record)
        fetched = repo.get_pack(job_id=pack.job_id, pack_id=pack.pack_id)
        assert fetched.pack_id == pack.pack_id
        assert fetched.items[0].title == "PSTNet"
        packs = repo.list_packs_for_job(job_id=pack.job_id)
        assert len(packs) == 1
        calls = repo.list_calls_for_job(job_id=pack.job_id)
        assert len(calls) == 1
        assert calls[0].status == "succeeded"


def test_put_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteMcpEvidenceRepository(Path(tmp) / "mcp.db")
        repo.initialize()
        pack = _make_pack()
        record = _make_call_record(pack, status="failed")
        repo.put_failure(record)
        calls = repo.list_calls_for_job(job_id=pack.job_id)
        assert len(calls) == 1
        assert calls[0].status == "failed"


def test_delete_for_job() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteMcpEvidenceRepository(Path(tmp) / "mcp.db")
        repo.initialize()
        pack = _make_pack()
        record = _make_call_record(pack)
        repo.put_success(pack=pack, record=record)
        count = repo.delete_for_job(pack.job_id)
        assert count == 2
        assert repo.list_packs_for_job(job_id=pack.job_id) == []
