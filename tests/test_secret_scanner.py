from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.secrets.redaction import SecretRedactor
from app.secrets.scanner import (
    SecretLeakFinding,
    SecretLeakScanner,
)


SECRET_VALUE = "sk-scanner-secret-1234567890"
SECRET_NAME = "OPENAI_API_KEY"


def _redactor() -> SecretRedactor:
    return SecretRedactor(
        known_values={SECRET_NAME: SECRET_VALUE}
    )


class TestScanFile:
    def test_scan_finds_known_secret(self, tmp_path: Path):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        target = tmp_path / "config.txt"
        target.write_text(
            f"api_key={SECRET_VALUE}\n",
            encoding="utf-8",
        )
        finding = scanner.scan_file(target)
        assert finding is not None
        assert SECRET_NAME in finding.secret_names
        assert str(target) in finding.path

    def test_scan_clean_file_returns_none(self, tmp_path: Path):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        target = tmp_path / "clean.txt"
        target.write_text("no secrets here\n", encoding="utf-8")
        finding = scanner.scan_file(target)
        assert finding is None

    def test_scan_nonexistent_file_returns_none(
        self, tmp_path: Path
    ):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        finding = scanner.scan_file(tmp_path / "missing.txt")
        assert finding is None

    def test_scan_directory_returns_none(self, tmp_path: Path):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        finding = scanner.scan_file(tmp_path)
        assert finding is None

    def test_scan_symlink_skipped(self, tmp_path: Path):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        real = tmp_path / "real.txt"
        real.write_text(
            f"key={SECRET_VALUE}\n", encoding="utf-8"
        )
        link = tmp_path / "link.txt"
        os.symlink(real, link)
        finding = scanner.scan_file(link)
        assert finding is None

    def test_scan_finds_multiple_secrets(self, tmp_path: Path):
        redactor = SecretRedactor(
            known_values={
                "K1": "alpha-scanner-secret-12",
                "K2": "beta-scanner-secret-123",
            }
        )
        scanner = SecretLeakScanner(redactor=redactor)
        target = tmp_path / "multi.txt"
        target.write_text(
            "alpha-scanner-secret-12 and "
            "beta-scanner-secret-123\n",
            encoding="utf-8",
        )
        finding = scanner.scan_file(target)
        assert finding is not None
        assert "K1" in finding.secret_names
        assert "K2" in finding.secret_names

    def test_cross_chunk_matching(self, tmp_path: Path):
        """Secret 恰好跨 chunk 边界时仍能被检测。"""
        redactor = _redactor()
        # 使用很小的 chunk 强制跨边界
        scanner = SecretLeakScanner(
            redactor=redactor,
            chunk_bytes=4096,
        )
        # 构造文件：padding + secret + padding
        padding_before = b"x" * 4090
        secret_bytes = SECRET_VALUE.encode("utf-8")
        padding_after = b"y" * 100
        target = tmp_path / "cross_chunk.bin"
        target.write_bytes(
            padding_before + secret_bytes + padding_after
        )
        finding = scanner.scan_file(target)
        assert finding is not None
        assert SECRET_NAME in finding.secret_names

    def test_empty_redactor_finds_nothing(self, tmp_path: Path):
        redactor = SecretRedactor.empty()
        scanner = SecretLeakScanner(redactor=redactor)
        target = tmp_path / "data.txt"
        target.write_text(SECRET_VALUE, encoding="utf-8")
        finding = scanner.scan_file(target)
        assert finding is None


class TestScanRoots:
    def test_scan_roots_finds_leak(self, tmp_path: Path):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        root = tmp_path / "project"
        root.mkdir()
        (root / "a.txt").write_text(
            f"key={SECRET_VALUE}\n", encoding="utf-8"
        )
        (root / "sub").mkdir()
        (root / "sub" / "b.txt").write_text(
            "clean\n", encoding="utf-8"
        )
        findings = scanner.scan_roots([root])
        assert len(findings) == 1
        assert SECRET_NAME in findings[0].secret_names
        assert "a.txt" in findings[0].path

    def test_scan_roots_multiple_files(self, tmp_path: Path):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        root = tmp_path / "data"
        root.mkdir()
        (root / "f1.txt").write_text(
            SECRET_VALUE, encoding="utf-8"
        )
        (root / "f2.txt").write_text(
            SECRET_VALUE, encoding="utf-8"
        )
        findings = scanner.scan_roots([root])
        assert len(findings) == 2
        paths = {f.path for f in findings}
        assert any("f1.txt" in p for p in paths)
        assert any("f2.txt" in p for p in paths)

    def test_scan_roots_sorted_by_path(self, tmp_path: Path):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        root = tmp_path / "sorted"
        root.mkdir()
        (root / "z.txt").write_text(
            SECRET_VALUE, encoding="utf-8"
        )
        (root / "a.txt").write_text(
            SECRET_VALUE, encoding="utf-8"
        )
        findings = scanner.scan_roots([root])
        assert len(findings) == 2
        assert findings[0].path < findings[1].path

    def test_scan_roots_empty(self, tmp_path: Path):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        root = tmp_path / "empty"
        root.mkdir()
        findings = scanner.scan_roots([root])
        assert findings == []

    def test_scan_roots_nonexistent_skipped(
        self, tmp_path: Path
    ):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        findings = scanner.scan_roots(
            [tmp_path / "does_not_exist"]
        )
        assert findings == []

    def test_scan_single_file_root(self, tmp_path: Path):
        redactor = _redactor()
        scanner = SecretLeakScanner(redactor=redactor)
        target = tmp_path / "single.txt"
        target.write_text(
            SECRET_VALUE, encoding="utf-8"
        )
        findings = scanner.scan_roots([target])
        assert len(findings) == 1


class TestExcludedRoots:
    def test_excluded_root_not_scanned(self, tmp_path: Path):
        redactor = _redactor()
        excluded = tmp_path / "vault"
        excluded.mkdir()
        (excluded / "secret.txt").write_text(
            SECRET_VALUE, encoding="utf-8"
        )
        scanner = SecretLeakScanner(
            redactor=redactor,
            excluded_roots=(excluded,),
        )
        findings = scanner.scan_roots([excluded])
        assert findings == []

    def test_excluded_subdirectory_not_scanned(
        self, tmp_path: Path
    ):
        redactor = _redactor()
        root = tmp_path / "project"
        root.mkdir()
        excluded = root / "secrets"
        excluded.mkdir()
        (excluded / "data.txt").write_text(
            SECRET_VALUE, encoding="utf-8"
        )
        (root / "normal.txt").write_text(
            "clean\n", encoding="utf-8"
        )
        scanner = SecretLeakScanner(
            redactor=redactor,
            excluded_roots=(excluded,),
        )
        findings = scanner.scan_roots([root])
        assert findings == []

    def test_excluded_file_directly(self, tmp_path: Path):
        redactor = _redactor()
        target = tmp_path / "config.txt"
        target.write_text(
            SECRET_VALUE, encoding="utf-8"
        )
        scanner = SecretLeakScanner(
            redactor=redactor,
            excluded_roots=(target,),
        )
        finding = scanner.scan_file(target)
        assert finding is None


class TestChunkValidation:
    def test_chunk_too_small_raises(self):
        redactor = _redactor()
        with pytest.raises(ValueError):
            SecretLeakScanner(
                redactor=redactor,
                chunk_bytes=100,
            )

    def test_chunk_minimum_accepted(self):
        redactor = _redactor()
        scanner = SecretLeakScanner(
            redactor=redactor,
            chunk_bytes=4096,
        )
        assert scanner.chunk_bytes == 4096


class TestFindingDataclass:
    def test_finding_is_frozen(self):
        finding = SecretLeakFinding(
            path="/tmp/test.txt",
            secret_names=("K1",),
        )
        with pytest.raises(AttributeError):
            finding.path = "/other"  # type: ignore[misc]

    def test_finding_fields(self):
        finding = SecretLeakFinding(
            path="/tmp/test.txt",
            secret_names=("K1", "K2"),
        )
        assert finding.path == "/tmp/test.txt"
        assert finding.secret_names == ("K1", "K2")
