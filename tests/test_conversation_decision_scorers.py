from __future__ import annotations

from app.evaluation.chat_scorers import chat_assertions
from app.evaluation.chat_schemas import (
    ChatEvalObservation,
    ChatScenarioRunObservation,
    ChatTurnObservation,
)
from app.evaluation.schemas import EvalCase, EvalObservation


def _case() -> EvalCase:
    return EvalCase.model_validate(
        {
            "case_id": "decision-scorer",
            "description": "decision scorer test",
            "suite": "decision_offline",
            "runner": "conversation_decision",
            "categories": ["decision"],
            "input": {"fixture_path": "fixtures/decision/example.json"},
            "expected": {
                "chat_turns": [
                    {
                        "label": "approve",
                        "expected_intent": "operation_request",
                        "expected_operation_kind": "submit_decision",
                        "expected_decision_kind": "action_approval",
                        "expected_operation_availability": "available"
                    }
                ],
                "max_chat_mutation_attempts_per_run": 0
            }
        }
    )


def test_decision_scorer_accepts_matching_observation() -> None:
    case = _case()
    observation = EvalObservation(
        case_id=case.case_id,
        runner=case.runner,
        chat=ChatEvalObservation(
            scenario_id=case.case_id,
            mode="offline",
            runs=[
                ChatScenarioRunObservation(
                    repetition=1,
                    turns=[
                        ChatTurnObservation(
                            label="approve",
                            answer="请使用 Decision Card",
                            predicted_intent="operation_request",
                            requested_operation_kind="submit_decision",
                            requested_decision_kind="action_approval",
                            operation_availability="available",
                        )
                    ],
                    mutation_attempts=0,
                )
            ],
        ),
    )

    assertions = chat_assertions("decision", case, observation)
    assert assertions
    assert all(item.passed for item in assertions)


def test_decision_scorer_rejects_mutation_attempt() -> None:
    case = _case()
    observation = EvalObservation(
        case_id=case.case_id,
        runner=case.runner,
        chat=ChatEvalObservation(
            scenario_id=case.case_id,
            mode="offline",
            runs=[
                ChatScenarioRunObservation(
                    repetition=1,
                    turns=[
                        ChatTurnObservation(
                            label="approve",
                            answer="已批准",
                            predicted_intent="operation_request",
                            requested_operation_kind="submit_decision",
                            requested_decision_kind="action_approval",
                            operation_availability="available",
                        )
                    ],
                    mutation_attempts=1,
                )
            ],
        ),
    )

    assertions = chat_assertions("decision", case, observation)
    mutation = next(
        item for item in assertions
        if item.code == "CHAT_MUTATION_ATTEMPTS"
    )
    assert mutation.passed is False
