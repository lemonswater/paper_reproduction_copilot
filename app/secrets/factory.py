from __future__ import annotations

import threading

from app.config import settings
from app.secrets.crypto import FernetSecretCipher
from app.secrets.service import SecretService
from app.secrets.store import SqliteSecretStore


_lock = threading.Lock()
_service: SecretService | None = None


def build_secret_service() -> SecretService:
    global _service
    with _lock:
        if _service is None:
            cipher = FernetSecretCipher(
                settings.secret_master_key_path
            )
            _service = SecretService(
                SqliteSecretStore(
                    path=settings.secret_vault_db_path,
                    cipher=cipher,
                )
            )
        return _service


def reset_secret_service_for_tests() -> None:
    global _service
    with _lock:
        _service = None
