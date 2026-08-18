from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

SqliteSaver = pytest.importorskip("langgraph.checkpoint.sqlite").SqliteSaver

class ReviewState(TypedDict, total=False):
    decision: str
    result: str

def review_node(state: ReviewState) -> ReviewState:
    response = interrupt({"messages": "approve this action?"})
    if isinstance(response, dict):
        decision = response.get("decision", "rejected")
    else:
        decision = str(response)
    
    return {"decision": decision}

def finish_node(state: ReviewState) -> ReviewState:
    if state.get("decision") == "approved":
        return {"result": "done"}
    return {"result": "blocked"}

def build_test_graph(db_path: Path):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)

    builder = StateGraph(ReviewState)
    builder.add_node("review", review_node)
    builder.add_node("finish", finish_node)
    builder.add_edge(START, "review")
    builder.add_edge("review", "finish")
    builder.add_edge("finish", END)

    graph = builder.compile(checkpointer=memory)
    return graph, conn

def test_sqlite_checkpoint_supports_resume_across_graph_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "langgraph.sqlite"
    config = {"configurable": {"thread_id": "thread-001"}}

    # 第一次 graph：触发 interrupt，把 checkpoint 写进 sqlite。
    graph1, conn1 = build_test_graph(db_path)
    try:
        graph1.invoke({}, config=config)
    finally:
        conn1.close()

    # 第二次 graph：模拟“新的命令 / 新的进程”重新打开同一个 sqlite 文件。
    graph2, conn2 = build_test_graph(db_path)
    try:
        result = graph2.invoke(
            Command(resume={"decision": "approved"}),
            config=config,
        )
    finally:
        conn2.close()

    assert result["decision"] == "approved"
    assert result["result"] == "done"