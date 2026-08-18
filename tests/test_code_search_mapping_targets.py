from __future__ import annotations

from pathlib import Path

from app.nodes.code_search_node import code_search_node
from app.schemas import CodeMappingTarget


def test_code_search_keys_evidence_by_mapping_target_id(
    run_state,
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "dataset.py").write_text(
        (
            "class MSRAction3DDataset:\n"
            "    def __getitem__(self, index):\n"
            "        return self.samples[index]\n"
        ),
        encoding="utf-8",
    )
    target = CodeMappingTarget(
        target_id="mapping_target_msr",
        category="data_pipeline",
        name="MSR-Action3D",
        description="Locate dataset loading and preprocessing.",
        possible_keywords=[
            "MSRAction3DDataset",
            "dataset",
        ],
    )

    result = code_search_node(
        {
            **run_state,
            "repo_path": str(repo),
            "mapping_targets": [
                target.model_dump(mode="json")
            ],
            "enable_dense_retrieval": False,
            "dense_retrieval_required": False,
        }
    )

    assert target.target_id in result[
        "code_evidence_packs"
    ]
    assert target.target_id in result[
        "code_evidence_pack_paths"
    ]
    assert target.target_id in result[
        "dense_retrieval_report_paths"
    ]
    assert target.name in result[
        "code_search_results"
    ]
    assert any(
        item["file_path"] == "dataset.py"
        for item in result[
            "code_evidence_packs"
        ][target.target_id]["items"]
    )
