from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_research_browser_has_no_process_execution_imports() -> None:
    forbidden = (
        "import subprocess",
        "from subprocess",
        "os.system(",
        "shell=True",
    )
    for path in (ROOT / "app" / "research_browser").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{path}: {marker}"


def test_research_browser_never_calls_resource_approval() -> None:
    forbidden = (
        ".approve(",
        ".reject(",
        ".run_worker(",
        ".materialize(",
    )
    for path in (ROOT / "app" / "research_browser").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{path}: {marker}"


def test_research_browser_has_no_shell_execution() -> None:
    forbidden = (
        "os.popen(",
        "os.exec",
        "os.spawn",
        "pty.spawn",
    )
    for path in (ROOT / "app" / "research_browser").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{path}: {marker}"


def test_research_tool_has_network_read_effect_only() -> None:
    from app.research_browser.tooling import build_research_tool_definition
    from app.tool_contracts.schemas import ToolEffect
    from app.research_browser.tooling import ResearchToolBindings

    class FakeCollector:
        def collect(self, request):
            from tests.research_browser_helpers import evidence_draft
            return evidence_draft()

    tool = build_research_tool_definition(
        ResearchToolBindings(collector=FakeCollector())
    )
    assert ToolEffect.NETWORK_READ in tool.contract.effects
    assert "network.read.research" in tool.contract.required_capabilities
    assert tool.contract.exposure.value == "agent_read_only"


def test_research_skill_only_declares_collect_tool() -> None:
    import json

    manifest_path = ROOT / "agent_skills" / "restricted_web_research" / "skill.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tool_names = [t["name"] for t in manifest["required_tools"]]
    assert tool_names == ["browser.collect_research_evidence"]
    assert "network.read.research" in manifest["required_capabilities"]
    assert manifest["side_effect_level"] == "proposal_only"
