from app.execution.base import ExecutionRunner
from app.execution.conda_runner import CondaRunner
from app.execution.local_runner import LocalRunner
from app.schemas import ExecutionProfile


def build_execution_runner(profile: ExecutionProfile) -> ExecutionRunner:
    """根据受信任 profile 选择执行后端。"""

    if profile.backend == "local":
        return LocalRunner(profile)

    if profile.backend == "conda":
        return CondaRunner(profile)

    raise ValueError(f"unsupported execution backend: {profile.backend}")