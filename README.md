# Paper Reproduction Copilot

基于 LangGraph 的论文复现 Agent。项目将论文理解、代码映射、实验规划、
受监管执行、失败诊断、人工审批和文件修复组织为可恢复工作流。

## 持续维护文档

- [全阶段功能与技术总览](a_implementation_guides/project_phase_capability_summary.md)：
  汇总基础 00、V0-V7 和 Phase 1 至当前阶段的功能、技术、核心思路、流程和关键产物。
- [Python 源码功能参考](a_implementation_guides/python_source_code_reference.md)：
  汇总项目 Python 文件、类、函数/方法、简化伪代码以及输入输出示例。

后续每次新增或调整功能，都必须同步更新这两份文档：阶段总览负责说明“为什么做、如何串联”，
源码参考负责说明“代码在哪里、函数如何调用”。如果入口命令、API、测试方式或 Artifact
发生变化，还要同步更新本 README。

## 目录结构

```text
state/              # 运行时状态（SQLite + 模块状态目录，不提交 Git）
  cache/            #   嵌入向量缓存
  chat/             #   对话记忆
  checkpoints/      #   LangGraph checkpoint（业务状态）
  control/          #   MCP / 模型路由 / 研究浏览审计库
  failure_memory/   #   失败案例记忆
  jobs/             #   任务队列与 worker 会话
  notifications/    #   通知投影
  project_memory/   #   项目长期事实
  rerun/            #   可信重跑提案
  resources/        #   受控资源目录 + 目录库
  retention/        #   保留 / GC 审计账本
  secrets/          #   加密 Secret Vault
  storage/          #   Artifact 目录库 + Blob
  acceptance/       #   手工验收工作区（含独立线程状态）
runs/               # 每次 run 的输出（可读索引见 runs/INDEX.md）
outputs/            # 精选产物归档（历史 run 的最终产物快照）
```

运行时 SQLite 统一位于 `state/` 下，可通过环境变量 `STATE_ROOT` 整体重定位；
单个 DB 仍可用原有 `CHECKPOINT_DB_PATH`、`JOB_DB_PATH` 等变量单独覆盖。
`state/` 整体不提交 Git。

## 当前 MCP 阶段

Phase 55 的 MCP Surface Snapshot、Client Profile、Candidate/Baseline、Golden Eval 与 Readiness，
以及 Phase 56 的 MCP Runtime Probe、运行报告、升级比较和有界调用源码已经实现。Phase 55 当前九组专项
测试为 `26 passed`；真实 HTTP `tools/call` 的完整闭环仍需结合 Runtime 专项测试和运行报告判断，不能只凭
目录发现测试宣称全部 MCP Runtime 能力已经通过。

- [Phase 55 契约评测教程](a_implementation_guides/66_phase_55_mcp_interoperability_contract_eval_and_single_host_operations.md)
- [Phase 56 业务调用可靠性、SLO 与 SDK 升级演练教程](a_implementation_guides/67_phase_56_mcp_invocation_reliability_slo_and_sdk_upgrade_rehearsal.md)

- [Phase 47-56 Python 源码函数参考](a_implementation_guides/python_source_code_reference_phase_47_56.md)

Phase 56 的实现重点是有界 async handler、modern/legacy/loopback HTTP 六操作矩阵、Runtime Report
与升级比较门禁；后续若继续扩展 MCP 能力，仍需同步更新源码参考分册和阶段总览。

## Agent Regression Evaluation

Phase 17 将确定性离线回归与真实模型评测分开：

```bash
# 普通测试不访问模型 Provider
python -m pytest -m "not provider" -q

# 运行全部 Offline Golden Cases
python -m app.evaluation.run_eval run --suite offline
```

Offline Suite 只允许 `fixture` 和 allowlist 中的 `route_function`，覆盖：

```text
Schema / Route / Tool / Evidence
Safety / Recovery / Quality / Efficiency
```

第一次建立或人工接受新的离线基线：

```bash
python -m app.evaluation.run_eval run \
  --suite offline \
  --update-baseline
```

只调试一个 Case：

```bash
python -m app.evaluation.run_eval run \
  --suite offline \
  --case-id route_executor_failure_to_debug
```

`--case-id` 不能和 `--update-baseline` 一起使用。baseline 更新路径必须位于
`app/evaluation/baselines/`，失败 Suite 不会覆盖已有 baseline。

真实 Provider Suite 必须显式运行：

```bash
python -m app.evaluation.run_eval run \
  --suite provider \
  --no-fail-on-regression
```

第一版 Provider Runner 不接受 scripted approval/resume，会停在首次 interrupt，
