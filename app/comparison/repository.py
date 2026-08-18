from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from pydantic import ValidationError

from app.comparison.errors import (
    ComparisonConflictError,
    ComparisonIntegrityError,
    ComparisonLimitExceededError,
    ComparisonNotFoundError,
)
from app.comparison.identity import (
    canonical_json_bytes,
    validate_report_identity,
)
from app.comparison.rendering import render_comparison_markdown
from app.comparison.schemas import (
    ComparisonListItem,
    ComparisonListResponse,
    ComparisonReport,
)


COMPARISON_ID_RE = re.compile(r"^comparison_[0-9a-f]{24}$")


class FileComparisonRepository:
    """单机内容寻址仓库，不修改源 Run，也不跟随符号链接。"""

    def __init__(
        self,
        root: Path,
        *,
        max_report_bytes: int,
        list_scan_limit: int,
        staging_ttl_seconds: int,
    ):
        self.max_report_bytes = max_report_bytes
        self.list_scan_limit = list_scan_limit
        self.staging_ttl_seconds = staging_ttl_seconds

        configured_root = root.expanduser()
        if configured_root.is_symlink():
            raise ComparisonConflictError("Comparison root 不能是符号链接")
        configured_root.mkdir(parents=True, exist_ok=True)
        if configured_root.is_symlink() or not configured_root.is_dir():
            raise ComparisonConflictError("Comparison root 必须是普通目录")
        self.root = configured_root.resolve()
        self.staging_root = self.root / ".staging"
        if self.staging_root.is_symlink():
            raise ComparisonConflictError("Comparison staging 不能是符号链接")
        self.staging_root.mkdir(parents=True, exist_ok=True)
        if self.staging_root.is_symlink():
            raise ComparisonConflictError("Comparison staging 不能是符号链接")

    def ping(self) -> None:
        if not self.root.is_dir() or not os.access(self.root, os.R_OK | os.W_OK):
            raise ComparisonConflictError("Comparison repository 不可读写")

    def _dir_for(self, comparison_id: str) -> Path:
        if not COMPARISON_ID_RE.fullmatch(comparison_id):
            raise ComparisonNotFoundError("非法 comparison_id")
        return self.root / comparison_id

    def _cleanup_staging(self) -> None:
        """只清理由本 Repository 创建、且超过 TTL 的直属 staging 目录。"""

        now = time.time()
        for child in self.staging_root.iterdir():
            if child.is_symlink() or not child.name.startswith("comparison-"):
                continue
            try:
                age = now - child.lstat().st_mtime
            except FileNotFoundError:
                continue
            if age >= self.staging_ttl_seconds and child.is_dir():
                shutil.rmtree(child)

    def _read_report_path(self, path: Path) -> ComparisonReport:
        if path.is_symlink() or not path.is_file():
            raise ComparisonNotFoundError("Comparison JSON 不存在")
        size = path.lstat().st_size
        if size > self.max_report_bytes:
            raise ComparisonLimitExceededError("Comparison JSON 超过读取上限")
        raw = path.read_bytes()
        if len(raw) != size or len(raw) > self.max_report_bytes:
            raise ComparisonIntegrityError("Comparison JSON 读取期间发生变化")
        try:
            report = ComparisonReport.model_validate_json(raw)
        except (ValidationError, json.JSONDecodeError) as exc:
            raise ComparisonIntegrityError(f"Comparison JSON 无效：{exc}") from exc
        validate_report_identity(report)
        return report

    @staticmethod
    def _durable_write(path: Path, payload: bytes) -> None:
        """写入、flush、fsync，避免崩溃后留下已重命名但未落盘的空文件。"""

        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    def get(self, comparison_id: str) -> ComparisonReport:
        directory = self._dir_for(comparison_id)
        if directory.is_symlink() or not directory.is_dir():
            raise ComparisonNotFoundError(f"Comparison 不存在：{comparison_id}")
        report = self._read_report_path(directory / "comparison.json")
        if report.comparison_id != comparison_id:
            raise ComparisonIntegrityError("目录 ID 与 Comparison 内容不一致")
        return report

    def save(self, report: ComparisonReport) -> ComparisonReport:
        """幂等保存；同 ID 不同内容必须报冲突，不能覆盖。"""

        validate_report_identity(report)
        target = self._dir_for(report.comparison_id)
        if target.exists():
            existing = self.get(report.comparison_id)
            if existing.comparison_hash != report.comparison_hash:
                raise ComparisonConflictError("相同 comparison_id 对应不同内容")
            return existing

        self._cleanup_staging()
        json_bytes = canonical_json_bytes(report.model_dump(mode="json"))
        markdown_bytes = render_comparison_markdown(report).encode("utf-8")
        if len(json_bytes) > self.max_report_bytes:
            raise ComparisonLimitExceededError("Comparison JSON 超过保存上限")
        if len(markdown_bytes) > self.max_report_bytes:
            raise ComparisonLimitExceededError("Comparison Markdown 超过保存上限")

        staging = Path(
            tempfile.mkdtemp(prefix="comparison-", dir=self.staging_root)
        )
        try:
            self._durable_write(staging / "comparison.json", json_bytes)
            self._durable_write(staging / "comparison.md", markdown_bytes)

            # staging 与 target 在同一文件系统，rename 才具有原子目录发布语义。
            try:
                staging.rename(target)
            except OSError:
                # POSIX 对"目标非空目录"可能返回 EEXIST 或 ENOTEMPTY。
                if not target.exists():
                    raise
                existing = self.get(report.comparison_id)
                if existing.comparison_hash != report.comparison_hash:
                    raise ComparisonConflictError(
                        "并发写入产生相同 ID 的不同 Comparison"
                    )
                return existing

            # fsync 父目录，提升断电后目录项持久化概率。
            directory_fd = os.open(
                self.root,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            return self.get(report.comparison_id)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def list_for_job(
        self,
        job_id: str,
        *,
        limit: int = 100,
    ) -> ComparisonListResponse:
        if limit < 1 or limit > 500:
            raise ComparisonLimitExceededError("limit 必须位于 1..500")

        candidates = [
            path
            for path in self.root.iterdir()
            if path.name != ".staging"
            and COMPARISON_ID_RE.fullmatch(path.name)
        ]
        if len(candidates) > self.list_scan_limit:
            raise ComparisonLimitExceededError(
                "Comparison 数量超过文件索引扫描上限；下一阶段应增加轻量索引"
            )

        items: list[ComparisonListItem] = []
        for path in candidates:
            if path.is_symlink() or not path.is_dir():
                continue
            report = self.get(path.name)
            if job_id in {report.base.job_id, report.target.job_id}:
                items.append(ComparisonListItem.from_report(report))

        items.sort(key=lambda item: (item.created_at, item.comparison_id), reverse=True)
        selected = items[:limit]
        return ComparisonListResponse(items=selected, count=len(selected))
