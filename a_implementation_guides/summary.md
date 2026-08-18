# 25. Phase 14：Graph 与文件修复安全闭环总结

## 一、文档目的

Phase 14 的目标不是继续增加新的 Agent 能力，而是把 Phase 13 已经实现的文件
修复链真正收紧成一条：

```text
路由唯一
  -> 结构化输出可重试、可降级
  -> Patch 身份可验证
  -> 隔离环境中运行行为测试
  -> 人工批准后才能修改原仓库
  -> Apply 可并发互斥、可崩溃恢复
  -> 修改后重新审批并执行
```

本阶段的问题并不是一次性出现的，而是随着单元测试、静态检查和真实 PSTNet
端到端验收逐步暴露。本总结按照问题实际出现的先后顺序记录：

- 当时看到的现象。
- 真正的根因。
- 最终采用的解决方案。
- 应该如何验证。
- 以后遇到同类问题时应优先检查什么。

其中，早期多次出现的“LLM 返回内容与 Pydantic Schema 不匹配”虽然主要在
Phase 12 处理，但它直接影响 Phase 14 的 Debug、Repair 和 File Repair 链，
因此也放在本总结最前面统一复盘。

---

## 二、最终安全闭环

完成 Phase 14 后，文件修复主链应当是：

```text
executor failed
    ↓
log_debug
    ↓
repair_planner
    ├── edit_command -> 有界命令修复
    ├── no_repair -> final_report
    └── manual_only + 源码证据
                    ↓
            file_repair_planner
                    ↓
               patch_builder
                    ↓
        patch_review interrupt
                    ↓ approved
             patch_verifier
          （隔离 worktree）
                    ↓
    behaviorally_verified
                    ↓
 patch_promotion_review interrupt
                    ↓ approved
               patch_apply
                    ↓
        重新生成 action/hash
                    ↓
           human_review
                    ↓ approved
  preflight -> smoke -> executor
                    ↓
        final_report/run_manifest
```

这里有三次不同含义的人工确认：

1. `human_review`：批准执行一条具体命令。
2. `patch_review`：只批准在隔离 worktree 中验证一份具体 Patch。
3. `patch_promotion_review`：Patch 已通过行为测试后，批准将同一份 Patch
   应用到原始仓库。

这三次批准不能合并，也不能复用旧的审批结果。

---

## 三、问题时间线与解决方案

### 1. 最早的 `PaperSummary` Schema 不匹配

#### 现象

读取论文时出现：

```text
ValidationError: 4 validation errors for PaperSummary
research_problem
  Field required
core_idea
  Field required
datasets.0
  Input should be a valid string
datasets.1
  Input should be a valid string
```

模型返回了 `paper_info` 等自定义层级，并把 `datasets` 返回成对象列表；程序的
`PaperSummary` 却要求顶层存在：

```text
research_problem
core_idea
datasets: list[str]
```

#### 根因

LLM 理解了任务语义，但没有严格遵守程序定义的字段名和字段类型。自然语言 Prompt
只能提高格式正确率，不能代替运行时 Schema 校验。

#### 解决方案

第一步是让 Prompt 中的 JSON 示例与 `PaperSummary.model_json_schema()` 完全
一致，不能自己发明 `paper_info` 之类的新层级。

第二步是使用：

```python
structured_llm = llm.with_structured_output(
    PaperSummary,
    include_raw=True,
)
```

第三步仍然要执行本地 Pydantic 校验，不能因为调用了
`with_structured_output()` 就默认结果一定合法。

#### 复盘结论

```text
Prompt 描述的是期望
Schema 定义的是程序契约
Pydantic 校验的是模型是否真的履约
```

三者缺一不可。

---

### 2. Prompt 中 JSON 大括号与 `.format()` 冲突

#### 现象

为了增强结构约束，在 `PAPER_SUMMARY_PROMPT` 中直接加入 JSON 示例后，出现：

```text
NameError: name 'paper_text' is not defined
```

或者 `.format(paper_text=paper_text)` 把 JSON 大括号识别成格式占位符。

#### 根因

Python 的 `str.format()` 会把单个 `{...}` 当作格式字段。Prompt 中既有真正的
`{paper_text}`，又有 JSON 对象的大括号，如果没有转义，二者会发生冲突。

如果进一步错误地把 Prompt 改成模块级 f-string，那么模块加载时就会立刻求值
`paper_text`；此时函数局部变量尚不存在，就会抛出 `NameError`。

#### 解决方案

保留真正的动态占位符：

```text
{paper_text}
```

JSON 示例中的字面量大括号写成：

```text
{{
  "research_problem": "..."
}}
```

不要把依赖函数局部变量的 Prompt 写成模块级 f-string。

#### 复盘结论

Prompt 模板失败与 LLM 无关。遇到模型请求尚未发出就出现 `NameError`、
`KeyError` 或格式化异常时，应先检查 Python 字符串模板，而不是调模型参数。

---

### 3. `ExperimentPlan` 返回自然语言而不是合法 JSON

#### 现象

实验计划阶段出现：

```text
ValidationError: Invalid JSON: key must be a string
input_value='{plan}\n\n# P4Transformer...'
```

模型返回了 Markdown、解释文字或字面量 `{plan}`，而不是
`ExperimentPlan` 所需的 JSON 对象。

#### 根因

仅在 Prompt 中写“请返回 JSON”约束不够强。模型可能把示例占位符原样输出，
或者在 JSON 前后增加解释性文字。

#### 解决方案

Prompt 中明确要求：

- 只输出一个 JSON 对象。
- 不使用 Markdown 代码块。
- 不在 JSON 前后添加说明。
- 字段、类型和枚举必须与 Schema 一致。
- 不确定时使用空列表、`null` 或 Schema 允许的保守值。

同时继续使用 structured output 和 Pydantic 校验。

#### 复盘结论

增强 Prompt 有帮助，但仍不能把“输出格式可靠性”完全交给模型。

---

### 4. `DebugReport` 缺少必填字段

#### 现象

执行 `plan-repair` 时出现：

```text
ValidationError: 1 validation error for DebugReport
error_type
  Field required
```

模型给出了 `diagnosis` 等自然语言字段，却漏掉了程序要求的 `error_type`。

#### 根因

模型对“诊断结果”的语义理解与程序对象的字段定义不一致。即使文本内容看起来
合理，只要字段名不一致，后续节点就无法稳定路由。

#### 解决方案

- Prompt 使用 `DebugReport` 的真实字段。
- 用 Pydantic 校验必填字段。
- 校验失败后携带具体 ValidationError 做有限重试。
- 多次失败后返回保守 DebugReport，而不是让整个 Graph 异常退出。

#### 复盘结论

Agent 中的结构化对象不仅用于展示，还用于路由。缺失 `error_type` 不是排版问题，
而是控制流输入不完整。

---

### 5. `RepairProposal` 结构错误后直接降级为 `no_repair`

#### 现象

模型识别出了 `cuda_oom`，但最终结果是：

```json
{
  "kind": "no_repair",
  "summary": "模型的 repair proposal 未通过结构校验，已安全降级。",
  "root_cause": "模型输出不符合 RepairProposal schema。"
}
```

后续真实验收中还出现过：

- 缺少 `summary` 或 `root_cause`。
- `step_type` 返回 `manual_review`、`manual_modification` 等未定义值。
- `risk` 返回自由文本而不是 `low | medium | high`。
- `kind=edit_command`，但 `repaired_command=null`。

#### 根因

当时的流程是：

```text
模型返回
  -> Pydantic 失败
  -> 立即 no_repair
```

它能保证安全，但对可以通过一次格式纠正修复的小错误过于保守。

#### 解决方案：建立完整的结构化输出可靠链

Phase 12 将调用升级为：

```text
确定性规则优先
        ↓
json_schema + strict=True
        ↓
Pydantic 结构校验
        ↓
Pydantic 语义校验
        ↓ 失败
携带具体 validation error 重试 1～2 次
        ↓ 仍失败
确定性 fallback / no_repair
        ↓
保存每次 attempt artifact
```

核心工具是：

```text
app/tools/structured_output_tools.py
```

核心函数包括：

- `invoke_structured_with_retry()`：统一结构化调用、校验、有限重试和 trace。
- `_build_validation_retry_prompt()`：把具体校验错误反馈给模型。
- 节点自己的 fallback：根据业务语义返回安全降级结果。

#### 为什么仍然需要 fallback

`strict=True` 不是绝对保证：

- Provider 可能不完整支持 `json_schema strict`。
- OpenAI 兼容服务可能只接受参数，但没有真正执行严格约束。
- Schema 合法不等于业务语义合法。
- 网络、超时和 Provider 异常不属于格式重试能解决的问题。

所以最终策略必须是：

```text
强约束 + 本地验证 + 有限重试 + 安全降级
```

而不是无限重试，或者把不合法结果直接交给执行节点。

#### 复盘结论

模型格式错误既不能直接放行，也不必第一次失败就永久放弃。最稳妥的边界是：

```text
允许少量、有证据、可观察的格式纠正
超过预算后立即降级
永远不把未通过本地 Schema 的对象交给副作用节点
```

---

### 6. Phase 14 开始时发现 Graph 路由可能重复

#### 现象

检查 `app/graph.py` 时发现：

- 某些 route 函数可能重复定义。
- `log_debug` 同时存在条件边和无条件 `final_report` 边。
- 路由返回值没有明确的有限集合。
- 条件边没有显式 `path_map`。

这会导致同一个节点可能同时向多个后继节点写 state，严重时出现：

```text
INVALID_CONCURRENT_GRAPH_UPDATE
```

#### 根因

随着阶段不断追加节点和边，旧路由没有完整清理。LangGraph 的条件边不是普通
`if/else` 注释，而是实际控制流；一条遗留无条件边就可能让两个分支同时运行。

#### 解决方案

在 `app/graph.py` 中：

- 每个 route 函数只保留一个定义。
- 删除错误的无条件边。
- 为路由声明 `Literal[...]` 返回类型。
- 为所有条件边增加显式 `path_map`。
- 允许测试注入内存 Checkpointer。
- 增加编译图拓扑测试和真实 StateGraph 路由测试。

例如：

```python
def route_after_patch_verifier(
    state: ReproductionState,
) -> Literal["patch_promotion_review", "final_report"]:
    ...
```

#### 复盘结论

Graph 代码必须当作控制流代码审查，不能只检查节点函数本身是否正确。

---

### 7. `passed` 无法表达“只通过语法”与“行为正确”的区别

#### 现象

Phase 13 的 Patch Verification 使用宽泛的 `passed`。但 Patch 能应用、文件能
编译，并不代表修复后的行为正确。

#### 风险

如果没有运行任何目标测试，只做了：

- `git apply --check`
- Hash 校验
- Python 语法检查

就允许 Promotion，Agent 可能把一个“语法正确但行为错误”的 Patch 写回原仓库。

#### 解决方案

重新定义验证状态：

```text
behaviorally_verified
structurally_valid
failed
blocked
```

只有满足下面所有条件时才能：

```text
status=behaviorally_verified
promotion_allowed=true
```

条件包括：

- 所有结构检查通过。
- 至少运行一个可信行为测试。
- 所有已运行行为测试全部通过。

没有行为测试时最多只能是：

```text
status=structurally_valid
promotion_allowed=false
```

#### 复盘结论

```text
能应用 != 能运行
能运行 != 行为正确
行为正确 != 已获准写回原仓库
```

这三层状态必须分开表达。

---

### 8. Verification Hash 只保存、不在边界重新计算

#### 现象

如果验证完成后，有人修改了：

- Patch 文件。
- Verification Report。
- Execution Profile。
- State 中的 Patch 身份。

旧的 Promotion 审批仍有可能被错误复用。

#### 根因

只比较 state 中已经保存的 Hash，相当于相信旧结论；没有从当前 artifact 内容
重新计算事实，无法防止审批与执行之间的 TOCTOU 问题。

#### 解决方案

增加并复用：

- `compute_verification_hash()`
- `validate_verification_hash()`
- `validate_patch_promotion_authorization()`

在 Promotion 和 Apply 两个信任边界都重新检查：

- `patch_id`
- `patch_sha256`
- `verification_sha256`
- Verification 状态
- `promotion_allowed`
- Execution Profile ID 和 fingerprint
- Promotion Record 是否绑定同一份 Patch 和 Report

#### 复盘结论

审批记录不是“批准过”这个布尔值，而是：

```text
某个人在某个时间
批准了某个 hash 对应的具体对象
```

对象变化后，旧审批必须失效。

---

### 9. 复用 Worktree 时只检查目标文件不够安全

#### 现象

相关测试最初失败：

```text
test_reused_worktree_rejects_staged_change
test_reused_worktree_rejects_missing_target
test_reused_worktree_rejects_changed_head
```

#### 根因

复用 worktree 时，如果只检查 Patch 目标文件，可能遗漏：

- 额外 tracked 修改。
- staged 修改。
- worktree HEAD 已变化。
- Patch 目标文件缺失。
- 实际 diff 范围超出 Patch Bundle。

#### 解决方案

`validate_worktree_matches_patch()` 统一检查：

- Worktree HEAD 是否仍等于预期 base commit。
- 是否存在 staged changes。
- 所有 Patch 目标文件是否存在。
- 完整 tracked diff 集合是否与 Patch Bundle 文件集合完全一致。
- Worktree diff hash 是否匹配。

#### 复盘结论

验证隔离目录时不能只证明“目标文件看起来正确”，还要证明“没有其他文件被偷偷
改变”。

---

### 10. 中文错误信息导致 `pytest.raises(..., match=...)` 不匹配

#### 现象

Worktree 负例测试使用：

```python
with pytest.raises(ValueError, match="staged changes"):
    ...
```

实现如果抛出中文错误信息，异常类型虽然正确，测试仍然失败：

```text
AssertionError: Regex pattern did not match
```

#### 根因

`pytest.raises()` 不只检查有没有抛出 `ValueError`。指定 `match` 后，还会对
异常文本做正则匹配。

#### 解决方案

安全边界的底层错误信息采用稳定、可检索的英文短语，例如：

```text
patch worktree contains staged changes
patch worktree target is missing
patch worktree HEAD changed
```

面向用户的中文解释可以放在 CLI 或报告层，不要让底层错误契约频繁变化。

#### 复盘结论

错误信息在测试和调用方依赖它时，也是接口契约的一部分。

---

### 11. `@contextmanager` 返回类型触发 basedpyright 弃用提示

#### 现象

`app/tools/repository_lock_tools.py` 中出现：

```text
Annotating the return type as -> Iterator[Foo] with @contextmanager
is deprecated. Use -> Generator[Foo] instead.
```

#### 根因

`@contextmanager` 装饰的函数本质上是生成器。新版 basedpyright 希望精确写出：

```python
Generator[YieldType, SendType, ReturnType]
```

#### 解决方案

修改为：

```python
from typing import Generator


@contextmanager
def acquire_repository_lock(...) -> Generator[str, None, None]:
    ...
```

#### 复盘结论

这是静态类型层面的修正，不是运行时锁逻辑失效，也不应该通过关闭
`reportDeprecated` 来掩盖。

---

### 12. Patch Apply 缺少跨进程互斥和崩溃恢复

#### 现象

两个不同 `thread_id` 的 Graph 可以同时操作同一个论文仓库。另一个问题是：

```text
git apply 已成功
但 checkpoint 写入前进程崩溃
```

恢复后如果再次盲目 `git apply`，会出现冲突；如果直接认为失败，又会丢失实际
已经完成的副作用。

#### 根因

LangGraph Checkpoint 只能隔离 Graph State，不能自动隔离外部共享仓库，也不能
让 Git 写操作天然具备事务语义。

#### 解决方案

增加两层机制。

第一层是 Repository Lock：

```text
app/tools/repository_lock_tools.py
```

`acquire_repository_lock()` 使用跨进程排他锁，保证同一仓库同一时刻只有一个
Patch Apply。

第二层是 Write-Ahead Journal：

```text
prepared
  -> applying
  -> applied
```

Apply 恢复时通过文件 Hash 和仓库 diff 判断：

```text
before   -> 可以执行 apply
after    -> 已执行成功，恢复 application record
conflict -> 停止并要求人工介入
```

#### 复盘结论

Checkpoint 解决“Agent 记得什么”，Repository Lock 解决“谁能修改共享资源”，
Journal 解决“副作用发生到哪一步”。三者职责不同。

---

### 13. `export` 环境变量后没有自动出现目录

#### 现象

执行：

```bash
export SESSION_ROOT="/data/tianshaoqi24/pstnet-phase14-direct"
export OUTPUT_DIR="$SESSION_ROOT/outputs"
```

之后，在文件管理器里看不到对应目录。

#### 根因

`export` 只是在当前 shell 中设置字符串变量，不会创建任何文件或目录。

#### 解决方案

显式执行：

```bash
mkdir -p \
  "$SESSION_ROOT/home" \
  "$SESSION_ROOT/tmp" \
  "$SESSION_ROOT/cache" \
  "$SESSION_ROOT/checkpoints" \
  "$OUTPUT_DIR" \
  "$RUNS_DIR" \
  "$PATCH_COORDINATION_DIR"
```

#### 复盘结论

配置路径与创建路径是两个动作。看到变量值正确，不代表路径已经存在。

---

### 14. Agent 环境与允许写入根目录发生冲突

#### 现象

路径守卫报告：

```text
ERROR: sys.executable is outside /data/tianshaoqi24
```

实际 Agent 解释器解析为：

```text
/data2t/home/tianshaoqi/miniconda3/envs/agent/bin/python3.10
```

论文复现环境则是：

```text
/home/tianshaoqi24/miniconda3/envs/3d
```

#### 根因

最初把“所有新增写入必须位于 `/data/tianshaoqi24`”错误扩大成了“Python
解释器本身也必须位于该目录”。但 Agent 环境是受信任的只读运行时，并不需要
在验收过程中写入。

#### 解决方案

将环境职责拆开：

```text
Agent 环境：
    运行 app.main、LangGraph、Pydantic 和 LLM 调用
    可以位于 /home 或 /data2t
    只读使用，不安装依赖

3d 复现环境：
    运行 preflight、pytest、smoke、executor、patch verifier
    通过 Conda Execution Profile 调用

可写 artifact/cache/checkpoint：
    全部重定向到 /data/tianshaoqi24 下的 SESSION_ROOT
```

路径守卫只检查可能写入的路径。Agent 解释器使用精确 prefix 校验，而不是要求
它位于可写根目录内。

#### 复盘结论

安全边界应区分：

```text
允许读取的受信任运行时
允许写入的受控目录
允许执行论文命令的隔离环境
```

不能用一个根目录规则替代三种不同权限。

---

### 15. 临时创建 Agent 虚拟环境并不是最佳方案

#### 现象

为了满足路径守卫，曾尝试：

```bash
python -m venv "$AGENT_VENV"
source "$AGENT_VENV/bin/activate"
python -m pip install --no-user -e "$PROJECT_ROOT[dev]"
```

这会重复安装项目依赖，可能受网络、磁盘、编译依赖和版本差异影响。

#### 根因

试图通过复制运行环境解决权限模型问题，增加了不必要的环境漂移。

#### 解决方案

继续使用已经可工作的 `agent` 环境作为精确受信任的只读运行时，并把缓存、
临时目录和输出重定向到 `SESSION_ROOT`。

如果误进入临时 venv，执行：

```bash
deactivate
```

#### 复盘结论

已有稳定环境时，优先隔离写入位置，不要为了路径形式重新构建整套环境。

---

### 16. PSTNet 仓库最初没有可验证的 Git Baseline

#### 现象

执行：

```bash
git -C "$REPO" status --short --branch
```

看到大量：

```text
?? README.md
?? modules/
?? train-msr.py
...
```

#### 根因

仓库文件存在，但没有形成明确的 tracked baseline。Patch Builder、Worktree 和
Apply 恢复都依赖 Git 对“修改前状态”的确定性描述。

#### 解决方案

在确认仓库来源和文件内容正确后，建立一次明确 baseline commit，并记录 commit
SHA。后续每轮验收都从同一 baseline 开始。

#### 复盘结论

文件修复 Agent 的前提不是“目录里有代码”，而是：

```text
有明确 base commit
tracked tree 干净
修改范围可计算
```

---

### 17. 第一次真实论文分析触发 `PaperSummary` fallback

#### 现象

真实运行结果出现：

```text
succeeded: False
fallback_used: True
experiment_settings: []
method_modules: 0
```

#### 根因

真实 PSTNet 论文触发了比单元测试更复杂的模型输出。Prompt 示例中的
`experiment_settings` 等字段与 Schema 仍存在形状差异，导致结构化校验失败。

#### 解决方案

- 直接对照 `PaperSummary.model_json_schema()` 修正 Prompt。
- 在正式启动 Graph 前增加最小真实模型 Probe。
- 检查 structured output attempt artifact，而不是只看最终 fallback。
- 保留 fallback，避免分析节点异常导致整个 Graph 崩溃。

#### 复盘结论

单元测试可以证明 fallback 正确，但只有真实模型 Probe 才能证明 Prompt、
Provider 和 Schema 在当前环境里能够协作。

---

### 18. 第一次命令审批后被 `torch_import_probe` 阻止

#### 现象

状态显示：

```text
final_status="blocked"
error="预检阻止执行：torch_import_probe"
```

#### 根因

执行命令绑定的 Execution Profile 与真正具备 Torch、pytest 和论文依赖的环境
不一致，或者 `3d` 环境缺少验收所需的测试工具。

#### 解决方案

- Execution Profile 使用 `backend=conda`。
- `conda_prefix` 精确指向 `3d` 环境。
- 在 `3d` 环境中验证：

```bash
"$CONDA_EXECUTABLE" run \
  --no-capture-output \
  -p "$REPRO_CONDA_PREFIX" \
  python -c "import torch; print(torch.__version__)"
```

- 在同一环境验证 `pytest`。
- 只补充复现环境真正缺少的依赖，不把 Torch 安装到 Agent 环境来绕过预检。

#### 复盘结论

Preflight 阻断不是 Agent 故障，而是在副作用发生前证明“这条命令将在什么环境
运行”。不能通过跳过检查来修复环境绑定错误。

---

### 19. `direct-002`：结构化调用在 `invoke()` 内直接抛出 ValidationError

#### 现象

受控 `shape_mismatch` 已被正确识别，但最终：

```text
repair_kind="no_repair"
```

Structured trace 显示模型第一次返回缺少字段或枚举不合法，但没有进入预期的
校验重试。

#### 根因

原来的 `invoke_structured_with_retry()` 只处理：

```text
invoke 成功
  -> 读取 parsed
  -> schema.model_validate(parsed) 失败
```

但某些 LangChain/Provider 组合会在：

```python
structured_llm.invoke(current_prompt)
```

内部就执行 Pydantic 校验并直接抛出 `ValidationError`。由于异常发生得更早，
原来的重试逻辑没有捕获它。

#### 解决方案

在 `invoke_structured_with_retry()` 的 `invoke()` 边界直接捕获 Pydantic
`ValidationError`：

```python
try:
    response = structured_llm.invoke(current_prompt)
except ValidationError as exc:
    # 记录 validation_error
    # 构造 retry prompt
    # 在预算内重试
```

普通网络/API/Provider 异常仍作为 `invoke_error`，不把所有异常都误当成格式错误
重试。

同时在 Repair Prompt 中显式限制：

```text
step_type = edit_command | manual_check | rerun_smoke | rerun_full
risk = low | medium | high
```

#### 复盘结论

`include_raw=True` 便于查看 raw/parsed/parsing_error，但不能保证调用永远以普通
返回值结束。可靠工具必须覆盖“调用内部已抛出 ValidationError”这条路径。

---

### 20. `direct-003`：Debug 只返回测试文件，遗漏真正源码

#### 现象

状态为：

```text
debug_error_type="shape_mismatch"
debug_related_files=["tests/test_phase14_demo.py"]
repair_kind="manual_only"
file_repair_kind="manual_only"
verification_targets=[]
```

但真实 traceback 明确包含：

```text
tests/test_phase14_demo.py
phase14_demo.py
```

#### 根因

`DebugReport.related_files` 完全依赖 LLM 语义提取。模型保留了测试入口，却遗漏了
真正抛异常的实现文件，导致 File Repair Planner 没有可安全修改的源码上下文。

#### 解决方案

在 `app/tools/log_tools.py` 增加：

```python
extract_repo_traceback_paths()
```

它确定性解析：

- Python traceback 的 `File "...", line N`。
- pytest 的 `path.py:N:`。

并只保留：

- 真正存在的文件。
- `.py` 文件。
- `resolve()` 后仍位于论文仓库内的文件。

`log_debug_node` 再把确定性路径放在前面，与模型结果去重合并：

```text
traceback 内可信文件
  + LLM 补充的语义相关文件
```

#### 复盘结论

日志里已经存在的文件路径属于确定性证据，不应该重新交给 LLM 猜测。

---

### 21. `shape_mismatch` 已有源码证据，却仍可能停在命令修复

#### 现象

错误已经定位到仓库源码，但 Repair Planner 仍可能依赖 LLM 自由选择
`no_repair`、`manual_only` 或非法枚举，无法稳定移交文件修复链。

#### 根因

一个已经有明确本地分类和源码证据的安全路由，仍被建模成概率决策。

#### 解决方案

在 `repair_planner_node.py` 增加：

```python
_build_file_repair_handoff_proposal()
```

当满足：

```text
error_type == shape_mismatch
related_files 非空
```

确定性生成：

```text
kind=manual_only
```

它只负责把证据移交给 File Repair Planner，不直接生成 Patch，也不绕过人工审批。

#### 复盘结论

能用确定性规则表达的安全路由，不应该继续依赖 LLM 自由发挥。

---

### 22. File Repair 可能修改测试，或者没有行为验证目标

#### 现象

当 Debug 只提供测试文件时，模型可能提出修改测试来“让测试通过”；另一个问题是
Patch 虽然修了实现，却没有携带 `verification_targets`，最终只能达到
`structurally_valid`。

#### 根因

模型没有天然理解：

```text
失败测试是行为契约
不是应该被修改掉的障碍
```

同时，可信测试命令已经存在于 `pending_action`，却没有被程序确定性复用。

#### 解决方案

在 `file_repair_planner_node.py` 中：

- `_is_test_path()` 识别测试路径。
- 拒绝任何试图修改测试文件的 File Repair Proposal。
- `_extract_action_verification_targets()` 从当前 pytest action 中提取真实存在的
  repo 内测试文件。
- 将这些目标合并到 `verification_targets`。

Prompt 同时明确：

- 不删除、跳过、弱化或修改失败测试。
- 只修改实现文件。
- 测试文件只能作为验证目标。

#### 复盘结论

测试不是模型的修复目标，而是 Patch 是否正确的外部证据。

---

### 23. `direct-004`：Diff 中的 `+` 和代码缩进容易混淆

#### 现象

候选 Patch 显示：

```diff
-    raise RuntimeError("shape mismatch: phase14 controlled source bug")
+    return left + right
```

肉眼容易误以为 `return` 前只有三个空格，担心出现 `IndentationError`。

#### 根因

Unified diff 行首的第一个 `+` 是“新增行”标记，不属于 Python 源码。显示字体和
复制格式也可能让空格数量不直观。

#### 解决方案

使用能够显示行尾和真实空白的命令检查 Patch：

```bash
sed -n '1,20l' "$PATCH_PATH"
```

实际 Patch 中是：

```text
+    return left + right$
```

即 `+` 后有四个缩进空格，Python 语法正确。

#### 复盘结论

Patch Review 不能只凭截图，应检查原始 `patch.diff`、目标文件集合和 Hash。

---

### 24. `realpath`、`python` 突然全部找不到

#### 现象

先出现：

```text
assert_under_allowed_root: command not found: realpath
```

随后：

```text
(agent) ping501i% python
zsh: command not found: python
```

提示符也从：

```text
(agent) user@host:/path$
```

变成：

```text
(agent) ping501i%
```

#### 根因

验收脚本原来使用：

```bash
for path in ...
```

这在 bash 中只是普通变量，但在 zsh 中，小写 `path` 是与大写 `PATH` 绑定的
特殊数组。循环不断给 `path` 赋值，相当于覆盖 `PATH`，最终所有正常命令目录
都从搜索路径中消失。

`(agent)` 只是 Prompt 中的 Conda 环境标记，不能证明 Agent 环境的 `bin` 仍然
存在于 `PATH`。

提示符以 `%` 结尾说明当前 shell 是 zsh；是否显示用户名和当前目录只由 Prompt
主题决定，目录本身并没有消失。

#### 解决方案

教程将循环变量改为：

```bash
for guarded_path in ...
```

路径解析使用精确受信任入口：

```bash
/usr/bin/realpath
```

已经损坏的当前 shell 可以临时恢复：

```zsh
export PATH="/data2t/home/tianshaoqi/miniconda3/envs/agent/bin:/home/tianshaoqi24/miniconda3/condabin:/usr/local/bin:/usr/bin:/bin"
rehash
```

然后检查：

```zsh
command -v python
python --version
command -v realpath
```

#### 复盘结论

编写同时支持 bash 和 zsh 的验收脚本时，要避免使用 zsh 特殊参数名作为普通
变量，尤其是：

```text
path
commands
status
```

路径安全检查还应使用绝对路径调用关键系统工具，避免依赖已经被污染的 `PATH`。

---

### 25. 手工 Repository Lock 测试进入 `dquote>`

#### 现象

粘贴并发锁测试后，zsh 出现：

```text
dquote>
```

并持续等待输入。

#### 根因

`dquote>` 表示 shell 检测到未闭合的双引号。常见原因包括：

- 多行代码只复制了一半。
- 开头的 `python ... <<'PY'` 遗漏。
- Heredoc 结尾 `PY` 没有单独顶格。
- 某一行末尾的引号在复制时丢失。

此时命令尚未完整解析，不能继续粘贴下一段。

#### 解决方案

先按：

```text
Ctrl+C
```

取消未完成输入，然后：

```zsh
jobs -l
wait
```

确认旧后台任务结束，再完整粘贴持锁进程和竞争进程。Heredoc 的结束标记必须：

```text
单独一行
顶格
没有前后空格
没有引号
```

成功结果应包含：

```text
holder acquired lock
expected: repository is busy: /data/tianshaoqi24/PST-Convolution-main
```

#### 复盘结论

看到 `dquote>`、`heredoc>` 或持续出现二级提示符时，优先判断 shell 仍在等待
语法闭合，不要把它误认为 Python 或 Agent 正在运行。

---

## 四、四轮真实端到端验收分别证明了什么

### 1. 初始验收：证明真实模型和真实论文会暴露 Schema 差异

主要问题：

```text
PaperSummary fallback
method_modules=0
experiment_settings 结构不匹配
```

主要收获：

- 单元测试不能代替真实模型 Probe。
- Prompt 示例必须与当前 Schema 同步。
- fallback 必须保留，避免 Graph 因模型格式问题直接崩溃。

### 2. `direct-002`：证明 structured output 重试边界不完整

主要问题：

```text
shape_mismatch 已识别
RepairProposal 在 invoke 内 ValidationError
最终 repair_kind=no_repair
```

主要修复：

- 在 `structured_llm.invoke()` 外层直接捕获 Pydantic ValidationError。
- 将其纳入同一条有限重试链。
- 收紧 RepairStep 枚举 Prompt。

### 3. `direct-003`：证明 LLM 不能独占调试证据提取

主要问题：

```text
traceback 有 source + test
LLM related_files 只有 test
file_repair_kind=manual_only
```

主要修复：

- 从 traceback 确定性提取 repo 内源码路径。
- 与模型相关文件合并。
- `shape_mismatch + related_files` 确定性移交 File Repair。
- 禁止 Patch 修改测试，并自动继承 pytest 验证目标。

### 4. `direct-004`：验证受控 Patch 已经能够生成

候选 Patch：

```diff
-    raise RuntimeError("shape mismatch: phase14 controlled source bug")
+    return left + right
```

这一轮证明：

- Debug 找到了真实实现文件。
- Repair Planner 成功移交文件修复。
- File Repair Planner 修改实现而不是测试。
- Patch Builder 生成了有界 unified diff。
- 下一步必须继续经过隔离验证和 Promotion 审批。

最终验收还应继续确认：

```text
verification_status=behaviorally_verified
promotion_allowed=true
原仓库只修改 phase14_demo.py
application journal=applied/after
Patch 后重新进入 human_review
最终 pytest 1 passed
```

---

## 五、涉及的核心文件和职责

### 1. 结构化输出可靠性

```text
app/tools/structured_output_tools.py
app/schemas.py
app/prompts/repair_prompt.py
app/prompts/file_repair_prompt.py
```

职责：

- JSON Schema strict 请求。
- Pydantic 结构与语义校验。
- 携带错误的有限重试。
- Attempt artifact。
- 节点级确定性 fallback。

### 2. Graph 路由

```text
app/graph.py
```

职责：

- 唯一条件出口。
- `Literal` 路由返回值。
- 显式 `path_map`。
- Patch Review、Verifier、Promotion、Apply 的顺序约束。

### 3. Debug 与 Repair 移交

```text
app/tools/log_tools.py
app/nodes/log_debug_node.py
app/nodes/repair_planner_node.py
app/nodes/file_repair_planner_node.py
```

职责：

- 从日志中提取确定性错误证据。
- 合并模型语义判断。
- 在证据充分时稳定进入受限文件修复。
- 禁止修改测试契约。
- 继承可信行为验证目标。

### 4. Patch 身份与隔离验证

```text
app/tools/patch_tools.py
app/nodes/patch_builder_node.py
app/nodes/patch_review_node.py
app/nodes/patch_verifier_node.py
app/nodes/patch_promotion_review_node.py
```

职责：

- 路径、old_text 唯一性、修改规模和文件类型约束。
- 生成统一 diff、before/after hash 和 patch hash。
- 隔离 worktree 验证。
- 区分结构验证与行为验证。
- Promotion 前重新验证 Patch 和 Report 身份。

### 5. 并发与崩溃恢复

```text
app/tools/repository_lock_tools.py
app/nodes/patch_apply_node.py
```

职责：

- 同仓库跨进程排他锁。
- Write-ahead journal。
- Before/After/Conflict 判断。
- Apply 后、Checkpoint 前崩溃的幂等恢复。

### 6. Artifact 与最终报告

```text
app/tools/artifact_tools.py
app/nodes/final_report_node.py
app/nodes/run_manifest_node.py
```

职责：

- 保存 Proposal、Patch、Review、Verification、Application Record 和 Journal。
- 在 Final Report 和 Run Manifest 中串起完整证据链。

---

## 六、本阶段涉及的 Agent 核心知识点

### 1. Structured Output 不是绝对保证

`with_structured_output()` 是约束和解析机制，不是“模型永远正确”的承诺。可靠
Agent 仍然需要：

```text
本地校验
有限重试
语义 validator
可观测 trace
安全 fallback
```

### 2. 确定性规则应优先于概率判断

以下事实不需要 LLM 猜：

- traceback 中真实存在的 repo 文件。
- pytest action 中真实存在的测试目标。
- 路径是否越过仓库边界。
- Patch 是否修改了测试。
- Hash 是否匹配。
- Worktree 是否有额外 diff。

LLM 负责语义推理，程序负责安全事实。

### 3. Human-in-the-loop 必须绑定对象身份

审批不能只保存：

```text
approved=true
```

而应该绑定：

```text
action_hash
patch_sha256
verification_sha256
execution_profile_fingerprint
```

这样对象被修改后，旧审批会自动失效。

### 4. Trust Boundary Revalidation

Patch Review、Verifier、Promotion 和 Apply 之间都可能暂停。每次跨越副作用边界
时，都要重新从当前 artifact 计算事实，不能相信旧 state 中的缓存结论。

### 5. Checkpoint 不等于事务

LangGraph Checkpoint 记录 Graph 状态，但 Git Apply 是外部副作用。要让它可靠，
还需要：

- Repository Lock。
- Write-Ahead Journal。
- Before/After/Conflict 状态识别。
- 幂等恢复。

### 6. Fail Closed

以下情况都必须停止：

- 没有源码证据。
- Patch 修改测试。
- 没有可信行为测试。
- Verification Report 被修改。
- Execution Profile fingerprint 变化。
- Worktree 出现额外 diff。
- 仓库状态既不是 before 也不是 after。
- 同一仓库被另一个进程占用。

安全 Agent 的正确结果不总是“自动修好”，有时是“明确证明当前不能安全继续”。

---

## 七、以后排查同类问题的推荐顺序

### 1. 模型输出不符合 Schema

依次检查：

```text
1. Prompt 示例是否与 model_json_schema() 一致
2. JSON 字面大括号是否正确转义
3. Provider 是否真正支持 json_schema strict
4. invoke 是否直接抛出了 ValidationError
5. attempt artifact 中具体缺少哪个字段
6. Pydantic 语义 validator 是否拒绝了字段组合
7. 是否按预期重试
8. 最终 fallback 是否安全
```

不要只看最终 `no_repair`，要看每次 attempt。

### 2. Graph 没有进入预期节点

依次检查：

```text
snapshot.next
snapshot.values 中路由依赖字段
route 函数返回值
add_conditional_edges 的 path_map
是否还存在遗留无条件边
是否复用了旧 thread_id/checkpoint
```

### 3. Patch 没有生成

依次检查：

```text
debug_report.related_files
repair_proposal.kind
file_repair_proposal.kind
file_repair_proposal.edits
verification_targets
pending_patch
```

### 4. Patch 无法 Promotion

依次检查：

```text
verification.status
promotion_allowed
structural_checks_passed
behavioral_checks_run
behavioral_checks_passed
worktree_diff_sha256
verification_sha256
execution_profile_fingerprint
```

### 5. Shell 突然找不到命令

依次检查：

```zsh
echo "$0"
print -r -- "$PATH"
command -v python
command -v realpath
pwd
```

如果使用 zsh，再检查脚本是否误写了：

```zsh
for path in ...
```

### 6. 终端出现 `dquote>` 或 `heredoc>`

立即停止继续粘贴：

```text
Ctrl+C
```

然后检查：

- 引号是否成对。
- Heredoc 开头和结尾是否完整。
- `PY` 是否顶格且单独占一行。
- 是否把两个 Markdown 代码块只复制了一部分。

---

## 八、本阶段测试与验收重点

自动化测试至少覆盖：

```text
Graph 编译拓扑与真实路由
Structured output ValidationError 重试
Patch verification 语义
Verification hash 篡改
Promotion authorization
Worktree staged/HEAD/target/diff scope 污染
Repository lock 并发互斥
Apply 故障注入与恢复
Worktree 清理边界
Debug traceback 文件提取
禁止修改测试
pytest verification target 自动继承
```

真实端到端验收至少确认：

```text
[ ] 使用新的 thread_id 和 SESSION_ROOT
[ ] Agent 与论文执行环境解耦
[ ] 第一次执行命令经过 human_review
[ ] 受控失败进入 log_debug
[ ] Debug 同时找到测试文件和实现文件
[ ] File Repair 只修改实现文件
[ ] 第一次 Patch Review 只允许隔离验证
[ ] 至少一个行为测试通过
[ ] Verification 达到 behaviorally_verified
[ ] Promotion 中断期间 worktree 不能清理
[ ] 第二次审批后才修改原仓库
[ ] 原仓库只出现预期文件修改
[ ] Application Journal 最终为 applied/after
[ ] Patch 后 action hash 变化并重新审批
[ ] 最终测试成功并生成报告
[ ] 流程结束后 worktree 可以显式清理
```

---

## 九、最终经验总结

Phase 14 最重要的变化，不是 Agent “终于会改代码”，而是我们不再把下面这些
事情混在一起：

```text
模型建议修改什么
程序能否安全生成 Patch
Patch 是否能在隔离环境应用
Patch 是否通过行为测试
用户是否批准写回原仓库
写回过程是否并发安全
进程崩溃后能否恢复真实状态
```

早期的 LLM Schema 不匹配问题也说明：Agent 的可靠性不能建立在“模型这次应该
会按要求回答”上。最终可靠链必须同时包含：

```text
Prompt 约束
Schema 约束
本地语义校验
有限重试
确定性证据
安全降级
人工审批
Hash 绑定
隔离验证
并发控制
崩溃恢复
完整 Artifact
```

这套思路不仅适用于论文复现 Agent，也适用于任何具备命令执行、代码修改或其他
真实副作用的 Agent。
