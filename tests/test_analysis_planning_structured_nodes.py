from __future__ import annotations

from pathlib import Path

import app.nodes.experiment_plan_node as experiment_plan_module
import app.nodes.mapping_node as mapping_module
import app.nodes.method_extractor_node as method_extractor_module
from app.nodes.paper_reader_node import paper_reader_node
from app.schemas import CodeMappingTarget, ModuleMapping
from app.tools.structured_output_tools import StructuredInvocationResult
from tests.helpers.model_routing import ScriptedModelGateway


def _failed_invocation() -> StructuredInvocationResult:
    return StructuredInvocationResult(
        value=None,
        attempts=[],
        method="json_schema",
        strict=True,
        max_retries=2,
    )


def _empty_code_evidence_pack(query: str) -> dict:
    """构造符合 Phase 20 mapping 输入契约的最小 Evidence Pack。"""

    return {
        "query": query,
        "keywords": [],
        "repo_fingerprint": "test-repo-fingerprint",
        "items": [],
    }


def test_method_extractor_falls_back_without_inventing_modules(
    monkeypatch,
    run_state,
    tmp_path: Path,
):
    gateway = ScriptedModelGateway([_failed_invocation()])
    monkeypatch.setattr(
        method_extractor_module,
        "build_model_gateway",
        lambda: gateway,
    )

    paper_path = tmp_path / "paper.md"
    paper_path.write_text(
        "# Method\nPaper content.\n",
        encoding="utf-8",
    )
    paper_index = paper_reader_node(
        {
            **run_state,
            "paper_path": str(paper_path),
        }
    )

    result = method_extractor_module.method_extractor_node(
        {**run_state, **paper_index}
    )

    assert result["method_modules"] == []
    assert result["paper_summary"]["research_problem"] == "unknown"
    trace_paths = [
        Path(path)
        for path in result["output_files"]
        if Path(path).name.startswith("method_extractor_")
        and path.endswith("_structured_attempts.json")
    ]
    assert len(trace_paths) == 1
    trace_path = trace_paths[0]
    assert trace_path.exists()
    assert str(trace_path) in result["output_files"]
    relative_trace_path = trace_path.relative_to(
        Path(run_state["run_dir"])
    ).as_posix()
    assert any(
        record["relative_path"]
        == relative_trace_path
        and record["run_id"] == run_state["run_id"]
        for record in result["artifact_records"]
    )


def test_mapping_keeps_successful_modules_and_uses_unique_traces(
    monkeypatch,
    run_state,
):
    success_mapping = ModuleMapping(
        module_name="P4D convolution",
        candidates=[],
        unresolved_questions=[],
    )
    invocations = iter(
        [
            StructuredInvocationResult(
                value=success_mapping,
                attempts=[],
                method="json_schema",
                strict=True,
                max_retries=2,
            ),
            _failed_invocation(),
        ]
    )

    gateway = ScriptedModelGateway(list(invocations))
    monkeypatch.setattr(
        mapping_module,
        "build_model_gateway",
        lambda: gateway,
    )

    result = mapping_module.mapping_node(
        {
            **run_state,
            "method_modules": [
                {"name": "P4D convolution"},
                {"name": "Transformer encoder"},
            ],
            "repo_path": "/repo",
            "code_evidence_packs": {
                "P4D convolution": _empty_code_evidence_pack(
                    "P4D convolution"
                ),
                "Transformer encoder": _empty_code_evidence_pack(
                    "Transformer encoder"
                ),
            },
        }
    )

    assert len(result["paper_code_mapping"]) == 2
    assert result["paper_code_mapping"][0]["module_name"] == "P4D convolution"
    assert result["paper_code_mapping"][1]["candidates"] == []

    traces = [
        path
        for path in result["output_files"]
        if path.endswith("_structured_attempts.json")
    ]
    assert len(traces) == 2
    assert len(set(traces)) == 2
    trace_dir = (
        Path(run_state["run_dir"]) / "traces" / "structured"
    )
    assert all(Path(path).parent == trace_dir for path in traces)


def test_mapping_preserves_categorized_target_identity(
    monkeypatch,
    run_state,
):
    target = CodeMappingTarget(
        target_id="mapping_target_dataset",
        category="data_pipeline",
        name="MSR-Action3D",
        description="Locate dataset loading and preprocessing.",
        possible_keywords=["dataset", "dataloader"],
    )
    invocation = StructuredInvocationResult(
        value=ModuleMapping(
            module_name="incorrect model name",
            candidates=[],
            unresolved_questions=[],
        ),
        attempts=[],
        method="json_schema",
        strict=True,
        max_retries=2,
    )

    gateway = ScriptedModelGateway([invocation])
    monkeypatch.setattr(
        mapping_module,
        "build_model_gateway",
        lambda: gateway,
    )

    result = mapping_module.mapping_node(
        {
            **run_state,
            "repo_path": str(
                Path(run_state["run_dir"])
            ),
            "mapping_targets": [
                target.model_dump(mode="json")
            ],
            "code_evidence_packs": {
                target.target_id: (
                    _empty_code_evidence_pack(
                        target.name
                    )
                )
            },
        }
    )

    mapping = result["paper_code_mapping"][0]
    assert mapping["module_name"] == target.name
    assert mapping["target_id"] == target.target_id
    assert mapping["target_category"] == "data_pipeline"
    assert any(
        "module_name 与输入不一致"
        in question
        for question in mapping[
            "unresolved_questions"
        ]
    )


def test_experiment_plan_failure_returns_no_commands(
    monkeypatch,
    run_state,
):
    gateway = ScriptedModelGateway([_failed_invocation()])
    monkeypatch.setattr(
        experiment_plan_module,
        "build_model_gateway",
        lambda: gateway,
    )

    result = experiment_plan_module.experiment_plan_node(
        {
            **run_state,
            "paper_summary": {"title": "demo"},
            "repo_map": {"repo_path": "/repo"},
            "paper_code_mapping": [
                {"module_name": "encoder", "candidates": []}
            ],
            "experiment_goal": "复现 main result",
        }
    )

    assert result["run_commands"] == []
    assert result["experiment_plan"]["goal"] == "复现 main result"
    trace_path = (
        Path(run_state["run_dir"])
        / "traces"
        / "structured"
        / "experiment_plan_structured_attempts.json"
    )
    assert trace_path.exists()
    assert str(trace_path) in result["output_files"]
