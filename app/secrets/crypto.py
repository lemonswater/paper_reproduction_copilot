from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.secrets.errors import (
    SecretConfigurationError,
    SecretIntegrityError,
)


def require_private_regular_file(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise SecretConfigurationError(
            f"Secret 文件不存在：{path}"
        ) from exc
    if stat.S_ISLNK(info.st_mode):
        raise SecretConfigurationError("Secret 文件不能是符号链接")
    if not stat.S_ISREG(info.st_mode):
        raise SecretConfigurationError("Secret 文件必须是普通文件")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise SecretConfigurationError(
            f"Secret 文件权限过宽：{path}，要求 0600"
        )


def create_master_key_file(path: Path) -> None:
    """显式初始化 Master Key；运行时不能静默重新生成。"""

    target = Path(os.path.abspath(path.expanduser()))
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent_info = parent.lstat()
    if stat.S_ISLNK(parent_info.st_mode):
        raise SecretConfigurationError(
            "Master Key 目录不能是符号链接"
        )
    if not stat.S_ISDIR(parent_info.st_mode):
        raise SecretConfigurationError(
            "Master Key 父路径必须是目录"
        )
    os.chmod(parent, 0o700)
    if target.exists() or target.is_symlink():
        raise SecretConfigurationError("Master Key 已存在")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(Fernet.generate_key() + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    os.chmod(target, 0o600)


class FernetSecretCipher:
    def __init__(self, key_path: Path):
        self.key_path = Path(
            os.path.abspath(key_path.expanduser())
        )
        require_private_regular_file(self.key_path)
        key = self.key_path.read_bytes().strip()
        try:
            raw_key = base64.urlsafe_b64decode(key)
            if len(raw_key) != 32:
                raise ValueError("invalid key length")
            self._fernet = Fernet(key)
        except (ValueError, TypeError) as exc:
            raise SecretConfigurationError(
                "Master Key 不是合法 Fernet Key"
            ) from exc
        self._fingerprint_key = hmac.new(
            raw_key,
            b"paper-copilot-phase41-fingerprint-v1",
            hashlib.sha256,
        ).digest()

    def fingerprint(self, value: str) -> str:
        digest = hmac.new(
            self._fingerprint_key,
            value.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"hmac-sha256:{digest}"

    def encrypt(
        self,
        *,
        name: str,
        version: int,
        value: str,
    ) -> bytes:
        envelope = json.dumps(
            {
                "format": "phase41-v1",
                "name": name,
                "version": version,
                "value": value,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return self._fernet.encrypt(envelope)

    def decrypt(
        self,
        *,
        name: str,
        version: int,
        ciphertext: bytes,
    ) -> str:
        try:
            envelope = json.loads(
                self._fernet.decrypt(ciphertext).decode("utf-8")
            )
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SecretIntegrityError(
                f"Secret 密文无法通过认证：{name} v{version}"
            ) from exc

        if (
            envelope.get("format") != "phase41-v1"
            or envelope.get("name") != name
            or envelope.get("version") != version
            or not isinstance(envelope.get("value"), str)
        ):
            raise SecretIntegrityError(
                f"Secret Envelope 身份不匹配：{name} v{version}"
            )
        return str(envelope["value"])
