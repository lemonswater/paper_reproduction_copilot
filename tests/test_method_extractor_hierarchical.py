from __future__ import annotations

import hashlib
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.config import settings
from app.nodes.method_extractor_node import method_extractor_node
from app.paper.schemas import (
    EvidenceDraft,
    ExperimentSettingDraft,
    PaperBlock,
    PaperDocument,
    PaperParseReport,
    PaperSection,
    SectionExtractionDraft,
    TextFactDraft,
)
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.structured_output_tools import invoke_structured_with_retry
from tests.helpers.model_routing import ScriptedModelGateway


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _prompt_metadata(prompt: str, name: str) -> str:
    match = re.search(
        rf"^- {re.escape(name)}: (.+)$",
        prompt,
        flags=re.MULTILINE,
    )
    if match is None:
        raise AssertionError(f"prompt 缺少元数据：{name}")
    return match.group(1).strip()


def _prompt_blocks(prompt: str) -> list[tuple[str, str]]:
    return re.findall(
        r"\[([^\]]+)\]\[page \d+\] ([^\n]+)",
        prompt,
    )


def _success_response(prompt: str) -> dict:
    section_id = _prompt_metadata(prompt, "section_id")
    chunk_id = _prompt_metadata(prompt, "chunk_id")
    blocks = _prompt_blocks(prompt)
    if not blocks:
        raise AssertionError("prompt 中没有可引用的 block")

    evidence_block_id = blocks[0][0]
    for block_id, text in blocks:
        if "35 epochs" in text:
            evidence_block_id = block_id
            break

    evidence = EvidenceDraft(
        block_ids=[evidence_block_id],
        summary="Evidence selected by the deterministic fake LLM.",
        confidence=0.9,
    )
    kwargs = {}

    if "35 epochs" in prompt:
        kwargs["experiment_settings"] = [
            ExperimentSettingDraft(
                name="training epochs",
                value="35",
                evidence=evidence,
            )
        ]
    elif "action recognition" in prompt:
        kwargs["research_problem_candidates"] = [
            TextFactDraft(
                value=(
                    "Recognize actions in dynamic point cloud sequences."
                ),
                evidence=evidence,
            )
        ]

    parsed = SectionExtractionDraft(
        section_id=section_id,
        chunk_id=chunk_id,
        summary="Successful deterministic section extraction.",
        **kwargs,
    )
    return {
        "raw": SimpleNamespace(content='{"status":"ok"}'),
        "parsed": parsed,
        "parsing_error": None,
    }


def _failure_response() -> dict:
    return {
        "raw": SimpleNamespace(content='{"invalid":true}'),
        "parsed": None,
        "parsing_error": ValueError(
            "synthetic structured output failure"
        ),
    }


def _empty_response(prompt: str) -> dict:
    parsed = SectionExtractionDraft(
        section_id=_prompt_metadata(prompt, "section_id"),
        chunk_id=_prompt_metadata(prompt, "chunk_id"),
        summary="",
    )
    return {
        "raw": SimpleNamespace(content='{"status":"empty"}'),
        "parsed": parsed,
        "parsing_error": None,
    }


def _invalid_evidence_response(prompt: str) -> dict:
    parsed = SectionExtractionDraft(
        section_id=_prompt_metadata(prompt, "section_id"),
        chunk_id=_prompt_metadata(prompt, "chunk_id"),
        summary="Invalid evidence response.",
        core_idea_candidates=[
            TextFactDraft(
                value="Unsupported claim.",
                evidence=EvidenceDraft(
                    block_ids=["invented-block-id"],
                    summary="Invented evidence.",
                    confidence=0.9,
                ),
            )
        ],
    )
    return {
        "raw": SimpleNamespace(content='{"status":"invalid"}'),
        "parsed": parsed,
        "parsing_error": None,
    }


class FakeStructuredRunnable:
    """按顺序消费结果，并保存节点实际发送的 prompt。"""

    def __init__(self, outcomes: list[str]):
        self.outcomes = list(outcomes)
        self.prompts: list[str] = []

    def invoke(
        self,
        prompt: str,
        config: dict | None = None,
    ) -> dict:
        self.prompts.append(prompt)
        if not self.outcomes:
            raise AssertionError(
                "fake LLM 没有剩余响应，说明发生了意外模型调用"
            )

        outcome = self.outcomes.pop(0)
        if outcome == "success":
            return _success_response(prompt)
        if outcome == "failure":
            return _failure_response()
        if outcome == "empty":
            return _empty_response(prompt)
        if outcome == "invalid_evidence":
            return _invalid_evidence_response(prompt)
        raise AssertionError(f"未知 fake outcome：{outcome}")


class FakeLLM:
    """实现 invoke_structured_with_retry() 需要的最小接口。"""

    def __init__(self, runnable: FakeStructuredRunnable):
        self.runnable = runnable
        self.structured_calls: list[dict] = []

    def with_structured_output(self, schema, **kwargs):
        self.structured_calls.append(
            {
                "schema": schema,
                **kwargs,
            }
        )
        return self.runnable


@pytest.fixture(autouse=True)
def stable_extractor_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """关闭重试，使一次 chunk 只消费一个 fake response。"""

    monkeypatch.setattr(
        settings,
        "paper_section_chunk_chars",
        10_000,
    )
    monkeypatch.setattr(
        settings,
        "paper_max_section_llm_calls",
        10,
    )
    monkeypatch.setattr(
        settings,
        "structured_output_max_retries",
        0,
    )
    monkeypatch.setattr(
        settings,
        "provider_max_retries",
        0,
    )


def _block(
    block_id: str,
    *,
    page: int,
    text: str,
) -> PaperBlock:
    return PaperBlock(
        block_id=block_id,
        page=page,
        order=0,
        block_type="paragraph",
        text=text,
        text_hash=_sha256(text),
    )


def _section(
    section_id: str,
    *,
    title: str,
    kind: str,
    page: int,
    block: PaperBlock,
) -> PaperSection:
    return PaperSection(
        section_id=section_id,
        title=title,
        normalized_title=title.casefold(),
        level=1,
        kind=kind,
        page_start=page,
        page_end=page,
        block_ids=[block.block_id],
        content_hash=_sha256(block.text_hash),
    )


def _hierarchical_state(
    run_state: dict,
    tmp_path: Path,
) -> dict:
    """写入三个分散页面的真实 paper index Artifact。"""

    source_path = tmp_path / "hierarchical-paper.pdf"
    source_path.write_bytes(b"deterministic test source")

    abstract = _block(
        "block-abstract",
        page=1,
        text=(
            "We study action recognition in dynamic point cloud "
            "sequences."
        ),
    )
    experiments = _block(
        "block-experiments",
        page=6,
        text="We evaluate the model on a public benchmark.",
    )
    implementation = _block(
        "block-implementation",
        page=14,
        text="We train all networks for 35 epochs.",
    )
    blocks = [abstract, experiments, implementation]

    sections = [
        _section(
            "sec-abstract",
            title="Abstract",
            kind="abstract",
            page=1,
            block=abstract,
        ),
        _section(
            "sec-experiments",
            title="Experiments",
            kind="experiments",
            page=6,
            block=experiments,
        ),
        _section(
            "sec-implementation",
            title="Implementation Details",
            kind="implementation",
            page=14,
            block=implementation,
        ),
    ]
    report = PaperParseReport(
        status="succeeded",
        page_count=14,
        indexed_pages=[1, 6, 14],
        block_count=len(blocks),
        section_count=len(sections),
    )

    blocks_path, blocks_record = write_json_artifact(
        state=run_state,
        relative_path="analysis/paper_blocks.json",
        payload=[item.model_dump(mode="json") for item in blocks],
        producer_node="test_fixture",
    )
    sections_path, sections_record = write_json_artifact(
        state=run_state,
        relative_path="analysis/paper_sections.json",
        payload=[item.model_dump(mode="json") for item in sections],
        producer_node="test_fixture",
    )
    report_path, report_record = write_json_artifact(
        state=run_state,
        relative_path="analysis/paper_parse_report.json",
        payload=report.model_dump(mode="json"),
        producer_node="test_fixture",
    )

    document = PaperDocument(
        document_id="paper-hierarchical-test",
        source_path=str(source_path),
        source_sha256=_sha256(
            source_path.read_text(encoding="utf-8")
        ),
        parser_version="phase18-v1",
        page_count=14,
        indexed_page_count=3,
        block_count=len(blocks),
        section_count=len(sections),
        blocks_artifact="analysis/paper_blocks.json",
        sections_artifact="analysis/paper_sections.json",
        parse_report_artifact="analysis/paper_parse_report.json",
    )
    _, document_record = write_json_artifact(
        state=run_state,
        relative_path="analysis/paper_document.json",
        payload=document.model_dump(mode="json"),
        producer_node="test_fixture",
    )

    artifact_update = artifact_state_update(
        run_state,
        [
            document_record,
            blocks_record,
            sections_record,
            report_record,
        ],
    )
    return {
        **run_state,
        "paper_path": str(source_path),
        "paper_document": document.model_dump(mode="json"),
        "paper_blocks_path": str(blocks_path),
        "paper_sections_path": str(sections_path),
        "paper_parse_report_path": str(report_path),
        **artifact_update,
    }


def _run_extractor(
    state: dict,
    outcomes: list[str],
) -> tuple[dict, FakeStructuredRunnable, FakeLLM]:
    runnable = FakeStructuredRunnable(outcomes)
    llm = FakeLLM(runnable)

    def invoke(**kwargs):
        return invoke_structured_with_retry(
            llm=llm,
            schema=kwargs["schema"],
            prompt=kwargs["prompt"],
            method=settings.structured_output_method,
            strict=settings.structured_output_strict,
            max_retries=settings.structured_output_max_retries,
            raw_preview_chars=settings.structured_output_raw_preview_chars,
            provider_max_retries=settings.provider_max_retries,
            provider_retry_base_seconds=settings.provider_retry_base_seconds,
        )

    gateway = ScriptedModelGateway(invoke)

    with patch(
        "app.nodes.method_extractor_node.build_model_gateway",
        return_value=gateway,
    ):
        result = method_extractor_node(state)

    return result, runnable, llm


def _relative_paths(result: dict) -> set[str]:
    return {
        item["relative_path"]
        for item in result.get("artifact_records", [])
    }


def test_extractor_reads_late_implementation_section(
    run_state: dict,
    tmp_path: Path,
) -> None:
    state = _hierarchical_state(run_state, tmp_path)

    result, runnable, llm = _run_extractor(
        state,
        ["success", "success", "success"],
    )

    assert len(runnable.prompts) == 3
    assert "Implementation Details" in runnable.prompts[0]
    assert "page 14" in runnable.prompts[0]
    assert (
        "We train all networks for 35 epochs."
        in runnable.prompts[0]
    )

    settings_by_name = {
        item["name"]: item["value"]
        for item in result["paper_summary"]["experiment_settings"]
    }
    assert settings_by_name["training epochs"] == "35"
    assert any(
        target["category"] == "training_config"
        for target in result["mapping_targets"]
    )
    assert result["mapping_targets_path"].endswith(
        "analysis/mapping_targets.json"
    )

    assert len(llm.structured_calls) == 3
    assert all(
        call["schema"] is SectionExtractionDraft
        and call["include_raw"] is True
        for call in llm.structured_calls
    )

    paths = _relative_paths(result)
    assert {
        "analysis/paper_summary.json",
        "analysis/method_modules.json",
        "analysis/paper_fact_index.json",
        "analysis/paper_conflicts.json",
        "analysis/mapping_targets.json",
    } <= paths
    assert len(
        {
            item
            for item in paths
            if item.startswith(
                "analysis/paper_sections/extractions/"
            )
        }
    ) == 3
    assert len(
        {
            item
            for item in paths
            if item.startswith("traces/structured/")
        }
    ) == 3


def test_one_section_failure_is_nonterminal_and_visible(
    run_state: dict,
    tmp_path: Path,
) -> None:
    state = _hierarchical_state(run_state, tmp_path)

    result, runnable, _ = _run_extractor(
        state,
        ["failure", "success", "success"],
    )

    assert len(runnable.prompts) == 3
    section_errors = [
        item
        for item in result["stage_errors"]
        if item["code"]
        == "STRUCTURED_OUTPUT_VALIDATION_FAILED"
    ]
    assert len(section_errors) == 1
    assert section_errors[0]["terminal"] is False
    assert section_errors[0]["context"]["section_id"] == (
        "sec-implementation"
    )
    assert "final_status" not in result

    unresolved = result["paper_summary"]["unresolved_questions"]
    assert any(
        "章节抽取存在局部失败" in item
        for item in unresolved
    )
    assert result["paper_summary"]["research_problem"] != "unknown"
    assert result["paper_summary"]["experiment_settings"] == []


def test_blank_structured_result_is_retried_before_cache(
    run_state: dict,
    tmp_path: Path,
) -> None:
    state = _hierarchical_state(run_state, tmp_path)

    result, runnable, _ = _run_extractor(
        state,
        ["empty", "success", "success", "success"],
    )

    assert len(runnable.prompts) == 4
    assert "内容完全为空" in runnable.prompts[1]
    settings_by_name = {
        item["name"]: item["value"]
        for item in result["paper_summary"][
            "experiment_settings"
        ]
    }
    assert settings_by_name["training epochs"] == "35"
    assert not any(
        item["code"] == "PAPER_SECTION_EXTRACTION_EMPTY"
        for item in result.get("stage_errors", [])
    )


def test_all_sections_failed_returns_terminal_fallback(
    run_state: dict,
    tmp_path: Path,
) -> None:
    state = _hierarchical_state(run_state, tmp_path)

    result, runnable, _ = _run_extractor(
        state,
        ["failure", "failure", "failure"],
    )

    assert len(runnable.prompts) == 3
    assert result["paper_summary"]["research_problem"] == "unknown"
    assert result["paper_summary"]["core_idea"] == "unknown"
    assert result["paper_summary"]["method_modules"] == []
    assert result["mapping_targets"] == []
    assert result["final_status"] == "agent_failed"
    assert any(
        item["code"] == "ALL_PAPER_SECTIONS_FAILED"
        and item["terminal"] is True
        for item in result["stage_errors"]
    )


def test_invalid_evidence_is_not_cached(
    run_state: dict,
    tmp_path: Path,
) -> None:
    state = _hierarchical_state(run_state, tmp_path)

    result, _, _ = _run_extractor(
        state,
        ["invalid_evidence", "success", "success"],
    )

    error = next(
        item
        for item in result["stage_errors"]
        if item["code"] == "PAPER_SECTION_EVIDENCE_INVALID"
    )
    assert error["terminal"] is False
    invalid_chunk_id = error["context"]["chunk_id"]

    paths = _relative_paths(result)
    assert (
        "analysis/paper_sections/extractions/"
        f"{invalid_chunk_id}.json"
    ) not in paths
    assert (
        "traces/structured/"
        f"method_extractor_{invalid_chunk_id}"
        "_structured_attempts.json"
    ) in paths


def test_cache_hit_skips_llm_and_prompt_version_invalidates(
    run_state: dict,
    tmp_path: Path,
) -> None:
    state = _hierarchical_state(run_state, tmp_path)
    runnable = FakeStructuredRunnable(
        ["success", "success", "success"]
    )
    llm = FakeLLM(runnable)

    def invoke(**kwargs):
        return invoke_structured_with_retry(
            llm=llm,
            schema=kwargs["schema"],
            prompt=kwargs["prompt"],
            method=settings.structured_output_method,
            strict=settings.structured_output_strict,
            max_retries=settings.structured_output_max_retries,
            raw_preview_chars=settings.structured_output_raw_preview_chars,
            provider_max_retries=settings.provider_max_retries,
            provider_retry_base_seconds=settings.provider_retry_base_seconds,
        )

    gateway = ScriptedModelGateway(invoke)

    with patch(
        "app.nodes.method_extractor_node.build_model_gateway",
        return_value=gateway,
    ):
        first = method_extractor_node(state)
        assert len(runnable.prompts) == 3

        resumed_state = {**state, **first}
        second = method_extractor_node(resumed_state)

        assert len(runnable.prompts) == 3
        assert second["paper_summary"] == first["paper_summary"]

        runnable.outcomes.extend(
            ["success", "success", "success"]
        )
        with patch(
                "app.nodes.method_extractor_node."
                "PAPER_SECTION_EXTRACTION_PROMPT_VERSION",
                "phase18-v3",
        ):
            third = method_extractor_node(
                {**resumed_state, **second}
            )

    assert len(runnable.prompts) == 6
    assert third["paper_summary"] == first["paper_summary"]
