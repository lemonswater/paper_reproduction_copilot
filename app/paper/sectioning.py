from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.paper.normalization import (
    looks_like_arxiv_overlay,
    normalize_heading,
    normalize_key,
    normalize_pdf_text,
)
from app.paper.schemas import (
    PaperBlock,
    PaperParseWarning,
    PaperSection,
    SectionKind,
)

_NUMBERED_HEADING_RE = re.compile(
    r"^(?P<number>\d+(?:\.\d+)*)(?:[.)])?\s+(?P<title>.+)$"
)
_APPENDIX_HEADING_RE = re.compile(
    r"^(?P<number>[A-Z](?:\.\d+)*)(?:[.)])?\s+(?P<title>.+)$"
)
_SPLIT_HEADING_NUMBER_RE = re.compile(
    r"^(?P<number>(?:\d+(?:\.\d+)*|[A-Z](?:\.\d+)*))(?:[.)])?$"
)
_TITLE_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+-]*")
_COORDINATE_FORMULA_RE = re.compile(
    r"\([A-Za-z]\s*,\s*[A-Za-z](?:\s*,\s*[A-Za-z])+\)"
)
# PyMuPDF 会把公式里的特殊符号替换为 \x03-\x05 等控制字符。
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
# PDF 截断的正文行常以这些介词/连词结尾，真实章节标题极少如此。
_TRAILING_STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "with", "for", "to",
    "in", "on", "at", "by", "from", "as", "is", "are", "was",
    "were", "be", "that", "this", "these", "those", "it", "its",
    "their", "our", "which", "while", "but", "not", "than", "into",
}

_NOISE_BLOCK_TYPES = {
    "table",
    "caption",
    "header",
    "footer",
    "formula",
}

_UNNUMBERED_HEADINGS = {
    "abstract",
    "acknowledgment",
    "acknowledgments",
    "conclusion",
    "conclusions",
    "references",
    "appendix",
    "limitations",
    "limitation",
}

# 参考文献条目行，如 "[1] Author, Title, Venue."。真实章节标题不会以 [n] 开头。
_REFERENCE_ENTRY_RE = re.compile(r"^\s*\[\d+\]")

# 首页 front matter 区块标题，不是论文章节。
_FRONT_MATTER_HEADINGS = {
    "ccs concepts",
    "key words",
    "keywords",
    "index terms",
    "index",
}

_FORMULA_MARKERS = {
    "=",
    "′",
    "″",
    "∑",
    "∏",
    "≤",
    "≥",
    "→",
    "←",
    "|",
}


@dataclass(frozen=True)
class HeadingCandidate:
    """一个已经通过硬过滤的逻辑标题候选。"""

    # start_index/end_index 指向 ordered blocks 的半开区间。
    # 同行拆分标题可能消费两个 block，跨行标题还会继续扩大 end。
    start_index: int
    end_index: int
    heading_block: PaperBlock
    number: str | None
    title: str


@dataclass(frozen=True)
class SectionBuildResult:
    """section 列表及其确定性结构诊断。"""

    sections: list[PaperSection]
    heading_candidate_count: int
    rejected_heading_count: int
    multiline_heading_merge_count: int
    warnings: list[PaperParseWarning]

    @property
    def accepted_heading_count(self) -> int:
        if (
            len(self.sections) == 1
            and self.sections[0].title == "Document"
        ):
            return 0
        return len(self.sections)

    @property
    def hierarchy_warning_count(self) -> int:
        return sum(
            warning.code
            in {
                "MISSING_SECTION_PARENT",
                "HEADING_SEQUENCE_CONFLICT",
            }
            for warning in self.warnings
        )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _has_heading_style(block: PaperBlock) -> bool:
    """正文句子不能仅凭正则成为标题。"""

    return (
        block.block_type in {"heading", "title"}
        or block.is_bold
    )


def _estimate_body_font_size(blocks: list[PaperBlock]) -> float:
    """正文最常出现的字号。

    用按文本长度加权的众数而非中位数：正文行通常更长，
    次要小字（表格、图注、页眉）既短又少，不会把估计值拉低。
    """

    weights: dict[float, float] = {}
    for block in blocks:
        if (
            block.font_size is None
            or not (5.0 <= block.font_size <= 20.0)
        ):
            continue
        rounded = round(block.font_size * 4) / 4.0
        weights[rounded] = (
            weights.get(rounded, 0.0)
            + min(len(block.text), 200)
        )
    if not weights:
        return 10.0
    return max(weights, key=weights.get)


def _has_visual_scale(
    block: PaperBlock,
    body_font_size: float | None,
) -> bool:
    """无编号标题必须有比正文更大的视觉字号。

    仅靠 bold 或 block_type=heading 不够——同字号的粗体句子、
    架构图内文字、被误标的正文行都会被这类弱信号放进来。
    """

    if block.block_type == "title":
        return True
    if block.font_size and body_font_size:
        return block.font_size >= body_font_size * 1.15
    return block.is_bold


def _is_front_matter_text(block: PaperBlock) -> bool:
    """首页作者行/机构名之外的 front matter 硬特征。"""

    if "@" in block.text:
        return True
    key = normalize_key(normalize_heading(block.text))
    return key in _FRONT_MATTER_HEADINGS


def _is_vertical_label(block: PaperBlock) -> bool:
    """利用 bbox 排除明显的竖排图像标签。"""

    if block.bbox is None:
        return False

    x0, y0, x1, y1 = block.bbox
    width = max(x1 - x0, 1.0)
    height = max(y1 - y0, 1.0)

    # 同时要求绝对高度大于 24，避免短小字符框被误判。
    return height > 24.0 and height > width * 1.5


def _looks_like_formula_text(text: str) -> bool:
    """拒绝公式变量、坐标表达式和明显数学行。"""

    normalized = normalize_pdf_text(text)
    if any(marker in normalized for marker in _FORMULA_MARKERS):
        return True
    if _COORDINATE_FORMULA_RE.search(normalized):
        return True

    letters = [
        character
        for character in normalized
        if character.isalpha()
    ]
    words = _TITLE_WORD_RE.findall(normalized)

    # W/T/S 这类单字符不能独立成为无编号章节。
    return len(letters) <= 2 and len(words) <= 1


def _valid_numeric_number(number: str) -> bool:
    """接受常见章节编号，拒绝年份和表格小数。"""

    parts = number.split(".")
    if not 1 <= len(parts) <= 4:
        return False
    if any(not part.isdigit() for part in parts):
        return False

    values = [int(part) for part in parts]

    # 0.00、0.6 等更可能是表格值或公式值。
    if values[0] == 0:
        return False

    # 论文一级章节通常不会大于 30。
    # 该限制同时拒绝 89.39、2500 和 2018/2019。
    if values[0] > 30:
        return False

    # 防止异常长的小数/编号分量。
    return all(value <= 99 for value in values[1:])


def _valid_appendix_number(number: str) -> bool:
    """接受 A、B.2 等附录编号。"""

    parts = number.split(".")
    if (
        not parts
        or len(parts[0]) != 1
        or not ("A" <= parts[0] <= "Z")
    ):
        return False
    return all(
        part.isdigit() and int(part) <= 99
        for part in parts[1:]
    )


def _valid_section_number(number: str) -> bool:
    if number[0].isdigit():
        return _valid_numeric_number(number)
    return _valid_appendix_number(number)


def _looks_like_title_phrase(text: str) -> bool:
    """标题文本本身必须像短语，而不是正文或公式。"""

    value = normalize_heading(text).strip()
    if not value or len(value) > 180:
        return False
    if _CONTROL_CHARS_RE.search(value):
        return False
    if value.endswith((".", "?", "!", ";")):
        return False
    if "#" in value or _looks_like_formula_text(value):
        return False

    words = _TITLE_WORD_RE.findall(value)
    letters = [
        character
        for character in value
        if character.isalpha()
    ]
    return 1 <= len(words) <= 18 and len(letters) >= 3


def _is_truncated_sentence(text: str) -> bool:
    """编号标题的 title 若是截断的正文行则拒绝。

    不用于跨行标题（编号+同行标题被拆分的情况），那些由
    _split_heading_parts 处理，不受此限制。
    """

    value = normalize_heading(text).strip()
    if not value:
        return True
    # 正文句子/截断行含句点；真实章节标题的 title 不含。
    if "." in value:
        return True
    key = normalize_key(value)
    words = key.split()
    last = words[-1]
    # "a sequence of 3" 这类"介词+数字"结尾是截断行；
    # "NTU RGB+D 120" 这类数据集名数字结尾是真实标题。
    if last.isdigit():
        return len(words) >= 2 and words[-2] in _TRAILING_STOPWORDS
    # "…of"、"…in" 这类以介词/连词结尾的截断行。
    if last in _TRAILING_STOPWORDS:
        return True
    return False


def _is_appendix_title_style(title: str) -> bool:
    """单字母附录标题（如 "A. Accuracy"）的 title 以大写开头。

    正文句子被 `_APPENDIX_HEADING_RE` 误匹配时 title 通常小写
    （如 "A point cloud video..." 的 "point cloud..."）。
    """

    stripped = title.strip()
    return bool(stripped) and stripped[0].isupper()


def _uppercase_ratio(text: str) -> float:
    letters = [
        character
        for character in text
        if character.isalpha()
    ]
    if not letters:
        return 0.0
    return sum(character.isupper() for character in letters) / len(letters)


def _same_visual_line(
    left: PaperBlock,
    right: PaperBlock,
) -> bool:
    """判断相邻 block 是否属于同一视觉行。"""

    if left.bbox is None or right.bbox is None:
        return False

    left_x0, left_y0, left_x1, left_y1 = left.bbox
    right_x0, right_y0, _, right_y1 = right.bbox
    left_height = max(left_y1 - left_y0, 1.0)
    right_height = max(right_y1 - right_y0, 1.0)
    center_delta = abs(
        ((left_y0 + left_y1) / 2.0)
        - ((right_y0 + right_y1) / 2.0)
    )
    vertical_tolerance = max(
        2.0,
        min(left_height, right_height) * 0.35,
    )
    horizontal_gap = right_x0 - left_x1
    return (
        center_delta <= vertical_tolerance
        and -2.0 <= horizontal_gap <= 48.0
        and right_x0 >= left_x0
    )


def _looks_like_split_title(block: PaperBlock) -> bool:
    """识别编号右侧被单独抽取的标题文本。"""

    if (
        block.excluded
        or block.block_type in _NOISE_BLOCK_TYPES
        or looks_like_arxiv_overlay(block.text)
        or _is_vertical_label(block)
        or not _looks_like_title_phrase(block.text)
    ):
        return False

    return (
        _has_heading_style(block)
        or _uppercase_ratio(block.text) >= 0.65
    )


def _split_heading_parts(
    number_block: PaperBlock,
    title_block: PaperBlock,
) -> tuple[str, str] | None:
    """合并 PDF 拆开的“编号 block + 同行标题 block”。"""

    if (
        number_block.excluded
        or number_block.block_type in _NOISE_BLOCK_TYPES
        or number_block.page != title_block.page
        or title_block.order != number_block.order + 1
        or _is_vertical_label(number_block)
        or not _same_visual_line(number_block, title_block)
        or not _looks_like_split_title(title_block)
    ):
        return None

    number_text = normalize_pdf_text(number_block.text)
    match = _SPLIT_HEADING_NUMBER_RE.fullmatch(number_text)
    if match is None:
        return None

    number = match.group("number")
    if not _valid_section_number(number):
        return None

    return number, normalize_heading(title_block.text)


def _heading_parts(
    block: PaperBlock,
    *,
    body_font_size: float | None = None,
) -> tuple[str | None, str] | None:
    """返回合法的 (section_number, title)。"""

    if (
        block.excluded
        or block.block_type in _NOISE_BLOCK_TYPES
        or looks_like_arxiv_overlay(block.text)
        or _is_vertical_label(block)
        or _REFERENCE_ENTRY_RE.match(block.text)
    ):
        return None

    raw_text = normalize_pdf_text(block.text)
    text = normalize_heading(raw_text)
    if not text or len(text) > 180:
        return None

    numbered = _NUMBERED_HEADING_RE.match(raw_text)
    if numbered:
        number = numbered.group("number")
        title = normalize_heading(
            numbered.group("title")
        ).strip()
        if (
            _valid_numeric_number(number)
            and _has_heading_style(block)
            and _looks_like_title_phrase(title)
            and not _is_truncated_sentence(title)
        ):
            return number, title
        return None

    appendix = _APPENDIX_HEADING_RE.match(raw_text)
    if appendix:
        number = appendix.group("number")
        title = normalize_heading(
            appendix.group("title")
        ).strip()
        if (
            _valid_appendix_number(number)
            and _has_heading_style(block)
            and _looks_like_title_phrase(title)
            and not _is_truncated_sentence(title)
            and _is_appendix_title_style(title)
        ):
            return number, title
        return None

    key = normalize_key(text)
    if key in _UNNUMBERED_HEADINGS:
        return None, text

    if (
        not _has_heading_style(block)
        or not _looks_like_title_phrase(text)
        or not _has_visual_scale(block, body_font_size)
    ):
        return None

    words = _TITLE_WORD_RE.findall(text)

    # 允许 PSTNET 这类较长全大写续接行，
    # 但拒绝 W/T/S 等单字符公式变量。
    if len(words) == 1:
        letters = [
            character
            for character in text
            if character.isalpha()
        ]
        if len(letters) < 4:
            return None

    return None, text


def _looks_like_raw_heading_candidate(block: PaperBlock) -> bool:
    """只用于统计，不代表最终接受。"""

    if block.excluded or looks_like_arxiv_overlay(block.text):
        return False

    text = normalize_pdf_text(block.text)
    key = normalize_key(text)
    return bool(
        _has_heading_style(block)
        or _NUMBERED_HEADING_RE.match(text)
        or _APPENDIX_HEADING_RE.match(text)
        or key in _UNNUMBERED_HEADINGS
    )


def _font_size_close(
    left: PaperBlock,
    right: PaperBlock,
) -> bool:
    if left.font_size is None or right.font_size is None:
        return False
    maximum = max(left.font_size, right.font_size, 1.0)
    return abs(left.font_size - right.font_size) / maximum <= 0.12


def _can_merge_multiline(
    left: HeadingCandidate,
    right: HeadingCandidate,
) -> bool:
    """严格判断 right 是否为 left 的下一视觉标题行。"""

    if (
        right.number is not None
        or left.end_index != right.start_index
        or left.heading_block.page != right.heading_block.page
        or not _has_heading_style(left.heading_block)
        or not _has_heading_style(right.heading_block)
        or not _font_size_close(
            left.heading_block,
            right.heading_block,
        )
        or normalize_key(right.title) in _UNNUMBERED_HEADINGS
        or _uppercase_ratio(left.title) < 0.65
        or _uppercase_ratio(right.title) < 0.65
    ):
        return False

    left_bbox = left.heading_block.bbox
    right_bbox = right.heading_block.bbox
    if left_bbox is None or right_bbox is None:
        return False

    left_x0, _, _, left_y1 = left_bbox
    right_x0, right_y0, _, _ = right_bbox
    horizontal_start_delta = abs(left_x0 - right_x0)
    vertical_gap = right_y0 - left_y1
    line_height = max(
        left.heading_block.font_size or 1.0,
        right.heading_block.font_size or 1.0,
    )

    if left.heading_block.font_name and right.heading_block.font_name:
        if (
            left.heading_block.font_name.casefold()
            != right.heading_block.font_name.casefold()
        ):
            return False

    return (
        horizontal_start_delta <= 28.0
        and -1.0 <= vertical_gap <= line_height * 1.3
    )


def _merge_multiline_candidates(
    candidates: list[HeadingCandidate],
) -> tuple[list[HeadingCandidate], int]:
    merged: list[HeadingCandidate] = []
    merge_count = 0

    for candidate in candidates:
        if merged and _can_merge_multiline(
            merged[-1],
            candidate,
        ):
            previous = merged.pop()
            merged.append(
                HeadingCandidate(
                    start_index=previous.start_index,
                    end_index=candidate.end_index,
                    heading_block=previous.heading_block,
                    number=previous.number,
                    title=normalize_heading(
                        f"{previous.title} {candidate.title}"
                    ),
                )
            )
            merge_count += 1
            continue

        merged.append(candidate)

    return merged, merge_count


def _collect_heading_candidates(
    ordered: list[PaperBlock],
    *,
    body_font_size: float | None = None,
) -> tuple[list[HeadingCandidate], int, int, int]:
    """收集、过滤并合并标题候选。"""

    candidates: list[HeadingCandidate] = []
    raw_candidate_count = 0
    rejected_candidate_count = 0

    # 首页最大字号通常是论文主标题。主标题保留，其余 front matter
    # （作者行、机构名、单位）在正文起点之前不进入候选。
    # arXiv 覆盖行（"arXiv:xxxx"）字号虽大但不是标题，需排除。
    page1_max_font_size = max(
        (
            block.font_size
            for block in ordered
            if (
                block.page == 1
                and block.font_size
                and not looks_like_arxiv_overlay(block.text)
            )
        ),
        default=None,
    )
    seen_body_marker = False

    index = 0
    while index < len(ordered):
        block = ordered[index]

        # 硬特征 front matter：邮箱行、KEYWORDS/CCS CONCEPTS/Index Terms。
        if not block.excluded and _is_front_matter_text(block):
            index += 1
            continue

        raw_text = (
            normalize_pdf_text(block.text)
            if not block.excluded
            else ""
        )
        key = normalize_key(normalize_heading(raw_text))
        if (
            key in _UNNUMBERED_HEADINGS
            or _NUMBERED_HEADING_RE.match(raw_text)
            or _APPENDIX_HEADING_RE.match(raw_text)
        ):
            seen_body_marker = True

        # 首页顶部的作者/机构区：正文起点之前、非主标题。
        # 纯编号 block（如 "1"、"A"）可能是拆分的章节编号，不在此列。
        raw_stripped = raw_text.strip()
        is_number_only = bool(
            raw_stripped
            and _SPLIT_HEADING_NUMBER_RE.fullmatch(raw_stripped)
        )
        if (
            block.page == 1
            and not seen_body_marker
            and not block.excluded
            and block.block_type != "title"
            and _has_heading_style(block)
            and not is_number_only
            and (
                page1_max_font_size is None
                or block.font_size is None
                or block.font_size < page1_max_font_size
            )
        ):
            index += 1
            continue

        raw_candidate = _looks_like_raw_heading_candidate(block)

        if index + 1 < len(ordered):
            split_parts = _split_heading_parts(
                block,
                ordered[index + 1],
            )
            if split_parts is not None:
                number, title = split_parts
                raw_candidate_count += 1
                candidates.append(
                    HeadingCandidate(
                        start_index=index,
                        end_index=index + 2,
                        heading_block=block,
                        number=number,
                        title=title,
                    )
                )
                index += 2
                continue

        if raw_candidate:
            raw_candidate_count += 1

        parts = _heading_parts(
            block,
            body_font_size=body_font_size,
        )
        if parts is None:
            if raw_candidate:
                rejected_candidate_count += 1
            index += 1
            continue

        number, title = parts
        candidates.append(
            HeadingCandidate(
                start_index=index,
                end_index=index + 1,
                heading_block=block,
                number=number,
                title=title,
            )
        )
        index += 1

    merged, merge_count = _merge_multiline_candidates(
        candidates
    )
    return (
        merged,
        raw_candidate_count,
        rejected_candidate_count,
        merge_count,
    )


def _heading_level(number: str | None, title: str) -> int:
    if number:
        return number.count(".") + 1
    if normalize_key(title) == "abstract":
        return 1
    return 1


def _parent_number(number: str) -> str | None:
    if "." not in number:
        return None
    return number.rsplit(".", 1)[0]


def classify_section(title: str) -> SectionKind:
    """根据规范化标题给 section 分类。"""

    key = normalize_key(title)

    if "abstract" in key:
        return "abstract"
    if "introduction" in key:
        return "introduction"
    if "related work" in key:
        return "related_work"
    if any(
        word in key
        for word in (
            "implementation detail",
            "training detail",
        )
    ):
        return "implementation"
    if any(
        word in key
        for word in (
            "ablation",
            "influence of",
            "impact of",
        )
    ):
        return "ablation"
    if any(
        word in key
        for word in ("experiment", "evaluation")
    ):
        return "experiments"
    if any(
        word in key
        for word in ("dataset", "benchmark")
    ):
        return "datasets"
    if any(
        word in key
        for word in ("result", "performance")
    ):
        return "results"
    if any(
        word in key
        for word in (
            "method",
            "network",
            "convolution",
            "model",
        )
    ):
        return "method"
    if "conclusion" in key:
        return "conclusion"
    if "reference" in key:
        return "references"
    if "limitation" in key:
        return "limitations"
    if key.startswith("appendix"):
        return "appendix"
    return "other"


def _section_id(
    *,
    number: str | None,
    title: str,
    heading_block_id: str,
) -> str:
    key = (
        f"{number or ''}|"
        f"{normalize_key(title)}|"
        f"{heading_block_id}"
    )
    return f"sec-{_sha256(key)[:12]}"


def _fallback_section(
    ordered: list[PaperBlock],
) -> list[PaperSection]:
    content_blocks = [
        block
        for block in ordered
        if not block.excluded
    ]
    if not content_blocks:
        return []

    content_hash = _sha256(
        "\n".join(
            block.text_hash
            for block in content_blocks
        )
    )
    return [
        PaperSection(
            section_id=f"sec-{content_hash[:12]}",
            title="Document",
            normalized_title="document",
            level=1,
            kind="other",
            page_start=content_blocks[0].page,
            page_end=content_blocks[-1].page,
            block_ids=[
                block.block_id
                for block in content_blocks
            ],
            content_hash=content_hash,
        )
    ]


def build_sections_with_diagnostics(
    blocks: Iterable[PaperBlock],
) -> SectionBuildResult:
    """构建 section，同时返回结构质量诊断。"""

    ordered = sorted(
        blocks,
        key=lambda item: (item.page, item.order),
    )
    body_font_size = _estimate_body_font_size(ordered)
    (
        candidates,
        raw_candidate_count,
        rejected_candidate_count,
        merge_count,
    ) = _collect_heading_candidates(
        ordered,
        body_font_size=body_font_size,
    )

    if not candidates:
        return SectionBuildResult(
            sections=_fallback_section(ordered),
            heading_candidate_count=raw_candidate_count,
            rejected_heading_count=rejected_candidate_count,
            multiline_heading_merge_count=merge_count,
            warnings=[],
        )

    sections: list[PaperSection] = []
    warnings: list[PaperParseWarning] = []
    section_id_by_number: dict[str, str] = {}
    parent_stack: list[tuple[int, str]] = []

    for position, candidate in enumerate(candidates):
        end = (
            candidates[position + 1].start_index
            if position + 1 < len(candidates)
            else len(ordered)
        )
        section_blocks = [
            block
            for block in ordered[
                candidate.start_index:end
            ]
            if not block.excluded
        ]
        if not section_blocks:
            continue

        level = _heading_level(
            candidate.number,
            candidate.title,
        )
        section_id = _section_id(
            number=candidate.number,
            title=candidate.title,
            heading_block_id=(
                candidate.heading_block.block_id
            ),
        )

        parent_id: str | None = None
        if candidate.number:
            expected_parent_number = _parent_number(
                candidate.number
            )
            if expected_parent_number is not None:
                parent_id = section_id_by_number.get(
                    expected_parent_number
                )
                if parent_id is None:
                    warnings.append(
                        PaperParseWarning(
                            code="MISSING_SECTION_PARENT",
                            message=(
                                "Section "
                                f"{candidate.number} has no "
                                "accepted parent "
                                f"{expected_parent_number}."
                            ),
                            page=(
                                candidate.heading_block.page
                            ),
                            block_id=(
                                candidate.heading_block.block_id
                            ),
                        )
                    )
        else:
            # 无编号标题没有显式父编号，才使用保守的层级栈。
            while (
                parent_stack
                and parent_stack[-1][0] >= level
            ):
                parent_stack.pop()
            parent_id = (
                parent_stack[-1][1]
                if parent_stack
                else None
            )

        content_hash = _sha256(
            "\n".join(
                block.text_hash
                for block in section_blocks
            )
        )
        section = PaperSection(
            section_id=section_id,
            number=candidate.number,
            title=candidate.title,
            normalized_title=normalize_key(
                candidate.title
            ),
            level=level,
            kind=classify_section(candidate.title),
            parent_id=parent_id,
            page_start=section_blocks[0].page,
            page_end=section_blocks[-1].page,
            heading_block_id=(
                candidate.heading_block.block_id
            ),
            block_ids=[
                block.block_id
                for block in section_blocks
            ],
            content_hash=content_hash,
        )
        sections.append(section)

        if candidate.number:
            if candidate.number in section_id_by_number:
                warnings.append(
                    PaperParseWarning(
                        code="HEADING_SEQUENCE_CONFLICT",
                        message=(
                            "Duplicate accepted section number: "
                            f"{candidate.number}."
                        ),
                        page=candidate.heading_block.page,
                        block_id=(
                            candidate.heading_block.block_id
                        ),
                    )
                )
            else:
                section_id_by_number[
                    candidate.number
                ] = section_id

        while (
            parent_stack
            and parent_stack[-1][0] >= level
        ):
            parent_stack.pop()
        parent_stack.append((level, section_id))

    return SectionBuildResult(
        sections=sections,
        heading_candidate_count=raw_candidate_count,
        rejected_heading_count=rejected_candidate_count,
        multiline_heading_merge_count=merge_count,
        warnings=warnings,
    )


def build_sections(
    blocks: Iterable[PaperBlock],
) -> list[PaperSection]:
    """保持 Phase 18 调用接口兼容。"""

    return build_sections_with_diagnostics(blocks).sections