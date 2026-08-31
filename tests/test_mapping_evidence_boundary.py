from __future__ import annotations

from app.nodes.mapping_node import (
    _recover_empty_mapping_from_strong_evidence,
    bind_mapping_to_evidence_pack,
)
from app.retrieval.service import (
    build_evidence_pack,
)
from app.schemas import (
    CodeCandidate,
    CodeMappingTarget,
    ModuleMapping,
)


def _build_pack(tmp_path):
    (tmp_path / "operator.py").write_text(
        "\n".join(
            [
                "class PSTConv:",
                "    def forward(self, points):",
                "        return points",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _, pack = build_evidence_pack(
        repo_path=tmp_path,
        query="PSTConv",
        keywords=["PSTConv"],
        top_k=3,
    )
    return pack


def test_mapping_drops_candidate_outside_pack(
    tmp_path,
):
    pack = _build_pack(tmp_path)
    mapping = ModuleMapping(
        module_name="PST convolution",
        candidates=[
            CodeCandidate(
                file_path="invented.py",
                symbols=["InventedLayer"],
                reason="model guessed it",
                evidence_ids=["fake-id"],
                confidence="high",
            )
        ],
    )

    bound = bind_mapping_to_evidence_pack(
        mapping=mapping,
        pack_payload=pack.model_dump(
            mode="json"
        ),
        repo_path=str(tmp_path),
    )

    assert bound.candidates == []
    assert any(
        "已丢弃无依据候选" in value
        for value in bound.unresolved_questions
    )


def test_mapping_rebuilds_evidence_from_valid_id(
    tmp_path,
):
    pack = _build_pack(tmp_path)
    item = next(
        value
        for value in pack.items
        if value.file_path == "operator.py"
    )
    mapping = ModuleMapping(
        module_name="PST convolution",
        candidates=[
            CodeCandidate(
                file_path="operator.py",
                symbols=[
                    "PSTConv",
                    "InventedSymbol",
                ],
                reason="exact class match",
                evidence_ids=[
                    item.evidence_id,
                    "fake-id",
                ],
                confidence="high",
            )
        ],
    )

    bound = bind_mapping_to_evidence_pack(
        mapping=mapping,
        pack_payload=pack.model_dump(
            mode="json"
        ),
        repo_path=str(tmp_path),
    )

    candidate = bound.candidates[0]
    assert candidate.file_path == "operator.py"
    assert candidate.symbols == ["PSTConv"]
    assert candidate.evidence_ids == [
        item.evidence_id
    ]
    assert len(candidate.evidence) == 1
    assert (
        candidate.evidence[0].file_sha256
        == item.file_sha256
    )
    assert candidate.evidence[0].start_line
    assert candidate.evidence[0].end_line


def test_mapping_drops_stale_pack_item(
    tmp_path,
):
    pack = _build_pack(tmp_path)
    item = pack.items[0]
    mapping = ModuleMapping(
        module_name="PST convolution",
        candidates=[
            CodeCandidate(
                file_path=item.file_path,
                symbols=[item.symbol]
                if item.symbol
                else [],
                reason="previous evidence",
                evidence_ids=[item.evidence_id],
                confidence="high",
            )
        ],
    )
    (tmp_path / item.file_path).write_text(
        "# source changed after retrieval\n",
        encoding="utf-8",
    )

    bound = bind_mapping_to_evidence_pack(
        mapping=mapping,
        pack_payload=pack.model_dump(
            mode="json"
        ),
        repo_path=str(tmp_path),
    )

    assert bound.candidates == []
    assert any(
        "失效" in value
        for value in bound.unresolved_questions
    )


def test_empty_core_mapping_recovers_only_strong_valid_evidence(
    tmp_path,
):
    pack = _build_pack(tmp_path)
    target = CodeMappingTarget(
        target_id="mapping_target_pstconv",
        category="core_method",
        name="PST convolution",
        description="Named spatio-temporal operator.",
        aliases=["PSTConv"],
        possible_keywords=["PSTConv"],
    )

    recovered = _recover_empty_mapping_from_strong_evidence(
        target=target,
        mapping=ModuleMapping(
            module_name=target.name,
            target_id=target.target_id,
            target_category=target.category,
            candidates=[],
            unresolved_questions=[],
        ),
        pack_payload=pack.model_dump(mode="json"),
        repo_path=str(tmp_path),
    )

    assert len(recovered.candidates) == 1
    candidate = recovered.candidates[0]
    assert candidate.file_path == "operator.py"
    assert candidate.symbols == ["PSTConv"]
    assert candidate.confidence == "medium"
    assert candidate.evidence_ids
    assert candidate.evidence
    assert any(
        "受约束的强 Evidence 兜底" in question
        for question in recovered.unresolved_questions
    )


def test_empty_non_core_mapping_does_not_use_evidence_recovery(
    tmp_path,
):
    pack = _build_pack(tmp_path)
    target = CodeMappingTarget(
        target_id="mapping_target_metric",
        category="evaluation_metric",
        name="PSTConv",
        description="Synthetic non-core target.",
    )

    recovered = _recover_empty_mapping_from_strong_evidence(
        target=target,
        mapping=ModuleMapping(
            module_name=target.name,
            target_id=target.target_id,
            target_category=target.category,
        ),
        pack_payload=pack.model_dump(mode="json"),
        repo_path=str(tmp_path),
    )

    assert recovered.candidates == []


def test_empty_core_mapping_does_not_recover_weak_evidence(
    tmp_path,
):
    pack = _build_pack(tmp_path).model_dump(mode="json")
    pack["items"][0]["retrieval_channels"] = [
        "symbol",
        "keyword",
    ]
    target = CodeMappingTarget(
        target_id="mapping_target_pstconv",
        category="core_method",
        name="PST convolution",
        description="Named spatio-temporal operator.",
        aliases=["PSTConv"],
    )

    recovered = _recover_empty_mapping_from_strong_evidence(
        target=target,
        mapping=ModuleMapping(
            module_name=target.name,
            target_id=target.target_id,
            target_category=target.category,
        ),
        pack_payload=pack,
        repo_path=str(tmp_path),
    )

    assert recovered.candidates == []


def test_empty_core_mapping_respects_transpose_conflict(
    tmp_path,
):
    pack = _build_pack(tmp_path)
    target = CodeMappingTarget(
        target_id="mapping_target_transposed",
        category="core_method",
        name="PST transposed convolution",
        description="Transposed operator.",
        aliases=["PSTConv"],
    )

    recovered = _recover_empty_mapping_from_strong_evidence(
        target=target,
        mapping=ModuleMapping(
            module_name=target.name,
            target_id=target.target_id,
            target_category=target.category,
        ),
        pack_payload=pack.model_dump(mode="json"),
        repo_path=str(tmp_path),
    )

    assert recovered.candidates == []
