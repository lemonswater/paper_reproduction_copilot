from __future__ import annotations


class ArtifactDeliveryError(RuntimeError):
    """Artifact 交付层错误基类。"""


class ArtifactPreviewUnsupported(ArtifactDeliveryError):
    """Artifact 可以下载，但不允许在浏览器内预览。"""


class ArtifactExportLimitExceeded(ArtifactDeliveryError):
    """导出数量、未压缩大小或压缩包大小超过配置上限。"""
