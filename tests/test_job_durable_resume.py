from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.job_runtime.graph_runner import (
    GraphJobRunner,
)
from app.job_runtime.heartbeat import (
    LeaseHeartbeat,
)
from app.job_runtime.schemas import JobRequest
from app.job_runtime.store import SqliteJobStore
from tests.workspace_helpers import (
    binding_fixture,
    manifest_fixture,
    requirements_fixture,
    worker_fixture,
)

SqliteSaver = pytest.importorskip(
    "langgraph.checkpoint.sqlite"
).SqliteSaver


class MiniState(TypedDict, total=False):
    job_id: str
    thread_id: str
    task_id: str
    run_id: str
    run_dir: str
    decision: str
    final_status: str


def review_node(
    state: MiniState,
) -> MiniState:
    response = interrupt(
        {"message": "approve test"}
    )
    return {
        "decision": str(
            response.get(
                "decision",
                "rejected",
            )
        )
    }


def finish_node(
    state: MiniState,
) -> MiniState:
    return {
        "final_status": (
            "succeeded"
            if state.get("decision")
            == "approved"
            else "rejected"
        )
    }


def build_mini_graph(
    db_path: Path,
):
    connection = sqlite3.connect(
        db_path,
        check_same_thread=False,
    )
    saver = SqliteSaver(connection)
    builder = StateGraph(MiniState)
    builder.add_node("review", review_node)
    builder.add_node("finish", finish_node)
    builder.add_edge(START, "review")
    builder.add_edge("review", "finish")
    builder.add_edge("finish", END)
    return (
        builder.compile(checkpointer=saver),
        connection,
    )


def _heartbeat(
    store,
    claim,
) -> LeaseHeartbeat:
    # 测试直接调用 runner，不启动 heartbeat thread；
    # raise_if_unhealthy 仍可检查本地状态。
    return LeaseHeartbeat(
        store=store,
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        lease_seconds=30,
        interval_seconds=5,
    )


def test_job_resume_across_graph_process_instances(
    tmp_path,
) -> None:
    checkpoint_path = (
        tmp_path / "langgraph.sqlite"
    )
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    store.submit(
        job_id="job-durable",
        idempotency_key="submit-durable",
        thread_id="thread-durable",
        run_id="run-durable",
        run_dir=str(tmp_path / "runs/run-durable"),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix="durable"),
        max_attempts=3,
    )

    first_worker = worker_fixture(
        worker_id="worker-1",
        session_id="session-1",
    )
    store.register_worker(
        worker=first_worker,
        lease_seconds=30,
    )
    first_claim = store.claim_next(
        worker=first_worker,
        lease_seconds=30,
    )
    assert first_claim is not None
    first_claim = first_claim.model_copy(
        update={
            "workspace_binding": binding_fixture(
                status="ready",
                run_dir=first_claim.job.run_dir,
                job_id=first_claim.job.job_id,
                run_id=first_claim.job.run_id,
            )
        }
    )
    graph1, connection1 = build_mini_graph(
        checkpoint_path
    )
    try:
        first_outcome = GraphJobRunner(
            graph_factory=lambda: graph1
        ).execute(
            first_claim,
            _heartbeat(
                store,
                first_claim,
            ),
        )
    finally:
        connection1.close()

    assert (
        first_outcome.status
        == "waiting_for_input"
    )
    store.mark_waiting(
        job_id=first_claim.job.job_id,
        claim_token=first_claim.claim_token,
        interrupts=first_outcome.interrupts,
        result=first_outcome.result,
        actor="worker-1",
    )
    store.queue_resume(
        job_id="job-durable",
        expected_node="review",
        value={"decision": "approved"},
        idempotency_key="resume-durable",
        actor="test",
    )

    second_worker = worker_fixture(
        worker_id="worker-2",
        session_id="session-2",
    )
    store.register_worker(
        worker=second_worker,
        lease_seconds=30,
    )
    second_claim = store.claim_next(
        worker=second_worker,
        lease_seconds=30,
    )
    assert second_claim is not None
    second_claim = second_claim.model_copy(
        update={
            "workspace_binding": binding_fixture(
                status="ready",
                run_dir=second_claim.job.run_dir,
                job_id=second_claim.job.job_id,
                run_id=second_claim.job.run_id,
            )
        }
    )
    graph2, connection2 = build_mini_graph(
        checkpoint_path
    )
    try:
        second_outcome = GraphJobRunner(
            graph_factory=lambda: graph2
        ).execute(
            second_claim,
            _heartbeat(
                store,
                second_claim,
            ),
        )
    finally:
        connection2.close()

    assert second_outcome.status == "succeeded"
    assert (
        second_outcome.result["final_status"]
        == "succeeded"
    )
    store.mark_succeeded(
        job_id=second_claim.job.job_id,
        claim_token=second_claim.claim_token,
        result=second_outcome.result,
        actor="worker-2",
    )
    assert (
        store.get("job-durable").status
        == "succeeded"
    )