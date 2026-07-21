from app.execution.base import ExecutionRunner


class CondaRunner(ExecutionRunner):
    """通过 `conda run -p` 在指定 Conda prefix 中执行。"""

    def build_host_command(self, program: str, args: list[str]) -> list[str]:
        conda_executable = self.profile.conda_executable
        conda_prefix = self.profile.conda_prefix

        if not conda_executable or not conda_prefix:
            raise ValueError("incomplete conda execution profile")

        return [
            conda_executable,
            "run",
            "--no-capture-output",
            "-p",
            conda_prefix,
            program,
            *args,
        ]