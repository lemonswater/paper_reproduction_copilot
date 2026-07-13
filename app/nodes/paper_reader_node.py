from app.tools.paper_tools import read_paper, split_text


def paper_reader_node(state: dict) -> dict:
    paper_path = state.get("paper_path")
    if not paper_path:
        return {"error": "paper_path is required"}

    paper_text = read_paper(paper_path)
    chunks = split_text(paper_text)

    return {
        "paper_text_chunks": chunks,
        "output_files": state.get("output_files", []),
    }