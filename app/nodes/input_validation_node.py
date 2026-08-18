from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.execution.profile_store import get_execution_profile
from app.schemas import InputCheck, InputValidationReport
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import (
    build_stage_error,
    persist_stage_errors,
)

SUPPORTED_PAPER_SUFFIXES = {".pdf", ".md", ".txt"}


def _check_required_file(
    *,
    name: str,
    raw_path: str | None,
    missing_code: str,
) -> InputCheck:
    if not raw_path:
        return InputCheck(
            name=name,
            status="failed",
            category="user",
            code=missing_code,
            message=f"必须提供 {name}",
        )

    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        return InputCheck(
            name=name,
            status="failed",
            category="user",
            code="INPUT_NOT_FOUND",
            message=f"{name} 不存在",
            path=str(path),
        )
    if not path.is_file():
        return InputCheck(
            name=name,
            status="failed",
            category="user",
            code="INPUT_NOT_FILE",
            message=f"{name} 不是普通文件",
            path=str(path),
        )

    return InputCheck(
        name=name,
        status="passed",
        category="user",
        code="OK",
        message=f"{name} 可读取",
        path=str(path),
    )


def _check_paper(path: str | None) -> list[InputCheck]:
    check = _check_required_file(
        name="paper_path",
        raw_path=path,
        missing_code="PAPER_PATH_REQUIRED",
    )
    checks = [check]

    if check.status == "passed" and check.path:
        suffix = Path(check.path).suffix.lower()
        if suffix not in SUPPORTED_PAPER_SUFFIXES:
            checks.append(
                InputCheck(
                    name="paper_format",
                    status="failed",
                    category="user",
                    code="UNSUPPORTED_PAPER_FORMAT",
                    message=f"不支持的论文格式：{suffix}",
                    path=check.path,
                )
            )
        else:
            checks.append(
                InputCheck(
                    name="paper_format",
                    status="passed",
                    category="user",
                    code="OK",
                    message=f"论文格式受支持：{suffix}",
                    path=check.path,
                )
            )

    return checks


def _check_repo(path: str | None) -> InputCheck:
    if not path:
        return InputCheck(
            name="repo_path",
            status="failed",
            category="user",
            code="REPO_PATH_REQUIRED",
            message="必须提供 repo_path",
        )

    repo = Path(path).expanduser().resolve()
    if not repo.exists():
        return InputCheck(
            name="repo_path",
            status="failed",
            category="user",
            code="REPO_NOT_FOUND",
            message="代码仓库目录不存在",
            path=str(repo),
        )
    if not repo.is_dir():
        return InputCheck(
            name="repo_path",
            status="failed",
            category="user",
            code="REPO_NOT_DIRECTORY",
            message="repo_path 不是目录",
            path=str(repo),
        )

    return InputCheck(
        name="repo_path",
        status="passed",
        category="user",
        code="OK",
        message="代码仓库目录存在",
        path=str(repo),
    )


def _check_optional_log(path: str | None) -> InputCheck:
    if not path:
        return InputCheck(
            name="log_path",
            status="passed",
            category="user",
            code="NOT_PROVIDED",
            message="本次未提供外部日志",
        )
    return _check_required_file(
        name="log_path",
        raw_path=path,
        missing_code="LOG_PATH_REQUIRED",
    )


def _check_execution_profile(
    *,
    profile_id: str | None,
    repo_path: str | None,
) -> InputCheck:
    if not profile_id:
        return InputCheck(
            name="execution_profile",
            status="failed",
            category="environment",
            code="EXECUTION_PROFILE_REQUIRED",
            message="缺少 execution_profile_id",
        )

    try:
        profile = get_execution_profile(profile_id)
    except (FileNotFoundError, ValueError) as exc:
        return InputCheck(
            name="execution_profile",
            status="failed",
            category="environment",
            code="EXECUTION_PROFILE_INVALID",
            message=str(exc),
        )

    workspace = Path(profile.workspace_root).expanduser().resolve()
    if not workspace.is_dir():
        return InputCheck(
            name="execution_profile",
            status="failed",
            category="environment",
            code="PROFILE_WORKSPACE_NOT_FOUND",
            message="execution profile workspace_root 不存在",
            path=str(workspace),
        )

    if repo_path:
        repo = Path(repo_path).expanduser().resolve()
        if repo != workspace and workspace not in repo.parents:
            return InputCheck(
                name="execution_profile",
                status="failed",
                category="environment",
                code="REPO_OUTSIDE_PROFILE_WORKSPACE",
                message=(
                    "repo_path 不在 execution profile workspace_root 内"
                ),
                path=str(workspace),
            )

    return InputCheck(
        name="execution_profile",
        status="passed",
        category="environment",
        code="OK",
        message=f"execution profile 可用：{profile.profile_id}",
        path=str(workspace),
    )


def input_validation_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    在任何 PDF、Git、rg、LLM 或论文命令之前检查外部输入。
    """

    checks = [
        *_check_paper(state.get("paper_path")),
        _check_repo(state.get("repo_path")),
        _check_optional_log(state.get("log_path")),
        _check_execution_profile(
            profile_id=state.get("execution_profile_id"),
            repo_path=state.get("repo_path"),
        ),
    ]

    valid = all(check.status != "failed" for check in checks)
    report = InputValidationReport(
        valid=valid,
        checks=checks,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    report_path, report_record = write_json_artifact(
        state=state,
        relative_path="inputs/input_validation_report.json",
        payload=report.model_dump(),
        producer_node="input_validation",
    )

    update: dict[str, Any] = {
        "input_validation_report": report.model_dump(),
        "inputs_validated": valid,
        **artifact_state_update(state, [report_record]),
    }

    if valid:
        return update

    errors = [
        build_stage_error(
            stage="input_validation",
            code=check.code,
            category=check.category,
            message=check.message,
            terminal=True,
            context={
                "check_name": check.name,
                "path": check.path,
            },
        )
        for check in checks
        if check.status == "failed"
    ]

    working_state = {**state, **update}
    return {
        **update,
        **persist_stage_errors(
            state=working_state,
            new_errors=errors,
        ),
    }