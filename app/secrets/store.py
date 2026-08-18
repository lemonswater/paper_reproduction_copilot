from __future__ import annotations

import json
import os
import sqlite3
import stat
from datetime import datetime, timezone
from pathlib import Path

from app.secrets.crypto import FernetSecretCipher
from app.secrets.errors import (
    SecretConfigurationError,
    SecretInactiveError,
    SecretIntegrityError,
    SecretNotFoundError,
    SecretUseDeniedError,
)
from app.secrets.ports import SecretMaterial
from app.secrets.schemas import (
    SECRET_NAME_RE,
    SecretAuditRecord,
    SecretMetadata,
    SecretReference,
    SecretStatus,
    SecretUse,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(value: str) -> str:
    name = value.strip().upper()
    if not SECRET_NAME_RE.fullmatch(name):
        raise ValueError(
            "Secret name 必须是 3..128 位大写字母、数字或下划线"
        )
    return name


def _validate_plaintext(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Secret value 必须是字符串")
    if not 8 <= len(value) <= 16384:
        raise ValueError("Secret value 长度必须位于 8..16384")
    if "\x00" in value:
        raise ValueError("Secret value 不能包含 NUL")
    return value


class SqliteSecretStore:
    def __init__(
        self,
        *,
        path: Path,
        cipher: FernetSecretCipher,
    ):
        self.path = Path(os.path.abspath(path.expanduser()))
        self.cipher = cipher

    def _prepare_private_database_file(self) -> None:
        """在 SQLite 打开前固定路径类型和权限，避免首次创建窗口。"""

        parent = self.path.parent
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent_info = parent.lstat()
        if stat.S_ISLNK(parent_info.st_mode):
            raise SecretConfigurationError(
                "Secret Vault 目录不能是符号链接"
            )
        if not stat.S_ISDIR(parent_info.st_mode):
            raise SecretConfigurationError(
                "Secret Vault 父路径必须是目录"
            )
        if stat.S_IMODE(parent_info.st_mode) & 0o077:
            raise SecretConfigurationError(
                "Secret Vault 目录权限必须为 0700"
            )

        if self.path.is_symlink():
            raise SecretConfigurationError(
                "Secret Vault 不能是符号链接"
            )
        if self.path.exists():
            info = self.path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise SecretConfigurationError(
                    "Secret Vault 必须是普通文件"
                )
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise SecretConfigurationError(
                    "Secret Vault 文件权限必须为 0600"
                )
            return

        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.path, flags, 0o600)
        os.close(descriptor)

    def _connect(self) -> sqlite3.Connection:
        self._prepare_private_database_file()
        connection = sqlite3.connect(
            self.path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS secret_versions (
                    name TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    ciphertext BLOB NOT NULL,
                    value_fingerprint TEXT NOT NULL,
                    allowed_uses_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_used_at TEXT,
                    PRIMARY KEY (name, version),
                    CHECK (version >= 1),
                    CHECK (
                        status IN ('active', 'superseded', 'revoked')
                    )
                );

                CREATE UNIQUE INDEX IF NOT EXISTS
                    uq_secret_one_active_version
                ON secret_versions(name)
                WHERE status = 'active';

                CREATE TABLE IF NOT EXISTS secret_audit (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    secret_name TEXT NOT NULL,
                    secret_version INTEGER NOT NULL,
                    use_name TEXT,
                    actor TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
        self._chmod_sqlite_files()

    def _chmod_sqlite_files(self) -> None:
        for candidate in (
            self.path,
            self.path.with_name(self.path.name + "-wal"),
            self.path.with_name(self.path.name + "-shm"),
        ):
            if candidate.exists():
                if candidate.is_symlink():
                    raise SecretConfigurationError(
                        "Secret SQLite 文件不能是符号链接"
                    )
                os.chmod(candidate, 0o600)

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        *,
        event_type: str,
        name: str,
        version: int,
        use: SecretUse | None,
        actor: str,
        outcome: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO secret_audit (
                event_type, secret_name, secret_version,
                use_name, actor, outcome, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                name,
                version,
                use.value if use is not None else None,
                actor[:200],
                outcome,
                _utc_now(),
            ),
        )

    @staticmethod
    def _metadata(row: sqlite3.Row) -> SecretMetadata:
        uses = [
            SecretUse(item)
            for item in json.loads(row["allowed_uses_json"])
        ]
        return SecretMetadata(
            reference=SecretReference(
                name=row["name"],
                version=row["version"],
                fingerprint=row["value_fingerprint"],
            ),
            status=SecretStatus(row["status"]),
            allowed_uses=uses,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_used_at=row["last_used_at"],
        )

    def put(
        self,
        *,
        name: str,
        value: str,
        allowed_uses: list[SecretUse],
        actor: str,
    ) -> SecretMetadata:
        normalized_name = _normalize_name(name)
        plaintext = _validate_plaintext(value)
        normalized_uses = sorted(
            set(allowed_uses),
            key=lambda item: item.value,
        )
        if not normalized_uses:
            raise ValueError("allowed_uses 不能为空")

        now = _utc_now()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT COALESCE(MAX(version), 0) AS latest
                FROM secret_versions
                WHERE name = ?
                """,
                (normalized_name,),
            ).fetchone()
            version = int(row["latest"]) + 1
            fingerprint = self.cipher.fingerprint(plaintext)
            ciphertext = self.cipher.encrypt(
                name=normalized_name,
                version=version,
                value=plaintext,
            )

            changed = connection.execute(
                """
                UPDATE secret_versions
                SET status = 'superseded', updated_at = ?
                WHERE name = ? AND status = 'active'
                """,
                (now, normalized_name),
            ).rowcount
            event_type = "secret.rotated" if changed else "secret.created"
            connection.execute(
                """
                INSERT INTO secret_versions (
                    name, version, ciphertext, value_fingerprint,
                    allowed_uses_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    normalized_name,
                    version,
                    ciphertext,
                    fingerprint,
                    json.dumps(
                        [item.value for item in normalized_uses],
                        separators=(",", ":"),
                    ),
                    now,
                    now,
                ),
            )
            self._audit(
                connection,
                event_type=event_type,
                name=normalized_name,
                version=version,
                use=None,
                actor=actor,
                outcome="succeeded",
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        self._chmod_sqlite_files()
        return self._get_metadata(normalized_name, version)

    def _get_row(
        self,
        *,
        name: str,
        version: int,
    ) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM secret_versions
                WHERE name = ? AND version = ?
                """,
                (name, version),
            ).fetchone()
        if row is None:
            raise SecretNotFoundError(
                f"Secret 不存在：{name} v{version}"
            )
        return row

    def _get_metadata(
        self,
        name: str,
        version: int,
    ) -> SecretMetadata:
        return self._metadata(
            self._get_row(name=name, version=version)
        )

    def current_reference(self, name: str) -> SecretReference:
        normalized_name = _normalize_name(name)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM secret_versions
                WHERE name = ? AND status = 'active'
                """,
                (normalized_name,),
            ).fetchone()
        if row is None:
            raise SecretNotFoundError(
                f"没有 active Secret：{normalized_name}"
            )
        return self._metadata(row).reference

    def resolve(
        self,
        *,
        reference: SecretReference,
        use: SecretUse,
        actor: str,
    ) -> SecretMaterial:
        row = self._get_row(
            name=reference.name,
            version=reference.version,
        )
        metadata = self._metadata(row)
        if metadata.status != SecretStatus.ACTIVE:
            raise SecretInactiveError(
                f"Secret 已失效：{reference.name} v{reference.version}"
            )
        if metadata.reference.fingerprint != reference.fingerprint:
            raise SecretIntegrityError(
                "Secret Reference fingerprint 不匹配："
                f"{reference.name} v{reference.version}"
            )
        if use not in metadata.allowed_uses:
            with self._connect() as connection:
                self._audit(
                    connection,
                    event_type="secret.resolved",
                    name=reference.name,
                    version=reference.version,
                    use=use,
                    actor=actor,
                    outcome="denied",
                )
            raise SecretUseDeniedError(
                f"Secret 未授权用途：{reference.name} -> {use.value}"
            )

        value = self.cipher.decrypt(
            name=reference.name,
            version=reference.version,
            ciphertext=bytes(row["ciphertext"]),
        )
        if self.cipher.fingerprint(value) != reference.fingerprint:
            raise SecretIntegrityError(
                "Secret 明文 fingerprint 不匹配："
                f"{reference.name} v{reference.version}"
            )

        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE secret_versions
                SET last_used_at = ?, updated_at = ?
                WHERE name = ? AND version = ? AND status = 'active'
                """,
                (
                    now,
                    now,
                    reference.name,
                    reference.version,
                ),
            )
            self._audit(
                connection,
                event_type="secret.resolved",
                name=reference.name,
                version=reference.version,
                use=use,
                actor=actor,
                outcome="succeeded",
            )
        return SecretMaterial(
            reference=reference,
            allowed_uses=tuple(metadata.allowed_uses),
            _value=value,
        )

    def list_metadata(self) -> list[SecretMetadata]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM secret_versions
                ORDER BY name, version DESC
                """
            ).fetchall()
        return [self._metadata(row) for row in rows]

    def revoke(
        self,
        *,
        reference: SecretReference,
        actor: str,
    ) -> SecretMetadata:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """
                UPDATE secret_versions
                SET status = 'revoked', updated_at = ?
                WHERE name = ?
                  AND version = ?
                  AND value_fingerprint = ?
                  AND status = 'active'
                """,
                (
                    _utc_now(),
                    reference.name,
                    reference.version,
                    reference.fingerprint,
                ),
            ).rowcount
            if changed != 1:
                raise SecretInactiveError(
                    "Secret 已失效或 Reference 不匹配"
                )
            self._audit(
                connection,
                event_type="secret.revoked",
                name=reference.name,
                version=reference.version,
                use=None,
                actor=actor,
                outcome="succeeded",
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self._get_metadata(
            reference.name,
            reference.version,
        )

    def active_materials_for_redaction(
        self,
        *,
        actor: str,
    ) -> list[SecretMaterial]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM secret_versions
                WHERE status = 'active'
                ORDER BY name
                """
            ).fetchall()
            materials: list[SecretMaterial] = []
            for row in rows:
                metadata = self._metadata(row)
                value = self.cipher.decrypt(
                    name=metadata.reference.name,
                    version=metadata.reference.version,
                    ciphertext=bytes(row["ciphertext"]),
                )
                if (
                    self.cipher.fingerprint(value)
                    != metadata.reference.fingerprint
                ):
                    raise SecretIntegrityError(
                        "Redactor 加载时 Secret fingerprint 不匹配"
                    )
                materials.append(
                    SecretMaterial(
                        reference=metadata.reference,
                        allowed_uses=tuple(metadata.allowed_uses),
                        _value=value,
                    )
                )
                self._audit(
                    connection,
                    event_type="secret.redactor_loaded",
                    name=metadata.reference.name,
                    version=metadata.reference.version,
                    use=None,
                    actor=actor,
                    outcome="succeeded",
                )
        return materials

    def list_audit(
        self,
        *,
        limit: int = 200,
    ) -> list[SecretAuditRecord]:
        bounded = min(max(limit, 1), 1000)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM secret_audit
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (bounded,),
            ).fetchall()
        return [
            SecretAuditRecord(
                event_id=row["event_id"],
                event_type=row["event_type"],
                secret_name=row["secret_name"],
                secret_version=row["secret_version"],
                use=(
                    SecretUse(row["use_name"])
                    if row["use_name"]
                    else None
                ),
                actor=row["actor"],
                outcome=row["outcome"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
