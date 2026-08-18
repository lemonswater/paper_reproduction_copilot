from __future__ import annotations

from app.tool_contracts import adapters
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
from app.tool_contracts.registry import (
    ToolRegistry,
    build_tool_definition,
)
from app.tool_contracts.schemas import (
    ToolDeterminism,
    ToolEffect,
    ToolErrorSpec,
    ToolExposure,
    ToolFailure,
    ToolRisk,
)
from app.tools.search_tools import SearchToolError

VERSION = "phase40-v1"


COMMON_READ_ERRORS = [
    ToolErrorSpec(
        code="TOOL_PATH_OUTSIDE_SCOPE",
        category="policy",
        retryable=False,
        summary="输入路径位于受控根目录之外",
    ),
    ToolErrorSpec(
        code="TOOL_INPUT_NOT_FOUND",
        category="user",
        retryable=False,
        summary="输入文件或目录不存在",
    ),
    ToolErrorSpec(
        code="TOOL_PERMISSION_DENIED",
        category="environment",
        retryable=False,
        summary="当前进程无权读取输入",
    ),
    ToolErrorSpec(
        code="TOOL_INPUT_REJECTED",
        category="policy",
        retryable=False,
        summary="输入违反 Adapter 的大小、类型或范围限制",
    ),
    ToolErrorSpec(
        code="TOOL_IO_ERROR",
        category="environment",
        retryable=False,
        summary="读取文件系统时发生错误",
    ),
]


SEARCH_ERRORS = [
    *COMMON_READ_ERRORS,
    ToolErrorSpec(
        code="TOOL_SEARCH_BACKEND_FAILED",
        category="tool",
        retryable=False,
        summary="rg 或搜索 fallback 执行失败",
    ),
]


PYTHON_ERRORS = [
    *COMMON_READ_ERRORS,
    ToolErrorSpec(
        code="TOOL_PYTHON_PARSE_FAILED",
        category="user",
        retryable=False,
        summary="Python 文件无法通过 ast 解析",
    ),
]


def map_read_error(exc: BaseException) -> ToolFailure | None:
    """只返回固定安全文案，不把原始异常文本写入审计结果。"""

    if isinstance(exc, ToolBoundaryError):
        return ToolFailure(
            code="TOOL_PATH_OUTSIDE_SCOPE",
            category="policy",
            message="工具输入路径位于允许范围之外",
        )
    if isinstance(exc, FileNotFoundError):
        return ToolFailure(
            code="TOOL_INPUT_NOT_FOUND",
            category="user",
            message="工具输入文件或目录不存在",
        )
    if isinstance(exc, PermissionError):
        return ToolFailure(
            code="TOOL_PERMISSION_DENIED",
            category="environment",
            message="当前进程无权读取工具输入",
        )
    if isinstance(exc, ValueError):
        return ToolFailure(
            code="TOOL_INPUT_REJECTED",
            category="policy",
            message="工具输入违反受控 Adapter 限制",
        )
    if isinstance(exc, OSError):
        return ToolFailure(
            code="TOOL_IO_ERROR",
            category="environment",
            message="读取工具输入时发生文件系统错误",
        )
    return None


def map_search_error(exc: BaseException) -> ToolFailure | None:
    if isinstance(exc, SearchToolError):
        return ToolFailure(
            code="TOOL_SEARCH_BACKEND_FAILED",
            category="tool",
            retryable=False,
            message="搜索后端执行失败或超时",
        )
    return map_read_error(exc)


def map_python_error(exc: BaseException) -> ToolFailure | None:
    if isinstance(exc, SyntaxError):
        return ToolFailure(
            code="TOOL_PYTHON_PARSE_FAILED",
            category="user",
            message="Python 文件语法无法解析",
        )
    return map_read_error(exc)


def no_declared_error(exc: BaseException) -> ToolFailure | None:
    del exc
    return None


def _register_repo_tools(registry: ToolRegistry) -> None:
    registry.register(
        build_tool_definition(
            name="repo.get_file_tree",
            version=VERSION,
            summary="读取受控 Workspace 中的仓库目录树",
            input_model=RepoTreeInput,
            output_model=RepoTreeOutput,
            handler=adapters.repo_tree_adapter,
            error_mapper=map_read_error,
            effects=[ToolEffect.FILESYSTEM_READ],
            required_capabilities=["filesystem.read.workspace"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.repo.get_file_tree",
            path_scopes=["workspace"],
            declared_errors=COMMON_READ_ERRORS,
        )
    )
    registry.register(
        build_tool_definition(
            name="repo.list_files",
            version=VERSION,
            summary="列出受控 Workspace 中的仓库相对文件路径",
            input_model=RepoListFilesInput,
            output_model=RelativeFilesOutput,
            handler=adapters.repo_list_files_adapter,
            error_mapper=map_read_error,
            effects=[ToolEffect.FILESYSTEM_READ],
            required_capabilities=["filesystem.read.workspace"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.repo.list_files",
            path_scopes=["workspace"],
            declared_errors=COMMON_READ_ERRORS,
        )
    )
    registry.register(
        build_tool_definition(
            name="repo.classify_repo_file",
            version=VERSION,
            summary="按训练、配置、模型和数据集等类别归类仓库文件",
            input_model=RepoPathInput,
            output_model=RepoClassificationOutput,
            handler=adapters.repo_classify_adapter,
            error_mapper=map_read_error,
            effects=[ToolEffect.FILESYSTEM_READ],
            required_capabilities=["filesystem.read.workspace"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.repo.classify_repo_file",
            path_scopes=["workspace"],
            declared_errors=COMMON_READ_ERRORS,
        )
    )


def _register_search_tools(registry: ToolRegistry) -> None:
    registry.register(
        build_tool_definition(
            name="search.search_text",
            version=VERSION,
            summary="在受控 Workspace 中执行有数量和超时限制的文本搜索",
            input_model=SearchTextInput,
            output_model=SearchTextOutput,
            handler=adapters.search_text_adapter,
            error_mapper=map_search_error,
            effects=[
                ToolEffect.FILESYSTEM_READ,
                ToolEffect.PROCESS_SPAWN,
            ],
            required_capabilities=[
                "filesystem.read.workspace",
                "process.spawn.rg",
            ],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.MEDIUM,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=60,
            audit_event="tool.search.search_text",
            path_scopes=["workspace"],
            declared_errors=SEARCH_ERRORS,
        )
    )
    registry.register(
        build_tool_definition(
            name="search.search_keywords",
            version=VERSION,
            summary="在受控 Workspace 中对多个关键词执行去重搜索",
            input_model=SearchKeywordsInput,
            output_model=SearchKeywordsOutput,
            handler=adapters.search_keywords_adapter,
            error_mapper=map_search_error,
            effects=[
                ToolEffect.FILESYSTEM_READ,
                ToolEffect.PROCESS_SPAWN,
            ],
            required_capabilities=[
                "filesystem.read.workspace",
                "process.spawn.rg",
            ],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.MEDIUM,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=60,
            audit_event="tool.search.search_keywords",
            path_scopes=["workspace"],
            declared_errors=SEARCH_ERRORS,
        )
    )


def _register_code_tools(registry: ToolRegistry) -> None:
    registry.register(
        build_tool_definition(
            name="code.read_file_slice",
            version=VERSION,
            summary="读取受控 Workspace 中文件的有限行窗口",
            input_model=CodeSliceInput,
            output_model=CodeSliceOutput,
            handler=adapters.code_slice_adapter,
            error_mapper=map_read_error,
            effects=[ToolEffect.FILESYSTEM_READ],
            required_capabilities=["filesystem.read.workspace"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.code.read_file_slice",
            path_scopes=["workspace"],
            declared_errors=COMMON_READ_ERRORS,
        )
    )
    registry.register(
        build_tool_definition(
            name="code.extract_python_symbols",
            version=VERSION,
            summary="从受控 Workspace 的 Python 文件抽取类和函数符号",
            input_model=PythonSymbolsInput,
            output_model=PythonSymbolsOutput,
            handler=adapters.python_symbols_adapter,
            error_mapper=map_python_error,
            effects=[ToolEffect.FILESYSTEM_READ],
            required_capabilities=["filesystem.read.workspace"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.code.extract_python_symbols",
            path_scopes=["workspace"],
            declared_errors=PYTHON_ERRORS,
        )
    )


def _register_log_tools(registry: ToolRegistry) -> None:
    registry.register(
        build_tool_definition(
            name="log.read_log",
            version=VERSION,
            summary="读取受控 Run 目录中的有限日志尾部",
            input_model=ReadLogInput,
            output_model=TextOutput,
            handler=adapters.read_log_adapter,
            error_mapper=map_read_error,
            effects=[ToolEffect.FILESYSTEM_READ],
            required_capabilities=["filesystem.read.run"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.log.read_log",
            path_scopes=["run"],
            declared_errors=COMMON_READ_ERRORS,
        )
    )
    registry.register(
        build_tool_definition(
            name="log.extract_traceback",
            version=VERSION,
            summary="从日志文本中确定性提取 traceback 或错误行",
            input_model=TextTransformInput,
            output_model=TextOutput,
            handler=adapters.extract_traceback_adapter,
            error_mapper=no_declared_error,
            effects=[ToolEffect.NONE],
            required_capabilities=[],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.DETERMINISTIC,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.log.extract_traceback",
            path_scopes=[],
            declared_errors=[],
        )
    )
    registry.register(
        build_tool_definition(
            name="log.classify_error_heuristic",
            version=VERSION,
            summary="使用确定性规则对 traceback 进行粗粒度分类",
            input_model=TextTransformInput,
            output_model=ErrorClassificationOutput,
            handler=adapters.classify_error_adapter,
            error_mapper=no_declared_error,
            effects=[ToolEffect.NONE],
            required_capabilities=[],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.DETERMINISTIC,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.log.classify_error_heuristic",
            path_scopes=[],
            declared_errors=[],
        )
    )
    registry.register(
        build_tool_definition(
            name="log.extract_repo_traceback_paths",
            version=VERSION,
            summary="从 traceback 中提取经过 Workspace 边界验证的仓库相对路径",
            input_model=TracebackPathsInput,
            output_model=TracebackPathsOutput,
            handler=adapters.traceback_paths_adapter,
            error_mapper=map_read_error,
            effects=[ToolEffect.FILESYSTEM_READ],
            required_capabilities=["filesystem.read.workspace"],
            exposure=ToolExposure.AGENT_READ_ONLY,
            risk_level=ToolRisk.LOW,
            determinism=ToolDeterminism.ENVIRONMENT_DEPENDENT,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.log.extract_repo_traceback_paths",
            path_scopes=["workspace"],
            declared_errors=COMMON_READ_ERRORS,
        )
    )


def _register_policy_tools(registry: ToolRegistry) -> None:
    registry.register(
        build_tool_definition(
            name="risk.assess_action_risk",
            version=VERSION,
            summary="由受信任策略节点对结构化 Action 进行启发式风险分类",
            input_model=ActionRiskInput,
            output_model=ActionRiskOutput,
            handler=adapters.assess_action_risk_adapter,
            error_mapper=no_declared_error,
            effects=[ToolEffect.NONE],
            required_capabilities=[],
            exposure=ToolExposure.TRUSTED_NODE_ONLY,
            risk_level=ToolRisk.MEDIUM,
            determinism=ToolDeterminism.DETERMINISTIC,
            idempotent=True,
            timeout_seconds=None,
            audit_event="tool.risk.assess_action_risk",
            path_scopes=[],
            declared_errors=[],
        )
    )


def build_tool_registry(*, research_bindings=None) -> ToolRegistry:
    registry = ToolRegistry()
    _register_repo_tools(registry)
    _register_search_tools(registry)
    _register_code_tools(registry)
    _register_log_tools(registry)
    _register_policy_tools(registry)
    if research_bindings is not None:
        from app.research_browser.tooling import build_research_tool_definition

        registry.register(build_research_tool_definition(research_bindings))
    return registry
