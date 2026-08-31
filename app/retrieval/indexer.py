from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from app.retrieval.schemas import (
    CliOptionRecord,
    ImportRecord,
    IndexedDocument,
    RepositoryIndex,
    SymbolRecord,
)
from app.tools.repo_tools import is_mapping_relevant_file

_RAW_TOKEN_RE = re.compile(
    r"[A-Za-z0-9_+.-]+"
)
_CAMEL_BOUNDARY_RE = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])"
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)
    return digest.hexdigest()


def tokenize(value: str) -> list[str]:
    """
    同时保留完整 identifier 和 snake/camel 子词。

    TemporalBlock -> temporalblock, temporal, block
    batch_size -> batch_size, batch, size
    """

    tokens: list[str] = []

    for raw in _RAW_TOKEN_RE.findall(value):
        whole = raw.casefold()
        if whole:
            tokens.append(whole)

        camel_parts = _CAMEL_BOUNDARY_RE.split(raw)
        for camel_part in camel_parts:
            for piece in re.split(
                r"[_+.-]+",
                camel_part,
            ):
                normalized = piece.casefold().strip()
                if normalized and normalized != whole:
                    tokens.append(normalized)

    return tokens


def repository_revision(root: Path) -> str | None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "rev-parse",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return None

    revision = result.stdout.strip()
    return revision or None


def _literal_value(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


class _PythonMetadataVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.class_stack: list[str] = []
        self.symbols: list[SymbolRecord] = []
        self.imports: list[ImportRecord] = []
        self.cli_options: list[CliOptionRecord] = []

    def _record_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        is_async: bool,
    ) -> None:
        in_class = bool(self.class_stack)
        if is_async:
            kind = (
                "async_method"
                if in_class
                else "async_function"
            )
        else:
            kind = "method" if in_class else "function"

        qualified = ".".join(
            [*self.class_stack, node.name]
        )
        self.symbols.append(
            SymbolRecord(
                file_path=self.file_path,
                name=node.name,
                qualified_name=qualified,
                kind=kind,
                start_line=node.lineno,
                end_line=getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
            )
        )

    def visit_ClassDef(
        self,
        node: ast.ClassDef,
    ) -> None:
        qualified = ".".join(
            [*self.class_stack, node.name]
        )
        self.symbols.append(
            SymbolRecord(
                file_path=self.file_path,
                name=node.name,
                qualified_name=qualified,
                kind="class",
                start_line=node.lineno,
                end_line=getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
            )
        )
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ) -> None:
        self._record_function(
            node,
            is_async=False,
        )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self._record_function(
            node,
            is_async=True,
        )
        self.generic_visit(node)

    def visit_Import(
        self,
        node: ast.Import,
    ) -> None:
        for alias in node.names:
            self.imports.append(
                ImportRecord(
                    file_path=self.file_path,
                    imported_module=alias.name,
                    imported_names=[],
                    line=node.lineno,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(
        self,
        node: ast.ImportFrom,
    ) -> None:
        self.imports.append(
            ImportRecord(
                file_path=self.file_path,
                imported_module=node.module or "",
                imported_names=[
                    alias.name
                    for alias in node.names
                ],
                line=node.lineno,
            )
        )
        self.generic_visit(node)

    def visit_Call(
        self,
        node: ast.Call,
    ) -> None:
        is_add_argument = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        )
        if is_add_argument:
            flags = [
                value
                for argument in node.args
                if isinstance(
                    (value := _literal_value(argument)),
                    str,
                )
            ]
            keywords = {
                item.arg: _literal_value(item.value)
                for item in node.keywords
                if item.arg
            }
            self.cli_options.append(
                CliOptionRecord(
                    file_path=self.file_path,
                    flags=flags,
                    dest=(
                        str(keywords["dest"])
                        if keywords.get("dest")
                        is not None
                        else None
                    ),
                    default_repr=(
                        repr(keywords["default"])
                        if "default" in keywords
                        else None
                    ),
                    help_text=(
                        str(keywords["help"])
                        if keywords.get("help")
                        is not None
                        else None
                    ),
                    line=node.lineno,
                )
            )
        self.generic_visit(node)


def _iter_indexable_files(
    root: Path,
) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root)
        if not is_mapping_relevant_file(relative):
            continue
        files.append(path)
    return sorted(
        files,
        key=lambda item: item.relative_to(root).as_posix(),
    )


def _repo_fingerprint(
    documents: list[IndexedDocument],
) -> str:
    payload = "\n".join(
        (
            f"{document.file_path}:"
            f"{document.file_sha256}"
        )
        for document in documents
    )
    return sha256_text(payload)


def build_repository_index(
    repo_path: str | Path,
    *,
    index_version: str,
    max_file_bytes: int = 1024 * 1024,
) -> RepositoryIndex:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"未找到代码仓库：{root}"
        )

    documents: list[IndexedDocument] = []
    symbols: list[SymbolRecord] = []
    imports: list[ImportRecord] = []
    cli_options: list[CliOptionRecord] = []
    warnings: list[str] = []

    for path in _iter_indexable_files(root):
        relative = path.relative_to(root).as_posix()
        size_bytes = path.stat().st_size
        if size_bytes > max_file_bytes:
            warnings.append(
                f"SKIPPED_LARGE_FILE:{relative}:{size_bytes}"
            )
            continue

        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
        file_symbols: list[SymbolRecord] = []

        if path.suffix.casefold() == ".py":
            try:
                tree = ast.parse(
                    source,
                    filename=relative,
                )
            except SyntaxError as exc:
                warnings.append(
                    f"PYTHON_AST_FAILED:{relative}:"
                    f"{exc.lineno}:{exc.msg}"
                )
            else:
                visitor = _PythonMetadataVisitor(relative)
                visitor.visit(tree)
                file_symbols = visitor.symbols
                symbols.extend(visitor.symbols)
                imports.extend(visitor.imports)
                cli_options.extend(visitor.cli_options)

        document_tokens = [
            *tokenize(relative),
            *tokenize(source),
            *[
                token
                for symbol in file_symbols
                for token in tokenize(
                    symbol.qualified_name
                )
            ],
        ]
        frequencies = Counter(document_tokens)

        documents.append(
            IndexedDocument(
                file_path=relative,
                file_sha256=sha256_path(path),
                size_bytes=size_bytes,
                line_count=len(source.splitlines()),
                token_count=sum(frequencies.values()),
                term_frequencies=dict(frequencies),
            )
        )

    return RepositoryIndex(
        index_version=index_version,
        repo_root=str(root),
        repo_revision=repository_revision(root),
        repo_fingerprint=_repo_fingerprint(documents),
        documents=documents,
        symbols=sorted(
            symbols,
            key=lambda item: (
                item.file_path,
                item.start_line,
                item.qualified_name,
            ),
        ),
        imports=sorted(
            imports,
            key=lambda item: (
                item.file_path,
                item.line,
                item.imported_module,
            ),
        ),
        cli_options=sorted(
            cli_options,
            key=lambda item: (
                item.file_path,
                item.line,
            ),
        ),
        warnings=warnings,
    )


def load_repository_index(
    path: str | Path,
) -> RepositoryIndex:
    payload = json.loads(
        Path(path).read_text(encoding="utf-8")
    )
    return RepositoryIndex.model_validate(payload)
