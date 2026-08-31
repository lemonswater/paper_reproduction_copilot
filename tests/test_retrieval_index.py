from __future__ import annotations

from app.retrieval.indexer import (
    build_repository_index,
)


def test_repository_index_collects_code_metadata(
    tmp_path,
):
    module_dir = tmp_path / "modules"
    model_dir = tmp_path / "models"
    module_dir.mkdir()
    model_dir.mkdir()

    (module_dir / "pst.py").write_text(
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
    (model_dir / "network.py").write_text(
        "\n".join(
            [
                "from modules.pst import PSTConv",
                "",
                "def build_model():",
                "    return PSTConv()",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "train.py").write_text(
        "\n".join(
            [
                "import argparse",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument(",
                "    '--epochs',",
                "    type=int,",
                "    default=35,",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )

    assert {
        item.file_path
        for item in index.documents
    } == {
        "models/network.py",
        "modules/pst.py",
        "train.py",
    }
    assert any(
        item.qualified_name == "PSTConv.forward"
        for item in index.symbols
    )
    assert any(
        item.imported_module == "modules.pst"
        and item.imported_names == ["PSTConv"]
        for item in index.imports
    )
    assert any(
        "--epochs" in item.flags
        and item.default_repr == "35"
        for item in index.cli_options
    )
    assert index.repo_fingerprint
    assert all(
        item.file_sha256
        for item in index.documents
    )


def test_repository_index_skips_large_file(
    tmp_path,
):
    (tmp_path / "small.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "large.py").write_text(
        "x" * 200,
        encoding="utf-8",
    )

    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
        max_file_bytes=100,
    )

    assert [
        item.file_path
        for item in index.documents
    ] == ["small.py"]
    assert any(
        warning.startswith(
            "SKIPPED_LARGE_FILE:large.py:"
        )
        for warning in index.warnings
    )


def test_repository_index_only_keeps_mapping_relevant_files(
    tmp_path,
):
    for directory in (
        "log",
        "output",
        "best_model",
        "build",
        "package.egg-info",
    ):
        path = tmp_path / directory
        path.mkdir()
        (path / "copied_model.py").write_text(
            "class Noise: pass\n",
            encoding="utf-8",
        )

    (tmp_path / "model.py").write_text(
        "class Model: pass\n",
        encoding="utf-8",
    )
    (tmp_path / "operator.cu").write_text(
        "// CUDA operator\n",
        encoding="utf-8",
    )
    (tmp_path / "operator.cpp").write_text(
        "// C++ operator\n",
        encoding="utf-8",
    )
    (tmp_path / "operator.pyi").write_text(
        "class Operator: ...\n",
        encoding="utf-8",
    )
    (tmp_path / "config.yaml").write_text(
        "epochs: 35\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# Reproduction\n",
        encoding="utf-8",
    )
    (tmp_path / "train.sh").write_text(
        "python model.py\n",
        encoding="utf-8",
    )
    (tmp_path / "model_best.pth").write_bytes(b"weights")
    (tmp_path / "training.log").write_text(
        "epoch=1\n",
        encoding="utf-8",
    )
    (tmp_path / "samples.csv").write_text(
        "x,y\n",
        encoding="utf-8",
    )

    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )

    assert {
        item.file_path
        for item in index.documents
    } == {
        "README.md",
        "config.yaml",
        "model.py",
        "train.sh",
    }
