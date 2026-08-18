from __future__ import annotations

from app.paper.indexer import index_paper_to_artifacts
from app.tools.artifact_tools import artifact_state_update
from app.tools.error_tools import stage_error_result


def paper_reader_node(state: dict) -> dict:
    paper_path = state.get("paper_path")
    if not paper_path:
        return stage_error_result(
            state=state,
            stage="paper_reader",
            code="PAPER_PATH_MISSING",
            category="user",
            message="必须提供 paper_path",
            terminal=True,
            extra_update={
                "paper_document": {},
                "paper_blocks_path": None,
                "paper_sections_path": None,
                "paper_parse_report_path": None,
            },
        )

    # FileNotFoundError、格式错误和解析异常交给现有 guard_node 统一分类。
    indexed = index_paper_to_artifacts(
        state=state,
        paper_path=str(paper_path),
    )
    update = {
        "paper_document": indexed.document.model_dump(mode="json"),
        "paper_blocks_path": str(indexed.blocks_path),
        "paper_sections_path": str(indexed.sections_path),
        "paper_parse_report_path": str(indexed.report_path),
        **artifact_state_update(state, indexed.records),
    }

    if indexed.parsed.report.status == "failed":
        working_state = {**state, **update}
        return stage_error_result(
            state=working_state,
            stage="paper_reader",
            code="PAPER_PARSE_FAILED",
            category="user",
            message="论文没有提取到任何可用文本 block",
            terminal=True,
            context={
                "paper_path": str(paper_path),
                "page_count": indexed.parsed.report.page_count,
            },
            extra_update=update,
        )

    # partial 不是 terminal。OCR/table warning 已位于 parse report。
    return update