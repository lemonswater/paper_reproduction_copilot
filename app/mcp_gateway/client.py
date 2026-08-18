from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx2
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.mcp_gateway.errors import (
    McpGatewayError,
    McpPolicyError,
    McpProtocolRejected,
    McpRemoteToolFailed,
    McpResultBudgetExceeded,
    McpSchemaDrift,
    McpServerUnavailable,
    McpStructuredOutputInvalid,
    McpToolNotAllowed,
)
from app.mcp_gateway.identity import schema_sha256, sha256_value
from app.mcp_gateway.policy import validate_loopback_endpoint
from app.mcp_gateway.ports import McpClientPort
from app.mcp_gateway.schemas import (
    McpObservedTool,
    McpRawCallResult,
    McpServerProfile,
    McpToolBinding,
)


def run_async_from_sync(coroutine, *, timeout_seconds: float):
    """sync MCP client cannot run inside an active event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        coroutine.close()
        raise McpPolicyError("sync MCP client cannot run inside an active event loop")
    return asyncio.run(asyncio.wait_for(coroutine, timeout=timeout_seconds))


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _walk_schema(value: Any, *, max_bytes: int, depth: int = 0) -> None:
    if depth == 0 and _json_size(value) > max_bytes:
        raise McpSchemaDrift("MCP schema exceeds local budget")
    if depth > 16:
        raise McpSchemaDrift("MCP schema nesting is too deep")
    if isinstance(value, dict):
        if len(value) > 128:
            raise McpSchemaDrift("MCP schema object is too large")
        for key, child in value.items():
            if key == "" and (not isinstance(child, str) or not child.startswith("#//")):
                raise McpSchemaDrift("external MCP schema reference denied")
            _walk_schema(child, max_bytes=max_bytes, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > 128:
            raise McpSchemaDrift("MCP schema list is too large")
        for child in value:
            _walk_schema(child, max_bytes=max_bytes, depth=depth + 1)


def _validate_json_schema(schema: dict[str, Any], *, max_bytes: int) -> None:
    _walk_schema(schema, max_bytes=max_bytes)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise McpSchemaDrift("MCP schema is not valid JSON Schema") from exc


def _validate_instance(*, value: Any, schema: dict[str, Any], error: type[McpGatewayError]) -> None:
    try:
        Draft202012Validator(schema).validate(value)
    except ValidationError as exc:
        raise error("MCP value does not match pinned schema") from exc


class SdkMcpClient(McpClientPort):
    """Official SDK 2.x restricted Streamable HTTP Adapter."""

    def __init__(self, *, total_timeout_seconds: float, max_tools: int, max_schema_bytes: int, max_result_bytes: int) -> None:
        self.total_timeout_seconds = total_timeout_seconds
        self.max_tools = max_tools
        self.max_schema_bytes = max_schema_bytes
        self.max_result_bytes = max_result_bytes

    async def _list_tools(self, client: Client) -> list[Any]:
        tools: list[Any] = []
        cursor: str | None = None
        pages = 0
        while True:
            pages += 1
            if pages > 8:
                raise McpToolNotAllowed("MCP tools/list pagination exceeded")
            page = await client.list_tools(cursor=cursor)
            tools.extend(page.tools)
            if len(tools) > self.max_tools:
                raise McpToolNotAllowed("MCP tool catalog exceeds local limit")
            cursor = page.next_cursor
            if cursor is None:
                return tools

    def _observe_tool(self, *, profile: McpServerProfile, binding: McpToolBinding, protocol_version: str, tools: list[Any]) -> McpObservedTool:
        matches = [tool for tool in tools if tool.name == binding.remote_tool_name]
        if len(matches) != 1:
            raise McpToolNotAllowed("pinned MCP tool is missing or ambiguous")
        tool = matches[0]
        input_schema = tool.input_schema
        output_schema = tool.output_schema
        if not isinstance(input_schema, dict):
            raise McpSchemaDrift("MCP input schema must be an object")
        if not isinstance(output_schema, dict):
            raise McpSchemaDrift("MCP output schema is required")
        _validate_json_schema(input_schema, max_bytes=self.max_schema_bytes)
        _validate_json_schema(output_schema, max_bytes=self.max_schema_bytes)
        observed = McpObservedTool(
            server_id=profile.server_id,
            protocol_version=protocol_version,
            remote_tool_name=tool.name,
            input_schema=input_schema,
            output_schema=output_schema,
            input_schema_sha256=schema_sha256(input_schema),
            output_schema_sha256=schema_sha256(output_schema),
        )
        return observed

    def _verify_pin(self, *, binding: McpToolBinding, observed: McpObservedTool) -> None:
        if observed.input_schema_sha256 != binding.expected_input_schema_sha256:
            raise McpSchemaDrift("MCP input schema hash changed")
        if observed.output_schema_sha256 != binding.expected_output_schema_sha256:
            raise McpSchemaDrift("MCP output schema hash changed")

    async def _open_and_observe(self, *, profile: McpServerProfile, binding: McpToolBinding, arguments: dict[str, Any] | None) -> McpObservedTool | McpRawCallResult:
        validate_loopback_endpoint(profile.endpoint)
        timeout = httpx2.Timeout(profile.connect_timeout_seconds, read=profile.read_timeout_seconds)
        async with httpx2.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as http_client:
            transport = streamable_http_client(profile.endpoint, http_client=http_client)
            async with Client(transport) as client:
                protocol_version = str(client.protocol_version)
                if protocol_version not in profile.allowed_protocol_versions:
                    raise McpProtocolRejected("MCP protocol version is not pinned")
                tools = await self._list_tools(client)
                observed = self._observe_tool(profile=profile, binding=binding, protocol_version=protocol_version, tools=tools)
                if arguments is None:
                    return observed
                self._verify_pin(binding=binding, observed=observed)
                _validate_instance(value=arguments, schema=observed.input_schema, error=McpStructuredOutputInvalid)
                result = await client.call_tool(binding.remote_tool_name, arguments)
                if result.is_error:
                    raise McpRemoteToolFailed("remote MCP tool failed")
                structured = result.structured_content
                if not isinstance(structured, dict):
                    raise McpStructuredOutputInvalid("MCP structured_content must be an object")
                if _json_size(structured) > self.max_result_bytes:
                    raise McpResultBudgetExceeded("MCP structured_content exceeds local budget")
                _validate_instance(value=structured, schema=observed.output_schema, error=McpStructuredOutputInvalid)
                return McpRawCallResult(observed_tool=observed, structured_content=structured, result_sha256=sha256_value(structured))

    def inspect_tool(self, *, profile: McpServerProfile, binding: McpToolBinding) -> McpObservedTool:
        try:
            result = run_async_from_sync(self._open_and_observe(profile=profile, binding=binding, arguments=None), timeout_seconds=self.total_timeout_seconds)
        except McpGatewayError:
            raise
        except (TimeoutError, OSError, RuntimeError) as exc:
            raise McpServerUnavailable("MCP inspect unavailable") from exc
        if not isinstance(result, McpObservedTool):
            raise McpStructuredOutputInvalid("unexpected MCP inspect result")
        return result

    def call_pinned_tool(self, *, profile: McpServerProfile, binding: McpToolBinding, arguments: dict[str, Any]) -> McpRawCallResult:
        try:
            result = run_async_from_sync(self._open_and_observe(profile=profile, binding=binding, arguments=arguments), timeout_seconds=self.total_timeout_seconds)
        except McpGatewayError:
            raise
        except (TimeoutError, OSError, RuntimeError) as exc:
            raise McpServerUnavailable("MCP call unavailable") from exc
        if not isinstance(result, McpRawCallResult):
            raise McpStructuredOutputInvalid("unexpected MCP call result")
        return result
