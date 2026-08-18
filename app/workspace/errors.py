from __future__ import annotations

class WorkspaceError(RuntimeError):
    """Workspace 子系统错误基类。"""


class WorkspaceIntegrityError(WorkspaceError):
    """Manifest、Blob、路径或 Git identity 校验失败。"""


class WorkspaceNotPortableError(WorkspaceError):
    """当前 workspace 只能由 affinity host 继续。"""


class WorkerCapabilityError(WorkspaceError):
    """Worker capability 配置不合法或不满足 Job。"""


class WorkspaceFencedError(WorkspaceError):
    """旧 claim/session 尝试更新当前 workspace pointer。"""
