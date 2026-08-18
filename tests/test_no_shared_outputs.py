from __future__ import annotations

from pathlib import Path


def test_graph_nodes_do_not_write_settings_output_dir():
    offenders = []
    for path in sorted(Path("app/nodes").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "settings.output_dir" in source:
            offenders.append(str(path))

    assert offenders == [], (
        "以下 Graph 节点仍在写共享 outputs："
        + ", ".join(offenders)
    )


def test_eval_does_not_read_shared_outputs():
    source = Path("app/evaluation/run_eval.py").read_text(
        encoding="utf-8"
    )
    assert 'Path("outputs")' not in source
    assert "OUTPUT_DIR" not in source