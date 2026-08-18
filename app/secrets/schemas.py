from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SECRET_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
FINGERPRINT_RE = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")


class SecretModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SecretUse(str, Enum):
    PROVIDER = "provider"
    EMBEDDING = "embedding"
    DATABASE = "database"
    API_AUTH = "api_auth"
    RESOURCE_HTTP = "resource_http"
    RESOURCE_GIT = "resource_git"
    EXECUTION_ENV = "execution_env"
    RESEARCH_SEARCH = "research_search"

    # MCP Export Token 只验证入站本机 MCP 请求，不能当成 API 或 Provider Key。
    MCP_EXPORT_AUTH = "mcp_export_auth"


class SecretStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"


class SecretReference(SecretModel):
    """可以进入 State、Action、Request 和 Approval Hash 的公开引用。"""

    name: str = Field(pattern=SECRET_NAME_RE.pattern)
    version: int = Field(ge=1)
    fingerprint: str = Field(pattern=FINGERPRINT_RE.pattern)


class SecretMetadata(SecretModel):
    reference: SecretReference
    status: SecretStatus
    allowed_uses: list[SecretUse] = Field(min_length=1)
    created_at: str
    updated_at: str
    last_used_at: str | None = None

    @field_validator("allowed_uses")
    @classmethod
    def normalize_uses(
        cls,
        value: list[SecretUse],
    ) -> list[SecretUse]:
        unique = sorted(set(value), key=lambda item: item.value)
        if not unique:
            raise ValueError("allowed_uses 不能为空")
        return unique


class SecretAuditRecord(SecretModel):
    event_id: int
    event_type: Literal[
        "secret.created",
        "secret.rotated",
        "secret.resolved",
        "secret.revoked",
        "secret.redactor_loaded",
    ]
    secret_name: str
    secret_version: int
    use: SecretUse | None = None
    actor: str
    outcome: Literal["succeeded", "denied", "failed"]
    created_at: str


class SecretHealthReport(SecretModel):
    ok: bool
    vault_initialized: bool
    key_permissions_ok: bool
    vault_permissions_ok: bool
    active_secret_count: int = Field(ge=0)
    issues: list[str] = Field(default_factory=list)
