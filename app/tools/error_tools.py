from __future__ import annotations

import json
import re
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from typing import Any
from uuid import uuid4

from langgraph.errors import GraphInterrupt
from pydantic import ValidationError

from app.schemas import StageError
from app.tools.artifact_tools import (
    artifact_state_update,
    build_run_id,
    create_run_layout,
    write_json_artifact,
    write_text_artifact,
)

NodeCallable = Callable[[dict[str, Any]], dict[str, Any]]

PROVIDER_STAGES = {
    "method_extractor",
    "mapping",
    "experiment_plan",
    "log_debug",
    "repair_planner",
    "file_repair_planner",
}

SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)"
    r"([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*)"
    r"\s*=\s*"
    r"([^\s,;]+)"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_error_message(value: object, max_chars: int = 4000) -> str:
    """
    错误报告不能把 API Key 等值原样写入 Artifact。

    这里只做基础兜底。Phase 16 还会从子进程环境层彻底隔离 secret。
    """

    text = str(value)
    text = SENSITIVE_ASSIGNMENT.sub(r"\1=<redacted>", text)
    return text[:max_chars]


def is_transient_provider_error(exc: BaseException) -> bool:
    """只识别常见传输、限流和服务端瞬时错误。"""

    material = (
        f"{type(exc).__module__}.{type(exc).__name__}: {exc}"
    ).lower()
    markers = (
        "timeout",
        "timed out",
        "connection",
        "ratelimit",
        "rate_limit",
        "429",
        "502",
        "503",
        "504",
        "temporarily unavailable",
    )
    return any(marker in material for marker in markers)


def classify_exception(
    *,
    stage: str,
    exc: BaseException,
) -> tuple[str, str, bool]:
    """
    返回 category、code、retryable。

    分类必须是确定性的，不把最终安全决定交给 LLM。
    """

    if isinstance(exc, FileNotFoundError):
        if stage in {"input_validation", "paper_reader", "repo_scan"}:
            return "user", "INPUT_NOT_FOUND", False
        return "environment", "FILE_NOT_FOUND", False

    if isinstance(exc, PermissionError):
        return "environment", "PERMISSION_DENIED", False

    if isinstance(exc, ValidationError):
        return "agent", "SCHEMA_VALIDATION_FAILED", False

    if isinstance(exc, (UnicodeDecodeError, json.JSONDecodeError)):
        return "user", "INVALID_INPUT_FORMAT", False

    if stage in PROVIDER_STAGES:
        return (
            "provider",
            "PROVIDER_TRANSIENT_ERROR"
            if is_transient_provider_error(exc)
            else "PROVIDER_ERROR",
            is_transient_provider_error(exc),
        )

    if isinstance(exc, OSError):
        return "environment", "OS_ERROR", False

    return "agent", "UNHANDLED_AGENT_EXCEPTION", False


def final_status_for_category(category: str) -> str:
    return {
        "user": "invalid_input",
        "agent": "agent_failed",
        "environment": "environment_blocked",
        "provider": "provider_failed",
        "paper_program": "failed",
    }.get(category, "agent_failed")


def build_stage_error(
    *,
    stage: str,
    code: str,
    category: str,
    message: str,
    retryable: bool = False,
    terminal: bool = True,
    exception_type: str | None = None,
    context: dict[str, Any] | None = None,
) -> StageError:
    """构造不包含完整 traceback 的错误记录。"""

    return StageError(
        error_id=f"error_{uuid4().hex[:16]}",
        code=code,
        category=category,
        stage=stage,
        message=sanitize_error_message(message),
        retryable=retryable,
        terminal=terminal,
        exception_type=exception_type,
        context=context or {},
        occurred_at=utc_now(),
    )


def render_error_report_markdown(
    errors: list[dict[str, Any]],
) -> str:
    lines = ["# Error Report", ""]

    if not errors:
        lines.extend(["当前 run 没有记录 StageError。", ""])
        return "\n".join(lines)

    for index, raw_error in enumerate(errors, 1):
        error = StageError.model_validate(raw_error)
        lines.extend(
            [
                f"## {index}. {error.code}",
                "",
                f"- Error ID：`{error.error_id}`",
                f"- Stage：`{error.stage}`",
                f"- Category：`{error.category}`",
                f"- Terminal：`{error.terminal}`",
                f"- Retryable：`{error.retryable}`",
                f"- Exception：`{error.exception_type or 'not_recorded'}`",
                f"- Time：`{error.occurred_at}`",
                f"- Message：{error.message}",
            ]
        )
        if error.traceback_artifact_path:
            lines.append(
                "- Traceback Artifact："
                f"`{error.traceback_artifact_path}`"
            )
        lines.append("")

    return "\n".join(lines)


def persist_stage_errors(
    *,
    state: dict[str, Any],
    new_errors: list[StageError],
    tracebacks: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    把新错误追加到 state，并重写当前 run 的汇总 Error Report。

    Error Artifact 写入失败时不能递归抛出另一个 guard error。
    """

    tracebacks = tracebacks or {}
    working_errors = [
        StageError.model_validate(item)
        for item in state.get("stage_errors", [])
    ]
    records = []

    for error in new_errors:
        traceback_text = tracebacks.get(error.error_id)
        if traceback_text:
            try:
                trace_path, trace_record = write_text_artifact(
                    state=state,
                    relative_path=(
                        f"traces/errors/{error.error_id}.traceback.txt"
                    ),
                    text=sanitize_error_message(
                        traceback_text,
                        max_chars=20000,
                    ),
                    producer_node=f"error_boundary:{error.stage}",
                )
                records.append(trace_record)
                error = error.model_copy(
                    update={
                        "traceback_artifact_path": str(trace_path),
                    }
                )
            except (OSError, ValueError):
                # run 存储本身不可写时只能保留 checkpoint 中的结构化错误。
                pass

        working_errors.append(error)

    serialized_errors = [item.model_dump() for item in working_errors]
    working_state = {
        **state,
        "stage_errors": serialized_errors,
    }

    try:
        json_path, json_record = write_json_artifact(
            state=working_state,
            relative_path="reports/error_report.json",
            payload={
                "run_id": state.get("run_id"),
                "error_count": len(serialized_errors),
                "errors": serialized_errors,
                "generated_at": utc_now(),
            },
            producer_node="error_report",
        )
        md_path, md_record = write_text_artifact(
            state=working_state,
            relative_path="reports/error_report.md",
            text=render_error_report_markdown(serialized_errors),
            producer_node="error_report",
            media_type="text/markdown",
        )
        records.extend([json_record, md_record])
        report_paths = {
            "error_report_json_path": str(json_path),
            "error_report_md_path": str(md_path),
        }
    except (OSError, ValueError):
        report_paths = {}

    active_error = working_errors[-1]
    update = {
        "stage_errors": serialized_errors,
        "active_stage_error": active_error.model_dump(),
        # 兼容旧 final_report；新的判断必须读取 stage_errors。
        "error": active_error.message,
        **report_paths,
    }

    if active_error.terminal:
        update["final_status"] = final_status_for_category(
            active_error.category
        )

    if records:
        update.update(artifact_state_update(working_state, records))

    return update

def stage_error_result(
    *,
    state: dict[str, Any],
    stage: str,
    code: str,
    category: str,
    message: str,
    terminal: bool = True,
    retryable: bool = False,
    context: dict[str, Any] | None = None,
    extra_update: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    给可预期业务错误使用，不需要先抛 Python Exception。

    extra_update 用于保留节点自己的字段，例如 pending_action=None。
    """

    error = build_stage_error(
        stage=stage,
        code=code,
        category=category,
        message=message,
        terminal=terminal,
        retryable=retryable,
        context=context,
    )
    base_update = extra_update or {}
    working_state = {**state, **base_update}
    persisted = persist_stage_errors(
        state=working_state,
        new_errors=[error],
    )
    result = {
        **base_update,
        # Error Report 写入后产生的 artifact_records 必须保留。
        **persisted,
    }
    if "final_status" in base_update:
        # 更细粒度业务状态只覆盖通用 category 状态。
        result["final_status"] = base_update["final_status"]
    return result


def build_structured_stage_error(
    *,
    stage: str,
    invocation: Any,
    terminal: bool,
    context: dict[str, Any] | None = None,
) -> StageError:
    """
    把 StructuredInvocationResult 的最终失败转换成 StageError。

    validation retry 与 transport retry 是不同概念：
    - validation_error：模型输出没有满足 schema；
    - invoke_error：Provider/API 调用失败；
    - configuration_error：客户端、method 或 strict 配置失败。
    """

    attempts = list(getattr(invocation, "attempts", []))
    last_attempt = attempts[-1] if attempts else None
    status = getattr(last_attempt, "status", "unknown")
    message = getattr(
        last_attempt,
        "error_message",
        "structured output failed",
    )
    exception_type = getattr(last_attempt, "error_type", None)

    if status == "invoke_error":
        category = "provider"
        code = "PROVIDER_INVOKE_FAILED"
        retryable = any(
            marker in str(message).lower()
            for marker in (
                "timeout",
                "connection",
                "429",
                "502",
                "503",
                "504",
            )
        )
    elif status == "configuration_error":
        category = "agent"
        code = "STRUCTURED_OUTPUT_CONFIGURATION_ERROR"
        retryable = False
    else:
        category = "provider"
        code = "STRUCTURED_OUTPUT_VALIDATION_FAILED"
        retryable = False

    attempt_diagnostics = {
        key: value
        for key, value in {
            "finish_reason": getattr(
                last_attempt,
                "finish_reason",
                None,
            ),
            "truncated": getattr(
                last_attempt,
                "truncated",
                None,
            ),
            "output_chars": getattr(
                last_attempt,
                "output_chars",
                None,
            ),
            "token_usage": getattr(
                last_attempt,
                "token_usage",
                None,
            ),
        }.items()
        if value is not None
    }

    return build_stage_error(
        stage=stage,
        code=code,
        category=category,
        message=str(message),
        retryable=retryable,
        terminal=terminal,
        exception_type=exception_type,
        context={
            "attempt_count": len(attempts),
            "method": getattr(invocation, "method", None),
            "strict": getattr(invocation, "strict", None),
            **attempt_diagnostics,
            **(context or {}),
        },
    )


def structured_failure_update(
    *,
    state: dict[str, Any],
    stage: str,
    invocation: Any,
    terminal: bool,
) -> dict[str, Any]:
    """登记一次结构化调用最终失败，并重写当前 run 的 Error Report。"""

    error = build_structured_stage_error(
        stage=stage,
        invocation=invocation,
        terminal=terminal,
    )
    return persist_stage_errors(
        state=state,
        new_errors=[error],
    )


def exception_to_stage_error_update(
    *,
    state: dict[str, Any],
    stage: str,
    exc: BaseException,
) -> dict[str, Any]:
    category, code, retryable = classify_exception(
        stage=stage,
        exc=exc,
    )
    error = build_stage_error(
        stage=stage,
        code=code,
        category=category,
        message=str(exc),
        retryable=retryable,
        terminal=True,
        exception_type=type(exc).__name__,
    )
    traceback_text = "".join(
        traceback.format_exception(
            type(exc),
            exc,
            exc.__traceback__,
        )
    )

    try:
        working_state = ensure_error_run_context(state)
        return {
            **{
                key: value
                for key, value in working_state.items()
                if key in {
                    "run_id",
                    "run_dir",
                    "run_started_at",
                }
            },
            **persist_stage_errors(
                state=working_state,
                new_errors=[error],
                tracebacks={error.error_id: traceback_text},
            ),
        }
    except Exception as persistence_exc:
        # 连错误目录都无法创建时，至少不丢失结构化事实。
        fallback_error = error.model_copy(
            update={
                "context": {
                    **error.context,
                    "error_persistence_failed": sanitize_error_message(
                        persistence_exc
                    ),
                }
            }
        )
        return {
            "stage_errors": [
                *state.get("stage_errors", []),
                fallback_error.model_dump(),
            ],
            "active_stage_error": fallback_error.model_dump(),
            "error": fallback_error.message,
            "final_status": final_status_for_category(category),
        }

def has_terminal_stage_error(state: dict[str, Any]) -> bool:
    for item in state.get("stage_errors", []):
        try:
            if StageError.model_validate(item).terminal:
                return True
        except ValidationError:
            # 无效错误记录本身就是 Agent 状态损坏，路由必须 fail closed。
            return True
    return False


def guard_node(
    node_name: str,
    node: NodeCallable,
) -> NodeCallable:
    """
    为 Graph 节点增加统一异常边界。

    只捕获 Exception，不捕获 KeyboardInterrupt/SystemExit。
    GraphInterrupt 必须原样抛出，否则人工审批无法暂停。
    """

    @wraps(node)
    def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        try:
            result = node(state)

            # 迁移期兜底：旧节点返回 error 字符串时也要生成 StageError。
            # 完成 Phase 15 后，应尽量由节点使用 stage_error_result 显式分类。
            legacy_error = result.get("error")
            if legacy_error and not result.get("active_stage_error"):
                error = build_stage_error(
                    stage=node_name,
                    code="LEGACY_NODE_ERROR",
                    category="agent",
                    message=str(legacy_error),
                    terminal=True,
                    context={
                        "legacy_final_status": result.get("final_status"),
                    },
                )
                working_state = {**state, **result}
                return {
                    **result,
                    **persist_stage_errors(
                        state=working_state,
                        new_errors=[error],
                    ),
                }

            return result
        except GraphInterrupt:
            raise
        except Exception as exc:
            return exception_to_stage_error_update(
                state=state,
                stage=node_name,
                exc=exc,
            )

    return wrapped

def ensure_error_run_context(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    错误边界的应急 run context。

    如果 RUNS_DIR 本身不可写，文件报告客观上无法生成，但 StageError 仍应
    尽量返回给 LangGraph/CLI。
    """

    if state.get("run_id") and state.get("run_dir"):
        return state

    run_id = str(
        state.get("run_id")
        or build_run_id(state.get("task_id"))
    )
    layout = create_run_layout(run_id)
    return {
        **state,
        "run_id": run_id,
        "run_dir": layout["run_root"],
        "run_started_at": (
            state.get("run_started_at")
            or utc_now()
        ),
    }
