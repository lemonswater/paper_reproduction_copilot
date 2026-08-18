from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.tool_contracts.registry import ToolRegistry
from app.tool_contracts.schemas import ContractIssue


class ModuleDisposition(str, Enum):
    CATALOGED = "cataloged"
    PIPELINE_INTERNAL = "pipeline_internal"
    SECURITY_BOUNDARY = "security_boundary"


@dataclass(frozen=True)
class ToolModulePolicy:
    disposition: ModuleDisposition
    reason: str
    # 只有 CATALOGED 模块需要逐个绑定公开函数与 Contract name。
    exported_functions: dict[str, str] = field(default_factory=dict)


TOOL_MODULE_POLICIES: dict[str, ToolModulePolicy] = {
    "action_tools": ToolModulePolicy(
        ModuleDisposition.SECURITY_BOUNDARY,
        "Action 构造和 Approval Hash 由 Graph 安全协议控制",
    ),
    "artifact_tools": ToolModulePolicy(
        ModuleDisposition.PIPELINE_INTERNAL,
        "Run-native Artifact 内部持久化 helper",
    ),
    "code_tools": ToolModulePolicy(
        ModuleDisposition.CATALOGED,
        "受控代码读取能力",
        {
            "read_file_slice": "code.read_file_slice",
            "extract_python_symbols": "code.extract_python_symbols",
        },
    ),
    "error_tools": ToolModulePolicy(
        ModuleDisposition.PIPELINE_INTERNAL,
        "Graph 错误边界和 StageError 持久化",
    ),
    "exec_tools": ToolModulePolicy(
        ModuleDisposition.SECURITY_BOUNDARY,
        "真实执行必须经过 Action Hash、Policy 和 Approval",
    ),
    "log_tools": ToolModulePolicy(
        ModuleDisposition.CATALOGED,
        "受控日志读取和确定性诊断 helper",
        {
            "read_log": "log.read_log",
            "extract_traceback": "log.extract_traceback",
            "classify_error_heuristic": "log.classify_error_heuristic",
            "extract_repo_traceback_paths": "log.extract_repo_traceback_paths",
        },
    ),
    "mapping_target_tools": ToolModulePolicy(
        ModuleDisposition.PIPELINE_INTERNAL,
        "论文代码映射内部 reducer",
    ),
    "paper_tools": ToolModulePolicy(
        ModuleDisposition.PIPELINE_INTERNAL,
        "论文入口由 Paper Reader 与输入验证节点控制",
    ),
    "patch_journal_tools": ToolModulePolicy(
        ModuleDisposition.SECURITY_BOUNDARY,
        "Patch Journal 只服务于受控修复事务",
    ),
    "patch_tools": ToolModulePolicy(
        ModuleDisposition.SECURITY_BOUNDARY,
        "补丁构建、验证和应用必须经过两次审批",
    ),
    "preflight_tools": ToolModulePolicy(
        ModuleDisposition.SECURITY_BOUNDARY,
        "预检会启动受监管 probe，不向 Agent 直接暴露",
    ),
    "repair_tools": ToolModulePolicy(
        ModuleDisposition.SECURITY_BOUNDARY,
        "修复动作只能生成 Proposal 并重新审批",
    ),
    "repo_tools": ToolModulePolicy(
        ModuleDisposition.CATALOGED,
        "受控仓库结构读取能力",
        {
            "get_file_tree": "repo.get_file_tree",
            "list_files": "repo.list_files",
            "classify_repo_file": "repo.classify_repo_file",
        },
    ),
    "repository_lock_tools": ToolModulePolicy(
        ModuleDisposition.SECURITY_BOUNDARY,
        "仓库锁是并发写安全边界",
    ),
    "safe_shell_tools": ToolModulePolicy(
        ModuleDisposition.CATALOGED,
        "只向受信任 Risk Node 暴露风险分类",
        {
            "assess_action_risk": "risk.assess_action_risk",
        },
    ),
    "search_tools": ToolModulePolicy(
        ModuleDisposition.CATALOGED,
        "受控 Workspace 搜索能力",
        {
            "search_text": "search.search_text",
            "search_keywords": "search.search_keywords",
        },
    ),
    "smoke_test_tools": ToolModulePolicy(
        ModuleDisposition.SECURITY_BOUNDARY,
        "Smoke Action 仍属于执行与审批协议",
    ),
    "structured_output_tools": ToolModulePolicy(
        ModuleDisposition.PIPELINE_INTERNAL,
        "Provider structured-output transport 与重试 helper",
    ),
}


def _public_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


def validate_tool_inventory(
    registry: ToolRegistry,
    *,
    tools_dir: Path | None = None,
) -> tuple[list[ContractIssue], int]:
    root = tools_dir or (
        Path(__file__).resolve().parents[1] / "tools"
    )
    discovered = {
        path.stem: path
        for path in root.glob("*.py")
        if path.name != "__init__.py" and not path.name.startswith("_")
    }
    issues: list[ContractIssue] = []

    for module_name in sorted(discovered.keys() - TOOL_MODULE_POLICIES.keys()):
        issues.append(
            ContractIssue(
                code="TOOL_MODULE_NOT_IN_INVENTORY",
                target=module_name,
                message="新工具模块尚未声明 disposition",
            )
        )

    for module_name in sorted(TOOL_MODULE_POLICIES.keys() - discovered.keys()):
        issues.append(
            ContractIssue(
                code="TOOL_INVENTORY_MODULE_MISSING",
                target=module_name,
                message="Inventory 声明的工具模块不存在",
            )
        )

    expected_contracts: set[str] = set()
    for module_name, policy in TOOL_MODULE_POLICIES.items():
        if policy.disposition != ModuleDisposition.CATALOGED:
            if policy.exported_functions:
                issues.append(
                    ContractIssue(
                        code="INTERNAL_MODULE_EXPORTS_CONTRACTS",
                        target=module_name,
                        message="非 cataloged 模块不能声明 exported_functions",
                    )
                )
            continue
        path = discovered.get(module_name)
        if path is None:
            continue

        actual_functions = _public_functions(path)
        expected_functions = set(policy.exported_functions)
        for function_name in sorted(actual_functions - expected_functions):
            issues.append(
                ContractIssue(
                    code="PUBLIC_TOOL_FUNCTION_NOT_REVIEWED",
                    target=f"{module_name}.{function_name}",
                    message="cataloged 模块新增公开函数但未建立处置记录",
                )
            )
        for function_name in sorted(expected_functions - actual_functions):
            issues.append(
                ContractIssue(
                    code="INVENTORY_FUNCTION_MISSING",
                    target=f"{module_name}.{function_name}",
                    message="Inventory 声明的公开函数不存在",
                )
            )

        for function_name, contract_name in policy.exported_functions.items():
            if contract_name in expected_contracts:
                issues.append(
                    ContractIssue(
                        code="DUPLICATE_INVENTORY_CONTRACT",
                        target=contract_name,
                        message="一个 Contract 被多个函数重复绑定",
                    )
                )
            expected_contracts.add(contract_name)

    actual_contracts = set(registry.names())
    for name in sorted(expected_contracts - actual_contracts):
        issues.append(
            ContractIssue(
                code="INVENTORY_CONTRACT_NOT_REGISTERED",
                target=name,
                message="Inventory 引用的 Contract 未注册",
            )
        )
    for name in sorted(actual_contracts - expected_contracts):
        issues.append(
            ContractIssue(
                code="REGISTERED_CONTRACT_NOT_IN_INVENTORY",
                target=name,
                message="已注册 Contract 没有来源函数处置记录",
            )
        )

    return issues, len(discovered)
