# app/run_evidence/schemas.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.workspace.schemas import WorkspaceManifest


@dataclass(frozen=True)
class VerifiedRunEvidence:
    """仅在受信任服务内部传递，不直接作为 API response。"""

    job: JobRecord
    workspace: WorkspaceManifest
    artifacts: tuple[ArtifactView, ...]
    run_manifest_artifact: ArtifactView
    run_manifest: dict[str, Any]
