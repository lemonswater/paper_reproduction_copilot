from app.evaluation.run_eval import render_eval_report_md


def test_render_eval_report_md_contains_summary_and_case_details() -> None:
    reports = [
        {
            "case_id": "case_success",
            "type": "paper_code_mapping",
            "final_status": "succeeded",
            "has_final_report": True,
            "has_debug_report": False,
            "output_files": ["outputs/final_report.md"],
            "score": {
                "score": 1.0,
                "file_recall": 1.0,
                "forbidden_claims": 0,
            },
        },
        {
            "case_id": "case_fail",
            "type": "paper_code_mapping",
            "final_status": "failed",
            "has_final_report": True,
            "has_debug_report": True,
            "output_files": ["outputs/final_report.md", "outputs/debug_report.md"],
            "score": {
                "score": 0.5,
                "file_recall": 0.5,
                "forbidden_claims": 0,
            },
        },
    ]

    text = render_eval_report_md(reports)

    assert "# Eval Report" in text
    assert "## Summary" in text
    assert "Succeeded: 1" in text
    assert "Failed: 1" in text
    assert "### case_success" in text
    assert "### case_fail" in text
    assert "Has Debug Report: `True`" in text