from pathlib import Path

ERROR_KEYWORDS = [
    "Traceback",
    "RuntimeError",
    "ValueError",
    "ImportError",
    "ModuleNotFoundError",
    "FileNotFoundError",
    "CUDA out of memory",
    "shape",
    "size mismatch"
]

def read_log(path: str, max_chars: int = 30000) -> str:
    log_path = Path(path)
    if not log_path.exists():
        raise FileNotFoundError(f"log not found: {path}")
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    return text[-max_chars:]

def extract_traceback(log_text: str) -> str:
    index = log_text.rfind("Traceback")
    if index >= 0:
        return log_text[index:]
    lines = log_text.splitlines()
    suspicious = [
        line for line in lines if any(keyword.lower() in line.lower() for keyword in ERROR_KEYWORDS)
    ]
    return "\n".join(suspicious[-80:])

def classify_error_heuristic(traceback: str) -> str:
    lower = traceback.lower()
    if "modulenotfounderror" in lower or "importerror" in lower:
        return "dependency_missing"
    if "filenotfounderror" in lower or "no such file" in lower:
        return "data_or_path_error"
    if "cuda out of memory" in lower:
        return "cuda_oom"
    if "size mismatch" in lower or "shape" in lower:
        return "shape_mismatch"
    if "permission denied" in lower:
        return "permission_error"
    return "unknown"