from __future__ import annotations

"""Phase 26 §49: Path rebind 与 atomic resume 测试。"""

from datetime import datetime, timezone
from typing import TypedDict

import pytest
from langgraph.checkpoint.memory import (
    MemorySaver,
)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.workspace.errors import (
    WorkspaceNotPortableError,
)
from app.workspace.rebind import (
    build_workspace_state_update,
)
from app.workspace.schemas import WorkspaceBinding


class _RebindState(TypedDict, total=False):
    path: str
    prepared: bool
    decision: str
    finished: bool
    finished_path: str


def _binding(
    *,
    host: str,
    epoch: int,
) -> WorkspaceBinding:
    root = (
        f"/data/workspaces/{host}/job/epochs/{epoch}"
    )
    now = datetime.now(
        timezone.utc
    ).isoformat()
    return WorkspaceBinding(
        assignment_id=(
            f"assignment-{host}-{epoch}"
        ),
        assignment_epoch=epoch,
        assignment_token=(
            f"token-{host}-{epoch}"
        ),
        job_id="job-test",
        run_id="run-test",
        manifest_id=f"manifest-{epoch}",
        manifest_hash=(
            "a" if epoch == 1 else "b"
        )
        * 64,
        manifest_generation=epoch - 1,
        worker_session_id=f"session-{host}",
        host_id=host,
        workspace_root=root,
        run_dir=f"{root}/run",
        repo_path=f"{root}/repo",
        paper_path=f"{root}/source/paper.pdf",
        log_path=None,
        status="ready",
        created_at=now,
        updated_at=now,
    )


def test_rebind_known_paths_without_mutating_plain_text() -> None:
    old = _binding(host="host-a", epoch=1)
    new = _binding(host="host-b", epoch=2)
    state = {
        "workspace_binding": old.model_dump(),
        "run_dir": old.run_dir,
        "repo_path": old.repo_path,
        "paper_path": old.paper_path,
        "repo_index_path": (
            f"{old.run_dir}/analysis/repo_index.json"
        ),
        "run_commands": [
            {
                "command": "python train.py",
                "cwd": old.repo_path,
            }
        ],
        "paper_summary": {
            "plain_text": (
                f"example path: {old.repo_path}"
            )
        },
    }

    update = build_workspace_state_update(
        state=state,
        new_binding=new,
    )

    assert update["repo_path"] == new.repo_path
    assert update["repo_index_path"].startswith(
        new.run_dir
    )
    assert (
        update["run_commands"][0]["cwd"]
        == new.repo_path
    )
    # 普通 LLM/Evidence 文本不在 update 中，不能被全局替换。
    assert "paper_summary" not in update


def test_command_text_with_old_absolute_path_blocks_handoff() -> None:
    old = _binding(host="host-a", epoch=1)
    new = _binding(host="host-b", epoch=2)
    state = {
        "workspace_binding": old.model_dump(),
        "run_commands": [
            {
                "command": (
                    f"python {old.repo_path}/train.py"
                ),
                "cwd": old.repo_path,
            }
        ],
    }
    with pytest.raises(
        WorkspaceNotPortableError,
        match="old_absolute_path",
    ):
        build_workspace_state_update(
            state=state,
            new_binding=new,
        )


def test_command_update_and_resume_are_atomic() -> None:
    prepare_calls: list[str] = []

    def prepare(state: _RebindState) -> dict:
        prepare_calls.append(state["path"])
        return {"prepared": True}

    def review(state: _RebindState) -> dict:
        del state
        return {
            "decision": interrupt({"kind": "review"})
        }

    def finish(state: _RebindState) -> dict:
        return {
            "finished_path": state["path"],
            "finished": (
                state["decision"] == "approved"
            ),
        }

    builder = StateGraph(_RebindState)
    builder.add_node("prepare", prepare)
    builder.add_node("review", review)
    builder.add_node("finish", finish)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "review")
    builder.add_edge("review", "finish")
    builder.add_edge("finish", END)
    graph = builder.compile(
        checkpointer=MemorySaver()
    )
    config = {
        "configurable": {
            "thread_id": "atomic-rebind"
        }
    }

    graph.invoke({"path": "/host-a/repo"}, config)
    final = graph.invoke(
        Command(
            resume="approved",
            update={"path": "/host-b/repo"},
        ),
        config,
    )

    assert final["finished"] is True
    assert final["finished_path"] == "/host-b/repo"
    assert prepare_calls == ["/host-a/repo"]
