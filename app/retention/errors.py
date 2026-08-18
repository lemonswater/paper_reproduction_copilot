"""Retention 领域错误定义。"""

class RetentionError(RuntimeError):
    """Retention 领域错误基类。"""


class RetentionNotFound(RetentionError):
    """Plan 或 Hold 不存在。"""


class RetentionConflict(RetentionError):
    """状态、版本、确认哈希或身份已经变化。"""


class RetentionBackendUnsupported(RetentionError):
    """当前 backend 只允许盘点，不允许 destructive sweep。"""


class StorageCapacityExceeded(RetentionError):
    """新任务会突破硬配额或最小剩余空间。"""


class RetentionPathUnsafe(RetentionError):
    """候选路径不满足 allowlist、identity 或 symlink 约束。"""