import json

from app.config import settings
from app.model import get_chat_model
from app.prompts.paper_prompt import PAPER_SUMMARY_PROMPT
from app.schemas import PaperSummary


def _merge_chunks(chunks: list[dict], max_chars: int = 24000) -> str:
    text_parts: list[str] = []
    total = 0
    for chunk in chunks:
        text = chunk["text"]
        if total + len(text) > max_chars:
            break
        text_parts.append(text)
        total += len(text)
    return "\n\n".join(text_parts)


def method_extractor_node(state: dict) -> dict:
    chunks = state.get("paper_text_chunks", [])
    if not chunks:
        return {"error": "paper_text_chunks is empty"}

    paper_text = _merge_chunks(chunks)
    llm = get_chat_model(temperature=0)
    prompt = PAPER_SUMMARY_PROMPT.format(paper_text=paper_text)
    # plain = llm.invoke(prompt)
    result = llm.with_structured_output(PaperSummary, include_raw=True).invoke(prompt)
    summary = result["parsed"]

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    paper_summary_path = settings.output_dir / "paper_summary.json"
    method_modules_path = settings.output_dir / "method_modules.json"

    paper_summary_path.write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    method_modules_path.write_text(
        json.dumps(
            [m.model_dump() for m in summary.method_modules],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "paper_summary": summary.model_dump(),
        "method_modules": [m.model_dump() for m in summary.method_modules],
        "output_files": [
            *state.get("output_files", []),
            str(paper_summary_path),
            str(method_modules_path),
        ],
    }