from __future__ import annotations

import os
import stat
from pathlib import Path

from app.secrets.crypto import FernetSecretCipher
from app.secrets.schemas import SecretHealthReport, SecretStatus
from app.secrets.store import SqliteSecretStore


LEGACY_PLAINTEXT_ENV_NAMES = (
    "OPENAI_API_KEY",
    "EMBEDDING_API_KEY",
    "AGENT_API_TOKEN",
    "DATABASE_URL",
)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _private_regular_file(path: Path) -> bool:
    if not path.exists() or path.is_symlink():
        return False
    info = path.lstat()
    return stat.S_ISREG(info.st_mode) and not (
        stat.S_IMODE(info.st_mode) & 0o077
    )


def inspect_secret_health(
    *,
    key_path: Path,
    vault_path: Path,
    allowed_root: Path,
) -> SecretHealthReport:
    """只读取安全状态和 Metadata；绝不返回 material。"""

    key = _absolute(key_path)
    vault = _absolute(vault_path)
    root = _absolute(allowed_root)
    secret_root = key.parent
    issues: list[str] = []

    if secret_root != vault.parent:
        issues.append("key 和 vault 不在同一目录")
    if not secret_root.is_relative_to(root):
        issues.append("secret root 位于 ALLOWED_ROOT 外")

    directory_ok = False
    if secret_root.exists() and not secret_root.is_symlink():
        info = secret_root.lstat()
        directory_ok = stat.S_ISDIR(info.st_mode) and not (
            stat.S_IMODE(info.st_mode) & 0o077
        )
    if not directory_ok:
        issues.append("secret root 必须是权限 0700 的普通目录")

    key_ok = _private_regular_file(key)
    vault_ok = _private_regular_file(vault)
    if not key_ok:
        issues.append("master key 缺失、类型错误或权限不是 0600")
    if not vault.exists():
        issues.append("vault 尚未初始化")
    elif not vault_ok:
        issues.append("vault 类型错误或权限不是 0600")

    active_count = 0
    vault_initialized = key_ok and vault_ok and directory_ok
    if vault_initialized:
        try:
            store = SqliteSecretStore(
                path=vault,
                cipher=FernetSecretCipher(key),
            )
            store.initialize()
            active_count = sum(
                item.status == SecretStatus.ACTIVE
                for item in store.list_metadata()
            )
        except Exception as exc:
            issues.append(
                f"vault schema/integrity check failed: "
                f"{type(exc).__name__}"
            )
            vault_initialized = False

    legacy_names = [
        name
        for name in LEGACY_PLAINTEXT_ENV_NAMES
        if os.getenv(name)
    ]
    if legacy_names:
        issues.append(
            "仍存在旧明文环境变量："
            + ",".join(sorted(legacy_names))
        )

    return SecretHealthReport(
        ok=not issues,
        vault_initialized=vault_initialized,
        key_permissions_ok=key_ok and directory_ok,
        vault_permissions_ok=vault_ok and directory_ok,
        active_secret_count=active_count,
        issues=issues,
    )
