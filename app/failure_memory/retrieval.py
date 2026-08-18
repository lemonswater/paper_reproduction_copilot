from __future__ import annotations

from datetime import datetime, timezone

from app.failure_memory.ports import FailureCaseRepository
from app.failure_memory.schemas import (
    FailureCaseMatch,
    FailureCasePack,
    FailureCaseRecord,
    FailureQuery,
    FailureScoreBreakdown,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jaccard(left: list[str], right: list[str]) -> float:
    a = set(left)
    b = set(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _authority(record: FailureCaseRecord) -> tuple[str, float]:
    if record.status == "run_verified":
        return "verified_precedent", 1.0
    if record.status == "human_confirmed":
        return "human_confirmed_advice", 0.65
    return "unverified_candidate", 0.25


def _compatibility(
    query: FailureQuery,
    record: FailureCaseRecord,
) -> tuple[str, float]:
    current = query.environment
    source = record.source.environment
    exact_signature = (
        query.signature.signature_sha256
        == record.signature.signature_sha256
    )
    same_repo = (
        current.repository_commit is not None
        and current.repository_commit == source.repository_commit
        and current.repository_clean is True
        and source.repository_clean is True
    )
    same_profile = (
        current.execution_profile_fingerprint
        == source.execution_profile_fingerprint
    )
    same_backend = current.execution_backend == source.execution_backend

    if exact_signature and same_repo and same_profile:
        return "exact_applicable", 1.0
    if not same_backend:
        return "incompatible", 0.0
    if (
        query.signature.stage == record.signature.stage
        and query.signature.code == record.signature.code
    ):
        return "review_required", 0.5
    if (
        query.signature.exception_type
        and query.signature.exception_type
        == record.signature.exception_type
    ):
        return "reference_only", 0.25
    return "incompatible", 0.0


def _match(
    query: FailureQuery,
    record: FailureCaseRecord,
) -> FailureCaseMatch:
    exact = float(
        query.signature.signature_sha256
        == record.signature.signature_sha256
    )
    stage_code = (
        float(query.signature.stage == record.signature.stage) * 0.4
        + float(query.signature.code == record.signature.code) * 0.6
    )
    frames = _jaccard(
        query.signature.frame_keys,
        record.signature.frame_keys,
    )
    tokens = _jaccard(
        query.signature.normalized_tokens,
        record.signature.normalized_tokens,
    )
    compatibility, environment = _compatibility(query, record)
    authority, authority_score = _authority(record)

    # 权重总和为 1.0；环境和 authority 不能掩盖完全无关的错误。
    total = (
        exact * 0.30
        + stage_code * 0.20
        + frames * 0.15
        + tokens * 0.15
        + environment * 0.10
        + authority_score * 0.10
    )
    score = FailureScoreBreakdown(
        signature=round(exact, 6),
        stage_code=round(stage_code, 6),
        frames=round(frames, 6),
        tokens=round(tokens, 6),
        environment=round(environment, 6),
        authority=round(authority_score, 6),
        total=round(total, 6),
    )

    confirmation = record.confirmation
    return FailureCaseMatch(
        case_id=record.case_id,
        status=record.status,
        authority=authority,
        compatibility=compatibility,
        score=score,
        diagnosis_summary=(
            confirmation.diagnosis_summary
            if confirmation is not None
            else record.candidate_diagnosis
        ),
        remedy=(
            confirmation.remedy
            if confirmation is not None
            else record.candidate_remedy
        ),
        applicability_note=(
            confirmation.applicability_note
            if confirmation is not None
            else "候选案例尚未经过人工确认"
        ),
        source_environment=record.source.environment,
        verification_environment=(
            record.verification.environment
            if record.verification is not None
            else None
        ),
        evidence=record.source.evidence,
    )


class FailureCaseRetriever:
    def __init__(
        self,
        *,
        repository: FailureCaseRepository,
        candidate_limit: int,
        top_k: int,
        minimum_score: float,
    ) -> None:
        self.repository = repository
        self.candidate_limit = candidate_limit
        self.top_k = top_k
        self.minimum_score = minimum_score

    def search(self, query: FailureQuery) -> FailureCasePack:
        candidates = self.repository.list_candidates(
            stage=query.signature.stage,
            code=query.signature.code,
            limit=self.candidate_limit,
        )
        matches = [_match(query, item) for item in candidates]
        matches = [
            item
            for item in matches
            if item.score.total >= self.minimum_score
            and item.compatibility != "incompatible"
        ]
        matches.sort(
            key=lambda item: (
                -item.score.total,
                item.case_id,
            )
        )
        return FailureCasePack(
            query_signature_sha256=(
                query.signature.signature_sha256
            ),
            items=matches[: self.top_k],
            generated_at=utc_now(),
        )
