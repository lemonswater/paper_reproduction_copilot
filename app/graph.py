from langgraph.graph import END, START, StateGraph

from app.state import ReproductionState
from app.memory.checkpoint import build_checkpointer
from app.nodes.code_search_node import code_search_node
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.log_debug_node import log_debug_node
from app.nodes.human_review_node import human_review_node
from app.nodes.risk_check_node import risk_check_node

def route_after_plan(state: ReproductionState) -> str:
    if state.get("pending_action"):
        return "risk_check"
    if state.get("log_path"):
        return "log_debug"
    return END

def route_after_risk_check(state: ReproductionState) -> str:
    if state.get("requires_approval"):
        return "human_review"
    return END

def build_graph():
    builder = StateGraph(ReproductionState)

    builder.add_node("paper_reader", paper_reader_node)
    builder.add_node("method_extractor", method_extractor_node)
    builder.add_node("repo_scan", repo_scan_node)
    builder.add_node("code_search", code_search_node)
    builder.add_node("mapping", mapping_node)
    builder.add_node("experiment_plan", experiment_plan_node)
    builder.add_node("log_debug", log_debug_node)
    builder.add_node("risk_check", risk_check_node)
    builder.add_node("human_review", human_review_node)


    builder.add_edge(START, "paper_reader")
    builder.add_edge("paper_reader", "method_extractor")
    builder.add_edge("method_extractor", "repo_scan")
    builder.add_edge("repo_scan", "code_search")
    builder.add_edge("code_search", "mapping")
    builder.add_edge("mapping", "experiment_plan")
    builder.add_conditional_edges("experiment_plan", route_after_plan)
    builder.add_conditional_edges("risk_check", route_after_risk_check)
    builder.add_edge("log_debug", END)
    builder.add_edge("human_review", END)

    return builder.compile(checkpointer=build_checkpointer())