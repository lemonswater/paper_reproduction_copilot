from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from app.secrets.crypto import (
    FernetSecretCipher,
    create_master_key_file,
)
from app.secrets.errors import (
    SecretConfigurationError,
    SecretInactiveError,
    SecretIntegrityError,
    SecretNotFoundError,
    SecretUseDeniedError,
)
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService
from app.secrets.store import SqliteSecretStore


@pytest.fixture()
def secret_env(tmp_path: Path):
    key_path = tmp_path / "master.key"
    vault_path = tmp_path / "vault.sqlite"
    create_master_key_file(key_path)
    cipher = FernetSecretCipher(key_path)
    store = SqliteSecretStore(path=vault_path, cipher=cipher)
    service = SecretService(store)
    return service


class TestSecretStore:
    def test_put_and_resolve(self, secret_env):
        metadata = secret_env.put(
            name="OPENAI_API_KEY",
            value="sk-test-12345678",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        assert metadata.reference.version == 1
        assert metadata.status.value == "active"
        assert "hmac-sha256:" in metadata.reference.fingerprint

        material = secret_env.resolve(
            reference=metadata.reference,
            use=SecretUse.PROVIDER,
            actor="test",
        )
        assert material.reveal() == "sk-test-12345678"

    def test_rotation_supersedes_old_version(
        self, secret_env
    ):
        v1 = secret_env.put(
            name="OPENAI_API_KEY",
            value="sk-old-12345678",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        v2 = secret_env.put(
            name="OPENAI_API_KEY",
            value="sk-new-12345678",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        assert v1.reference.version == 1
        assert v2.reference.version == 2

        with pytest.raises(SecretInactiveError):
            secret_env.resolve(
                reference=v1.reference,
                use=SecretUse.PROVIDER,
                actor="test",
            )

        material = secret_env.resolve(
            reference=v2.reference,
            use=SecretUse.PROVIDER,
            actor="test",
        )
        assert material.reveal() == "sk-new-12345678"

    def test_use_denied(self, secret_env):
        metadata = secret_env.put(
            name="OPENAI_API_KEY",
            value="sk-test-12345678",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        with pytest.raises(SecretUseDeniedError):
            secret_env.resolve(
                reference=metadata.reference,
                use=SecretUse.DATABASE,
                actor="test",
            )

    def test_revoke(self, secret_env):
        metadata = secret_env.put(
            name="OPENAI_API_KEY",
            value="sk-test-12345678",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        revoked = secret_env.revoke(
            reference=metadata.reference,
            actor="test",
        )
        assert revoked.status.value == "revoked"

        with pytest.raises(SecretInactiveError):
            secret_env.resolve(
                reference=metadata.reference,
                use=SecretUse.PROVIDER,
                actor="test",
            )

    def test_fingerprint_mismatch_fails(
        self, secret_env
    ):
        metadata = secret_env.put(
            name="OPENAI_API_KEY",
            value="sk-test-12345678",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        bad_ref = metadata.reference.model_copy(
            update={
                "fingerprint": "hmac-sha256:"
                + "0" * 64
            }
        )
        with pytest.raises(SecretIntegrityError):
            secret_env.resolve(
                reference=bad_ref,
                use=SecretUse.PROVIDER,
                actor="test",
            )

    def test_not_found(self, secret_env):
        with pytest.raises(SecretNotFoundError):
            secret_env.reference("NONEXISTENT_KEY")

    def test_material_repr_is_redacted(
        self, secret_env
    ):
        metadata = secret_env.put(
            name="OPENAI_API_KEY",
            value="sk-secret-value-99",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        material = secret_env.resolve(
            reference=metadata.reference,
            use=SecretUse.PROVIDER,
            actor="test",
        )
        assert "sk-secret-value-99" not in repr(material)
        assert "sk-secret-value-99" not in str(material)
        assert "<redacted>" in str(material)

    def test_material_forbids_pickle(
        self, secret_env
    ):
        import pickle

        metadata = secret_env.put(
            name="OPENAI_API_KEY",
            value="sk-test-12345678",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        material = secret_env.resolve(
            reference=metadata.reference,
            use=SecretUse.PROVIDER,
            actor="test",
        )
        with pytest.raises(TypeError):
            pickle.dumps(material)

    def test_list_metadata(self, secret_env):
        secret_env.put(
            name="KEY_A",
            value="value-a-1234567",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        secret_env.put(
            name="KEY_B",
            value="value-b-1234567",
            allowed_uses={SecretUse.DATABASE},
            actor="test",
        )
        items = secret_env.list_metadata()
        names = {item.reference.name for item in items}
        assert names == {"KEY_A", "KEY_B"}

    def test_vault_file_permissions(self, tmp_path):
        key_path = tmp_path / "master.key"
        vault_path = tmp_path / "vault.sqlite"
        create_master_key_file(key_path)

        cipher = FernetSecretCipher(key_path)
        store = SqliteSecretStore(
            path=vault_path, cipher=cipher
        )
        store.initialize()

        mode = stat.S_IMODE(vault_path.lstat().st_mode)
        assert mode == 0o600

        key_mode = stat.S_IMODE(
            key_path.lstat().st_mode
        )
        assert key_mode == 0o600

    def test_symlink_key_rejected(self, tmp_path):
        real_key = tmp_path / "real.key"
        create_master_key_file(real_key)
        link_key = tmp_path / "link.key"
        os.symlink(real_key, link_key)

        with pytest.raises(SecretConfigurationError):
            FernetSecretCipher(link_key)

    def test_current_reference_returns_active(
        self, secret_env
    ):
        v1 = secret_env.put(
            name="TEST_KEY",
            value="v1-value-1234567",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        v2 = secret_env.put(
            name="TEST_KEY",
            value="v2-value-1234567",
            allowed_uses={SecretUse.PROVIDER},
            actor="test",
        )
        current = secret_env.reference("TEST_KEY")
        assert current.version == 2
        assert current.fingerprint == v2.reference.fingerprint
