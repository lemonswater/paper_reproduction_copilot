from __future__ import annotations

"""Phase 27 OCI Runner。

不调用 base ``ProcessSupervisor`` 执行论文命令；容器 supervisor 接管生命周期。
容器 ownership 使用当前 ``WorkspaceBinding.assignment_token`` 的 hash；
数据库终态仍由 Job Worker 的 claim token fencing 保护。
"""


from pathlib import Path
from typing import Any

from app.config import settings
from app.execution.base import (
    ExecutionRunner,
    ExecutionRuntimeContext,
)
from app.execution.capability_policy import (
    evaluate_action_capabilities,
)
from app.execution.container_plan import build_container_plan
from app.execution.container_records import record_path
from app.execution.container_supervisor import (
    ContainerSupervisor,
)
from app.schemas import (
    ExecutableAction,
    ExecutionProfile,
    ExecutionResult,
)
from app.secrets.service import SecretService


class OciRunner(ExecutionRunner):
    """OCI 容器执行后端。

    完全重写 ``run()``，不使用宿主机 ``ProcessSupervisor``。
    """

    backend = "oci"

    def __init__(
        self,
        profile: ExecutionProfile,
        supervisor: ContainerSupervisor,
        *,
        secret_service: SecretService | None = None,
    ):
        # 不调用 base ProcessSupervisor 执行论文命令；容器 supervisor 接管生命周期。
        super().__init__(profile, secret_service=secret_service)
        self.supervisor = supervisor

    def build_host_command(
        self, program: str, args: list[str]
    ) -> list[str]:
        raise RuntimeError(
            "OCI Runner 不通过 host command 路径执行论文程序"
        )

    def run(
        self,
        action: dict[str, Any],
        *,
        run_dir: str,
        stage: str,
        runtime_context: ExecutionRuntimeContext | None = None,
    ) -> dict[str, Any]:
        if runtime_context is None:
            raise ValueError(
                "OCI execution 缺少 current WorkspaceBinding"
            )

        parsed = ExecutableAction.model_validate(action)
        decision = evaluate_action_capabilities(
            raw_action=parsed.model_dump(),
            profile=self.profile,
        )
        if not decision.allowed:
            message = ", ".join(
                item.code for item in decision.violations
            )
            return ExecutionResult(
                ok=False,
                returncode=None,
                end_reason="policy_denied",
                stderr=message,
                combined_output=message,
                execution_profile_id=self.profile.profile_id,
                execution_backend="oci",
                cwd=parsed.cwd,
            ).model_dump()

        binding = runtime_context.workspace_binding
        if (
            Path(run_dir).resolve()
            != Path(binding.run_dir).resolve()
        ):
            raise ValueError(
                "run_dir 与 current WorkspaceBinding 不一致"
            )

        plan = build_container_plan(
            action=parsed,
            profile=self.profile,
            binding=binding,
            job_id=runtime_context.job_id,
            run_id=runtime_context.run_id,
        )
        record = self.supervisor.execute(
            plan=plan,
            run_dir=Path(binding.run_dir),
        )

        end_reason = (
            "memory_limit" if record.oom_killed else "exited"
        )
        result = ExecutionResult(
            ok=(
                record.exit_code == 0
                and not record.oom_killed
            ),
            returncode=record.exit_code,
            end_reason=end_reason,
            stdout="",
            stderr="",
            combined_output="",
            execution_id=(
                f"container_{record.container_id[:16]}"
            ),
            execution_profile_id=self.profile.profile_id,
            execution_backend="oci",
            cwd=parsed.cwd,
            process_record_path=str(
                record_path(Path(binding.run_dir))
            ),
            # ContainerSupervisor 接入 bounded log sink 后在这里返回真实路径。
            combined_log_path=None,
        )

        # 成功/失败后按配置决定是否自动 remove。
        should_remove = (
            (record.exit_code == 0 and not record.oom_killed)
            and settings.container_remove_succeeded
        ) or (
            (record.exit_code != 0 or record.oom_killed)
            and settings.container_remove_failed
        )
        if should_remove and record.status == "exited":
            self.supervisor.stop_and_remove(
                record=record,
                run_dir=Path(binding.run_dir),
            )

        return result.model_dump()
