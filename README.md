# Paper Reproduction Copilot

基于 LangGraph 的论文复现 Agent。项目将论文理解、代码映射、实验规划、
受监管执行、失败诊断、人工审批和文件修复组织为可恢复工作流。


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
