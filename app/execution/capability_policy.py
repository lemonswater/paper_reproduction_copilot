from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.execution.environment import is_sensitive_env_name
from app.schemas import (
    ActionCapabilityRequest,
    CapabilityDecision,
    ExecutableAction,
    ExecutionProfile,
    PolicyViolation,
    ResourceBudget,
    ResourceBudgetOverride,
)
from app.tools.action_tools import compute_action_hash

READ_ONLY_PROGRAMS = {"echo", "pwd", "ls", "which"}
DYNAMIC_CODE_FLAGS = {
    "python": {"-c"},
    "python3": {"-c"},
    "bash": {"-c"},
    "sh": {"-c"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _within(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _violation(
    code: str,
    field: str,
    message: str,
) -> PolicyViolation:
    return PolicyViolation(
        code=code,
        field=field,
        message=message,
    )


def _merge_effective_budget(
    *,
    profile_budget: ResourceBudget,
    action_timeout_seconds: int,
    override: ResourceBudgetOverride | None,
) -> tuple[ResourceBudget, list[PolicyViolation]]:
    """Action 的任何非空预算都只能小于等于 profile 上限。"""

    violations: list[PolicyViolation] = []
    material = profile_budget.model_dump()

    if action_timeout_seconds > profile_budget.max_wall_time_seconds:
        violations.append(
            _violation(
                "WALL_TIME_EXCEEDS_PROFILE",
                "timeout_seconds",
                "Action timeout 超过 profile wall-time budget",
            )
        )
    else:
        material["max_wall_time_seconds"] = float(
            action_timeout_seconds
        )

    if override is None:
        return ResourceBudget.model_validate(material), violations

    requested = override.model_dump(exclude_none=True)
    for field, value in requested.items():
        profile_value = getattr(profile_budget, field)

        # Profile 为 None 表示没有设置这一项上限，Action 可以主动收紧。
        if profile_value is not None and value > profile_value:
            violations.append(
                _violation(
                    "RESOURCE_BUDGET_EXPANSION",
                    f"resource_budget.{field}",
                    f"Action 请求 {value}，超过 profile 上限 "
                    f"{profile_value}",
                )
            )
            continue

        material[field] = value

    material["max_wall_time_seconds"] = min(
        float(material["max_wall_time_seconds"]),
        float(action_timeout_seconds),
    )
    return ResourceBudget.model_validate(material), violations


def evaluate_action_capabilities(
    *,
    raw_action: dict,
    profile: ExecutionProfile,
) -> CapabilityDecision:
    """
    确定性检查 Action 的全部声明能力。

    该函数不调用 LLM、不执行程序、不访问网络，也不修改 Action。
    """

    action = ExecutableAction.model_validate(raw_action)
    action_hash = compute_action_hash(action.model_dump())
    violations: list[PolicyViolation] = []

    workspace_root = Path(profile.workspace_root).resolve()
    writable_roots = [
        Path(path).resolve()
        for path in profile.writable_roots
    ]

    cwd = Path(action.cwd).expanduser().resolve()
    if not _within(cwd, [workspace_root]):
        violations.append(
            _violation(
                "CWD_OUTSIDE_WORKSPACE",
                "cwd",
                f"cwd 位于 profile workspace 之外：{cwd}",
            )
        )

    # Action program 必须是 basename。Conda wrapper 由 Runner 构造。
    program = action.program.strip()
    if Path(program).name != program:
        violations.append(
            _violation(
                "ABSOLUTE_PROGRAM_NOT_ALLOWED",
                "program",
                "Action program 必须是 basename",
            )
        )
    elif program not in set(profile.allowed_programs):
        violations.append(
            _violation(
                "PROGRAM_NOT_ALLOWED",
                "program",
                f"profile 未允许程序：{program}",
            )
        )

    for index, arg in enumerate(action.args):
        for marker in profile.blocked_arg_markers:
            if marker and marker in arg:
                violations.append(
                    _violation(
                        "BLOCKED_ARGUMENT_MARKER",
                        f"args.{index}",
                        "参数包含 profile 阻断的控制字符",
                    )
                )

    blocked_flags = DYNAMIC_CODE_FLAGS.get(program, set())
    if blocked_flags.intersection(action.args):
        violations.append(
            _violation(
                "DYNAMIC_CODE_FLAG_BLOCKED",
                "args",
                f"不允许通过 {program} 动态传入代码",
            )
        )

    normalized_writable_paths: list[str] = []
    for raw_path in action.writable_paths:
        path = Path(raw_path).expanduser().resolve()
        normalized_writable_paths.append(str(path))
        if not _within(path, writable_roots):
            violations.append(
                _violation(
                    "WRITABLE_PATH_NOT_ALLOWED",
                    "writable_paths",
                    f"可写路径不在 profile writable_roots：{path}",
                )
            )

    if (
        action.network_access == "outbound"
        and profile.network_policy != "allow"
    ):
        violations.append(
            _violation(
                "NETWORK_NOT_ALLOWED",
                "network_access",
                "Action 请求外网，但 profile network_policy=deny",
            )
        )

    for key in action.env_overrides:
        if is_sensitive_env_name(key):
            violations.append(
                _violation(
                    "SENSITIVE_ENV_NOT_ALLOWED",
                    "env_overrides",
                    f"Action 禁止注入 secret 环境变量：{key}",
                )
            )
        elif key not in profile.allowed_action_env_keys:
            violations.append(
                _violation(
                    "ACTION_ENV_NOT_ALLOWED",
                    "env_overrides",
                    f"profile 未允许 Action 环境变量：{key}",
                )
            )

    effective_budget, budget_violations = _merge_effective_budget(
        profile_budget=profile.budget,
        action_timeout_seconds=action.timeout_seconds,
        override=action.resource_budget,
    )
    
    if (
        effective_budget.max_gpu_memory_bytes is not None
        and profile.backend in {"local", "conda"}
    ):
        violations.append(
            _violation(
                "GPU_BUDGET_UNSUPPORTED",
                "resource_budget.max_gpu_memory_bytes",
                "当前 local/conda runner 没有可靠 GPU memory enforcer",
            )
        )

    violations.extend(budget_violations)

    request = ActionCapabilityRequest(
        network_access=action.network_access,
        writable_paths=normalized_writable_paths,
        env_keys=sorted(action.env_overrides),
    )

    if violations:
        risk_level = "blocked"
        requires_approval = False
        reason = "Action capability policy 拒绝执行"
    elif (
        action.network_access == "outbound"
        or action.env_overrides
        or program not in READ_ONLY_PROGRAMS
        or normalized_writable_paths
    ):
        risk_level = (
            "high"
            if action.network_access == "outbound"
            else "medium"
        )
        requires_approval = True
        reason = "Action 包含执行、写入、环境或网络能力"
    else:
        risk_level = "low"
        requires_approval = False
        reason = "Action 只使用允许的只读能力"

    return CapabilityDecision(
        decision_id=f"cap_{uuid4().hex[:12]}",
        action_id=action.action_id,
        action_hash=action_hash,
        allowed=not violations,
        requires_approval=requires_approval,
        risk_level=risk_level,
        reason=reason,
        request=request,
        violations=violations,
        effective_budget=effective_budget,
        evaluated_at=utc_now(),
    )