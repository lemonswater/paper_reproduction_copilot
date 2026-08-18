from __future__ import annotations

from app.retrieval.indexer import (
    build_repository_index,
)
from app.retrieval.service import (
    build_evidence_pack,
    validate_code_evidence,
)


def _write_fixture_repo(root) -> None:
    (root / "modules").mkdir()
    (root / "models").mkdir()
    (root / "notes").mkdir()

    (root / "modules" / "pst.py").write_text(
        "\n".join(
            [
                "class PSTConv:",
                "    def forward(self, points):",
                "        # spatio temporal point tube",
                "        return points",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (
        root
        / "models"
        / "classification.py"
    ).write_text(
        "\n".join(
            [
                "from modules.pst import PSTConv",
                "",
                "class Network:",
                "    def __init__(self):",
                "        self.layer = PSTConv()",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (
        root
        / "notes"
        / "pstconv.md"
    ).write_text(
        "# PSTConv\nspatio temporal point tube\n",
        encoding="utf-8",
    )


def test_exact_symbol_and_import_graph_rank_high(
    tmp_path,
):
    _write_fixture_repo(tmp_path)
    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )

    _, pack = build_evidence_pack(
        repo_path=tmp_path,
        query="PST convolution spatio temporal",
        keywords=["PSTConv"],
        index=index,
        top_k=5,
    )

    paths = [
        item.file_path
        for item in pack.items
    ]
    assert paths[0] == "modules/pst.py"
    assert "models/classification.py" in paths

    operator = pack.items[0]
    assert "symbol" in operator.retrieval_channels
    assert operator.symbol == "PSTConv"
    assert validate_code_evidence(
        repo_path=tmp_path,
        evidence=operator,
    )


def test_evidence_becomes_stale_after_source_change(
    tmp_path,
):
    _write_fixture_repo(tmp_path)
    _, pack = build_evidence_pack(
        repo_path=tmp_path,
        query="PSTConv",
        keywords=["PSTConv"],
        top_k=3,
    )
    evidence = next(
        item
        for item in pack.items
        if item.file_path == "modules/pst.py"
    )

    (tmp_path / "modules" / "pst.py").write_text(
        "class PSTConvV2:\n    pass\n",
        encoding="utf-8",
    )

    assert not validate_code_evidence(
        repo_path=tmp_path,
        evidence=evidence,
    )


def test_traceback_path_receives_strong_channel(
    tmp_path,
):
    _write_fixture_repo(tmp_path)

    _, pack = build_evidence_pack(
        repo_path=tmp_path,
        query="RuntimeError unexpected tensor shape",
        keywords=["RuntimeError"],
        preferred_paths=[
            "models/classification.py"
        ],
        top_k=3,
    )

    assert pack.items[0].file_path == (
        "models/classification.py"
    )
    assert "traceback" in (
        pack.items[0].retrieval_channels
    )