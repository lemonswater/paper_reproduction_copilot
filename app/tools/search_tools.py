import subprocess
from pathlib import Path


def search_text(repo_path: str, query: str, max_results: int = 20) -> list[dict]:
    root = Path(repo_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"repo not fount: {repo_path}")
    
    result = subprocess.run(
        [
            "rg",
            "--line-number",
            "--no-heading",
            "--glob",
            "!{.git,__pycache__,outputs,checkpoints,wandb}/**",
            query,
            str(root)
        ],
        check=False,
        capture_output=True,
        text=True
    )

    matches: list[dict] = []
    for line in result.stdout.splitlines()[:max_results]:
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        file_path, line_no, text = parts
        matches.append(
            {
                "file_path": str(Path(file_path).relative_to(root)),
                "line": int(line_no),
                "text": text.strip()
            }
        )
    return matches

def search_keywords(repo_path: str, keywords: list[str], max_per_keyword: int = 10) -> list[dict]:
    all_matches: list[dict] = []
    seen: set[tuple[str, int, str]] = set()

    for keyword in keywords:
        if not keyword.strip():
            continue
        for match in search_text(repo_path, keyword, max_results=max_per_keyword):
            key = (match["file_path"], match["line"], match["text"])
            if key not in seen:
                seen.add(key)
                match["keyword"] = keyword
                all_matches.append(match)
    return all_matches
