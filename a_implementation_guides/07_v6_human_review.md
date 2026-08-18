# 07. V6 Human-in-the-loop 安全审批

## 目标

在写文件、修改配置、执行命令前暂停，等待用户确认。

本项目的原则：

```text
只读分析工具：默认允许
写 outputs 文件：允许
修改用户 repo：必须审批
执行命令：必须审批
危险命令：禁止
```

这一阶段先做 proposal-only，不急着真正执行命令。

## 本阶段要新增的文件

```text
app/tools/safe_shell_tools.py
app/nodes/risk_check_node.py
app/nodes/human_review_node.py
```

## app/tools/safe_shell_tools.py

```python
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
    "git",
}


@dataclass
class CommandRisk:
    command: str
    risk_level: RiskLevel
    reason: str
    blocked: bool


# 评估一条命令的风险等级、原因以及是否应直接阻断。
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
            blocked=True,
        )

    if first in {"pip", "conda", "python"} and any(item in tokens for item in ["install", "-m"]):
        return CommandRisk(
            command=command,
            risk_level="high",
            reason="environment-changing command requires approval",
            blocked=False,
        )

    if first in {"python", "torchrun", "accelerate"}:
        return CommandRisk(
            command=command,
            risk_level="medium",
            reason="training or script execution requires approval",
            blocked=False,
        )

    return CommandRisk(
        command=command,
        risk_level="medium",
        reason="unknown command, review before execution",
        blocked=False,
    )
```

## app/nodes/risk_check_node.py

```python
from app.tools.safe_shell_tools import assess_command_risk


# 根据 pending_action 生成执行前的风险判断结果。
def risk_check_node(state: dict) -> dict:
    pending_action = state.get("pending_action")
    if not pending_action:
        return {
            "requires_approval": False,
            "pending_action": None,
        }

    action_type = pending_action.get("type")
    if action_type == "run_command":
        risk = assess_command_risk(pending_action["command"])
        pending_action["risk"] = {
            "level": risk.risk_level,
            "reason": risk.reason,
            "blocked": risk.blocked,
        }
        return {
            "pending_action": pending_action,
            "requires_approval": not risk.blocked,
            "error": risk.reason if risk.blocked else None,
        }

    if action_type in {"modify_config", "write_repo_file"}:
        pending_action["risk"] = {
            "level": "high",
            "reason": "action modifies user repository",
            "blocked": False,
        }
        return {
            "pending_action": pending_action,
            "requires_approval": True,
        }

    pending_action["risk"] = {
        "level": "medium",
        "reason": "unknown action type",
        "blocked": False,
    }
    return {
        "pending_action": pending_action,
        "requires_approval": True,
    }
```

## app/nodes/human_review_node.py

LangGraph 的 `interrupt()` 会暂停图执行，等待外部输入。注意：调用 `interrupt()` 的节点被恢复时会从节点开头重新执行，所以 interrupt 前面的副作用必须是幂等的。本节点只构造 payload，不写文件、不执行命令。

```python
from langgraph.types import interrupt


# 通过 interrupt 暂停图执行，并等待人工返回审批结果。
def human_review_node(state: dict) -> dict:
    if not state.get("requires_approval"):
        return {"user_approval": "not_required"}

    pending_action = state.get("pending_action")
    if not pending_action:
        return {"user_approval": "missing_action"}

    payload = {
        "message": "请确认是否允许执行该操作",
        "action": pending_action,
        "allowed_responses": ["approved", "rejected", "revise"],
    }

    response = interrupt(payload)

    if isinstance(response, dict):
        decision = response.get("decision", "rejected")
        feedback = response.get("feedback")
    else:
        decision = str(response)
        feedback = None

    return {
        "user_approval": decision,
        "human_feedback": feedback,
    }
```

## 在 graph 中接入

V6 阶段可以把 `experiment_plan_node` 后的 router 改成：

```python
from app.nodes.human_review_node import human_review_node
from app.nodes.risk_check_node import risk_check_node


# 根据当前 state 决定是否进入风险检查或日志调试分支。
def route_after_plan(state: ReproductionState) -> str:
    if state.get("pending_action"):
        return "risk_check"
    if state.get("log_path"):
        return "log_debug"
    return END


# 根据风险检查结果决定是否需要进入人工审批节点。
def route_after_risk_check(state: ReproductionState) -> str:
    if state.get("requires_approval"):
        return "human_review"
    return END


builder.add_node("risk_check", risk_check_node)
builder.add_node("human_review", human_review_node)
builder.add_conditional_edges("experiment_plan", route_after_plan)
builder.add_conditional_edges("risk_check", route_after_risk_check)
builder.add_edge("human_review", END)
```

## CLI 恢复示例

初次运行可能返回 `__interrupt__`：

```python
from langgraph.types import Command


# 用外部给定的审批结果恢复此前被 interrupt 的图执行。
@app.command()
def resume_review(thread_id: str, decision: str = "approved", feedback: str | None = None):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        Command(resume={"decision": decision, "feedback": feedback}),
        config=config,
    )
    print(result)
```

## 本阶段验收

构造一个 `pending_action`：

```python
{
    "type": "run_command",
    "command": "python train.py --config configs/base.yaml",
    "cwd": "/path/to/repo",
    "reason": "run baseline training"
}
```

期望：

- `risk_check_node` 标记为 medium 或 high。
- `human_review_node` 触发 interrupt。
- 使用同一个 `thread_id` 和 `Command(resume=...)` 可以继续。

## 面试讲法

```text
我没有给 Agent 任意 shell 权限，而是把行动分为只读、受限写和高风险执行。
只读工具默认可用；修改用户仓库和执行命令都必须进入 risk_check，
再由 LangGraph interrupt 暂停等待人工审批。
这样既保留 Agent 的自动化能力，也控制了副作用风险。
```

## 参考官方文档

- LangGraph interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts
