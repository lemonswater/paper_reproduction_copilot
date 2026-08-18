"""Phase 30 测试共用 fixtures。

不从产品源码导入私有 helper，也不修改产品源码来复用测试代码。
"""

from __future__ import annotations

from app.interaction.schemas import (
    JobView,
    PublicJobInput,
)


def make_job(**updates) -> JobView:
    """构造一个可定制的公开 JobView，供 timeline / UI API 测试共用。"""

    values = {
        "job_id": "job-1",
        "thread_id": "thread-1",
        "run_id": "run-1",
        "status": "running",
        "version": 2,
        "attempt_count": 1,
        "max_attempts": 3,
        "wait_generation": 0,
        "interrupt_nodes": [],
        "interrupts": [],
        "cancel_requested": False,
        "input": PublicJobInput(
            paper_name="paper:r-paper",
            repo_name="git_repository:r-repo",
            experiment_goal="reproduce main result",
            execution_profile_id="local",
        ),
        "allowed_operations": [],
        "created_at": "2026-08-01T00:00:00+00:00",
        "updated_at": "2026-08-01T00:01:00+00:00",
    }
    values.update(updates)
    return JobView(**values)
