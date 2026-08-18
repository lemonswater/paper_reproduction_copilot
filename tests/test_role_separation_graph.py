from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from app.graph import (
    build_graph,
    route_after_execution_verifier,
    route_after_executor,
    route_after_patch_verdict,
    route_after_patch_verification_executor,
)


def test_new_execution_evidence_always_routes_to_verifier() -> None:
    state = {
        "execution_evidence": {
            "evidence_id": "exec-evidence"
        },
        # 即使某个旧字段错误地残留 succeeded，也必须先验证新 Evidence。
        "final_status": "succeeded",
    }

    assert route_after_executor(state) == "execution_verifier"


def test_verified_failure_routes_to_debug() -> None:
    state = {
        "execution_verification": {"verdict": "failed"},
        "final_status": "failed",
        "log_path": "/run/combined.log",
    }

    assert route_after_execution_verifier(state) == "log_debug"


def test_patch_evidence_routes_to_patch_verdict() -> None:
    state = {
        "patch_verification_evidence": {
            "evidence_id": "patch-evidence"
        }
    }

    assert route_after_patch_verification_executor(state) == (
        "patch_verdict"
    )


def test_only_verified_patch_routes_to_promotion() -> None:
    state = {
        "patch_verification_passed": True,
        "patch_verification_report": {
            "status": "behaviorally_verified",
            "promotion_allowed": True,
        },
    }

    assert route_after_patch_verdict(state) == (
        "patch_promotion_review"
    )


def test_compiled_graph_contains_authority_handoffs() -> None:
    graph = build_graph(checkpointer=MemorySaver())
    nodes = set(graph.get_graph().nodes)

    assert "executor" in nodes
    assert "execution_verifier" in nodes
    assert "patch_verification_executor" in nodes
    assert "patch_verdict" in nodes
    # 迁移期保留旧 Checkpoint 节点名。
    assert "patch_verifier" in nodes
