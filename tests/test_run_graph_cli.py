from __future__ import annotations

import json

from typer.testing import CliRunner

from app.config import settings
from app.main import app


def test_run_graph_persists_reports_when_graph_initialization_fails(
    tmp_path,
    monkeypatch,
):
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(settings, "runs_dir", runs_dir)

    def fail_to_build_graph():
        raise RuntimeError("controlled graph initialization failure")

    monkeypatch.setattr("app.main.build_graph", fail_to_build_graph)

    result = CliRunner().invoke(
        app,
        [
            "run-graph",
            "paper.pdf",
            "repo",
            "--thread-id",
            "cli-failure-test",
        ],
    )

    assert result.exit_code == 1
    run_dirs = list(runs_dir.glob("cli-failure-test-*"))
    assert len(run_dirs) == 1

    run_dir = run_dirs[0]
    error_path = run_dir / "reports" / "error_report.json"
    final_report_path = run_dir / "reports" / "final_report.md"
    manifest_path = run_dir / "reports" / "run_manifest.json"

    assert error_path.exists()
    assert final_report_path.exists()
    assert manifest_path.exists()

    errors = json.loads(error_path.read_text(encoding="utf-8"))
    assert errors["errors"][-1]["stage"] == "cli.run_graph"
    assert errors["errors"][-1]["category"] == "agent"
