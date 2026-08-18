from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.secrets.redaction import SecretRedactor


@dataclass(frozen=True)
class SecretLeakFinding:
    path: str
    secret_names: tuple[str, ...]


class SecretLeakScanner:
    """按 chunk 扫描已知 Secret bytes，同时处理跨 chunk 匹配。"""

    def __init__(
        self,
        *,
        redactor: SecretRedactor,
        excluded_roots: tuple[Path, ...] = (),
        chunk_bytes: int = 1024 * 1024,
    ):
        if chunk_bytes < 4096:
            raise ValueError("chunk_bytes 不能小于 4096")
        self.redactor = redactor
        self.chunk_bytes = chunk_bytes
        self.excluded_roots = tuple(
            Path(os.path.abspath(item.expanduser()))
            for item in excluded_roots
        )
        self._overlap = max(
            (
                len(pattern) - 1
                for pattern in redactor.byte_patterns
            ),
            default=0,
        )

    def _is_excluded(self, path: Path) -> bool:
        absolute = Path(os.path.abspath(path))
        return any(
            absolute == root or absolute.is_relative_to(root)
            for root in self.excluded_roots
        )

    def scan_file(
        self,
        path: Path,
    ) -> SecretLeakFinding | None:
        absolute = Path(os.path.abspath(path.expanduser()))
        if self._is_excluded(absolute) or absolute.is_symlink():
            return None
        if not absolute.is_file():
            return None

        names: set[str] = set()
        carry = b""
        with absolute.open("rb") as handle:
            while True:
                chunk = handle.read(self.chunk_bytes)
                if not chunk:
                    break
                window = carry + chunk
                names.update(
                    self.redactor.find_known_in_bytes(window)
                )
                carry = (
                    window[-self._overlap :]
                    if self._overlap
                    else b""
                )

        if not names:
            return None
        return SecretLeakFinding(
            path=str(absolute),
            secret_names=tuple(sorted(names)),
        )

    def scan_roots(
        self,
        roots: list[Path],
    ) -> list[SecretLeakFinding]:
        findings: list[SecretLeakFinding] = []
        seen: set[Path] = set()
        for raw_root in roots:
            root = Path(
                os.path.abspath(raw_root.expanduser())
            )
            if self._is_excluded(root) or not root.exists():
                continue
            candidates = [root] if root.is_file() else root.rglob("*")
            for path in candidates:
                absolute = Path(os.path.abspath(path))
                if absolute in seen:
                    continue
                seen.add(absolute)
                finding = self.scan_file(absolute)
                if finding is not None:
                    findings.append(finding)
        return sorted(findings, key=lambda item: item.path)
