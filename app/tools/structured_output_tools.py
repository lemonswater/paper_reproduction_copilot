from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generic, TypeVar

from langchain_core.callbacks import BaseCallbackHandler
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.observability.ports import TelemetryPort
from app.observability.runtime import build_telemetry_runtime as _build_tel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _derive_model_family(model_name: str | None) -> str:
    if not model_name:
        return "other"
    lowered = model_name.lower()
    if "mimo" in lowered:
        return "mimo"
    if "gpt" in lowered:
        return "gpt"
    if "qwen" in lowered:
        return "qwen"
    if "deepseek" in lowered:
        return "deepseek"
    return "other"


def _derive_provider() -> str:
    base_url = (settings.openai_base_url or "").lower()
    if "xiaomimimo.com" in base_url:
        return "mimo"
    if "openai.com" in base_url:
        return "openai"
    if "dashscope" in base_url or "qwen" in base_url:
        return "qwen"
    if "deepseek" in base_url:
        return "deepseek"
    return "openai_compat"


_DEFAULT_TELEMETRY: TelemetryPort | None = None


def _get_default_telemetry() -> TelemetryPort:
    global _DEFAULT_TELEMETRY
    if _DEFAULT_TELEMETRY is None:
        try:
            _DEFAULT_TELEMETRY = _build_tel().telemetry
        except Exception:
            from app.observability.noop import NoOpTelemetry
            _DEFAULT_TELEMETRY = NoOpTelemetry()
    return _DEFAULT_TELEMETRY


def _record_token_usage_safe(
    token_usage: dict[str, Any] | None,
    *,
    telemetry: TelemetryPort | None = None,
) -> None:
    if not token_usage:
        return
    try:
        tel = telemetry if telemetry is not None else _get_default_telemetry()
    except Exception:
        return
    try:
        prompt_tokens = 0
        completion_tokens = 0
        if isinstance(token_usage, dict):
            prompt_tokens = int(
                token_usage.get("prompt_tokens")
                or token_usage.get("input_tokens")
                or 0
            )
            completion_tokens = int(
                token_usage.get("completion_tokens")
                or token_usage.get("output_tokens")
                or 0
            )
        provider = _derive_provider()
        model_family = _derive_model_family(settings.openai_model)
        if prompt_tokens > 0:
            try:
                tel.counter(
                    "paper_copilot_prompt_completion_tokens_total",
                    prompt_tokens,
                    {"provider": provider, "model_family": model_family},
                )
            except Exception:
                pass
        if completion_tokens > 0:
            try:
                tel.counter(
                    "paper_copilot_prompt_completion_tokens_total",
                    completion_tokens,
                    {"provider": provider, "model_family": model_family},
                )
            except Exception:
                pass
    except Exception:
        pass


@dataclass
class StructuredOutputAttempt:
    """记录一次模型结构化输出尝试，不保存完整敏感上下文。"""

    attempt_number: int
    status: str
    prompt_kind: str
    error_type: str | None = None
    error_message: str | None = None
    raw_preview: str | None = None
    finish_reason: str | None = None
    token_usage: dict[str, Any] | None = None
    output_chars: int | None = None
    truncated: bool = False


@dataclass
class StructuredInvocationResult(Generic[SchemaT]):
    """通用调用结果；value=None 表示所有 attempt 都失败。"""

    value: SchemaT | None
    attempts: list[StructuredOutputAttempt]
    method: str
    strict: bool | None
    max_retries: int
    provider_max_retries: int = 2
    provider_retry_base_seconds: float = 0.5

    @property
    def succeeded(self) -> bool:
        return self.value is not None


def _plain_mapping(value: Any) -> dict[str, Any] | None:
    """把 Provider usage 等对象转换成可写入 JSON 的普通字典。"""
    if value is None:
        return None
    if isinstance(value, BaseModel):
        value = value.model_dump()
    elif not isinstance(value, dict):
        try:
            value = dict(value)
        except (TypeError, ValueError):
            return None

    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


class _ResponseMetadataCapture(BaseCallbackHandler):
    """
    在 output parser 运行前捕获模型响应元数据。

    部分 LangChain parser 会直接抛出 ValidationError，导致 include_raw
    来不及返回 raw。LLM callback 仍会先收到原始 generation，因此可用
    于保留 finish_reason 和 token usage。
    """

    def __init__(self) -> None:
        self.finish_reason: str | None = None
        self.token_usage: dict[str, Any] | None = None

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        llm_output = getattr(response, "llm_output", None) or {}
        if isinstance(llm_output, dict):
            self.token_usage = _plain_mapping(
                llm_output.get("token_usage") or llm_output.get("usage")
            )

        for generation_group in getattr(response, "generations", []) or []:
            for generation in generation_group or []:
                generation_info = getattr(generation, "generation_info", None) or {}
                message = getattr(generation, "message", None)
                response_metadata = getattr(message, "response_metadata", None) or {}

                if self.finish_reason is None:
                    self.finish_reason = response_metadata.get(
                        "finish_reason"
                    ) or generation_info.get("finish_reason")

                if self.token_usage is None:
                    self.token_usage = _plain_mapping(
                        getattr(message, "usage_metadata", None)
                        or response_metadata.get("token_usage")
                        or response_metadata.get("usage")
                    )


def _raw_to_text(raw: Any) -> str | None:
    if raw is None:
        return None

    content = getattr(raw, "content", raw)
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, default=str)
    except TypeError:
        return str(content)


def _response_diagnostics(
    raw: Any,
    capture: _ResponseMetadataCapture,
) -> tuple[str | None, dict[str, Any] | None]:
    """优先读取 raw message，并用 callback 捕获结果补齐缺失字段。"""
    response_metadata = getattr(raw, "response_metadata", None) or {}
    finish_reason = response_metadata.get("finish_reason") or capture.finish_reason
    token_usage = (
        _plain_mapping(
            getattr(raw, "usage_metadata", None)
            or response_metadata.get("token_usage")
            or response_metadata.get("usage")
        )
        or capture.token_usage
    )
    return finish_reason, token_usage


def _validation_error_input(exc: ValidationError) -> str | None:
    """从 Pydantic JSON 错误中恢复导致校验失败的模型原始字符串。"""
    candidates: list[str] = []
    for error in exc.errors(include_input=True):
        input_value = error.get("input")
        if isinstance(input_value, str):
            candidates.append(input_value)
    return max(candidates, key=len) if candidates else None


def _looks_like_truncation(
    *,
    error_message: str,
    raw_text: str | None,
    finish_reason: str | None,
) -> bool:
    normalized_reason = str(finish_reason or "").strip().lower()
    if normalized_reason in {
        "length",
        "max_tokens",
        "max_output_tokens",
    }:
        return True

    material = f"{error_message}\n{raw_text or ''}".lower()
    return any(
        marker in material
        for marker in (
            "eof while parsing",
            "unexpected end of json",
            "end of json input",
            "unterminated string",
        )
    )


def _is_transient_provider_exception(exc: Exception) -> bool:
    """只把明确的瞬时传输或限流故障标记为可重试。"""

    material = (f"{type(exc).__module__}.{type(exc).__name__}: {exc}").lower()
    return any(
        marker in material
        for marker in (
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
    )


def _invoke_with_transport_retry(
    *,
    invoke: Callable[[], Any],
    prompt_kind: str,
    attempt_number_start: int,
    max_retries: int,
    base_seconds: float,
) -> tuple[
    Any | None,
    list[StructuredOutputAttempt],
    Exception | None,
]:
    """
    只负责 Provider transport retry，不消费 schema validation retry。

    ValidationError 必须交还外层格式修正循环；认证失败、模型不存在和
    普通 4xx 也会在第一次失败后立即返回。
    """

    provider_attempts: list[StructuredOutputAttempt] = []

    for retry_index in range(max_retries + 1):
        try:
            return invoke(), provider_attempts, None
        except ValidationError:
            raise
        except Exception as exc:
            retryable = _is_transient_provider_exception(exc)
            will_retry = retryable and retry_index < max_retries
            provider_attempts.append(
                StructuredOutputAttempt(
                    attempt_number=(attempt_number_start + len(provider_attempts)),
                    status=("provider_retry" if will_retry else "invoke_error"),
                    prompt_kind=prompt_kind,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )

            if not will_retry:
                return None, provider_attempts, exc

            time.sleep(base_seconds * (2**retry_index))

    raise AssertionError("transport retry loop reached invalid state")


def _raw_to_preview(raw: Any, max_chars: int) -> str | None:
    """
    从 LangChain AIMessage 或普通对象提取可审计预览。

    只保存模型输出预览，不保存完整 prompt，避免论文正文、路径或其他
    上下文无限复制到日志中。
    """
    text = _raw_to_text(raw)
    return text[:max_chars] if text is not None else None


def _build_validation_retry_prompt(
    *,
    original_prompt: str,
    schema: type[BaseModel],
    validation_error: str,
    previous_raw_preview: str | None,
    schema_already_in_prompt: bool = False,
) -> str:
    """
    把上一轮具体错误反馈给模型。

    这里强调“只修结构”，避免每次 retry 都重新生成完全不同的方案。
    """
    schema_section = (
        ""
        if schema_already_in_prompt
        else (
            "\n\n要求的 JSON Schema：\n"
            + json.dumps(
                schema.model_json_schema(),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    )

    return f"""
{original_prompt}

上一轮结构化输出没有通过本地校验。

校验错误：
{validation_error}

上一轮输出预览：
{previous_raw_preview or "<不可用>"}
{schema_section}

请只修复字段名、字段类型、枚举值和缺失字段。
不要增加新的事实，不要改变原有证据，不要输出解释、Markdown 或代码围栏。
只返回符合 schema 的 JSON 对象。
""".strip()


def _build_json_mode_prompt(
    *,
    original_prompt: str,
    schema: type[BaseModel],
) -> str:
    """
    json_object 只保证 JSON 语法，必须在 prompt 中显式提供字段契约。

    使用紧凑 schema，既适配 MiMo json_mode，也避免手工维护第二份字段定义。
    """
    schema_json = json.dumps(
        schema.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""
{original_prompt}

当前 Provider 使用 JSON Object 模式，不会在服务端强制字段结构。
你必须严格遵守下面的 JSON Schema，最终只返回一个完整 JSON 对象。

要求的 JSON Schema：
{schema_json}
""".strip()


def _build_truncation_retry_prompt(
    *,
    original_prompt: str,
    validation_error: str,
) -> str:
    """
    截断时不再重复附加完整 schema，避免 retry prompt 继续膨胀。

    原始 prompt 已经包含任务约束和 schema；这里只要求模型压缩内容并
    确保 JSON 闭合。
    """
    return f"""
{original_prompt}

上一轮输出在 JSON 对象完成前被截断。

校验错误：
{validation_error}

请重新生成完整结果，并遵守以下额外限制：
1. 使用紧凑单行 JSON，不要缩进、换行、解释或 Markdown。
2. 所有必需顶层字段都必须存在，所有字符串必须闭合。
3. 每个列表只保留完成任务所需的最少项目；没有可靠内容时返回 []。
4. 字符串使用简短摘要，不要重复论文、README 或 schema 原文。
5. 必须在输出预算内返回完整、可被 json.loads() 解析的 JSON 对象。
""".strip()


def invoke_structured_with_retry(
    *,
    llm: Any,
    schema: type[SchemaT],
    prompt: str,
    method: str = "json_schema",
    strict: bool = True,
    max_retries: int = 2,
    raw_preview_chars: int = 2000,
    provider_max_retries: int = 2,
    provider_retry_base_seconds: float = 0.5,
    telemetry: TelemetryPort | None = None,
) -> StructuredInvocationResult[SchemaT]:
    """
    使用 Provider 结构化输出能力 + Pydantic 完成有限重试。

    max_retries 表示第一次失败之后额外尝试的次数：
    - 0：总共调用 1 次；
    - 1：总共最多调用 2 次；
    - 2：总共最多调用 3 次。

    这里只重试结构/语义校验失败。
    API 连接失败或 Provider 不支持当前 method 时直接返回失败，避免对
    同一个能力错误无意义地连续请求。json_mode 不向 Provider 传 strict，
    但返回内容仍会经过 Pydantic 本地校验。
    """
    if method not in {"json_schema", "function_calling", "json_mode"}:
        raise ValueError(f"不支持的结构化输出方法：{method}")
    if max_retries < 0:
        raise ValueError("max_retries 必须大于或等于 0")
    if provider_max_retries < 0:
        raise ValueError("provider_max_retries 必须大于或等于 0")
    if provider_retry_base_seconds < 0:
        raise ValueError("provider_retry_base_seconds 必须大于或等于 0")

    try:
        tel: TelemetryPort = (
            telemetry if telemetry is not None else _get_default_telemetry()
        )
    except Exception:
        from app.observability.noop import NoOpTelemetry
        tel = NoOpTelemetry()

    attempts: list[StructuredOutputAttempt] = []
    effective_strict = None if method == "json_mode" else strict

    try:
        if method == "json_mode":
            structured_llm = llm.with_structured_output(
                schema,
                method=method,
                include_raw=True,
            )
        else:
            structured_llm = llm.with_structured_output(
                schema,
                method=method,
                strict=strict,
                include_raw=True,
            )
    except Exception as exc:
        # 某些客户端会在创建 structured runnable 时就检查 schema、method
        # 或 strict 参数。此时请求尚未发送，因此与 invoke_error 分开记录。
        attempts.append(
            StructuredOutputAttempt(
                attempt_number=0,
                status="configuration_error",
                prompt_kind="configuration",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        )
        return StructuredInvocationResult(
            value=None,
            attempts=attempts,
            method=method,
            strict=effective_strict,
            max_retries=max_retries,
            provider_max_retries=provider_max_retries,
            provider_retry_base_seconds=(provider_retry_base_seconds),
        )

    base_prompt = (
        _build_json_mode_prompt(
            original_prompt=prompt,
            schema=schema,
        )
        if method == "json_mode"
        else prompt
    )
    current_prompt = base_prompt

    for attempt_index in range(max_retries + 1):
        prompt_kind = "original" if attempt_index == 0 else "validation_retry"
        metadata_capture = _ResponseMetadataCapture()

        try:
            response, transport_attempts, invoke_error = _invoke_with_transport_retry(
                invoke=lambda prompt=current_prompt, capture=metadata_capture: (
                    structured_llm.invoke(
                        prompt,
                        config={"callbacks": [capture]},
                    )
                ),
                prompt_kind=prompt_kind,
                attempt_number_start=len(attempts) + 1,
                max_retries=provider_max_retries,
                base_seconds=provider_retry_base_seconds,
            )
            attempts.extend(transport_attempts)
        except ValidationError as exc:
            # Provider 已返回但 schema 校验失败，进入格式修正循环；不消耗
            # transport retry 预算。
            error_message = str(exc)
            raw_text = _validation_error_input(exc)
            finish_reason, token_usage = _response_diagnostics(
                None,
                metadata_capture,
            )
            truncated = _looks_like_truncation(
                error_message=error_message,
                raw_text=raw_text,
                finish_reason=finish_reason,
            )
            attempts.append(
                StructuredOutputAttempt(
                    attempt_number=len(attempts) + 1,
                    status="validation_error",
                    prompt_kind=prompt_kind,
                    error_type=type(exc).__name__,
                    error_message=error_message,
                    raw_preview=(
                        raw_text[:raw_preview_chars]
                        if raw_text is not None
                        else None
                    ),
                    finish_reason=finish_reason,
                    token_usage=token_usage,
                    output_chars=(len(raw_text) if raw_text is not None else None),
                    truncated=truncated,
                )
            )
            _record_token_usage_safe(token_usage, telemetry=tel)

            if attempt_index >= max_retries:
                break

            current_prompt = (
                _build_truncation_retry_prompt(
                    original_prompt=base_prompt,
                    validation_error=error_message,
                )
                if truncated
                else _build_validation_retry_prompt(
                    original_prompt=base_prompt,
                    schema=schema,
                    validation_error=error_message,
                    previous_raw_preview=(
                        raw_text[:raw_preview_chars] if raw_text is not None else None
                    ),
                    schema_already_in_prompt=(method == "json_mode"),
                )
            )
            continue

        if invoke_error is not None:
            break

        attempt_number = len(attempts) + 1

        if isinstance(response, schema):
            parsed = response
            raw = None
            parsing_error = None
        elif isinstance(response, dict):
            parsed = response.get("parsed")
            raw = response.get("raw")
            parsing_error = response.get("parsing_error")
        else:
            parsed = response
            raw = None
            parsing_error = None

        raw_text = _raw_to_text(raw)
        raw_preview = _raw_to_preview(raw, raw_preview_chars)
        finish_reason, token_usage = _response_diagnostics(
            raw,
            metadata_capture,
        )

        try:
            if parsed is None:
                raise ValueError(str(parsing_error or "结构化输出的解析结果为 None"))

            value = schema.model_validate(parsed)
        except (TypeError, ValueError, ValidationError) as exc:
            error_message = str(exc)
            truncated = _looks_like_truncation(
                error_message=error_message,
                raw_text=raw_text,
                finish_reason=finish_reason,
            )
            attempts.append(
                StructuredOutputAttempt(
                    attempt_number=attempt_number,
                    status="validation_error",
                    prompt_kind=prompt_kind,
                    error_type=type(exc).__name__,
                    error_message=error_message,
                    raw_preview=raw_preview,
                    finish_reason=finish_reason,
                    token_usage=token_usage,
                    output_chars=(len(raw_text) if raw_text is not None else None),
                    truncated=truncated,
                )
            )
            _record_token_usage_safe(token_usage, telemetry=tel)

            if attempt_index >= max_retries:
                break

            current_prompt = (
                _build_truncation_retry_prompt(
                    original_prompt=base_prompt,
                    validation_error=error_message,
                )
                if truncated
                else _build_validation_retry_prompt(
                    original_prompt=base_prompt,
                    schema=schema,
                    validation_error=error_message,
                    previous_raw_preview=raw_preview,
                    schema_already_in_prompt=(method == "json_mode"),
                )
            )
            continue

        attempts.append(
            StructuredOutputAttempt(
                attempt_number=attempt_number,
                status="succeeded",
                prompt_kind=prompt_kind,
                raw_preview=raw_preview,
                finish_reason=finish_reason,
                token_usage=token_usage,
                output_chars=(len(raw_text) if raw_text is not None else None),
            )
        )
        _record_token_usage_safe(token_usage, telemetry=tel)
        return StructuredInvocationResult(
            value=value,
            attempts=attempts,
            method=method,
            strict=effective_strict,
            max_retries=max_retries,
            provider_max_retries=provider_max_retries,
            provider_retry_base_seconds=(provider_retry_base_seconds),
        )

    return StructuredInvocationResult(
        value=None,
        attempts=attempts,
        method=method,
        strict=effective_strict,
        max_retries=max_retries,
        provider_max_retries=provider_max_retries,
        provider_retry_base_seconds=provider_retry_base_seconds,
    )


def write_structured_output_trace(
    *,
    result: StructuredInvocationResult[Any],
    node_name: str,
    schema_name: str,
    output_dir: Path,
    fallback_used: bool,
) -> Path:
    """把结构化调用过程写成独立 artifact，方便调试和评测。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{node_name}_structured_attempts.json"

    payload = {
        "node_name": node_name,
        "schema_name": schema_name,
        "method": result.method,
        "strict": result.strict,
        "max_retries": result.max_retries,
        "provider_max_retries": result.provider_max_retries,
        "provider_retry_base_seconds": (result.provider_retry_base_seconds),
        "succeeded": result.succeeded,
        "fallback_used": fallback_used,
        "attempt_count": len(result.attempts),
        "attempts": [asdict(item) for item in result.attempts],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
