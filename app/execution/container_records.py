from __future__ import annotations

"""Phase 27 容器运行记录的原子持久化。

使用 run-native Artifact，符合 Phase 26 的 Workspace 生命周期。
记录路径固定在 ``<run_dir>/execution/container_runtime.json``。
"""


import json
import os
from pathlib import Path

from app.execution.container_schemas import (
    ContainerRuntimeRecord,
)


def record_path(run_dir: Path) -> Path:
    """返回 ``<run_dir>/execution/container_runtime.json``。"""

    return run_dir / "execution" / "container_runtime.json"


def write_container_record(
    run_dir: Path,
    record: ContainerRuntimeRecord,
) -> Path:
    """原子写入容器运行记录。

    先写 ``.json.part``，fsync 后 rename，保证 create-before-start
    journal 在崩溃后仍可读。
    """

    target = record_path(run_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.part")
    payload = json.dumps(
        record.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    temporary.write_text(
        payload + "\n", encoding="utf-8"
    )
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(target)
    return target


def load_container_record(
    run_dir: Path,
) -> ContainerRuntimeRecord | None:
    """加载容器运行记录；不存在时返回 ``None``。"""

    target = record_path(run_dir)
    if not target.exists():
        return None
    return ContainerRuntimeRecord.model_validate_json(
        target.read_text(encoding="utf-8")
    )
