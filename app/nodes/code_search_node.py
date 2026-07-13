from pathlib import Path
from app.tools.code_tools import read_file_slice
from app.tools.search_tools  import search_keywords

def _candidate_file_from_matched(matches: list[dict], limit: int = 8) -> list[str]:
    scores: dict[str, int] = {}
    for match in matches:
        file_path = match["file_path"]
        scores[file_path] = scores.get(file_path, 0) + 1
    return [
        file_path for file_path , _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]

def code_search_node(state: dict) -> dict:
    repo_path = state.get("repo_path")
    modules = state.get("method_modules", [])
    if not repo_path:
        return {"error": "repo_path is required"}
    if not modules:
        return {"error": "method_modules is empty"}

    module_search_results: dict[str, dict] = {}
    root = Path(repo_path).resolve()

    for module in modules:
        module_name = module["name"]
        keywords = [module_name, *module.get("possible_keywords", [])]
        matches = search_keywords(repo_path, keywords)
        candidate_files = _candidate_file_from_matched(matches)

        slices: list[dict] = []
        for rel_path in candidate_files[:5]:
            abs_path = root / rel_path
            if abs_path.exists() and abs_path.suffix in {".py", ".yaml", ".yml", ".json", ".md"}:
                slices.append(
                    {
                        "file_path": rel_path,
                        "content": read_file_slice(str(abs_path), 1, 160)
                    }
                )
        module_search_results[module_name] = {
            "keywords": keywords,
            "matches": matches,
            "candidate_files": candidate_files,
            "code_slices": slices
        }

    return {"code_search_results": module_search_results}
