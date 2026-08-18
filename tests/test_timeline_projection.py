"""Phase 30 Timeline 投影测试。"""

from __future__ import annotations

from app.interaction.schemas import (
    AllowedOperation,
    EventView,
    PublicInterrupt,
)
from app.interaction.timeline import build_timeline
from tests.helpers.interaction import make_job


def test_timeline_is_deterministic_and_does_not_copy_payload():
    event = EventView(
        event_id=7,
        job_id="job-1",
        event_type="future_internal_event",
        actor="worker",
        payload={"claim_token": "must-not-leak"},
        created_at="2026-08-01T00:00:10+00:00",
    )

    first = build_timeline(job=make_job(), events=[event])
    second = build_timeline(job=make_job(), events=[event])

    assert first == second
    assert first.items[0].role == "user"
    assert first.items[1].item_id == "event:7"
    assert "must-not-leak" not in first.model_dump_json()


def test_waiting_job_uses_server_operation_for_decision_item():
    operation = AllowedOperation(
        operation_id="wait:1:human_review",
        kind="submit_decision",
        endpoint="/v1/jobs/job-1/decisions",
        decision_kind="action_approval",
        expected_node="human_review",
        expected_job_version=3,
        expected_wait_generation=1,
        allowed_decisions=["approved", "rejected", "revise"],
    )
    interrupt = PublicInterrupt(
        node="human_review",
        value_preview={"action": {"command": "python train.py"}},
    )
    timeline = build_timeline(
        job=make_job(
            status="waiting_for_input",
            version=3,
            wait_generation=1,
            interrupt_nodes=["human_review"],
            interrupts=[interrupt],
            allowed_operations=[operation],
        ),
        events=[],
    )

    decision = timeline.items[-1]
    assert decision.kind == "decision"
    assert decision.operation == operation
    assert decision.interrupt == interrupt


def test_error_item_is_appended_when_job_has_error():
    timeline = build_timeline(
        job=make_job(
            error={"type": "ValueError", "message": "boom"},
        ),
        events=[],
    )

    error_item = timeline.items[-1]
    assert error_item.kind == "error"
    assert "boom" in error_item.content


def test_last_event_id_defaults_to_zero_without_events():
    timeline = build_timeline(job=make_job(), events=[])
    assert timeline.last_event_id == 0
