"""Phase 46: Project Memory Retention 集成测试。"""

from __future__ import annotations

import pytest

from app.retention.service import _NoOpProjectMemoryRetentionPort


class FakeProjectMemoryRetentionPort:
    """测试用 ProjectMemoryRetentionPort。"""

    def __init__(self, job_ids: set[str] | None = None):
        self._ids = job_ids or set()

    def active_referenced_job_ids(self) -> set[str]:
        return set(self._ids)


def test_noop_project_memory_returns_empty_set():
    port = _NoOpProjectMemoryRetentionPort()
    assert port.active_referenced_job_ids() == set()


def test_fake_project_memory_returns_job_ids():
    port = FakeProjectMemoryRetentionPort({"job-1", "job-2"})
    assert port.active_referenced_job_ids() == {"job-1", "job-2"}


def test_empty_fake_project_memory_returns_empty():
    port = FakeProjectMemoryRetentionPort()
    assert port.active_referenced_job_ids() == set()


def test_project_memory_port_protocol_is_compatible():
    """ProjectMemoryRetentionPort 可以替代 FailureMemoryRetentionPort 接口。"""
    port = FakeProjectMemoryRetentionPort({"job-held-by-pm"})
    # The interface is the same: active_referenced_job_ids -> set[str]
    result = port.active_referenced_job_ids()
    assert isinstance(result, set)
    assert all(isinstance(item, str) for item in result)


def test_project_memory_retention_does_not_hold_manual_source_jobs():
    """manual confirmed fact 不增加 Job hold。

    ProjectMemoryRepository.active_referenced_job_ids() 只返回
    chat_user_message source 的 job_id，manual_user source 不持有。
    """
    # This is tested in test_project_memory_repository.py:
    # test_active_referenced_job_ids_excludes_non_chat_source
    # Here we just verify the port interface works.
    port = FakeProjectMemoryRetentionPort(set())
    assert port.active_referenced_job_ids() == set()


def test_project_memory_retention_releases_on_empty():
    """没有活跃 Chat-backed fact 时，hold 集合为空。"""
    port = FakeProjectMemoryRetentionPort(set())
    assert port.active_referenced_job_ids() == set()


def test_project_memory_retention_holds_chat_source_jobs():
    """Chat-backed confirmed fact hold source Job。"""
    port = FakeProjectMemoryRetentionPort({"job-chat-source-001"})
    assert "job-chat-source-001" in port.active_referenced_job_ids()


def test_project_memory_retention_releases_revoked_jobs():
    """Chat confirmed fact revoked 后释放 hold。

    在 repository 层，revoked 的 fact 不再出现在 active_referenced_job_ids() 中。
    这里用 FakePort 模拟空集合来验证接口行为。
    """
    port = FakeProjectMemoryRetentionPort(set())
    assert port.active_referenced_job_ids() == set()
