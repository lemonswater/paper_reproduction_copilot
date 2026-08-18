from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import settings
from app.failure_memory.errors import FailureMemoryError
from app.failure_memory.identity import build_failure_signature
from app.failure_memory.schemas import (
    FailureEnvironmentIdentity,
    FailureQuery,
)
from app.model_routing.factory import build_model_gateway
from app.prompts.debug_prompt import DEBUG_PROMPT
from app.retrieval.indexer import (
    build_repository_index,
    load_repository_index,
)
from app.retrieval.service import build_evidence_pack
from app.schemas import DebugReport, StageError
from app.tools.artifact_tools import (
    artifact_dir,
    artifact_state_update,
    register_existing_artifact,
    try_get_git_commit,
    try_is_git_clean,
    write_json_artifact,
    write_text_artifact,
)
from app.tools.error_tools import (
    stage_error_result,
    structured_failure_update,
)
from app.tools.log_tools import (
    classify_error_heuristic,
    extract_repo_traceback_paths,
    extract_traceback,
    read_log,
)
from app.skills.catalog import build_skill_registry
from app.skills.schemas import (
    SkillInvocationContext,
    SkillInvocationRequest,
)
from app.tools.search_tools import SearchToolError
from app.tools.structured_output_tools import (
    write_structured_output_trace,
)


def _build_fallback_report(
    *,
    error_type: str,
    traceback: str,
    log_path: str,
) -> DebugReport:
    """在没有错误证据或模型格式错误时返回保守、可继续流转的报告。"""

    if not traceback.strip():
        return DebugReport(
            error_type="unknown",
            most_likely_causes=[
                "日志中没有检测到 traceback 或已知错误关键字。",
            ],
            related_files=[],
            check_order=[
                f"确认 {log_path} 是失败执行产生的日志，而不是 --help 输出。",
                "重新执行失败命令，并同时保存 stdout、stderr 和返回码。",
                "使用新生成的失败日志重新运行 plan-repair。",
            ],
            suggested_fixes=[
                "先获取真实失败日志；当前证据不足，不应自动修改命令。",
            ],
            risks=[
                "根据没有错误信息的日志制定修复方案可能导致误判。",
            ],
            unresolved_questions=[
                "原命令的非零返回码和 stderr 是什么？",
            ],
        )

    return DebugReport(
        error_type=error_type,
        most_likely_causes=[
            "检测到了错误证据，但模型返回结果未通过 DebugReport 结构校验。",
        ],
        related_files=[],
        check_order=[
            "先根据原始 traceback 和错误类型初判进行人工排查。",
            "确认日志完整后重新生成结构化调试报告。",
        ],
        suggested_fixes=[
            "保留原始日志，在证据确认前不要自动执行修复命令。",
        ],
        risks=[
            "fallback 报告没有模型的上下文诊断，可能遗漏具体根因。",
        ],
        unresolved_questions=[
            "模型为何没有返回符合 DebugReport 的结构？",
        ],
    )


def _build_cuda_oom_report() -> DebugReport:
    """为证据明确的 CUDA OOM 提供无需 LLM 的确定性诊断。"""

    return DebugReport(
        error_type="cuda_oom",
        most_likely_causes=[
            "当前 batch size 导致单次前向或反向计算的 GPU 显存需求过高。",
            "GPU 上可能同时存在其他进程，导致可用显存不足。",
        ],
        related_files=["train-msr-small.py"],
        check_order=[
            "使用 nvidia-smi 检查 GPU 可用显存和其他占用进程。",
            "将命令中已有的 batch size 缩小为 1 后重新运行 smoke test。",
            "若仍然 OOM，再检查输入点数、clip length 和模型维度。",
        ],
        suggested_fixes=[
            "优先把已有 batch size 参数缩小为 1，不修改源码或依赖环境。",
        ],
        risks=[
            "batch size 变化会影响吞吐量，正式训练时可能需要重新评估学习率。",
        ],
        unresolved_questions=[
            "失败时 GPU 上是否存在其他占用显存的进程？",
        ],
    )

def _debug_keywords(
    *,
    error_type: str,
    traceback: str,
    traceback_paths: list[str],
) -> list[str]:
    """从本地错误事实提取有限关键词，不调用模型。"""

    exception_names = re.findall(
        r"\b[A-Z][A-Za-z0-9_]*(?:Error|Exception)\b",
        traceback,
    )
    quoted_identifiers = re.findall(
        r"""["']([A-Za-z_][A-Za-z0-9_.-]{2,80})["']""",
        traceback,
    )
    path_terms = [
        Path(path).stem
        for path in traceback_paths
    ]
    return list(
        dict.fromkeys(
            value
            for value in [
                error_type,
                *exception_names,
                *quoted_identifiers,
                *path_terms,
            ]
            if value.strip()
        )
    )[:24]


def _build_debug_evidence(
    *,
    state: dict,
    error_type: str,
    traceback: str,
    traceback_paths: list[str],
) -> tuple[dict | None, str | None, list, str | None]:
    """
    返回：
    pack payload、pack path、新 ArtifactRecord、可恢复 warning。

    检索失败不应掩盖原始实验错误，所以这里返回 warning，
    由 DebugReport.unresolved_questions 记录，而不是终止节点。
    """

    repo_path = state.get("repo_path")
    if not repo_path:
        return (
            None,
            None,
            [],
            "未提供 repo_path，无法建立 Debug Evidence Pack。",
        )

    records = []
    try:
        index_path = state.get("repo_index_path")
        if (
            index_path
            and Path(str(index_path)).is_file()
        ):
            index = load_repository_index(
                str(index_path)
            )
        else:
            index = build_repository_index(
                repo_path,
                index_version=(
                    settings.retrieval_index_version
                ),
                max_file_bytes=(
                    settings.retrieval_max_file_bytes
                ),
            )
            generated_index_path, index_record = (
                write_json_artifact(
                    state=state,
                    relative_path=(
                        "debug/repository_index.json"
                    ),
                    payload=index.model_dump(
                        mode="json"
                    ),
                    producer_node="log_debug",
                )
            )
            index_path = str(
                generated_index_path
            )
            records.append(index_record)

        _, pack = build_evidence_pack(
            repo_path=repo_path,
            query=(
                f"{error_type}\n"
                f"{traceback[-12000:]}"
            ),
            keywords=_debug_keywords(
                error_type=error_type,
                traceback=traceback,
                traceback_paths=traceback_paths,
            ),
            index=index,
            index_version=(
                settings.retrieval_index_version
            ),
            max_file_bytes=(
                settings.retrieval_max_file_bytes
            ),
            top_k=settings.retrieval_top_k,
            context_lines=(
                settings.retrieval_context_lines
            ),
            max_span_lines=(
                settings.retrieval_max_span_lines
            ),
            rrf_k=settings.retrieval_rrf_k,
            preferred_paths=traceback_paths,
        )

        pack_path, pack_record = write_json_artifact(
            state=state,
            relative_path=(
                "debug/debug_evidence_pack.json"
            ),
            payload=pack.model_dump(mode="json"),
            producer_node="log_debug",
        )
        records.append(pack_record)
        return (
            pack.model_dump(mode="json"),
            str(pack_path),
            records,
            None,
        )
    except (
        OSError,
        SearchToolError,
        ValueError,
    ) as exc:
        return (
            None,
            None,
            records,
            (
                "Debug Evidence 检索失败："
                f"{type(exc).__name__}: {exc}"
            ),
        )

def _build_failure_case_pack(
    *,
    state: dict,
    error_type: str,
    traceback: str,
) -> tuple[dict | None, str | None, list, str | None]:
    """检索失败时降级，不掩盖当前实验的原始错误。"""

    if not settings.failure_memory_enabled:
        return None, None, [], None

    # Lazy import to break circular dependency:
    # log_debug_node -> failure_memory.factory -> comparison.factory
    # -> comparison.__init__ -> run_evidence.__init__ -> interaction.artifacts
    # -> graph -> log_debug_node
    from app.execution.profile_store import (
        get_execution_profile,
    )
    from app.failure_memory.factory import (
        build_failure_case_retriever,
    )

    raw_error = state.get("active_stage_error")
    if not raw_error:
        return (
            None,
            None,
            [],
            "当前 State 缺少 active_stage_error，未检索历史失败案例。",
        )

    try:
        stage_error = StageError.model_validate(raw_error)
        profile_id = str(state.get("execution_profile_id") or "")
        profile_fingerprint = str(
            state.get("execution_profile_fingerprint") or ""
        )
        if not profile_id or not profile_fingerprint:
            raise ValueError("当前 Run 缺少 Execution Profile identity")

        profile = get_execution_profile(profile_id)
        environment = FailureEnvironmentIdentity(
            execution_profile_id=profile_id,
            execution_profile_fingerprint=profile_fingerprint,
            execution_backend=profile.backend,
            repository_commit=try_get_git_commit(
                state.get("repo_path")
            ),
            repository_clean=try_is_git_clean(
                state.get("repo_path")
            ),
        )
        signature = build_failure_signature(
            stage_error=stage_error,
            error_type=error_type,
            traceback_text=traceback,
            repo_path=state.get("repo_path"),
        )
        pack = build_failure_case_retriever().search(
            FailureQuery(
                signature=signature,
                environment=environment,
            )
        )
        pack_path, record = write_json_artifact(
            state=state,
            relative_path="debug/failure_case_pack.json",
            payload=pack.model_dump(mode="json"),
            producer_node="log_debug",
        )
        return (
            pack.model_dump(mode="json"),
            str(pack_path),
            [record],
            None,
        )
    except (
        FailureMemoryError,
        OSError,
        ValueError,
    ) as exc:
        return (
            None,
            None,
            [],
            "历史 Failure Case 检索失败："
            f"{type(exc).__name__}: {exc}",
        )


CUDA_BUILD_MARKERS = (
    "nvcc",
    "cudaextension",
    "cuda extension",
    "cuda_home",
    "unsupported gpu architecture",
    "unsupported cuda architecture",
    "ninja: build stopped",
)

BUILD_FAILURE_MARKERS = (
    "error",
    "failed",
    "not found",
    "no such file",
    "undefined symbol",
    "unsupported",
)


def _should_run_cuda_build_skill(log_text: str) -> bool:
    """仅在同时具备 CUDA/构建身份和失败特征时选择 Skill。"""

    lowered = log_text.lower()
    return (
        any(marker in lowered for marker in CUDA_BUILD_MARKERS)
        and any(marker in lowered for marker in BUILD_FAILURE_MARKERS)
    )


def _is_under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _run_optional_cuda_build_skill(
    *,
    state: dict,
    log_text: str,
) -> tuple[
    dict | None,
    str | None,
    str | None,
    list,
    str | None,
]:
    """
    返回：typed output、result path、record path、Artifact records、warning。

    这是可选增强路径。任何 Skill 失败都只能返回 warning，不能覆盖当前
    experiment StageError，也不能阻止原 Debug 流程继续执行。
    """

    if not settings.agent_skills_enabled:
        return None, None, None, [], None
    if not _should_run_cuda_build_skill(log_text):
        return None, None, None, [], None

    raw_repo_path = state.get("repo_path")
    raw_log_path = state.get("log_path")
    if not raw_repo_path or not raw_log_path:
        return (
            None,
            None,
            None,
            [],
            "CUDA Build Skill 缺少 repo_path 或 log_path。",
        )

    try:
        repo_path = Path(str(raw_repo_path)).expanduser().resolve(
            strict=True
        )
        log_path = Path(str(raw_log_path)).expanduser().resolve(
            strict=True
        )
        allowed_root = settings.allowed_root.expanduser().resolve()
        if (
            not repo_path.is_dir()
            or not log_path.is_file()
            or not _is_under(repo_path, allowed_root)
            or not _is_under(log_path, allowed_root)
        ):
            raise ValueError("Skill 输入不在受控根目录")

        # Tool 输入保持相对路径；绝对根目录只由可信 Host Context 提供。
        workspace_root = repo_path.parent
        run_root = log_path.parent
        registry = build_skill_registry(
            package_root=settings.agent_skill_package_dir,
            globally_enabled=settings.agent_skills_enabled,
            enabled_skill_ids=set(settings.agent_skill_enabled_ids),
        )
        bound = registry.get("cuda_build_diagnosis")
        result = registry.invoke(
            request=SkillInvocationRequest(
                skill_id="cuda_build_diagnosis",
                skill_version=bound.package.manifest.skill_version,
                expected_skill_sha256=bound.skill_sha256,
                input_payload={
                    "repo_path": repo_path.name,
                    "log_path": log_path.name,
                    "max_log_chars": 30_000,
                },
            ),
            context=SkillInvocationContext(
                actor="node:log_debug",
                request_id=(
                    str(state.get("task_id") or "log-debug")
                ),
                job_id=(
                    str(state["job_id"])
                    if state.get("job_id")
                    else None
                ),
                workspace_root=str(workspace_root),
                run_root=str(run_root),
                granted_capabilities=sorted(
                    settings.agent_skill_granted_capabilities
                ),
            ),
        )

        result_path, result_record = write_json_artifact(
            state=state,
            relative_path=(
                "debug/skills/cuda_build_diagnosis_result.json"
            ),
            payload={
                "skill_id": "cuda_build_diagnosis",
                "skill_sha256": bound.skill_sha256,
                "output": result.output,
                "failure": (
                    result.failure.model_dump(mode="json")
                    if result.failure
                    else None
                ),
            },
            producer_node="log_debug",
        )
        invocation_path, invocation_record = write_json_artifact(
            state=state,
            relative_path=(
                "debug/skills/"
                "cuda_build_diagnosis_invocation.json"
            ),
            payload=result.record.model_dump(mode="json"),
            producer_node="log_debug",
        )
        records = [result_record, invocation_record]

        if result.failure is not None:
            return (
                None,
                str(result_path),
                str(invocation_path),
                records,
                "CUDA Build Skill 未成功："
                f"{result.failure.code}",
            )
        return (
            result.output,
            str(result_path),
            str(invocation_path),
            records,
            None,
        )
    except (OSError, ValueError) as exc:
        # 不拼接 exc 文本，避免路径或第三方错误内容进入最终提示。
        return (
            None,
            None,
            None,
            [],
            "CUDA Build Skill 初始化失败："
            f"{type(exc).__name__}",
        )


def log_debug_node(state: dict) -> dict:
    log_path = state.get("log_path")
    if not log_path:
        return stage_error_result(
            state=state,
            stage="log_debug",
            code="LOG_PATH_REQUIRED",
            category="agent",
            message="必须提供 log_path",
        )

    log_text = read_log(log_path)
    traceback = extract_traceback(log_text)
    error_type = classify_error_heuristic(
        traceback
    )
    traceback_paths = extract_repo_traceback_paths(
        traceback,
        repo_path=state.get("repo_path"),
    )
    (
        debug_pack,
        debug_pack_path,
        retrieval_records,
        retrieval_warning,
    ) = _build_debug_evidence(
        state=state,
        error_type=error_type,
        traceback=traceback,
        traceback_paths=traceback_paths,
    )
    (
        failure_case_pack,
        failure_case_pack_path,
        failure_case_records,
        failure_case_warning,
    ) = _build_failure_case_pack(
        state=state,
        error_type=error_type,
        traceback=traceback,
    )
    (
        cuda_skill_output,
        cuda_skill_result_path,
        cuda_skill_record_path,
        skill_records,
        skill_warning,
    ) = _run_optional_cuda_build_skill(
        state=state,
        log_text=log_text,
    )

    trace_path = None
    invocation = None

    # 高置信度规则优先，不浪费 LLM 调用。
    if error_type == "cuda_oom":
        report = _build_cuda_oom_report()
    elif not traceback.strip():
        report = _build_fallback_report(
            error_type=error_type,
            traceback=traceback,
            log_path=log_path,
        )
    else:
        prompt = DEBUG_PROMPT.format(
            error_type=error_type,
            traceback=traceback,
            experiment_plan=json.dumps(
                state.get(
                    "experiment_plan",
                    {},
                ),
                ensure_ascii=False,
                indent=2,
            ),
            debug_evidence_pack=json.dumps(
                debug_pack or {
                    "items": [],
                    "warning": retrieval_warning,
                },
                ensure_ascii=False,
                indent=2,
            ),
            failure_case_pack=json.dumps(
                failure_case_pack or {
                    "items": [],
                    "warning": failure_case_warning,
                },
                ensure_ascii=False,
                indent=2,
            ),
            skill_evidence=json.dumps(
                cuda_skill_output or {
                    "finding_codes": [],
                    "related_files": [],
                    "warning": skill_warning,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        invocation = build_model_gateway().invoke_structured(
            task_kind="failure_debug",
            schema=DebugReport,
            prompt=prompt,
            node_name="log_debug",
            job_id=state.get("job_id"),
            run_id=state.get("run_id"),
            quality_tier="high",
        )

        if invocation.value is not None:
            report = invocation.value
            if report.error_type != error_type:
                report = report.model_copy(
                    update={
                        "error_type": error_type,
                    }
                )
        else:
            report = _build_fallback_report(
                error_type=error_type,
                traceback=traceback,
                log_path=log_path,
            )

        trace_path = write_structured_output_trace(
            result=invocation.result,
            node_name="log_debug",
            schema_name="DebugReport",
            output_dir=artifact_dir(
                state,
                "traces",
                "structured",
            ),
            fallback_used=(
                invocation.value is None
            ),
            model_invocation_id=invocation.invocation_id,
            model_decision_sha256=(
                invocation.decision.decision_sha256
            ),
            model_profile_id=(
                invocation.decision.executed_profile_id
            ),
            model_name=(
                invocation.decision.executed_model_name
            ),
            model_usage_quality=(
                invocation.ledger_record.usage_quality
                if invocation.ledger_record is not None
                else None
            ),
        )

    allowed_paths = {
        str(item["file_path"])
        for item in (
            (debug_pack or {}).get("items", [])
        )
        if isinstance(item, dict)
        and item.get("file_path")
    }
    allowed_paths.update(
        str(path)
        for path in (
            (cuda_skill_output or {}).get("related_files", [])
        )
    )

    # 模型输出的 related_files 必须落入 pack 白名单。
    # traceback 路径已在 log_tools 中通过真实仓库边界校验，
    # 但若 pack 可用，仍要求它进入当前检索结果。
    trusted_traceback_paths = [
        path
        for path in traceback_paths
        if not allowed_paths
        or path in allowed_paths
    ]
    trusted_model_paths = [
        path
        for path in report.related_files
        if path in allowed_paths
    ]
    allowed_case_ids = {
        str(item["case_id"])
        for item in (failure_case_pack or {}).get("items", [])
        if isinstance(item, dict) and item.get("case_id")
    }
    trusted_case_ids = [
        case_id
        for case_id in report.historical_failure_case_ids
        if case_id in allowed_case_ids
    ]
    unresolved = list(
        report.unresolved_questions
    )
    if retrieval_warning:
        unresolved.append(retrieval_warning)
    if failure_case_warning:
        unresolved.append(failure_case_warning)
    if skill_warning:
        unresolved.append(skill_warning)

    report = report.model_copy(
        update={
            "related_files": list(
                dict.fromkeys(
                    [
                        *trusted_traceback_paths,
                        *trusted_model_paths,
                    ]
                )
            ),
            "historical_failure_case_ids": list(
                dict.fromkeys(trusted_case_ids)
            ),
            "unresolved_questions": list(
                dict.fromkeys(unresolved)
            ),
        }
    )

    _, json_record = write_json_artifact(
        state=state,
        relative_path="debug/debug_report.json",
        payload=report.model_dump(
            mode="json"
        ),
        producer_node="log_debug",
    )
    _, md_record = write_text_artifact(
        state=state,
        relative_path="debug/debug_report.md",
        text=_render_debug_markdown(report),
        producer_node="log_debug",
        media_type="text/markdown",
    )

    records = [
        *retrieval_records,
        *failure_case_records,
        *skill_records,
        json_record,
        md_record,
    ]
    if trace_path is not None:
        records.append(
            register_existing_artifact(
                state=state,
                path=trace_path,
                producer_node="log_debug",
                media_type="application/json",
            )
        )

    payload = {
        "debug_report": report.model_dump(
            mode="json"
        ),
        "debug_evidence_pack": debug_pack,
        "debug_evidence_pack_path": (
            debug_pack_path
        ),
        "failure_case_pack": failure_case_pack,
        "failure_case_pack_path": (
            failure_case_pack_path
        ),
        "skill_results": {
            **state.get("skill_results", {}),
            **(
                {"cuda_build_diagnosis": cuda_skill_output}
                if cuda_skill_output is not None
                else {}
            ),
        },
        "skill_result_paths": {
            **state.get("skill_result_paths", {}),
            **(
                {"cuda_build_diagnosis": cuda_skill_result_path}
                if cuda_skill_result_path
                else {}
            ),
        },
        "skill_invocation_record_paths": {
            **state.get("skill_invocation_record_paths", {}),
            **(
                {"cuda_build_diagnosis": cuda_skill_record_path}
                if cuda_skill_record_path
                else {}
            ),
        },
        **artifact_state_update(
            state,
            records,
        ),
    }

    if (
        invocation is not None
        and invocation.value is None
    ):
        payload.update(
            structured_failure_update(
                state={
                    **state,
                    **payload,
                },
                stage="log_debug",
                invocation=invocation,
                terminal=False,
            )
        )

    return payload

def _render_debug_markdown(report: DebugReport) -> str:
    lines = ["# 调试报告", "", f"错误类型：`{report.error_type}`", ""]
    sections = [
        ("最可能的原因", report.most_likely_causes),
        ("相关文件", report.related_files),
        ("检查顺序", report.check_order),
        ("建议修复方案", report.suggested_fixes),
        ("风险", report.risks),
        ("待解决问题", report.unresolved_questions),
        ("历史失败案例", report.historical_failure_case_ids),
    ]
    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("- 无")
        else:
            for item in items:
                lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)
