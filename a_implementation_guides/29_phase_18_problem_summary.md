# Phase 18 论文章节解析问题分析

## 一、文档目的

本文单独记录 Phase 18 在论文结构化解析过程中发现的问题，方便后续开发、测试和复盘。

本次分析使用的论文是：

```text
pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf
```

对应的解析产物是：

```text
runs/index-paper-20260728-130748-dc149163/analysis/paper_blocks.json
runs/index-paper-20260728-130748-dc149163/analysis/paper_sections.json
runs/index-paper-20260728-130748-dc149163/analysis/paper_parse_report.json
```

需要先区分两个概念：

```text
文本提取成功 != 章节结构解析正确
```

当前 `paper_parse_report.json` 中的 `status: succeeded` 表示 PDF 中存在可用文本，并且解析流程没有发生终止性异常。它不代表识别出的标题、章节层级和正文归属完全正确。

---

## 二、当前问题

### 2.1 当前解析结果概况

本次 PSTNet 论文解析结果如下：

| 指标 | 结果 |
|---|---:|
| PDF 总页数 | 23 |
| 成功索引页数 | 23 |
| OCR required 页数 | 0 |
| 提取 block 数量 | 2270 |
| 生成 section 数量 | 87 |
| 分配给 section 的 block 数量 | 2247 |
| 被排除的重复页眉数量 | 23 |

正文提取和页面覆盖率较好。没有分配给 section 的 23 个 block，都是每页重复出现的：

```text
Published as a conference paper at ICLR 2021
```

这些 block 被识别为重复页眉并排除，是符合预期的。

主要问题出现在标题候选识别阶段。论文实际逻辑章节大约为 37 个，但当前生成了 87 个 section，说明标题召回率较高，但误检较多。

### 2.2 论文主标题被拆分

当前结果生成了两个一级 section：

```text
PSTNET: POINT SPATIO-TEMPORAL CONVOLUTION
ON POINT CLOUD SEQUENCES
```

它们实际上属于同一个论文标题：

```text
PSTNET: POINT SPATIO-TEMPORAL CONVOLUTION
ON POINT CLOUD SEQUENCES
```

当前实现只能合并同一视觉行中的“章节编号 block + 标题 block”，不能合并跨行的无编号标题，因此论文主标题被拆成两个 section。

### 2.3 引用年份被误识别为章节

例如正文中的：

```text
2018) and pooling techniques (Fan et al., 2017) are employed...
2019) converts a point cloud sequence into a 4D occupancy grid...
```

被解析为：

```text
number = "2018"
number = "2019"
```

当前数字标题正则是：

```python
r"^(?P<number>\d+(?:\.\d+)*)(?:[.)])?\s+(?P<title>.+)$"
```

这个正则只检查“数字 + 后续文本”，没有限制：

- block 是否为视觉标题；
- 数字是否为四位年份；
- 后续文本是否为完整正文句子；
- 字号、粗体和位置是否符合标题特征。

因此正文中的引用年份也会命中标题规则。

### 2.4 公式符号被误识别为附录标题

以下公式片段被生成了独立 section：

```text
F′(x,y,z)
M(x,y,z)
W
T
S
```

当前附录标题规则允许以下形式：

```text
大写字母 + 后续文本
```

同时，视觉分类阶段可能因为公式字体或字号将单个符号初步标记为 `heading`。

这会导致公式变量与附录编号 `A`、`B`、`C` 等产生冲突。

### 2.5 正文和图注被误识别为章节

例如：

```text
L = 5 frames, with N = 8 points per frame...
2 to halve the temporal resolution...
```

分别被误认为附录 `L` 和主章节 `2`。

第一个例子符合“大写字母 + 文本”的附录正则；第二个例子符合“数字 + 文本”的数字章节正则。

这些文本的实际 `block_type` 是 `paragraph`，但当前数字标题规则并没有要求 block 必须具有标题排版特征。

### 2.6 表格和图表数据被误识别为章节

例如：

```text
2500 CPU 2205 GPU...
89.39 97.68 69.43 86.52...
0.00 44.61
96.88 97.72 86.20...
```

这些内容来自图表或表格，却被识别为数字章节或子章节。

其中一部分 block 的 `block_type` 已经是 `table`，但 `_heading_parts()` 当前没有在入口处统一拒绝 `table`。

另一部分是表格中的小字号文本行。因为 `89.39` 形式可以命中数字编号正则，所以会被误认为二级标题。

### 2.7 图中的竖排标签被误识别为标题

论文第 21 页中的图像标签：

```text
PSTConv1: N=1024
PSTConv2a: N=512
PSTConv2b: N=512
PSTConv3a: N=256
PSTConv3b: N=256
PSTConv4: N=128
```

被识别成多个一级 section。

以其中一个 block 为例，它的 bbox 宽度约为 9，高度约为 81，说明文本很可能是竖排图像标注，而不是正常的横向章节标题。

当前视觉分类主要使用字号和粗体，没有利用 bbox 的宽高比过滤竖排文本。

### 2.8 跨行附录标题被拆分

附录 M 的标题被解析为：

```text
M VISUALIZATION OF THE OUTPUT OF EACH PST CONVOLUTION LAYER IN
PSTNET
```

当前结果中，前一行成为附录 M，后一行 `PSTNET` 又成为独立的一级 section。

这与论文主标题被拆分的原因相同：当前只支持同行的“编号 + 标题”合并，不支持同一样式的跨行标题续接。

### 2.9 误检标题破坏父子层级

当前层级构建使用一个按 `level` 维护的父节点栈。正常情况下：

```text
3
├── 3.1
├── 3.2
│   ├── 3.2.1
│   └── 3.2.2
├── 3.3
└── 3.4
```

但是误检标题进入父节点栈后，实际结果出现了：

```text
3.2.2 POINT TUBE
└── parent: L = 5 frames...

3.3 POINT SPATIO-TEMPORAL TRANSPOSED CONVOLUTION
└── parent: L = 5 frames...

3.4 PSTNET ARCHITECTURES
└── parent: F′′(x,y,z)
```

这会直接影响后续按 section 检索、按父子关系提取方法模块以及证据溯源。

### 2.10 当前评测无法充分发现误检

现有 paper parser 评测主要检查：

- 页面覆盖率；
- 必要 section kind 是否存在；
- 必要标题是否存在；
- OCR 和冲突数量是否超过阈值。

只要目标章节被识别出来，即使同时存在大量错误 section，当前评测仍然可能通过。

因此曾出现以下现象：

```text
Offline parser eval score = 1.0
实际 paper_sections.json 中仍有大量误检
```

评测当前关注“有没有识别到”，但没有充分检查“识别出的内容是否过多或错误”。

---

## 三、当前的解决方法

当前方法是一套不依赖 LLM 的确定性解析流程：

```text
PDF
  ↓
PyMuPDF 提取文本行和排版信息
  ↓
生成 PaperBlock
  ↓
文本标准化、页眉页脚过滤、表格提取
  ↓
排版特征 + 正则规则识别标题
  ↓
按标题边界切分 PaperSection
  ↓
使用 level 栈建立父子关系
  ↓
写入 run-native Artifact
```

### 3.1 PDF 文本提取

涉及文件：

```text
app/paper/pdf_parser.py
```

核心函数：

```python
extract_pdf_blocks()
```

当前使用：

```python
page.get_text("dict", sort=True)
```

其中：

- `dict` 用于获取文本、bbox、字号、字体和粗体信息；
- `sort=True` 尝试按视觉阅读顺序输出；
- 当前以 PDF 中的每个视觉文本行为一个 `PaperBlock`；
- 图片对象暂时不进入文本解析流程。

### 3.2 正文字号估计和视觉初判

核心函数：

```python
_estimate_body_font()
_provisional_type()
```

系统先根据较长文本的字号中位数估计正文字号，然后执行视觉初判：

```text
字号 >= 正文的 1.45 倍  -> title
粗体或字号 >= 1.15 倍   -> heading
Figure/Fig./Table 开头  -> caption
其他                    -> paragraph
```

这一步只是生成候选类型，真正的标题判断在 `sectioning.py` 中完成。

### 3.3 文本标准化

涉及文件：

```text
app/paper/normalization.py
```

核心函数：

```python
normalize_pdf_text()
normalize_heading()
normalize_key()
```

当前会处理：

- Unicode NFKC 标准化；
- 软连字符和不间断空格；
- 连续空格；
- 标点前空格；
- `P ROPOSED` 一类字母间距问题；
- 标题匹配时的大小写和标点差异。

### 3.4 重复页眉页脚过滤

核心函数：

```python
mark_repeated_marginalia()
```

系统检查页面顶部和底部的重复文本。如果同一内容出现在至少 35% 的页面中，就标记为：

```python
excluded = True
block_type = "header" 或 "footer"
```

这是当前解析中效果较稳定的一部分。

### 3.5 表格提取

核心函数：

```python
extract_pdf_tables()
```

当前使用 PyMuPDF 的 `page.find_tables()` 提取表格，并将结果保存为 `table` block。

如果表格解析失败，只写入 warning，不猜测缺失内容。

### 3.6 标题候选识别

涉及文件：

```text
app/paper/sectioning.py
```

核心函数：

```python
_heading_parts()
```

当前支持四类标题：

1. 数字章节标题，例如 `3 METHOD`、`3.2 PST CONVOLUTION`；
2. 附录章节标题，例如 `A APPENDIX`、`B.2 ARCHITECTURE`；
3. 固定无编号标题，例如 `ABSTRACT`、`REFERENCES`；
4. 视觉类型为 `heading` 且单词数量较少的无编号标题。

### 3.7 同行拆分标题合并

核心函数：

```python
_split_heading_parts()
```

它用于恢复被 PDF 拆开的同行标题：

```text
block 1: 4.3
block 2: ABLATION STUDY
```

合并时会检查：

- 位于同一页；
- order 连续；
- bbox 位于同一视觉行；
- 水平间距合理；
- 标题长度和大写比例合理。

当前不支持跨行标题续接。

### 3.8 section 切分和层级建立

核心函数：

```python
build_sections()
```

当前把“一个标题到下一个标题之间”的所有非 excluded block 分配给当前 section。

标题层级由编号计算：

```text
3       -> level 1
3.2     -> level 2
3.2.1   -> level 3
A       -> level 1
B.2     -> level 2
```

父节点通过最近的低层级 section 栈计算。

### 3.9 section 语义分类

核心函数：

```python
classify_section()
```

系统根据标题关键词把 section 分类为：

```text
abstract
introduction
related_work
method
experiments
datasets
implementation
ablation
results
conclusion
references
limitations
other
```

### 3.10 Artifact 持久化

涉及文件：

```text
app/paper/indexer.py
app/nodes/paper_reader_node.py
```

当前会写入：

```text
analysis/paper_document.json
analysis/paper_blocks.json
analysis/paper_sections.json
analysis/paper_parse_report.json
```

这些文件都位于本次 run 目录下，可以被后续 section extraction、reducer、mapping 和 evaluation 使用。

---

## 四、当前方法的优缺点

### 4.1 优点

#### 4.1.1 不依赖 LLM

PDF 到 `PaperSection` 的解析过程是确定性的：

- 不产生模型调用成本；
- 不受 provider 稳定性影响；
- 不会因为模型输出格式错误导致解析失败；
- 相同输入和规则能够得到稳定结果。

#### 4.1.2 页面和正文提取完整

本次 PSTNet 论文实现了：

```text
23 / 23 页成功索引
0 个空页
0 个 OCR_REQUIRED 页
```

说明 PyMuPDF 对这份文字型 PDF 的正文提取效果较好。

#### 4.1.3 Artifact 可追踪

每个 block 都有：

```text
block_id
page
order
bbox
font_size
font_name
text_hash
```

每个 section 都有：

```text
section_id
heading_block_id
block_ids
content_hash
page_start
page_end
parent_id
```

因此后续结果可以追溯到原始页面和文本 block。

#### 4.1.4 对常规章节编号有较高召回率

当前已经能够识别：

```text
1 INTRODUCTION
3.2 PST CONVOLUTION
4.1.2 NTU RGB+D 60 AND NTU RGB+D 120
C IMPLEMENTATION DETAILS
O LIMITATION
```

说明基础编号规则和同行标题合并方向是有效的。

#### 4.1.5 页眉页脚过滤有效

本次 23 个重复会议页眉均被排除，没有污染正文 section。

#### 4.1.6 解析失败可安全降级

如果完全找不到可靠标题，系统会生成一个 `Document` fallback section，而不是让整个工作流直接崩溃。

### 4.2 缺点

#### 4.2.1 标题规则过于宽松

数字和附录正则主要检查文本格式，没有充分结合 block 类型、字体、字号、bbox 和句法特征。

因此高召回率是以大量误检为代价的。

#### 4.2.2 视觉初判特征较少

当前主要使用：

```text
字号
粗体
简单 caption 前缀
```

没有充分利用：

- bbox 宽高比；
- 页面区域；
- 文本方向；
- 与前后 block 的样式一致性；
- 标题上下留白；
- 多栏布局；
- 图像区域和表格区域。

#### 4.2.3 表格与正文标题规则没有完全隔离

已经识别为 `table` 的 block 仍可能进入最终标题正则。

小字号表格文本也可能以普通文本行形式被提取，再被数字标题正则接受。

#### 4.2.4 不支持通用跨行标题合并

当前只能合并同行的编号和标题，无法处理：

- 多行论文主标题；
- 多行附录标题；
- 因页面列宽产生的标题换行。

#### 4.2.5 父子关系依赖候选顺序

父节点栈默认前面的 section 都是合法标题。一旦出现误检，后续真实 section 的父节点可能被污染。

#### 4.2.6 `succeeded` 不能反映结构质量

当前 parse report 主要反映文本是否提取成功，没有反映：

- 标题是否可疑；
- section 数是否异常；
- 父子关系是否完整；
- 是否存在大量短 section；
- 是否出现年份、公式或表格型标题。

#### 4.2.7 当前评测偏重召回率

评测会检查关键标题是否存在，但缺少误检数量和层级准确率指标，因此无法阻止“关键标题都存在，但额外生成大量错误标题”的情况。

#### 4.2.8 对扫描件和复杂布局支持有限

当前没有实际 OCR 流程，也没有对图片中的文字、双栏阅读顺序错误、复杂表格和公式布局进行专门恢复。

---

## 五、下一步的解决方案

下一步应采用：

```text
先建立可量化评测
  ↓
收紧确定性标题规则
  ↓
补充跨行标题合并
  ↓
按编号重建父子关系
  ↓
最后再考虑布局模型或 LLM fallback
```

不建议一开始就让 LLM 重新判断所有 block，因为当前问题的大部分误检都可以通过确定性规则低成本解决。

### 5.1 第一批：建立 PSTNet Golden Heading Case

优先修改：

```text
tests/test_paper_sectioning.py
tests/test_paper_eval.py
app/evaluation/cases/offline/pstnet_paper_parser.json
```

需要记录必须识别的标题：

```text
ABSTRACT
1 INTRODUCTION
2 RELATED WORK
3 PROPOSED POINT SPATIO-TEMPORAL CONVOLUTIONAL NETWORK
3.2.2 POINT TUBE
4 EXPERIMENTS
4.3 ABLATION STUDY
C IMPLEMENTATION DETAILS
O LIMITATION
```

需要记录禁止识别的标题：

```text
2018) and pooling techniques...
F′(x,y,z)
L = 5 frames...
89.39 97.68...
PSTConv1: N=1024
```

建议新增评测字段：

```text
max_section_count
max_unexpected_section_count
forbidden_section_titles
required_parent_relations
```

当前 `tests/test_paper_sectioning.py` 中的：

```python
test_split_heading_does_not_merge_formula_fragment
```

只验证 `W` 没有和公式片段合并，但仍允许 `W` 自己成为 section。下一步应将预期改为：公式变量不能产生任何 section。

### 5.2 第二批：增加标题候选硬过滤

优先修改：

```text
app/paper/sectioning.py
```

在 `_heading_parts()` 入口排除：

```python
if block.block_type in {
    "table",
    "caption",
    "header",
    "footer",
}:
    return None
```

数字标题还应满足：

- block 是 `heading` 或 `title`；
- 编号不是四位年份；
- 文本不是小数表格行；
- 文本不以正文句号结尾；
- 文本长度和单词数处于标题范围；
- 字号不能明显小于正文。

目标效果：

```text
4 EXPERIMENTS       -> 接受
4.3 ABLATION STUDY  -> 接受
2018) and pooling   -> 拒绝
89.39 97.68 69.43   -> 拒绝
```

### 5.3 第三批：收紧附录编号识别

附录标题应优先识别为：

```text
单独的附录编号 block
  +
相邻的标题 block
```

建议条件：

- 编号 block 必须是 `heading`；
- 编号只能是单独的 `A` 到 `Z`，或者 `B.1` 形式；
- 标题 block 必须具有标题样式或较高大写比例；
- 两个 block 必须同行或满足严格的跨行标题条件；
- 不再使用“文本长度小于 100”作为单独的接受条件。

目标效果：

```text
C + IMPLEMENTATION DETAILS  -> 接受
F′(x,y,z)                    -> 拒绝
L = 5 frames                 -> 拒绝
```

### 5.4 第四批：利用 bbox 排除竖排图像标签

优先修改：

```text
app/paper/pdf_parser.py
```

可以增加宽高比判断：

```python
width = x1 - x0
height = y1 - y0

if height > width * 1.5:
    # 更可能是竖排图像标注，而不是正常横向标题。
    return "unknown"
```

阈值需要通过 PSTNet 和其他论文测试校准，不能只依赖单篇论文。

### 5.5 第五批：支持跨行标题合并

优先修改：

```text
app/paper/sectioning.py
```

建议增加：

```python
_same_heading_style()
_looks_like_title_continuation()
_merge_multiline_headings()
```

跨行合并条件可以包括：

- 同一页；
- order 连续；
- 都是 `heading` 或 `title`；
- 字号差异在允许范围内；
- 字体接近；
- 横向起点接近；
- 垂直距离接近正常行距；
- 文本大写比例较高；
- 后一行不像正文完整句子。

需要覆盖：

```text
PSTNET: POINT SPATIO-TEMPORAL CONVOLUTION
ON POINT CLOUD SEQUENCES
```

以及：

```text
M VISUALIZATION OF THE OUTPUT OF EACH PST CONVOLUTION LAYER IN
PSTNET
```

### 5.6 第六批：根据编号计算父节点

优先修改：

```text
app/paper/sectioning.py
```

对于有编号的 section，先根据编号寻找父节点：

```text
3.2.2 -> 3.2
3.2   -> 3
3.3   -> 3
4.1.2 -> 4.1
B.2   -> B
```

可以维护：

```python
section_id_by_number: dict[str, str]
```

如果显式父编号不存在：

- 不要绑定到最近的公式或误检 section；
- 可以将 `parent_id` 设为 `None`；
- 在 parse report 中记录层级 warning。

无编号标题仍可以使用保守的层级栈，但不应污染有编号章节的父节点计算。

### 5.7 第七批：增强 Parse Report

建议在 `PaperParseReport` 中增加：

```text
heading_candidate_count
suspicious_heading_count
hierarchy_warning_count
multiline_heading_merge_count
```

建议增加 warning：

```text
SUSPICIOUS_SECTION_COUNT
SUSPICIOUS_HEADING
MISSING_SECTION_PARENT
HEADING_SEQUENCE_CONFLICT
```

这样报告可以分别表达：

```text
文本抽取是否成功
章节结构是否可信
```

### 5.8 第八批：可选的高级能力

完成确定性规则优化后，再考虑：

1. 使用更强的 PDF layout parser 处理多栏、表格和阅读顺序；
2. 对 `OCR_REQUIRED` 页面接入 OCR；
3. 对低置信度标题候选调用 LLM，而不是把整篇 PDF 都交给 LLM；
4. 为标题候选保存置信度和接受原因；
5. 建立多篇论文的 Golden Dataset，避免规则只适配 PSTNet；
6. 引入标题检测 precision、recall 和 hierarchy accuracy。

LLM fallback 应当只处理规则无法确定的少量候选：

```text
确定性规则高置信度接受
  ↓
确定性规则高置信度拒绝
  ↓
只有中间模糊区域调用 LLM
```

---

## 六、建议验收标准

完成上述改进后，PSTNet 论文应满足：

| 验收项 | 目标 |
|---|---|
| 页面索引覆盖率 | 23 / 23 |
| OCR required 页数 | 0 |
| section 总数 | 建议 35～45 |
| 主章节 1～5 | 全部存在 |
| 方法章节 3.1～3.4 | 全部存在 |
| 实验章节 4.1～4.3 | 全部存在 |
| 附录 C Implementation Details | 存在 |
| 附录 O Limitation | 存在 |
| 四位引用年份 section | 0 |
| 公式变量 section | 0 |
| 表格数值 section | 0 |
| 竖排 PSTConv 标签 section | 0 |
| 论文主标题 | 合并为一个逻辑标题 |
| 附录 M 标题 | 合并完整 |
| `3.2.2` 父节点 | `3.2` |
| `3.3` 父节点 | `3` |
| `3.4` 父节点 | `3` |
| `4.1.1` 父节点 | `4.1` |
| `B.2` 父节点 | `B` |

建议运行：

```bash
python -m pytest \
  tests/test_paper_sectioning.py \
  tests/test_paper_eval.py \
  -q
```

重新生成论文索引：

```bash
python -m app.main index-paper \
  "pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf"
```

运行离线评测：

```bash
python -m app.evaluation.run_eval run \
  --suite offline \
  --case-id offline_pstnet_paper_parser
```

验收时不能只看 `passed` 和总分，还要实际检查：

```text
analysis/paper_sections.json
analysis/paper_parse_report.json
```

---

## 七、结论

当前 Phase 18 的 PDF 文本抽取和 Artifact 设计已经具备良好基础，主要瓶颈不是“读取不到论文”，而是“标题候选规则过宽，导致章节精确率不足”。

下一步最值得优先完成的是：

```text
PSTNet Golden Case
  ↓
过滤 paragraph/table/公式/年份/竖排标签
  ↓
跨行标题合并
  ↓
编号驱动的父子关系
  ↓
增强评测和 Parse Report
```

完成这些改进后，再引入 layout parser、OCR 或 LLM fallback，能够避免用高成本模型掩盖本可以通过确定性规则解决的问题。
