from __future__ import annotations

import json

from app.evaluation.schemas import (
    BaselineDiff,
    EvalSuiteResult,
)


def _value(value) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= 800 else text[:800] + "...<truncated>"


def render_eval_report(
    result: EvalSuiteResult,
    diff: BaselineDiff | None,
) -> str:
    passed_count = sum(item.passed for item in result.case_results)
    lines = [
        "# Agent Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Eval ID：`{result.eval_id}`",
        f"- Suite：`{result.suite}`",
        f"- Passed：`{result.passed}`",
        f"- Overall score：`{result.overall_score:.4f}`",
        f"- Cases：`{passed_count}/{len(result.case_results)}`",
        f"- Revision：`{result.revision or 'unknown'}`",
        f"- Dirty worktree：`{result.dirty_worktree}`",
        "",
        "## Category Scores",
        "",
        "| Category | Score |",
        "|---|---:|",
    ]

    for name, score in sorted(result.category_scores.items()):
        lines.append(f"| {name} | {score:.4f} |")

    lines.extend(["", "## Problem Coverage", ""])
    for problem_id, case_ids in sorted(result.problem_coverage.items()):
        lines.append(
            f"- Problem {problem_id}："
            + ", ".join(f"`{item}`" for item in case_ids)
        )

    if diff is not None:
        lines.extend(
            [
                "",
                "## Baseline Diff",
                "",
                f"- Passed：`{diff.passed}`",
                f"- New cases：`{diff.new_cases}`",
                f"- Missing cases：`{diff.missing_cases}`",
                f"- Newly failed：`{diff.newly_failed_cases}`",
                f"- Score regressions：`{len(diff.score_regressions)}`",
            ]
        )
        for item in diff.score_regressions:
            lines.append(
                "- "
                f"`{item['case_id']}` "
                f"({item.get('category', 'overall')})："
                f"{item['baseline_score']:.4f} -> "
                f"{item['current_score']:.4f} "
                f"(delta={item['delta']:.4f})"
            )

    lines.extend(["", "## Case Details", ""])
    for case_result in result.case_results:
        lines.extend(
            [
                f"### {case_result.case_id}",
                "",
                f"- Passed：`{case_result.passed}`",
                f"- Score：`{case_result.overall_score:.4f}`",
                f"- Runner：`{case_result.runner}`",
                f"- Observation：`{case_result.observation_path}`",
            ]
        )
        if case_result.error:
            lines.append(f"- Runner error：{case_result.error}")

        for scorer in case_result.scorer_results:
            lines.extend(
                [
                    "",
                    f"#### {scorer.category}",
                    "",
                    f"- Passed：`{scorer.passed}`",
                    f"- Score：`{scorer.score:.4f}`",
                ]
            )
            for assertion in scorer.assertions:
                marker = "PASS" if assertion.passed else "FAIL"
                lines.extend(
                    [
                        (
                            f"- `{marker}` `{assertion.code}`："
                            f"{assertion.message}"
                        ),
                        f"  - expected：`{_value(assertion.expected)}`",
                        f"  - actual：`{_value(assertion.actual)}`",
                    ]
                )
        lines.append("")

    return "\n".join(lines)