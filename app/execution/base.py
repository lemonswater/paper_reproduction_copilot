import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from app.schemas import ExecutionProfile

def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value

def _combine_output(stdout: str, stderr: str) -> str:
    if stdout and stderr:
        return stdout + "\n\n[stderr]\n" + stderr
    if stderr:
        return "[stderr]\n" + stderr
    return stdout

class ExecutionRunner(ABC):
    def __init__(self, profile: ExecutionProfile):
        self.profile = profile

    @abstractmethod
    def build_host_command(self, program: str, args: list[str]) -> list[str]:
        """把目标命令转换成宿主机实际启动的 token 列表。"""
    def validate_cwd(self, cwd: str) -> Path:
        workspace_root = Path(self.profile.workspace_root).resolve()
        resolved_cwd = Path(cwd).resolve()

        if (
            resolved_cwd != workspace_root
            and workspace_root not in resolved_cwd.parents
        ):
            raise ValueError(f"cwd is outside execution workspace: {resolved_cwd}")

        return resolved_cwd

    def run_program(
        self,
        *,
        program: str,
        args: list[str],
        cwd: str,
        timeout_seconds: int,
        action_env: dict[str, str] | None = None
    ) -> dict[str, Any]:
        try:
            resolved_cwd = self.validate_cwd(cwd)
            host_command = self.build_host_command(program, args)

            env = os.environ.copy()
            env.update(self.profile.env)
            env.update(action_env or {})

            completed = subprocess.run(
                host_command,
                cwd=str(resolved_cwd),
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                shell=False,
                check=False,
            )

            stdout = completed.stdout or ""
            stderr = completed.stderr or ""

            return {
                "ok": completed.returncode == 0,
                "returncode": completed.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "combined_output": _combine_output(stdout, stderr),
                "timeout": False,
                "execution_profile_id": self.profile.profile_id,
                "execution_backend": self.profile.backend,
                "cwd": str(resolved_cwd),
            }
        except subprocess.TimeoutExpired as exc:
            stdout = _to_text(exc.stdout)
            stderr = _to_text(exc.stderr)
            combined = _combine_output(stdout, stderr)
            if not combined:
                combined = f"command timed out after {timeout_seconds} seconds"

            return {
                "ok": False,
                "returncode": None,
                "stdout": stdout,
                "stderr": stderr or combined,
                "combined_output": combined,
                "timeout": True,
                "execution_profile_id": self.profile.profile_id,
                "execution_backend": self.profile.backend,
            }

        except (FileNotFoundError, OSError, ValueError) as exc:
            message = str(exc)
            return {
                "ok": False,
                "returncode": None,
                "stdout": "",
                "stderr": message,
                "combined_output": message,
                "timeout": False,
                "execution_profile_id": self.profile.profile_id,
                "execution_backend": self.profile.backend,
            }

    def run(self, action: dict[str, Any]) -> dict[str, Any]:
        """执行经过 action builder 和审批链生成的正式动作。"""

        return self.run_program(
            program=str(action.get("program") or ""),
            args=list(action.get("args") or []),
            cwd=str(action.get("cwd") or self.profile.workspace_root),
            timeout_seconds=int(action.get("timeout_seconds", 300)),
            action_env=dict(action.get("env_allowlist") or {}),
        )

    def probe(
        self,
        *,
        program: str,
        args: list[str],
        cwd: str,
        timeout_seconds: int = 15,
    ) -> dict[str, Any]:
        """preflight 使用的短时探测，同样走目标执行环境。"""

        return self.run_program(
            program=program,
            args=args,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )

    def which(self, program: str, cwd: str) -> str | None:
        """在目标环境中解析程序，而不是读取 Agent 自己的 PATH。"""

        script = (
            "import shutil, sys; "
            "resolved = shutil.which(sys.argv[1]); "
            "print(resolved or '')"
        )
        result = self.probe(
            program="python",
            args=["-c", script, program],
            cwd=cwd,
        )

        if not result["ok"]:
            return None

        resolved = result["stdout"].strip()
        return resolved or None
    

