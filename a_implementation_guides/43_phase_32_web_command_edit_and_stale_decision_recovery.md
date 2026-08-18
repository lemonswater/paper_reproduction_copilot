# 43. Phase 32：Web Command Edit 与 Stale Decision Recovery

Phase 31 已经让用户可以在 Web Console 中围绕当前 Job 继续提问，但真正推进论文复现任务时仍有一个
明显断点：`command_selection` 卡片只能选择命令，不能修改命令。

当前模型生成的候选命令经常包含需要人工确认的部分：

```text
python train.py --dataset_path <path_to_dataset>
conda activate p4transformer
python test.py --checkpoint /path/to/checkpoint
python train.py --batch_size 32 --epochs 100
```

用户可能需要把数据集路径、环境名、checkpoint 路径或显存相关参数改成当前机器上的真实值。后端和
Graph 已经支持 `CommandEdit`，但 Phase 30 的前端始终提交 `edits: []`，因此用户还要退出页面改 JSON
并使用 CLI 恢复任务。

本阶段补齐这条链路，但重点不是做一个复杂编辑器，而是把**人工编辑作为不可信 Agent 输入**完整收口：

```text
浏览器只收集差异
  -> Interaction API 校验当前 Job/interrupt/hash
  -> durable resume 只入队一次
  -> Graph 节点恢复后再次校验
  -> 重新生成 Action 和 Action Hash
  -> 继续经过 Risk Check / Human Review
```

> **本教程中的源码均为待实现代码。**
>
> 本阶段继续保持单机、单用户。前端只实现多命令文本编辑、选择、恢复原值和错误提示，不引入富文本
> 编辑器、终端模拟器或 Chat 自动改命令。

---

## 一、本阶段解决什么问题

> **本节类型：问题分析，不修改项目代码。**

### 1.1 前端能力缺口

当前 `web/src/components/DecisionCard.tsx` 在命令选择分支中固定发送：

```typescript
const decision = {
  kind: "command_selection",
  selected_index: index,
  edits: [],
  run_commands_hash: commandsHash,
};
```

后端 `CommandSelectionDecision` 已经允许：

```json
{
  "kind": "command_selection",
  "selected_index": 1,
  "edits": [
    {
      "index": 0,
      "command": "python train.py --dataset_path /data/ntu60"
    },
    {
      "index": 1,
      "command": "python test.py --checkpoint /data/checkpoints/best.pth"
    }
  ],
  "run_commands_hash": "<64-hex>"
}
```

也就是说，Graph 能力已经存在，Web 只是没有把它完整暴露出来。

### 1.2 校验时机过晚

目前 `run_commands_hash`、索引范围和空命令主要在 `command_selection_node` 从 checkpoint 恢复后校验。
如果 HTTP 输入非法，系统可能先把 resume 持久化并把 Job 改成 `queued`，随后 Worker 才发现错误。

更合理的边界是：

```text
HTTP request
  -> schema syntax validation
  -> current interrupt semantic validation
  -> queue resume
  -> graph defensive validation
```

只有通过前两层的输入才能进入 durable queue。

### 1.3 Mutation route 不能调用两次

当前决策路由使用下面的容错模式：

```python
try:
    with telemetry.span(...):
        return service.submit_decision(...)
except Exception:
    return service.submit_decision(...)
```

这里的 `except Exception` 无法区分 telemetry 失败和业务失败。`submit_decision()` 抛出 stale conflict 时，
路由会再次调用同一个 mutation。Store 的幂等和 CAS 能降低损害，但 API 层仍不应该依赖下游来修复一次
请求触发两次业务调用的问题。

---

## 二、完成定义

> **本节类型：目标说明，不修改项目代码。**

完成后必须满足：

1. Web 可以编辑一条或多条候选命令；
2. Web 可以独立选择首先执行的命令；
3. 前端只提交真正变化的 `{index, command}`；
4. `CommandEdit` 拒绝负索引、空命令、超长命令、控制字符和未知字段；
5. 同一个 decision 中不允许重复编辑同一索引；
6. Interaction Service 在 queue resume 前校验命令列表和 hash；
7. `selected_index` 和每个 edit index 都必须落在当前候选列表内；
8. server preview hash 必须和 preview 中的 `run_commands` 一致；
9. 浏览器提交的 hash 必须和当前 preview hash 一致；
10. Job version 或 wait generation 变化时继续返回 409；
11. stale command hash 返回 409，Job 保持 `waiting_for_input`；
12. 非法索引、空命令等用户输入返回 422，不进入 resume queue；
13. 决策 mutation route 每个 HTTP 请求只调用一次业务方法；
14. Graph 恢复后继续执行相同的领域校验，不能只相信 API；
15. 编辑命令后旧 Action、审批、Preflight 和执行结果继续失效；
16. 仍然经过原有 Risk Check 和 Human Review；
17. 后端、Graph、API 和最小前端测试全部通过。

---

## 三、本阶段明确不做

> **本节类型：范围说明，不修改项目代码。**

```text
不让 Chat Agent 自动修改命令
不让 LLM 决定用户最终提交的编辑
不在浏览器执行 shell 或命令探测
不修改 cwd、source、risk_level 和 reason
不新增任意环境变量编辑器
不增加 terminal emulator
不增加 Bash 语法高亮或自动补全
不因为命令可编辑就绕过 Risk Check
不自动重放 stale decision
不把完整 command 放入低基数 metric label
不引入多用户锁、Redis 或消息队列
```

Command Selection 的职责只是确定“用户希望尝试什么”。命令是否可执行、是否允许使用当前 profile、
是否需要审批，仍由后续确定性策略决定。

---

## 四、三重身份与双重校验

> **本节类型：Agent 协议说明，不修改项目代码。**

一次有效命令编辑同时绑定三种身份：

```text
expected_job_version
    防止旧 Job 页面修改已经变化的 Job。

expected_wait_generation
    防止第 N 次 interrupt 的决定被应用到第 N+1 次 interrupt。

run_commands_hash
    防止对候选命令列表 A 的编辑被应用到候选列表 B。
```

请求链路：

```text
DecisionCard
  |
  | DecisionEnvelope
  v
InteractionService.submit_decision
  |- validate_decision
  |    |- status == waiting_for_input
  |    |- job_version 一致
  |    |- wait_generation 一致
  |    `- decision kind 与 node 一致
  |
  |- normalize_decision_against_record
  |    |- preview 完整
  |    |- preview hash 自洽
  |    |- request hash 当前
  |    |- selected_index 有效
  |    `- edits 规范且索引唯一
  |
  `- JobService.resume
       `- Store CAS + idempotency

Worker 恢复 Graph
  `- command_selection_node 再执行同一份领域校验
```

API 前置校验改善用户体验和 durable state 正确性；Graph 后置校验负责防御 CLI、旧 checkpoint、数据库
导入和未来其他调用入口。两层不能互相替代。

---

## 五、文件清单

> **本节类型：实施清单。**

新增后端领域文件：

```text
app/command_selection.py
```

修改后端文件：

```text
app/schemas.py
app/nodes/command_selection_node.py
app/interaction/schemas.py
app/interaction/policy.py
app/interaction/service.py
app/api/routes.py
```

新增或修改后端测试：

```text
tests/test_command_selection_contract.py
tests/test_interaction_policy.py
tests/test_interaction_api.py
tests/test_decision_route_exactly_once.py
```

修改前端文件：

```text
web/src/api/types.ts
web/src/api/client.ts
web/src/components/DecisionCard.tsx
web/src/styles/app.css
```

新增前端测试：

```text
web/tests/command-selection.test.tsx
```

本阶段不修改 Graph 拓扑，也不增加新的 LangGraph node。

---

## 六、收紧 CommandEdit Schema

> **本节类型：需要修改项目代码。**
>
> 修改：`app/schemas.py`。

先在 Pydantic import 中加入 `ConfigDict`：

```diff
 from pydantic import (
     AliasChoices,
     BaseModel,
+    ConfigDict,
     Field,
     model_validator,
 )
```

找到现有 `CommandEdit`、`CommandSelectionResponse` 和 `CommandSelectionRecord`，用下面代码整体替换：

```python
# HTTP、CLI 和 Graph 共用的硬上限。它限制单条人工编辑的内存、日志和
# checkpoint 体积，不表示命令达到该长度就一定能通过后续 Risk Check。
MAX_COMMAND_EDIT_CHARS = 8192
MAX_COMMAND_SELECTION_EDITS = 128


class CommandEdit(BaseModel):
    """用户对候选命令的索引化替换；不允许静默忽略未知字段。"""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    command: str = Field(
        min_length=1,
        max_length=MAX_COMMAND_EDIT_CHARS,
    )


class CommandSelectionResponse(BaseModel):
    """Graph interrupt 和 CLI 共同接受的命令选择响应。"""

    model_config = ConfigDict(extra="forbid")

    selected_index: int = Field(ge=0)
    edits: list[CommandEdit] = Field(
        default_factory=list,
        max_length=MAX_COMMAND_SELECTION_EDITS,
    )
    # CLI 兼容层先保留 min_length；API schema 会进一步要求 64 hex。
    run_commands_hash: str = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_edit_indexes(
        self,
    ) -> "CommandSelectionResponse":
        indexes = [item.index for item in self.edits]
        if len(indexes) != len(set(indexes)):
            raise ValueError(
                "同一命令索引不能在一次 decision 中重复编辑"
            )
        return self


class CommandSelectionRecord(BaseModel):
    selected_index: int = Field(ge=0)
    edits: list[CommandEdit] = Field(default_factory=list)
    original_count: int = Field(ge=1)
    run_commands_hash: str = Field(min_length=1)
    reviewed_at: str
```

这里故意不在 Pydantic validator 中自动执行 `.strip()`。Schema 层负责形状和大小，领域层负责明确地
规范化命令并返回一个新的模型，避免字段在反序列化时被不透明地修改。

---

## 七、实现命令选择领域模块

> **本节类型：需要新增项目代码。**
>
> 新增：`app/command_selection.py`。

这个模块不访问数据库、不读取 checkpoint、不调用 LLM，也不执行命令。它只负责稳定 hash、编辑规范化、
索引校验和纯内存应用，因此可以同时被 Interaction 层和 Graph 节点复用。

```python
from __future__ import annotations

import hashlib
import hmac
import json
import re
from copy import deepcopy
from typing import Any

from app.schemas import (
    MAX_COMMAND_EDIT_CHARS,
    MAX_COMMAND_SELECTION_EDITS,
    CommandEdit,
    CommandSelectionResponse,
)


class CommandSelectionValidationError(ValueError):
    """用户提交的选择或编辑不满足命令选择领域约束。"""


class StaleCommandSelectionError(
    CommandSelectionValidationError
):
    """请求绑定的候选命令列表已经不是当前列表。"""


class CommandSelectionIntegrityError(
    CommandSelectionValidationError
):
    """服务端 interrupt preview 自身不完整或 hash 不自洽。"""


RUN_COMMANDS_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def compute_run_commands_hash(
    run_commands: list[dict[str, Any]],
) -> str:
    """计算键顺序无关、列表顺序敏感的稳定 SHA-256。"""

    canonical_json = json.dumps(
        run_commands,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()


def _validated_command_text(
    command: str,
    *,
    index: int,
) -> str:
    """返回规范化命令，但不在这里判断命令风险。"""

    normalized = command.strip()
    if not normalized:
        raise CommandSelectionValidationError(
            f"修改后的命令不能为空：index={index}"
        )
    if len(normalized) > MAX_COMMAND_EDIT_CHARS:
        raise CommandSelectionValidationError(
            "修改后的命令过长："
            f"index={index}, max={MAX_COMMAND_EDIT_CHARS}"
        )

    # NUL、换行和其他 ASCII 控制字符会让显示、shlex 和审计内容产生歧义。
    if any(
        ord(character) < 32 or ord(character) == 127
        for character in normalized
    ):
        raise CommandSelectionValidationError(
            f"修改后的命令包含控制字符：index={index}"
        )
    return normalized


def normalize_command_edits(
    edits: list[CommandEdit],
    *,
    command_count: int,
) -> list[CommandEdit]:
    """校验索引唯一性和范围，并返回规范化的新对象。"""

    if command_count < 1:
        raise CommandSelectionIntegrityError(
            "当前 command_selection 没有候选命令"
        )
    if len(edits) > MAX_COMMAND_SELECTION_EDITS:
        raise CommandSelectionValidationError(
            "一次 decision 的命令编辑数量过多"
        )

    seen: set[int] = set()
    normalized: list[CommandEdit] = []
    for edit in edits:
        if edit.index in seen:
            raise CommandSelectionValidationError(
                f"命令编辑索引重复：{edit.index}"
            )
        seen.add(edit.index)

        if edit.index >= command_count:
            raise CommandSelectionValidationError(
                f"修改索引超出范围：{edit.index}"
            )
        normalized.append(
            CommandEdit(
                index=edit.index,
                command=_validated_command_text(
                    edit.command,
                    index=edit.index,
                ),
            )
        )
    return normalized


def validate_command_selection_response(
    *,
    run_commands: list[dict[str, Any]],
    response: CommandSelectionResponse,
    expected_preview_hash: str | None = None,
) -> CommandSelectionResponse:
    """把 response 绑定到当前候选列表并返回规范化结果。"""

    if not run_commands:
        raise CommandSelectionIntegrityError(
            "当前 command_selection 没有候选命令"
        )
    for index, item in enumerate(run_commands):
        if not isinstance(item, dict):
            raise CommandSelectionIntegrityError(
                f"候选命令不是对象：index={index}"
            )
        if not isinstance(item.get("command"), str):
            raise CommandSelectionIntegrityError(
                f"候选命令缺少 command：index={index}"
            )

    current_hash = compute_run_commands_hash(run_commands)
    if (
        expected_preview_hash is not None
        and not RUN_COMMANDS_HASH_PATTERN.fullmatch(
            expected_preview_hash
        )
    ):
        raise CommandSelectionIntegrityError(
            "interrupt preview 的 run_commands_hash 格式无效"
        )
    if (
        expected_preview_hash is not None
        and not hmac.compare_digest(
            expected_preview_hash,
            current_hash,
        )
    ):
        raise CommandSelectionIntegrityError(
            "interrupt preview 的 run_commands_hash 与内容不一致"
        )

    if not RUN_COMMANDS_HASH_PATTERN.fullmatch(
        response.run_commands_hash
    ):
        raise StaleCommandSelectionError(
            "命令选择已经过期：run_commands_hash 格式无效"
        )
    if not hmac.compare_digest(
        response.run_commands_hash,
        current_hash,
    ):
        raise StaleCommandSelectionError(
            "命令选择已经过期：run_commands_hash 不匹配"
        )

    if response.selected_index >= len(run_commands):
        raise CommandSelectionValidationError(
            "selected_index 超出范围："
            f"{response.selected_index}"
        )

    normalized_edits = normalize_command_edits(
        response.edits,
        command_count=len(run_commands),
    )
    return response.model_copy(
        update={
            "edits": normalized_edits,
            "run_commands_hash": current_hash,
        }
    )


def apply_command_edits(
    run_commands: list[dict[str, Any]],
    edits: list[CommandEdit],
) -> list[dict[str, Any]]:
    """纯函数：复制候选列表，并只替换允许修改的 command 字段。"""

    normalized_edits = normalize_command_edits(
        edits,
        command_count=len(run_commands),
    )
    effective_commands = deepcopy(run_commands)
    for edit in normalized_edits:
        effective_commands[edit.index]["command"] = (
            edit.command
        )
    return effective_commands
```

这个模块不拒绝 `|`、`&&` 或 `>` 等字符，因为 Command Selection 不是 Shell policy。后续
`action_builder -> risk_check -> execution profile` 必须继续决定命令能否执行；本阶段只拒绝会破坏协议
边界的空值、控制字符、非法索引和 stale identity。

---

## 八、让 Graph 节点复用领域校验

> **本节类型：需要修改项目代码。**
>
> 修改：`app/nodes/command_selection_node.py`。

### 8.1 调整 import

删除本文件中的 `hashlib`、`deepcopy` import，并增加：

```python
from app.command_selection import (
    apply_command_edits,
    compute_run_commands_hash,
    validate_command_selection_response,
)
```

`compute_run_commands_hash` 通过这个 import 仍然存在于
`app.nodes.command_selection_node` 的模块命名空间，因此当前 `app/main.py` 和旧测试的 import 暂时不会
中断。后续可以再单独迁移 import，不要在本阶段同时扩大改动范围。

### 8.2 删除重复实现

删除节点文件中原来的两个函数：

```text
compute_run_commands_hash(...)
_apply_command_edits(...)
```

`build_command_selection_template()`、`ensure_command_selection_input_file()` 保留不变，它们会自动使用新
import 的 `compute_run_commands_hash()`。

### 8.3 替换恢复后的校验与应用代码

在 `command_selection_node()` 中找到：

```python
response = interrupt(payload)
parsed = _normalize_interrupt_response(response, expected_hash)
```

从这里到旧 `_apply_command_edits()` 调用为止，替换成：

```python
response = interrupt(payload)
parsed = _normalize_interrupt_response(
    response,
    expected_hash,
)

# 即使 HTTP 层已经校验，Graph 恢复后仍使用 checkpoint 中的真实
# run_commands 再校验一次，防御 CLI、旧 checkpoint 和其他调用入口。
parsed = validate_command_selection_response(
    run_commands=run_commands,
    response=parsed,
    expected_preview_hash=expected_hash,
)
effective_commands = apply_command_edits(
    run_commands,
    parsed.edits,
)
```

删除旧的 `parsed.run_commands_hash != expected_hash` 分支、旧的
`selected_index < 0 or selected_index >= len(run_commands)` 分支，以及
`_apply_command_edits(run_commands, parsed.edits)` 调用。新领域函数已经统一覆盖这三部分逻辑。

节点后半部分继续写入：

```text
planning/command_selection_record.json
planning/effective_run_commands.json
```

并继续清空旧 `pending_action`、审批、Preflight 和执行结果。命令编辑改变了执行语义，必须由
`action_builder` 重新生成 Action 和 Action Hash。

---

## 九、收紧公开 Decision Schema

> **本节类型：需要修改项目代码。**
>
> 修改：`app/interaction/schemas.py`。

当前 HTTP schema 只要求 hash 非空。Web API 不需要兼容旧 CLI 的短 hash，因此应要求严格的 64 位小写
十六进制值，并在请求解析时拒绝重复索引。

先扩展 `app.schemas` import：

```diff
-from app.schemas import CommandEdit
+from app.schemas import (
+    MAX_COMMAND_SELECTION_EDITS,
+    CommandEdit,
+)
```

然后整体替换 `CommandSelectionDecision`：

```python
class CommandSelectionDecision(InteractionModel):
    """公开 API 的命令选择协议；真正的范围和 stale 校验由 policy 完成。"""

    kind: Literal["command_selection"]
    selected_index: int = Field(ge=0)
    edits: list[CommandEdit] = Field(
        default_factory=list,
        max_length=MAX_COMMAND_SELECTION_EDITS,
    )
    run_commands_hash: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def reject_duplicate_edit_indexes(
        self,
    ) -> "CommandSelectionDecision":
        indexes = [item.index for item in self.edits]
        if len(indexes) != len(set(indexes)):
            raise ValueError(
                "同一命令索引不能在一次 decision 中重复编辑"
            )
        return self
```

这一层能确定字段形状、hash 语法、edit 数量、非负唯一索引、字符串大小和未知字段；它不能确定索引
是否小于当前命令数量，也不能确定 hash 是否属于当前 interrupt，这些事实必须从当前 `JobRecord` 获得。

---

## 十、在 Interaction Policy 中绑定当前 Interrupt

> **本节类型：需要修改项目代码。**
>
> 修改：`app/interaction/policy.py`。

### 10.1 增加 import

```python
from app.command_selection import (
    CommandSelectionIntegrityError,
    CommandSelectionValidationError,
    StaleCommandSelectionError,
    validate_command_selection_response,
)
from app.interaction.schemas import (
    AllowedOperation,
    CommandSelectionDecision,
    Decision,
    DecisionEnvelope,
)
from app.schemas import CommandSelectionResponse
```

原来的 `AllowedOperation`、`Decision`、`DecisionEnvelope` import 不要重复保留。

### 10.2 增加规范化函数

在 `validate_decision()` 后、`decision_to_resume_value()` 前增加：

```python
def normalize_decision_against_record(
    *,
    record: JobRecord,
    decision: Decision,
) -> Decision:
    """使用当前服务端 interrupt 规范化需要绑定动态状态的 decision。"""

    if not isinstance(
        decision,
        CommandSelectionDecision,
    ):
        return decision

    command_interrupts = [
        item
        for item in record.interrupts
        if item.node == "command_selection"
    ]
    if len(command_interrupts) != 1:
        raise JobConflictError(
            "当前 command_selection interrupt 不唯一，"
            "请刷新 Job 后重新确认"
        )

    preview = command_interrupts[0].value_preview
    if not isinstance(preview, dict):
        raise JobConflictError(
            "command_selection interrupt preview 缺失"
        )

    raw_commands = preview.get("run_commands")
    preview_hash = preview.get("run_commands_hash")
    if (
        not isinstance(raw_commands, list)
        or not all(
            isinstance(item, dict)
            for item in raw_commands
        )
        or not isinstance(preview_hash, str)
    ):
        raise JobConflictError(
            "command_selection interrupt preview 不完整"
        )

    response = CommandSelectionResponse(
        selected_index=decision.selected_index,
        edits=decision.edits,
        run_commands_hash=decision.run_commands_hash,
    )
    try:
        normalized = validate_command_selection_response(
            run_commands=raw_commands,
            response=response,
            expected_preview_hash=preview_hash,
        )
    except StaleCommandSelectionError as exc:
        # stale 是并发身份冲突，不是普通表单格式错误。
        raise JobConflictError(str(exc)) from exc
    except CommandSelectionIntegrityError as exc:
        # 服务端 preview 不自洽时也不能把决定排队。
        raise JobConflictError(str(exc)) from exc
    except CommandSelectionValidationError as exc:
        # 非法索引、空命令等属于 422 用户输入错误。
        raise ValueError(str(exc)) from exc

    return decision.model_copy(
        update={
            "selected_index": normalized.selected_index,
            "edits": normalized.edits,
            "run_commands_hash": normalized.run_commands_hash,
        }
    )
```

不要使用浏览器提交的 `run_commands` 做范围校验。浏览器只提交索引、差异和 hash；候选列表必须来自
当前 `JobRecord.interrupts`，否则用户可以伪造一份更长列表来让越界索引通过。

`validate_decision()` 原有逻辑继续保留。它先验证 `waiting_for_input`、Job version、wait generation、
唯一 interrupt node 和 decision kind，之后才读取 command preview。

---

## 十一、在 Durable Resume 入队前调用领域校验

> **本节类型：需要修改项目代码。**
>
> 修改：`app/interaction/service.py`。

扩展 policy import：

```diff
 from app.interaction.policy import (
     allowed_operations,
     decision_to_resume_value,
+    normalize_decision_against_record,
     validate_decision,
 )
```

然后整体替换 `InteractionService.submit_decision()`：

```python
def submit_decision(
    self,
    *,
    job_id: str,
    envelope: DecisionEnvelope,
    idempotency_key: str,
    actor: str,
) -> JobMutationResponse:
    key = _required_idempotency_key(
        idempotency_key
    )
    current = self.job_service.get(job_id)

    # 第一层：Job、generation 和 node 身份。
    expected_node = validate_decision(
        record=current,
        envelope=envelope,
    )

    # 第二层：需要动态服务端状态的 decision 语义。
    normalized_decision = (
        normalize_decision_against_record(
            record=current,
            decision=envelope.decision,
        )
    )
    value = decision_to_resume_value(
        normalized_decision
    )

    # 只有两层校验都成功才允许 durable resume 入队。
    updated, created = self.job_service.resume(
        job_id=job_id,
        expected_node=expected_node,
        value=value,
        idempotency_key=key,
        expected_job_version=(
            envelope.expected_job_version
        ),
        expected_wait_generation=(
            envelope.expected_wait_generation
        ),
        actor=actor,
    )
    return JobMutationResponse(
        job=project_job(updated),
        replayed=not created,
    )
```

Policy 校验和 Store CAS 之间仍可能发生竞争，因此 `JobService.resume()` 必须继续接收 version 和
generation。前置校验不是 CAS 的替代品。

---

## 十二、保证 Decision Route 只调用一次 Mutation

> **本节类型：需要修改项目代码。**
>
> 修改：`app/api/routes.py`。

HTTP middleware 已经记录统一的 `http.request` span。为了避免 route-level telemetry 容错逻辑重新调用
业务 mutation，把 `submit_decision()` 路由改成单次调用：

```python
@router.post(
    "/jobs/{job_id}/decisions",
    response_model=JobMutationResponse,
)
def submit_decision(
    job_id: str,
    body: DecisionEnvelope,
    idempotency_key: IdempotencyKey,
    actor: Actor,
    service: InteractionDependency,
) -> JobMutationResponse:
    # mutation 绝不能放在“捕获任意异常后再调用一次”的 fallback 中。
    # JobConflictError/ValueError 交给 app/api/errors.py 的稳定 handler。
    return service.submit_decision(
        job_id=job_id,
        envelope=body,
        idempotency_key=idempotency_key,
        actor=actor,
    )
```

不要捕获任意异常后再次执行 `service.submit_decision()`。如果以后需要 route-specific span，应实现一个
经过测试的通用 adapter，不能用“失败后重跑业务方法”代替 telemetry 降级。

现有错误映射继续使用：

```text
JobConflictError -> HTTP 409 / JOB_CONFLICT
ValueError       -> HTTP 422 / INVALID_REQUEST
```

因此本阶段不修改 `app/api/errors.py`。

---

## 十三、审核与 Artifact 语义保持不变

> **本节类型：行为说明，不修改项目代码。**

合法 decision 入队后，Store 的 `job_resume_queued` Event 只记录 `value_hash`、generation 和 expected node，
不把完整命令复制到 Event payload 或 metric label。Graph 消费 decision 后继续生成：

```text
planning/command_selection_record.json
planning/effective_run_commands.json
```

然后 `action_builder` 根据选中的 effective command 构建新的 `ExecutableAction` 和 action hash。后续链路
必须保持：

```text
command_selection
  -> action_builder
  -> risk_check
  -> human_review（需要时）
  -> preflight
  -> smoke_test
  -> executor
```

用户编辑命令不等于批准命令。编辑发生后，旧 Action、审批、Preflight 和执行结果都必须失效。

---

## 十四、测试命令选择领域模块

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_command_selection_contract.py`。

```python
from __future__ import annotations

import pytest

from app.command_selection import (
    CommandSelectionIntegrityError,
    CommandSelectionValidationError,
    StaleCommandSelectionError,
    apply_command_edits,
    compute_run_commands_hash,
    validate_command_selection_response,
)
from app.schemas import (
    CommandEdit,
    CommandSelectionResponse,
)


RUN_COMMANDS = [
    {
        "command": "python train.py --dataset_path <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "high",
        "reason": "main training entry",
    },
    {
        "command": "python test.py --checkpoint <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "medium",
        "reason": "evaluation entry",
    },
]


def _response(
    *,
    selected_index: int = 0,
    edits: list[CommandEdit] | None = None,
    run_commands_hash: str | None = None,
) -> CommandSelectionResponse:
    return CommandSelectionResponse(
        selected_index=selected_index,
        edits=edits or [],
        run_commands_hash=(
            run_commands_hash
            or compute_run_commands_hash(RUN_COMMANDS)
        ),
    )


def test_hash_ignores_dict_key_order_but_keeps_list_order():
    reordered_keys = [
        dict(reversed(list(item.items())))
        for item in RUN_COMMANDS
    ]

    assert compute_run_commands_hash(
        reordered_keys
    ) == compute_run_commands_hash(RUN_COMMANDS)
    assert compute_run_commands_hash(
        list(reversed(RUN_COMMANDS))
    ) != compute_run_commands_hash(RUN_COMMANDS)


def test_validates_normalizes_and_applies_multiple_edits():
    response = _response(
        selected_index=1,
        edits=[
            CommandEdit(
                index=0,
                command=(
                    "  python train.py "
                    "--dataset_path /data/ntu60  "
                ),
            ),
            CommandEdit(
                index=1,
                command=(
                    "python test.py --checkpoint "
                    "/data/best.pth"
                ),
            ),
        ],
    )

    normalized = validate_command_selection_response(
        run_commands=RUN_COMMANDS,
        response=response,
        expected_preview_hash=(
            compute_run_commands_hash(RUN_COMMANDS)
        ),
    )
    effective = apply_command_edits(
        RUN_COMMANDS,
        normalized.edits,
    )

    assert normalized.selected_index == 1
    assert normalized.edits[0].command.startswith("python")
    assert effective[0]["command"].endswith("/data/ntu60")
    assert effective[1]["cwd"] == RUN_COMMANDS[1]["cwd"]
    # 纯函数不能反向修改模型生成的原候选列表。
    assert RUN_COMMANDS[0]["command"].endswith("<path>")


def test_rejects_stale_request_hash():
    with pytest.raises(
        StaleCommandSelectionError,
        match="过期",
    ):
        validate_command_selection_response(
            run_commands=RUN_COMMANDS,
            response=_response(
                run_commands_hash="0" * 64
            ),
            expected_preview_hash=(
                compute_run_commands_hash(RUN_COMMANDS)
            ),
        )


def test_rejects_inconsistent_server_preview_hash():
    with pytest.raises(
        CommandSelectionIntegrityError,
        match="preview",
    ):
        validate_command_selection_response(
            run_commands=RUN_COMMANDS,
            response=_response(),
            expected_preview_hash="f" * 64,
        )


@pytest.mark.parametrize(
    ("selected_index", "edits", "message"),
    [
        (2, [], "selected_index"),
        (
            0,
            [CommandEdit(index=2, command="python x.py")],
            "修改索引",
        ),
        (
            0,
            [CommandEdit(index=0, command="   ")],
            "不能为空",
        ),
        (
            0,
            [
                CommandEdit(
                    index=0,
                    command="python x.py\nrm -rf x",
                )
            ],
            "控制字符",
        ),
    ],
)
def test_rejects_invalid_selection_semantics(
    selected_index,
    edits,
    message,
):
    with pytest.raises(
        CommandSelectionValidationError,
        match=message,
    ):
        validate_command_selection_response(
            run_commands=RUN_COMMANDS,
            response=_response(
                selected_index=selected_index,
                edits=edits,
            ),
        )


def test_duplicate_edit_indexes_are_rejected_by_schema():
    with pytest.raises(ValueError, match="重复"):
        _response(
            edits=[
                CommandEdit(index=0, command="python a.py"),
                CommandEdit(index=0, command="python b.py"),
            ]
        )
```

最后一个测试验证静态 Schema，其他测试验证依赖当前候选列表的动态领域语义。不能只测前端，因为 CLI、
API、checkpoint 恢复和未来其他客户端都需要同一边界。

---

## 十五、测试 Interaction Policy 的当前状态绑定

> **本节类型：需要修改测试代码。**
>
> 修改：`tests/test_interaction_policy.py`。

在 import 中加入：

```python
from app.command_selection import compute_run_commands_hash
from app.interaction.policy import (
    allowed_operations,
    decision_to_resume_value,
    normalize_decision_against_record,
    validate_decision,
)
from app.interaction.schemas import (
    ActionApprovalDecision,
    CommandSelectionDecision,
    DecisionEnvelope,
)
```

保留文件原有 helper 和测试，然后在末尾增加：

```python
COMMANDS = [
    {
        "command": "python train.py --dataset_path <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "high",
        "reason": "train",
    },
    {
        "command": "python test.py --checkpoint <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "medium",
        "reason": "test",
    },
]


def _command_waiting_job() -> JobRecord:
    record = _waiting_job(
        node="command_selection"
    )
    command_hash = compute_run_commands_hash(COMMANDS)
    return record.model_copy(
        update={
            "interrupts": [
                JobInterrupt(
                    node="command_selection",
                    value_preview={
                        "message": "select command",
                        "run_commands": COMMANDS,
                        "run_commands_hash": command_hash,
                    },
                )
            ]
        }
    )


def _command_decision(
    *,
    command_hash: str | None = None,
    selected_index: int = 0,
) -> CommandSelectionDecision:
    return CommandSelectionDecision(
        kind="command_selection",
        selected_index=selected_index,
        edits=[
            {
                "index": 0,
                "command": (
                    "  python train.py "
                    "--dataset_path /data/ntu60  "
                ),
            }
        ],
        run_commands_hash=(
            command_hash
            or compute_run_commands_hash(COMMANDS)
        ),
    )


def test_command_decision_is_normalized_against_preview():
    decision = normalize_decision_against_record(
        record=_command_waiting_job(),
        decision=_command_decision(),
    )

    assert isinstance(
        decision,
        CommandSelectionDecision,
    )
    assert decision.edits[0].command == (
        "python train.py --dataset_path /data/ntu60"
    )


def test_stale_command_hash_is_rejected_before_resume():
    with pytest.raises(
        JobConflictError,
        match="run_commands_hash",
    ):
        normalize_decision_against_record(
            record=_command_waiting_job(),
            decision=_command_decision(
                command_hash="0" * 64
            ),
        )


def test_out_of_range_selection_is_user_input_error():
    with pytest.raises(
        ValueError,
        match="selected_index",
    ):
        normalize_decision_against_record(
            record=_command_waiting_job(),
            decision=_command_decision(
                selected_index=2
            ),
        )


def test_tampered_server_preview_is_rejected():
    record = _command_waiting_job()
    preview = dict(
        record.interrupts[0].value_preview
    )
    preview["run_commands_hash"] = "f" * 64
    tampered = record.model_copy(
        update={
            "interrupts": [
                JobInterrupt(
                    node="command_selection",
                    value_preview=preview,
                )
            ]
        }
    )

    with pytest.raises(
        JobConflictError,
        match="preview",
    ):
        normalize_decision_against_record(
            record=tampered,
            decision=_command_decision(),
        )
```

这组测试验证 Policy 使用服务端当前 interrupt，而不是信任客户端提供的候选列表。

---

## 十六、测试 API 在入队前拒绝 Stale Edit

> **本节类型：需要修改测试代码。**
>
> 修改：`tests/test_interaction_api.py`。

在 import 中加入：

```python
from app.command_selection import compute_run_commands_hash
```

在文件末尾增加下面 helper 和测试。它复用当前 `_client()`、`_submit()`、`AUTH` 与 worker fixture：

```python
COMMAND_SELECTION_COMMANDS = [
    {
        "command": "python train.py --dataset_path <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "high",
        "reason": "train",
    },
    {
        "command": "python test.py --checkpoint <path>",
        "cwd": "/data/repo",
        "source": "script",
        "risk_level": "medium",
        "reason": "test",
    },
]


def _mark_command_selection_waiting(
    client,
    service,
    policy_hash,
):
    job_id = _submit(client).json()["job"]["job_id"]
    worker = worker_fixture(
        worker_id="command-api-worker",
        policy_hash=policy_hash,
    )
    service.store.register_worker(
        worker=worker,
        lease_seconds=30,
    )
    claim = service.store.claim_next(
        worker=worker,
        lease_seconds=30,
    )
    assert claim is not None

    command_hash = compute_run_commands_hash(
        COMMAND_SELECTION_COMMANDS
    )
    waiting = service.store.mark_waiting(
        job_id=job_id,
        claim_token=claim.claim_token,
        interrupts=[
            JobInterrupt(
                node="command_selection",
                value_preview={
                    "message": "select command",
                    "run_commands": (
                        COMMAND_SELECTION_COMMANDS
                    ),
                    "run_commands_hash": command_hash,
                },
            )
        ],
        result={},
        actor="command-api-worker",
    )
    return waiting, command_hash


def _post_command_decision(
    client,
    waiting,
    *,
    command_hash,
    selected_index=0,
    edits=None,
    key="command-decision-1",
):
    return client.post(
        f"/v1/jobs/{waiting.job_id}/decisions",
        headers={
            **AUTH,
            "Idempotency-Key": key,
        },
        json={
            "expected_job_version": waiting.version,
            "expected_wait_generation": (
                waiting.wait_generation
            ),
            "decision": {
                "kind": "command_selection",
                "selected_index": selected_index,
                "edits": edits or [],
                "run_commands_hash": command_hash,
            },
        },
    )


def test_stale_command_hash_does_not_queue_resume(
    tmp_path,
    monkeypatch,
):
    client, service, policy_hash = _client(
        tmp_path,
        monkeypatch,
    )
    waiting, _ = _mark_command_selection_waiting(
        client,
        service,
        policy_hash,
    )

    response = _post_command_decision(
        client,
        waiting,
        command_hash="0" * 64,
        key="stale-command-decision",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "JOB_CONFLICT"
    assert service.get(waiting.job_id).status == (
        "waiting_for_input"
    )
    assert all(
        item.event_type != "job_resume_queued"
        for item in service.events(waiting.job_id)
    )


def test_out_of_range_command_index_returns_422(
    tmp_path,
    monkeypatch,
):
    client, service, policy_hash = _client(
        tmp_path,
        monkeypatch,
    )
    waiting, command_hash = (
        _mark_command_selection_waiting(
            client,
            service,
            policy_hash,
        )
    )

    response = _post_command_decision(
        client,
        waiting,
        command_hash=command_hash,
        selected_index=99,
        key="invalid-command-index",
    )

    assert response.status_code == 422
    assert service.get(waiting.job_id).status == (
        "waiting_for_input"
    )


def test_valid_multiple_edits_queue_one_resume(
    tmp_path,
    monkeypatch,
):
    client, service, policy_hash = _client(
        tmp_path,
        monkeypatch,
    )
    waiting, command_hash = (
        _mark_command_selection_waiting(
            client,
            service,
            policy_hash,
        )
    )

    response = _post_command_decision(
        client,
        waiting,
        command_hash=command_hash,
        selected_index=1,
        edits=[
            {
                "index": 0,
                "command": (
                    "python train.py "
                    "--dataset_path /data/ntu60"
                ),
            },
            {
                "index": 1,
                "command": (
                    "python test.py "
                    "--checkpoint /data/best.pth"
                ),
            },
        ],
        key="valid-command-edits",
    )

    assert response.status_code == 200
    assert response.json()["job"]["status"] == "queued"
    queued_events = [
        item
        for item in service.events(waiting.job_id)
        if item.event_type == "job_resume_queued"
    ]
    assert len(queued_events) == 1
    # Event 只保存 value_hash，不复制用户完整命令。
    assert "/data/ntu60" not in str(
        queued_events[0].payload
    )
```

如果项目中的 `JobService` 没有 `get()`，最后几个状态断言改为 `service.store.get(job_id)`；不要为了测试
给产品 Service 新增只用于测试的方法。

---

## 十七、回归 Mutation Route 只调用一次

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_decision_route_exactly_once.py`。

```python
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import install_error_handlers
from app.api.routes import router
from app.job_runtime.errors import JobConflictError
from app.observability.noop import NoOpTelemetry


class CountingConflictService:
    def __init__(self):
        self.calls = 0

    def submit_decision(self, **_kwargs):
        self.calls += 1
        raise JobConflictError("stale decision")


def test_business_conflict_does_not_repeat_mutation():
    service = CountingConflictService()
    app = FastAPI()
    app.state.api_token = None
    app.state.telemetry = NoOpTelemetry()
    app.state.interaction_service = service
    app.include_router(router)
    install_error_handlers(app)
    client = TestClient(app)

    response = client.post(
        "/v1/jobs/job-1/decisions",
        headers={
            "Idempotency-Key": "exactly-once-route-test"
        },
        json={
            "expected_job_version": 4,
            "expected_wait_generation": 2,
            "decision": {
                "kind": "action_approval",
                "decision": "approved",
                "feedback": None,
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "JOB_CONFLICT"
    assert service.calls == 1
```

这里测试的是 route invocation exactly once，不是在宣称整个分布式系统拥有 exactly-once delivery。
真正的 durable mutation 仍依靠 idempotency key、value hash 和 Store CAS 获得可重放语义。

---

## 十八、增加最小前端类型

> **本节类型：需要修改前端代码。**
>
> 修改：`web/src/api/types.ts`。

在 `AllowedOperation` 后增加：

```typescript
export type RunCommandPreview = {
  command: string;
  cwd?: string;
  source?: string;
  risk_level?: string;
  reason?: string;
};

export type CommandSelectionPreview = {
  run_commands: RunCommandPreview[];
  run_commands_hash: string;
};

export type CommandEditPayload = {
  index: number;
  command: string;
};

export type CommandSelectionDecision = {
  kind: "command_selection";
  selected_index: number;
  edits: CommandEditPayload[];
  run_commands_hash: string;
};

export type ReviewDecision = {
  kind:
    | "action_approval"
    | "patch_review"
    | "patch_promotion";
  decision: "approved" | "rejected" | "revise";
  feedback: string | null;
};

export type DecisionPayload =
  | CommandSelectionDecision
  | ReviewDecision;
```

`PublicInterrupt.value_preview` 继续保持 `unknown`。不同 node 的 preview 不应被全局伪装成同一个类型；
`DecisionCard` 必须先做最小运行时检查，再把它视为 `CommandSelectionPreview`。

---

## 十九、让 API Client 接受类型化 Decision

> **本节类型：需要修改前端代码。**
>
> 修改：`web/src/api/client.ts`。

在 type import 中加入 `DecisionPayload`：

```diff
 import type {
     AllowedOperation,
     ArtifactView,
     ChatAskResponse,
     ChatMessage,
+    DecisionPayload,
     JobView,
     ResourceView,
     TimelineResponse,
     UiConfig,
 } from "./types";
```

修改 `submitDecision()` 的第三个参数类型，其他逻辑不变：

```typescript
export const api = {
  // config/listJobs/createJob/... 等现有方法保持不变。
  submitDecision(
    _job: JobView,
    operation: AllowedOperation,
    decision: DecisionPayload,
  ) {
    return request<{ job: JobView }>(operation.endpoint!, {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({
        expected_job_version: operation.expected_job_version,
        expected_wait_generation: operation.expected_wait_generation,
        decision,
      }),
    }).then((value) => value.job);
  },
};
```

前端仍不计算 `run_commands_hash`。它只把服务端 preview 中的 hash 原样带回；真正的 hash 计算和比较只
存在于 Python 领域模块。

---

## 二十、实现简单的多命令编辑卡片

> **本节类型：需要修改前端代码。**
>
> 修改：`web/src/components/DecisionCard.tsx`。

为了避免只给局部 JSX 导致 Hooks 位置错误，下面给出完整文件。直接用它替换当前文件：

```tsx
import { useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import type {
  CommandEditPayload,
  CommandSelectionPreview,
  DecisionPayload,
  JobView,
  RunCommandPreview,
  TimelineItem,
} from "../api/types";

type Props = {
  job: JobView;
  item: TimelineItem;
  onMutation: (
    action: () => Promise<unknown>
  ) => Promise<void>;
};

const MAX_COMMAND_CHARS = 8192;
const HASH_PATTERN = /^[0-9a-f]{64}$/;

function isRecord(
  value: unknown,
): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

export function parseCommandSelectionPreview(
  value: unknown,
): CommandSelectionPreview | null {
  if (!isRecord(value)) return null;
  if (
    !Array.isArray(value.run_commands)
    || typeof value.run_commands_hash !== "string"
    || !HASH_PATTERN.test(value.run_commands_hash)
  ) {
    return null;
  }

  const commands: RunCommandPreview[] = [];
  for (const raw of value.run_commands) {
    if (!isRecord(raw) || typeof raw.command !== "string") {
      return null;
    }
    commands.push({
      command: raw.command,
      cwd: optionalString(raw.cwd),
      source: optionalString(raw.source),
      risk_level: optionalString(raw.risk_level),
      reason: optionalString(raw.reason),
    });
  }
  if (commands.length === 0) return null;

  return {
    run_commands: commands,
    run_commands_hash: value.run_commands_hash,
  };
}

function changedEdits(
  preview: CommandSelectionPreview,
  drafts: string[],
): CommandEditPayload[] {
  return drafts.flatMap((draft, index) => {
    const normalized = draft.trim();
    return normalized === preview.run_commands[index].command
      ? []
      : [{ index, command: normalized }];
  });
}

export function DecisionCard({
  job,
  item,
  onMutation,
}: Props) {
  const operation = item.operation!;
  const commandPreview = (
    operation.decision_kind === "command_selection"
      ? parseCommandSelectionPreview(
          item.interrupt?.value_preview,
        )
      : null
  );

  // operation_id 包含 wait_generation；新 interrupt 会生成新的 timeline key，
  // 因而 React 会重新挂载卡片，不会把旧草稿带入新 generation。
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [draftCommands, setDraftCommands] = useState<string[]>(
    () => (
      commandPreview?.run_commands.map(
        (item) => item.command,
      ) ?? []
    ),
  );
  const [feedback, setFeedback] = useState("");
  const [localError, setLocalError] = useState<string | null>(
    null,
  );
  const [busy, setBusy] = useState(false);

  async function submit(decision: DecisionPayload) {
    setBusy(true);
    setLocalError(null);
    try {
      await onMutation(
        () => api.submitDecision(
          job,
          operation,
          decision,
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  function updateCommand(index: number, command: string) {
    setDraftCommands((current) => current.map(
      (item, itemIndex) => (
        itemIndex === index ? command : item
      ),
    ));
  }

  async function submitCommandSelection(
    event: FormEvent,
  ) {
    event.preventDefault();
    if (!commandPreview) return;

    const invalidIndex = draftCommands.findIndex(
      (command) => (
        !command.trim()
        || command.trim().length > MAX_COMMAND_CHARS
        || /[\u0000-\u001f\u007f]/.test(command.trim())
      ),
    );
    if (invalidIndex >= 0) {
      setLocalError(
        `Command ${invalidIndex + 1} is empty, too long, or contains control characters.`,
      );
      return;
    }

    await submit({
      kind: "command_selection",
      selected_index: selectedIndex,
      edits: changedEdits(
        commandPreview,
        draftCommands,
      ),
      run_commands_hash: (
        commandPreview.run_commands_hash
      ),
    });
  }

  if (operation.decision_kind === "command_selection") {
    if (!commandPreview) {
      return (
        <div className="decision-card inline-error">
          Command preview is incomplete. Refresh the session before deciding.
        </div>
      );
    }

    return (
      <form
        className="decision-card command-editor"
        onSubmit={submitCommandSelection}
      >
        <p>
          Edit only what this machine requires, then choose the
          command to execute first.
        </p>

        {commandPreview.run_commands.map((command, index) => (
          <fieldset
            className="command-edit-row"
            key={`${index}:${command.command}`}
          >
            <label className="command-choice">
              <input
                type="radio"
                name="selected-command"
                aria-label={`Select command ${index + 1}`}
                checked={selectedIndex === index}
                onChange={() => setSelectedIndex(index)}
              />
              Run command {index + 1} first
            </label>

            <label htmlFor={`command-edit-${index}`}>
              Command {index + 1}
            </label>
            <textarea
              id={`command-edit-${index}`}
              rows={3}
              maxLength={MAX_COMMAND_CHARS}
              value={draftCommands[index]}
              onChange={(event) => updateCommand(
                index,
                event.currentTarget.value,
              )}
            />
            <small>
              cwd: {command.cwd ?? "not provided"}
              {command.risk_level
                ? ` / risk: ${command.risk_level}`
                : ""}
            </small>
            {command.reason && <p>{command.reason}</p>}
          </fieldset>
        ))}

        {localError && (
          <p className="inline-error" role="alert">
            {localError}
          </p>
        )}
        <div className="decision-actions">
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              setDraftCommands(
                commandPreview.run_commands.map(
                  (item) => item.command,
                ),
              );
              setLocalError(null);
            }}
          >
            Restore generated commands
          </button>
          <button type="submit" disabled={busy}>
            Continue with selected command
          </button>
        </div>
      </form>
    );
  }

  const kind = operation.decision_kind;
  if (!kind) {
    return (
      <div className="decision-card inline-error">
        Unsupported decision.
      </div>
    );
  }

  const canRevise = operation.allowed_decisions.includes(
    "revise",
  );
  const canApprove = operation.allowed_decisions.includes(
    "approved",
  );
  const canReject = operation.allowed_decisions.includes(
    "rejected",
  );

  return (
    <div className="decision-card">
      <pre>
        {JSON.stringify(
          item.interrupt?.value_preview,
          null,
          2,
        )}
      </pre>
      <label>
        Feedback
        <textarea
          value={feedback}
          onChange={(event) => setFeedback(
            event.currentTarget.value,
          )}
          maxLength={4000}
        />
      </label>
      <div className="decision-actions">
        {canApprove && (
          <button
            disabled={busy}
            onClick={() => void submit({
              kind,
              decision: "approved",
              feedback: feedback || null,
            })}
          >
            Approve
          </button>
        )}
        {canReject && (
          <button
            disabled={busy}
            onClick={() => void submit({
              kind,
              decision: "rejected",
              feedback: feedback || null,
            })}
          >
            Reject
          </button>
        )}
        {canRevise && (
          <button
            disabled={busy}
            onClick={() => void submit({
              kind,
              decision: "revise",
              feedback: feedback || null,
            })}
          >
            Request revision
          </button>
        )}
      </div>
    </div>
  );
}
```

这里只允许改 `command`，不允许改 `cwd`、来源和风险等级。`cwd` 是仓库/Workspace 身份的一部分，开放
任意修改会扩大路径逃逸和审批语义，需要单独设计，不能顺手加入本阶段。

---

## 二十一、增加少量样式

> **本节类型：需要修改前端代码。**
>
> 修改：`web/src/styles/app.css`。

在 Phase 31 样式后追加：

```css
/* Phase 32 command edit */
.command-editor {
  display: grid;
  gap: 0.9rem;
}

.command-edit-row {
  min-width: 0;
  margin: 0;
  border: 1px solid var(--line);
  border-radius: 0.8rem;
  padding: 0.8rem;
}

.command-choice {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.55rem;
  font-weight: 700;
}

.command-choice input {
  width: auto;
  margin: 0;
}

.command-edit-row textarea {
  min-height: 5.8rem;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.82rem;
  resize: vertical;
}
```

不需要引入代码编辑器依赖。命令通常只有一到三行，原生 `textarea` 更容易测试，也不会增加前端构建和
供应链复杂度。

---

## 二十二、前端命令编辑测试

> **本节类型：需要新增前端测试。**
>
> 新增：`web/tests/command-selection.test.tsx`。

```tsx
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { api } from "../src/api/client";
import { DecisionCard } from "../src/components/DecisionCard";
import type {
  AllowedOperation,
  JobView,
  TimelineItem,
} from "../src/api/types";

const commandHash = "a".repeat(64);

const operation: AllowedOperation = {
  operation_id: "wait:2:command_selection",
  kind: "submit_decision",
  endpoint: "/v1/jobs/job-1/decisions",
  decision_kind: "command_selection",
  expected_node: "command_selection",
  expected_job_version: 4,
  expected_wait_generation: 2,
  allowed_decisions: [],
  requires_idempotency_key: true,
  detail: null,
};

const job: JobView = {
  job_id: "job-1",
  thread_id: "thread-1",
  run_id: "run-1",
  status: "waiting_for_input",
  version: 4,
  attempt_count: 1,
  max_attempts: 3,
  wait_generation: 2,
  interrupts: [],
  cancel_requested: false,
  cancellation_reason: null,
  result: null,
  error: null,
  reconciliation: null,
  input: {
    paper_name: "paper.pdf",
    repo_name: "repo",
    experiment_goal: "reproduce main result",
    execution_profile_id: "local",
  },
  allowed_operations: [operation],
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:01:00Z",
};

const item: TimelineItem = {
  item_id: "decision:wait:2:command_selection",
  role: "assistant",
  kind: "decision",
  title: "Select command",
  content: "Choose and edit a command.",
  created_at: "2026-08-01T00:01:00Z",
  event_id: null,
  operation,
  interrupt: {
    node: "command_selection",
    interrupt_id: "interrupt-1",
    value_preview: {
      run_commands: [
        {
          command: "python train.py --dataset_path <path>",
          cwd: "/data/repo",
          risk_level: "high",
          reason: "train",
        },
        {
          command: "python test.py --checkpoint <path>",
          cwd: "/data/repo",
          risk_level: "medium",
          reason: "test",
        },
      ],
      run_commands_hash: commandHash,
    },
  },
};

afterEach(() => {
  vi.restoreAllMocks();
});

function renderCard() {
  const onMutation = vi.fn(
    async (action: () => Promise<unknown>) => {
      await action();
    },
  );
  render(
    <DecisionCard
      job={job}
      item={item}
      onMutation={onMutation}
    />,
  );
  return onMutation;
}

describe("command selection editor", () => {
  it("submits selection without redundant edits", async () => {
    const submit = vi.spyOn(
      api,
      "submitDecision",
    ).mockResolvedValue(job);
    renderCard();

    fireEvent.click(
      screen.getByLabelText("Select command 2"),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue with selected command",
      }),
    );

    await waitFor(() => {
      expect(submit).toHaveBeenCalled();
    });
    expect(submit.mock.calls[0][2]).toEqual({
      kind: "command_selection",
      selected_index: 1,
      edits: [],
      run_commands_hash: commandHash,
    });
  });

  it("submits only changed commands with original indexes", async () => {
    const submit = vi.spyOn(
      api,
      "submitDecision",
    ).mockResolvedValue(job);
    renderCard();

    fireEvent.change(
      screen.getByLabelText("Command 1"),
      {
        target: {
          value: (
            "python train.py "
            + "--dataset_path /data/ntu60"
          ),
        },
      },
    );
    fireEvent.change(
      screen.getByLabelText("Command 2"),
      {
        target: {
          value: (
            "python test.py "
            + "--checkpoint /data/best.pth"
          ),
        },
      },
    );
    fireEvent.click(
      screen.getByLabelText("Select command 2"),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue with selected command",
      }),
    );

    await waitFor(() => {
      expect(submit).toHaveBeenCalled();
    });
    expect(submit.mock.calls[0][2]).toMatchObject({
      selected_index: 1,
      run_commands_hash: commandHash,
      edits: [
        {
          index: 0,
          command: (
            "python train.py "
            + "--dataset_path /data/ntu60"
          ),
        },
        {
          index: 1,
          command: (
            "python test.py "
            + "--checkpoint /data/best.pth"
          ),
        },
      ],
    });
  });

  it("restores generated commands without submitting", () => {
    const submit = vi.spyOn(api, "submitDecision");
    renderCard();
    const first = screen.getByLabelText(
      "Command 1",
    ) as HTMLTextAreaElement;

    fireEvent.change(first, {
      target: { value: "python changed.py" },
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: "Restore generated commands",
      }),
    );

    expect(first.value).toContain("train.py");
    expect(submit).not.toHaveBeenCalled();
  });
});
```

本阶段前端测试只验证表单到协议的投影。hash 计算、stale 识别、索引范围和 durable queue 行为必须由
Python 测试承担。

---

## 二十三、确认浏览器的 Stale Recovery

> **本节类型：需要核对现有代码；Phase 30 已实现时不重复修改。**
>
> 核对：`web/src/App.tsx`。

`runMutation()` 必须保留下面的 409 行为：

```tsx
async function runMutation(
  action: () => Promise<unknown>,
) {
  try {
    await action();
    await Promise.all([
      refreshTimeline(),
      refreshJobs(),
    ]);
  } catch (caught) {
    if (
      caught instanceof ApiClientError
      && caught.status === 409
    ) {
      // 只刷新当前事实，不自动重放旧 decision。
      await refreshTimeline();
      setError(
        "状态已经变化，页面已刷新，请重新确认当前操作。",
      );
      return;
    }
    setError(
      caught instanceof Error
        ? caught.message
        : "操作失败",
    );
  }
}
```

Phase 30 已经有等价代码时不要重复增加第二套 stale state。`TimelineItem.item_id` 使用
`AllowedOperation.operation_id`，后者包含 wait generation；刷新得到新 interrupt 后，旧
`DecisionCard` 会卸载，新卡片从新的 preview 初始化。

这里必须遵守：

```text
409 -> refresh -> 用户重新确认
```

不能改成：

```text
409 -> 把旧 edits 自动提交到新 hash
```

候选命令已经变化时，旧编辑是否仍然合理只能由用户判断。自动迁移会重新引入本阶段正在消除的
TOCTOU 问题。

---

## 二十四、测试与验证顺序

> **本节类型：运行验证，不修改项目代码。**

测试临时文件继续放在项目内 `.pytest-tmp/`。不要把本项目临时脚本写入系统 `/tmp`。

### 24.1 领域、Graph 与 CLI 回归

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m pytest -q \
  tests/test_command_selection_contract.py \
  tests/test_command_selection_node.py \
  tests/test_command_selection_cli.py \
  --basetemp=.pytest-tmp/phase32-domain
```

这一步确认新领域模块没有破坏旧 CLI 和 Graph interrupt 行为。

### 24.2 Interaction 与 API

```bash
python -m pytest -q \
  tests/test_interaction_policy.py \
  tests/test_interaction_api.py \
  tests/test_decision_route_exactly_once.py \
  tests/test_job_store_interaction_semantics.py \
  --basetemp=.pytest-tmp/phase32-interaction
```

重点确认：

```text
stale version -> 409
stale generation -> 409
stale command hash -> 409
invalid index -> 422
valid edits -> exactly one resume event
business conflict -> service method 只调用一次
```

### 24.3 审批与执行身份回归

```bash
python -m pytest -q \
  tests/test_structured_action_and_approval_hash.py \
  tests/test_review_flow.py \
  tests/test_preflight_check_node.py \
  tests/test_executor_node.py \
  tests/test_low_risk_route.py \
  --basetemp=.pytest-tmp/phase32-action
```

命令编辑后必须重新构建 Action，不能因为本阶段只改交互层就跳过旧审批 hash 测试。

### 24.4 前端

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot/web
npm run typecheck
npm test
npm run build
```

### 24.5 静态检查

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m compileall -q app tests
ruff check app tests
```

### 24.6 全量离线回归

```bash
python -m pytest -q \
  -m 'not provider and not postgres and not container_runtime and not network' \
  --basetemp=.pytest-tmp/phase32-all
```

本阶段不需要真实 LLM Provider，不应为了测试命令编辑发送模型请求。

---

## 二十五、手工端到端验收

> **本节类型：手工操作，不修改项目代码。**

### 25.1 启动单机 Stack

先构建前端：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot/web
npm run build
```

再启动单机 API、Job Worker 和 Resource Worker：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
python -m app.main serve-stack \
  --host 127.0.0.1 \
  --port 8000
```

确认：

```bash
curl -s http://127.0.0.1:8000/livez
curl -s http://127.0.0.1:8000/readyz
```

### 25.2 准备一个 Command Selection Job

1. 在 Web Console 创建或打开一个论文复现 Job；
2. 等待 Agent 完成论文分析、仓库扫描、Mapping 和 Experiment Plan；
3. 当 Job 进入 `waiting_for_input` 时确认当前 node 是 `command_selection`；
4. 卡片至少应显示一条候选命令、`cwd` 和风险等级；
5. 浏览器页面不应显示 `input_path`、`run_dir` 或其他内部绝对状态字段。

如果模型只生成一条命令，仍能验证编辑；多命令选择测试可以使用已有测试 fixture，不必为了手工测试让
LLM 强行生成额外命令。

### 25.3 验证单条编辑

例如原命令是：

```text
python train.py --dataset_path <path_to_dataset>
```

把它改为当前机器上的真实路径：

```text
python train.py --dataset_path /data/tianshaoqi24/datasets/example
```

然后：

1. 选中该命令；
2. 点击 `Continue with selected command`；
3. 确认 Job 先变成 `queued`，再由 Worker 恢复；
4. 确认后续重新出现 Action/Risk/Approval，而不是复用旧审批；
5. 打开 Artifact，检查 `planning/effective_run_commands.json` 中是编辑后的命令；
6. 检查 `planning/command_selection_record.json` 中记录了 index 和 hash；
7. 检查 `job_resume_queued` Event 没有复制完整命令。

### 25.4 验证多条编辑和选择

1. 同时修改第 0、1 条命令；
2. 选择第 1 条首先执行；
3. 在浏览器 Network 面板确认 payload 中有两个 edit，index 分别为 0 和 1；
4. 确认 `selected_index` 是 1；
5. 确认未修改的命令不会进入 `edits`；
6. 恢复 Graph 后确认 `edited_run_commands` 保留全部命令，但只替换两个 `command` 字段；
7. `cwd`、`source`、`risk_level` 和 `reason` 必须保持原值。

### 25.5 用两个浏览器标签验证 stale recovery

这是本阶段最重要的手工测试：

1. 在标签 A 和标签 B 打开同一个等待命令选择的 Job；
2. 两个标签都编辑命令，但先不要提交；
3. 在标签 A 提交；
4. 标签 A 应看到任务进入 queued/running；
5. 立即在标签 B 提交旧卡片；
6. 标签 B 应收到 HTTP 409；
7. 页面应刷新 timeline 并提示重新确认；
8. 标签 B 的旧 edits 不能自动应用；
9. Job Event 中只能有一个 `job_resume_queued`；
10. Worker 不能执行两次 command selection resume。

### 25.6 验证非法输入

分别尝试：

```text
清空一条命令
输入只有空格的命令
通过 API 提交 selected_index=999
通过 API 提交重复 edit index
通过 API 提交 63 位 hash
通过 API 提交另一候选列表的 64 位 hash
```

期望行为：

```text
浏览器可提前发现的空值 -> 本地提示，不发送请求
Schema 形状错误             -> 422
动态索引错误                -> 422
stale 64 位 hash            -> 409
所有失败                    -> Job 仍 waiting_for_input
所有失败                    -> 不产生 job_resume_queued
```

---

## 二十六、常见问题

> **本节类型：问题排查，不修改项目代码。**

### 26.1 API 测试突然因为 `run_commands_hash="abc"` 返回 422

公开 `CommandSelectionDecision` 现在要求 64 位小写 hex。涉及 HTTP Decision 的 fixture 应使用
`compute_run_commands_hash(commands)` 或测试用的 `"a" * 64`。Store 层测试中的历史 raw dict 如果不经过
HTTP schema，可以保持原样；不要无差别修改全部 fixture。

### 26.2 提交非法索引后 Job 仍然变成 queued

说明 `InteractionService.submit_decision()` 仍然直接对原 decision 调用
`decision_to_resume_value()`，没有先执行 `normalize_decision_against_record()`。

### 26.3 stale hash 在 Worker 恢复后才报错

说明 Graph 后置校验存在，但 Interaction 前置校验没有接好。检查 Policy 是否从当前
`record.interrupts` 读取 preview，以及 Service 是否在 `JobService.resume()` 之前调用 Policy。

### 26.4 一个 409 导致 Service 被调用两次

检查 `app/api/routes.py::submit_decision()` 是否仍保留宽泛 `except Exception` fallback。运行：

```bash
python -m pytest -q tests/test_decision_route_exactly_once.py
```

### 26.5 前端总是提交 `edits: []`

检查比较的是 `draft.trim()` 和对应的原始 `preview.run_commands[index].command`，并确认 textarea 的
`onChange` 使用原 index 更新数组。不要根据过滤后的数组位置重新编号。

### 26.6 修改命令后直接复用了旧 Approval

这是安全错误。检查 `command_selection_node()` 是否继续清空：

```text
pending_action
pending_action_hash
user_approval
approval_record
preflight_report
execution_result
```

并确认 Action Builder 会从 `edited_run_commands` 重新生成 Action。

### 26.7 第二个标签页的编辑内容消失

如果第一个标签已经提交，这是预期行为。第二个标签持有的 identity 已经 stale，系统宁可要求用户重新
输入，也不能自动把旧 edit 迁移到新 interrupt。

### 26.8 含换行的命令被拒绝

本阶段只支持单条命令字符串，不支持多行脚本。需要多步操作时应由 Experiment Plan 生成多条
`run_commands`，或者以后设计受控 Script Artifact；不要用换行把多条命令塞进一次 edit。

---

## 二十七、本阶段 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 27.1 Human-in-the-loop 输入同样不可信

人工审批不代表输入天然安全。浏览器可能过期、请求可能被手工构造、两个标签页可能同时提交。HITL 仍需
Schema、状态身份、hash、CAS 和审计。

### 27.2 Stale identity 不只是数据库 version

Job version 保护整个聚合状态，wait generation 保护 interrupt 轮次，run command hash 保护决定所针对的
业务对象。Agent 系统经常需要多层 identity，单一 version 无法表达所有语义。

### 27.3 Validate before enqueue, verify after resume

持久队列之前校验可以避免污染 durable state；恢复后校验可以防御其他入口和历史状态。这类似安全系统中
“入口验证 + 使用时验证”，而不是重复劳动。

### 27.4 Exactly-once invocation 不等于 Exactly-once delivery

API route 应只调用一次 Service，但网络超时仍可能让客户端不知道结果。真正可恢复的语义来自：

```text
Idempotency-Key
value hash
Store unique constraint
version/generation CAS
replay response
```

不要只写一个进程锁就宣称实现 exactly once。

### 27.5 UI 消费 Capability，不复制 Policy

Decision Card 根据服务端 `AllowedOperation` 和 interrupt preview 渲染。它不判断命令风险，也不猜 Graph
下一节点。安全策略仍集中在后端确定性代码中。

### 27.6 编辑会创建新的执行身份

Command Edit 不是对旧 Action 的展示修改，而是产生新的 effective command，继而产生新的 Action Hash。
所以审批绑定必须从命令选择一直延伸到执行前。

### 27.7 Audit 不等于到处复制原文

Event 使用 value hash 表示 decision 身份，完整编辑保存在当前 Run 的受控 Artifact。这样既能审计，也
避免命令、路径或潜在敏感参数进入高基数 telemetry。

---

## 二十八、完成标准

> **本节类型：最终验收，不修改项目代码。**

- `CommandEdit` 具有索引、大小、未知字段和控制字符边界；
- hash 计算与 edit 应用集中在纯领域模块；
- Interaction Service 在 queue resume 前绑定当前 interrupt preview；
- stale version、generation 和 command hash 均不会入队；
- 非法索引和空命令不会入队；
- Graph 恢复后执行相同领域校验；
- Decision HTTP route 对一次请求只调用一次 Service；
- Web 支持选择、单条编辑、多条编辑和恢复原值；
- Web 只提交变化项，不允许修改 cwd 和风险字段；
- 409 只刷新，不自动重放旧 edits；
- 编辑后重新生成 Action 和审批身份；
- command selection、Interaction、API、审批、执行和前端回归全部通过；
- 没有增加 LLM 调用、Chat tool、Redis、多用户或复杂编辑器。

---

## 二十九、Phase 32 之后做什么

> **本节类型：后续路线，不修改项目代码。**

在仍然优先单机单用户、暂不判断复现结果成功与否的前提下，下一阶段建议做：

```text
Phase 33：Controlled Local Input Import
```

它解决当前 Web Resource Wizard 只能接受 HTTPS PDF 和 Git URL 的问题，让用户可以安全导入本机 PDF、
Git bundle 或受控仓库 snapshot。重点应是 staging、大小限制、SHA-256、文件类型、软链接、路径边界和
不可变 Resource Identity，而不是简单地把任意宿主机路径传给 Agent。

后续轻量顺序：

```text
P1 受控本地 PDF / Repository 输入导入
P1 Artifact 安全页面内预览与单 Job 导出
P2 Chat Citation Golden Eval
P2 单机 Run / Resource / Chat 数据保留与清理
P3 由评测证明需要后再升级 Chat dense retrieval
```

仍不建议优先做多 Agent、跨 Job 长期记忆、Chat 自动执行、多用户 RBAC、Redis 或消息队列。
