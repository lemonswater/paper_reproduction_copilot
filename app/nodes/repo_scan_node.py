import json
from app.config import settings
from app.schemas import RepoMap
from app.tools.repo_tools import classify_repo_file, get_file_tree

def repo_scan_node(state: dict) -> dict:
    repo_path = state.get("repo_path")
    if not repo_path:
        return {"error": "repo_path is required"}

    tree = get_file_tree(repo_path)
    classified = classify_repo_file(repo_path)
    important_files = sorted(
        set(
            classified["readme_files"]
            + classified["train_entries"]
            + classified["eval_entries"]
            + classified["config_files"]
            + classified["model_files"]
            + classified["dataset_files"]
            + classified["loss_files"]
        )
    )
    repo_map = RepoMap(
        repo_path=repo_path,
        important_files=important_files,
        **classified
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    repo_map_path = settings.output_dir / "repo_map.json"
    repo_summary_path = settings.output_dir / "repo_summary.md"

    repo_map_path.write_text(repo_map.model_dump_json(indent=2), encoding="utf-8")
    repo_summary_path.write_text(
        "# Repo Summary\n\n"
        "## File Tree\n\n"
        f"```text\n{tree}\n```\n\n"
        "## Important Files\n\n"
        f"```json\n{json.dumps(repo_map.model_dump(), ensure_ascii=False, indent=2)}\n```\n",
        encoding="utf-8",
    )


    return {
        "repo_tree": tree,
        "repo_map": repo_map.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(repo_map_path),
            str(repo_summary_path)
        ]
    }