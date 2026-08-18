from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

import psutil

from app.config import settings
from app.execution.container_engine import ContainerEngine
from app.execution.container_errors import (
    ContainerRuntimeUnavailable,
)
from app.execution.profile_store import (
    compute_execution_policy_hash,
    load_execution_profiles,
)
from app.schemas import ExecutionProfile
from app.workspace.errors import WorkerCapabilityError
from app.workspace.schemas import (
    JobRequirements,
    SchedulingExplanation,
    WorkerCapabilities,
    WorkerIdentity,
)


def requirements_from_profile(
    profile: ExecutionProfile,
) -> JobRequirements:
    """只从受信任 profile 派生，绝不接受模型自行降低要求。"""

    return JobRequirements(
        worker_pool=profile.worker_pool,
        execution_profile_id=profile.profile_id,
        execution_policy_hash=compute_execution_policy_hash(profile),
        execution_backend=profile.backend,
        min_workspace_free_bytes=profile.min_workspace_free_bytes,
        min_gpu_count=profile.min_gpu_count,
        cuda_major=profile.cuda_major,
        required_labels=profile.required_worker_labels,
    )


def load_worker_capabilities(
    path: Path | None = None,
) -> WorkerCapabilities:
    config_path = (path or settings.worker_capabilities_path).resolve()
    if not config_path.is_file():
        raise WorkerCapabilityError(
            f"Worker capability 文件不存在：{config_path}"
        )

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    declared = WorkerCapabilities.model_validate(payload)

    profiles = load_execution_profiles()
    missing = sorted(
        set(declared.execution_profile_ids) - set(profiles)
    )
    if missing:
        raise WorkerCapabilityError(
            "Worker 声明了本机不存在的 profile：" + ", ".join(missing)
        )

    actual_backends = {
        profiles[profile_id].backend
        for profile_id in declared.execution_profile_ids
    }
    if not actual_backends.issubset(
        set(declared.execution_backends)
    ):
        raise WorkerCapabilityError(
            "execution_backends 未覆盖已声明 profile"
        )

    workspace_root = settings.worker_workspace_root.resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(workspace_root).free

    normalized_mounts: dict[str, str] = {}
    allowed_root = settings.allowed_root.resolve()
    for label, raw_path in declared.dataset_mounts.items():
        if label not in declared.labels:
            raise WorkerCapabilityError(
                f"dataset_mount label 未出现在 labels：{label}"
            )
        mount = Path(raw_path).expanduser()
        if not mount.is_absolute():
            raise WorkerCapabilityError(
                f"dataset mount 必须是绝对路径：{label}"
            )
        resolved = mount.resolve()
        if resolved != allowed_root and allowed_root not in resolved.parents:
            raise WorkerCapabilityError(
                f"dataset mount 位于 ALLOWED_ROOT 外：{label}"
            )
        normalized_mounts[label] = str(resolved)

    return declared.model_copy(
        update={
            "cpu_count": os.cpu_count() or declared.cpu_count,
            "memory_bytes": int(psutil.virtual_memory().total),
            "workspace_free_bytes": int(free_bytes),
            "execution_policy_hashes": {
                profile_id: compute_execution_policy_hash(
                    profiles[profile_id]
                )
                for profile_id in declared.execution_profile_ids
            },
            "dataset_mounts": normalized_mounts,
        }
    )


def build_worker_identity(
    *,
    worker_id: str,
    worker_session_id: str | None = None,
) -> WorkerIdentity:
    return WorkerIdentity(
        worker_id=worker_id,
        worker_session_id=(
            worker_session_id or f"ws_{uuid4().hex}"
        ),
        host_id=settings.worker_host_id,
        pool=settings.worker_pool,
        workspace_root=str(
            settings.worker_workspace_root.resolve()
        ),
        capabilities=load_worker_capabilities(),
    )


def explain_compatibility(
    *,
    requirements: JobRequirements,
    worker: WorkerIdentity,
    affinity_host_id: str | None,
) -> SchedulingExplanation:
    """供单元测试、CLI explain 和 SQL 语义对照使用。"""

    caps = worker.capabilities
    reasons: list[str] = []

    if worker.pool != requirements.worker_pool:
        reasons.append("worker_pool_mismatch")
    if (
        requirements.execution_profile_id
        not in caps.execution_profile_ids
    ):
        reasons.append("execution_profile_missing")
    elif (
        caps.execution_policy_hashes.get(
            requirements.execution_profile_id
        )
        != requirements.execution_policy_hash
    ):
        reasons.append("execution_policy_hash_mismatch")
    if requirements.execution_backend not in caps.execution_backends:
        reasons.append("execution_backend_missing")
    if caps.workspace_free_bytes < requirements.min_workspace_free_bytes:
        reasons.append("workspace_disk_insufficient")
    if caps.gpu_count < requirements.min_gpu_count:
        reasons.append("gpu_count_insufficient")
    if (
        requirements.cuda_major is not None
        and caps.cuda_major != requirements.cuda_major
    ):
        reasons.append("cuda_major_mismatch")
    if not set(requirements.required_labels).issubset(set(caps.labels)):
        reasons.append("required_worker_label_missing")
    if affinity_host_id is not None and worker.host_id != affinity_host_id:
        reasons.append("host_affinity_mismatch")

    return SchedulingExplanation(
        compatible=not reasons,
        reasons=reasons,
    )


def probe_oci_profile(
    engine: ContainerEngine,
    profile: ExecutionProfile,
) -> dict[str, object]:
    """探测 OCI profile 是否可在本机运行。

    探测失败抛出 ``ContainerRuntimeUnavailable``。
    Worker 只上报探测成功的 OCI profile。
    """

    if profile.backend != "oci" or profile.oci is None:
        raise ValueError("not an OCI profile")

    probe = engine.probe()
    if not probe.rootless:
        raise ContainerRuntimeUnavailable(
            "strict OCI profile 要求 rootless Podman"
        )
    if probe.cgroup_version not in {"v2", "2"}:
        raise ContainerRuntimeUnavailable(
            "strict OCI profile 要求 cgroup v2"
        )
    if not engine.image_exists(profile.oci.image_ref):
        raise ContainerRuntimeUnavailable(
            "digest-pinned image 不在本机；"
            "执行路径禁止自动 pull"
        )
    return {
        "runtime": probe.runtime,
        "runtime_version": probe.version,
        "profile_id": profile.profile_id,
        "image_ref": profile.oci.image_ref,
    }
