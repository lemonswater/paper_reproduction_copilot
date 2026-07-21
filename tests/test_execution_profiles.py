import json

from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    load_execution_profiles,
)


def test_load_execution_profiles(tmp_path) -> None:
    config_path = tmp_path / "profiles.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "profile_id": "paper-conda",
                        "backend": "conda",
                        "workspace_root": "/tmp/paper-repo",
                        "artifact_root": "/tmp/paper-artifacts",
                        "conda_executable": "/opt/conda/bin/conda",
                        "conda_prefix": "/opt/conda/envs/paper",
                        "env": {"CUDA_VISIBLE_DEVICES": "0"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    profiles = load_execution_profiles(config_path)

    assert set(profiles) == {"paper-conda"}
    assert profiles["paper-conda"].backend == "conda"


def test_profile_fingerprint_changes_with_environment(tmp_path) -> None:
    config_path = tmp_path / "profiles.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "profile_id": "paper-conda",
                        "backend": "conda",
                        "workspace_root": "/tmp/paper-repo",
                        "artifact_root": "/tmp/paper-artifacts",
                        "conda_executable": "/opt/conda/bin/conda",
                        "conda_prefix": "/opt/conda/envs/paper",
                        "env": {"CUDA_VISIBLE_DEVICES": "0"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    profile = load_execution_profiles(config_path)["paper-conda"]
    original = compute_execution_profile_fingerprint(profile)

    changed_profile = profile.model_copy(
        update={"conda_prefix": "/opt/conda/envs/paper-v2"}
    )
    changed = compute_execution_profile_fingerprint(changed_profile)

    assert original != changed