from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from app.tool_contracts.errors import ToolBoundaryError
from app.tool_contracts.models import (
    ActionRiskInput,
    ActionRiskOutput,
    CodeSliceInput,
    CodeSliceOutput,
    ErrorClassificationOutput,
    PythonSymbolsInput,
    PythonSymbolsOutput,
    ReadLogInput,
    RelativeFilesOutput,
    RepoClassificationOutput,
    RepoListFilesInput,
    RepoPathInput,
    RepoTreeInput,
    RepoTreeOutput,
    SearchKeywordsInput,
    SearchKeywordsOutput,
    SearchTextInput,
    SearchTextOutput,
    TextOutput,
    TextTransformInput,
    TracebackPathsInput,
    TracebackPathsOutput,
)
from app.tool_contracts.schemas import ToolInvocationContext
from app.tools import (
    code_tools,
    log_tools,
    repo_tools,
    safe_shell_tools,
    search_tools,
)


def _context_root(
    context: ToolInvocationContext,
    scope: str,
) -> Path:
    raw_root = (
        context.workspace_root
        if scope == "workspace"
        else context.run_root
    )
    if not raw_root:
        raise ToolBoundaryError(f"调用上下文缺少 {scope}_root")

    root = Path(raw_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"{scope}_root 不存在")
    return root


def _resolve_scoped_path(
    raw_path: str,
    *,
    context: ToolInvocationContext,
    scope: str,
    expected: str,
) -> Path:
    root = _context_root(context, scope)
    candidate = Path(raw_path).expanduser()
    unresolved = candidate if candidate.is_absolute() else root / candidate
    resolved = unresolved.resolve()

    if resolved != root and root not in resolved.parents:
        raise ToolBoundaryError(f"路径位于 {scope}_root 之外")
    if unresolved.is_symlink():
        raise ToolBoundaryError("不允许把符号链接作为工具输入")

    if expected == "file" and not resolved.is_file():
        raise FileNotFoundError("工具输入文件不存在")
    if expected == "directory" and not resolved.is_dir():
        raise FileNotFoundError("工具输入目录不存在")
    return resolved


def repo_tree_adapter(
    payload: RepoTreeInput,
    context: ToolInvocationContext,
) -> RepoTreeOutput:
    repo = _resolve_scoped_path(
        payload.repo_path,
        context=context,
        scope="workspace",
        expected="directory",
    )
    return RepoTreeOutput(
        tree=repo_tools.get_file_tree(
            str(repo),
            max_depth=payload.max_depth,
        )
    )


def repo_list_files_adapter(
    payload: RepoListFilesInput,
    context: ToolInvocationContext,
) -> RelativeFilesOutput:
    repo = _resolve_scoped_path(
        payload.repo_path,
        context=context,
        scope="workspace",
        expected="directory",
    )
    suffixes = (
        tuple(payload.suffixes)
        if payload.suffixes is not None
        else None
    )
    return RelativeFilesOutput(
        files=repo_tools.list_files(
            str(repo),
            suffixes=suffixes,
        )
    )


def repo_classify_adapter(
    payload: RepoPathInput,
    context: ToolInvocationContext,
) -> RepoClassificationOutput:
    repo = _resolve_scoped_path(
        payload.repo_path,
        context=context,
        scope="workspace",
        expected="directory",
    )
    return RepoClassificationOutput.model_validate(
        repo_tools.classify_repo_file(str(repo))
    )


def search_text_adapter(
    payload: SearchTextInput,
    context: ToolInvocationContext,
) -> SearchTextOutput:
    repo = _resolve_scoped_path(
        payload.repo_path,
        context=context,
        scope="workspace",
        expected="directory",
    )
    return SearchTextOutput(
        matches=search_tools.search_text(
            str(repo),
            payload.query,
            max_results=payload.max_results,
            literal=payload.literal,
            ignore_case=payload.ignore_case,
            timeout_seconds=payload.timeout_seconds,
        )
    )


def search_keywords_adapter(
    payload: SearchKeywordsInput,
    context: ToolInvocationContext,
) -> SearchKeywordsOutput:
    repo = _resolve_scoped_path(
        payload.repo_path,
        context=context,
        scope="workspace",
        expected="directory",
    )
    return SearchKeywordsOutput(
        matches=search_tools.search_keywords(
            str(repo),
            payload.keywords,
            max_per_keyword=payload.max_per_keyword,
            timeout_seconds=payload.timeout_seconds,
        )
    )


def code_slice_adapter(
    payload: CodeSliceInput,
    context: ToolInvocationContext,
) -> CodeSliceOutput:
    path = _resolve_scoped_path(
        payload.path,
        context=context,
        scope="workspace",
        expected="file",
    )
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("代码文件超过 2 MiB 读取上限")
    return CodeSliceOutput(
        text=code_tools.read_file_slice(
            str(path),
            start_line=payload.start_line,
            end_line=payload.end_line,
        )
    )


def python_symbols_adapter(
    payload: PythonSymbolsInput,
    context: ToolInvocationContext,
) -> PythonSymbolsOutput:
    path = _resolve_scoped_path(
        payload.path,
        context=context,
        scope="workspace",
        expected="file",
    )
    if path.suffix.lower() != ".py":
        raise ValueError("符号抽取只接受 .py 文件")
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Python 文件超过 2 MiB 解析上限")
    return PythonSymbolsOutput(
        symbols=code_tools.extract_python_symbols(str(path))
    )


def read_log_adapter(
    payload: ReadLogInput,
    context: ToolInvocationContext,
) -> TextOutput:
    path = _resolve_scoped_path(
        payload.path,
        context=context,
        scope="run",
        expected="file",
    )
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("日志文件超过 50 MiB 读取上限")
    return TextOutput(
        text=log_tools.read_log(
            str(path),
            max_chars=payload.max_chars,
        )
    )


def extract_traceback_adapter(
    payload: TextTransformInput,
    context: ToolInvocationContext,
) -> TextOutput:
    del context
    return TextOutput(
        text=log_tools.extract_traceback(payload.text)
    )


def classify_error_adapter(
    payload: TextTransformInput,
    context: ToolInvocationContext,
) -> ErrorClassificationOutput:
    del context
    return ErrorClassificationOutput(
        category=log_tools.classify_error_heuristic(payload.text)
    )


def traceback_paths_adapter(
    payload: TracebackPathsInput,
    context: ToolInvocationContext,
) -> TracebackPathsOutput:
    if payload.repo_path is None:
        return TracebackPathsOutput(paths=[])
    repo = _resolve_scoped_path(
        payload.repo_path,
        context=context,
        scope="workspace",
        expected="directory",
    )
    return TracebackPathsOutput(
        paths=log_tools.extract_repo_traceback_paths(
            payload.traceback,
            repo_path=str(repo),
        )
    )


def assess_action_risk_adapter(
    payload: ActionRiskInput,
    context: ToolInvocationContext,
) -> ActionRiskOutput:
    del context
    risk = safe_shell_tools.assess_action_risk(payload.action)
    return ActionRiskOutput.model_validate(asdict(risk))
