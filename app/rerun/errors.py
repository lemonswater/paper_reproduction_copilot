# app/rerun/errors.py

class RerunError(RuntimeError):
    """Phase 39 重跑域错误基类。"""


class RerunNotFoundError(RerunError):
    """Proposal 不存在。"""


class RerunConflictError(RerunError):
    """状态、版本、幂等键或 stale identity 冲突。"""


class RerunIntegrityError(RerunError):
    """已持久化内容、父证据或 hash 校验失败。"""


class RerunCommandRejectedError(RerunError):
    """父命令或参数编辑超出安全子集。"""


class RerunExpiredError(RerunConflictError):
    """Proposal 已经过期，必须基于当前证据重新创建。"""
