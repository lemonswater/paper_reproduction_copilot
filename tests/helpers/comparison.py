from __future__ import annotations

from app.comparison.identity import (
    comparison_id_for_hash,
    compute_comparison_hash,
    compute_snapshot_hash,
)
from app.comparison.schemas import (
    CommandSnapshot,
    ComparisonReport,
    ComparisonSummary,
    ExecutionFacts,
    RunSnapshot,
)


def make_snapshot(
    *,
    job_id: str,
    run_id: str,
    paper_sha256: str = "a" * 64,
    job_status: str = "succeeded",
    command: str = "python train.py --batch-size 8",
) -> RunSnapshot:
    draft = RunSnapshot(
        snapshot_hash="0" * 64,
        job_id=job_id,
        run_id=run_id,
        job_status=job_status,
        experiment_goal="复现论文 main result",
        workspace_manifest_id=f"manifest-{job_id}",
        workspace_manifest_hash="b" * 64,
        workspace_manifest_generation=0,
        paper_sha256=paper_sha256,
        repository_commit="c" * 40,
        repository_clean=True,
        datasets=[],
        execution_profile_id="cpu-local",
        execution_policy_hash="d" * 64,
        execution_backend="local",
        execution_profile_fingerprint="e" * 64,
        selected_command=CommandSnapshot(
            present=True,
            display=command,
            command_sha256="f" * 64,
            cwd_sha256="1" * 64,
            source="readme",
            risk_level="low",
        ),
        execution=ExecutionFacts(
            final_status="succeeded",
            ok=True,
            returncode=0,
            end_reason="exited",
        ),
        smoke_test_status="passed",
        smoke_test_passed=True,
        run_manifest_artifact_id=f"artifact-manifest-{job_id}",
        run_manifest_sha256="2" * 64,
    )
    return draft.model_copy(
        update={"snapshot_hash": compute_snapshot_hash(draft)}
    )


def make_report(
    *,
    created_at: str = "2026-08-09T00:00:00+00:00",
) -> ComparisonReport:
    draft = ComparisonReport(
        comparison_id="comparison_" + "0" * 24,
        comparison_hash="0" * 64,
        created_at=created_at,
        allow_cross_paper=False,
        base=make_snapshot(job_id="job-base", run_id="run-base"),
        target=make_snapshot(job_id="job-target", run_id="run-target"),
        summary=ComparisonSummary(
            change_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            changed_categories=[],
            artifact_added=0,
            artifact_removed=0,
            artifact_changed=0,
        ),
        changes=[],
    )
    digest = compute_comparison_hash(draft)
    return draft.model_copy(
        update={
            "comparison_hash": digest,
            "comparison_id": comparison_id_for_hash(digest),
        }
    )
