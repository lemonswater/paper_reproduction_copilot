from __future__ import annotations

import re
import unicodedata

_MULTI_SPACE_RE = re.compile(r"\s+")
_LETTER_SPACING_RE = re.compile(r"\b([A-Z])\s+([A-Z][A-Z0-9a-z-]+)\b")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
_SPACE_AROUND_HYPHEN_RE = re.compile(r"\s*-\s*")


def normalize_pdf_text(text: str) -> str:
    """清理 PDF 抽取产生的空白，但不改变事实内容。"""

    value = unicodedata.normalize("NFKC", text)
    value = value.replace("\u00ad", "")
    value = value.replace("\u00a0", " ")
    value = _MULTI_SPACE_RE.sub(" ", value).strip()
    value = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", value)
    return value


def normalize_heading(text: str) -> str:
    """把分散的大写标题恢复为适合匹配的形式。"""

    value = normalize_pdf_text(text)

    # 连续执行是因为一个标题中可能存在多个 “P ROPOSED” 形式的单词。
    previous = None
    while previous != value:
        previous = value
        value = _LETTER_SPACING_RE.sub(r"\1\2", value)

    value = _SPACE_AROUND_HYPHEN_RE.sub("-", value)
    return value.strip()


def normalize_key(text: str) -> str:
    """生成去格式差异的比较键，用于去重和冲突识别。"""

    value = normalize_heading(text).casefold()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    return _MULTI_SPACE_RE.sub(" ", value).strip()


def looks_like_arxiv_overlay(text: str) -> bool:
    """过滤首页上字号很大、但并非论文标题的 arXiv 叠加信息。"""

    value = normalize_pdf_text(text).casefold()
    return value.startswith("arxiv:") or bool(
        re.search(r"\barxiv:\d{4}\.\d+", value)
    )