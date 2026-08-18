# Paper Reproduction Copilot 当前功能完整验收教程

> 验收对象：P4Transformer 论文与代码仓库  
> 项目根目录：`/data/tianshaoqi24/agent/paper_reproduction_copilot`  
> 论文：`pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf`  
> 仓库：`/data/tianshaoqi24/P4Transformer/`  
> Agent 环境：`/home/tianshaoqi24/miniconda3/envs/agent`  
> 复现环境：`/home/tianshaoqi24/miniconda3/envs/3d`

本文不是新的功能实现阶段，而是对当前项目已有能力进行一次完整、分层、可复查的验收。默认流程不会开始真实训练，不会下载数据集，也不会批准补丁写回 P4Transformer 原始仓库。

---

## 一、验收目标

本次验收分成六层：

1. **配置层**：路径、Python 环境、Execution Profile、Secret Vault 是否可用。
2. **工程层**：静态检查和自动化测试是否存在代码回归。
3. **Agent 评测层**：Golden Case、路由、安全、恢复、证据和对话决策是否通过基线门禁。
4. **端到端工作流层**：论文解析、仓库检索、实验规划、命令选择、风险审批、预检、执行和报告能否连通。
5. **服务层**：异步 Job、Checkpoint、事件流、Web/API、Chat 和 Artifact 是否可用。
6. **互操作层**：Tool Contract、Skill、MCP Contract 和 MCP Runtime SLO 是否可用。

这里的“完整验收”表示验证当前单机、单用户配置实际启用的能力。以下能力需要额外基础设施，因此不属于本次基础门禁：

- PostgreSQL 多 Worker 抢占；
- S3/对象存储远端发布；
- 跨主机 Workspace 迁移；
- OCI 镜像运行；
- 真实互联网资源获取；
- P4Transformer 数据集训练结果是否达到论文指标。

这些能力可以继续运行各阶段专项测试，或在基础设施准备完成后执行本文末尾的可选验收。

---

## 二、先理解两个 Python 环境

本项目同时使用两个环境，它们的职责不同。

### 2.1 Agent 控制环境

```text
/home/tianshaoqi24/miniconda3/envs/agent
```

这个环境负责运行：

- LangGraph；
- FastAPI；
- Job Worker；
- 评测框架；
- MCP Server/Client；
- 项目 CLI。

### 2.2 论文复现环境

```text
/home/tianshaoqi24/miniconda3/envs/3d
```

这个环境只负责执行 P4Transformer 命令，例如导入 PyTorch、CUDA 扩展和训练脚本。

不要在 `3d` 环境中启动 Agent，也不要让执行器直接使用 `agent` 环境运行论文代码。后续命令统一用绝对路径变量 `AGENT_PY` 调用 Agent，避免终端实际落到 Python 3.9 或其他 Conda 环境。

---

## 三、设置本次验收变量

进入项目根目录：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
```

设置固定配置：

```bash
export PROJECT_ROOT="/data/tianshaoqi24/agent/paper_reproduction_copilot"
export AGENT_PY="/home/tianshaoqi24/miniconda3/envs/agent/bin/python"
export CONDA_EXE="/home/tianshaoqi24/miniconda3/bin/conda"

export PAPER="pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf"
export REPO="/data/tianshaoqi24/P4Transformer/"
export REPRO_CONDA_PREFIX="/home/tianshaoqi24/miniconda3/envs/3d"
export PROFILE_ID="profile-P4Transformer"
```

每次完整验收都应使用新的 `THREAD_ID`，否则旧 Checkpoint 可能让工作流从历史中断位置继续：

```bash
export ACCEPTANCE_ID="$(date +%Y%m%d-%H%M%S)"
export THREAD_ID="thread-P4Transformer-${ACCEPTANCE_ID}"
```

如果必须继续使用原来的固定 ID：

```bash
export THREAD_ID="thread-P4Transformer"
```

此时必须先执行：

```bash
"$AGENT_PY" -m app.main show-state --thread-id "$THREAD_ID"
```

若存在旧状态，优先改用新 ID。只有确认旧状态不再需要时，才可以删除对应 Checkpoint：

```bash
"$AGENT_PY" -m app.main reset-thread "$THREAD_ID"
```

`reset-thread` 会删除该线程的持久化状态，不是只读命令。

---

## 四、执行最小环境检查

### 4.1 检查文件和目录

```bash
test -d "$PROJECT_ROOT" && echo "project root: ok"
test -f "$PAPER" && echo "paper: ok"
test -d "$REPO" && echo "repository: ok"
test -x "$AGENT_PY" && echo "agent python: ok"
test -d "$REPRO_CONDA_PREFIX" && echo "reproduction conda prefix: ok"
```

五项都应输出 `ok`。

### 4.2 检查 Agent Python

```bash
"$AGENT_PY" --version
"$AGENT_PY" -m app.main version
```

Python 必须是 3.10 或更高版本。不要只运行 `python --version`，因为当前 Shell 的 `python` 可能仍指向 base 环境。

### 4.3 检查论文复现 Python

```bash
"$CONDA_EXE" run -p "$REPRO_CONDA_PREFIX" python --version
"$CONDA_EXE" run -p "$REPRO_CONDA_PREFIX" python -c \
  "import torch; print('torch=', torch.__version__); print('cuda=', torch.cuda.is_available())"
```

第二条命令只检查 PyTorch 和 CUDA 可见性，不运行训练。

### 4.4 记录仓库验收前状态

```bash
git -C "$REPO" status --short
git -C "$REPO" rev-parse HEAD
```

把输出保留在验收记录中。仓库不一定必须干净，但如果后面人工批准文件修复，必须能够区分原有修改和 Agent 修改。

---

## 五、配置 P4Transformer Execution Profile

`REPRO_CONDA_PREFIX` 只是 Shell 变量，执行器不会自动读取它。真正决定执行环境的是：

```text
config/execution_profiles.local.json
```

当前 `PROFILE_ID` 必须在这个文件的 `profiles` 数组中真实存在。可在保留已有 Profile 的前提下增加以下对象：

```json
{
  "profile_id": "profile-P4Transformer",
  "backend": "conda",
  "workspace_root": "/data/tianshaoqi24/P4Transformer",
  "artifact_root": "/data/tianshaoqi24/agent/paper_reproduction_copilot/runs",
  "conda_executable": "/home/tianshaoqi24/miniconda3/bin/conda",
  "conda_prefix": "/home/tianshaoqi24/miniconda3/envs/3d",
  "inherited_env_keys": [
    "PATH",
    "LANG",
    "LC_ALL",
    "TERM"
  ],
  "env": {
    "CUDA_VISIBLE_DEVICES": "0"
  },
  "allowed_action_env_keys": [
    "OMP_NUM_THREADS"
  ],
  "allowed_secret_env_keys": [],
  "allowed_programs": [
    "python",
    "python3",
    "torchrun",
    "pytest"
  ],
  "writable_roots": [
    "/data/tianshaoqi24/P4Transformer",
    "/data/tianshaoqi24/agent/paper_reproduction_copilot/runs"
  ],
  "network_policy": "deny",
  "enforcement_mode": "best_effort",
  "budget": {
    "max_wall_time_seconds": 3600,
    "max_cpu_seconds": 7200,
    "max_memory_bytes": 17179869184,
    "max_processes": 64,
    "max_write_bytes": 107374182400,
    "max_gpu_memory_bytes": null,
    "max_log_bytes_per_stream": 16777216,
    "max_preview_bytes": 65536,
    "sample_interval_seconds": 0.2,
    "terminate_grace_seconds": 5
  }
}
```

注意：

- `profile-P4Transformer` 是 Execution Profile ID，不是 MCP Client Profile ID；
- `network_policy=deny` 表示执行阶段不应隐式下载数据或依赖；
- Conda backend 的 `best_effort` 提供策略检查和进程监管，但不等同于 OCI 的 OS 级隔离；
- 本文不会自动替你修改这个文件，防止覆盖已有 Profile。

验证 Profile：

```bash
"$AGENT_PY" -c '
import os
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)

profile = get_execution_profile(os.environ["PROFILE_ID"])
print("profile_id=", profile.profile_id)
print("backend=", profile.backend)
print("workspace_root=", profile.workspace_root)
print("conda_prefix=", profile.conda_prefix)
print("fingerprint=", compute_execution_profile_fingerprint(profile))
'
```

预期：

```text
profile_id= profile-P4Transformer
backend= conda
workspace_root= /data/tianshaoqi24/P4Transformer
conda_prefix= /home/tianshaoqi24/miniconda3/envs/3d
fingerprint= <64位十六进制字符串>
```

如果提示 `未找到执行环境配置`，不要继续运行 Graph，应先修正 Profile 文件或 `PROFILE_ID`。

---

## 六、检查 Secret 与 Provider

当前项目使用加密 Secret Vault。`.env` 中的 Provider 地址、模型名等普通配置仍可保留，但 API Key 应通过 Secret Store 管理。

当前项目的 `.env` 仍声明了 `OPENAI_API_KEY` 和 `EMBEDDING_API_KEY` 变量。完成 Vault 迁移并确认 Provider Probe 正常后，应移除或注释其中的明文值；不要把旧 `.env` 复制进 Run、Artifact、验收记录或 Git。

### 6.1 初始化并检查 Vault

```bash
"$AGENT_PY" -m app.main init-secret-store
"$AGENT_PY" -m app.main secret-doctor
"$AGENT_PY" -m app.main list-secrets
```

如果 `OPENAI_API_KEY` 和 `EMBEDDING_API_KEY` 尚未存在，使用隐藏输入设置：

```bash
"$AGENT_PY" -m app.main set-secret OPENAI_API_KEY --use provider
"$AGENT_PY" -m app.main set-secret EMBEDDING_API_KEY --use embedding
```

`set-secret` 会要求输入两次，不要把真实 Key 写在命令参数、Markdown 或 Shell history 中。

### 6.2 探测结构化输出

先运行最小 Schema：

```bash
"$AGENT_PY" -m app.main probe-structured-output --schema minimal
```

再运行接近实验计划复杂度的 Schema：

```bash
"$AGENT_PY" -m app.main probe-structured-output --schema experiment-plan
```

这两条命令会真实调用模型，但不会读取 P4Transformer 仓库或修改文件。两次都成功，才能说明当前 Provider、模型、`STRUCTURED_OUTPUT_METHOD` 和输出预算基本兼容。

### 6.3 探测 Embedding

```bash
"$AGENT_PY" -m app.main probe-embedding
```

该命令只发送两句测试文本，不上传源码。

若要对 P4Transformer 源码启用稠密检索，还必须确认 Provider 数据策略，然后显式设置：

```bash
export ENABLE_DENSE_RETRIEVAL=true
export ALLOW_CODE_EMBEDDING_UPLOAD=true
```

如果不希望上传代码，保持 `ALLOW_CODE_EMBEDDING_UPLOAD=false`。此时完整 Graph 仍可使用稀疏检索和确定性证据链完成验收。

---

## 七、工程回归门禁

这一层用于证明代码没有明显工程回归，不应把 `pytest passed` 数量写成 Agent 效果指标。

### 7.1 Ruff

```bash
"$AGENT_PY" -m ruff check app tests
```

预期退出码为 0。

### 7.2 全量自动化测试

```bash
timeout 1200s "$AGENT_PY" -m pytest -q
```

判断标准：

- `failed=0`；
- 外部 Provider、PostgreSQL、S3、Podman 或网络测试可以按 Marker 明确跳过；
- 不能把 ImportError、依赖缺失或挂死伪装成正常跳过；
- 命令应在外层 `timeout` 前自然退出。

如果全量测试时间过长，可先运行与当前单机闭环直接相关的测试：

```bash
timeout 600s "$AGENT_PY" -m pytest -q \
  tests/test_compiled_graph_routes.py \
  tests/test_durable_checkpoint_resume.py \
  tests/test_job_graph_runner.py \
  tests/test_job_durable_resume.py \
  tests/test_role_separation_end_to_end.py \
  tests/test_chat_service.py \
  tests/test_tool_calling_loop.py \
  tests/test_mcp_contract_golden.py
```

---

## 八、运行 Agent Golden Evaluation

这一层才是简历和项目效果分析应优先使用的数据。

### 8.1 完整离线 Agent 评测

```bash
"$AGENT_PY" -m app.evaluation.run_eval run --suite offline
```

当前离线套件覆盖：

- `schema`：结构化输出和重试；
- `route`：Graph 路由；
- `tool`：工具调用边界；
- `evidence`：证据约束；
- `safety`：审批、Secret 和危险动作；
- `recovery`：租约与幂等恢复；
- `quality`：映射和结果质量；
- `efficiency`：调用次数和预算。

预期终端输出包含：

```text
passed: True
score: 1.0
baseline_diff_passed: True
```

这表示当前内部 Golden Set 没有回归，不表示对未知论文的公开 Benchmark 准确率为 100%。

### 8.2 对话与决策离线评测

```bash
"$AGENT_PY" -m app.evaluation.run_eval run --suite chat_offline
"$AGENT_PY" -m app.evaluation.run_eval run --suite decision_offline
```

`chat_offline` 重点检查引用、记忆、拒答、降级和 Prompt 预算；`decision_offline` 重点检查只读请求、操作请求和不可用操作的分类边界。

### 8.3 Provider 评测

以下命令会真实调用模型，产生费用和非确定性结果：

```bash
"$AGENT_PY" -m app.evaluation.run_eval run --suite provider
"$AGENT_PY" -m app.evaluation.run_eval run --suite chat_provider
"$AGENT_PY" -m app.evaluation.run_eval run --suite decision_provider
```

Provider 评测失败时，应先查看单个 Case 的 Observation，不能直接把它当作 Graph 功能故障。

### 8.4 查看最新评测报告

```bash
find runs -path '*/reports/eval_report.md' -printf '%T@ %p\n' \
  | sort -nr \
  | head
```

选择最新目录后：

```bash
export EVAL_RUN_DIR="/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/<agent-eval-run-id>"
jq '{suite, passed, overall_score, category_scores}' \
  "$EVAL_RUN_DIR/reports/eval_suite.json"
cat "$EVAL_RUN_DIR/reports/eval_report.md"
```

验收记录至少保存：

- Suite 名称；
- Case 数量；
- Overall Score；
- Category Scores；
- Baseline Diff；
- Git revision；
- 是否为 dirty worktree。

---

## 九、运行只读 Doctor 和本地能力检查

这些命令不会调用论文训练，也不会修改 P4Transformer 仓库。

### 9.1 Artifact、可观测性与 Readiness

```bash
"$AGENT_PY" -m app.main check-artifact-storage
"$AGENT_PY" -m app.main observability-doctor
"$AGENT_PY" -m app.main readiness-check --component api
"$AGENT_PY" -m app.main readiness-check --component worker
```

本地 SQLite、Local Blob Store 和 in-memory Observability 配置下，基础组件应为 `ready` 或有解释的 `degraded`，不应出现未捕获 Traceback。

### 9.2 Tool Contract 与 Skill

```bash
"$AGENT_PY" -m app.main validate-tool-contracts
"$AGENT_PY" -m app.main validate-skills
"$AGENT_PY" -m app.main list-skills
```

如果 `AGENT_SKILLS_ENABLED=false`，Skill 显示为 disabled 是配置结果，不是验证失败。`validate-skills` 仍应验证 Manifest、Hash、Contract 和 Eval Suite。

### 9.3 模型路由、Tool Calling 和浏览器 Agent

```bash
"$AGENT_PY" -m app.main model-routing-doctor
"$AGENT_PY" -m app.main tool-calling-doctor
"$AGENT_PY" -m app.main research-doctor
```

若对应 Feature Gate 是 `off` 或 `false`，Doctor 应明确报告 disabled，而不是假装已经启用。要验收真实 Tool Calling，后面的 Web/Chat 步骤需要设置：

```bash
export CHAT_ENABLED=true
export CHAT_TOOL_CALLING_ENABLED=true
```

### 9.4 Secret 泄漏扫描

```bash
"$AGENT_PY" -m app.main scan-secret-leaks
```

预期没有发现已知 Secret 明文。不要使用 `grep "$REAL_TOKEN"` 检查泄漏，否则 Token 会再次进入 Shell history。

### 9.5 GC 只读检查

```bash
"$AGENT_PY" -m app.main gc-summary
"$AGENT_PY" -m app.main gc-plan
```

`gc-plan` 只生成待确认计划，不执行删除。本次验收不要运行 `gc-confirm`，除非已经人工核对 Plan 中每一个 Job 和 Artifact。

---

## 十、单独验证 P4Transformer 执行边界

在运行完整 Graph 前，先确认 Conda Runner 能在指定 Profile 下工作。

### 10.1 预检一个无副作用命令

```bash
"$AGENT_PY" -m app.main run-preflight \
  "$REPO" \
  'python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"' \
  --cwd "$REPO" \
  --execution-profile "$PROFILE_ID" \
  --source inferred \
  --reason "P4Transformer acceptance environment probe"
```

检查输出中的：

- `execution_profile_id`；
- Profile Fingerprint；
- Conda Prefix；
- Program 是否为 `python`；
- CWD 是否位于 `$REPO`；
- Preflight 是否通过。

### 10.2 冒烟导入 P4Transformer 依赖

```bash
"$AGENT_PY" -m app.main run-smoke \
  "$REPO" \
  'python train-msr-small.py --batch-size 2 --help' \
  --cwd "$REPO" \
  --execution-profile "$PROFILE_ID" \
  --source script \
  --reason "P4Transformer import-only smoke test"
```

Smoke 策略会把命令中已经存在的 `--batch-size 2` 收缩为 `--batch-size 1`，然后执行 `--help`。这条命令不会加载数据集或开始训练，但 Python 在处理 `--help` 前会导入 Torch、TorchVision、THOP 和 P4Transformer 模块，因此可以发现缺失依赖或 CUDA 扩展导入问题。

可能结果：

- 返回码 0：依赖导入和参数入口可用；
- ImportError：复现环境尚未准备完成，Agent 执行边界本身可能仍正常；
- `smoke_test_status=passed`：参数收缩后的导入与参数入口验证成功；
- `smoke_test_status=failed`：查看本次 Run 下的 `execution/smoke_test_report.md` 和日志。

---

## 十一、同步 Graph 端到端成功路径

这一部分真实调用 LLM，会读取论文和仓库，但默认把最终执行命令改成无副作用的环境探测。

### 11.1 启动 Graph

```bash
"$AGENT_PY" -m app.main run-graph \
  "$PAPER" \
  "$REPO" \
  --thread-id "$THREAD_ID" \
  --execution-profile "$PROFILE_ID" \
  --goal "解析 P4Transformer，定位核心模块并验证复现环境可用性"
```

正常情况下，第一次调用会依次完成：

```text
input_validation
paper_reader
method_extractor
repo_scan
code_search
mapping
experiment_plan
command_selection_prepare
command_selection -> interrupt
```

CLI 显示“工作流运行完成”不等于 Job 已经终态。只要 `snapshot.next` 中仍有节点，就说明 Graph 正在等待恢复。

### 11.2 检查 Checkpoint

```bash
"$AGENT_PY" -m app.main show-state --thread-id "$THREAD_ID"
"$AGENT_PY" -m app.main list-checkpoints "$THREAD_ID" --limit 10
```

预期：

```text
next=('command_selection',)
```

记录首次命令输出中的 `run_id` 和 `run_dir`：

```bash
export RUN_ID="<run_graph 输出中的 run_id>"
export RUN_DIR="<run_graph 输出中的 run_dir>"
```

### 11.3 检查分析 Artifact

```bash
find "$RUN_DIR/analysis" "$RUN_DIR/planning" -maxdepth 3 -type f | sort
jq '.paper_info.title' "$RUN_DIR/analysis/paper_summary.json"
jq '.run_commands' "$RUN_DIR/planning/experiment_plan.json"
cat "$RUN_DIR/analysis/paper_code_mapping.md"
```

至少应存在：

- `analysis/paper_summary.json`；
- `analysis/method_modules.json`；
- `analysis/repo_map.json`；
- `analysis/paper_code_mapping.json`；
- `planning/experiment_plan.json`；
- `planning/command_selection_input.json`。

### 11.4 编辑命令选择文件

先查看文件：

```bash
cat "$RUN_DIR/planning/command_selection_input.json"
```

保留 `run_commands_hash`，把 `selected_index` 设为要验收的命令索引，并把该索引对应的命令改成：

```text
python -c "import torch; print('torch=', torch.__version__); print('cuda=', torch.cuda.is_available())"
```

示例结构如下，其中 Hash 必须使用文件原值：

```json
{
  "run_commands_hash": "<保留原来的64位Hash>",
  "selected_index": 0,
  "edits": [
    {
      "index": 0,
      "command": "python -c \"import torch; print('torch=', torch.__version__); print('cuda=', torch.cuda.is_available())\""
    }
  ]
}
```

不要手工重新计算 `run_commands_hash`。它绑定的是模型原始生成的整组命令，不是编辑后的单条命令。

### 11.5 恢复命令选择

```bash
"$AGENT_PY" -m app.main resume-command-selection \
  "$THREAD_ID" \
  --input "$RUN_DIR/planning/command_selection_input.json"
```

恢复后可能出现两种正常结果：

1. 低风险动作直接进入 Preflight/Smoke/Executor；
2. 风险检查要求人工审批，Graph 在 `human_review` 中断。

再次检查：

```bash
"$AGENT_PY" -m app.main show-state --thread-id "$THREAD_ID"
```

### 11.6 处理人工审批

只有当 `next` 包含 `human_review` 时才执行：

```bash
"$AGENT_PY" -m app.main resume-review \
  "$THREAD_ID" \
  --decision approved \
  --feedback "approved for bounded environment probe only"
```

如果展示的 `pending_action` 不是刚才编辑后的安全命令，应选择拒绝：

```bash
"$AGENT_PY" -m app.main resume-review \
  "$THREAD_ID" \
  --decision rejected \
  --feedback "pending action does not match reviewed command"
```

审批的对象是动作 Hash，不是模糊的“这次任务”。审批后动作发生变化时，旧审批必须失效。

### 11.7 验证终态

```bash
"$AGENT_PY" -m app.main show-state --thread-id "$THREAD_ID"
"$AGENT_PY" -m app.main show-run "$RUN_ID"
```

检查 Artifact：

```bash
find "$RUN_DIR" -maxdepth 3 -type f | sort
cat "$RUN_DIR/reports/final_report.md"
jq '.' "$RUN_DIR/reports/run_manifest.json"
```

成功路径应满足：

- `next=()`；
- `final_status=succeeded`；
- 有 Final Report 和 Run Manifest；
- Manifest 中的 Artifact 路径都位于当前 `$RUN_DIR`；
- 执行日志包含 Torch/CUDA 探测结果；
- P4Transformer 仓库没有新增 Agent 补丁。

最后再次检查仓库：

```bash
git -C "$REPO" status --short
```

---

## 十二、同步 Graph 失败诊断路径

成功路径不能证明 `executor -> debug -> repair` 路由可用，因此使用新 Thread 做一次可控失败。

```bash
export FAIL_THREAD_ID="thread-P4Transformer-failure-${ACCEPTANCE_ID}"
```

按第十一章重新运行到 `command_selection`，但将命令改成：

```text
python -c "raise RuntimeError('p4transformer acceptance failure')"
```

继续完成命令选择和必要审批。预期执行失败后进入日志诊断，并生成以下部分 Artifact：

- `execution/*.log`；
- `debug/debug_report.json`；
- `debug/debug_report.md`；
- Repair Proposal 或无法自动修复的明确结论；
- `reports/final_report.md`；
- `reports/error_report.json`。

本次故障是验收主动制造的，不代表 P4Transformer 复现失败，也不代表 Agent 基础设施失败。

若流程进入 `patch_review`：

- 检查补丁只位于隔离 Worktree；
- 检查文件数、行数、Hash 和授权边界；
- 本次验收选择 `rejected` 或 `revise`；
- 不执行 `patch_promotion=approved`。

这样可以验证文件修复审批边界，而不修改原始仓库。

---

## 十三、异步 Job、Worker 与持久化恢复

同步 Graph 验证节点逻辑；异步 Job 才是当前 Web/API 部署使用的主路径。

### 13.1 提交 Job

```bash
export JOB_THREAD_ID="job-P4Transformer-${ACCEPTANCE_ID}"

"$AGENT_PY" -m app.main submit-job \
  "$PAPER" \
  "$REPO" \
  --thread-id "$JOB_THREAD_ID" \
  --execution-profile "$PROFILE_ID" \
  --goal "P4Transformer asynchronous acceptance" \
  --idempotency-key "submit-${ACCEPTANCE_ID}"
```

记录输出中的 Job ID：

```bash
export JOB_ID="job_<输出中的32位hex>"
```

使用相同 `idempotency-key` 再提交一次时，应返回原 Job，而不是创建第二个 Job。

### 13.2 Worker 运行到第一次中断

```bash
"$AGENT_PY" -m app.main run-worker \
  --worker-id "worker-P4Transformer-${ACCEPTANCE_ID}" \
  --once
```

查看 Job：

```bash
"$AGENT_PY" -m app.main show-job "$JOB_ID"
"$AGENT_PY" -m app.main show-job-events "$JOB_ID" --limit 200
```

正常情况下，状态会变为 `waiting`，`interrupt_nodes` 包含 `command_selection`。

从 `show-job` 输出记录 `run_dir`：

```bash
export JOB_RUN_DIR="<show-job 输出中的 run_dir>"
```

### 13.3 提交命令选择 Decision

编辑：

```text
$JOB_RUN_DIR/planning/command_selection_input.json
```

同样把被选命令改为安全的 Torch/CUDA 探测，然后执行：

```bash
"$AGENT_PY" -m app.main resume-job \
  "$JOB_ID" \
  --expected-node command_selection \
  --input "$JOB_RUN_DIR/planning/command_selection_input.json" \
  --idempotency-key "command-selection-${ACCEPTANCE_ID}"
```

再次运行 Worker：

```bash
"$AGENT_PY" -m app.main run-worker \
  --worker-id "worker-P4Transformer-${ACCEPTANCE_ID}" \
  --once
```

### 13.4 提交 Action Approval

如果 Job 再次进入 `waiting` 且节点为 `human_review`：

```bash
"$AGENT_PY" -m app.main resume-job \
  "$JOB_ID" \
  --expected-node human_review \
  --decision approved \
  --feedback "approved for bounded environment probe only" \
  --idempotency-key "action-approval-${ACCEPTANCE_ID}"
```

然后再次运行 Worker：

```bash
"$AGENT_PY" -m app.main run-worker \
  --worker-id "worker-P4Transformer-${ACCEPTANCE_ID}" \
  --once
```

每次恢复前都要重新执行 `show-job`，以当前 `interrupt_nodes` 为准。不要猜测下一个节点，也不要直接修改 Job 数据库。

### 13.5 等待并检查终态

```bash
"$AGENT_PY" -m app.main wait-job "$JOB_ID" --timeout 300
"$AGENT_PY" -m app.main show-job "$JOB_ID"
"$AGENT_PY" -m app.main show-job-events "$JOB_ID" --limit 300
"$AGENT_PY" -m app.main tail-job-log "$JOB_ID" --lines 200
```

### 13.6 发布 Artifact

```bash
"$AGENT_PY" -m app.main publish-job-artifacts "$JOB_ID"
"$AGENT_PY" -m app.main check-artifact-storage
```

重复执行 `publish-job-artifacts` 不应产生不一致的重复对象。

### 13.7 验证崩溃恢复

在另一个测试 Job 上，可以在 Worker 运行时按 `Ctrl+C` 正常停止，然后重新执行：

```bash
"$AGENT_PY" -m app.main run-worker \
  --worker-id "worker-P4Transformer-recovery-${ACCEPTANCE_ID}" \
  --once
```

判断标准：

- 已提交的 Decision 不会重复生效；
- 已完成节点不会无条件重新执行；
- Job Version 和 Wait Generation 单调增加；
- 旧 Decision 或旧 Hash 会被判定为 stale；
- 不直接使用 `kill -9`，除非专门测试进程崩溃恢复并已保存诊断信息。

---

## 十四、启动 Web/API/Chat 完整服务

### 14.1 启用本地 Chat 和有界 Tool Calling

```bash
export CHAT_ENABLED=true
export CHAT_TOOL_CALLING_ENABLED=true
export AGENT_API_HOST=127.0.0.1
export AGENT_API_PORT=8000
```

当前是单机单用户验收，必须监听 loopback。远程浏览器应通过 SSH Tunnel 访问，不要直接监听 `0.0.0.0`。

`serve-stack` 的浏览器 EventSource 模式不携带 Bearer Header。如果 Vault 中存在 active 的 `AGENT_API_TOKEN`，`serve-stack` 会主动拒绝启动。先执行：

```bash
"$AGENT_PY" -m app.main list-secrets
```

若确实配置了 API Token，有两种选择：使用支持 Bearer Header 的 `serve-api` 客户端验收，或者在确认当前只做 loopback 单用户验收后撤销该 Token。不要为了通过验收删除或覆盖不属于本次测试的 Secret。

### 14.2 终端 A 启动服务栈

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

export CHAT_ENABLED=true
export CHAT_TOOL_CALLING_ENABLED=true

/home/tianshaoqi24/miniconda3/envs/agent/bin/python \
  -m app.main serve-stack \
  --host 127.0.0.1 \
  --port 8000
```

`serve-stack` 会启动 API、Job Worker 和 Resource Worker。保持终端 A 运行。

### 14.3 终端 B 检查健康状态

```bash
curl --fail --silent http://127.0.0.1:8000/healthz | jq
curl --fail --silent http://127.0.0.1:8000/livez | jq
curl --silent http://127.0.0.1:8000/readyz | jq
curl --fail --silent http://127.0.0.1:8000/v1/jobs?limit=5 | jq
```

判断标准：

- `/healthz` 返回 `status=ok`；
- `/livez` 返回 `status=alive`；
- `/readyz` 返回 `ready` 或有明确原因的 `degraded`；
- `/v1/jobs` 能看到刚才的 `$JOB_ID`。

浏览器访问：

```text
http://127.0.0.1:8000/
```

如果 `web/dist` 尚未构建且 `WEB_UI_REQUIRED=false`，API 可正常工作但首页可能没有完整前端，这不影响后端验收。

### 14.4 验证 SSE

```bash
curl --no-buffer --max-time 10 \
  "http://127.0.0.1:8000/v1/jobs/$JOB_ID/events/stream?follow=false"
```

预期返回当前事件 backlog 后主动结束，不应永久挂住。

### 14.5 验证 Artifact-grounded Chat

```bash
curl --fail --silent \
  -X POST \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: chat-status-${ACCEPTANCE_ID}" \
  -d '{"question":"当前复现任务执行到哪一步？请引用对应证据。"}' \
  "http://127.0.0.1:8000/v1/jobs/$JOB_ID/chat" \
  | jq
```

继续询问失败原因或 Final Report：

```bash
curl --fail --silent \
  -X POST \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: chat-report-${ACCEPTANCE_ID}" \
  -d '{"question":"根据已经发布的 Artifact，总结本次运行结果；没有证据的结论请明确说明不知道。"}' \
  "http://127.0.0.1:8000/v1/jobs/$JOB_ID/chat" \
  | jq
```

检查消息与 Memory：

```bash
curl --fail --silent \
  "http://127.0.0.1:8000/v1/jobs/$JOB_ID/chat/recent?limit=20" \
  | jq

curl --fail --silent \
  "http://127.0.0.1:8000/v1/jobs/$JOB_ID/chat/memory" \
  | jq
```

验收标准：

- 回答引用真实 Artifact/Job Evidence；
- 不声称执行了实际未执行的动作；
- Chat 只能提出操作请求，不能绕过 Decision Protocol 直接批准或执行；
- 使用同一 `Idempotency-Key` 重放请求时，不重复创建对话副作用；
- Tool Calling 只能访问 Catalog 中的有界只读工具。

完成后在终端 A 按 `Ctrl+C` 正常停止服务。

---

## 十五、MCP 离线契约与 Runtime 验收

这里的 `$PROFILE_ID` 与 MCP 无关。MCP 使用 `config/mcp_client_profiles.local.json` 中的 `in-memory-modern`、`in-memory-legacy` 和 `loopback-http`。

离线 Runtime 会在进程内构造只读 Export Service，但仍遵守 Feature Gate，因此先设置：

```bash
export MCP_EXPORT_ENABLED=true
export MCP_GATEWAY_ENABLED=false
```

### 15.1 MCP Stack Doctor

```bash
"$AGENT_PY" -m app.main mcp-stack-doctor
```

Doctor 只检查 SDK、Contract、Gateway 和 Export 配置，不会调用业务工具。

### 15.2 离线 Contract Evaluation

```bash
"$AGENT_PY" -m app.main mcp-contract-eval --mode offline
```

它比较实际只读 MCP Surface 与人工审核 Baseline，重点检查：

- Tool 名称；
- Input/Output Schema；
- Schema Hash；
- Resource Template；
- 禁止出现 Shell、Write、Delete、Approve 等变更型能力。

### 15.3 离线 Runtime Probe

Runtime Probe 需要已经生成并发布 Final Report 的 `$JOB_ID`：

```bash
timeout 90s "$AGENT_PY" -m app.main mcp-runtime-probe \
  "$JOB_ID" \
  --mode offline
```

预期：

- `passed=true`；
- modern 和 legacy 两个 in-memory Profile 都完成六种只读业务操作；
- 每个操作满足当前 Policy 的成功率和 P95 延迟门限；
- Report 写入 `analysis/mcp_runtime/reports/`；
- Report 不包含 Token、原始 Prompt 或任意写操作。

---

## 十六、MCP Loopback HTTP 可选验收

这一章会启动本机 MCP HTTP Server，但仍不连接公网。

### 16.1 准备 MCP Export Token

```bash
"$AGENT_PY" -m app.main init-secret-store
"$AGENT_PY" -m app.main set-secret \
  PAPER_COPILOT_MCP_EXPORT_TOKEN \
  --use mcp_export_auth
```

如果 Token 已经存在，不要重复创建；先运行：

```bash
"$AGENT_PY" -m app.main list-secrets
```

### 16.2 终端 A 启动 MCP Export

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

export MCP_EXPORT_ENABLED=true
export MCP_EXPORT_HOST=127.0.0.1
export MCP_EXPORT_PORT=8770

/home/tianshaoqi24/miniconda3/envs/agent/bin/python \
  -m app.main mcp-export-doctor

/home/tianshaoqi24/miniconda3/envs/agent/bin/python \
  -m app.main serve-mcp-export
```

### 16.3 终端 B 验证 HTTP、Contract 和 SLO

```bash
curl --fail --silent http://127.0.0.1:8770/healthz

export MCP_EXPORT_ENABLED=true
export MCP_EXPORT_HOST=127.0.0.1
export MCP_EXPORT_PORT=8770

"$AGENT_PY" -m app.main mcp-contract-candidate --include-http
"$AGENT_PY" -m app.main mcp-contract-eval --mode release

timeout 120s "$AGENT_PY" -m app.main mcp-runtime-probe \
  "$JOB_ID" \
  --mode release
```

Release Probe 应同时覆盖：

```text
in-memory-modern
in-memory-legacy
loopback-http
```

不要在没有人工核对 Candidate 的情况下执行 `mcp-contract-accept --replace`。Contract Candidate 与 Runtime Report 通过，已经足以完成本次只读验收。

在终端 A 按 `Ctrl+C` 正常停止 MCP Server。

---

## 十七、当前配置之外的可选基础设施验收

### 17.1 PostgreSQL

只有当以下配置都切换到 PostgreSQL 时运行：

```text
JOB_STORE_BACKEND=postgresql
CHECKPOINT_BACKEND=postgresql
DATABASE_URL=<通过受控配置提供>
```

命令：

```bash
"$AGENT_PY" -m app.main migrate-database
"$AGENT_PY" -m app.main check-database
```

不要为了“完整”而临时把正在使用的 SQLite 数据迁移到未备份的数据库。

### 17.2 OCI Runtime

当前 `$PROFILE_ID` 是 Conda Profile，因此下面命令不应作为基础门禁：

```bash
"$AGENT_PY" -m app.main runtime-doctor --profile-id "$PROFILE_ID"
```

它会正确提示“Profile 不是 OCI backend”。只有准备好 Digest-pinned 镜像和 OCI Profile 后，才应期望 `ready=true`。

### 17.3 受控资源获取

真实资源获取涉及网络和供应链边界。基础验收只执行：

```bash
"$AGENT_PY" -m app.main research-doctor
"$AGENT_PY" -m app.main readiness-check --component worker
```

不要用论文复现端到端验收顺便下载未知 URL、模型权重或数据集。

---

## 十八、验收结果记录模板

每次验收结束后，建议在项目内新建一份记录，至少包含：

```markdown
# P4Transformer Agent Acceptance

- acceptance_id:
- date:
- git_revision:
- dirty_worktree:
- paper:
- repository_revision:
- execution_profile_id:
- execution_profile_fingerprint:
- agent_python:
- reproduction_python:

## Engineering Gate

- ruff:
- pytest:

## Agent Evaluation

- offline_eval_id:
- offline_case_count:
- offline_overall_score:
- baseline_diff_passed:
- chat_offline_score:
- decision_offline_score:
- provider_suite_result:

## End-to-End

- sync_thread_id:
- sync_run_id:
- sync_final_status:
- async_job_id:
- async_run_id:
- async_final_status:
- command_selection_interrupted:
- human_review_interrupted:
- checkpoint_resume_verified:
- final_report_path:

## Services

- api_readiness:
- sse:
- chat_grounding:
- tool_calling:
- artifact_publication:

## MCP

- contract_offline:
- runtime_offline:
- contract_release:
- runtime_release:
- runtime_report_path:

## Known Limitations

-
```

不要只记录“成功/失败”。同时保存 Run ID、Report 路径、Git revision 和 Profile Fingerprint，后续才能复现验收环境。

---

## 十九、最终通过标准

### 19.1 基础门禁必须通过

- Agent Python 与复现 Python 职责分离；
- P4Transformer Execution Profile 能加载并生成稳定 Fingerprint；
- Secret Doctor、Artifact Storage、Observability 和 Readiness 没有未解释错误；
- Ruff 和当前环境可运行的自动化测试无失败；
- `offline` Agent Evaluation 通过 Baseline Diff；
- 同步 Graph 能到达 `command_selection`，并能从 Checkpoint 恢复；
- 安全命令经过 Risk/Review/Preflight/Executor 后生成 Final Report；
- 异步 Job 能在 Worker 中等待、恢复并进入终态；
- Job Event、Execution Log、Run Manifest 和 Artifact Catalog 可以查询；
- Chat 回答受 Artifact/Citation 约束，不能越权执行；
- MCP Offline Contract 和 Runtime Probe 通过。

### 19.2 以下结果不等于项目失败

- P4Transformer 缺少数据集；
- CUDA 扩展尚未编译；
- OCI Profile 未配置；
- PostgreSQL/S3 未启用；
- Research Browser Feature Gate 关闭；
- Skill 或 Tool Calling Feature Gate 关闭；
- Graph 正常停在 `command_selection`、`human_review`、`patch_review` 等人工中断；
- 可控失败任务最终为 `failed`，但 Debug Report 和 Final Report 完整生成。

### 19.3 以下情况属于验收失败

- 使用同一 `THREAD_ID` 却读取不到已持久化状态；
- Graph 显示完成，但中断节点和 Checkpoint 不可查询；
- 动作修改后仍复用旧 Approval Hash；
- Job 恢复后重复执行已经完成的外部副作用；
- Final Report 引用了不存在的 Artifact；
- Chat 声称执行了未执行的命令；
- Secret 明文出现在日志、State、Artifact 或 MCP Report；
- MCP Surface 暴露 Shell、Write、Delete、Approve 等变更型工具；
- 未批准 `patch_promotion` 就修改了 P4Transformer 原仓库；
- Doctor、Worker 或 MCP Probe 无限制挂起且没有超时与错误 Artifact。

---

## 二十、推荐实际执行顺序

为了减少排查范围，按下面顺序执行，不要一开始就启动完整 Graph：

```text
1. 第三至第五章：变量、路径、Python、Execution Profile
2. 第六章：Secret、Structured Output、Embedding Probe
3. 第七章：Ruff 与自动化测试
4. 第八章：Offline/Chat/Decision Golden Evaluation
5. 第九章：Doctor、Contract、Readiness、Leak Scan
6. 第十章：P4Transformer Preflight 与 Import Smoke
7. 第十一章：同步 Graph 成功路径
8. 第十二章：可控失败与 Debug 路径
9. 第十三章：异步 Job、Worker、Checkpoint 与 Artifact
10. 第十四章：Web/API/SSE/Chat/Tool Calling
11. 第十五章：MCP Offline Contract 与 Runtime
12. 第十六章：可选 Loopback HTTP MCP
```

某一层失败时先停止，不要继续批准真实训练或文件修复。这样可以判断故障究竟来自 Provider、Agent 状态机、执行环境、论文仓库，还是外部服务配置。
