from __future__ import annotations

import json
from pathlib import Path

from app.evaluation.schemas import EvalCase, EvalCaseBundle

EVALUATION_ROOT = Path(__file__).resolve().parent
DEFAULT_CASE_DIR = EVALUATION_ROOT / "cases"


def _is_relative_to(path: Path, root: Path) -> bool:
    """
    Python 3.10 兼容的路径包含检查。

    不使用 Path.is_relative_to() 之外的新版本 API，保持项目最低版本约束。
    """

    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_evaluation_path(relative_path: str) -> Path:
    """
    只允许 case 引用 app/evaluation/ 目录内的 fixture。

    case 文件属于仓库内容，但仍不能允许：
      ../../.env
      /etc/passwd
      指向工作区外的软链接
    """

    candidate = (EVALUATION_ROOT / relative_path).resolve()
    root = EVALUATION_ROOT.resolve()

    if not _is_relative_to(candidate, root):
        raise ValueError(
            f"评测路径逃逸 EVALUATION_ROOT：{relative_path}"
        )
    return candidate


def _validate_case_fixture(case: EvalCase) -> None:
    if case.runner in {
        "fixture",
        "chat_scenario",
        "chat_provider",
        "conversation_decision",
        "conversation_decision_provider",
    }:
        fixture_path = resolve_evaluation_path(
            str(case.input.fixture_path)
        )
        if not fixture_path.is_file():
            raise FileNotFoundError(
                f"case={case.case_id} 的 fixture 不存在："
                f"{fixture_path}"
            )


def load_case_file(path: Path) -> EvalCase:
    """读取传统单 Case JSON；Bundle 请通过 load_case_entries 读取。"""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "cases" in payload:
        raise ValueError(
            f"{path} 是 Case Bundle，不能通过 load_case_file 读取"
        )
    case = EvalCase.model_validate(payload)
    _validate_case_fixture(case)

    return case


def load_case_entries(path: Path) -> list[EvalCase]:
    """同时兼容传统单 Case JSON 和同类 Case Bundle JSON。"""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "cases" in payload:
        cases = EvalCaseBundle.model_validate(payload).cases
    else:
        cases = [EvalCase.model_validate(payload)]

    for case in cases:
        _validate_case_fixture(case)
    return cases


def load_cases(
    *,
    case_dir: Path = DEFAULT_CASE_DIR,
    suite: str = "offline",
    case_ids: set[str] | None = None,
) -> list[EvalCase]:
    """
    递归读取指定 suite 的单 Case JSON 或 Case Bundle JSON。

    case_ids 用于本地只跑一个或几个 case；None 表示运行整个 suite。
    """

    suite_dir = (case_dir / suite).resolve()
    root = case_dir.resolve()
    if not _is_relative_to(suite_dir, root):
        raise ValueError("suite 路径逃逸 case_dir")
    if not suite_dir.is_dir():
        raise FileNotFoundError(f"评测 suite 不存在：{suite_dir}")

    loaded: list[EvalCase] = []
    seen_ids: set[str] = set()

    for path in sorted(suite_dir.rglob("*.json")):
        for case in load_case_entries(path):
            if case.suite != suite:
                raise ValueError(
                    f"{path} 声明 suite={case.suite}，"
                    f"但位于 suite={suite} 目录"
                )
            if case.case_id in seen_ids:
                raise ValueError(f"重复 case_id：{case.case_id}")
            seen_ids.add(case.case_id)

            if case_ids is None or case.case_id in case_ids:
                loaded.append(case)

    if case_ids:
        missing = sorted(case_ids - {case.case_id for case in loaded})
        if missing:
            raise KeyError(f"未找到指定 case：{missing}")

    if not loaded:
        raise ValueError(f"suite={suite} 没有可运行 case")

    return loaded
