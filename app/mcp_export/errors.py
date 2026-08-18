from __future__ import annotations


class McpExportError(RuntimeError):
    """可以映射成稳定 MCP 公开错误的领域异常。"""

    code = "MCP_EXPORT_ERROR"
    public_message = "MCP Export request failed"


class McpExportDisabled(McpExportError):
    code = "MCP_EXPORT_DISABLED"
    public_message = "MCP Export is disabled"


class McpExportUnauthorized(McpExportError):
    code = "MCP_EXPORT_UNAUTHORIZED"
    public_message = "Authentication required"


class McpExportInputInvalid(McpExportError):
    code = "MCP_EXPORT_INPUT_INVALID"
    public_message = "Request input is invalid"


class McpExportJobNotFound(McpExportError):
    code = "MCP_EXPORT_JOB_NOT_FOUND"
    public_message = "Reproduction job was not found"


class McpExportFinalReportNotFound(McpExportError):
    code = "MCP_EXPORT_FINAL_REPORT_NOT_FOUND"
    public_message = "Final report is not available"


class McpExportEvidenceUnavailable(McpExportError):
    code = "MCP_EXPORT_EVIDENCE_UNAVAILABLE"
    public_message = "Reproduction evidence is unavailable"


class McpExportRateLimited(McpExportError):
    code = "MCP_EXPORT_RATE_LIMITED"
    public_message = "MCP Export rate limit exceeded"


class McpExportBusy(McpExportError):
    code = "MCP_EXPORT_BUSY"
    public_message = "MCP Export is temporarily busy"


class McpExportTimedOut(McpExportError):
    code = "MCP_EXPORT_TIMEOUT"
    public_message = "MCP Export request timed out"


class McpExportIntegrityError(McpExportError):
    code = "MCP_EXPORT_INTEGRITY_ERROR"
    public_message = "Exported evidence failed integrity validation"


class McpExportInternalError(McpExportError):
    code = "MCP_EXPORT_INTERNAL"
    public_message = "MCP Export internal error"
