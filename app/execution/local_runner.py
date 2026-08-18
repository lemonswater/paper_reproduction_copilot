from __future__ import annotations

from app.execution.base import ExecutionRunner


class LocalRunner(ExecutionRunner):
    """宿主机执行后端；监管和安全环境由基类统一提供。"""

    def build_host_command(
        self,
        program: str,
        args: list[str],
    ) -> list[str]:
        return [program, *args]