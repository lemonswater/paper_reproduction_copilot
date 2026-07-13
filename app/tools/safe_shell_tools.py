import shlex
from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["low", "medium", "high", "blocked"]

BLOCKED_TOKENS = {
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

@dataclass
class CommandRisk:
    command: str
    risk_level: RiskLevel
    reason: str
    blocked: bool

def assess_command_risk(command: str) -> CommandRisk:
    tokens = shlex.split(command)
    if not tokens:
        return CommandRisk(command, "blocked", "empty command", True)
    
    first = tokens[0]
    if first in BLOCKED_TOKENS:
        return CommandRisk(
            command=command,
            risk_level="blocked",
            reason=f"command starts with blocked token: {first}",
            blocked=True
        )
    
    if first in {"pip", "conda", "python"} and any(item in tokens for item in ["install", "-m"]):
        return CommandRisk(
            command=command,
            risk_level="high",
            reason="environment-changing command requires approval",
            blocked=False
        )
    
    if first in {"python", "torchrun", "accelerate"}:
        return CommandRisk(
            command=command,
            risk_level="medium",
            reason="training or script execution requires approval",
            blocked=False
        )

    return CommandRisk(
        command=command,
        risk_level="medium",
        reason="unknown command, review before execution",
        blocked=False
    )