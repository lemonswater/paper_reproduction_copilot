from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.model import get_chat_model
from app.prompts.file_repair_prompt import FILE_REPAIR_PROMPT
from app.schemas import FileRepairProposal
from app.tools.artifact_tools import (
    artifact_dir,
    artifact_state_update,
    register_existing_artifact,
    write_json_artifact,
)
from app.tools.error_tools import structured_failure_update
from app.tools.log_tools import extract_traceback, read_log
from app.tools.patch_tools import collect_source_context, resolve_patch_target
from app.tools.structured_output_tools import (
    invoke_structured_with_retry,
    write_structured_output_trace,
)


def _no_patch(summary: str, root_cause: str) -> FileRepairProposal:
    """任何输入不足或校验失败都安全降级，不生成文件修改。"""

    return FileRepairProposal(
        proposal_id=f"file_repair_{uuid4().hex[:12]}",
        kind="no_patch",
        summary=summary,
        root_cause=root_cause,
        edits=[],
        verification_targets=[],
        risks=["证据不足时自动修改源码可能改变论文实现语义。"],
        bounded=True,
    )


def _is_test_path(relative_path: str) -> bool:
    path = Path(relative_path)
    return "tests" in path.parts or path.name.startswith("test_")


def _extract_action_verification_targets(
    *,
    pending_action: dict,
    repo_path: str,
) -> list[str]:
    """从 pytest action 中提取已有测试文件，建立确定性行为验证目标。"""

    program = pending_action.get("program")
    args = list(pending_action.get("args") or [])
    if program != "python" or "pytest" not in args:
        return []

    repo = Path(repo_path).resolve()
    targets: list[str] = []

    for arg in args:
        raw_path = str(arg).split("::", 1)[0]
        if not raw_path.endswith(".py"):
            continue

        candidate = Path(raw_path)
        target = (
            candidate.resolve()
            if candidate.is_absolute()
            else (repo / candidate).resolve()
        )
        if target == repo or repo not in target.parents:
            continue

        relative = target.relative_to(repo).as_posix()
        if not _is_test_path(relative):
            continue

        try:
            resolve_patch_target(repo, relative)
        except ValueError:
            continue

        if relative not in targets:
            targets.append(relative)

    return targets


def _proposal_state_update(
    *,
    state: dict,
    proposal: FileRepairProposal,
    trace_path: Path | None = None,
    invocation: object | None = None,
) -> dict:
    """所有 no_patch/patch 分支都写入并登记同一个 run-native Artifact。"""

    _, proposal_record = write_json_artifact(
        state=state,
        relative_path="debug/file_repair_proposal.json",
        payload=proposal.model_dump(),
        producer_node="file_repair_planner",
    )
    records = [proposal_record]
    if trace_path is not None:
        records.append(
            register_existing_artifact(
                state=state,
                path=trace_path,
                producer_node="file_repair_planner",
                media_type="application/json",
            )
        )

    payload = {
        "file_repair_proposal": proposal.model_dump(),
        **artifact_state_update(state, records),
    }
    if invocation is not None and getattr(invocation, "value", None) is None:
        payload.update(
            structured_failure_update(
                state={**state, **payload},
                stage="file_repair_planner",
                invocation=invocation,
                terminal=False,
            )
        )
    return payload


def file_repair_planner_node(state: dict) -> dict:
    if not settings.enable_file_repair:
        proposal = _no_patch(
            "文件修复功能已禁用",
            "ENABLE_FILE_REPAIR 为 false",
        )
        return _proposal_state_update(state=state, proposal=proposal)

    attempts = int(state.get("file_repair_attempt_count", 0))
    if attempts >= settings.max_file_repair_attempts:
        proposal = _no_patch(
            "已达到文件修复次数上限",
            "当前运行已经尝试过文件级修复",
        )
        return _proposal_state_update(state=state, proposal=proposal)

    repo_path = state.get("repo_path")
    debug_report = state.get("debug_report") or {}
    log_path = state.get("log_path")
    related_files = list(debug_report.get("related_files") or [])

    if not repo_path or not log_path or not related_files:
        proposal = _no_patch(
            "缺少文件修复所需的证据",
            "repo_path、log_path 或 debug_report.related_files 为空",
        )
        return _proposal_state_update(state=state, proposal=proposal)

    try:
        source_context, allowed_paths = collect_source_context(
            repo_path=repo_path,
            related_files=related_files,
        )
        traceback = extract_traceback(read_log(log_path))
    except (FileNotFoundError, UnicodeDecodeError, ValueError) as exc:
        proposal = _no_patch(
            "无法收集安全的源码上下文",
            str(exc),
        )
        return _proposal_state_update(state=state, proposal=proposal)

    if not allowed_paths or not traceback.strip():
        proposal = _no_patch(
            "源码上下文或 traceback 为空",
            "没有足够的精确证据来生成补丁建议",
        )
        return _proposal_state_update(state=state, proposal=proposal)

    prompt = FILE_REPAIR_PROMPT.format(
        execution_mode=state.get("active_execution_mode", "unknown"),
        debug_report=json.dumps(debug_report, ensure_ascii=False, indent=2),
        traceback=traceback,
        pending_action=json.dumps(
            state.get("pending_action") or {},
            ensure_ascii=False,
            indent=2,
        ),
        source_context=source_context,
    )
    action_verification_targets = _extract_action_verification_targets(
        pending_action=state.get("pending_action") or {},
        repo_path=repo_path,
    )

    invocation = invoke_structured_with_retry(
        llm=get_chat_model(temperature=0),
        schema=FileRepairProposal,
        prompt=prompt,
        method=settings.structured_output_method,
        strict=settings.structured_output_strict,
        max_retries=settings.structured_output_max_retries,
        raw_preview_chars=settings.structured_output_raw_preview_chars,
        provider_max_retries=settings.provider_max_retries,
        provider_retry_base_seconds=(
            settings.provider_retry_base_seconds
        ),
    )

    if invocation.value is None:
        proposal = _no_patch(
            "模型未返回合法的文件修复建议",
            "结构化输出重试次数已用尽",
        )
    else:
        proposal = invocation.value
        if not proposal.proposal_id:
            proposal = proposal.model_copy(
                update={"proposal_id": f"file_repair_{uuid4().hex[:12]}"}
            )

        # Prompt 白名单必须再由程序强制检查。
        proposed_paths = {edit.relative_path for edit in proposal.edits}
        if not proposed_paths.issubset(set(allowed_paths)):
            proposal = _no_patch(
                "修复建议引用了所提供上下文之外的文件",
                "模型尝试修改不在白名单中的路径",
            )
        elif any(_is_test_path(path) for path in proposed_paths):
            proposal = _no_patch(
                "修复建议试图修改行为测试",
                "测试文件只能作为 verification target，不能作为自动补丁目标",
            )
        else:
            verification_targets = list(
                dict.fromkeys(
                    [
                        *action_verification_targets,
                        *proposal.verification_targets,
                    ]
                )
            )
            proposal = proposal.model_copy(
                update={"verification_targets": verification_targets}
            )

    trace_path = write_structured_output_trace(
        result=invocation,
        node_name="file_repair_planner",
        schema_name="FileRepairProposal",
        output_dir=artifact_dir(
            state,
            "traces",
            "structured",
        ),
        fallback_used=invocation.value is None,
    )

    return _proposal_state_update(
        state=state,
        proposal=proposal,
        trace_path=trace_path,
        invocation=invocation,
    )
