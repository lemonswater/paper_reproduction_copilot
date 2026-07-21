from typing import Any
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.execution.registry import build_execution_runner

def _execution_failure(
    *,
    message: str,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """统一返回 executor 已经熟悉的失败结构。"""

    return {
        "ok": False,
        "returncode": None,
        "stdout": "",
        "stderr": message,
        "combined_output": message,
        "timeout": False,
        "execution_profile_id": profile_id,
    }

def run_action_safe(action: dict) -> dict[str, Any]:

    profile_id = action.get("execution_profile_id")
    if not profile_id:
        return _execution_failure(message="missing execution_profile_id")

    try:
        profile = get_execution_profile(profile_id)
        current_fingerprint = compute_execution_profile_fingerprint(profile)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return _execution_failure(
            message=str(exc),
            profile_id=profile_id
        )
    
    expect_fingerprint = action.get("execution_profile_fingerprint")
    if expect_fingerprint != current_fingerprint:
        return _execution_failure(
            message=(
                "execution profile changed after action creation; "
                "rebuild and re-approve the action"
            ),
            profile_id=profile_id
        )
    
    runner = build_execution_runner(profile)
    return runner.run(action)