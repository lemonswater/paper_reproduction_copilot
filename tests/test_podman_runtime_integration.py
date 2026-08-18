"""Phase 27 真实 CPU Podman integration test。

默认 skip；必须显式设置 ``ENABLE_CONTAINER_INTEGRATION_TESTS=true``
和 ``TEST_OCI_IMAGE`` 环境变量。

第一轮只用 CPU 小镜像验证边界，不直接训练 PSTNet。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.container_runtime


def require_container_runtime() -> None:
    if (
        os.getenv("ENABLE_CONTAINER_INTEGRATION_TESTS")
        != "true"
    ):
        pytest.skip(
            "set ENABLE_CONTAINER_INTEGRATION_TESTS=true explicitly"
        )


def _get_test_image() -> str:
    image = os.getenv("TEST_OCI_IMAGE")
    if not image:
        pytest.skip(
            "set TEST_OCI_IMAGE to a digest-pinned image ref"
        )
    return image


def test_runtime_probe_rootless_and_cgroup_v2() -> None:
    require_container_runtime()
    from app.execution.podman_engine import PodmanEngine

    engine = PodmanEngine()
    probe = engine.probe()
    assert probe.runtime == "podman"
    assert probe.rootless is True
    assert probe.cgroup_version in {"v2", "2"}


def test_image_exists() -> None:
    require_container_runtime()
    from app.execution.podman_engine import PodmanEngine

    image_ref = _get_test_image()
    engine = PodmanEngine()
    assert engine.image_exists(image_ref)


def test_cpu_smoke_write_run_dir_success(
    tmp_path: Path,
) -> None:
    """容器内写 /workspace/run/smoke.txt 应成功。"""

    require_container_runtime()
    from app.execution.container_engine import (
        ContainerEngine,
    )
    from app.execution.container_plan import (
        build_podman_create_tokens,
    )
    from app.execution.container_schemas import (
        ContainerMount,
        ContainerPlan,
    )
    from app.execution.podman_engine import PodmanEngine

    image_ref = _get_test_image()
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True)
    (run_root / "smoke.txt").unlink(missing_ok=True)

    plan = ContainerPlan(
        job_id="job-smoke",
        run_id="run-smoke",
        ownership_token_hash="a" * 64,
        image_ref=image_ref,
        name="prc-smoke-test",
        workdir="/workspace/run",
        argv=[
            "python",
            "-c",
            "open('/workspace/run/smoke.txt','w').write('ok')",
        ],
        env={},
        mounts=[
            ContainerMount(
                host_path=str(run_root),
                container_path="/workspace/run",
                mode="rw",
            )
        ],
        labels={
            "io.paper-copilot.managed": "true",
            "io.paper-copilot.job-id": "job-smoke",
            "io.paper-copilot.run-id": "run-smoke",
            "io.paper-copilot.ownership-hash": "a" * 64,
        },
        memory_bytes=512 * 1024 * 1024,
        cpus=1.0,
        pids_limit=128,
        tmpfs_bytes=64 * 1024 * 1024,
    )
    tokens = build_podman_create_tokens(plan)

    engine: ContainerEngine = PodmanEngine()
    container_id = engine.create(tokens)
    try:
        engine.start_attach(container_id)
        inspected = engine.inspect(container_id)
        assert not inspected.running
        assert inspected.exit_code == 0
        assert (run_root / "smoke.txt").read_text() == "ok"
    finally:
        try:
            engine.remove(container_id)
        except Exception:  # noqa: BLE001, S110
            pass


def test_write_to_readonly_rootfs_fails(
    tmp_path: Path,
) -> None:
    """写 /etc/forbidden 应失败（read-only rootfs）。"""

    require_container_runtime()
    from app.execution.container_engine import (
        ContainerEngine,
    )
    from app.execution.container_plan import (
        build_podman_create_tokens,
    )
    from app.execution.container_schemas import (
        ContainerMount,
        ContainerPlan,
    )
    from app.execution.podman_engine import PodmanEngine

    image_ref = _get_test_image()
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True)

    plan = ContainerPlan(
        job_id="job-readonly",
        run_id="run-readonly",
        ownership_token_hash="b" * 64,
        image_ref=image_ref,
        name="prc-readonly-test",
        workdir="/workspace/run",
        argv=[
            "python",
            "-c",
            "open('/etc/forbidden','w').write('x')",
        ],
        env={},
        mounts=[
            ContainerMount(
                host_path=str(run_root),
                container_path="/workspace/run",
                mode="rw",
            )
        ],
        labels={
            "io.paper-copilot.managed": "true",
            "io.paper-copilot.job-id": "job-readonly",
            "io.paper-copilot.run-id": "run-readonly",
            "io.paper-copilot.ownership-hash": "b" * 64,
        },
        memory_bytes=512 * 1024 * 1024,
        cpus=1.0,
        pids_limit=128,
        tmpfs_bytes=64 * 1024 * 1024,
    )
    tokens = build_podman_create_tokens(plan)

    engine: ContainerEngine = PodmanEngine()
    container_id = engine.create(tokens)
    try:
        engine.start_attach(container_id)
        inspected = engine.inspect(container_id)
        assert not inspected.running
        assert inspected.exit_code != 0
    finally:
        try:
            engine.remove(container_id)
        except Exception:  # noqa: BLE001, S110
            pass
