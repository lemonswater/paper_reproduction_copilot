from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.auth import require_api_auth
from app.mcp_gateway.repository import SqliteMcpEvidenceRepository
from app.mcp_gateway.schemas import McpEvidencePack


router = APIRouter(prefix="/v1/jobs/{job_id}/mcp-evidence")
Actor = Annotated[str, Depends(require_api_auth)]


def repository_dependency(request: Request) -> SqliteMcpEvidenceRepository:
    repository = getattr(request.app.state, "mcp_evidence_repository", None)
    if repository is None:
        raise HTTPException(status_code=404, detail={"code": "MCP_GATEWAY_DISABLED", "message": "MCP Gateway not enabled"})
    return repository


RepositoryDependency = Annotated[SqliteMcpEvidenceRepository, Depends(repository_dependency)]


@router.get("", response_model=list[McpEvidencePack])
def list_mcp_evidence(job_id: str, _actor: Actor, repository: RepositoryDependency, limit: int = Query(default=20, ge=1, le=100)) -> list[McpEvidencePack]:
    return repository.list_packs_for_job(job_id=job_id, limit=limit)


@router.get("/{pack_id}", response_model=McpEvidencePack)
def get_mcp_evidence(job_id: str, pack_id: str, _actor: Actor, repository: RepositoryDependency) -> McpEvidencePack:
    try:
        return repository.get_pack(job_id=job_id, pack_id=pack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "MCP_EVIDENCE_NOT_FOUND", "message": "MCP Evidence Pack not found"}) from exc
