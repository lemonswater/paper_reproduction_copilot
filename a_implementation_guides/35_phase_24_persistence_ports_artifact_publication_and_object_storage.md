# 进入 Phase 24 前：分类论文事实到代码映射与调用预算

> **本节状态：代码已经实现。**
>
> 本节先解决进入持久化改造前暴露出的一个分析阶段问题：旧流程会把
> `method_modules` 中的每个条目都当成独立检索目标。这既会漏掉数据、
> 训练参数和指标，也会因为中英文别名重复调用 LLM 与 Embedding Provider。

---

## 0.1 先明确映射范围

当前 Agent **不会为论文中的每一句话寻找代码**。

以下内容通常没有直接代码入口，因此不会进入代码映射：

- 摘要中的背景描述；
- Introduction 中的研究动机；
- Related Work 中对其他论文的综述；
- 结论中的概括性表达；
- 纯理论推导、证明和没有实现载体的文字。

进入代码检索的是五类对复现有直接行动价值的事实：

| 分类 | 含义 | 典型代码位置 |
|---|---|---|
| `core_method` | 核心模型、算子、网络模块 | `models/`、`modules/` |
| `data_pipeline` | 数据集、加载器、预处理 | `datasets/`、`data/` |
| `training_config` | 优化器、学习率、epoch、batch size | 训练脚本、配置文件 |
| `evaluation_metric` | accuracy、mIoU 等指标 | eval 脚本、metric 函数 |
| `ablation_switch` | 消融变体、功能开关、baseline 差异 | CLI 参数、配置项、条件分支 |

因此，新的链路是：

```text
论文 section 抽取
    ↓
PaperSummary + MethodModule
    ↓
确定性分类、别名合并、预算截断
    ↓
CodeMappingTarget[]
    ↓
每个 target 构造一个 Evidence Pack
    ↓
每个 target 最多执行一次逻辑上的结构化映射
```

这里的“逻辑上一次”不等于底层 HTTP 请求一定只有一次。
如果启用了结构化输出重试或 Provider transport retry，同一个逻辑调用仍可能产生
多个网络请求。

---

## 0.2 本次修改的文件

```text
app/schemas.py
app/config.py
app/state.py
app/tools/mapping_target_tools.py
app/retrieval/query_builder.py
app/prompts/mapping_prompt.py
app/nodes/method_extractor_node.py
app/nodes/code_search_node.py
app/nodes/mapping_node.py
app/nodes/final_report_node.py
.env.example
config/mapping_aliases.example.json

tests/test_mapping_targets.py
tests/test_code_search_mapping_targets.py
tests/test_analysis_planning_structured_nodes.py
```

核心原则是：

```text
LLM 负责从论文 section 抽取事实
程序负责分类、去重、预算和身份绑定
检索器负责生成有限 Evidence Pack
LLM 只能在 Evidence Pack 内做映射判断
```

分类、去重和预算不能再次交给 LLM，否则不仅增加调用次数，还会让同一份论文在
不同运行中产生不稳定的目标列表。

---

## 0.3 增加分类映射 Schema

在 `app/schemas.py` 中增加：

```python
CodeMappingTargetCategory = Literal[
    "core_method",
    "data_pipeline",
    "training_config",
    "evaluation_metric",
    "ablation_switch",
]


class CodeMappingTarget(BaseModel):
    """进入代码检索的、经过确定性去重和预算控制的论文事实。"""

    # 稳定身份，不使用可能重复或变化的显示名称作为字典键。
    target_id: str
    category: CodeMappingTargetCategory
    name: str
    description: str

    # 通用括号缩写可以自动合并；领域同义词通过 alias 配置合并。
    aliases: list[str] = Field(default_factory=list)
    possible_keywords: list[str] = Field(default_factory=list)

    # 保留论文侧 provenance，后续可追溯目标来自哪些论文证据。
    evidence: list[Evidence] = Field(default_factory=list)
    source_evidence_ids: list[str] = Field(default_factory=list)
```

同时扩展旧的 `ModuleMapping`：

```python
class ModuleMapping(BaseModel):
    # 继续保留旧字段，避免旧 Artifact、测试和 checkpoint 全部失效。
    module_name: str

    # 新流程用稳定 ID 和分类表达目标身份。
    target_id: str | None = None
    target_category: CodeMappingTargetCategory = "core_method"

    candidates: list[CodeCandidate] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
```

这里没有直接把 `module_name` 重命名成 `target_name`，原因是项目已经存在大量历史
JSON、评测 fixture 和 checkpoint。保留旧字段并增加新字段，是一次向后兼容迁移。

---

## 0.4 构建确定性的 Mapping Target

新增 `app/tools/mapping_target_tools.py`，它不调用模型，主要完成四项工作：

1. 把论文事实分成五类；
2. 合并核心方法的中英文别名；
3. 为每个目标生成稳定 `target_id`；
4. 在 Provider 调用前执行分类预算和总预算。

稳定 ID 的核心写法：

```python
def _target_id(
    category: CodeMappingTargetCategory,
    canonical_key: str,
) -> str:
    digest = hashlib.sha256(
        f"{category}|{canonical_key}".encode()
    ).hexdigest()[:16]
    return f"mapping_target_{digest}"
```

同一分类、同一规范化名称会得到同一个 ID。这样即使显示名称包含中文、空格或大小写
变化，Evidence Pack 仍可按稳定键传递。

### 0.4.1 核心方法别名合并

很多论文会同时使用全称、缩写、表格短名和不同语言翻译。例如同一个模块可能写成：

```text
Temporal Aggregation Block
TA Block
Temporal Aggregation (TA) Block
时序聚合模块
```

当前实现分两层处理：

```text
通用层：
    自动处理 "Long Name (ABC) Block" 与 "ABC Block" 这类括号缩写

可配置层：
    使用 MAPPING_ALIASES_PATH 指向的 JSON 文件合并领域同义词
```

也就是说，项目代码里不再写死某篇论文的专属规则。真正需要领域词典时，放到配置文件中：

```json
{
  "version": "phase23.5-v2",
  "rules": [
    {
      "canonical_key": "temporal-aggregation-block",
      "aliases": [
        "Temporal Aggregation Block",
        "TAB",
        "Temporal Aggregation (TAB) Block"
      ],
      "match_all": [
        "temporal",
        "aggregation"
      ],
      "exclude_any": [
        "ablation"
      ]
    }
  ]
}
```

对应环境变量：

```dotenv
MAPPING_ALIASES_PATH=config/mapping_aliases.local.json
```

文件不存在或环境变量为空时，Agent 使用通用规则和规范化名称去重；这保证换一篇论文时不会默认套用当前 PSTNet 的术语。

核心读取入口：

```python
mapping_alias_rules = load_mapping_alias_rules(
    settings.mapping_aliases_path
)
```

合并后：

```text
name       = 第一个稳定出现的名称
aliases    = 其他等价名称
description = 去重后的描述摘要
keywords   = 所有别名条目的关键词并集
evidence   = 按 evidence_id/content_hash 去重后的论文证据
```

PSTNet 仍然可以作为一个配置化 alias 示例来验收，但它不再是运行时代码的内置假设。

### 0.4.2 数据集具体名称优先

论文抽取结果中可能同时出现：

```text
widely-used 3D action recognition datasets
MSR-Action3D
NTU RGB+D 60 /120
```

如果直接按抽取顺序取前两个，真正的数据集名称会被泛化短语挤掉。因此
`_named_targets()` 在应用预算前执行稳定排序：

```python
indexed_values.sort(
    key=lambda item: (
        _is_generic_collection_name(
            _named_value(item[1])
        ),
        item[0],
    )
)
```

排序只把 `widely-used`、`commonly used` 等泛化描述放到后面；同一优先级内仍保留
原始顺序，因此结果可复现。

### 0.4.3 训练参数聚合

一篇论文可能抽取几十个实验参数。如果每个参数单独检索，会产生几十次 Embedding
query 和 mapping LLM 调用。

当前实现把普通实验设置聚合为一个目标：

```text
Training and optimization configuration
```

其 `aliases` 包含：

```text
Optimizer
Initial learning rate
Training epochs
Batch size
Temporal kernel size
Spatial search radius
...
```

这些关键词会共同检索训练入口、`argparse`、配置文件和优化器构造代码。

包含 `ablation`、`without`、`variant`、`消融`、`基线` 等标记的设置不会进入普通
训练配置，而会聚合为：

```text
Ablation variants and switches
```

这避免了“训练参数”和“消融开关”在语义上混在一起。

---

## 0.5 增加双层调用预算

在 `app/config.py` 和 `.env.example` 中加入：

```dotenv
# 每篇论文最多选择多少个 section chunk 做结构化抽取。
PAPER_MAX_SECTION_LLM_CALLS=12

# 代码映射总预算。
MAPPING_MAX_TARGETS=12

# 每类目标自己的预算。
MAPPING_MAX_CORE_METHOD_TARGETS=6
MAPPING_MAX_DATA_PIPELINE_TARGETS=2
MAPPING_MAX_TRAINING_CONFIG_TARGETS=1
MAPPING_MAX_EVALUATION_METRIC_TARGETS=2
MAPPING_MAX_ABLATION_SWITCH_TARGETS=1

# 可选领域别名配置。留空时不加载任何论文专属词典。
MAPPING_ALIASES_PATH=
```

第一层预算限制论文理解阶段：

```text
select_extraction_chunks(...)
    -> 最多 PAPER_MAX_SECTION_LLM_CALLS 个 section chunk
```

第二层预算限制代码映射阶段：

```text
分类候选
    -> 每类先截断
    -> 合并结果再受 MAPPING_MAX_TARGETS 限制
```

为什么不能只有总预算：

```text
假设方法模块有 20 个，数据集有 3 个，指标有 2 个

只设总预算 12：
    前 12 个可能全是方法模块
    数据、配置和指标全部消失

分类预算：
    核心方法最多 6
    数据最多 2
    配置最多 1
    指标最多 2
    消融最多 1
```

这样既控制费用，也保留复现闭环需要的信息覆盖面。

当前默认配置下，在不计算重试、调试和修复调用时，前置分析阶段的逻辑调用上界大致为：

```text
section 抽取：最多 12
代码映射：最多 12
实验计划：1
合计：约 25 次逻辑 LLM 调用
```

Embedding 方面：

```text
仓库代码 chunk 向量：
    首次建立索引时按 batch 请求
    后续命中 SQLite cache 时不重复上传

query 向量：
    每个 mapping target 最多 1 次
    默认最多 12 个
```

---

## 0.6 在 Method Extractor 后生成目标 Artifact

`app/nodes/method_extractor_node.py` 在得到 `PaperSummary` 后调用：

```python
mapping_alias_rules = load_mapping_alias_rules(
    settings.mapping_aliases_path
)

mapping_target_result = build_code_mapping_targets(
    paper_summary=summary.model_dump(mode="json"),
    method_modules=[
        module.model_dump(mode="json")
        for module in summary.method_modules
    ],
    max_targets=settings.mapping_max_targets,
    category_limits={
        "core_method": settings.mapping_max_core_method_targets,
        "data_pipeline": settings.mapping_max_data_pipeline_targets,
        "training_config": settings.mapping_max_training_config_targets,
        "evaluation_metric": (
            settings.mapping_max_evaluation_metric_targets
        ),
        "ablation_switch": (
            settings.mapping_max_ablation_switch_targets
        ),
    },
    alias_rules=mapping_alias_rules,
)
```

并写入：

```text
analysis/mapping_targets.json
```

该 Artifact 不只保存最终目标，还保存：

```json
{
  "policy_version": "phase23.5-v2",
  "source_counts": {},
  "limits": {},
  "selected_count": 12,
  "targets": [],
  "dropped": []
}
```

`dropped` 中的原因可能是：

```text
category_budget_exceeded
total_budget_exceeded
```

这让“为什么某个论文事实没有进入代码映射”变成可审计结果，而不是静默丢失。

节点同时把精简后的目标写入 LangGraph state：

```python
return {
    "paper_summary": summary.model_dump(mode="json"),
    "method_modules": [...],  # 保留旧字段
    "mapping_targets": [
        target.model_dump(mode="json")
        for target in mapping_target_result.targets
    ],
    "mapping_targets_path": str(targets_path),
}
```

---

## 0.7 Code Search 按 target_id 生成 Evidence Pack

旧实现使用：

```text
module_name -> EvidencePack
```

名称可能重复，也可能因语言变化而改变。新实现使用：

```text
target_id -> EvidencePack
```

`app/nodes/code_search_node.py` 的关键逻辑：

```python
for position, target in enumerate(targets):
    target_name = target["name"]
    target_id = target["target_id"]
    target_category = target["category"]

    keywords = [
        target_name,
        *target.get("possible_keywords", []),
        *target.get("aliases", []),
    ]

    # 文件名同时包含位置、分类和名称，便于人工排查。
    relative_path = (
        "analysis/retrieval/evidence_packs/"
        f"{position:02d}_"
        f"{_slug(target_category)}_"
        f"{_slug(target_name)}.json"
    )

    packs[target_id] = pack_payload
    pack_paths[target_id] = str(pack_path)
```

例如：

```text
analysis/retrieval/evidence_packs/
    00_core-method_pstnet.json
    01_core-method_pst-convolution.json
    06_data-pipeline_msr-action3d.json
    08_training-config_training-and-optimization-configuration.json
```

文件名用于阅读，`target_id` 才是程序内部身份。

---

## 0.8 Mapping Node 只允许使用对应 Evidence Pack

`app/nodes/mapping_node.py` 先按 `target_id` 读取证据：

```python
pack_payload = (
    evidence_packs.get(target.target_id)
    or evidence_packs.get(target.name)
)
```

第二个按名称读取的分支只用于兼容旧 Artifact。

结构化调用成功后，程序不会直接相信模型返回的目标身份，而是强制覆盖：

```python
mapping = mapping.model_copy(
    update={
        "module_name": target.name,
        "target_id": target.target_id,
        "target_category": target.category,
    }
)
```

随后仍执行已有的 Evidence 边界校验：

```text
模型返回 candidate
    ↓
file_path 必须存在于 Evidence Pack
    ↓
symbol 必须存在于对应 Evidence item
    ↓
evidence_id 必须真实存在
    ↓
repo revision、文件 hash、代码片段 hash 必须仍有效
```

所以分类扩展没有放松原有“模型不能编造代码证据”的安全边界。

最终的 `paper_code_mapping.json` 现在会包含：

```json
{
  "module_name": "MSR-Action3D",
  "target_id": "mapping_target_...",
  "target_category": "data_pipeline",
  "candidates": [],
  "unresolved_questions": []
}
```

最终报告也会显示：

```text
[data_pipeline] MSR-Action3D：首选候选为 ...
[training_config] Training and optimization configuration：首选候选为 ...
```

---

## 0.9 旧 Checkpoint 的兼容策略

旧 checkpoint 只有：

```text
method_modules
```

没有：

```text
mapping_targets
```

`mapping_targets_from_state()` 会在新字段为空时确定性迁移：

```python
def mapping_targets_from_state(
    state: dict[str, Any],
) -> list[CodeMappingTarget]:
    targets = [
        CodeMappingTarget.model_validate(payload)
        for payload in state.get("mapping_targets", [])
    ]
    if targets:
        return targets

    return legacy_method_targets(
        list(state.get("method_modules") or [])
    )
```

兼容路径只会恢复 `core_method`，因为旧 state 没有完整的分类目标 Artifact。
如果希望旧任务也获得数据、训练、指标和消融映射，应使用新 `thread_id` 重新运行，
不要从旧的 `code_search` 或 `mapping` checkpoint 继续。

---

## 0.10 自动化测试

新增的测试覆盖：

```text
tests/test_mapping_targets.py
    中英文方法别名合并
    无 alias 配置时不应用领域知识
    括号缩写与短名自动合并
    可选 alias 配置可读取
    五类目标都能生成
    具体数据集名称优先
    分类预算和总预算
    旧 method_modules state 兼容

tests/test_code_search_mapping_targets.py
    Evidence Pack 按 target_id 保存
    文件名包含分类
    旧 code_search_results 仍按名称保留

tests/test_analysis_planning_structured_nodes.py
    mapping 保留 target_id
    mapping 保留 target_category
    模型返回错误名称时由程序覆盖
```

运行定向测试：

```bash
python -m pytest \
  tests/test_mapping_targets.py \
  tests/test_code_search_mapping_targets.py \
  tests/test_analysis_planning_structured_nodes.py \
  tests/test_mapping_evidence_boundary.py \
  tests/test_semantic_query_builder.py \
  tests/test_method_extractor_hierarchical.py \
  -q
```

预期：

```text
所有定向测试通过
```

检查本次修改文件：

```bash
python -m ruff check \
  app/tools/mapping_target_tools.py \
  app/nodes/method_extractor_node.py \
  app/nodes/code_search_node.py \
  app/nodes/mapping_node.py \
  app/nodes/final_report_node.py \
  app/retrieval/query_builder.py \
  tests/test_mapping_targets.py \
  tests/test_code_search_mapping_targets.py \
  tests/test_analysis_planning_structured_nodes.py
```

---

## 0.11 手工验收

如果要验证某个领域的中英文同义词合并，先创建本次论文对应的
`config/mapping_aliases.local.json`，再设置：

```bash
export MAPPING_ALIASES_PATH=config/mapping_aliases.local.json
```

使用新的 `thread_id` 运行，避免命中旧 checkpoint：

```bash
python -m app.main run-graph \
  "pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf" \
  /data/tianshaoqi24/PST-Convolution-main/ \
  --thread-id phase24-mapping-targets-001 \
  --execution-profile pstnet-local-supervised
```

找到本次 `run_dir` 后检查目标 Artifact：

```bash
python - <<'PY'
import json
from pathlib import Path

# 修改为本次命令输出的实际 run_dir。
run_dir = Path("runs/<actual-run-id>")
path = run_dir / "analysis" / "mapping_targets.json"
payload = json.loads(path.read_text(encoding="utf-8"))

print("selected_count:", payload["selected_count"])
print("source_counts:", payload["source_counts"])
print("limits:", payload["limits"])
print()

for target in payload["targets"]:
    print(
        target["category"],
        target["target_id"],
        target["name"],
    )
PY
```

PSTNet 的合理结果应接近：

```text
core_method        PSTNet
core_method        PST convolution
core_method        PST Transposed Convolution
data_pipeline      MSR-Action3D
data_pipeline      NTU RGB+D 60 /120
training_config    Training and optimization configuration
evaluation_metric  accuracy (%)
evaluation_metric  mIoU (%)
ablation_switch    Ablation variants and switches
```

具体方法目标可能随论文抽取证据变化，但必须满足：

1. `selected_count <= MAPPING_MAX_TARGETS`；
2. 配置 alias 后，同义的 PST convolution 不应产生多个独立目标；
3. `PST convolution` 和 `PST Transposed Convolution` 不能被错误合并；
4. 数据集预算应优先保留真实数据集名称；
5. 每个目标都有唯一 `target_id`；
6. Evidence Pack 和 mapping 通过同一个 `target_id` 关联；
7. 超出预算的目标出现在 `dropped`，而不是静默消失。

---

## 0.12 本次增强后的边界

这次实现解决的是：

```text
只映射 method_modules
    -> 扩展为五类可执行论文事实

中英文同义模块重复调用
    -> 确定性别名合并

目标数量随论文长度失控
    -> section 预算 + 分类映射预算

名称作为跨节点身份不稳定
    -> 稳定 target_id
```

它仍然没有解决：

- 通用跨论文术语本体；
- 利用 Citation Graph 区分本文方法和引用方法；
- 参数级精确代码绑定；
- 一个训练配置目标内部的子参数排序；
- 根据仓库类型动态分配分类预算；
- 跨 run 的 mapping 结果缓存；
- 按调用耗时、token 和费用做动态预算。

这些可以在 Phase 24 的持久 Artifact 与 Catalog 完成后继续扩展。届时
`mapping_targets.json`、Evidence Pack 和 mapping 结果都可以发布到统一 Artifact
Store，为跨任务缓存和评测提供稳定数据基础。

---

# 35. Phase 24：Persistence Ports、Artifact Publication 与 Object Storage

Phase 23 已经稳定了 `job_id`、`artifact_id`、`event_id` 和结构化 Decision
协议，但底层仍然存在两个直接耦合：

```text
JobService / Worker
    -> SqliteJobStore

Artifact API
    -> LangGraph checkpoint
    -> runs/<run_id>/ 本地文件
```

本阶段先切开这些依赖，并完成第一个真实远程存储闭环：

```text
本地 run workspace
    -> 幂等 Artifact Publisher
    -> Local Blob Store 或 S3/MinIO
    -> SQLite Artifact Catalog
    -> Artifact API 流式下载
```

> **本教程中的源码均为待实现代码。**
>
> 除了明确标记为“知识说明”的小节，其余小节都会指出需要新增或修改的文件。
> 你仍然自己修改项目源码；本教程不会直接修改 `app/` 和 `tests/`。

---

## 一、为什么本阶段先迁移 Artifact，而不是立刻迁移全部数据库

> **本节类型：架构决策说明，不修改项目代码。**

当前最明显的本地耦合不是 Job 表，而是：

```text
PDF、日志、JSON、Markdown、补丁和报告
全部依赖当前机器上的 runs/<run_id>/
```

如果先把 Job 表迁移到 MySQL，但 Artifact 仍在本地：

```text
API 实例 A 创建 Job
Worker B 执行 Job
API 实例 C 查询 Artifact
```

API C 仍然无法读取 Worker B 的本地文件。

因此本阶段优先完成：

1. Job Store 接口化，但继续使用 SQLite 实现；
2. Artifact 元数据和二进制内容分层；
3. 本地 Blob Store 与 S3/MinIO 双实现；
4. Worker 在释放 lease 前发布 Artifact；
5. API 从持久 ArtifactStore 下载，而不是读取 run workspace；
6. 历史 Job 可以显式迁移；
7. 用 contract test 固定后端语义。

下一阶段再迁移：

```text
JobRepository
LangGraph Checkpointer
跨主机 worker claim
```

这样每次只替换一个持久化边界，出现问题时更容易定位。

---

## 二、工作区与 ArtifactStore 不能合并

> **本节类型：知识说明，不修改项目代码。**

即使接入 MinIO，也不能删除本地工作区。

训练脚本、Git、CUDA 编译、patch worktree 和日志写入都需要真实文件系统：

```text
runs/<run_id>/
    execution workspace
    可变
    允许进程持续写入
```

对象存储适合的是已经完成写入的不可变内容：

```text
ArtifactStore
    durable publication
    immutable blob
    content-addressed
    Blob 可跨主机读取
```

这里要准确区分 Blob 与元数据：

```text
Phase 24：
    S3/MinIO Blob 可以跨主机读取
    SQLite Job/Catalog metadata 仍要求 API 与 Worker 共享同一主机或共享磁盘

Phase 25：
    Job/Catalog metadata 迁入关系数据库
    LangGraph checkpoint 迁入共享后端
    才形成真正的多主机任务运行时
```

因此 Phase 24 是“先解除大文件对 Worker 本地磁盘的绑定”，不是宣称整个系统已经
完成分布式部署。

正确关系：

```text
Graph node 完成原子文件写入
    ↓
ArtifactRecord 进入 checkpoint
    ↓
Graph 到达 interrupt 或 terminal boundary
    ↓
Worker 校验本地文件
    ↓
Publisher 上传 Blob
    ↓
Catalog 登记当前 revision
    ↓
Job 才进入 waiting/succeeded
```

不要让每个 Graph 节点直接调用 S3。否则：

- 节点测试必须依赖网络；
- 一个节点可能留下半上传对象；
- Graph retry 与上传 retry 混在一起；
- 本地执行工具仍需要把对象重新下载；
- Provider/存储故障会污染业务节点。

---

## 三、本阶段目标

> **本节类型：实现目标，不修改项目代码。**

完成后应满足：

1. `JobService`、`JobWorker`、Heartbeat 和 Reconciler 依赖 `JobStore` Protocol；
2. `SqliteJobStore` 继续实现相同行为；
3. Job Store 的选择集中在 factory；
4. Artifact Blob 使用 SHA-256 内容寻址；
5. 相同内容重复发布不重复上传；
6. 同一个 `artifact_id` 内容变化时形成新 revision；
7. Catalog 不保存 `absolute_path`；
8. 上传顺序为 Blob first、metadata second；
9. Worker 在 lease heartbeat 仍运行时发布 Artifact；
10. 发布完成后才把 Job 标记为 waiting/succeeded；
11. 临时对象存储错误可以从 terminal checkpoint 安全重试；
12. 完整性错误不能自动重试；
13. API 下载使用流，而不是先把 S3 对象完整读入内存；
14. API 不暴露 bucket、object key 和凭据；
15. Local 与 S3/MinIO 后端具有同一 contract；
16. 历史 Phase 23 Job 可以通过 CLI 发布；
17. 删除本地已发布文件后，S3 后端仍能下载；
18. 当前阶段不自动删除 run workspace。

---

## 四、本阶段明确不做什么

> **本节类型：范围说明，不修改项目代码。**

本阶段不做：

- 不实现 MySQL/PostgreSQL JobStore；
- 不迁移 LangGraph checkpoint；
- 不引入 Redis；
- 不引入消息队列；
- 不自动清理本地 run；
- 不实现 S3 presigned URL；
- 不开放公网 bucket；
- 不把 AWS/MinIO 凭据写入数据库；
- 不把 S3 ETag 当作内容 SHA-256；
- 不实现 Artifact 删除和生命周期回收；
- 不实现多租户 bucket 隔离；
- 不实现跨区域复制；
- 不把正在写入的日志实时同步到 S3；
- 不保证用户强制取消瞬间产生的所有临时文件都已发布；
- 不让同步 `run-graph` 自动伪造 Job 身份。

本阶段主要覆盖异步 Job Runtime。旧同步 `run-graph` 继续使用本地 Artifact；服务
化部署应优先使用 `submit-job + run-worker`。

---

## 五、目标架构

> **本节类型：架构说明，不修改项目代码。**

```text
                        +--------------------+
                        | JobStore Protocol  |
                        +---------+----------+
                                  |
                         SqliteJobStore

Graph checkpoint
      |
      | JobExecutionOutcome.artifact_records
      v
+--------------------+
| ArtifactPublisher  |
+---------+----------+
          |
          +---------------------+
          |                     |
          v                     v
  BlobStore Protocol    ArtifactRepository Protocol
          |                     |
    +-----+------+       SqliteArtifactRepository
    |            |
LocalBlobStore  S3BlobStore
                 |
              MinIO / S3

API
 |
 v
PublishedArtifactCatalog
 |
 +--> ArtifactRepository
 +--> BlobStoreRegistry
```

---

## 六、Artifact 一致性模型

> **本节类型：知识说明，不修改项目代码。**

### 6.1 为什么必须 Blob first

安全顺序：

```text
1. 上传并校验 Blob
2. Catalog 切换当前 revision
```

如果步骤 1 后崩溃：

```text
最多留下没有 metadata 的孤儿 Blob
API 不会返回它
后续重试可以复用它
```

如果反过来先写 metadata：

```text
Catalog 已经可见
Blob 还不存在
API 返回一个永远下载失败的 Artifact
```

### 6.2 为什么 object key 使用内容哈希

```text
sha256/ab/abcdef...
```

相同内容：

```text
不同 Job
不同 relative_path
重复重试
```

可以复用同一个 Blob。

访问控制仍然通过：

```text
job_id + artifact_id -> Catalog
```

客户端不能根据 SHA-256 直接读取任意对象。

### 6.3 为什么 Catalog 需要 revision

当前 `artifact_id` 由：

```text
run_id + relative_path
```

稳定生成。同一路径被重新写入时：

```text
artifact_id 不变
sha256 变化
```

Catalog 必须：

```text
保留历史版本
把 head 指向最新版本
revision + 1
```

不能简单把它当成冲突，也不能覆盖后丢失审计信息。

### 6.4 S3 ETag 不是 SHA-256

单段上传时 ETag 经常看起来像 MD5；multipart、加密和不同兼容实现下，其语义
可能变化。本项目始终使用：

```text
ArtifactRecord.sha256
S3 user metadata["sha256"]
ContentLength
```

验证完整性。ETag 只作为后端返回的辅助标识保存。

---

## 七、需要新增和修改的文件

> **本节类型：文件清单，不修改项目代码。**

新增：

```text
app/job_runtime/ports.py
app/job_runtime/factory.py

app/storage/__init__.py
app/storage/errors.py
app/storage/schemas.py
app/storage/ports.py
app/storage/local_blob_store.py
app/storage/s3_blob_store.py
app/storage/artifact_repository.py
app/storage/publisher.py
app/storage/catalog.py
app/storage/factory.py

tests/test_job_store_port.py
tests/test_local_blob_store.py
tests/test_artifact_repository.py
tests/test_artifact_publisher.py
tests/test_worker_artifact_publication.py
tests/test_published_artifact_catalog.py
tests/test_s3_blob_store.py
tests/test_artifact_storage_api.py
```

修改：

```text
pyproject.toml
app/config.py
app/job_runtime/schemas.py
app/job_runtime/service.py
app/job_runtime/worker.py
app/job_runtime/heartbeat.py
app/job_runtime/process_reconcile.py
app/job_runtime/graph_runner.py
app/interaction/artifacts.py
app/api/routes.py
app/api/app.py
app/api/errors.py
app/main.py
.env.example
.gitignore
a_implementation_guides/README.md
```

---

## 八、先修复 Phase 23 TestClient 依赖

> **本节类型：需要修改依赖。**
>
> 修改：`pyproject.toml`

当前环境中：

```text
FastAPI 0.141.1
Starlette 1.3.1
httpx 0.28.1
```

Starlette 的 `TestClient` 已优先使用 `httpx2`。只安装旧 `httpx` 时可能出现弃用
警告，当前环境的 API 测试还会在第一个请求处阻塞。

把可选依赖改成：

```toml
[project.optional-dependencies]
api = [
    "fastapi>=0.141,<1",
    "uvicorn>=0.30,<1",
]

storage-s3 = [
    "boto3>=1.43,<2",
]

dev = [
    "pytest>=8",
    "ruff>=0.6",
    "httpx2>=2.7,<3",
]
```

不要卸载旧 `httpx`，OpenAI、LangSmith 等依赖可能仍然使用它。`httpx2` 是额外
安装的 TestClient 后端。

安装：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent
python -m pip install -e ".[api,storage-s3,dev]"
```

先验证 Phase 23：

```bash
python -m pytest \
  tests/test_interaction_api.py \
  tests/test_interaction_sse.py \
  -q
```

如果这两个文件仍然阻塞，先不要继续存储改造。

参考：

- [Starlette TestClient](https://www.starlette.io/testclient/)
- [HTTPX2 PyPI](https://pypi.org/project/httpx2/)
- [Boto3 PyPI](https://pypi.org/project/boto3/)

---

## 九、增加 Artifact Storage 配置

> **本节类型：需要修改代码。**
>
> 修改：`app/config.py`

在 Job/API 配置之后增加：

```python
    # Phase 24 只实现 sqlite JobStore，但业务层不再依赖具体类。
    job_store_backend: str = os.getenv(
        "JOB_STORE_BACKEND",
        "sqlite",
    )

    # local 用于离线测试和单机回退；s3 同时兼容 AWS S3 与 MinIO。
    artifact_blob_backend: str = os.getenv(
        "ARTIFACT_BLOB_BACKEND",
        "local",
    )

    artifact_catalog_db_path: Path = Path(
        os.getenv(
            "ARTIFACT_CATALOG_DB_PATH",
            "storage/artifacts.sqlite",
        )
    )

    artifact_local_store_dir: Path = Path(
        os.getenv(
            "ARTIFACT_LOCAL_STORE_DIR",
            "storage/artifacts",
        )
    )

    artifact_s3_endpoint_url: str | None = os.getenv(
        "ARTIFACT_S3_ENDPOINT_URL"
    )

    artifact_s3_bucket: str = os.getenv(
        "ARTIFACT_S3_BUCKET",
        "paper-reproduction-artifacts",
    )

    artifact_s3_region: str = os.getenv(
        "ARTIFACT_S3_REGION",
        "us-east-1",
    )

    artifact_s3_prefix: str = os.getenv(
        "ARTIFACT_S3_PREFIX",
        "copilot",
    ).strip("/")

    artifact_s3_force_path_style: bool = _env_bool(
        "ARTIFACT_S3_FORCE_PATH_STYLE",
        True,
    )

    # 生产 bucket 应由 IaC 创建；只在本机 MinIO 手工验收时开启。
    artifact_s3_auto_create_bucket: bool = _env_bool(
        "ARTIFACT_S3_AUTO_CREATE_BUCKET",
        False,
    )

    artifact_s3_connect_timeout_seconds: float = float(
        os.getenv(
            "ARTIFACT_S3_CONNECT_TIMEOUT_SECONDS",
            "5",
        )
    )

    artifact_s3_read_timeout_seconds: float = float(
        os.getenv(
            "ARTIFACT_S3_READ_TIMEOUT_SECONDS",
            "60",
        )
    )

    artifact_s3_max_attempts: int = int(
        os.getenv(
            "ARTIFACT_S3_MAX_ATTEMPTS",
            "3",
        )
    )

    artifact_stream_chunk_bytes: int = int(
        os.getenv(
            "ARTIFACT_STREAM_CHUNK_BYTES",
            str(1024 * 1024),
        )
    )
```

在 `settings = Settings()` 后的目录初始化区域增加：

```python
settings.artifact_catalog_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
```

不要在 import 时创建 S3 bucket，也不要在 import 时连接 MinIO。

在配置校验区域增加：

```python
if settings.job_store_backend not in {
    "sqlite",
}:
    raise ValueError(
        "当前 JOB_STORE_BACKEND 只支持 sqlite"
    )

if settings.artifact_blob_backend not in {
    "local",
    "s3",
}:
    raise ValueError(
        "ARTIFACT_BLOB_BACKEND 必须是 local 或 s3"
    )

if not settings.artifact_s3_bucket.strip():
    raise ValueError(
        "ARTIFACT_S3_BUCKET 不能为空"
    )

if settings.artifact_s3_max_attempts < 1:
    raise ValueError(
        "ARTIFACT_S3_MAX_ATTEMPTS 必须至少为 1"
    )

if settings.artifact_stream_chunk_bytes < 64 * 1024:
    raise ValueError(
        "ARTIFACT_STREAM_CHUNK_BYTES 不能小于 64 KiB"
    )
```

### 9.1 凭据放在哪里

使用 Boto3 标准凭据链：

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN（可选）
```

这些字段不要加入 `Settings` dataclass，不要写入 Job DB，不要进入 Event。

---

## 十、定义 JobStore Protocol

> **本节类型：需要新增代码。**
>
> 新增：`app/job_runtime/ports.py`

完整代码：

```python
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.job_runtime.schemas import (
    HeartbeatResult,
    JobClaim,
    JobEvent,
    JobInterrupt,
    JobRecord,
    JobRequest,
)


@runtime_checkable
class JobStore(Protocol):
    """Job Runtime 使用的完整持久化端口。"""

    def initialize(self) -> None:
        ...

    def submit(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        thread_id: str,
        run_id: str,
        run_dir: str,
        request: JobRequest,
        max_attempts: int,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
        ...

    def get(self, job_id: str) -> JobRecord:
        ...

    def list_jobs(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[JobRecord]:
        ...

    def list_events(
        self,
        job_id: str,
        *,
        limit: int = 200,
    ) -> list[JobEvent]:
        ...

    def list_events_after(
        self,
        job_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 200,
    ) -> list[JobEvent]:
        ...

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: float,
        now: float | None = None,
    ) -> JobClaim | None:
        ...

    def heartbeat(
        self,
        *,
        job_id: str,
        claim_token: str,
        lease_seconds: float,
        now: float | None = None,
    ) -> HeartbeatResult:
        ...

    def mark_waiting(
        self,
        *,
        job_id: str,
        claim_token: str,
        interrupts: list[JobInterrupt],
        result: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def mark_succeeded(
        self,
        *,
        job_id: str,
        claim_token: str,
        result: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def mark_cancelled(
        self,
        *,
        job_id: str,
        claim_token: str,
        reason: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def mark_failed(
        self,
        *,
        job_id: str,
        claim_token: str,
        error: dict[str, Any],
        actor: str,
        retryable: bool = False,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def queue_resume(
        self,
        *,
        job_id: str,
        expected_node: str,
        value: Any,
        idempotency_key: str,
        actor: str,
        expected_job_version: int | None = None,
        expected_wait_generation: int | None = None,
        now: float | None = None,
    ) -> tuple[JobRecord, bool]:
        ...

    def request_cancel(
        self,
        *,
        job_id: str,
        reason: str,
        actor: str,
        idempotency_key: str | None = None,
        expected_job_version: int | None = None,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def list_expired_running(
        self,
        *,
        now: float | None = None,
        limit: int = 100,
    ) -> list[JobRecord]:
        ...

    def requeue_expired(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def require_reconciliation(
        self,
        *,
        job_id: str,
        expired_claim_token: str,
        reconciliation: dict[str, Any],
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...

    def resolve_reconciliation(
        self,
        *,
        job_id: str,
        decision: str,
        detail: str,
        actor: str,
        now: float | None = None,
    ) -> JobRecord:
        ...
```

Protocol 不保存 SQL，也不要求继承。`SqliteJobStore` 只要结构匹配就自动实现。

---

## 十一、增加 JobStore Factory

> **本节类型：需要新增代码。**
>
> 新增：`app/job_runtime/factory.py`

完整代码：

```python
from app.config import settings
from app.job_runtime.ports import JobStore
from app.job_runtime.store import (
    SqliteJobStore,
)


def build_job_store() -> JobStore:
    """把具体后端选择集中在 composition root。"""

    if settings.job_store_backend == "sqlite":
        store = SqliteJobStore(
            settings.job_db_path
        )
        store.initialize()
        return store

    raise ValueError(
        "不支持的 JOB_STORE_BACKEND："
        f"{settings.job_store_backend}"
    )
```

> 修改：`app/job_runtime/service.py`

把：

```python
from app.job_runtime.store import (
    JobConflictError,
    SqliteJobStore,
)
```

改为：

```python
from app.job_runtime.factory import (
    build_job_store,
)
from app.job_runtime.ports import JobStore
from app.job_runtime.store import (
    JobConflictError,
)
```

构造函数改为：

```python
class JobService:
    def __init__(self, store: JobStore):
        self.store = store
        self.store.initialize()
```

文件底部改为：

```python
def build_job_service() -> JobService:
    """CLI、API 和 Worker 共用同一个 JobStore factory。"""

    return JobService(
        build_job_store()
    )
```

> 修改以下文件中的类型注解：

```text
app/job_runtime/worker.py
app/job_runtime/heartbeat.py
app/job_runtime/process_reconcile.py
```

把 `SqliteJobStore` import 和注解改为：

```python
from app.job_runtime.ports import JobStore
```

例如 Worker：

```python
class JobWorker:
    def __init__(
        self,
        *,
        worker_id: str,
        store: JobStore,
        # 其余参数保持不变
    ):
        ...
```

这一阶段不要重命名 `SqliteJobStore`，避免把“接口化”和“数据库迁移”混在一次
改动中。

---

## 十二、定义 Storage 错误

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/__init__.py`

```python
"""Artifact 持久化端口与后端实现。"""
```

> 新增：`app/storage/errors.py`

完整代码：

```python
class ArtifactStorageError(RuntimeError):
    """Artifact 持久层错误基类。"""


class ArtifactNotFoundError(ArtifactStorageError):
    """Catalog 或 Blob 中不存在目标 Artifact。"""


class ArtifactIntegrityError(ArtifactStorageError):
    """身份、路径、大小或 SHA-256 不一致。"""


class ArtifactBackendUnavailable(ArtifactStorageError):
    """网络、超时或后端 5xx 等可重试故障。"""
```

完整性错误不能自动 retry，因为重试不会修复被替换的本地文件。

---

## 十三、定义 Storage Schema

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/schemas.py`

完整代码：

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import (
    ArtifactLayer,
    ArtifactRecord,
)


class StorageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArtifactDescriptor(StorageModel):
    """
    持久 Catalog 中的公开身份。

    故意不包含 absolute_path。
    """

    artifact_id: str
    run_id: str
    layer: ArtifactLayer
    relative_path: str
    media_type: str
    sha256: str
    size_bytes: int = Field(ge=0)
    producer_node: str
    created_at: str

    @classmethod
    def from_record(
        cls,
        record: ArtifactRecord,
    ) -> ArtifactDescriptor:
        return cls(
            artifact_id=record.artifact_id,
            run_id=record.run_id,
            layer=record.layer,
            relative_path=record.relative_path,
            media_type=record.media_type,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
            producer_node=record.producer_node,
            created_at=record.created_at,
        )


class BlobStat(StorageModel):
    backend: str
    object_key: str
    size_bytes: int = Field(ge=0)
    sha256: str
    etag: str | None = None
    version_id: str | None = None


class PublishedArtifact(StorageModel):
    job_id: str
    descriptor: ArtifactDescriptor
    backend: str
    object_key: str
    etag: str | None = None
    object_version_id: str | None = None
    revision: int = Field(ge=1)
    published_at: str


class ArtifactPublicationReport(StorageModel):
    status: Literal["completed"] = "completed"
    artifact_count: int = Field(ge=0)
    published_count: int = Field(ge=0)
    reused_count: int = Field(ge=0)
    backend: str
    artifact_ids: list[str] = Field(
        default_factory=list
    )
```

---

## 十四、定义 Blob 与 Catalog Ports

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/ports.py`

完整代码：

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)


@dataclass(frozen=True)
class OpenedBlob:
    """body 必须由响应迭代器最终关闭。"""

    stat: BlobStat
    body: BinaryIO


@dataclass(frozen=True)
class OpenedArtifact:
    """Catalog 已鉴权定位的元数据与后端流。"""

    artifact: PublishedArtifact
    blob: OpenedBlob


class BlobStore(Protocol):
    backend_name: str

    def ensure_ready(self) -> None:
        ...

    def stat(
        self,
        object_key: str,
    ) -> BlobStat | None:
        ...

    def put_file(
        self,
        *,
        object_key: str,
        source_path: Path,
        expected_sha256: str,
        expected_size: int,
        media_type: str,
    ) -> BlobStat:
        ...

    def open(
        self,
        object_key: str,
    ) -> OpenedBlob:
        ...


class ArtifactRepository(Protocol):
    def initialize(self) -> None:
        ...

    def publish(
        self,
        *,
        job_id: str,
        descriptor: ArtifactDescriptor,
        blob: BlobStat,
    ) -> PublishedArtifact:
        ...

    def find(
        self,
        *,
        job_id: str,
        artifact_id: str,
    ) -> PublishedArtifact | None:
        ...

    def list_for_job(
        self,
        job_id: str,
    ) -> list[PublishedArtifact]:
        ...
```

`BinaryIO` 同时兼容本地文件和 Boto3 `StreamingBody` 所需的 `read()/close()` 使用
方式。静态类型工具如果对 `StreamingBody` 不满意，可后续定义更小的
`ReadableBody Protocol`，本阶段先保持实现直接。`OpenedArtifact` 放在 storage
port 中，是为了让本地兼容 Catalog 和持久 Catalog 返回完全相同的对象，而不互相
依赖具体实现模块。

---

## 十五、实现 Local Blob Store

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/local_blob_store.py`

完整代码：

```python
from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
from uuid import uuid4

from app.storage.errors import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
)
from app.storage.ports import OpenedBlob
from app.storage.schemas import BlobStat
from app.tools.artifact_tools import sha256_file


class LocalBlobStore:
    backend_name = "local"

    def __init__(self, root: Path):
        self.root = root.resolve()

    def ensure_ready(self) -> None:
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _path(self, object_key: str) -> Path:
        logical = PurePosixPath(object_key)
        if (
            logical.is_absolute()
            or not logical.parts
            or any(
                part in {"", ".", ".."}
                for part in logical.parts
            )
        ):
            raise ArtifactIntegrityError(
                "无效的 object_key"
            )

        candidate = (
            self.root.joinpath(
                *logical.parts
            ).resolve()
        )
        if self.root not in candidate.parents:
            raise ArtifactIntegrityError(
                "object_key 逃逸 Blob root"
            )
        return candidate

    def stat(
        self,
        object_key: str,
    ) -> BlobStat | None:
        path = self._path(object_key)
        if not path.is_file():
            return None
        digest = sha256_file(path)
        return BlobStat(
            backend=self.backend_name,
            object_key=object_key,
            size_bytes=path.stat().st_size,
            sha256=digest,
            etag=digest,
        )

    def put_file(
        self,
        *,
        object_key: str,
        source_path: Path,
        expected_sha256: str,
        expected_size: int,
        media_type: str,
    ) -> BlobStat:
        del media_type
        self.ensure_ready()
        source = source_path.resolve()
        if not source.is_file():
            raise ArtifactNotFoundError(
                f"待发布文件不存在：{source}"
            )
        if source.stat().st_size != expected_size:
            raise ArtifactIntegrityError(
                "待发布文件大小与 ArtifactRecord 不一致"
            )
        if sha256_file(source) != expected_sha256:
            raise ArtifactIntegrityError(
                "待发布文件 SHA-256 与 ArtifactRecord 不一致"
            )

        existing = self.stat(object_key)
        if existing is not None:
            if (
                existing.sha256 != expected_sha256
                or existing.size_bytes != expected_size
            ):
                raise ArtifactIntegrityError(
                    "已有 Blob 与目标内容不一致"
                )
            return existing

        target = self._path(object_key)
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temp = target.with_name(
            f".{target.name}.{uuid4().hex}.tmp"
        )
        digest = hashlib.sha256()
        copied = 0
        try:
            with (
                source.open("rb") as source_file,
                temp.open("xb") as target_file,
            ):
                while True:
                    chunk = source_file.read(
                        1024 * 1024
                    )
                    if not chunk:
                        break
                    target_file.write(chunk)
                    digest.update(chunk)
                    copied += len(chunk)
                target_file.flush()
                os.fsync(target_file.fileno())

            if (
                copied != expected_size
                or digest.hexdigest()
                != expected_sha256
            ):
                raise ArtifactIntegrityError(
                    "复制期间源文件发生变化"
                )

            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()

        stored = self.stat(object_key)
        if stored is None:
            raise ArtifactIntegrityError(
                "Blob 原子写入后不可见"
            )
        return stored

    def open(
        self,
        object_key: str,
    ) -> OpenedBlob:
        stat = self.stat(object_key)
        if stat is None:
            raise ArtifactNotFoundError(
                "Artifact Blob 不存在"
            )
        path = self._path(object_key)
        return OpenedBlob(
            stat=stat,
            body=path.open("rb"),
        )
```

Local Blob Store 与 run workspace 必须使用不同目录：

```text
runs/...
storage/artifacts/...
```

否则无法验证“发布后不依赖源文件”。

---

## 十六、实现 S3/MinIO Blob Store

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/s3_blob_store.py`

完整代码：

```python
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    ConnectionClosedError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from app.storage.errors import (
    ArtifactBackendUnavailable,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStorageError,
)
from app.storage.ports import OpenedBlob
from app.storage.schemas import BlobStat
from app.tools.artifact_tools import sha256_file


_TRANSIENT_CODES = {
    "RequestTimeout",
    "SlowDown",
    "Throttling",
    "TooManyRequestsException",
    "ServiceUnavailable",
    "InternalError",
}

_NOT_FOUND_CODES = {
    "404",
    "NoSuchKey",
    "NotFound",
}


class S3BlobStore:
    backend_name = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str,
        endpoint_url: str | None,
        region: str,
        force_path_style: bool,
        auto_create_bucket: bool,
        connect_timeout: float,
        read_timeout: float,
        max_attempts: int,
        client: Any | None = None,
    ):
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.region = region
        self.auto_create_bucket = (
            auto_create_bucket
        )
        self.client = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            config=Config(
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                retries={
                    "mode": "standard",
                    "max_attempts": max_attempts,
                },
                s3={
                    "addressing_style": (
                        "path"
                        if force_path_style
                        else "auto"
                    )
                },
            ),
        )

    def _key(self, object_key: str) -> str:
        logical = PurePosixPath(object_key)
        if (
            logical.is_absolute()
            or not logical.parts
            or any(
                part in {"", ".", ".."}
                for part in logical.parts
            )
        ):
            raise ArtifactIntegrityError(
                "无效的 object_key"
            )
        normalized = "/".join(logical.parts)
        if self.prefix:
            return f"{self.prefix}/{normalized}"
        return normalized

    def _raise_backend(
        self,
        exc: BaseException,
    ) -> NoReturn:
        if isinstance(
            exc,
            (
                EndpointConnectionError,
                ConnectTimeoutError,
                ConnectionClosedError,
                ReadTimeoutError,
            ),
        ):
            raise ArtifactBackendUnavailable(
                "S3 backend 暂时不可用"
            ) from exc

        if isinstance(exc, ClientError):
            error = exc.response.get(
                "Error",
                {},
            )
            code = str(error.get("Code", ""))
            status = int(
                exc.response.get(
                    "ResponseMetadata",
                    {},
                ).get("HTTPStatusCode", 0)
                or 0
            )
            if (
                code in _TRANSIENT_CODES
                or status == 429
                or status >= 500
            ):
                raise ArtifactBackendUnavailable(
                    "S3 backend 暂时不可用"
                ) from exc
            raise ArtifactStorageError(
                "S3 backend 请求失败"
            ) from exc

        raise ArtifactStorageError(
            "S3 SDK 调用失败"
        ) from exc

    def ensure_ready(self) -> None:
        try:
            self.client.head_bucket(
                Bucket=self.bucket
            )
            return
        except ClientError as exc:
            status = int(
                exc.response.get(
                    "ResponseMetadata",
                    {},
                ).get("HTTPStatusCode", 0)
                or 0
            )
            code = str(
                exc.response.get(
                    "Error",
                    {},
                ).get("Code", "")
            )
            missing = (
                status == 404
                or code in {
                    "404",
                    "NoSuchBucket",
                    "NotFound",
                }
            )
            if not (
                missing
                and self.auto_create_bucket
            ):
                self._raise_backend(exc)
        except BotoCoreError as exc:
            self._raise_backend(exc)

        create_kwargs = {
            "Bucket": self.bucket,
        }
        if self.region != "us-east-1":
            create_kwargs[
                "CreateBucketConfiguration"
            ] = {
                "LocationConstraint": (
                    self.region
                )
            }

        try:
            self.client.create_bucket(
                **create_kwargs
            )
        except (
            ClientError,
            BotoCoreError,
        ) as exc:
            self._raise_backend(exc)

    def stat(
        self,
        object_key: str,
    ) -> BlobStat | None:
        key = self._key(object_key)
        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=key,
            )
        except ClientError as exc:
            code = str(
                exc.response.get(
                    "Error",
                    {},
                ).get("Code", "")
            )
            status = int(
                exc.response.get(
                    "ResponseMetadata",
                    {},
                ).get("HTTPStatusCode", 0)
                or 0
            )
            if (
                code in _NOT_FOUND_CODES
                or status == 404
            ):
                return None
            self._raise_backend(exc)
        except BotoCoreError as exc:
            self._raise_backend(exc)

        metadata = response.get(
            "Metadata",
            {},
        )
        sha256 = str(
            metadata.get("sha256", "")
        )
        if not sha256:
            raise ArtifactIntegrityError(
                "S3 对象缺少 sha256 metadata"
            )
        return BlobStat(
            backend=self.backend_name,
            object_key=object_key,
            size_bytes=int(
                response["ContentLength"]
            ),
            sha256=sha256,
            etag=str(
                response.get("ETag", "")
            ).strip('"')
            or None,
            version_id=response.get(
                "VersionId"
            ),
        )

    def put_file(
        self,
        *,
        object_key: str,
        source_path: Path,
        expected_sha256: str,
        expected_size: int,
        media_type: str,
    ) -> BlobStat:
        source = source_path.resolve()
        if not source.is_file():
            raise ArtifactNotFoundError(
                "待发布 Artifact 文件不存在"
            )
        if source.stat().st_size != expected_size:
            raise ArtifactIntegrityError(
                "待发布文件大小与 ArtifactRecord 不一致"
            )
        if sha256_file(source) != expected_sha256:
            raise ArtifactIntegrityError(
                "待发布文件 SHA-256 与 ArtifactRecord 不一致"
            )

        existing = self.stat(object_key)
        if existing is not None:
            if (
                existing.sha256 != expected_sha256
                or existing.size_bytes != expected_size
            ):
                raise ArtifactIntegrityError(
                    "已有 S3 Blob 与目标内容不一致"
                )
            return existing

        key = self._key(object_key)
        try:
            self.client.upload_file(
                str(source),
                self.bucket,
                key,
                ExtraArgs={
                    "ContentType": media_type,
                    "Metadata": {
                        "sha256": expected_sha256,
                        "size-bytes": str(
                            expected_size
                        ),
                    },
                },
            )
        except (
            ClientError,
            BotoCoreError,
        ) as exc:
            self._raise_backend(exc)

        stored = self.stat(object_key)
        if stored is None:
            raise ArtifactBackendUnavailable(
                "S3 上传完成后对象仍不可见"
            )
        if (
            stored.sha256 != expected_sha256
            or stored.size_bytes != expected_size
        ):
            raise ArtifactIntegrityError(
                "S3 上传后完整性校验失败"
            )
        return stored

    def open(
        self,
        object_key: str,
    ) -> OpenedBlob:
        key = self._key(object_key)
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=key,
            )
        except ClientError as exc:
            code = str(
                exc.response.get(
                    "Error",
                    {},
                ).get("Code", "")
            )
            if code in _NOT_FOUND_CODES:
                raise ArtifactNotFoundError(
                    "Artifact Blob 不存在"
                ) from exc
            self._raise_backend(exc)
        except BotoCoreError as exc:
            self._raise_backend(exc)

        metadata = response.get(
            "Metadata",
            {},
        )
        stat = BlobStat(
            backend=self.backend_name,
            object_key=object_key,
            size_bytes=int(
                response["ContentLength"]
            ),
            sha256=str(
                metadata.get("sha256", "")
            ),
            etag=str(
                response.get("ETag", "")
            ).strip('"')
            or None,
            version_id=response.get(
                "VersionId"
            ),
        )
        if not stat.sha256:
            response["Body"].close()
            raise ArtifactIntegrityError(
                "S3 下载对象缺少 sha256 metadata"
            )
        return OpenedBlob(
            stat=stat,
            body=response["Body"],
        )
```

Boto3 的 `upload_file()` 会自动处理大文件 multipart；本项目不使用 ETag 校验
内容，而是保存独立 SHA-256 metadata。

参考：

- [Boto3 上传文件](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-uploading-files.html)
- [S3 HeadObject](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/head_object.html)
- [MinIO Server](https://min.io/docs/minio/linux/reference/minio-server/minio-server.html)

---

## 十七、实现 SQLite Artifact Repository

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/artifact_repository.py`

完整代码：

```python
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from app.storage.errors import (
    ArtifactIntegrityError,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).isoformat()


class SqliteArtifactRepository:
    """
    Artifact versions 与当前 head 分表。

    同一个 artifact_id 可以保留多个 sha256/backend revision。
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(
            "PRAGMA journal_mode=WAL"
        )
        connection.execute(
            "PRAGMA synchronous=NORMAL"
        )
        connection.execute(
            "PRAGMA busy_timeout=30000"
        )
        connection.execute(
            "PRAGMA foreign_keys=ON"
        )
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS artifact_versions (
                    artifact_id TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    backend TEXT NOT NULL,

                    job_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    producer_node TEXT NOT NULL,
                    artifact_created_at TEXT NOT NULL,

                    object_key TEXT NOT NULL,
                    etag TEXT,
                    object_version_id TEXT,
                    published_at REAL NOT NULL,

                    PRIMARY KEY (
                        artifact_id,
                        sha256,
                        backend
                    )
                );

                CREATE TABLE IF NOT EXISTS artifact_heads (
                    artifact_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    current_sha256 TEXT NOT NULL,
                    current_backend TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    updated_at REAL NOT NULL,

                    FOREIGN KEY (
                        artifact_id,
                        current_sha256,
                        current_backend
                    )
                    REFERENCES artifact_versions (
                        artifact_id,
                        sha256,
                        backend
                    )
                );

                CREATE UNIQUE INDEX IF NOT EXISTS
                idx_artifact_heads_job_path
                ON artifact_heads(
                    job_id,
                    relative_path
                );

                CREATE INDEX IF NOT EXISTS
                idx_artifact_heads_job
                ON artifact_heads(
                    job_id,
                    artifact_id
                );
                """
            )

    def _joined_select(self) -> str:
        return """
            SELECT
                v.*,
                h.revision
            FROM artifact_heads AS h
            JOIN artifact_versions AS v
              ON v.artifact_id = h.artifact_id
             AND v.sha256 = h.current_sha256
             AND v.backend = h.current_backend
        """

    def _row_to_published(
        self,
        row: sqlite3.Row,
    ) -> PublishedArtifact:
        return PublishedArtifact(
            job_id=row["job_id"],
            descriptor=ArtifactDescriptor(
                artifact_id=row["artifact_id"],
                run_id=row["run_id"],
                layer=row["layer"],
                relative_path=(
                    row["relative_path"]
                ),
                media_type=row["media_type"],
                sha256=row["sha256"],
                size_bytes=row["size_bytes"],
                producer_node=(
                    row["producer_node"]
                ),
                created_at=(
                    row["artifact_created_at"]
                ),
            ),
            backend=row["backend"],
            object_key=row["object_key"],
            etag=row["etag"],
            object_version_id=(
                row["object_version_id"]
            ),
            revision=row["revision"],
            published_at=_iso(
                row["published_at"]
            ),
        )

    def publish(
        self,
        *,
        job_id: str,
        descriptor: ArtifactDescriptor,
        blob: BlobStat,
    ) -> PublishedArtifact:
        if (
            descriptor.sha256 != blob.sha256
            or descriptor.size_bytes
            != blob.size_bytes
        ):
            raise ArtifactIntegrityError(
                "Blob 与 ArtifactDescriptor 不一致"
            )

        now = time.time()
        connection = self._connect()
        try:
            connection.execute(
                "BEGIN IMMEDIATE"
            )
            head = connection.execute(
                """
                SELECT *
                FROM artifact_heads
                WHERE artifact_id = ?
                """,
                (descriptor.artifact_id,),
            ).fetchone()

            if head is not None and (
                head["job_id"] != job_id
                or head["run_id"]
                != descriptor.run_id
                or head["relative_path"]
                != descriptor.relative_path
            ):
                raise ArtifactIntegrityError(
                    "artifact_id 身份发生冲突"
                )

            existing_version = connection.execute(
                """
                SELECT *
                FROM artifact_versions
                WHERE artifact_id = ?
                  AND sha256 = ?
                  AND backend = ?
                """,
                (
                    descriptor.artifact_id,
                    descriptor.sha256,
                    blob.backend,
                ),
            ).fetchone()
            if (
                existing_version is not None
                and existing_version["object_key"]
                != blob.object_key
            ):
                raise ArtifactIntegrityError(
                    "相同 Artifact version "
                    "对应不同 object_key"
                )

            connection.execute(
                """
                INSERT OR IGNORE INTO artifact_versions (
                    artifact_id,
                    sha256,
                    backend,
                    job_id,
                    run_id,
                    layer,
                    relative_path,
                    media_type,
                    size_bytes,
                    producer_node,
                    artifact_created_at,
                    object_key,
                    etag,
                    object_version_id,
                    published_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    descriptor.artifact_id,
                    descriptor.sha256,
                    blob.backend,
                    job_id,
                    descriptor.run_id,
                    descriptor.layer,
                    descriptor.relative_path,
                    descriptor.media_type,
                    descriptor.size_bytes,
                    descriptor.producer_node,
                    descriptor.created_at,
                    blob.object_key,
                    blob.etag,
                    blob.version_id,
                    now,
                ),
            )

            same_head = (
                head is not None
                and head["current_sha256"]
                == descriptor.sha256
                and head["current_backend"]
                == blob.backend
            )
            if head is None:
                connection.execute(
                    """
                    INSERT INTO artifact_heads (
                        artifact_id,
                        job_id,
                        run_id,
                        relative_path,
                        current_sha256,
                        current_backend,
                        revision,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        descriptor.artifact_id,
                        job_id,
                        descriptor.run_id,
                        descriptor.relative_path,
                        descriptor.sha256,
                        blob.backend,
                        now,
                    ),
                )
            elif not same_head:
                connection.execute(
                    """
                    UPDATE artifact_heads
                    SET current_sha256 = ?,
                        current_backend = ?,
                        revision = revision + 1,
                        updated_at = ?
                    WHERE artifact_id = ?
                    """,
                    (
                        descriptor.sha256,
                        blob.backend,
                        now,
                        descriptor.artifact_id,
                    ),
                )

            row = connection.execute(
                self._joined_select()
                + """
                  WHERE h.artifact_id = ?
                """,
                (descriptor.artifact_id,),
            ).fetchone()
            connection.commit()
            assert row is not None
            return self._row_to_published(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def find(
        self,
        *,
        job_id: str,
        artifact_id: str,
    ) -> PublishedArtifact | None:
        with self._connect() as connection:
            row = connection.execute(
                self._joined_select()
                + """
                  WHERE h.job_id = ?
                    AND h.artifact_id = ?
                """,
                (
                    job_id,
                    artifact_id,
                ),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_published(row)

    def list_for_job(
        self,
        job_id: str,
    ) -> list[PublishedArtifact]:
        with self._connect() as connection:
            rows = connection.execute(
                self._joined_select()
                + """
                  WHERE h.job_id = ?
                  ORDER BY
                    v.layer,
                    v.relative_path
                """,
                (job_id,),
            ).fetchall()
        return [
            self._row_to_published(row)
            for row in rows
        ]
```

Artifact Catalog 使用独立 SQLite 文件，避免直接修改 Phase 22 Job 表。下一阶段
迁移关系数据库时，再用同一个 `ArtifactRepository` contract 实现 SQLAlchemy
后端。

---

## 十八、实现 Artifact Publisher

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/publisher.py`

完整代码：

```python
from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from app.job_runtime.schemas import JobRecord
from app.schemas import ArtifactRecord
from app.storage.errors import (
    ArtifactIntegrityError,
)
from app.storage.ports import (
    ArtifactRepository,
    BlobStore,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    ArtifactPublicationReport,
)
from app.tools.artifact_tools import sha256_file


def artifact_object_key(
    record: ArtifactRecord,
) -> str:
    """使用内容地址，不把本地路径写入 object key。"""

    return (
        f"sha256/{record.sha256[:2]}/"
        f"{record.sha256}"
    )


class ArtifactPublisher:
    def __init__(
        self,
        *,
        repository: ArtifactRepository,
        blob_store: BlobStore,
    ):
        self.repository = repository
        self.blob_store = blob_store
        self.repository.initialize()

    def _source_path(
        self,
        *,
        job: JobRecord,
        record: ArtifactRecord,
    ) -> Path:
        if record.run_id != job.run_id:
            raise ArtifactIntegrityError(
                "Artifact run_id 与 Job 不一致"
            )

        run_root = Path(
            job.run_dir
        ).resolve()
        source = (
            run_root
            / record.relative_path
        ).resolve()
        if (
            source == run_root
            or run_root not in source.parents
        ):
            raise ArtifactIntegrityError(
                "Artifact source 逃逸 run_dir"
            )
        if (
            Path(record.absolute_path).resolve()
            != source
        ):
            raise ArtifactIntegrityError(
                "Artifact absolute_path "
                "与 relative_path 不一致"
            )
        if not source.is_file():
            raise ArtifactIntegrityError(
                "Artifact source 不存在"
            )
        if source.stat().st_size != (
            record.size_bytes
        ):
            raise ArtifactIntegrityError(
                "Artifact source 大小变化"
            )
        if sha256_file(source) != record.sha256:
            raise ArtifactIntegrityError(
                "Artifact source SHA-256 变化"
            )
        return source

    def publish(
        self,
        *,
        job: JobRecord,
        records: Iterable[
            ArtifactRecord | dict
        ],
        ensure_active: Callable[
            [],
            None,
        ] = lambda: None,
    ) -> ArtifactPublicationReport:
        # 同一个 checkpoint 中同一 artifact_id 只发布最后一条。
        latest: dict[str, ArtifactRecord] = {}
        for raw in records:
            record = (
                raw
                if isinstance(
                    raw,
                    ArtifactRecord,
                )
                else ArtifactRecord.model_validate(
                    raw
                )
            )
            latest[record.artifact_id] = record

        published_count = 0
        reused_count = 0
        artifact_ids: list[str] = []

        for record in sorted(
            latest.values(),
            key=lambda item: (
                item.layer,
                item.relative_path,
            ),
        ):
            ensure_active()
            source = self._source_path(
                job=job,
                record=record,
            )
            descriptor = (
                ArtifactDescriptor.from_record(
                    record
                )
            )
            current = self.repository.find(
                job_id=job.job_id,
                artifact_id=record.artifact_id,
            )

            reusable = (
                current is not None
                and current.backend
                == self.blob_store.backend_name
                and current.descriptor.sha256
                == record.sha256
            )
            if reusable:
                blob = self.blob_store.stat(
                    current.object_key
                )
                if (
                    blob is None
                    or blob.sha256
                    != record.sha256
                    or blob.size_bytes
                    != record.size_bytes
                ):
                    raise ArtifactIntegrityError(
                        "Catalog 当前 Blob 不可用"
                    )
                reused_count += 1
            else:
                blob = self.blob_store.put_file(
                    object_key=(
                        artifact_object_key(
                            record
                        )
                    ),
                    source_path=source,
                    expected_sha256=(
                        record.sha256
                    ),
                    expected_size=(
                        record.size_bytes
                    ),
                    media_type=(
                        record.media_type
                    ),
                )
                self.repository.publish(
                    job_id=job.job_id,
                    descriptor=descriptor,
                    blob=blob,
                )
                published_count += 1

            artifact_ids.append(
                record.artifact_id
            )
            ensure_active()

        return ArtifactPublicationReport(
            artifact_count=len(latest),
            published_count=published_count,
            reused_count=reused_count,
            backend=(
                self.blob_store.backend_name
            ),
            artifact_ids=artifact_ids,
        )
```

这里有一个重要细节：即使 Blob 已经存在，只要当前 Catalog head 指向其他 backend，
也要调用 `repository.publish()` 切换 head。上面代码在 `reusable=False` 分支中完成
这一步。

---

## 十九、让 Graph Runner 返回 ArtifactRecord

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/schemas.py`

增加 import：

```python
from app.schemas import ArtifactRecord
```

把 `JobExecutionOutcome` 改为：

```python
class JobExecutionOutcome(JobModel):
    status: Literal[
        "succeeded",
        "waiting_for_input",
        "cancelled",
    ]
    result: dict[str, Any] = Field(
        default_factory=dict
    )
    interrupts: list[JobInterrupt] = Field(
        default_factory=list
    )
    artifact_records: list[
        ArtifactRecord
    ] = Field(default_factory=list)
```

> 修改：`app/job_runtime/graph_runner.py`

增加 import：

```python
from app.schemas import ArtifactRecord
```

在 `_result_summary()` 后增加：

```python
def _artifact_records(
    state: dict[str, Any],
    *,
    expected_run_id: str,
) -> list[ArtifactRecord]:
    """从 checkpoint 提取并验证本次 run 的 Artifact。"""

    records = [
        ArtifactRecord.model_validate(item)
        for item in state.get(
            "artifact_records",
            [],
        )
    ]
    for record in records:
        if record.run_id != expected_run_id:
            raise JobGraphStateError(
                "checkpoint Artifact run_id "
                "与 Job 不一致"
            )
    return records
```

所有创建 `JobExecutionOutcome` 的位置都要增加：

```python
artifact_records=_artifact_records(
    values_or_final_values,
    expected_run_id=claim.job.run_id,
),
```

例如 terminal checkpoint 快速恢复分支完整改为：

```python
        if values and not next_nodes:
            return JobExecutionOutcome(
                status="succeeded",
                result=_result_summary(
                    claim=claim,
                    state=values,
                ),
                artifact_records=(
                    _artifact_records(
                        values,
                        expected_run_id=(
                            claim.job.run_id
                        ),
                    )
                ),
            )
```

初始 interrupt 分支：

```python
        if interrupts:
            if claim.resume_request is None:
                return JobExecutionOutcome(
                    status="waiting_for_input",
                    result=_result_summary(
                        claim=claim,
                        state=values,
                    ),
                    interrupts=interrupts,
                    artifact_records=(
                        _artifact_records(
                            values,
                            expected_run_id=(
                                claim.job.run_id
                            ),
                        )
                    ),
                )
```

旧 resume 对不上新 interrupt 的分支同样使用 `values`。

Graph stream 结束后的 interrupt 分支使用 `final_values`：

```python
        if final_interrupts:
            return JobExecutionOutcome(
                status="waiting_for_input",
                result=_result_summary(
                    claim=claim,
                    state=final_values,
                ),
                interrupts=final_interrupts,
                artifact_records=(
                    _artifact_records(
                        final_values,
                        expected_run_id=(
                            claim.job.run_id
                        ),
                    )
                ),
            )
```

最终 succeeded 分支也使用 `final_values`：

```python
        if not final_next:
            return JobExecutionOutcome(
                status="succeeded",
                result=_result_summary(
                    claim=claim,
                    state=final_values,
                ),
                artifact_records=(
                    _artifact_records(
                        final_values,
                        expected_run_id=(
                            claim.job.run_id
                        ),
                    )
                ),
            )
```

不要只修改最后一个 return。Job 可能在 Worker 重启后直接从函数前半部分返回。

---

## 二十、把 Publisher 接入 Worker

> **本节类型：需要修改代码。**
>
> 修改：`app/job_runtime/worker.py`

增加 import：

```python
from app.storage.errors import (
    ArtifactBackendUnavailable,
)
from app.storage.publisher import (
    ArtifactPublisher,
)
```

构造函数增加参数并保存：

```python
class JobWorker:
    def __init__(
        self,
        *,
        worker_id: str,
        store: JobStore,
        runner: GraphJobRunner | None = None,
        artifact_publisher: (
            ArtifactPublisher | None
        ) = None,
        lease_seconds: float | None = None,
        heartbeat_seconds: float | None = None,
        poll_seconds: float | None = None,
    ):
        # 原有校验保持不变
        self.artifact_publisher = (
            artifact_publisher
        )
```

`run_once()` 的主 try 块改为下面结构。重点是发布发生在 `with heartbeat` 内：

```python
        try:
            with heartbeat:
                outcome = self.runner.execute(
                    claim,
                    heartbeat,
                )
                heartbeat.raise_if_unhealthy()

                publication = None
                if (
                    self.artifact_publisher
                    is not None
                ):
                    publication = (
                        self.artifact_publisher
                        .publish(
                            job=claim.job,
                            records=(
                                outcome
                                .artifact_records
                            ),
                            ensure_active=(
                                heartbeat
                                .raise_if_unhealthy
                            ),
                        )
                    )
                heartbeat.raise_if_unhealthy()

            result = dict(outcome.result)
            if publication is not None:
                result[
                    "artifact_publication"
                ] = publication.model_dump()

            if outcome.status == "waiting_for_input":
                self.store.mark_waiting(
                    job_id=claim.job.job_id,
                    claim_token=claim.claim_token,
                    interrupts=outcome.interrupts,
                    result=result,
                    actor=self.worker_id,
                )
            elif outcome.status == "cancelled":
                self.store.mark_cancelled(
                    job_id=claim.job.job_id,
                    claim_token=claim.claim_token,
                    reason=(
                        heartbeat.cancellation_reason
                        or "runner cancelled"
                    ),
                    actor=self.worker_id,
                )
            else:
                self.store.mark_succeeded(
                    job_id=claim.job.job_id,
                    claim_token=claim.claim_token,
                    result=result,
                    actor=self.worker_id,
                )
        except ArtifactBackendUnavailable as exc:
            try:
                self.store.mark_failed(
                    job_id=claim.job.job_id,
                    claim_token=claim.claim_token,
                    error=self._error_payload(
                        exc
                    ),
                    actor=self.worker_id,
                    # Graph 已有 checkpoint；远程存储恢复后可重新发布。
                    retryable=True,
                )
            except LeaseLostError:
                pass
```

上面的 `ArtifactBackendUnavailable` 分支必须放在原有
`except JobCancellationRequested` 和通用 `except Exception` 之前，随后保留原来的
其他异常分支。

`ArtifactIntegrityError` 会进入原有未知异常分支并 `retryable=False`，这是预期行为。

### 20.1 为什么发布时仍要 heartbeat

大文件 multipart 上传可能比 lease 长。如果先退出 heartbeat context：

```text
Worker A 上传中
lease 过期
Worker B claim 同一个 Job
两个 worker 同时发布并写终态
```

Heartbeat 线程必须覆盖：

```text
Graph execute
Artifact publish
Job terminal/waiting 提交前
```

最终 Store 写入仍由 claim token fencing。

---

## 二十一、实现 Published Artifact Catalog

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/catalog.py`

完整代码：

```python
from __future__ import annotations

from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.storage.errors import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
)
from app.storage.ports import (
    ArtifactRepository,
    BlobStore,
    OpenedArtifact,
)


class BlobStoreRegistry:
    def __init__(
        self,
        stores: list[BlobStore],
    ):
        self._stores = {
            item.backend_name: item
            for item in stores
        }

    def get(self, backend: str) -> BlobStore:
        store = self._stores.get(backend)
        if store is None:
            raise ArtifactNotFoundError(
                "当前进程没有注册 Artifact backend："
                f"{backend}"
            )
        return store


class PublishedArtifactCatalog:
    def __init__(
        self,
        *,
        repository: ArtifactRepository,
        registry: BlobStoreRegistry,
    ):
        self.repository = repository
        self.registry = registry
        self.repository.initialize()

    def list_views(
        self,
        job: JobRecord,
    ) -> list[ArtifactView]:
        return [
            ArtifactView(
                artifact_id=(
                    item.descriptor.artifact_id
                ),
                run_id=item.descriptor.run_id,
                layer=item.descriptor.layer,
                relative_path=(
                    item.descriptor.relative_path
                ),
                media_type=(
                    item.descriptor.media_type
                ),
                sha256=item.descriptor.sha256,
                size_bytes=(
                    item.descriptor.size_bytes
                ),
                producer_node=(
                    item.descriptor.producer_node
                ),
                created_at=(
                    item.descriptor.created_at
                ),
                integrity_status="unchecked",
            )
            for item in (
                self.repository.list_for_job(
                    job.job_id
                )
            )
            if item.descriptor.run_id
            == job.run_id
        ]

    def open(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> OpenedArtifact:
        artifact = self.repository.find(
            job_id=job.job_id,
            artifact_id=artifact_id,
        )
        if artifact is None:
            raise ArtifactNotFoundError(
                "当前 Job 中不存在 "
                f"artifact_id={artifact_id}"
            )
        if artifact.descriptor.run_id != (
            job.run_id
        ):
            raise ArtifactIntegrityError(
                "Catalog Artifact run_id "
                "与 Job 不一致"
            )

        store = self.registry.get(
            artifact.backend
        )
        opened = store.open(
            artifact.object_key
        )
        if (
            opened.stat.sha256
            != artifact.descriptor.sha256
            or opened.stat.size_bytes
            != artifact.descriptor.size_bytes
        ):
            opened.body.close()
            raise ArtifactIntegrityError(
                "Blob 与 Catalog 当前 revision "
                "不一致"
            )
        return OpenedArtifact(
            artifact=artifact,
            blob=opened,
        )
```

Registry 同时注册 local 和 s3 后，可以在迁移期间读取两个 backend 的历史
revision。

---

## 二十二、让 Phase 23 Local Catalog 也支持流式 open

> **本节类型：需要修改代码。**
>
> 修改：`app/interaction/artifacts.py`

保留原 `resolve()` 和原测试。先把原有 typing import：

```python
from typing import Any
```

改为：

```python
from typing import Any, Protocol
```

再增加 storage import：

```python
from app.storage.ports import (
    OpenedArtifact,
    OpenedBlob,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)
```

在 `StateReader` 后、`LocalArtifactCatalog` 前定义统一端口：

```python
class ArtifactCatalog(Protocol):
    """
    HTTP 层只依赖该协议。

    LocalArtifactCatalog 和 PublishedArtifactCatalog 都通过结构化类型
    自动满足，不需要继承。
    """

    def list_views(
        self,
        job: JobRecord,
    ) -> list[ArtifactView]:
        ...

    def open(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> OpenedArtifact:
        ...
```

在 `LocalArtifactCatalog` 中增加：

```python
    def open(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> OpenedArtifact:
        """Phase 23 本地兼容适配器。"""

        resolved = self.resolve(
            job=job,
            artifact_id=artifact_id,
        )
        descriptor = (
            ArtifactDescriptor.from_record(
                resolved.record
            )
        )
        published = PublishedArtifact(
            job_id=job.job_id,
            descriptor=descriptor,
            backend="legacy-local",
            object_key=(
                resolved.record.relative_path
            ),
            etag=resolved.record.sha256,
            revision=1,
            published_at=(
                resolved.record.created_at
            ),
        )
        return OpenedArtifact(
            artifact=published,
            blob=OpenedBlob(
                stat=BlobStat(
                    backend="legacy-local",
                    object_key=(
                        resolved.record
                        .relative_path
                    ),
                    size_bytes=(
                        resolved.record
                        .size_bytes
                    ),
                    sha256=(
                        resolved.record.sha256
                    ),
                    etag=(
                        resolved.record.sha256
                    ),
                ),
                body=resolved.path.open("rb"),
            ),
        )
```

这个兼容适配器只用于旧测试和迁移前回退。新 API 默认使用
`PublishedArtifactCatalog`。HTTP 层使用 `ArtifactCatalog` Protocol，因此两个
实现可以无条件互换，测试也不需要连接真实 storage。

---

## 二十三、实现 Storage Factory

> **本节类型：需要新增代码。**
>
> 新增：`app/storage/factory.py`

完整代码：

```python
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.storage.artifact_repository import (
    SqliteArtifactRepository,
)
from app.storage.catalog import (
    BlobStoreRegistry,
    PublishedArtifactCatalog,
)
from app.storage.local_blob_store import (
    LocalBlobStore,
)
from app.storage.ports import (
    ArtifactRepository,
    BlobStore,
)
from app.storage.publisher import (
    ArtifactPublisher,
)


@dataclass(frozen=True)
class ArtifactStorageBundle:
    repository: ArtifactRepository
    stores: list[BlobStore]
    publisher: ArtifactPublisher
    catalog: PublishedArtifactCatalog


def build_artifact_storage() -> (
    ArtifactStorageBundle
):
    repository = (
        SqliteArtifactRepository(
            settings.artifact_catalog_db_path
        )
    )
    repository.initialize()

    local = LocalBlobStore(
        settings.artifact_local_store_dir
    )
    local.ensure_ready()
    stores: list[BlobStore] = [local]

    if settings.artifact_blob_backend == "local":
        selected: BlobStore = local
    elif (
        settings.artifact_blob_backend
        == "s3"
    ):
        # 动态 import：只使用 local 时不强制安装 boto3。
        from app.storage.s3_blob_store import (
            S3BlobStore,
        )

        selected = S3BlobStore(
            bucket=(
                settings.artifact_s3_bucket
            ),
            prefix=(
                settings.artifact_s3_prefix
            ),
            endpoint_url=(
                settings
                .artifact_s3_endpoint_url
            ),
            region=(
                settings.artifact_s3_region
            ),
            force_path_style=(
                settings
                .artifact_s3_force_path_style
            ),
            auto_create_bucket=(
                settings
                .artifact_s3_auto_create_bucket
            ),
            connect_timeout=(
                settings
                .artifact_s3_connect_timeout_seconds
            ),
            read_timeout=(
                settings
                .artifact_s3_read_timeout_seconds
            ),
            max_attempts=(
                settings
                .artifact_s3_max_attempts
            ),
        )
        stores.append(selected)
    else:
        raise ValueError(
            "不支持的 ARTIFACT_BLOB_BACKEND："
            f"{settings.artifact_blob_backend}"
        )

    registry = BlobStoreRegistry(stores)
    return ArtifactStorageBundle(
        repository=repository,
        stores=stores,
        publisher=ArtifactPublisher(
            repository=repository,
            blob_store=selected,
        ),
        catalog=PublishedArtifactCatalog(
            repository=repository,
            registry=registry,
        ),
    )
```

### 23.1 迁移期间读取旧 S3 backend

当前 factory 只在 `ARTIFACT_BLOB_BACKEND=s3` 时注册 S3。如果已经发布过 S3
Artifact，之后把配置切回 local，API 无法读取旧 S3 head，这是明确的 fail closed。

生产迁移时应增加：

```text
ARTIFACT_READ_BACKENDS=local,s3
```

本教程第一版不增加该配置，手工验收期间保持 API 和 Worker backend 一致。

---

## 二十四、让 API 从持久 Catalog 流式下载

> **本节类型：需要修改代码。**
>
> 修改：`app/api/routes.py`

删除：

```python
from fastapi.responses import FileResponse
```

保留 `StreamingResponse`，增加：

```python
from collections.abc import Iterator
from urllib.parse import quote

from app.interaction.artifacts import (
    ArtifactCatalog,
)
```

将依赖类型从 `LocalArtifactCatalog` 改为：

```python
def artifact_catalog(
    request: Request,
) -> ArtifactCatalog:
    return request.app.state.artifact_catalog


ArtifactCatalogDependency = Annotated[
    ArtifactCatalog,
    Depends(artifact_catalog),
]
```

这里不能注解为 `PublishedArtifactCatalog`。路由只需要 `list_views()` 和 `open()`，
依赖具体类会让 Phase 23 的 `LocalArtifactCatalog` 测试适配器在静态类型上失效。

在路由前增加流迭代器：

```python
def _iter_blob(
    body,
    *,
    chunk_bytes: int,
) -> Iterator[bytes]:
    """无论客户端正常完成还是中断，最终都关闭后端 body。"""

    try:
        while True:
            chunk = body.read(chunk_bytes)
            if not chunk:
                break
            yield chunk
    finally:
        body.close()
```

用下面完整函数替换 `download_artifact()`：

```python
@router.get(
    "/jobs/{job_id}/artifacts/"
    "{artifact_id}/content"
)
def download_artifact(
    job_id: str,
    artifact_id: str,
    _actor: Actor,
    service: InteractionDependency,
    catalog: ArtifactCatalogDependency,
) -> StreamingResponse:
    internal_job = (
        service.job_service.get(job_id)
    )
    opened = catalog.open(
        job=internal_job,
        artifact_id=artifact_id,
    )
    descriptor = (
        opened.artifact.descriptor
    )
    filename = Path(
        descriptor.relative_path
    ).name

    return StreamingResponse(
        _iter_blob(
            opened.blob.body,
            chunk_bytes=(
                settings
                .artifact_stream_chunk_bytes
            ),
        ),
        media_type=descriptor.media_type,
        headers={
            "Content-Length": str(
                descriptor.size_bytes
            ),
            "Content-Disposition": (
                "attachment; filename*=UTF-8''"
                f"{quote(filename)}"
            ),
            "ETag": (
                f'"sha256:{descriptor.sha256}"'
            ),
            "Cache-Control": (
                "private, no-store"
            ),
        },
    )
```

第一版不实现 HTTP Range。如果模型 checkpoint 或大数据集需要断点下载，再单独
增加 Range contract，不能只在 S3 分支临时支持。

---

## 二十五、修改 API App Factory

> **本节类型：需要修改代码。**
>
> 修改：`app/api/app.py`

将 `LocalArtifactCatalog` import 改为：

```python
from app.interaction.artifacts import (
    ArtifactCatalog,
)
from app.storage.factory import (
    build_artifact_storage,
)
```

参数改为：

```python
def create_api_app(
    *,
    job_service: JobService | None = None,
    artifact_catalog: (
        ArtifactCatalog | None
    ) = None,
    api_token: str | None = None,
) -> FastAPI:
```

在设置 `app.state` 前构建一次 storage：

```python
    selected_catalog = artifact_catalog
    if selected_catalog is None:
        selected_catalog = (
            build_artifact_storage().catalog
        )
```

赋值改为：

```python
    app.state.artifact_catalog = (
        selected_catalog
    )
```

测试仍然可以注入 `LocalArtifactCatalog`。上一节定义的 `ArtifactCatalog`
Protocol 是正式边界，不要为了消除类型错误而让测试连接真实 storage，也不要退回
具体 Catalog 注解。

---

## 二十六、增加 Storage API 错误映射

> **本节类型：需要修改代码。**
>
> 修改：`app/api/errors.py`

增加 import：

```python
from app.storage.errors import (
    ArtifactBackendUnavailable,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
)
```

在 `install_error_handlers()` 中增加：

```python
    @app.exception_handler(
        ArtifactNotFoundError
    )
    async def handle_artifact_not_found(
        request: Request,
        exc: ArtifactNotFoundError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=404,
            code="ARTIFACT_NOT_FOUND",
            message=str(exc),
        )

    @app.exception_handler(
        ArtifactIntegrityError
    )
    async def handle_artifact_integrity(
        request: Request,
        exc: ArtifactIntegrityError,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=409,
            code="ARTIFACT_INTEGRITY_ERROR",
            message=str(exc),
        )

    @app.exception_handler(
        ArtifactBackendUnavailable
    )
    async def handle_artifact_unavailable(
        request: Request,
        exc: ArtifactBackendUnavailable,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=503,
            code="ARTIFACT_BACKEND_UNAVAILABLE",
            message=str(exc),
        )
```

不要把 S3 endpoint、bucket、access key 或原始 ClientError response 返回给客户端。

---

## 二十七、把 Publisher 注入 Worker CLI

> **本节类型：需要修改代码。**
>
> 修改：`app/main.py`

增加 import：

```python
from app.storage.factory import (
    build_artifact_storage,
)
```

在 `run_worker_command()` 中，构造 Worker 前增加：

```python
    artifact_storage = (
        build_artifact_storage()
    )
```

Worker 构造改为：

```python
    worker = JobWorker(
        worker_id=effective_worker_id,
        store=service.store,
        artifact_publisher=(
            artifact_storage.publisher
        ),
    )
```

启动输出增加非敏感 backend：

```python
            "artifact_backend": (
                settings.artifact_blob_backend
            ),
```

不要输出：

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
完整 S3 signed request
```

---

## 二十八、增加 Artifact Storage CLI

> **本节类型：需要修改代码。**
>
> 修改：`app/main.py`

增加：

```python
@app.command("check-artifact-storage")
def check_artifact_storage_command():
    """检查 Catalog 和当前 Blob backend 是否可用。"""

    bundle = build_artifact_storage()
    bundle.repository.initialize()
    for store in bundle.stores:
        store.ensure_ready()
    print(
        {
            "status": "ready",
            "selected_backend": (
                settings.artifact_blob_backend
            ),
            "registered_backends": [
                item.backend_name
                for item in bundle.stores
            ],
            "catalog_db": str(
                settings
                .artifact_catalog_db_path
            ),
        }
    )


@app.command("publish-job-artifacts")
def publish_job_artifacts_command(
    job_id: str,
):
    """
    发布历史 Job 当前 checkpoint 中登记的 Artifact。

    该命令不改变 Job 状态，只迁移 Artifact。
    """

    service = build_job_service()
    job = service.get(job_id)
    state = read_graph_state(
        job.thread_id
    )
    records = state.get(
        "artifact_records",
        [],
    )
    bundle = build_artifact_storage()
    report = bundle.publisher.publish(
        job=job,
        records=records,
    )
    print(report.model_dump())
```

还需要增加 import：

```python
from app.interaction.artifacts import (
    read_graph_state,
)
```

历史迁移命令是显式操作，不要在 API 的 GET `/artifacts` 中偷偷上传文件。

---

## 二十九、更新 `.env.example` 与 `.gitignore`

> **本节类型：需要修改配置文件。**

修改 `.env.example`：

```dotenv
JOB_STORE_BACKEND=sqlite

ARTIFACT_BLOB_BACKEND=local
ARTIFACT_CATALOG_DB_PATH=storage/artifacts.sqlite
ARTIFACT_LOCAL_STORE_DIR=storage/artifacts

# S3/MinIO 示例，不要提交真实凭据。
# ARTIFACT_S3_ENDPOINT_URL=http://127.0.0.1:9000
# ARTIFACT_S3_BUCKET=paper-reproduction-artifacts
# ARTIFACT_S3_REGION=us-east-1
# ARTIFACT_S3_PREFIX=copilot
# ARTIFACT_S3_FORCE_PATH_STYLE=true
# ARTIFACT_S3_AUTO_CREATE_BUCKET=false
```

凭据只写变量名：

```dotenv
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_SESSION_TOKEN=
```

修改 `.gitignore`：

```gitignore
# Phase 24 local Artifact Catalog / Blob backend
/storage/
```

这不会忽略源码目录 `app/storage/`。

---

## 三十、增加 JobStore Port 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_job_store_port.py`

完整代码：

```python
from app.job_runtime.ports import JobStore
from app.job_runtime.store import (
    SqliteJobStore,
)


def test_sqlite_store_implements_job_store(
    tmp_path,
) -> None:
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )

    assert isinstance(store, JobStore)
```

Protocol 测试只能证明方法存在。真正的事务语义仍由 Phase 22/23 Store tests 保证。
下一阶段增加 SQLAlchemy 后端时，必须让同一组 contract tests 对两个实现运行。

---

## 三十一、增加 Local Blob Store 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_local_blob_store.py`

完整代码：

```python
import hashlib

import pytest

from app.storage.errors import (
    ArtifactIntegrityError,
)
from app.storage.local_blob_store import (
    LocalBlobStore,
)


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_local_blob_put_is_idempotent(
    tmp_path,
) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"artifact")
    digest = _digest(b"artifact")
    store = LocalBlobStore(
        tmp_path / "blob-store"
    )

    first = store.put_file(
        object_key=f"sha256/{digest}",
        source_path=source,
        expected_sha256=digest,
        expected_size=8,
        media_type="application/octet-stream",
    )
    second = store.put_file(
        object_key=f"sha256/{digest}",
        source_path=source,
        expected_sha256=digest,
        expected_size=8,
        media_type="application/octet-stream",
    )

    assert first == second
    opened = store.open(
        f"sha256/{digest}"
    )
    try:
        assert opened.body.read() == b"artifact"
    finally:
        opened.body.close()


def test_local_blob_rejects_path_escape(
    tmp_path,
) -> None:
    store = LocalBlobStore(
        tmp_path / "blob-store"
    )

    with pytest.raises(
        ArtifactIntegrityError,
        match="object_key",
    ):
        store.stat("../outside")


def test_local_blob_rejects_source_hash_change(
    tmp_path,
) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"changed")
    store = LocalBlobStore(
        tmp_path / "blob-store"
    )

    with pytest.raises(
        ArtifactIntegrityError,
        match="SHA-256",
    ):
        store.put_file(
            object_key="sha256/expected",
            source_path=source,
            expected_sha256=_digest(b"old"),
            expected_size=len(b"changed"),
            media_type=(
                "application/octet-stream"
            ),
        )
```

---

## 三十二、增加 Artifact Repository 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_artifact_repository.py`

完整代码：

```python
from app.storage.artifact_repository import (
    SqliteArtifactRepository,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
)


def _descriptor(
    sha256: str,
    size: int,
) -> ArtifactDescriptor:
    return ArtifactDescriptor(
        artifact_id="artifact-1",
        run_id="run-1",
        layer="reports",
        relative_path="reports/final.md",
        media_type="text/markdown",
        sha256=sha256,
        size_bytes=size,
        producer_node="final_report",
        created_at=(
            "2026-07-30T00:00:00+00:00"
        ),
    )


def _blob(
    sha256: str,
    size: int,
    backend: str = "local",
) -> BlobStat:
    return BlobStat(
        backend=backend,
        object_key=f"sha256/{sha256}",
        size_bytes=size,
        sha256=sha256,
        etag="etag",
    )


def test_publish_same_version_is_idempotent(
    tmp_path,
) -> None:
    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    repository.initialize()

    first = repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )
    second = repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )

    assert first.revision == 1
    assert second.revision == 1


def test_new_content_increments_revision(
    tmp_path,
) -> None:
    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    repository.initialize()
    repository.publish(
        job_id="job-1",
        descriptor=_descriptor("a" * 64, 10),
        blob=_blob("a" * 64, 10),
    )

    current = repository.publish(
        job_id="job-1",
        descriptor=_descriptor("b" * 64, 20),
        blob=_blob("b" * 64, 20),
    )

    assert current.revision == 2
    assert (
        current.descriptor.sha256
        == "b" * 64
    )


def test_backend_migration_increments_revision(
    tmp_path,
) -> None:
    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    repository.initialize()
    descriptor = _descriptor(
        "a" * 64,
        10,
    )
    repository.publish(
        job_id="job-1",
        descriptor=descriptor,
        blob=_blob(
            "a" * 64,
            10,
            "local",
        ),
    )

    current = repository.publish(
        job_id="job-1",
        descriptor=descriptor,
        blob=_blob(
            "a" * 64,
            10,
            "s3",
        ),
    )

    assert current.revision == 2
    assert current.backend == "s3"
```

---

## 三十三、增加 Publisher 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_artifact_publisher.py`

完整代码：

```python
from app.job_runtime.schemas import (
    JobRequest,
)
from app.job_runtime.store import (
    SqliteJobStore,
)
from app.storage.artifact_repository import (
    SqliteArtifactRepository,
)
from app.storage.local_blob_store import (
    LocalBlobStore,
)
from app.storage.publisher import (
    ArtifactPublisher,
)
from app.tools.artifact_tools import (
    build_artifact_record,
)


def test_publisher_survives_source_removal(
    tmp_path,
) -> None:
    run_root = tmp_path / "runs" / "run-1"
    report = run_root / "reports/final.md"
    report.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    report.write_text(
        "final report",
        encoding="utf-8",
    )

    state = {
        "run_id": "run-1",
        "run_dir": str(run_root),
    }
    record = build_artifact_record(
        state=state,
        path=report,
        producer_node="test",
    )

    job_store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    job_store.initialize()
    job, _ = job_store.submit(
        job_id="job-1",
        idempotency_key="submit-1",
        thread_id="thread-1",
        run_id="run-1",
        run_dir=str(run_root),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        max_attempts=3,
    )

    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    blob_store = LocalBlobStore(
        tmp_path / "blob-store"
    )
    publisher = ArtifactPublisher(
        repository=repository,
        blob_store=blob_store,
    )

    first = publisher.publish(
        job=job,
        records=[record],
    )
    second = publisher.publish(
        job=job,
        records=[record],
    )

    assert first.published_count == 1
    assert second.reused_count == 1

    published = repository.find(
        job_id=job.job_id,
        artifact_id=record.artifact_id,
    )
    assert published is not None
    report.unlink()

    opened = blob_store.open(
        published.object_key
    )
    try:
        assert (
            opened.body.read()
            == b"final report"
        )
    finally:
        opened.body.close()
```

---

## 三十四、增加 Worker 发布顺序测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_worker_artifact_publication.py`

完整代码：

```python
from app.job_runtime.schemas import (
    JobExecutionOutcome,
    JobRequest,
)
from app.job_runtime.store import (
    SqliteJobStore,
)
from app.job_runtime.worker import JobWorker
from app.storage.errors import (
    ArtifactBackendUnavailable,
)
from app.storage.schemas import (
    ArtifactPublicationReport,
)


class OutcomeRunner:
    """避免单测依赖另一个 test module 的私有 helper。"""

    def __init__(self, outcome):
        self.outcome = outcome

    def execute(self, claim, heartbeat):
        del claim
        heartbeat.raise_if_unhealthy()
        return self.outcome


def _queued_store(tmp_path):
    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    store.submit(
        job_id="job-worker",
        idempotency_key="submit-worker",
        thread_id="thread-worker",
        run_id="run-worker",
        run_dir=str(
            tmp_path / "runs/run-worker"
        ),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        max_attempts=3,
    )
    return store


class RecordingPublisher:
    def __init__(self):
        self.calls = 0

    def publish(
        self,
        *,
        job,
        records,
        ensure_active,
    ):
        self.calls += 1
        ensure_active()
        assert list(records) == []
        return ArtifactPublicationReport(
            artifact_count=0,
            published_count=0,
            reused_count=0,
            backend="local",
        )


class UnavailablePublisher:
    def publish(self, **kwargs):
        raise ArtifactBackendUnavailable(
            "controlled outage"
        )


def test_worker_publishes_before_succeeded(
    tmp_path,
) -> None:
    store = _queued_store(tmp_path)
    publisher = RecordingPublisher()
    worker = JobWorker(
        worker_id="worker-storage",
        store=store,
        runner=OutcomeRunner(
            JobExecutionOutcome(
                status="succeeded",
                result={
                    "final_status": "succeeded"
                },
            )
        ),
        artifact_publisher=publisher,
        lease_seconds=1.0,
        heartbeat_seconds=0.1,
    )

    worker.run_once()

    record = store.get("job-worker")
    assert publisher.calls == 1
    assert record.status == "succeeded"
    assert (
        record.result[
            "artifact_publication"
        ]["status"]
        == "completed"
    )


def test_temporary_storage_error_requeues(
    tmp_path,
) -> None:
    store = _queued_store(tmp_path)
    worker = JobWorker(
        worker_id="worker-storage",
        store=store,
        runner=OutcomeRunner(
            JobExecutionOutcome(
                status="succeeded",
                result={},
            )
        ),
        artifact_publisher=(
            UnavailablePublisher()
        ),
        lease_seconds=1.0,
        heartbeat_seconds=0.1,
    )

    worker.run_once()

    record = store.get("job-worker")
    assert record.status == "queued"
    assert (
        record.error["type"]
        == "ArtifactBackendUnavailable"
    )
```

测试 helper 已经完整写在本文件中，避免 pytest 收集顺序、包路径或其他测试文件
重构影响本测试。不要为了复用这两个小 helper 而把它们放进生产源码。

---

## 三十五、增加 Published Catalog 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_published_artifact_catalog.py`

完整代码：

```python
from app.storage.artifact_repository import (
    SqliteArtifactRepository,
)
from app.storage.catalog import (
    BlobStoreRegistry,
    PublishedArtifactCatalog,
)
from app.storage.local_blob_store import (
    LocalBlobStore,
)
from app.storage.publisher import (
    ArtifactPublisher,
)
from app.tools.artifact_tools import (
    build_artifact_record,
)


def test_catalog_lists_and_opens_published_blob(
    tmp_path,
) -> None:
    run_root = tmp_path / "runs/run-catalog"
    source = run_root / "reports/final.md"
    source.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    source.write_text(
        "catalog artifact",
        encoding="utf-8",
    )

    store = SqliteJobStore(
        tmp_path / "jobs.sqlite"
    )
    store.initialize()
    job, _ = store.submit(
        job_id="job-catalog",
        idempotency_key="catalog-submit",
        thread_id="thread-catalog",
        run_id="run-catalog",
        run_dir=str(run_root),
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        max_attempts=3,
    )
    record = build_artifact_record(
        state={
            "run_id": job.run_id,
            "run_dir": job.run_dir,
        },
        path=source,
        producer_node="test",
    )

    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    blob_store = LocalBlobStore(
        tmp_path / "blob-store"
    )
    ArtifactPublisher(
        repository=repository,
        blob_store=blob_store,
    ).publish(
        job=job,
        records=[record],
    )
    source.unlink()

    catalog = PublishedArtifactCatalog(
        repository=repository,
        registry=BlobStoreRegistry(
            [blob_store]
        ),
    )
    views = catalog.list_views(job)
    assert [
        item.artifact_id
        for item in views
    ] == [record.artifact_id]

    opened = catalog.open(
        job=job,
        artifact_id=record.artifact_id,
    )
    try:
        assert (
            opened.blob.body.read()
            == b"catalog artifact"
        )
    finally:
        opened.blob.body.close()
```

该测试与 Repository 单测的区别是：它经过 Catalog 的 Job/run 身份校验和 backend
registry，再真正打开 Blob。下一节继续验证同一组合经过 HTTP 层也能工作。

---

## 三十六、增加 Artifact Storage API 测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_artifact_storage_api.py`

完整代码：

```python
from fastapi.testclient import TestClient

from app.api.app import create_api_app
from app.config import settings
from app.job_runtime.schemas import (
    JobRequest,
)
from app.job_runtime.service import JobService
from app.job_runtime.store import (
    SqliteJobStore,
)
from app.storage.artifact_repository import (
    SqliteArtifactRepository,
)
from app.storage.catalog import (
    BlobStoreRegistry,
    PublishedArtifactCatalog,
)
from app.storage.local_blob_store import (
    LocalBlobStore,
)
from app.storage.publisher import (
    ArtifactPublisher,
)
from app.tools.artifact_tools import (
    build_artifact_record,
)


def test_api_downloads_published_blob_after_source_deleted(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "runs_dir",
        tmp_path / "runs",
    )

    job_service = JobService(
        SqliteJobStore(
            tmp_path / "jobs.sqlite"
        )
    )
    job, _ = job_service.submit(
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id="local",
        ),
        thread_id="artifact-api",
        idempotency_key="artifact-api",
    )
    # JobService 生成自己的 run_dir，所以测试文件要移动到该目录。
    actual_source = (
        tmp_path
        / "runs"
        / job.run_id
        / "reports"
        / "final.md"
    )
    actual_source.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    actual_source.write_text(
        "durable artifact",
        encoding="utf-8",
    )
    record = build_artifact_record(
        state={
            "run_id": job.run_id,
            "run_dir": job.run_dir,
        },
        path=actual_source,
        producer_node="test",
    )

    repository = SqliteArtifactRepository(
        tmp_path / "artifacts.sqlite"
    )
    blob_store = LocalBlobStore(
        tmp_path / "blob-store"
    )
    ArtifactPublisher(
        repository=repository,
        blob_store=blob_store,
    ).publish(
        job=job,
        records=[record],
    )
    catalog = PublishedArtifactCatalog(
        repository=repository,
        registry=BlobStoreRegistry(
            [blob_store]
        ),
    )
    actual_source.unlink()

    app = create_api_app(
        job_service=job_service,
        artifact_catalog=catalog,
        api_token="test-token",
    )
    with TestClient(app) as client:
        response = client.get(
            (
                f"/v1/jobs/{job.job_id}"
                "/artifacts/"
                f"{record.artifact_id}"
                "/content"
            ),
            headers={
                "Authorization": (
                    "Bearer test-token"
                )
            },
        )

    assert response.status_code == 200
    assert response.content == (
        b"durable artifact"
    )
    assert "object_key" not in (
        response.headers
    )
```

测试只在 `JobService` 生成的真实 `job.run_id` 目录中创建源文件，不要先创建一个
不会被使用的假 run 目录。

---

## 三十七、增加 S3 Adapter 单元测试

> **本节类型：需要新增测试代码。**
>
> 新增：`tests/test_s3_blob_store.py`

S3 adapter 单测不要连接真实网络。使用最小 fake client：

```python
import hashlib
from io import BytesIO

import pytest

pytest.importorskip("boto3")

from botocore.exceptions import (
    EndpointConnectionError,
)
from app.storage.errors import (
    ArtifactBackendUnavailable,
)
from app.storage.s3_blob_store import (
    S3BlobStore,
)


class FakeS3:
    def __init__(self):
        self.objects = {}

    def head_bucket(self, *, Bucket):
        return {}

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            error = {
                "Error": {"Code": "404"},
                "ResponseMetadata": {
                    "HTTPStatusCode": 404
                },
            }
            from botocore.exceptions import (
                ClientError,
            )

            raise ClientError(
                error,
                "HeadObject",
            )
        value = self.objects[Key]
        return {
            "ContentLength": len(
                value["body"]
            ),
            "Metadata": value["metadata"],
            "ETag": '"fake-etag"',
        }

    def upload_file(
        self,
        filename,
        bucket,
        key,
        ExtraArgs,
    ):
        with open(filename, "rb") as file_obj:
            body = file_obj.read()
        self.objects[key] = {
            "body": body,
            "metadata": ExtraArgs["Metadata"],
        }

    def get_object(self, *, Bucket, Key):
        value = self.objects[Key]
        return {
            "Body": BytesIO(value["body"]),
            "ContentLength": len(
                value["body"]
            ),
            "Metadata": value["metadata"],
            "ETag": '"fake-etag"',
        }


class UnavailableS3(FakeS3):
    def head_object(self, *, Bucket, Key):
        del Bucket, Key
        raise EndpointConnectionError(
            endpoint_url=(
                "http://127.0.0.1:1"
            )
        )


def _store(client) -> S3BlobStore:
    return S3BlobStore(
        bucket="test",
        prefix="copilot",
        endpoint_url=None,
        region="us-east-1",
        force_path_style=True,
        auto_create_bucket=False,
        connect_timeout=1,
        read_timeout=1,
        max_attempts=1,
        client=client,
    )


def test_s3_store_round_trip(
    tmp_path,
) -> None:
    source = tmp_path / "artifact.bin"
    source.write_bytes(b"s3 artifact")

    digest = hashlib.sha256(
        b"s3 artifact"
    ).hexdigest()
    fake = FakeS3()
    store = _store(fake)

    stored = store.put_file(
        object_key=f"sha256/{digest}",
        source_path=source,
        expected_sha256=digest,
        expected_size=len(b"s3 artifact"),
        media_type=(
            "application/octet-stream"
        ),
    )
    opened = store.open(
        f"sha256/{digest}"
    )
    try:
        assert (
            opened.body.read()
            == b"s3 artifact"
        )
    finally:
        opened.body.close()

    assert stored.sha256 == digest
    assert (
        "copilot/sha256/"
        in next(iter(fake.objects))
    )


def test_s3_network_error_is_retryable() -> None:
    store = _store(UnavailableS3())

    with pytest.raises(
        ArtifactBackendUnavailable
    ):
        store.stat("sha256/missing")
```

真实 MinIO 连接放到手工验收，不进入普通离线测试。

---

## 三十八、完整测试命令

> **本节类型：运行验证，不修改项目代码。**

先检查 Phase 23 API 不再阻塞：

```bash
python -m pytest \
  tests/test_interaction_api.py \
  tests/test_interaction_sse.py \
  -q
```

运行本阶段测试：

```bash
python -m pytest \
  tests/test_job_store_port.py \
  tests/test_local_blob_store.py \
  tests/test_artifact_repository.py \
  tests/test_artifact_publisher.py \
  tests/test_worker_artifact_publication.py \
  tests/test_published_artifact_catalog.py \
  tests/test_s3_blob_store.py \
  tests/test_artifact_storage_api.py \
  -q
```

运行 Phase 22/23 回归：

```bash
python -m pytest \
  tests/test_job_store.py \
  tests/test_job_heartbeat.py \
  tests/test_job_process_reconcile.py \
  tests/test_job_graph_runner.py \
  tests/test_job_worker.py \
  tests/test_job_cli.py \
  tests/test_job_durable_resume.py \
  tests/test_job_store_interaction_semantics.py \
  tests/test_interaction_policy.py \
  tests/test_interaction_artifacts.py \
  tests/test_interaction_api.py \
  tests/test_interaction_sse.py \
  -q
```

静态检查：

```bash
python -m compileall \
  app/storage \
  app/job_runtime \
  app/interaction \
  app/api

python -m ruff check \
  --select E4,E7,E9,F \
  app/storage \
  app/job_runtime \
  app/interaction \
  app/api \
  tests/test_job_store_port.py \
  tests/test_local_blob_store.py \
  tests/test_artifact_repository.py \
  tests/test_artifact_publisher.py \
  tests/test_worker_artifact_publication.py \
  tests/test_published_artifact_catalog.py \
  tests/test_s3_blob_store.py \
  tests/test_artifact_storage_api.py
```

最后运行全量离线回归：

```bash
python -m pytest -m "not provider" -q
```

---

## 三十九、本地后端手工验收

> **本节类型：运行验证，不修改项目代码。**

先不启动 MinIO，验证 contract：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent

export ALLOWED_ROOT=/data/tianshaoqi24
export RUNS_DIR=/data/tianshaoqi24/agent/paper_reproduction_copilot/runs
export JOB_DB_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/jobs/runtime.sqlite
export CHECKPOINT_DB_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/checkpoints/langgraph.sqlite

export JOB_STORE_BACKEND=sqlite
export ARTIFACT_BLOB_BACKEND=local
export ARTIFACT_CATALOG_DB_PATH=/data/tianshaoqi24/agent/paper_reproduction_copilot/storage/artifacts.sqlite
export ARTIFACT_LOCAL_STORE_DIR=/data/tianshaoqi24/agent/paper_reproduction_copilot/storage/artifacts
```

检查：

```bash
python -m app.main check-artifact-storage
```

应看到：

```text
selected_backend = local
registered_backends = ["local"]
status = ready
```

选择一个已有 Job：

```bash
python -m app.main list-jobs --limit 10
export JOB_ID=job_实际值
```

发布：

```bash
python -m app.main publish-job-artifacts \
  "$JOB_ID"
```

再次执行，`reused_count` 应增加，不应重复生成 revision。

---

## 四十、启动本机 MinIO

> **本节类型：运行验证，不修改项目代码。**

MinIO 二进制和数据都放在：

```text
/data/tianshaoqi24/
```

假设可执行文件已经位于：

```text
/data/tianshaoqi24/bin/minio
```

创建数据目录：

```bash
mkdir -p /data/tianshaoqi24/minio-data
```

设置本次验收凭据，不要写入仓库：

```bash
export MINIO_ROOT_USER='phase24-local-admin'
export MINIO_ROOT_PASSWORD='替换为至少32位随机密码'
```

启动：

```bash
/data/tianshaoqi24/bin/minio server \
  /data/tianshaoqi24/minio-data \
  --address 127.0.0.1:9000 \
  --console-address 127.0.0.1:9001
```

这个终端保持运行。

如果本机没有 MinIO，不要在教程实现过程中自动下载未知二进制。先从 MinIO 官方
渠道获取并核对校验值。

---

## 四十一、配置 S3/MinIO 后端

> **本节类型：运行验证，不修改项目代码。**

在 API 和 Worker 的每个终端中设置完全相同的变量：

```bash
export ARTIFACT_BLOB_BACKEND=s3
export ARTIFACT_S3_ENDPOINT_URL=http://127.0.0.1:9000
export ARTIFACT_S3_BUCKET=paper-reproduction-artifacts
export ARTIFACT_S3_REGION=us-east-1
export ARTIFACT_S3_PREFIX=phase24
export ARTIFACT_S3_FORCE_PATH_STYLE=true
export ARTIFACT_S3_AUTO_CREATE_BUCKET=true

export AWS_ACCESS_KEY_ID="$MINIO_ROOT_USER"
export AWS_SECRET_ACCESS_KEY="$MINIO_ROOT_PASSWORD"
```

如果不同终端没有 `MINIO_ROOT_USER`，直接把同一个 ASCII 值重新 export。不要使用
中文弯引号。

检查：

```bash
python -m app.main check-artifact-storage
```

应看到：

```text
selected_backend = s3
registered_backends = ["local", "s3"]
status = ready
```

手工验收结束后，生产配置应把：

```text
ARTIFACT_S3_AUTO_CREATE_BUCKET=false
```

bucket 由基础设施管理。

---

## 四十二、运行 PSTNet 异步闭环

> **本节类型：运行验证，不修改项目代码。**

本阶段继续使用：

```text
论文：
/data/tianshaoqi24/agent/paper_reproduction_copilot/
pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf

仓库：
/data/tianshaoqi24/PST-Convolution-main/
```

终端 A 启动 API：

```bash
export AGENT_API_TOKEN='替换为本次验收使用的高熵随机值'

python -m app.main serve-api \
  --host 127.0.0.1 \
  --port 8000
```

终端 B 使用完全相同的 Job、Checkpoint、S3 和 AWS 环境变量启动 Worker：

```bash
python -m app.main run-worker \
  --worker-id phase24-storage-worker
```

终端 C 设置 API 地址和与终端 A 完全相同的 token：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
conda activate agent

export API_BASE=http://127.0.0.1:8000
export AGENT_API_TOKEN='终端A使用的同一个高熵随机值'

mkdir -p \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24
```

先验证 API：

```bash
curl --fail --silent \
  "$API_BASE/healthz"
```

然后提交 Job。请求必须使用当前真实 execution profile：

```bash
curl --fail-with-body --silent --show-error \
  --request POST \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --header "Idempotency-Key: phase24-pstnet-submit-001" \
  --header "Content-Type: application/json" \
  --data '{
    "paper_path": "/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf",
    "repo_path": "/data/tianshaoqi24/PST-Convolution-main/",
    "thread_id": "phase24-pstnet-001",
    "experiment_goal": "复现论文 main result",
    "execution_profile_id": "pstnet-local-supervised"
  }' \
  --output \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/job_submit.json \
  "$API_BASE/v1/jobs"
```

查看响应：

```bash
python -m json.tool \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/job_submit.json
```

从响应提取真实 `JOB_ID`：

```bash
export JOB_ID="$(
  python -c \
  'import json; print(json.load(open("/data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/job_submit.json", encoding="utf-8"))["job"]["job_id"])'
)"

printf '%s\n' "$JOB_ID"
```

轮询 Job，直到它进入 `waiting_for_input` 或终态：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --output \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/job_current.json \
  "$API_BASE/v1/jobs/$JOB_ID"

python -m json.tool \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/job_current.json
```

列出已经发布的 Artifact：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --output \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/artifacts.json \
  "$API_BASE/v1/jobs/$JOB_ID/artifacts"

python -m json.tool \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/artifacts.json
```

Job 到达 command selection 后：

1. `status` 必须是 `waiting_for_input`；
2. `result.artifact_publication.status` 在内部 Job 记录中应是 `completed`；
3. Artifact Catalog 应包含 `planning/command_selection_input.json`；
4. API 下载应来自 S3 backend；
5. resume 后下一批 Artifact 可以继续发布；
6. 最终报告发布后 Job 才进入 `succeeded`。

Command Selection、Action Approval 等 Decision 请求沿用 Phase 23 的
`expected_job_version + expected_wait_generation + Idempotency-Key` 协议。每次恢复
前必须重新 GET Job，不要复用旧 version；本阶段只改变 Artifact 存储，不改变审批
协议。

---

## 四十三、证明 API 不再依赖本地源文件

> **本节类型：运行验证，不修改项目代码。**

只对已经结束的 Job 操作，选择：

```text
reports/final_report.md
```

先从上一节保存的响应中提取 `RUN_ID` 和该文件的 `ARTIFACT_ID`：

```bash
export RUN_ID="$(
  python -c \
  'import json; print(json.load(open("/data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/job_current.json", encoding="utf-8"))["run_id"])'
)"

export RUN_DIR="/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/$RUN_ID"

export ARTIFACT_ID="$(
  python -c \
  'import json; items=json.load(open("/data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/artifacts.json", encoding="utf-8"))["items"]; print(next(item["artifact_id"] for item in items if item["relative_path"] == "reports/final_report.md"))'
)"

printf 'RUN_ID=%s\nRUN_DIR=%s\nARTIFACT_ID=%s\n' \
  "$RUN_ID" \
  "$RUN_DIR" \
  "$ARTIFACT_ID"
```

如果 Job 在上一节之后又继续运行，先重新 GET Job 和 Artifact list，覆盖
`job_current.json` 与 `artifacts.json`，再提取变量。`next(...)` 报
`StopIteration` 表示最终报告尚未发布，不能随便选另一个 Artifact 代替。

先通过 API 下载一份：

```bash
curl --fail \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --output \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/final_report.remote.md \
  "$API_BASE/v1/jobs/$JOB_ID/artifacts/$ARTIFACT_ID/content"
```

确认源文件存在：

```bash
test -f "$RUN_DIR/reports/final_report.md"
```

把本地源文件临时改名，不要删除，并注册异常恢复：

```bash
export FINAL_REPORT_BACKUP="$RUN_DIR/reports/final_report.md.local-backup"

mv \
  "$RUN_DIR/reports/final_report.md" \
  "$FINAL_REPORT_BACKUP"

trap 'if test -f "$FINAL_REPORT_BACKUP"; then mv "$FINAL_REPORT_BACKUP" "$RUN_DIR/reports/final_report.md"; fi' EXIT
```

再次通过 API 下载：

```bash
curl --fail \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --output \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/final_report.remote-without-source.md \
  "$API_BASE/v1/jobs/$JOB_ID/artifacts/$ARTIFACT_ID/content"
```

比较：

```bash
sha256sum \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/final_report.remote.md \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/final_report.remote-without-source.md
```

最后立即恢复：

```bash
mv \
  "$FINAL_REPORT_BACKUP" \
  "$RUN_DIR/reports/final_report.md"

trap - EXIT
```

两次 SHA-256 应一致。这证明 API 使用持久 Blob，而不是 run workspace。

---

## 四十四、验证 MinIO 故障恢复

> **本节类型：运行验证，不修改项目代码。**

不要在持续运行的 Worker 上长时间停止 MinIO。否则 Worker 可能连续 retry，快速耗尽
`max_attempts`。使用一个独立 Job 和 `--once` 做确定性测试。

先在终端 B 用 `Ctrl+C` 停止持续 Worker。终端 C 提交一个新的 outage Job：

```bash
curl --fail-with-body --silent --show-error \
  --request POST \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --header "Idempotency-Key: phase24-minio-outage-submit-001" \
  --header "Content-Type: application/json" \
  --data '{
    "paper_path": "/data/tianshaoqi24/agent/paper_reproduction_copilot/pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf",
    "repo_path": "/data/tianshaoqi24/PST-Convolution-main/",
    "thread_id": "phase24-minio-outage-001",
    "experiment_goal": "验证 Artifact storage 故障恢复",
    "execution_profile_id": "pstnet-local-supervised"
  }' \
  --output \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/outage_submit.json \
  "$API_BASE/v1/jobs"

export OUTAGE_JOB_ID="$(
  python -c \
  'import json; print(json.load(open("/data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/outage_submit.json", encoding="utf-8"))["job"]["job_id"])'
)"
```

在 MinIO 终端按 `Ctrl+C`，确认 9000 端口已经不可用：

```bash
curl --silent \
  --output /dev/null \
  --write-out '%{http_code}\n' \
  http://127.0.0.1:9000/minio/health/live
```

此时应得到连接失败或 `000`。在终端 B 只处理一次：

```bash
python -m app.main run-worker \
  --worker-id phase24-outage-worker-1 \
  --once
```

Graph 会运行到第一个 command selection interrupt，但 Artifact 发布会因 MinIO
不可用而失败。查询：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  --output \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/outage_after_failure.json \
  "$API_BASE/v1/jobs/$OUTAGE_JOB_ID"

python -m json.tool \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/manual_acceptance/phase24/outage_after_failure.json
```

必须看到：

```text
status = queued
attempt_count = 1
error.type = ArtifactBackendUnavailable
```

查看 Event：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$OUTAGE_JOB_ID/events?after=0&limit=100"
```

其中应有 `job_retry_scheduled`，不能有 `job_succeeded`。

使用第四十节的同一命令重启 MinIO。等到 storage readiness 恢复：

```bash
python -m app.main check-artifact-storage
sleep 2
```

再次只处理一次：

```bash
python -m app.main run-worker \
  --worker-id phase24-outage-worker-2 \
  --once
```

再次查询 Job 和 Artifact：

```bash
curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$OUTAGE_JOB_ID"

curl --fail --silent \
  --header "Authorization: Bearer $AGENT_API_TOKEN" \
  "$API_BASE/v1/jobs/$OUTAGE_JOB_ID/artifacts"
```

这次必须看到：

```text
status = waiting_for_input
interrupt_nodes = ["command_selection"]
Artifact list 非空
```

第二次 Worker 应读取第一次留下的 interrupt checkpoint，Publisher 复用已存在的 Blob
或补齐缺失 Blob，再登记 Catalog；不应从论文解析起点重新运行 Graph。

不能出现：

```text
S3 不可用
但 Job 已显示 succeeded
```

第一个 interrupt 发生在命令选择之前，因此这个故障测试不会执行训练命令。对于已到
terminal checkpoint 的 Job，快速恢复分支同样必须返回 ArtifactRecord 给
Publisher，不能重新执行已经完成的训练。

---

## 四十五、直接检查 Artifact Catalog

> **本节类型：调试验证，不修改项目代码。**

```bash
python - <<'PY'
import sqlite3

path = (
    "/data/tianshaoqi24/agent/"
    "paper_reproduction_copilot/"
    "storage/artifacts.sqlite"
)
connection = sqlite3.connect(path)
connection.row_factory = sqlite3.Row

print("HEADS")
for row in connection.execute(
    """
    SELECT
        artifact_id,
        job_id,
        relative_path,
        current_sha256,
        current_backend,
        revision
    FROM artifact_heads
    ORDER BY updated_at DESC
    LIMIT 30
    """
):
    print(dict(row))

print("VERSIONS")
for row in connection.execute(
    """
    SELECT
        artifact_id,
        sha256,
        backend,
        object_key,
        size_bytes
    FROM artifact_versions
    ORDER BY published_at DESC
    LIMIT 30
    """
):
    print(dict(row))
PY
```

Catalog 中不得出现：

```text
absolute_path
AWS secret
Bearer token
完整 Prompt
```

---

## 四十六、常见问题排查

> **本节类型：故障排查，不修改项目代码。**

### 46.1 Phase 23 API 测试一直卡住

检查：

```bash
python -m pip show \
  fastapi starlette httpx httpx2
```

当前 Starlette TestClient 需要 `httpx2`。安装后重新运行，不要把阻塞误判成 SQLite
死锁。

### 46.2 `ModuleNotFoundError: boto3`

执行：

```bash
python -m pip install -e ".[storage-s3]"
```

只使用 local backend 时不需要导入 S3 adapter。

### 46.3 `ARTIFACT_BACKEND_UNAVAILABLE`

检查：

```text
MinIO 是否运行
endpoint 是否是 127.0.0.1:9000
API 与 Worker 是否使用同一 bucket/prefix
AWS_ACCESS_KEY_ID 是否一致
bucket 是否存在
是否把 console 端口 9001 当成 S3 端口
```

### 46.4 `AccessDenied`

不要把 403 当作对象不存在。缺少 `ListBucket` 时 S3 对不存在对象也可能返回 403。
检查 IAM policy 和 bucket policy。

### 46.5 Artifact list 为空

Phase 24 后 API 默认只读持久 Catalog。历史 Job 需要：

```bash
python -m app.main publish-job-artifacts "$JOB_ID"
```

不要在 GET 请求中自动迁移。

### 46.6 上传成功但 Catalog 没有记录

可能是 Blob first 后进程崩溃。重新执行发布即可。内容寻址对象会被复用。

### 46.7 Catalog 有记录但 Blob 不存在

这表示：

```text
对象被外部删除
bucket 生命周期规则提前清理
配置指向错误 bucket/prefix
```

API 应返回完整性或不存在错误，不能回退到任意本地路径。

### 46.8 revision 不断增加

检查：

```text
是否每次发布都切换 backend
同一路径文件是否被时间戳等非确定字段重写
ArtifactRecord.sha256 是否稳定
prefix 变化是否生成了不同 object key
```

相同 sha256 + 相同 backend 的重试不应增加 revision。

### 46.9 Worker 因上传失败重新执行训练

检查 `GraphJobRunner` 的：

```text
terminal checkpoint fast path
artifact_records 返回
```

Job retry 后应直接读取 terminal checkpoint，再次发布 Artifact，而不是重新 invoke
Graph。

### 46.10 API 下载占用大量内存

确认使用：

```text
StreamingResponse
body.read(chunk_bytes)
finally body.close()
```

不要使用：

```python
content = body.read()
return Response(content)
```

---

## 四十七、本阶段 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 47.1 Hexagonal Architecture

```text
业务层 -> Port
基础设施 -> Adapter
composition root -> 选择 Adapter
```

Protocol 的价值不是“看起来抽象”，而是让业务语义可以通过 contract test 固定。

### 47.2 Workspace 与 Durable Artifact

Agent 执行需要可变工作区；用户和其他服务需要不可变、可寻址的产物。二者生命周期
不同，不能共用一个存储概念。

### 47.3 Content-addressed Storage

内容哈希同时提供：

```text
去重
幂等
完整性
稳定 object key
```

但它不自动提供访问控制。授权仍绑定 Job 和 Artifact metadata。

### 47.4 Metadata/Blob 分离

```text
Catalog：
    小、结构化、可事务查询。

Blob：
    大、不可变、适合对象存储。
```

数据库不应承担所有大文件，S3 也不应承担 Job 状态事务。

### 47.5 Crash Consistency

无法跨 SQLite 和 S3 建立普通 ACID 事务，因此使用：

```text
可重试顺序
幂等 object key
metadata 后置
orphan 可回收
```

这是 Saga/补偿思维，而不是伪装成分布式事务。

### 47.6 Read-after-write 与最终一致

Publisher 上传后执行 `HEAD` 校验，再写 Catalog。兼容后端如果存在可见性延迟，
应把“上传后暂不可见”归类为临时错误并重试。

### 47.7 Fencing 仍然重要

对象存储幂等不能替代 Job claim token。旧 Worker 即使上传了相同 Blob，也不能
覆盖新 Worker 的 Job 状态。

### 47.8 Backpressure

同步发布会延长 Job 持有 lease 的时间，但语义清晰。未来 Artifact 很大时可改为
Outbox + 独立 Publisher Worker；在此之前不要先引入消息队列。

---

## 四十八、安全边界复核

> **本节类型：安全清单，不修改项目代码。**

本阶段必须保持：

- run workspace 与 Blob root 分离；
- object key 不包含绝对路径；
- object key 拒绝 `..` 和绝对路径；
- Publisher 重新校验 run 边界；
- Publisher 重新校验 size 和 SHA-256；
- Catalog 不保存 absolute_path；
- Catalog 不保存 AWS/MinIO secret；
- Blob first、metadata second；
- S3 ETag 不当作 SHA-256；
- S3 metadata 缺少 SHA-256 时 fail closed；
- S3 403 不当作普通 not found；
- 远程 5xx/timeout 才标记 retryable；
- 完整性错误不自动 retry；
- Publisher 在 heartbeat context 内运行；
- Job 终态仍由 claim token fencing；
- API 不返回 bucket 和 object key；
- API 以流式方式读取并关闭 body；
- bucket 默认私有；
- 生产默认不自动创建 bucket；
- 本阶段不自动删除本地 run；
- 历史迁移必须显式执行；
- API GET 不产生上传副作用；
- 测试 fake S3 不连接公网；
- MinIO 数据目录位于 `/data/tianshaoqi24/`；
- 不把本机 MinIO root 凭据提交到 Git。

---

## 四十九、完成标准

> **本节类型：最终验收清单，不修改项目代码。**

只有以下全部满足，才算 Phase 24 完成：

- Phase 23 API 测试不再阻塞；
- SqliteJobStore 满足 JobStore Protocol；
- Service/Worker/Heartbeat/Reconciler 不再注解具体 SQLite 类；
- JobStore factory 成为唯一 composition root；
- Local Blob Store contract 通过；
- S3 fake client contract 通过；
- Blob object key 使用 SHA-256；
- Local path escape 被拒绝；
- 待发布源文件 hash 变化被拒绝；
- Artifact Catalog 不含 absolute_path；
- 同版本重复发布 revision 不变；
- 内容变化 revision 增加；
- backend 迁移 revision 增加；
- Worker 在 heartbeat 内发布；
- 发布成功后才 mark waiting/succeeded；
- 临时 S3 故障使 Job retry；
- 完整性故障使 Job failed；
- terminal checkpoint retry 不重跑 Graph；
- Published Catalog 能列出 Artifact；
- API 能流式下载 Local Blob；
- API 能流式下载 MinIO Blob；
- 删除本地源文件后远程下载仍成功；
- API 不返回 bucket/object key；
- 历史 Job 可显式迁移；
- 重复历史迁移不会重复上传；
- MinIO 停止与恢复测试通过；
- Phase 22/23 回归通过；
- 全量离线回归通过；
- PSTNet 至少在一个 interrupt boundary 发布 Artifact 到 MinIO；
- 最终 run Manifest 和 Artifact Catalog 查询结果被保留。

---

## 五十、下一阶段建议

> **本节类型：路线说明，不修改项目代码。**

Phase 24 完成后，下一阶段最值得做的是：

```text
Phase 25：
Relational JobRepository、Shared Checkpoint 与 Distributed Worker Claim
```

推荐内容：

```text
SQLAlchemy 2.x repository
Alembic migration
PostgreSQL 或 MySQL 单一目标实现
SELECT ... FOR UPDATE SKIP LOCKED
数据库时间作为 lease 时间源
connection pool 与 health check
Job/Event/Artifact metadata 同库事务边界
LangGraph 数据库 Checkpointer
SQLite -> relational migration CLI
双后端 contract tests
多进程/多主机 claim 验证
```

仍然不必立即引入 Redis/MQ。只有关系库 claim 已经成为实际吞吐瓶颈，或者需要按
GPU、队列优先级、租户和地域路由时，再设计消息分发层。

---

## 五十一、阶段结论

> **本节类型：总结，不修改项目代码。**

Phase 24 不是简单“把文件上传到 MinIO”，而是建立完整的 Artifact 提交协议：

```text
可变工作区
    -> immutable ArtifactRecord
    -> content-addressed Blob
    -> versioned Catalog head
    -> authenticated API stream
```

完成后，本地 run 文件系统从“Artifact 的唯一持久化事实”降级为“当前 Worker 的
执行工作区”。在 API 与 Worker 能访问同一 SQLite Catalog 的前提下，Artifact Blob
已经可以跨进程读取；跨主机共享 Catalog、Job 状态和 Checkpoint 则由 Phase 25
完成。
