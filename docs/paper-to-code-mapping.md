# 论文 → 代码检索映射机制

> 本文档记录论文复现 Copilot（LangGraph agent）如何把论文中的方法描述、数据集、实验设置等概念检索映射到目标代码库的实体（文件 / 符号 / 配置）上。
>
> 设计核心一句话：**检索是确定性的，LLM 是检索结果的"消费者"而非"引擎"** —— 所有需要"猜"的地方交给 LLM，所有能"算"的地方都用确定性代码实现。

---

## 0. 整体流水线

```
paper_reader
    │  解析 PDF → 结构化方法描述 / 数据集 / 实验设置
    ▼
method_extractor
    │  抽取核心方法、数据管线、训练配置、评测指标、消融开关（5 类 target 的素材）
    ▼
repo_scan
    │  扫描仓库 → AST 符号索引 / import 图 / CLI 配置 / BM25 倒排
    ▼
mapping_alias_resolver
    │  同义词 / 命名变体归并（把论文术语对齐到代码术语）
    ▼
code_search
    │  8 通道混合检索 + RRF 融合 → 候选代码片段 + 证据
    ▼
mapping
    │  LLM 做最终映射决策 + 安全证据绑定（SHA256 / revision 校验）
    ▼
experiment_plan
        生成可执行的复现实验计划
```

整条链路分三个阶段：

1. **构建映射目标（targets）** —— 论文侧要"找什么"。
2. **多通道检索（retrieval）** —— 代码库侧"在哪找"。
3. **LLM 决策 + 证据绑定（mapping）** —— 最终"选哪个、凭什么"。

---

## 1. 方式一：确定性映射目标构建

**文件**：`app/tools/mapping_target_tools.py`（约 1647 行）

入口 `build_code_mapping_targets()` 把论文的方法描述拆成**有预算上限的检索目标列表**，而不是让 LLM 自由发挥"我要找 X"。

### 5 类 target

| target 类型 | 含义 | 示例 |
|---|---|---|
| `core_method` | 论文核心方法 / 模型结构 | "multi-head self-attention"，"transpose of input" |
| `data_pipeline` | 数据加载 / 预处理 / 增强管线 | "random crop 224"，"normalize imagenet mean/std" |
| `training_config` | 训练超参 / 优化器 / 学习率调度 | "adamw lr 1e-4"，"cosine schedule" |
| `evaluation_metric` | 评测指标 / 验证方式 | "f1 score"，"per-point accuracy" |
| `ablation_switch` | 消融实验的开关 / 变体 | "with/without positional encoding" |

### 预算上限（防发散）

总 target 数有硬顶，避免一次检索面铺太开：

- 总共 **12** 个 target
- 其中 `core_method` 最多 **6** 个（核心方法优先，保证资源倾斜到主干）
- 其余类型共享剩余预算

这样既保证覆盖 5 个维度，又保证每类检索都是聚焦的、可追溯的。

### 为什么要确定性

- 相同输入 → 相同 target 列表，复现 agent 的中间产物可审计、可对拍。
- target 是"带类型的检索意图"，下游检索能根据类型做**类别感知**的路径加权（见方式三）。

---

## 2. 方式二：LLM 辅助别名解析（同义词归并）

**文件**：`app/tools/mapping_alias_tools.py`（约 836 行）+ `app/nodes/mapping_alias_resolver_node.py`

论文术语和代码命名往往不一致（如论文说 "spatial transformer"，代码里叫 `pst_block`）。这一步把术语对齐成"该找什么"的候选集。

### 确定性预分组

不直接问 LLM"这两个是不是同义词"，而是先用**确定性的成对打分**把候选名聚类成组：

| 匹配策略 | 得分 |
|---|---|
| 名称完全相同 | 90 |
| 名称含对方关键字 | 75 |
| 仅关键字命中 | 45 |
| token 重叠度 | 60 ~ 30 |

- 聚类阈值：**55**（得分 ≥ 55 才认为是同组候选）
- 采用**贪心聚类**：按得分降序依次合并，避免组合爆炸

### LLM 只做最后一步决策

确定性打分只能把"明显像"的聚在一起，边界情况才轮到 LLM：**LLM 只负责判断两个候选组是否应该合并**，不负责打分、不负责枚举。

### 冲突族检测

某些命名差异是**语义相反**的，绝对不能合并：

- `transpose` vs `forward`
- `encoder` vs `decoder`
- `teacher` vs `student`
- `input` vs `output`

这些冲突族在聚类时显式排除，防止 LLM 把"输入投影"和"输出投影"误并成同一个检索目标。

---

## 3. 方式三：8 通道混合检索 + RRF 融合

**目录**：`app/retrieval/`（`indexer.py` / `chunking.py` / `dense.py` / `ranking.py` / `service.py` / `query_builder.py` / `policy.py`）+ `config/retrieval_policy.json`

这是整条链路的核心：**8 个检索通道各打各的候选，再用 RRF 无参融合排序**。

### 通道与权重

| 通道 | 权重 | 检索什么 |
|---|---|---|
| traceback | 3.0 | 历史运行 traceback 命中的位置（**最高**，代表"代码真出过问题的地方"） |
| symbol | 2.4 | AST 符号名匹配（类 / 函数 / 变量） |
| dense | 2.1 | 语义向量检索（embedding 相似度） |
| keyword | 2.0 | 关键词匹配 |
| import_graph | 1.7 | import 依赖图上相邻的模块 |
| cli_config | 1.6 | CLI 参数 / 配置文件键 |
| path | 1.2 | 路径名子串匹配 |
| bm25 | 1.0 | 经典 BM25 全文检索（基线） |

- 融合算法：**RRF（Reciprocal Rank Fusion）**，`rrf_k = 60`，多通道排名直接融合，无需调权阈值。
- **类别感知路径加分** `_target_path_bonus()`：同一 target 会按类型加分 —— 比如 `training_config` 的候选命中在 `config/*.yaml` 路径上，会额外加权；`core_method` 命中在 `model/` / `network/` 下同理。把方式一的类型信息回灌进检索。

### 离线索引

| 文件 | 作用 |
|---|---|
| `indexer.py` | 扫仓库构建 **AST symbols**、**imports**、**CLI options**、**BM25 TF** 四类索引 |
| `chunking.py` | 滑动窗口切 chunk：**80 行 / 16 行重叠**，且做**符号感知**（尽量不在函数 / 类定义中间切断） |
| `dense.py` | embedding 向量化，配 **SQLite embedding cache**（命中缓存免重复计算） |
| `policy.py` | 检索策略（profile）路由，`config/retrieval_policy.json` 定义 **5 个 profile**（如精确符号 / 语义模糊 / 消融变体等场景各用不同通道子集与权重） |

### 为什么是混合通道

单通道必然有盲区：符号名匹配不到"改了名"的代码，BM25 匹配不到"没出现论文词汇"的实现，dense 又可能把语义相近但不相关的文件顶上来。8 通道 + RRF 是**拿召回换精度**：先广撒网，再用融合排序把"多方都点名"的候选推到最前。

---

## 4. 方式四：LLM 映射决策 + 安全证据绑定

**文件**：`app/nodes/mapping_node.py`（约 696 行）

检索完拿到候选，**最终选哪个**由 LLM 决定，但 LLM 的输出被严格约束：**永远不允许自己写文件路径、行号、哈希**。

### LLM 输出什么

LLM 在候选集里**选择并解释**，输出的是"这个 target 对应候选 A"，而不是凭空捏造一个路径。

### 安全证据绑定 `bind_mapping_to_evidence_pack()`

LLM 选定候选后，由确定性代码把候选**绑定成带防伪的证据包**：

- 校验**文件存在**
- 计算并记录 **SHA256**
- 记录当前 **repo revision**
- 再校验 **content hash**

任何一步不通过 → 该绑定被拒绝。这样下游 experiment_plan 拿到的每一个映射都有"当时文件确实长这样"的证明，杜绝幻觉路径 / 过期内容。

### 为什么 LLM 不产出路径

路径 / 行号 / 哈希是**可验证的客观事实**，LLM 生成它们最容易幻觉。让 LLM 只做"选择 + 归因"，客观事实由代码生成并校验 —— 这整条链路信任边界的核心。

---

## 5. 数据流小结

```
论文 PDF
   │  paper_reader（分节解析）
   ▼
结构化方法描述
   │  method_extractor → 5 类 target 素材
   ▼
build_code_mapping_targets()   [方式一：确定性 target + 预算]
   │
   ▼
repo_scan 建立离线索引（AST / imports / CLI / BM25 / dense + cache）
   │
   ▼
mapping_alias_resolver        [方式二：确定性聚类 + LLM 合并决策 + 冲突排除]
   │
   ▼
code_search: 8 通道 → RRF(k=60) → 类别感知加分   [方式三]
   │
   ▼
mapping_node: LLM 选择 + bind_mapping_to_evidence_pack   [方式四]
   │
   ▼
experiment_plan: 可执行复现计划
```

## 6. 设计原则

1. **确定性优先**：target 构建、别名打分、索引、检索融合全部确定性实现，中间产物可审计、可对拍。
2. **LLM 只做决策**：聚类是否合并、候选选哪个 —— 是"判断题"而不是"填空题"。
3. **客观事实不交给 LLM**：路径、行号、SHA256、revision 一律由代码生成并校验。
4. **证据可验证**：每个最终映射都绑定文件存在性 + 哈希 + revision，实验计划里可直接回溯。
5. **检索上下文是 LLM 唯一的信息来源**：LLM 从不超越检索结果去"发明"代码位置。
