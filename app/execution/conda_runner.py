from __future__ import annotations

from pathlib import Path

from app.execution.base import ExecutionRunner


class CondaRunner(ExecutionRunner):
    """通过 conda run -p 执行，使用与 LocalRunner 相同的 Supervisor。"""

    def build_host_command(
        self,
        program: str,
        args: list[str],
    ) -> list[str]:
        conda_executable = self.profile.conda_executable
        conda_prefix = self.profile.conda_prefix
        if not conda_executable or not conda_prefix:
            raise ValueError("conda 执行环境配置不完整")

        executable_path = Path(conda_executable).resolve()
        prefix_path = Path(conda_prefix).resolve()
        if not executable_path.is_file():
            raise FileNotFoundError(
                f"conda executable 不存在：{executable_path}"
            )
        if not prefix_path.is_dir():
            raise FileNotFoundError(
                f"conda prefix 不存在：{prefix_path}"
            )

        return [
            str(executable_path),
            "run",
            "--no-capture-output",
            "-p",
            str(prefix_path),
            program,
            *args,
        ]