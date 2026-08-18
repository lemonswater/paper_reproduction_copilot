from __future__ import annotations


class McpContractError(RuntimeError):
    """Phase 55 稳定错误基类；message 不能包含 Token 或协议正文。"""

    code = "MCP_CONTRACT_ERROR"


class McpContractDependencyMissing(McpContractError):
    code = "MCP_CONTRACT_DEPENDENCY_MISSING"


class McpClientProfileInvalid(McpContractError):
    code = "MCP_CLIENT_PROFILE_INVALID"


class McpSurfaceObservationFailed(McpContractError):
    code = "MCP_SURFACE_OBSERVATION_FAILED"


class McpContractBaselineMissing(McpContractError):
    code = "MCP_CONTRACT_BASELINE_MISSING"


class McpContractBaselineInvalid(McpContractError):
    code = "MCP_CONTRACT_BASELINE_INVALID"


class McpContractDrift(McpContractError):
    code = "MCP_CONTRACT_DRIFT"


class McpContractPromotionRejected(McpContractError):
    code = "MCP_CONTRACT_PROMOTION_REJECTED"


class McpLiveProbeFailed(McpContractError):
    code = "MCP_LIVE_PROBE_FAILED"
