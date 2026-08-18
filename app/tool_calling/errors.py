from __future__ import annotations


class ToolCallingError(RuntimeError):
    """Phase 52 的稳定错误基类。"""

    code = "TOOL_CALLING_ERROR"
    retryable = False


class ToolCatalogError(ToolCallingError):
    code = "TOOL_CALLING_CATALOG_INVALID"


class ToolLoopPolicyError(ToolCallingError):
    code = "TOOL_CALLING_POLICY_DENIED"


class ToolLoopLimitExceeded(ToolCallingError):
    code = "TOOL_CALLING_LIMIT_EXCEEDED"


class ToolModelUnavailable(ToolCallingError):
    code = "TOOL_CALLING_MODEL_UNAVAILABLE"
    retryable = True


class ToolEvidenceUnavailable(ToolCallingError):
    code = "TOOL_CALLING_EVIDENCE_UNAVAILABLE"


class ToolTraceIntegrityError(ToolCallingError):
    code = "TOOL_CALLING_TRACE_INTEGRITY"
