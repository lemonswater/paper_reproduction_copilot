from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_api_app
from app.command_selection import compute_run_commands_hash
from app.config import settings
from app.interaction.artifacts import (
    LocalArtifactCatalog,
)
from app.job_runtime.schemas import (
    JobInterrupt,
)
from app.job_runtime.service import (
    JobService,
)
from app.job_runtime.store import (
    SqliteJobStore,
)
from tests.workspace_helpers import (
    FakeWorkspaceSnapshotter,
    setup_local_execution_profile,
    worker_fixture,
)

AUTH = {
    "Authorization": "Bearer test-token"
}


def _client(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    policy_hash = setup_local_execution_profile(
        tmp_path, monkeypatch
    )
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    service = JobService(
        store,
        workspace_snapshotter=FakeWorkspaceSnapshotter(),
    )
    catalog = LocalArtifactCatalog(
        state_reader=lambda _: {}
    )
    app = create_api_app(
        job_service=service,
        artifact_catalog=catalog,
        api_token="test-token",
    )
    return TestClient(app), service, policy_hash


def _submit(client):
    return client.post(
        "/v1/jobs",
        headers={
            **AUTH,
            "Idempotency-Key": "submit-api-1",
        },
        json={
            "paper_path": "/data/paper.pdf",
            "repo_path": "/data/repo",
            "thread_id": "api-thread-1",
            "experiment_goal": "test",
            "execution_profile_id": (
                settings.default_execution_profile
            ),
        },
    )


def test_api_requires_token(
    tmp_path,
    monkeypatch,
):
    client, _, _ = _client(
        tmp_path,
        monkeypatch,
    )

    response = client.get("/v1/jobs")

    assert response.status_code == 401


def test_submit_is_idempotent_and_public(
    tmp_path,
    monkeypatch,
):
    client, _, _ = _client(
        tmp_path,
        monkeypatch,
    )

    first = _submit(client)
    second = _submit(client)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["replayed"] is True

    body = first.json()["job"]
    assert "run_dir" not in body
    assert "claim_token" not in body
    assert "idempotency_key" not in body
    assert "paper_path" not in body["input"]


def test_stale_decision_returns_409(
    tmp_path,
    monkeypatch,
):
    client, service, policy_hash = _client(
        tmp_path,
        monkeypatch,
    )
    submitted = _submit(client).json()
    job_id = submitted["job"]["job_id"]

    service.store.register_worker(
        worker=worker_fixture(
            worker_id="test-worker",
            policy_hash=policy_hash,
        ),
        lease_seconds=30,
    )
    claim = service.store.claim_next(
        worker=worker_fixture(
            worker_id="test-worker",
            policy_hash=policy_hash,
        ),
        lease_seconds=30,
    )
    assert claim is not None
    waiting = service.store.mark_waiting(
        job_id=job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={
                    "action": {
                        "command": "python x.py"
                    }
                },
            )
        ],
        result={},
        actor="test-worker",
    )

    response = client.post(
        f"/v1/jobs/{job_id}/decisions",
        headers={
            **AUTH,
            "Idempotency-Key": (
                "decision-stale"
            ),
        },
        json={
            "expected_job_version": (
                waiting.version - 1
            ),
            "expected_wait_generation": (
                waiting.wait_generation
            ),
            "decision": {
                "kind": "action_approval",
                "decision": "approved",
            },
        },
    )

    assert response.status_code == 409
    assert (
        response.json()["code"]
        == "JOB_CONFLICT"
    )


def test_current_decision_queues_resume(
    tmp_path,
    monkeypatch,
):
    client, service, policy_hash = _client(
        tmp_path,
        monkeypatch,
    )
    submitted = _submit(client).json()
    job_id = submitted["job"]["job_id"]
    service.store.register_worker(
        worker=worker_fixture(
            worker_id="test-worker",
            policy_hash=policy_hash,
        ),
        lease_seconds=30,
    )
    claim = service.store.claim_next(
        worker=worker_fixture(
            worker_id="test-worker",
            policy_hash=policy_hash,
        ),
        lease_seconds=30,
    )
    assert claim is not None
    waiting = service.store.mark_waiting(
        job_id=job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="human_review",
                value_preview={},
            )
        ],
        result={},
        actor="test-worker",
    )

    response = client.post(
        f"/v1/jobs/{job_id}/decisions",
        headers={
            **AUTH,
            "Idempotency-Key": (
                "decision-current"
            ),
        },
        json={
            "expected_job_version": (
                waiting.version
            ),
            "expected_wait_generation": (
                waiting.wait_generation
            ),
            "decision": {
                "kind": "action_approval",
                "decision": "approved",
            },
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["job"]["status"]
        == "queued"
    )


COMMAND_SELECTION_COMMANDS = [
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


def _mark_command_selection_waiting(
    client,
    service,
    policy_hash,
):
    job_id = _submit(client).json()["job"]["job_id"]
    worker = worker_fixture(
        worker_id="command-api-worker",
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
    assert claim is not None

    command_hash = compute_run_commands_hash(
        COMMAND_SELECTION_COMMANDS
    )
    waiting = service.store.mark_waiting(
        job_id=job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="command_selection",
                value_preview={
                    "message": "select command",
                    "run_commands": (
                        COMMAND_SELECTION_COMMANDS
                    ),
                    "run_commands_hash": command_hash,
                },
            )
        ],
        result={},
        actor="command-api-worker",
    )
    return waiting, command_hash


def _post_command_decision(
    client,
    waiting,
    *,
    command_hash,
    selected_index=0,
    edits=None,
    key="command-decision-1",
):
    return client.post(
        f"/v1/jobs/{waiting.job_id}/decisions",
        headers={
            **AUTH,
            "Idempotency-Key": key,
        },
        json={
            "expected_job_version": waiting.version,
            "expected_wait_generation": (
                waiting.wait_generation
            ),
            "decision": {
                "kind": "command_selection",
                "selected_index": selected_index,
                "edits": edits or [],
                "run_commands_hash": command_hash,
            },
        },
    )


def test_stale_command_hash_does_not_queue_resume(
    tmp_path,
    monkeypatch,
):
    client, service, policy_hash = _client(
        tmp_path,
        monkeypatch,
    )
    waiting, _ = _mark_command_selection_waiting(
        client,
        service,
        policy_hash,
    )

    response = _post_command_decision(
        client,
        waiting,
        command_hash="0" * 64,
        key="stale-command-decision",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "JOB_CONFLICT"
    assert service.get(waiting.job_id).status == (
        "waiting_for_input"
    )
    assert all(
        item.event_type != "job_resume_queued"
        for item in service.events(waiting.job_id)
    )


def test_out_of_range_command_index_returns_422(
    tmp_path,
    monkeypatch,
):
    client, service, policy_hash = _client(
        tmp_path,
        monkeypatch,
    )
    waiting, command_hash = (
        _mark_command_selection_waiting(
            client,
            service,
            policy_hash,
        )
    )

    response = _post_command_decision(
        client,
        waiting,
        command_hash=command_hash,
        selected_index=99,
        key="invalid-command-index",
    )

    assert response.status_code == 422
    assert service.get(waiting.job_id).status == (
        "waiting_for_input"
    )


def test_valid_multiple_edits_queue_one_resume(
    tmp_path,
    monkeypatch,
):
    client, service, policy_hash = _client(
        tmp_path,
        monkeypatch,
    )
    waiting, command_hash = (
        _mark_command_selection_waiting(
            client,
            service,
            policy_hash,
        )
    )

    response = _post_command_decision(
        client,
        waiting,
        command_hash=command_hash,
        selected_index=1,
        edits=[
            {
                "index": 0,
                "command": (
                    "python train.py "
                    "--dataset_path /data/ntu60"
                ),
            },
            {
                "index": 1,
                "command": (
                    "python test.py "
                    "--checkpoint /data/best.pth"
                ),
            },
        ],
        key="valid-command-edits",
    )

    assert response.status_code == 200
    assert response.json()["job"]["status"] == "queued"
    queued_events = [
        item
        for item in service.events(waiting.job_id)
        if item.event_type == "job_resume_queued"
    ]
    assert len(queued_events) == 1
    # Event 只保存 value_hash，不复制用户完整命令。
    assert "/data/ntu60" not in str(
        queued_events[0].payload
    )
