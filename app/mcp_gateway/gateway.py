from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from app.mcp_gateway.ports import McpClientPort
from app.mcp_gateway.errors import (
    McpGatewayError,
    McpStructuredOutputInvalid,
)
from app.mcp_gateway.identity import (
    build_evidence_item,
    compute_pack_hash,
    profile_sha256,
    sha256_value,
    stable_id,
)
from app.mcp_gateway.repository import SqliteMcpEvidenceRepository
from app.mcp_gateway.schemas import (
    McpCallRecord,
    McpEvidencePack,
    McpGatewayPolicy,
    McpSearchInput,
    RemotePaperSearchResult,
)

try:
    from app.research_browser.identity import canonicalize_research_url
except ImportError:
    def canonicalize_research_url(uri: str) -> str:
        return uri


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReadOnlyMcpEvidenceGateway:
    """Adapt a pinned MCP Tool into project-persistent, citable evidence."""

    ALIAS = "search_external_paper_evidence"

    def __init__(self, *, policy: McpGatewayPolicy, client: McpClientPort, repository: SqliteMcpEvidenceRepository) -> None:
        selected = policy.enabled_binding(self.ALIAS)
        if selected is None:
            raise ValueError("MCP search binding is not enabled")
        self.policy = policy
        self.profile, self.binding = selected
        self.client = client
        self.repository = repository

    @property
    def authority_fingerprint(self) -> str:
        return profile_sha256(profile=self.profile, binding=self.binding)

    def search(self, *, job_id: str, request_id: str, payload: McpSearchInput) -> McpEvidencePack:
        started_at = utc_now()
        started = perf_counter()
        arguments = payload.model_dump(mode="json")
        request_sha256 = sha256_value(arguments)
        call_id = f"mcpcall_{uuid4().hex[:24]}"

        try:
            raw = self.client.call_pinned_tool(profile=self.profile, binding=self.binding, arguments=arguments)
            parsed = RemotePaperSearchResult.model_validate(raw.structured_content)

            items = []
            for remote in parsed.items[: payload.limit]:
                source_uri = canonicalize_research_url(remote.source_uri)
                title = " ".join(remote.title.replace("\x00", " ").split())
                excerpt = " ".join(remote.excerpt.replace("\x00", " ").split())
                locator = " ".join(remote.locator.replace("\x00", " ").split())
                items.append(build_evidence_item(server_id=self.profile.server_id, binding_id=self.binding.binding_id, title=title, source_uri=source_uri, excerpt=excerpt, locator=locator))

            created_at = utc_now()
            pack_identity = {
                "job_id": job_id,
                "server_id": self.profile.server_id,
                "binding_id": self.binding.binding_id,
                "profile_sha256": self.authority_fingerprint,
                "request_sha256": request_sha256,
                "result_sha256": raw.result_sha256,
            }
            draft = McpEvidencePack(
                pack_id=stable_id("mcppack", pack_identity),
                job_id=job_id,
                server_id=self.profile.server_id,
                binding_id=self.binding.binding_id,
                profile_sha256=self.authority_fingerprint,
                input_schema_sha256=raw.observed_tool.input_schema_sha256,
                output_schema_sha256=raw.observed_tool.output_schema_sha256,
                request_sha256=request_sha256,
                result_sha256=raw.result_sha256,
                created_at=created_at,
                items=items,
                truncated=parsed.truncated or len(parsed.items) > payload.limit,
                pack_sha256="0" * 64,
            )
            pack = draft.model_copy(update={"pack_sha256": compute_pack_hash(draft)})

            record = McpCallRecord(
                call_id=call_id, job_id=job_id, server_id=self.profile.server_id, binding_id=self.binding.binding_id,
                profile_sha256=self.authority_fingerprint, request_sha256=request_sha256, result_sha256=raw.result_sha256,
                status="succeeded", protocol_version=raw.observed_tool.protocol_version,
                started_at=started_at, finished_at=utc_now(), duration_ms=(perf_counter() - started) * 1000,
            )
            self.repository.put_success(pack=pack, record=record)
            return pack
        except Exception as exc:
            if isinstance(exc, McpGatewayError):
                error_code = exc.code
            else:
                error_code = "MCP_STRUCTURED_OUTPUT_INVALID"
            record = McpCallRecord(
                call_id=call_id, job_id=job_id, server_id=self.profile.server_id, binding_id=self.binding.binding_id,
                profile_sha256=self.authority_fingerprint, request_sha256=request_sha256,
                status="failed", error_code=error_code,
                started_at=started_at, finished_at=utc_now(), duration_ms=(perf_counter() - started) * 1000,
            )
            self.repository.put_failure(record)
            if isinstance(exc, McpGatewayError):
                raise
            raise McpStructuredOutputInvalid("MCP evidence normalization failed") from exc
