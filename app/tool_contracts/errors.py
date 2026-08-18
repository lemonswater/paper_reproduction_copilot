from __future__ import annotations


class ToolContractError(RuntimeError):
    """Tool Contract 子系统的基础异常。"""


class ToolRegistryError(ToolContractError):
    """重名、缺失或定义不合法。"""


class ToolBoundaryError(ToolContractError):
    """受控 Adapter 检测到 Workspace/Run 路径越界。"""
