from __future__ import annotations

import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from app.execution.cancellation import (
    list_runtime_records,
    write_runtime_record,
)
from app.job_runtime.schemas import (
    JobRecord,
    ReconcileDecision,
)
from app.job_runtime.errors import (
    JobConflictError,
    LeaseLostError,
)
from app.job_runtime.store import (
    SqliteJobStore,
)
from app.workspace.paths import require_managed_run_root


ACTIVE_PROCESS_STATUSES = {
    "starting",
    "running",
    "terminating",
}

PATH_BOUND_INTERRUPT_NODES = {
    "human_review",
    "patch_review",
    "patch_promotion_review",
}


def workspace_portability_blockers(
    *,
    run_dir: str,
    interrupt_nodes: list[str],
    state: dict[str, Any],
) -> list[str]:
    """只返回原因，不执行 requeue、kill 或文件修改。"""

    blockers: list[str] = []

    if set(interrupt_nodes).intersection(
        PATH_BOUND_INTERRUPT_NODES
    ):
        blockers.append(
            "path_bound_approval_interrupt"
        )

    # 已构造的 action/patch 通常包含绝对 cwd、repo path 和审批 hash。
    if state.get("pending_action") is not None:
        blockers.append(
            "pending_action_contains_local_paths"
        )
    if state.get("pending_patch") is not None:
        blockers.append(
            "pending_patch_contains_local_paths"
        )
    if state.get("patch_approval_record") is not None:
        blockers.append(
            "patch_approval_is_path_bound"
        )

    run_root = require_managed_run_root(run_dir)
    records = list_runtime_records(run_root)
    active = [
        item
        for item in records
        if item.get("status")
        in ACTIVE_PROCESS_STATUSES
    ]
    if active:
        blockers.append(
            "active_or_ambiguous_subprocess"
        )

    return sorted(set(blockers))


def _parse_iso(value: str | None) -> float:
    if not value:
        return 0.0
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).timestamp()


def _record_started_after_claim(
    record: dict[str, Any],
    claimed_at: str | None,
) -> bool:
    # 缺时间戳时采用保守语义，不能因字段缺失自动重跑。
    started_at = record.get("started_at")
    if not started_at or not claimed_at:
        return True
    return _parse_iso(
        str(started_at)
    ) >= _parse_iso(claimed_at)


def _process_identity_is_alive(
    record: dict[str, Any],
) -> bool:
    pid = record.get("pid")
    expected_create_time = record.get(
        "process_create_time"
    )
    expected_pgid = record.get("pgid")
    if (
        not isinstance(pid, int)
        or not isinstance(
            expected_create_time,
            (int, float),
        )
        or not isinstance(expected_pgid, int)
    ):
        return False

    try:
        process = psutil.Process(pid)
        actual_create_time = process.create_time()
        actual_pgid = os.getpgid(pid)
    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
        ProcessLookupError,
        PermissionError,
    ):
        return False

    return (
        abs(
            actual_create_time
            - float(expected_create_time)
        )
        < 1e-3
        and actual_pgid == expected_pgid
    )


def inspect_job_processes(
    job: JobRecord,
) -> ReconcileDecision:
    run_dir = Path(job.run_dir)
    if not run_dir.is_dir():
        return ReconcileDecision(
            disposition="safe_to_requeue",
            detail="run_dir 尚未创建，没有进程副作用记录",
            process_records=[],
        )

    records = [
        item
        for item in list_runtime_records(run_dir)
        if _record_started_after_claim(
            item,
            job.claimed_at,
        )
    ]
    if not records:
        return ReconcileDecision(
            disposition="safe_to_requeue",
            detail="本次 claim 后没有受监管进程记录",
            process_records=[],
        )

    active_records = [
        item
        for item in records
        if item.get("status")
        in ACTIVE_PROCESS_STATUSES
    ]
    live_records = [
        item
        for item in active_records
        if _process_identity_is_alive(item)
    ]

    if live_records:
        return ReconcileDecision(
            disposition="active_process",
            detail=(
                "worker lease 已过期，但精确 PID/create_time/PGID "
                "对应的受监管进程仍存活"
            ),
            process_records=live_records,
        )

    if active_records:
        return ReconcileDecision(
            disposition="ambiguous_process",
            detail=(
                "存在 active ProcessRecord，但无法确认对应进程仍存活；"
                "副作用结果不确定"
            ),
            process_records=active_records,
        )

    finished_records = [
        item
        for item in records
        if item.get("status") == "finished"
    ]
    if finished_records:
        return ReconcileDecision(
            disposition=(
                "finished_process_without_checkpoint"
            ),
            detail=(
                "本次 claim 后已有 finished ProcessRecord，"
                "但 Job 未提交终态；禁止自动重复执行"
            ),
            process_records=finished_records,
        )

    return ReconcileDecision(
        disposition="ambiguous_process",
        detail="发现无法识别的进程记录状态",
        process_records=records,
    )


class JobReconciler:
    def __init__(
        self,
        *,
        store: SqliteJobStore,
        actor: str,
        host_id: str | None = None,
    ):
        self.store = store
        self.actor = actor
        self.host_id = host_id

    def reconcile_expired(
        self,
        *,
        now: float | None = None,
    ) -> int:
        jobs = self.store.list_expired_running(
            now=now
        )
        changed = 0
        for job in jobs:
            token = job.claim_token
            if token is None:
                continue

            decision = inspect_job_processes(job)
            try:
                if (
                    decision.disposition
                    == "safe_to_requeue"
                ):
                    self.store.requeue_expired(
                        job_id=job.job_id,
                        expired_claim_token=token,
                        detail=decision.detail,
                        actor=self.actor,
                        now=now,
                    )
                else:
                    self.store.require_reconciliation(
                        job_id=job.job_id,
                        expired_claim_token=token,
                        reconciliation=(
                            decision.model_dump()
                        ),
                        actor=self.actor,
                        now=now,
                    )
                changed += 1
            except LeaseLostError:
                # heartbeat 与 reconcile 竞争是正常并发结果。
                continue
        return changed

    def resolve(
        self,
        *,
        job_id: str,
        decision: str,
        confirm_requeue: bool = False,
    ) -> JobRecord:
        """
        - failed：人工判定失败；
        - cancelled：精确进程仍活着时先终止进程组；
        - requeue：确认没有活动进程并显式承担重跑风险。
        """

        job = self.store.get(job_id)
        if job.status != "reconciliation_required":
            raise JobConflictError(
                "Job 当前不需要 reconciliation"
            )

        current = inspect_job_processes(job)

        if decision == "requeue":
            if not confirm_requeue:
                raise JobConflictError(
                    "requeue 可能重复副作用，必须显式确认"
                )
            if (
                current.disposition
                == "active_process"
            ):
                raise JobConflictError(
                    "仍有精确匹配的活动进程，禁止 requeue"
                )
            return self.store.resolve_reconciliation(
                job_id=job_id,
                decision="requeue",
                detail=(
                    "operator confirmed requeue; "
                    + current.detail
                ),
                actor=self.actor,
            )

        if decision == "failed":
            return self.store.resolve_reconciliation(
                job_id=job_id,
                decision="failed",
                detail=current.detail,
                actor=self.actor,
            )

        if decision == "cancelled":
            for record in current.process_records:
                if _process_identity_is_alive(
                    record
                ):
                    terminate_recorded_process_group(
                        job=job,
                        record=record,
                    )
            return self.store.resolve_reconciliation(
                job_id=job_id,
                decision="cancelled",
                detail=(
                    "operator cancelled ambiguous "
                    "or orphaned process"
                ),
                actor=self.actor,
            )

        raise ValueError(
            f"不支持的 reconciliation decision：{decision}"
        )


def terminate_recorded_process_group(
    *,
    job: JobRecord,
    record: dict[str, Any],
    grace_seconds: float = 5.0,
) -> None:
    """
    只终止 ProcessRecord 中经过 PID/create_time/PGID 校验的进程组。
    """

    if not _process_identity_is_alive(record):
        return

    pid = int(record["pid"])
    pgid = int(record["pgid"])

    # Supervisor 使用 start_new_session=True，正常情况下 pid == pgid。
    if pid != pgid:
        raise JobConflictError(
            "记录中的 pid != pgid，拒绝终止未知进程组"
        )

    os.killpg(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if not _process_identity_is_alive(record):
            break
        time.sleep(0.1)
    else:
        # SIGKILL 前再次校验，避免等待期间 PID 被复用。
        if _process_identity_is_alive(record):
            os.killpg(pgid, signal.SIGKILL)

    kill_deadline = time.monotonic() + 2.0
    while (
        _process_identity_is_alive(record)
        and time.monotonic() < kill_deadline
    ):
        time.sleep(0.05)
    if _process_identity_is_alive(record):
        raise JobConflictError(
            "进程组在终止请求后仍然存活"
        )

    updated = {
        **record,
        "status": "finished",
        "finished_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "end_reason": "orphan_cleanup",
        "cancellation_requested": True,
        "cancellation_reason": (
            "job reconciliation cancelled orphan"
        ),
    }
    write_runtime_record(
        run_dir=job.run_dir,
        execution_id=str(record["execution_id"]),
        payload=updated,
    )