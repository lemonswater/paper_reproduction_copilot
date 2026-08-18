from __future__ import annotations

import base64
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from pydantic import BaseModel

from app.secrets.errors import SecretLeakDetectedError
from app.secrets.ports import SecretMaterial


REDACTED = "<redacted>"
REDACTED_BYTES = REDACTED.encode("utf-8")

SENSITIVE_KEY_PARTS = {
    "authorization",
    "api_key",
    "apikey",
    "token",
    "password",
    "passwd",
    "secret",
    "credential",
    "cookie",
}

_ASSIGNMENT_RE = re.compile(
    r"(?i)"
    r"([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)"
    r"[A-Z0-9_]*)"
    r"\s*=\s*([^\s,;]+)"
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
_URL_USERINFO_RE = re.compile(
    r"(?i)\b(https?://)[^/\s:@]+:[^/\s@]+@"
)


def _sanitize_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<invalid-url>"
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


class SecretRedactor:
    """同时使用已知值匹配和通用 secret-like 规则。"""

    def __init__(
        self,
        materials: Sequence[SecretMaterial] = (),
        *,
        known_values: Mapping[str, str] | None = None,
    ):
        patterns: dict[str, str] = {}
        byte_patterns: dict[bytes, str] = {}

        values = [
            (material.reference.name, material.reveal())
            for material in materials
        ]
        values.extend((known_values or {}).items())

        for name, value in values:
            variants = {value, quote(value, safe="")}
            if len(value) >= 12:
                encoded = base64.urlsafe_b64encode(
                    value.encode("utf-8")
                ).decode("ascii")
                variants.add(encoded)
                variants.add(encoded.rstrip("="))
            for variant in variants:
                if len(variant) < 8:
                    continue
                patterns[variant] = name
                byte_patterns[variant.encode("utf-8")] = name
        self._patterns = tuple(
            sorted(patterns, key=len, reverse=True)
        )
        self._pattern_names = patterns
        self._byte_patterns = tuple(
            sorted(byte_patterns, key=len, reverse=True)
        )
        self._byte_pattern_names = byte_patterns

    @classmethod
    def empty(cls) -> "SecretRedactor":
        return cls()

    @classmethod
    def from_values(
        cls,
        values: Sequence[str],
    ) -> "SecretRedactor":
        """只供测试或受信任的短生命周期边界使用。"""

        return cls(
            known_values={
                f"INLINE_SECRET_{index}": value
                for index, value in enumerate(values)
            }
        )

    @property
    def byte_patterns(self) -> tuple[bytes, ...]:
        return self._byte_patterns

    def redact_text(
        self,
        value: object,
        *,
        max_chars: int | None = None,
    ) -> str:
        text = str(value)
        for pattern in self._patterns:
            text = text.replace(pattern, REDACTED)
        text = _ASSIGNMENT_RE.sub(r"\1=<redacted>", text)
        text = _BEARER_RE.sub("Bearer <redacted>", text)
        text = _URL_USERINFO_RE.sub(r"\1<redacted>@", text)
        if text.startswith(("http://", "https://")):
            text = _sanitize_url(text)
        if max_chars is not None:
            text = text[:max_chars]
        return text

    def redact_object(
        self,
        value: Any,
        *,
        max_chars: int = 2000,
    ) -> Any:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        if isinstance(value, Mapping):
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                name = str(key)
                normalized = name.lower()
                if any(
                    part in normalized
                    for part in SENSITIVE_KEY_PARTS
                ):
                    cleaned[name] = REDACTED
                else:
                    cleaned[name] = self.redact_object(
                        item,
                        max_chars=max_chars,
                    )
            return cleaned
        if isinstance(value, (list, tuple)):
            return [
                self.redact_object(item, max_chars=max_chars)
                for item in value[:100]
            ]
        if isinstance(value, str):
            return self.redact_text(
                value,
                max_chars=max_chars,
            )
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return self.redact_text(value, max_chars=max_chars)

    def find_known_in_text(self, value: str) -> list[str]:
        return sorted(
            {
                self._pattern_names[pattern]
                for pattern in self._patterns
                if pattern in value
            }
        )

    def find_known_in_bytes(self, value: bytes) -> list[str]:
        return sorted(
            {
                self._byte_pattern_names[pattern]
                for pattern in self._byte_patterns
                if pattern in value
            }
        )

    def contains_secret(self, value: str) -> bool:
        return bool(self.find_known_in_text(value))

    def contains_secret_bytes(self, value: bytes) -> bool:
        return bool(self.find_known_in_bytes(value))

    def assert_no_known_secret(
        self,
        value: bytes,
        *,
        boundary: str,
    ) -> None:
        names = self.find_known_in_bytes(value)
        if names:
            raise SecretLeakDetectedError(
                f"{boundary} 检测到 Secret：{', '.join(names)}"
            )

    def stream(self) -> "StreamingSecretRedactor":
        return StreamingSecretRedactor(self._byte_patterns)


class StreamingSecretRedactor:
    """跨 chunk 精确匹配已知 Secret byte pattern。"""

    def __init__(self, patterns: Sequence[bytes]):
        self._patterns = tuple(
            sorted(set(patterns), key=len, reverse=True)
        )
        self._buffer = bytearray()
        self._closed = False

    def _drain(self, *, final: bool) -> bytes:
        output = bytearray()
        while self._buffer:
            current = bytes(self._buffer)
            matched = next(
                (
                    pattern
                    for pattern in self._patterns
                    if current.startswith(pattern)
                ),
                None,
            )
            if matched is not None:
                output.extend(REDACTED_BYTES)
                del self._buffer[: len(matched)]
                continue

            could_be_prefix = any(
                pattern.startswith(current)
                for pattern in self._patterns
            )
            if could_be_prefix and not final:
                break

            output.append(self._buffer[0])
            del self._buffer[0]
        return bytes(output)

    def feed(self, data: bytes) -> bytes:
        if self._closed:
            raise RuntimeError("StreamingSecretRedactor 已关闭")
        self._buffer.extend(data)
        return self._drain(final=False)

    def flush(self) -> bytes:
        if self._closed:
            return b""
        self._closed = True
        return self._drain(final=True)
