"""Phase 27 OciRunner 测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.execution.base import ExecutionRuntimeContext
from app.execution.container_schemas import (
    ContainerInspect,
)
from app.execution.container_supervisor import (
    ContainerSupervisor,
)
from app.execution.oci_runner import OciRunner
from app.schemas import (
    ExecutableAction,
    ExecutionProfile,
    OciExecutionConfig,
    ResourceBudget,
)
from app.workspace.schemas import WorkspaceBinding
from tests.fakes.fake_container_engine import (
    FakeContainerEngine,
)


def _make_profile(
    tmp_path: Path,
) -> ExecutionProfile:
    return ExecutionProfile(
        profile_id="test-oci",
        backend="oci",
        workspace_root=str(tmp_path / "repo"),
        artifact_root=str(tmp_path / "artifacts"),
        enforcement_mode="strict",
        network_policy="deny",
        budget=ResourceBudget(),
        allowed_programs=["python"],
        allowed_action_env_keys=[
            "PYTHONUNBUFFERED",
            "OMP_NUM_THREADS",
        ],
        writable_roots=[str(tmp_path / "repo")],
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
) -> WorkspaceBinding:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    return WorkspaceBinding(
        assignment_id="was_test",
        assignment_epoch=1,
        assignment_token="wa_test_secret",
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
) -> dict:
    return ExecutableAction(
        action_id="act_test",
        program="python",
        args=["hello.py"],
        cwd=cwd,
        source="script",
        reason="test",
        env_overrides={"PYTHONUNBUFFERED": "1"},
        execution_profile_id="test-oci",
        execution_profile_fingerprint="e" * 64,
    ).model_dump()


def _ownership_hash() -> str:
    """Match ExecutionRuntimeContext.ownership_token_hash for 'wa_test_secret'."""

    import hashlib

    return hashlib.sha256(b"wa_test_secret").hexdigest()


def _make_inspect(
    *,
    exit_code: int = 0,
    oom: bool = False,
    ownership_hash: str | None = None,
) -> ContainerInspect:
    return ContainerInspect(
        container_id="a" * 64,
        name="prc-job-test-aaaaaaaaaaaa",
        running=False,
        status="exited",
        exit_code=exit_code,
        oom_killed=oom,
        image_digest="sha256:" + "a" * 64,
        labels={
            "io.paper-copilot.managed": "true",
            "io.paper-copilot.job-id": "job-test",
            "io.paper-copilot.run-id": "run-test",
            "io.paper-copilot.ownership-hash": (
                ownership_hash or _ownership_hash()
            ),
        },
    )


class TestOciRunnerRun:
    def test_successful_execution(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect(exit_code=0)
        supervisor = ContainerSupervisor(engine=engine)
        profile = _make_profile(tmp_path)
        runner = OciRunner(
            profile=profile, supervisor=supervisor
        )
        binding = _make_binding(tmp_path)
        ctx = ExecutionRuntimeContext(
            job_id="job-test",
            run_id="run-test",
            workspace_binding=binding,
        )
        action = _make_action(
            cwd=str(tmp_path / "repo")
        )

        result = runner.run(
            action,
            run_dir=str(binding.run_dir),
            stage="executor",
            runtime_context=ctx,
        )

        assert result["ok"] is True
        assert result["returncode"] == 0
        assert result["execution_backend"] == "oci"
        assert (
            result["execution_profile_id"]
            == "test-oci"
        )

    def test_missing_runtime_context_raises(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        supervisor = ContainerSupervisor(engine=engine)
        profile = _make_profile(tmp_path)
        runner = OciRunner(
            profile=profile, supervisor=supervisor
        )
        action = _make_action(
            cwd=str(tmp_path / "repo")
        )

        with pytest.raises(
            ValueError, match="WorkspaceBinding"
        ):
            runner.run(
                action,
                run_dir=str(tmp_path / "run"),
                stage="executor",
                runtime_context=None,
            )

    def test_oom_killed_reports_failure(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect(
            exit_code=137, oom=True
        )
        supervisor = ContainerSupervisor(engine=engine)
        profile = _make_profile(tmp_path)
        runner = OciRunner(
            profile=profile, supervisor=supervisor
        )
        binding = _make_binding(tmp_path)
        ctx = ExecutionRuntimeContext(
            job_id="job-test",
            run_id="run-test",
            workspace_binding=binding,
        )
        action = _make_action(
            cwd=str(tmp_path / "repo")
        )

        result = runner.run(
            action,
            run_dir=str(binding.run_dir),
            stage="executor",
            runtime_context=ctx,
        )

        assert result["ok"] is False
        assert result["end_reason"] == "memory_limit"
        assert result["returncode"] == 137

    def test_non_zero_exit_reports_failure(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect(
            exit_code=1
        )
        supervisor = ContainerSupervisor(engine=engine)
        profile = _make_profile(tmp_path)
        runner = OciRunner(
            profile=profile, supervisor=supervisor
        )
        binding = _make_binding(tmp_path)
        ctx = ExecutionRuntimeContext(
            job_id="job-test",
            run_id="run-test",
            workspace_binding=binding,
        )
        action = _make_action(
            cwd=str(tmp_path / "repo")
        )

        result = runner.run(
            action,
            run_dir=str(binding.run_dir),
            stage="executor",
            runtime_context=ctx,
        )

        assert result["ok"] is False
        assert result["returncode"] == 1

    def test_run_dir_mismatch_raises(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect()
        supervisor = ContainerSupervisor(engine=engine)
        profile = _make_profile(tmp_path)
        runner = OciRunner(
            profile=profile, supervisor=supervisor
        )
        binding = _make_binding(tmp_path)
        ctx = ExecutionRuntimeContext(
            job_id="job-test",
            run_id="run-test",
            workspace_binding=binding,
        )
        action = _make_action(
            cwd=str(tmp_path / "repo")
        )

        with pytest.raises(
            ValueError, match="run_dir"
        ):
            runner.run(
                action,
                run_dir="/wrong/path",
                stage="executor",
                runtime_context=ctx,
            )
