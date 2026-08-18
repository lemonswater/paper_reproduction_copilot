"""Phase 27 单元测试使用的 FakeContainerEngine。

不访问真实 Podman；所有容器状态保存在内存中。
"""

from __future__ import annotations

from app.execution.container_engine import RuntimeProbe
from app.execution.container_errors import ContainerRuntimeError
from app.execution.container_schemas import ContainerInspect


class FakeContainerEngine:
    """内存容器引擎，用于单元测试。

    通过设置 ``inspect_result``、``start_attach_code`` 和
    ``create_container_id`` 控制返回值。
    """

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.create_container_id: str = "a" * 64
        self.start_attach_code: int = 0
        self.inspect_result: ContainerInspect | None = None
        self._stopped: set[str] = set()
        self._removed: set[str] = set()
        self._image_exists: bool = True
        self._probe: RuntimeProbe = RuntimeProbe(
            runtime="podman",
            version="5.0.0-fake",
            rootless=True,
            cgroup_version="v2",
        )
        self.inspect_should_raise: bool = False

    def set_image_exists(self, value: bool) -> None:
        self._image_exists = value

    def set_probe(
        self,
        *,
        rootless: bool = True,
        cgroup_version: str = "v2",
    ) -> None:
        self._probe = RuntimeProbe(
            runtime="podman",
            version="5.0.0-fake",
            rootless=rootless,
            cgroup_version=cgroup_version,
        )

    def probe(self) -> RuntimeProbe:
        self.calls.append(("probe",))
        return self._probe

    def image_exists(self, image_ref: str) -> bool:
        self.calls.append(("image_exists", image_ref))
        return self._image_exists

    def create(self, tokens: list[str]) -> str:
        self.calls.append(("create", list(tokens)))
        return self.create_container_id

    def start_attach(self, container_id: str) -> int:
        self.calls.append(("start_attach", container_id))
        return self.start_attach_code

    def inspect(self, container_id: str) -> ContainerInspect:
        self.calls.append(("inspect", container_id))
        if self.inspect_should_raise:
            raise ContainerRuntimeError(
                "fake inspect failed"
            )
        if self.inspect_result is None:
            raise ContainerRuntimeError(
                "inspect_result 未设置"
            )
        return self.inspect_result

    def stop(
        self, container_id: str, timeout_seconds: float
    ) -> None:
        self.calls.append(
            ("stop", container_id, timeout_seconds)
        )
        self._stopped.add(container_id)

    def remove(self, container_id: str) -> None:
        self.calls.append(("remove", container_id))
        self._removed.add(container_id)

    def was_stopped(self, container_id: str) -> bool:
        return container_id in self._stopped

    def was_removed(self, container_id: str) -> bool:
        return container_id in self._removed
