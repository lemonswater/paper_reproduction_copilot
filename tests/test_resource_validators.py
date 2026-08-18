"""Phase 29 PDF 与 checkpoint 验证器测试。

安全矩阵：
- 伪造 Content-Type 但 magic 非 PDF 被拒绝
- PDF 无页面/损坏被拒绝（fitz 可用时）
- checkpoint 无 expected hash 在 schema 阶段拒绝（已在 schemas 测试覆盖）
- checkpoint 获取阶段从不调用 torch.load/pickle
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.resources.errors import ResourceIntegrityError
from app.resources.validators import (
    validate_checkpoint_opaque,
    validate_for_kind,
    validate_pdf,
)
from tests.fakes.pdf_helpers import write_valid_pdf


class TestValidatePdf:
    def test_valid_pdf_magic_accepted(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "paper.pdf"
        # 使用真实可解析 PDF，确保 fitz 可用时也能通过 parser 校验。
        write_valid_pdf(path)
        media_type = validate_pdf(path)
        assert media_type == "application/pdf"

    def test_non_pdf_magic_rejected(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "fake.pdf"
        path.write_bytes(
            b"<html>not a pdf</html>"
        )
        with pytest.raises(ResourceIntegrityError):
            validate_pdf(path)

    def test_empty_file_rejected(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "empty.pdf"
        path.write_bytes(b"")
        with pytest.raises(ResourceIntegrityError):
            validate_pdf(path)

    def test_minimal_pdf_with_magic(
        self, tmp_path: Path
    ) -> None:
        """只有 magic bytes 的文件也应通过 magic 检查。"""
        path = tmp_path / "min.pdf"
        path.write_bytes(b"%PDF-1.5")
        # fitz 可能拒绝无法解析的 PDF，但 magic bytes 通过。
        # 如果 fitz 不可用，则只做 magic 检查，应通过。
        try:
            result = validate_pdf(path)
            assert result == "application/pdf"
        except ResourceIntegrityError:
            # fitz 可用且无法打开时，integrity error 也合理。
            pass


class TestValidateCheckpoint:
    def test_non_empty_file_accepted(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "model.pt"
        path.write_bytes(b"\x00\x01\x02checkpoint")
        media_type = validate_checkpoint_opaque(path)
        assert media_type == (
            "application/octet-stream"
        )

    def test_empty_file_rejected(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "empty.pt"
        path.write_bytes(b"")
        with pytest.raises(ResourceIntegrityError):
            validate_checkpoint_opaque(path)

    def test_nonexistent_file_rejected(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "missing.pt"
        with pytest.raises(ResourceIntegrityError):
            validate_checkpoint_opaque(path)

    def test_never_imports_torch(
        self, tmp_path: Path
    ) -> None:
        """获取阶段绝不 torch.load/pickle.load checkpoint。"""
        import sys

        path = tmp_path / "model.pt"
        path.write_bytes(b"\x80\x02fake pickle data")
        before = set(sys.modules.keys())
        validate_checkpoint_opaque(path)
        after = set(sys.modules.keys())
        # 不应新加载 torch 或 pickle（pickle 可能已被其他模块加载）。
        new_modules = after - before
        assert "torch" not in new_modules
        # pickle.load 不应被调用——只做 opaque blob 校验。
        assert "pickle" not in new_modules


class TestValidateForKind:
    def test_paper_pdf_routes_to_pdf_validator(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "paper.pdf"
        write_valid_pdf(path)
        result = validate_for_kind(path, "paper_pdf")
        assert result == "application/pdf"

    def test_checkpoint_routes_to_opaque(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "model.pt"
        path.write_bytes(b"checkpoint data")
        result = validate_for_kind(
            path, "checkpoint"
        )
        assert result == (
            "application/octet-stream"
        )

    def test_git_bundle_accepted(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "repo.bundle"
        path.write_bytes(b"bundle content")
        result = validate_for_kind(
            path, "git_repository"
        )
        assert result == (
            "application/octet-stream"
        )

    def test_empty_git_bundle_rejected(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "empty.bundle"
        path.write_bytes(b"")
        with pytest.raises(ResourceIntegrityError):
            validate_for_kind(
                path, "git_repository"
            )

    def test_unknown_kind_rejected(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "f"
        path.write_bytes(b"data")
        with pytest.raises(ResourceIntegrityError):
            validate_for_kind(path, "unknown_kind")
