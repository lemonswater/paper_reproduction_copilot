from __future__ import annotations

from pathlib import Path

from app.tool_contracts import (
    ToolInvocationContext,
    build_tool_registry,
)
from app.tool_contracts.schemas import (
    ToolEffect,
    ToolExposure,
)
from app.tools import search_tools


def _fixture(tmp_path: Path):
    workspace = tmp_path / "workspace"
    repo = workspace / "repo"
    run = tmp_path / "runs" / "run-1"
    repo.mkdir(parents=True)
    run.mkdir(parents=True)
    (repo / "README.md").write_text("PSTNet demo\n", encoding="utf-8")
    (repo / "train.py").write_text(
        "class Model:\n"
        "    pass\n\n"
        "def train():\n"
        "    return 'PSTConv'\n",
        encoding="utf-8",
    )
    (run / "execution.log").write_text(
        "Traceback (most recent call last):\n"
        "ModuleNotFoundError: missing_demo\n",
        encoding="utf-8",
    )
    context = ToolInvocationContext(
        actor="test",
        request_id="catalog-test",
        caller_kind="agent",
        workspace_root=str(workspace),
        run_root=str(run),
        granted_capabilities={
            "filesystem.read.workspace",
            "filesystem.read.run",
            "process.spawn.rg",
        },
    )
    return workspace, repo, run, context


def test_catalog_contains_exact_first_wave_tools() -> None:
    registry = build_tool_registry()

    assert registry.names() == [
        "code.extract_python_symbols",
        "code.read_file_slice",
        "log.classify_error_heuristic",
        "log.extract_repo_traceback_paths",
        "log.extract_traceback",
        "log.read_log",
        "repo.classify_repo_file",
        "repo.get_file_tree",
        "repo.list_files",
        "risk.assess_action_risk",
        "search.search_keywords",
        "search.search_text",
    ]
    assert registry.validate_definitions() == []


def test_agent_read_only_contracts_never_declare_write_effects() -> None:
    registry = build_tool_registry()
    forbidden = {
        ToolEffect.FILESYSTEM_WRITE,
        ToolEffect.PROCESS_CONTROL,
        ToolEffect.NETWORK_WRITE,
        ToolEffect.REPOSITORY_WRITE,
        ToolEffect.ENVIRONMENT_WRITE,
    }

    for name in registry.names():
        contract = registry.get(name).contract
        if contract.exposure == ToolExposure.AGENT_READ_ONLY:
            assert not forbidden.intersection(contract.effects), name


def test_repo_tool_returns_only_relative_files(tmp_path: Path) -> None:
    _, _, _, context = _fixture(tmp_path)
    registry = build_tool_registry()

    result = registry.invoke(
        name="repo.list_files",
        raw_input={
            "repo_path": "repo",
            "suffixes": [".py"],
        },
        context=context,
    )

    assert result.failure is None
    assert result.output == {"files": ["train.py"]}


def test_workspace_path_escape_is_policy_failure(tmp_path: Path) -> None:
    _, _, _, context = _fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    registry = build_tool_registry()

    result = registry.invoke(
        name="repo.list_files",
        raw_input={"repo_path": str(outside)},
        context=context,
    )

    assert result.failure is not None
    assert result.failure.code == "TOOL_PATH_OUTSIDE_SCOPE"


def test_repo_scan_does_not_follow_symlink(tmp_path: Path) -> None:
    workspace, repo, _, context = _fixture(tmp_path)
    outside = tmp_path / "outside-secret"
    outside.mkdir()
    (outside / "secret.py").write_text("TOKEN = 'secret'\n", encoding="utf-8")
    (repo / "linked").symlink_to(outside, target_is_directory=True)
    registry = build_tool_registry()

    result = registry.invoke(
        name="repo.list_files",
        raw_input={"repo_path": str(repo)},
        context=context,
    )

    assert result.failure is None
    assert "linked/secret.py" not in result.output["files"]
    assert str(workspace) not in result.output["files"]


def test_search_contract_uses_deterministic_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _, _, _, context = _fixture(tmp_path)
    monkeypatch.setattr(search_tools.shutil, "which", lambda _: None)
    registry = build_tool_registry()

    result = registry.invoke(
        name="search.search_text",
        raw_input={
            "repo_path": "repo",
            "query": "PSTConv",
            "max_results": 10,
        },
        context=context,
    )

    assert result.failure is None
    assert result.output["matches"] == [
        {
            "file_path": "train.py",
            "line": 5,
            "text": "return 'PSTConv'",
        }
    ]


def test_code_and_log_tools_use_different_roots(tmp_path: Path) -> None:
    _, _, _, context = _fixture(tmp_path)
    registry = build_tool_registry()

    code_result = registry.invoke(
        name="code.extract_python_symbols",
        raw_input={"path": "repo/train.py"},
        context=context,
    )
    log_result = registry.invoke(
        name="log.read_log",
        raw_input={"path": "execution.log", "max_chars": 1000},
        context=context,
    )

    assert code_result.failure is None
    assert code_result.output["symbols"] == [
        {"type": "class", "name": "Model", "line": 1},
        {"type": "function", "name": "train", "line": 4},
    ]
    assert log_result.failure is None
    assert "ModuleNotFoundError" in log_result.output["text"]


def test_risk_tool_is_not_agent_exposed() -> None:
    registry = build_tool_registry()
    definition = registry.get("risk.assess_action_risk")

    assert definition.contract.exposure == ToolExposure.TRUSTED_NODE_ONLY
    denied = registry.invoke(
        name="risk.assess_action_risk",
        raw_input={
            "action": {
                "program": "pip",
                "args": ["install", "demo"],
            }
        },
        context=ToolInvocationContext(
            actor="chat-agent",
            request_id="risk-denied-test",
            caller_kind="agent",
        ),
    )
    assert denied.failure is not None
    assert denied.failure.code == "TOOL_ACCESS_DENIED"

    result = registry.invoke(
        name="risk.assess_action_risk",
        raw_input={
            "action": {
                "program": "pip",
                "args": ["install", "demo"],
            }
        },
        context=ToolInvocationContext(
            actor="trusted-risk-node",
            request_id="risk-test",
            caller_kind="trusted_node",
        ),
    )
    assert result.failure is None
    assert result.output["risk_level"] == "high"
