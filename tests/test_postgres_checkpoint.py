from __future__ import annotations

"""共享 PostgreSQL Checkpoint 跨进程 handoff 测试。

验证 Phase 25 的核心 checkpoint 保证：Saver A 运行到 interrupt 后关闭，
Saver B 用同一 ``thread_id`` 恢复并继续执行，且前置节点不会重复执行。

这个测试不连接 Provider、不执行真实训练，只使用 LangGraph 原生
``interrupt``/``Command(resume=...)`` 语义。
"""

import os
from typing import TypedDict
from uuid import uuid4

import pytest
from langgraph.checkpoint.postgres import (
    PostgresSaver,
)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


pytestmark = pytest.mark.postgres


class HandoffState(TypedDict, total=False):
    prepared: int
    decision: str
    finished: bool


def _build_handoff_graph(
    *,
    checkpointer,
    prepare_calls: list[str],
):
    def prepare(state: HandoffState) -> dict:
        prepare_calls.append("prepare")
        return {
            "prepared": state.get("prepared", 0) + 1
        }

    def review(state: HandoffState) -> dict:
        del state
        value = interrupt({"kind": "test_review"})
        return {"decision": str(value)}

    def finish(state: HandoffState) -> dict:
        assert state["decision"] == "approved"
        return {"finished": True}

    builder = StateGraph(HandoffState)
    builder.add_node("prepare", prepare)
    builder.add_node("review", review)
    builder.add_node("finish", finish)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "review")
    builder.add_edge("review", "finish")
    builder.add_edge("finish", END)
    return builder.compile(checkpointer=checkpointer)


def _conn_string() -> str:
    """把 SQLAlchemy DSN 转为 PostgresSaver 可接受的格式。"""

    url = os.environ["TEST_DATABASE_URL"]
    return url.replace(
        "postgresql+psycopg://",
        "postgresql://",
    )


def test_second_graph_reads_first_graph_checkpoint():
    """Saver A interrupt -> Saver B resume，prepare 只执行一次。"""

    thread_id = f"handoff-{uuid4().hex}"
    config = {"configurable": {"thread_id": thread_id}}
    prepare_calls: list[str] = []

    with PostgresSaver.from_conn_string(
        _conn_string()
    ) as saver_a:
        saver_a.setup()
        graph_a = _build_handoff_graph(
            checkpointer=saver_a,
            prepare_calls=prepare_calls,
        )
        first = graph_a.invoke({}, config)
        assert "__interrupt__" in first

    with PostgresSaver.from_conn_string(
        _conn_string()
    ) as saver_b:
        graph_b = _build_handoff_graph(
            checkpointer=saver_b,
            prepare_calls=prepare_calls,
        )
        final = graph_b.invoke(
            Command(resume="approved"),
            config,
        )

    assert final["finished"] is True
    assert final["prepared"] == 1
    assert prepare_calls == ["prepare"]


def test_checkpoint_survives_saver_close_and_reopen():
    """关闭并重新打开 Saver 后，checkpoint 历史仍然可读。"""

    thread_id = f"persist-{uuid4().hex}"
    config = {"configurable": {"thread_id": thread_id}}
    prepare_calls: list[str] = []

    with PostgresSaver.from_conn_string(
        _conn_string()
    ) as saver_a:
        saver_a.setup()
        graph_a = _build_handoff_graph(
            checkpointer=saver_a,
            prepare_calls=prepare_calls,
        )
        graph_a.invoke({}, config)

    # Saver A 已经完全关闭。新 Saver 读取同一 thread 的 checkpoint。
    with PostgresSaver.from_conn_string(
        _conn_string()
    ) as saver_b:
        saver_b.setup()
        graph_b = _build_handoff_graph(
            checkpointer=saver_b,
            prepare_calls=prepare_calls,
        )
        state = graph_b.get_state(config)

    # prepare 已经执行过，checkpoint 中应有 prepared=1。
    assert state.values.get("prepared") == 1
    assert prepare_calls == ["prepare"]


def test_independent_threads_do_not_interfere():
    """不同 thread_id 的 checkpoint 完全隔离。"""

    thread_a = f"iso-a-{uuid4().hex}"
    thread_b = f"iso-b-{uuid4().hex}"
    calls_a: list[str] = []
    calls_b: list[str] = []

    with PostgresSaver.from_conn_string(
        _conn_string()
    ) as saver:
        saver.setup()
        graph_a = _build_handoff_graph(
            checkpointer=saver,
            prepare_calls=calls_a,
        )
        graph_b = _build_handoff_graph(
            checkpointer=saver,
            prepare_calls=calls_b,
        )
        graph_a.invoke(
            {},
            {"configurable": {"thread_id": thread_a}},
        )
        graph_b.invoke(
            {},
            {"configurable": {"thread_id": thread_b}},
        )
        state_a = graph_a.get_state(
            {"configurable": {"thread_id": thread_a}}
        )
        state_b = graph_b.get_state(
            {"configurable": {"thread_id": thread_b}}
        )

    assert state_a.values.get("prepared") == 1
    assert state_b.values.get("prepared") == 1
    assert calls_a == ["prepare"]
    assert calls_b == ["prepare"]
