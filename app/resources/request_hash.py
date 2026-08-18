from __future__ import annotations

"""Phase 29 URL 规范化与 request hash。

审批必须绑定 request_sha256。审批后若 URL/commit/expected hash/purpose 任一改变，
旧审批自动失效（stale approval）。
"""

import hashlib
import json
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from app.resources.schemas import ResourceRequest


def canonicalize_url(raw: str) -> str:
    """规范化 URL：只允许 HTTPS、默认 443 端口、无 userinfo/query/fragment。"""

    parsed = urlsplit(raw.strip())
    if parsed.scheme.lower() != "https":
        raise ValueError("Resource URL 第一版只允许 HTTPS")
    if (
        parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Resource URL 禁止 userinfo")
    if parsed.fragment:
        raise ValueError("Resource URL 禁止 fragment")
    if parsed.query:
        # 第一版不接受 query，避免误把 presigned token/凭据持久化或写入日志。
        raise ValueError("Resource URL 第一版禁止 query 参数")
    if not parsed.hostname:
        raise ValueError("Resource URL 缺少 host")

    try:
        host = parsed.hostname.encode("idna").decode(
            "ascii"
        ).lower()
    except UnicodeError as exc:
        raise ValueError(
            "Resource URL host IDNA 编码失败"
        ) from exc
    port = parsed.port
    if port not in {None, 443}:
        raise ValueError(
            "Resource URL 只允许 HTTPS 默认端口 443"
        )
    netloc = host

    # 第一版 query 已被拒绝，只需稳定编码 path。
    path = quote(
        unquote(parsed.path or "/"), safe="/%:@"
    )
    return urlunsplit(("https", netloc, path, "", ""))


def resource_request_sha256(
    request: ResourceRequest,
) -> str:
    """对 request 做确定性 hash，URL 先经 canonicalize_url 规范化。"""

    payload = request.model_copy(
        update={
            "source_url": canonicalize_url(
                request.source_url
            )
        }
    ).model_dump(mode="json")
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
