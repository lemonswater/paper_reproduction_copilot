import json
from pathlib import Path

import typer
from langgraph.types import Command
from rich import print

from app.config import settings
from app.graph import build_graph
from app.memory import checkpoint
from app.memory.checkpoint import build_checkpointer
from app.nodes.code_search_node import code_search_node
from app.nodes.command_selection_node import (
    compute_run_commands_hash,
    ensure_command_selection_input_file,
)
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.mapping_node import mapping_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.log_debug_node import log_debug_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.preflight_check_node import preflight_check_node
from app.nodes.repair_planner_node import repair_planner_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.smoke_test_node import smoke_test_node
from app.tools.action_tools import build_run_action_from_command, compute_action_hash
from app.tools.preflight_tools import build_preflight_action_from_command
from app.execution.profile_store import get_execution_profile, compute_execution_profile_fingerprint
app = typer.Typer(help="Paper Reproduction Copilot")


@app.command()
def version():
    print("[green]paper-reproduction-copilot 0.1.0[/green]")


@app.command()
def init_outputs():
    Path("outputs").mkdir(exist_ok=True)
    print("[green]outputs/ is ready[/green]")


@app.command()
def read_paper(paper_path: str):
    state = {"paper_path": paper_path, "output_files": []}
    state.update(paper_reader_node(state))
    state.update(method_extractor_node(state))
    print("[green]paper reading finished[/green]")
    print(state["output_files"])

@app.command()
def scan_repo(repo_path: str):
    state = {"repo_path": repo_path, "output_files": []}
    state.update(repo_scan_node(state))
    print("[green]repo scan finished[/green]")
    print(state["output_files"])

@app.command()
def map_code(paper_path: str, repo_path: str):
    state = {
        "paper_path": paper_path,
        "repo_path": repo_path,
        "output_files": []
    }
    state.update(paper_reader_node(state))
    state.update(method_extractor_node(state))
    state.update(repo_scan_node(state))
    state.update(code_search_node(state))
    state.update(mapping_node(state))
    print("[green]paper-code mapping finished[/green]")
    print(state["output_files"])

@app.command()
def plan_experiment(
    paper_path: str,
    repo_path: str,
    goal: str = "复现论文 main result"
):
    state = {
        "paper_path": paper_path,
        "repo_path": repo_path,
        "experiment_goal": goal,
        "output_files": []
    }
    state.update(paper_reader_node(state))
    state.update(method_extractor_node(state))
    state.update(repo_scan_node(state))
    state.update(code_search_node(state))
    state.update(mapping_node(state))
    state.update(experiment_plan_node(state))
    print("[green]experiment plan finished[/green]")
    print(state["output_files"])

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
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {
            "paper_path": paper_path,
            "repo_path": repo_path,
            "execution_profile_id": profile_id,
            "log_path": log_path,
            "experiment_goal": goal,
            "output_files": [],
            "step_count": 0,
            "max_steps": 20
        },
        config=config
    )
    print("[green]graph finished[/green]")
    print(result.get("output_files", []))

@app.command()
def show_state(thread_id: str = "demo_thread"):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    print(state)

@app.command()
def show_run(run_id: str):
    manifest_path = settings.runs_dir / run_id / "reports" / "run_manifest.json"
    if not manifest_path.exists():
        raise typer.BadParameter(f"run manifest not found: {manifest_path}")

    print(manifest_path.read_text(encoding="utf-8"))

@app.command()
def resume_review(thread_id: str, decision: str = "approved", feedback: str | None = None):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if "human_review" not in snapshot.next:
        raise typer.BadParameter(
            f"thread_id={thread_id} is not waiting at human_review; "
            f"current next={snapshot.next}"
        )

    result = graph.invoke(
        Command(resume={"decision": decision, "feedback": feedback}),
        config=config
    )
    print("[green]resume finished[/green]")
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
            f"thread_id={thread_id} is not waiting at command_selection; "
            f"current next={snapshot.next}"
        )

    run_commands = snapshot.values.get("run_commands", [])
    if not run_commands:
        raise typer.BadParameter(
            "run_commands not found in checkpoint; "
            "run the graph until command_selection first"
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
                f"run_dir not found for thread_id={thread_id}; "
                "run the graph until command_selection first"
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
                "[green]generated command selection input:[/green] "
                f"{generated_input}"
            )
            if stale_backup_path:
                print(
                    "[yellow]stale input backup:[/yellow] "
                    f"{stale_backup_path}"
                )
            print("Edit this file, then run the same resume command again.")
            return

        payload = json.loads(generated_input.read_text(encoding="utf-8"))
        print(f"[cyan]using generated input:[/cyan] {generated_input}")

    if (
        not isinstance(payload, dict)
        or payload.get("run_commands_hash") != expected_hash
    ):
        raise typer.BadParameter(
            "command selection input is stale: run_commands_hash does not "
            "match the current checkpoint"
        )

    result = graph.invoke(
        Command(resume=payload),
        config=config,
    )
    print("[green]command selection resume finished[/green]")
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
    print(f"[yellow]deleted checkpoints for thread_id={thread_id}[/yellow]")

@app.command()
def run_preflight(
    repo_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "manual preflight check",
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

    state = {
        "repo_path": repo_path,
        "execution_profile_id": profile.profile_id,
        "execution_profile_fingerprint": profile_fingerprint,
        "pending_action": action,
        "pending_action_hash": action_hash,
        "requires_approval": False,
        "user_approval": "not_required",
        "output_files": [],
    }

    result = preflight_check_node(state)
    print("[green]preflight finished[/green]")
    print(result.get("preflight_report"))

@app.command()
def run_smoke(
    repo_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "manual smoke test",
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

    state = {
        "repo_path": repo_path,
        "execution_profile_id": profile.profile_id,
        "execution_profile_fingerprint": profile_fingerprint,
        "pending_action": action,
        "pending_action_hash": action_hash,
        "output_files": [],
    }

    result = smoke_test_node(state)
    print("[green]smoke test finished[/green]")
    print(result.get("smoke_test_report"))
    print(result.get("output_files", []))

@app.command()
def plan_repair(
    repo_path: str,
    log_path: str,
    command: str,
    cwd: str | None = None,
    source: str = "inferred",
    reason: str = "manual repair planning",
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

    state = {
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
        "output_files": [],
    }

    state.update(log_debug_node(state))
    state.update(repair_planner_node(state))

    print("[green]repair planning finished[/green]")
    print(state.get("repair_proposal"))
    print(state.get("output_files", []))

if __name__ == "__main__":
    app()
