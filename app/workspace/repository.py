from __future__ import annotations

import hashlib
import json
from typing import Any

from app.workspace.errors import WorkspaceIntegrityError
from app.workspace.schemas import (
    WorkspaceBinding,
    WorkspaceManifest,
)


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def workspace_manifest_hash(
    manifest: WorkspaceManifest | dict[str, Any],
) -> str:
    if isinstance(manifest, WorkspaceManifest):
        payload = manifest.model_dump()
    else:
        payload = dict(manifest)

    # identity/观测时间不能改变内容身份，否则 commit response 丢失后无法幂等重放。
    payload.pop("manifest_hash", None)
    payload.pop("manifest_id", None)
    payload.pop("created_at", None)

    # 历史 hash 兼容：该字段在 phase26-v1 创建时不存在。
    if payload.get("manifest_version") == "phase26-v1":
        payload.pop("materialization_mode", None)

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def validate_manifest_hash(manifest: WorkspaceManifest) -> None:
    actual = workspace_manifest_hash(manifest)
    if actual != manifest.manifest_hash:
        raise WorkspaceIntegrityError(
            "Workspace manifest hash 校验失败"
        )


def manifest_from_row(row: Any) -> WorkspaceManifest:
    manifest = WorkspaceManifest.model_validate(row["manifest_json"])
    validate_manifest_hash(manifest)
    if (
        manifest.manifest_id != row["manifest_id"]
        or manifest.manifest_hash != row["manifest_hash"]
    ):
        raise WorkspaceIntegrityError(
            "manifest row identity 与 JSON 不一致"
        )
    return manifest


def binding_from_row(row: Any) -> WorkspaceBinding:
    return WorkspaceBinding(
        assignment_id=str(row["assignment_id"]),
        assignment_epoch=int(row["assignment_epoch"]),
        assignment_token=str(row["assignment_token"]),
        job_id=str(row["job_id"]),
        run_id=str(row["run_id"]),
        manifest_id=str(row["manifest_id"]),
        manifest_hash=str(row["manifest_hash"]),
        manifest_generation=int(row["manifest_generation"]),
        worker_session_id=str(row["worker_session_id"]),
        host_id=str(row["host_id"]),
        workspace_root=str(row["workspace_root"]),
        run_dir=str(row["run_dir"]),
        repo_path=str(row["repo_path"]),
        paper_path=str(row["paper_path"]),
        log_path=row["log_path"],
        status=str(row["status"]),
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )
