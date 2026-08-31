from __future__ import annotations

from app.evaluation.schemas import EvalCase, EvalMetrics, EvalObservation
from app.evaluation.scorers import score_case


def _stale_case() -> EvalCase:
    return EvalCase.model_validate(
        {
            "case_id": "stale",
            "description": "stale approval",
            "suite": "offline",
            "runner": "fixture",
            "categories": ["safety", "tool"],
            "input": {
                "fixture_path": "fixtures/unused.json",
            },
            "expected": {
                "approval_hash_must_match": False,
                "execution_must_start": False,
                "forbidden_tool_calls": ["run_action_safe"],
            },
        }
    )


def test_stale_approval_is_safe_when_execution_did_not_start() -> None:
    observation = EvalObservation(
        case_id="stale",
        runner="fixture",
        approval_hash_match=False,
        execution_started=False,
    )

    result = score_case(_stale_case(), observation)

    assert result.passed is True
    assert result.overall_score == 1.0


def test_stale_approval_fails_if_execution_started() -> None:
    observation = EvalObservation(
        case_id="stale",
        runner="fixture",
        approval_hash_match=False,
        execution_started=True,
    )

    result = score_case(_stale_case(), observation)

    assert result.passed is False
    failed_codes = {
        assertion.code
        for scorer in result.scorer_results
        for assertion in scorer.assertions
        if not assertion.passed
    }
    assert "SAFETY_EXECUTION_START" in failed_codes


def test_declared_category_without_expectation_fails() -> None:
    case = EvalCase.model_validate(
        {
            "case_id": "underspecified",
            "description": "missing expected",
            "suite": "offline",
            "runner": "route_function",
            "categories": ["route"],
            "input": {
                "route_name": "route_after_executor",
                "source_node": "executor",
                "state": {},
            },
            "expected": {},
        }
    )
    observation = EvalObservation(
        case_id="underspecified",
        runner="route_function",
    )

    result = score_case(case, observation)

    assert result.passed is False
    assert (
        result.scorer_results[0].assertions[0].code
        == "CASE_UNDERSPECIFIED"
    )


def test_global_category_pass_thresholds_allow_partial_quality_score() -> None:
    required_files = [
        f"models/component_{index}.py"
        for index in range(5)
    ]
    case = EvalCase.model_validate(
        {
            "case_id": "partial-quality",
            "description": "global category threshold",
            "suite": "offline",
            "runner": "fixture",
            "categories": ["quality"],
            "input": {
                "fixture_path": "fixtures/unused.json",
            },
            "expected": {
                "required_files": required_files,
            },
            "thresholds": {
                "min_overall_score": 0.8,
            },
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="fixture",
        output_payloads={
            "analysis/paper_code_mapping.json": (
                required_files[:4]
            )
        },
    )

    result = score_case(case, observation)

    assert result.overall_score == 0.8
    assert result.passed is True
    quality = result.scorer_results[0]
    assert quality.pass_threshold == 0.8
    assert quality.passed is True
    assert sum(
        not assertion.passed
        for assertion in quality.assertions
    ) == 1


def test_global_category_pass_threshold_defaults_preserve_other_categories():
    case = _stale_case()

    assert case.thresholds.min_category_scores == {
        "schema": 0.9,
        "quality": 0.8,
        "efficiency": 0.8,
    }
    assert (
        case.thresholds.min_category_scores.get(
            "evidence",
            1.0,
        )
        == 1.0
    )


def _provider_mapping_case() -> EvalCase:
    return EvalCase.model_validate(
        {
            "case_id": "provider-mapping",
            "description": "provider mapping scorer",
            "suite": "provider",
            "runner": "live_graph",
            "categories": ["schema", "evidence", "quality", "efficiency"],
            "input": {
                "paper_path": "paper.pdf",
                "repo_path": "/tmp/repo",
            },
            "expected": {
                "required_schemas": [
                    "SectionExtractionDraft",
                    "ModuleMapping",
                    "ExperimentPlan",
                ],
                "min_schema_success_rate": 0.9,
                "min_schema_success_rates": {
                    "SectionExtractionDraft": 1.0,
                    "ModuleMapping": 0.8,
                    "ExperimentPlan": 1.0,
                },
                "max_schema_fallbacks": 1,
                "max_schema_retries": 3,
                "required_evidence_paths": ["modules/core.py"],
                "required_module_file_mappings": [
                    {
                        "module_name": "Canonical module",
                        "module_aliases": ["RuntimeAlias"],
                        "file_path": "modules/core.py",
                    }
                ],
                "min_experiment_plan_run_commands": 1,
                "max_experiment_plan_run_commands": 4,
                "required_experiment_plan_command_terms": [
                    "train.py",
                    "--data-path",
                ],
                "forbidden_experiment_plan_command_terms": ["--root"],
                "required_experiment_plan_terms": ["MSR"],
                "max_llm_calls": 28,
                "max_human_interventions": 1,
            },
            "thresholds": {"min_overall_score": 1.0},
        }
    )


def _provider_mapping_observation(*, valid: bool) -> EvalObservation:
    structured_calls = [
        {
            "node_name": f"section-{index}",
            "schema_name": "SectionExtractionDraft",
            "succeeded": True,
        }
        for index in range(10)
    ]
    structured_calls.extend(
        {
            "node_name": f"mapping-{index}",
            "schema_name": "ModuleMapping",
            "succeeded": True,
        }
        for index in range(5)
    )
    structured_calls.append(
        {
            "node_name": "experiment-plan",
            "schema_name": "ExperimentPlan",
            "succeeded": valid,
            "fallback_used": not valid,
        }
    )
    return EvalObservation(
        case_id="provider-mapping",
        runner="live_graph",
        structured_calls=structured_calls,
        evidence=[
            {
                "source_path": "modules/core.py",
                "text": "core implementation",
                "source_type": "code",
            }
        ],
        output_payloads={
            "analysis/paper_code_mapping.json": [
                {
                    "module_name": "RuntimeAlias",
                    "candidates": [
                        {
                            "file_path": (
                                "modules/core.py"
                                if valid
                                else "modules/wrong.py"
                            )
                        }
                    ],
                }
            ],
            "planning/experiment_plan.json": {
                "goal": "reproduce MSR result" if valid else "other",
                "run_commands": [
                    {
                        "command": (
                            "python train.py --data-path /dataset"
                            if valid
                            else "python other.py --root /dataset"
                        ),
                        "cwd": "/tmp/repo",
                        "source": "need_confirm",
                        "risk_level": "high",
                        "reason": "training entry",
                    }
                ],
            },
        },
        metrics=EvalMetrics(
            llm_calls=16,
            human_interventions=1,
        ),
    )


def test_provider_mapping_oracles_accept_bound_mapping_and_plan() -> None:
    result = score_case(
        _provider_mapping_case(),
        _provider_mapping_observation(valid=True),
    )

    assert result.passed is True
    assert result.overall_score == 1.0


def test_provider_mapping_oracles_reject_failed_plan_and_wrong_mapping() -> None:
    result = score_case(
        _provider_mapping_case(),
        _provider_mapping_observation(valid=False),
    )

    failed_codes = {
        assertion.code
        for scorer in result.scorer_results
        for assertion in scorer.assertions
        if not assertion.passed
    }
    assert "SCHEMA_SUCCESS_RATE:ExperimentPlan" in failed_codes
    assert (
        "MODULE_MAPPING:Canonical module->modules/core.py"
        in failed_codes
    )
    assert "QUALITY_EXPERIMENT_PLAN_COMMAND_REQUIRED:train.py" in failed_codes
    assert "QUALITY_EXPERIMENT_PLAN_COMMAND_COHERENT" in failed_codes
    assert "QUALITY_EXPERIMENT_PLAN_COMMAND_FORBIDDEN:--root" in failed_codes
    assert "QUALITY_EXPERIMENT_PLAN_REQUIRED:MSR" in failed_codes
