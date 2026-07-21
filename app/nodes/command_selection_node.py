from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from langgraph.types import interrupt
from rich import print

from app.config import settings
from app.schemas import(
    CommandEdit,
    CommandSelectionRecord,
    CommandSelectionResponse
)

def _render_run_commands_for_terminal(run_commands: list[dict]) -> None:
    print("\n[bold cyan]Available run_commands[/bold cyan]")
    for index, item in enumerate(run_commands):
        print(f"\n[yellow][{index}][/yellow] {item.get('command', '')}")
        print(f"  cwd: {item.get('cwd', '')}")
        print(f"  source: {item.get('source', '')}")
        print(f"  risk_level: {item.get('risk_level', '')}")
        print(f"  reason: {item.get('reason', '')}")


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


def compute_run_commands_hash(run_commands: list[dict]) -> str:
    """计算与字典键顺序无关、但保留命令列表顺序的稳定哈希。"""

    canonical_json = json.dumps(
        run_commands,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


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


def _command_selection_input_path(state: dict) -> Path:
    """优先把输入模板放入当前 run，直接调用节点时回退到 outputs。"""

    run_dir = state.get("run_dir")
    if run_dir:
        return Path(run_dir) / "planning" / "command_selection_input.json"
    return settings.output_dir / "command_selection_input.json"


def _ensure_command_selection_input(
    state: dict,
    run_commands: list[dict],
) -> tuple[Path, str, Path | None]:
    """
    为本次 run 创建预填输入文件，但不覆盖用户已经修改过的文件。

    LangGraph 从 interrupt 恢复时会从节点开头重新执行，因此这里不能
    每次无条件写文件，否则用户刚编辑好的命令会在恢复瞬间被覆盖。
    """

    input_path = _command_selection_input_path(state)
    status, backup_path = ensure_command_selection_input_file(
        input_path,
        run_commands,
    )
    return input_path, status, backup_path

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
    
    raise ValueError("invalid command selection response")

def _apply_command_edits(
    run_commands: list[dict],
    edits: list[CommandEdit]
) -> list[dict]:
    effective_commands = deepcopy(run_commands)
    for edit in edits:
        if edit.index < 0 or edit.index >= len(effective_commands):
            raise ValueError(f"edit index out of range: {edit.index}")

        new_command = edit.command.strip()
        if not new_command:
             raise ValueError(f"edited command cannot be empty: index={edit.index}")

        effective_commands[edit.index]["command"] = new_command

    return effective_commands

def command_selection_node(state: dict) -> dict:
    run_commands = state.get("run_commands", [])
    if not run_commands:
        return {
            "selected_run_command_index": None,
            "edited_run_commands": []
        }
    
    expected_hash = compute_run_commands_hash(run_commands)
    input_path, input_status, stale_backup_path = _ensure_command_selection_input(
        state,
        run_commands,
    )

    _render_run_commands_for_terminal(run_commands)
    print(
        "\n[green]Command selection input:[/green] "
        f"[bold]{input_path}[/bold]"
    )
    print("Edit this file, then resume the current thread.")
    if input_status == "refreshed":
        print(
            "[yellow]Stale command selection input was backed up to:[/yellow] "
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
    parsed = _normalize_interrupt_response(response, expected_hash)

    if parsed.run_commands_hash != expected_hash:
        raise ValueError(
            "stale command selection response: run_commands_hash does not "
            "match the current checkpoint; review the regenerated input file"
        )

    if parsed.selected_index < 0 or parsed.selected_index >= len(run_commands):
        raise ValueError(f"selected_index out of range: {parsed.selected_index}")
    
    effective_commands = _apply_command_edits(run_commands, parsed.edits)

    record = CommandSelectionRecord(
        selected_index=parsed.selected_index,
        edits=parsed.edits,
        original_count=len(run_commands),
        run_commands_hash=expected_hash,
        reviewed_at=datetime.now(timezone.utc).isoformat()
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    record_path = settings.output_dir / "command_selection_record.json"
    effective_path = settings.output_dir / "effective_run_commands.json"

    record_path.write_text(
        record.model_dump_json(indent=2),
        encoding="utf-8",
    )
    effective_path.write_text(
        json.dumps(effective_commands, ensure_ascii=False, indent=2),
        encoding="utf-8",
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
        "output_files": [
            *state.get("output_files", []),
            str(input_path),
            str(record_path),
            str(effective_path),
        ],
    }
