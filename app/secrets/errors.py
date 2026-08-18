from __future__ import annotations


class SecretError(RuntimeError):
    """Phase 41 Secret 子系统的稳定基类。"""


class SecretConfigurationError(SecretError):
    """Vault 路径、Master Key 或权限配置不安全。"""


class SecretNotFoundError(SecretError):
    """指定名称或版本不存在。"""


class SecretInactiveError(SecretError):
    """Secret 已轮换、撤销或删除，旧引用不能继续使用。"""


class SecretUseDeniedError(SecretError):
    """Secret 没有授权给当前用途。"""


class SecretIntegrityError(SecretError):
    """密文、Envelope、Fingerprint 或 Reference 身份不一致。"""


class SecretLeakDetectedError(SecretError):
    """持久化边界检测到已知 Secret 明文。"""
