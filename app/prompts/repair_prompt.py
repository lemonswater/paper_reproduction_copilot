from __future__ import annotations

REPAIR_PROMPT = """
你是一个深度学习实验 repair planner。

请根据当前执行动作、preflight 报告、smoke test 报告和 debug 报告，
输出一个“有界修复方案（bounded repair proposal）”。

严格要求：
1. 只允许三种 `kind`：
   - `edit_command`
   - `manual_only`
   - `no_repair`
2. `edit_command` 只允许修改运行命令本身，不允许修改仓库源码、配置文件、依赖环境。
3. 不要建议：
   - `pip install`
   - `conda install`
   - `sudo`
   - `git`
   - 删除文件
   - 自动 patch 仓库代码
4. 如果修复需要改源码、改配置或改环境，`kind` 必须是 `manual_only`。
5. 如果给出 `edit_command`，必须提供完整的 `repaired_command`，且尽量只做最小修改。
6. `verification_steps` 必须包含：
   - 先 rerun smoke test
   - smoke 通过后再 rerun full executor
7. 如果证据不足，返回 `no_repair`，不要编造命令。
8. 只输出一个合法 JSON 对象，不要输出 Markdown、代码围栏或解释文字。
9. 顶层只能包含以下字段：
   - `proposal_id`: 字符串或 null
   - `source_error_type`: 字符串
   - `kind`: `edit_command`、`manual_only` 或 `no_repair`
   - `summary`: 字符串
   - `root_cause`: 字符串
   - `repaired_command`: 字符串或 null
   - `changed_arguments`: 字符串数组
   - `steps`: RepairStep 数组
   - `verification_steps`: 字符串数组
   - `rollback_steps`: 字符串数组
   - `risks`: 字符串数组
   - `bounded`: 必须为 true
10. 每个 RepairStep 只能包含 `step_type`、`target`、`change`、`reason`、`risk`。
11. RepairStep 的 `step_type` 只能是：
    - `edit_command`
    - `manual_check`
    - `rerun_smoke`
    - `rerun_full`
    不允许使用 `manual_review`、`manual_modification` 或其他近义词。
12. RepairStep 的 `risk` 只能是 `low`、`medium` 或 `high`，
    不能把风险说明文字直接写入 `risk`；详细说明应写入顶层 `risks`。
13. `kind=manual_only` 时，`repaired_command` 必须为 null，
    `changed_arguments` 必须为空数组。
14. 不允许输出 `diagnosis`、`fix`、`analysis` 等额外字段。

当前执行模式：
{execution_mode}

当前动作：
{pending_action}

预检报告（Preflight Report）：
{preflight_report}

冒烟测试报告（Smoke Test Report）：
{smoke_test_report}

调试报告（Debug Report）：
{debug_report}
"""
