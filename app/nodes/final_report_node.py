from __future__ import annotations

import json
from pathlib import Path

from app.schemas import StageError
from app.tools.artifact_tools import (
    artifact_state_update,
    write_text_artifact,
)


def final_report_node(state: dict) -> dict:
    report_text = _render_final_report(state)
    _, report_record = write_text_artifact(
        state=state,
        relative_path="reports/final_report.md",
        text=report_text,
        producer_node="final_report",
        media_type="text/markdown",
    )

    return {
        "final_report": report_text,
        **artifact_state_update(state, [report_record]),
    }

def _render_section(title: str, items: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    if not items:
        lines.append("- 无")
        lines.append("")
        return lines

    for item in items:
        lines.append(f"- {item}")
    lines.append("")
    return lines

def _load_process_record_summary(state: dict) -> dict:
    raw_path = state.get("active_process_record_path")
    raw_run_dir = state.get("run_dir")
    if not raw_path or not raw_run_dir:
        return {}

    try:
        run_dir = Path(raw_run_dir).resolve()
        path = Path(raw_path).resolve()
        if run_dir not in path.parents or not path.is_file():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}

    allowed_keys = {
        "execution_id",
        "pid",
        "pgid",
        "duration_seconds",
        "end_reason",
        "returncode",
        "termination_signal",
        "hard_kill_used",
        "stdout_truncated",
        "stderr_truncated",
        "resource_usage",
    }
    return {
        key: payload.get(key)
        for key in allowed_keys
        if key in payload
    }


def _execution_status_items(
    state: dict,
    stage_errors: list[StageError],
) -> list[str]:
    status = state.get("final_status", "unknown")
    if status == "succeeded":
        return [
            "Verifier 确认执行协议证据完整，论文程序以 return code 0 退出。",
            "该状态不自动等价于论文科学结果已经复现。",
        ]
    if status == "failed":
        return [
            "论文程序返回非零状态或触发资源预算，可进入 Debug/Repair。",
            "该结果不自动等价于论文结论无法复现。",
        ]
    if status == "cancelled":
        return [
            "用户请求取消了受监管执行。",
            "取消不是论文复现失败，系统不会自动进入修复。",
        ]
    if status == "policy_blocked":
        return ["Action 请求的执行能力不被 Execution Profile 允许。"]
    if status == "environment_blocked":
        return ["执行环境阻止了子进程启动，应先修复环境配置。"]
    if status == "agent_failed":
        return [
            "Supervisor 或 Agent 执行基础设施失败。",
            "该状态不代表论文程序本身失败。",
        ]

    if any(error.category == "paper_program" for error in stage_errors):
        return ["论文程序发生运行失败，Agent 已保留日志和调试证据。"]
    if any(error.terminal for error in stage_errors):
        return ["当前 run 因终止性阶段错误结束，请先处理 Error Report。"]
    return []


def _render_final_report(state: dict) -> str:
    """
    将 state 中已经积累的结构化结果组织成最终 markdown 报告。
    """

    lines: list[str] = ["# 最终报告", ""]

    # 1. 基本信息
    lines += _render_section(
        "运行摘要",
        [
            f"论文路径：`{state.get('paper_path', '')}`" if state.get("paper_path") else "论文路径：不适用",
            f"仓库路径：`{state.get('repo_path', '')}`" if state.get("repo_path") else "仓库路径：不适用",
            f"实验目标：{state.get('experiment_goal', '不适用')}",
            f"最终状态：`{state.get('final_status', 'unknown')}`",
            f"用户审批：`{state.get('user_approval', 'not_recorded')}`",
        ],
    )

    stage_errors = [
        StageError.model_validate(item)
        for item in state.get("stage_errors", [])
    ]
    error_items: list[str] = []
    for error in stage_errors:
        error_items.extend(
            [
                (
                    f"`{error.code}`：category=`{error.category}`，"
                    f"stage=`{error.stage}`，terminal=`{error.terminal}`"
                ),
                f"说明：{error.message}",
            ]
        )
    lines += _render_section("结构化错误摘要", error_items)

    lines += _render_section(
        "结果解释",
        _execution_status_items(state, stage_errors),
    )

    # 2. 论文摘要信息
    paper_summary = state.get("paper_summary", {})
    lines += _render_section(
        "论文摘要",
        [
            f"标题：{paper_summary.get('title', '不适用')}",
            f"研究问题：{paper_summary.get('research_problem', '不适用')}",
            f"核心思路：{paper_summary.get('core_idea', '不适用')}",
        ],
    )

    # 3. RepoMap 摘要
    repo_map = state.get("repo_map", {})
    important_files = repo_map.get("important_files", [])
    lines += _render_section(
        "仓库要点",
        [f"重要文件：`{path}`" for path in important_files[:10]],
    )

    # 4. 映射结果摘要
    mappings = state.get("paper_code_mapping", [])
    mapping_items: list[str] = []
    for mapping in mappings:
        module_name = mapping.get("module_name", "未知模块")
        category = mapping.get(
            "target_category",
            "core_method",
        )
        label = f"[{category}] {module_name}"
        candidates = mapping.get("candidates", [])
        if not candidates:
            mapping_items.append(
                f"{label}：未找到有把握的代码候选"
            )
            continue

        top_candidate = candidates[0]
        mapping_items.append(
            f"{label}：首选候选为 "
            f"`{top_candidate.get('file_path', '不适用')}`"
            f"（置信度={top_candidate.get('confidence', 'unknown')}）"
        )
    lines += _render_section("论文与代码映射摘要", mapping_items)

    # 5. 实验计划摘要
    plan = state.get("experiment_plan", {})
    run_commands = state.get("run_commands", [])
    lines += _render_section(
        "实验计划摘要",
        [
            f"目标：{plan.get('goal', '不适用')}",
            f"环境步骤数：{len(plan.get('environment_steps', []))}",
            f"数据步骤数：{len(plan.get('data_steps', []))}",
            f"训练步骤数：{len(plan.get('train_steps', []))}",
            f"评估步骤数：{len(plan.get('eval_steps', []))}",
            f"运行命令数：{len(run_commands)}",
        ],
    )

    # 6. 审批与待执行动作
    pending_action = state.get("pending_action")
    review_items: list[str] = []
    if pending_action:
        review_items.append(f"待执行动作类型：`{pending_action.get('action_type', 'unknown')}`")
        review_items.append(f"待执行程序：`{pending_action.get('program', '')}`")
        review_items.append(f"待执行参数：`{pending_action.get('args', '')}`")
        review_items.append(f"动作来源：`{pending_action.get('source', 'unknown')}`")
    human_feedback = state.get("human_feedback")
    if human_feedback:
        review_items.append(f"人工反馈：{human_feedback}")
    lines += _render_section("审批摘要", review_items)

    # 7. 执行结果摘要
    execution_result = state.get("execution_result", {})
    execution_items: list[str] = []
    if execution_result:
        execution_items.extend(
            [
                f"执行是否成功：`{execution_result.get('ok')}`",
                f"返回码：`{execution_result.get('returncode')}`",
                f"执行日志路径：`{state.get('execution_log_path', '')}`"
                if state.get("execution_log_path")
                else "执行日志路径：不适用",
            ]
        )
    # Phase 43：执行事实和验证结论分开展示。
    verification = state.get("execution_verification") or {}
    verification_items: list[str] = []
    if verification:
        verification_items.extend(
            [
                (
                    "验证作用域："
                    f"`{verification.get('claim_scope', 'unknown')}`"
                ),
                (
                    "验证结论："
                    f"`{verification.get('verdict', 'unknown')}`"
                ),
                (
                    "投影终态："
                    f"`{verification.get('projected_final_status', 'unknown')}`"
                ),
                (
                    "Evidence SHA-256："
                    f"`{verification.get('evidence_sha256', '')}`"
                ),
                (
                    "Verification SHA-256："
                    f"`{verification.get('verification_sha256', '')}`"
                ),
                str(verification.get("summary", "")),
            ]
        )
    lines += _render_section(
        "Execution Verification",
        verification_items,
    )
    lines += _render_section("执行摘要", execution_items)

    process_record = _load_process_record_summary(state)
    resource_usage = (
        state.get("execution_resource_usage")
        or process_record.get("resource_usage")
        or execution_result.get("resource_usage")
        or {}
    )
    preflight_report = state.get("preflight_report", {})
    supervision_items: list[str] = []
    execution_id = (
        state.get("active_execution_id")
        or process_record.get("execution_id")
    )
    if execution_id:
        supervision_items.extend(
            [
                f"Execution ID：`{execution_id}`",
                (
                    "Backend / Profile："
                    f"`{execution_result.get('execution_backend', 'unknown')}` / "
                    f"`{state.get('execution_profile_id', 'unknown')}`"
                ),
                (
                    "End Reason："
                    f"`{state.get('execution_end_reason') or process_record.get('end_reason') or 'unknown'}`"
                ),
                f"PID / PGID：`{process_record.get('pid')}` / `{process_record.get('pgid')}`",
                f"Duration seconds：`{process_record.get('duration_seconds')}`",
                f"Peak RSS bytes：`{resource_usage.get('peak_rss_bytes', 0)}`",
                f"CPU seconds：`{resource_usage.get('total_cpu_seconds', 0)}`",
                f"Process peak：`{resource_usage.get('peak_process_count', 0)}`",
                f"Observed write bytes：`{resource_usage.get('total_write_bytes', 0)}`",
                f"Log truncated：`{execution_result.get('log_truncated', False)}`",
                (
                    "Termination signal / hard kill："
                    f"`{process_record.get('termination_signal')}` / "
                    f"`{process_record.get('hard_kill_used', False)}`"
                ),
                (
                    "Capability enforcement mode："
                    f"`{preflight_report.get('execution_enforcement_mode', 'unknown')}`"
                ),
            ]
        )
        pending_action = state.get("pending_action") or {}
        if pending_action.get("network_access", "none") == "none":
            supervision_items.append(
                "Action 未声明网络能力；当前 local/conda backend "
                "未提供 OS 级网络隔离。"
            )
        supervision_items.append(
            "可写路径经过策略检查；当前 local/conda backend "
            "未提供 OS 级文件系统隔离。"
        )
    lines += _render_section(
        "Execution Supervision",
        supervision_items,
    )

    # 8. Preflight 摘要
    preflight_report = state.get("preflight_report", {})
    preflight_items: list[str] = []
    if preflight_report:
        preflight_items.append(
            f"是否可执行：`{preflight_report.get('ready_to_execute', False)}`"
        )
        preflight_items.append(
            f"阻塞项数量：{len(preflight_report.get('blocking_items', []))}"
        )

        for name in preflight_report.get("blocking_items", [])[:5]:
            preflight_items.append(f"阻塞项：{name}")

    lines += _render_section("预检摘要", preflight_items)

    # 9. Debug 结果摘要
    debug_report = state.get("debug_report", {})
    debug_items: list[str] = []
    if debug_report:
        debug_items.append(f"错误类型：`{debug_report.get('error_type', 'unknown')}`")
        for cause in debug_report.get("most_likely_causes", [])[:5]:
            debug_items.append(f"可能原因：{cause}")
    lines += _render_section("调试摘要", debug_items)

    # 10. Smoke 结果摘要
    smoke_report = state.get("smoke_test_report", {})
    smoke_items: list[str] = []
    if smoke_report:
        smoke_items.append(f"冒烟测试状态：`{smoke_report.get('status', 'unknown')}`")
        smoke_items.append(
            f"冒烟测试覆盖参数数量：{len(smoke_report.get('applied_overrides', []))}"
        )
        for item in smoke_report.get("applied_overrides", [])[:5]:
            smoke_items.append(f"覆盖参数：{item}")
    lines += _render_section("冒烟测试摘要", smoke_items)

    # 11. Repair 摘要
    repair_proposal = state.get("repair_proposal", {})
    repair_items: list[str] = []
    if repair_proposal:
        repair_items.append(f"修复类型：`{repair_proposal.get('kind', 'unknown')}`")
        repair_items.append(f"修复摘要：{repair_proposal.get('summary', '不适用')}")
    repair_attempt_count = state.get("repair_attempt_count")
    if repair_attempt_count is not None:
        repair_items.append(f"修复尝试次数：`{repair_attempt_count}`")
    lines += _render_section("修复摘要", repair_items)

    # 12. Repair Report
    file_repair_items: list[str] = []
    file_proposal = state.get("file_repair_proposal") or {}
    if file_proposal:
        file_repair_items.append(
            f"文件修复类型：`{file_proposal.get('kind', 'unknown')}`"
        )
        file_repair_items.append(
            f"文件修复摘要：{file_proposal.get('summary', '不适用')}"
        )

    pending_patch = state.get("pending_patch") or {}
    if pending_patch:
        file_repair_items.append(
            f"补丁 ID：`{pending_patch.get('patch_id', '不适用')}`"
        )
        file_repair_items.append(
            f"补丁 SHA-256：`{pending_patch.get('patch_sha256', '不适用')}`"
        )

    verification = state.get("patch_verification_report") or {}
    if verification:
        file_repair_items.extend(
            [
                f"Verification Status: `{verification.get('status')}`",
                f"Promotion Allowed: `{verification.get('promotion_allowed', False)}`",
                (
                    "Behavioral Checks: "
                    f"`{verification.get('behavioral_checks_passed', 0)}` / "
                    f"`{verification.get('behavioral_checks_run', 0)}`"
                ),
            ]
        )

    application = state.get("patch_application_record") or {}
    if application:
        file_repair_items.extend(
            [
                f"Application Status: `{application.get('status')}`",
                f"Recovered After Crash: `{application.get('recovered', False)}`",
                f"Journal: `{application.get('journal_path', 'N/A')}`",
            ]
        )

    lines += _render_section("文件修复总结", file_repair_items)


    # 13. 输出文件列表
    lines += _render_section(
        "输出文件",
        [f"`{path}`" for path in state.get("output_files", [])],
    )

    return "\n".join(lines)
