"""Phase 30 SPA 静态文件托管。

生产构建使用 ``vite build`` 生成 ``web/dist/``，由 FastAPI 同源托管，
不需要 CORS。未知的无扩展名路径回退到 index.html，让前端路由接管。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response


class SpaStaticFiles(StaticFiles):
    """未知的无扩展名路径回退到 index.html，静态资源 404 不回退。"""

    async def get_response(
        self, path: str, scope
    ) -> Response:
        try:
            response = await super().get_response(
                path, scope
            )
        except HTTPException as exc:
            # StaticFiles 在没有自定义 404.html 时会抛异常，
            # 但 JS/CSS/image 等真实静态资源仍应保持 404。
            if exc.status_code != 404 or Path(path).suffix:
                raise
            return await super().get_response(
                "index.html", scope
            )

        # 如果 dist 中存在 404.html，StaticFiles 可能返回 404 Response
        # 而不是抛异常，因此这个分支也要保留。
        if response.status_code == 404 and not Path(
            path
        ).suffix:
            return await super().get_response(
                "index.html", scope
            )
        return response


def mount_web_ui(
    app: FastAPI,
    *,
    dist_dir: Path,
    required: bool,
) -> None:
    resolved = dist_dir.expanduser().resolve()
    index = resolved / "index.html"
    if not index.is_file():
        if required:
            raise RuntimeError(
                f"WEB_UI_REQUIRED=true，但缺少前端构建：{index}"
            )
        return

    # 必须最后 mount，避免吞掉 /v1、/docs、/livez 和 /readyz。
    app.mount(
        "/",
        SpaStaticFiles(directory=resolved, html=True),
        name="web-ui",
    )
