from __future__ import annotations

import ipaddress
import json
import socket
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import typer
from langgraph.types import Command
from rich import print

from app.comparison.factory import build_comparison_service
from app.comparison.schemas import ComparisonCreateRequest
from app.comparison.service import build_command_snapshot
from app.config import settings
from app.rerun.factory import build_rerun_service
from app.rerun.schemas import (
    RerunArgumentEdit,
    RerunProposalCancelRequest,
    RerunProposalCreateRequest,
    RerunProposalSubmitRequest,
)
from app.execution.cancellation import (
    list_runtime_records,
    request_run_cancellation,
)
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.graph import build_graph
from app.interaction.artifacts import (
    read_graph_state,
)
from app.job_runtime.errors import (
    JobStoreError,
)
from app.job_runtime.schemas import JobRequest
from app.job_runtime.service import (
    build_job_service,
)
from app.job_runtime.worker import JobWorker
from app.memory import checkpoint
from app.memory.checkpoint import (
    build_checkpointer,
    setup_checkpointer,
)
from app.model import get_chat_model
from app.nodes.code_search_node import code_search_node
from app.nodes.command_selection_node import (
    compute_run_commands_hash,
    ensure_command_selection_input_file,
)
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.final_report_node import final_report_node
from app.nodes.log_debug_node import log_debug_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.preflight_check_node import preflight_check_node
from app.nodes.repair_planner_node import repair_planner_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node
from app.nodes.smoke_test_node import smoke_test_node
from app.observability.context import (
    bind_telemetry_context,
)
from app.observability.json_logging import (
    configure_structured_logging,
)
from app.observability.readiness import (
    ReadinessProbe,
    ReadinessService,
)
from app.observability.runtime import (
    build_telemetry_runtime,
)
from app.persistence.database import ping_database
from app.retrieval import (
    cosine_similarity,
    get_embedding_backend,
)
from app.schemas import ExperimentPlan, StructuredOutputProbe
from app.storage.factory import (
    build_artifact_storage,
)
from app.tools.action_tools import build_run_action_from_command, compute_action_hash
from app.tools.error_tools import (
    exception_to_stage_error_update,
    guard_node,
    has_terminal_stage_error,
    sanitize_error_message,
)
from app.tools.patch_tools import remove_patch_worktree
from app.tools.preflight_tools import build_preflight_action_from_command
from app.model_routing.factory import build_model_gateway
from app.model_routing.identity import sha256_text
from app.model_routing.schemas import ModelRouteRequest
from app.tools.structured_output_tools import (
    invoke_structured_with_retry,
    write_structured_output_trace,
)


def _initialize_cli_run(
    *,
    task_id: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    """
    read-paper、scan-repo 等直接节点命令也必须有独立 run。
    """

    state = {
        "task_id": task_id,
        "output_files": [],
        "artifact_records": [],
        "stage_errors": [],
        **values,
    }
    state.update(run_context_node(state))
    return state

def _run_cli_pipeline(
    state: dict[str, Any],
    stages: list[tuple[str, Callable]],
) -> dict[str, Any]:
    """
    直接 CLI 也复用 Graph 的错误边界，并在结束时生成报告和 Manifest。
    """

    for stage_name, node in stages:
        state.update(guard_node(stage_name, node)(state))
        if has_terminal_stage_error(state):
            break

    if not state.get("final_status"):
        state["final_status"] = "succeeded"

    state.update(final_report_node(state))
    state.update(run_manifest_node(state))
    return state

def _resolve_run_dir_for_control(
    *,
    run_id: str | None,
    thread_id: str | None,
) -> Path:
    if bool(run_id) == bool(thread_id):
        raise typer.BadParameter(
            "必须且只能提供 --run-id 或 --thread-id"
        )

    if run_id:
        if Path(run_id).name != run_id or run_id in {".", ".."}:
            raise typer.BadParameter("无效 run_id")
        run_dir = (settings.runs_dir / run_id).resolve()
    else:
        graph = build_graph()
        snapshot = graph.get_state(
            {"configurable": {"thread_id": thread_id}}
        )
        raw_run_dir = snapshot.values.get("run_dir")
        if not raw_run_dir:
            raise typer.BadParameter(
                f"thread_id={thread_id} 没有 run_dir"
            )
        run_dir = Path(raw_run_dir).resolve()

    runs_root = settings.runs_dir.resolve()
    if run_dir == runs_root or runs_root not in run_dir.parents:
        raise typer.BadParameter("run_dir 位于 RUNS_DIR 之外")
    if not run_dir.is_dir():
        raise typer.BadParameter(f"run_dir 不存在：{run_dir}")
    return run_dir


# CLI 启动即配置结构化日志。
if settings.structured_logging_enabled:
    try:
        configure_structured_logging()
    except Exception:
        pass  # 日志配置失败不阻止 CLI

_CLI_TELEMETRY_RUNTIME = None


def _cli_telemetry():
    global _CLI_TELEMETRY_RUNTIME
    if _CLI_TELEMETRY_RUNTIME is None:
        _CLI_TELEMETRY_RUNTIME = build_telemetry_runtime()
    return _CLI_TELEMETRY_RUNTIME


app = typer.Typer(help="论文复现助手")

@app.command()
def version():
    print("[green]paper-reproduction-copilot 0.1.0[/green]")

@app.command()
def init_outputs():
    Path("outputs").mkdir(exist_ok=True)
    print("[green]outputs/ 已准备就绪[/green]")

@app.command("index-paper")
def index_paper_command(paper_path: str):
    """只建立论文 block/section 索引，不调用 LLM。"""

    state = _initialize_cli_run(
        task_id="index-paper",
        values={"paper_path": paper_path},
    )
    state = _run_cli_pipeline(
        state,
        [("paper_reader", paper_reader_node)],
    )

    document = state.get("paper_document") or {}
    print(
        {
            "run_id": state["run_id"],
            "run_dir": state["run_dir"],
            "final_status": state["final_status"],
            "document_id": document.get("document_id"),
            "pages": (
                f"{document.get('indexed_page_count', 0)}/"
                f"{document.get('page_count', 0)}"
            ),
            "blocks": document.get("block_count", 0),
            "sections": document.get("section_count", 0),
            "paper_parse_report_path": state.get(
                "paper_parse_report_path"
            ),
            "run_manifest_path": state.get("run_manifest_path"),
        }
    )

    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)

@app.command()
def read_paper(paper_path: str):
    state = _initialize_cli_run(
        task_id="read-paper",
        values={"paper_path": paper_path},
    )
    state = _run_cli_pipeline(
        state,
        [
            ("paper_reader", paper_reader_node),
            ("method_extractor", method_extractor_node),
        ],
    )
    print(
        {
            "run_id": state["run_id"],
            "run_dir": state["run_dir"],
            "final_status": state["final_status"],
        }
    )
    print(state["output_files"])
    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)

@app.command()
def scan_repo(repo_path: str):
    state = _initialize_cli_run(
        task_id="scan-repo",
        values={"repo_path": repo_path},
    )
    state = _run_cli_pipeline(
        state,
        [("repo_scan", repo_scan_node)],
    )
    print("[green]代码仓库扫描完成[/green]")
    print(
        {
            "run_id": state["run_id"],
            "run_dir": state["run_dir"],
            "final_status": state["final_status"],
            "run_manifest_path": state["run_manifest_path"],
        }
    )
    print(state["output_files"])
    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)

@app.command("probe-embedding")
def probe_embedding():
    """
    只发送两句无敏感测试文本，不读取或上传代码仓库。
    """

    backend = get_embedding_backend()
    vectors = backend.embed_documents(
        [
            "spatial temporal feature aggregation",
            "database transaction retry policy",
        ]
    )
    similarity = cosine_similarity(
        vectors[0],
        vectors[1],
    )
    print(
        {
            "provider_namespace": (
                backend
                .identity
                .provider_namespace
            ),
            "model": backend.identity.model,
            "dimensions": len(vectors[0]),
            "probe_similarity": similarity,
        }
    )

@app.command("retrieve-code")
def retrieve_code(
    repo_path: str,
    query: str,
    keyword: list[str] | None = typer.Option(
        None,
        "--keyword",
        "-k",
        help="可重复传入的精确检索词",
    ),
    dense: bool = typer.Option(
        False,
        "--dense/--no-dense",
        help=(
            "启用 Dense Retrieval；仍要求环境变量"
            " ALLOW_CODE_EMBEDDING_UPLOAD=true"
        ),
    ),
    require_dense: bool = typer.Option(
        False,
        "--require-dense/--allow-dense-fallback",
        help="Dense 失败时是否禁止降级 Sparse Hybrid",
    ),
):
    """
    运行 Hybrid Code Retrieval。

    --dense=false：
        不调用 Provider。

    --dense=true：
        可能把脱敏后的代码 chunk 发送给 Embedding Provider。
    """

    dense = dense or require_dense
    module_name = "ad_hoc_retrieval"
    state = _initialize_cli_run(
        task_id="retrieve-code",
        values={
            "repo_path": repo_path,
            "enable_dense_retrieval": dense,
            "dense_retrieval_required": (
                require_dense
            ),
            "method_modules": [
                {
                    "name": module_name,
                    "description": query,
                    "possible_keywords": (
                        keyword or []
                    ),
                    "evidence": [],
                }
            ],
        },
    )
    state = _run_cli_pipeline(
        state,
        [
            ("repo_scan", repo_scan_node),
            ("code_search", code_search_node),
        ],
    )

    pack = (
        state.get(
            "code_evidence_packs",
            {},
        ).get(module_name, {})
    )
    print("[bold]Hybrid code retrieval[/bold]")
    print(
        {
            "run_id": state.get("run_id"),
            "run_dir": state.get("run_dir"),
            "final_status": state.get(
                "final_status"
            ),
            "dense_requested": dense,
            "dense_required": require_dense,
            "repo_index_path": state.get(
                "repo_index_path"
            ),
            "semantic_index_manifest_path": (
                state.get(
                    "semantic_index_manifest_path"
                )
            ),
            "dense_report_path": (
                state.get(
                    "dense_retrieval_report_paths",
                    {},
                ).get(module_name)
            ),
            "evidence_pack_path": (
                state.get(
                    "code_evidence_pack_paths",
                    {},
                ).get(module_name)
            ),
        }
    )

    for rank, item in enumerate(
        pack.get("items", []),
        start=1,
    ):
        print(
            {
                "rank": rank,
                "file_path": item.get(
                    "file_path"
                ),
                "symbol": item.get("symbol"),
                "lines": (
                    f"{item.get('start_line')}-"
                    f"{item.get('end_line')}"
                ),
                "channels": item.get(
                    "retrieval_channels",
                    [],
                ),
                "score": item.get(
                    "fused_score"
                ),
                "evidence_id": item.get(
                    "evidence_id"
                ),
            }
        )

    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)

@app.command()
def map_code(paper_path: str, repo_path: str):
    state = _initialize_cli_run(
        task_id="map-code",
        values={
            "paper_path": paper_path,
            "repo_path": repo_path,
        },
    )
    state = _run_cli_pipeline(
        state,
        [
            ("paper_reader", paper_reader_node),
            ("method_extractor", method_extractor_node),
            ("repo_scan", repo_scan_node),
            ("code_search", code_search_node),
            ("mapping", mapping_node),
        ],
    )
    print("[green]论文与代码映射完成[/green]")
    print(
        {
            "run_id": state["run_id"],
            "run_dir": state["run_dir"],
            "final_status": state["final_status"],
            "run_manifest_path": state["run_manifest_path"],
        }
    )
    print(state["output_files"])
    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)

@app.command()
def plan_experiment(
    paper_path: str,
    repo_path: str,
    goal: str = "复现论文 main result"
):
    state = _initialize_cli_run(
        task_id="plan-experiment",
        values={
            "paper_path": paper_path,
            "repo_path": repo_path,
            "experiment_goal": goal,
        },
    )
    state = _run_cli_pipeline(
        state,
        [
            ("paper_reader", paper_reader_node),
            ("method_extractor", method_extractor_node),
            ("repo_scan", repo_scan_node),
            ("code_search", code_search_node),
            ("mapping", mapping_node),
            ("experiment_plan", experiment_plan_node),
        ],
    )
    print("[green]实验计划生成完成[/green]")
    print(
        {
            "run_id": state["run_id"],
            "run_dir": state["run_dir"],
            "final_status": state["final_status"],
            "run_manifest_path": state["run_manifest_path"],
        }
    )
    print(state["output_files"])
    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)

@app.command()
def run_graph(
    paper_path: str,
    repo_path: str,
    log_path: str | None = typer.Argument(None),
    thread_id: str = "demo_thread",
    goal: str = "复现论文 main result",
    execution_profile: str | None = typer.Option(
        None,
        "--execution-profile",
        help="受信任执行环境的 profile_id",
    )
):
    profile_id = execution_profile or settings.default_execution_profile
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "task_id": thread_id,
        "paper_path": paper_path,
        "repo_path": repo_path,
        "execution_profile_id": profile_id,
        "log_path": log_path,
        "experiment_goal": goal,
        "output_files": [],
        "artifact_records": [],
        "stage_errors": [],
        "inputs_validated": False,
        "step_count": 0,
        "max_steps": 20,
    }
    initial_state.update(run_context_node(initial_state))

    try:
        graph = build_graph()
        result = graph.invoke(initial_state, config=config)
    except Exception as exc:  # noqa: BLE001
        # CLI 边界必须把所有 Graph 基础设施异常持久化为报告。
        initial_state.update(
            exception_to_stage_error_update(
                state=initial_state,
                stage="cli.run_graph",
                exc=exc,
            )
        )
        initial_state.update(final_report_node(initial_state))
        initial_state.update(run_manifest_node(initial_state))

        print(
            "[red]工作流基础设施初始化失败：[/red]"
            f"{sanitize_error_message(exc)}"
        )
        print(
            {
                "run_id": initial_state.get("run_id"),
                "run_dir": initial_state.get("run_dir"),
                "run_manifest_path": initial_state.get(
                    "run_manifest_path"
                ),
            }
        )
        raise typer.Exit(code=1) from None

    print("[green]工作流运行完成[/green]")
    print(
        {
            "run_id": result.get("run_id"),
            "run_dir": result.get("run_dir"),
            "final_status": result.get("final_status"),
            "run_manifest_path": result.get("run_manifest_path"),
        }
    )
    print(result.get("output_files", []))
    if has_terminal_stage_error(result):
        raise typer.Exit(code=1)

@app.command("show-process")
def show_process(
    run_id: str | None = typer.Option(None, "--run-id"),
    thread_id: str | None = typer.Option(None, "--thread-id"),
):
    run_dir = _resolve_run_dir_for_control(
        run_id=run_id,
        thread_id=thread_id,
    )
    records = list_runtime_records(run_dir)
    print(
        {
            "run_dir": str(run_dir),
            "processes": records,
        }
    )


@app.command("cancel-run")
def cancel_run(
    reason: str = typer.Option(
        "user requested cancellation",
        "--reason",
    ),
    run_id: str | None = typer.Option(None, "--run-id"),
    thread_id: str | None = typer.Option(None, "--thread-id"),
):
    run_dir = _resolve_run_dir_for_control(
        run_id=run_id,
        thread_id=thread_id,
    )
    try:
        request = request_run_cancellation(
            run_dir=run_dir,
            reason=reason,
            requested_by="cli",
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None

    print(
        {
            "run_dir": str(run_dir),
            "execution_id": request.execution_id,
            "requested_at": request.requested_at,
            "reason": request.reason,
        }
    )


@app.command()
def show_state(thread_id: str = "demo_thread"):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    print(state)

@app.command()
def show_run(run_id: str):
    run_dir = settings.runs_dir / run_id
    manifest_path = run_dir / "reports" / "run_manifest.json"
    error_path = run_dir / "reports" / "error_report.json"

    if not manifest_path.exists():
        raise typer.BadParameter(f"未找到运行清单：{manifest_path}")

    payload = {
        "manifest": json.loads(
            manifest_path.read_text(encoding="utf-8")
        ),
        "errors": (
            json.loads(error_path.read_text(encoding="utf-8"))
            if error_path.exists()
            else None
        ),
    }
    print(payload)

@app.command()
def resume_review(thread_id: str, decision: str = "approved", feedback: str | None = None):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if "human_review" not in snapshot.next:
        raise typer.BadParameter(
            f"thread_id={thread_id} 当前未在 human_review 节点等待；"
            f"当前后续节点为 {snapshot.next}"
        )

    result = graph.invoke(
        Command(resume={"decision": decision, "feedback": feedback}),
        config=config
    )
    print("[green]恢复执行完成[/green]")
    print(result)

@app.command()
def resume_command_selection(
    thread_id: str,
    selected_index: int | None = typer.Option(None, "--selected-index"),
    input: str | None = typer.Option(None, "--input"),
):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if "command_selection" not in snapshot.next:
        raise typer.BadParameter(
            f"thread_id={thread_id} 当前未在 command_selection 节点等待；"
            f"当前后续节点为 {snapshot.next}"
        )

    run_commands = snapshot.values.get("run_commands", [])
    if not run_commands:
        raise typer.BadParameter(
            "checkpoint 中未找到 run_commands；"
            "请先运行工作流，直到进入 command_selection 节点"
        )
    expected_hash = compute_run_commands_hash(run_commands)

    if input:
        payload = json.loads(Path(input).read_text(encoding="utf-8"))
    elif selected_index is not None:
        payload = {
            "run_commands_hash": expected_hash,
            "selected_index": selected_index,
            "edits": [],
        }
    else:
        # 默认读取 command_selection 为当前 run 生成的预填文件。
        run_dir = snapshot.values.get("run_dir")
        if not run_dir:
            raise typer.BadParameter(
                f"未找到 thread_id={thread_id} 对应的 run_dir；"
                "请先运行工作流，直到进入 command_selection 节点"
            )

        generated_input = (
            Path(run_dir) / "planning" / "command_selection_input.json"
        )
        input_status, stale_backup_path = ensure_command_selection_input_file(
            generated_input,
            run_commands,
        )
        if input_status != "current":
            print(
                "[green]已生成命令选择输入文件：[/green] "
                f"{generated_input}"
            )
            if stale_backup_path:
                print(
                    "[yellow]过期输入的备份文件：[/yellow] "
                    f"{stale_backup_path}"
                )
            print("请编辑此文件，然后再次运行相同的恢复命令。")
            return

        payload = json.loads(generated_input.read_text(encoding="utf-8"))
        print(f"[cyan]使用已生成的输入文件：[/cyan] {generated_input}")

    if (
        not isinstance(payload, dict)
        or payload.get("run_commands_hash") != expected_hash
    ):
        raise typer.BadParameter(
            "命令选择输入已经过期：run_commands_hash 与当前 checkpoint 不匹配"
        )

    result = graph.invoke(
        Command(resume=payload),
        config=config,
    )
    print("[green]命令选择恢复完成[/green]")
    print(result)

@app.command()
def list_checkpoints(thread_id: str, limit: int = 5):
    checkpointer = checkpoint.build_checkpointer()
    config = {"configurable": {"thread_id": thread_id}}
    checkpoints = list(checkpointer.list(config, limit=limit))
    rows = []
    for item in checkpoints:
        rows.append(
            {
                "config": item.config,
                "metadata": item.metadata,
                "has_parent": item.parent_config is not None,
            }
        )
    print(rows)

@app.command()
def reset_thread(thread_id: str):
    checkpointer = build_checkpointer()
    checkpointer.delete_thread(thread_id)
    print(f"[yellow]已删除 thread_id={thread_id} 的 checkpoint[/yellow]")

@app.command()
def run_preflight(
    repo_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "手动执行预检",
    execution_profile: str | None = typer.Option(
        None,
        "--execution-profile",
    ),
):
    profile_id = execution_profile or settings.default_execution_profile
    profile = get_execution_profile(profile_id)
    profile_fingerprint = compute_execution_profile_fingerprint(profile)


    action = build_preflight_action_from_command(
        command=command,
        cwd=cwd or profile.workspace_root,
        source=source,
        reason=reason,
        execution_profile_id=profile_id,
        execution_profile_fingerprint=profile_fingerprint,
        timeout_seconds=300,
    )
    action_hash = compute_action_hash(action)

    state = _initialize_cli_run(
        task_id="run-preflight",
        values={
            "repo_path": repo_path,
            "execution_profile_id": profile.profile_id,
            "execution_profile_fingerprint": profile_fingerprint,
            "pending_action": action,
            "pending_action_hash": action_hash,
            "requires_approval": False,
            "user_approval": "not_required",
        },
    )
    state = _run_cli_pipeline(
        state,
        [("preflight_check", preflight_check_node)],
    )
    print("[green]预检完成[/green]")
    print(
        {
            "run_id": state["run_id"],
            "run_dir": state["run_dir"],
            "final_status": state["final_status"],
            "run_manifest_path": state["run_manifest_path"],
        }
    )
    print(state.get("preflight_report"))
    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)

@app.command()
def run_smoke(
    repo_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "手动执行冒烟测试",
    execution_profile: str | None = typer.Option(
        None,
        "--execution-profile",
        help="执行 smoke test 的受信任环境 profile_id",
    ),
):
    profile_id = execution_profile or settings.default_execution_profile
    profile = get_execution_profile(profile_id)
    profile_fingerprint = compute_execution_profile_fingerprint(profile)

    action = build_run_action_from_command(
        command=command,
        cwd=cwd or repo_path,
        source=source,
        reason=reason,
        timeout_seconds=300,
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint=profile_fingerprint,
    )
    action_hash = compute_action_hash(action)

    state = _initialize_cli_run(
        task_id="run-smoke",
        values={
            "repo_path": repo_path,
            "execution_profile_id": profile.profile_id,
            "execution_profile_fingerprint": profile_fingerprint,
            "pending_action": action,
            "pending_action_hash": action_hash,
        },
    )
    state = _run_cli_pipeline(
        state,
        [("smoke_test", smoke_test_node)],
    )
    print("[green]冒烟测试完成[/green]")
    print(
        {
            "run_id": state["run_id"],
            "run_dir": state["run_dir"],
            "final_status": state["final_status"],
            "run_manifest_path": state["run_manifest_path"],
        }
    )
    print(state.get("smoke_test_report"))
    print(state.get("output_files", []))
    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)

@app.command()
def plan_repair(
    repo_path: str,
    log_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "手动生成修复计划",
    execution_profile: str | None = typer.Option(
        None,
        "--execution-profile",
        help="原失败命令使用的受信任环境 profile_id",
    ),
):
    profile_id = execution_profile or settings.default_execution_profile
    profile = get_execution_profile(profile_id)
    profile_fingerprint = compute_execution_profile_fingerprint(profile)

    action = build_run_action_from_command(
        command=command,
        cwd=cwd or repo_path,
        source=source,
        reason=reason,
        timeout_seconds=300,
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint=profile_fingerprint,
    )
    action_hash = compute_action_hash(action)

    state = _initialize_cli_run(
        task_id="plan-repair",
        values={
            "repo_path": repo_path,
            "execution_profile_id": profile.profile_id,
            "execution_profile_fingerprint": profile_fingerprint,
            "pending_action": action,
            "pending_action_hash": action_hash,
            "log_path": log_path,
            "repo_map": {},
            "experiment_plan": {},
            "preflight_report": {},
            "smoke_test_report": {},
        },
    )
    state = _run_cli_pipeline(
        state,
        [
            ("log_debug", log_debug_node),
            ("repair_planner", repair_planner_node),
        ],
    )

    print("[green]修复计划生成完成[/green]")
    print(
        {
            "run_id": state["run_id"],
            "run_dir": state["run_dir"],
            "final_status": state["final_status"],
            "run_manifest_path": state["run_manifest_path"],
        }
    )
    print(state.get("repair_proposal"))
    print(state.get("output_files", []))
    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)

@app.command()
def probe_structured_output(
    schema_name: str = typer.Option(
        "minimal",
        "--schema",
        help="使用 minimal 或 experiment-plan schema 进行探测。",
    ),
):
    """
    验证当前 model/provider 是否支持项目配置的结构化模式。

    该命令会真实调用一次模型 API，但不会运行论文代码或修改仓库。
    """
    if schema_name == "minimal":
        probe_schema = StructuredOutputProbe
        probe_prompt = (
            "请返回一个 status='ok' 且 value=1 的 JSON 对象。"
            "不要返回任何其他字段。"
        )
        trace_node_name = "structured_output_probe"
    elif schema_name == "experiment-plan":
        probe_schema = ExperimentPlan
        probe_prompt = """
请返回一个紧凑的 ExperimentPlan JSON，用于验证复杂 schema 输出能力。
goal 必须是“结构化输出能力探测”。
environment_steps、data_steps、train_steps、eval_steps 各返回 1 项，
每项 evidence=[]、done=false，使用简短中文字符串。
run_commands 返回 2 项安全的示例 python 命令，cwd="/data/tianshaoqi24/example-repository"。
risks 和 unresolved_questions 各返回 2 个简短字符串。
只返回完整 JSON，不要输出 Markdown 或解释。
""".strip()
        trace_node_name = "experiment_plan_probe"
    else:
        raise typer.BadParameter(
            "--schema 只能是 minimal 或 experiment-plan"
        )

    invocation = build_model_gateway().invoke_structured(
        task_kind="evaluation_probe",
        schema=probe_schema,
        prompt=probe_prompt,
        node_name=trace_node_name,
        quality_tier="balanced",
        requested_max_output_tokens=2048,
    )

    trace_path = write_structured_output_trace(
        result=invocation.result,
        node_name=trace_node_name,
        schema_name=probe_schema.__name__,
        output_dir=settings.output_dir,
        fallback_used=not invocation.succeeded,
        model_invocation_id=invocation.invocation_id,
        model_decision_sha256=(
            invocation.decision.decision_sha256
        ),
        model_profile_id=(
            invocation.decision.executed_profile_id
        ),
        model_name=(
            invocation.decision.executed_model_name
        ),
        model_usage_quality=(
            invocation.ledger_record.usage_quality
            if invocation.ledger_record is not None
            else None
        ),
    )
    last_attempt = (
        invocation.attempts[-1]
        if invocation.attempts
        else None
    )

    print(
        {
            "succeeded": invocation.succeeded,
            "schema": schema_name,
            "method": invocation.method,
            "strict": invocation.strict,
            "attempt_count": len(invocation.attempts),
            "value": invocation.value.model_dump() if invocation.value else None,
            "max_output_tokens": settings.openai_max_output_tokens,
            "finish_reason": getattr(
                last_attempt,
                "finish_reason",
                None,
            ),
            "token_usage": getattr(
                last_attempt,
                "token_usage",
                None,
            ),
            "output_chars": getattr(
                last_attempt,
                "output_chars",
                None,
            ),
            "truncated": getattr(
                last_attempt,
                "truncated",
                False,
            ),
            "trace_path": str(trace_path),
        }
    )

    if not invocation.succeeded:
        raise typer.Exit(code=1)


@app.command("model-routing-doctor")
def model_routing_doctor() -> None:
    """只读检查 Policy、Profile、Route 和 Ledger；不解析 Secret。"""

    gateway = build_model_gateway()
    catalog = gateway.router.catalog
    gateway.ledger.ping()
    unpriced = [
        profile.profile_id
        for profile in catalog.document.profiles
        if profile.enabled
        and profile.pricing.billing_mode == "unpriced"
    ]
    active_ready = not (
        unpriced
        and not catalog.document.budget.allow_unpriced_in_active
    )
    print(
        {
            "mode": gateway.mode,
            "policy_version": catalog.document.policy_version,
            "policy_sha256": catalog.policy_sha256,
            "profile_count": len(catalog.document.profiles),
            "route_count": len(catalog.document.routes),
            "unpriced_profiles": unpriced,
            "active_ready": active_ready,
            "ledger": "ready",
        }
    )
    if not active_ready:
        raise typer.Exit(code=2)


@app.command("model-route-preview")
def model_route_preview(
    task_kind: str,
    estimated_input_tokens: int = typer.Option(..., min=1),
    requested_max_output_tokens: int = typer.Option(0, min=0),
    quality_tier: str = typer.Option("balanced"),
) -> None:
    """用长度和能力元数据预览路由，不接收或读取 Prompt 正文。"""

    gateway = build_model_gateway()
    route = gateway.router.catalog.route(task_kind)
    required = set(route.required_capabilities)
    if route.workload_kind == "chat":
        method_capability = {
            "json_schema": "structured_json_schema",
            "function_calling": "structured_function_calling",
            "json_mode": "structured_json_mode",
        }[settings.structured_output_method]
        required.add(method_capability)
    else:
        required.add("embedding")

    request = ModelRouteRequest(
        task_kind=task_kind,
        workload_kind=route.workload_kind,
        required_capabilities=required,
        requested_quality_tier=quality_tier,
        estimated_input_tokens=estimated_input_tokens,
        requested_max_output_tokens=requested_max_output_tokens,
        prompt_sha256=sha256_text(
            f"preview:{task_kind}:{estimated_input_tokens}"
        ),
        prompt_chars=0,
        schema_name=("PreviewSchema" if route.workload_kind == "chat" else None),
        schema_sha256=("0" * 64 if route.workload_kind == "chat" else None),
        node_name="cli_model_route_preview",
    )
    decision, _ = gateway.router.route(
        request=request,
        mode=gateway.mode,
    )
    print(decision.model_dump(mode="json"))


@app.command("model-budget-summary")
def model_budget_summary(
    utc_date: str = typer.Option(""),
    job_id: str = typer.Option(""),
) -> None:
    selected_date = (
        utc_date.strip()
        or datetime.now(timezone.utc).date().isoformat()
    )
    summary = build_model_gateway().ledger.summary(
        utc_date=selected_date,
        job_id=job_id.strip() or None,
    )
    print(summary.model_dump(mode="json"))


@app.command("list-model-invocations")
def list_model_invocations(
    limit: int = typer.Option(50, min=1, max=500),
    job_id: str = typer.Option(""),
) -> None:
    records = build_model_gateway().ledger.list_invocations(
        limit=limit,
        job_id=job_id.strip() or None,
    )
    print([item.model_dump(mode="json") for item in records])


@app.command("reconcile-model-reservations")
def reconcile_model_reservations(
    limit: int = typer.Option(100, min=1, max=1000),
) -> None:
    records = build_model_gateway().ledger.reconcile_stale(limit=limit)
    print(
        {
            "reconciled": len(records),
            "invocation_ids": [item.invocation_id for item in records],
        }
    )


@app.command()
def resume_patch_review(
    thread_id: str,
    decision: str = typer.Option("approved", "--decision"),
    feedback: str | None = typer.Option(None, "--feedback"),
):
    """恢复第一次 patch review；批准后只进入隔离验证。"""

    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if "patch_review" not in snapshot.next:
        raise typer.BadParameter(
            f"thread_id={thread_id} 当前未在 patch_review 节点等待；"
            f"当前后续节点为 {snapshot.next}"
        )

    result = graph.invoke(
        Command(
            resume={
                "decision": decision,
                "feedback": feedback,
            }
        ),
        config=config,
    )
    print("[green]补丁审核恢复完成[/green]")
    print(result)

@app.command()
def resume_patch_promotion(
    thread_id: str,
    decision: str = typer.Option("rejected", "--decision"),
    feedback: str | None = typer.Option(None, "--feedback"),
):
    """恢复第二次 review；approved 会修改原仓库。"""

    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if "patch_promotion_review" not in snapshot.next:
        raise typer.BadParameter(
            f"thread_id={thread_id} 当前未在 patch_promotion_review 节点等待；"
            f"当前后续节点为 {snapshot.next}"
        )

    result = graph.invoke(
        Command(
            resume={
                "decision": decision,
                "feedback": feedback,
            }
        ),
        config=config,
    )
    print("[green]补丁应用审批恢复完成[/green]")
    print(result)

@app.command()
def cleanup_patch_worktree(
    thread_id: str,
    force: bool = typer.Option(False, "--force"),
):
    """显式清理已结束 patch 流程的隔离 worktree。"""

    graph = build_graph()
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 60,
    }
    snapshot = graph.get_state(config)

    protected_nodes = {"patch_review", "patch_promotion_review"}
    if protected_nodes.intersection(snapshot.next):
        raise typer.BadParameter(
            "cannot clean a worktree while patch review is pending"
        )

    values = snapshot.values
    report = values.get("patch_verification_report") or {}
    worktree_path = report.get("worktree_path")
    if not worktree_path:
        raise typer.BadParameter("patch worktree not found in checkpoint")

    application = values.get("patch_application_record") or {}
    if application.get("status") != "applied" and not force:
        raise typer.BadParameter(
            "patch is not applied; inspect it or pass --force"
        )

    remove_patch_worktree(
        repo_path=values["repo_path"],
        worktree_path=worktree_path,
        run_dir=values["run_dir"],
    )
    print(f"[green]removed patch worktree:[/green] {worktree_path}")

@app.command("submit-job")
def submit_job_command(
    paper_path: str,
    repo_path: str,
    thread_id: str | None = typer.Option(
        None,
        "--thread-id",
    ),
    goal: str = typer.Option(
        "复现论文 main result",
        "--goal",
    ),
    log_path: str | None = typer.Option(
        None,
        "--log-path",
    ),
    execution_profile: str | None = typer.Option(
        None,
        "--execution-profile",
    ),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
    ),
):
    """提交异步 Graph Job，不在当前 CLI 中运行 Graph。"""

    service = build_job_service()
    request = JobRequest(
        paper_path=paper_path,
        repo_path=repo_path,
        log_path=log_path,
        experiment_goal=goal,
        execution_profile_id=(
            execution_profile
            or settings.default_execution_profile
        ),
    )
    try:
        record, created = service.submit(
            request=request,
            thread_id=thread_id,
            idempotency_key=idempotency_key,
        )
    except (ValueError, JobStoreError) as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None

    print(
        {
            "created": created,
            "job_id": record.job_id,
            "status": record.status,
            "thread_id": record.thread_id,
            "run_id": record.run_id,
            "run_dir": record.run_dir,
        }
    )


def build_job_worker(worker_id: str) -> JobWorker:
    """CLI 独立 Worker 和 serve-stack 共用完全相同的构造路径。"""

    from app.workspace.manager import (
        WorkspaceManager,
    )
    from app.workspace.materializer import (
        WorkspaceMaterializer,
    )
    from app.workspace.snapshot import (
        WorkspaceSnapshotter,
    )

    service = build_job_service()
    artifact_storage = (
        build_artifact_storage()
    )
    workspace_manager = WorkspaceManager(
        store=service.store,
        materializer=WorkspaceMaterializer(
            blob_store=artifact_storage.selected_store,
        ),
        snapshotter=WorkspaceSnapshotter(
            blob_store=artifact_storage.selected_store,
        ),
    )
    return JobWorker(
        worker_id=worker_id,
        store=service.store,
        workspace_manager=workspace_manager,
        artifact_publisher=(
            artifact_storage.publisher
        ),
    )


def build_resource_worker(worker_id: str):
    """Resource Worker 仍保留 Phase 29 的网络 guard，不因 Web 部署降级。"""

    if settings.resource_require_network_guard and (
        not settings.resource_network_guard_configured
    ):
        raise RuntimeError(
            "RESOURCE_REQUIRE_NETWORK_GUARD=true 但未配置 egress guard"
        )

    from app.resources.service import (
        build_resource_service,
    )
    from app.resources.worker import ResourceWorker

    resource_service = build_resource_service()
    artifact_storage = build_artifact_storage()
    return ResourceWorker(
        repository=resource_service.repository,
        blob_store=artifact_storage.selected_store,
        worker_id=worker_id,
    )


@app.command("run-worker")
def run_worker_command(
    worker_id: str | None = typer.Option(
        None,
        "--worker-id",
    ),
    once: bool = typer.Option(
        False,
        "--once",
        help="最多处理一个 Job 后退出",
    ),
):
    effective_worker_id = (
        worker_id
        or (
            f"{socket.gethostname()}-"
            f"{uuid4().hex[:8]}"
        )
    )
    worker = build_job_worker(effective_worker_id)
    print(
        {
            "worker_id": effective_worker_id,
            "host_id": settings.worker_host_id,
            "worker_pool": settings.worker_pool,
            "workspace_root": str(
                settings.worker_workspace_root.resolve()
            ),
            "artifact_backend": (
                settings.artifact_blob_backend
            ),
            "once": once,
        }
    )

    if once:
        try:
            handled = worker.run_once()
            print({"handled": handled})
        finally:
            worker.close()
        return

    try:
        worker.run_forever()
    except KeyboardInterrupt:
        print(
            "[yellow]worker 已收到 Ctrl+C，"
            "当前安全边界处理结束后退出[/yellow]"
        )


@app.command("show-job")
def show_job_command(job_id: str):
    service = build_job_service()
    try:
        record = service.get(job_id)
    except JobStoreError as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None
    print(record.model_dump())


@app.command("list-jobs")
def list_jobs_command(
    status: str | None = typer.Option(
        None,
        "--status",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
    ),
):
    service = build_job_service()
    records = service.list(
        status=status,
        limit=limit,
    )
    print(
        [
            {
                "job_id": item.job_id,
                "status": item.status,
                "thread_id": item.thread_id,
                "run_id": item.run_id,
                "attempt_count": (
                    item.attempt_count
                ),
                "updated_at": item.updated_at,
            }
            for item in records
        ]
    )


@app.command("compare-runs")
def compare_runs_command(
    base_job_id: str = typer.Argument(...),
    target_job_id: str = typer.Argument(...),
    allow_cross_paper: bool = typer.Option(
        False,
        "--allow-cross-paper",
        help="允许不同 paper SHA 的诊断比较；不会给出科学复现结论。",
    ),
) -> None:
    """比较两个终态 Job 的已验证运行事实。"""

    job_service = build_job_service()
    storage = build_artifact_storage()
    service = build_comparison_service(
        jobs=job_service.store,
        artifact_catalog=storage.catalog,
    )
    report = service.create(
        ComparisonCreateRequest(
            base_job_id=base_job_id,
            target_job_id=target_job_id,
            allow_cross_paper=allow_cross_paper,
        )
    )
    print(
        {
            "comparison_id": report.comparison_id,
            "base_job_id": report.base.job_id,
            "target_job_id": report.target.job_id,
            "change_count": report.summary.change_count,
            "high_count": report.summary.high_count,
            "changed_categories": report.summary.changed_categories,
            "json": str(
                settings.comparison_root
                / report.comparison_id
                / "comparison.json"
            ),
            "markdown": str(
                settings.comparison_root
                / report.comparison_id
                / "comparison.md"
            ),
        }
    )


@app.command("show-job-events")
def show_job_events_command(
    job_id: str,
    limit: int = typer.Option(
        200,
        "--limit",
    ),
):
    service = build_job_service()
    try:
        events = service.events(
            job_id,
            limit=limit,
        )
    except JobStoreError as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None
    print(
        [
            item.model_dump()
            for item in events
        ]
    )

@app.command("resume-job")
def resume_job_command(
    job_id: str,
    expected_node: str = typer.Option(
        ...,
        "--expected-node",
        help=(
            "必须与 show-job.interrupt_nodes "
            "中的当前节点一致"
        ),
    ),
    input_path: str | None = typer.Option(
        None,
        "--input",
        help="JSON 文件；command_selection 推荐使用",
    ),
    decision: str | None = typer.Option(
        None,
        "--decision",
        help="审批节点的 approved/rejected/revise",
    ),
    feedback: str | None = typer.Option(
        None,
        "--feedback",
    ),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
    ),
    expected_version: int | None = typer.Option(
        None,
        "--expected-version",
        min=0,
    ),
    expected_wait_generation: (
        int | None
    ) = typer.Option(
        None,
        "--expected-wait-generation",
        min=1,
    ),
):
    if bool(input_path) == bool(decision):
        raise typer.BadParameter(
            "必须且只能提供 --input 或 --decision"
        )

    if input_path:
        try:
            value = json.loads(
                Path(input_path).read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise typer.BadParameter(
                f"无法读取 resume JSON：{exc}"
            ) from None
    else:
        value = {
            "decision": decision,
            "feedback": feedback,
        }

    service = build_job_service()
    try:
        current = service.get(job_id)
        record, created = service.resume(
            job_id=job_id,
            expected_node=expected_node,
            value=value,
            idempotency_key=idempotency_key,
            expected_job_version=(
                expected_version
                if expected_version is not None
                else current.version
            ),
            expected_wait_generation=(
                expected_wait_generation
                if expected_wait_generation
                is not None
                else current.wait_generation
            ),
            actor="cli",
        )
    except (ValueError, JobStoreError) as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None

    print(
        {
            "created": created,
            "job_id": record.job_id,
            "status": record.status,
            "pending_resume_id": (
                record.pending_resume_id
            ),
        }
    )


@app.command("cancel-job")
def cancel_job_command(
    job_id: str,
    reason: str = typer.Option(
        "user requested cancellation",
        "--reason",
    ),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
    ),
    expected_version: int | None = typer.Option(
        None,
        "--expected-version",
        min=0,
    ),
):
    service = build_job_service()
    try:
        current = service.get(job_id)
        record = service.cancel(
            job_id=job_id,
            reason=reason,
            idempotency_key=(
                idempotency_key
            ),
            expected_job_version=(
                expected_version
                if expected_version is not None
                else current.version
            ),
            actor="cli",
        )
    except JobStoreError as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None
    print(
        {
            "job_id": record.job_id,
            "status": record.status,
            "cancel_requested": (
                record.cancel_requested
            ),
            "reason": (
                record.cancellation_reason
            ),
        }
    )


@app.command("wait-job")
def wait_job_command(
    job_id: str,
    timeout: float | None = typer.Option(
        None,
        "--timeout",
    ),
):
    service = build_job_service()
    try:
        record = service.wait(
            job_id=job_id,
            timeout_seconds=timeout,
        )
    except JobStoreError as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None
    print(record.model_dump())


@app.command("tail-job-log")
def tail_job_log_command(
    job_id: str,
    lines: int = typer.Option(
        100,
        "--lines",
    ),
):
    service = build_job_service()
    try:
        path, content = service.tail_log(
            job_id=job_id,
            lines=lines,
        )
    except JobStoreError as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None
    print({"log_path": path})
    if content:
        print(content)


@app.command("resolve-job")
def resolve_job_command(
    job_id: str,
    decision: str = typer.Option(
        ...,
        "--decision",
        help="requeue、failed 或 cancelled",
    ),
    confirm_requeue: bool = typer.Option(
        False,
        "--confirm-requeue",
        help="确认可能重复外部副作用",
    ),
):
    service = build_job_service()
    try:
        record = service.resolve_reconciliation(
            job_id=job_id,
            decision=decision,
            confirm_requeue=confirm_requeue,
            actor="cli",
        )
    except (ValueError, JobStoreError) as exc:
        raise typer.BadParameter(
            str(exc)
        ) from None
    print(record.model_dump())

def _is_loopback_host(host: str) -> bool:
    """只接受明确的 loopback 名称或 IP。"""

    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(
            normalized
        ).is_loopback
    except ValueError:
        return False


def _api_token_available() -> bool:
    """检查 SecretService 中是否已配置 API Token。"""
    from app.secrets.errors import SecretNotFoundError

    try:
        from app.secrets.factory import build_secret_service

        build_secret_service().reference(
            settings.api_token_secret_name
        )
        return True
    except SecretNotFoundError:
        return False
    except Exception:
        return False


@app.command("serve-api")
def serve_api_command(
    host: str = typer.Option(
        settings.api_host,
        "--host",
    ),
    port: int = typer.Option(
        settings.api_port,
        "--port",
        min=1,
        max=65535,
    ),
):
    """启动本地优先的任务交互 API。"""

    if (
        not _is_loopback_host(host)
        and not _api_token_available()
    ):
        raise typer.BadParameter(
            "监听非 loopback 地址前必须设置 "
            "AGENT_API_TOKEN"
        )

    # 动态 import，避免只运行 worker 时强制依赖 uvicorn。
    import uvicorn

    print(
        {
            "host": host,
            "port": port,
        "authentication": (
            "bearer"
            if _api_token_available()
            else "local-only"
        ),
        }
    )
    uvicorn.run(
        "app.api.app:create_api_app",
        host=host,
        port=port,
        reload=False,
        factory=True,
        proxy_headers=False,
    )


@app.command("serve-stack")
def serve_stack_command(
    host: str = typer.Option(  # noqa: B008
        "127.0.0.1",
        "--host",
    ),
    port: int = typer.Option(  # noqa: B008
        8000,
        "--port",
        min=1,
        max=65535,
    ),
) -> None:
    """启动 Web/API、Job Worker 和 Resource Worker。

    Phase 30 单用户单主机部署：API 只监听 loopback，
    远程浏览器通过 SSH tunnel 访问。
    """

    if not _is_loopback_host(host):
        raise typer.BadParameter(
            "Phase 30 serve-stack 只允许 loopback；"
            "远程访问请使用 SSH tunnel"
        )
    if _api_token_available():
        raise typer.BadParameter(
            "Phase 30 浏览器 EventSource 不携带 Bearer header；"
            "请在 loopback 部署中取消 AGENT_API_TOKEN"
        )

    import uvicorn

    from app.api.app import create_api_app
    from app.service_host import ServiceHost

    hostname = socket.gethostname()
    host_runtime = ServiceHost(
        job_worker_factory=lambda: build_job_worker(
            f"{hostname}-web-{uuid4().hex[:8]}"
        ),
        resource_worker_factory=lambda: build_resource_worker(
            f"{hostname}-resource-{uuid4().hex[:8]}"
        ),
        resource_poll_seconds=(
            settings.resource_poll_seconds
        ),
    )
    host_runtime.start()
    try:
        uvicorn.run(
            create_api_app(service_host=host_runtime),
            host=host,
            port=port,
            reload=False,
            proxy_headers=False,
            workers=1,
        )
    finally:
        host_runtime.stop()

@app.command("check-artifact-storage")
def check_artifact_storage_command():
    """检查 Catalog 和当前 Blob backend 是否可用。"""

    bundle = build_artifact_storage()
    bundle.repository.initialize()
    for store in bundle.stores:
        store.ensure_ready()
    print(
        {
            "status": "ready",
            "selected_backend": (
                settings.artifact_blob_backend
            ),
            "registered_backends": [
                item.backend_name
                for item in bundle.stores
            ],
            "catalog_db": str(
                settings
                .artifact_catalog_db_path
            ),
        }
    )


@app.command("publish-job-artifacts")
def publish_job_artifacts_command(
    job_id: str,
):
    """
    发布历史 Job 当前 checkpoint 中登记的 Artifact。

    该命令不改变 Job 状态，只迁移 Artifact。
    """

    service = build_job_service()
    job = service.get(job_id)
    state = read_graph_state(
        job.thread_id
    )
    records = state.get(
        "artifact_records",
        [],
    )
    bundle = build_artifact_storage()
    report = bundle.publisher.publish(
        job=job,
        records=records,
    )
    print(report.model_dump())


@app.command("migrate-database")
def migrate_database_command():
    """升级应用表，再升级 LangGraph Saver 自有表。"""

    if settings.job_store_backend != "postgresql":
        raise typer.BadParameter(
            "migrate-database 只用于 PostgreSQL backend"
        )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    if settings.checkpoint_backend == "postgresql":
        setup_checkpointer()
    print(
        {
            "status": "migrated",
            "job_backend": settings.job_store_backend,
            "checkpoint_backend": (
                settings.checkpoint_backend
            ),
        }
    )


@app.command("check-database")
def check_database_command():
    """检查连接和当前 Alembic revision，不输出 DSN。"""

    ping_database()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "current",
            "--check-heads",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise typer.BadParameter(
            "数据库 revision 未到 head"
        )
    print(
        {
            "status": "ready",
            "job_backend": settings.job_store_backend,
            "checkpoint_backend": (
                settings.checkpoint_backend
            ),
        }
    )


@app.command("runtime-doctor")
def runtime_doctor_command(
    profile_id: str = typer.Option(  # noqa: B008
        ...,
        "--profile-id",
        help="要检查的 OCI ExecutionProfile ID",
    ),
) -> None:
    """只读检查 OCI runtime 和 image 是否就绪。

    doctor 不能 build、pull、remove 或修复任何东西。
    它只解释"为什么该 profile 当前可用/不可用"。
    """

    from app.execution.podman_engine import PodmanEngine
    from app.workspace.capabilities import (
        probe_oci_profile,
    )

    try:
        profile = get_execution_profile(profile_id)
    except ValueError as exc:
        print(
            {
                "profile_id": profile_id,
                "profile_valid": False,
                "ready": False,
                "error": str(exc),
            }
        )
        raise typer.Exit(code=1) from None

    engine = PodmanEngine(
        executable=settings.container_runtime
    )

    if profile.backend != "oci" or profile.oci is None:
        print(
            {
                "profile_id": profile_id,
                "profile_valid": True,
                "ready": False,
                "error": "profile 不是 OCI backend",
            }
        )
        raise typer.Exit(code=1)

    try:
        probe = engine.probe()
        image_present = engine.image_exists(
            profile.oci.image_ref
        )
        probe_oci_profile(engine, profile)
        print(
            {
                "runtime": probe.runtime,
                "version": probe.version,
                "rootless": probe.rootless,
                "cgroup": probe.cgroup_version,
                "image_ref": profile.oci.image_ref,
                "image_present": image_present,
                "profile_valid": True,
                "ready": True,
            }
        )
    except Exception as exc:
        print(
            {
                "profile_id": profile_id,
                "profile_valid": True,
                "ready": False,
                "error": str(exc),
            }
        )
        raise typer.Exit(code=1) from None


@app.command("observability-doctor")
def observability_doctor_command() -> None:
    """检查 observability 配置和 backend 初始化状态（只读，不发送数据）。"""

    runtime = _cli_telemetry()
    backend = runtime.backend
    otlp_endpoint = settings.otlp_http_endpoint
    issues: list[str] = []

    if backend not in {"noop", "in_memory", "otel"}:
        issues.append(
            f"未知 backend: {backend}，合法值: noop/in_memory/otel"
        )

    if backend == "otel":
        if not otlp_endpoint:
            issues.append(
                "backend=otel 但未设置 OTEL_EXPORTER_OTLP_ENDPOINT"
            )
        if settings.otel_trace_enabled is False and settings.otel_metric_enabled is False:
            issues.append(
                "otel backend 但 trace 和 metric 均被关闭"
            )

    # 不真的发送生产 span，只是测试能否构造 backend 并开 span。
    carrier = None
    try:
        with runtime.telemetry.span(
            "observability_doctor.self_check",
            attributes={"backend": backend},
        ) as span:
            span.set_attribute("ready", True)
            carrier = span.carrier()
        span_ok = True
    except Exception as exc:
        span_ok = False
        issues.append(f"span 初始化失败: {exc}")

    try:
        runtime.telemetry.counter(
            "paper_copilot_http_requests_total",
            0,
            {
                "method": "GET",
                "route": "/observability_doctor",
                "status_class": "2xx",
            },
        )
        metric_ok = True
    except Exception as exc:
        metric_ok = False
        issues.append(f"metric 写入失败: {exc}")

    structured_enabled = settings.structured_logging_enabled
    environment = settings.telemetry_environment
    carrier_present = carrier is not None and bool(
        getattr(carrier, "traceparent", None)
    )

    print(
        {
            "backend": backend,
            "environment": environment,
            "otlp_endpoint_configured": bool(
                otlp_endpoint
            ),
            "trace_enabled": settings.otel_trace_enabled,
            "metric_enabled": settings.otel_metric_enabled,
            "structured_logging": structured_enabled,
            "span_init_ok": span_ok,
            "metric_init_ok": metric_ok,
            "carrier_present": carrier_present,
            "issues": issues,
            "ok": not issues,
        }
    )
    if issues:
        raise typer.Exit(code=1)


@app.command("readiness-check")
def readiness_check_command(
    component: str = typer.Option(  # noqa: B008
        "api",
        "--component",
        "-c",
        help="api 或 worker",
    ),
) -> None:
    """执行本地只读 readiness 检查并打印报告。"""

    if component not in {"api", "worker"}:
        raise typer.BadParameter(
            "component 必须是 'api' 或 'worker'"
        )

    def db_check() -> str:
        try:
            js = build_job_service()
            js.store.ping()
            return "ready"
        except Exception:
            return "not_ready"

    def storage_check() -> str:
        try:
            bundle = build_artifact_storage()
            bundle.repository.initialize()
            if hasattr(bundle, "selected_store") and bundle.selected_store is not None:
                if hasattr(bundle.selected_store, "ensure_ready"):
                    bundle.selected_store.ensure_ready()
            return "ready"
        except Exception:
            return "degraded"

    def checkpoint_check() -> str:
        try:
            checkpointer = build_checkpointer()
            if hasattr(checkpointer, "apayload") and False:
                pass
            return "ready"
        except Exception:
            return "degraded"

    def resource_db_check() -> str:
        # Phase 29：Resource catalog 是 acquisition 的前提；
        # API 与 Worker 都依赖它。
        try:
            from app.resources.service import (
                build_resource_service,
            )

            build_resource_service().repository.ping()
            return "ready"
        except Exception:
            return "not_ready"

    def staging_root_check() -> str:
        # Phase 29 Worker：staging root 必须可写并位于 allowed_root。
        try:
            root = settings.resource_staging_root
            root.mkdir(parents=True, exist_ok=True)
            probe = root / ".readiness_probe"
            probe.write_bytes(b"ok")
            probe.unlink()
            return "ready"
        except Exception:
            return "not_ready"

    def network_guard_check() -> str:
        # Phase 29 Worker：未配置 egress guard 时报告 degraded，
        # 不能声称"完全防 SSRF"。
        if settings.resource_require_network_guard:
            return (
                "ready"
                if settings.resource_network_guard_configured
                else "not_ready"
            )
        # 开发环境未要求 guard；明确 degraded 而非 ready。
        return (
            "ready"
            if settings.resource_network_guard_configured
            else "degraded"
        )

    def git_executable_check() -> str:
        # Phase 29 Worker：启用 Git resource 时需要 git 可用。
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                check=True,
                timeout=2,
            )
            return "ready"
        except Exception:
            return "not_ready"

    probes = [
        ReadinessProbe(
            name="job_store.ping",
            is_critical=True,
            check=db_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        ),
        ReadinessProbe(
            name="resource_db.ping",
            is_critical=True,
            check=resource_db_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        ),
        ReadinessProbe(
            name="artifact_storage.readiness",
            is_critical=False,
            check=storage_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        ),
        ReadinessProbe(
            name="checkpoint_store.readiness",
            is_critical=(component == "worker"),
            check=checkpoint_check,
            timeout_seconds=settings.readiness_timeout_seconds,
        ),
    ]
    if component == "worker":
        # Phase 29 Acquisition Worker 专属探针。
        probes.extend(
            [
                ReadinessProbe(
                    name="resource_staging_root.writable",
                    is_critical=True,
                    check=staging_root_check,
                    timeout_seconds=settings.readiness_timeout_seconds,
                ),
                ReadinessProbe(
                    name="blob_store.ensure_ready",
                    is_critical=True,
                    check=storage_check,
                    timeout_seconds=(
                        settings.readiness_timeout_seconds
                    ),
                ),
                ReadinessProbe(
                    name=(
                        "egress_network_guard"
                    ),
                    is_critical=(
                        settings.resource_require_network_guard
                    ),
                    check=network_guard_check,
                    timeout_seconds=(
                        settings.readiness_timeout_seconds
                    ),
                ),
                ReadinessProbe(
                    name="git_executable",
                    is_critical=False,
                    check=git_executable_check,
                    timeout_seconds=(
                        settings.readiness_timeout_seconds
                    ),
                ),
            ]
        )
    service = ReadinessService(
        component=component,  # type: ignore[arg-type]
        probes=probes,
        max_workers=settings.readiness_probe_workers,
    )
    report = service.check()
    print(report.model_dump())
    if report.status == "not_ready":
        raise typer.Exit(code=2)
    if report.status == "degraded":
        raise typer.Exit(code=0)


# ---------------------------------------------------------------------------
# Phase 29：受控资源获取 CLI
#
# 网络权限只属于 Resource Worker；LLM 只能通过 request-resource 提出 proposal，
# 由运维 approve-resource 后才能被 Worker 获取。执行容器仍保持 network=none。
# ---------------------------------------------------------------------------


@app.command("request-resource")
def request_resource_command(
    kind: str = typer.Option(  # noqa: B008
        ...,
        "--kind",
        help="资源类型：paper_pdf | git_repository | checkpoint",
    ),
    url: str = typer.Option(  # noqa: B008
        ...,
        "--url",
        help="HTTPS resource URL（第一版禁止 query/userinfo/fragment）",
    ),
    purpose: str = typer.Option(  # noqa: B008
        ...,
        "--purpose",
        help="资源用途说明（用于审批）",
    ),
    expected_sha256: str | None = typer.Option(  # noqa: B008
        None,
        "--expected-sha256",
        help="checkpoint 必填；paper_pdf 可选；git_repository 禁用",
    ),
    expected_git_commit: str | None = typer.Option(  # noqa: B008
        None,
        "--expected-git-commit",
        help="git_repository 必填（exact full commit SHA）",
    ),
    idempotency_key: str = typer.Option(  # noqa: B008
        None,
        "--idempotency-key",
        help="幂等键；不提供时自动生成",
    ),
) -> None:
    """提交 ResourceRequest，状态进入 awaiting_approval 等待人工批准。"""

    from app.resources.request_hash import (
        resource_request_sha256,
    )
    from app.resources.schemas import ResourceRequest
    from app.resources.service import (
        build_resource_service,
        sanitize_resource_view,
    )

    if kind not in {"paper_pdf", "git_repository", "checkpoint"}:
        raise typer.BadParameter(
            "kind 必须是 paper_pdf/git_repository/checkpoint"
        )

    try:
        request = ResourceRequest(
            kind=kind,  # type: ignore[arg-type]
            source_url=url,
            purpose=purpose,
            expected_sha256=expected_sha256,
            expected_git_commit=expected_git_commit,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None

    service = build_resource_service()
    key = idempotency_key or f"cli_{uuid4().hex}"
    try:
        record, created = service.submit(
            request=request,
            idempotency_key=key,
        )
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from None

    view = sanitize_resource_view(record)
    view["request_sha256_preview"] = resource_request_sha256(
        request
    )
    print(
        {
            "created": created,
            "resource": view,
        }
    )


@app.command("show-resource")
def show_resource_command(
    resource_id: str = typer.Argument(...),
    reveal_source: bool = typer.Option(  # noqa: B008
        False,
        "--reveal-source",
        help="显示原始 source URL（默认只显示 sanitized canonical URL）",
    ),
) -> None:
    """查看 Resource 公开视图；claim_token 永不返回。"""

    from app.resources.errors import ResourceNotFoundError
    from app.resources.service import (
        build_resource_service,
        sanitize_resource_view,
    )

    service = build_resource_service()
    try:
        record = service.get(resource_id)
    except ResourceNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from None

    print(sanitize_resource_view(record, reveal_source=reveal_source))


@app.command("approve-resource")
def approve_resource_command(
    resource_id: str = typer.Argument(...),
    request_sha256: str = typer.Option(  # noqa: B008
        ...,
        "--request-sha256",
        help="审批必须绑定当前 request hash；改动后旧审批失效",
    ),
    reason: str | None = typer.Option(  # noqa: B008
        None,
        "--reason",
    ),
    expected_version: int | None = typer.Option(  # noqa: B008
        None,
        "--expected-version",
    ),
) -> None:
    """批准 Resource 进入 queued，等待 Acquisition Worker 获取。"""

    from datetime import datetime, timezone

    from app.resources.errors import (
        ResourceConflictError,
        ResourceNotFoundError,
    )
    from app.resources.schemas import ResourceApproval
    from app.resources.service import (
        build_resource_service,
        sanitize_resource_view,
    )

    approval = ResourceApproval(
        decision="approved",
        request_sha256=request_sha256,
        decided_by="cli-operator",
        decided_at=datetime.now(timezone.utc).isoformat(),
        reason=reason,
    )
    service = build_resource_service()
    try:
        record = service.approve(
            resource_id=resource_id,
            approval=approval,
            expected_version=expected_version,
        )
    except (ResourceNotFoundError, ResourceConflictError) as exc:
        raise typer.BadParameter(str(exc)) from None

    print(sanitize_resource_view(record))


@app.command("reject-resource")
def reject_resource_command(
    resource_id: str = typer.Argument(...),
    request_sha256: str = typer.Option(  # noqa: B008
        ...,
        "--request-sha256",
    ),
    reason: str | None = typer.Option(  # noqa: B008
        None,
        "--reason",
    ),
    expected_version: int | None = typer.Option(  # noqa: B008
        None,
        "--expected-version",
    ),
) -> None:
    """拒绝 Resource，进入 rejected 终态。"""

    from datetime import datetime, timezone

    from app.resources.errors import (
        ResourceConflictError,
        ResourceNotFoundError,
    )
    from app.resources.schemas import ResourceApproval
    from app.resources.service import (
        build_resource_service,
        sanitize_resource_view,
    )

    approval = ResourceApproval(
        decision="rejected",
        request_sha256=request_sha256,
        decided_by="cli-operator",
        decided_at=datetime.now(timezone.utc).isoformat(),
        reason=reason,
    )
    service = build_resource_service()
    try:
        record = service.approve(
            resource_id=resource_id,
            approval=approval,
            expected_version=expected_version,
        )
    except (ResourceNotFoundError, ResourceConflictError) as exc:
        raise typer.BadParameter(str(exc)) from None

    print(sanitize_resource_view(record))


@app.command("cancel-resource")
def cancel_resource_command(
    resource_id: str = typer.Argument(...),
    reason: str = typer.Option(  # noqa: B008
        "cli requested cancellation",
        "--reason",
    ),
) -> None:
    """取消 Resource（非终态才可取消）。"""

    from app.resources.errors import (
        ResourceConflictError,
        ResourceNotFoundError,
    )
    from app.resources.service import (
        build_resource_service,
        sanitize_resource_view,
    )

    service = build_resource_service()
    try:
        record = service.cancel(
            resource_id=resource_id,
            reason=reason,
            actor="cli-operator",
        )
    except (ResourceNotFoundError, ResourceConflictError) as exc:
        raise typer.BadParameter(str(exc)) from None

    print(sanitize_resource_view(record))


@app.command("show-resource-events")
def show_resource_events_command(
    resource_id: str = typer.Argument(...),
    limit: int = typer.Option(  # noqa: B008
        200,
        "--limit",
    ),
) -> None:
    """查看 Resource 审计事件（payload 不含 claim_token / URL query）。"""

    from app.resources.errors import ResourceNotFoundError
    from app.resources.service import build_resource_service

    service = build_resource_service()
    try:
        events = service.events(resource_id, limit=limit)
    except ResourceNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from None

    print(
        {
            "resource_id": resource_id,
            "count": len(events),
            "items": [e.model_dump() for e in events],
        }
    )


@app.command("run-resource-worker")
def run_resource_worker_command(
    worker_id: str | None = typer.Option(  # noqa: B008
        None,
        "--worker-id",
    ),
    once: bool = typer.Option(  # noqa: B008
        False,
        "--once",
        help="最多获取一个 Resource 后退出",
    ),
) -> None:
    """运行 Acquisition Worker。

    网络权限只属于本 Worker；论文执行容器保持 network=none。
    若 RESOURCE_REQUIRE_NETWORK_GUARD=true 且未配置 egress guard，
    Worker readiness 报 not_ready 并拒绝启动。
    不带 --once 时持续轮询，直到 Ctrl+C。
    """

    if settings.resource_require_network_guard and (
        not settings.resource_network_guard_configured
    ):
        raise typer.BadParameter(
            "RESOURCE_REQUIRE_NETWORK_GUARD=true 但未配置 egress guard；"
            "Worker 不能启动。请配置网络层 guard 或显式设置 "
            "RESOURCE_NETWORK_GUARD_CONFIGURED=true（仅用于开发环境，"
            "readiness 会报告 degraded_application_guard_only）"
        )

    effective_worker_id = (
        worker_id
        or f"{socket.gethostname()}-res-{uuid4().hex[:8]}"
    )
    worker = build_resource_worker(effective_worker_id)
    print(
        {
            "worker_id": effective_worker_id,
            "staging_root": str(
                settings.resource_staging_root.resolve()
            ),
            "allowed_hosts": list(
                settings.resource_allowed_hosts
            ),
            "network_guard_configured": (
                settings.resource_network_guard_configured
            ),
            "degraded_application_guard_only": (
                not settings.resource_network_guard_configured
            ),
            "once": once,
        }
    )

    if once:
        processed = worker.run_once()
        print({"processed": int(processed)})
        return

    try:
        worker.run_forever(
            poll_seconds=settings.resource_poll_seconds,
        )
    except KeyboardInterrupt:
        print("[yellow]Resource Worker 已停止[/yellow]")


@app.command("reconcile-resources")
def reconcile_resources_command(
    limit: int = typer.Option(  # noqa: B008
        100,
        "--limit",
    ),
) -> None:
    """扫描 lease 过期的 fetching Resource 并按 staging/blob 事实恢复。

    不会重新联网；blob 已存在且 hash 匹配时恢复 publication，
    否则按安全规则 requeue 或标记 reconciliation_required。
    """

    from app.resources.reconcile import ResourceReconciler
    from app.resources.service import build_resource_service
    from app.storage.factory import build_artifact_storage

    resource_service = build_resource_service()
    storage = build_artifact_storage()
    reconciler = ResourceReconciler(
        repository=resource_service.repository,
        blob_store=storage.selected_store,
    )
    results = reconciler.reconcile_expired(limit=limit)
    print(
        {
            "scanned": len(results),
            "results": [
                {
                    "resource_id": r.resource_id,
                    "disposition": r.disposition,
                    "detail": r.detail,
                }
                for r in results
            ],
        }
    )


@app.command("gc-plan")
def gc_plan_command() -> None:
    """Phase 35: 创建垃圾回收 Plan。"""
    if not settings.retention_enabled:
        raise typer.Abort("RETENTION_ENABLED=false")
    from app.job_runtime.factory import build_job_store
    from app.storage.factory import build_artifact_storage
    from app.retention.factory import build_retention

    bundle = build_retention(
        job_store=build_job_store(),
        artifact_storage=build_artifact_storage(),
    )
    if bundle.service is None:
        raise typer.Abort("当前 backend 不支持 destructive GC")

    plan = bundle.service.create_plan()
    print(
        json.dumps(
            {
                "plan_id": plan.plan_id,
                "status": plan.status,
                "plan_hash": plan.plan_hash,
                "targets": [t.model_dump(mode="json") for t in plan.targets],
                "expires_at": plan.expires_at,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("gc-confirm")
def gc_confirm_command(
    plan_id: str,
) -> None:
    """Phase 35: 确认并执行垃圾回收 Sweep。"""
    if not settings.retention_enabled:
        raise typer.Abort("RETENTION_ENABLED=false")
    from app.job_runtime.factory import build_job_store
    from app.storage.factory import build_artifact_storage
    from app.retention.factory import build_retention

    bundle = build_retention(
        job_store=build_job_store(),
        artifact_storage=build_artifact_storage(),
    )
    if bundle.service is None:
        raise typer.Abort("当前 backend 不支持 destructive GC")

    plan = bundle.service.get_plan(plan_id)
    result = bundle.service.sweep(
        plan_id=plan_id,
        plan_hash=plan.plan_hash,
    )
    print(
        json.dumps(
            {
                "plan_id": result.plan.plan_id,
                "deleted_jobs": result.deleted_jobs,
                "deleted_blob_count": result.deleted_blob_count,
                "retained_shared_blob_count": result.retained_shared_blob_count,
                "reclaimed_logical_bytes": result.reclaimed_logical_bytes,
                "step_count": len(result.steps),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("gc-summary")
def gc_summary_command() -> None:
    """Phase 35: 打印受管存储摘要。"""
    if not settings.retention_enabled:
        raise typer.Abort("RETENTION_ENABLED=false")
    from app.job_runtime.factory import build_job_store
    from app.storage.factory import build_artifact_storage
    from app.retention.factory import build_retention

    bundle = build_retention(
        job_store=build_job_store(),
        artifact_storage=build_artifact_storage(),
    )
    summary = bundle.inventory.summarize()
    print(
        json.dumps(
            summary.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Phase 39：可信重跑提案 CLI
# ---------------------------------------------------------------------------


def _build_cli_rerun_service():
    job_service = build_job_service()
    storage = build_artifact_storage()
    comparison = build_comparison_service(
        jobs=job_service.store,
        artifact_catalog=storage.catalog,
    )
    return build_rerun_service(
        job_service=job_service,
        artifact_catalog=storage.catalog,
        comparison_service=comparison,
    )


@app.command("inspect-rerun-source")
def inspect_rerun_source_command(
    parent_job_id: str = typer.Argument(...),
) -> None:
    """显示创建 Proposal 需要的 SHA 和脱敏命令摘要。"""

    service = _build_cli_rerun_service()
    evidence = service.evidence_reader.read(parent_job_id)
    snapshot = build_command_snapshot(
        evidence.run_manifest.get("selected_run_command")
    )
    print(
        {
            "parent_job_id": evidence.job.job_id,
            "parent_run_id": evidence.job.run_id,
            "parent_job_version": evidence.job.version,
            "run_manifest_sha256": (
                evidence.run_manifest_artifact.sha256
            ),
            "workspace_manifest_hash": evidence.workspace.manifest_hash,
            "selected_command_display": snapshot.display,
            "selected_command_sha256": snapshot.command_sha256,
            "execution_profile_id": (
                evidence.job.request.execution_profile_id
            ),
            "dataset_labels": [
                item.required_worker_label
                for item in evidence.workspace.external_data
            ],
        }
    )


@app.command("create-rerun-proposal")
def create_rerun_proposal_command(
    parent_job_id: str = typer.Argument(...),
    expected_manifest_sha: str = typer.Option(
        ...,
        "--expected-manifest-sha",
    ),
    expected_job_version: int = typer.Option(
        ...,
        "--expected-job-version",
        min=0,
    ),
    edits_file: Path = typer.Option(
        ...,
        "--edits-file",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    idempotency_key: str = typer.Option(
        ...,
        "--idempotency-key",
    ),
    experiment_goal: str | None = typer.Option(
        None,
        "--experiment-goal",
    ),
    execution_profile_id: str | None = typer.Option(
        None,
        "--execution-profile-id",
    ),
    comparison_id: str | None = typer.Option(None, "--comparison-id"),
    comparison_hash: str | None = typer.Option(None, "--comparison-hash"),
) -> None:
    raw = json.loads(edits_file.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise typer.BadParameter("edits-file 顶层必须是 JSON array")
    edits = [RerunArgumentEdit.model_validate(item) for item in raw]

    service = _build_cli_rerun_service()
    record, created = service.create_proposal(
        request=RerunProposalCreateRequest(
            parent_job_id=parent_job_id,
            expected_parent_job_version=expected_job_version,
            expected_parent_run_manifest_sha256=expected_manifest_sha,
            edits=edits,
            experiment_goal=experiment_goal,
            execution_profile_id=execution_profile_id,
            comparison_id=comparison_id,
            expected_comparison_hash=comparison_hash,
        ),
        idempotency_key=idempotency_key,
    )
    print(
        {
            "proposal_id": record.proposal.proposal_id,
            "proposal_hash": record.proposal.proposal_hash,
            "status": record.status,
            "version": record.version,
            "created": created,
            "expires_at": record.proposal.expires_at,
        }
    )


@app.command("show-rerun-proposal")
def show_rerun_proposal_command(
    proposal_id: str = typer.Argument(...),
) -> None:
    service = _build_cli_rerun_service()
    record = service.get_proposal(proposal_id)
    print(record.model_dump(mode="json"))


@app.command("submit-rerun-proposal")
def submit_rerun_proposal_command(
    proposal_id: str = typer.Argument(...),
    expected_hash: str = typer.Option(..., "--expected-hash"),
    expected_version: int = typer.Option(..., "--expected-version", min=0),
    idempotency_key: str = typer.Option(..., "--idempotency-key"),
) -> None:
    service = _build_cli_rerun_service()
    record, child, created = service.submit_proposal(
        proposal_id=proposal_id,
        request=RerunProposalSubmitRequest(
            expected_proposal_hash=expected_hash,
            expected_version=expected_version,
        ),
        idempotency_key=idempotency_key,
    )
    print(
        {
            "proposal_id": record.proposal.proposal_id,
            "proposal_status": record.status,
            "proposal_version": record.version,
            "child_job_id": child.job_id,
            "child_thread_id": child.thread_id,
            "child_status": child.status,
            "job_created": created,
        }
    )


@app.command("cancel-rerun-proposal")
def cancel_rerun_proposal_command(
    proposal_id: str = typer.Argument(...),
    expected_hash: str = typer.Option(..., "--expected-hash"),
    expected_version: int = typer.Option(..., "--expected-version", min=0),
    reason: str = typer.Option("user cancelled", "--reason"),
) -> None:
    service = _build_cli_rerun_service()
    record = service.cancel_proposal(
        proposal_id=proposal_id,
        request=RerunProposalCancelRequest(
            expected_proposal_hash=expected_hash,
            expected_version=expected_version,
            reason=reason,
        ),
    )
    print(record.model_dump(mode="json"))


@app.command("validate-tool-contracts")
def validate_tool_contracts_command() -> None:
    """离线验证 Contract、Adapter 绑定和 app/tools Inventory。"""

    # 使用局部 import，避免普通 CLI 命令无条件构建 Tool Catalog。
    from app.tool_contracts import (
        build_tool_registry,
        validate_tool_contract_system,
    )

    report = validate_tool_contract_system()
    registry = build_tool_registry()
    print(
        {
            "report": report.model_dump(mode="json"),
            "contracts": registry.catalog_snapshot(),
        }
    )
    if not report.ok:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Phase 48: Agent Skill / Plugin CLI
# ---------------------------------------------------------------------------


def _build_cli_skill_registry():
    from app.skills.catalog import build_skill_registry

    return build_skill_registry(
        package_root=settings.agent_skill_package_dir,
        globally_enabled=settings.agent_skills_enabled,
        enabled_skill_ids=set(settings.agent_skill_enabled_ids),
    )


def _resolve_skill_cli_root(path: Path, *, label: str) -> Path:
    unresolved = path.expanduser()
    if unresolved.is_symlink():
        raise typer.BadParameter(f"{label} 不能是符号链接")
    try:
        resolved = unresolved.resolve(strict=True)
    except OSError as exc:
        raise typer.BadParameter(f"{label} 不存在或不可访问") from exc

    allowed_root = settings.allowed_root.expanduser().resolve()
    if (
        not resolved.is_dir()
        or not (
            resolved == allowed_root
            or allowed_root in resolved.parents
        )
    ):
        raise typer.BadParameter(
            f"{label} 必须是 ALLOWED_ROOT 内的普通目录"
        )
    return resolved


def _read_skill_payload(path: Path) -> dict[str, Any]:
    unresolved = path.expanduser()
    if unresolved.is_symlink() or not unresolved.is_file():
        raise typer.BadParameter("payload-file 必须是普通 JSON 文件")
    resolved = unresolved.resolve(strict=True)
    allowed_root = settings.allowed_root.expanduser().resolve()
    if not (
        resolved == allowed_root
        or allowed_root in resolved.parents
    ):
        raise typer.BadParameter("payload-file 必须位于 ALLOWED_ROOT 内")
    if resolved.stat().st_size > 256 * 1024:
        raise typer.BadParameter("payload-file 超过 256 KiB")
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise typer.BadParameter("payload-file 不是有效 UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise typer.BadParameter("payload-file 顶层必须是 JSON object")
    return value


@app.command("validate-skills")
def validate_skills_command() -> None:
    """验证 Package、内置绑定、Tool Contract 和 Eval Suite。"""

    try:
        registry = _build_cli_skill_registry()
        entries = registry.catalog_snapshot()
    except (OSError, ValueError) as exc:
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=1) from exc

    typer.echo(
        json.dumps(
            {
                "ok": True,
                "skills_checked": len(entries),
                "skills": [
                    item.model_dump(mode="json") for item in entries
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("list-skills")
def list_skills_command() -> None:
    """列出绑定后的 Schema、Hash 和 enabled 状态，不执行 Skill。"""

    registry = _build_cli_skill_registry()
    typer.echo(
        json.dumps(
            [
                item.model_dump(mode="json")
                for item in registry.catalog_snapshot()
            ],
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("invoke-skill")
def invoke_skill_command(
    skill_id: str = typer.Argument(...),
    payload_file: Path = typer.Option(..., "--payload-file"),
    workspace_root: Path = typer.Option(..., "--workspace-root"),
    run_root: Path = typer.Option(..., "--run-root"),
    expected_skill_sha256: str | None = typer.Option(
        None,
        "--expected-skill-sha256",
        help="省略时使用本次 Catalog Hash；生产调用应显式提交旧快照 Hash。",
    ),
) -> None:
    """在显式受控根目录下手工调用一个已启用 Skill。"""

    from app.skills.schemas import (
        SkillInvocationContext,
        SkillInvocationRequest,
    )

    registry = _build_cli_skill_registry()
    bound = registry.get(skill_id)
    workspace = _resolve_skill_cli_root(
        workspace_root,
        label="workspace-root",
    )
    run = _resolve_skill_cli_root(
        run_root,
        label="run-root",
    )
    result = registry.invoke(
        request=SkillInvocationRequest(
            skill_id=skill_id,
            skill_version=bound.package.manifest.skill_version,
            expected_skill_sha256=(
                expected_skill_sha256 or bound.skill_sha256
            ),
            input_payload=_read_skill_payload(payload_file),
        ),
        context=SkillInvocationContext(
            actor="cli:invoke-skill",
            request_id=f"skill-cli-{uuid4().hex[:12]}",
            workspace_root=str(workspace),
            run_root=str(run),
            granted_capabilities=sorted(
                settings.agent_skill_granted_capabilities
            ),
        ),
    )
    typer.echo(
        json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
    )
    if result.failure is not None:
        raise typer.Exit(code=1)


@app.command("init-secret-store")
def init_secret_store() -> None:
    """初始化本地加密 Secret Vault 和 Master Key。"""

    from app.secrets.crypto import create_master_key_file
    from app.secrets.factory import build_secret_service

    key_path = settings.secret_master_key_path
    vault_path = settings.secret_vault_db_path

    # Vault 已存在而 Key 丢失时绝不能创建新 Key，否则旧密文永久不可解。
    if vault_path.exists() and not key_path.exists():
        raise typer.BadParameter(
            "Vault 已存在但 Master Key 缺失；请从安全备份恢复 Key"
        )
    if not key_path.exists():
        create_master_key_file(key_path)

    # Service 构造会初始化空 Vault，并执行路径、权限和 Schema 校验。
    build_secret_service()
    typer.echo("secret store initialized")


@app.command("set-secret")
def set_secret(
    name: str = typer.Argument(...),
    use: str = typer.Option(..., "--use"),
) -> None:
    """从隐藏终端输入写入新版本；不接受 --value。"""

    from app.secrets.factory import build_secret_service
    from app.secrets.schemas import SecretUse

    try:
        secret_use = SecretUse(use)
    except ValueError:
        valid = ", ".join(item.value for item in SecretUse)
        raise typer.BadParameter(
            f"无效的 use：{use}；可选值：{valid}"
        )

    value = typer.prompt(
        "Secret value",
        hide_input=True,
        confirmation_prompt=True,
    )
    service = build_secret_service()
    metadata = service.put(
        name=name,
        value=value,
        allowed_uses={secret_use},
    )
    typer.echo(
        f"stored {metadata.reference.name} "
        f"version={metadata.reference.version} "
        f"fingerprint={metadata.reference.fingerprint[:24]}..."
    )


@app.command("list-secrets")
def list_secrets() -> None:
    """列出所有 Secret 的 metadata（不输出明文）。"""

    from app.secrets.factory import build_secret_service

    for metadata in build_secret_service().list_metadata():
        reference = metadata.reference
        uses = ",".join(
            item.value for item in metadata.allowed_uses
        )
        typer.echo(
            f"{reference.name} v{reference.version} "
            f"status={metadata.status.value} "
            f"uses={uses} "
            f"fingerprint={reference.fingerprint[:24]}..."
        )


@app.command("revoke-secret")
def revoke_secret(
    name: str,
    version: int = typer.Option(..., "--version", min=1),
) -> None:
    """撤销指定 Secret 的当前 active 版本。"""

    from app.secrets.factory import build_secret_service

    service = build_secret_service()
    current = service.reference(name)
    if current.version != version:
        raise typer.BadParameter(
            "指定版本不是当前 active version"
        )
    metadata = service.revoke(reference=current)
    typer.echo(
        f"revoked {metadata.reference.name} "
        f"v{metadata.reference.version}"
    )


@app.command("secret-doctor")
def secret_doctor() -> None:
    """检查 Secret Vault 安全状态。"""

    from app.secrets.doctor import inspect_secret_health

    report = inspect_secret_health(
        key_path=settings.secret_master_key_path,
        vault_path=settings.secret_vault_db_path,
        allowed_root=settings.allowed_root,
    )
    typer.echo(
        f"secret health: "
        f"{'ready' if report.ok else 'not-ready'}"
    )
    typer.echo(
        f"active_secret_count={report.active_secret_count}"
    )
    for issue in report.issues:
        typer.echo(f"- {issue}")
    if not report.ok:
        raise typer.Exit(code=1)


def _default_secret_scan_roots() -> list[Path]:
    """只扫描项目已知持久化面，不扫描 Vault 本身。"""

    return [
        settings.runs_dir,
        settings.output_dir,
        settings.checkpoint_db_path,
        settings.embedding_cache_db_path,
        settings.job_db_path,
        settings.artifact_catalog_db_path,
        settings.artifact_local_store_dir,
        settings.resource_db_path,
        settings.chat_db_path,
        settings.rerun_db_path,
        settings.retention_db_path,
    ]


@app.command("scan-secret-leaks")
def scan_secret_leaks(
    roots: list[Path] | None = typer.Option(
        None,
        "--root",
        help="可重复指定；省略时扫描项目已知持久化面",
    ),
) -> None:
    """扫描持久化面中是否包含已知 Secret 明文。"""

    from app.secrets.factory import build_secret_service
    from app.secrets.scanner import SecretLeakScanner

    service = build_secret_service()
    redactor = service.build_redactor(
        actor="cli:leak-scan"
    )
    scanner = SecretLeakScanner(
        redactor=redactor,
        excluded_roots=(
            settings.secret_master_key_path.parent,
        ),
    )
    findings = scanner.scan_roots(
        roots or _default_secret_scan_roots()
    )
    if not findings:
        typer.echo("no known secret material found")
        return

    for finding in findings:
        typer.echo(
            f"{finding.path}: "
            f"{','.join(finding.secret_names)}"
        )
    raise typer.Exit(code=2)


# Phase 51: Restricted Research Browser CLI


@app.command("research-submit")
def research_submit(
    query: str = typer.Argument(...),
    purpose: str = typer.Option(..., "--purpose"),
    job_id: str | None = typer.Option(None, "--job-id"),
    host: list[str] | None = typer.Option(None, "--host"),
    max_results: int = typer.Option(5, "--max-results", min=1, max=20),
    idempotency_key: str = typer.Option(..., "--idempotency-key"),
) -> None:
    """提交受限研究请求；这里只建记录，不自动联网。"""
    from app.research_browser.factory import (
        build_research_browser_service,
    )
    from app.research_browser.schemas import (
        ResearchPublicRecord,
        ResearchRequest,
    )

    service = build_research_browser_service()
    record = service.submit(
        request=ResearchRequest(
            query=query,
            purpose=purpose,
            job_id=job_id,
            allowed_hosts=host or [],
            max_results=max_results,
        ),
        idempotency_key=idempotency_key,
        actor="cli",
    )
    typer.echo(
        ResearchPublicRecord.from_record(
            record
        ).model_dump_json(indent=2)
    )


@app.command("research-run")
def research_run(
    research_id: str,
    expected_version: int = typer.Option(
        ..., "--expected-version", min=0
    ),
) -> None:
    """领取并同步执行一个 pending Research Session。"""
    from app.research_browser.factory import (
        build_research_browser_service,
    )
    from app.research_browser.schemas import (
        ResearchPublicRecord,
    )

    record = build_research_browser_service().run(
        session_id=research_id,
        expected_version=expected_version,
        actor="cli",
    )
    typer.echo(
        ResearchPublicRecord.from_record(
            record
        ).model_dump_json(indent=2)
    )


@app.command("research-show")
def research_show(research_id: str) -> None:
    """显示会话公开状态，不输出 lease token。"""
    from app.research_browser.factory import (
        build_research_browser_service,
    )
    from app.research_browser.schemas import (
        ResearchPublicRecord,
    )

    record = build_research_browser_service().get(
        research_id
    )
    typer.echo(
        ResearchPublicRecord.from_record(
            record
        ).model_dump_json(indent=2)
    )


@app.command("research-pack")
def research_pack(research_id: str) -> None:
    """显示已完成且通过完整性校验的 Evidence Pack。"""
    from app.research_browser.factory import (
        build_research_browser_service,
    )

    pack = build_research_browser_service().get_pack(
        research_id
    )
    typer.echo(pack.model_dump_json(indent=2))


@app.command("research-request-resource")
def research_request_resource(
    research_id: str,
    candidate_id: str = typer.Option(..., "--candidate-id"),
    candidate_sha256: str = typer.Option(
        ..., "--candidate-sha256"
    ),
    pack_sha256: str = typer.Option(..., "--pack-sha256"),
    purpose: str = typer.Option(..., "--purpose"),
) -> None:
    """把一个候选交给现有资源审批流，不直接下载。"""
    from app.research_browser.factory import (
        build_research_browser_service,
    )
    from app.research_browser.schemas import (
        ResearchResourceLinkResponse,
        ResearchResourceSelection,
    )

    record = (
        build_research_browser_service().submit_resource_candidate(
            session_id=research_id,
            selection=ResearchResourceSelection(
                candidate_id=candidate_id,
                candidate_sha256=candidate_sha256,
                expected_pack_sha256=pack_sha256,
                purpose=purpose,
            ),
            actor="cli",
        )
    )
    response = ResearchResourceLinkResponse(
        session_id=research_id,
        candidate_id=candidate_id,
        resource_id=record.resource_id,
        resource_request_sha256=record.request_sha256,
        resource_status=record.status,
        resource_version=record.version,
    )
    typer.echo(response.model_dump_json(indent=2))


@app.command("research-reconcile")
def research_reconcile() -> None:
    """回收过期 running lease，使崩溃任务可重新领取。"""
    from app.research_browser.factory import (
        build_research_browser_service,
    )

    count = build_research_browser_service().reconcile(
        actor="cli"
    )
    typer.echo(f"requeued={count}")


@app.command("research-doctor")
def research_doctor() -> None:
    """只检查配置、Policy、Vault metadata 和数据库，不发起真实搜索。"""
    from app.research_browser.doctor import (
        inspect_research_browser,
    )

    report = inspect_research_browser()
    typer.echo(report.model_dump_json(indent=2))
    if not report.ready:
        raise typer.Exit(code=1)


@app.command("tool-calling-doctor")
def tool_calling_doctor() -> None:
    """检查 Chat Tool Calling 的本地配置、Catalog 和 Model Route。"""
    from app.chat.context import ChatContextBuilder
    from app.interaction.service import InteractionService
    from app.tool_calling.factory import doctor_chat_tool_calling

    job_service = build_job_service()
    artifact_storage = build_artifact_storage()
    interaction = InteractionService(job_service)
    context_builder = ChatContextBuilder(
        interaction=interaction,
        artifact_catalog=artifact_storage.catalog,
        artifacts_to_open=settings.chat_artifacts_to_open,
        source_limit=settings.chat_source_limit,
        artifact_max_bytes=settings.chat_artifact_max_bytes,
        total_context_chars=settings.chat_total_context_chars,
        log_max_bytes=settings.chat_log_max_bytes,
    )

    report = doctor_chat_tool_calling(
        context_builder=context_builder,
    )
    typer.echo(report.model_dump_json(indent=2))
    if not report.ready:
        raise typer.Exit(code=1)


@app.command("mcp-inspect")
def mcp_inspect(
    server_id: str = typer.Argument(...),
    binding_id: str = typer.Argument(...),
) -> None:
    """Connect to a pinned local MCP Server and list the real Schema/Hash for one configured Binding."""

    import json as _json

    from app.mcp_gateway.factory import build_mcp_client
    from app.mcp_gateway.policy import load_mcp_gateway_policy

    policy = load_mcp_gateway_policy(
        settings.mcp_gateway_policy_path,
        allowed_root=settings.allowed_root,
    )
    matches = [
        (server, binding)
        for server in policy.servers
        if server.server_id == server_id
        for binding in server.bindings
        if binding.binding_id == binding_id
    ]
    if len(matches) != 1:
        typer.echo(
            _json.dumps(
                {"ready": False, "issue": "binding_not_unique"},
                ensure_ascii=False,
            )
        )
        raise typer.Exit(code=1)

    profile, binding = matches[0]
    observed = build_mcp_client().inspect_tool(
        profile=profile,
        binding=binding,
    )
    typer.echo(observed.model_dump_json(indent=2))


@app.command("mcp-doctor")
def mcp_doctor(
    connect: bool = typer.Option(
        False,
        "--connect",
        help="Connect to local MCP Server and run tools/list; will not call_tool.",
    ),
) -> None:
    """Check Feature, Policy, Binding, and optionally verify remote Schema Pin."""

    from app.mcp_gateway.factory import inspect_mcp_gateway

    report = inspect_mcp_gateway(connect=connect)
    typer.echo(report.model_dump_json(indent=2))
    if not report.ready:
        raise typer.Exit(code=1)


@app.command("mcp-export-doctor")
def mcp_export_doctor() -> None:
    """离线检查 Phase 54 配置、Token 和 Audit，不启动监听端口。"""

    from app.mcp_export.factory import inspect_mcp_export

    report = inspect_mcp_export()
    typer.echo(
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
    )
    if not report.ready:
        raise typer.Exit(code=1)


@app.command("serve-mcp-export")
def serve_mcp_export() -> None:
    """启动独立的本机只读 Streamable HTTP MCP Server。"""

    if not settings.mcp_export_enabled:
        raise typer.BadParameter(
            "MCP_EXPORT_ENABLED=false；拒绝启动 MCP Export"
        )
    if settings.mcp_export_host != "127.0.0.1":
        raise typer.BadParameter(
            "Phase 54 只允许监听 127.0.0.1"
        )

    from app.mcp_export.asgi import build_mcp_export_asgi_bundle

    try:
        import uvicorn
    except ImportError as exc:
        raise typer.BadParameter(
            "缺少 MCP/uvicorn 依赖，请安装 python -m pip install -e '.[mcp]'"
        ) from exc

    bundle = build_mcp_export_asgi_bundle()
    uvicorn.run(
        bundle.app,
        host=settings.mcp_export_host,
        port=settings.mcp_export_port,
        log_level="info",
        access_log=False,
        # 开发环境也不要自动 reload，避免重复初始化 Vault/DB。
        reload=False,
    )


@app.command("mcp-contract-candidate")
def mcp_contract_candidate(
    include_http: bool = typer.Option(
        False,
        "--include-http",
        help="同时连接已经启动的 loopback MCP Export。",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="可选项目内 Candidate 路径。",
    ),
) -> None:
    """观察 MCP 公开目录并生成待审核 Candidate，不修改 Baseline。"""

    from app.mcp_contracts.commands import generate_candidate

    path, candidate = generate_candidate(
        include_http=include_http,
        output_path=output,
    )
    typer.echo(
        json.dumps(
            {
                "candidate_path": str(path),
                "candidate_sha256": candidate.candidate_sha256,
                "surface_sha256": candidate.surface_sha256,
                "consistent_surface": candidate.consistent_surface,
                "profile_ids": candidate.profile_ids,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not candidate.consistent_surface:
        raise typer.Exit(code=1)


@app.command("mcp-contract-accept")
def mcp_contract_accept(
    candidate_path: Path = typer.Argument(...),
    expected_surface_sha256: str = typer.Option(
        ...,
        "--expected-surface-sha256",
    ),
    reviewed_by: str = typer.Option(..., "--reviewed-by"),
    reason: str = typer.Option(..., "--reason"),
    replace: bool = typer.Option(False, "--replace"),
    expected_current_baseline_sha256: str | None = typer.Option(
        None,
        "--expected-current-baseline-sha256",
    ),
) -> None:
    """人工确认 Candidate；所有覆盖都需要绑定旧 Baseline Hash。"""

    from app.mcp_contracts.commands import accept_candidate

    baseline = accept_candidate(
        candidate_path=candidate_path,
        expected_surface_sha256=expected_surface_sha256,
        reviewed_by=reviewed_by,
        reason=reason,
        replace=replace,
        expected_current_baseline_sha256=(
            expected_current_baseline_sha256
        ),
    )
    typer.echo(baseline.model_dump_json(indent=2))


@app.command("mcp-contract-eval")
def mcp_contract_eval(
    mode: str = typer.Option(
        "offline",
        "--mode",
        help="offline 或 release。",
    ),
) -> None:
    """将实际 MCP Surface 与已审核 Golden 比较。"""

    if mode not in {"offline", "release"}:
        raise typer.BadParameter("mode 必须是 offline 或 release")

    from app.mcp_contracts.commands import run_contract_eval

    json_path, markdown_path, report = run_contract_eval(
        mode=mode,
    )
    typer.echo(
        json.dumps(
            {
                "passed": report.passed,
                "eval_id": report.eval_id,
                "report_sha256": report.report_sha256,
                "json_path": str(json_path),
                "markdown_path": str(markdown_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not report.passed:
        raise typer.Exit(code=1)


@app.command("mcp-stack-doctor")
def mcp_stack_doctor(
    connect_gateway: bool = typer.Option(
        False,
        "--connect-gateway",
        help="显式连接 Phase 53 Server 并验证 Schema Pin。",
    ),
) -> None:
    """统一检查 SDK、Contract、Phase 53 Gateway 与 Phase 54 Export。"""

    from app.mcp_contracts.commands import stack_doctor

    report = stack_doctor(connect_gateway=connect_gateway)
    typer.echo(report.model_dump_json(indent=2))
    if report.status == "not_ready":
        raise typer.Exit(code=1)


@app.command("mcp-runtime-probe")
def mcp_runtime_probe(
    job_id: str = typer.Argument(
        ...,
        help="已有 Final Report 的测试 Job ID。",
    ),
    mode: str = typer.Option(
        "offline",
        "--mode",
        help="offline 或 release。",
    ),
) -> None:
    """执行六个只读业务操作并生成项目内 SLO Report。"""

    if mode not in {"offline", "release"}:
        raise typer.BadParameter("mode 必须是 offline 或 release")

    from app.mcp_operations.commands import run_runtime_evaluation

    json_path, markdown_path, report = run_runtime_evaluation(
        mode=mode,
        job_id=job_id,
    )
    typer.echo(
        json.dumps(
            {
                "passed": report.passed,
                "report_id": report.report_id,
                "report_sha256": report.report_sha256,
                "json_path": str(json_path),
                "markdown_path": str(markdown_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not report.passed:
        raise typer.Exit(code=1)


@app.command("mcp-runtime-compare")
def mcp_runtime_compare(
    before: Path = typer.Option(..., "--before"),
    after: Path = typer.Option(..., "--after"),
) -> None:
    """比较两个已生成的 release Report，不安装或升级依赖。"""

    from app.mcp_operations.commands import compare_upgrade_reports

    output_path, comparison = compare_upgrade_reports(
        before_path=before,
        after_path=after,
    )
    typer.echo(
        json.dumps(
            {
                "passed": comparison.passed,
                "comparison_id": comparison.comparison_id,
                "comparison_sha256": comparison.comparison_sha256,
                "output_path": str(output_path),
                "finding_codes": comparison.finding_codes,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not comparison.passed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    with bind_telemetry_context(
        request_id=f"cli_{uuid4().hex}"
    ):
        app()
