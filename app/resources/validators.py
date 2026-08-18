from __future__ import annotations

"""Phase 29 PDF 与 checkpoint 验证器。

获取阶段绝不 ``torch.load``/``pickle.load`` checkpoint：
只做 opaque blob + hash 身份验证。真正加载发生在受控 OCI 运行中
（优先 ``weights_only=True``）。
"""

from pathlib import Path

from app.resources.errors import ResourceIntegrityError


def validate_pdf(path: Path) -> str:
    """校验 PDF magic bytes 与可解析性。

    pymupdf(fitz) 可能未安装（如离线测试环境）；此时只做 magic bytes 校验，
    parser/page 检查降级跳过。生产部署应安装 pymupdf 以启用完整校验。
    """

    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise ResourceIntegrityError(
                "paper_pdf magic bytes 不是 PDF"
            )

    page_count: int | None = None
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError:
        fitz = None

    if fitz is not None:
        try:
            document = fitz.open(path)
            page_count = document.page_count
            document.close()
        except Exception as exc:  # noqa: BLE001
            raise ResourceIntegrityError(
                "PDF parser 无法打开文件"
            ) from exc
        if page_count is not None and page_count < 1:
            raise ResourceIntegrityError("PDF 没有页面")

    return "application/pdf"


def validate_checkpoint_opaque(path: Path) -> str:
    """checkpoint 作为 opaque blob：只校验非空文件存在。

    获取阶段绝不 torch.load/pickle.load，只做 hash 身份验证。
    """

    if (
        not path.is_file()
        or path.stat().st_size == 0
    ):
        raise ResourceIntegrityError(
            "checkpoint 为空或不存在"
        )
    return "application/octet-stream"


def validate_for_kind(
    path: Path, kind: str
) -> str:
    if kind == "paper_pdf":
        return validate_pdf(path)
    if kind == "checkpoint":
        return validate_checkpoint_opaque(path)
    # git_repository 的发布内容是 bundle，由 git_fetcher 单独校验 identity。
    if kind == "git_repository":
        if (
            not path.is_file()
            or path.stat().st_size == 0
        ):
            raise ResourceIntegrityError(
                "git bundle 为空或不存在"
            )
        return "application/octet-stream"
    raise ResourceIntegrityError(
        f"未知 resource kind：{kind}"
    )
