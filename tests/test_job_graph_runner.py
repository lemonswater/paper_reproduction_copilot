from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from langgraph.types import Command

from app.job_runtime.graph_runner import (
    GraphJobRunner,
    JobGraphStateError,
)
from app.job_runtime.schemas import (
    JobInterrupt,
    JobRequest,
)
from app.job_runtime.store import SqliteJobStore
from tests.workspace_helpers import (
    binding_fixture,
    manifest_fixture,
    requirements_fixture,
    worker_fixture,
)


@dataclass
class FakeInterrupt:
    value: Any
    id: str = "interrupt-1"


@dataclass
class FakeTask:
    name: str
    interrupts: tuple[FakeInterrupt, ...]


@dataclass
class FakeSnapshot:
    values: dict[str, Any] = field(
        default_factory=dict
    )
    next: tuple[str, ...] = ()
    tasks: tuple[FakeTask, ...] = ()


class FakeGraph:
    def __init__(
        self,
        before: FakeSnapshot,
        after: FakeSnapshot | None = None,
    ):
        self.current = before
        self.after = after or before
        self.stream_calls = []

    def get_state(self, config):
        return self.current

    def stream(
        self,
        graph_input,
        *,
        config,
        stream_mode,
    ):
        self.stream_calls.append(graph_input)
        self.current = self.after
        yield {"fake_node": {"ok": True}}


class HealthyHeartbeat:
    def raise_if_unhealthy(self) -> None:
        return None


def _with_ready_binding(claim):
    """GraphJobRunner 要求 claim.workspace_binding 处于 ready。

    store.claim_next() 返回的 claim 没有绑定 workspace_binding，
    这里用 fixture 补一个 status='ready' 的 binding。
    """
    return claim.model_copy(
        update={
            "workspace_binding": binding_fixture(
                suffix="graph",
                status="ready",
                run_dir=claim.job.run_dir,
                job_id=claim.job.job_id,
                run_id=claim.job.run_id,
            )
        }
    )


def _claim(
    tmp_path,
    *,
    with_resume: bool,
):
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    store.submit(
        job_id="job-graph",
        idempotency_key="submit-graph",
        thread_id="thread-graph",
        run_id="run-graph",
        run_dir=str(tmp_path / "runs/run-graph"),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix="graph"),
        max_attempts=3,
        now=100.0,
    )
    worker_a = worker_fixture(
        worker_id="worker-a",
        session_id="session-a",
    )
    store.register_worker(
        worker=worker_a, lease_seconds=30
    )
    first = store.claim_next(
        worker=worker_a,
        lease_seconds=10,
        now=101.0,
    )
    assert first is not None
    first = _with_ready_binding(first)
    if not with_resume:
        return first

    store.mark_waiting(
        job_id=first.job.job_id,
        claim_token=first.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={},
            )
        ],
        result={},
        actor="worker-a",
        now=102.0,
    )
    store.queue_resume(
        job_id=first.job.job_id,
        expected_node="human_review",
        value={
            "decision": "approved",
            "feedback": None,
        },
        idempotency_key="resume-graph",
        actor="cli",
        now=103.0,
    )
    worker_b = worker_fixture(
        worker_id="worker-b",
        session_id="session-b",
    )
    store.register_worker(
        worker=worker_b, lease_seconds=30
    )
    second = store.claim_next(
        worker=worker_b,
        lease_seconds=10,
        now=104.0,
    )
    assert second is not None
    return _with_ready_binding(second)


def test_terminal_checkpoint_is_not_invoked_again(
    tmp_path,
) -> None:
    claim = _claim(
        tmp_path,
        with_resume=False,
    )
    graph = FakeGraph(
        FakeSnapshot(
            values={
                "job_id": "job-graph",
                "run_id": "run-graph",
                "final_status": "succeeded",
            },
            next=(),
        )
    )
    runner = GraphJobRunner(
        graph_factory=lambda: graph
    )

    outcome = runner.execute(
        claim,
        HealthyHeartbeat(),
    )

    assert outcome.status == "succeeded"
    assert graph.stream_calls == []


def test_checkpoint_identity_must_match_job(
    tmp_path,
) -> None:
    claim = _claim(
        tmp_path,
        with_resume=False,
    )
    graph = FakeGraph(
        FakeSnapshot(
            values={
                "job_id": "another-job",
                "run_id": "another-run",
            },
            next=("some_node",),
        )
    )
    runner = GraphJobRunner(
        graph_factory=lambda: graph
    )

    with pytest.raises(JobGraphStateError):
        runner.execute(
            claim,
            HealthyHeartbeat(),
        )

    assert graph.stream_calls == []


def test_interrupt_without_resume_becomes_waiting(
    tmp_path,
) -> None:
    claim = _claim(
        tmp_path,
        with_resume=False,
    )
    graph = FakeGraph(
        FakeSnapshot(
            values={
                "job_id": "job-graph",
                "run_id": "run-graph",
            },
            next=("command_selection",),
            tasks=(
                FakeTask(
                    name="command_selection",
                    interrupts=(
                        FakeInterrupt(
                            {"message": "choose"}
                        ),
                    ),
                ),
            ),
        )
    )
    runner = GraphJobRunner(
        graph_factory=lambda: graph
    )

    outcome = runner.execute(
        claim,
        HealthyHeartbeat(),
    )

    assert (
        outcome.status
        == "waiting_for_input"
    )
    assert outcome.interrupts[0].node == (
        "command_selection"
    )
    assert graph.stream_calls == []


def test_matching_resume_uses_langgraph_command(
    tmp_path,
) -> None:
    claim = _claim(
        tmp_path,
        with_resume=True,
    )
    graph = FakeGraph(
        before=FakeSnapshot(
            values={
                "job_id": "job-graph",
                "run_id": "run-graph",
            },
            next=("human_review",),
            tasks=(
                FakeTask(
                    name="human_review",
                    interrupts=(
                        FakeInterrupt(
                            {"message": "approve"}
                        ),
                    ),
                ),
            ),
        ),
        after=FakeSnapshot(
            values={
                "job_id": "job-graph",
                "run_id": "run-graph",
                "final_status": "succeeded",
            },
            next=(),
        ),
    )
    runner = GraphJobRunner(
        graph_factory=lambda: graph
    )

    outcome = runner.execute(
        claim,
        HealthyHeartbeat(),
    )

    assert outcome.status == "succeeded"
    assert len(graph.stream_calls) == 1
    assert isinstance(
        graph.stream_calls[0],
        Command,
    )