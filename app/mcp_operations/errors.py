from __future__ import annotations


class McpOperationError(RuntimeError):
    """Phase 56 稳定错误基类；message 不得包含响应正文或凭证。"""

    code = "MCP_OPERATION_ERROR"


class McpRuntimePolicyInvalid(McpOperationError):
    code = "MCP_RUNTIME_POLICY_INVALID"


class McpRuntimeProbeFailed(McpOperationError):
    code = "MCP_RUNTIME_PROBE_FAILED"


class McpRuntimeReportInvalid(McpOperationError):
    code = "MCP_RUNTIME_REPORT_INVALID"


class McpUpgradeRejected(McpOperationError):
    code = "MCP_UPGRADE_REJECTED"
