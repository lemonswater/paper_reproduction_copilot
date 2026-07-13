from pathlib import Path

import typer
from rich import print
from app import graph
from app.nodes.experiment_plan_node import experiment_plan_node
from app.nodes.method_extractor_node import method_extractor_node
from app.nodes.paper_reader_node import paper_reader_node
from app.nodes.repo_scan_node import repo_scan_node
from app.nodes.code_search_node import code_search_node
from app.nodes.mapping_node import mapping_node
from app.graph import build_graph

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
    log_path: str,
    thread_id: str = "demo_thread",
    goal: str = "复现论文 main result"
):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {
            "paper_path": paper_path,
            "repo_path": repo_path,
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
def show_state(thread_id: str = "demo-thread"):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    print(state)

@app.command()
def resume_review(thread_id: str, decision: str = "approved", feedback: str | None = None):
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        Command(resume={"decision": decision, "feedback": feedback}),
        config=config
    )
    print(result)

if __name__ == "__main__":
    app()
