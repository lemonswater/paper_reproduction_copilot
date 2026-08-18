# tests/test_rerun_repository.py
from __future__ import annotations

import pytest

from app.rerun.errors import RerunConflictError
from app.rerun.identity import (
    command_template_hash,
    proposal_hash,
    proposal_id_for_hash,
)
from app.rerun.repository import SqliteRerunRepository
from app.rerun.schemas import (
    RerunArgumentEdit,
    RerunCommandTemplate,
    RerunProposal,
    RerunSourceIdentity,
    RerunTemplateArg,
)


def _proposal() -> RerunProposal:
    template_draft = RerunCommandTemplate(
        argv=[
            RerunTemplateArg(kind="literal", value="python"),
            RerunTemplateArg(kind="literal", value="train.py"),
            RerunTemplateArg(kind="literal", value="--epochs"),
            RerunTemplateArg(kind="literal", value="100"),
        ],
        cwd_relative=".",
        reason="test rerun",
        parent_command_sha256="a" * 64,
        template_hash="0" * 64,
    )
    template = template_draft.model_copy(
        update={"template_hash": command_template_hash(template_draft)}
    )
    draft = RerunProposal(
        proposal_id="rerun_" + "0" * 24,
        proposal_hash="0" * 64,
        source=RerunSourceIdentity(
            parent_job_id="job-parent",
            parent_run_id="run-parent",
            parent_workspace_manifest_id="wm-parent",
            parent_workspace_manifest_hash="b" * 64,
            parent_workspace_generation=2,
            parent_run_manifest_artifact_id="artifact-manifest",
            parent_run_manifest_sha256="c" * 64,
        ),
        edits=[
            RerunArgumentEdit(
                option="--epochs",
                operation="set",
                expected_old_value="50",
                value="100",
            )
        ],
        command_template=template,
        experiment_goal="rerun test",
        execution_profile_id="cpu-local",
        execution_policy_hash="e" * 64,
        execution_backend="local",
        created_at="2026-08-09T00:00:00+00:00",
        expires_at="2026-08-10T00:00:00+00:00",
    )
    digest = proposal_hash(draft)
    return draft.model_copy(
        update={
            "proposal_hash": digest,
            "proposal_id": proposal_id_for_hash(digest),
        }
    )


def _repository(tmp_path) -> SqliteRerunRepository:
    repository = SqliteRerunRepository(
        tmp_path / "rerun.sqlite",
        clock=lambda: "2026-08-09T01:00:00+00:00",
    )
    repository.initialize()
    return repository


def test_create_is_idempotent(tmp_path) -> None:
    repository = _repository(tmp_path)
    proposal = _proposal()
    first, first_created = repository.create(
        proposal=proposal,
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    second, second_created = repository.create(
        proposal=proposal,
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    assert first_created is True
    assert second_created is False
    assert first.proposal.proposal_id == second.proposal.proposal_id


def test_same_create_key_with_different_request_conflicts(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.create(
        proposal=_proposal(),
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    with pytest.raises(RerunConflictError):
        repository.find_create_replay(
            idempotency_key="create-1",
            request_hash="e" * 64,
        )


def test_submission_recovery_reuses_same_ownership(tmp_path) -> None:
    repository = _repository(tmp_path)
    pending, _ = repository.create(
        proposal=_proposal(),
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    submitting = repository.begin_submission(
        proposal_id=pending.proposal.proposal_id,
        expected_hash=pending.proposal.proposal_hash,
        expected_version=pending.version,
        submit_idempotency_key="submit-operation-1",
    )
    assert submitting.status == "submitting"

    # 模拟 Job 创建后、complete 前崩溃：同 operation key 可恢复。
    replay = repository.begin_submission(
        proposal_id=pending.proposal.proposal_id,
        expected_hash=pending.proposal.proposal_hash,
        expected_version=pending.version,
        submit_idempotency_key="submit-operation-1",
    )
    assert replay.status == "submitting"

    with pytest.raises(RerunConflictError):
        repository.begin_submission(
            proposal_id=pending.proposal.proposal_id,
            expected_hash=pending.proposal.proposal_hash,
            expected_version=pending.version,
            submit_idempotency_key="submit-operation-2",
        )

    completed = repository.complete_submission(
        proposal_id=pending.proposal.proposal_id,
        submit_idempotency_key="submit-operation-1",
        child_job_id="job-child",
    )
    assert completed.status == "submitted"
    assert completed.child_job_id == "job-child"


def test_only_pending_proposal_can_be_cancelled(tmp_path) -> None:
    repository = _repository(tmp_path)
    pending, _ = repository.create(
        proposal=_proposal(),
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    cancelled = repository.cancel(
        proposal_id=pending.proposal.proposal_id,
        expected_hash=pending.proposal.proposal_hash,
        expected_version=pending.version,
        reason="not needed",
    )
    assert cancelled.status == "cancelled"


def test_expired_proposal_returns_expired_on_get(tmp_path) -> None:
    clock_state = {"now": "2026-08-09T01:00:00+00:00"}

    def clock():
        return clock_state["now"]

    repository = SqliteRerunRepository(
        tmp_path / "rerun.sqlite",
        clock=clock,
    )
    repository.initialize()
    pending, _ = repository.create(
        proposal=_proposal(),
        idempotency_key="create-1",
        request_hash="d" * 64,
    )
    assert pending.status == "pending"

    # 推进时间到过期后
    clock_state["now"] = "2026-08-11T01:00:00+00:00"
    expired = repository.get(pending.proposal.proposal_id)
    assert expired.status == "expired"

    from app.rerun.errors import RerunExpiredError

    with pytest.raises(RerunExpiredError):
        repository.begin_submission(
            proposal_id=pending.proposal.proposal_id,
            expected_hash=pending.proposal.proposal_hash,
            expected_version=expired.version,
            submit_idempotency_key="submit-1",
        )
