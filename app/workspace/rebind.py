from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from app.schemas import ArtifactRecord
from app.workspace.errors import WorkspaceNotPortableError
from app.workspace.schemas import WorkspaceBinding

SINGLE_PATH_KEYS = {
    "run_dir",
    "paper_path",
    "repo_path",
    "log_path",
    "repo_index_path",
    "mapping_targets_path",
    "run_manifest_path",
    "artifact_index_path",
    "execution_log_path",
    "smoke_test_log_path",
    "preflight_report_path",
    "capability_report_path",
    "active_process_record_path",
    "paper_blocks_path",
    "paper_sections_path",
    "paper_parse_report_path",
    "semantic_index_manifest_path",
    "debug_evidence_pack_path",
    "error_report_json_path",
    "error_report_md_path",
    "command_selection_input_path",
}

PATH_MAP_KEYS = {
    "code_evidence_pack_paths",
    "dense_retrieval_report_paths",
}


def _rebase_absolute_path(
    raw_value: str | None,
    *,
    old_run: Path,
    new_run: Path,
    old_repo: Path,
    new_repo: Path,
    old_paper: Path,
    new_paper: Path,
    old_log: Path | None,
    new_log: Path | None,
) -> str | None:
    if raw_value is None:
        return None
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        return raw_value
    resolved = candidate.resolve()

    if resolved == old_paper:
        return str(new_paper)
    if old_log is not None and resolved == old_log:
        if new_log is None:
            raise WorkspaceNotPortableError(
                "新 binding 缺少旧 state 使用的 log"
            )
        return str(new_log)
    if resolved == old_run or old_run in resolved.parents:
        relative = resolved.relative_to(old_run)
        return str((new_run / relative).resolve())
    if resolved == old_repo or old_repo in resolved.parents:
        relative = resolved.relative_to(old_repo)
        return str((new_repo / relative).resolve())
    return raw_value


def _rebind_commands(
    commands: list[dict[str, Any]],
    *,
    old_binding: WorkspaceBinding,
    new_binding: WorkspaceBinding,
) -> list[dict[str, Any]]:
    result = deepcopy(commands)
    old_roots = {
        old_binding.repo_path,
        old_binding.run_dir,
        old_binding.paper_path,
    }

    for command in result:
        raw_command = str(command.get("command", ""))
        # 不修改 shell-like command 文本；发现旧绝对路径就阻断迁移。
        if any(root and root in raw_command for root in old_roots):
            raise WorkspaceNotPortableError(
                "run_command_text_contains_old_absolute_path"
            )
        cwd = command.get("cwd")
        if cwd:
            command["cwd"] = _rebase_absolute_path(
                str(cwd),
                old_run=Path(old_binding.run_dir),
                new_run=Path(new_binding.run_dir),
                old_repo=Path(old_binding.repo_path),
                new_repo=Path(new_binding.repo_path),
                old_paper=Path(old_binding.paper_path),
                new_paper=Path(new_binding.paper_path),
                old_log=(
                    Path(old_binding.log_path)
                    if old_binding.log_path
                    else None
                ),
                new_log=(
                    Path(new_binding.log_path)
                    if new_binding.log_path
                    else None
                ),
            )
    return result


def build_workspace_state_update(
    *,
    state: dict[str, Any],
    new_binding: WorkspaceBinding,
) -> dict[str, Any]:
    """构造有界 update；本函数不直接写 checkpoint。"""

    raw_old = state.get("workspace_binding")
    if raw_old is None:
        # 旧 checkpoint 没有 Phase 26 binding 时，以 state 顶层路径建立旧视图。
        old_binding = new_binding.model_copy(
            update={
                "run_dir": str(state.get("run_dir") or new_binding.run_dir),
                "repo_path": str(
                    state.get("repo_path") or new_binding.repo_path
                ),
                "paper_path": str(
                    state.get("paper_path") or new_binding.paper_path
                ),
                "log_path": state.get("log_path"),
            }
        )
    else:
        old_binding = WorkspaceBinding.model_validate(raw_old)

    if old_binding.job_id != new_binding.job_id:
        raise WorkspaceNotPortableError("workspace binding job_id 改变")
    if old_binding.run_id != new_binding.run_id:
        raise WorkspaceNotPortableError("workspace binding run_id 改变")
    if old_binding.assignment_epoch > new_binding.assignment_epoch:
        raise WorkspaceNotPortableError("拒绝回退 workspace epoch")

    old_run = Path(old_binding.run_dir).resolve()
    new_run = Path(new_binding.run_dir).resolve()
    old_repo = Path(old_binding.repo_path).resolve()
    new_repo = Path(new_binding.repo_path).resolve()
    old_paper = Path(old_binding.paper_path).resolve()
    new_paper = Path(new_binding.paper_path).resolve()
    old_log = (
        Path(old_binding.log_path).resolve()
        if old_binding.log_path
        else None
    )
    new_log = (
        Path(new_binding.log_path).resolve()
        if new_binding.log_path
        else None
    )

    update: dict[str, Any] = {
        "workspace_binding": new_binding.model_dump(),
        "workspace_assignment_epoch": new_binding.assignment_epoch,
        "workspace_manifest_id": new_binding.manifest_id,
        "workspace_manifest_hash": new_binding.manifest_hash,
        "run_dir": str(new_run),
        "repo_path": str(new_repo),
        "paper_path": str(new_paper),
        "log_path": str(new_log) if new_log is not None else None,
        # 新 workspace 必须重新建立 effective profile fingerprint。
        "execution_profile_fingerprint": "",
    }

    for key in SINGLE_PATH_KEYS:
        if key not in state or key in update:
            continue
        update[key] = _rebase_absolute_path(
            state.get(key),
            old_run=old_run,
            new_run=new_run,
            old_repo=old_repo,
            new_repo=new_repo,
            old_paper=old_paper,
            new_paper=new_paper,
            old_log=old_log,
            new_log=new_log,
        )

    for key in PATH_MAP_KEYS:
        if key not in state:
            continue
        update[key] = {
            map_key: _rebase_absolute_path(
                str(value),
                old_run=old_run,
                new_run=new_run,
                old_repo=old_repo,
                new_repo=new_repo,
                old_paper=old_paper,
                new_paper=new_paper,
                old_log=old_log,
                new_log=new_log,
            )
            for map_key, value in dict(state[key]).items()
        }

    for key in ("run_commands", "edited_run_commands"):
        if key in state:
            update[key] = _rebind_commands(
                list(state[key]),
                old_binding=old_binding,
                new_binding=new_binding,
            )

    if "output_files" in state:
        update["output_files"] = [
            _rebase_absolute_path(
                str(value),
                old_run=old_run,
                new_run=new_run,
                old_repo=old_repo,
                new_repo=new_repo,
                old_paper=old_paper,
                new_paper=new_paper,
                old_log=old_log,
                new_log=new_log,
            )
            for value in state["output_files"]
        ]

    if "artifact_records" in state:
        records = [
            ArtifactRecord.model_validate(item)
            for item in state["artifact_records"]
        ]
        update["artifact_records"] = [
            record.model_copy(
                update={
                    "absolute_path": str(
                        (new_run / record.relative_path).resolve()
                    )
                }
            ).model_dump()
            for record in records
        ]

    return update
