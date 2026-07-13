import json
from pathlib import Path

from app.graph import build_graph


CASE_DIR = Path("app/evaluation/cases")
OUTPUT_DIR = Path("outputs")


# 读取评测目录下的全部 case 定义文件。
def load_cases() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CASE_DIR.glob("*.json"))
    ]


# 对 paper-code mapping case 进行基础规则打分。
def score_mapping_case(case: dict) -> dict:
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


# 运行单个评测 case，并汇总输出文件和得分结果。
def run_case(case: dict) -> dict:
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
        },
        config=config,
    )

    if case["type"] == "paper_code_mapping":
        score = score_mapping_case(case)
    else:
        score = {"score": None, "reason": "manual review required"}

    return {
        "case_id": case_id,
        "type": case["type"],
        "output_files": result.get("output_files", []),
        "score": score,
    }


# 运行全部评测 case，并写出最终评测报告。
def main():
    reports = [run_case(case) for case in load_cases()]
    report_path = OUTPUT_DIR / "eval_report.json"
    report_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()