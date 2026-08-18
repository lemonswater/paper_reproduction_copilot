from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.research_browser.catalog import LoadedResearchPolicy
from app.research_browser.errors import (
    ResearchBrowserDisabled,
    ResearchConflict,
    ResearchIntegrityError,
    ResearchResourceCandidateRejected,
    ResearchSynthesisRejected,
)
from app.research_browser.identity import (
    request_sha256,
    sha256_value,
    stable_id,
    without_hash,
)
from app.research_browser.repository import SqliteResearchRepository
from app.research_browser.schemas import (
    ResearchEvidenceDraft,
    ResearchEvidencePack,
    ResearchReport,
    ResearchRequest,
    ResearchResourceSelection,
)
from app.research_browser.synthesis import ResearchSynthesizer
from app.resources.schemas import ResourceRequest
from app.resources.service import ResourceService
from app.secrets.redaction import SecretRedactor
from app.skills.registry import SkillRegistry
from app.skills.schemas import (
    SkillInvocationContext,
    SkillInvocationRequest,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchBrowserService:
    def __init__(
        self,
        *,
        enabled: bool,
        repository: SqliteResearchRepository,
        policy: LoadedResearchPolicy,
        skills: SkillRegistry,
        synthesizer: ResearchSynthesizer,
        redactor: SecretRedactor,
        resource_service: ResourceService,
        workspace_root: str,
        run_root: str,
        lease_seconds: int = 180,
    ) -> None:
        self.enabled = enabled
        self.repository = repository
        self.policy = policy
        self.skills = skills
        self.synthesizer = synthesizer
        self.redactor = redactor
        self.resource_service = resource_service
        self.workspace_root = workspace_root
        self.run_root = run_root
        self.lease_seconds = lease_seconds
        self.repository.initialize()

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise ResearchBrowserDisabled("RESEARCH_BROWSER_DISABLED")

    def submit(
        self,
        *,
        request: ResearchRequest,
        idempotency_key: str,
        actor: str,
    ):
        self._require_enabled()
        key = idempotency_key.strip()
        if not key or len(key) > 300:
            raise ValueError("idempotency_key 长度必须为 1..300")

        # Query/Purpose 在进入数据库、Search Provider 和 Prompt 前统一脱敏。
        normalized = ResearchRequest.model_validate(
            {
                **request.model_dump(mode="python"),
                "query": self.redactor.redact_text(
                    request.query,
                    max_chars=400,
                ),
                "purpose": self.redactor.redact_text(
                    request.purpose,
                    max_chars=500,
                ),
            }
        )
        # 只做范围校验；真正网络打开时仍会逐 URL、DNS、redirect 校验。
        self.policy.effective_hosts(normalized)
        digest = request_sha256(normalized)
        session_id = f"research_{uuid4().hex[:24]}"
        record, _created = self.repository.submit(
            session_id=session_id,
            idempotency_key=key,
            request=normalized,
            request_sha256=digest,
            policy_sha256=self.policy.policy_sha256,
            actor=actor,
        )
        return record

    def run(
        self,
        *,
        session_id: str,
        expected_version: int,
        actor: str,
    ):
        self._require_enabled()
        current = self.repository.get(session_id)
        if current.policy_sha256 != self.policy.policy_sha256:
            # Policy 更新后不能继续执行旧请求，避免审计记录与真实边界不一致。
            raise ResearchConflict("RESEARCH_POLICY_STALE")
        if current.request_sha256 != request_sha256(current.request):
            raise ResearchIntegrityError("RESEARCH_REQUEST_HASH_INVALID")
        lease_token = f"rlease_{uuid4().hex}"
        running = self.repository.start(
            session_id=session_id,
            expected_version=expected_version,
            lease_token=lease_token,
            lease_seconds=self.lease_seconds,
            actor=actor,
        )
        try:
            bound = self.skills.get("restricted_web_research")
            result = self.skills.invoke(
                request=SkillInvocationRequest(
                    skill_id="restricted_web_research",
                    skill_version=bound.package.manifest.skill_version,
                    expected_skill_sha256=bound.skill_sha256,
                    input_payload={
                        "request": running.request.model_dump(mode="json")
                    },
                ),
                context=SkillInvocationContext(
                    actor=actor,
                    request_id=f"research-run:{session_id}:{running.attempt_count}",
                    job_id=running.request.job_id,
                    workspace_root=self.workspace_root,
                    run_root=self.run_root,
                    granted_capabilities=["network.read.research"],
                ),
            )
            if result.failure is not None:
                return self.repository.fail(
                    session_id=session_id,
                    lease_token=lease_token,
                    error_code=result.failure.code,
                    retryable=result.failure.retryable,
                    actor=actor,
                )
            evidence = ResearchEvidenceDraft.model_validate(
                (result.output or {})["evidence"]
            )
            try:
                report = self.synthesizer.synthesize(
                    request=running.request,
                    evidence=evidence,
                )
            except ResearchSynthesisRejected:
                # 网络 Evidence 仍可审阅；模型引用伪造不会让它们丢失。
                report = ResearchReport(
                    synthesis_status="evidence_only",
                    answer="外部证据已保存，但模型返回了无效引用，综合结果已拒绝。",
                    citations=evidence.citations[:8],
                    resource_candidates=[],
                )

            pack_id = stable_id(
                "rpack",
                {
                    "session_id": session_id,
                    "request_sha256": running.request_sha256,
                    "snapshots": [
                        item.snapshot_id for item in evidence.snapshots
                    ],
                },
            )
            draft_pack = ResearchEvidencePack(
                pack_id=pack_id,
                session_id=session_id,
                request_sha256=running.request_sha256,
                policy_sha256=running.policy_sha256,
                search_hits=evidence.search_hits,
                snapshots=evidence.snapshots,
                citations=evidence.citations,
                resource_candidates=evidence.resource_candidates,
                report=report,
                pack_sha256="0" * 64,
                created_at=utc_now(),
            )
            pack = draft_pack.model_copy(
                update={
                    "pack_sha256": sha256_value(
                        without_hash(draft_pack, "pack_sha256")
                    )
                }
            )
            return self.repository.complete(
                session_id=session_id,
                lease_token=lease_token,
                pack=pack,
                actor=actor,
            )
        except Exception as exc:
            # 只保存异常类型映射后的稳定码，不保存网页/Provider message。
            code = f"RESEARCH_{type(exc).__name__.upper()}"[:100]
            retryable = type(exc).__name__ in {
                "ResearchTransportUnavailable",
                "TimeoutError",
                "ConnectionError",
            }
            return self.repository.fail(
                session_id=session_id,
                lease_token=lease_token,
                error_code=code,
                retryable=retryable,
                actor=actor,
            )

    def get(self, session_id: str):
        return self.repository.get(session_id)

    def get_pack(self, session_id: str) -> ResearchEvidencePack:
        return self.repository.get_pack(session_id)

    def cancel(self, *, session_id: str, expected_version: int, actor: str):
        return self.repository.cancel(
            session_id=session_id,
            expected_version=expected_version,
            actor=actor,
        )

    def events(
        self,
        session_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ):
        return self.repository.list_events(
            session_id,
            after_event_id=after_event_id,
            limit=limit,
        )

    def reconcile(self, *, actor: str) -> int:
        return self.repository.requeue_expired(
            now=datetime.now(timezone.utc),
            actor=actor,
        )

    def submit_resource_candidate(
        self,
        *,
        session_id: str,
        selection: ResearchResourceSelection,
        actor: str,
    ):
        self._require_enabled()
        pack = self.repository.get_pack(session_id)
        if pack.pack_sha256 != selection.expected_pack_sha256:
            raise ResearchConflict("RESEARCH_RESOURCE_PACK_STALE")
        candidate = next(
            (
                item for item in pack.resource_candidates
                if item.candidate_id == selection.candidate_id
            ),
            None,
        )
        if candidate is None:
            raise ResearchResourceCandidateRejected(
                "RESEARCH_RESOURCE_CANDIDATE_NOT_FOUND"
            )
        expected_candidate_hash = sha256_value(
            without_hash(candidate, "candidate_sha256")
        )
        if (
            candidate.candidate_sha256 != expected_candidate_hash
            or selection.candidate_sha256 != expected_candidate_hash
        ):
            raise ResearchConflict("RESEARCH_RESOURCE_CANDIDATE_STALE")

        resource_request = ResourceRequest(
            kind=candidate.kind,
            source_url=candidate.source_url_sanitized,
            expected_sha256=candidate.expected_sha256,
            expected_git_commit=candidate.expected_git_commit,
            purpose=self.redactor.redact_text(selection.purpose, max_chars=500),
        )
        # 由服务端身份派生，换一个 HTTP Idempotency-Key 也不会创建第二个 Resource。
        bridge_key = f"research-resource:{session_id}:{candidate.candidate_id}"
        resource, _created = self.resource_service.submit(
            request=resource_request,
            idempotency_key=bridge_key,
        )
        linked_id = self.repository.record_resource_link(
            session_id=session_id,
            candidate_id=candidate.candidate_id,
            candidate_sha256=candidate.candidate_sha256,
            pack_sha256=pack.pack_sha256,
            idempotency_key=bridge_key,
            resource_id=resource.resource_id,
        )
        if linked_id != resource.resource_id:
            raise ResearchConflict("RESEARCH_RESOURCE_LINK_MISMATCH")
        # 返回的 Resource 仍应是 awaiting_approval；这里绝不调用 approve。
        if resource.status != "awaiting_approval":
            raise ResearchConflict("RESEARCH_RESOURCE_STATUS_UNEXPECTED")
        return resource
