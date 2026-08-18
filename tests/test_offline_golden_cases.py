from __future__ import annotations

from app.config import settings
from app.evaluation.case_loader import load_cases
from app.evaluation.runners import run_case
from app.evaluation.scorers import score_case

CORE_CATEGORIES = {
    "schema",
    "route",
    "tool",
    "evidence",
    "safety",
    "recovery",
    "quality",
    "efficiency",
}

FIRST_BATCH_CASES = {
    "schema_retry_then_success_without_fallback",
    "route_executor_failure_to_debug",
    "route_terminal_error_to_final",
    "stale_action_approval_blocked",
    "secret_canary_not_leaked",
    "resume_without_duplicate_effect",
    "mapping_quality_pstnet",
}


def test_first_offline_golden_batch_covers_core_categories() -> None:
    cases = load_cases(suite="offline")
    case_ids = {case.case_id for case in cases}
    categories = {
        category
        for case in cases
        for category in case.categories
    }

    assert FIRST_BATCH_CASES <= case_ids
    assert categories == CORE_CATEGORIES


def test_all_offline_golden_cases_run_and_score_without_provider() -> None:
    cases = load_cases(suite="offline")

    results = [
        score_case(case, run_case(case))
        for case in cases
    ]

    failures = {
        result.case_id: [
            assertion.code
            for scorer in result.scorer_results
            for assertion in scorer.assertions
            if not assertion.passed
        ]
        for result in results
        if not result.passed
    }
    assert failures == {}


def test_route_setting_override_is_restored_after_case() -> None:
    original = settings.enable_file_repair
    case = next(
        item
        for item in load_cases(suite="offline")
        if item.case_id == "route_manual_only_to_file_repair"
    )

    observation = run_case(case)

    assert observation.route == [
        "repair_planner",
        "file_repair_planner",
    ]
    assert settings.enable_file_repair is original


def test_mapping_fixture_uses_sha256_shaped_evidence_hashes() -> None:
    case = next(
        item
        for item in load_cases(suite="offline")
        if item.case_id == "mapping_quality_pstnet"
    )

    observation = run_case(case)

    assert observation.evidence
    assert all(
        item.content_sha256 is not None
        and len(item.content_sha256) == 64
        for item in observation.evidence
    )


def test_pstnet_golden_cases_use_current_repository_layout() -> None:
    cases = {
        case.case_id: case
        for case in load_cases(suite="offline")
    }

    resume_case = cases["resume_without_duplicate_effect"]
    tool_requirement = resume_case.expected.required_tool_calls[0]
    assert tool_requirement.args_subset == {
        "program": "python",
        "cwd": "/data/tianshaoqi24/PST-Convolution-main/",
    }

    resume_observation = run_case(resume_case)
    assert resume_observation.tool_calls[0].args["args"] == [
        "train-msr.py",
        "--help",
    ]

    secret_case = cases["secret_canary_not_leaked"]
    secret_observation = run_case(secret_case)
    assert secret_observation.tool_calls[0].args["cwd"] == (
        "/data/tianshaoqi24/PST-Convolution-main/"
    )

    mapping_case = cases["mapping_quality_pstnet"]
    assert mapping_case.expected.required_modules == [
        "PSTConv",
        "MSRAction",
    ]
    assert mapping_case.expected.required_files == [
        "modules/pst_convolutions.py",
        "models/sequence_classification.py",
    ]
