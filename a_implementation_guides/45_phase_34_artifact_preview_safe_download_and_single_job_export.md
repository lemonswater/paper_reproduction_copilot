# Phase 34：Artifact 安全预览、下载与单 Job 导出

> 本章是在 Phase 33 已完成之后的下一阶段实现教程。
>
> 本章会给出需要新增或修改的文件、带上下文的核心代码、测试代码、测试命令和手工验收步骤；本教程本身不会直接修改 `app/`、`tests/` 或 `web/`。

---

## 一、为什么下一阶段优先补齐结果交付

> **本节类型：设计说明，不修改项目代码。**

Phase 33 已经把本机论文和仓库安全导入为不可变 Resource，系统入口形成了闭环。当前输出端已经有：

```text
ArtifactRecord
  -> ArtifactPublisher
  -> ArtifactRepository + BlobStore
  -> ArtifactCatalog.list_views()/open()
  -> Web Artifact 列表与 Chat citation
```

但是用户拿到结果时仍有三个明显缺口：

1. Web 中点击 Artifact 只能下载，不能快速查看 Markdown、JSON、日志和补丁；
2. 现有下载响应直接沿用 Artifact 的 media type，浏览器和代理可能尝试解释内容；
3. 一个 Job 的报告、证据、日志和 manifest 分散在多个 Artifact 中，不能一次性导出归档。

因此，下一阶段最值得做的是：

```text
ArtifactCatalog
  |- 有界文本预览（JSON 响应）
  |- 强制附件下载（application/octet-stream）
  `- 单 Job ZIP 导出（manifest + 全部 Artifact）
```

这一步不提高论文复现成功率，但会显著提高产品完整性：用户可以查看、取走、验证和保存 Agent 的结果。它也为后续的数据保留、配额与垃圾回收提供了清晰的交付边界。

---

## 二、本阶段完成后的能力

> **本节类型：目标说明，不修改项目代码。**

完成后应满足：

1. Artifact 列表明确告诉前端哪些条目允许预览；
2. 预览只支持显式允许的文本媒体类型和扩展名；
3. HTML、SVG、二进制、无效 UTF-8 和含 NUL 的内容不能预览；
4. 预览读取有字节上限，并返回 `truncated`，不会把大文件全部载入内存；
5. 前端使用 React 文本节点和 `<pre>` 显示内容，不执行 Markdown、HTML 或脚本；
6. 单 Artifact 下载始终使用 `Content-Disposition: attachment`；
7. 下载始终使用 `application/octet-stream` 和 `nosniff`；
8. 下载和预览都继续通过 `artifact_id + job_id` 打开 Catalog；
9. 单 Job 导出包含当前 Artifact 快照和公开 Job 信息；
10. ZIP 内包含可验证的 `metadata/export_manifest.json`；
11. 导出逐项重新核对 artifact id、run id、路径、大小和 SHA-256；
12. Artifact 在“列出后、打开前”发生变化时，导出失败而不是悄悄混入新内容；
13. 导出先完整构建并校验，成功后才开始返回 HTTP 响应；
14. 构建失败时删除 `.part` 文件；客户端下载结束或中断后删除临时 ZIP；
15. staging 位于项目目录内，不使用系统 `/tmp`；
16. Artifact 数量、未压缩总大小、ZIP 大小和 staging 生命周期都有上限；
17. 本地 BlobStore 与 S3/MinIO 继续使用同一套 ArtifactDeliveryService；
18. 现有 `/content` 下载地址保留为兼容别名。

---

## 三、本阶段明确不做

> **本节类型：范围说明，不修改项目代码。**

```text
不在线渲染任意 HTML 或 SVG
不把 Markdown 转换为可执行 HTML
不实现 PDF、图片、视频或模型权重在线预览
不支持任意服务端文件路径下载
不让前端传入 ZIP 内部路径
不把导出 ZIP 再注册成当前 Job 的 Artifact
不实现跨 Job 批量导出
不实现密码保护 ZIP
不实现 HTTP Range、断点续传或对象存储预签名 URL
不在 ZIP 中放入 run_dir、object_key、API token、claim token 或本地绝对路径
不在 ZIP 构建失败后返回半个成功响应
不引入 Celery、Redis、消息队列或单独导出 Worker
不实现数据保留和自动 GC；本阶段只做过期 staging 清理
```

导出包是“交付视图”，不是新的运行产物。如果将它再次发布为 Artifact，下一次导出可能把上一次 ZIP 也打包进去，形成递归和生命周期混乱。

---

## 四、核心协议与安全边界

> **本节类型：架构说明，不修改项目代码。**

### 4.1 三条 API

```text
GET /v1/jobs/{job_id}/artifacts
    返回 Artifact 元数据和 preview_supported。

GET /v1/jobs/{job_id}/artifacts/{artifact_id}/preview
    返回有界 UTF-8 文本 JSON，不返回任意媒体内容。

GET /v1/jobs/{job_id}/artifacts/{artifact_id}/download
    强制以附件下载单个 Artifact。

GET /v1/jobs/{job_id}/export
    返回已经完整构建并校验的 ZIP。
```

原地址继续保留：

```text
GET /v1/jobs/{job_id}/artifacts/{artifact_id}/content
    与 /download 使用同一实现，作为兼容别名。
```

### 4.2 不接受路径参数

以下接口是错误设计：

```text
GET /v1/files?path=/data/.../final_report.md
GET /v1/jobs/{job_id}/preview?relative_path=../../.env
```

正确边界是：

```text
job_id + artifact_id
        |
        v
ArtifactCatalog.open(job=当前 Job, artifact_id=...)
        |
        v
Catalog 验证 Artifact 归属、Blob 大小和 SHA-256
```

浏览器永远不能决定宿主机路径或对象存储 key。

### 4.3 为什么预览同时检查 media type 和扩展名

只检查媒体类型不够，因为错误或恶意 metadata 可能把 `report.html` 标成 `text/plain`。只检查扩展名也不够，因为 `report.txt` 可能被标成 `text/html`。

第一版采用保守策略：

```text
media type 在 allowlist
AND
suffix 在 allowlist
AND
内容是严格 UTF-8
AND
内容不含 NUL 或危险控制字符
```

不满足任何一项都返回 `415 ARTIFACT_PREVIEW_UNSUPPORTED`，用户仍可使用安全下载。

### 4.4 为什么下载强制使用二进制类型

下载的目标是“取走原始字节”，不是“让浏览器解释内容”。即使 Artifact 的声明类型是 `text/html`，下载响应也应是：

```text
Content-Type: application/octet-stream
Content-Disposition: attachment
X-Content-Type-Options: nosniff
Content-Security-Policy: sandbox; default-src 'none'
```

`descriptor.media_type` 仍保留在 Artifact 元数据和导出 manifest 中，但不作为浏览器下载响应的执行提示。

### 4.5 导出的时序

```text
列出当前 Job Artifact
        |
        v
冻结 descriptor 快照并检查数量/总大小
        |
        v
在 exports/.staging 创建随机 .part
        |
        v
逐个 catalog.open() + 身份核对 + 流式写 ZIP + 重新计算 hash
        |
        v
写 metadata/job.json 与 export_manifest.json
        |
        v
关闭 ZIP，检查最终压缩包大小，计算 ZIP SHA-256
        |
        v
原子 rename 为 .zip
        |
        v
创建 StreamingResponse
        |
        v
响应结束/断开 -> finally 删除临时 ZIP
```

关键点是先构建，后响应。若边生成 ZIP 边向客户端发送，第三个 Artifact 校验失败时，HTTP 状态已经是 `200`，客户端只会得到一个损坏文件，无法收到结构化错误。

运行中的 Job 也允许导出，但导出的只是“请求开始时已经发布的 Artifact 快照”，manifest 会记录当时的公开 Job 状态。若用户需要最终完整包，应等待 Job 进入终态后再导出；Delivery Service 不会为了导出而暂停 Worker。

---

## 五、涉及文件总览

> **本节类型：实施清单。以下文件需要修改或新增。**

### 5.1 新增文件

```text
app/artifact_delivery/__init__.py
app/artifact_delivery/errors.py
app/artifact_delivery/schemas.py
app/artifact_delivery/service.py
web/src/components/ArtifactPreviewPanel.tsx
tests/test_artifact_delivery_service.py
tests/test_artifact_delivery_api.py
web/tests/artifact-delivery.test.tsx
```

### 5.2 修改文件

```text
.gitignore
.env.example
app/config.py
app/interaction/schemas.py
app/api/errors.py
app/api/app.py
app/api/routes.py
web/src/api/types.ts
web/src/api/client.ts
web/src/components/RunContextPanel.tsx
web/src/styles/app.css
```

如果 Phase 33 的前端代码使 `RunContextPanel.tsx` 与本章示例不同，不要整文件覆盖；保留已有 Local Import 和 Decision 代码，只替换 Artifact tab 相关状态、加载和渲染部分。

---

## 六、增加配置和项目内 staging

> **本节类型：需要修改配置文件。**

### 6.1 修改 `.gitignore`

在文件末尾增加：

```gitignore
# Phase 34：临时导出包。响应结束后会删除，崩溃残留由 TTL 清理。
exports/

# 本章测试把 pytest basetemp 固定在项目内。
.pytest-tmp/
```

不要忽略所有 `*.zip`，否则可能误伤测试 fixture 或用户主动保存的样例。

### 6.2 修改 `.env.example`

在 Artifact 配置附近增加：

```dotenv
# Phase 34：安全文本预览最大读取 256 KiB。
ARTIFACT_PREVIEW_MAX_BYTES=262144

# 必须是项目控制的目录；不要指向 /tmp，也不要放入用户论文仓库。
JOB_EXPORT_ALLOWED_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot
JOB_EXPORT_STAGING_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/exports/.staging

# 防止一次请求打包过多对象或形成超大 ZIP。
JOB_EXPORT_MAX_ARTIFACTS=500
JOB_EXPORT_MAX_UNCOMPRESSED_BYTES=1073741824
JOB_EXPORT_MAX_ARCHIVE_BYTES=536870912

# API 异常退出后，下一次导出会清理超过 1 小时的残留文件。
JOB_EXPORT_STAGING_TTL_SECONDS=3600
```

### 6.3 修改 `app/config.py`

在现有 `artifact_stream_chunk_bytes` 下方增加以下字段：

```python
    artifact_stream_chunk_bytes: int = int(
        os.getenv(
            "ARTIFACT_STREAM_CHUNK_BYTES",
            str(1024 * 1024),
        )
    )

    # Phase 34：预览只读取有界文本，不允许大 Artifact 全量进内存。
    artifact_preview_max_bytes: int = int(
        os.getenv(
            "ARTIFACT_PREVIEW_MAX_BYTES",
            str(256 * 1024),
        )
    )

    # 导出 staging 位于项目目录内，不依赖系统 /tmp。
    job_export_allowed_root: Path = Path(
        os.getenv(
            "JOB_EXPORT_ALLOWED_ROOT",
            str(Path(__file__).resolve().parents[1]),
        )
    )

    job_export_staging_root: Path = Path(
        os.getenv(
            "JOB_EXPORT_STAGING_ROOT",
            "exports/.staging",
        )
    )

    job_export_max_artifacts: int = int(
        os.getenv(
            "JOB_EXPORT_MAX_ARTIFACTS",
            "500",
        )
    )

    job_export_max_uncompressed_bytes: int = int(
        os.getenv(
            "JOB_EXPORT_MAX_UNCOMPRESSED_BYTES",
            str(1024 * 1024 * 1024),
        )
    )

    job_export_max_archive_bytes: int = int(
        os.getenv(
            "JOB_EXPORT_MAX_ARCHIVE_BYTES",
            str(512 * 1024 * 1024),
        )
    )

    job_export_staging_ttl_seconds: int = int(
        os.getenv(
            "JOB_EXPORT_STAGING_TTL_SECONDS",
            "3600",
        )
    )
```

在配置校验区、现有 `ARTIFACT_STREAM_CHUNK_BYTES` 校验后增加：

```python
if settings.artifact_stream_chunk_bytes < 64 * 1024:
    raise ValueError(
        "ARTIFACT_STREAM_CHUNK_BYTES 不能小于 64 KiB"
    )

if not 1024 <= settings.artifact_preview_max_bytes <= 4 * 1024 * 1024:
    raise ValueError(
        "ARTIFACT_PREVIEW_MAX_BYTES 必须位于 1 KiB..4 MiB"
    )

if settings.job_export_max_artifacts < 1:
    raise ValueError(
        "JOB_EXPORT_MAX_ARTIFACTS 必须至少为 1"
    )

if settings.job_export_max_uncompressed_bytes < 1024:
    raise ValueError(
        "JOB_EXPORT_MAX_UNCOMPRESSED_BYTES 必须至少为 1 KiB"
    )

if settings.job_export_max_archive_bytes < 1024:
    raise ValueError(
        "JOB_EXPORT_MAX_ARCHIVE_BYTES 必须至少为 1 KiB"
    )

if settings.job_export_staging_ttl_seconds < 60:
    raise ValueError(
        "JOB_EXPORT_STAGING_TTL_SECONDS 不能小于 60 秒"
    )
```

这里没有在 import 时创建目录。目录创建和安全检查应由 Delivery Service 在真正使用时完成，避免单纯 import 模块就修改文件系统。

---

## 七、定义 Delivery 错误类型

> **本节类型：需要新增代码。**
>
> **新增文件：** `app/artifact_delivery/__init__.py`、`app/artifact_delivery/errors.py`

创建空的 `app/artifact_delivery/__init__.py`：

```python
"""Artifact 的预览、下载和导出交付层。"""
```

创建 `app/artifact_delivery/errors.py`：

```python
from __future__ import annotations


class ArtifactDeliveryError(RuntimeError):
    """Artifact 交付层错误基类。"""


class ArtifactPreviewUnsupported(ArtifactDeliveryError):
    """Artifact 可以下载，但不允许在浏览器内预览。"""


class ArtifactExportLimitExceeded(ArtifactDeliveryError):
    """导出数量、未压缩大小或压缩包大小超过配置上限。"""
```

不要把“不支持预览”映射成 404。Artifact 确实存在，只是服务器拒绝把它解释为网页内文本，因此 HTTP 语义应是 415。

导出快照漂移、hash 不一致和重复路径不再新建错误，而是复用 `ArtifactIntegrityError`，统一映射成 409。

---

## 八、定义 Preview、Manifest 和 PreparedExport schema

> **本节类型：需要新增代码。**
>
> **新增文件：** `app/artifact_delivery/schemas.py`

写入完整代码：

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArtifactDeliveryModel(BaseModel):
    """交付 API 的结构化对象都拒绝未知字段。"""

    model_config = ConfigDict(extra="forbid")


class ArtifactPreviewResponse(ArtifactDeliveryModel):
    artifact_id: str
    relative_path: str
    media_type: str
    sha256: str
    total_size_bytes: int = Field(ge=0)
    returned_bytes: int = Field(ge=0)
    truncated: bool
    encoding: str = "utf-8"
    content: str


class ExportArtifactEntry(ArtifactDeliveryModel):
    artifact_id: str
    run_id: str
    layer: str
    relative_path: str
    archive_path: str
    media_type: str
    sha256: str
    size_bytes: int = Field(ge=0)
    producer_node: str
    created_at: str


class JobExportManifest(ArtifactDeliveryModel):
    manifest_version: str = "phase34-v1"
    generated_at: str
    job_id: str
    run_id: str
    artifact_count: int = Field(ge=0)
    total_uncompressed_bytes: int = Field(ge=0)
    job: dict[str, Any]
    artifacts: list[ExportArtifactEntry]
    manifest_sha256: str


@dataclass(frozen=True)
class PreparedJobExport:
    """已经完成校验、可以开始响应的临时 ZIP。"""

    path: Path
    filename: str
    size_bytes: int
    sha256: str
    manifest: JobExportManifest
```

`PreparedJobExport.path` 只存在于 API 进程内部，不能出现在公开 JSON、Event 或 telemetry attribute 中。

---

## 九、实现 ArtifactDeliveryService

> **本节类型：需要新增核心代码。**
>
> **新增文件：** `app/artifact_delivery/service.py`

这是本阶段的核心。完整写入以下代码：

```python
from __future__ import annotations

import codecs
import hashlib
import json
import os
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from app.artifact_delivery.errors import (
    ArtifactExportLimitExceeded,
    ArtifactPreviewUnsupported,
)
from app.artifact_delivery.schemas import (
    ArtifactPreviewResponse,
    ExportArtifactEntry,
    JobExportManifest,
    PreparedJobExport,
)
from app.interaction.artifacts import ArtifactCatalog
from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.storage.errors import ArtifactIntegrityError
from app.storage.schemas import ArtifactDescriptor


# 预览需要媒体类型和扩展名同时命中。HTML/SVG 不在其中。
SAFE_PREVIEW_MEDIA_TYPES = {
    "application/json",
    "application/x-yaml",
    "text/csv",
    "text/markdown",
    "text/plain",
    "text/x-diff",
    "text/x-python",
    "text/yaml",
}

SAFE_PREVIEW_SUFFIXES = {
    ".csv",
    ".diff",
    ".json",
    ".jsonl",
    ".log",
    ".markdown",
    ".md",
    ".patch",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    """manifest hash 使用稳定 JSON 编码，不能依赖缩进或 key 顺序。"""

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def preview_supported(*, media_type: str, relative_path: str) -> bool:
    """公开给 API 与 Web 共用的确定性预览能力判断。"""

    normalized_media_type = media_type.split(";", 1)[0].strip().lower()
    suffix = PurePosixPath(relative_path).suffix.lower()
    return (
        normalized_media_type in SAFE_PREVIEW_MEDIA_TYPES
        and suffix in SAFE_PREVIEW_SUFFIXES
    )


def _archive_path(relative_path: str) -> str:
    """把 Catalog 相对路径变成安全 ZIP member 名称。"""

    if "\x00" in relative_path or "\\" in relative_path:
        raise ArtifactIntegrityError("Artifact 导出路径包含非法字符")

    parts = relative_path.split("/")
    if (
        not relative_path
        or relative_path.startswith("/")
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ArtifactIntegrityError("Artifact 导出路径不是安全相对路径")

    normalized = PurePosixPath(relative_path)
    if normalized.is_absolute():
        raise ArtifactIntegrityError("Artifact 导出路径不能是绝对路径")

    return str(PurePosixPath("artifacts") / normalized)


def _zip_info(name: str) -> zipfile.ZipInfo:
    """使用普通文件权限，避免把宿主机权限带入导出包。"""

    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def _same_snapshot(
    view: ArtifactView,
    descriptor: ArtifactDescriptor,
) -> bool:
    """list_views() 后到 open() 前不能发生身份漂移。"""

    return all(
        (
            descriptor.artifact_id == view.artifact_id,
            descriptor.run_id == view.run_id,
            descriptor.layer == view.layer,
            descriptor.relative_path == view.relative_path,
            descriptor.media_type == view.media_type,
            descriptor.sha256 == view.sha256,
            descriptor.size_bytes == view.size_bytes,
            descriptor.producer_node == view.producer_node,
            descriptor.created_at == view.created_at,
        )
    )


class ArtifactDeliveryService:
    def __init__(
        self,
        *,
        catalog: ArtifactCatalog,
        preview_max_bytes: int,
        stream_chunk_bytes: int,
        export_allowed_root: Path,
        export_staging_root: Path,
        export_max_artifacts: int,
        export_max_uncompressed_bytes: int,
        export_max_archive_bytes: int,
        export_staging_ttl_seconds: int,
    ) -> None:
        self.catalog = catalog
        self.preview_max_bytes = preview_max_bytes
        self.stream_chunk_bytes = stream_chunk_bytes
        self.export_allowed_root = export_allowed_root
        self.export_staging_root = export_staging_root
        self.export_max_artifacts = export_max_artifacts
        self.export_max_uncompressed_bytes = export_max_uncompressed_bytes
        self.export_max_archive_bytes = export_max_archive_bytes
        self.export_staging_ttl_seconds = export_staging_ttl_seconds

    def list_views(self, job: JobRecord) -> list[ArtifactView]:
        """只增加能力标记，不暴露 BlobStore 内部字段。"""

        return [
            item.model_copy(
                update={
                    "preview_supported": preview_supported(
                        media_type=item.media_type,
                        relative_path=item.relative_path,
                    )
                }
            )
            for item in self.catalog.list_views(job)
        ]

    def preview(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> ArtifactPreviewResponse:
        """读取最多 max + 1 字节，额外一字节只用于判断截断。"""

        opened = self.catalog.open(job=job, artifact_id=artifact_id)
        descriptor = opened.artifact.descriptor
        try:
            if not preview_supported(
                media_type=descriptor.media_type,
                relative_path=descriptor.relative_path,
            ):
                raise ArtifactPreviewUnsupported(
                    "该 Artifact 类型不支持网页内预览，请使用下载"
                )

            raw = opened.blob.body.read(self.preview_max_bytes + 1)
        finally:
            # 不论类型拒绝、解码失败还是正常返回，都关闭本地/S3 body。
            opened.blob.body.close()

        if descriptor.size_bytes <= self.preview_max_bytes:
            if (
                len(raw) != descriptor.size_bytes
                or hashlib.sha256(raw).hexdigest() != descriptor.sha256
            ):
                raise ArtifactIntegrityError(
                    "Artifact 预览时大小或 SHA-256 校验失败"
                )
        elif len(raw) != self.preview_max_bytes + 1:
            # 声明为大文件却提前 EOF，说明 descriptor/blob 已漂移。
            raise ArtifactIntegrityError(
                "Artifact 预览流早于声明大小结束"
            )

        truncated = descriptor.size_bytes > self.preview_max_bytes
        bounded = raw[: self.preview_max_bytes]

        if b"\x00" in bounded:
            raise ArtifactPreviewUnsupported(
                "Artifact 内容包含 NUL，不能作为文本预览"
            )

        # final=False 允许 decoder 暂存被字节上限截断的 UTF-8 尾部；
        # 中间位置的非法字节仍会严格报错。
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        try:
            content = decoder.decode(
                bounded,
                final=not truncated,
            )
        except UnicodeDecodeError as exc:
            raise ArtifactPreviewUnsupported(
                "Artifact 不是有效 UTF-8 文本"
            ) from exc

        buffered_tail, _decoder_state = decoder.getstate()
        decoded_bytes = len(bounded) - len(buffered_tail)

        # 允许换行、回车和制表符，拒绝其他 C0 控制字符。
        if any(ord(char) < 32 and char not in "\n\r\t" for char in content):
            raise ArtifactPreviewUnsupported(
                "Artifact 包含不允许的控制字符"
            )

        return ArtifactPreviewResponse(
            artifact_id=descriptor.artifact_id,
            relative_path=descriptor.relative_path,
            media_type=descriptor.media_type,
            sha256=descriptor.sha256,
            total_size_bytes=descriptor.size_bytes,
            returned_bytes=decoded_bytes,
            truncated=truncated,
            content=content,
        )

    def _prepare_staging(self) -> Path:
        """创建项目内 staging，并顺带清理崩溃遗留的小范围文件。"""

        allowed_root = self.export_allowed_root.expanduser().resolve()
        if not allowed_root.is_dir():
            raise ArtifactIntegrityError("导出 allowed root 不存在或不是目录")

        configured = self.export_staging_root.expanduser()
        if not configured.is_absolute():
            configured = allowed_root / configured

        # strict=False 会解析已经存在的父目录和软链接，但不要求叶子存在。
        resolved = configured.resolve(strict=False)
        if resolved == allowed_root or allowed_root not in resolved.parents:
            raise ArtifactIntegrityError("导出 staging root 越出允许目录")

        if configured.exists() and configured.is_symlink():
            raise ArtifactIntegrityError("导出 staging root 不能是软链接")

        configured.mkdir(parents=True, exist_ok=True, mode=0o700)
        # mkdir 与后续使用之间再次解析，避免配置指向意外位置。
        resolved = configured.resolve()
        if allowed_root not in resolved.parents:
            raise ArtifactIntegrityError("导出 staging root 越出允许目录")

        cutoff = time.time() - self.export_staging_ttl_seconds
        for candidate in resolved.iterdir():
            # 只处理当前目录直属、由本服务命名的临时文件。
            if not candidate.is_file() or candidate.suffix not in {".part", ".zip"}:
                continue
            try:
                if candidate.stat().st_mtime < cutoff:
                    candidate.unlink()
            except FileNotFoundError:
                pass

        return resolved

    def _snapshot_entries(
        self,
        job: JobRecord,
    ) -> tuple[list[ArtifactView], list[ExportArtifactEntry], int]:
        views = self.catalog.list_views(job)
        if len(views) > self.export_max_artifacts:
            raise ArtifactExportLimitExceeded(
                "当前 Job 的 Artifact 数量超过导出上限"
            )

        total = sum(item.size_bytes for item in views)
        if total > self.export_max_uncompressed_bytes:
            raise ArtifactExportLimitExceeded(
                "当前 Job 的 Artifact 未压缩总大小超过导出上限"
            )

        entries: list[ExportArtifactEntry] = []
        archive_paths: set[str] = set()
        archive_paths_casefold: set[str] = set()
        artifact_ids: set[str] = set()
        for view in sorted(views, key=lambda item: (item.layer, item.relative_path)):
            if view.run_id != job.run_id:
                raise ArtifactIntegrityError("Artifact run_id 与当前 Job 不一致")
            if view.artifact_id in artifact_ids:
                raise ArtifactIntegrityError("导出中出现重复 artifact_id")
            artifact_ids.add(view.artifact_id)
            archive_path = _archive_path(view.relative_path)
            folded_path = archive_path.casefold()
            if (
                archive_path in archive_paths
                or folded_path in archive_paths_casefold
            ):
                raise ArtifactIntegrityError("导出中出现重复 Artifact 路径")
            archive_paths.add(archive_path)
            archive_paths_casefold.add(folded_path)
            entries.append(
                ExportArtifactEntry(
                    artifact_id=view.artifact_id,
                    run_id=view.run_id,
                    layer=view.layer,
                    relative_path=view.relative_path,
                    archive_path=archive_path,
                    media_type=view.media_type,
                    sha256=view.sha256,
                    size_bytes=view.size_bytes,
                    producer_node=view.producer_node,
                    created_at=view.created_at,
                )
            )

        return views, entries, total

    def _write_artifact(
        self,
        *,
        archive: zipfile.ZipFile,
        job: JobRecord,
        view: ArtifactView,
        entry: ExportArtifactEntry,
    ) -> None:
        opened = self.catalog.open(job=job, artifact_id=view.artifact_id)
        descriptor = opened.artifact.descriptor
        digest = hashlib.sha256()
        written = 0

        try:
            if not _same_snapshot(view, descriptor):
                raise ArtifactIntegrityError(
                    "Artifact 在导出快照建立后发生变化"
                )

            with archive.open(_zip_info(entry.archive_path), mode="w") as target:
                while True:
                    chunk = opened.blob.body.read(self.stream_chunk_bytes)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > view.size_bytes:
                        raise ArtifactIntegrityError(
                            "Artifact 实际大小超过导出快照"
                        )
                    digest.update(chunk)
                    target.write(chunk)
        finally:
            opened.blob.body.close()

        if written != view.size_bytes or digest.hexdigest() != view.sha256:
            raise ArtifactIntegrityError(
                "Artifact 导出时大小或 SHA-256 校验失败"
            )

    def build_export(
        self,
        *,
        job: JobRecord,
        public_job: dict[str, Any],
    ) -> PreparedJobExport:
        """完整构建成功后才返回 PreparedJobExport。"""

        views, entries, total = self._snapshot_entries(job)
        # 用 artifact_id 关联排序后的 manifest entry，避免依赖两个列表顺序。
        entries_by_id = {item.artifact_id: item for item in entries}

        staging_root = self._prepare_staging()
        token = uuid4().hex
        part_path = staging_root / f"{token}.part"
        final_path = staging_root / f"{token}.zip"

        generated_at = utc_now()
        manifest_without_hash: dict[str, Any] = {
            "manifest_version": "phase34-v1",
            "generated_at": generated_at,
            "job_id": job.job_id,
            "run_id": job.run_id,
            "artifact_count": len(entries),
            "total_uncompressed_bytes": total,
            "job": public_job,
            "artifacts": [item.model_dump(mode="json") for item in entries],
        }
        manifest_hash = hashlib.sha256(
            canonical_json_bytes(manifest_without_hash)
        ).hexdigest()
        manifest = JobExportManifest(
            **manifest_without_hash,
            manifest_sha256=manifest_hash,
        )

        try:
            with zipfile.ZipFile(
                part_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
                allowZip64=True,
            ) as archive:
                # 先写公开 Job 投影；禁止直接 dump 内部 JobRecord。
                archive.writestr(
                    _zip_info("metadata/job.json"),
                    json.dumps(
                        public_job,
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    ).encode("utf-8"),
                )

                for view in sorted(
                    views,
                    key=lambda item: (item.layer, item.relative_path),
                ):
                    self._write_artifact(
                        archive=archive,
                        job=job,
                        view=view,
                        entry=entries_by_id[view.artifact_id],
                    )

                archive.writestr(
                    _zip_info("metadata/export_manifest.json"),
                    json.dumps(
                        manifest.model_dump(mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                        indent=2,
                    ).encode("utf-8"),
                )

            archive_size = part_path.stat().st_size
            if archive_size > self.export_max_archive_bytes:
                raise ArtifactExportLimitExceeded(
                    "生成的 ZIP 大小超过导出上限"
                )

            archive_digest = hashlib.sha256()
            with part_path.open("rb") as stream:
                while True:
                    chunk = stream.read(self.stream_chunk_bytes)
                    if not chunk:
                        break
                    archive_digest.update(chunk)

            os.replace(part_path, final_path)

            safe_job = _SAFE_FILENAME.sub("_", job.job_id).strip("._") or "job"
            safe_run = _SAFE_FILENAME.sub("_", job.run_id).strip("._") or "run"
            filename = f"paper-copilot-{safe_job[:60]}-{safe_run[:60]}.zip"

            return PreparedJobExport(
                path=final_path,
                filename=filename,
                size_bytes=archive_size,
                sha256=archive_digest.hexdigest(),
                manifest=manifest,
            )
        except Exception:
            # part 或 rename 后的 final 都可能存在；失败时不能留下垃圾。
            part_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise
```

### 9.1 为什么 `public_job` 由 API 层传入

内部 `JobRecord` 包含：

```text
run_dir
claim_token
worker_session_id
workspace_assignment_token
内部 Resource object_key
```

这些字段不能直接写进用户导出包。API 已经有 `InteractionService.get_job()` 的公开投影，因此 Delivery Service 只接受它的 `model_dump(mode="json")`。

### 9.2 为什么再次计算每个 Artifact 的 SHA-256

`PublishedArtifactCatalog.open()` 已经验证 Blob stat，但导出时再次边读边 hash 可以防止：

- 自定义或测试 Catalog 没有完整校验；
- 后端在 `stat()` 与流式读取之间发生变化；
- 未来新增 BlobStore 时遗漏读取阶段校验。

校验属于交付边界，不能只相信上游。

### 9.3 为什么 ZIP 中只使用 POSIX 路径

ZIP member 统一使用 `/`。拒绝绝对路径、`..`、空 path segment、反斜杠和 NUL，可以防止解压时的 Zip Slip，也避免 Windows/Linux 对同一路径产生不同解释。

---

## 十、扩展公开 Artifact schema

> **本节类型：需要修改代码。**
>
> **修改文件：** `app/interaction/schemas.py`

找到现有 `ArtifactView`，在 `integrity_status` 前增加 `preview_supported`。修改后的完整类应为：

```python
class ArtifactView(InteractionModel):
    artifact_id: str
    run_id: str
    layer: str
    relative_path: str
    media_type: str
    sha256: str
    size_bytes: int
    producer_node: str
    created_at: str

    # 这是服务端能力声明，前端不自行猜测安全类型。
    preview_supported: bool = False

    integrity_status: Literal[
        "unchecked",
        "current",
    ] = "unchecked"
```

默认值必须是 `False`，这样旧测试、旧 Catalog 以及数据库中已存在的对象不需要迁移。只有经过 `ArtifactDeliveryService.list_views()` 的 API 列表才会得到确定性的能力标记。

---

## 十一、把 Delivery 错误映射成稳定 HTTP 语义

> **本节类型：需要修改代码。**
>
> **修改文件：** `app/api/errors.py`

在 import 区增加：

```python
from app.artifact_delivery.errors import (
    ArtifactExportLimitExceeded,
    ArtifactPreviewUnsupported,
)
```

在 `install_error_handlers()` 末尾、仍位于函数体内部增加：

```python
    @app.exception_handler(
        ArtifactPreviewUnsupported
    )
    async def handle_preview_unsupported(
        request: Request,
        exc: ArtifactPreviewUnsupported,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=415,
            code="ARTIFACT_PREVIEW_UNSUPPORTED",
            message=str(exc),
        )

    @app.exception_handler(
        ArtifactExportLimitExceeded
    )
    async def handle_export_limit(
        request: Request,
        exc: ArtifactExportLimitExceeded,
    ) -> JSONResponse:
        return _response(
            request,
            status_code=413,
            code="ARTIFACT_EXPORT_LIMIT_EXCEEDED",
            message=str(exc),
        )
```

最终错误语义如下：

| 情况 | HTTP | code |
|---|---:|---|
| Job 不存在 | 404 | `JOB_NOT_FOUND` |
| Artifact 不存在或不属于 Job | 404 | `ARTIFACT_NOT_FOUND` |
| Artifact 类型不允许预览 | 415 | `ARTIFACT_PREVIEW_UNSUPPORTED` |
| Artifact 快照、路径、大小或 hash 漂移 | 409 | `ARTIFACT_INTEGRITY_ERROR` |
| 导出数量或大小超限 | 413 | `ARTIFACT_EXPORT_LIMIT_EXCEEDED` |
| BlobStore 暂时不可用 | 503 | `ARTIFACT_BACKEND_UNAVAILABLE` |

不要在错误消息里加入 `object_key`、staging 绝对路径或异常的完整 `repr()`。

---

## 十二、在 App Factory 中装配 Delivery Service

> **本节类型：需要修改代码。**
>
> **修改文件：** `app/api/app.py`

### 12.1 增加 import

在顶部 import 区增加：

```python
from app.artifact_delivery.service import (
    ArtifactDeliveryService,
)
```

### 12.2 扩展 `create_api_app()` 参数

找到函数签名，在 `artifact_catalog` 后增加可注入 service：

```python
def create_api_app(
    *,
    job_service: JobService | None = None,
    artifact_catalog: (
        ArtifactCatalog | None
    ) = None,
    artifact_delivery_service: (
        ArtifactDeliveryService | None
    ) = None,
    api_token: str | None = None,
    service_host: Any | None = None,
    chat_service: ChatService | None = None,
) -> FastAPI:
```

测试可以注入更小的限制和临时 staging，而生产环境使用 Settings。

### 12.3 在 `selected_catalog` 后创建 service

找到：

```python
    selected_catalog = (
        artifact_catalog
        if artifact_catalog is not None
        else storage.catalog
    )

    app.state.artifact_catalog = (
        selected_catalog
    )
```

在两者之间插入：

```python
    if selected_catalog is None:
        raise RuntimeError(
            "Artifact delivery 需要可用的 ArtifactCatalog"
        )

    selected_delivery_service = (
        artifact_delivery_service
        if artifact_delivery_service is not None
        else ArtifactDeliveryService(
            catalog=selected_catalog,
            preview_max_bytes=(
                settings.artifact_preview_max_bytes
            ),
            stream_chunk_bytes=(
                settings.artifact_stream_chunk_bytes
            ),
            export_allowed_root=(
                settings.job_export_allowed_root
            ),
            export_staging_root=(
                settings.job_export_staging_root
            ),
            export_max_artifacts=(
                settings.job_export_max_artifacts
            ),
            export_max_uncompressed_bytes=(
                settings.job_export_max_uncompressed_bytes
            ),
            export_max_archive_bytes=(
                settings.job_export_max_archive_bytes
            ),
            export_staging_ttl_seconds=(
                settings.job_export_staging_ttl_seconds
            ),
        )
    )

    app.state.artifact_delivery_service = (
        selected_delivery_service
    )
```

保留原来的：

```python
    app.state.artifact_catalog = selected_catalog
```

两者职责不同：Catalog 负责“这个 Job 是否拥有该 Artifact，以及如何打开可信 Blob”；Delivery Service 负责“允许如何把可信 Blob 交给用户”。

### 12.4 不要让全局 CSP 覆盖下载路由的更严格 CSP

同一文件的 `observability_middleware()` 当前会为 Web 响应统一写入 CSP。如果它无条件赋值，会覆盖下载路由的：

```text
sandbox; default-src 'none'
```

找到：

```python
                    if settings.web_ui_required:
                        response.headers[
                            "Content-Security-Policy"
                        ] = (
                            # 现有 CSP 内容……
                        )
```

把条件改为：

```python
                    # 路由可以提供更严格的响应专用 CSP；全局中间件
                    # 只在响应尚未设置时补充 Web UI 默认策略。
                    if (
                        settings.web_ui_required
                        and "Content-Security-Policy"
                        not in response.headers
                    ):
                        response.headers[
                            "Content-Security-Policy"
                        ] = (
                            "default-src 'self'; "
                            "script-src 'self'; "
                            "style-src 'self'; "
                            "font-src 'self'; "
                            "img-src 'self' data:; "
                            "connect-src 'self'; "
                            "frame-ancestors 'none'"
                        )
```

这是本章容易漏掉的接线点。路由返回对象上的 header 会在 `call_next()` 之后进入中间件；如果中间件直接覆盖，路由代码看起来正确，最终线上响应却不是预期策略。

---

## 十三、增加 Preview、Download 和 Export API

> **本节类型：需要修改核心 API 代码。**
>
> **修改文件：** `app/api/routes.py`

### 13.1 修改 import

把 `collections.abc` import 改为：

```python
from collections.abc import Iterator
```

在现有 import 区增加：

```python
import re

from app.artifact_delivery.schemas import (
    ArtifactPreviewResponse,
)
from app.artifact_delivery.service import (
    ArtifactDeliveryService,
)
```

现有 `Path`、`quote`、`StreamingResponse` 和 `settings` import 继续保留。

### 13.2 增加依赖读取函数

放在现有 `artifact_catalog()` 下方：

```python
def artifact_delivery_service(
    request: Request,
) -> ArtifactDeliveryService:
    return request.app.state.artifact_delivery_service
```

放在 `ArtifactCatalogDependency` 下方：

```python
ArtifactDeliveryDependency = Annotated[
    ArtifactDeliveryService,
    Depends(artifact_delivery_service),
]
```

### 13.3 增加通用附件名和临时文件迭代器

放在现有 `_iter_blob()` 后方：

```python
_UNSAFE_ATTACHMENT_CHARS = re.compile(
    r"[^A-Za-z0-9._-]+"
)


def _attachment_disposition(filename: str) -> str:
    """同时提供保守 ASCII fallback 和 RFC 5987 UTF-8 文件名。"""

    basename = Path(filename).name or "download.bin"
    fallback = _UNSAFE_ATTACHMENT_CHARS.sub(
        "_",
        basename,
    ).strip("._")[:120]
    if not fallback:
        fallback = "download.bin"

    return (
        f'attachment; filename="{fallback}"; '
        "filename*=UTF-8''"
        f"{quote(basename, safe='')}"
    )


def _iter_file_and_delete(
    path: Path,
    *,
    chunk_bytes: int,
) -> Iterator[bytes]:
    """导出响应完成或断开时都删除临时 ZIP。"""

    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(chunk_bytes)
                if not chunk:
                    break
                yield chunk
    finally:
        path.unlink(missing_ok=True)
```

### 13.4 替换 Artifact 列表路由

把当前 `list_artifacts()` 中的 Catalog 依赖改为 Delivery Service：

```python
@router.get(
    "/jobs/{job_id}/artifacts",
    response_model=ArtifactListResponse,
)
def list_artifacts(
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
    delivery: ArtifactDeliveryDependency,
) -> ArtifactListResponse:
    internal_job = service.job_service.get(job_id)
    items = delivery.list_views(internal_job)
    return ArtifactListResponse(
        items=items,
        count=len(items),
    )
```

### 13.5 增加安全预览路由

紧接 Artifact 列表路由增加：

```python
@router.get(
    "/jobs/{job_id}/artifacts/"
    "{artifact_id}/preview",
    response_model=ArtifactPreviewResponse,
)
def preview_artifact(
    job_id: str,
    artifact_id: str,
    _actor: Actor,
    service: InteractionDependency,
    delivery: ArtifactDeliveryDependency,
) -> ArtifactPreviewResponse:
    internal_job = service.job_service.get(job_id)
    return delivery.preview(
        job=internal_job,
        artifact_id=artifact_id,
    )
```

### 13.6 替换下载路由并保留兼容地址

删除旧的单个 `@router.get(.../content)` 和 `download_artifact()`，替换为：

```python
@router.get(
    "/jobs/{job_id}/artifacts/"
    "{artifact_id}/content",
    include_in_schema=False,
)
@router.get(
    "/jobs/{job_id}/artifacts/"
    "{artifact_id}/download"
)
def download_artifact(
    job_id: str,
    artifact_id: str,
    _actor: Actor,
    service: InteractionDependency,
    catalog: ArtifactCatalogDependency,
) -> StreamingResponse:
    internal_job = service.job_service.get(job_id)
    opened = catalog.open(
        job=internal_job,
        artifact_id=artifact_id,
    )
    descriptor = opened.artifact.descriptor
    filename = Path(descriptor.relative_path).name

    return StreamingResponse(
        _iter_blob(
            opened.blob.body,
            chunk_bytes=(
                settings.artifact_stream_chunk_bytes
            ),
        ),
        # 下载只交付原始字节，不让浏览器按 Artifact 类型解释。
        media_type="application/octet-stream",
        headers={
            "Content-Length": str(descriptor.size_bytes),
            "Content-Disposition": _attachment_disposition(filename),
            "ETag": f'"sha256:{descriptor.sha256}"',
            "X-Artifact-SHA256": descriptor.sha256,
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": (
                "sandbox; default-src 'none'"
            ),
        },
    )
```

`include_in_schema=False` 只隐藏旧别名，不移除兼容行为。OpenAPI 只推荐 `/download`。

### 13.7 增加单 Job 导出路由

放在下载路由后方：

```python
@router.get("/jobs/{job_id}/export")
def export_job(
    job_id: str,
    _actor: Actor,
    service: InteractionDependency,
    delivery: ArtifactDeliveryDependency,
) -> StreamingResponse:
    internal_job = service.job_service.get(job_id)
    public_job = service.get_job(job_id)

    # build_export 在返回前已经关闭 ZIP 并完成全部校验。
    prepared = delivery.build_export(
        job=internal_job,
        public_job=public_job.model_dump(mode="json"),
    )

    try:
        return StreamingResponse(
            _iter_file_and_delete(
                prepared.path,
                chunk_bytes=(
                    settings.artifact_stream_chunk_bytes
                ),
            ),
            media_type="application/zip",
            headers={
                "Content-Length": str(prepared.size_bytes),
                "Content-Disposition": (
                    _attachment_disposition(prepared.filename)
                ),
                "ETag": f'"sha256:{prepared.sha256}"',
                "X-Export-SHA256": prepared.sha256,
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception:
        # 若响应对象构造本身失败，generator 尚未启动，需在这里清理。
        prepared.path.unlink(missing_ok=True)
        raise
```

### 13.8 路由层不能做的事

不要在路由中直接：

```python
# 错误：绕过 Catalog 读取 run_dir。
Path(internal_job.run_dir, relative_path).open("rb")

# 错误：把用户路径直接作为 ZIP member。
archive.write(user_path)

# 错误：先创建 StreamingResponse，再在 generator 内校验快照。
return StreamingResponse(build_zip_while_sending())
```

路由只负责鉴权、取得 Job、调用领域 service 和构造 HTTP 响应。

---

## 十四、前端 API 类型和客户端

> **本节类型：需要修改前端代码。**
>
> **修改文件：** `web/src/api/types.ts`、`web/src/api/client.ts`

### 14.1 修改 `web/src/api/types.ts`

把 `ArtifactView` 替换为：

```typescript
export type ArtifactView = {
  artifact_id: string;
  run_id: string;
  layer: string;
  relative_path: string;
  media_type: string;
  sha256: string;
  size_bytes: number;
  producer_node: string;
  created_at: string;
  preview_supported: boolean;
  integrity_status: "unchecked" | "current";
};

export type ArtifactPreview = {
  artifact_id: string;
  relative_path: string;
  media_type: string;
  sha256: string;
  total_size_bytes: number;
  returned_bytes: number;
  truncated: boolean;
  encoding: "utf-8";
  content: string;
};
```

### 14.2 修改 `web/src/api/client.ts`

在 type import 中增加 `ArtifactPreview`：

```typescript
import type {
  AllowedOperation,
  ArtifactPreview,
  ArtifactView,
  // 保留其余已有类型……
} from "./types";
```

在 `export const api = { ... }` 的 `artifacts()` 后增加：

```typescript
  artifactPreview(jobId: string, artifactId: string) {
    return request<ArtifactPreview>(
      `/v1/jobs/${encodeURIComponent(jobId)}`
      + `/artifacts/${encodeURIComponent(artifactId)}/preview`,
    );
  },

  artifactDownloadUrl(jobId: string, artifactId: string) {
    return (
      `/v1/jobs/${encodeURIComponent(jobId)}`
      + `/artifacts/${encodeURIComponent(artifactId)}/download`
    );
  },

  jobExportUrl(jobId: string) {
    return `/v1/jobs/${encodeURIComponent(jobId)}/export`;
  },
```

下载和导出不要调用现有 `request<T>()`，因为该函数固定按 JSON 解析响应。返回 URL 后交给普通 `<a>`，浏览器会按 `Content-Disposition` 保存流，不会把整个 ZIP 放入 JavaScript 内存。

---

## 十五、新增 ArtifactPreviewPanel

> **本节类型：需要新增前端代码。**
>
> **新增文件：** `web/src/components/ArtifactPreviewPanel.tsx`

完整写入：

```tsx
import type { ArtifactPreview } from "../api/types";

type Props = {
  preview: ArtifactPreview;
  onClose: () => void;
};

export function ArtifactPreviewPanel({ preview, onClose }: Props) {
  return (
    <section className="artifact-preview" aria-label="Artifact preview">
      <header>
        <div>
          <strong>{preview.relative_path}</strong>
          <small>
            {preview.returned_bytes} / {preview.total_size_bytes} bytes
            {preview.truncated ? " · truncated" : ""}
          </small>
        </div>
        <button type="button" onClick={onClose}>Close</button>
      </header>

      {/* React 会转义字符串；不要改成 dangerouslySetInnerHTML。 */}
      <pre>{preview.content}</pre>
    </section>
  );
}
```

这里故意不引入 Markdown renderer。即使内容包含：

```html
<script>alert("xss")</script>
```

React 也只会把它显示成文本。以后如果确实需要 Markdown 富文本，必须单独增加 sanitizer、链接协议 allowlist 和安全回归测试，不能直接使用 `dangerouslySetInnerHTML`。

---

## 十六、接入 RunContextPanel

> **本节类型：需要修改前端代码。**
>
> **修改文件：** `web/src/components/RunContextPanel.tsx`

为了避免只给零散片段，下面给出当前文件的完整参考版本。若你的文件已经包含 Phase 33 新增状态，请合并 Artifact 部分，不要覆盖其他功能：

```tsx
import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type {
  ArtifactPreview,
  ArtifactView,
  JobStatus,
  JobView,
} from "../api/types";
import { ArtifactPreviewPanel } from "./ArtifactPreviewPanel";
import { StatusBadge } from "./StatusBadge";

type Tab = "overview" | "artifacts" | "logs";

const ACTIVE_STATUSES = new Set<JobStatus>([
  "queued",
  "running",
  "waiting_for_input",
  "cancelling",
]);

type Props = {
  job: JobView | null;
  onMutation: (action: () => Promise<unknown>) => Promise<void>;
};

export function RunContextPanel({ job, onMutation }: Props) {
  const [tab, setTab] = useState<Tab>("overview");
  const [artifacts, setArtifacts] = useState<ArtifactView[]>([]);
  const [preview, setPreview] = useState<ArtifactPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [log, setLog] = useState("");
  const [error, setError] = useState<string | null>(null);
  const currentJobId = useRef(job?.job_id);

  // 切换 Job 时不能继续显示上一个 Job 的预览或错误。
  useEffect(() => {
    currentJobId.current = job?.job_id;
    setArtifacts([]);
    setPreview(null);
    setPreviewLoading(false);
    setLog("");
    setError(null);
  }, [job?.job_id]);

  useEffect(() => {
    if (!job || tab !== "artifacts") return;
    let disposed = false;
    setError(null);
    void api.artifacts(job.job_id)
      .then((items) => {
        if (!disposed) setArtifacts(items);
      })
      .catch((caught) => {
        if (!disposed) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Artifact 加载失败",
          );
        }
      });
    return () => {
      disposed = true;
    };
  }, [job?.job_id, tab]);

  useEffect(() => {
    if (!job || tab !== "logs") return;
    let disposed = false;
    async function refreshLog() {
      try {
        const result = await api.log(job!.job_id);
        if (!disposed) setLog(result.content);
      } catch (caught) {
        if (!disposed) {
          setError(
            caught instanceof Error
              ? caught.message
              : "日志加载失败",
          );
        }
      }
    }

    void refreshLog();
    const timer = ACTIVE_STATUSES.has(job.status)
      ? window.setInterval(() => void refreshLog(), 2000)
      : null;
    return () => {
      disposed = true;
      if (timer !== null) window.clearInterval(timer);
    };
  }, [job?.job_id, job?.status, tab]);

  async function openPreview(artifact: ArtifactView) {
    if (!job) return;
    const requestedJobId = job.job_id;
    setPreviewLoading(true);
    setError(null);
    try {
      const result = await api.artifactPreview(
        requestedJobId,
        artifact.artifact_id,
      );
      if (currentJobId.current === requestedJobId) {
        setPreview(result);
      }
    } catch (caught) {
      if (currentJobId.current === requestedJobId) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Artifact 预览失败",
        );
      }
    } finally {
      if (currentJobId.current === requestedJobId) {
        setPreviewLoading(false);
      }
    }
  }

  if (!job) {
    return (
      <aside className="run-context">
        <p>Select a session.</p>
      </aside>
    );
  }

  const canCancel = job.allowed_operations.some(
    (item) => item.kind === "cancel",
  );
  const operatorOperation = job.allowed_operations.find(
    (item) => item.kind === "operator_reconciliation_required",
  );

  return (
    <aside className="run-context">
      <header>
        <p className="eyebrow">Run context</p>
        <StatusBadge status={job.status} />
      </header>
      <nav className="context-tabs" aria-label="Run context">
        {(["overview", "artifacts", "logs"] as Tab[]).map((name) => (
          <button
            key={name}
            aria-pressed={tab === name}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </nav>

      {error && (
        <p className="inline-error" role="alert">{error}</p>
      )}

      {tab === "overview" && (
        <dl>
          <dt>Paper</dt><dd>{job.input.paper_name}</dd>
          <dt>Repository</dt><dd>{job.input.repo_name}</dd>
          <dt>Profile</dt><dd>{job.input.execution_profile_id}</dd>
          <dt>Attempt</dt><dd>{job.attempt_count} / {job.max_attempts}</dd>
        </dl>
      )}

      {tab === "artifacts" && (
        <section className="artifact-section">
          <div className="artifact-toolbar">
            <strong>{artifacts.length} artifacts</strong>
            <a
              className="artifact-export-link"
              href={api.jobExportUrl(job.job_id)}
            >
              Export job (.zip)
            </a>
          </div>

          {preview && (
            <ArtifactPreviewPanel
              preview={preview}
              onClose={() => setPreview(null)}
            />
          )}

          {artifacts.length === 0 ? (
            <p>No artifacts published yet.</p>
          ) : (
            <ul className="artifact-list">
              {artifacts.map((artifact) => (
                <li key={artifact.artifact_id}>
                  <strong>{artifact.relative_path}</strong>
                  <small>
                    {artifact.media_type} / {artifact.size_bytes} bytes
                  </small>
                  <div className="artifact-actions">
                    {artifact.preview_supported && (
                      <button
                        type="button"
                        disabled={previewLoading}
                        onClick={() => void openPreview(artifact)}
                      >
                        Preview
                      </button>
                    )}
                    <a
                      href={api.artifactDownloadUrl(
                        job.job_id,
                        artifact.artifact_id,
                      )}
                    >
                      Download
                    </a>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === "logs" && (
        <pre className="log-tail">{log || "No log output yet."}</pre>
      )}

      {operatorOperation && (
        <p className="operator-note">{operatorOperation.detail}</p>
      )}
      {canCancel && (
        <button
          className="danger-action"
          onClick={() => void onMutation(() => api.cancel(job))}
        >
          Cancel session
        </button>
      )}
    </aside>
  );
}
```

注意：如果 API token 不是通过同源 Cookie，而是只保存在 JavaScript 并通过 `Authorization` header 发送，那么普通 `<a>` 不会带这个 header。当前项目默认同源、本机单用户部署可以使用 `<a>`；如果你启用了纯 Bearer 模式，需要把下载改为一次性 download token 或同源 HttpOnly Cookie，不能把长期 token 拼到 URL 查询参数中。

---

## 十七、增加轻量样式

> **本节类型：需要修改前端代码。**
>
> **修改文件：** `web/src/styles/app.css`

在 `.log-tail` 规则附近增加：

```css
.artifact-section {
  display: grid;
  gap: 0.8rem;
}

.artifact-toolbar,
.artifact-preview > header,
.artifact-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.65rem;
}

.artifact-export-link,
.artifact-actions a,
.artifact-actions button,
.artifact-preview button {
  border: 1px solid var(--line);
  border-radius: 0.65rem;
  padding: 0.45rem 0.6rem;
  color: var(--signal-dark);
  background: var(--paper-raised);
  text-decoration: none;
  cursor: pointer;
}

.artifact-list {
  display: grid;
  gap: 0.65rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.artifact-list li {
  display: grid;
  gap: 0.4rem;
  border: 1px solid var(--line);
  border-radius: 0.8rem;
  padding: 0.7rem;
  overflow-wrap: anywhere;
  background: rgb(255 253 247 / 64%);
}

.artifact-list small,
.artifact-preview small {
  display: block;
  color: var(--ink-muted);
}

.artifact-preview {
  border: 1px solid var(--line);
  border-left: 3px solid var(--signal);
  border-radius: 0.8rem;
  padding: 0.7rem;
  background: var(--paper-raised);
}

.artifact-preview pre {
  max-height: 24rem;
  overflow: auto;
  margin: 0.75rem 0 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.76rem;
}
```

这个阶段不需要复杂弹窗、语法高亮或树形文件浏览器。先保证后端交付协议和安全性完整。

---

## 十八、为 Delivery Service 增加领域测试

> **本节类型：需要新增测试代码。**
>
> **新增文件：** `tests/test_artifact_delivery_service.py`

下面的测试使用内存 Blob；运行命令会通过 `--basetemp` 把 pytest 隔离目录固定在项目内，不依赖真实论文或 S3：

```python
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from app.artifact_delivery.errors import (
    ArtifactExportLimitExceeded,
    ArtifactPreviewUnsupported,
)
from app.artifact_delivery.service import (
    ArtifactDeliveryService,
    canonical_json_bytes,
)
from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.storage.errors import ArtifactIntegrityError
from app.storage.ports import OpenedArtifact, OpenedBlob
from app.storage.schemas import (
    ArtifactDescriptor,
    BlobStat,
    PublishedArtifact,
)


class TrackingBytesIO(io.BytesIO):
    was_closed = False

    def close(self) -> None:
        self.was_closed = True
        super().close()


def make_view(
    artifact_id: str,
    relative_path: str,
    media_type: str,
    content: bytes,
) -> ArtifactView:
    return ArtifactView(
        artifact_id=artifact_id,
        run_id="run-1",
        layer=relative_path.split("/", 1)[0],
        relative_path=relative_path,
        media_type=media_type,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        producer_node="test",
        created_at="2026-08-06T00:00:00+00:00",
    )


class FakeCatalog:
    def __init__(self, items: list[tuple[ArtifactView, bytes]]) -> None:
        self.items = {
            view.artifact_id: (view, content)
            for view, content in items
        }
        self.last_body: TrackingBytesIO | None = None

    def list_views(self, _job: JobRecord) -> list[ArtifactView]:
        return [view for view, _content in self.items.values()]

    def open(
        self,
        *,
        job: JobRecord,
        artifact_id: str,
    ) -> OpenedArtifact:
        view, content = self.items[artifact_id]
        descriptor = ArtifactDescriptor(
            artifact_id=view.artifact_id,
            run_id=view.run_id,
            layer=view.layer,
            relative_path=view.relative_path,
            media_type=view.media_type,
            sha256=view.sha256,
            size_bytes=view.size_bytes,
            producer_node=view.producer_node,
            created_at=view.created_at,
        )
        body = TrackingBytesIO(content)
        self.last_body = body
        return OpenedArtifact(
            artifact=PublishedArtifact(
                job_id=job.job_id,
                descriptor=descriptor,
                backend="memory",
                object_key=f"objects/{artifact_id}",
                revision=1,
                published_at=view.created_at,
            ),
            blob=OpenedBlob(
                stat=BlobStat(
                    backend="memory",
                    object_key=f"objects/{artifact_id}",
                    size_bytes=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                ),
                body=body,
            ),
        )


def fake_job() -> JobRecord:
    # Service 测试只需要公开身份；真实 JobRecord 构造由 API 测试覆盖。
    return cast(
        JobRecord,
        SimpleNamespace(job_id="job-1", run_id="run-1"),
    )


def make_service(
    tmp_path: Path,
    catalog: FakeCatalog,
    *,
    preview_max_bytes: int = 8,
    max_artifacts: int = 20,
    max_uncompressed: int = 1024 * 1024,
) -> ArtifactDeliveryService:
    return ArtifactDeliveryService(
        catalog=catalog,
        preview_max_bytes=preview_max_bytes,
        stream_chunk_bytes=4,
        export_allowed_root=tmp_path,
        export_staging_root=tmp_path / "exports/.staging",
        export_max_artifacts=max_artifacts,
        export_max_uncompressed_bytes=max_uncompressed,
        export_max_archive_bytes=1024 * 1024,
        export_staging_ttl_seconds=3600,
    )


def test_preview_is_bounded_utf8_and_closes_body(tmp_path: Path) -> None:
    content = "你好，artifact preview".encode("utf-8")
    view = make_view(
        "a1",
        "reports/final.md",
        "text/markdown",
        content,
    )
    catalog = FakeCatalog([(view, content)])

    result = make_service(
        tmp_path,
        catalog,
        preview_max_bytes=8,
    ).preview(job=fake_job(), artifact_id="a1")

    assert result.truncated is True
    # 第 7～9 字节是全角逗号；上限 8 落在字符中间，安全退回 6 字节。
    assert result.returned_bytes == 6
    assert result.content == "你好"
    assert catalog.last_body is not None
    assert catalog.last_body.was_closed is True


@pytest.mark.parametrize(
    ("path", "media_type", "content"),
    [
        ("reports/page.html", "text/html", b"<script>x</script>"),
        ("reports/fake.txt", "text/plain", b"a\x00b"),
        ("reports/fake.txt", "text/plain", b"\xff\xfe"),
    ],
)
def test_preview_rejects_unsafe_or_non_text_content(
    tmp_path: Path,
    path: str,
    media_type: str,
    content: bytes,
) -> None:
    view = make_view("a1", path, media_type, content)
    catalog = FakeCatalog([(view, content)])

    with pytest.raises(ArtifactPreviewUnsupported):
        make_service(tmp_path, catalog).preview(
            job=fake_job(),
            artifact_id="a1",
        )

    assert catalog.last_body is not None
    assert catalog.last_body.was_closed is True


def test_export_contains_artifacts_and_verifiable_manifest(
    tmp_path: Path,
) -> None:
    first = b"# final\n"
    second = b'{"status":"succeeded"}'
    views = [
        make_view("a1", "reports/final.md", "text/markdown", first),
        make_view("a2", "reports/run.json", "application/json", second),
    ]
    catalog = FakeCatalog([(views[0], first), (views[1], second)])
    service = make_service(tmp_path, catalog)

    prepared = service.build_export(
        job=fake_job(),
        public_job={"job_id": "job-1", "status": "succeeded"},
    )

    assert prepared.path.is_file()
    with zipfile.ZipFile(prepared.path) as archive:
        assert archive.read("artifacts/reports/final.md") == first
        assert archive.read("artifacts/reports/run.json") == second
        assert json.loads(archive.read("metadata/job.json")) == {
            "job_id": "job-1",
            "status": "succeeded",
        }
        manifest = json.loads(
            archive.read("metadata/export_manifest.json")
        )

    expected_hash = manifest.pop("manifest_sha256")
    assert hashlib.sha256(
        canonical_json_bytes(manifest)
    ).hexdigest() == expected_hash
    assert prepared.sha256 == hashlib.sha256(
        prepared.path.read_bytes()
    ).hexdigest()
    prepared.path.unlink()


def test_export_rejects_snapshot_drift_and_removes_partial_zip(
    tmp_path: Path,
) -> None:
    content = b"original"
    view = make_view("a1", "reports/final.md", "text/markdown", content)

    class DriftingCatalog(FakeCatalog):
        def open(self, *, job: JobRecord, artifact_id: str) -> OpenedArtifact:
            opened = super().open(job=job, artifact_id=artifact_id)
            changed = opened.artifact.descriptor.model_copy(
                update={"relative_path": "reports/changed.md"}
            )
            return OpenedArtifact(
                artifact=opened.artifact.model_copy(
                    update={"descriptor": changed}
                ),
                blob=opened.blob,
            )

    service = make_service(
        tmp_path,
        DriftingCatalog([(view, content)]),
    )

    with pytest.raises(ArtifactIntegrityError):
        service.build_export(
            job=fake_job(),
            public_job={"job_id": "job-1"},
        )

    staging = tmp_path / "exports/.staging"
    assert list(staging.glob("*.part")) == []
    assert list(staging.glob("*.zip")) == []


def test_export_rejects_duplicate_archive_paths(tmp_path: Path) -> None:
    first = make_view("a1", "reports/final.md", "text/markdown", b"one")
    # 大小写不同在 Linux 可并存，但在部分解压目标会冲突，也要拒绝。
    second = make_view("a2", "reports/FINAL.md", "text/markdown", b"two")
    catalog = FakeCatalog([(first, b"one"), (second, b"two")])

    with pytest.raises(ArtifactIntegrityError):
        make_service(tmp_path, catalog).build_export(
            job=fake_job(),
            public_job={"job_id": "job-1"},
        )


def test_export_enforces_count_and_uncompressed_limits(tmp_path: Path) -> None:
    content = b"12345"
    view = make_view("a1", "reports/final.txt", "text/plain", content)
    catalog = FakeCatalog([(view, content)])

    with pytest.raises(ArtifactExportLimitExceeded):
        make_service(
            tmp_path,
            catalog,
            max_artifacts=20,
            max_uncompressed=4,
        ).build_export(
            job=fake_job(),
            public_job={"job_id": "job-1"},
        )


def test_export_staging_cannot_escape_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    catalog = FakeCatalog([])
    service = ArtifactDeliveryService(
        catalog=catalog,
        preview_max_bytes=8,
        stream_chunk_bytes=4,
        export_allowed_root=allowed,
        export_staging_root=tmp_path / "outside",
        export_max_artifacts=20,
        export_max_uncompressed_bytes=1024,
        export_max_archive_bytes=1024,
        export_staging_ttl_seconds=3600,
    )

    with pytest.raises(ArtifactIntegrityError):
        service.build_export(
            job=fake_job(),
            public_job={"job_id": "job-1"},
        )
```

### 18.1 关于第一个 UTF-8 测试

`"你好，"` 正好是 9 个 UTF-8 字节，测试上限 8 会落在全角逗号中间。实现使用 incremental decoder：它只丢弃不完整的尾部；中间位置的非法 UTF-8 仍然返回 415。不要使用 `errors="replace"` 掩盖真实内容错误。

### 18.2 运行领域测试

```bash
python -m pytest \
  --basetemp=.pytest-tmp/phase34-service \
  tests/test_artifact_delivery_service.py \
  -q
```

预期至少 9 个 case 通过，其中参数化的 unsafe preview 会展开为多个 case。

---

## 十九、增加真实 API 集成测试

> **本节类型：需要新增测试代码。**
>
> **新增文件：** `tests/test_artifact_delivery_api.py`

这个测试沿用项目现有的 JobService、ArtifactPublisher、SQLite Catalog 和 LocalBlobStore。它会在发布后删除 run 目录中的源文件，证明 API 没有偷偷绕过 BlobStore：

```python
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.app import create_api_app
from app.artifact_delivery.service import ArtifactDeliveryService
from app.config import settings
from app.job_runtime.schemas import JobRequest
from app.job_runtime.service import JobService
from app.job_runtime.store import SqliteJobStore
from app.storage.artifact_repository import SqliteArtifactRepository
from app.storage.catalog import BlobStoreRegistry, PublishedArtifactCatalog
from app.storage.local_blob_store import LocalBlobStore
from app.storage.publisher import ArtifactPublisher
from app.tools.artifact_tools import build_artifact_record
from tests.workspace_helpers import FakeWorkspaceSnapshotter


def test_artifact_preview_download_and_job_export(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "runs_dir", tmp_path / "runs")

    job_service = JobService(
        SqliteJobStore(tmp_path / "jobs.sqlite"),
        workspace_snapshotter=FakeWorkspaceSnapshotter(),
    )
    job, _created = job_service.submit(
        request=JobRequest(
            paper_path="/data/paper.pdf",
            repo_path="/data/repo",
            execution_profile_id=settings.default_execution_profile,
        ),
        thread_id="artifact-delivery-api",
        idempotency_key="artifact-delivery-api",
    )

    run_root = Path(job.run_dir)
    report = run_root / "reports/final.md"
    binary = run_root / "reports/model.bin"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Final\n<script>not executed</script>\n",
        encoding="utf-8",
    )
    binary.write_bytes(b"\x00\x01\x02")

    report_record = build_artifact_record(
        state={"run_id": job.run_id, "run_dir": job.run_dir},
        path=report,
        producer_node="test",
        media_type="text/markdown",
    )
    binary_record = build_artifact_record(
        state={"run_id": job.run_id, "run_dir": job.run_dir},
        path=binary,
        producer_node="test",
        media_type="application/octet-stream",
    )

    repository = SqliteArtifactRepository(tmp_path / "artifacts.sqlite")
    blob_store = LocalBlobStore(tmp_path / "blob-store")
    ArtifactPublisher(
        repository=repository,
        blob_store=blob_store,
    ).publish(
        job=job,
        records=[report_record, binary_record],
    )
    catalog = PublishedArtifactCatalog(
        repository=repository,
        registry=BlobStoreRegistry([blob_store]),
    )

    # 删除原始文件，后续成功只能来自发布后的 BlobStore。
    report.unlink()
    binary.unlink()

    staging_root = tmp_path / "exports/.staging"
    delivery = ArtifactDeliveryService(
        catalog=catalog,
        preview_max_bytes=1024,
        stream_chunk_bytes=4,
        export_allowed_root=tmp_path,
        export_staging_root=staging_root,
        export_max_artifacts=10,
        export_max_uncompressed_bytes=1024 * 1024,
        export_max_archive_bytes=1024 * 1024,
        export_staging_ttl_seconds=3600,
    )
    app = create_api_app(
        job_service=job_service,
        artifact_catalog=catalog,
        artifact_delivery_service=delivery,
        api_token="test-token",
    )
    auth = {"Authorization": "Bearer test-token"}

    with TestClient(app) as client:
        unauthorized = client.get(
            f"/v1/jobs/{job.job_id}/artifacts"
        )
        assert unauthorized.status_code == 401

        listing = client.get(
            f"/v1/jobs/{job.job_id}/artifacts",
            headers=auth,
        )
        assert listing.status_code == 200
        items = {
            item["artifact_id"]: item
            for item in listing.json()["items"]
        }
        assert items[report_record.artifact_id]["preview_supported"] is True
        assert items[binary_record.artifact_id]["preview_supported"] is False
        assert "object_key" not in listing.text

        preview = client.get(
            f"/v1/jobs/{job.job_id}/artifacts/"
            f"{report_record.artifact_id}/preview",
            headers=auth,
        )
        assert preview.status_code == 200
        assert "<script>not executed</script>" in preview.json()["content"]
        assert preview.json()["truncated"] is False

        rejected = client.get(
            f"/v1/jobs/{job.job_id}/artifacts/"
            f"{binary_record.artifact_id}/preview",
            headers=auth,
        )
        assert rejected.status_code == 415
        assert rejected.json()["code"] == "ARTIFACT_PREVIEW_UNSUPPORTED"

        download = client.get(
            f"/v1/jobs/{job.job_id}/artifacts/"
            f"{report_record.artifact_id}/download",
            headers=auth,
        )
        assert download.status_code == 200
        assert download.content.startswith(b"# Final")
        assert download.headers["content-type"].startswith(
            "application/octet-stream"
        )
        assert "attachment" in download.headers["content-disposition"]
        assert download.headers["x-artifact-sha256"] == report_record.sha256
        assert download.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in download.headers["content-security-policy"]

        # 旧 Chat citation 使用的 /content 仍然有效，并走同一安全响应。
        compatibility = client.get(
            f"/v1/jobs/{job.job_id}/artifacts/"
            f"{report_record.artifact_id}/content",
            headers=auth,
        )
        assert compatibility.status_code == 200
        assert compatibility.content == download.content

        exported = client.get(
            f"/v1/jobs/{job.job_id}/export",
            headers=auth,
        )
        assert exported.status_code == 200
        assert exported.headers["content-type"].startswith("application/zip")
        assert "attachment" in exported.headers["content-disposition"]
        assert len(exported.headers["x-export-sha256"]) == 64

    # TestClient 已消费完整响应，generator finally 应删除临时 ZIP。
    assert list(staging_root.glob("*.part")) == []
    assert list(staging_root.glob("*.zip")) == []

    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert archive.read("artifacts/reports/final.md").startswith(b"# Final")
        assert archive.read("artifacts/reports/model.bin") == b"\x00\x01\x02"
        manifest = json.loads(
            archive.read("metadata/export_manifest.json")
        )
        public_job = json.loads(archive.read("metadata/job.json"))

    assert manifest["job_id"] == job.job_id
    assert manifest["run_id"] == job.run_id
    assert manifest["artifact_count"] == 2
    serialized = json.dumps(
        {"manifest": manifest, "job": public_job},
        ensure_ascii=False,
    )
    assert "run_dir" not in serialized
    assert "object_key" not in serialized
    assert "claim_token" not in serialized
```

运行：

```bash
python -m pytest \
  --basetemp=.pytest-tmp/phase34-api \
  tests/test_artifact_delivery_api.py \
  -q
```

如果 `unauthorized.status_code` 在你的认证模式中不是 401，而是 403，请以现有 `tests/test_api_*auth*.py` 的项目约定为准，但必须保留“未认证不能列出、预览、下载或导出”的测试。

---

## 二十、增加前端安全渲染测试

> **本节类型：需要新增测试代码。**
>
> **新增文件：** `web/tests/artifact-delivery.test.tsx`

写入：

```tsx
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../src/api/client";
import { RunContextPanel } from "../src/components/RunContextPanel";
import type { ArtifactPreview, ArtifactView, JobView } from "../src/api/types";

const job: JobView = {
  job_id: "job-1",
  thread_id: "thread-1",
  run_id: "run-1",
  status: "succeeded",
  version: 4,
  attempt_count: 1,
  max_attempts: 3,
  wait_generation: 0,
  interrupts: [],
  cancel_requested: false,
  cancellation_reason: null,
  result: null,
  error: null,
  reconciliation: null,
  input: {
    paper_name: "paper.pdf",
    repo_name: "repo",
    experiment_goal: "reproduce main result",
    execution_profile_id: "local",
  },
  allowed_operations: [],
  created_at: "2026-08-06T00:00:00Z",
  updated_at: "2026-08-06T00:01:00Z",
};

const artifact: ArtifactView = {
  artifact_id: "artifact-1",
  run_id: "run-1",
  layer: "reports",
  relative_path: "reports/final.md",
  media_type: "text/markdown",
  sha256: "a".repeat(64),
  size_bytes: 42,
  producer_node: "final_report_node",
  created_at: "2026-08-06T00:01:00Z",
  preview_supported: true,
  integrity_status: "unchecked",
};

const preview: ArtifactPreview = {
  artifact_id: artifact.artifact_id,
  relative_path: artifact.relative_path,
  media_type: artifact.media_type,
  sha256: artifact.sha256,
  total_size_bytes: 42,
  returned_bytes: 42,
  truncated: false,
  encoding: "utf-8",
  content: '<script data-test="unsafe">window.pwned = true</script>',
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("artifact delivery", () => {
  it("previews as text and exposes download/export links", async () => {
    vi.spyOn(api, "artifacts").mockResolvedValue([artifact]);
    vi.spyOn(api, "artifactPreview").mockResolvedValue(preview);

    const { container } = render(
      <RunContextPanel
        job={job}
        onMutation={async (action) => {
          await action();
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "artifacts" }));
    fireEvent.click(await screen.findByRole("button", { name: "Preview" }));

    await waitFor(() => {
      expect(api.artifactPreview).toHaveBeenCalledWith(
        "job-1",
        "artifact-1",
      );
    });

    // 字符串可见，但 DOM 中没有 script 元素。
    expect(await screen.findByText(preview.content)).toBeTruthy();
    expect(container.querySelector(".artifact-preview script")).toBeNull();

    expect(
      screen.getByRole("link", { name: "Download" }).getAttribute("href"),
    ).toBe(
      "/v1/jobs/job-1/artifacts/artifact-1/download",
    );
    expect(
      screen.getByRole("link", { name: "Export job (.zip)" })
        .getAttribute("href"),
    ).toBe("/v1/jobs/job-1/export");
  });

  it("does not offer preview when the server disables it", async () => {
    vi.spyOn(api, "artifacts").mockResolvedValue([
      {
        ...artifact,
        artifact_id: "binary-1",
        relative_path: "reports/model.bin",
        media_type: "application/octet-stream",
        preview_supported: false,
      },
    ]);

    render(
      <RunContextPanel job={job} onMutation={async () => undefined} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "artifacts" }));
    await screen.findByText("reports/model.bin");

    expect(screen.queryByRole("button", { name: "Preview" })).toBeNull();
    expect(screen.getByRole("link", { name: "Download" })).toBeTruthy();
  });
});
```

运行：

```bash
cd web
npm test -- artifact-delivery.test.tsx
npm run typecheck
npm run build
cd ..
```

这个测试不是在证明 React 永远安全，而是在锁定本阶段的关键约束：预览内容只能进入文本节点，不能改成 HTML 注入。

---

## 二十一、更新已有回归测试

> **本节类型：需要检查并可能修改已有测试。**

### 21.1 `tests/test_artifact_storage_api.py`

旧测试可能断言 `/content` 返回原 media type。Phase 34 后 `/content` 是安全下载兼容别名，应该改为：

```python
assert response.headers["content-type"].startswith(
    "application/octet-stream"
)
assert "attachment" in response.headers["content-disposition"]
assert response.headers["x-content-type-options"] == "nosniff"
```

仍保留：

```python
assert response.content == b"durable artifact"
assert "object_key" not in response.headers
```

### 21.2 `web/tests/chat-panel.test.tsx`

当前 Chat citation 仍指向：

```text
/v1/jobs/{job_id}/artifacts/{artifact_id}/content
```

本阶段保留了兼容别名，所以旧测试可以不改。若想统一新 URL，可以把 `JobChatPanel` 改为调用 `api.artifactDownloadUrl()`，并同步把期望改成 `/download`。这不是本阶段阻塞项。

### 21.3 全量回归

```bash
python -m pytest \
  --basetemp=.pytest-tmp/phase34-full \
  -q

cd web
npm test
npm run typecheck
npm run build
cd ..

python -m ruff check app tests
```

如果全量测试很慢，先运行本阶段测试和原 Artifact 测试：

```bash
python -m pytest \
  --basetemp=.pytest-tmp/phase34-artifact-regression \
  tests/test_artifact_delivery_service.py \
  tests/test_artifact_delivery_api.py \
  tests/test_artifact_storage_api.py \
  tests/test_published_artifact_catalog.py \
  tests/test_interaction_artifacts.py \
  -q
```

---

## 二十二、推荐实施顺序

> **本节类型：实施建议，不新增额外代码。**

不要先改 Web 再补后端。推荐按以下顺序：

1. 修改 `.gitignore`、`.env.example` 和 `app/config.py`；
2. 新增 `artifact_delivery/errors.py` 和 `schemas.py`；
3. 新增 `ArtifactDeliveryService`；
4. 先运行领域测试，修正预览、hash、路径和清理逻辑；
5. 扩展 `ArtifactView.preview_supported`；
6. 修改错误映射和 App Factory 注入；
7. 修改 Artifact 列表、预览、下载、导出路由；
8. 运行 API 集成测试和已有 Artifact 回归；
9. 修改 TypeScript 类型和 API client；
10. 新增 PreviewPanel 并接入 RunContextPanel；
11. 增加前端安全测试、typecheck 和 build；
12. 运行全量后端与前端回归；
13. 最后执行真实 Job 手工验收。

每一步都建立在上一层稳定边界上。领域测试失败时不要先通过路由捕获所有异常来“让接口返回 200”；应先修复领域不变量。

---

## 二十三、静态检查与自动化测试

> **本节类型：验证步骤，不修改项目代码。**

### 23.1 后端定向测试

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

python -m pytest \
  --basetemp=.pytest-tmp/phase34-targeted \
  tests/test_artifact_delivery_service.py \
  tests/test_artifact_delivery_api.py \
  tests/test_artifact_storage_api.py \
  tests/test_published_artifact_catalog.py \
  tests/test_interaction_artifacts.py \
  -q
```

### 23.2 后端全量测试和 Ruff

```bash
python -m pytest \
  --basetemp=.pytest-tmp/phase34-full \
  -q
python -m ruff check app tests
```

### 23.3 前端测试和构建

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot/web

npm test
npm run typecheck
npm run build
```

### 23.4 配置加载检查

回到项目根目录：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

python -c "from app.config import settings; print(settings.job_export_staging_root); print(settings.artifact_preview_max_bytes)"
```

预期 staging 位于：

```text
/data/tianshaoqi24/agent/paper_reproduction_copilot/exports/.staging
```

如果输出相对路径 `exports/.staging` 也能工作，但启动进程的 working directory 必须固定为项目根目录。部署时更推荐 `.env` 中的绝对路径。

---

## 二十四、手工验收前准备

> **本节类型：详细手工验收，不修改源代码。会在项目目录内产生验收下载文件。**

### 24.1 设置项目内验收目录

所有临时验收文件都放在当前项目内：

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot

mkdir -p manual_acceptance/phase34
```

不要把验收文件写到 `/tmp`，也不要写到论文代码仓库中。

### 24.2 检查 `.env`

至少确认：

```dotenv
JOB_EXPORT_ALLOWED_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot
JOB_EXPORT_STAGING_ROOT=/data/tianshaoqi24/agent/paper_reproduction_copilot/exports/.staging
ARTIFACT_PREVIEW_MAX_BYTES=262144
JOB_EXPORT_MAX_ARTIFACTS=500
JOB_EXPORT_MAX_UNCOMPRESSED_BYTES=1073741824
JOB_EXPORT_MAX_ARCHIVE_BYTES=536870912
JOB_EXPORT_STAGING_TTL_SECONDS=3600
```

如设置了 API token，在当前 shell 中准备同一个值：

```bash
export AGENT_API_TOKEN='<你的本地 token>'
```

不要把真实 token 写进教程、Git 或命令输出文件。

### 24.3 构建 Web

```bash
cd /data/tianshaoqi24/agent/paper_reproduction_copilot/web
npm run build
cd /data/tianshaoqi24/agent/paper_reproduction_copilot
```

### 24.4 启动单机服务

```bash
python -m app.main serve-stack --host 127.0.0.1 --port 8000
```

保持这个终端运行，在另一个终端执行后续命令。

### 24.5 选择一个已有 Job

优先选择已经产生 `reports/final_report.md`、JSON 和日志 Artifact 的 Job。可以在 Web 中打开任务，也可以列出最近任务：

```bash
curl -sS \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  'http://127.0.0.1:8000/v1/jobs?limit=20' \
  | python -m json.tool
```

把目标 Job ID 保存为 shell 变量：

```bash
export JOB_ID='<替换为真实 job_id>'
```

如果没有已发布 Artifact 的 Job，先通过 Web 创建一次小任务，等待它至少完成论文读取和报告发布。Phase 34 不要求论文复现必须成功，失败 Job 的日志和错误报告同样可以导出。

---

## 二十五、手工验收 Artifact 列表和预览

> **本节类型：详细手工验收，不修改源代码。**

### 25.1 获取 Artifact 列表

```bash
curl -sS \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  "http://127.0.0.1:8000/v1/jobs/${JOB_ID}/artifacts" \
  > manual_acceptance/phase34/artifacts.json

python -m json.tool manual_acceptance/phase34/artifacts.json
```

检查：

```text
每项都有 artifact_id、run_id、relative_path、sha256 和 size_bytes
Markdown/JSON/TXT/LOG 等安全文本有 preview_supported=true
PDF、BIN、ZIP、图片等为 preview_supported=false
响应中没有 absolute_path、run_dir、object_key、claim_token
```

选择一个 `preview_supported=true` 的 Artifact：

```bash
export TEXT_ARTIFACT_ID='<替换为真实 artifact_id>'
```

### 25.2 调用预览接口

```bash
curl -sS \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  "http://127.0.0.1:8000/v1/jobs/${JOB_ID}/artifacts/${TEXT_ARTIFACT_ID}/preview" \
  > manual_acceptance/phase34/preview.json

python -m json.tool manual_acceptance/phase34/preview.json
```

检查：

```text
encoding 是 utf-8
content 是文本字符串
returned_bytes 不大于 ARTIFACT_PREVIEW_MAX_BYTES
total_size_bytes 与列表一致
sha256 与列表一致
大文件被截断时 truncated=true
```

### 25.3 验证二进制不能预览

从列表中选择一个 `preview_supported=false` 的 Artifact：

```bash
export BINARY_ARTIFACT_ID='<替换为真实 artifact_id>'
```

执行：

```bash
curl -sS -i \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  "http://127.0.0.1:8000/v1/jobs/${JOB_ID}/artifacts/${BINARY_ARTIFACT_ID}/preview"
```

预期：

```text
HTTP 415
code = ARTIFACT_PREVIEW_UNSUPPORTED
仍然可以通过 /download 下载
```

### 25.4 Web 验收

浏览器打开：

```text
http://127.0.0.1:8000
```

选择相同 Job，切换到 `artifacts`：

1. 安全文本条目出现 Preview；
2. 二进制条目只有 Download；
3. Preview 在当前面板内以等宽纯文本显示；
4. Markdown 标题、HTML 标签和 `<script>` 只显示字符，不被执行；
5. Close 可以关闭预览；
6. 切换到另一个 Job 后，不保留旧 Job 的预览。

---

## 二十六、手工验收单文件下载

> **本节类型：详细手工验收，不修改源代码。**

### 26.1 下载并保存响应头

```bash
curl -sS \
  -D manual_acceptance/phase34/download.headers \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  "http://127.0.0.1:8000/v1/jobs/${JOB_ID}/artifacts/${TEXT_ARTIFACT_ID}/download" \
  -o manual_acceptance/phase34/downloaded-artifact.bin

cat manual_acceptance/phase34/download.headers
```

检查响应头至少包含：

```text
Content-Type: application/octet-stream
Content-Disposition: attachment
Content-Length: 与 Artifact size_bytes 一致
ETag: "sha256:<Artifact sha256>"
X-Artifact-SHA256: <Artifact sha256>
Cache-Control: private, no-store
X-Content-Type-Options: nosniff
```

### 26.2 验证下载内容 SHA-256

```bash
sha256sum manual_acceptance/phase34/downloaded-artifact.bin
```

输出 hash 必须与 `artifacts.json` 中该 Artifact 的 `sha256` 完全相同。

### 26.3 验证旧 `/content` 兼容地址

```bash
curl -sS \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  "http://127.0.0.1:8000/v1/jobs/${JOB_ID}/artifacts/${TEXT_ARTIFACT_ID}/content" \
  -o manual_acceptance/phase34/legacy-content.bin

cmp \
  manual_acceptance/phase34/downloaded-artifact.bin \
  manual_acceptance/phase34/legacy-content.bin
```

`cmp` 无输出且退出码为 0 表示兼容地址和新下载地址返回相同字节。

---

## 二十七、手工验收单 Job ZIP 导出

> **本节类型：详细手工验收，不修改源代码。**

### 27.1 下载导出包

```bash
curl -sS \
  -D manual_acceptance/phase34/export.headers \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  "http://127.0.0.1:8000/v1/jobs/${JOB_ID}/export" \
  -o manual_acceptance/phase34/job-export.zip

cat manual_acceptance/phase34/export.headers
```

检查：

```text
Content-Type 是 application/zip
Content-Disposition 是 attachment
Content-Length 与实际 ZIP 大小一致
X-Export-SHA256 是 64 位小写十六进制
ETag 使用同一个 ZIP SHA-256
```

### 27.2 验证 ZIP 自身 hash

```bash
sha256sum manual_acceptance/phase34/job-export.zip
```

必须与 `X-Export-SHA256` 一致。

### 27.3 检查 ZIP 目录

```bash
unzip -t manual_acceptance/phase34/job-export.zip
unzip -l manual_acceptance/phase34/job-export.zip
```

预期：

```text
unzip -t 报 No errors detected
包含 metadata/job.json
包含 metadata/export_manifest.json
每个 Artifact 位于 artifacts/<原 relative_path>
不包含绝对路径
不包含 ../
不包含 exports/.staging 路径
```

### 27.4 验证 manifest 自身 hash 和每个 Artifact

下面的命令只读取 ZIP，不写入系统临时目录：

```bash
python - <<'PY'
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

archive_path = Path(
    "/data/tianshaoqi24/agent/paper_reproduction_copilot/"
    "manual_acceptance/phase34/job-export.zip"
)

with zipfile.ZipFile(archive_path) as archive:
    manifest = json.loads(
        archive.read("metadata/export_manifest.json")
    )

    expected_manifest_hash = manifest.pop("manifest_sha256")
    canonical = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    actual_manifest_hash = hashlib.sha256(canonical).hexdigest()
    assert actual_manifest_hash == expected_manifest_hash

    for item in manifest["artifacts"]:
        member_path = item["archive_path"]
        assert not member_path.startswith("/")
        assert ".." not in Path(member_path).parts
        content = archive.read(member_path)
        assert len(content) == item["size_bytes"]
        assert hashlib.sha256(content).hexdigest() == item["sha256"]

serialized = json.dumps(manifest, ensure_ascii=False)
for forbidden in (
    "run_dir",
    "object_key",
    "claim_token",
    "workspace_assignment_token",
):
    assert forbidden not in serialized

print(
    "verified",
    manifest["artifact_count"],
    "artifacts for job",
    manifest["job_id"],
)
PY
```

不要直接对不受信任 ZIP 执行 `unzip -d`。本阶段生成器已经限制 member path，但验收优先使用 `zipfile.read()`，避免把“检查归档”变成“向文件系统写归档”。

### 27.5 确认响应结束后 staging 已清理

```bash
find \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/exports/.staging \
  -maxdepth 1 \
  -type f \
  -print
```

正常完成后不应看到刚刚生成的 `.zip` 或 `.part`。若 API 进程在响应期间被强制杀死，文件可能暂时保留；下一次导出会按 TTL 清理。

---

## 二十八、手工验收限制和失败路径

> **本节类型：详细手工验收，需要临时改环境配置并重启服务，不修改源代码。**

### 28.1 验证 Artifact 数量上限

停止 `serve-stack`，在当前 shell 临时设置：

```bash
export JOB_EXPORT_MAX_ARTIFACTS=1
python -m app.main serve-stack --host 127.0.0.1 --port 8000
```

选择一个至少有两个 Artifact 的 Job，再请求导出：

```bash
curl -sS -i \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  "http://127.0.0.1:8000/v1/jobs/${JOB_ID}/export"
```

预期：

```text
HTTP 413
code = ARTIFACT_EXPORT_LIMIT_EXCEEDED
响应是 JSON，不是半截 ZIP
staging 中没有新增残留文件
```

验收后恢复：

```bash
unset JOB_EXPORT_MAX_ARTIFACTS
```

再按正常配置重启服务。

### 28.2 验证过期残留清理

仅在项目 staging 中创建人工残留：

```bash
mkdir -p \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/exports/.staging

touch \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/exports/.staging/manual-old.part

touch -d '2 hours ago' \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/exports/.staging/manual-old.part
```

在 TTL 为 3600 秒时再次请求一次导出，然后检查：

```bash
test ! -e \
  /data/tianshaoqi24/agent/paper_reproduction_copilot/exports/.staging/manual-old.part
```

退出码 0 表示旧残留已删除。清理器只删除 staging 根目录直属的 `.part` 和 `.zip`，不递归、不跟随目录、不处理其他扩展名。

### 28.3 验证错误 Job 或 Artifact 不能越权读取

准备两个 Job，取 Job A 的 `artifact_id`，放入 Job B URL：

```bash
curl -sS -i \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  "http://127.0.0.1:8000/v1/jobs/${OTHER_JOB_ID}/artifacts/${TEXT_ARTIFACT_ID}/download"
```

预期 404，不应因为 `artifact_id` 全局存在就允许下载。相同检查也要对 `/preview` 执行。

### 28.4 验证客户端中断后的清理

如果 Job 导出包足够大，可以限制下载速度后按 `Ctrl+C`：

```bash
curl --limit-rate 32k \
  -H "Authorization: Bearer ${AGENT_API_TOKEN}" \
  "http://127.0.0.1:8000/v1/jobs/${JOB_ID}/export" \
  -o manual_acceptance/phase34/interrupted.zip
```

中断后等待数秒，再检查 staging。Starlette 正常取消响应迭代器时会进入 generator 的 `finally`。若直接 `kill -9` API 进程，无法执行 `finally`，这正是 TTL 清理存在的原因。

---

## 二十九、安全验收清单

> **本节类型：安全复核，不修改项目代码。**

逐项确认：

- API 只接受 `job_id` 和 `artifact_id`，不接受文件路径或 object key；
- `ArtifactCatalog.open()` 仍然验证 Artifact 属于当前 Job 和 run；
- Preview allowlist 同时检查 media type 与 suffix；
- HTML、SVG、PDF、图片、ZIP、模型权重和未知类型不能预览；
- Preview 最大读取 `max_bytes + 1`，不会全量读取大对象；
- Preview 严格验证 UTF-8、NUL 和控制字符；
- 前端不使用 `dangerouslySetInnerHTML`；
- Download 使用 `attachment + octet-stream + nosniff`；
- Content-Disposition 的 ASCII fallback 不包含 CR/LF 或引号注入；
- ZIP member 只使用受校验的相对 POSIX 路径；
- ZIP 拒绝 `/`、`..`、空 segment、反斜杠、NUL，以及大小写折叠后重复的路径；
- 导出前检查 Artifact 数量与未压缩总大小；
- 导出后检查 ZIP 大小；
- 每个 Blob 在写入 ZIP 时重新计算大小和 SHA-256；
- `list_views()` 与 `open()` descriptor 不一致时返回 409；
- 构建失败时 `.part` 和 `.zip` 都会删除；
- 导出响应结束或断开时临时 ZIP 删除；
- staging root 不能是软链接；
- staging root 解析后必须位于 `JOB_EXPORT_ALLOWED_ROOT` 内；
- 过期清理只处理 staging 直属 `.part/.zip`；
- manifest 只包含公开 Job 投影；
- manifest 和响应不包含 `run_dir`、`object_key`、token 或本地绝对路径；
- 未认证请求不能列出、预览、下载或导出；
- Job A 的 Artifact ID 不能放到 Job B URL 中读取。

---

## 三十、错误类型和处理方式

> **本节类型：问题排查，不修改项目代码。**

| 错误 | 含义 | 是否重试 | 处理方式 |
|---|---|---|---|
| `JOB_NOT_FOUND` | Job ID 不存在 | 否 | 刷新 Job 列表并检查 ID |
| `ARTIFACT_NOT_FOUND` | Artifact 不存在或不属于当前 Job | 否 | 重新获取当前 Job 的 Artifact 列表 |
| `ARTIFACT_PREVIEW_UNSUPPORTED` | 类型、编码或内容不满足安全预览策略 | 否 | 使用 Download，不要放宽到 HTML/SVG |
| `ARTIFACT_INTEGRITY_ERROR` | run、路径、大小、hash 或快照发生漂移 | 否 | 停止交付，检查 Catalog/Blob 发布与并发更新 |
| `ARTIFACT_EXPORT_LIMIT_EXCEEDED` | 数量、未压缩总大小或 ZIP 大小超限 | 否 | 调整合理上限，或只下载必要 Artifact |
| `ARTIFACT_BACKEND_UNAVAILABLE` | S3/MinIO/本地存储暂时不可用 | 是 | 检查 readiness、网络与存储后重试 |

导出失败不应修改 Job 状态。Job 的执行结果已经产生，导出只是读取交付；失败应记录 HTTP/telemetry，而不是把 `succeeded` Job 改成 `failed`。

---

## 三十一、常见问题

> **本节类型：问题排查，不修改项目代码。**

### 31.1 文本 Artifact 没有 Preview 按钮

检查两个字段：

```text
media_type 是否位于 SAFE_PREVIEW_MEDIA_TYPES
relative_path 后缀是否位于 SAFE_PREVIEW_SUFFIXES
```

例如 `reports/final_report` 没有扩展名，即使 media type 是 `text/plain`，第一版仍保守地不允许预览。优先修正 Artifact 命名和 media type，不要让前端自行猜测。

### 31.2 中文大文件偶尔预览失败

确认使用的是教程中的 incremental UTF-8 decoder，而不是直接：

```python
bounded.decode("utf-8")
```

直接 decode 会在字节上限切中汉字时误报。若仍失败，说明非法字节位于内容中间，应保持 415 并下载原文件检查编码。

### 31.3 点击 Download 后返回 JSON 解析错误

不要使用 `request<T>()` 获取 ZIP 或原始文件。该 helper 会调用 `response.json()`。下载和导出应使用普通 `<a href>`，或未来增加专门的流式下载函数。

### 31.4 Bearer token 模式下 `<a>` 返回 401

普通链接无法自定义 Authorization header。单机同源部署优先使用安全 Cookie；或以后增加短期、单次、绑定 `job_id + artifact_id` 的 download capability。不要把长期 token 放入 URL。

### 31.5 ZIP 构建很慢，API 暂时不能响应其他请求

当前路由是同步函数，FastAPI 会在线程池执行，且有数量/大小上限，适合单机单用户第一版。如果导出达到数 GiB 或多个用户并发导出，应升级为异步 Export Job，而不是继续扩大同步限制。

### 31.6 staging 中一直有 ZIP

区分三种情况：

```text
正在下载：正常，响应结束后删除。
API 被 kill -9：finally 无法运行，等待 TTL 或下次导出清理。
正常响应后仍存在：检查 _iter_file_and_delete 是否真正作为 StreamingResponse body。
```

### 31.7 导出返回 409，但单个 Artifact 可以下载

导出冻结的是一组 descriptor 快照。可能在 list 后 Catalog revision 变化，或存在重复 relative path。单文件下载只验证一个当前对象，因此仍可能成功。重新获取列表后再导出；若持续发生，检查 Artifact publication 的 current-head 规则。

### 31.8 ZIP 中缺少执行日志

只有发布到 Artifact Catalog 的文件才会导出。`/logs` 读取的当前日志若未注册为 Artifact，不会自动进入 ZIP。正确做法是确保 Phase 15/24 的日志发布逻辑把最终日志注册为 `execution/*.log`，不要让 Delivery Service读取 `job.run_dir` 补文件。

### 31.9 ZIP 中出现内部字段

检查 `build_export()` 是否接收：

```python
service.get_job(job_id).model_dump(mode="json")
```

而不是：

```python
service.job_service.get(job_id).model_dump()
```

后者是内部 JobRecord，禁止导出。

### 31.10 Windows 解压工具显示路径异常

确认所有 member 使用 `PurePosixPath` 和 `/`，不要使用 `Path` 生成 ZIP member。`Path` 会随运行平台改变分隔符。

---

## 三十二、本阶段涉及的 Agent 知识点

> **本节类型：知识总结，不修改项目代码。**

### 32.1 Agent 输出也是受控能力

Agent 不仅需要限制“能读取什么”和“能执行什么”，也要限制“能向用户交付什么”。Artifact Catalog 是能力边界：用户获得的是某个 Job 已发布的 Artifact，而不是宿主机任意文件读取能力。

### 32.2 Provenance 与 Portability

单独复制 `final_report.md` 会丢失上下文。导出 manifest 把 Artifact 的 run、producer、hash、media type 和路径一起保存，使结果可以离开当前服务后继续验证。

### 32.3 Validate at Use

Artifact 发布时验证一次不代表交付时永远可信。预览、下载和导出发生在更晚时间，必须在实际打开和读取时重新确认大小与 hash。这与 Resource、Approval Hash 和 Workspace Materialization 的原则一致。

### 32.4 Snapshot Isolation

导出不是“遍历过程中看到什么就打包什么”，而是先冻结一组 descriptor，再要求每次 open 与快照一致。它是一个轻量的应用层 snapshot protocol。

### 32.5 Structured Evidence Package

ZIP 不是一堆无结构文件。`export_manifest.json` 是机器可读索引，可被后续评测、审计、迁移、Run diff 或另一个 Agent 消费。

### 32.6 Fail Closed

遇到未知媒体类型、非法编码、重复路径、hash 漂移或超限时，默认拒绝预览/导出。用户仍可在身份校验通过后下载原始字节，但系统不猜测内容语义。

### 32.7 Bounded Context 与 Bounded I/O

Chat Agent 有 context budget，执行器有资源预算，交付层同样需要 preview、artifact count、uncompressed bytes 和 archive bytes 上限。Agent 系统的每个边界都应显式有界。

### 32.8 Durable Artifact 与 Ephemeral Projection

Artifact 是长期、可寻址、可校验对象；ZIP 是按请求生成的临时投影。区分 durable data 和 ephemeral delivery 可以避免递归 Artifact、重复存储和难以解释的生命周期。

---

## 三十三、完成标准

> **本节类型：最终验收，不修改项目代码。**

- `.env.example` 有预览、导出数量、大小、staging 和 TTL 配置；
- `exports/` 已加入 `.gitignore`；
- staging 位于项目目录，不使用 `/tmp`；
- `ArtifactView` 有默认关闭的 `preview_supported`；
- Delivery Service 统一实现 list、preview 和 export；
- Preview 同时检查媒体类型、后缀、UTF-8、NUL 和控制字符；
- Preview 有严格字节上限并正确处理 UTF-8 尾部；
- HTML、SVG 和二进制预览返回 415；
- Download 强制 `attachment + octet-stream + nosniff`；
- `/content` 兼容地址仍有效；
- 导出冻结 descriptor 快照；
- ZIP member path 拒绝路径逃逸和重复；
- 每个 Artifact 写入时重新计算大小和 SHA-256；
- ZIP 包含公开 `job.json` 和可自校验的 `export_manifest.json`；
- 导出包不包含内部路径、object key 或 token；
- 导出在开始响应前完成构建和校验；
- 失败时清理 `.part/.zip`；
- 响应结束或断开时删除临时 ZIP；
- 崩溃残留可由 TTL 清理；
- 前端只以文本节点显示预览；
- Web 有 Preview、Download 和 Export 按钮；
- 领域测试、API 集成、前端安全测试、全量回归和 build 全部通过；
- 真实 Job 导出的 manifest 和每个 Artifact hash 均可离线验证。

---

## 三十四、Phase 34 之后做什么

> **本节类型：后续路线，不修改项目代码。**

在单机单用户、先把完整产品做稳、暂不继续扩大分布式复杂度的前提下，下一阶段建议：

```text
Phase 35：单机数据保留、配额与可审计垃圾回收
```

原因是系统已经产生多类持久数据：

```text
Resource Blob 与本地导入 staging
Job/Checkpoint/Event/Chat 数据库
Artifact Catalog 与 BlobStore
Workspace snapshot/materialization
运行日志、trace 与手工导出残留
```

如果没有 retention 和 quota，单机长期运行后最先遇到的通常不是 Agent 推理问题，而是磁盘耗尽、旧数据不知道能否删除、数据库记录与 Blob 不一致。

Phase 35 第一版应保持简单：

```text
容量与年龄统计 API
按 Job 展示可回收字节
Preview -> Confirm -> Sweep 两阶段 GC
删除前绑定 cleanup_plan_hash
只清理终态且超过保留期的 Job
Artifact/Resource 引用计数与 orphan 检测
Checkpoint、Event、Chat、Workspace 的明确删除顺序
dry-run 默认开启
结构化 cleanup report Artifact/审计记录
Web 一个简洁的 Storage 页面
```

后续再按实际需求考虑：

```text
P2 Chat Citation Golden Eval
P2 两个 Run 的 Manifest/Artifact Diff
P2 异步大导出与下载 capability
P3 多用户 RBAC、对象锁和法务保留策略
```

此时仍不建议优先做多 Agent 编排、Redis、消息队列或复杂前端。先让单机系统能够安全地接收输入、运行、交互、交付结果并管理自身数据生命周期。
