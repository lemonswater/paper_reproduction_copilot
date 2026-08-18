from __future__ import annotations

"""Phase 27 容器崩溃恢复与精确 reconcile。

Worker 每轮 claim 前先扫描当前项目管理的未终态 record，但只能处理精确 ID。

最危险的错误是"查不到就重跑"。它可能造成训练任务实际仍运行，
却启动第二份副作用。因此 ``container not found`` 必须返回 ambiguous。
"""


from datetime import datetime, timezone
from pathlib import Path

from app.execution.container_engine import ContainerEngine
from app.execution.container_errors import (
    ContainerIdentityMismatch,
)
from app.execution.container_records import (
    write_container_record,
)
from app.execution.container_schemas import (
    ContainerRuntimeRecord,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContainerReconciler:
    """容器状态 reconciler，只操作精确 container ID。"""

    def __init__(self, engine: ContainerEngine):
        self.engine = engine

    def reconcile(
        self,
        record: ContainerRuntimeRecord,
        run_dir: Path,
    ) -> str:
        """检查容器当前状态并更新 record。

        返回 reconcile 决策字符串：

        - ``active_requires_ownership_check``: 容器仍在运行，
          是否 stop 取决于 Job claim 是否仍有效。
        - ``exited_requires_job_reconciliation``: 容器已退出，
          记录 exit code，恢复 Job 或人工判定。
        - ``ambiguous_container_missing``: 容器不存在但 record
          非终态，禁止自动重跑。
        - ``already_terminal``: record 已是终态，无需操作。
        """

        if record.status in {"removed", "reconciliation_required"}:
            return "already_terminal"

        try:
            inspected = self.engine.inspect(
                record.container_id
            )
        except Exception:  # noqa: BLE001
            # inspect 失败：不能证明容器已停止，禁止自动重跑。
            record.status = "reconciliation_required"
            record.updated_at = _now_iso()
            write_container_record(run_dir, record)
            return "ambiguous_container_missing"

        # 先验证 identity，再做任何 stop/remove。
        expected_ownership = record.ownership_token_hash
        labels = inspected.labels
        if (
            labels.get("io.paper-copilot.managed") != "true"
            or labels.get("io.paper-copilot.job-id")
            != record.job_id
            or labels.get("io.paper-copilot.ownership-hash")
            != expected_ownership
        ):
            raise ContainerIdentityMismatch(
                "reconcile ownership mismatch"
            )

        if inspected.running:
            # 是否 stop 取决于当前 Job claim 是否仍有效；
            # 不能只看 record 时间。
            record.status = "running"
            record.updated_at = _now_iso()
            write_container_record(run_dir, record)
            return "active_requires_ownership_check"

        record.status = "exited"
        record.exit_code = inspected.exit_code
        record.oom_killed = inspected.oom_killed
        record.updated_at = _now_iso()
        write_container_record(run_dir, record)
        return "exited_requires_job_reconciliation"
