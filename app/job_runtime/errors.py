from __future__ import annotations

class JobStoreError(RuntimeError):
    """Job control plane 错误基类。"""


class JobNotFoundError(JobStoreError):
    """目标 Job 不存在。"""


class JobConflictError(JobStoreError):
    """幂等身份、版本或当前状态冲突。"""


class LeaseLostError(JobStoreError):
    """claim token 已失效，旧 owner 不得继续写状态。"""


class JobBackendUnavailable(JobStoreError):
    """数据库连接或后端暂时不可用。"""