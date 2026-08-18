from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.case_loader import (
    load_case_file,
    resolve_evaluation_path,
)
from app.evaluation.schemas import EvalCase


def _route_case_payload() -> dict:
    return {
        "schema_version": 1,
        "case_id": "loader_route_case",
        "description": "loader route case",
        "suite": "offline",
        "runner": "route_function",
        "categories": ["route"],
        "input": {
            "route_name": "route_after_executor",
            "source_node": "executor",
            "state": {},
        },
        "expected": {
            "exact_route": ["executor", "final_report"],
        },
    }


def test_live_graph_must_be_provider_suite() -> None:
    payload = {
        "case_id": "bad_live",
        "description": "bad",
        "suite": "offline",
        "runner": "live_graph",
        "categories": ["quality"],
        "input": {
            "paper_path": "paper.pdf",
            "repo_path": "/tmp/repo",
        },
        "expected": {
            "required_files": ["train-msr.py"],
        },
    }

    with pytest.raises(
        ValidationError,
        match="live_graph 必须放入 provider suite",
    ):
        EvalCase.model_validate(payload)


def test_fixture_path_cannot_escape_evaluation_root() -> None:
    with pytest.raises(ValueError, match="逃逸"):
        resolve_evaluation_path("../../.env")


def test_duplicate_categories_are_rejected() -> None:
    payload = _route_case_payload()
    payload["case_id"] = "duplicate"
    payload["description"] = "duplicate category"
    payload["categories"] = ["route", "route"]

    with pytest.raises(ValidationError, match="不能重复"):
        EvalCase.model_validate(payload)


def test_load_case_file_returns_validated_model(
    tmp_path: Path,
) -> None:
    case_path = tmp_path / "route_case.json"
    case_path.write_text(
        json.dumps(
            _route_case_payload(),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    case = load_case_file(case_path)

    assert isinstance(case, EvalCase)
    assert case.case_id == "loader_route_case"
    assert case.input.route_name == "route_after_executor"


def test_load_case_file_rejects_missing_fixture(
    tmp_path: Path,
) -> None:
    payload = {
        "schema_version": 1,
        "case_id": "missing_fixture",
        "description": "fixture must exist",
        "suite": "offline",
        "runner": "fixture",
        "categories": ["safety"],
        "input": {
            "fixture_path": "fixtures/does_not_exist.json",
        },
        "expected": {
            "max_secret_leaks": 0,
        },
    }
    case_path = tmp_path / "missing_fixture.json"
    case_path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="fixture 不存在"):
        load_case_file(case_path)


def test_chat_fixture_must_exist_under_evaluation_root(tmp_path: Path) -> None:
    case_path = tmp_path / "chat-case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "chat-missing-fixture",
                "description": "missing fixture",
                "suite": "chat_offline",
                "runner": "chat_scenario",
                "categories": ["quality"],
                "input": {
                    "fixture_path": "fixtures/chat/not-found.json",
                },
                "expected": {
                    "chat_turns": [
                        {
                            "label": "turn-1",
                            "expected_refusal": True,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError):
        load_case_file(case_path)
