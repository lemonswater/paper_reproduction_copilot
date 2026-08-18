"""安全路径验证与删除。"""
from __future__ import annotations
import json
import os
import re
import shutil
from pathlib import Path
from app.job_runtime.schemas import JobRecord
from app.retention.errors import RetentionPathUnsafe
from app.workspace.schemas import WorkspaceBinding

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

def _component(value: str, field: str) -> str:
    if value in {".", ".."} or not _SAFE_COMPONENT.fullmatch(value):
        raise RetentionPathUnsafe(f"{field} 不能用作受管目录名")
    return value

def _reject_symlink_chain(path: Path, root: Path) -> None:
    current = path
    while current != root:
        if current.is_symlink():
            raise RetentionPathUnsafe(f"路径链包含 symlink：{current}")
        if root not in current.parents:
            raise RetentionPathUnsafe(f"路径逃逸受管 root：{path}")
        current = current.parent

def _tree_logical_bytes(root: Path) -> int:
    """删除前估算；不跟随 symlink，symlink 本身也不允许存在。"""
    total = 0
    pending = [root]
    while pending:
        current = pending.pop()
        if current.is_symlink():
            raise RetentionPathUnsafe(f"待删除树包含 symlink：{current}")
        with os.scandir(current) as iterator:
            for entry in iterator:
                if entry.is_symlink():
                    raise RetentionPathUnsafe(
                        f"待删除树包含 symlink：{entry.path}"
                    )
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                else:
                    total += entry.stat(follow_symlinks=False).st_size
    return total

class SafePathRemover:
    def __init__(self, *, runs_root: Path, worker_root: Path):
        self.runs_root = runs_root.resolve()
        self.worker_root = worker_root.resolve()

    def _workspace_epoch_root(self, binding: WorkspaceBinding) -> Path:
        expected = (
            self.worker_root
            / "jobs"
            / _component(binding.job_id, "job_id")
            / "epochs"
            / f"{binding.assignment_epoch:08d}"
        )
        if Path(binding.workspace_root) != expected:
            raise RetentionPathUnsafe("workspace_root 与受管派生路径不一致")
        _reject_symlink_chain(expected, self.worker_root)

        if expected.exists():
            marker = expected / ".workspace-binding.json"
            if not marker.is_file() or marker.is_symlink():
                raise RetentionPathUnsafe("workspace binding marker 缺失")
            local = WorkspaceBinding.model_validate_json(
                marker.read_text(encoding="utf-8")
            )
            identity = (
                local.assignment_id,
                local.assignment_token,
                local.manifest_hash,
                local.job_id,
                local.run_id,
            )
            expected_identity = (
                binding.assignment_id,
                binding.assignment_token,
                binding.manifest_hash,
                binding.job_id,
                binding.run_id,
            )
            if identity != expected_identity:
                raise RetentionPathUnsafe("workspace binding marker 身份不一致")
        return expected

    def validate_job_paths(
        self,
        *,
        job: JobRecord,
        bindings: list[WorkspaceBinding],
    ) -> list[Path]:
        workspace_roots = [self._workspace_epoch_root(item) for item in bindings]

        legacy = self.runs_root / _component(job.run_id, "run_id")
        declared_run = Path(job.run_dir)
        binding_run_dirs = {Path(item.run_dir) for item in bindings}
        if declared_run == legacy:
            _reject_symlink_chain(legacy, self.runs_root)
            candidates = [*workspace_roots, legacy]
        elif declared_run in binding_run_dirs:
            candidates = workspace_roots
        else:
            raise RetentionPathUnsafe("Job run_dir 不是合法 legacy/workspace 路径")

        ordered = sorted(set(candidates), key=lambda item: len(item.parts))
        result: list[Path] = []
        for candidate in ordered:
            if any(parent == candidate or parent in candidate.parents for parent in result):
                continue
            result.append(candidate)
        return result

    def remove_tree(self, path: Path) -> int:
        """不存在视为已删除；存在时先完整安全扫描，再 rmtree。"""
        if not path.exists() and not path.is_symlink():
            return 0
        if path.is_symlink() or not path.is_dir():
            raise RetentionPathUnsafe(f"GC target 不是普通目录：{path}")
        size = _tree_logical_bytes(path)
        shutil.rmtree(path)
        return size