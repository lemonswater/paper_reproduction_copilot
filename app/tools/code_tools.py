from __future__ import annotations

import ast
from pathlib import Path


def read_file_slice(path: str, start_line: int = 1, end_line: int = 120) -> str:
    file_path = Path(path)
    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = max(start_line, 1)
    end = min(end_line, len(lines))
    numbered = [
        f"{line_no}: {lines[line_no - 1]}"
        for line_no in range(start, end + 1)
    ]
    return "\n".join(numbered)

def extract_python_symbols(path: str) -> list[dict]:
    file_path = Path(path)
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)

    symbols: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(
                {
                    "type": "class",
                    "name": node.name,
                    "line": node.lineno
                }
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                {
                    "type": "function",
                    "name": node.name,
                    "line": node.lineno
                }
            )
    return sorted(symbols, key=lambda item: item["line"])
