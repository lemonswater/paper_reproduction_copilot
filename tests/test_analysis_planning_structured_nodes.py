from __future__ import annotations

import json
from pathlib import Path

import app.nodes.experiment_plan_node as experiment_plan_module
import app.nodes.mapping_node as mapping_module
import app.nodes.mapping_alias_resolver_node as alias_resolver_module
import app.nodes.method_extractor_node as method_extractor_module
from app.model_routing.errors import ModelRouteUnavailable
from app.nodes.paper_reader_node import paper_reader_node
from app.paper.schemas import SectionChunk
from app.retrieval.indexer import build_repository_index
from app.schemas import (
    CodeMappingTarget,
    ExperimentPlan,
    ModuleMapping,
    MappingAliasBatchDecision,
    RunCommand,
)
from app.tools.structured_output_tools import StructuredInvocationResult
from tests.helpers.model_routing import ScriptedModelGateway
from app.tools.mapping_alias_tools import build_alias_candidate_groups
from app.tools.mapping_target_tools import prepare_mapping_method_modules


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


def test_mapping_alias_resolver_merges_high_confidence_group(
    monkeypatch,
    run_state,
):
    paper_summary = {
        "title": "Example paper",
        "research_problem": "Example",
        "core_idea": "Point sequence processing.",
        "method_modules": [],
        "datasets": [],
        "metrics": [],
        "experiment_settings": [],
        "reproduction_risks": [],
        "unresolved_questions": [],
    }
    method_modules = [
        {
            "name": "P4Conv",
            "description": "Paper abbreviation.",
            "possible_keywords": ["P4Conv"],
            "evidence": [],
            "missing_info": [],
        },
        {
            "name": "Point 4D Convolution",
            "description": "Full operator name.",
            "possible_keywords": [
                "P4DConv",
                "point_4d_convolution",
            ],
            "evidence": [],
            "missing_info": [],
        },
    ]
    candidates = build_alias_candidate_groups(
        prepare_mapping_method_modules(
            paper_summary=paper_summary,
            method_modules=method_modules,
        )
    )
    group = candidates.groups[0]
    invocation = StructuredInvocationResult(
        value=MappingAliasBatchDecision.model_validate(
            {
                "decisions": [
                    {
                        "group_id": group["group_id"],
                        "should_merge": True,
                        "confidence": "high",
                        "member_ids": [
                            module["module_id"]
                            for module in group["modules"]
                        ],
                        "canonical_member_id": next(
                            module["module_id"]
                            for module in group["modules"]
                            if module["name"]
                            == "Point 4D Convolution"
                        ),
                        "reason": "Same implementation entity.",
                    }
                ]
            }
        ),
        attempts=[],
        method="json_schema",
        strict=True,
        max_retries=1,
    )
    gateway = ScriptedModelGateway([invocation])
    monkeypatch.setattr(
        alias_resolver_module,
        "build_model_gateway",
        lambda: gateway,
    )
    monkeypatch.setattr(
        alias_resolver_module.settings,
        "mapping_aliases_path",
        None,
    )

    result = alias_resolver_module.mapping_alias_resolver_node(
        {
            **run_state,
            "paper_summary": paper_summary,
            "method_modules": method_modules,
        }
    )

    assert gateway.calls[0]["task_kind"] == (
        "mapping_alias_resolution"
    )
    assert gateway.calls[0]["requested_max_output_tokens"] == 4096
    assert result["mapping_alias_resolution_status"] == "resolved"
    assert result["mapping_alias_decisions"][0]["accepted"] is True
    assert len(result["mapping_targets"]) == 1
    assert result["mapping_targets"][0]["name"] == (
        "Point 4D Convolution"
    )
    paths = {
        record["relative_path"]
        for record in result["artifact_records"]
    }
    assert {
        "analysis/mapping_alias_candidates.json",
        "analysis/mapping_alias_decisions.json",
        "analysis/mapping_targets.json",
        (
            "traces/structured/"
            "mapping_alias_resolver_structured_attempts.json"
        ),
    } <= paths


def test_mapping_alias_resolver_route_failure_is_nonterminal_fallback(
    monkeypatch,
    run_state,
):
    paper_summary = {
        "title": "Example paper",
        "research_problem": "Example",
        "core_idea": "Point sequence processing.",
        "method_modules": [],
        "datasets": [],
        "metrics": [],
        "experiment_settings": [],
        "reproduction_risks": [],
        "unresolved_questions": [],
    }
    method_modules = [
        {
            "name": "P4Conv",
            "description": "Paper abbreviation.",
            "possible_keywords": ["P4Conv"],
            "evidence": [],
            "missing_info": [],
        },
        {
            "name": "Point 4D Convolution",
            "description": "Full operator name.",
            "possible_keywords": ["P4DConv"],
            "evidence": [],
            "missing_info": [],
        },
    ]

    def unavailable(**_kwargs):
        raise ModelRouteUnavailable(
            "MODEL_ROUTE_INPUT_LIMIT_EXCEEDED"
        )

    gateway = ScriptedModelGateway(unavailable)
    monkeypatch.setattr(
        alias_resolver_module,
        "build_model_gateway",
        lambda: gateway,
    )
    monkeypatch.setattr(
        alias_resolver_module.settings,
        "mapping_aliases_path",
        None,
    )

    result = alias_resolver_module.mapping_alias_resolver_node(
        {
            **run_state,
            "paper_summary": paper_summary,
            "method_modules": method_modules,
        }
    )

    assert result["mapping_alias_resolution_status"] == "fallback"
    assert len(result["mapping_targets"]) == 2
    error = result["stage_errors"][-1]
    assert error["code"] == "MAPPING_ALIAS_MODEL_ROUTE_UNAVAILABLE"
    assert error["terminal"] is False


def test_mapping_alias_resolver_provider_failure_is_nonterminal_fallback(
    monkeypatch,
    run_state,
):
    method_modules = [
        {
            "name": "P4Conv",
            "description": "Paper abbreviation.",
            "possible_keywords": ["P4Conv"],
            "evidence": [],
            "missing_info": [],
        },
        {
            "name": "Point 4D Convolution",
            "description": "Full operator name.",
            "possible_keywords": ["P4DConv"],
            "evidence": [],
            "missing_info": [],
        },
    ]

    def provider_failure(**_kwargs):
        raise RuntimeError("provider unavailable")

    gateway = ScriptedModelGateway(provider_failure)
    monkeypatch.setattr(
        alias_resolver_module,
        "build_model_gateway",
        lambda: gateway,
    )
    monkeypatch.setattr(
        alias_resolver_module.settings,
        "mapping_aliases_path",
        None,
    )

    result = alias_resolver_module.mapping_alias_resolver_node(
        {
            **run_state,
            "paper_summary": {
                "title": "Example paper",
                "core_idea": "Point sequence processing.",
            },
            "method_modules": method_modules,
        }
    )

    assert result["mapping_alias_resolution_status"] == "fallback"
    assert len(result["mapping_targets"]) == 2
    error = result["stage_errors"][-1]
    assert error["code"] == "MAPPING_ALIAS_MODEL_INVOCATION_FAILED"
    assert error["terminal"] is False


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


def test_document_root_title_does_not_require_method_module_retry():
    # PDF 首页可以在论文标题前包含出版信息 block（例如 p001-b0000）。
    # 根标题应由文档首个 section 识别，不能依赖全局首个 block。
    root_chunk = SectionChunk(
        chunk_id="sec-title-c000",
        section_id="sec-title",
        section_title="PSTNet: Point Spatio-Temporal Convolution",
        section_kind="method",
        page_start=1,
        page_end=1,
        block_ids=["p001-b0001", "p001-b0002"],
        text="paper title and abstract",
        content_hash="root-title-hash",
    )
    method_chunk = root_chunk.model_copy(
        update={
            "chunk_id": "sec-method-c000",
            "section_id": "sec-method",
            "section_title": "Proposed method",
            "page_start": 3,
            "page_end": 3,
            "block_ids": ["p003-b0001"],
            "content_hash": "method-hash",
        }
    )

    assert not method_extractor_module._requires_method_module_retry(
        root_chunk,
        document_root_section_id="sec-title",
    )
    assert method_extractor_module._requires_method_module_retry(
        method_chunk,
        document_root_section_id="sec-title",
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


def test_mapping_prompt_omits_binding_only_evidence_metadata():
    target = CodeMappingTarget(
        target_id="mapping_target_compact",
        category="core_method",
        name="Compact operator",
        description="Locate the operator implementation.",
        evidence=[
            {
                "source_type": "paper",
                "source_path": "paper.pdf",
                "quote_or_summary": (
                    "REMOVE_FULL_PAPER_EVIDENCE"
                ),
                "block_ids": [
                    "REMOVE_BLOCK_IDS"
                ],
            }
        ],
    )
    prompt = mapping_module._build_mapping_prompt(
        target=target,
        pack_payload={
            "query": target.name,
            "keywords": ["operator"],
            "repo_fingerprint": (
                "REMOVE_REPO_FINGERPRINT"
            ),
            "items": [
                {
                    "evidence_id": "code-0123456789abcdef0123",
                    "file_path": "models/operator.py",
                    "symbol": "CompactOperator",
                    "start_line": 10,
                    "end_line": 20,
                    "retrieval_channels": [
                        "lexical",
                        "symbol",
                    ],
                    "fused_score": 0.9,
                    "text": "class CompactOperator: pass",
                    "content_hash": "REMOVE_CONTENT_HASH",
                    "file_sha256": "REMOVE_FILE_HASH",
                    "retrieval_signals": {
                        "marker": "REMOVE_RETRIEVAL_SIGNALS"
                    },
                }
            ],
        },
    )

    assert "class CompactOperator: pass" in prompt
    assert "REMOVE_FULL_PAPER_EVIDENCE" not in prompt
    assert "REMOVE_BLOCK_IDS" not in prompt
    assert "REMOVE_REPO_FINGERPRINT" not in prompt
    assert "REMOVE_CONTENT_HASH" not in prompt
    assert "REMOVE_FILE_HASH" not in prompt
    assert "REMOVE_RETRIEVAL_SIGNALS" not in prompt


def test_mapping_route_failure_is_isolated_to_one_target(
    monkeypatch,
    run_state,
):
    first_target = CodeMappingTarget(
        target_id="mapping_target_first",
        category="core_method",
        name="First operator",
        description="First operator implementation.",
    )
    second_target = CodeMappingTarget(
        target_id="mapping_target_second",
        category="training_config",
        name="Training configuration",
        description="Training arguments.",
    )
    responses = iter(
        [
            StructuredInvocationResult(
                value=ModuleMapping(
                    module_name=first_target.name,
                    candidates=[],
                    unresolved_questions=[],
                ),
                attempts=[],
                method="json_schema",
                strict=True,
                max_retries=2,
            ),
            ModelRouteUnavailable(
                "MODEL_ROUTE_INPUT_LIMIT_EXCEEDED"
            ),
        ]
    )

    def scripted_invocation(**_kwargs):
        response = next(responses)
        if isinstance(response, BaseException):
            raise response
        return response

    gateway = ScriptedModelGateway(scripted_invocation)
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
                first_target.model_dump(mode="json"),
                second_target.model_dump(mode="json"),
            ],
            "code_evidence_packs": {
                first_target.target_id: (
                    _empty_code_evidence_pack(
                        first_target.name
                    )
                ),
                second_target.target_id: (
                    _empty_code_evidence_pack(
                        second_target.name
                    )
                ),
            },
        }
    )

    mappings = result["paper_code_mapping"]
    assert len(mappings) == 2
    assert mappings[0]["module_name"] == first_target.name
    assert mappings[1]["module_name"] == second_target.name
    assert mappings[1]["candidates"] == []
    route_errors = [
        error
        for error in result["stage_errors"]
        if error["code"]
        == "MAPPING_MODEL_ROUTE_UNAVAILABLE"
    ]
    assert len(route_errors) == 1
    assert route_errors[0]["terminal"] is False
    assert route_errors[0]["context"]["target_id"] == (
        second_target.target_id
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
            "paper_summary": {
                "title": "demo",
                "experiment_settings": [
                    {
                        "name": "epochs",
                        "value": "35",
                        "evidence": [
                            {
                                "quote_or_summary": "REMOVE_SETTING_EVIDENCE",
                            }
                        ],
                    }
                ],
                "method_modules": [
                    {
                        "name": "encoder",
                        "description": "encode features",
                        "evidence": [
                            {
                                "quote_or_summary": "REMOVE_FROM_PLAN_PROMPT",
                                "content_hash": "secret-sized-provenance",
                            }
                        ],
                    }
                ],
            },
            "repo_map": {"repo_path": "/repo"},
            "paper_code_mapping": [
                {
                    "module_name": "encoder",
                    "candidates": [
                        {
                            "file_path": "models/encoder.py",
                            "symbols": ["Encoder"],
                            "reason": "implementation",
                            "confidence": "high",
                            "evidence": [
                                {
                                    "text": "REMOVE_MAPPING_SOURCE",
                                }
                            ],
                        }
                    ],
                }
            ],
            "experiment_goal": "复现 main result",
        }
    )

    assert result["run_commands"] == []
    assert result["experiment_plan"]["goal"] == "复现 main result"
    call = gateway.calls[0]
    assert call["requested_max_output_tokens"] == 8192
    assert "models/encoder.py" in call["prompt"]
    assert "REMOVE_FROM_PLAN_PROMPT" not in call["prompt"]
    assert "REMOVE_SETTING_EVIDENCE" not in call["prompt"]
    assert "REMOVE_MAPPING_SOURCE" not in call["prompt"]
    trace_path = (
        Path(run_state["run_dir"])
        / "traces"
        / "structured"
        / "experiment_plan_structured_attempts.json"
    )
    assert trace_path.exists()
    assert str(trace_path) in result["output_files"]


def test_experiment_plan_applies_repository_cli_contract(
    monkeypatch,
    run_state,
):
    repo_path = (
        Path(run_state["run_dir"])
        / "fixture-repo"
    )
    repo_path.mkdir()
    (repo_path / "train.py").write_text(
        "\n".join(
            [
                "import argparse",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--data-path', default='data/demo')",
                "parser.add_argument('--batch-size', type=int, default=16)",
                "parser.add_argument('--epochs', type=int, default=35)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    index = build_repository_index(
        repo_path,
        index_version="test-cli-v1",
    )
    index_path = (
        Path(run_state["run_dir"])
        / "analysis"
        / "retrieval"
        / "repo_index.json"
    )
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        json.dumps(
            index.model_dump(mode="json"),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    plan = ExperimentPlan(
        goal="复现 main result",
        run_commands=[
            RunCommand(
                command=(
                    "python train.py --batch_size 16 "
                    "--temporal_kernel_size 3 --epochs 35"
                ),
                cwd=str(repo_path.parent / "wrong-repo"),
                source="inferred",
                risk_level="high",
                reason="Train the model.",
            )
        ],
    )
    invocation = StructuredInvocationResult(
        value=plan,
        attempts=[],
        method="json_schema",
        strict=True,
        max_retries=2,
    )
    gateway = ScriptedModelGateway([invocation])
    monkeypatch.setattr(
        experiment_plan_module,
        "build_model_gateway",
        lambda: gateway,
    )

    result = experiment_plan_module.experiment_plan_node(
        {
            **run_state,
            "repo_path": str(repo_path),
            "repo_index_path": str(index_path),
            "paper_summary": {"title": "demo"},
            "repo_map": {
                "repo_path": str(repo_path),
                "train_entries": ["train.py"],
                "eval_entries": [],
            },
            "paper_code_mapping": [
                {
                    "module_name": "demo",
                    "candidates": [],
                }
            ],
            "experiment_goal": "复现 main result",
        }
    )

    command = result["run_commands"][0]
    assert command["command"] == (
        "python train.py --batch-size 16 --epochs 35 "
        "--data-path data/demo"
    )
    assert command["source"] == "need_confirm"
    assert command["cwd"] == str(repo_path.resolve())
    assert "argparse 契约校正" in command["reason"]
    assert "工作目录" in command["reason"]
    assert any(
        "不支持参数 --temporal_kernel_size"
        in question
        for question in result["experiment_plan"][
            "unresolved_questions"
        ]
    )
    prompt = gateway.calls[0]["prompt"]
    assert '"--data-path"' in prompt
    assert '"--batch-size"' in prompt


def test_cli_contract_prioritizes_paper_method_entry(
    run_state,
):
    repo_path = Path(run_state["run_dir"]) / "maple-repo"
    (repo_path / "z_mask").mkdir(parents=True)
    (repo_path / "pseudo_labels").mkdir()

    for relative in (
        "train-msr.py",
        "pseudo_labels/train-msr-twotrans.py",
        "z_mask/train-msr-twotrans.py",
    ):
        path = repo_path / relative
        path.write_text(
            "\n".join(
                [
                    "import argparse",
                    "parser = argparse.ArgumentParser()",
                    "parser.add_argument('--data-path', default='data/msr')",
                    "parser.add_argument('--data-meta-unlabel', default='meta/u.list')",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    (repo_path / "README.md").write_text(
        "Train MAPLE with z_mask/train_mse_msr_gpu0.sh.\n",
        encoding="utf-8",
    )

    index = build_repository_index(
        repo_path,
        index_version="test-cli-priority-v1",
    )
    index_path = (
        Path(run_state["run_dir"])
        / "analysis"
        / "retrieval"
        / "priority_repo_index.json"
    )
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(index.model_dump(mode="json")),
        encoding="utf-8",
    )
    repo_map = {
        "repo_path": str(repo_path),
        "readme_files": ["README.md"],
        "train_entries": [
            "pseudo_labels/train-msr-twotrans.py",
            "train-msr.py",
            "z_mask/train-msr-twotrans.py",
        ],
        "eval_entries": [],
    }
    state = {
        **run_state,
        "repo_index_path": str(index_path),
        "paper_summary": {
            "title": "MAPLE: Masked Pseudo-Labeling autoEncoder",
            "datasets": ["MSR-Action3D"],
        },
        "experiment_goal": (
            "复现 MAPLE 在 MSR-Action3D 上的半监督 main result"
        ),
    }

    contracts = experiment_plan_module._load_cli_contract(
        state=state,
        repo_map=repo_map,
    )

    assert contracts[0]["entry"] == (
        "z_mask/train-msr-twotrans.py"
    )
    assert {
        option["flags"][0]
        for option in contracts[0]["options"]
    } >= {"--data-path", "--data-meta-unlabel"}
