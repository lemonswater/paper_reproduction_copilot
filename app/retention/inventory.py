"""容量盘点：不跟随符号链接统计受管目录。"""
from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from app.retention.schemas import ManagedRootUsage, StorageSummary

@dataclass(frozen=True)
class InventoryConfig:
    roots: tuple[tuple[str, Path], ...]
    filesystem_anchor: Path
    soft_limit_bytes: int
    hard_limit_bytes: int
    min_free_bytes: int
    max_warnings: int
    destructive_gc_supported: bool

def _allocated_bytes(stat_result: os.stat_result) -> int:
    blocks = getattr(stat_result, "st_blocks", None)
    return stat_result.st_size if blocks is None else int(blocks) * 512

def _scan_root(
    *,
    name: str,
    root: Path,
    warnings: list[str],
    max_warnings: int,
) -> ManagedRootUsage:
    """使用 scandir + follow_symlinks=False，绝不穿过 symlink。"""
    logical = 0
    allocated = 0
    files = 0
    directories = 0
    skipped_symlinks = 0
    errors = 0

    if not root.exists() and not root.is_symlink():
        return ManagedRootUsage(
            name=name,
            path=str(root),
            exists=False,
            logical_bytes=0,
            allocated_bytes=0,
            file_count=0,
            directory_count=0,
            skipped_symlink_count=0,
            error_count=0,
        )

    if root.is_symlink():
        return ManagedRootUsage(
            name=name,
            path=str(root),
            exists=True,
            logical_bytes=0,
            allocated_bytes=0,
            file_count=0,
            directory_count=0,
            skipped_symlink_count=1,
            error_count=0,
        )

    pending = [root]
    while pending:
        current = pending.pop()
        try:
            current_stat = current.stat(follow_symlinks=False)
            logical += current_stat.st_size
            allocated += _allocated_bytes(current_stat)
            if current.is_file():
                files += 1
                continue
            directories += 1

            with os.scandir(current) as iterator:
                for entry in iterator:
                    try:
                        if entry.is_symlink():
                            skipped_symlinks += 1
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(Path(entry.path))
                            continue
                        stat_result = entry.stat(follow_symlinks=False)
                        logical += stat_result.st_size
                        allocated += _allocated_bytes(stat_result)
                        files += 1
                    except OSError as exc:
                        errors += 1
                        if len(warnings) < max_warnings:
                            warnings.append(f"inventory entry skipped: {exc}")
        except OSError as exc:
            errors += 1
            if len(warnings) < max_warnings:
                warnings.append(f"inventory root skipped: {current}: {exc}")

    return ManagedRootUsage(
        name=name,
        path=str(root),
        exists=True,
        logical_bytes=logical,
        allocated_bytes=allocated,
        file_count=files,
        directory_count=directories,
        skipped_symlink_count=skipped_symlinks,
        error_count=errors,
    )

class StorageInventoryService:
    def __init__(self, config: InventoryConfig):
        self.config = config

    def summarize(self) -> StorageSummary:
        warnings: list[str] = []
        usages = [
            _scan_root(
                name=name,
                root=path,
                warnings=warnings,
                max_warnings=self.config.max_warnings,
            )
            for name, path in self.config.roots
        ]
        statvfs = os.statvfs(self.config.filesystem_anchor)
        total = statvfs.f_blocks * statvfs.f_frsize
        free = statvfs.f_bavail * statvfs.f_frsize
        managed_allocated = sum(item.allocated_bytes for item in usages)

        hard = (
            (
                self.config.hard_limit_bytes > 0
                and managed_allocated >= self.config.hard_limit_bytes
            )
            or free < self.config.min_free_bytes
        )
        soft = (
            self.config.soft_limit_bytes > 0
            and managed_allocated >= self.config.soft_limit_bytes
        )
        pressure = "hard" if hard else "soft" if soft else "normal"

        return StorageSummary(
            generated_at=datetime.now(timezone.utc).isoformat(),
            managed_logical_bytes=sum(item.logical_bytes for item in usages),
            managed_allocated_bytes=managed_allocated,
            filesystem_total_bytes=total,
            filesystem_free_bytes=free,
            soft_limit_bytes=self.config.soft_limit_bytes,
            hard_limit_bytes=self.config.hard_limit_bytes,
            min_free_bytes=self.config.min_free_bytes,
            pressure=pressure,
            destructive_gc_supported=self.config.destructive_gc_supported,
            roots=usages,
            warnings=warnings,
        )