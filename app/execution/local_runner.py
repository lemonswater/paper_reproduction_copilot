from app.execution.base import ExecutionRunner


class LocalRunner(ExecutionRunner):
    """直接使用 Agent 当前宿主机环境执行，主要用于兼容和测试。"""

    def build_host_command(self, program: str, args: list[str]) -> list[str]:
        return [program, *args]