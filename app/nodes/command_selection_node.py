from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from langgraph.types import interrupt
from rich import print

from app.command_selection import (
    apply_command_edits,
    compute_run_commands_hash,
    validate_command_selection_response,
)
from app.schemas import CommandSelectionRecord, CommandSelectionResponse
from app.tools.artifact_tools import (
    artifact_state_update,
    register_existing_artifact,
    resolve_artifact_path,
    write_json_artifact,
)
from app.tools.error_tools import stage_error_result


def _render_run_commands_for_terminal(run_commands: list[dict]) -> None:
    print("\n[bold cyan]可用的运行命令（run_commands）[/bold cyan]")
    for index, item in enumerate(run_commands):
        print(f"\n[yellow][{index}][/yellow] {item.get('command', '')}")
        print(f"  工作目录：{item.get('cwd', '')}")
        print(f"  来源：{item.get('source', '')}")
        print(f"  风险等级：{item.get('risk_level', '')}")
        print(f"  原因：{item.get('reason', '')}")


def build_command_selection_template(run_commands: list[dict]) -> dict:
    """生成可直接用于恢复 command selection 的预填 JSON。"""

    return {
        "run_commands_hash": compute_run_commands_hash(run_commands),
        "selected_index": 0,
        "edits": [
            {
                "index": index,
                "command": item.get("command", ""),
            }
            for index, item in enumerate(run_commands)
        ],
    }


def _write_command_selection_template(
    input_path: Path,
    run_commands: list[dict],
) -> None:
    template = build_command_selection_template(run_commands)
    input_path.write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ensure_command_selection_input_file(
    input_path: Path,
    run_commands: list[dict],
) -> tuple[str, Path | None]:
    """
    确保输入文件对应当前 run_commands。

    返回 ``(status, backup_path)``。status 为 current、created 或 refreshed；
    过期或无哈希的文件会先备份，再用当前命令列表重新生成。
    """

    input_path.parent.mkdir(parents=True, exist_ok=True)
    if not input_path.exists():
        _write_command_selection_template(input_path, run_commands)
        return "created", None

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        payload = {}

    expected_hash = compute_run_commands_hash(run_commands)
    if (
        isinstance(payload, dict)
        and payload.get("run_commands_hash") == expected_hash
    ):
        return "current", None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = input_path.with_name(
        f"{input_path.stem}.stale-{timestamp}{input_path.suffix}"
    )
    shutil.copy2(input_path, backup_path)
    _write_command_selection_template(input_path, run_commands)
    return "refreshed", backup_path

def _normalize_interrupt_response(
    response: object,
    expected_hash: str,
) -> CommandSelectionResponse:
    if isinstance(response, dict):
        return CommandSelectionResponse.model_validate(response)
    if isinstance(response, int):
        return CommandSelectionResponse(
            selected_index=response,
            edits=[],
            run_commands_hash=expected_hash,
        )
    if isinstance(response, str) and response.isdigit():
        return CommandSelectionResponse(
            selected_index=int(response),
            edits=[],
            run_commands_hash=expected_hash,
        )
    
    raise ValueError("无效的命令选择响应")

def command_selection_node(state: dict) -> dict:
    run_commands = state.get("run_commands", [])
    if not run_commands:
        return {
            "selected_run_command_index": None,
            "edited_run_commands": []
        }
    
    expected_hash = compute_run_commands_hash(run_commands)
    raw_input_path = state.get("command_selection_input_path")
    if not raw_input_path:
        return stage_error_result(
            state=state,
            stage="command_selection",
            code="COMMAND_SELECTION_INPUT_MISSING",
            category="agent",
            message="checkpoint 中缺少 command_selection_input_path",
            extra_update={
                "selected_run_command_index": None,
                "edited_run_commands": [],
            },
        )

    input_path = Path(raw_input_path)
    input_status = state.get("command_selection_input_status", "current")
    stale_backup_path = None

    _render_run_commands_for_terminal(run_commands)
    print(
        "\n[green]命令选择输入文件：[/green] "
        f"[bold]{input_path}[/bold]"
    )
    print("请编辑此文件，然后恢复当前 thread。")
    if input_status == "refreshed":
        print(
            "[yellow]过期的命令选择输入已备份到：[/yellow] "
            f"{stale_backup_path}"
        )

    payload = {
        "message": "请选择先执行哪个 run_command，并可选修改一个或多个 command",
        "run_commands": run_commands,
        "run_commands_hash": expected_hash,
        "input_path": str(input_path),
        "resume_example": {
            "run_commands_hash": expected_hash,
            "selected_index": 0,
            "edits": [
                {"index": 0, "command": "python train.py --dataset_path /data/demo"}
            ]
        }
    }

    response = interrupt(payload)
    parsed = _normalize_interrupt_response(
        response,
        expected_hash,
    )

    # 即使 HTTP 层已经校验，Graph 恢复后仍使用 checkpoint 中的真实
    # run_commands 再校验一次，防御 CLI、旧 checkpoint 和其他调用入口。
    parsed = validate_command_selection_response(
        run_commands=run_commands,
        response=parsed,
        expected_preview_hash=expected_hash,
    )
    effective_commands = apply_command_edits(
        run_commands,
        parsed.edits,
    )

    record = CommandSelectionRecord(
        selected_index=parsed.selected_index,
        edits=parsed.edits,
        original_count=len(run_commands),
        run_commands_hash=expected_hash,
        reviewed_at=datetime.now(timezone.utc).isoformat()
    )

    _record_path, record_artifact = write_json_artifact(
        state=state,
        relative_path="planning/command_selection_record.json",
        payload=record.model_dump(),
        producer_node="command_selection",
    )
    _effective_path, effective_artifact = write_json_artifact(
        state=state,
        relative_path="planning/effective_run_commands.json",
        payload=effective_commands,
        producer_node="command_selection",
    )

    return {
        "selected_run_command_index": parsed.selected_index,
        "edited_run_commands": effective_commands,
        "command_selection_record": record.model_dump(),

        # 新的选择或编辑会改变执行语义，不能继续复用旧 action、审批或结果。
        # action_builder 会根据本次 effective_commands 重新生成并计算哈希。
        "pending_action": None,
        "pending_action_hash": None,
        "requires_approval": False,
        "user_approval": None,
        "human_feedback": None,
        "approval_record": None,
        "preflight_report": None,
        "preflight_passed": False,
        "execution_result": {},
        "execution_log_path": None,
        "last_action_result": {},
        "final_status": None,
        "error": None,
        **artifact_state_update(
            state,
            [record_artifact, effective_artifact],
        ),
    }

def command_selection_prepare_node(state: dict) -> dict:
    """
    在 interrupt 节点之前落盘并登记命令选择模板。

    这样 checkpoint 到达 command_selection 时，模板已经是当前 run 的
    正式 Artifact。
    """

    run_commands = state.get("run_commands", [])
    if not run_commands:
        return {
            "command_selection_input_path": None,
            "selected_run_command_index": None,
            "edited_run_commands": [],
        }

    input_path = resolve_artifact_path(
        state,
        "planning/command_selection_input.json",
    )
    status, stale_backup_path = ensure_command_selection_input_file(
        input_path,
        run_commands,
    )

    records = [
        register_existing_artifact(
            state=state,
            path=input_path,
            producer_node="command_selection_prepare",
            media_type="application/json",
        )
    ]
    if stale_backup_path is not None:
        records.append(
            register_existing_artifact(
                state=state,
                path=stale_backup_path,
                producer_node="command_selection_prepare",
                media_type="application/json",
            )
        )

    return {
        "command_selection_input_path": str(input_path),
        "command_selection_input_status": status,
        **artifact_state_update(state, records),
    }
