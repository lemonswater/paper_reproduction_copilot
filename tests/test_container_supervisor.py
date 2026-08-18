"""Phase 27 ContainerSupervisor 测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.execution.container_errors import (
    ContainerIdentityMismatch,
    ContainerStateAmbiguous,
)
from app.execution.container_records import (
    load_container_record,
)
from app.execution.container_schemas import (
    ContainerInspect,
    ContainerPlan,
)
from app.execution.container_supervisor import (
    ContainerSupervisor,
)
from tests.fakes.fake_container_engine import (
    FakeContainerEngine,
)


def _make_plan(
    *,
    ownership_hash: str = "a" * 64,
) -> ContainerPlan:
    return ContainerPlan(
        job_id="job-test",
        run_id="run-test",
        ownership_token_hash=ownership_hash,
        image_ref=(
            "docker.io/library/python@sha256:"
            + "a" * 64
        ),
        name="prc-job-test-aaaaaaaaaaaa",
        workdir="/workspace/repo",
        argv=["python", "-c", "print('hello')"],
        env={},
        mounts=[],
        labels={
            "io.paper-copilot.managed": "true",
            "io.paper-copilot.job-id": "job-test",
            "io.paper-copilot.run-id": "run-test",
            "io.paper-copilot.ownership-hash": (
                ownership_hash
            ),
        },
        memory_bytes=512 * 1024 * 1024,
        cpus=2.0,
        pids_limit=256,
        tmpfs_bytes=128 * 1024 * 1024,
    )


def _make_inspect(
    *,
    container_id: str = "a" * 64,
    running: bool = False,
    exit_code: int = 0,
    oom_killed: bool = False,
    ownership_hash: str = "a" * 64,
) -> ContainerInspect:
    return ContainerInspect(
        container_id=container_id,
        name="prc-job-test-aaaaaaaaaaaa",
        running=running,
        status="exited" if not running else "running",
        exit_code=exit_code,
        oom_killed=oom_killed,
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


class TestContainerSupervisorExecute:
    def test_create_record_start_inspect_order(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect()
        supervisor = ContainerSupervisor(engine=engine)
        plan = _make_plan()

        record = supervisor.execute(
            plan=plan, run_dir=tmp_path
        )

        call_types = [c[0] for c in engine.calls]
        assert call_types == [
            "create",
            "start_attach",
            "inspect",
        ]
        assert record.status == "exited"
        assert record.exit_code == 0

    def test_record_persisted_before_start(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect()
        supervisor = ContainerSupervisor(engine=engine)
        plan = _make_plan()

        record = supervisor.execute(
            plan=plan, run_dir=tmp_path
        )

        # record 文件在 execute 后存在
        loaded = load_container_record(tmp_path)
        assert loaded is not None
        assert loaded.container_id == record.container_id
        assert loaded.status == "exited"

    def test_attach_zero_but_running_raises_ambiguous(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.start_attach_code = 0
        engine.inspect_result = _make_inspect(
            running=True
        )
        supervisor = ContainerSupervisor(engine=engine)
        plan = _make_plan()

        with pytest.raises(ContainerStateAmbiguous):
            supervisor.execute(
                plan=plan, run_dir=tmp_path
            )

        loaded = load_container_record(tmp_path)
        assert loaded is not None
        assert (
            loaded.status == "reconciliation_required"
        )

    def test_oom_killed_written_to_record(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect(
            exit_code=137, oom_killed=True
        )
        supervisor = ContainerSupervisor(engine=engine)
        plan = _make_plan()

        record = supervisor.execute(
            plan=plan, run_dir=tmp_path
        )

        assert record.oom_killed is True
        assert record.exit_code == 137

    def test_ownership_mismatch_rejected(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect(
            ownership_hash="b" * 64,
        )
        supervisor = ContainerSupervisor(engine=engine)
        plan = _make_plan()

        with pytest.raises(ContainerIdentityMismatch):
            supervisor.execute(
                plan=plan, run_dir=tmp_path
            )

    def test_container_id_mismatch_rejected(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.create_container_id = "a" * 64
        engine.inspect_result = _make_inspect(
            container_id="b" * 64,
        )
        supervisor = ContainerSupervisor(engine=engine)
        plan = _make_plan()

        with pytest.raises(ContainerIdentityMismatch):
            supervisor.execute(
                plan=plan, run_dir=tmp_path
            )


class TestContainerSupervisorStopAndRemove:
    def test_stop_and_remove_exited_container(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_result = _make_inspect(
            running=False, exit_code=0
        )
        supervisor = ContainerSupervisor(engine=engine)

        from datetime import datetime, timezone

        from app.execution.container_schemas import (
            ContainerRuntimeRecord,
        )

        now = datetime.now(timezone.utc).isoformat()
        record = ContainerRuntimeRecord(
            job_id="job-test",
            run_id="run-test",
            ownership_token_hash="a" * 64,
            container_id="a" * 64,
            container_name="prc-test",
            image_ref="sha256:" + "a" * 64,
            plan_sha256="d" * 64,
            status="exited",
            created_at=now,
            updated_at=now,
        )

        result = supervisor.stop_and_remove(
            record=record, run_dir=tmp_path
        )

        assert result.status == "removed"
        assert engine.was_removed("a" * 64)

    def test_stop_running_container_then_remove(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        # First inspect: running; after stop: not running
        engine.inspect_result = _make_inspect(
            running=True
        )
        supervisor = ContainerSupervisor(engine=engine)

        from datetime import datetime, timezone

        from app.execution.container_schemas import (
            ContainerRuntimeRecord,
        )

        now = datetime.now(timezone.utc).isoformat()
        record = ContainerRuntimeRecord(
            job_id="job-test",
            run_id="run-test",
            ownership_token_hash="a" * 64,
            container_id="a" * 64,
            container_name="prc-test",
            image_ref="sha256:" + "a" * 64,
            plan_sha256="d" * 64,
            status="exited",
            created_at=now,
            updated_at=now,
        )

        # After stop, update inspect to not running
        def inspect_side_effect(container_id: str):
            if engine.was_stopped(container_id):
                return _make_inspect(running=False)
            return _make_inspect(running=True)

        engine.inspect = inspect_side_effect  # type: ignore

        result = supervisor.stop_and_remove(
            record=record, run_dir=tmp_path
        )

        assert result.status == "removed"
        assert engine.was_stopped("a" * 64)
        assert engine.was_removed("a" * 64)

    def test_inspect_failure_writes_reconciliation(
        self, tmp_path: Path
    ) -> None:
        engine = FakeContainerEngine()
        engine.inspect_should_raise = True
        supervisor = ContainerSupervisor(engine=engine)

        from datetime import datetime, timezone

        from app.execution.container_schemas import (
            ContainerRuntimeRecord,
        )

        now = datetime.now(timezone.utc).isoformat()
        record = ContainerRuntimeRecord(
            job_id="job-test",
            run_id="run-test",
            ownership_token_hash="a" * 64,
            container_id="a" * 64,
            container_name="prc-test",
            image_ref="sha256:" + "a" * 64,
            plan_sha256="d" * 64,
            status="exited",
            created_at=now,
            updated_at=now,
        )

        result = supervisor.stop_and_remove(
            record=record, run_dir=tmp_path
        )

        assert (
            result.status == "reconciliation_required"
        )
        assert not engine.was_removed("a" * 64)
