from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import settings
from app.execution.environment import is_sensitive_env_name
from app.schemas import ExecutionProfile


def _require_absolute_path(
    value: str,
    *,
    field: str,
) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"{field} 必须是绝对路径：{value}")
    return path.resolve()


def _validate_execution_profile(
    profile: ExecutionProfile,
) -> ExecutionProfile:
    workspace_root = _require_absolute_path(
        profile.workspace_root,
        field="workspace_root",
    )
    if not workspace_root.is_dir():
        raise ValueError(
            f"workspace_root 不存在或不是目录：{workspace_root}"
        )

    allowed_root = settings.allowed_root.expanduser().resolve()
    artifact_root = _require_absolute_path(
        profile.artifact_root,
        field="artifact_root",
    )
    if (
        artifact_root != allowed_root
        and allowed_root not in artifact_root.parents
    ):
        raise ValueError(
            f"artifact_root 位于 ALLOWED_ROOT 之外：{artifact_root}"
        )

    conda_executable: str | None = None
    if profile.conda_executable:
        executable = _require_absolute_path(
            profile.conda_executable,
            field="conda_executable",
        )
        if not executable.is_file():
            raise ValueError(
                f"conda_executable 不存在或不是文件：{executable}"
            )
        conda_executable = str(executable)

    conda_prefix: str | None = None
    if profile.conda_prefix:
        prefix = _require_absolute_path(
            profile.conda_prefix,
            field="conda_prefix",
        )
        if not prefix.is_dir():
            raise ValueError(
                f"conda_prefix 不存在或不是目录：{prefix}"
            )
        conda_prefix = str(prefix)

    writable_roots = [
        str(
            _require_absolute_path(
                value,
                field="writable_roots",
            )
        )
        for value in profile.writable_roots
    ]

    sensitive_keys = sorted(
        key for key in profile.env if is_sensitive_env_name(key)
    )
    if sensitive_keys:
        raise ValueError(
            "profile.env 禁止包含敏感变量："
            + ", ".join(sensitive_keys)
        )

    return profile.model_copy(
        update={
            "workspace_root": str(workspace_root),
            "artifact_root": str(artifact_root),
            "conda_executable": conda_executable,
            "conda_prefix": conda_prefix,
            "writable_roots": writable_roots,
        }
    )


def load_execution_profiles(path: Path | None = None) -> dict[str, ExecutionProfile]:
    config_path = path or settings.execution_profiles_path
    if not config_path.exists():
        raise FileNotFoundError(f"未找到执行环境配置文件：{config_path}")
    
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    raw_profiles = payload.get("profiles", [])
    profiles: dict[str, ExecutionProfile] = {}
    for raw_profile in raw_profiles:
        profile = _validate_execution_profile(
            ExecutionProfile.model_validate(raw_profile)
        )
        if profile.profile_id in profiles:
            raise ValueError(f"执行环境配置 ID 重复：{profile.profile_id}")

        profiles[profile.profile_id] = profile
    return profiles

def get_execution_profile(profile_id: str) -> ExecutionProfile:
    profiles = load_execution_profiles()
    profile = profiles.get(profile_id)

    if profile is None:
        available = ", ".join(sorted(profiles)) or "<none>"
        raise ValueError(
            f"未找到执行环境配置：{profile_id}；"
            f"可用配置：{available}"
        )

    return profile

def compute_execution_profile_fingerprint(
    profile: ExecutionProfile,
) -> str:
    """
    所有能够改变执行权限或资源上限的字段都必须进入指纹。

    人工审批之后修改任何安全字段，旧 action hash 都必须失效。
    """

    material = {
        "profile_id": profile.profile_id,
        "backend": profile.backend,
        "workspace_root": profile.workspace_root,
        "artifact_root": profile.artifact_root,
        "conda_executable": profile.conda_executable,
        "conda_prefix": profile.conda_prefix,
        "inherited_env_keys": sorted(
            profile.inherited_env_keys
        ),
        "env": profile.env,
        "allowed_action_env_keys": sorted(
            profile.allowed_action_env_keys
        ),
        "allowed_programs": sorted(profile.allowed_programs),
        "blocked_arg_markers": sorted(
            profile.blocked_arg_markers
        ),
        "writable_roots": sorted(profile.writable_roots),
        "network_policy": profile.network_policy,
        "budget": profile.budget.model_dump(),
        "enforcement_mode": profile.enforcement_mode,
        "worker_pool": profile.worker_pool,
        "min_workspace_free_bytes": profile.min_workspace_free_bytes,
        "min_gpu_count": profile.min_gpu_count,
        "cuda_major": profile.cuda_major,
        "required_worker_labels": sorted(
            profile.required_worker_labels
        ),
        # Phase 27：OCI image digest / 资源上限变更必须使旧 action hash 失效。
        "oci": (
            profile.oci.model_dump(mode="json")
            if profile.oci is not None
            else None
        ),
    }

    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def compute_execution_policy_hash(
    profile: ExecutionProfile,
) -> str:
    """
    只用于跨主机调度等价性的 hash。

    它不包含 host-local path，但包含所有安全策略：
    不同主机的 workspace/Conda 绝对路径可以不同，但策略必须一致。
    """

    material = {
        "profile_id": profile.profile_id,
        "backend": profile.backend,
        "inherited_env_keys": sorted(profile.inherited_env_keys),
        "env_keys": sorted(profile.env),
        "allowed_action_env_keys": sorted(
            profile.allowed_action_env_keys
        ),
        "allowed_programs": sorted(profile.allowed_programs),
        "blocked_arg_markers": sorted(profile.blocked_arg_markers),
        "network_policy": profile.network_policy,
        "budget": profile.budget.model_dump(),
        "enforcement_mode": profile.enforcement_mode,
        "worker_pool": profile.worker_pool,
        "min_workspace_free_bytes": profile.min_workspace_free_bytes,
        "min_gpu_count": profile.min_gpu_count,
        "cuda_major": profile.cuda_major,
        "required_worker_labels": sorted(
            profile.required_worker_labels
        ),
        # Phase 27：OCI 配置影响调度等价性和安全边界。
        "oci": (
            profile.oci.model_dump(mode="json")
            if profile.oci is not None
            else None
        ),
    }
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
