from __future__ import annotations

class ArtifactStorageError(RuntimeError):
    """Artifact 持久层错误基类。"""


class ArtifactNotFoundError(ArtifactStorageError):
    """Catalog 或 Blob 中不存在目标 Artifact。"""


class ArtifactIntegrityError(ArtifactStorageError):
    """身份、路径、大小或 SHA-256 不一致。"""


class ArtifactBackendUnavailable(ArtifactStorageError):
    """网络、超时或后端 5xx 等可重试故障。"""