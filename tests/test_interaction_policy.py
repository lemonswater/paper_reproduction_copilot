from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.command_selection import compute_run_commands_hash
from app.interaction.policy import (
    allowed_operations,
    decision_to_resume_value,
    normalize_decision_against_record,
    validate_decision,
)
from app.interaction.schemas import (
    ActionApprovalDecision,
    CommandSelectionDecision,
    DecisionEnvelope,
)
from app.job_runtime.errors import (
    JobConflictError,
)
from app.job_runtime.schemas import (
    JobInterrupt,
    JobRecord,
    JobRequest,
)
from tests.workspace_helpers import (
    requirements_fixture,
)


def _waiting_job(
    *,
    version: int = 4,
    generation: int = 2,
    node: str = "human_review",
) -> JobRecord:
    now = datetime.now(
        timezone.utc
    ).isoformat()
    return JobRecord(
        job_id="job_policy",
        idempotency_key="submit-policy",
        request_hash="request-hash",
        thread_id="thread-policy",
        run_id="run-policy",
        run_dir="/data/runs/run-policy",
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        workspace_manifest_id="manifest-policy",
        workspace_manifest_generation=1,
        workspace_assignment_epoch=1,
        status="waiting_for_input",
        version=version,
        attempt_count=1,
        max_attempts=3,
        wait_generation=generation,
        available_at=now,
        interrupt_nodes=[node],
        interrupts=[
            JobInterrupt(
                node=node,
                value_preview={
                    "message": "review"
                },
            )
        ],
        created_at=now,
        updated_at=now,
    )


def _envelope(
    *,
    version: int = 4,
    generation: int = 2,
) -> DecisionEnvelope:
    return DecisionEnvelope(
        expected_job_version=version,
        expected_wait_generation=(
            generation
        ),
        decision=ActionApprovalDecision(
            kind="action_approval",
            decision="approved",
        ),
    )


def test_allowed_operation_contains_server_identity():
    record = _waiting_job()

    operation = allowed_operations(
        record
    )[0]

    assert operation.kind == "submit_decision"
    assert (
        operation.expected_job_version
        == record.version
    )
    assert (
        operation.expected_wait_generation
        == record.wait_generation
    )
    assert (
        operation.decision_kind
        == "action_approval"
    )


def test_stale_job_version_is_rejected():
    with pytest.raises(
        JobConflictError,
        match="version",
    ):
        validate_decision(
            record=_waiting_job(
                version=5
            ),
            envelope=_envelope(
                version=4
            ),
        )


def test_stale_wait_generation_is_rejected():
    with pytest.raises(
        JobConflictError,
        match="generation",
    ):
        validate_decision(
            record=_waiting_job(
                generation=3
            ),
            envelope=_envelope(
                generation=2
            ),
        )


def test_wrong_decision_kind_is_rejected():
    with pytest.raises(
        JobConflictError,
        match="不匹配",
    ):
        validate_decision(
            record=_waiting_job(
                node="patch_review"
            ),
            envelope=_envelope(),
        )


def test_decision_value_does_not_include_kind():
    value = decision_to_resume_value(
        _envelope().decision
    )

    assert value == {
        "decision": "approved",
        "feedback": None,
    }


COMMANDS = [
    {
        "command": "python train.py --dataset_path <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "high",
        "reason": "train",
    },
    {
        "command": "python test.py --checkpoint <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "medium",
        "reason": "test",
    },
]


def _command_waiting_job() -> JobRecord:
    record = _waiting_job(
        node="command_selection"
    )
    command_hash = compute_run_commands_hash(COMMANDS)
    return record.model_copy(
        update={
            "interrupts": [
                JobInterrupt(
                    node="command_selection",
                    value_preview={
                        "message": "select command",
                        "run_commands": COMMANDS,
                        "run_commands_hash": command_hash,
                    },
                )
            ]
        }
    )


def _command_decision(
    *,
    command_hash: str | None = None,
    selected_index: int = 0,
) -> CommandSelectionDecision:
    return CommandSelectionDecision(
        kind="command_selection",
        selected_index=selected_index,
        edits=[
            {
                "index": 0,
                "command": (
                    "  python train.py "
                    "--dataset_path /data/ntu60  "
                ),
            }
        ],
        run_commands_hash=(
            command_hash
            or compute_run_commands_hash(COMMANDS)
        ),
    )


def test_command_decision_is_normalized_against_preview():
    decision = normalize_decision_against_record(
        record=_command_waiting_job(),
        decision=_command_decision(),
    )

    assert isinstance(
        decision,
        CommandSelectionDecision,
    )
    assert decision.edits[0].command == (
        "python train.py --dataset_path /data/ntu60"
    )


def test_stale_command_hash_is_rejected_before_resume():
    with pytest.raises(
        JobConflictError,
        match="run_commands_hash",
    ):
        normalize_decision_against_record(
            record=_command_waiting_job(),
            decision=_command_decision(
                command_hash="0" * 64
            ),
        )


def test_out_of_range_selection_is_user_input_error():
    with pytest.raises(
        ValueError,
        match="selected_index",
    ):
        normalize_decision_against_record(
            record=_command_waiting_job(),
            decision=_command_decision(
                selected_index=2
            ),
        )


def test_tampered_server_preview_is_rejected():
    record = _command_waiting_job()
    preview = dict(
        record.interrupts[0].value_preview
    )
    preview["run_commands_hash"] = "f" * 64
    tampered = record.model_copy(
        update={
            "interrupts": [
                JobInterrupt(
                    node="command_selection",
                    value_preview=preview,
                )
            ]
        }
    )

    with pytest.raises(
        JobConflictError,
        match="preview",
    ):
        normalize_decision_against_record(
            record=tampered,
            decision=_command_decision(),
        )