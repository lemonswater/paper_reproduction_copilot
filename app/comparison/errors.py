class ComparisonError(RuntimeError):
    """Comparison 子系统的公开错误基类。"""


class ComparisonNotFoundError(ComparisonError):
    """Comparison 或必要的源 Artifact 不存在。"""


class ComparisonConflictError(ComparisonError):
    """源 Job 不可比较，或两个证据身份互相冲突。"""


class ComparisonIntegrityError(ComparisonError):
    """内容大小、SHA-256、资源 ID 或内部摘要不一致。"""


class ComparisonLimitExceededError(ComparisonError):
    """读取大小、Artifact 数量或变化数量超过安全上限。"""
