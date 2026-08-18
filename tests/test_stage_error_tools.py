from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.errors import GraphInterrupt

from app.tools.error_tools import (
    build_stage_error,
    guard_node,
    has_terminal_stage_error,
    persist_stage_errors,
    sanitize_error_message,
)


def test_persist_stage_error_writes_json_and_markdown(run_state):
    error = build_stage_error(
        stage="paper_reader",
        code="INPUT_NOT_FOUND",
        category="user",
        message="paper file does not exist",
        terminal=True,
    )

    result = persist_stage_errors(
        state=run_state,
        new_errors=[error],
    )

    assert result["final_status"] == "invalid_input"
    assert has_terminal_stage_error(result) is True
    assert (
        Path(run_state["run_dir"])
        / "reports"
        / "error_report.json"
    ).exists()
    assert (
        Path(run_state["run_dir"])
        / "reports"
        / "error_report.md"
    ).exists()


def test_nonterminal_paper_program_error_does_not_stop(run_state):
    error = build_stage_error(
        stage="executor",
        code="PAPER_PROGRAM_NONZERO_EXIT",
        category="paper_program",
        message="return code 1",
        terminal=False,
    )

    result = persist_stage_errors(
        state=run_state,
        new_errors=[error],
    )

    assert has_terminal_stage_error(result) is False
    assert "final_status" not in result


def test_guard_converts_unhandled_exception(run_state):
    def broken_node(state):
        raise RuntimeError("controlled failure")

    result = guard_node("broken_node", broken_node)(run_state)

    assert result["final_status"] == "agent_failed"
    assert result["active_stage_error"]["code"] == (
        "UNHANDLED_AGENT_EXCEPTION"
    )
    assert result["active_stage_error"]["stage"] == "broken_node"
    trace_path = result["active_stage_error"][
        "traceback_artifact_path"
    ]
    assert trace_path
    assert Path(trace_path).exists()


def test_guard_does_not_swallow_graph_interrupt(run_state):
    def interrupted_node(state):
        # 当前 LangGraph 版本的构造参数是 interrupts 序列。
        raise GraphInterrupt(())

    with pytest.raises(GraphInterrupt):
        guard_node(
            "interrupted_node",
            interrupted_node,
        )(run_state)


def test_error_message_redacts_secret_assignment():
    message = sanitize_error_message(
        "OPENAI_API_KEY=secret-value connection failed"
    )
    assert "secret-value" not in message
    assert "OPENAI_API_KEY=<redacted>" in message