"""Phase 42 Decision Protocol 确定性回归测试。

验证以下 8 个不变量（section 29）：
1. stale expected_job_version -> JobConflictError / HTTP 409
2. stale expected_wait_generation -> JobConflictError / HTTP 409
3. decision kind 与 interrupt node 不匹配 -> HTTP 409
4. command list hash 已变化 -> HTTP 409
5. action hash 与 approval hash 不匹配 -> stale_approval，不启动进程
6. 同 idempotency key + 同 payload -> replayed=true，不重复 resume
7. 同 idempotency key + 不同 payload -> conflict，不覆盖首次请求
8. 业务冲突只调用一次 service，不在 API 层重试 mutation

这些测试是确定性安全协议的回归门禁，不依赖 Provider。
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.errors import install_error_handlers
from app.api.routes import router
from app.command_selection import compute_run_commands_hash
from app.interaction.policy import (
    allowed_operations,
    validate_decision,
)
from app.interaction.schemas import (
    ActionApprovalDecision,
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
from app.job_runtime.store import (
    SqliteJobStore,
)
from app.nodes.executor_node import executor_node
from app.observability.noop import NoOpTelemetry
from app.tools.action_tools import compute_action_hash
from tests.workspace_helpers import (
    manifest_fixture,
    requirements_fixture,
    worker_fixture,
)

_TOKEN = SecretStr("test-token")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _waiting_record(
    *,
    version: int = 4,
    generation: int = 2,
    node: str = "human_review",
) -> JobRecord:
    now = datetime.now(timezone.utc).isoformat()
    return JobRecord(
        job_id="job_regression",
        idempotency_key="submit-regression",
        request_hash="request-hash",
        thread_id="thread-regression",
        run_id="run-regression",
        run_dir="/data/runs/run-regression",
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        workspace_manifest_id="manifest-regression",
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
                value_preview={"message": "review"},
            )
        ],
        created_at=now,
        updated_at=now,
    )


def _envelope(
    *,
    version: int = 4,
    generation: int = 2,
    decision: str = "approved",
) -> DecisionEnvelope:
    return DecisionEnvelope(
        expected_job_version=version,
        expected_wait_generation=generation,
        decision=ActionApprovalDecision(
            kind="action_approval",
            decision=decision,
        ),
    )


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


def _command_waiting_record() -> JobRecord:
    record = _waiting_record(node="command_selection")
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


# ---------------------------------------------------------------------------
# 1. stale expected_job_version
# ---------------------------------------------------------------------------

def test_stale_job_version_rejected_at_policy():
    """Invariant 1: 旧 Job version 必须被 policy 层拒绝。"""
    with pytest.raises(JobConflictError, match="version"):
        validate_decision(
            record=_waiting_record(version=5),
            envelope=_envelope(version=4),
        )


def test_stale_job_version_returns_409_at_api(
    tmp_path, monkeypatch,
):
    """Invariant 1: 旧 Job version 必须返回 HTTP 409。"""
    from app.api.app import create_api_app
    from app.config import settings
    from app.interaction.artifacts import LocalArtifactCatalog
    from app.job_runtime.service import JobService
    from tests.workspace_helpers import (
        FakeWorkspaceSnapshotter,
        setup_local_execution_profile,
    )

    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")
    policy_hash = setup_local_execution_profile(tmp_path, monkeypatch)
    store = SqliteJobStore(tmp_path / "jobs.sqlite")
    service = JobService(
        store,
        workspace_snapshotter=FakeWorkspaceSnapshotter(),
    )
    catalog = LocalArtifactCatalog(state_reader=lambda _: {})
    app = create_api_app(
        job_service=service,
        artifact_catalog=catalog,
        api_token="test-token",
    )
    app.state.api_token_override = _TOKEN
    client = TestClient(app)

    submitted = client.post(
        "/v1/jobs",
        headers={
            "Authorization": "Bearer test-token",
            "Idempotency-Key": "submit-regression-1",
        },
        json={
            "paper_path": "/data/paper.pdf",
            "repo_path": "/data/repo",
            "thread_id": "api-thread-1",
            "experiment_goal": "test",
            "execution_profile_id": settings.default_execution_profile,
        },
    )
    job_id = submitted.json()["job"]["job_id"]

    worker = worker_fixture(
        worker_id="test-worker",
        policy_hash=policy_hash,
    )
    service.store.register_worker(
        worker=worker,
        lease_seconds=30,
    )
    claim = service.store.claim_next(
        worker=worker,
        lease_seconds=30,
    )
    waiting = service.store.mark_waiting(
        job_id=job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={"message": "review"},
            )
        ],
        result={},
        actor="test-worker",
    )

    response = client.post(
        f"/v1/jobs/{job_id}/decisions",
        headers={
            "Authorization": "Bearer test-token",
            "Idempotency-Key": "decision-stale-version",
        },
        json={
            "expected_job_version": waiting.version - 1,
            "expected_wait_generation": waiting.wait_generation,
            "decision": {
                "kind": "action_approval",
                "decision": "approved",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "JOB_CONFLICT"


# ---------------------------------------------------------------------------
# 2. stale expected_wait_generation
# ---------------------------------------------------------------------------

def test_stale_wait_generation_rejected_at_policy():
    """Invariant 2: 旧 wait generation 必须被 policy 层拒绝。"""
    with pytest.raises(JobConflictError, match="generation"):
        validate_decision(
            record=_waiting_record(generation=3),
            envelope=_envelope(generation=2),
        )


# ---------------------------------------------------------------------------
# 3. decision kind 与 interrupt node 不匹配
# ---------------------------------------------------------------------------

def test_wrong_decision_kind_rejected_at_policy():
    """Invariant 3: decision kind 与 interrupt node 不匹配必须被拒绝。"""
    with pytest.raises(JobConflictError, match="不匹配"):
        validate_decision(
            record=_waiting_record(node="patch_review"),
            envelope=_envelope(),
        )


# ---------------------------------------------------------------------------
# 4. command list hash 已变化
# ---------------------------------------------------------------------------

def test_stale_command_hash_rejected_at_policy():
    """Invariant 4: command list hash 已变化必须被 policy 层拒绝。"""
    from app.interaction.policy import (
        normalize_decision_against_record,
    )
    from app.interaction.schemas import (
        CommandSelectionDecision,
    )

    decision = CommandSelectionDecision(
        kind="command_selection",
        selected_index=0,
        edits=[],
        run_commands_hash="0" * 64,
    )
    with pytest.raises(JobConflictError, match="run_commands_hash"):
        normalize_decision_against_record(
            record=_command_waiting_record(),
            decision=decision,
        )


# ---------------------------------------------------------------------------
# 5. action hash 与 approval hash 不匹配 -> stale_approval
# ---------------------------------------------------------------------------

def _build_pending_action() -> dict:
    return {
        "action_id": "action_regression",
        "action_type": "run_command",
        "program": "python",
        "args": ["train.py"],
        "cwd": "/tmp/demo-repo",
        "reason": "run baseline training",
        "source": "script",
        "timeout_seconds": 300,
        "env_overrides": {},
        "writable_paths": ["/tmp/demo-repo"],
        "network_access": "none",
        "execution_profile_id": "test-local",
        "execution_profile_fingerprint": "profile-hash",
    }


def _build_approval_record(action: dict) -> dict:
    return {
        "approval_id": "approval_regression",
        "action_id": action["action_id"],
        "action_hash": compute_action_hash(action),
        "decision": "approved",
        "reviewer": "human",
        "risk_level": "medium",
        "reviewed_at": "2026-08-10T00:00:00+00:00",
        "comment": None,
    }


def test_stale_action_hash_does_not_start_process(run_state) -> None:
    """Invariant 5: action hash 与 approval hash 不匹配时不启动进程。"""
    pending_action = _build_pending_action()
    approval_record = _build_approval_record(pending_action)

    # 修改 pending_action 使其 hash 与 approval_record 不一致
    tampered_action = {**pending_action, "args": ["eval.py"]}
    assert (
        compute_action_hash(tampered_action)
        != approval_record["action_hash"]
    )

    state = {
        **run_state,
        "user_approval": "approved",
        "pending_action": tampered_action,
        "approval_record": approval_record,
    }

    with patch(
        "app.nodes.executor_node.run_action_safe"
    ) as mocked_run:
        result = executor_node(state)

    mocked_run.assert_not_called()
    assert result["final_status"] == "stale_approval"
    assert result["last_action_result"]["status"] == "stale_approval"


# ---------------------------------------------------------------------------
# 6. 同 idempotency key + 同 payload -> replayed=true
# ---------------------------------------------------------------------------

def _store_and_waiting_job(tmp_path):
    store = SqliteJobStore(tmp_path / "jobs.sqlite")
    store.initialize()
    record, _ = store.submit(
        job_id="job_regression_replay",
        idempotency_key="submit-replay",
        thread_id="thread-replay",
        run_id="run-replay",
        run_dir=str(tmp_path / "runs" / "run-replay"),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        requirements=requirements_fixture(),
        initial_manifest=manifest_fixture(suffix="replay"),
        max_attempts=3,
        now=100.0,
    )
    worker = worker_fixture(worker_id="worker-replay")
    store.register_worker(worker=worker, lease_seconds=30)
    claim = store.claim_next(
        worker=worker, lease_seconds=30, now=101.0
    )
    waiting = store.mark_waiting(
        job_id=claim.job.job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={},
            )
        ],
        result={},
        actor="worker-replay",
        now=102.0,
    )
    return store, waiting


def test_same_idempotency_key_same_payload_replays(tmp_path):
    """Invariant 6: 同 idempotency key + 同 payload 返回 replayed=true。"""
    store, waiting = _store_and_waiting_job(tmp_path)

    args = {
        "job_id": waiting.job_id,
        "expected_node": "human_review",
        "value": {"decision": "approved"},
        "idempotency_key": "resume-replay-regression",
        "actor": "api",
        "expected_job_version": waiting.version,
        "expected_wait_generation": waiting.wait_generation,
        "now": 103.0,
    }

    first, first_created = store.queue_resume(**args)
    second, second_created = store.queue_resume(**args)

    assert first_created is True
    assert second_created is False
    assert (
        first.pending_resume_id == second.pending_resume_id
    )

    # 只有一个 resume 事件
    events = store.list_events(waiting.job_id)
    resume_events = [
        e for e in events if e.event_type == "job_resume_queued"
    ]
    assert len(resume_events) == 1


# ---------------------------------------------------------------------------
# 7. 同 idempotency key + 不同 payload -> conflict
# ---------------------------------------------------------------------------

def test_same_idempotency_key_different_payload_conflicts(tmp_path):
    """Invariant 7: 同 idempotency key + 不同 payload 必须冲突。"""
    store, waiting = _store_and_waiting_job(tmp_path)

    base_args = {
        "job_id": waiting.job_id,
        "expected_node": "human_review",
        "idempotency_key": "resume-conflict-regression",
        "actor": "api",
        "expected_job_version": waiting.version,
        "expected_wait_generation": waiting.wait_generation,
        "now": 103.0,
    }

    # 第一次：approved
    store.queue_resume(
        value={"decision": "approved"},
        **base_args,
    )

    # 第二次：同 key 但 decision 变为 rejected -> 必须冲突
    with pytest.raises(JobConflictError, match="不同"):
        store.queue_resume(
            value={"decision": "rejected"},
            **base_args,
        )


# ---------------------------------------------------------------------------
# 8. 业务冲突只调用一次 service
# ---------------------------------------------------------------------------

class CountingConflictService:
    """模拟 service 在 submit_decision 时抛 JobConflictError。"""

    def __init__(self):
        self.calls = 0

    def submit_decision(self, **_kwargs):
        self.calls += 1
        raise JobConflictError("stale decision")


def test_business_conflict_does_not_retry_mutation():
    """Invariant 8: 业务冲突只调用一次 service，不在 API 层重试。"""
    service = CountingConflictService()
    app = FastAPI()
    app.state.api_token_override = _TOKEN
    app.state.telemetry = NoOpTelemetry()
    app.state.interaction_service = service
    app.include_router(router)
    install_error_handlers(app)
    client = TestClient(app)

    response = client.post(
        "/v1/jobs/job-regression/decisions",
        headers={
            "Authorization": "Bearer test-token",
            "Idempotency-Key": "exactly-once-regression",
        },
        json={
            "expected_job_version": 4,
            "expected_wait_generation": 2,
            "decision": {
                "kind": "action_approval",
                "decision": "approved",
                "feedback": None,
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "JOB_CONFLICT"
    assert service.calls == 1


# ---------------------------------------------------------------------------
# 额外：AllowedOperation 只由服务端 JobRecord 生成
# ---------------------------------------------------------------------------

def test_allowed_operation_carries_server_identity():
    """Invariant 3 (补充): AllowedOperation 必须包含服务端版本和 generation。"""
    record = _waiting_record(version=7, generation=4)
    operations = allowed_operations(record)

    assert len(operations) >= 1
    op = operations[0]
    assert op.kind == "submit_decision"
    assert op.expected_job_version == record.version
    assert op.expected_wait_generation == record.wait_generation
    assert op.decision_kind == "action_approval"
