from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.model as model_module
from app.evaluation import runners
from app.evaluation.schemas import (
    EvalCase,
    EvalObservation,
    PaperSectionObservation,
)
from app.evaluation.scorers import score_evidence, score_quality


def _paper_parser_case(
    *,
    expected: dict | None = None,
) -> EvalCase:
    """构造不依赖真实 PDF 的最小 paper_parser Golden Case。"""

    return EvalCase.model_validate(
        {
            "schema_version": 1,
            "case_id": "paper_parser_test",
            "description": "paper parser evaluation test",
            "suite": "offline",
            "runner": "paper_parser",
            "categories": ["quality"],
            "input": {
                "paper_path": "paper.pdf",
            },
            "expected": expected
            or {
                "min_indexed_page_ratio": 1.0,
            },
        }
    )


def _failed_codes(result) -> set[str]:
    return {
        assertion.code
        for assertion in result.assertions
        if not assertion.passed
    }


def test_paper_parser_case_can_be_validated() -> None:
    case = _paper_parser_case()

    assert case.runner == "paper_parser"
    assert case.suite == "offline"
    assert case.input.paper_path == "paper.pdf"


def test_paper_parser_runner_does_not_call_chat_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("paper_parser runner must not call a chat model")

    monkeypatch.setattr(
        model_module,
        "get_chat_model",
        fail_if_called,
    )
    # 同时放置 runner 全局哨兵，避免未来改成直接 import 后测试失去保护。
    monkeypatch.setattr(
        runners,
        "get_chat_model",
        fail_if_called,
        raising=False,
    )
    monkeypatch.setattr(
        runners,
        "_resolve_eval_paper_path",
        lambda _: Path("/allowed/paper.pdf"),
    )
    monkeypatch.setattr(
        runners,
        "parse_paper_source",
        lambda _: SimpleNamespace(
            report=SimpleNamespace(
                status="succeeded",
                page_count=2,
                indexed_pages=[1, 2],
                ocr_required_pages=[],
            ),
            sections=[
                SimpleNamespace(
                    section_id="sec-abstract",
                    number=None,
                    title="Abstract",
                    kind="abstract",
                    parent_id=None,
                )
            ],
        ),
    )

    observation = runners.run_paper_parser_case(_paper_parser_case())

    assert observation.final_status == "succeeded"
    assert observation.metrics.llm_calls == 0
    assert observation.paper_indexed_pages == [1, 2]
    assert observation.paper_sections == [
        PaperSectionObservation(
            number=None,
            title="Abstract",
            parent_number=None,
            parent_title=None,
        )
    ]


def test_quality_scores_full_page_ratio_for_23_of_23_pages() -> None:
    case = _paper_parser_case(
        expected={"min_indexed_page_ratio": 1.0}
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        paper_page_count=23,
        paper_indexed_pages=list(range(1, 24)),
    )

    result = score_quality(case, observation)

    assert result.passed is True
    assertion = result.assertions[0]
    assert assertion.code == "QUALITY_PAPER_INDEXED_PAGE_RATIO"
    assert assertion.actual == 1.0


def test_quality_fails_when_implementation_section_is_missing() -> None:
    case = _paper_parser_case(
        expected={"required_section_kinds": ["implementation"]}
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        paper_section_kinds=["abstract", "method", "experiments"],
    )

    result = score_quality(case, observation)

    assert result.passed is False
    assert (
        "QUALITY_PAPER_SECTION_KIND:implementation"
        in _failed_codes(result)
    )


def test_quality_title_uses_normalized_contains_matching() -> None:
    case = _paper_parser_case(
        expected={
            "required_section_titles": ["Implementation Details"],
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        paper_section_titles=[
            "C I MPLEMENTATION D ETAILS",
        ],
    )

    result = score_quality(case, observation)

    assert result.passed is True
    assert result.assertions[0].code == (
        "QUALITY_PAPER_SECTION_TITLE:Implementation Details"
    )


def test_evidence_scores_exact_paper_provenance_ratio() -> None:
    case = EvalCase.model_validate(
        {
            "case_id": "paper_provenance",
            "description": "paper provenance ratio",
            "suite": "offline",
            "runner": "fixture",
            "categories": ["evidence"],
            "input": {
                "fixture_path": "fixtures/unused.json",
            },
            "expected": {
                "min_paper_evidence_provenance_ratio": 0.75,
            },
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="fixture",
        paper_evidence_count=4,
        paper_provenance_evidence_count=3,
    )

    result = score_evidence(case, observation)

    assert result.passed is True
    assertion = result.assertions[0]
    assert assertion.code == "EVIDENCE_PAPER_PROVENANCE_RATIO"
    assert assertion.actual == 0.75


def test_quality_fails_when_ocr_and_conflicts_exceed_limits() -> None:
    case = _paper_parser_case(
        expected={
            "max_paper_conflicts": 0,
            "max_ocr_required_pages": 0,
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        paper_conflict_count=1,
        paper_ocr_required_pages=[7],
    )

    result = score_quality(case, observation)

    assert result.passed is False
    assert _failed_codes(result) == {
        "QUALITY_PAPER_CONFLICTS",
        "QUALITY_PAPER_OCR_REQUIRED",
    }


def test_phase17_fixture_loads_with_phase18_defaults() -> None:
    fixture_path = Path(
        "app/evaluation/fixtures/mapping_quality_pstnet.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    observation = EvalObservation.model_validate(payload)

    assert observation.case_id == "mapping_quality_pstnet"
    assert observation.paper_page_count == 0
    assert observation.paper_indexed_pages == []
    assert observation.paper_section_titles == []
    assert observation.paper_section_kinds == []
    assert observation.paper_experiment_setting_names == []
    assert observation.paper_conflict_count == 0
    assert observation.paper_ocr_required_pages == []
    assert observation.paper_evidence_count == 0
    assert observation.paper_provenance_evidence_count == 0
    assert observation.paper_sections == []

def test_quality_fails_when_section_count_is_too_large() -> None:
    case = _paper_parser_case(
        expected={
            "min_section_count": 35,
            "max_section_count": 45,
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        paper_section_titles=[
            f"Section {index}"
            for index in range(87)
        ],
    )

    result = score_quality(case, observation)

    assert result.passed is False
    assert (
        "QUALITY_PAPER_SECTION_COUNT_MAX"
        in _failed_codes(result)
    )


def test_quality_rejects_exact_and_term_titles() -> None:
    case = _paper_parser_case(
        expected={
            "forbidden_exact_section_titles": [
                "W",
            ],
            "forbidden_section_title_terms": [
                "and pooling techniques",
            ],
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        paper_section_titles=[
            "W",
            (
                "and pooling techniques "
                "(Fan et al., 2017) are employed"
            ),
        ],
    )

    result = score_quality(case, observation)

    assert result.passed is False
    failed = _failed_codes(result)
    assert any(
        code.startswith(
            "QUALITY_PAPER_SECTION_FORBIDDEN_EXACT"
        )
        for code in failed
    )
    assert any(
        code.startswith(
            "QUALITY_PAPER_SECTION_FORBIDDEN_TERM"
        )
        for code in failed
    )


def test_quality_requires_exact_multiline_title() -> None:
    case = _paper_parser_case(
        expected={
            "required_exact_section_titles": [
                (
                    "PSTNET: POINT SPATIO-TEMPORAL "
                    "CONVOLUTION ON POINT CLOUD SEQUENCES"
                )
            ],
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        paper_section_titles=[
            (
                "PSTNET: POINT SPATIO-TEMPORAL "
                "CONVOLUTION"
            ),
            "ON POINT CLOUD SEQUENCES",
        ],
    )

    result = score_quality(case, observation)

    assert result.passed is False


def test_quality_checks_numbered_parent_relation() -> None:
    case = _paper_parser_case(
        expected={
            "required_parent_relations": [
                {
                    "child_number": "3.2.2",
                    "parent_number": "3.2",
                }
            ],
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        paper_sections=[
            PaperSectionObservation(
                number="3.2.2",
                title="POINT TUBE",
                parent_number="3",
                parent_title="METHOD",
            )
        ],
    )

    result = score_quality(case, observation)

    assert result.passed is False
    assert "QUALITY_PAPER_PARENT:3.2.2" in (
        _failed_codes(result)
    )


def test_quality_accepts_complete_section_structure() -> None:
    case = _paper_parser_case(
        expected={
            "required_exact_section_titles": [
                (
                    "PSTNET: POINT SPATIO-TEMPORAL "
                    "CONVOLUTION ON POINT CLOUD SEQUENCES"
                )
            ],
            "forbidden_exact_section_titles": ["W"],
            "min_section_count": 2,
            "max_section_count": 4,
            "required_parent_relations": [
                {
                    "child_number": "3.2.2",
                    "parent_number": "3.2",
                }
            ],
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner="paper_parser",
        paper_section_titles=[
            (
                "PSTNET: POINT SPATIO-TEMPORAL "
                "CONVOLUTION ON POINT CLOUD SEQUENCES"
            ),
            "PST CONVOLUTION",
            "POINT TUBE",
        ],
        paper_sections=[
            PaperSectionObservation(
                number=None,
                title=(
                    "PSTNET: POINT SPATIO-TEMPORAL "
                    "CONVOLUTION ON POINT CLOUD SEQUENCES"
                ),
            ),
            PaperSectionObservation(
                number="3.2",
                title="PST CONVOLUTION",
                parent_number="3",
                parent_title="METHOD",
            ),
            PaperSectionObservation(
                number="3.2.2",
                title="POINT TUBE",
                parent_number="3.2",
                parent_title="PST CONVOLUTION",
            ),
        ],
    )

    result = score_quality(case, observation)

    assert result.passed is True
