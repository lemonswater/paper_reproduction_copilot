from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from pydantic import ValidationError

from app.authority.evidence import (
    compute_execution_verification_hash,
)
from app.authority.schemas import ExecutionVerificationRecord
from app.failure_memory.errors import (
    FailureCaseConflictError,
    FailureCaseIntegrityError,
)
from app.failure_memory.evidence_reader import FailureEvidenceReader
from app.failure_memory.identity import (
    build_failure_signature,
    canonical_sha256,
    case_id_for_source,
    compute_case_hash,
)
from app.failure_memory.ports import FailureCaseRepository
from app.failure_memory.retrieval import FailureCaseRetriever
from app.failure_memory.schemas import (
    FailureCaseConfirmRequest,
    FailureCaseCreateRequest,
    FailureCaseDeprecateRequest,
    FailureCaseMutationResponse,
    FailureCaseRecord,
    FailureCaseVerifyRequest,
    FailureEnvironmentIdentity,
    FailureQuery,
    FailureRemedy,
    FailureRunVerification,
    HumanConfirmation,
)
from app.observability.redaction import sanitize_error_message
from app.run_evidence.reader import VerifiedRunEvidenceReader
from app.schemas import DebugReport


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_idempotency_key(value: str) -> str:
    key = value.strip()
    if not key or len(key) > 300:
        raise ValueError("Idempotency-Key 长度必须为 1..300")
    return key


def _operation_key(kind: str, idempotency_key: str) -> str:
    return f"phase45:{kind}:{_required_idempotency_key(idempotency_key)}"


def _request_hash(value) -> str:
    return canonical_sha256(value.model_dump(mode="json"))


def _clean_text(value: object, *, limit: int) -> str:
    text = sanitize_error_message(value, max_chars=limit).strip()
    if not text:
        raise ValueError("Failure Case 文本脱敏后不能为空")
    return text


def _clean_items(values: list[str], *, limit: int) -> list[str]:
    return [
        _clean_text(item, limit=limit)
        for item in values[:12]
    ]


def _validated_case_with_hash(
    draft: FailureCaseRecord,
) -> FailureCaseRecord:
    """model_copy 不验证 update；状态迁移后必须完整重验 Schema。"""

    raw = draft.model_dump(mode="json")
    raw["case_hash"] = "0" * 64
    validated = FailureCaseRecord.model_validate(raw)
    raw["case_hash"] = compute_case_hash(validated)
    return FailureCaseRecord.model_validate(raw)


def _candidate_from_debug(
    debug_report: DebugReport | None,
    *,
    fallback_message: str,
) -> tuple[str, FailureRemedy]:
    if debug_report is None:
        return (
            _clean_text(fallback_message, limit=2000),
            FailureRemedy(
                kind="unknown",
                summary="当前候选缺少结构化 DebugReport，需要人工诊断。",
                steps=[],
                risks=["证据不足，不能直接执行修复。"],
            ),
        )

    causes = _clean_items(
        debug_report.most_likely_causes,
        limit=500,
    )
    fixes = _clean_items(
        debug_report.suggested_fixes,
        limit=500,
    )
    risks = _clean_items(debug_report.risks, limit=500)
    diagnosis = "；".join(causes) or _clean_text(
        fallback_message,
        limit=2000,
    )
    remedy_summary = (
        "；".join(fixes)
        or "DebugReport 没有给出可确认的修复方向。"
    )
    return (
        diagnosis[:2000],
        FailureRemedy(
            kind="unknown",
            summary=remedy_summary[:2000],
            steps=fixes,
            risks=risks,
        ),
    )


class FailureCaseService:
    def __init__(
        self,
        *,
        repository: FailureCaseRepository,
        evidence_reader: FailureEvidenceReader,
        verified_runs: VerifiedRunEvidenceReader,
        retriever: FailureCaseRetriever,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.repository = repository
        self.evidence_reader = evidence_reader
        self.verified_runs = verified_runs
        self.retriever = retriever
        self.clock = clock
        self.repository.initialize()

    def ping(self) -> None:
        self.repository.ping()

    def get(self, case_id: str) -> FailureCaseRecord:
        return self.repository.get(case_id)

    def list_cases(
        self,
        *,
        include_deprecated: bool = False,
        limit: int = 100,
    ) -> list[FailureCaseRecord]:
        return self.repository.list_records(
            include_deprecated=include_deprecated,
            limit=limit,
        )

    def create_candidate(
        self,
        *,
        request: FailureCaseCreateRequest,
        idempotency_key: str,
    ) -> FailureCaseMutationResponse:
        operation_key = _operation_key("create", idempotency_key)
        request_hash = _request_hash(request)
        replay = self.repository.find_replay(
            operation_key=operation_key,
            request_hash=request_hash,
        )
        if replay is not None:
            return FailureCaseMutationResponse(
                case=replay,
                replayed=True,
            )

        snapshot = self.evidence_reader.read(request.source_job_id)
        source = snapshot.source
        if source.job_version != request.expected_source_job_version:
            raise FailureCaseConflictError(
                "源 Job version 已变化，请刷新任务详情"
            )
        if source.run_manifest_sha256 != request.expected_run_manifest_sha256:
            raise FailureCaseConflictError(
                "源 run_manifest SHA-256 已变化"
            )
        if source.environment.execution_profile_fingerprint == "unknown":
            raise FailureCaseConflictError(
                "源 Run 缺少 Execution Profile fingerprint"
            )

        error_type = (
            snapshot.debug_report.error_type
            if snapshot.debug_report is not None
            else snapshot.stage_error.code.lower()
        )
        signature = build_failure_signature(
            stage_error=snapshot.stage_error,
            error_type=error_type,
            traceback_text=snapshot.traceback_text,
            repo_path=(
                snapshot.verified_run.workspace.source_paths.repo_path
                if snapshot.verified_run.workspace.source_paths is not None
                else None
            ),
        )
        diagnosis, remedy = _candidate_from_debug(
            snapshot.debug_report,
            fallback_message=snapshot.stage_error.message,
        )
        now = self.clock()
        draft = FailureCaseRecord(
            case_id=case_id_for_source(
                source_job_id=source.job_id,
                run_manifest_sha256=source.run_manifest_sha256,
                signature_sha256=signature.signature_sha256,
            ),
            case_hash="0" * 64,
            version=0,
            status="candidate",
            signature=signature,
            source=source,
            candidate_diagnosis=diagnosis,
            candidate_remedy=remedy,
            created_at=now,
            updated_at=now,
        )
        record = _validated_case_with_hash(draft)
        created = self.repository.create(
            record=record,
            operation_key=operation_key,
            request_hash=request_hash,
        )
        return FailureCaseMutationResponse(case=created)

    def confirm(
        self,
        *,
        case_id: str,
        request: FailureCaseConfirmRequest,
        idempotency_key: str,
        actor: str = "local-user",
    ) -> FailureCaseMutationResponse:
        operation_key = _operation_key("confirm", idempotency_key)
        request_hash = _request_hash(request)
        replay = self.repository.find_replay(
            operation_key=operation_key,
            request_hash=request_hash,
        )
        if replay is not None:
            return FailureCaseMutationResponse(
                case=replay,
                replayed=True,
            )

        current = self.repository.get(case_id)
        if current.status != "candidate":
            raise FailureCaseConflictError(
                "只有 candidate 可以进入 human_confirmed"
            )
        remedy = request.remedy.model_copy(
            update={
                "summary": _clean_text(
                    request.remedy.summary,
                    limit=2000,
                ),
                "steps": _clean_items(request.remedy.steps, limit=500),
                "risks": _clean_items(request.remedy.risks, limit=500),
            }
        )
        now = self.clock()
        confirmation = HumanConfirmation(
            actor=_clean_text(actor, limit=100),
            diagnosis_summary=_clean_text(
                request.diagnosis_summary,
                limit=2000,
            ),
            remedy=remedy,
            applicability_note=_clean_text(
                request.applicability_note,
                limit=1000,
            ),
            confirmed_at=now,
        )
        draft = current.model_copy(
            update={
                "version": current.version + 1,
                "status": "human_confirmed",
                "confirmation": confirmation,
                "updated_at": now,
                "case_hash": "0" * 64,
            }
        )
        updated = _validated_case_with_hash(draft)
        stored = self.repository.replace(
            record=updated,
            expected_version=request.expected_version,
            expected_case_hash=request.expected_case_hash,
            operation_key=operation_key,
            request_hash=request_hash,
        )
        return FailureCaseMutationResponse(case=stored)

    @staticmethod
    def _verified_child(
        *,
        current: FailureCaseRecord,
        verification_evidence,
        expected_manifest_sha256: str,
        verified_at: str,
    ) -> FailureRunVerification:
        child = verification_evidence.job
        manifest = verification_evidence.run_manifest
        artifact = verification_evidence.run_manifest_artifact
        if artifact.sha256 != expected_manifest_sha256:
            raise FailureCaseConflictError(
                "验证 Run manifest SHA-256 已变化"
            )

        derived = child.request.derived_run
        if derived is None:
            raise FailureCaseConflictError(
                "验证 Job 不是 Phase 39 派生 Run"
            )
        if derived.source.parent_job_id != current.source.job_id:
            raise FailureCaseConflictError(
                "验证 Job 不是从当前失败源派生"
            )
        if (
            derived.source.parent_run_manifest_sha256
            != current.source.run_manifest_sha256
        ):
            raise FailureCaseIntegrityError(
                "验证 Job 的父 Run identity 与 Failure Case 不一致"
            )

        raw_execution = manifest.get("execution")
        raw_verification = (
            raw_execution.get("verification")
            if isinstance(raw_execution, dict)
            else None
        )
        try:
            verification = ExecutionVerificationRecord.model_validate(
                raw_verification
            )
        except ValidationError as exc:
            raise FailureCaseIntegrityError(
                "验证 Run 缺少有效 ExecutionVerificationRecord"
            ) from exc
        if (
            compute_execution_verification_hash(verification)
            != verification.verification_sha256
        ):
            raise FailureCaseIntegrityError(
                "验证 Run 的 Execution Verification hash 无效"
            )
        if verification.verdict != "verified":
            raise FailureCaseConflictError(
                "验证 Run 的执行协议没有通过独立 Verifier"
            )
        if str(manifest.get("final_status")) != "succeeded":
            raise FailureCaseConflictError(
                "验证 Run 的业务 final_status 不是 succeeded"
            )

        raw_profile = manifest.get("execution_profile")
        fingerprint = (
            raw_profile.get("fingerprint")
            if isinstance(raw_profile, dict)
            else None
        )
        if not isinstance(fingerprint, str) or not fingerprint:
            raise FailureCaseIntegrityError(
                "验证 Run 缺少 Execution Profile fingerprint"
            )
        environment = FailureEnvironmentIdentity(
            execution_profile_id=child.request.execution_profile_id,
            execution_profile_fingerprint=fingerprint,
            execution_backend=child.requirements.execution_backend,
            repository_commit=(
                verification_evidence.workspace.repository.commit_sha
            ),
            repository_clean=(
                verification_evidence.workspace.repository.clean
            ),
        )
        return FailureRunVerification(
            job_id=child.job_id,
            run_id=child.run_id,
            run_manifest_artifact_id=artifact.artifact_id,
            run_manifest_sha256=artifact.sha256,
            proposal_id=derived.proposal_id,
            proposal_hash=derived.proposal_hash,
            execution_verification_id=verification.verification_id,
            execution_verification_sha256=(
                verification.verification_sha256
            ),
            environment=environment,
            verified_at=verified_at,
        )

    def verify(
        self,
        *,
        case_id: str,
        request: FailureCaseVerifyRequest,
        idempotency_key: str,
    ) -> FailureCaseMutationResponse:
        operation_key = _operation_key("verify", idempotency_key)
        request_hash = _request_hash(request)
        replay = self.repository.find_replay(
            operation_key=operation_key,
            request_hash=request_hash,
        )
        if replay is not None:
            return FailureCaseMutationResponse(
                case=replay,
                replayed=True,
            )

        current = self.repository.get(case_id)
        if current.status != "human_confirmed":
            raise FailureCaseConflictError(
                "只有 human_confirmed 可以进入 run_verified"
            )
        child_evidence = self.verified_runs.read(
            request.verification_job_id
        )
        now = self.clock()
        verification = self._verified_child(
            current=current,
            verification_evidence=child_evidence,
            expected_manifest_sha256=(
                request.expected_verification_manifest_sha256
            ),
            verified_at=now,
        )
        draft = current.model_copy(
            update={
                "version": current.version + 1,
                "status": "run_verified",
                "verification": verification,
                "updated_at": now,
                "case_hash": "0" * 64,
            }
        )
        updated = _validated_case_with_hash(draft)
        stored = self.repository.replace(
            record=updated,
            expected_version=request.expected_version,
            expected_case_hash=request.expected_case_hash,
            operation_key=operation_key,
            request_hash=request_hash,
        )
        return FailureCaseMutationResponse(case=stored)

    def deprecate(
        self,
        *,
        case_id: str,
        request: FailureCaseDeprecateRequest,
        idempotency_key: str,
    ) -> FailureCaseMutationResponse:
        operation_key = _operation_key("deprecate", idempotency_key)
        request_hash = _request_hash(request)
        replay = self.repository.find_replay(
            operation_key=operation_key,
            request_hash=request_hash,
        )
        if replay is not None:
            return FailureCaseMutationResponse(
                case=replay,
                replayed=True,
            )

        current = self.repository.get(case_id)
        if current.status == "deprecated":
            raise FailureCaseConflictError(
                "Deprecated Case 不允许再次变更"
            )
        now = self.clock()
        draft = current.model_copy(
            update={
                "version": current.version + 1,
                "status": "deprecated",
                "deprecation_reason": _clean_text(
                    request.reason,
                    limit=1000,
                ),
                "updated_at": now,
                "case_hash": "0" * 64,
            }
        )
        updated = _validated_case_with_hash(draft)
        stored = self.repository.replace(
            record=updated,
            expected_version=request.expected_version,
            expected_case_hash=request.expected_case_hash,
            operation_key=operation_key,
            request_hash=request_hash,
        )
        return FailureCaseMutationResponse(case=stored)

    def search_source_job(self, job_id: str):
        """管理 API 只允许按可信 Job 查询，不接收任意 traceback。"""

        snapshot = self.evidence_reader.read(job_id)
        error_type = (
            snapshot.debug_report.error_type
            if snapshot.debug_report is not None
            else snapshot.stage_error.code.lower()
        )
        signature = build_failure_signature(
            stage_error=snapshot.stage_error,
            error_type=error_type,
            traceback_text=snapshot.traceback_text,
            repo_path=(
                snapshot.verified_run.workspace.source_paths.repo_path
                if snapshot.verified_run.workspace.source_paths is not None
                else None
            ),
        )
        return self.retriever.search(
            FailureQuery(
                signature=signature,
                environment=snapshot.source.environment,
            )
        )
