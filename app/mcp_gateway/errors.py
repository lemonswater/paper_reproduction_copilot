"""MCP Gateway errors."""
from __future__ import annotations


class McpGatewayError(RuntimeError):
    code = "MCP_GATEWAY_ERROR"
    retryable = False


class McpPolicyError(McpGatewayError):
    code = "MCP_POLICY_INVALID"


class McpEndpointRejected(McpGatewayError):
    code = "MCP_ENDPOINT_REJECTED"


class McpServerUnavailable(McpGatewayError):
    code = "MCP_SERVER_UNAVAILABLE"
    retryable = True


class McpProtocolRejected(McpGatewayError):
    code = "MCP_PROTOCOL_REJECTED"


class McpToolNotAllowed(McpGatewayError):
    code = "MCP_TOOL_NOT_ALLOWED"


class McpSchemaDrift(McpGatewayError):
    code = "MCP_SCHEMA_DRIFT"


class McpRemoteToolFailed(McpGatewayError):
    code = "MCP_REMOTE_TOOL_FAILED"
    retryable = True


class McpStructuredOutputInvalid(McpGatewayError):
    code = "MCP_STRUCTURED_OUTPUT_INVALID"


class McpResultBudgetExceeded(McpGatewayError):
    code = "MCP_RESULT_BUDGET_EXCEEDED"


class McpEvidenceIntegrityError(McpGatewayError):
    code = "MCP_EVIDENCE_INTEGRITY_ERROR"