from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.graph import build_graph
from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.job_runtime.errors import (
    JobConflictError,
    JobNotFoundError,
)
from app.schemas import ArtifactRecord
from app.tools.artifact_tools import sha256_file
from app.storage.ports import (
    OpenedArtifact,
    OpenedBlob,
)
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)
from app.workspace.paths import require_managed_run_root


StateReader = Callable[
    [str],
    dict[str, Any],
]


@dataclass(frozen=True)
class ResolvedArtifact:
    """只在 API 内部短暂存在，不能直接序列化返回。"""

    record: ArtifactRecord
    path: Path


def read_graph_state(
    thread_id: str,
) -> dict[str, Any]:
    """从 LangGraph checkpoint 读取当前完整 state。"""

    snapshot = build_graph().get_state(
        {
            "configurable": {
                "thread_id": thread_id,
            }
        }
    )
    return dict(
        getattr(
            snapshot,
            "values",
            {},
        )
        or {}
    )


class ArtifactCatalog(Protocol):
    """
    HTTP 层只依赖该协议。

    LocalArtifactCatalog 和 PublishedArtifactCatalog 都通过结构化类型
    自动满足，不需要继承。
    """

    def list_views(
        self,
        job: JobRecord,
    ) -> list[ArtifactView]:
        ...

    def open(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> OpenedArtifact:
        ...
    

class LocalArtifactCatalog:
    """
    当前本地 Artifact 适配器。

    API 依赖这个 catalog，而不是直接拼接 runs 路径。Phase 24 可增加
    S3ArtifactStore，同时保持 HTTP 协议不变。
    """

    def __init__(
        self,
        *,
        state_reader: StateReader = read_graph_state,
    ):
        self.state_reader = state_reader

    def _run_root(
        self,
        job: JobRecord,
    ) -> Path:
        run_root = require_managed_run_root(job.run_dir)
        return run_root

    def _manifest_records(
        self,
        run_root: Path,
    ) -> list[dict[str, Any]]:
        """
        checkpoint 不可用时读取最终 Artifact index。

        这只是当前本地实现的恢复路径，不进入公开 API schema。
        """

        index_path = (
            run_root
            / "reports"
            / "artifact_index.json"
        )
        if not index_path.is_file():
            return []
        try:
            payload = json.loads(
                index_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise JobConflictError(
                f"无法读取 Artifact index：{exc}"
            ) from exc
        return list(
            payload.get("artifacts", [])
        )

    def records(
        self,
        job: JobRecord,
    ) -> list[ArtifactRecord]:
        run_root = self._run_root(job)
        state = self.state_reader(
            job.thread_id
        )

        raw_records = state.get(
            "artifact_records",
            [],
        )
        if not raw_records:
            raw_records = (
                self._manifest_records(
                    run_root
                )
            )

        records: dict[
            str,
            ArtifactRecord,
        ] = {}
        for raw in raw_records:
            record = (
                ArtifactRecord.model_validate(
                    raw
                )
            )
            if record.run_id != job.run_id:
                raise JobConflictError(
                    "Artifact run_id 与 Job 不匹配"
                )
            previous = records.get(
                record.artifact_id
            )
            if (
                previous is not None
                and previous.relative_path
                != record.relative_path
            ):
                raise JobConflictError(
                    "同一 artifact_id 对应多个路径"
                )
            records[record.artifact_id] = (
                record
            )

        return sorted(
            records.values(),
            key=lambda item: (
                item.layer,
                item.relative_path,
            ),
        )

    def list_views(
        self,
        job: JobRecord,
    ) -> list[ArtifactView]:
        # 列表查询不逐个计算大文件 hash，下载时再做强校验。
        return [
            ArtifactView(
                artifact_id=item.artifact_id,
                run_id=item.run_id,
                layer=item.layer,
                relative_path=(
                    item.relative_path
                ),
                media_type=item.media_type,
                sha256=item.sha256,
                size_bytes=item.size_bytes,
                producer_node=(
                    item.producer_node
                ),
                created_at=item.created_at,
                integrity_status="unchecked",
            )
            for item in self.records(job)
        ]

    def resolve(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> ResolvedArtifact:
        run_root = self._run_root(job)
        record = next(
            (
                item
                for item in self.records(job)
                if item.artifact_id
                == artifact_id
            ),
            None,
        )
        if record is None:
            raise JobNotFoundError(
                "当前 Job 中不存在 "
                f"artifact_id={artifact_id}"
            )

        # 只使用受校验的 run_root + relative_path。
        # 不信任 record.absolute_path。
        candidate = (
            run_root
            / record.relative_path
        ).resolve()
        if (
            candidate == run_root
            or run_root not in candidate.parents
        ):
            raise JobConflictError(
                "Artifact 路径逃逸当前 run"
            )
        if not candidate.is_file():
            raise JobNotFoundError(
                "Artifact 文件不存在"
            )
        if candidate.stat().st_size != (
            record.size_bytes
        ):
            raise JobConflictError(
                "Artifact 大小与记录不一致"
            )
        if sha256_file(candidate) != record.sha256:
            raise JobConflictError(
                "Artifact SHA-256 校验失败"
            )

        return ResolvedArtifact(
            record=record,
            path=candidate,
        )
    def open(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> OpenedArtifact:
        """Phase 23 本地兼容适配器。"""

        resolved = self.resolve(
            job=job,
            artifact_id=artifact_id,
        )
        descriptor = (
            ArtifactDescriptor.from_record(
                resolved.record
            )
        )
        published = PublishedArtifact(
            job_id=job.job_id,
            descriptor=descriptor,
            backend="legacy-local",
            object_key=(
                resolved.record.relative_path
            ),
            etag=resolved.record.sha256,
            revision=1,
            published_at=(
                resolved.record.created_at
            ),
        )
        return OpenedArtifact(
            artifact=published,
            blob=OpenedBlob(
                stat=BlobStat(
                    backend="legacy-local",
                    object_key=(
                        resolved.record
                        .relative_path
                    ),
                    size_bytes=(
                        resolved.record
                        .size_bytes
                    ),
                    sha256=(
                        resolved.record.sha256
                    ),
                    etag=(
                        resolved.record.sha256
                    ),
                ),
                body=resolved.path.open("rb"),
            ),
        )