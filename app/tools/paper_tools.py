from pathlib import Path

import fitz


def read_pdf(path: str) -> str:
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"paper not found: {path}")

    chunks: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                chunks.append(f"[page {page_index + 1}]\n{text}")
    return "\n\n".join(chunks)


def read_text_file(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"paper not found: {path}")
    return file_path.read_text(encoding="utf-8", errors="ignore")


def read_paper(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix in {".md", ".txt"}:
        return read_text_file(path)
    raise ValueError(f"unsupported paper format: {suffix}")


def split_text(text: str, chunk_size: int = 5000, overlap: int = 500) -> list[dict]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[dict] = []
    start = 0
    chunk_id = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(
            {
                "chunk_id": chunk_id,
                "start": start,
                "end": end,
                "text": text[start:end],
            }
        )
        chunk_id += 1
        start = end - overlap
        if start < 0:
            start = 0
        if end == len(text):
            break
    return chunks