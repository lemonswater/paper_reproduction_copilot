# CLI 命令使用手册

这个文档不是某一个实现阶段的教程，而是一个持续维护的“命令使用手册”。

它的目标很简单：

- 把当前项目里常用 CLI 命令的真实用途写清楚
- 给出一套能直接复制运行的命令顺序
- 说明每条命令成功时应该看到什么
- 说明常见报错通常意味着什么

后面如果你新增了新的 CLI 命令，比如：

- `show-state`
- `list-checkpoints`
- `reset-thread`
- `show-run`
- 其他调试命令

都可以继续追加到这个文件里。

---

## 一、使用前先确认两件事

### 1. 你当前在“能正常运行项目”的 Python 环境里

最基本的一点是：

```bash
python -m app.main version
```

如果这一步都跑不通，比如报：

```text
ModuleNotFoundError: No module named 'langgraph'
```

那说明你当前不在正确的虚拟环境里，或者依赖还没装好。

这时不要继续跑后面的命令，先切回你平时能正常运行这个项目的环境。

### 2. 区分 `thread_id` 和 `run_id`

这两个名字很容易混。

#### `thread_id`

它是 LangGraph checkpoint / resume 使用的“任务身份”。

你在这些命令里会用到它：

- `run-graph --thread-id ...`
- `show-state --thread-id ...`
- `resume-command-selection ...`
- `resume-review ...`

#### `run_id`

它是 Phase 19 引入的“本次运行的归档目录名”。

你在这些地方会用到它：

- `runs/<run_id>/...`
- `show-run <run_id>`

也就是说：

```text
thread_id 用来恢复 graph
run_id 用来查看本次运行生成的 artifact / manifest
```

### 3. 现在的 `run_id` 可能会长成 `run-...`

如果你当前 `app.main.run_graph()` 还没有把：

```python
"task_id": thread_id
```

传进初始 state，那么 `run_context_node` 默认会生成这种前缀：

```text
run-20260717-030927-22f4ba90
```

这不是错误，只是说明当前实现里 `run_id` 还没有复用 `thread_id` 当作前缀。

---

## 二、场景 1：从 `run-graph` 一路跑到 `show-run`

这是你现在最常用的一条命令链。

目标是完成下面这件事：

```text
启动 graph
-> 中断在 command_selection / human_review 时继续 resume
-> 直到 graph 真正结束
-> 最后查看 run_manifest.json
```

---

## 三、完整命令顺序

下面这套命令是推荐顺序。

为了避免 checkpoint 干扰，建议每次都用一个新的 `thread_id`。

这里用：

```text
manifest-002
```

作为示例。

### 第 1 步：启动 graph

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer/ \
  --thread-id manifest-002
```

### 这一步应该发生什么

Graph 会先跑前面的主链，例如：

```text
run_context
-> paper_reader
-> method_extractor
-> repo_scan
-> code_search
-> mapping
-> experiment_plan
```

之后通常会停在：

- `command_selection`
- 或更后面的 `human_review`

### 很重要：看到 `graph finished` 不一定代表真的结束

这是当前最容易误判的一点。

如果某个节点内部调用了：

```python
interrupt(...)
```

那么 `graph.invoke(...)` 会先返回，CLI 也可能打印：

```text
graph finished
```

但这并不等于 graph 真的走到了：

```text
END
```

它更像是：

```text
这一次 invoke 暂时停住了
等待你后续 resume
```

所以后面一定要配合 `show-state` 看当前停在哪。

---

### 第 2 步：查看当前 state，并拿到 `run_id`

```bash
python -m app.main show-state --thread-id manifest-002
```

### 这一步重点看什么

你主要看 `values` 里有没有下面这些字段：

- `run_id`
- `run_dir`
- `output_files`

如果 `run_context_node` 已经执行过，你通常能看到：

- `run_id`
  - 比如 `run-20260717-030927-22f4ba90`
- `run_dir`
  - 比如 `runs/run-20260717-030927-22f4ba90`

### 这时候为什么通常还没有 `run_manifest_path`

因为 `run_manifest.json` 是在 graph 最后的：

```text
final_report
-> run_manifest
-> END
```

这一段才会生成。

如果 graph 还停在 `command_selection`，那么：

- `runs/<run_id>/` 目录可能已经存在
- 但 `reports/run_manifest.json` 还不存在

这属于正常现象。

---

### 第 3 步：如果停在 `command_selection`，继续 resume

现在 `command_selection_node` 会为每次 run 自动创建：

```text
runs/<run_id>/planning/command_selection_input.json
```

文件会根据 Agent 本次生成的所有 `run_commands` 自动预填，例如：

```json
{
  "run_commands_hash": "8c4f...省略...9a21",
  "selected_index": 0,
  "edits": [
    {
      "index": 0,
      "command": "python train-msr-small.py"
    },
    {
      "index": 1,
      "command": "python train-ntu60.py"
    }
  ]
}
```

`run_commands_hash` 绑定生成该文件时的原始命令列表，用于防止上游计划变化后继续沿用旧索引。只修改 `selected_index` 和需要调整的 `command`，不要手动修改或删除 `run_commands_hash`，也不要新建另一个 JSON 文件。

编辑完成后，只传 `thread-id`：

```bash
python -m app.main resume-command-selection manifest-002
```

CLI 会从 checkpoint 读取 `run_dir`，再自动加载该 run 的 `command_selection_input.json`。

如果是升级前已经停在 `command_selection` 的旧 thread，第一次执行上面的命令会补建文件并停止；编辑文件后再次执行同一条命令即可。

如果同一个 thread 的 `run_commands` 已经重新生成，CLI 会发现文件中的哈希与 checkpoint 不一致：

1. 将旧文件备份为 `command_selection_input.stale-<时间戳>.json`。
2. 根据 checkpoint 中的最新命令重新生成 `command_selection_input.json`。
3. 停止本次恢复，等待用户重新检查索引和命令。
4. 编辑完成后，再执行一次相同的 `resume-command-selection` 命令。

这样既不会丢失之前的人工编辑，也不会把旧文件中的 `index=1` 错误应用到已经变化的新命令列表。

如果不需要修改，只想直接选第 0 条，仍然可以使用：

```bash
python -m app.main resume-command-selection manifest-002 --selected-index 0
```

### 这一步的含义

它等价于告诉 graph：

```text
我选择先执行第 0 条 run_command
```

`--input` 仍然保留，用于显式读取其他 JSON 文件：

```bash
python -m app.main resume-command-selection \
  manifest-002 \
  --input path/to/another-selection.json
```

显式输入文件也必须包含与当前 checkpoint 一致的 `run_commands_hash`；不一致时 CLI 会拒绝恢复，而不会执行过期选择。

日常调试推荐直接编辑 run 目录下自动生成的文件，然后使用无额外参数的恢复命令。

---

### 第 4 步：再次查看 state

```bash
python -m app.main show-state --thread-id manifest-002
```

这一步通常会出现两种情况。

#### 情况 A：进入 `human_review`

常见于：

- `python train.py`
- `python -m ...`
- `pip install ...`
- 编译脚本

也就是仍然需要人工审批的动作。

#### 情况 B：低风险动作自动放行

如果你已经把低风险分支打通，而且当前命令属于低风险白名单，那么 graph 可能会直接进入：

```text
executor
```

甚至已经继续往后走。

---

### 第 5 步：如果停在 `human_review`，继续审批

```bash
python -m app.main resume-review manifest-002 --decision approved
```

你也可以把 `approved` 改成：

- `rejected`
- `revise`

如果你要附带反馈内容，可以继续补：

```bash
python -m app.main resume-review manifest-002 \
  --decision revise \
  --feedback "请先补 dataset_path"
```

---

### 第 6 步：再看一次 state，确认 graph 是否真正结束

```bash
python -m app.main show-state --thread-id manifest-002
```

### 这一步重点确认 4 件事

#### 1. `next=()`

如果 `next=()`，通常说明当前没有挂起的后续节点了。

#### 2. `final_status`

你要确认这次运行最后状态是什么，比如：

- `succeeded`
- `failed`
- `blocked`
- `invalid_action`

#### 3. `run_manifest_path`

如果 graph 真正走到了 `run_manifest_node`，这里应该已经出现：

```text
runs/<run_id>/reports/run_manifest.json
```

#### 4. `output_files`

这里应该也能看到：

- `artifact_index.json`
- `run_manifest.json`

如果你还看不到这些字段，说明 graph 还没有真正走到最后。

---

### 第 7 步：查看最终 `run_manifest.json`

先从 `show-state` 输出里拿到 `run_id`，再执行：

```bash
python -m app.main show-run <run_id>
```

例如：

```bash
python -m app.main show-run run-20260717-030927-22f4ba90
```

这条命令会读取：

```text
runs/<run_id>/reports/run_manifest.json
```

并直接把内容打印出来。

---

## 四、最推荐的实际操作顺序

如果你只想记一条最短流程，就记下面这组：

```text
run-graph
-> show-state
-> resume-command-selection
-> show-state
-> resume-review（如果需要）
-> show-state
-> show-run
```

对应命令模板如下：

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer/ \
  --thread-id manifest-002

python -m app.main show-state --thread-id manifest-002

python -m app.main resume-command-selection manifest-002 --selected-index 0

python -m app.main show-state --thread-id manifest-002

python -m app.main resume-review manifest-002 --decision approved

python -m app.main show-state --thread-id manifest-002

python -m app.main show-run <run_id>
```

---

## 五、你现在最容易遇到的几个现象

### 现象 1：`show-run` 提示 `run manifest not found`

例如：

```text
Invalid value: run manifest not found: runs/run-20260717-030927-22f4ba90/reports/run_manifest.json
```

这通常不表示 `show-run` 命令坏了，而表示：

```text
graph 还没有真正走到 run_manifest_node
```

最常见原因是：

- 还停在 `command_selection`
- 还停在 `human_review`
- 这次运行还没真正走到 `END`

### 怎么确认

先执行：

```bash
python -m app.main show-state --thread-id <thread_id>
```

如果 state 里还没有：

- `run_manifest_path`
- `artifact_index_path`

那就说明还需要继续 resume。

---

### 现象 2：`runs/<run_id>/` 目录已经有了，但里面几乎是空的

这通常说明：

```text
run_context_node 已经跑了
但 run_manifest_node 还没跑到
```

这是因为 `run_context_node` 会在 graph 很早的时候就创建：

```text
runs/<run_id>/
```

所以你会看到目录提前存在。

但真正的：

- `artifact_index.json`
- `run_manifest.json`

只有在 graph 结束时才会写入。

---

### 现象 3：`graph finished` 了，但 `show-run` 还是看不到 manifest

这个现象和前面一样，通常意味着：

```text
当前 invoke 结束了
但整个 graph 还没结束
```

在有 `interrupt()` 的系统里，这很正常。

所以不要只看：

```text
graph finished
```

还要看：

```text
show-state 的 next / values / run_manifest_path
```

---

## 六、如果想直接看文件，不走 `show-run`

你也可以直接在终端里查看归档目录。

### 先看某次运行到底生成了哪些文件

```bash
find runs/<run_id> -maxdepth 2 -type f | sort
```

例如：

```bash
find runs/run-20260717-030927-22f4ba90 -maxdepth 2 -type f | sort
```

### 直接查看 manifest

```bash
cat runs/<run_id>/reports/run_manifest.json
```

### 直接查看 artifact index

```bash
cat runs/<run_id>/reports/artifact_index.json
```

这种方式的好处是：

- 不依赖 CLI 包装
- 调试时很直接

---

## 七、这一条命令链背后的核心判断逻辑

你可以把这条流程记成下面这张图：

```text
run-graph
  -> 生成 thread_id 对应的 checkpoint 状态
  -> 生成 run_id 对应的归档目录
  -> 如果 interrupt，则等待 resume
  -> 只有真正走到 final_report -> run_manifest -> END
     才会出现 run_manifest.json
```

更具体一点：

```text
thread_id
  -> 用来恢复 graph

run_id
  -> 用来找 artifact

show-state
  -> 看“任务现在卡在哪”

show-run
  -> 看“这次运行最后留下了什么”
```

---

## 八、后面可以继续往这个手册里补什么

这个文件后面很适合继续补这些命令场景：

1. `show-state` 的字段怎么看
2. `list-checkpoints` 的输出怎么理解
3. `reset-thread` 在什么情况下使用
4. `resume-review` 的不同 `decision` 会触发什么结果
5. 自动生成的 `command_selection_input.json` 如何校验和审计
6. `show-run` 和直接查看 `runs/<run_id>/` 的区别

---

## 最后一句话总结

如果你现在只想知道“为什么 `show-run` 看不到 manifest”，最核心的判断标准就是：

```text
只要 graph 还停在 command_selection / human_review 这类 interrupt 节点，
run_manifest.json 就还不会存在。
```

只有当整条图真正走完：

```text
... -> final_report -> run_manifest -> END
```

你才能稳定地通过：

```bash
python -m app.main show-run <run_id>
```

看到最终结果。
