from __future__ import annotations

import json
from typing import Any

from app.comparison.schemas import ComparisonReport, RunChange


def _inline(value: Any, *, max_chars: int = 240) -> str:
    """生成单行、有界、不会破坏 Markdown 表格的值。"""

    if value is None:
        text = "null"
    elif isinstance(value, str):
        text = value
    else:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    text = text.replace("\n", " ").replace("\r", " ").replace("|", "\\|")
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


def _render_change(change: RunChange) -> str:
    return (
        f"| `{_inline(change.field_path)}` "
        f"| {change.kind} "
        f"| {change.importance} "
        f"| {_inline(change.base_value)} "
        f"| {_inline(change.target_value)} "
        f"| {_inline(change.message)} |"
    )


def render_comparison_markdown(report: ComparisonReport) -> str:
    """只渲染 Comparison 中已经 allowlist、脱敏的字段。"""

    warning_lines = (
        [f"- {_inline(item, max_chars=500)}" for item in report.summary.scope_warnings]
        or ["- 无"]
    )
    change_lines = (
        [_render_change(item) for item in report.changes]
        or ["| `-` | - | - | - | - | 未发现结构化差异 |"]
    )
    return "\n".join(
        [
            "# Run Comparison",
            "",
            f"- Comparison ID: `{report.comparison_id}`",
            f"- Base Job: `{report.base.job_id}` / `{report.base.run_id}`",
            f"- Target Job: `{report.target.job_id}` / `{report.target.run_id}`",
            f"- Comparator: `{report.comparator_version}`",
            "",
            "## Summary",
            "",
            f"- Changes: {report.summary.change_count}",
            f"- Importance: high={report.summary.high_count}, "
            f"medium={report.summary.medium_count}, low={report.summary.low_count}",
            f"- Categories: {', '.join(report.summary.changed_categories) or 'none'}",
            f"- Artifacts: added={report.summary.artifact_added}, "
            f"removed={report.summary.artifact_removed}, "
            f"changed={report.summary.artifact_changed}",
            "",
            "## Scope Warnings",
            "",
            *warning_lines,
            "",
            "## Changes",
            "",
            "| Field | Kind | Importance | Base | Target | Explanation |",
            "|---|---|---|---|---|---|",
            *change_lines,
            "",
            "## Evidence Boundary",
            "",
            "This report compares verified operational facts. It does not prove that "
            "the paper result was scientifically reproduced.",
            "",
        ]
    )


def comparison_chat_projection(report: ComparisonReport) -> str:
    """给 Chat 的有界结构化来源；不把整份 JSON 注入 Prompt。"""

    important = sorted(
        report.changes,
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}[item.importance],
            item.category,
            item.field_path,
        ),
    )[:30]
    payload = {
        "comparison_id": report.comparison_id,
        "comparison_hash": report.comparison_hash,
        "base_job_id": report.base.job_id,
        "target_job_id": report.target.job_id,
        "scope_warnings": report.summary.scope_warnings,
        "summary": report.summary.model_dump(mode="json"),
        "changes": [
            {
                "category": item.category,
                "field_path": item.field_path,
                "kind": item.kind,
                "importance": item.importance,
                "base_value": item.base_value,
                "target_value": item.target_value,
                "message": item.message,
            }
            for item in important
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
