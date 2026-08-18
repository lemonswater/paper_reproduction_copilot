from __future__ import annotations

"""Phase 27 容器引擎端口。

业务层依赖此 Protocol；单元测试使用 FakeContainerEngine。

端口刻意不提供 ``run(raw_flags: str)``，否则调用者仍可绕过策略拼接
``--privileged``。所有 Podman token 必须由 ``container_plan.py`` 确定性构造。
"""


from dataclasses import dataclass
from typing import Protocol

from app.execution.container_schemas import ContainerInspect


@dataclass(frozen=True)
class RuntimeProbe:
    """rootless Podman + cgroup v2 探测结果。"""

    runtime: str
    version: str
    rootless: bool
    cgroup_version: str


class ContainerEngine(Protocol):
    """业务层依赖端口；单元测试使用 FakeContainerEngine。"""

    def probe(self) -> RuntimeProbe:
        """检测 runtime、rootless 模式和 cgroup 版本。"""
        ...

    def image_exists(self, image_ref: str) -> bool:
        """检查 digest-pinned image 是否已存在于本机。"""
        ...

    def create(self, tokens: list[str]) -> str:
        """返回完整 container ID；此方法不能启动容器。"""
        ...

    def start_attach(self, container_id: str) -> int:
        """阻塞等待 attach client，返回 CLI exit code，不代表容器 exit code。"""
        ...

    def inspect(self, container_id: str) -> ContainerInspect:
        """返回容器当前状态的结构化投影。"""
        ...

    def stop(self, container_id: str, timeout_seconds: float) -> None:
        """按精确 container ID 停止容器。"""
        ...

    def remove(self, container_id: str) -> None:
        """移除已停止的容器；不使用 --force。"""
        ...
