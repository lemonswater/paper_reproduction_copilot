# app/run_evidence/errors.py
class RunEvidenceError(RuntimeError):
    """已完成 Run 的可信证据读取错误基类。"""


class RunEvidenceNotFoundError(RunEvidenceError):
    """所需运行 Artifact 不存在或数量不唯一。"""


class RunEvidenceConflictError(RunEvidenceError):
    """Job 状态或 Manifest 版本不满足读取前提。"""


class RunEvidenceIntegrityError(RunEvidenceError):
    """Job、Workspace、Catalog、Descriptor 或 Blob 身份不一致。"""


class RunEvidenceLimitExceededError(RunEvidenceError):
    """Manifest 或 Artifact 数量超过有界读取上限。"""
