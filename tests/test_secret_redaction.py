from __future__ import annotations

import base64
import pickle
from urllib.parse import quote

import pytest

from app.secrets.errors import SecretLeakDetectedError
from app.secrets.ports import SecretMaterial
from app.secrets.redaction import (
    REDACTED,
    REDACTED_BYTES,
    SecretRedactor,
    StreamingSecretRedactor,
)
from app.secrets.schemas import (
    SecretReference,
    SecretUse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SECRET_VALUE = "sk-test-secret-1234567890"
SECRET_NAME = "OPENAI_API_KEY"
FINGERPRINT = "hmac-sha256:" + "a" * 64


def _material(value: str = SECRET_VALUE) -> SecretMaterial:
    return SecretMaterial(
        reference=SecretReference(
            name=SECRET_NAME,
            version=1,
            fingerprint=FINGERPRINT,
        ),
        allowed_uses=(SecretUse.PROVIDER,),
        _value=value,
    )


# ---------------------------------------------------------------------------
# redact_text — known-value matching
# ---------------------------------------------------------------------------


class TestRedactText:
    def test_known_value_replaced(self):
        redactor = SecretRedactor(known_values={SECRET_NAME: SECRET_VALUE})
        text = f"Authorization: {SECRET_VALUE}"
        result = redactor.redact_text(text)
        assert REDACTED in result
        assert SECRET_VALUE not in result

    def test_no_known_value_passthrough(self):
        redactor = SecretRedactor.empty()
        text = "hello world"
        assert redactor.redact_text(text) == "hello world"

    def test_multiple_known_values(self):
        redactor = SecretRedactor(
            known_values={
                "KEY_A": "alpha-secret-1234",
                "KEY_B": "beta-secret-12345",
            }
        )
        text = "alpha-secret-1234 and beta-secret-12345"
        result = redactor.redact_text(text)
        assert "alpha-secret-1234" not in result
        assert "beta-secret-12345" not in result
        assert result.count(REDACTED) == 2

    def test_value_shorter_than_eight_ignored(self):
        """短于 8 字符的 pattern 不注册，避免误匹配。"""
        redactor = SecretRedactor(
            known_values={"SHORT": "abc"}
        )
        text = "abc"
        # abc 不注册为 pattern，但 _ASSIGNMENT_RE 也不会匹配
        result = redactor.redact_text(text)
        assert result == "abc"

    def test_max_chars_truncation(self):
        redactor = SecretRedactor(
            known_values={"K": "long-secret-value-123456"}
        )
        text = "long-secret-value-123456 rest"
        result = redactor.redact_text(text, max_chars=10)
        assert len(result) <= 10

    def test_url_encoded_variant(self):
        """特殊字符被 URL 编码后仍可匹配。"""
        value = "sk+test/secret=12345678"
        redactor = SecretRedactor(known_values={"K": value})
        encoded = quote(value, safe="")
        text = f"key={encoded}"
        result = redactor.redact_text(text)
        assert encoded not in result
        assert value not in result

    def test_base64_variant(self):
        """值 >= 12 字符时注册 base64url 变体。"""
        value = "sk-base64-secret-value"
        redactor = SecretRedactor(known_values={"K": value})
        encoded = base64.urlsafe_b64encode(
            value.encode("utf-8")
        ).decode("ascii")
        # strip padding 变体也应被脱敏
        encoded_stripped = encoded.rstrip("=")
        for variant in (encoded, encoded_stripped):
            text = f"config: {variant}"
            result = redactor.redact_text(text)
            assert variant not in result


# ---------------------------------------------------------------------------
# redact_text — heuristic rules
# ---------------------------------------------------------------------------


class TestRedactTextHeuristics:
    def test_assignment_pattern_redacted(self):
        redactor = SecretRedactor.empty()
        text = "API_KEY=sk-assignment-test-value"
        result = redactor.redact_text(text)
        assert "sk-assignment-test-value" not in result
        assert REDACTED in result

    def test_bearer_token_redacted(self):
        redactor = SecretRedactor.empty()
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig"
        result = redactor.redact_text(text)
        assert "Bearer <redacted>" in result
        assert "eyJhbGciOiJIUzI1NiJ9" not in result

    def test_url_userinfo_redacted(self):
        """URL 中嵌入的密码必须被移除。

        以 http(s):// 开头的 URL 会先经过 userinfo 正则，
        再经过 _sanitize_url 完全剥离 userinfo，因此
        最终结果中不含密码也不含 <redacted> 标记。
        """
        redactor = SecretRedactor.empty()
        text = "https://user:password123@example.com/path"
        result = redactor.redact_text(text)
        assert "password123" not in result
        assert "user:password123" not in result
        assert "example.com" in result

    def test_url_sanitized_when_starts_with_http(self):
        redactor = SecretRedactor.empty()
        text = "https://user:pass@host.example.com:8080/api?key=val"
        result = redactor.redact_text(text)
        assert "user:pass" not in result
        assert "host.example.com" in result

    def test_non_url_not_sanitized(self):
        redactor = SecretRedactor.empty()
        text = "just a plain string"
        assert redactor.redact_text(text) == text


# ---------------------------------------------------------------------------
# redact_object
# ---------------------------------------------------------------------------


class TestRedactObject:
    def test_sensitive_key_redacted(self):
        redactor = SecretRedactor.empty()
        data = {
            "api_key": "sk-value-12345678",
            "name": "project",
        }
        result = redactor.redact_object(data)
        assert result["api_key"] == REDACTED
        assert result["name"] == "project"

    def test_nested_sensitive_key(self):
        redactor = SecretRedactor.empty()
        data = {
            "config": {
                "token": "tok-1234567890",
                "port": 8080,
            }
        }
        result = redactor.redact_object(data)
        assert result["config"]["token"] == REDACTED
        assert result["config"]["port"] == 8080

    def test_list_items_redacted(self):
        redactor = SecretRedactor(
            known_values={"K": "list-secret-123456"}
        )
        data = ["list-secret-123456", "plain"]
        result = redactor.redact_object(data)
        assert result[0] == REDACTED
        assert result[1] == "plain"

    def test_known_value_in_object_string(self):
        redactor = SecretRedactor(
            known_values={"K": SECRET_VALUE}
        )
        data = {"message": f"token is {SECRET_VALUE}"}
        result = redactor.redact_object(data)
        assert SECRET_VALUE not in result["message"]
        assert REDACTED in result["message"]

    def test_scalars_passthrough(self):
        redactor = SecretRedactor.empty()
        assert redactor.redact_object(42) == 42
        assert redactor.redact_object(3.14) == 3.14
        assert redactor.redact_object(True) is True
        assert redactor.redact_object(None) is None

    def test_max_chars_applied_to_strings(self):
        redactor = SecretRedactor.empty()
        long_string = "x" * 500
        result = redactor.redact_object(
            {"data": long_string}, max_chars=10
        )
        assert len(result["data"]) <= 10


# ---------------------------------------------------------------------------
# find_known / contains / assert_no_known_secret
# ---------------------------------------------------------------------------


class TestFindAndContains:
    def test_find_known_in_text(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        names = redactor.find_known_in_text(
            f"value={SECRET_VALUE}"
        )
        assert SECRET_NAME in names

    def test_find_known_in_text_empty(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        assert redactor.find_known_in_text("nothing") == []

    def test_find_known_in_bytes(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        names = redactor.find_known_in_bytes(
            SECRET_VALUE.encode("utf-8")
        )
        assert SECRET_NAME in names

    def test_contains_secret(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        assert redactor.contains_secret(SECRET_VALUE)
        assert not redactor.contains_secret("no-secret-here")

    def test_contains_secret_bytes(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        assert redactor.contains_secret_bytes(
            SECRET_VALUE.encode("utf-8")
        )
        assert not redactor.contains_secret_bytes(b"clean")

    def test_assert_no_known_secret_passes(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        redactor.assert_no_known_secret(
            b"clean data", boundary="test"
        )

    def test_assert_no_known_secret_raises(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        with pytest.raises(SecretLeakDetectedError) as exc_info:
            redactor.assert_no_known_secret(
                SECRET_VALUE.encode("utf-8"),
                boundary="artifact",
            )
        assert "artifact" in str(exc_info.value)
        assert SECRET_NAME in str(exc_info.value)


# ---------------------------------------------------------------------------
# StreamingSecretRedactor
# ---------------------------------------------------------------------------


class TestStreamingRedactor:
    def test_single_chunk_redacted(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        stream = redactor.stream()
        data = f"prefix {SECRET_VALUE} suffix".encode("utf-8")
        out = stream.feed(data)
        out += stream.flush()
        assert SECRET_VALUE.encode("utf-8") not in out
        assert REDACTED_BYTES in out

    def test_secret_split_across_chunks(self):
        """Secret 被切到两个 chunk 中间时仍可匹配。"""
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        stream = redactor.stream()
        encoded = SECRET_VALUE.encode("utf-8")
        mid = len(encoded) // 2
        out1 = stream.feed(encoded[:mid])
        out2 = stream.feed(encoded[mid:])
        out3 = stream.flush()
        combined = out1 + out2 + out3
        assert encoded not in combined
        assert REDACTED_BYTES in combined

    def test_secret_at_boundary(self):
        """Secret 恰好在 chunk 边界开始。"""
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        stream = redactor.stream()
        encoded = SECRET_VALUE.encode("utf-8")
        out1 = stream.feed(b"prefix:")
        out2 = stream.feed(encoded)
        out3 = stream.feed(b":suffix")
        out4 = stream.flush()
        combined = out1 + out2 + out3 + out4
        assert encoded not in combined
        assert REDACTED_BYTES in combined

    def test_no_secret_passthrough(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        stream = redactor.stream()
        data = b"just regular content"
        out = stream.feed(data)
        out += stream.flush()
        assert out == data

    def test_multiple_secrets_in_stream(self):
        redactor = SecretRedactor(
            known_values={
                "K1": "alpha-secret-1234",
                "K2": "beta-secret-12345",
            }
        )
        stream = redactor.stream()
        data = (
            b"alpha-secret-1234 then beta-secret-12345 end"
        )
        out = stream.feed(data)
        out += stream.flush()
        assert b"alpha-secret-1234" not in out
        assert b"beta-secret-12345" not in out
        assert out.count(REDACTED_BYTES) == 2

    def test_flush_after_flush_returns_empty(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        stream = redactor.stream()
        stream.feed(b"data")
        stream.flush()
        assert stream.flush() == b""

    def test_feed_after_flush_raises(self):
        redactor = SecretRedactor(
            known_values={SECRET_NAME: SECRET_VALUE}
        )
        stream = redactor.stream()
        stream.flush()
        with pytest.raises(RuntimeError):
            stream.feed(b"more")

    def test_partial_prefix_held_in_buffer(self):
        """buffer 中只可能是某个 pattern 的前缀时，flush 前不输出。"""
        redactor = SecretRedactor(
            known_values={"K": "abcdefghij-secret"}
        )
        stream = redactor.stream()
        # 只发送前 3 个字符
        out = stream.feed(b"abc")
        # 此时不应输出任何字节，因为可能是 pattern 前缀
        assert out == b""
        # flush 后输出原始数据
        out = stream.flush()
        assert out == b"abc"


# ---------------------------------------------------------------------------
# Material integration
# ---------------------------------------------------------------------------


class TestRedactorFromMaterial:
    def test_redactor_built_from_material(self):
        material = _material()
        redactor = SecretRedactor([material])
        text = f"key={SECRET_VALUE}"
        result = redactor.redact_text(text)
        assert SECRET_VALUE not in result
        assert REDACTED in result

    def test_from_values_factory(self):
        redactor = SecretRedactor.from_values([SECRET_VALUE])
        text = f"token: {SECRET_VALUE}"
        result = redactor.redact_text(text)
        assert SECRET_VALUE not in result


# ---------------------------------------------------------------------------
# Material anti-serialization
# ---------------------------------------------------------------------------


class TestMaterialSafety:
    def test_material_str_is_redacted(self):
        material = _material()
        assert str(material) == "<redacted>"

    def test_material_repr_does_not_leak(self):
        material = _material()
        rendered = repr(material)
        assert SECRET_VALUE not in rendered
        assert "<redacted>" in rendered

    def test_material_forbids_pickle(self):
        material = _material()
        with pytest.raises(TypeError):
            pickle.dumps(material)

    def test_material_forbids_copy(self):
        import copy

        material = _material()
        with pytest.raises(TypeError):
            copy.deepcopy(material)
