from __future__ import annotations

from typing import Literal

from app.failure_memory.identity import (
    build_failure_signature,
    compute_case_hash,
)
from app.failure_memory.schemas import (
    FailureCaseRecord,
    FailureEnvironmentIdentity,
    FailureEvidenceReference,
    FailureRemedy,
    FailureRunVerification,
    FailureSourceIdentity,
    HumanConfirmation,
)
from app.schemas import StageError


NOW = "2026-08-11T00:00:00+00:00"


def make_environment(
    *,
    profile_fingerprint: str = "profile-source-v1",
    repository_commit: str = "a" * 40,
    backend: Literal["local", "conda", "oci"] = "local",
) -> FailureEnvironmentIdentity:
    return FailureEnvironmentIdentity(
        execution_profile_id="local",
        execution_profile_fingerprint=profile_fingerprint,
        execution_backend=backend,
        repository_commit=repository_commit,
        repository_clean=True,
    )


def make_stage_error(
    *,
    code: str = "PROCESS_NONZERO_EXIT",
    message: str = "CUDA extension build failed with gcc incompatibility",
) -> StageError:
    return StageError(
        error_id="error-test-001",
        code=code,
        category="paper_program",
        stage="execution_verifier",
        message=message,
        retryable=False,
        terminal=True,
        exception_type="RuntimeError",
        context={"end_reason": "exited"},
        occurred_at=NOW,
    )


def make_signature(
    *,
    traceback_text: str | None = None,
    code: str = "PROCESS_NONZERO_EXIT",
):
    return build_failure_signature(
        stage_error=make_stage_error(code=code),
        error_type="cuda_extension_build",
        traceback_text=(
            traceback_text
            or '  File "/repo/modules/setup.py", line 42, in build_ext\n'
            'RuntimeError: CUDA extension build failed\n'
        ),
        repo_path="/repo",
    )


def make_case(
    *,
    case_id: str = "failure_" + "1" * 24,
    source_job_id: str = "job-failed",
    status: str = "candidate",
    profile_fingerprint: str = "profile-source-v1",
    repository_commit: str = "a" * 40,
) -> FailureCaseRecord:
    signature = make_signature()
    source = FailureSourceIdentity(
        job_id=source_job_id,
        job_version=3,
        run_id=f"run-{source_job_id}",
        workspace_manifest_id=f"manifest-{source_job_id}",
        workspace_manifest_hash="b" * 64,
        run_manifest_artifact_id=f"artifact-{source_job_id}-manifest",
        run_manifest_sha256="c" * 64,
        final_status="failed",
        environment=make_environment(
            profile_fingerprint=profile_fingerprint,
            repository_commit=repository_commit,
        ),
        evidence=[
            FailureEvidenceReference(
                purpose="run_manifest",
                artifact_id=f"artifact-{source_job_id}-manifest",
                relative_path="reports/run_manifest.json",
                sha256="c" * 64,
                size_bytes=1024,
            )
        ],
    )
    confirmation = None
    verification = None
    deprecation_reason = None
    if status in {"human_confirmed", "run_verified"}:
        confirmation = HumanConfirmation(
            actor="local-user",
            diagnosis_summary="GCC 与 CUDA extension toolchain 不兼容。",
            remedy=FailureRemedy(
                kind="environment_change",
                summary="切换到受支持的 GCC profile 后重新构建。",
                steps=["选择兼容 GCC 的 Execution Profile。"],
                risks=["环境变化后必须重新执行预检。"],
            ),
            applicability_note="仅限同仓库 commit 和相同失败环境。",
            confirmed_at=NOW,
        )
    if status == "run_verified":
        verification = FailureRunVerification(
            job_id="job-fixed",
            run_id="run-job-fixed",
            run_manifest_artifact_id="artifact-fixed-manifest",
            run_manifest_sha256="d" * 64,
            proposal_id="rerun_" + "2" * 24,
            proposal_hash="e" * 64,
            execution_verification_id="exec-verification:test",
            execution_verification_sha256="f" * 64,
            environment=make_environment(
                profile_fingerprint="profile-fixed-v1",
                repository_commit=repository_commit,
            ),
            verified_at=NOW,
        )
    if status == "deprecated":
        deprecation_reason = "案例已由新证据取代"

    draft = FailureCaseRecord(
        case_id=case_id,
        case_hash="0" * 64,
        version={
            "candidate": 0,
            "human_confirmed": 1,
            "run_verified": 2,
            "deprecated": 3,
        }[status],
        status=status,
        signature=signature,
        source=source,
        candidate_diagnosis="可能是 GCC 与 CUDA toolchain 不兼容。",
        candidate_remedy=FailureRemedy(
            kind="unknown",
            summary="检查编译器与 CUDA 兼容矩阵。",
            risks=["候选尚未确认。"],
        ),
        confirmation=confirmation,
        verification=verification,
        deprecation_reason=deprecation_reason,
        created_at=NOW,
        updated_at=NOW,
    )
    return draft.model_copy(
        update={"case_hash": compute_case_hash(draft)}
    )
