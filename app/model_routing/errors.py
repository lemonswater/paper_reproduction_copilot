from __future__ import annotations


class ModelRoutingError(RuntimeError):
    """模型路由、预算和账本错误的稳定基类。"""


class ModelCatalogError(ModelRoutingError):
    """Policy 文件、Profile 或 Route 配置非法。"""


class ModelRouteUnavailable(ModelRoutingError):
    """没有满足 workload、能力、上下文和质量要求的 Profile。"""


class ModelBudgetExceeded(ModelRoutingError):
    """调用前预算预留被拒绝。"""

    def __init__(
        self,
        *,
        scope: str,
        limit: int,
        used_or_reserved: int,
        requested: int,
    ) -> None:
        self.scope = scope
        self.limit = limit
        self.used_or_reserved = used_or_reserved
        self.requested = requested
        super().__init__(
            "MODEL_BUDGET_EXCEEDED: "
            f"scope={scope}, limit={limit}, "
            f"used_or_reserved={used_or_reserved}, requested={requested}"
        )


class ModelLedgerConflict(ModelRoutingError):
    """同一 Invocation 身份被不同 Request 或 Decision 重用。"""


class ModelLedgerIntegrityError(ModelRoutingError):
    """持久化行、Hash 或状态迁移不一致。"""


class ModelProviderBindingError(ModelRoutingError):
    """Profile 试图使用未知或 workload 不匹配的受信任 Provider Binding。"""


class ModelUsageError(ModelRoutingError):
    """Provider usage 为负数、类型错误或不满足守恒关系。"""
