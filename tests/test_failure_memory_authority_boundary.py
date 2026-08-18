from pathlib import Path


FORBIDDEN_IMPORTS = {
    "subprocess",
    "app.execution",
    "app.tools.exec_tools",
    "app.tools.patch_tools",
    "app.nodes.executor_node",
}


def test_failure_memory_modules_do_not_import_execution_capabilities():
    root = Path("app/failure_memory")
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in root.glob("*.py")
    )
    for forbidden in FORBIDDEN_IMPORTS:
        assert forbidden not in source


def test_debug_report_has_historical_failure_case_ids_field():
    from app.schemas import DebugReport

    report = DebugReport(error_type="test")
    assert hasattr(report, "historical_failure_case_ids")
    assert report.historical_failure_case_ids == []


def test_fallback_report_includes_empty_historical_case_ids():
    from app.nodes.log_debug_node import _build_fallback_report

    report = _build_fallback_report(
        error_type="unknown",
        traceback="",
        log_path="/tmp/test.log",
    )
    assert report.historical_failure_case_ids == []


def test_cuda_oom_report_includes_empty_historical_case_ids():
    from app.nodes.log_debug_node import _build_cuda_oom_report

    report = _build_cuda_oom_report()
    assert report.historical_failure_case_ids == []
