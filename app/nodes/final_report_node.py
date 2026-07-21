from app.config import settings

def final_report_node(state: dict) -> dict:
    report_text = _render_final_report(state)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = settings.output_dir / "final_report.md"
    report_path.write_text(report_text, encoding="utf-8")

    return {
        "final_report": report_text,
        "output_files": [
            *state.get("output_files", []),
            str(report_path),
        ],
    }

def _render_section(title: str, items: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    if not items:
        lines.append("- None")
        lines.append("")
        return lines

    for item in items:
        lines.append(f"- {item}")
    lines.append("")
    return lines

def _render_final_report(state: dict) -> str:
    """
    将 state 中已经积累的结构化结果组织成最终 markdown 报告。
    """

    lines: list[str] = ["# Final Report", ""]

    # 1. 基本信息
    lines += _render_section(
        "Run Summary",
        [
            f"Paper Path: `{state.get('paper_path', '')}`" if state.get("paper_path") else "Paper Path: N/A",
            f"Repo Path: `{state.get('repo_path', '')}`" if state.get("repo_path") else "Repo Path: N/A",
            f"Experiment Goal: {state.get('experiment_goal', 'N/A')}",
            f"Final Status: `{state.get('final_status', 'unknown')}`",
            f"User Approval: `{state.get('user_approval', 'not_recorded')}`",
        ],
    )

    # 2. 论文摘要信息
    paper_summary = state.get("paper_summary", {})
    lines += _render_section(
        "Paper Summary",
        [
            f"Title: {paper_summary.get('title', 'N/A')}",
            f"Research Problem: {paper_summary.get('research_problem', 'N/A')}",
            f"Core Idea: {paper_summary.get('core_idea', 'N/A')}",
        ],
    )

    # 3. RepoMap 摘要
    repo_map = state.get("repo_map", {})
    important_files = repo_map.get("important_files", [])
    lines += _render_section(
        "Repository Highlights",
        [f"Important File: `{path}`" for path in important_files[:10]],
    )

    # 4. 映射结果摘要
    mappings = state.get("paper_code_mapping", [])
    mapping_items: list[str] = []
    for mapping in mappings:
        module_name = mapping.get("module_name", "Unknown Module")
        candidates = mapping.get("candidates", [])
        if not candidates:
            mapping_items.append(f"{module_name}: no confident code candidate found")
            continue

        top_candidate = candidates[0]
        mapping_items.append(
            f"{module_name}: top candidate is `{top_candidate.get('file_path', 'N/A')}` "
            f"(confidence={top_candidate.get('confidence', 'unknown')})"
        )
    lines += _render_section("Paper-Code Mapping Summary", mapping_items)

    # 5. 实验计划摘要
    plan = state.get("experiment_plan", {})
    run_commands = state.get("run_commands", [])
    lines += _render_section(
        "Experiment Plan Summary",
        [
            f"Goal: {plan.get('goal', 'N/A')}",
            f"Environment Steps: {len(plan.get('environment_steps', []))}",
            f"Data Steps: {len(plan.get('data_steps', []))}",
            f"Train Steps: {len(plan.get('train_steps', []))}",
            f"Eval Steps: {len(plan.get('eval_steps', []))}",
            f"Run Commands: {len(run_commands)}",
        ],
    )

    # 6. 审批与待执行动作
    pending_action = state.get("pending_action")
    review_items: list[str] = []
    if pending_action:
        review_items.append(f"Pending Action Type: `{pending_action.get('action_type', 'unknown')}`")
        review_items.append(f"Pending Program: `{pending_action.get('program', '')}`")
        review_items.append(f"Pending Args: `{pending_action.get('args', '')}`")
        review_items.append(f"Action Source: `{pending_action.get('source', 'unknown')}`")
    human_feedback = state.get("human_feedback")
    if human_feedback:
        review_items.append(f"Human Feedback: {human_feedback}")
    lines += _render_section("Approval Summary", review_items)

    # 7. 执行结果摘要
    execution_result = state.get("execution_result", {})
    execution_items: list[str] = []
    if execution_result:
        execution_items.extend(
            [
                f"Execution OK: `{execution_result.get('ok')}`",
                f"Return Code: `{execution_result.get('returncode')}`",
                f"Execution Log Path: `{state.get('execution_log_path', '')}`"
                if state.get("execution_log_path")
                else "Execution Log Path: N/A",
            ]
        )
    lines += _render_section("Execution Summary", execution_items)

    # 8. Preflight 摘要
    preflight_report = state.get("preflight_report", {})
    preflight_items: list[str] = []
    if preflight_report:
        preflight_items.append(
            f"Ready To Execute: `{preflight_report.get('ready_to_execute', False)}`"
        )
        preflight_items.append(
            f"Blocking Items: {len(preflight_report.get('blocking_items', []))}"
        )

        for name in preflight_report.get("blocking_items", [])[:5]:
            preflight_items.append(f"Blocking: {name}")

    lines += _render_section("Preflight Summary", preflight_items)

    # 9. Debug 结果摘要
    debug_report = state.get("debug_report", {})
    debug_items: list[str] = []
    if debug_report:
        debug_items.append(f"Error Type: `{debug_report.get('error_type', 'unknown')}`")
        for cause in debug_report.get("most_likely_causes", [])[:5]:
            debug_items.append(f"Possible Cause: {cause}")
    lines += _render_section("Debug Summary", debug_items)

    # 10. Smoke 结果摘要
    smoke_report = state.get("smoke_test_report", {})
    smoke_items: list[str] = []
    if smoke_report:
        smoke_items.append(f"Smoke Status: `{smoke_report.get('status', 'unknown')}`")
        smoke_items.append(
            f"Smoke Overrides: {len(smoke_report.get('applied_overrides', []))}"
        )
        for item in smoke_report.get("applied_overrides", [])[:5]:
            smoke_items.append(f"Override: {item}")
    lines += _render_section("Smoke Test Summary", smoke_items)

    # 11. Repair 摘要
    repair_proposal = state.get("repair_proposal", {})
    repair_items: list[str] = []
    if repair_proposal:
        repair_items.append(f"Repair Kind: `{repair_proposal.get('kind', 'unknown')}`")
        repair_items.append(f"Repair Summary: {repair_proposal.get('summary', 'N/A')}")
    repair_attempt_count = state.get("repair_attempt_count")
    if repair_attempt_count is not None:
        repair_items.append(f"Repair Attempt Count: `{repair_attempt_count}`")
    lines += _render_section("Repair Summary", repair_items)

    # 12. 输出文件列表
    lines += _render_section(
        "Output Files",
        [f"`{path}`" for path in state.get("output_files", [])],
    )

    return "\n".join(lines)