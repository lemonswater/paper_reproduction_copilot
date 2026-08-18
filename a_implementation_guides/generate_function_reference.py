"""Generate behavior-oriented function references for project functions.

The generated Markdown is intentionally derived from the current Python AST:
- every function/method is listed once in one phase-range volume;
- inputs describe both Python type and domain meaning;
- outputs distinguish IDs, hashes, commands, records, routes and side effects;
- pseudocode preserves branches, loops, try/except, with, raise and return
  boundaries, but groups adjacent statements into plain-language steps instead
  of translating Python syntax line by line.

Run from the repository root with the project Python 3.10 interpreter.
"""

from __future__ import annotations

import ast
import re
import textwrap
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
GUIDES = ROOT / "a_implementation_guides"
AST_MATCH = getattr(ast, "Match", None)

VOLUMES = OrderedDict(
    [
        (
            "phase_00_v7",
            (
                "Python 源码函数参考：基础 00 与 V0-V7",
                "python_source_code_reference_phase_00_v7.md",
            ),
        ),
        (
            "phase_01_16",
            (
                "Python 源码函数参考：Phase 1-16",
                "python_source_code_reference_phase_01_16.md",
            ),
        ),
        (
            "phase_17_29",
            (
                "Python 源码函数参考：Phase 17-29",
                "python_source_code_reference_phase_17_29.md",
            ),
        ),
        (
            "phase_30_39",
            (
                "Python 源码函数参考：Phase 30-39",
                "python_source_code_reference_phase_30_39.md",
            ),
        ),
        (
            "phase_40_46",
            (
                "Python 源码函数参考：Phase 40-46",
                "python_source_code_reference_phase_40_46.md",
            ),
        ),
        (
            "phase_47_56",
            (
                "Python 源码函数参考：Phase 47-56",
                "python_source_code_reference_phase_47_56.md",
            ),
        ),
    ]
)


@dataclass(frozen=True)
class FunctionInfo:
    path: Path
    relative_path: str
    module_doc: str
    qualname: str
    node: ast.FunctionDef | ast.AsyncFunctionDef
    source: str
    phase: str


class FunctionCollector(ast.NodeVisitor):
    def __init__(
        self,
        *,
        path: Path,
        relative_path: str,
        module_doc: str,
        source: str,
        phase: str,
    ) -> None:
        self.path = path
        self.relative_path = relative_path
        self.module_doc = module_doc
        self.source = source
        self.phase = phase
        self.stack: list[str] = []
        self.items: list[FunctionInfo] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        qualname = ".".join([*self.stack, node.name])
        self.items.append(
            FunctionInfo(
                path=self.path,
                relative_path=self.relative_path,
                module_doc=self.module_doc,
                qualname=qualname,
                node=node,
                source=self.source,
                phase=self.phase,
            )
        )
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _test_phase(name: str) -> str:
    lowered = name.lower()
    if "mcp" in lowered or any(
        token in lowered
        for token in (
            "knowledge_",
            "model_routing",
            "research_browser",
            "retrieval_policy",
            "semantic_retrieval",
            "skill_",
            "tool_calling",
        )
    ) or lowered.endswith("_skill.py"):
        return "phase_47_56"
    phase_40 = (
        "project_memory",
        "failure_memory",
        "notification",
        "secret",
        "authority",
        "role_separation",
        "verifier_import",
        "tool_contract",
        "decision_protocol",
        "conversation_decision",
        "chat_decision",
    )
    phase_30 = (
        "chat",
        "comparison",
        "rerun",
        "retention",
        "artifact_delivery",
        "web_static",
        "ui_api",
        "local_input",
        "single_job_export",
    )
    phase_17 = (
        "paper_",
        "pdf_",
        "retrieval",
        "embedding",
        "resource",
        "job_",
        "workspace",
        "worker",
        "postgres",
        "container",
        "oci_",
        "podman",
        "observability",
        "artifact_storage",
        "artifact_publication",
        "published_artifact",
        "interaction",
        "timeline",
        "sse",
    )
    phase_01 = (
        "action_",
        "command_",
        "executor",
        "execution_",
        "repair",
        "patch",
        "run_manifest",
        "preflight",
        "smoke",
        "durable",
        "review_flow",
        "structured_action",
        "stage_error",
        "run_native",
        "input_validation",
        "final_report",
        "fail_to_debug",
    )
    if any(token in lowered for token in phase_40):
        return "phase_40_46"
    if any(token in lowered for token in phase_30):
        return "phase_30_39"
    if any(token in lowered for token in phase_17):
        return "phase_17_29"
    if any(token in lowered for token in phase_01):
        return "phase_01_16"
    return "phase_00_v7"


def classify_phase(relative_path: str) -> str:
    if relative_path == "a_implementation_guides/generate_function_reference.py":
        return "phase_40_46"
    if "mcp" in relative_path.lower() or relative_path == "create_mcp_phase1.py":
        return "phase_47_56"
    if relative_path.startswith("tests/"):
        return _test_phase(relative_path)
    if relative_path.startswith("alembic/"):
        return "phase_17_29"
    if relative_path in {"continue_phase35.py", "install_phase35.py"}:
        return "phase_30_39"

    parts = relative_path.split("/")
    if parts[0] != "app":
        return "phase_00_v7"
    component = parts[1] if len(parts) > 2 else ""
    phase_47_paths = {
        "app/api/knowledge_routes.py",
        "app/api/mcp_gateway_routes.py",
        "app/api/model_routing_routes.py",
        "app/api/research_browser_routes.py",
        "app/prompts/research_browser_prompt.py",
        "app/prompts/tool_calling_prompt.py",
        "app/retrieval/policy.py",
        "app/retrieval/policy_eval.py",
        "app/retrieval/policy_schemas.py",
    }
    if relative_path in phase_47_paths or component in {
        "knowledge_base",
        "mcp_contracts",
        "mcp_export",
        "mcp_gateway",
        "mcp_operations",
        "model_routing",
        "research_browser",
        "skills",
        "tool_calling",
    }:
        return "phase_47_56"
    if component in {
        "authority",
        "failure_memory",
        "notifications",
        "project_memory",
        "secrets",
        "tool_contracts",
    }:
        return "phase_40_46"
    if component in {
        "api",
        "artifact_delivery",
        "chat",
        "comparison",
        "rerun",
        "retention",
        "run_evidence",
    } or relative_path in {"app/service_host.py", "app/web.py"}:
        return "phase_30_39"
    if component in {
        "evaluation",
        "interaction",
        "job_runtime",
        "observability",
        "paper",
        "persistence",
        "resources",
        "retrieval",
        "storage",
        "workspace",
    }:
        return "phase_17_29"
    if component in {"execution", "memory", "nodes"}:
        return "phase_01_16"
    if component == "tools":
        early = {
            "app/tools/code_tools.py",
            "app/tools/repo_tools.py",
            "app/tools/search_tools.py",
        }
        return "phase_00_v7" if relative_path in early else "phase_01_16"
    if component == "prompts":
        return "phase_00_v7"
    if relative_path in {"app/graph.py", "app/command_selection.py"}:
        return "phase_01_16"
    return "phase_00_v7"


def python_paths() -> list[Path]:
    paths: list[Path] = []
    for root_name in ("app", "tests", "alembic"):
        root = ROOT / root_name
        if not root.exists():
            continue
        paths.extend(
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts
        )
    paths.extend(ROOT.glob("*.py"))
    paths.append(GUIDES / "generate_function_reference.py")
    return sorted(set(paths), key=_relative)


def collect_functions() -> tuple[list[FunctionInfo], list[str]]:
    functions: list[FunctionInfo] = []
    errors: list[str] = []
    for path in python_paths():
        relative_path = _relative(path)
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative_path)
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"{relative_path}: {type(exc).__name__}: {exc}")
            continue
        module_doc = (ast.get_docstring(tree, clean=True) or "").split("\n\n", 1)[0]
        collector = FunctionCollector(
            path=path,
            relative_path=relative_path,
            module_doc=module_doc,
            source=source,
            phase=classify_phase(relative_path),
        )
        collector.visit(tree)
        functions.extend(collector.items)
    functions.sort(key=lambda item: (item.phase, item.relative_path, item.node.lineno, item.qualname))
    return functions, errors


def annotation_text(node: ast.AST | None) -> str:
    if node is None:
        return "未显式标注"
    try:
        return ast.unparse(node)
    except Exception:
        return "无法解析的类型标注"


def _default_map(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, ast.AST | None]:
    positional = [*node.args.posonlyargs, *node.args.args]
    defaults: dict[str, ast.AST | None] = {item.arg: None for item in positional}
    if node.args.defaults:
        for argument, value in zip(positional[-len(node.args.defaults):], node.args.defaults):
            defaults[argument.arg] = value
    for argument, value in zip(node.args.kwonlyargs, node.args.kw_defaults):
        defaults[argument.arg] = value
    return defaults


def default_description(node: ast.AST | None) -> str:
    """Explain CLI/default wrappers by their effective default, not constructor syntax."""
    if node is None:
        return "默认未提供"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr in {"Option", "Argument"} and node.args:
            value = node.args[0]
            if isinstance(value, ast.Constant) and value.value is Ellipsis:
                return "命令行必须提供"
            if isinstance(value, ast.Constant) and value.value is None:
                return "未提供时为空"
            return f"命令行默认 {expression(value)}"
    return f"默认 {expression(node)}"


def function_parameters(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    function_name: str | None = None,
) -> list[tuple[str, str, str]]:
    defaults = _default_map(node)
    result: list[tuple[str, str, str]] = []
    for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
        default = defaults.get(argument.arg)
        default_text = ""
        if default is not None:
            default_text = f"；{default_description(default)}"
        result.append(
            (
                argument.arg,
                annotation_text(argument.annotation),
                input_meaning(
                    argument.arg,
                    annotation_text(argument.annotation),
                    function_name=function_name,
                ) + default_text,
            )
        )
    if node.args.vararg is not None:
        result.append(
            (
                f"*{node.args.vararg.arg}",
                annotation_text(node.args.vararg.annotation),
                "额外位置参数序列。",
            )
        )
    if node.args.kwarg is not None:
        result.append(
            (
                f"**{node.args.kwarg.arg}",
                annotation_text(node.args.kwarg.annotation),
                "额外关键字参数映射。",
            )
        )
    return result


def input_meaning(
    name: str,
    type_text: str,
    *,
    function_name: str | None = None,
) -> str:
    lowered = name.lower()
    function_lowered = (function_name or "").lower()
    if lowered == "self":
        return "当前类实例，保存该方法需要的 Repository、配置或运行依赖。"
    if lowered == "cls":
        return "当前类对象，用于类级构造或校验。"
    if lowered in {"index", "selected_index", "command_index"} or lowered.endswith("_index"):
        return "候选集合中的零基索引，用于定位选中项；它不是业务 ID 或内容 Hash。"
    if lowered == "workers":
        return "MCP 调用 worker 数量；用于限制并发处理能力和关闭时的资源回收范围。"
    if lowered == "profile_id":
        return "MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。"
    if lowered == "token_resolver":
        return "MCP 凭据解析器；只在实际连接的短生命周期内解析 Secret，不把 Token 写入 Profile 或报告。"
    if lowered == "surface_sha256":
        return "MCP 能力表面的 SHA-256；用于确认 Tool、Resource、Prompt 目录没有发生未审核漂移。"
    if lowered in {"count", "command_count", "item_count", "retry_count"} or lowered.endswith("_count"):
        return "对象数量或重试次数，用于范围和上限校验，不是进程退出码。"
    if "command" in lowered:
        return "待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。"
    if "sha256" in lowered or lowered.endswith("_hash") or "fingerprint" in lowered:
        return "内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。"
    if lowered.endswith("_id") or lowered in {"id", "thread_id", "run_id", "job_id"}:
        return "稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。"
    if "url" in lowered or "uri" in lowered:
        return "资源地址；进入网络或持久化前仍需策略校验和必要的脱敏。"
    if lowered in {"state", "values"} or lowered.endswith("_state"):
        return "Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。"
    if "request" in lowered or lowered in {"body", "payload"}:
        return "调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。"
    if lowered in {"max_results", "max_files", "max_attempts", "max_retries", "max_per_keyword", "limit", "top_k", "max_bytes"}:
        return "输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。"
    if lowered == "literal":
        return "是否按字面量匹配检索词；为真时不把检索词解释为正则表达式。"
    if lowered == "ignore_case":
        return "是否忽略大小写；为真时统一大小写后再比较源码文本。"
    if lowered in {"content", "value", "data"} or lowered.endswith("_content"):
        return "待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。"
    if lowered in {"normalized"} or lowered.endswith("_text"):
        return "已规范化或待输出的文本；进入持久化或 Prompt 前可能需要限长和脱敏。"
    if "response" in lowered or "result" in lowered or "outcome" in lowered:
        return "前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。"
    if "record" in lowered or "manifest" in lowered or "evidence" in lowered:
        return "持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。"
    if "repository" in lowered or lowered in {"store", "catalog"}:
        return "持久化或目录访问端口；负责读取、CAS 更新或 Artifact 定位。"
    if lowered.endswith("_service") or lowered == "service":
        return "已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。"
    if lowered.endswith("_reader") or lowered == "reader":
        return "只读证据或数据读取端口；负责把外部持久化内容投影为受约束领域输入。"
    if lowered.endswith("_retriever") or lowered == "retriever":
        return "检索服务或端口；返回有界候选及可解释排序信息，不授予执行权限。"
    if lowered.endswith("_profile") or lowered in {"profile", "execution_profile"}:
        return "运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。"
    if lowered in {"fact", "project_fact"} or lowered.endswith("_fact"):
        return "项目事实记录或类型化事实值；包含来源、状态、版本与内容身份。"
    if lowered in {"project", "project_record"}:
        return "项目注册记录；定义稳定项目身份及其不可变锚点。"
    if lowered in {"message", "chat_message"} or lowered.endswith("_message"):
        return "对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。"
    if lowered in {"action", "pending_action", "executable_action"} or lowered.endswith("_action"):
        return "结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。"
    if lowered in {"approval", "approval_record", "decision"} or lowered.endswith("_decision"):
        return "人工审批或决策记录；必须与目标动作 Hash、版本和允许操作一致。"
    if "pytest.monkeypatch" in type_text.lower() or lowered == "monkeypatch":
        return "pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。"
    if "pytest.config" in type_text.lower() or lowered == "config" and "pytest" in type_text.lower():
        return "pytest 会话配置对象，用于读取测试运行参数或注册测试钩子。"
    if lowered in {"cwd", "working_dir", "workdir"}:
        return "命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。"
    if lowered in {"paper_path", "pdf_path", "paper_file"}:
        return "待读取论文或 PDF 文件的路径；函数会据此定位输入文件，不代表文件内容本身。"
    if lowered in {"repo_path", "repository_path", "repo_root"}:
        return "代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。"
    if lowered in {"path", "file_path", "filename", "source_path", "target_path"}:
        return "待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。"
    if lowered.endswith("_path") or lowered in {"file", "directory"}:
        return "文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。"
    if lowered in {"relative_path", "logical_path"}:
        return "相对于仓库或 Artifact 根目录的路径；用于标识文件，不应被当作宿主机绝对路径。"
    if lowered in {"run_dir", "output_dir", "staging_root", "root", "root_dir"}:
        return "运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。"
    if lowered in {"start_line", "end_line", "line", "line_no", "page", "max_depth", "depth"}:
        return "文件行号、页码或遍历深度边界；用于限制读取/扫描范围，不是业务 ID。"
    if lowered in {"name", "env_name", "variable_name"} and "env" in function_lowered:
        return "环境变量名称；用于从运行环境读取配置，而不是环境变量的实际值。"
    if lowered == "name" and "secret" in function_lowered:
        return "Secret Store 中的凭据名称；用于定位密钥元数据，不是凭据明文。"
    if lowered == "use" and "secret" in function_lowered:
        return "凭据用途或绑定场景；用于限制该 Secret 可以被哪个业务动作引用。"
    if lowered == "default":
        return "配置缺失或解析失败时使用的回退值；只有显式允许的场景才会采用它。"
    if lowered in {"source", "kind", "purpose", "component", "backend", "status", "reason"}:
        return "来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。"
    if lowered in {"goal", "experiment_goal", "feedback", "query", "prompt", "text"}:
        return "用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。"
    if lowered == "input":
        return "命令行输入内容或输入文件位置；具体是文本、JSON 路径还是交互值由当前命令决定。"
    if lowered == "route_name":
        return "受限的 Graph 路由函数名称；用于评测或恢复指定流程，不是任意可执行函数名。"
    if lowered == "prefix":
        return "目录树展示用的缩进前缀；只影响输出排版，不改变仓库路径。"
    if lowered == "program":
        return "待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。"
    if lowered == "code":
        return "待解析、执行或断言的代码文本；处理前应处于受控测试/执行边界内。"
    if lowered in {"title", "section_title"}:
        return "论文/文档章节标题；用于建立可检索的章节身份和展示文本。"
    if lowered in {"keyword", "keywords", "suffixes"}:
        if lowered == "suffixes":
            return "允许的文件扩展名集合，例如 `.py`、`.json`；用于筛选文件而不是匹配文件内容。"
        return "用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。"
    if lowered in {"query", "pattern", "regex"}:
        return "待搜索的文本或匹配表达式；是否按字面量/正则解释由调用模式决定。"
    if lowered in {"start", "end", "offset", "cursor", "after", "sequence"}:
        return "分页、文本切片或事件序列位置；用于确定本次读取的起止边界。"
    if type_text == "bytes" or type_text.endswith("bytes"):
        return "原始字节内容；可用于文件、序列化载荷或摘要计算，不应直接当作普通文本记录。"
    if type_text == "Path" or type_text.endswith(".Path"):
        return "已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。"
    if lowered in {"fixture", "case", "_case"}:
        return "测试夹具或评测用例对象；提供场景数据和受控依赖，不是生产业务输入。"
    if lowered in {"job", "run", "manifest", "record", "evidence"}:
        return "任务、运行、Manifest、记录或证据领域对象；携带关联 ID、状态和内容身份。"
    if lowered in {"config", "settings", "options"}:
        return "配置或选项对象；描述运行约束，不等同于执行结果。"
    if lowered in {"idempotency_key"}:
        return "调用方提供的幂等键；重复请求应复用同一结果，而不是再次产生副作用。"
    if lowered in {"schema", "schema_name"}:
        return "结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。"
    if lowered in {"host", "port"}:
        return "服务监听地址或端口；用于绑定本地/网络服务，并受运行环境策略限制。"
    if lowered in {"timeout", "timeout_seconds", "deadline"}:
        return "超时或截止时间限制；用于防止等待/搜索/执行无限持续。"
    if lowered in {"lines", "max_items", "max_results", "max_files", "max_attempts", "max_retries", "max_per_keyword", "limit", "top_k", "max_bytes"}:
        return "输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。"
    if lowered in {"raw", "source_text", "stdout", "stderr"}:
        return "外部读取到的原始文本或进程输出；可能需要截断、规范化或脱敏后才能进入报告。"
    if lowered in {"actor", "created_by", "decided_by", "user_id"}:
        return "执行或决策操作的审计主体标识，不是授权凭证本身。"
    if lowered in {"token", "secret", "password", "api_key"} or "token" in lowered or "secret" in lowered:
        return "敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。"
    if lowered.startswith("expected_"):
        return "调用方观察到的旧身份，用于 stale/CAS 校验，防止覆盖并发更新。"
    if lowered == "is_bold":
        return "当前文本是否使用粗体；用于论文 PDF 标题/正文的视觉层初判。"
    if lowered.startswith("is_") or lowered.startswith("has_") or type_text == "bool":
        return "布尔条件或能力开关，用于控制流程分支。"
    if "error" in lowered or "exception" in lowered or lowered == "exc":
        return "异常、错误记录或错误分类信息，用于失败处理和诊断。"
    if "callback" in lowered or "handler" in lowered or "invoker" in lowered:
        return "可调用依赖；由当前函数在受控位置调用。"
    if lowered in {"clock", "now", "created_at", "updated_at", "expires_at"}:
        return "时间值或可注入时钟，用于排序、过期、租约或可重复测试。"
    if "Callable" in type_text:
        return "可调用依赖；其参数和返回契约由类型标注限定。"
    domain_meaning = _DOMAIN_TERMS.get(lowered)
    if domain_meaning:
        return f"{domain_meaning}；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。"
    if type_text.startswith(("list[", "set[", "tuple[", "Sequence[", "Iterable[")):
        return f"`{type_text}` 元素集合；元素代表的业务对象由参数名 `{name}` 和调用位置确定。"
    if type_text.startswith(("dict[", "Mapping[")) or type_text == "dict":
        return f"名为 `{name}` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。"
    if type_text in {"str", "str | None"}:
        return f"名为 `{name}` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。"
    if type_text in {"int", "int | None", "float", "float | None"}:
        return f"名为 `{name}` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。"
    return f"名为 `{name}` 的 `{type_text}` 领域输入；用于当前函数的业务处理，具体约束见校验分支。"


def inferred_return_type(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    explicit = annotation_text(node.returns)
    if explicit != "未显式标注":
        return explicit
    returns = [item for item in ast.walk(node) if isinstance(item, ast.Return)]
    if not returns or all(item.value is None for item in returns):
        return "None（隐式）"
    return "未显式标注（存在 return）"


def output_meaning(name: str, return_type: str, node: ast.AST) -> str:
    lowered = name.lower()
    if return_type in {"None", "None（隐式）"}:
        return "无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。"
    if lowered == "_env_bool":
        return "返回环境配置的布尔判断结果；`True` 表示配置值属于允许的真值集合，`False` 表示属于允许的假值集合。"
    if lowered == "_uses_mimo_provider":
        return "返回 Provider 判断结果；`True` 表示当前地址或模型名使用 MiMo 兼容配置，`False` 表示不使用。"
    if lowered == "_env_path":
        return "返回可选的文件或目录路径；环境变量为空时返回 `None`。"
    if lowered == "_env_paths":
        return "返回按平台路径分隔符解析后的目录路径元组；至少包含一个有效目录，否则抛出异常。"
    if lowered in {"read_file_slice"}:
        return "返回带原始行号的文件文本切片；范围会被限制在文件实际行数内。"
    if lowered in {"extract_python_symbols"}:
        return "返回按源码行号排序的 Python 类/函数符号清单，每项包含符号类型、名称和起始行号。"
    if lowered in {"get_file_tree"}:
        return "返回经过忽略规则过滤的仓库目录树文本；不会把符号链接或受忽略目录展开进去。"
    if lowered in {"list_files"}:
        return "返回仓库内符合后缀筛选条件的相对文件路径列表，并按稳定顺序排序。"
    if lowered in {"classify_repo_file"}:
        return "返回按 README、训练、评测、配置、模型、数据集和损失等类别组织的相对路径映射。"
    if lowered in {"search_text", "search_keywords", "_python_literal_search"}:
        return "返回受控文本检索结果；结果包含匹配位置/内容等证据，不代表代码已执行。"
    if lowered in {"_parse_rg_json", "_relative_path"}:
        return "返回解析或规范化后的搜索结果/相对路径，供上层建立可追溯证据。"
    if lowered in {"_sha", "_digest"} or "sha256" in lowered:
        return "返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。"
    if lowered in {"_job", "fixture"}:
        return "返回用于测试或读取流程的任务/夹具对象；对象携带稳定 ID、状态和关联 Manifest。"
    if lowered in {"_run_manifest"}:
        return "返回序列化后的运行 Manifest 字节载荷，用于测试完整性校验和证据读取。"
    if lowered.startswith("test_"):
        return "无业务返回值；通过断言或预期异常验证目标行为。"
    if return_type.startswith("未显式标注"):
        return "源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。"
    if "hash" in lowered or "sha256" in lowered or "fingerprint" in lowered:
        return "返回内容身份摘要，通常为 SHA-256 十六进制字符串。"
    if lowered.endswith("_id") or lowered.startswith(("new_id", "build_id", "create_id")):
        return "返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。"
    if lowered.startswith("route_") or "Literal[" in return_type:
        return "返回 Graph 路由标签或受限枚举值，不是任意文本。"
    if return_type == "bool" or lowered.startswith(("is_", "has_", "validate_")) and return_type == "bool":
        return "返回条件判断结果：`True` 表示满足，`False` 表示不满足。"
    if "command" in lowered:
        return "返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。"
    if lowered.startswith(("serialize", "dump", "encode")):
        return "返回序列化或编码后的表示，用于持久化、传输或身份计算；不等于加密授权凭证。"
    if lowered.startswith(("deserialize", "load", "decode", "parse")):
        return "返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。"
    if "Path" in return_type:
        return "返回解析后的文件或目录路径对象。"
    if "Record" in return_type or "Manifest" in return_type or "Evidence" in return_type:
        return "返回经过 Schema 校验的领域记录、Manifest 或证据对象。"
    if "Response" in return_type or "Result" in return_type or "Outcome" in return_type:
        return "返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。"
    if return_type.startswith("list[") or return_type.startswith("set[") or return_type.startswith("tuple["):
        return "返回有界或排序后的对象集合；元素类型由返回标注给出。"
    if return_type.startswith("dict[") or return_type == "dict":
        return "返回键值映射；常用于状态更新、序列化投影或索引结果。"
    if return_type == "str":
        if lowered.startswith(("format", "render", "join", "normalize", "clean")):
            return "返回整理、格式化或规范化后的文本表示。"
        return "返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。"
    if return_type == "int":
        return "返回整数计数、序号、字节数或退出码；具体含义由函数名决定。"
    if return_type == "float":
        return "返回浮点分数、时间或比例值。"
    if "Iterator" in return_type or "Iterable" in return_type or "Generator" in return_type:
        return "返回惰性迭代结果，调用方逐项消费。"
    if isinstance(node, ast.AsyncFunctionDef):
        return f"异步返回 `{return_type}` 结果；调用方必须 `await`。"
    return f"返回 `{return_type}` 类型的领域结果；必要时可能通过异常表示失败。"


def _clip(value: str, limit: int = 1200) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def expression(node: ast.AST | None) -> str:
    if node is None:
        return "空值"
    if isinstance(node, ast.Constant):
        if node.value is Ellipsis:
            return "接口占位（无具体实现）"
        if isinstance(node.value, str):
            if "\n" in node.value or len(node.value) > 120:
                return f"文本（{len(node.value)} 个字符）"
            return repr(node.value)
        if node.value is None:
            return "空值"
        if node.value is True:
            return "真"
        if node.value is False:
            return "假"
        return repr(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{expression(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        return f"{expression(node.value)}[{expression(node.slice)}]"
    if isinstance(node, ast.Slice):
        return f"{expression(node.lower)}:{expression(node.upper)}:{expression(node.step)}"
    if isinstance(node, ast.List):
        return "[" + ", ".join(expression(item) for item in node.elts) + "]"
    if isinstance(node, ast.Tuple):
        return "(" + ", ".join(expression(item) for item in node.elts) + ")"
    if isinstance(node, ast.Set):
        return "{" + ", ".join(expression(item) for item in node.elts) + "}"
    if isinstance(node, ast.Dict):
        pairs = []
        for key, value in zip(node.keys, node.values):
            if key is None:
                pairs.append(f"**{expression(value)}")
            else:
                pairs.append(f"{expression(key)}: {expression(value)}")
        return "{" + ", ".join(pairs) + "}"
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "strip" and not node.args:
            return f"去除 {expression(node.func.value)} 的首尾空白"
        if isinstance(node.func, ast.Name) and node.func.id == "len" and node.args:
            return f"{expression(node.args[0])} 的长度"
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            args = ", ".join(expression(item) for item in node.args)
            return f"从 {expression(node.func.value)} 读取 {args}"
        arguments = [expression(item) for item in node.args]
        arguments.extend(
            f"{item.arg}={expression(item.value)}"
            if item.arg is not None
            else f"**{expression(item.value)}"
            for item in node.keywords
        )
        return _clip(f"调用 {expression(node.func)}({', '.join(arguments)})")
    if isinstance(node, ast.Await):
        return f"等待 {expression(node.value)} 完成"
    if isinstance(node, ast.Compare):
        operators = {
            ast.Eq: "等于",
            ast.NotEq: "不等于",
            ast.Lt: "小于",
            ast.LtE: "小于等于",
            ast.Gt: "大于",
            ast.GtE: "大于等于",
            ast.In: "属于",
            ast.NotIn: "不属于",
            ast.Is: "是",
            ast.IsNot: "不是",
        }
        parts = [expression(node.left)]
        for operator, comparator in zip(node.ops, node.comparators):
            parts.append(operators.get(type(operator), type(operator).__name__))
            parts.append(expression(comparator))
        return " ".join(parts).replace(" 是 空值", " 为空").replace(" 不是 空值", " 不为空")
    if isinstance(node, ast.BoolOp):
        joiner = " 且 " if isinstance(node.op, ast.And) else " 或 "
        return joiner.join(expression(item) for item in node.values)
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            value = expression(node.operand)
            return f"{value} 为空或为假"
        if isinstance(node.op, ast.USub):
            return f"负 {expression(node.operand)}"
    if isinstance(node, ast.BinOp):
        operators = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "×",
            ast.Div: "÷",
            ast.FloorDiv: "整除",
            ast.Mod: "取模",
            ast.Pow: "幂",
            ast.BitOr: "合并",
        }
        return f"{expression(node.left)} {operators.get(type(node.op), type(node.op).__name__)} {expression(node.right)}"
    if isinstance(node, ast.IfExp):
        return f"如果 {expression(node.test)} 则 {expression(node.body)}，否则 {expression(node.orelse)}"
    if isinstance(node, ast.NamedExpr):
        return f"{expression(node.target)} ← {expression(node.value)}"
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
        return _clip("按推导式生成结果：" + ast.unparse(node))
    if isinstance(node, ast.Lambda):
        return _clip("匿名函数：" + ast.unparse(node))
    if isinstance(node, ast.JoinedStr):
        return _clip("格式化文本：" + ast.unparse(node))
    try:
        return _clip(ast.unparse(node))
    except Exception:
        return type(node).__name__


def target(node: ast.AST) -> str:
    if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript, ast.Tuple, ast.List)):
        return expression(node)
    return _clip(ast.unparse(node))


def _raise_text(node: ast.Raise) -> str:
    if node.exc is None:
        return "重新抛出当前异常"
    if isinstance(node.exc, ast.Call):
        error_type = expression(node.exc.func)
        detail = expression(node.exc.args[0]) if node.exc.args else ""
        suffix = f"：{detail}" if detail else ""
        return f"抛出 {error_type}{suffix}"
    return f"抛出 {expression(node.exc)}"


_DOMAIN_TERMS = {
    "self": "当前对象",
    "cls": "当前类型",
    "command": "当前命令",
    "commands": "候选命令集合",
    "command_count": "候选命令的数量",
    "command_index": "候选命令的索引",
    "command_text": "命令文本",
    "run_commands": "候选运行命令集合",
    "max_results": "检索结果数量上限",
    "max_files": "文件数量上限",
    "max_attempts": "尝试次数上限",
    "max_retries": "重试次数上限",
    "max_per_keyword": "每个关键词的结果数量上限",
    "max_command_edit_chars": "命令编辑文本的最大字符数",
    "font_size": "当前文本字号",
    "body_font_size": "正文基准字号",
    "is_bold": "文本是否加粗",
    "raw_pages": "原始 PDF 页面记录集合",
    "canonical_json": "规范化 JSON 文本",
    "numbered": "带行号的源码片段集合",
    "children": "当前目录的子项集合",
    "relative": "仓库相对路径",
    "character": "当前字符",
    "input": "输入内容",
    "prefix": "目录树缩进前缀",
    "program": "待启动程序",
    "code": "待解析或验证的代码",
    "json": "JSON 数据",
    "edit": "编辑文本",
    "edits": "命令修改项集合",
    "chars": "字符数",
    "current": "当前值",
    "first": "第一项",
    "second": "第二项",
    "third": "第三项",
    "previous": "前一项",
    "next": "下一项",
    "existing": "已有记录",
    "resolved": "解析后的值",
    "parsed": "解析后的结果",
    "normalized": "规范化后的文本",
    "lowered": "转为小写的比较文本",
    "cleaned": "清理后的文本或记录",
    "destination": "结果写入目标",
    "receiver": "方法调用接收对象",
    "bound": "边界值",
    "material": "待处理的论文或源码材料",
    "op": "当前业务操作",
    "actual": "实际值",
    "expected": "期望值",
    "output": "输出结果",
    "loaded": "已加载结果",
    "stored": "已存储记录",
    "saved": "已保存结果",
    "created": "已创建记录",
    "updated": "更新后的记录",
    "changed": "发生变化的内容",
    "opened": "已打开资源",
    "closed": "已关闭资源",
    "draft": "草稿对象",
    "parsed_text": "解析后的文本",
    "relative_path": "仓库内相对路径",
    "tmp_path": "临时工作目录路径",
    "media_type": "Artifact 媒体类型",
    "object_key": "存储对象键",
    "object_key": "存储对象键",
    "entries": "记录条目集合",
    "views": "Artifact 视图集合",
    "findings": "诊断发现集合",
    "violations": "约束违反项集合",
    "warnings": "警告集合",
    "checks": "校验项集合",
    "results": "处理结果集合",
    "rows": "数据库记录行集合",
    "cases": "评测用例集合",
    "sources": "证据来源集合",
    "events": "审计事件集合",
    "attempts": "模型尝试记录集合",
    "parameters": "调用参数集合",
    "attributes": "对象属性集合",
    "metadata": "元数据",
    "requirements": "运行要求集合",
    "definition": "契约定义",
    "relation": "领域关系",
    "mapping": "论文-代码映射",
    "binding": "资源绑定记录",
    "assignment": "任务分配记录",
    "reservation": "资源预留记录",
    "lease": "任务租约",
    "claim": "领取声明",
    "identity": "对象身份",
    "policy": "安全策略",
    "registry": "组件注册表",
    "router": "API 路由器",
    "gateway": "外部服务网关",
    "engine": "执行引擎",
    "reader": "证据读取器",
    "retriever": "证据检索器",
    "scanner": "安全扫描器",
    "redactor": "敏感信息脱敏器",
    "builder": "领域对象构造器",
    "runner": "运行调度器",
    "supervisor": "进程监督器",
    "context": "运行上下文",
    "runtime": "运行时环境",
    "telemetry": "运行观测数据",
    "invocation": "工具调用记录",
    "operation": "业务操作",
    "verification": "验证结果",
    "execution": "执行记录",
    "stage": "流水线阶段",
    "stale": "过期的",
    "replayed": "重放的",
    "duplicate": "重复的",
    "successes": "成功结果集合",
    "failures": "失败结果集合",
    "fail": "失败结果",
    "candidate": "当前候选项",
    "candidates": "候选项集合",
    "selected": "选中的候选项",
    "selected_index": "选中候选项的索引",
    "index": "当前候选项的索引",
    "item": "当前处理项",
    "items": "待处理项集合",
    "value": "当前字段值",
    "values": "状态字段集合",
    "raw_value": "原始配置值",
    "normalized": "规范化后的文本",
    "text": "待处理文本",
    "raw": "原始内容",
    "content": "业务内容",
    "data": "待处理数据",
    "source": "数据来源标记",
    "status": "当前状态",
    "reason": "操作原因",
    "kind": "业务类别",
    "purpose": "业务用途",
    "category": "分类标签",
    "type": "对象类型",
    "name": "对象名称",
    "title": "文档或章节标题",
    "description": "对象说明",
    "path": "目标路径",
    "file_path": "目标文件路径",
    "filename": "目标文件名",
    "paper_path": "论文 PDF 路径",
    "pdf_path": "论文 PDF 路径",
    "repo_path": "代码仓库根目录",
    "repository_path": "代码仓库根目录",
    "repo": "代码仓库",
    "repository": "代码仓库",
    "root": "当前扫描根目录",
    "root_dir": "受控根目录",
    "run_root": "运行产物根目录",
    "run_dir": "本次复现运行目录",
    "output_dir": "复现输出目录",
    "staging_root": "暂存工作区根目录",
    "relative_path": "仓库内相对路径",
    "logical_path": "Artifact 逻辑路径",
    "cwd": "命令执行工作目录",
    "working_dir": "命令执行工作目录",
    "workdir": "命令执行工作目录",
    "start_line": "源码起始行号",
    "end_line": "源码结束行号",
    "line": "源码行号",
    "line_no": "源码行号",
    "page": "论文页码",
    "max_depth": "最大遍历深度",
    "depth": "当前遍历深度",
    "start": "读取起点",
    "end": "读取终点",
    "offset": "分页偏移量",
    "cursor": "增量读取游标",
    "after": "增量读取起点",
    "limit": "结果数量上限",
    "max_items": "结果数量上限",
    "top_k": "保留的前 K 个结果数",
    "max_bytes": "读取字节数上限",
    "lines": "待输出的文本行",
    "keywords": "检索关键词集合",
    "keyword": "检索关键词",
    "suffixes": "允许的文件扩展名集合",
    "query": "语义检索问题",
    "pattern": "文本匹配模式",
    "regex": "正则匹配表达式",
    "goal": "复现实验目标",
    "experiment_goal": "复现实验目标",
    "feedback": "用户修正意见",
    "prompt": "发给模型的结构化提示",
    "model": "模型标识",
    "base_url": "Provider 基础地址",
    "backend": "模型或检索后端",
    "profile": "执行环境配置",
    "execution_profile": "执行环境配置",
    "profile_id": "执行环境配置 ID",
    "profile_fingerprint": "执行环境配置指纹",
    "job": "复现任务记录",
    "jobs": "复现任务记录集合",
    "job_id": "复现任务 ID",
    "run_id": "本次复现运行 ID",
    "thread_id": "流程线程 ID",
    "project": "复现项目记录",
    "project_id": "复现项目 ID",
    "resource_id": "输入资源 ID",
    "id": "业务对象 ID",
    "version": "记录版本号",
    "generation": "工作区生成代次",
    "expected_version": "调用方看到的旧版本号",
    "expected_hash": "调用方看到的旧内容 Hash",
    "expected_sha256": "调用方看到的旧 SHA-256",
    "request": "业务请求",
    "payload": "结构化请求载荷",
    "body": "请求正文",
    "request_hash": "请求内容 Hash",
    "request_sha256": "请求内容 SHA-256",
    "idempotency_key": "请求幂等键",
    "hash": "内容 Hash",
    "sha256": "内容 SHA-256",
    "sha256_value": "内容 SHA-256",
    "fingerprint": "内容或环境指纹",
    "digest": "内容摘要",
    "manifest": "运行或工作区 Manifest",
    "record": "领域记录",
    "records": "领域记录集合",
    "row": "数据库记录行",
    "evidence": "可追溯证据记录",
    "report": "复现报告",
    "summary": "阶段摘要",
    "document": "论文解析文档",
    "section": "论文文档章节",
    "sections": "论文文档章节集合",
    "block": "论文原文块",
    "blocks": "论文原文块集合",
    "chunk": "检索文本块",
    "chunks": "检索文本块集合",
    "citation": "论文引用证据",
    "citations": "论文引用证据集合",
    "claim": "论文主张",
    "claims": "论文主张集合",
    "action": "待执行复现动作",
    "pending_action": "待审批复现动作",
    "approval": "人工审批记录",
    "decision": "人工决策结果",
    "proposal": "修复或重跑提案",
    "patch": "代码修复补丁",
    "plan": "实验计划",
    "result": "阶段处理结果",
    "response": "结构化响应",
    "outcome": "执行结论",
    "error": "错误信息",
    "exc": "捕获的异常",
    "issue": "诊断问题",
    "issues": "诊断问题集合",
    "stdout": "进程标准输出",
    "stderr": "进程标准错误",
    "log_path": "运行日志路径",
    "program": "待启动程序",
    "code": "待解析或验证的代码",
    "host": "服务监听地址",
    "port": "服务监听端口",
    "timeout": "等待超时时间",
    "timeout_seconds": "等待超时时间（秒）",
    "retry_count": "已重试次数",
    "count": "对象数量",
    "size": "对象大小",
    "bytes": "字节内容",
    "raw_bytes": "原始字节内容",
    "time": "时间值",
    "now": "当前时间",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "expires_at": "过期时间",
    "actor": "审计主体",
    "token": "敏感令牌",
    "secret": "敏感凭据",
    "config": "运行配置",
    "settings": "应用运行设置",
    "state": "复现流程状态",
    "run_state": "本次运行状态",
    "snapshot": "流程状态快照",
    "graph": "复现流程图",
    "node": "当前流程节点",
    "route": "流程路由结果",
    "service": "领域服务",
    "repository": "持久化仓库",
    "store": "数据存储端口",
    "catalog": "Artifact 目录",
    "connection": "数据库连接",
    "client": "外部服务客户端",
    "worker": "后台复现工作器",
    "transport": "外部资源传输端口",
    "resource": "复现输入资源",
    "resources": "复现输入资源集合",
    "bundle": "代码仓库归档包",
    "workspace": "本次复现工作区",
    "pack": "检索或映射证据包",
    "candidates": "候选结果集合",
    "hits": "检索命中结果",
    "vectors": "文本嵌入向量",
    "embedding": "文本嵌入向量",
    "similarity": "语义相似度",
    "score": "评测或排序分数",
    "category": "评测类别",
    "case": "评测用例",
    "fixture": "测试夹具",
    "observation": "评测观察结果",
    "default": "配置缺失时采用的回退值",
    "message": "面向用户或日志的提示信息",
    "messages": "对话或日志消息集合",
    "question": "论文复现问题或用户问题",
    "questions": "待处理问题集合",
    "url": "外部论文、仓库或服务地址",
    "raw_url": "未经校验的外部资源地址",
    "allowed_hosts": "允许访问的主机集合",
    "method": "论文方法或 HTTP 方法",
    "methods": "论文方法集合",
    "field": "结构化对象字段",
    "fields": "结构化对象字段集合",
    "key": "映射键或对象字段名",
    "keys": "映射键集合",
    "schema": "输入输出 Schema 契约",
    "schemas": "Schema 契约集合",
    "target": "待定位的代码对象或业务目标",
    "targets": "待定位的代码对象集合",
    "reference": "论文或源码引用证据",
    "references": "论文或源码引用证据集合",
    "locator": "源码或文档定位信息",
    "provenance": "证据来源与追溯信息",
    "provenances": "证据来源记录集合",
    "entity": "知识库实体记录",
    "entity_ids": "知识库实体 ID 集合",
    "left": "关系左侧实体或比较左值",
    "right": "关系右侧实体或比较右值",
    "parent": "父级目录或父领域对象",
    "child": "子级目录或子领域对象",
    "children": "子级目录或子领域对象集合",
    "roots": "受控扫描根目录集合",
    "root": "受控扫描根目录",
    "paths": "文件或目录路径集合",
    "path": "文件或目录路径",
    "suffix": "文件扩展名或文本后缀",
    "suffixes": "允许的文件扩展名集合",
    "part": "拆分后的文本或路径片段",
    "parts": "拆分后的文本或路径片段集合",
    "term": "检索词或规范化术语",
    "terms": "检索词或规范化术语集合",
    "token": "模型或命令 token",
    "tokens": "模型或命令 token 集合",
    "args": "命令行或函数位置参数集合",
    "kwargs": "函数关键字参数映射",
    "updates": "待应用的字段更新映射",
    "override": "覆盖默认配置的字段",
    "overrides": "覆盖默认配置的字段映射",
    "batch": "当前批次的记录集合",
    "batches": "待处理批次集合",
    "items": "待处理项集合",
    "texts": "待处理文本集合",
    "links": "外部链接或引用集合",
    "calls": "工具或模型调用记录集合",
    "arguments": "结构化调用参数",
    "response": "结构化响应",
    "responses": "结构化响应集合",
    "detail": "诊断或错误详情",
    "info": "补充诊断信息",
    "traceback": "异常堆栈文本",
    "traceback_paths": "异常堆栈中的源码路径集合",
    "error": "错误信息",
    "errors": "错误信息集合",
    "retryable": "是否允许重试的判断",
    "ok": "处理是否成功的判断",
    "valid": "输入或结果是否有效的判断",
    "strict": "是否启用严格校验的开关",
    "enabled": "功能是否启用的开关",
    "include_candidates": "是否包含候选证据的开关",
    "include_archived": "是否包含已归档记录的开关",
    "include_expired": "是否包含已过期记录的开关",
    "include_terminal": "是否包含已终止运行的开关",
    "unread_only": "是否只读取未读通知的开关",
    "scope": "查询或授权作用域",
    "role": "调用方职责角色",
    "roles": "调用方职责角色集合",
    "producer_node": "产生当前状态的流程节点",
    "terminal": "流程是否已进入终止状态的判断",
    "waiting": "流程是否正在等待的判断",
    "started": "运行是否已经启动的判断",
    "started_at": "运行启动时间",
    "timestamp": "状态事件时间戳",
    "clock": "统一时间来源",
    "environment": "实验执行环境描述",
    "env": "进程环境变量映射",
    "process": "受监督的实验进程",
    "pgid": "实验进程组 ID",
    "exit_code": "实验进程退出码",
    "program": "待启动实验程序",
    "argv": "实验程序命令行参数序列",
    "batch": "当前批次记录集合",
    "ledger": "幂等、租约或审计账本",
    "reservation": "资源预留记录",
    "lease": "任务租约记录",
    "budget": "模型或实验资源预算",
    "usage": "模型或运行资源用量",
    "tokens": "模型 token 用量",
    "pricing": "模型计费配置",
    "quality_tier": "模型质量档位",
    "requested_max_output_tokens": "调用方要求的最大输出 token 数",
    "estimated_input_tokens": "估算的输入 token 数",
    "input_tokens": "实际输入 token 数",
    "output_tokens": "实际输出 token 数",
    "reserved_input_tokens": "预留的输入 token 数",
    "reserved_output_tokens": "预留的输出 token 数",
    "reserved_cost_micro_usd": "预留的微美元成本",
    "provider": "模型服务商配置",
    "providers": "模型服务商配置集合",
    "model": "模型标识或模型配置",
    "runnable": "可调用的模型或 Runnable 对象",
    "invoker": "工具或模型调用器",
    "tools": "受控工具定义集合",
    "tool": "受控工具定义",
    "descriptor": "工具或组件描述信息",
    "descriptors": "工具或组件描述集合",
    "catalog": "模型、工具或 Artifact 目录",
    "marker": "测试或状态标记",
    "monkeypatch": "测试环境修改工具",
    "fixture": "测试夹具",
    "suite": "评测套件",
    "baseline": "评测基线结果",
    "scenario": "复现实验场景",
    "facts": "项目事实记录集合",
    "fact": "项目事实记录",
    "changes": "项目或运行状态变更集合",
    "history": "历史对话或运行记录",
    "interaction": "用户交互记录",
    "delivery": "通知投递记录",
    "sink": "日志或观测数据接收端",
    "sinks": "日志或观测数据接收端集合",
    "audit_sink": "审计事件接收端",
    "trace": "调用链追踪信息",
    "envelope": "事件或请求封装",
    "payload": "结构化请求载荷",
    "patch_bundle": "代码修复补丁包",
    "patches": "代码修复补丁集合",
    "app_and_service": "应用与服务测试对象",
    "service": "领域服务对象",
    "svc": "领域服务对象",
    "reconciler": "状态或资源对账器",
    "resolver": "路径、配置或依赖解析器",
    "projector": "领域记录投影器",
    "component": "系统组件",
    "module": "Python 模块",
    "modules": "Python 模块集合",
    "statements": "源码语句集合",
    "statement": "当前源码语句",
    "doc": "模块或函数文档文本",
    "anchor": "源码或文档锚点",
    "span": "源码位置范围",
    "entity_ids": "知识库实体 ID 集合",
    "alias": "对象别名",
    "alias_rules": "别名解析规则",
    "preferred_paths": "优先使用的路径集合",
    "related_files": "相关源码文件集合",
    "forbidden": "被策略禁止的内容或操作",
    "allowed_uses": "凭据允许的用途集合",
    "used_or_reserved": "已使用或已预留的资源量",
    "older_than": "记录保留期限阈值",
    "after_sequence": "增量读取的起始序号",
    "through_sequence": "增量读取的结束序号",
    "from_statuses": "允许作为迁移起点的状态集合",
    "server": "MCP 服务端实例",
    "server_id": "外部 MCP 服务端稳定标识",
    "endpoint": "MCP 服务端点地址",
    "uri": "MCP 资源或外部研究地址",
    "uri_template": "MCP 资源模板地址",
    "mime_type": "资源媒体类型",
    "surface": "MCP 公开能力表面",
    "surface_sha256": "MCP 能力表面的 SHA-256",
    "snapshot": "MCP 能力快照",
    "candidate": "待审核的 MCP 能力候选",
    "candidate_path": "MCP 候选文件路径",
    "baseline": "已审核的 MCP 能力基线",
    "baseline_path": "MCP 基线文件路径",
    "observations": "MCP Client 观测结果集合",
    "observation": "MCP Client 单次观测结果",
    "profiles": "MCP Client 配置档案集合",
    "profile": "MCP Client 配置档案",
    "profile_id": "MCP Client 配置档案 ID",
    "binding_id": "MCP Tool 绑定 ID",
    "protocol_version": "MCP 协议版本",
    "input_schema": "MCP Tool 输入 Schema",
    "output_schema": "MCP Tool 输出 Schema",
    "annotations": "MCP Tool 行为标注",
    "tool_name": "MCP Tool 名称",
    "resource_name": "MCP Resource 名称",
    "prompt_name": "MCP Prompt 名称",
    "token_resolver": "MCP 凭据解析器",
    "connect_gateway": "是否连接外部 MCP Gateway 的开关",
    "connect": "是否建立 MCP 连接的开关",
    "include_http": "是否包含 Streamable HTTP 观测的开关",
    "mode": "MCP 评测或运行模式",
    "operation": "MCP 业务操作名称",
    "operations": "MCP 业务操作集合",
    "sample_index": "操作采样序号",
    "sample_count": "操作采样数量",
    "samples": "操作采样结果集合",
    "maximum": "允许的最大数量",
    "queue_capacity": "MCP 调用队列容量上限",
    "max_calls_per_minute": "单个调用方每分钟最大调用次数",
    "actor_fingerprint": "调用方身份指纹",
    "function_kwargs": "MCP 操作函数关键字参数",
    "fallback_calls": "备用调用路径集合",
    "request_id": "MCP 请求 ID",
    "metric_operation": "观测指标中的 MCP 操作名",
    "metric_job_id": "观测指标中的复现任务 ID",
    "metric_request_id": "观测指标中的 MCP 请求 ID",
    "report": "MCP 评测或运行报告",
    "runtime_report": "MCP 运行可靠性报告",
    "workers": "MCP 调用 worker 数量",
    "before": "升级前运行报告",
    "after": "升级后运行报告",
    "before_path": "升级前报告路径",
    "after_path": "升级后报告路径",
    "comparison": "SDK 或 MCP 运行升级比较结果",
    "accepted_surface_sha256": "已接受 MCP 能力表面的 SHA-256",
    "reviewed_by": "基线审核人标识",
    "replace": "是否替换现有基线的开关",
    "reason": "基线接受或运行操作原因",
}


_WORD_TERMS = {
    "tmp": "临时",
    "temp": "临时",
    "numbered": "带编号的",
    "children": "子项",
    "relative": "相对",
    "canonical": "规范化",
    "json": "JSON",
    "edit": "编辑",
    "chars": "字符数",
    "character": "字符",
    "current": "当前",
    "first": "第一项",
    "second": "第二项",
    "third": "第三项",
    "previous": "前一项",
    "next": "下一项",
    "existing": "已有",
    "resolved": "解析后的",
    "parsed": "解析后的",
    "actual": "实际",
    "expected": "期望",
    "loaded": "已加载",
    "stored": "已存储",
    "saved": "已保存",
    "created": "已创建",
    "updated": "更新后的",
    "changed": "变化的",
    "opened": "已打开",
    "closed": "已关闭",
    "draft": "草稿",
    "entry": "条目",
    "entries": "条目集合",
    "view": "视图",
    "views": "视图集合",
    "finding": "发现",
    "findings": "发现集合",
    "violation": "违反项",
    "violations": "违反项集合",
    "warning": "警告",
    "warnings": "警告集合",
    "check": "校验",
    "checks": "校验项集合",
    "result": "结果",
    "results": "结果集合",
    "row": "记录行",
    "rows": "记录行集合",
    "case": "用例",
    "cases": "用例集合",
    "source": "来源",
    "sources": "来源集合",
    "event": "事件",
    "events": "事件集合",
    "attempt": "尝试",
    "attempts": "尝试记录集合",
    "parameter": "参数",
    "parameters": "参数集合",
    "attribute": "属性",
    "attributes": "属性集合",
    "metadata": "元数据",
    "requirement": "要求",
    "requirements": "要求集合",
    "definition": "定义",
    "relation": "关系",
    "mapping": "映射",
    "binding": "绑定",
    "assignment": "分配",
    "reservation": "预留",
    "lease": "租约",
    "claim": "领取声明",
    "identity": "身份",
    "policy": "策略",
    "registry": "注册表",
    "router": "路由器",
    "gateway": "网关",
    "engine": "引擎",
    "reader": "读取器",
    "retriever": "检索器",
    "scanner": "扫描器",
    "redactor": "脱敏器",
    "builder": "构造器",
    "runner": "运行器",
    "supervisor": "监督器",
    "context": "上下文",
    "runtime": "运行时",
    "telemetry": "观测数据",
    "invocation": "调用记录",
    "operation": "操作",
    "verification": "验证",
    "execution": "执行",
    "stage": "阶段",
    "stale": "过期",
    "replayed": "重放",
    "duplicate": "重复",
    "success": "成功",
    "successes": "成功结果集合",
    "failure": "失败",
    "failures": "失败结果集合",
    "mode": "模式",
    "level": "等级",
    "rate": "比例",
    "score": "分数",
    "chars": "字符数",
    "bytes": "字节数",
    "media": "媒体",
    "object": "对象",
    "key": "键",
    "keys": "键集合",
    "blob": "Blob 内容",
    "store": "存储",
    "local": "本地",
    "remote": "远程",
    "test": "测试",
    "fake": "测试替身",
    "mock": "模拟对象",
    "provider": "模型服务商",
    "llm": "语言模型",
    "chat": "对话",
    "memory": "记忆",
    "project": "项目",
    "fact": "事实",
    "secret": "凭据",
    "authorization": "授权",
    "authority": "职责权限",
    "tool": "工具",
    "contract": "契约",
    "notification": "通知",
    "failure": "失败",
    "memory": "记忆",
    "paper": "论文",
    "pdf": "PDF",
    "repo": "仓库",
    "repository": "代码仓库",
    "file": "文件",
    "path": "路径",
    "dir": "目录",
    "root": "根目录",
    "run": "运行",
    "job": "任务",
    "project": "项目",
    "resource": "资源",
    "command": "命令",
    "candidate": "候选项",
    "item": "处理项",
    "record": "记录",
    "manifest": "Manifest",
    "evidence": "证据",
    "artifact": "Artifact",
    "content": "内容",
    "text": "文本",
    "value": "值",
    "result": "结果",
    "response": "响应",
    "error": "错误",
    "status": "状态",
    "state": "状态",
    "count": "数量",
    "index": "索引",
    "number": "编号",
    "id": "标识",
    "hash": "Hash",
    "sha": "SHA",
    "version": "版本",
    "profile": "配置",
    "fingerprint": "指纹",
    "query": "查询",
    "keyword": "关键词",
    "section": "章节",
    "block": "原文块",
    "chunk": "文本块",
    "page": "页码",
    "line": "行号",
    "depth": "深度",
    "limit": "上限",
    "time": "时间",
    "date": "日期",
    "source": "来源",
    "kind": "类别",
    "type": "类型",
    "reason": "原因",
    "mode": "模式",
    "key": "键",
    "value": "值",
    "row": "记录行",
    "column": "列",
}


def _domain_term(name: str) -> str:
    """Turn an implementation variable into a short paper-reproduction noun phrase."""
    raw = name.lstrip("*_ ")
    if not raw:
        return "当前处理结果"
    lowered = raw.lower()
    if lowered in _DOMAIN_TERMS:
        return _DOMAIN_TERMS[lowered]
    if lowered.startswith("is_"):
        return f"是否{_domain_term(lowered[3:])}"
    if lowered.startswith("has_"):
        return f"是否已有{_domain_term(lowered[4:])}"
    if lowered.startswith("can_"):
        return f"是否能够{_domain_term(lowered[4:])}"
    if lowered.startswith("no_"):
        return f"没有{_domain_term(lowered[3:])}"
    if lowered.startswith("max_"):
        return f"最大{_domain_term(lowered[4:])}"
    if lowered.startswith("min_"):
        return f"最小{_domain_term(lowered[4:])}"
    for suffix, label in (
        ("_count", "的数量"),
        ("_index", "的索引"),
        ("_id", "的 ID"),
        ("_hash", "的 Hash"),
        ("_sha256", "的 SHA-256"),
        ("_path", "的路径"),
        ("_dir", "的目录"),
        ("_name", "的名称"),
        ("_text", "的文本"),
        ("_bytes", "的字节内容"),
        ("_time", "的时间"),
    ):
        if lowered.endswith(suffix) and len(lowered) > len(suffix):
            return f"{_domain_term(lowered[:-len(suffix)])}{label}"
    words = [part for part in lowered.split("_") if part]
    translated = [_WORD_TERMS.get(word) for word in words]
    known = [item for item in translated if item is not None]
    if not known:
        return "当前处理结果"
    plural_like = lowered.endswith("s") and not lowered.endswith(
        ("_chars", "_bytes", "_status", "_process", "_analysis")
    )
    return "".join(known) + ("集合" if plural_like else "")


def _target_label(node: ast.AST) -> str:
    """Render a variable as a reference in prose, not as an assignment target."""
    if isinstance(node, ast.Name):
        return _domain_term(node.id)
    if isinstance(node, ast.Attribute):
        return _domain_term(node.attr)
    if isinstance(node, ast.Subscript):
        return f"{_target_label(node.value)}中的对应字段"
    if isinstance(node, (ast.Tuple, ast.List)):
        return "多个解包结果"
    return "当前处理结果"


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return "辅助操作"


def _subject_label(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return _domain_term(node.id)
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Call):
            return f"前一步操作返回对象的{_domain_term(node.attr)}"
        return _domain_term(node.attr)
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Call):
            return "前一步操作返回对象中的对应字段"
        if isinstance(node.value, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            if isinstance(node.slice, ast.Slice):
                return "新构造集合中按范围取出的部分"
            return "新构造集合中的指定项"
        return f"{_subject_label(node.value)}中的对应字段"
    if isinstance(node, ast.Call):
        name = _call_name(node)
        if name == "len" and node.args:
            return f"{_subject_label(node.args[0])} 的长度"
        if name == "ord" and node.args:
            return f"{_subject_label(node.args[0])} 对应的 ASCII/Unicode 编码"
        return f"辅助操作“{_call_effect(node)}”的结果"
    return "当前输入内容"


def _call_effect(node: ast.Call) -> str:
    """Describe the purpose of a call without reproducing its Python syntax."""
    name = _call_name(node)
    normalized_name = name.lstrip("_")
    receiver = expression(node.func.value) if isinstance(node.func, ast.Attribute) else ""
    receiver_label = _subject_label(node.func.value) if isinstance(node.func, ast.Attribute) else "当前输入"
    if name == "getenv":
        return "从运行环境读取配置项；若未设置则使用调用方提供的默认值"
    if name == "Path":
        return "把外部位置解析为文件系统路径对象"
    if name[:1].isupper():
        return f"构造 `{name}` 结构化领域对象"
    if normalized_name in {"utc_now", "clock", "now"}:
        return "读取当前时间，作为状态变更的统一时间戳"
    if name in {"expanduser", "resolve", "absolute"}:
        return f"将{receiver_label}规范化为受控的绝对路径"
    if name in {"read_text", "read_bytes"}:
        return f"读取{receiver_label}中的文件内容"
    if name in {"write_text", "write_bytes"}:
        return f"将处理结果写入{receiver_label}指定的文件"
    if name in {"mkdir", "makedirs"}:
        return f"创建{receiver_label}对应的目录"
    if name in {"iterdir", "rglob", "glob"}:
        return f"枚举{receiver_label}下符合范围的文件系统项"
    if name in {"relative_to", "as_posix"}:
        return f"把{receiver_label}转换为稳定的仓库相对路径表示"
    if name in {"is_dir", "is_file", "is_symlink", "exists"}:
        return f"检查{receiver_label}的文件系统属性"
    if name in {"strip", "lower", "casefold", "splitlines", "split"}:
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            return f"{_call_effect(node.func.value)}，再对返回文本执行规范化或拆分"
        return f"对{receiver_label}中的文本执行规范化或拆分"
    if name in {"startswith", "endswith", "contains"}:
        return f"检查{receiver_label}是否满足文本匹配条件"
    if name in {"append", "extend", "add", "update", "setdefault"}:
        if node.args:
            item = _subject_label(node.args[0]) if isinstance(
                node.args[0], (ast.Name, ast.Attribute, ast.Subscript)
            ) else "新的处理结果"
            return f"把{item}追加或合并到{receiver_label}"
        return f"把新结果追加或合并到{receiver_label}"
    if name == "pop":
        return f"从{receiver_label}取出并移除最后一项"
    if name in {"sort", "sorted"}:
        return "按稳定规则整理结果顺序"
    if name in {"model_copy", "model_dump", "model_validate", "dict"}:
        return "复制、序列化或校验结构化领域对象"
    if name in {"get", "get_state", "get_workspace_manifest", "list_views"}:
        return f"从{receiver_label}读取所需的状态或领域记录"
    if name in {"print", "write"}:
        return "向终端或输出流写出当前结果/诊断信息"
    if name in {"commit", "flush"}:
        return f"提交{receiver_label}中已完成的数据变更"
    if name == "rollback":
        return f"回滚{receiver_label}中未完成的数据变更"
    if name in {"close", "aclose"}:
        return f"关闭{receiver_label}并释放相关资源"
    if name in {"dumps", "encode"}:
        return "将结构化内容序列化或编码为可传输表示"
    if name in {"loads", "decode"}:
        return "将外部表示解析为结构化内容"
    if name == "sha256" or name == "hexdigest":
        return "计算输入内容的 SHA-256 身份摘要"
    if name == "parse" and receiver == "ast":
        return "将 Python 源码解析为抽象语法树"
    if name == "walk" and receiver == "ast":
        return "遍历抽象语法树中的所有节点"
    if name == "generic_visit":
        return "继续遍历当前 AST 节点内部的子节点"
    if name in {"any", "all"}:
        quantifier = "是否存在" if name == "any" else "是否全部"
        if node.args and isinstance(node.args[0], ast.GeneratorExp):
            generator = node.args[0]
            if generator.generators:
                source = _iterable_effect(generator.generators[0].iter)
                condition = _condition_effect(generator.elt)
                return f"检查{source}中{quantifier}满足“{condition}”的项"
        return f"检查集合中{quantifier}满足条件的项"
    if name in {"len", "max", "min", "bool", "isinstance", "issubclass"}:
        return "计算数量、边界或类型判断结果"
    if name in {"tuple", "list", "set", "dict", "SimpleNamespace"}:
        return "构造临时集合、映射或轻量领域对象"
    if name in {"sorted", "enumerate", "range", "list"}:
        return "准备有序、带序号或有界的迭代输入"
    if name in {"build_graph", "run_context_node", "final_report_node", "run_manifest_node"}:
        return f"执行 `{name}` 对应的阶段流程并取得状态结果"
    if name in {"invoke", "ainvoke"}:
        return f"调用{receiver_label}完成模型或 Runnable 处理"
    if name in {"execute", "executemany", "scalar", "scalars"}:
        return f"通过{receiver_label}执行数据查询或命令"
    if normalized_name.startswith(("build_", "create_")):
        return f"调用 `{name}` 组装当前阶段需要的领域对象"
    if normalized_name.startswith(("get_", "load_", "read_", "find_", "list_", "search_", "query_")):
        return f"调用 `{name}` 读取或查询当前阶段需要的数据"
    if normalized_name.startswith(("parse_", "resolve_", "normalize_", "redact_", "format_")):
        return f"调用 `{name}` 解析、规范化或转换当前输入"
    if normalized_name.startswith(("save_", "write_", "put_", "insert_", "update_", "delete_")):
        return f"调用 `{name}` 持久化或更新当前领域数据"
    if normalized_name.startswith(("compute_", "hash_", "fingerprint_")) or "sha256" in normalized_name:
        return f"调用 `{name}` 计算内容身份、分数或派生结果"
    if normalized_name.startswith(("has_", "is_", "check_", "validate_")):
        return f"调用 `{name}` 校验当前输入或状态"
    return f"调用 `{name}` 完成该函数的一项辅助处理"


def _semantic_expression(node: ast.AST) -> str:
    """Render expressions used in conditions without exposing local variable names."""
    if isinstance(node, ast.Name):
        return _domain_term(node.id)
    if isinstance(node, (ast.Attribute, ast.Subscript, ast.Call)):
        return _subject_label(node)
    if isinstance(node, ast.Constant):
        return expression(node)
    if isinstance(node, ast.BinOp):
        operators = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "×",
            ast.Div: "÷",
            ast.FloorDiv: "整除",
            ast.Mod: "取模",
            ast.Pow: "幂",
            ast.BitOr: "合并",
        }
        operator = operators.get(type(node.op), "组合")
        return f"{_semantic_expression(node.left)} {operator} {_semantic_expression(node.right)}"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return f"负 {_semantic_expression(node.operand)}"
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        opening, closing = {
            ast.Tuple: ("(", ")"),
            ast.List: ("[", "]"),
            ast.Set: ("{", "}"),
        }[type(node)]
        return opening + ", ".join(_semantic_expression(item) for item in node.elts) + closing
    if isinstance(node, ast.Dict):
        fields: list[str] = []
        for key, value in zip(node.keys, node.values):
            key_text = expression(key) if key is not None else "动态字段"
            fields.append(f"{key_text}: {_semantic_expression(value)}")
        return "{" + ", ".join(fields) + "}"
    return expression(node)


def _value_effect(node: ast.AST | None) -> str:
    if node is None:
        return "空值"
    if isinstance(node, ast.Call):
        return _call_effect(node)
    if isinstance(node, ast.Await):
        return f"等待异步操作完成并取得结果（{_value_effect(node.value)}）"
    if isinstance(node, ast.Dict):
        return "按字段初始化键值映射"
    if isinstance(node, ast.List):
        return "初始化顺序集合"
    if isinstance(node, ast.Set):
        return "初始化去重集合"
    if isinstance(node, ast.Tuple):
        return "组合多个值形成元组"
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
        return "遍历输入、按条件筛选并生成新的集合"
    if isinstance(node, ast.JoinedStr):
        return "根据字段和固定文本生成格式化文本"
    if isinstance(node, ast.BinOp):
        return "组合或计算已有值"
    if isinstance(node, ast.IfExp):
        return "根据条件从两个候选结果中选择一个"
    if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
        return f"读取{_subject_label(node)}的当前值"
    if isinstance(node, ast.Constant):
        return "使用固定配置或常量值"
    return "计算当前表达式的结果"


def _condition_effect(node: ast.AST) -> str:
    if isinstance(node, ast.Compare):
        operators = {
            ast.Eq: "等于",
            ast.NotEq: "不等于",
            ast.Lt: "小于",
            ast.LtE: "不大于",
            ast.Gt: "大于",
            ast.GtE: "不小于",
            ast.In: "属于",
            ast.NotIn: "不属于",
            ast.Is: "是",
            ast.IsNot: "不是",
        }
        left = _subject_label(node.left)
        parts = [left]
        for operator, comparator in zip(node.ops, node.comparators):
            relation = operators.get(type(operator), "满足比较关系")
            if isinstance(operator, (ast.Is, ast.IsNot)) and isinstance(comparator, ast.Constant) and comparator.value is None:
                parts.append("为空" if isinstance(operator, ast.Is) else "不为空")
            else:
                if isinstance(comparator, (ast.Name, ast.Attribute, ast.Subscript, ast.Call)):
                    right = _subject_label(comparator)
                else:
                    right = _semantic_expression(comparator)
                parts.extend([relation, right])
        return "".join(parts)
    if isinstance(node, ast.BoolOp):
        joiner = " 且 " if isinstance(node.op, ast.And) else " 或 "
        return f"{joiner.join(_condition_effect(item) for item in node.values)}"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        if isinstance(node.operand, ast.Name):
            return f"{_domain_term(node.operand.id)}为空或为假"
        if isinstance(node.operand, ast.Call):
            return f"“{_call_effect(node.operand)}”后未得到肯定结果"
        return f"“{_condition_effect(node.operand)}”不成立"
    if isinstance(node, ast.Call):
        name = _call_name(node)
        if name in {"any", "all"} and node.args and isinstance(node.args[0], ast.GeneratorExp):
            generator = node.args[0]
            if generator.generators:
                source = _iterable_effect(generator.generators[0].iter)
                condition = _condition_effect(generator.elt)
                quantifier = "存在" if name == "any" else "每一项都"
                return f"{source}中{quantifier}满足“{condition}”的项"
        return f"“{_call_effect(node)}”后得到肯定结果"
    if isinstance(node, ast.Name):
        return f"{_domain_term(node.id)}有值或为真"
    if isinstance(node, (ast.Attribute, ast.Subscript)):
        return f"{_subject_label(node)}有值或为真"
    return f"当前条件（{_value_effect(node)}）成立"


def _iterable_effect(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        name = _call_name(node)
        if name == "range":
            return "限定范围内的序列"
        if name == "enumerate":
            return "带顺序编号的输入集合"
        if name == "walk" and isinstance(node.func, ast.Attribute) and node.func.attr == "walk":
            return "语法树节点集合"
        return f"辅助操作产生的可迭代结果（{_call_effect(node)}）"
    if isinstance(node, ast.Name):
        return f"由{_domain_term(node.id)}组成的集合或迭代器"
    return "当前可迭代输入"


def _return_effect(node: ast.AST | None) -> str:
    if node is None:
        return "结束当前函数，不返回业务值"
    if isinstance(node, ast.Call):
        effect = _call_effect(node)
        if effect.startswith("构造 `"):
            return effect.replace("构造 `", "构造并返回 `", 1)
        return f"{effect}，并返回处理结果"
    if isinstance(node, ast.Dict):
        keys = [
            str(item.value)
            for item in node.keys
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ]
        if keys:
            shown = "、".join(f"`{item}`" for item in keys[:8])
            suffix = " 等字段" if len(keys) > 8 else " 字段"
            return f"返回包含 {shown}{suffix}的结构化映射"
        return "返回当前构造的结构化映射"
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return "返回当前构造的顺序或去重集合"
    if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
        subject = _subject_label(node)
        if subject in {"当前处理结果", "当前输入内容"}:
            return "返回前一步处理得到的结果"
        return f"返回{subject}的当前值"
    if isinstance(node, ast.IfExp):
        return "返回按条件选出的结果"
    if isinstance(node, ast.Compare):
        return "返回比较判断结果"
    if isinstance(node, ast.BoolOp):
        return "返回组合判断结果"
    if isinstance(node, ast.Constant):
        return f"返回固定值 `{expression(node)}`"
    return "返回当前计算得到的结果"


def _raise_effect(node: ast.Raise) -> str:
    if node.exc is None:
        return "重新抛出当前异常，保持原始失败信息"
    if isinstance(node.exc, ast.Call):
        error_type = expression(node.exc.func)
        return f"拒绝继续处理并抛出 `{error_type}`，向调用方报告输入或运行失败"
    return "拒绝继续处理并抛出当前异常对象"


def _is_docstring_statement(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _is_flow_statement(statement: ast.stmt) -> bool:
    """Return whether a statement owns a nested control-flow body."""
    flow_types = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
    )
    if AST_MATCH is not None:
        flow_types += (AST_MATCH,)
    return isinstance(statement, flow_types)


def _assignment_targets(statement: ast.Assign | ast.AnnAssign) -> list[ast.AST]:
    if isinstance(statement, ast.Assign):
        return list(statement.targets)
    return [statement.target]


def _empty_collection_kind(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.List) and not node.elts:
        return "空列表"
    if isinstance(node, ast.Dict) and not node.keys:
        return "空映射"
    if isinstance(node, ast.Set) and not node.elts:
        return "空去重集合"
    if isinstance(node, ast.Call) and not node.args and not node.keywords:
        name = _call_name(node)
        return {"list": "空列表", "dict": "空映射", "set": "空去重集合"}.get(name)
    return None


def _field_copy(statement: ast.stmt) -> tuple[str, str] | None:
    """Recognize ``self.field = parameter`` so adjacent copies can be explained together."""
    if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
        return None
    targets = _assignment_targets(statement)
    value = statement.value
    if len(targets) != 1 or not isinstance(value, ast.Name):
        return None
    destination = targets[0]
    if not (
        isinstance(destination, ast.Attribute)
        and isinstance(destination.value, ast.Name)
        and destination.value.id in {"self", "cls"}
    ):
        return None
    return value.id, expression(destination)


def _simple_statement_clause(statement: ast.stmt) -> str:
    """Translate one leaf statement; callers combine adjacent clauses into a step."""
    if isinstance(statement, (ast.Assign, ast.AnnAssign)):
        targets = _assignment_targets(statement)
        labels = "、".join(_target_label(item) for item in targets)
        if statement.value is None:
            return f"声明 {labels}，暂不赋值"
        empty_kind = _empty_collection_kind(statement.value)
        if empty_kind is not None:
            return f"把 {labels} 初始化为{empty_kind}，用来收集后续结果"
        if isinstance(statement.value, ast.Call):
            if (
                _call_name(statement.value) == "strip"
                and isinstance(statement.value.func, ast.Attribute)
            ):
                source = _subject_label(statement.value.func.value)
                return f"去除{source}的首尾空白，并把规范化后的文本记为 {labels}"
            result_label = "该调用返回的结果" if labels == "当前处理结果" else labels
            return f"{_call_effect(statement.value)}，并把结果记为 {result_label}"
        if isinstance(statement.value, ast.Await):
            return f"等待异步处理完成，并把结果记为 {labels}"
        if isinstance(statement.value, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            return f"遍历并筛选输入，将整理后的结果保存为 {labels}"
        if isinstance(statement.value, (ast.Name, ast.Attribute, ast.Subscript)):
            result_label = "后续步骤使用的结果" if labels == "当前处理结果" else labels
            return f"读取{_subject_label(statement.value)}，并保存为 {result_label}"
        return f"计算{_value_effect(statement.value)}，并保存为 {labels}"
    if isinstance(statement, ast.AugAssign):
        return f"将新的计算结果累加或合并到{_target_label(statement.target)}"
    if isinstance(statement, ast.Expr):
        if isinstance(statement.value, ast.Call):
            return _call_effect(statement.value)
        if isinstance(statement.value, ast.Await):
            return "等待异步处理完成，并提交它产生的状态变更"
        if isinstance(statement.value, ast.Constant) and statement.value.value is Ellipsis:
            return "仅声明接口契约，这里没有具体实现"
        return "完成当前表达式对应的校验或状态操作"
    if isinstance(statement, ast.Return):
        return _return_effect(statement.value)
    if isinstance(statement, ast.Raise):
        return _raise_effect(statement)
    if isinstance(statement, ast.Assert):
        detail = f"，失败时附带断言说明" if statement.msg else ""
        return f"断言{_condition_effect(statement.test)}{detail}；不满足就终止当前测试或流程"
    if isinstance(statement, ast.Break):
        return "立即结束当前循环"
    if isinstance(statement, ast.Continue):
        return "跳过本轮剩余处理，直接进入下一轮"
    if isinstance(statement, ast.Pass):
        return "不执行额外操作"
    if isinstance(statement, (ast.Import, ast.ImportFrom)):
        return "加载这一步需要的外部依赖"
    if isinstance(statement, (ast.Global, ast.Nonlocal)):
        return f"声明后续会读写外层作用域中的 {'、'.join(_domain_term(item) for item in statement.names)}"
    if isinstance(statement, ast.Delete):
        labels = "、".join(_target_label(item) for item in statement.targets)
        return f"移除{labels}中的当前内容"
    return "完成当前语句对应的状态或控制操作"


def _simple_clauses(statements: list[ast.stmt]) -> list[str]:
    """Collapse repeated setup statements while preserving their original order."""
    clauses: list[str] = []
    index = 0
    while index < len(statements):
        copied_fields: list[tuple[str, str]] = []
        while index < len(statements):
            copied = _field_copy(statements[index])
            if copied is None:
                break
            copied_fields.append(copied)
            index += 1
        if copied_fields:
            same_name = all(source == destination.rsplit(".", 1)[-1] for source, destination in copied_fields)
            if same_name:
                names = "、".join(_domain_term(source) for source, _ in copied_fields)
                clauses.append(f"把传入的 {names} 分别保存到同名实例字段")
            else:
                pairs = "、".join(
                    f"{_domain_term(source)} → {_domain_term(destination.rsplit('.', 1)[-1])}"
                    for source, destination in copied_fields
                )
                clauses.append(f"把传入参数保存到实例字段（{pairs}）")
            continue

        collection_kind: str | None = None
        collection_targets: list[str] = []
        collection_index = index
        while collection_index < len(statements):
            current = statements[collection_index]
            if not isinstance(current, (ast.Assign, ast.AnnAssign)):
                break
            current_kind = _empty_collection_kind(current.value)
            targets = _assignment_targets(current)
            if current_kind is None or len(targets) != 1:
                break
            if collection_kind is not None and current_kind != collection_kind:
                break
            collection_kind = current_kind
            collection_targets.append(_target_label(targets[0]))
            collection_index += 1
        if collection_targets:
            clauses.append(
                f"将 {'、'.join(collection_targets)} 初始化为{collection_kind}，用来收集后续结果"
            )
            index = collection_index
            continue

        clauses.append(_simple_statement_clause(statements[index]))
        index += 1
    return clauses


def _join_clauses(clauses: list[str]) -> str:
    return "；".join(item.rstrip("。；") for item in clauses) + "。"


def _render_simple_group(statements: list[ast.stmt], indent: int) -> list[str]:
    """Render several leaf statements as a few readable paragraphs."""
    prefix = "    " * indent
    clauses = _simple_clauses(statements)
    lines: list[str] = []
    paragraph: list[str] = []
    for clause in clauses:
        candidate = [*paragraph, clause]
        # 连续小步骤可以合并，但不让一个段落长到难以扫读。
        if paragraph and (len(candidate) > 4 or len(_join_clauses(candidate)) > 280):
            lines.append(prefix + _join_clauses(paragraph))
            paragraph = [clause]
        else:
            paragraph = candidate
    if paragraph:
        lines.append(prefix + _join_clauses(paragraph))
    return lines


def _inline_body(statements: list[ast.stmt]) -> str | None:
    meaningful = [item for item in statements if not _is_docstring_statement(item)]
    if not meaningful or any(_is_flow_statement(item) for item in meaningful):
        return None
    clauses = _simple_clauses(meaningful)
    if len(clauses) > 4:
        return None
    summary = "；".join(item.rstrip("。；") for item in clauses)
    if len(summary) > 280:
        return None
    return summary


def _long_bool_condition(node: ast.AST) -> tuple[str, list[str]] | None:
    """Split a large and/or condition into a reader-friendly numbered checklist."""
    if not isinstance(node, ast.BoolOp) or len(node.values) < 3:
        return None
    condition = _condition_effect(node)
    if len(condition) <= 260:
        return None
    mode = "任意一项成立" if isinstance(node.op, ast.Or) else "全部成立"
    return mode, [_condition_effect(item) for item in node.values]


def pseudocode_statements(statements: list[ast.stmt], indent: int = 0) -> list[str]:
    """Explain code as grouped, plain-language steps while preserving control flow."""
    lines: list[str] = []
    prefix = "    " * indent
    index = 0
    while index < len(statements):
        statement = statements[index]
        if _is_docstring_statement(statement):
            index += 1
            continue
        if not _is_flow_statement(statement):
            end = index + 1
            while end < len(statements):
                candidate = statements[end]
                if _is_docstring_statement(candidate):
                    end += 1
                    continue
                if _is_flow_statement(candidate):
                    break
                end += 1
            meaningful = [item for item in statements[index:end] if not _is_docstring_statement(item)]
            lines.extend(_render_simple_group(meaningful, indent))
            index = end
            continue

        if isinstance(statement, ast.If):
            body = _inline_body(statement.body)
            alternative = _inline_body(statement.orelse) if statement.orelse else None
            condition = _condition_effect(statement.test)
            long_condition = _long_bool_condition(statement.test)
            if long_condition is not None:
                mode, conditions = long_condition
                lines.append(f"{prefix}如果以下条件{mode}：")
                lines.extend(
                    f"{prefix}    {number}. {item}。"
                    for number, item in enumerate(conditions, start=1)
                )
                if body is not None and (not statement.orelse or alternative is not None):
                    sentence = f"{prefix}满足上述组合条件时，{body}"
                    if alternative is not None:
                        sentence += f"；否则{alternative}"
                    lines.append(sentence + "。")
                else:
                    lines.append(f"{prefix}满足上述组合条件时：")
                    lines.extend(pseudocode_statements(statement.body, indent + 1))
                    if statement.orelse:
                        lines.append(f"{prefix}否则：")
                        lines.extend(pseudocode_statements(statement.orelse, indent + 1))
            elif body is not None and (not statement.orelse or alternative is not None):
                sentence = f"{prefix}如果{condition}，就{body}"
                if alternative is not None:
                    sentence += f"；否则{alternative}"
                lines.append(sentence + "。")
            else:
                lines.append(f"{prefix}如果{condition}：")
                lines.extend(pseudocode_statements(statement.body, indent + 1) or [f"{prefix}    不执行额外操作。"])
                if statement.orelse:
                    lines.append(f"{prefix}否则：")
                    lines.extend(pseudocode_statements(statement.orelse, indent + 1))
        elif isinstance(statement, (ast.For, ast.AsyncFor)):
            await_word = "异步" if isinstance(statement, ast.AsyncFor) else ""
            body = _inline_body(statement.body)
            header = (
                f"{await_word}遍历{_iterable_effect(statement.iter)}，"
                f"每次把当前项记为{_target_label(statement.target)}"
            )
            if body is not None:
                lines.append(f"{prefix}{header}，然后{body}。")
            else:
                lines.append(f"{prefix}{header}：")
                lines.extend(pseudocode_statements(statement.body, indent + 1) or [f"{prefix}    不执行额外操作。"])
            if statement.orelse:
                lines.append(f"{prefix}如果循环正常完成而没有提前 `break`：")
                lines.extend(pseudocode_statements(statement.orelse, indent + 1))
        elif isinstance(statement, ast.While):
            body = _inline_body(statement.body)
            condition = _condition_effect(statement.test)
            if body is not None:
                lines.append(f"{prefix}只要{condition}，就重复{body}。")
            else:
                lines.append(f"{prefix}只要{condition}，就重复以下处理：")
                lines.extend(pseudocode_statements(statement.body, indent + 1) or [f"{prefix}    不执行额外操作。"])
            if statement.orelse:
                lines.append(f"{prefix}循环正常结束后：")
                lines.extend(pseudocode_statements(statement.orelse, indent + 1))
        elif isinstance(statement, (ast.With, ast.AsyncWith)):
            async_word = "异步" if isinstance(statement, ast.AsyncWith) else ""
            contexts = []
            for item in statement.items:
                context = _value_effect(item.context_expr)
                if item.optional_vars is not None:
                    context += f"，并把上下文资源交给{_target_label(item.optional_vars)}"
                contexts.append(context)
            body = _inline_body(statement.body)
            context_text = "、".join(contexts)
            if body is not None:
                lines.append(
                    f"{prefix}在{async_word}上下文“{context_text}”中{body}，退出时自动清理资源。"
                )
            else:
                lines.append(f"{prefix}进入{async_word}上下文“{context_text}”，退出时自动清理资源：")
                lines.extend(pseudocode_statements(statement.body, indent + 1))
        elif isinstance(statement, ast.Try):
            lines.append(f"{prefix}先尝试完成以下处理：")
            lines.extend(pseudocode_statements(statement.body, indent + 1))
            for handler in statement.handlers:
                error_type = expression(handler.type) if handler.type is not None else "任意异常"
                suffix = "并把异常保存为捕获的异常对象" if handler.name else ""
                lines.append(f"{prefix}如果出现 `{error_type}`{suffix}：")
                lines.extend(pseudocode_statements(handler.body, indent + 1))
            if statement.orelse:
                lines.append(f"{prefix}如果主处理没有异常：")
                lines.extend(pseudocode_statements(statement.orelse, indent + 1))
            if statement.finalbody:
                lines.append(f"{prefix}无论成功还是失败，最后都要：")
                lines.extend(pseudocode_statements(statement.finalbody, indent + 1))
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.append(f"{prefix}定义内部辅助函数 `{statement.name}`，供当前函数在后续步骤中调用。")
        elif isinstance(statement, ast.ClassDef):
            lines.append(f"{prefix}定义内部类型 `{statement.name}`，用于组织当前函数的临时逻辑。")
        elif AST_MATCH is not None and isinstance(statement, AST_MATCH):
            lines.append(f"{prefix}根据当前输入的结构选择一条处理路径：")
            for case in statement.cases:
                guard = f"，且{_condition_effect(case.guard)}" if case.guard is not None else ""
                lines.append(f"{prefix}    当输入匹配该模式{guard}：")
                lines.extend(pseudocode_statements(case.body, indent + 2))
        index += 1
    return lines


def _reproduction_scenario(info: FunctionInfo) -> str:
    path = info.relative_path.lower()
    if path.startswith("tests/"):
        if "mcp" in path:
            return "论文复现 Agent 的 MCP 互操作、只读证据导出和运行可靠性验证阶段"
        if "knowledge_" in path:
            return "跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段"
        if "model_routing" in path:
            return "论文复现模型路由、Provider 能力治理、成本预算和调用降级的验证阶段"
        if "research_browser" in path:
            return "受限研究型浏览器的来源采集、内容提取、引用合成和安全边界验证阶段"
        if "tool_calling" in path:
            return "论文复现 Agent 有界 Tool Calling、Schema 校验、证据回写和编排闭环的验证阶段"
        if "skill_" in path or path.endswith("_skill.py"):
            return "论文复现 Agent Skill/Plugin 的清单加载、权限隔离、运行时和调试日志验证阶段"
        if "retrieval_policy" in path or "semantic_retrieval" in path:
            return "论文方法检索质量优化、候选排序策略和离线检索评测阶段"
        if "eval" in path or "golden" in path or "scorer" in path:
            return "论文复现的离线评测与回归检查阶段"
        if "paper" in path or "method" in path or "mapping" in path:
            return "论文阅读、方法抽取和论文-代码映射阶段的自动化验证"
        if "execution" in path or "executor" in path or "process" in path:
            return "复现实验命令的受控执行、监督和失败恢复阶段"
        if "secret" in path or "safety" in path or "authority" in path:
            return "论文复现系统的安全、权限和敏感信息隔离阶段"
        return "论文复现系统的自动化测试和边界验证阶段"
    if "mcp" in path:
        return "围绕论文复现证据、运行状态和报告建立受控 MCP 互操作与可靠性闭环的阶段"
    if "/knowledge_base/" in path or path.endswith("/knowledge_routes.py"):
        return "跨论文知识库的事实沉淀、来源追踪、关系审核和复现证据复用阶段"
    if "/model_routing/" in path or path.endswith("/model_routing_routes.py"):
        return "为论文复现选择模型 Provider、执行成本预算、能力治理和失败降级的阶段"
    if "/research_browser/" in path or path.endswith("/research_browser_routes.py") or path.endswith("/research_browser_prompt.py"):
        return "在受限网络和来源策略下采集研究资料、提取证据并生成可引用复现上下文的阶段"
    if "/skills/" in path:
        return "装载和运行论文复现 Agent Skill/Plugin，并实施清单、权限和调试日志约束的阶段"
    if "/tool_calling/" in path or path.endswith("/tool_calling_prompt.py"):
        return "在 Schema、预算和只读证据边界内编排论文复现 Agent 的有界 Tool Calling 阶段"
    if path.endswith("/retrieval/policy.py") or path.endswith("/retrieval/policy_eval.py") or path.endswith("/retrieval/policy_schemas.py"):
        return "优化论文方法检索策略、候选排序和离线评测质量的阶段"
    if "/paper/" in path or path.startswith("app/paper/") or "/prompts/" in path:
        return "论文解析、章节理解和方法证据提取阶段"
    if "/retrieval/" in path or "/tools/search" in path:
        return "根据论文方法描述检索代码证据、建立候选映射的阶段"
    if "command_selection" in path:
        return "从论文和仓库证据中选择、校验并固定可复现实验命令的阶段"
    if "/tools/" in path:
        return "为论文阅读、源码分析和复现实验提供受控工具调用的阶段"
    if path.endswith("/schemas.py") or "/schemas/" in path:
        return "约束论文复现请求、运行状态、证据和结果结构的契约校验阶段"
    if path.endswith("/model.py"):
        return "调用模型服务完成论文内容理解、代码语义分析或向量化的阶段"
    if "/execution/" in path or "/nodes/executor" in path or "/nodes/preflight" in path:
        return "把实验计划转换为可审计命令并在受控环境中执行的阶段"
    if "/nodes/" in path or path.endswith("/graph.py") or path.endswith("/main.py"):
        return "编排论文复现流水线、传递阶段状态并生成运行产物的阶段"
    if "/workspace/" in path or "/storage/" in path or "/persistence/" in path:
        return "隔离每次论文复现运行、保存 Artifact 并校验可复现证据的阶段"
    if "/resources/" in path:
        return "准备论文 PDF、代码仓库或检查点等复现输入资源的阶段"
    if "/evaluation/" in path:
        return "运行离线/Provider 评测、比较基线并形成质量报告的阶段"
    if "/chat/" in path or "/comparison/" in path or "/rerun/" in path:
        return "围绕复现运行进行问答、结果比较和受控重跑的阶段"
    if "/secrets/" in path or "/authority/" in path or "/tool_contracts/" in path:
        return "论文复现系统的凭证保护、职责隔离和工具契约治理阶段"
    if "/failure_memory/" in path or "/project_memory/" in path or "/notifications/" in path:
        return "沉淀复现失败诊断、项目事实并向用户反馈运行进展的阶段"
    return "论文复现系统的基础配置、数据转换或公共支撑阶段"


def _function_action(name: str) -> str:
    lowered = name.lower().lstrip("_")
    if lowered.startswith("test_"):
        return "构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束"
    if lowered.startswith(("observe_", "inspect_mcp", "run_contract_eval", "run_runtime", "compare_runtime", "compare_upgrade", "stack_doctor", "generate_candidate", "accept_candidate")):
        return "发现、观测或评估 MCP 的公开 Tool/Resource/Prompt 契约，比较协议、Schema、延迟和失败结果，并为论文复现系统保留可审核的基线或运行报告"
    if lowered.startswith(("call_pinned_tool", "search_external", "build_mcp", "register_mcp", "connect")):
        return "在固定 MCP Policy、Schema Pin、调用预算和只读职责边界内连接或调用外部能力，并把返回内容转换为可追溯的复现证据"
    if lowered.endswith("_command") or lowered == "command":
        return "作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户"
    if lowered.endswith("_node") or lowered == "node":
        return "作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点"
    if lowered.startswith(("env_", "_env_")):
        return "读取并规范化复现系统的环境配置，给论文解析、模型调用或执行环境选择提供稳定默认值"
    if lowered in {"__init__", "__enter__", "__exit__", "__call__"}:
        return "初始化或管理当前复现组件所需的依赖、资源和生命周期状态"
    if lowered.startswith(("route_", "select_", "choose_")):
        return "根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径"
    if lowered.startswith(("validate_", "check_", "verify_", "assess_", "require_")):
        return "检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转"
    if lowered.startswith(("parse_", "read_", "extract_", "index_", "section", "normalize_", "reduce_")):
        return "读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据"
    if lowered.startswith(("search_", "retrieve_", "rank_", "query_", "chunk_", "embed_")):
        return "围绕论文方法语义检索、切分和排序代码证据，为后续方法映射与实验规划提供候选结果"
    if lowered.startswith(("map_", "classify_", "match_", "resolve_")):
        return "把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据"
    if lowered.startswith(("build_", "create_", "construct_", "make_")):
        return "装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求"
    if lowered.startswith(("run_", "execute_", "submit_", "resume_", "wait_", "cancel_", "worker")):
        return "驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因"
    if lowered.startswith(("save_", "write_", "put_", "insert_", "publish_", "persist_", "update_", "delete_", "revoke_")):
        return "在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact"
    if lowered.startswith(("hash", "digest", "fingerprint", "compute_")):
        return "计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测"
    if lowered.startswith(("render_", "format_", "serialize_", "dump_", "encode_")):
        return "把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示"
    if lowered.startswith(("load_", "get_", "list_", "find_", "open_")):
        return "从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态"
    return "围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调"


def _function_input_summary(info: FunctionInfo) -> str:
    parameters = [item for item in function_parameters(info.node, function_name=info.node.name) if item[0] not in {"self", "cls"}]
    if not parameters:
        return "当前运行配置、模块状态和已注入依赖"
    terms = [_domain_term(item[0]) for item in parameters[:4]]
    suffix = "等输入" if len(parameters) > 4 else ""
    return "、".join(terms) + suffix


def _function_output_summary(info: FunctionInfo) -> str:
    return_type = inferred_return_type(info.node)
    if return_type in {"None", "None（隐式）"}:
        return "更新流程状态、写入运行产物或通过异常报告不可复现原因"
    if return_type == "bool":
        return "一个可用于路由、校验或安全判断的布尔结果"
    if "Path" in return_type:
        return "一个经过边界校验的文件或目录路径"
    if return_type.startswith("list[") or return_type.startswith("tuple[") or return_type.startswith("set["):
        return "有界、排序或带证据来源的结果集合"
    if return_type.startswith("dict[") or return_type == "dict":
        return "包含复现状态、索引或序列化字段的结构化映射"
    if "str" == return_type:
        return "文本、路径、状态标签或内容身份摘要"
    if "float" in return_type:
        return "用于排序或质量评估的分数、比例或相似度"
    if "int" in return_type:
        return "数量、序号、字节数或版本等整数结果"
    if "Response" in return_type or "Result" in return_type or "Record" in return_type or "Manifest" in return_type:
        return "经过 Schema 校验、可继续审计的领域结果对象"
    return f"标注为 `{return_type}` 的领域结果"


def function_description(info: FunctionInfo) -> str:
    doc = ast.get_docstring(info.node, clean=True)
    doc_text = " ".join(doc.split("\n\n", 1)[0].split()) if doc else ""
    doc_text = doc_text.rstrip("。.!！?？")
    scenario = _reproduction_scenario(info)
    action = _function_action(info.node.name)
    inputs = _function_input_summary(info)
    output = _function_output_summary(info)
    if doc_text:
        return f"在{scenario}中，{doc_text}。该函数接收{inputs}，用于{action}，最终{output}。"
    return f"在{scenario}中，该函数接收{inputs}，用于{action}，最终{output}。"


def signature(info: FunctionInfo) -> str:
    node = info.node
    try:
        raw = ast.get_source_segment(info.source, node) or ""
        first = raw.splitlines()[0].strip()
        if first.startswith(("def ", "async def ")) and first.endswith(":"):
            return first[:-1]
    except Exception:
        pass
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    parameters = []
    for name, type_text, _ in function_parameters(node, function_name=node.name):
        parameters.append(f"{name}: {type_text}")
    return f"{prefix} {node.name}({', '.join(parameters)}) -> {inferred_return_type(node)}"


def render_function(info: FunctionInfo, *, heading_level: int = 4) -> str:
    hashes = "#" * heading_level
    return_type = inferred_return_type(info.node)
    lines = [
        f"{hashes} `{info.qualname}`",
        "",
        f"- **源码**：`{info.relative_path}:{info.node.lineno}`",
        f"- **签名**：`{signature(info)}`",
        f"- **作用**：{function_description(info)}",
        "",
        "**输入**",
        "",
    ]
    parameters = function_parameters(info.node, function_name=info.node.name)
    if parameters:
        lines.extend(
            [
                "| 参数 | Python 类型 | 语义 |",
                "|---|---|---|",
            ]
        )
        for name, type_text, meaning in parameters:
            lines.append(f"| `{name}` | `{type_text}` | {meaning} |")
    else:
        lines.append("无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。")
    lines.extend(
        [
            "",
            "**输出**",
            "",
            f"- **Python 类型**：`{return_type}`",
            f"- **语义**：{output_meaning(info.node.name, return_type, info.node)}",
            "",
            "**伪代码**",
            "",
            "```text",
        ]
    )
    body = pseudocode_statements(info.node.body)
    lines.extend(body or ["不执行额外操作", "返回，无业务值"])
    lines.extend(["```", ""])
    return "\n".join(lines)


def render_volume(
    phase: str,
    title: str,
    items: list[FunctionInfo],
    errors: list[str],
) -> str:
    by_file: dict[str, list[FunctionInfo]] = defaultdict(list)
    for item in items:
        by_file[item.relative_path].append(item)
    lines = [
        f"# {title}",
        "",
        f"> 自动同步日期：{date.today().isoformat()}",
        f"> 覆盖文件：{len(by_file)}；函数/方法：{len(items)}。",
        "> 本文由当前 Python AST 生成；伪代码保留控制流和失败边界，但会把相邻语句合并为通俗的逻辑步骤。",
        "> 阶段归类按文件的主要职责完成；跨阶段持续修改的文件只进入一个主分册，源码行号是最终依据。",
        "",
        "## 阅读约定",
        "",
        "- 伪代码按“一段逻辑做什么”组织；连续初始化、校验或字段更新会合并成一句或一段。",
        "- 简单的 `if`、`for` 和 `with` 会直接概括成完整句子；有嵌套分支或提前返回时才使用缩进展开。",
        "- 变量名只用来标识数据保存在哪里；文字是为了解释意图，不是可直接运行的 Python 代码。",
        "- 输入表中的路径、ID、Hash、命令、状态和领域记录分别表示不同的业务对象，不能互换。",
        "- “抛出异常”对应真实 `raise`，调用方不会收到正常返回值。",
        "- Hash/fingerprint 表示内容身份，不是加密后的业务正文，也不是授权凭证。",
        "- Command 表示命令文本或结构化命令；只有 Executor 路径才可能真正执行。",
        "- Protocol 中只有 `...` 的函数会显示为“接口占位（无具体实现）”，它声明契约而不是具体实现。",
        "",
        "## 文件索引",
        "",
    ]
    for relative_path, functions in sorted(by_file.items()):
        anchor = re.sub(r"[^a-z0-9]+", "-", relative_path.lower()).strip("-")
        lines.append(f"- [`{relative_path}`](#{anchor})：{len(functions)} 个函数/方法")
    lines.extend(["", "## 逐函数参考", ""])
    for relative_path, functions in sorted(by_file.items()):
        module_doc = functions[0].module_doc
        lines.extend(
            [
                f"### `{relative_path}`",
                "",
                f"**模块作用**：{module_doc or '以源码中的函数、类和常量共同实现该模块职责。'}",
                "",
            ]
        )
        for function in functions:
            lines.append(render_function(function))
    if errors:
        lines.extend(
            [
                "## 未解析文件",
                "",
                *[f"- `{item}`" for item in errors],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


PHASE46_MARKER_BEGIN = "<!-- BEGIN GENERATED PHASE46 FUNCTION REFERENCE -->"
PHASE46_MARKER_END = "<!-- END GENERATED PHASE46 FUNCTION REFERENCE -->"


def phase46_relevant(info: FunctionInfo) -> bool:
    path = info.relative_path
    if path.startswith("app/project_memory/"):
        return True
    if path == "app/api/project_memory_routes.py":
        return True
    if path.startswith("tests/") and "project_memory" in path:
        return True
    if path == "tests/helpers/project_memory.py":
        return True
    if path in {
        "app/api/app.py",
        "app/api/errors.py",
        "app/chat/context.py",
        "app/chat/memory.py",
        "app/chat/schemas.py",
        "app/retention/factory.py",
        "app/retention/service.py",
    }:
        segment = ast.get_source_segment(info.source, info.node) or ""
        return "project_memory" in segment or "project_fact" in segment or "phase46" in segment.lower()
    return False


def render_phase46_appendix(items: list[FunctionInfo]) -> str:
    selected = [item for item in items if phase46_relevant(item)]
    by_file: dict[str, list[FunctionInfo]] = defaultdict(list)
    for item in selected:
        by_file[item.relative_path].append(item)
    lines = [
        PHASE46_MARKER_BEGIN,
        "## 三十一、Phase 46 每个函数的伪代码与输入输出",
        "",
        "> **本节类型：实际源码函数参考，不修改代码。**",
        ">",
        "> 本附录以当前已经实现的 Phase 46 源码和专项测试为准，而不是以早期教程草案为准。",
        "> 输入表会区分命令、ID、路径、Hash、记录、请求和审计主体；伪代码保留真实 AST 的",
        "> 分支、循环、异常、事务和返回顺序，但将连续语句合并为人能直接阅读的逻辑步骤。",
        "> Protocol 方法的函数体只有 `...`，所以伪代码显示“接口占位（无具体实现）”；它表示接口契约，不是遗漏实现。",
        "",
        f"本附录覆盖 `{len(by_file)}` 个相关 Python 文件、`{len(selected)}` 个函数/方法。",
        "",
    ]
    for relative_path, functions in sorted(by_file.items()):
        lines.extend([f"### `{relative_path}`", ""])
        for function in functions:
            lines.append(render_function(function, heading_level=4))
    lines.extend([PHASE46_MARKER_END, ""])
    return "\n".join(lines)


def update_phase46_guide(items: list[FunctionInfo]) -> None:
    path = GUIDES / "57_phase_46_project_scoped_long_term_memory_and_revocable_fact_governance.md"
    text = path.read_text(encoding="utf-8")
    appendix = render_phase46_appendix(items)
    # 删除上一版只链接到未创建 57a-57d 文件的占位附录，避免重复章节。
    legacy = re.compile(
        r"\n---\n\n## 三十一、函数伪代码与输入输出附录.*?"
        r"(?=\n---\n\n<!-- BEGIN GENERATED PHASE46 FUNCTION REFERENCE -->)",
        re.S,
    )
    text = legacy.sub("\n", text)
    if PHASE46_MARKER_BEGIN in text and PHASE46_MARKER_END in text:
        pattern = re.compile(
            re.escape(PHASE46_MARKER_BEGIN)
            + r".*?"
            + re.escape(PHASE46_MARKER_END)
            + r"\n?",
            re.S,
        )
        text = pattern.sub(appendix, text)
    else:
        text = text.rstrip() + "\n\n---\n\n" + appendix
    path.write_text(text, encoding="utf-8")


def main() -> None:
    items, errors = collect_functions()
    grouped: dict[str, list[FunctionInfo]] = defaultdict(list)
    for item in items:
        grouped[item.phase].append(item)
    for phase, (title, filename) in VOLUMES.items():
        output = render_volume(phase, title, grouped[phase], errors)
        (GUIDES / filename).write_text(output, encoding="utf-8")
    update_phase46_guide(items)

    counts = ", ".join(
        f"{phase}={len(grouped[phase])}" for phase in VOLUMES
    )
    print(f"generated {len(items)} functions: {counts}")
    if errors:
        print(f"unparsed files: {len(errors)}")


if __name__ == "__main__":
    main()
