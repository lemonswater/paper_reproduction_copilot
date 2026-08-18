# Phase 23：统一交互 API 与结构化输出问题复盘

## 一、文档目的

本次验收同时涉及三层系统：

```text
HTTP API / Bearer Token
        ↓
异步 Job Runtime / Worker / Lease
        ↓
LangGraph / Provider / Interrupt
```

遇到的问题表面上都表现为“没有走到人工审批”，但实际根因分别来自认证、
执行环境配置、Job 调度和 LLM 结构化输出。

本文按照问题出现的时间顺序记录：

1. 当时看到的现象。
2. 真正的根因。
3. 对应解决方案。
4. 应该如何验证。
5. 以后排查同类问题时应先看什么。

---

## 二、问题时间线与解决方案

### 1. Job 完成，但 Graph 结果是 `environment_blocked`

#### 现象

通过 Worker 执行 Job 后，`show-job` 返回：

```text
status = succeeded
result.final_status = environment_blocked
interrupt_nodes = []
```

错误报告显示：

```text
未找到执行环境配置：local；
可用配置：pstnet-local-supervised
```

#### 根因

项目中存在两个容易混淆的字段：

```json
{
  "profile_id": "pstnet-local-supervised",
  "backend": "local"
}
```

- `profile_id` 是 CLI、API 和 Graph 引用的配置名称。
- `backend` 表示执行方式为本机执行，不是 profile 名称。

如果请求没有显式提供 profile，程序原来的默认值是：

```text
DEFAULT_EXECUTION_PROFILE=local
```

但是当前 `config/execution_profiles.local.json` 中只注册了：

```text
pstnet-local-supervised
```

因此 profile 查找失败，Graph 在 `input_validation` 阶段终止。

#### 解决方案

CLI 中显式指定：

```bash
--execution-profile pstnet-local-supervised
```

API 请求体中使用：

```json
"execution_profile_id": "pstnet-local-supervised"
```

也可以在实际 `.env` 中设置默认值：

```dotenv
DEFAULT_EXECUTION_PROFILE=pstnet-local-supervised
```

#### 验证

```bash
python -c \
  "from app.config import settings; print(settings.default_execution_profile)"
```

预期输出：

```text
pstnet-local-supervised
```

#### 复盘结论

```text
profile_id 是策略身份
backend 是执行实现
```

安全执行配置应使用明确的仓库级名称，不应把通用的 `local` 同时当成二者。

---

### 2. `run-worker` 看起来一直卡住

#### 现象

执行：

```bash
python -m app.main run-worker \
  --worker-id phase22-worker-1
```

终端只输出一次启动信息，之后不再返回 shell 提示符。

#### 根因

`run-worker` 默认是常驻进程。它会持续轮询 Job 队列，并不是执行一轮后退出。
没有新 Job 时保持安静是正常行为。

#### 解决方案

保持 Worker 终端运行，在另一个终端查询 Job：

```bash
python -m app.main show-job "$JOB_ID"
```

只处理一个 Job 后退出时使用：

```bash
python -m app.main run-worker \
  --worker-id phase22-worker-1 \
  --once
```

需要停止常驻 Worker 时按 `Ctrl+C`。

#### 判断 Worker 是否正常

同时满足以下条件，说明 Worker 正在工作：

```text
status = running
worker_id 不为空
heartbeat_at 持续更新
lease_expires_at 晚于 heartbeat_at
```

---

### 3. `attempt_count = 2`，看起来像重复执行

#### 现象

Job 运行中出现：

```text
attempt_count = 2
status = running
```

#### 根因

事件记录显示第一次 claim 后 lease 到期，系统生成：

```text
job_lease_requeued
```

随后 Worker 第二次 claim，所以 attempt 数变为 2。

这通常表示：

- 第一次 Worker 在 claim 后退出或重启。
- lease 到期前没有完成状态持久化。
- Reconciliation 判断没有活跃受监管进程，可以安全重新入队。

#### 解决方案

通过事件记录确认，而不是只看计数：

```bash
python -m app.main show-job-events "$JOB_ID"
```

如果事件顺序为：

```text
job_claimed
job_lease_requeued
job_claimed
```

说明 crash recovery 正常工作。

#### 复盘结论

`attempt_count` 是 Worker claim 次数，不是 LLM retry 次数，也不是训练命令
执行次数。三种重试预算必须分开理解。

---

### 4. API 返回 `401 Unauthorized`

#### 现象

终端 C 执行 `curl`，终端 A 显示：

```text
POST /v1/jobs HTTP/1.1 401 Unauthorized
```

#### 根因

不同终端不会自动共享 `export` 的环境变量。

API 在终端 A 启动时读取一次：

```text
AGENT_API_TOKEN
```

如果终端 C 中：

- 没有设置 token；
- 使用了不同 token；
- token 前后包含空格；
- 使用中文弯引号；

都会导致 Bearer Token 精确比较失败。

下面这种写法是错误的：

```bash
export AGENT_API_TOKEN=”123456789“
```

中文弯引号不是 shell 引号，而会成为变量值的一部分。

#### 解决方案

在终端 A 和终端 C 中设置完全相同的值，并使用 ASCII 引号：

```bash
export AGENT_API_TOKEN='同一个高熵随机token'
```

设置后必须重启 API，因为运行中的 API 不会自动重新读取 shell 环境。

#### 验证

无认证访问受保护端点应返回 401：

```bash
curl --silent \
  --output /dev/null \
  --write-out '%{http_code}\n' \
  "$API_BASE/v1/jobs"
```

携带正确 token 应返回 200：

```bash
curl --silent \
  --output /dev/null \
  --write-out '%{http_code}\n' \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs"
```

#### 安全注意

不要把真实 token 写进仓库、教程或提交记录。手工验收 token 应只存在于
当前 shell 或受控 Secret Manager 中。

---

### 5. SSE 返回 `Internal Server Error`

#### 现象

执行事件流监听：

```bash
curl --no-buffer \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID/events/stream?after=0"
```

返回：

```text
Internal Server Error
```

#### 排查结果

当时 token 使用了中文弯引号，应先修正认证变量。随后普通 Job 查询能够成功，
说明：

- API 可访问；
- token 已匹配；
- Job 确实存在。

但是 SSE 返回 500 不能只凭客户端输出判断根因，必须同时查看终端 A 中 Uvicorn
打印的 traceback。

#### 建议排查顺序

先查询普通 Job：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID"
```

再查询非流式事件分页：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID/events?after=0"
```

最后测试读取 backlog 后关闭：

```bash
curl --no-buffer --silent --show-error \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$JOB_ID/events/stream?after=0&follow=false"
```

如果仍返回 500，应以 API 终端 traceback 为准，不能继续猜测。

#### 相关测试风险

当前依赖会给出：

```text
StarletteDeprecationWarning:
Using httpx with starlette.testclient is deprecated; install httpx2 instead.
```

本机曾执行交互测试得到 `19 passed`；但 Codex 内部执行完整测试时，
`Starlette TestClient` 在 AnyIO blocking portal 中出现等待。该现象属于
测试客户端兼容性问题，不等同于真实 Uvicorn + curl 的生产路径失败。

后续应单独升级和验证 FastAPI、Starlette、httpx/httpx2 组合。

---

### 6. Job 长时间处于 `queued`

#### 现象

新 Job 返回：

```text
status = queued
attempt_count = 0
worker_id = null
```

多次查询状态暂时不变。

#### 根因

当时唯一的 Worker 仍在处理前一个 Job。

当前 Worker 是串行消费者：一个 Worker 同一时间只 claim 一个 Job。新 Job
只能等待前一个 Job 结束或进入 interrupt。

#### 解决方案

查看所有 Job：

```bash
python -m app.main list-jobs --limit 10
```

如果存在：

```text
旧 Job = running
新 Job = queued
```

说明只是正常排队。

不要为了“状态没变化”连续提交更多 Job，否则只会增加队列长度。

如果确实需要并发 Worker，必须使用不同 `worker_id`，并额外评估：

- Provider 并发额度。
- GPU 和内存竞争。
- 同一仓库的写入互斥。
- Job DB 和 checkpoint 并发语义。

---

### 7. `status = succeeded` 不代表 Agent 复现成功

#### 现象

Job 返回：

```text
status = succeeded
result.final_status = provider_failed
```

看起来两个状态相互矛盾。

#### 根因

它们属于不同层次：

```text
status
    Job Runtime 状态：
    Worker 是否成功领取、运行 Graph 并持久化结果。

result.final_status
    Graph 业务状态：
    Agent 实际在哪一种结果下结束。
```

因此：

```text
status = succeeded
result.final_status = provider_failed
```

表示 Worker 本身没有崩溃，并成功保存了“Provider 阶段失败”的 Graph 结果。

#### 正确判断方法

是否到达人工交互点，应同时检查：

```text
status == "waiting_for_input"
interrupt_nodes 包含目标节点
allowed_operations 包含对应 decision
```

是否完成业务目标，应检查：

```text
result.final_status
stage_error_count
reports/error_report.json
```

---

### 8. Job 没有立即进入 `waiting_for_input`

#### 现象

Job 已经是：

```text
status = running
```

但：

```text
interrupt_nodes = []
```

#### 根因

`command_selection` 不是 Graph 的第一个节点。流程还需要经过：

```text
论文解析
  -> 方法提取
  -> 仓库扫描
  -> Sparse/Dense 代码检索
  -> 论文-代码映射
  -> 实验计划
  -> command_selection
  -> interrupt()
```

启用 Dense Retrieval 后，会生成多个：

```text
analysis/retrieval/dense_reports/*.json
analysis/retrieval/evidence_packs/*.json
```

模型调用和 Embedding 请求可能持续数分钟。

#### 判断是“仍在运行”还是“卡住”

正常运行：

```text
heartbeat_at 持续更新
run_dir 中持续产生新 Artifact
result = null
```

可能异常：

```text
heartbeat_at 长时间不更新
lease 已过期
run_dir 长时间无新文件
Job 进入 reconciliation_required
```

---

### 9. 最小 structured-output probe 成功，但真实 Graph 仍失败

#### 现象

最小探测返回：

```text
succeeded = True
value = {"status": "ok", "value": 1}
```

但真实 Graph 在 `experiment_plan` 阶段返回：

```text
STRUCTURED_OUTPUT_VALIDATION_FAILED
Invalid JSON: EOF while parsing
attempt_count = 3
```

#### 根因

最小 probe 只生成非常短的 JSON，只能证明 Provider 可以返回一个简单 JSON，
不能证明它完整支持：

```text
response_format = json_schema
strict = true
```

真实 `ExperimentPlan` 包含：

- 四类实验步骤。
- Evidence。
- 多条 run command。
- 风险和未解决问题。

它的输出长度远大于最小 probe。

失败输出分别停在 JSON 列表、对象或字符串中间，例如：

```json
..."confidence":"high"}],"risk":"
```

这说明响应在 JSON 闭合前结束，但仅凭 `EOF while parsing` 还不能断言是
4096 token 预算耗尽。

因此第一轮先增加显式输出预算、压缩 Prompt，并补充复杂 schema probe，以区分
“简单 JSON 能返回”和“真实业务 schema 能稳定返回”。

#### 非终止错误与终止错误

同一个 run 中还出现过：

```text
PAPER_SECTION_EVIDENCE_INVALID
```

这些错误是局部章节证据引用失败，属于非终止错误。

真正阻止 Graph 到达 `command_selection` 的是：

```text
stage = experiment_plan
terminal = true
code = STRUCTURED_OUTPUT_VALIDATION_FAILED
```

---

### 10. 复杂 `ExperimentPlan` probe 仍只返回 74 个字符

#### 现象

完成第一轮输出预算和截断诊断修复后，执行：

```bash
python -m app.main probe-structured-output \
  --schema experiment-plan
```

得到：

```text
succeeded = False
schema = experiment-plan
method = json_schema
strict = True
attempt_count = 1
value = None
max_output_tokens = 4096
finish_reason = None
token_usage = None
output_chars = 74
truncated = True
```

trace 中保存的模型输出只到：

```json
{
  "goal": "结构化输出能力探测",
  "environment_steps": [
    {
      "description
```

JSON 字符串和对象都没有闭合，因此 Pydantic 报 `EOF while parsing`。

#### 如何解读这些字段

`truncated=True` 是程序根据“不完整 JSON + EOF”推断出的结果，并不等于
Provider 明确返回了 token 超限。

因为本次同时出现：

```text
output_chars = 74
finish_reason = None
token_usage = None
```

所以不能继续简单归因于“4096 token 不够”。如果真的是正常用完 4096 token，
通常应该看到更长输出，或者至少看到 `finish_reason=length`、completion token
usage 等诊断信息。

#### 最终根因

当前模型是 MiMo，官方兼容接口公开支持的是：

```text
response_format = {"type": "json_object"}
```

也就是 LangChain 的 `json_mode`。官方文档没有声明支持：

```text
method = json_schema
strict = true
```

OpenAI-compatible 网关接受未知参数，不代表后端真正实现了 JSON Schema strict。
因此最小 probe 偶然成功，只能证明模型能生成简单 JSON，不能证明服务端执行了
复杂 schema 约束。

另一个影响因素是 MiMo 默认开启 thinking。`max_completion_tokens` 同时覆盖
推理内容和最终可见输出，复杂 schema 可能让隐藏推理占用预算，减少最终 JSON
可用空间。

#### 解决方案

第一步，针对 MiMo 自动使用以下默认配置：

```dotenv
OPENAI_MAX_OUTPUT_TOKENS=4096
OPENAI_THINKING_MODE=disabled
STRUCTURED_OUTPUT_METHOD=json_mode
STRUCTURED_OUTPUT_STRICT=false
```

第二步，`app/model.py` 通过 `extra_body` 关闭 thinking：

```python
{
    "thinking": {
        "type": "disabled",
    }
}
```

第三步，`app/tools/structured_output_tools.py` 在 `json_mode` 下不再向 Provider
传递 `strict`，而是自动把：

```python
schema.model_json_schema()
```

转换成紧凑 JSON 后写入 Prompt。

第四步，模型返回后仍执行：

```python
schema.model_validate(parsed)
```

如果字段名、类型、枚举值或必填字段不符合 Pydantic schema，就携带具体校验
错误有限重试。达到重试上限后安全降级或终止，不把不可信结果继续传入 Graph。

最终结构化输出链路变为：

```text
Provider json_mode
        ↓ 保证返回 JSON 对象
Prompt 注入完整 JSON Schema
        ↓ 指导字段结构
Pydantic 本地校验
        ↓ 失败
携带校验错误有限重试
        ↓ 仍失败
安全降级或终止
```

#### Provider 感知默认值

为了避免 `.env` 漏写后再次回到旧模式，`app/config.py` 会根据
`OPENAI_BASE_URL` 和 `OPENAI_MODEL` 判断是否使用 MiMo：

```text
MiMo
  -> json_mode
  -> strict=False
  -> thinking=disabled

其他 Provider
  -> 默认 json_schema
  -> strict=True
  -> 不注入 MiMo thinking 扩展字段
```

显式环境变量仍然具有最高优先级，可以覆盖这些默认值。

#### 验证结果

新增测试覆盖：

- `json_mode` 不向 LangChain 传递 `strict`。
- JSON Schema 会自动加入 Prompt。
- 返回结果仍经过 Pydantic 本地校验。
- MiMo `thinking=disabled` 正确写入 `extra_body`。
- 非 MiMo Provider 不会收到 thinking 扩展字段。

定向测试：

```text
27 passed
```

非 Provider 全量回归：

```text
351 passed, 1 deselected
```

Ruff 检查通过。

#### 重新验收

先检查实际运行配置：

```bash
python -c "from app.config import settings; print({
    'thinking': settings.openai_thinking_mode,
    'method': settings.structured_output_method,
    'strict': settings.structured_output_strict,
    'max_output_tokens': settings.openai_max_output_tokens,
})"
```

MiMo 的预期配置为：

```text
thinking = disabled
method = json_mode
strict = False
max_output_tokens = 4096
```

然后重新执行：

```bash
python -m app.main probe-structured-output \
  --schema experiment-plan
```

理想结果为：

```text
succeeded = True
method = json_mode
strict = None
truncated = False
```

其中：

- 配置中的 `strict=False` 表示不请求 Provider 执行 JSON Schema strict。
- probe 中的 `strict=None` 表示 `json_mode` 调用根本没有向 Provider 传该参数。

probe 成功后还要重启 API 和 Worker，确保长驻进程加载新代码和新配置，再使用
新的 `thread_id`、`Idempotency-Key` 和 `JOB_ID` 重新提交验收 Job。

#### 参考资料

- MiMo 结构化输出：
  <https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/text-generation/structured-output>
- MiMo 深度思考：
  <https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/text-generation/deep-thinking>

---

### 11. `run-worker` 一次运行触发大量 LLM 和 Embedding 请求

#### 现象

执行：

```bash
python -m app.main run-worker \
  --worker-id phase23-worker
```

Provider 控制台中短时间出现大量调用记录：

```text
mimo-v2.5-pro
mimo-v2.5-pro
mimo-v2.5-pro
...
qwen-text-embedding-v4
qwen-text-embedding-v4
qwen-text-embedding-v4
...
```

这会造成两个疑问：

```text
1. 是不是每篇论文的每一段内容都会去找代码？
2. 换一篇论文或换一个仓库后，当前逻辑是不是仍然写死 PSTNet？
```

#### 根因

大量请求不是单个节点死循环，而是多个阶段叠加后的结果：

```text
论文 section 抽取
    -> 每个选中的 section chunk 都会调用一次 LLM
    -> 失败时还有 structured output retry 和 provider retry

代码检索
    -> Dense Retrieval 首次索引仓库时会把代码 chunk 批量送 Embedding
    -> 每个 mapping target 还会生成 query embedding

论文-代码映射
    -> 每个目标都会基于对应 Evidence Pack 调用一次映射 LLM

实验计划
    -> 还会调用一次 ExperimentPlan 结构化输出
```

旧流程还有一个结构性问题：

```text
method_modules 中的每个条目都被当成独立代码映射目标
```

这会导致：

- 中英文别名重复映射；
- 同一个核心模块被多次检索；
- 数据集、训练参数、指标和消融开关没有稳定分类；
- 目标数量随论文抽取结果波动；
- prompt 中的 PSTConv / NTU / MSR 示例会给弱模型带来领域偏置。

因此真正的问题不是“Worker 调用了一次却应该只有一次 LLM 请求”，而是：

```text
分析阶段没有先把论文事实压缩成有限、去重、可审计的映射目标
```

#### 重要澄清

Agent 不应该、也不会为论文中的每一句话寻找代码。

不进入代码映射的内容包括：

- Abstract 中的背景描述；
- Introduction 中的动机；
- Related Work 中对其他论文的介绍；
- Conclusion 中的总结；
- 纯理论推导或没有实现载体的文字。

真正需要进入代码映射的，是对复现有直接行动价值的事实。

#### 最终解决方案

新增确定性的 `CodeMappingTarget` 层，把论文事实先压缩成五类目标：

```text
core_method
    核心模型、算子、网络模块

data_pipeline
    数据集、DataLoader、预处理脚本

training_config
    optimizer、learning rate、batch size、epochs 等训练配置

evaluation_metric
    accuracy、mIoU 等评估指标

ablation_switch
    消融变体、baseline、功能开关
```

新的链路变为：

```text
论文 section 抽取
    ↓
PaperSummary + MethodModule
    ↓
程序确定性分类、去重、别名合并、预算截断
    ↓
CodeMappingTarget[]
    ↓
每个 target 生成一个 Evidence Pack
    ↓
每个 target 最多执行一次逻辑映射调用
```

这里的“逻辑调用”仍可能因为以下原因产生多个 HTTP 请求：

```text
structured output retry
provider transport retry
embedding batch
```

但目标数量已经由程序控制，不再任由模型抽取结果膨胀。

#### 预算控制

在 `app/config.py` 和 `.env.example` 中增加：

```dotenv
PAPER_MAX_SECTION_LLM_CALLS=12

MAPPING_MAX_TARGETS=12
MAPPING_MAX_CORE_METHOD_TARGETS=6
MAPPING_MAX_DATA_PIPELINE_TARGETS=2
MAPPING_MAX_TRAINING_CONFIG_TARGETS=1
MAPPING_MAX_EVALUATION_METRIC_TARGETS=2
MAPPING_MAX_ABLATION_SWITCH_TARGETS=1
```

预算分两层：

```text
第一层：限制论文 section 抽取调用数
第二层：限制代码映射目标数量
```

这样即使论文很长，前置分析阶段的调用规模也有上界。

#### 去除 PSTNet 运行时硬编码

原先的风险是：

```text
PST convolution / PST卷积 / PSTConv 等领域别名写在 Python 代码里
```

这会让新论文默认带着 PSTNet 的术语假设运行。

最终改成：

```text
通用规则
    自动处理 Long Name (ABC) Block 与 ABC Block 这类括号缩写

可选配置
    通过 MAPPING_ALIASES_PATH 加载某一篇论文或某个领域的 alias JSON
```

新增示例配置：

```text
config/mapping_aliases.example.json
```

对应环境变量：

```dotenv
MAPPING_ALIASES_PATH=config/mapping_aliases.local.json
```

如果环境变量为空或文件不存在，Agent 不加载任何论文专属别名，只使用通用去重规则。

#### Prompt 去偏置

同步清理 prompt 中的固定领域示例：

```text
PSTConv
NTU RGB+D
MSR-Action3D
```

这些示例被替换为通用模块、通用数据集约束和通用实验设置表述，避免模型在换论文后
仍向 PSTNet 方向联想。

#### 代码涉及文件

本次解决方案主要涉及：

```text
app/schemas.py
app/config.py
app/state.py
app/tools/mapping_target_tools.py
app/nodes/method_extractor_node.py
app/nodes/code_search_node.py
app/nodes/mapping_node.py
app/nodes/final_report_node.py
app/prompts/mapping_prompt.py
app/prompts/paper_prompt.py
app/prompts/paper_section_prompt.py
app/retrieval/query_builder.py
app/retrieval/indexer.py
.env.example
config/mapping_aliases.example.json
```

#### 如何验证

定向测试：

```bash
python -m pytest \
  tests/test_mapping_targets.py \
  tests/test_code_search_mapping_targets.py \
  tests/test_analysis_planning_structured_nodes.py \
  tests/test_method_extractor_hierarchical.py \
  tests/test_mapping_evidence_boundary.py \
  tests/test_semantic_query_builder.py \
  tests/test_final_report_node.py \
  tests/test_retrieval_eval.py \
  -q
```

本次验证结果：

```text
28 passed
```

静态检查：

```bash
python -m ruff check \
  app/retrieval/indexer.py \
  app/tools/mapping_target_tools.py \
  app/nodes/method_extractor_node.py \
  app/prompts/mapping_prompt.py \
  app/prompts/paper_prompt.py \
  app/prompts/paper_section_prompt.py \
  tests/test_mapping_targets.py
```

本次验证结果：

```text
All checks passed!
```

#### 换论文和换仓库时的边界

换论文时：

```text
运行时代码不会再默认套用 PSTNet alias；
但如果新论文有大量特殊缩写，建议单独配置 mapping_aliases.local.json。
```

换仓库时：

```text
仍然必须使用对应仓库的 execution_profile_id。
```

原因是 `ExecutionProfile` 不只是路径配置，它还定义：

- 允许在哪个 workspace 下运行；
- 可以写入哪些目录；
- 允许执行哪些程序；
- 是否允许网络；
- 资源预算和进程监管策略。

因此 `config/execution_profiles.local.json` 中固定的 PSTNet 路径不是论文理解硬编码，
而是当前本机复现仓库的安全白名单。换仓库应新增或生成新的 profile，而不是让一个
通用 `local` profile 覆盖所有仓库。

#### 复盘结论

这次问题的核心不是“LLM 调用太多”本身，而是：

```text
没有在调用 Provider 前完成目标归并和预算裁剪
```

最终原则是：

```text
LLM 负责抽取有证据的论文事实
程序负责分类、去重、预算和身份绑定
检索器负责生成有限 Evidence Pack
LLM 只能在 Evidence Pack 内做映射判断
```

这能同时解决：

- 调用次数失控；
- 同义模块重复映射；
- prompt 领域偏置；
- 换论文时被 PSTNet 规则影响；
- 换仓库时执行边界不清晰。

---

## 三、本次代码修复

### 1. 显式设置模型输出预算

在 `app/config.py` 中增加：

```python
openai_max_output_tokens: int = int(
    os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "4096")
)
```

在 `app/model.py` 中传给 `ChatOpenAI`：

```python
max_completion_tokens=settings.openai_max_output_tokens
```

`.env.example` 同步增加：

```dotenv
OPENAI_MAX_OUTPUT_TOKENS=4096
```

这避免 OpenAI-compatible Provider 使用过小的默认输出限制。

---

### 2. 对齐 MiMo 的真实结构化输出能力

运行时会根据 Provider 地址和模型名选择安全默认值。MiMo 默认使用：

```dotenv
OPENAI_MAX_OUTPUT_TOKENS=4096
OPENAI_THINKING_MODE=disabled
STRUCTURED_OUTPUT_METHOD=json_mode
STRUCTURED_OUTPUT_STRICT=false
```

`app/model.py` 通过 `extra_body` 传递：

```python
{
    "thinking": {
        "type": "disabled",
    }
}
```

`app/tools/structured_output_tools.py` 在 `json_mode` 下：

1. 不向 LangChain/Provider 传递不受支持的 `strict` 参数。
2. 自动把 `schema.model_json_schema()` 注入 Prompt。
3. 继续使用 Pydantic 在本地校验字段、类型和枚举值。
4. 校验失败时最多进行配置数量的有限重试。

这不是放弃结构约束，而是把“服务端无法保证的 strict”转移到程序能够可靠控制
的本地校验层。

参考：

- <https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/text-generation/structured-output>
- <https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/text-generation/deep-thinking>

---

### 3. 压缩 `EXPERIMENT_PLAN_PROMPT`

旧 Prompt 同时包含：

- 完整字段说明。
- 嵌套 Evidence 字段说明。
- 大段 JSON 示例。
- Provider 已经收到的 JSON Schema。

这些内容重复且容易诱导模型输出过长。

新的 `app/prompts/plan_prompt.py` 只保留业务约束，并限制规模：

```text
每类 ExperimentStep 最多 3 项
run_commands 最多 4 项
risks / unresolved_questions 最多 6 项
每个步骤 evidence 最多 1 项
```

Schema 仍由：

```python
llm.with_structured_output(
    ExperimentPlan,
    method="json_mode",
)
```

配合 Prompt 中的 JSON Schema 和本地 Pydantic 负责，因此压缩 Prompt 不会取消
结构校验。

---

### 4. 压缩输入上下文 JSON

`experiment_plan_node` 原来使用：

```python
json.dumps(..., indent=2)
```

现在使用：

```python
json.dumps(
    ...,
    ensure_ascii=False,
    separators=(",", ":"),
)
```

这会移除不必要的空格和缩进，减少发送给模型的输入体积。

---

### 5. 捕获 `finish_reason` 和 token usage

`include_raw=True` 不一定能覆盖所有异常路径。

某些 LangChain parser 会在返回 `raw` 字典之前直接抛出 Pydantic
`ValidationError`。因此新增 `_ResponseMetadataCapture` callback，在 parser
运行前捕获：

```text
finish_reason
token_usage
```

每次结构化尝试现在还记录：

```text
output_chars
truncated
raw_preview
```

这些字段会写入：

```text
traces/structured/*_structured_attempts.json
```

最终失败时，最后一次尝试的诊断信息也会进入：

```text
reports/error_report.json
```

---

### 6. 从 Pydantic 错误恢复被截断的原始输出

当 Pydantic 抛出 JSON 解析错误时，错误详情中的 `input` 可能仍包含模型返回的
原始字符串。

程序现在会提取该字符串并记录 bounded preview 和字符数，避免出现：

```text
raw_preview = null
```

却无法判断模型到底返回了什么的情况。

---

### 7. 增加截断感知重试

程序会根据以下证据识别截断：

```text
finish_reason = length
EOF while parsing
unterminated string
unexpected end of JSON
```

普通 Schema 错误继续使用“携带 Schema 的修正重试”。

截断错误改用紧凑重试：

```text
不重复附加完整 Schema
使用单行紧凑 JSON
减少列表项目
缩短字符串
确保所有括号和字符串闭合
```

这样避免重试 Prompt 越来越大、再次触发截断。

---

### 8. 增加真实 `ExperimentPlan` probe

最小 probe 保留：

```bash
python -m app.main probe-structured-output
```

新增复杂 Schema probe：

```bash
python -m app.main probe-structured-output \
  --schema experiment-plan
```

终端会显示：

```text
succeeded
schema
max_output_tokens
finish_reason
token_usage
output_chars
truncated
trace_path
```

只有复杂 probe 成功，才能说明当前 Provider 至少具备生成代表性
`ExperimentPlan` 的能力。

---

## 四、测试结果

本次新增和更新了以下测试能力：

- 模型工厂传递显式输出预算。
- 截断 JSON 被正确识别。
- Pydantic 异常路径恢复 raw preview。
- callback 捕获 `finish_reason=length`。
- token usage 写入 attempt。
- 截断后使用紧凑重试。
- StageError 暴露最后一次诊断。
- 测试 Fake Runnable 接受 LangChain `config`。

第一次修复的定向测试结果：

```text
25 passed
```

完成 `json_mode + thinking disabled` 适配后的定向测试结果：

```text
27 passed
```

排除 Provider 和当前 Codex 环境中阻塞的两个 TestClient 文件后：

```text
349 passed, 1 deselected
```

Ruff 检查通过。

---

## 五、重新验收步骤

### 1. 停止旧 Worker

旧 Worker 已加载旧代码，必须在 Worker 终端按：

```text
Ctrl+C
```

然后重新启动。

### 2. 先运行复杂 Schema probe

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent

python -m app.main probe-structured-output \
  --schema experiment-plan
```

继续验收前至少应满足：

```text
succeeded = True
method = json_mode
strict = None
truncated = False
```

先确认当前进程读取到的配置：

```bash
python -c "from app.config import settings; print({
    'thinking': settings.openai_thinking_mode,
    'method': settings.structured_output_method,
    'strict': settings.structured_output_strict,
    'max_output_tokens': settings.openai_max_output_tokens,
})"
```

预期：

```text
thinking = disabled
method = json_mode
strict = False
max_output_tokens = 4096
```

注意：配置中的 `strict=False` 表示不请求 Provider 执行 JSON Schema strict；
probe 结果中的 `strict=None` 表示 `json_mode` 调用根本没有向 Provider 传该参数。

### 3. 重启 Worker

```bash
python -m app.main run-worker \
  --worker-id phase23-worker
```

### 4. 使用新身份提交 Job

已经终结的 Job 不能修改请求后继续执行。必须使用新的：

```text
thread_id
Idempotency-Key
JOB_ID
```

请求必须指定：

```json
"execution_profile_id": "pstnet-local-supervised"
```

### 5. 监控三个层次

Job 调度：

```text
status
attempt_count
heartbeat_at
lease_expires_at
```

人工交互：

```text
interrupt_nodes
allowed_operations
wait_generation
```

Graph 业务结果：

```text
result.final_status
stage_error_count
reports/error_report.json
```

### 6. 理想结果

```text
status = waiting_for_input
interrupt_nodes = ["command_selection"]
allowed_operations 包含 command_selection decision
```

---

## 六、最终排查清单

如果 Job 没有进入 `waiting_for_input`，按以下顺序检查：

1. `execution_profile_id` 是否存在。
2. API 和 curl 是否使用相同 Bearer Token。
3. Worker 是否正在运行。
4. Job 是 `queued`、`running` 还是终态。
5. `heartbeat_at` 是否更新。
6. 是否有旧 Job 占用唯一 Worker。
7. `run_dir` 是否持续生成 Artifact。
8. `result.final_status` 是什么。
9. `error_report.json` 中哪个错误是 `terminal=true`。
10. structured trace 是否显示 `truncated=true`。
11. `finish_reason` 是否为 `length`。
12. `OPENAI_MAX_OUTPUT_TOKENS` 是否生效。
13. 真实 `ExperimentPlan` probe 是否成功。
14. MiMo 是否使用 `STRUCTURED_OUTPUT_METHOD=json_mode`。
15. `OPENAI_THINKING_MODE` 是否为 `disabled`。
16. 修改配置后 API 和 Worker 是否都已重启。

不要只根据一个 `status` 字段判断整个 Agent 是否成功。

---

## 七、核心经验

本次最重要的经验可以总结为：

```text
认证成功
    不代表 profile 正确

Worker succeeded
    不代表 Graph succeeded

Graph running
    不代表已经到达 interrupt

最小 schema probe 成功
    不代表复杂 schema 不会被截断

兼容接口接受 strict 参数
    不代表 Provider 实现 JSON Schema strict

Provider JSON mode
    不代表字段自动符合 Pydantic schema
```

完整判断必须同时依赖：

```text
HTTP 状态
+ Job Runtime 状态
+ LangGraph interrupt
+ result.final_status
+ StageError
+ structured trace
```
