from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_api_app
from app.config import settings
from app.interaction.artifacts import (
    LocalArtifactCatalog,
)
from app.job_runtime.schemas import (
    JobRequest,
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
)


def test_sse_returns_backlog_after_cursor(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    setup_local_execution_profile(tmp_path, monkeypatch)
    service = JobService(
        SqliteJobStore(
            tmp_path / "jobs.sqlite"
        ),
        workspace_snapshotter=FakeWorkspaceSnapshotter(),
    )
    job, _ = service.submit(
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id=(
                settings.default_execution_profile
            ),
        ),
        thread_id="sse-thread",
        idempotency_key="sse-submit",
    )
    app = create_api_app(
        job_service=service,
        artifact_catalog=(
            LocalArtifactCatalog(
                state_reader=lambda _: {}
            )
        ),
        api_token="test-token",
    )
    client = TestClient(app)

    response = client.get(
        (
            f"/v1/jobs/{job.job_id}"
            "/events/stream"
            "?after=0&follow=false"
        ),
        headers={
            "Authorization": (
                "Bearer test-token"
            )
        },
    )

    assert response.status_code == 200
    assert "event: job_submitted" in (
        response.text
    )
    assert "id: " in response.text


def test_event_page_cursor_does_not_repeat(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )
    setup_local_execution_profile(tmp_path, monkeypatch)
    service = JobService(
        SqliteJobStore(
            tmp_path / "jobs.sqlite"
        ),
        workspace_snapshotter=FakeWorkspaceSnapshotter(),
    )
    job, _ = service.submit(
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id=(
                settings.default_execution_profile
            ),
        ),
        thread_id="cursor-thread",
        idempotency_key="cursor-submit",
    )
    client = TestClient(
        create_api_app(
            job_service=service,
            artifact_catalog=(
                LocalArtifactCatalog(
                    state_reader=lambda _: {}
                )
            ),
            api_token="test-token",
        )
    )
    headers = {
        "Authorization": "Bearer test-token"
    }

    first = client.get(
        f"/v1/jobs/{job.job_id}/events",
        headers=headers,
    ).json()
    second = client.get(
        (
            f"/v1/jobs/{job.job_id}/events"
            f"?after={first['next_after']}"
        ),
        headers=headers,
    ).json()

    assert first["items"]
    assert second["items"] == []
