# Paper Reproduction Copilot

Paper Reproduction Copilot 是一个面向机器学习论文复现任务的工程化 Agent 系统。它以论文和代码仓库为输入，将论文结构化理解、代码证据检索、论文与实现映射、实验规划、命令审批、环境预检、受控执行、失败诊断和结果归档组织为可恢复的 LangGraph 工作流。

项目同时提供 CLI、FastAPI 和本地 Web Console。用户可以创建复现任务、查看实时事件、选择或修改运行命令、完成人工审批，并在任务结束后通过带引用的 Chat Agent 查询报告、日志和 Artifact。


## 系统架构

```text
Web Console / CLI / REST API / SSE
                    |
                    v
       Job Control Plane + Decision Protocol
                    |
                    v
              LangGraph Workflow
                    |
        +-----------+------------+
        |                        |
        v                        v
Paper / Retrieval / Mapping   Authority / Risk / Review
        |                        |
        +-----------+------------+
                    v
      Preflight / Smoke / Supervised Execution
                    |
                    v
       Verifier / Debug / Bounded Repair
                    |
                    v
   Run Artifacts / Memory / Chat / Evaluation

Supporting services:
Resource Acquisition | Secret Vault | Model Gateway
Notifications        | Observability | Tool Calling / MCP
```

默认单机部署使用 SQLite、Local BlobStore 和本地 Checkpoint；同一套端口还支持 PostgreSQL 控制面、S3 兼容对象存储、OpenTelemetry 和 OCI Runtime。


## 环境要求

- Python 3.10 或更高版本
- Git
- `ripgrep`，用于代码与日志检索
- Node.js 20.19+，用于构建 Web Console
- 可访问的 OpenAI-compatible 模型服务
- 一个与 Agent 控制环境隔离的论文复现环境，例如独立 Conda Environment

PostgreSQL、S3、Podman 和 OpenTelemetry Collector 可按部署配置启用。

## 快速开始

### 1. 安装 Agent

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[api,resources,mcp,dev]"
```

确认当前解释器满足版本要求：

```bash
python --version
python -m app.main version
```

### 2. 配置运行参数

以 [.env.example](.env.example) 为模板创建 `.env`，配置模型地址、模型名、状态目录和运行策略。API Key 不写入 `.env`，而是交给项目的 Secret Vault：

```bash
python -m app.main init-secret-store
python -m app.main set-secret OPENAI_API_KEY --use provider
python -m app.main set-secret EMBEDDING_API_KEY --use embedding
python -m app.main secret-doctor
```

`set-secret` 使用隐藏输入。Embedding 不启用时可以只配置模型调用所需的 Secret。

### 3. 配置论文执行环境

编辑 [config/execution_profiles.local.json](config/execution_profiles.local.json)，为目标仓库定义 Execution Profile。Profile 负责固定：

```text
profile_id
backend 与 Conda/OCI 身份
workspace_root
允许执行的程序
允许写入的目录
网络策略
环境变量边界
CPU、内存、时间、进程和日志预算
```

在 `.env` 中设置默认 Profile，或在提交任务时使用 `--execution-profile`：

```bash
DEFAULT_EXECUTION_PROFILE=profile-P4Transformer
```

Agent 控制环境负责运行 LangGraph、API 和 Worker；论文执行环境只负责运行目标仓库命令，两者不要混用。

### 4. 构建 Web Console

```bash
cd web
npm ci
npm run build
cd ..
```

### 5. 启动单机服务

```bash
python -m app.main serve-stack \
  --host 127.0.0.1 \
  --port 8000
```

`serve-stack` 在一个进程中启动 Web/API、Job Worker 和 Resource Worker。浏览器打开：

```text
http://127.0.0.1:8000
```

本地单用户 Web 模式只监听 loopback，并使用同源 local-only 访问；该模式不在 Secret Vault 中启用 `AGENT_API_TOKEN`。浏览器位于另一台 Windows 机器时，可以建立 SSH Tunnel：

```bash
ssh -L 8000:127.0.0.1:8000 <user>@<agent-host>
```

然后在 Windows 浏览器访问 `http://127.0.0.1:8000`。

## 使用方式

### Web Console

Web Console 提供完整的交互入口：

1. 创建论文与仓库 Resource；
2. 创建复现任务并立即获得 `job_id`；
3. 通过 SSE 查看状态、日志和等待原因；
4. 选择或编辑 `run_commands`；
5. 审批高风险命令和修复提案；
6. 预览、下载或导出任务 Artifact；
7. 使用 Chat Agent 查询结果，并查看回答引用；
8. 比较历史运行，创建证据化重跑任务。

FastAPI 交互文档位于 `http://127.0.0.1:8000/docs`。

### 异步 CLI Job

异步 Job 适合长时间运行和恢复：

```bash
export PAPER="pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf"
export REPO="/data/tianshaoqi24/P4Transformer/"
export THREAD_ID="thread-P4Transformer-001"

python -m app.main submit-job \
  "$PAPER" \
  "$REPO" \
  --thread-id "$THREAD_ID" \
  --execution-profile profile-P4Transformer
```

提交结果会直接返回 `job_id`、`thread_id`、`run_id` 和 `run_dir`。Worker 可以单独启动：

```bash
python -m app.main run-worker
```

常用查询命令：

```bash
python -m app.main list-jobs --limit 20
python -m app.main show-job <JOB_ID>
python -m app.main show-job-events <JOB_ID>
python -m app.main tail-job-log <JOB_ID> --lines 100
python -m app.main wait-job <JOB_ID> --timeout 600
```

任务停在审批节点时，先通过 `show-job` 读取当前 `interrupt_nodes`、`version` 和 `wait_generation`，再提交与当前节点绑定的决定：

```bash
python -m app.main resume-job <JOB_ID> \
  --expected-node human_review \
  --decision approved \
  --expected-version <VERSION> \
  --expected-wait-generation <WAIT_GENERATION>
```

命令选择节点使用 `--input <JSON_FILE>` 提交选择和编辑结果。Web Console 会自动生成对应的结构化请求。

### 同步 LangGraph

同步入口适合学习节点流转和断点调试：

```bash
python -m app.main run-graph \
  "$PAPER" \
  "$REPO" \
  --thread-id "$THREAD_ID" \
  --execution-profile profile-P4Transformer
```

查看 Checkpoint：

```bash
python -m app.main show-state --thread-id "$THREAD_ID"
python -m app.main list-checkpoints "$THREAD_ID" --limit 5
```

同步 Graph 的命令选择、人工审批和 Patch 审批分别使用 `resume-command-selection`、`resume-review`、`resume-patch-review` 和 `resume-patch-promotion` 恢复。

## 运行产物

每次运行写入独立目录：

```text
runs/<run_id>/
  inputs/       输入请求与校验报告
  analysis/     论文结构、摘要、仓库地图、检索证据和映射结果
  planning/     实验计划、命令选择和 Preflight 报告
  execution/    进程记录、资源使用和执行日志
  repairs/      诊断、修复提案、Patch 与验证证据
  reports/      Artifact Index、Error Report、Final Report、Run Manifest
  traces/       结构化输出、错误和节点 Trace
```

关键文件包括：

- `reports/run_manifest.json`：本次运行的输入、环境、状态和 Artifact 身份；
- `reports/artifact_index.json`：Artifact 路径、类型、SHA-256 和生产节点；
- `reports/final_report.md`：面向用户的最终复现报告；
- `reports/error_report.json`：统一错误模型和阶段错误；
- `execution/process_record.json`：受监管进程的执行与资源记录。

运行状态默认集中在 `state/`，可以使用 `STATE_ROOT` 整体重定位。Artifact 和状态目录不应提交到 Git。

## 安全设计

项目将 LLM 输出视为不可信候选，而不是直接权限：

- 命令先转换为结构化 `ExecutableAction`，再经过风险策略、Hash 绑定审批、Preflight 和执行器；
- Shell 默认使用 `shell=False`，程序、参数、工作目录和环境变量分别校验；
- 高风险动作必须人工确认，过期版本或内容 Hash 会触发 stale decision；
- 文件修复先应用到隔离 Worktree，验证通过后必须经过独立 Promotion Approval 才能写回原仓库；
- 论文执行环境默认采用网络拒绝策略，资源获取由独立 Resource Worker 负责；
- Secret 通过加密 Vault 保存，日志、错误、模型上下文和 Artifact 经过统一脱敏与泄漏扫描；
- Planner、Executor 和 Verifier 权限分离，Verifier 只依据执行证据给出结论；
- Artifact、Resource、Approval、Execution Profile 和 Run 都使用确定性 Hash 建立身份链。

## 配置与部署

主要配置入口：

| 文件或变量 | 作用 |
|---|---|
| `.env` | 模型、状态目录、Feature Policy、超时和预算 |
| `config/execution_profiles.local.json` | 论文执行环境和资源边界 |
| `config/model_routing_policy.json` | 模型选择、质量等级和成本预算 |
| `config/retrieval_policy.json` | 检索 Profile、Shadow/Active 策略 |
| `config/research_browser_policy.json` | 外部研究来源、主机和预算策略 |
| `config/mcp_gateway_policy.example.json` | MCP Client Gateway 只读策略模板 |
| `STATE_ROOT` | SQLite、Checkpoint、Cache、Memory 和审计状态根目录 |
| `RUNS_DIR` | Run-Native Artifact 根目录 |

运行环境组合：

```text
单机开发：SQLite + Local BlobStore + Conda Profile
共享控制面：PostgreSQL + Shared Checkpoint
对象存储：S3-compatible BlobStore
强运行隔离：Podman/OCI + Immutable Environment Identity
可观测部署：OpenTelemetry + OTLP Collector
```

## 测试与评测

运行不访问模型 Provider 的工程回归：

```bash
python -m pytest -m "not provider" -q
python -m ruff check app tests
```

运行离线 Agent Golden Evaluation：

```bash
python -m app.evaluation.run_eval run --suite offline
```

运行单个 Case：

```bash
python -m app.evaluation.run_eval run \
  --suite offline \
  --case-id route_executor_failure_to_debug
```

真实模型评测使用显式 Provider Suite：

```bash
python -m app.evaluation.run_eval run \
  --suite provider \
  --no-fail-on-regression
```

评测产物同样写入独立 Run，并保留 Case 观察、评分、基线差异和 Manifest，便于区分工程测试通过与 Agent 行为质量。

## 项目结构

```text
app/
  nodes/               LangGraph 业务节点
  paper/               PDF 解析、章节识别、证据和摘要归并
  retrieval/           仓库索引、混合检索、Dense Cache 和策略优化
  execution/           Profile、Runner、Supervisor、OCI 与进程记录
  job_runtime/         异步 Job、Lease、Heartbeat 和恢复
  resources/           受控外部资源获取与 Resource Manifest
  authority/           Planner/Executor/Verifier 权限边界
  chat/                Artifact Grounded Chat 与上下文管理
  failure_memory/      可信失败案例与诊断检索
  project_memory/      项目长期事实与可撤销治理
  knowledge_base/      跨论文证据知识库
  model_routing/       模型策略、预算和调用账本
  research_browser/    受限研究浏览与证据归档
  tool_calling/        有界工具调用与复现编排
  skills/              Agent Skill/Plugin Registry
  mcp_gateway/         只读 MCP Client Gateway
  mcp_export/          只读 MCP Server Export
  evaluation/          Golden Cases、Runner、Scorer 和 Baseline
  api/                 FastAPI、SSE 和 Web 托管
web/                   React Web Console
config/                Execution、Retrieval、Model、Browser 和 MCP Policy
alembic/               PostgreSQL Schema Migration
state/                 本地运行状态
runs/                  Run-Native Artifacts

