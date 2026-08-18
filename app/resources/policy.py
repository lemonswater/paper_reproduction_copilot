from __future__ import annotations

"""Phase 29 确定性 URL/DNS policy。

应用层 DNS/IP 检查重要，但不能单独彻底解决 DNS rebinding/TOCTOU：
代码检查域名解析结果后，HTTP/Git 客户端可能再次解析。生产级边界应是两层：
- 应用层：scheme/host/port/DNS/redirect/size/hash/type policy（本模块）
- 网络层：专用 Acquisition Worker + egress proxy/firewall

未配置网络层 guard 时 readiness 必须报告 degraded_application_guard_only。
"""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.resources.errors import ResourcePolicyViolation
from app.resources.request_hash import canonicalize_url


@dataclass(frozen=True)
class ValidatedDestination:
    canonical_url: str
    host: str
    resolved_ips: tuple[str, ...]


def host_allowed(
    host: str, allowed_hosts: tuple[str, ...]
) -> bool:
    """精确 host 或明确子域。

    ``endswith("github.com")`` 会错误接受 ``evilgithub.com``，因此必须带点。
    """

    return any(
        host == item or host.endswith(f".{item}")
        for item in allowed_hosts
    )


def resolve_public_ips(host: str) -> tuple[str, ...]:
    """解析所有 A/AAAA 地址（不做公网校验，校验由 validate_destination 统一执行）。

    分离 resolution 与 validation 的原因：测试注入 fake resolver 时，
    IP 校验仍必须在 ``validate_destination`` 中发生，否则 SSRF 防护被绕过。
    """

    try:
        addresses = {
            row[4][0]
            for row in socket.getaddrinfo(
                host,
                443,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
        }
    except socket.gaierror as exc:
        raise ResourcePolicyViolation(
            f"Resource host DNS 解析失败：{host}"
        ) from exc
    if not addresses:
        raise ResourcePolicyViolation(
            "host 没有可用 A/AAAA address"
        )
    return tuple(sorted(addresses))


def validate_public_ips(
    ips: tuple[str, ...],
) -> tuple[str, ...]:
    """校验所有解析地址均为公网地址。

    ``is_global=False`` 覆盖 private/loopback/link-local/reserved/unspecified，
    含 IPv4-mapped IPv6 private address。``is_multicast`` 在部分 Python 版本
    不被 ``is_global`` 包含，需显式拒绝。任一非公网就拒绝整个 host。
    """

    for raw in ips:
        try:
            address = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise ResourcePolicyViolation(
                f"Resource host 解析到非 IP 地址：{raw}"
            ) from exc
        if not address.is_global or address.is_multicast:
            raise ResourcePolicyViolation(
                f"Resource host 解析到非公网地址：{address}"
            )
    return ips


def validate_destination(
    raw_url: str,
    *,
    allowed_hosts: tuple[str, ...],
    resolver=resolve_public_ips,
) -> ValidatedDestination:
    """规范化 URL 并校验 host allowlist + 公网 IP。

    IP 校验在 ``validate_destination`` 中执行（而非 resolver 内部），
    确保测试注入 fake resolver 时 SSRF 防护不被绕过。
    """

    canonical = canonicalize_url(raw_url)
    host = (urlsplit(canonical).hostname or "").lower()
    if not host:
        raise ResourcePolicyViolation(
            "Resource URL 缺少 host"
        )
    if not host_allowed(host, allowed_hosts):
        raise ResourcePolicyViolation(
            f"Resource host 不在 allowlist：{host}"
        )
    resolved_ips = resolver(host)
    if not resolved_ips:
        raise ResourcePolicyViolation(
            "host 没有可用 A/AAAA address"
        )
    return ValidatedDestination(
        canonical_url=canonical,
        host=host,
        resolved_ips=validate_public_ips(
            resolved_ips
        ),
    )
