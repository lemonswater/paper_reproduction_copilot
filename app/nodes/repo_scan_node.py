from __future__ import annotations

import json

from app.schemas import RepoMap
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
    write_text_artifact,
)
from app.tools.error_tools import stage_error_result
from app.tools.repo_tools import classify_repo_file, get_file_tree


def repo_scan_node(state: dict) -> dict:
    repo_path = state.get("repo_path")
    if not repo_path:
        return stage_error_result(
            state=state,
            stage="repo_scan",
            code="REPO_PATH_REQUIRED",
            category="user",
            message="必须提供 repo_path",
            extra_update={"repo_map": {}},
        )

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

    _, repo_map_record = write_json_artifact(
        state=state,
        relative_path="analysis/repo_map.json",
        payload=repo_map.model_dump(),
        producer_node="repo_scan",
    )
    summary_text = (
        "# 仓库摘要\n\n"
        "## 文件树\n\n"
        f"```text\n{tree}\n```\n\n"
        "## 重要文件\n\n"
        "```json\n"
        f"{json.dumps(repo_map.model_dump(), ensure_ascii=False, indent=2)}"
        "\n```\n"
    )
    _, summary_record = write_text_artifact(
        state=state,
        relative_path="analysis/repo_summary.md",
        text=summary_text,
        producer_node="repo_scan",
        media_type="text/markdown",
    )

    return {
        "repo_tree": tree,
        "repo_map": repo_map.model_dump(),
        **artifact_state_update(
            state,
            [repo_map_record, summary_record],
        ),
    }
