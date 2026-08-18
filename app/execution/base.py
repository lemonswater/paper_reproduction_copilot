from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.execution.capability_policy import (
    evaluate_action_capabilities,
)
from app.execution.environment import build_minimal_environment
from app.execution.process_supervisor import (
    ProcessSupervisor,
    SupervisedExecutionRequest,
)
from app.schemas import (
    ExecutableAction,
    ExecutionProfile,
)
from app.secrets.service import SecretService
from app.workspace.schemas import WorkspaceBinding


@dataclass(frozen=True)
class ExecutionRuntimeContext:
    """携带本次 Workspace 身份的执行上下文。

    OCI Runner 需要 ``WorkspaceBinding.assignment_token`` 的 hash
    作为容器 ownership label。原始 token 不能写入日志、label 或 Artifact。

    local/conda Runner 忽略此参数。
    """

    job_id: str
    run_id: str
    workspace_binding: WorkspaceBinding

    @property
    def ownership_token_hash(self) -> str:
        import hashlib

        return hashlib.sha256(
            self.workspace_binding.assignment_token.encode(
                "utf-8"
            )
        ).hexdigest()


class ExecutionRunner(ABC):
    def __init__(
        self,
        profile: ExecutionProfile,
        *,
        secret_service: SecretService | None = None,
    ):
        self.profile = profile
        self.secret_service = secret_service
        self.supervisor = ProcessSupervisor()

    @abstractmethod
    def build_host_command(
        self,
        program: str,
        args: list[str],
    ) -> list[str]:
        """把目标命令转换成宿主机实际启动的 token 列表。"""

    def validate_cwd(self, cwd: str) -> Path:
        workspace_root = Path(
            self.profile.workspace_root
        ).resolve()
        resolved_cwd = Path(cwd).expanduser().resolve()
        if (
            resolved_cwd != workspace_root
            and workspace_root not in resolved_cwd.parents
        ):
            raise ValueError(
                f"cwd 位于执行工作区之外：{resolved_cwd}"
            )
        if not resolved_cwd.is_dir():
            raise FileNotFoundError(
                f"执行 cwd 不存在：{resolved_cwd}"
            )
        return resolved_cwd

    def run(
        self,
        action: dict[str, Any],
        *,
        run_dir: str,
        stage: str,
        runtime_context: ExecutionRuntimeContext | None = None,
    ) -> dict[str, Any]:
        """
        正式 Action 必须重新经过 capability policy。

        risk_check 是面向审批的第一次检查；这里是执行边界的 fail-closed
        第二次检查，防止 state 在审批后被错误修改。

        ``runtime_context`` 只供 OCI Runner 使用；local/conda 忽略它。
        """

        del runtime_context  # local/conda 不需要 WorkspaceBinding
        parsed = ExecutableAction.model_validate(action)
        resolved_cwd = self.validate_cwd(parsed.cwd)
        decision = evaluate_action_capabilities(
            raw_action=parsed.model_dump(),
            profile=self.profile,
        )
        if not decision.allowed:
            message = ", ".join(
                item.code for item in decision.violations
            )
            return {
                "ok": False,
                "returncode": None,
                "end_reason": "policy_denied",
                "stdout": "",
                "stderr": message,
                "combined_output": message,
                "timeout": False,
                "cancelled": False,
                "log_truncated": False,
                "execution_profile_id": self.profile.profile_id,
                "execution_backend": self.profile.backend,
                "cwd": str(resolved_cwd),
                "resource_usage": {},
            }

        execution_id = f"exec_{uuid4().hex[:16]}"
        env_result = build_minimal_environment(
            profile=self.profile,
            action=parsed,
            run_dir=run_dir,
            execution_id=execution_id,
            secret_service=self.secret_service,
        )
        host_command = self.build_host_command(
            parsed.program,
            parsed.args,
        )
        result = self.supervisor.execute(
            SupervisedExecutionRequest(
                host_command=host_command,
                cwd=resolved_cwd,
                env=env_result.env,
                run_dir=Path(run_dir).resolve(),
                action_id=parsed.action_id,
                stage=stage,
                profile_id=self.profile.profile_id,
                backend=self.profile.backend,
                budget=decision.effective_budget,
                execution_id=execution_id,
            ),
            inherited_env_keys=env_result.inherited_keys,
            profile_env_keys=env_result.profile_keys,
            action_env_keys=env_result.action_keys,
            secret_env_keys=env_result.secret_keys,
            redactor=env_result.redactor,
        )
        return result.model_dump()

    def probe(
        self,
        *,
        program: str,
        args: list[str],
        cwd: str,
        run_dir: str,
        stage: str,
        timeout_seconds: int = 15,
    ) -> dict[str, Any]:
        """
        受信任的内部探测也使用最小环境和 Supervisor。

        probe 不是 LLM Action，所以不走 DYNAMIC_CODE_FLAGS；但 program、cwd、
        profile 和预算都由 Agent 确定，不能接受用户提供的任意 shell 字符串。
        """

        resolved_cwd = self.validate_cwd(cwd)
        probe_action = ExecutableAction(
            action_id=f"probe_{uuid4().hex[:12]}",
            program=program,
            args=args,
            cwd=str(resolved_cwd),
            source="inferred",
            reason=f"internal probe: {stage}",
            timeout_seconds=timeout_seconds,
            env_overrides={},
            writable_paths=[],
            network_access="none",
            execution_profile_id=self.profile.profile_id,
            execution_profile_fingerprint="internal-probe",
        )
        execution_id = f"exec_{uuid4().hex[:16]}"
        env_result = build_minimal_environment(
            profile=self.profile,
            action=probe_action,
            run_dir=run_dir,
            execution_id=execution_id,
            secret_service=self.secret_service,
        )
        budget = self.profile.budget.model_copy(
            update={
                "max_wall_time_seconds": min(
                    float(timeout_seconds),
                    self.profile.budget.max_wall_time_seconds,
                ),
                "max_log_bytes_per_stream": min(
                    1024 * 1024,
                    self.profile.budget.max_log_bytes_per_stream,
                ),
                "max_preview_bytes": min(
                    64 * 1024,
                    self.profile.budget.max_preview_bytes,
                ),
            }
        )
        result = self.supervisor.execute(
            SupervisedExecutionRequest(
                host_command=self.build_host_command(
                    program,
                    args,
                ),
                cwd=resolved_cwd,
                env=env_result.env,
                run_dir=Path(run_dir).resolve(),
                action_id=probe_action.action_id,
                stage=stage,
                profile_id=self.profile.profile_id,
                backend=self.profile.backend,
                budget=budget,
                execution_id=execution_id,
            ),
            inherited_env_keys=env_result.inherited_keys,
            profile_env_keys=env_result.profile_keys,
            action_env_keys=[],
            secret_env_keys=env_result.secret_keys,
            redactor=env_result.redactor,
        )
        return result.model_dump()

    def which(
        self,
        program: str,
        cwd: str,
        *,
        run_dir: str,
    ) -> tuple[str | None, dict[str, Any]]:
        """在目标环境中解析程序，并返回对应 probe result。"""

        script = (
            "import shutil, sys; "
            "resolved = shutil.which(sys.argv[1]); "
            "print(resolved or '')"
        )
        result = self.probe(
            program="python",
            args=["-c", script, program],
            cwd=cwd,
            run_dir=run_dir,
            stage="preflight_which",
            timeout_seconds=15,
        )
        if not result["ok"]:
            return None, result
        resolved = result["stdout"].strip()
        return resolved or None, result
