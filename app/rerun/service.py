# app/rerun/service.py
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from app.comparison.schemas import ComparisonReport
from app.execution.profile_store import get_execution_profile
from app.job_runtime.schemas import JobRecord, JobRequest
from app.job_runtime.service import JobService
from app.rerun.command_template import build_command_template
from app.rerun.errors import (
    RerunConflictError,
    RerunIntegrityError,
)
from app.rerun.identity import (
    proposal_hash,
    proposal_id_for_hash,
    sha256_value,
    validate_command_template_hash,
    validate_proposal_hash,
)
from app.rerun.repository import SqliteRerunRepository
from app.rerun.schemas import (
    DerivedRunInput,
    RerunProposal,
    RerunProposalCancelRequest,
    RerunProposalCreateRequest,
    RerunProposalRecord,
    RerunProposalSubmitRequest,
    RerunSourceIdentity,
)
from app.run_evidence.errors import (
    RunEvidenceConflictError,
    RunEvidenceIntegrityError,
    RunEvidenceLimitExceededError,
    RunEvidenceNotFoundError,
)
from app.run_evidence.reader import VerifiedRunEvidenceReader
from app.run_evidence.schemas import VerifiedRunEvidence
from app.workspace.capabilities import requirements_from_profile
from app.workspace.schemas import JobRequirements


class ComparisonReader(Protocol):
    def get(self, comparison_id: str) -> ComparisonReport:
        ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_key(value: str) -> str:
    key = value.strip()
    if not key or len(key) > 300:
        raise ValueError("Idempotency-Key 长度必须为 1..300")
    return key


def _expires_at(created_at: str, ttl_seconds: int) -> str:
    created = datetime.fromisoformat(created_at)
    if created.tzinfo is None:
        raise ValueError("clock 必须返回带 timezone 的 ISO 时间")
    return (created + timedelta(seconds=ttl_seconds)).isoformat()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _trusted_requirements(profile_id: str) -> JobRequirements:
    return requirements_from_profile(
        get_execution_profile(profile_id)
    )


class RerunService:
    def __init__(
        self,
        *,
        repository: SqliteRerunRepository,
        evidence_reader: VerifiedRunEvidenceReader,
        job_service: JobService,
        comparison_reader: ComparisonReader | None,
        proposal_ttl_seconds: int,
        max_command_chars: int,
        max_argv_items: int,
        max_edits: int,
        clock: Callable[[], str] = utc_now,
        requirements_resolver: Callable[
            [str], JobRequirements
        ] = _trusted_requirements,
    ) -> None:
        self.repository = repository
        self.evidence_reader = evidence_reader
        self.job_service = job_service
        self.comparison_reader = comparison_reader
        self.proposal_ttl_seconds = proposal_ttl_seconds
        self.max_command_chars = max_command_chars
        self.max_argv_items = max_argv_items
        self.max_edits = max_edits
        self.clock = clock
        self.requirements_resolver = requirements_resolver
        self.repository.initialize()

    def _read_evidence(self, job_id: str) -> VerifiedRunEvidence:
        try:
            return self.evidence_reader.read(job_id)
        except (
            RunEvidenceNotFoundError,
            RunEvidenceConflictError,
            RunEvidenceLimitExceededError,
        ) as exc:
            raise RerunConflictError(str(exc)) from exc
        except RunEvidenceIntegrityError as exc:
            raise RerunIntegrityError(
                "Parent Run evidence integrity validation failed"
            ) from exc

    def _verify_comparison(
        self,
        *,
        parent_job_id: str,
        comparison_id: str | None,
        expected_hash: str | None,
    ) -> None:
        if comparison_id is None:
            return
        if self.comparison_reader is None or expected_hash is None:
            raise RerunConflictError("Comparison reader 未配置")
        report = self.comparison_reader.get(comparison_id)
        if report.comparison_hash != expected_hash:
            raise RerunConflictError("Comparison hash 已变化")
        if parent_job_id not in {report.base.job_id, report.target.job_id}:
            raise RerunConflictError(
                "父 Job 不属于指定 Comparison"
            )

    @staticmethod
    def _source_identity(
        evidence: VerifiedRunEvidence,
    ) -> RerunSourceIdentity:
        job = evidence.job
        workspace = evidence.workspace
        artifact = evidence.run_manifest_artifact
        return RerunSourceIdentity(
            parent_job_id=job.job_id,
            parent_run_id=job.run_id,
            parent_workspace_manifest_id=workspace.manifest_id,
            parent_workspace_manifest_hash=workspace.manifest_hash,
            parent_workspace_generation=workspace.generation,
            parent_run_manifest_artifact_id=artifact.artifact_id,
            parent_run_manifest_sha256=artifact.sha256,
        )

    @staticmethod
    def _verify_source_against_proposal(
        *,
        evidence: VerifiedRunEvidence,
        proposal: RerunProposal,
    ) -> None:
        current = RerunService._source_identity(evidence)
        if current != proposal.source:
            raise RerunConflictError(
                "父 Run Evidence identity 已变化，Proposal 已 stale"
            )
        selected = evidence.run_manifest.get("selected_run_command")
        if not isinstance(selected, dict):
            raise RerunIntegrityError(
                "父 run_manifest 缺少 selected_run_command"
            )
        command = str(selected.get("command") or "")
        if _text_sha256(command) != proposal.command_template.parent_command_sha256:
            raise RerunIntegrityError(
                "父 selected command 与 Proposal identity 不一致"
            )

    def create_proposal(
        self,
        *,
        request: RerunProposalCreateRequest,
        idempotency_key: str,
    ) -> tuple[RerunProposalRecord, bool]:
        key = _required_key(idempotency_key)
        if len(request.edits) > self.max_edits:
            raise ValueError("Rerun edits 超过配置上限")
        request_hash = sha256_value(request.model_dump(mode="json"))

        replay = self.repository.find_create_replay(
            idempotency_key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return replay, False

        evidence = self._read_evidence(request.parent_job_id)
        if evidence.job.version != request.expected_parent_job_version:
            raise RerunConflictError(
                "父 Job version 与调用方预期不一致，请刷新页面"
            )
        if (
            evidence.run_manifest_artifact.sha256
            != request.expected_parent_run_manifest_sha256
        ):
            raise RerunConflictError(
                "父 run_manifest SHA 与调用方预期不一致，请刷新页面"
            )
        self._verify_comparison(
            parent_job_id=request.parent_job_id,
            comparison_id=request.comparison_id,
            expected_hash=request.expected_comparison_hash,
        )

        template = build_command_template(
            selected_action=evidence.run_manifest.get(
                "selected_run_command"
            ),
            run_manifest=evidence.run_manifest,
            workspace=evidence.workspace,
            edits=request.edits,
            max_command_chars=self.max_command_chars,
            max_argv_items=self.max_argv_items,
        )
        profile_id = (
            request.execution_profile_id
            or evidence.job.request.execution_profile_id
        )
        requirements = self.requirements_resolver(profile_id)
        created_at = self.clock()
        draft = RerunProposal(
            proposal_id="rerun_" + "0" * 24,
            proposal_hash="0" * 64,
            source=self._source_identity(evidence),
            comparison_id=request.comparison_id,
            comparison_hash=request.expected_comparison_hash,
            edits=request.edits,
            command_template=template,
            experiment_goal=(
                request.experiment_goal
                or evidence.job.request.experiment_goal
            ),
            execution_profile_id=profile_id,
            execution_policy_hash=requirements.execution_policy_hash,
            execution_backend=requirements.execution_backend,
            created_at=created_at,
            expires_at=_expires_at(
                created_at,
                self.proposal_ttl_seconds,
            ),
        )
        digest = proposal_hash(draft)
        proposal = draft.model_copy(
            update={
                "proposal_hash": digest,
                "proposal_id": proposal_id_for_hash(digest),
            }
        )
        return self.repository.create(
            proposal=proposal,
            idempotency_key=key,
            request_hash=request_hash,
        )

    def get_proposal(self, proposal_id: str) -> RerunProposalRecord:
        return self.repository.get(proposal_id)

    def cancel_proposal(
        self,
        *,
        proposal_id: str,
        request: RerunProposalCancelRequest,
    ) -> RerunProposalRecord:
        return self.repository.cancel(
            proposal_id=proposal_id,
            expected_hash=request.expected_proposal_hash,
            expected_version=request.expected_version,
            reason=request.reason,
        )

    def submit_proposal(
        self,
        *,
        proposal_id: str,
        request: RerunProposalSubmitRequest,
        idempotency_key: str,
    ) -> tuple[RerunProposalRecord, JobRecord, bool]:
        operation_key = _required_key(idempotency_key)
        record = self.repository.begin_submission(
            proposal_id=proposal_id,
            expected_hash=request.expected_proposal_hash,
            expected_version=request.expected_version,
            submit_idempotency_key=operation_key,
        )
        if record.status == "submitted":
            if record.child_job_id is None:
                raise RerunIntegrityError(
                    "submitted Proposal 缺少 child_job_id"
                )
            return record, self.job_service.get(record.child_job_id), False

        proposal = record.proposal
        validate_proposal_hash(proposal)
        validate_command_template_hash(proposal.command_template)

        try:
            # 提交前再次打开父证据，而不是只相信创建 Proposal 时的内存对象。
            evidence = self._read_evidence(
                proposal.source.parent_job_id
            )
            self._verify_source_against_proposal(
                evidence=evidence,
                proposal=proposal,
            )
            self._verify_comparison(
                parent_job_id=proposal.source.parent_job_id,
                comparison_id=proposal.comparison_id,
                expected_hash=proposal.comparison_hash,
            )
            current_requirements = self.requirements_resolver(
                proposal.execution_profile_id
            )
            if (
                current_requirements.execution_policy_hash
                != proposal.execution_policy_hash
                or current_requirements.execution_backend
                != proposal.execution_backend
            ):
                raise RerunConflictError(
                    "Execution Profile policy 已变化，Proposal 已 stale"
                )

            child, created = self.job_service.submit(
                request=JobRequest(
                    derived_run=DerivedRunInput(
                        proposal_id=proposal.proposal_id,
                        proposal_hash=proposal.proposal_hash,
                        source=proposal.source,
                        command_template=proposal.command_template,
                    ),
                    experiment_goal=proposal.experiment_goal,
                    execution_profile_id=proposal.execution_profile_id,
                    dataset_refs=[
                        item.model_copy(deep=True)
                        for item in evidence.workspace.external_data
                    ],
                ),
                thread_id=f"rerun-{proposal.proposal_id}",
                # 跨 Rerun DB 与 Job DB 的 exactly-once 锚点。
                idempotency_key=f"rerun-submit:{proposal.proposal_id}",
            )
        except Exception as exc:
            self.repository.record_submission_error(
                proposal_id=proposal_id,
                submit_idempotency_key=operation_key,
                detail=f"{type(exc).__name__}: {exc}",
            )
            raise

        completed = self.repository.complete_submission(
            proposal_id=proposal_id,
            submit_idempotency_key=operation_key,
            child_job_id=child.job_id,
        )
        return completed, child, created
