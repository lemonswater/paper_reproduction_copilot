from __future__ import annotations

"""根据受信任 profile 选择执行后端。

OCI 后端需要 ``ContainerEngine``；工厂在首次调用时探测 rootless Podman，
探测成功后才实例化可用 runner。探测失败抛出
``ContainerRuntimeUnavailable``。
"""


from app.config import settings
from app.execution.base import ExecutionRunner
from app.execution.conda_runner import CondaRunner
from app.execution.container_engine import ContainerEngine
from app.execution.container_errors import (
    ContainerRuntimeUnavailable,
)
from app.execution.container_supervisor import (
    ContainerSupervisor,
)
from app.execution.local_runner import LocalRunner
from app.execution.oci_runner import OciRunner
from app.execution.podman_engine import PodmanEngine
from app.schemas import ExecutionProfile
from app.secrets.service import SecretService

# 模块级 probe 缓存，避免每次 action 都 fork podman info。
_probe_cache: dict[str, bool] = {}


def build_execution_runner(
    profile: ExecutionProfile,
    *,
    engine: ContainerEngine | None = None,
    secret_service: SecretService | None = None,
) -> ExecutionRunner:
    """根据受信任 profile 选择执行后端。

    ``engine`` 参数供单元测试注入 ``FakeContainerEngine``；
    生产路径自动构造 ``PodmanEngine`` 并探测。
    """

    if profile.backend == "local":
        return LocalRunner(
            profile, secret_service=secret_service
        )

    if profile.backend == "conda":
        return CondaRunner(
            profile, secret_service=secret_service
        )

    if profile.backend == "oci":
        if profile.oci is None:
            raise ContainerRuntimeUnavailable(
                "OCI profile 缺少 oci 配置"
            )

        if engine is None:
            engine = PodmanEngine(
                executable=settings.container_runtime
            )

        cache_key = (
            f"{settings.container_runtime}:"
            f"{profile.oci.image_ref}"
        )
        if not _probe_cache.get(cache_key):
            probe = engine.probe()
            if not probe.rootless:
                raise ContainerRuntimeUnavailable(
                    "strict OCI profile 要求 rootless Podman"
                )
            if probe.cgroup_version not in {"v2", "2"}:
                raise ContainerRuntimeUnavailable(
                    "strict OCI profile 要求 cgroup v2"
                )
            if not engine.image_exists(profile.oci.image_ref):
                raise ContainerRuntimeUnavailable(
                    "digest-pinned image 不在本机；"
                    "执行路径禁止自动 pull"
                )
            _probe_cache[cache_key] = True

        supervisor = ContainerSupervisor(engine=engine)
        return OciRunner(
            profile=profile,
            supervisor=supervisor,
            secret_service=secret_service,
        )

    raise ValueError(f"不支持的执行后端：{profile.backend}")


def reset_probe_cache() -> None:
    """测试辅助：清空 probe 缓存。"""

    _probe_cache.clear()
