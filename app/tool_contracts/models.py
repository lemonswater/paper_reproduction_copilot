from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, field_validator, model_validator

from app.tool_contracts.schemas import ContractModel

if TYPE_CHECKING:
    from app.research_browser.schemas import (
        ResearchEvidenceDraft,
        ResearchRequest,
    )


def _validate_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise ValueError("输出路径必须是安全的仓库相对路径")
    return path.as_posix()


class RepoTreeInput(ContractModel):
    repo_path: str = Field(min_length=1, max_length=4096)
    max_depth: int = Field(default=3, ge=1, le=8)


class RepoTreeOutput(ContractModel):
    tree: str = Field(max_length=200_000)


class RepoPathInput(ContractModel):
    repo_path: str = Field(min_length=1, max_length=4096)


class RepoListFilesInput(ContractModel):
    repo_path: str = Field(min_length=1, max_length=4096)
    suffixes: list[str] | None = Field(default=None, max_length=32)

    @field_validator("suffixes")
    @classmethod
    def validate_suffixes(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for suffix in value:
            item = suffix.strip().lower()
            if not item.startswith(".") or len(item) > 20:
                raise ValueError("suffix 必须是类似 .py 的短扩展名")
            if item not in normalized:
                normalized.append(item)
        return normalized


class RelativeFilesOutput(ContractModel):
    files: list[str] = Field(max_length=20_000)

    @field_validator("files")
    @classmethod
    def validate_files(cls, value: list[str]) -> list[str]:
        return [_validate_relative_path(item) for item in value]


class RepoClassificationOutput(ContractModel):
    readme_files: list[str]
    train_entries: list[str]
    eval_entries: list[str]
    config_files: list[str]
    model_files: list[str]
    dataset_files: list[str]
    loss_files: list[str]

    @field_validator("*", mode="after")
    @classmethod
    def validate_paths(cls, value: list[str]) -> list[str]:
        return [_validate_relative_path(item) for item in value]


class SearchTextInput(ContractModel):
    repo_path: str = Field(min_length=1, max_length=4096)
    query: str = Field(min_length=1, max_length=1000)
    max_results: int = Field(default=20, ge=1, le=200)
    literal: bool = True
    ignore_case: bool = True
    timeout_seconds: int = Field(default=10, ge=1, le=60)


class SearchKeywordsInput(ContractModel):
    repo_path: str = Field(min_length=1, max_length=4096)
    # 最多 5 个关键词，每个最多等待 10 秒，使整个 Adapter 保持在 60 秒契约上限内。
    keywords: list[str] = Field(min_length=1, max_length=5)
    max_per_keyword: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=10, ge=1, le=10)

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if not normalized:
            raise ValueError("keywords 不能全部为空")
        if any(len(item) > 1000 for item in normalized):
            raise ValueError("单个 keyword 不能超过 1000 字符")
        return normalized


class SearchMatch(ContractModel):
    file_path: str
    line: int = Field(ge=1)
    text: str = Field(max_length=20_000)

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, value: str) -> str:
        return _validate_relative_path(value)


class KeywordSearchMatch(SearchMatch):
    keyword: str = Field(min_length=1, max_length=1000)


class SearchTextOutput(ContractModel):
    matches: list[SearchMatch] = Field(max_length=200)


class SearchKeywordsOutput(ContractModel):
    matches: list[KeywordSearchMatch] = Field(max_length=500)


class CodeSliceInput(ContractModel):
    path: str = Field(min_length=1, max_length=4096)
    start_line: int = Field(default=1, ge=1)
    end_line: int = Field(default=120, ge=1)

    @model_validator(mode="after")
    def validate_window(self) -> CodeSliceInput:
        if self.end_line < self.start_line:
            raise ValueError("end_line 不能小于 start_line")
        if self.end_line - self.start_line + 1 > 500:
            raise ValueError("单次最多读取 500 行")
        return self


class CodeSliceOutput(ContractModel):
    text: str = Field(max_length=200_000)


class PythonSymbolsInput(ContractModel):
    path: str = Field(min_length=1, max_length=4096)


class PythonSymbol(ContractModel):
    type: Literal["class", "function"]
    name: str = Field(min_length=1, max_length=300)
    line: int = Field(ge=1)


class PythonSymbolsOutput(ContractModel):
    symbols: list[PythonSymbol] = Field(max_length=10_000)


class ReadLogInput(ContractModel):
    path: str = Field(min_length=1, max_length=4096)
    max_chars: int = Field(default=30_000, ge=1, le=100_000)


class TextTransformInput(ContractModel):
    text: str = Field(max_length=200_000)


class TextOutput(ContractModel):
    text: str = Field(max_length=200_000)


class ErrorClassificationOutput(ContractModel):
    category: Literal[
        "dependency_missing",
        "data_or_path_error",
        "cuda_oom",
        "shape_mismatch",
        "permission_error",
        "unknown",
    ]


class TracebackPathsInput(ContractModel):
    traceback: str = Field(max_length=200_000)
    repo_path: str | None = Field(default=None, max_length=4096)


class TracebackPathsOutput(ContractModel):
    paths: list[str] = Field(max_length=200)

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, value: list[str]) -> list[str]:
        return [_validate_relative_path(item) for item in value]


class ActionRiskInput(ContractModel):
    action: dict[str, Any]

    @model_validator(mode="after")
    def limit_action_size(self) -> ActionRiskInput:
        payload = json.dumps(
            self.action,
            ensure_ascii=False,
            default=str,
        )
        if len(payload) > 20_000:
            raise ValueError("action payload 过大")
        return self


class ActionRiskOutput(ContractModel):
    program: str
    args: list[str]
    risk_level: Literal["low", "medium", "high", "blocked"]
    reason: str
    blocked: bool


class ResearchCollectInput(ContractModel):
    request: "ResearchRequest"


class ResearchCollectOutput(ContractModel):
    evidence: "ResearchEvidenceDraft"


# Avoid circular import at module load time; resolve at call time.
def _resolve_research_schemas() -> None:
    from app.research_browser.schemas import (
        ResearchEvidenceDraft,
        ResearchRequest,
    )
    globals()["ResearchRequest"] = ResearchRequest
    globals()["ResearchEvidenceDraft"] = ResearchEvidenceDraft


_resolve_research_schemas()

ResearchCollectInput.model_rebuild()
ResearchCollectOutput.model_rebuild()
