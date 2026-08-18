from __future__ import annotations

import ast
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from app.graph import (
    build_graph,
    route_after_executor,
    route_after_input_validation,
    route_after_smoke_test,
)


def test_terminal_input_error_routes_to_final_report():
    state = {
        "inputs_validated": False,
        "stage_errors": [
            {
                "error_id": "error_fixture",
                "code": "PAPER_NOT_FOUND",
                "category": "user",
                "stage": "input_validation",
                "message": "missing",
                "retryable": False,
                "terminal": True,
                "context": {},
                "occurred_at": "2026-07-24T00:00:00+00:00",
            }
        ],
    }

    assert route_after_input_validation(state) == "final_report"


def test_nonterminal_paper_error_still_routes_to_debug():
    state = {
        "final_status": "failed",
        "log_path": (
            "/data/tianshaoqi24/phase15-fixture/execution.log"
        ),
        "stage_errors": [
            {
                "error_id": "error_fixture",
                "code": "PAPER_PROGRAM_NONZERO_EXIT",
                "category": "paper_program",
                "stage": "executor",
                "message": "return code 1",
                "retryable": False,
                "terminal": False,
                "context": {},
                "occurred_at": "2026-07-24T00:00:00+00:00",
            }
        ],
    }

    assert route_after_executor(state) == "log_debug"


def test_terminal_cancellation_routes_directly_to_final_report():
    state = {
        "final_status": "cancelled",
        "log_path": "/tmp/cancelled.log",
        "stage_errors": [
            {
                "error_id": "error_cancelled",
                "code": "EXECUTION_CANCELLED",
                "category": "user",
                "stage": "executor",
                "message": "cancelled by user",
                "retryable": False,
                "terminal": True,
                "context": {},
                "occurred_at": "2026-07-27T00:00:00+00:00",
            }
        ],
    }

    assert route_after_executor(state) == "final_report"


def test_nonterminal_smoke_resource_error_routes_to_debug():
    state = {
        "smoke_test_status": "failed",
        "log_path": "/tmp/smoke-resource-limit.log",
        "stage_errors": [
            {
                "error_id": "error_resource",
                "code": "SMOKE_RESOURCE_LIMIT",
                "category": "paper_program",
                "stage": "smoke_test",
                "message": "memory limit exceeded",
                "retryable": False,
                "terminal": False,
                "context": {},
                "occurred_at": "2026-07-27T00:00:00+00:00",
            }
        ],
    }

    assert route_after_smoke_test(state) == "log_debug"


def test_compiled_graph_contains_input_and_prepare_nodes():
    graph = build_graph(checkpointer=MemorySaver())
    drawable = graph.get_graph()

    assert "input_validation" in drawable.nodes
    assert "command_selection_prepare" in drawable.nodes

    run_context_targets = {
        edge.target
        for edge in drawable.edges
        if edge.source == "run_context"
    }
    assert run_context_targets == {
        "input_validation",
        "final_report",
    }


def test_route_functions_are_not_defined_twice():
    graph_source = Path("app/graph.py").read_text(encoding="utf-8")
    module = ast.parse(graph_source)
    function_names = [
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    assert function_names.count("route_after_log_debug") == 1
    assert function_names.count("route_after_repair_planner") == 1


def test_compiled_graph_has_no_unconditional_log_debug_edge():
    graph = build_graph(checkpointer=MemorySaver())
    drawable = graph.get_graph()
    log_debug_edges = [
        edge for edge in drawable.edges if edge.source == "log_debug"
    ]

    assert {edge.target for edge in log_debug_edges} == {
        "repair_planner",
        "final_report",
    }
    assert all(edge.conditional for edge in log_debug_edges)