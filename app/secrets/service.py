from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.secrets.ports import SecretMaterial, SecretStore
from app.secrets.redaction import SecretRedactor
from app.secrets.schemas import (
    SecretMetadata,
    SecretReference,
    SecretUse,
)


class SecretService:
    def __init__(self, store: SecretStore):
        self.store = store
        self.store.initialize()

    def put(
        self,
        *,
        name: str,
        value: str,
        allowed_uses: list[SecretUse] | set[SecretUse],
        actor: str = "local:operator",
    ) -> SecretMetadata:
        return self.store.put(
            name=name,
            value=value,
            allowed_uses=list(allowed_uses),
            actor=actor,
        )

    def reference(self, name: str) -> SecretReference:
        return self.store.current_reference(name)

    def list_metadata(self) -> list[SecretMetadata]:
        return self.store.list_metadata()

    def revoke(
        self,
        *,
        reference: SecretReference,
        actor: str = "local:operator",
    ) -> SecretMetadata:
        return self.store.revoke(
            reference=reference,
            actor=actor,
        )

    def resolve(
        self,
        *,
        reference: SecretReference,
        use: SecretUse,
        actor: str,
    ) -> SecretMaterial:
        return self.store.resolve(
            reference=reference,
            use=use,
            actor=actor,
        )

    def resolve_current(
        self,
        *,
        name: str,
        use: SecretUse,
        actor: str,
    ) -> SecretMaterial:
        return self.resolve(
            reference=self.reference(name),
            use=use,
            actor=actor,
        )

    def build_redactor(
        self,
        *,
        actor: str,
    ) -> SecretRedactor:
        materials = self.store.active_materials_for_redaction(
            actor=actor
        )
        return SecretRedactor(materials)

    @contextmanager
    def material(
        self,
        reference: SecretReference,
        *,
        required_use: SecretUse,
        actor: str = "runtime:scoped",
    ) -> Iterator[SecretMaterial]:
        """给调用方一个结构化短生命周期边界。

        Python str 无法可靠清零；context manager 的价值是限制变量作用域，
        不是声称能从内存中物理擦除 material。
        """

        material = self.resolve(
            reference=reference,
            use=required_use,
            actor=actor,
        )
        try:
            yield material
        finally:
            del material
