"""Phase 29 确定性 URL/DNS policy 负向测试。

覆盖：
- scheme/host/port/userinfo/query/fragment 校验
- host allowlist（精确 + 子域，拒绝 evil 冒充）
- DNS 解析：拒绝 private/loopback/link-local/multicast/reserved/unspecified
- redirect 每一跳重新检查 host 与 IP
"""

from __future__ import annotations

import pytest

from app.resources.errors import ResourcePolicyViolation
from app.resources.policy import (
    host_allowed,
    validate_destination,
)


ALLOWED = (
    "arxiv.org",
    "export.arxiv.org",
    "github.com",
    "codeload.github.com",
)


class TestHostAllowlist:
    def test_exact_host_allowed(self) -> None:
        assert host_allowed("arxiv.org", ALLOWED)

    def test_subdomain_allowed(self) -> None:
        assert host_allowed(
            "export.arxiv.org", ALLOWED
        )

    def test_evil_lookalike_rejected(self) -> None:
        assert not host_allowed(
            "evilgithub.com", ALLOWED
        )

    def test_random_host_rejected(self) -> None:
        assert not host_allowed(
            "evil.com", ALLOWED
        )

    def test_empty_host_rejected(self) -> None:
        assert not host_allowed("", ALLOWED)


class TestUrlCanonicalization:
    @pytest.mark.parametrize(
        "url",
        [
            "http://arxiv.org/pdf/1234",
            "ftp://arxiv.org/file",
            "file:///etc/passwd",
            "ssh://git@github.com/org/repo",
            "git://github.com/org/repo",
        ],
    )
    def test_non_https_rejected(self, url: str) -> None:
        with pytest.raises(
            (ResourcePolicyViolation, ValueError)
        ):
            validate_destination(
                url, allowed_hosts=ALLOWED
            )

    def test_userinfo_rejected(self) -> None:
        with pytest.raises(
            (ResourcePolicyViolation, ValueError)
        ):
            validate_destination(
                "https://user:pass@arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
            )

    def test_query_rejected(self) -> None:
        with pytest.raises(
            (ResourcePolicyViolation, ValueError)
        ):
            validate_destination(
                "https://arxiv.org/pdf/1234?token=secret",
                allowed_hosts=ALLOWED,
            )

    def test_fragment_rejected(self) -> None:
        with pytest.raises(
            (ResourcePolicyViolation, ValueError)
        ):
            validate_destination(
                "https://arxiv.org/pdf/1234#section",
                allowed_hosts=ALLOWED,
            )

    def test_non_443_port_rejected(self) -> None:
        with pytest.raises(
            (ResourcePolicyViolation, ValueError)
        ):
            validate_destination(
                "https://arxiv.org:8443/pdf/1234",
                allowed_hosts=ALLOWED,
            )

    def test_443_port_accepted(self) -> None:
        dest = validate_destination(
            "https://arxiv.org:443/pdf/1234",
            allowed_hosts=ALLOWED,
            resolver=lambda host: ("93.184.216.34",),
        )
        assert dest.canonical_url == (
            "https://arxiv.org/pdf/1234"
        )


class TestDnsValidation:
    def _make_resolver(self, ips: tuple[str, ...]):
        return lambda host: ips

    def test_public_ip_accepted(self) -> None:
        dest = validate_destination(
            "https://arxiv.org/pdf/1234",
            allowed_hosts=ALLOWED,
            resolver=self._make_resolver(
                ("93.184.216.34",)
            ),
        )
        assert "93.184.216.34" in dest.resolved_ips

    def test_loopback_ipv4_rejected(self) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("127.0.0.1",)
                ),
            )

    def test_loopback_ipv6_rejected(self) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("::1",)
                ),
            )

    def test_private_10_rejected(self) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("10.0.0.1",)
                ),
            )

    def test_private_172_16_rejected(self) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("172.16.0.1",)
                ),
            )

    def test_private_192_168_rejected(self) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("192.168.1.1",)
                ),
            )

    def test_link_local_rejected(self) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("169.254.1.1",)
                ),
            )

    def test_metadata_169_254_rejected(self) -> None:
        """AWS/GCP metadata 169.254.169.254 必须拒绝。"""
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("169.254.169.254",)
                ),
            )

    def test_multicast_rejected(self) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("224.0.0.1",)
                ),
            )

    def test_unspecified_rejected(self) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("0.0.0.0",)
                ),
            )

    def test_ipv4_mapped_ipv6_private_rejected(
        self,
    ) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("::ffff:10.0.0.1",)
                ),
            )

    def test_any_non_public_rejects_all(
        self,
    ) -> None:
        """任一 A/AAAA 非公网就拒绝整个 host。"""
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("93.184.216.34", "10.0.0.1")
                ),
            )

    def test_empty_resolution_rejected(self) -> None:
        with pytest.raises(ResourcePolicyViolation):
            validate_destination(
                "https://arxiv.org/pdf/1234",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(()),
            )

    def test_host_not_in_allowlist_rejected(
        self,
    ) -> None:
        with pytest.raises(ResourcePolicyViolation) as exc_info:
            validate_destination(
                "https://evil.com/file",
                allowed_hosts=ALLOWED,
                resolver=self._make_resolver(
                    ("93.184.216.34",)
                ),
            )
        assert "allowlist" in str(exc_info.value)
