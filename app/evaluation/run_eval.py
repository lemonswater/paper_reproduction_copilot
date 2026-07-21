import json
from pathlib import Path

from app.graph import build_graph


CASE_DIR = Path("app/evaluation/cases")
OUTPUT_DIR = Path("outputs")


def load_cases() -> list[dict]:
    """
    读取评测目录下全部 case 定义文件。
    """
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CASE_DIR.glob("*.json"))
    ]


def score_mapping_case(case: dict) -> dict:
    """
    对 paper_code_mapping 类型 case 做基础规则打分。
    当前仍然保持轻量策略：
    - must_find_files 命中率
    - must_not_claim 惩罚
    """
    mapping_path = OUTPUT_DIR / "paper_code_mapping.json"
    if not mapping_path.exists():
        return {"score": 0, "reason": "missing paper_code_mapping.json"}

    mapping_text = mapping_path.read_text(encoding="utf-8")
    expected = case.get("expected", {})

    must_find = expected.get("must_find_files", [])
    found_count = sum(1 for item in must_find if item in mapping_text)

    forbidden = expected.get("must_not_claim", [])
    forbidden_count = sum(1 for item in forbidden if item in mapping_text)

    file_recall = found_count / max(len(must_find), 1)
    hallucination_penalty = forbidden_count

    return {
        "file_recall": file_recall,
        "forbidden_claims": forbidden_count,
        "score": max(file_recall - hallucination_penalty, 0),
    }


def run_case(case: dict) -> dict:
    """
    运行单个 case，并返回用于最终汇总的结构化结果。
    """
    graph = build_graph()
    case_id = case["case_id"]
    config = {"configurable": {"thread_id": case_id}}
    inputs = case["input"]

    result = graph.invoke(
        {
            "paper_path": inputs.get("paper_path"),
            "repo_path": inputs.get("repo_path"),
            "log_path": inputs.get("log_path"),
            "experiment_goal": inputs.get("experiment_goal", "复现论文 main result"),
            "output_files": [],
            "step_count": 0,
            "max_steps": 20,
        },
        config=config,
    )

    if case["type"] == "paper_code_mapping":
        score = score_mapping_case(case)
    else:
        score = {"score": None, "reason": "manual review required"}

    output_files = result.get("output_files", [])
    has_final_report = any(path.endswith("final_report.md") for path in output_files)
    has_debug_report = any(path.endswith("debug_report.md") for path in output_files)

    return {
        "case_id": case_id,
        "type": case["type"],
        "final_status": result.get("final_status"),
        "output_files": output_files,
        "has_final_report": has_final_report,
        "has_debug_report": has_debug_report,
        "score": score,
    }


def render_eval_report_md(reports: list[dict]) -> str:
    """
    将结构化评测结果渲染成人可读 markdown 报告。
    """
    lines = ["# Eval Report", ""]

    total = len(reports)
    success_count = sum(1 for item in reports if item.get("final_status") == "succeeded")
    fail_count = sum(1 for item in reports if item.get("final_status") == "failed")
    final_report_count = sum(1 for item in reports if item.get("has_final_report"))
    debug_report_count = sum(1 for item in reports if item.get("has_debug_report"))

    lines += [
        "## Summary",
        "",
        f"- Case Count: {total}",
        f"- Succeeded: {success_count}",
        f"- Failed: {fail_count}",
        f"- Final Report Generated: {final_report_count}/{total}",
        f"- Debug Report Generated: {debug_report_count}/{total}",
        "",
    ]

    lines += ["## Case Details", ""]

    for report in reports:
        lines.append(f"### {report['case_id']}")
        lines.append("")
        lines.append(f"- Type: `{report['type']}`")
        lines.append(f"- Final Status: `{report.get('final_status', 'unknown')}`")
        lines.append(f"- Has Final Report: `{report.get('has_final_report')}`")
        lines.append(f"- Has Debug Report: `{report.get('has_debug_report')}`")

        score = report.get("score", {})
        if score:
            lines.append(f"- Score: `{score.get('score')}`")
            if "file_recall" in score:
                lines.append(f"- Mapping File Recall: `{score.get('file_recall')}`")
            if "forbidden_claims" in score:
                lines.append(f"- Forbidden Claims: `{score.get('forbidden_claims')}`")
            if score.get("reason"):
                lines.append(f"- Note: {score['reason']}")

        output_files = report.get("output_files", [])
        if output_files:
            lines.append("- Output Files:")
            for path in output_files:
                lines.append(f"  - `{path}`")

        lines.append("")

    return "\n".join(lines)


def main():
    reports = [run_case(case) for case in load_cases()]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    report_json_path = OUTPUT_DIR / "eval_report.json"
    report_md_path = OUTPUT_DIR / "eval_report.md"

    report_json_path.write_text(
        json.dumps(reports, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_path.write_text(
        render_eval_report_md(reports),
        encoding="utf-8",
    )

    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()