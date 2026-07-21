import shlex
from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["low", "medium", "high", "blocked"]

BLOCKED_PROGRAMS = {
    "rm",
    "sudo",
    "chmod",
    "chown",
    "mkfs",
    "dd",
    "shutdown",
    "reboot",
    "git"
}

LOW_RISK_PROGRAMS = {
    "echo",
    "pwd",
    "ls",
    "which",
}

@dataclass
class ActionRisk:
    program: str
    args: list[str]
    risk_level: RiskLevel
    reason: str
    blocked: bool

def assess_action_risk(action: dict) -> ActionRisk:
    program = action.get("program", "")
    args = action.get("args", [])
    if not program:
        return ActionRisk(
            program="",
            args=[],
            risk_level="blocked",
            reason="missing executable program",
            blocked=True,
        )

    if program in BLOCKED_PROGRAMS:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="blocked",
            reason=f"program is blocked: {program}",
            blocked=True,
        )

    if program in LOW_RISK_PROGRAMS:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="low",
            reason="read-only utility command can run without manual approval",
            blocked=False,
        )
    
    if program in {"pip", "conda"} and "install" in args:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="high",
            reason="environment-changing command requires approval",
            blocked=False,
        )
    
    if program == "python" and "-m" in args:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="high",
            reason="python module execution requires explicit approval",
            blocked=False,
        )

    if program in {"python", "torchrun", "accelerate", "bash"}:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="medium",
            reason="script or training execution requires approval",
            blocked=False,
        )

    return ActionRisk(
        program=program,
        args=args,
        risk_level="medium",
        reason="unknown executable, review before execution",
        blocked=False,
    )