from __future__ import annotations

from pathlib import Path

from app.nodes.input_validation_node import input_validation_node
from app.schemas import ExecutionProfile


def _profile(workspace: Path) -> ExecutionProfile:
    return ExecutionProfile(
        profile_id="test-profile",
        backend="local",
        workspace_root=str(workspace),
        artifact_root=str(workspace / "artifacts"),
        env={},
    )


def test_input_validation_accepts_valid_inputs(
    run_state,
    tmp_path,
    monkeypatch,
):
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"%PDF-controlled-fixture")
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(
        "app.nodes.input_validation_node.get_execution_profile",
        lambda profile_id: _profile(repo),
    )

    state = {
        **run_state,
        "paper_path": str(paper),
        "repo_path": str(repo),
        "execution_profile_id": "test-profile",
    }
    result = input_validation_node(state)

    assert result["inputs_validated"] is True
    assert result["input_validation_report"]["valid"] is True
    assert not result.get("stage_errors")


def test_missing_paper_becomes_user_stage_error(
    run_state,
    tmp_path,
    monkeypatch,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    missing_paper = tmp_path / "missing.pdf"

    monkeypatch.setattr(
        "app.nodes.input_validation_node.get_execution_profile",
        lambda profile_id: _profile(repo),
    )

    state = {
        **run_state,
        "paper_path": str(missing_paper),
        "repo_path": str(repo),
        "execution_profile_id": "test-profile",
    }
    result = input_validation_node(state)

    assert result["inputs_validated"] is False
    assert result["final_status"] == "invalid_input"
    assert any(
        item["code"] == "INPUT_NOT_FOUND"
        and item["category"] == "user"
        for item in result["stage_errors"]
    )


def test_repo_outside_profile_workspace_is_blocked(
    run_state,
    tmp_path,
    monkeypatch,
):
    paper = tmp_path / "paper.txt"
    paper.write_text("paper", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    other_repo = tmp_path / "other-repo"
    other_repo.mkdir()

    monkeypatch.setattr(
        "app.nodes.input_validation_node.get_execution_profile",
        lambda profile_id: _profile(workspace),
    )

    state = {
        **run_state,
        "paper_path": str(paper),
        "repo_path": str(other_repo),
        "execution_profile_id": "test-profile",
    }
    result = input_validation_node(state)

    assert result["inputs_validated"] is False
    assert result["final_status"] == "environment_blocked"
    assert any(
        item["code"] == "REPO_OUTSIDE_PROFILE_WORKSPACE"
        for item in result["stage_errors"]
    )