from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, Request

from app.secrets.errors import SecretNotFoundError
from app.secrets.schemas import SecretUse


_MISSING = object()


def require_api_auth(
    request: Request,
    authorization: str | None = Header(
        default=None,
        alias="Authorization",
    ),
) -> str:
    """
    返回审计 actor。

    未配置 token 时，serve-api 会强制只能监听 loopback。
    """

    override = getattr(
        request.app.state, "api_token_override", None
    )
    if override is not None:
        expected = override.get_secret_value()
    else:
        # 兼容只挂载 router 的旧测试/嵌入式应用。生产 App Factory
        # 不再设置 api_token，而是始终注入 SecretService。
        legacy_token = getattr(
            request.app.state, "api_token", _MISSING
        )
        if legacy_token is not _MISSING:
            if not legacy_token:
                return "api:local"
            get_secret_value = getattr(
                legacy_token, "get_secret_value", None
            )
            expected = (
                get_secret_value()
                if callable(get_secret_value)
                else str(legacy_token)
            )
        else:
            secret_service = getattr(
                request.app.state, "secret_service", None
            )
            secret_name = getattr(
                request.app.state,
                "api_token_secret_name",
                None,
            )
            if secret_service is None or not secret_name:
                raise RuntimeError(
                    "API 认证依赖未装配：缺少 SecretService"
                )

            try:
                material = secret_service.resolve_current(
                    name=secret_name,
                    use=SecretUse.API_AUTH,
                    actor="api:auth",
                )
                expected = material.reveal()
            except SecretNotFoundError:
                # 未配置 Token 只允许 serve 命令绑定 loopback；
                # 非 loopback 的检查仍由 serve-api 启动边界执行。
                return "api:local"

    scheme, separator, credentials = (
        authorization or ""
    ).partition(" ")
    valid = (
        separator == " "
        and scheme.lower() == "bearer"
        and secrets.compare_digest(credentials, expected)
    )
    if not valid:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "缺少或无效的 Bearer Token",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "api:token"
