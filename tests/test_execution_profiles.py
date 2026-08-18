from __future__ import annotations

import json

import pytest

from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    load_execution_profiles,
)


def _write_conda_profile(tmp_path, monkeypatch):
    workspace = tmp_path / "paper-repo"
    workspace.mkdir()
    artifact_root = tmp_path / "paper-artifacts"
    conda_executable = tmp_path / "conda"
    conda_executable.write_text("#!/bin/sh\n", encoding="utf-8")
    conda_prefix = tmp_path / "conda-env"
    conda_prefix.mkdir()
    monkeypatch.setattr(
        "app.execution.profile_store.settings.allowed_root",
        tmp_path,
    )

    config_path = tmp_path / "profiles.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "profile_id": "paper-conda",
                        "backend": "conda",
                        "workspace_root": str(workspace),
                        "artifact_root": str(artifact_root),
                        "conda_executable": str(conda_executable),
                        "conda_prefix": str(conda_prefix),
                        "env": {"CUDA_VISIBLE_DEVICES": "0"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return config_path


def test_load_execution_profiles(tmp_path, monkeypatch) -> None:
    config_path = _write_conda_profile(tmp_path, monkeypatch)

    profiles = load_execution_profiles(config_path)

    assert set(profiles) == {"paper-conda"}
    assert profiles["paper-conda"].backend == "conda"
    assert profiles["paper-conda"].workspace_root == str(
        (tmp_path / "paper-repo").resolve()
    )


def test_profile_fingerprint_changes_with_environment(
    tmp_path,
    monkeypatch,
) -> None:
    config_path = _write_conda_profile(tmp_path, monkeypatch)
    profile = load_execution_profiles(config_path)["paper-conda"]
    original = compute_execution_profile_fingerprint(profile)

    changed = compute_execution_profile_fingerprint(
        profile.model_copy(update={"network_policy": "allow"})
    )

    assert original != changed


def test_profile_loader_rejects_sensitive_environment(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    monkeypatch.setattr(
        "app.execution.profile_store.settings.allowed_root",
        tmp_path,
    )
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "profile_id": "bad",
                        "backend": "local",
                        "workspace_root": str(workspace),
                        "artifact_root": str(tmp_path / "artifacts"),
                        "env": {"OPENAI_API_KEY": "must-not-load"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="敏感变量"):
        load_execution_profiles(path)


def test_profile_loader_rejects_artifact_root_escape(
    tmp_path,
    monkeypatch,
) -> None:
    allowed = tmp_path / "allowed"
    workspace = allowed / "repo"
    workspace.mkdir(parents=True)
    monkeypatch.setattr(
        "app.execution.profile_store.settings.allowed_root",
        allowed,
    )
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "profile_id": "bad",
                        "backend": "local",
                        "workspace_root": str(workspace),
                        "artifact_root": str(tmp_path / "outside"),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ALLOWED_ROOT 之外"):
        load_execution_profiles(path)
