from __future__ import annotations

import pytest

from app.evaluation.runners import (
    ROUTE_FUNCTIONS,
    run_route_case,
)
from app.evaluation.schemas import EvalCase


def _route_case(
    *,
    route_name: str = "route_after_executor",
) -> EvalCase:
    return EvalCase.model_validate(
        {
            "schema_version": 1,
            "case_id": "executor_failed",
            "description": "failed executor routes to debug",
            "suite": "offline",
            "runner": "route_function",
            "categories": ["route"],
            "input": {
                "route_name": route_name,
                "source_node": "executor",
                "state": {
                    "final_status": "failed",
                    "log_path": "/tmp/fixture.log",
                    "stage_errors": [],
                },
            },
            "expected": {
                "exact_route": ["executor", "log_debug"],
            },
        }
    )


def test_route_runner_calls_allowlisted_route() -> None:
    observation = run_route_case(_route_case())

    assert observation.route == ["executor", "log_debug"]
    assert observation.runner == "route_function"


def test_route_runner_rejects_unknown_function() -> None:
    case = _route_case(route_name="os_system")

    assert "os_system" not in ROUTE_FUNCTIONS
    with pytest.raises(ValueError, match="不在 allowlist"):
        run_route_case(case)


def test_route_runner_preserves_source_state() -> None:
    case = _route_case()
    original_state = dict(case.input.state)

    run_route_case(case)

    assert case.input.state == original_state


def test_route_allowlist_contains_only_callables() -> None:
    assert ROUTE_FUNCTIONS
    assert all(
        callable(route)
        for route in ROUTE_FUNCTIONS.values()
    )
