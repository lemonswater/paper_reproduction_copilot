import importlib

from app.config import settings
from app.nodes.log_debug_node import (
    _run_optional_cuda_build_skill,
    _should_run_cuda_build_skill,
)


module = importlib.import_module("app.nodes.log_debug_node")


def test_cuda_skill_selector_requires_cuda_and_failure_markers():
    assert _should_run_cuda_build_skill(
        "nvcc fatal: unsupported gpu architecture"
    )
    assert not _should_run_cuda_build_skill(
        "CUDA is available and training started"
    )
    assert not _should_run_cuda_build_skill(
        "ordinary ValueError: invalid shape"
    )


def test_disabled_skill_does_not_build_registry(monkeypatch):
    monkeypatch.setattr(settings, "agent_skills_enabled", False)

    def fail_if_called(**kwargs):
        del kwargs
        raise AssertionError("disabled Skill 不应构建 Registry")

    monkeypatch.setattr(module, "build_skill_registry", fail_if_called)
    result = _run_optional_cuda_build_skill(
        state={},
        log_text="nvcc failed: no such file",
    )

    assert result == (None, None, None, [], None)
