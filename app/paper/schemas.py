from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BlockType = Literal[
    "title",
    "heading",
    "paragraph",
    "table",
    "caption",
    "formula",
    "header",
    "footer",
    "unknown",
]

SectionKind = Literal[
    "abstract",
    "introduction",
    "related_work",
    "method",
    "experiments",
    "datasets",
    "implementation",
    "results",
    "ablation",
    "conclusion",
    "appendix",
    "references",
    "limitations",
    "other",
]


class PaperBlock(BaseModel):
    """PDF 页面上的最小可追踪文本单元。"""

    model_config = ConfigDict(extra="forbid")

    # ID 必须由 page、order 和 text_hash 确定性生成，不能使用随机 UUID。
    block_id: str
    page: int = Field(ge=1)
    order: int = Field(ge=0)
    block_type: BlockType = "unknown"
    text: str
    bbox: tuple[float, float, float, float] | None = None
    font_size: float | None = None
    font_name: str | None = None
    is_bold: bool = False
    text_hash: str

    # 重复页眉页脚等噪声不删除，保留原始可审计记录，但不参与 section 正文。
    excluded: bool = False
    exclusion_reason: str | None = None


class PaperSection(BaseModel):
    """由 heading 和连续 block 组成的层级章节。"""

    model_config = ConfigDict(extra="forbid")

    section_id: str
    number: str | None = None
    title: str
    normalized_title: str
    level: int = Field(ge=1)
    kind: SectionKind = "other"
    parent_id: str | None = None
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    heading_block_id: str | None = None
    block_ids: list[str] = Field(default_factory=list)
    content_hash: str


class PaperParseWarning(BaseModel):
    """不阻断索引、但需要下游知道的解析异常。"""

    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "EMPTY_PAGE",
        "OCR_REQUIRED",
        "TABLE_PARSE_FAILED",
        "NO_HEADINGS",
        "HEADING_AMBIGUOUS",
        "UNSUPPORTED_FORMAT",
        # 子章节出现时没有找到显式父编号。
        "MISSING_SECTION_PARENT",
        # 同一个显式编号被多个标题重复占用。
        "HEADING_SEQUENCE_CONFLICT",
    ]
    message: str
    page: int | None = None
    block_id: str | None = None


class PaperParseReport(BaseModel):
    """文本覆盖率和章节结构质量报告。"""

    model_config = ConfigDict(extra="forbid")

    # status 继续表示文本提取是否可用，保持 Phase 18 兼容。
    status: Literal["succeeded", "partial", "failed"]

    # structure_status 单独表达章节结构是否可信。
    structure_status: Literal[
        "reliable",
        "degraded",
        "unknown",
    ] = "unknown"

    page_count: int = Field(ge=0)
    indexed_pages: list[int] = Field(default_factory=list)
    empty_pages: list[int] = Field(default_factory=list)
    ocr_required_pages: list[int] = Field(default_factory=list)
    block_count: int = Field(ge=0)
    section_count: int = Field(ge=0)

    # raw candidate 是“看起来可能像标题”的原始候选。
    heading_candidate_count: int = Field(default=0, ge=0)

    # accepted 是跨行合并完成后的最终逻辑标题数。
    accepted_heading_count: int = Field(default=0, ge=0)

    # rejected 是被确定性硬规则拒绝的原始候选数。
    rejected_heading_count: int = Field(default=0, ge=0)

    # 两个或多个视觉标题行合并成一个逻辑标题的次数。
    multiline_heading_merge_count: int = Field(default=0, ge=0)

    # 缺少父编号、重复编号等层级 warning 数量。
    hierarchy_warning_count: int = Field(default=0, ge=0)

    warnings: list[PaperParseWarning] = Field(default_factory=list)


class PaperDocument(BaseModel):
    """适合存入 Graph state 的紧凑论文文档元数据。"""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    source_path: str
    source_sha256: str
    parser_version: str
    page_count: int = Field(ge=0)
    indexed_page_count: int = Field(ge=0)
    block_count: int = Field(ge=0)
    section_count: int = Field(ge=0)

    # 这些路径相对于本次 run 的 artifact 根目录。
    blocks_artifact: str
    sections_artifact: str
    parse_report_artifact: str


class SectionChunk(BaseModel):
    """交给一次 LLM map 调用的章节片段。"""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    section_id: str
    section_title: str
    section_kind: SectionKind
    page_start: int
    page_end: int
    block_ids: list[str]
    text: str
    content_hash: str


class EvidenceDraft(BaseModel):
    """模型可生成的 Evidence 草稿，只允许引用已有 block。"""

    model_config = ConfigDict(extra="forbid")

    block_ids: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class TextFactDraft(BaseModel):
    """带 Evidence 的普通文本事实。"""

    model_config = ConfigDict(extra="forbid")

    value: str
    evidence: EvidenceDraft


class NamedFactDraft(BaseModel):
    """数据集、指标等具名事实。"""

    model_config = ConfigDict(extra="forbid")

    name: str
    evidence: EvidenceDraft


class MethodModuleDraft(BaseModel):
    """单章节抽取到的方法模块候选。"""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    possible_keywords: list[str] = Field(default_factory=list)
    evidence: EvidenceDraft


class ExperimentSettingDraft(BaseModel):
    """单章节抽取到的实验设置候选。"""

    model_config = ConfigDict(extra="forbid")

    name: str
    value: str
    evidence: EvidenceDraft


class SectionExtractionDraft(BaseModel):
    """一次 section map 调用的严格结构化输出。"""

    model_config = ConfigDict(extra="forbid")

    section_id: str
    chunk_id: str
    summary: str
    research_problem_candidates: list[TextFactDraft] = Field(default_factory=list)
    core_idea_candidates: list[TextFactDraft] = Field(default_factory=list)
    method_modules: list[MethodModuleDraft] = Field(default_factory=list)
    datasets: list[NamedFactDraft] = Field(default_factory=list)
    metrics: list[NamedFactDraft] = Field(default_factory=list)
    experiment_settings: list[ExperimentSettingDraft] = Field(default_factory=list)
    reproduction_risks: list[TextFactDraft] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)

    # 表格存在但无法可靠抽取单元格时，必须把问题写在这里。
    table_claims_unresolved: list[str] = Field(default_factory=list)


class PaperEvidence(BaseModel):
    """EvidenceDraft 经过确定性解析后的完整来源记录。"""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    document_id: str
    section_id: str
    block_ids: list[str]
    page_start: int
    page_end: int
    text: str
    summary: str
    content_hash: str
    confidence: float = Field(ge=0.0, le=1.0)


class PaperFactRecord(BaseModel):
    """独立事实索引中的一条事实。"""

    model_config = ConfigDict(extra="forbid")

    fact_id: str
    category: Literal[
        "research_problem",
        "core_idea",
        "method_module",
        "dataset",
        "metric",
        "experiment_setting",
        "reproduction_risk",
    ]
    name: str
    value: str
    normalized_key: str
    evidence: PaperEvidence


class PaperConflict(BaseModel):
    """同一规范化配置键出现多个不同值。"""

    model_config = ConfigDict(extra="forbid")

    conflict_id: str
    normalized_key: str
    fact_ids: list[str] = Field(min_length=2)
    values: list[str] = Field(min_length=2)
    reason: str