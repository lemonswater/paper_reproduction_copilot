from __future__ import annotations

import secrets

from starlette.responses import JSONResponse


class LocalBearerAuthMiddleware:
    """保护本机 HTTP MCP endpoint；不实现 OAuth 或 Token 转发。"""

    def __init__(
        self,
        app,
        *,
        expected_token: str,
        public_paths: set[str] | None = None,
    ) -> None:
        token = expected_token.strip()
        if len(token) < 32:
            raise ValueError("MCP Export Token 至少需要 32 个字符")
        self.app = app
        self._expected = token.encode("utf-8")
        self.public_paths = set(public_paths or {"/healthz"})

    @staticmethod
    def _authorization_values(scope) -> list[bytes]:
        return [
            value
            for key, value in scope.get("headers", [])
            if key.lower() == b"authorization"
        ]

    async def __call__(self, scope, receive, send) -> None:
        # lifespan 和非 HTTP scope 必须原样传递给 MCP SDK。
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("path") in self.public_paths:
            await self.app(scope, receive, send)
            return

        values = self._authorization_values(scope)
        valid = False
        if len(values) == 1:
            try:
                raw = values[0].decode("utf-8")
            except UnicodeDecodeError:
                raw = ""
            scheme, separator, credential = raw.partition(" ")
            valid = (
                separator == " "
                and scheme.lower() == "bearer"
                and secrets.compare_digest(
                    credential.encode("utf-8"),
                    self._expected,
                )
            )

        if not valid:
            response = JSONResponse(
                {
                    "error": {
                        "code": "MCP_EXPORT_UNAUTHORIZED",
                        "message": "Authentication required",
                    }
                },
                status_code=401,
                headers={
                    "WWW-Authenticate": (
                        'Bearer realm="paper-reproduction-mcp"'
                    ),
                    "Cache-Control": "no-store",
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
