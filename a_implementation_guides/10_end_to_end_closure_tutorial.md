# 10. 如何补齐端到端闭环：详细落地教程

这份教程不是再讲单个节点怎么写，而是专门回答一个问题：

> 现在这个项目已经有论文阅读、仓库扫描、代码映射、实验计划、日志 debug、human review、评测骨架了，下一步怎么把它补成一个真正“能跑完整闭环”的 Agent？

这里的“端到端闭环”指的是：

```text
输入论文 + repo
→ 结构化分析
→ 生成实验计划
→ 自动挑出待执行动作
→ 风险判断
→ 人工审批
→ 受控执行
→ 记录日志与执行结果
→ 失败时进入 debug
→ 产出最终报告 / 评测结果
```

这份教程会尽量贴着你当前仓库的现状来写，而不是写成一个和现有实现脱节的理想方案。

---

## 一、先明确：什么叫“补齐闭环”

当前项目已经具备很多“分析能力”，但还没有真正形成完整执行闭环。

所谓闭环，不只是图能从 `START` 跑到 `END`，而是要满足下面几件事：

1. 有明确输入  
   论文路径、仓库路径、可选日志路径、实验目标。

2. 有中间结构化状态  
   `paper_summary`、`repo_map`、`paper_code_mapping`、`experiment_plan` 等。

3. 有从“分析”到“动作”的桥  
   也就是把 `experiment_plan.run_commands` 转成 `pending_action`。

4. 有真正的执行阶段  
   审批通过后，不只是把结果写回 state，而是真的受控执行一个动作。

5. 有执行结果回流  
   比如 stdout、stderr、returncode、日志路径、产物路径。

6. 有失败分支  
   执行失败后，能进入 `log_debug_node` 或类似分支做诊断。

7. 有评测和报告  
   跑完后，不只是终端打印一下，而是留下报告、测试与可复盘结果。

只有把这 7 件事串起来，才算真正补齐端到端闭环。

---

## 二、当前项目距离闭环还差什么

结合你当前仓库的代码，已经有的部分和缺失的部分可以拆开看。

### 已经有的部分

- 论文阅读：
  - `paper_reader_node`
  - `method_extractor_node`

- 仓库扫描：
  - `repo_scan_node`

- 论文-代码映射：
  - `code_search_node`
  - `mapping_node`

- 实验计划生成：
  - `experiment_plan_node`

- 图工作流骨架：
  - `build_graph()`
  - `thread_id`
  - `checkpoint`

- 日志 debug：
  - `log_debug_node`

- 风险判断与人工审批：
  - `risk_check_node`
  - `human_review_node`

- 节点级测试：
  - `tests/test_review_flow.py`

### 还缺的关键环节

#### 1. 没有节点自动生成 `pending_action`

现在图里虽然已经有：

- `risk_check_node`
- `human_review_node`

但前面没有节点真正产出：

```python
state["pending_action"]
```

这意味着审批分支虽然存在，但大多数情况下根本进不去。

#### 2. 审批通过后没有真正执行动作的节点

现在图在 `human_review` 后直接 `END`。

也就是说：

- Agent 可以“建议”
- 可以“审批”
- 但不能“受控执行”

这使得当前项目更像一个 proposal-only Agent，而不是闭环 Agent。

#### 3. 缺少执行结果状态

当前 `state.py` 里没有一组专门的执行结果字段，例如：

- `run_commands`
- `human_feedback`
- `execution_result`
- `execution_log_path`
- `last_action_result`
- `final_status`

没有这些字段，执行后就很难继续往：

- debug
- report
- eval

这些后续环节流转。

#### 4. 缺少失败后自动回流到 debug 的桥

现在 `log_debug_node` 是通过 `log_path` 进入的，但没有和“执行失败”自然接起来。

理想情况应该是：

- 执行节点失败
- 自动生成运行日志
- 将日志路径写回 state
- 路由到 `log_debug`

#### 5. `resume_review` 还没有完全打通

当前 [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:1) 里的 `resume_review()` 用了：

```python
Command(resume=...)
```

但文件里还没有导入 `Command`。

这属于小问题，但会直接影响端到端恢复链。

#### 6. `run_graph` 的入口还不够“正常流程友好”

当前 `run_graph()` 把 `log_path` 设成了必填。

但正常流程应该是：

- 没有日志时也能跑主链
- 只有在执行失败或用户显式传日志时才进入 debug

所以 `log_path` 更适合做成可选参数。

#### 7. 评测脚本还没有覆盖“执行-审批-恢复”链

`run_eval.py` 现在更偏向分析链路评测，不足以验证：

- interrupt
- resume
- execution
- debug 回流

这意味着闭环补齐后，评测体系也要升级。

---

## 三、先给出目标架构

建议你补齐闭环后的目标图，不要一步到位做得太复杂，先做到下面这一版：

```text
START
  -> paper_reader
  -> method_extractor
  -> repo_scan
  -> code_search
  -> mapping
  -> experiment_plan
  -> action_builder
  -> risk_check
  -> human_review
  -> executor
      -> success: final_report / END
      -> failure: log_debug -> final_report / END
```

如果审批被拒绝，则：

```text
human_review
  -> rejected / revise
  -> END 或返回 action_builder / experiment_plan
```

这个版本的关键点是：

- 先只支持“一次挑一个动作执行”
- 审批通过后只执行一个 `pending_action`
- 如果失败，就走 debug
- 如果成功，就写结果并结束

先把一条最小闭环跑通，比一开始就支持批量动作、自动重试、并发执行更重要。

---

## 四、推荐实施顺序

建议你按下面 6 个阶段做，而不是同时改很多处。

### 阶段 A：先补状态字段和接口

先把 state 和 CLI 补稳。

### 阶段 B：把 experiment plan 变成待执行动作

新增 `action_builder_node`。

### 阶段 C：让审批后真的执行

新增 `executor_node`。

### 阶段 D：把失败自动接到 log_debug

让执行失败自然进入 debug 分支。

### 阶段 E：补齐 resume 和端到端测试

把 interrupt / resume 跑通。

### 阶段 F：升级 eval 和最终报告

让闭环具备可验证、可展示、可复盘能力。

下面按这个顺序细讲。

---

## 五、阶段 A：先补状态字段和接口

这一阶段的目标不是新增功能，而是先把闭环要依赖的状态结构铺平。

### 1. 修改 `app/state.py`

建议把下面这些字段补进 `ReproductionState`：

```python
run_commands: list[dict[str, Any]]
human_feedback: Optional[str]
execution_result: dict[str, Any]
execution_log_path: Optional[str]
last_action_result: dict[str, Any]
final_status: Optional[str]
```

同时建议把这两个字段修正一下：

- `experiment_plan`
  - 当前更合理的类型应该是 `dict[str, Any]`
  - 不是 `list[dict[str, Any]]`

- `debug_report`
  - 保持 `dict[str, Any]` 即可

### 2. 修改 `app/main.py`

建议先做这几个接口调整：

#### `run_graph()` 改成 `log_path` 可选

目标是让正常主链可以不传日志：

```python
def run_graph(
    paper_path: str,
    repo_path: str,
    log_path: str | None = None,
    ...
):
```

然后 `graph.invoke()` 里仍然写：

```python
"log_path": log_path,
```

这样：

- 正常执行时不需要日志
- 失败复盘时可以直接传已有日志

#### 给 `resume_review()` 补 `Command` 导入

在文件顶部加入：

```python
from langgraph.types import Command
```

这是跑通审批恢复的必要条件。

### 3. 本阶段完成后的验收

你应该能做到：

- `run_graph` 不传 `log_path` 也能进入主链
- `resume_review` 至少在语法层面可运行
- `state.py` 里已经有后续闭环需要的执行结果字段

---

## 六、阶段 B：新增 `action_builder_node`

这是闭环里最关键的一步，因为它把“计划”变成“待执行动作”。

### 1. 为什么必须要这个节点

现在 `experiment_plan_node()` 只会输出：

- `experiment_plan`
- `run_commands`

但图后面的 `risk_check_node()` 需要的是：

```python
pending_action
```

所以你必须在中间加一层桥，把：

```text
run_commands -> pending_action
```

### 2. 新增文件建议

建议新增：

```text
app/nodes/action_builder_node.py
```

### 3. 这个节点应该做什么

最小实现先只做一件事：

- 从 `state["run_commands"]` 里挑第一条命令
- 转成一个标准 `pending_action`

例如：

```python
{
    "type": "run_command",
    "command": "python train.py --config configs/base.yaml",
    "cwd": "/path/to/repo",
    "reason": "run baseline training",
    "source": "experiment_plan"
}
```

### 4. 核心逻辑建议

建议函数大致像这样：

```python
def action_builder_node(state: dict) -> dict:
    run_commands = state.get("run_commands", [])
    if not run_commands:
        return {
            "pending_action": None,
            "final_status": "no_action",
        }

    first = run_commands[0]
    return {
        "pending_action": {
            "type": "run_command",
            "command": first["command"],
            "cwd": first["cwd"],
            "reason": first.get("reason", "from experiment plan"),
            "source": "experiment_plan",
        }
    }
```

### 5. 图中怎么接

把图改成：

```text
mapping -> experiment_plan -> action_builder -> risk_check
```

而不是现在这样：

```text
mapping -> experiment_plan -> route_after_plan
```

### 6. 为什么建议先只挑第一条命令

因为当前目标是补“最小闭环”，不是做完整任务编排器。

先只执行第一条命令有几个好处：

- 状态最简单
- 审批链容易验证
- 失败后 debug 路径清楚

等这条链稳定后，再扩展成：

- 多动作队列
- 批量审批
- 每个动作单独执行状态

### 7. 本阶段完成后的验收

你应该能验证：

- `experiment_plan_node()` 输出 `run_commands`
- `action_builder_node()` 能生成 `pending_action`
- graph 能稳定进入 `risk_check_node`

---

## 七、阶段 C：新增 `executor_node`

这个节点决定项目是否真正拥有“执行能力”。

### 1. 为什么现在必须补 executor

如果没有执行节点，当前项目只能：

- 读论文
- 看代码
- 出计划
- 做审批

但不能：

- 真正运行训练命令
- 真正拿到运行结果
- 真正产生失败日志

闭环就在这里断掉了。

### 2. 新增文件建议

建议新增：

```text
app/nodes/executor_node.py
app/tools/exec_tools.py
```

### 3. `executor_node` 最小目标

先只支持：

- 审批通过后的 `run_command`
- 在指定 `cwd` 中执行
- 捕获 stdout / stderr / returncode
- 写出运行日志
- 把执行结果写回 state

### 4. 执行工具层建议

在 `app/tools/exec_tools.py` 里封装一个纯工具函数，比如：

```python
def run_command_safe(command: str, cwd: str) -> dict:
    ...
```

返回格式建议统一成：

```python
{
    "ok": True or False,
    "returncode": 0,
    "stdout": "...",
    "stderr": "...",
    "combined_output": "...",
}
```

如果你想更稳一点，也可以先只支持：

- `python`
- `torchrun`
- `accelerate`

不需要一开始就支持复杂 shell 特性。

### 5. `executor_node` 该如何判断是否执行

在执行前先看：

- `pending_action` 是否存在
- `user_approval` 是否是 `approved`

逻辑建议是：

- `approved`
  - 执行
- `rejected`
  - 返回 `final_status = "rejected"`
- `revise`
  - 返回 `final_status = "revise_requested"`

### 6. 建议写出的 state

执行后建议写回：

```python
{
    "execution_result": {...},
    "execution_log_path": "outputs/run_case_xxx.log",
    "last_action_result": {...},
    "final_status": "succeeded" or "failed",
}
```

### 7. 为什么一定要把执行日志落盘

因为后面 `log_debug_node()` 需要吃日志。

所以不要只把 stdout/stderr 存在内存里，建议一定写：

```text
outputs/execution.log
```

或者：

```text
outputs/{thread_id}_execution.log
```

这会让失败回流到 debug 分支非常自然。

### 8. 图中怎么接

建议图改成：

```text
risk_check
  -> requires_approval=True  -> human_review
  -> requires_approval=False -> executor 或 END

human_review
  -> approved / rejected / revise
  -> executor 或 END
```

更简单一点的做法是：

- `risk_check` 后仍然只去 `human_review` 或 `END`
- `human_review` 后固定去 `executor`
- `executor` 自己判断 `user_approval`

这样图结构更简单。

### 9. 本阶段完成后的验收

你应该能做到：

- 审批通过后真的执行一条命令
- 日志被写到 `outputs/`
- 执行结果回写到 state

---

## 八、阶段 D：把失败自动接到 `log_debug`

这是把“执行链”和“debug 链”真正接起来的关键。

### 1. 当前的问题

现在 `log_debug_node()` 依赖：

```python
state["log_path"]
```

但执行失败后，没有节点自动把运行日志路径塞回去。

### 2. 推荐改法

在 `executor_node()` 里：

- 执行失败时写出日志文件
- 返回：

```python
{
    "log_path": str(log_path),
    "final_status": "failed",
}
```

### 3. 图中新增路由

建议新增一个 router，例如：

```python
def route_after_executor(state: ReproductionState) -> str:
    if state.get("final_status") == "failed" and state.get("log_path"):
        return "log_debug"
    return END
```

然后：

```text
executor
  -> failed + log_path -> log_debug
  -> success -> END
```

### 4. 为什么这是闭环最关键的一跳

只有这一步补上，项目才真正拥有：

```text
执行 -> 失败 -> 诊断
```

而不是：

```text
执行失败 -> 人工自己去翻日志
```

### 5. 本阶段完成后的验收

你应该能构造一条必然失败的命令，例如：

```bash
python not_exists.py
```

然后观察：

- executor 写出失败日志
- graph 自动进入 `log_debug`
- 生成 `debug_report.json` 和 `debug_report.md`

---

## 九、阶段 E：补齐 interrupt / resume 端到端测试

这个阶段不是写新功能，而是证明闭环真的跑通。

### 1. 当前测试覆盖到了什么

你已经有：

- `tests/test_review_flow.py`

它证明了：

- `assess_command_risk()`
- `risk_check_node()`
- `human_review_node()`

在节点级是通的。

但还没有证明：

- graph 真的 pause 了
- `resume_review()` 真的恢复了
- 恢复后真的执行了 executor

### 2. 建议新增的测试层次

#### 第一层：action builder 测试

建议新增：

```text
tests/test_action_builder_node.py
```

验证：

- 有 `run_commands` 时能产出 `pending_action`
- 无命令时能返回 `no_action`

#### 第二层：executor 测试

建议新增：

```text
tests/test_executor_node.py
```

验证：

- `approved` 时执行
- `rejected` 时不执行
- 失败时写日志并设置 `log_path`

#### 第三层：graph 级 interrupt / resume 测试

建议新增：

```text
tests/test_graph_review_resume.py
```

验证链路：

```text
pending_action -> risk_check -> human_review(interrupt)
-> Command(resume=approved)
-> executor
```

### 3. 真实运行验收命令建议

建议补齐后用下面方式手测：

#### 正常审批通过执行

```bash
python -m app.main run-graph "pdf/xxx.pdf" "/path/to/repo" --thread-id review-001
python -m app.main resume-review --thread-id review-001 --decision approved
```

#### 审批拒绝

```bash
python -m app.main resume-review --thread-id review-001 --decision rejected
```

#### 审批要求修改

```bash
python -m app.main resume-review --thread-id review-001 --decision revise --feedback "先换成更安全的命令"
```

### 4. 本阶段完成后的验收

你应该能明确回答：

- graph 有没有真正 pause
- resume 能不能继续同一个 thread
- 继续之后是不是走到了 executor

---

## 十、阶段 F：升级评测与最终报告

闭环补齐后，评测也要升级，否则你只能“看起来能跑”，却很难证明它稳定。

### 1. 升级 `run_eval.py`

当前 `run_eval.py` 更偏向分析链。

补齐闭环后，建议再加三类 case：

#### `execution_success`

验证：

- plan -> action_builder -> risk_check -> review -> executor
- 最终执行成功

#### `execution_fail_then_debug`

验证：

- executor 失败
- 自动写日志
- 自动进入 `log_debug`

#### `approval_flow`

验证：

- 需要审批的动作是否被正确拦住
- 是否符合安全边界

### 2. 增加 `eval_report.md`

建议除了 `eval_report.json`，再生成：

```text
outputs/eval_report.md
```

里面至少写：

- case 列表
- 成功数 / 失败数
- 审批链是否通过
- debug 链是否通过
- 失败原因

### 3. 增加 `final_report_node`

如果你想让闭环更完整，建议新增：

```text
app/nodes/final_report_node.py
```

它负责汇总：

- 输入
- 分析结果
- 计划
- 审批结果
- 执行结果
- debug 结果

然后输出：

```text
outputs/final_report.md
```

这样项目最后会真正有一个“可交付结果”，而不是散落在多个 JSON / md 里。

---

## 十一、建议的新文件清单

如果你按这套教程推进，比较推荐新增这些文件：

```text
app/nodes/action_builder_node.py
app/nodes/executor_node.py
app/nodes/final_report_node.py
app/tools/exec_tools.py
tests/test_action_builder_node.py
tests/test_executor_node.py
tests/test_graph_review_resume.py
tests/test_log_debug_e2e.py
```

可选新增：

```text
app/prompts/final_report_prompt.py
app/evaluation/cases/case_004_execution_success.json
app/evaluation/cases/case_005_execution_fail_debug.json
app/evaluation/cases/case_006_approval.json
```

---

## 十二、一个推荐的最小落地顺序

如果你想尽量稳地推进，建议按下面顺序做：

### 第 1 周目：先打通“审批但不执行”

1. 修 `state.py`
2. 修 `main.py`
3. 新增 `action_builder_node`
4. 改 graph，让 `experiment_plan -> action_builder -> risk_check`
5. 验证审批分支真的能稳定进入

### 第 2 周目：打通“审批后执行”

1. 新增 `exec_tools.py`
2. 新增 `executor_node`
3. 改 graph，让 `human_review -> executor`
4. 验证成功执行与失败执行

### 第 3 周目：打通“失败自动 debug”

1. executor 失败时写日志
2. 新增 `route_after_executor`
3. 自动进入 `log_debug`
4. 生成 debug_report

### 第 4 周目：补评测和报告

1. 扩展 `run_eval.py`
2. 增加更多 case
3. 生成 `eval_report.md`
4. 可选新增 `final_report_node`

这个顺序的好处是：

- 每一轮都有可见成果
- 每一轮都能单独验证
- 出问题时容易定位

---

## 十三、每一阶段该如何判断“算完成了”

### A 阶段完成标准

- `run_graph` 参数更合理
- `resume_review` 可调用
- state 字段补齐

### B 阶段完成标准

- `run_commands` 能转成 `pending_action`
- graph 能稳定进入 `risk_check`

### C 阶段完成标准

- 审批通过后能执行命令
- 执行结果进入 state

### D 阶段完成标准

- 执行失败后自动写日志
- 自动进入 `log_debug`
- 自动产出 `debug_report`

### E 阶段完成标准

- interrupt / resume 能 graph 级验证通过
- 有端到端测试

### F 阶段完成标准

- 能跑多 case
- 有 `eval_report.json`
- 最好还有 `eval_report.md`
- 能做一次完整 demo

---

## 十四、你现在最适合先做哪一步

结合你当前项目的状态，我最建议你从下面这一步开始：

### 优先级最高：先实现 `action_builder_node`

原因很简单：

- 它是当前闭环缺失的第一块桥
- 没有它，就没有 `pending_action`
- 没有 `pending_action`，后面的风险判断、人工审批、执行链都接不上

所以最实际的第一步不是先写 executor，而是：

1. 补 `run_commands` / `pending_action` 相关 state
2. 写 `action_builder_node`
3. 把 graph 接上
4. 先让审批链真正被触发

这一步打通之后，再做 executor 和失败 debug 回流会顺很多。

---

## 十五、最后的建议

补闭环时最容易犯的错误，是一下子同时改：

- state
- graph
- cli
- executor
- debug
- eval

这样很容易让问题交织在一起。

更稳的做法是：

- 一次只补一段桥
- 每补完一段就加测试
- 每补完一段就手工跑一次

你可以把整个闭环拆成四个问题来逐个回答：

1. 分析结果怎样变成动作？
2. 动作怎样进入审批？
3. 审批通过后怎样执行？
4. 执行失败后怎样回流到 debug？

只要这四个问题都在代码里有清楚的节点和状态，你的 Agent 就不再只是“会分析”，而是真正开始具备可控、可恢复、可调试的端到端能力。
