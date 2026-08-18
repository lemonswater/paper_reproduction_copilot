"""Phase 26 §52: 双 root 跨 host handoff 测试。

在一台机器上用不同 workspace root 模拟两个 host，验证：
- prepare 节点只执行一次；
- run Artifact 被带到 host-b；
- repo commit 相同；
- resume 使用 host-b path。

不调用 Provider，也不需要真实 GPU。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.config import settings
from app.schemas import ArtifactRecord
from app.storage.local_blob_store import LocalBlobStore
from app.tools.artifact_tools import sha256_file
from app.workspace.materializer import WorkspaceMaterializer
from app.workspace.rebind import (
    build_workspace_state_update,
)
from app.workspace.schemas import (
    JobRequirements,
    WorkerCapabilities,
    WorkerIdentity,
)
from app.workspace.snapshot import WorkspaceSnapshotter
from tests.test_repo_capsule import _clean_repo


class SharedLocalBlobStore(LocalBlobStore):
    sharing_scope = "shared"


class HandoffState(TypedDict, total=False):
    run_dir: str
    repo_path: str
    paper_path: str
    workspace_binding: dict[str, Any]
    workspace_assignment_epoch: int
    workspace_manifest_id: str
    workspace_manifest_hash: str
    artifact_records: list[dict[str, Any]]
    run_commands: list[dict[str, Any]]
    prepared: int
    decision: str
    finished: bool
    finished_repo_path: str


def _worker(host: str, root: Path) -> WorkerIdentity:
    return WorkerIdentity(
        worker_id=f"worker-{host}",
        worker_session_id=f"session-{host}",
        host_id=host,
        pool="default",
        workspace_root=str(root.resolve()),
        capabilities=WorkerCapabilities(
            execution_profile_ids=["local"],
            execution_backends=["local"],
            execution_policy_hashes={"local": "a" * 64},
            cpu_count=8,
            memory_bytes=16 * 1024**3,
            workspace_free_bytes=100 * 1024**3,
        ),
    )


def _requirements() -> JobRequirements:
    return JobRequirements(
        execution_profile_id="local",
        execution_policy_hash="a" * 64,
        execution_backend="local",
    )


def test_safe_interrupt_handoff_between_distinct_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(
        settings, "workspace_staging_root", staging
    )
    monkeypatch.setattr(
        settings, "runs_dir", tmp_path / "legacy-runs"
    )
    monkeypatch.setattr(
        settings, "workspace_max_file_bytes", 1024**3
    )
    monkeypatch.setattr(
        settings, "workspace_max_total_bytes", 2 * 1024**3
    )

    source_repo = _clean_repo(tmp_path)
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"%PDF-1.4\nphase26\n")
    blob = SharedLocalBlobStore(tmp_path / "shared-blobs")
    snapshotter = WorkspaceSnapshotter(blob_store=blob)
    initial_manifest = snapshotter.snapshot_initial(
        job_id="job-handoff",
        run_id="run-handoff",
        paper_path=str(paper),
        repo_path=str(source_repo),
        log_path=None,
        source_host_id="host-a",
        external_data=[],
    )
    assert initial_manifest.portable is True

    host_a_root = tmp_path / "host-a-workspaces"
    monkeypatch.setattr(
        settings, "worker_workspace_root", host_a_root
    )
    materializer_a = WorkspaceMaterializer(blob_store=blob)
    binding_a = materializer_a.planned_binding(
        worker=_worker("host-a", host_a_root),
        manifest=initial_manifest,
        requirements=_requirements(),
        assignment_epoch=1,
        assignment_token="token-a",
    )
    binding_a = materializer_a.materialize(
        manifest=initial_manifest,
        binding=binding_a,
    )

    prepare_calls: list[str] = []

    def prepare(state: HandoffState) -> dict[str, Any]:
        prepare_calls.append(state["repo_path"])
        output = (
            Path(state["run_dir"]) / "analysis" / "prepared.txt"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "prepared once\n", encoding="utf-8"
        )
        relative = output.relative_to(
            Path(state["run_dir"])
        ).as_posix()
        record = ArtifactRecord(
            artifact_id="artifact-prepared",
            run_id="run-handoff",
            layer="analysis",
            relative_path=relative,
            absolute_path=str(output.resolve()),
            media_type="text/plain",
            sha256=sha256_file(output),
            size_bytes=output.stat().st_size,
            producer_node="prepare",
            created_at="2026-07-31T00:00:00+00:00",
        )
        return {
            "prepared": state.get("prepared", 0) + 1,
            "artifact_records": [record.model_dump()],
            "run_commands": [
                {
                    "command": "python train.py",
                    "cwd": state["repo_path"],
                }
            ],
        }

    def review(state: HandoffState) -> dict[str, Any]:
        del state
        return {
            "decision": str(
                interrupt({"kind": "command_selection"})
            )
        }

    def finish(state: HandoffState) -> dict[str, Any]:
        assert (
            Path(
                state["run_dir"],
                "analysis",
                "prepared.txt",
            ).read_text(encoding="utf-8")
            == "prepared once\n"
        )
        return {
            "finished": state["decision"] == "approved",
            "finished_repo_path": state["repo_path"],
        }

    builder = StateGraph(HandoffState)
    builder.add_node("prepare", prepare)
    builder.add_node("review", review)
    builder.add_node("finish", finish)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "review")
    builder.add_edge("review", "finish")
    builder.add_edge("finish", END)
    graph = builder.compile(checkpointer=MemorySaver())
    config = {
        "configurable": {
            "thread_id": "phase26-handoff"
        }
    }
    first = graph.invoke(
        {
            "run_dir": binding_a.run_dir,
            "repo_path": binding_a.repo_path,
            "paper_path": binding_a.paper_path,
            "workspace_binding": binding_a.model_dump(),
            "workspace_assignment_epoch": 1,
            "workspace_manifest_id": initial_manifest.manifest_id,
            "workspace_manifest_hash": initial_manifest.manifest_hash,
            "artifact_records": [],
        },
        config,
    )
    assert "__interrupt__" in first
    state_a = dict(graph.get_state(config).values)

    sealed = snapshotter.seal(
        job_id="job-handoff",
        run_id="run-handoff",
        run_dir=binding_a.run_dir,
        repo_path=binding_a.repo_path,
        paper_path=binding_a.paper_path,
        log_path=None,
        parent=initial_manifest,
        source_host_id="host-a",
        source_worker_session_id="session-host-a",
        artifact_records=state_a["artifact_records"],
        external_data=[],
        blocked_reasons=[],
    )
    assert sealed.portable is True

    host_b_root = tmp_path / "host-b-workspaces"
    assert host_b_root != host_a_root
    monkeypatch.setattr(
        settings, "worker_workspace_root", host_b_root
    )
    materializer_b = WorkspaceMaterializer(blob_store=blob)
    binding_b = materializer_b.planned_binding(
        worker=_worker("host-b", host_b_root),
        manifest=sealed,
        requirements=_requirements(),
        assignment_epoch=2,
        assignment_token="token-b",
    )
    binding_b = materializer_b.materialize(
        manifest=sealed,
        binding=binding_b,
    )
    assert binding_b.repo_path != binding_a.repo_path
    assert binding_b.run_dir != binding_a.run_dir

    update = build_workspace_state_update(
        state=state_a,
        new_binding=binding_b,
    )
    final = graph.invoke(
        Command(resume="approved", update=update),
        config,
    )

    assert final["finished"] is True
    assert final["finished_repo_path"] == binding_b.repo_path
    assert prepare_calls == [binding_a.repo_path]
    assert (
        Path(
            binding_b.run_dir,
            "analysis",
            "prepared.txt",
        ).is_file()
    )
