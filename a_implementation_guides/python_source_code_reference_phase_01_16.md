# Python 源码函数参考：Phase 1-16

> 自动同步日期：2026-08-19
> 覆盖文件：101；函数/方法：561。
> 本文由当前 Python AST 生成；伪代码保留控制流和失败边界，但会把相邻语句合并为通俗的逻辑步骤。
> 阶段归类按文件的主要职责完成；跨阶段持续修改的文件只进入一个主分册，源码行号是最终依据。

## 阅读约定

- 伪代码按“一段逻辑做什么”组织；连续初始化、校验或字段更新会合并成一句或一段。
- 简单的 `if`、`for` 和 `with` 会直接概括成完整句子；有嵌套分支或提前返回时才使用缩进展开。
- 变量名只用来标识数据保存在哪里；文字是为了解释意图，不是可直接运行的 Python 代码。
- 输入表中的路径、ID、Hash、命令、状态和领域记录分别表示不同的业务对象，不能互换。
- “抛出异常”对应真实 `raise`，调用方不会收到正常返回值。
- Hash/fingerprint 表示内容身份，不是加密后的业务正文，也不是授权凭证。
- Command 表示命令文本或结构化命令；只有 Executor 路径才可能真正执行。
- Protocol 中只有 `...` 的函数会显示为“接口占位（无具体实现）”，它声明契约而不是具体实现。

## 文件索引

- [`app/command_selection.py`](#app-command-selection-py)：5 个函数/方法
- [`app/execution/base.py`](#app-execution-base-py)：7 个函数/方法
- [`app/execution/cancellation.py`](#app-execution-cancellation-py)：9 个函数/方法
- [`app/execution/capability_policy.py`](#app-execution-capability-policy-py)：5 个函数/方法
- [`app/execution/conda_runner.py`](#app-execution-conda-runner-py)：1 个函数/方法
- [`app/execution/container_engine.py`](#app-execution-container-engine-py)：7 个函数/方法
- [`app/execution/container_plan.py`](#app-execution-container-plan-py)：4 个函数/方法
- [`app/execution/container_reconcile.py`](#app-execution-container-reconcile-py)：3 个函数/方法
- [`app/execution/container_records.py`](#app-execution-container-records-py)：3 个函数/方法
- [`app/execution/container_supervisor.py`](#app-execution-container-supervisor-py)：5 个函数/方法
- [`app/execution/environment.py`](#app-execution-environment-py)：5 个函数/方法
- [`app/execution/local_runner.py`](#app-execution-local-runner-py)：1 个函数/方法
- [`app/execution/oci_runner.py`](#app-execution-oci-runner-py)：3 个函数/方法
- [`app/execution/podman_engine.py`](#app-execution-podman-engine-py)：9 个函数/方法
- [`app/execution/process_supervisor.py`](#app-execution-process-supervisor-py)：15 个函数/方法
- [`app/execution/profile_store.py`](#app-execution-profile-store-py)：6 个函数/方法
- [`app/execution/registry.py`](#app-execution-registry-py)：2 个函数/方法
- [`app/graph.py`](#app-graph-py)：24 个函数/方法
- [`app/memory/checkpoint.py`](#app-memory-checkpoint-py)：5 个函数/方法
- [`app/nodes/action_builder_node.py`](#app-nodes-action-builder-node-py)：1 个函数/方法
- [`app/nodes/code_search_node.py`](#app-nodes-code-search-node-py)：11 个函数/方法
- [`app/nodes/command_selection_node.py`](#app-nodes-command-selection-node-py)：7 个函数/方法
- [`app/nodes/execution_verifier_node.py`](#app-nodes-execution-verifier-node-py)：2 个函数/方法
- [`app/nodes/executor_node.py`](#app-nodes-executor-node-py)：2 个函数/方法
- [`app/nodes/experiment_plan_node.py`](#app-nodes-experiment-plan-node-py)：7 个函数/方法
- [`app/nodes/file_repair_planner_node.py`](#app-nodes-file-repair-planner-node-py)：5 个函数/方法
- [`app/nodes/final_report_node.py`](#app-nodes-final-report-node-py)：5 个函数/方法
- [`app/nodes/human_review_node.py`](#app-nodes-human-review-node-py)：1 个函数/方法
- [`app/nodes/input_validation_node.py`](#app-nodes-input-validation-node-py)：6 个函数/方法
- [`app/nodes/log_debug_node.py`](#app-nodes-log-debug-node-py)：10 个函数/方法
- [`app/nodes/mapping_node.py`](#app-nodes-mapping-node-py)：7 个函数/方法
- [`app/nodes/method_extractor_node.py`](#app-nodes-method-extractor-node-py)：4 个函数/方法
- [`app/nodes/paper_reader_node.py`](#app-nodes-paper-reader-node-py)：1 个函数/方法
- [`app/nodes/patch_apply_node.py`](#app-nodes-patch-apply-node-py)：1 个函数/方法
- [`app/nodes/patch_builder_node.py`](#app-nodes-patch-builder-node-py)：1 个函数/方法
- [`app/nodes/patch_promotion_review_node.py`](#app-nodes-patch-promotion-review-node-py)：2 个函数/方法
- [`app/nodes/patch_review_node.py`](#app-nodes-patch-review-node-py)：1 个函数/方法
- [`app/nodes/patch_verdict_node.py`](#app-nodes-patch-verdict-node-py)：2 个函数/方法
- [`app/nodes/patch_verification_executor_node.py`](#app-nodes-patch-verification-executor-node-py)：2 个函数/方法
- [`app/nodes/patch_verifier_node.py`](#app-nodes-patch-verifier-node-py)：1 个函数/方法
- [`app/nodes/preflight_check_node.py`](#app-nodes-preflight-check-node-py)：1 个函数/方法
- [`app/nodes/repair_action_builder_node.py`](#app-nodes-repair-action-builder-node-py)：1 个函数/方法
- [`app/nodes/repair_planner_node.py`](#app-nodes-repair-planner-node-py)：4 个函数/方法
- [`app/nodes/repo_scan_node.py`](#app-nodes-repo-scan-node-py)：1 个函数/方法
- [`app/nodes/rerun_seed_node.py`](#app-nodes-rerun-seed-node-py)：1 个函数/方法
- [`app/nodes/risk_check_node.py`](#app-nodes-risk-check-node-py)：1 个函数/方法
- [`app/nodes/run_context_node.py`](#app-nodes-run-context-node-py)：1 个函数/方法
- [`app/nodes/run_manifest_node.py`](#app-nodes-run-manifest-node-py)：1 个函数/方法
- [`app/nodes/smoke_test_node.py`](#app-nodes-smoke-test-node-py)：1 个函数/方法
- [`app/tools/action_tools.py`](#app-tools-action-tools-py)：7 个函数/方法
- [`app/tools/artifact_tools.py`](#app-tools-artifact-tools-py)：22 个函数/方法
- [`app/tools/error_tools.py`](#app-tools-error-tools-py)：16 个函数/方法
- [`app/tools/exec_tools.py`](#app-tools-exec-tools-py)：4 个函数/方法
- [`app/tools/log_tools.py`](#app-tools-log-tools-py)：4 个函数/方法
- [`app/tools/mapping_target_tools.py`](#app-tools-mapping-target-tools-py)：25 个函数/方法
- [`app/tools/paper_tools.py`](#app-tools-paper-tools-py)：4 个函数/方法
- [`app/tools/patch_journal_tools.py`](#app-tools-patch-journal-tools-py)：4 个函数/方法
- [`app/tools/patch_tools.py`](#app-tools-patch-tools-py)：34 个函数/方法
- [`app/tools/preflight_tools.py`](#app-tools-preflight-tools-py)：16 个函数/方法
- [`app/tools/repair_tools.py`](#app-tools-repair-tools-py)：3 个函数/方法
- [`app/tools/repository_lock_tools.py`](#app-tools-repository-lock-tools-py)：2 个函数/方法
- [`app/tools/safe_shell_tools.py`](#app-tools-safe-shell-tools-py)：1 个函数/方法
- [`app/tools/smoke_test_tools.py`](#app-tools-smoke-test-tools-py)：5 个函数/方法
- [`app/tools/structured_output_tools.py`](#app-tools-structured-output-tools-py)：21 个函数/方法
- [`tests/test_action_builder_node.py`](#tests-test-action-builder-node-py)：4 个函数/方法
- [`tests/test_action_capability_policy.py`](#tests-test-action-capability-policy-py)：5 个函数/方法
- [`tests/test_command_selection_cli.py`](#tests-test-command-selection-cli-py)：8 个函数/方法
- [`tests/test_command_selection_contract.py`](#tests-test-command-selection-contract-py)：7 个函数/方法
- [`tests/test_command_selection_node.py`](#tests-test-command-selection-node-py)：8 个函数/方法
- [`tests/test_durable_checkpoint_resume.py`](#tests-test-durable-checkpoint-resume-py)：4 个函数/方法
- [`tests/test_execution_cancellation.py`](#tests-test-execution-cancellation-py)：2 个函数/方法
- [`tests/test_execution_profile_hash.py`](#tests-test-execution-profile-hash-py)：5 个函数/方法
- [`tests/test_execution_profiles.py`](#tests-test-execution-profiles-py)：5 个函数/方法
- [`tests/test_execution_runners.py`](#tests-test-execution-runners-py)：4 个函数/方法
- [`tests/test_execution_verifier_node.py`](#tests-test-execution-verifier-node-py)：7 个函数/方法
- [`tests/test_executor_node.py`](#tests-test-executor-node-py)：8 个函数/方法
- [`tests/test_fail_to_debug_flow.py`](#tests-test-fail-to-debug-flow-py)：6 个函数/方法
- [`tests/test_failed_run_manifest.py`](#tests-test-failed-run-manifest-py)：2 个函数/方法
- [`tests/test_file_repair_planner_node.py`](#tests-test-file-repair-planner-node-py)：4 个函数/方法
- [`tests/test_final_report_node.py`](#tests-test-final-report-node-py)：2 个函数/方法
- [`tests/test_input_validation_node.py`](#tests-test-input-validation-node-py)：4 个函数/方法
- [`tests/test_manual_cli_execution_profiles.py`](#tests-test-manual-cli-execution-profiles-py)：3 个函数/方法
- [`tests/test_minimal_execution_environment.py`](#tests-test-minimal-execution-environment-py)：5 个函数/方法
- [`tests/test_patch_application_recovery.py`](#tests-test-patch-application-recovery-py)：3 个函数/方法
- [`tests/test_patch_authorization_boundaries.py`](#tests-test-patch-authorization-boundaries-py)：8 个函数/方法
- [`tests/test_patch_review_nodes.py`](#tests-test-patch-review-nodes-py)：7 个函数/方法
- [`tests/test_patch_tools.py`](#tests-test-patch-tools-py)：9 个函数/方法
- [`tests/test_patch_verification_semantics.py`](#tests-test-patch-verification-semantics-py)：5 个函数/方法
- [`tests/test_patch_verifier_node.py`](#tests-test-patch-verifier-node-py)：10 个函数/方法
- [`tests/test_patch_worktree_cleanup.py`](#tests-test-patch-worktree-cleanup-py)：3 个函数/方法
- [`tests/test_preflight_check_node.py`](#tests-test-preflight-check-node-py)：3 个函数/方法
- [`tests/test_repair_action_builder_node.py`](#tests-test-repair-action-builder-node-py)：2 个函数/方法
- [`tests/test_repair_proposal_semantics.py`](#tests-test-repair-proposal-semantics-py)：4 个函数/方法
- [`tests/test_review_flow.py`](#tests-test-review-flow-py)：1 个函数/方法
- [`tests/test_run_manifest_node.py`](#tests-test-run-manifest-node-py)：4 个函数/方法
- [`tests/test_run_native_artifacts.py`](#tests-test-run-native-artifacts-py)：5 个函数/方法
- [`tests/test_smoke_repair_flow.py`](#tests-test-smoke-repair-flow-py)：12 个函数/方法
- [`tests/test_smoke_test_node.py`](#tests-test-smoke-test-node-py)：5 个函数/方法
- [`tests/test_stage_error_tools.py`](#tests-test-stage-error-tools-py)：7 个函数/方法
- [`tests/test_structured_action_and_approval_hash.py`](#tests-test-structured-action-and-approval-hash-py)：1 个函数/方法
- [`tests/test_supervised_execution_integration.py`](#tests-test-supervised-execution-integration-py)：1 个函数/方法

## 逐函数参考

### `app/command_selection.py`

**模块作用**：命令选择领域模块：纯内存 hash、编辑规范化、索引校验。

#### `compute_run_commands_hash`

- **源码**：`app/command_selection.py:43`
- **签名**：`def compute_run_commands_hash(run_commands: list[dict[str, Any]]) -> str`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，计算键顺序无关、列表顺序敏感的稳定 SHA-256。该函数接收候选运行命令集合，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_commands` | `list[dict[str, Any]]` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并把结果记为 规范化 JSON 文本；计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_validated_command_text`

- **源码**：`app/command_selection.py:59`
- **签名**：`def _validated_command_text(command: str, index: int) -> str`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，返回规范化命令，但不在这里判断命令风险。该函数接收当前命令、当前候选项的索引，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `index` | `int` | 候选集合中的零基索引，用于定位选中项；它不是业务 ID 或内容 Hash。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
去除当前命令的首尾空白，并把规范化后的文本记为 规范化后的文本。
如果规范化后的文本为空或为假，就拒绝继续处理并抛出 `CommandSelectionValidationError`，向调用方报告输入或运行失败。
如果规范化后的文本 的长度大于命令编辑文本的最大字符数，就拒绝继续处理并抛出 `CommandSelectionValidationError`，向调用方报告输入或运行失败。
如果由规范化后的文本组成的集合或迭代器中存在满足“当前字符 对应的 ASCII/Unicode 编码小于32 或 当前字符 对应的 ASCII/Unicode 编码等于127”的项，就拒绝继续处理并抛出 `CommandSelectionValidationError`，向调用方报告输入或运行失败。
返回规范化后的文本的当前值。
```

#### `normalize_command_edits`

- **源码**：`app/command_selection.py:88`
- **签名**：`def normalize_command_edits(edits: list[CommandEdit], command_count: int) -> list[CommandEdit]`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，校验索引唯一性和范围，并返回规范化的新对象。该函数接收命令修改项集合、候选命令的数量，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `edits` | `list[CommandEdit]` | 命令修改项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `command_count` | `int` | 对象数量或重试次数，用于范围和上限校验，不是进程退出码。 |

**输出**

- **Python 类型**：`list[CommandEdit]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
如果候选命令的数量小于1，就拒绝继续处理并抛出 `CommandSelectionIntegrityError`，向调用方报告输入或运行失败。
如果命令修改项集合 的长度大于最大命令集合，就拒绝继续处理并抛出 `CommandSelectionValidationError`，向调用方报告输入或运行失败。
将 当前处理结果 初始化为空去重集合，用来收集后续结果；将 规范化后的文本 初始化为空列表，用来收集后续结果。
遍历由命令修改项集合组成的集合或迭代器，每次把当前项记为编辑文本：
    如果当前候选项的索引属于当前处理结果，就拒绝继续处理并抛出 `CommandSelectionValidationError`，向调用方报告输入或运行失败。
    把当前候选项的索引追加或合并到当前处理结果。
    如果当前候选项的索引不小于候选命令的数量，就拒绝继续处理并抛出 `CommandSelectionValidationError`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到规范化后的文本。
返回规范化后的文本的当前值。
```

#### `validate_command_selection_response`

- **源码**：`app/command_selection.py:129`
- **签名**：`def validate_command_selection_response(run_commands: list[dict[str, Any]], response: CommandSelectionResponse, expected_preview_hash: str | None) -> CommandSelectionResponse`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，把 response 绑定到当前候选列表并返回规范化结果。该函数接收候选运行命令集合、结构化响应、期望的 Hash，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_commands` | `list[dict[str, Any]]` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `response` | `CommandSelectionResponse` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `expected_preview_hash` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。；默认 空值 |

**输出**

- **Python 类型**：`CommandSelectionResponse`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
如果候选运行命令集合为空或为假，就拒绝继续处理并抛出 `CommandSelectionIntegrityError`，向调用方报告输入或运行失败。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `CommandSelectionIntegrityError`，向调用方报告输入或运行失败。
    如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `CommandSelectionIntegrityError`，向调用方报告输入或运行失败。
调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果，并把结果记为 当前值的 Hash。
如果期望的 Hash不为空 且 “调用 `fullmatch` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `CommandSelectionIntegrityError`，向调用方报告输入或运行失败。
如果期望的 Hash不为空 且 “调用 `compare_digest` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `CommandSelectionIntegrityError`，向调用方报告输入或运行失败。
如果“调用 `fullmatch` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `StaleCommandSelectionError`，向调用方报告输入或运行失败。
如果“调用 `compare_digest` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `StaleCommandSelectionError`，向调用方报告输入或运行失败。
如果选中候选项的索引不小于候选运行命令集合 的长度，就拒绝继续处理并抛出 `CommandSelectionValidationError`，向调用方报告输入或运行失败。
调用 `normalize_command_edits` 解析、规范化或转换当前输入，并把结果记为 该调用返回的结果；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `apply_command_edits`

- **源码**：`app/command_selection.py:204`
- **签名**：`def apply_command_edits(run_commands: list[dict[str, Any]], edits: list[CommandEdit]) -> list[dict[str, Any]]`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，纯函数：复制候选列表，并只替换允许修改的 command 字段。该函数接收候选运行命令集合、命令修改项集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_commands` | `list[dict[str, Any]]` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `edits` | `list[CommandEdit]` | 命令修改项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[dict[str, Any]]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
调用 `normalize_command_edits` 解析、规范化或转换当前输入，并把结果记为 该调用返回的结果；调用 `deepcopy` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为编辑文本，然后读取当前命令，并保存为 当前处理结果中的对应字段中的对应字段。
返回前一步处理得到的结果。
```

### `app/execution/base.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ExecutionRuntimeContext.ownership_token_hash`

- **源码**：`app/execution/base.py:40`
- **签名**：`def ownership_token_hash(self) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
加载这一步需要的外部依赖；计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `ExecutionRunner.__init__`

- **源码**：`app/execution/base.py:51`
- **签名**：`def __init__(self: 未显式标注, profile: ExecutionProfile, secret_service: SecretService | None) -> None（隐式）`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收MCP Client 配置档案、凭据，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `secret_service` | `SecretService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 MCP Client 配置档案、凭据 分别保存到同名实例字段；构造 `ProcessSupervisor` 结构化领域对象，并把结果记为 进程监督器。
```

#### `ExecutionRunner.build_host_command`

- **源码**：`app/execution/base.py:62`
- **签名**：`def build_host_command(self: 未显式标注, program: str, args: list[str]) -> list[str]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，把目标命令转换成宿主机实际启动的 token 列表。该函数接收待启动实验程序、命令行或函数位置参数集合，用于作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `program` | `str` | 待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
不执行额外操作
返回，无业务值
```

#### `ExecutionRunner.validate_cwd`

- **源码**：`app/execution/base.py:69`
- **签名**：`def validate_cwd(self, cwd: str) -> Path`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收命令执行工作目录，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `cwd` | `str` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 根目录；将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 解析后的。
如果解析后的不等于根目录 且 根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“检查解析后的的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
返回解析后的的当前值。
```

#### `ExecutionRunner.run`

- **源码**：`app/execution/base.py:87`
- **签名**：`def run(self: 未显式标注, action: dict[str, Any], run_dir: str, stage: str, runtime_context: ExecutionRuntimeContext | None) -> dict[str, Any]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，正式 Action 必须重新经过 capability policy。该函数接收待执行复现动作、本次复现运行目录、流水线阶段、运行时上下文，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `action` | `dict[str, Any]` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `runtime_context` | `ExecutionRuntimeContext | None` | 名为 `runtime_context` 的 `ExecutionRuntimeContext | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
移除运行时上下文中的当前内容；复制、序列化或校验结构化领域对象，并把结果记为 解析后的结果；调用 `validate_cwd` 校验当前输入或状态，并把结果记为 解析后的；调用 `evaluate_action_capabilities` 完成该函数的一项辅助处理，并把结果记为 人工决策结果。
如果“当前处理结果有值或为真”不成立，就调用 `join` 完成该函数的一项辅助处理，并把结果记为 面向用户或日志的提示信息；返回包含 `ok`、`returncode`、`end_reason`、`stdout`、`stderr`、`combined_output`、`timeout`、`cancelled` 等字段的结构化映射。
计算根据字段和固定文本生成格式化文本，并保存为 执行记录的 ID；调用 `build_minimal_environment` 组装当前阶段需要的领域对象，并把结果记为 结果；调用 `build_host_command` 组装当前阶段需要的领域对象，并把结果记为 命令；通过进程监督器执行数据查询或命令，并把结果记为 阶段处理结果。
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `ExecutionRunner.probe`

- **源码**：`app/execution/base.py:164`
- **签名**：`def probe(self: 未显式标注, program: str, args: list[str], cwd: str, run_dir: str, stage: str, timeout_seconds: int) -> dict[str, Any]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，受信任的内部探测也使用最小环境和 Supervisor。该函数接收待启动实验程序、命令行或函数位置参数集合、命令执行工作目录、本次复现运行目录等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `program` | `str` | 待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `cwd` | `str` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `timeout_seconds` | `int` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。；默认 15 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `validate_cwd` 校验当前输入或状态，并把结果记为 解析后的；构造 `ExecutableAction` 结构化领域对象，并把结果记为 该调用返回的结果；计算根据字段和固定文本生成格式化文本，并保存为 执行记录的 ID；调用 `build_minimal_environment` 组装当前阶段需要的领域对象，并把结果记为 结果。
复制、序列化或校验结构化领域对象，并把结果记为 模型或实验资源预算；通过进程监督器执行数据查询或命令，并把结果记为 阶段处理结果；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `ExecutionRunner.which`

- **源码**：`app/execution/base.py:244`
- **签名**：`def which(self: 未显式标注, program: str, cwd: str, run_dir: str) -> tuple[str | None, dict[str, Any]]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，在目标环境中解析程序，并返回对应 probe result。该函数接收待启动实验程序、命令执行工作目录、本次复现运行目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `program` | `str` | 待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。 |
| `cwd` | `str` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`tuple[str | None, dict[str, Any]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 当前处理结果；调用 `probe` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果“阶段处理结果中的对应字段有值或为真”不成立，就返回当前构造的顺序或去重集合。
去除阶段处理结果中的对应字段的首尾空白，并把规范化后的文本记为 解析后的值；返回当前构造的顺序或去重集合。
```

### `app/execution/cancellation.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/execution/cancellation.py:14`
- **签名**：`def utc_now() -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `require_control_dir`

- **源码**：`app/execution/cancellation.py:18`
- **签名**：`def require_control_dir(run_dir: str | Path) -> Path`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收本次复现运行目录，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
调用 `require_managed_run_root` 完成该函数的一项辅助处理，并把结果记为 运行产物根目录；将当前输入内容规范化为受控的绝对路径，并把结果记为 当前处理结果的目录。
如果运行产物根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
创建当前处理结果的目录对应的目录；返回当前处理结果的目录的当前值。
```

#### `atomic_write_json`

- **源码**：`app/execution/cancellation.py:28`
- **签名**：`def atomic_write_json(path: Path, payload: Any) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收文件或目录路径、结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `payload` | `Any` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
创建父级目录或父领域对象对应的目录；调用 `with_name` 完成该函数的一项辅助处理，并把结果记为 临时的路径；将结构化内容序列化或编码为可传输表示，并把结果记为 待处理数据。
先尝试完成以下处理：
    在上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给文件”中向终端或输出流写出当前结果/诊断信息；提交文件中已完成的数据变更；调用 `fsync` 完成该函数的一项辅助处理，退出时自动清理资源。
    调用 `replace` 完成该函数的一项辅助处理。
无论成功还是失败，最后都要：
    如果“检查临时的路径的文件系统属性”后得到肯定结果，就调用 `unlink` 完成该函数的一项辅助处理。
```

#### `runtime_record_path`

- **源码**：`app/execution/cancellation.py:54`
- **签名**：`def runtime_record_path(run_dir: str | Path, execution_id: str) -> Path`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收本次复现运行目录、执行记录的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `execution_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果执行记录的 ID为空或为假 或 前一步操作返回对象的对象名称不等于执行记录的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前计算得到的结果。
```

#### `cancel_request_path`

- **源码**：`app/execution/cancellation.py:65`
- **签名**：`def cancel_request_path(run_dir: str | Path, execution_id: str) -> Path`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收本次复现运行目录、执行记录的 ID，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `execution_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果执行记录的 ID为空或为假 或 前一步操作返回对象的对象名称不等于执行记录的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前计算得到的结果。
```

#### `write_runtime_record`

- **源码**：`app/execution/cancellation.py:76`
- **签名**：`def write_runtime_record(run_dir: str | Path, execution_id: str, payload: dict[str, Any]) -> Path`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收本次复现运行目录、执行记录的 ID、结构化请求载荷，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `execution_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `payload` | `dict[str, Any]` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
调用 `runtime_record_path` 完成该函数的一项辅助处理，并把结果记为 文件或目录路径；调用 `atomic_write_json` 完成该函数的一项辅助处理；返回文件或目录路径的当前值。
```

#### `read_cancel_request`

- **源码**：`app/execution/cancellation.py:87`
- **签名**：`def read_cancel_request(run_dir: str | Path, execution_id: str) -> CancellationRequest | None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收本次复现运行目录、执行记录的 ID，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终标注为 `CancellationRequest | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `execution_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`CancellationRequest | None`
- **语义**：返回 `CancellationRequest | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `cancel_request_path` 完成该函数的一项辅助处理，并把结果记为 文件或目录路径。
如果“检查文件或目录路径的文件系统属性”后未得到肯定结果，就返回固定值 `空值`。
调用 `model_validate_json` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `list_runtime_records`

- **源码**：`app/execution/cancellation.py:100`
- **签名**：`def list_runtime_records(run_dir: str | Path) -> list[dict[str, Any]]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收本次复现运行目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`list[dict[str, Any]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `require_control_dir` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的目录；将 领域记录集合 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为文件或目录路径：
    先尝试完成以下处理：
        将外部表示解析为结构化内容，并把结果记为 结构化请求载荷。
    如果出现 `(OSError, json.JSONDecodeError)`：
        跳过本轮剩余处理，直接进入下一轮。
    调用 `str` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷中的对应字段；把结构化请求载荷追加或合并到领域记录集合。
返回领域记录集合的当前值。
```

#### `request_run_cancellation`

- **源码**：`app/execution/cancellation.py:115`
- **签名**：`def request_run_cancellation(run_dir: str | Path, reason: str, requested_by: str) -> CancellationRequest`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，找到当前 run 唯一的 running/starting execution 并写取消请求。该函数接收本次复现运行目录、基线接受或运行操作原因、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CancellationRequest` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `requested_by` | `str` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。；默认 'cli' |

**输出**

- **Python 类型**：`CancellationRequest`
- **语义**：返回 `CancellationRequest` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果 的长度不等于1，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `str` 完成该函数的一项辅助处理，并把结果记为 执行记录的 ID。
如果执行记录的 ID为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
构造 `CancellationRequest` 结构化领域对象，并把结果记为 业务请求；调用 `atomic_write_json` 完成该函数的一项辅助处理；返回业务请求的当前值。
```

### `app/execution/capability_policy.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/execution/capability_policy.py:28`
- **签名**：`def utc_now() -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_within`

- **源码**：`app/execution/capability_policy.py:32`
- **签名**：`def _within(path: Path, roots: list[Path]) -> bool`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收文件或目录路径、受控扫描根目录集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `roots` | `list[Path]` | 受控扫描根目录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
检查由受控扫描根目录集合组成的集合或迭代器中是否存在满足“文件或目录路径等于受控扫描根目录 或 受控扫描根目录属于当前处理结果”的项，并返回处理结果。
```

#### `_violation`

- **源码**：`app/execution/capability_policy.py:36`
- **签名**：`def _violation(code: str, field: str, message: str) -> PolicyViolation`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收待解析或验证的代码、结构化对象字段、面向用户或日志的提示信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `PolicyViolation` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `code` | `str` | 待解析、执行或断言的代码文本；处理前应处于受控测试/执行边界内。 |
| `field` | `str` | 结构化对象字段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`PolicyViolation`
- **语义**：返回 `PolicyViolation` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `PolicyViolation` 结构化领域对象。
```

#### `_merge_effective_budget`

- **源码**：`app/execution/capability_policy.py:48`
- **签名**：`def _merge_effective_budget(profile_budget: ResourceBudget, action_timeout_seconds: int, override: ResourceBudgetOverride | None) -> tuple[ResourceBudget, list[PolicyViolation]]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，Action 的任何非空预算都只能小于等于 profile 上限。该函数接收配置、当前处理结果、覆盖默认配置的字段，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile_budget` | `ResourceBudget` | 名为 `profile_budget` 的 `ResourceBudget` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `action_timeout_seconds` | `int` | 名为 `action_timeout_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `override` | `ResourceBudgetOverride | None` | 覆盖默认配置的字段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[ResourceBudget, list[PolicyViolation]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 约束违反项集合 初始化为空列表，用来收集后续结果；复制、序列化或校验结构化领域对象，并把结果记为 待处理的论文或源码材料。
如果当前处理结果大于最大时间集合，就把新的处理结果追加或合并到约束违反项集合；否则调用 `float` 完成该函数的一项辅助处理，并把结果记为 待处理的论文或源码材料中的对应字段。
如果覆盖默认配置的字段为空，就返回当前构造的顺序或去重集合。
复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 配置值。
    如果配置值不为空 且 当前字段值大于配置值，就把新的处理结果追加或合并到约束违反项集合；跳过本轮剩余处理，直接进入下一轮。
    读取当前字段值，并保存为 待处理的论文或源码材料中的对应字段。
计算数量、边界或类型判断结果，并把结果记为 待处理的论文或源码材料中的对应字段；返回当前构造的顺序或去重集合。
```

#### `evaluate_action_capabilities`

- **源码**：`app/execution/capability_policy.py:100`
- **签名**：`def evaluate_action_capabilities(raw_action: dict, profile: ExecutionProfile) -> CapabilityDecision`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，确定性检查 Action 的全部声明能力。该函数接收当前处理结果、MCP Client 配置档案，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CapabilityDecision` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `raw_action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`CapabilityDecision`
- **语义**：返回 `CapabilityDecision` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 待执行复现动作；调用 `compute_action_hash` 计算内容身份、分数或派生结果，并把结果记为 待执行复现动作的 Hash；将 约束违反项集合 初始化为空列表，用来收集后续结果；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 根目录。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 命令执行工作目录。
如果“调用 `_within` 完成该函数的一项辅助处理”后未得到肯定结果，就把新的处理结果追加或合并到约束违反项集合。
去除待启动实验程序的首尾空白，并把规范化后的文本记为 待启动实验程序。
如果前一步操作返回对象的对象名称不等于待启动实验程序：
    把新的处理结果追加或合并到约束违反项集合。
否则：
    如果待启动实验程序不属于辅助操作“构造临时集合、映射或轻量领域对象”的结果，就把新的处理结果追加或合并到约束违反项集合。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    遍历当前可迭代输入，每次把当前项记为测试或状态标记：
        如果测试或状态标记有值或为真 且 测试或状态标记属于当前处理结果，就把新的处理结果追加或合并到约束违反项集合。
从当前处理结果读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果“调用 `intersection` 完成该函数的一项辅助处理”后得到肯定结果，就把新的处理结果追加或合并到约束违反项集合。
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为原始内容的路径：
    将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 文件或目录路径；把新的处理结果追加或合并到当前处理结果。
    如果“调用 `_within` 完成该函数的一项辅助处理”后未得到肯定结果，就把新的处理结果追加或合并到约束违反项集合。
如果当前处理结果等于'outbound' 且 策略不等于'allow'，就把新的处理结果追加或合并到约束违反项集合。
遍历当前可迭代输入，每次把当前项记为映射键或对象字段名：
    如果“调用 `is_sensitive_env_name` 校验当前输入或状态”后得到肯定结果：
        把新的处理结果追加或合并到约束违反项集合。
    否则：
        如果映射键或对象字段名不属于键集合集合，就把新的处理结果追加或合并到约束违反项集合。
调用 `_merge_effective_budget` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果最大记忆的字节内容不为空 且 模型或检索后端属于{'local', 'conda'}，就把新的处理结果追加或合并到约束违反项集合。
把违反项集合集合追加或合并到约束违反项集合；构造 `ActionCapabilityRequest` 结构化领域对象，并把结果记为 业务请求。
如果约束违反项集合有值或为真：
    计算使用固定配置或常量值，并保存为 等级；计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 基线接受或运行操作原因。
否则：
    如果当前处理结果等于'outbound' 或 当前处理结果有值或为真 或 待启动实验程序不属于当前处理结果 或 当前处理结果有值或为真，就计算根据条件从两个候选结果中选择一个，并保存为 等级；计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 基线接受或运行操作原因；否则计算使用固定配置或常量值，并保存为 等级；计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 基线接受或运行操作原因。
构造并返回 `CapabilityDecision` 结构化领域对象。
```

### `app/execution/conda_runner.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `CondaRunner.build_host_command`

- **源码**：`app/execution/conda_runner.py:11`
- **签名**：`def build_host_command(self: 未显式标注, program: str, args: list[str]) -> list[str]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收待启动实验程序、命令行或函数位置参数集合，用于作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `program` | `str` | 待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
读取当前处理结果，并保存为 后续步骤使用的结果；读取当前处理结果，并保存为 后续步骤使用的结果。
如果当前处理结果为空或为假 或 当前处理结果为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 当前处理结果的路径；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 目录树缩进前缀的路径。
如果“检查当前处理结果的路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
如果“检查目录树缩进前缀的路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
返回当前构造的顺序或去重集合。
```

### `app/execution/container_engine.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `ContainerEngine.probe`

- **源码**：`app/execution/container_engine.py:31`
- **签名**：`def probe(self) -> RuntimeProbe`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，检测 runtime、rootless 模式和 cgroup 版本。该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RuntimeProbe` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`RuntimeProbe`
- **语义**：返回 `RuntimeProbe` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ContainerEngine.image_exists`

- **源码**：`app/execution/container_engine.py:35`
- **签名**：`def image_exists(self, image_ref: str) -> bool`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，检查 digest-pinned image 是否已存在于本机。该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `image_ref` | `str` | 名为 `image_ref` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ContainerEngine.create`

- **源码**：`app/execution/container_engine.py:39`
- **签名**：`def create(self, tokens: list[str]) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，返回完整 container ID；此方法不能启动容器。该函数接收模型 token 用量，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `tokens` | `list[str]` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ContainerEngine.start_attach`

- **源码**：`app/execution/container_engine.py:43`
- **签名**：`def start_attach(self, container_id: str) -> int`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，阻塞等待 attach client，返回 CLI exit code，不代表容器 exit code。该函数接收当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `container_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ContainerEngine.inspect`

- **源码**：`app/execution/container_engine.py:47`
- **签名**：`def inspect(self, container_id: str) -> ContainerInspect`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，返回容器当前状态的结构化投影。该函数接收当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ContainerInspect` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `container_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ContainerInspect`
- **语义**：返回 `ContainerInspect` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ContainerEngine.stop`

- **源码**：`app/execution/container_engine.py:51`
- **签名**：`def stop(self, container_id: str, timeout_seconds: float) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，按精确 container ID 停止容器。该函数接收当前处理结果的 ID、等待超时时间（秒），用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `container_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

#### `ContainerEngine.remove`

- **源码**：`app/execution/container_engine.py:55`
- **签名**：`def remove(self, container_id: str) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，移除已停止的容器；不使用 --force。该函数接收当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `container_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
仅声明接口契约，这里没有具体实现。
```

### `app/execution/container_plan.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_sha256_text`

- **源码**：`app/execution/container_plan.py:34`
- **签名**：`def _sha256_text(value: str) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `build_container_plan`

- **源码**：`app/execution/container_plan.py:38`
- **签名**：`def build_container_plan(action: ExecutableAction, profile: ExecutionProfile, binding: WorkspaceBinding, job_id: str, run_id: str) -> ContainerPlan`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，把已审批 Action 映射为固定容器视图。该函数接收待执行复现动作、MCP Client 配置档案、资源绑定记录、复现任务 ID等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ContainerPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `ExecutableAction` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `binding` | `WorkspaceBinding` | 资源绑定记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `job_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ContainerPlan`
- **语义**：返回 `ContainerPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果模型或检索后端不等于'oci' 或 当前处理结果为空，就拒绝继续处理并抛出 `ContainerPolicyViolation`，向调用方报告输入或运行失败。
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 仓库根目录；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 运行产物根目录；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    把当前处理结果转换为稳定的仓库相对路径表示，并把结果记为 相对。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ContainerPolicyViolation`，向调用方报告输入或运行失败。
计算初始化顺序集合，并保存为 实验程序命令行参数序列。
如果“对实验程序命令行参数序列中的对应字段中的文本执行规范化或拆分”后未得到肯定结果，就拒绝继续处理并抛出 `ContainerPolicyViolation`，向调用方报告输入或运行失败。
调用 `_sha256_text` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 Hash；读取前一步操作返回对象中的对应字段，并保存为 任务；计算根据字段和固定文本生成格式化文本，并保存为 对象名称；计算按字段初始化键值映射，并保存为 当前处理结果。
遍历并筛选输入，将整理后的结果保存为 进程环境变量映射；构造并返回 `ContainerPlan` 结构化领域对象。
```

#### `build_podman_create_tokens`

- **源码**：`app/execution/container_plan.py:119`
- **签名**：`def build_podman_create_tokens(plan: ContainerPlan) -> list[str]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，将 ``ContainerPlan`` 编译成固定 Podman ``create`` token 列表。该函数接收实验计划，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `plan` | `ContainerPlan` | 实验计划；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算初始化顺序集合，并保存为 模型 token 用量。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为多个解包结果，然后把新的处理结果追加或合并到模型 token 用量。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为当前处理结果，然后把新的处理结果追加或合并到模型 token 用量。
遍历辅助操作产生的可迭代结果（按稳定规则整理结果顺序），每次把当前项记为多个解包结果，然后把新的处理结果追加或合并到模型 token 用量。
把新的处理结果追加或合并到模型 token 用量；返回模型 token 用量的当前值。
```

#### `plan_sha256`

- **源码**：`app/execution/container_plan.py:169`
- **签名**：`def plan_sha256(plan: ContainerPlan) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，确定性哈希；同一 plan 始终得到同一 sha256。该函数接收实验计划，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `plan` | `ContainerPlan` | 实验计划；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并把结果记为 结构化请求载荷；调用 `_sha256_text` 计算内容身份、分数或派生结果，并返回处理结果。
```

### `app/execution/container_reconcile.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_now_iso`

- **源码**：`app/execution/container_reconcile.py:27`
- **签名**：`def _now_iso() -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ContainerReconciler.__init__`

- **源码**：`app/execution/container_reconcile.py:34`
- **签名**：`def __init__(self, engine: ContainerEngine)`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收执行引擎，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `engine` | `ContainerEngine` | 执行引擎；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 执行引擎 分别保存到同名实例字段。
```

#### `ContainerReconciler.reconcile`

- **源码**：`app/execution/container_reconcile.py:37`
- **签名**：`def reconcile(self: 未显式标注, record: ContainerRuntimeRecord, run_dir: Path) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，检查容器当前状态并更新 record。该函数接收领域记录、本次复现运行目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `record` | `ContainerRuntimeRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `run_dir` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果当前状态属于{'removed', 'reconciliation_required'}，就返回固定值 `'already_terminal'`。
先尝试完成以下处理：
    调用 `inspect` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果出现 `Exception`：
    计算使用固定配置或常量值，并保存为 当前状态；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 更新时间；调用 `write_container_record` 持久化或更新当前领域数据；返回固定值 `'ambiguous_container_missing'`。
读取当前处理结果的 Hash，并保存为 期望；读取当前处理结果，并保存为 后续步骤使用的结果。
如果辅助操作“从当前处理结果读取所需的状态或领域记录”的结果不等于'true' 或 辅助操作“从当前处理结果读取所需的状态或领域记录”的结果不等于复现任务 ID 或 辅助操作“从当前处理结果读取所需的状态或领域记录”的结果不等于期望，就拒绝继续处理并抛出 `ContainerIdentityMismatch`，向调用方报告输入或运行失败。
如果当前处理结果有值或为真，就计算使用固定配置或常量值，并保存为 当前状态；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 更新时间；调用 `write_container_record` 持久化或更新当前领域数据；返回固定值 `'active_requires_ownership_check'`。
计算使用固定配置或常量值，并保存为 当前状态；读取实验进程退出码，并保存为 实验进程退出码；读取当前处理结果，并保存为 后续步骤使用的结果；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 更新时间。
调用 `write_container_record` 持久化或更新当前领域数据；返回固定值 `'exited_requires_job_reconciliation'`。
```

### `app/execution/container_records.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `record_path`

- **源码**：`app/execution/container_records.py:19`
- **签名**：`def record_path(run_dir: Path) -> Path`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，返回 ``<run_dir>/execution/container_runtime.json``。该函数接收本次复现运行目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `write_container_record`

- **源码**：`app/execution/container_records.py:25`
- **签名**：`def write_container_record(run_dir: Path, record: ContainerRuntimeRecord) -> Path`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，原子写入容器运行记录。该函数接收本次复现运行目录、领域记录，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `record` | `ContainerRuntimeRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
调用 `record_path` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象或业务目标；创建父级目录或父领域对象对应的目录；调用 `with_suffix` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；将结构化内容序列化或编码为可传输表示，并把结果记为 结构化请求载荷。
将处理结果写入当前处理结果指定的文件。
在上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `fsync` 完成该函数的一项辅助处理，退出时自动清理资源。
调用 `replace` 完成该函数的一项辅助处理；返回待定位的代码对象或业务目标的当前值。
```

#### `load_container_record`

- **源码**：`app/execution/container_records.py:53`
- **签名**：`def load_container_record(run_dir: Path) -> ContainerRuntimeRecord | None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，加载容器运行记录；不存在时返回 ``None``。该函数接收本次复现运行目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_dir` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`ContainerRuntimeRecord | None`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
调用 `record_path` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象或业务目标。
如果“检查待定位的代码对象或业务目标的文件系统属性”后未得到肯定结果，就返回固定值 `空值`。
调用 `model_validate_json` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/execution/container_supervisor.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_now_iso`

- **源码**：`app/execution/container_supervisor.py:40`
- **签名**：`def _now_iso() -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ContainerSupervisor.__init__`

- **源码**：`app/execution/container_supervisor.py:47`
- **签名**：`def __init__(self: 未显式标注, engine: ContainerEngine, telemetry: TelemetryPort | None) -> None（隐式）`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收执行引擎、运行观测数据，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `engine` | `ContainerEngine` | 执行引擎；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `telemetry` | `TelemetryPort | None` | 运行观测数据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 执行引擎 分别保存到同名实例字段。
先尝试完成以下处理：
    计算根据条件从两个候选结果中选择一个，并保存为 运行观测数据。
如果出现 `Exception`：
    加载这一步需要的外部依赖；构造 `NoOpTelemetry` 结构化领域对象，并把结果记为 运行观测数据。
```

#### `ContainerSupervisor._assert_owned`

- **源码**：`app/execution/container_supervisor.py:62`
- **签名**：`def _assert_owned(self: 未显式标注, record: ContainerRuntimeRecord, labels: dict[str, str]) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，验证 container ownership labels 与 record 一致。该函数接收领域记录、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `record` | `ContainerRuntimeRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `labels` | `dict[str, str]` | 名为 `labels` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 期望值。
如果辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理）中存在满足“辅助操作“从当前处理结果读取所需的状态或领域记录”的结果不等于当前字段值”的项，就拒绝继续处理并抛出 `ContainerIdentityMismatch`，向调用方报告输入或运行失败。
```

#### `ContainerSupervisor.execute`

- **源码**：`app/execution/container_supervisor.py:85`
- **签名**：`def execute(self: 未显式标注, plan: ContainerPlan, run_dir: Path) -> ContainerRuntimeRecord`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，主执行顺序：create -> record -> start -> inspect。该函数接收实验计划、本次复现运行目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `plan` | `ContainerPlan` | 实验计划；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `run_dir` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`ContainerRuntimeRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
读取运行观测数据，并保存为 运行观测数据；调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 读取起点；计算计算当前表达式的结果，并保存为 模型或检索后端；读取对象名称，并保存为 当前处理结果的名称。
先尝试完成以下处理：
    进入上下文“调用 `span` 完成该函数的一项辅助处理，并把上下文资源交给源码位置范围”，退出时自动清理资源：
        先尝试完成以下处理：
            调用 `build_podman_create_tokens` 组装当前阶段需要的领域对象，并把结果记为 模型 token 用量；调用 `create` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的 ID；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 当前时间；构造 `ContainerRuntimeRecord` 结构化领域对象，并把结果记为 领域记录。
            调用 `write_container_record` 持久化或更新当前领域数据；调用 `start_attach` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `inspect` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_assert_owned` 完成该函数的一项辅助处理。
            如果当前处理结果的 ID不等于当前处理结果的 ID，就拒绝继续处理并抛出 `ContainerIdentityMismatch`，向调用方报告输入或运行失败。
            如果当前处理结果有值或为真，就计算使用固定配置或常量值，并保存为 当前状态；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 更新时间；调用 `write_container_record` 持久化或更新当前领域数据；拒绝继续处理并抛出 `ContainerStateAmbiguous`，向调用方报告输入或运行失败。
            计算使用固定配置或常量值，并保存为 当前状态；读取实验进程退出码，并保存为 实验进程退出码；读取当前处理结果，并保存为 后续步骤使用的结果；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 更新时间。
            调用 `write_container_record` 持久化或更新当前领域数据；计算组合或计算已有值，并保存为 当前处理结果。
            先尝试完成以下处理：
                计算根据条件从两个候选结果中选择一个，并保存为 实验进程退出码；计算根据条件从两个候选结果中选择一个，并保存为 执行结论；调用 `histogram` 完成该函数的一项辅助处理。
            如果出现 `Exception`：
                不执行额外操作。
            返回领域记录的当前值。
        如果出现 `Exception`并把异常保存为捕获的异常对象：
            计算组合或计算已有值，并保存为 当前处理结果。
            先尝试完成以下处理：
                调用 `record_span_exception_safe` 完成该函数的一项辅助处理。
            如果出现 `Exception`：
                不执行额外操作。
            先尝试完成以下处理：
                调用 `histogram` 完成该函数的一项辅助处理。
            如果出现 `Exception`：
                不执行额外操作。
            重新抛出当前异常，保持原始失败信息。
如果出现 `Exception`：
    重新抛出当前异常，保持原始失败信息。
```

#### `ContainerSupervisor.stop_and_remove`

- **源码**：`app/execution/container_supervisor.py:183`
- **签名**：`def stop_and_remove(self: 未显式标注, record: ContainerRuntimeRecord, run_dir: Path) -> ContainerRuntimeRecord`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，按精确 ID 停止并移除容器。该函数接收领域记录、本次复现运行目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `record` | `ContainerRuntimeRecord` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `run_dir` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`ContainerRuntimeRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
先尝试完成以下处理：
    调用 `inspect` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果出现 `Exception`：
    计算使用固定配置或常量值，并保存为 当前状态；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 更新时间；调用 `write_container_record` 持久化或更新当前领域数据；返回领域记录的当前值。
如果当前处理结果有值或为真：
    计算使用固定配置或常量值，并保存为 当前状态；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 更新时间；调用 `write_container_record` 持久化或更新当前领域数据；调用 `stop` 完成该函数的一项辅助处理。
    调用 `inspect` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果有值或为真，就计算使用固定配置或常量值，并保存为 当前状态；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 更新时间；调用 `write_container_record` 持久化或更新当前领域数据；返回领域记录的当前值。
计算使用固定配置或常量值，并保存为 当前状态；读取实验进程退出码，并保存为 实验进程退出码；读取当前处理结果，并保存为 后续步骤使用的结果；调用 `_now_iso` 完成该函数的一项辅助处理，并把结果记为 更新时间。
调用 `write_container_record` 持久化或更新当前领域数据；调用 `remove` 完成该函数的一项辅助处理；返回领域记录的当前值。
```

### `app/execution/environment.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `is_sensitive_env_name`

- **源码**：`app/execution/environment.py:51`
- **签名**：`def is_sensitive_env_name(name: str) -> bool`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，按变量名拒绝 secret；不要把 secret 值写进错误消息。该函数接收对象名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 环境变量名称；用于从运行环境读取配置，而不是环境变量的实际值。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
计算数量、边界或类型判断结果，并返回处理结果。
```

#### `_validate_env_pair`

- **源码**：`app/execution/environment.py:57`
- **签名**：`def _validate_env_pair(name: str, value: str) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收对象名称、当前字段值，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 环境变量名称；用于从运行环境读取配置，而不是环境变量的实际值。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“调用 `fullmatch` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“调用 `is_sensitive_env_name` 校验当前输入或状态”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前输入内容属于当前字段值，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `_is_within`

- **源码**：`app/execution/environment.py:66`
- **签名**：`def _is_within(path: Path, roots: list[Path]) -> bool`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收文件或目录路径、受控扫描根目录集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `roots` | `list[Path]` | 受控扫描根目录集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
检查由受控扫描根目录集合组成的集合或迭代器中是否存在满足“文件或目录路径等于受控扫描根目录 或 受控扫描根目录属于当前处理结果”的项，并返回处理结果。
```

#### `_validate_path_list`

- **源码**：`app/execution/environment.py:70`
- **签名**：`def _validate_path_list(value: str, allowed_roots: list[Path], variable_name: str) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，校验 PATH/PYTHONPATH 一类路径列表。该函数接收当前字段值、当前处理结果、当前处理结果的名称，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `allowed_roots` | `list[Path]` | `list[Path]` 元素集合；元素代表的业务对象由参数名 `allowed_roots` 和调用位置确定。 |
| `variable_name` | `str` | 名为 `variable_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
将 规范化后的文本 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（对当前字段值中的文本执行规范化或拆分），每次把当前项记为处理项：
    如果处理项为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 待审核的 MCP 能力候选。
    如果“调用 `is_absolute` 校验当前输入或状态”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    将待审核的 MCP 能力候选规范化为受控的绝对路径，并把结果记为 解析后的值。
    如果当前处理结果的名称等于'PYTHONPATH' 且 “调用 `_is_within` 校验当前输入或状态”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到规范化后的文本。
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `build_minimal_environment`

- **源码**：`app/execution/environment.py:110`
- **签名**：`def build_minimal_environment(profile: ExecutionProfile, action: ExecutableAction, run_dir: str | Path, execution_id: str, secret_service: SecretService | None) -> EnvironmentBuildResult`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，从空字典构建论文程序环境，不再调用 os.environ.copy()。该函数接收MCP Client 配置档案、待执行复现动作、本次复现运行目录、执行记录的 ID等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `action` | `ExecutableAction` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `execution_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `secret_service` | `SecretService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。 |

**输出**

- **Python 类型**：`EnvironmentBuildResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `require_managed_run_root` 完成该函数的一项辅助处理，并把结果记为 运行产物根目录；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 根目录；计算初始化顺序集合，并保存为 当前处理结果。
如果当前处理结果有值或为真，就把新的处理结果追加或合并到当前处理结果。
将 进程环境变量映射 初始化为空映射，用来收集后续结果；将 键集合集合、配置键集合集合、键集合集合 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为映射键或对象字段名：
    如果映射键或对象字段名不属于键集合集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果“调用 `is_sensitive_env_name` 校验当前输入或状态”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    从当前处理结果读取所需的状态或领域记录，并把结果记为 当前字段值。
    如果当前字段值不为空，就调用 `_validate_env_pair` 校验当前输入或状态；读取当前字段值，并保存为 进程环境变量映射中的对应字段；把映射键或对象字段名追加或合并到键集合集合。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    如果映射键或对象字段名属于监督器键集合集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前字段值；调用 `_validate_env_pair` 校验当前输入或状态；读取当前字段值，并保存为 进程环境变量映射中的对应字段；把映射键或对象字段名追加或合并到配置键集合集合。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    如果映射键或对象字段名不属于键集合集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果映射键或对象字段名属于监督器键集合集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前字段值；调用 `_validate_env_pair` 校验当前输入或状态；读取当前字段值，并保存为 进程环境变量映射中的对应字段；把映射键或对象字段名追加或合并到键集合集合。
将当前输入内容规范化为受控的绝对路径，并把结果记为 运行时环境的目录。
如果运行产物根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 当前处理结果的目录；计算组合或计算已有值，并保存为 临时的目录；计算组合或计算已有值，并保存为 当前处理结果的目录；计算组合或计算已有值，并保存为 当前处理结果的目录。
遍历当前可迭代输入，每次把当前项记为当前处理结果，然后创建当前处理结果对应的目录。
把新的处理结果追加或合并到进程环境变量映射。
如果当前输入内容不属于进程环境变量映射，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `_validate_path_list` 校验当前输入或状态，并把结果记为 进程环境变量映射中的对应字段。
如果当前输入内容属于进程环境变量映射，就调用 `_validate_path_list` 校验当前输入或状态，并把结果记为 进程环境变量映射中的对应字段。
将 凭据键集合集合、当前处理结果 初始化为空列表，用来收集后续结果。
如果模型或检索后端等于'oci' 且 凭据集合有值或为真，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果凭据集合有值或为真 且 凭据为空，就加载这一步需要的外部依赖；调用 `build_secret_service` 组装当前阶段需要的领域对象，并把结果记为 凭据。
遍历当前可迭代输入，每次把当前项记为资源绑定记录：
    断言凭据不为空；不满足就终止当前测试或流程；读取进程环境变量映射的名称，并保存为 映射键或对象字段名。
    如果映射键或对象字段名不属于凭据键集合集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果映射键或对象字段名属于监督器键集合集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果映射键或对象字段名属于进程环境变量映射，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果“调用 `fullmatch` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    将凭据规范化为受控的绝对路径，并把结果记为 待处理的论文或源码材料；调用 `reveal` 完成该函数的一项辅助处理，并把结果记为 当前字段值。
    如果当前输入内容属于当前字段值，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    读取当前字段值，并保存为 进程环境变量映射中的对应字段；把映射键或对象字段名追加或合并到凭据键集合集合；把待处理的论文或源码材料追加或合并到当前处理结果。
构造并返回 `EnvironmentBuildResult` 结构化领域对象。
```

### `app/execution/local_runner.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `LocalRunner.build_host_command`

- **源码**：`app/execution/local_runner.py:9`
- **签名**：`def build_host_command(self: 未显式标注, program: str, args: list[str]) -> list[str]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收待启动实验程序、命令行或函数位置参数集合，用于作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `program` | `str` | 待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
返回当前构造的顺序或去重集合。
```

### `app/execution/oci_runner.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `OciRunner.__init__`

- **源码**：`app/execution/oci_runner.py:43`
- **签名**：`def __init__(self: 未显式标注, profile: ExecutionProfile, supervisor: ContainerSupervisor, secret_service: SecretService | None) -> None（隐式）`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收MCP Client 配置档案、进程监督器、凭据，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `supervisor` | `ContainerSupervisor` | 进程监督器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `secret_service` | `SecretService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `__init__` 完成该函数的一项辅助处理；把传入的 进程监督器 分别保存到同名实例字段。
```

#### `OciRunner.build_host_command`

- **源码**：`app/execution/oci_runner.py:54`
- **签名**：`def build_host_command(self: 未显式标注, program: str, args: list[str]) -> list[str]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收待启动实验程序、命令行或函数位置参数集合，用于作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `program` | `str` | 待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `OciRunner.run`

- **源码**：`app/execution/oci_runner.py:61`
- **签名**：`def run(self: 未显式标注, action: dict[str, Any], run_dir: str, stage: str, runtime_context: ExecutionRuntimeContext | None) -> dict[str, Any]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收待执行复现动作、本次复现运行目录、流水线阶段、运行时上下文，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `action` | `dict[str, Any]` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `runtime_context` | `ExecutionRuntimeContext | None` | 名为 `runtime_context` 的 `ExecutionRuntimeContext | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
如果运行时上下文为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
复制、序列化或校验结构化领域对象，并把结果记为 解析后的结果；调用 `evaluate_action_capabilities` 完成该函数的一项辅助处理，并把结果记为 人工决策结果。
如果“当前处理结果有值或为真”不成立，就调用 `join` 完成该函数的一项辅助处理，并把结果记为 面向用户或日志的提示信息；复制、序列化或校验结构化领域对象，并返回处理结果。
读取绑定，并保存为 资源绑定记录。
如果辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果不等于辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `build_container_plan` 组装当前阶段需要的领域对象，并把结果记为 实验计划；通过进程监督器执行数据查询或命令，并把结果记为 领域记录；计算根据条件从两个候选结果中选择一个，并保存为 原因；构造 `ExecutionResult` 结构化领域对象，并把结果记为 阶段处理结果。
计算计算当前表达式的结果，并保存为 当前处理结果。
如果当前处理结果有值或为真 且 当前状态等于'exited'，就调用 `stop_and_remove` 完成该函数的一项辅助处理。
复制、序列化或校验结构化领域对象，并返回处理结果。
```

### `app/execution/podman_engine.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `PodmanEngine.__init__`

- **源码**：`app/execution/podman_engine.py:24`
- **签名**：`def __init__(self, executable: str = "podman")`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `executable` | `str` | 名为 `executable` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'podman' |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把传入的 当前处理结果 分别保存到同名实例字段。
```

#### `PodmanEngine._run`

- **源码**：`app/execution/podman_engine.py:27`
- **签名**：`def _run(self: 未显式标注, timeout: float, *args: str) -> subprocess.CompletedProcess[str]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收等待超时时间、命令行或函数位置参数集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `subprocess.CompletedProcess[str]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `timeout` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。；默认 30.0 |
| `*args` | `str` | 额外位置参数序列。 |

**输出**

- **Python 类型**：`subprocess.CompletedProcess[str]`
- **语义**：返回 `subprocess.CompletedProcess[str]` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果不等于0，就读取前一步操作返回对象中的对应字段，并保存为 诊断或错误详情；拒绝继续处理并抛出 `ContainerRuntimeError`，向调用方报告输入或运行失败。
返回前一步处理得到的结果。
```

#### `PodmanEngine.probe`

- **源码**：`app/execution/podman_engine.py:48`
- **签名**：`def probe(self) -> RuntimeProbe`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RuntimeProbe` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`RuntimeProbe`
- **语义**：返回 `RuntimeProbe` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 补充诊断信息；将外部表示解析为结构化内容，并把结果记为 记录版本号；构造并返回 `RuntimeProbe` 结构化领域对象。
```

#### `PodmanEngine.image_exists`

- **源码**：`app/execution/podman_engine.py:74`
- **签名**：`def image_exists(self, image_ref: str) -> bool`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `image_ref` | `str` | 名为 `image_ref` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；返回比较判断结果。
```

#### `PodmanEngine.create`

- **源码**：`app/execution/podman_engine.py:84`
- **签名**：`def create(self, tokens: list[str]) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收模型 token 用量，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `tokens` | `list[str]` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
去除前一步操作返回对象的进程标准输出的首尾空白，并把规范化后的文本记为 当前处理结果的 ID。
如果当前处理结果的 ID 的长度小于12，就拒绝继续处理并抛出 `ContainerRuntimeError`，向调用方报告输入或运行失败。
返回当前处理结果的 ID的当前值。
```

#### `PodmanEngine.start_attach`

- **源码**：`app/execution/podman_engine.py:94`
- **签名**：`def start_attach(self, container_id: str) -> int`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `container_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；返回前一步处理得到的结果。
```

#### `PodmanEngine.inspect`

- **源码**：`app/execution/podman_engine.py:102`
- **签名**：`def inspect(self, container_id: str) -> ContainerInspect`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ContainerInspect` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `container_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`ContainerInspect`
- **语义**：返回 `ContainerInspect` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将外部表示解析为结构化内容，并把结果记为 数据库记录行集合。
如果数据库记录行集合 的长度不等于1，就拒绝继续处理并抛出 `ContainerRuntimeError`，向调用方报告输入或运行失败。
读取数据库记录行集合中的对应字段，并保存为 数据库记录行；从数据库记录行读取所需的状态或领域记录，并把结果记为 复现流程状态；从数据库记录行读取所需的状态或领域记录，并把结果记为 运行配置；调用 `str` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
构造并返回 `ContainerInspect` 结构化领域对象。
```

#### `PodmanEngine.stop`

- **源码**：`app/execution/podman_engine.py:127`
- **签名**：`def stop(self: 未显式标注, container_id: str, timeout_seconds: float) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前处理结果的 ID、等待超时时间（秒），用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `container_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_run` 完成该函数的一项辅助处理。
```

#### `PodmanEngine.remove`

- **源码**：`app/execution/podman_engine.py:137`
- **签名**：`def remove(self, container_id: str) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前处理结果的 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `container_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_run` 完成该函数的一项辅助处理。
```

### `app/execution/process_supervisor.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_redact_command_tokens`

- **源码**：`app/execution/process_supervisor.py:39`
- **签名**：`def _redact_command_tokens(tokens: list[str]) -> list[str]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，Process Record 保留命令结构，但隐藏常见 secret 参数值。该函数接收模型 token 用量，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tokens` | `list[str]` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
将 阶段处理结果 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 下一项。
遍历由模型 token 用量组成的集合或迭代器，每次把当前项记为模型或命令 token：
    对模型或命令 token中的文本执行规范化或拆分，并把结果记为 转为小写的比较文本。
    如果下一项有值或为真，就把新的处理结果追加或合并到阶段处理结果；计算使用固定配置或常量值，并保存为 下一项；跳过本轮剩余处理，直接进入下一轮。
    如果转为小写的比较文本属于当前处理结果，就把模型或命令 token追加或合并到阶段处理结果；计算使用固定配置或常量值，并保存为 下一项；跳过本轮剩余处理，直接进入下一轮。
    计算使用固定配置或常量值，并保存为 分配。
    遍历由当前处理结果组成的集合或迭代器，每次把当前项记为对象名称：
        计算组合或计算已有值，并保存为 目录树缩进前缀。
        如果“检查转为小写的比较文本是否满足文本匹配条件”后得到肯定结果，就把新的处理结果追加或合并到阶段处理结果；计算使用固定配置或常量值，并保存为 分配；立即结束当前循环。
    如果分配为空或为假，就把模型或命令 token追加或合并到阶段处理结果。
返回阶段处理结果的当前值。
```

#### `_process_group_exists`

- **源码**：`app/execution/process_supervisor.py:69`
- **签名**：`def _process_group_exists(pgid: int) -> bool`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收实验进程组 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pgid` | `int` | 实验进程组 ID；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
先尝试完成以下处理：
    调用 `killpg` 完成该函数的一项辅助处理。
如果出现 `ProcessLookupError`：
    返回固定值 `假`。
如果出现 `PermissionError`：
    返回固定值 `真`。
返回固定值 `真`。
```

#### `_terminate_process_group_final`

- **源码**：`app/execution/process_supervisor.py:80`
- **签名**：`def _terminate_process_group_final(process: subprocess.Popen[bytes], pgid: int, selector: selectors.BaseSelector, sinks: dict[str, BoundedLogSink], combined_sink: BoundedLogSink, grace_seconds: float) -> bool`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，即使 group leader 已经退出，也检查并终止仍存活的 PGID。该函数接收受监督的实验进程、实验进程组 ID、当前处理结果、日志或观测数据接收端集合等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `process` | `subprocess.Popen[bytes]` | 受监督的实验进程；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `pgid` | `int` | 实验进程组 ID；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `selector` | `selectors.BaseSelector` | 名为 `selector` 的 `selectors.BaseSelector` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `sinks` | `dict[str, BoundedLogSink]` | 日志或观测数据接收端集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `combined_sink` | `BoundedLogSink` | 名为 `combined_sink` 的 `BoundedLogSink` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `grace_seconds` | `float` | 名为 `grace_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
如果“调用 `_process_group_exists` 完成该函数的一项辅助处理”后未得到肯定结果，就返回固定值 `假`。
调用 `_signal_process_group` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 当前处理结果。
只要“调用 `_process_group_exists` 完成该函数的一项辅助处理”后得到肯定结果 且 辅助操作“调用 `monotonic` 完成该函数的一项辅助处理”的结果小于当前处理结果，就重复以下处理：
    调用 `_drain_ready_streams` 完成该函数的一项辅助处理。
    如果辅助操作“调用 `poll` 完成该函数的一项辅助处理”的结果为空，就调用 `poll` 完成该函数的一项辅助处理。
如果“调用 `_process_group_exists` 完成该函数的一项辅助处理”后未得到肯定结果，就返回固定值 `假`。
调用 `_signal_process_group` 完成该函数的一项辅助处理；返回固定值 `真`。
```

#### `ProcessTreeSampler.__init__`

- **源码**：`app/execution/process_supervisor.py:138`
- **签名**：`def __init__(self) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 当前处理结果的字节内容；计算使用固定配置或常量值，并保存为 当前处理结果的数量；将 身份、身份 初始化为空映射，用来收集后续结果；计算使用固定配置或常量值，并保存为 操作采样结果集合。
```

#### `ProcessTreeSampler.sample`

- **源码**：`app/execution/process_supervisor.py:149`
- **签名**：`def sample(self, root_pid: int) -> ResourceUsage`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ResourceUsage` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `root_pid` | `int` | 名为 `root_pid` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`ResourceUsage`
- **语义**：返回 `ResourceUsage` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
先尝试完成以下处理：
    构造 `Process` 结构化领域对象，并把结果记为 受控扫描根目录；计算初始化顺序集合，并保存为 当前处理结果。
如果出现 `(psutil.NoSuchProcess, psutil.AccessDenied)`：
    将 当前处理结果 初始化为空列表，用来收集后续结果。
计算使用固定配置或常量值，并保存为 当前集合；计算使用固定配置或常量值，并保存为 当前值的数量。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为受监督的实验进程：
    先尝试完成以下处理：
        计算组合多个值形成元组，并保存为 对象身份；将新的计算结果累加或合并到当前集合；将新的计算结果累加或合并到当前值的数量；调用 `cpu_times` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        调用 `float` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算数量、边界或类型判断结果，并把结果记为 身份中的对应字段。
        先尝试完成以下处理：
            调用 `int` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的字节内容。
        如果出现 `(AttributeError, NotImplementedError)`：
            计算使用固定配置或常量值，并保存为 当前处理结果的字节内容。
        计算数量、边界或类型判断结果，并把结果记为 身份中的对应字段。
    如果出现 `(psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess)`：
        跳过本轮剩余处理，直接进入下一轮。
计算数量、边界或类型判断结果，并把结果记为 当前处理结果的字节内容；计算数量、边界或类型判断结果，并把结果记为 当前处理结果的数量；将新的计算结果累加或合并到操作采样结果集合；构造并返回 `ResourceUsage` 结构化领域对象。
```

#### `budget_end_reason`

- **源码**：`app/execution/process_supervisor.py:213`
- **签名**：`def budget_end_reason(usage: ResourceUsage, budget: ResourceBudget) -> str | None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收模型或运行资源用量、模型或实验资源预算，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `usage` | `ResourceUsage` | 模型或运行资源用量；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `budget` | `ResourceBudget` | 模型或实验资源预算；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果最大记忆的字节内容不为空 且 当前处理结果的字节内容大于最大记忆的字节内容，就返回固定值 `'memory_limit'`。
如果当前处理结果的数量大于最大当前处理结果，就返回固定值 `'process_limit'`。
如果最大当前处理结果不为空 且 当前处理结果大于最大当前处理结果，就返回固定值 `'cpu_limit'`。
如果最大当前处理结果的字节内容不为空 且 当前处理结果的字节内容大于最大当前处理结果的字节内容，就返回固定值 `'write_limit'`。
返回固定值 `空值`。
```

#### `BoundedLogSink.__init__`

- **源码**：`app/execution/process_supervisor.py:243`
- **签名**：`def __init__(self: 未显式标注, path: Path, max_file_bytes: int, max_preview_bytes: int, stream_redactor: StreamingSecretRedactor | None) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收文件或目录路径、最大文件的字节内容、最大当前处理结果的字节内容、脱敏器，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `max_file_bytes` | `int` | 名为 `max_file_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_preview_bytes` | `int` | 名为 `max_preview_bytes` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `stream_redactor` | `StreamingSecretRedactor | None` | 名为 `stream_redactor` 的 `StreamingSecretRedactor | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
创建父级目录或父领域对象对应的目录；把传入的 文件或目录路径、最大文件的字节内容、最大当前处理结果的字节内容 分别保存到同名实例字段；计算使用固定配置或常量值，并保存为 字节数；计算使用固定配置或常量值，并保存为 字节数。
调用 `bytearray` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 当前处理结果；把传入参数保存到实例字段（脱敏器 → 敏感信息脱敏器）；调用 `open` 完成该函数的一项辅助处理，并把结果记为 文件。
```

#### `BoundedLogSink._write_safe`

- **源码**：`app/execution/process_supervisor.py:262`
- **签名**：`def _write_safe(self, data: bytes) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收待处理数据，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `data` | `bytes` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果待处理数据为空或为假，就结束当前函数，不返回业务值。
计算组合或计算已有值，并保存为 当前处理结果。
如果当前处理结果大于0，就把待处理数据中的对应字段追加或合并到当前处理结果。
计算组合或计算已有值，并保存为 文件。
如果文件大于0，就读取待处理数据中的对应字段，并保存为 检索文本块；向终端或输出流写出当前结果/诊断信息；将新的计算结果累加或合并到字节数。
```

#### `BoundedLogSink.consume`

- **源码**：`app/execution/process_supervisor.py:277`
- **签名**：`def consume(self, data: bytes) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收待处理数据，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `data` | `bytes` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果待处理数据为空或为假，就结束当前函数，不返回业务值。
将新的计算结果累加或合并到字节数；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；调用 `_write_safe` 持久化或更新当前领域数据。
如果字节数大于最大文件的字节内容，就计算使用固定配置或常量值，并保存为 当前处理结果。
```

#### `BoundedLogSink.close`

- **源码**：`app/execution/process_supervisor.py:290`
- **签名**：`def close(self) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果已关闭资源有值或为真，就结束当前函数，不返回业务值。
如果敏感信息脱敏器不为空，就调用 `_write_safe` 持久化或更新当前领域数据。
提交文件中已完成的数据变更；调用 `fsync` 完成该函数的一项辅助处理；关闭文件并释放相关资源。
```

#### `BoundedLogSink.preview_text`

- **源码**：`app/execution/process_supervisor.py:299`
- **签名**：`def preview_text(self) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
将外部表示解析为结构化内容，并返回处理结果。
```

#### `_signal_process_group`

- **源码**：`app/execution/process_supervisor.py:305`
- **签名**：`def _signal_process_group(pgid: int, sig: int) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，只接受 Supervisor 自己创建并记录的 PGID。该函数接收实验进程组 ID、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pgid` | `int` | 实验进程组 ID；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `sig` | `int` | 名为 `sig` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
先尝试完成以下处理：
    调用 `killpg` 完成该函数的一项辅助处理。
如果出现 `ProcessLookupError`：
    结束当前函数，不返回业务值。
```

#### `_drain_ready_streams`

- **源码**：`app/execution/process_supervisor.py:314`
- **签名**：`def _drain_ready_streams(selector: selectors.BaseSelector, sinks: dict[str, BoundedLogSink], combined_sink: BoundedLogSink, timeout: float) -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前处理结果、日志或观测数据接收端集合、当前处理结果、等待超时时间，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `selector` | `selectors.BaseSelector` | 名为 `selector` 的 `selectors.BaseSelector` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `sinks` | `dict[str, BoundedLogSink]` | 日志或观测数据接收端集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `combined_sink` | `BoundedLogSink` | 名为 `combined_sink` 的 `BoundedLogSink` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `timeout` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
遍历辅助操作产生的可迭代结果（调用 `select` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的名称。
    先尝试完成以下处理：
        调用 `read` 完成该函数的一项辅助处理，并把结果记为 待处理数据。
    如果出现 `BlockingIOError`：
        跳过本轮剩余处理，直接进入下一轮。
    如果待处理数据为空或为假：
        先尝试完成以下处理：
            调用 `unregister` 完成该函数的一项辅助处理。
        如果出现 `KeyError`：
            不执行额外操作。
        跳过本轮剩余处理，直接进入下一轮。
    调用 `consume` 完成该函数的一项辅助处理；调用 `consume` 完成该函数的一项辅助处理。
```

#### `_terminate_process_group`

- **源码**：`app/execution/process_supervisor.py:340`
- **签名**：`def _terminate_process_group(process: subprocess.Popen[bytes], pgid: int, selector: selectors.BaseSelector, sinks: dict[str, BoundedLogSink], combined_sink: BoundedLogSink, grace_seconds: float) -> bool`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，先 SIGTERM，继续 drain 日志；宽限期后仍存活则 SIGKILL。该函数接收受监督的实验进程、实验进程组 ID、当前处理结果、日志或观测数据接收端集合等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `process` | `subprocess.Popen[bytes]` | 受监督的实验进程；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `pgid` | `int` | 实验进程组 ID；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `selector` | `selectors.BaseSelector` | 名为 `selector` 的 `selectors.BaseSelector` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `sinks` | `dict[str, BoundedLogSink]` | 日志或观测数据接收端集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `combined_sink` | `BoundedLogSink` | 名为 `combined_sink` 的 `BoundedLogSink` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `grace_seconds` | `float` | 名为 `grace_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
如果辅助操作“调用 `poll` 完成该函数的一项辅助处理”的结果不为空，就返回固定值 `假`。
调用 `_signal_process_group` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 当前处理结果。
只要辅助操作“调用 `poll` 完成该函数的一项辅助处理”的结果为空 且 辅助操作“调用 `monotonic` 完成该函数的一项辅助处理”的结果小于当前处理结果，就重复调用 `_drain_ready_streams` 完成该函数的一项辅助处理。
如果辅助操作“调用 `poll` 完成该函数的一项辅助处理”的结果不为空，就返回固定值 `假`。
调用 `_signal_process_group` 完成该函数的一项辅助处理；返回固定值 `真`。
```

#### `ProcessSupervisor.execute`

- **源码**：`app/execution/process_supervisor.py:377`
- **签名**：`def execute(self: 未显式标注, request: SupervisedExecutionRequest, inherited_env_keys: list[str] | None, profile_env_keys: list[str] | None, action_env_keys: list[str] | None, secret_env_keys: list[str] | None, redactor: SecretRedactor | None) -> ExecutionResult`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收业务请求、键集合集合、配置键集合集合、键集合集合等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `request` | `SupervisedExecutionRequest` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `inherited_env_keys` | `list[str] | None` | `list[str] | None` 元素集合；元素代表的业务对象由参数名 `inherited_env_keys` 和调用位置确定。；默认 空值 |
| `profile_env_keys` | `list[str] | None` | `list[str] | None` 元素集合；元素代表的业务对象由参数名 `profile_env_keys` 和调用位置确定。；默认 空值 |
| `action_env_keys` | `list[str] | None` | `list[str] | None` 元素集合；元素代表的业务对象由参数名 `action_env_keys` 和调用位置确定。；默认 空值 |
| `secret_env_keys` | `list[str] | None` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。；默认 空值 |
| `redactor` | `SecretRedactor | None` | 敏感信息脱敏器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ExecutionResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
如果对象名称不等于'posix'，就拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
如果“命令有值或为真”不成立，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“调用 `isalnum` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
读取执行记录的 ID，并保存为 执行记录的 ID；将本次复现运行目录规范化为受控的绝对路径，并把结果记为 运行产物根目录；将当前输入内容规范化为受控的绝对路径，并把结果记为 尝试的目录。
如果运行产物根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
创建尝试的目录对应的目录；计算组合或计算已有值，并保存为 进程标准输出的路径；计算组合或计算已有值，并保存为 进程标准错误的路径；计算组合或计算已有值，并保存为 当前处理结果的路径。
计算组合或计算已有值，并保存为 记录的路径；构造 `BoundedLogSink` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `BoundedLogSink` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `BoundedLogSink` 结构化领域对象，并把结果记为 该调用返回的结果。
计算按字段初始化键值映射，并保存为 日志或观测数据接收端集合；调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `isoformat` 完成该函数的一项辅助处理，并把结果记为 运行启动时间；构造 `ProcessRecord` 结构化领域对象，并把结果记为 领域记录。
调用 `write_runtime_record` 持久化或更新当前领域数据；计算使用固定配置或常量值，并保存为 受监督的实验进程；构造 `DefaultSelector` 结构化领域对象，并把结果记为 该调用返回的结果；构造 `ProcessTreeSampler` 结构化领域对象，并把结果记为 该调用返回的结果。
构造 `ResourceUsage` 结构化领域对象，并把结果记为 模型或运行资源用量；计算使用固定配置或常量值，并保存为 原因；计算使用固定配置或常量值，并保存为 原因；计算使用固定配置或常量值，并保存为 当前处理结果。
计算使用固定配置或常量值，并保存为 当前处理结果。
先尝试完成以下处理：
    构造 `Popen` 结构化领域对象，并把结果记为 受监督的实验进程；断言进程标准输出不为空；不满足就终止当前测试或流程；断言进程标准错误不为空；不满足就终止当前测试或流程；调用 `set_blocking` 完成该函数的一项辅助处理。
    调用 `set_blocking` 完成该函数的一项辅助处理；调用 `register` 完成该函数的一项辅助处理；调用 `register` 完成该函数的一项辅助处理；调用 `getpgid` 完成该函数的一项辅助处理，并把结果记为 实验进程组 ID。
    调用 `create_time` 组装当前阶段需要的领域对象，并把结果记为 当前处理结果的时间；复制、序列化或校验结构化领域对象，并把结果记为 领域记录；调用 `write_runtime_record` 持久化或更新当前领域数据；计算使用固定配置或常量值，并保存为 当前处理结果。
    只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
        调用 `_drain_ready_streams` 完成该函数的一项辅助处理；调用 `poll` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_process_group_exists` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        如果当前处理结果不为空：
            如果当前处理结果为空或为假，就计算使用固定配置或常量值，并保存为 原因；立即结束当前循环。
            如果当前处理结果为空：
                调用 `monotonic` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
            否则：
                如果当前输入内容不小于当前处理结果，就计算使用固定配置或常量值，并保存为 原因；立即结束当前循环。
        如果当前处理结果为空：
            调用 `sample` 完成该函数的一项辅助处理，并把结果记为 模型或运行资源用量；调用 `budget_end_reason` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
            如果当前处理结果不为空，就读取当前处理结果，并保存为 原因；立即结束当前循环。
        调用 `read_cancel_request` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
        如果当前处理结果不为空，就计算使用固定配置或常量值，并保存为 原因；读取基线接受或运行操作原因，并保存为 原因；立即结束当前循环。
        计算组合或计算已有值，并保存为 当前处理结果。
        如果当前处理结果大于最大时间集合，就计算使用固定配置或常量值，并保存为 原因；立即结束当前循环。
    如果原因不等于'exited' 且 “调用 `_process_group_exists` 完成该函数的一项辅助处理”后得到肯定结果，就复制、序列化或校验结构化领域对象，并把结果记为 领域记录；调用 `write_runtime_record` 持久化或更新当前领域数据；调用 `_terminate_process_group_final` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
    先尝试完成以下处理：
        调用 `wait` 完成该函数的一项辅助处理。
    如果出现 `subprocess.TimeoutExpired`：
        如果“调用 `_process_group_exists` 完成该函数的一项辅助处理”后得到肯定结果，就调用 `_signal_process_group` 完成该函数的一项辅助处理；计算使用固定配置或常量值，并保存为 当前处理结果；读取当前处理结果，并保存为 后续步骤使用的结果。
        调用 `wait` 完成该函数的一项辅助处理。
    计算组合或计算已有值，并保存为 当前处理结果。
    只要“调用 `get_map` 读取或查询当前阶段需要的数据”后得到肯定结果 且 辅助操作“调用 `monotonic` 完成该函数的一项辅助处理”的结果小于当前处理结果，就重复调用 `_drain_ready_streams` 完成该函数的一项辅助处理。
    调用 `sample` 完成该函数的一项辅助处理，并把结果记为 模型或运行资源用量。
如果出现 `KeyboardInterrupt`：
    计算使用固定配置或常量值，并保存为 原因；计算使用固定配置或常量值，并保存为 原因。
    如果受监督的实验进程不为空 且 当前处理结果有值或为真：
        先尝试完成以下处理：
            调用 `getpgid` 完成该函数的一项辅助处理，并把结果记为 实验进程组 ID。
        如果出现 `ProcessLookupError`：
            读取当前处理结果，并保存为 实验进程组 ID。
        调用 `_terminate_process_group_final` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
如果出现 `OSError`并把异常保存为捕获的异常对象：
    计算使用固定配置或常量值，并保存为 原因；将结构化内容序列化或编码为可传输表示，并把结果记为 错误信息的字节内容；调用 `consume` 完成该函数的一项辅助处理；调用 `consume` 完成该函数的一项辅助处理。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    计算使用固定配置或常量值，并保存为 原因；将结构化内容序列化或编码为可传输表示，并把结果记为 错误信息的字节内容；调用 `consume` 完成该函数的一项辅助处理；调用 `consume` 完成该函数的一项辅助处理。
    如果受监督的实验进程不为空 且 辅助操作“调用 `poll` 完成该函数的一项辅助处理”的结果为空：
        先尝试完成以下处理：
            调用 `getpgid` 完成该函数的一项辅助处理，并把结果记为 实验进程组 ID。
        如果出现 `ProcessLookupError`：
            读取当前处理结果，并保存为 实验进程组 ID。
        调用 `_terminate_process_group_final` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
无论成功还是失败，最后都要：
    关闭当前处理结果并释放相关资源。
    遍历当前可迭代输入，每次把当前项记为日志或观测数据接收端，然后关闭日志或观测数据接收端并释放相关资源。
调用 `isoformat` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算组合或计算已有值，并保存为 当前处理结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
如果受监督的实验进程不为空 且 操作采样结果集合等于0，就调用 `sample` 完成该函数的一项辅助处理，并把结果记为 模型或运行资源用量。
复制、序列化或校验结构化领域对象，并把结果记为 领域记录；调用 `atomic_write_json` 完成该函数的一项辅助处理；调用 `write_runtime_record` 持久化或更新当前领域数据；调用 `preview_text` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
调用 `preview_text` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `preview_text` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算计算当前表达式的结果，并保存为 处理是否成功的判断；构造并返回 `ExecutionResult` 结构化领域对象。
```

### `app/execution/profile_store.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_require_absolute_path`

- **源码**：`app/execution/profile_store.py:12`
- **签名**：`def _require_absolute_path(value: str, field: str) -> Path`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收当前字段值、结构化对象字段，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `field` | `str` | 结构化对象字段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 文件或目录路径。
如果“调用 `is_absolute` 校验当前输入或状态”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
将文件或目录路径规范化为受控的绝对路径，并返回处理结果。
```

#### `_validate_execution_profile`

- **源码**：`app/execution/profile_store.py:23`
- **签名**：`def _validate_execution_profile(profile: ExecutionProfile) -> ExecutionProfile`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收MCP Client 配置档案，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `ExecutionProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`ExecutionProfile`
- **语义**：返回 `ExecutionProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_require_absolute_path` 完成该函数的一项辅助处理，并把结果记为 根目录。
如果“检查根目录的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
将辅助操作“将根目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 根目录；调用 `_require_absolute_path` 完成该函数的一项辅助处理，并把结果记为 Artifact根目录。
如果Artifact根目录不等于根目录 且 根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算使用固定配置或常量值，并保存为 当前处理结果。
如果当前处理结果有值或为真：
    调用 `_require_absolute_path` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果“检查当前处理结果的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    调用 `str` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
计算使用固定配置或常量值，并保存为 当前处理结果。
如果当前处理结果有值或为真：
    调用 `_require_absolute_path` 完成该函数的一项辅助处理，并把结果记为 目录树缩进前缀。
    如果“检查目录树缩进前缀的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    调用 `str` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；按稳定规则整理结果顺序，并把结果记为 键集合集合。
如果键集合集合有值或为真，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `load_execution_profiles`

- **源码**：`app/execution/profile_store.py:102`
- **签名**：`def load_execution_profiles(path: Path | None = None) -> dict[str, ExecutionProfile]`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收文件或目录路径，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path | None` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。；默认 空值 |

**输出**

- **Python 类型**：`dict[str, ExecutionProfile]`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 运行配置的路径。
如果“检查运行配置的路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
将外部表示解析为结构化内容，并把结果记为 结构化请求载荷；从结构化请求载荷读取所需的状态或领域记录，并把结果记为 该调用返回的结果；将 MCP Client 配置档案集合 初始化为空映射，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为配置：
    调用 `_validate_execution_profile` 校验当前输入或状态，并把结果记为 MCP Client 配置档案。
    如果MCP Client 配置档案 ID属于MCP Client 配置档案集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    读取MCP Client 配置档案，并保存为 MCP Client 配置档案集合中的对应字段。
返回MCP Client 配置档案集合的当前值。
```

#### `get_execution_profile`

- **源码**：`app/execution/profile_store.py:120`
- **签名**：`def get_execution_profile(profile_id: str) -> ExecutionProfile`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收MCP Client 配置档案 ID，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `ExecutionProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile_id` | `str` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。 |

**输出**

- **Python 类型**：`ExecutionProfile`
- **语义**：返回 `ExecutionProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `load_execution_profiles` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案集合；从MCP Client 配置档案集合读取所需的状态或领域记录，并把结果记为 MCP Client 配置档案。
如果MCP Client 配置档案为空，就计算计算当前表达式的结果，并保存为 当前处理结果；拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回MCP Client 配置档案的当前值。
```

#### `compute_execution_profile_fingerprint`

- **源码**：`app/execution/profile_store.py:133`
- **签名**：`def compute_execution_profile_fingerprint(profile: ExecutionProfile) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，所有能够改变执行权限或资源上限的字段都必须进入指纹。该函数接收MCP Client 配置档案，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 待处理的论文或源码材料；将结构化内容序列化或编码为可传输表示，并把结果记为 该调用返回的结果；计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `compute_execution_policy_hash`

- **源码**：`app/execution/profile_store.py:189`
- **签名**：`def compute_execution_policy_hash(profile: ExecutionProfile) -> str`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，只用于跨主机调度等价性的 hash。该函数接收MCP Client 配置档案，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 待处理的论文或源码材料；将结构化内容序列化或编码为可传输表示，并把结果记为 该调用返回的结果；计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

### `app/execution/registry.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `build_execution_runner`

- **源码**：`app/execution/registry.py:31`
- **签名**：`def build_execution_runner(profile: ExecutionProfile, engine: ContainerEngine | None, secret_service: SecretService | None) -> ExecutionRunner`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，根据受信任 profile 选择执行后端。该函数接收MCP Client 配置档案、执行引擎、凭据，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ExecutionRunner` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `engine` | `ContainerEngine | None` | 执行引擎；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `secret_service` | `SecretService | None` | 已注入的领域服务；封装业务规则并协调 Repository、Evidence Reader 或其他端口。；默认 空值 |

**输出**

- **Python 类型**：`ExecutionRunner`
- **语义**：返回 `ExecutionRunner` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果模型或检索后端等于'local'，就构造并返回 `LocalRunner` 结构化领域对象。
如果模型或检索后端等于'conda'，就构造并返回 `CondaRunner` 结构化领域对象。
如果模型或检索后端等于'oci'：
    如果当前处理结果为空，就拒绝继续处理并抛出 `ContainerRuntimeUnavailable`，向调用方报告输入或运行失败。
    如果执行引擎为空，就构造 `PodmanEngine` 结构化领域对象，并把结果记为 执行引擎。
    计算根据字段和固定文本生成格式化文本，并保存为 键。
    如果“从当前处理结果读取所需的状态或领域记录”后未得到肯定结果：
        调用 `probe` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `ContainerRuntimeUnavailable`，向调用方报告输入或运行失败。
        如果版本不属于{'v2', '2'}，就拒绝继续处理并抛出 `ContainerRuntimeUnavailable`，向调用方报告输入或运行失败。
        如果“调用 `image_exists` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ContainerRuntimeUnavailable`，向调用方报告输入或运行失败。
        计算使用固定配置或常量值，并保存为 当前处理结果中的对应字段。
    构造 `ContainerSupervisor` 结构化领域对象，并把结果记为 进程监督器；构造并返回 `OciRunner` 结构化领域对象。
拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `reset_probe_cache`

- **源码**：`app/execution/registry.py:95`
- **签名**：`def reset_probe_cache() -> None`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，测试辅助：清空 probe 缓存。该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `clear` 完成该函数的一项辅助处理。
```

### `app/graph.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `route_after_action_builder`

- **源码**：`app/graph.py:52`
- **签名**：`def route_after_action_builder(state: ReproductionState) -> Literal['risk_check', 'log_debug', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['risk_check', 'log_debug', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['risk_check', 'log_debug', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'risk_check'`。
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'log_debug'`。
返回固定值 `'final_report'`。
```

#### `route_after_risk_check`

- **源码**：`app/graph.py:63`
- **签名**：`def route_after_risk_check(state: ReproductionState) -> Literal['final_report', 'human_review', 'preflight_check']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['final_report', 'human_review', 'preflight_check']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['final_report', 'human_review', 'preflight_check']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果辅助操作“从复现流程状态读取所需的状态或领域记录”的结果等于'blocked'，就返回固定值 `'final_report'`。
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'human_review'`。
返回固定值 `'preflight_check'`。
```

#### `route_after_human_review`

- **源码**：`app/graph.py:74`
- **签名**：`def route_after_human_review(state: ReproductionState) -> Literal['preflight_check', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['preflight_check', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['preflight_check', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
从复现流程状态读取所需的状态或领域记录，并把结果记为 人工决策结果。
如果人工决策结果等于'approved'，就返回固定值 `'preflight_check'`。
返回固定值 `'final_report'`。
```

#### `route_after_preflight`

- **源码**：`app/graph.py:84`
- **签名**：`def route_after_preflight(state: ReproductionState) -> Literal['smoke_test', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['smoke_test', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['smoke_test', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'smoke_test'`。
返回固定值 `'final_report'`。
```

#### `route_after_smoke_test`

- **源码**：`app/graph.py:93`
- **签名**：`def route_after_smoke_test(state: ReproductionState) -> Literal['executor', 'log_debug', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['executor', 'log_debug', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['executor', 'log_debug', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
从复现流程状态读取所需的状态或领域记录，并把结果记为 当前状态。
如果当前状态属于{'passed', 'skipped'}，就返回固定值 `'executor'`。
如果当前状态等于'failed' 且 “从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'log_debug'`。
返回固定值 `'final_report'`。
```

#### `route_after_executor`

- **源码**：`app/graph.py:105`
- **签名**：`def route_after_executor(state: ReproductionState) -> Literal['execution_verifier', 'log_debug', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，新 Evidence 必须进入 Verifier；后两项只兼容旧 checkpoint。该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['execution_verifier', 'log_debug', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['execution_verifier', 'log_debug', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'execution_verifier'`。
如果辅助操作“从复现流程状态读取所需的状态或领域记录”的结果等于'failed' 且 “从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'log_debug'`。
返回固定值 `'final_report'`。
```

#### `route_after_execution_verifier`

- **源码**：`app/graph.py:130`
- **签名**：`def route_after_execution_verifier(state: ReproductionState) -> Literal['log_debug', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['log_debug', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['log_debug', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果辅助操作“从复现流程状态读取所需的状态或领域记录”的结果等于'failed' 且 “从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'log_debug'`。
返回固定值 `'final_report'`。
```

#### `route_after_repair_action_builder`

- **源码**：`app/graph.py:142`
- **签名**：`def route_after_repair_action_builder(state: ReproductionState) -> Literal['risk_check', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['risk_check', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['risk_check', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'risk_check'`。
返回固定值 `'final_report'`。
```

#### `route_after_log_debug`

- **源码**：`app/graph.py:151`
- **签名**：`def route_after_log_debug(state: ReproductionState) -> Literal['repair_planner', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，command repair 和 file repair 使用独立预算。该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['repair_planner', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['repair_planner', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
调用 `int` 完成该函数的一项辅助处理，并把结果记为 命令尝试记录集合集合；调用 `int` 完成该函数的一项辅助处理，并把结果记为 文件尝试记录集合集合；计算计算当前表达式的结果，并保存为 命令；计算计算当前表达式的结果，并保存为 文件。
如果命令有值或为真 或 文件有值或为真，就返回固定值 `'repair_planner'`。
返回固定值 `'final_report'`。
```

#### `route_after_repair_planner`

- **源码**：`app/graph.py:178`
- **签名**：`def route_after_repair_planner(state: ReproductionState) -> Literal['repair_action_builder', 'file_repair_planner', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['repair_action_builder', 'file_repair_planner', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['repair_action_builder', 'file_repair_planner', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
计算计算当前表达式的结果，并保存为 修复或重跑提案；计算计算当前表达式的结果，并保存为 命令。
如果命令有值或为真 且 辅助操作“从修复或重跑提案读取所需的状态或领域记录”的结果等于'edit_command' 且 “从修复或重跑提案读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'repair_action_builder'`。
如果文件有值或为真 且 辅助操作“从修复或重跑提案读取所需的状态或领域记录”的结果等于'manual_only' 且 “从当前输入内容读取所需的状态或领域记录”后得到肯定结果 且 辅助操作“调用 `int` 完成该函数的一项辅助处理”的结果小于最大文件尝试记录集合集合，就返回固定值 `'file_repair_planner'`。
返回固定值 `'final_report'`。
```

#### `route_after_file_repair_planner`

- **源码**：`app/graph.py:212`
- **签名**：`def route_after_file_repair_planner(state: ReproductionState) -> Literal['patch_builder', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['patch_builder', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['patch_builder', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
计算计算当前表达式的结果，并保存为 修复或重跑提案。
如果辅助操作“从修复或重跑提案读取所需的状态或领域记录”的结果等于'patch' 且 “从修复或重跑提案读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'patch_builder'`。
返回固定值 `'final_report'`。
```

#### `route_after_patch_builder`

- **源码**：`app/graph.py:223`
- **签名**：`def route_after_patch_builder(state: ReproductionState) -> Literal['patch_review', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['patch_review', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['patch_review', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果 且 “从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'patch_review'`。
返回固定值 `'final_report'`。
```

#### `route_after_patch_review`

- **源码**：`app/graph.py:233`
- **签名**：`def route_after_patch_review(state: ReproductionState) -> Literal['patch_verification_executor', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['patch_verification_executor', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['patch_verification_executor', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果辅助操作“从复现流程状态读取所需的状态或领域记录”的结果等于'approved'，就返回固定值 `'patch_verification_executor'`。
返回固定值 `'final_report'`。
```

#### `route_after_patch_verification_executor`

- **源码**：`app/graph.py:243`
- **签名**：`def route_after_patch_verification_executor(state: ReproductionState) -> Literal['patch_verdict', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['patch_verdict', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['patch_verdict', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'patch_verdict'`。
返回固定值 `'final_report'`。
```

#### `route_after_patch_verdict`

- **源码**：`app/graph.py:253`
- **签名**：`def route_after_patch_verdict(state: ReproductionState) -> Literal['patch_promotion_review', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['patch_promotion_review', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['patch_promotion_review', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
计算计算当前表达式的结果，并保存为 MCP 评测或运行报告。
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果 且 辅助操作“从MCP 评测或运行报告读取所需的状态或领域记录”的结果等于'behaviorally_verified' 且 辅助操作“从MCP 评测或运行报告读取所需的状态或领域记录”的结果是真，就返回固定值 `'patch_promotion_review'`。
返回固定值 `'final_report'`。
```

#### `route_after_patch_verifier`

- **源码**：`app/graph.py:269`
- **签名**：`def route_after_patch_verifier(state: ReproductionState) -> Literal['patch_promotion_review', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['patch_promotion_review', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['patch_promotion_review', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
调用 `route_after_patch_verdict` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `route_after_patch_promotion_review`

- **源码**：`app/graph.py:275`
- **签名**：`def route_after_patch_promotion_review(state: ReproductionState) -> Literal['patch_apply', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['patch_apply', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['patch_apply', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
如果辅助操作“从复现流程状态读取所需的状态或领域记录”的结果等于'approved'，就返回固定值 `'patch_apply'`。
返回固定值 `'final_report'`。
```

#### `route_after_patch_apply`

- **源码**：`app/graph.py:285`
- **签名**：`def route_after_patch_apply(state: ReproductionState) -> Literal['risk_check', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['risk_check', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['risk_check', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
计算计算当前表达式的结果，并保存为 领域记录。
如果辅助操作“从领域记录读取所需的状态或领域记录”的结果等于'applied' 且 “从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回固定值 `'risk_check'`。
返回固定值 `'final_report'`。
```

#### `route_to_next_or_final`

- **源码**：`app/graph.py:295`
- **签名**：`def route_to_next_or_final(state: ReproductionState, next_node: str) -> str`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，早期线性节点发生 terminal StageError 时统一转 Final Report。该函数接收复现流程状态、下一项，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `next_node` | `str` | 名为 `next_node` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
返回下一项的当前值。
```

#### `route_after_run_context`

- **源码**：`app/graph.py:306`
- **签名**：`def route_after_run_context(state: ReproductionState) -> Literal['input_validation', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['input_validation', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['input_validation', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果，就返回固定值 `'final_report'`。
返回固定值 `'input_validation'`。
```

#### `route_after_input_validation`

- **源码**：`app/graph.py:314`
- **签名**：`def route_after_input_validation(state: ReproductionState) -> Literal['paper_reader', 'final_report']`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于根据当前运行状态、证据完整性、风险等级或人工决策选择下一条复现流程路径，最终标注为 `Literal['paper_reader', 'final_report']` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReproductionState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Literal['paper_reader', 'final_report']`
- **语义**：返回 Graph 路由标签或受限枚举值，不是任意文本。

**伪代码**

```text
如果“调用 `has_terminal_stage_error` 校验当前输入或状态”后得到肯定结果 或 “从复现流程状态读取所需的状态或领域记录”后未得到肯定结果，就返回固定值 `'final_report'`。
返回固定值 `'paper_reader'`。
```

#### `build_graph`

- **源码**：`app/graph.py:324`
- **签名**：`def build_graph(*, checkpointer=None)`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收当前处理结果，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `checkpointer` | `未显式标注` | 名为 `checkpointer` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
构造 `StateGraph` 结构化领域对象，并把结果记为 领域对象构造器。
定义内部辅助函数 `add_guarded`，供当前函数在后续步骤中调用。
定义内部辅助函数 `add_role_guarded`，供当前函数在后续步骤中调用。
调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理。
调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理。
调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_role_guarded` 完成该函数的一项辅助处理；调用 `add_role_guarded` 完成该函数的一项辅助处理。
调用 `add_role_guarded` 完成该函数的一项辅助处理；调用 `add_role_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理。
调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理。
调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_role_guarded` 完成该函数的一项辅助处理；调用 `add_role_guarded` 完成该函数的一项辅助处理；调用 `add_role_guarded` 完成该函数的一项辅助处理。
调用 `add_role_guarded` 完成该函数的一项辅助处理；调用 `add_role_guarded` 完成该函数的一项辅助处理；调用 `add_role_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理。
调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_guarded` 完成该函数的一项辅助处理；调用 `add_edge` 完成该函数的一项辅助处理。
调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理。
遍历当前可迭代输入，每次把当前项记为多个解包结果，然后调用 `add_conditional_edges` 完成该函数的一项辅助处理。
调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理。
调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理。
调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理。
调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理。
调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_conditional_edges` 完成该函数的一项辅助处理；调用 `add_edge` 完成该函数的一项辅助处理；调用 `add_edge` 完成该函数的一项辅助处理。
计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；调用 `compile` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `build_graph.add_guarded`

- **源码**：`app/graph.py:328`
- **签名**：`def add_guarded(builder: StateGraph, name: str, node: Callable) -> None`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收领域对象构造器、对象名称、当前流程节点，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `builder` | `StateGraph` | 领域对象构造器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `node` | `Callable` | 可调用依赖；其参数和返回契约由类型标注限定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `add_node` 完成该函数的一项辅助处理。
```

#### `build_graph.add_role_guarded`

- **源码**：`app/graph.py:335`
- **签名**：`def add_role_guarded(builder: StateGraph, name: str, node: Callable, role: Literal['planner', 'executor', 'verifier']) -> None`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，先做 authority 校验，再由统一 Error Guard 捕获违规。该函数接收领域对象构造器、对象名称、当前流程节点、调用方职责角色，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `builder` | `StateGraph` | 领域对象构造器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `node` | `Callable` | 可调用依赖；其参数和返回契约由类型标注限定。 |
| `role` | `Literal['planner', 'executor', 'verifier']` | 调用方职责角色；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `role_guarded_node` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `add_node` 完成该函数的一项辅助处理。
```

### `app/memory/checkpoint.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_build_sqlite_checkpointer`

- **源码**：`app/memory/checkpoint.py:17`
- **签名**：`def _build_sqlite_checkpointer()`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
加载这一步需要的外部依赖；声明后续会读写外层作用域中的 当前处理结果；创建父级目录或父领域对象对应的目录；调用 `connect` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
通过当前处理结果执行数据查询或命令；通过当前处理结果执行数据查询或命令；通过当前处理结果执行数据查询或命令；构造并返回 `SqliteSaver` 结构化领域对象。
```

#### `_build_postgres_checkpointer`

- **源码**：`app/memory/checkpoint.py:44`
- **签名**：`def _build_postgres_checkpointer()`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖；加载这一步需要的外部依赖。
声明后续会读写外层作用域中的 当前处理结果；构造 `ConnectionPool` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `wait` 完成该函数的一项辅助处理；构造并返回 `PostgresSaver` 结构化领域对象。
```

#### `build_checkpointer`

- **源码**：`app/memory/checkpoint.py:81`
- **签名**：`def build_checkpointer()`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
声明后续会读写外层作用域中的 当前处理结果。
如果当前处理结果不为空，就返回前一步处理得到的结果。
进入上下文“读取当前处理结果的当前值”，退出时自动清理资源：
    如果当前处理结果不为空，就返回前一步处理得到的结果。
    如果当前处理结果等于'sqlite'：
        调用 `_build_sqlite_checkpointer` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
    否则：
        如果当前处理结果等于'postgresql'，就调用 `_build_postgres_checkpointer` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；否则拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    返回前一步处理得到的结果。
```

#### `setup_checkpointer`

- **源码**：`app/memory/checkpoint.py:104`
- **签名**：`def setup_checkpointer() -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，显式创建/升级 Saver 自有表；只由迁移 CLI 调用。该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_checkpointer` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `setup` 完成该函数的一项辅助处理。
```

#### `close_checkpointer`

- **源码**：`app/memory/checkpoint.py:111`
- **签名**：`def close_checkpointer() -> None`
- **作用**：在论文复现系统的基础配置、数据转换或公共支撑阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
声明后续会读写外层作用域中的 当前处理结果；声明后续会读写外层作用域中的 当前处理结果；声明后续会读写外层作用域中的 当前处理结果。
进入上下文“读取当前处理结果的当前值”，退出时自动清理资源：
    计算使用固定配置或常量值，并保存为 当前处理结果。
    如果当前处理结果不为空，就关闭当前处理结果并释放相关资源；计算使用固定配置或常量值，并保存为 当前处理结果。
    如果当前处理结果不为空，就关闭当前处理结果并释放相关资源；计算使用固定配置或常量值，并保存为 当前处理结果。
```

### `app/nodes/action_builder_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `action_builder_node`

- **源码**：`app/nodes/action_builder_node.py:8`
- **签名**：`def action_builder_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 已有。
如果已有有值或为真，就返回包含 `pending_action`、`pending_action_hash` 字段的结构化映射。
计算计算当前表达式的结果，并保存为 运行集合。
如果运行集合为空或为假，就返回包含 `pending_action`、`pending_action_hash`、`final_status` 字段的结构化映射。
从复现流程状态读取所需的状态或领域记录，并把结果记为 选中候选项的索引。
如果选中候选项的索引小于0 或 选中候选项的索引不小于运行集合 的长度，就返回包含 `pending_action`、`pending_action_hash`、`final_status`、`error` 字段的结构化映射。
读取运行集合中的对应字段，并保存为 命令；计算计算当前表达式的结果，并保存为 MCP Client 配置档案 ID。
先尝试完成以下处理：
    调用 `get_execution_profile` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 执行环境配置指纹；计算计算当前表达式的结果，并保存为 命令执行工作目录；调用 `build_run_action_from_command` 组装当前阶段需要的领域对象，并把结果记为 待执行复现动作。
如果出现 `(FileNotFoundError, KeyError, ValueError)`并把异常保存为捕获的异常对象：
    返回包含 `pending_action`、`pending_action_hash`、`final_status`、`error` 字段的结构化映射。
调用 `compute_action_hash` 计算内容身份、分数或派生结果，并把结果记为 待执行复现动作的 Hash；返回包含 `execution_profile_id`、`execution_profile_fingerprint`、`pending_action`、`pending_action_hash` 字段的结构化映射。
```

### `app/nodes/code_search_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_slug`

- **源码**：`app/nodes/code_search_node.py:44`
- **签名**：`def _slug(value: str) -> str`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
去除辅助操作“调用 `sub` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 当前处理结果；返回当前输入内容中的对应字段的当前值。
```

#### `_legacy_search_result`

- **源码**：`app/nodes/code_search_node.py:53`
- **签名**：`def _legacy_search_result(pack: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，保持旧 mapping/report fixture 可读取。该函数接收检索或映射证据包，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pack` | `dict` | 检索或映射证据包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 待处理项集合；返回包含 `keywords`、`matches`、`candidate_files`、`code_slices` 字段的结构化映射。
```

#### `_dense_flags`

- **源码**：`app/nodes/code_search_node.py:90`
- **签名**：`def _dense_flags(state: dict) -> tuple[bool, bool]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`tuple[bool, bool]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算数量、边界或类型判断结果，并把结果记为 功能是否启用的开关；计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果；返回当前构造的顺序或去重集合。
```

#### `_prepare_dense`

- **源码**：`app/nodes/code_search_node.py:109`
- **签名**：`def _prepare_dense(repo_path: str, index: 未显式标注, state: dict | None) -> tuple[PreparedDenseRetriever, dict]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收代码仓库根目录、当前候选项的索引、复现流程状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `str` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `index` | `未显式标注` | 候选集合中的零基索引，用于定位选中项；它不是业务 ID 或内容 Hash。 |
| `state` | `dict | None` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。；默认 空值 |

**输出**

- **Python 类型**：`tuple[PreparedDenseRetriever, dict]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果“当前处理结果有值或为真”不成立，就拒绝继续处理并抛出 `EmbeddingProviderError`，向调用方报告输入或运行失败。
调用 `build_semantic_chunks` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；计算计算当前表达式的结果，并保存为 本次运行状态；调用 `get_embedding_backend` 读取或查询当前阶段需要的数据，并把结果记为 模型或检索后端；构造 `SQLiteEmbeddingCache` 结构化领域对象，并把结果记为 该调用返回的结果。
调用 `prepare` 完成该函数的一项辅助处理，并把结果记为 证据检索器；返回当前构造的顺序或去重集合。
```

#### `_fallback_report`

- **源码**：`app/nodes/code_search_node.py:163`
- **签名**：`def _fallback_report(enabled: bool, required: bool, reason: str | None) -> DenseRetrievalReport`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收功能是否启用的开关、当前处理结果、基线接受或运行操作原因，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `DenseRetrievalReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `enabled` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `required` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `reason` | `str | None` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |

**输出**

- **Python 类型**：`DenseRetrievalReport`
- **语义**：返回 `DenseRetrievalReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `DenseRetrievalReport` 结构化领域对象。
```

#### `_mapping_targets`

- **源码**：`app/nodes/code_search_node.py:176`
- **签名**：`def _mapping_targets(state: dict) -> list[dict]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[dict]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `_policy_mode`

- **源码**：`app/nodes/code_search_node.py:185`
- **签名**：`def _policy_mode() -> RetrievalPolicyMode`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，Settings 已在启动时验证，这里只做类型收窄。该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RetrievalPolicyMode` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`RetrievalPolicyMode`
- **语义**：返回 `RetrievalPolicyMode` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回策略模式的当前值。
```

#### `_paper_evidence_count`

- **源码**：`app/nodes/code_search_node.py:191`
- **签名**：`def _paper_evidence_count(target: dict) -> int`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，只统计结构化 Evidence 项数，不解析或信任其自然语言内容。该函数接收待定位的代码对象或业务目标，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `target` | `dict` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 状态字段集合；调用 `sum` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_target_keywords`

- **源码**：`app/nodes/code_search_node.py:198`
- **签名**：`def _target_keywords(target: dict, target_name: str) -> list[str]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，保持当前节点的关键词构造顺序，并确定性去重。该函数接收待定位的代码对象或业务目标、待定位的代码对象或业务目标的名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `target` | `dict` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `target_name` | `str` | 名为 `target_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算初始化顺序集合，并保存为 状态字段集合；构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `_policy_decision`

- **源码**：`app/nodes/code_search_node.py:224`
- **签名**：`def _policy_decision(policy: RetrievalPolicyConfig, mode: RetrievalPolicyMode, target_payload: dict, lexical_query: str, keywords: list[str], dense_available: bool) -> RetrievalDecision`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，为一个 mapping target 生成不含 query 原文的 Decision。该函数接收安全策略、MCP 评测或运行模式、当前处理结果、查询等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `RetrievalDecision` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `policy` | `RetrievalPolicyConfig` | 安全策略；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `mode` | `RetrievalPolicyMode` | MCP 评测或运行模式；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `target_payload` | `dict` | 名为 `target_payload` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |
| `lexical_query` | `str` | 名为 `lexical_query` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `keywords` | `list[str]` | 用于精确检索或文件分类的关键词集合；匹配范围由当前工具决定。 |
| `dense_available` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`RetrievalDecision`
- **语义**：返回 `RetrievalDecision` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `build_query_features` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `select_retrieval_profile` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `code_search_node`

- **源码**：`app/nodes/code_search_node.py:249`
- **签名**：`def code_search_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 代码仓库根目录；调用 `_mapping_targets` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象集合。
如果代码仓库根目录为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
如果待定位的代码对象集合为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
先尝试完成以下处理：
    调用 `build_repository_index` 组装当前阶段需要的领域对象，并把结果记为 当前候选项的索引。
如果出现 `(FileNotFoundError, OSError)`并把异常保存为捕获的异常对象：
    调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算初始化顺序集合，并保存为 领域记录集合；调用 `_policy_mode` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行模式；计算使用固定配置或常量值，并保存为 安全策略。
计算使用固定配置或常量值，并保存为 安全策略的 SHA-256。
如果MCP 评测或运行模式不等于'off'：
    先尝试完成以下处理：
        调用 `load_retrieval_policy` 读取或查询当前阶段需要的数据，并把结果记为 安全策略；调用 `sha256_value` 计算内容身份、分数或派生结果，并把结果记为 安全策略的 SHA-256。
    如果出现 `(OSError, ValueError, KeyError)`并把异常保存为捕获的异常对象：
        调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `_dense_flags` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算使用固定配置或常量值，并保存为 检索器；计算使用固定配置或常量值，并保存为 原因；计算使用固定配置或常量值，并保存为 Manifest的路径。
计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 策略。
如果MCP 评测或运行模式等于'active' 且 安全策略不为空：
    遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
        调用 `str` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象或业务目标的名称；计算按字段初始化键值映射，并保存为 当前处理结果；调用 `_target_keywords` 完成该函数的一项辅助处理，并把结果记为 检索关键词集合；调用 `build_lexical_query` 组装当前阶段需要的领域对象，并把结果记为 查询。
        调用 `_policy_decision` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        如果当前处理结果有值或为真 且 当前处理结果有值或为真 且 当前输入内容不属于当前处理结果，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
        如果当前输入内容属于当前处理结果，就计算使用固定配置或常量值，并保存为 策略；立即结束当前循环。
    计算计算当前表达式的结果，并保存为 当前处理结果。
如果当前处理结果有值或为真：
    如果“当前处理结果有值或为真”不成立：
        计算使用固定配置或常量值，并保存为 原因。
        如果当前处理结果有值或为真，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
    否则：
        先尝试完成以下处理：
            调用 `_prepare_dense` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `str` 完成该函数的一项辅助处理，并把结果记为 Manifest的路径；把Manifest记录追加或合并到领域记录集合。
        如果出现 `(EmbeddingProviderError, OSError, ValueError)`并把异常保存为捕获的异常对象：
            计算根据字段和固定文本生成格式化文本，并保存为 原因。
            如果当前处理结果有值或为真，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
将 当前处理结果、当前处理结果、当前处理结果、策略集合、结果集合集合 初始化为空映射，用来收集后续结果。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    调用 `str` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象或业务目标的名称；调用 `str` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象或业务目标的 ID；调用 `str` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算按字段初始化键值映射，并保存为 当前处理结果。
    调用 `_target_keywords` 完成该函数的一项辅助处理，并把结果记为 检索关键词集合；调用 `build_lexical_query` 组装当前阶段需要的领域对象，并把结果记为 查询；计算使用固定配置或常量值，并保存为 人工决策结果。
    如果安全策略不为空，就调用 `_policy_decision` 完成该函数的一项辅助处理，并把结果记为 人工决策结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `str` 完成该函数的一项辅助处理，并把结果记为 策略集合中的对应字段；把记录追加或合并到领域记录集合。
    将 当前处理结果 初始化为空列表，用来收集后续结果；计算数量、边界或类型判断结果，并把结果记为 配置；计算数量、边界或类型判断结果，并把结果记为 该调用返回的结果。
    如果当前处理结果有值或为真：
        先尝试完成以下处理：
            调用 `build_semantic_query` 组装当前阶段需要的领域对象，并把结果记为 查询；调用 `rank` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
        如果出现 `(EmbeddingProviderError, OSError, ValueError)`并把异常保存为捕获的异常对象：
            计算根据字段和固定文本生成格式化文本，并保存为 基线接受或运行操作原因。
            如果当前处理结果有值或为真，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
            调用 `_fallback_report` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    否则：
        计算根据条件从两个候选结果中选择一个，并保存为 配置原因；调用 `_fallback_report` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    计算根据字段和固定文本生成格式化文本，并保存为 相对的路径；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前处理结果中的对应字段；把记录追加或合并到领域记录集合。
    计算根据条件从两个候选结果中选择一个，并保存为 配置；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
    先尝试完成以下处理：
        调用 `build_evidence_pack` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
    如果出现 `(SearchToolError, OSError, ValueError)`并把异常保存为捕获的异常对象：
        调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
    复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；计算根据字段和固定文本生成格式化文本，并保存为 仓库内相对路径；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；读取当前处理结果，并保存为 当前处理结果中的对应字段。
    调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前处理结果中的对应字段；调用 `_legacy_search_result` 完成该函数的一项辅助处理，并把结果记为 结果集合集合中的对应字段；把记录追加或合并到领域记录集合。
返回包含 `repo_index_path`、`semantic_index_manifest_path`、`dense_retrieval_report_paths`、`retrieval_policy_decision_paths`、`retrieval_policy_sha256`、`code_evidence_pack_paths`、`code_evidence_packs`、`code_search_results` 字段的结构化映射。
```

### `app/nodes/command_selection_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_render_run_commands_for_terminal`

- **源码**：`app/nodes/command_selection_node.py:26`
- **签名**：`def _render_run_commands_for_terminal(run_commands: list[dict]) -> None`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，该函数接收候选运行命令集合，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_commands` | `list[dict]` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
向终端或输出流写出当前结果/诊断信息。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    向终端或输出流写出当前结果/诊断信息；向终端或输出流写出当前结果/诊断信息；向终端或输出流写出当前结果/诊断信息；向终端或输出流写出当前结果/诊断信息。
    向终端或输出流写出当前结果/诊断信息。
```

#### `build_command_selection_template`

- **源码**：`app/nodes/command_selection_node.py:36`
- **签名**：`def build_command_selection_template(run_commands: list[dict]) -> dict`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，生成可直接用于恢复 command selection 的预填 JSON。该函数接收候选运行命令集合，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_commands` | `list[dict]` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
返回包含 `run_commands_hash`、`selected_index`、`edits` 字段的结构化映射。
```

#### `_write_command_selection_template`

- **源码**：`app/nodes/command_selection_node.py:52`
- **签名**：`def _write_command_selection_template(input_path: Path, run_commands: list[dict]) -> None`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，该函数接收输入内容的路径、候选运行命令集合，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `input_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_commands` | `list[dict]` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_command_selection_template` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；将处理结果写入输入内容的路径指定的文件。
```

#### `ensure_command_selection_input_file`

- **源码**：`app/nodes/command_selection_node.py:63`
- **签名**：`def ensure_command_selection_input_file(input_path: Path, run_commands: list[dict]) -> tuple[str, Path | None]`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，确保输入文件对应当前 run_commands。该函数接收输入内容的路径、候选运行命令集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `input_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_commands` | `list[dict]` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`tuple[str, Path | None]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
创建父级目录或父领域对象对应的目录。
如果“检查输入内容的路径的文件系统属性”后未得到肯定结果，就调用 `_write_command_selection_template` 持久化或更新当前领域数据；返回当前构造的顺序或去重集合。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 结构化请求载荷。
如果出现 `(json.JSONDecodeError, OSError)`：
    将 结构化请求载荷 初始化为空映射，用来收集后续结果。
调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果，并把结果记为 调用方看到的旧内容 Hash。
如果“计算数量、边界或类型判断结果”后得到肯定结果 且 辅助操作“从结构化请求载荷读取所需的状态或领域记录”的结果等于调用方看到的旧内容 Hash，就返回当前构造的顺序或去重集合。
调用 `strftime` 完成该函数的一项辅助处理，并把结果记为 状态事件时间戳；调用 `with_name` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的路径；调用 `copy2` 完成该函数的一项辅助处理；调用 `_write_command_selection_template` 持久化或更新当前领域数据。
返回当前构造的顺序或去重集合。
```

#### `_normalize_interrupt_response`

- **源码**：`app/nodes/command_selection_node.py:99`
- **签名**：`def _normalize_interrupt_response(response: object, expected_hash: str) -> CommandSelectionResponse`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，该函数接收结构化响应、调用方看到的旧内容 Hash，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `response` | `object` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `expected_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`CommandSelectionResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就复制、序列化或校验结构化领域对象，并返回处理结果。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就构造并返回 `CommandSelectionResponse` 结构化领域对象。
如果“计算数量、边界或类型判断结果”后得到肯定结果 且 “调用 `isdigit` 完成该函数的一项辅助处理”后得到肯定结果，就构造并返回 `CommandSelectionResponse` 结构化领域对象。
拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `command_selection_node`

- **源码**：`app/nodes/command_selection_node.py:120`
- **签名**：`def command_selection_node(state: dict) -> dict`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 候选运行命令集合。
如果候选运行命令集合为空或为假，就返回包含 `selected_run_command_index`、`edited_run_commands` 字段的结构化映射。
调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果，并把结果记为 调用方看到的旧内容 Hash；从复现流程状态读取所需的状态或领域记录，并把结果记为 当前处理结果的路径。
如果当前处理结果的路径为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
把外部位置解析为文件系统路径对象，并把结果记为 输入内容的路径；从复现流程状态读取所需的状态或领域记录，并把结果记为 状态；计算使用固定配置或常量值，并保存为 过期的路径；调用 `_render_run_commands_for_terminal` 完成该函数的一项辅助处理。
向终端或输出流写出当前结果/诊断信息；向终端或输出流写出当前结果/诊断信息。
如果状态等于'refreshed'，就向终端或输出流写出当前结果/诊断信息。
计算按字段初始化键值映射，并保存为 结构化请求载荷；调用 `interrupt` 完成该函数的一项辅助处理，并把结果记为 结构化响应；调用 `_normalize_interrupt_response` 解析、规范化或转换当前输入，并把结果记为 解析后的结果；调用 `validate_command_selection_response` 校验当前输入或状态，并把结果记为 解析后的结果。
调用 `apply_command_edits` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；构造 `CommandSelectionRecord` 结构化领域对象，并把结果记为 领域记录；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
返回包含 `selected_run_command_index`、`edited_run_commands`、`command_selection_record`、`pending_action`、`pending_action_hash`、`requires_approval`、`user_approval`、`human_feedback` 等字段的结构化映射。
```

#### `command_selection_prepare_node`

- **源码**：`app/nodes/command_selection_node.py:238`
- **签名**：`def command_selection_prepare_node(state: dict) -> dict`
- **作用**：在从论文和仓库证据中选择、校验并固定可复现实验命令的阶段中，在 interrupt 节点之前落盘并登记命令选择模板。该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 候选运行命令集合。
如果候选运行命令集合为空或为假，就返回包含 `command_selection_input_path`、`selected_run_command_index`、`edited_run_commands` 字段的结构化映射。
调用 `resolve_artifact_path` 解析、规范化或转换当前输入，并把结果记为 输入内容的路径；调用 `ensure_command_selection_input_file` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算初始化顺序集合，并保存为 领域记录集合。
如果过期的路径不为空，就把新的处理结果追加或合并到领域记录集合。
返回包含 `command_selection_input_path`、`command_selection_input_status` 字段的结构化映射。
```

### `app/nodes/execution_verifier_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_invalid_verification_input`

- **源码**：`app/nodes/execution_verifier_node.py:25`
- **签名**：`def _invalid_verification_input(state: dict, message: str) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态、面向用户或日志的提示信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `execution_verifier_node`

- **源码**：`app/nodes/execution_verifier_node.py:43`
- **签名**：`def execution_verifier_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，只读取既有执行事实，不调用 Runner，也不修改 Action。该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 待执行复现动作；复制、序列化或校验结构化领域对象，并把结果记为 阶段处理结果；复制、序列化或校验结构化领域对象，并把结果记为 可追溯证据记录；调用 `str` 完成该函数的一项辅助处理，并把结果记为 人工决策结果。
    计算根据条件从两个候选结果中选择一个，并保存为 人工审批记录。
如果出现 `ValidationError`并把异常保存为捕获的异常对象：
    调用 `_invalid_verification_input` 完成该函数的一项辅助处理，并返回处理结果。
调用 `build_execution_verification` 组装当前阶段需要的领域对象，并把结果记为 验证结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 当前处理结果。
如果当前处理结果等于'verified'，就返回包含 `error` 字段的结构化映射。
如果当前处理结果等于'inconclusive'，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `build_execution_stage_error` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 状态；调用 `persist_stage_errors` 完成该函数的一项辅助处理，并把结果记为 错误；返回包含 `final_status`、`log_path`、`last_action_result` 字段的结构化映射。
```

### `app/nodes/executor_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_run_approved_action`

- **源码**：`app/nodes/executor_node.py:22`
- **签名**：`def _run_approved_action(state: dict, pending_action: ExecutableAction) -> dict`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，Executor 运行已批准 Action，并只返回 Process 事实和 Evidence。该函数接收复现流程状态、待审批复现动作，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `pending_action` | `ExecutableAction` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `run_action_safe` 完成该函数的一项辅助处理，并把结果记为 结果。
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 阶段处理结果。
如果出现 `ValidationError`并把异常保存为捕获的异常对象：
    调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `register_execution_artifacts` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `build_execution_evidence` 组装当前阶段需要的领域对象，并把结果记为 可追溯证据记录；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算初始化顺序集合，并保存为 当前处理结果。
读取当前处理结果的路径，并保存为 运行日志路径；计算按字段初始化键值映射，并保存为 当前处理结果。
如果“处理是否成功的判断有值或为真”不成立 且 运行日志路径有值或为真，就读取运行日志路径，并保存为 当前处理结果中的对应字段。
返回前一步处理得到的结果。
```

#### `executor_node`

- **源码**：`app/nodes/executor_node.py:107`
- **签名**：`def executor_node(state: dict) -> dict`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 待审批复现动作。
如果出现 `ValidationError`并把异常保存为捕获的异常对象：
    调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
从复现流程状态读取所需的状态或领域记录，并把结果记为 人工决策结果。
如果人工决策结果等于'rejected'，就返回包含 `final_status`、`last_action_result` 字段的结构化映射。
如果人工决策结果等于'revise'，就返回包含 `final_status`、`last_action_result` 字段的结构化映射。
如果人工决策结果不属于{'approved', 'not_required'}，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
如果类型不等于'run_command'，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `compute_action_hash` 计算内容身份、分数或派生结果，并把结果记为 当前的 Hash。
如果人工决策结果等于'approved'：
    从复现流程状态读取所需的状态或领域记录，并把结果记为 记录。
    如果记录为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
    从记录读取所需的状态或领域记录，并把结果记为 当前处理结果的 Hash。
    如果当前处理结果的 Hash不等于当前的 Hash，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `_run_approved_action` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/nodes/experiment_plan_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_build_plan_fallback`

- **源码**：`app/nodes/experiment_plan_node.py:25`
- **签名**：`def _build_plan_fallback(*, goal: str, reason: str) -> ExperimentPlan`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现实验目标、基线接受或运行操作原因，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ExperimentPlan` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `goal` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |

**输出**

- **Python 类型**：`ExperimentPlan`
- **语义**：返回 `ExperimentPlan` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ExperimentPlan` 结构化领域对象。
```

#### `_compact_paper_summary`

- **源码**：`app/nodes/experiment_plan_node.py:40`
- **签名**：`def _compact_paper_summary(payload: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，保留规划所需论文事实，移除已验证但体积很大的 provenance。该函数接收结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `dict` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果中的对应字段；遍历并筛选输入，将整理后的结果保存为 当前处理结果中的对应字段；返回前一步处理得到的结果。
```

#### `_compact_repo_map`

- **源码**：`app/nodes/experiment_plan_node.py:82`
- **签名**：`def _compact_repo_map(payload: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，限制仓库文件列表规模，同时保留训练入口和关键文件。该函数接收结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `dict` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
将 当前处理结果 初始化为空映射，用来收集后续结果。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        读取当前字段值中的对应字段，并保存为 当前处理结果中的对应字段。
    否则：
        如果当前字段值不属于(空值, '')，就读取当前字段值，并保存为 当前处理结果中的对应字段。
返回前一步处理得到的结果。
```

#### `_compact_code_mapping`

- **源码**：`app/nodes/experiment_plan_node.py:94`
- **签名**：`def _compact_code_mapping(payload: list) -> list[dict]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，规划只消费映射结论，不重复发送完整源码、哈希和检索信号。该函数接收结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `list` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`list[dict]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历由结构化请求载荷组成的集合或迭代器，每次把当前项记为论文-代码映射：
    如果“计算数量、边界或类型判断结果”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    将 候选结果集合 初始化为空列表，用来收集后续结果；从论文-代码映射读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
    如果“计算数量、边界或类型判断结果”后未得到肯定结果，就将 当前处理结果 初始化为空列表，用来收集后续结果。
    遍历当前可迭代输入，每次把当前项记为待审核的 MCP 能力候选：
        如果“计算数量、边界或类型判断结果”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
        把新的处理结果追加或合并到候选结果集合。
    把新的处理结果追加或合并到当前处理结果。
返回前一步处理得到的结果。
```

#### `_render_steps`

- **源码**：`app/nodes/experiment_plan_node.py:138`
- **签名**：`def _render_steps(title: str, steps: list) -> list[str]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收文档或章节标题、当前处理结果，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `title` | `str` | 论文/文档章节标题；用于建立可检索的章节身份和展示文本。 |
| `steps` | `list` | 名为 `steps` 的 `list` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行。
如果当前处理结果为空或为假，就把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；返回待输出的文本行的当前值。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理结果：
    把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
    如果当前处理结果有值或为真，就把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行。
返回待输出的文本行的当前值。
```

#### `_render_plan_markdown`

- **源码**：`app/nodes/experiment_plan_node.py:156`
- **签名**：`def _render_plan_markdown(plan: ExperimentPlan) -> str`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收实验计划，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `plan` | `ExperimentPlan` | 实验计划；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行；将新的计算结果累加或合并到待输出的文本行；将新的计算结果累加或合并到待输出的文本行；将新的计算结果累加或合并到待输出的文本行。
将新的计算结果累加或合并到待输出的文本行；将新的计算结果累加或合并到待输出的文本行。
遍历当前可迭代输入，每次把当前项记为当前命令：
    把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
如果当前处理结果有值或为真：
    将新的计算结果累加或合并到待输出的文本行。
    遍历当前可迭代输入，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `experiment_plan_node`

- **源码**：`app/nodes/experiment_plan_node.py:179`
- **签名**：`def experiment_plan_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 论文；从复现流程状态读取所需的状态或领域记录，并把结果记为 仓库；从复现流程状态读取所需的状态或领域记录，并把结果记为 论文映射；计算计算当前表达式的结果，并保存为 复现实验目标。
计算使用固定配置或常量值，并保存为 调用链追踪信息的路径；计算使用固定配置或常量值，并保存为 工具调用记录；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
如果当前处理结果有值或为真：
    调用 `_build_plan_fallback` 组装当前阶段需要的领域对象，并把结果记为 实验计划。
否则：
    调用 `format` 完成该函数的一项辅助处理，并把结果记为 发给模型的结构化提示；调用 `invoke_structured` 完成该函数的一项辅助处理，并把结果记为 工具调用记录。
    如果当前字段值不为空：
        读取当前字段值，并保存为 实验计划。
        如果复现实验目标不等于复现实验目标，就复制、序列化或校验结构化领域对象，并把结果记为 实验计划。
    否则：
        调用 `_build_plan_fallback` 组装当前阶段需要的领域对象，并把结果记为 实验计划。
    调用 `write_structured_output_trace` 持久化或更新当前领域数据，并把结果记为 调用链追踪信息的路径。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算初始化顺序集合，并保存为 领域记录集合。
如果调用链追踪信息的路径不为空，就把新的处理结果追加或合并到领域记录集合。
计算按字段初始化键值映射，并保存为 结构化请求载荷。
如果当前处理结果有值或为真，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
如果工具调用记录不为空 且 当前字段值为空，就计算按字段初始化键值映射，并保存为 状态；返回当前构造的结构化映射。
返回结构化请求载荷的当前值。
```

### `app/nodes/file_repair_planner_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_no_patch`

- **源码**：`app/nodes/file_repair_planner_node.py:25`
- **签名**：`def _no_patch(summary: str, root_cause: str) -> FileRepairProposal`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，任何输入不足或校验失败都安全降级，不生成文件修改。该函数接收阶段摘要、根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `FileRepairProposal` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `summary` | `str` | 阶段摘要；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `root_cause` | `str` | 名为 `root_cause` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`FileRepairProposal`
- **语义**：返回 `FileRepairProposal` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `FileRepairProposal` 结构化领域对象。
```

#### `_is_test_path`

- **源码**：`app/nodes/file_repair_planner_node.py:40`
- **签名**：`def _is_test_path(relative_path: str) -> bool`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收仓库内相对路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 文件或目录路径；返回组合判断结果。
```

#### `_extract_action_verification_targets`

- **源码**：`app/nodes/file_repair_planner_node.py:45`
- **签名**：`def _extract_action_verification_targets(pending_action: dict, repo_path: str) -> list[str]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，从 pytest action 中提取已有测试文件，建立确定性行为验证目标。该函数接收待审批复现动作、代码仓库根目录，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pending_action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `repo_path` | `str` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从待审批复现动作读取所需的状态或领域记录，并把结果记为 待启动实验程序；构造临时集合、映射或轻量领域对象，并把结果记为 命令行或函数位置参数集合。
如果待启动实验程序不等于'python' 或 当前输入内容不属于命令行或函数位置参数集合，就返回当前构造的顺序或去重集合。
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 代码仓库；将 待定位的代码对象集合 初始化为空列表，用来收集后续结果。
遍历由命令行或函数位置参数集合组成的集合或迭代器，每次把当前项记为当前处理结果：
    读取前一步操作返回对象中的对应字段，并保存为 原始内容的路径。
    如果“检查原始内容的路径是否满足文本匹配条件”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    把外部位置解析为文件系统路径对象，并把结果记为 待审核的 MCP 能力候选；计算根据条件从两个候选结果中选择一个，并保存为 待定位的代码对象或业务目标。
    如果待定位的代码对象或业务目标等于代码仓库 或 代码仓库不属于当前处理结果，就跳过本轮剩余处理，直接进入下一轮。
    把辅助操作“把待定位的代码对象或业务目标转换为稳定的仓库相对路径表示”的结果转换为稳定的仓库相对路径表示，并把结果记为 仓库相对路径。
    如果“调用 `_is_test_path` 校验当前输入或状态”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    先尝试完成以下处理：
        调用 `resolve_patch_target` 解析、规范化或转换当前输入。
    如果出现 `ValueError`：
        跳过本轮剩余处理，直接进入下一轮。
    如果仓库相对路径不属于待定位的代码对象集合，就把仓库相对路径追加或合并到待定位的代码对象集合。
返回待定位的代码对象集合的当前值。
```

#### `_proposal_state_update`

- **源码**：`app/nodes/file_repair_planner_node.py:89`
- **签名**：`def _proposal_state_update(state: dict, proposal: FileRepairProposal, trace_path: Path | None, invocation: object | None) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，所有 no_patch/patch 分支都写入并登记同一个 run-native Artifact。该函数接收复现流程状态、修复或重跑提案、调用链追踪信息的路径、工具调用记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `proposal` | `FileRepairProposal` | 修复或重跑提案；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `trace_path` | `Path | None` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。；默认 空值 |
| `invocation` | `object | None` | 工具调用记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算初始化顺序集合，并保存为 领域记录集合。
如果调用链追踪信息的路径不为空，就把新的处理结果追加或合并到领域记录集合。
计算按字段初始化键值映射，并保存为 结构化请求载荷。
如果工具调用记录不为空 且 辅助操作“调用 `getattr` 完成该函数的一项辅助处理”的结果为空，就把新的处理结果追加或合并到结构化请求载荷。
返回结构化请求载荷的当前值。
```

#### `file_repair_planner_node`

- **源码**：`app/nodes/file_repair_planner_node.py:131`
- **签名**：`def file_repair_planner_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
如果“文件有值或为真”不成立，就调用 `_no_patch` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案；调用 `_proposal_state_update` 完成该函数的一项辅助处理，并返回处理结果。
调用 `int` 完成该函数的一项辅助处理，并把结果记为 模型尝试记录集合。
如果模型尝试记录集合不小于最大文件尝试记录集合集合，就调用 `_no_patch` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案；调用 `_proposal_state_update` 完成该函数的一项辅助处理，并返回处理结果。
从复现流程状态读取所需的状态或领域记录，并把结果记为 代码仓库根目录；计算计算当前表达式的结果，并保存为 当前处理结果；从复现流程状态读取所需的状态或领域记录，并把结果记为 运行日志路径；构造临时集合、映射或轻量领域对象，并把结果记为 相关源码文件集合。
如果代码仓库根目录为空或为假 或 运行日志路径为空或为假 或 相关源码文件集合为空或为假，就调用 `_no_patch` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案；调用 `_proposal_state_update` 完成该函数的一项辅助处理，并返回处理结果。
先尝试完成以下处理：
    调用 `collect_source_context` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `extract_traceback` 完成该函数的一项辅助处理，并把结果记为 异常堆栈文本。
如果出现 `(FileNotFoundError, UnicodeDecodeError, ValueError)`并把异常保存为捕获的异常对象：
    调用 `_no_patch` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案；调用 `_proposal_state_update` 完成该函数的一项辅助处理，并返回处理结果。
如果当前处理结果为空或为假 或 “对异常堆栈文本中的文本执行规范化或拆分”后未得到肯定结果，就调用 `_no_patch` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案；调用 `_proposal_state_update` 完成该函数的一项辅助处理，并返回处理结果。
调用 `format` 完成该函数的一项辅助处理，并把结果记为 发给模型的结构化提示；调用 `_extract_action_verification_targets` 完成该函数的一项辅助处理，并把结果记为 验证集合；调用 `invoke_structured` 完成该函数的一项辅助处理，并把结果记为 工具调用记录。
如果当前字段值为空：
    调用 `_no_patch` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案。
否则：
    读取当前字段值，并保存为 修复或重跑提案。
    如果“修复或重跑提案的 ID有值或为真”不成立，就复制、序列化或校验结构化领域对象，并把结果记为 修复或重跑提案。
    遍历并筛选输入，将整理后的结果保存为 当前处理结果。
    如果“调用 `issubset` 完成该函数的一项辅助处理”后未得到肯定结果：
        调用 `_no_patch` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案。
    否则：
        如果由当前处理结果组成的集合或迭代器中存在满足““调用 `_is_test_path` 校验当前输入或状态”后得到肯定结果”的项，就调用 `_no_patch` 完成该函数的一项辅助处理，并把结果记为 修复或重跑提案；否则构造临时集合、映射或轻量领域对象，并把结果记为 验证集合；复制、序列化或校验结构化领域对象，并把结果记为 修复或重跑提案。
调用 `write_structured_output_trace` 持久化或更新当前领域数据，并把结果记为 调用链追踪信息的路径；调用 `_proposal_state_update` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/nodes/final_report_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `final_report_node`

- **源码**：`app/nodes/final_report_node.py:13`
- **签名**：`def final_report_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `_render_final_report` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告的文本；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回包含 `final_report` 字段的结构化映射。
```

#### `_render_section`

- **源码**：`app/nodes/final_report_node.py:28`
- **签名**：`def _render_section(title: str, items: list[str]) -> list[str]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收文档或章节标题、待处理项集合，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `title` | `str` | 论文/文档章节标题；用于建立可检索的章节身份和展示文本。 |
| `items` | `list[str]` | 待处理项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行。
如果待处理项集合为空或为假，就把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；返回待输出的文本行的当前值。
遍历由待处理项集合组成的集合或迭代器，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
把新的处理结果追加或合并到待输出的文本行；返回待输出的文本行的当前值。
```

#### `_load_process_record_summary`

- **源码**：`app/nodes/final_report_node.py:40`
- **签名**：`def _load_process_record_summary(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 原始内容的路径；从复现流程状态读取所需的状态或领域记录，并把结果记为 运行的目录。
如果原始内容的路径为空或为假 或 运行的目录为空或为假，就返回当前构造的结构化映射。
先尝试完成以下处理：
    将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 本次复现运行目录；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 文件或目录路径。
    如果本次复现运行目录不属于当前处理结果 或 “检查文件或目录路径的文件系统属性”后未得到肯定结果，就返回当前构造的结构化映射。
    将外部表示解析为结构化内容，并把结果记为 结构化请求载荷。
如果出现 `(OSError, ValueError, json.JSONDecodeError)`：
    返回当前构造的结构化映射。
计算初始化去重集合，并保存为 键集合集合；返回当前计算得到的结果。
```

#### `_execution_status_items`

- **源码**：`app/nodes/final_report_node.py:75`
- **签名**：`def _execution_status_items(state: dict, stage_errors: list[StageError]) -> list[str]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态、阶段集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `stage_errors` | `list[StageError]` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 当前状态。
如果当前状态等于'succeeded'，就返回当前构造的顺序或去重集合。
如果当前状态等于'failed'，就返回当前构造的顺序或去重集合。
如果当前状态等于'cancelled'，就返回当前构造的顺序或去重集合。
如果当前状态等于'policy_blocked'，就返回当前构造的顺序或去重集合。
如果当前状态等于'environment_blocked'，就返回当前构造的顺序或去重集合。
如果当前状态等于'agent_failed'，就返回当前构造的顺序或去重集合。
如果由阶段集合组成的集合或迭代器中存在满足“评测类别等于'paper_program'”的项，就返回当前构造的顺序或去重集合。
如果由阶段集合组成的集合或迭代器中存在满足“流程是否已进入终止状态的判断有值或为真”的项，就返回当前构造的顺序或去重集合。
返回当前构造的顺序或去重集合。
```

#### `_render_final_report`

- **源码**：`app/nodes/final_report_node.py:112`
- **签名**：`def _render_final_report(state: dict) -> str`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，将 state 中已经积累的结构化结果组织成最终 markdown 报告。该函数接收复现流程状态，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行；将新的计算结果累加或合并到待输出的文本行；遍历并筛选输入，将整理后的结果保存为 阶段集合；将 错误集合 初始化为空列表，用来收集后续结果。
遍历由阶段集合组成的集合或迭代器，每次把当前项记为错误信息，然后把新的处理结果追加或合并到错误集合。
将新的计算结果累加或合并到待输出的文本行；将新的计算结果累加或合并到待输出的文本行；从复现流程状态读取所需的状态或领域记录，并把结果记为 论文；将新的计算结果累加或合并到待输出的文本行。
从复现流程状态读取所需的状态或领域记录，并把结果记为 仓库；从仓库读取所需的状态或领域记录，并把结果记为 该调用返回的结果；将新的计算结果累加或合并到待输出的文本行；从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
将 映射集合 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为论文-代码映射：
    从论文-代码映射读取所需的状态或领域记录，并把结果记为 Python 模块的名称；从论文-代码映射读取所需的状态或领域记录，并把结果记为 评测类别；计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果；从论文-代码映射读取所需的状态或领域记录，并把结果记为 候选结果集合。
    如果候选结果集合为空或为假，就把新的处理结果追加或合并到映射集合；跳过本轮剩余处理，直接进入下一轮。
    读取候选结果集合中的对应字段，并保存为 候选项；把新的处理结果追加或合并到映射集合。
将新的计算结果累加或合并到待输出的文本行；从复现流程状态读取所需的状态或领域记录，并把结果记为 实验计划；从复现流程状态读取所需的状态或领域记录，并把结果记为 候选运行命令集合；将新的计算结果累加或合并到待输出的文本行。
从复现流程状态读取所需的状态或领域记录，并把结果记为 待审批复现动作；将 当前处理结果 初始化为空列表，用来收集后续结果。
如果待审批复现动作有值或为真，就把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到当前处理结果。
从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真，就把新的处理结果追加或合并到当前处理结果。
将新的计算结果累加或合并到待输出的文本行；从复现流程状态读取所需的状态或领域记录，并把结果记为 执行结果；将 执行集合 初始化为空列表，用来收集后续结果。
如果执行结果有值或为真，就把新的处理结果追加或合并到执行集合。
计算计算当前表达式的结果，并保存为 验证结果；将 验证集合 初始化为空列表，用来收集后续结果。
如果验证结果有值或为真，就把新的处理结果追加或合并到验证集合。
将新的计算结果累加或合并到待输出的文本行；将新的计算结果累加或合并到待输出的文本行；调用 `_load_process_record_summary` 读取或查询当前阶段需要的数据，并把结果记为 记录；计算计算当前表达式的结果，并保存为 资源。
从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果；计算计算当前表达式的结果，并保存为 执行记录的 ID。
如果执行记录的 ID有值或为真：
    把新的处理结果追加或合并到当前处理结果；计算计算当前表达式的结果，并保存为 待审批复现动作。
    如果辅助操作“从待审批复现动作读取所需的状态或领域记录”的结果等于'none'，就把新的处理结果追加或合并到当前处理结果。
    把新的处理结果追加或合并到当前处理结果。
将新的计算结果累加或合并到待输出的文本行；从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
如果当前处理结果有值或为真：
    把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到当前处理结果。
    遍历当前可迭代输入，每次把当前项记为对象名称，然后把新的处理结果追加或合并到当前处理结果。
将新的计算结果累加或合并到待输出的文本行；从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
如果当前处理结果有值或为真：
    把新的处理结果追加或合并到当前处理结果。
    遍历当前可迭代输入，每次把当前项记为当前处理结果，然后把新的处理结果追加或合并到当前处理结果。
将新的计算结果累加或合并到待输出的文本行；从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
如果当前处理结果有值或为真：
    把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到当前处理结果。
    遍历当前可迭代输入，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到当前处理结果。
将新的计算结果累加或合并到待输出的文本行；从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
如果当前处理结果有值或为真，就把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到当前处理结果。
从复现流程状态读取所需的状态或领域记录，并把结果记为 尝试的数量。
如果尝试的数量不为空，就把新的处理结果追加或合并到当前处理结果。
将新的计算结果累加或合并到待输出的文本行；将 文件集合 初始化为空列表，用来收集后续结果；计算计算当前表达式的结果，并保存为 文件。
如果文件有值或为真，就把新的处理结果追加或合并到文件集合；把新的处理结果追加或合并到文件集合。
计算计算当前表达式的结果，并保存为 当前处理结果。
如果当前处理结果有值或为真，就把新的处理结果追加或合并到文件集合；把新的处理结果追加或合并到文件集合。
计算计算当前表达式的结果，并保存为 验证结果。
如果验证结果有值或为真，就把新的处理结果追加或合并到文件集合。
计算计算当前表达式的结果，并保存为 当前处理结果。
如果当前处理结果有值或为真，就把新的处理结果追加或合并到文件集合。
将新的计算结果累加或合并到待输出的文本行；将新的计算结果累加或合并到待输出的文本行；调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/nodes/human_review_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `human_review_node`

- **源码**：`app/nodes/human_review_node.py:12`
- **签名**：`def human_review_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
如果“从复现流程状态读取所需的状态或领域记录”后未得到肯定结果，就返回包含 `user_approval` 字段的结构化映射。
从复现流程状态读取所需的状态或领域记录，并把结果记为 待审批复现动作。
如果待审批复现动作为空或为假，就返回包含 `user_approval` 字段的结构化映射。
计算计算当前表达式的结果，并保存为 待执行复现动作的 Hash；计算按字段初始化键值映射，并保存为 结构化请求载荷；调用 `interrupt` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就从结构化响应读取所需的状态或领域记录，并把结果记为 人工决策结果；从结构化响应读取所需的状态或领域记录，并把结果记为 用户修正意见；否则调用 `str` 完成该函数的一项辅助处理，并把结果记为 人工决策结果；计算使用固定配置或常量值，并保存为 用户修正意见。
调用 `build_approval_record` 组装当前阶段需要的领域对象，并把结果记为 记录；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回包含 `user_approval`、`human_feedback`、`approval_record`、`pending_action_hash` 字段的结构化映射。
```

### `app/nodes/input_validation_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_check_required_file`

- **源码**：`app/nodes/input_validation_node.py:21`
- **签名**：`def _check_required_file(name: str, raw_path: str | None, missing_code: str) -> InputCheck`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收对象名称、原始内容的路径、当前处理结果，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `InputCheck` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `raw_path` | `str | None` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `missing_code` | `str` | 名为 `missing_code` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`InputCheck`
- **语义**：返回 `InputCheck` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果原始内容的路径为空或为假，就构造并返回 `InputCheck` 结构化领域对象。
将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 文件或目录路径。
如果“检查文件或目录路径的文件系统属性”后未得到肯定结果，就构造并返回 `InputCheck` 结构化领域对象。
如果“检查文件或目录路径的文件系统属性”后未得到肯定结果，就构造并返回 `InputCheck` 结构化领域对象。
构造并返回 `InputCheck` 结构化领域对象。
```

#### `_check_paper`

- **源码**：`app/nodes/input_validation_node.py:66`
- **签名**：`def _check_paper(path: str | None) -> list[InputCheck]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收文件或目录路径，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `str | None` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`list[InputCheck]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `_check_required_file` 校验当前输入或状态，并把结果记为 校验；计算初始化顺序集合，并保存为 校验项集合。
如果当前状态等于'passed' 且 文件或目录路径有值或为真：
    对前一步操作返回对象的文件扩展名或文本后缀中的文本执行规范化或拆分，并把结果记为 文件扩展名或文本后缀。
    如果文件扩展名或文本后缀不属于论文集合，就把新的处理结果追加或合并到校验项集合；否则把新的处理结果追加或合并到校验项集合。
返回校验项集合的当前值。
```

#### `_check_repo`

- **源码**：`app/nodes/input_validation_node.py:102`
- **签名**：`def _check_repo(path: str | None) -> InputCheck`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收文件或目录路径，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `InputCheck` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `str | None` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`InputCheck`
- **语义**：返回 `InputCheck` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果文件或目录路径为空或为假，就构造并返回 `InputCheck` 结构化领域对象。
将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 代码仓库。
如果“检查代码仓库的文件系统属性”后未得到肯定结果，就构造并返回 `InputCheck` 结构化领域对象。
如果“检查代码仓库的文件系统属性”后未得到肯定结果，就构造并返回 `InputCheck` 结构化领域对象。
构造并返回 `InputCheck` 结构化领域对象。
```

#### `_check_optional_log`

- **源码**：`app/nodes/input_validation_node.py:142`
- **签名**：`def _check_optional_log(path: str | None) -> InputCheck`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收文件或目录路径，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `InputCheck` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `str | None` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`InputCheck`
- **语义**：返回 `InputCheck` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果文件或目录路径为空或为假，就构造并返回 `InputCheck` 结构化领域对象。
调用 `_check_required_file` 校验当前输入或状态，并返回处理结果。
```

#### `_check_execution_profile`

- **源码**：`app/nodes/input_validation_node.py:158`
- **签名**：`def _check_execution_profile(profile_id: str | None, repo_path: str | None) -> InputCheck`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收MCP Client 配置档案 ID、代码仓库根目录，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `InputCheck` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile_id` | `str | None` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。 |
| `repo_path` | `str | None` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`InputCheck`
- **语义**：返回 `InputCheck` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果MCP Client 配置档案 ID为空或为假，就构造并返回 `InputCheck` 结构化领域对象。
先尝试完成以下处理：
    调用 `get_execution_profile` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案。
如果出现 `(FileNotFoundError, ValueError)`并把异常保存为捕获的异常对象：
    构造并返回 `InputCheck` 结构化领域对象。
将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 本次复现工作区。
如果“检查本次复现工作区的文件系统属性”后未得到肯定结果，就构造并返回 `InputCheck` 结构化领域对象。
如果代码仓库根目录有值或为真：
    将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 代码仓库。
    如果代码仓库不等于本次复现工作区 且 本次复现工作区不属于当前处理结果，就构造并返回 `InputCheck` 结构化领域对象。
构造并返回 `InputCheck` 结构化领域对象。
```

#### `input_validation_node`

- **源码**：`app/nodes/input_validation_node.py:218`
- **签名**：`def input_validation_node(state: dict[str, Any]) -> dict[str, Any]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，在任何 PDF、Git、rg、LLM 或论文命令之前检查外部输入。该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
计算初始化顺序集合，并保存为 校验项集合；检查由校验项集合组成的集合或迭代器中是否全部满足“当前状态不等于'failed'”的项，并把结果记为 输入或结果是否有效的判断；构造 `InputValidationReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
计算按字段初始化键值映射，并保存为 当前处理结果。
如果输入或结果是否有效的判断有值或为真，就返回前一步处理得到的结果。
遍历并筛选输入，将整理后的结果保存为 错误信息集合；计算按字段初始化键值映射，并保存为 状态；返回当前构造的结构化映射。
```

### `app/nodes/log_debug_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_build_fallback_report`

- **源码**：`app/nodes/log_debug_node.py:52`
- **签名**：`def _build_fallback_report(error_type: str, traceback: str, log_path: str) -> DebugReport`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，在没有错误证据或模型格式错误时返回保守、可继续流转的报告。该函数接收错误类型、异常堆栈文本、运行日志路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `DebugReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `error_type` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `traceback` | `str` | 异常堆栈文本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `log_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`DebugReport`
- **语义**：返回 `DebugReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果“对异常堆栈文本中的文本执行规范化或拆分”后未得到肯定结果，就构造并返回 `DebugReport` 结构化领域对象。
构造并返回 `DebugReport` 结构化领域对象。
```

#### `_build_cuda_oom_report`

- **源码**：`app/nodes/log_debug_node.py:105`
- **签名**：`def _build_cuda_oom_report() -> DebugReport`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，为证据明确的 CUDA OOM 提供无需 LLM 的确定性诊断。该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `DebugReport` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`DebugReport`
- **语义**：返回 `DebugReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `DebugReport` 结构化领域对象。
```

#### `_debug_keywords`

- **源码**：`app/nodes/log_debug_node.py:131`
- **签名**：`def _debug_keywords(error_type: str, traceback: str, traceback_paths: list[str]) -> list[str]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，从本地错误事实提取有限关键词，不调用模型。该函数接收错误类型、异常堆栈文本、异常堆栈中的源码路径集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `error_type` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `traceback` | `str` | 异常堆栈文本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `traceback_paths` | `list[str]` | 异常堆栈中的源码路径集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `findall` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `findall` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 路径集合；返回前一步操作返回对象中的对应字段的当前值。
```

#### `_build_debug_evidence`

- **源码**：`app/nodes/log_debug_node.py:165`
- **签名**：`def _build_debug_evidence(state: dict, error_type: str, traceback: str, traceback_paths: list[str]) -> tuple[dict | None, str | None, list, str | None]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，返回： pack payload、pack path、新 ArtifactRecord、可恢复 warning。该函数接收复现流程状态、错误类型、异常堆栈文本、异常堆栈中的源码路径集合，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `error_type` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `traceback` | `str` | 异常堆栈文本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `traceback_paths` | `list[str]` | 异常堆栈中的源码路径集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[dict | None, str | None, list, str | None]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 代码仓库根目录。
如果代码仓库根目录为空或为假，就返回当前构造的顺序或去重集合。
将 领域记录集合 初始化为空列表，用来收集后续结果。
先尝试完成以下处理：
    从复现流程状态读取所需的状态或领域记录，并把结果记为 当前候选项的索引的路径。
    如果当前候选项的索引的路径有值或为真 且 “检查辅助操作“把外部位置解析为文件系统路径对象”的结果的文件系统属性”后得到肯定结果，就调用 `load_repository_index` 读取或查询当前阶段需要的数据，并把结果记为 当前候选项的索引；否则调用 `build_repository_index` 组装当前阶段需要的领域对象，并把结果记为 当前候选项的索引；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前候选项的索引的路径；把索引记录追加或合并到领域记录集合。
    调用 `build_evidence_pack` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；把记录追加或合并到领域记录集合；返回当前构造的顺序或去重集合。
如果出现 `(OSError, SearchToolError, ValueError)`并把异常保存为捕获的异常对象：
    返回当前构造的顺序或去重集合。
```

#### `_build_failure_case_pack`

- **源码**：`app/nodes/log_debug_node.py:285`
- **签名**：`def _build_failure_case_pack(state: dict, error_type: str, traceback: str) -> tuple[dict | None, str | None, list, str | None]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，检索失败时降级，不掩盖当前实验的原始错误。该函数接收复现流程状态、错误类型、异常堆栈文本，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `error_type` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `traceback` | `str` | 异常堆栈文本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[dict | None, str | None, list, str | None]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果“失败记忆有值或为真”不成立，就返回当前构造的顺序或去重集合。
加载这一步需要的外部依赖；加载这一步需要的外部依赖；从复现流程状态读取所需的状态或领域记录，并把结果记为 错误。
如果错误为空或为假，就返回当前构造的顺序或去重集合。
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 阶段错误；调用 `str` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案 ID；调用 `str` 完成该函数的一项辅助处理，并把结果记为 执行环境配置指纹。
    如果MCP Client 配置档案 ID为空或为假 或 执行环境配置指纹为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    调用 `get_execution_profile` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案；构造 `FailureEnvironmentIdentity` 结构化领域对象，并把结果记为 实验执行环境描述；调用 `build_failure_signature` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `search` 完成该函数的一项辅助处理，并把结果记为 检索或映射证据包。
    调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回当前构造的顺序或去重集合。
如果出现 `(FailureMemoryError, OSError, ValueError)`并把异常保存为捕获的异常对象：
    返回当前构造的顺序或去重集合。
```

#### `_should_run_cuda_build_skill`

- **源码**：`app/nodes/log_debug_node.py:395`
- **签名**：`def _should_run_cuda_build_skill(log_text: str) -> bool`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，仅在同时具备 CUDA/构建身份和失败特征时选择 Skill。该函数接收当前处理结果的文本，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `log_text` | `str` | 已规范化或待输出的文本；进入持久化或 Prompt 前可能需要限长和脱敏。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
对当前处理结果的文本中的文本执行规范化或拆分，并把结果记为 转为小写的比较文本；返回组合判断结果。
```

#### `_is_under`

- **源码**：`app/nodes/log_debug_node.py:405`
- **签名**：`def _is_under(path: Path, root: Path) -> bool`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收文件或目录路径、受控扫描根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `root` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
返回组合判断结果。
```

#### `_run_optional_cuda_build_skill`

- **源码**：`app/nodes/log_debug_node.py:409`
- **签名**：`def _run_optional_cuda_build_skill(state: dict, log_text: str) -> tuple[dict | None, str | None, str | None, list, str | None]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，返回：typed output、result path、record path、Artifact records、warning。该函数接收复现流程状态、当前处理结果的文本，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `log_text` | `str` | 已规范化或待输出的文本；进入持久化或 Prompt 前可能需要限长和脱敏。 |

**输出**

- **Python 类型**：`tuple[dict | None, str | None, str | None, list, str | None]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果“当前处理结果有值或为真”不成立，就返回当前构造的顺序或去重集合。
如果“调用 `_should_run_cuda_build_skill` 完成该函数的一项辅助处理”后未得到肯定结果，就返回当前构造的顺序或去重集合。
从复现流程状态读取所需的状态或领域记录，并把结果记为 仓库的路径；从复现流程状态读取所需的状态或领域记录，并把结果记为 当前处理结果的路径。
如果仓库的路径为空或为假 或 当前处理结果的路径为空或为假，就返回当前构造的顺序或去重集合。
先尝试完成以下处理：
    将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 代码仓库根目录；将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 运行日志路径；将辅助操作“将根目录规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 根目录。
    如果“检查代码仓库根目录的文件系统属性”后未得到肯定结果 或 “检查运行日志路径的文件系统属性”后未得到肯定结果 或 “调用 `_is_under` 校验当前输入或状态”后未得到肯定结果 或 “调用 `_is_under` 校验当前输入或状态”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    读取父级目录或父领域对象，并保存为 根目录；读取父级目录或父领域对象，并保存为 运行产物根目录；调用 `build_skill_registry` 组装当前阶段需要的领域对象，并把结果记为 组件注册表；从组件注册表读取所需的状态或领域记录，并把结果记为 边界值。
    调用组件注册表完成模型或 Runnable 处理，并把结果记为 阶段处理结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算初始化顺序集合，并保存为 领域记录集合。
    如果失败不为空，就返回当前构造的顺序或去重集合。
    返回当前构造的顺序或去重集合。
如果出现 `(OSError, ValueError)`并把异常保存为捕获的异常对象：
    返回当前构造的顺序或去重集合。
```

#### `log_debug_node`

- **源码**：`app/nodes/log_debug_node.py:553`
- **签名**：`def log_debug_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 运行日志路径。
如果运行日志路径为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `read_log` 读取或查询当前阶段需要的数据，并把结果记为 当前处理结果的文本；调用 `extract_traceback` 完成该函数的一项辅助处理，并把结果记为 异常堆栈文本；调用 `classify_error_heuristic` 完成该函数的一项辅助处理，并把结果记为 错误类型；调用 `extract_repo_traceback_paths` 完成该函数的一项辅助处理，并把结果记为 异常堆栈中的源码路径集合。
调用 `_build_debug_evidence` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `_build_failure_case_pack` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；调用 `_run_optional_cuda_build_skill` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算使用固定配置或常量值，并保存为 调用链追踪信息的路径。
计算使用固定配置或常量值，并保存为 工具调用记录。
如果错误类型等于'cuda_oom'：
    调用 `_build_cuda_oom_report` 组装当前阶段需要的领域对象，并把结果记为 MCP 评测或运行报告。
否则：
    如果“对异常堆栈文本中的文本执行规范化或拆分”后未得到肯定结果：
        调用 `_build_fallback_report` 组装当前阶段需要的领域对象，并把结果记为 MCP 评测或运行报告。
    否则：
        调用 `format` 完成该函数的一项辅助处理，并把结果记为 发给模型的结构化提示；调用 `invoke_structured` 完成该函数的一项辅助处理，并把结果记为 工具调用记录。
        如果当前字段值不为空：
            读取当前字段值，并保存为 MCP 评测或运行报告。
            如果错误类型不等于错误类型，就复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告。
        否则：
            调用 `_build_fallback_report` 组装当前阶段需要的领域对象，并把结果记为 MCP 评测或运行报告。
        调用 `write_structured_output_trace` 持久化或更新当前领域数据，并把结果记为 调用链追踪信息的路径。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；把新的处理结果追加或合并到当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
遍历并筛选输入，将整理后的结果保存为 用例集合；遍历并筛选输入，将整理后的结果保存为 用例集合；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
如果警告有值或为真，就把警告追加或合并到当前处理结果。
如果失败用例警告有值或为真，就把失败用例警告追加或合并到当前处理结果。
如果警告有值或为真，就把警告追加或合并到当前处理结果。
复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算初始化顺序集合，并保存为 领域记录集合。
如果调用链追踪信息的路径不为空，就把新的处理结果追加或合并到领域记录集合。
计算按字段初始化键值映射，并保存为 结构化请求载荷。
如果工具调用记录不为空 且 当前字段值为空，就把新的处理结果追加或合并到结构化请求载荷。
返回结构化请求载荷的当前值。
```

#### `_render_debug_markdown`

- **源码**：`app/nodes/log_debug_node.py:870`
- **签名**：`def _render_debug_markdown(report: DebugReport) -> str`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收MCP 评测或运行报告，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `DebugReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行；计算初始化顺序集合，并保存为 论文文档章节集合。
遍历由论文文档章节集合组成的集合或迭代器，每次把当前项记为多个解包结果：
    把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
    如果待处理项集合为空或为假：
        把新的处理结果追加或合并到待输出的文本行。
    否则：
        遍历由待处理项集合组成的集合或迭代器，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行。
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/nodes/mapping_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_trace_slug`

- **源码**：`app/nodes/mapping_node.py:40`
- **签名**：`def _trace_slug(value: str) -> str`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
去除辅助操作“调用 `sub` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 当前处理结果；返回当前输入内容中的对应字段的当前值。
```

#### `_build_mapping_fallback`

- **源码**：`app/nodes/mapping_node.py:49`
- **签名**：`def _build_mapping_fallback(target: CodeMappingTarget) -> ModuleMapping`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收待定位的代码对象或业务目标，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `ModuleMapping` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `target` | `CodeMappingTarget` | 待定位的代码对象或业务目标；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`ModuleMapping`
- **语义**：返回 `ModuleMapping` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ModuleMapping` 结构化领域对象。
```

#### `_render_mapping_markdown`

- **源码**：`app/nodes/mapping_node.py:63`
- **签名**：`def _render_mapping_markdown(mappings: list[dict]) -> str`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收当前处理结果，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `mappings` | `list[dict]` | `list[dict]` 元素集合；元素代表的业务对象由参数名 `mappings` 和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为论文-代码映射：
    把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
    从论文-代码映射读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
    如果当前处理结果有值或为真：
        把新的处理结果追加或合并到待输出的文本行。
        遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
        把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
    遍历辅助操作产生的可迭代结果（从论文-代码映射读取所需的状态或领域记录），每次把当前项记为待审核的 MCP 能力候选，然后调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `join` 完成该函数的一项辅助处理，并把结果记为 证据集合；调用 `replace` 完成该函数的一项辅助处理，并把结果记为 基线接受或运行操作原因；把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行。
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_compact_excerpt`

- **源码**：`app/nodes/mapping_node.py:114`
- **签名**：`def _compact_excerpt(text: str, limit: int) -> str`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，业务输出保存有限引用，完整片段仍在 Evidence Pack Artifact。该函数接收待处理文本、结果数量上限，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `text` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `limit` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 800 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本。
如果规范化后的文本 的长度不大于结果数量上限，就返回规范化后的文本的当前值。
返回当前计算得到的结果。
```

#### `_to_business_evidence`

- **源码**：`app/nodes/mapping_node.py:129`
- **签名**：`def _to_business_evidence(evidence: CodeEvidence) -> Evidence`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，只根据已验证 CodeEvidence 构造业务 Evidence。该函数接收可追溯证据记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Evidence` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `evidence` | `CodeEvidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`Evidence`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `Evidence` 结构化领域对象。
```

#### `bind_mapping_to_evidence_pack`

- **源码**：`app/nodes/mapping_node.py:165`
- **签名**：`def bind_mapping_to_evidence_pack(mapping: ModuleMapping, pack_payload: dict, repo_path: str) -> ModuleMapping`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，将不可信模型选择绑定到当前仓库中的有效 Evidence。该函数接收论文-代码映射、当前处理结果、代码仓库根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ModuleMapping` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `mapping` | `ModuleMapping` | 论文-代码映射；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `pack_payload` | `dict` | 名为 `pack_payload` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |
| `repo_path` | `str` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`ModuleMapping`
- **语义**：返回 `ModuleMapping` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 检索或映射证据包；遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果的 ID；将 当前处理结果的路径 初始化为空映射，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理项，然后把当前处理项追加或合并到辅助操作“把目标文件路径追加或合并到当前处理结果的路径”的结果。
将 当前处理结果、当前处理结果 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为待审核的 MCP 能力候选：
    如果目标文件路径不属于当前处理结果的路径，就把新的处理结果追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
    遍历并筛选输入，将整理后的结果保存为 选中的候选项。
    如果选中的候选项为空或为假，就读取当前处理结果的路径中的对应字段中的对应字段，并保存为 选中的候选项。
    如果选中的候选项为空或为假，就把新的处理结果追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
    遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；把新的处理结果追加或合并到当前处理结果。
构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
如果当前处理结果 的长度小于待处理项集合 的长度，就把新的处理结果追加或合并到当前处理结果。
把新的处理结果追加或合并到当前处理结果；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `mapping_node`

- **源码**：`app/nodes/mapping_node.py:289`
- **签名**：`def mapping_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `mapping_targets_from_state` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象集合；从复现流程状态读取所需的状态或领域记录，并把结果记为 证据集合；从复现流程状态读取所需的状态或领域记录，并把结果记为 代码仓库根目录。
如果待定位的代码对象集合为空或为假 或 证据集合为空或为假 或 代码仓库根目录为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `build_model_gateway` 组装当前阶段需要的领域对象，并把结果记为 网关；将 当前处理结果、当前处理结果、当前处理结果 初始化为空列表，用来收集后续结果。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；读取对象名称，并保存为 待定位的代码对象或业务目标的名称；计算计算当前表达式的结果，并保存为 当前处理结果。
    如果“计算数量、边界或类型判断结果”后未得到肯定结果，就把新的处理结果追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
    调用 `format` 完成该函数的一项辅助处理，并把结果记为 发给模型的结构化提示；调用 `invoke_structured` 完成该函数的一项辅助处理，并把结果记为 工具调用记录。
    如果当前字段值不为空：
        读取当前字段值，并保存为 论文-代码映射；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
        如果Python 模块的名称不等于待定位的代码对象或业务目标的名称，就把新的处理结果追加或合并到当前处理结果。
        复制、序列化或校验结构化领域对象，并把结果记为 论文-代码映射；调用 `bind_mapping_to_evidence_pack` 完成该函数的一项辅助处理，并把结果记为 论文-代码映射。
    否则：
        调用 `_build_mapping_fallback` 组装当前阶段需要的领域对象，并把结果记为 论文-代码映射；把新的处理结果追加或合并到当前处理结果。
    调用 `write_structured_output_trace` 持久化或更新当前领域数据，并把结果记为 调用链追踪信息的路径；把新的处理结果追加或合并到当前处理结果；把新的处理结果追加或合并到当前处理结果。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 结构化请求载荷。
如果当前处理结果有值或为真，就计算按字段初始化键值映射，并保存为 状态；把新的处理结果追加或合并到结构化请求载荷。
返回结构化请求载荷的当前值。
```

### `app/nodes/method_extractor_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_build_method_extraction_fallback`

- **源码**：`app/nodes/method_extractor_node.py:63`
- **签名**：`def _build_method_extraction_fallback() -> PaperSummary`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，结构化提取失败时不编造论文方法，确保下游不会生成可执行命令。该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `PaperSummary` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`PaperSummary`
- **语义**：返回 `PaperSummary` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `PaperSummary` 结构化领域对象。
```

#### `_invocation_is_truncation`

- **源码**：`app/nodes/method_extractor_node.py:83`
- **签名**：`def _invocation_is_truncation(invocation: RoutedStructuredInvocation) -> bool`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，判断调用失败是不是因为输出在 JSON 完成前被截断。该函数接收工具调用记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `invocation` | `RoutedStructuredInvocation` | 工具调用记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
如果阶段处理结果为空，就返回固定值 `假`。
遍历当前可迭代输入，每次把当前项记为尝试：
    如果当前处理结果有值或为真，就返回固定值 `真`。
    如果错误类型有值或为真 且 当前输入内容属于辅助操作“对错误类型中的文本执行规范化或拆分”的结果，就返回固定值 `真`。
    计算根据条件从两个候选结果中选择一个，并保存为 原因。
    如果原因属于{'length', 'max_tokens', 'max_output_tokens'}，就返回固定值 `真`。
返回固定值 `假`。
```

#### `_invoke_section_attempt`

- **源码**：`app/nodes/method_extractor_node.py:105`
- **签名**：`def _invoke_section_attempt(model_gateway: 未显式标注, chunk: SectionChunk, prompt: str, state: dict, generated_records: list, attempt_label: str, route_preview: 未显式标注) -> tuple[RoutedStructuredInvocation, str]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，对单个 chunk 执行一次 preview + invoke，并登记调用 trace。该函数接收网关、检索文本块、发给模型的结构化提示、复现流程状态等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `model_gateway` | `未显式标注` | 名为 `model_gateway` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `chunk` | `SectionChunk` | 检索文本块；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `generated_records` | `list` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `attempt_label` | `str` | 名为 `attempt_label` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 '' |
| `route_preview` | `未显式标注` | 名为 `route_preview` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`tuple[RoutedStructuredInvocation, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果当前处理结果为空，就调用 `preview_structured` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
调用 `invoke_structured` 完成该函数的一项辅助处理，并把结果记为 工具调用记录；调用 `write_structured_output_trace` 持久化或更新当前领域数据，并把结果记为 调用链追踪信息的路径；把新的处理结果追加或合并到当前处理结果；返回当前构造的顺序或去重集合。
```

#### `method_extractor_node`

- **源码**：`app/nodes/method_extractor_node.py:177`
- **签名**：`def method_extractor_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果；从复现流程状态读取所需的状态或领域记录，并把结果记为 论文原文块集合的路径；从复现流程状态读取所需的状态或领域记录，并把结果记为 论文文档章节集合的路径。
如果当前处理结果为空或为假 或 论文原文块集合的路径为空或为假 或 论文文档章节集合的路径为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
复制、序列化或校验结构化领域对象，并把结果记为 论文解析文档；调用 `load_paper_blocks` 读取或查询当前阶段需要的数据，并把结果记为 论文原文块集合；调用 `load_paper_sections` 读取或查询当前阶段需要的数据，并把结果记为 论文文档章节集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果的 ID。
调用 `build_section_chunks` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；调用 `select_extraction_chunks` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `build_model_gateway` 组装当前阶段需要的领域对象，并把结果记为 网关；将 当前处理结果、章节集合、当前处理结果 初始化为空列表，用来收集后续结果；读取当前处理结果，并保存为 论文方法或 HTTP 方法；读取当前处理结果，并保存为 是否启用严格校验的开关。
读取论文版本，并保存为 版本。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为检索文本块：
    调用 `format` 完成该函数的一项辅助处理，并把结果记为 发给模型的结构化提示；计算计算当前表达式的结果，并保存为 是否论文方法或 HTTP 方法；调用 `preview_structured` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；读取当前处理结果的名称，并保存为 模型标识或模型配置的名称。
    调用 `build_section_cache_key` 组装当前阶段需要的领域对象，并把结果记为 键；调用 `load_valid_section_cache` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
    如果当前处理结果不为空：
        先尝试完成以下处理：
            调用 `validate_extraction_identity` 校验当前输入或状态；调用 `validate_extraction_evidence_references` 校验当前输入或状态。
        如果出现 `(ValueError, InvalidEvidenceReference)`并把异常保存为捕获的异常对象：
            把新的处理结果追加或合并到章节集合；计算使用固定配置或常量值，并保存为 当前处理结果。
    如果当前处理结果不为空 且 是否论文方法或 HTTP 方法有值或为真 且 “当前处理结果有值或为真”不成立，就把新的处理结果追加或合并到章节集合；计算使用固定配置或常量值，并保存为 当前处理结果。
    如果当前处理结果不为空，就调用 `resolve_artifact_path` 解析、规范化或转换当前输入，并把结果记为 当前处理结果的路径；把新的处理结果追加或合并到当前处理结果；把当前处理结果追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
    调用 `_invoke_section_attempt` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
    如果当前字段值为空 且 是否论文方法或 HTTP 方法有值或为真，就计算组合或计算已有值，并保存为 当前处理结果；调用 `_invoke_section_attempt` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；读取调用记录，并保存为 工具调用记录。
    如果当前字段值为空，就把新的处理结果追加或合并到章节集合；跳过本轮剩余处理，直接进入下一轮。
    读取当前字段值，并保存为 后续步骤使用的结果。
    如果是否论文方法或 HTTP 方法有值或为真 且 “当前处理结果有值或为真”不成立：
        计算组合或计算已有值，并保存为 当前处理结果；调用 `_invoke_section_attempt` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
        如果当前字段值不为空，就读取当前字段值，并保存为 后续步骤使用的结果。
    如果是否论文方法或 HTTP 方法有值或为真 且 “当前处理结果有值或为真”不成立，就把新的处理结果追加或合并到章节集合。
    先尝试完成以下处理：
        调用 `validate_extraction_identity` 校验当前输入或状态；调用 `validate_extraction_evidence_references` 校验当前输入或状态。
    如果出现 `(ValueError, InvalidEvidenceReference)`并把异常保存为捕获的异常对象：
        把新的处理结果追加或合并到章节集合；跳过本轮剩余处理，直接进入下一轮。
    调用 `write_section_cache` 持久化或更新当前领域数据，并把结果记为 多个解包结果；把记录追加或合并到当前处理结果；把当前处理结果追加或合并到当前处理结果。
如果当前处理结果为空或为假：
    调用 `_build_method_extraction_fallback` 组装当前阶段需要的领域对象，并把结果记为 阶段摘要；将 项目事实记录集合、当前处理结果 初始化为空列表，用来收集后续结果；把新的处理结果追加或合并到章节集合。
否则：
    调用 `reduce_section_extractions` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
    如果章节集合有值或为真，就遍历并筛选输入，将整理后的结果保存为 当前处理结果；复制、序列化或校验结构化领域对象，并把结果记为 阶段摘要。
先尝试完成以下处理：
    调用 `load_mapping_alias_rules` 读取或查询当前阶段需要的数据，并把结果记为 映射集合。
如果出现 `(TypeError, ValueError)`并把异常保存为捕获的异常对象：
    把新的处理结果追加或合并到章节集合；将 映射集合 初始化为空列表，用来收集后续结果。
计算根据条件从两个候选结果中选择一个，并保存为 错误；计算按字段初始化键值映射，并保存为 状态；调用 `build_code_mapping_targets` 组装当前阶段需要的领域对象，并把结果记为 映射结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
计算初始化顺序集合，并保存为 当前处理结果；返回包含 `paper_summary`、`method_modules`、`mapping_targets`、`mapping_targets_path` 字段的结构化映射。
```

### `app/nodes/paper_reader_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `paper_reader_node`

- **源码**：`app/nodes/paper_reader_node.py:8`
- **签名**：`def paper_reader_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 论文 PDF 路径。
如果论文 PDF 路径为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `index_paper_to_artifacts` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算按字段初始化键值映射，并保存为 当前处理结果。
如果当前状态等于'failed'，就计算按字段初始化键值映射，并保存为 状态；调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
返回前一步处理得到的结果。
```

### `app/nodes/patch_apply_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `patch_apply_node`

- **源码**：`app/nodes/patch_apply_node.py:22`
- **签名**：`def patch_apply_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 代码仓库归档包；复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告；复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；调用 `validate_patch_promotion_authorization` 校验当前输入或状态。
如果出现 `(KeyError, ValidationError, ValueError)`并把异常保存为捕获的异常对象：
    调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `str` 完成该函数的一项辅助处理，并把结果记为 本次复现运行 ID；调用 `apply_verified_patch_to_source` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
如果当前状态不等于'applied'，就计算按字段初始化键值映射，并保存为 结构化请求载荷；调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
复制、序列化或校验结构化领域对象，并把结果记为 待审批复现动作；读取代码修复补丁的 SHA-256，并保存为 待审批复现动作中的对应字段；调用 `compute_action_hash` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 Hash；计算组合或计算已有值，并保存为 模型尝试记录集合。
计算按字段初始化键值映射，并保存为 条目；返回包含 `patch_application_record`、`applied_patch_hash`、`file_repair_attempt_count`、`file_repair_history`、`pending_action`、`pending_action_hash`、`user_approval`、`human_feedback` 等字段的结构化映射。
```

### `app/nodes/patch_builder_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `patch_builder_node`

- **源码**：`app/nodes/patch_builder_node.py:16`
- **签名**：`def patch_builder_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假，就返回包含 `pending_patch`、`pending_patch_hash`、`final_status` 字段的结构化映射。
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 修复或重跑提案。
如果出现 `ValidationError`并把异常保存为捕获的异常对象：
    返回包含 `pending_patch`、`pending_patch_hash`、`final_status`、`error` 字段的结构化映射。
如果业务类别不等于'patch'，就返回包含 `pending_patch`、`pending_patch_hash`、`final_status` 字段的结构化映射。
调用 `artifact_dir` 完成该函数的一项辅助处理，并把结果记为 根目录。
先尝试完成以下处理：
    调用 `build_patch_bundle` 组装当前阶段需要的领域对象，并把结果记为 代码仓库归档包。
如果出现 `(FileNotFoundError, KeyError, OSError, ValueError)`并把异常保存为捕获的异常对象：
    返回包含 `pending_patch`、`pending_patch_hash`、`final_status`、`error` 字段的结构化映射。
调用 `with_name` 完成该函数的一项辅助处理，并把结果记为 代码仓库归档包的路径；调用 `register_existing_artifact` 完成该函数的一项辅助处理，并把结果记为 记录；调用 `register_existing_artifact` 完成该函数的一项辅助处理，并把结果记为 记录。
返回包含 `pending_patch`、`pending_patch_hash`、`patch_approval`、`patch_feedback`、`patch_approval_record`、`patch_verification_report`、`patch_verification_passed`、`patch_verification_hash` 等字段的结构化映射。
```

### `app/nodes/patch_promotion_review_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_promotion_blocked`

- **源码**：`app/nodes/patch_promotion_review_node.py:22`
- **签名**：`def _promotion_blocked(state: dict, final_status: str, error: str) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态、状态、错误信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `final_status` | `str` | 名为 `final_status` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `error` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `patch_promotion_review_node`

- **源码**：`app/nodes/patch_promotion_review_node.py:43`
- **签名**：`def patch_promotion_review_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 代码仓库归档包；复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告；调用 `validate_patch_promotion_authorization` 校验当前输入或状态，并把结果记为 当前处理结果的 Hash。
如果出现 `(KeyError, ValidationError, ValueError)`并把异常保存为捕获的异常对象：
    调用 `_promotion_blocked` 完成该函数的一项辅助处理，并返回处理结果。
调用 `interrupt` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 代码仓库归档包；复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告；调用 `validate_patch_promotion_authorization` 校验当前输入或状态，并把结果记为 当前处理结果的 Hash。
如果出现 `(KeyError, ValidationError, ValueError)`并把异常保存为捕获的异常对象：
    调用 `_promotion_blocked` 完成该函数的一项辅助处理，并返回处理结果。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就从结构化响应读取所需的状态或领域记录，并把结果记为 该调用返回的结果；从结构化响应读取所需的状态或领域记录，并把结果记为 用户修正意见；否则读取结构化响应，并保存为 后续步骤使用的结果；计算使用固定配置或常量值，并保存为 用户修正意见。
调用 `str` 完成该函数的一项辅助处理，并把结果记为 人工决策结果。
如果人工决策结果不属于{'approved', 'rejected'}，就计算使用固定配置或常量值，并保存为 人工决策结果；计算根据字段和固定文本生成格式化文本，并保存为 用户修正意见。
构造 `PatchPromotionRecord` 结构化领域对象，并把结果记为 领域记录；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回包含 `patch_promotion_decision`、`patch_promotion_feedback`、`patch_promotion_record`、`final_status`、`error` 字段的结构化映射。
```

### `app/nodes/patch_review_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `patch_review_node`

- **源码**：`app/nodes/patch_review_node.py:18`
- **签名**：`def patch_review_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 代码仓库归档包。
先尝试完成以下处理：
    调用 `validate_patch_bundle` 校验当前输入或状态。
如果出现 `(OSError, ValueError)`并把异常保存为捕获的异常对象：
    调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
读取辅助操作“把外部位置解析为文件系统路径对象”的结果中的文件内容，并把结果记为 代码修复补丁的文本；调用 `interrupt` 完成该函数的一项辅助处理，并把结果记为 结构化响应；调用 `str` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；读取当前处理结果，并保存为 人工决策结果。
从结构化响应读取所需的状态或领域记录，并把结果记为 用户修正意见。
如果人工决策结果不属于{'approved', 'rejected', 'revise'}，就计算使用固定配置或常量值，并保存为 人工决策结果；计算根据字段和固定文本生成格式化文本，并保存为 用户修正意见。
先尝试完成以下处理：
    调用 `validate_patch_bundle` 校验当前输入或状态。
如果出现 `(OSError, ValueError)`并把异常保存为捕获的异常对象：
    调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
构造 `PatchApprovalRecord` 结构化领域对象，并把结果记为 领域记录；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回包含 `patch_approval`、`patch_feedback`、`patch_approval_record` 字段的结构化映射。
```

### `app/nodes/patch_verdict_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_patch_verdict_error`

- **源码**：`app/nodes/patch_verdict_node.py:27`
- **签名**：`def _patch_verdict_error(state: dict, final_status: str, message: str) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态、状态、面向用户或日志的提示信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `final_status` | `str` | 名为 `final_status` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `patch_verdict_node`

- **源码**：`app/nodes/patch_verdict_node.py:48`
- **签名**：`def patch_verdict_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，依据 Patch Evidence 重算 verdict；绝不调用 worktree Runner。该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 代码仓库归档包；复制、序列化或校验结构化领域对象，并把结果记为 人工审批记录；复制、序列化或校验结构化领域对象，并把结果记为 可追溯证据记录。
如果出现 `ValidationError`并把异常保存为捕获的异常对象：
    调用 `_patch_verdict_error` 完成该函数的一项辅助处理，并返回处理结果。
先尝试完成以下处理：
    调用 `validate_patch_evidence_hash` 校验当前输入或状态。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    调用 `_patch_verdict_error` 完成该函数的一项辅助处理，并返回处理结果。
计算计算当前表达式的结果，并保存为 当前处理结果。
如果当前处理结果为空或为假，就调用 `_patch_verdict_error` 完成该函数的一项辅助处理，并返回处理结果。
调用 `summarize_patch_verification` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果当前状态等于'behaviorally_verified'：
    计算使用固定配置或常量值，并保存为 阶段摘要。
否则：
    如果当前状态等于'structurally_valid'：
        计算使用固定配置或常量值，并保存为 阶段摘要。
    否则：
        如果当前状态等于'failed'，就计算使用固定配置或常量值，并保存为 阶段摘要；否则计算使用固定配置或常量值，并保存为 阶段摘要。
构造 `PatchVerificationReport` 结构化领域对象，并把结果记为 草稿对象；复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算计算当前表达式的结果，并保存为 当前处理结果。
返回包含 `patch_verification_report`、`patch_verification_passed`、`patch_verification_hash`、`final_status`、`error` 字段的结构化映射。
```

### `app/nodes/patch_verification_executor_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_patch_execution_error`

- **源码**：`app/nodes/patch_verification_executor_node.py:22`
- **签名**：`def _patch_execution_error(state: dict, final_status: str, message: str) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，输入或执行环境不足时不会伪造 Patch Evidence。该函数接收复现流程状态、状态、面向用户或日志的提示信息，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `final_status` | `str` | 名为 `final_status` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `patch_verification_executor_node`

- **源码**：`app/nodes/patch_verification_executor_node.py:43`
- **签名**：`def patch_verification_executor_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，执行 worktree 检查，只输出 Evidence，不输出 promotion verdict。该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
先尝试完成以下处理：
    复制、序列化或校验结构化领域对象，并把结果记为 代码仓库归档包；复制、序列化或校验结构化领域对象，并把结果记为 人工审批记录；复制、序列化或校验结构化领域对象，并把结果记为 修复或重跑提案。
如果出现 `ValidationError`并把异常保存为捕获的异常对象：
    调用 `_patch_execution_error` 完成该函数的一项辅助处理，并返回处理结果。
如果人工决策结果不等于'approved'，就调用 `_patch_execution_error` 完成该函数的一项辅助处理，并返回处理结果。
如果代码修复补丁的 ID不等于代码修复补丁的 ID 或 代码修复补丁的 SHA-256不等于代码修复补丁的 SHA-256，就调用 `_patch_execution_error` 完成该函数的一项辅助处理，并返回处理结果。
从复现流程状态读取所需的状态或领域记录，并把结果记为 MCP Client 配置档案 ID；从复现流程状态读取所需的状态或领域记录，并把结果记为 执行环境配置指纹。
如果MCP Client 配置档案 ID为空或为假 或 执行环境配置指纹为空或为假，就调用 `_patch_execution_error` 完成该函数的一项辅助处理，并返回处理结果。
调用 `require_run_root` 完成该函数的一项辅助处理，并把结果记为 本次复现运行目录；计算组合或计算已有值，并保存为 当前处理结果的路径。
先尝试完成以下处理：
    调用 `verify_patch_in_worktree` 完成该函数的一项辅助处理，并把结果记为 运行器。
如果出现 `(OSError, ValueError)`并把异常保存为捕获的异常对象：
    调用 `_patch_execution_error` 完成该函数的一项辅助处理，并返回处理结果。
调用 `build_patch_verification_evidence` 组装当前阶段需要的领域对象，并把结果记为 可追溯证据记录；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回包含 `patch_verification_evidence` 字段的结构化映射。
```

### `app/nodes/patch_verifier_node.py`

**模块作用**：Phase 43 迁移兼容入口。

#### `patch_verifier_node`

- **源码**：`app/nodes/patch_verifier_node.py:13`
- **签名**：`def patch_verifier_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `patch_verification_executor_node` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/nodes/preflight_check_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `preflight_check_node`

- **源码**：`app/nodes/preflight_check_node.py:16`
- **签名**：`def preflight_check_node(state: dict) -> dict`
- **作用**：在把实验计划转换为可审计命令并在受控环境中执行的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 待审批复现动作。
如果待审批复现动作为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
从复现流程状态读取所需的状态或领域记录，并把结果记为 本次复现运行目录。
如果本次复现运行目录为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
从复现流程状态读取所需的状态或领域记录，并把结果记为 待执行复现动作的 Hash；调用 `build_preflight_report` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历由结果集合集合组成的集合或迭代器，每次把当前项记为阶段处理结果，然后把新的处理结果追加或合并到当前处理结果。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 结构化请求载荷。
如果“从复现流程状态读取所需的状态或领域记录”后未得到肯定结果 且 “从复现流程状态读取所需的状态或领域记录”后未得到肯定结果，就计算使用固定配置或常量值，并保存为 结构化请求载荷中的对应字段。
如果当前处理结果有值或为真，就返回结构化请求载荷的当前值。
调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/nodes/repair_action_builder_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `repair_action_builder_node`

- **源码**：`app/nodes/repair_action_builder_node.py:10`
- **签名**：`def repair_action_builder_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 修复或重跑提案。
如果修复或重跑提案为空或为假，就返回包含 `final_status`、`error` 字段的结构化映射。
调用 `int` 完成该函数的一项辅助处理，并把结果记为 模型尝试记录集合。
如果模型尝试记录集合不小于最大尝试记录集合集合，就返回包含 `final_status`、`error` 字段的结构化映射。
从修复或重跑提案读取所需的状态或领域记录，并把结果记为 业务类别；去除当前输入内容的首尾空白，并把规范化后的文本记为 命令。
如果业务类别不等于'edit_command'，就返回包含 `final_status`、`last_action_result` 字段的结构化映射。
调用 `validate_bounded_repair_command` 校验当前输入或状态，并把结果记为 多个解包结果。
如果处理是否成功的判断为空或为假，就返回包含 `final_status`、`error`、`last_action_result` 字段的结构化映射。
先尝试完成以下处理：
    调用 `apply_command_repair_to_state` 完成该函数的一项辅助处理，并把结果记为 更新后的。
如果出现 `(FileNotFoundError, KeyError, ValueError)`并把异常保存为捕获的异常对象：
    返回包含 `pending_action`、`pending_action_hash`、`final_status`、`error`、`last_action_result` 字段的结构化映射。
计算按字段初始化键值映射，并保存为 条目；返回包含 `repair_attempt_count`、`repair_history`、`user_approval`、`human_feedback`、`approval_record`、`preflight_report`、`preflight_passed`、`preflight_report_path` 等字段的结构化映射。
```

### `app/nodes/repair_planner_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_build_cuda_oom_repair_proposal`

- **源码**：`app/nodes/repair_planner_node.py:30`
- **签名**：`def _build_cuda_oom_repair_proposal(pending_action: dict) -> RepairProposal | None`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，仅缩小命令中已有的 batch 参数，不引入新的执行语义。该函数接收待审批复现动作，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RepairProposal | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `pending_action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |

**输出**

- **Python 类型**：`RepairProposal | None`
- **语义**：返回 `RepairProposal | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
去除辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 待启动实验程序；构造临时集合、映射或轻量领域对象，并把结果记为 命令行或函数位置参数集合。
如果待启动实验程序为空或为假 或 命令行或函数位置参数集合为空或为假，就返回固定值 `空值`。
构造临时集合、映射或轻量领域对象，并把结果记为 更新后的集合；计算使用固定配置或常量值，并保存为 变化的；计算使用固定配置或常量值，并保存为 当前处理结果。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    如果模型或命令 token属于当前处理结果 且 当前输入内容小于更新后的集合 的长度：
        读取更新后的集合中的对应字段，并保存为 值。
        如果值等于'1'，就返回固定值 `空值`。
        计算使用固定配置或常量值，并保存为 更新后的集合中的对应字段；计算根据字段和固定文本生成格式化文本，并保存为 变化的；计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果；立即结束当前循环。
    遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理结果：
        计算根据字段和固定文本生成格式化文本，并保存为 目录树缩进前缀。
        如果“检查模型或命令 token是否满足文本匹配条件”后得到肯定结果：
            读取模型或命令 token中的对应字段，并保存为 值。
            如果值等于'1'，就返回固定值 `空值`。
            计算根据字段和固定文本生成格式化文本，并保存为 更新后的集合中的对应字段；计算根据字段和固定文本生成格式化文本，并保存为 变化的；计算根据字段和固定文本生成格式化文本，并保存为 当前处理结果；立即结束当前循环。
    如果变化的有值或为真，就立即结束当前循环。
如果变化的为空或为假 或 当前处理结果为空或为假，就返回固定值 `空值`。
调用 `join` 完成该函数的一项辅助处理，并把结果记为 命令；构造并返回 `RepairProposal` 结构化领域对象。
```

#### `_build_no_repair_proposal`

- **源码**：`app/nodes/repair_planner_node.py:107`
- **签名**：`def _build_no_repair_proposal(error_type: str, summary: str, root_cause: str) -> RepairProposal`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，在证据不足或模型格式错误时生成保守的有界结果。该函数接收错误类型、阶段摘要、根目录，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RepairProposal` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `error_type` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `summary` | `str` | 阶段摘要；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `root_cause` | `str` | 名为 `root_cause` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`RepairProposal`
- **语义**：返回 `RepairProposal` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `RepairProposal` 结构化领域对象。
```

#### `_build_file_repair_handoff_proposal`

- **源码**：`app/nodes/repair_planner_node.py:134`
- **签名**：`def _build_file_repair_handoff_proposal(error_type: str, related_files: list[str]) -> RepairProposal`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，将证据明确的源码类错误移交给受限文件修复流程。该函数接收错误类型、相关源码文件集合，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `RepairProposal` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `error_type` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `related_files` | `list[str]` | 相关源码文件集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`RepairProposal`
- **语义**：返回 `RepairProposal` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并把结果记为 待定位的代码对象集合；构造并返回 `RepairProposal` 结构化领域对象。
```

#### `repair_planner_node`

- **源码**：`app/nodes/repair_planner_node.py:178`
- **签名**：`def repair_planner_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假：
    调用 `_build_no_repair_proposal` 组装当前阶段需要的领域对象，并把结果记为 修复或重跑提案；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 结构化请求载荷。
    调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `str` 完成该函数的一项辅助处理，并把结果记为 错误类型；计算使用固定配置或常量值，并保存为 调用链追踪信息的路径；计算使用固定配置或常量值，并保存为 工具调用记录；遍历并筛选输入，将整理后的结果保存为 相关源码文件集合。
计算使用固定配置或常量值，并保存为 当前处理结果。
如果错误类型等于'cuda_oom'：
    调用 `_build_cuda_oom_repair_proposal` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
否则：
    如果错误类型等于'shape_mismatch' 且 相关源码文件集合有值或为真，就调用 `_build_file_repair_handoff_proposal` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果。
如果当前处理结果不为空：
    读取当前处理结果，并保存为 修复或重跑提案。
否则：
    如果错误类型等于'unknown'：
        调用 `_build_no_repair_proposal` 组装当前阶段需要的领域对象，并把结果记为 修复或重跑提案。
    否则：
        调用 `format` 完成该函数的一项辅助处理，并把结果记为 发给模型的结构化提示；调用 `invoke_structured` 完成该函数的一项辅助处理，并把结果记为 工具调用记录。
        如果当前字段值不为空，就读取当前字段值，并保存为 修复或重跑提案；否则调用 `_build_no_repair_proposal` 组装当前阶段需要的领域对象，并把结果记为 修复或重跑提案。
        调用 `write_structured_output_trace` 持久化或更新当前领域数据，并把结果记为 调用链追踪信息的路径。
如果“修复或重跑提案的 ID有值或为真”不成立，就复制、序列化或校验结构化领域对象，并把结果记为 修复或重跑提案。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算初始化顺序集合，并保存为 领域记录集合。
如果调用链追踪信息的路径不为空，就把新的处理结果追加或合并到领域记录集合。
计算按字段初始化键值映射，并保存为 结构化请求载荷。
如果工具调用记录不为空 且 当前字段值为空，就把新的处理结果追加或合并到结构化请求载荷。
返回结构化请求载荷的当前值。
```

### `app/nodes/repo_scan_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `repo_scan_node`

- **源码**：`app/nodes/repo_scan_node.py:15`
- **签名**：`def repo_scan_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 代码仓库根目录。
如果代码仓库根目录为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `get_file_tree` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果；调用 `classify_repo_file` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；按稳定规则整理结果顺序，并把结果记为 该调用返回的结果；构造 `RepoMap` 结构化领域对象，并把结果记为 仓库。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算根据字段和固定文本生成格式化文本，并保存为 阶段摘要的文本；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回包含 `repo_tree`、`repo_map` 字段的结构化映射。
```

### `app/nodes/rerun_seed_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `rerun_seed_node`

- **源码**：`app/nodes/rerun_seed_node.py:11`
- **签名**：`def rerun_seed_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，普通 Job 是 no-op；派生 Job 用可信种子覆盖 LLM 候选命令。该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果当前处理结果为空，就返回当前构造的结构化映射。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
复制、序列化或校验结构化领域对象，并把结果记为 当前命令；计算按字段初始化键值映射，并保存为 结构化请求载荷；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
返回包含 `run_commands`、`edited_run_commands`、`selected_run_command_index`、`command_selection_record`、`pending_action`、`pending_action_hash`、`requires_approval`、`user_approval` 等字段的结构化映射。
```

### `app/nodes/risk_check_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `risk_check_node`

- **源码**：`app/nodes/risk_check_node.py:14`
- **签名**：`def risk_check_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 待审批复现动作。
如果待审批复现动作为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
从待审批复现动作读取所需的状态或领域记录，并把结果记为 MCP Client 配置档案 ID。
如果MCP Client 配置档案 ID为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `get_execution_profile` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案；调用 `evaluate_action_capabilities` 完成该函数的一项辅助处理，并把结果记为 人工决策结果；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 当前处理结果。
计算按字段初始化键值映射，并保存为 结构化请求载荷。
如果“当前处理结果有值或为真”不成立，就调用 `join` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
如果“当前处理结果有值或为真”不成立，就把新的处理结果追加或合并到结构化请求载荷。
返回结构化请求载荷的当前值。
```

### `app/nodes/run_context_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `run_context_node`

- **源码**：`app/nodes/run_context_node.py:15`
- **签名**：`def run_context_node(state: dict[str, Any]) -> dict[str, Any]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，为新 run 创建目录；checkpoint resume 时复用原 run。该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 已有运行的 ID；从复现流程状态读取所需的状态或领域记录，并把结果记为 已有运行的目录；从复现流程状态读取所需的状态或领域记录，并把结果记为 已有；计算计算当前表达式的结果，并保存为 本次复现运行 ID。
调用 `create_run_layout` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 期望运行的目录。
如果已有运行的目录有值或为真 且 辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果不等于期望运行的目录，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `str` 完成该函数的一项辅助处理，并把结果记为 本次复现运行目录；计算计算当前表达式的结果，并保存为 运行；计算按字段初始化键值映射，并保存为 上下文状态；计算按字段初始化键值映射，并保存为 当前处理结果。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回包含 `run_id`、`run_dir`、`run_started_at`、`stage_errors`、`artifact_records` 字段的结构化映射。
```

### `app/nodes/run_manifest_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `run_manifest_node`

- **源码**：`app/nodes/run_manifest_node.py:17`
- **签名**：`def run_manifest_node(state: dict[str, Any]) -> dict[str, Any]`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，只索引当前 run 已登记的 Artifact，不再从共享 outputs/ 复制文件。该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 状态；调用 `inspect_artifact_records` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果诊断问题集合有值或为真，就遍历并筛选输入，将整理后的结果保存为 当前处理结果；调用 `persist_stage_errors` 完成该函数的一项辅助处理，并把结果记为 错误；把错误追加或合并到状态；调用 `inspect_artifact_records` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 索引处理项；计算初始化顺序集合，并保存为 Manifest集合；调用 `build_run_manifest` 组装当前阶段需要的领域对象，并把结果记为 运行或工作区 Manifest。
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `artifact_state_update` 完成该函数的一项辅助处理，并把结果记为 Artifact；返回包含 `run_id`、`run_dir`、`stage_errors`、`active_stage_error`、`error`、`final_status`、`artifact_index_path`、`run_manifest_path` 字段的结构化映射。
```

### `app/nodes/smoke_test_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `smoke_test_node`

- **源码**：`app/nodes/smoke_test_node.py:25`
- **签名**：`def smoke_test_node(state: dict) -> dict`
- **作用**：在编排论文复现流水线、传递阶段状态并生成运行产物的阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 待审批复现动作。
如果待审批复现动作为空或为假，就调用 `stage_error_result` 完成该函数的一项辅助处理，并返回处理结果。
调用 `derive_smoke_test_action` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果当前处理结果为空，就调用 `build_smoke_test_report` 组装当前阶段需要的领域对象，并把结果记为 MCP 评测或运行报告；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；返回包含 `smoke_test_report`、`smoke_test_status`、`smoke_test_passed` 字段的结构化映射。
调用 `compute_action_hash` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 Hash；调用 `run_action_safe` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；调用 `register_execution_artifacts` 完成该函数的一项辅助处理，并把结果记为 领域记录集合；从阶段处理结果读取所需的状态或领域记录，并把结果记为 当前处理结果的路径。
计算根据条件从两个候选结果中选择一个，并保存为 当前状态；调用 `build_smoke_test_report` 组装当前阶段需要的领域对象，并把结果记为 MCP 评测或运行报告；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
计算初始化顺序集合，并保存为 当前处理结果；计算按字段初始化键值映射，并保存为 结构化请求载荷。
如果当前状态等于'passed'，就返回结构化请求载荷的当前值。
调用 `build_execution_stage_error` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；把新的处理结果追加或合并到结构化请求载荷。
如果当前处理结果的路径有值或为真，就读取当前处理结果的路径，并保存为 结构化请求载荷中的对应字段。
返回包含 `final_status` 字段的结构化映射。
```

### `app/tools/action_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_strip_leading_cd`

- **源码**：`app/tools/action_tools.py:30`
- **签名**：`def _strip_leading_cd(command: str, cwd: str) -> tuple[str, str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前命令、命令执行工作目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `cwd` | `str` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |

**输出**

- **Python 类型**：`tuple[str, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
去除当前命令的首尾空白，并把规范化后的文本记为 当前处理结果。
如果“检查当前处理结果是否满足文本匹配条件”后未得到肯定结果，就返回当前构造的顺序或去重集合。
如果当前输入内容不属于当前处理结果，就返回当前构造的顺序或去重集合。
对当前处理结果中的文本执行规范化或拆分，并把结果记为 多个解包结果；去除关系左侧实体或比较左值的首尾空白，并把规范化后的文本记为 关系左侧实体或比较左值；去除关系右侧实体或比较右值的首尾空白，并把规范化后的文本记为 关系右侧实体或比较右值。
先尝试完成以下处理：
    对当前处理结果中的文本执行规范化或拆分，并把结果记为 模型 token 用量。
如果出现 `ValueError`：
    返回当前构造的顺序或去重集合。
如果模型 token 用量 的长度等于2 且 模型 token 用量中的对应字段等于'cd'，就返回当前构造的顺序或去重集合。
返回当前构造的顺序或去重集合。
```

#### `_contains_unsupported_shell_syntax`

- **源码**：`app/tools/action_tools.py:52`
- **签名**：`def _contains_unsupported_shell_syntax(command: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前命令，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
检查由当前处理结果组成的集合或迭代器中是否存在满足“测试或状态标记属于当前命令”的项，并返回处理结果。
```

#### `_contains_bracket_placeholder`

- **源码**：`app/tools/action_tools.py:55`
- **签名**：`def _contains_bracket_placeholder(command: str) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前命令，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
先尝试完成以下处理：
    对当前处理结果中的文本执行规范化或拆分，并把结果记为 模型 token 用量。
如果出现 `ValueError`：
    对当前命令中的文本执行规范化或拆分，并把结果记为 模型 token 用量。
检查由模型 token 用量组成的集合或迭代器中是否存在满足““检查模型或命令 token是否满足文本匹配条件”后得到肯定结果 且 “检查模型或命令 token是否满足文本匹配条件”后得到肯定结果 且 模型或命令 token 的长度大于2”的项，并返回处理结果。
```

#### `_contains_placeholder`

- **源码**：`app/tools/action_tools.py:66`
- **签名**：`def _contains_placeholder(command: str) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前命令，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
对当前命令中的文本执行规范化或拆分，并把结果记为 转为小写的比较文本；返回组合判断结果。
```

#### `build_run_action_from_command`

- **源码**：`app/tools/action_tools.py:73`
- **签名**：`def build_run_action_from_command(command: str, cwd: str, source: str, reason: str, timeout_seconds: int, execution_profile_id: str, execution_profile_fingerprint: str) -> dict`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前命令、命令执行工作目录、数据来源标记、基线接受或运行操作原因等输入，用于作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `cwd` | `str` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |
| `source` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `timeout_seconds` | `int` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。；默认 300 |
| `execution_profile_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `execution_profile_fingerprint` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
调用 `_strip_leading_cd` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果“调用 `_contains_unsupported_shell_syntax` 完成该函数的一项辅助处理”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“调用 `_contains_placeholder` 完成该函数的一项辅助处理”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    对当前处理结果中的文本执行规范化或拆分，并把结果记为 模型 token 用量。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果模型 token 用量为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
构造 `ExecutableAction` 结构化领域对象，并把结果记为 待执行复现动作；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `compute_action_hash`

- **源码**：`app/tools/action_tools.py:123`
- **签名**：`def compute_action_hash(action: dict) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，审批绑定“执行什么 + 在哪里执行 + 能使用什么能力”。该函数接收待执行复现动作，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 待处理的论文或源码材料；将结构化内容序列化或编码为可传输表示，并把结果记为 结构化请求载荷；计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `build_approval_record`

- **源码**：`app/tools/action_tools.py:161`
- **签名**：`def build_approval_record(action: dict, action_hash: str, decision: str, risk_level: str, comment: str | None) -> dict`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待执行复现动作、待执行复现动作的 Hash、人工决策结果、等级等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `action_hash` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `decision` | `str` | 人工审批或决策记录；必须与目标动作 Hash、版本和允许操作一致。 |
| `risk_level` | `str` | 名为 `risk_level` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `comment` | `str | None` | 名为 `comment` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
构造 `ApprovalRecord` 结构化领域对象，并把结果记为 领域记录；复制、序列化或校验结构化领域对象，并返回处理结果。
```

### `app/tools/artifact_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/tools/artifact_tools.py:36`
- **签名**：`def utc_now() -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，统一使用 UTC ISO-8601，便于跨时区比较和排序。该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_slugify`

- **源码**：`app/tools/artifact_tools.py:41`
- **签名**：`def _slugify(value: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
对当前字段值中的文本执行规范化或拆分，再对返回文本执行规范化或拆分，并把结果记为 转为小写的比较文本；调用 `sub` 完成该函数的一项辅助处理，并把结果记为 转为小写的比较文本；返回组合判断结果。
```

#### `build_run_id`

- **源码**：`app/tools/artifact_tools.py:46`
- **签名**：`def build_run_id(task_id: str | None) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前处理结果的 ID，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `task_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
调用 `_slugify` 完成该函数的一项辅助处理，并把结果记为 目录树缩进前缀；调用 `strftime` 完成该函数的一项辅助处理，并把结果记为 状态事件时间戳；读取前一步操作返回对象的当前处理结果中的对应字段，并保存为 文件扩展名或文本后缀；返回当前计算得到的结果。
```

#### `create_run_layout`

- **源码**：`app/tools/artifact_tools.py:52`
- **签名**：`def create_run_layout(run_id: str, run_root_override: str | Path | None) -> dict[str, str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，创建当前 run 的标准目录。该函数接收本次复现运行 ID、运行根目录，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `run_root_override` | `str | Path | None` | 名为 `run_root_override` 的 `str | Path | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`dict[str, str]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
如果本次复现运行 ID为空或为假 或 前一步操作返回对象的对象名称不等于本次复现运行 ID 或 本次复现运行 ID属于{'.', '..'}，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果运行根目录为空，就将当前输入内容规范化为受控的绝对路径，并把结果记为 运行产物根目录；否则将辅助操作“将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径”的结果规范化为受控的绝对路径，并把结果记为 运行产物根目录。
调用 `create_run_layout_at` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `require_run_root`

- **源码**：`app/tools/artifact_tools.py:74`
- **签名**：`def require_run_root(state: dict[str, Any]) -> Path`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，读取并校验 state.run_dir。该函数接收复现流程状态，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 运行的目录。
如果运行的目录为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `require_managed_run_root` 完成该函数的一项辅助处理，并把结果记为 运行产物根目录；创建运行产物根目录对应的目录；返回运行产物根目录的当前值。
```

#### `resolve_artifact_path`

- **源码**：`app/tools/artifact_tools.py:89`
- **签名**：`def resolve_artifact_path(state: dict[str, Any], relative_path: str) -> Path`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把 run 内相对路径解析为绝对路径。该函数接收复现流程状态、仓库内相对路径，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
构造 `PurePosixPath` 结构化领域对象，并把结果记为 当前处理结果的路径。
如果“调用 `is_absolute` 校验当前输入或状态”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前输入内容属于拆分后的文本或路径片段集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果拆分后的文本或路径片段集合 的长度小于2，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果拆分后的文本或路径片段集合中的对应字段不属于Artifact集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `require_run_root` 完成该函数的一项辅助处理，并把结果记为 运行产物根目录；将辅助操作“调用 `joinpath` 完成该函数的一项辅助处理”的结果规范化为受控的绝对路径，并把结果记为 待定位的代码对象或业务目标。
如果待定位的代码对象或业务目标等于运行产物根目录 或 运行产物根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回待定位的代码对象或业务目标的当前值。
```

#### `artifact_dir`

- **源码**：`app/tools/artifact_tools.py:126`
- **签名**：`def artifact_dir(state: dict[str, Any], layer: str, *parts: str) -> Path`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，给需要自行生成多个文件的旧工具提供受控目录。该函数接收复现流程状态、当前处理结果、拆分后的文本或路径片段集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `layer` | `str` | 名为 `layer` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `*parts` | `str` | 额外位置参数序列。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并把结果记为 文件扩展名或文本后缀；调用 `resolve_artifact_path` 解析、规范化或转换当前输入，并把结果记为 测试或状态标记；读取父级目录或父领域对象，并保存为 后续步骤使用的结果；创建当前处理结果对应的目录。
返回前一步处理得到的结果。
```

#### `sha256_file`

- **源码**：`app/tools/artifact_tools.py:139`
- **签名**：`def sha256_file(path: Path) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，计算磁盘文件 SHA-256；文件不存在时由 open() 明确报错。该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并把结果记为 内容摘要。
进入上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给文件”，退出时自动清理资源：
    遍历辅助操作产生的可迭代结果（调用 `iter` 完成该函数的一项辅助处理），每次把当前项记为检索文本块，然后把检索文本块追加或合并到内容摘要。
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `try_get_git_commit`

- **源码**：`app/tools/artifact_tools.py:148`
- **签名**：`def try_get_git_commit(repo_path: str | None) -> str | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收代码仓库根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `str | None` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果代码仓库根目录为空或为假，就返回固定值 `空值`。
把外部位置解析为文件系统路径对象，并把结果记为 代码仓库的目录。
如果“检查代码仓库的目录的文件系统属性”后未得到肯定结果，就返回固定值 `空值`。
调用 `run` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果当前处理结果不等于0，就返回固定值 `空值`。
去除进程标准输出的首尾空白，并把规范化后的文本记为 当前处理结果；返回组合判断结果。
```

#### `try_is_git_clean`

- **源码**：`app/tools/artifact_tools.py:169`
- **签名**：`def try_is_git_clean(repo_path: str | None) -> bool | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，返回受管仓库是否 clean；无法确认时返回 None，不猜测。该函数接收代码仓库根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `bool | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `str | None` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`bool | None`
- **语义**：返回 `bool | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果代码仓库根目录为空或为假，就返回固定值 `空值`。
把外部位置解析为文件系统路径对象，并把结果记为 代码仓库的目录。
如果“检查代码仓库的目录的文件系统属性”后未得到肯定结果，就返回固定值 `空值`。
调用 `run` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果当前处理结果不等于0，就返回固定值 `空值`。
返回当前计算得到的结果。
```

#### `build_run_manifest`

- **源码**：`app/tools/artifact_tools.py:195`
- **签名**：`def build_run_manifest(state: dict[str, Any], artifact_records: list[dict[str, Any]]) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收复现流程状态、Artifact集合，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `artifact_records` | `list[dict[str, Any]]` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从复现流程状态读取所需的状态或领域记录，并把结果记为 选中候选项的索引；计算计算当前表达式的结果，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 命令。
如果“计算数量、边界或类型判断结果”后得到肯定结果 且 当前输入内容不大于选中候选项的索引小于当前处理结果 的长度，就读取当前处理结果中的对应字段，并保存为 命令。
构造临时集合、映射或轻量领域对象，并把结果记为 阶段集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果；调用 `sum` 完成该函数的一项辅助处理，并把结果记为 当前值的数量；返回包含 `manifest_version`、`job_id`、`thread_id`、`run_id`、`task_id`、`run_dir`、`run_started_at`、`manifest_generated_at` 等字段的结构化映射。
```

#### `_atomic_write_bytes`

- **源码**：`app/tools/artifact_tools.py:342`
- **签名**：`def _atomic_write_bytes(path: Path, data: bytes) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，在目标目录内写临时文件，再使用 os.replace 原子替换。该函数接收文件或目录路径、待处理数据，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `data` | `bytes` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
创建父级目录或父领域对象对应的目录；调用 `with_name` 完成该函数的一项辅助处理，并把结果记为 临时的路径。
先尝试完成以下处理：
    在上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给文件”中向终端或输出流写出当前结果/诊断信息；提交文件中已完成的数据变更；调用 `fsync` 完成该函数的一项辅助处理，退出时自动清理资源。
    调用 `replace` 完成该函数的一项辅助处理。
无论成功还是失败，最后都要：
    如果“检查临时的路径的文件系统属性”后得到肯定结果，就调用 `unlink` 完成该函数的一项辅助处理。
```

#### `_guess_media_type`

- **源码**：`app/tools/artifact_tools.py:364`
- **签名**：`def _guess_media_type(path: Path) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `guess_type` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果Artifact 媒体类型有值或为真，就返回Artifact 媒体类型的当前值。
如果文件扩展名或文本后缀等于'.log'，就返回固定值 `'text/plain'`。
返回固定值 `'application/octet-stream'`。
```

#### `_artifact_id`

- **源码**：`app/tools/artifact_tools.py:372`
- **签名**：`def _artifact_id(run_id: str, relative_path: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收本次复现运行 ID、仓库内相对路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并把结果记为 待处理的论文或源码材料；返回当前计算得到的结果。
```

#### `build_artifact_record`

- **源码**：`app/tools/artifact_tools.py:376`
- **签名**：`def build_artifact_record(state: dict[str, Any], path: Path, producer_node: str, media_type: str | None) -> ArtifactRecord`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，为已经完整写入磁盘的文件生成元数据。该函数接收复现流程状态、文件或目录路径、产生当前状态的流程节点、Artifact 媒体类型，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `producer_node` | `str` | 产生当前状态的流程节点；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `media_type` | `str | None` | Artifact 媒体类型；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ArtifactRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `require_run_root` 完成该函数的一项辅助处理，并把结果记为 运行产物根目录；将文件或目录路径规范化为受控的绝对路径，并把结果记为 解析后的值的路径。
如果运行产物根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“检查解析后的值的路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
把辅助操作“把解析后的值的路径转换为稳定的仓库相对路径表示”的结果转换为稳定的仓库相对路径表示，并把结果记为 仓库内相对路径；读取前一步操作返回对象中的对应字段，并保存为 后续步骤使用的结果。
如果当前处理结果不属于Artifact集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `str` 完成该函数的一项辅助处理，并把结果记为 本次复现运行 ID。
如果本次复现运行 ID为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
构造并返回 `ArtifactRecord` 结构化领域对象。
```

#### `write_bytes_artifact`

- **源码**：`app/tools/artifact_tools.py:414`
- **签名**：`def write_bytes_artifact(state: dict[str, Any], relative_path: str, data: bytes, producer_node: str, media_type: str | None, redactor: SecretRedactor | None) -> tuple[Path, ArtifactRecord]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，原子写入并立即生成 ArtifactRecord。该函数接收复现流程状态、仓库内相对路径、待处理数据、产生当前状态的流程节点等输入，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `data` | `bytes` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `producer_node` | `str` | 产生当前状态的流程节点；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `media_type` | `str | None` | Artifact 媒体类型；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `redactor` | `SecretRedactor | None` | 敏感信息脱敏器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`tuple[Path, ArtifactRecord]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果敏感信息脱敏器不为空 且 “调用 `contains_secret_bytes` 完成该函数的一项辅助处理”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `resolve_artifact_path` 解析、规范化或转换当前输入，并把结果记为 文件或目录路径；调用 `_atomic_write_bytes` 完成该函数的一项辅助处理；调用 `build_artifact_record` 组装当前阶段需要的领域对象，并把结果记为 领域记录；返回当前构造的顺序或去重集合。
```

#### `write_text_artifact`

- **源码**：`app/tools/artifact_tools.py:442`
- **签名**：`def write_text_artifact(state: dict[str, Any], relative_path: str, text: str, producer_node: str, media_type: str, redactor: SecretRedactor | None) -> tuple[Path, ArtifactRecord]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，Phase 41: 如果 redactor 非空，先脱敏再写入。该函数接收复现流程状态、仓库内相对路径、待处理文本、产生当前状态的流程节点等输入，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `text` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `producer_node` | `str` | 产生当前状态的流程节点；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `media_type` | `str` | Artifact 媒体类型；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'text/plain' |
| `redactor` | `SecretRedactor | None` | 敏感信息脱敏器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`tuple[Path, ArtifactRecord]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果敏感信息脱敏器不为空，就调用 `redact_text` 解析、规范化或转换当前输入，并把结果记为 当前处理结果的文本；否则读取待处理文本，并保存为 当前处理结果的文本。
调用 `write_bytes_artifact` 持久化或更新当前领域数据，并返回处理结果。
```

#### `write_json_artifact`

- **源码**：`app/tools/artifact_tools.py:465`
- **签名**：`def write_json_artifact(state: dict[str, Any], relative_path: str, payload: Any, producer_node: str, redactor: SecretRedactor | None) -> tuple[Path, ArtifactRecord]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，Phase 41: 如果 redactor 非空，先对 payload 做对象级脱敏。该函数接收复现流程状态、仓库内相对路径、结构化请求载荷、产生当前状态的流程节点等输入，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `payload` | `Any` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `producer_node` | `str` | 产生当前状态的流程节点；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `redactor` | `SecretRedactor | None` | 敏感信息脱敏器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`tuple[Path, ArtifactRecord]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果敏感信息脱敏器不为空，就调用 `redact_object` 解析、规范化或转换当前输入，并把结果记为 该调用返回的结果；否则读取结构化请求载荷，并保存为 后续步骤使用的结果。
计算组合或计算已有值，并保存为 待处理文本；调用 `write_text_artifact` 持久化或更新当前领域数据，并返回处理结果。
```

#### `register_existing_artifact`

- **源码**：`app/tools/artifact_tools.py:493`
- **签名**：`def register_existing_artifact(state: dict[str, Any], path: str | Path, producer_node: str, media_type: str | None) -> ArtifactRecord`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，登记由已有工具生成的文件。该函数接收复现流程状态、文件或目录路径、产生当前状态的流程节点、Artifact 媒体类型，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `path` | `str | Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `producer_node` | `str` | 产生当前状态的流程节点；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `media_type` | `str | None` | Artifact 媒体类型；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`ArtifactRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `build_artifact_record` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `merge_artifact_records`

- **源码**：`app/tools/artifact_tools.py:514`
- **签名**：`def merge_artifact_records(existing: list[dict[str, Any]], new_records: list[ArtifactRecord | dict[str, Any]]) -> list[dict[str, Any]]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，按 relative_path upsert。该函数接收已有记录、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `existing` | `list[dict[str, Any]]` | 已有记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `new_records` | `list[ArtifactRecord | dict[str, Any]]` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`list[dict[str, Any]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 当前处理结果 初始化为空列表，用来收集后续结果；将 当前处理结果的路径 初始化为空映射，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为记录：
    复制、序列化或校验结构化领域对象，并把结果记为 领域记录；读取领域记录中的对应字段，并保存为 仓库内相对路径。
    如果仓库内相对路径不属于当前处理结果的路径，就把仓库内相对路径追加或合并到当前处理结果。
    读取领域记录，并保存为 当前处理结果的路径中的对应字段。
返回当前计算得到的结果。
```

#### `artifact_state_update`

- **源码**：`app/tools/artifact_tools.py:537`
- **签名**：`def artifact_state_update(state: dict[str, Any], records: list[ArtifactRecord | dict[str, Any]]) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，同时维护新 artifact_records 和兼容字段 output_files。该函数接收复现流程状态、领域记录集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `records` | `list[ArtifactRecord | dict[str, Any]]` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `merge_artifact_records` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；将 当前处理结果 初始化为空列表，用来收集后续结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为文件或目录路径：
    如果文件或目录路径不属于当前处理结果，就把文件或目录路径追加或合并到当前处理结果；把文件或目录路径追加或合并到当前处理结果。
返回包含 `artifact_records`、`output_files` 字段的结构化映射。
```

#### `inspect_artifact_records`

- **源码**：`app/tools/artifact_tools.py:563`
- **签名**：`def inspect_artifact_records(state: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，在生成 Artifact Index 前重新检查路径和 hash。该函数接收复现流程状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`tuple[list[dict[str, Any]], list[dict[str, str]]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `require_run_root` 完成该函数的一项辅助处理，并把结果记为 运行产物根目录；将 当前处理结果、诊断问题集合 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（从复现流程状态读取所需的状态或领域记录），每次把当前项记为记录：
    先尝试完成以下处理：
        复制、序列化或校验结构化领域对象，并把结果记为 领域记录。
    如果出现 `ValidationError`并把异常保存为捕获的异常对象：
        把新的处理结果追加或合并到诊断问题集合；跳过本轮剩余处理，直接进入下一轮。
    将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 文件或目录路径；计算使用固定配置或常量值，并保存为 当前状态；计算使用固定配置或常量值，并保存为 诊断或错误详情。
    如果文件或目录路径等于运行产物根目录 或 运行产物根目录不属于当前处理结果：
        计算使用固定配置或常量值，并保存为 当前状态；计算使用固定配置或常量值，并保存为 诊断或错误详情。
    否则：
        如果“检查文件或目录路径的文件系统属性”后未得到肯定结果：
            计算使用固定配置或常量值，并保存为 当前状态；计算使用固定配置或常量值，并保存为 诊断或错误详情。
        否则：
            调用 `sha256_file` 计算内容身份、分数或派生结果，并把结果记为 当前值的 Hash。
            如果当前值的 Hash不等于内容 SHA-256，就计算使用固定配置或常量值，并保存为 当前状态；计算根据字段和固定文本生成格式化文本，并保存为 诊断或错误详情。
    把新的处理结果追加或合并到当前处理结果。
    如果当前状态不等于'current'，就把新的处理结果追加或合并到诊断问题集合。
返回当前构造的顺序或去重集合。
```

### `app/tools/error_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `utc_now`

- **源码**：`app/tools/error_tools.py:43`
- **签名**：`def utc_now() -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `isoformat` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `sanitize_error_message`

- **源码**：`app/tools/error_tools.py:47`
- **签名**：`def sanitize_error_message(value: object, max_chars: int = 4000) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，错误报告不能把 API Key 等值原样写入 Artifact。该函数接收当前字段值、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `object` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 4000 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
加载这一步需要的外部依赖；调用 `_unified_sanitize` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `is_transient_provider_error`

- **源码**：`app/tools/error_tools.py:62`
- **签名**：`def is_transient_provider_error(exc: BaseException) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，只识别常见传输、限流和服务端瞬时错误。该函数接收捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
对当前输入内容中的文本执行规范化或拆分，并把结果记为 待处理的论文或源码材料；计算组合多个值形成元组，并保存为 当前处理结果；检查由当前处理结果组成的集合或迭代器中是否存在满足“测试或状态标记属于待处理的论文或源码材料”的项，并返回处理结果。
```

#### `classify_exception`

- **源码**：`app/tools/error_tools.py:83`
- **签名**：`def classify_exception(stage: str, exc: BaseException) -> tuple[str, str, bool]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，返回 category、code、retryable。该函数接收流水线阶段、捕获的异常，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`tuple[str, str, bool]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果：
    如果流水线阶段属于{'input_validation', 'paper_reader', 'repo_scan'}，就返回当前构造的顺序或去重集合。
    返回当前构造的顺序或去重集合。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前构造的顺序或去重集合。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前构造的顺序或去重集合。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前构造的顺序或去重集合。
如果流水线阶段属于模型服务商集合，就返回当前构造的顺序或去重集合。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回当前构造的顺序或去重集合。
返回当前构造的顺序或去重集合。
```

#### `final_status_for_category`

- **源码**：`app/tools/error_tools.py:123`
- **签名**：`def final_status_for_category(category: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收评测类别，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `category` | `str` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
从当前输入内容读取所需的状态或领域记录，并返回处理结果。
```

#### `build_stage_error`

- **源码**：`app/tools/error_tools.py:133`
- **签名**：`def build_stage_error(stage: str, code: str, category: str, message: str, retryable: bool, terminal: bool, exception_type: str | None, context: dict[str, Any] | None) -> StageError`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，构造不包含完整 traceback 的错误记录。该函数接收流水线阶段、待解析或验证的代码、评测类别、面向用户或日志的提示信息等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `StageError` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `code` | `str` | 待解析、执行或断言的代码文本；处理前应处于受控测试/执行边界内。 |
| `category` | `str` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |
| `retryable` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |
| `terminal` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 真 |
| `exception_type` | `str | None` | 异常、错误记录或错误分类信息，用于失败处理和诊断。；默认 空值 |
| `context` | `dict[str, Any] | None` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`StageError`
- **语义**：返回 `StageError` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `StageError` 结构化领域对象。
```

#### `render_error_report_markdown`

- **源码**：`app/tools/error_tools.py:160`
- **签名**：`def render_error_report_markdown(errors: list[dict[str, Any]]) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收错误信息集合，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `errors` | `list[dict[str, Any]]` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回整理、格式化或规范化后的文本表示。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行。
如果错误信息集合为空或为假，就把新的处理结果追加或合并到待输出的文本行；调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    复制、序列化或校验结构化领域对象，并把结果记为 错误信息；把新的处理结果追加或合并到待输出的文本行。
    如果Artifact的路径有值或为真，就把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行。
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `persist_stage_errors`

- **源码**：`app/tools/error_tools.py:195`
- **签名**：`def persist_stage_errors(state: dict[str, Any], new_errors: list[StageError], tracebacks: dict[str, str] | None) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把新错误追加到 state，并重写当前 run 的汇总 Error Report。该函数接收复现流程状态、当前处理结果、当前处理结果，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `new_errors` | `list[StageError]` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `tracebacks` | `dict[str, str] | None` | 名为 `tracebacks` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。；默认 空值 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；将 领域记录集合 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为错误信息：
    从当前处理结果读取所需的状态或领域记录，并把结果记为 异常堆栈文本的文本。
    如果异常堆栈文本的文本有值或为真：
        先尝试完成以下处理：
            调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；把记录追加或合并到领域记录集合；复制、序列化或校验结构化领域对象，并把结果记为 错误信息。
        如果出现 `(OSError, ValueError)`：
            不执行额外操作。
    把错误信息追加或合并到当前处理结果。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；计算按字段初始化键值映射，并保存为 状态。
先尝试完成以下处理：
    调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；把新的处理结果追加或合并到领域记录集合；计算按字段初始化键值映射，并保存为 当前处理结果。
如果出现 `(OSError, ValueError)`：
    将 当前处理结果 初始化为空映射，用来收集后续结果。
读取当前处理结果中的对应字段，并保存为 错误；计算按字段初始化键值映射，并保存为 当前处理结果。
如果流程是否已进入终止状态的判断有值或为真，就调用 `final_status_for_category` 完成该函数的一项辅助处理，并把结果记为 当前处理结果中的对应字段。
如果领域记录集合有值或为真，就把新的处理结果追加或合并到当前处理结果。
返回前一步处理得到的结果。
```

#### `stage_error_result`

- **源码**：`app/tools/error_tools.py:293`
- **签名**：`def stage_error_result(state: dict[str, Any], stage: str, code: str, category: str, message: str, terminal: bool, retryable: bool, context: dict[str, Any] | None, extra_update: dict[str, Any] | None) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，给可预期业务错误使用，不需要先抛 Python Exception。该函数接收复现流程状态、流水线阶段、待解析或验证的代码、评测类别等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `code` | `str` | 待解析、执行或断言的代码文本；处理前应处于受控测试/执行边界内。 |
| `category` | `str` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |
| `terminal` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 真 |
| `retryable` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |
| `context` | `dict[str, Any] | None` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `extra_update` | `dict[str, Any] | None` | 名为 `extra_update` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。；默认 空值 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `build_stage_error` 组装当前阶段需要的领域对象，并把结果记为 错误信息；计算计算当前表达式的结果，并保存为 当前处理结果；计算按字段初始化键值映射，并保存为 状态；调用 `persist_stage_errors` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
计算按字段初始化键值映射，并保存为 阶段处理结果。
如果当前输入内容属于当前处理结果，就读取当前处理结果中的对应字段，并保存为 阶段处理结果中的对应字段。
返回阶段处理结果的当前值。
```

#### `build_structured_stage_error`

- **源码**：`app/tools/error_tools.py:337`
- **签名**：`def build_structured_stage_error(stage: str, invocation: Any, terminal: bool, context: dict[str, Any] | None) -> StageError`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把 StructuredInvocationResult 的最终失败转换成 StageError。该函数接收流水线阶段、工具调用记录、流程是否已进入终止状态的判断、运行上下文，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `StageError` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `invocation` | `Any` | 工具调用记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `terminal` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `context` | `dict[str, Any] | None` | 运行上下文；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`StageError`
- **语义**：返回 `StageError` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 模型尝试记录集合；计算根据条件从两个候选结果中选择一个，并保存为 尝试；调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 当前状态；调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 面向用户或日志的提示信息。
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 类型。
如果当前状态等于'invoke_error'：
    计算使用固定配置或常量值，并保存为 评测类别；计算使用固定配置或常量值，并保存为 待解析或验证的代码；检查当前可迭代输入中是否存在满足“测试或状态标记属于辅助操作“调用 `str` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分”的结果”的项，并把结果记为 是否允许重试的判断。
否则：
    如果当前状态等于'configuration_error'，就计算使用固定配置或常量值，并保存为 评测类别；计算使用固定配置或常量值，并保存为 待解析或验证的代码；计算使用固定配置或常量值，并保存为 是否允许重试的判断；否则计算使用固定配置或常量值，并保存为 评测类别；计算使用固定配置或常量值，并保存为 待解析或验证的代码；计算使用固定配置或常量值，并保存为 是否允许重试的判断。
遍历并筛选输入，将整理后的结果保存为 尝试集合；调用 `build_stage_error` 组装当前阶段需要的领域对象，并返回处理结果。
```

#### `structured_failure_update`

- **源码**：`app/tools/error_tools.py:431`
- **签名**：`def structured_failure_update(state: dict[str, Any], stage: str, invocation: Any, terminal: bool) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，登记一次结构化调用最终失败，并重写当前 run 的 Error Report。该函数接收复现流程状态、流水线阶段、工具调用记录、流程是否已进入终止状态的判断，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `invocation` | `Any` | 工具调用记录；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `terminal` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `build_structured_stage_error` 组装当前阶段需要的领域对象，并把结果记为 错误信息；调用 `persist_stage_errors` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `exception_to_stage_error_update`

- **源码**：`app/tools/error_tools.py:451`
- **签名**：`def exception_to_stage_error_update(state: dict[str, Any], stage: str, exc: BaseException) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收复现流程状态、流水线阶段、捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `exc` | `BaseException` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `classify_exception` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `build_stage_error` 组装当前阶段需要的领域对象，并把结果记为 错误信息；调用 `join` 完成该函数的一项辅助处理，并把结果记为 异常堆栈文本的文本。
先尝试完成以下处理：
    调用 `ensure_error_run_context` 完成该函数的一项辅助处理，并把结果记为 状态；返回当前构造的结构化映射。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    复制、序列化或校验结构化领域对象，并把结果记为 错误；返回包含 `stage_errors`、`active_stage_error`、`error`、`final_status` 字段的结构化映射。
```

#### `has_terminal_stage_error`

- **源码**：`app/tools/error_tools.py:518`
- **签名**：`def has_terminal_stage_error(state: dict[str, Any]) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收复现流程状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
遍历辅助操作产生的可迭代结果（从复现流程状态读取所需的状态或领域记录），每次把当前项记为当前处理项：
    先尝试完成以下处理：
        如果前一步操作返回对象的流程是否已进入终止状态的判断有值或为真，就返回固定值 `真`。
    如果出现 `ValidationError`：
        返回固定值 `真`。
返回固定值 `假`。
```

#### `guard_node`

- **源码**：`app/tools/error_tools.py:529`
- **签名**：`def guard_node(node_name: str, node: NodeCallable) -> NodeCallable`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，为 Graph 节点增加统一异常边界。该函数接收当前流程节点的名称、当前流程节点，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终标注为 `NodeCallable` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `node` | `NodeCallable` | 可调用依赖；其参数和返回契约由类型标注限定。 |

**输出**

- **Python 类型**：`NodeCallable`
- **语义**：返回 `NodeCallable` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
定义内部辅助函数 `wrapped`，供当前函数在后续步骤中调用。
返回前一步处理得到的结果。
```

#### `guard_node.wrapped`

- **源码**：`app/tools/error_tools.py:541`
- **签名**：`def wrapped(state: dict[str, Any]) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收复现流程状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
先尝试完成以下处理：
    调用 `node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；从阶段处理结果读取所需的状态或领域记录，并把结果记为 错误。
    如果错误有值或为真 且 “从阶段处理结果读取所需的状态或领域记录”后未得到肯定结果，就调用 `build_stage_error` 组装当前阶段需要的领域对象，并把结果记为 错误信息；计算按字段初始化键值映射，并保存为 状态；返回当前构造的结构化映射。
    返回阶段处理结果的当前值。
如果出现 `GraphInterrupt`：
    重新抛出当前异常，保持原始失败信息。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    调用 `exception_to_stage_error_update` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `ensure_error_run_context`

- **源码**：`app/tools/error_tools.py:580`
- **签名**：`def ensure_error_run_context(state: dict[str, Any]) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，错误边界的应急 run context。该函数接收复现流程状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
如果“从复现流程状态读取所需的状态或领域记录”后得到肯定结果 且 “从复现流程状态读取所需的状态或领域记录”后得到肯定结果，就返回复现流程状态的当前值。
调用 `str` 完成该函数的一项辅助处理，并把结果记为 本次复现运行 ID；调用 `create_run_layout` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；返回包含 `run_id`、`run_dir`、`run_started_at` 字段的结构化映射。
```

### `app/tools/exec_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_execution_failure`

- **源码**：`app/tools/exec_tools.py:23`
- **签名**：`def _execution_failure(message: str, end_reason: str, profile_id: str | None) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收面向用户或日志的提示信息、原因、MCP Client 配置档案 ID，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |
| `end_reason` | `str` | 名为 `end_reason` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `profile_id` | `str | None` | MCP Client 配置档案 ID；用于区分连接地址、协议版本和能力基线。；默认 空值 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `ok`、`returncode`、`end_reason`、`stdout`、`stderr`、`combined_output`、`timeout`、`cancelled` 等字段的结构化映射。
```

#### `run_action_safe`

- **源码**：`app/tools/exec_tools.py:45`
- **签名**：`def run_action_safe(action: dict, state: dict, stage: str) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，校验 profile 指纹后，把 Action 交给受监管 Runner。该函数接收待执行复现动作、复现流程状态、流水线阶段，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
从待执行复现动作读取所需的状态或领域记录，并把结果记为 MCP Client 配置档案 ID。
如果MCP Client 配置档案 ID为空或为假，就调用 `_execution_failure` 完成该函数的一项辅助处理，并返回处理结果。
从复现流程状态读取所需的状态或领域记录，并把结果记为 本次复现运行目录。
如果本次复现运行目录为空或为假，就调用 `_execution_failure` 完成该函数的一项辅助处理，并返回处理结果。
先尝试完成以下处理：
    调用 `get_execution_profile` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 当前指纹。
如果出现 `(FileNotFoundError, KeyError, ValueError)`并把异常保存为捕获的异常对象：
    调用 `_execution_failure` 完成该函数的一项辅助处理，并返回处理结果。
从待执行复现动作读取所需的状态或领域记录，并把结果记为 期望指纹。
如果期望指纹不等于当前指纹，就调用 `_execution_failure` 完成该函数的一项辅助处理，并返回处理结果。
调用 `build_execution_runner` 组装当前阶段需要的领域对象，并把结果记为 运行调度器；计算使用固定配置或常量值，并保存为 运行时上下文。
如果模型或检索后端等于'oci'：
    从复现流程状态读取所需的状态或领域记录，并把结果记为 绑定。
    如果绑定为空或为假，就调用 `_execution_failure` 完成该函数的一项辅助处理，并返回处理结果。
    加载这一步需要的外部依赖；加载这一步需要的外部依赖；构造 `ExecutionRuntimeContext` 结构化领域对象，并把结果记为 运行时上下文。
调用 `run` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `register_execution_artifacts`

- **源码**：`app/tools/exec_tools.py:131`
- **签名**：`def register_execution_artifacts(state: dict, result: dict[str, Any], producer_node: str) -> list`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，登记 Supervisor 已经完整关闭并 fsync 的执行文件。该函数接收复现流程状态、阶段处理结果、产生当前状态的流程节点，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `list` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `result` | `dict[str, Any]` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `producer_node` | `str` | 产生当前状态的流程节点；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list`
- **语义**：返回 `list` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算初始化顺序集合，并保存为 候选结果集合；将 领域记录集合 初始化为空列表，用来收集后续结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历由候选结果集合组成的集合或迭代器，每次把当前项记为多个解包结果：
    如果原始内容的路径为空或为假 或 原始内容的路径属于当前处理结果，就跳过本轮剩余处理，直接进入下一轮。
    把原始内容的路径追加或合并到当前处理结果；把新的处理结果追加或合并到领域记录集合。
返回领域记录集合的当前值。
```

#### `build_execution_stage_error`

- **源码**：`app/tools/exec_tools.py:165`
- **签名**：`def build_execution_stage_error(stage: str, result: dict[str, Any], log_path: str | None) -> tuple[StageError, str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把 Process Supervisor 事实映射到 Phase 15 StageError。该函数接收流水线阶段、阶段处理结果、运行日志路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `result` | `dict[str, Any]` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `log_path` | `str | None` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`tuple[StageError, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `str` 完成该函数的一项辅助处理，并把结果记为 基线接受或运行操作原因；计算按字段初始化键值映射，并保存为 运行上下文。
如果基线接受或运行操作原因等于'exited'，就返回当前构造的顺序或去重集合。
如果基线接受或运行操作原因属于资源集合，就返回当前构造的顺序或去重集合。
如果基线接受或运行操作原因属于{'cancelled', 'interrupted'}，就返回当前构造的顺序或去重集合。
如果基线接受或运行操作原因等于'policy_denied'，就返回当前构造的顺序或去重集合。
如果基线接受或运行操作原因等于'launch_error'，就返回当前构造的顺序或去重集合。
返回当前构造的顺序或去重集合。
```

### `app/tools/log_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `read_log`

- **源码**：`app/tools/log_tools.py:18`
- **签名**：`def read_log(path: str, max_chars: int = 30000) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收文件或目录路径、最大字符数，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `str` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 30000 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 运行日志路径。
如果“检查运行日志路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
读取运行日志路径中的文件内容，并把结果记为 待处理文本；返回待处理文本中的对应字段的当前值。
```

#### `extract_traceback`

- **源码**：`app/tools/log_tools.py:25`
- **签名**：`def extract_traceback(log_text: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前处理结果的文本，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `log_text` | `str` | 已规范化或待输出的文本；进入持久化或 Prompt 前可能需要限长和脱敏。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `rfind` 完成该函数的一项辅助处理，并把结果记为 当前候选项的索引。
如果当前候选项的索引不小于0，就返回当前处理结果的文本中的对应字段的当前值。
对当前处理结果的文本中的文本执行规范化或拆分，并把结果记为 待输出的文本行；遍历并筛选输入，将整理后的结果保存为 当前处理结果；调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `classify_error_heuristic`

- **源码**：`app/tools/log_tools.py:35`
- **签名**：`def classify_error_heuristic(traceback: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收异常堆栈文本，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `traceback` | `str` | 异常堆栈文本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
对异常堆栈文本中的文本执行规范化或拆分，并把结果记为 该调用返回的结果。
如果当前输入内容属于当前处理结果 或 当前输入内容属于当前处理结果，就返回固定值 `'dependency_missing'`。
如果当前输入内容属于当前处理结果 或 当前输入内容属于当前处理结果，就返回固定值 `'data_or_path_error'`。
如果当前输入内容属于当前处理结果，就返回固定值 `'cuda_oom'`。
如果当前输入内容属于当前处理结果 或 当前输入内容属于当前处理结果，就返回固定值 `'shape_mismatch'`。
如果当前输入内容属于当前处理结果，就返回固定值 `'permission_error'`。
返回固定值 `'unknown'`。
```

#### `extract_repo_traceback_paths`

- **源码**：`app/tools/log_tools.py:50`
- **签名**：`def extract_repo_traceback_paths(traceback: str, repo_path: str | None) -> list[str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，从 Python/pytest traceback 中提取真实存在的仓库相对路径。该函数接收异常堆栈文本、代码仓库根目录，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `traceback` | `str` | 异常堆栈文本；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `repo_path` | `str | None` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果代码仓库根目录为空或为假 或 “对异常堆栈文本中的文本执行规范化或拆分”后未得到肯定结果，就返回当前构造的顺序或去重集合。
计算组合多个值形成元组，并保存为 当前处理结果；将 候选结果集合 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为文本匹配模式，然后把新的处理结果追加或合并到候选结果集合。
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 代码仓库；将 当前处理结果 初始化为空列表，用来收集后续结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历由候选结果集合组成的集合或迭代器，每次把当前项记为原始内容的路径：
    把外部位置解析为文件系统路径对象，并把结果记为 待审核的 MCP 能力候选；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
    先尝试完成以下处理：
        将当前处理结果规范化为受控的绝对路径，并把结果记为 待定位的代码对象或业务目标。
    如果出现 `OSError`：
        跳过本轮剩余处理，直接进入下一轮。
    如果待定位的代码对象或业务目标等于代码仓库 或 代码仓库不属于当前处理结果，就跳过本轮剩余处理，直接进入下一轮。
    如果“检查待定位的代码对象或业务目标的文件系统属性”后未得到肯定结果 或 “检查待定位的代码对象或业务目标的文件系统属性”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    如果辅助操作“对文件扩展名或文本后缀中的文本执行规范化或拆分”的结果不等于'.py' 或 “检查当前处理结果的文件系统属性”后得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    把辅助操作“把待定位的代码对象或业务目标转换为稳定的仓库相对路径表示”的结果转换为稳定的仓库相对路径表示，并把结果记为 仓库相对路径。
    如果仓库相对路径属于当前处理结果，就跳过本轮剩余处理，直接进入下一轮。
    把仓库相对路径追加或合并到当前处理结果；把仓库相对路径追加或合并到当前处理结果。
返回前一步处理得到的结果。
```

### `app/tools/mapping_target_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `MappingTargetBuildResult.artifact_payload`

- **源码**：`app/tools/mapping_target_tools.py:63`
- **签名**：`def artifact_payload(self) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `policy_version`、`source_counts`、`limits`、`selected_count`、`targets`、`dropped` 字段的结构化映射。
```

#### `_clean`

- **源码**：`app/tools/mapping_target_tools.py:79`
- **签名**：`def _clean(value: Any) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_normalized`

- **源码**：`app/tools/mapping_target_tools.py:83`
- **签名**：`def _normalized(value: Any) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `normalize` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 待处理文本；调用 `sub` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_unique_text`

- **源码**：`app/tools/mapping_target_tools.py:91`
- **签名**：`def _unique_text(values: list[Any]) -> list[str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收状态字段集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `values` | `list[Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 输出结果 初始化为空列表，用来收集后续结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历由状态字段集合组成的集合或迭代器，每次把当前项记为当前字段值：
    调用 `_clean` 完成该函数的一项辅助处理，并把结果记为 清理后的文本或记录；调用 `_normalized` 完成该函数的一项辅助处理，并把结果记为 映射键或对象字段名。
    如果映射键或对象字段名为空或为假 或 映射键或对象字段名属于当前处理结果，就跳过本轮剩余处理，直接进入下一轮。
    把映射键或对象字段名追加或合并到当前处理结果；把清理后的文本或记录追加或合并到输出结果。
返回输出结果的当前值。
```

#### `_target_id`

- **源码**：`app/tools/mapping_target_tools.py:104`
- **签名**：`def _target_id(category: CodeMappingTargetCategory, canonical_key: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收评测类别、规范化键，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `category` | `CodeMappingTargetCategory` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `canonical_key` | `str` | 名为 `canonical_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回稳定业务标识符，用于后续查询、关联或幂等绑定；它不是路径或内容 Hash。

**伪代码**

```text
读取前一步操作返回对象中的对应字段，并保存为 内容摘要；返回当前计算得到的结果。
```

#### `_normalized_terms`

- **源码**：`app/tools/mapping_target_tools.py:114`
- **签名**：`def _normalized_terms(values: tuple[str, ...] | list[str]) -> list[str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收状态字段集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `values` | `tuple[str, ...] | list[str]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `_alias_rule_matches`

- **源码**：`app/tools/mapping_target_tools.py:127`
- **签名**：`def _alias_rule_matches(rule: MappingAliasRule, value: str) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前处理结果、当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `rule` | `MappingAliasRule` | 名为 `rule` 的 `MappingAliasRule` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `_normalized` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本。
如果规范化后的文本为空或为假，就返回固定值 `假`。
调用 `_normalized_terms` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果由当前处理结果组成的集合或迭代器中存在满足“检索词或规范化术语属于规范化后的文本”的项，就返回固定值 `假`。
调用 `_normalized_terms` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果由当前处理结果组成的集合或迭代器中存在满足“规范化后的文本等于检索词或规范化术语 或 检索词或规范化术语属于规范化后的文本 或 规范化后的文本属于检索词或规范化术语”的项，就返回固定值 `真`。
调用 `_normalized_terms` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真 且 “检查由当前处理结果组成的集合或迭代器中是否全部满足“检索词或规范化术语属于规范化后的文本”的项”后未得到肯定结果，就返回固定值 `假`。
调用 `_normalized_terms` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真，就检查由当前处理结果组成的集合或迭代器中是否存在满足“检索词或规范化术语属于规范化后的文本”的项，并返回处理结果。
计算数量、边界或类型判断结果，并返回处理结果。
```

#### `_alias_rule_key`

- **源码**：`app/tools/mapping_target_tools.py:167`
- **签名**：`def _alias_rule_key(values: list[Any], alias_rules: list[MappingAliasRule]) -> str | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收状态字段集合、别名解析规则，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `values` | `list[Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `alias_rules` | `list[MappingAliasRule]` | 别名解析规则；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
遍历由状态字段集合组成的集合或迭代器，每次把当前项记为当前字段值：
    调用 `_clean` 完成该函数的一项辅助处理，并把结果记为 清理后的文本或记录。
    如果清理后的文本或记录为空或为假，就跳过本轮剩余处理，直接进入下一轮。
    遍历由别名解析规则组成的集合或迭代器，每次把当前项记为当前处理结果：
        如果“调用 `_alias_rule_matches` 完成该函数的一项辅助处理”后得到肯定结果，就调用 `_normalized` 完成该函数的一项辅助处理，并返回处理结果。
返回固定值 `空值`。
```

#### `_parenthetical_acronym_key`

- **源码**：`app/tools/mapping_target_tools.py:183`
- **签名**：`def _parenthetical_acronym_key(value: str) -> str | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，通用处理 "Long Name (ABC) Block" 与 "ABC Block" 这类同义写法。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_clean` 完成该函数的一项辅助处理，并把结果记为 对象名称。
如果对象名称为空或为假，就返回固定值 `空值`。
构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假，就返回固定值 `空值`。
读取对象名称，并保存为 映射键或对象字段名。
遍历辅助操作产生的可迭代结果（调用 `reversed` 完成该函数的一项辅助处理），每次把当前项记为当前处理结果：
    调用 `group` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；读取映射键或对象字段名中的对应字段，并保存为 目录树缩进前缀；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；调用 `sub` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 该调用返回的结果。
    调用 `start` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    如果当前处理结果有值或为真 且 当前处理结果 的长度不小于当前处理结果 的长度：
        读取当前处理结果中的对应字段，并保存为 候选项集合；调用 `join` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 候选项集合。
        如果候选项集合等于当前处理结果，就调用 `start` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    计算组合或计算已有值，并保存为 映射键或对象字段名。
调用 `_normalized` 完成该函数的一项辅助处理，并把结果记为 规范化后的文本；返回组合判断结果。
```

#### `_method_key`

- **源码**：`app/tools/mapping_target_tools.py:248`
- **签名**：`def _method_key(module: dict[str, Any], alias_rules: list[MappingAliasRule]) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收Python 模块、别名解析规则，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `module` | `dict[str, Any]` | Python 模块；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `alias_rules` | `list[MappingAliasRule]` | 别名解析规则；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `_clean` 完成该函数的一项辅助处理，并把结果记为 对象名称；调用 `_alias_rule_key` 完成该函数的一项辅助处理，并把结果记为 键。
如果键有值或为真，就返回键的当前值。
调用 `_parenthetical_acronym_key` 完成该函数的一项辅助处理，并把结果记为 键。
如果键有值或为真，就返回键的当前值。
遍历辅助操作产生的可迭代结果（调用 `findall` 完成该函数的一项辅助处理），每次把当前项记为当前处理结果：
    调用 `_alias_rule_key` 完成该函数的一项辅助处理，并把结果记为 键。
    如果键有值或为真，就返回键的当前值。
返回组合判断结果。
```

#### `_string_tuple`

- **源码**：`app/tools/mapping_target_tools.py:289`
- **签名**：`def _string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收结构化请求载荷、映射键或对象字段名，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `payload` | `dict[str, Any]` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |
| `key` | `str` | 映射键或对象字段名；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[str, ...]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从结构化请求载荷读取所需的状态或领域记录，并把结果记为 当前字段值。
如果当前字段值为空，就返回当前构造的顺序或去重集合。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `TypeError`，向调用方报告输入或运行失败。
构造临时集合、映射或轻量领域对象，并返回处理结果。
```

#### `load_mapping_alias_rules`

- **源码**：`app/tools/mapping_target_tools.py:307`
- **签名**：`def load_mapping_alias_rules(path: str | Path | None) -> list[MappingAliasRule]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，从可选 JSON 文件读取论文/领域别名规则。该函数接收文件或目录路径，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `str | Path | None` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`list[MappingAliasRule]`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
如果文件或目录路径为空，就返回当前构造的顺序或去重集合。
把外部位置解析为文件系统路径对象，并把结果记为 解析后的值。
如果“检查解析后的值的文件系统属性”后未得到肯定结果，就返回当前构造的顺序或去重集合。
先尝试完成以下处理：
    将外部表示解析为结构化内容，并把结果记为 结构化请求载荷。
如果出现 `json.JSONDecodeError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `TypeError`，向调用方报告输入或运行失败。
从结构化请求载荷读取所需的状态或领域记录，并把结果记为 该调用返回的结果。
如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `TypeError`，向调用方报告输入或运行失败。
将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    如果“计算数量、边界或类型判断结果”后未得到肯定结果，就拒绝继续处理并抛出 `TypeError`，向调用方报告输入或运行失败。
    调用 `_clean` 完成该函数的一项辅助处理，并把结果记为 规范化键。
    如果规范化键为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    把新的处理结果追加或合并到当前处理结果。
返回前一步处理得到的结果。
```

#### `_evidence_key`

- **源码**：`app/tools/mapping_target_tools.py:380`
- **签名**：`def _evidence_key(evidence: Evidence) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收可追溯证据记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `evidence` | `Evidence` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
返回组合判断结果。
```

#### `_merge_evidence`

- **源码**：`app/tools/mapping_target_tools.py:393`
- **签名**：`def _merge_evidence(modules: list[dict[str, Any]]) -> list[Evidence]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收Python 模块集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `modules` | `list[dict[str, Any]]` | Python 模块集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[Evidence]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
将 输出结果 初始化为空列表，用来收集后续结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果。
遍历由Python 模块集合组成的集合或迭代器，每次把当前项记为Python 模块：
    遍历当前可迭代输入，每次把当前项记为结构化请求载荷：
        先尝试完成以下处理：
            复制、序列化或校验结构化领域对象，并把结果记为 可追溯证据记录。
        如果出现 `(TypeError, ValueError)`：
            跳过本轮剩余处理，直接进入下一轮。
        调用 `_evidence_key` 完成该函数的一项辅助处理，并把结果记为 映射键或对象字段名。
        如果映射键或对象字段名属于当前处理结果，就跳过本轮剩余处理，直接进入下一轮。
        把映射键或对象字段名追加或合并到当前处理结果；把可追溯证据记录追加或合并到输出结果。
返回输出结果的当前值。
```

#### `_source_evidence_ids`

- **源码**：`app/tools/mapping_target_tools.py:414`
- **签名**：`def _source_evidence_ids(evidence: list[Evidence]) -> list[str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收可追溯证据记录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `evidence` | `list[Evidence]` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |

**输出**

- **Python 类型**：`list[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前计算得到的结果。
```

#### `_is_ablation_text`

- **源码**：`app/tools/mapping_target_tools.py:428`
- **签名**：`def _is_ablation_text(value: Any) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `_clean` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 规范化后的文本；检查由当前处理结果组成的集合或迭代器中是否存在满足“测试或状态标记属于规范化后的文本”的项，并返回处理结果。
```

#### `_method_targets`

- **源码**：`app/tools/mapping_target_tools.py:436`
- **签名**：`def _method_targets(modules: list[dict[str, Any]], alias_rules: list[MappingAliasRule]) -> tuple[list[CodeMappingTarget], list[dict[str, Any]]]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收Python 模块集合、别名解析规则，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `modules` | `list[dict[str, Any]]` | Python 模块集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `alias_rules` | `list[MappingAliasRule]` | 别名解析规则；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[list[CodeMappingTarget], list[dict[str, Any]]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 当前处理结果 初始化为空映射，用来收集后续结果；将 当前处理结果 初始化为空列表，用来收集后续结果。
遍历由Python 模块集合组成的集合或迭代器，每次把当前项记为Python 模块：
    如果“计算数量、边界或类型判断结果”后未得到肯定结果，就跳过本轮剩余处理，直接进入下一轮。
    调用 `_clean` 完成该函数的一项辅助处理，并把结果记为 对象名称；调用 `_clean` 完成该函数的一项辅助处理，并把结果记为 对象说明。
    如果对象名称为空或为假，就跳过本轮剩余处理，直接进入下一轮。
    如果“调用 `_is_ablation_text` 校验当前输入或状态”后得到肯定结果，就把Python 模块追加或合并到当前处理结果；跳过本轮剩余处理，直接进入下一轮。
    把Python 模块追加或合并到辅助操作“把新的处理结果追加或合并到当前处理结果”的结果。
将 待定位的代码对象集合 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    调用 `_unique_text` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_unique_text` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_unique_text` 完成该函数的一项辅助处理，并把结果记为 检索关键词集合；调用 `_merge_evidence` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录。
    把新的处理结果追加或合并到待定位的代码对象集合。
返回当前构造的顺序或去重集合。
```

#### `_named_value`

- **源码**：`app/tools/mapping_target_tools.py:520`
- **签名**：`def _named_value(value: Any) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果“计算数量、边界或类型判断结果”后得到肯定结果，就调用 `_clean` 完成该函数的一项辅助处理，并返回处理结果。
调用 `_clean` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_named_targets`

- **源码**：`app/tools/mapping_target_tools.py:529`
- **签名**：`def _named_targets(values: list[Any], category: CodeMappingTargetCategory, description_prefix: str, generic_keywords: list[str], prefer_specific_names: bool) -> list[CodeMappingTarget]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收状态字段集合、评测类别、当前处理结果、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `values` | `list[Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `category` | `CodeMappingTargetCategory` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `description_prefix` | `str` | 名为 `description_prefix` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `generic_keywords` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `generic_keywords` 和调用位置确定。 |
| `prefer_specific_names` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |

**输出**

- **Python 类型**：`list[CodeMappingTarget]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 待定位的代码对象集合 初始化为空列表，用来收集后续结果；将 当前处理结果 初始化为空去重集合，用来收集后续结果；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真，就按稳定规则整理结果顺序。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为多个解包结果：
    调用 `_named_value` 完成该函数的一项辅助处理，并把结果记为 对象名称；调用 `_normalized` 完成该函数的一项辅助处理，并把结果记为 规范化键。
    如果规范化键为空或为假 或 规范化键属于当前处理结果，就跳过本轮剩余处理，直接进入下一轮。
    把规范化键追加或合并到当前处理结果；把新的处理结果追加或合并到待定位的代码对象集合。
返回待定位的代码对象集合的当前值。
```

#### `_is_generic_collection_name`

- **源码**：`app/tools/mapping_target_tools.py:578`
- **签名**：`def _is_generic_collection_name(value: str) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `_clean` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 规范化后的文本；检查规范化后的文本是否满足文本匹配条件，并返回处理结果。
```

#### `_setting_evidence`

- **源码**：`app/tools/mapping_target_tools.py:590`
- **签名**：`def _setting_evidence(settings_payload: list[dict[str, Any]]) -> list[Evidence]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `settings_payload` | `list[dict[str, Any]]` | `list[dict[str, Any]]` 元素集合；元素代表的业务对象由参数名 `settings_payload` 和调用位置确定。 |

**输出**

- **Python 类型**：`list[Evidence]`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
调用 `_merge_evidence` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_aggregate_setting_target`

- **源码**：`app/tools/mapping_target_tools.py:606`
- **签名**：`def _aggregate_setting_target(category: CodeMappingTargetCategory, name: str, settings_payload: list[dict[str, Any]], extra_descriptions: list[str], generic_keywords: list[str]) -> CodeMappingTarget | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收评测类别、对象名称、当前处理结果、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `CodeMappingTarget | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `category` | `CodeMappingTargetCategory` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `settings_payload` | `list[dict[str, Any]]` | `list[dict[str, Any]]` 元素集合；元素代表的业务对象由参数名 `settings_payload` 和调用位置确定。 |
| `extra_descriptions` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `extra_descriptions` 和调用位置确定。 |
| `generic_keywords` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `generic_keywords` 和调用位置确定。 |

**输出**

- **Python 类型**：`CodeMappingTarget | None`
- **语义**：返回 `CodeMappingTarget | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_unique_text` 完成该函数的一项辅助处理，并把结果记为 拆分后的文本或路径片段集合。
如果拆分后的文本或路径片段集合为空或为假，就返回固定值 `空值`。
调用 `_setting_evidence` 完成该函数的一项辅助处理，并把结果记为 可追溯证据记录；调用 `_unique_text` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；构造并返回 `CodeMappingTarget` 结构化领域对象。
```

#### `build_code_mapping_targets`

- **源码**：`app/tools/mapping_target_tools.py:661`
- **签名**：`def build_code_mapping_targets(paper_summary: dict[str, Any], method_modules: list[dict[str, Any]], max_targets: int, category_limits: dict[CodeMappingTargetCategory, int], alias_rules: list[MappingAliasRule] | None) -> MappingTargetBuildResult`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，构造五类映射目标，并在任何 Provider 调用前执行预算限制。该函数接收论文、当前处理结果、最大待定位的代码对象集合、当前处理结果等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `paper_summary` | `dict[str, Any]` | 名为 `paper_summary` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |
| `method_modules` | `list[dict[str, Any]]` | `list[dict[str, Any]]` 元素集合；元素代表的业务对象由参数名 `method_modules` 和调用位置确定。 |
| `max_targets` | `int` | 名为 `max_targets` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `category_limits` | `dict[CodeMappingTargetCategory, int]` | 名为 `category_limits` 的键值映射；键和值分别承载的业务字段由读取/写入分支确定。 |
| `alias_rules` | `list[MappingAliasRule] | None` | 别名解析规则；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`MappingTargetBuildResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
调用 `_method_targets` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `_named_targets` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_named_targets` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；调用 `_aggregate_setting_target` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_aggregate_setting_target` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
计算按字段初始化键值映射，并保存为 候选结果集合；将 选中的候选项、当前处理结果 初始化为空列表，用来收集后续结果。
遍历由当前处理结果组成的集合或迭代器，每次把当前项记为评测类别，然后从当前处理结果读取所需的状态或领域记录，并把结果记为 结果数量上限；读取候选结果集合中的对应字段，并保存为 后续步骤使用的结果；把当前处理结果中的对应字段追加或合并到选中的候选项；把新的处理结果追加或合并到当前处理结果。
如果选中的候选项 的长度大于最大待定位的代码对象集合，就把新的处理结果追加或合并到当前处理结果；读取选中的候选项中的对应字段，并保存为 选中的候选项。
计算按字段初始化键值映射，并保存为 当前处理结果；构造并返回 `MappingTargetBuildResult` 结构化领域对象。
```

#### `legacy_method_targets`

- **源码**：`app/tools/mapping_target_tools.py:847`
- **签名**：`def legacy_method_targets(modules: list[dict[str, Any]]) -> list[CodeMappingTarget]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，为旧测试、旧 checkpoint 和独立节点调用保留兼容入口。该函数接收Python 模块集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `modules` | `list[dict[str, Any]]` | Python 模块集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`list[CodeMappingTarget]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `_method_targets` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；返回待定位的代码对象集合的当前值。
```

#### `mapping_targets_from_state`

- **源码**：`app/tools/mapping_target_tools.py:859`
- **签名**：`def mapping_targets_from_state(state: dict[str, Any]) -> list[CodeMappingTarget]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，读取新目标；无新字段时从旧 method_modules 确定性迁移。该函数接收复现流程状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`list[CodeMappingTarget]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 待定位的代码对象集合 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为结构化请求载荷：
    先尝试完成以下处理：
        把新的处理结果追加或合并到待定位的代码对象集合。
    如果出现 `(TypeError, ValueError)`：
        跳过本轮剩余处理，直接进入下一轮。
如果待定位的代码对象集合有值或为真，就返回待定位的代码对象集合的当前值。
调用 `legacy_method_targets` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/tools/paper_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `read_pdf`

- **源码**：`app/tools/paper_tools.py:8`
- **签名**：`def read_pdf(path: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收文件或目录路径，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `str` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 论文 PDF 路径。
如果“检查论文 PDF 路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
将 检索文本块集合 初始化为空列表，用来收集后续结果。
进入上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给模块或函数文档文本”，退出时自动清理资源：
    遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
        去除辅助操作“调用 `get_text` 读取或查询当前阶段需要的数据”的结果的首尾空白，并把规范化后的文本记为 待处理文本。
        如果待处理文本有值或为真，就把新的处理结果追加或合并到检索文本块集合。
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `read_text_file`

- **源码**：`app/tools/paper_tools.py:22`
- **签名**：`def read_text_file(path: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收文件或目录路径，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `str` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 目标文件路径。
如果“检查目标文件路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `FileNotFoundError`，向调用方报告输入或运行失败。
读取目标文件路径中的文件内容，并返回处理结果。
```

#### `read_paper`

- **源码**：`app/tools/paper_tools.py:29`
- **签名**：`def read_paper(path: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收文件或目录路径，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `str` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
对前一步操作返回对象的文件扩展名或文本后缀中的文本执行规范化或拆分，并把结果记为 文件扩展名或文本后缀。
如果文件扩展名或文本后缀等于'.pdf'，就调用 `read_pdf` 读取或查询当前阶段需要的数据，并返回处理结果。
如果文件扩展名或文本后缀属于{'.md', '.txt'}，就调用 `read_text_file` 读取或查询当前阶段需要的数据，并返回处理结果。
拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `split_text`

- **源码**：`app/tools/paper_tools.py:38`
- **签名**：`def split_text(text: str, chunk_size: int = 5000, overlap: int = 500) -> list[dict]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待处理文本、文本块、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `text` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `chunk_size` | `int` | 名为 `chunk_size` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 5000 |
| `overlap` | `int` | 名为 `overlap` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 500 |

**输出**

- **Python 类型**：`list[dict]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果文本块不大于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
将 检索文本块集合 初始化为空列表，用来收集后续结果；计算使用固定配置或常量值，并保存为 读取起点；计算使用固定配置或常量值，并保存为 检索文本块的 ID。
只要读取起点小于待处理文本 的长度，就重复以下处理：
    计算数量、边界或类型判断结果，并把结果记为 读取终点；把新的处理结果追加或合并到检索文本块集合；将新的计算结果累加或合并到检索文本块的 ID；计算组合或计算已有值，并保存为 读取起点。
    计算数量、边界或类型判断结果，并把结果记为 读取起点。
    如果读取终点等于待处理文本 的长度，就立即结束当前循环。
返回检索文本块集合的当前值。
```

### `app/tools/patch_journal_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `patch_journal_path`

- **源码**：`app/tools/patch_journal_tools.py:14`
- **签名**：`def patch_journal_path(bundle: PatchBundle) -> Path`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，同一 repo + patch 在所有 run 中共享一个 journal。该函数接收代码仓库归档包，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
调用 `repository_lock_key` 完成该函数的一项辅助处理，并把结果记为 仓库键；计算组合或计算已有值，并保存为 当前处理结果的目录；创建当前处理结果的目录对应的目录；返回当前计算得到的结果。
```

#### `atomic_write_json`

- **源码**：`app/tools/patch_journal_tools.py:23`
- **签名**：`def atomic_write_json(path: Path, payload: dict[str, Any]) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，写临时文件并 fsync，再原子替换目标 JSON。该函数接收文件或目录路径、结构化请求载荷，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |
| `payload` | `dict[str, Any]` | 调用请求或结构化业务载荷；通常需要 Schema、身份 Hash 和权限校验。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
创建父级目录或父领域对象对应的目录；调用 `with_name` 完成该函数的一项辅助处理，并把结果记为 临时的路径；将结构化内容序列化或编码为可传输表示，并把结果记为 该调用返回的结果。
在上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给文件”中向终端或输出流写出当前结果/诊断信息；提交文件中已完成的数据变更；调用 `fsync` 完成该函数的一项辅助处理，退出时自动清理资源。
调用 `replace` 完成该函数的一项辅助处理；调用 `open` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
先尝试完成以下处理：
    调用 `fsync` 完成该函数的一项辅助处理。
无论成功还是失败，最后都要：
    关闭当前处理结果并释放相关资源。
```

#### `load_patch_journal`

- **源码**：`app/tools/patch_journal_tools.py:48`
- **签名**：`def load_patch_journal(bundle: PatchBundle) -> PatchApplicationJournal | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收代码仓库归档包，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `PatchApplicationJournal | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`PatchApplicationJournal | None`
- **语义**：返回从外部表示解析并校验后的领域值；格式非法时通过异常失败。

**伪代码**

```text
调用 `patch_journal_path` 完成该函数的一项辅助处理，并把结果记为 文件或目录路径。
如果“检查文件或目录路径的文件系统属性”后未得到肯定结果，就返回固定值 `空值`。
调用 `model_validate_json` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `write_patch_journal`

- **源码**：`app/tools/patch_journal_tools.py:59`
- **签名**：`def write_patch_journal(bundle: PatchBundle, owner_run_id: str, status: Literal['prepared', 'applying', 'applied', 'blocked', 'manual_intervention'], repository_state: Literal['before', 'after', 'conflict'], recovered: bool, error: str | None) -> tuple[PatchApplicationJournal, Path]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收代码仓库归档包、运行的 ID、当前状态、代码仓库状态等输入，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `owner_run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `status` | `Literal['prepared', 'applying', 'applied', 'blocked', 'manual_intervention']` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `repository_state` | `Literal['before', 'after', 'conflict']` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `recovered` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |
| `error` | `str | None` | 异常、错误记录或错误分类信息，用于失败处理和诊断。；默认 空值 |

**输出**

- **Python 类型**：`tuple[PatchApplicationJournal, Path]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
调用 `patch_journal_path` 完成该函数的一项辅助处理，并把结果记为 文件或目录路径；调用 `load_patch_journal` 读取或查询当前阶段需要的数据，并把结果记为 前一项；调用 `isoformat` 完成该函数的一项辅助处理，并把结果记为 当前时间；构造 `PatchApplicationJournal` 结构化领域对象，并把结果记为 该调用返回的结果。
调用 `atomic_write_json` 完成该函数的一项辅助处理；返回当前构造的顺序或去重集合。
```

### `app/tools/patch_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `sha256_bytes`

- **源码**：`app/tools/patch_tools.py:82`
- **签名**：`def sha256_bytes(value: bytes) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `bytes` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `sha256_text`

- **源码**：`app/tools/patch_tools.py:85`
- **签名**：`def sha256_text(value: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
调用 `sha256_bytes` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `sha256_file`

- **源码**：`app/tools/patch_tools.py:88`
- **签名**：`def sha256_file(path: Path) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收文件或目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `path` | `Path` | 待读取、写入或校验的文件系统路径；是否允许访问由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回输入内容的 SHA-256 身份摘要，用于完整性校验，不是加密后的正文。

**伪代码**

```text
计算输入内容的 SHA-256 身份摘要，并把结果记为 内容摘要。
进入上下文“调用 `open` 完成该函数的一项辅助处理，并把上下文资源交给文件”，退出时自动清理资源：
    遍历辅助操作产生的可迭代结果（调用 `iter` 完成该函数的一项辅助处理），每次把当前项记为检索文本块，然后把检索文本块追加或合并到内容摘要。
计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `_run_git`

- **源码**：`app/tools/patch_tools.py:95`
- **签名**：`def _run_git(repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，所有 Git 调用都使用 token 列表和 shell=False。该函数接收代码仓库根目录、命令行或函数位置参数集合，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终标注为 `subprocess.CompletedProcess[str]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `Path` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`subprocess.CompletedProcess[str]`
- **语义**：返回 `subprocess.CompletedProcess[str]` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `get_git_commit`

- **源码**：`app/tools/patch_tools.py:106`
- **签名**：`def get_git_commit(repo_path: Path) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收代码仓库根目录，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `Path` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `_run_git` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果当前处理结果不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
对进程标准输出中的文本执行规范化或拆分，并返回处理结果。
```

#### `ensure_clean_tracked_files`

- **源码**：`app/tools/patch_tools.py:115`
- **签名**：`def ensure_clean_tracked_files(repo_path: Path) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，第一版不在 dirty tracked tree 上生成 patch。该函数接收代码仓库根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `Path` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_run_git` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果当前处理结果不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“对进程标准输出中的文本执行规范化或拆分”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `resolve_patch_target`

- **源码**：`app/tools/patch_tools.py:135`
- **签名**：`def resolve_patch_target(repo_path: Path, relative_path: str) -> Path`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把模型路径限制在 repo_path 内的已有普通文本文件。该函数接收代码仓库根目录、仓库内相对路径，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `Path` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 待审核的 MCP 能力候选。
如果“调用 `is_absolute` 校验当前输入或状态”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前输入内容属于拆分后的文本或路径片段集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前可迭代输入中存在满足“拆分后的文本或路径片段属于路径集合”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果辅助操作“对对象名称中的文本执行规范化或拆分”的结果属于文件集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果辅助操作“对文件扩展名或文本后缀中的文本执行规范化或拆分”的结果不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
将代码仓库根目录规范化为受控的绝对路径，并把结果记为 受控扫描根目录；将当前输入内容规范化为受控的绝对路径，并把结果记为 待定位的代码对象或业务目标。
如果待定位的代码对象或业务目标不等于受控扫描根目录 且 受控扫描根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 当前处理结果。
如果“检查当前处理结果的文件系统属性”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“检查待定位的代码对象或业务目标的文件系统属性”后未得到肯定结果 或 “检查待定位的代码对象或业务目标的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果前一步操作返回对象的当前处理结果大于最大文件的字节内容，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回待定位的代码对象或业务目标的当前值。
```

#### `apply_exact_replacements`

- **源码**：`app/tools/patch_tools.py:167`
- **签名**：`def apply_exact_replacements(original_text: str, replacements: list[dict[str, str]]) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，顺序执行精确替换。该函数接收当前处理结果的文本、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `original_text` | `str` | 已规范化或待输出的文本；进入持久化或 Prompt 前可能需要限长和脱敏。 |
| `replacements` | `list[dict[str, str]]` | `list[dict[str, str]]` 元素集合；元素代表的业务对象由参数名 `replacements` 和调用位置确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
读取当前处理结果的文本，并保存为 更新后的记录。
遍历带顺序编号的输入集合，每次把当前项记为多个解包结果：
    读取当前处理结果中的对应字段，并保存为 当前处理结果的文本；读取当前处理结果中的对应字段，并保存为 当前处理结果的文本；调用 `count` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的数量。
    如果当前处理结果的数量不等于1，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    调用 `replace` 完成该函数的一项辅助处理，并把结果记为 更新后的记录。
如果更新后的记录等于当前处理结果的文本，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回更新后的记录的当前值。
```

#### `count_changed_lines`

- **源码**：`app/tools/patch_tools.py:196`
- **签名**：`def count_changed_lines(before: str, after: str) -> int`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，按 SequenceMatcher opcode 统计新增、删除或替换影响的行数。该函数接收升级前运行报告、升级后运行报告，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终数量、序号、字节数或版本等整数结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `before` | `str` | 升级前运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `after` | `str` | 分页、文本切片或事件序列位置；用于确定本次读取的起止边界。 |

**输出**

- **Python 类型**：`int`
- **语义**：返回整数计数、序号、字节数或退出码；具体含义由函数名决定。

**伪代码**

```text
对升级前运行报告中的文本执行规范化或拆分，并把结果记为 该调用返回的结果；对升级后运行报告中的文本执行规范化或拆分，并把结果记为 该调用返回的结果；构造 `SequenceMatcher` 结构化领域对象，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 发生变化的内容。
遍历辅助操作产生的可迭代结果（调用 `get_opcodes` 读取或查询当前阶段需要的数据），每次把当前项记为多个解包结果：
    如果当前处理结果等于'equal'，就跳过本轮剩余处理，直接进入下一轮。
    将新的计算结果累加或合并到发生变化的内容。
返回发生变化的内容的当前值。
```

#### `build_unified_diff`

- **源码**：`app/tools/patch_tools.py:211`
- **签名**：`def build_unified_diff(relative_path: str, before: str, after: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，统一由程序生成 diff，确保文件路径和上下文来自真实文件。该函数接收仓库内相对路径、升级前运行报告、升级后运行报告，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `relative_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `before` | `str` | 升级前运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `after` | `str` | 分页、文本切片或事件序列位置；用于确定本次读取的起止边界。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `build_patch_bundle`

- **源码**：`app/tools/patch_tools.py:223`
- **签名**：`def build_patch_bundle(repo_path: str, proposal: FileRepairProposal, bundle_root: Path) -> PatchBundle`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把 LLM proposal 编译成确定性 patch。该函数接收代码仓库根目录、修复或重跑提案、根目录，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `PatchBundle` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `str` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `proposal` | `FileRepairProposal` | 修复或重跑提案；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `bundle_root` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`PatchBundle`
- **语义**：返回 `PatchBundle` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果业务类别不等于'patch'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 代码仓库。
如果“检查代码仓库的文件系统属性”后未得到肯定结果 或 “检查代码仓库的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `ensure_clean_tracked_files` 完成该函数的一项辅助处理；调用 `get_git_commit` 读取或查询当前阶段需要的数据，并把结果记为 该调用返回的结果。
如果命令修改项集合 的长度大于最大当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `sum` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果大于最大当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历并筛选输入，将整理后的结果保存为 相对集合。
如果相对集合 的长度不等于辅助操作“构造临时集合、映射或轻量领域对象”的结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算根据字段和固定文本生成格式化文本，并保存为 代码修复补丁的 ID；计算组合或计算已有值，并保存为 代码修复补丁的目录；创建代码修复补丁的目录对应的目录；将 当前处理结果、文件集合 初始化为空列表，用来收集后续结果。
计算使用固定配置或常量值，并保存为 变化的集合。
遍历当前可迭代输入，每次把当前项记为编辑文本：
    调用 `resolve_patch_target` 解析、规范化或转换当前输入，并把结果记为 待定位的代码对象或业务目标。
    先尝试完成以下处理：
        读取待定位的代码对象或业务目标中的文件内容，并把结果记为 升级前运行报告。
    如果出现 `UnicodeDecodeError`并把异常保存为捕获的异常对象：
        拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    调用 `apply_exact_replacements` 完成该函数的一项辅助处理，并把结果记为 升级后运行报告；调用 `count_changed_lines` 完成该函数的一项辅助处理，并把结果记为 变化的行号的数量；将新的计算结果累加或合并到变化的集合；调用 `build_unified_diff` 组装当前阶段需要的领域对象，并把结果记为 当前处理结果的文本。
    如果当前处理结果的文本为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    把当前处理结果的文本追加或合并到当前处理结果；把新的处理结果追加或合并到文件集合。
如果变化的集合大于最大变化的集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算组合或计算已有值，并保存为 代码修复补丁的路径；调用 `join` 完成该函数的一项辅助处理，并把结果记为 代码修复补丁的文本；将处理结果写入代码修复补丁的路径指定的文件；调用 `sha256_file` 计算内容身份、分数或派生结果，并把结果记为 代码修复补丁的 Hash。
构造 `PatchBundle` 结构化领域对象，并把结果记为 代码仓库归档包；计算组合或计算已有值，并保存为 代码仓库归档包的路径；将处理结果写入代码仓库归档包的路径指定的文件；返回代码仓库归档包的当前值。
```

#### `validate_patch_bundle`

- **源码**：`app/tools/patch_tools.py:333`
- **签名**：`def validate_patch_bundle(bundle: PatchBundle, require_clean_repo: bool) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，在验证和推广前重复检查 patch、commit 与每个原文件哈希。该函数接收代码仓库归档包、仓库，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `require_clean_repo` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 真 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 代码仓库；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 代码修复补丁的路径。
如果“检查代码修复补丁的路径的文件系统属性”后未得到肯定结果 或 “检查代码修复补丁的路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果不等于代码修复补丁的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `get_git_commit` 读取或查询当前阶段需要的数据，并把结果记为 当前。
如果当前不等于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果仓库有值或为真，就调用 `ensure_clean_tracked_files` 完成该函数的一项辅助处理。
遍历当前可迭代输入，每次把当前项记为文件记录：
    调用 `resolve_patch_target` 解析、规范化或转换当前输入，并把结果记为 待定位的代码对象或业务目标。
    如果辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果不等于升级前运行报告的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `compute_verification_hash`

- **源码**：`app/tools/patch_tools.py:366`
- **签名**：`def compute_verification_hash(report: PatchVerificationReport) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，对验证报告做 canonical JSON 哈希，供第二次人工确认绑定。该函数接收MCP 评测或运行报告，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `PatchVerificationReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 待处理的论文或源码材料；将结构化内容序列化或编码为可传输表示，并把结果记为 结构化请求载荷；调用 `sha256_text` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `collect_source_context`

- **源码**：`app/tools/patch_tools.py:378`
- **签名**：`def collect_source_context(repo_path: str, related_files: list[str], max_files: int, max_chars_per_file: int) -> tuple[str, list[str]]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，只读取 debug_report 明确指出的已有相对路径。该函数接收代码仓库根目录、相关源码文件集合、文件数量上限、最大字符数文件，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `str` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `related_files` | `list[str]` | 相关源码文件集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `max_files` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 3 |
| `max_chars_per_file` | `int` | 名为 `max_chars_per_file` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 12000 |

**输出**

- **Python 类型**：`tuple[str, list[str]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 代码仓库；将 论文文档章节集合、当前处理结果 初始化为空列表，用来收集后续结果。
遍历当前可迭代输入，每次把当前项记为原始内容的路径：
    先尝试完成以下处理：
        调用 `resolve_patch_target` 解析、规范化或转换当前输入，并把结果记为 待定位的代码对象或业务目标。
    如果出现 `ValueError`：
        跳过本轮剩余处理，直接进入下一轮。
    读取待定位的代码对象或业务目标中的文件内容，并把结果记为 待处理文本。
    如果待处理文本 的长度大于最大字符数文件，就读取待处理文本中的对应字段，并保存为 待处理文本；计算使用固定配置或常量值，并保存为 当前处理结果；否则计算使用固定配置或常量值，并保存为 当前处理结果。
    把辅助操作“把待定位的代码对象或业务目标转换为稳定的仓库相对路径表示”的结果转换为稳定的仓库相对路径表示，并把结果记为 仓库相对路径；把仓库相对路径追加或合并到当前处理结果；把新的处理结果追加或合并到论文文档章节集合。
返回当前构造的顺序或去重集合。
```

#### `_run_command`

- **源码**：`app/tools/patch_tools.py:423`
- **签名**：`def _run_command(command: list[str], cwd: Path, timeout_seconds: int) -> PatchVerificationCheck`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，运行由程序构造的固定命令，不接受 LLM shell 字符串。该函数接收当前命令、命令执行工作目录、等待超时时间（秒），用于作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户，最终标注为 `PatchVerificationCheck` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `list[str]` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `cwd` | `Path` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |
| `timeout_seconds` | `int` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`PatchVerificationCheck`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
先尝试完成以下处理：
    调用 `run` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；计算计算当前表达式的结果，并保存为 输出结果。
    如果进程标准错误有值或为真，就将新的计算结果累加或合并到输出结果。
    构造并返回 `PatchVerificationCheck` 结构化领域对象。
如果出现 `subprocess.TimeoutExpired`并把异常保存为捕获的异常对象：
    构造并返回 `PatchVerificationCheck` 结构化领域对象。
```

#### `_build_worktree_verification_runner`

- **源码**：`app/tools/patch_tools.py:461`
- **签名**：`def _build_worktree_verification_runner(execution_profile_id: str, expected_profile_fingerprint: str, worktree_path: Path) -> tuple[ExecutionRunner, str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，复用论文执行环境，但把运行边界限制在隔离 worktree。该函数接收执行环境配置的 ID、期望配置指纹、当前处理结果的路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `execution_profile_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `expected_profile_fingerprint` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `worktree_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`tuple[ExecutionRunner, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `get_execution_profile` 读取或查询当前阶段需要的数据，并把结果记为 配置；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 当前指纹。
如果当前指纹不等于期望配置指纹，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
复制、序列化或校验结构化领域对象，并把结果记为 验证配置；返回当前构造的顺序或去重集合。
```

#### `_run_profile_command`

- **源码**：`app/tools/patch_tools.py:484`
- **签名**：`def _run_profile_command(runner: ExecutionRunner, name: str, program: str, args: list[str], cwd: Path, run_dir: str | Path, timeout_seconds: int) -> PatchVerificationCheck`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，通过临时 profile Runner 执行论文运行时检查。该函数接收运行调度器、对象名称、待启动实验程序、命令行或函数位置参数集合等输入，用于作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户，最终标注为 `PatchVerificationCheck` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `runner` | `ExecutionRunner` | 运行调度器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `program` | `str` | 待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `cwd` | `Path` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `timeout_seconds` | `int` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`PatchVerificationCheck`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
计算初始化顺序集合，并保存为 当前命令；调用 `probe` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；调用 `str` 完成该函数的一项辅助处理，并把结果记为 输出结果；构造并返回 `PatchVerificationCheck` 结构化领域对象。
```

#### `create_patch_worktree`

- **源码**：`app/tools/patch_tools.py:514`
- **签名**：`def create_patch_worktree(bundle: PatchBundle, worktree_path: Path) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，从 bundle 绑定的 commit 创建独立 detached worktree。该函数接收代码仓库归档包、当前处理结果的路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `worktree_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果“检查当前处理结果的路径的文件系统属性”后得到肯定结果：
    如果“检查当前输入内容的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    调用 `_run_git` 完成该函数的一项辅助处理，并把结果记为 当前。
    如果当前处理结果不等于0 或 辅助操作“对进程标准输出中的文本执行规范化或拆分”的结果不等于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    结束当前函数，不返回业务值。
创建父级目录或父领域对象对应的目录；调用 `_run_git` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果当前处理结果不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `summarize_patch_verification`

- **源码**：`app/tools/patch_tools.py:556`
- **签名**：`def summarize_patch_verification(checks: list[PatchVerificationCheck]) -> tuple[str, bool, bool, int, int]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，返回 status、promotion_allowed、structural_passed、 behavioral_run、behavioral_passed。该函数接收校验项集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `checks` | `list[PatchVerificationCheck]` | 校验项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[str, bool, bool, int, int]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果校验项集合为空或为假，就返回当前构造的顺序或去重集合。
计算初始化去重集合，并保存为 当前处理结果；遍历并筛选输入，将整理后的结果保存为 当前处理结果；调用 `issubset` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；检查由校验项集合组成的集合或迭代器中是否存在满足“对象名称属于校验集合 且 当前状态等于'failed'”的项，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真，就返回当前构造的顺序或去重集合。
如果当前处理结果为空或为假，就返回当前构造的顺序或去重集合。
遍历并筛选输入，将整理后的结果保存为 校验项集合集合；计算数量、边界或类型判断结果，并把结果记为 运行的数量；调用 `sum` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的数量。
如果运行的数量等于0，就返回当前构造的顺序或去重集合。
如果当前处理结果的数量等于运行的数量，就返回当前构造的顺序或去重集合。
返回当前构造的顺序或去重集合。
```

#### `verify_patch_in_worktree`

- **源码**：`app/tools/patch_tools.py:604`
- **签名**：`def verify_patch_in_worktree(bundle: PatchBundle, worktree_path: Path, verification_targets: list[str], execution_profile_id: str, execution_profile_fingerprint: str, run_dir: str | Path) -> PatchVerificationReport`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，在隔离 worktree 中执行四层检查： 1. git apply --check 2. git apply 3. after SHA-256 4. Python 语法与受限测试目标。该函数接收代码仓库归档包、当前处理结果的路径、验证集合、执行环境配置的 ID等输入，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `PatchVerificationReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `worktree_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `verification_targets` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `verification_targets` 和调用位置确定。 |
| `execution_profile_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `execution_profile_fingerprint` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `run_dir` | `str | Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`PatchVerificationReport`
- **语义**：返回 `PatchVerificationReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `validate_patch_bundle` 校验当前输入或状态；将 校验项集合 初始化为空列表，用来收集后续结果；调用 `_build_worktree_verification_runner` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
先尝试完成以下处理：
    调用 `create_patch_worktree` 组装当前阶段需要的领域对象。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    构造并返回 `PatchVerificationReport` 结构化领域对象。
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 代码修复补丁的路径。
定义内部辅助函数 `_all_file_hashes_match`，供当前函数在后续步骤中调用。
调用 `_all_file_hashes_match` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_all_file_hashes_match` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真：
    构造 `PatchVerificationCheck` 结构化领域对象，并把结果记为 校验；构造 `PatchVerificationCheck` 结构化领域对象，并把结果记为 结果；把新的处理结果追加或合并到校验项集合。
否则：
    如果当前处理结果有值或为真：
        调用 `_run_command` 完成该函数的一项辅助处理，并把结果记为 校验；计算使用固定配置或常量值，并保存为 对象名称；把校验追加或合并到校验项集合。
        如果当前状态等于'passed'，就调用 `_run_command` 完成该函数的一项辅助处理，并把结果记为 结果；计算使用固定配置或常量值，并保存为 对象名称；把结果追加或合并到校验项集合；否则构造 `PatchVerificationCheck` 结构化领域对象，并把结果记为 结果；把结果追加或合并到校验项集合。
    否则：
        构造 `PatchVerificationCheck` 结构化领域对象，并把结果记为 校验；构造 `PatchVerificationCheck` 结构化领域对象，并把结果记为 结果；把新的处理结果追加或合并到校验项集合。
如果当前状态等于'passed'：
    将 Hash集合 初始化为空列表，用来收集后续结果。
    遍历当前可迭代输入，每次把当前项记为文件记录：
        计算组合或计算已有值，并保存为 待定位的代码对象或业务目标。
        如果“检查待定位的代码对象或业务目标的文件系统属性”后未得到肯定结果，就把新的处理结果追加或合并到Hash集合；跳过本轮剩余处理，直接进入下一轮。
        调用 `sha256_file` 计算内容身份、分数或派生结果，并把结果记为 实际值的 Hash。
        如果实际值的 Hash不等于升级后运行报告的 SHA-256，就把新的处理结果追加或合并到Hash集合。
    把新的处理结果追加或合并到校验项集合。
    先尝试完成以下处理：
        调用 `validate_worktree_matches_patch` 校验当前输入或状态，并把结果记为 当前处理结果的 SHA-256；把新的处理结果追加或合并到校验项集合。
    如果出现 `ValueError`并把异常保存为捕获的异常对象：
        计算使用固定配置或常量值，并保存为 当前处理结果的 SHA-256；把新的处理结果追加或合并到校验项集合。
    遍历并筛选输入，将整理后的结果保存为 当前处理结果。
    如果当前处理结果有值或为真，就调用 `_run_profile_command` 完成该函数的一项辅助处理，并把结果记为 校验；把校验追加或合并到校验项集合；否则把新的处理结果追加或合并到校验项集合。
    将 测试集合 初始化为空列表，用来收集后续结果。
    遍历由验证集合组成的集合或迭代器，每次把当前项记为当前处理结果：
        把外部位置解析为文件系统路径对象，并把结果记为 待审核的 MCP 能力候选。
        如果“调用 `is_absolute` 校验当前输入或状态”后得到肯定结果 或 当前输入内容属于拆分后的文本或路径片段集合，就跳过本轮剩余处理，直接进入下一轮。
        如果“拆分后的文本或路径片段集合有值或为真”不成立 或 拆分后的文本或路径片段集合中的对应字段不等于'tests'，就跳过本轮剩余处理，直接进入下一轮。
        如果“检查当前输入内容的文件系统属性”后得到肯定结果，就把新的处理结果追加或合并到测试集合。
    如果测试集合有值或为真，就调用 `_run_profile_command` 完成该函数的一项辅助处理，并把结果记为 测试校验；把测试校验追加或合并到校验项集合；否则把新的处理结果追加或合并到校验项集合。
调用 `summarize_patch_verification` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；构造 `PatchVerificationReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告；调用 `compute_verification_hash` 计算内容身份、分数或派生结果，并把结果记为 验证结果的 Hash；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `verify_patch_in_worktree._all_file_hashes_match`

- **源码**：`app/tools/patch_tools.py:652`
- **签名**：`def _all_file_hashes_match(field_name: str) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收结构化对象字段的名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `field_name` | `str` | 名为 `field_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
遍历当前可迭代输入，每次把当前项记为文件记录：
    计算组合或计算已有值，并保存为 待定位的代码对象或业务目标。
    如果“检查待定位的代码对象或业务目标的文件系统属性”后未得到肯定结果，就返回固定值 `假`。
    如果辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果不等于辅助操作“调用 `getattr` 完成该函数的一项辅助处理”的结果，就返回固定值 `假`。
返回固定值 `真`。
```

#### `_git_output`

- **源码**：`app/tools/patch_tools.py:855`
- **签名**：`def _git_output(repo_path: Path, args: list[str]) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收代码仓库根目录、命令行或函数位置参数集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `Path` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `_run_git` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果当前处理结果不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回进程标准输出的当前值。
```

#### `get_changed_tracked_paths`

- **源码**：`app/tools/patch_tools.py:861`
- **签名**：`def get_changed_tracked_paths(worktree_path: Path) -> set[str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前处理结果的路径，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `worktree_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`set[str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
调用 `_git_output` 完成该函数的一项辅助处理，并把结果记为 输出结果；返回当前计算得到的结果。
```

#### `ensure_no_staged_changes`

- **源码**：`app/tools/patch_tools.py:868`
- **签名**：`def ensure_no_staged_changes(worktree_path: Path) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前处理结果的路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `worktree_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_git_output` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果“对当前处理结果中的文本执行规范化或拆分”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

#### `compute_worktree_diff_hash`

- **源码**：`app/tools/patch_tools.py:876`
- **签名**：`def compute_worktree_diff_hash(worktree_path: Path) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，对完整 tracked binary diff 做哈希。该函数接收当前处理结果的路径，用于计算输入、命令、运行配置或证据的稳定派生值，保证复现链路中的身份校验和 stale 检测，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `worktree_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
调用 `_git_output` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的文本；调用 `sha256_text` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `validate_worktree_matches_patch`

- **源码**：`app/tools/patch_tools.py:885`
- **签名**：`def validate_worktree_matches_patch(bundle: PatchBundle, worktree_path: Path) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，目标文件必须全部为 after hash，且 tracked diff 只能包含 bundle 文件。该函数接收代码仓库归档包、当前处理结果的路径，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `worktree_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果辅助操作“调用 `get_git_commit` 读取或查询当前阶段需要的数据”的结果不等于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `ensure_no_staged_changes` 完成该函数的一项辅助处理；遍历并筛选输入，将整理后的结果保存为 期望集合；调用 `get_changed_tracked_paths` 读取或查询当前阶段需要的数据，并把结果记为 变化的集合。
如果变化的集合不等于期望集合，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
遍历当前可迭代输入，每次把当前项记为文件记录：
    计算组合或计算已有值，并保存为 待定位的代码对象或业务目标。
    如果“检查待定位的代码对象或业务目标的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果不等于升级后运行报告的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `_run_git` 完成该函数的一项辅助处理，并把结果记为 校验。
如果当前处理结果不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `compute_worktree_diff_hash` 计算内容身份、分数或派生结果，并返回处理结果。
```

#### `validate_verification_hash`

- **源码**：`app/tools/patch_tools.py:928`
- **签名**：`def validate_verification_hash(report: PatchVerificationReport) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，重新序列化完整报告并校验 embedded hash。该函数接收MCP 评测或运行报告，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `PatchVerificationReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回内容身份摘要，通常为 SHA-256 十六进制字符串。

**伪代码**

```text
读取验证结果的 SHA-256，并保存为 当前处理结果的 Hash。
如果当前处理结果的 Hash为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `compute_verification_hash` 计算内容身份、分数或派生结果，并把结果记为 当前处理结果的 Hash。
如果“调用 `compare_digest` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前处理结果的 Hash的当前值。
```

#### `validate_patch_promotion_authorization`

- **源码**：`app/tools/patch_tools.py:944`
- **签名**：`def validate_patch_promotion_authorization(bundle: PatchBundle, report: PatchVerificationReport, promotion: PatchPromotionRecord | None, state: dict[str, Any], require_promotion: bool) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，在 promotion review 和 apply 边界复用同一套确定性校验。该函数接收代码仓库归档包、MCP 评测或运行报告、当前处理结果、复现流程状态等输入，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `report` | `PatchVerificationReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `promotion` | `PatchPromotionRecord | None` | 名为 `promotion` 的 `PatchPromotionRecord | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `require_promotion` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 代码修复补丁的路径。
如果“检查代码修复补丁的路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果不等于代码修复补丁的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `validate_verification_hash` 校验当前输入或状态，并把结果记为 当前处理结果的 Hash。
如果当前状态不等于'behaviorally_verified'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果不是真，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果代码修复补丁的 ID不等于代码修复补丁的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果代码修复补丁的 SHA-256不等于代码修复补丁的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
从复现流程状态读取所需的状态或领域记录，并把结果记为 状态配置的 ID；从复现流程状态读取所需的状态或领域记录，并把结果记为 状态指纹；计算计算当前表达式的结果，并保存为 待审批复现动作。
如果执行环境配置的 ID不等于状态配置的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果执行配置指纹不等于状态指纹，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果辅助操作“从待审批复现动作读取所需的状态或领域记录”的结果不等于状态配置的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果辅助操作“从待审批复现动作读取所需的状态或领域记录”的结果不等于状态指纹，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `get_execution_profile` 读取或查询当前阶段需要的数据，并把结果记为 当前配置；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 当前指纹。
如果当前指纹不等于状态指纹，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果当前处理结果有值或为真：
    如果当前处理结果为空 或 人工决策结果不等于'approved'，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果代码修复补丁的 ID不等于代码修复补丁的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果代码修复补丁的 SHA-256不等于代码修复补丁的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
    如果“调用 `compare_digest` 完成该函数的一项辅助处理”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前处理结果的 Hash的当前值。
```

#### `inspect_source_patch_state`

- **源码**：`app/tools/patch_tools.py:1023`
- **签名**：`def inspect_source_patch_state(bundle: PatchBundle) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，返回 before、after 或 conflict。该函数接收代码仓库归档包，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 代码仓库。
如果辅助操作“调用 `get_git_commit` 读取或查询当前阶段需要的数据”的结果不等于当前处理结果，就返回固定值 `'conflict'`。
调用 `_git_output` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果“对当前处理结果中的文本执行规范化或拆分”后得到肯定结果，就返回固定值 `'conflict'`。
调用 `get_changed_tracked_paths` 读取或查询当前阶段需要的数据，并把结果记为 变化的集合；遍历并筛选输入，将整理后的结果保存为 期望集合；检查当前可迭代输入中是否全部满足““检查当前输入内容的文件系统属性”后得到肯定结果”的项，并把结果记为 该调用返回的结果。
如果当前处理结果为空或为假，就返回固定值 `'conflict'`。
检查当前可迭代输入中是否全部满足“辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果等于升级前运行报告的 SHA-256”的项，并把结果记为 该调用返回的结果；检查当前可迭代输入中是否全部满足“辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果等于升级后运行报告的 SHA-256”的项，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真 且 变化的集合为空或为假，就返回固定值 `'before'`。
如果当前处理结果有值或为真 且 变化的集合等于期望集合，就返回固定值 `'after'`。
返回固定值 `'conflict'`。
```

#### `_application_record`

- **源码**：`app/tools/patch_tools.py:1064`
- **签名**：`def _application_record(bundle: PatchBundle, status: str, applied_at: str, recovered: bool, error: str | None, journal_path: Path | None, lock_key: str | None) -> PatchApplicationRecord`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收代码仓库归档包、当前状态、当前处理结果、当前处理结果等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `status` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `applied_at` | `str` | 名为 `applied_at` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `recovered` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |
| `error` | `str | None` | 异常、错误记录或错误分类信息，用于失败处理和诊断。；默认 空值 |
| `journal_path` | `Path | None` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。；默认 空值 |
| `lock_key` | `str | None` | 名为 `lock_key` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`PatchApplicationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
构造并返回 `PatchApplicationRecord` 结构化领域对象。
```

#### `apply_verified_patch_to_source`

- **源码**：`app/tools/patch_tools.py:1087`
- **签名**：`def apply_verified_patch_to_source(bundle: PatchBundle, owner_run_id: str, fault_hook: FaultHook | None) -> PatchApplicationRecord`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，在仓库锁内通过 write-ahead journal 幂等应用 patch。该函数接收代码仓库归档包、运行的 ID、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `bundle` | `PatchBundle` | 代码仓库归档包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `owner_run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `fault_hook` | `FaultHook | None` | 名为 `fault_hook` 的 `FaultHook | None` 领域输入；用于当前函数的业务处理，具体约束见校验分支。；默认 空值 |

**输出**

- **Python 类型**：`PatchApplicationRecord`
- **语义**：返回经过 Schema 校验的领域记录、Manifest 或证据对象。

**伪代码**

```text
将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 代码仓库。
定义内部辅助函数 `inject`，供当前函数在后续步骤中调用。
先尝试完成以下处理：
    进入上下文“调用 `acquire_repository_lock` 完成该函数的一项辅助处理，并把上下文资源交给键”，退出时自动清理资源：
        把外部位置解析为文件系统路径对象，并把结果记为 代码修复补丁的路径。
        如果“检查代码修复补丁的路径的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        如果辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果不等于代码修复补丁的 SHA-256，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        调用 `inspect_source_patch_state` 完成该函数的一项辅助处理，并把结果记为 代码仓库状态。
        如果代码仓库状态等于'after'，就调用 `write_patch_journal` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `_application_record` 完成该函数的一项辅助处理，并返回处理结果。
        如果代码仓库状态等于'conflict'，就计算使用固定配置或常量值，并保存为 面向用户或日志的提示信息；调用 `write_patch_journal` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `_application_record` 完成该函数的一项辅助处理，并返回处理结果。
        调用 `write_patch_journal` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `inject` 完成该函数的一项辅助处理；调用 `_run_git` 完成该函数的一项辅助处理，并把结果记为 校验。
        如果当前处理结果不等于0，就调用 `write_patch_journal` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `_application_record` 完成该函数的一项辅助处理，并返回处理结果。
        调用 `write_patch_journal` 持久化或更新当前领域数据；调用 `inject` 完成该函数的一项辅助处理；调用 `_run_git` 完成该函数的一项辅助处理，并把结果记为 结果。
        如果当前处理结果不等于0，就调用 `inspect_source_patch_state` 完成该函数的一项辅助处理，并把结果记为 当前状态；计算根据条件从两个候选结果中选择一个，并保存为 状态；调用 `write_patch_journal` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `_application_record` 完成该函数的一项辅助处理，并返回处理结果。
        调用 `inject` 完成该函数的一项辅助处理。
        如果辅助操作“调用 `inspect_source_patch_state` 完成该函数的一项辅助处理”的结果不等于'after'，就计算使用固定配置或常量值，并保存为 面向用户或日志的提示信息；调用 `write_patch_journal` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `_application_record` 完成该函数的一项辅助处理，并返回处理结果。
        调用 `write_patch_journal` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `inject` 完成该函数的一项辅助处理；调用 `_application_record` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `RepositoryLockBusyError`并把异常保存为捕获的异常对象：
    调用 `_application_record` 完成该函数的一项辅助处理，并返回处理结果。
如果出现 `(OSError, ValueError)`并把异常保存为捕获的异常对象：
    调用 `_application_record` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `apply_verified_patch_to_source.inject`

- **源码**：`app/tools/patch_tools.py:1101`
- **签名**：`def inject(point: str) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `point` | `str` | 名为 `point` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前处理结果不为空，就调用 `fault_hook` 完成该函数的一项辅助处理。
```

#### `validate_patch_worktree_path`

- **源码**：`app/tools/patch_tools.py:1277`
- **签名**：`def validate_patch_worktree_path(worktree_path: Path, run_dir: Path) -> Path`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，只允许当前 run/execution/patch_worktrees 下的精确路径。该函数接收当前处理结果的路径、本次复现运行目录，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `worktree_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_dir` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
将当前处理结果的路径规范化为受控的绝对路径，并把结果记为 解析后的；计算组合或计算已有值，并保存为 根目录。
如果解析后的不等于根目录 且 根目录不属于当前处理结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果“检查当前输入内容的文件系统属性”后未得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回解析后的的当前值。
```

#### `remove_patch_worktree`

- **源码**：`app/tools/patch_tools.py:1296`
- **签名**：`def remove_patch_worktree(repo_path: str, worktree_path: str, run_dir: str) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收代码仓库根目录、当前处理结果的路径、本次复现运行目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `str` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `worktree_path` | `str` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `validate_patch_worktree_path` 校验当前输入或状态，并把结果记为 待定位的代码对象或业务目标；调用 `_run_git` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
如果当前处理结果不等于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
```

### `app/tools/preflight_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_resolve_action_runner`

- **源码**：`app/tools/preflight_tools.py:46`
- **签名**：`def _resolve_action_runner(action: dict) -> tuple[ExecutionRunner, str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待执行复现动作，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |

**输出**

- **Python 类型**：`tuple[ExecutionRunner, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从待执行复现动作读取所需的状态或领域记录，并把结果记为 MCP Client 配置档案 ID。
如果MCP Client 配置档案 ID为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `get_execution_profile` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 当前指纹；从待执行复现动作读取所需的状态或领域记录，并把结果记为 期望指纹。
如果期望指纹不等于当前指纹，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
返回当前构造的顺序或去重集合。
```

#### `_contains_bracket_placeholder`

- **源码**：`app/tools/preflight_tools.py:59`
- **签名**：`def _contains_bracket_placeholder(value: str) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
先尝试完成以下处理：
    对当前处理结果中的文本执行规范化或拆分，并把结果记为 模型 token 用量。
如果出现 `ValueError`：
    对当前字段值中的文本执行规范化或拆分，并把结果记为 模型 token 用量。
检查由模型 token 用量组成的集合或迭代器中是否存在满足““检查模型或命令 token是否满足文本匹配条件”后得到肯定结果 且 “检查模型或命令 token是否满足文本匹配条件”后得到肯定结果 且 模型或命令 token 的长度大于2”的项，并返回处理结果。
```

#### `_contains_placeholder`

- **源码**：`app/tools/preflight_tools.py:70`
- **签名**：`def _contains_placeholder(value: str) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `str` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
对当前字段值中的文本执行规范化或拆分，并把结果记为 转为小写的比较文本；返回组合判断结果。
```

#### `_strip_leading_cd_for_preflight`

- **源码**：`app/tools/preflight_tools.py:77`
- **签名**：`def _strip_leading_cd_for_preflight(command: str, cwd: str) -> tuple[str, str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前命令、命令执行工作目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `cwd` | `str` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |

**输出**

- **Python 类型**：`tuple[str, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
去除当前命令的首尾空白，并把规范化后的文本记为 当前处理结果。
如果“检查当前处理结果是否满足文本匹配条件”后未得到肯定结果，就返回当前构造的顺序或去重集合。
如果当前输入内容不属于当前处理结果，就返回当前构造的顺序或去重集合。
对当前处理结果中的文本执行规范化或拆分，并把结果记为 多个解包结果；去除关系左侧实体或比较左值的首尾空白，并把规范化后的文本记为 关系左侧实体或比较左值；去除关系右侧实体或比较右值的首尾空白，并把规范化后的文本记为 关系右侧实体或比较右值。
先尝试完成以下处理：
    对当前处理结果中的文本执行规范化或拆分，并把结果记为 模型 token 用量。
如果出现 `ValueError`：
    返回当前构造的顺序或去重集合。
如果模型 token 用量 的长度等于2 且 模型 token 用量中的对应字段等于'cd'，就返回当前构造的顺序或去重集合。
返回当前构造的顺序或去重集合。
```

#### `_contains_unsupported_preflight_shell_syntax`

- **源码**：`app/tools/preflight_tools.py:99`
- **签名**：`def _contains_unsupported_preflight_shell_syntax(command: str) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前命令，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
检查由文本集合组成的集合或迭代器中是否存在满足“测试或状态标记属于当前命令”的项，并返回处理结果。
```

#### `_resolve_path`

- **源码**：`app/tools/preflight_tools.py:102`
- **签名**：`def _resolve_path(candidate: str, cwd: Path) -> Path`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待审核的 MCP 能力候选、命令执行工作目录，用于把论文中的方法、模块或实验意图与仓库中的可验证对象建立稳定关联，并保留匹配依据，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `candidate` | `str` | 待审核的 MCP 能力候选；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `cwd` | `Path` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 文件或目录路径。
如果“调用 `is_absolute` 校验当前输入或状态”后得到肯定结果，就返回文件或目录路径的当前值。
将当前输入内容规范化为受控的绝对路径，并返回处理结果。
```

#### `_add_item`

- **源码**：`app/tools/preflight_tools.py:108`
- **签名**：`def _add_item(items: list[PreflightItem], name: str, category: str, status: str, evidence: str, recommendation: str | None) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待处理项集合、对象名称、评测类别、当前状态等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `items` | `list[PreflightItem]` | 待处理项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `category` | `str` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `status` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `evidence` | `str` | 持久化领域记录、Manifest 或证据对象，通常携带版本、关联 ID 和内容身份。 |
| `recommendation` | `str | None` | 名为 `recommendation` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把新的处理结果追加或合并到待处理项集合。
```

#### `_extract_flag_values`

- **源码**：`app/tools/preflight_tools.py:127`
- **签名**：`def _extract_flag_values(args: list[str]) -> dict[str, str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收命令行或函数位置参数集合，用于读取并整理论文、源码或运行产物，把原始输入转换成带位置和身份信息的结构化证据，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict[str, str]`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
将 状态字段集合 初始化为空映射，用来收集后续结果；计算使用固定配置或常量值，并保存为 当前候选项的索引。
只要当前候选项的索引小于命令行或函数位置参数集合 的长度，就重复以下处理：
    读取命令行或函数位置参数集合中的对应字段，并保存为 模型或命令 token。
    如果模型或命令 token属于路径集合 且 当前输入内容小于命令行或函数位置参数集合 的长度，就读取命令行或函数位置参数集合中的对应字段，并保存为 状态字段集合中的对应字段；将新的计算结果累加或合并到当前候选项的索引；跳过本轮剩余处理，直接进入下一轮。
    如果“检查模型或命令 token是否满足文本匹配条件”后得到肯定结果 且 当前输入内容属于模型或命令 token：
        对模型或命令 token中的文本执行规范化或拆分，并把结果记为 多个解包结果。
        如果映射键或对象字段名属于路径集合，就读取当前字段值，并保存为 状态字段集合中的对应字段。
    将新的计算结果累加或合并到当前候选项的索引。
返回状态字段集合的当前值。
```

#### `_detect_entry_script`

- **源码**：`app/tools/preflight_tools.py:148`
- **签名**：`def _detect_entry_script(program: str, args: list[str], cwd: Path) -> Path | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待启动实验程序、命令行或函数位置参数集合、命令执行工作目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `program` | `str` | 待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `cwd` | `Path` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |

**输出**

- **Python 类型**：`Path | None`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果命令行或函数位置参数集合为空或为假，就返回固定值 `空值`。
如果待启动实验程序等于'python'：
    读取命令行或函数位置参数集合中的对应字段，并保存为 第一项。
    如果第一项等于'-m'，就返回固定值 `空值`。
    如果“检查第一项是否满足文本匹配条件”后得到肯定结果，就返回固定值 `空值`。
    调用 `_resolve_path` 解析、规范化或转换当前输入，并返回处理结果。
如果待启动实验程序等于'bash'：
    读取命令行或函数位置参数集合中的对应字段，并保存为 第一项。
    如果“检查第一项是否满足文本匹配条件”后得到肯定结果，就返回固定值 `空值`。
    调用 `_resolve_path` 解析、规范化或转换当前输入，并返回处理结果。
返回固定值 `空值`。
```

#### `_detect_dependency_files`

- **源码**：`app/tools/preflight_tools.py:168`
- **签名**：`def _detect_dependency_files(repo_path: str | None) -> list[Path]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收代码仓库根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `str | None` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`list[Path]`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
如果代码仓库根目录为空或为假，就返回当前构造的顺序或去重集合。
把外部位置解析为文件系统路径对象，并把结果记为 代码仓库的目录；计算初始化顺序集合，并保存为 候选结果集合；返回当前计算得到的结果。
```

#### `_run_probe`

- **源码**：`app/tools/preflight_tools.py:181`
- **签名**：`def _run_probe(runner: ExecutionRunner, command: list[str], cwd: Path, run_dir: str, stage: str, timeout_seconds: int) -> tuple[bool, str, dict]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收运行调度器、当前命令、命令执行工作目录、本次复现运行目录等输入，用于驱动或监督一次论文复现运行，记录命令、工作目录、资源使用、状态迁移和失败原因，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `runner` | `ExecutionRunner` | 运行调度器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `command` | `list[str]` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `cwd` | `Path` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `stage` | `str` | 流水线阶段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `timeout_seconds` | `int` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。；默认 8 |

**输出**

- **Python 类型**：`tuple[bool, str, dict]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
如果当前命令为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
调用 `probe` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；返回当前构造的顺序或去重集合。
```

#### `build_preflight_action_from_command`

- **源码**：`app/tools/preflight_tools.py:204`
- **签名**：`def build_preflight_action_from_command(command: str, cwd: str, source: str, reason: str, timeout_seconds: int, execution_profile_id: str, execution_profile_fingerprint: str) -> dict`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前命令、命令执行工作目录、数据来源标记、基线接受或运行操作原因等输入，用于作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `cwd` | `str` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |
| `source` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `reason` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `timeout_seconds` | `int` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。；默认 300 |
| `execution_profile_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `execution_profile_fingerprint` | `str` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
调用 `_strip_leading_cd_for_preflight` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
如果“调用 `_contains_unsupported_preflight_shell_syntax` 完成该函数的一项辅助处理”后得到肯定结果，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    对当前处理结果中的文本执行规范化或拆分，并把结果记为 模型 token 用量。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果模型 token 用量为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果由模型 token 用量组成的集合或迭代器中存在满足“模型或命令 token属于文本集合”的项，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
构造 `ExecutableAction` 结构化领域对象，并把结果记为 待执行复现动作；复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `collect_static_preflight_items`

- **源码**：`app/tools/preflight_tools.py:250`
- **签名**：`def collect_static_preflight_items(runner: ExecutionRunner, action: dict, repo_path: str | None, run_dir: str, probe_results: list[dict]) -> list[PreflightItem]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收运行调度器、待执行复现动作、代码仓库根目录、本次复现运行目录等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `runner` | `ExecutionRunner` | 运行调度器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `repo_path` | `str | None` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `probe_results` | `list[dict]` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |

**输出**

- **Python 类型**：`list[PreflightItem]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 待处理项集合 初始化为空列表，用来收集后续结果；从待执行复现动作读取所需的状态或领域记录，并把结果记为 待启动实验程序；从待执行复现动作读取所需的状态或领域记录，并把结果记为 命令行或函数位置参数集合；把外部位置解析为文件系统路径对象，并把结果记为 命令执行工作目录。
如果“检查命令执行工作目录的文件系统属性”后得到肯定结果 且 “检查命令执行工作目录的文件系统属性”后得到肯定结果，就调用 `_add_item` 完成该函数的一项辅助处理；否则调用 `_add_item` 完成该函数的一项辅助处理。
如果“检查命令执行工作目录的文件系统属性”后得到肯定结果：
    如果“调用 `access` 完成该函数的一项辅助处理”后得到肯定结果，就调用 `_add_item` 完成该函数的一项辅助处理；否则调用 `_add_item` 完成该函数的一项辅助处理。
调用 `which` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；把结果追加或合并到结果集合集合。
如果解析后的有值或为真，就调用 `_add_item` 完成该函数的一项辅助处理；否则调用 `_add_item` 完成该函数的一项辅助处理。
去除辅助操作“调用 `join` 完成该函数的一项辅助处理”的结果的首尾空白，并把规范化后的文本记为 当前处理结果。
如果“调用 `_contains_placeholder` 完成该函数的一项辅助处理”后得到肯定结果，就调用 `_add_item` 完成该函数的一项辅助处理；否则调用 `_add_item` 完成该函数的一项辅助处理。
调用 `_detect_entry_script` 完成该函数的一项辅助处理，并把结果记为 条目。
如果条目不为空：
    如果“检查条目的文件系统属性”后得到肯定结果，就调用 `_add_item` 完成该函数的一项辅助处理；否则调用 `_add_item` 完成该函数的一项辅助处理。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    读取路径集合中的对应字段，并保存为 后续步骤使用的结果。
    如果“调用 `_contains_placeholder` 完成该函数的一项辅助处理”后得到肯定结果，就调用 `_add_item` 完成该函数的一项辅助处理；跳过本轮剩余处理，直接进入下一轮。
    调用 `_resolve_path` 解析、规范化或转换当前输入，并把结果记为 待定位的代码对象或业务目标的路径。
    如果“检查待定位的代码对象或业务目标的路径的文件系统属性”后得到肯定结果，就调用 `_add_item` 完成该函数的一项辅助处理；否则调用 `_add_item` 完成该函数的一项辅助处理。
调用 `_detect_dependency_files` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
如果当前处理结果有值或为真，就调用 `_add_item` 完成该函数的一项辅助处理；否则调用 `_add_item` 完成该函数的一项辅助处理。
返回待处理项集合的当前值。
```

#### `collect_runtime_preflight_items`

- **源码**：`app/tools/preflight_tools.py:419`
- **签名**：`def collect_runtime_preflight_items(action: dict, runner: ExecutionRunner, run_dir: str, probe_results: list[dict]) -> list[PreflightItem]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待执行复现动作、运行调度器、本次复现运行目录、结果集合集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `runner` | `ExecutionRunner` | 运行调度器；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `probe_results` | `list[dict]` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |

**输出**

- **Python 类型**：`list[PreflightItem]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 待处理项集合 初始化为空列表，用来收集后续结果；调用 `str` 完成该函数的一项辅助处理，并把结果记为 待启动实验程序；把外部位置解析为文件系统路径对象，并把结果记为 命令执行工作目录；调用 `which` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
把结果追加或合并到结果集合集合。
如果解析后的值为空或为假，就返回待处理项集合的当前值。
如果待启动实验程序属于{'python', 'python3'}：
    调用 `_run_probe` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；把阶段处理结果追加或合并到结果集合集合；调用 `_add_item` 完成该函数的一项辅助处理；调用 `_run_probe` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
    把阶段处理结果追加或合并到结果集合集合；调用 `_add_item` 完成该函数的一项辅助处理；调用 `_run_probe` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；把阶段处理结果追加或合并到结果集合集合。
    调用 `_add_item` 完成该函数的一项辅助处理。
否则：
    如果待启动实验程序等于'torchrun'，就调用 `_run_probe` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；把阶段处理结果追加或合并到结果集合集合；调用 `_add_item` 完成该函数的一项辅助处理；否则调用 `_run_probe` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；把阶段处理结果追加或合并到结果集合集合；调用 `_add_item` 完成该函数的一项辅助处理。
返回待处理项集合的当前值。
```

#### `build_preflight_report`

- **源码**：`app/tools/preflight_tools.py:558`
- **签名**：`def build_preflight_report(action: dict, repo_path: str | None, action_hash: str | None, run_dir: str) -> tuple[PreflightReport, list[dict]]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，返回报告和所有内部 probe 的 ExecutionResult。该函数接收待执行复现动作、代码仓库根目录、待执行复现动作的 Hash、本次复现运行目录，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `repo_path` | `str | None` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `action_hash` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `run_dir` | `str` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |

**输出**

- **Python 类型**：`tuple[PreflightReport, list[dict]]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
先尝试完成以下处理：
    调用 `_resolve_action_runner` 解析、规范化或转换当前输入，并把结果记为 多个解包结果。
如果出现 `(FileNotFoundError, KeyError, ValueError)`并把异常保存为捕获的异常对象：
    构造 `PreflightItem` 结构化领域对象，并把结果记为 当前处理项；构造 `PreflightReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告；返回当前构造的顺序或去重集合。
将 结果集合集合 初始化为空列表，用来收集后续结果；调用 `collect_static_preflight_items` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `collect_runtime_preflight_items` 完成该函数的一项辅助处理，并把结果记为 运行时集合；计算初始化顺序集合，并保存为 待处理项集合。
读取MCP Client 配置档案，并保存为 MCP Client 配置档案。
如果模式等于'strict' 且 模型或检索后端属于{'local', 'conda'}，就调用 `_add_item` 完成该函数的一项辅助处理。
遍历并筛选输入，将整理后的结果保存为 当前处理结果；计算计算当前表达式的结果，并保存为 当前处理结果；计算根据条件从两个候选结果中选择一个，并保存为 阶段摘要；构造 `PreflightReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告。
返回当前构造的顺序或去重集合。
```

#### `render_preflight_report_md`

- **源码**：`app/tools/preflight_tools.py:654`
- **签名**：`def render_preflight_report_md(report: PreflightReport) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收MCP 评测或运行报告，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `PreflightReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回整理、格式化或规范化后的文本表示。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行；将新的计算结果累加或合并到待输出的文本行；将新的计算结果累加或合并到待输出的文本行。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果，然后把新的处理结果追加或合并到待输出的文本行。
把新的处理结果追加或合并到待输出的文本行。
如果当前处理结果有值或为真：
    将新的计算结果累加或合并到待输出的文本行。
    遍历当前可迭代输入，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行。
将新的计算结果累加或合并到待输出的文本行。
遍历当前可迭代输入，每次把当前项记为当前处理项：
    把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行。
    如果当前处理结果有值或为真，就把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行。
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/tools/repair_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `validate_bounded_repair_command`

- **源码**：`app/tools/repair_tools.py:36`
- **签名**：`def validate_bounded_repair_command(command: str) -> tuple[bool, str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，校验 repair proposal 给出的新命令是否仍然在本阶段允许的边界内。该函数接收当前命令，用于作为 CLI 入口接收论文路径、仓库路径、运行 ID 或实验命令，启动对应复现阶段并把状态和产物输出给用户，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`tuple[bool, str]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
去除当前命令的首尾空白，并把规范化后的文本记为 当前处理结果。
如果当前处理结果为空或为假，就返回当前构造的顺序或去重集合。
如果由当前处理结果组成的集合或迭代器中存在满足“测试或状态标记属于当前处理结果”的项，就返回当前构造的顺序或去重集合。
先尝试完成以下处理：
    对当前处理结果中的文本执行规范化或拆分，并把结果记为 模型 token 用量。
如果出现 `ValueError`并把异常保存为捕获的异常对象：
    返回当前构造的顺序或去重集合。
如果模型 token 用量为空或为假，就返回当前构造的顺序或去重集合。
如果模型 token 用量中的对应字段属于当前处理结果，就返回当前构造的顺序或去重集合。
返回当前构造的顺序或去重集合。
```

#### `render_repair_proposal_md`

- **源码**：`app/tools/repair_tools.py:60`
- **签名**：`def render_repair_proposal_md(proposal: dict[str, Any]) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收修复或重跑提案，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `proposal` | `dict[str, Any]` | 修复或重跑提案；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回整理、格式化或规范化后的文本表示。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行；将新的计算结果累加或合并到待输出的文本行；从修复或重跑提案读取所需的状态或领域记录，并把结果记为 命令；将新的计算结果累加或合并到待输出的文本行。
如果命令有值或为真，就把新的处理结果追加或合并到待输出的文本行；否则把新的处理结果追加或合并到待输出的文本行。
把新的处理结果追加或合并到待输出的文本行；计算初始化顺序集合，并保存为 论文文档章节集合。
遍历由论文文档章节集合组成的集合或迭代器，每次把当前项记为多个解包结果：
    把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
    如果待处理项集合为空或为假：
        把新的处理结果追加或合并到待输出的文本行。
    否则：
        遍历由待处理项集合组成的集合或迭代器，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行。
从修复或重跑提案读取所需的状态或领域记录，并把结果记为 该调用返回的结果；将新的计算结果累加或合并到待输出的文本行。
如果当前处理结果为空或为假：
    把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
否则：
    遍历由当前处理结果组成的集合或迭代器，每次把当前项记为当前处理结果，然后把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行；把新的处理结果追加或合并到待输出的文本行。
    把新的处理结果追加或合并到待输出的文本行。
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `apply_command_repair_to_state`

- **源码**：`app/tools/repair_tools.py:116`
- **签名**：`def apply_command_repair_to_state(state: dict[str, Any], repaired_command: str) -> dict[str, Any]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把 bounded repair 作用到当前“被选中的命令”上，并重新生成 pending_action。该函数接收复现流程状态、命令，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict[str, Any]` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `repaired_command` | `str` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |

**输出**

- **Python 类型**：`dict[str, Any]`
- **语义**：返回已校验/规范化的命令文本、命令对象或命令集合；不等于已经执行。

**伪代码**

```text
调用 `deepcopy` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；从复现流程状态读取所需的状态或领域记录，并把结果记为 选中候选项的索引。
如果当前处理结果为空或为假，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果选中候选项的索引为空 或 选中候选项的索引小于0 或 选中候选项的索引不小于当前处理结果 的长度，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
读取当前处理结果中的对应字段，并保存为 命令；读取命令，并保存为 命令中的对应字段；计算计算当前表达式的结果，并保存为 前一项；从复现流程状态读取所需的状态或领域记录，并把结果记为 状态配置的 ID。
从前一项读取所需的状态或领域记录，并把结果记为 配置的 ID。
如果状态配置的 ID有值或为真 且 配置的 ID有值或为真 且 状态配置的 ID不等于配置的 ID，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
计算计算当前表达式的结果，并保存为 MCP Client 配置档案 ID；调用 `get_execution_profile` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 执行环境配置指纹；计算计算当前表达式的结果，并保存为 命令执行工作目录。
从命令读取所需的状态或领域记录，并把结果记为 数据来源标记；从命令读取所需的状态或领域记录，并把结果记为 基线接受或运行操作原因；调用 `build_run_action_from_command` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；返回包含 `execution_profile_id`、`execution_profile_fingerprint`、`edited_run_commands`、`pending_action`、`pending_action_hash` 字段的结构化映射。
```

### `app/tools/repository_lock_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `repository_lock_key`

- **源码**：`app/tools/repository_lock_tools.py:21`
- **签名**：`def repository_lock_key(repo_path: str | Path) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收代码仓库根目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `str | Path` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
调用 `str` 完成该函数的一项辅助处理，并把结果记为 规范化；计算输入内容的 SHA-256 身份摘要，并返回处理结果。
```

#### `acquire_repository_lock`

- **源码**：`app/tools/repository_lock_tools.py:27`
- **签名**：`def acquire_repository_lock(repo_path: str | Path, owner_run_id: str, timeout_seconds: float) -> Generator[str, None, None]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，获取跨进程排他锁；锁文件不写入论文仓库。该函数接收代码仓库根目录、运行的 ID、等待超时时间（秒），用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `Generator[str, None, None]` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_path` | `str | Path` | 代码仓库根目录路径；用于限制文件扫描、相对路径计算和后续工具访问范围。 |
| `owner_run_id` | `str` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。 |
| `timeout_seconds` | `float` | 超时或截止时间限制；用于防止等待/搜索/执行无限持续。 |

**输出**

- **Python 类型**：`Generator[str, None, None]`
- **语义**：返回惰性迭代结果，调用方逐项消费。

**伪代码**

```text
调用 `repository_lock_key` 完成该函数的一项辅助处理，并把结果记为 键；计算组合或计算已有值，并保存为 当前处理结果的目录；创建当前处理结果的目录对应的目录；计算组合或计算已有值，并保存为 当前处理结果的路径。
调用 `open` 完成该函数的一项辅助处理，并把结果记为 文件；计算组合或计算已有值，并保存为 当前处理结果。
先尝试完成以下处理：
    只要当前条件（使用固定配置或常量值）成立，就重复以下处理：
        先尝试完成以下处理：
            调用 `flock` 完成该函数的一项辅助处理；立即结束当前循环。
        如果出现 `BlockingIOError`：
            如果辅助操作“调用 `monotonic` 完成该函数的一项辅助处理”的结果不小于当前处理结果，就拒绝继续处理并抛出 `RepositoryLockBusyError`，向调用方报告输入或运行失败。
            调用 `sleep` 完成该函数的一项辅助处理。
    调用 `seek` 完成该函数的一项辅助处理；调用 `truncate` 完成该函数的一项辅助处理；向终端或输出流写出当前结果/诊断信息；提交文件中已完成的数据变更。
    调用 `fsync` 完成该函数的一项辅助处理；完成当前表达式对应的校验或状态操作。
无论成功还是失败，最后都要：
    先尝试完成以下处理：
        调用 `flock` 完成该函数的一项辅助处理。
    无论成功还是失败，最后都要：
        关闭文件并释放相关资源。
```

### `app/tools/safe_shell_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `assess_action_risk`

- **源码**：`app/tools/safe_shell_tools.py:35`
- **签名**：`def assess_action_risk(action: dict) -> ActionRisk`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待执行复现动作，用于检查输入、运行状态、内容身份和策略约束，阻止不满足复现条件的数据继续流转，最终标注为 `ActionRisk` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |

**输出**

- **Python 类型**：`ActionRisk`
- **语义**：返回 `ActionRisk` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
从待执行复现动作读取所需的状态或领域记录，并把结果记为 待启动实验程序；从待执行复现动作读取所需的状态或领域记录，并把结果记为 命令行或函数位置参数集合。
如果待启动实验程序为空或为假，就构造并返回 `ActionRisk` 结构化领域对象。
如果待启动实验程序属于当前处理结果，就构造并返回 `ActionRisk` 结构化领域对象。
如果待启动实验程序属于当前处理结果，就构造并返回 `ActionRisk` 结构化领域对象。
如果待启动实验程序属于{'pip', 'conda'} 且 当前输入内容属于命令行或函数位置参数集合，就构造并返回 `ActionRisk` 结构化领域对象。
如果待启动实验程序等于'python' 且 当前输入内容属于命令行或函数位置参数集合，就构造并返回 `ActionRisk` 结构化领域对象。
如果待启动实验程序属于{'python', 'torchrun', 'accelerate', 'bash'}，就构造并返回 `ActionRisk` 结构化领域对象。
构造并返回 `ActionRisk` 结构化领域对象。
```

### `app/tools/smoke_test_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_set_flag_value`

- **源码**：`app/tools/smoke_test_tools.py:41`
- **签名**：`def _set_flag_value(args: list[str], flag: str, new_value: str) -> tuple[list[str], bool]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，支持两类常见 flag 形式： 1. --batch_size 16 2. --batch_size=16。该函数接收命令行或函数位置参数集合、当前处理结果、值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `flag` | `str` | 名为 `flag` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `new_value` | `str` | 名为 `new_value` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[list[str], bool]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
构造临时集合、映射或轻量领域对象，并把结果记为 更新后的记录；计算使用固定配置或常量值，并保存为 发生变化的内容；计算使用固定配置或常量值，并保存为 当前候选项的索引。
只要当前候选项的索引小于更新后的记录 的长度，就重复以下处理：
    读取更新后的记录中的对应字段，并保存为 模型或命令 token。
    如果模型或命令 token等于当前处理结果 且 当前输入内容小于更新后的记录 的长度：
        如果更新后的记录中的对应字段不等于值，就读取值，并保存为 更新后的记录中的对应字段；计算使用固定配置或常量值，并保存为 发生变化的内容。
        将新的计算结果累加或合并到当前候选项的索引；跳过本轮剩余处理，直接进入下一轮。
    计算根据字段和固定文本生成格式化文本，并保存为 目录树缩进前缀。
    如果“检查模型或命令 token是否满足文本匹配条件”后得到肯定结果：
        如果模型或命令 token不等于格式化文本：f'{flag}={new_value}'，就计算根据字段和固定文本生成格式化文本，并保存为 更新后的记录中的对应字段；计算使用固定配置或常量值，并保存为 发生变化的内容。
    将新的计算结果累加或合并到当前候选项的索引。
返回当前构造的顺序或去重集合。
```

#### `_render_action_preview`

- **源码**：`app/tools/smoke_test_tools.py:71`
- **签名**：`def _render_action_preview(action: dict[str, Any]) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待执行复现动作，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict[str, Any]` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
从待执行复现动作读取所需的状态或领域记录，并把结果记为 待启动实验程序；从待执行复现动作读取所需的状态或领域记录，并把结果记为 命令行或函数位置参数集合；调用 `join` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并返回处理结果。
```

#### `derive_smoke_test_action`

- **源码**：`app/tools/smoke_test_tools.py:76`
- **签名**：`def derive_smoke_test_action(action: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，从 full action 派生 smoke action。该函数接收待执行复现动作，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict[str, Any]` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |

**输出**

- **Python 类型**：`tuple[dict[str, Any] | None, list[str], str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
从待执行复现动作读取所需的状态或领域记录，并把结果记为 待启动实验程序；构造临时集合、映射或轻量领域对象，并把结果记为 命令行或函数位置参数集合。
如果待启动实验程序不属于当前处理结果，就返回当前构造的顺序或去重集合。
构造临时集合、映射或轻量领域对象，并把结果记为 更新后的集合；将 覆盖默认配置的字段映射 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（调用 `items` 完成该函数的一项辅助处理），每次把当前项记为多个解包结果：
    调用 `_set_flag_value` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
    如果发生变化的内容有值或为真，就把新的处理结果追加或合并到覆盖默认配置的字段映射。
如果覆盖默认配置的字段映射为空或为假，就返回当前构造的顺序或去重集合。
计算按字段初始化键值映射，并保存为 当前处理结果；返回当前构造的顺序或去重集合。
```

#### `build_smoke_test_report`

- **源码**：`app/tools/smoke_test_tools.py:117`
- **签名**：`def build_smoke_test_report(action: dict[str, Any], action_hash: str | None, status: str, summary: str, applied_overrides: list[str], result: dict[str, Any] | None, log_path: str | None) -> SmokeTestReport`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收待执行复现动作、待执行复现动作的 Hash、当前状态、阶段摘要等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `SmokeTestReport` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict[str, Any]` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |
| `action_hash` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。 |
| `status` | `str` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `summary` | `str` | 阶段摘要；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `applied_overrides` | `list[str]` | `list[str]` 元素集合；元素代表的业务对象由参数名 `applied_overrides` 和调用位置确定。 |
| `result` | `dict[str, Any] | None` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。；默认 空值 |
| `log_path` | `str | None` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。；默认 空值 |

**输出**

- **Python 类型**：`SmokeTestReport`
- **语义**：返回 `SmokeTestReport` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `SmokeTestReport` 结构化领域对象。
```

#### `render_smoke_test_report_md`

- **源码**：`app/tools/smoke_test_tools.py:139`
- **签名**：`def render_smoke_test_report_md(report: SmokeTestReport) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收MCP 评测或运行报告，用于把复现过程中的结构化状态、证据或结果转换为可读、可传输或可持久化的表示，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `report` | `SmokeTestReport` | MCP 评测或运行报告；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回整理、格式化或规范化后的文本表示。

**伪代码**

```text
计算初始化顺序集合，并保存为 待输出的文本行；将新的计算结果累加或合并到待输出的文本行；将新的计算结果累加或合并到待输出的文本行。
如果“当前处理结果有值或为真”不成立：
    把新的处理结果追加或合并到待输出的文本行。
否则：
    遍历当前可迭代输入，每次把当前项记为当前处理项，然后把新的处理结果追加或合并到待输出的文本行。
把新的处理结果追加或合并到待输出的文本行。
如果阶段处理结果有值或为真，就将新的计算结果累加或合并到待输出的文本行。
调用 `join` 完成该函数的一项辅助处理，并返回处理结果。
```

### `app/tools/structured_output_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_derive_model_family`

- **源码**：`app/tools/structured_output_tools.py:21`
- **签名**：`def _derive_model_family(model_name: str | None) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收模型标识或模型配置的名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `model_name` | `str | None` | 名为 `model_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
如果模型标识或模型配置的名称为空或为假，就返回固定值 `'other'`。
对模型标识或模型配置的名称中的文本执行规范化或拆分，并把结果记为 转为小写的比较文本。
如果当前输入内容属于转为小写的比较文本，就返回固定值 `'mimo'`。
如果当前输入内容属于转为小写的比较文本，就返回固定值 `'gpt'`。
如果当前输入内容属于转为小写的比较文本，就返回固定值 `'qwen'`。
如果当前输入内容属于转为小写的比较文本，就返回固定值 `'deepseek'`。
返回固定值 `'other'`。
```

#### `_derive_provider`

- **源码**：`app/tools/structured_output_tools.py:36`
- **签名**：`def _derive_provider() -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终文本、路径、状态标签或内容身份摘要。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
对当前输入内容中的文本执行规范化或拆分，并把结果记为 Provider 基础地址。
如果当前输入内容属于Provider 基础地址，就返回固定值 `'mimo'`。
如果当前输入内容属于Provider 基础地址，就返回固定值 `'openai'`。
如果当前输入内容属于Provider 基础地址 或 当前输入内容属于Provider 基础地址，就返回固定值 `'qwen'`。
如果当前输入内容属于Provider 基础地址，就返回固定值 `'deepseek'`。
返回固定值 `'openai_compat'`。
```

#### `_get_default_telemetry`

- **源码**：`app/tools/structured_output_tools.py:52`
- **签名**：`def _get_default_telemetry() -> TelemetryPort`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `TelemetryPort` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`TelemetryPort`
- **语义**：返回 `TelemetryPort` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
声明后续会读写外层作用域中的 观测数据。
如果观测数据为空：
    先尝试完成以下处理：
        读取前一步操作返回对象的运行观测数据，并保存为 观测数据。
    如果出现 `Exception`：
        加载这一步需要的外部依赖；构造 `NoOpTelemetry` 结构化领域对象，并把结果记为 观测数据。
返回观测数据的当前值。
```

#### `_record_token_usage_safe`

- **源码**：`app/tools/structured_output_tools.py:63`
- **签名**：`def _record_token_usage_safe(token_usage: dict[str, Any] | None, telemetry: TelemetryPort | None, provider_label: str | None, model_name: str | None) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前处理结果、运行观测数据、模型服务商、模型标识或模型配置的名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `token_usage` | `dict[str, Any] | None` | 敏感凭证或其引用；不得写入日志、Prompt 或普通 Artifact。 |
| `telemetry` | `TelemetryPort | None` | 运行观测数据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `provider_label` | `str | None` | 名为 `provider_label` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |
| `model_name` | `str | None` | 名为 `model_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前处理结果为空或为假，就结束当前函数，不返回业务值。
先尝试完成以下处理：
    计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
如果出现 `Exception`：
    结束当前函数，不返回业务值。
先尝试完成以下处理：
    计算使用固定配置或常量值，并保存为 当前处理结果；计算使用固定配置或常量值，并保存为 当前处理结果。
    如果“计算数量、边界或类型判断结果”后得到肯定结果，就调用 `int` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `int` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
    计算计算当前表达式的结果，并保存为 模型服务商配置；调用 `_derive_model_family` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算按字段初始化键值映射，并保存为 当前处理结果。
    如果当前处理结果大于0：
        先尝试完成以下处理：
            调用 `counter` 完成该函数的一项辅助处理；调用 `counter` 完成该函数的一项辅助处理。
        如果出现 `Exception`：
            不执行额外操作。
    如果当前处理结果大于0：
        先尝试完成以下处理：
            调用 `counter` 完成该函数的一项辅助处理；调用 `counter` 完成该函数的一项辅助处理。
        如果出现 `Exception`：
            不执行额外操作。
如果出现 `Exception`：
    不执行额外操作。
```

#### `StructuredInvocationResult.succeeded`

- **源码**：`app/tools/structured_output_tools.py:159`
- **签名**：`def succeeded(self) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
返回比较判断结果。
```

#### `_plain_mapping`

- **源码**：`app/tools/structured_output_tools.py:163`
- **签名**：`def _plain_mapping(value: Any) -> dict[str, Any] | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把 Provider usage 等对象转换成可写入 JSON 的普通字典。该函数接收当前字段值，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `value` | `Any` | 待处理的业务内容或类型化值；具体是文本、记录还是字节由类型标注和调用位置确定。 |

**输出**

- **Python 类型**：`dict[str, Any] | None`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
如果当前字段值为空，就返回固定值 `空值`。
如果“计算数量、边界或类型判断结果”后得到肯定结果：
    复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
否则：
    如果“计算数量、边界或类型判断结果”后未得到肯定结果：
        先尝试完成以下处理：
            复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
        如果出现 `(TypeError, ValueError)`：
            返回固定值 `空值`。
将外部表示解析为结构化内容，并返回处理结果。
```

#### `_ResponseMetadataCapture.__init__`

- **源码**：`app/tools/structured_output_tools.py:187`
- **签名**：`def __init__(self) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算使用固定配置或常量值，并保存为 原因；计算使用固定配置或常量值，并保存为 当前处理结果。
```

#### `_ResponseMetadataCapture.on_llm_end`

- **源码**：`app/tools/structured_output_tools.py:191`
- **签名**：`def on_llm_end(self, response: Any, **kwargs: Any) -> None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收结构化响应、函数关键字参数映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `response` | `Any` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `**kwargs` | `Any` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 语言模型。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就调用 `_plain_mapping` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
遍历当前可迭代输入，每次把当前项记为当前处理结果：
    遍历当前可迭代输入，每次把当前项记为工作区生成代次：
        计算计算当前表达式的结果，并保存为 当前处理结果；调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 面向用户或日志的提示信息；计算计算当前表达式的结果，并保存为 响应元数据。
        如果原因为空，就计算计算当前表达式的结果，并保存为 原因。
        如果当前处理结果为空，就调用 `_plain_mapping` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
```

#### `_raw_to_text`

- **源码**：`app/tools/structured_output_tools.py:217`
- **签名**：`def _raw_to_text(raw: Any) -> str | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收原始内容，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `raw` | `Any` | 外部读取到的原始文本或进程输出；可能需要截断、规范化或脱敏后才能进入报告。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果原始内容为空，就返回固定值 `空值`。
调用 `getattr` 完成该函数的一项辅助处理，并把结果记为 业务内容。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就返回业务内容的当前值。
先尝试完成以下处理：
    将结构化内容序列化或编码为可传输表示，并返回处理结果。
如果出现 `TypeError`：
    调用 `str` 完成该函数的一项辅助处理，并返回处理结果。
```

#### `_response_diagnostics`

- **源码**：`app/tools/structured_output_tools.py:230`
- **签名**：`def _response_diagnostics(raw: Any, capture: _ResponseMetadataCapture) -> tuple[str | None, dict[str, Any] | None]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，优先读取 raw message，并用 callback 捕获结果补齐缺失字段。该函数接收原始内容、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `raw` | `Any` | 外部读取到的原始文本或进程输出；可能需要截断、规范化或脱敏后才能进入报告。 |
| `capture` | `_ResponseMetadataCapture` | 名为 `capture` 的 `_ResponseMetadataCapture` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`tuple[str | None, dict[str, Any] | None]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算计算当前表达式的结果，并保存为 响应元数据；计算计算当前表达式的结果，并保存为 原因；计算计算当前表达式的结果，并保存为 当前处理结果；返回当前构造的顺序或去重集合。
```

#### `_validation_error_input`

- **源码**：`app/tools/structured_output_tools.py:248`
- **签名**：`def _validation_error_input(exc: ValidationError) -> str | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，从 Pydantic JSON 错误中恢复导致校验失败的模型原始字符串。该函数接收捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `ValidationError` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
将 候选结果集合 初始化为空列表，用来收集后续结果。
遍历辅助操作产生的可迭代结果（调用 `errors` 完成该函数的一项辅助处理），每次把当前项记为错误信息：
    从错误信息读取所需的状态或领域记录，并把结果记为 值。
    如果“计算数量、边界或类型判断结果”后得到肯定结果，就把值追加或合并到候选结果集合。
返回按条件选出的结果。
```

#### `_looks_like_truncation`

- **源码**：`app/tools/structured_output_tools.py:258`
- **签名**：`def _looks_like_truncation(error_message: str, raw_text: str | None, finish_reason: str | None) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，该函数接收错误、原始内容的文本、原因，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `error_message` | `str` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |
| `raw_text` | `str | None` | 已规范化或待输出的文本；进入持久化或 Prompt 前可能需要限长和脱敏。 |
| `finish_reason` | `str | None` | 名为 `finish_reason` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
调用 `str` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，再对返回文本执行规范化或拆分，并把结果记为 原因。
如果原因属于{'length', 'max_tokens', 'max_output_tokens'}，就返回固定值 `真`。
对当前输入内容中的文本执行规范化或拆分，并把结果记为 待处理的论文或源码材料；检查当前可迭代输入中是否存在满足“测试或状态标记属于待处理的论文或源码材料”的项，并返回处理结果。
```

#### `_is_transient_provider_exception`

- **源码**：`app/tools/structured_output_tools.py:284`
- **签名**：`def _is_transient_provider_exception(exc: Exception) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，只把明确的瞬时传输或限流故障标记为可重试。该函数接收捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `Exception` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
对当前输入内容中的文本执行规范化或拆分，并把结果记为 待处理的论文或源码材料；检查当前可迭代输入中是否存在满足“测试或状态标记属于待处理的论文或源码材料”的项，并返回处理结果。
```

#### `_is_output_length_exception`

- **源码**：`app/tools/structured_output_tools.py:305`
- **签名**：`def _is_output_length_exception(exc: Exception) -> bool`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，识别由结构化解析器抛出的输出预算截断。该函数接收捕获的异常，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终一个可用于路由、校验或安全判断的布尔结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `exc` | `Exception` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`bool`
- **语义**：返回条件判断结果：`True` 表示满足，`False` 表示不满足。

**伪代码**

```text
对前一步操作返回对象的当前处理结果中的文本执行规范化或拆分，并把结果记为 错误类型；调用 `str` 完成该函数的一项辅助处理，再对返回文本执行规范化或拆分，并把结果记为 待处理的论文或源码材料；返回组合判断结果。
```

#### `_invoke_with_transport_retry`

- **源码**：`app/tools/structured_output_tools.py:317`
- **签名**：`def _invoke_with_transport_retry(invoke: Callable[[], Any], prompt_kind: str, attempt_number_start: int, max_retries: int, base_seconds: float) -> tuple[Any | None, list[StructuredOutputAttempt], Exception | None]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，只负责 Provider transport retry，不消费 schema validation retry。该函数接收当前处理结果、类别、尝试编号、重试次数上限等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `invoke` | `Callable[[], Any]` | 可调用依赖；其参数和返回契约由类型标注限定。 |
| `prompt_kind` | `str` | 名为 `prompt_kind` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `attempt_number_start` | `int` | 名为 `attempt_number_start` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |
| `max_retries` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。 |
| `base_seconds` | `float` | 名为 `base_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`tuple[Any | None, list[StructuredOutputAttempt], Exception | None]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
将 模型服务商尝试记录集合集合 初始化为空列表，用来收集后续结果。
遍历限定范围内的序列，每次把当前项记为当前处理结果的索引：
    先尝试完成以下处理：
        返回当前构造的顺序或去重集合。
    如果出现 `ValidationError`：
        重新抛出当前异常，保持原始失败信息。
    如果出现 `Exception`并把异常保存为捕获的异常对象：
        调用 `_is_transient_provider_exception` 校验当前输入或状态，并把结果记为 是否允许重试的判断；计算计算当前表达式的结果，并保存为 当前处理结果；把新的处理结果追加或合并到模型服务商尝试记录集合集合。
        如果当前处理结果为空或为假，就返回当前构造的顺序或去重集合。
        调用 `sleep` 完成该函数的一项辅助处理。
拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
```

#### `_raw_to_preview`

- **源码**：`app/tools/structured_output_tools.py:364`
- **签名**：`def _raw_to_preview(raw: Any, max_chars: int) -> str | None`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，从 LangChain AIMessage 或普通对象提取可审计预览。该函数接收原始内容、最大字符数，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `str | None` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `raw` | `Any` | 外部读取到的原始文本或进程输出；可能需要截断、规范化或脱敏后才能进入报告。 |
| `max_chars` | `int` | 名为 `max_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`str | None`
- **语义**：返回 `str | None` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `_raw_to_text` 完成该函数的一项辅助处理，并把结果记为 待处理文本；返回按条件选出的结果。
```

#### `_build_validation_retry_prompt`

- **源码**：`app/tools/structured_output_tools.py:375`
- **签名**：`def _build_validation_retry_prompt(original_prompt: str, schema: type[BaseModel], validation_error: str, previous_raw_preview: str | None, schema_already_in_prompt: bool) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把上一轮具体错误反馈给模型。该函数接收当前处理结果、输入输出 Schema 契约、错误、前一项等输入，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `original_prompt` | `str` | 名为 `original_prompt` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `schema` | `type[BaseModel]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |
| `validation_error` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |
| `previous_raw_preview` | `str | None` | 名为 `previous_raw_preview` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `schema_already_in_prompt` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 假 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
计算根据条件从两个候选结果中选择一个，并保存为 章节；对当前输入内容中的文本执行规范化或拆分，并返回处理结果。
```

#### `_build_json_mode_prompt`

- **源码**：`app/tools/structured_output_tools.py:419`
- **签名**：`def _build_json_mode_prompt(original_prompt: str, schema: type[BaseModel]) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，json_object 只保证 JSON 语法，必须在 prompt 中显式提供字段契约。该函数接收当前处理结果、输入输出 Schema 契约，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `original_prompt` | `str` | 名为 `original_prompt` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `schema` | `type[BaseModel]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
将结构化内容序列化或编码为可传输表示，并把结果记为 JSON；对当前输入内容中的文本执行规范化或拆分，并返回处理结果。
```

#### `_build_truncation_retry_prompt`

- **源码**：`app/tools/structured_output_tools.py:445`
- **签名**：`def _build_truncation_retry_prompt(original_prompt: str, validation_error: str) -> str`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，截断时不再重复附加完整 schema，避免 retry prompt 继续膨胀。该函数接收当前处理结果、错误，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终文本、路径、状态标签或内容身份摘要。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `original_prompt` | `str` | 名为 `original_prompt` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `validation_error` | `str` | 异常、错误记录或错误分类信息，用于失败处理和诊断。 |

**输出**

- **Python 类型**：`str`
- **语义**：返回文本或领域字符串；其具体用途由函数名和调用位置确定，例如路径、状态、报告或序列化内容。

**伪代码**

```text
对当前输入内容中的文本执行规范化或拆分，并返回处理结果。
```

#### `invoke_structured_with_retry`

- **源码**：`app/tools/structured_output_tools.py:473`
- **签名**：`def invoke_structured_with_retry(llm: Any, schema: type[SchemaT], prompt: str, method: str, strict: bool, max_retries: int, raw_preview_chars: int, provider_max_retries: int, provider_retry_base_seconds: float, telemetry: TelemetryPort | None, telemetry_provider_label: str | None, telemetry_model_name: str | None) -> StructuredInvocationResult[SchemaT]`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，使用 Provider 结构化输出能力 + Pydantic 完成有限重试。该函数接收语言模型、输入输出 Schema 契约、发给模型的结构化提示、论文方法或 HTTP 方法等输入，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `llm` | `Any` | 名为 `llm` 的 `Any` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `schema` | `type[SchemaT]` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |
| `prompt` | `str` | 用户目标、检索问题、反馈或待处理文本；会作为当前阶段的业务语境输入，并可能受到长度/脱敏约束。 |
| `method` | `str` | 论文方法或 HTTP 方法；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 'json_schema' |
| `strict` | `bool` | 布尔条件或能力开关，用于控制流程分支。；默认 真 |
| `max_retries` | `int` | 输出、检索或读取的数量/容量上限，用于控制结果规模和资源消耗。；默认 2 |
| `raw_preview_chars` | `int` | 名为 `raw_preview_chars` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 2000 |
| `provider_max_retries` | `int` | 名为 `provider_max_retries` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 2 |
| `provider_retry_base_seconds` | `float` | 名为 `provider_retry_base_seconds` 的数量、序号、分数或时间参数；有效范围由函数用途和校验分支确定。；默认 0.5 |
| `telemetry` | `TelemetryPort | None` | 运行观测数据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `telemetry_provider_label` | `str | None` | 名为 `telemetry_provider_label` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |
| `telemetry_model_name` | `str | None` | 名为 `telemetry_model_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`StructuredInvocationResult[SchemaT]`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
如果论文方法或 HTTP 方法不属于{'json_schema', 'function_calling', 'json_mode'}，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果重试次数上限小于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果模型服务商集合小于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
如果模型服务商集合小于0，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
先尝试完成以下处理：
    计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
如果出现 `Exception`：
    加载这一步需要的外部依赖；构造 `NoOpTelemetry` 结构化领域对象，并把结果记为 该调用返回的结果。
将 模型尝试记录集合 初始化为空列表，用来收集后续结果；计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果。
先尝试完成以下处理：
    如果论文方法或 HTTP 方法等于'json_mode'，就调用 `with_structured_output` 完成该函数的一项辅助处理，并把结果记为 语言模型；否则调用 `with_structured_output` 完成该函数的一项辅助处理，并把结果记为 语言模型。
如果出现 `Exception`并把异常保存为捕获的异常对象：
    把新的处理结果追加或合并到模型尝试记录集合；构造并返回 `StructuredInvocationResult` 结构化领域对象。
计算根据条件从两个候选结果中选择一个，并保存为 当前处理结果；读取当前处理结果，并保存为 当前。
遍历限定范围内的序列，每次把当前项记为尝试的索引：
    计算根据条件从两个候选结果中选择一个，并保存为 类别；调用 `_ResponseMetadataCapture` 完成该函数的一项辅助处理，并把结果记为 元数据。
    先尝试完成以下处理：
        调用 `_invoke_with_transport_retry` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；把尝试记录集合集合追加或合并到模型尝试记录集合。
    如果出现 `ValidationError`并把异常保存为捕获的异常对象：
        调用 `str` 完成该函数的一项辅助处理，并把结果记为 错误；调用 `_validation_error_input` 完成该函数的一项辅助处理，并把结果记为 原始内容的文本；调用 `_response_diagnostics` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `_looks_like_truncation` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果。
        把新的处理结果追加或合并到模型尝试记录集合；调用 `_record_token_usage_safe` 完成该函数的一项辅助处理。
        如果尝试的索引不小于重试次数上限，就立即结束当前循环。
        计算根据条件从两个候选结果中选择一个，并保存为 当前；跳过本轮剩余处理，直接进入下一轮。
    如果错误不为空：
        如果“调用 `_is_output_length_exception` 校验当前输入或状态”后得到肯定结果：
            读取模型尝试记录集合中的对应字段，并保存为 后续步骤使用的结果；计算使用固定配置或常量值，并保存为 当前状态；计算使用固定配置或常量值，并保存为 当前处理结果。
            如果尝试的索引小于重试次数上限，就调用 `_build_truncation_retry_prompt` 组装当前阶段需要的领域对象，并把结果记为 当前；跳过本轮剩余处理，直接进入下一轮。
        立即结束当前循环。
    计算组合或计算已有值，并保存为 尝试编号。
    如果“计算数量、边界或类型判断结果”后得到肯定结果：
        读取结构化响应，并保存为 解析后的结果；计算使用固定配置或常量值，并保存为 原始内容；计算使用固定配置或常量值，并保存为 错误。
    否则：
        如果“计算数量、边界或类型判断结果”后得到肯定结果，就从结构化响应读取所需的状态或领域记录，并把结果记为 解析后的结果；从结构化响应读取所需的状态或领域记录，并把结果记为 原始内容；从结构化响应读取所需的状态或领域记录，并把结果记为 错误；否则读取结构化响应，并保存为 解析后的结果；计算使用固定配置或常量值，并保存为 原始内容；计算使用固定配置或常量值，并保存为 错误。
    调用 `_raw_to_text` 完成该函数的一项辅助处理，并把结果记为 原始内容的文本；调用 `_raw_to_preview` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `_response_diagnostics` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
    先尝试完成以下处理：
        如果解析后的结果为空，就拒绝继续处理并抛出 `ValueError`，向调用方报告输入或运行失败。
        复制、序列化或校验结构化领域对象，并把结果记为 当前字段值。
    如果出现 `(TypeError, ValueError, ValidationError)`并把异常保存为捕获的异常对象：
        调用 `str` 完成该函数的一项辅助处理，并把结果记为 错误；调用 `_looks_like_truncation` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；把新的处理结果追加或合并到模型尝试记录集合；调用 `_record_token_usage_safe` 完成该函数的一项辅助处理。
        如果尝试的索引不小于重试次数上限，就立即结束当前循环。
        计算根据条件从两个候选结果中选择一个，并保存为 当前；跳过本轮剩余处理，直接进入下一轮。
    把新的处理结果追加或合并到模型尝试记录集合；调用 `_record_token_usage_safe` 完成该函数的一项辅助处理；构造并返回 `StructuredInvocationResult` 结构化领域对象。
构造并返回 `StructuredInvocationResult` 结构化领域对象。
```

#### `write_structured_output_trace`

- **源码**：`app/tools/structured_output_tools.py:774`
- **签名**：`def write_structured_output_trace(result: StructuredInvocationResult[Any], node_name: str, schema_name: str, output_dir: Path, fallback_used: bool, model_invocation_id: str | None, model_decision_sha256: str | None, model_profile_id: str | None, model_name: str | None, model_usage_quality: str | None) -> Path`
- **作用**：在为论文阅读、源码分析和复现实验提供受控工具调用的阶段中，把结构化调用过程写成独立 artifact，方便调试和评测。该函数接收阶段处理结果、当前流程节点的名称、输入输出 Schema 契约的名称、复现输出目录等输入，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `result` | `StructuredInvocationResult[Any]` | 前序调用产生的结构化响应、结果或执行结论，供当前函数继续判断或投影。 |
| `node_name` | `str` | 名为 `node_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |
| `schema_name` | `str` | 结构化输出 Schema 或其名称；用于约束解析结果的字段和类型。 |
| `output_dir` | `Path` | 运行产物或受控工作区的目录路径；用于隔离本次运行生成的文件。 |
| `fallback_used` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `model_invocation_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `model_decision_sha256` | `str | None` | 内容身份摘要，通常是 64 位小写十六进制 SHA-256；它不是可执行内容或授权凭证。；默认 空值 |
| `model_profile_id` | `str | None` | 稳定业务标识符，用于查询、关联或幂等绑定；它不是文件路径或内容 Hash。；默认 空值 |
| `model_name` | `str | None` | 名为 `model_name` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |
| `model_usage_quality` | `str | None` | 名为 `model_usage_quality` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 空值 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
创建复现输出目录对应的目录；计算组合或计算已有值，并保存为 文件或目录路径；计算按字段初始化键值映射，并保存为 结构化请求载荷；将处理结果写入文件或目录路径指定的文件。
返回文件或目录路径的当前值。
```

### `tests/test_action_builder_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_profile`

- **源码**：`tests/test_action_builder_node.py:10`
- **签名**：`def _profile(tmp_path) -> ExecutionProfile`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ExecutionProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`ExecutionProfile`
- **语义**：返回 `ExecutionProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现工作区对应的目录；构造并返回 `ExecutionProfile` 结构化领域对象。
```

#### `test_action_builder_builds_pending_action_from_first_run_command`

- **源码**：`tests/test_action_builder_node.py:22`
- **签名**：`def test_action_builder_builds_pending_action_from_first_run_command(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；计算按字段初始化键值映射，并保存为 复现流程状态。
在上下文“调用 `patch` 完成该函数的一项辅助处理”中调用 `action_builder_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
读取阶段处理结果中的对应字段，并保存为 待执行复现动作；断言待执行复现动作中的对应字段等于'run_command'；不满足就终止当前测试或流程；断言待执行复现动作中的对应字段等于'python'；不满足就终止当前测试或流程；断言待执行复现动作中的对应字段等于['train.py', '--config', 'configs/base.yaml']；不满足就终止当前测试或流程。
断言待执行复现动作中的对应字段等于根目录；不满足就终止当前测试或流程；断言待执行复现动作中的对应字段等于'run baseline training'；不满足就终止当前测试或流程；断言待执行复现动作中的对应字段等于'script'；不满足就终止当前测试或流程；断言待执行复现动作中的对应字段等于[根目录]；不满足就终止当前测试或流程。
断言待执行复现动作中的对应字段等于'none'；不满足就终止当前测试或流程；断言待执行复现动作中的对应字段为空；不满足就终止当前测试或流程；断言待执行复现动作中的对应字段等于MCP Client 配置档案 ID；不满足就终止当前测试或流程；断言待执行复现动作中的对应字段有值或为真；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段等于辅助操作“调用 `compute_action_hash` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
```

#### `test_action_builder_returns_no_action_when_run_commands_is_empty`

- **源码**：`tests/test_action_builder_node.py:70`
- **签名**：`def test_action_builder_returns_no_action_when_run_commands_is_empty() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `action_builder_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'no_action'；不满足就终止当前测试或流程。
```

#### `test_action_builder_keeps_existing_pending_action`

- **源码**：`tests/test_action_builder_node.py:78`
- **签名**：`def test_action_builder_keeps_existing_pending_action() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 已有；计算按字段初始化键值映射，并保存为 复现流程状态；调用 `action_builder_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段等于已有；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段等于'known_hash'；不满足就终止当前测试或流程。
```

### `tests/test_action_capability_policy.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_action`

- **源码**：`tests/test_action_capability_policy.py:9`
- **签名**：`def _action(workspace, **updates) -> dict`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次复现工作区、待应用的字段更新映射，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `workspace` | `未显式标注` | 本次复现工作区；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `**updates` | `未显式标注` | 额外关键字参数映射。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 待执行复现动作；把待应用的字段更新映射追加或合并到待执行复现动作；返回待执行复现动作的当前值。
```

#### `_profile`

- **源码**：`tests/test_action_capability_policy.py:26`
- **签名**：`def _profile(tmp_path) -> ExecutionProfile`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ExecutionProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`ExecutionProfile`
- **语义**：返回 `ExecutionProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现工作区对应的目录；构造并返回 `ExecutionProfile` 结构化领域对象。
```

#### `test_policy_rejects_network_when_profile_denies`

- **源码**：`tests/test_action_capability_policy.py:40`
- **签名**：`def test_policy_rejects_network_when_profile_denies(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；调用 `evaluate_action_capabilities` 完成该函数的一项辅助处理，并把结果记为 人工决策结果；断言当前处理结果是假；不满足就终止当前测试或流程；断言当前可迭代输入中存在满足“待解析或验证的代码等于'NETWORK_NOT_ALLOWED'”的项；不满足就终止当前测试或流程。
```

#### `test_policy_rejects_writable_path_escape`

- **源码**：`tests/test_action_capability_policy.py:59`
- **签名**：`def test_policy_rejects_writable_path_escape(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；计算组合或计算已有值，并保存为 当前处理结果；创建当前处理结果对应的目录；调用 `evaluate_action_capabilities` 完成该函数的一项辅助处理，并把结果记为 人工决策结果。
断言当前处理结果是假；不满足就终止当前测试或流程；断言当前可迭代输入中存在满足“待解析或验证的代码等于'WRITABLE_PATH_NOT_ALLOWED'”的项；不满足就终止当前测试或流程。
```

#### `test_action_budget_cannot_expand_profile`

- **源码**：`tests/test_action_capability_policy.py:78`
- **签名**：`def test_action_budget_cannot_expand_profile(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；调用 `evaluate_action_capabilities` 完成该函数的一项辅助处理，并把结果记为 人工决策结果；断言当前处理结果是假；不满足就终止当前测试或流程；断言当前可迭代输入中存在满足“待解析或验证的代码等于'RESOURCE_BUDGET_EXPANSION'”的项；不满足就终止当前测试或流程。
```

### `tests/test_command_selection_cli.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `FakeGraph.__init__`

- **源码**：`tests/test_command_selection_cli.py:18`
- **签名**：`def __init__(self, values: dict, next_nodes: tuple[str, ...] = ("command_selection",))`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收状态字段集合、下一项集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `values` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `next_nodes` | `tuple[str, ...]` | `tuple[str, ...]` 元素集合；元素代表的业务对象由参数名 `next_nodes` 和调用位置确定。；默认 ('command_selection') |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `SimpleNamespace` 结构化领域对象，并把结果记为 MCP 能力快照；将 当前处理结果 初始化为空列表，用来收集后续结果。
```

#### `FakeGraph.get_state`

- **源码**：`tests/test_command_selection_cli.py:22`
- **签名**：`def get_state(self, config: dict) -> SimpleNamespace`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收运行配置，用于从受控存储、运行目录或服务端口读取论文复现所需的记录、证据和状态，最终标注为 `SimpleNamespace` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `config` | `dict` | 配置或选项对象；描述运行约束，不等同于执行结果。 |

**输出**

- **Python 类型**：`SimpleNamespace`
- **语义**：返回 `SimpleNamespace` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
返回MCP 能力快照的当前值。
```

#### `FakeGraph.invoke`

- **源码**：`tests/test_command_selection_cli.py:25`
- **签名**：`def invoke(self, command: object, config: dict) -> dict`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前命令、运行配置，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `command` | `object` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。 |
| `config` | `dict` | 配置或选项对象；描述运行约束，不等同于执行结果。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
把新的处理结果追加或合并到当前处理结果；返回包含 `final_status` 字段的结构化映射。
```

#### `test_resume_command_selection_loads_generated_input`

- **源码**：`tests/test_command_selection_cli.py:30`
- **签名**：`def test_resume_command_selection_loads_generated_input(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现运行目录；计算组合或计算已有值，并保存为 输入内容的路径；创建父级目录或父领域对象对应的目录；计算初始化顺序集合，并保存为 候选运行命令集合。
计算按字段初始化键值映射，并保存为 结构化请求载荷；将处理结果写入输入内容的路径指定的文件；构造 `FakeGraph` 结构化领域对象，并把结果记为 复现流程图。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”中调用 `resume_command_selection` 完成该函数的一项辅助处理，退出时自动清理资源。
断言当前处理结果 的长度等于1；不满足就终止当前测试或流程；读取当前处理结果中的对应字段，并保存为 多个解包结果；断言当前处理结果等于结构化请求载荷；不满足就终止当前测试或流程；断言运行配置等于{'configurable': {'thread_id': 'thread-001'}}；不满足就终止当前测试或流程。
```

#### `test_resume_command_selection_generates_missing_input_before_resume`

- **源码**：`tests/test_command_selection_cli.py:76`
- **签名**：`def test_resume_command_selection_generates_missing_input_before_resume(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现运行目录；计算初始化顺序集合，并保存为 候选运行命令集合；构造 `FakeGraph` 结构化领域对象，并把结果记为 复现流程图。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”中调用 `resume_command_selection` 完成该函数的一项辅助处理，退出时自动清理资源。
计算组合或计算已有值，并保存为 输入内容的路径；断言辅助操作“将外部表示解析为结构化内容”的结果等于{'run_commands_hash': 辅助操作“调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果”的结果, 'selected_index': 0, 'edits': [{'index': 0, 'command': 'python train.py --help'}]}；不满足就终止当前测试或流程；断言当前处理结果等于[]；不满足就终止当前测试或流程。
```

#### `test_resume_command_selection_refreshes_stale_generated_input`

- **源码**：`tests/test_command_selection_cli.py:114`
- **签名**：`def test_resume_command_selection_refreshes_stale_generated_input(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现运行目录；计算组合或计算已有值，并保存为 输入内容的路径；创建父级目录或父领域对象对应的目录；计算初始化顺序集合，并保存为 当前处理结果。
计算初始化顺序集合，并保存为 当前集合；计算按字段初始化键值映射，并保存为 当前处理结果；将处理结果写入输入内容的路径指定的文件；构造 `FakeGraph` 结构化领域对象，并把结果记为 复现流程图。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”中调用 `resume_command_selection` 完成该函数的一项辅助处理，退出时自动清理资源。
断言辅助操作“将外部表示解析为结构化内容”的结果等于辅助操作“调用 `build_command_selection_template` 组装当前阶段需要的领域对象”的结果；不满足就终止当前测试或流程；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；断言当前处理结果 的长度等于1；不满足就终止当前测试或流程；断言辅助操作“将外部表示解析为结构化内容”的结果等于当前处理结果；不满足就终止当前测试或流程。
断言当前处理结果等于[]；不满足就终止当前测试或流程。
```

#### `test_resume_command_selection_rejects_stale_explicit_input`

- **源码**：`tests/test_command_selection_cli.py:165`
- **签名**：`def test_resume_command_selection_rejects_stale_explicit_input(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现运行目录；计算初始化顺序集合，并保存为 当前集合；计算组合或计算已有值，并保存为 过期；将处理结果写入过期指定的文件。
构造 `FakeGraph` 结构化领域对象，并把结果记为 复现流程图。
进入上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”，退出时自动清理资源：
    在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `resume_command_selection` 完成该函数的一项辅助处理，退出时自动清理资源。
断言当前处理结果等于[]；不满足就终止当前测试或流程。
```

#### `test_resume_command_selection_rejects_wrong_interrupt`

- **源码**：`tests/test_command_selection_cli.py:198`
- **签名**：`def test_resume_command_selection_rejects_wrong_interrupt(tmp_path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `FakeGraph` 结构化领域对象，并把结果记为 复现流程图。
进入上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”，退出时自动清理资源：
    在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `resume_command_selection` 完成该函数的一项辅助处理，退出时自动清理资源。
断言当前处理结果等于[]；不满足就终止当前测试或流程。
```

### `tests/test_command_selection_contract.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_response`

- **源码**：`tests/test_command_selection_contract.py:36`
- **签名**：`def _response(selected_index: int, edits: list[CommandEdit] | None, run_commands_hash: str | None) -> CommandSelectionResponse`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收选中候选项的索引、命令修改项集合、候选运行命令集合的 Hash，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `selected_index` | `int` | 候选集合中的零基索引，用于定位选中项；它不是业务 ID 或内容 Hash。；默认 0 |
| `edits` | `list[CommandEdit] | None` | 命令修改项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。；默认 空值 |
| `run_commands_hash` | `str | None` | 待展示、校验或执行的命令文本/结构化命令；仅进入 Executor 路径后才可能产生执行副作用。；默认 空值 |

**输出**

- **Python 类型**：`CommandSelectionResponse`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
构造并返回 `CommandSelectionResponse` 结构化领域对象。
```

#### `test_hash_ignores_dict_key_order_but_keeps_list_order`

- **源码**：`tests/test_command_selection_contract.py:52`
- **签名**：`def test_hash_ignores_dict_key_order_but_keeps_list_order()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
遍历并筛选输入，将整理后的结果保存为 键集合集合；断言辅助操作“调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果”的结果等于辅助操作“调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程；断言辅助操作“调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果”的结果不等于辅助操作“调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
```

#### `test_validates_normalizes_and_applies_multiple_edits`

- **源码**：`tests/test_command_selection_contract.py:66`
- **签名**：`def test_validates_normalizes_and_applies_multiple_edits()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_response` 完成该函数的一项辅助处理，并把结果记为 结构化响应；调用 `validate_command_selection_response` 校验当前输入或状态，并把结果记为 规范化后的文本；调用 `apply_command_edits` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言选中候选项的索引等于1；不满足就终止当前测试或流程。
断言“检查当前命令是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前处理结果中的对应字段中的对应字段是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言当前处理结果中的对应字段中的对应字段等于候选运行命令集合中的对应字段中的对应字段；不满足就终止当前测试或流程；断言“检查候选运行命令集合中的对应字段中的对应字段是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_rejects_stale_request_hash`

- **源码**：`tests/test_command_selection_contract.py:107`
- **签名**：`def test_rejects_stale_request_hash()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_command_selection_response` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_rejects_inconsistent_server_preview_hash`

- **源码**：`tests/test_command_selection_contract.py:123`
- **签名**：`def test_rejects_inconsistent_server_preview_hash()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_command_selection_response` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_rejects_invalid_selection_semantics`

- **源码**：`tests/test_command_selection_contract.py:161`
- **签名**：`def test_rejects_invalid_selection_semantics(selected_index: 未显式标注, edits: 未显式标注, message: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收选中候选项的索引、命令修改项集合、面向用户或日志的提示信息，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `selected_index` | `未显式标注` | 候选集合中的零基索引，用于定位选中项；它不是业务 ID 或内容 Hash。 |
| `edits` | `未显式标注` | 命令修改项集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `message` | `未显式标注` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_command_selection_response` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_duplicate_edit_indexes_are_rejected_by_schema`

- **源码**：`tests/test_command_selection_contract.py:179`
- **签名**：`def test_duplicate_edit_indexes_are_rejected_by_schema()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `_response` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_command_selection_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_prepare`

- **源码**：`tests/test_command_selection_node.py:18`
- **签名**：`def _prepare(state: dict, run_state: dict) -> dict`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现流程状态、本次运行状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `run_state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 状态；把新的处理结果追加或合并到状态；返回状态的当前值。
```

#### `test_command_selection_selects_index_without_edits`

- **源码**：`tests/test_command_selection_node.py:24`
- **签名**：`def test_command_selection_selects_index_without_edits(run_state) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；调用 `_prepare` 完成该函数的一项辅助处理，并把结果记为 复现流程状态；调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果，并把结果记为 候选运行命令集合的 Hash；调用 `next` 完成该函数的一项辅助处理，并把结果记为 记录。
断言记录中的对应字段等于本次运行状态中的对应字段；不满足就终止当前测试或流程；断言复现流程状态中的对应字段等于记录中的对应字段；不满足就终止当前测试或流程。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”中调用 `command_selection_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段等于1；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段中的对应字段等于'python b.py'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于1；不满足就终止当前测试或流程；把外部位置解析为文件系统路径对象，并把结果记为 输入内容的路径。
断言“检查输入内容的路径的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言辅助操作“将外部表示解析为结构化内容”的结果等于{'run_commands_hash': 候选运行命令集合的 Hash, 'selected_index': 0, 'edits': [{'index': 0, 'command': 'python a.py'}, {'index': 1, 'command': 'python b.py'}]}；不满足就终止当前测试或流程。
断言辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果属于阶段处理结果中的对应字段；不满足就终止当前测试或流程；计算初始化去重集合，并保存为 期望集合；遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前输入内容等于期望集合；不满足就终止当前测试或流程。
断言由当前处理结果组成的集合或迭代器中每一项都满足“领域记录中的对应字段等于本次运行状态中的对应字段”的项；不满足就终止当前测试或流程；断言由当前处理结果组成的集合或迭代器中每一项都满足“辅助操作“把外部位置解析为文件系统路径对象”的结果属于前一步操作返回对象的当前处理结果”的项；不满足就终止当前测试或流程。
```

#### `test_command_selection_applies_multiple_command_edits`

- **源码**：`tests/test_command_selection_node.py:106`
- **签名**：`def test_command_selection_applies_multiple_command_edits(run_state) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；调用 `_prepare` 完成该函数的一项辅助处理，并把结果记为 复现流程状态；调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果，并把结果记为 候选运行命令集合的 Hash。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”中调用 `command_selection_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段等于0；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段中的对应字段等于'python train-ntu60.py --dataset_path /data/ntu60 --batch_size 8'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段 的长度等于2；不满足就终止当前测试或流程。
```

#### `test_command_selection_does_not_overwrite_edited_input`

- **源码**：`tests/test_command_selection_node.py:156`
- **签名**：`def test_command_selection_does_not_overwrite_edited_input(run_state: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；调用 `_prepare` 完成该函数的一项辅助处理，并把结果记为 复现流程状态；把外部位置解析为文件系统路径对象，并把结果记为 输入内容的路径；计算按字段初始化键值映射，并保存为 当前处理结果。
将处理结果写入输入内容的路径指定的文件。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”中调用 `command_selection_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言辅助操作“将外部表示解析为结构化内容”的结果等于当前处理结果；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段中的对应字段等于'python train.py --epochs 1'；不满足就终止当前测试或流程。
```

#### `test_command_selection_clears_stale_execution_state`

- **源码**：`tests/test_command_selection_node.py:197`
- **签名**：`def test_command_selection_clears_stale_execution_state(run_state: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；调用 `_prepare` 完成该函数的一项辅助处理，并把结果记为 复现流程状态；调用 `compute_run_commands_hash` 计算内容身份、分数或派生结果，并把结果记为 候选运行命令集合的 Hash。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”中调用 `command_selection_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段是假；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于{}；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程。
```

#### `test_command_selection_refreshes_stale_input_and_keeps_backup`

- **源码**：`tests/test_command_selection_node.py:244`
- **签名**：`def test_command_selection_refreshes_stale_input_and_keeps_backup(run_state: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化顺序集合，并保存为 当前处理结果；计算初始化顺序集合，并保存为 当前处理结果；调用 `_prepare` 完成该函数的一项辅助处理，并把结果记为 复现流程状态；把外部位置解析为文件系统路径对象，并把结果记为 输入内容的路径。
调用 `build_command_selection_template` 组装当前阶段需要的领域对象，并把结果记为 该调用返回的结果；计算使用固定配置或常量值，并保存为 当前处理结果中的对应字段中的对应字段中的对应字段；将处理结果写入输入内容的路径指定的文件；读取当前处理结果，并保存为 复现流程状态中的对应字段。
把新的处理结果追加或合并到复现流程状态；调用 `build_command_selection_template` 组装当前阶段需要的领域对象，并把结果记为 结构化响应；计算使用固定配置或常量值，并保存为 结构化响应中的对应字段。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”中调用 `command_selection_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段等于1；不满足就终止当前测试或流程；断言辅助操作“将外部表示解析为结构化内容”的结果等于辅助操作“调用 `build_command_selection_template` 组装当前阶段需要的领域对象”的结果；不满足就终止当前测试或流程；构造临时集合、映射或轻量领域对象，并把结果记为 该调用返回的结果；断言当前处理结果 的长度等于1；不满足就终止当前测试或流程。
断言辅助操作“将外部表示解析为结构化内容”的结果等于当前处理结果；不满足就终止当前测试或流程。
```

#### `test_command_selection_rejects_stale_response_hash`

- **源码**：`tests/test_command_selection_node.py:293`
- **签名**：`def test_command_selection_rejects_stale_response_hash(run_state: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化顺序集合，并保存为 当前集合；计算按字段初始化键值映射，并保存为 过期响应；调用 `_prepare` 完成该函数的一项辅助处理，并把结果记为 复现流程状态。
进入上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”，退出时自动清理资源：
    在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `command_selection_node` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_action_builder_uses_selected_index_from_edited_run_commands`

- **源码**：`tests/test_command_selection_node.py:325`
- **签名**：`def test_action_builder_uses_selected_index_from_edited_run_commands(tmp_path: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
加载这一步需要的外部依赖；计算组合或计算已有值，并保存为 代码仓库；计算组合或计算已有值，并保存为 Python 模块集合；创建Python 模块集合对应的目录。
构造 `ExecutionProfile` 结构化领域对象，并把结果记为 MCP Client 配置档案；计算按字段初始化键值映射，并保存为 复现流程状态。
在上下文“调用 `patch` 完成该函数的一项辅助处理”中调用 `action_builder_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段中的对应字段等于'python'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于['setup.py', 'install']；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段有值或为真；不满足就终止当前测试或流程。
```

### `tests/test_durable_checkpoint_resume.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `review_node`

- **源码**：`tests/test_durable_checkpoint_resume.py:17`
- **签名**：`def review_node(state: ReviewState) -> ReviewState`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终标注为 `ReviewState` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReviewState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`ReviewState`
- **语义**：返回 `ReviewState` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
调用 `interrupt` 完成该函数的一项辅助处理，并把结果记为 结构化响应。
如果“计算数量、边界或类型判断结果”后得到肯定结果，就从结构化响应读取所需的状态或领域记录，并把结果记为 人工决策结果；否则调用 `str` 完成该函数的一项辅助处理，并把结果记为 人工决策结果。
返回包含 `decision` 字段的结构化映射。
```

#### `finish_node`

- **源码**：`tests/test_durable_checkpoint_resume.py:26`
- **签名**：`def finish_node(state: ReviewState) -> ReviewState`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终标注为 `ReviewState` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `ReviewState` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`ReviewState`
- **语义**：返回 `ReviewState` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
如果辅助操作“从复现流程状态读取所需的状态或领域记录”的结果等于'approved'，就返回包含 `result` 字段的结构化映射。
返回包含 `result` 字段的结构化映射。
```

#### `build_test_graph`

- **源码**：`tests/test_durable_checkpoint_resume.py:31`
- **签名**：`def build_test_graph(db_path: Path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前处理结果的路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `db_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
调用 `connect` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；构造 `SqliteSaver` 结构化领域对象，并把结果记为 记忆；构造 `StateGraph` 结构化领域对象，并把结果记为 领域对象构造器；调用 `add_node` 完成该函数的一项辅助处理。
调用 `add_node` 完成该函数的一项辅助处理；调用 `add_edge` 完成该函数的一项辅助处理；调用 `add_edge` 完成该函数的一项辅助处理；调用 `add_edge` 完成该函数的一项辅助处理。
调用 `compile` 完成该函数的一项辅助处理，并把结果记为 复现流程图；返回当前构造的顺序或去重集合。
```

#### `test_sqlite_checkpoint_supports_resume_across_graph_instances`

- **源码**：`tests/test_durable_checkpoint_resume.py:45`
- **签名**：`def test_sqlite_checkpoint_supports_resume_across_graph_instances(tmp_path: Path) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果的路径；计算按字段初始化键值映射，并保存为 运行配置；调用 `build_test_graph` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
先尝试完成以下处理：
    调用当前处理结果完成模型或 Runnable 处理。
无论成功还是失败，最后都要：
    关闭当前处理结果并释放相关资源。
调用 `build_test_graph` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果。
先尝试完成以下处理：
    调用当前处理结果完成模型或 Runnable 处理，并把结果记为 阶段处理结果。
无论成功还是失败，最后都要：
    关闭当前处理结果并释放相关资源。
断言阶段处理结果中的对应字段等于'approved'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'done'；不满足就终止当前测试或流程。
```

### `tests/test_execution_cancellation.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_external_cancel_request_stops_supervisor`

- **源码**：`tests/test_execution_cancellation.py:20`
- **签名**：`def test_external_cancel_request_stops_supervisor(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果的目录；计算组合或计算已有值，并保存为 本次复现运行目录；计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现运行目录对应的目录。
创建本次复现工作区对应的目录；调用 `setattr` 完成该函数的一项辅助处理；构造 `SupervisedExecutionRequest` 结构化领域对象，并把结果记为 业务请求；将 当前处理结果 初始化为空映射，用来收集后续结果。
定义内部辅助函数 `run`，供当前函数在后续步骤中调用。
构造 `Thread` 结构化领域对象，并把结果记为 该调用返回的结果；调用 `start` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 当前处理结果。
只要辅助操作“调用 `monotonic` 完成该函数的一项辅助处理”的结果小于当前处理结果，就重复以下处理：
    遍历并筛选输入，将整理后的结果保存为 当前处理结果。
    如果当前处理结果有值或为真，就立即结束当前循环。
    调用 `sleep` 完成该函数的一项辅助处理。
循环正常结束后：
    拒绝继续处理并抛出 `AssertionError`，向调用方报告输入或运行失败。
调用 `request_run_cancellation` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `join` 完成该函数的一项辅助处理；断言“调用 `is_alive` 校验当前输入或状态”后未得到肯定结果；不满足就终止当前测试或流程；断言执行记录的 ID等于'exec_cancel'；不满足就终止当前测试或流程。
读取当前处理结果中的对应字段，并保存为 阶段处理结果；断言原因等于'cancelled'；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程；断言原因等于'test cancellation'；不满足就终止当前测试或流程。
```

#### `test_external_cancel_request_stops_supervisor.run`

- **源码**：`tests/test_execution_cancellation.py:59`
- **签名**：`def run() -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
通过辅助操作“构造 `ProcessSupervisor` 结构化领域对象”的结果执行数据查询或命令，并把结果记为 当前处理结果中的对应字段。
```

### `tests/test_execution_profile_hash.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_action`

- **源码**：`tests/test_execution_profile_hash.py:14`
- **签名**：`def _action() -> dict`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `action_id`、`action_type`、`program`、`args`、`cwd`、`source`、`reason`、`timeout_seconds` 等字段的结构化映射。
```

#### `test_action_hash_changes_when_profile_changes`

- **源码**：`tests/test_execution_profile_hash.py:31`
- **签名**：`def test_action_hash_changes_when_profile_changes() -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_action` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；调用 `deepcopy` 完成该函数的一项辅助处理，并把结果记为 发生变化的内容；计算使用固定配置或常量值，并保存为 发生变化的内容中的对应字段；断言辅助操作“调用 `compute_action_hash` 计算内容身份、分数或派生结果”的结果不等于辅助操作“调用 `compute_action_hash` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
```

#### `_profile`

- **源码**：`tests/test_execution_profile_hash.py:39`
- **签名**：`def _profile(tmp_path) -> ExecutionProfile`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ExecutionProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`ExecutionProfile`
- **语义**：返回 `ExecutionProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现工作区对应的目录；构造并返回 `ExecutionProfile` 结构化领域对象。
```

#### `test_profile_hash_changes_when_network_policy_changes`

- **源码**：`tests/test_execution_profile_hash.py:55`
- **签名**：`def test_profile_hash_changes_when_network_policy_changes(tmp_path: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 该调用返回的结果；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 发生变化的内容；断言当前处理结果不等于发生变化的内容；不满足就终止当前测试或流程。
```

#### `test_profile_hash_covers_execution_security_fields`

- **源码**：`tests/test_execution_profile_hash.py:84`
- **签名**：`def test_profile_hash_covers_execution_security_fields(tmp_path: 未显式标注, field: 未显式标注, changed_value: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、结构化对象字段、变化的值，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `field` | `未显式标注` | 结构化对象字段；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `changed_value` | `未显式标注` | 名为 `changed_value` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；复制、序列化或校验结构化领域对象，并把结果记为 发生变化的内容；断言辅助操作“调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果”的结果不等于辅助操作“调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程。
```

### `tests/test_execution_profiles.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_write_conda_profile`

- **源码**：`tests/test_execution_profiles.py:13`
- **签名**：`def _write_conda_profile(tmp_path, monkeypatch)`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于在版本、幂等键和内容 Hash 约束下保存、发布或变更复现记录和 Artifact，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现工作区对应的目录；计算组合或计算已有值，并保存为 Artifact根目录；计算组合或计算已有值，并保存为 当前处理结果。
将处理结果写入当前处理结果指定的文件；计算组合或计算已有值，并保存为 当前处理结果；创建当前处理结果对应的目录；调用 `setattr` 完成该函数的一项辅助处理。
计算组合或计算已有值，并保存为 运行配置的路径；将处理结果写入运行配置的路径指定的文件；返回运行配置的路径的当前值。
```

#### `test_load_execution_profiles`

- **源码**：`tests/test_execution_profiles.py:48`
- **签名**：`def test_load_execution_profiles(tmp_path, monkeypatch) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_write_conda_profile` 持久化或更新当前领域数据，并把结果记为 运行配置的路径；调用 `load_execution_profiles` 读取或查询当前阶段需要的数据，并把结果记为 MCP Client 配置档案集合；断言辅助操作“构造临时集合、映射或轻量领域对象”的结果等于{'paper-conda'}；不满足就终止当前测试或流程；断言模型或检索后端等于'conda'；不满足就终止当前测试或流程。
断言根目录等于辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程。
```

#### `test_profile_fingerprint_changes_with_environment`

- **源码**：`tests/test_execution_profiles.py:60`
- **签名**：`def test_profile_fingerprint_changes_with_environment(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_write_conda_profile` 持久化或更新当前领域数据，并把结果记为 运行配置的路径；读取前一步操作返回对象中的对应字段，并保存为 MCP Client 配置档案；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 该调用返回的结果；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 发生变化的内容。
断言当前处理结果不等于发生变化的内容；不满足就终止当前测试或流程。
```

#### `test_profile_loader_rejects_sensitive_environment`

- **源码**：`tests/test_execution_profiles.py:75`
- **签名**：`def test_profile_loader_rejects_sensitive_environment(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现工作区对应的目录；调用 `setattr` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 文件或目录路径。
将处理结果写入文件或目录路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_execution_profiles` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

#### `test_profile_loader_rejects_artifact_root_escape`

- **源码**：`tests/test_execution_profiles.py:107`
- **签名**：`def test_profile_loader_rejects_artifact_root_escape(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果；计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现工作区对应的目录；调用 `setattr` 完成该函数的一项辅助处理。
计算组合或计算已有值，并保存为 文件或目录路径；将处理结果写入文件或目录路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `load_execution_profiles` 读取或查询当前阶段需要的数据，退出时自动清理资源。
```

### `tests/test_execution_runners.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_profile`

- **源码**：`tests/test_execution_runners.py:13`
- **签名**：`def _profile(tmp_path) -> tuple[ExecutionProfile, str]`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`tuple[ExecutionProfile, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现工作区对应的目录；读取前一步操作返回对象的对象名称，并保存为 待启动实验程序；构造 `ExecutionProfile` 结构化领域对象，并把结果记为 MCP Client 配置档案。
返回当前构造的顺序或去重集合。
```

#### `_action`

- **源码**：`tests/test_execution_runners.py:30`
- **签名**：`def _action(profile: ExecutionProfile, program: str, cwd: str) -> dict`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收MCP Client 配置档案、待启动实验程序、命令执行工作目录，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |
| `program` | `str` | 待启动的程序名或可执行文件路径；是否允许运行由执行策略决定。 |
| `cwd` | `str` | 命令执行时的当前工作目录；它是受控的文件系统目录路径，不是命令文本。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并返回处理结果。
```

#### `test_local_runner_executes_inside_workspace`

- **源码**：`tests/test_execution_runners.py:49`
- **签名**：`def test_local_runner_executes_inside_workspace(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；将处理结果写入当前输入内容指定的文件；计算组合或计算已有值，并保存为 当前处理结果的目录；计算组合或计算已有值，并保存为 本次复现运行目录。
创建本次复现运行目录对应的目录；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；调用 `run` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
断言阶段处理结果中的对应字段是真；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'exited'；不满足就终止当前测试或流程；断言辅助操作“对阶段处理结果中的对应字段中的文本执行规范化或拆分”的结果等于根目录；不满足就终止当前测试或流程；断言“检查辅助操作“把外部位置解析为文件系统路径对象”的结果的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_local_runner_rejects_cwd_outside_workspace`

- **源码**：`tests/test_execution_runners.py:76`
- **签名**：`def test_local_runner_rejects_cwd_outside_workspace(tmp_path) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算组合或计算已有值，并保存为 当前处理结果；创建当前处理结果对应的目录。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `run` 完成该函数的一项辅助处理，退出时自动清理资源。
```

### `tests/test_execution_verifier_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_action`

- **源码**：`tests/test_execution_verifier_node.py:10`
- **签名**：`def _action() -> ExecutableAction`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ExecutableAction` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`ExecutableAction`
- **语义**：返回 `ExecutableAction` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ExecutableAction` 结构化领域对象。
```

#### `_result`

- **源码**：`tests/test_execution_verifier_node.py:23`
- **签名**：`def _result(*, ok: bool) -> ExecutionResult`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收处理是否成功的判断，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `ok` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`ExecutionResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
构造并返回 `ExecutionResult` 结构化领域对象。
```

#### `_state`

- **源码**：`tests/test_execution_verifier_node.py:36`
- **签名**：`def _state(run_state: dict, *, ok: bool) -> dict`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态、处理是否成功的判断，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `dict` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `ok` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
调用 `_action` 完成该函数的一项辅助处理，并把结果记为 待执行复现动作；调用 `_result` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；调用 `build_execution_evidence` 组装当前阶段需要的领域对象，并把结果记为 可追溯证据记录；返回包含 `pending_action`、`user_approval`、`execution_result`、`execution_evidence`、`last_action_result` 字段的结构化映射。
```

#### `test_execution_verifier_projects_success`

- **源码**：`tests/test_execution_verifier_node.py:56`
- **签名**：`def test_execution_verifier_projects_success(run_state) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `execution_verifier_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段等于'succeeded'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'verified'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'execution_protocol'；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段中的对应字段等于'succeeded'；不满足就终止当前测试或流程。
```

#### `test_execution_verifier_classifies_nonzero_exit`

- **源码**：`tests/test_execution_verifier_node.py:73`
- **签名**：`def test_execution_verifier_classifies_nonzero_exit(run_state: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `execution_verifier_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段等于'failed'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'failed'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'paper_program'；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段中的对应字段是假；不满足就终止当前测试或流程。
```

#### `test_execution_verifier_fails_closed_on_tampering`

- **源码**：`tests/test_execution_verifier_node.py:90`
- **签名**：`def test_execution_verifier_fails_closed_on_tampering(run_state: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_state` 完成该函数的一项辅助处理，并把结果记为 复现流程状态；计算使用固定配置或常量值，并保存为 复现流程状态中的对应字段中的对应字段；调用 `execution_verifier_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段等于'agent_failed'；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段中的对应字段等于'inconclusive'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段是真；不满足就终止当前测试或流程。
```

#### `test_execution_verifier_rejects_stale_approval`

- **源码**：`tests/test_execution_verifier_node.py:105`
- **签名**：`def test_execution_verifier_rejects_stale_approval(run_state: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_state` 完成该函数的一项辅助处理，并把结果记为 复现流程状态；计算使用固定配置或常量值，并保存为 复现流程状态中的对应字段；计算按字段初始化键值映射，并保存为 复现流程状态中的对应字段；调用 `execution_verifier_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果。
断言阶段处理结果中的对应字段等于'agent_failed'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'inconclusive'；不满足就终止当前测试或流程；遍历并筛选输入，将整理后的结果保存为 校验项集合；断言校验项集合中的对应字段是假；不满足就终止当前测试或流程。
```

### `tests/test_executor_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_build_pending_action`

- **源码**：`tests/test_executor_node.py:14`
- **签名**：`def _build_pending_action() -> dict`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `action_id`、`action_type`、`program`、`args`、`cwd`、`reason`、`source`、`timeout_seconds` 等字段的结构化映射。
```

#### `_build_approval_record`

- **源码**：`tests/test_executor_node.py:32`
- **签名**：`def _build_approval_record(action: dict) -> dict`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收待执行复现动作，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `action` | `dict` | 结构化待执行动作；包含命令、工作目录、风险和内容身份，但尚不表示已执行。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `approval_id`、`action_id`、`action_hash`、`decision`、`reviewer`、`risk_level`、`reviewed_at`、`comment` 字段的结构化映射。
```

#### `_supervisor_result`

- **源码**：`tests/test_executor_node.py:45`
- **签名**：`def _supervisor_result(run_state: 未显式标注, ok: bool, end_reason: str) -> dict`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态、处理是否成功的判断、原因，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `ok` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `end_reason` | `str` | 名为 `end_reason` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'exited' |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
计算组合或计算已有值，并保存为 尝试；创建尝试对应的目录；计算组合或计算已有值，并保存为 进程标准输出的路径；计算组合或计算已有值，并保存为 进程标准错误的路径。
计算组合或计算已有值，并保存为 当前处理结果的路径；计算组合或计算已有值，并保存为 领域记录的路径；将处理结果写入进程标准输出的路径指定的文件；将处理结果写入进程标准错误的路径指定的文件。
将处理结果写入当前处理结果的路径指定的文件；将处理结果写入领域记录的路径指定的文件；返回包含 `ok`、`returncode`、`end_reason`、`stdout`、`stderr`、`combined_output`、`timeout`、`cancelled` 等字段的结构化映射。
```

#### `test_executor_runs_command_when_approved`

- **源码**：`tests/test_executor_node.py:96`
- **签名**：`def test_executor_runs_command_when_approved(run_state) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_pending_action` 组装当前阶段需要的领域对象，并把结果记为 待审批复现动作；计算按字段初始化键值映射，并保存为 复现流程状态；调用 `_supervisor_result` 完成该函数的一项辅助处理，并把结果记为 测试替身结果。
在上下文“调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给运行”中调用 `executor_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
复制、序列化或校验结构化领域对象，并把结果记为 期望；调用 `assert_called_once_with` 完成该函数的一项辅助处理；断言当前输入内容不属于阶段处理结果；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段是真；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段有值或为真；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于测试替身结果中的对应字段；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'exec-test'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'evidence_recorded'；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段中的对应字段等于'exited'；不满足就终止当前测试或流程；断言当前输入内容 的长度等于5；不满足就终止当前测试或流程；断言当前输入内容不属于阶段处理结果；不满足就终止当前测试或流程。
```

#### `test_executor_does_not_run_when_rejected`

- **源码**：`tests/test_executor_node.py:139`
- **签名**：`def test_executor_does_not_run_when_rejected(run_state) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_pending_action` 组装当前阶段需要的领域对象，并把结果记为 待审批复现动作；计算按字段初始化键值映射，并保存为 复现流程状态。
在上下文“调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给运行”中调用 `executor_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
调用 `assert_not_called` 完成该函数的一项辅助处理；断言阶段处理结果中的对应字段等于'rejected'；不满足就终止当前测试或流程。
```

#### `test_executor_does_not_run_when_revise_requested`

- **源码**：`tests/test_executor_node.py:153`
- **签名**：`def test_executor_does_not_run_when_revise_requested(run_state) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_pending_action` 组装当前阶段需要的领域对象，并把结果记为 待审批复现动作；计算按字段初始化键值映射，并保存为 复现流程状态。
在上下文“调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给运行”中调用 `executor_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
调用 `assert_not_called` 完成该函数的一项辅助处理；断言阶段处理结果中的对应字段等于'revise_requested'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'请先缩小 batch size'；不满足就终止当前测试或流程。
```

#### `test_executor_classifies_nonzero_exit_and_sets_log_path`

- **源码**：`tests/test_executor_node.py:169`
- **签名**：`def test_executor_classifies_nonzero_exit_and_sets_log_path(run_state: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_build_pending_action` 组装当前阶段需要的领域对象，并把结果记为 待审批复现动作；计算按字段初始化键值映射，并保存为 复现流程状态；调用 `_supervisor_result` 完成该函数的一项辅助处理，并把结果记为 测试替身结果。
在上下文“调用 `patch` 完成该函数的一项辅助处理”中调用 `executor_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言当前输入内容不属于阶段处理结果；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于1；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于1；不满足就终止当前测试或流程；断言当前输入内容不属于阶段处理结果；不满足就终止当前测试或流程。
```

#### `test_execution_end_reason_classification`

- **源码**：`tests/test_executor_node.py:206`
- **签名**：`def test_execution_end_reason_classification(reason: 未显式标注, category: 未显式标注, terminal: 未显式标注, final_status: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收基线接受或运行操作原因、评测类别、流程是否已进入终止状态的判断、状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `reason` | `未显式标注` | 来源、类别、用途、后端、状态或操作原因等控制字段；通常对应有限的业务枚举或审计文本。 |
| `category` | `未显式标注` | 评测类别；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `terminal` | `未显式标注` | 流程是否已进入终止状态的判断；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `final_status` | `未显式标注` | 名为 `final_status` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_execution_stage_error` 组装当前阶段需要的领域对象，并把结果记为 多个解包结果；断言评测类别等于评测类别；不满足就终止当前测试或流程；断言流程是否已进入终止状态的判断是流程是否已进入终止状态的判断；不满足就终止当前测试或流程；断言当前状态等于状态；不满足就终止当前测试或流程。
```

### `tests/test_fail_to_debug_flow.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_route_after_new_executor_requires_verifier`

- **源码**：`tests/test_fail_to_debug_flow.py:9`
- **签名**：`def test_route_after_new_executor_requires_verifier() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；断言辅助操作“调用 `route_after_executor` 完成该函数的一项辅助处理”的结果等于'execution_verifier'；不满足就终止当前测试或流程。
```

#### `test_route_after_verifier_debugs_verified_failure`

- **源码**：`tests/test_fail_to_debug_flow.py:18`
- **签名**：`def test_route_after_verifier_debugs_verified_failure() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；断言辅助操作“调用 `route_after_execution_verifier` 完成该函数的一项辅助处理”的结果等于'log_debug'；不满足就终止当前测试或流程。
```

#### `test_route_after_verifier_finishes_verified_success`

- **源码**：`tests/test_fail_to_debug_flow.py:27`
- **签名**：`def test_route_after_verifier_finishes_verified_success() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；断言辅助操作“调用 `route_after_execution_verifier` 完成该函数的一项辅助处理”的结果等于'final_report'；不满足就终止当前测试或流程。
```

#### `test_legacy_checkpoint_failed_with_log_goes_to_debug`

- **源码**：`tests/test_fail_to_debug_flow.py:35`
- **签名**：`def test_legacy_checkpoint_failed_with_log_goes_to_debug() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；调用 `route_after_executor` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果等于'log_debug'；不满足就终止当前测试或流程。
```

#### `test_legacy_checkpoint_succeeded_goes_to_final_report`

- **源码**：`tests/test_fail_to_debug_flow.py:46`
- **签名**：`def test_legacy_checkpoint_succeeded_goes_to_final_report() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；调用 `route_after_executor` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果等于'final_report'；不满足就终止当前测试或流程。
```

#### `test_legacy_checkpoint_failed_no_log_goes_to_final_report`

- **源码**：`tests/test_fail_to_debug_flow.py:57`
- **签名**：`def test_legacy_checkpoint_failed_no_log_goes_to_final_report() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；调用 `route_after_executor` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果等于'final_report'；不满足就终止当前测试或流程。
```

### `tests/test_failed_run_manifest.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_failed_run_still_has_error_final_and_manifest`

- **源码**：`tests/test_failed_run_manifest.py:18`
- **签名**：`def test_failed_run_still_has_error_final_and_manifest(run_state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_stage_error` 组装当前阶段需要的领域对象，并把结果记为 错误信息；计算按字段初始化键值映射，并保存为 复现流程状态；把新的处理结果追加或合并到复现流程状态；把新的处理结果追加或合并到复现流程状态。
把外部位置解析为文件系统路径对象，并把结果记为 本次复现运行目录；断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；将外部表示解析为结构化内容，并把结果记为 运行或工作区 Manifest；断言运行或工作区 Manifest中的对应字段等于'invalid_input'；不满足就终止当前测试或流程。
断言运行或工作区 Manifest中的对应字段中的对应字段等于1；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足““调用 `is_relative_to` 校验当前输入或状态”后得到肯定结果”的项；不满足就终止当前测试或流程。
```

#### `test_manifest_records_tampered_artifact_and_still_writes`

- **源码**：`tests/test_failed_run_manifest.py:58`
- **签名**：`def test_manifest_records_tampered_artifact_and_still_writes(run_state: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 复现流程状态；将处理结果写入文件或目录路径指定的文件；执行 `run_manifest_node` 对应的阶段流程并取得状态结果，并把结果记为 阶段处理结果。
把外部位置解析为文件系统路径对象，并把结果记为 运行或工作区 Manifest的路径；断言“检查运行或工作区 Manifest的路径的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'agent_failed'；不满足就终止当前测试或流程；断言当前可迭代输入中存在满足“当前处理项中的对应字段等于'ARTIFACT_HASH_MISMATCH'”的项；不满足就终止当前测试或流程。
将外部表示解析为结构化内容，并把结果记为 运行或工作区 Manifest；调用 `next` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；断言当前处理结果中的对应字段等于'hash_mismatch'；不满足就终止当前测试或流程。
```

### `tests/test_file_repair_planner_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_make_state`

- **源码**：`tests/test_file_repair_planner_node.py:12`
- **签名**：`def _make_state(tmp_path) -> tuple[dict, str, str]`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终有界、排序或带证据来源的结果集合。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`tuple[dict, str, str]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库；计算组合或计算已有值，并保存为 测试文件；计算组合或计算已有值，并保存为 来源文件；创建父级目录或父领域对象对应的目录。
计算使用固定配置或常量值，并保存为 数据来源标记的文本；计算使用固定配置或常量值，并保存为 测试的文本；将处理结果写入来源文件指定的文件；将处理结果写入测试文件指定的文件。
计算组合或计算已有值，并保存为 运行日志路径；将处理结果写入运行日志路径指定的文件；计算按字段初始化键值映射，并保存为 复现流程状态；返回当前构造的顺序或去重集合。
```

#### `_invocation`

- **源码**：`tests/test_file_repair_planner_node.py:63`
- **签名**：`def _invocation(proposal: FileRepairProposal) -> StructuredInvocationResult`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收修复或重跑提案，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终经过 Schema 校验、可继续审计的领域结果对象。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `proposal` | `FileRepairProposal` | 修复或重跑提案；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`StructuredInvocationResult`
- **语义**：返回结构化响应/结果对象，字段语义由对应 Pydantic Schema 定义。

**伪代码**

```text
构造并返回 `StructuredInvocationResult` 结构化领域对象。
```

#### `test_file_repair_adds_pytest_target_from_pending_action`

- **源码**：`tests/test_file_repair_planner_node.py:73`
- **签名**：`def test_file_repair_adds_pytest_target_from_pending_action(tmp_path: 未显式标注, run_state: 未显式标注, monkeypatch: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、本次运行状态、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_make_state` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 复现流程状态；构造 `FileRepairProposal` 结构化领域对象，并把结果记为 修复或重跑提案；调用 `setattr` 完成该函数的一项辅助处理。
调用 `setattr` 完成该函数的一项辅助处理；构造 `ScriptedModelGateway` 结构化领域对象，并把结果记为 外部服务网关。
在上下文“调用 `patch` 完成该函数的一项辅助处理”中调用 `file_repair_planner_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段中的对应字段等于'patch'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于['tests/test_phase14_demo.py']；不满足就终止当前测试或流程。
```

#### `test_file_repair_rejects_test_file_edit`

- **源码**：`tests/test_file_repair_planner_node.py:120`
- **签名**：`def test_file_repair_rejects_test_file_edit(tmp_path: 未显式标注, run_state: 未显式标注, monkeypatch: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、本次运行状态、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_make_state` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 复现流程状态；构造 `FileRepairProposal` 结构化领域对象，并把结果记为 修复或重跑提案；调用 `setattr` 完成该函数的一项辅助处理。
调用 `setattr` 完成该函数的一项辅助处理；构造 `ScriptedModelGateway` 结构化领域对象，并把结果记为 外部服务网关。
在上下文“调用 `patch` 完成该函数的一项辅助处理”中调用 `file_repair_planner_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段中的对应字段等于'no_patch'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于[]；不满足就终止当前测试或流程；断言当前输入内容属于阶段处理结果中的对应字段中的对应字段；不满足就终止当前测试或流程。
```

### `tests/test_final_report_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_final_report_node_writes_supervision_summary`

- **源码**：`tests/test_final_report_node.py:9`
- **签名**：`def test_final_report_node_writes_supervision_summary(run_state) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 记录的路径；创建父级目录或父领域对象对应的目录；将处理结果写入记录的路径指定的文件；计算按字段初始化键值映射，并保存为 复现流程状态。
执行 `final_report_node` 对应的阶段流程并取得状态结果，并把结果记为 阶段处理结果；读取阶段处理结果中的对应字段，并保存为 MCP 评测或运行报告；断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程；断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程。
断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程；断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程；断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程；断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程。
断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程；断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程；计算组合或计算已有值，并保存为 MCP 评测或运行报告的路径；断言“检查MCP 评测或运行报告的路径的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
断言辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果属于阶段处理结果中的对应字段；不满足就终止当前测试或流程。
```

#### `test_final_report_distinguishes_user_cancellation`

- **源码**：`tests/test_final_report_node.py:105`
- **签名**：`def test_final_report_distinguishes_user_cancellation(run_state) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；读取前一步操作返回对象中的对应字段，并保存为 MCP 评测或运行报告；断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程；断言当前输入内容属于MCP 评测或运行报告；不满足就终止当前测试或流程。
```

### `tests/test_input_validation_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_profile`

- **源码**：`tests/test_input_validation_node.py:9`
- **签名**：`def _profile(workspace: Path) -> ExecutionProfile`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次复现工作区，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ExecutionProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `workspace` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |

**输出**

- **Python 类型**：`ExecutionProfile`
- **语义**：返回 `ExecutionProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ExecutionProfile` 结构化领域对象。
```

#### `test_input_validation_accepts_valid_inputs`

- **源码**：`tests/test_input_validation_node.py:19`
- **签名**：`def test_input_validation_accepts_valid_inputs(run_state: 未显式标注, tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态、临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 论文；将处理结果写入论文指定的文件；计算组合或计算已有值，并保存为 代码仓库；创建代码仓库对应的目录。
调用 `setattr` 完成该函数的一项辅助处理；计算按字段初始化键值映射，并保存为 复现流程状态；调用 `input_validation_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段是真；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段中的对应字段是真；不满足就终止当前测试或流程；断言“从阶段处理结果读取所需的状态或领域记录”后未得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_missing_paper_becomes_user_stage_error`

- **源码**：`tests/test_input_validation_node.py:47`
- **签名**：`def test_missing_paper_becomes_user_stage_error(run_state: 未显式标注, tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态、临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库；创建代码仓库对应的目录；计算组合或计算已有值，并保存为 论文；调用 `setattr` 完成该函数的一项辅助处理。
计算按字段初始化键值映射，并保存为 复现流程状态；调用 `input_validation_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段是假；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'invalid_input'；不满足就终止当前测试或流程。
断言当前可迭代输入中存在满足“当前处理项中的对应字段等于'INPUT_NOT_FOUND' 且 当前处理项中的对应字段等于'user'”的项；不满足就终止当前测试或流程。
```

#### `test_repo_outside_profile_workspace_is_blocked`

- **源码**：`tests/test_input_validation_node.py:78`
- **签名**：`def test_repo_outside_profile_workspace_is_blocked(run_state: 未显式标注, tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态、临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 论文；将处理结果写入论文指定的文件；计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现工作区对应的目录。
计算组合或计算已有值，并保存为 仓库；创建仓库对应的目录；调用 `setattr` 完成该函数的一项辅助处理；计算按字段初始化键值映射，并保存为 复现流程状态。
调用 `input_validation_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段是假；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'environment_blocked'；不满足就终止当前测试或流程；断言当前可迭代输入中存在满足“当前处理项中的对应字段等于'REPO_OUTSIDE_PROFILE_WORKSPACE'”的项；不满足就终止当前测试或流程。
```

### `tests/test_manual_cli_execution_profiles.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_test_profile`

- **源码**：`tests/test_manual_cli_execution_profiles.py:10`
- **签名**：`def _test_profile() -> ExecutionProfile`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终标注为 `ExecutionProfile` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`ExecutionProfile`
- **语义**：返回 `ExecutionProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ExecutionProfile` 结构化领域对象。
```

#### `test_run_smoke_binds_action_to_execution_profile`

- **源码**：`tests/test_manual_cli_execution_profiles.py:21`
- **签名**：`def test_run_smoke_binds_action_to_execution_profile() -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_test_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；计算按字段初始化键值映射，并保存为 测试替身结果。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果、调用 `patch` 完成该函数的一项辅助处理”中调用 `run_smoke` 完成该函数的一项辅助处理，退出时自动清理资源。
读取命令行或函数位置参数集合中的对应字段，并保存为 复现流程状态；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 期望指纹；断言复现流程状态中的对应字段等于MCP Client 配置档案 ID；不满足就终止当前测试或流程；断言复现流程状态中的对应字段等于期望指纹；不满足就终止当前测试或流程。
断言复现流程状态中的对应字段中的对应字段等于MCP Client 配置档案 ID；不满足就终止当前测试或流程；断言复现流程状态中的对应字段中的对应字段等于期望指纹；不满足就终止当前测试或流程。
```

#### `test_plan_repair_binds_action_to_execution_profile`

- **源码**：`tests/test_manual_cli_execution_profiles.py:52`
- **签名**：`def test_plan_repair_binds_action_to_execution_profile(tmp_path) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_test_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；计算组合或计算已有值，并保存为 运行日志路径；将处理结果写入运行日志路径指定的文件。
在上下文“调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果、调用 `patch` 完成该函数的一项辅助处理、调用 `patch` 完成该函数的一项辅助处理”中调用 `plan_repair` 完成该函数的一项辅助处理，退出时自动清理资源。
读取命令行或函数位置参数集合中的对应字段，并保存为 复现流程状态；调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果，并把结果记为 期望指纹；断言复现流程状态中的对应字段等于MCP Client 配置档案 ID；不满足就终止当前测试或流程；断言复现流程状态中的对应字段中的对应字段等于MCP Client 配置档案 ID；不满足就终止当前测试或流程。
断言复现流程状态中的对应字段中的对应字段等于期望指纹；不满足就终止当前测试或流程。
```

### `tests/test_minimal_execution_environment.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_NullSecretService.resolve`

- **源码**：`tests/test_minimal_execution_environment.py:13`
- **签名**：`def resolve(self, *, reference, use, actor)`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收论文或源码引用证据、当前处理结果、审计主体，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `self` | `未显式标注` | 当前类实例，保存该方法需要的 Repository、配置或运行依赖。 |
| `reference` | `未显式标注` | 论文或源码引用证据；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `use` | `未显式标注` | 名为 `use` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `actor` | `未显式标注` | 执行或决策操作的审计主体标识，不是授权凭证本身。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `_profile`

- **源码**：`tests/test_minimal_execution_environment.py:17`
- **签名**：`def _profile(tmp_path) -> ExecutionProfile`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ExecutionProfile` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`ExecutionProfile`
- **语义**：返回 `ExecutionProfile` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现工作区；创建本次复现工作区对应的目录；构造并返回 `ExecutionProfile` 结构化领域对象。
```

#### `_action`

- **源码**：`tests/test_minimal_execution_environment.py:32`
- **签名**：`def _action(profile: ExecutionProfile) -> ExecutableAction`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收MCP Client 配置档案，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `ExecutableAction` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `profile` | `ExecutionProfile` | 运行/执行环境配置或 profile 标识；描述能力和限制，不是一次执行的结果。 |

**输出**

- **Python 类型**：`ExecutableAction`
- **语义**：返回 `ExecutableAction` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `ExecutableAction` 结构化领域对象。
```

#### `test_minimal_env_does_not_inherit_agent_secret`

- **源码**：`tests/test_minimal_execution_environment.py:47`
- **签名**：`def test_minimal_env_does_not_inherit_agent_secret(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；调用 `_action` 完成该函数的一项辅助处理，并把结果记为 待执行复现动作；计算组合或计算已有值，并保存为 当前处理结果的目录；计算组合或计算已有值，并保存为 本次复现运行目录。
创建本次复现运行目录对应的目录；调用 `setattr` 完成该函数的一项辅助处理；调用 `setenv` 完成该函数的一项辅助处理；调用 `build_minimal_environment` 组装当前阶段需要的领域对象，并把结果记为 阶段处理结果。
断言当前输入内容不属于进程环境变量映射；不满足就终止当前测试或流程；断言进程环境变量映射中的对应字段等于'2'；不满足就终止当前测试或流程；断言“检查进程环境变量映射中的对应字段是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_action_cannot_override_unapproved_env`

- **源码**：`tests/test_minimal_execution_environment.py:73`
- **签名**：`def test_action_cannot_override_unapproved_env(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_profile` 完成该函数的一项辅助处理，并把结果记为 MCP Client 配置档案；复制、序列化或校验结构化领域对象，并把结果记为 待执行复现动作；计算组合或计算已有值，并保存为 当前处理结果的目录；计算组合或计算已有值，并保存为 本次复现运行目录。
创建本次复现运行目录对应的目录；调用 `setattr` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `build_minimal_environment` 组装当前阶段需要的领域对象，退出时自动清理资源。
```

### `tests/test_patch_application_recovery.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_replay_is_idempotent_at_every_fault_point`

- **源码**：`tests/test_patch_application_recovery.py:26`
- **签名**：`def test_replay_is_idempotent_at_every_fault_point(patch_bundle: 未显式标注, fault_point: 未显式标注, state_after_crash: 未显式标注, recovered: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码修复补丁包、当前处理结果、状态、当前处理结果，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `fault_point` | `未显式标注` | 名为 `fault_point` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `state_after_crash` | `未显式标注` | 名为 `state_after_crash` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `recovered` | `未显式标注` | 名为 `recovered` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
定义内部辅助函数 `crash`，供当前函数在后续步骤中调用。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `apply_verified_patch_to_source` 完成该函数的一项辅助处理，退出时自动清理资源。
断言辅助操作“调用 `inspect_source_patch_state` 完成该函数的一项辅助处理”的结果等于状态；不满足就终止当前测试或流程；调用 `apply_verified_patch_to_source` 完成该函数的一项辅助处理，并把结果记为 重放的；断言当前状态等于'applied'；不满足就终止当前测试或流程；断言当前处理结果是当前处理结果；不满足就终止当前测试或流程。
断言辅助操作“调用 `inspect_source_patch_state` 完成该函数的一项辅助处理”的结果等于'after'；不满足就终止当前测试或流程。
```

#### `test_replay_is_idempotent_at_every_fault_point.crash`

- **源码**：`tests/test_patch_application_recovery.py:32`
- **签名**：`def crash(point: str) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `point` | `str` | 名为 `point` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
如果当前处理结果等于当前处理结果，就拒绝继续处理并抛出 `SimulatedProcessCrash`，向调用方报告输入或运行失败。
```

#### `test_extra_tracked_change_requires_manual_intervention`

- **源码**：`tests/test_patch_application_recovery.py:54`
- **签名**：`def test_extra_tracked_change_requires_manual_intervention(patch_bundle: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码修复补丁包，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果的路径；将处理结果写入当前处理结果的路径指定的文件；调用 `apply_verified_patch_to_source` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前状态等于'manual_intervention'；不满足就终止当前测试或流程。
断言辅助操作“读取当前处理结果的路径中的文件内容”的结果等于文本（19 个字符）；不满足就终止当前测试或流程；断言辅助操作“调用 `inspect_source_patch_state` 完成该函数的一项辅助处理”的结果等于'conflict'；不满足就终止当前测试或流程。
```

### `tests/test_patch_authorization_boundaries.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_tampering_any_report_field_invalidates_hash`

- **源码**：`tests/test_patch_authorization_boundaries.py:14`
- **签名**：`def test_tampering_any_report_field_invalidates_hash(valid_report)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前处理结果，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `valid_report` | `未显式标注` | 名为 `valid_report` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_verification_hash` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_embedded_hash_is_recomputed`

- **源码**：`tests/test_patch_authorization_boundaries.py:20`
- **签名**：`def test_embedded_hash_is_recomputed(valid_report)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前处理结果，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `valid_report` | `未显式标注` | 名为 `valid_report` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
复制、序列化或校验结构化领域对象，并把结果记为 该调用返回的结果；调用 `compute_verification_hash` 计算内容身份、分数或派生结果，并把结果记为 期望值；复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告；断言辅助操作“调用 `validate_verification_hash` 校验当前输入或状态”的结果等于期望值；不满足就终止当前测试或流程。
```

#### `_authorization_inputs`

- **源码**：`tests/test_patch_authorization_boundaries.py:31`
- **签名**：`def _authorization_inputs(valid_report, patch_bundle)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，让 bundle、report、promotion 和 state 指向同一身份。该函数接收当前处理结果、代码修复补丁包，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `未显式标注（存在 return）` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `valid_report` | `未显式标注` | 名为 `valid_report` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`未显式标注（存在 return）`
- **语义**：源码未声明返回类型；按各个 `return` 分支返回运行时领域对象，失败通过异常表示。

**伪代码**

```text
读取代码修复补丁包，并保存为 代码仓库归档包；构造 `PatchPromotionRecord` 结构化领域对象，并把结果记为 该调用返回的结果；计算按字段初始化键值映射，并保存为 复现流程状态；返回当前构造的顺序或去重集合。
```

#### `_trust_current_fixture_profile`

- **源码**：`tests/test_patch_authorization_boundaries.py:58`
- **签名**：`def _trust_current_fixture_profile(monkeypatch, valid_report)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，隔离 profile store，只测试 authorization 绑定逻辑。该函数接收测试环境修改工具、当前处理结果，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |
| `valid_report` | `未显式标注` | 名为 `valid_report` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理。
```

#### `test_report_mismatch_blocks_authorization`

- **源码**：`tests/test_patch_authorization_boundaries.py:90`
- **签名**：`def test_report_mismatch_blocks_authorization(monkeypatch: 未显式标注, valid_report: 未显式标注, patch_bundle: 未显式标注, report_updates: 未显式标注, message: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收测试环境修改工具、当前处理结果、代码修复补丁包、当前处理结果等输入，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |
| `valid_report` | `未显式标注` | 名为 `valid_report` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `report_updates` | `未显式标注` | 名为 `report_updates` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `message` | `未显式标注` | 对话消息记录或消息文本；角色、顺序和内容 Hash 可能参与证据校验。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_trust_current_fixture_profile` 完成该函数的一项辅助处理；调用 `_authorization_inputs` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告；复制、序列化或校验结构化领域对象，并把结果记为 MCP 评测或运行报告。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_patch_promotion_authorization` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_old_promotion_hash_is_rejected`

- **源码**：`tests/test_patch_authorization_boundaries.py:119`
- **签名**：`def test_old_promotion_hash_is_rejected(monkeypatch: 未显式标注, valid_report: 未显式标注, patch_bundle: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收测试环境修改工具、当前处理结果、代码修复补丁包，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |
| `valid_report` | `未显式标注` | 名为 `valid_report` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_trust_current_fixture_profile` 完成该函数的一项辅助处理；调用 `_authorization_inputs` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；复制、序列化或校验结构化领域对象，并把结果记为 过期的。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_patch_promotion_authorization` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_state_profile_mismatch_is_rejected`

- **源码**：`tests/test_patch_authorization_boundaries.py:143`
- **签名**：`def test_state_profile_mismatch_is_rejected(monkeypatch: 未显式标注, valid_report: 未显式标注, patch_bundle: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收测试环境修改工具、当前处理结果、代码修复补丁包，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |
| `valid_report` | `未显式标注` | 名为 `valid_report` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_trust_current_fixture_profile` 完成该函数的一项辅助处理；调用 `_authorization_inputs` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；计算使用固定配置或常量值，并保存为 复现流程状态中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_patch_promotion_authorization` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_changed_profile_fingerprint_is_rejected`

- **源码**：`tests/test_patch_authorization_boundaries.py:165`
- **签名**：`def test_changed_profile_fingerprint_is_rejected(monkeypatch: 未显式标注, valid_report: 未显式标注, patch_bundle: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收测试环境修改工具、当前处理结果、代码修复补丁包，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |
| `valid_report` | `未显式标注` | 名为 `valid_report` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_authorization_inputs` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_patch_promotion_authorization` 校验当前输入或状态，退出时自动清理资源。
```

### `tests/test_patch_review_nodes.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_approved_patch_routes_to_verification_executor`

- **源码**：`tests/test_patch_review_nodes.py:12`
- **签名**：`def test_approved_patch_routes_to_verification_executor()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_patch_review` 完成该函数的一项辅助处理”的结果等于'patch_verification_executor'；不满足就终止当前测试或流程。
```

#### `test_rejected_patch_routes_to_final_report`

- **源码**：`tests/test_patch_review_nodes.py:18`
- **签名**：`def test_rejected_patch_routes_to_final_report()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_patch_review` 完成该函数的一项辅助处理”的结果等于'final_report'；不满足就终止当前测试或流程。
```

#### `test_patch_execution_evidence_goes_to_verdict`

- **源码**：`tests/test_patch_review_nodes.py:24`
- **签名**：`def test_patch_execution_evidence_goes_to_verdict() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_patch_verification_executor` 完成该函数的一项辅助处理”的结果等于'patch_verdict'；不满足就终止当前测试或流程。
```

#### `test_patch_verdict_goes_to_promotion_review`

- **源码**：`tests/test_patch_review_nodes.py:30`
- **签名**：`def test_patch_verdict_goes_to_promotion_review() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_patch_verdict` 完成该函数的一项辅助处理”的结果等于'patch_promotion_review'；不满足就终止当前测试或流程。
```

#### `test_only_passed_verification_routes_to_promotion_review`

- **源码**：`tests/test_patch_review_nodes.py:42`
- **签名**：`def test_only_passed_verification_routes_to_promotion_review()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_patch_verifier` 完成该函数的一项辅助处理”的结果等于'patch_promotion_review'；不满足就终止当前测试或流程；断言辅助操作“调用 `route_after_patch_verifier` 完成该函数的一项辅助处理”的结果等于'final_report'；不满足就终止当前测试或流程。
```

#### `test_structural_verification_cannot_route_to_promotion_review`

- **源码**：`tests/test_patch_review_nodes.py:57`
- **签名**：`def test_structural_verification_cannot_route_to_promotion_review()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_patch_verifier` 完成该函数的一项辅助处理”的结果等于'final_report'；不满足就终止当前测试或流程。
```

#### `test_only_approved_promotion_routes_to_apply`

- **源码**：`tests/test_patch_review_nodes.py:69`
- **签名**：`def test_only_approved_promotion_routes_to_apply()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_patch_promotion_review` 完成该函数的一项辅助处理”的结果等于'patch_apply'；不满足就终止当前测试或流程；断言辅助操作“调用 `route_after_patch_promotion_review` 完成该函数的一项辅助处理”的结果等于'final_report'；不满足就终止当前测试或流程。
```

### `tests/test_patch_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_git`

- **源码**：`tests/test_patch_tools.py:18`
- **签名**：`def _git(repo: Path, *args: str) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码仓库、命令行或函数位置参数集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `*args` | `str` | 额外位置参数序列。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前处理结果等于0，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `_make_repo`

- **源码**：`tests/test_patch_tools.py:28`
- **签名**：`def _make_repo(tmp_path: Path) -> Path`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库；创建代码仓库对应的目录；调用 `_git` 完成该函数的一项辅助处理；调用 `_git` 完成该函数的一项辅助处理。
调用 `_git` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 数据来源标记；将处理结果写入数据来源标记指定的文件；调用 `_git` 完成该函数的一项辅助处理。
调用 `_git` 完成该函数的一项辅助处理；返回代码仓库的当前值。
```

#### `_proposal`

- **源码**：`tests/test_patch_tools.py:45`
- **签名**：`def _proposal() -> FileRepairProposal`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `FileRepairProposal` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`FileRepairProposal`
- **语义**：返回 `FileRepairProposal` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `FileRepairProposal` 结构化领域对象。
```

#### `test_exact_replacement_requires_unique_old_text`

- **源码**：`tests/test_patch_tools.py:70`
- **签名**：`def test_exact_replacement_requires_unique_old_text()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `apply_exact_replacements` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_patch_path_cannot_escape_repo`

- **源码**：`tests/test_patch_tools.py:84`
- **签名**：`def test_patch_path_cannot_escape_repo(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_make_repo` 完成该函数的一项辅助处理，并把结果记为 代码仓库。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `resolve_patch_target` 解析、规范化或转换当前输入，退出时自动清理资源。
```

#### `test_patch_path_cannot_target_env`

- **源码**：`tests/test_patch_tools.py:90`
- **签名**：`def test_patch_path_cannot_target_env(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_make_repo` 完成该函数的一项辅助处理，并把结果记为 代码仓库；计算组合或计算已有值，并保存为 进程环境变量映射的路径；将处理结果写入进程环境变量映射的路径指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `resolve_patch_target` 解析、规范化或转换当前输入，退出时自动清理资源。
```

#### `test_build_patch_bundle_does_not_modify_source`

- **源码**：`tests/test_patch_tools.py:98`
- **签名**：`def test_build_patch_bundle_does_not_modify_source(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_make_repo` 完成该函数的一项辅助处理，并把结果记为 代码仓库；计算组合或计算已有值，并保存为 数据来源标记；调用 `sha256_file` 计算内容身份、分数或派生结果，并把结果记为 升级前运行报告的 Hash；调用 `build_patch_bundle` 组装当前阶段需要的领域对象，并把结果记为 代码仓库归档包。
断言“检查辅助操作“把外部位置解析为文件系统路径对象”的结果的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果等于升级前运行报告的 Hash；不满足就终止当前测试或流程；断言当前输入内容属于辅助操作“读取辅助操作“把外部位置解析为文件系统路径对象”的结果中的文件内容”的结果；不满足就终止当前测试或流程。
```

#### `test_bundle_becomes_stale_when_patch_file_changes`

- **源码**：`tests/test_patch_tools.py:114`
- **签名**：`def test_bundle_becomes_stale_when_patch_file_changes(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_make_repo` 完成该函数的一项辅助处理，并把结果记为 代码仓库；调用 `build_patch_bundle` 组装当前阶段需要的领域对象，并把结果记为 代码仓库归档包；将处理结果写入辅助操作“把外部位置解析为文件系统路径对象”的结果指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_patch_bundle` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_bundle_becomes_stale_when_source_changes`

- **源码**：`tests/test_patch_tools.py:127`
- **签名**：`def test_bundle_becomes_stale_when_source_changes(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_make_repo` 完成该函数的一项辅助处理，并把结果记为 代码仓库；调用 `build_patch_bundle` 组装当前阶段需要的领域对象，并把结果记为 代码仓库归档包；将处理结果写入当前输入内容指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_patch_bundle` 校验当前输入或状态，退出时自动清理资源。
```

### `tests/test_patch_verification_semantics.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_passed`

- **源码**：`tests/test_patch_verification_semantics.py:7`
- **签名**：`def _passed(name: str) -> PatchVerificationCheck`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收对象名称，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `PatchVerificationCheck` 的领域结果。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `name` | `str` | 对象名称；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`PatchVerificationCheck`
- **语义**：返回 `PatchVerificationCheck` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `PatchVerificationCheck` 结构化领域对象。
```

#### `_structural_checks`

- **源码**：`tests/test_patch_verification_semantics.py:11`
- **签名**：`def _structural_checks() -> list[PatchVerificationCheck]`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终有界、排序或带证据来源的结果集合。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`list[PatchVerificationCheck]`
- **语义**：返回有界或排序后的对象集合；元素类型由返回标注给出。

**伪代码**

```text
返回当前构造的顺序或去重集合。
```

#### `test_no_behavior_test_is_only_structurally_valid`

- **源码**：`tests/test_patch_verification_semantics.py:21`
- **签名**：`def test_no_behavior_test_is_only_structurally_valid()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化顺序集合，并保存为 校验项集合；调用 `summarize_patch_verification` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言当前状态等于'structurally_valid'；不满足就终止当前测试或流程；断言当前处理结果是假；不满足就终止当前测试或流程。
断言当前处理结果是真；不满足就终止当前测试或流程；断言运行的数量等于0；不满足就终止当前测试或流程；断言当前处理结果等于0；不满足就终止当前测试或流程。
```

#### `test_passed_behavior_test_allows_promotion`

- **源码**：`tests/test_patch_verification_semantics.py:36`
- **签名**：`def test_passed_behavior_test_allows_promotion()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化顺序集合，并保存为 校验项集合；调用 `summarize_patch_verification` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言当前状态等于'behaviorally_verified'；不满足就终止当前测试或流程；断言当前处理结果是真；不满足就终止当前测试或流程。
断言运行的数量等于1；不满足就终止当前测试或流程；断言当前处理结果等于1；不满足就终止当前测试或流程。
```

#### `test_failed_behavior_test_fails_verification`

- **源码**：`tests/test_patch_verification_semantics.py:47`
- **签名**：`def test_failed_behavior_test_fails_verification()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算初始化顺序集合，并保存为 校验项集合；调用 `summarize_patch_verification` 完成该函数的一项辅助处理，并把结果记为 多个解包结果；断言当前状态等于'failed'；不满足就终止当前测试或流程；断言当前处理结果是假；不满足就终止当前测试或流程。
```

### `tests/test_patch_verifier_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_git`

- **源码**：`tests/test_patch_verifier_node.py:15`
- **签名**：`def _git(repo: Path, *args: str) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码仓库、命令行或函数位置参数集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `*args` | `str` | 额外位置参数序列。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言当前处理结果等于0，失败时附带断言说明；不满足就终止当前测试或流程。
```

#### `_make_repo`

- **源码**：`tests/test_patch_verifier_node.py:25`
- **签名**：`def _make_repo(tmp_path: Path) -> Path`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，创建只供当前集成测试使用的最小 Git 仓库。该函数接收临时工作目录路径，用于装配论文复现阶段需要的领域对象、执行动作、服务依赖或结构化请求，最终一个经过边界校验的文件或目录路径。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `Path` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`Path`
- **语义**：返回解析后的文件或目录路径对象。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库；创建代码仓库对应的目录；调用 `_git` 完成该函数的一项辅助处理；调用 `_git` 完成该函数的一项辅助处理。
调用 `_git` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 数据来源标记；将处理结果写入数据来源标记指定的文件；调用 `_git` 完成该函数的一项辅助处理。
调用 `_git` 完成该函数的一项辅助处理；返回代码仓库的当前值。
```

#### `_proposal`

- **源码**：`tests/test_patch_verifier_node.py:44`
- **签名**：`def _proposal() -> FileRepairProposal`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终标注为 `FileRepairProposal` 的领域结果。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`FileRepairProposal`
- **语义**：返回 `FileRepairProposal` 类型的领域结果；必要时可能通过异常表示失败。

**伪代码**

```text
构造并返回 `FileRepairProposal` 结构化领域对象。
```

#### `test_patch_verification_uses_worktree_and_keeps_source_unchanged`

- **源码**：`tests/test_patch_verifier_node.py:69`
- **签名**：`def test_patch_verification_uses_worktree_and_keeps_source_unchanged(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_make_repo` 完成该函数的一项辅助处理，并把结果记为 代码仓库；计算组合或计算已有值，并保存为 数据来源标记；读取数据来源标记中的文件内容，并把结果记为 该调用返回的结果；构造 `ExecutionProfile` 结构化领域对象，并把结果记为 MCP Client 配置档案。
调用 `setattr` 完成该函数的一项辅助处理；调用 `build_patch_bundle` 组装当前阶段需要的领域对象，并把结果记为 代码仓库归档包；计算组合或计算已有值，并保存为 当前处理结果的目录；计算组合或计算已有值，并保存为 本次复现运行目录。
创建本次复现运行目录对应的目录；调用 `setattr` 完成该函数的一项辅助处理；调用 `verify_patch_in_worktree` 完成该函数的一项辅助处理，并把结果记为 MCP 评测或运行报告；断言当前状态等于'structurally_valid'；不满足就终止当前测试或流程。
断言当前处理结果是假；不满足就终止当前测试或流程；断言校验项集合是真；不满足就终止当前测试或流程；断言校验项集合运行等于0；不满足就终止当前测试或流程；断言验证结果的 SHA-256有值或为真；不满足就终止当前测试或流程。
断言执行环境配置的 ID等于MCP Client 配置档案 ID；不满足就终止当前测试或流程；断言执行等于'local'；不满足就终止当前测试或流程；断言根目录等于辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程；断言辅助操作“读取数据来源标记中的文件内容”的结果等于当前处理结果；不满足就终止当前测试或流程。
计算组合或计算已有值，并保存为 来源；断言当前输入内容属于辅助操作“读取来源中的文件内容”的结果；不满足就终止当前测试或流程。
```

#### `_git_for_test`

- **源码**：`tests/test_patch_verifier_node.py:131`
- **签名**：`def _git_for_test(repo: Path, *args: str) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码仓库、命令行或函数位置参数集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `*args` | `str` | 额外位置参数序列。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理。
```

#### `test_reused_worktree_rejects_extra_tracked_change`

- **源码**：`tests/test_patch_verifier_node.py:141`
- **签名**：`def test_reused_worktree_rejects_extra_tracked_change(patch_bundle: 未显式标注, verified_worktree: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码修复补丁包、当前处理结果，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `verified_worktree` | `未显式标注` | 名为 `verified_worktree` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将处理结果写入当前输入内容指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_worktree_matches_patch` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_reused_worktree_rejects_staged_change`

- **源码**：`tests/test_patch_verifier_node.py:158`
- **签名**：`def test_reused_worktree_rejects_staged_change(patch_bundle: 未显式标注, verified_worktree: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码修复补丁包、当前处理结果，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `verified_worktree` | `未显式标注` | 名为 `verified_worktree` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 当前处理结果；将处理结果写入当前处理结果指定的文件；调用 `_git_for_test` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_worktree_matches_patch` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_reused_worktree_rejects_missing_target`

- **源码**：`tests/test_patch_verifier_node.py:173`
- **签名**：`def test_reused_worktree_rejects_missing_target(patch_bundle: 未显式标注, verified_worktree: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码修复补丁包、当前处理结果，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `verified_worktree` | `未显式标注` | 名为 `verified_worktree` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `unlink` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_worktree_matches_patch` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_reused_worktree_rejects_wrong_after_hash`

- **源码**：`tests/test_patch_verifier_node.py:186`
- **签名**：`def test_reused_worktree_rejects_wrong_after_hash(patch_bundle: 未显式标注, verified_worktree: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码修复补丁包、当前处理结果，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `verified_worktree` | `未显式标注` | 名为 `verified_worktree` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
将处理结果写入当前输入内容指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_worktree_matches_patch` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_reused_worktree_rejects_changed_head`

- **源码**：`tests/test_patch_verifier_node.py:202`
- **签名**：`def test_reused_worktree_rejects_changed_head(patch_bundle: 未显式标注, verified_worktree: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码修复补丁包、当前处理结果，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `verified_worktree` | `未显式标注` | 名为 `verified_worktree` 的 `未显式标注` 领域输入；用于当前函数的业务处理，具体约束见校验分支。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_git_for_test` 完成该函数的一项辅助处理；调用 `_git_for_test` 完成该函数的一项辅助处理。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_worktree_matches_patch` 校验当前输入或状态，退出时自动清理资源。
```

### `tests/test_patch_worktree_cleanup.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_git`

- **源码**：`tests/test_patch_worktree_cleanup.py:14`
- **签名**：`def _git(repo: Path, *args: str) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码仓库、命令行或函数位置参数集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `*args` | `str` | 额外位置参数序列。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `run` 完成该函数的一项辅助处理。
```

#### `test_cleanup_rejects_path_outside_current_run`

- **源码**：`tests/test_patch_worktree_cleanup.py:24`
- **签名**：`def test_cleanup_rejects_path_outside_current_run(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现运行目录；计算组合或计算已有值，并保存为 当前处理结果；创建当前处理结果对应的目录；将处理结果写入当前输入内容指定的文件。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `validate_patch_worktree_path` 校验当前输入或状态，退出时自动清理资源。
```

#### `test_cleanup_removes_only_valid_run_worktree`

- **源码**：`tests/test_patch_worktree_cleanup.py:37`
- **签名**：`def test_cleanup_removes_only_valid_run_worktree(patch_bundle: 未显式标注, tmp_path: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码修复补丁包、临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `patch_bundle` | `未显式标注` | 代码修复补丁包；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
把外部位置解析为文件系统路径对象，并把结果记为 代码仓库；计算组合或计算已有值，并保存为 本次复现运行目录；计算组合或计算已有值，并保存为 当前处理结果；创建父级目录或父领域对象对应的目录。
调用 `_git` 完成该函数的一项辅助处理；调用 `remove_patch_worktree` 完成该函数的一项辅助处理；断言“检查当前处理结果的文件系统属性”后未得到肯定结果；不满足就终止当前测试或流程。
```

### `tests/test_preflight_check_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_probe_result`

- **源码**：`tests/test_preflight_check_node.py:11`
- **签名**：`def _probe_result(run_state) -> dict`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
计算组合或计算已有值，并保存为 尝试；创建尝试对应的目录；计算按字段初始化键值映射，并保存为 文件或目录路径集合。
遍历辅助操作产生的可迭代结果（调用 `values` 完成该函数的一项辅助处理），每次把当前项记为文件或目录路径，然后将处理结果写入文件或目录路径指定的文件。
返回当前计算得到的结果。
```

#### `test_preflight_report_is_written_to_current_run`

- **源码**：`tests/test_preflight_check_node.py:30`
- **签名**：`def test_preflight_report_is_written_to_current_run(run_state) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `PreflightReport` 结构化领域对象，并把结果记为 MCP 评测或运行报告；调用 `_probe_result` 完成该函数的一项辅助处理，并把结果记为 该调用返回的结果；计算按字段初始化键值映射，并保存为 复现流程状态。
在上下文“调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `preflight_check_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
调用 `assert_called_once_with` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 MCP 评测或运行报告的路径；计算组合或计算已有值，并保存为 当前处理结果的路径；断言阶段处理结果中的对应字段是真；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段等于辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程；断言“检查MCP 评测或运行报告的路径的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前处理结果的路径的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；遍历并筛选输入，将整理后的结果保存为 当前处理结果。
断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程；断言当前输入内容属于当前处理结果；不满足就终止当前测试或流程；断言由当前处理结果组成的集合或迭代器中存在满足““检查文件或目录路径是否满足文本匹配条件”后得到肯定结果”的项；不满足就终止当前测试或流程。
```

#### `test_preflight_requires_run_dir`

- **源码**：`tests/test_preflight_check_node.py:85`
- **签名**：`def test_preflight_requires_run_dir() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `preflight_check_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段是假；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'agent_failed'；不满足就终止当前测试或流程。
```

### `tests/test_repair_action_builder_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_repair_action_builder_rebuilds_pending_action_and_increments_attempts`

- **源码**：`tests/test_repair_action_builder_node.py:10`
- **签名**：`def test_repair_action_builder_rebuilds_pending_action_and_increments_attempts()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
构造 `ExecutionProfile` 结构化领域对象，并把结果记为 MCP Client 配置档案；计算按字段初始化键值映射，并保存为 复现流程状态。
在上下文“调用 `patch` 完成该函数的一项辅助处理”中调用 `repair_action_builder_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段等于1；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'python'；不满足就终止当前测试或流程；断言当前输入内容属于阶段处理结果中的对应字段中的对应字段；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'paper-conda'；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段等于辅助操作“调用 `compute_execution_profile_fingerprint` 计算内容身份、分数或派生结果”的结果；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'paper-conda'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于阶段处理结果中的对应字段；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段为空；不满足就终止当前测试或流程。
```

#### `test_repair_action_builder_rejects_out_of_bounds_command`

- **源码**：`tests/test_repair_action_builder_node.py:81`
- **签名**：`def test_repair_action_builder_rejects_out_of_bounds_command()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；调用 `repair_action_builder_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段等于'repair_out_of_bounds'；不满足就终止当前测试或流程。
```

### `tests/test_repair_proposal_semantics.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_base_payload`

- **源码**：`tests/test_repair_proposal_semantics.py:9`
- **签名**：`def _base_payload() -> dict`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `proposal_id`、`source_error_type`、`kind`、`summary`、`root_cause`、`repaired_command`、`changed_arguments`、`steps` 等字段的结构化映射。
```

#### `test_edit_command_requires_repaired_command`

- **源码**：`tests/test_repair_proposal_semantics.py:26`
- **签名**：`def test_edit_command_requires_repaired_command()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_base_payload` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；计算使用固定配置或常量值，并保存为 结构化请求载荷中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_no_repair_must_not_contain_command`

- **源码**：`tests/test_repair_proposal_semantics.py:34`
- **签名**：`def test_no_repair_must_not_contain_command()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_base_payload` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；计算使用固定配置或常量值，并保存为 结构化请求载荷中的对应字段。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中复制、序列化或校验结构化领域对象，退出时自动清理资源。
```

#### `test_edit_command_accepts_complete_bounded_proposal`

- **源码**：`tests/test_repair_proposal_semantics.py:42`
- **签名**：`def test_edit_command_accepts_complete_bounded_proposal()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `_base_payload` 完成该函数的一项辅助处理，并把结果记为 结构化请求载荷；把新的处理结果追加或合并到结构化请求载荷；复制、序列化或校验结构化领域对象，并把结果记为 修复或重跑提案；断言业务类别等于'edit_command'；不满足就终止当前测试或流程。
```

### `tests/test_review_flow.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_executor_runs_when_not_required`

- **源码**：`tests/test_review_flow.py:8`
- **签名**：`def test_executor_runs_when_not_required(run_state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；计算按字段初始化键值映射，并保存为 测试替身结果。
在上下文“调用 `patch` 完成该函数的一项辅助处理”中调用 `executor_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言当前输入内容不属于阶段处理结果；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段有值或为真；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段是真；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'evidence_recorded'；不满足就终止当前测试或流程。
```

### `tests/test_run_manifest_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_run_context_node_creates_run_id_and_run_dir`

- **源码**：`tests/test_run_manifest_node.py:17`
- **签名**：`def test_run_context_node_creates_run_id_and_run_dir(tmp_path, monkeypatch)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `setattr` 完成该函数的一项辅助处理；执行 `run_context_node` 对应的阶段流程并取得状态结果，并把结果记为 阶段处理结果；断言“检查阶段处理结果中的对应字段是否满足文本匹配条件”后得到肯定结果；不满足就终止当前测试或流程；断言“检查辅助操作“把外部位置解析为文件系统路径对象”的结果的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段有值或为真；不满足就终止当前测试或流程。
```

#### `test_run_context_node_reuses_existing_run_on_resume`

- **源码**：`tests/test_run_manifest_node.py:32`
- **签名**：`def test_run_context_node_reuses_existing_run_on_resume(tmp_path, monkeypatch)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `setattr` 完成该函数的一项辅助处理；计算组合或计算已有值，并保存为 已有运行的目录；计算按字段初始化键值映射，并保存为 复现流程状态；执行 `run_context_node` 对应的阶段流程并取得状态结果，并把结果记为 阶段处理结果。
断言阶段处理结果中的对应字段等于'demo-run'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'2026-07-16T00:00:00+00:00'；不满足就终止当前测试或流程；断言“检查已有运行的目录的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_run_manifest_node_indexes_registered_run_artifacts`

- **源码**：`tests/test_run_manifest_node.py:50`
- **签名**：`def test_run_manifest_node_indexes_registered_run_artifacts(tmp_path: 未显式标注, run_state: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库的目录；创建代码仓库的目录对应的目录；计算按字段初始化键值映射，并保存为 复现流程状态；调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；把新的处理结果追加或合并到复现流程状态；执行 `run_manifest_node` 对应的阶段流程并取得状态结果，并把结果记为 阶段处理结果；把外部位置解析为文件系统路径对象，并把结果记为 Artifact的索引的路径。
把外部位置解析为文件系统路径对象，并把结果记为 运行Manifest的路径；断言“检查Artifact的索引的路径的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言“检查运行Manifest的路径的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；将外部表示解析为结构化内容，并把结果记为 Artifact的索引。
将外部表示解析为结构化内容，并把结果记为 运行或工作区 Manifest；读取Artifact的索引中的对应字段，并保存为 后续步骤使用的结果；断言Artifact的索引中的对应字段等于本次运行状态中的对应字段；不满足就终止当前测试或流程；断言Artifact的索引中的对应字段等于当前处理结果 的长度；不满足就终止当前测试或流程。
断言由当前处理结果组成的集合或迭代器中存在满足“当前处理项中的对应字段等于'analysis/paper_summary.json' 且 当前处理项中的对应字段等于'analysis' 且 当前处理项中的对应字段等于'method_extractor' 且 当前处理项中的对应字段等于'current'”的项；不满足就终止当前测试或流程。
断言由当前处理结果组成的集合或迭代器中存在满足“当前处理项中的对应字段等于'reports/final_report.md' 且 当前处理项中的对应字段等于'reports' 且 当前处理项中的对应字段等于'final_report' 且 当前处理项中的对应字段等于'current'”的项；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段等于5；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段等于本次运行状态中的对应字段；不满足就终止当前测试或流程。
断言运行或工作区 Manifest中的对应字段等于'succeeded'；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段中的对应字段中的对应字段等于'a' × 64；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段中的对应字段中的对应字段等于'execution_protocol'；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段中的对应字段等于'c' × 64；不满足就终止当前测试或流程。
断言运行或工作区 Manifest中的对应字段中的对应字段等于'python train.py --dataset_path /data/demo'；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段等于'hash-demo'；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段中的对应字段中的对应字段是真；不满足就终止当前测试或流程；读取运行或工作区 Manifest中的对应字段，并保存为 后续步骤使用的结果。
断言当前处理结果中的对应字段等于'exec-test'；不满足就终止当前测试或流程；断言当前处理结果中的对应字段等于'exited'；不满足就终止当前测试或流程；断言当前处理结果中的对应字段中的对应字段是真；不满足就终止当前测试或流程；断言当前处理结果中的对应字段中的对应字段是假；不满足就终止当前测试或流程。
断言运行或工作区 Manifest中的对应字段中的对应字段等于0；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段中的对应字段等于运行或工作区 Manifest中的对应字段中的对应字段；不满足就终止当前测试或流程；把外部位置解析为文件系统路径对象，并把结果记为 本次复现运行目录；断言父级目录或父领域对象等于本次复现运行目录 ÷ 'reports'；不满足就终止当前测试或流程。
断言父级目录或父领域对象等于本次复现运行目录 ÷ 'reports'；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“领域记录中的对应字段等于本次运行状态中的对应字段”的项；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“本次复现运行目录属于前一步操作返回对象的当前处理结果”的项；不满足就终止当前测试或流程；断言当前可迭代输入中每一项都满足“领域记录中的对应字段等于辅助操作“调用 `sha256_file` 计算内容身份、分数或派生结果”的结果”的项；不满足就终止当前测试或流程。
```

#### `test_manifest_allows_legacy_sync_run_without_job_identity`

- **源码**：`tests/test_run_manifest_node.py:212`
- **签名**：`def test_manifest_allows_legacy_sync_run_without_job_identity(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `setattr` 完成该函数的一项辅助处理；计算按字段初始化键值映射，并保存为 复现流程状态；把新的处理结果追加或合并到复现流程状态；执行 `run_manifest_node` 对应的阶段流程并取得状态结果，并把结果记为 阶段处理结果。
将外部表示解析为结构化内容，并把结果记为 运行或工作区 Manifest；断言运行或工作区 Manifest中的对应字段等于5；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段为空；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段为空；不满足就终止当前测试或流程。
断言运行或工作区 Manifest中的对应字段中的对应字段为空；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段中的对应字段为空；不满足就终止当前测试或流程；断言运行或工作区 Manifest中的对应字段中的对应字段为空；不满足就终止当前测试或流程。
```

### `tests/test_run_native_artifacts.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_write_artifact_is_inside_current_run`

- **源码**：`tests/test_run_native_artifacts.py:17`
- **签名**：`def test_write_artifact_is_inside_current_run(run_state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_json_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；将辅助操作“把外部位置解析为文件系统路径对象”的结果规范化为受控的绝对路径，并把结果记为 本次复现运行目录；断言本次复现运行目录属于前一步操作返回对象的当前处理结果；不满足就终止当前测试或流程；断言仓库内相对路径等于'analysis/demo.json'；不满足就终止当前测试或流程。
断言当前处理结果等于'analysis'；不满足就终止当前测试或流程；断言产生当前状态的流程节点等于'test_node'；不满足就终止当前测试或流程；断言内容 SHA-256有值或为真；不满足就终止当前测试或流程；断言对象大小的字节内容大于0；不满足就终止当前测试或流程。
```

#### `test_artifact_path_escape_is_rejected`

- **源码**：`tests/test_run_native_artifacts.py:44`
- **签名**：`def test_artifact_path_escape_is_rejected(run_state: 未显式标注, relative_path: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态、仓库内相对路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `relative_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `resolve_artifact_path` 解析、规范化或转换当前输入，退出时自动清理资源。
```

#### `test_artifact_records_are_upserted_by_relative_path`

- **源码**：`tests/test_run_native_artifacts.py:52`
- **签名**：`def test_artifact_records_are_upserted_by_relative_path(run_state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；调用 `artifact_state_update` 完成该函数的一项辅助处理，并把结果记为 第一项；计算按字段初始化键值映射，并保存为 状态；调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果。
调用 `artifact_state_update` 完成该函数的一项辅助处理，并把结果记为 第二项；遍历并筛选输入，将整理后的结果保存为 当前处理结果；断言当前处理结果 的长度等于1；不满足就终止当前测试或流程；断言当前处理结果中的对应字段中的对应字段等于'second_node'；不满足就终止当前测试或流程。
断言辅助操作“读取辅助操作“把外部位置解析为文件系统路径对象”的结果中的文件内容”的结果等于'second'；不满足就终止当前测试或流程。
```

#### `test_inspect_artifact_detects_hash_mismatch`

- **源码**：`tests/test_run_native_artifacts.py:86`
- **签名**：`def test_inspect_artifact_detects_hash_mismatch(run_state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `write_text_artifact` 持久化或更新当前领域数据，并把结果记为 多个解包结果；计算按字段初始化键值映射，并保存为 状态；将处理结果写入文件或目录路径指定的文件；调用 `inspect_artifact_records` 完成该函数的一项辅助处理，并把结果记为 多个解包结果。
调用 `next` 完成该函数的一项辅助处理，并把结果记为 当前处理项；断言当前处理项中的对应字段等于'hash_mismatch'；不满足就终止当前测试或流程；断言由诊断问题集合组成的集合或迭代器中存在满足“诊断问题中的对应字段等于'ARTIFACT_HASH_MISMATCH'”的项；不满足就终止当前测试或流程。
```

#### `test_artifact_record_schema_rejects_negative_size`

- **源码**：`tests/test_run_native_artifacts.py:113`
- **签名**：`def test_artifact_record_schema_rejects_negative_size()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
在上下文“调用 `raises` 完成该函数的一项辅助处理”中构造 `ArtifactRecord` 结构化领域对象，退出时自动清理资源。
```

### `tests/test_smoke_repair_flow.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_route_after_preflight_goes_to_smoke_when_passed`

- **源码**：`tests/test_smoke_repair_flow.py:21`
- **签名**：`def test_route_after_preflight_goes_to_smoke_when_passed()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_preflight` 完成该函数的一项辅助处理”的结果等于'smoke_test'；不满足就终止当前测试或流程。
```

#### `test_route_after_smoke_test_goes_to_executor_when_passed`

- **源码**：`tests/test_smoke_repair_flow.py:25`
- **签名**：`def test_route_after_smoke_test_goes_to_executor_when_passed()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_smoke_test` 完成该函数的一项辅助处理”的结果等于'executor'；不满足就终止当前测试或流程。
```

#### `test_route_after_smoke_test_goes_to_executor_when_skipped`

- **源码**：`tests/test_smoke_repair_flow.py:29`
- **签名**：`def test_route_after_smoke_test_goes_to_executor_when_skipped()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_smoke_test` 完成该函数的一项辅助处理”的结果等于'executor'；不满足就终止当前测试或流程。
```

#### `test_route_after_smoke_test_goes_to_log_debug_when_failed`

- **源码**：`tests/test_smoke_repair_flow.py:33`
- **签名**：`def test_route_after_smoke_test_goes_to_log_debug_when_failed()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；断言辅助操作“调用 `route_after_smoke_test` 完成该函数的一项辅助处理”的结果等于'log_debug'；不满足就终止当前测试或流程。
```

#### `test_route_after_log_debug_goes_to_repair_planner_before_limit`

- **源码**：`tests/test_smoke_repair_flow.py:41`
- **签名**：`def test_route_after_log_debug_goes_to_repair_planner_before_limit()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_log_debug` 完成该函数的一项辅助处理”的结果等于'repair_planner'；不满足就终止当前测试或流程。
```

#### `test_route_after_repair_planner_goes_to_repair_action_builder_for_edit_command`

- **源码**：`tests/test_smoke_repair_flow.py:45`
- **签名**：`def test_route_after_repair_planner_goes_to_repair_action_builder_for_edit_command()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态；断言辅助操作“调用 `route_after_repair_planner` 完成该函数的一项辅助处理”的结果等于'repair_action_builder'；不满足就终止当前测试或流程。
```

#### `test_route_after_repair_action_builder_returns_to_risk_check`

- **源码**：`tests/test_smoke_repair_flow.py:55`
- **签名**：`def test_route_after_repair_action_builder_returns_to_risk_check()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
断言辅助操作“调用 `route_after_repair_action_builder` 完成该函数的一项辅助处理”的结果等于'risk_check'；不满足就终止当前测试或流程。
```

#### `test_cuda_oom_builds_bounded_batch_size_repair_without_llm`

- **源码**：`tests/test_smoke_repair_flow.py:59`
- **签名**：`def test_cuda_oom_builds_bounded_batch_size_repair_without_llm(run_state: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 复现流程状态。
在上下文“调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `repair_planner_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
调用 `assert_not_called` 完成该函数的一项辅助处理；读取阶段处理结果中的对应字段，并保存为 修复或重跑提案；断言修复或重跑提案中的对应字段等于'edit_command'；不满足就终止当前测试或流程；断言当前输入内容属于修复或重跑提案中的对应字段；不满足就终止当前测试或流程。
断言修复或重跑提案中的对应字段等于['--batch-size 8 -> 1']；不满足就终止当前测试或流程。
```

#### `test_cuda_oom_debug_report_does_not_require_llm`

- **源码**：`tests/test_smoke_repair_flow.py:89`
- **签名**：`def test_cuda_oom_debug_report_does_not_require_llm(tmp_path: 未显式标注, run_state: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 运行日志路径；将处理结果写入运行日志路径指定的文件。
在上下文“调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `log_debug_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
调用 `assert_not_called` 完成该函数的一项辅助处理；断言阶段处理结果中的对应字段中的对应字段等于'cuda_oom'；不满足就终止当前测试或流程。
```

#### `test_shape_mismatch_with_related_files_hands_off_to_file_repair`

- **源码**：`tests/test_smoke_repair_flow.py:109`
- **签名**：`def test_shape_mismatch_with_related_files_hands_off_to_file_repair(run_state: 未显式标注, monkeypatch: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `setattr` 完成该函数的一项辅助处理；调用 `setattr` 完成该函数的一项辅助处理；计算按字段初始化键值映射，并保存为 复现流程状态。
在上下文“调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给当前处理结果”中调用 `repair_planner_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
调用 `assert_not_called` 完成该函数的一项辅助处理；读取阶段处理结果中的对应字段，并保存为 修复或重跑提案；断言修复或重跑提案中的对应字段等于'manual_only'；不满足就终止当前测试或流程；断言修复或重跑提案中的对应字段为空；不满足就终止当前测试或流程。
断言修复或重跑提案中的对应字段中的对应字段中的对应字段等于'manual_check'；不满足就终止当前测试或流程；断言修复或重跑提案中的对应字段中的对应字段中的对应字段等于'medium'；不满足就终止当前测试或流程；计算按字段初始化键值映射，并保存为 状态；断言辅助操作“调用 `route_after_repair_planner` 完成该函数的一项辅助处理”的结果等于'file_repair_planner'；不满足就终止当前测试或流程。
```

#### `test_traceback_paths_are_limited_to_existing_repo_python_files`

- **源码**：`tests/test_smoke_repair_flow.py:143`
- **签名**：`def test_traceback_paths_are_limited_to_existing_repo_python_files(tmp_path)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库；计算组合或计算已有值，并保存为 测试文件；计算组合或计算已有值，并保存为 来源文件；创建父级目录或父领域对象对应的目录。
将处理结果写入测试文件指定的文件；将处理结果写入来源文件指定的文件；计算根据字段和固定文本生成格式化文本，并保存为 异常堆栈文本；断言辅助操作“调用 `extract_repo_traceback_paths` 完成该函数的一项辅助处理”的结果等于['tests/test_demo.py', 'demo.py']；不满足就终止当前测试或流程。
```

#### `test_log_debug_merges_traceback_paths_with_model_related_files`

- **源码**：`tests/test_smoke_repair_flow.py:166`
- **签名**：`def test_log_debug_merges_traceback_paths_with_model_related_files(tmp_path: 未显式标注, run_state: 未显式标注, monkeypatch: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、本次运行状态、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库；计算组合或计算已有值，并保存为 测试文件；计算组合或计算已有值，并保存为 来源文件；创建父级目录或父领域对象对应的目录。
将处理结果写入测试文件指定的文件；将处理结果写入来源文件指定的文件；计算组合或计算已有值，并保存为 运行日志路径；将处理结果写入运行日志路径指定的文件。
构造 `StructuredInvocationResult` 结构化领域对象，并把结果记为 工具调用记录；构造 `ScriptedModelGateway` 结构化领域对象，并把结果记为 外部服务网关。
在上下文“调用 `patch` 完成该函数的一项辅助处理”中调用 `log_debug_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段中的对应字段等于['tests/test_demo.py', 'demo.py']；不满足就终止当前测试或流程。
```

### `tests/test_smoke_test_node.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `_action`

- **源码**：`tests/test_smoke_test_node.py:9`
- **签名**：`def _action(repo_dir: Path, args: list[str]) -> dict`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收代码仓库的目录、命令行或函数位置参数集合，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `repo_dir` | `Path` | 已经解析的文件或目录路径对象；后续操作仍需遵守仓库/工作区边界。 |
| `args` | `list[str]` | 命令行或函数位置参数集合；用于当前函数的论文复现处理，具体约束由类型标注和校验分支确定。 |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
返回包含 `action_id`、`action_type`、`program`、`args`、`cwd`、`source`、`reason`、`timeout_seconds` 等字段的结构化映射。
```

#### `_supervisor_result`

- **源码**：`tests/test_smoke_test_node.py:28`
- **签名**：`def _supervisor_result(run_state: 未显式标注, ok: bool, end_reason: str) -> dict`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态、处理是否成功的判断、原因，用于围绕论文复现链路完成一次受控的数据处理、状态更新或依赖协调，最终包含复现状态、索引或序列化字段的结构化映射。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |
| `ok` | `bool` | 布尔条件或能力开关，用于控制流程分支。 |
| `end_reason` | `str` | 名为 `end_reason` 的业务文本或控制字符串；具体允许值由函数用途和校验分支确定。；默认 'exited' |

**输出**

- **Python 类型**：`dict`
- **语义**：返回键值映射；常用于状态更新、序列化投影或索引结果。

**伪代码**

```text
计算组合或计算已有值，并保存为 尝试；创建尝试对应的目录；计算组合或计算已有值，并保存为 进程标准输出的路径；计算组合或计算已有值，并保存为 进程标准错误的路径。
计算组合或计算已有值，并保存为 当前处理结果的路径；计算组合或计算已有值，并保存为 领域记录的路径；将处理结果写入进程标准输出的路径指定的文件；将处理结果写入进程标准错误的路径指定的文件。
将处理结果写入当前处理结果的路径指定的文件；将处理结果写入领域记录的路径指定的文件；返回包含 `ok`、`returncode`、`end_reason`、`stdout`、`stderr`、`combined_output`、`timeout`、`cancelled` 等字段的结构化映射。
```

#### `test_smoke_test_node_runs_reduced_action_and_writes_report`

- **源码**：`tests/test_smoke_test_node.py:69`
- **签名**：`def test_smoke_test_node_runs_reduced_action_and_writes_report(tmp_path: 未显式标注, run_state: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库的目录；创建代码仓库的目录对应的目录；计算按字段初始化键值映射，并保存为 复现流程状态；调用 `_supervisor_result` 完成该函数的一项辅助处理，并把结果记为 测试替身结果。
在上下文“调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给运行”中调用 `smoke_test_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
读取命令行或函数位置参数集合中的对应字段，并保存为 后续步骤使用的结果；调用 `assert_called_once_with` 完成该函数的一项辅助处理；断言阶段处理结果中的对应字段等于'passed'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段是真；不满足就终止当前测试或流程。
断言阶段处理结果中的对应字段等于测试替身结果中的对应字段；不满足就终止当前测试或流程；断言当前处理结果中的对应字段等于'none'；不满足就终止当前测试或流程；断言当前处理结果中的对应字段等于[辅助操作“调用 `str` 完成该函数的一项辅助处理”的结果]；不满足就终止当前测试或流程；读取阶段处理结果中的对应字段，并保存为 MCP 评测或运行报告。
断言当前输入内容属于MCP 评测或运行报告中的对应字段；不满足就终止当前测试或流程；断言当前输入内容属于MCP 评测或运行报告中的对应字段；不满足就终止当前测试或流程；断言当前输入内容属于MCP 评测或运行报告中的对应字段；不满足就终止当前测试或流程。
```

#### `test_smoke_test_node_skips_when_no_safe_reduction_found`

- **源码**：`tests/test_smoke_test_node.py:116`
- **签名**：`def test_smoke_test_node_skips_when_no_safe_reduction_found(tmp_path: 未显式标注, run_state: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库的目录；创建代码仓库的目录对应的目录；计算按字段初始化键值映射，并保存为 复现流程状态。
在上下文“调用 `patch` 完成该函数的一项辅助处理，并把上下文资源交给运行”中调用 `smoke_test_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
调用 `assert_not_called` 完成该函数的一项辅助处理；断言阶段处理结果中的对应字段等于'skipped'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段是真；不满足就终止当前测试或流程。
```

#### `test_smoke_test_node_sets_log_path_when_failed`

- **源码**：`tests/test_smoke_test_node.py:139`
- **签名**：`def test_smoke_test_node_sets_log_path_when_failed(tmp_path: 未显式标注, run_state: 未显式标注) -> None（隐式）`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收临时工作目录路径、本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 代码仓库的目录；创建代码仓库的目录对应的目录；计算按字段初始化键值映射，并保存为 复现流程状态；调用 `_supervisor_result` 完成该函数的一项辅助处理，并把结果记为 测试替身结果。
在上下文“调用 `patch` 完成该函数的一项辅助处理”中调用 `smoke_test_node` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果，退出时自动清理资源。
断言阶段处理结果中的对应字段等于'failed'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于测试替身结果中的对应字段；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段等于'failed'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'paper_program'；不满足就终止当前测试或流程。
```

### `tests/test_stage_error_tools.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_persist_stage_error_writes_json_and_markdown`

- **源码**：`tests/test_stage_error_tools.py:17`
- **签名**：`def test_persist_stage_error_writes_json_and_markdown(run_state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_stage_error` 组装当前阶段需要的领域对象，并把结果记为 错误信息；调用 `persist_stage_errors` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段等于'invalid_input'；不满足就终止当前测试或流程；断言辅助操作“调用 `has_terminal_stage_error` 校验当前输入或状态”的结果是真；不满足就终止当前测试或流程。
断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程；断言“检查当前输入内容的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_nonterminal_paper_program_error_does_not_stop`

- **源码**：`tests/test_stage_error_tools.py:45`
- **签名**：`def test_nonterminal_paper_program_error_does_not_stop(run_state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `build_stage_error` 组装当前阶段需要的领域对象，并把结果记为 错误信息；调用 `persist_stage_errors` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言辅助操作“调用 `has_terminal_stage_error` 校验当前输入或状态”的结果是假；不满足就终止当前测试或流程；断言当前输入内容不属于阶段处理结果；不满足就终止当前测试或流程。
```

#### `test_guard_converts_unhandled_exception`

- **源码**：`tests/test_stage_error_tools.py:63`
- **签名**：`def test_guard_converts_unhandled_exception(run_state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
定义内部辅助函数 `broken_node`，供当前函数在后续步骤中调用。
调用 `辅助操作` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段等于'agent_failed'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'UNHANDLED_AGENT_EXCEPTION'；不满足就终止当前测试或流程；断言阶段处理结果中的对应字段中的对应字段等于'broken_node'；不满足就终止当前测试或流程。
读取阶段处理结果中的对应字段中的对应字段，并保存为 调用链追踪信息的路径；断言调用链追踪信息的路径有值或为真；不满足就终止当前测试或流程；断言“检查辅助操作“把外部位置解析为文件系统路径对象”的结果的文件系统属性”后得到肯定结果；不满足就终止当前测试或流程。
```

#### `test_guard_converts_unhandled_exception.broken_node`

- **源码**：`tests/test_stage_error_tools.py:64`
- **签名**：`def broken_node(state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `RuntimeError`，向调用方报告输入或运行失败。
```

#### `test_guard_does_not_swallow_graph_interrupt`

- **源码**：`tests/test_stage_error_tools.py:81`
- **签名**：`def test_guard_does_not_swallow_graph_interrupt(run_state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收本次运行状态，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `run_state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
定义内部辅助函数 `interrupted_node`，供当前函数在后续步骤中调用。
在上下文“调用 `raises` 完成该函数的一项辅助处理”中调用 `辅助操作` 完成该函数的一项辅助处理，退出时自动清理资源。
```

#### `test_guard_does_not_swallow_graph_interrupt.interrupted_node`

- **源码**：`tests/test_stage_error_tools.py:82`
- **签名**：`def interrupted_node(state)`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收复现流程状态，用于作为 Graph 节点读取当前复现状态，完成一个阶段动作，并以状态更新形式把证据、错误或产物交给下一节点，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `state` | `未显式标注` | Agent/Graph 当前状态或状态字段映射；节点通过它传递阶段结果和错误信息。 |

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
拒绝继续处理并抛出 `GraphInterrupt`，向调用方报告输入或运行失败。
```

#### `test_error_message_redacts_secret_assignment`

- **源码**：`tests/test_stage_error_tools.py:93`
- **签名**：`def test_error_message_redacts_secret_assignment()`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None（隐式）`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
调用 `sanitize_error_message` 完成该函数的一项辅助处理，并把结果记为 面向用户或日志的提示信息；断言当前输入内容不属于面向用户或日志的提示信息；不满足就终止当前测试或流程；断言当前输入内容属于面向用户或日志的提示信息；不满足就终止当前测试或流程。
```

### `tests/test_structured_action_and_approval_hash.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_action_hash_binds_network_and_budget`

- **源码**：`tests/test_structured_action_and_approval_hash.py:6`
- **签名**：`def test_action_hash_binds_network_and_budget() -> None`
- **作用**：在论文复现系统的自动化测试和边界验证阶段中，该函数接收当前运行配置、模块状态和已注入依赖，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

无显式输入；函数从模块配置、闭包或已注入实例依赖读取所需状态。

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算按字段初始化键值映射，并保存为 待执行复现动作；调用 `compute_action_hash` 计算内容身份、分数或派生结果，并把结果记为 该调用返回的结果；调用 `compute_action_hash` 计算内容身份、分数或派生结果，并把结果记为 该调用返回的结果；调用 `compute_action_hash` 计算内容身份、分数或派生结果，并把结果记为 该调用返回的结果。
断言当前处理结果不等于当前处理结果；不满足就终止当前测试或流程；断言当前处理结果不等于当前处理结果；不满足就终止当前测试或流程。
```

### `tests/test_supervised_execution_integration.py`

**模块作用**：以源码中的函数、类和常量共同实现该模块职责。

#### `test_local_runner_child_cannot_read_agent_api_key`

- **源码**：`tests/test_supervised_execution_integration.py:12`
- **签名**：`def test_local_runner_child_cannot_read_agent_api_key(tmp_path: 未显式标注, monkeypatch: 未显式标注) -> None`
- **作用**：在复现实验命令的受控执行、监督和失败恢复阶段中，该函数接收临时工作目录路径、测试环境修改工具，用于构造受控输入、替身依赖或失败场景，并验证系统输出、状态变化、异常边界和安全约束，最终更新流程状态、写入运行产物或通过异常报告不可复现原因。

**输入**

| 参数 | Python 类型 | 语义 |
|---|---|---|
| `tmp_path` | `未显式标注` | 文件或目录路径；用于定位输入、输出或日志，访问范围由函数内的路径边界检查决定。 |
| `monkeypatch` | `未显式标注` | pytest 提供的环境/对象替换工具，用于隔离测试副作用；不是业务输入。 |

**输出**

- **Python 类型**：`None`
- **语义**：无业务返回值；函数通过注册、持久化、文件写入、状态更新或异常产生效果。

**伪代码**

```text
计算组合或计算已有值，并保存为 本次复现工作区；计算组合或计算已有值，并保存为 当前处理结果的目录；计算组合或计算已有值，并保存为 本次复现运行目录；创建本次复现工作区对应的目录。
创建本次复现运行目录对应的目录；计算组合或计算已有值，并保存为 当前处理结果；将处理结果写入当前处理结果指定的文件；调用 `str` 完成该函数的一项辅助处理，并把结果记为 当前处理结果的目录。
读取前一步操作返回对象的对象名称，并保存为 待启动实验程序；构造 `ExecutionProfile` 结构化领域对象，并把结果记为 MCP Client 配置档案；构造 `ExecutableAction` 结构化领域对象，并把结果记为 待执行复现动作；调用 `setenv` 完成该函数的一项辅助处理。
调用 `setattr` 完成该函数的一项辅助处理；调用 `run` 完成该函数的一项辅助处理，并把结果记为 阶段处理结果；断言阶段处理结果中的对应字段是真；不满足就终止当前测试或流程；断言辅助操作“对阶段处理结果中的对应字段中的文本执行规范化或拆分”的结果等于'<missing>'；不满足就终止当前测试或流程。
将外部表示解析为结构化内容，并把结果记为 记录；计算初始化去重集合，并保存为 键集合集合；断言当前输入内容不属于键集合集合；不满足就终止当前测试或流程。
```
