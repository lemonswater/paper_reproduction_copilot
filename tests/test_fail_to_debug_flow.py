from app.graph import route_after_executor


def test_route_after_executor_goes_to_log_debug_when_failed_with_log_path() -> None:
    state = {
        "final_status": "failed",
        "log_path": "outputs/execution.log",
    }

    result = route_after_executor(state)

    assert result == "log_debug"


def test_route_after_executor_goes_to_final_report_when_succeeded() -> None:
    state = {
        "final_status": "succeeded",
        "execution_log_path": "outputs/execution.log",
    }

    result = route_after_executor(state)

    assert result == "final_report"


def test_route_after_executor_goes_to_final_report_when_failed_but_no_log_path() -> None:
    state = {
        "final_status": "failed",
    }

    result = route_after_executor(state)

    assert result == "final_report"