from langgraph.graph import END, START, StateGraph
from app.config import settings
from app.memory.checkpoint import build_checkpointer
from app.nodes.action_builder_node import action_builder_node
from app.nodes.code_search_node import code_search_node
from app.nodes.command_selection_node import command_selection_node
from app.nodes.executor_node import executor_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.final_report_node import final_report_node
from app.nodes.human_review_node import human_review_node
from app.nodes.log_debug_node import log_debug_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.preflight_check_node import preflight_check_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.risk_check_node import risk_check_node
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node
from app.nodes.smoke_test_node import smoke_test_node
from app.nodes.repair_action_builder_node import repair_action_builder_node
from app.nodes.repair_planner_node import repair_planner_node
from app.state import ReproductionState

def route_after_action_builder(state: ReproductionState) -> str:
    if state.get("pending_action"):
        return "risk_check"
    if state.get("log_path"):
        return "log_debug"
    return "final_report"

def route_after_risk_check(state: ReproductionState) -> str:
    if state.get("final_status") == "blocked":
        return "final_report"
    if state.get("requires_approval"):
        return "human_review"
    return "preflight_check"

def route_after_human_review(state: ReproductionState) -> str:
    decision = state.get("user_approval")
    if decision == "approved":
        return "preflight_check"
    return "final_report"

def route_after_preflight(state: ReproductionState) -> str:
    if state.get("preflight_passed"):
        return "smoke_test"
    return "final_report"

def route_after_smoke_test(state: ReproductionState) -> str:
    status = state.get("smoke_test_status")
    if status in {"passed", "skipped"}:
        return "executor"
    if status == "failed" and state.get("log_path"):
        return "log_debug"
    return "final_report"

def route_after_executor(state: ReproductionState) -> str:
    if state.get("final_status") == "failed" and state.get("log_path"):
        return "log_debug"
    return "final_report"

def route_after_log_debug(state: ReproductionState) -> str:
    attempts = int(state.get("repair_attempt_count", 0))
    if attempts >= settings.max_repair_attempts:
        return "final_report"
    return "repair_planner"

def route_after_repair_planner(state: ReproductionState) -> str:
    proposal = state.get("repair_proposal", {})
    if proposal.get("kind") == "edit_command" and proposal.get("repaired_command"):
        return "repair_action_builder"
    return "final_report"

def route_after_repair_action_builder(state: ReproductionState) -> str:
    if state.get("pending_action"):
        return "risk_check"
    return "final_report"

def build_graph():
    builder = StateGraph(ReproductionState)

    builder.add_node("run_context", run_context_node)
    builder.add_node("paper_reader", paper_reader_node)
    builder.add_node("method_extractor", method_extractor_node)
    builder.add_node("repo_scan", repo_scan_node)
    builder.add_node("code_search", code_search_node)
    builder.add_node("mapping", mapping_node)
    builder.add_node("experiment_plan", experiment_plan_node)
    builder.add_node("command_selection", command_selection_node)
    builder.add_node("action_builder", action_builder_node)
    builder.add_node("risk_check", risk_check_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("preflight_check", preflight_check_node)
    builder.add_node("smoke_test", smoke_test_node)
    builder.add_node("executor", executor_node)
    builder.add_node("log_debug", log_debug_node)
    builder.add_node("repair_planner", repair_planner_node)
    builder.add_node("repair_action_builder", repair_action_builder_node)
    builder.add_node("final_report", final_report_node)
    builder.add_node("run_manifest", run_manifest_node)


    builder.add_edge(START, "run_context")
    builder.add_edge("run_context", "paper_reader")
    builder.add_edge("paper_reader", "method_extractor")
    builder.add_edge("method_extractor", "repo_scan")
    builder.add_edge("repo_scan", "code_search")
    builder.add_edge("code_search", "mapping")
    builder.add_edge("mapping", "experiment_plan")
    builder.add_edge("experiment_plan", "command_selection")
    builder.add_edge("command_selection", "action_builder")

    builder.add_conditional_edges("action_builder", route_after_action_builder)
    builder.add_conditional_edges("risk_check", route_after_risk_check)
    builder.add_conditional_edges("human_review", route_after_human_review)
    builder.add_conditional_edges("preflight_check", route_after_preflight)
    builder.add_conditional_edges("smoke_test", route_after_smoke_test)
    builder.add_conditional_edges("executor", route_after_executor)
    builder.add_conditional_edges("log_debug", route_after_log_debug)
    builder.add_conditional_edges("repair_planner", route_after_repair_planner)
    builder.add_conditional_edges(
        "repair_action_builder",
        route_after_repair_action_builder,
    )

    builder.add_edge("log_debug", "final_report")
    builder.add_edge("final_report", "run_manifest")
    builder.add_edge("run_manifest", END)
    

    return builder.compile(checkpointer=build_checkpointer())