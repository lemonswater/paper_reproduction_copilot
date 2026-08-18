from __future__ import annotations

"""Phase 29 Resource 错误类型。

错误分类与 Phase 15 统一错误模型一致：Resource 只是增加 stage/category，
不建立互不相容的第二套错误报告。
"""


class ResourceError(RuntimeError):
    pass


class ResourcePolicyViolation(ResourceError):
    """URL、DNS、redirect、协议或审批违反确定性策略；terminal。"""


class ResourceIntegrityError(ResourceError):
    """hash、commit、magic bytes 或内容结构不匹配；terminal。"""


class ResourceLimitExceeded(ResourceError):
    """字节数、文件数、时间或 redirect 超限；terminal。"""


class ResourceTransportUnavailable(ResourceError):
    """DNS、连接、服务端 5xx 等瞬时失败；可按策略 retry。"""


class ResourceLeaseLost(ResourceError):
    """旧 Worker 失去 ownership，必须停止写入和发布。"""


class ResourceStateAmbiguous(ResourceError):
    """不能证明旧获取进程已停止；必须 reconcile，不能直接重试。"""


class ResourceNotFoundError(ResourceError):
    """resource_id 不存在。"""


class ResourceConflictError(ResourceError):
    """idempotency key 冲突或状态机非法迁移。"""


def is_retryable_resource_error(exc: BaseException) -> bool:
    """只有传输瞬时错误可重试；policy/integrity/limit 默认 terminal。"""

    return isinstance(exc, ResourceTransportUnavailable)
