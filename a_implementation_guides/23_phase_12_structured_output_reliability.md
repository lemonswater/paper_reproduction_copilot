# 23. Phase 12：Structured Output Reliability

这一阶段不急着让 Agent 获得修改仓库文件的能力。

先解决一个更基础的问题：

```text
模型有时知道答案
但没有按照程序要求的 schema 返回
导致节点 ValidationError、流程中断或只能 no_repair
```

本阶段要把结构化调用升级成一条可观测、可重试、可降级的可靠链：

```text
确定性规则优先
        ↓ 无规则命中
JSON Schema strict 约束
        ↓
Pydantic 结构与语义校验
        ↓ 失败
携带 validation error 重试 1～2 次
        ↓ 仍失败
确定性 fallback / no_repair
        ↓
保存每次 attempt artifact
```

完成这一阶段后，再进入：

```text
Phase 13：Manual File Repair Review 与 Patch-Level Verification
```

这样可以避免把不稳定的模型输出直接升级成能够修改代码仓库的 patch。

---

## 一、本阶段解决什么问题

你当前已经使用了：

```python
llm.with_structured_output(RepairProposal, include_raw=True)
```

也已经使用：

```python
RepairProposal.model_validate(parsed)
```

但目前仍然存在四个缺口。

### 缺口 1：没有显式开启 strict

当前 LangChain 默认方法虽然已经是 `json_schema`，但代码没有明确写出：

```python
method="json_schema"
strict=True
```

这会让“当前依赖默认值是什么”变得不够清楚，也不方便做 provider 能力检查。

### 缺口 2：第一次校验失败就降级

当前流程大致是：

```text
模型返回
  -> Pydantic 失败
  -> no_repair
```

但很多格式错误其实很容易纠正，例如：

```text
source_error_type 缺失
kind 枚举值拼错
steps 中漏了 risk
bounded 返回成字符串
```

更合理的流程是把具体错误反馈给模型，再尝试一次。

### 缺口 3：只检查字段类型，没有完整检查字段关系

例如下面这个对象可能通过基础字段校验：

```json
{
  "source_error_type": "cuda_oom",
  "kind": "edit_command",
  "summary": "reduce batch size",
  "root_cause": "GPU memory is insufficient",
  "repaired_command": null,
  "bounded": true
}
```

但它在语义上不合法，因为：

```text
kind = edit_command
却没有 repaired_command
```

因此还需要 Pydantic `model_validator`。

### 缺口 4：失败过程不可观测

目前你只能看到最终：

```text
模型输出不符合 RepairProposal schema
```

却看不到：

- 第几次失败
- 使用了什么 structured output method
- 是否开启 strict
- Pydantic 具体报了什么
- 模型上一轮返回了什么摘要
- 最终是否使用 fallback

本阶段要把这些信息落盘。

---

## 二、本阶段边界

### 本阶段要做

- 显式启用 `json_schema + strict=True`
- 抽取通用结构化调用工具
- 增加最多两次格式修正重试
- 增加 Pydantic 语义校验
- 保存结构化调用 attempt artifact
- 增加 provider capability probe
- 接入全部五个 LLM 结构化输出节点：
  - `PaperSummary`
  - `ModuleMapping`
  - `ExperimentPlan`
  - `DebugReport`
  - `RepairProposal`
- 保留确定性规则和安全 fallback

### 本阶段不做

- 不修改论文仓库文件
- 不生成或应用 patch
- 不让模型绕过人工审批
- 不无限重试
- 不因为结构化输出失败而自动切换到更宽松、不可审计的自由文本执行
- 不新增新的 LLM 决策节点
- 不把非 LLM 节点强行改造成 structured output 调用

这里尤其要强调：

```text
retry 只负责修正结构
不负责不断重新思考直到模型给出“想要的答案”
```

因此最多重试两次。

---

## 三、最终架构

本阶段完成后的调用关系建议是：

```text
method_extractor / mapping / experiment_plan
log_debug / repair_planner
                ↓
输入和确定性规则检查
                ↓ 需要调用模型
invoke_structured_with_retry()
                ↓
ChatOpenAI.with_structured_output(
    method="json_schema",
    strict=True,
    include_raw=True,
)
                ↓
Pydantic.model_validate()
                ↓
成功 ─────────────────→ 返回结构化对象
                ↓ 失败
build_validation_retry_prompt()
                ↓
有限重试
                ↓ 仍失败
节点自己的安全 fallback
```

为什么 fallback 仍然留在节点中？

因为通用工具只知道：

```text
结构化调用失败了
```

但只有业务节点知道应该如何降级：

- `log_debug_node` 可以生成保守 `DebugReport`
- `repair_planner_node` 应该返回 `no_repair`
- `method_extractor_node` 应该返回不含方法模块的保守摘要
- `mapping_node` 应该只降级当前失败的模块，不丢弃其他模块
- `experiment_plan_node` 应该返回不含 `run_commands` 的保守计划

通用基础设施不应该替业务节点决定降级语义。

---

## 四、涉及文件

建议新增：

```text
app/tools/structured_output_tools.py
tests/test_structured_output_tools.py
tests/test_repair_proposal_semantics.py
```

建议修改：

```text
app/config.py
app/schemas.py
app/nodes/method_extractor_node.py
app/nodes/mapping_node.py
app/nodes/experiment_plan_node.py
app/nodes/log_debug_node.py
app/nodes/repair_planner_node.py
app/tools/artifact_tools.py
app/main.py
tests/test_analysis_planning_structured_nodes.py
tests/test_smoke_repair_flow.py
```

本阶段不需要修改图拓扑：

```text
app/graph.py
```

因为我们只是在增强节点内部的结构化调用可靠性。

---

## 五、前置检查：确认本地 LangChain 支持 strict

先执行：

```bash
python -c "import inspect; from langchain_openai import ChatOpenAI; print(inspect.signature(ChatOpenAI.with_structured_output))"
```

当前项目环境应能看到类似：

```text
method: Literal['function_calling', 'json_mode', 'json_schema']
strict: bool | None
include_raw: bool
```

这只能证明：

```text
本地 langchain-openai 客户端支持这些参数
```

不能证明：

```text
OPENAI_BASE_URL 对应的模型服务完整支持 json_schema strict
```

因此后面还要增加真实 provider probe。

---

## 六、配置 structured output 策略

修改 [app/config.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/config.py:1)。

先增加一个布尔环境变量解析函数：

```python
def _env_bool(name: str, default: bool) -> bool:
    """
    把常见环境变量字符串转换为 bool。

    接受：
    - true / false
    - 1 / 0
    - yes / no
    - on / off

    遇到无法识别的值时直接报错，避免配置悄悄失效。
    """
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"invalid boolean environment variable {name}={raw_value!r}")
```

然后在 `Settings` 中增加：

```python
@dataclass
class Settings:
    # ...保留原字段...

    # 结构化输出优先使用 provider 原生 JSON Schema。
    structured_output_method: str = os.getenv(
        "STRUCTURED_OUTPUT_METHOD",
        "json_schema",
    )

    # strict=True 时，服务端如果支持，会在生成阶段约束 JSON Schema。
    structured_output_strict: bool = _env_bool(
        "STRUCTURED_OUTPUT_STRICT",
        True,
    )

    # 这里表示“第一次失败后额外重试几次”。
    # 设置为 2 时，总调用次数最多为 3 次。
    structured_output_max_retries: int = int(
        os.getenv("STRUCTURED_OUTPUT_MAX_RETRIES", "2")
    )

    # attempt artifact 只保存原始输出预览，避免文件无限增大。
    structured_output_raw_preview_chars: int = int(
        os.getenv("STRUCTURED_OUTPUT_RAW_PREVIEW_CHARS", "2000")
    )
```

建议在 `.env.example` 中增加：

```dotenv
STRUCTURED_OUTPUT_METHOD=json_schema
STRUCTURED_OUTPUT_STRICT=true
STRUCTURED_OUTPUT_MAX_RETRIES=2
STRUCTURED_OUTPUT_RAW_PREVIEW_CHARS=2000
```

为什么把这些放进配置？

因为不同 provider 的能力不同。

如果后端明确不支持 `json_schema`，你可以临时设置：

```dotenv
STRUCTURED_OUTPUT_METHOD=function_calling
STRUCTURED_OUTPUT_STRICT=false
```

但此时必须继续保留：

```text
Pydantic 校验
有限重试
安全 fallback
attempt artifact
```

不要退回到“相信模型自然语言输出”。

---

## 七、增强 RepairProposal 语义校验

修改 [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:197)。

当前文件已经导入：

```python
from pydantic import BaseModel, Field, model_validator
```

在 `RepairProposal` 中增加：

```python
class RepairProposal(BaseModel):
    proposal_id: str | None = None
    source_error_type: str
    kind: Literal["edit_command", "manual_only", "no_repair"] = "no_repair"
    summary: str
    root_cause: str
    repaired_command: str | None = None
    changed_arguments: list[str] = Field(default_factory=list)
    steps: list[RepairStep] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    bounded: bool = True

    @model_validator(mode="after")
    def validate_repair_semantics(self) -> "RepairProposal":
        """
        字段类型正确不代表 proposal 可以安全进入 repair 链。

        这里校验字段之间的业务关系：
        - 所有 proposal 都必须是 bounded；
        - edit_command 必须给出完整命令；
        - 非 edit_command 不允许偷偷携带命令；
        - edit_command 必须说明如何验证和回滚。
        """
        if self.bounded is not True:
            raise ValueError("repair proposal must keep bounded=true")

        if self.kind == "edit_command":
            if not self.repaired_command or not self.repaired_command.strip():
                raise ValueError("edit_command requires repaired_command")
            if not self.changed_arguments:
                raise ValueError("edit_command requires changed_arguments")
            if not self.verification_steps:
                raise ValueError("edit_command requires verification_steps")
            if not self.rollback_steps:
                raise ValueError("edit_command requires rollback_steps")
        elif self.repaired_command is not None:
            raise ValueError(
                "manual_only/no_repair must not contain repaired_command"
            )

        return self
```

为什么 `manual_only` 不能携带 `repaired_command`？

因为图路由通常会检查：

```python
proposal.get("kind") == "edit_command"
```

虽然当前路由不会执行 `manual_only`，但把可执行命令混在里面会让审计语义变得模糊。

结构化对象最好做到：

```text
不可执行 proposal 中就不存在可执行命令
```

---

## 八、新增通用 structured output 工具

新建：

```text
app/tools/structured_output_tools.py
```

完整参考实现如下。

```python
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError


SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass
class StructuredOutputAttempt:
    """记录一次模型结构化输出尝试，不保存完整敏感上下文。"""

    attempt_number: int
    status: str
    prompt_kind: str
    error_type: str | None = None
    error_message: str | None = None
    raw_preview: str | None = None


@dataclass
class StructuredInvocationResult(Generic[SchemaT]):
    """通用调用结果；value=None 表示所有 attempt 都失败。"""

    value: SchemaT | None
    attempts: list[StructuredOutputAttempt]
    method: str
    strict: bool
    max_retries: int

    @property
    def succeeded(self) -> bool:
        return self.value is not None


def _raw_to_preview(raw: Any, max_chars: int) -> str | None:
    """
    从 LangChain AIMessage 或普通对象提取可审计预览。

    只保存模型输出预览，不保存完整 prompt，避免论文正文、路径或其他
    上下文无限复制到日志中。
    """
    if raw is None:
        return None

    content = getattr(raw, "content", raw)
    if isinstance(content, str):
        text = content
    else:
        try:
            text = json.dumps(content, ensure_ascii=False, default=str)
        except TypeError:
            text = str(content)

    return text[:max_chars]


def _build_validation_retry_prompt(
    *,
    original_prompt: str,
    schema: type[BaseModel],
    validation_error: str,
    previous_raw_preview: str | None,
) -> str:
    """
    把上一轮具体错误反馈给模型。

    这里强调“只修结构”，避免每次 retry 都重新生成完全不同的方案。
    """
    schema_json = json.dumps(
        schema.model_json_schema(),
        ensure_ascii=False,
        indent=2,
    )

    return f"""
{original_prompt}

上一轮结构化输出没有通过本地校验。

Validation error:
{validation_error}

Previous output preview:
{previous_raw_preview or "<unavailable>"}

Required JSON Schema:
{schema_json}

请只修复字段名、字段类型、枚举值和缺失字段。
不要增加新的事实，不要改变原有证据，不要输出解释、Markdown 或代码围栏。
只返回符合 schema 的 JSON 对象。
""".strip()


def invoke_structured_with_retry(
    *,
    llm: Any,
    schema: type[SchemaT],
    prompt: str,
    method: str = "json_schema",
    strict: bool = True,
    max_retries: int = 2,
    raw_preview_chars: int = 2000,
) -> StructuredInvocationResult[SchemaT]:
    """
    使用 provider structured output + Pydantic 完成有限重试。

    max_retries 表示第一次失败之后额外尝试的次数：
    - 0：总共调用 1 次；
    - 1：总共最多调用 2 次；
    - 2：总共最多调用 3 次。

    这里只重试结构/语义校验失败。
    API 连接失败或 provider 不支持 json_schema 时直接返回失败，避免对
    同一个能力错误无意义地连续请求。
    """
    if method not in {"json_schema", "function_calling", "json_mode"}:
        raise ValueError(f"unsupported structured output method: {method}")
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    attempts: list[StructuredOutputAttempt] = []

    try:
        structured_llm = llm.with_structured_output(
            schema,
            method=method,
            strict=strict,
            include_raw=True,
        )
    except Exception as exc:
        # 某些客户端会在创建 structured runnable 时就检查 schema、method
        # 或 strict 参数。此时请求尚未发送，因此与 invoke_error 分开记录。
        attempts.append(
            StructuredOutputAttempt(
                attempt_number=0,
                status="configuration_error",
                prompt_kind="configuration",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        )
        return StructuredInvocationResult(
            value=None,
            attempts=attempts,
            method=method,
            strict=strict,
            max_retries=max_retries,
        )

    current_prompt = prompt

    for attempt_index in range(max_retries + 1):
        attempt_number = attempt_index + 1
        prompt_kind = "original" if attempt_index == 0 else "validation_retry"

        try:
            response = structured_llm.invoke(current_prompt)
        except Exception as exc:
            # 这是 LLM/provider 边界。不同 OpenAI-compatible 服务可能抛出
            # 不同异常，因此记录异常类型后受控返回，由节点决定 fallback。
            attempts.append(
                StructuredOutputAttempt(
                    attempt_number=attempt_number,
                    status="invoke_error",
                    prompt_kind=prompt_kind,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
            break

        if isinstance(response, schema):
            parsed = response
            raw = None
            parsing_error = None
        elif isinstance(response, dict):
            parsed = response.get("parsed")
            raw = response.get("raw")
            parsing_error = response.get("parsing_error")
        else:
            parsed = response
            raw = None
            parsing_error = None

        raw_preview = _raw_to_preview(raw, raw_preview_chars)

        try:
            if parsed is None:
                raise ValueError(
                    str(parsing_error or "structured output parsed value is None")
                )

            value = schema.model_validate(parsed)
        except (TypeError, ValueError, ValidationError) as exc:
            error_message = str(exc)
            attempts.append(
                StructuredOutputAttempt(
                    attempt_number=attempt_number,
                    status="validation_error",
                    prompt_kind=prompt_kind,
                    error_type=type(exc).__name__,
                    error_message=error_message,
                    raw_preview=raw_preview,
                )
            )

            if attempt_index >= max_retries:
                break

            current_prompt = _build_validation_retry_prompt(
                original_prompt=prompt,
                schema=schema,
                validation_error=error_message,
                previous_raw_preview=raw_preview,
            )
            continue

        attempts.append(
            StructuredOutputAttempt(
                attempt_number=attempt_number,
                status="succeeded",
                prompt_kind=prompt_kind,
                raw_preview=raw_preview,
            )
        )
        return StructuredInvocationResult(
            value=value,
            attempts=attempts,
            method=method,
            strict=strict,
            max_retries=max_retries,
        )

    return StructuredInvocationResult(
        value=None,
        attempts=attempts,
        method=method,
        strict=strict,
        max_retries=max_retries,
    )


def write_structured_output_trace(
    *,
    result: StructuredInvocationResult[Any],
    node_name: str,
    schema_name: str,
    output_dir: Path,
    fallback_used: bool,
) -> Path:
    """把结构化调用过程写成独立 artifact，方便调试和评测。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{node_name}_structured_attempts.json"

    payload = {
        "node_name": node_name,
        "schema_name": schema_name,
        "method": result.method,
        "strict": result.strict,
        "max_retries": result.max_retries,
        "succeeded": result.succeeded,
        "fallback_used": fallback_used,
        "attempt_count": len(result.attempts),
        "attempts": [asdict(item) for item in result.attempts],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
```

### 为什么不在工具里直接返回 fallback

不要这样设计：

```python
invoke_structured_with_retry(..., fallback=RepairProposal(...))
```

第一版最好让工具只返回：

```text
value
attempts
method
strict
```

节点自己决定 fallback，可以让基础设施和业务语义保持分离。

### 为什么 invoke error 不继续结构重试

下面这些错误不是修改 Prompt 能解决的：

- DNS 失败
- API key 错误
- provider 不支持 `response_format=json_schema`
- 服务端 5xx
- 请求超时

SDK 自身通常已经有传输层重试。

本阶段的 retry 专门解决：

```text
模型已返回内容
但内容没有通过结构或语义校验
```

这是两个不同层次的问题。

---

## 九、让 structured attempt 进入 artifact 分层

修改 [app/tools/artifact_tools.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/tools/artifact_tools.py:75)。

在 `classify_output_file()` 前半部分增加：

```python
def classify_output_file(path: str) -> str:
    name = Path(path).name

    # 结构化调用 attempt 属于调试与可观测性产物。
    # 使用后缀判断，便于不同节点使用自己的文件名。
    if name.endswith("_structured_attempts.json"):
        return "debug"

    # ...保留原分类逻辑...
```

最终会得到类似：

```text
runs/<run_id>/debug/
  method_extractor_structured_attempts.json
  mapping_00_p4d-convolution_structured_attempts.json
  mapping_01_transformer_structured_attempts.json
  experiment_plan_structured_attempts.json
  log_debug_structured_attempts.json
  repair_planner_structured_attempts.json
```

为什么归到 `debug/` 而不是 `reports/`？

因为它们主要用于：

- 排查模型格式失败
- 评估 provider structured output 能力
- 统计 retry 次数
- 判断 fallback 是否频繁触发

它们不是面向最终用户的主报告。

---

## 十、接入 log_debug_node

修改 [app/nodes/log_debug_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/log_debug_node.py:1)。

先调整 import：

```python
import json

from app.config import settings
from app.model import get_chat_model
from app.prompts.debug_prompt import DEBUG_PROMPT
from app.schemas import DebugReport
from app.tools.log_tools import classify_error_heuristic, extract_traceback, read_log
from app.tools.structured_output_tools import (
    invoke_structured_with_retry,
    write_structured_output_trace,
)
```

然后把原来的直接调用：

```python
structured_llm = llm.with_structured_output(...)
result = structured_llm.invoke(...)
```

替换为：

```python
def log_debug_node(state: dict) -> dict:
    log_path = state.get("log_path")
    if not log_path:
        return {"error": "log_path is required"}

    log_text = read_log(log_path)
    traceback = extract_traceback(log_text)
    error_type = classify_error_heuristic(traceback)
    trace_path = None

    # 高置信度规则优先，不需要浪费 LLM 调用。
    if error_type == "cuda_oom":
        report = _build_cuda_oom_report()

    # 没有错误证据时也不让模型硬猜。
    elif not traceback.strip():
        report = _build_fallback_report(
            error_type=error_type,
            traceback=traceback,
            log_path=log_path,
        )

    else:
        prompt = DEBUG_PROMPT.format(
            error_type=error_type,
            traceback=traceback,
            repo_map=json.dumps(
                state.get("repo_map", {}),
                ensure_ascii=False,
                indent=2,
            ),
            experiment_plan=json.dumps(
                state.get("experiment_plan", {}),
                ensure_ascii=False,
                indent=2,
            ),
        )

        invocation = invoke_structured_with_retry(
            llm=get_chat_model(temperature=0),
            schema=DebugReport,
            prompt=prompt,
            method=settings.structured_output_method,
            strict=settings.structured_output_strict,
            max_retries=settings.structured_output_max_retries,
            raw_preview_chars=settings.structured_output_raw_preview_chars,
        )

        if invocation.value is not None:
            report = invocation.value

            # error_type 来自本地启发式，不允许模型擅自改变路由语义。
            if report.error_type != error_type:
                report = report.model_copy(update={"error_type": error_type})
        else:
            report = _build_fallback_report(
                error_type=error_type,
                traceback=traceback,
                log_path=log_path,
            )

        trace_path = write_structured_output_trace(
            result=invocation,
            node_name="log_debug",
            schema_name="DebugReport",
            output_dir=settings.output_dir,
            fallback_used=invocation.value is None,
        )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "debug_report.json"
    md_path = settings.output_dir / "debug_report.md"

    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_render_debug_markdown(report), encoding="utf-8")

    output_files = [
        *state.get("output_files", []),
        str(json_path),
        str(md_path),
    ]
    if trace_path is not None:
        output_files.append(str(trace_path))

    return {
        "debug_report": report.model_dump(),
        "output_files": output_files,
    }
```

### 为什么本地 error_type 优先

如果 traceback 明确包含：

```text
CUDA out of memory
```

本地规则分类为：

```text
cuda_oom
```

模型却返回：

```text
dependency_missing
```

不能让模型改变后续 repair 路由。

因此这里使用：

```python
report.model_copy(update={"error_type": error_type})
```

这体现的是：

```text
确定性证据控制路由
LLM 负责补充解释
```

---

## 十一、接入 repair_planner_node

修改 [app/nodes/repair_planner_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/repair_planner_node.py:1)。

增加 import：

```python
from app.tools.structured_output_tools import (
    invoke_structured_with_retry,
    write_structured_output_trace,
)
```

保留现有：

```python
_build_cuda_oom_repair_proposal()
_build_no_repair_proposal()
```

然后把模型分支改成：

```python
def repair_planner_node(state: dict) -> dict:
    debug_report = state.get("debug_report")
    if not debug_report:
        # 建议继续保留你现有的 missing debug_report fallback。
        return {...}

    error_type = str(debug_report.get("error_type") or "unknown")
    trace_path = None

    deterministic_proposal = None
    if error_type == "cuda_oom":
        deterministic_proposal = _build_cuda_oom_repair_proposal(
            state.get("pending_action") or {}
        )

    if deterministic_proposal is not None:
        proposal = deterministic_proposal

    elif error_type == "unknown":
        proposal = _build_no_repair_proposal(
            error_type=error_type,
            summary="错误证据不足，不能生成可靠的自动修复命令。",
            root_cause="调试报告未识别出具体错误类型。",
        )

    else:
        prompt = REPAIR_PROMPT.format(
            execution_mode=state.get("active_execution_mode", "unknown"),
            pending_action=json.dumps(
                state.get("pending_action", {}),
                ensure_ascii=False,
                indent=2,
            ),
            preflight_report=json.dumps(
                state.get("preflight_report", {}),
                ensure_ascii=False,
                indent=2,
            ),
            smoke_test_report=json.dumps(
                state.get("smoke_test_report", {}),
                ensure_ascii=False,
                indent=2,
            ),
            debug_report=json.dumps(
                debug_report,
                ensure_ascii=False,
                indent=2,
            ),
        )

        invocation = invoke_structured_with_retry(
            llm=get_chat_model(temperature=0),
            schema=RepairProposal,
            prompt=prompt,
            method=settings.structured_output_method,
            strict=settings.structured_output_strict,
            max_retries=settings.structured_output_max_retries,
            raw_preview_chars=settings.structured_output_raw_preview_chars,
        )

        if invocation.value is not None:
            proposal = invocation.value
        else:
            proposal = _build_no_repair_proposal(
                error_type=error_type,
                summary=(
                    "模型在有限重试后仍未返回合法 RepairProposal，"
                    "已安全降级。"
                ),
                root_cause="结构化输出校验连续失败。",
            )

        trace_path = write_structured_output_trace(
            result=invocation,
            node_name="repair_planner",
            schema_name="RepairProposal",
            output_dir=settings.output_dir,
            fallback_used=invocation.value is None,
        )

    if not proposal.proposal_id:
        proposal = proposal.model_copy(
            update={"proposal_id": f"repair_{uuid4().hex[:12]}"}
        )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "repair_proposal.json"
    md_path = settings.output_dir / "repair_proposal.md"

    json_path.write_text(
        proposal.model_dump_json(indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        render_repair_proposal_md(proposal.model_dump()),
        encoding="utf-8",
    )

    output_files = [
        *state.get("output_files", []),
        str(json_path),
        str(md_path),
    ]
    if trace_path is not None:
        output_files.append(str(trace_path))

    return {
        "repair_proposal": proposal.model_dump(),
        "output_files": output_files,
    }
```

### 为什么 CUDA OOM 不进入 LLM retry

因为当前已经有足够明确的本地证据：

```text
error_type = cuda_oom
命令中存在 --batch-size 8
```

允许的最小有界变化是：

```text
--batch-size 8 -> 1
```

这种规则：

- 容易解释
- 容易测试
- 容易回滚
- 不需要模型补充
- 不会发生 schema 漂移

LLM 应该用在规则覆盖不了的复杂诊断上，而不是替代所有确定性逻辑。

---

## 十二、接入 method_extractor_node

修改 [app/nodes/method_extractor_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/method_extractor_node.py:1)。

这个节点的模型输出不是一份只给人看的摘要。它会继续成为：

```text
method_modules
    -> code_search_node
    -> mapping_node
    -> experiment_plan_node
```

因此不能继续直接假设：

```python
result["parsed"]
```

一定是合法的 `PaperSummary`。当前写法一旦 `parsed=None`，后面的
`summary.model_dump_json()` 就会直接报错。

先增加通用工具 import：

```python
from app.tools.structured_output_tools import (
    invoke_structured_with_retry,
    write_structured_output_trace,
)
```

然后增加一个保守 fallback：

```python
def _build_method_extraction_fallback() -> PaperSummary:
    """结构化提取失败时不编造论文方法，确保下游不会生成可执行命令。"""

    return PaperSummary(
        title=None,
        research_problem="unknown",
        core_idea="unknown",
        method_modules=[],
        datasets=[],
        metrics=[],
        experiment_settings=[],
        reproduction_risks=[
            "论文结构化提取失败，当前结果不能用于可靠复现。",
        ],
        unresolved_questions=[
            "模型为什么没有返回符合 PaperSummary 的结构？",
            "需要重新检查论文文本提取结果和 structured output provider。",
        ],
    )
```

这里故意把 `method_modules` 设为空列表。

不要在失败后让模型自由输出一段自然语言，再尝试从中猜方法模块。否则虽然 graph
表面上继续运行了，后续代码搜索和实验命令却可能建立在不可审计的数据上。

完整节点调用部分可以改成：

```python
def method_extractor_node(state: dict) -> dict:
    chunks = state.get("paper_text_chunks", [])
    if not chunks:
        return {"error": "paper_text_chunks is empty"}

    paper_text = _merge_chunks(chunks)
    prompt = PAPER_SUMMARY_PROMPT.format(paper_text=paper_text)

    invocation = invoke_structured_with_retry(
        llm=get_chat_model(temperature=0),
        schema=PaperSummary,
        prompt=prompt,
        method=settings.structured_output_method,
        strict=settings.structured_output_strict,
        max_retries=settings.structured_output_max_retries,
        raw_preview_chars=settings.structured_output_raw_preview_chars,
    )

    if invocation.value is not None:
        summary = invocation.value
    else:
        summary = _build_method_extraction_fallback()

    trace_path = write_structured_output_trace(
        result=invocation,
        node_name="method_extractor",
        schema_name="PaperSummary",
        output_dir=settings.output_dir,
        fallback_used=invocation.value is None,
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    paper_summary_path = settings.output_dir / "paper_summary.json"
    method_modules_path = settings.output_dir / "method_modules.json"

    paper_summary_path.write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    method_modules_path.write_text(
        json.dumps(
            [module.model_dump() for module in summary.method_modules],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "paper_summary": summary.model_dump(),
        "method_modules": [
            module.model_dump()
            for module in summary.method_modules
        ],
        "output_files": [
            *state.get("output_files", []),
            str(paper_summary_path),
            str(method_modules_path),
            str(trace_path),
        ],
    }
```

### 注意 PaperSummary 中的任意字典

当前 Schema 中有：

```python
experiment_settings: dict = Field(default_factory=dict)
```

任意 key 的 `dict` 在不同 strict JSON Schema provider 上兼容性并不完全一致。
有些实现要求每一层对象都声明：

```json
{"additionalProperties": false}
```

这会与“允许任意实验参数名”的字典语义冲突。

因此最小 provider probe 成功后，还必须真实运行一次 `PaperSummary` 节点。如果
artifact 显示 provider 拒绝 `experiment_settings` 的 schema，长期方案是把它改成
有界结构，例如：

```python
class ExperimentSetting(BaseModel):
    name: str
    value: str
    evidence: list[Evidence] = Field(default_factory=list)


class PaperSummary(BaseModel):
    # ...其他字段保持不变...
    experiment_settings: list[ExperimentSetting] = Field(default_factory=list)
```

同时更新 `PAPER_SUMMARY_PROMPT` 和依赖这个字段的测试。不要只针对
`method_extractor_node` 静默关闭 strict；如果必须临时使用
`function_calling + strict=false`，应该让 attempt artifact 明确记录这一配置。

---

## 十三、接入 mapping_node

修改 [app/nodes/mapping_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/mapping_node.py:1)。

`mapping_node` 和其他节点有一个关键区别：

```text
一个 method module 对应一次 LLM 调用
```

因此迁移时要同时解决两个问题：

- 某一个模块失败时，不能丢掉已经成功的其他模块。
- 每个模块必须使用不同的 trace 文件名，否则循环中的后一次调用会覆盖前一次。

先调整 import，并增加安全的文件名片段函数：

```python
import json
import re

from app.config import settings
from app.model import get_chat_model
from app.prompts.mapping_prompt import MAPPING_PROMPT
from app.schemas import ModuleMapping
from app.tools.structured_output_tools import (
    invoke_structured_with_retry,
    write_structured_output_trace,
)


def _trace_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "module")[:60]
```

中文模块名可能得到统一的 `module`，但前面还会加入循环序号，所以文件名仍然唯一。

再增加当前模块的局部 fallback：

```python
def _build_mapping_fallback(module_name: str) -> ModuleMapping:
    return ModuleMapping(
        module_name=module_name,
        candidates=[],
        unresolved_questions=[
            "该模块的结构化映射调用失败，未生成可信代码候选。",
        ],
    )
```

然后把节点主体改成：

```python
def mapping_node(state: dict) -> dict:
    modules = state.get("method_modules", [])
    search_results = state.get("code_search_results", {})
    if not modules or not search_results:
        return {
            "paper_code_mapping": [],
            "error": "mapping requires method_modules and code_search_results",
        }

    llm = get_chat_model(temperature=0)
    mappings: list[dict] = []
    trace_paths: list[str] = []

    for index, module in enumerate(modules):
        module_name = str(
            module.get("name") or f"unnamed_module_{index}"
        )
        search_result = search_results.get(module_name, {})
        prompt = MAPPING_PROMPT.format(
            module=json.dumps(module, ensure_ascii=False, indent=2),
            search_results=json.dumps(
                search_result.get("matches", []),
                ensure_ascii=False,
                indent=2,
            ),
            code_slices=json.dumps(
                search_result.get("code_slices", []),
                ensure_ascii=False,
                indent=2,
            ),
        )

        invocation = invoke_structured_with_retry(
            llm=llm,
            schema=ModuleMapping,
            prompt=prompt,
            method=settings.structured_output_method,
            strict=settings.structured_output_strict,
            max_retries=settings.structured_output_max_retries,
            raw_preview_chars=settings.structured_output_raw_preview_chars,
        )

        if invocation.value is not None:
            mapping = invocation.value

            # 模块名来自上游已验证输入，不允许模型改写路由键。
            if mapping.module_name != module_name:
                mapping = mapping.model_copy(
                    update={
                        "module_name": module_name,
                        "unresolved_questions": [
                            *mapping.unresolved_questions,
                            "模型返回的 module_name 与输入不一致，"
                            "已使用输入模块名覆盖。",
                        ],
                    }
                )
        else:
            mapping = _build_mapping_fallback(module_name)

        trace_path = write_structured_output_trace(
            result=invocation,
            node_name=(
                f"mapping_{index:02d}_{_trace_slug(module_name)}"
            ),
            schema_name="ModuleMapping",
            output_dir=settings.output_dir,
            fallback_used=invocation.value is None,
        )

        mappings.append(mapping.model_dump())
        trace_paths.append(str(trace_path))

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "paper_code_mapping.json"
    md_path = settings.output_dir / "paper_code_mapping.md"

    json_path.write_text(
        json.dumps(mappings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        _render_mapping_markdown(mappings),
        encoding="utf-8",
    )

    return {
        "paper_code_mapping": mappings,
        "output_files": [
            *state.get("output_files", []),
            str(json_path),
            str(md_path),
            *trace_paths,
        ],
    }
```

### 为什么按模块降级

假设论文有五个模块：

```text
P4D convolution       succeeded
positional encoding   succeeded
transformer encoder   validation_error x 3
classification head   succeeded
loss                   succeeded
```

合理结果应该保留四个成功映射，只把 transformer encoder 记录成：

```json
{
  "module_name": "transformer encoder",
  "candidates": [],
  "unresolved_questions": [
    "该模块的结构化映射调用失败，未生成可信代码候选。"
  ]
}
```

如果整个节点一起 fallback，不仅浪费成功调用，也无法从 artifact 判断究竟是哪一个
模块的 Schema 或 Prompt 最不稳定。

### strict 不等于文件路径真实

`ModuleMapping` 通过 strict 和 Pydantic 只能证明：

```text
file_path 是字符串
confidence 是合法枚举
evidence 是合法对象列表
```

它不能证明 `file_path` 真正在仓库中存在。后续还应该增加确定性语义校验：

- 路径必须是 repo-relative path。
- 解析后的路径不能逃出 `repo_path`。
- 候选路径最好来自 `matches` 或 `code_slices`。
- 模型声称的 symbol 应能在对应文件中再次搜索到。

这些检查属于 mapping 业务层，不应该放进通用 structured output 工具。

---

## 十四、接入 experiment_plan_node

修改 [app/nodes/experiment_plan_node.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/nodes/experiment_plan_node.py:1)。

这是三个节点中安全优先级最高的一个，因为它输出的：

```text
ExperimentPlan.run_commands
```

会继续经过命令选择、action builder、风险检查、审批和执行链。结构化调用失败时，
最安全的 fallback 不是猜一条命令，而是生成一份没有 `run_commands` 的计划。

先增加 import：

```python
from app.tools.structured_output_tools import (
    invoke_structured_with_retry,
    write_structured_output_trace,
)
```

再增加 fallback：

```python
def _build_plan_fallback(*, goal: str, reason: str) -> ExperimentPlan:
    return ExperimentPlan(
        goal=goal,
        environment_steps=[],
        data_steps=[],
        train_steps=[],
        eval_steps=[],
        run_commands=[],
        risks=[
            "实验计划缺少可信结构化结果，禁止进入自动执行。",
        ],
        unresolved_questions=[reason],
    )
```

完整节点主体可以改成：

```python
def experiment_plan_node(state: dict) -> dict:
    paper_summary = state.get("paper_summary")
    repo_map = state.get("repo_map")
    paper_code_mapping = state.get("paper_code_mapping")
    experiment_goal = (
        state.get("experiment_goal")
        or "复现论文 main result"
    )
    trace_path = None

    missing_inputs = [
        name
        for name, value in (
            ("paper_summary", paper_summary),
            ("repo_map", repo_map),
            ("paper_code_mapping", paper_code_mapping),
        )
        if not value
    ]

    if missing_inputs:
        # 输入不足时没有调用模型，因此也不生成 structured attempt trace。
        plan = _build_plan_fallback(
            goal=experiment_goal,
            reason=(
                "缺少实验规划输入：" + ", ".join(missing_inputs)
            ),
        )
    else:
        prompt = EXPERIMENT_PLAN_PROMPT.format(
            paper_summary=json.dumps(
                paper_summary,
                ensure_ascii=False,
                indent=2,
            ),
            repo_map=json.dumps(
                repo_map,
                ensure_ascii=False,
                indent=2,
            ),
            paper_code_mapping=json.dumps(
                paper_code_mapping,
                ensure_ascii=False,
                indent=2,
            ),
            experiment_goal=experiment_goal,
        )

        invocation = invoke_structured_with_retry(
            llm=get_chat_model(temperature=0),
            schema=ExperimentPlan,
            prompt=prompt,
            method=settings.structured_output_method,
            strict=settings.structured_output_strict,
            max_retries=settings.structured_output_max_retries,
            raw_preview_chars=settings.structured_output_raw_preview_chars,
        )

        if invocation.value is not None:
            plan = invocation.value

            # goal 来自用户输入，不允许模型悄悄改写任务目标。
            if plan.goal != experiment_goal:
                plan = plan.model_copy(
                    update={"goal": experiment_goal}
                )
        else:
            plan = _build_plan_fallback(
                goal=experiment_goal,
                reason=(
                    "模型在有限重试后仍未返回合法 ExperimentPlan。"
                ),
            )

        trace_path = write_structured_output_trace(
            result=invocation,
            node_name="experiment_plan",
            schema_name="ExperimentPlan",
            output_dir=settings.output_dir,
            fallback_used=invocation.value is None,
        )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = settings.output_dir / "experiment_plan.json"
    md_path = settings.output_dir / "experiment_plan.md"

    json_path.write_text(
        plan.model_dump_json(indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        _render_plan_markdown(plan),
        encoding="utf-8",
    )

    output_files = [
        *state.get("output_files", []),
        str(json_path),
        str(md_path),
    ]
    if trace_path is not None:
        output_files.append(str(trace_path))

    return {
        "experiment_plan": plan.model_dump(),
        "run_commands": [
            command.model_dump()
            for command in plan.run_commands
        ],
        "output_files": output_files,
    }
```

### 为什么缺输入时不调用 LLM

如果 `paper_code_mapping` 为空，模型没有论文方法到代码文件的关键证据。继续请求模型
生成命令只会提高“看起来完整”的概率，不会提高正确率。

因此这里区分两类 fallback：

```text
输入缺失
  -> 不调用 LLM
  -> 不生成 attempt trace
  -> 返回空 run_commands

模型已经调用但结构失败
  -> 有限重试
  -> 写 attempt trace
  -> 返回空 run_commands
```

下游 `command_selection_node` 收到空命令列表后不会请求人工选择，
`action_builder_node` 会把状态设为 `no_action`，因此不会形成待执行动作。

### strict 之后仍要保留命令安全链

即使 `ExperimentPlan` 完全通过 JSON Schema，也只说明它满足接口协议。它不能证明：

- 命令来自真实 README 或脚本。
- `cwd` 在允许的 workspace 内。
- 参数不会覆盖数据或 checkpoint。
- 当前 execution profile 中存在对应依赖。
- 命令适合直接执行而不是只适合人工参考。

所以后续的 command selection、action hash、risk check、human review、preflight 和
smoke test 都不能因为 strict 成功而省略。

---

## 十五、增加 provider capability probe

客户端支持 strict，不代表服务端支持。

建议在 [app/schemas.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/schemas.py:1) 增加一个极小 schema：

```python
class StructuredOutputProbe(BaseModel):
    status: Literal["ok"]
    value: int
```

然后在 [app/main.py](/data/tianshaoqi24/agent/paper_reproduction_copilot/app/main.py:1) 增加 import：

```python
from app.model import get_chat_model
from app.schemas import StructuredOutputProbe
from app.tools.structured_output_tools import (
    invoke_structured_with_retry,
    write_structured_output_trace,
)
```

新增 CLI：

```python
@app.command()
def probe_structured_output():
    """
    用最小请求验证当前 model/provider 是否支持项目配置的结构化模式。

    该命令会真实调用一次模型 API，但不会运行论文代码或修改仓库。
    """
    result = invoke_structured_with_retry(
        llm=get_chat_model(temperature=0),
        schema=StructuredOutputProbe,
        prompt=(
            "Return a JSON object with status='ok' and value=1. "
            "Do not return any other fields."
        ),
        method=settings.structured_output_method,
        strict=settings.structured_output_strict,
        max_retries=0,
        raw_preview_chars=settings.structured_output_raw_preview_chars,
    )

    trace_path = write_structured_output_trace(
        result=result,
        node_name="structured_output_probe",
        schema_name="StructuredOutputProbe",
        output_dir=settings.output_dir,
        fallback_used=False,
    )

    print(
        {
            "succeeded": result.succeeded,
            "method": result.method,
            "strict": result.strict,
            "attempt_count": len(result.attempts),
            "value": result.value.model_dump() if result.value else None,
            "trace_path": str(trace_path),
        }
    )

    if not result.succeeded:
        raise typer.Exit(code=1)
```

执行：

```bash
python -m app.main probe-structured-output
```

成功时应看到：

```text
succeeded: true
method: json_schema
strict: true
value: {status: ok, value: 1}
```

失败时先查看：

```text
outputs/structured_output_probe_structured_attempts.json
```

### 如果服务端不支持 json_schema strict

你有两个选择。

选择 A：更换为支持原生 Structured Output 的 provider/model。

这是更推荐的长期方案。

选择 B：暂时使用：

```dotenv
STRUCTURED_OUTPUT_METHOD=function_calling
STRUCTURED_OUTPUT_STRICT=false
```

然后依赖：

```text
Pydantic + retry + fallback
```

需要在报告中明确记录：

```text
当前不是 provider 原生 strict 模式
```

不要静默降级，否则你以后无法解释为什么某次结构化成功率突然下降。

---

## 十六、单元测试：通用 retry 工具

新建：

```text
tests/test_structured_output_tools.py
```

参考实现：

```python
from types import SimpleNamespace

from pydantic import BaseModel

from app.tools.structured_output_tools import invoke_structured_with_retry


class DemoOutput(BaseModel):
    answer: str
    count: int


class FakeStructuredRunnable:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeLLM:
    def __init__(self, runnable):
        self.runnable = runnable
        self.structured_kwargs = None

    def with_structured_output(self, schema, **kwargs):
        self.structured_kwargs = {
            "schema": schema,
            **kwargs,
        }
        return self.runnable


class FailingSetupLLM:
    def with_structured_output(self, schema, **kwargs):
        raise RuntimeError("structured output setup failed")


def test_structured_output_succeeds_on_first_attempt():
    runnable = FakeStructuredRunnable(
        [
            {
                "raw": SimpleNamespace(
                    content='{"answer":"ok","count":1}'
                ),
                "parsed": DemoOutput(answer="ok", count=1),
                "parsing_error": None,
            }
        ]
    )
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        method="json_schema",
        strict=True,
        max_retries=2,
    )

    assert result.succeeded is True
    assert result.value == DemoOutput(answer="ok", count=1)
    assert len(result.attempts) == 1
    assert result.attempts[0].status == "succeeded"
    assert llm.structured_kwargs["method"] == "json_schema"
    assert llm.structured_kwargs["strict"] is True
    assert llm.structured_kwargs["include_raw"] is True


def test_structured_output_retries_with_validation_error():
    runnable = FakeStructuredRunnable(
        [
            {
                "raw": SimpleNamespace(content='{"answer":"missing count"}'),
                "parsed": None,
                "parsing_error": ValueError("count field required"),
            },
            {
                "raw": SimpleNamespace(
                    content='{"answer":"fixed","count":2}'
                ),
                "parsed": DemoOutput(answer="fixed", count=2),
                "parsing_error": None,
            },
        ]
    )
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=2,
    )

    assert result.succeeded is True
    assert result.value == DemoOutput(answer="fixed", count=2)
    assert [item.status for item in result.attempts] == [
        "validation_error",
        "succeeded",
    ]
    assert "count field required" in runnable.prompts[1]
    assert "Required JSON Schema" in runnable.prompts[1]


def test_structured_output_exhausts_retries():
    invalid = {
        "raw": SimpleNamespace(content='{"wrong":true}'),
        "parsed": None,
        "parsing_error": ValueError("invalid schema"),
    }
    runnable = FakeStructuredRunnable([invalid, invalid, invalid])
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=2,
    )

    assert result.succeeded is False
    assert result.value is None
    assert len(result.attempts) == 3
    assert all(
        item.status == "validation_error"
        for item in result.attempts
    )


def test_structured_output_does_not_format_retry_invoke_error():
    runnable = FakeStructuredRunnable(
        [RuntimeError("provider does not support json_schema")]
    )
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=2,
    )

    assert result.succeeded is False
    assert len(result.attempts) == 1
    assert result.attempts[0].status == "invoke_error"


def test_structured_output_returns_configuration_error_when_setup_fails():
    result = invoke_structured_with_retry(
        llm=FailingSetupLLM(),
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=2,
    )

    assert result.succeeded is False
    assert result.value is None
    assert len(result.attempts) == 1
    assert result.attempts[0].attempt_number == 0
    assert result.attempts[0].status == "configuration_error"
    assert result.attempts[0].prompt_kind == "configuration"
```

运行：

```bash
python -m pytest tests/test_structured_output_tools.py -q
```

---

## 十七、单元测试：RepairProposal 语义

新建：

```text
tests/test_repair_proposal_semantics.py
```

参考实现：

```python
import pytest
from pydantic import ValidationError

from app.schemas import RepairProposal


def _base_payload() -> dict:
    return {
        "proposal_id": "repair_demo",
        "source_error_type": "runtime_error",
        "kind": "no_repair",
        "summary": "demo",
        "root_cause": "unknown",
        "repaired_command": None,
        "changed_arguments": [],
        "steps": [],
        "verification_steps": [],
        "rollback_steps": [],
        "risks": [],
        "bounded": True,
    }


def test_edit_command_requires_repaired_command():
    payload = _base_payload()
    payload["kind"] = "edit_command"

    with pytest.raises(ValidationError, match="requires repaired_command"):
        RepairProposal.model_validate(payload)


def test_no_repair_must_not_contain_command():
    payload = _base_payload()
    payload["repaired_command"] = "python train.py"

    with pytest.raises(ValidationError, match="must not contain"):
        RepairProposal.model_validate(payload)


def test_edit_command_accepts_complete_bounded_proposal():
    payload = _base_payload()
    payload.update(
        {
            "kind": "edit_command",
            "repaired_command": "python train.py --batch-size 1",
            "changed_arguments": ["--batch-size 8 -> 1"],
            "verification_steps": ["rerun smoke test"],
            "rollback_steps": ["restore batch size 8"],
        }
    )

    proposal = RepairProposal.model_validate(payload)

    assert proposal.kind == "edit_command"
```

运行：

```bash
python -m pytest tests/test_repair_proposal_semantics.py -q
```

---

## 十八、节点级测试

除了通用工具，还需要验证节点是否正确选择：

```text
deterministic
LLM success
LLM retry success
fallback
```

建议在现有 smoke/repair 测试中至少补下面几类。

### 1. CUDA OOM 不调用 LLM

你当前已经有类似测试：

```python
def test_cuda_oom_builds_bounded_batch_size_repair_without_llm(...):
    ...
```

保留它。

### 2. 非确定性错误调用通用工具

```python
from app.schemas import RepairProposal
import app.nodes.experiment_plan_node as experiment_plan_module
import app.nodes.mapping_node as mapping_module
import app.nodes.method_extractor_node as method_extractor_module
from app.config import settings
from app.schemas import ModuleMapping
from app.tools.structured_output_tools import StructuredInvocationResult


def test_repair_planner_uses_structured_invocation(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")

    proposal = RepairProposal(
        proposal_id="repair_demo",
        source_error_type="shape_mismatch",
        kind="manual_only",
        summary="shape mismatch needs code inspection",
        root_cause="tensor dimensions differ",
        repaired_command=None,
        changed_arguments=[],
        steps=[],
        verification_steps=[],
        rollback_steps=[],
        risks=["source change requires human review"],
        bounded=True,
    )
    fake_invocation = StructuredInvocationResult(
        value=proposal,
        attempts=[],
        method="json_schema",
        strict=True,
        max_retries=2,
    )

    with patch(
        "app.nodes.repair_planner_node.invoke_structured_with_retry",
        return_value=fake_invocation,
    ):
        result = repair_planner_node(
            {
                "debug_report": {"error_type": "shape_mismatch"},
                "pending_action": {"program": "python", "args": ["train.py"]},
                "output_files": [],
            }
        )

    assert result["repair_proposal"]["kind"] == "manual_only"
```

### 3. 重试耗尽后 no_repair

构造：

```python
StructuredInvocationResult(
    value=None,
    attempts=[...],
    method="json_schema",
    strict=True,
    max_retries=2,
)
```

然后断言：

```python
assert result["repair_proposal"]["kind"] == "no_repair"
assert any(
    path.endswith("repair_planner_structured_attempts.json")
    for path in result["output_files"]
)
```

### 4. method_extractor 重试耗尽后使用空模块 fallback

建议新建：

```text
tests/test_analysis_planning_structured_nodes.py
```

核心测试结构如下：

```python
from app.tools.structured_output_tools import StructuredInvocationResult


def _failed_invocation() -> StructuredInvocationResult:
    return StructuredInvocationResult(
        value=None,
        attempts=[],
        method="json_schema",
        strict=True,
        max_retries=2,
    )


def test_method_extractor_falls_back_without_inventing_modules(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")
    monkeypatch.setattr(
        method_extractor_module,
        "get_chat_model",
        lambda temperature=0: object(),
    )
    monkeypatch.setattr(
        method_extractor_module,
        "invoke_structured_with_retry",
        lambda **kwargs: _failed_invocation(),
    )

    result = method_extractor_module.method_extractor_node(
        {
            "paper_text_chunks": [{"text": "paper content"}],
            "output_files": [],
        }
    )

    assert result["method_modules"] == []
    assert result["paper_summary"]["research_problem"] == "unknown"
    assert any(
        path.endswith("method_extractor_structured_attempts.json")
        for path in result["output_files"]
    )
```

这个测试的重点不是 fallback 文案，而是确保失败后没有虚构方法模块。

### 5. mapping 对单个模块局部降级且 trace 不覆盖

构造两个模块，让第一个调用成功、第二个调用失败：

```python
def test_mapping_keeps_successful_modules_and_uses_unique_traces(
    tmp_path,
    monkeypatch,
):
    success_mapping = ModuleMapping(
        module_name="P4D convolution",
        candidates=[],
        unresolved_questions=[],
    )
    invocations = iter(
        [
            StructuredInvocationResult(
                value=success_mapping,
                attempts=[],
                method="json_schema",
                strict=True,
                max_retries=2,
            ),
            _failed_invocation(),
        ]
    )

    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")
    monkeypatch.setattr(
        mapping_module,
        "get_chat_model",
        lambda temperature=0: object(),
    )
    monkeypatch.setattr(
        mapping_module,
        "invoke_structured_with_retry",
        lambda **kwargs: next(invocations),
    )

    result = mapping_module.mapping_node(
        {
            "method_modules": [
                {"name": "P4D convolution"},
                {"name": "Transformer encoder"},
            ],
            "code_search_results": {
                "P4D convolution": {"matches": [], "code_slices": []},
                "Transformer encoder": {"matches": [], "code_slices": []},
            },
            "output_files": [],
        }
    )

    assert len(result["paper_code_mapping"]) == 2
    assert result["paper_code_mapping"][0]["module_name"] == "P4D convolution"
    assert result["paper_code_mapping"][1]["candidates"] == []

    traces = [
        path
        for path in result["output_files"]
        if path.endswith("_structured_attempts.json")
    ]
    assert len(traces) == 2
    assert len(set(traces)) == 2
```

### 6. experiment_plan 失败后不能留下运行命令

```python
def test_experiment_plan_failure_returns_no_commands(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "output_dir", tmp_path / "outputs")
    monkeypatch.setattr(
        experiment_plan_module,
        "get_chat_model",
        lambda temperature=0: object(),
    )
    monkeypatch.setattr(
        experiment_plan_module,
        "invoke_structured_with_retry",
        lambda **kwargs: _failed_invocation(),
    )

    result = experiment_plan_module.experiment_plan_node(
        {
            "paper_summary": {"title": "demo"},
            "repo_map": {"repo_path": "/repo"},
            "paper_code_mapping": [
                {"module_name": "encoder", "candidates": []}
            ],
            "experiment_goal": "复现 main result",
            "output_files": [],
        }
    )

    assert result["run_commands"] == []
    assert result["experiment_plan"]["goal"] == "复现 main result"
    assert any(
        path.endswith("experiment_plan_structured_attempts.json")
        for path in result["output_files"]
    )
```

还应该增加一个“缺少输入时完全不调用 LLM”的测试，用 mock 断言：

```python
invoke_mock.assert_not_called()
```

---

## 十九、手工测试顺序

### 第 1 步：先跑纯单元测试

```bash
python -m pytest \
  tests/test_structured_output_tools.py \
  tests/test_repair_proposal_semantics.py \
  tests/test_analysis_planning_structured_nodes.py \
  tests/test_smoke_repair_flow.py
```

这一步不应访问真实模型 API。

### 第 2 步：运行 provider probe

```bash
python -m app.main probe-structured-output
```

检查：

```text
outputs/structured_output_probe_structured_attempts.json
```

### 第 3 步：测试确定性 CUDA OOM

使用已有合成日志：

```bash
python -m app.main plan-repair \
  /data/tianshaoqi24/P4Transformer/ \
  outputs/execution_failure_demo.log \
  "python train-msr-small.py --data-path /data/tianshaoqi24/datasets/MSRAction3D/npz --batch-size 8 --epochs 100 --workers 8" \
  --execution-profile p4transformer-conda
```

这一条应该：

- 不调用 LLM
- 输出 `source_error_type=cuda_oom`
- 输出 `kind=edit_command`
- 把 `--batch-size 8` 改成 `--batch-size 1`
- 不生成 structured attempts 文件，因为没有发生模型调用

### 第 4 步：测试真实 LLM structured output

准备一份不是 CUDA OOM、但能被启发式分类的失败日志，例如：

```text
ModuleNotFoundError: No module named 'pointnet2_ops'
```

然后执行：

```bash
python -m app.main plan-repair \
  /data/tianshaoqi24/P4Transformer/ \
  outputs/dependency_failure_demo.log \
  "python train-msr-small.py --help" \
  --execution-profile p4transformer-conda
```

由于依赖安装不允许自动执行，合理 proposal 应该是：

```text
kind = manual_only
```

并生成：

```text
outputs/log_debug_structured_attempts.json
outputs/repair_planner_structured_attempts.json
```

### 第 5 步：运行完整论文复现 graph

在三个前置分析节点完成迁移后，再运行真实命令：

```bash
python -m app.main run-graph \
  "pdf/Point 4D Transformer Networks for Spatio-Temporal Modeling.pdf" \
  /data/tianshaoqi24/P4Transformer \
  /tmp/test_oom.log \
  --thread-id debug-001 \
  --goal "复现论文 main result"
```

在进入命令选择中断点之前，至少应该看到：

```text
outputs/method_extractor_structured_attempts.json
outputs/mapping_00_*_structured_attempts.json
outputs/mapping_01_*_structured_attempts.json
outputs/experiment_plan_structured_attempts.json
```

映射 trace 的数量应该等于实际进入 `mapping_node` 的方法模块数量。逐个检查：

- `method` 是否为 `json_schema`。
- `strict` 是否为 `true`。
- `succeeded` 和 `fallback_used` 是否符合最终节点输出。
- 同一个模块是否发生多次 validation retry。
- fallback 后是否仍然产生了候选命令。

最后一项必须满足：

```text
experiment_plan fallback_used = true
    -> run_commands = []
    -> pending_action = None
```

---

## 二十、如何阅读 attempt artifact

成功示例：

```json
{
  "node_name": "repair_planner",
  "schema_name": "RepairProposal",
  "method": "json_schema",
  "strict": true,
  "max_retries": 2,
  "succeeded": true,
  "fallback_used": false,
  "attempt_count": 2,
  "attempts": [
    {
      "attempt_number": 1,
      "status": "validation_error",
      "prompt_kind": "original",
      "error_type": "ValidationError",
      "error_message": "source_error_type Field required",
      "raw_preview": "{...}"
    },
    {
      "attempt_number": 2,
      "status": "succeeded",
      "prompt_kind": "validation_retry",
      "error_type": null,
      "error_message": null,
      "raw_preview": "{...}"
    }
  ]
}
```

这个结果说明：

```text
第一次模型格式错误
第二次根据 Pydantic 错误修正成功
没有触发 fallback
```

provider 能力错误示例：

```json
{
  "attempt_number": 1,
  "status": "invoke_error",
  "error_type": "BadRequestError",
  "error_message": "response_format json_schema is not supported"
}
```

这时不要继续改 Prompt。

应该处理的是：

```text
provider/model 能力或配置
```

如果 `with_structured_output()` 在请求发出前就拒绝当前 schema 或参数，
trace 会记录：

```json
{
  "attempt_number": 0,
  "status": "configuration_error",
  "prompt_kind": "configuration",
  "error_type": "ValueError",
  "error_message": "unsupported structured output configuration"
}
```

这表示模型调用次数是 0。应检查客户端版本、schema、`method` 和 `strict`
配置，而不是增加重试次数。

---

## 二十一、不要犯的几个错误

### 错误 1：无限重试

不要：

```python
while parsed is None:
    invoke_again()
```

这会导致：

- 成本失控
- 延迟失控
- 同一错误反复出现
- graph 长时间不结束

最多额外重试两次。

### 错误 2：重试时把错误信息当成可信业务证据

ValidationError 只能告诉模型：

```text
格式哪里错了
```

不能把它变成新的错误诊断证据。

所以 Retry Prompt 必须写：

```text
只修复结构，不增加新事实
```

### 错误 3：模型格式正确就直接执行

即使 Pydantic 成功，也还必须经过：

```text
validate_bounded_repair_command
action hash
risk_check
human review
preflight
smoke test
```

结构化成功只代表：

```text
数据接口合法
```

不代表：

```text
动作已经安全
```

### 错误 4：静默从 strict 降级到自由文本

如果 provider 不支持 strict，应明确记录：

```text
method=function_calling
strict=false
```

不要在代码里静默切换后还把结果标记成 strict success。

### 错误 5：把完整 prompt 和论文正文写入 attempt artifact

attempt artifact 只保存：

- 方法
- 状态
- validation error
- 截断后的 raw output preview

不要重复保存完整论文文本或 API 凭据。

---

## 二十二、建议增加的评测指标

这一阶段完成后，可以把下面指标加入 evaluation：

```text
structured_output_total
structured_output_first_pass_success
structured_output_retry_success
structured_output_fallback_count
structured_output_configuration_error_count
structured_output_invoke_error_count
average_structured_attempt_count
```

例如：

```json
{
  "structured_output_total": 20,
  "first_pass_success_rate": 0.75,
  "retry_recovery_rate": 0.6,
  "fallback_rate": 0.1,
  "configuration_error_count": 0,
  "average_attempt_count": 1.35
}
```

这些指标可以回答：

- strict 是否真的提升成功率
- 哪个节点最容易格式漂移
- retry 是否有效
- schema 或客户端配置是否在调用前失败
- provider 是否稳定
- Prompt 修改后成功率是否变好

第一版不必马上实现汇总器，只要 attempt artifact 格式稳定，就已经为后续评测打好了基础。

---

## 二十三、完整回归测试

完成所有修改后，先运行：

```bash
python -m pytest \
  tests/test_structured_output_tools.py \
  tests/test_repair_proposal_semantics.py \
  tests/test_analysis_planning_structured_nodes.py \
  tests/test_smoke_repair_flow.py \
  tests/test_repair_action_builder_node.py \
  tests/test_manual_cli_execution_profiles.py
```

然后运行完整测试：

```bash
python -m pytest -q
```

最后检查 CLI：

```bash
python -m app.main probe-structured-output --help
python -m app.main plan-repair --help
```

---

## 二十四、验收标准

### Provider 验收

- 能明确知道当前 provider 是否支持 `json_schema + strict=True`
- 不支持时能够从 artifact 看见明确错误
- 不发生静默降级

### 结构化调用验收

- 第一次合法时直接成功
- 第一次格式错误、第二次正确时能够恢复
- 连续失败时最多调用三次
- invoke error 不做无意义的格式重试
- raw preview 被限制长度

### Schema 验收

- `PaperSummary`、`ModuleMapping` 和 `ExperimentPlan` 能被当前 provider 接受
- `PaperSummary.experiment_settings` 不会导致 strict schema capability error
- `ModuleMapping.module_name` 最终与输入模块名一致
- `ExperimentPlan.goal` 最终与用户目标一致
- `edit_command` 没有命令时被拒绝
- `no_repair` 携带命令时被拒绝
- `bounded=false` 被拒绝
- 可执行 proposal 必须有验证和回滚步骤

### 节点验收

- 方法提取失败时不生成虚构的 `method_modules`
- 一个 mapping 失败不会丢弃其他成功 mapping
- experiment plan 失败或缺输入时 `run_commands=[]`
- CUDA OOM 继续走确定性规则
- 无错误证据继续返回 `unknown/no_repair`
- 复杂错误才调用 LLM
- LLM 连续失败不会让 graph 崩溃
- fallback 结果仍符合 Pydantic schema

### Artifact 验收

- LLM 调用生成 `*_structured_attempts.json`
- 每个 mapping module 有独立且不会互相覆盖的 attempt artifact
- run manifest 能归档 attempt artifact
- artifact 能看出 attempt 数量、错误和 fallback 状态

---

## 二十五、本阶段涉及的 Agent 知识点

### 1. Model output is untrusted input

模型输出和用户输入、仓库 README 一样，都不能直接信任。

必须经过：

```text
协议约束
结构校验
语义校验
安全策略
```

### 2. Constrained generation

`json_schema + strict` 属于生成阶段约束。

它比只在 Prompt 里说“请输出 JSON”更可靠，但仍然受 provider 能力影响。

### 3. Validation-driven retry

重试不是简单重复相同请求。

更有效的是：

```text
把具体 ValidationError 反馈给模型
让模型只修复接口问题
```

### 4. Bounded retry

Agent 不能为了得到合法输出无限消耗预算。

有限重试是：

```text
可靠性
成本
延迟
可预测性
```

之间的平衡。

### 5. Hybrid agent

论文文本、代码搜索结果和复杂错误交给 LLM 做有界归纳；输入完整性、模块名、用户
目标、CUDA OOM 和执行安全仍由确定性逻辑控制。

这比“所有事情都问模型”更稳定，也更容易评测。

### 6. Graceful degradation

模型失败后不是整个 graph 崩溃，而是返回：

```text
不含 method_modules 的保守 PaperSummary
当前模块 candidates=[] 的 ModuleMapping
run_commands=[] 的 ExperimentPlan
保守 DebugReport
no_repair
明确 artifact
```

这就是 graceful degradation。

### 7. Observability as a control surface

attempt artifact 不只是日志。

它还是后续优化 Prompt、模型选择和评测体系的控制面。

---

## 二十六、完成后下一步

完成本阶段后，再进入：

```text
Phase 13：Manual File Repair Review 与 Patch-Level Verification
```

下一阶段建议继续保持分层：

```text
Patch Proposal
    ↓
路径与修改规模策略检查
    ↓
原文件 SHA-256 绑定
    ↓
人工审批 patch hash
    ↓
临时 worktree / 副本应用
    ↓
语法检查 + 单测 + smoke
    ↓
成功后保留，失败后回滚
```

不要一开始就允许 Agent：

```text
直接修改任意文件
直接在主仓库应用 patch
修改依赖环境
验证失败后继续保留修改
```

本阶段稳定后，你就拥有了进入 patch repair 所需要的可靠控制面。

---

## 最后总结

这一阶段最重要的变化不是多调用两次模型，而是把结构化输出从：

```text
模型最好按格式返回
```

升级成：

```text
provider 尽量约束
程序必须验证
失败有限重试
过程完整留痕
最终安全降级
```

它是 command-level repair 走向 file-level repair 之前必须补齐的可靠性基础。
