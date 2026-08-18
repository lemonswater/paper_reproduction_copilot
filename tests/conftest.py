from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from os import getpid
from pathlib import Path
from uuid import uuid4

import pytest

from app.config import settings
from app.nodes.run_context_node import run_context_node
from app.schemas import (
    PatchBundle,
    PatchFileRecord,
    PatchVerificationCheck,
    PatchVerificationReport,
)
from app.tools.patch_tools import (
    build_unified_diff,
    compute_verification_hash,
    sha256_file,
    sha256_text,
)


def pytest_configure(
    config: pytest.Config,
) -> None:
    """
    公共服务器上不把 pytest 临时文件写到系统 /tmp。

    每个 pytest 进程使用独立 basetemp，避免并行测试互相清理同一个目录。
    """

    config.addinivalue_line(
        "markers",
        "postgres: 需要 TEST_DATABASE_URL 的 PostgreSQL integration test",
    )
    project_root = Path(
        str(config.rootpath)
    ).resolve()
    config.option.basetemp = str(
        project_root
        / ".pytest-tmp"
        / f"pytest-{getpid()}-{uuid4().hex[:8]}"
    )


@pytest.fixture
def postgres_engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("未设置 TEST_DATABASE_URL")

    import sqlalchemy as sa

    from app.persistence.tables import metadata

    engine = sa.create_engine(
        url,
        pool_pre_ping=True,
    )
    metadata.drop_all(engine)
    metadata.create_all(engine)
    try:
        yield engine
    finally:
        metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def require_postgres_url_for_marked_test(
    request: pytest.FixtureRequest,
):
    if (
        request.node.get_closest_marker("postgres") is not None
        and not os.getenv("TEST_DATABASE_URL")
    ):
        pytest.skip("未设置 TEST_DATABASE_URL")


@pytest.fixture(autouse=True)
def skip_container_runtime_unless_enabled(
    request: pytest.FixtureRequest,
):
    """真实 Podman/容器测试默认跳过，避免普通 pytest 操作宿主机容器。"""

    if (
        request.node.get_closest_marker("container_runtime")
        is not None
        and not os.getenv("ENABLE_CONTAINER_INTEGRATION_TESTS", "").lower()
        == "true"
    ):
        pytest.skip(
            "未设置 ENABLE_CONTAINER_INTEGRATION_TESTS=true"
        )


@pytest.fixture
def run_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """为会写 Artifact 的节点创建真实且隔离的 run context。"""

    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")
    state = {
        "task_id": "phase15-test",
        "output_files": [],
        "artifact_records": [],
        "stage_errors": [],
    }
    state.update(run_context_node(state))
    return state


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """测试只执行固定 Git token，不经过 shell。"""

    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )


@pytest.fixture
def valid_report(
    patch_bundle: PatchBundle,
    tmp_path: Path,
) -> PatchVerificationReport:
    """构造语义有效且 embedded hash 正确的验证报告。"""

    checks = [
        PatchVerificationCheck(
            name="git_apply_check",
            status="passed",
        ),
        PatchVerificationCheck(name="git_apply", status="passed"),
        PatchVerificationCheck(name="after_sha256", status="passed"),
        PatchVerificationCheck(
            name="worktree_diff_scope",
            status="passed",
        ),
        PatchVerificationCheck(name="python_syntax", status="passed"),
        PatchVerificationCheck(name="targeted_tests", status="passed"),
    ]
    report = PatchVerificationReport(
        patch_id=patch_bundle.patch_id,
        patch_sha256=patch_bundle.patch_sha256,
        execution_profile_id="local",
        execution_profile_fingerprint="b" * 64,
        execution_backend="local",
        status="behaviorally_verified",
        promotion_allowed=True,
        structural_checks_passed=True,
        behavioral_checks_run=1,
        behavioral_checks_passed=1,
        worktree_path=str(
            tmp_path / "fixture-worktree"
        ),
        worktree_diff_sha256="c" * 64,
        checks=checks,
        summary="fixture verification passed",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return report.model_copy(
        update={"verification_sha256": compute_verification_hash(report)}
    )


@pytest.fixture
def patch_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> PatchBundle:
    """创建包含一个目标文件和一个额外 tracked 文件的真实 Git 仓库。"""

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "Tests")

    target = repo / "train.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "extra.py").write_text("EXTRA = 1\n", encoding="utf-8")
    _git(repo, "add", "train.py", "extra.py")
    _git(repo, "commit", "-m", "initial")

    before = target.read_text(encoding="utf-8")
    after = "VALUE = 2\n"
    patch_text = build_unified_diff("train.py", before, after)

    patch_dir = tmp_path / "bundle"
    patch_dir.mkdir()
    patch_path = patch_dir / "patch.diff"
    patch_path.write_text(patch_text, encoding="utf-8")

    # Lock 和 journal 都隔离到 pytest 临时目录，避免污染 runs/。
    coordination_dir = tmp_path / "coordination"
    monkeypatch.setattr(
        settings,
        "patch_coordination_dir",
        coordination_dir,
    )
    monkeypatch.setattr(
        settings,
        "patch_repo_lock_timeout_seconds",
        0.0,
    )

    return PatchBundle(
        patch_id="patch_fixture",
        proposal_id="proposal_fixture",
        repo_path=str(repo.resolve()),
        base_git_commit=_git(repo, "rev-parse", "HEAD").stdout.strip(),
        patch_path=str(patch_path.resolve()),
        patch_sha256=sha256_file(patch_path),
        files=[
            PatchFileRecord(
                relative_path="train.py",
                before_sha256=sha256_text(before),
                after_sha256=sha256_text(after),
                replacement_count=1,
                changed_line_count=1,
            )
        ],
        summary="change fixture value",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def verified_worktree(
    patch_bundle: PatchBundle,
    tmp_path: Path,
):
    """创建 HEAD 正确、且已精确应用 bundle 的 detached worktree。"""

    source_repo = Path(patch_bundle.repo_path)
    worktree = tmp_path / "verified-worktree"
    _git(
        source_repo,
        "worktree",
        "add",
        "--detach",
        str(worktree),
        patch_bundle.base_git_commit,
    )
    _git(worktree, "apply", patch_bundle.patch_path)

    try:
        yield worktree
    finally:
        subprocess.run(
            [
                "git",
                "-C",
                str(source_repo),
                "worktree",
                "remove",
                "--force",
                str(worktree),
            ],
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
