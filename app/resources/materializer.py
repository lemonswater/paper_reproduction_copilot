"""Phase 29 Resource -> Workspace 物化适配器。

把 published Resource 作为只读输入物化进 Workspace。Materializer 继续使用
Phase 26 的：object stat → stream/copy → expected size → SHA-256 →
atomic rename → workspace path containment。

逻辑路径：
- paper_pdf       -> source/paper.pdf
- git_repository  -> capsule/repository.bundle
- checkpoint      -> inputs/checkpoints/<resource_id>.bin

OCI mount：repo 只读、run 可写、checkpoint 单独只读。论文程序如果需要
checkpoint 路径，应由 Action/Profile 注入确定性容器路径，不能让 LLM 指定。
"""

from __future__ import annotations

from app.resources.schemas import ResourceManifest
from app.workspace.schemas import WorkspaceBlobEntry

RESOURCE_LOGICAL_PATHS: dict[str, str] = {
    "paper_pdf": "source/paper.pdf",
    "git_repository": "capsule/repository.bundle",
}

RESOURCE_ENTRY_ROLES: dict[str, str] = {
    "paper_pdf": "paper",
    "git_repository": "repository_bundle",
}


def resource_logical_path(
    *,
    kind: str,
    resource_id: str,
) -> str:
    """计算 resource 在 workspace 中的逻辑路径。"""

    if kind in RESOURCE_LOGICAL_PATHS:
        return RESOURCE_LOGICAL_PATHS[kind]
    if kind == "checkpoint":
        safe_id = resource_id
        if "/" in safe_id or safe_id in {".", ".."}:
            raise ValueError(
                "resource_id 不能用作 checkpoint 文件名"
            )
        return f"inputs/checkpoints/{safe_id}.bin"
    raise ValueError(f"未知 resource kind：{kind}")


def resource_workspace_entry(
    *,
    manifest: ResourceManifest,
) -> WorkspaceBlobEntry:
    """把 ResourceManifest 转为只读 WorkspaceBlobEntry。

    直接引用同一 Blob object_key，避免再次上传内容。
    """

    logical_path = resource_logical_path(
        kind=manifest.kind,
        resource_id=manifest.resource_id,
    )
    role = RESOURCE_ENTRY_ROLES.get(manifest.kind, "paper")
    media_type = (
        "application/pdf"
        if manifest.kind == "paper_pdf"
        else manifest.media_type
    )
    return WorkspaceBlobEntry(
        logical_path=logical_path,
        role=role,  # type: ignore[arg-type]
        object_key=manifest.object_key,
        sha256=manifest.sha256,
        size_bytes=manifest.size_bytes,
        media_type=media_type,
        executable=False,
    )


def resolved_resource_workspace_entry(
    *,
    resolved,
) -> WorkspaceBlobEntry:
    """从 ResolvedResourceInput 直接构建只读 WorkspaceBlobEntry。

    Job 已冻结 manifest snapshot；无需重建完整 ResourceManifest，
    只需要 content identity（object_key/sha256/size/kind）。
    """

    logical_path = resource_logical_path(
        kind=resolved.kind,
        resource_id=resolved.resource_id,
    )
    role = RESOURCE_ENTRY_ROLES.get(resolved.kind, "paper")
    media_type = (
        "application/pdf"
        if resolved.kind == "paper_pdf"
        else "application/octet-stream"
    )
    return WorkspaceBlobEntry(
        logical_path=logical_path,
        role=role,  # type: ignore[arg-type]
        object_key=resolved.object_key,
        sha256=resolved.content_sha256,
        size_bytes=resolved.size_bytes,
        media_type=media_type,
        executable=False,
    )
