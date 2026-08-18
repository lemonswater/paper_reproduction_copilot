from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.authority.policy import role_guarded_node
from app.config import settings
from app.memory.checkpoint import build_checkpointer
from app.nodes.action_builder_node import action_builder_node
from app.nodes.code_search_node import code_search_node
from app.nodes.command_selection_node import (
    command_selection_node,
    command_selection_prepare_node,
)
from app.nodes.execution_verifier_node import (
    execution_verifier_node,
)
from app.nodes.executor_node import executor_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.file_repair_planner_node import file_repair_planner_node
from app.nodes.final_report_node import final_report_node
from app.nodes.human_review_node import human_review_node
from app.nodes.input_validation_node import input_validation_node
from app.nodes.log_debug_node import log_debug_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.patch_apply_node import patch_apply_node
from app.nodes.patch_builder_node import patch_builder_node
from app.nodes.patch_promotion_review_node import patch_promotion_review_node
from app.nodes.patch_review_node import patch_review_node
from app.nodes.patch_verdict_node import patch_verdict_node
from app.nodes.patch_verification_executor_node import (
    patch_verification_executor_node,
)
from app.nodes.patch_verifier_node import patch_verifier_node
from app.nodes.preflight_check_node import preflight_check_node
from app.nodes.repair_action_builder_node import repair_action_builder_node
from app.nodes.repair_planner_node import repair_planner_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.rerun_seed_node import rerun_seed_node
from app.nodes.risk_check_node import risk_check_node
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node
from app.nodes.smoke_test_node import smoke_test_node
from app.state import ReproductionState
from app.tools.error_tools import guard_node, has_terminal_stage_error


def route_after_action_builder(
    state: ReproductionState,
) -> Literal["risk_check", "log_debug", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    if state.get("pending_action"):
        return "risk_check"
    if state.get("log_path"):
        return "log_debug"
    return "final_report"

def route_after_risk_check(
    state: ReproductionState,
) -> Literal["final_report", "human_review", "preflight_check"]:
    if has_terminal_stage_error(state):
        return "final_report"
    if state.get("final_status") == "blocked":
        return "final_report"
    if state.get("requires_approval"):
        return "human_review"
    return "preflight_check"

def route_after_human_review(
    state: ReproductionState,
) -> Literal["preflight_check", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    decision = state.get("user_approval")
    if decision == "approved":
        return "preflight_check"
    return "final_report"

def route_after_preflight(
    state: ReproductionState,
) -> Literal["smoke_test", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    if state.get("preflight_passed"):
        return "smoke_test"
    return "final_report"

def route_after_smoke_test(
    state: ReproductionState,
) -> Literal["executor", "log_debug", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    status = state.get("smoke_test_status")
    if status in {"passed", "skipped"}:
        return "executor"
    if status == "failed" and state.get("log_path"):
        return "log_debug"
    return "final_report"

def route_after_executor(
    state: ReproductionState,
) -> Literal[
    "execution_verifier",
    "log_debug",
    "final_report",
]:
    """新 Evidence 必须进入 Verifier；后两项只兼容旧 checkpoint。"""

    if has_terminal_stage_error(state):
        return "final_report"

    if state.get("execution_evidence"):
        return "execution_verifier"

    # Phase 43 部署前已经执行完 Executor 的旧 Checkpoint 没有 Evidence。
    # 迁移期按旧状态收尾，不能要求它重新执行命令来补 Evidence。
    if (
        state.get("final_status") == "failed"
        and state.get("log_path")
    ):
        return "log_debug"
    return "final_report"


def route_after_execution_verifier(
    state: ReproductionState,
) -> Literal["log_debug", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    if (
        state.get("final_status") == "failed"
        and state.get("log_path")
    ):
        return "log_debug"
    return "final_report"

def route_after_repair_action_builder(
    state: ReproductionState,
) -> Literal["risk_check", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    if state.get("pending_action"):
        return "risk_check"
    return "final_report"

def route_after_log_debug(
    state: ReproductionState,
) -> Literal["repair_planner", "final_report"]:
    """
    command repair 和 file repair 使用独立预算。

    不能因为 command repair 已经用过一次，就直接阻止尚未尝试的
    file-level repair。
    """

    if has_terminal_stage_error(state):
        return "final_report"
    command_attempts = int(state.get("repair_attempt_count", 0))
    file_attempts = int(state.get("file_repair_attempt_count", 0))

    command_budget_available = (
        command_attempts < settings.max_repair_attempts
    )
    file_budget_available = (
        settings.enable_file_repair
        and file_attempts < settings.max_file_repair_attempts
    )

    if command_budget_available or file_budget_available:
        return "repair_planner"
    return "final_report"

def route_after_repair_planner(
    state: ReproductionState,
) -> Literal[
    "repair_action_builder",
    "file_repair_planner",
    "final_report",
]:
    if has_terminal_stage_error(state):
        return "final_report"
    proposal = state.get("repair_proposal") or {}

    command_budget_available = (
        int(state.get("repair_attempt_count", 0))
        < settings.max_repair_attempts
    )
    if (
        command_budget_available
        and proposal.get("kind") == "edit_command"
        and proposal.get("repaired_command")
    ):
        return "repair_action_builder"

    # command repair 判断需要改源码时，才进入单独的 file repair planner。
    if (
        settings.enable_file_repair
        and proposal.get("kind") == "manual_only"
        and (state.get("debug_report") or {}).get("related_files")
        and int(state.get("file_repair_attempt_count", 0))
        < settings.max_file_repair_attempts
    ):
        return "file_repair_planner"

    return "final_report"

def route_after_file_repair_planner(
    state: ReproductionState,
) -> Literal["patch_builder", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    proposal = state.get("file_repair_proposal") or {}
    if proposal.get("kind") == "patch" and proposal.get("edits"):
        return "patch_builder"
    return "final_report"


def route_after_patch_builder(
    state: ReproductionState,
) -> Literal["patch_review", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    if state.get("pending_patch") and state.get("pending_patch_hash"):
        return "patch_review"
    return "final_report"


def route_after_patch_review(
    state: ReproductionState,
) -> Literal["patch_verification_executor", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    if state.get("patch_approval") == "approved":
        return "patch_verification_executor"
    return "final_report"


def route_after_patch_verification_executor(
    state: ReproductionState,
) -> Literal["patch_verdict", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    if state.get("patch_verification_evidence"):
        return "patch_verdict"
    return "final_report"


def route_after_patch_verdict(
    state: ReproductionState,
) -> Literal["patch_promotion_review", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    report = state.get("patch_verification_report") or {}
    if (
        state.get("patch_verification_passed")
        and report.get("status") == "behaviorally_verified"
        and report.get("promotion_allowed") is True
    ):
        return "patch_promotion_review"
    return "final_report"


# Eval Case 和外部测试在一个迁移周期内仍可使用旧函数名。
def route_after_patch_verifier(
    state: ReproductionState,
) -> Literal["patch_promotion_review", "final_report"]:
    return route_after_patch_verdict(state)


def route_after_patch_promotion_review(
    state: ReproductionState,
) -> Literal["patch_apply", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    if state.get("patch_promotion_decision") == "approved":
        return "patch_apply"
    return "final_report"


def route_after_patch_apply(
    state: ReproductionState,
) -> Literal["risk_check", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    record = state.get("patch_application_record") or {}
    if record.get("status") == "applied" and state.get("pending_action"):
        return "risk_check"
    return "final_report"

def route_to_next_or_final(
    state: ReproductionState,
    *,
    next_node: str,
) -> str:
    """早期线性节点发生 terminal StageError 时统一转 Final Report。"""

    if has_terminal_stage_error(state):
        return "final_report"
    return next_node

def route_after_run_context(
    state: ReproductionState,
) -> Literal["input_validation", "final_report"]:
    if has_terminal_stage_error(state):
        return "final_report"
    return "input_validation"


def route_after_input_validation(
    state: ReproductionState,
) -> Literal["paper_reader", "final_report"]:
    if (
        has_terminal_stage_error(state)
        or not state.get("inputs_validated")
    ):
        return "final_report"
    return "paper_reader"

def build_graph(*, checkpointer=None):

    builder = StateGraph(ReproductionState)

    def add_guarded(
        builder: StateGraph,
        name: str,
        node: Callable,
    ) -> None:
        builder.add_node(name, guard_node(name, node))

    def add_role_guarded(
        builder: StateGraph,
        name: str,
        node: Callable,
        *,
        role: Literal["planner", "executor", "verifier"],
    ) -> None:
        """先做 authority 校验，再由统一 Error Guard 捕获违规。"""

        wrapped = role_guarded_node(
            node_name=name,
            role=role,
            node=node,
        )
        builder.add_node(name, guard_node(name, wrapped))

    # Analysis / control nodes：不是本阶段三个 Agent authority 之一。
    add_guarded(builder, "run_context", run_context_node)
    add_guarded(builder, "input_validation", input_validation_node)
    add_guarded(builder, "paper_reader", paper_reader_node)
    add_guarded(builder, "method_extractor", method_extractor_node)
    add_guarded(builder, "repo_scan", repo_scan_node)
    add_guarded(builder, "code_search", code_search_node)
    add_guarded(builder, "mapping", mapping_node)
    add_guarded(builder, "rerun_seed", rerun_seed_node)
    add_guarded(
        builder,
        "command_selection_prepare",
        command_selection_prepare_node,
    )
    add_guarded(
        builder,
        "command_selection",
        command_selection_node,
    )

    # Planner：只能构造 Proposal/Action 草稿。
    add_role_guarded(
        builder,
        "experiment_plan",
        experiment_plan_node,
        role="planner",
    )
    add_role_guarded(
        builder,
        "action_builder",
        action_builder_node,
        role="planner",
    )
    add_role_guarded(
        builder,
        "repair_planner",
        repair_planner_node,
        role="planner",
    )
    add_role_guarded(
        builder,
        "file_repair_planner",
        file_repair_planner_node,
        role="planner",
    )

    # 这两个节点会显式失效旧 Approval/Execution/Verification，属于
    # 确定性状态迁移控制，不向普通 Planner 放宽字段权限。
    add_guarded(
        builder,
        "repair_action_builder",
        repair_action_builder_node,
    )
    add_guarded(
        builder,
        "patch_builder",
        patch_builder_node,
    )

    # Deterministic policy / human authority.
    add_guarded(builder, "risk_check", risk_check_node)
    add_guarded(builder, "human_review", human_review_node)
    add_guarded(builder, "preflight_check", preflight_check_node)
    add_guarded(builder, "patch_review", patch_review_node)
    add_guarded(
        builder,
        "patch_promotion_review",
        patch_promotion_review_node,
    )

    # Executor：启动进程或收集 Patch 检查 Evidence。
    add_role_guarded(
        builder,
        "smoke_test",
        smoke_test_node,
        role="executor",
    )
    add_role_guarded(
        builder,
        "executor",
        executor_node,
        role="executor",
    )
    add_role_guarded(
        builder,
        "patch_verification_executor",
        patch_verification_executor_node,
        role="executor",
    )
    # 旧 checkpoint 节点名仍指向相同 Executor 行为。
    add_role_guarded(
        builder,
        "patch_verifier",
        patch_verifier_node,
        role="executor",
    )

    # Verifier：只能读取事实并形成限定作用域结论。
    add_role_guarded(
        builder,
        "execution_verifier",
        execution_verifier_node,
        role="verifier",
    )
    add_role_guarded(
        builder,
        "patch_verdict",
        patch_verdict_node,
        role="verifier",
    )

    add_guarded(builder, "log_debug", log_debug_node)

    # patch_apply 是 Phase 14 已有的专用事务控制节点：它既写仓库，
    # 又必须失效旧 Action/Approval。第一版不套用通用 Executor Contract，
    # 继续由 Patch Hash、Promotion Approval、Journal 和 Repository Lock 控制。
    add_guarded(builder, "patch_apply", patch_apply_node)

    add_guarded(builder, "final_report", final_report_node)
    add_guarded(builder, "run_manifest", run_manifest_node)

    builder.add_edge(START, "run_context")
    builder.add_conditional_edges(
        "run_context",
        route_after_run_context,
        {
            "input_validation": "input_validation",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "input_validation",
        route_after_input_validation,
        {
            "paper_reader": "paper_reader",
            "final_report": "final_report",
        },
    )
    for source, target in [
        ("paper_reader", "method_extractor"),
        ("method_extractor", "repo_scan"),
        ("repo_scan", "code_search"),
        ("code_search", "mapping"),
        ("mapping", "experiment_plan"),
        ("experiment_plan", "rerun_seed"),
        ("rerun_seed", "command_selection_prepare"),
        ("command_selection_prepare", "command_selection"),
        ("command_selection", "action_builder"),
    ]:
        builder.add_conditional_edges(
            source,
            lambda state, next_node=target: route_to_next_or_final(
                state,
                next_node=next_node,
            ),
            {
                target: target,
                "final_report": "final_report",
            },
        )
    builder.add_conditional_edges(
        "action_builder",
        route_after_action_builder,
        {
            "risk_check": "risk_check",
            "log_debug": "log_debug",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "risk_check",
        route_after_risk_check,
        {
            "final_report": "final_report",
            "human_review": "human_review",
            "preflight_check": "preflight_check",
        },
    )
    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "preflight_check": "preflight_check",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "preflight_check",
        route_after_preflight,
        {
            "smoke_test": "smoke_test",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "smoke_test",
        route_after_smoke_test,
        {
            "executor": "executor",
            "log_debug": "log_debug",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "execution_verifier": "execution_verifier",
            # 以下两个只用于 legacy checkpoint 路由。
            "log_debug": "log_debug",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "execution_verifier",
        route_after_execution_verifier,
        {
            "log_debug": "log_debug",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "log_debug",
        route_after_log_debug,
        {
            "repair_planner": "repair_planner",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "repair_planner",
        route_after_repair_planner,
        {
            "repair_action_builder": "repair_action_builder",
            "file_repair_planner": "file_repair_planner",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "repair_action_builder",
        route_after_repair_action_builder,
        {
            "risk_check": "risk_check",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "file_repair_planner",
        route_after_file_repair_planner,
        {
            "patch_builder": "patch_builder",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_builder",
        route_after_patch_builder,
        {
            "patch_review": "patch_review",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_review",
        route_after_patch_review,
        {
            "patch_verification_executor": (
                "patch_verification_executor"
            ),
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_verification_executor",
        route_after_patch_verification_executor,
        {
            "patch_verdict": "patch_verdict",
            "final_report": "final_report",
        },
    )
    # 只服务旧 checkpoint 中保存的 next=patch_verifier。
    builder.add_conditional_edges(
        "patch_verifier",
        route_after_patch_verification_executor,
        {
            "patch_verdict": "patch_verdict",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_verdict",
        route_after_patch_verdict,
        {
            "patch_promotion_review": "patch_promotion_review",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_promotion_review",
        route_after_patch_promotion_review,
        {
            "patch_apply": "patch_apply",
            "final_report": "final_report",
        },
    )
    builder.add_conditional_edges(
        "patch_apply",
        route_after_patch_apply,
        {
            "risk_check": "risk_check",
            "final_report": "final_report",
        },
    )

    builder.add_edge("final_report", "run_manifest")
    builder.add_edge("run_manifest", END)

    selected_checkpointer = (
        checkpointer
        if checkpointer is not None
        else build_checkpointer()
    )
    return builder.compile(checkpointer=selected_checkpointer)
