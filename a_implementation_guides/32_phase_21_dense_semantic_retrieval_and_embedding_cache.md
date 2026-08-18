# 32. Phase 21：Dense Semantic Retrieval 与 Embedding Cache

> 本阶段建立在 Phase 20 的 Hybrid Code Evidence Retrieval 之上。
>
> Phase 20 已经具备 literal keyword、AST symbol、import graph、path、CLI/config、BM25、traceback、RRF、Evidence Pack 和 provenance 校验。但是当论文术语与代码命名完全不一致时，精确检索仍可能无法产生可靠种子候选。
>
> 本阶段增加代码语义切块、OpenAI-compatible Embedding 后端、SQLite Embedding Cache 和 Dense Retrieval 通道。Dense 只作为 Phase 20 多通道检索的补充，不替代 AST、BM25、traceback、文件 hash 和程序级 Evidence 白名单。
>
> 本教程只给出实现步骤、完整代码、测试和验收方法。请按照顺序自行修改项目代码。

> **章节标识说明**
>
> - “需要新增”表示创建完整文件。
> - “需要完整替换”表示替换指定文件或函数。
> - “需要局部修改”会给出明确的插入位置和上下文。
> - “原理、运行、调试或验收说明”不要求修改代码。
> - 本阶段不会直接修改你的 `app/` 或 `tests/`，教程代码由你自行落地。
> - 临时验证内容只能放在项目内 `.codex_tmp/`，完成后删除。

---

## 一、为什么 Phase 21 优先做 Dense Retrieval

> **本节类型：优先级分析，不修改项目代码。**

Phase 20 最擅长处理：

```text
论文术语：PST convolution
代码符号：PSTConv
文件路径：modules/pst_convolutions.py
```

但真实仓库可能写成：

```python
class Block(nn.Module):
    def forward(self, x, y):
        neighbor_ids = radius_neighbors(x)
        temporal_delta = y[:, 1:] - y[:, :-1]
        return aggregate(neighbor_ids, temporal_delta)
```

论文描述是：

```text
在连续帧中构造点管道，对空间邻域和时间邻域进行联合特征聚合。
```

这两边可能没有任何共同标识符。此时：

```text
keyword / symbol / path
    可能全部零命中

BM25
    可能只剩少量通用词，排序不稳定

import graph
    需要先有一个可靠的 symbol 或 module 种子
```

Dense Retrieval 可以比较整段作用语义：

```text
论文模块语义
    -> query embedding

局部代码块的数据流和操作
    -> code chunk embedding

cosine similarity
    -> dense candidate
```

上一版路线建议下一阶段进入异步 Job Runtime。但 Phase 20 完成后，检索链路中最直接的准确率缺口已经变成“跨语言、跨命名的语义召回”。因此本阶段先补 Dense Retrieval，异步 Job Runtime 顺延到 Phase 22。

---

## 二、本阶段目标

> **本节类型：目标说明，不修改项目代码。**

完成后系统应具备：

1. 从 `MethodModule` 的名称、描述、关键词和论文 Evidence 构造语义查询；
2. 按 Python symbol 和有限滑动窗口切分代码，而不是整文件 embedding；
3. 在发送远程 Embedding 前对疑似密钥行进行保守脱敏；
4. 使用 OpenAI-compatible Embedding API；
5. 使用 Fake Backend 完成无网络单元测试；
6. 使用 SQLite 按内容 hash 缓存向量；
7. 同一仓库、模型和 chunk policy 不重复 embedding；
8. 计算 query 与 code chunk 的 cosine similarity；
9. 把 Dense 结果作为 `dense` 通道接入 Phase 20 RRF；
10. 继续由 `CodeEvidence` 保存真实源码行号与 hash；
11. Embedding Provider 不可用时可配置为降级 Sparse Hybrid；
12. 在 required 模式下，Embedding 失败必须成为明确 StageError；
13. 保存 semantic chunk manifest 和 dense query report；
14. 增加专门的 provider Golden Case；
15. 量化 embedding call、cache hit 和目标文件 rank。

---

## 三、本阶段不做什么

> **本节类型：范围说明，不修改项目代码。**

本阶段不做：

- 不部署 Milvus、pgvector、Elasticsearch 或独立向量服务；
- 不让 Dense Retrieval 替代 keyword、AST、BM25 或 traceback；
- 不对整个仓库构造一个超长 embedding；
- 不把完整源码放进 LangGraph checkpoint；
- 不把 API key 写入 cache key、Artifact 或日志；
- 不默认允许把私有源码发送给远程 Provider；
- 不因为 cosine similarity 高就允许 file repair 修改文件；
- 不让 Embedding 模型决定最终可访问文件范围；
- 不实现 Cross Encoder 模型下载与 GPU 推理；
- 不把 provider 网络测试放进普通离线回归。

这里需要区分：

```text
Embedding 模型：
    负责生成语义向量。

Vector Store / Cache：
    负责保存向量。

Vector Database：
    负责大规模持久化、过滤和近似最近邻检索。
```

单个中小型论文仓库通常只有几百到几千个语义 chunk。第一版使用 SQLite 缓存向量、在内存中计算 cosine similarity，足以建立准确率基线。

当出现以下情况时再替换为 FAISS 或 pgvector：

```text
单仓库 chunk 数超过约 20,000
需要同时检索大量历史仓库
穷举 cosine 延迟超过评测预算
需要按租户、语言、revision 做服务端过滤
需要多 worker 并发共享索引
```

---

## 四、安全边界

> **本节类型：安全设计，不修改项目代码。**

远程 Embedding 与普通本地 AST 检索有本质区别：

```text
本地 AST / BM25：
    源码不离开机器。

远程 Embedding：
    代码 chunk 会发送到 EMBEDDING_BASE_URL。
```

因此本阶段必须增加独立开关：

```text
ENABLE_DENSE_RETRIEVAL=false
ALLOW_CODE_EMBEDDING_UPLOAD=false
```

只有两者同时为 true，才允许发送代码。

推荐安全语义：

| 场景 | 行为 |
|---|---|
| Dense 未开启 | 只运行 Phase 20 Hybrid |
| Dense 开启但未授权上传 | 记录 fallback，不发送源码 |
| 已授权但 Provider 缺少配置 | 记录 fallback 或 required 失败 |
| Provider 瞬时失败，required=false | 降级 Sparse Hybrid |
| Provider 失败，required=true | 生成 terminal StageError |
| chunk 疑似包含 secret | 脱敏后 embedding，并记录计数 |
| 源码在 embedding 后变化 | CodeEvidence hash 校验失败 |

脱敏不是完整 DLP。即使做了正则脱敏，用户仍必须确认仓库允许发送到目标 Provider。

---

## 五、目标架构

> **本节类型：架构说明，不修改项目代码。**

```mermaid
flowchart TD
    A["MethodModule + PaperEvidence"] --> B["Semantic Query Builder"]
    C["RepositoryIndex"] --> D["Symbol-aware Chunker"]
    D --> E["Secret Redaction"]
    E --> F["Embedding Cache lookup"]
    F -->|miss| G["Embedding Provider"]
    G --> H["SQLite Cache"]
    F -->|hit| I["Chunk Vectors"]
    H --> I
    B --> J["Query Embedding"]
    J --> K["Cosine Ranking"]
    I --> K
    K --> L["Dense ChannelHit"]
    M["Phase 20 sparse channels"] --> N["Weighted RRF"]
    L --> N
    N --> O["Bounded Evidence Pack"]
    O --> P["Mapping / Debug"]
    P --> Q["Programmatic provenance validation"]
```

最重要的边界：

```text
Dense score 只影响候选排名
    !=
Dense score 自动授权文件访问或修改
```

最终 `CodeEvidence.text` 仍然由真实仓库文件按行号读取，并经过：

```text
repo_revision
file_sha256
content_hash
path boundary
```

验证。

---

## 六、涉及文件

> **本节类型：实施清单，不修改项目代码。**

需要新增：

```text
app/retrieval/query_builder.py
app/retrieval/chunking.py
app/retrieval/embedding_backend.py
app/retrieval/embedding_cache.py
app/retrieval/dense.py

tests/test_semantic_query_builder.py
tests/test_semantic_chunking.py
tests/test_embedding_cache.py
tests/test_dense_retrieval.py
tests/test_dense_retrieval_safety.py
tests/test_semantic_retrieval_eval.py

app/evaluation/fixtures/retrieval_repo/obfuscated/operator_core.py
app/evaluation/fixtures/retrieval_repo/obfuscated/image_filter.py
app/evaluation/cases/provider/retrieval_obfuscated_semantics.json
```

需要修改：

```text
app/retrieval/schemas.py
app/retrieval/ranking.py
app/retrieval/service.py
app/retrieval/__init__.py

app/config.py
app/state.py
app/nodes/code_search_node.py
app/main.py
.env.example
.gitignore
pyproject.toml

app/evaluation/schemas.py
app/evaluation/runners.py
app/evaluation/scorers.py
a_implementation_guides/README.md
```

不需要修改 Graph 拓扑：

```text
repo_scan -> code_search -> mapping
```

Dense Retrieval 是 `code_search_node` 内部的可选召回通道。

---

## 七、先记录 Phase 20 基线

> **本节类型：运行说明，不修改项目代码。**

先确认 Phase 20 回归：

```bash
python -m pytest \
  tests/test_search_tools_v2.py \
  tests/test_retrieval_index.py \
  tests/test_retrieval_ranking.py \
  tests/test_hybrid_retrieval.py \
  tests/test_mapping_evidence_boundary.py \
  tests/test_retrieval_eval.py \
  -q
```

然后运行一个刻意不使用 `PSTConv` 名字的查询：

```bash
python -m app.main retrieve-code \
  /data/tianshaoqi24/PST-Convolution-main/ \
  "locate the module that groups spatial neighbors across consecutive frames and jointly aggregates point features"
```

记录：

```text
modules/pst_convolutions.py 的 rank
是否进入 top-k
命中的 retrieval_channels
Evidence snippet 是否靠近核心 forward
```

这个结果就是 Dense Retrieval 的对照基线。后续不能只看 Dense 模式“找到了什么”，还要比较目标 rank 是否提高、旧 Golden 是否回归。

---

## 八、扩展 Retrieval Schema

> **本节类型：需要修改项目代码。**
>
> **需要修改：** `app/retrieval/schemas.py`

### 8.1 增加 dense 通道

将 `RetrievalChannel` 改为：

```python
RetrievalChannel = Literal[
    "keyword",
    "symbol",
    "import_graph",
    "path",
    "cli_config",
    "bm25",
    "traceback",
    "dense",
]
```

### 8.2 增加语义 chunk 和 Artifact schema

在 `RepositoryIndex` 后、`ChannelHit` 前增加：

```python
class SemanticChunk(RetrievalModel):
    """
    仅在 code_search_node 当前进程内使用。

    embedding_text 是脱敏后的 Provider 输入，不写入 checkpoint。
    """

    chunk_id: str
    repo_fingerprint: str
    file_path: str
    file_sha256: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    symbol: str | None = None
    source_content_hash: str
    embedding_content_hash: str
    embedding_text: str
    redacted_line_count: int = Field(default=0, ge=0)


class SemanticChunkMetadata(RetrievalModel):
    """写入 Artifact 的 chunk metadata，不包含源码正文和向量。"""

    chunk_id: str
    file_path: str
    file_sha256: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    symbol: str | None = None
    source_content_hash: str
    embedding_content_hash: str
    redacted_line_count: int = Field(default=0, ge=0)


class SemanticIndexManifest(RetrievalModel):
    index_version: str
    chunk_policy_version: str
    repo_root: str
    repo_revision: str | None = None
    repo_fingerprint: str
    chunk_count: int = Field(ge=0)
    redacted_line_count: int = Field(default=0, ge=0)
    chunks: list[SemanticChunkMetadata] = Field(
        default_factory=list
    )
    warnings: list[str] = Field(default_factory=list)
```

在 `ChannelHit` 后增加：

```python
class DenseRetrievalReport(RetrievalModel):
    enabled: bool
    required: bool = False
    provider_namespace: str | None = None
    model: str | None = None
    embedding_dimensions: int | None = Field(
        default=None,
        ge=1,
    )
    query_hash: str | None = None
    chunk_count: int = Field(default=0, ge=0)
    cache_hits: int = Field(default=0, ge=0)
    cache_misses: int = Field(default=0, ge=0)
    embedding_document_calls: int = Field(
        default=0,
        ge=0,
    )
    embedding_query_calls: int = Field(
        default=0,
        ge=0,
    )
    hits: list[ChannelHit] = Field(
        default_factory=list
    )
    fallback_reason: str | None = None
```

这里故意不把向量写入 run Artifact：

```text
SQLite Cache：
    保存向量，用于复用计算。

SemanticIndexManifest：
    保存 chunk 身份、hash、行号和脱敏计数。

DenseRetrievalReport：
    保存模型身份、cache 命中和最终排名。
```

---

## 九、构造论文模块的语义查询

> **本节类型：需要新增项目代码。**
>
> **需要新增：** `app/retrieval/query_builder.py`

完整文件：

```python
from __future__ import annotations

from typing import Any


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _append_unique(
    output: list[str],
    value: Any,
) -> None:
    normalized = _clean(value)
    if normalized and normalized not in output:
        output.append(normalized)


def build_lexical_query(
    module: dict[str, Any],
) -> str:
    """
    Phase 20 sparse 通道继续使用短查询。

    不把大量 PaperEvidence 塞给 literal rg，否则长句几乎不会逐行命中。
    """

    values: list[str] = []
    _append_unique(values, module.get("name"))
    _append_unique(
        values,
        module.get("description"),
    )
    return "\n".join(values)


def build_semantic_query(
    module: dict[str, Any],
    *,
    max_chars: int = 6000,
) -> str:
    """
    为 Dense Retrieval 提供包含论文语义和行为线索的查询。

    查询只来自已经结构化、可追踪的 MethodModule，不让模型临时扩写。
    """

    if max_chars < 200:
        raise ValueError(
            "semantic query max_chars 不能小于 200"
        )

    lines: list[str] = []
    name = _clean(module.get("name"))
    description = _clean(
        module.get("description")
    )
    if name:
        lines.append(f"paper module: {name}")
    if description:
        lines.append(
            f"module behavior: {description}"
        )

    keywords: list[str] = []
    for value in (
        module.get("possible_keywords") or []
    ):
        _append_unique(keywords, value)
    if keywords:
        lines.append(
            "paper terminology: "
            + ", ".join(keywords)
        )

    evidence_values: list[str] = []
    for evidence in module.get(
        "evidence",
        [],
    ):
        if not isinstance(evidence, dict):
            continue
        _append_unique(
            evidence_values,
            evidence.get("quote_or_summary")
            or evidence.get("summary")
            or evidence.get("text"),
        )

    for value in evidence_values:
        candidate = (
            "paper evidence: "
            f"{value}"
        )
        if (
            len("\n".join([*lines, candidate]))
            > max_chars
        ):
            break
        lines.append(candidate)

    query = "\n".join(lines).strip()
    if not query:
        raise ValueError(
            "MethodModule 无法构造 semantic query"
        )
    return query[:max_chars]
```

为什么要分成两个 query：

```text
lexical query：
    短、精确，适合 rg / symbol / BM25。

semantic query：
    包含论文行为描述和 Evidence，适合 Embedding。
```

不要用语义长查询替换所有 sparse query。

---

## 十、实现符号感知代码切块与脱敏

> **本节类型：需要新增项目代码。**
>
> **需要新增：** `app/retrieval/chunking.py`

完整文件：

```python
from __future__ import annotations

import re
from pathlib import Path

from app.retrieval.indexer import (
    sha256_path,
    sha256_text,
)
from app.retrieval.schemas import (
    RepositoryIndex,
    SemanticChunk,
    SemanticChunkMetadata,
    SemanticIndexManifest,
)


SEMANTIC_SUFFIXES = {
    ".py",
    ".md",
    ".rst",
    ".txt",
}

_SECRET_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    (
        \b(?:
            api[_-]?key
            |access[_-]?token
            |auth[_-]?token
            |password
            |passwd
            |client[_-]?secret
            |private[_-]?key
        )\b
        \s*[:=]\s*
    )
    .+$
    """
)

_PRIVATE_KEY_MARKER_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    re.IGNORECASE,
)


def _safe_file(
    root: Path,
    relative_path: str,
) -> Path:
    unresolved = root / relative_path
    if unresolved.is_symlink():
        raise ValueError(
            "Semantic chunk 不允许读取软链接："
            f"{relative_path}"
        )
    candidate = unresolved.resolve()
    if (
        candidate == root
        or root not in candidate.parents
        or not candidate.is_file()
    ):
        raise ValueError(
            "Semantic chunk 文件越界、缺失或为软链接："
            f"{relative_path}"
        )
    return candidate


def _redact_line(
    line: str,
) -> tuple[str, bool]:
    if _PRIVATE_KEY_MARKER_RE.search(line):
        return "<REDACTED_PRIVATE_KEY>", True

    replaced, count = _SECRET_ASSIGNMENT_RE.subn(
        lambda match: (
            f"{match.group(1)}<REDACTED>"
        ),
        line,
    )
    return replaced, bool(count)


def _windows(
    *,
    start_line: int,
    end_line: int,
    max_lines: int,
    overlap_lines: int,
) -> list[tuple[int, int]]:
    if start_line > end_line:
        return []
    if max_lines < 8:
        raise ValueError(
            "semantic chunk max_lines 不能小于 8"
        )
    if (
        overlap_lines < 0
        or overlap_lines >= max_lines
    ):
        raise ValueError(
            "overlap_lines 必须满足 "
            "0 <= overlap_lines < max_lines"
        )

    step = max_lines - overlap_lines
    output = []
    cursor = start_line
    while cursor <= end_line:
        window_end = min(
            end_line,
            cursor + max_lines - 1,
        )
        output.append((cursor, window_end))
        if window_end >= end_line:
            break
        cursor += step
    return output


def _chunk_id(
    *,
    repo_fingerprint: str,
    file_path: str,
    start_line: int,
    end_line: int,
    symbol: str | None,
    source_content_hash: str,
) -> str:
    payload = "|".join(
        [
            repo_fingerprint,
            file_path,
            str(start_line),
            str(end_line),
            symbol or "<module>",
            source_content_hash,
        ]
    )
    return (
        "semantic-"
        f"{sha256_text(payload)[:24]}"
    )


def _embedding_text(
    *,
    file_path: str,
    symbol: str | None,
    lines: list[str],
) -> str:
    header = [
        f"file: {file_path}",
        f"symbol: {symbol or '<module>'}",
        "code:",
    ]
    return "\n".join(
        [
            *header,
            *lines,
        ]
    )


def build_semantic_chunks(
    *,
    repo_path: str | Path,
    index: RepositoryIndex,
    chunk_policy_version: str,
    max_lines: int = 80,
    overlap_lines: int = 16,
    max_chunks: int = 5000,
) -> tuple[
    list[SemanticChunk],
    SemanticIndexManifest,
]:
    root = Path(repo_path).expanduser().resolve()
    if Path(index.repo_root).resolve() != root:
        raise ValueError(
            "RepositoryIndex 与 semantic repo_path 不一致"
        )
    if max_chunks < 1:
        raise ValueError(
            "semantic max_chunks 必须大于 0"
        )

    symbols_by_file: dict[str, list] = {}
    for symbol in index.symbols:
        symbols_by_file.setdefault(
            symbol.file_path,
            [],
        ).append(symbol)

    chunks: list[SemanticChunk] = []
    warnings: list[str] = []
    total_redacted_lines = 0
    reached_limit = False

    for document in index.documents:
        if reached_limit:
            break
        if (
            Path(document.file_path)
            .suffix.casefold()
            not in SEMANTIC_SUFFIXES
        ):
            continue

        path = _safe_file(
            root,
            document.file_path,
        )
        if sha256_path(path) != document.file_sha256:
            warnings.append(
                "STALE_SOURCE_SKIPPED:"
                f"{document.file_path}"
            )
            continue

        source_lines = path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()
        if not source_lines:
            continue
        if any(
            _PRIVATE_KEY_MARKER_RE.search(line)
            for line in source_lines
        ):
            # 私钥正文跨多行，逐行替换无法可靠保证不泄漏，整文件跳过。
            warnings.append(
                "PRIVATE_KEY_FILE_SKIPPED:"
                f"{document.file_path}"
            )
            continue

        redacted_lines = []
        file_redacted_count = 0
        for line in source_lines:
            redacted, changed = _redact_line(line)
            redacted_lines.append(redacted)
            file_redacted_count += int(changed)
        total_redacted_lines += file_redacted_count

        # 全文件滑动窗口负责 module-level 数据流、import 和不规则代码。
        spans: list[
            tuple[int, int, str | None]
        ] = [
            (
                start,
                end,
                None,
            )
            for start, end in _windows(
                start_line=1,
                end_line=len(source_lines),
                max_lines=max_lines,
                overlap_lines=overlap_lines,
            )
        ]

        # Symbol span 让类和函数边界成为额外的高质量语义 chunk。
        for symbol in symbols_by_file.get(
            document.file_path,
            [],
        ):
            symbol_end = min(
                symbol.end_line,
                len(source_lines),
            )
            for start, end in _windows(
                start_line=symbol.start_line,
                end_line=symbol_end,
                max_lines=max_lines,
                overlap_lines=overlap_lines,
            ):
                spans.append(
                    (
                        start,
                        end,
                        symbol.qualified_name,
                    )
                )

        seen_spans: set[
            tuple[int, int, str | None]
        ] = set()
        for start, end, symbol_name in spans:
            identity = (
                start,
                end,
                symbol_name,
            )
            if identity in seen_spans:
                continue
            seen_spans.add(identity)

            raw_slice = "\n".join(
                source_lines[
                    start - 1:end
                ]
            )
            safe_slice_lines = redacted_lines[
                start - 1:end
            ]
            safe_text = _embedding_text(
                file_path=document.file_path,
                symbol=symbol_name,
                lines=safe_slice_lines,
            )
            source_hash = sha256_text(
                raw_slice
            )

            chunks.append(
                SemanticChunk(
                    chunk_id=_chunk_id(
                        repo_fingerprint=(
                            index.repo_fingerprint
                        ),
                        file_path=(
                            document.file_path
                        ),
                        start_line=start,
                        end_line=end,
                        symbol=symbol_name,
                        source_content_hash=(
                            source_hash
                        ),
                    ),
                    repo_fingerprint=(
                        index.repo_fingerprint
                    ),
                    file_path=(
                        document.file_path
                    ),
                    file_sha256=(
                        document.file_sha256
                    ),
                    start_line=start,
                    end_line=end,
                    symbol=symbol_name,
                    source_content_hash=(
                        source_hash
                    ),
                    embedding_content_hash=(
                        sha256_text(safe_text)
                    ),
                    embedding_text=safe_text,
                    redacted_line_count=sum(
                        1
                        for raw, safe in zip(
                            source_lines[
                                start - 1:end
                            ],
                            safe_slice_lines,
                        )
                        if raw != safe
                    ),
                )
            )

            if len(chunks) >= max_chunks:
                reached_limit = True
                warnings.append(
                    "SEMANTIC_CHUNK_LIMIT_REACHED:"
                    f"{max_chunks}"
                )
                break

    metadata = [
        SemanticChunkMetadata(
            chunk_id=chunk.chunk_id,
            file_path=chunk.file_path,
            file_sha256=chunk.file_sha256,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            symbol=chunk.symbol,
            source_content_hash=(
                chunk.source_content_hash
            ),
            embedding_content_hash=(
                chunk.embedding_content_hash
            ),
            redacted_line_count=(
                chunk.redacted_line_count
            ),
        )
        for chunk in chunks
    ]

    return chunks, SemanticIndexManifest(
        index_version=index.index_version,
        chunk_policy_version=(
            chunk_policy_version
        ),
        repo_root=str(root),
        repo_revision=index.repo_revision,
        repo_fingerprint=(
            index.repo_fingerprint
        ),
        chunk_count=len(chunks),
        redacted_line_count=(
            total_redacted_lines
        ),
        chunks=metadata,
        warnings=warnings,
    )
```

切块策略的作用：

```text
全文件滑动窗口：
    保证命名不规则、module-level 代码和 import 仍可召回。

Symbol chunk：
    让函数和类的局部行为形成更集中的语义表示。

overlap：
    避免数据流刚好被窗口边界切断。
```

`SemanticIndexManifest` 不保存 `embedding_text`，避免把整个仓库源码复制进 run Artifact。

---

## 十一、实现可替换 Embedding Backend

> **本节类型：需要新增项目代码。**
>
> **需要新增：** `app/retrieval/embedding_backend.py`

完整文件：

```python
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from langchain_openai import OpenAIEmbeddings

from app.config import settings


class EmbeddingProviderError(RuntimeError):
    """Embedding Provider 配置、传输或返回值错误。"""


@dataclass(frozen=True)
class EmbeddingBackendIdentity:
    provider_namespace: str
    model: str


@runtime_checkable
class EmbeddingBackend(Protocol):
    @property
    def identity(
        self,
    ) -> EmbeddingBackendIdentity:
        ...

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        ...

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        ...


def validate_vectors(
    vectors: list[list[float]],
    *,
    expected_count: int,
    expected_dimensions: int | None = None,
) -> int:
    """验证 Provider 没有返回空向量、NaN、Inf 或维度漂移。"""

    if len(vectors) != expected_count:
        raise EmbeddingProviderError(
            "Embedding 返回数量不一致："
            f"expected={expected_count}, "
            f"actual={len(vectors)}"
        )
    if not vectors:
        raise EmbeddingProviderError(
            "Embedding 返回为空"
        )

    dimensions = len(vectors[0])
    if dimensions < 1:
        raise EmbeddingProviderError(
            "Embedding 向量维度必须大于 0"
        )
    if (
        expected_dimensions is not None
        and dimensions != expected_dimensions
    ):
        raise EmbeddingProviderError(
            "Embedding 维度与缓存不一致："
            f"expected={expected_dimensions}, "
            f"actual={dimensions}"
        )

    for vector in vectors:
        if len(vector) != dimensions:
            raise EmbeddingProviderError(
                "同一次 Embedding 返回了不同维度"
            )
        if not all(
            math.isfinite(float(value))
            for value in vector
        ):
            raise EmbeddingProviderError(
                "Embedding 向量包含 NaN 或 Inf"
            )
    return dimensions


class OpenAICompatibleEmbeddingBackend:
    """
    复用项目已有 langchain-openai 依赖。

    tiktoken_enabled=False：
        避免 OpenAI-compatible 自定义模型因 tokenizer 名称未知而失败。

    check_embedding_ctx_length=False：
        chunker 已负责限制输入；长度错误由 Provider 明确返回。
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        if not api_key.strip():
            raise EmbeddingProviderError(
                "EMBEDDING_API_KEY 未配置"
            )
        if not base_url.strip():
            raise EmbeddingProviderError(
                "EMBEDDING_BASE_URL 未配置"
            )
        if not model.strip():
            raise EmbeddingProviderError(
                "EMBEDDING_MODEL 未配置"
            )

        # Namespace 只保存 endpoint hash，不把完整内部地址写入 cache key。
        endpoint_hash = hashlib.sha256(
            base_url.rstrip("/").encode(
                "utf-8"
            )
        ).hexdigest()[:16]
        self._identity = EmbeddingBackendIdentity(
            provider_namespace=(
                f"openai-compatible:{endpoint_hash}"
            ),
            model=model,
        )
        self._client = OpenAIEmbeddings(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout_seconds,
            max_retries=max_retries,
            tiktoken_enabled=False,
            check_embedding_ctx_length=False,
        )

    @property
    def identity(
        self,
    ) -> EmbeddingBackendIdentity:
        return self._identity

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self._client.embed_documents(
                texts
            )
        except Exception as exc:  # noqa: BLE001
            # 不把 Provider 原始对象或请求 headers 写入错误。
            raise EmbeddingProviderError(
                "Embedding document request failed: "
                f"{type(exc).__name__}"
            ) from exc

        validate_vectors(
            vectors,
            expected_count=len(texts),
        )
        return [
            [float(value) for value in vector]
            for vector in vectors
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        if not text.strip():
            raise EmbeddingProviderError(
                "Embedding query 不能为空"
            )
        try:
            vector = self._client.embed_query(text)
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingProviderError(
                "Embedding query request failed: "
                f"{type(exc).__name__}"
            ) from exc

        validate_vectors(
            [vector],
            expected_count=1,
        )
        return [
            float(value)
            for value in vector
        ]


def get_embedding_backend(
) -> EmbeddingBackend:
    return OpenAICompatibleEmbeddingBackend(
        api_key=(
            settings.embedding_api_key or ""
        ),
        base_url=(
            settings.embedding_base_url or ""
        ),
        model=settings.embedding_model,
        timeout_seconds=(
            settings.embedding_timeout_seconds
        ),
        max_retries=(
            settings.embedding_max_retries
        ),
    )
```

为什么定义 `EmbeddingBackend` Protocol：

```text
生产：
    OpenAICompatibleEmbeddingBackend

单元测试：
    FakeEmbeddingBackend

未来：
    LocalSentenceTransformerBackend
    HuggingFaceTEIBackend
    Azure/OpenAI Backend
```

Dense 核心逻辑不应依赖某个 Provider SDK。

---

## 十二、实现 SQLite Embedding Cache

> **本节类型：需要新增项目代码。**
>
> **需要新增：** `app/retrieval/embedding_cache.py`

完整文件：

```python
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.retrieval.embedding_backend import (
    EmbeddingBackendIdentity,
    EmbeddingProviderError,
)


def build_embedding_cache_key(
    *,
    identity: EmbeddingBackendIdentity,
    cache_version: str,
    value_kind: str,
    content_hash: str,
) -> str:
    """
    API key 不得进入 key。

    value_kind 区分 document/query，避免相同文本在未来采用不同
    Provider instruction 时错误复用。
    """

    payload = "|".join(
        [
            identity.provider_namespace,
            identity.model,
            cache_version,
            value_kind,
            content_hash,
        ]
    )
    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def _decode_vector(
    raw_value: str,
    *,
    expected_dimensions: int,
) -> list[float]:
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise EmbeddingProviderError(
            "Embedding cache vector JSON 损坏"
        ) from exc

    if (
        not isinstance(payload, list)
        or len(payload) != expected_dimensions
    ):
        raise EmbeddingProviderError(
            "Embedding cache vector 维度损坏"
        )
    vector = [float(value) for value in payload]
    if not all(math.isfinite(value) for value in vector):
        raise EmbeddingProviderError(
            "Embedding cache vector 包含 NaN 或 Inf"
        )
    return vector


class SQLiteEmbeddingCache:
    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._initialize()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=15,
        )
        connection.execute(
            "PRAGMA journal_mode=WAL"
        )
        connection.execute(
            "PRAGMA busy_timeout=15000"
        )
        return connection

    def _initialize(
        self,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    cache_key TEXT PRIMARY KEY,
                    provider_namespace TEXT NOT NULL,
                    model TEXT NOT NULL,
                    cache_version TEXT NOT NULL,
                    value_kind TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    dimensions INTEGER NOT NULL,
                    vector_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def get_many(
        self,
        keys: list[str],
    ) -> dict[str, list[float]]:
        unique_keys = list(
            dict.fromkeys(keys)
        )
        if not unique_keys:
            return {}

        output: dict[str, list[float]] = {}
        # SQLite 默认变量数可能为 999，按 500 分批读取。
        with self._connect() as connection:
            for offset in range(
                0,
                len(unique_keys),
                500,
            ):
                batch = unique_keys[
                    offset:offset + 500
                ]
                placeholders = ",".join(
                    "?"
                    for _ in batch
                )
                rows = connection.execute(
                    (
                        "SELECT cache_key, dimensions, "
                        "vector_json "
                        "FROM embedding_cache "
                        f"WHERE cache_key IN ({placeholders})"
                    ),
                    batch,
                ).fetchall()
                for key, dimensions, raw_vector in rows:
                    try:
                        output[str(key)] = _decode_vector(
                            str(raw_vector),
                            expected_dimensions=int(
                                dimensions
                            ),
                        )
                    except EmbeddingProviderError:
                        # 损坏项当作 cache miss，稍后由 Provider 重建。
                        connection.execute(
                            (
                                "DELETE FROM embedding_cache "
                                "WHERE cache_key = ?"
                            ),
                            (key,),
                        )
        return output

    def put_many(
        self,
        *,
        identity: EmbeddingBackendIdentity,
        cache_version: str,
        value_kind: str,
        values: list[
            tuple[str, str, list[float]]
        ],
    ) -> None:
        """
        values:
            (cache_key, content_hash, vector)
        """

        if not values:
            return
        created_at = datetime.now(
            timezone.utc
        ).isoformat()
        rows = []
        for key, content_hash, vector in values:
            if not vector or not all(
                math.isfinite(float(value))
                for value in vector
            ):
                raise EmbeddingProviderError(
                    "拒绝缓存无效 Embedding 向量"
                )
            rows.append(
                (
                    key,
                    identity.provider_namespace,
                    identity.model,
                    cache_version,
                    value_kind,
                    content_hash,
                    len(vector),
                    json.dumps(
                        [
                            float(value)
                            for value in vector
                        ],
                        separators=(",", ":"),
                    ),
                    created_at,
                )
            )

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO embedding_cache (
                    cache_key,
                    provider_namespace,
                    model,
                    cache_version,
                    value_kind,
                    content_hash,
                    dimensions,
                    vector_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
```

Cache identity：

```text
endpoint namespace hash
+ model
+ cache version
+ document/query
+ content hash
```

以下内容不能进入 Cache：

```text
API key
完整 Provider headers
用户身份 token
未脱敏源码正文
```

---

## 十三、实现 Dense Retriever

> **本节类型：需要新增项目代码。**
>
> **需要新增：** `app/retrieval/dense.py`

完整文件：

```python
from __future__ import annotations

import math
from dataclasses import dataclass

from app.retrieval.embedding_backend import (
    EmbeddingBackend,
    EmbeddingProviderError,
    validate_vectors,
)
from app.retrieval.embedding_cache import (
    SQLiteEmbeddingCache,
    build_embedding_cache_key,
)
from app.retrieval.indexer import sha256_text
from app.retrieval.schemas import (
    ChannelHit,
    DenseRetrievalReport,
    SemanticChunk,
)


def cosine_similarity(
    left: list[float],
    right: list[float],
) -> float:
    if not left or len(left) != len(right):
        raise EmbeddingProviderError(
            "Cosine 向量维度不一致"
        )

    dot = sum(
        a * b
        for a, b in zip(left, right)
    )
    left_norm = math.sqrt(
        sum(value * value for value in left)
    )
    right_norm = math.sqrt(
        sum(value * value for value in right)
    )
    if left_norm == 0 or right_norm == 0:
        raise EmbeddingProviderError(
            "Embedding 向量不能是零向量"
        )
    return dot / (left_norm * right_norm)


@dataclass(frozen=True)
class DensePreparationStats:
    cache_hits: int
    cache_misses: int
    embedding_document_calls: int
    dimensions: int


class PreparedDenseRetriever:
    """
    当前 code_search_node 内复用：

    - document chunk 只准备一次；
    - 每个 MethodModule 只新增一个 query embedding；
    - 对象不进入 Graph State 或 checkpoint。
    """

    def __init__(
        self,
        *,
        chunks: list[SemanticChunk],
        vectors_by_chunk_id: dict[
            str,
            list[float],
        ],
        backend: EmbeddingBackend,
        cache: SQLiteEmbeddingCache,
        cache_version: str,
        stats: DensePreparationStats,
    ) -> None:
        self.chunks = chunks
        self.vectors_by_chunk_id = (
            vectors_by_chunk_id
        )
        self.backend = backend
        self.cache = cache
        self.cache_version = cache_version
        self.stats = stats

    @classmethod
    def prepare(
        cls,
        *,
        chunks: list[SemanticChunk],
        backend: EmbeddingBackend,
        cache: SQLiteEmbeddingCache,
        cache_version: str,
        batch_size: int,
    ) -> "PreparedDenseRetriever":
        if not chunks:
            raise EmbeddingProviderError(
                "没有可用于 Dense Retrieval 的代码 chunk"
            )
        if batch_size < 1:
            raise ValueError(
                "embedding batch_size 必须大于 0"
            )

        key_by_chunk_id = {
            chunk.chunk_id: (
                build_embedding_cache_key(
                    identity=backend.identity,
                    cache_version=cache_version,
                    value_kind="document",
                    content_hash=(
                        chunk.embedding_content_hash
                    ),
                )
            )
            for chunk in chunks
        }
        cached = cache.get_many(
            list(key_by_chunk_id.values())
        )

        vectors_by_chunk_id: dict[
            str,
            list[float],
        ] = {}
        missing_chunks = []
        for chunk in chunks:
            key = key_by_chunk_id[
                chunk.chunk_id
            ]
            vector = cached.get(key)
            if vector is None:
                missing_chunks.append(chunk)
            else:
                vectors_by_chunk_id[
                    chunk.chunk_id
                ] = vector

        document_calls = 0
        for offset in range(
            0,
            len(missing_chunks),
            batch_size,
        ):
            batch = missing_chunks[
                offset:offset + batch_size
            ]
            vectors = backend.embed_documents(
                [
                    chunk.embedding_text
                    for chunk in batch
                ]
            )
            validate_vectors(
                vectors,
                expected_count=len(batch),
            )
            document_calls += 1

            rows = []
            for chunk, vector in zip(
                batch,
                vectors,
            ):
                vectors_by_chunk_id[
                    chunk.chunk_id
                ] = vector
                rows.append(
                    (
                        key_by_chunk_id[
                            chunk.chunk_id
                        ],
                        chunk.embedding_content_hash,
                        vector,
                    )
                )
            cache.put_many(
                identity=backend.identity,
                cache_version=cache_version,
                value_kind="document",
                values=rows,
            )

        all_vectors = list(
            vectors_by_chunk_id.values()
        )
        dimensions = validate_vectors(
            all_vectors,
            expected_count=len(chunks),
        )

        return cls(
            chunks=chunks,
            vectors_by_chunk_id=(
                vectors_by_chunk_id
            ),
            backend=backend,
            cache=cache,
            cache_version=cache_version,
            stats=DensePreparationStats(
                cache_hits=(
                    len(chunks)
                    - len(missing_chunks)
                ),
                cache_misses=len(
                    missing_chunks
                ),
                embedding_document_calls=(
                    document_calls
                ),
                dimensions=dimensions,
            ),
        )

    def rank(
        self,
        *,
        query: str,
        min_similarity: float,
        max_hits: int,
        required: bool,
    ) -> tuple[
        list[ChannelHit],
        DenseRetrievalReport,
    ]:
        if not query.strip():
            raise ValueError(
                "Dense query 不能为空"
            )
        if not 0 <= min_similarity <= 1:
            raise ValueError(
                "min_similarity 必须位于 [0, 1]"
            )
        if max_hits < 1:
            raise ValueError(
                "dense max_hits 必须大于 0"
            )

        query_hash = sha256_text(query)
        query_key = build_embedding_cache_key(
            identity=self.backend.identity,
            cache_version=self.cache_version,
            value_kind="query",
            content_hash=query_hash,
        )
        cached_query = self.cache.get_many(
            [query_key]
        ).get(query_key)
        query_calls = 0
        if cached_query is None:
            query_vector = (
                self.backend.embed_query(query)
            )
            query_calls = 1
            self.cache.put_many(
                identity=self.backend.identity,
                cache_version=self.cache_version,
                value_kind="query",
                values=[
                    (
                        query_key,
                        query_hash,
                        query_vector,
                    )
                ],
            )
            query_cache_hit = 0
            query_cache_miss = 1
        else:
            query_vector = cached_query
            query_cache_hit = 1
            query_cache_miss = 0

        validate_vectors(
            [query_vector],
            expected_count=1,
            expected_dimensions=(
                self.stats.dimensions
            ),
        )

        chunk_hits = []
        for chunk in self.chunks:
            similarity = cosine_similarity(
                query_vector,
                self.vectors_by_chunk_id[
                    chunk.chunk_id
                ],
            )
            # 负 cosine 没有检索价值；ChannelHit 要求非负。
            score = max(0.0, similarity)
            if score < min_similarity:
                continue
            chunk_hits.append(
                ChannelHit(
                    channel="dense",
                    file_path=chunk.file_path,
                    raw_score=score,
                    anchor_line=chunk.start_line,
                    anchor_end_line=(
                        chunk.end_line
                    ),
                    symbol=chunk.symbol,
                )
            )

        chunk_hits.sort(
            key=lambda item: (
                -item.raw_score,
                item.file_path,
                item.anchor_line,
                item.symbol or "",
            )
        )

        # RRF 的每个通道按文件排名，保留同一文件的最佳 chunk。
        best_by_file: dict[
            str,
            ChannelHit,
        ] = {}
        for hit in chunk_hits:
            best_by_file.setdefault(
                hit.file_path,
                hit,
            )
        hits = list(
            best_by_file.values()
        )[:max_hits]

        return hits, DenseRetrievalReport(
            enabled=True,
            required=required,
            provider_namespace=(
                self.backend
                .identity
                .provider_namespace
            ),
            model=self.backend.identity.model,
            embedding_dimensions=(
                self.stats.dimensions
            ),
            query_hash=query_hash,
            chunk_count=len(self.chunks),
            cache_hits=(
                self.stats.cache_hits
                + query_cache_hit
            ),
            cache_misses=(
                self.stats.cache_misses
                + query_cache_miss
            ),
            embedding_document_calls=(
                self.stats.embedding_document_calls
            ),
            embedding_query_calls=query_calls,
            hits=hits,
        )
```

这里的 `max_hits` 是 Dense 通道进入 RRF 前的文件数，不是最终 Evidence Pack 的 `top_k`。

数据规模：

```text
N 个 chunk，D 维向量
单次 query 穷举复杂度约 O(N * D)
```

第一版先通过评测记录真实耗时。只有超过预算后才需要 ANN Vector Database。

---

## 十四、把 Dense 通道接入 RRF

> **本节类型：需要修改项目代码。**
>
> **需要修改：** `app/retrieval/ranking.py`

### 14.1 增加通道权重和 anchor 优先级

将两个常量改为：

```python
DEFAULT_CHANNEL_WEIGHTS: dict[
    RetrievalChannel,
    float,
] = {
    "traceback": 3.0,
    "symbol": 2.4,
    "dense": 2.1,
    "keyword": 2.0,
    "import_graph": 1.7,
    "cli_config": 1.6,
    "path": 1.2,
    "bm25": 1.0,
}

_ANCHOR_PRIORITY: dict[
    RetrievalChannel,
    int,
] = {
    "traceback": 8,
    "symbol": 7,
    "dense": 6,
    "keyword": 5,
    "cli_config": 4,
    "import_graph": 3,
    "path": 2,
    "bm25": 1,
}
```

精确 symbol 仍然高于 Dense，traceback 仍然最高。Dense 的作用是补充语义召回，不覆盖确定性强证据。

### 14.2 完整替换 build_channel_rankings

```python
def build_channel_rankings(
    index: RepositoryIndex,
    *,
    query: str,
    keywords: list[str],
    preferred_paths: list[str] | None = None,
    dense_hits: list[ChannelHit] | None = None,
) -> dict[
    RetrievalChannel,
    list[ChannelHit],
]:
    symbol_hits = rank_symbol(
        index,
        query=query,
        keywords=keywords,
    )
    return {
        "traceback": rank_traceback_paths(
            index,
            preferred_paths=(
                preferred_paths or []
            ),
        ),
        "symbol": symbol_hits,
        "dense": list(dense_hits or []),
        "keyword": rank_keyword(
            index,
            query=query,
            keywords=keywords,
        ),
        "import_graph": rank_import_graph(
            index,
            symbol_hits=symbol_hits,
            query=query,
            keywords=keywords,
        ),
        "cli_config": rank_cli_config(
            index,
            query=query,
            keywords=keywords,
        ),
        "path": rank_path(
            index,
            query=query,
            keywords=keywords,
        ),
        "bm25": rank_bm25(
            index,
            query=query,
            keywords=keywords,
        ),
    }
```

`fuse_rankings()` 不需要修改。它已经能够处理任意 `RetrievalChannel` 排名。

---

## 十五、让 Evidence Pack 接收 Dense Hits

> **本节类型：需要修改项目代码。**
>
> **需要修改：** `app/retrieval/service.py`

在 `build_evidence_pack()` 参数最后增加：

```python
def build_evidence_pack(
    *,
    repo_path: str | Path,
    query: str,
    keywords: list[str],
    index: RepositoryIndex | None = None,
    index_version: str = "phase20-v1",
    max_file_bytes: int = 1024 * 1024,
    top_k: int = 8,
    context_lines: int = 20,
    max_span_lines: int = 120,
    rrf_k: int = 60,
    preferred_paths: list[str] | None = None,
    dense_hits: list[ChannelHit] | None = None,
) -> tuple[RepositoryIndex, EvidencePack]:
```

同时在文件顶部的 schema import 中增加：

```python
from app.retrieval.schemas import (
    ChannelHit,
    CodeEvidence,
    EvidencePack,
    FusedCandidate,
    RepositoryIndex,
    RetrievalSignal,
)
```

把原来的：

```python
    rankings = build_channel_rankings(
        active_index,
        query=query,
        keywords=normalized_keywords,
        preferred_paths=preferred_paths,
    )
```

替换为：

```python
    rankings = build_channel_rankings(
        active_index,
        query=query,
        keywords=normalized_keywords,
        preferred_paths=preferred_paths,
        dense_hits=dense_hits,
    )
```

其余 `build_evidence_pack()` 不变。Dense 命中的：

```text
anchor_line
anchor_end_line
symbol
raw_score
```

会进入现有 `RetrievalSignal`，最终 snippet 会围绕 Dense chunk，而不是文件开头。

---

## 十六、更新 retrieval 包入口

> **本节类型：需要完整替换项目代码。**
>
> **需要替换：** `app/retrieval/__init__.py`

完整文件：

```python
from app.retrieval.chunking import (
    build_semantic_chunks,
)
from app.retrieval.dense import (
    PreparedDenseRetriever,
    cosine_similarity,
)
from app.retrieval.embedding_backend import (
    EmbeddingBackend,
    EmbeddingProviderError,
    get_embedding_backend,
)
from app.retrieval.embedding_cache import (
    SQLiteEmbeddingCache,
)
from app.retrieval.indexer import (
    build_repository_index,
    load_repository_index,
)
from app.retrieval.query_builder import (
    build_lexical_query,
    build_semantic_query,
)
from app.retrieval.schemas import (
    CodeEvidence,
    DenseRetrievalReport,
    EvidencePack,
    RepositoryIndex,
    SemanticIndexManifest,
)
from app.retrieval.service import (
    build_evidence_pack,
    validate_code_evidence,
)

__all__ = [
    "CodeEvidence",
    "DenseRetrievalReport",
    "EmbeddingBackend",
    "EmbeddingProviderError",
    "EvidencePack",
    "PreparedDenseRetriever",
    "RepositoryIndex",
    "SQLiteEmbeddingCache",
    "SemanticIndexManifest",
    "build_evidence_pack",
    "build_lexical_query",
    "build_repository_index",
    "build_semantic_chunks",
    "build_semantic_query",
    "cosine_similarity",
    "get_embedding_backend",
    "load_repository_index",
    "validate_code_evidence",
]
```

---

## 十七、增加配置和环境变量

> **本节类型：需要修改项目代码和配置。**
>
> **需要修改：**
>
> - `app/config.py`
> - `.env.example`
> - `pyproject.toml`

### 17.1 修改 app/config.py

在 Phase 20 retrieval 配置后、`settings = Settings()` 前增加：

```python
    # 默认关闭：开启后会构造 semantic chunks。
    enable_dense_retrieval: bool = _env_bool(
        "ENABLE_DENSE_RETRIEVAL",
        False,
    )

    # required=true 时，Dense 失败不允许静默降级。
    dense_retrieval_required: bool = _env_bool(
        "DENSE_RETRIEVAL_REQUIRED",
        False,
    )

    # 远程源码上传必须单独明确授权。
    allow_code_embedding_upload: bool = _env_bool(
        "ALLOW_CODE_EMBEDDING_UPLOAD",
        False,
    )

    embedding_timeout_seconds: float = float(
        os.getenv(
            "EMBEDDING_TIMEOUT_SECONDS",
            "60",
        )
    )

    embedding_max_retries: int = int(
        os.getenv(
            "EMBEDDING_MAX_RETRIES",
            "2",
        )
    )

    embedding_batch_size: int = int(
        os.getenv(
            "EMBEDDING_BATCH_SIZE",
            "32",
        )
    )

    embedding_cache_db_path: Path = Path(
        os.getenv(
            "EMBEDDING_CACHE_DB_PATH",
            "cache/embeddings.sqlite",
        )
    )

    embedding_cache_version: str = os.getenv(
        "EMBEDDING_CACHE_VERSION",
        "phase21-v1",
    )

    semantic_chunk_policy_version: str = os.getenv(
        "SEMANTIC_CHUNK_POLICY_VERSION",
        "phase21-v1",
    )

    semantic_chunk_max_lines: int = int(
        os.getenv(
            "SEMANTIC_CHUNK_MAX_LINES",
            "80",
        )
    )

    semantic_chunk_overlap_lines: int = int(
        os.getenv(
            "SEMANTIC_CHUNK_OVERLAP_LINES",
            "16",
        )
    )

    semantic_max_chunks: int = int(
        os.getenv(
            "SEMANTIC_MAX_CHUNKS",
            "5000",
        )
    )

    semantic_query_max_chars: int = int(
        os.getenv(
            "SEMANTIC_QUERY_MAX_CHARS",
            "6000",
        )
    )

    dense_min_similarity: float = float(
        os.getenv(
            "DENSE_MIN_SIMILARITY",
            "0.20",
        )
    )

    dense_max_hits: int = int(
        os.getenv(
            "DENSE_MAX_HITS",
            "40",
        )
    )
```

在文件底部增加 cache 目录创建：

```python
settings = Settings()
settings.runs_dir.mkdir(
    parents=True,
    exist_ok=True,
)
settings.checkpoint_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
settings.patch_coordination_dir.mkdir(
    parents=True,
    exist_ok=True,
)
settings.embedding_cache_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
```

如果你原文件底部已有前三个 `mkdir`，只增加最后一项，不要重复整段。

### 17.2 修改 .env.example

在 Embedding 配置后增加：

```dotenv
# 默认不发送源码。只有确认仓库和 Provider 策略后才同时开启。
ENABLE_DENSE_RETRIEVAL=false
DENSE_RETRIEVAL_REQUIRED=false
ALLOW_CODE_EMBEDDING_UPLOAD=false

EMBEDDING_TIMEOUT_SECONDS=60
EMBEDDING_MAX_RETRIES=2
EMBEDDING_BATCH_SIZE=32
EMBEDDING_CACHE_DB_PATH=cache/embeddings.sqlite
EMBEDDING_CACHE_VERSION=phase21-v1

SEMANTIC_CHUNK_POLICY_VERSION=phase21-v1
SEMANTIC_CHUNK_MAX_LINES=80
SEMANTIC_CHUNK_OVERLAP_LINES=16
SEMANTIC_MAX_CHUNKS=5000
SEMANTIC_QUERY_MAX_CHARS=6000

DENSE_MIN_SIMILARITY=0.20
DENSE_MAX_HITS=40
```

生产 `.env` 中不要照抄 `ALLOW_CODE_EMBEDDING_UPLOAD=true`。需要由仓库所有者确认后单独修改。

### 17.3 修改 .gitignore

增加：

```gitignore
# Phase 21 shared Embedding cache and SQLite side files
cache/embeddings.sqlite*
```

向量 cache 可以重建，不应提交到 Git。run-native manifest 和 dense report 仍由 Artifact 系统保存。

### 17.4 收紧 langchain-openai 兼容范围

本教程中的 `OpenAIEmbeddings` 构造参数已在项目当前安装的 `langchain-openai 1.3.2` 上验证。把 `pyproject.toml` 中：

```toml
"langchain-openai>=0.2",
```

改为：

```toml
"langchain-openai>=1.3,<2",
```

然后在 Agent 环境中安装项目依赖：

```bash
python -m pip install -e ".[dev]"
```

不要在论文复现环境中安装这些 Agent 依赖；继续保持 Agent 环境和论文环境隔离。

---

## 十八、扩展 Graph State

> **本节类型：需要修改项目代码。**
>
> **需要修改：** `app/state.py`

在 Phase 20 retrieval 字段之后增加：

```python
    # CLI 可以对单次运行覆盖是否启用 Dense；
    # 远程上传授权不能由 LLM 或 state 覆盖，只读取 Settings。
    enable_dense_retrieval: bool
    dense_retrieval_required: bool

    # Manifest 不含源码正文和向量。
    semantic_index_manifest_path: Optional[str]

    # module_name -> DenseRetrievalReport Artifact 路径。
    dense_retrieval_report_paths: dict[str, str]
```

不要把以下对象放入 State：

```text
PreparedDenseRetriever
EmbeddingBackend client
全部 chunk text
全部 vectors
SQLite connection
```

这些对象不可安全序列化，也会让 checkpoint 膨胀。

---

## 十九、完整升级 code_search_node

> **本节类型：需要完整替换项目代码。**
>
> **需要替换：** `app/nodes/code_search_node.py`

完整文件：

```python
from __future__ import annotations

import re

from app.config import settings
from app.retrieval import (
    EmbeddingProviderError,
    PreparedDenseRetriever,
    SQLiteEmbeddingCache,
    build_evidence_pack,
    build_lexical_query,
    build_repository_index,
    build_semantic_chunks,
    build_semantic_query,
    get_embedding_backend,
)
from app.retrieval.schemas import (
    DenseRetrievalReport,
)
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
)
from app.tools.error_tools import (
    stage_error_result,
)
from app.tools.search_tools import (
    SearchToolError,
)


def _slug(value: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        value.casefold(),
    ).strip("-")
    return (slug or "module")[:60]


def _legacy_search_result(
    pack: dict,
) -> dict:
    """保持旧 mapping/report fixture 可读取。"""

    items = list(pack.get("items") or [])
    return {
        "keywords": list(
            pack.get("keywords") or []
        ),
        "matches": [
            {
                "file_path": item["file_path"],
                "line": item["start_line"],
                "text": (
                    item["text"].splitlines()[0]
                    if item.get("text")
                    else ""
                ),
                "keyword": "hybrid",
            }
            for item in items
        ],
        "candidate_files": [
            item["file_path"]
            for item in items
        ],
        "code_slices": [
            {
                "file_path": item["file_path"],
                "content": item["text"],
            }
            for item in items
        ],
    }


def _dense_flags(
    state: dict,
) -> tuple[bool, bool]:
    enabled = bool(
        state.get(
            "enable_dense_retrieval",
            settings.enable_dense_retrieval,
        )
    )
    required = bool(
        state.get(
            "dense_retrieval_required",
            settings.dense_retrieval_required,
        )
    )
    # required 本身意味着用户要求启用。
    return enabled or required, required


def _prepare_dense(
    *,
    repo_path: str,
    index,
) -> tuple[
    PreparedDenseRetriever,
    dict,
]:
    if not settings.allow_code_embedding_upload:
        raise EmbeddingProviderError(
            "Dense Retrieval 已开启，但 "
            "ALLOW_CODE_EMBEDDING_UPLOAD=false"
        )

    chunks, manifest = build_semantic_chunks(
        repo_path=repo_path,
        index=index,
        chunk_policy_version=(
            settings
            .semantic_chunk_policy_version
        ),
        max_lines=(
            settings.semantic_chunk_max_lines
        ),
        overlap_lines=(
            settings
            .semantic_chunk_overlap_lines
        ),
        max_chunks=settings.semantic_max_chunks,
    )
    backend = get_embedding_backend()
    cache = SQLiteEmbeddingCache(
        settings.embedding_cache_db_path
    )
    retriever = PreparedDenseRetriever.prepare(
        chunks=chunks,
        backend=backend,
        cache=cache,
        cache_version=(
            settings.embedding_cache_version
        ),
        batch_size=settings.embedding_batch_size,
    )
    return (
        retriever,
        manifest.model_dump(mode="json"),
    )


def _fallback_report(
    *,
    enabled: bool,
    required: bool,
    reason: str | None,
) -> DenseRetrievalReport:
    return DenseRetrievalReport(
        enabled=enabled,
        required=required,
        fallback_reason=reason,
    )


def code_search_node(
    state: dict,
) -> dict:
    repo_path = state.get("repo_path")
    modules = list(
        state.get("method_modules") or []
    )
    if not repo_path:
        return stage_error_result(
            state=state,
            stage="code_search",
            code="REPO_PATH_REQUIRED",
            category="user",
            message=(
                "代码检索必须提供 repo_path"
            ),
            extra_update={
                "code_search_results": {},
                "code_evidence_packs": {},
            },
        )
    if not modules:
        return stage_error_result(
            state=state,
            stage="code_search",
            code="METHOD_MODULES_REQUIRED",
            category="agent",
            message=(
                "代码检索需要 method_modules"
            ),
            extra_update={
                "code_search_results": {},
                "code_evidence_packs": {},
            },
        )

    try:
        index = build_repository_index(
            repo_path,
            index_version=(
                settings.retrieval_index_version
            ),
            max_file_bytes=(
                settings.retrieval_max_file_bytes
            ),
        )
    except (
        FileNotFoundError,
        OSError,
    ) as exc:
        return stage_error_result(
            state=state,
            stage="code_search",
            code="REPO_INDEX_FAILED",
            category="environment",
            message=str(exc),
            extra_update={
                "code_search_results": {},
                "code_evidence_packs": {},
            },
        )

    index_path, index_record = (
        write_json_artifact(
            state=state,
            relative_path=(
                "analysis/retrieval/"
                "repo_index.json"
            ),
            payload=index.model_dump(
                mode="json"
            ),
            producer_node="code_search",
        )
    )

    dense_enabled, dense_required = (
        _dense_flags(state)
    )
    dense_retriever = None
    dense_fallback_reason = None
    semantic_manifest_path = None
    records = [index_record]

    if dense_enabled:
        if not settings.allow_code_embedding_upload:
            dense_fallback_reason = (
                "Dense Retrieval 已开启，但 "
                "ALLOW_CODE_EMBEDDING_UPLOAD=false"
            )
            if dense_required:
                return stage_error_result(
                    state=state,
                    stage="code_search",
                    code=(
                        "DENSE_UPLOAD_NOT_ALLOWED"
                    ),
                    category="user",
                    message=(
                        dense_fallback_reason
                    ),
                    extra_update={
                        "repo_index_path": str(
                            index_path
                        ),
                        **artifact_state_update(
                            state,
                            records,
                        ),
                    },
                )
        else:
            try:
                (
                    dense_retriever,
                    semantic_manifest,
                ) = _prepare_dense(
                    repo_path=str(repo_path),
                    index=index,
                )
                (
                    manifest_path,
                    manifest_record,
                ) = write_json_artifact(
                    state=state,
                    relative_path=(
                        "analysis/retrieval/"
                        "semantic_index_manifest.json"
                    ),
                    payload=semantic_manifest,
                    producer_node="code_search",
                )
                semantic_manifest_path = str(
                    manifest_path
                )
                records.append(manifest_record)
            except (
                EmbeddingProviderError,
                OSError,
                ValueError,
            ) as exc:
                dense_fallback_reason = (
                    f"{type(exc).__name__}: {exc}"
                )
                if dense_required:
                    return stage_error_result(
                        state=state,
                        stage="code_search",
                        code=(
                            "DENSE_PREPARATION_FAILED"
                        ),
                        category="provider",
                        message=(
                            dense_fallback_reason
                        ),
                        extra_update={
                            "repo_index_path": str(
                                index_path
                            ),
                            "code_search_results": {},
                            "code_evidence_packs": {},
                            **artifact_state_update(
                                state,
                                records,
                            ),
                        },
                    )

    packs: dict[str, dict] = {}
    pack_paths: dict[str, str] = {}
    dense_report_paths: dict[str, str] = {}
    legacy_results: dict[str, dict] = {}

    for position, module in enumerate(
        modules
    ):
        module_name = str(
            module.get("name")
            or f"unnamed_module_{position}"
        )
        module_payload = {
            **module,
            "name": module_name,
        }
        keywords = [
            module_name,
            *[
                str(value)
                for value in (
                    module.get(
                        "possible_keywords"
                    )
                    or []
                )
            ],
        ]
        lexical_query = build_lexical_query(
            module_payload
        )
        dense_hits = []

        if dense_retriever is not None:
            try:
                semantic_query = (
                    build_semantic_query(
                        module_payload,
                        max_chars=(
                            settings
                            .semantic_query_max_chars
                        ),
                    )
                )
                (
                    dense_hits,
                    dense_report,
                ) = dense_retriever.rank(
                    query=semantic_query,
                    min_similarity=(
                        settings
                        .dense_min_similarity
                    ),
                    max_hits=(
                        settings.dense_max_hits
                    ),
                    required=dense_required,
                )
            except (
                EmbeddingProviderError,
                OSError,
                ValueError,
            ) as exc:
                reason = (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )
                if dense_required:
                    return stage_error_result(
                        state=state,
                        stage="code_search",
                        code=(
                            "DENSE_QUERY_FAILED"
                        ),
                        category="provider",
                        message=(
                            f"{module_name}: "
                            f"{reason}"
                        ),
                        extra_update={
                            "code_search_results": (
                                legacy_results
                            ),
                            "code_evidence_packs": (
                                packs
                            ),
                            **artifact_state_update(
                                state,
                                records,
                            ),
                        },
                    )
                dense_report = (
                    _fallback_report(
                        enabled=True,
                        required=False,
                        reason=reason,
                    )
                )
        else:
            dense_report = _fallback_report(
                enabled=dense_enabled,
                required=dense_required,
                reason=dense_fallback_reason,
            )

        dense_relative_path = (
            "analysis/retrieval/dense_reports/"
            f"{position:02d}_"
            f"{_slug(module_name)}.json"
        )
        (
            dense_report_path,
            dense_report_record,
        ) = write_json_artifact(
            state=state,
            relative_path=(
                dense_relative_path
            ),
            payload=dense_report.model_dump(
                mode="json"
            ),
            producer_node="code_search",
        )
        dense_report_paths[module_name] = str(
            dense_report_path
        )
        records.append(
            dense_report_record
        )

        try:
            _, pack = build_evidence_pack(
                repo_path=repo_path,
                query=lexical_query,
                keywords=keywords,
                index=index,
                index_version=(
                    settings
                    .retrieval_index_version
                ),
                max_file_bytes=(
                    settings
                    .retrieval_max_file_bytes
                ),
                top_k=(
                    settings.retrieval_top_k
                ),
                context_lines=(
                    settings
                    .retrieval_context_lines
                ),
                max_span_lines=(
                    settings
                    .retrieval_max_span_lines
                ),
                rrf_k=settings.retrieval_rrf_k,
                dense_hits=dense_hits,
            )
        except (
            SearchToolError,
            OSError,
            ValueError,
        ) as exc:
            return stage_error_result(
                state=state,
                stage="code_search",
                code=(
                    "HYBRID_RETRIEVAL_FAILED"
                ),
                category="environment",
                message=(
                    f"{module_name}: {exc}"
                ),
                extra_update={
                    "code_search_results": (
                        legacy_results
                    ),
                    "code_evidence_packs": packs,
                    **artifact_state_update(
                        state,
                        records,
                    ),
                },
            )

        pack_payload = pack.model_dump(
            mode="json"
        )
        relative_path = (
            "analysis/retrieval/evidence_packs/"
            f"{position:02d}_"
            f"{_slug(module_name)}.json"
        )
        pack_path, pack_record = (
            write_json_artifact(
                state=state,
                relative_path=relative_path,
                payload=pack_payload,
                producer_node="code_search",
            )
        )
        packs[module_name] = pack_payload
        pack_paths[module_name] = str(
            pack_path
        )
        legacy_results[module_name] = (
            _legacy_search_result(
                pack_payload
            )
        )
        records.append(pack_record)

    return {
        "repo_index_path": str(index_path),
        "semantic_index_manifest_path": (
            semantic_manifest_path
        ),
        "dense_retrieval_report_paths": (
            dense_report_paths
        ),
        "code_evidence_pack_paths": (
            pack_paths
        ),
        "code_evidence_packs": packs,
        "code_search_results": legacy_results,
        **artifact_state_update(
            state,
            records,
        ),
    }
```

关键降级语义：

```text
enabled=false：
    Dense report.enabled=false，Phase 20 行为不变。

enabled=true + required=false + Provider 失败：
    Dense report 记录 fallback，Sparse Hybrid 继续。

required=true + Provider 失败：
    code_search 终止，不能声称运行了 Dense。
```

远程上传授权只从 `settings.allow_code_embedding_upload` 读取，不能让 LLM 通过 Graph state 将它改成 true。

每个 module 的 Dense report 都会带上本次共享 document preparation 统计。不要把多个 report 的 `embedding_document_calls` 简单相加；它们描述的是同一个 `PreparedDenseRetriever`。任务级总调用量可在后续 Job Runtime/telemetry 阶段单独汇总。

---

## 二十、增加 Embedding Probe 并升级 retrieve-code CLI

> **本节类型：需要修改项目代码。**
>
> **需要修改：** `app/main.py`

### 20.1 增加 import

在 retrieval 相关 import 中增加：

```python
from app.retrieval import (
    cosine_similarity,
    get_embedding_backend,
)
```

### 20.2 增加无源码 Probe

放在 `retrieve-code` 命令前：

```python
@app.command("probe-embedding")
def probe_embedding():
    """
    只发送两句无敏感测试文本，不读取或上传代码仓库。
    """

    backend = get_embedding_backend()
    vectors = backend.embed_documents(
        [
            "spatial temporal feature aggregation",
            "database transaction retry policy",
        ]
    )
    similarity = cosine_similarity(
        vectors[0],
        vectors[1],
    )
    print(
        {
            "provider_namespace": (
                backend
                .identity
                .provider_namespace
            ),
            "model": backend.identity.model,
            "dimensions": len(vectors[0]),
            "probe_similarity": similarity,
        }
    )
```

这个命令用于确认：

```text
API key
Base URL
模型名
向量维度
Provider 网络
```

不用于评测代码检索质量。

### 20.3 完整替换 retrieve_code 函数

```python
@app.command("retrieve-code")
def retrieve_code(
    repo_path: str,
    query: str,
    keyword: list[str] | None = typer.Option(
        None,
        "--keyword",
        "-k",
        help="可重复传入的精确检索词",
    ),
    dense: bool = typer.Option(
        False,
        "--dense/--no-dense",
        help=(
            "启用 Dense Retrieval；仍要求环境变量"
            " ALLOW_CODE_EMBEDDING_UPLOAD=true"
        ),
    ),
    require_dense: bool = typer.Option(
        False,
        "--require-dense/--allow-dense-fallback",
        help="Dense 失败时是否禁止降级 Sparse Hybrid",
    ),
):
    """
    运行 Hybrid Code Retrieval。

    --dense=false：
        不调用 Provider。

    --dense=true：
        可能把脱敏后的代码 chunk 发送给 Embedding Provider。
    """

    dense = dense or require_dense
    module_name = "ad_hoc_retrieval"
    state = _initialize_cli_run(
        task_id="retrieve-code",
        values={
            "repo_path": repo_path,
            "enable_dense_retrieval": dense,
            "dense_retrieval_required": (
                require_dense
            ),
            "method_modules": [
                {
                    "name": module_name,
                    "description": query,
                    "possible_keywords": (
                        keyword or []
                    ),
                    "evidence": [],
                }
            ],
        },
    )
    state = _run_cli_pipeline(
        state,
        [
            ("repo_scan", repo_scan_node),
            ("code_search", code_search_node),
        ],
    )

    pack = (
        state.get(
            "code_evidence_packs",
            {},
        ).get(module_name, {})
    )
    print("[bold]Hybrid code retrieval[/bold]")
    print(
        {
            "run_id": state.get("run_id"),
            "run_dir": state.get("run_dir"),
            "final_status": state.get(
                "final_status"
            ),
            "dense_requested": dense,
            "dense_required": require_dense,
            "repo_index_path": state.get(
                "repo_index_path"
            ),
            "semantic_index_manifest_path": (
                state.get(
                    "semantic_index_manifest_path"
                )
            ),
            "dense_report_path": (
                state.get(
                    "dense_retrieval_report_paths",
                    {},
                ).get(module_name)
            ),
            "evidence_pack_path": (
                state.get(
                    "code_evidence_pack_paths",
                    {},
                ).get(module_name)
            ),
        }
    )

    for rank, item in enumerate(
        pack.get("items", []),
        start=1,
    ):
        print(
            {
                "rank": rank,
                "file_path": item.get(
                    "file_path"
                ),
                "symbol": item.get("symbol"),
                "lines": (
                    f"{item.get('start_line')}-"
                    f"{item.get('end_line')}"
                ),
                "channels": item.get(
                    "retrieval_channels",
                    [],
                ),
                "score": item.get(
                    "fused_score"
                ),
                "evidence_id": item.get(
                    "evidence_id"
                ),
            }
        )

    if has_terminal_stage_error(state):
        raise typer.Exit(code=1)
```

---

## 二十一、扩展评测 Schema

> **本节类型：需要修改项目代码。**
>
> **需要修改：** `app/evaluation/schemas.py`

正式评测使用 `app.evaluation.schemas`。`app/schemas.py` 中仍有一套早期遗留 Eval 类型，本阶段不要在两处重复增加 runner；后续应单独清理遗留定义。

### 21.1 增加 runner

```python
EvalRunnerKind = Literal[
    "fixture",
    "route_function",
    "live_graph",
    "paper_parser",
    "code_retrieval",
    "semantic_code_retrieval",
]
```

### 21.2 增加 Embedding 效率预算

在 `EvalExpected` 的效率字段中增加：

```python
    max_duration_ms: float | None = Field(
        default=None,
        ge=0,
    )
    max_llm_calls: int | None = Field(
        default=None,
        ge=0,
    )

    max_embedding_document_calls: int | None = Field(
        default=None,
        ge=0,
    )
    max_embedding_query_calls: int | None = Field(
        default=None,
        ge=0,
    )
    min_embedding_cache_hit_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    max_human_interventions: int | None = Field(
        default=None,
        ge=0,
    )
```

完整替换 `EvalMetrics`：

```python
class EvalMetrics(EvalModel):
    duration_ms: float = Field(
        default=0,
        ge=0,
    )
    llm_calls: int = Field(default=0, ge=0)
    human_interventions: int = Field(
        default=0,
        ge=0,
    )
    tool_calls: int = Field(default=0, ge=0)

    embedding_document_calls: int = Field(
        default=0,
        ge=0,
    )
    embedding_query_calls: int = Field(
        default=0,
        ge=0,
    )
    embedding_cache_hits: int = Field(
        default=0,
        ge=0,
    )
    embedding_cache_misses: int = Field(
        default=0,
        ge=0,
    )
```

在 `EvalObservation` 的 `code_retrieval` 后增加：

```python
    embedding_provider_namespace: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = Field(
        default=None,
        ge=1,
    )
    dense_fallback_reason: str | None = None
```

### 21.3 限制 semantic runner

在 `EvalCase.validate_runner_input()` 中增加：

```python
        if self.runner == "semantic_code_retrieval":
            if self.suite != "provider":
                raise ValueError(
                    "semantic_code_retrieval 必须放入 "
                    "provider suite"
                )
            if (
                not self.input.repo_path
                or not self.input.retrieval_query
            ):
                raise ValueError(
                    "semantic_code_retrieval 要求 "
                    "repo_path 和 retrieval_query"
                )
```

Provider suite 的原因是这个 runner 会发起真实 Embedding 网络调用。普通离线评测只能使用 Fake Backend 的单元测试。

---

## 二十二、实现 semantic_code_retrieval Runner

> **本节类型：需要修改项目代码。**
>
> **需要修改：** `app/evaluation/runners.py`

### 22.1 增加 import

```python
from app.retrieval import (
    PreparedDenseRetriever,
    SQLiteEmbeddingCache,
    build_evidence_pack,
    build_repository_index,
    build_semantic_chunks,
    get_embedding_backend,
)
```

如果文件已经分别 import 了 `build_repository_index` 或 `build_evidence_pack`，合并 import，不要保留重复名称。

### 22.2 增加 runner

放在 `run_code_retrieval_case()` 后：

```python
def run_semantic_code_retrieval_case(
    case: EvalCase,
) -> EvalObservation:
    """
    运行真实 Embedding Provider。

    只在显式选择 provider case 时执行。
    """

    if case.suite != "provider":
        raise ValueError(
            "semantic_code_retrieval "
            "case must use provider suite"
        )
    if (
        not case.input.repo_path
        or not case.input.retrieval_query
    ):
        raise ValueError(
            "semantic_code_retrieval requires "
            "repo_path and retrieval_query"
        )
    if not settings.allow_code_embedding_upload:
        raise ValueError(
            "Provider eval 要求 "
            "ALLOW_CODE_EMBEDDING_UPLOAD=true"
        )

    repo_path = _resolve_eval_repo_path(
        case.input.repo_path
    )
    started = time.perf_counter()
    index = build_repository_index(
        repo_path,
        index_version=(
            settings.retrieval_index_version
        ),
        max_file_bytes=(
            settings.retrieval_max_file_bytes
        ),
    )
    chunks, _ = build_semantic_chunks(
        repo_path=repo_path,
        index=index,
        chunk_policy_version=(
            settings
            .semantic_chunk_policy_version
        ),
        max_lines=(
            settings.semantic_chunk_max_lines
        ),
        overlap_lines=(
            settings
            .semantic_chunk_overlap_lines
        ),
        max_chunks=settings.semantic_max_chunks,
    )
    retriever = PreparedDenseRetriever.prepare(
        chunks=chunks,
        backend=get_embedding_backend(),
        cache=SQLiteEmbeddingCache(
            settings.embedding_cache_db_path
        ),
        cache_version=(
            settings.embedding_cache_version
        ),
        batch_size=settings.embedding_batch_size,
    )
    dense_hits, dense_report = retriever.rank(
        query=case.input.retrieval_query,
        min_similarity=(
            settings.dense_min_similarity
        ),
        max_hits=settings.dense_max_hits,
        required=True,
    )
    _, pack = build_evidence_pack(
        repo_path=repo_path,
        query=case.input.retrieval_query,
        keywords=(
            case.input.retrieval_keywords
        ),
        index=index,
        index_version=(
            settings.retrieval_index_version
        ),
        max_file_bytes=(
            settings.retrieval_max_file_bytes
        ),
        top_k=settings.retrieval_top_k,
        context_lines=(
            settings.retrieval_context_lines
        ),
        max_span_lines=(
            settings.retrieval_max_span_lines
        ),
        rrf_k=settings.retrieval_rrf_k,
        dense_hits=dense_hits,
    )
    duration_ms = (
        time.perf_counter() - started
    ) * 1000

    observations = []
    for rank, item in enumerate(
        pack.items,
        start=1,
    ):
        observations.append(
            CodeRetrievalObservation(
                rank=rank,
                file_path=item.file_path,
                symbol=item.symbol,
                retrieval_channels=list(
                    item.retrieval_channels
                ),
                fused_score=item.fused_score,
                evidence_id=item.evidence_id,
                repo_revision=(
                    item.repo_revision
                ),
                repo_fingerprint=(
                    item.repo_fingerprint
                ),
                file_sha256=item.file_sha256,
                start_line=item.start_line,
                end_line=item.end_line,
                content_hash=item.content_hash,
                provenance_complete=bool(
                    item.evidence_id
                    and item.repo_fingerprint
                    and item.file_sha256
                    and item.content_hash
                    and (
                        item.start_line
                        <= item.end_line
                    )
                ),
            )
        )

    return EvalObservation(
        case_id=case.case_id,
        runner="semantic_code_retrieval",
        route=[
            "repository_index",
            "semantic_chunking",
            "embedding_provider",
            "dense_hybrid_retrieval",
        ],
        final_status="succeeded",
        code_retrieval=observations,
        embedding_provider_namespace=(
            dense_report.provider_namespace
        ),
        embedding_model=dense_report.model,
        embedding_dimensions=(
            dense_report.embedding_dimensions
        ),
        dense_fallback_reason=(
            dense_report.fallback_reason
        ),
        metrics=EvalMetrics(
            duration_ms=duration_ms,
            embedding_document_calls=(
                dense_report
                .embedding_document_calls
            ),
            embedding_query_calls=(
                dense_report
                .embedding_query_calls
            ),
            embedding_cache_hits=(
                dense_report.cache_hits
            ),
            embedding_cache_misses=(
                dense_report.cache_misses
            ),
        ),
    )
```

### 22.3 接入 run_case

在 `code_retrieval` 分支之后增加：

```python
    elif case.runner == "semantic_code_retrieval":
        observation = (
            run_semantic_code_retrieval_case(
                case
            )
        )
```

---

## 二十三、扩展 Efficiency Scorer

> **本节类型：需要修改项目代码。**
>
> **需要修改：** `app/evaluation/scorers.py`

完整替换 `score_efficiency()`：

```python
def score_efficiency(
    case: EvalCase,
    actual: EvalObservation,
) -> ScorerResult:
    expected, items = case.expected, []
    checks = [
        (
            "DURATION",
            expected.max_duration_ms,
            actual.metrics.duration_ms,
        ),
        (
            "LLM_CALLS",
            expected.max_llm_calls,
            actual.metrics.llm_calls,
        ),
        (
            "EMBEDDING_DOCUMENT_CALLS",
            (
                expected
                .max_embedding_document_calls
            ),
            (
                actual
                .metrics
                .embedding_document_calls
            ),
        ),
        (
            "EMBEDDING_QUERY_CALLS",
            (
                expected
                .max_embedding_query_calls
            ),
            (
                actual
                .metrics
                .embedding_query_calls
            ),
        ),
        (
            "HUMAN",
            (
                expected
                .max_human_interventions
            ),
            (
                actual
                .metrics
                .human_interventions
            ),
        ),
    ]
    for code, maximum, value in checks:
        if maximum is not None:
            items.append(
                _assertion(
                    f"EFFICIENCY_{code}",
                    value <= maximum,
                    "效率指标不超过预算",
                    maximum,
                    value,
                )
            )

    if (
        expected.min_embedding_cache_hit_ratio
        is not None
    ):
        hits = (
            actual.metrics.embedding_cache_hits
        )
        misses = (
            actual.metrics.embedding_cache_misses
        )
        ratio = (
            hits / (hits + misses)
            if hits + misses
            else 0.0
        )
        items.append(
            _assertion(
                "EFFICIENCY_EMBEDDING_CACHE_HIT_RATIO",
                ratio
                >= expected
                .min_embedding_cache_hit_ratio,
                "Embedding cache hit ratio 达到下限",
                (
                    expected
                    .min_embedding_cache_hit_ratio
                ),
                ratio,
            )
        )

    return _finish("efficiency", items)
```

---

## 二十四、增加命名错位 Fixture 和 Provider Golden Case

> **本节类型：需要新增评测 Fixture 和 Case。**

### 24.1 增加真实语义算子

新增 `app/evaluation/fixtures/retrieval_repo/obfuscated/operator_core.py`：

```python
def collect_local_groups(
    coordinates,
    radius,
):
    """Return nearby point indices for every frame."""

    return radius_neighbors(
        coordinates,
        radius,
    )


class LocalMixer:
    """
    Aggregate geometric neighborhoods over adjacent frames.

    The deliberately generic name does not expose the paper module name.
    """

    def forward(
        self,
        frame_coordinates,
        frame_features,
    ):
        groups = collect_local_groups(
            frame_coordinates,
            radius=0.5,
        )
        motion_offsets = (
            frame_coordinates[:, 1:]
            - frame_coordinates[:, :-1]
        )
        return weighted_pool(
            frame_features,
            groups,
            motion_offsets,
        )
```

这个文件没有：

```text
PSTConv
PST convolution
point tube
```

但局部代码行为包含：

```text
空间邻域
连续帧
运动偏移
联合特征聚合
```

### 24.2 增加语义干扰文件

新增 `app/evaluation/fixtures/retrieval_repo/obfuscated/image_filter.py`：

```python
class ImageSmoother:
    """Average nearby image pixels independently in each frame."""

    def forward(self, video):
        spatial_average = video.mean(
            axis=(-1, -2),
            keepdims=True,
        )
        return video - spatial_average
```

它也有 `frame` 和 `spatial` 语义，但没有 3D point neighborhood、跨帧 motion 或联合聚合。

### 24.3 增加 Provider Case

新增 `app/evaluation/cases/provider/retrieval_obfuscated_semantics.json`：

```json
{
  "schema_version": 1,
  "case_id": "provider_retrieval_obfuscated_semantics",
  "description": "Dense Retrieval 应在命名不一致时召回局部时空点特征算子",
  "suite": "provider",
  "runner": "semantic_code_retrieval",
  "categories": [
    "evidence",
    "efficiency"
  ],
  "tags": [
    "provider",
    "embedding",
    "retrieval",
    "phase21",
    "semantic-gap"
  ],
  "problem_ids": [],
  "input": {
    "repo_path": "fixtures/retrieval_repo",
    "retrieval_query": "Locate the paper module that forms neighborhoods of 3D points over consecutive frames, models motion between adjacent frames, and jointly aggregates spatial and temporal point features.",
    "retrieval_keywords": []
  },
  "expected": {
    "required_retrieval_paths": [
      "obfuscated/operator_core.py"
    ],
    "max_retrieval_rank_by_path": {
      "obfuscated/operator_core.py": 2
    },
    "required_retrieval_channels": [
      "dense"
    ],
    "min_retrieval_provenance_ratio": 1.0,
    "max_duration_ms": 120000,
    "max_llm_calls": 0,
    "max_embedding_document_calls": 10,
    "max_embedding_query_calls": 1
  },
  "thresholds": {
    "min_overall_score": 1.0,
    "max_score_regression": 0.0
  }
}
```

Provider Case 不要求固定 cosine score。不同模型的分数分布不同，稳定契约仍然是：

```text
目标路径进入 top-k
目标最大 rank
dense 通道存在
provenance 完整
调用和耗时不超预算
```

---

## 二十五、增加 Semantic Query 测试

> **本节类型：需要新增测试代码。**
>
> **需要新增：** `tests/test_semantic_query_builder.py`

完整文件：

```python
import pytest

from app.retrieval.query_builder import (
    build_lexical_query,
    build_semantic_query,
)


def test_semantic_query_includes_paper_evidence():
    module = {
        "name": "Point tube aggregation",
        "description": (
            "Aggregate local geometry across frames"
        ),
        "possible_keywords": [
            "point tube",
            "temporal radius",
        ],
        "evidence": [
            {
                "quote_or_summary": (
                    "Neighbors are grouped in space "
                    "and time before feature pooling."
                )
            }
        ],
    }

    lexical = build_lexical_query(module)
    semantic = build_semantic_query(module)

    assert "Point tube aggregation" in lexical
    assert "Neighbors are grouped" not in lexical
    assert "module behavior:" in semantic
    assert "paper terminology:" in semantic
    assert "Neighbors are grouped" in semantic


def test_semantic_query_is_bounded():
    module = {
        "name": "module",
        "description": "behavior",
        "evidence": [
            {
                "quote_or_summary": "x" * 1000
            }
            for _ in range(20)
        ],
    }

    query = build_semantic_query(
        module,
        max_chars=300,
    )

    assert len(query) <= 300


def test_semantic_query_rejects_empty_module():
    with pytest.raises(
        ValueError,
        match="无法构造",
    ):
        build_semantic_query({})
```

---

## 二十六、增加 Semantic Chunking 测试

> **本节类型：需要新增测试代码。**
>
> **需要新增：** `tests/test_semantic_chunking.py`

完整文件：

```python
from app.retrieval.chunking import (
    build_semantic_chunks,
)
from app.retrieval.indexer import (
    build_repository_index,
)


def test_semantic_chunks_use_symbol_windows_and_redact(
    tmp_path,
):
    source = tmp_path / "operator.py"
    source.write_text(
        "\n".join(
            [
                'API_KEY = "do-not-upload-this"',
                "",
                "class LocalMixer:",
                "    def forward(self, frames):",
                "        groups = radius_neighbors(frames)",
                "        return weighted_pool(groups)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )

    chunks, manifest = build_semantic_chunks(
        repo_path=tmp_path,
        index=index,
        chunk_policy_version="test-v1",
        max_lines=8,
        overlap_lines=2,
        max_chunks=30,
    )

    assert chunks
    assert any(
        chunk.symbol == "LocalMixer.forward"
        for chunk in chunks
    )
    assert all(
        "do-not-upload-this"
        not in chunk.embedding_text
        for chunk in chunks
    )
    assert any(
        "<REDACTED>" in chunk.embedding_text
        for chunk in chunks
    )
    assert manifest.redacted_line_count == 1
    payload = manifest.model_dump(
        mode="json"
    )
    assert "embedding_text" not in str(payload)


def test_private_key_file_is_skipped(
    tmp_path,
):
    (tmp_path / "unsafe.py").write_text(
        "\n".join(
            [
                "-----BEGIN PRIVATE KEY-----",
                "private-material",
                "-----END PRIVATE KEY-----",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "safe.py").write_text(
        "def useful_operator(x):\n    return x\n",
        encoding="utf-8",
    )
    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )

    chunks, manifest = build_semantic_chunks(
        repo_path=tmp_path,
        index=index,
        chunk_policy_version="test-v1",
        max_lines=8,
        overlap_lines=0,
    )

    assert {
        chunk.file_path
        for chunk in chunks
    } == {"safe.py"}
    assert (
        "PRIVATE_KEY_FILE_SKIPPED:unsafe.py"
        in manifest.warnings
    )


def test_stale_source_is_not_embedded(
    tmp_path,
):
    path = tmp_path / "operator.py"
    path.write_text(
        "def original(x):\n    return x\n",
        encoding="utf-8",
    )
    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )
    path.write_text(
        "def changed(x):\n    return x + 1\n",
        encoding="utf-8",
    )

    chunks, manifest = build_semantic_chunks(
        repo_path=tmp_path,
        index=index,
        chunk_policy_version="test-v1",
    )

    assert chunks == []
    assert (
        "STALE_SOURCE_SKIPPED:operator.py"
        in manifest.warnings
    )
```

---

## 二十七、增加 Embedding Cache 测试

> **本节类型：需要新增测试代码。**
>
> **需要新增：** `tests/test_embedding_cache.py`

完整文件：

```python
import sqlite3

from app.retrieval.embedding_backend import (
    EmbeddingBackendIdentity,
)
from app.retrieval.embedding_cache import (
    SQLiteEmbeddingCache,
    build_embedding_cache_key,
)


def _identity() -> EmbeddingBackendIdentity:
    return EmbeddingBackendIdentity(
        provider_namespace="fake-provider",
        model="fake-model",
    )


def test_embedding_cache_round_trip(
    tmp_path,
):
    cache = SQLiteEmbeddingCache(
        tmp_path / "embeddings.sqlite"
    )
    key = build_embedding_cache_key(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        content_hash="content-hash",
    )

    cache.put_many(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        values=[
            (
                key,
                "content-hash",
                [1.0, 0.5, 0.25],
            )
        ],
    )

    assert cache.get_many([key]) == {
        key: [1.0, 0.5, 0.25]
    }


def test_cache_key_separates_query_and_document():
    document_key = build_embedding_cache_key(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        content_hash="same",
    )
    query_key = build_embedding_cache_key(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="query",
        content_hash="same",
    )

    assert document_key != query_key


def test_corrupt_cache_entry_becomes_miss(
    tmp_path,
):
    path = tmp_path / "embeddings.sqlite"
    cache = SQLiteEmbeddingCache(path)
    key = build_embedding_cache_key(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        content_hash="content-hash",
    )
    cache.put_many(
        identity=_identity(),
        cache_version="test-v1",
        value_kind="document",
        values=[
            (
                key,
                "content-hash",
                [1.0, 0.0],
            )
        ],
    )

    with sqlite3.connect(path) as connection:
        connection.execute(
            (
                "UPDATE embedding_cache "
                "SET vector_json = ? "
                "WHERE cache_key = ?"
            ),
            ("not-json", key),
        )

    assert cache.get_many([key]) == {}
```

---

## 二十八、增加 Dense Retrieval 测试

> **本节类型：需要新增测试代码。**
>
> **需要新增：** `tests/test_dense_retrieval.py`

完整文件：

```python
from app.retrieval.dense import (
    PreparedDenseRetriever,
    cosine_similarity,
)
from app.retrieval.embedding_backend import (
    EmbeddingBackendIdentity,
)
from app.retrieval.embedding_cache import (
    SQLiteEmbeddingCache,
)
from app.retrieval.indexer import (
    build_repository_index,
    sha256_text,
)
from app.retrieval.schemas import (
    ChannelHit,
    SemanticChunk,
)
from app.retrieval.service import (
    build_evidence_pack,
)


class FakeEmbeddingBackend:
    def __init__(self) -> None:
        self.document_calls = 0
        self.query_calls = 0

    @property
    def identity(
        self,
    ) -> EmbeddingBackendIdentity:
        return EmbeddingBackendIdentity(
            provider_namespace="fake-provider",
            model="fake-semantic-model",
        )

    @staticmethod
    def _vector(text: str) -> list[float]:
        lower = text.casefold()
        if (
            "radius_neighbors" in lower
            or "motion_offsets" in lower
            or "3d points" in lower
        ):
            return [1.0, 0.05, 0.0]
        if (
            "image" in lower
            or "pixels" in lower
        ):
            return [0.05, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        self.document_calls += 1
        return [
            self._vector(text)
            for text in texts
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        self.query_calls += 1
        return self._vector(text)


def _chunk(
    *,
    chunk_id: str,
    file_path: str,
    text: str,
) -> SemanticChunk:
    content_hash = sha256_text(text)
    return SemanticChunk(
        chunk_id=chunk_id,
        repo_fingerprint="repo-fingerprint",
        file_path=file_path,
        file_sha256=(
            f"file-sha-{chunk_id}"
        ),
        start_line=1,
        end_line=10,
        symbol=None,
        source_content_hash=content_hash,
        embedding_content_hash=content_hash,
        embedding_text=text,
    )


def test_dense_retriever_ranks_semantic_operator(
    tmp_path,
):
    backend = FakeEmbeddingBackend()
    retriever = PreparedDenseRetriever.prepare(
        chunks=[
            _chunk(
                chunk_id="operator",
                file_path="operator_core.py",
                text=(
                    "radius_neighbors motion_offsets "
                    "weighted_pool"
                ),
            ),
            _chunk(
                chunk_id="image",
                file_path="image_filter.py",
                text="image pixels average",
            ),
        ],
        backend=backend,
        cache=SQLiteEmbeddingCache(
            tmp_path / "cache.sqlite"
        ),
        cache_version="test-v1",
        batch_size=8,
    )

    hits, report = retriever.rank(
        query=(
            "aggregate neighborhoods of 3D points "
            "across adjacent frames"
        ),
        min_similarity=0.2,
        max_hits=5,
        required=True,
    )

    assert hits[0].file_path == (
        "operator_core.py"
    )
    assert hits[0].channel == "dense"
    assert report.embedding_document_calls == 1
    assert report.embedding_query_calls == 1
    assert report.embedding_dimensions == 3


def test_second_run_uses_document_and_query_cache(
    tmp_path,
):
    cache = SQLiteEmbeddingCache(
        tmp_path / "cache.sqlite"
    )
    chunks = [
        _chunk(
            chunk_id="operator",
            file_path="operator_core.py",
            text="radius_neighbors motion_offsets",
        )
    ]
    first_backend = FakeEmbeddingBackend()
    first = PreparedDenseRetriever.prepare(
        chunks=chunks,
        backend=first_backend,
        cache=cache,
        cache_version="test-v1",
        batch_size=8,
    )
    first.rank(
        query="3D points across frames",
        min_similarity=0.0,
        max_hits=5,
        required=True,
    )

    second_backend = FakeEmbeddingBackend()
    second = PreparedDenseRetriever.prepare(
        chunks=chunks,
        backend=second_backend,
        cache=cache,
        cache_version="test-v1",
        batch_size=8,
    )
    _, report = second.rank(
        query="3D points across frames",
        min_similarity=0.0,
        max_hits=5,
        required=True,
    )

    assert second_backend.document_calls == 0
    assert second_backend.query_calls == 0
    assert report.embedding_document_calls == 0
    assert report.embedding_query_calls == 0
    assert report.cache_hits == 2


def test_dense_hit_enters_evidence_pack(
    tmp_path,
):
    path = tmp_path / "operator.py"
    path.write_text(
        "\n".join(
            [
                "class LocalMixer:",
                "    def forward(self, x):",
                "        return aggregate(x)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    index = build_repository_index(
        tmp_path,
        index_version="test-v1",
    )

    _, pack = build_evidence_pack(
        repo_path=tmp_path,
        query="unrelated paper vocabulary",
        keywords=[],
        index=index,
        top_k=3,
        dense_hits=[
            ChannelHit(
                channel="dense",
                file_path="operator.py",
                raw_score=0.92,
                anchor_line=1,
                anchor_end_line=3,
                symbol="LocalMixer",
            )
        ],
    )

    assert pack.items[0].file_path == (
        "operator.py"
    )
    assert "dense" in (
        pack.items[0].retrieval_channels
    )


def test_cosine_similarity_rejects_zero_vector():
    try:
        cosine_similarity(
            [0.0, 0.0],
            [1.0, 0.0],
        )
    except Exception as exc:  # noqa: BLE001
        assert "零向量" in str(exc)
    else:
        raise AssertionError(
            "zero vector should be rejected"
        )
```

最后一个测试也可以使用 `pytest.raises`。这里不强制引入额外 import。

---

## 二十九、增加 Dense 安全边界测试

> **本节类型：需要新增测试代码。**
>
> **需要新增：** `tests/test_dense_retrieval_safety.py`

完整文件：

```python
import pytest

from app.config import settings
from app.nodes.code_search_node import (
    _dense_flags,
    _prepare_dense,
)
from app.retrieval.embedding_backend import (
    EmbeddingProviderError,
    validate_vectors,
)


def test_required_implies_dense_enabled():
    enabled, required = _dense_flags(
        {
            "enable_dense_retrieval": False,
            "dense_retrieval_required": True,
        }
    )

    assert enabled is True
    assert required is True


def test_remote_code_upload_requires_explicit_setting(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "allow_code_embedding_upload",
        False,
    )

    with pytest.raises(
        EmbeddingProviderError,
        match="ALLOW_CODE_EMBEDDING_UPLOAD=false",
    ):
        # Guard 在读取 index 或源码之前执行。
        _prepare_dense(
            repo_path="/unused",
            index=None,
        )


@pytest.mark.parametrize(
    "vector",
    [
        [float("nan"), 0.0],
        [float("inf"), 0.0],
        [],
    ],
)
def test_invalid_provider_vectors_are_rejected(
    vector,
):
    with pytest.raises(
        EmbeddingProviderError
    ):
        validate_vectors(
            [vector],
            expected_count=1,
        )
```

---

## 三十、增加 Semantic Eval 测试

> **本节类型：需要新增测试代码。**
>
> **需要新增：** `tests/test_semantic_retrieval_eval.py`

完整文件：

```python
import os
from pathlib import Path

import pytest

from app.config import settings
from app.evaluation.case_loader import (
    load_case_file,
)
from app.evaluation.runners import run_case
from app.evaluation.schemas import (
    EvalCase,
    EvalMetrics,
    EvalObservation,
)
from app.evaluation.scorers import score_case


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_CASE = (
    PROJECT_ROOT
    / "app"
    / "evaluation"
    / "cases"
    / "provider"
    / "retrieval_obfuscated_semantics.json"
)


def test_semantic_runner_rejects_offline_suite():
    payload = {
        "case_id": "invalid_offline_dense",
        "description": "must be rejected",
        "suite": "offline",
        "runner": "semantic_code_retrieval",
        "categories": ["evidence"],
        "input": {
            "repo_path": (
                "fixtures/retrieval_repo"
            ),
            "retrieval_query": (
                "semantic behavior"
            ),
        },
        "expected": {},
    }

    with pytest.raises(
        ValueError,
        match="provider suite",
    ):
        EvalCase.model_validate(payload)


def test_efficiency_scorer_checks_embedding_budget():
    case = EvalCase.model_validate(
        {
            "case_id": "embedding_budget",
            "description": "embedding budget",
            "suite": "provider",
            "runner": (
                "semantic_code_retrieval"
            ),
            "categories": ["efficiency"],
            "input": {
                "repo_path": (
                    "fixtures/retrieval_repo"
                ),
                "retrieval_query": "behavior",
            },
            "expected": {
                "max_embedding_document_calls": 2,
                "max_embedding_query_calls": 1,
            },
        }
    )
    observation = EvalObservation(
        case_id=case.case_id,
        runner=(
            "semantic_code_retrieval"
        ),
        metrics=EvalMetrics(
            embedding_document_calls=3,
            embedding_query_calls=1,
        ),
    )

    result = score_case(
        case,
        observation,
    )

    assert result.passed is False
    assert any(
        assertion.code
        == (
            "EFFICIENCY_"
            "EMBEDDING_DOCUMENT_CALLS"
        )
        and not assertion.passed
        for scorer in result.scorer_results
        for assertion in scorer.assertions
    )


@pytest.mark.provider
def test_real_embedding_provider_case():
    if (
        not os.getenv("EMBEDDING_API_KEY")
        or not os.getenv(
            "EMBEDDING_BASE_URL"
        )
        or not settings
        .allow_code_embedding_upload
    ):
        pytest.skip(
            "真实 Embedding Provider 未显式配置"
        )

    case = load_case_file(PROVIDER_CASE)
    observation = run_case(case)
    result = score_case(
        case,
        observation,
    )

    assert result.passed, [
        assertion.model_dump()
        for scorer in result.scorer_results
        for assertion in scorer.assertions
        if not assertion.passed
    ]
```

普通测试中 provider case 会 skip，不会访问网络。显式配置后才能执行。

---

## 三十一、按层运行测试

> **本节类型：运行和验收说明，不修改项目代码。**

### 31.1 语法与导入检查

```bash
python -m compileall \
  app/retrieval \
  app/nodes/code_search_node.py \
  app/evaluation
```

### 31.2 Phase 21 离线单元测试

```bash
python -m pytest \
  tests/test_semantic_query_builder.py \
  tests/test_semantic_chunking.py \
  tests/test_embedding_cache.py \
  tests/test_dense_retrieval.py \
  tests/test_dense_retrieval_safety.py \
  tests/test_semantic_retrieval_eval.py \
  -m "not provider" \
  -q
```

这组测试不需要：

```text
EMBEDDING_API_KEY
网络
真实 Embedding 模型
向量数据库
GPU
```

### 31.3 Phase 20 + Phase 21 Retrieval 回归

```bash
python -m pytest \
  tests/test_search_tools_v2.py \
  tests/test_retrieval_index.py \
  tests/test_retrieval_ranking.py \
  tests/test_hybrid_retrieval.py \
  tests/test_mapping_evidence_boundary.py \
  tests/test_retrieval_eval.py \
  tests/test_semantic_query_builder.py \
  tests/test_semantic_chunking.py \
  tests/test_embedding_cache.py \
  tests/test_dense_retrieval.py \
  tests/test_dense_retrieval_safety.py \
  tests/test_semantic_retrieval_eval.py \
  -m "not provider" \
  -q
```

### 31.4 全量离线回归

```bash
python -m pytest -m "not provider"
```

### 31.5 Provider Probe

先只验证无源码文本：

```bash
python -m app.main probe-embedding
```

预期输出包含：

```text
provider_namespace
model
dimensions
probe_similarity
```

不应输出 API key。

### 31.6 显式 Provider Golden

确认 `.env` 中已经设置：

```dotenv
ALLOW_CODE_EMBEDDING_UPLOAD=true
```

然后运行：

```bash
python -m app.evaluation.run_eval run \
  --suite provider \
  --case-id provider_retrieval_obfuscated_semantics \
  --no-fail-on-regression
```

第一次新增 Case 尚未写入 baseline，所以先使用 `--no-fail-on-regression` 查看结果。Case 本身仍应显示通过。

也可以直接运行测试：

```bash
python -m pytest \
  tests/test_semantic_retrieval_eval.py \
  -m provider \
  -q
```

---

## 三十二、先验证安全降级

> **本节类型：手工验收，不修改项目代码。**

保持：

```dotenv
ALLOW_CODE_EMBEDDING_UPLOAD=false
```

运行可降级模式：

```bash
python -m app.main retrieve-code \
  /data/tianshaoqi24/PST-Convolution-main/ \
  "find the block that aggregates local geometry across adjacent frames" \
  --dense \
  --allow-dense-fallback
```

预期：

```text
Graph 不发送源码
Phase 20 Sparse Hybrid 继续运行
dense_report.enabled = true
dense_report.fallback_reason 包含 ALLOW_CODE_EMBEDDING_UPLOAD=false
final_status 可成功
```

再运行 required 模式：

```bash
python -m app.main retrieve-code \
  /data/tianshaoqi24/PST-Convolution-main/ \
  "find the block that aggregates local geometry across adjacent frames" \
  --dense \
  --require-dense
```

预期：

```text
final_status 失败
StageError.code = DENSE_UPLOAD_NOT_ALLOWED
没有发送源码
```

只有这两个行为都符合预期，才允许把上传开关改为 true。

---

## 三十三、真实 PST 仓库 Dense 对照验收

> **本节类型：手工验收，不修改项目代码。**
>
> **仓库：** `/data/tianshaoqi24/PST-Convolution-main/`

### 33.1 记录 Sparse 结果

```bash
python -m app.main retrieve-code \
  /data/tianshaoqi24/PST-Convolution-main/ \
  "locate the block that groups spatial neighbors over consecutive frames and jointly aggregates point features" \
  --no-dense
```

记录：

```text
modules/pst_convolutions.py 的 rank
retrieval_channels
snippet 行号
```

### 33.2 运行 Dense Hybrid

确认仓库允许上传，并设置：

```dotenv
ENABLE_DENSE_RETRIEVAL=true
ALLOW_CODE_EMBEDDING_UPLOAD=true
```

运行：

```bash
python -m app.main retrieve-code \
  /data/tianshaoqi24/PST-Convolution-main/ \
  "locate the block that groups spatial neighbors over consecutive frames and jointly aggregates point features" \
  --dense \
  --require-dense
```

检查：

1. `modules/pst_convolutions.py` 是否进入 top-k；
2. `retrieval_channels` 是否包含 `dense`；
3. Dense anchor 是否靠近 `PSTConv.forward`；
4. semantic manifest 是否不包含 `embedding_text`；
5. dense report 是否没有 API key 和完整源码；
6. Evidence Pack 的 snippet 是否仍从真实文件重新读取；
7. `validate_code_evidence()` 是否仍然通过。

### 33.3 验证 Cache

用完全相同的 query 再运行一次：

```bash
python -m app.main retrieve-code \
  /data/tianshaoqi24/PST-Convolution-main/ \
  "locate the block that groups spatial neighbors over consecutive frames and jointly aggregates point features" \
  --dense \
  --require-dense
```

第二次 dense report 应满足：

```text
embedding_document_calls = 0
embedding_query_calls = 0
cache_hits > 0
cache_misses = 0
```

如果 query 或源码改变，相关 cache miss 是正常的。

### 33.4 检查 Run Artifacts

在新 `run_dir` 中检查：

```text
analysis/retrieval/repo_index.json
analysis/retrieval/semantic_index_manifest.json
analysis/retrieval/dense_reports/00_ad-hoc-retrieval.json
analysis/retrieval/evidence_packs/00_ad-hoc-retrieval.json
reports/run_manifest.json
```

Semantic manifest 只应包含：

```text
chunk_id
file path
file hash
line range
symbol
source/embedding content hash
redaction count
```

不应包含：

```text
embedding_text
vector
API key
Provider request headers
```

---

## 三十四、验证完整 Paper-to-Code Mapping

> **本节类型：Provider 手工验收，不修改项目代码。**

使用论文：

```text
pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf
```

运行：

```bash
python -m app.main map-code \
  "pdf/PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences.pdf" \
  /data/tianshaoqi24/PST-Convolution-main/
```

由于 `.env` 已开启 Dense，`code_search_node` 会对每个 `MethodModule`：

```text
构造 semantic query
生成或复用 code chunk vectors
生成 query vector
产生 dense hits
与 Phase 20 通道做 RRF
生成 Evidence Pack
进入 mapping_node
```

重点检查：

```text
论文术语与代码命名一致的模块：
    symbol/keyword 仍应是强信号。

论文术语与代码命名不一致的模块：
    dense 应补充候选，但不能绕过 Evidence Pack。

mapping candidate：
    evidence_ids 必须属于 pack。

源码在检索后改变：
    mapping binder 必须删除 stale Evidence。
```

Dense Retrieval 不改变人工审批和 file repair 的权限边界。

---

## 三十五、VS Code Debug 配置

> **本节类型：调试配置说明。**
>
> **如需保存配置，需要修改：** `.vscode/launch.json`

如果当前没有 `launch.json`，可以使用：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Phase 21: probe embedding",
      "type": "debugpy",
      "request": "launch",
      "module": "app.main",
      "console": "integratedTerminal",
      "justMyCode": true,
      "args": [
        "probe-embedding"
      ]
    },
    {
      "name": "Phase 21: dense PST retrieval",
      "type": "debugpy",
      "request": "launch",
      "module": "app.main",
      "console": "integratedTerminal",
      "justMyCode": true,
      "args": [
        "retrieve-code",
        "/data/tianshaoqi24/PST-Convolution-main/",
        "locate the block that groups spatial neighbors over consecutive frames and jointly aggregates point features",
        "--dense",
        "--require-dense"
      ]
    },
    {
      "name": "Phase 21: semantic provider eval",
      "type": "debugpy",
      "request": "launch",
      "module": "app.evaluation.run_eval",
      "console": "integratedTerminal",
      "justMyCode": true,
      "args": [
        "run",
        "--suite",
        "provider",
        "--case-id",
        "provider_retrieval_obfuscated_semantics",
        "--no-fail-on-regression"
      ]
    }
  ]
}
```

推荐断点：

```text
app/retrieval/chunking.py
    build_semantic_chunks()

app/retrieval/embedding_cache.py
    get_many()
    put_many()

app/retrieval/dense.py
    PreparedDenseRetriever.prepare()
    PreparedDenseRetriever.rank()

app/retrieval/ranking.py
    fuse_rankings()

app/nodes/code_search_node.py
    _prepare_dense()
    code_search_node()
```

Debug Console 可查看：

```python
len(chunks)

manifest.redacted_line_count

retriever.stats

[
    (hit.file_path, hit.raw_score, hit.symbol)
    for hit in dense_hits[:10]
]

dense_report.model_dump()
```

不要在断点表达式中重新调用 `embed_documents()`。Debug evaluation 可能重复产生费用，并可能因为其他线程暂停而超时。

---

## 三十六、常见问题与处理方式

> **本节类型：排错说明，不修改项目代码。**

### 36.1 `DENSE_UPLOAD_NOT_ALLOWED`

这是安全开关生效，不是代码故障。

确认：

```text
仓库是否允许上传
Embedding Provider 的数据保留策略
目标 Base URL 是否可信
是否确实需要 required 模式
```

确认后再设置：

```dotenv
ALLOW_CODE_EMBEDDING_UPLOAD=true
```

### 36.2 `EMBEDDING_API_KEY 未配置`

检查：

```dotenv
EMBEDDING_API_KEY=...
EMBEDDING_BASE_URL=...
EMBEDDING_MODEL=...
```

先运行 `probe-embedding`，不要直接用整个仓库测试配置。

### 36.3 Provider 返回 401/403，但报告只有异常类型

生产错误故意不保存 Provider 原始请求和 headers。可在本地 Debug 查看 exception cause，但不要把包含认证信息的完整对象写入 Artifact。

### 36.4 Embedding 维度与缓存不一致

可能原因：

```text
Provider 在相同 model 名下切换了维度
修改了 model_kwargs
旧 cache 已损坏
```

先更新：

```dotenv
EMBEDDING_CACHE_VERSION=phase21-v2
```

如果确认旧 cache 可以丢弃，再删除项目内生成文件：

```bash
rm -f \
  cache/embeddings.sqlite \
  cache/embeddings.sqlite-shm \
  cache/embeddings.sqlite-wal
```

不要删除 `runs/` 中的历史 Dense report。

### 36.5 第一次运行很慢

第一次需要给全部 chunk 生成向量。检查：

```text
semantic_max_chunks 是否过大
symbol chunk 是否产生大量重叠
embedding_batch_size 是否过小
Provider 是否限制批量大小
仓库是否包含大量生成文件
```

不要通过整文件 embedding 来减少 chunk 数，这会降低定位精度。

### 36.6 第二次运行仍然全是 Cache Miss

检查是否改变：

```text
EMBEDDING_MODEL
EMBEDDING_BASE_URL
EMBEDDING_CACHE_VERSION
SEMANTIC_CHUNK_POLICY_VERSION
源码内容
文件路径
query 文本
```

这些变化本来就应该使 cache 失效。

### 36.7 Dense 没有命中任何文件

可能是：

```text
DENSE_MIN_SIMILARITY 过高
query 太短或只有论文缩写
chunk 太小导致行为上下文丢失
模型不擅长代码与自然语言跨模态检索
目标文件被 private-key 安全规则跳过
```

先查看 dense report 和 semantic manifest，不要直接降低所有安全限制。

### 36.8 Dense 召回太多语义相似误报

这是 Dense 提高 recall 后的典型代价。优先：

```text
保留 symbol/traceback 高权重
调整 query Evidence
增加负例 Golden Case
降低 dense weight
提高 min_similarity
```

如果仍然无法区分，再考虑 Cross Encoder reranker，不要让 LLM 无边界读取更多文件。

### 36.9 为什么不直接使用 pgvector

当前单仓库 chunk 较少，准确率瓶颈在：

```text
query 质量
chunk 质量
embedding 模型
融合权重
Golden Case
```

向量数据库主要解决规模和服务化，不会自动修复错误 chunk 或错误模型。先证明 Dense channel 有质量收益，再迁移存储层。

### 36.10 Provider Case 不稳定

检查是否发生：

```text
模型版本漂移
相似度阈值过紧
Golden rank 要求过于绝对
Provider 对输入增加了不同 instruction
fixture 中存在过强词面提示
```

Golden 应限制路径和 rank，不固定浮点 cosine。

---

## 三十七、本阶段涉及的 Agent 知识

> **本节类型：知识总结，不修改项目代码。**

### 37.1 Sparse 和 Dense 是互补关系

```text
Sparse / AST：
    精确、可解释、适合符号名和路径。

Dense：
    适合术语错位、命名不规则和自然语言到代码行为的匹配。
```

可靠 Agent 不应只选择其中一种。

### 37.2 Chunking 决定检索上限

Embedding 模型无法修复完全错误的切块：

```text
chunk 太大：
    多种职责混在一起，语义被稀释。

chunk 太小：
    输入、操作和输出被切开。

symbol + overlap：
    在局部语义和上下文之间折中。
```

### 37.3 Cache 是内容寻址的派生数据

Cache 不是长期记忆：

```text
输入内容和模型相同：
    可以复用。

内容、模型或策略改变：
    必须失效。
```

因此 cache key 必须绑定模型和 content hash。

### 37.4 Provider 调用也是 Tool 边界

Embedding 虽然不生成自然语言，也仍然具有：

```text
网络副作用
成本
隐私风险
超时
重试
返回格式漂移
```

需要与 Chat LLM 一样被配置、观测和评测。

### 37.5 Semantic Similarity 不是 Evidence

Cosine score 只能说明向量接近：

```text
不能证明文件就是论文实现
不能证明代码能够运行
不能证明参数与论文一致
不能授权修改文件
```

最终结论仍需要真实源码片段、行号、hash 和 mapping 判断。

### 37.6 Vector Database 不等于 Retrieval Quality

Vector Database 解决：

```text
规模
持久化
过滤
并发
ANN 延迟
```

Retrieval Quality 主要取决于：

```text
query
chunk
embedding model
fusion/reranking
Golden data
```

不要用基础设施复杂度代替质量评测。

---

## 三十八、完成标准

> **本节类型：最终验收清单，不修改项目代码。**

只有以下各项全部满足，才算 Phase 21 完成：

- Dense 默认关闭；
- 远程代码上传有独立显式授权；
- required 与 fallback 语义不同；
- semantic query 使用 MethodModule 和 PaperEvidence；
- lexical query 不被长 Evidence 污染；
- Python symbol 和滑动窗口都能生成 chunk；
- chunk 有稳定 ID、文件 hash、行号和 source hash；
- 疑似 secret assignment 在上传前脱敏；
- private key 文件整体跳过；
- manifest 不保存源码正文或向量；
- Embedding Backend 可以用 Fake 实现替换；
- Provider 返回数量、维度、NaN 和 Inf 被校验；
- SQLite cache key 绑定 endpoint namespace、model、版本和内容；
- cache 不保存 API key；
- 第二次相同运行不重复调用 document/query embedding；
- Dense 作为独立通道进入 RRF；
- symbol 和 traceback 权重仍高于 Dense；
- Dense anchor 能生成正确局部 CodeEvidence；
- Evidence provenance 和 stale 校验仍然有效；
- 普通离线测试不访问 Provider；
- provider Golden 能召回命名错位算子；
- Embedding 调用数和耗时进入 EvalMetrics；
- Phase 20 旧 Golden 全部通过；
- 真实 PST 查询的目标 rank 不低于 Sparse 基线；
- 至少保留一个 Dense `map-code` run 作为验收记录。

---

## 三十九、下一阶段建议

> **本节类型：路线说明，不修改项目代码。**

本阶段完成后，最值得优先做的是：

```text
Phase 22：异步 Job Runtime、Heartbeat、Lease 与崩溃恢复
```

原因：

1. 论文结构、Paper Evidence、Sparse/Dense Code Retrieval、Mapping、执行和修复已经形成质量闭环；
2. Embedding 和长实验都可能成为长耗时任务；
3. 当前 CLI/Graph 仍缺少统一 job identity、worker claim、heartbeat 和 stale lease recovery；
4. Web UI、远程 worker 和任务队列都依赖稳定 Job Runtime。

Phase 22 推荐边界：

```text
JobRecord
JobStore
queued/running/interrupted/succeeded/failed/cancelled
worker claim token
heartbeat
lease expiry
幂等 graph resume
任务级 cancel
job_id/thread_id/run_id 关联
crash + reclaim 离线测试
```

Cross Encoder reranker 暂不作为独立阶段。先积累 Dense false-positive Golden Case；只有证据表明 RRF + mapping 无法稳定排序时，再增加 bounded reranker。
