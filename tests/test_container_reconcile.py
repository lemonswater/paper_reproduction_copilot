"""Phase 27 容器 reconcile 测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.execution.container_errors import (
    ContainerIdentityMismatch,
)
from app.execution.container_reconcile import (
    ContainerReconciler,
)
from app.execution.container_schemas import (
    ContainerInspect,
    ContainerRuntimeRecord,
)
from tests.fakes.fake_container_engine import (
    FakeContainerEngine,
)


def _make_record(
    *,
    status: str = "created",
    ownership_hash: str = "a" * 64,
    container_id: str = "a" * 64,
) -> ContainerRuntimeRecord:
    now = datetime.now(timezone.utc).isoformat()
    return ContainerRuntimeRecord(
        job_id="job-test",
        run_id="run-test",
        ownership_token_hash=ownership_hash,
        container_id=container_id,
        container_name="prc-test",
        image_ref="sha256:" + "a" * 64,
        plan_sha256="d" * 64,
        status=status,
        created_at=now,
        updated_at=now,
    )


def _make_inspect(
    *,
    running: bool = False,
    exit_code: int = 0,
    ownership_hash: str = "a" * 64,
    container_id: str = "a" * 64,
) -> ContainerInspect:
    return ContainerInspect(
        container_id=container_id,
        name="prc-test",
        running=running,
        status="exited" if not running else "running",
        exit_code=exit_code,
        oom_killed=False,
        image_digest="sha256:" + "a" * 64,
        labels={
            "io.paper-copilot.managed": "true",
            "io.paper-copilot.job-id": "job-test",
            "io.paper-copilot.run-id": "run-test",
            "io.paper-copilot.ownership-hash": (
                ownership_hash
            ),
        },
    )


class TestContainerReconciler:
    def test_running_container_returns_active(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect(
            running=True
        )
        reconciler = ContainerReconciler(engine=engine)
        record = _make_record(status="created")

        result = reconciler.reconcile(
            record, run_dir=tmp_path
        )

        assert (
            result == "active_requires_ownership_check"
        )

    def test_exited_container_returns_reconciliation(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect(
            exit_code=42
        )
        reconciler = ContainerReconciler(engine=engine)
        record = _make_record(status="running")

        result = reconciler.reconcile(
            record, run_dir=tmp_path
        )

        assert (
            result
            == "exited_requires_job_reconciliation"
        )
        loaded = record
        assert loaded.status == "exited"
        assert loaded.exit_code == 42

    def test_container_missing_returns_ambiguous(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_should_raise = True
        reconciler = ContainerReconciler(engine=engine)
        record = _make_record(status="running")

        result = reconciler.reconcile(
            record, run_dir=tmp_path
        )

        assert result == "ambiguous_container_missing"
        assert (
            record.status == "reconciliation_required"
        )

    def test_ownership_mismatch_raises(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect(
            ownership_hash="b" * 64,
        )
        reconciler = ContainerReconciler(engine=engine)
        record = _make_record(status="created")

        with pytest.raises(
            ContainerIdentityMismatch
        ):
            reconciler.reconcile(
                record, run_dir=tmp_path
            )

    def test_already_terminal_returns_noop(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        reconciler = ContainerReconciler(engine=engine)
        record = _make_record(status="removed")

        result = reconciler.reconcile(
            record, run_dir=tmp_path
        )

        assert result == "already_terminal"
        # 不应该调用任何 engine 方法
        assert engine.calls == []

    def test_reconciliation_required_returns_noop(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        reconciler = ContainerReconciler(engine=engine)
        record = _make_record(
            status="reconciliation_required"
        )

        result = reconciler.reconcile(
            record, run_dir=tmp_path
        )

        assert result == "already_terminal"
        assert engine.calls == []
