class FailureMemoryError(RuntimeError):
    """Failure Memory 领域错误基类。"""


class FailureCaseNotFoundError(FailureMemoryError):
    pass


class FailureCaseConflictError(FailureMemoryError):
    """状态、版本、Hash、幂等请求或证据前置条件冲突。"""


class FailureCaseIntegrityError(FailureMemoryError):
    """受信任 Artifact、Case Hash 或派生身份不可验证。"""


class FailureCaseLimitExceededError(FailureMemoryError):
    """输入 Artifact、候选数量或文本大小超过安全上限。"""
