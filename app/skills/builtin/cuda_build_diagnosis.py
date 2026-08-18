from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.skills.runtime import SkillRuntime


class CudaSkillModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _safe_relative_path(value: str) -> str:
    raw = value.strip()
    if "\\" in raw:
        raise ValueError("路径必须使用 POSIX 分隔符")
    path = PurePosixPath(raw)
    normalized = path.as_posix()
    if (
        not raw
        or path.is_absolute()
        or raw != normalized
        or ".." in path.parts
        or ":" in path.parts[0]
        or normalized == "."
    ):
        raise ValueError("路径必须是受控根目录内的相对路径")
    return normalized


class CudaBuildDiagnosisInput(CudaSkillModel):
    repo_path: str = Field(min_length=1, max_length=4096)
    log_path: str = Field(min_length=1, max_length=4096)
    max_log_chars: int = Field(default=30_000, ge=1000, le=100_000)

    @field_validator("repo_path", "log_path")
    @classmethod
    def validate_paths(cls, value: str) -> str:
        return _safe_relative_path(value)


class CudaBuildEvidenceRef(CudaSkillModel):
    tool_call_id: str = Field(pattern=r"^toolcall_[0-9a-f]{16}$")
    source_type: Literal["log", "traceback", "repository_search"]
    relative_path: str | None = None
    line: int | None = Field(default=None, ge=1)

    @field_validator("relative_path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _safe_relative_path(value)


class CudaBuildDiagnosisOutput(CudaSkillModel):
    error_category: Literal[
        "dependency_missing",
        "cuda_toolchain",
        "extension_abi",
        "compiler_compatibility",
        "cuda_architecture",
        "build_backend",
        "unknown_cuda_build",
    ]
    finding_codes: list[str] = Field(min_length=1, max_length=12)
    related_files: list[str] = Field(default_factory=list, max_length=30)
    evidence_refs: list[CudaBuildEvidenceRef] = Field(
        min_length=1,
        max_length=30,
    )
    recommended_checks: list[str] = Field(min_length=1, max_length=12)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_main_agent_proposal: Literal[True] = True

    @field_validator("related_files")
    @classmethod
    def validate_related_files(cls, value: list[str]) -> list[str]:
        return [_safe_relative_path(item) for item in value]


def _last_call_id(runtime: SkillRuntime) -> str:
    references = runtime.tool_call_refs
    if not references:
        raise RuntimeError("Skill Tool 调用记录缺失")
    return references[-1].call_id


def _classify_findings(text: str) -> tuple[str, list[str]]:
    lowered = text.lower()
    findings: list[str] = []

    if "nvcc" in lowered and any(
        marker in lowered
        for marker in ["not found", "no such file", "is not recognized"]
    ):
        findings.append("NVCC_NOT_FOUND")
    if "undefined symbol" in lowered or "symbol not found" in lowered:
        findings.append("EXTENSION_ABI_MISMATCH")
    if any(
        marker in lowered
        for marker in [
            "unsupported gcc version",
            "unsupported gnu version",
            "compiler version is not supported",
        ]
    ):
        findings.append("HOST_COMPILER_MISMATCH")
    if any(
        marker in lowered
        for marker in [
            "unsupported gpu architecture",
            "unsupported cuda architecture",
            "nvcc fatal   : unsupported",
        ]
    ):
        findings.append("CUDA_ARCH_UNSUPPORTED")
    if "ninja" in lowered and any(
        marker in lowered
        for marker in ["failed", "error", "stopped"]
    ):
        findings.append("NINJA_BUILD_FAILURE")
    if any(
        marker in lowered
        for marker in ["cuda_home", "cuda toolkit", "cuda extension"]
    ):
        findings.append("CUDA_TOOLCHAIN_CONFIGURATION")

    findings = list(dict.fromkeys(findings))
    if not findings:
        return "unknown_cuda_build", ["CUDA_BUILD_FAILURE_UNCLASSIFIED"]
    if "NVCC_NOT_FOUND" in findings:
        return "cuda_toolchain", findings
    if "EXTENSION_ABI_MISMATCH" in findings:
        return "extension_abi", findings
    if "HOST_COMPILER_MISMATCH" in findings:
        return "compiler_compatibility", findings
    if "CUDA_ARCH_UNSUPPORTED" in findings:
        return "cuda_architecture", findings
    if "NINJA_BUILD_FAILURE" in findings:
        return "build_backend", findings
    return "cuda_toolchain", findings


def _search_keywords(finding_codes: list[str]) -> list[str]:
    mapping = {
        "NVCC_NOT_FOUND": ["CUDA_HOME", "nvcc"],
        "EXTENSION_ABI_MISMATCH": ["CUDAExtension", "cpp_extension"],
        "HOST_COMPILER_MISMATCH": ["gcc", "CC"],
        "CUDA_ARCH_UNSUPPORTED": ["TORCH_CUDA_ARCH_LIST", "gencode"],
        "NINJA_BUILD_FAILURE": ["BuildExtension", "ninja"],
        "CUDA_TOOLCHAIN_CONFIGURATION": ["CUDA_HOME", "CUDAExtension"],
        "CUDA_BUILD_FAILURE_UNCLASSIFIED": ["CUDAExtension", "setup.py"],
    }
    values: list[str] = []
    for code in finding_codes:
        values.extend(mapping.get(code, []))
    return list(dict.fromkeys(values))[:5]


def _recommended_checks(finding_codes: list[str]) -> list[str]:
    checks: list[str] = []
    mapping = {
        "NVCC_NOT_FOUND": (
            "核对当前执行环境是否安装 CUDA Toolkit，以及 CUDA_HOME "
            "是否指向包含 nvcc 的同一版本目录。"
        ),
        "EXTENSION_ABI_MISMATCH": (
            "核对 PyTorch、CUDA、Python 和已编译扩展的 ABI 身份，"
            "不要复用其他环境生成的二进制扩展。"
        ),
        "HOST_COMPILER_MISMATCH": (
            "根据当前 CUDA Toolkit 支持矩阵核对 GCC/G++ 版本，"
            "先记录版本事实，再形成环境变更提案。"
        ),
        "CUDA_ARCH_UNSUPPORTED": (
            "核对 GPU compute capability 与构建配置中的架构列表，"
            "确认没有沿用不受当前 nvcc 支持的架构。"
        ),
        "NINJA_BUILD_FAILURE": (
            "向前检查 ninja 最终报错之前的第一条编译器错误，"
            "不要把汇总行本身当作根因。"
        ),
        "CUDA_TOOLCHAIN_CONFIGURATION": (
            "核对 PyTorch 识别到的 CUDA 版本与系统 Toolkit 路径是否一致。"
        ),
        "CUDA_BUILD_FAILURE_UNCLASSIFIED": (
            "保留完整编译日志，并从首个 compiler error 开始补充诊断证据。"
        ),
    }
    for code in finding_codes:
        check = mapping.get(code)
        if check and check not in checks:
            checks.append(check)
    return checks


def diagnose_cuda_build(
    payload: CudaBuildDiagnosisInput,
    runtime: SkillRuntime,
) -> CudaBuildDiagnosisOutput:
    log_output = runtime.call_tool(
        "log.read_log",
        {
            "path": payload.log_path,
            "max_chars": payload.max_log_chars,
        },
    )
    log_call_id = _last_call_id(runtime)
    log_text = str(log_output.get("text") or "")

    traceback_output = runtime.call_tool(
        "log.extract_traceback",
        {"text": log_text},
    )
    traceback_call_id = _last_call_id(runtime)
    traceback_text = str(traceback_output.get("text") or "")

    heuristic_output = runtime.call_tool(
        "log.classify_error_heuristic",
        {"text": traceback_text or log_text},
    )
    heuristic_category = str(
        heuristic_output.get("category") or "unknown"
    )

    paths_output = runtime.call_tool(
        "log.extract_repo_traceback_paths",
        {
            "traceback": traceback_text,
            "repo_path": payload.repo_path,
        },
    )
    traceback_paths = [
        str(item) for item in paths_output.get("paths", [])
    ]

    error_category, finding_codes = _classify_findings(
        f"{log_text}\n{traceback_text}"
    )
    if (
        error_category == "unknown_cuda_build"
        and heuristic_category == "dependency_missing"
    ):
        error_category = "dependency_missing"
        finding_codes = ["DEPENDENCY_OR_BUILD_TOOL_MISSING"]

    search_output = runtime.call_tool(
        "search.search_keywords",
        {
            "repo_path": payload.repo_path,
            "keywords": _search_keywords(finding_codes),
            "max_per_keyword": 6,
            "timeout_seconds": 10,
        },
    )
    search_call_id = _last_call_id(runtime)
    matches = list(search_output.get("matches", []))[:20]

    related_files = list(
        dict.fromkeys(
            [
                *traceback_paths,
                *[
                    str(item["file_path"])
                    for item in matches
                    if item.get("file_path")
                ],
            ]
        )
    )[:30]
    evidence_refs = [
        CudaBuildEvidenceRef(
            tool_call_id=log_call_id,
            source_type="log",
            relative_path=payload.log_path,
        ),
        CudaBuildEvidenceRef(
            tool_call_id=traceback_call_id,
            source_type="traceback",
            relative_path=payload.log_path,
        ),
        *[
            CudaBuildEvidenceRef(
                tool_call_id=search_call_id,
                source_type="repository_search",
                relative_path=str(item["file_path"]),
                line=int(item["line"]),
            )
            for item in matches
            if item.get("file_path") and item.get("line")
        ],
    ][:30]

    return CudaBuildDiagnosisOutput(
        error_category=error_category,
        finding_codes=finding_codes,
        related_files=related_files,
        evidence_refs=evidence_refs,
        recommended_checks=_recommended_checks(finding_codes),
        confidence=(0.9 if finding_codes[0] != "CUDA_BUILD_FAILURE_UNCLASSIFIED" else 0.45),
        requires_main_agent_proposal=True,
    )
