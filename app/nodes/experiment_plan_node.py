from __future__ import annotations

import ast
import json
import re
import shlex
from pathlib import Path

from app.config import settings
from app.model_routing.factory import build_model_gateway
from app.prompts.plan_prompt import EXPERIMENT_PLAN_PROMPT
from app.retrieval.indexer import load_repository_index
from app.schemas import ExperimentPlan, RunCommand
from app.tools.artifact_tools import (
    artifact_dir,
    artifact_state_update,
    register_existing_artifact,
    write_json_artifact,
    write_text_artifact,
)
from app.tools.error_tools import (
    stage_error_result,
    structured_failure_update,
)
from app.tools.structured_output_tools import (
    write_structured_output_trace,
)
from app.tools.repo_tools import (
    is_mapping_relevant_file,
)


def _build_plan_fallback(*, goal: str, reason: str) -> ExperimentPlan:
    return ExperimentPlan(
        goal=goal,
        environment_steps=[],
        data_steps=[],
        train_steps=[],
        eval_steps=[],
        run_commands=[],
        risks=[
            "实验计划缺少可信结构化结果，禁止进入自动执行。",
        ],
        unresolved_questions=[reason],
    )


def _compact_paper_summary(payload: dict) -> dict:
    """保留规划所需论文事实，移除已验证但体积很大的 provenance。"""

    compact = {
        key: payload.get(key)
        for key in (
            "title",
            "research_problem",
            "core_idea",
            "datasets",
            "metrics",
            "reproduction_risks",
            "unresolved_questions",
        )
        if payload.get(key) not in (None, [], "")
    }
    compact["method_modules"] = [
        {
            key: module.get(key)
            for key in (
                "name",
                "description",
                "possible_keywords",
                "missing_info",
            )
            if module.get(key) not in (None, [], "")
        }
        for module in payload.get("method_modules", [])
        if isinstance(module, dict)
    ]
    compact["experiment_settings"] = [
        {
            key: setting.get(key)
            for key in ("name", "value")
            if setting.get(key) not in (None, "")
        }
        for setting in payload.get("experiment_settings", [])
        if isinstance(setting, dict)
    ]
    return compact


def _entry_context_tokens(state: dict) -> set[str]:
    """收集论文方法、数据集和实验目标中的入口排序词。"""

    summary = state.get("paper_summary")
    if not isinstance(summary, dict):
        summary = {}
    values: list[str] = [
        str(state.get("experiment_goal") or ""),
        str(summary.get("title") or ""),
        str(summary.get("core_idea") or ""),
        *[
            str(value)
            for value in summary.get("datasets") or []
        ],
    ]
    for module in summary.get("method_modules") or []:
        if not isinstance(module, dict):
            continue
        values.extend(
            [
                str(module.get("name") or ""),
                str(module.get("description") or ""),
            ]
        )
    return {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            " ".join(values).casefold(),
        )
        if len(token) >= 3
    }


def _readme_reference_text(repo_map: dict) -> str:
    """读取有限 README 文本，用于优先选择作者公开的实验入口。"""

    raw_root = repo_map.get("repo_path")
    if not raw_root:
        return ""
    try:
        root = Path(str(raw_root)).expanduser().resolve()
    except OSError:
        return ""
    if not root.is_dir():
        return ""

    values: list[str] = []
    for raw_path in list(
        repo_map.get("readme_files") or []
    )[:5]:
        try:
            path = (root / str(raw_path)).resolve()
            path.relative_to(root)
            if (
                not path.is_file()
                or path.stat().st_size > 1024 * 1024
            ):
                continue
            values.append(
                path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).casefold()
            )
        except (OSError, ValueError):
            continue
    return "\n".join(values)


def _entry_priority(
    entry: str,
    *,
    context_tokens: set[str],
    readme_text: str,
    goal_text: str,
) -> tuple[int, int, str]:
    """按论文相关性、README 证据和目录深度排列实验入口。"""

    path = Path(entry)
    normalized = entry.removeprefix("./").casefold()
    path_tokens = set(
        re.findall(r"[a-z0-9]+", normalized)
    )
    score = 0

    if path.suffix.casefold() == ".py":
        score += 20
    elif path.suffix.casefold() == ".sh":
        score += 8
    if len(path.parts) == 1:
        score += 30
    if any(
        marker in path.stem.casefold()
        for marker in ("train", "finetune")
    ):
        score += 15

    if normalized and normalized in readme_text:
        score += 90
    elif path.name.casefold() in readme_text:
        score += 45
    parent_prefix = path.parent.as_posix().casefold().strip("./")
    if (
        parent_prefix
        and parent_prefix != "."
        and f"{parent_prefix}/" in readme_text
    ):
        score += 65

    related_tokens = 0
    for path_token in path_tokens:
        if len(path_token) < 3:
            continue
        if any(
            path_token == context_token
            or (
                min(len(path_token), len(context_token)) >= 4
                and path_token[:4] == context_token[:4]
            )
            for context_token in context_tokens
        ):
            related_tokens += 1
    score += min(related_tokens, 4) * 32

    # 伪标签、VAT、baseline、resume 等通常是对比实验或后续阶段；除非
    # 用户目标明确点名，否则不能压过论文主方法训练入口。
    normalized_goal = goal_text.casefold()
    auxiliary_markers = {
        "pseudo_labels": "pseudo",
        "baseline": "baseline",
        "vat": "vat",
        "resume": "resume",
        "entmin": "entmin",
    }
    for path_marker, goal_marker in auxiliary_markers.items():
        if (
            path_marker in normalized
            and goal_marker not in normalized_goal
        ):
            score -= 55

    return (-score, len(path.parts), normalized)


def _ordered_entries(
    *,
    state: dict,
    repo_map: dict,
) -> list[str]:
    context_tokens = _entry_context_tokens(state)
    readme_text = _readme_reference_text(repo_map)
    goal_text = str(
        state.get("experiment_goal") or ""
    )
    values = list(
        dict.fromkeys(
            [
                *list(repo_map.get("train_entries") or []),
                *list(repo_map.get("eval_entries") or []),
            ]
        )
    )
    relevant = [
        str(value)
        for value in values
        if is_mapping_relevant_file(str(value))
    ]
    return sorted(
        relevant,
        key=lambda entry: _entry_priority(
            entry,
            context_tokens=context_tokens,
            readme_text=readme_text,
            goal_text=goal_text,
        ),
    )


def _compact_repo_map(
    payload: dict,
    *,
    state: dict,
) -> dict:
    """限制仓库文件列表规模，同时保留训练入口和关键文件。"""

    ordered_entries = _ordered_entries(
        state=state,
        repo_map=payload,
    )
    train_entry_set = set(
        payload.get("train_entries") or []
    )
    eval_entry_set = set(
        payload.get("eval_entries") or []
    )
    compact: dict = {}
    for key, value in payload.items():
        if isinstance(value, list):
            if key == "train_entries":
                compact[key] = [
                    entry
                    for entry in ordered_entries
                    if entry in train_entry_set
                ][:20]
            elif key == "eval_entries":
                compact[key] = [
                    entry
                    for entry in ordered_entries
                    if entry in eval_entry_set
                ][:20]
            else:
                compact[key] = value[:20]
        elif value not in (None, ""):
            compact[key] = value
    return compact


def _compact_code_mapping(payload: list) -> list[dict]:
    """规划只消费映射结论，不重复发送完整源码、哈希和检索信号。"""

    compact: list[dict] = []
    for mapping in payload:
        if not isinstance(mapping, dict):
            continue
        candidates = []
        raw_candidates = mapping.get("candidates")
        if not isinstance(raw_candidates, list):
            raw_candidates = []
        for candidate in raw_candidates[:3]:
            if not isinstance(candidate, dict):
                continue
            candidates.append(
                {
                    key: candidate.get(key)
                    for key in (
                        "file_path",
                        "symbols",
                        "reason",
                        "confidence",
                    )
                    if candidate.get(key) not in (None, [], "")
                }
            )
        compact.append(
            {
                "module_name": mapping.get("module_name"),
                "target_category": mapping.get("target_category"),
                "candidates": candidates,
                "unresolved_questions": (
                    mapping.get("unresolved_questions")[:3]
                    if isinstance(
                        mapping.get("unresolved_questions"),
                        list,
                    )
                    else []
                ),
            }
        )
    return compact


def _load_cli_contract(
    *,
    state: dict,
    repo_map: dict,
) -> list[dict]:
    """从本次运行的 RepositoryIndex 读取训练/评测入口 CLI 契约。"""

    raw_index_path = state.get("repo_index_path")
    raw_run_dir = state.get("run_dir")
    if not raw_index_path or not raw_run_dir:
        return []

    try:
        index_path = Path(str(raw_index_path)).resolve()
        run_dir = Path(str(raw_run_dir)).resolve()
        index_path.relative_to(run_dir)
        index = load_repository_index(index_path)
    except (OSError, ValueError, TypeError):
        return []

    available_cli_entries = {
        option.file_path
        for option in index.cli_options
    }
    entry_paths = [
        entry
        for entry in _ordered_entries(
            state=state,
            repo_map=repo_map,
        )
        if entry in available_cli_entries
    ][:8]
    entry_set = set(entry_paths)
    grouped: dict[str, list[dict]] = {
        path: []
        for path in entry_paths
    }
    for option in index.cli_options:
        if option.file_path not in entry_set:
            continue
        options = grouped[option.file_path]
        if len(options) >= 40:
            continue
        options.append(
            {
                key: value
                for key, value in {
                    "flags": list(option.flags),
                    "default": option.default_repr,
                    "help": option.help_text,
                }.items()
                if value not in (None, [], "")
            }
        )

    return [
        {
            "entry": entry,
            "options": grouped[entry],
        }
        for entry in entry_paths
        if grouped[entry]
    ]


def _option_key(flag: str) -> str:
    return "".join(
        character
        for character in flag.lstrip("-").casefold()
        if character.isalnum()
    )


def _preferred_flag(flags: list[str]) -> str | None:
    long_flags = [
        flag
        for flag in flags
        if flag.startswith("--")
    ]
    if long_flags:
        return long_flags[0]
    return flags[0] if flags else None


def _default_cli_token(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        parsed = value
    if isinstance(parsed, (str, int, float)):
        token = str(parsed).strip()
        return token or None
    return None


def _is_option_token(value: str) -> bool:
    if not value.startswith("-") or value in {"-", "--"}:
        return False
    try:
        float(value)
    except ValueError:
        return True
    return False


def _contract_by_entry(
    cli_contract: list[dict],
) -> dict[str, dict]:
    contracts: dict[str, dict] = {}
    basenames: dict[str, list[dict]] = {}
    for item in cli_contract:
        entry = str(item.get("entry") or "").strip()
        if not entry:
            continue
        contracts[entry.removeprefix("./")] = item
        basenames.setdefault(
            Path(entry).name,
            [],
        ).append(item)
    for basename, items in basenames.items():
        if len(items) == 1:
            contracts[basename] = items[0]
    return contracts


def _sanitize_command_with_cli_contract(
    command: RunCommand,
    *,
    contracts: dict[str, dict],
) -> tuple[RunCommand | None, list[str]]:
    """校正连字符变体并删除目标入口不支持的 CLI 参数。"""

    try:
        tokens = shlex.split(command.command, posix=True)
    except ValueError as exc:
        return None, [
            f"命令无法解析，已停止使用：{exc}"
        ]

    script_index = None
    contract = None
    for index, token in enumerate(tokens):
        normalized = token.removeprefix("./")
        candidate = contracts.get(normalized)
        if candidate is None:
            candidate = contracts.get(
                Path(normalized).name
            )
        if candidate is not None:
            script_index = index
            contract = candidate
            break
    if script_index is None or contract is None:
        return command, []

    raw_options = contract.get("options")
    if not isinstance(raw_options, list):
        return command, []

    exact_flags: dict[str, str] = {}
    normalized_flags: dict[str, set[str]] = {}
    data_path_options: list[tuple[str, str]] = []
    for option in raw_options:
        if not isinstance(option, dict):
            continue
        flags = [
            str(flag)
            for flag in option.get("flags") or []
            if str(flag).startswith("-")
        ]
        for flag in flags:
            exact_flags[flag] = flag
            normalized_flags.setdefault(
                _option_key(flag),
                set(),
            ).add(flag)

        preferred = _preferred_flag(flags)
        default_token = _default_cli_token(
            option.get("default")
        )
        if (
            preferred is not None
            and _option_key(preferred)
            in {
                "datapath",
                "datasetpath",
                "dataroot",
                "datasetroot",
            }
            and default_token is not None
        ):
            data_path_options.append(
                (preferred, default_token)
            )

    output = tokens[: script_index + 1]
    diagnostics: list[str] = []
    used_flags: set[str] = set()
    index = script_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            output.extend(tokens[index:])
            break
        if not _is_option_token(token):
            output.append(token)
            index += 1
            continue

        raw_flag, separator, attached_value = (
            token.partition("=")
        )
        resolved_flag = exact_flags.get(raw_flag)
        if resolved_flag is None:
            candidates = normalized_flags.get(
                _option_key(raw_flag),
                set(),
            )
            if len(candidates) == 1:
                resolved_flag = next(iter(candidates))
                diagnostics.append(
                    f"已将 {raw_flag} 校正为 {resolved_flag}。"
                )

        if resolved_flag is None:
            diagnostics.append(
                f"入口 {contract['entry']} 不支持参数 {raw_flag}，已移除。"
            )
            index += 1
            if not separator:
                while (
                    index < len(tokens)
                    and not _is_option_token(
                        tokens[index]
                    )
                ):
                    index += 1
            continue

        used_flags.add(resolved_flag)
        output.append(
            (
                f"{resolved_flag}={attached_value}"
                if separator
                else resolved_flag
            )
        )
        index += 1

    for flag, default_value in data_path_options:
        if flag in used_flags:
            continue
        output.extend([flag, default_value])
        diagnostics.append(
            f"已显式补充仓库默认数据路径 {flag}={default_value}，路径仍需确认。"
        )

    sanitized = command.model_copy(
        update={
            "command": shlex.join(output),
            "source": (
                "need_confirm"
                if diagnostics
                else command.source
            ),
            "reason": (
                command.reason
                + (
                    "；命令参数已按仓库 argparse 契约校正。"
                    if diagnostics
                    else ""
                )
            ),
        }
    )
    return sanitized, diagnostics


def _apply_cli_contract(
    plan: ExperimentPlan,
    *,
    cli_contract: list[dict],
    repo_path: str | None,
) -> ExperimentPlan:
    if not plan.run_commands:
        return plan

    contracts = _contract_by_entry(cli_contract)
    commands: list[RunCommand] = []
    diagnostics: list[str] = []
    for command in plan.run_commands:
        sanitized, command_diagnostics = (
            _sanitize_command_with_cli_contract(
                command,
                contracts=contracts,
            )
        )
        diagnostics.extend(command_diagnostics)
        if sanitized is not None:
            if repo_path:
                try:
                    repo_root = Path(
                        repo_path
                    ).expanduser().resolve()
                    command_cwd = Path(
                        sanitized.cwd
                    ).expanduser().resolve()
                except OSError:
                    repo_root = None
                    command_cwd = None
                if (
                    repo_root is not None
                    and command_cwd != repo_root
                ):
                    diagnostics.append(
                        "命令工作目录不在当前论文代码仓库根目录，"
                        f"已校正为 {repo_root}。"
                    )
                    sanitized = sanitized.model_copy(
                        update={
                            "cwd": str(repo_root),
                            "source": "need_confirm",
                            "reason": (
                                sanitized.reason
                                + "；工作目录已按当前仓库根目录校正。"
                            ),
                        }
                    )
            commands.append(sanitized)

    return plan.model_copy(
        update={
            "run_commands": commands,
            "unresolved_questions": list(
                dict.fromkeys(
                    [
                        *plan.unresolved_questions,
                        *diagnostics,
                    ]
                )
            )[:12],
        }
    )


def _render_steps(title: str, steps: list) -> list[str]:
    lines = [f"## {title}", ""]
    if not steps:
        lines.append("- 暂无明确步骤")
        lines.append("")
        return lines

    for step in steps:
        lines.append(f"### {step.order}. {step.name}")
        lines.append("")
        lines.append(f"- 动作：{step.action}")
        lines.append(f"- 来源：{step.source}")
        if step.risk:
            lines.append(f"- 风险：{step.risk}")
        lines.append("")
    return lines


def _render_plan_markdown(plan: ExperimentPlan) -> str:
    lines = ["# 实验计划", "", f"目标：{plan.goal}", ""]
    lines += _render_steps("环境", plan.environment_steps)
    lines += _render_steps("数据", plan.data_steps)
    lines += _render_steps("训练", plan.train_steps)
    lines += _render_steps("评估", plan.eval_steps)

    lines += ["## 运行命令", ""]
    for command in plan.run_commands:
        lines.append(f"```bash\n{command.command}\n```")
        lines.append(f"- 工作目录（cwd）：`{command.cwd}`")
        lines.append(f"- 来源：{command.source}")
        lines.append(f"- 风险：{command.risk_level}")
        lines.append(f"- 原因：{command.reason}")
        lines.append("")

    if plan.unresolved_questions:
        lines += ["## 待解决问题", ""]
        for item in plan.unresolved_questions:
            lines.append(f"- {item}")
    return "\n".join(lines)


def experiment_plan_node(state: dict) -> dict:
    paper_summary = state.get("paper_summary")
    repo_map = state.get("repo_map")
    paper_code_mapping = state.get("paper_code_mapping")
    experiment_goal = state.get("experiment_goal") or "复现论文 main result"
    cli_contract = (
        _load_cli_contract(
            state=state,
            repo_map=repo_map,
        )
        if isinstance(repo_map, dict)
        else []
    )
    trace_path = None
    invocation = None

    missing_inputs = [
        name
        for name, value in (
            ("paper_summary", paper_summary),
            ("repo_map", repo_map),
            ("paper_code_mapping", paper_code_mapping),
        )
        if not value
    ]

    if missing_inputs:
        # 输入不足时没有调用模型，因此也不生成 structured attempt trace。
        plan = _build_plan_fallback(
            goal=experiment_goal,
            reason=("缺少实验规划输入：" + ", ".join(missing_inputs)),
        )
    else:
        prompt = EXPERIMENT_PLAN_PROMPT.format(
            paper_summary=json.dumps(
                _compact_paper_summary(paper_summary),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            repo_map=json.dumps(
                _compact_repo_map(
                    repo_map,
                    state=state,
                ),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            paper_code_mapping=json.dumps(
                _compact_code_mapping(paper_code_mapping),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            cli_contract=json.dumps(
                cli_contract,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            experiment_goal=experiment_goal,
        )

        invocation = build_model_gateway().invoke_structured(
            task_kind="experiment_plan",
            schema=ExperimentPlan,
            prompt=prompt,
            node_name="experiment_plan",
            job_id=state.get("job_id"),
            run_id=state.get("run_id"),
            quality_tier="balanced",
            requested_max_output_tokens=8192,
        )

        if invocation.value is not None:
            plan = invocation.value

            # goal 来自用户输入，不允许模型悄悄改写任务目标。
            if plan.goal != experiment_goal:
                plan = plan.model_copy(update={"goal": experiment_goal})
            plan = _apply_cli_contract(
                plan,
                cli_contract=cli_contract,
                repo_path=str(
                    repo_map.get("repo_path")
                    or state.get("repo_path")
                    or ""
                ),
            )
        else:
            plan = _build_plan_fallback(
                goal=experiment_goal,
                reason=("模型在有限重试后仍未返回合法 ExperimentPlan。"),
            )

        trace_path = write_structured_output_trace(
            result=invocation.result,
            node_name="experiment_plan",
            schema_name="ExperimentPlan",
            output_dir=artifact_dir(
                state,
                "traces",
                "structured",
            ),
            fallback_used=invocation.value is None,
            model_invocation_id=invocation.invocation_id,
            model_decision_sha256=(
                invocation.decision.decision_sha256
            ),
            model_profile_id=(
                invocation.decision.executed_profile_id
            ),
            model_name=(
                invocation.decision.executed_model_name
            ),
            model_usage_quality=(
                invocation.ledger_record.usage_quality
                if invocation.ledger_record is not None
                else None
            ),
        )

    _, json_record = write_json_artifact(
        state=state,
        relative_path="planning/experiment_plan.json",
        payload=plan.model_dump(),
        producer_node="experiment_plan",
    )
    _, md_record = write_text_artifact(
        state=state,
        relative_path="planning/experiment_plan.md",
        text=_render_plan_markdown(plan),
        producer_node="experiment_plan",
        media_type="text/markdown",
    )

    records = [json_record, md_record]
    if trace_path is not None:
        records.append(
            register_existing_artifact(
                state=state,
                path=trace_path,
                producer_node="experiment_plan",
                media_type="application/json",
            )
        )

    payload = {
        "experiment_plan": plan.model_dump(),
        "run_commands": [command.model_dump() for command in plan.run_commands],
        **artifact_state_update(state, records),
    }

    if missing_inputs:
        return stage_error_result(
            state={**state, **payload},
            stage="experiment_plan",
            code="EXPERIMENT_PLAN_INPUT_MISSING",
            category="agent",
            message="缺少实验规划输入：" + ", ".join(missing_inputs),
            extra_update=payload,
        )

    if invocation is not None and invocation.value is None:
        working_state = {**state, **payload}
        return {
            **payload,
            **structured_failure_update(
                state=working_state,
                stage="experiment_plan",
                invocation=invocation,
                terminal=True,
            ),
        }

    return payload
