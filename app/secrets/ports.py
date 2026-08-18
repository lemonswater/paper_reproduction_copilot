from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.secrets.schemas import (
    SecretAuditRecord,
    SecretMetadata,
    SecretReference,
    SecretUse,
)


@dataclass(frozen=True)
class SecretMaterial:
    """受信任调用栈内的短期明文包装。

    _value 不参与 repr；对象禁止 pickle，避免进入 Checkpoint。
    """

    reference: SecretReference
    allowed_uses: tuple[SecretUse, ...]
    _value: str = field(repr=False)

    def reveal(self) -> str:
        return self._value

    def __str__(self) -> str:
        return "<redacted>"

    def __repr__(self) -> str:
        return (
            "SecretMaterial("
            f"name={self.reference.name!r}, "
            f"version={self.reference.version}, "
            "value=<redacted>)"
        )

    def __getstate__(self):
        raise TypeError("SecretMaterial 禁止序列化或写入 Checkpoint")

    def __reduce__(self):
        raise TypeError("SecretMaterial 禁止 pickle")


class SecretStore(Protocol):
    def initialize(self) -> None:
        ...

    def put(
        self,
        *,
        name: str,
        value: str,
        allowed_uses: list[SecretUse],
        actor: str,
    ) -> SecretMetadata:
        ...

    def current_reference(self, name: str) -> SecretReference:
        ...

    def resolve(
        self,
        *,
        reference: SecretReference,
        use: SecretUse,
        actor: str,
    ) -> SecretMaterial:
        ...

    def list_metadata(self) -> list[SecretMetadata]:
        ...

    def revoke(
        self,
        *,
        reference: SecretReference,
        actor: str,
    ) -> SecretMetadata:
        ...

    def active_materials_for_redaction(
        self,
        *,
        actor: str,
    ) -> list[SecretMaterial]:
        ...

    def list_audit(
        self,
        *,
        limit: int = 200,
    ) -> list[SecretAuditRecord]:
        ...
