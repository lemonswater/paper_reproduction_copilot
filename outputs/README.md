# outputs/ 精选产物归档

本目录存放**精选产物快照**——从 run 中挑选出的、值得长期保留的最终产物
（如 `experiment_plan.json`、`paper_summary.json`、`repo_map.json`、
`paper_code_mapping.json` 等），用于跨 run 对比和人工查阅。

与 `runs/` 的区别：

- `runs/<run-id>/`：每次 run 的完整输出（analysis/execution/planning/reports 等），保留全量过程。
- `outputs/`：只保留人工精选的最终产物快照，通常是某个 run 结束后显式导出到这里。

当前目录内容为空；git 历史中曾跟踪过以下精选产物：
`experiment_plan.json`、`experiment_plan.md`、`method_modules.json`、
`paper_code_mapping.json`、`paper_code_mapping.md`、`paper_summary.json`、
`repo_map.json`、`repo_summary.md`。
