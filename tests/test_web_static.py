"""Phase 30 SPA 静态文件托管测试。"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.web import mount_web_ui


def test_missing_optional_dist_does_not_break_api(tmp_path):
    app = FastAPI()

    @app.get("/readyz")
    def readyz():
        return {"status": "ready"}

    mount_web_ui(
        app, dist_dir=tmp_path / "missing", required=False
    )

    assert (
        TestClient(app).get("/readyz").status_code == 200
    )


def test_missing_required_dist_fails_fast(tmp_path):
    with pytest.raises(RuntimeError, match="index.html"):
        mount_web_ui(
            FastAPI(),
            dist_dir=tmp_path / "missing",
            required=True,
        )


def test_spa_fallback_does_not_hide_missing_assets(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<html><body>paper-copilot-ui</body></html>",
        encoding="utf-8",
    )
    app = FastAPI()

    @app.get("/v1/ping")
    def ping():
        return {"ok": True}

    mount_web_ui(app, dist_dir=dist, required=True)
    client = TestClient(app)

    assert "paper-copilot-ui" in client.get("/").text
    assert (
        "paper-copilot-ui"
        in client.get("/jobs/job-1").text
    )
    assert (
        client.get("/assets/missing.js").status_code
        == 404
    )
    assert client.get("/v1/ping").json() == {"ok": True}
