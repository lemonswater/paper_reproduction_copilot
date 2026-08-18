from __future__ import annotations

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
            reason="缺少可执行程序",
            blocked=True,
        )

    if program in BLOCKED_PROGRAMS:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="blocked",
            reason=f"程序已被安全策略阻止：{program}",
            blocked=True,
        )

    if program in LOW_RISK_PROGRAMS:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="low",
            reason="只读工具命令可以在无需人工审批的情况下运行",
            blocked=False,
        )
    
    if program in {"pip", "conda"} and "install" in args:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="high",
            reason="会修改环境的命令需要人工审批",
            blocked=False,
        )
    
    if program == "python" and "-m" in args:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="high",
            reason="执行 Python 模块需要明确的人工审批",
            blocked=False,
        )

    if program in {"python", "torchrun", "accelerate", "bash"}:
        return ActionRisk(
            program=program,
            args=args,
            risk_level="medium",
            reason="执行脚本或训练任务需要人工审批",
            blocked=False,
        )

    return ActionRisk(
        program=program,
        args=args,
        risk_level="medium",
        reason="未知的可执行程序，运行前需要人工审核",
        blocked=False,
    )
