"""Phase 27 ContainerPlan 构造和 Podman token 编译测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.execution.container_errors import (
    ContainerPolicyViolation,
)
from app.execution.container_plan import (
    build_container_plan,
    build_podman_create_tokens,
    plan_sha256,
)
from app.execution.container_schemas import ContainerPlan
from app.schemas import (
    ExecutableAction,
    ExecutionProfile,
    OciExecutionConfig,
    ResourceBudget,
)
from app.workspace.schemas import WorkspaceBinding


def _make_profile() -> ExecutionProfile:
    return ExecutionProfile(
        profile_id="test-oci",
        backend="oci",
        workspace_root="/tmp/workspace",
        artifact_root="/tmp/artifacts",
        enforcement_mode="strict",
        network_policy="deny",
        budget=ResourceBudget(),
        oci=OciExecutionConfig(
            image_ref=(
                "docker.io/library/python@sha256:"
                + "a" * 64
            ),
            memory_bytes=512 * 1024 * 1024,
            cpus=2.0,
            pids_limit=256,
            tmpfs_bytes=128 * 1024 * 1024,
        ),
    )


def _make_binding(
    tmp_path: Path,
    repo_path: Path | None = None,
) -> WorkspaceBinding:
    repo = repo_path or (tmp_path / "repo")
    repo.mkdir(parents=True, exist_ok=True)
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    return WorkspaceBinding(
        assignment_id="was_test",
        assignment_epoch=1,
        assignment_token="wa_test_secret_token",
        job_id="job-test",
        run_id="run-test",
        manifest_id="manifest-test",
        manifest_hash="c" * 64,
        manifest_generation=0,
        worker_session_id="session-test",
        host_id="host-a",
        workspace_root=str(tmp_path),
        run_dir=str(run_dir),
        repo_path=str(repo),
        paper_path="/tmp/paper.pdf",
        log_path=None,
        status="ready",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _make_action(
    cwd: str,
    program: str = "python",
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> ExecutableAction:
    return ExecutableAction(
        action_id="act_test",
        program=program,
        args=args or ["-c", "print('hello')"],
        cwd=cwd,
        source="inferred",
        reason="test",
        env_overrides=env or {},
        execution_profile_id="test-oci",
        execution_profile_fingerprint="e" * 64,
    )


class TestBuildContainerPlan:
    def test_cwd_mapped_to_container_repo_root(
        self, tmp_path: Path
    ) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        sub = repo / "src"
        sub.mkdir()
        binding = _make_binding(tmp_path, repo_path=repo)
        profile = _make_profile()
        action = _make_action(cwd=str(sub))

        plan = build_container_plan(
            action=action,
            profile=profile,
            binding=binding,
            job_id="job-test",
            run_id="run-test",
        )
        assert (
            plan.workdir
            == "/workspace/repo/src"
        )

    def test_repo_mount_ro_run_mount_rw(
        self, tmp_path: Path
    ) -> None:
        binding = _make_binding(tmp_path)
        profile = _make_profile()
        action = _make_action(cwd=str(tmp_path / "repo"))

        plan = build_container_plan(
            action=action,
            profile=profile,
            binding=binding,
            job_id="job-test",
            run_id="run-test",
        )
        mounts = {
            m.container_path: m for m in plan.mounts
        }
        assert mounts["/workspace/repo"].mode == "ro"
        assert mounts["/workspace/run"].mode == "rw"

    def test_rejects_cwd_outside_repo(
        self, tmp_path: Path
    ) -> None:
        binding = _make_binding(tmp_path)
        profile = _make_profile()
        outside = tmp_path / "outside"
        outside.mkdir()
        action = _make_action(cwd=str(outside))

        with pytest.raises(
            ContainerPolicyViolation, match="cwd"
        ):
            build_container_plan(
                action=action,
                profile=profile,
                binding=binding,
                job_id="job-test",
                run_id="run-test",
            )

    def test_env_allowlist_only(
        self, tmp_path: Path
    ) -> None:
        binding = _make_binding(tmp_path)
        profile = _make_profile()
        action = _make_action(
            cwd=str(tmp_path / "repo"),
            env={
                "PYTHONUNBUFFERED": "1",
                "SECRET_KEY": "leak",
                "OMP_NUM_THREADS": "4",
            },
        )

        plan = build_container_plan(
            action=action,
            profile=profile,
            binding=binding,
            job_id="job-test",
            run_id="run-test",
        )
        assert "PYTHONUNBUFFERED" in plan.env
        assert "OMP_NUM_THREADS" in plan.env
        assert "SECRET_KEY" not in plan.env

    def test_ownership_hash_not_raw_token(
        self, tmp_path: Path
    ) -> None:
        binding = _make_binding(tmp_path)
        profile = _make_profile()
        action = _make_action(cwd=str(tmp_path / "repo"))

        plan = build_container_plan(
            action=action,
            profile=profile,
            binding=binding,
            job_id="job-test",
            run_id="run-test",
        )
        assert (
            plan.ownership_token_hash
            != binding.assignment_token
        )
        assert len(plan.ownership_token_hash) == 64
        assert (
            plan.ownership_token_hash
            not in binding.assignment_token
        )


class TestBuildPodmanCreateTokens:
    def _make_plan(
        self, tmp_path: Path
    ) -> ContainerPlan:
        binding = _make_binding(tmp_path)
        profile = _make_profile()
        action = _make_action(cwd=str(tmp_path / "repo"))
        return build_container_plan(
            action=action,
            profile=profile,
            binding=binding,
            job_id="job-test",
            run_id="run-test",
        )

    def test_tokens_contain_required_security_flags(
        self, tmp_path: Path
    ) -> None:
        plan = self._make_plan(tmp_path)
        tokens = build_podman_create_tokens(plan)

        assert "--pull=never" in tokens
        assert "--read-only" in tokens
        assert "--network=none" in tokens
        assert "--cap-drop=all" in tokens
        assert (
            "--security-opt=no-new-privileges"
            in tokens
        )

    def test_tokens_never_contain_dangerous_flags(
        self, tmp_path: Path
    ) -> None:
        plan = self._make_plan(tmp_path)
        tokens = build_podman_create_tokens(plan)
        token_str = " ".join(tokens)

        assert "--privileged" not in token_str
        assert "--network=host" not in token_str
        assert "--pid=host" not in token_str
        assert "--ipc=host" not in token_str
        assert "--userns=host" not in token_str
        assert "podman.sock" not in token_str
        assert "docker.sock" not in token_str

    def test_same_input_same_plan_hash(
        self, tmp_path: Path
    ) -> None:
        plan1 = self._make_plan(tmp_path)
        plan2 = self._make_plan(tmp_path)
        assert plan_sha256(plan1) == plan_sha256(plan2)

    def test_different_input_different_plan_hash(
        self, tmp_path: Path
    ) -> None:
        plan = self._make_plan(tmp_path)
        modified = plan.model_copy(
            update={"memory_bytes": 1024 * 1024 * 1024}
        )
        assert plan_sha256(plan) != plan_sha256(modified)
