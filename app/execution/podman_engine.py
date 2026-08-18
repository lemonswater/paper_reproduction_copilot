from __future__ import annotations

"""Phase 27 rootless Podman CLI adapter。

所有 token 由 ``container_plan.build_podman_create_tokens`` 确定性构造，
本模块只负责将 token 列表安全地传递给 Podman CLI。

正式接入时应将 ``start_attach`` 的 stdout/stderr 重定向到现有 bounded log
sink，而不是无限保留在内存。
"""


import json
import subprocess

from app.execution.container_engine import RuntimeProbe
from app.execution.container_errors import ContainerRuntimeError
from app.execution.container_schemas import ContainerInspect


class PodmanEngine:
    """``ContainerEngine`` Protocol 的 rootless Podman 实现。"""

    def __init__(self, executable: str = "podman"):
        self.executable = executable

    def _run(
        self,
        *args: str,
        timeout: float = 30.0,
    ) -> subprocess.CompletedProcess[str]:
        # shell=False 且参数逐 token 传入，避免 shell 展开。
        completed = subprocess.run(
            [self.executable, *args],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            # 正式代码应经过现有 sanitize_error_message 再写日志。
            detail = completed.stderr.strip()[-2000:]
            raise ContainerRuntimeError(
                f"podman {' '.join(args[:2])} failed: {detail}"
            )
        return completed

    def probe(self) -> RuntimeProbe:
        info = json.loads(
            self._run("info", "--format", "json").stdout
        )
        version = json.loads(
            self._run("version", "--format", "json").stdout
        )
        return RuntimeProbe(
            runtime="podman",
            version=str(
                version.get("Client", {}).get(
                    "Version", "unknown"
                )
            ),
            rootless=bool(
                info.get("host", {})
                .get("security", {})
                .get("rootless")
            ),
            cgroup_version=str(
                info.get("host", {}).get(
                    "cgroupVersion", "unknown"
                )
            ),
        )

    def image_exists(self, image_ref: str) -> bool:
        completed = subprocess.run(
            [self.executable, "image", "exists", image_ref],
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        return completed.returncode == 0

    def create(self, tokens: list[str]) -> str:
        container_id = self._run(
            "create", *tokens, timeout=60
        ).stdout.strip()
        if len(container_id) < 12:
            raise ContainerRuntimeError(
                "podman create 未返回有效 container ID"
            )
        return container_id

    def start_attach(self, container_id: str) -> int:
        completed = subprocess.run(
            [self.executable, "start", "--attach", container_id],
            text=False,
            check=False,
        )
        return completed.returncode

    def inspect(self, container_id: str) -> ContainerInspect:
        rows = json.loads(
            self._run("inspect", container_id).stdout
        )
        if len(rows) != 1:
            raise ContainerRuntimeError(
                "podman inspect 返回数量异常"
            )
        row = rows[0]
        state = row.get("State", {})
        config = row.get("Config", {})
        image_digest = str(
            row.get("ImageDigest") or row.get("ImageName") or ""
        )
        return ContainerInspect(
            container_id=str(row["Id"]),
            name=str(row["Name"]),
            running=bool(state.get("Running")),
            status=str(state.get("Status", "unknown")),
            exit_code=state.get("ExitCode"),
            oom_killed=bool(state.get("OOMKilled")),
            image_digest=image_digest,
            labels=dict(config.get("Labels") or {}),
        )

    def stop(
        self, container_id: str, timeout_seconds: float
    ) -> None:
        self._run(
            "stop",
            "--time",
            str(int(timeout_seconds)),
            container_id,
        )

    def remove(self, container_id: str) -> None:
        # 不使用 --force；调用者必须先 inspect 证明容器已停止。
        self._run("rm", container_id)
