from __future__ import annotations

"""Phase 28 统一脱敏。

Phase 41 起整合 SecretRedactor 的已知值匹配能力。
不要只依赖 key 名。现有 sanitize_error_message() 仍应在异常入口先做路径/凭据清理，
telemetry redaction 是最后一层防线。
"""

from typing import Any
from urllib.parse import urlsplit, urlunsplit
import re

from app.secrets.redaction import SecretRedactor

SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "token",
    "claim_token",
    "assignment_token",
    "password",
    "secret",
    "cookie",
}

_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)"
    r"([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*)"
    r"\s*=\s*"
    r"([^\s,;]+)"
)

# Phase 41: 模块级全局 redactor，由 SecretService 加载已知值。
_global_redactor: SecretRedactor = SecretRedactor.empty()


def set_global_redactor(redactor: SecretRedactor) -> None:
    """供 composition root 或测试注入已知 Secret 值 redactor。"""
    global _global_redactor
    _global_redactor = redactor


def sanitize_error_message(value: object, max_chars: int = 4000) -> str:
    """轻量级错误消息脱敏（不引入 app.tools.error_tools 的 langgraph 等重型依赖）。

    与 ``app.tools.error_tools.sanitize_error_message`` 保持等价语义：
    - 先用 SecretRedactor 匹配已知 Secret 值；
    - 替换 ``KEY=...`` 形式的敏感赋值为 ``<redacted>``；
    - 限制总长度，防止巨量 payload 拖垮 telemetry。
    """

    text = _global_redactor.redact_text(str(value), max_chars=None)
    text = _SENSITIVE_ASSIGNMENT_RE.sub(r"\1=<redacted>", text)
    return text[:max_chars]


def sanitize_url(value: str) -> str:
    """保留 scheme/host/path，丢弃 userinfo、query 和 fragment。"""

    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<invalid-url>"
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit(
        (parsed.scheme, host, parsed.path, "", "")
    )


def redact(
    value: Any, *, max_chars: int = 2000
) -> Any:
    # Phase 41: 先用全局 redactor 做已知值匹配。
    value = _global_redactor.redact_object(
        value, max_chars=max_chars
    )
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if any(
                secret in normalized
                for secret in SENSITIVE_KEYS
            ):
                cleaned[str(key)] = "<redacted>"
            else:
                cleaned[str(key)] = redact(
                    item, max_chars=max_chars
                )
        return cleaned
    if isinstance(value, list):
        return [
            redact(item, max_chars=max_chars)
            for item in value[:100]
        ]
    if isinstance(value, str):
        if value.startswith(
            ("http://", "https://")
        ):
            value = sanitize_url(value)
        return value[:max_chars]
    if value is None or isinstance(
        value, (bool, int, float)
    ):
        return value
    return str(value)[:max_chars]
